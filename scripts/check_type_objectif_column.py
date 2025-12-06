"""
Script pour vérifier le type de la colonne type_objectif
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)

def check_column_type():
    """Vérifie le type de la colonne type_objectif"""
    try:
        with engine.connect() as conn:
            check_query = text("""
                SELECT 
                    column_name, 
                    data_type, 
                    udt_name,
                    character_maximum_length,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = 'objectif_performance' 
                AND column_name = 'type_objectif'
            """)
            
            result = conn.execute(check_query).fetchone()
            conn.commit()  # Commit pour voir les résultats
            
            if not result:
                print("⚠️ Colonne type_objectif non trouvée dans objectif_performance")
                logger.warning("⚠️ Colonne type_objectif non trouvée dans objectif_performance")
                return
            
            column_name, data_type, udt_name, max_length, default = result
            print(f"📊 Informations sur la colonne type_objectif:")
            print(f"   Nom: {column_name}")
            print(f"   Type de données: {data_type}")
            print(f"   Type UDT: {udt_name}")
            print(f"   Longueur max: {max_length}")
            print(f"   Valeur par défaut: {default}")
            
            logger.info(f"📊 Informations sur la colonne type_objectif:")
            logger.info(f"   Nom: {column_name}")
            logger.info(f"   Type de données: {data_type}")
            logger.info(f"   Type UDT: {udt_name}")
            logger.info(f"   Longueur max: {max_length}")
            logger.info(f"   Valeur par défaut: {default}")
            
            if data_type == 'character varying' or data_type == 'varchar':
                print("✅ La colonne est déjà de type VARCHAR - Migration non nécessaire")
                logger.info("✅ La colonne est déjà de type VARCHAR - Migration non nécessaire")
            elif data_type == 'USER-DEFINED' and udt_name == 'typeobjectif':
                print("⚠️ La colonne est encore de type ENUM - Migration nécessaire")
                logger.info("⚠️ La colonne est encore de type ENUM - Migration nécessaire")
            else:
                print(f"⚠️ Type inattendu: {data_type} ({udt_name})")
                logger.warning(f"⚠️ Type inattendu: {data_type} ({udt_name})")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        logger.error(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_column_type()

