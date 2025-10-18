# app/models/rh.py
"""
Modèles de données pour le système RH
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel, Field
from app.core.enums import RequestType, WorkflowState, ActeAdministratifType


# --- Référentiels ---
class Grade(SQLModel, table=True):
    """Grades/Catégories hiérarchiques"""
    __tablename__ = "grade"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    libelle: str
    
    # Note: Pas de Relationship() pour éviter les problèmes SQLAlchemy 2.0
    # Les relations sont gérées via les foreign keys uniquement

class ServiceDept(SQLModel, table=True):
    """Services/Départements"""
    __tablename__ = "servicedept"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    libelle: str
    description: Optional[str] = None
    actif: bool = Field(default=True)
    direction_id: Optional[int] = Field(default=None, foreign_key="direction.id")
    
    # Note: Pas de Relationship() pour éviter les problèmes SQLAlchemy 2.0
    # Les relations sont gérées via les foreign keys uniquement

# --- Agent ---
class Agent(SQLModel, table=True):
    """Agent/Employé"""
    __tablename__ = "agent"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    matricule: str = Field(index=True, unique=True)
    nom: str
    prenom: str
    email: Optional[str] = None
    date_recrutement: Optional[date] = None
    actif: bool = True

    # Foreign keys (relations gérées manuellement)
    grade_id: Optional[int] = Field(default=None, foreign_key="grade.id")
    service_id: Optional[int] = Field(default=None, foreign_key="servicedept.id")
    
    # Note: Pas de Relationship() - on récupère les objets liés manuellement via les services

# --- Demandes (congés, permissions, formations, besoins d'acte) ---
class HRRequestBase(SQLModel):
    """Base pour les demandes administratives"""
    type: RequestType
    objet: str
    motif: Optional[str] = None
    
    # Pour congés/permissions/formations
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    nb_jours: Optional[float] = None
    
    # Pour besoins d'actes administratifs
    acte_type: Optional[str] = None  # Type d'acte spécifique (ActeAdministratifType)
    
    # Document joint (optionnel)
    document_joint: Optional[str] = Field(default=None, max_length=500)  # Chemin vers le fichier
    document_filename: Optional[str] = Field(default=None, max_length=255)  # Nom original du fichier
    
    # Satisfaction après traitement
    satisfaction_note: Optional[int] = Field(default=None, ge=1, le=5)  # note agent après traitement (1..5)

class HRRequest(HRRequestBase, table=True):
    """Demande administrative complète"""
    __tablename__ = "hrrequest"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    current_state: WorkflowState = Field(default=WorkflowState.DRAFT)
    current_assignee_role: Optional[str] = None  # ex: "AGENT", "N1", "N2", "DRH", "DG", "DAF"

# --- Workflow paramétrique ---
class WorkflowStep(SQLModel, table=True):
    """
    Définit l’enchaînement des étapes pour un type de demande dans l’administration.
    Exemple standard: SUBMITTED -> VALIDATION_N1 -> VALIDATION_DRH -> SIGNATURE_DG -> ARCHIVED
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    type: RequestType
    from_state: WorkflowState
    to_state: WorkflowState
    assignee_role: Optional[str] = None      # rôle en charge à l’étape cible (N1/DRH/DG)
    order_index: int = 0

# Historique des transitions
class WorkflowHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: int = Field(foreign_key="hrrequest.id", index=True)
    from_state: WorkflowState
    to_state: WorkflowState
    acted_by_user_id: Optional[int] = None   # selon ton modèle User
    acted_by_role: Optional[str] = None
    comment: Optional[str] = None
    acted_at: datetime = Field(default_factory=datetime.utcnow)
