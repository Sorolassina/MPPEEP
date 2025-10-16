"""
Fonctions helpers générales
"""
import string
import secrets
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import Request


def generate_random_string(length: int = 32, include_special: bool = False) -> str:
    """
    Génère une chaîne aléatoire sécurisée
    
    Args:
        length: Longueur de la chaîne
        include_special: Inclure des caractères spéciaux
    
    Returns:
        Chaîne aléatoire
        
    Example:
        token = generate_random_string(32)
        → "aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3"
    """
    if include_special:
        alphabet = string.ascii_letters + string.digits + string.punctuation
    else:
        alphabet = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_verification_code(length: int = 6) -> str:
    """
    Génère un code de vérification numérique
    
    Args:
        length: Longueur du code (défaut: 6)
    
    Returns:
        Code numérique
        
    Example:
        code = generate_verification_code()
        → "123456"
    """
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def slugify(text: str) -> str:
    """
    Convertit un texte en slug URL-friendly
    
    Args:
        text: Texte à convertir
    
    Returns:
        Slug
        
    Example:
        slugify("Mon Article 2024!")
        → "mon-article-2024"
    """
    if not text:
        return ""
    
    # Convertir en minuscules
    text = text.lower()
    
    # Remplacer les caractères accentués
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'ù': 'u', 'û': 'u', 'ü': 'u',
        'ô': 'o', 'ö': 'o',
        'î': 'i', 'ï': 'i',
        'ç': 'c',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Remplacer les espaces et caractères spéciaux par des tirets
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    
    # Retirer les tirets en début et fin
    text = text.strip('-')
    
    return text


def get_client_ip(request: Request) -> str:
    """
    Récupère l'IP du client en tenant compte des proxies
    
    Args:
        request: Requête FastAPI
    
    Returns:
        Adresse IP du client
        
    Example:
        @router.get("/")
        def index(request: Request):
            ip = get_client_ip(request)
            logger.info(f"Requête depuis {ip}")
    """
    # Vérifier les headers de proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Prendre la première IP (client réel)
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback sur l'IP directe
    return request.client.host if request.client else "unknown"


def format_file_size(size_bytes: int) -> str:
    """
    Formate une taille de fichier en format lisible
    
    Args:
        size_bytes: Taille en bytes
    
    Returns:
        Taille formatée
        
    Example:
        format_file_size(1536)
        → "1.5 KB"
        
        format_file_size(1048576)
        → "1.0 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def time_ago(dt: datetime) -> str:
    """
    Retourne une représentation "il y a X" d'une date
    
    Args:
        dt: Datetime à formater
    
    Returns:
        Texte "il y a X"
        
    Example:
        time_ago(datetime.now() - timedelta(minutes=5))
        → "il y a 5 minutes"
    """
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "à l'instant"
    
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    
    hours = int(minutes / 60)
    if hours < 24:
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    
    days = int(hours / 24)
    if days < 30:
        return f"il y a {days} jour{'s' if days > 1 else ''}"
    
    months = int(days / 30)
    if months < 12:
        return f"il y a {months} mois"
    
    years = int(months / 12)
    return f"il y a {years} an{'s' if years > 1 else ''}"


def parse_bool(value: Any) -> bool:
    """
    Parse une valeur en booléen de manière intelligente
    
    Args:
        value: Valeur à convertir
    
    Returns:
        Booléen
        
    Example:
        parse_bool("true") → True
        parse_bool("1") → True
        parse_bool("yes") → True
        parse_bool("false") → False
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'oui', 'on')
    
    return bool(value)


def safe_int(value: Any, default: int = 0) -> int:
    """
    Convertit une valeur en int de manière sûre
    
    Args:
        value: Valeur à convertir
        default: Valeur par défaut si conversion impossible
    
    Returns:
        Entier
        
    Example:
        safe_int("123") → 123
        safe_int("12.5") → 12
        safe_int("abc") → 0
        safe_int("abc", -1) → -1
    """
    try:
        # Essayer de convertir d'abord en float puis en int
        # Cela permet de gérer les strings comme "12.5"
        return int(float(value))
    except (ValueError, TypeError):
        return default

