"""
Modèles pour la configuration dynamique des workflows
Permet de créer et gérer des circuits de validation personnalisés
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class WorkflowDirection(str, Enum):
    """Direction du workflow"""

    ASCENDANT = "ASCENDANT"  # Agent → Hiérarchie (demandes classiques)
    DESCENDANT = "DESCENDANT"  # Hiérarchie → Agent (tâches, instructions)


class WorkflowRoleType(str, Enum):
    """Types de rôles dans un workflow"""

    DEMANDEUR = "DEMANDEUR"  # Celui qui initie la demande
    N_PLUS_1 = "N+1"  # Chef de service
    N_PLUS_2 = "N+2"  # Sous-directeur
    RH = "RH"  # Sous-directeur RH
    DAF = "DAF"  # Direction Administrative et Financière
    CUSTOM = "CUSTOM"  # Rôle personnalisé


# ==========================================
# TEMPLATES DE WORKFLOW
# ==========================================


class WorkflowTemplate(SQLModel, table=True):
    """
    Template de workflow réutilisable
    Définit un circuit de validation type
    """

    __tablename__ = "workflow_template"

    id: int | None = Field(default=None, primary_key=True)

    # Identification
    code: str = Field(index=True, unique=True, max_length=50)  # Ex: "CONGE_STD"
    nom: str = Field(max_length=200)  # Ex: "Circuit Congé Standard"
    description: str | None = None

    # Direction du workflow
    direction: WorkflowDirection = Field(default=WorkflowDirection.ASCENDANT)

    # Icône (emoji ou FontAwesome)
    icone: str = Field(default="📄", max_length=50)

    # Couleur (pour l'interface)
    couleur: str = Field(default="#3498db", max_length=20)

    # Statut
    actif: bool = True
    est_systeme: bool = False  # Si True, ne peut pas être supprimé (workflows système)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int | None = None
    updated_by: int | None = None


class WorkflowTemplateStep(SQLModel, table=True):
    """
    Étape dans un template de workflow
    Définit un rôle qui doit intervenir
    """

    __tablename__ = "workflow_template_step"

    id: int | None = Field(default=None, primary_key=True)

    # Relation avec le template
    template_id: int = Field(foreign_key="workflow_template.id", index=True)

    # Ordre dans le circuit
    order_index: int = Field(ge=1)  # 1, 2, 3, ...

    # Type de rôle à cette étape
    role_type: WorkflowRoleType

    # Pour CUSTOM : nom du rôle personnalisé
    custom_role_name: str | None = Field(default=None, max_length=100)

    # Règles
    obligatoire: bool = True  # Si False, peut être sauté
    peut_rejeter: bool = True  # Si False, ne peut que valider
    delai_jours: int | None = None  # Délai de traitement suggéré (en jours)

    # Notifications
    notifier_par_email: bool = True
    notifier_par_sms: bool = False

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# TYPES DE DEMANDES PERSONNALISÉS
# ==========================================


class RequestTypeCustom(SQLModel, table=True):
    """
    Type de demande personnalisé
    Associé à un template de workflow
    """

    __tablename__ = "request_type_custom"

    id: int | None = Field(default=None, primary_key=True)

    # Identification
    code: str = Field(index=True, unique=True, max_length=50)  # Ex: "DEMANDE_MATERIEL"
    libelle: str = Field(max_length=200)  # Ex: "Demande de matériel"
    description: str | None = None

    # Workflow associé
    workflow_template_id: int = Field(foreign_key="workflow_template.id", index=True)

    # Catégorie (pour regroupement dans l'interface)
    categorie: str = Field(default="Autre", max_length=100)  # Ex: "RH", "Logistique", "Administratif"

    # Icône et couleur (héritées du template par défaut, mais peuvent être surchargées)
    icone: str | None = Field(default=None, max_length=50)
    couleur: str | None = Field(default=None, max_length=20)

    # Champs du formulaire (JSON)
    # Ex: [{"name": "date_debut", "type": "date", "required": true, "label": "Date de début"}]
    champs_formulaire: str | None = None  # JSON stringifié

    # Documents requis
    document_obligatoire: bool = False
    types_documents_acceptes: str | None = None  # Ex: "pdf,doc,docx"

    # Règles métier
    necessite_validation_rh: bool = False  # Force le passage par RH
    necessite_validation_daf: bool = False  # Force le passage par DAF

    # Statut
    actif: bool = True
    est_systeme: bool = False  # Si True, ne peut pas être supprimé

    # Ordre d'affichage dans les menus
    ordre_affichage: int = Field(default=999)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int | None = None
    updated_by: int | None = None


# ==========================================
# RÔLES PERSONNALISÉS
# ==========================================


class CustomRole(SQLModel, table=True):
    """
    Rôle personnalisé dans l'organisation
    Permet de définir des validateurs au-delà de la hiérarchie standard
    """

    __tablename__ = "custom_role"

    id: int | None = Field(default=None, primary_key=True)

    # Identification
    code: str = Field(index=True, unique=True, max_length=50)  # Ex: "RESP_BUDGET"
    libelle: str = Field(max_length=200)  # Ex: "Responsable Budget"
    description: str | None = None

    # Agent(s) ayant ce rôle
    # Note: Géré via une table de liaison CustomRoleAssignment

    # Statut
    actif: bool = True

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CustomRoleAssignment(SQLModel, table=True):
    """
    Attribution d'un rôle personnalisé à un agent
    """

    __tablename__ = "custom_role_assignment"

    id: int | None = Field(default=None, primary_key=True)

    # Relations
    custom_role_id: int = Field(foreign_key="custom_role.id", index=True)
    agent_id: int = Field(foreign_key="agent_complet.id", index=True)

    # Période de validité
    date_debut: datetime = Field(default_factory=datetime.utcnow)
    date_fin: datetime | None = None

    # Statut
    actif: bool = True

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int | None = None


# ==========================================
# HISTORIQUE DES MODIFICATIONS DE CONFIG
# ==========================================


class WorkflowConfigHistory(SQLModel, table=True):
    """
    Historique des modifications de configuration des workflows
    Pour audit et traçabilité
    """

    __tablename__ = "workflow_config_history"

    id: int | None = Field(default=None, primary_key=True)

    # Type d'entité modifiée
    entity_type: str = Field(max_length=50)  # "WorkflowTemplate", "RequestTypeCustom", etc.
    entity_id: int

    # Type d'action
    action: str = Field(max_length=20)  # "CREATE", "UPDATE", "DELETE", "ACTIVATE", "DEACTIVATE"

    # Détails de la modification (JSON)
    changes: str | None = None  # JSON stringifié avec les changements

    # Métadonnées
    performed_at: datetime = Field(default_factory=datetime.utcnow)
    performed_by: int  # ID de l'utilisateur
    ip_address: str | None = Field(default=None, max_length=50)
