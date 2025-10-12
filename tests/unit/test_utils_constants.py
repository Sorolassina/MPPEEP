"""
Tests unitaires pour les constantes
"""
from app.utils.constants import (
    PASSWORD_MIN_LENGTH,
    MAX_LOGIN_ATTEMPTS,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ALLOWED_IMAGE_EXTENSIONS,
    ROLES,
    STATUSES
)


def test_password_constants():
    """Test les constantes de mot de passe"""
    assert PASSWORD_MIN_LENGTH >= 8
    assert isinstance(PASSWORD_MIN_LENGTH, int)


def test_login_constants():
    """Test les constantes de login"""
    assert MAX_LOGIN_ATTEMPTS > 0
    assert isinstance(MAX_LOGIN_ATTEMPTS, int)


def test_pagination_constants():
    """Test les constantes de pagination"""
    assert DEFAULT_PAGE_SIZE > 0
    assert MAX_PAGE_SIZE >= DEFAULT_PAGE_SIZE


def test_file_extensions():
    """Test les extensions de fichiers autorisées"""
    assert '.jpg' in ALLOWED_IMAGE_EXTENSIONS
    assert '.png' in ALLOWED_IMAGE_EXTENSIONS
    assert isinstance(ALLOWED_IMAGE_EXTENSIONS, set)


def test_roles_list():
    """Test la liste des rôles"""
    assert 'user' in ROLES
    assert 'admin' in ROLES
    assert isinstance(ROLES, list)


def test_statuses_list():
    """Test la liste des statuts"""
    assert 'active' in STATUSES
    assert 'inactive' in STATUSES
    assert isinstance(STATUSES, list)

