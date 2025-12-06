# app/models/personnel.py
"""
Modèles de données pour la gestion complète du personnel
"""

from __future__ import annotations

from datetime import date, datetime

from sqlmodel import Field, SQLModel
from sqlalchemy import String, Column, Text

from app.core.enums import GradeCategory, PositionAdministrative, RoleBudgetaire, SituationFamiliale, TypeDocument

# ==========================================
# STRUCTURE ORGANISATIONNELLE
# ==========================================


class Cabinet(SQLModel, table=True):
    """Cabinet du Ministre (peut avoir des directions, sous-directions ou services)"""

    __tablename__ = "cabinet"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=20)
    libelle: str = Field(max_length=200)
    description: str | None = None
    actif: bool = True

    # Responsable du cabinet (optionnel)
    responsable_id: int | None = Field(default=None, foreign_key="agent_complet.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Programme(SQLModel, table=True):
    """Programme budgétaire (niveau le plus haut)"""

    __tablename__ = "programme"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=20)
    libelle: str = Field(max_length=200)
    description: str | None = None
    actif: bool = True

    # Responsable du programme (optionnel)
    responsable_id: int | None = Field(default=None, foreign_key="agent_complet.id")
    
    # Missions du programme (JSON: liste de strings)
    missions: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Direction(SQLModel, table=True):
    """Direction (rattachée à un programme ou à un cabinet)"""

    __tablename__ = "direction"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=20)
    libelle: str = Field(max_length=200)
    description: str | None = None
    actif: bool = True
    type: str | None = Field(default=None, index=True)  # Type de direction: "CENTRALE", "GENERALE", etc.

    # Hiérarchie - peut être rattachée à un Programme OU à un Cabinet (exclusion mutuelle)
    programme_id: int | None = Field(default=None, foreign_key="programme.id")
    cabinet_id: int | None = Field(default=None, foreign_key="cabinet.id")

    # Chef de direction (optionnel)
    directeur_id: int | None = Field(default=None, foreign_key="agent_complet.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SousDirection(SQLModel, table=True):
    """Sous-direction (peut être rattachée à une direction, un programme ou un cabinet)"""

    __tablename__ = "sous_direction"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=20)
    libelle: str = Field(max_length=200)
    description: str | None = None
    actif: bool = True

    # Hiérarchie - peut être rattachée à une Direction, un Programme ou un Cabinet (exclusion mutuelle)
    direction_id: int | None = Field(default=None, foreign_key="direction.id")
    programme_id: int | None = Field(default=None, foreign_key="programme.id")
    cabinet_id: int | None = Field(default=None, foreign_key="cabinet.id")

    # Chef de sous-direction (optionnel)
    chef_sous_direction_id: int | None = Field(default=None, foreign_key="agent_complet.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Service(SQLModel, table=True):
    """Service (peut être rattaché à une sous-direction, une direction, un programme ou un cabinet)"""

    __tablename__ = "service"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=20)
    libelle: str = Field(max_length=200)
    description: str | None = None
    actif: bool = True

    # Hiérarchie - peut être rattaché à une Sous-direction, une Direction, un Programme ou un Cabinet (exclusion mutuelle)
    sous_direction_id: int | None = Field(default=None, foreign_key="sous_direction.id")
    direction_id: int | None = Field(default=None, foreign_key="direction.id")
    programme_id: int | None = Field(default=None, foreign_key="programme.id")
    cabinet_id: int | None = Field(default=None, foreign_key="cabinet.id")

    # Chef de service (optionnel)
    chef_service_id: int | None = Field(default=None, foreign_key="agent_complet.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# GRADES
# ==========================================


class GradeComplet(SQLModel, table=True):
    """
    Grade complet de la fonction publique
    Exemples: A4, A3, A2, A1, B4, B3, B2, B1, etc.
    """

    __tablename__ = "grade_complet"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=10)  # Ex: "A4", "B3"
    libelle: str = Field(max_length=200)  # Ex: "Administrateur civil principal"
    categorie: GradeCategory = Field(sa_type=String)  # A, B, C, D - stocké comme string
    echelon_min: int = 1
    echelon_max: int = 10

    # Indices salariaux (optionnel)
    indice_min: int | None = None
    indice_max: int | None = None

    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# AGENT COMPLET
# ==========================================


class AgentComplet(SQLModel, table=True):
    """
    Agent avec toutes les informations nécessaires pour la gestion du personnel
    """

    __tablename__ = "agent_complet"

    id: int | None = Field(default=None, primary_key=True)

    # Identification
    matricule: str = Field(index=True, unique=True, max_length=50)
    numero_cni: str | None = Field(default=None, max_length=50)
    numero_passeport: str | None = Field(default=None, max_length=50)

    # État civil
    nom: str = Field(max_length=100)
    prenom: str = Field(max_length=100)
    nom_jeune_fille: str | None = Field(default=None, max_length=100)
    date_naissance: date | None = None
    lieu_naissance: str | None = Field(default=None, max_length=200)
    nationalite: str = Field(default="Ivoirienne", max_length=100)
    sexe: str | None = Field(default=None, max_length=1)  # M/F
    situation_familiale: SituationFamiliale | None = Field(default=None, sa_type=String)  # Stocké comme string
    nombre_enfants: int = Field(default=0, ge=0)

    # Coordonnées
    email_professionnel: str | None = Field(default=None, max_length=150)
    email_personnel: str | None = Field(default=None, max_length=150)
    telephone_1: str | None = Field(default=None, max_length=20)
    telephone_2: str | None = Field(default=None, max_length=20)
    adresse: str | None = Field(default=None, max_length=500)
    ville: str | None = Field(default=None, max_length=100)
    code_postal: str | None = Field(default=None, max_length=10)

    # Carrière
    date_recrutement: date | None = None
    date_prise_service: date | None = None
    date_depart_retraite_prevue: date | None = None
    position_administrative: PositionAdministrative = Field(default=PositionAdministrative.EN_ACTIVITE, sa_type=String)  # Stocké comme string

    # Affectation actuelle
    grade_id: int | None = Field(default=None, foreign_key="grade_complet.id")
    echelon: int = Field(default=1, ge=1)
    indice: int | None = None

    # Rattachement hiérarchique (tous optionnels)
    # Un agent peut être rattaché à un service, une sous-direction, ou une direction
    # Aucun rattachement n'est obligatoire - un agent peut exister sans rattachement hiérarchique
    # Exclusion mutuelle : si service_id est renseigné, sous_direction_id et direction_id doivent être None
    # Si sous_direction_id est renseigné, direction_id doit être None
    service_id: int | None = Field(default=None, foreign_key="service.id")
    sous_direction_id: int | None = Field(default=None, foreign_key="sous_direction.id")
    direction_id: int | None = Field(default=None, foreign_key="direction.id")
    programme_id: int | None = Field(default=None, foreign_key="programme.id")  # Déprécié, conservé pour compatibilité

    fonction: str | None = Field(default=None, max_length=200)  # Ex: "Chef de division"

    # Rôle budgétaire
    role_budgetaire: RoleBudgetaire | None = Field(default=None, sa_type=String)  # Stocké comme string

    # Lien avec compte utilisateur (optionnel)
    user_id: int | None = Field(default=None, foreign_key="user.id")

    # Congés annuels
    solde_conges_annuel: float = Field(default=30.0, ge=0)  # Jours de congé restants
    conges_annee_en_cours: int = Field(default=30, ge=0)  # Jours alloués cette année

    # Statut
    actif: bool = True

    # Photo (chemin vers le fichier)
    photo_path: str | None = Field(default=None, max_length=500)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int | None = None
    updated_by: int | None = None

    # Notes/Remarques
    notes: str | None = None


# ==========================================
# DOCUMENTS
# ==========================================


class DocumentAgent(SQLModel, table=True):
    """Documents liés à un agent"""

    __tablename__ = "document_agent"

    id: int | None = Field(default=None, primary_key=True)

    agent_id: int = Field(foreign_key="agent_complet.id", index=True)

    type_document: TypeDocument
    titre: str = Field(max_length=200)
    description: str | None = None

    # Fichier
    file_path: str = Field(max_length=500)
    file_name: str = Field(max_length=255)
    file_size: int | None = None  # en octets
    file_type: str | None = Field(default=None, max_length=50)  # MIME type

    # Dates importantes (pour documents avec validité)
    date_emission: date | None = None
    date_expiration: date | None = None

    # Métadonnées
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by: int | None = None

    actif: bool = True


# ==========================================
# HISTORIQUE DE CARRIÈRE
# ==========================================


class HistoriqueCarriere(SQLModel, table=True):
    """Historique des événements de carrière d'un agent"""

    __tablename__ = "historique_carriere"

    id: int | None = Field(default=None, primary_key=True)

    agent_id: int = Field(foreign_key="agent_complet.id", index=True)

    type_evenement: str = Field(max_length=50)  # PROMOTION, MUTATION, AFFECTATION, SANCTION, etc.
    date_evenement: date

    # Détails de l'événement
    description: str

    # Avant/Après (pour promotions, mutations)
    ancien_grade_id: int | None = Field(default=None, foreign_key="grade_complet.id")
    nouveau_grade_id: int | None = Field(default=None, foreign_key="grade_complet.id")

    ancien_service_id: int | None = Field(default=None, foreign_key="service.id")
    nouveau_service_id: int | None = Field(default=None, foreign_key="service.id")

    ancien_echelon: int | None = None
    nouveau_echelon: int | None = None

    # Référence administrative
    numero_decision: str | None = Field(default=None, max_length=100)
    document_path: str | None = Field(default=None, max_length=500)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int | None = None


# ==========================================
# ÉVALUATIONS
# ==========================================


class EvaluationAgent(SQLModel, table=True):
    """Évaluations annuelles des agents"""

    __tablename__ = "evaluation_agent"

    id: int | None = Field(default=None, primary_key=True)

    agent_id: int = Field(foreign_key="agent_complet.id", index=True)

    annee: int = Field(index=True)
    periode_debut: date
    periode_fin: date

    # Évaluateur
    evaluateur_id: int | None = Field(default=None, foreign_key="agent_complet.id")

    # Notes (sur 20 ou autre échelle)
    note_competence_technique: float | None = Field(default=None, ge=0, le=20)
    note_sens_organisation: float | None = Field(default=None, ge=0, le=20)
    note_esprit_initiative: float | None = Field(default=None, ge=0, le=20)
    note_assiduite: float | None = Field(default=None, ge=0, le=20)
    note_relation_service: float | None = Field(default=None, ge=0, le=20)

    note_finale: float | None = Field(default=None, ge=0, le=20)
    appreciation: str | None = None  # EXCELLENT, TRES_BON, BON, PASSABLE, INSUFFISANT

    # Commentaires
    points_forts: str | None = None
    points_amelioration: str | None = None
    objectifs_annee_suivante: str | None = None
    commentaire_evaluateur: str | None = None
    commentaire_agent: str | None = None

    # Statut
    statut: str = Field(default="DRAFT")  # DRAFT, SOUMIS, VALIDE, CONTESTE

    # Document
    document_path: str | None = Field(default=None, max_length=500)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    validated_at: datetime | None = None
    validated_by: int | None = None
