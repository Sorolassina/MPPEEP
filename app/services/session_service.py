"""
Service de gestion des sessions utilisateur
Gère la création, validation et suppression des sessions
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select
from fastapi import Request, Response

from app.models.session import UserSession
from app.models.user import User
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Nom du cookie de session
SESSION_COOKIE_NAME = "mppeep_session"


class SessionService:
    """Service de gestion des sessions utilisateur"""
    
    @staticmethod
    def create_session(
        db_session: Session,
        user: User,
        request: Request,
        remember_me: bool = False
    ) -> UserSession:
        """
        Crée une nouvelle session pour l'utilisateur
        
        Args:
            db_session: Session de base de données
            user: Utilisateur pour lequel créer la session
            request: Requête FastAPI (pour récupérer IP et User-Agent)
            remember_me: Si True, session de 30 jours, sinon 7 jours
        
        Returns:
            UserSession créée
        """
        # Générer le token
        session_token = UserSession.generate_token()
        
        # Récupérer les informations du client
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Extraire le device_info du user_agent
        device_info = SessionService._extract_device_info(user_agent)
        
        # Durée de la session
        days = 30 if remember_me else 7
        
        # Créer la session
        user_session = UserSession(
            session_token=session_token,
            user_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=datetime.now() + timedelta(days=days),
            is_active=True
        )
        
        db_session.add(user_session)
        db_session.commit()
        db_session.refresh(user_session)
        
        logger.info(
            f"✅ Session créée pour l'utilisateur {user.email} "
            f"(ID: {user.id}, Device: {device_info}, IP: {client_ip})"
        )
        
        return user_session
    
    @staticmethod
    def get_session_by_token(
        db_session: Session,
        session_token: str
    ) -> Optional[UserSession]:
        """
        Récupère une session par son token
        
        Args:
            db_session: Session de base de données
            session_token: Token de session
        
        Returns:
            UserSession si trouvée et valide, None sinon
        """
        statement = select(UserSession).where(
            UserSession.session_token == session_token,
            UserSession.is_active == True
        )
        session = db_session.exec(statement).first()
        
        if not session:
            return None
        
        # Vérifier si la session est expirée
        if session.is_expired():
            logger.info(f"⚠️  Session expirée : {session_token[:10]}...")
            session.deactivate()
            db_session.commit()
            return None
        
        return session
    
    @staticmethod
    def get_user_from_session(
        db_session: Session,
        session_token: str
    ) -> Optional[User]:
        """
        Récupère l'utilisateur associé à une session
        
        Args:
            db_session: Session de base de données
            session_token: Token de session
        
        Returns:
            User si session valide, None sinon
        """
        user_session = SessionService.get_session_by_token(db_session, session_token)
        
        if not user_session:
            return None
        
        # Récupérer l'utilisateur
        statement = select(User).where(User.id == user_session.user_id)
        user = db_session.exec(statement).first()
        
        if not user or not user.is_active:
            return None
        
        # Rafraîchir la session (update last_activity)
        user_session.refresh()
        db_session.commit()
        
        return user
    
    @staticmethod
    def delete_session(
        db_session: Session,
        session_token: str
    ) -> bool:
        """
        Supprime (désactive) une session
        
        Args:
            db_session: Session de base de données
            session_token: Token de session à supprimer
        
        Returns:
            True si supprimée, False sinon
        """
        user_session = SessionService.get_session_by_token(db_session, session_token)
        
        if not user_session:
            return False
        
        user_session.deactivate()
        db_session.commit()
        
        logger.info(f"✅ Session déconnectée : {session_token[:10]}...")
        
        return True
    
    @staticmethod
    def delete_all_user_sessions(
        db_session: Session,
        user_id: int
    ) -> int:
        """
        Supprime toutes les sessions d'un utilisateur
        
        Args:
            db_session: Session de base de données
            user_id: ID de l'utilisateur
        
        Returns:
            Nombre de sessions supprimées
        """
        statement = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        )
        sessions = db_session.exec(statement).all()
        
        count = 0
        for session in sessions:
            session.deactivate()
            count += 1
        
        db_session.commit()
        
        logger.info(f"✅ {count} session(s) déconnectée(s) pour l'utilisateur ID {user_id}")
        
        return count
    
    @staticmethod
    def get_active_sessions(
        db_session: Session,
        user_id: int
    ) -> list[UserSession]:
        """
        Récupère toutes les sessions actives d'un utilisateur
        
        Args:
            db_session: Session de base de données
            user_id: ID de l'utilisateur
        
        Returns:
            Liste des sessions actives
        """
        statement = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now()
        ).order_by(UserSession.last_activity.desc())
        
        return list(db_session.exec(statement).all())
    
    @staticmethod
    def cleanup_expired_sessions(db_session: Session) -> int:
        """
        Nettoie les sessions expirées
        
        Args:
            db_session: Session de base de données
        
        Returns:
            Nombre de sessions nettoyées
        """
        statement = select(UserSession).where(
            UserSession.is_active == True,
            UserSession.expires_at < datetime.now()
        )
        sessions = db_session.exec(statement).all()
        
        count = 0
        for session in sessions:
            session.deactivate()
            count += 1
        
        db_session.commit()
        
        if count > 0:
            logger.info(f"🧹 {count} session(s) expirée(s) nettoyée(s)")
        
        return count
    
    @staticmethod
    def _extract_device_info(user_agent: str) -> str:
        """
        Extrait une description simple du device depuis le user-agent
        
        Args:
            user_agent: User-Agent string
        
        Returns:
            Description du device (ex: "Chrome on Windows")
        """
        ua = user_agent.lower()
        
        # Déterminer le navigateur
        if "edg" in ua:
            browser = "Edge"
        elif "chrome" in ua:
            browser = "Chrome"
        elif "firefox" in ua:
            browser = "Firefox"
        elif "safari" in ua and "chrome" not in ua:
            browser = "Safari"
        else:
            browser = "Unknown"
        
        # Déterminer l'OS
        if "windows" in ua:
            os = "Windows"
        elif "mac" in ua:
            os = "macOS"
        elif "linux" in ua:
            os = "Linux"
        elif "android" in ua:
            os = "Android"
        elif "iphone" in ua or "ipad" in ua:
            os = "iOS"
        else:
            os = "Unknown"
        
        return f"{browser} on {os}"
    
    @staticmethod
    def set_session_cookie(
        response: Response,
        session_token: str,
        max_age: int = 7 * 24 * 60 * 60  # 7 jours par défaut
    ):
        """
        Définit le cookie de session dans la réponse
        
        Args:
            response: Réponse FastAPI
            session_token: Token de session
            max_age: Durée de vie du cookie en secondes
        """
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            max_age=max_age,
            httponly=True,  # Protection XSS
            secure=False,   # TODO: Mettre à True en production (HTTPS)
            samesite="lax"  # Protection CSRF
        )
    
    @staticmethod
    def delete_session_cookie(response: Response):
        """
        Supprime le cookie de session
        
        Args:
            response: Réponse FastAPI
        """
        response.delete_cookie(key=SESSION_COOKIE_NAME)


__all__ = ["SessionService", "SESSION_COOKIE_NAME"]

