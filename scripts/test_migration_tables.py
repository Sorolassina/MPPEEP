#!/usr/bin/env python3
"""
Test simple des migrations PostgreSQL
"""

import os
import sys
from pathlib import Path

# Configuration
os.environ['DATABASE_URL'] = 'postgresql://mppeepuser:mppeep@localhost:5432/mppeep'

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.migrate_schema import SchemaMigrator

def main():
    print("=== TEST MIGRATIONS POSTGRESQL ===")
    
    try:
        migrator = SchemaMigrator()
        
        # Récupérer les schémas
        current = migrator.get_current_schema()
        expected = migrator.get_expected_schema()
        
        print(f"Tables actuelles: {len(current)}")
        print(f"Tables attendues: {len(expected)}")
        
        # Afficher les noms des tables
        print("\n📋 TABLES ACTUELLES (56):")
        for i, table_name in enumerate(sorted(current.keys()), 1):
            print(f"  {i:2d}. {table_name}")
        
        print("\n📋 TABLES ATTENDUES (45):")
        for i, table_name in enumerate(sorted(expected.keys()), 1):
            print(f"  {i:2d}. {table_name}")
        
        # Comparer
        differences = migrator.compare_schemas(current, expected)
        
        print(f"\nTables manquantes: {len(differences['missing_tables'])}")
        print(f"Colonnes manquantes: {sum(len(cols) for cols in differences['missing_columns'].values())}")
        print(f"Colonnes en trop: {sum(len(cols) for cols in differences['extra_columns'].values())}")
        
        # Afficher les détails
        if differences['missing_tables']:
            print(f"\n❌ Tables manquantes: {differences['missing_tables']}")
        
        if differences['extra_columns']:
            print("\n⚠️  Tables avec colonnes en trop:")
            for table, cols in differences['extra_columns'].items():
                print(f"  {table}: {cols}")
        
        if differences['missing_columns']:
            print("\n➕ Tables avec colonnes manquantes:")
            for table, cols in differences['missing_columns'].items():
                print(f"  {table}: {cols}")
        
        # Trouver les tables en trop
        current_tables = set(current.keys())
        expected_tables = set(expected.keys())
        extra_tables = current_tables - expected_tables
        
        if extra_tables:
            print(f"\n📊 TABLES EN TROP ({len(extra_tables)}):")
            for i, table_name in enumerate(sorted(extra_tables), 1):
                print(f"  {i:2d}. {table_name}")
        
        print("\n=== FIN TEST ===")
        
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
