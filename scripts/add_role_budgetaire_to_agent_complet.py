#!/usr/bin/env python3
"""
Script de migration pour ajouter la colonne role_budgetaire à la table agent_complet
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au path pour les imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.db.session import engine
from sqlalchemy import text

def migrate():
    """Exécute la migration pour ajouter role_budgetaire"""
    
    sql_file = root_dir / "scripts" / "add_role_budgetaire_to_agent_complet.sql"
    
    if not sql_file.exists():
        print(f"❌ Fichier SQL non trouvé: {sql_file}")
        return False
    
    print("🔄 Exécution de la migration: Ajout de role_budgetaire à agent_complet...")
    
    try:
        with engine.connect() as conn:
            # Lire et exécuter le script SQL
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            conn.execute(text(sql_content))
            conn.commit()
            
        print("✅ Migration réussie: La colonne role_budgetaire a été ajoutée à agent_complet")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migration: Ajouter role_budgetaire à agent_complet")
    parser.add_argument("--yes", action="store_true", help="Exécuter sans confirmation")
    args = parser.parse_args()
    
    if not args.yes:
        response = input("⚠️  Cette migration va ajouter la colonne role_budgetaire à la table agent_complet. Continuer? (oui/non): ")
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            print("❌ Migration annulée")
            sys.exit(1)
    
    success = migrate()
    sys.exit(0 if success else 1)

