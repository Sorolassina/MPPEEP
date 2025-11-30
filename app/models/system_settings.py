"""
Modèle pour les paramètres système
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


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
    company_description: str | None = Field(default=None)
    company_email: str | None = Field(default=None)
    company_phone: str | None = Field(default=None)
    company_address: str | None = Field(default=None)

    # Apparence
    logo_path: str | None = Field(default="images/logo.webp")
    primary_color: str = Field(default="#ffd300")
    secondary_color: str = Field(default="#036c1d")
    accent_color: str = Field(default="#e63600")
    minister_photo: str | None = Field(default="images/utilisateur.png")
    minister_civility: str | None = Field(default="Monsieur")
    minister_name: str | None = Field(default=None)
    minister_role: str | None = Field(default=None)
    ministry_mission: str | None = Field(default=None)  # Mission du ministère
    minister_nomination_date: str | None = Field(default=None)  # Date de nomination du ministre (ex: "17 octobre 2023")
    decret_attribution_numero: str | None = Field(default=None)  # Numéro du décret d'attribution (ex: "n° 2023-820")
    decret_attribution_date: str | None = Field(default=None)  # Date du décret d'attribution (ex: "25 octobre 2023")
    
    # Structure organisationnelle
    structure_cabinet: str | None = Field(default=None)  # Nom du cabinet (ex: "Cabinet du Ministre")
    nb_directions_centrales: int | None = Field(default=None)  # Nombre de directions centrales
    nb_services: int | None = Field(default=None)  # Nombre de services
    nb_directions_generales: int | None = Field(default=None)  # Nombre de directions générales
    decret_organisation_numero: str | None = Field(default=None)  # Numéro du décret d'organisation (ex: "n° 2023-963")
    decret_organisation_date: str | None = Field(default=None)  # Date du décret d'organisation (ex: "6 décembre 2023")
    
    # Informations pays/devise
    pays: str | None = Field(default=None)  # Nom du pays (ex: "République de Côte d'Ivoire")
    devise: str | None = Field(default=None)  # Devise nationale (ex: "Union – Discipline – Travail")
    section: str | None = Field(default=None)  # Section administrative (ex: "SECTION 376")

    # Personnalisation
    footer_text: str | None = Field(default="Tous droits réservés")

    # Paramètres système
    maintenance_mode: bool = Field(default=False)
    allow_registration: bool = Field(default=False)
    max_upload_size_mb: int = Field(default=10)
    session_timeout_minutes: int = Field(default=30)

    # Métadonnées
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by_user_id: int | None = Field(default=None)

    def update_timestamp(self, user_id: int):
        """Met à jour le timestamp et l'utilisateur qui a modifié"""
        self.updated_at = datetime.now()
        self.updated_by_user_id = user_id
