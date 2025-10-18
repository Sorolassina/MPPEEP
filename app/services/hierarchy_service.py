"""
Service de gestion de la hiérarchie organisationnelle
Détermine les validateurs (N+1, N+2, RH, DAF) pour chaque agent
"""
from typing import Optional, Dict, List
from sqlmodel import Session, select
from app.models.personnel import AgentComplet, Service, Direction
from app.models.rh import HRRequest, WorkflowStep
from app.core.enums import RequestType, WorkflowState


class HierarchyService:
    """Service pour déterminer la hiérarchie et les circuits de validation"""
    
    # Types de demandes qui DOIVENT passer par le RH
    RH_REQUIRED_TYPES = [
        RequestType.CONGE,
        RequestType.FORMATION,
        RequestType.BESOIN_ACTE,
    ]
    
    # Types de demandes qui s'arrêtent au Sous-directeur
    SHORT_CIRCUIT_TYPES = [
        RequestType.PERMISSION,
    ]
    
    @staticmethod
    def get_hierarchy(session: Session, agent_id: int) -> Dict[str, Optional[AgentComplet]]:
        """
        Détermine la hiérarchie complète d'un agent
        
        Returns:
            {
                'agent': AgentComplet,
                'position': str,  # "Agent", "Chef de service", "Sous-directeur", "DAF"
                'n_plus_1': AgentComplet | None,
                'n_plus_2': AgentComplet | None,
                'rh': AgentComplet | None,
                'daf': AgentComplet | None,
            }
        """
        agent = session.get(AgentComplet, agent_id)
        if not agent:
            return {}
        
        hierarchy = {
            'agent': agent,
            'position': 'Agent',  # Par défaut
            'n_plus_1': None,
            'n_plus_2': None,
            'rh': None,
            'daf': None,
        }
        
        # Déterminer la position de l'agent
        fonction = (agent.fonction or "").lower()
        
        # ═══════════════════════════════════════════════════════════
        # CAS 1 : Agent simple
        # ═══════════════════════════════════════════════════════════
        if ("agent" in fonction or not fonction) and "chef" not in fonction and "directeur" not in fonction and "daf" not in fonction:
            hierarchy['position'] = "Agent"
            
            # N+1 = Chef de service
            if agent.service_id:
                service = session.get(Service, agent.service_id)
                if service and service.chef_service_id:
                    hierarchy['n_plus_1'] = session.get(AgentComplet, service.chef_service_id)
            
            # N+2 = Sous-directeur (directeur de la direction)
            if agent.direction_id:
                direction = session.get(Direction, agent.direction_id)
                if direction and direction.directeur_id:
                    hierarchy['n_plus_2'] = session.get(AgentComplet, direction.directeur_id)
        
        # ═══════════════════════════════════════════════════════════
        # CAS 2 : Chef de service
        # ═══════════════════════════════════════════════════════════
        elif "chef" in fonction and "service" in fonction:
            hierarchy['position'] = "Chef de service"
            
            # N+1 = Sous-directeur
            if agent.direction_id:
                direction = session.get(Direction, agent.direction_id)
                if direction and direction.directeur_id:
                    hierarchy['n_plus_1'] = session.get(AgentComplet, direction.directeur_id)
            
            # N+2 = DAF
            hierarchy['n_plus_2'] = HierarchyService._get_daf(session)
        
        # ═══════════════════════════════════════════════════════════
        # CAS 3 : Sous-directeur
        # ═══════════════════════════════════════════════════════════
        elif "sous-directeur" in fonction or ("directeur" in fonction and "sous" in fonction):
            hierarchy['position'] = "Sous-directeur"
            
            # N+1 = DAF
            hierarchy['n_plus_1'] = HierarchyService._get_daf(session)
            hierarchy['n_plus_2'] = None  # Pas de N+2 pour un sous-directeur
        
        # ═══════════════════════════════════════════════════════════
        # CAS 4 : DAF
        # ═══════════════════════════════════════════════════════════
        elif "daf" in fonction:
            hierarchy['position'] = "DAF"
            hierarchy['n_plus_1'] = None  # Le DAF n'a pas de N+1 dans ce système
            hierarchy['n_plus_2'] = None
        
        # ═══════════════════════════════════════════════════════════
        # RH : Sous-directeur RH (si différent de l'agent)
        # ═══════════════════════════════════════════════════════════
        rh_agent = HierarchyService._get_rh(session)
        if rh_agent and rh_agent.id != agent_id:
            hierarchy['rh'] = rh_agent
        
        # ═══════════════════════════════════════════════════════════
        # DAF : Toujours le même
        # ═══════════════════════════════════════════════════════════
        hierarchy['daf'] = HierarchyService._get_daf(session)
        
        return hierarchy
    
    @staticmethod
    def _get_daf(session: Session) -> Optional[AgentComplet]:
        """Récupère le DAF (Direction Administrative et Financière)"""
        daf = session.exec(
            select(AgentComplet)
            .where(AgentComplet.fonction.ilike("%DAF%"))
            .where(AgentComplet.actif == True)
        ).first()
        return daf
    
    @staticmethod
    def _get_rh(session: Session) -> Optional[AgentComplet]:
        """Récupère le Sous-directeur RH"""
        # Chercher la direction RH
        rh_direction = session.exec(
            select(Direction)
            .where(Direction.code.ilike("%RH%"))
            .where(Direction.actif == True)
        ).first()
        
        if rh_direction and rh_direction.directeur_id:
            return session.get(AgentComplet, rh_direction.directeur_id)
        
        return None
    
    @staticmethod
    def get_workflow_circuit(
        session: Session, 
        agent_id: int, 
        request_type: RequestType
    ) -> List[WorkflowState]:
        """
        Détermine le circuit de validation pour un agent et un type de demande
        
        Returns:
            Liste des états dans l'ordre: [DRAFT, SUBMITTED, VALIDATION_N1, ...]
        """
        hierarchy = HierarchyService.get_hierarchy(session, agent_id)
        position = hierarchy.get('position', 'Agent')
        
        circuit = [WorkflowState.DRAFT, WorkflowState.SUBMITTED]
        
        # ═══════════════════════════════════════════════════════════
        # Circuit selon la position de l'agent
        # ═══════════════════════════════════════════════════════════
        
        if position == "DAF":
            # Le DAF n'a pas de circuit de validation (auto-validation)
            circuit.append(WorkflowState.ARCHIVED)
            return circuit
        
        if position == "Sous-directeur":
            # Sous-directeur → DAF direct (ou RH selon type)
            if request_type in HierarchyService.RH_REQUIRED_TYPES and hierarchy.get('rh'):
                circuit.append(WorkflowState.VALIDATION_RH)
            circuit.append(WorkflowState.SIGNATURE_DAF)
            circuit.append(WorkflowState.ARCHIVED)
            return circuit
        
        # Pour Agent et Chef de service
        if hierarchy.get('n_plus_1'):
            circuit.append(WorkflowState.VALIDATION_N1)
        
        if hierarchy.get('n_plus_2'):
            circuit.append(WorkflowState.VALIDATION_N2)
        
        # ═══════════════════════════════════════════════════════════
        # Ajout de RH et DAF selon le type
        # ═══════════════════════════════════════════════════════════
        
        if request_type in HierarchyService.SHORT_CIRCUIT_TYPES:
            # PERMISSION : s'arrête au Sous-directeur (N+2)
            circuit.append(WorkflowState.ARCHIVED)
        
        elif request_type in HierarchyService.RH_REQUIRED_TYPES:
            # Types RH : passe par RH puis DAF
            if hierarchy.get('rh'):
                circuit.append(WorkflowState.VALIDATION_RH)
            if hierarchy.get('daf'):
                circuit.append(WorkflowState.SIGNATURE_DAF)
            circuit.append(WorkflowState.ARCHIVED)
        
        else:
            # Autres types : DAF direct (pas de RH)
            if hierarchy.get('daf'):
                circuit.append(WorkflowState.SIGNATURE_DAF)
            circuit.append(WorkflowState.ARCHIVED)
        
        return circuit
    
    @staticmethod
    def get_expected_validator(
        session: Session, 
        request_id: int, 
        to_state: WorkflowState
    ) -> Optional[AgentComplet]:
        """
        Détermine quel agent DOIT valider une demande pour passer à un état donné
        
        Returns:
            L'agent qui doit valider, ou None si pas de validateur spécifique
        """
        request = session.get(HRRequest, request_id)
        if not request:
            return None
        
        hierarchy = HierarchyService.get_hierarchy(session, request.agent_id)
        
        # Mapping état → validateur
        if to_state == WorkflowState.SUBMITTED:
            # L'agent lui-même soumet
            return hierarchy.get('agent')
        
        elif to_state == WorkflowState.VALIDATION_N1:
            # Le N+1 valide
            return hierarchy.get('n_plus_1')
        
        elif to_state == WorkflowState.VALIDATION_N2:
            # Le N+2 valide
            return hierarchy.get('n_plus_2')
        
        elif to_state == WorkflowState.VALIDATION_RH:
            # Le RH valide
            return hierarchy.get('rh')
        
        elif to_state == WorkflowState.SIGNATURE_DAF:
            # Le DAF signe
            return hierarchy.get('daf')
        
        elif to_state == WorkflowState.ARCHIVED:
            # Archivage automatique (ou par le dernier validateur)
            return None
        
        return None
    
    @staticmethod
    def can_user_validate(
        session: Session, 
        user_id: int, 
        request_id: int, 
        to_state: WorkflowState
    ) -> bool:
        """
        Vérifie si un utilisateur peut valider une demande pour passer à un état donné
        
        Args:
            user_id: ID de l'utilisateur qui tente la validation
            request_id: ID de la demande
            to_state: État cible
        
        Returns:
            True si l'utilisateur peut valider, False sinon
        """
        # Récupérer l'agent lié à l'utilisateur
        user_agent = session.exec(
            select(AgentComplet)
            .where(AgentComplet.user_id == user_id)
            .where(AgentComplet.actif == True)
        ).first()
        
        if not user_agent:
            return False
        
        # Récupérer le validateur attendu
        expected_validator = HierarchyService.get_expected_validator(
            session, request_id, to_state
        )
        
        if not expected_validator:
            # Pas de validateur spécifique requis (ex: archivage automatique)
            return True
        
        # Vérifier que l'agent de l'utilisateur est le validateur attendu
        return user_agent.id == expected_validator.id
    
    @staticmethod
    def get_pending_requests_for_user(
        session: Session, 
        user_id: int
    ) -> List[HRRequest]:
        """
        Récupère les demandes en attente de validation par un utilisateur
        
        Returns:
            Liste des demandes que l'utilisateur doit valider
        """
        # Récupérer l'agent lié à l'utilisateur
        user_agent = session.exec(
            select(AgentComplet)
            .where(AgentComplet.user_id == user_id)
            .where(AgentComplet.actif == True)
        ).first()
        
        if not user_agent:
            return []
        
        # Récupérer toutes les demandes non archivées
        all_requests = session.exec(
            select(HRRequest)
            .where(HRRequest.current_state != WorkflowState.ARCHIVED)
            .where(HRRequest.current_state != WorkflowState.REJECTED)
        ).all()
        
        pending_requests = []
        
        for request in all_requests:
            # Déterminer le prochain état possible
            circuit = HierarchyService.get_workflow_circuit(
                session, request.agent_id, request.type
            )
            
            # Trouver l'état actuel dans le circuit
            try:
                current_index = circuit.index(request.current_state)
                if current_index < len(circuit) - 1:
                    next_state = circuit[current_index + 1]
                    
                    # Vérifier si l'utilisateur peut valider cette transition
                    expected_validator = HierarchyService.get_expected_validator(
                        session, request.id, next_state
                    )
                    
                    if expected_validator and expected_validator.id == user_agent.id:
                        pending_requests.append(request)
            except ValueError:
                # État actuel pas dans le circuit (ne devrait pas arriver)
                continue
        
        return pending_requests
    
    @staticmethod
    def get_user_hierarchy_info(session: Session, user_id: int) -> Dict:
        """
        Récupère les informations hiérarchiques d'un utilisateur
        Utile pour afficher son rôle et ses subordonnés
        
        Returns:
            {
                'agent': AgentComplet,
                'position': str,
                'subordinates': List[AgentComplet],  # Pour chefs et sous-directeurs
                'is_rh': bool,
                'is_daf': bool,
            }
        """
        user_agent = session.exec(
            select(AgentComplet)
            .where(AgentComplet.user_id == user_id)
            .where(AgentComplet.actif == True)
        ).first()
        
        if not user_agent:
            return {}
        
        hierarchy = HierarchyService.get_hierarchy(session, user_agent.id)
        
        info = {
            'agent': user_agent,
            'position': hierarchy.get('position', 'Agent'),
            'subordinates': [],
            'is_rh': False,
            'is_daf': False,
        }
        
        # Déterminer si l'utilisateur est RH ou DAF
        rh = HierarchyService._get_rh(session)
        daf = HierarchyService._get_daf(session)
        
        if rh and user_agent.id == rh.id:
            info['is_rh'] = True
        
        if daf and user_agent.id == daf.id:
            info['is_daf'] = True
        
        # Récupérer les subordonnés selon la position
        if info['position'] == "Chef de service" and user_agent.service_id:
            # Tous les agents du service (sauf lui-même)
            info['subordinates'] = session.exec(
                select(AgentComplet)
                .where(AgentComplet.service_id == user_agent.service_id)
                .where(AgentComplet.id != user_agent.id)
                .where(AgentComplet.actif == True)
            ).all()
        
        elif info['position'] == "Sous-directeur" and user_agent.direction_id:
            # Tous les agents de la direction (sauf lui-même)
            info['subordinates'] = session.exec(
                select(AgentComplet)
                .where(AgentComplet.direction_id == user_agent.direction_id)
                .where(AgentComplet.id != user_agent.id)
                .where(AgentComplet.actif == True)
            ).all()
        
        elif info['is_daf']:
            # Le DAF voit tout le monde
            info['subordinates'] = session.exec(
                select(AgentComplet)
                .where(AgentComplet.id != user_agent.id)
                .where(AgentComplet.actif == True)
            ).all()
        
        return info

