"""
Modèle pour les données du Rapport du Cadre de Performance (CP)
"""

from datetime import datetime

from sqlalchemy import Column, Text, JSON
from sqlmodel import Field, SQLModel


class CPData(SQLModel, table=True):
    """
    Données spécifiques au Rapport du Cadre de Performance (CP)
    Une seule ligne par programme (les données précédentes sont écrasées à chaque sauvegarde)
    """

    __tablename__ = "cp_data"

    id: int = Field(primary_key=True)

    # Clé unique pour identifier un rapport par programme
    programme_id: int = Field(foreign_key="programme.id", index=True, unique=True)
    
    # Année de début et fin de la période
    annee_debut: int | None = Field(default=None, index=True)
    annee_fin: int | None = Field(default=None, index=True)

    # ===== ONGLET GENERAL =====
    titre_rapport: str | None = Field(default=None, sa_column=Column(Text))
    section: str | None = Field(default=None, max_length=200)
    ministere: str | None = Field(default=None, sa_column=Column(Text))
    logo_path: str | None = Field(default=None, max_length=500)

    # ===== ONGLET CADRE GLOBALE =====
    cadre_global_commentaire: str | None = Field(default=None, sa_column=Column(Text))
    organisme_tutelle_directe: str | None = Field(default=None, sa_column=Column(Text))
    organisme_prive_ong: str | None = Field(default=None, sa_column=Column(Text))
    projets_hors_pip: str | None = Field(default=None, sa_column=Column(Text))
    tableau_2_commentaire: str | None = Field(default=None, sa_column=Column(Text))

    # ===== ONGLET CADRE PROGRAMME =====
    cp_programme_commentaire: str | None = Field(default=None, sa_column=Column(Text))
    cp_cadre_performance_commentaire: str | None = Field(default=None, sa_column=Column(Text))

    # ===== ONGLET MODIFICATION ARCHITECTURE =====
    # Stockage des modifications d'architecture sous forme JSON
    # Format: [
    #   {
    #     "type": "programme|action|activite",
    #     "code_ancien": "...",
    #     "libelle_ancien": "...",
    #     "code_nouveau": "...",
    #     "libelle_nouveau": "...",
    #     "annee_periode": "2025-2027|2026-2028"
    #   },
    #   ...
    # ]
    modifications_architecture: str | None = Field(default=None, sa_column=Column(JSON))

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_user_id: int | None = Field(default=None)

    def update_timestamp(self, user_id: int):
        """Met à jour le timestamp et l'utilisateur qui a modifié"""
        self.updated_at = datetime.now()
        self.updated_by_user_id = user_id

