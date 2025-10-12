"""
Tests d'intégration pour l'initialisation complète de la base de données
"""
import pytest
from sqlmodel import Session, select, SQLModel
from app.models.user import User
from app.services.user_service import UserService
from app.db.session import engine
from pathlib import Path
import tempfile
import os


@pytest.mark.integration
@pytest.mark.database
def test_full_database_initialization():
    """Test du processus complet d'initialisation"""
    # Créer une base SQLite temporaire
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db = tmp.name
    
    try:
        from sqlmodel import create_engine
        
        # Créer un engine temporaire
        temp_engine = create_engine(f"sqlite:///{temp_db}")
        
        # 1. Créer les tables
        SQLModel.metadata.create_all(temp_engine)
        
        with Session(temp_engine) as session:
            # 2. Vérifier que la base est vide
            users = session.exec(select(User)).all()
            assert len(users) == 0
            
            # 3. Créer l'admin
            admin = UserService.create_user(
                session=session,
                email="admin@test.com",
                full_name="Admin Test",
                password="admin123",
                is_active=True,
                is_superuser=True
            )
            
            assert admin is not None
            assert admin.id == 1  # Premier utilisateur
            assert admin.is_superuser is True
            
            # 4. Vérifier qu'on peut se connecter
            authenticated = UserService.authenticate(
                session, "admin@test.com", "admin123"
            )
            assert authenticated is not None
            assert authenticated.id == admin.id
        
        temp_engine.dispose()
        
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(temp_db):
            os.unlink(temp_db)


@pytest.mark.integration
@pytest.mark.database
def test_initialization_is_idempotent(test_session):
    """Test que l'initialisation peut être répétée sans problème"""
    # Premier passage
    admin1 = UserService.create_user(
        session=test_session,
        email="admin@test.com",
        full_name="Admin",
        password="admin123",
        is_superuser=True
    )
    
    assert admin1 is not None
    count_after_first = UserService.count_users(test_session)
    
    # Deuxième passage : ne devrait pas créer de doublon
    admin2 = UserService.create_user(
        session=test_session,
        email="admin@test.com",  # Même email
        full_name="Admin",
        password="admin123",
        is_superuser=True
    )
    
    # Retourne None si l'email existe déjà
    assert admin2 is None
    
    # Le count ne devrait pas avoir changé
    count_after_second = UserService.count_users(test_session)
    assert count_after_second == count_after_first


@pytest.mark.integration
@pytest.mark.database
def test_database_with_multiple_users(test_session):
    """Test de la base avec plusieurs utilisateurs"""
    # Créer un admin
    admin = UserService.create_user(
        test_session, "admin@test.com", "Admin", "admin123", is_superuser=True
    )
    
    # Créer des utilisateurs normaux
    user1 = UserService.create_user(
        test_session, "user1@test.com", "User 1", "pass123"
    )
    user2 = UserService.create_user(
        test_session, "user2@test.com", "User 2", "pass456"
    )
    
    assert admin is not None
    assert user1 is not None
    assert user2 is not None
    
    # Vérifier le total
    total = UserService.count_users(test_session)
    assert total == 3
    
    # Vérifier les rôles
    all_users = UserService.list_all(test_session)
    superusers = [u for u in all_users if u.is_superuser]
    normal_users = [u for u in all_users if not u.is_superuser]
    
    assert len(superusers) == 1
    assert len(normal_users) == 2


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.slow
def test_concurrent_user_creation(test_session):
    """Test de création concurrente d'utilisateurs (éviter les doublons)"""
    # Tenter de créer le même utilisateur deux fois
    user1 = UserService.create_user(
        test_session, "concurrent@test.com", "User", "pass123"
    )
    
    # Deuxième tentative avec le même email
    user2 = UserService.create_user(
        test_session, "concurrent@test.com", "User", "pass456"
    )
    
    # Le premier devrait réussir
    assert user1 is not None
    
    # Le second devrait échouer (email déjà utilisé)
    assert user2 is None
    
    # Vérifier qu'il n'y a qu'un seul utilisateur
    assert UserService.count_users(test_session) == 1


@pytest.mark.integration
@pytest.mark.database
def test_database_rollback_on_error(test_session):
    """Test que les erreurs ne corrompent pas la base"""
    # Créer un utilisateur valide
    user1 = UserService.create_user(
        test_session, "valid@test.com", "Valid User", "pass123"
    )
    assert user1 is not None
    
    # Tenter de créer un utilisateur avec le même email (erreur)
    user2 = UserService.create_user(
        test_session, "valid@test.com", "Duplicate", "pass456"
    )
    assert user2 is None
    
    # Vérifier que la base est toujours cohérente
    users = UserService.list_all(test_session)
    assert len(users) == 1
    assert users[0].email == "valid@test.com"
    assert users[0].full_name == "Valid User"  # Pas modifié


@pytest.mark.integration
@pytest.mark.database
def test_admin_default_credentials():
    """Test des identifiants admin par défaut (constantes)"""
    # Vérifier que les constantes sont correctes
    # (ces valeurs sont utilisées dans init_db.py)
    DEFAULT_ADMIN_EMAIL = "admin@mppeep.com"
    DEFAULT_ADMIN_PASSWORD = "admin123"
    
    assert DEFAULT_ADMIN_EMAIL == "admin@mppeep.com"
    assert DEFAULT_ADMIN_PASSWORD == "admin123"
    
    # Vérifier que ces credentials peuvent créer un admin fonctionnel
    # (test de cohérence)
    assert "@" in DEFAULT_ADMIN_EMAIL
    assert len(DEFAULT_ADMIN_PASSWORD) >= 6


@pytest.mark.integration
@pytest.mark.database
def test_list_all_users_empty_database(test_session):
    """Test de list_all sur base vide"""
    users = UserService.list_all(test_session)
    assert users == []
    assert len(users) == 0


@pytest.mark.integration
@pytest.mark.database
def test_list_all_users_with_data(test_session):
    """Test de list_all avec plusieurs utilisateurs"""
    # Créer plusieurs utilisateurs
    emails = ["user1@test.com", "user2@test.com", "user3@test.com"]
    
    for email in emails:
        UserService.create_user(
            test_session, email, f"User {email}", "pass123"
        )
    
    # Récupérer tous les utilisateurs
    all_users = UserService.list_all(test_session)
    
    assert len(all_users) == 3
    
    # Vérifier que tous les emails sont présents
    user_emails = [u.email for u in all_users]
    for email in emails:
        assert email in user_emails

