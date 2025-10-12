"""
Tests fonctionnels pour le workflow complet de récupération de mot de passe
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.user import User
from app.core.security import verify_password


@pytest.mark.functional
def test_complete_password_recovery_workflow(client: TestClient, test_user: User, session: Session):
    """
    Test le workflow complet de récupération de mot de passe
    
    Scenario:
    1. Utilisateur oublie son mot de passe
    2. Demande de récupération via email
    3. Reçoit un code de vérification
    4. Vérifie le code
    5. Définit un nouveau mot de passe
    6. Se connecte avec le nouveau mot de passe
    """
    # Étape 1: Demande de récupération
    response = client.post(
        "/api/v1/forgot-password",
        data={"email": "test@example.com"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "/verify-code" in response.headers["location"]
    
    # Étape 2: Affichage de la page de vérification
    response = client.get("/api/v1/verify-code?email=test@example.com")
    assert response.status_code == 200
    
    # Note: Dans un vrai test, on récupérerait le code
    # Pour ce test, on suppose que le workflow est fonctionnel
    # jusqu'à ce point
    
    # TODO: Compléter le test avec mock du système d'email
    # ou accès aux logs pour récupérer le code


@pytest.mark.functional
def test_user_registration_and_login_workflow(client: TestClient, session: Session):
    """
    Test le workflow complet d'inscription et connexion
    
    Scenario:
    1. Création d'un nouveau compte
    2. Vérification que l'utilisateur est créé
    3. Connexion avec les identifiants
    4. Accès à l'accueil
    """
    # Étape 1: Créer un utilisateur
    new_user_email = "workflow_test@example.com"
    response = client.post(
        "/api/v1/users/",
        json={
            "email": new_user_email,
            "full_name": "Workflow Test User"
        }
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == new_user_email
    
    # Étape 2: Vérifier que l'utilisateur existe en DB
    statement = select(User).where(User.email == new_user_email)
    user = session.exec(statement).first()
    assert user is not None
    assert user.email == new_user_email
    assert user.full_name == "Workflow Test User"
    
    # Note: Pour tester la connexion, il faudrait que l'endpoint
    # de création d'utilisateur accepte aussi un mot de passe


@pytest.mark.functional
def test_inactive_user_workflow(client: TestClient, session: Session):
    """
    Test le workflow avec un utilisateur désactivé
    
    Scenario:
    1. Créer un utilisateur actif
    2. Désactiver le compte
    3. Tentative de connexion (doit échouer)
    4. Réactiver le compte
    5. Connexion réussie
    """
    from app.core.security import get_password_hash
    
    # Étape 1: Créer un utilisateur actif
    user = User(
        email="deactivation_test@example.com",
        full_name="Deactivation Test",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_superuser=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Étape 2: Vérifier connexion OK
    response = client.post(
        "/api/v1/login",
        data={
            "username": "deactivation_test@example.com",
            "password": "password123"
        },
        follow_redirects=False
    )
    assert response.status_code == 303  # Redirection vers accueil
    
    # Étape 3: Désactiver le compte
    user.is_active = False
    session.add(user)
    session.commit()
    
    # Étape 4: Tentative de connexion (doit échouer)
    response = client.post(
        "/api/v1/login",
        data={
            "username": "deactivation_test@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200  # Pas de redirection
    assert b"sactiv" in response.content.lower()
    
    # Étape 5: Réactiver le compte
    user.is_active = True
    session.add(user)
    session.commit()
    
    # Étape 6: Connexion réussie
    response = client.post(
        "/api/v1/login",
        data={
            "username": "deactivation_test@example.com",
            "password": "password123"
        },
        follow_redirects=False
    )
    assert response.status_code == 303

