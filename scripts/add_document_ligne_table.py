#!/usr/bin/env python3
"""
Script pour ajouter la table documents_lignes_budgetaires
à la base de données existante
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlmodel import SQLModel, create_engine
from app.core.config import settings
from app.models.budget import DocumentLigneBudgetaire
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def create_document_ligne_table():
    """Créer la table documents_lignes_budgetaires"""
    try:
        # Créer l'engine
        engine = create_engine(str(settings.DATABASE_URL), echo=True)
        
        logger.info("🗄️  Création de la table documents_lignes_budgetaires...")
        
        # Créer uniquement la nouvelle table
        DocumentLigneBudgetaire.metadata.create_all(engine)
        
        logger.info("✅ Table documents_lignes_budgetaires créée avec succès !")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la table : {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("CRÉATION DE LA TABLE DOCUMENTS_LIGNES_BUDGETAIRES")
    print("=" * 60)
    
    create_document_ligne_table()
    
    print("\n✅ Script terminé avec succès !")

