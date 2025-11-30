"""
Script de migration du schéma de base de données
Détecte et applique les modifications de structure des tables
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text, MetaData, create_engine
from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel, Session
from app.core.logging_config import get_logger
from app.core.config import settings

# Importer tous les modèles pour charger les métadonnées
from app.models import *

logger = get_logger(__name__)

class SchemaMigrator:
    """Gestionnaire de migration du schéma de base de données"""
    
    def __init__(self):
        # Créer l'engine avec gestion d'erreur
        try:
            self.engine = create_engine(
                settings.database_url,
                echo=False,
                pool_pre_ping=True
            )
            self.inspector = inspect(self.engine)
            self.metadata = MetaData()
        except Exception as e:
            logger.error(f"❌ Erreur de connexion à la base de données: {e}")
            logger.error(f"   URL: {settings.database_url}")
            logger.error(f"   DEBUG mode: {settings.DEBUG}")
            raise
        
    def get_current_schema(self) -> Dict[str, Dict]:
        """
        Récupère le schéma actuel de la base de données
        
        Returns:
            Dict avec structure: {table_name: {column_name: column_info}}
        """
        try:
            current_schema = {}
            
            # Récupérer toutes les tables existantes
            existing_tables = self.inspector.get_table_names()
            
            for table_name in existing_tables:
                # Récupérer les colonnes de chaque table
                columns = self.inspector.get_columns(table_name)
                current_schema[table_name] = {
                    col['name']: {
                        'type': str(col['type']),
                        'nullable': col['nullable'],
                        'default': col['default'],
                        'primary_key': col.get('primary_key', False)
                    }
                    for col in columns
                }
            
            logger.info(f"📊 Schéma actuel récupéré: {len(existing_tables)} tables")
            return current_schema
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du schéma: {e}")
            return {}
    
    def get_expected_schema(self) -> Dict[str, Dict]:
        """
        Récupère le schéma attendu basé sur les modèles SQLModel
        
        Returns:
            Dict avec structure: {table_name: {column_name: column_info}}
        """
        try:
            expected_schema = {}
            
            # Inspecter directement les métadonnées SQLModel sans créer les tables
            for table_name, table in SQLModel.metadata.tables.items():
                expected_schema[table_name] = {}
                
                for column in table.columns:
                    expected_schema[table_name][column.name] = {
                        'type': str(column.type),
                        'nullable': column.nullable,
                        'default': column.default.arg if column.default else None,
                        'primary_key': column.primary_key
                    }
            
            logger.info(f"📋 Schéma attendu généré: {len(expected_schema)} tables")
            return expected_schema
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération du schéma attendu: {e}")
            return {}
    
    def compare_schemas(self, current: Dict, expected: Dict) -> Dict:
        """
        Compare les schémas actuel et attendu
        
        Args:
            current: Schéma actuel de la DB
            expected: Schéma attendu des modèles
            
        Returns:
            Dict avec les différences détectées
        """
        differences = {
            'missing_tables': [],
            'extra_tables': [],
            'missing_columns': {},
            'extra_columns': {},
            'modified_columns': {},
            'type_changes': {}
        }
        
        # Tables manquantes
        for table_name in expected:
            if table_name not in current:
                differences['missing_tables'].append(table_name)
        
        # Tables en trop
        for table_name in current:
            if table_name not in expected:
                differences['extra_tables'].append(table_name)
        
        # Comparer les colonnes pour chaque table commune
        for table_name in expected:
            if table_name in current:
                current_cols = current[table_name]
                expected_cols = expected[table_name]
                
                # Colonnes manquantes
                missing_cols = []
                for col_name in expected_cols:
                    if col_name not in current_cols:
                        missing_cols.append(col_name)
                
                if missing_cols:
                    differences['missing_columns'][table_name] = missing_cols
                
                # Colonnes en trop
                extra_cols = []
                for col_name in current_cols:
                    if col_name not in expected_cols:
                        extra_cols.append(col_name)
                
                if extra_cols:
                    differences['extra_columns'][table_name] = extra_cols
                
                # Modifications de colonnes existantes
                for col_name in expected_cols:
                    if col_name in current_cols:
                        current_col = current_cols[col_name]
                        expected_col = expected_cols[col_name]
                        
                        # Vérifier les changements de type
                        if current_col['type'] != expected_col['type']:
                            if table_name not in differences['type_changes']:
                                differences['type_changes'][table_name] = {}
                            differences['type_changes'][table_name][col_name] = {
                                'current': current_col['type'],
                                'expected': expected_col['type']
                            }
                        
                        # Vérifier les changements de nullable
                        if current_col['nullable'] != expected_col['nullable']:
                            if table_name not in differences['modified_columns']:
                                differences['modified_columns'][table_name] = {}
                            if col_name not in differences['modified_columns'][table_name]:
                                differences['modified_columns'][table_name][col_name] = {}
                            differences['modified_columns'][table_name][col_name]['nullable'] = {
                                'current': current_col['nullable'],
                                'expected': expected_col['nullable']
                            }
        
        return differences
    
    def apply_migrations(self, differences: Dict, dry_run: bool = True) -> bool:
        """
        Applique les migrations détectées
        
        Args:
            differences: Différences détectées par compare_schemas
            dry_run: Si True, affiche seulement ce qui serait fait
            
        Returns:
            True si succès, False sinon
        """
        try:
            with Session(self.engine) as session:
                applied_columns = 0
                failed_columns = 0
                
                # Tables manquantes
                if differences['missing_tables']:
                    logger.info(f"📋 Tables manquantes: {differences['missing_tables']}")
                    if not dry_run:
                        # Créer les tables manquantes
                        SQLModel.metadata.create_all(self.engine, checkfirst=True)
                        logger.info("✅ Tables manquantes créées")
                
                # Colonnes manquantes
                if differences['missing_columns']:
                    for table_name, missing_cols in differences['missing_columns'].items():
                        logger.info(f"📋 Colonnes manquantes dans {table_name}: {missing_cols}")
                        if not dry_run:
                            for col_name in missing_cols:
                                # Récupérer la définition de la colonne depuis les métadonnées
                                table = SQLModel.metadata.tables[table_name]
                                column = table.columns[col_name]
                                
                                # Générer l'ALTER TABLE avec IF NOT EXISTS pour éviter les erreurs si la colonne existe déjà
                                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {column.type}"
                                if not column.nullable and column.default is None:
                                    # Ne pas ajouter NOT NULL si pas de default pour éviter les erreurs
                                    pass
                                elif not column.nullable:
                                    alter_sql += " NOT NULL"
                                if column.default is not None:
                                    alter_sql += f" DEFAULT {column.default}"
                                
                                try:
                                    session.execute(text(alter_sql))
                                    session.commit()  # Commiter immédiatement après chaque colonne réussie
                                    logger.info(f"✅ Colonne {col_name} ajoutée à {table_name}")
                                    applied_columns += 1
                                except Exception as e:
                                    logger.warning(f"⚠️ Erreur ajout colonne {col_name} (peut-être existe déjà): {e}")
                                    # Rollback et continuer avec la colonne suivante
                                    try:
                                        session.rollback()
                                    except Exception:
                                        pass
                                    failed_columns += 1
                                    # Continuer avec la colonne suivante même si celle-ci échoue
                                    continue
                
                # Colonnes en trop (optionnel - généralement on ne les supprime pas)
                if differences['extra_columns']:
                    logger.warning("⚠️  Colonnes en trop détectées (non supprimées pour sécurité):")
                    for table_name, extra_cols in differences['extra_columns'].items():
                        logger.warning(f"   {table_name}: {extra_cols}")
                
                # Changements de type (attention - peut causer des pertes de données)
                if differences['type_changes']:
                    logger.warning("⚠️  Changements de type détectés (non appliqués pour sécurité):")
                    for table_name, changes in differences['type_changes'].items():
                        for col_name, change_info in changes.items():
                            logger.warning(f"   {table_name}.{col_name}: {change_info['current']} → {change_info['expected']}")
                
                # Les commits sont déjà faits individuellement après chaque colonne
                if not dry_run:
                    if applied_columns > 0:
                        logger.info(f"✅ {applied_columns} colonne(s) ajoutée(s) avec succès")
                    if failed_columns > 0:
                        logger.warning(f"⚠️ {failed_columns} colonne(s) n'ont pas pu être ajoutée(s)")
                    if applied_columns == 0 and failed_columns == 0 and not differences.get('missing_tables'):
                        # Rien n'a été appliqué car seuls des changements de type sont détectés
                        logger.info("✅ Aucune migration structurelle à appliquer (seuls changements de type détectés, non appliqués pour sécurité)")
                    else:
                        logger.info("✅ Migrations appliquées avec succès")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'application des migrations: {e}")
            # Tenter un rollback si la session existe encore
            try:
                with Session(self.engine) as session:
                    session.rollback()
            except Exception:
                pass
            return False
    
    def run_migration_check(self, dry_run: bool = True) -> bool:
        """
        Exécute une vérification complète des migrations
        
        Args:
            dry_run: Si True, affiche seulement les différences sans les appliquer
            
        Returns:
            True si pas de migration nécessaire ou succès, False sinon
        """
        logger.info("\n" + "="*60)
        logger.info("🔍 Vérification des migrations de schéma...")
        logger.info("="*60)
        
        # Récupérer les schémas
        current_schema = self.get_current_schema()
        expected_schema = self.get_expected_schema()
        
        if not current_schema or not expected_schema:
            logger.error("❌ Impossible de récupérer les schémas")
            return False
        
        # Comparer les schémas
        differences = self.compare_schemas(current_schema, expected_schema)
        
        # Vérifier s'il y a des différences
        has_differences = any([
            differences['missing_tables'],
            differences['missing_columns'],
            differences['extra_columns'],
            differences['modified_columns'],
            differences['type_changes']
        ])
        
        if not has_differences:
            logger.info("✅ Aucune migration nécessaire - Schéma à jour")
            return True
        
        # Afficher les différences
        logger.info("📊 Différences détectées:")
        
        if differences['missing_tables']:
            logger.info(f"   📋 Tables manquantes: {differences['missing_tables']}")
        
        if differences['missing_columns']:
            logger.info("   📋 Colonnes manquantes:")
            for table, cols in differences['missing_columns'].items():
                logger.info(f"      {table}: {cols}")
        
        if differences['extra_columns']:
            logger.info("   📋 Colonnes en trop:")
            for table, cols in differences['extra_columns'].items():
                logger.info(f"      {table}: {cols}")
        
        if differences['type_changes']:
            logger.info("   📋 Changements de type:")
            for table, changes in differences['type_changes'].items():
                for col, change in changes.items():
                    logger.info(f"      {table}.{col}: {change['current']} → {change['expected']}")
        
        if differences['modified_columns']:
            logger.info("   📋 Modifications de colonnes:")
            for table, changes in differences['modified_columns'].items():
                for col, change in changes.items():
                    logger.info(f"      {table}.{col}: {change}")
        
        # Appliquer les migrations si demandé
        if not dry_run:
            logger.info("\n🔄 Application des migrations...")
            return self.apply_migrations(differences, dry_run=False)
        else:
            logger.info("\n💡 Mode dry-run activé - Aucune modification appliquée")
            logger.info("   Pour appliquer les migrations: python scripts/migrate_schema.py --apply")
            return True

def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Vérification et migration du schéma de base de données")
    parser.add_argument("--apply", action="store_true", help="Appliquer les migrations (par défaut: dry-run)")
    parser.add_argument("--check-only", action="store_true", help="Vérification seulement (pas d'application)")
    
    args = parser.parse_args()
    
    # Déterminer le mode
    dry_run = not args.apply and not args.check_only
    
    migrator = SchemaMigrator()
    success = migrator.run_migration_check(dry_run=dry_run)
    
    if success:
        logger.info("✅ Vérification terminée avec succès")
        sys.exit(0)
    else:
        logger.error("❌ Erreur lors de la vérification")
        sys.exit(1)

if __name__ == "__main__":
    main()
