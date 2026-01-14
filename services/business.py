import logging
from typing import Optional, Tuple
from models.entities import User, Vehicle
from clients.tracker_api import tracker_api

logger = logging.getLogger(__name__)

class BusinessService:
    def __init__(self):
        self.api = tracker_api
    
    def authenticate_user(self, cpf: str, password: str) -> Optional[User]:
        return self.api.authenticate(cpf, password)
    
    def get_vehicle_location(self, vehicle: Vehicle) -> Optional[dict]:
        return self.api.get_vehicle_location(vehicle.id)
    
    def block_vehicle(self, vehicle: Vehicle) -> Tuple[bool, str]:
        success = self.api.block_vehicle(vehicle.id)
        if success:
            vehicle.is_blocked = True
            return True, f"Veiculo {vehicle.plate} bloqueado com sucesso!"
        return False, "Erro ao bloquear veiculo. Tente novamente."
    
    def unblock_vehicle(self, vehicle: Vehicle) -> Tuple[bool, str]:
        success = self.api.unblock_vehicle(vehicle.id)
        if success:
            vehicle.is_blocked = False
            return True, f"Veiculo {vehicle.plate} desbloqueado com sucesso!"
        return False, "Erro ao desbloquear veiculo. Tente novamente."

business_service = BusinessService()
