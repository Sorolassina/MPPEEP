"""
Configuration de l'application
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid",         # on verrouille
        case_sensitive=False,   # accepte MIN/maj dans .env
        env_nested_delimiter="__",
    )
    # ==========================================
    # APPLICATION
    # ==========================================
    APP_NAME: str = "MPPEEP Dashboard"
    ENV: Literal["dev", "staging", "production"] = "dev"
    DEBUG: bool = True
    SECRET_KEY: str = "changeme-in-production"
    
    # ==========================================
    # DATABASE
    # ==========================================
    DATABASE_URL: str | None = None
    
    # SQLite (dev)
    SQLITE_DB_PATH: str = "./app.db"
    
    # PostgreSQL (production)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mppeep"
    
    # ==========================================
    # CORS & SECURITY
    # ==========================================
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ALLOW_ALL: bool = False  # True = autorise toutes les origines (dev uniquement)
    
    # ==========================================
    # MIDDLEWARES
    # ==========================================
    ENABLE_HTTPS_REDIRECT: bool = False  # True en production
    ENABLE_CORS: bool = True
    ENABLE_GZIP: bool = True
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_LOGGING: bool = True
    ENABLE_REQUEST_ID: bool = True
    ENABLE_CACHE_CONTROL: bool = True
    ENABLE_CSP: bool = True
    ENABLE_ERROR_HANDLING: bool = True
    ENABLE_IP_FILTER: bool = False  # Activer si nécessaire
    ENABLE_USER_AGENT_FILTER: bool = False  # Activer si nécessaire
    ENABLE_REQUEST_SIZE_LIMIT: bool = True


    # ==========================================
    # CLOUDFLARE
    # ==========================================
    CLOUDFLARE_API_TOKEN: str = ""
    CLOUDFLARE_ZONE_ID: str = ""
    CLOUDFLARE_DOMAIN: str = ""
    
    # ============================================
    # EMAIL (Configuration SMTP)
    # ============================================
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    
    # ============================================
    # MONITORING & LOGS
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # ============================================
    # LIMITES & QUOTAS
    # ============================================
    MAX_REQUEST_SIZE: int = 10485760
    MAX_LOGIN_ATTEMPTS: int = 5
    SESSION_TIMEOUT: int = 3600
    PASSWORD_MIN_LENGTH: int = 8

    
    @property
    def database_url(self) -> str:
        """
        Retourne l'URL de la base de données selon l'environnement
        
        - Si DATABASE_URL est défini → utilise cette valeur
        - Sinon, si DEBUG=True ou ENV=dev → SQLite
        - Sinon → PostgreSQL
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        if self.DEBUG or self.ENV == "dev":
            return f"sqlite:///{self.SQLITE_DB_PATH}"
        else:
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

settings = Settings()
