"""
Fonctions de sécurité pour l'authentification
"""

from passlib.context import CryptContext

# Configuration du contexte de hashing
pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],  # 👈 au lieu de "bcrypt"
    deprecated="auto",
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair correspond au hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash un mot de passe en clair
    """
    return pwd_context.hash(password)
