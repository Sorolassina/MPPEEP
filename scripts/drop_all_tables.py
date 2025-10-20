#!/usr/bin/env python
"""
Script pour supprimer TOUTES les tables de la base de données
Fonctionne avec PostgreSQL et SQLite
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from app.core.config import settings


def drop_all_tables_postgres(engine):
    """Supprime toutes les tables PostgreSQL"""
    print("🗑️  Suppression de toutes les tables PostgreSQL...")
    
    with engine.connect() as conn:
        # Désactiver les contraintes de clés étrangères temporairement
        conn.execute(text("SET session_replication_role = 'replica';"))
        conn.commit()
        
        # Récupérer toutes les tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("ℹ️  Aucune table à supprimer")
            return
        
        print(f"📋 {len(tables)} table(s) trouvée(s) : {', '.join(tables)}")
        
        # Supprimer chaque table
        for table in tables:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
                print(f"   ✅ Table supprimée : {table}")
            except Exception as e:
                print(f"   ❌ Erreur sur {table} : {e}")
        
        conn.commit()
        
        # Réactiver les contraintes
        conn.execute(text("SET session_replication_role = 'origin';"))
        conn.commit()
        
        print("\n✅ Toutes les tables PostgreSQL ont été supprimées")


def drop_all_tables_sqlite(engine):
    """Supprime toutes les tables SQLite"""
    print("🗑️  Suppression de toutes les tables SQLite...")
    
    with engine.connect() as conn:
        # Désactiver les contraintes de clés étrangères
        conn.execute(text("PRAGMA foreign_keys = OFF;"))
        
        # Récupérer toutes les tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("ℹ️  Aucune table à supprimer")
            return
        
        print(f"📋 {len(tables)} table(s) trouvée(s) : {', '.join(tables)}")
        
        # Supprimer chaque table
        for table in tables:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}";'))
                print(f"   ✅ Table supprimée : {table}")
            except Exception as e:
                print(f"   ❌ Erreur sur {table} : {e}")
        
        conn.commit()
        
        # Réactiver les contraintes
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        conn.commit()
        
        print("\n✅ Toutes les tables SQLite ont été supprimées")


def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("🗑️  SUPPRESSION DE TOUTES LES TABLES")
    print("=" * 60)
    print(f"📂 Base de données : {settings.database_url}")
    print()
    
    # Confirmation
    print("⚠️  ATTENTION : Cette opération supprimera TOUTES les tables !")
    print("⚠️  Toutes les données seront perdues de manière irréversible !")
    print()
    
    confirmation = input("Voulez-vous continuer ? (tapez 'OUI' en majuscules) : ")
    if confirmation != "OUI":
        print("\n❌ Opération annulée")
        return
    
    print()
    
    # Créer le moteur
    engine = create_engine(settings.database_url, echo=False)
    
    # Détecter le type de base
    db_type = "postgres" if "postgresql" in settings.database_url else "sqlite"
    print(f"🔍 Type de base détecté : {db_type.upper()}")
    print()
    
    try:
        if db_type == "postgres":
            drop_all_tables_postgres(engine)
        else:
            drop_all_tables_sqlite(engine)
        
        print()
        print("=" * 60)
        print("✅ Opération terminée avec succès")
        print("=" * 60)
        print()
        print("💡 Pour recréer les tables, lancez : make db-init")
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERREUR : {e}")
        print("=" * 60)
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

