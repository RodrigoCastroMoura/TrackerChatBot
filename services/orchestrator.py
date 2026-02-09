import logging
from models.entities import Session
from services.session_manager import session_manager
from handlers.message_handlers import MessageHandler

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    """
    Orquestrador de mensagens com deduplicação.
    
    Responsável por:
    1. Verificar se mensagem já foi processada (deduplicação)
    2. Marcar mensagem como processada
    3. Obter/criar sessão do usuário
    4. Delegar processamento ao handler apropriado
    """
    
    def __init__(self):
        self.handler = MessageHandler()
    
    def process_message(
        self, 
        phone_number: str, 
        message: str, 
        message_type: str = "text", 
        message_id: str = None
    ) -> None:
        """
        Processa uma mensagem do WhatsApp com deduplicação.
        
        Args:
            phone_number: Número do telefone do usuário
            message: Conteúdo da mensagem
            message_type: Tipo da mensagem (text, interactive, etc)
            message_id: ID único da mensagem para deduplicação
        """
        
        # PASSO 1: Deduplicação - Verificar se já foi processada
        if message_id and session_manager.is_message_processed(phone_number, message_id):
            logger.info(f"[DEDUP] Mensagem duplicada ignorada: {message_id[:20]}... de {phone_number}")
            return
        
        # PASSO 2: Marcar como processada ANTES de processar
        # (previne race conditions se mesma mensagem chegar simultaneamente)
        if message_id:
            session_manager.mark_message_processed(phone_number, message_id)
        
        # PASSO 3: Obter sessão do usuário
        session = session_manager.get_session(phone_number)
        
        # PASSO 4: Log para debugging
        logger.info(f"[PROCESS] {phone_number} | Estado: {session.state} | Tipo: {message_type} | Msg: '{message[:50]}'")
        
        # PASSO 5: Processar mensagem
        try:
            self.handler.handle(session, message, message_type)
        except Exception as e:
            logger.error(f"[ERROR] Erro ao processar mensagem {message_id}: {e}", exc_info=True)
            # Não re-raise - queremos que o webhook retorne 200 mesmo com erro interno

# Instância global
orchestrator = MessageOrchestrator()