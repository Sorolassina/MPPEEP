# app/core/logging_config.py
from __future__ import annotations

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Optional


DEFAULT_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENV = os.getenv("APP_ENV", os.getenv("ENV", "prod"))
DEBUG = os.getenv("DEBUG", "0") in {"1", "true", "True"}


def _supports_utf8_console() -> bool:
    enc = getattr(sys.stdout, "encoding", "") or ""
    return "utf" in enc.lower()


def _banner_lines(log_dir: Path) -> list[str]:
    if _supports_utf8_console():
        return [
            "=" * 60,
            "🚀 Système de logging initialisé",
            "=" * 60,
            f"📂 Dossier logs : {log_dir}",
            "📄 Logs généraux : logs/app.log",
            "❌ Logs erreurs : logs/error.log",
            "🌐 Logs accès   : logs/access.log",
            f"🔊 Niveau de log : {DEFAULT_LEVEL}",
            f"🌱  Environnement : {ENV}",
            f"🪲 Debug mode : {DEBUG}",
            "=" * 60,
        ]
    else:
        return [
            "=" * 60,
            "Systeme de logging initialise",
            "=" * 60,
            f"Dossier logs : {log_dir}",
            "Logs generaux : logs/app.log",
            "Logs erreurs  : logs/error.log",
            "Logs acces    : logs/access.log",
            f"Niveau de log : {DEFAULT_LEVEL}",
            f"Environnement : {ENV}",
            f"Debug mode    : {DEBUG}",
            "=" * 60,
        ]


def setup_logging(
    log_dir: Optional[Path] = None,
    level: str = DEFAULT_LEVEL,
    uvicorn_integration: bool = True,
) -> logging.Logger:
    """
    Configure tout le système de logs de l'application.
    À appeler UNE SEULE FOIS par process (ex: dans lifespan FastAPI).
    """
    if getattr(logging, "_mppeep_configured", False):
        # Déjà configuré dans ce process
        return logging.getLogger("mppeep")

    log_dir = Path(log_dir or DEFAULT_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Formats
    simple_fmt = "%(asctime)s | %(levelname)s | %(message)s"
    app_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    access_fmt = '%(asctime)s | %(levelname)s | %(message)s'  # uvicorn access message déjà formaté

    # Handlers (console + fichiers rotatifs)
    config = {
        "version": 1,
        "disable_existing_loggers": False,  # on laisse les loggers existants
        "formatters": {
            "simple": {"format": simple_fmt},
            "app": {"format": app_fmt},
            "access": {"format": access_fmt},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "app",
                "filename": str(log_dir / "app.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "WARNING",
                "formatter": "app",
                "filename": str(log_dir / "error.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "access_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "access",
                "filename": str(log_dir / "access.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            # Logger principal de l'app
            "mppeep": {
                "level": level,
                "handlers": ["console", "app_file", "error_file"],
                "propagate": False,
            },
            # Logger pour les accès HTTP (branché sur uvicorn.access)
            "mppeep.access": {
                "level": level,
                "handlers": ["access_file", "console"],
                "propagate": False,
            },
        },
        "root": {  # au cas où des libs loggent sans logger nommé
            "level": level,
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(config)

    app_logger = logging.getLogger("mppeep")

    # Intégration Uvicorn / FastAPI
    if uvicorn_integration:
        # uvicorn.error -> on réutilise nos handlers "mppeep"
        uv_err = logging.getLogger("uvicorn.error")
        uv_err.handlers = app_logger.handlers[:]  # même handlers (console + app_file + error_file)
        uv_err.setLevel(level)
        uv_err.propagate = False

        # uvicorn.access -> redirigé vers notre logger d'accès
        uv_acc = logging.getLogger("uvicorn.access")
        acc_logger = logging.getLogger("mppeep.access")
        uv_acc.handlers = acc_logger.handlers[:]
        uv_acc.setLevel(level)
        uv_acc.propagate = False

    # Bannière d’initialisation
    for line in _banner_lines(log_dir):
        app_logger.info(line)

    logging._mppeep_configured = True
    return app_logger


def get_logger(name: str = "mppeep") -> logging.Logger:
    """
    Récupère un logger déjà configuré par setup_logging().
    """
    return logging.getLogger(name)


# Logger d'accès HTTP séparé (déjà configuré ci-dessus)
app_logger = logging.getLogger("mppeep")
access_logger = logging.getLogger("mppeep.access")

# Export minimal utile
__all__ = ["access_logger", "app_logger", "setup_logging", "get_logger"]
