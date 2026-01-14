import requests
import logging
from config.settings import Config

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self):
        self.api_url = Config.WHATSAPP_API_URL
        self.token = Config.WHATSAPP_TOKEN
        self.phone_number_id = Config.PHONE_NUMBER_ID
    
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def send_message(self, to: str, message: str) -> bool:
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            logger.info(f"Mensagem enviada para {to}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    def send_interactive_buttons(self, to: str, body: str, buttons: list) -> bool:
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        button_list = []
        for i, btn in enumerate(buttons[:3]):
            button_list.append({
                "type": "reply",
                "reply": {
                    "id": btn.get("id", f"btn_{i}"),
                    "title": btn.get("title", f"Opcao {i+1}")[:20]
                }
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": button_list}
            }
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            logger.info(f"Botoes enviados para {to}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar botoes: {e}")
            return False
    
    def send_list(self, to: str, body: str, button_text: str, sections: list) -> bool:
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body},
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            logger.info(f"Lista enviada para {to}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar lista: {e}")
            return False

whatsapp_client = WhatsAppClient()
