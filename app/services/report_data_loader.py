"""
Service centralisé pour charger toutes les données nécessaires aux rapports.

Ce service regroupe toutes les méthodes de chargement de données organisées par domaine :
- data_performance : Données de performance (objectifs, indicateurs, etc.)
- data_sigobe : Données SIGOBE (exécution budgétaire, investissements)
- data_agents : Données des agents (effectifs, catégories, etc.)
- data_programmes : Données des programmes
- data_ministere : Données ministérielles (orientations stratégiques, etc.)

Les générateurs de rapports utilisent ces méthodes pour charger les données de manière centralisée.
"""

import logging
from typing import Any
from sqlmodel import Session, select, and_, or_, func
from decimal import Decimal
from datetime import date

from app.models.performance import (
    ObjectifPerformance,
    IndicateurPerformance,
    TypeObjectif,
    OrientationStrategique,
    ResultatStrategique,
)
from app.models.personnel import Programme, AgentComplet, GradeComplet
from app.models.budget import (
    SigobeExecution,
    SigobeChargement,
    SuiviInvestissement,
    NatureDepense,
)

logger = logging.getLogger(__name__)


class ReportDataLoader:
    """
    Service centralisé pour charger toutes les données nécessaires aux rapports.
    
    Toutes les méthodes retournent des dictionnaires structurés pour faciliter
    leur utilisation dans les générateurs de rapports.
    """
    
    # ========================================================================
    # DATA PERFORMANCE - Données de performance
    # ========================================================================
    
    @staticmethod
    def load_data_performance(
        session: Session,
        annee: int,
        programme_id: int | None = None,
        programme_nom: str | None = None
    ) -> dict[str, Any]:
        """
        Charge les données de performance (objectifs, indicateurs).
        
        Args:
            session: Session de base de données
            annee: Année pour laquelle charger les données
            programme_id: ID du programme (optionnel)
            programme_nom: Nom du programme (optionnel, utilisé si programme_id n'est pas fourni)
        
        Returns:
            Dictionnaire contenant :
            - objectifs_globaux: Liste des objectifs globaux
            - objectifs_specifiques: Liste des objectifs spécifiques
            - indicateurs: Liste des indicateurs
            - objectifs_avec_indicateurs: Liste des objectifs avec leurs indicateurs
            - architecture: Dict avec les compteurs (nb_programmes, nb_og, nb_os, nb_indicateurs, nb_cibles)
            - taux_realisation: Taux de réalisation global
            - nb_cibles_atteintes: Nombre de cibles atteintes
            - realisations: Liste des réalisations par programme
        """
        result = {
            "objectifs_globaux": [],
            "objectifs_specifiques": [],
            "indicateurs": [],
            "objectifs_avec_indicateurs": [],
            "architecture": {
                "nb_programmes": 0,
                "nb_objectifs_globaux": 0,
                "nb_objectifs_specifiques": 0,
                "nb_indicateurs": 0,
                "nb_cibles": 0,
            },
            "taux_realisation": 0.0,
            "nb_cibles_atteintes": 0,
            "realisations": [],
        }
        
        try:
            # Si programme_nom fourni mais pas programme_id, chercher le programme
            if programme_nom and not programme_id:
                programme_db = session.exec(
                    select(Programme).where(
                        or_(
                            Programme.libelle.ilike(f"%{programme_nom}%"),
                            Programme.code.ilike(f"%{programme_nom}%")
                        )
                    )
                ).first()
                if programme_db:
                    programme_id = programme_db.id
                    logger.info(f"📊 Programme '{programme_nom}' trouvé avec ID: {programme_id}")
            
            # 1. Récupérer les objectifs globaux
            og_query = select(ObjectifPerformance.id).where(
                and_(
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value,
                    ObjectifPerformance.resultat_strategique_id.isnot(None)
                )
            )
            if programme_id:
                og_query = og_query.where(ObjectifPerformance.programme_id == programme_id)
            
            og_ids_raw = list(session.exec(og_query).all())
            og_ids = []
            for item in og_ids_raw:
                if isinstance(item, tuple):
                    og_ids.append(item[0])
                elif isinstance(item, (int, str)):
                    og_ids.append(int(item))
                else:
                    og_ids.append(item)
            
            objectifs_globaux = [session.get(ObjectifPerformance, og_id) for og_id in og_ids if session.get(ObjectifPerformance, og_id)]
            result["objectifs_globaux"] = objectifs_globaux
            result["architecture"]["nb_objectifs_globaux"] = len(objectifs_globaux)
            
            # 2. Récupérer les objectifs spécifiques liés aux OG
            os_query = select(ObjectifPerformance).where(
                ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
            )
            
            if og_ids:
                os_query = os_query.where(ObjectifPerformance.objectif_global_id.in_(og_ids))
            
            objectifs_specifiques = list(session.exec(os_query.order_by(ObjectifPerformance.code, ObjectifPerformance.id)).all())
            result["objectifs_specifiques"] = objectifs_specifiques
            result["architecture"]["nb_objectifs_specifiques"] = len(objectifs_specifiques)
            
            # 3. Récupérer les indicateurs (filtrés par année)
            ind_query = select(IndicateurPerformance.id).where(
                and_(
                    IndicateurPerformance.actif == True,
                    IndicateurPerformance.annee == annee
                )
            )
            ind_ids_raw = list(session.exec(ind_query).all())
            ind_ids = []
            for item in ind_ids_raw:
                if isinstance(item, tuple):
                    ind_ids.append(item[0])
                elif isinstance(item, (int, str)):
                    ind_ids.append(int(item))
                else:
                    ind_ids.append(item)
            
            indicateurs = [session.get(IndicateurPerformance, ind_id) for ind_id in ind_ids if session.get(IndicateurPerformance, ind_id)]
            result["indicateurs"] = indicateurs
            result["architecture"]["nb_indicateurs"] = len(indicateurs)
            result["architecture"]["nb_cibles"] = len(indicateurs)
            
            # 4. Compter les cibles atteintes
            cibles_atteintes = 0
            for ind in indicateurs:
                if ind.valeur_actuelle and ind.valeur_cible:
                    try:
                        if float(ind.valeur_actuelle) >= float(ind.valeur_cible):
                            cibles_atteintes += 1
                    except (ValueError, TypeError):
                        pass
            
            result["nb_cibles_atteintes"] = cibles_atteintes
            result["taux_realisation"] = (cibles_atteintes / len(indicateurs) * 100) if len(indicateurs) > 0 else 0.0
            
            # 5. Construire objectifs_avec_indicateurs (pour RPROG)
            objectifs_avec_indicateurs = []
            for os_obj in objectifs_specifiques:
                query_indicateurs = select(IndicateurPerformance).where(
                    and_(
                        IndicateurPerformance.objectif_id == os_obj.id,
                        IndicateurPerformance.actif == True,
                        IndicateurPerformance.annee == annee
                    )
                ).order_by(IndicateurPerformance.id)
                
                indicateurs_os = list(session.exec(query_indicateurs).all())
                
                if indicateurs_os:
                    objectifs_avec_indicateurs.append({
                        "objectif": os_obj,
                        "indicateurs": indicateurs_os
                    })
            
            result["objectifs_avec_indicateurs"] = objectifs_avec_indicateurs
            
            # 6. Construire realisations (pour rapport annuel)
            realisations = []
            if programme_id:
                # Pour un programme spécifique
                prog = session.get(Programme, programme_id)
                if prog:
                    for os_obj in objectifs_specifiques:
                        query_indicateurs = select(IndicateurPerformance).where(
                            and_(
                                IndicateurPerformance.objectif_id == os_obj.id,
                                IndicateurPerformance.actif == True,
                                IndicateurPerformance.annee == annee
                            )
                        )
                        indicateurs_os = list(session.exec(query_indicateurs).all())
                        
                        if indicateurs_os:
                            nb_cibles_os = len(indicateurs_os)
                            nb_cibles_atteintes_os = sum(
                                1 for ind in indicateurs_os
                                if ind.valeur_actuelle is not None and ind.valeur_cible is not None
                                and float(ind.valeur_actuelle) >= float(ind.valeur_cible)
                            )
                            
                            # Construire le nom du programme: "P{code}: {libelle}"
                            # Vérifier si le code contient déjà "P" pour éviter "PP1"
                            prog_code = prog.code or ""
                            if prog_code:
                                # Si le code commence déjà par "P", l'utiliser tel quel
                                if prog_code.startswith("P"):
                                    prog_nom = f"{prog_code}: {prog.libelle}"
                                else:
                                    # Sinon, ajouter "P" devant
                                    prog_nom = f"P{prog_code}: {prog.libelle}"
                            else:
                                prog_nom = prog.libelle
                            
                            # Construire le nom de l'objectif spécifique: "{code} : {titre}"
                            # Le code est déjà sous la forme "OS 1.1", donc on utilise le code tel quel sans ajouter "OS"
                            os_code = os_obj.code or ""
                            os_titre = os_obj.titre or ""
                            if os_code and os_titre:
                                os_nom = f"{os_code} : {os_titre}"
                            elif os_code:
                                os_nom = os_code
                            elif os_titre:
                                os_nom = os_titre
                            else:
                                os_nom = ""
                            
                            realisations.append({
                                "programme": prog_nom,
                                "objectif_specifique": os_nom,
                                "os_code": os_code,  # Stocker le code pour faciliter le tri
                                "nb_cibles": nb_cibles_os,
                                "nb_cibles_atteintes": nb_cibles_atteintes_os,
                            })
            else:
                # Pour tous les programmes
                programmes = session.exec(select(Programme).where(Programme.actif == True).order_by(Programme.code)).all()
                result["architecture"]["nb_programmes"] = len(programmes)
                
                for prog in programmes:
                    # Trouver les OG du programme
                    og_prog_ids_query = select(ObjectifPerformance.id).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value,
                            ObjectifPerformance.programme_id == prog.id
                        )
                    )
                    og_prog_ids_raw = list(session.exec(og_prog_ids_query).all())
                    og_prog_ids = []
                    for item in og_prog_ids_raw:
                        if isinstance(item, tuple):
                            og_prog_ids.append(item[0])
                        elif isinstance(item, (int, str)):
                            og_prog_ids.append(int(item))
                        else:
                            og_prog_ids.append(item)
                    
                    # Trouver les OS liés à ces OG
                    os_prog_query = select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value,
                            ObjectifPerformance.objectif_global_id.in_(og_prog_ids) if og_prog_ids else False
                        )
                    )
                    os_prog_list = list(session.exec(os_prog_query).all())
                    
                    for os_obj in os_prog_list:
                        query_indicateurs = select(IndicateurPerformance).where(
                            and_(
                                IndicateurPerformance.objectif_id == os_obj.id,
                                IndicateurPerformance.actif == True,
                                IndicateurPerformance.annee == annee
                            )
                        )
                        indicateurs_os = list(session.exec(query_indicateurs).all())
                        
                        if indicateurs_os:
                            nb_cibles_os = len(indicateurs_os)
                            nb_cibles_atteintes_os = sum(
                                1 for ind in indicateurs_os
                                if ind.valeur_actuelle is not None and ind.valeur_cible is not None
                                and float(ind.valeur_actuelle) >= float(ind.valeur_cible)
                            )
                            
                            # Construire le nom du programme: "P{code}: {libelle}"
                            # Vérifier si le code contient déjà "P" pour éviter "PP1"
                            prog_code = prog.code or ""
                            if prog_code:
                                # Si le code commence déjà par "P", l'utiliser tel quel
                                if prog_code.startswith("P"):
                                    prog_nom = f"{prog_code}: {prog.libelle}"
                                else:
                                    # Sinon, ajouter "P" devant
                                    prog_nom = f"P{prog_code}: {prog.libelle}"
                            else:
                                prog_nom = prog.libelle
                            
                            # Construire le nom de l'objectif spécifique: "{code} : {titre}"
                            # Le code est déjà sous la forme "OS 1.1", donc on utilise le code tel quel sans ajouter "OS"
                            os_code = os_obj.code or ""
                            os_titre = os_obj.titre or ""
                            if os_code and os_titre:
                                os_nom = f"{os_code} : {os_titre}"
                            elif os_code:
                                os_nom = os_code
                            elif os_titre:
                                os_nom = os_titre
                            else:
                                os_nom = ""
                            
                            realisations.append({
                                "programme": prog_nom,
                                "objectif_specifique": os_nom,
                                "os_code": os_code,  # Stocker le code pour faciliter le tri
                                "nb_cibles": nb_cibles_os,
                                "nb_cibles_atteintes": nb_cibles_atteintes_os,
                            })
            
            # Trier les réalisations : d'abord par programme, puis par code d'objectif spécifique croissant
            def sort_key_realisation(real):
                """Fonction de tri pour les réalisations"""
                # Extraire le programme pour le tri
                programme = real.get("programme", "")
                
                # Utiliser le code OS stocké directement, ou l'extraire depuis objectif_specifique
                os_code_for_sort = real.get("os_code", "")
                if not os_code_for_sort:
                    # Fallback: extraire depuis objectif_specifique si os_code n'est pas disponible
                    os_full = real.get("objectif_specifique", "")
                    if os_full:
                        if " : " in os_full:
                            os_code_for_sort = os_full.split(" : ")[0].strip()
                        elif ":" in os_full:
                            os_code_for_sort = os_full.split(":")[0].strip()
                        else:
                            os_code_for_sort = os_full.strip()
                
                # Normaliser le code pour un tri correct (ex: "OS 1.1" -> ["OS", 1, 1])
                # Convertir en tuple pour un tri naturel
                try:
                    # Séparer "OS" et "1.1"
                    parts = os_code_for_sort.split()
                    if len(parts) >= 2:
                        prefix = parts[0]  # "OS"
                        numbers = parts[1].split(".")  # ["1", "1"]
                        # Convertir en tuple pour tri numérique (ex: (1, 1) pour "1.1")
                        num_tuple = tuple(int(n) if n.isdigit() else 0 for n in numbers)
                        return (programme, prefix, num_tuple)
                    else:
                        return (programme, os_code_for_sort, ())
                except (ValueError, AttributeError):
                    # En cas d'erreur, utiliser le texte brut
                    return (programme, os_code_for_sort, ())
            
            realisations.sort(key=sort_key_realisation)
            
            result["realisations"] = realisations
            
            logger.info(f"✅ Data performance chargée: {len(objectifs_globaux)} OG, {len(objectifs_specifiques)} OS, {len(indicateurs)} indicateurs, {len(realisations)} réalisations")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données de performance: {e}", exc_info=True)
        
        return result
    
    # ========================================================================
    # DATA SIGOBE - Données SIGOBE (exécution budgétaire, investissements)
    # ========================================================================
    
    @staticmethod
    def load_data_sigobe(
        session: Session,
        annee: int,
        programme_nom: str | None = None
    ) -> dict[str, Any]:
        """
        Charge les données SIGOBE (exécution budgétaire, investissements).
        
        Args:
            session: Session de base de données
            annee: Année pour laquelle charger les données
            programme_nom: Nom du programme (optionnel)
        
        Returns:
            Dictionnaire contenant :
            - executions: Liste des exécutions budgétaires
            - investissements: Liste des investissements
            - activites_majeures: Liste des activités majeures
        """
        result = {
            "executions": [],
            "investissements": [],
            "activites_majeures": [],
        }
        
        try:
            # 1. Charger les exécutions budgétaires
            if programme_nom:
                executions_query = select(SigobeExecution).where(
                    and_(
                        SigobeExecution.annee == annee,
                        SigobeExecution.programmes.ilike(f"%{programme_nom}%")
                    )
                )
            else:
                executions_query = select(SigobeExecution).where(
                    SigobeExecution.annee == annee
                )
            
            executions = list(session.exec(executions_query).all())
            result["executions"] = executions
            
            # 2. Charger les investissements
            investissements_query = select(SuiviInvestissement).where(
                SuiviInvestissement.annee == annee
            )
            if programme_nom:
                investissements_query = investissements_query.where(
                    SuiviInvestissement.programme.ilike(f"%{programme_nom}%")
                )
            
            investissements = list(session.exec(investissements_query).all())
            result["investissements"] = investissements
            
            # 3. Charger les activités majeures (si programme fourni)
            if programme_nom:
                activites_query = (
                    select(
                        SigobeExecution.activites,
                        func.sum(SigobeExecution.budget_actuel).label("budget_total"),
                        func.sum(SigobeExecution.mandats_pec).label("execution_total"),
                    )
                    .where(
                        and_(
                            SigobeExecution.annee == annee,
                            SigobeExecution.programmes.ilike(f"%{programme_nom}%"),
                            SigobeExecution.activites.isnot(None),
                            SigobeExecution.activites != ""
                        )
                    )
                    .group_by(SigobeExecution.activites)
                )
                
                activites_db = session.exec(activites_query).all()
                
                seuil_taux = 80.0
                seuil_budget = 10000000  # 10 millions FCFA
                
                activites_filtrees = []
                for activite in activites_db:
                    if activite.activites and activite.budget_total and activite.budget_total > 0:
                        taux = float((activite.execution_total or Decimal(0)) / activite.budget_total * 100)
                        if taux >= seuil_taux or (activite.budget_total and activite.budget_total >= seuil_budget):
                            activites_filtrees.append({
                                "libelle": activite.activites,
                                "taux_execution": taux,
                            })
                
                if activites_filtrees:
                    activites_filtrees.sort(key=lambda x: x["taux_execution"], reverse=True)
                    result["activites_majeures"] = activites_filtrees[:20]
            
            logger.info(f"✅ Data SIGOBE chargée: {len(executions)} exécutions, {len(investissements)} investissements, {len(result['activites_majeures'])} activités majeures")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données SIGOBE: {e}", exc_info=True)
        
        return result
    
    @staticmethod
    def load_data_financement_global(
        session: Session,
        annee: int
    ) -> dict[str, Any]:
        """
        Charge les données de financement global par nature de dépense depuis sigobe_execution.
        
        Args:
            session: Session de base de données
            annee: Année pour laquelle charger les données
        
        Returns:
            Dictionnaire contenant :
            - budget_initial_total: Budget initial total (budget_vote)
            - budget_reel_total: Budget réel total (budget_actuel)
            - evolution_total: Évolution totale (budget_reel - budget_initial)
            - taux_evolution_total: Taux d'évolution totale en %
            - par_nature: Dict avec les données par nature de dépense (P, BS, T, I)
                - libelle: Libellé de la nature
                - budget_initial: Budget initial pour cette nature
                - budget_reel: Budget réel pour cette nature
                - evolution: Évolution pour cette nature
                - taux_evolution: Taux d'évolution pour cette nature en %
        """
        result = {
            "budget_initial_total": 0,
            "budget_reel_total": 0,
            "evolution_total": 0,
            "taux_evolution_total": 0.0,
            "par_nature": {},
        }
        
        try:
            # Récupérer le dernier chargement SIGOBE pour l'année
            dernier_chargement_id_stmt = select(SigobeChargement.id).where(
                SigobeChargement.annee == annee
            ).order_by(SigobeChargement.date_chargement.desc())
            dernier_chargement_id_result = session.exec(dernier_chargement_id_stmt)
            dernier_chargement_id = dernier_chargement_id_result.first()
            
            dernier_chargement = None
            if dernier_chargement_id:
                dernier_chargement = session.get(SigobeChargement, dernier_chargement_id)
            
            financement_par_nature = {}
            budget_initial_total_sigobe = Decimal(0)
            budget_reel_total_sigobe = Decimal(0)
            
            # Charger les natures de dépense pour le mapping
            natures_db = {n.code: n for n in session.exec(select(NatureDepense)).all()}
            
            # Fonction helper pour détecter le code de nature depuis type_depense
            def detect_nature_code(type_depense: str | None, natures_map: dict) -> str | None:
                """Détecte le code de nature (P, BS, T, I) depuis le type_depense de SigobeExecution"""
                if not type_depense:
                    return None
                
                type_dep_upper = type_depense.upper().strip()
                
                # Essayer d'abord de trouver une correspondance exacte dans les codes de NatureDepense
                for code, nature in natures_map.items():
                    if code.upper() == type_dep_upper or nature.libelle.upper() == type_dep_upper:
                        return code
                    if code.upper() in type_dep_upper or nature.libelle.upper() in type_dep_upper:
                        return code
                
                # Mapper les types SIGOBE vers les codes de nature
                if any(keyword in type_dep_upper for keyword in ["PERSONNEL", "P -", "P "]) or type_dep_upper == "P":
                    return "P"
                if any(keyword in type_dep_upper for keyword in ["BIENS", "SERVICES", "BS -", "BS "]) or type_dep_upper == "BS":
                    return "BS"
                if any(keyword in type_dep_upper for keyword in ["TRANSFERT", "T -", "T "]) or type_dep_upper == "T":
                    return "T"
                if any(keyword in type_dep_upper for keyword in ["INVESTISSEMENT", "I -", "I "]) or type_dep_upper == "I":
                    return "I"
                
                return None
            
            if dernier_chargement:
                sigobe_executions = session.exec(
                    select(SigobeExecution)
                    .where(SigobeExecution.chargement_id == dernier_chargement.id)
                ).all()
                
                # Grouper par code de nature de dépense
                depenses_par_code = {}
                
                for exec_sigobe in sigobe_executions:
                    code_nature = detect_nature_code(exec_sigobe.type_depense, natures_db)
                    
                    if not code_nature:
                        continue
                    
                    if code_nature not in depenses_par_code:
                        depenses_par_code[code_nature] = {
                            "budget_vote": Decimal(0),
                            "budget_actuel": Decimal(0),
                        }
                    
                    depenses_par_code[code_nature]["budget_vote"] += Decimal(exec_sigobe.budget_vote or 0)
                    depenses_par_code[code_nature]["budget_actuel"] += Decimal(exec_sigobe.budget_actuel or 0)
                
                # Construire financement_par_nature
                for code_nature, montants in depenses_par_code.items():
                    budget_initial = float(montants["budget_vote"])
                    budget_reel = float(montants["budget_actuel"])
                    
                    budget_initial_total_sigobe += Decimal(montants["budget_vote"])
                    budget_reel_total_sigobe += Decimal(montants["budget_actuel"])
                    
                    nature_obj = natures_db.get(code_nature)
                    libelle = nature_obj.libelle if nature_obj else code_nature
                    
                    financement_par_nature[code_nature] = {
                        "libelle": libelle,
                        "budget_initial": budget_initial,
                        "budget_reel": budget_reel,
                        "evolution": budget_reel - budget_initial,
                        "taux_evolution": ((budget_reel - budget_initial) / budget_initial * 100) if budget_initial > 0 else 0,
                    }
            
            if not financement_par_nature:
                logger.warning(f"⚠️ Aucune donnée SIGOBE trouvée pour l'année {annee}. Les montants budgétaires seront à 0.")
            
            budget_initial_total_final = float(budget_initial_total_sigobe)
            budget_reel_total_final = float(budget_reel_total_sigobe)
            evolution_total_sigobe = budget_reel_total_final - budget_initial_total_final
            taux_evolution_total_sigobe = (evolution_total_sigobe / budget_initial_total_final * 100) if budget_initial_total_final > 0 else 0.0
            
            result = {
                "budget_initial_total": budget_initial_total_final,
                "budget_reel_total": budget_reel_total_final,
                "evolution_total": evolution_total_sigobe,
                "taux_evolution_total": taux_evolution_total_sigobe,
                "par_nature": financement_par_nature,
            }
            
            logger.info(f"✅ Data financement global chargée: budget_initial={budget_initial_total_final}, budget_reel={budget_reel_total_final}, natures={list(financement_par_nature.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données de financement global: {e}", exc_info=True)
        
        return result
    
    # ========================================================================
    # DATA AGENTS - Données des agents (effectifs)
    # ========================================================================
    
    @staticmethod
    def load_data_agents(
        session: Session,
        programme_id: int | None = None,
        direction_id: int | None = None,
        sous_direction_id: int | None = None,
        service_id: int | None = None,
        date_debut: date | None = None,
        date_fin: date | None = None
    ) -> dict[str, Any]:
        """
        Charge les données des agents (effectifs).
        
        Args:
            session: Session de base de données
            programme_id: ID du programme (optionnel)
            direction_id: ID de la direction (optionnel)
            sous_direction_id: ID de la sous-direction (optionnel)
            service_id: ID du service (optionnel)
            date_debut: Date de début pour le filtrage (optionnel)
            date_fin: Date de fin pour le filtrage (optionnel)
        
        Returns:
            Dictionnaire contenant :
            - agents: Liste de tous les agents
            - effectifs_par_categorie: Dict avec le nombre d'agents par catégorie (A, B, C, D, Non fonctionnaires)
            - effectifs_entrees: Dict avec les entrées par catégorie
            - effectifs_sorties: Dict avec les sorties par catégorie
            - total_agents: Nombre total d'agents
        """
        result = {
            "agents": [],
            "effectifs_par_categorie": {"A": 0, "B": 0, "C": 0, "D": 0, "Non fonctionnaires": 0},
            "effectifs_entrees": {"A": 0, "B": 0, "C": 0, "D": 0, "Non fonctionnaires": 0},
            "effectifs_sorties": {"A": 0, "B": 0, "C": 0, "D": 0, "Non fonctionnaires": 0},
            "total_agents": 0,
        }
        
        try:
            # Construire la requête de base
            agents_query = select(AgentComplet).where(AgentComplet.actif == True)
            
            # Ajouter les filtres
            conditions = []
            if programme_id:
                conditions.append(AgentComplet.programme_id == programme_id)
            if direction_id:
                conditions.append(AgentComplet.direction_id == direction_id)
            if sous_direction_id:
                conditions.append(AgentComplet.sous_direction_id == sous_direction_id)
            if service_id:
                conditions.append(AgentComplet.service_id == service_id)
            
            if conditions:
                agents_query = agents_query.where(or_(*conditions))
            
            agents = list(session.exec(agents_query).all())
            result["agents"] = agents
            result["total_agents"] = len(agents)
            
            # Compter par catégorie (extraire la catégorie du code grade, ex: "A1" -> "A")
            for agent in agents:
                if agent.grade_id:
                    grade = session.get(GradeComplet, agent.grade_id)
                    if grade and grade.code:
                        categorie = grade.code[0] if len(grade.code) > 0 else "Non fonctionnaires"
                        if categorie in ["A", "B", "C", "D"]:
                            result["effectifs_par_categorie"][categorie] = result["effectifs_par_categorie"].get(categorie, 0) + 1
                        else:
                            result["effectifs_par_categorie"]["Non fonctionnaires"] = result["effectifs_par_categorie"].get("Non fonctionnaires", 0) + 1
                    else:
                        result["effectifs_par_categorie"]["Non fonctionnaires"] = result["effectifs_par_categorie"].get("Non fonctionnaires", 0) + 1
                else:
                    result["effectifs_par_categorie"]["Non fonctionnaires"] = result["effectifs_par_categorie"].get("Non fonctionnaires", 0) + 1
            
            # TODO: Implémenter le calcul des entrées/sorties si nécessaire
            # Cela nécessite de comparer les dates d'embauche/départ avec date_debut/date_fin
            
            logger.info(f"✅ Data agents chargée: {len(agents)} agents")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données agents: {e}", exc_info=True)
        
        return result
    
    # ========================================================================
    # DATA PROGRAMMES - Données des programmes
    # ========================================================================
    
    @staticmethod
    def load_data_programmes(
        session: Session,
        programme_id: int | None = None,
        programme_nom: str | None = None,
        actif_only: bool = True,
        annee: int | None = None,
        include_sigobe_stats: bool = False
    ) -> dict[str, Any]:
        """
        Charge les données des programmes.
        
        Args:
            session: Session de base de données
            programme_id: ID du programme (optionnel)
            programme_nom: Nom du programme (optionnel)
            actif_only: Si True, ne charge que les programmes actifs
            annee: Année pour calculer les stats SIGOBE (optionnel, requis si include_sigobe_stats=True)
            include_sigobe_stats: Si True, calcule les stats d'actions/activités depuis SIGOBE
        
        Returns:
            Dictionnaire contenant :
            - programmes: Liste des programmes (avec stats si include_sigobe_stats=True)
            - programme: Programme spécifique (si programme_id ou programme_nom fourni)
            - total_programmes: Nombre total de programmes
            - total_actions: Nombre total d'actions (si include_sigobe_stats=True)
            - total_activites: Nombre total d'activités (si include_sigobe_stats=True)
        """
        result = {
            "programmes": [],
            "programme": None,
            "total_programmes": 0,
            "total_actions": 0,
            "total_activites": 0,
        }
        
        try:
            from collections import defaultdict
            
            programmes_list = []
            
            if programme_id:
                programme = session.get(Programme, programme_id)
                if programme:
                    result["programme"] = programme
                    programmes_list = [programme]
            elif programme_nom:
                programme = session.exec(
                    select(Programme).where(
                        and_(
                            or_(
                                Programme.libelle.ilike(f"%{programme_nom}%"),
                                Programme.code.ilike(f"%{programme_nom}%")
                            ),
                            Programme.actif == actif_only if actif_only else True
                        )
                    )
                ).first()
                if programme:
                    result["programme"] = programme
                    programmes_list = [programme]
            else:
                programmes_query = select(Programme)
                if actif_only:
                    programmes_query = programmes_query.where(Programme.actif == True)
                programmes_query = programmes_query.order_by(Programme.code)
                
                programmes_list = list(session.exec(programmes_query).all())
            
            result["total_programmes"] = len(programmes_list)
            
            # Si on doit inclure les stats SIGOBE
            if include_sigobe_stats and annee:
                from app.models.budget import SigobeChargement
                
                # Récupérer le dernier chargement SIGOBE pour l'année
                dernier_chargement_id_stmt = select(SigobeChargement.id).where(
                    SigobeChargement.annee == annee
                ).order_by(SigobeChargement.date_chargement.desc())
                dernier_chargement_id_result = session.exec(dernier_chargement_id_stmt)
                dernier_chargement_id = dernier_chargement_id_result.first()
                
                dernier_chargement = None
                if dernier_chargement_id:
                    dernier_chargement = session.get(SigobeChargement, dernier_chargement_id)
                
                if dernier_chargement:
                    # Charger les données depuis sigobe_execution
                    sigobe_executions_stmt = select(SigobeExecution).where(
                        SigobeExecution.chargement_id == dernier_chargement.id
                    ).where(
                        SigobeExecution.programmes.isnot(None)
                    ).where(
                        SigobeExecution.programmes != ""
                    )
                    sigobe_executions = list(session.exec(sigobe_executions_stmt))
                    
                    if sigobe_executions:
                        # Grouper par programme
                        programmes_dict: dict[str, dict[str, set]] = defaultdict(lambda: {"actions": set(), "activites": set()})
                        
                        for exec_sigobe in sigobe_executions:
                            prog_nom = exec_sigobe.programmes
                            if not prog_nom:
                                continue
                            
                            # Normaliser le nom du programme (enlever espaces en début/fin)
                            prog_nom = prog_nom.strip()
                            
                            if exec_sigobe.actions:
                                programmes_dict[prog_nom]["actions"].add(exec_sigobe.actions)
                            if exec_sigobe.activites:
                                programmes_dict[prog_nom]["activites"].add(exec_sigobe.activites)
                        
                        logger.info(f"📊 Programmes trouvés dans SIGOBE: {list(programmes_dict.keys())}")
                        
                        # Construire la liste des programmes avec leurs comptes
                        # IMPORTANT: Inclure TOUS les programmes actifs, même ceux sans données SIGOBE
                        programmes_with_stats = []
                        
                        # Créer un dictionnaire pour mapper les noms de programmes SIGOBE aux stats
                        sigobe_stats_by_name = {}
                        for prog_nom, prog_data in programmes_dict.items():
                            sigobe_stats_by_name[prog_nom] = {
                                "nb_actions": len(prog_data["actions"]),
                                "nb_activites": len(prog_data["activites"]),
                            }
                        
                        # Réinitialiser les totaux pour les recalculer avec tous les programmes
                        result["total_actions"] = 0
                        result["total_activites"] = 0
                        
                        # Parcourir TOUS les programmes actifs et ajouter leurs stats SIGOBE si disponibles
                        for idx, prog in enumerate(programmes_list, 1):
                            prog_nom = prog.libelle or prog.code or ""
                            if not prog_nom:
                                continue
                            
                            # Chercher les stats SIGOBE pour ce programme (par nom exact ou partiel)
                            stats = sigobe_stats_by_name.get(prog_nom, {"nb_actions": 0, "nb_activites": 0})
                            
                            # Si pas de correspondance exacte, chercher une correspondance partielle
                            if stats["nb_actions"] == 0 and stats["nb_activites"] == 0:
                                for sigobe_nom, sigobe_stats in sigobe_stats_by_name.items():
                                    # Normaliser les noms pour la comparaison (enlever espaces, accents, etc.)
                                    prog_nom_normalized = prog_nom.upper().strip()
                                    sigobe_nom_normalized = sigobe_nom.upper().strip()
                                    
                                    # Correspondance exacte après normalisation
                                    if prog_nom_normalized == sigobe_nom_normalized:
                                        stats = sigobe_stats
                                        logger.debug(f"✅ Correspondance exacte trouvée: '{prog_nom}' = '{sigobe_nom}'")
                                        break
                                    # Correspondance partielle (un nom contient l'autre)
                                    elif prog_nom_normalized in sigobe_nom_normalized or sigobe_nom_normalized in prog_nom_normalized:
                                        stats = sigobe_stats
                                        logger.debug(f"✅ Correspondance partielle trouvée: '{prog_nom}' ≈ '{sigobe_nom}'")
                                        break
                            
                            # Ajouter les stats au total
                            result["total_actions"] += stats["nb_actions"]
                            result["total_activites"] += stats["nb_activites"]
                            
                            programmes_with_stats.append({
                                "numero": idx,
                                "titre": prog_nom,
                                "nb_actions": stats["nb_actions"],
                                "nb_activites": stats["nb_activites"],
                            })
                            
                            logger.debug(f"📊 Programme {idx}: '{prog_nom}' - {stats['nb_actions']} actions, {stats['nb_activites']} activités")
                        
                        result["programmes"] = programmes_with_stats
                        logger.info(f"✅ Data programmes chargée avec stats SIGOBE: {len(programmes_with_stats)} programme(s), {result['total_actions']} actions, {result['total_activites']} activités")
                        logger.info(f"📋 Programmes SIGOBE trouvés: {list(sigobe_stats_by_name.keys())}")
                        logger.info(f"📋 Programmes DB chargés: {[p.libelle or p.code for p in programmes_list]}")
                        return result
            
            # Sinon, retourner juste les programmes
            result["programmes"] = programmes_list
            logger.info(f"✅ Data programmes chargée: {len(programmes_list)} programme(s)")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données programmes: {e}", exc_info=True)
        
        return result
    
    # ========================================================================
    # DATA MINISTERE - Données ministérielles (orientations stratégiques)
    # ========================================================================
    
    @staticmethod
    def load_data_ministere(
        session: Session
    ) -> dict[str, Any]:
        """
        Charge les données ministérielles (orientations stratégiques, résultats stratégiques).
        
        Args:
            session: Session de base de données
        
        Returns:
            Dictionnaire contenant :
            - orientations: Liste des orientations stratégiques
            - resultats: Liste des résultats stratégiques
            - objectifs_globaux: Liste des objectifs globaux liés aux résultats stratégiques
            - orientations_count: Nombre d'orientations
            - resultats_count: Nombre de résultats
            - objectifs_globaux_count: Nombre d'objectifs globaux
        """
        result = {
            "orientations": [],
            "resultats": [],
            "objectifs_globaux": [],
            "orientations_count": 0,
            "resultats_count": 0,
            "objectifs_globaux_count": 0,
        }
        
        try:
            # 1. Charger les orientations stratégiques
            orientations_ids_query = select(OrientationStrategique.id).where(
                OrientationStrategique.actif == True
            ).order_by(OrientationStrategique.ordre.asc(), OrientationStrategique.libelle.asc())
            
            orientations_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(orientations_ids_query).all()]
            orientations = [session.get(OrientationStrategique, oid) for oid in orientations_ids if session.get(OrientationStrategique, oid)]
            
            result["orientations"] = orientations
            result["orientations_count"] = len(orientations)
            
            # 2. Charger les résultats stratégiques
            resultats_ids_query = select(ResultatStrategique.id).where(
                ResultatStrategique.actif == True
            ).order_by(ResultatStrategique.ordre.asc(), ResultatStrategique.libelle.asc())
            
            resultats_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(resultats_ids_query).all()]
            resultats = [session.get(ResultatStrategique, rid) for rid in resultats_ids if session.get(ResultatStrategique, rid)]
            
            result["resultats"] = resultats
            result["resultats_count"] = len(resultats)
            
            # 3. Charger les objectifs globaux liés aux résultats stratégiques
            objectifs_globaux_ids_query = select(ObjectifPerformance.id).where(
                and_(
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value,
                    ObjectifPerformance.resultat_strategique_id.isnot(None)
                )
            )
            
            objectifs_globaux_ids = [row[0] if isinstance(row, tuple) else row for row in session.exec(objectifs_globaux_ids_query).all()]
            objectifs_globaux = [session.get(ObjectifPerformance, ogid) for ogid in objectifs_globaux_ids if session.get(ObjectifPerformance, ogid)]
            
            result["objectifs_globaux"] = objectifs_globaux
            result["objectifs_globaux_count"] = len(objectifs_globaux)
            
            logger.info(f"✅ Data ministère chargée: {len(orientations)} orientations, {len(resultats)} résultats, {len(objectifs_globaux)} objectifs globaux")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données ministère: {e}", exc_info=True)
        
        return result
    
    # ========================================================================
    # MÉTHODE UTILITAIRE - Charger toutes les données en une fois
    # ========================================================================
    
    @staticmethod
    def load_all_data(
        session: Session,
        annee: int,
        programme_id: int | None = None,
        programme_nom: str | None = None,
        direction_id: int | None = None,
        sous_direction_id: int | None = None,
        service_id: int | None = None,
        date_debut: date | None = None,
        date_fin: date | None = None
    ) -> dict[str, Any]:
        """
        Charge toutes les données nécessaires pour un rapport en une seule fois.
        
        Args:
            session: Session de base de données
            annee: Année pour laquelle charger les données
            programme_id: ID du programme (optionnel)
            programme_nom: Nom du programme (optionnel)
            direction_id: ID de la direction (optionnel)
            sous_direction_id: ID de la sous-direction (optionnel)
            service_id: ID du service (optionnel)
            date_debut: Date de début pour le filtrage des agents (optionnel)
            date_fin: Date de fin pour le filtrage des agents (optionnel)
        
        Returns:
            Dictionnaire contenant toutes les données organisées par domaine :
            - data_performance: Données de performance
            - data_sigobe: Données SIGOBE
            - data_agents: Données des agents
            - data_programmes: Données des programmes
            - data_ministere: Données ministérielles
        """
        logger.info(f"🔄 Chargement de toutes les données pour l'année {annee}...")
        
        result = {
            "data_performance": {},
            "data_sigobe": {},
            "data_agents": {},
            "data_programmes": {},
            "data_ministere": {},
        }
        
        try:
            # Charger toutes les données
            result["data_performance"] = ReportDataLoader.load_data_performance(
                session, annee, programme_id, programme_nom
            )
            
            result["data_sigobe"] = ReportDataLoader.load_data_sigobe(
                session, annee, programme_nom
            )
            
            result["data_agents"] = ReportDataLoader.load_data_agents(
                session, programme_id, direction_id, sous_direction_id, service_id, date_debut, date_fin
            )
            
            result["data_programmes"] = ReportDataLoader.load_data_programmes(
                session, programme_id, programme_nom
            )
            
            result["data_ministere"] = ReportDataLoader.load_data_ministere(session)
            
            logger.info(f"✅ Toutes les données chargées avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement de toutes les données: {e}", exc_info=True)
        
        return result

