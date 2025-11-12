"""
Configuration de l'application
"""

import datetime
import subprocess
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid",  # on verrouille
        case_sensitive=False,  # accepte MIN/maj dans .env
        env_nested_delimiter="__",
    )
    # ==========================================
    # APPLICATION
    # ==========================================
    APP_NAME: str = "SYGEP"
    ENV: Literal["dev", "staging", "prod"] = "prod"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-in-production"

    # ROOT_PATH configuré dynamiquement selon l'environnement
    # Vide en dev (accès direct), /mppeep en prod (derrière proxy)
    ROOT_PATH: str = ""

    # ==========================================
    # DATABASE
    # ==========================================

    # SQLite (dev)
    SQLITE_DB_PATH: str = "./app.db"

    # PostgreSQL (production)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"  # Utiliser "db" en production Docker
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "postgres"
    
    # URL complète de la base de données (prioritaire sur les valeurs individuelles)
    DATABASE_URL: str | None = None
    # ==========================================
    # CORS & SECURITY
    # ==========================================
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "*.skpartners.consulting", "skpartners.consulting"]
    CORS_ALLOW_ALL: bool = False  # True = autorise toutes les origines (dev uniquement)

    # ==========================================
    # MIDDLEWARES (configurés automatiquement selon DEBUG/ENV)
    # Les valeurs peuvent être overridées dans .env
    # ==========================================
    # Sécurité (toujours actifs)
    ENABLE_CORS: bool = True
    ENABLE_ERROR_HANDLING: bool = True
    ENABLE_LOGGING: bool = True
    ENABLE_REQUEST_ID: bool = True
    ENABLE_REQUEST_SIZE_LIMIT: bool = True

    # Filtres optionnels (manuels)
    ENABLE_IP_FILTER: bool = False  # Activer manuellement si nécessaire
    ENABLE_USER_AGENT_FILTER: bool = False  # Activer manuellement si nécessaire

    # Les middlewares ci-dessous utilisent les properties should_enable_*
    # qui s'activent automatiquement selon DEBUG (voir plus bas)
    # Valeurs par défaut (overridable via .env) :
    ENABLE_GZIP: bool = True  # → OFF si DEBUG=True
    ENABLE_CACHE_CONTROL: bool = True  # → OFF si DEBUG=True
    ENABLE_SECURITY_HEADERS: bool = True  # → OFF si DEBUG=True
    ENABLE_CSP: bool = True  # → OFF si DEBUG=True
    ENABLE_HTTPS_REDIRECT: bool = False  # → ON si DEBUG=False
    ENABLE_FORWARD_PROTO: bool = False  # → ON si DEBUG=False
    ENABLE_CLOUDFLARE: bool = False  # → ON si DEBUG=False

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
    
    # Charte de confidentialité
    PRIVACY_POLICY_VERSION: str = "1.0"  # Version actuelle de la charte
    PRIVACY_POLICY_REQUIRED: bool = True  # Forcer l'acceptation

    # ==========================================
    # PROPERTIES DYNAMIQUES (selon DEBUG/ENV)
    # ==========================================

    @property
    def should_enable_https_redirect(self) -> bool:
        """Active la redirection HTTPS uniquement si DEBUG=False"""
        if self.DEBUG:
            return False
        return self.ENABLE_HTTPS_REDIRECT

    @property
    def should_enable_security_headers(self) -> bool:
        """Active les headers de sécurité uniquement si DEBUG=False"""
        if self.DEBUG:
            return False
        return self.ENABLE_SECURITY_HEADERS

    @property
    def should_enable_csp(self) -> bool:
        """Active CSP uniquement si DEBUG=False"""
        if self.DEBUG:
            return False
        return self.ENABLE_CSP

    @property
    def should_enable_gzip(self) -> bool:
        """Active Gzip uniquement si DEBUG=False"""
        if self.DEBUG:
            return False
        return self.ENABLE_GZIP

    @property
    def should_enable_cache_control(self) -> bool:
        """Active le cache control uniquement si DEBUG=False"""
        if self.DEBUG:
            return False
        return self.ENABLE_CACHE_CONTROL

    @property
    def should_enable_forward_proto(self) -> bool:
        """Active ForwardProto uniquement si DEBUG=False"""
        if self.DEBUG:
            return False
        return self.ENABLE_FORWARD_PROTO

    @property
    def should_enable_cloudflare(self) -> bool:
        """Active Cloudflare uniquement si DEBUG=False"""
        if self.DEBUG:
            return False
        return self.ENABLE_CLOUDFLARE

    @property
    def get_root_path(self) -> str:
        """
        Retourne ROOT_PATH selon l'environnement
        - Dev/Debug : vide (accès direct sans préfixe)
        - Prod : /mppeep (derrière reverse proxy)
        """

        # Sinon, automatique selon DEBUG
        if self.DEBUG:
            return ""  # Dev : pas de préfixe
        else:
            return "/mppeep"  # Prod : avec préfixe

    @property
    def database_url(self) -> str:
        """
        Retourne l'URL de la base de données selon l'environnement

        - Si DATABASE_URL est défini dans les variables d'environnement → utilise cette valeur (PRIORITAIRE)
        - Sinon, si DEBUG=True ou ENV=dev → SQLite
        - Sinon → PostgreSQL (construit à partir des variables individuelles)
        """
        
        # PRIORITÉ 1 : Si DATABASE_URL est défini explicitement dans les env vars, l'utiliser
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        # PRIORITÉ 2 : Si DEBUG=True, utiliser SQLite
        if self.DEBUG:
            return f"sqlite:///{self.SQLITE_DB_PATH}"
        
        # PRIORITÉ 3 : Construire l'URL PostgreSQL à partir des variables individuelles
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @staticmethod
    def _get_asset_version() -> str:
        """Génère la version des assets pour le cache busting"""
        import os

        env_version = os.getenv("ASSET_VERSION")
        if env_version:
            return env_version

        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
            ).strip()
            if commit:
                return commit[:8]
        except Exception:
            pass
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    ASSET_VERSION: str = Field(default_factory=_get_asset_version)


settings = Settings()
