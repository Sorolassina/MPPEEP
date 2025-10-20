# app/models/rh.py
"""
Modèles de données pour le système RH
"""

from __future__ import annotations

from datetime import date, datetime

from sqlmodel import Field, SQLModel
from sqlalchemy import String

from app.core.enums import RequestType, WorkflowState


# --- Référentiels ---
class Grade(SQLModel, table=True):
    """Grades/Catégories hiérarchiques"""

    __tablename__ = "grade"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    libelle: str

    # Note: Pas de Relationship() pour éviter les problèmes SQLAlchemy 2.0
    # Les relations sont gérées via les foreign keys uniquement


# --- Agent ---
class Agent(SQLModel, table=True):
    """Agent/Employé"""

    __tablename__ = "agent"

    id: int | None = Field(default=None, primary_key=True)
    matricule: str = Field(index=True, unique=True)
    nom: str
    prenom: str
    email: str | None = None
    date_recrutement: date | None = None
    actif: bool = True

    # Foreign keys (relations gérées manuellement)
    grade_id: int | None = Field(default=None, foreign_key="grade.id")
    service_id: int | None = Field(default=None, foreign_key="service.id")

    # Note: Pas de Relationship() - on récupère les objets liés manuellement via les services


# --- Demandes (congés, permissions, formations, besoins d'acte) ---
class HRRequestBase(SQLModel):
    """Base pour les demandes administratives"""

    type: str  # Code du type de demande (ex: 'DEMANDE_CONGE', 'DEMANDE_MATERIEL')
    objet: str
    motif: str | None = None

    # Pour congés/permissions/formations
    date_debut: date | None = None
    date_fin: date | None = None
    nb_jours: float | None = None

    # Pour besoins d'actes administratifs
    acte_type: str | None = None  # Type d'acte spécifique (ActeAdministratifType)

    # Document joint (optionnel)
    document_joint: str | None = Field(default=None, max_length=500)  # Chemin vers le fichier
    document_filename: str | None = Field(default=None, max_length=255)  # Nom original du fichier

    # Satisfaction après traitement
    satisfaction_note: int | None = Field(default=None, ge=1, le=5)  # note agent après traitement (1..5)


class HRRequest(HRRequestBase, table=True):
    """Demande administrative complète"""

    __tablename__ = "hrrequest"

    id: int | None = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    current_state: WorkflowState = Field(default=WorkflowState.DRAFT, sa_type=String)  # Stocké comme string
    current_assignee_role: str | None = None  # ex: "AGENT", "N1", "N2", "DRH", "DG", "DAF"


# --- Workflow paramétrique ---
class WorkflowStep(SQLModel, table=True):
    """
    Définit l’enchaînement des étapes pour un type de demande dans l’administration.
    Exemple standard: SUBMITTED -> VALIDATION_N1 -> VALIDATION_DRH -> SIGNATURE_DG -> ARCHIVED
    """

    id: int | None = Field(default=None, primary_key=True)
    type: RequestType = Field(sa_type=String)  # Stocké comme string
    from_state: WorkflowState = Field(sa_type=String)  # Stocké comme string
    to_state: WorkflowState = Field(sa_type=String)  # Stocké comme string
    assignee_role: str | None = None  # rôle en charge à l'étape cible (N1/DRH/DG)
    order_index: int = 0


# Historique des transitions
class WorkflowHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    request_id: int = Field(foreign_key="hrrequest.id", index=True)
    from_state: WorkflowState = Field(sa_type=String)  # Stocké comme string
    to_state: WorkflowState = Field(sa_type=String)  # Stocké comme string
    acted_by_user_id: int | None = None  # selon ton modèle User
    acted_by_role: str | None = None
    comment: str | None = None
    acted_at: datetime = Field(default_factory=datetime.utcnow)
