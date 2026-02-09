import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from models.entities import Session
from config.settings import Config

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.processed_messages: Dict[str, Set[str]] = {}  # phone_number -> set of message_ids
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
    
    def is_message_processed(self, phone_number: str, message_id: str) -> bool:
        """Verifica se a mensagem já foi processada"""
        if phone_number not in self.processed_messages:
            return False
        return message_id in self.processed_messages[phone_number]
    
    def mark_message_processed(self, phone_number: str, message_id: str) -> None:
        """Marca a mensagem como processada"""
        if phone_number not in self.processed_messages:
            self.processed_messages[phone_number] = set()
        self.processed_messages[phone_number].add(message_id)
        
        # Limitar o tamanho do conjunto para evitar uso excessivo de memória
        # Manter apenas os últimos 100 message_ids por usuário
        if len(self.processed_messages[phone_number]) > 100:
            # Remover os mais antigos (arbitrariamente remove alguns)
            messages_list = list(self.processed_messages[phone_number])
            self.processed_messages[phone_number] = set(messages_list[-100:])
    
    def _cleanup_expired(self):
        now = datetime.now()
        expired = []
        
        for phone, session in self.sessions.items():
            if now - session.last_activity > timedelta(minutes=self.timeout_minutes):
                expired.append(phone)
        
        for phone in expired:
            del self.sessions[phone]
            # Limpar também mensagens processadas de sessões expiradas
            if phone in self.processed_messages:
                del self.processed_messages[phone]
            logger.info(f"Sessao expirada removida: {phone}")

session_manager = SessionManager()