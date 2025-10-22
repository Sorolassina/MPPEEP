"""
Tests unitaires pour la validation des données existantes
"""

import pytest
from pydantic import ValidationError

from app.core.enums import (
    UserType,
    FileType,
    FileStatus
)
from app.schemas.user import UserCreate
from app.schemas.file import FileUploadMetadata
from app.models.user import User
from app.models.file import File


@pytest.mark.critical
@pytest.mark.unit
def test_user_create_validation():
    """Test validation du schéma UserCreate - EXISTANT"""
    # Email valide
    user_data = UserCreate(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )
    assert user_data.email == "test@example.com"
    assert user_data.password == "password123"
    assert user_data.full_name == "Test User"
    
    # Email avec majuscules (doit être converti en minuscules)
    user_data = UserCreate(
        email="TEST@EXAMPLE.COM",
        password="password123",
        full_name="Test User"
    )
    assert user_data.email == "test@example.com"


@pytest.mark.critical
@pytest.mark.unit
def test_user_create_email_validation():
    """Test validation des emails - EXISTANT"""
    # Emails valides
    valid_emails = [
        "user@example.com",
        "test.user@domain.co.uk",
        "user+tag@example.org",
        "user123@test-domain.com"
    ]
    
    for email in valid_emails:
        user_data = UserCreate(
            email=email,
            password="password123",
            full_name="Test User"
        )
        assert user_data.email == email.lower()
    
    # Emails invalides
    invalid_emails = [
        "invalid-email",
        "@example.com",
        "user@",
        "user@.com",
        "",
        None
    ]
    
    for email in invalid_emails:
        with pytest.raises(ValidationError):
            UserCreate(
                email=email,
                password="password123",
                full_name="Test User"
            )


@pytest.mark.critical
@pytest.mark.unit
def test_user_create_password_validation():
    """Test validation des mots de passe - EXISTANT"""
    # Mot de passe valide
    user_data = UserCreate(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )
    assert user_data.password == "password123"
    
    # Mot de passe trop court
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password="123",
            full_name="Test User"
        )
    
    # Mot de passe vide
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password="",
            full_name="Test User"
        )


@pytest.mark.critical
@pytest.mark.unit
def test_user_create_full_name_validation():
    """Test validation du nom complet - EXISTANT"""
    # Nom valide
    user_data = UserCreate(
        email="test@example.com",
        password="password123",
        full_name="Jean Dupont"
    )
    assert user_data.full_name == "Jean Dupont"
    
    # Nom avec espaces multiples (doit être nettoyé)
    user_data = UserCreate(
        email="test@example.com",
        password="password123",
        full_name="  Jean   Dupont  "
    )
    assert user_data.full_name == "Jean Dupont"
    
    # Nom avec chiffres seulement (doit échouer)
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password="password123",
            full_name="123456"
        )


@pytest.mark.critical
@pytest.mark.unit
def test_file_upload_metadata_validation():
    """Test validation du schéma FileUploadMetadata - EXISTANT"""
    # Métadonnées valides (utiliser FileType.BUDGET.value)
    metadata = FileUploadMetadata(
        file_type=FileType.BUDGET.value,  # "données budgétaires"
        program="Programme Test",
        period="2024-01",
        title="Fichier Budget Test",
        description="Description optionnelle"
    )
    assert metadata.file_type == FileType.BUDGET.value
    assert metadata.program == "Programme Test"
    assert metadata.period == "2024-01"
    assert metadata.title == "Fichier Budget Test"
    assert metadata.description == "Description optionnelle"


@pytest.mark.critical
@pytest.mark.unit
def test_file_type_validation():
    """Test validation du type de fichier - EXISTANT"""
    # Types valides
    valid_types = [ft.value for ft in FileType]
    
    for file_type in valid_types:
        metadata = FileUploadMetadata(
            file_type=file_type,
            program="Programme Test",
            period="2024-01",
            title="Fichier Test"
        )
        assert metadata.file_type == file_type
    
    # Type invalide
    with pytest.raises(ValidationError):
        FileUploadMetadata(
            file_type="invalid_type",
            program="Programme Test",
            period="2024-01",
            title="Fichier Test"
        )


@pytest.mark.critical
@pytest.mark.unit
def test_file_period_validation():
    """Test validation de la période - EXISTANT"""
    # Période valide
    metadata = FileUploadMetadata(
        file_type=FileType.AUTRE.value,  # Utiliser un type valide
        program="Programme Test",
        period="2024-01",
        title="Fichier Test"
    )
    assert metadata.period == "2024-01"
    
    # Période avec espaces (doit être nettoyée)
    metadata = FileUploadMetadata(
        file_type=FileType.AUTRE.value,
        program="Programme Test",
        period="  2024-01  ",
        title="Fichier Test"
    )
    assert metadata.period == "2024-01"
    
    # Période vide (doit échouer)
    with pytest.raises(ValidationError):
        FileUploadMetadata(
            file_type=FileType.AUTRE.value,
            program="Programme Test",
            period="",
            title="Fichier Test"
        )


@pytest.mark.critical
@pytest.mark.unit
def test_user_model_properties():
    """Test des propriétés du modèle User - EXISTANT"""
    # Utilisateur admin
    admin_user = User(
        email="admin@example.com",
        hashed_password="hashed_password",
        type_user=UserType.ADMIN.value
    )
    assert admin_user.is_admin is True
    
    # Utilisateur normal
    normal_user = User(
        email="user@example.com",
        hashed_password="hashed_password",
        type_user=UserType.AGENT.value  # "agent"
    )
    assert normal_user.is_admin is False


@pytest.mark.critical
@pytest.mark.unit
def test_enum_values():
    """Test des valeurs d'enum - EXISTANT"""
    # UserType (valeurs réelles)
    assert UserType.ADMIN.value == "admin"
    assert UserType.AGENT.value == "agent"  # Pas "user" mais "agent"
    assert UserType.INVITE.value == "invité"
    
    # FileType (valeurs réelles)
    assert FileType.BUDGET.value == "données budgétaires"
    assert FileType.AUTRE.value == "autre"
    assert FileType.FICHE_PERSONNEL.value == "fiche personnel"
    
    # FileStatus (valeurs réelles en français)
    assert FileStatus.UPLOADED.value == "téléchargé"
    assert FileStatus.PROCESSING.value == "en traitement"
    assert FileStatus.PROCESSED.value == "traité"
    assert FileStatus.ERROR.value == "erreur"


@pytest.mark.critical
@pytest.mark.unit
def test_enum_validation():
    """Test validation des enums - EXISTANT"""
    # Test UserType (valeurs réelles)
    valid_user_types = [ut.value for ut in UserType]
    assert "admin" in valid_user_types
    assert "agent" in valid_user_types  # Pas "user"
    assert "invité" in valid_user_types  # Pas "guest"
    assert "chef service" in valid_user_types
    
    # Test FileType (valeurs réelles)
    valid_file_types = [ft.value for ft in FileType]
    assert "données budgétaires" in valid_file_types
    assert "autre" in valid_file_types
    assert "fiche personnel" in valid_file_types
    
    # Test FileStatus (valeurs en français)
    valid_file_statuses = [fs.value for fs in FileStatus]
    assert "téléchargé" in valid_file_statuses
    assert "en traitement" in valid_file_statuses
    assert "traité" in valid_file_statuses
    assert "erreur" in valid_file_statuses


@pytest.mark.critical
@pytest.mark.unit
def test_blocked_email_domains():
    """Test des domaines email bloqués - EXISTANT"""
    blocked_domains = ["tempmail.com", "throwaway.email", "10minutemail.com"]
    
    for domain in blocked_domains:
        with pytest.raises(ValidationError):
            UserCreate(
                email=f"test@{domain}",
                password="password123",
                full_name="Test User"
            )


@pytest.mark.critical
@pytest.mark.unit
def test_user_model_fields():
    """Test des champs du modèle User - EXISTANT"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True,
        type_user=UserType.AGENT.value
    )
    
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.type_user == UserType.AGENT.value
    assert user.is_superuser is False  # Valeur par défaut


@pytest.mark.critical
@pytest.mark.unit
def test_file_model_fields():
    """Test des champs du modèle File - EXISTANT"""
    file_obj = File(
        original_filename="test.xlsx",
        stored_filename="stored_test.xlsx",
        file_path="/path/to/file.xlsx",
        file_size=1024,
        file_type=FileType.BUDGET.value,
        program="Programme Test",
        period="2024-01",
        title="Fichier Test"
    )
    
    assert file_obj.original_filename == "test.xlsx"
    assert file_obj.stored_filename == "stored_test.xlsx"
    assert file_obj.file_path == "/path/to/file.xlsx"
    assert file_obj.file_size == 1024
    assert file_obj.file_type == FileType.BUDGET.value
    assert file_obj.program == "Programme Test"
    assert file_obj.period == "2024-01"
    assert file_obj.title == "Fichier Test"
    assert file_obj.status == FileStatus.UPLOADED.value  # Valeur par défaut
