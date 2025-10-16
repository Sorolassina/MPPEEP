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

def profile_picture_url(user_or_picture: any, add_cache_buster: bool = True) -> str:
    """
    Génère l'URL de la photo de profil avec fallback vers l'image par défaut
    
    Args:
        user_or_picture: Peut être:
            - Un objet User avec user.profile_picture
            - Un objet Agent avec agent.photo_path
            - Un dict avec user['profile_picture'] ou agent['photo_path']
            - Une chaîne directe (chemin de l'image)
            - None
        add_cache_buster: Ajouter un paramètre de cache pour forcer le refresh
    
    Usage dans template:
        {{ profile_picture_url(current_user) }}
        {{ profile_picture_url(agent) }}  # Utilise photo_path
        {{ profile_picture_url(user.profile_picture) }}
        {{ profile_picture_url(None) }}  # Retourne l'image par défaut
    
    Returns:
        URL de l'image de profil ou de l'image par défaut
    """
    from datetime import datetime
    
    # Image par défaut
    default_image = "/static/images/default-avatar.svg"
    
    # Extraire le chemin de l'image
    picture_path = None
    user_id = None
    
    if user_or_picture is None:
        return default_image
    
    # Si c'est un dict (comme current_user dans les templates)
    if isinstance(user_or_picture, dict):
        # Essayer profile_picture (User) puis photo_path (Agent)
        picture_path = user_or_picture.get('profile_picture') or user_or_picture.get('photo_path')
        user_id = user_or_picture.get('id')
    # Si c'est une chaîne directe
    elif isinstance(user_or_picture, str):
        picture_path = user_or_picture
    # Si c'est un objet avec attributs
    else:
        # Essayer profile_picture (User) puis photo_path (Agent/Personnel)
        picture_path = getattr(user_or_picture, 'profile_picture', None) or getattr(user_or_picture, 'photo_path', None)
        user_id = getattr(user_or_picture, 'id', None)
    
    # Si pas d'image définie, retourner l'image par défaut
    if not picture_path:
        return default_image
    
    # Si le chemin commence déjà par /uploads/ ou /static/, le retourner tel quel
    if picture_path.startswith('/uploads/') or picture_path.startswith('/static/'):
        return picture_path
    
    # Construire l'URL de l'image
    image_url = f"/uploads/{picture_path}"
    
    # Ajouter un cache buster si demandé
    if add_cache_buster and user_id:
        timestamp = int(datetime.now().timestamp())
        image_url += f"?v={user_id}_{timestamp}"
    
    return image_url

def user_initials(user_or_name: any) -> str:
    """
    Génère les initiales d'un utilisateur pour l'affichage dans un avatar
    
    Args:
        user_or_name: Peut être:
            - Un objet User avec user.full_name
            - Un dict avec user['full_name'] ou user['email']
            - Une chaîne directe (nom complet)
            - None
    
    Usage dans template:
        {{ user_initials(current_user) }}
        {{ user_initials("Jean Dupont") }}
    
    Returns:
        Initiales (ex: "JD") ou "U" par défaut
    """
    name = None
    email = None
    
    if user_or_name is None:
        return "U"
    
    # Si c'est un dict
    if isinstance(user_or_name, dict):
        name = user_or_name.get('full_name')
        email = user_or_name.get('email')
    # Si c'est une chaîne directe
    elif isinstance(user_or_name, str):
        name = user_or_name
    # Si c'est un objet
    else:
        name = getattr(user_or_name, 'full_name', None)
        email = getattr(user_or_name, 'email', None)
    
    # Utiliser le nom si disponible
    if name:
        parts = name.strip().split()
        if len(parts) >= 2:
            # Prénom + Nom
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1:
            # Un seul mot : prendre les 2 premières lettres
            return parts[0][:2].upper()
    
    # Fallback sur l'email
    if email:
        return email[0].upper()
    
    # Fallback final
    return "U"

# ==========================================
# ENREGISTREMENT DES FILTRES
# ==========================================

def extract_initials(text: str, max_length: int = 4) -> str:
    """
    Extrait les initiales d'un texte pour créer un code court.
    Fonction générique utilisable pour n'importe quel texte.
    
    Exemples d'utilisation:
    - "Biens et Services" → "BS"
    - "Personnel" → "P"
    - "Investissements" → "I"
    - "Transferts" → "T"
    - "Direction Générale" → "DG"
    - "Ministère de la Santé" → "MS"
    - "Projet de Développement" → "PD"
    - "Gestion des Ressources Humaines" → "GRH"
    
    Usage: 
    - {{ "Biens et Services"|extract_initials }}
    - {{ "Un Très Long Texte"|extract_initials(3) }}  (max 3 caractères)
    """
    if not text:
        return ""
    
    # Mappings spécifiques (optionnels, pour des cas courants)
    # Peut être étendu selon les besoins
    mappings = {
        'biens et services': 'BS',
        'biens & services': 'BS',
        'personnel': 'P',
        'investissements': 'I',
        'investissement': 'I',
        'transferts': 'T',
        'transfert': 'T',
        'direction générale': 'DG',
        'ressources humaines': 'RH',
    }
    
    text_lower = text.lower().strip()
    
    # Vérifier si on a un mapping direct
    if text_lower in mappings:
        return mappings[text_lower]
    
    # Extraire les initiales des mots significatifs
    # Stop-words en français (mots à ignorer)
    stop_words = {
        'et', 'de', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 
        'en', 'au', 'aux', 'à', 'd', 'l', 'pour', 'par', 'sur',
        'dans', 'avec', 'sans', 'sous', 'vers', 'chez'
    }
    
    # Séparer par espaces, tirets, underscores, etc.
    import re
    words = re.split(r'[\s\-_/]+', text)
    initials = []
    
    for word in words:
        # Nettoyer le mot (enlever la ponctuation, garder alphanumérique)
        clean_word = ''.join(c for c in word if c.isalnum())
        
        # Ignorer les stop-words et mots vides
        if clean_word and clean_word.lower() not in stop_words:
            initials.append(clean_word[0].upper())
    
    result = ''.join(initials)
    
    # Limiter la longueur si nécessaire
    if len(result) > max_length:
        result = result[:max_length]
    
    # Si le résultat est vide, prendre les premières lettres du texte original
    if not result:
        clean_text = ''.join(c for c in text if c.isalnum())
        result = clean_text[:min(3, len(clean_text))].upper()
    
    return result


templates.env.filters["format_date"] = format_date
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_time"] = format_time
templates.env.filters["format_number_french"] = format_number_french
templates.env.filters["truncate_smart"] = truncate_smart
templates.env.filters["extract_initials"] = extract_initials

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
    profile_picture_url=profile_picture_url,  # Helper pour images de profil avec fallback
    user_initials=user_initials,  # Helper pour générer les initiales
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
