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
        
        # Deduplicação: verifica se a mensagem já foi processada
        if message_id and session_manager.is_message_processed(phone_number, message_id):
            logger.info(f"Mensagem duplicada ignorada: {message_id} de {phone_number}")
            return
        
        # Marca a mensagem como processada ANTES de processar
        if message_id:
            session_manager.mark_message_processed(phone_number, message_id)
        
        # Processa a mensagem
        session = session_manager.get_session(phone_number)
        
        logger.info(f"Mensagem de {phone_number}: {message} (estado: {session.state})")
        
        try:
            self.handler.handle(session, message, message_type)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem {message_id}: {e}", exc_info=True)

orchestrator = MessageOrchestrator()