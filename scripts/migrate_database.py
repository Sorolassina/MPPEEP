"""
Script pour migrer les données d'une base à une autre
Exemple : SQLite → PostgreSQL
"""
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH pour pouvoir importer app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select, create_engine
from app.models.user import User
from app.core.config import settings

def migrate_data(source_url: str, target_url: str):
    """
    Migre les données d'une base source vers une base cible
    
    Args:
        source_url: URL de la base source (ex: sqlite:///./app.db)
        target_url: URL de la base cible (ex: postgresql://...)
    """
    print("=" * 60)
    print("🔄 MIGRATION DE BASE DE DONNÉES")
    print("=" * 60)
    print(f"📥 Source : {source_url}")
    print(f"📤 Cible  : {target_url}")
    print()
    
    if source_url == target_url:
        print("❌ Erreur : Les bases source et cible sont identiques !")
        return
    
    # Connexion aux bases
    print("🔌 Connexion aux bases de données...")
    source_engine = create_engine(source_url, echo=False)
    target_engine = create_engine(target_url, echo=False)
    
    # Créer les tables dans la cible
    print("📋 Création des tables dans la base cible...")
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(target_engine)
    
    # Migration des utilisateurs
    print("👥 Migration des utilisateurs...")
    with Session(source_engine) as source_session:
        with Session(target_engine) as target_session:
            # Récupérer tous les users de la source
            users = source_session.exec(select(User)).all()
            
            if not users:
                print("   ℹ️  Aucun utilisateur à migrer")
            else:
                migrated = 0
                for user in users:
                    # Vérifier si l'user existe déjà dans la cible
                    existing = target_session.exec(
                        select(User).where(User.email == user.email)
                    ).first()
                    
                    if existing:
                        print(f"   ⚠️  {user.email} existe déjà, ignoré")
                    else:
                        # Créer un nouvel utilisateur (sans l'ID pour éviter les conflits)
                        new_user = User(
                            email=user.email,
                            full_name=user.full_name,
                            hashed_password=user.hashed_password,
                            is_active=user.is_active,
                            is_superuser=user.is_superuser
                        )
                        target_session.add(new_user)
                        migrated += 1
                        print(f"   ✅ {user.email} migré")
                
                target_session.commit()
                print()
                print(f"✅ {migrated}/{len(users)} utilisateurs migrés avec succès !")
    
    print("=" * 60)
    print("🎉 Migration terminée !")
    print("=" * 60)

def main():
    """Point d'entrée principal"""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       🗄️  MIGRATION DE BASE DE DONNÉES                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    # Exemples
    print("📝 Exemples d'utilisation :")
    print()
    print("1. SQLite → PostgreSQL")
    print("   python scripts/migrate_database.py \\")
    print("       \"sqlite:///./app.db\" \\")
    print("       \"postgresql://user:pass@localhost:5432/mppeep\"")
    print()
    print("2. PostgreSQL → SQLite (backup)")
    print("   python scripts/migrate_database.py \\")
    print("       \"postgresql://user:pass@localhost:5432/mppeep\" \\")
    print("       \"sqlite:///./backup.db\"")
    print()
    
    if len(sys.argv) != 3:
        print("❌ Usage:")
        print(f"   python {sys.argv[0]} <source_url> <target_url>")
        print()
        print("💡 Base actuelle configurée :")
        print(f"   {settings.database_url}")
        sys.exit(1)
    
    source = sys.argv[1]
    target = sys.argv[2]
    
    # Confirmation
    print()
    print("⚠️  ATTENTION : Cette opération va :")
    print("   1. Créer les tables dans la base cible (si elles n'existent pas)")
    print("   2. Copier toutes les données de la source vers la cible")
    print("   3. Les données existantes dans la cible ne seront PAS écrasées")
    print()
    
    confirm = input("Continuer ? (oui/non) : ").lower().strip()
    
    if confirm not in ["oui", "yes", "y", "o"]:
        print("❌ Migration annulée")
        sys.exit(0)
    
    print()
    migrate_data(source, target)

if __name__ == "__main__":
    main()

