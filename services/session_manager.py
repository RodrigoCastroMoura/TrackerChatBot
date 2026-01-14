import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from models.entities import Session
from config.settings import Config

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.timeout_minutes = Config.SESSION_TIMEOUT_MINUTES
    
    def get_session(self, phone_number: str) -> Session:
        self._cleanup_expired()
        
        if phone_number not in self.sessions:
            self.sessions[phone_number] = Session(phone_number=phone_number)
            logger.info(f"Nova sessao criada para {phone_number}")
        
        session = self.sessions[phone_number]
        session.update_activity()
        return session
    
    def end_session(self, phone_number: str) -> bool:
        if phone_number in self.sessions:
            del self.sessions[phone_number]
            logger.info(f"Sessao encerrada para {phone_number}")
            return True
        return False
    
    def get_active_count(self) -> int:
        self._cleanup_expired()
        return len(self.sessions)
    
    def _cleanup_expired(self):
        now = datetime.now()
        expired = []
        
        for phone, session in self.sessions.items():
            if now - session.last_activity > timedelta(minutes=self.timeout_minutes):
                expired.append(phone)
        
        for phone in expired:
            del self.sessions[phone]
            logger.info(f"Sessao expirada removida: {phone}")

session_manager = SessionManager()
