# app/services/rh.py
"""
Service de gestion RH
Contient toute la logique métier liée aux ressources humaines
"""

from typing import Any

from sqlmodel import Session, col, func, select

from app.core.enums import WorkflowState
from app.core.logging_config import get_logger
from app.models.rh import HRRequest, WorkflowHistory, WorkflowStep

logger = get_logger(__name__)


class RHService:
    # --- KPIs & Stats ---
    @staticmethod
    def kpis(session: Session) -> dict[str, Any]:
        from app.models.personnel import AgentComplet

        total_agents = session.exec(select(func.count(AgentComplet.id))).one()
        actifs = session.exec(select(func.count(AgentComplet.id)).where(AgentComplet.actif)).one()

        # === STATISTIQUES DEMANDES ===

        # Total de demandes
        total_demandes = session.exec(select(func.count(HRRequest.id))).one()

        # Demandes en cours (non archivées, non rejetées)
        demandes_en_cours = session.exec(
            select(func.count(HRRequest.id)).where(
                HRRequest.current_state.not_in([WorkflowState.ARCHIVED, WorkflowState.REJECTED])
            )
        ).one()

        # Demandes archivées (terminées)
        demandes_archivees = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.current_state == WorkflowState.ARCHIVED)
        ).one()

        # Demandes en attente par état (dynamique)
        # Récupérer tous les états possibles et compter les demandes pour chacun
        demandes_par_etat = {}
        for state in WorkflowState:
            count = session.exec(select(func.count(HRRequest.id)).where(HRRequest.current_state == state)).one()
            if count > 0:  # Ne garder que les états avec des demandes
                demandes_par_etat[state.value] = count

        # Demandes par type (dynamique - depuis request_type_custom)
        from app.models.workflow_config import RequestTypeCustom

        demandes_par_type = {}
        request_types = session.exec(select(RequestTypeCustom).where(RequestTypeCustom.actif)).all()

        for rt in request_types:
            count = session.exec(select(func.count(HRRequest.id)).where(HRRequest.type == rt.code)).one()
            if count > 0:  # Ne garder que les types avec des demandes
                demandes_par_type[rt.code] = {"count": count, "libelle": rt.libelle, "icone": rt.icone}

        en_attente_n5 = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.current_state == WorkflowState.VALIDATION_N5)
        ).one()

        en_attente_n6 = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.current_state == WorkflowState.VALIDATION_N6)
        ).one()

        # Demandes par type (compatibilité avec anciens types)
        conges = session.exec(select(func.count(HRRequest.id)).where(HRRequest.type == "CONGE")).one()

        permissions = session.exec(select(func.count(HRRequest.id)).where(HRRequest.type == "PERMISSION")).one()

        formations = session.exec(select(func.count(HRRequest.id)).where(HRRequest.type == "FORMATION")).one()

        besoins_actes = session.exec(select(func.count(HRRequest.id)).where(HRRequest.type == "BESOIN_ACTE")).one()

        # Ajouter aussi les types personnalisés
        d_acte_rh = session.exec(select(func.count(HRRequest.id)).where(HRRequest.type == "D-ACTE RH")).one()

        # Satisfaction moyenne (sur besoins d'actes traités)
        sats = session.exec(
            select(func.avg(col(HRRequest.satisfaction_note))).where(
                HRRequest.satisfaction_note.is_not(None), HRRequest.current_state == WorkflowState.ARCHIVED
            )
        ).one()
        satisfaction = round(float(sats), 2) if sats is not None else None

        # Taux de traitement (archivées / total)
        taux_traitement = round((demandes_archivees / total_demandes * 100), 1) if total_demandes > 0 else 0

        return {
            # Agents
            "total_agents": total_agents,
            "actifs": actifs,
            # Demandes - Vue générale
            "total_demandes": total_demandes,
            "demandes_en_cours": demandes_en_cours,
            "demandes_archivees": demandes_archivees,
            "taux_traitement": taux_traitement,
            # Demandes par état (dynamique - tous les états)
            "demandes_par_etat": demandes_par_etat,
            # Demandes par type (dynamique - types personnalisés)
            "demandes_par_type": demandes_par_type,
            # Types traditionnels (pour compatibilité)
            "conges": conges,
            "permissions": permissions,
            "formations": formations,
            "besoins_actes": besoins_actes,
            "d_acte_rh": d_acte_rh,
            # Satisfaction moyenne
            "satisfaction_moyenne": satisfaction,
        }

    @staticmethod
    def evolution_par_annee(session: Session) -> list[dict[str, Any]]:
        from app.models.personnel import AgentComplet

        # nombre d'agents recrutés par année
        rows = session.exec(
            select(func.extract("year", AgentComplet.date_recrutement).label("annee"), func.count(AgentComplet.id))
            .where(AgentComplet.date_recrutement.is_not(None))
            .group_by(func.extract("year", AgentComplet.date_recrutement))
            .order_by(func.extract("year", AgentComplet.date_recrutement))
        ).all()
        return [{"annee": int(a[0]), "effectif": int(a[1])} for a in rows]

    @staticmethod
    def repartition_par_grade(session: Session) -> list[dict[str, Any]]:
        from app.models.personnel import AgentComplet, GradeComplet

        rows = session.exec(
            select(GradeComplet.libelle, func.count(AgentComplet.id))
            .join(AgentComplet, GradeComplet.id == AgentComplet.grade_id, isouter=True)
            .group_by(GradeComplet.libelle)
            .order_by(GradeComplet.libelle)
        ).all()
        return [{"grade": r[0], "nb": int(r[1])} for r in rows]

    @staticmethod
    def repartition_par_service(session: Session) -> list[dict[str, Any]]:
        from app.models.personnel import AgentComplet, Service

        rows = session.exec(
            select(Service.libelle, func.count(AgentComplet.id))
            .join(AgentComplet, Service.id == AgentComplet.service_id, isouter=True)
            .group_by(Service.libelle)
            .order_by(Service.libelle)
        ).all()
        return [{"service": r[0], "nb": int(r[1])} for r in rows]

    @staticmethod
    def satisfaction_besoins(session: Session) -> dict[str, Any]:
        # ratio besoins "satisfaits" (archivés) vs "exprimés"
        exprimes = session.exec(select(func.count(HRRequest.id)).where(HRRequest.type == "BESOIN_ACTE")).one()
        satisfaits = session.exec(
            select(func.count(HRRequest.id)).where(
                HRRequest.type == "BESOIN_ACTE", HRRequest.current_state == WorkflowState.ARCHIVED
            )
        ).one()
        taux = (satisfaits / exprimes * 100) if exprimes else 0
        return {"exprimes": exprimes, "satisfaits": satisfaits, "taux": round(taux, 2)}

    # --- Workflow ---
    @staticmethod
    def next_states_for(session: Session, request_id: int) -> list[dict]:
        """
        Retourne les prochains états possibles pour une demande
        Basé sur le workflow personnalisé configuré
        """
        from app.services.hierarchy_service import HierarchyService

        request = session.get(HRRequest, request_id)
        if not request:
            return []

        # Récupérer le circuit complet
        circuit = HierarchyService.get_workflow_circuit(session, request_id)

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
        skip_hierarchy_check: bool = False,
    ) -> HRRequest:
        """
        Effectue une transition dans le workflow d'une demande RH

        Args:
            session: Session SQLModel
            request_id: ID de la demande
            to_state: État cible
            acted_by_user_id: ID de l'utilisateur qui effectue la transition
            acted_by_role: Rôle de l'utilisateur (pour historique)
            comment: Commentaire optionnel
            skip_hierarchy_check: Si True, ne vérifie pas la hiérarchie (pour admin/tests)

        Returns:
            La demande mise à jour

        Raises:
            ValueError: Si la transition est interdite
        """
        from app.services.hierarchy_service import HierarchyService

        req = session.get(HRRequest, request_id)
        if not req:
            raise ValueError("Demande introuvable")

        allowed = [s.to_state for s in RHService.next_states_for(session, req.type, req.current_state)]
        if to_state not in allowed:
            raise ValueError(f"Transition interdite: {req.current_state} -> {to_state}")

        # ✅ NOUVEAU : Vérifier que l'utilisateur a le droit de faire cette transition
        if not skip_hierarchy_check:
            can_validate = HierarchyService.can_user_validate(session, acted_by_user_id, request_id, to_state)

            if not can_validate:
                expected_validator = HierarchyService.get_expected_validator(session, request_id, to_state)
                expected_name = (
                    f"{expected_validator.nom} {expected_validator.prenom}" if expected_validator else "inconnu"
                )
                raise ValueError(
                    f"Vous n'êtes pas autorisé à effectuer cette validation. "
                    f"Cette action doit être effectuée par : {expected_name}"
                )

        # maj current assignee selon Step configuré
        step = session.exec(
            select(WorkflowStep).where(
                WorkflowStep.type == req.type,
                WorkflowStep.from_state == req.current_state,
                WorkflowStep.to_state == to_state,
            )
        ).first()
        req.current_state = to_state
        req.current_assignee_role = step.assignee_role if step else None

        session.add(
            WorkflowHistory(
                request_id=request_id,
                from_state=step.from_state if step else req.current_state,
                to_state=to_state,
                acted_by_user_id=acted_by_user_id,
                acted_by_role=acted_by_role,
                comment=comment,
            )
        )
        session.add(req)
        session.commit()
        session.refresh(req)
        return req
