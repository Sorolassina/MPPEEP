#!/usr/bin/env python3
"""
Script pour ajouter le champ valeur_actuelle aux tables orientation_strategique et resultat_strategique
"""

import sys
from pathlib import Path
from app.db.session import get_session
from sqlalchemy import text

def main():
    script_path = Path(__file__).parent / "add_valeur_actuelle_to_orientation_and_resultat.sql"
    
    if not script_path.exists():
        print(f"❌ Erreur: Le fichier {script_path} n'existe pas")
        return 1
    
    with open(script_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    print("🔄 Exécution de la migration pour ajouter valeur_actuelle...")
    
    try:
        session = next(get_session())
        session.execute(text(sql_script))
        session.commit()
        print("✅ Migration réussie: Les colonnes valeur_actuelle ont été ajoutées")
        print("   - orientation_strategique.valeur_actuelle")
        print("   - resultat_strategique.valeur_actuelle")
        return 0
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        session.rollback()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())

