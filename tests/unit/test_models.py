"""
Tests unitaires pour les modèles de données
"""
import pytest
from sqlmodel import Session

from app.models.user import User
from app.core.security import get_password_hash


def test_create_user(session: Session):
    """Test la création d'un utilisateur"""
    user = User(
        email="model_test@example.com",
        full_name="Model Test",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_superuser=False
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    assert user.id is not None
    assert user.email == "model_test@example.com"
    assert user.full_name == "Model Test"
    assert user.is_active is True
    assert user.is_superuser is False


def test_user_default_values(session: Session):
    """Test les valeurs par défaut du modèle User"""
    user = User(
        email="defaults@example.com",
        hashed_password=get_password_hash("password123")
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Valeurs par défaut
    assert user.is_active is True  # default=True
    assert user.is_superuser is False  # default=False
    assert user.full_name is None  # Optional


def test_user_email_unique(session: Session):
    """Test l'unicité de l'email"""
    user1 = User(
        email="unique@example.com",
        hashed_password=get_password_hash("password123")
    )
    session.add(user1)
    session.commit()
    
    # Tenter de créer un deuxième user avec le même email
    user2 = User(
        email="unique@example.com",
        hashed_password=get_password_hash("password456")
    )
    session.add(user2)
    
    # Devrait lever une exception
    with pytest.raises(Exception):  # IntegrityError
        session.commit()


def test_user_superuser_flag(session: Session):
    """Test le flag superuser"""
    admin = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_superuser=True
    )
    
    session.add(admin)
    session.commit()
    session.refresh(admin)
    
    assert admin.is_superuser is True


def test_user_inactive_account(session: Session):
    """Test un compte inactif"""
    user = User(
        email="inactive@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=False
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    assert user.is_active is False

