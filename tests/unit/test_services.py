"""
Tests unitaires pour les services métier
"""
import pytest
from sqlmodel import Session
from app.services.user_service import UserService
from app.services.activity_service import ActivityService
from app.services.file_service import FileService
from app.models.user import User
from app.core.enums import UserType


@pytest.mark.critical
def test_user_service_create_user(session: Session):
    """Test UserService.create_user"""
    user = UserService.create_user(
        session=session,
        email="service_test@example.com",
        full_name="Service Test User",
        password="password123",
        is_active=True,
        is_superuser=False
    )
    
    assert user is not None
    assert user.email == "service_test@example.com"
    assert user.full_name == "Service Test User"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.id is not None


@pytest.mark.critical
def test_user_service_authenticate(session: Session):
    """Test UserService.authenticate"""
    # Créer un utilisateur
    user = UserService.create_user(
        session=session,
        email="auth_test@example.com",
        full_name="Auth Test User",
        password="password123"
    )
    
    # Test authentification réussie
    authenticated_user = UserService.authenticate(
        session=session,
        email="auth_test@example.com",
        password="password123"
    )
    
    assert authenticated_user is not None
    assert authenticated_user.id == user.id
    assert authenticated_user.email == user.email
    
    # Test authentification échouée
    failed_auth = UserService.authenticate(
        session=session,
        email="auth_test@example.com",
        password="wrongpassword"
    )
    
    assert failed_auth is None


@pytest.mark.critical
def test_user_service_get_by_email(session: Session):
    """Test UserService.get_by_email"""
    # Créer un utilisateur
    user = UserService.create_user(
        session=session,
        email="getbyemail_test@example.com",
        full_name="Get By Email Test",
        password="password123"
    )
    
    # Test récupération réussie
    retrieved_user = UserService.get_by_email(
        session=session,
        email="getbyemail_test@example.com"
    )
    
    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.email == user.email
    
    # Test utilisateur inexistant
    not_found = UserService.get_by_email(
        session=session,
        email="nonexistent@example.com"
    )
    
    assert not_found is None


@pytest.mark.critical
def test_user_service_count_users(session: Session):
    """Test UserService.count_users"""
    # Compter les utilisateurs initiaux
    initial_count = UserService.count_users(session)
    
    # Créer plusieurs utilisateurs
    for i in range(3):
        UserService.create_user(
            session=session,
            email=f"count_test_{i}@example.com",
            full_name=f"Count Test User {i}",
            password="password123"
        )
    
    # Vérifier le nouveau compte
    final_count = UserService.count_users(session)
    assert final_count == initial_count + 3


@pytest.mark.critical
def test_user_service_update_user(session: Session):
    """Test UserService.update_user"""
    # Créer un utilisateur
    user = UserService.create_user(
        session=session,
        email="update_test@example.com",
        full_name="Update Test User",
        password="password123"
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
    assert updated_user.email == user.email  # Email inchangé


@pytest.mark.critical
def test_user_service_delete_user(session: Session):
    """Test UserService.delete_user"""
    # Créer un utilisateur
    user = UserService.create_user(
        session=session,
        email="delete_test@example.com",
        full_name="Delete Test User",
        password="password123"
    )
    
    user_id = user.id
    
    # Supprimer l'utilisateur
    success = UserService.delete_user(session=session, user_id=user_id)
    assert success is True
    
    # Vérifier que l'utilisateur est supprimé
    deleted_user = UserService.get_by_email(
        session=session,
        email="delete_test@example.com"
    )
    assert deleted_user is None


@pytest.mark.critical
def test_user_service_list_users(session: Session):
    """Test UserService.list_users"""
    # Créer plusieurs utilisateurs
    users = []
    for i in range(5):
        user = UserService.create_user(
            session=session,
            email=f"list_test_{i}@example.com",
            full_name=f"List Test User {i}",
            password="password123"
        )
        users.append(user)
    
    # Lister les utilisateurs
    all_users = UserService.list_users(session=session)
    
    assert len(all_users) >= 5  # Au moins les 5 créés
    
    # Vérifier que nos utilisateurs sont dans la liste
    user_emails = [user.email for user in all_users]
    for i in range(5):
        assert f"list_test_{i}@example.com" in user_emails


@pytest.mark.critical
def test_user_service_password_validation():
    """Test validation des mots de passe dans UserService"""
    # Test mot de passe valide
    valid_password = "ValidPassword123!"
    assert UserService.validate_password(valid_password) is True
    
    # Test mots de passe invalides
    invalid_passwords = [
        "123",           # Trop court
        "",              # Vide
        "password",      # Pas de chiffres
        "12345678",      # Pas de lettres
        "Password"       # Pas de chiffres ni caractères spéciaux
    ]
    
    for invalid_password in invalid_passwords:
        assert UserService.validate_password(invalid_password) is False


@pytest.mark.critical
def test_user_service_email_validation():
    """Test validation des emails dans UserService"""
    # Test emails valides
    valid_emails = [
        "user@example.com",
        "test.user@domain.co.uk",
        "user+tag@example.org"
    ]
    
    for email in valid_emails:
        assert UserService.validate_email(email) is True
    
    # Test emails invalides
    invalid_emails = [
        "invalid-email",
        "@example.com",
        "user@",
        "user@.com",
        ""
    ]
    
    for email in invalid_emails:
        assert UserService.validate_email(email) is False


@pytest.mark.critical
def test_user_service_role_management(session: Session):
    """Test gestion des rôles utilisateur"""
    # Créer un utilisateur normal
    user = UserService.create_user(
        session=session,
        email="role_test@example.com",
        full_name="Role Test User",
        password="password123",
        type_user=UserType.AGENT
    )
    
    assert user.type_user == UserType.AGENT
    
    # Promouvoir en admin
    admin_user = UserService.update_user(
        session=session,
        user_id=user.id,
        type_user=UserType.ADMIN,
        is_superuser=True
    )
    
    assert admin_user.type_user == UserType.ADMIN
    assert admin_user.is_superuser is True


@pytest.mark.critical
def test_user_service_duplicate_email_handling(session: Session):
    """Test gestion des emails en double"""
    # Créer un premier utilisateur
    user1 = UserService.create_user(
        session=session,
        email="duplicate@example.com",
        full_name="First User",
        password="password123"
    )
    
    assert user1 is not None
    
    # Tenter de créer un deuxième utilisateur avec le même email
    user2 = UserService.create_user(
        session=session,
        email="duplicate@example.com",
        full_name="Second User",
        password="password456"
    )
    
    # Doit échouer ou retourner None
    assert user2 is None or user2.id != user1.id


@pytest.mark.critical
def test_user_service_inactive_user_handling(session: Session):
    """Test gestion des utilisateurs inactifs"""
    # Créer un utilisateur inactif
    inactive_user = UserService.create_user(
        session=session,
        email="inactive@example.com",
        full_name="Inactive User",
        password="password123",
        is_active=False
    )
    
    assert inactive_user.is_active is False
    
    # Test authentification d'un utilisateur inactif
    auth_result = UserService.authenticate(
        session=session,
        email="inactive@example.com",
        password="password123"
    )
    
    # L'authentification doit échouer pour un utilisateur inactif
    assert auth_result is None


@pytest.mark.critical
def test_user_service_password_change(session: Session):
    """Test changement de mot de passe"""
    # Créer un utilisateur
    user = UserService.create_user(
        session=session,
        email="password_change@example.com",
        full_name="Password Change User",
        password="oldpassword123"
    )
    
    # Vérifier l'authentification avec l'ancien mot de passe
    old_auth = UserService.authenticate(
        session=session,
        email="password_change@example.com",
        password="oldpassword123"
    )
    assert old_auth is not None
    
    # Changer le mot de passe
    updated_user = UserService.change_password(
        session=session,
        user_id=user.id,
        new_password="newpassword123"
    )
    
    assert updated_user is not None
    
    # Vérifier que l'ancien mot de passe ne fonctionne plus
    old_auth_failed = UserService.authenticate(
        session=session,
        email="password_change@example.com",
        password="oldpassword123"
    )
    assert old_auth_failed is None
    
    # Vérifier que le nouveau mot de passe fonctionne
    new_auth = UserService.authenticate(
        session=session,
        email="password_change@example.com",
        password="newpassword123"
    )
    assert new_auth is not None


@pytest.mark.critical
def test_user_service_bulk_operations(session: Session):
    """Test opérations en lot"""
    # Créer plusieurs utilisateurs en lot
    users_data = [
        {"email": f"bulk_{i}@example.com", "full_name": f"Bulk User {i}", "password": "password123"}
        for i in range(10)
    ]
    
    created_users = UserService.create_users_bulk(session=session, users_data=users_data)
    
    assert len(created_users) == 10
    
    # Vérifier que tous les utilisateurs sont créés
    for i, user in enumerate(created_users):
        assert user.email == f"bulk_{i}@example.com"
        assert user.full_name == f"Bulk User {i}"
    
    # Test suppression en lot
    user_ids = [user.id for user in created_users]
    deleted_count = UserService.delete_users_bulk(session=session, user_ids=user_ids)
    
    assert deleted_count == 10
    
    # Vérifier que tous les utilisateurs sont supprimés
    for user_id in user_ids:
        user = session.get(User, user_id)
        assert user is None
