"""
Modèle pour les données du Rapport d'Activité RPROG
"""

from datetime import datetime

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class RprogData(SQLModel, table=True):
    """
    Données spécifiques au Rapport d'Activité RPROG
    Un rapport est identifié UNIQUEMENT par programme_id
    Une seule ligne par programme (les données précédentes sont écrasées à chaque sauvegarde)
    """

    __tablename__ = "rprog_data"
    __table_args__ = (
        UniqueConstraint("programme_id", name="uq_rprog_programme"),
    )

    id: int = Field(primary_key=True)

    # Clé unique pour identifier un rapport par programme
    programme_id: int = Field(foreign_key="programme.id", index=True, unique=True)
    
    # Année et période sont stockées mais ne font pas partie de la clé unique
    # Elles peuvent être mises à jour à chaque sauvegarde
    annee: int | None = Field(default=None, index=True)
    periode: str | None = Field(default=None, max_length=100, index=True)  # "PREMIER SEMESTRE", "DEUXIÈME SEMESTRE", "ANNÉE COMPLÈTE"

    # ===== ONGLET 1: INFORMATIONS GÉNÉRALES =====
    titre_rapport: str | None = Field(default=None, sa_column=Column(Text))
    section: str | None = Field(default=None, max_length=200)
    ministere: str | None = Field(default=None, sa_column=Column(Text))
    date_publication: str | None = Field(default=None, max_length=50)
    responsable_programme: str | None = Field(default=None, max_length=200)
    logo_path: str | None = Field(default=None, max_length=500)

    # ===== ONGLET 2: ACTIVITÉS =====
    activites_commentaires: str | None = Field(default=None, sa_column=Column(Text))  # Commentaires personnalisés sur les activités

    # ===== ONGLET 3: CRÉDITS BUDGÉTAIRES =====
    credits_commentaires: str | None = Field(default=None, sa_column=Column(Text))  # Commentaires personnalisés sur les crédits

    # ===== ONGLET 4: INVESTISSEMENTS =====
    investissements_commentaires: str | None = Field(default=None, sa_column=Column(Text))  # Commentaires personnalisés sur les investissements

    # ===== ONGLET 5: EFFECTIFS =====
    effectifs_commentaires: str | None = Field(default=None, sa_column=Column(Text))  # Commentaires personnalisés sur les effectifs

    # ===== ONGLET 6: PERFORMANCE =====
    performance_commentaires: str | None = Field(default=None, sa_column=Column(Text))  # Commentaires personnalisés sur la performance

    # ===== ONGLET 7: DIFFICULTÉS ET SOLUTIONS =====
    difficultes_rencontrees: str | None = Field(default=None, sa_column=Column(Text))  # JSON: liste de difficultés
    actions_solutions: str | None = Field(default=None, sa_column=Column(Text))  # JSON: liste d'actions/solutions
    difficultes_intro: str | None = Field(default=None, sa_column=Column(Text))  # Texte d'introduction personnalisé pour les difficultés
    solutions_intro: str | None = Field(default=None, sa_column=Column(Text))  # Texte d'introduction personnalisé pour les solutions

    # ===== CONCLUSION =====
    conclusion_texte: str | None = Field(default=None, sa_column=Column(Text))  # Texte de conclusion personnalisé

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_user_id: int | None = Field(default=None)

    def update_timestamp(self, user_id: int):
        """Met à jour le timestamp et l'utilisateur qui a modifié"""
        self.updated_at = datetime.now()
        self.updated_by_user_id = user_id

