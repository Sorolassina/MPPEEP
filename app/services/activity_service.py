"""
Service pour la gestion des activités du système
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.core.logging_config import get_logger
from app.models.activity import Activity

logger = get_logger(__name__)


class ActivityService:
    """Service de gestion des activités"""

    # Mapping des types d'actions vers icônes
    ACTION_ICONS = {
        "create": "➕",
        "update": "✏️",
        "delete": "🗑️",
        "login": "🔐",
        "logout": "🚪",
        "upload": "📤",
        "download": "📥",
        "view": "👁️",
        "settings": "⚙️",
    }

    @staticmethod
    def log_user_activity(
        session: Session,
        user: "User",
        action_type: str,
        target_type: str,
        description: str,
        target_id: int | None = None,
        icon: str | None = None,
    ) -> Optional["Activity"]:
        """
        Enregistre une activité utilisateur (interface simplifiée)

        Args:
            session: Session de base de données
            user: Objet User (from get_current_user)
            action_type: Type d'action (create, update, delete, etc.)
            target_type: Type de cible (fiche_technique, demande_rh, agent, etc.)
            description: Description de l'action
            target_id: ID de la cible (optionnel)
            icon: Icône emoji (optionnel, auto-détecté si None)

        Returns:
            L'activité créée ou None en cas d'erreur
        """
        try:
            # Auto-détection de l'icône si non fournie
            if icon is None:
                icon = ActivityService.ACTION_ICONS.get(action_type, "📝")

            activity = Activity(
                user_id=user.id,
                user_email=user.email,
                user_full_name=user.full_name,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                description=description,
                icon=icon,
            )

            session.add(activity)
            session.commit()
            session.refresh(activity)

            logger.debug(f"📊 Activité loguée: {action_type} on {target_type} by {user.email}")

            return activity

        except Exception as e:
            logger.error(f"❌ Erreur lors du log d'activité: {e}")
            session.rollback()
            # Ne pas lever l'exception pour ne pas impacter l'opération principale
            return None

    @staticmethod
    def log_activity(
        db_session: Session,
        user_id: int | None,
        user_email: str,
        action_type: str,
        target_type: str,
        description: str,
        target_id: int | None = None,
        icon: str | None = None,
        user_full_name: str | None = None,
    ) -> Optional["Activity"]:
        """
        Enregistre une nouvelle activité

        Args:
            db_session: Session de base de données
            user_id: ID de l'utilisateur
            user_email: Email de l'utilisateur
            action_type: Type d'action (create, update, delete, etc.)
            target_type: Type de cible (user, settings, etc.)
            description: Description de l'action
            target_id: ID de la cible (optionnel)
            icon: Icône emoji (optionnel, auto-détecté si None)

        Returns:
            L'activité créée
        """
        try:
            # Auto-détection de l'icône si non fournie
            if icon is None:
                icon = ActivityService.ACTION_ICONS.get(action_type, "📝")

            activity = Activity(
                user_id=user_id,
                user_email=user_email,
                user_full_name=user_full_name,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                description=description,
                icon=icon,
            )

            db_session.add(activity)
            db_session.commit()
            db_session.refresh(activity)

            logger.debug(f"📊 Activité loguée: {action_type} on {target_type} by {user_email}")

            return activity

        except Exception as e:
            logger.error(f"❌ Erreur lors du log d'activité: {e}")
            db_session.rollback()
            # Ne pas lever l'exception pour ne pas impacter l'opération principale
            return None

    @staticmethod
    def get_recent_activities(db_session: Session, limit: int = 10, days: int = 7) -> list[dict]:
        """
        Récupère les activités récentes

        Args:
            db_session: Session de base de données
            limit: Nombre maximum d'activités à retourner
            days: Nombre de jours dans le passé à considérer

        Returns:
            Liste des activités sous forme de dictionnaires
        """
        try:
            # Date limite
            cutoff_date = datetime.now() - timedelta(days=days)

            # Requête avec filtrage et tri
            statement = (
                select(Activity)
                .where(Activity.created_at >= cutoff_date)
                .order_by(Activity.created_at.desc())
                .limit(limit)
            )

            activities = db_session.exec(statement).all()

            # Convertir en dictionnaires avec toutes les informations
            result = [
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "user_email": a.user_email,
                    "user_full_name": a.user_full_name,
                    "action_type": a.action_type,
                    "target_type": a.target_type,
                    "target_id": a.target_id,
                    "description": a.description,
                    "icon": a.icon,
                    "time": a.created_at,
                    "title": a.description,  # Pour compatibilité avec les anciens templates
                }
                for a in activities
            ]

            return result

        except Exception as e:
            logger.error(f"❌ Erreur récupération activités: {e}")
            return []

    @staticmethod
    def cleanup_old_activities(db_session: Session, days: int = 30) -> int:
        """
        Supprime les activités de plus de X jours

        Args:
            db_session: Session de base de données
            days: Nombre de jours à conserver

        Returns:
            Nombre d'activités supprimées
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            statement = select(Activity).where(Activity.created_at < cutoff_date)
            old_activities = db_session.exec(statement).all()

            count = len(old_activities)

            for activity in old_activities:
                db_session.delete(activity)

            db_session.commit()

            logger.info(f"🧹 {count} activités anciennes supprimées")

            return count

        except Exception as e:
            logger.error(f"❌ Erreur nettoyage activités: {e}")
            db_session.rollback()
            return 0

    @staticmethod
    def get_user_activities(db_session: Session, user_id: int, limit: int = 20) -> list[dict]:
        """
        Récupère les activités d'un utilisateur spécifique

        Args:
            db_session: Session de base de données
            user_id: ID de l'utilisateur
            limit: Nombre maximum d'activités

        Returns:
            Liste des activités de l'utilisateur
        """
        try:
            statement = (
                select(Activity).where(Activity.user_id == user_id).order_by(Activity.created_at.desc()).limit(limit)
            )

            activities = db_session.exec(statement).all()

            return [
                {
                    "description": a.description,
                    "icon": a.icon,
                    "time": a.created_at,
                }
                for a in activities
            ]

        except Exception as e:
            logger.error(f"❌ Erreur récupération activités utilisateur: {e}")
            return []


__all__ = ["ActivityService"]
