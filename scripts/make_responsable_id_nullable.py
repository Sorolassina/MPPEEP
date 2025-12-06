"""
Script pour rendre responsable_id nullable dans objectif_performance
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)

def make_responsable_id_nullable():
    """Rend la colonne responsable_id nullable"""
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                logger.info("🔄 Modification de responsable_id pour permettre NULL")
                
                # Vérifier l'état actuel
                check_query = text("""
                    SELECT 
                        column_name, 
                        is_nullable,
                        data_type
                    FROM information_schema.columns 
                    WHERE table_name = 'objectif_performance' 
                    AND column_name = 'responsable_id'
                """)
                
                result = conn.execute(check_query).fetchone()
                
                if not result:
                    logger.warning("⚠️ Colonne responsable_id non trouvée")
                    trans.rollback()
                    return False
                
                column_name, is_nullable, data_type = result
                logger.info(f"📊 État actuel: {column_name}, nullable: {is_nullable}, type: {data_type}")
                
                if is_nullable == 'YES':
                    logger.info("✅ La colonne est déjà nullable. Aucune modification nécessaire.")
                    trans.rollback()
                    return True
                
                # Modifier la colonne pour permettre NULL
                logger.info("📝 Modification de la colonne pour permettre NULL")
                conn.execute(text("""
                    ALTER TABLE objectif_performance 
                    ALTER COLUMN responsable_id DROP NOT NULL
                """))
                
                # Vérification
                result = conn.execute(check_query).fetchone()
                if result and result[1] == 'YES':
                    logger.info("✅ Modification réussie! responsable_id est maintenant nullable")
                
                trans.commit()
                logger.info("✅ Migration terminée avec succès!")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Erreur lors de la migration: {e}")
                import traceback
                traceback.print_exc()
                raise
                
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rendre responsable_id nullable")
    parser.add_argument('--yes', '-y', action='store_true', help='Exécuter sans confirmation')
    args = parser.parse_args()
    
    logger.info("🚀 Démarrage de la migration: rendre responsable_id nullable")
    
    if not args.yes:
        response = input("⚠️ Cette migration va modifier la structure de la base de données. Continuer? (oui/non): ")
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            logger.info("❌ Migration annulée par l'utilisateur")
            sys.exit(0)
    else:
        logger.info("⚠️ Mode automatique activé (--yes). Exécution de la migration...")
    
    success = make_responsable_id_nullable()
    
    if success:
        logger.info("✅ Migration terminée avec succès!")
        sys.exit(0)
    else:
        logger.error("❌ Migration échouée")
        sys.exit(1)

