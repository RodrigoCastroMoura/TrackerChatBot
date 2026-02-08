import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from models.entities import Session
from config.settings import Config

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.processed_messages: Dict[str, Set[str]] = {}  # phone -> set of message_ids
        self.timeout_minutes = Config.SESSION_TIMEOUT_MINUTES
        self.message_expiry_minutes = 5  # Tempo para manter histórico de mensagens processadas
    
    def get_session(self, phone_number: str) -> Session:
        self._cleanup_expired()
        
        if phone_number not in self.sessions:
            self.sessions[phone_number] = Session(phone_number=phone_number)
            self.processed_messages[phone_number] = set()
            logger.info(f"Nova sessao criada para {phone_number}")
        
        session = self.sessions[phone_number]
        session.update_activity()
        return session
    
    def is_message_processed(self, phone_number: str, message_id: str) -> bool:
        """Verifica se uma mensagem já foi processada"""
        if phone_number not in self.processed_messages:
            self.processed_messages[phone_number] = set()
        
        return message_id in self.processed_messages[phone_number]
    
    def mark_message_processed(self, phone_number: str, message_id: str) -> None:
        """Marca uma mensagem como processada"""
        if phone_number not in self.processed_messages:
            self.processed_messages[phone_number] = set()
        
        self.processed_messages[phone_number].add(message_id)
        logger.debug(f"Mensagem {message_id} marcada como processada para {phone_number}")
    
    def end_session(self, phone_number: str) -> bool:
        if phone_number in self.sessions:
            del self.sessions[phone_number]
            # Mantém o histórico de mensagens por um tempo
            logger.info(f"Sessao encerrada para {phone_number}")
            return True
        return False
    
    def get_active_count(self) -> int:
        self._cleanup_expired()
        return len(self.sessions)
    
    def _cleanup_expired(self):
        now = datetime.now()
        expired_sessions = []
        expired_messages = []
        
        # Limpar sessões expiradas
        for phone, session in self.sessions.items():
            if now - session.last_activity > timedelta(minutes=self.timeout_minutes):
                expired_sessions.append(phone)
        
        for phone in expired_sessions:
            del self.sessions[phone]
            logger.info(f"Sessao expirada removida: {phone}")
        
        # Limpar histórico de mensagens antigas (não implementado por simplicidade)
        # Você pode adicionar timestamps às mensagens processadas se necessário

session_manager = SessionManager()