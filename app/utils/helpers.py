"""
Fonctions helpers générales
"""

import re
import secrets
import string
from datetime import datetime
from typing import Any

from fastapi import Request

from app.core.config import settings


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

    return "".join(secrets.choice(alphabet) for _ in range(length))


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
    return "".join(secrets.choice(string.digits) for _ in range(length))


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
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ô": "o",
        "ö": "o",
        "î": "i",
        "ï": "i",
        "ç": "c",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remplacer les espaces et caractères spéciaux par des tirets
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)

    # Retirer les tirets en début et fin
    text = text.strip("-")

    return text


"""
Retourne l'URL complète de l'endpoint
"""


def endpoint(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"

    root = settings.get_root_path.rstrip("/")
    return f"{root}{path}" if root else path


def get_client_ip(request: Request) -> str:
    """
    Récupère l'IP du client en tenant compte des proxies (Cloudflare, Nginx, etc.)

    Ordre de priorité :
    1. CF-Connecting-IP (Cloudflare - IP réelle du client)
    2. X-Forwarded-For (Proxies standards)
    3. X-Real-IP (Nginx)
    4. request.client.host (Connexion directe)

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
    # 1. Cloudflare - IP réelle du client
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # 2. Headers de proxy standards
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Prendre la première IP (client réel)
        return forwarded.split(",")[0].strip()

    # 3. Nginx et autres proxies
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 4. Fallback sur l'IP directe
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
    for unit in ["B", "KB", "MB", "GB", "TB"]:
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
        return value.lower() in ("true", "1", "yes", "oui", "on")

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


def convert_french_date_to_iso_str(french_date: str) -> str | None:
    """
    Convertit une date française (ex: "17 octobre 2023") vers format ISO (ex: "2023-10-17")
    
    Args:
        french_date: Date au format français (ex: "17 octobre 2023", "17/10/2023")
        
    Returns:
        Date au format ISO "YYYY-MM-DD" ou None si conversion impossible
        
    Example:
        convert_french_date_to_iso_str("17 octobre 2023") → "2023-10-17"
        convert_french_date_to_iso_str("17/10/2023") → "2023-10-17"
    """
    if not french_date or not french_date.strip():
        return None
    
    mois_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    
    try:
        date_str = french_date.strip()
        
        # Si c'est déjà en format ISO, le retourner tel quel
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # Si c'est au format DD/MM/YYYY
        if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
            parts = date_str.split('/')
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        # Si c'est au format "DD mois YYYY"
        parts = date_str.split()
        if len(parts) >= 3:
            jour = int(parts[0])
            mois_nom = parts[1].lower()
            annee = int(parts[2])
            
            # Trouver l'index du mois
            mois_index = -1
            for i, mois in enumerate(mois_fr):
                if mois_nom.startswith(mois[:3]) or mois_nom == mois:
                    mois_index = i
                    break
            
            if mois_index != -1:
                mois_str = str(mois_index + 1).zfill(2)
                jour_str = str(jour).zfill(2)
                return f"{annee}-{mois_str}-{jour_str}"
    except (ValueError, IndexError, AttributeError) as e:
        pass
    
    return None


def convert_iso_to_french_date_str(iso_date: str) -> str | None:
    """
    Convertit une date ISO (ex: "2023-10-17") vers format français (ex: "17 octobre 2023")
    
    Args:
        iso_date: Date au format ISO "YYYY-MM-DD"
        
    Returns:
        Date au format français "DD mois YYYY" ou None si conversion impossible
        
    Example:
        convert_iso_to_french_date_str("2023-10-17") → "17 octobre 2023"
    """
    if not iso_date or not iso_date.strip():
        return None
    
    mois_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    
    try:
        # Si c'est déjà en format français, le retourner tel quel
        if re.match(r'\d{1,2}\s+\w+\s+\d{4}', iso_date):
            return iso_date
        
        # Parser ISO: YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}$', iso_date):
            parts = iso_date.split('-')
            annee = int(parts[0])
            mois = int(parts[1]) - 1
            jour = int(parts[2])
            
            if 0 <= mois < 12:
                return f"{jour} {mois_fr[mois]} {annee}"
    except (ValueError, IndexError) as e:
        pass
    
    return None


def convert_french_month_to_iso_str(french_month: str) -> str | None:
    """
    Convertit un mois français (ex: "Mai 2025") vers format ISO (ex: "2025-05")
    
    Args:
        french_month: Mois au format français (ex: "Mai 2025", "mai 2025")
        
    Returns:
        Mois au format ISO "YYYY-MM" ou None si conversion impossible
        
    Example:
        convert_french_month_to_iso_str("Mai 2025") → "2025-05"
        convert_french_month_to_iso_str("mai 2025") → "2025-05"
    """
    if not french_month or not french_month.strip():
        return None
    
    mois_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    
    try:
        month_str = french_month.strip()
        
        # Si c'est déjà en format ISO, le retourner tel quel
        if re.match(r'^\d{4}-\d{2}$', month_str):
            return month_str
        
        # Parser format français: "Mois AAAA" ou "mois AAAA"
        parts = month_str.split()
        if len(parts) >= 2:
            mois_nom = parts[0].lower()
            annee = int(parts[1])
            
            # Trouver l'index du mois
            mois_index = -1
            for i, mois in enumerate(mois_fr):
                if mois_nom.startswith(mois[:3]) or mois_nom == mois:
                    mois_index = i
                    break
            
            if mois_index != -1:
                mois_str = str(mois_index + 1).zfill(2)
                return f"{annee}-{mois_str}"
    except (ValueError, IndexError) as e:
        pass
    
    return None


def convert_iso_month_to_french_str(iso_month: str) -> str | None:
    """
    Convertit un mois ISO (ex: "2025-05") vers format français (ex: "Mai 2025")
    
    Args:
        iso_month: Mois au format ISO "YYYY-MM"
        
    Returns:
        Mois au format français "Mois AAAA" ou None si conversion impossible
        
    Example:
        convert_iso_month_to_french_str("2025-05") → "Mai 2025"
    """
    if not iso_month or not iso_month.strip():
        return None
    
    mois_fr = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]
    
    try:
        # Si c'est déjà en format français, le retourner tel quel
        if re.match(r'\w+\s+\d{4}', iso_month):
            return iso_month
        
        # Parser ISO: YYYY-MM
        if re.match(r'^\d{4}-\d{2}$', iso_month):
            parts = iso_month.split('-')
            annee = int(parts[0])
            mois = int(parts[1]) - 1
            
            if 0 <= mois < 12:
                return f"{mois_fr[mois]} {annee}"
    except (ValueError, IndexError) as e:
        pass
    
    return None