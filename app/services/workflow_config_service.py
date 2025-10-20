"""
Service de gestion des workflows configurables
Permet de créer, modifier et gérer des circuits de validation personnalisés
"""

import json
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.models.personnel import AgentComplet
from app.models.workflow_config import (
    CustomRole,
    CustomRoleAssignment,
    RequestTypeCustom,
    WorkflowConfigHistory,
    WorkflowDirection,
    WorkflowRoleType,
    WorkflowTemplate,
    WorkflowTemplateStep,
)


class WorkflowConfigService:
    """Service pour la configuration des workflows"""

    # ═══════════════════════════════════════════════════════════
    # GESTION DES TEMPLATES DE WORKFLOW
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def create_template(
        session: Session,
        code: str,
        nom: str,
        description: str | None = None,
        direction: WorkflowDirection = WorkflowDirection.ASCENDANT,
        icone: str = "📄",
        couleur: str = "#3498db",
        user_id: int | None = None,
    ) -> WorkflowTemplate:
        """Crée un nouveau template de workflow"""

        # Vérifier que le code n'existe pas déjà
        existing = session.exec(select(WorkflowTemplate).where(WorkflowTemplate.code == code)).first()

        if existing:
            raise ValueError(f"Un template avec le code '{code}' existe déjà")

        template = WorkflowTemplate(
            code=code,
            nom=nom,
            description=description,
            direction=direction,
            icone=icone,
            couleur=couleur,
            created_by=user_id,
            updated_by=user_id,
        )

        session.add(template)
        session.commit()
        session.refresh(template)

        # Enregistrer dans l'historique
        WorkflowConfigService._log_change(session, "WorkflowTemplate", template.id, "CREATE", user_id)

        return template

    @staticmethod
    def add_step_to_template(
        session: Session,
        template_id: int,
        role_type: WorkflowRoleType,
        order_index: int,
        custom_role_name: str | None = None,
        obligatoire: bool = True,
        peut_rejeter: bool = True,
        delai_jours: int | None = None,
        user_id: int | None = None,
    ) -> WorkflowTemplateStep:
        """Ajoute une étape à un template"""

        template = session.get(WorkflowTemplate, template_id)
        if not template:
            raise ValueError("Template introuvable")

        step = WorkflowTemplateStep(
            template_id=template_id,
            order_index=order_index,
            role_type=role_type,
            custom_role_name=custom_role_name,
            obligatoire=obligatoire,
            peut_rejeter=peut_rejeter,
            delai_jours=delai_jours,
        )

        session.add(step)
        template.updated_at = datetime.utcnow()
        template.updated_by = user_id
        session.add(template)
        session.commit()
        session.refresh(step)

        # Enregistrer dans l'historique
        WorkflowConfigService._log_change(
            session,
            "WorkflowTemplateStep",
            step.id,
            "CREATE",
            user_id,
            changes={"template_id": template_id, "role_type": role_type.value},
        )

        return step

    @staticmethod
    def get_template_steps(session: Session, template_id: int) -> list[WorkflowTemplateStep]:
        """Récupère toutes les étapes d'un template, ordonnées"""
        return session.exec(
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.template_id == template_id)
            .order_by(WorkflowTemplateStep.order_index)
        ).all()

    @staticmethod
    def delete_template(session: Session, template_id: int, user_id: int | None = None):
        """Supprime un template (soft delete en désactivant)"""
        template = session.get(WorkflowTemplate, template_id)
        if not template:
            raise ValueError("Template introuvable")

        # Vérifier qu'aucun type de demande n'utilise ce template
        types_utilisant = session.exec(
            select(RequestTypeCustom)
            .where(RequestTypeCustom.workflow_template_id == template_id)
            .where(RequestTypeCustom.actif)
        ).all()

        if types_utilisant:
            raise ValueError(f"Ce template est utilisé par {len(types_utilisant)} type(s) de demande actif(s)")

        template.actif = False
        template.updated_at = datetime.utcnow()
        template.updated_by = user_id
        session.add(template)
        session.commit()

        WorkflowConfigService._log_change(session, "WorkflowTemplate", template_id, "DEACTIVATE", user_id)

    @staticmethod
    def delete_template_permanently(session: Session, template_id: int, user_id: int | None = None):
        """Supprime définitivement un template (hard delete)"""
        template = session.get(WorkflowTemplate, template_id)
        if not template:
            raise ValueError("Template introuvable")

        # Vérifier qu'aucun type de demande n'utilise ce template (actif OU inactif)
        types_utilisant = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.workflow_template_id == template_id)
        ).all()

        if types_utilisant:
            raise ValueError(
                f"Ce template est utilisé par {len(types_utilisant)} type(s) de demande. "
                f"Supprimez d'abord ces types ou désactivez-les."
            )

        # Enregistrer dans l'historique AVANT de supprimer
        WorkflowConfigService._log_change(session, "WorkflowTemplate", template_id, "DELETE", user_id)

        # Supprimer les étapes du template
        steps = session.exec(select(WorkflowTemplateStep).where(WorkflowTemplateStep.template_id == template_id)).all()

        for step in steps:
            session.delete(step)

        # Supprimer le template
        session.delete(template)
        session.commit()

    # ═══════════════════════════════════════════════════════════
    # GESTION DES TYPES DE DEMANDES
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def create_request_type(
        session: Session,
        code: str,
        libelle: str,
        workflow_template_id: int,
        description: str | None = None,
        categorie: str = "Autre",
        champs_formulaire: list[dict] | None = None,
        document_obligatoire: bool = False,
        necessite_validation_rh: bool = False,
        necessite_validation_daf: bool = False,
        user_id: int | None = None,
    ) -> RequestTypeCustom:
        """Crée un nouveau type de demande"""

        # Vérifier que le code n'existe pas
        existing = session.exec(select(RequestTypeCustom).where(RequestTypeCustom.code == code)).first()

        if existing:
            raise ValueError(f"Un type de demande avec le code '{code}' existe déjà")

        # Vérifier que le template existe
        template = session.get(WorkflowTemplate, workflow_template_id)
        if not template:
            raise ValueError("Template de workflow introuvable")

        # Sérialiser les champs du formulaire en JSON
        champs_json = json.dumps(champs_formulaire) if champs_formulaire else None

        request_type = RequestTypeCustom(
            code=code,
            libelle=libelle,
            description=description,
            workflow_template_id=workflow_template_id,
            categorie=categorie,
            champs_formulaire=champs_json,
            document_obligatoire=document_obligatoire,
            necessite_validation_rh=necessite_validation_rh,
            necessite_validation_daf=necessite_validation_daf,
            created_by=user_id,
            updated_by=user_id,
        )

        session.add(request_type)
        session.commit()
        session.refresh(request_type)

        WorkflowConfigService._log_change(session, "RequestTypeCustom", request_type.id, "CREATE", user_id)

        return request_type

    @staticmethod
    def get_active_request_types(session: Session, categorie: str | None = None) -> list[RequestTypeCustom]:
        """Récupère tous les types de demandes actifs, optionnellement filtrés par catégorie"""
        query = select(RequestTypeCustom).where(RequestTypeCustom.actif)

        if categorie:
            query = query.where(RequestTypeCustom.categorie == categorie)

        return session.exec(query.order_by(RequestTypeCustom.ordre_affichage)).all()

    @staticmethod
    def get_request_type_by_code(session: Session, code: str) -> RequestTypeCustom | None:
        """Récupère un type de demande par son code"""
        return session.exec(select(RequestTypeCustom).where(RequestTypeCustom.code == code)).first()

    # ═══════════════════════════════════════════════════════════
    # GESTION DES RÔLES PERSONNALISÉS
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def create_custom_role(
        session: Session, code: str, libelle: str, description: str | None = None, user_id: int | None = None
    ) -> CustomRole:
        """Crée un rôle personnalisé"""

        existing = session.exec(select(CustomRole).where(CustomRole.code == code)).first()

        if existing:
            raise ValueError(f"Un rôle avec le code '{code}' existe déjà")

        role = CustomRole(code=code, libelle=libelle, description=description)

        session.add(role)
        session.commit()
        session.refresh(role)

        WorkflowConfigService._log_change(session, "CustomRole", role.id, "CREATE", user_id)

        return role

    @staticmethod
    def assign_role_to_agent(
        session: Session,
        custom_role_id: int,
        agent_id: int,
        date_fin: datetime | None = None,
        user_id: int | None = None,
    ) -> CustomRoleAssignment:
        """Attribue un rôle personnalisé à un agent"""

        # Vérifier que le rôle et l'agent existent
        role = session.get(CustomRole, custom_role_id)
        if not role:
            raise ValueError("Rôle introuvable")

        agent = session.get(AgentComplet, agent_id)
        if not agent:
            raise ValueError("Agent introuvable")

        # Vérifier qu'il n'y a pas déjà une attribution active
        existing = session.exec(
            select(CustomRoleAssignment)
            .where(CustomRoleAssignment.custom_role_id == custom_role_id)
            .where(CustomRoleAssignment.agent_id == agent_id)
            .where(CustomRoleAssignment.actif)
        ).first()

        if existing:
            raise ValueError("L'agent a déjà ce rôle (attribution active)")

        assignment = CustomRoleAssignment(
            custom_role_id=custom_role_id, agent_id=agent_id, date_fin=date_fin, created_by=user_id
        )

        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        WorkflowConfigService._log_change(
            session,
            "CustomRoleAssignment",
            assignment.id,
            "CREATE",
            user_id,
            changes={"role_id": custom_role_id, "agent_id": agent_id},
        )

        return assignment

    @staticmethod
    def get_agents_with_role(session: Session, custom_role_id: int) -> list[AgentComplet]:
        """Récupère tous les agents ayant un rôle personnalisé"""
        assignments = session.exec(
            select(CustomRoleAssignment)
            .where(CustomRoleAssignment.custom_role_id == custom_role_id)
            .where(CustomRoleAssignment.actif)
        ).all()

        agent_ids = [a.agent_id for a in assignments]

        if not agent_ids:
            return []

        return session.exec(select(AgentComplet).where(AgentComplet.id.in_(agent_ids)).where(AgentComplet.actif)).all()

    # ═══════════════════════════════════════════════════════════
    # INITIALISATION DES WORKFLOWS SYSTÈME
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def initialize_system_workflows(session: Session):
        """
        Crée les workflows système de base
        (CONGE, PERMISSION, FORMATION, BESOIN_ACTE)
        """

        # 1. Template pour circuits longs (avec RH)
        template_long = session.exec(select(WorkflowTemplate).where(WorkflowTemplate.code == "CIRCUIT_LONG_RH")).first()

        if not template_long:
            template_long = WorkflowTemplate(
                code="CIRCUIT_LONG_RH",
                nom="Circuit Long (avec RH)",
                description="Circuit complet : Agent → N+1 → N+2 → RH → DAF",
                direction=WorkflowDirection.ASCENDANT,
                icone="📋",
                couleur="#2ecc71",
                est_systeme=True,
            )
            session.add(template_long)
            session.commit()
            session.refresh(template_long)

            # Ajouter les étapes
            steps_long = [
                (1, WorkflowRoleType.N_PLUS_1),
                (2, WorkflowRoleType.N_PLUS_2),
                (3, WorkflowRoleType.RH),
                (4, WorkflowRoleType.DAF),
            ]

            for order, role in steps_long:
                step = WorkflowTemplateStep(
                    template_id=template_long.id, order_index=order, role_type=role, obligatoire=True
                )
                session.add(step)

            session.commit()

        # 2. Template pour circuits moyens (sans RH)
        template_moyen = session.exec(select(WorkflowTemplate).where(WorkflowTemplate.code == "CIRCUIT_MOYEN")).first()

        if not template_moyen:
            template_moyen = WorkflowTemplate(
                code="CIRCUIT_MOYEN",
                nom="Circuit Moyen (sans RH)",
                description="Circuit : Agent → N+1 → N+2",
                direction=WorkflowDirection.ASCENDANT,
                icone="📄",
                couleur="#3498db",
                est_systeme=True,
            )
            session.add(template_moyen)
            session.commit()
            session.refresh(template_moyen)

            # Ajouter les étapes
            steps_moyen = [
                (1, WorkflowRoleType.N_PLUS_1),
                (2, WorkflowRoleType.N_PLUS_2),
            ]

            for order, role in steps_moyen:
                step = WorkflowTemplateStep(
                    template_id=template_moyen.id, order_index=order, role_type=role, obligatoire=True
                )
                session.add(step)

            session.commit()

        # 3. Template pour tâches descendantes
        template_descendant = session.exec(
            select(WorkflowTemplate).where(WorkflowTemplate.code == "TACHE_DESCENDANTE")
        ).first()

        if not template_descendant:
            template_descendant = WorkflowTemplate(
                code="TACHE_DESCENDANTE",
                nom="Tâche Descendante",
                description="Tâche assignée par un supérieur qui se termine au demandeur",
                direction=WorkflowDirection.DESCENDANT,
                icone="⬇️",
                couleur="#e74c3c",
                est_systeme=True,
            )
            session.add(template_descendant)
            session.commit()
            session.refresh(template_descendant)

            # Ajouter l'étape (retour au demandeur)
            step = WorkflowTemplateStep(
                template_id=template_descendant.id,
                order_index=1,
                role_type=WorkflowRoleType.DEMANDEUR,
                obligatoire=True,
            )
            session.add(step)
            session.commit()

        return True  # Succès

    # ═══════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _log_change(
        session: Session,
        entity_type: str,
        entity_id: int,
        action: str,
        user_id: int | None = None,
        changes: dict[str, Any] | None = None,
    ):
        """Enregistre une modification dans l'historique"""
        history = WorkflowConfigHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by=user_id or 0,
            changes=json.dumps(changes) if changes else None,
        )
        session.add(history)
        session.commit()

    @staticmethod
    def get_workflow_preview(session: Session, template_id: int) -> dict:
        """
        Génère un aperçu visuel d'un workflow
        Retourne une structure pour affichage dans l'interface
        """
        template = session.get(WorkflowTemplate, template_id)
        if not template:
            return {}

        steps = WorkflowConfigService.get_template_steps(session, template_id)

        preview = {
            "template": {
                "nom": template.nom,
                "description": template.description,
                "direction": template.direction.value,
                "icone": template.icone,
                "couleur": template.couleur,
            },
            "circuit": [],
        }

        if template.direction == WorkflowDirection.ASCENDANT:
            preview["circuit"].append(
                {"etape": 0, "role": "DEMANDEUR", "libelle": "Demandeur (Agent)", "action": "Soumet la demande"}
            )

        for step in steps:
            preview["circuit"].append(
                {
                    "etape": step.order_index,
                    "role": step.role_type.value,
                    "libelle": step.custom_role_name or step.role_type.value,
                    "obligatoire": step.obligatoire,
                    "peut_rejeter": step.peut_rejeter,
                    "delai_jours": step.delai_jours,
                }
            )

        preview["circuit"].append(
            {"etape": len(steps) + 1, "role": "SYSTEME", "libelle": "Archivage", "action": "Demande archivée"}
        )

        return preview
