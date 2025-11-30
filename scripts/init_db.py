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
from app.models.personnel import Programme, Direction, Service, GradeComplet
from app.core.config import settings
from app.services.user_service import UserService
from app.services.system_settings_service import SystemSettingsService
from app.core.enums import UserType, GradeCategory
from app.core.logging_config import get_logger
from sqlmodel import SQLModel, Session, select

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

def check_schema_migrations():
    """Vérifie et applique automatiquement les migrations de schéma si nécessaire"""
    try:
        from scripts.migrate_schema import SchemaMigrator
        
        migrator = SchemaMigrator()
        
        # Récupérer les schémas pour vérifier s'il y a des différences
        logger.info("🔍 Vérification des migrations de schéma...")
        current_schema = migrator.get_current_schema()
        expected_schema = migrator.get_expected_schema()
        
        if not current_schema or not expected_schema:
            logger.error("❌ Impossible de récupérer les schémas")
            return False
        
        # Comparer les schémas pour détecter les différences
        differences = migrator.compare_schemas(current_schema, expected_schema)
        
        # Vérifier s'il y a des différences
        has_differences = any([
            differences.get('missing_tables', []),
            differences.get('missing_columns', {}),
            differences.get('extra_columns', {}),
            differences.get('modified_columns', {}),
            differences.get('type_changes', {})
        ])
        
        if not has_differences:
            logger.info("✅ Aucune migration nécessaire - Schéma à jour")
            return True
        
        # Afficher les différences détectées
        logger.info("📊 Différences détectées:")
        if differences.get('missing_tables'):
            logger.info(f"   📋 Tables manquantes: {differences['missing_tables']}")
        if differences.get('missing_columns'):
            logger.info("   📋 Colonnes manquantes:")
            for table, cols in differences['missing_columns'].items():
                logger.info(f"      {table}: {cols}")
        if differences.get('type_changes'):
            logger.info("   📋 Changements de type:")
            for table, changes in differences['type_changes'].items():
                for col, change in changes.items():
                    logger.info(f"      {table}.{col}: {change.get('current', '?')} → {change.get('expected', '?')}")
        
        # Appliquer automatiquement les migrations nécessaires
        logger.info("🔄 Application automatique des migrations...")
        success = migrator.apply_migrations(differences, dry_run=False)
        
        if success:
            logger.info("✅ Migrations appliquées avec succès")
            return True
        else:
            logger.error("❌ Erreur lors de l'application des migrations")
            return False
                
    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification des migrations: {e}")
        import traceback
        logger.debug(f"   Traceback: {traceback.format_exc()}")
        logger.warning("⚠️  Continuons sans migration automatique")
        return True  # Continue quand même pour ne pas bloquer le démarrage

def initialize_system_settings():
    """Initialise les paramètres système par défaut"""
    try:
        with Session(engine) as session:
            try:
                settings = SystemSettingsService.get_settings(session)
                logger.info(f"✅ Paramètres système initialisés/vérifiés")
                logger.info(f"   Entreprise: {settings.company_name}")
                return True
            except Exception as inner_error:
                # Si une erreur se produit, faire un rollback avant de relancer
                logger.warning(f"⚠️ Erreur lors de la récupération des paramètres: {inner_error}")
                try:
                    session.rollback()
                    logger.info("   🔄 Rollback effectué, nouvelle tentative...")
                    # Réessayer avec une nouvelle session propre
                    with Session(engine) as new_session:
                        settings = SystemSettingsService.get_settings(new_session)
                        logger.info(f"✅ Paramètres système initialisés/vérifiés (après rollback)")
                        logger.info(f"   Entreprise: {settings.company_name}")
                        return True
                except Exception as retry_error:
                    logger.error(f"❌ Erreur même après rollback: {retry_error}")
                    raise inner_error  # Re-lever l'erreur originale
    except Exception as e:
        logger.error(f"❌ Erreur initialisation paramètres système: {e}")
        import traceback
        logger.debug(f"   Traceback complet: {traceback.format_exc()}")
        return False

def initialize_personnel_data():
    """Initialise les données de référence du personnel (programmes, directions, services, grades)"""
    try:
        with Session(engine) as session:
            # Vérifier si les données existent déjà
            existing_programmes = session.exec(select(Programme)).first()
            if existing_programmes:
                logger.info("ℹ️  Données de référence du personnel déjà initialisées")
                return True
            
            logger.info("📋 Initialisation des données de référence du personnel...")
            
            # Programmes
            programmes_data = [
                {"code": "P01", "libelle": "Pilotage et Soutien Institutionnel", "description": "Programme de pilotage"},
                {"code": "P02", "libelle": "Gestion du Portefeuille de l'État", "description": "Gestion des participations"},
                {"code": "P03", "libelle": "Gestion du Patrimoine de l'État", "description": "Gestion du patrimoine"},
            ]
            for prog_data in programmes_data:
                prog = Programme(**prog_data)
                session.add(prog)
            session.commit()
            logger.info("✅ 3 Programmes créés")
            
            # Directions
            programmes = {p.code: p for p in session.exec(select(Programme)).all()}
            directions_data = [
                {"code": "DG", "libelle": "Direction Générale", "programme_id": programmes["P01"].id},
                {"code": "DAF", "libelle": "Direction Administrative et Financière", "programme_id": programmes["P01"].id},
                {"code": "DRH", "libelle": "Direction des Ressources Humaines", "programme_id": programmes["P01"].id},
                {"code": "DPE", "libelle": "Direction du Portefeuille de l'État", "programme_id": programmes["P02"].id},
                {"code": "DPAT", "libelle": "Direction du Patrimoine de l'État", "programme_id": programmes["P03"].id},
            ]
            for dir_data in directions_data:
                direction = Direction(**dir_data)
                session.add(direction)
            session.commit()
            logger.info("✅ 5 Directions créées")
            
            # Services
            directions = {d.code: d for d in session.exec(select(Direction)).all()}
            services_data = [
                {"code": "SCPT", "libelle": "Service Comptabilité", "direction_id": directions["DAF"].id},
                {"code": "SBUD", "libelle": "Service Budget", "direction_id": directions["DAF"].id},
                {"code": "SAPV", "libelle": "Service Approvisionnement", "direction_id": directions["DAF"].id},
                {"code": "SCAR", "libelle": "Service Carrière", "direction_id": directions["DRH"].id},
                {"code": "SPAY", "libelle": "Service Paie", "direction_id": directions["DRH"].id},
                {"code": "SFOR", "libelle": "Service Formation", "direction_id": directions["DRH"].id},
                {"code": "SPAR", "libelle": "Service Participations", "direction_id": directions["DPE"].id},
                {"code": "SETU", "libelle": "Service Études", "direction_id": directions["DPE"].id},
                {"code": "SGIM", "libelle": "Service Gestion Immobilière", "direction_id": directions["DPAT"].id},
                {"code": "SINV", "libelle": "Service Inventaire", "direction_id": directions["DPAT"].id},
            ]
            for serv_data in services_data:
                service = Service(**serv_data)
                session.add(service)
            session.commit()
            logger.info("✅ 10 Services créés")
            
            # Grades
            grades_data = [
                {"code": "A1", "libelle": "Administrateur Civil", "categorie": GradeCategory.A, "echelon_min": 1, "echelon_max": 7},
                {"code": "A2", "libelle": "Attaché d'Administration", "categorie": GradeCategory.A, "echelon_min": 1, "echelon_max": 6},
                {"code": "A3", "libelle": "Secrétaire d'Administration", "categorie": GradeCategory.A, "echelon_min": 1, "echelon_max": 5},
                {"code": "B1", "libelle": "Contrôleur des Services Administratifs", "categorie": GradeCategory.B, "echelon_min": 1, "echelon_max": 6},
                {"code": "B2", "libelle": "Contrôleur du Trésor", "categorie": GradeCategory.B, "echelon_min": 1, "echelon_max": 5},
                {"code": "B3", "libelle": "Secrétaire d'Administration", "categorie": GradeCategory.B, "echelon_min": 1, "echelon_max": 5},
                {"code": "C1", "libelle": "Commis des Services Administratifs", "categorie": GradeCategory.C, "echelon_min": 1, "echelon_max": 5},
                {"code": "C2", "libelle": "Agent Administratif", "categorie": GradeCategory.C, "echelon_min": 1, "echelon_max": 4},
                {"code": "C3", "libelle": "Aide Administratif", "categorie": GradeCategory.C, "echelon_min": 1, "echelon_max": 3},
                {"code": "D1", "libelle": "Agent de Bureau", "categorie": GradeCategory.D, "echelon_min": 1, "echelon_max": 4},
                {"code": "D2", "libelle": "Homme de Service", "categorie": GradeCategory.D, "echelon_min": 1, "echelon_max": 3},
            ]
            for grade_data in grades_data:
                grade = GradeComplet(**grade_data)
                session.add(grade)
            session.commit()
            logger.info("✅ 11 Grades créés")
            
            logger.info("🎉 Données de référence du personnel initialisées avec succès !")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erreur initialisation données personnel: {e}", exc_info=True)
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
    3. Initialise les données de référence du personnel
    4. Crée l'utilisateur admin si aucun utilisateur n'existe
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
    logger.info("✅ Base de données créée avec succès")
    # Étape 1: Créer les tables
    if not create_tables():
        logger.error("❌ Échec de l'initialisation des tables")
        return False
    logger.info("✅ Tables créées avec succès")
    
    # Étape 1.5: Vérifier et appliquer les migrations de schéma
    if not check_schema_migrations():
        logger.error("❌ Échec de la vérification des migrations")
        return False
    logger.info("✅ Migrations vérifiées avec succès")
    # Étape 2: Initialiser les paramètres système
    if not initialize_system_settings():
        logger.error("❌ Échec de l'initialisation des paramètres système")
        return False
    logger.info("✅ Paramètres système initialisés avec succès")
    # Étape 3: Initialiser les données de référence du personnel (DÉSACTIVÉ - géré par l'utilisateur)
    # if not initialize_personnel_data():
    #     logger.error("❌ Échec de l'initialisation des données de référence")
    #     return False
    logger.info("ℹ️  Initialisation des référentiels désactivée - À créer via l'interface")
    
    # Étape 4: Créer l'admin si besoin
    if not create_admin_user():
        logger.error("❌ Échec de la création de l'utilisateur admin")
        return False
    logger.info("✅ Utilisateur admin créé avec succès")
    
    # Étape 5: Les workflows sont à configurer via l'interface (pas d'initialisation auto)
    logger.info("ℹ️  Configuration des workflows désactivée - À créer via l'interface /admin/workflow-config")
    
    logger.info("✅ Initialisation terminée avec succès!")
    logger.info("="*60 + "\n")
    return True

if __name__ == "__main__":
    # Permet d'exécuter le script manuellement
    success = initialize_database()
    sys.exit(0 if success else 1)

