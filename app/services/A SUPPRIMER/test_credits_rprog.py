"""
Script de test pour vérifier la récupération des données depuis sigobe_execution
pour le tableau "Exécution financière par action du programme".

Ce script vérifie simplement que les données sont bien récupérées depuis la base de données.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_session
from app.models.budget import SigobeExecution
from sqlmodel import select, or_
from decimal import Decimal
import logging

# Configurer le logging pour voir tous les détails
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def test_sigobe_data_retrieval():
    """Test de récupération des données depuis sigobe_execution"""
    
    logger.info("=" * 80)
    logger.info("🧪 TEST - Vérification des données SIGOBE")
    logger.info("=" * 80)
    
    # Créer une session de base de données
    session = next(get_session())
    
    try:
        # Paramètres de test (modifiables)
        programme = "ADMINISTRATION GENERALE"
        annee = 2024
        periode = None  # None = pas de filtre de période, ou "PREMIER SEMESTRE", "DEUXIEME SEMESTRE"
        
        logger.info(f"📋 Paramètres de test:")
        logger.info(f"   - Programme: {programme}")
        logger.info(f"   - Année: {annee}")
        logger.info(f"   - Période: {periode or 'Aucune (tous les trimestres)'}")
        logger.info("")
        
        # Stratégie de recherche pour SIGOBE (même que dans draw_realisations_credits)
        programme_sigobe_mapping = {
            "ADMINISTRATION GENERALE": "AFFAIRES ADMINISTRATIVES ET FINANCIERES",
            "ADMINISTRATION GÉNÉRALE": "AFFAIRES ADMINISTRATIVES ET FINANCIERES",
        }
        programme_sigobe_name = programme_sigobe_mapping.get(
            programme.upper() if programme else "",
            programme
        )
        
        logger.info(f"🔍 Mapping programme:")
        logger.info(f"   - Programme original: {programme}")
        logger.info(f"   - Programme SIGOBE: {programme_sigobe_name}")
        logger.info("")
        
        # Construire les conditions de recherche pour SIGOBE
        search_conditions_sigobe = []
        if programme:
            search_conditions_sigobe.extend([
                SigobeExecution.programmes.ilike(f"%{programme}%"),
                SigobeExecution.programmes.ilike(f"%{programme_sigobe_name}%"),
            ])
        
        # Construire la requête pour récupérer les données SIGOBE
        query = select(SigobeExecution).where(SigobeExecution.annee == annee)
        
        # Filtrer par programme si fourni (avec mapping robuste)
        if search_conditions_sigobe:
            query = query.where(or_(*search_conditions_sigobe))
        
        # Filtrer par période si fournie (semestre)
        # Si periode est None, on ne filtre pas par trimestre
        if periode and "SEMESTRE" in periode.upper():
            if "PREMIER" in periode.upper() or "1" in periode:
                query = query.where(
                    (SigobeExecution.trimestre == 1) | (SigobeExecution.trimestre == 2)
                )
            elif "DEUXIEME" in periode.upper() or "2" in periode:
                query = query.where(
                    (SigobeExecution.trimestre == 3) | (SigobeExecution.trimestre == 4)
                )
        
        # Exécuter la requête
        logger.info("🔍 Exécution de la requête...")
        sigobe_data = session.exec(query.order_by(
            SigobeExecution.actions,
            SigobeExecution.activites,
            SigobeExecution.type_depense
        )).all()
        
        logger.info(f"📊 Résultats:")
        logger.info(f"   - Nombre de lignes trouvées: {len(sigobe_data)}")
        logger.info("")
        
        if len(sigobe_data) == 0:
            logger.warning("⚠️  Aucune donnée trouvée avec les critères spécifiés!")
            logger.warning("")
            logger.warning("🔍 Diagnostic de la base de données...")
            logger.warning("")
            
            # Vérifier les années disponibles
            logger.info("📅 Années disponibles dans sigobe_execution:")
            years_query = select(SigobeExecution.annee).distinct()
            years = session.exec(years_query).all()
            if years:
                logger.info(f"   - Années: {sorted(set(years))}")
            else:
                logger.warning("   - Aucune donnée dans sigobe_execution!")
            
            # Vérifier les programmes disponibles pour l'année
            logger.info("")
            logger.info(f"📋 Programmes disponibles pour l'année {annee}:")
            programmes_query = select(SigobeExecution.programmes).where(
                SigobeExecution.annee == annee
            ).distinct()
            programmes = session.exec(programmes_query).all()
            programmes_list = [p for p in programmes if p]
            if programmes_list:
                logger.info(f"   - Nombre de programmes: {len(programmes_list)}")
                logger.info("   - Programmes (10 premiers):")
                for prog in sorted(set(programmes_list))[:10]:
                    logger.info(f"     * {prog}")
            else:
                logger.warning(f"   - Aucun programme trouvé pour l'année {annee}")
            
            # Vérifier les trimestres disponibles
            logger.info("")
            logger.info(f"📅 Trimestres disponibles pour l'année {annee}:")
            trimestres_query = select(SigobeExecution.trimestre).where(
                SigobeExecution.annee == annee
            ).distinct()
            trimestres = session.exec(trimestres_query).all()
            trimestres_list = [t for t in trimestres if t is not None]
            if trimestres_list:
                logger.info(f"   - Trimestres: {sorted(set(trimestres_list))}")
            else:
                logger.warning(f"   - Aucun trimestre trouvé pour l'année {annee}")
            
            # Vérifier si des données existent avec des critères plus larges
            logger.info("")
            logger.info("🔍 Recherche avec critères élargis...")
            broad_query = select(SigobeExecution).where(SigobeExecution.annee == annee)
            broad_data = session.exec(broad_query).all()
            logger.info(f"   - Nombre total de lignes pour l'année {annee}: {len(broad_data)}")
            
            if len(broad_data) > 0:
                logger.info("")
                logger.info("📋 Exemples de programmes trouvés (sans filtre programme):")
                sample_programmes = set()
                for sigobe in broad_data[:20]:
                    if sigobe.programmes:
                        sample_programmes.add(sigobe.programmes)
                for prog in sorted(sample_programmes)[:10]:
                    logger.info(f"     * {prog}")
            
            logger.warning("")
            logger.warning("💡 Suggestions:")
            logger.warning(f"   - Vérifiez que l'année {annee} contient des données")
            logger.warning(f"   - Vérifiez que le programme '{programme}' ou '{programme_sigobe_name}' existe")
            logger.warning(f"   - Vérifiez que les trimestres 1 et 2 contiennent des données pour le premier semestre")
            logger.warning("")
            return False
        
        # Afficher un échantillon des données
        logger.info("📋 Échantillon des données (5 premières lignes):")
        logger.info("-" * 80)
        for i, sigobe in enumerate(sigobe_data[:5], 1):
            logger.info(f"Ligne {i}:")
            logger.info(f"   - Programme: {sigobe.programmes}")
            logger.info(f"   - Action: {sigobe.actions}")
            logger.info(f"   - Activité: {sigobe.activites}")
            logger.info(f"   - Type dépense: {sigobe.type_depense}")
            logger.info(f"   - Budget actuel: {sigobe.budget_actuel or 0}")
            logger.info(f"   - Mandats PEC: {sigobe.mandats_pec or 0}")
            logger.info(f"   - Trimestre: {sigobe.trimestre}")
            logger.info("")
        
        # Organiser les données par action et activité (comme dans draw_realisations_credits)
        logger.info("📊 Organisation des données par action et activité...")
        actions_data = {}
        
        for sigobe in sigobe_data:
            action_code = sigobe.actions or "Sans action"
            activite_code = sigobe.activites or ""
            type_depense = sigobe.type_depense or ""
            
            # Normaliser le type de dépense
            type_normalized = ""
            if type_depense:
                type_upper = type_depense.upper()
                if "PERSONNEL" in type_upper:
                    type_normalized = "PERSONNEL"
                elif "BIENS" in type_upper and "SERVICES" in type_upper:
                    type_normalized = "BIENS_ET_SERVICES"
                elif "INVESTISSEMENT" in type_upper:
                    type_normalized = "INVESTISSEMENTS"
            
            if not type_normalized:
                continue
            
            # Initialiser la structure si nécessaire
            if action_code not in actions_data:
                actions_data[action_code] = {
                    "action_libelle": action_code,
                    "activites": {}
                }
            
            if activite_code not in actions_data[action_code]["activites"]:
                actions_data[action_code]["activites"][activite_code] = {
                    "activite_libelle": activite_code,
                    "types_depense": {
                        "PERSONNEL": {"programme": Decimal(0), "realise": Decimal(0)},
                        "BIENS_ET_SERVICES": {"programme": Decimal(0), "realise": Decimal(0)},
                        "INVESTISSEMENTS": {"programme": Decimal(0), "realise": Decimal(0)}
                    }
                }
            
            # Ajouter les montants
            budget_actuel = sigobe.budget_actuel or Decimal(0)
            mandats_pec = sigobe.mandats_pec or Decimal(0)
            
            actions_data[action_code]["activites"][activite_code]["types_depense"][type_normalized]["programme"] += budget_actuel
            actions_data[action_code]["activites"][activite_code]["types_depense"][type_normalized]["realise"] += mandats_pec
        
        logger.info(f"📊 Données organisées:")
        logger.info(f"   - Nombre d'actions: {len(actions_data)}")
        
        total_activites = sum(len(act["activites"]) for act in actions_data.values())
        logger.info(f"   - Nombre total d'activités: {total_activites}")
        logger.info("")
        
        # Afficher un résumé par action
        logger.info("📋 Résumé par action (3 premières):")
        logger.info("-" * 80)
        for i, (action_code, action_data) in enumerate(list(actions_data.items())[:3], 1):
            logger.info(f"Action {i}: {action_code}")
            logger.info(f"   - Nombre d'activités: {len(action_data['activites'])}")
            for activite_code, activite_data in list(action_data["activites"].items())[:2]:
                logger.info(f"   - Activité: {activite_code}")
                for type_dep, montants in activite_data["types_depense"].items():
                    if montants["programme"] > 0 or montants["realise"] > 0:
                        logger.info(f"     * {type_dep}: Programmé={montants['programme']}, Réalisé={montants['realise']}")
            logger.info("")
        
        logger.info("=" * 80)
        logger.info("✅ TEST TERMINÉ AVEC SUCCÈS")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ ERREUR LORS DU TEST: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        # Fermer la session
        if session:
            session.close()
            logger.info("🔒 Session de base de données fermée")

if __name__ == "__main__":
    success = test_sigobe_data_retrieval()
    sys.exit(0 if success else 1)

