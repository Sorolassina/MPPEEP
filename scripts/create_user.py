"""
Script CLI pour créer un utilisateur (admin ou normal)
Utilisation: python scripts/create_user.py [email] [nom] [mot_de_passe] [--superuser]
"""
import sys
from pathlib import Path
import argparse

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine, Session
from app.services.user_service import UserService
from app.core.enums import UserType
from sqlmodel import SQLModel

def create_user_cli(
    email: str, 
    full_name: str, 
    password: str, 
    is_superuser: bool = False,
    type_user: str = UserType.AGENT
):
    """
    Interface CLI pour créer un utilisateur
    Utilise le UserService pour la logique métier
    
    Args:
        email: Email de l'utilisateur
        full_name: Nom complet
        password: Mot de passe en clair
        is_superuser: Si True, l'utilisateur sera admin (rétrocompatibilité)
        type_user: Type d'utilisateur (admin, user, moderator, guest)
    """
    
    # Créer les tables si elles n'existent pas
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Utiliser le service pour créer l'utilisateur
        user = UserService.create_user(
            session=session,
            email=email,
            full_name=full_name,
            password=password,
            is_active=True,
            is_superuser=is_superuser,
            type_user=type_user
        )
        
        if user:
            # Succès - Afficher les informations
            print("\n" + "="*50)
            print("✅ UTILISATEUR CRÉÉ")
            print("="*50)
            print(f"📧 Email      : {user.email}")
            print(f"👤 Nom        : {user.full_name}")
            print(f"🔑 Password   : {password}")
            print(f"🆔 ID         : {user.id}")
            print(f"👔 Type       : {user.type_user}")
            print(f"👑 Superuser  : {'Oui' if user.is_superuser else 'Non'}")
            print(f"✓  Actif      : {'Oui' if user.is_active else 'Non'}")
            print("="*50 + "\n")
            return user
        else:
            # L'utilisateur existe déjà
            existing = UserService.get_by_email(session, email)
            print(f"\n⚠️  L'utilisateur {email} existe déjà")
            print(f"   ID: {existing.id}")
            print(f"   Nom: {existing.full_name}")
            print(f"   Actif: {existing.is_active}")
            print(f"   Admin: {existing.is_superuser}\n")
            return None

def main():
    """Point d'entrée du script avec arguments en ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Créer un utilisateur dans la base de données"
    )
    parser.add_argument(
        "email",
        nargs="?",
        default="admin@mppeep.com",
        help="Email de l'utilisateur (défaut: admin@mppeep.com)"
    )
    parser.add_argument(
        "full_name",
        nargs="?",
        default="Admin MPPEEP",
        help="Nom complet (défaut: Admin MPPEEP)"
    )
    parser.add_argument(
        "password",
        nargs="?",
        default="admin123",
        help="Mot de passe (défaut: admin123)"
    )
    parser.add_argument(
        "--superuser",
        action="store_true",
        help="Créer un super utilisateur (admin) - rétrocompatibilité"
    )
    parser.add_argument(
        "--type",
        choices=["admin", "user", "moderator", "guest"],
        default="user",
        help="Type d'utilisateur (défaut: user)"
    )
    
    args = parser.parse_args()
    
    # Si aucun argument, créer l'admin par défaut
    is_default = (
        args.email == "admin@mppeep.com" and 
        args.full_name == "Admin MPPEEP"
    )
    
    # Déterminer le type d'utilisateur
    if args.superuser or is_default:
        user_type = UserType.ADMIN
    else:
        user_type = getattr(UserType, args.type.upper(), UserType.AGENT)
    
    create_user_cli(
        email=args.email,
        full_name=args.full_name,
        password=args.password,
        is_superuser=args.superuser or is_default,
        type_user=user_type
    )

if __name__ == "__main__":
    main()

