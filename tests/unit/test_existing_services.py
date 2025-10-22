"""
Tests unitaires pour les services existants
"""

import pytest
from sqlmodel import Session

from app.services.user_service import UserService
from app.services.rh import RHService
from app.services.stock_service import StockService
from app.services.file_service import FileService
from app.services.activity_service import ActivityService
from app.models.user import User
from app.core.enums import UserType


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_get_by_email(session: Session):
    """Test UserService.get_by_email - EXISTANT"""
    # Créer un utilisateur de test
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        type_user=UserType.AGENT.value
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Test récupération par email
    found_user = UserService.get_by_email(session, "test@example.com")
    assert found_user is not None
    assert found_user.email == "test@example.com"
    assert found_user.full_name == "Test User"
    
    # Test avec email inexistant
    not_found = UserService.get_by_email(session, "nonexistent@example.com")
    assert not_found is None


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_get_by_id(session: Session):
    """Test UserService.get_by_id - EXISTANT"""
    # Créer un utilisateur de test
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        type_user=UserType.AGENT.value
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Test récupération par ID
    found_user = UserService.get_by_id(session, user.id)
    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email == "test@example.com"
    
    # Test avec ID inexistant
    not_found = UserService.get_by_id(session, 99999)
    assert not_found is None


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_create_user(session: Session):
    """Test UserService.create_user - EXISTANT"""
    # Créer un utilisateur
    user = UserService.create_user(
        session=session,
        email="newuser@example.com",
        full_name="New User",
        password="password123",
        type_user=UserType.AGENT
    )
    
    assert user is not None
    assert user.email == "newuser@example.com"
    assert user.full_name == "New User"
    assert user.type_user == UserType.AGENT.value
    assert user.is_active is True
    assert user.hashed_password is not None
    assert user.hashed_password != "password123"  # Doit être hashé


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_authenticate(session: Session):
    """Test UserService.authenticate - EXISTANT"""
    # Créer un utilisateur avec mot de passe
    user = UserService.create_user(
        session=session,
        email="auth@example.com",
        full_name="Auth User",
        password="password123",
        type_user=UserType.AGENT
    )
    
    # Test authentification réussie
    authenticated_user = UserService.authenticate(session, "auth@example.com", "password123")
    assert authenticated_user is not None
    assert authenticated_user.email == "auth@example.com"
    
    # Test avec mauvais mot de passe
    failed_auth = UserService.authenticate(session, "auth@example.com", "wrongpassword")
    assert failed_auth is None
    
    # Test avec email inexistant
    not_found = UserService.authenticate(session, "nonexistent@example.com", "password123")
    assert not_found is None


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_update_user(session: Session):
    """Test UserService.update_user - EXISTANT"""
    # Créer un utilisateur
    user = UserService.create_user(
        session=session,
        email="update@example.com",
        full_name="Original Name",
        password="password123",
        type_user=UserType.AGENT
    )
    
    # Mettre à jour l'utilisateur
    updated_user = UserService.update_user(
        session=session,
        user_id=user.id,
        full_name="Updated Name",
        is_active=False
    )
    
    assert updated_user is not None
    assert updated_user.full_name == "Updated Name"
    assert updated_user.is_active is False
    assert updated_user.email == "update@example.com"  # Email inchangé


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_list_users(session: Session):
    """Test UserService.list_users - EXISTANT"""
    # Créer plusieurs utilisateurs
    users_data = [
        ("user1@example.com", "User 1", UserType.AGENT),
        ("user2@example.com", "User 2", UserType.ADMIN),
        ("user3@example.com", "User 3", UserType.MODERATOR)
    ]
    
    created_users = []
    for email, name, user_type in users_data:
        user = UserService.create_user(
            session=session,
            email=email,
            full_name=name,
            password="password123",
            type_user=user_type
        )
        created_users.append(user)
    
    # Lister tous les utilisateurs
    all_users = UserService.list_users(session)
    assert len(all_users) >= len(created_users)
    
    # Vérifier que nos utilisateurs sont dans la liste
    emails = [user.email for user in all_users]
    assert "user1@example.com" in emails
    assert "user2@example.com" in emails
    assert "user3@example.com" in emails


@pytest.mark.critical
@pytest.mark.unit
def test_rh_service_kpis(session: Session):
    """Test RHService.kpis - EXISTANT"""
    # Le service RH existe et a une méthode kpis
    kpis = RHService.kpis(session)
    
    # Vérifier que les KPIs sont retournés
    assert isinstance(kpis, dict)
    
    # Vérifier les clés attendues
    expected_keys = [
        "total_agents",
        "agents_actifs", 
        "total_demandes",
        "demandes_en_cours",
        "demandes_archivees",
        "demandes_par_etat",
        "demandes_par_type"
    ]
    
    for key in expected_keys:
        assert key in kpis


@pytest.mark.critical
@pytest.mark.unit
def test_stock_service_get_kpis(session: Session):
    """Test StockService.get_kpis - EXISTANT"""
    # Le service Stock existe et a une méthode get_kpis
    kpis = StockService.get_kpis(session)
    
    # Vérifier que les KPIs sont retournés
    assert isinstance(kpis, dict)
    
    # Vérifier les clés attendues
    expected_keys = [
        "total_articles",
        "articles_actifs",
        "articles_rupture",
        "valeur_stock",
        "total_demandes",
        "demandes_en_attente",
        "demandes_validees"
    ]
    
    for key in expected_keys:
        assert key in kpis


@pytest.mark.critical
@pytest.mark.unit
def test_file_service_class_exists():
    """Test que FileService existe - EXISTANT"""
    # Vérifier que la classe existe et a les méthodes attendues
    assert hasattr(FileService, '_ensure_directories')
    assert hasattr(FileService, '_generate_stored_filename')
    
    # Vérifier que les constantes de dossiers existent
    assert hasattr(FileService, 'RAW_DIR')
    assert hasattr(FileService, 'PROCESSED_DIR')
    assert hasattr(FileService, 'ARCHIVE_DIR')


@pytest.mark.critical
@pytest.mark.unit
def test_activity_service_class_exists():
    """Test que ActivityService existe - EXISTANT"""
    # Vérifier que la classe existe
    assert ActivityService is not None
    
    # Vérifier que les méthodes principales existent
    assert hasattr(ActivityService, 'log_activity')
    assert hasattr(ActivityService, 'get_activities')


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_password_hashing():
    """Test du hachage des mots de passe - EXISTANT"""
    from app.core.security import get_password_hash, verify_password
    
    # Test hachage
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    assert hashed != password  # Doit être différent du mot de passe original
    assert len(hashed) > 50   # Le hash bcrypt est assez long
    
    # Test vérification
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_email_case_insensitive(session: Session):
    """Test que les emails sont insensibles à la casse - EXISTANT"""
    # Créer un utilisateur avec email en minuscules
    user = UserService.create_user(
        session=session,
        email="test@example.com",
        full_name="Test User",
        password="password123",
        type_user=UserType.AGENT
    )
    
    # Rechercher avec différentes casses
    found_lower = UserService.get_by_email(session, "test@example.com")
    found_upper = UserService.get_by_email(session, "TEST@EXAMPLE.COM")
    found_mixed = UserService.get_by_email(session, "Test@Example.Com")
    
    # Tous doivent retourner le même utilisateur
    assert found_lower is not None
    assert found_upper is not None
    assert found_mixed is not None
    
    assert found_lower.id == found_upper.id == found_mixed.id


@pytest.mark.critical
@pytest.mark.unit
def test_user_service_unique_email_constraint(session: Session):
    """Test contrainte d'unicité des emails - EXISTANT"""
    # Créer un premier utilisateur
    UserService.create_user(
        session=session,
        email="unique@example.com",
        full_name="First User",
        password="password123",
        type_user=UserType.AGENT
    )
    
    # Essayer de créer un deuxième utilisateur avec le même email
    with pytest.raises(Exception):  # Doit lever une exception d'unicité
        UserService.create_user(
            session=session,
            email="unique@example.com",
            full_name="Second User",
            password="password123",
            type_user=UserType.AGENT
        )
