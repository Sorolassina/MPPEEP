"""
Tests d'intégration pour l'authentification via l'API
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User


def test_login_page_get(client: TestClient):
    """Test l'affichage de la page de login"""
    response = client.get("/api/v1/login")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"Connexion" in response.content or b"login" in response.content.lower()


def test_login_success(client: TestClient, test_user: User):
    """Test une connexion réussie"""
    response = client.post(
        "/api/v1/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        },
        follow_redirects=False
    )
    
    # Doit rediriger vers l'accueil
    assert response.status_code == 303
    assert response.headers["location"] == "/accueil"


def test_login_wrong_password(client: TestClient, test_user: User):
    """Test une connexion avec mauvais mot de passe"""
    response = client.post(
        "/api/v1/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 200
    assert b"incorrect" in response.content.lower()


def test_login_user_not_found(client: TestClient):
    """Test une connexion avec email inexistant"""
    response = client.post(
        "/api/v1/login",
        data={
            "username": "notfound@example.com",
            "password": "anypassword"
        }
    )
    
    assert response.status_code == 200
    assert b"incorrect" in response.content.lower()


def test_login_inactive_user(client: TestClient, session: Session):
    """Test une connexion avec compte désactivé"""
    # Créer un user inactif
    from app.core.security import get_password_hash
    
    inactive_user = User(
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password=get_password_hash("password123"),
        is_active=False,
        is_superuser=False
    )
    session.add(inactive_user)
    session.commit()
    
    response = client.post(
        "/api/v1/login",
        data={
            "username": "inactive@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    assert b"sactiv" in response.content.lower()  # "désactivé" ou "inactive"


def test_forgot_password_page(client: TestClient):
    """Test l'affichage de la page mot de passe oublié"""
    response = client.get("/api/v1/forgot-password")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_forgot_password_submit(client: TestClient, test_user: User):
    """Test la soumission du formulaire mot de passe oublié"""
    response = client.post(
        "/api/v1/forgot-password",
        data={"email": "test@example.com"},
        follow_redirects=False
    )
    
    # Doit rediriger vers la page de vérification
    assert response.status_code == 303
    assert "/verify-code" in response.headers["location"]


def test_verify_code_page(client: TestClient):
    """Test l'affichage de la page de vérification de code"""
    response = client.get("/api/v1/verify-code?email=test@example.com")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

