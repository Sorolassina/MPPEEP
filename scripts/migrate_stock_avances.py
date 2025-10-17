#!/usr/bin/env python3
"""
Script de migration pour ajouter les fonctionnalités avancées au module Stock :
- Gestion des articles périssables (lots, dates de péremption)
- Amortissement du matériel (dépréciation comptable)
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, create_engine, text
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def migrate_database():
    """Applique les migrations pour les fonctionnalités avancées du stock"""
    
    logger.info("=" * 70)
    logger.info("MIGRATION : Fonctionnalités avancées du module Stock")
    logger.info("=" * 70)
    
    # Créer l'engine
    engine = create_engine(settings.database_url)
    
    with Session(engine) as session:
        try:
            # ============================================
            # 1. AJOUTER LES COLONNES POUR ARTICLES PÉRISSABLES
            # ============================================
            logger.info("\n📅 1. Migration des articles périssables...")
            
            colonnes_perissables = [
                ("est_perissable", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("duree_conservation_jours", "INTEGER"),
                ("seuil_alerte_peremption_jours", "INTEGER DEFAULT 30 NOT NULL"),
            ]
            
            for colonne, type_sql in colonnes_perissables:
                try:
                    session.exec(text(f"ALTER TABLE article ADD COLUMN {colonne} {type_sql}"))
                    logger.info(f"✅ Colonne 'article.{colonne}' ajoutée")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                        logger.info(f"ℹ️  Colonne 'article.{colonne}' existe déjà")
                    else:
                        logger.error(f"❌ Erreur ajout colonne '{colonne}': {e}")
            
            # ============================================
            # 2. AJOUTER LES COLONNES POUR MATÉRIELS AMORTISSABLES
            # ============================================
            logger.info("\n💰 2. Migration des matériels amortissables...")
            
            colonnes_amortissement = [
                ("est_amortissable", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("date_acquisition", "DATE"),
                ("valeur_acquisition", "DECIMAL(15, 2)"),
                ("duree_amortissement_annees", "INTEGER"),
                ("taux_amortissement", "DECIMAL(5, 2)"),
                ("valeur_residuelle", "DECIMAL(15, 2)"),
                ("methode_amortissement", "VARCHAR(20) DEFAULT 'LINEAIRE'"),
            ]
            
            for colonne, type_sql in colonnes_amortissement:
                try:
                    session.exec(text(f"ALTER TABLE article ADD COLUMN {colonne} {type_sql}"))
                    logger.info(f"✅ Colonne 'article.{colonne}' ajoutée")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                        logger.info(f"ℹ️  Colonne 'article.{colonne}' existe déjà")
                    else:
                        logger.error(f"❌ Erreur ajout colonne '{colonne}': {e}")
            
            # ============================================
            # 3. CRÉER LA TABLE LOT_PERISSABLE
            # ============================================
            logger.info("\n📦 3. Création de la table 'lot_perissable'...")
            
            try:
                session.exec(text("""
                    CREATE TABLE IF NOT EXISTS lot_perissable (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        article_id INTEGER NOT NULL,
                        numero_lot VARCHAR(100) NOT NULL,
                        date_fabrication DATE,
                        date_reception DATE NOT NULL,
                        date_peremption DATE NOT NULL,
                        quantite_initiale DECIMAL(10, 2) NOT NULL,
                        quantite_restante DECIMAL(10, 2) NOT NULL,
                        statut VARCHAR(20) DEFAULT 'ACTIF' NOT NULL,
                        fournisseur_id INTEGER,
                        observations TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (article_id) REFERENCES article(id),
                        FOREIGN KEY (fournisseur_id) REFERENCES fournisseur(id)
                    )
                """))
                logger.info("✅ Table 'lot_perissable' créée")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️  Table 'lot_perissable' existe déjà")
                else:
                    logger.error(f"❌ Erreur création table 'lot_perissable': {e}")
            
            # Index sur numero_lot pour recherches rapides
            try:
                session.exec(text("CREATE INDEX IF NOT EXISTS idx_lot_perissable_numero ON lot_perissable(numero_lot)"))
                session.exec(text("CREATE INDEX IF NOT EXISTS idx_lot_perissable_article ON lot_perissable(article_id)"))
                session.exec(text("CREATE INDEX IF NOT EXISTS idx_lot_perissable_peremption ON lot_perissable(date_peremption)"))
                logger.info("✅ Index créés sur 'lot_perissable'")
            except Exception as e:
                logger.warning(f"⚠️  Erreur création index: {e}")
            
            # ============================================
            # 4. CRÉER LA TABLE AMORTISSEMENT
            # ============================================
            logger.info("\n📊 4. Création de la table 'amortissement'...")
            
            try:
                session.exec(text("""
                    CREATE TABLE IF NOT EXISTS amortissement (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        article_id INTEGER NOT NULL,
                        annee INTEGER NOT NULL,
                        periode VARCHAR(50) NOT NULL,
                        valeur_brute DECIMAL(15, 2) NOT NULL,
                        amortissement_cumule_debut DECIMAL(15, 2) NOT NULL,
                        amortissement_periode DECIMAL(15, 2) NOT NULL,
                        amortissement_cumule_fin DECIMAL(15, 2) NOT NULL,
                        valeur_nette_comptable DECIMAL(15, 2) NOT NULL,
                        taux_applique DECIMAL(5, 2) NOT NULL,
                        methode VARCHAR(20) NOT NULL,
                        base_calcul DECIMAL(15, 2),
                        statut VARCHAR(20) DEFAULT 'CALCULE' NOT NULL,
                        totalement_amorti BOOLEAN DEFAULT FALSE NOT NULL,
                        observations TEXT,
                        calcule_par_user_id INTEGER,
                        date_calcul DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (article_id) REFERENCES article(id),
                        FOREIGN KEY (calcule_par_user_id) REFERENCES user(id),
                        UNIQUE(article_id, annee)
                    )
                """))
                logger.info("✅ Table 'amortissement' créée")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️  Table 'amortissement' existe déjà")
                else:
                    logger.error(f"❌ Erreur création table 'amortissement': {e}")
            
            # Index sur annee pour recherches rapides
            try:
                session.exec(text("CREATE INDEX IF NOT EXISTS idx_amortissement_annee ON amortissement(annee)"))
                session.exec(text("CREATE INDEX IF NOT EXISTS idx_amortissement_article ON amortissement(article_id)"))
                logger.info("✅ Index créés sur 'amortissement'")
            except Exception as e:
                logger.warning(f"⚠️  Erreur création index: {e}")
            
            # ============================================
            # 5. COMMIT DES CHANGEMENTS
            # ============================================
            session.commit()
            logger.info("\n" + "=" * 70)
            logger.info("✅ Migration terminée avec succès !")
            logger.info("=" * 70)
            logger.info("\n📝 Prochaines étapes :")
            logger.info("  1. Identifier les articles périssables existants")
            logger.info("  2. Activer 'est_perissable=True' pour ces articles")
            logger.info("  3. Créer des lots avec dates de péremption")
            logger.info("  4. Identifier les matériels amortissables")
            logger.info("  5. Configurer les données d'amortissement")
            logger.info("  6. Calculer les amortissements annuels")
            logger.info("\n📚 Documentation : STOCK_AVANCES.md")
            
        except Exception as e:
            session.rollback()
            logger.error(f"\n❌ ERREUR LORS DE LA MIGRATION: {e}")
            logger.error("Les changements ont été annulés (rollback)")
            raise


def verifier_migration():
    """Vérifie que les tables et colonnes ont bien été créées"""
    
    logger.info("\n🔍 Vérification de la migration...")
    
    engine = create_engine(settings.database_url)
    
    with Session(engine) as session:
        try:
            # Vérifier les colonnes de la table article
            result = session.exec(text("PRAGMA table_info(article)")).all()
            colonnes_article = [row[1] for row in result]
            
            colonnes_attendues = [
                'est_perissable', 'duree_conservation_jours', 'seuil_alerte_peremption_jours',
                'est_amortissable', 'date_acquisition', 'valeur_acquisition',
                'duree_amortissement_annees', 'taux_amortissement', 'valeur_residuelle',
                'methode_amortissement'
            ]
            
            logger.info("\n📋 Vérification des colonnes 'article':")
            for col in colonnes_attendues:
                if col in colonnes_article:
                    logger.info(f"  ✅ {col}")
                else:
                    logger.error(f"  ❌ {col} - MANQUANTE")
            
            # Vérifier la table lot_perissable
            try:
                session.exec(text("SELECT 1 FROM lot_perissable LIMIT 1"))
                logger.info("\n✅ Table 'lot_perissable' accessible")
            except Exception:
                logger.error("\n❌ Table 'lot_perissable' introuvable")
            
            # Vérifier la table amortissement
            try:
                session.exec(text("SELECT 1 FROM amortissement LIMIT 1"))
                logger.info("✅ Table 'amortissement' accessible")
            except Exception:
                logger.error("❌ Table 'amortissement' introuvable")
            
            logger.info("\n✅ Vérification terminée")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification: {e}")


if __name__ == "__main__":
    try:
        logger.info("🚀 Démarrage de la migration des fonctionnalités avancées du stock")
        migrate_database()
        verifier_migration()
        logger.info("\n🎉 Migration et vérification terminées avec succès !")
    except Exception as e:
        logger.error(f"\n💥 Échec de la migration: {e}")
        sys.exit(1)

