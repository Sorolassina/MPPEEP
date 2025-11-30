"""
Modèle pour les données du Rapport Annuel de Performance (RAP)
"""

from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class RapData(SQLModel, table=True):
    """
    Données spécifiques au Rapport Annuel de Performance (RAP)
    Singleton - toujours ID 1
    """

    __tablename__ = "rap_data"

    id: int = Field(default=1, primary_key=True)  # Singleton - toujours ID 1

    # Contexte et structure du rapport
    contexte_texte: str | None = Field(default=None, sa_column=Column(Text))  # Texte de contexte pour l'introduction générale
    rapport_structure_premiere_partie: str | None = Field(default=None, sa_column=Column(Text))  # Structure première partie (JSON)
    rapport_structure_seconde_partie: str | None = Field(default=None, sa_column=Column(Text))  # Structure seconde partie (JSON)
    
    # Informations générales du rapport
    titre_rapport: str | None = Field(default=None, sa_column=Column(Text))  # Titre complet du rapport
    titre_annee: str | None = Field(default=None, max_length=100)  # Titre de l'année (ex: "AU TITRE DE L'ANNÉE")
    annee: int | None = Field(default=None)  # Année de référence du rapport
    date_publication: str | None = Field(default=None, max_length=50)  # Date de publication (format: "YYYY-MM" ou "Mois AAAA")
    
    # Politique ministérielle - Orientations stratégiques
    orientations_strategiques: str | None = Field(default=None, sa_column=Column(Text))  # Orientations stratégiques (JSON: liste de {orientation, resultat, objectif})
    
    # Financement global du ministère - Interprétations personnalisées
    financement_interpretations: str | None = Field(default=None, sa_column=Column(Text))  # Interprétations personnalisées du financement (JSON)
    
    # Conclusion et points positifs - Interprétations personnalisées
    conclusion_interpretations: str | None = Field(default=None, sa_column=Column(Text))  # Points positifs, difficultés, recommandations et conclusion (JSON)
    
    # Conclusion générale du rapport
    conclusion_generale: str | None = Field(default=None, sa_column=Column(Text))  # Conclusion générale (JSON: {intro, performance_indicators, budget_execution, avancees, limites, perspectives})

    # Métadonnées
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_user_id: int | None = Field(default=None)

    def update_timestamp(self, user_id: int):
        """Met à jour le timestamp et l'utilisateur qui a modifié"""
        self.updated_at = datetime.now()
        self.updated_by_user_id = user_id

