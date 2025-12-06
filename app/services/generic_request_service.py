"""
Service générique pour la gestion des demandes dans tous les modules
Utilise le système de workflow personnalisé
"""

import json
from typing import Any

from sqlmodel import Session, select

from app.core.enums import WorkflowState
from app.models.generic_request import GenericRequest, GenericWorkflowHistory
from app.models.personnel import AgentComplet
from app.models.workflow_config import CustomRole, CustomRoleAssignment, RequestTypeCustom, WorkflowTemplateStep
from app.services.hierarchy_service import HierarchyService


class GenericRequestService:
    """Service pour gérer les demandes génériques dans tous les modules"""

    @staticmethod
    def get_workflow_circuit(session: Session, request_id: int) -> list[WorkflowState]:
        """
        Récupère le circuit de validation complet pour une demande générique
        Basé sur le template configuré pour le type de demande

        Args:
            request_id: ID de la demande générique

        Returns:
            Liste des états dans l'ordre: [DRAFT, SUBMITTED, VALIDATION_N1, ...]
        """
        request = session.get(GenericRequest, request_id)
        if not request:
            return [WorkflowState.DRAFT, WorkflowState.ARCHIVED]

        # 1. Récupérer le template du type de demande
        request_type_custom = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.code == request.type).where(RequestTypeCustom.actif)
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
    def get_expected_validator(session: Session, request_id: int, to_state: WorkflowState) -> AgentComplet | None:
        """
        Détermine quel agent DOIT valider une demande pour passer à un état donné
        Basé uniquement sur les rôles personnalisés configurés dans le template
        """
        request = session.get(GenericRequest, request_id)
        if not request:
            return None

        # Cas spécial : SUBMITTED → c'est le demandeur
        if to_state == WorkflowState.SUBMITTED:
            return session.get(AgentComplet, request.demandeur_id)

        # Cas spécial : ARCHIVED → pas de validateur
        if to_state == WorkflowState.ARCHIVED:
            return None

        # Récupérer le template du type de demande
        request_type_custom = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.code == request.type).where(RequestTypeCustom.actif)
        ).first()

        if not request_type_custom:
            return None

        # Récupérer les étapes du template
        steps = session.exec(
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.template_id == request_type_custom.workflow_template_id)
            .order_by(WorkflowTemplateStep.order_index)
        ).all()

        # Mapper l'état cible à l'index de l'étape
        state_to_index = {
            WorkflowState.VALIDATION_N1: 0,
            WorkflowState.VALIDATION_N2: 1,
            WorkflowState.VALIDATION_N3: 2,
            WorkflowState.VALIDATION_N4: 3,
            WorkflowState.VALIDATION_N5: 4,
            WorkflowState.VALIDATION_N6: 5,
        }

        step_index = state_to_index.get(to_state)
        if step_index is None or step_index >= len(steps):
            return None

        step = steps[step_index]

        # Si c'est un rôle personnalisé, récupérer l'agent assigné
        if step.role_type.value == "CUSTOM" and step.custom_role_name:
            custom_role = session.exec(
                select(CustomRole).where(CustomRole.libelle == step.custom_role_name).where(CustomRole.actif)
            ).first()

            if custom_role:
                # Récupérer l'assignation active pour cet agent
                assignment = session.exec(
                    select(CustomRoleAssignment)
                    .where(CustomRoleAssignment.custom_role_id == custom_role.id)
                    .where(CustomRoleAssignment.actif)
                    .where(CustomRoleAssignment.agent_id == request.demandeur_id)
                ).first()

                if assignment:
                    return session.get(AgentComplet, assignment.agent_id)

        return None

    @staticmethod
    def get_workflow_info(session: Session, request_id: int) -> dict[str, Any]:
        """
        Récupère les informations détaillées du workflow pour une demande
        """
        request = session.get(GenericRequest, request_id)
        if not request:
            return {}

        circuit = GenericRequestService.get_workflow_circuit(session, request_id)

        # Récupérer le template du type de demande
        request_type_custom = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.code == request.type).where(RequestTypeCustom.actif)
        ).first()

        if not request_type_custom:
            return {
                "template_name": "Circuit minimal",
                "steps": {},
            }

        # Récupérer les étapes du template
        steps = session.exec(
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.template_id == request_type_custom.workflow_template_id)
            .order_by(WorkflowTemplateStep.order_index)
        ).all()

        # Construire le mapping état → info étape
        state_to_index = {
            WorkflowState.VALIDATION_N1: 0,
            WorkflowState.VALIDATION_N2: 1,
            WorkflowState.VALIDATION_N3: 2,
            WorkflowState.VALIDATION_N4: 3,
            WorkflowState.VALIDATION_N5: 4,
            WorkflowState.VALIDATION_N6: 5,
        }

        steps_info = {}
        for state, index in state_to_index.items():
            if index < len(steps):
                step = steps[index]
                role_name = step.custom_role_name if step.role_type.value == "CUSTOM" else step.role_type.value
                steps_info[state.value] = {
                    "role_name": role_name,
                    "obligatoire": step.obligatoire,
                    "peut_rejeter": step.peut_rejeter,
                }

        return {
            "template_name": request_type_custom.libelle,
            "steps": steps_info,
        }

    @staticmethod
    def get_pending_requests_for_user(session: Session, user_id: int, module: str | None = None) -> list[GenericRequest]:
        """
        Récupère les demandes en attente de validation par un utilisateur
        Basé sur les rôles personnalisés assignés à l'utilisateur

        Args:
            user_id: ID de l'utilisateur
            module: Module spécifique (optionnel). Si None, retourne toutes les demandes

        Returns:
            Liste des demandes en attente
        """
        from app.models.user import User

        user = session.get(User, user_id)
        if not user or not user.agent_id:
            return []

        # Récupérer les rôles personnalisés assignés à l'agent
        assignments = session.exec(
            select(CustomRoleAssignment)
            .where(CustomRoleAssignment.agent_id == user.agent_id)
            .where(CustomRoleAssignment.actif)
        ).all()

        if not assignments:
            return []

        # Récupérer les codes des rôles
        role_names = [session.get(CustomRole, a.custom_role_id).libelle for a in assignments if session.get(CustomRole, a.custom_role_id)]

        # Récupérer toutes les demandes en attente
        query = select(GenericRequest).where(GenericRequest.current_state != WorkflowState.DRAFT).where(
            GenericRequest.current_state != WorkflowState.ARCHIVED
        )

        if module:
            query = query.where(GenericRequest.module == module)

        all_requests = session.exec(query).all()

        # Filtrer selon les rôles
        pending = []
        for req in all_requests:
            circuit = GenericRequestService.get_workflow_circuit(session, req.id)
            try:
                current_index = circuit.index(req.current_state)
                if current_index < len(circuit) - 1:
                    next_state = circuit[current_index + 1]
                    validator = GenericRequestService.get_expected_validator(session, req.id, next_state)
                    if validator and validator.id == user.agent_id:
                        pending.append(req)
            except ValueError:
                continue

        return pending

    @staticmethod
    def next_states_for(session: Session, request_id: int) -> list[dict]:
        """
        Retourne les prochains états possibles pour une demande
        Basé sur le workflow personnalisé configuré
        """
        request = session.get(GenericRequest, request_id)
        if not request:
            return []

        # Récupérer le circuit complet
        circuit = GenericRequestService.get_workflow_circuit(session, request_id)

        try:
            current_index = circuit.index(request.current_state)
            if current_index < len(circuit) - 1:
                next_state = circuit[current_index + 1]

                # Retourner sous forme compatible
                return [{"to_state": next_state, "from_state": request.current_state, "type": request.type}]
        except ValueError:
            return []

        return []

    @staticmethod
    def transition(
        session: Session,
        request_id: int,
        to_state: WorkflowState,
        acted_by_user_id: int,
        acted_by_role: str,
        comment: str | None = None,
    ) -> GenericRequest:
        """
        Effectue une transition de workflow pour une demande générique
        """
        request = session.get(GenericRequest, request_id)
        if not request:
            raise ValueError("Demande introuvable")

        # Vérifier que la transition est valide
        circuit = GenericRequestService.get_workflow_circuit(session, request_id)
        try:
            current_index = circuit.index(request.current_state)
            if current_index >= len(circuit) - 1:
                raise ValueError("Aucune transition possible depuis cet état")
            if circuit[current_index + 1] != to_state:
                raise ValueError(f"Transition invalide : {request.current_state} → {to_state}")
        except ValueError as e:
            if "Aucune transition" in str(e) or "Transition invalide" in str(e):
                raise
            raise ValueError(f"État actuel non trouvé dans le circuit : {request.current_state}")

        # Enregistrer l'historique
        history = GenericWorkflowHistory(
            request_id=request_id,
            from_state=request.current_state,
            to_state=to_state,
            acted_by_user_id=acted_by_user_id,
            acted_by_role=acted_by_role,
            comment=comment,
        )
        session.add(history)

        # Mettre à jour la demande
        request.current_state = to_state

        # Déterminer le prochain rôle assigné
        if current_index + 1 < len(circuit) - 1:
            next_state = circuit[current_index + 2]
            validator = GenericRequestService.get_expected_validator(session, request_id, next_state)
            if validator:
                # Récupérer le nom du rôle depuis le template
                request_type_custom = session.exec(
                    select(RequestTypeCustom).where(RequestTypeCustom.code == request.type).where(RequestTypeCustom.actif)
                ).first()
                if request_type_custom:
                    steps = session.exec(
                        select(WorkflowTemplateStep)
                        .where(WorkflowTemplateStep.template_id == request_type_custom.workflow_template_id)
                        .order_by(WorkflowTemplateStep.order_index)
                    ).all()
                    state_to_index = {
                        WorkflowState.VALIDATION_N1: 0,
                        WorkflowState.VALIDATION_N2: 1,
                        WorkflowState.VALIDATION_N3: 2,
                        WorkflowState.VALIDATION_N4: 3,
                        WorkflowState.VALIDATION_N5: 4,
                        WorkflowState.VALIDATION_N6: 5,
                    }
                    step_index = state_to_index.get(next_state)
                    if step_index is not None and step_index < len(steps):
                        step = steps[step_index]
                        request.current_assignee_role = (
                            step.custom_role_name if step.role_type.value == "CUSTOM" else step.role_type.value
                        )
        else:
            request.current_assignee_role = None

        session.add(request)
        session.commit()
        session.refresh(request)

        return request

