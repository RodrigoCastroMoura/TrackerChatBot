import os
import hmac
import hashlib
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from services.orchestrator import orchestrator
from services.session_manager import session_manager
from config.settings import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

print("Chatbot WhatsApp iniciado!")

def verify_signature(payload: bytes, signature: str) -> bool:
    if not Config.APP_SECRET:
        logger.warning("APP_SECRET nao configurado - verificacao de assinatura desabilitada")
        return True
    
    if not signature:
        return False
    
    expected = "sha256=" + hmac.new(
        Config.APP_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "active_sessions": session_manager.get_active_count(),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == Config.VERIFY_TOKEN:
        logger.info("Webhook verificado com sucesso!")
        return challenge, 200
    
    logger.warning("Falha na verificacao do webhook")
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        payload = request.get_data()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        if not verify_signature(payload, signature):
            logger.warning("Assinatura invalida no webhook")
            return "Unauthorized", 401
        
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "no data"}), 200
        
        entry = data.get("entry", [])
        for e in entry:
            changes = e.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                
                # Ignora notificações de status
                if "statuses" in value:
                    continue
                    
                messages = value.get("messages", [])
                for msg in messages:
                    message_id = msg.get("id")
                    if not message_id:
                        continue
                        
                    phone_number = msg.get("from", "")
                    message_type = msg.get("type", "text")
                    if message_type == "text":
                        text = msg.get("text", {}).get("body", "")
                    elif message_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            text = interactive.get("button_reply", {}).get("id", "")
                        elif interactive.get("type") == "list_reply":
                            text = interactive.get("list_reply", {}).get("id", "")
                        else:
                            text = ""
                    else:
                        text = ""
                    
                    if phone_number and text:
                        orchestrator.process_message(phone_number, text, message_type, message_id)
        
        return jsonify({"status": "ok"}), 200
    
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "WhatsApp Chatbot - Sistema de Rastreamento",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/webhook": "WhatsApp webhook (GET para verificacao, POST para mensagens)"
        }
    })

if __name__ == "__main__":
    print("Iniciando servidor Flask...")
    app.run(host="0.0.0.0", port=5000, debug=False)