import logging
from models.entities import Session, Vehicle
from services.business import business_service
from services.session_manager import session_manager
from clients.whatsapp import whatsapp_client
from config.settings import Config
logger = logging.getLogger(__name__)

class MessageHandler:
    
    def handle(self, session: Session, message: str, message_type: str = "text") -> None:
        msg_lower = message.lower().strip()
        
        logger.info(f"[HANDLER] Estado atual: {session.state}, Mensagem: '{message}', Tipo: {message_type}")
        
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
        """
        Trata a seleção de veículo quando o estado é AUTHENTICATED
        """
        msg_lower = message.lower().strip()
        
        logger.info(f"[AUTHENTICATED] Recebido: '{message}', tipo: {message_type}")
        logger.info(f"[AUTHENTICATED] Veiculos disponiveis: {[(v.id, v.plate) for v in session.user.vehicles]}")
        
        # Se for uma mensagem interativa (lista), a mensagem virá como o ID do veículo
        vehicle = None
        
        # Primeiro: tenta encontrar pelo ID exato (vem da lista interativa)
        if message_type == "interactive":
            logger.info(f"[AUTHENTICATED] Tentando buscar veiculo por ID: {message}")
            vehicle = self.get_vehicle_by_id(session, message)
            if vehicle:
                logger.info(f"[AUTHENTICATED] Veiculo encontrado por ID: {vehicle.plate}")
        
        # Segundo: se não encontrou e é mensagem de texto, tenta pela placa/modelo
        if not vehicle and message_type == "text":
            logger.info(f"[AUTHENTICATED] Tentando buscar veiculo por placa/modelo: {msg_lower}")
            vehicle = self.get_vehicle_by_plate(session, msg_lower)
            if vehicle:
                logger.info(f"[AUTHENTICATED] Veiculo encontrado por placa/modelo: {vehicle.plate}")
        
        # Se encontrou o veículo, muda para estado VEHICLE_SELECTED
        if vehicle:
            logger.info(f"[AUTHENTICATED] Selecionando veiculo: {vehicle.plate} (ID: {vehicle.id})")
            session.selected_vehicle = vehicle
            session.state = "VEHICLE_SELECTED"
            self._show_vehicle_options(session)
            return
        else:
            logger.warning(f"[AUTHENTICATED] Veiculo nao encontrado para mensagem: '{message}'")
            whatsapp_client.send_message(
                session.phone_number,
                "Veiculo nao encontrado. Por favor, selecione um veiculo da lista."
            )
            # Mostra a lista novamente mas NÃO muda o estado
            # Isso evita loop infinito
            self._show_vehicles(session)
            return
          
    def _show_vehicles(self, session: Session) -> None:
        """
        Mostra a lista de veículos disponíveis
        """
        user = session.user
        greeting = f"Olá, {user.name}!\n\n" if not session.user.intrudution_shown else ""
    
        logger.info(f"[SHOW_VEHICLES] Usuario {user.name} tem {len(session.user.vehicles)} veiculo(s)")
    
        if len(session.user.vehicles) == 0:  
            session.user.intrudution_shown = True        
            whatsapp_client.send_message(
                session.phone_number,
                f"{greeting}"
                f"Você não possui veículos cadastrados no sistema de Rastreamento."
            )
            return

        elif len(session.user.vehicles) == 1:
            # Se tem apenas 1 veículo, seleciona automaticamente
            logger.info(f"[SHOW_VEHICLES] Apenas 1 veiculo, selecionando automaticamente")
            session.selected_vehicle = session.user.vehicles[0]
            session.state = "VEHICLE_SELECTED"
            self._show_vehicle_options(session)
            return
        else:
            # Se tem múltiplos veículos, mostra a lista
            sections = [{
                "title": "Seus Veiculos",
                "rows": [
                    {
                        "id": v.id,  # ID do veículo
                        "title": v.plate,
                        "description": v.model
                    } for v in session.user.vehicles
                ]
            }]
            
            logger.info(f"[SHOW_VEHICLES] Mostrando lista de {len(session.user.vehicles)} veiculos")
            
            session.user.intrudution_shown = True
            session.state = "AUTHENTICATED"  # Define estado como AUTHENTICATED
            session.selected_vehicle = None  # IMPORTANTE: Limpa seleção anterior
            
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
        """
        Mostra as opções disponíveis para o veículo selecionado
        """
        vehicle = session.selected_vehicle
        user = session.user
        
        if not vehicle:
            logger.error("[SHOW_OPTIONS] Nenhum veiculo selecionado!")
            self._show_vehicles(session)
            return
        
        logger.info(f"[SHOW_OPTIONS] Mostrando opcoes para veiculo: {vehicle.plate} (ID: {vehicle.id})")
        
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
                {"id": "sair" if len(session.user.vehicles) == 1 else "menu", 
                "title": "Sair" if len(session.user.vehicles) == 1 else "Menu"}
            ]
        )
    
    def _handle_vehicle_action(self, session: Session, message: str, message_type: str = "text") -> None:
        """
        Trata as ações do veículo quando está no estado VEHICLE_SELECTED
        """
        msg_lower = message.lower().strip()
        vehicle = session.selected_vehicle
        
        if not vehicle:
            logger.error("[VEHICLE_ACTION] Nenhum veiculo selecionado no estado VEHICLE_SELECTED!")
            self._show_vehicles(session)
            return
        
        logger.info(f"[VEHICLE_ACTION] Acao '{msg_lower}' para veiculo: {vehicle.plate}")

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
            logger.info(f"[VEHICLE_ACTION] Buscando localizacao do veiculo {vehicle.plate}")
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
            logger.info(f"[VEHICLE_ACTION] Bloqueando veiculo {vehicle.plate}")
            success, msg = business_service.block_vehicle(vehicle, session)
            whatsapp_client.send_interactive_buttons(
                    session.phone_number,
                    f"{msg}\n\n"
                    "Escolha uma opcao:",
                    buttons
                )
        
        elif msg_lower in ["desbloquear", "unblock", "u"]:
            logger.info(f"[VEHICLE_ACTION] Desbloqueando veiculo {vehicle.plate}")
            success, msg = business_service.unblock_vehicle(vehicle, session)
            whatsapp_client.send_interactive_buttons(
                    session.phone_number,
                    f"{msg}\n\n"
                    "Escolha uma opcao:",
                    buttons
                )
        
        elif msg_lower in ["voltar", "back"]:
            logger.info(f"[VEHICLE_ACTION] Voltando para opcoes do veiculo")
            self._show_vehicle_options(session)
        
        elif msg_lower in ["menu"]:
            logger.info(f"[VEHICLE_ACTION] Voltando para o menu principal")
            # IMPORTANTE: Limpa a seleção e volta para AUTHENTICATED
            session.selected_vehicle = None
            session.state = "AUTHENTICATED"
            self._show_vehicles(session)

        else:
            # Comando não reconhecido - mostra as opções novamente
            logger.warning(f"[VEHICLE_ACTION] Comando nao reconhecido: '{message}'")
            self._show_vehicle_options(session)
    
    def _handle_logout(self, session: Session) -> None:
        phone = session.phone_number
        logger.info(f"[LOGOUT] Usuario {phone} saindo do sistema")
        session_manager.end_session(phone)
        whatsapp_client.send_message(
            phone,
            "Sessao encerrada com sucesso!\n\n"
            "Muito obrigado por usar o nosso serviços.\n"
        )
    
    def _handle_unknown(self, session: Session, message: str, message_type: str = "text") -> None:
        logger.warning(f"[UNKNOWN] Estado desconhecido: {session.state}")
        whatsapp_client.send_message(
            session.phone_number,
            "Nao entendi sua mensagem.\n"
            "Digite *menu* para ver as opcoes."
        )

    def remover_caracteres_esquerda(self, numero_str, quantidade=2):
        """
        Remove N caracteres da esquerda de uma string
        
        Args:
            numero_str: String a ser processada
            quantidade: Número de caracteres a remover (padrão: 2)
        """
        return numero_str[quantidade:]
    
    def get_vehicle_by_id(self, session: Session, vehicle_id: str) -> Vehicle | None:
        """
        Busca um veículo pelo ID (usado quando vem de lista interativa)
        """
        vehicle_id_clean = str(vehicle_id).strip()
        logger.debug(f"[GET_BY_ID] Buscando veiculo com ID: '{vehicle_id_clean}'")
        
        for vehicle in session.user.vehicles:
            vehicle_id_str = str(vehicle.id).strip()
            logger.debug(f"[GET_BY_ID] Comparando '{vehicle_id_clean}' com '{vehicle_id_str}'")
            
            if vehicle_id_str == vehicle_id_clean:
                logger.info(f"[GET_BY_ID] Veiculo encontrado: {vehicle.plate}")
                return vehicle
        
        logger.warning(f"[GET_BY_ID] Nenhum veiculo encontrado com ID: '{vehicle_id_clean}'")
        return None
    
    def get_vehicle_by_plate(self, session: Session, plate: str) -> Vehicle | None:
        """
        Busca um veículo pela placa ou modelo (usado para input de texto)
        """
        plate_clean = plate.lower().strip()
        logger.debug(f"[GET_BY_PLATE] Buscando veiculo com placa/modelo: '{plate_clean}'")
        
        for vehicle in session.user.vehicles:
            vehicle_plate = vehicle.plate.lower().strip()
            vehicle_model = vehicle.model.lower().strip()
            
            if vehicle_plate == plate_clean or vehicle_model == plate_clean:
                logger.info(f"[GET_BY_PLATE] Veiculo encontrado: {vehicle.plate}")
                return vehicle
        
        logger.warning(f"[GET_BY_PLATE] Nenhum veiculo encontrado com placa/modelo: '{plate_clean}'")
        return None