import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from models.entities import Session
from config.settings import Config

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Gerenciador de sessões com deduplicação de mensagens.
    
    IMPORTANTE: Em produção com múltiplos workers Gunicorn,
    este gerenciador é POR WORKER. Para compartilhar estado
    entre workers, use Redis ou banco de dados.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.processed_messages: Dict[str, Set[str]] = {}  # phone -> set(message_ids)
        self.timeout_minutes = Config.SESSION_TIMEOUT_MINUTES
        
        # Configuração de limpeza automática
        self.max_messages_per_user = 100  # Limitar memória
        self.cleanup_counter = 0
        self.cleanup_interval = 50  # Limpar a cada 50 operações
    
    def get_session(self, phone_number: str) -> Session:
        """
        Obtém ou cria uma sessão para o telefone.
        
        Args:
            phone_number: Número do telefone do usuário
            
        Returns:
            Session: Sessão do usuário
        """
        self._auto_cleanup()
        
        if phone_number not in self.sessions:
            self.sessions[phone_number] = Session(phone_number=phone_number)
            logger.info(f"Nova sessao criada para {phone_number}")
        
        session = self.sessions[phone_number]
        session.update_activity()
        return session
    
    def end_session(self, phone_number: str) -> bool:
        """
        Encerra uma sessão e limpa mensagens processadas.
        
        Args:
            phone_number: Número do telefone
            
        Returns:
            bool: True se sessão foi encerrada, False se não existia
        """
        if phone_number in self.sessions:
            del self.sessions[phone_number]
            
            # Limpar mensagens processadas também
            if phone_number in self.processed_messages:
                del self.processed_messages[phone_number]
            
            logger.info(f"Sessao encerrada para {phone_number}")
            return True
        return False
    
    def get_active_count(self) -> int:
        """Retorna número de sessões ativas"""
        self._cleanup_expired()
        return len(self.sessions)
    
    def is_message_processed(self, phone_number: str, message_id: str) -> bool:
        """
        Verifica se uma mensagem já foi processada (deduplicação).
        
        Args:
            phone_number: Número do telefone
            message_id: ID único da mensagem do WhatsApp
            
        Returns:
            bool: True se já foi processada, False caso contrário
        """
        if not message_id:
            return False
        
        if phone_number not in self.processed_messages:
            return False
        
        return message_id in self.processed_messages[phone_number]
    
    def mark_message_processed(self, phone_number: str, message_id: str) -> None:
        """
        Marca uma mensagem como processada.
        
        Args:
            phone_number: Número do telefone
            message_id: ID único da mensagem
        """
        if not message_id:
            return
        
        # Inicializar conjunto se não existir
        if phone_number not in self.processed_messages:
            self.processed_messages[phone_number] = set()
        
        # Adicionar message_id
        self.processed_messages[phone_number].add(message_id)
        
        # Limitar tamanho do conjunto (prevenir uso excessivo de memória)
        if len(self.processed_messages[phone_number]) > self.max_messages_per_user:
            # Converter para lista, pegar últimos N, converter de volta para set
            messages_list = list(self.processed_messages[phone_number])
            self.processed_messages[phone_number] = set(messages_list[-self.max_messages_per_user:])
            logger.debug(f"Limitado histórico de mensagens para {phone_number}")
    
    def _cleanup_expired(self):
        """Remove sessões expiradas pelo timeout"""
        now = datetime.now()
        expired = []
        
        for phone, session in self.sessions.items():
            if now - session.last_activity > timedelta(minutes=self.timeout_minutes):
                expired.append(phone)
        
        for phone in expired:
            del self.sessions[phone]
            
            # Limpar mensagens processadas também
            if phone in self.processed_messages:
                del self.processed_messages[phone]
            
            logger.info(f"Sessao expirada removida: {phone}")
    
    def _auto_cleanup(self):
        """
        Limpeza automática periódica.
        
        Executa limpeza a cada N operações para evitar
        sobrecarga em cada requisição.
        """
        self.cleanup_counter += 1
        
        if self.cleanup_counter >= self.cleanup_interval:
            self._cleanup_expired()
            self.cleanup_counter = 0
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do gerenciador de sessões.
        
        Returns:
            dict: Estatísticas incluindo número de sessões e mensagens
        """
        return {
            "active_sessions": len(self.sessions),
            "tracked_users": len(self.processed_messages),
            "total_processed_messages": sum(len(msgs) for msgs in self.processed_messages.values())
        }

# Instância global (compartilhada apenas dentro do worker)
session_manager = SessionManager()