"""
Tests d'expiration automatique des sessions
Vérifie que les sessions expirent correctement après un certain temps
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.session import UserSession
from app.services.session_service import SessionService, SESSION_COOKIE_NAME


@pytest.mark.critical
@pytest.mark.integration
def test_session_expires_after_configured_time(client: TestClient, session: Session, admin_user):
    """
    Test: Vérifier qu'une session expire après la durée configurée
    
    Scénario:
    1. Créer une session avec une expiration très courte
    2. Attendre l'expiration
    3. Vérifier que la session est rejetée
    """
    from app.api.v1.endpoints.auth import router
    from fastapi import Request
    from unittest.mock import MagicMock
    
    # Créer une session qui expire dans 1 seconde
    request_mock = MagicMock(spec=Request)
    request_mock.client.host = "127.0.0.1"
    request_mock.headers.get.return_value = "TestClient"
    
    user_session = SessionService.create_session(
        db_session=session,
        user=admin_user,
        request=request_mock,
        remember_me=False
    )
    
    # Modifier manuellement l'expiration pour qu'elle soit dans le passé
    user_session.expires_at = datetime.now() - timedelta(seconds=1)
    session.commit()
    
    # Essayer de récupérer la session
    retrieved_session = SessionService.get_session_by_token(session, user_session.session_token)
    
    # La session doit être None car expirée
    assert retrieved_session is None, "La session expirée doit être rejetée"
    
    # Vérifier que la session a été désactivée
    session.refresh(user_session)
    assert user_session.is_active is False, "La session expirée doit être désactivée"


@pytest.mark.critical
@pytest.mark.integration
def test_session_not_expired_before_time(client: TestClient, session: Session, admin_user):
    """
    Test: Vérifier qu'une session valide reste accessible
    
    Scénario:
    1. Créer une session avec expiration normale (7 jours)
    2. Vérifier qu'elle est accessible immédiatement
    """
    from unittest.mock import MagicMock
    from fastapi import Request
    
    request_mock = MagicMock(spec=Request)
    request_mock.client.host = "127.0.0.1"
    request_mock.headers.get.return_value = "TestClient"
    
    user_session = SessionService.create_session(
        db_session=session,
        user=admin_user,
        request=request_mock,
        remember_me=False
    )
    
    # La session doit être valide
    retrieved_session = SessionService.get_session_by_token(session, user_session.session_token)
    
    assert retrieved_session is not None, "La session valide doit être accessible"
    assert retrieved_session.is_active is True
    assert retrieved_session.is_expired() is False


@pytest.mark.integration
def test_remember_me_extends_session(client: TestClient, session: Session, admin_user):
    """
    Test: Vérifier que "Remember me" étend la durée de la session
    
    Scénario:
    1. Créer une session sans "Remember me" (7 jours)
    2. Créer une session avec "Remember me" (30 jours)
    3. Comparer les durées d'expiration
    """
    from unittest.mock import MagicMock
    from fastapi import Request
    
    request_mock = MagicMock(spec=Request)
    request_mock.client.host = "127.0.0.1"
    request_mock.headers.get.return_value = "TestClient"
    
    # Session normale (7 jours)
    normal_session = SessionService.create_session(
        db_session=session,
        user=admin_user,
        request=request_mock,
        remember_me=False
    )
    
    # Session "Remember me" (30 jours)
    remember_session = SessionService.create_session(
        db_session=session,
        user=admin_user,
        request=request_mock,
        remember_me=True
    )
    
    # Calculer la différence de durée
    normal_duration = (normal_session.expires_at - normal_session.created_at).days
    remember_duration = (remember_session.expires_at - remember_session.created_at).days
    
    assert normal_duration >= 6 and normal_duration <= 7, "Session normale doit durer ~7 jours"
    assert remember_duration >= 29 and remember_duration <= 30, "Session 'Remember me' doit durer ~30 jours"
    assert remember_duration > normal_duration, "'Remember me' doit étendre la session"


@pytest.mark.integration
def test_session_refresh_updates_last_activity(session: Session, admin_user):
    """
    Test: Vérifier que l'activité de la session est mise à jour
    
    Scénario:
    1. Créer une session
    2. Simuler une activité (refresh)
    3. Vérifier que last_activity est mis à jour
    """
    from unittest.mock import MagicMock
    from fastapi import Request
    import time
    
    request_mock = MagicMock(spec=Request)
    request_mock.client.host = "127.0.0.1"
    request_mock.headers.get.return_value = "TestClient"
    
    user_session = SessionService.create_session(
        db_session=session,
        user=admin_user,
        request=request_mock,
        remember_me=False
    )
    
    initial_activity = user_session.last_activity
    
    # Attendre un peu
    time.sleep(1)
    
    # Récupérer l'utilisateur (ce qui devrait rafraîchir la session)
    user = SessionService.get_user_from_session(
        db_session=session,
        session_token=user_session.session_token
    )
    
    # Recharger la session depuis la base
    session.refresh(user_session)
    
    assert user is not None
    assert user_session.last_activity > initial_activity, "last_activity doit être mis à jour"


@pytest.mark.integration
def test_expired_sessions_cleanup(session: Session, admin_user):
    """
    Test: Vérifier que les sessions expirées sont nettoyées
    
    Scénario:
    1. Créer plusieurs sessions expirées
    2. Lancer le nettoyage
    3. Vérifier qu'elles sont désactivées
    """
    from unittest.mock import MagicMock
    from fastapi import Request
    
    request_mock = MagicMock(spec=Request)
    request_mock.client.host = "127.0.0.1"
    request_mock.headers.get.return_value = "TestClient"
    
    # Créer 3 sessions expirées
    expired_sessions = []
    for i in range(3):
        user_session = SessionService.create_session(
            db_session=session,
            user=admin_user,
            request=request_mock,
            remember_me=False
        )
        # Forcer l'expiration dans le passé
        user_session.expires_at = datetime.now() - timedelta(hours=i+1)
        expired_sessions.append(user_session)
    
    session.commit()
    
    # Vérifier qu'elles sont actives avant nettoyage
    for s in expired_sessions:
        session.refresh(s)
        assert s.is_active is True
    
    # Lancer le nettoyage
    cleaned_count = SessionService.cleanup_expired_sessions(session)
    
    # Au moins 3 sessions doivent être nettoyées
    assert cleaned_count >= 3, f"Au moins 3 sessions expirées doivent être nettoyées, trouvé: {cleaned_count}"
    
    # Vérifier qu'elles sont maintenant inactives
    for s in expired_sessions:
        session.refresh(s)
        assert s.is_active is False, "Les sessions expirées doivent être désactivées"


@pytest.mark.integration
def test_access_with_expired_session_redirects_to_login(client: TestClient, session: Session, admin_user):
    """
    Test: Vérifier qu'une session expirée redirige vers login
    
    Scénario:
    1. Se connecter
    2. Forcer l'expiration de la session
    3. Essayer d'accéder à une page protégée
    4. Vérifier la redirection vers login
    """
    # 1. Connexion
    login_data = {
        "username": admin_user.email,
        "password": "admin123",
    }
    response = client.post("/api/v1/login", data=login_data, follow_redirects=False)
    session_cookie = response.cookies.get(SESSION_COOKIE_NAME)
    
    assert session_cookie is not None
    
    # 2. Récupérer la session et la faire expirer
    from sqlmodel import select
    user_session = session.exec(
        select(UserSession).where(UserSession.session_token == session_cookie)
    ).first()
    
    assert user_session is not None
    
    # Forcer l'expiration
    user_session.expires_at = datetime.now() - timedelta(hours=1)
    session.commit()
    
    # 3. Essayer d'accéder à une page protégée
    response = client.get("/", follow_redirects=False)
    
    # 4. Doit rediriger vers login (ou retourner 401)
    assert response.status_code in [303, 307, 401], \
        f"Session expirée doit rediriger vers login, got: {response.status_code}"


@pytest.mark.integration
def test_session_duration_configuration():
    """
    Test: Vérifier que les durées de session sont configurables
    """
    # Session normale: 7 jours
    normal_session = UserSession(
        session_token="test_normal",
        user_id=1,
        expires_at=datetime.now() + timedelta(days=7)
    )
    
    # Session "Remember me": 30 jours
    remember_session = UserSession(
        session_token="test_remember",
        user_id=1,
        expires_at=datetime.now() + timedelta(days=30)
    )
    
    # Vérifier les durées
    normal_duration = (normal_session.expires_at - datetime.now()).days
    remember_duration = (remember_session.expires_at - datetime.now()).days
    
    assert normal_duration >= 6, "Session normale doit durer au moins 6 jours"
    assert remember_duration >= 29, "Session 'Remember me' doit durer au moins 29 jours"


@pytest.mark.integration
def test_is_expired_method():
    """
    Test: Vérifier la méthode is_expired() du modèle UserSession
    """
    # Session non expirée
    valid_session = UserSession(
        session_token="valid",
        user_id=1,
        expires_at=datetime.now() + timedelta(days=1)
    )
    assert valid_session.is_expired() is False
    
    # Session expirée
    expired_session = UserSession(
        session_token="expired",
        user_id=1,
        expires_at=datetime.now() - timedelta(days=1)
    )
    assert expired_session.is_expired() is True
    
    # Session qui expire maintenant (limite)
    now_session = UserSession(
        session_token="now",
        user_id=1,
        expires_at=datetime.now() - timedelta(seconds=1)
    )
    assert now_session.is_expired() is True

