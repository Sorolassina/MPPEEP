"""
Script pour créer la table activity
"""
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine
from app.models.activity import Activity
from app.core.logging_config import get_logger
from sqlmodel import SQLModel

logger = get_logger(__name__)


def create_activity_table():
    """
    Crée la table activity si elle n'existe pas
    """
    try:
        logger.info("📦 Création de la table activity...")
        
        # Créer la table via SQLModel
        SQLModel.metadata.create_all(engine, tables=[Activity.__table__])
        
        logger.info("✅ Table activity créée/vérifiée avec succès")
        
        # Vérifier que la table existe
        with engine.connect() as conn:
            if "sqlite" in str(engine.url):
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='activity'"))
                if result.fetchone():
                    logger.info("✅ Vérification: Table activity existe")
                    return True
            elif "postgresql" in str(engine.url):
                result = conn.execute(text("SELECT tablename FROM pg_tables WHERE tablename='activity'"))
                if result.fetchone():
                    logger.info("✅ Vérification: Table activity existe")
                    return True
        
        return True
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la table activity: {e}")
        return False


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("🔄 Création de la table activity")
    logger.info("="*60)
    
    success = create_activity_table()
    
    if success:
        logger.info("="*60)
        logger.info("✅ Table activity créée avec succès!")
        logger.info("="*60 + "\n")
        sys.exit(0)
    else:
        logger.error("="*60)
        logger.error("❌ Échec de la création!")
        logger.error("="*60 + "\n")
        sys.exit(1)

