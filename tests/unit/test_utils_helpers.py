"""
Tests unitaires pour les fonctions helpers
"""
import pytest
from datetime import datetime, timedelta
from app.utils.helpers import (
    generate_random_string,
    generate_verification_code,
    slugify,
    format_file_size,
    time_ago,
    parse_bool,
    safe_int
)


def test_generate_random_string():
    """Test la génération de chaînes aléatoires"""
    s1 = generate_random_string(32)
    s2 = generate_random_string(32)
    
    assert len(s1) == 32
    assert len(s2) == 32
    assert s1 != s2  # Doivent être différents
    
    # Avec caractères spéciaux
    s3 = generate_random_string(16, include_special=True)
    assert len(s3) == 16


def test_generate_verification_code():
    """Test la génération de codes de vérification"""
    code = generate_verification_code(6)
    
    assert len(code) == 6
    assert code.isdigit()
    
    # Code de longueur différente
    code_short = generate_verification_code(4)
    assert len(code_short) == 4


def test_slugify():
    """Test la slugification de texte"""
    assert slugify("Mon Article 2024") == "mon-article-2024"
    assert slugify("Événement à Paris") == "evenement-a-paris"
    assert slugify("Test with CAPS") == "test-with-caps"
    assert slugify("Multiple   spaces") == "multiple-spaces"
    assert slugify("Special!@#$%chars") == "specialchars"
    assert slugify("") == ""
    assert slugify("Café") == "cafe"


def test_format_file_size():
    """Test le formatage de taille de fichier"""
    assert format_file_size(0) == "0.0 B"
    assert format_file_size(1023) == "1023.0 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1536) == "1.5 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(1073741824) == "1.0 GB"


def test_time_ago():
    """Test le formatage 'il y a X'"""
    now = datetime.now()
    
    # À l'instant
    assert time_ago(now) == "à l'instant"
    
    # Minutes
    five_minutes_ago = now - timedelta(minutes=5)
    assert "5 minute" in time_ago(five_minutes_ago)
    
    # Heures
    two_hours_ago = now - timedelta(hours=2)
    assert "2 heure" in time_ago(two_hours_ago)
    
    # Jours
    three_days_ago = now - timedelta(days=3)
    assert "3 jour" in time_ago(three_days_ago)


def test_parse_bool():
    """Test le parsing de booléens"""
    # True values
    assert parse_bool(True) is True
    assert parse_bool("true") is True
    assert parse_bool("True") is True
    assert parse_bool("1") is True
    assert parse_bool("yes") is True
    assert parse_bool("oui") is True
    assert parse_bool("on") is True
    
    # False values
    assert parse_bool(False) is False
    assert parse_bool("false") is False
    assert parse_bool("0") is False
    assert parse_bool("no") is False
    assert parse_bool("") is False
    assert parse_bool(None) is False


def test_safe_int():
    """Test la conversion sûre en int"""
    assert safe_int("123") == 123
    assert safe_int(456) == 456
    assert safe_int("abc") == 0
    assert safe_int("abc", -1) == -1
    assert safe_int(None) == 0
    assert safe_int("12.5") == 12

