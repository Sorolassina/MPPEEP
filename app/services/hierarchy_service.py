"""
Service de gestion des workflows basés sur les rôles personnalisés
Nouvelle version : 100% personnalisable via la configuration
"""
from typing import Optional, Dict, List
from sqlmodel import Session, select
from app.models.personnel import AgentComplet
from app.models.rh import HRRequest
from app.core.enums import WorkflowState


class HierarchyService:
    """Service pour gérer les circuits de validation basés sur les rôles personnalisés"""
    
    @staticmethod
    def get_workflow_circuit(
        session: Session, 
        request_id: int
    ) -> List[WorkflowState]:
        """
        Récupère le circuit de validation complet pour une demande
        Basé sur le template configuré pour le type de demande
        
        Args:
            request_id: ID de la demande
        
        Returns:
            Liste des états dans l'ordre: [DRAFT, SUBMITTED, VALIDATION_N1, ...]
        """
        from app.models.workflow_config import RequestTypeCustom, WorkflowTemplateStep
        
        request = session.get(HRRequest, request_id)
        if not request:
            return [WorkflowState.DRAFT, WorkflowState.ARCHIVED]
        
        # 1. Récupérer le template du type de demande
        request_type_custom = session.exec(
            select(RequestTypeCustom)
            .where(RequestTypeCustom.code == request.type)
            .where(RequestTypeCustom.actif == True)
        ).first()
        
        if not request_type_custom:
            # Pas de template configuré → circuit minimal
            return [WorkflowState.DRAFT, WorkflowState.SUBMITTED, WorkflowState.ARCHIVED]
        
        # 2. Récupérer les étapes du template
        steps = session.exec(
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.template_id == request_type_custom.workflow_template_id)
            .order_by(WorkflowTemplateStep.order_index)
        ).all()
        
        # 3. Construire le circuit en utilisant les états disponibles
        circuit = [WorkflowState.DRAFT, WorkflowState.SUBMITTED]
        
        # Mapper les étapes aux états WorkflowState disponibles
        # Utilisation de N+1, N+2, N+3, N+4, N+5, N+6 (jusqu'à 6 niveaux)
        available_states = [
            WorkflowState.VALIDATION_N1,
            WorkflowState.VALIDATION_N2,
            WorkflowState.VALIDATION_N3,
            WorkflowState.VALIDATION_N4,
            WorkflowState.VALIDATION_N5,
            WorkflowState.VALIDATION_N6,
        ]
        
        # Ajouter autant d'états que d'étapes configurées (max 6)
        for i, step in enumerate(steps):
            if i < len(available_states):
                circuit.append(available_states[i])
        
        # Toujours ajouter "Archivé" à la fin
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
        Basé uniquement sur les rôles personnalisés configurés dans le template
        
        Args:
            request_id: ID de la demande
            to_state: État cible
        
        Returns:
            L'agent qui doit valider, ou None si pas de validateur
        """
        from app.models.workflow_config import RequestTypeCustom, WorkflowTemplateStep, CustomRole, CustomRoleAssignment
        
        request = session.get(HRRequest, request_id)
        if not request:
            return None
        
        # Cas spécial : SUBMITTED → c'est le demandeur
        if to_state == WorkflowState.SUBMITTED:
            return session.get(AgentComplet, request.agent_id)
        
        # Cas spécial : ARCHIVED → pas de validateur
        if to_state == WorkflowState.ARCHIVED:
            return None
        
        # 1. Récupérer le template du type de demande
        request_type_custom = session.exec(
            select(RequestTypeCustom)
            .where(RequestTypeCustom.code == request.type)
            .where(RequestTypeCustom.actif == True)
        ).first()
        
        if not request_type_custom:
            return None
        
        # 2. Récupérer les étapes du template
        steps = session.exec(
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.template_id == request_type_custom.workflow_template_id)
            .order_by(WorkflowTemplateStep.order_index)
        ).all()
        
        if not steps:
            return None
        
        # 3. Mapper l'état à un index d'étape
        step_index = HierarchyService._get_step_index_for_state(to_state)
        
        if step_index is None or step_index >= len(steps):
            return None
        
        step = steps[step_index]
        
        # 4. Récupérer l'agent ayant le rôle de cette étape
        custom_role = session.exec(
            select(CustomRole)
            .where(CustomRole.code == step.custom_role_name)
            .where(CustomRole.actif == True)
        ).first()
        
        if not custom_role:
            return None
        
        # 5. Trouver l'agent ayant ce rôle
        assignment = session.exec(
            select(CustomRoleAssignment)
            .where(CustomRoleAssignment.custom_role_id == custom_role.id)
            .where(CustomRoleAssignment.actif == True)
        ).first()
        
        if not assignment:
            return None
        
        return session.get(AgentComplet, assignment.agent_id)
    
    @staticmethod
    def _get_step_index_for_state(state: WorkflowState) -> Optional[int]:
        """
        Mappe un état de workflow à un index d'étape dans le template
        
        VALIDATION_N1 → Étape 1 (index 0)
        VALIDATION_N2 → Étape 2 (index 1)
        VALIDATION_N3 → Étape 3 (index 2)
        VALIDATION_N4 → Étape 4 (index 3)
        VALIDATION_N5 → Étape 5 (index 4)
        VALIDATION_N6 → Étape 6 (index 5)
        """
        state_to_index = {
            WorkflowState.VALIDATION_N1: 0,
            WorkflowState.VALIDATION_N2: 1,
            WorkflowState.VALIDATION_N3: 2,
            WorkflowState.VALIDATION_N4: 3,
            WorkflowState.VALIDATION_N5: 4,
            WorkflowState.VALIDATION_N6: 5,
        }
        return state_to_index.get(state)
    
    @staticmethod
    def can_user_validate(
        session: Session, 
        user_id: int, 
        request_id: int, 
        to_state: WorkflowState
    ) -> bool:
        """
        Vérifie si un utilisateur peut valider une demande pour passer à un état donné
        Compare l'utilisateur connecté avec l'agent ayant le rôle de l'étape
        
        Args:
            user_id: ID de l'utilisateur qui tente la validation
            request_id: ID de la demande
            to_state: État cible
        
        Returns:
            True si l'utilisateur peut valider, False sinon
        """
        # 1. Récupérer l'agent lié à l'utilisateur connecté
        user_agent = session.exec(
            select(AgentComplet)
            .where(AgentComplet.user_id == user_id)
            .where(AgentComplet.actif == True)
        ).first()
        
        if not user_agent:
            return False
        
        # 2. Récupérer le validateur attendu pour cette étape
        expected_validator = HierarchyService.get_expected_validator(
            session, request_id, to_state
        )
        
        if not expected_validator:
            # Pas de validateur spécifique (ex: archivage automatique)
            return True
        
        # 3. Vérifier que l'agent de l'utilisateur correspond au validateur attendu
        return user_agent.id == expected_validator.id
    
    @staticmethod
    def get_pending_requests_for_user(
        session: Session, 
        user_id: int
    ) -> List[HRRequest]:
        """
        Récupère les demandes en attente de validation par un utilisateur
        Basé sur les rôles personnalisés attribués à l'utilisateur
        
        Args:
            user_id: ID de l'utilisateur
        
        Returns:
            Liste des demandes que l'utilisateur doit valider
        """
        from app.models.workflow_config import CustomRoleAssignment, CustomRole
        
        # 1. Récupérer l'agent lié à l'utilisateur
        user_agent = session.exec(
            select(AgentComplet)
            .where(AgentComplet.user_id == user_id)
            .where(AgentComplet.actif == True)
        ).first()
        
        if not user_agent:
            return []
        
        # 2. Récupérer tous les rôles de l'utilisateur
        user_role_assignments = session.exec(
            select(CustomRoleAssignment)
            .where(CustomRoleAssignment.agent_id == user_agent.id)
            .where(CustomRoleAssignment.actif == True)
        ).all()
        
        user_role_codes = []
        for assignment in user_role_assignments:
            role = session.get(CustomRole, assignment.custom_role_id)
            if role and role.actif:
                user_role_codes.append(role.code)
        
        # 3. Récupérer toutes les demandes non terminées
        all_requests = session.exec(
            select(HRRequest)
            .where(HRRequest.current_state != WorkflowState.ARCHIVED)
            .where(HRRequest.current_state != WorkflowState.REJECTED)
            .where(HRRequest.current_state != WorkflowState.DRAFT)
        ).all()
        
        pending_requests = []
        
        # 4. Pour chaque demande, vérifier si l'utilisateur doit la valider
        for request in all_requests:
            # Déterminer le prochain état
            circuit = HierarchyService.get_workflow_circuit(session, request.id)
            
            try:
                current_index = circuit.index(request.current_state)
                if current_index < len(circuit) - 1:
                    next_state = circuit[current_index + 1]
                    
                    # Vérifier si l'utilisateur peut valider
                    if HierarchyService.can_user_validate(session, user_id, request.id, next_state):
                        pending_requests.append(request)
            except ValueError:
                continue
        
        return pending_requests
    
    @staticmethod
    def get_user_roles(session: Session, user_id: int) -> List[Dict]:
        """
        Récupère tous les rôles personnalisés d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
        
        Returns:
            Liste des rôles avec leurs informations
        """
        from app.models.workflow_config import CustomRoleAssignment, CustomRole
        
        user_agent = session.exec(
            select(AgentComplet)
            .where(AgentComplet.user_id == user_id)
            .where(AgentComplet.actif == True)
        ).first()
        
        if not user_agent:
            return []
        
        assignments = session.exec(
            select(CustomRoleAssignment)
            .where(CustomRoleAssignment.agent_id == user_agent.id)
            .where(CustomRoleAssignment.actif == True)
        ).all()
        
        roles_info = []
        for assignment in assignments:
            role = session.get(CustomRole, assignment.custom_role_id)
            if role and role.actif:
                roles_info.append({
                    'code': role.code,
                    'libelle': role.libelle,
                    'description': role.description,
                    'date_debut': assignment.date_debut,
                    'date_fin': assignment.date_fin
                })
        
        return roles_info
    
    @staticmethod
    def get_agents_with_role(session: Session, role_code: str) -> List[AgentComplet]:
        """
        Récupère tous les agents ayant un rôle personnalisé spécifique
        
        Args:
            role_code: Code du rôle (ex: 'RESP_BUDGET')
        
        Returns:
            Liste des agents ayant ce rôle
        """
        from app.models.workflow_config import CustomRole, CustomRoleAssignment
        
        custom_role = session.exec(
            select(CustomRole)
            .where(CustomRole.code == role_code)
            .where(CustomRole.actif == True)
        ).first()
        
        if not custom_role:
            return []
        
        assignments = session.exec(
            select(CustomRoleAssignment)
            .where(CustomRoleAssignment.custom_role_id == custom_role.id)
            .where(CustomRoleAssignment.actif == True)
            ).all()
        
        agents = []
        for assignment in assignments:
            agent = session.get(AgentComplet, assignment.agent_id)
            if agent and agent.actif:
                agents.append(agent)
        
        return agents
    
    @staticmethod
    def get_next_validator_name(session: Session, request_id: int) -> Optional[str]:
        """
        Récupère le nom du prochain validateur pour une demande
        
        Args:
            request_id: ID de la demande
        
        Returns:
            Nom complet du prochain validateur ou None
        """
        request = session.get(HRRequest, request_id)
        if not request:
            return None
        
        # Récupérer le circuit
        circuit = HierarchyService.get_workflow_circuit(session, request_id)
        
        try:
            current_index = circuit.index(request.current_state)
            if current_index < len(circuit) - 1:
                next_state = circuit[current_index + 1]
                
                validator = HierarchyService.get_expected_validator(
                    session, request_id, next_state
                )
                
                if validator:
                    return f"{validator.prenom} {validator.nom}"
        except ValueError:
            pass
        
        return None
    
    @staticmethod
    def get_workflow_info(session: Session, request_id: int) -> Dict:
        """
        Récupère toutes les informations du workflow d'une demande
        
        Args:
            request_id: ID de la demande
        
        Returns:
            Dictionnaire avec circuit, étapes, validateurs, etc.
        """
        from app.models.workflow_config import RequestTypeCustom, WorkflowTemplateStep, WorkflowTemplate
        
        request = session.get(HRRequest, request_id)
        if not request:
            return {}
        
        # Récupérer le template
        request_type_custom = session.exec(
            select(RequestTypeCustom)
            .where(RequestTypeCustom.code == request.type)
            .where(RequestTypeCustom.actif == True)
        ).first()
        
        if not request_type_custom:
            return {
                'circuit': [],
                'current_step': None,
                'next_validator': None,
                'template': None
            }
        
        template = session.get(WorkflowTemplate, request_type_custom.workflow_template_id)
        
        steps = session.exec(
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.template_id == request_type_custom.workflow_template_id)
            .order_by(WorkflowTemplateStep.order_index)
            ).all()
        
        # Mapper les états aux étapes
        # Les états disponibles dans l'ordre (jusqu'à 6 niveaux)
        available_states = [
            WorkflowState.VALIDATION_N1,
            WorkflowState.VALIDATION_N2,
            WorkflowState.VALIDATION_N3,
            WorkflowState.VALIDATION_N4,
            WorkflowState.VALIDATION_N5,
            WorkflowState.VALIDATION_N6,
        ]
        
        # Construire un dictionnaire : état → info de l'étape
        steps_dict = {}
        for i, step in enumerate(steps):
            if i < len(available_states):
                state = available_states[i]
                
                # Récupérer le validateur assigné
                validator = None
                if step.custom_role_name:
                    agents = HierarchyService.get_agents_with_role(session, step.custom_role_name)
                    if agents:
                        validator = agents[0]
                
                steps_dict[state.value] = {
                    'role_name': step.custom_role_name or 'Non défini',
                    'validator_name': f"{validator.prenom} {validator.nom}" if validator else None,
                    'order_index': step.order_index
                }
        
        return {
            'template_name': template.nom if template else None,
            'circuit': HierarchyService.get_workflow_circuit(session, request_id),
            'steps': steps_dict,
            'current_state': request.current_state
        }

