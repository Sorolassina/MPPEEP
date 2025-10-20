"""
Tests fonctionnels pour le workflow complet d'initialisation de la base
"""
import os
import tempfile

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.services.user_service import UserService


@pytest.mark.critical
@pytest.mark.functional
@pytest.mark.database
def test_first_startup_workflow():
    """
    Test du workflow complet du premier démarrage
    Simule ce qui se passe quand on lance l'application pour la première fois
    """
    # Créer une base temporaire
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db = tmp.name

    try:
        # 1. SIMULATION : Créer l'engine (comme dans session.py)
        temp_engine = create_engine(f"sqlite:///{temp_db}")

        # 2. ÉTAPE 1 : Créer les tables (comme create_tables())
        SQLModel.metadata.create_all(temp_engine)

        with Session(temp_engine) as session:
            # 3. ÉTAPE 2 : Vérifier que la base est vide
            count = UserService.count_users(session)
            assert count == 0, "La base devrait être vide au démarrage"

            # 4. ÉTAPE 3 : Créer l'admin par défaut (comme create_admin_user())
            admin = UserService.create_user(
                session=session,
                email="admin@mppeep.com",
                full_name="Administrateur MPPEEP",
                password="admin123",
                is_active=True,
                is_superuser=True
            )

            assert admin is not None, "L'admin devrait être créé"
            assert admin.id == 1, "L'admin devrait avoir l'ID 1"
            assert admin.is_superuser is True

            # 5. VÉRIFICATION : L'admin peut se connecter
            authenticated = UserService.authenticate(
                session, "admin@mppeep.com", "admin123"
            )

            assert authenticated is not None
            assert authenticated.id == admin.id
            assert authenticated.email == "admin@mppeep.com"

            # 6. VÉRIFICATION : Un seul utilisateur en base
            final_count = UserService.count_users(session)
            assert final_count == 1

        temp_engine.dispose()

    finally:
        # Nettoyer
        if os.path.exists(temp_db):
            session.close()
            temp_engine.dispose()
            os.unlink(temp_db)


@pytest.mark.functional
@pytest.mark.database
def test_subsequent_startup_workflow():
    """
    Test du workflow des démarrages suivants
    Simule ce qui se passe quand l'application redémarre avec une base existante
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db = tmp.name

    try:
        temp_engine = create_engine(f"sqlite:///{temp_db}")

        # 1. PREMIER DÉMARRAGE : Initialiser la base
        SQLModel.metadata.create_all(temp_engine)

        with Session(temp_engine) as session:
            # Créer l'admin
            admin = UserService.create_user(
                session, "admin@mppeep.com", "Admin", "admin123", is_superuser=True
            )
            assert admin is not None

            # Créer d'autres utilisateurs
            UserService.create_user(
                session, "user1@test.com", "User 1", "pass123"
            )
            UserService.create_user(
                session, "user2@test.com", "User 2", "pass456"
            )

            count_after_first_startup = UserService.count_users(session)

        # 2. DEUXIÈME DÉMARRAGE : Simuler un redémarrage
        with Session(temp_engine) as session:
            # Créer les tables (idempotent, aucun effet)
            SQLModel.metadata.create_all(temp_engine)

            # Vérifier le nombre d'utilisateurs
            count_before = UserService.count_users(session)

            # Logique d'init : Ne pas recréer l'admin si users existent
            if count_before > 0:
                # Skip la création
                pass

            # Vérifier que rien n'a changé
            count_after = UserService.count_users(session)
            assert count_after == count_after_first_startup
            assert count_after == 3  # Admin + 2 users

            # Vérifier que l'admin existe toujours
            admin_check = UserService.get_by_email(session, "admin@mppeep.com")
            assert admin_check is not None
            assert admin_check.is_superuser is True

        temp_engine.dispose()

    finally:
        if os.path.exists(temp_db):
            os.unlink(temp_db)


@pytest.mark.functional
@pytest.mark.database
@pytest.mark.slow
def test_database_reset_workflow():
    """
    Test du workflow de réinitialisation complète
    Simule : rm app.db && uvicorn app.main:app
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db = tmp.name

    try:
        temp_engine = create_engine(f"sqlite:///{temp_db}")

        # 1. PREMIER CYCLE : Initialisation
        SQLModel.metadata.create_all(temp_engine)

        with Session(temp_engine) as session:
            admin1 = UserService.create_user(
                session, "admin@mppeep.com", "Admin", "admin123", is_superuser=True
            )
            admin1_id = admin1.id

        # 2. SUPPRESSION : Simuler la suppression de la base
        temp_engine.dispose()
        os.unlink(temp_db)

        # 3. NOUVEAU DÉMARRAGE : Recréer tout
        temp_engine = create_engine(f"sqlite:///{temp_db}")
        SQLModel.metadata.create_all(temp_engine)

        with Session(temp_engine) as session:
            # La base devrait être vide
            count = UserService.count_users(session)
            assert count == 0

            # Recréer l'admin
            admin2 = UserService.create_user(
                session, "admin@mppeep.com", "Admin", "admin123", is_superuser=True
            )

            # Nouvel ID (nouvelle base)
            assert admin2.id == 1  # Recommence à 1
            assert admin2.email == "admin@mppeep.com"

        temp_engine.dispose()

    finally:
        if os.path.exists(temp_db):
            os.unlink(temp_db)


@pytest.mark.functional
@pytest.mark.database
def test_initialization_with_existing_admin():
    """Test que l'admin n'est pas recréé si un admin existe déjà"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db = tmp.name

    try:
        temp_engine = create_engine(f"sqlite:///{temp_db}")
        SQLModel.metadata.create_all(temp_engine)

        with Session(temp_engine) as session:
            # Créer un admin personnalisé
            custom_admin = UserService.create_user(
                session,
                "custom_admin@company.com",
                "Custom Admin",
                "secure_password",
                is_superuser=True
            )
            assert custom_admin is not None

            # Simuler l'initialisation qui vérifie s'il y a des users
            user_count = UserService.count_users(session)

            # Si des users existent, ne pas créer l'admin par défaut
            if user_count > 0:
                # Skip
                pass
            else:
                # Créer admin par défaut (ne devrait pas arriver)
                UserService.create_user(
                    session, "admin@mppeep.com", "Admin", "admin123", is_superuser=True
                )

            # Vérifier qu'il n'y a toujours qu'un seul admin
            final_count = UserService.count_users(session)
            assert final_count == 1

            # Vérifier que c'est bien le custom admin
            admin_check = UserService.get_by_email(session, "custom_admin@company.com")
            assert admin_check is not None
            assert admin_check.is_superuser is True

        temp_engine.dispose()

    finally:
        if os.path.exists(temp_db):
            os.unlink(temp_db)


@pytest.mark.functional
@pytest.mark.database
def test_admin_login_after_initialization(test_session):
    """Test que l'admin peut se connecter après initialisation"""
    # Créer l'admin (comme lors de l'initialisation)
    admin = UserService.create_user(
        test_session,
        "admin@mppeep.com",
        "Administrateur MPPEEP",
        "admin123",
        is_active=True,
        is_superuser=True
    )

    assert admin is not None

    # Tester la connexion
    authenticated = UserService.authenticate(
        test_session, "admin@mppeep.com", "admin123"
    )

    assert authenticated is not None
    assert authenticated.id == admin.id
    assert authenticated.is_active is True
    assert authenticated.is_superuser is True

    # Tester avec un mauvais mot de passe
    failed_auth = UserService.authenticate(
        test_session, "admin@mppeep.com", "wrong_password"
    )

    assert failed_auth is None

