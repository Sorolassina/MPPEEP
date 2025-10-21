"""
Tests de sécurité pour la déconnexion
Vérifie que la session est bien invalidée après logout
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.services.session_service import SessionService, SESSION_COOKIE_NAME


@pytest.mark.critical
@pytest.mark.integration
def test_logout_invalidates_session(client: TestClient, session: Session, admin_user):
    """
    Test: Vérifier que la déconnexion invalide bien la session
    
    Scénario:
    1. Connexion réussie
    2. Vérification que l'utilisateur est connecté
    3. Déconnexion
    4. Vérification que la session est invalide
    """
    # 1. Connexion
    login_data = {
        "username": admin_user.email,
        "password": "admin123",
        "remember-me": "false"
    }
    response = client.post("/api/v1/login", data=login_data, follow_redirects=False)
    assert response.status_code == 303
    
    # Récupérer le cookie de session
    session_cookie = response.cookies.get(SESSION_COOKIE_NAME)
    assert session_cookie is not None, "Le cookie de session doit être présent après connexion"
    
    # 2. Vérifier que l'utilisateur est connecté (accès à une page protégée)
    response = client.get("/")
    assert response.status_code == 200
    
    # 3. Déconnexion
    response = client.get("/api/v1/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/api/v1/login")
    
    # 4. Vérifier que le cookie a été supprimé
    # FastAPI delete_cookie met max-age=0
    deleted_cookie = response.cookies.get(SESSION_COOKIE_NAME)
    # Le cookie devrait être absent ou avoir max-age=0
    
    # 5. Vérifier que la session est invalide en base
    user_session = SessionService.get_session_by_token(session, session_cookie)
    assert user_session is None, "La session doit être invalide après déconnexion"
    
    # 6. Vérifier qu'on ne peut plus accéder aux pages protégées
    response = client.get("/", follow_redirects=False)
    # Devrait rediriger vers login
    assert response.status_code in [303, 307], "Doit rediriger vers login si non connecté"


@pytest.mark.critical
@pytest.mark.integration
def test_old_session_token_rejected(client: TestClient, session: Session, admin_user):
    """
    Test: Vérifier qu'un ancien token de session est rejeté après logout
    
    Scénario:
    1. Connexion et récupération du token
    2. Déconnexion
    3. Tentative d'utilisation du vieux token
    """
    # 1. Connexion
    login_data = {
        "username": admin_user.email,
        "password": "admin123",
    }
    response = client.post("/api/v1/login", data=login_data, follow_redirects=False)
    old_session_token = response.cookies.get(SESSION_COOKIE_NAME)
    
    # 2. Déconnexion
    client.get("/api/v1/logout")
    
    # 3. Créer un nouveau client avec le vieux cookie
    new_client = TestClient(client.app)
    new_client.cookies.set(SESSION_COOKIE_NAME, old_session_token)
    
    # 4. Tenter d'accéder à une page protégée avec le vieux token
    response = new_client.get("/", follow_redirects=False)
    assert response.status_code in [303, 307], "Le vieux token doit être rejeté"


@pytest.mark.critical
@pytest.mark.integration
def test_concurrent_sessions_logout(client: TestClient, session: Session, admin_user):
    """
    Test: Vérifier qu'on peut avoir plusieurs sessions et déconnecter une seule
    
    Scénario:
    1. Créer 2 sessions sur 2 appareils différents
    2. Déconnecter la session 1
    3. Vérifier que la session 2 est toujours active
    """
    # 1. Connexion session 1
    client1 = TestClient(client.app)
    login_data = {
        "username": admin_user.email,
        "password": "admin123",
    }
    response1 = client1.post("/api/v1/login", data=login_data, follow_redirects=False)
    token1 = response1.cookies.get(SESSION_COOKIE_NAME)
    
    # 2. Connexion session 2 (simule un autre appareil)
    client2 = TestClient(client.app)
    response2 = client2.post("/api/v1/login", data=login_data, follow_redirects=False)
    token2 = response2.cookies.get(SESSION_COOKIE_NAME)
    
    # Vérifier que les tokens sont différents
    assert token1 != token2, "Chaque connexion doit créer une session unique"
    
    # 3. Déconnecter session 1
    client1.get("/api/v1/logout")
    
    # 4. Vérifier que session 1 est invalide
    session1_db = SessionService.get_session_by_token(session, token1)
    assert session1_db is None, "Session 1 doit être invalide"
    
    # 5. Vérifier que session 2 est toujours active
    session2_db = SessionService.get_session_by_token(session, token2)
    assert session2_db is not None, "Session 2 doit rester active"
    assert session2_db.is_active is True
    
    # 6. Client 2 peut toujours accéder aux pages
    response = client2.get("/")
    assert response.status_code == 200


@pytest.mark.integration
def test_session_security_flags(client: TestClient, admin_user):
    """
    Test: Vérifier que les cookies de session ont les bons flags de sécurité
    """
    from app.core.config import settings
    
    login_data = {
        "username": admin_user.email,
        "password": "admin123",
    }
    response = client.post("/api/v1/login", data=login_data, follow_redirects=False)
    
    # Récupérer les headers Set-Cookie
    set_cookie_header = response.headers.get("set-cookie", "")
    
    # Vérifier httponly (protection XSS)
    assert "HttpOnly" in set_cookie_header or "httponly" in set_cookie_header.lower(), \
        "Le cookie doit avoir le flag HttpOnly pour se protéger contre XSS"
    
    # Vérifier samesite (protection CSRF)
    assert "SameSite" in set_cookie_header or "samesite" in set_cookie_header.lower(), \
        "Le cookie doit avoir le flag SameSite pour se protéger contre CSRF"
    
    # En production, vérifier secure (HTTPS uniquement)
    if not settings.DEBUG:
        assert "Secure" in set_cookie_header or "secure" in set_cookie_header.lower(), \
            "Le cookie doit avoir le flag Secure en production (HTTPS uniquement)"


@pytest.mark.integration
def test_multiple_logout_attempts(client: TestClient, admin_user):
    """
    Test: Vérifier que plusieurs tentatives de déconnexion ne causent pas d'erreur
    """
    # 1. Connexion
    login_data = {
        "username": admin_user.email,
        "password": "admin123",
    }
    client.post("/api/v1/login", data=login_data)
    
    # 2. Première déconnexion
    response1 = client.get("/api/v1/logout", follow_redirects=False)
    assert response1.status_code == 303
    
    # 3. Deuxième déconnexion (déjà déconnecté)
    response2 = client.get("/api/v1/logout", follow_redirects=False)
    # Ne doit pas causer d'erreur, juste rediriger
    assert response2.status_code == 303
    assert response2.headers["location"].endswith("/api/v1/login")

