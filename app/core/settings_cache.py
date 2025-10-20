"""
Cache pour les paramètres système
Évite de charger depuis la DB à chaque requête
"""

from datetime import datetime

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SettingsCache:
    """Cache singleton pour les paramètres système"""

    _instance = None
    _settings: dict | None = None
    _last_update: datetime | None = None
    _cache_duration: int = 300  # 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self) -> dict | None:
        """Récupère les paramètres du cache"""
        if self._settings is None:
            return None

        # Vérifier si le cache est expiré
        if self._last_update is None:
            return None

        age = datetime.now() - self._last_update
        if age.total_seconds() > self._cache_duration:
            logger.debug("⏰ Cache des paramètres expiré")
            return None

        return self._settings

    def set(self, settings: dict):
        """Met à jour le cache"""
        self._settings = settings
        self._last_update = datetime.now()
        logger.debug("💾 Cache des paramètres mis à jour")

    def clear(self):
        """Vide le cache"""
        self._settings = None
        self._last_update = None
        logger.debug("🗑️  Cache des paramètres vidé")

    def is_valid(self) -> bool:
        """Vérifie si le cache est valide"""
        if self._settings is None or self._last_update is None:
            return False

        age = datetime.now() - self._last_update
        return age.total_seconds() <= self._cache_duration


# Instance globale
settings_cache = SettingsCache()

__all__ = ["settings_cache"]
