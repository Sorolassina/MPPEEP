# app/models/performance.py
"""
Modèles de données pour le module Performance
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import String
from sqlmodel import Field, SQLModel, Column

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

    GLOBAL = "global"  # Objectif Global (lié à un résultat stratégique)
    SPECIFIQUE = "specifique"  # Objectif Spécifique (lié à un objectif global)
    FINANCIER = "FINANCIER"
    RH = "RH"
    QUALITE = "QUALITE"
    CLIENT = "CLIENT"


class ModeCollecteDonnees(str, Enum):
    """Modes de collecte des données pour les indicateurs"""

    ROUTINE = "routine"
    ENQUETE = "enquête"
    AUTRES = "autres"


class SensAppreciation(str, Enum):
    """Sens d'appréciation d'un indicateur"""

    HAUT = "haut"  # Plus le taux est élevé, plus on est satisfait
    BAS = "bas"  # Plus le taux est bas, plus on est satisfait


# ============================================
# ORIENTATIONS STRATÉGIQUES
# ============================================


class OrientationStrategique(SQLModel, table=True):
    """Orientations stratégiques du ministère"""

    __tablename__ = "orientation_strategique"

    id: int | None = Field(default=None, primary_key=True)

    # Informations générales
    libelle: str = Field(max_length=500, index=True)  # Libellé de l'orientation stratégique
    description: str | None = None

    # Ordre d'affichage
    ordre: int | None = Field(default=None, index=True)  # Ordre d'affichage

    # Valeur actuelle (calculée automatiquement comme moyenne des RS)
    valeur_actuelle: Decimal | None = Field(default=0, max_digits=15, decimal_places=2)

    # Statut
    actif: bool = Field(default=True, index=True)

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_id: int = Field(foreign_key="user.id")


# ============================================
# RÉSULTATS STRATÉGIQUES
# ============================================


class ResultatStrategique(SQLModel, table=True):
    """Résultats stratégiques liés aux orientations stratégiques"""

    __tablename__ = "resultat_strategique"

    id: int | None = Field(default=None, primary_key=True)

    # Relation avec l'orientation stratégique
    orientation_id: int = Field(foreign_key="orientation_strategique.id", index=True)

    # Informations générales
    libelle: str = Field(max_length=500, index=True)  # Libellé du résultat stratégique
    description: str | None = None

    # Ordre d'affichage
    ordre: int | None = Field(default=None, index=True)  # Ordre d'affichage au sein de l'orientation

    # Valeur actuelle (calculée automatiquement comme moyenne des OG)
    valeur_actuelle: Decimal | None = Field(default=0, max_digits=15, decimal_places=2)

    # Statut
    actif: bool = Field(default=True, index=True)

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_id: int = Field(foreign_key="user.id")


# ============================================
# OBJECTIFS DE PERFORMANCE
# ============================================


class ObjectifPerformance(SQLModel, table=True):
    """Objectifs de performance organisationnelle"""

    __tablename__ = "objectif_performance"

    id: int | None = Field(default=None, primary_key=True)

    # Informations générales
    code: str | None = Field(default=None, max_length=50, index=True)  # Code de l'objectif (ex: OG01, OS01)
    titre: str = Field(max_length=200, index=True)
    description: str | None = None

    # Classification
    # Stocké en string dans la DB, mais validé avec l'enum Python côté backend
    type_objectif: str = Field(
        default=TypeObjectif.SPECIFIQUE.value,
        sa_column=Column(String(50), default=TypeObjectif.SPECIFIQUE.value)
    )
    priorite: PrioriteObjectif = Field(default=PrioriteObjectif.NORMALE)

    # Relations hiérarchiques
    # Pour les objectifs globaux (type GLOBAL) : lié à un résultat stratégique et optionnellement à un programme
    resultat_strategique_id: int | None = Field(default=None, foreign_key="resultat_strategique.id", index=True)
    programme_id: int | None = Field(default=None, foreign_key="programme.id", index=True)  # Programme associé (pour les OG)
    # Pour les objectifs spécifiques (type SPECIFIQUE) : lié à un objectif global (GLOBAL)
    objectif_global_id: int | None = Field(default=None, foreign_key="objectif_performance.id", index=True)

    # Période et échéances
    date_debut: date = Field(default_factory=date.today)
    date_fin: date
    periode: str = Field(max_length=50)  # "2025", "Q1 2025", "Janvier 2025"

    # Valeurs et objectifs
    valeur_cible: Decimal = Field(max_digits=15, decimal_places=2)
    valeur_actuelle: Decimal | None = Field(default=0, max_digits=15, decimal_places=2)
    unite: str = Field(max_length=50)  # "%", "€", "nombre", "heures"

    # Responsabilité
    responsable_id: int | None = Field(default=None, foreign_key="user.id")
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

    # Relation avec l'objectif (OBLIGATOIRE)
    objectif_id: int = Field(foreign_key="objectif_performance.id", index=True)

    # Informations générales
    nom: str = Field(max_length=200, index=True)
    description: str | None = None
    formule_calcul: str | None = None

    # Classification
    categorie: str = Field(max_length=100)  # "Qualité", "Efficacité", "RH", "Commercial"
    type_indicateur: str = Field(max_length=50)  # "Pourcentage", "Nombre", "Montant", "Temps"

    # Année de référence (permet d'avoir des valeurs historiques : N, N-1, N-2, etc.)
    annee: int = Field(index=True)  # Année de l'indicateur (ex: 2024, 2023, 2022)

    # Valeurs et seuils
    valeur_cible: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)  # Prévision pour cette année
    valeur_actuelle: Decimal | None = Field(default=0, max_digits=15, decimal_places=2)  # Réalisation pour cette année
    unite: str = Field(max_length=50)

    # Nombre d'activités (optionnel, pour certains indicateurs comme le taux de réalisation du PTA)
    nb_activites: int | None = Field(default=None)  # Nombre d'activités réalisées (ex: 15)

    # Valeurs cibles futures (format texte : "100% en 2024, 100% en 2025, 100% en 2026")
    valeurs_cibles_futures: str | None = Field(default=None, max_length=500)
    
    # Cibles pour les années suivantes
    cible_N_plus_1: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=2, sa_column_kwargs={"name": "cible_n_plus_1"}
    )  # Cible pour N+1
    cible_N_plus_2: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=2, sa_column_kwargs={"name": "cible_n_plus_2"}
    )  # Cible pour N+2

    # Seuils d'alerte
    seuil_alerte_bas: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)
    seuil_alerte_haut: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)

    # Fréquence de mise à jour
    frequence_maj: str = Field(max_length=50)  # "Quotidien", "Hebdomadaire", "Mensuel", "Trimestriel"

    # Responsabilité
    responsable_id: int | None = Field(default=None, foreign_key="user.id")
    service_responsable: str | None = Field(default=None, max_length=100)

    # Source de données
    source_donnees: str | None = Field(default=None, max_length=200)

    # Méthode et collecte des données
    methode: str | None = Field(default=None, max_length=500)  # Méthode de calcul/évaluation
    mode_collecte_donnees: str | None = Field(default=None, max_length=50)  # routine, enquête, autres
    derniere_valeur_connue: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)  # Dernière valeur connue
    
    # Sens d'appréciation
    sens_appreciation: str | None = Field(
        default=SensAppreciation.HAUT.value,
        max_length=10,
        sa_column=Column(String(10), default=SensAppreciation.HAUT.value)
    )  # "haut" = plus élevé = mieux, "bas" = plus bas = mieux
    
    # Document justificatif
    doc_justif: str | None = Field(default=None, max_length=500)  # Chemin du document justifiant la valeur actuelle

    # Commentaires
    commentaires: str | None = None

    # Statut
    actif: bool = Field(default=True)

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
    responsable_id: int | None = Field(default=None, foreign_key="user.id")

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
