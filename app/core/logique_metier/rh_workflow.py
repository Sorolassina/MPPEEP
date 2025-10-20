from sqlmodel import Session, select

from app.core.enums import RequestType, WorkflowState
from app.models.rh import WorkflowStep


def ensure_workflow_steps(session: Session):
    def add(t, f, to, role, idx):
        if not session.exec(
            select(WorkflowStep).where(
                WorkflowStep.type == t, WorkflowStep.from_state == f, WorkflowStep.to_state == to
            )
        ).first():
            session.add(WorkflowStep(type=t, from_state=f, to_state=to, assignee_role=role, order_index=idx))

    for t in [RequestType.CONGE, RequestType.PERMISSION, RequestType.FORMATION, RequestType.BESOIN_ACTE]:
        # Circuit complet OBLIGATOIRE : DRAFT → SUBMITTED → N1 → N2 → DRH → DAF → ARCHIVED
        # N2 et DAF sont OBLIGATOIRES
        add(t, WorkflowState.DRAFT, WorkflowState.SUBMITTED, "AGENT", 1)
        add(t, WorkflowState.SUBMITTED, WorkflowState.VALIDATION_N1, "N1", 2)
        add(t, WorkflowState.VALIDATION_N1, WorkflowState.VALIDATION_N2, "N2", 3)  # N2 OBLIGATOIRE
        add(t, WorkflowState.VALIDATION_N2, WorkflowState.VALIDATION_DRH, "DRH", 4)
        add(t, WorkflowState.VALIDATION_DRH, WorkflowState.SIGNATURE_DAF, "DAF", 5)  # DAF OBLIGATOIRE
        add(t, WorkflowState.SIGNATURE_DAF, WorkflowState.ARCHIVED, None, 6)

    session.commit()
