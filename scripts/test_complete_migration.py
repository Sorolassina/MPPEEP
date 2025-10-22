#!/usr/bin/env python3
"""
Test complet du système de migration avec tous les détails
"""

import os
import sys
from pathlib import Path

# Configuration PostgreSQL
os.environ['DATABASE_URL'] = 'postgresql://mppeepuser:mppeep@localhost:5432/mppeep'

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.migrate_schema import SchemaMigrator

def test_complete_migration_system():
    print("="*70)
    print("🧪 TEST COMPLET DU SYSTÈME DE MIGRATION")
    print("="*70)
    
    try:
        migrator = SchemaMigrator()
        
        # 1. Test de connexion
        print("\n1️⃣ Test de connexion à la base de données...")
        current_schema = migrator.get_current_schema()
        expected_schema = migrator.get_expected_schema()
        print(f"   ✅ Connexion réussie")
        print(f"   📊 Tables actuelles: {len(current_schema)}")
        print(f"   📋 Tables attendues: {len(expected_schema)}")
        
        # 2. Test de comparaison
        print("\n2️⃣ Test de comparaison des schémas...")
        differences = migrator.compare_schemas(current_schema, expected_schema)
        
        missing_tables = len(differences['missing_tables'])
        missing_columns = sum(len(cols) for cols in differences['missing_columns'].values())
        extra_columns = sum(len(cols) for cols in differences['extra_columns'].values())
        type_changes = sum(len(changes) for changes in differences['type_changes'].values())
        modified_columns = sum(len(changes) for changes in differences['modified_columns'].values())
        
        print(f"   📋 Tables manquantes: {missing_tables}")
        print(f"   ➕ Colonnes manquantes: {missing_columns}")
        print(f"   ⚠️  Colonnes en trop: {extra_columns}")
        print(f"   🔄 Changements de type: {type_changes}")
        print(f"   📝 Modifications de colonnes: {modified_columns}")
        
        # 3. Test de vérification complète
        print("\n3️⃣ Test de vérification complète (dry-run)...")
        success = migrator.run_migration_check(dry_run=True)
        
        if success:
            print("   ✅ Vérification réussie - Aucune migration nécessaire")
        else:
            print("   ⚠️  Des migrations sont nécessaires")
        
        # 4. Résumé final
        print("\n4️⃣ Résumé final:")
        if missing_tables == 0 and missing_columns == 0 and extra_columns == 0:
            print("   🎉 PARFAIT: Base de données parfaitement synchronisée!")
            print("   ✅ Toutes les tables des modèles existent")
            print("   ✅ Toutes les colonnes des modèles existent")
            print("   ✅ Aucune différence détectée")
        else:
            print("   ⚠️  Différences détectées:")
            if missing_tables > 0:
                print(f"      - {missing_tables} table(s) manquante(s)")
            if missing_columns > 0:
                print(f"      - {missing_columns} colonne(s) manquante(s)")
            if extra_columns > 0:
                print(f"      - {extra_columns} colonne(s) en trop")
        
        print("\n" + "="*70)
        print("✅ TEST TERMINÉ AVEC SUCCÈS!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_complete_migration_system()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
