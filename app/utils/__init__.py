"""
Utilitaires et fonctions helpers pour l'application
"""
from app.utils.email import send_email, send_verification_email, send_password_reset_email
from app.utils.validators import validate_email, validate_password_strength
from app.utils.helpers import generate_random_string, slugify, get_client_ip
from app.utils.constants import (
    PASSWORD_MIN_LENGTH,
    PASSWORD_REGEX,
    EMAIL_REGEX,
    MAX_LOGIN_ATTEMPTS,
    SESSION_TIMEOUT
)

__all__ = [
    # Email
    "send_email",
    "send_verification_email",
    "send_password_reset_email",
    
    # Validators
    "validate_email",
    "validate_password_strength",
    
    # Helpers
    "generate_random_string",
    "slugify",
    "get_client_ip",
    
    # Constants
    "PASSWORD_MIN_LENGTH",
    "PASSWORD_REGEX",
    "EMAIL_REGEX",
    "MAX_LOGIN_ATTEMPTS",
    "SESSION_TIMEOUT",
]

