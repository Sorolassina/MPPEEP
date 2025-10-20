"""
Tests unitaires pour les fonctions de sécurité
"""
import pytest
from app.core.security import get_password_hash, verify_password


@pytest.mark.critical
def test_password_hashing():
    """Test le hashing de mot de passe"""
    password = "mysecretpassword123"
    hashed = get_password_hash(password)
    
    # Le hash ne doit pas être vide
    assert hashed
    assert len(hashed) > 0
    
    # Le hash ne doit pas être le mot de passe en clair
    assert hashed != password
    
    # Le hash doit commencer par $2b$ (bcrypt) ou $bcrypt-sha256$ (bcrypt-sha256)
    assert hashed.startswith("$2b$") or hashed.startswith("$bcrypt-sha256$")


@pytest.mark.critical
def test_password_verification_success():
    """Test la vérification d'un mot de passe correct"""
    password = "mysecretpassword123"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True


def test_password_verification_failure():
    """Test la vérification d'un mot de passe incorrect"""
    password = "mysecretpassword123"
    wrong_password = "wrongpassword"
    hashed = get_password_hash(password)
    
    assert verify_password(wrong_password, hashed) is False


def test_different_hashes_for_same_password():
    """Test que le même mot de passe génère des hashs différents (salt)"""
    password = "mysecretpassword123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    
    # Les hashs doivent être différents (grâce au salt)
    assert hash1 != hash2
    
    # Mais les deux doivent vérifier le même mot de passe
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_empty_password():
    """Test avec un mot de passe vide"""
    password = ""
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("notempty", hashed) is False


def test_special_characters_password():
    """Test avec des caractères spéciaux"""
    password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True


def test_unicode_password():
    """Test avec des caractères unicode"""
    password = "Mot_de_passe_français_éèêë_çà_🔒"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True


def test_long_password():
    """Test avec un très long mot de passe"""
    password = "a" * 1000  # 1000 caractères
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("a" * 999, hashed) is False

