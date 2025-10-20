from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.enums import UserType


class User(SQLModel, table=True):
    """
    Modèle utilisateur

    Attributes:
        id: Identifiant unique
        email: Email unique (login)
        full_name: Nom complet
        hashed_password: Mot de passe hashé (bcrypt)
        is_active: Compte actif ou non
        is_superuser: Droits superuser (pour rétrocompatibilité)
        type_user: Type d'utilisateur (admin, user, moderator, guest)
        created_at: Date de création
        updated_at: Date de dernière modification
    """

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str | None = None
    hashed_password: str
    profile_picture: str | None = Field(default=None, max_length=500)  # Chemin vers la photo
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)  # Rétrocompatibilité
    type_user: str = Field(default=UserType.USER)  # Stocké comme VARCHAR

    # Lien avec AgentComplet (optionnel - un user peut être lié à un agent)
    agent_id: int | None = Field(default=None, foreign_key="agent_complet.id", index=True)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_admin(self) -> bool:
        """Vérifie si l'utilisateur est admin"""
        return self.type_user == UserType.ADMIN or self.is_superuser

    @property
    def is_moderator(self) -> bool:
        """Vérifie si l'utilisateur est modérateur"""
        return self.type_user == UserType.MODERATOR
