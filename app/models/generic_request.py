"""
Modèle générique pour les demandes utilisables dans tous les modules
Basé sur HRRequest mais généralisé pour être utilisé par RH, Budget, Stock, Performance, etc.
"""

from datetime import date, datetime

from sqlalchemy import Column, String, Text
from sqlmodel import Field, SQLModel

from app.core.enums import WorkflowState


class GenericRequestBase(SQLModel):
    """Base pour les demandes génériques (utilisables dans tous les modules)"""

    # Module d'origine (rh, budget, stock, performance, etc.)
    module: str = Field(index=True, max_length=50)  # Ex: "rh", "budget", "stock", "performance"

    # Type de demande (code du RequestTypeCustom)
    type: str = Field(index=True, max_length=50)  # Ex: 'DEMANDE_CONGE', 'DEMANDE_MATERIEL', 'DEMANDE_BUDGET'

    # Contenu de la demande
    objet: str = Field(max_length=500)
    motif: str | None = None
    description: str | None = Field(default=None, sa_column=Column(Text))

    # Dates (optionnelles selon le type de demande)
    date_debut: date | None = None
    date_fin: date | None = None
    nb_jours: float | None = None

    # Données spécifiques au module (JSON pour flexibilité)
    # Ex: pour Budget: {"montant": 1000000, "programme_id": 1}
    # Ex: pour Stock: {"article_id": 5, "quantite": 10}
    donnees_metier: str | None = Field(default=None, sa_column=Column(Text))  # JSON stringifié

    # Document joint (optionnel)
    document_joint: str | None = Field(default=None, max_length=500)  # Chemin vers le fichier
    document_filename: str | None = Field(default=None, max_length=255)  # Nom original du fichier

    # Satisfaction après traitement
    satisfaction_note: int | None = Field(default=None, ge=1, le=5)  # note agent après traitement (1..5)
    satisfaction_commentaire: str | None = Field(default=None, sa_column=Column(Text))


class GenericRequest(GenericRequestBase, table=True):
    """Demande générique complète (utilisable dans tous les modules)"""

    __tablename__ = "generic_request"

    id: int | None = Field(default=None, primary_key=True)

    # Agent/Utilisateur demandeur
    demandeur_id: int = Field(foreign_key="agent_complet.id", index=True)  # ID de l'agent demandeur
    demandeur_user_id: int | None = Field(
        default=None, foreign_key="user.id", index=True
    )  # ID de l'utilisateur (si différent de l'agent)

    # Workflow
    current_state: WorkflowState = Field(default=WorkflowState.DRAFT, sa_type=String, index=True)  # Stocké comme string
    current_assignee_role: str | None = Field(default=None, max_length=100)  # ex: "AGENT", "N1", "N2", "DRH", "DG", "DAF"

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class GenericWorkflowHistory(SQLModel, table=True):
    """Historique des transitions de workflow pour les demandes génériques"""

    __tablename__ = "generic_workflow_history"

    id: int | None = Field(default=None, primary_key=True)
    request_id: int = Field(foreign_key="generic_request.id", index=True)
    from_state: WorkflowState = Field(sa_type=String)  # Stocké comme string
    to_state: WorkflowState = Field(sa_type=String)  # Stocké comme string
    acted_by_user_id: int | None = Field(default=None, foreign_key="user.id")
    acted_by_role: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, sa_column=Column(Text))
    acted_at: datetime = Field(default_factory=datetime.utcnow)

