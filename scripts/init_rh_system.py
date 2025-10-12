#!/usr/bin/env python3
"""
Script d'initialisation du système RH
Crée les tables et les données de base (workflow steps)
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel
from app.db.session import engine, get_session
from app.core.logging_config import setup_logging, get_logger
from app.models.rh import (
    Grade, ServiceDept, Agent, HRRequest, WorkflowStep, WorkflowHistory
)
from app.core.rh_workflow_seed import ensure_workflow_steps

# Initialiser le logging
setup_logging()
logger = get_logger(__name__)


def init_rh_tables():
    """
    Crée les tables du système RH si elles n'existent pas
    """
    logger.info("🔨 Création des tables RH...")
    
    # Créer toutes les tables définies dans les modèles
    SQLModel.metadata.create_all(engine)
    
    logger.info("✅ Tables RH créées/vérifiées")


def init_workflow_steps():
    """
    Initialise les étapes de workflow pour tous les types de demandes
    """
    logger.info("🔄 Initialisation des étapes de workflow...")
    
    session = next(get_session())
    try:
        ensure_workflow_steps(session)
        logger.info("✅ Workflow steps initialisés")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation des workflows: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


def init_sample_data():
    """
    Crée des données d'exemple (optionnel)
    """
    logger.info("📊 Création de données d'exemple...")
    
    session = next(get_session())
    try:
        # Créer des grades d'exemple
        from sqlmodel import select
        
        # Vérifier si des grades existent déjà
        existing_grades = session.exec(select(Grade)).first()
        if not existing_grades:
            grades = [
                Grade(code="A1", libelle="Catégorie A - Niveau 1"),
                Grade(code="A2", libelle="Catégorie A - Niveau 2"),
                Grade(code="B1", libelle="Catégorie B - Niveau 1"),
                Grade(code="B2", libelle="Catégorie B - Niveau 2"),
                Grade(code="C1", libelle="Catégorie C - Niveau 1"),
            ]
            for grade in grades:
                session.add(grade)
            logger.info(f"   ✅ {len(grades)} grades créés")
        else:
            logger.info("   ⏭️  Grades déjà existants, skip")
        
        # Créer des services d'exemple
        existing_services = session.exec(select(ServiceDept)).first()
        if not existing_services:
            services = [
                ServiceDept(code="DRH", libelle="Direction des Ressources Humaines"),
                ServiceDept(code="DAF", libelle="Direction Administrative et Financière"),
                ServiceDept(code="DSI", libelle="Direction des Systèmes d'Information"),
                ServiceDept(code="COM", libelle="Direction de la Communication"),
            ]
            for service in services:
                session.add(service)
            logger.info(f"   ✅ {len(services)} services créés")
        else:
            logger.info("   ⏭️  Services déjà existants, skip")
        
        session.commit()
        logger.info("✅ Données d'exemple créées")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des données: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


def main():
    """
    Fonction principale
    """
    print("=" * 60)
    print("🚀 INITIALISATION DU SYSTÈME RH")
    print("=" * 60)
    
    try:
        # 1. Créer les tables
        init_rh_tables()
        
        # 2. Initialiser les workflows
        init_workflow_steps()
        
        # 3. Créer des données d'exemple (optionnel)
        import os
        if os.getenv("CREATE_SAMPLE_DATA", "true").lower() == "true":
            init_sample_data()
        else:
            logger.info("⏭️  Création de données d'exemple désactivée")
        
        print("=" * 60)
        print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS")
        print("=" * 60)
        
    except Exception as e:
        print("=" * 60)
        print("❌ ERREUR LORS DE L'INITIALISATION")
        print("=" * 60)
        logger.error(f"Erreur: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

