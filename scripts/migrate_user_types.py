#!/usr/bin/env python3
"""
Script de migration pour ajouter les nouveaux types d'utilisateurs
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging_config import get_logger
from app.core.enums import UserType
from app.models.user import User
from app.db.session import get_session
from sqlmodel import Session, select

logger = get_logger(__name__)

def migrate_user_types():
    """
    Migre les anciens types d'utilisateurs vers les nouveaux
    """
    logger.info("🔄 Migration des types d'utilisateurs...")
    
    try:
        with Session(next(get_session())) as session:
            # Mapping des anciens types vers les nouveaux
            type_mapping = {
                "agent": UserType.AGENT.value,
                "chef service": UserType.CS.value,
                "directeur": UserType.DAF.value,  # Les directeurs deviennent DAF
                "directeur des ressources humaines": UserType.SDRH.value,
                "directeur administratif et financier": UserType.DAF.value,
                "invité": UserType.INVITE.value,
            }
            
            # Récupérer tous les utilisateurs
            users = session.exec(select(User)).all()
            
            updated_count = 0
            
            for user in users:
                old_type = user.type_user
                new_type = type_mapping.get(old_type)
                
                if new_type and new_type != old_type:
                    logger.info(f"🔄 Migration utilisateur {user.email}: {old_type} → {new_type}")
                    user.type_user = new_type
                    updated_count += 1
                elif old_type not in type_mapping and old_type not in [t.value for t in UserType]:
                    # Type inconnu, migrer vers USER par défaut
                    logger.warning(f"⚠️  Type inconnu pour {user.email}: {old_type} → user")
                    user.type_user = UserType.AGENT.value
                    updated_count += 1
            
            if updated_count > 0:
                session.commit()
                logger.info(f"✅ {updated_count} utilisateurs migrés avec succès")
            else:
                logger.info("ℹ️  Aucune migration nécessaire")
            
            # Afficher le résumé des types actuels
            logger.info("\n📊 Résumé des types d'utilisateurs après migration:")
            type_counts = {}
            for user in users:
                type_counts[user.type_user] = type_counts.get(user.type_user, 0) + 1
            
            for user_type, count in sorted(type_counts.items()):
                display_name = PermissionManager.get_user_type_display_name(user_type)
                logger.info(f"   {display_name} ({user_type}): {count} utilisateur(s)")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}", exc_info=True)
        return False

def main():
    """Point d'entrée principal"""
    logger.info("\n" + "="*60)
    logger.info("🚀 MIGRATION DES TYPES D'UTILISATEURS")
    logger.info("="*60)
    
    success = migrate_user_types()
    
    if success:
        logger.info("✅ Migration terminée avec succès!")
    else:
        logger.error("❌ Migration échouée!")
    
    logger.info("="*60 + "\n")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
