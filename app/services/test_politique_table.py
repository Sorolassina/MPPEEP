"""
Fichier de test pour diagnostiquer le problème du tableau de politique ministérielle vide.

Ce script teste le chargement des données d'orientations stratégiques depuis la base de données.
"""
import logging
from sqlmodel import Session, select
from app.db.session import engine
from app.services.rapport_annuel_performance_generator_modular import RAPDataLoader, RAPBaseGenerator
from app.models.performance import OrientationStrategique, ResultatStrategique, ObjectifPerformance, TypeObjectif

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_load_orientations():
    """Test le chargement des orientations stratégiques depuis la base de données."""
    logger.info("=" * 80)
    logger.info("TEST: Chargement des orientations stratégiques")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        # Test 1: Charger directement depuis la base
        logger.info("\n1. Test direct depuis la base de données:")
        try:
            orientations = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
                .order_by(OrientationStrategique.ordre.asc(), OrientationStrategique.libelle.asc())
            ).all()
            
            logger.info(f"   ✅ {len(orientations)} orientation(s) stratégique(s) trouvée(s)")
            for i, orient in enumerate(orientations, 1):
                logger.info(f"      {i}. {orient.libelle} (ID: {orient.id}, Ordre: {orient.ordre})")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Test 2: Utiliser la méthode load_performance_hierarchy_from_db
        logger.info("\n2. Test via load_performance_hierarchy_from_db:")
        try:
            hierarchy = RAPDataLoader.load_performance_hierarchy_from_db(session)
            if hierarchy:
                logger.info(f"   ✅ {len(hierarchy)} ligne(s) de tableau trouvée(s)")
                logger.info(f"   ✅ Première ligne: {hierarchy[0] if hierarchy else 'None'}")
                
                # Compter les éléments uniques
                unique_orientations = len(set(entry.get("orientation") for entry in hierarchy if entry.get("orientation")))
                unique_resultats = len(set(entry.get("resultat") for entry in hierarchy if entry.get("resultat")))
                unique_objectifs = len(set(entry.get("objectif") for entry in hierarchy if entry.get("objectif")))
                
                logger.info(f"   ✅ Compteurs: {unique_orientations} orientation(s), {unique_resultats} résultat(s), {unique_objectifs} objectif(s)")
            else:
                logger.warning("   ⚠️ Aucune hiérarchie retournée (None)")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Test 3: Vérifier la structure complète
        logger.info("\n3. Test de la structure complète (Orientation -> Résultat -> Objectif):")
        try:
            orientations = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
            ).all()
            
            for orient in orientations:
                logger.info(f"\n   Orientation: {orient.libelle} (ID: {orient.id})")
                
                resultats = session.exec(
                    select(ResultatStrategique)
                    .where(
                        ResultatStrategique.orientation_id == orient.id,
                        ResultatStrategique.actif == True
                    )
                ).all()
                
                logger.info(f"      → {len(resultats)} résultat(s) stratégique(s)")
                for resultat in resultats:
                    logger.info(f"         - {resultat.libelle} (ID: {resultat.id})")
                    
                    objectifs = session.exec(
                        select(ObjectifPerformance)
                        .where(
                            ObjectifPerformance.resultat_strategique_id == resultat.id,
                            ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL
                        )
                    ).all()
                    
                    logger.info(f"            → {len(objectifs)} objectif(s) global(aux)")
                    for obj in objectifs:
                        logger.info(f"               • {obj.titre} (ID: {obj.id})")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Test 4: Vérifier comment les données sont stockées dans cls.data
        logger.info("\n4. Test du stockage dans cls.data:")
        try:
            # Simuler le chargement comme dans generate_pdf
            db_data = RAPDataLoader.load_system_settings_data(session)
            logger.info(f"   ✅ db_data chargé: {list(db_data.keys())}")
            
            if "partie_ministere" in db_data:
                partie_ministere = db_data["partie_ministere"]
                logger.info(f"   ✅ partie_ministere trouvé: {list(partie_ministere.keys())}")
                
                if "orientations" in partie_ministere:
                    orientations_list = partie_ministere["orientations"]
                    logger.info(f"   ✅ orientations trouvé: {len(orientations_list) if orientations_list else 0} élément(s)")
                    if orientations_list:
                        logger.info(f"   ✅ Premier élément: {orientations_list[0]}")
                        logger.info(f"   ✅ Tous les éléments:")
                        for i, item in enumerate(orientations_list[:5], 1):  # Afficher les 5 premiers
                            logger.info(f"      {i}. {item}")
                else:
                    logger.warning("   ⚠️ 'orientations' non trouvé dans partie_ministere")
            else:
                logger.warning("   ⚠️ 'partie_ministere' non trouvé dans db_data")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Test 5: Vérifier la fusion dans RAPBaseGenerator.data
        logger.info("\n5. Test de la fusion dans RAPBaseGenerator.data:")
        try:
            # Simuler la fusion comme dans generate_pdf
            db_data = RAPDataLoader.load_system_settings_data(session)
            RAPBaseGenerator.data = {**db_data, **{}}
            
            # Simuler la fusion avec budget_data
            from datetime import datetime
            annee = datetime.now().year
            budget_data = RAPDataLoader.load_budget_data(session, annee)
            
            if budget_data:
                if "partie_ministere" not in RAPBaseGenerator.data:
                    RAPBaseGenerator.data["partie_ministere"] = {}
                
                partie_ministere = RAPBaseGenerator.data["partie_ministere"]
                
                # Préserver les orientations
                if "partie_ministere" in db_data and "orientations" in db_data["partie_ministere"]:
                    partie_ministere["orientations"] = db_data["partie_ministere"]["orientations"]
                    logger.info(f"   ✅ Orientations préservées: {len(partie_ministere.get('orientations', []))} élément(s)")
                else:
                    logger.warning("   ⚠️ Pas d'orientations à préserver")
            
            # Vérifier le résultat final
            if "partie_ministere" in RAPBaseGenerator.data:
                partie_ministere_final = RAPBaseGenerator.data["partie_ministere"]
                logger.info(f"   ✅ partie_ministere final: {list(partie_ministere_final.keys())}")
                if "orientations" in partie_ministere_final:
                    logger.info(f"   ✅ orientations final: {len(partie_ministere_final['orientations']) if partie_ministere_final['orientations'] else 0} élément(s)")
                else:
                    logger.warning("   ⚠️ 'orientations' non trouvé dans partie_ministere final")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_load_orientations()

