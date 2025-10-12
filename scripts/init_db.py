"""
Script d'initialisation de la base de données et de l'utilisateur admin
Exécuté automatiquement au démarrage de l'application
"""
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine, init_db
from app.models.user import User
from app.models.system_settings import SystemSettings
from app.models.activity import Activity
from app.models.file import File  # Import du modèle File pour créer la table
from app.core.config import settings
from app.services.user_service import UserService
from app.services.system_settings_service import SystemSettingsService
from app.core.enums import UserType
from app.core.logging_config import get_logger
from sqlmodel import SQLModel, Session

# Logger pour ce script
logger = get_logger(__name__)

def create_database_if_not_exists():
    """
    Crée la base de données PostgreSQL si elle n'existe pas
    (Pour SQLite, le fichier est créé automatiquement)
    """
    # Si c'est SQLite, rien à faire
    if "sqlite" in settings.database_url.lower():
        logger.info("📁 SQLite: Le fichier sera créé automatiquement")
        return True
    
    # Pour PostgreSQL, vérifier et créer la base si nécessaire
    if "postgresql" in settings.database_url.lower():
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.exc import OperationalError, ProgrammingError
            
            # Construire l'URL de connexion au serveur (sans le nom de la DB)
            db_parts = settings.database_url.rsplit('/', 1)
            server_url = db_parts[0] + '/postgres'  # Connexion à la base par défaut
            db_name = settings.POSTGRES_DB
            
            # Tester la connexion au serveur PostgreSQL
            try:
                test_engine = create_engine(server_url)
                with test_engine.connect() as conn:
                    # Vérifier si la base existe
                    result = conn.execute(
                        text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
                    )
                    exists = result.fetchone() is not None
                    
                    if exists:
                        logger.info(f"✅ Base de données PostgreSQL '{db_name}' existe déjà")
                    else:
                        logger.info(f"📦 Création de la base de données PostgreSQL '{db_name}'...")
                        # Fermer la transaction actuelle
                        conn.execute(text("COMMIT"))
                        # Créer la base
                        conn.execute(text(f"CREATE DATABASE {db_name}"))
                        logger.info(f"✅ Base de données '{db_name}' créée avec succès")
                
                test_engine.dispose()
                return True
                
            except OperationalError as e:
                logger.error(f"❌ Impossible de se connecter au serveur PostgreSQL: {e}")
                logger.error(f"   Vérifiez que PostgreSQL est démarré et accessible")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️  Erreur lors de la vérification de la base PostgreSQL: {e}")
            logger.warning(f"   La base '{settings.POSTGRES_DB}' doit exister manuellement")
            return True  # Continue quand même
    
    return True

def create_tables():
    """Crée toutes les tables de la base de données"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("✅ Tables de la base de données créées/vérifiées")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des tables: {e}", exc_info=True)
        return False

def initialize_system_settings():
    """Initialise les paramètres système par défaut"""
    try:
        with Session(engine) as session:
            settings = SystemSettingsService.get_settings(session)
            logger.info(f"✅ Paramètres système initialisés/vérifiés")
            logger.info(f"   Entreprise: {settings.company_name}")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur initialisation paramètres système: {e}")
        return False

def create_admin_user():
    """Crée l'utilisateur admin par défaut SI aucun admin n'existe"""
    try:
        with Session(engine) as session:
            # Vérifier si un ADMIN existe déjà (nouvelle logique)
            admin_count = UserService.get_admin_count(session)
            
            if admin_count > 0:
                logger.info(f"ℹ️  {admin_count} administrateur(s) trouvé(s) - Pas de création nécessaire")
                return True
            
            # Vérifier le total d'utilisateurs (pour info)
            user_count = UserService.count_users(session)
            if user_count > 0:
                logger.info(f"ℹ️  {user_count} utilisateur(s) trouvé(s) mais aucun admin")
                logger.info(f"📦 Création de l'admin par défaut...")
            
            # Aucun admin n'existe, créer l'admin par défaut
            admin_email = "admin@mppeep.com"
            admin_password = "admin123"
            
            # Utiliser le service pour créer l'admin avec type_user=ADMIN
            admin = UserService.create_user(
                session=session,
                email=admin_email,
                full_name="Administrateur MPPEEP",
                password=admin_password,
                is_active=True,
                is_superuser=True,
                type_user=UserType.ADMIN  # Type admin explicite
            )
            
            if admin:
                logger.info("\n" + "="*50)
                logger.info("✅ ADMINISTRATEUR CRÉÉ")
                logger.info("="*50)
                logger.info(f"📧 Email      : {admin_email}")
                logger.info(f"🔑 Password   : {admin_password}")
                logger.info(f"🆔 ID         : {admin.id}")
                logger.info(f"👑 Type       : {admin.type_user}")
                logger.info(f"✓  Superuser  : {admin.is_superuser}")
                logger.info("="*50)
                logger.warning("⚠️  IMPORTANT: Changez ce mot de passe en production!")
                logger.info("="*50 + "\n")
                return True
            else:
                logger.error("❌ Impossible de créer l'admin")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de l'admin: {e}", exc_info=True)
        return False

def initialize_database():
    """
    Initialise la base de données complète :
    0. Crée la base de données PostgreSQL si nécessaire
    1. Crée les tables si elles n'existent pas
    2. Initialise les paramètres système
    3. Crée l'utilisateur admin si aucun utilisateur n'existe
    """
    logger.info("\n" + "="*60)
    logger.info("🚀 Initialisation de la base de données...")
    logger.info("="*60)
    logger.info(f"📂 Type: {'SQLite' if 'sqlite' in settings.database_url else 'PostgreSQL'}")
    logger.info(f"📂 URL: {settings.database_url}")
    logger.info("-" * 60)
    
    # Étape 0: Créer la base PostgreSQL si nécessaire
    if not create_database_if_not_exists():
        logger.error("❌ Échec de la création/vérification de la base de données")
        return False
    
    # Étape 1: Créer les tables
    if not create_tables():
        logger.error("❌ Échec de l'initialisation des tables")
        return False
    
    # Étape 2: Initialiser les paramètres système
    if not initialize_system_settings():
        logger.error("❌ Échec de l'initialisation des paramètres système")
        return False
    
    # Étape 3: Créer l'admin si besoin
    if not create_admin_user():
        logger.error("❌ Échec de la création de l'utilisateur admin")
        return False
    
    logger.info("✅ Initialisation terminée avec succès!")
    logger.info("="*60 + "\n")
    return True

if __name__ == "__main__":
    # Permet d'exécuter le script manuellement
    success = initialize_database()
    sys.exit(0 if success else 1)

