"""
Configuration centralisée des chemins de l'application
"""
from pathlib import Path
from typing import Dict

# Répertoire de base du projet
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class PathConfig:
    """
    Configuration centralisée des chemins de l'application
    
    Usage:
        from app.core.path_config import path_config
        
        logo_path = path_config.get_file_path("static", "images/logo.png")
    """
    
    def __init__(self):
        # === CHEMINS DE BASE ===
        self.BASE_DIR = BASE_DIR
        self.STATIC_DIR = BASE_DIR / "app" / "static"
        self.TEMPLATES_DIR = BASE_DIR / "app" / "templates"
        self.UPLOADS_DIR = BASE_DIR / "uploads"
        self.MEDIA_DIR = BASE_DIR / "media"
        
        # === CHEMINS SPÉCIFIQUES ===
        self.STATIC_CSS_DIR = self.STATIC_DIR / "css"
        self.STATIC_JS_DIR = self.STATIC_DIR / "js"
        self.STATIC_IMAGES_DIR = self.STATIC_DIR / "images"
        self.STATIC_FONTS_DIR = self.STATIC_DIR / "fonts"
        
        # === UPLOADS SPÉCIFIQUES ===
        self.UPLOADS_PROFILES_DIR = self.UPLOADS_DIR / "profiles"
        self.UPLOADS_FILES_DIR = self.UPLOADS_DIR / "files"
        self.UPLOADS_FILES_RAW_DIR = self.UPLOADS_FILES_DIR / "raw"
        self.UPLOADS_FILES_PROCESSED_DIR = self.UPLOADS_FILES_DIR / "processed"
        self.UPLOADS_FILES_ARCHIVE_DIR = self.UPLOADS_FILES_DIR / "archive"
        
        # === CONFIGURATION DES MONTAGES ===
        self.MOUNT_CONFIGS = {
            "static": {
                "path": "/static",
                "directory": str(self.STATIC_DIR),
                "name": "static"
            },
            "uploads": {
                "path": "/uploads",
                "directory": str(self.UPLOADS_DIR),
                "name": "uploads"
            },
            "media": {
                "path": "/media",
                "directory": str(self.MEDIA_DIR),
                "name": "media"
            },
        }
    
    def get_mount_path(self, mount_name: str) -> str:
        """Obtenir le chemin URL d'un montage"""
        if mount_name not in self.MOUNT_CONFIGS:
            raise ValueError(f"Montage '{mount_name}' non trouvé")
        return self.MOUNT_CONFIGS[mount_name]["path"]
    
    def get_mount_directory(self, mount_name: str) -> str:
        """Obtenir le répertoire physique d'un montage"""
        if mount_name not in self.MOUNT_CONFIGS:
            raise ValueError(f"Montage '{mount_name}' non trouvé")
        return self.MOUNT_CONFIGS[mount_name]["directory"]
    
    def get_file_url(self, mount_name: str, file_path: str) -> str:
        """
        Générer l'URL complète d'un fichier
        
        Example:
            path_config.get_file_url("static", "images/logo.png")
            → "/static/images/logo.png"
        """
        mount_path = self.get_mount_path(mount_name)
        clean_path = file_path.lstrip('/')
        return f"{mount_path}/{clean_path}"
    
    def get_physical_path(self, mount_name: str, file_path: str) -> Path:
        """
        Obtenir le chemin physique complet d'un fichier
        
        Example:
            path_config.get_physical_path("static", "images/logo.png")
            → Path("/path/to/project/app/static/images/logo.png")
        """
        mount_directory = self.get_mount_directory(mount_name)
        clean_path = file_path.lstrip('/')
        return Path(mount_directory) / clean_path
    
    def ensure_directory_exists(self, directory: Path) -> Path:
        """Créer un répertoire s'il n'existe pas"""
        directory.mkdir(parents=True, exist_ok=True)
        return directory

# Instance globale
path_config = PathConfig()

# Créer les répertoires au démarrage
path_config.ensure_directory_exists(path_config.UPLOADS_DIR)
path_config.ensure_directory_exists(path_config.MEDIA_DIR)
path_config.ensure_directory_exists(path_config.UPLOADS_PROFILES_DIR)
path_config.ensure_directory_exists(path_config.UPLOADS_FILES_DIR)
path_config.ensure_directory_exists(path_config.UPLOADS_FILES_RAW_DIR)
path_config.ensure_directory_exists(path_config.UPLOADS_FILES_PROCESSED_DIR)
path_config.ensure_directory_exists(path_config.UPLOADS_FILES_ARCHIVE_DIR)
