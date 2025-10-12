"""
Validateurs personnalisés pour l'application
"""
import re
from typing import Tuple
from app.utils.constants import EMAIL_REGEX, PASSWORD_REGEX, PASSWORD_MIN_LENGTH


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Valide un email
    
    Args:
        email: Email à valider
    
    Returns:
        (is_valid, error_message)
        
    Example:
        is_valid, error = validate_email("user@example.com")
        if not is_valid:
            raise ValueError(error)
    """
    if not email:
        return False, "L'email est requis"
    
    if not re.match(EMAIL_REGEX, email):
        return False, "Format d'email invalide"
    
    if len(email) > 255:
        return False, "L'email est trop long (max 255 caractères)"
    
    return True, ""


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Valide la force d'un mot de passe
    
    Critères :
    - Minimum 8 caractères
    - Au moins une majuscule
    - Au moins une minuscule
    - Au moins un chiffre
    
    Args:
        password: Mot de passe à valider
    
    Returns:
        (is_valid, error_message)
        
    Example:
        is_valid, error = validate_password_strength("MyP@ss123")
        if not is_valid:
            raise ValueError(error)
    """
    if not password:
        return False, "Le mot de passe est requis"
    
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères"
    
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une majuscule"
    
    if not re.search(r'[a-z]', password):
        return False, "Le mot de passe doit contenir au moins une minuscule"
    
    if not re.search(r'[0-9]', password):
        return False, "Le mot de passe doit contenir au moins un chiffre"
    
    # Optionnel : Vérifier les caractères spéciaux
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     return False, "Le mot de passe doit contenir au moins un caractère spécial"
    
    return True, ""


def validate_username(username: str, min_length: int = 3, max_length: int = 50) -> Tuple[bool, str]:
    """
    Valide un nom d'utilisateur
    
    Args:
        username: Nom d'utilisateur à valider
        min_length: Longueur minimale
        max_length: Longueur maximale
    
    Returns:
        (is_valid, error_message)
    """
    if not username:
        return False, "Le nom d'utilisateur est requis"
    
    if len(username) < min_length:
        return False, f"Le nom d'utilisateur doit contenir au moins {min_length} caractères"
    
    if len(username) > max_length:
        return False, f"Le nom d'utilisateur doit contenir au maximum {max_length} caractères"
    
    # Alphanumerique, tirets et underscores seulement
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Le nom d'utilisateur ne peut contenir que des lettres, chiffres, tirets et underscores"
    
    return True, ""


def validate_phone_number(phone: str, country_code: str = "FR") -> Tuple[bool, str]:
    """
    Valide un numéro de téléphone
    
    Args:
        phone: Numéro de téléphone
        country_code: Code pays (FR par défaut)
    
    Returns:
        (is_valid, error_message)
    """
    if not phone:
        return False, "Le numéro de téléphone est requis"
    
    # Retirer les espaces, tirets, etc.
    clean_phone = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    if country_code == "FR":
        # Format français : 0X XX XX XX XX ou +33 X XX XX XX XX
        if re.match(r'^0[1-9]\d{8}$', clean_phone):
            return True, ""
        if re.match(r'^\+33[1-9]\d{8}$', clean_phone):
            return True, ""
        return False, "Format de téléphone français invalide (ex: 06 12 34 56 78)"
    
    # Format international basique
    if re.match(r'^\+?[1-9]\d{7,14}$', clean_phone):
        return True, ""
    
    return False, "Format de téléphone invalide"


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Valide une URL
    
    Args:
        url: URL à valider
    
    Returns:
        (is_valid, error_message)
    """
    if not url:
        return False, "L'URL est requise"
    
    url_pattern = re.compile(
        r'^https?://'  # http:// ou https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domaine
        r'localhost|'  # ou localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ou IP
        r'(?::\d+)?'  # port optionnel
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        return False, "Format d'URL invalide"
    
    return True, ""

