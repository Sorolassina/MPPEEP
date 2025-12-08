"""
Script de test pour diagnostiquer la recherche des actions (nb_actions)
dans le rapport RPROG.

Usage:
    python test_nb_actions.py [nom_du_programme]
    
Exemple:
    python test_nb_actions.py "ADMINISTRATION GENERALE"
"""

import sys
import logging
from sqlmodel import Session, select, and_
from app.db import engine
from app.models.personnel import Programme
from app.models.budget import SigobeExecution

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_nb_actions(programme_name: str = None):
    """
    Teste la recherche des actions pour un programme donné.
    
    Args:
        programme_name: Nom du programme à tester. Si None, teste tous les programmes.
    """
    logger.info("=" * 80)
    logger.info("🧪 TEST DE RECHERCHE DES ACTIONS (nb_actions)")
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
        
        # 3. Pour chaque programme, tester la recherche des actions
        for programme_obj in programmes_to_test:
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 TEST POUR LE PROGRAMME: {programme_obj.libelle} (ID: {programme_obj.id})")
            logger.info("=" * 80)
            
            # 3.1. Lister toutes les exécutions SIGOBE pour ce programme
            logger.info("\n📋 ÉTAPE 3.1: Analyse de toutes les exécutions SIGOBE")
            logger.info("-" * 80)
            all_executions_query = select(SigobeExecution).where(
                SigobeExecution.programmes.ilike(f"%{programme_obj.libelle}%")
            )
            all_executions = session.exec(all_executions_query).all()
            logger.info(f"Total de {len(all_executions)} exécutions SIGOBE trouvées pour le programme '{programme_obj.libelle}'")
            
            if all_executions:
                logger.info("\n   Exemples d'exécutions (5 premières):")
                for idx, exec_item in enumerate(all_executions[:5], 1):
                    logger.info(f"   {idx}. Programme: '{exec_item.programmes}' | Action: '{exec_item.actions}' | Année: {exec_item.annee}")
            
            # 3.2. Compter les exécutions avec actions non vides
            logger.info("\n📋 ÉTAPE 3.2: Analyse des actions")
            logger.info("-" * 80)
            executions_with_actions = []
            executions_without_actions = []
            
            for exec_item in all_executions:
                if exec_item.actions and str(exec_item.actions).strip():
                    executions_with_actions.append(exec_item)
                else:
                    executions_without_actions.append(exec_item)
            
            logger.info(f"   - {len(executions_with_actions)} exécutions avec actions non vides")
            logger.info(f"   - {len(executions_without_actions)} exécutions sans actions (NULL ou vide)")
            
            if executions_with_actions:
                logger.info("\n   Exemples d'exécutions avec actions (5 premières):")
                for idx, exec_item in enumerate(executions_with_actions[:5], 1):
                    logger.info(f"   {idx}. Action: '{exec_item.actions}' | Année: {exec_item.annee} | Programme: '{exec_item.programmes}'")
            
            # 3.3. Récupérer les actions distinctes
            logger.info("\n📊 ÉTAPE 3.3: Récupération des actions distinctes")
            logger.info("-" * 80)
            actions_query = select(SigobeExecution.actions).where(
                and_(
                    SigobeExecution.programmes.ilike(f"%{programme_obj.libelle}%"),
                    SigobeExecution.actions.isnot(None),
                    SigobeExecution.actions != ""
                )
            ).distinct()
            actions_list = session.exec(actions_query).all()
            
            logger.info(f"   {len(actions_list)} actions distinctes trouvées (avant filtrage None/vides)")
            
            # Filtrer les valeurs None/vides
            actions_list_filtered = [a for a in actions_list if a and str(a).strip()]
            nb_actions = len(actions_list_filtered)
            
            logger.info(f"   {nb_actions} actions distinctes trouvées (après filtrage)")
            
            if actions_list_filtered:
                logger.info("\n   Liste complète des actions trouvées:")
                for idx, action in enumerate(actions_list_filtered, 1):
                    logger.info(f"   {idx}. '{action}'")
            else:
                logger.warning("\n   ⚠️ Aucune action trouvée après filtrage!")
                
                # Diagnostic supplémentaire
                if all_executions:
                    logger.info("\n   🔍 DIAGNOSTIC: Analyse détaillée des exécutions:")
                    logger.info(f"   - Total exécutions: {len(all_executions)}")
                    logger.info(f"   - Avec actions non-None: {sum(1 for e in all_executions if e.actions is not None)}")
                    logger.info(f"   - Avec actions non-vide (str): {sum(1 for e in all_executions if e.actions and str(e.actions).strip())}")
                    
                    # Vérifier les valeurs exactes du champ actions
                    actions_values = set()
                    for exec_item in all_executions:
                        if exec_item.actions is not None:
                            actions_values.add(str(exec_item.actions))
                    
                    logger.info(f"\n   🔍 Valeurs uniques du champ 'actions' trouvées ({len(actions_values)}):")
                    for val in sorted(actions_values)[:10]:
                        logger.info(f"      - '{val}' (longueur: {len(val)})")
                    if len(actions_values) > 10:
                        logger.info(f"      ... et {len(actions_values) - 10} autres valeurs")
            
            # 3.4. Vérifier si le problème vient du nom du programme
            logger.info("\n📋 ÉTAPE 3.4: Vérification du matching du nom de programme")
            logger.info("-" * 80)
            
            # Lister tous les noms de programmes uniques dans SIGOBE
            all_programmes_sigobe_query = select(SigobeExecution.programmes).where(
                SigobeExecution.programmes.isnot(None)
            ).distinct()
            all_programmes_sigobe = session.exec(all_programmes_sigobe_query).all()
            all_programmes_sigobe_filtered = [p for p in all_programmes_sigobe if p and str(p).strip()]
            
            logger.info(f"   {len(all_programmes_sigobe_filtered)} noms de programmes uniques dans SIGOBE")
            
            # Vérifier si le nom du programme correspond exactement
            matching_programmes = [
                p for p in all_programmes_sigobe_filtered 
                if programme_obj.libelle.lower() in str(p).lower() or str(p).lower() in programme_obj.libelle.lower()
            ]
            
            if matching_programmes:
                logger.info(f"\n   ✅ Programmes SIGOBE correspondant au programme '{programme_obj.libelle}':")
                for prog_sigobe in matching_programmes[:5]:
                    logger.info(f"      - '{prog_sigobe}'")
            else:
                logger.warning(f"\n   ⚠️ Aucun programme SIGOBE ne correspond exactement à '{programme_obj.libelle}'")
                logger.info("\n   🔍 Exemples de noms de programmes dans SIGOBE:")
                for prog_sigobe in all_programmes_sigobe_filtered[:10]:
                    logger.info(f"      - '{prog_sigobe}'")
            
            # 3.5. Résumé
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 RÉSUMÉ POUR LE PROGRAMME: {programme_obj.libelle}")
            logger.info("=" * 80)
            logger.info(f"   Programme ID: {programme_obj.id}")
            logger.info(f"   Nombre d'exécutions SIGOBE: {len(all_executions)}")
            logger.info(f"   Nombre d'actions distinctes: {nb_actions}")
            if nb_actions > 0:
                logger.info(f"   ✅ SUCCÈS: {nb_actions} actions trouvées")
            else:
                logger.warning(f"   ❌ ÉCHEC: Aucune action trouvée")
                if len(all_executions) == 0:
                    logger.warning(f"   💡 RAISON: Aucune exécution SIGOBE trouvée pour ce programme")
                elif len(executions_with_actions) == 0:
                    logger.warning(f"   💡 RAISON: Toutes les exécutions ont le champ 'actions' vide ou NULL")
                else:
                    logger.warning(f"   💡 RAISON: Le filtrage a supprimé toutes les actions")
            logger.info("=" * 80)


if __name__ == "__main__":
    from sqlmodel import or_
    
    # Récupérer le nom du programme depuis les arguments
    programme_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    if programme_name:
        logger.info(f"🎯 Test pour le programme: {programme_name}")
    else:
        logger.info("🎯 Test pour tous les programmes")
    
    try:
        test_nb_actions(programme_name)
    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}", exc_info=True)
        sys.exit(1)

