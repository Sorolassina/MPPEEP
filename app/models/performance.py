# app/models/performance.py
"""
Modèles de données pour le module Performance
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlmodel import Field, SQLModel

# ============================================
# ENUMS
# ============================================


class StatutObjectif(str, Enum):
    """Statuts possibles pour un objectif"""

    PLANIFIE = "PLANIFIE"
    EN_COURS = "EN_COURS"
    ATTEINT = "ATTEINT"
    EN_RETARD = "EN_RETARD"
    ANNULE = "ANNULE"


class PrioriteObjectif(str, Enum):
    """Priorités d'un objectif"""

    BASSE = "BASSE"
    NORMALE = "NORMALE"
    HAUTE = "HAUTE"
    CRITIQUE = "CRITIQUE"


class TypeObjectif(str, Enum):
    """Types d'objectifs"""

    STRATEGIQUE = "STRATEGIQUE"
    OPERATIONNEL = "OPERATIONNEL"
    FINANCIER = "FINANCIER"
    RH = "RH"
    QUALITE = "QUALITE"
    CLIENT = "CLIENT"


# ============================================
# OBJECTIFS DE PERFORMANCE
# ============================================


class ObjectifPerformance(SQLModel, table=True):
    """Objectifs de performance organisationnelle"""

    __tablename__ = "objectif_performance"

    id: int | None = Field(default=None, primary_key=True)

    # Informations générales
    titre: str = Field(max_length=200, index=True)
    description: str | None = None

    # Classification
    type_objectif: TypeObjectif = Field(default=TypeObjectif.OPERATIONNEL)
    priorite: PrioriteObjectif = Field(default=PrioriteObjectif.NORMALE)

    # Période et échéances
    date_debut: date = Field(default_factory=date.today)
    date_fin: date
    periode: str = Field(max_length=50)  # "2025", "Q1 2025", "Janvier 2025"

    # Valeurs et objectifs
    valeur_cible: Decimal = Field(max_digits=15, decimal_places=2)
    valeur_actuelle: Decimal | None = Field(default=0, max_digits=15, decimal_places=2)
    unite: str = Field(max_length=50)  # "%", "€", "nombre", "heures"

    # Responsabilité
    responsable_id: int = Field(foreign_key="user.id")
    service_responsable: str | None = Field(default=None, max_length=100)

    # Statut et progression
    statut: StatutObjectif = Field(default=StatutObjectif.PLANIFIE)
    progression_pourcentage: Decimal | None = Field(default=0, max_digits=5, decimal_places=2)

    # Indicateurs associés
    indicateurs_associes: str | None = None  # JSON string des IDs d'indicateurs

    # Commentaires et notes
    commentaires: str | None = None
    notes_internes: str | None = None

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_id: int = Field(foreign_key="user.id")


# ============================================
# INDICATEURS DE PERFORMANCE
# ============================================


class IndicateurPerformance(SQLModel, table=True):
    """Indicateurs clés de performance (KPIs)"""

    __tablename__ = "indicateur_performance"

    id: int | None = Field(default=None, primary_key=True)

    # Informations générales
    nom: str = Field(max_length=200, index=True)
    description: str | None = None
    formule_calcul: str | None = None

    # Classification
    categorie: str = Field(max_length=100)  # "Qualité", "Efficacité", "RH", "Commercial"
    type_indicateur: str = Field(max_length=50)  # "Pourcentage", "Nombre", "Montant", "Temps"

    # Valeurs et seuils
    valeur_cible: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)
    valeur_actuelle: Decimal | None = Field(default=0, max_digits=15, decimal_places=2)
    unite: str = Field(max_length=50)

    # Seuils d'alerte
    seuil_alerte_bas: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)
    seuil_alerte_haut: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)

    # Fréquence de mise à jour
    frequence_maj: str = Field(max_length=50)  # "Quotidien", "Hebdomadaire", "Mensuel", "Trimestriel"

    # Responsabilité
    responsable_id: int = Field(foreign_key="user.id")
    service_responsable: str | None = Field(default=None, max_length=100)

    # Source de données
    source_donnees: str | None = Field(default=None, max_length=200)

    # Commentaires
    commentaires: str | None = None

    # Statut
    actif: bool = Field(default=True)

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_id: int = Field(foreign_key="user.id")


# ============================================
# PROGRAMMES DE PERFORMANCE
# ============================================


class ProgrammePerformance(SQLModel, table=True):
    """Programmes de performance organisationnelle"""

    __tablename__ = "programme_performance"

    id: int | None = Field(default=None, primary_key=True)

    # Informations générales
    nom: str = Field(max_length=200, index=True)
    description: str | None = None

    # Période
    date_debut: date = Field(default_factory=date.today)
    date_fin: date | None = None

    # Statut
    statut: str = Field(max_length=50, default="ACTIF")  # "ACTIF", "TERMINE", "SUSPENDU"

    # Responsabilité
    responsable_id: int = Field(foreign_key="user.id")

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_id: int = Field(foreign_key="user.id")


# ============================================
# ÉVALUATIONS DE PERFORMANCE
# ============================================


class EvaluationPerformance(SQLModel, table=True):
    """Évaluations de performance"""

    __tablename__ = "evaluation_performance"

    id: int | None = Field(default=None, primary_key=True)

    # Informations générales
    titre: str = Field(max_length=200, index=True)
    description: str | None = None

    # Période d'évaluation
    periode_evaluation: str = Field(max_length=50)  # "2025", "Q1 2025"
    date_debut: date
    date_fin: date

    # Type d'évaluation
    type_evaluation: str = Field(max_length=50)  # "INDIVIDUELLE", "EQUIPE", "ORGANISATIONNELLE"

    # Statut
    statut: str = Field(max_length=50, default="PLANIFIEE")  # "PLANIFIEE", "EN_COURS", "TERMINEE"

    # Responsabilité
    responsable_id: int = Field(foreign_key="user.id")

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_id: int = Field(foreign_key="user.id")


# ============================================
# RAPPORTS DE PERFORMANCE
# ============================================


class RapportPerformance(SQLModel, table=True):
    """Historique des rapports de performance générés"""

    __tablename__ = "rapport_performance"

    id: int | None = Field(default=None, primary_key=True)

    # Informations du rapport
    titre: str = Field(max_length=200, index=True)
    description: str | None = None

    # Type et format
    type_rapport: str = Field(max_length=50)  # "GLOBAL", "OBJECTIFS", "INDICATEURS", "SYNTHESE"
    format_fichier: str = Field(max_length=20)  # "PDF", "EXCEL", "POWERPOINT", "HTML"

    # Période couverte
    periode: str = Field(max_length=50)  # "CURRENT_MONTH", "LAST_QUARTER", etc.
    date_debut: date
    date_fin: date

    # Chemin du fichier généré
    fichier_path: str | None = Field(max_length=500)
    fichier_nom: str = Field(max_length=200)
    fichier_taille: int | None = None  # Taille en octets

    # Statistiques du rapport
    nb_objectifs: int | None = Field(default=0)
    nb_indicateurs: int | None = Field(default=0)
    taux_realisation: Decimal | None = Field(default=0, max_digits=5, decimal_places=2)

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    created_by_id: int = Field(foreign_key="user.id")
    created_by_nom: str | None = Field(max_length=200)
