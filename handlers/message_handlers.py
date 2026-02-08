import logging
from typing import Optional
from models.entities import Session, Vehicle
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
        handler(session, message, message_type)
    
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
    
    def _handle_initial(self, session: Session, message: str, message_type: str = "text") -> None:

        if session.is_authenticated():
            self._show_vehicles(session)
            return
        else:
            phone_number = self.remover_caracteres_esquerda(session.phone_number)
            user = business_service.authenticate_user(phone_number, Config.PASSWORD_CHATBOT_SALT, "auth/customer/chatbot/login")

            if user:
                session.user = user
                session.state = "AUTHENTICATED"
                self._show_vehicles(session)
                return
            else:
                self._handle_menu(session)
                return
    
    def _handle_cpf(self, session: Session, message: str, message_type: str = "text") -> None:
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
    
    def _handle_password(self, session: Session, message: str, message_type: str = "text") -> None:
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
    
    def _handle_authenticated(self, session: Session, message: str, message_type: str = "text") -> None:
        msg_lower = message.lower().strip()
        
        logger.info(f"=== HANDLE_AUTHENTICATED ===")
        logger.info(f"Phone: {session.phone_number}")
        logger.info(f"Message: '{message}'")
        logger.info(f"Message_type: '{message_type}'")
        logger.info(f"Estado atual: {session.state}")
        logger.info(f"Veiculo atual selecionado: {session.selected_vehicle.plate if session.selected_vehicle else 'None'}")
        
        # Busca veículo por ID (lista) ou placa (texto)
        vehicle = None
        if message_type == "interactive":
            logger.info(f"Buscando veiculo por ID: '{message}'")
            vehicle = self.get_vehicle_by_id(session, message)
            logger.info(f"Veiculo encontrado por ID: {vehicle.plate if vehicle else 'None'}")
        if not vehicle:
            logger.info(f"Buscando veiculo por placa: '{msg_lower}'")
            vehicle = self.get_vehicle_by_plate(session, msg_lower)
            logger.info(f"Veiculo encontrado por placa: {vehicle.plate if vehicle else 'None'}")
        
        if vehicle:
            logger.info(f"ATUALIZANDO selected_vehicle DE {session.selected_vehicle.plate if session.selected_vehicle else 'None'} PARA {vehicle.plate}")
            session.state = "VEHICLE_SELECTED"
            session.selected_vehicle = vehicle
            logger.info(f"selected_vehicle atualizado: {session.selected_vehicle.plate}")
            self._show_vehicle_options(session)
            return
        else:
            logger.warning(f"Veiculo nao encontrado para mensagem: '{message}'")
            whatsapp_client.send_message(
                session.phone_number,
                "Veiculo nao encontrado."
            )
            self._show_vehicles(session)
            return
          
    def _show_vehicles(self, session: Session) -> None:
        user = session.user
        greeting = f"Olá, {user.name}!\n\n" if not session.user.intrudution_shown else ""
    
        if  len(session.user.vehicles) == 0:  
            session.user.intrudution_shown = True        
            whatsapp_client.send_message(
                session.phone_number,
                f"{greeting}"
                f"Você não possui veículos cadastrados no sistema de Rastreamento."
            )
            return

        elif len(session.user.vehicles) == 1:
            session.selected_vehicle = session.user.vehicles[0]
            session.state = "VEHICLE_SELECTED"
            self._show_vehicle_options(session)
            return
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
            session.user.intrudution_shown = True
            session.state = "AUTHENTICATED"
            session.selected_vehicle = None  # Limpa seleção anterior
            whatsapp_client.send_list(
                session.phone_number,
                f"{greeting}"
                f"Você esta no sistema de Rastreamento!\n\n"
                f"Selecione um veiculo para ver opcoes:",
                "Ver Veiculos",
                sections
            )
            return
  
    def _show_vehicle_options(self, session: Session) -> None:
        vehicle = session.selected_vehicle
        user = session.user
        status = "Bloqueado" if vehicle.is_blocked else "Desbloqueado" 
        greeting = f"Olá, {user.name}!\n\n Você esta no sistema de Rastreamento!\n\n" if len(session.user.vehicles) == 1 and not session.user.intrudution_shown else "Você esta no sistema de Rastreamento!\n\n"
        session.user.intrudution_shown = True
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
                {"id": "sair"  if len(session.user.vehicles) == 1  else "menu", 
                "title": "Sair" if len(session.user.vehicles) == 1 else "Menu"}
               
            ]
        )
    
    def _handle_vehicle_action(self, session: Session, message: str, message_type: str = "text") -> None:
        msg_lower = message.lower().strip()
        vehicle = session.selected_vehicle
        
        logger.info(f"=== HANDLE_VEHICLE_ACTION ===")
        logger.info(f"Phone: {session.phone_number}")
        logger.info(f"Message: '{message}'")
        logger.info(f"Estado: {session.state}")
        logger.info(f"Veiculo selecionado: {vehicle.plate if vehicle else 'None'} (ID: {vehicle.id if vehicle else 'None'})")

        # Define os botões baseado na quantidade de veículos
        if len(session.user.vehicles) == 1:
            buttons = [
                {"id": "voltar", "title": "Voltar"},
                {"id": "sair", "title": "Sair"}
            ]
        else:
            buttons = [
                {"id": "voltar", "title": "Voltar"},
                {"id": "menu", "title": "Menu"},
                {"id": "sair", "title": "Sair"}
            ]
     
        if msg_lower in ["localizacao", "loc", "l"]:
            location = business_service.get_vehicle_location(vehicle, session)
            if location:
                whatsapp_client.send_interactive_buttons(
                    session.phone_number,
                    f"Localizacao do veiculo modelo {vehicle.model} de placa {vehicle.plate}:\n\n"
                    f"Endereco: {location['address']}\n"
                    f"Velocidade: {location['speed']} km/h\n"
                    f"Ultima atualizacao: {location['last_update']}\n\n"
                    f"Maps: https://maps.google.com/?q={location['latitude']},{location['longitude']}\n\n"
                    "Escolha uma opcao:",
                    buttons
                )
            else:
                whatsapp_client.send_interactive_buttons(
                    session.phone_number,
                    "Nao foi possivel obter a localizacao. Tente novamente.",
                    buttons
                )
               
        elif msg_lower in ["bloquear", "block", "b"]:
            success, msg = business_service.block_vehicle(vehicle, session)
            whatsapp_client.send_interactive_buttons(
                    session.phone_number,
                    f"{msg}\n\n"
                    "Escolha uma opcao:",
                    buttons
                )
        
        elif msg_lower in ["desbloquear", "unblock", "u"]:
            success, msg = business_service.unblock_vehicle(vehicle, session)
            whatsapp_client.send_interactive_buttons(
                    session.phone_number,
                    f"{msg}\n\n"
                    "Escolha uma opcao:",
                    buttons
                )
        
        elif msg_lower in ["voltar", "back"]:
             self._show_vehicle_options(session)
        
        elif msg_lower in ["menu"]:
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
    
    def _handle_unknown(self, session: Session, message: str, message_type: str = "text") -> None:
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
    
    def get_vehicle_by_plate(self, session: Session, plate: str) -> Optional[Vehicle]:
        for vehicle in session.user.vehicles:
            if vehicle.plate.lower().strip() == plate:
                return vehicle
            if vehicle.model.lower().strip() == plate:
                return vehicle
        return None
    
    def get_vehicle_by_id(self, session: Session, vehicle_id: str) -> Optional[Vehicle]:
        """Busca veículo pelo ID (usado em lista interativa)"""
        logger.info(f"=== GET_VEHICLE_BY_ID ===")
        logger.info(f"Buscando ID: '{vehicle_id}'")
        logger.info(f"Veiculos disponiveis:")
        for v in session.user.vehicles:
            logger.info(f"  - {v.plate}: ID='{v.id}' (match: {str(v.id).strip() == str(vehicle_id).strip()})")
        
        for vehicle in session.user.vehicles:
            if str(vehicle.id).strip() == str(vehicle_id).strip():
                logger.info(f"MATCH! Veiculo encontrado: {vehicle.plate}")
                return vehicle
        
        logger.warning(f"Nenhum veiculo encontrado com ID: '{vehicle_id}'")
        return None