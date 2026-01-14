import os

class Config:
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "meu_token_secreto_123")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
    APP_SECRET = os.getenv("APP_SECRET", "")
    
    WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"
    
    SESSION_TIMEOUT_MINUTES = 30
    
    TEST_USERS = {
        "12345678900": {
            "password": "123456",
            "name": "Usuario Teste",
            "vehicles": [
                {"id": "V001", "plate": "ABC-1234", "model": "Honda CG 160", "status": "active"},
                {"id": "V002", "plate": "XYZ-5678", "model": "Yamaha Factor 150", "status": "active"}
            ]
        }
    }
