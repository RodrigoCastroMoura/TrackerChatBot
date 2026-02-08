import logging
from models.entities import Session
from services.session_manager import session_manager
from handlers.message_handlers import MessageHandler

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    def __init__(self):
        self.handler = MessageHandler()
    
    def process_message(self, phone_number: str, message: str, message_type: str = "text", message_id: str = None) -> None:
        """
        Processa uma mensagem com deduplicação
        
        Args:
            phone_number: Número do telefone do usuário
            message: Texto da mensagem
            message_type: Tipo da mensagem (text, interactive, etc)
            message_id: ID único da mensagem para deduplicação
        """
        
        # Se não tiver message_id, processa normalmente (para compatibilidade)
        if not message_id:
            logger.warning(f"Mensagem sem ID recebida de {phone_number} - processando sem deduplicação")
            session = session_manager.get_session(phone_number)
            logger.info(f"Mensagem de {phone_number}: {message} (estado: {session.state})")
            self.handler.handle(session, message, message_type)
            return
        
        # Verifica se a mensagem já foi processada
        if session_manager.is_message_processed(phone_number, message_id):
            logger.info(f"Mensagem duplicada ignorada: {message_id} de {phone_number}")
            return
        
        # Marca a mensagem como processada ANTES de processar
        # para evitar condições de corrida
        session_manager.mark_message_processed(phone_number, message_id)
        
        # Processa a mensagem
        session = session_manager.get_session(phone_number)
        logger.info(f"Mensagem de {phone_number}: {message} (ID: {message_id}, estado: {session.state})")
        
        try:
            self.handler.handle(session, message, message_type)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem {message_id}: {e}", exc_info=True)

orchestrator = MessageOrchestrator()