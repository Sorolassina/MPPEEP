"""
Tests unitaires pour la configuration de l'application
"""
import pytest
from app.core.config import Settings


@pytest.mark.critical
def test_default_config():
    """Test la configuration par défaut"""
    settings = Settings()
    
    assert settings.APP_NAME == "MPPEEP Dashboard"
    assert settings.ENV == "dev"
    assert settings.DEBUG is True
    # SECRET_KEY peut être surchargée par variable d'environnement
    assert settings.SECRET_KEY is not None
    assert len(settings.SECRET_KEY) > 0


def test_database_url_auto_sqlite_debug_true():
    """Test que DEBUG=True utilise SQLite"""
    settings = Settings(DEBUG=True, ENV="production")
    
    assert settings.database_url.startswith("sqlite:///")


def test_database_url_auto_sqlite_env_dev():
    """Test que ENV=dev utilise SQLite"""
    settings = Settings(DEBUG=False, ENV="dev")
    
    assert settings.database_url.startswith("sqlite:///")


def test_database_url_auto_postgres_production():
    """Test que DEBUG=False et ENV=production utilise PostgreSQL"""
    settings = Settings(DEBUG=False, ENV="production")
    
    assert settings.database_url.startswith("postgresql://")


def test_database_url_manual_override():
    """Test que DATABASE_URL manuel a la priorité"""
    custom_url = "postgresql://custom:password@localhost:5432/custom_db"
    settings = Settings(DATABASE_URL=custom_url, DEBUG=True)
    
    assert settings.database_url == custom_url


def test_postgres_connection_string():
    """Test la construction de la chaîne PostgreSQL"""
    settings = Settings(
        DEBUG=False,
        ENV="production",
        POSTGRES_USER="myuser",
        POSTGRES_PASSWORD="mypass",
        POSTGRES_HOST="db.example.com",
        POSTGRES_PORT=5433,
        POSTGRES_DB="mydb"
    )
    
    expected = "postgresql://myuser:mypass@db.example.com:5433/mydb"
    assert settings.database_url == expected


def test_env_values_validation():
    """Test la validation des valeurs ENV"""
    # ENV ne peut être que dev, staging ou production
    settings = Settings(ENV="dev")
    assert settings.ENV == "dev"
    
    settings = Settings(ENV="staging")
    assert settings.ENV == "staging"
    
    settings = Settings(ENV="production")
    assert settings.ENV == "production"


def test_sqlite_custom_path():
    """Test un chemin SQLite personnalisé"""
    settings = Settings(
        DEBUG=True,
        SQLITE_DB_PATH="./custom_test.db"
    )
    
    assert settings.database_url == "sqlite:///./custom_test.db"

