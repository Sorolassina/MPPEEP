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
    type_user: str = Field(default=UserType.AGENT)  # Stocké comme VARCHAR

    # Lien avec AgentComplet (optionnel - un user peut être lié à un agent)
    agent_id: int | None = Field(default=None, foreign_key="agent_complet.id", index=True)
    
    # Charte de confidentialité
    privacy_policy_accepted: bool = Field(default=False)
    privacy_policy_accepted_at: datetime | None = Field(default=None)
    privacy_policy_version: str | None = Field(default=None, max_length=20)

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
    
    @property
    def is_direction(self) -> bool:
        """Vérifie si l'utilisateur est d'une direction"""
        from app.core.permissions import PermissionManager
        return PermissionManager.is_direction(self.type_user)
    
    def has_permission(self, permission: str) -> bool:
        """Vérifie si l'utilisateur a une permission spécifique"""
        from app.core.permissions import PermissionManager
        return PermissionManager.has_permission(self.type_user, permission)
    
    def can_access_module(self, module: str) -> bool:
        """Vérifie si l'utilisateur peut accéder à un module"""
        from app.core.permissions import PermissionManager
        return PermissionManager.can_access_module(self.type_user, module)
    
    def get_accessible_modules(self) -> list:
        """Récupère la liste des modules accessibles"""
        from app.core.permissions import PermissionManager
        return PermissionManager.get_accessible_modules(self.type_user)
    
    @property
    def is_guest(self) -> bool:
        """Vérifie si l'utilisateur est un invité (mode MVP)"""
        from app.core.permissions import PermissionManager
        return PermissionManager.is_guest(self.type_user)
    
    def can_view_data(self) -> bool:
        """Vérifie si l'utilisateur peut voir les données réelles"""
        from app.core.permissions import PermissionManager
        return PermissionManager.can_view_data(self.type_user)
    
    def can_perform_crud(self) -> bool:
        """Vérifie si l'utilisateur peut effectuer des opérations CRUD"""
        from app.core.permissions import PermissionManager
        return PermissionManager.can_perform_crud(self.type_user)