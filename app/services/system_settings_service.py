"""
Service pour la gestion des paramètres système
"""
from sqlmodel import Session, select
from typing import Optional, Dict
from pathlib import Path

from app.models.system_settings import SystemSettings
from app.core.logging_config import get_logger
from app.core.path_config import path_config
from app.core.settings_cache import settings_cache
from app.core.config import settings as app_settings

logger = get_logger(__name__)


class SystemSettingsService:
    """Service de gestion des paramètres système"""
    
    @staticmethod
    def get_settings(db_session: Session) -> SystemSettings:
        """
        Récupère les paramètres système (singleton)
        Si aucun paramètre n'existe, en crée un avec valeurs par défaut depuis la config
        
        Args:
            db_session: Session de base de données
        
        Returns:
            Les paramètres système
        """
        settings = db_session.get(SystemSettings, 1)
        
        if not settings:
            # Créer les paramètres par défaut complets
            settings = SystemSettings(
                id=1,
                company_name=app_settings.APP_NAME,
                company_description="Système de gestion intégré",
                company_email="contact@mppeep.com",
                company_phone="+225 00 00 00 00 00",
                company_address="Abidjan, Côte d'Ivoire",
                logo_path="images/logo_default.png",  # Détection auto via get_logo_url()
                primary_color="#f77902",      # Orange
                secondary_color="#038c25",    # Vert
                accent_color="#fcc603",       # Jaune
                footer_text=f"© 2025 {app_settings.APP_NAME}. Tous droits réservés."
            )
            db_session.add(settings)
            db_session.commit()
            db_session.refresh(settings)
            logger.info(f"✅ Paramètres système créés avec valeurs par défaut complètes")
            logger.info(f"   📛 Entreprise: {settings.company_name}")
            logger.info(f"   🎨 Couleurs: Primary={settings.primary_color}, Secondary={settings.secondary_color}")
            logger.info(f"   🖼️  Logo: {settings.logo_path}")
        
        return settings
    
    @staticmethod
    def update_settings(
        db_session: Session,
        user_id: int,
        **kwargs
    ) -> SystemSettings:
        """
        Met à jour les paramètres système
        
        Args:
            db_session: Session de base de données
            user_id: ID de l'utilisateur qui modifie
            **kwargs: Paramètres à mettre à jour
        
        Returns:
            Les paramètres mis à jour
        """
        settings = SystemSettingsService.get_settings(db_session)
        
        # Mettre à jour uniquement les champs fournis
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        # Mettre à jour le timestamp et l'utilisateur
        settings.update_timestamp(user_id)
        
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        # Vider le cache pour forcer le rechargement
        settings_cache.clear()
        
        logger.info(f"✅ Paramètres système mis à jour par user #{user_id}")
        
        return settings
    
    @staticmethod
    def get_settings_as_dict(db_session: Session) -> Dict:
        """
        Récupère les paramètres système sous forme de dictionnaire
        Utilise le cache si disponible, sinon charge depuis la DB
        
        Args:
            db_session: Session de base de données
        
        Returns:
            Dictionnaire des paramètres
        """
        # Vérifier le cache
        cached = settings_cache.get()
        if cached is not None:
            return cached
        
        # Charger depuis la DB
        try:
            settings = SystemSettingsService.get_settings(db_session)
            
            result = {
                "company_name": settings.company_name,
                "company_description": settings.company_description,
                "company_email": settings.company_email,
                "company_phone": settings.company_phone,
                "company_address": settings.company_address,
                "logo_path": settings.logo_path,
                "primary_color": settings.primary_color,
                "secondary_color": settings.secondary_color,
                "accent_color": settings.accent_color,
                # Calculer les couleurs dérivées
                "primary_dark": SystemSettingsService.darken_color(settings.primary_color, 0.1),
                "primary_light": SystemSettingsService.lighten_color(settings.primary_color, 0.2),
                "footer_text": settings.footer_text,
                "maintenance_mode": settings.maintenance_mode,
                "allow_registration": settings.allow_registration,
                "max_upload_size_mb": settings.max_upload_size_mb,
                "session_timeout_minutes": settings.session_timeout_minutes,
                "updated_at": settings.updated_at,
            }
            
            # Mettre en cache
            settings_cache.set(result)
            
            return result
        except Exception as e:
            logger.warning(f"⚠️  Impossible de charger les paramètres depuis la DB, utilisation des valeurs par défaut: {e}")
            # Fallback sur les valeurs par défaut depuis la config
            return SystemSettingsService.get_default_settings()
    
    @staticmethod
    def lighten_color(hex_color: str, percent: float = 0.15) -> str:
        """
        Éclaircit une couleur hex
        
        Args:
            hex_color: Couleur au format #RRGGBB
            percent: Pourcentage d'éclaircissement (0.0 à 1.0)
        
        Returns:
            Couleur éclaircie au format #RRGGBB
        """
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            
            r = min(255, int(r + (255 - r) * percent))
            g = min(255, int(g + (255 - g) * percent))
            b = min(255, int(b + (255 - b) * percent))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color
    
    @staticmethod
    def darken_color(hex_color: str, percent: float = 0.15) -> str:
        """
        Assombrit une couleur hex
        
        Args:
            hex_color: Couleur au format #RRGGBB
            percent: Pourcentage d'assombrissement (0.0 à 1.0)
        
        Returns:
            Couleur assombrie au format #RRGGBB
        """
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            
            r = max(0, int(r * (1 - percent)))
            g = max(0, int(g * (1 - percent)))
            b = max(0, int(b * (1 - percent)))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color
    
    @staticmethod
    def get_default_settings() -> Dict:
        """
        Retourne les paramètres par défaut depuis la configuration
        Utilisé comme fallback si la DB n'est pas accessible
        
        Returns:
            Dictionnaire des paramètres par défaut
        """
        default_primary = "#ffd300"
        
        return {
            "company_name": app_settings.APP_NAME,
            "company_description": None,
            "company_email": None,
            "company_phone": None,
            "company_address": None,
            "logo_path": "images/logo.jpg",
            "primary_color": default_primary,
            "secondary_color": "#036c1d",
            "accent_color": "#e63600",
            # Couleurs dérivées
            "primary_dark": SystemSettingsService.darken_color(default_primary, 0.1),
            "primary_light": SystemSettingsService.lighten_color(default_primary, 0.2),
            "footer_text": "Tous droits réservés",
            "maintenance_mode": False,
            "allow_registration": False,
            "max_upload_size_mb": 10,
            "session_timeout_minutes": 30,
            "updated_at": None,
        }
    
    @staticmethod
    def save_logo(file_path: str, file_data: bytes) -> str:
        """
        Sauvegarde un logo uploadé
        
        Args:
            file_path: Nom du fichier
            file_data: Données binaires du fichier
        
        Returns:
            Chemin relatif du logo sauvegardé
        """
        try:
            # Créer le chemin complet
            logo_dir = path_config.STATIC_IMAGES_DIR
            logo_dir.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder le fichier
            full_path = logo_dir / file_path
            with open(full_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"📁 Logo sauvegardé: {file_path}")
            
            return f"images/{file_path}"
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde logo: {e}")
            raise


__all__ = ["SystemSettingsService"]

