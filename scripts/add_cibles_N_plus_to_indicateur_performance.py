#!/usr/bin/env python3
"""
Script pour ajouter les colonnes cible_N_plus_1 et cible_N_plus_2 
à la table indicateur_performance
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules de l'application
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_session
from sqlalchemy import text

def main():
    """Exécute la migration SQL pour ajouter les nouvelles colonnes"""
    script_path = Path(__file__).parent / "add_cibles_N_plus_to_indicateur_performance.sql"
    
    if not script_path.exists():
        print(f"❌ Erreur: Le fichier {script_path} n'existe pas")
        return 1
    
    with open(script_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    print("🔄 Exécution de la migration pour ajouter les colonnes cible_N_plus_1 et cible_N_plus_2...")
    
    try:
        session = next(get_session())
        session.execute(text(sql_script))
        session.commit()
        print("✅ Migration réussie: Les colonnes ont été ajoutées à la table indicateur_performance")
        print("   - cible_N_plus_1")
        print("   - cible_N_plus_2")
        return 0
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        session.rollback()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())

