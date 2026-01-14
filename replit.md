# WhatsApp Chatbot - Sistema de Rastreamento

## Overview
A WhatsApp chatbot integrated with Meta Business API for vehicle tracking with authentication, session management, and interactive commands.

## Project Structure
```
.
├── app.py                    # Main Flask application with webhook endpoints
├── requirements.txt          # Python dependencies
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration and environment variables
├── models/
│   ├── __init__.py
│   └── entities.py           # Data models (User, Vehicle, Session)
├── clients/
│   ├── __init__.py
│   ├── whatsapp.py           # WhatsApp API client
│   └── tracker_api.py        # Vehicle tracking API (mock)
├── services/
│   ├── __init__.py
│   ├── session_manager.py    # Session handling
│   ├── business.py           # Business logic
│   └── orchestrator.py       # Message orchestration
└── handlers/
    ├── __init__.py
    └── message_handlers.py   # Command handlers
```

## Required Secrets
Configure these in Replit Secrets:
- `WHATSAPP_TOKEN`: Meta Business API token
- `VERIFY_TOKEN`: Webhook verification token (default: meu_token_secreto_123)
- `PHONE_NUMBER_ID`: WhatsApp Phone Number ID from Meta
- `APP_SECRET`: Meta App Secret (for webhook signature verification)

## Endpoints
- `GET /`: API info
- `GET /health`: Health check with active sessions count
- `GET /webhook`: Meta webhook verification
- `POST /webhook`: Receive WhatsApp messages

## Bot Commands
| Command | Action |
|---------|--------|
| menu | Start/restart conversation |
| veiculos | List vehicles |
| sair | End session |

## Test Credentials
- CPF: 12345678900
- Password: 123456

## Running Locally
```bash
python app.py
```

## Webhook Setup (Meta)
1. Go to Meta Developers > WhatsApp > Configuration
2. Callback URL: https://your-repl-url.repl.co/webhook
3. Verify Token: meu_token_secreto_123
4. Subscribe to: messages

## Recent Changes
- 2026-01-14: Initial project setup with full chatbot functionality
