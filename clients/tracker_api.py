import logging
from typing import Optional, Dict, List
from config.settings import Config
from models.entities import User, Vehicle
import requests

logger = logging.getLogger(__name__)

class TrackerAPI:
    def __init__(self):
        self.url = Config.API_BASE_URL
        self.request_timeout = Config.SESSION_TIMEOUT_MINUTES
    
    def authenticate(self, identifier: str, password: str, url: str) -> Optional[User]:
        
        response = requests.post(f"{self.url}/{url}",
                                     json={
                                         'identifier': identifier,
                                         'password': password
                                     },
                                     timeout=self.request_timeout)
        if response.status_code == 200:
            data = response.json()
            user = User(
                name=data['user'].get("name"),
                token=data['access_token']
            )

            Vehicle_response = requests.get(f"{self.url}//tracking/vehicles",
                                     headers={
                                            'Authorization': f'Bearer {user.token}',
                                            'Accept': 'application/json',
                                            'Content-Type': 'application/json'
                                        },
                                     timeout=self.request_timeout)
            
            if Vehicle_response.status_code == 200:
                vehicles_data = Vehicle_response.json()
                vehicles = []
                for v in vehicles_data["vehicles"]:
                    vehicle = Vehicle(
                        id=v.get("id"),
                        plate=v.get("plate"),
                        model=v.get("model"),
                        blocked=v.get("block"),
                        is_blocked=v.get("block") == "bloqueado"
                    )
                    vehicles.append(vehicle)
                user.vehicles = vehicles

            return user
        return None

    def get_vehicle_location(self, vehicle_id: str, token: str) -> Optional[Dict]:
        try:
            response = requests.get(f"{self.url}/tracking/vehicles/{vehicle_id}/location",
                                         headers={
                                                'Authorization': f'Bearer {token}',
                                                'Accept': 'application/json',
                                                'Content-Type': 'application/json'
                                            },
                                         timeout=self.request_timeout)
            if response.status_code == 200:
                data = response.json()
                locations = {
                    "latitude": data["location"].get("lat"),
                    "longitude": data["location"].get("lng"),
                    "address": data["location"].get("address"),
                    "speed": data["location"].get("speed"),
                    "last_update": data["location"].get("timestamp")
                }
                return locations
            else:
                logger.warning(f"Falha ao obter localização: status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erro ao obter localização do veículo {vehicle_id}: {e}")
            return None
    
    def block_vehicle(self, vehicle_id: str, token: str) -> bool:
    
        response = requests.post(f"{self.url}/vehicles/{vehicle_id}/block",
                                headers={
                                    'Authorization': f'Bearer {token}',
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json'
                                },
                                json={"comando": "bloquear"},
                                timeout=self.request_timeout)
        
        if response.status_code != 200:
            return False
        
        logger.info(f"Comando de bloqueio enviado para o veiculo {vehicle_id}")
        return True
    
    def unblock_vehicle(self, vehicle_id: str, token: str) -> bool:
        response = requests.post(f"{self.url}/vehicles/{vehicle_id}/block",
                                headers={
                                    'Authorization': f'Bearer {token}',
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json'
                                },
                                json={"comando": "desbloquear"},
                                timeout=self.request_timeout)
        
        if response.status_code != 200:
            return False
        
        logger.info(f"Veiculo {vehicle_id} desbloqueado")
        return True

tracker_api = TrackerAPI()