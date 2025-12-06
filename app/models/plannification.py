# app/models/plannification.py
"""
Modèles de données pour le module Plannification
"""

from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import String, Text
from sqlmodel import Field, SQLModel, Column


# ============================================
# ENUMS
# ============================================


class TypeEvenement(str, Enum):
    """Types d'événements"""

    REUNION = "REUNION"
    FORMATION = "FORMATION"
    ACTIVITE = "ACTIVITE"
    DEADLINE = "DEADLINE"
    AUTRE = "AUTRE"


class StatutEvenement(str, Enum):
    """Statuts possibles pour un événement"""

    PLANIFIE = "PLANIFIE"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"


class PrioriteEvenement(str, Enum):
    """Priorités d'un événement"""

    BASSE = "BASSE"
    NORMALE = "NORMALE"
    HAUTE = "HAUTE"
    URGENTE = "URGENTE"


# ============================================
# MODÈLES
# ============================================


class EvenementPlannification(SQLModel, table=True):
    """
    Événement de planification affiché sur le calendrier
    """

    __tablename__ = "evenement_plannification"

    id: int | None = Field(default=None, primary_key=True)

    # Informations de base
    titre: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    type_evenement: str = Field(default=TypeEvenement.AUTRE, max_length=50)
    statut: str = Field(default=StatutEvenement.PLANIFIE, max_length=50)
    priorite: str = Field(default=PrioriteEvenement.NORMALE, max_length=50)

    # Dates et heures
    date_debut: date = Field(index=True)
    heure_debut: time | None = Field(default=None)
    date_fin: date | None = Field(default=None, index=True)
    heure_fin: time | None = Field(default=None)
    journee_entiere: bool = Field(default=False)  # Si True, ignore les heures

    # Localisation
    lieu: str | None = Field(default=None, max_length=255)

    # Participants et responsables
    responsable_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    participants: str | None = Field(default=None, sa_column=Column(Text))  # Liste séparée par virgules ou JSON

    # Rappels
    rappel_actif: bool = Field(default=False)
    rappel_avant_jours: int | None = Field(default=None)  # Nombre de jours avant l'événement
    rappel_avant_heures: int | None = Field(default=None)  # Nombre d'heures avant l'événement

    # Couleur pour l'affichage dans le calendrier
    couleur: str | None = Field(default=None, max_length=7)  # Code hexadécimal (ex: #FF5733)

    # Répétition (optionnel, pour événements récurrents)
    recurrence: str | None = Field(default=None, max_length=50)  # "JOUR", "SEMAINE", "MOIS", "ANNEE", "CUSTOM"
    recurrence_fin: date | None = Field(default=None)  # Date de fin de la récurrence
    recurrence_config: str | None = Field(default=None, sa_column=Column(Text))  # Configuration JSON pour récurrence custom

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_id: int = Field(foreign_key="user.id")
    updated_by_id: int | None = Field(default=None, foreign_key="user.id")

