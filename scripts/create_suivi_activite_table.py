#!/usr/bin/env python3
"""
Script pour créer la table suivi_activite
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_session
from sqlalchemy import text

def main():
    script_path = Path(__file__).parent / "create_suivi_activite_table.sql"
    
    if not script_path.exists():
        print(f"❌ Erreur: Le fichier {script_path} n'existe pas")
        return 1
    
    with open(script_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    print("🔄 Exécution de la migration pour créer la table suivi_activite...")
    
    try:
        session = next(get_session())
        session.execute(text(sql_script))
        session.commit()
        print("✅ Migration réussie: La table suivi_activite a été créée")
        return 0
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        session.rollback()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())

