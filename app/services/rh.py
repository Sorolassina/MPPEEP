# app/services/rh.py
"""
Service de gestion RH
Contient toute la logique métier liée aux ressources humaines
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import date
from sqlmodel import Session, select, func, col
from app.core.logging_config import get_logger

from app.models.rh import (
    Agent, Grade, ServiceDept,
    HRRequest, WorkflowStep, WorkflowHistory
)
from app.core.enums import RequestType, WorkflowState

logger = get_logger(__name__)

class RHService:
    # --- KPIs & Stats ---
    @staticmethod
    def kpis(session: Session) -> Dict[str, Any]:
        total_agents = session.exec(select(func.count(Agent.id))).one()
        actifs = session.exec(select(func.count(Agent.id)).where(Agent.actif == True)).one()

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
        
        # Demandes en attente par étape
        en_attente_n1 = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.current_state == WorkflowState.VALIDATION_N1)
        ).one()
        
        en_attente_n2 = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.current_state == WorkflowState.VALIDATION_N2)
        ).one()
        
        en_attente_drh = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.current_state == WorkflowState.VALIDATION_DRH)
        ).one()
        
        en_attente_daf = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.current_state == WorkflowState.SIGNATURE_DAF)
        ).one()
        
        # Demandes par type
        conges = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.type == RequestType.CONGE)
        ).one()
        
        permissions = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.type == RequestType.PERMISSION)
        ).one()
        
        formations = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.type == RequestType.FORMATION)
        ).one()
        
        besoins_actes = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.type == RequestType.BESOIN_ACTE)
        ).one()

        # Satisfaction moyenne (sur besoins d'actes traités)
        sats = session.exec(
            select(func.avg(col(HRRequest.satisfaction_note))).where(
                HRRequest.type == RequestType.BESOIN_ACTE,
                HRRequest.satisfaction_note.is_not(None),
                HRRequest.current_state == WorkflowState.ARCHIVED
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
            
            # Demandes en attente par étape du circuit
            "en_attente_n1": en_attente_n1,
            "en_attente_n2": en_attente_n2,
            "en_attente_drh": en_attente_drh,
            "en_attente_daf": en_attente_daf,
            
            # Demandes par type
            "conges": conges,
            "permissions": permissions,
            "formations": formations,
            "besoins_actes": besoins_actes,
            
            # Satisfaction
            "satisfaction_besoins_archives": satisfaction
        }

    @staticmethod
    def evolution_par_annee(session: Session) -> List[Dict[str, Any]]:
        # nombre d'agents recrutés par année
        rows = session.exec(
            select(func.extract('year', Agent.date_recrutement).label("annee"),
                   func.count(Agent.id))
            .where(Agent.date_recrutement.is_not(None))
            .group_by(func.extract('year', Agent.date_recrutement))
            .order_by(func.extract('year', Agent.date_recrutement))
        ).all()
        return [{"annee": int(a[0]), "effectif": int(a[1])} for a in rows]

    @staticmethod
    def repartition_par_grade(session: Session) -> List[Dict[str, Any]]:
        rows = session.exec(
            select(Grade.libelle, func.count(Agent.id))
            .join(Agent, isouter=True)
            .group_by(Grade.libelle)
            .order_by(Grade.libelle)
        ).all()
        return [{"grade": r[0], "nb": int(r[1])} for r in rows]

    @staticmethod
    def repartition_par_service(session: Session) -> List[Dict[str, Any]]:
        rows = session.exec(
            select(ServiceDept.libelle, func.count(Agent.id))
            .join(Agent, isouter=True)
            .group_by(ServiceDept.libelle)
            .order_by(ServiceDept.libelle)
        ).all()
        return [{"service": r[0], "nb": int(r[1])} for r in rows]

    @staticmethod
    def satisfaction_besoins(session: Session) -> Dict[str, Any]:
        # ratio besoins "satisfaits" (archivés) vs "exprimés"
        exprimes = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.type == RequestType.BESOIN_ACTE)
        ).one()
        satisfaits = session.exec(
            select(func.count(HRRequest.id)).where(HRRequest.type == RequestType.BESOIN_ACTE,
                                                   HRRequest.current_state == WorkflowState.ARCHIVED)
        ).one()
        taux = (satisfaits / exprimes * 100) if exprimes else 0
        return {"exprimes": exprimes, "satisfaits": satisfaits, "taux": round(taux, 2)}

    # --- Workflow ---
    @staticmethod
    def next_states_for(session: Session, req_type: RequestType, from_state: WorkflowState) -> List[WorkflowStep]:
        return session.exec(
            select(WorkflowStep)
            .where(WorkflowStep.type == req_type, WorkflowStep.from_state == from_state)
            .order_by(WorkflowStep.order_index)
        ).all()

    @staticmethod
    def transition(session: Session, request_id: int, to_state: WorkflowState, acted_by_user_id: int,
                   acted_by_role: str, comment: Optional[str] = None, skip_hierarchy_check: bool = False) -> HRRequest:
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
            can_validate = HierarchyService.can_user_validate(
                session, acted_by_user_id, request_id, to_state
            )
            
            if not can_validate:
                expected_validator = HierarchyService.get_expected_validator(
                    session, request_id, to_state
                )
                expected_name = f"{expected_validator.nom} {expected_validator.prenom}" if expected_validator else "inconnu"
                raise ValueError(
                    f"Vous n'êtes pas autorisé à effectuer cette validation. "
                    f"Cette action doit être effectuée par : {expected_name}"
                )

        # maj current assignee selon Step configuré
        step = session.exec(
            select(WorkflowStep).where(
                WorkflowStep.type == req.type,
                WorkflowStep.from_state == req.current_state,
                WorkflowStep.to_state == to_state
            )
        ).first()
        req.current_state = to_state
        req.current_assignee_role = step.assignee_role if step else None

        session.add(WorkflowHistory(
            request_id=request_id,
            from_state=step.from_state if step else req.current_state,
            to_state=to_state,
            acted_by_user_id=acted_by_user_id,
            acted_by_role=acted_by_role,
            comment=comment
        ))
        session.add(req)
        session.commit()
        session.refresh(req)
        return req
