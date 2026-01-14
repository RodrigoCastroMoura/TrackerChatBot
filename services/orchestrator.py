import logging
from models.entities import Session
from services.session_manager import session_manager
from handlers.message_handlers import MessageHandler

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    def __init__(self):
        self.handler = MessageHandler()
    
    def process_message(self, phone_number: str, message: str, message_type: str = "text") -> None:
        session = session_manager.get_session(phone_number)
        
        logger.info(f"Mensagem de {phone_number}: {message} (estado: {session.state})")
        
        self.handler.handle(session, message, message_type)

orchestrator = MessageOrchestrator()
