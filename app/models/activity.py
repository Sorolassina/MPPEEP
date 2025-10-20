"""
Modèle pour les activités récentes du système
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Activity(SQLModel, table=True):
    """
    Activités récentes du système

    Attributes:
        id: Identifiant unique
        user_id: ID de l'utilisateur qui a fait l'action
        user_email: Email de l'utilisateur (pour affichage)
        action_type: Type d'action (create, update, delete, login, etc.)
        target_type: Type de cible (user, settings, etc.)
        target_id: ID de la cible (optionnel)
        description: Description de l'action
        icon: Icône emoji pour l'affichage
        created_at: Date et heure de l'action
    """

    __tablename__ = "activity"

    id: int | None = Field(default=None, primary_key=True)

    # Utilisateur qui a fait l'action
    user_id: int | None = Field(default=None, index=True)
    user_email: str = Field(max_length=255)
    user_full_name: str | None = Field(default=None, max_length=255)

    # Type d'action
    action_type: str = Field(max_length=50, index=True)  # create, update, delete, login, logout, etc.
    target_type: str = Field(max_length=50)  # user, settings, session, etc.
    target_id: int | None = Field(default=None)

    # Description et affichage
    description: str = Field(max_length=500)
    icon: str = Field(default="📝", max_length=10)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.now, index=True)

    def __repr__(self):
        return f"<Activity {self.action_type} on {self.target_type} by {self.user_email}>"
