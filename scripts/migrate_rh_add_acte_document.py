#!/usr/bin/env python3
"""
Migration : Ajouter les colonnes acte_type et document_joint à HRRequest
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine
from app.core.logging_config import setup_logging, get_logger
from sqlalchemy import text

setup_logging()
logger = get_logger(__name__)

print("=" * 60)
print("🔄 Migration : Ajout colonnes acte_type et document_joint")
print("=" * 60)

try:
    with engine.connect() as conn:
        # Vérifier si les colonnes existent déjà
        logger.info("📋 Vérification de la structure de la table hrrequest...")
        
        # SQLite : utiliser PRAGMA
        result = conn.execute(text("PRAGMA table_info(hrrequest)"))
        columns = [row[1] for row in result.fetchall()]
        
        logger.info(f"   Colonnes actuelles : {columns}")
        
        # Ajouter acte_type si manquant
        if 'acte_type' not in columns:
            logger.info("📝 Ajout de la colonne 'acte_type'...")
            conn.execute(text("ALTER TABLE hrrequest ADD COLUMN acte_type VARCHAR(100)"))
            conn.commit()
            logger.info("   ✅ Colonne 'acte_type' ajoutée")
        else:
            logger.info("   ⏭️  Colonne 'acte_type' déjà existante")
        
        # Ajouter document_joint si manquant
        if 'document_joint' not in columns:
            logger.info("📝 Ajout de la colonne 'document_joint'...")
            conn.execute(text("ALTER TABLE hrrequest ADD COLUMN document_joint VARCHAR(500)"))
            conn.commit()
            logger.info("   ✅ Colonne 'document_joint' ajoutée")
        else:
            logger.info("   ⏭️  Colonne 'document_joint' déjà existante")
        
        # Ajouter document_filename si manquant
        if 'document_filename' not in columns:
            logger.info("📝 Ajout de la colonne 'document_filename'...")
            conn.execute(text("ALTER TABLE hrrequest ADD COLUMN document_filename VARCHAR(255)"))
            conn.commit()
            logger.info("   ✅ Colonne 'document_filename' ajoutée")
        else:
            logger.info("   ⏭️  Colonne 'document_filename' déjà existante")
        
        print("=" * 60)
        print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
        print("=" * 60)
        print("\n💡 La table hrrequest a été mise à jour.")
        print("   Nouvelles colonnes disponibles :")
        print("   - acte_type (type d'acte administratif)")
        print("   - document_joint (chemin du fichier)")
        print("   - document_filename (nom original)")

except Exception as e:
    print("=" * 60)
    print("❌ ERREUR LORS DE LA MIGRATION")
    print("=" * 60)
    logger.error(f"Erreur: {e}", exc_info=True)
    sys.exit(1)

