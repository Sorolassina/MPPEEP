"""
Script de test pour diagnostiquer la recherche des objectifs (nb_objectifs)
dans le rapport RPROG.

Usage:
    python test_nb_objectifs.py [nom_du_programme]
    
Exemple:
    python test_nb_objectifs.py "Programme 1"
"""

import sys
import logging
from sqlmodel import Session, select, and_, or_, func
from app.db import engine
from app.models.personnel import Programme
from app.models.performance import ObjectifPerformance, TypeObjectif

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_nb_objectifs(programme_name: str = None):
    """
    Teste la recherche des objectifs pour un programme donné.
    
    Args:
        programme_name: Nom du programme à tester. Si None, teste tous les programmes.
    """
    logger.info("=" * 80)
    logger.info("🧪 TEST DE RECHERCHE DES OBJECTIFS (nb_objectifs)")
    logger.info("=" * 80)
    
    with Session(engine) as session:
        # 1. Lister tous les programmes disponibles
        logger.info("\n📋 ÉTAPE 1: Liste des programmes disponibles")
        logger.info("-" * 80)
        all_programmes = session.exec(select(Programme)).all()
        logger.info(f"Total de {len(all_programmes)} programme(s) trouvé(s):")
        for prog in all_programmes:
            logger.info(f"   - ID: {prog.id} | Code: {prog.code or 'N/A'} | Libellé: {prog.libelle}")
        
        # 2. Rechercher le programme spécifique
        if programme_name:
            logger.info(f"\n🔍 ÉTAPE 2: Recherche du programme '{programme_name}'")
            logger.info("-" * 80)
            programme_query = select(Programme).where(
                or_(
                    Programme.libelle.ilike(f"%{programme_name}%"),
                    Programme.code.ilike(f"%{programme_name}%")
                )
            )
            programme_obj = session.exec(programme_query).first()
            
            if not programme_obj:
                logger.error(f"❌ Programme '{programme_name}' non trouvé!")
                logger.info("\n💡 Programmes disponibles:")
                for prog in all_programmes:
                    logger.info(f"   - {prog.libelle} (Code: {prog.code or 'N/A'})")
                return
            
            logger.info(f"✅ Programme trouvé: ID={programme_obj.id}, Code={programme_obj.code}, Libellé={programme_obj.libelle}")
            programmes_to_test = [programme_obj]
        else:
            logger.info("\n🔍 ÉTAPE 2: Test de tous les programmes")
            logger.info("-" * 80)
            programmes_to_test = all_programmes
        
        # 3. Pour chaque programme, tester la recherche des objectifs
        for programme_obj in programmes_to_test:
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 TEST POUR LE PROGRAMME: {programme_obj.libelle} (ID: {programme_obj.id})")
            logger.info("=" * 80)
            
            # 3.1. Lister tous les OG dans la base
            logger.info("\n📋 ÉTAPE 3.1: Analyse de tous les objectifs globaux (OG)")
            logger.info("-" * 80)
            all_og_query = select(ObjectifPerformance).where(
                ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value
            )
            all_ogs = session.exec(all_og_query).all()
            logger.info(f"Total de {len(all_ogs)} objectifs globaux (OG) dans la base de données")
            
            # Compter les OG avec/sans programme_id
            ogs_with_programme = [og for og in all_ogs if og.programme_id is not None]
            ogs_without_programme = [og for og in all_ogs if og.programme_id is None]
            logger.info(f"   - {len(ogs_with_programme)} OG avec programme_id défini")
            logger.info(f"   - {len(ogs_without_programme)} OG sans programme_id (NULL)")
            
            # Afficher les OG avec programme_id défini
            if ogs_with_programme:
                logger.info("\n   OG avec programme_id défini:")
                for og in ogs_with_programme[:10]:  # Limiter à 10
                    logger.info(f"      - OG ID {og.id}: '{og.titre or og.code or 'N/A'}' | programme_id={og.programme_id}")
            
            # Afficher quelques OG sans programme_id
            if ogs_without_programme:
                logger.info("\n   Exemples d'OG sans programme_id:")
                for og in ogs_without_programme[:5]:  # Limiter à 5
                    logger.info(f"      - OG ID {og.id}: '{og.titre or og.code or 'N/A'}' | programme_id=NULL")
            
            # 3.2. Rechercher les OG liés au programme
            logger.info(f"\n🔍 ÉTAPE 3.2: Recherche des OG pour le programme ID={programme_obj.id}")
            logger.info("-" * 80)
            og_query = select(ObjectifPerformance.id).where(
                and_(
                    ObjectifPerformance.programme_id == programme_obj.id,
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value
                )
            )
            og_ids = list(session.exec(og_query).all())
            logger.info(f"✅ {len(og_ids)} objectifs globaux (OG) trouvés pour le programme '{programme_obj.libelle}'")
            
            if og_ids:
                logger.info(f"   IDs des OG: {og_ids}")
                
                # Afficher les détails de ces OG
                og_details_query = select(ObjectifPerformance).where(
                    ObjectifPerformance.id.in_(og_ids)
                )
                og_details = session.exec(og_details_query).all()
                logger.info("\n   Détails des OG trouvés:")
                for og_detail in og_details:
                    logger.info(f"      - OG ID {og_detail.id}: '{og_detail.titre or og_detail.code or 'N/A'}'")
                    logger.info(f"        programme_id={og_detail.programme_id} | type_objectif='{og_detail.type_objectif}'")
            else:
                logger.warning(f"⚠️  Aucun OG trouvé avec programme_id={programme_obj.id}")
                
                # Vérifier s'il y a des OG avec d'autres programme_id
                ogs_other_programme = [og for og in all_ogs if og.programme_id is not None and og.programme_id != programme_obj.id]
                if ogs_other_programme:
                    programme_ids_found = set(og.programme_id for og in ogs_other_programme)
                    logger.info(f"\n   💡 {len(ogs_other_programme)} OG trouvés avec d'autres programme_id: {programme_ids_found}")
            
            # 3.3. Compter les OS liés aux OG trouvés
            logger.info(f"\n📊 ÉTAPE 3.3: Comptage des objectifs spécifiques (OS)")
            logger.info("-" * 80)
            
            if og_ids:
                # Compter les OS liés à ces OG
                os_query = select(func.count(ObjectifPerformance.id)).where(
                    and_(
                        ObjectifPerformance.objectif_global_id.in_(og_ids),
                        ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
                    )
                )
                nb_objectifs = session.exec(os_query).first() or 0
                logger.info(f"✅ {nb_objectifs} objectifs spécifiques (OS) trouvés liés à {len(og_ids)} OG")
                
                # Afficher les détails des OS
                os_details_query = select(ObjectifPerformance).where(
                    and_(
                        ObjectifPerformance.objectif_global_id.in_(og_ids),
                        ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
                    )
                )
                os_details = session.exec(os_details_query).all()
                logger.info(f"\n   Détails des {len(os_details)} OS trouvés:")
                for os_detail in os_details:
                    logger.info(f"      - OS ID {os_detail.id}: '{os_detail.titre or os_detail.code or 'N/A'}'")
                    logger.info(f"        objectif_global_id={os_detail.objectif_global_id} | type_objectif='{os_detail.type_objectif}'")
            else:
                nb_objectifs = 0
                logger.warning(f"⚠️  Aucun OS trouvé car aucun OG n'a été trouvé pour ce programme")
                
                # Diagnostic: Vérifier tous les OS et leurs OG parents
                logger.info("\n   🔍 DIAGNOSTIC: Analyse de tous les OS dans la base")
                all_os_query = select(ObjectifPerformance).where(
                    ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
                )
                all_os = session.exec(all_os_query).all()
                logger.info(f"   Total de {len(all_os)} objectifs spécifiques (OS) dans la base")
                
                if all_os:
                    # Récupérer les OG parents de ces OS
                    og_parent_ids = set(os_obj.objectif_global_id for os_obj in all_os if os_obj.objectif_global_id is not None)
                    logger.info(f"   {len(og_parent_ids)} OG uniques sont parents d'au moins un OS")
                    
                    # Vérifier le programme_id de ces OG parents
                    if og_parent_ids:
                        og_parents_query = select(ObjectifPerformance).where(
                            ObjectifPerformance.id.in_(list(og_parent_ids))
                        )
                        og_parents = session.exec(og_parents_query).all()
                        logger.info("\n   Programme_id des OG parents des OS:")
                        programme_ids_of_parents = {}
                        for og_parent in og_parents:
                            prog_id = og_parent.programme_id
                            if prog_id not in programme_ids_of_parents:
                                programme_ids_of_parents[prog_id] = []
                            programme_ids_of_parents[prog_id].append(og_parent.id)
                        
                        for prog_id, og_ids_list in programme_ids_of_parents.items():
                            logger.info(f"      - programme_id={prog_id}: {len(og_ids_list)} OG (IDs: {og_ids_list[:5]}{'...' if len(og_ids_list) > 5 else ''})")
            
            # 3.4. Résumé
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 RÉSUMÉ POUR LE PROGRAMME: {programme_obj.libelle}")
            logger.info("=" * 80)
            logger.info(f"   Programme ID: {programme_obj.id}")
            logger.info(f"   Nombre d'OG trouvés: {len(og_ids)}")
            logger.info(f"   Nombre d'OS trouvés: {nb_objectifs}")
            if og_ids:
                logger.info(f"   ✅ SUCCÈS: {nb_objectifs} objectifs spécifiques trouvés")
            else:
                logger.warning(f"   ❌ ÉCHEC: Aucun objectif global trouvé pour ce programme")
                logger.warning(f"   💡 SOLUTION: Vérifiez que les OG ont bien leur champ 'programme_id' défini à {programme_obj.id}")
            logger.info("=" * 80)


if __name__ == "__main__":
    # Récupérer le nom du programme depuis les arguments
    programme_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    if programme_name:
        logger.info(f"🎯 Test pour le programme: {programme_name}")
    else:
        logger.info("🎯 Test pour tous les programmes")
    
    try:
        test_nb_objectifs(programme_name)
    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}", exc_info=True)
        sys.exit(1)

