"""
Modèle de session utilisateur
Permet la gestion de multiples sessions simultanées par utilisateur
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
import secrets


class UserSession(SQLModel, table=True):
    """
    Session utilisateur pour gérer les connexions multiples
    
    Permet à un utilisateur d'avoir plusieurs sessions actives
    (ex: ordinateur bureau + mobile + ordinateur maison)
    """
    __tablename__ = "user_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Clé de session unique (stockée dans le cookie)
    session_token: str = Field(unique=True, index=True, max_length=255)
    
    # Utilisateur associé
    user_id: int = Field(foreign_key="user.id", index=True)
    
    # Informations de la session
    ip_address: Optional[str] = Field(default=None, max_length=45)  # IPv6 max length
    user_agent: Optional[str] = Field(default=None, max_length=500)
    device_info: Optional[str] = Field(default=None, max_length=255)  # Ex: "Chrome on Windows"
    
    # Gestion temporelle
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(days=7))
    
    # État de la session
    is_active: bool = Field(default=True)
    
    # Relation vers l'utilisateur
    # user: "User" = Relationship(back_populates="sessions")
    
    @staticmethod
    def generate_token() -> str:
        """Génère un token de session sécurisé"""
        return secrets.token_urlsafe(32)
    
    def is_expired(self) -> bool:
        """Vérifie si la session est expirée"""
        return datetime.now() > self.expires_at
    
    def refresh(self, days: int = 7):
        """Rafraîchit la session (met à jour last_activity et extends expiration)"""
        self.last_activity = datetime.now()
        self.expires_at = datetime.now() + timedelta(days=days)
    
    def deactivate(self):
        """Désactive la session (logout)"""
        self.is_active = False


__all__ = ["UserSession"]

