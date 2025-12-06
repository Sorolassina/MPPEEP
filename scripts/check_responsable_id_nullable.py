"""
Script pour vérifier si responsable_id est nullable
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine

def check_nullable():
    """Vérifie si responsable_id est nullable"""
    try:
        with engine.connect() as conn:
            check_query = text("""
                SELECT 
                    column_name, 
                    is_nullable,
                    data_type
                FROM information_schema.columns 
                WHERE table_name = 'objectif_performance' 
                AND column_name = 'responsable_id'
            """)
            
            result = conn.execute(check_query).fetchone()
            conn.commit()
            
            if not result:
                print("⚠️ Colonne responsable_id non trouvée")
                return
            
            column_name, is_nullable, data_type = result
            print(f"📊 Colonne: {column_name}")
            print(f"   Nullable: {is_nullable}")
            print(f"   Type: {data_type}")
            
            if is_nullable == 'YES':
                print("✅ La colonne est nullable - OK")
            else:
                print("❌ La colonne n'est PAS nullable - Migration nécessaire")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_nullable()

