# app/models/besoins.py
"""
Modèles pour la gestion des besoins en agents
Permet de suivre les besoins exprimés par les services, directions et programmes
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel


class BesoinAgent(SQLModel, table=True):
    """
    Besoin en agent exprimé par un service
    Peut être regroupé au niveau direction puis programme
    """

    __tablename__ = "besoin_agent"

    id: int | None = Field(default=None, primary_key=True)

    # Période du besoin
    annee: int = Field(index=True)  # Année du besoin (ex: 2025)
    periode: str | None = Field(max_length=50)  # Ex: "Trimestre 1", "Semestre 1"

    # Hiérarchie organisationnelle
    service_id: int | None = Field(default=None, foreign_key="service.id")
    direction_id: int | None = Field(default=None, foreign_key="direction.id")
    programme_id: int | None = Field(default=None, foreign_key="programme.id")

    # Description du besoin
    poste_libelle: str = Field(max_length=200)  # Ex: "Secrétaire de Direction"
    grade_id: int | None = Field(default=None, foreign_key="grade_complet.id")  # Grade souhaité
    categorie_souhaitee: str | None = Field(max_length=1)  # A, B, C, D

    # Quantité
    nombre_demande: int = Field(default=1)  # Nombre d'agents demandés
    nombre_obtenu: int = Field(default=0)  # Nombre d'agents effectivement obtenus

    # Justification
    motif: str | None = None  # Raison du besoin
    urgence: str | None = Field(max_length=20, default="Normale")  # Faible, Normale, Élevée, Critique

    # Statut
    statut: str = Field(
        max_length=50, default="Exprimé"
    )  # Exprimé, Transmis, En attente, Partiellement satisfait, Satisfait, Rejeté

    # Dates
    date_expression: date = Field(default_factory=date.today)  # Date où le besoin est exprimé
    date_transmission: date | None = None  # Date de transmission au ministère
    date_satisfaction: date | None = None  # Date où le besoin est satisfait

    # Metadata
    exprime_par_user_id: int | None = Field(default=None, foreign_key="user.id")  # Qui a exprimé le besoin
    valide_par_user_id: int | None = Field(default=None, foreign_key="user.id")  # Qui a validé

    observations: str | None = None  # Commentaires/notes

    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SuiviBesoin(SQLModel, table=True):
    """
    Historique des changements de statut d'un besoin
    Permet de tracer l'évolution du besoin
    """

    __tablename__ = "suivi_besoin"

    id: int | None = Field(default=None, primary_key=True)
    besoin_id: int = Field(foreign_key="besoin_agent.id")

    # Changement
    ancien_statut: str | None = Field(max_length=50)
    nouveau_statut: str = Field(max_length=50)

    nombre_obtenu_avant: int = Field(default=0)
    nombre_obtenu_apres: int = Field(default=0)

    # Auteur du changement
    modifie_par_user_id: int | None = Field(default=None, foreign_key="user.id")

    commentaire: str | None = None
    date_modification: datetime = Field(default_factory=datetime.utcnow)


class ConsolidationBesoin(SQLModel, table=True):
    """
    Vue consolidée des besoins au niveau Direction ou Programme
    Permet d'avoir une vue d'ensemble
    """

    __tablename__ = "consolidation_besoin"

    id: int | None = Field(default=None, primary_key=True)

    # Période
    annee: int = Field(index=True)
    periode: str | None = Field(max_length=50)

    # Niveau de consolidation
    niveau: str = Field(max_length=20)  # "Service", "Direction", "Programme", "Ministère"
    direction_id: int | None = Field(default=None, foreign_key="direction.id")
    programme_id: int | None = Field(default=None, foreign_key="programme.id")

    # Agrégats
    total_demande: int = Field(default=0)
    total_obtenu: int = Field(default=0)
    taux_satisfaction: Decimal | None = Field(default=None, max_digits=5, decimal_places=2)  # Pourcentage

    # Par catégorie
    demande_cat_a: int = Field(default=0)
    obtenu_cat_a: int = Field(default=0)
    demande_cat_b: int = Field(default=0)
    obtenu_cat_b: int = Field(default=0)
    demande_cat_c: int = Field(default=0)
    obtenu_cat_c: int = Field(default=0)
    demande_cat_d: int = Field(default=0)
    obtenu_cat_d: int = Field(default=0)

    # Statut de la consolidation
    statut: str = Field(max_length=50, default="En cours")  # En cours, Transmis, Clôturé
    date_consolidation: datetime = Field(default_factory=datetime.utcnow)

    observations: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
