"""
Tests d'intégration pour les endpoints utilisateurs
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User


def test_get_users(client: TestClient, admin_user: User, test_user: User):
    """Test la récupération de la liste des utilisateurs avec authentification réelle"""
    
    # Étape 1 : Se connecter en tant qu'admin via l'API de login
    login_response = client.post(
        "/api/v1/login",
        data={
            "username": "admin@example.com",
            "password": "admin123",
            "remember-me": "false"
        },
        follow_redirects=False  # Ne pas suivre la redirection
    )
    
    # Vérifier que la connexion a réussi (redirection 303)
    assert login_response.status_code == 303
    
    # Étape 2 : Utiliser la session obtenue pour accéder à l'endpoint
    response = client.get("/api/v1/users/")
    
    # Étape 3 : Vérifier la réponse
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # Au moins test_user et admin_user
    # Vérifier que test_user est dans la liste
    emails = [user["email"] for user in data]
    assert "test@example.com" in emails
    assert "admin@example.com" in emails


def test_get_user_by_id(client: TestClient, admin_user: User, test_user: User):
    """Test la récupération d'un utilisateur par ID"""
    
    # Étape 1 : Se connecter en tant qu'admin
    login_response = client.post(
        "/api/v1/login",
        data={
            "username": "admin@example.com",
            "password": "admin123",
            "remember-me": "false"
        },
        follow_redirects=False
    )
    
    # Vérifier que la connexion a réussi
    assert login_response.status_code == 303
    
    # Étape 2 : Récupérer l'utilisateur par ID
    response = client.get(f"/api/v1/users/{test_user.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


def test_get_user_not_found(client: TestClient):
    """Test la récupération d'un utilisateur inexistant"""
    response = client.get("/api/v1/users/99999")
    
    assert response.status_code == 404


def test_create_user(client: TestClient, admin_user: User):
    """Test la création d'un nouvel utilisateur"""
    
    # Étape 1 : Se connecter en tant qu'admin
    login_response = client.post(
        "/api/v1/login",
        data={
            "username": "admin@example.com",
            "password": "admin123",
            "remember-me": "false"
        },
        follow_redirects=False
    )
    
    # Vérifier que la connexion a réussi
    assert login_response.status_code == 303
    
    # Étape 2 : Créer un nouvel utilisateur
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "newuser@example.com",
            "full_name": "New User"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data


def test_create_user_duplicate_email(client: TestClient, admin_user: User, test_user: User):
    """Test la création d'un utilisateur avec email existant"""
    
    # Étape 1 : Se connecter en tant qu'admin
    login_response = client.post(
        "/api/v1/login",
        data={
            "username": "admin@example.com",
            "password": "admin123",
            "remember-me": "false"
        },
        follow_redirects=False
    )
    
    # Vérifier que la connexion a réussi
    assert login_response.status_code == 303
    
    # Étape 2 : Essayer de créer un utilisateur avec email existant
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "test@example.com",  # Email déjà utilisé
            "full_name": "Duplicate User"
        }
    )
    
    # Devrait échouer (erreur ou conflit)
    # Le comportement exact dépend de l'implémentation
    assert response.status_code in [400, 409, 422]

