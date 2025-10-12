from sqlmodel import Session, select
from app.models.rh import WorkflowStep
from app.core.enums import RequestType, WorkflowState

def ensure_workflow_steps(session: Session):
    def add(t, f, to, role, idx):
        if not session.exec(
            select(WorkflowStep).where(WorkflowStep.type==t, WorkflowStep.from_state==f, WorkflowStep.to_state==to)
        ).first():
            session.add(WorkflowStep(type=t, from_state=f, to_state=to, assignee_role=role, order_index=idx))

    for t in [RequestType.CONGE, RequestType.PERMISSION, RequestType.FORMATION, RequestType.BESOIN_ACTE]:
        # Circuit complet OBLIGATOIRE : DRAFT → SUBMITTED → N1 → N2 → DRH → DG → DAF → ARCHIVED
        # N2 est OBLIGATOIRE (pas de chemin direct N1→DRH)
        add(t, WorkflowState.DRAFT,         WorkflowState.SUBMITTED,      "AGENT",  1)
        add(t, WorkflowState.SUBMITTED,     WorkflowState.VALIDATION_N1,  "N1",     2)
        add(t, WorkflowState.VALIDATION_N1, WorkflowState.VALIDATION_N2,  "N2",     3)  # N2 OBLIGATOIRE
        add(t, WorkflowState.VALIDATION_N2, WorkflowState.VALIDATION_DRH, "DRH",    4)
        add(t, WorkflowState.VALIDATION_DRH,WorkflowState.SIGNATURE_DG,   "DG",     5)
        add(t, WorkflowState.SIGNATURE_DG,  WorkflowState.SIGNATURE_DAF,  "DAF",    6)  # DAF OBLIGATOIRE
        add(t, WorkflowState.SIGNATURE_DAF, WorkflowState.ARCHIVED,       None,     7)

    session.commit()