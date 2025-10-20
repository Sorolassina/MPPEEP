"""
Service de gestion des utilisateurs
Contient toute la logique métier liée aux utilisateurs
"""

from sqlmodel import Session, select

from app.core.enums import UserType
from app.core.security import get_password_hash, verify_password
from app.models.user import User


class UserService:
    """Service pour gérer les utilisateurs"""

    @staticmethod
    def get_by_email(session: Session, email: str) -> User | None:
        """
        Récupère un utilisateur par son email

        Args:
            session: Session de base de données
            email: Email de l'utilisateur

        Returns:
            User si trouvé, None sinon
        """
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()

    @staticmethod
    def get_by_id(session: Session, user_id: int) -> User | None:
        """
        Récupère un utilisateur par son ID

        Args:
            session: Session de base de données
            user_id: ID de l'utilisateur

        Returns:
            User si trouvé, None sinon
        """
        return session.get(User, user_id)

    @staticmethod
    def create_user(
        session: Session,
        email: str,
        full_name: str,
        password: str,
        is_active: bool = True,
        is_superuser: bool = False,
        type_user: str = UserType.USER,
    ) -> User | None:
        """
        Crée un nouvel utilisateur

        Args:
            session: Session de base de données
            email: Email de l'utilisateur (unique)
            full_name: Nom complet
            password: Mot de passe en clair (sera hashé)
            is_active: Si l'utilisateur est actif (défaut: True)
            is_superuser: Si l'utilisateur est admin (défaut: False, rétrocompatibilité)
            type_user: Type d'utilisateur (admin, user, moderator, guest)

        Returns:
            User créé, ou None si l'email existe déjà
        """
        # Vérifier si l'utilisateur existe déjà
        existing_user = UserService.get_by_email(session, email)
        if existing_user:
            return None

        # Si is_superuser=True, forcer type_user à ADMIN
        if is_superuser and type_user == UserType.USER:
            type_user = UserType.ADMIN

        # Créer le nouvel utilisateur
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=is_active,
            is_superuser=is_superuser,
            type_user=type_user,
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        return user

    @staticmethod
    def authenticate(session: Session, email: str, password: str) -> User | None:
        """
        Authentifie un utilisateur

        Args:
            session: Session de base de données
            email: Email
            password: Mot de passe en clair

        Returns:
            User si authentification réussie, None sinon
        """
        user = UserService.get_by_email(session, email)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    def update_password(session: Session, user: User, new_password: str) -> bool:
        """
        Met à jour le mot de passe d'un utilisateur

        Args:
            session: Session de base de données
            user: Utilisateur à modifier
            new_password: Nouveau mot de passe en clair

        Returns:
            True si succès
        """
        try:
            user.hashed_password = get_password_hash(new_password)
            session.add(user)
            session.commit()
            session.refresh(user)
            return True
        except Exception:
            session.rollback()
            return False

    @staticmethod
    def count_users(session: Session) -> int:
        """
        Compte le nombre total d'utilisateurs

        Args:
            session: Session de base de données

        Returns:
            Nombre d'utilisateurs
        """
        statement = select(User)
        users = session.exec(statement).all()
        return len(users)

    @staticmethod
    def list_all(session: Session) -> list[User]:
        """
        Liste tous les utilisateurs

        Args:
            session: Session de base de données

        Returns:
            Liste des utilisateurs
        """
        statement = select(User)
        return session.exec(statement).all()

    @staticmethod
    def get_admin_count(session: Session) -> int:
        """
        Compte le nombre d'administrateurs dans la base

        Args:
            session: Session de base de données

        Returns:
            Nombre d'administrateurs
        """
        statement = select(User).where(User.type_user == UserType.ADMIN)
        admins = session.exec(statement).all()
        return len(admins)

    @staticmethod
    def has_admin(session: Session) -> bool:
        """
        Vérifie si au moins un administrateur existe

        Args:
            session: Session de base de données

        Returns:
            True si au moins un admin existe, False sinon
        """
        return UserService.get_admin_count(session) > 0
