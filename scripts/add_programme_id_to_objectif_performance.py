"""
Script pour ajouter le champ programme_id à la table objectif_performance
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)

def add_programme_id_to_objectif_performance():
    """Ajoute la colonne programme_id à objectif_performance"""
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                logger.info("🔄 Ajout de programme_id à objectif_performance...")
                
                # Vérifier l'état actuel
                check_query = text("""
                    SELECT 
                        column_name, 
                        is_nullable,
                        data_type
                    FROM information_schema.columns 
                    WHERE table_name = 'objectif_performance' 
                    AND column_name = 'programme_id'
                """)
                
                result = conn.execute(check_query).fetchone()
                
                if result:
                    logger.info(f"✅ La colonne programme_id existe déjà dans objectif_performance")
                    logger.info(f"   - Nullable: {result[1]}")
                    logger.info(f"   - Type: {result[2]}")
                    trans.commit()
                    return
                
                # Lire le script SQL
                script_path = Path(__file__).parent / "add_programme_id_to_objectif_performance.sql"
                with open(script_path, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                
                # Exécuter le script
                conn.execute(text(sql_script))
                trans.commit()
                
                logger.info("✅ Colonne programme_id ajoutée avec succès à objectif_performance")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Erreur lors de l'ajout de programme_id: {e}")
                raise
                
    except Exception as e:
        logger.error(f"❌ Erreur lors de la connexion à la base de données: {e}")
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ajouter programme_id à objectif_performance")
    parser.add_argument("--yes", action="store_true", help="Exécuter sans confirmation")
    args = parser.parse_args()
    
    if not args.yes:
        response = input("⚠️  Êtes-vous sûr de vouloir ajouter programme_id à objectif_performance ? (oui/non): ")
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            print("❌ Opération annulée")
            sys.exit(0)
    
    try:
        add_programme_id_to_objectif_performance()
        print("✅ Migration réussie")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

