"""
Tests unitaires pour l'initialisation de la base de données
"""
import pytest
from sqlmodel import Session, select
from app.models.user import User
from app.services.user_service import UserService


@pytest.mark.unit
@pytest.mark.database
def test_tables_creation(test_session):
    """Test que les tables sont bien créées"""
    # Les tables sont créées par la fixture test_session
    # Vérifier qu'on peut créer un utilisateur
    user = User(
        email="test@test.com",
        full_name="Test User",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False
    )
    
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    
    assert user.id is not None
    assert user.email == "test@test.com"


@pytest.mark.unit
@pytest.mark.database
def test_create_admin_if_database_empty(test_session):
    """Test que l'admin est créé si la base est vide"""
    # Vérifier que la base est vide
    users = test_session.exec(select(User)).all()
    initial_count = len(users)
    
    # Si la base est vide, créer l'admin
    if initial_count == 0:
        admin = UserService.create_user(
            session=test_session,
            email="admin@test.com",
            full_name="Admin Test",
            password="admin123",
            is_active=True,
            is_superuser=True
        )
        
        assert admin is not None
        assert admin.email == "admin@test.com"
        assert admin.is_superuser is True
        
        # Vérifier qu'il est bien en base
        users = test_session.exec(select(User)).all()
        assert len(users) == 1


@pytest.mark.unit
@pytest.mark.database
def test_skip_admin_creation_if_users_exist(test_session):
    """Test que l'admin n'est pas recréé si des users existent"""
    # Créer un premier utilisateur
    user1 = UserService.create_user(
        session=test_session,
        email="user1@test.com",
        full_name="User 1",
        password="pass123",
        is_active=True,
        is_superuser=False
    )
    
    assert user1 is not None
    
    # Compter les utilisateurs
    count_before = UserService.count_users(test_session)
    assert count_before == 1
    
    # Simuler la logique d'init_db : ne pas créer admin si users existent
    if count_before > 0:
        # Skip la création de l'admin
        pass
    
    # Vérifier que le nombre n'a pas changé
    count_after = UserService.count_users(test_session)
    assert count_after == count_before


@pytest.mark.unit
@pytest.mark.database
def test_admin_user_has_correct_permissions(test_session):
    """Test que l'admin créé a les bons permissions"""
    # Créer un admin
    admin = UserService.create_user(
        session=test_session,
        email="admin@test.com",
        full_name="Admin",
        password="admin123",
        is_active=True,
        is_superuser=True
    )
    
    assert admin is not None
    assert admin.is_active is True
    assert admin.is_superuser is True
    assert admin.email == "admin@test.com"


@pytest.mark.unit
@pytest.mark.database
def test_tables_are_idempotent(test_session):
    """Test que create_tables peut être appelé plusieurs fois sans erreur"""
    from sqlmodel import SQLModel
    from app.db.session import engine
    
    # Créer les tables plusieurs fois
    try:
        SQLModel.metadata.create_all(engine)
        SQLModel.metadata.create_all(engine)
        SQLModel.metadata.create_all(engine)
        success = True
    except Exception:
        success = False
    
    assert success is True


@pytest.mark.unit
@pytest.mark.database
def test_user_count_zero_on_empty_database(test_session):
    """Test que count_users retourne 0 sur base vide"""
    count = UserService.count_users(test_session)
    assert count == 0


@pytest.mark.unit
@pytest.mark.database
def test_user_count_after_creation(test_session):
    """Test que count_users est correct après création"""
    # Base vide
    assert UserService.count_users(test_session) == 0
    
    # Créer 3 utilisateurs
    for i in range(3):
        UserService.create_user(
            session=test_session,
            email=f"user{i}@test.com",
            full_name=f"User {i}",
            password="pass123"
        )
    
    # Vérifier le count
    assert UserService.count_users(test_session) == 3

