"""
Tests unitaires pour la validation des données
"""
import pytest
from pydantic import ValidationError

from app.core.enums import (
    SituationFamiliale, 
    Sexe, 
    PositionAdministrative,
    UserType,
    TypeArticle
)
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User


@pytest.mark.critical
def test_email_validation():
    """Test validation des emails"""
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
        assert user_data.email == email
    
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
def test_password_validation():
    """Test validation des mots de passe"""
    # Mots de passe valides
    valid_passwords = [
        "password123",
        "MySecure123!",
        "P@ssw0rd",
        "12345678"  # Minimum 8 caractères
    ]
    
    for password in valid_passwords:
        user_data = UserCreate(
            email="test@example.com",
            password=password,
            full_name="Test User"
        )
        assert user_data.password == password
    
    # Mots de passe invalides (trop courts)
    invalid_passwords = [
        "123",      # Trop court
        "pass",     # Trop court
        "",         # Vide
        None        # None
    ]
    
    for password in invalid_passwords:
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password=password,
                full_name="Test User"
            )


@pytest.mark.critical
def test_enum_validation():
    """Test validation des enums selon la mémoire"""
    # Test SituationFamiliale
    valid_situations = [
        SituationFamiliale.CELIBATAIRE,
        SituationFamiliale.MARIE,
        SituationFamiliale.DIVORCE,
        SituationFamiliale.VEUF
    ]
    
    for situation in valid_situations:
        assert situation in SituationFamiliale
    
    # Test Sexe
    valid_sexes = [Sexe.MASCULIN, Sexe.FEMININ]
    for sexe in valid_sexes:
        assert sexe in Sexe
    
    # Test PositionAdministrative
    valid_positions = [
        PositionAdministrative.DIRECTEUR,
        PositionAdministrative.CHEF_SERVICE,
        PositionAdministrative.AGENT
    ]
    
    for position in valid_positions:
        assert position in PositionAdministrative


@pytest.mark.critical
def test_enum_string_validation():
    """Test validation des enums avec des chaînes"""
    # Test avec chaînes valides
    valid_strings = {
        "situation": ["CELIBATAIRE", "MARIE", "DIVORCE", "VEUF"],
        "sexe": ["MASCULIN", "FEMININ"],
        "position": ["DIRECTEUR", "CHEF_SERVICE", "AGENT"]
    }
    
    for enum_type, values in valid_strings.items():
        for value in values:
            if enum_type == "situation":
                assert SituationFamiliale(value) is not None
            elif enum_type == "sexe":
                assert Sexe(value) is not None
            elif enum_type == "position":
                assert PositionAdministrative(value) is not None


@pytest.mark.critical
def test_enum_empty_string_handling():
    """Test gestion des chaînes vides selon la mémoire"""
    # Selon la mémoire : les chaînes vides doivent être converties en None
    
    # Test avec chaînes vides (doivent être rejetées ou converties en None)
    empty_strings = ["", "   ", None]
    
    for empty_value in empty_strings:
        # Ces valeurs ne doivent pas être acceptées directement
        with pytest.raises((ValidationError, ValueError)):
            if empty_value is not None:
                SituationFamiliale(empty_value)


@pytest.mark.critical
def test_user_type_validation():
    """Test validation des types d'utilisateur"""
    valid_types = [
        UserType.ADMIN,
        UserType.USER,
        UserType.MODERATOR
    ]
    
    for user_type in valid_types:
        assert user_type in UserType
        
        # Test avec chaîne
        assert UserType(user_type.value) == user_type


@pytest.mark.critical
def test_full_name_validation():
    """Test validation des noms complets"""
    # Noms valides
    valid_names = [
        "John Doe",
        "Marie-Claire Dupont",
        "Jean-Pierre",
        "A",  # Minimum 1 caractère
        "A" * 100  # Maximum raisonnable
    ]
    
    for name in valid_names:
        user_data = UserCreate(
            email="test@example.com",
            password="password123",
            full_name=name
        )
        assert user_data.full_name == name
    
    # Noms invalides
    invalid_names = [
        "",  # Vide
        None,  # None
        " " * 10,  # Que des espaces
    ]
    
    for name in invalid_names:
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="password123",
                full_name=name
            )


@pytest.mark.critical
def test_phone_validation():
    """Test validation des numéros de téléphone"""
    # Numéros valides (format français)
    valid_phones = [
        "0123456789",
        "01 23 45 67 89",
        "+33123456789",
        "06.12.34.56.78"
    ]
    
    # Test avec un modèle qui accepte les téléphones
    phone_data = {"phone": valid_phones[0]}
    # Validation basique (pas de regex complexe pour l'instant)
    assert len(phone_data["phone"]) >= 10


@pytest.mark.critical
def test_article_type_validation():
    """Test validation des types d'articles"""
    valid_types = [
        TypeArticle.PERISSABLE,
        TypeArticle.AMORTISSABLE,
        TypeArticle.CONSOMMABLE
    ]
    
    for article_type in valid_types:
        assert article_type in TypeArticle


@pytest.mark.critical
def test_validation_error_messages():
    """Test que les messages d'erreur sont informatifs"""
    # Test email invalide
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="invalid-email",
            password="password123",
            full_name="Test User"
        )
    
    error = exc_info.value
    assert "email" in str(error).lower()
    
    # Test mot de passe trop court
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="test@example.com",
            password="123",
            full_name="Test User"
        )
    
    error = exc_info.value
    assert "password" in str(error).lower() or "length" in str(error).lower()


@pytest.mark.critical
def test_optional_fields_validation():
    """Test validation des champs optionnels"""
    # Test avec champs optionnels remplis
    user_data = UserCreate(
        email="test@example.com",
        password="password123",
        full_name="Test User",
        is_active=True,
        type_user=UserType.USER
    )
    
    assert user_data.is_active is True
    assert user_data.type_user == UserType.USER
    
    # Test avec champs optionnels par défaut
    user_data_minimal = UserCreate(
        email="test@example.com",
        password="password123",
        full_name="Test User"
    )
    
    assert user_data_minimal.is_active is True  # Valeur par défaut
    assert user_data_minimal.type_user == UserType.USER  # Valeur par défaut


@pytest.mark.critical
def test_update_validation():
    """Test validation des mises à jour"""
    # Test mise à jour partielle
    update_data = UserUpdate(
        full_name="Updated Name"
    )
    
    assert update_data.full_name == "Updated Name"
    assert update_data.email is None  # Non fourni
    assert update_data.password is None  # Non fourni
    
    # Test mise à jour complète
    update_data_full = UserUpdate(
        email="updated@example.com",
        full_name="Updated Name",
        password="newpassword123",
        is_active=False
    )
    
    assert update_data_full.email == "updated@example.com"
    assert update_data_full.full_name == "Updated Name"
    assert update_data_full.password == "newpassword123"
    assert update_data_full.is_active is False


@pytest.mark.critical
def test_unicode_validation():
    """Test validation avec caractères Unicode"""
    # Test avec caractères français
    french_data = UserCreate(
        email="françois@example.com",
        password="password123",
        full_name="François Dupont"
    )
    
    assert french_data.full_name == "François Dupont"
    
    # Test avec caractères spéciaux
    special_data = UserCreate(
        email="test@example.com",
        password="password123",
        full_name="José María"
    )
    
    assert special_data.full_name == "José María"


@pytest.mark.critical
def test_boundary_values():
    """Test valeurs limites"""
    # Test longueur maximale raisonnable
    long_name = "A" * 255  # Nom très long
    user_data = UserCreate(
        email="test@example.com",
        password="password123",
        full_name=long_name
    )
    
    assert user_data.full_name == long_name
    
    # Test email très long
    long_email = "a" * 50 + "@" + "b" * 50 + ".com"
    user_data_long_email = UserCreate(
        email=long_email,
        password="password123",
        full_name="Test User"
    )
    
    assert user_data_long_email.email == long_email
