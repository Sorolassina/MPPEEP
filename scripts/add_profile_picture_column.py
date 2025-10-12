"""
Script de migration pour ajouter la colonne profile_picture à la table user
"""
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def add_profile_picture_column():
    """
    Ajoute la colonne profile_picture à la table user si elle n'existe pas
    """
    try:
        with engine.connect() as conn:
            # Vérifier si la colonne existe déjà
            if "sqlite" in str(engine.url):
                # Pour SQLite
                result = conn.execute(text("PRAGMA table_info(user)"))
                columns = [row[1] for row in result]
                
                if 'profile_picture' in columns:
                    logger.info("✅ La colonne profile_picture existe déjà")
                    return True
                
                # Ajouter la colonne
                logger.info("📦 Ajout de la colonne profile_picture...")
                conn.execute(text("ALTER TABLE user ADD COLUMN profile_picture VARCHAR(500)"))
                conn.commit()
                logger.info("✅ Colonne profile_picture ajoutée avec succès")
                
            elif "postgresql" in str(engine.url):
                # Pour PostgreSQL
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='user'
                """))
                columns = [row[0] for row in result]
                
                if 'profile_picture' in columns:
                    logger.info("✅ La colonne profile_picture existe déjà")
                    return True
                
                # Ajouter la colonne
                logger.info("📦 Ajout de la colonne profile_picture...")
                conn.execute(text("ALTER TABLE user ADD COLUMN profile_picture VARCHAR(500)"))
                conn.commit()
                logger.info("✅ Colonne profile_picture ajoutée avec succès")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        return False


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("🔄 Migration: Ajout colonne profile_picture")
    logger.info("="*60)
    
    success = add_profile_picture_column()
    
    if success:
        logger.info("="*60)
        logger.info("✅ Migration terminée avec succès!")
        logger.info("="*60 + "\n")
        sys.exit(0)
    else:
        logger.error("="*60)
        logger.error("❌ Migration échouée!")
        logger.error("="*60 + "\n")
        sys.exit(1)

