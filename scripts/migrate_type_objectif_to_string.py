"""
Script de migration: Convertir type_objectif de ENUM à VARCHAR
Date: 2025-12-04
Description: Convertit la colonne type_objectif de objectif_performance 
             d'un enum PostgreSQL vers VARCHAR pour stocker des strings
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def migrate_type_objectif_to_string():
    """Convertit la colonne type_objectif de ENUM à VARCHAR"""
    
    try:
        with engine.connect() as conn:
            # Démarrer une transaction
            trans = conn.begin()
            
            try:
                logger.info("🔄 Début de la migration: type_objectif ENUM → VARCHAR")
                
                # Vérifier si la colonne existe et son type actuel
                check_query = text("""
                    SELECT 
                        column_name, 
                        data_type, 
                        udt_name
                    FROM information_schema.columns 
                    WHERE table_name = 'objectif_performance' 
                    AND column_name = 'type_objectif'
                """)
                
                result = conn.execute(check_query).fetchone()
                
                if not result:
                    logger.warning("⚠️ Colonne type_objectif non trouvée. La table existe-t-elle ?")
                    trans.rollback()
                    return False
                
                column_name, data_type, udt_name = result
                logger.info(f"📊 Colonne actuelle: {column_name}, type: {data_type}, udt: {udt_name}")
                
                # Si c'est déjà VARCHAR, pas besoin de migration
                if data_type == 'character varying' or data_type == 'varchar':
                    logger.info("✅ La colonne est déjà de type VARCHAR. Aucune migration nécessaire.")
                    trans.rollback()
                    return True
                
                # Si ce n'est pas un enum, on ne peut pas migrer
                if data_type != 'USER-DEFINED' and udt_name != 'typeobjectif':
                    logger.warning(f"⚠️ Type de colonne inattendu: {data_type} ({udt_name})")
                    logger.warning("⚠️ Migration annulée pour éviter la perte de données.")
                    trans.rollback()
                    return False
                
                logger.info("📝 Étape 1: Création de la colonne temporaire VARCHAR")
                conn.execute(text("""
                    ALTER TABLE objectif_performance 
                    ADD COLUMN type_objectif_new VARCHAR(50)
                """))
                
                logger.info("📝 Étape 2: Copie des données avec conversion")
                conn.execute(text("""
                    UPDATE objectif_performance 
                    SET type_objectif_new = CASE 
                        WHEN type_objectif::text = 'GLOBAL' THEN 'global'
                        WHEN type_objectif::text = 'SPECIFIQUE' THEN 'specifique'
                        WHEN type_objectif::text = 'FINANCIER' THEN 'FINANCIER'
                        WHEN type_objectif::text = 'RH' THEN 'RH'
                        WHEN type_objectif::text = 'QUALITE' THEN 'QUALITE'
                        WHEN type_objectif::text = 'CLIENT' THEN 'CLIENT'
                        ELSE LOWER(type_objectif::text)
                    END
                """))
                
                logger.info("📝 Étape 3: Définition de la valeur par défaut")
                conn.execute(text("""
                    ALTER TABLE objectif_performance 
                    ALTER COLUMN type_objectif_new SET DEFAULT 'specifique'
                """))
                
                logger.info("📝 Étape 4: Suppression de l'ancienne colonne enum")
                conn.execute(text("""
                    ALTER TABLE objectif_performance 
                    DROP COLUMN type_objectif
                """))
                
                logger.info("📝 Étape 5: Renommage de la nouvelle colonne")
                conn.execute(text("""
                    ALTER TABLE objectif_performance 
                    RENAME COLUMN type_objectif_new TO type_objectif
                """))
                
                # Vérification finale
                verify_query = text("""
                    SELECT 
                        column_name, 
                        data_type, 
                        character_maximum_length,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'objectif_performance' 
                    AND column_name = 'type_objectif'
                """)
                
                result = conn.execute(verify_query).fetchone()
                if result:
                    logger.info(f"✅ Migration réussie!")
                    logger.info(f"   Colonne: {result[0]}")
                    logger.info(f"   Type: {result[1]}")
                    logger.info(f"   Longueur max: {result[2]}")
                    logger.info(f"   Valeur par défaut: {result[3]}")
                
                # Commit de la transaction
                trans.commit()
                logger.info("✅ Migration terminée avec succès!")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Erreur lors de la migration: {e}")
                logger.error("🔄 Rollback effectué. Aucune modification n'a été appliquée.")
                raise
                
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration: Convertir type_objectif de ENUM à VARCHAR")
    parser.add_argument('--yes', '-y', action='store_true', help='Exécuter sans confirmation')
    args = parser.parse_args()
    
    logger.info("🚀 Démarrage de la migration type_objectif ENUM → VARCHAR")
    
    # Demander confirmation sauf si --yes est passé
    if not args.yes:
        response = input("⚠️ Cette migration va modifier la structure de la base de données. Continuer? (oui/non): ")
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            logger.info("❌ Migration annulée par l'utilisateur")
            sys.exit(0)
    else:
        logger.info("⚠️ Mode automatique activé (--yes). Exécution de la migration...")
    
    success = migrate_type_objectif_to_string()
    
    if success:
        logger.info("✅ Migration terminée avec succès!")
        sys.exit(0)
    else:
        logger.error("❌ Migration échouée")
        sys.exit(1)

