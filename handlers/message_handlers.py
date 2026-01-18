import logging
from models.entities import Session
from services.business import business_service
from services.session_manager import session_manager
from clients.whatsapp import whatsapp_client
from config.settings import Config
logger = logging.getLogger(__name__)

class MessageHandler:
    
    def handle(self, session: Session, message: str, message_type: str = "text") -> None:
        msg_lower = message.lower().strip()
        
        if msg_lower == "sair":
            self._handle_logout(session)
            return
        
        state_handlers = {
            "INITIAL": self._handle_initial,
            "WAITING_CPF": self._handle_cpf,
            "WAITING_PASSWORD": self._handle_password,
            "AUTHENTICATED": self._handle_authenticated,
            "VEHICLE_SELECTED": self._handle_vehicle_action
        }
        
        handler = state_handlers.get(session.state, self._handle_unknown)
        handler(session, message)
    
    def _handle_menu(self, session: Session) -> None:
        if session.is_authenticated():
            self._show_vehicles(session)
        else:
            session.state = "WAITING_CPF"
            whatsapp_client.send_message(
                session.phone_number,
                "Bem-vindo ao Sistema de Rastreamento!\n\n"
                "Para continuar, digite seu CPF (apenas numeros):"
            )
    
    def _handle_initial(self, session: Session, message: str) -> None:

        phone_number = self.remover_caracteres_esquerda(session.phone_number)
        user = business_service.authenticate_user(phone_number, Config.PASSWORD_CHATBOT_SALT, "auth/customer/chatbot/login")
        if user:
            session.user = user
            session.state = "AUTHENTICATED"
            self._show_vehicles(session)
        else:
            self._handle_menu(session)
    
    def _handle_cpf(self, session: Session, message: str) -> None:
        cpf_clean = message.replace(".", "").replace("-", "").strip()
        
        if len(cpf_clean) != 11 or not cpf_clean.isdigit():
            whatsapp_client.send_message(
                session.phone_number,
                "CPF invalido. Digite apenas os 11 numeros do seu CPF:"
            )
            return
        
        session.cpf_input = cpf_clean
        session.state = "WAITING_PASSWORD"
        whatsapp_client.send_message(
            session.phone_number,
            "Agora digite sua senha:"
        )
    
    def _handle_password(self, session: Session, message: str) -> None:
        user = business_service.authenticate_user(session.cpf_input, message, "auth/customer/login")
        
        if user:
            session.user = user
            session.state = "AUTHENTICATED"
            self._show_vehicles(session)
        else:
            session.state = "WAITING_CPF"
            session.cpf_input = None
            whatsapp_client.send_message(
                session.phone_number,
                "CPF ou senha incorretos.\n\n"
                "Digite seu CPF novamente para tentar:"
            )
    
    def _show_main_menu(self, session: Session) -> None:
        user = session.user
        vehicle_list = "\n".join([
            f"  - {v.plate} ({v.model})" for v in user.vehicles
        ])
        
        whatsapp_client.send_interactive_buttons(
            session.phone_number,
            f"Ola, {user.name}!\n\n"
            f"Seus veiculos:\n{vehicle_list}\n\n"
            "O que deseja fazer?",
            [
                {"id": "ver_veiculos", "title": "Ver Veiculos"},
                {"id": "sair", "title": "Sair"}
            ]
        )
    
    def _handle_authenticated(self, session: Session, message: str) -> None:
        msg_lower = message.lower().strip()
        
        if msg_lower in ["ver_veiculos", "veiculos", "v"]:
            self._show_vehicles(session)
        elif msg_lower.startswith("v"):
            vehicle_num = msg_lower.replace("v", "").strip()
            if vehicle_num.isdigit():
                idx = int(vehicle_num) - 1
                if 0 <= idx < len(session.user.vehicles):
                    session.selected_vehicle = session.user.vehicles[idx]
                    session.state = "VEHICLE_SELECTED"
                    self._show_vehicle_options(session)
                    return
            self._show_main_menu(session)
        else:
            for i, v in enumerate(session.user.vehicles):
                if v.id == message or v.plate.replace("-", "").lower() == msg_lower.replace("-", ""):
                    session.selected_vehicle = v
                    session.state = "VEHICLE_SELECTED"
                    self._show_vehicle_options(session)
                    return
            self._show_main_menu(session)
    
    def _show_vehicles(self, session: Session) -> None:
        user = session.user
          
        if  session.user.vehicles.count == 0:          
            whatsapp_client.send_message(
                session.phone_number,
                f"Olá, {user.name}!\n\n"
                f"Você não possui veículos cadastrados no sistema de Rastreamento."
            )

        elif  session.user.vehicles.count == 1:
            session.selected_vehicle = session.user.vehicles[0]
            self._show_vehicle_options(session)
        else:
            sections = [{
                "title": "Seus Veiculos",
                "rows": [
                    {
                        "id": v.id,
                        "title": v.plate,
                        "description": v.model
                    } for v in session.user.vehicles
                ]
            }]
            
            whatsapp_client.send_list(
                session.phone_number,
                f"Olá, {user.name}!\n\n"
                f"Você esta no sistema de Rastreamento!\n\n"
                f"Selecione um veiculo para ver opcoes:",
                "Ver Veiculos",
                sections
            )
        
    def _show_vehicle_options(self, session: Session) -> None:
        vehicle = session.selected_vehicle
        user = session.user
        status = "Bloqueado" if vehicle.is_blocked else "Ativo" 
        greeting = f"Olá, {user.name}!\n\n" if session.user.vehicles.count == 1 else ""

        whatsapp_client.send_interactive_buttons(
            session.phone_number,
            f"{greeting}"
            f"Veiculo: {vehicle.plate}\n"
            f"Modelo: {vehicle.model}\n"
            f"Status: {status}\n\n"
            "Escolha uma opcao:",
            [
                {"id": "localizacao", "title": "Localizacao"},
                {"id": "bloquear" if not vehicle.is_blocked else "desbloquear", 
                "title": "Bloquear" if not vehicle.is_blocked else "Desbloquear"},
                {"id": "voltar", "title": "Voltar"},
                {"id": "sair", "title": "Sair"}
                
            ]
        )
    
    def _handle_vehicle_action(self, session: Session, message: str) -> None:
        msg_lower = message.lower().strip()
        vehicle = session.selected_vehicle
        
        if msg_lower in ["localizacao", "loc", "l"]:
            location = business_service.get_vehicle_location(vehicle, session)
            if location:
                whatsapp_client.send_message(
                    session.phone_number,
                    f"Localizacao de {vehicle.plate}:\n\n"
                    f"Endereco: {location['address']}\n"
                    f"Velocidade: {location['speed']} km/h\n"
                    f"Ultima atualizacao: {location['last_update']}\n\n"
                    f"Maps: https://maps.google.com/?q={location['latitude']},{location['longitude']}"
                )
            else:
                whatsapp_client.send_message(
                    session.phone_number,
                    "Nao foi possivel obter a localizacao. Tente novamente."
                )
            self._show_vehicle_options(session)
        
        elif msg_lower in ["bloquear", "block", "b"]:
            success, msg = business_service.block_vehicle(vehicle, session)
            whatsapp_client.send_message(session.phone_number, msg)
            self._show_vehicle_options(session)
        
        elif msg_lower in ["desbloquear", "unblock", "u"]:
            success, msg = business_service.unblock_vehicle(vehicle, session)
            whatsapp_client.send_message(session.phone_number, msg)
            self._show_vehicle_options(session)
        
        elif msg_lower in ["voltar", "back", "menu"]:
            session.selected_vehicle = None
            session.state = "AUTHENTICATED"
            self._show_vehicles(session)
        
        else:
            self._show_vehicle_options(session)
    
    def _handle_logout(self, session: Session) -> None:
        phone = session.phone_number
        session_manager.end_session(phone)
        whatsapp_client.send_message(
            phone,
            "Sessao encerrada com sucesso!\n\n"
            "Muito obrigado por usar o nosso serviços.\n"
        )
    
    def _handle_unknown(self, session: Session, message: str) -> None:
        whatsapp_client.send_message(
            session.phone_number,
            "Nao entendi sua mensagem.\n"
            "Digite *menu* para ver as opcoes."
        )

    def remover_caracteres_esquerda(self,numero_str, quantidade=2):
        """
        Remove N caracteres da esquerda de uma string
        
        Args:
            numero_str: String a ser processada
            quantidade: Número de caracteres a remover (padrão: 2)
        """
        return numero_str[quantidade:]