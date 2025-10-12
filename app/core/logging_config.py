"""
Configuration du système de logging
- Root : centralise tous les logs (console + fichiers)
- Logger 'mppeep' : niveau affiné, pas de handler
- Logger 'mppeep.access' : handler dédié access.log, pas de propagation
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from app.core.config import settings

# (Optionnel) Windows : activer les couleurs ANSI en console
try:
    import colorama  # pip install colorama
    colorama.just_fix_windows_console()
except Exception:
    pass


class ColoredFormatter(logging.Formatter):
    """Formateur avec couleurs pour la console"""
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Vert
        'WARNING': '\033[33m',    # Jaune
        'ERROR': '\033[31m',      # Rouge
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    def format(self, record):
        levelname_original = record.levelname
        if levelname_original in self.COLORS:
            record.levelname = f"{self.COLORS[levelname_original]}{levelname_original}{self.COLORS['RESET']}"
        result = super().format(record)
        record.levelname = levelname_original
        return result


def setup_logging() -> logging.Logger:
    """
    Configure le système de logging complet (idempotent).
    Fichiers :
      - logs/app.log      : tous les niveaux
      - logs/error.log    : >= ERROR
      - logs/access.log   : accès HTTP (logger dédié)
    Console :
      - stdout : < ERROR (coloré)
      - stderr : >= ERROR (coloré)
    """
    # --- idempotence : si déjà configuré, ne rien refaire ---
    root = logging.getLogger()
    if getattr(root, "_mppeep_configured", False):
        return logging.getLogger("mppeep")

    # Dossier logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Niveaux
    global_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Nettoyer le root
    root.handlers.clear()
    root.setLevel(global_level)

    # Logger applicatif (pas de handlers → propagation vers root)
    app_logger = logging.getLogger("mppeep")
    app_logger.setLevel(global_level)
    app_logger.handlers.clear()      # important : pas de handler ici
    app_logger.propagate = True

    # ---------- Formats ----------
    file_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_color = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # ---------- Handlers console ----------
    class StdoutFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.levelno < logging.ERROR

    h_stdout = logging.StreamHandler(sys.stdout)
    h_stdout.setLevel(logging.DEBUG)       # laisse passer, filtré par le logger + filtre
    h_stdout.setFormatter(console_color)
    h_stdout.addFilter(StdoutFilter())

    h_stderr = logging.StreamHandler(sys.stderr)
    h_stderr.setLevel(logging.ERROR)
    h_stderr.setFormatter(console_color)

    root.addHandler(h_stdout)
    root.addHandler(h_stderr)

    # ---------- Fichiers ----------
    h_app = RotatingFileHandler(
        filename=log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    h_app.setLevel(logging.DEBUG)
    h_app.setFormatter(file_format)
    root.addHandler(h_app)

    h_err = RotatingFileHandler(
        filename=log_dir / "error.log", maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    h_err.setLevel(logging.ERROR)
    h_err.setFormatter(file_format)
    root.addHandler(h_err)

    # ---------- Access logger dédié ----------
    access_logger = logging.getLogger("mppeep.access")
    access_logger.setLevel(logging.INFO)
    access_logger.handlers.clear()
    access_logger.propagate = False  # évite double écriture console/app.log

    h_access = RotatingFileHandler(
        filename=log_dir / "access.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    h_access.setLevel(logging.INFO)
    h_access.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    access_logger.addHandler(h_access)

    # ---------- Harmoniser Uvicorn ----------
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()   # on laisse le root gérer (sauf access si tu veux un fichier dédié)
        lg.setLevel(root.level)
        lg.propagate = True

    # ---------- Bannière ----------
    app_logger.info("=" * 60)
    app_logger.info("🚀 Système de logging initialisé")
    app_logger.info("=" * 60)
    app_logger.info(f"📂 Dossier logs : {log_dir.absolute()}")
    app_logger.info("📄 Logs généraux : logs/app.log")
    app_logger.info("❌ Logs erreurs : logs/error.log")
    app_logger.info("🌐 Logs accès : logs/access.log")
    app_logger.info(f"🔍 Niveau de log : {app_logger.level}")
    app_logger.info(f"🏷️  Environnement : {settings.ENV}")
    app_logger.info(f"🐛 Debug mode : {settings.DEBUG}")
    app_logger.info("=" * 60)

    # Marqueur d'initialisation (persiste tant que le process vit)
    setattr(root, "_mppeep_configured", True)
    return app_logger


# ⚠️ Évite d’appeler setup_logging() au moment de l’import si tu utilises --reload.
# Appelle-le explicitement dans main.py / asgi.py (au démarrage de l’appli).
app_logger = setup_logging()

def get_logger(name: str = "mppeep") -> logging.Logger:
    """Récupérer un logger pour un module."""
    return logging.getLogger(name)

# Logger d'accès HTTP séparé (déjà configuré ci-dessus)
access_logger = logging.getLogger("mppeep.access")

__all__ = ["setup_logging", "get_logger", "app_logger", "access_logger"]
