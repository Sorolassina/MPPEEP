"""
Migration pour créer la table rapport_performance
"""
import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import SQLModel, create_engine
from app.core.config import settings
from app.models.performance import RapportPerformance
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def run_migration():
    """Crée la table rapport_performance"""
    try:
        # Créer l'engine
        if settings.DATABASE_URL:
            engine = create_engine(str(settings.DATABASE_URL), echo=True)
        else:
            # Fallback sur SQLite
            db_path = project_root / "app.db"
            engine = create_engine(f"sqlite:///{db_path}", echo=True)
        
        logger.info("🔧 Création de la table rapport_performance...")
        
        # Créer la table
        SQLModel.metadata.create_all(engine, tables=[RapportPerformance.__table__])
        
        logger.info("✅ Table rapport_performance créée avec succès !")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise


if __name__ == "__main__":
    run_migration()

