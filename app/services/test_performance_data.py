"""
Script de test pour diagnostiquer le chargement des données de performance
depuis la base de données pour le tableau "I.2. Politique ministérielle".
"""

import logging
from sqlmodel import Session, select, and_
from app.db.session import engine
from app.services.rapport_annuel_performance_generator_modular import RAPDataLoader, RAPBaseGenerator
from app.models.performance import (
    OrientationStrategique,
    ResultatStrategique,
    ObjectifPerformance,
    TypeObjectif,
    IndicateurPerformance,
)
from app.models.personnel import Programme

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_direct_queries():
    """Test des requêtes directes sur les tables de performance."""
    logger.info("=" * 80)
    logger.info("TEST 1: Requêtes directes sur les tables")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        # Test 1.1: Orientations stratégiques
        logger.info("\n1.1. Test des orientations stratégiques:")
        try:
            orientations = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
                .order_by(OrientationStrategique.ordre.asc(), OrientationStrategique.libelle.asc())
            ).all()
            
            logger.info(f"   ✅ {len(orientations)} orientation(s) stratégique(s) active(s) trouvée(s)")
            for i, orient in enumerate(orientations, 1):
                logger.info(f"      {i}. ID: {orient.id}, Libellé: {orient.libelle}, Ordre: {orient.ordre}")
                logger.info(f"         Type: {type(orient)}, Has 'id': {hasattr(orient, 'id')}")
                if hasattr(orient, 'id'):
                    logger.info(f"         ✅ Accès à orient.id: {orient.id}")
                else:
                    logger.error(f"         ❌ ERREUR: orient.id non accessible")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Test 1.2: Résultats stratégiques
        logger.info("\n1.2. Test des résultats stratégiques:")
        try:
            resultats = session.exec(
                select(ResultatStrategique)
                .where(ResultatStrategique.actif == True)
                .order_by(ResultatStrategique.ordre.asc(), ResultatStrategique.libelle.asc())
            ).all()
            
            logger.info(f"   ✅ {len(resultats)} résultat(s) stratégique(s) actif(s) trouvé(s)")
            for i, resultat in enumerate(resultats, 1):
                logger.info(f"      {i}. ID: {resultat.id}, Libellé: {resultat.libelle}, Orientation ID: {resultat.orientation_id}")
                logger.info(f"         Type: {type(resultat)}, Has 'id': {hasattr(resultat, 'id')}")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Test 1.3: Objectifs de performance (GLOBAUX)
        logger.info("\n1.3. Test des objectifs de performance (GLOBAUX):")
        try:
            objectifs_globaux = session.exec(
                select(ObjectifPerformance)
                .where(ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL)
                .order_by(ObjectifPerformance.titre.asc())
            ).all()
            
            logger.info(f"   ✅ {len(objectifs_globaux)} objectif(s) global(aux) trouvé(s)")
            for i, obj in enumerate(objectifs_globaux, 1):
                logger.info(f"      {i}. ID: {obj.id}, Titre: {obj.titre}, Résultat ID: {obj.resultat_strategique_id}")
                logger.info(f"         Type: {type(obj)}, Has 'id': {hasattr(obj, 'id')}")
        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


def test_hierarchy_structure():
    """Test de la structure hiérarchique complète."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Structure hiérarchique complète")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        try:
            # Récupérer toutes les orientations actives
            orientations = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
                .order_by(OrientationStrategique.ordre.asc(), OrientationStrategique.libelle.asc())
            ).all()
            
            logger.info(f"\n📊 {len(orientations)} orientation(s) stratégique(s) active(s)")
            
            total_resultats = 0
            total_objectifs = 0
            
            for orient in orientations:
                logger.info(f"\n   📌 Orientation: {orient.libelle} (ID: {orient.id})")
                
                # Récupérer les résultats stratégiques pour cette orientation
                resultats = session.exec(
                    select(ResultatStrategique)
                    .where(
                        and_(
                            ResultatStrategique.orientation_id == orient.id,
                            ResultatStrategique.actif == True
                        )
                    )
                    .order_by(ResultatStrategique.ordre.asc(), ResultatStrategique.libelle.asc())
                ).all()
                
                logger.info(f"      → {len(resultats)} résultat(s) stratégique(s)")
                total_resultats += len(resultats)
                
                for resultat in resultats:
                    logger.info(f"         - {resultat.libelle} (ID: {resultat.id})")
                    
                    # Récupérer les objectifs globaux pour ce résultat
                    objectifs_globaux = session.exec(
                        select(ObjectifPerformance)
                        .where(
                            and_(
                                ObjectifPerformance.resultat_strategique_id == resultat.id,
                                ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL
                            )
                        )
                        .order_by(ObjectifPerformance.titre.asc())
                    ).all()
                    
                    logger.info(f"            → {len(objectifs_globaux)} objectif(s) global(aux)")
                    total_objectifs += len(objectifs_globaux)
                    
                    for obj in objectifs_globaux:
                        logger.info(f"               • {obj.titre} (ID: {obj.id})")
            
            logger.info(f"\n📊 RÉSUMÉ:")
            logger.info(f"   - Orientations stratégiques: {len(orientations)}")
            logger.info(f"   - Résultats stratégiques: {total_resultats}")
            logger.info(f"   - Objectifs globaux: {total_objectifs}")
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


def test_load_performance_hierarchy_method():
    """Test de la méthode load_performance_hierarchy_from_db."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Méthode load_performance_hierarchy_from_db")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        try:
            hierarchy = RAPDataLoader.load_performance_hierarchy_from_db(session)
            
            if hierarchy:
                logger.info(f"✅ {len(hierarchy)} ligne(s) de tableau retournée(s)")
                
                # Compter les éléments uniques
                unique_orientations = len(set(entry.get("orientation") for entry in hierarchy if entry.get("orientation")))
                unique_resultats = len(set(entry.get("resultat") for entry in hierarchy if entry.get("resultat")))
                unique_objectifs = len(set(entry.get("objectif") for entry in hierarchy if entry.get("objectif")))
                
                logger.info(f"📊 Compteurs:")
                logger.info(f"   - Orientations uniques: {unique_orientations}")
                logger.info(f"   - Résultats uniques: {unique_resultats}")
                logger.info(f"   - Objectifs uniques: {unique_objectifs}")
                
                logger.info(f"\n📋 Premières lignes du tableau:")
                for i, entry in enumerate(hierarchy[:5], 1):
                    logger.info(f"   {i}. Orientation: '{entry.get('orientation', '')}'")
                    logger.info(f"      Résultat: '{entry.get('resultat', '')}'")
                    logger.info(f"      Objectif: '{entry.get('objectif', '')}'")
            else:
                logger.warning("⚠️ Aucune hiérarchie retournée (None)")
                
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


def test_system_settings_data():
    """Test du chargement des données système."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Chargement des données système")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        try:
            db_data = RAPDataLoader.load_system_settings_data(session)
            
            logger.info(f"✅ db_data chargé: {list(db_data.keys())}")
            
            if "partie_ministere" in db_data:
                partie_ministere = db_data["partie_ministere"]
                logger.info(f"✅ partie_ministere trouvé: {list(partie_ministere.keys())}")
                
                if "orientations" in partie_ministere:
                    orientations_list = partie_ministere["orientations"]
                    logger.info(f"✅ orientations trouvé: {len(orientations_list) if orientations_list else 0} élément(s)")
                    if orientations_list:
                        logger.info(f"✅ Premier élément: {orientations_list[0]}")
                else:
                    logger.warning("⚠️ 'orientations' non trouvé dans partie_ministere")
            else:
                logger.warning("⚠️ 'partie_ministere' non trouvé dans db_data")
                
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


def test_row_vs_sqlmodel():
    """Test pour vérifier si on obtient des Row objects ou des SQLModel objects."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Vérification Row vs SQLModel")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        try:
            # Test avec .all()
            logger.info("\n5.1. Test avec .all():")
            orientations_all = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
            ).all()
            
            if orientations_all:
                orient = orientations_all[0]
                logger.info(f"   Type: {type(orient)}")
                logger.info(f"   Type name: {type(orient).__name__}")
                logger.info(f"   Is instance of OrientationStrategique: {isinstance(orient, OrientationStrategique)}")
                logger.info(f"   Has 'id': {hasattr(orient, 'id')}")
                logger.info(f"   Has '__dict__': {hasattr(orient, '__dict__')}")
                if hasattr(orient, 'id'):
                    logger.info(f"   ✅ orient.id = {orient.id}")
                    logger.info(f"   ✅ orient.libelle = {orient.libelle}")
                else:
                    logger.error(f"   ❌ orient.id non accessible")
                    # Essayer d'accéder comme un Row
                    if hasattr(orient, '__getitem__'):
                        logger.info(f"   ⚠️ C'est un Row object, essai d'accès par index...")
                        try:
                            logger.info(f"   orient[0] = {orient[0]}")
                        except:
                            pass
            
            # Test avec list()
            logger.info("\n5.2. Test avec list():")
            orientations_result = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
            )
            orientations_list = list(orientations_result)
            
            if orientations_list:
                orient = orientations_list[0]
                logger.info(f"   Type: {type(orient)}")
                logger.info(f"   Type name: {type(orient).__name__}")
                logger.info(f"   Is instance of OrientationStrategique: {isinstance(orient, OrientationStrategique)}")
                logger.info(f"   Has 'id': {hasattr(orient, 'id')}")
                if hasattr(orient, 'id'):
                    logger.info(f"   ✅ orient.id = {orient.id}")
                    logger.info(f"   ✅ orient.libelle = {orient.libelle}")
                else:
                    logger.error(f"   ❌ orient.id non accessible")
                    
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


def test_og_os_indicateurs_detailed():
    """Test détaillé des Objectifs Globaux (OG), Objectifs Spécifiques (OS) et Indicateurs."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Données détaillées OG, OS et Indicateurs")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        try:
            # 1. Objectifs Globaux (OG)
            logger.info("\n📌 1. OBJECTIFS GLOBAUX (OG):")
            logger.info("-" * 80)
            
            objectifs_globaux_ids_query = select(ObjectifPerformance.id).where(
                and_(
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL,
                    ObjectifPerformance.resultat_strategique_id.isnot(None)
                )
            ).order_by(ObjectifPerformance.titre.asc())
            objectifs_globaux_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(objectifs_globaux_ids_query).all()]
            
            logger.info(f"   ✅ {len(objectifs_globaux_ids)} objectif(s) global(aux) trouvé(s)")
            
            total_os = 0
            total_indicateurs = 0
            
            for og_id in objectifs_globaux_ids:
                og = session.get(ObjectifPerformance, og_id)
                if og:
                    logger.info(f"\n   🔹 OG ID: {og.id}")
                    logger.info(f"      - Titre: {og.titre}")
                    logger.info(f"      - Code: {og.code or 'N/A'}")
                    logger.info(f"      - Type: {og.type_objectif}")
                    logger.info(f"      - Résultat stratégique ID: {og.resultat_strategique_id}")
                    logger.info(f"      - Programme ID: {og.programme_id}")
                    logger.info(f"      - Date début: {og.date_debut}")
                    logger.info(f"      - Date fin: {og.date_fin}")
                    
                    # Compter les Objectifs Spécifiques (OS) liés à cet OG
                    os_ids_query = select(ObjectifPerformance.id).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE,
                            ObjectifPerformance.objectif_global_id == og.id
                        )
                    )
                    os_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(os_ids_query).all()]
                    total_os += len(os_ids)
                    
                    logger.info(f"      - Nombre d'OS liés: {len(os_ids)}")
                    
                    # Afficher les OS détaillés
                    if os_ids:
                        logger.info(f"      📋 Objectifs Spécifiques (OS) liés:")
                        for os_id in os_ids:
                            os_obj = session.get(ObjectifPerformance, os_id)
                            if os_obj:
                                logger.info(f"         • OS ID: {os_obj.id}")
                                logger.info(f"           - Titre: {os_obj.titre}")
                                logger.info(f"           - Code: {os_obj.code or 'N/A'}")
                                logger.info(f"           - Type: {os_obj.type_objectif}")
                                logger.info(f"           - Programme ID: {os_obj.programme_id}")
                                
                                # Compter les Indicateurs liés à cet OS (actifs uniquement)
                                indicateurs_ids_query = select(IndicateurPerformance.id).where(
                                    and_(
                                        IndicateurPerformance.objectif_id == os_obj.id,
                                        IndicateurPerformance.actif == True
                                    )
                                )
                                indicateurs_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(indicateurs_ids_query).all()]
                                total_indicateurs += len(indicateurs_ids)
                                
                                logger.info(f"           - Nombre d'indicateurs liés: {len(indicateurs_ids)}")
                                
                                # Afficher les Indicateurs détaillés
                                if indicateurs_ids:
                                    logger.info(f"           📊 Indicateurs liés:")
                                    for ind_id in indicateurs_ids:
                                        ind = session.get(IndicateurPerformance, ind_id)
                                        if ind:
                                            logger.info(f"              → Indicateur ID: {ind.id}")
                                            logger.info(f"                 - Nom: {ind.nom}")
                                            logger.info(f"                 - Unité: {ind.unite}")
                                            logger.info(f"                 - Année: {ind.annee}")
                                            logger.info(f"                 - Valeur cible: {ind.valeur_cible}")
                                            logger.info(f"                 - Valeur actuelle: {ind.valeur_actuelle}")
                                            logger.info(f"                 - Catégorie: {ind.categorie}")
                                            logger.info(f"                 - Type: {ind.type_indicateur}")
                                            
                                            # Vérifier si la cible est atteinte
                                            if ind.valeur_cible and ind.valeur_actuelle:
                                                try:
                                                    if float(ind.valeur_actuelle) >= float(ind.valeur_cible):
                                                        logger.info(f"                 ✅ CIBLE ATTEINTE")
                                                    else:
                                                        logger.info(f"                 ⚠️ Cible non atteinte")
                                                except (ValueError, TypeError):
                                                    pass
            
            # 2. Résumé global
            logger.info("\n" + "=" * 80)
            logger.info("📊 RÉSUMÉ GLOBAL:")
            logger.info("=" * 80)
            logger.info(f"   - Nombre total d'Objectifs Globaux (OG): {len(objectifs_globaux_ids)}")
            logger.info(f"   - Nombre total d'Objectifs Spécifiques (OS): {total_os}")
            logger.info(f"   - Nombre total d'Indicateurs: {total_indicateurs}")
            
            # 3. Compter les cibles atteintes
            logger.info("\n📈 2. ANALYSE DES CIBLES:")
            logger.info("-" * 80)
            
            all_indicateurs_ids_query = select(IndicateurPerformance.id).where(IndicateurPerformance.actif == True)
            all_indicateurs_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(all_indicateurs_ids_query).all()]
            
            cibles_atteintes = 0
            cibles_non_atteintes = 0
            cibles_sans_valeurs = 0
            
            for ind_id in all_indicateurs_ids:
                ind = session.get(IndicateurPerformance, ind_id)
                if ind:
                    if ind.valeur_cible and ind.valeur_actuelle:
                        try:
                            if float(ind.valeur_actuelle) >= float(ind.valeur_cible):
                                cibles_atteintes += 1
                            else:
                                cibles_non_atteintes += 1
                        except (ValueError, TypeError):
                            cibles_sans_valeurs += 1
                    else:
                        cibles_sans_valeurs += 1
            
            logger.info(f"   - Cibles atteintes: {cibles_atteintes}")
            logger.info(f"   - Cibles non atteintes: {cibles_non_atteintes}")
            logger.info(f"   - Cibles sans valeurs: {cibles_sans_valeurs}")
            
            if total_indicateurs > 0:
                taux_realisation = (cibles_atteintes / total_indicateurs) * 100
                logger.info(f"   - Taux de réalisation: {taux_realisation:.2f}%")
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


def test_approche_rprog():
    """
    Test avec l'APPROCHE RPROG - exactement comme dans rapport_activite_rprog_generator.py
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 7: APPROCHE RPROG - Récupération des données de performance")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        try:
            # Simuler les paramètres du rapport (comme dans RPROG)
            programme_nom = "ADMINISTRATION GENERALE"  # À adapter selon vos données
            annee = 2026  # Les indicateurs sont définis pour 2026
            
            logger.info(f"\n📋 Paramètres:")
            logger.info(f"   - Programme recherché: {programme_nom}")
            logger.info(f"   - Année: {annee}")
            
            # 1. Trouver le programme par son nom/libellé (comme dans RPROG ligne 5535-5548)
            from sqlmodel import or_
            programme_db = session.exec(
                select(Programme).where(
                    or_(
                        Programme.libelle.ilike(f"%{programme_nom}%"),
                        Programme.code.ilike(f"%{programme_nom}%")
                    )
                )
            ).first()
            
            programme_id = None
            if programme_db:
                programme_id = programme_db.id
                logger.info(f"\n✅ Programme trouvé:")
                logger.info(f"   - ID: {programme_id}")
                logger.info(f"   - Code: {programme_db.code}")
                logger.info(f"   - Libellé: {programme_db.libelle}")
            else:
                logger.warning(f"\n⚠️ Programme '{programme_nom}' non trouvé. Test de tous les programmes actifs...")
                # Si programme non trouvé, tester tous les programmes actifs
                programmes = session.exec(select(Programme).where(Programme.actif == True)).all()
                if programmes:
                    programme_db = programmes[0]
                    programme_id = programme_db.id
                    programme_nom = programme_db.libelle or programme_db.code
                    logger.info(f"   → Utilisation du premier programme: {programme_nom} (ID: {programme_id})")
            
            if not programme_id:
                logger.error("❌ Aucun programme trouvé. Impossible de continuer.")
                return
            
            # 2. Récupérer les objectifs globaux liés au programme (comme dans RPROG ligne 5550-5561)
            query_og = select(ObjectifPerformance.id).where(
                and_(
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value,
                    ObjectifPerformance.programme_id == programme_id
                )
            )
            # Extraire les IDs correctement (peuvent être des tuples ou des entiers)
            og_ids_raw = list(session.exec(query_og).all())
            objectifs_globaux_ids = []
            for item in og_ids_raw:
                if isinstance(item, tuple):
                    objectifs_globaux_ids.append(item[0])
                elif isinstance(item, (int, str)):
                    objectifs_globaux_ids.append(int(item))
                else:
                    objectifs_globaux_ids.append(item)
            
            logger.info(f"\n📊 {len(objectifs_globaux_ids)} objectif(s) global(aux) trouvé(s) pour le programme {programme_nom} (ID: {programme_id})")
            logger.info(f"   IDs: {objectifs_globaux_ids}")
            
            # 3. Récupérer les objectifs spécifiques liés à ces objectifs globaux (comme dans RPROG ligne 5563-5580)
            query_objectifs = select(ObjectifPerformance).where(
                ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
            )
            
            if objectifs_globaux_ids:
                # Filtrer par objectifs globaux du programme
                query_objectifs = query_objectifs.where(
                    ObjectifPerformance.objectif_global_id.in_(objectifs_globaux_ids)
                )
                logger.info(f"   → Filtrage des OS par {len(objectifs_globaux_ids)} objectifs globaux")
            else:
                logger.warning(f"   ⚠️ Aucun objectif global trouvé. Récupération de tous les objectifs spécifiques.")
            
            objectifs = session.exec(query_objectifs.order_by(ObjectifPerformance.code, ObjectifPerformance.id)).all()
            logger.info(f"\n📊 {len(objectifs)} objectif(s) spécifique(s) trouvé(s) pour le programme {programme_nom}")
            
            # Afficher les détails des OS trouvés
            for obj in objectifs:
                logger.info(f"\n   🔹 OS ID={obj.id}: {obj.code or ''} - {obj.titre or 'N/A'}")
                logger.info(f"      - objectif_global_id: {obj.objectif_global_id}")
                logger.info(f"      - programme_id: {obj.programme_id}")
            
            # 4. Récupérer les indicateurs pour chaque objectif (filtrés par année) (comme dans RPROG ligne 5582-5604)
            objectifs_avec_indicateurs = []
            for objectif in objectifs:
                # D'abord, vérifier TOUS les indicateurs (toutes années) pour ce OS
                query_indicateurs_tous = select(IndicateurPerformance).where(
                    and_(
                        IndicateurPerformance.objectif_id == objectif.id,
                        IndicateurPerformance.actif == True
                    )
                ).order_by(IndicateurPerformance.annee.desc(), IndicateurPerformance.id)
                
                indicateurs_tous = session.exec(query_indicateurs_tous).all()
                logger.info(f"\n   📋 OS ID={objectif.id} '{objectif.code} {objectif.titre}':")
                logger.info(f"      → {len(indicateurs_tous)} indicateur(s) actif(s) au total (toutes années)")
                
                if indicateurs_tous:
                    # Afficher les années disponibles
                    annees_disponibles = sorted(set(ind.annee for ind in indicateurs_tous if ind.annee))
                    logger.info(f"      → Années disponibles: {annees_disponibles}")
                    for ind in indicateurs_tous[:3]:  # Afficher les 3 premiers
                        logger.info(f"         • {ind.nom} (année: {ind.annee}, objectif_id: {ind.objectif_id})")
                
                # Maintenant, filtrer par année (comme dans RPROG)
                query_indicateurs = select(IndicateurPerformance).where(
                    and_(
                        IndicateurPerformance.objectif_id == objectif.id,
                        IndicateurPerformance.actif == True,
                        IndicateurPerformance.annee == annee  # Filtrer par année
                    )
                ).order_by(IndicateurPerformance.id)
                
                indicateurs = session.exec(query_indicateurs).all()
                
                if indicateurs:  # Ne garder que les objectifs avec des indicateurs
                    logger.info(f"      ✅ {len(indicateurs)} indicateur(s) pour l'année {annee}")
                    objectifs_avec_indicateurs.append({
                        "objectif": objectif,
                        "indicateurs": indicateurs
                    })
                    
                    # Afficher les détails des indicateurs
                    for ind in indicateurs:
                        logger.info(f"         📊 Indicateur: {ind.nom}")
                        logger.info(f"            - Unité: {ind.unite}")
                        logger.info(f"            - Valeur cible: {ind.valeur_cible}")
                        logger.info(f"            - Valeur actuelle: {ind.valeur_actuelle}")
                        logger.info(f"            - Année: {ind.annee}")
                else:
                    logger.warning(f"      ⚠️ Aucun indicateur pour l'année {annee} (mais {len(indicateurs_tous)} indicateur(s) existent pour d'autres années)")
            
            logger.info(f"\n" + "=" * 80)
            logger.info(f"📊 RÉSUMÉ FINAL (APPROCHE RPROG):")
            logger.info("=" * 80)
            logger.info(f"   - Programme: {programme_nom} (ID: {programme_id})")
            logger.info(f"   - Année: {annee}")
            logger.info(f"   - Objectifs globaux (OG): {len(objectifs_globaux_ids)}")
            logger.info(f"   - Objectifs spécifiques (OS) trouvés: {len(objectifs)}")
            logger.info(f"   - Objectifs avec indicateurs: {len(objectifs_avec_indicateurs)}")
            
            total_indicateurs = sum(len(obj_data["indicateurs"]) for obj_data in objectifs_avec_indicateurs)
            logger.info(f"   - Total indicateurs: {total_indicateurs}")
            
            if len(objectifs_avec_indicateurs) > 0:
                logger.info(f"\n✅ SUCCÈS: Les données seront affichées dans le tableau de performance")
            else:
                logger.warning(f"\n⚠️ ATTENTION: Aucune donnée ne sera affichée dans le tableau de performance")
                logger.warning(f"   Raisons possibles:")
                logger.warning(f"   - Aucun OG lié au programme")
                logger.warning(f"   - Aucun OS lié aux OG")
                logger.warning(f"   - Aucun indicateur actif pour l'année {annee}")
                
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


def test_og_os_relation():
    """
    Test spécifique pour vérifier la relation entre OG et OS par programme.
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 8: Relation OG → OS par programme")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        try:
            # 1. Trouver tous les programmes actifs
            programmes_ids_query = select(Programme.id).where(Programme.actif == True).order_by(Programme.code)
            programmes_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(programmes_ids_query).all()]
            
            logger.info(f"📋 {len(programmes_ids)} programme(s) actif(s) trouvé(s)")
            
            for prog_id in programmes_ids:
                prog = session.get(Programme, prog_id)
                if not prog:
                    continue
                
                prog_num = getattr(prog, 'code', None) or getattr(prog, 'numero', None) or ""
                prog_titre = getattr(prog, 'libelle', None) or ""
                logger.info(f"\n🔹 Programme: {prog_num} - {prog_titre} (ID: {prog_id})")
                
                # 2. Trouver les OG liés à ce programme
                og_ids_query = select(ObjectifPerformance.id).where(
                    and_(
                        ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL,
                        ObjectifPerformance.programme_id == prog_id
                    )
                )
                og_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(og_ids_query).all()]
                
                logger.info(f"   → {len(og_ids)} OG trouvé(s): {og_ids}")
                
                for og_id in og_ids:
                    og = session.get(ObjectifPerformance, og_id)
                    if og:
                        logger.info(f"     • OG ID={og_id}: {og.titre or og.code or 'N/A'}")
                        
                        # 3. Trouver les OS liés à cet OG
                        os_ids_query = select(ObjectifPerformance.id).where(
                            and_(
                                ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE,
                                ObjectifPerformance.objectif_global_id == og_id
                            )
                        )
                        os_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(os_ids_query).all()]
                        
                        logger.info(f"       → {len(os_ids)} OS trouvé(s) via objectif_global_id={og_id}: {os_ids}")
                        
                        if len(os_ids) == 0:
                            # Vérifier s'il y a des OS avec objectif_global_id=NULL ou d'autres valeurs
                            all_os_query = select(ObjectifPerformance).where(
                                ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE
                            )
                            all_os = session.exec(all_os_query).all()
                            logger.info(f"       ⚠️ Vérification: {len(all_os)} OS au total dans la base")
                            for os_temp in all_os[:5]:  # Afficher les 5 premiers
                                logger.info(f"         - OS ID={os_temp.id}: objectif_global_id={os_temp.objectif_global_id}, programme_id={os_temp.programme_id}")
                    
                    # 4. Vérification alternative: OS directement liés au programme
                    os_direct_ids_query = select(ObjectifPerformance.id).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE,
                            ObjectifPerformance.programme_id == prog_id
                        )
                    )
                    os_direct_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(os_direct_ids_query).all()]
                    if len(os_direct_ids) > 0:
                        logger.info(f"       ⚠️ ATTENTION: {len(os_direct_ids)} OS trouvé(s) directement lié(s) au programme (via programme_id): {os_direct_ids}")
        
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())


if __name__ == "__main__":
    logger.info("🔍 DÉBUT DES TESTS DE DIAGNOSTIC")
    logger.info("=" * 80)
    
    # Test principal avec l'approche RPROG
    test_approche_rprog()
    
    # Autres tests (commentés pour se concentrer sur RPROG)
    # test_direct_queries()
    # test_hierarchy_structure()
    # test_load_performance_hierarchy_method()
    # test_system_settings_data()
    # test_row_vs_sqlmodel()
    # test_og_os_indicateurs_detailed()
    # test_og_os_relation()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ FIN DES TESTS DE DIAGNOSTIC")
    logger.info("=" * 80)

