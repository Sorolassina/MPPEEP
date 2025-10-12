"""
Tests unitaires pour les validateurs
"""
import pytest
from app.utils.validators import (
    validate_email,
    validate_password_strength,
    validate_username,
    validate_phone_number,
    validate_url
)


def test_validate_email_valid():
    """Test validation d'emails valides"""
    valid_emails = [
        "user@example.com",
        "john.doe@example.com",
        "user+tag@example.co.uk",
        "123@example.com",
    ]
    
    for email in valid_emails:
        is_valid, error = validate_email(email)
        assert is_valid is True, f"{email} devrait être valide"
        assert error == ""


def test_validate_email_invalid():
    """Test validation d'emails invalides"""
    invalid_emails = [
        "",
        "invalid",
        "@example.com",
        "user@",
        "user @example.com",
        "user@example",
    ]
    
    for email in invalid_emails:
        is_valid, error = validate_email(email)
        assert is_valid is False, f"{email} devrait être invalide"
        assert error != ""


def test_validate_password_strength_valid():
    """Test validation de mots de passe valides"""
    valid_passwords = [
        "Password123",
        "MyP@ssw0rd",
        "Abcd1234",
        "StrongPass1",
    ]
    
    for password in valid_passwords:
        is_valid, error = validate_password_strength(password)
        assert is_valid is True, f"{password} devrait être valide"
        assert error == ""


def test_validate_password_strength_invalid():
    """Test validation de mots de passe invalides"""
    test_cases = [
        ("", "requis"),
        ("short", "8 caractères"),
        ("nouppercase123", "majuscule"),
        ("NOLOWERCASE123", "minuscule"),
        ("NoDigits", "chiffre"),
    ]
    
    for password, expected_error in test_cases:
        is_valid, error = validate_password_strength(password)
        assert is_valid is False
        assert expected_error.lower() in error.lower()


def test_validate_username_valid():
    """Test validation de noms d'utilisateur valides"""
    valid_usernames = [
        "john",
        "john_doe",
        "john-doe",
        "user123",
        "JohnDoe",
    ]
    
    for username in valid_usernames:
        is_valid, error = validate_username(username)
        assert is_valid is True
        assert error == ""


def test_validate_username_invalid():
    """Test validation de noms d'utilisateur invalides"""
    invalid_usernames = [
        "",
        "ab",  # Trop court
        "john doe",  # Espace
        "john@doe",  # Caractère spécial
        "john.doe",  # Point
    ]
    
    for username in invalid_usernames:
        is_valid, error = validate_username(username)
        assert is_valid is False
        assert error != ""


def test_validate_phone_number_french():
    """Test validation de numéros français"""
    valid_phones = [
        "0612345678",
        "06 12 34 56 78",
        "06-12-34-56-78",
        "+33612345678",
    ]
    
    for phone in valid_phones:
        is_valid, error = validate_phone_number(phone, "FR")
        assert is_valid is True, f"{phone} devrait être valide"


def test_validate_url_valid():
    """Test validation d'URLs valides"""
    valid_urls = [
        "https://example.com",
        "http://example.com",
        "https://www.example.com/path",
        "http://localhost:8000",
        "https://192.168.1.1",
    ]
    
    for url in valid_urls:
        is_valid, error = validate_url(url)
        assert is_valid is True, f"{url} devrait être valide"


def test_validate_url_invalid():
    """Test validation d'URLs invalides"""
    invalid_urls = [
        "",
        "not a url",
        "ftp://example.com",  # Pas http/https
        "example.com",  # Pas de protocole
        "http://",
    ]
    
    for url in invalid_urls:
        is_valid, error = validate_url(url)
        assert is_valid is False, f"{url} devrait être invalide"

