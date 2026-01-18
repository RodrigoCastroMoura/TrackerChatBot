from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Vehicle:
    id: str
    plate: str
    model: str
    status: str = "active"
    last_location: Optional[dict] = None
    is_blocked: bool = False

@dataclass
class User:
    name: str
    vehicles: List[Vehicle] = field(default_factory=list)
    token: Optional[str] = None

@dataclass
class Session:
    phone_number: str
    state: str = "INITIAL"
    user: Optional[User] = None
    cpf_input: Optional[str] = None
    selected_vehicle: Optional[Vehicle] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        self.last_activity = datetime.now()
    
    def is_authenticated(self) -> bool:
        return self.user is not None
