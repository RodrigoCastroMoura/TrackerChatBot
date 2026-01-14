import logging
from typing import Optional, Dict, List
from config.settings import Config
from models.entities import User, Vehicle

logger = logging.getLogger(__name__)

class TrackerAPI:
    def __init__(self):
        self.users = Config.TEST_USERS
    
    def authenticate(self, cpf: str, password: str) -> Optional[User]:
        cpf_clean = cpf.replace(".", "").replace("-", "").strip()
        
        user_data = self.users.get(cpf_clean)
        if user_data and user_data.get("password") == password:
            vehicles = [
                Vehicle(
                    id=v["id"],
                    plate=v["plate"],
                    model=v["model"],
                    status=v["status"]
                ) for v in user_data.get("vehicles", [])
            ]
            logger.info(f"Usuario {cpf_clean} autenticado com sucesso")
            return User(cpf=cpf_clean, name=user_data["name"], vehicles=vehicles)
        
        logger.warning(f"Falha na autenticacao para CPF: {cpf_clean}")
        return None
    
    def get_vehicle_location(self, vehicle_id: str) -> Optional[Dict]:
        locations = {
            "V001": {
                "latitude": -23.550520,
                "longitude": -46.633308,
                "address": "Av. Paulista, 1000 - Sao Paulo, SP",
                "speed": 0,
                "last_update": "2024-01-15 14:30:00"
            },
            "V002": {
                "latitude": -23.561414,
                "longitude": -46.656167,
                "address": "Rua Augusta, 500 - Sao Paulo, SP",
                "speed": 35,
                "last_update": "2024-01-15 14:28:00"
            }
        }
        return locations.get(vehicle_id)
    
    def block_vehicle(self, vehicle_id: str) -> bool:
        logger.info(f"Veiculo {vehicle_id} bloqueado")
        return True
    
    def unblock_vehicle(self, vehicle_id: str) -> bool:
        logger.info(f"Veiculo {vehicle_id} desbloqueado")
        return True

tracker_api = TrackerAPI()
