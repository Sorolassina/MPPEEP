"""
Configuration des templates Jinja2 pour le projet
"""
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
from app.core.path_config import path_config

# Configuration du répertoire des templates
TEMPLATES_DIR = Path(__file__).parent

# Initialisation Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ==========================================
# FILTRES JINJA2 PERSONNALISÉS
# ==========================================

def format_date(value, format_str="%d/%m/%Y"):
    """
    Formate une date
    
    Usage dans template: {{ ma_date|format_date }}
    """
    if value:
        return value.strftime(format_str)
    return "Non renseigné"

def format_datetime(value, format_str="%d/%m/%Y à %H:%M"):
    """
    Formate une date et heure
    
    Usage: {{ ma_datetime|format_datetime }}
    """
    if value:
        return value.strftime(format_str)
    return "Non renseigné"

def format_time(value, format_str="%H:%M"):
    """
    Formate une heure
    
    Usage: {{ mon_heure|format_time }}
    """
    if value:
        return value.strftime(format_str)
    return "Non renseigné"

def format_number_french(value, decimals=2):
    """
    Formate un nombre au format français (virgule pour les décimales)
    
    Usage: {{ prix|format_number_french }}
    Exemple: 1234.56 → "1 234,56"
    """
    if value is None:
        return "0,00"
    
    try:
        if isinstance(value, str):
            value = float(value)
        
        if decimals == 0:
            formatted = f"{int(value):,}".replace(",", " ")
        else:
            formatted = f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")
        
        return formatted
    except (ValueError, TypeError):
        return "0,00"

def truncate_smart(value, max_length=50, suffix="..."):
    """
    Tronque intelligemment un texte
    
    Usage: {{ long_texte|truncate_smart(30) }}
    """
    if not value:
        return ""
    
    if len(value) <= max_length:
        return value
    
    return value[:max_length - len(suffix)] + suffix

# ==========================================
# FONCTIONS GLOBALES (disponibles partout)
# ==========================================

def get_current_time():
    """Retourne l'heure actuelle"""
    return datetime.now()

def get_current_year():
    """Retourne l'année actuelle"""
    return datetime.now().year

def static_url(file_path: str) -> str:
    """
    Génère l'URL pour un fichier statique
    
    Usage dans template: {{ static_url('images/logo.png') }}
    Résultat: /static/images/logo.jpg
    """
    return path_config.get_file_url("static", file_path)

def media_url(file_path: str) -> str:
    """
    Génère l'URL pour un fichier media
    
    Usage dans template: {{ media_url('avatars/user.jpg') }}
    Résultat: /media/avatars/user.jpg
    """
    return path_config.get_file_url("media", file_path)

def upload_url(file_path: str) -> str:
    """
    Génère l'URL pour un fichier upload
    
    Usage dans template: {{ upload_url('documents/file.pdf') }}
    Résultat: /uploads/documents/file.pdf
    """
    return path_config.get_file_url("uploads", file_path)

# ==========================================
# ENREGISTREMENT DES FILTRES
# ==========================================

templates.env.filters["format_date"] = format_date
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_time"] = format_time
templates.env.filters["format_number_french"] = format_number_french
templates.env.filters["truncate_smart"] = truncate_smart

# ==========================================
# CONTEXT PROCESSOR
# ==========================================

def get_template_context(request, **kwargs):
    """
    Génère le contexte de base pour tous les templates
    Inclut automatiquement current_user, app_name, system_settings, etc.
    """
    from app.core.config import settings
    from typing import Optional
    from app.models.user import User
    
    # Récupérer l'utilisateur connecté
    current_user: Optional[User] = None
    user_dict: Optional[dict] = None
    
    # Récupérer les paramètres système
    system_settings: dict = {}
    
    try:
        from app.api.v1.endpoints.auth import get_current_user
        from app.db.session import get_session
        from app.services.session_service import SESSION_COOKIE_NAME
        from app.services.system_settings_service import SystemSettingsService
        
        db = next(get_session())
        
        # Charger l'utilisateur connecté
        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        if session_token:
            current_user = get_current_user(db=db, session_token=session_token)
            # Convertir en dict pour éviter les problèmes de session SQLAlchemy
            if current_user:
                user_dict = {
                    "id": current_user.id,
                    "email": current_user.email,
                    "full_name": current_user.full_name,
                    "is_active": current_user.is_active,
                    "is_superuser": current_user.is_superuser,
                    "type_user": current_user.type_user,
                    "profile_picture": current_user.profile_picture,
                }
        
        # Charger les paramètres système (avec cache)
        system_settings = SystemSettingsService.get_settings_as_dict(db)
        
    except Exception as e:
        # En cas d'erreur, utiliser les valeurs par défaut
        from app.services.system_settings_service import SystemSettingsService
        system_settings = SystemSettingsService.get_default_settings()
    
    # Contexte de base
    context = {
        "request": request,
        "app_name": system_settings.get("company_name", settings.APP_NAME),
        "current_user": user_dict,  # Dict au lieu de l'objet SQLAlchemy
        "system_settings": system_settings,  # Paramètres système disponibles partout
    }
    
    # Ajouter les kwargs supplémentaires
    context.update(kwargs)
    
    return context

# ==========================================
# ENREGISTREMENT DES GLOBALS
# ==========================================

templates.env.globals.update(
    now=get_current_time,
    current_year=get_current_year,
    datetime=datetime,
    static_url=static_url,
    media_url=media_url,
    upload_url=upload_url,
    path_config=path_config,  # Accès complet à path_config si nécessaire
)

# ==========================================
# CONFIGURATION
# ==========================================

# Auto-reload des templates en développement
# (à activer via settings.DEBUG si vous avez des settings)
templates.env.auto_reload = True

# ==========================================
# EXPORTS
# ==========================================

__all__ = ["templates", "get_template_context"]
