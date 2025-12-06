#!/usr/bin/env python3
"""
Script simple pour exécuter la migration SQL
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import engine
from sqlalchemy import text

def main():
    """Exécute la migration SQL pour ajouter les nouvelles colonnes"""
    script_path = Path(__file__).parent / "scripts" / "add_cibles_N_plus_to_indicateur_performance.sql"
    
    if not script_path.exists():
        print(f"❌ Erreur: Le fichier {script_path} n'existe pas")
        return 1
    
    with open(script_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    print("🔄 Exécution de la migration pour ajouter les colonnes cible_N_plus_1 et cible_N_plus_2...")
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql_script))
            conn.commit()
        print("✅ Migration réussie: Les colonnes ont été ajoutées à la table indicateur_performance")
        print("   - cible_N_plus_1")
        print("   - cible_N_plus_2")
        return 0
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

