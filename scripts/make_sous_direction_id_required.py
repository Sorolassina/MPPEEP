"""
Script pour rendre sous_direction_id obligatoire (NOT NULL) dans la table service
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
from app.core.logging_config import get_logger

logger = get_logger(__name__)

def make_sous_direction_id_required():
    """Rend la colonne sous_direction_id NOT NULL"""
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                logger.info("🔄 Vérification de l'état actuel de sous_direction_id")
                
                # Vérifier l'état actuel
                check_query = text("""
                    SELECT 
                        column_name, 
                        is_nullable,
                        data_type
                    FROM information_schema.columns 
                    WHERE table_name = 'service' 
                    AND column_name = 'sous_direction_id'
                """)
                
                result = conn.execute(check_query).fetchone()
                
                if not result:
                    logger.warning("⚠️ Colonne sous_direction_id non trouvée dans la table service")
                    print("⚠️ Colonne sous_direction_id non trouvée dans la table service")
                    trans.rollback()
                    return False
                
                column_name, is_nullable, data_type = result
                logger.info(f"📊 État actuel: {column_name}, nullable: {is_nullable}, type: {data_type}")
                print(f"📊 État actuel: {column_name}, nullable: {is_nullable}, type: {data_type}")
                
                if is_nullable == 'NO':
                    logger.info("✅ La colonne est déjà NOT NULL. Aucune modification nécessaire.")
                    print("✅ La colonne est déjà NOT NULL. Aucune modification nécessaire.")
                    trans.rollback()
                    return True
                
                # Vérifier s'il y a des services sans sous_direction_id
                count_query = text("""
                    SELECT COUNT(*) 
                    FROM service 
                    WHERE sous_direction_id IS NULL
                """)
                
                count_result = conn.execute(count_query).fetchone()
                null_count = count_result[0] if count_result else 0
                
                if null_count > 0:
                    logger.warning(f"⚠️ Il y a {null_count} service(s) sans sous_direction_id")
                    print(f"\n⚠️ ATTENTION: Il y a {null_count} service(s) sans sous_direction_id")
                    
                    # Lister ces services
                    list_query = text("""
                        SELECT id, code, libelle 
                        FROM service 
                        WHERE sous_direction_id IS NULL
                    """)
                    
                    services = conn.execute(list_query).fetchall()
                    
                    print("\n📋 Services sans sous_direction_id:")
                    for service in services:
                        print(f"   - ID: {service[0]}, Code: {service[1]}, Libellé: {service[2]}")
                    
                    print("\n❌ Impossible de rendre la colonne NOT NULL car il y a des services sans sous_direction_id.")
                    print("   Veuillez d'abord corriger ces services en leur assignant une sous-direction.")
                    logger.error("❌ Impossible de rendre la colonne NOT NULL car il y a des services sans sous_direction_id")
                    trans.rollback()
                    return False
                
                # Modifier la colonne pour rendre NOT NULL
                logger.info("📝 Modification de la colonne pour rendre NOT NULL")
                print("\n📝 Modification de la colonne pour rendre NOT NULL...")
                
                conn.execute(text("""
                    ALTER TABLE service 
                    ALTER COLUMN sous_direction_id SET NOT NULL
                """))
                
                trans.commit()
                
                logger.info("✅ Colonne sous_direction_id rendue NOT NULL avec succès")
                print("✅ Colonne sous_direction_id rendue NOT NULL avec succès")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Erreur lors de la modification: {e}")
                print(f"❌ Erreur lors de la modification: {e}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rendre sous_direction_id obligatoire dans la table service")
    parser.add_argument("--yes", action="store_true", help="Confirmer automatiquement sans demander")
    args = parser.parse_args()
    
    if not args.yes:
        print("⚠️  Cette opération va rendre la colonne sous_direction_id obligatoire (NOT NULL)")
        print("   Assurez-vous qu'aucun service n'a de sous_direction_id NULL avant de continuer.")
        response = input("\nContinuer ? (oui/non): ")
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            print("❌ Opération annulée")
            sys.exit(0)
    
    success = make_sous_direction_id_required()
    sys.exit(0 if success else 1)

