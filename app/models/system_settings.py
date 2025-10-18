"""
Modèle pour les paramètres système
"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class SystemSettings(SQLModel, table=True):
    """
    Paramètres système de l'application
    
    Attributes:
        id: Identifiant unique (toujours 1 - singleton)
        company_name: Nom de l'entreprise
        company_description: Description de l'entreprise
        company_email: Email de contact
        company_phone: Téléphone de contact
        company_address: Adresse de l'entreprise
        logo_path: Chemin vers le logo
        primary_color: Couleur principale (hex)
        secondary_color: Couleur secondaire (hex)
        accent_color: Couleur d'accentuation (hex)
        footer_text: Texte personnalisé du footer
        maintenance_mode: Mode maintenance activé/désactivé
        allow_registration: Autoriser les nouvelles inscriptions
        max_upload_size_mb: Taille max des uploads en MB
        session_timeout_minutes: Durée de session en minutes
        updated_at: Date de dernière modification
        updated_by_user_id: ID de l'utilisateur qui a fait la modification
    """
    __tablename__ = "system_settings"
    
    id: int = Field(default=1, primary_key=True)  # Singleton - toujours ID 1
    
    # Informations entreprise
    company_name: str = Field(default="MPPEEP Dashboard")  # Sera remplacé par APP_NAME au runtime
    company_description: Optional[str] = Field(default=None)
    company_email: Optional[str] = Field(default=None)
    company_phone: Optional[str] = Field(default=None)
    company_address: Optional[str] = Field(default=None)
    
    # Apparence
    logo_path: Optional[str] = Field(default="images/logo.webp")
    primary_color: str = Field(default="#ffd300")
    secondary_color: str = Field(default="#036c1d")
    accent_color: str = Field(default="#e63600")
    
    # Personnalisation
    footer_text: Optional[str] = Field(default="Tous droits réservés")
    
    # Paramètres système
    maintenance_mode: bool = Field(default=False)
    allow_registration: bool = Field(default=False)
    max_upload_size_mb: int = Field(default=10)
    session_timeout_minutes: int = Field(default=30)
    
    # Métadonnées
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_user_id: Optional[int] = Field(default=None)
    
    def update_timestamp(self, user_id: int):
        """Met à jour le timestamp et l'utilisateur qui a modifié"""
        self.updated_at = datetime.now()
        self.updated_by_user_id = user_id

