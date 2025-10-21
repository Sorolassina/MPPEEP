"""
Configuration pytest et fixtures partagées
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Forcer le mode DEBUG pour les tests
os.environ["DEBUG"] = "True"
os.environ["ENV"] = "dev"

from app.core.security import get_password_hash
from app.db.session import get_session
from app.main import app
from app.models.user import User


@pytest.fixture(name="session")
def session_fixture():
    """
    Crée une base de données SQLite en mémoire pour les tests
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture(name="test_session")
def test_session_fixture():
    """
    Alias pour session - pour compatibilité avec les anciens tests
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Client de test FastAPI avec une session DB de test
    """
    from app.main import subapp  # Import subapp aussi
    
    def get_session_override():
        return session

    # Override sur app et subapp pour être sûr
    app.dependency_overrides[get_session] = get_session_override
    subapp.dependency_overrides[get_session] = get_session_override

    # Utiliser raise_server_exceptions=False pour capturer les erreurs 500
    client = TestClient(app, raise_server_exceptions=False)
    yield client

    app.dependency_overrides.clear()
    subapp.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """
    Crée un utilisateur de test dans la base
    """
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_superuser=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """
    Crée un utilisateur admin de test dans la base
    """
    from app.core.enums import UserType

    user = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_superuser=True,
        type_user=UserType.ADMIN  # Important pour require_roles("admin")
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_client")
def admin_client_fixture(client: TestClient, session: Session, admin_user: User):
    """
    Client authentifié en tant qu'admin
    """
    from unittest.mock import Mock

    from app.services.session_service import SESSION_COOKIE_NAME, SessionService

    # Créer une fausse request pour le service
    mock_request = Mock()
    mock_request.client.host = "testclient"
    mock_request.headers.get.return_value = "test-agent"

    # Créer une session pour l'admin
    user_session = SessionService.create_session(
        db_session=session,
        user=admin_user,
        request=mock_request,
        remember_me=False
    )

    # Configurer le cookie dans le client
    client.cookies.set(SESSION_COOKIE_NAME, user_session.session_token)

    return client

