# app/services/performance_service.py
"""
Service de gestion de la performance
Contient toute la logique métier liée à la gestion de la performance
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Session, and_, func, select

from app.core.logging_config import get_logger
from app.models.performance import (
    IndicateurPerformance,
    ObjectifPerformance,
    OrientationStrategique,
    PrioriteObjectif,
    ResultatStrategique,
    StatutObjectif,
    TypeObjectif,
)
from app.models.personnel import Programme

logger = get_logger(__name__)


class PerformanceService:
    """Service de gestion de la performance"""

    # ============================================
    # OBJECTIFS DE PERFORMANCE
    # ============================================

    @staticmethod
    def creer_objectif(session: Session, objectif_data: dict[str, Any], created_by_id: int) -> ObjectifPerformance:
        """Crée un nouvel objectif de performance"""
        try:
            # Calculer la progression initiale
            progression = 0
            if objectif_data.get("valeur_cible") and objectif_data.get("valeur_actuelle"):
                valeur_cible = Decimal(str(objectif_data["valeur_cible"]))
                valeur_actuelle = Decimal(str(objectif_data["valeur_actuelle"]))
                if valeur_cible > 0:
                    progression = (valeur_actuelle / valeur_cible) * 100

            # Déterminer le statut initial
            statut = StatutObjectif.PLANIFIE
            if progression > 0:
                statut = StatutObjectif.EN_COURS

            # Normaliser le type_objectif (convertir en minuscules pour correspondre à l'enum)
            type_obj_str = objectif_data.get("type_objectif", "specifique")
            logger.info(f"🔍 Type objectif reçu: {type_obj_str} (type: {type(type_obj_str)})")
            
            if isinstance(type_obj_str, str):
                type_obj_lower = type_obj_str.lower()
                # Pour "global" et "specifique", utiliser la valeur minuscule
                if type_obj_lower in ["global", "specifique"]:
                    type_obj_str = type_obj_lower
                else:
                    # Pour les autres types (FINANCIER, RH, etc.), garder en majuscules
                    type_obj_str = type_obj_str.upper()
            
            logger.info(f"🔍 Type objectif normalisé: {type_obj_str}")
            
            # Valider avec l'enum mais stocker la string
            # Vérifier que la valeur est valide en utilisant l'enum
            try:
                TypeObjectif(type_obj_str)  # Validation
            except ValueError:
                # Si ce n'est pas une valeur d'enum valide, utiliser la valeur par défaut
                logger.warning(f"⚠️ Type objectif invalide '{type_obj_str}', utilisation de la valeur par défaut")
                type_obj_str = TypeObjectif.SPECIFIQUE.value

            objectif = ObjectifPerformance(
                code=objectif_data.get("code"),
                titre=objectif_data["titre"],
                description=objectif_data.get("description"),
                type_objectif=type_obj_str,  # Stocker directement la string
                priorite=PrioriteObjectif(objectif_data.get("priorite", "NORMALE")),
                date_debut=objectif_data.get("date_debut", date.today()),
                date_fin=objectif_data["date_fin"],
                periode=objectif_data.get("periode", ""),
                valeur_cible=Decimal(str(objectif_data["valeur_cible"])),
                valeur_actuelle=Decimal(str(objectif_data.get("valeur_actuelle", 0))),
                unite=objectif_data.get("unite", ""),
                responsable_id=objectif_data.get("responsable_id"),
                service_responsable=objectif_data.get("service_responsable"),
                resultat_strategique_id=objectif_data.get("resultat_strategique_id"),
                programme_id=objectif_data.get("programme_id"),
                objectif_global_id=objectif_data.get("objectif_global_id"),
                statut=statut,
                progression_pourcentage=progression,
                indicateurs_associes=objectif_data.get("indicateurs_associes"),
                commentaires=objectif_data.get("commentaires"),
                notes_internes=objectif_data.get("notes_internes"),
                created_by_id=created_by_id,
            )

            session.add(objectif)
            session.commit()
            session.refresh(objectif)

            logger.info(f"Objectif créé: {objectif.titre} (ID: {objectif.id})")
            return objectif

        except Exception as e:
            session.rollback()
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Erreur lors de la création de l'objectif: {e}")
            logger.error(f"Détails de l'erreur:\n{error_details}")
            raise

    @staticmethod
    def get_objectif(session: Session, objectif_id: int) -> ObjectifPerformance | None:
        """Récupère un objectif par son ID"""
        try:
            return session.exec(select(ObjectifPerformance).where(ObjectifPerformance.id == objectif_id)).first()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'objectif {objectif_id}: {e}")
            return None

    @staticmethod
    def get_objectifs(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        statut: str | None = None,
        responsable_id: int | None = None,
        type_objectif: str | None = None,
    ) -> list[ObjectifPerformance]:
        """Récupère la liste des objectifs avec filtres"""
        try:
            query = select(ObjectifPerformance)

            # Appliquer les filtres
            conditions = []
            if statut:
                conditions.append(ObjectifPerformance.statut == statut)
            if responsable_id:
                conditions.append(ObjectifPerformance.responsable_id == responsable_id)
            if type_objectif:
                # Normaliser le type_objectif pour la comparaison
                type_obj_normalized = type_objectif.lower() if isinstance(type_objectif, str) else type_objectif
                if type_obj_normalized not in ["global", "specifique"]:
                    type_obj_normalized = type_objectif.upper() if isinstance(type_objectif, str) else type_objectif
                conditions.append(ObjectifPerformance.type_objectif == type_obj_normalized)

            if conditions:
                query = query.where(and_(*conditions))

            # Tri par code (si présent), puis par date de création décroissante
            # Utiliser NULLS LAST pour que les objectifs sans code soient en dernier
            from sqlalchemy import nullslast
            query = query.order_by(
                nullslast(ObjectifPerformance.code.asc()),
                ObjectifPerformance.created_at.desc()
            )

            # Pagination
            query = query.offset(skip).limit(limit)

            return list(session.exec(query))

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des objectifs: {e}")
            return []

    @staticmethod
    def modifier_objectif(
        session: Session, objectif_id: int, objectif_data: dict[str, Any]
    ) -> ObjectifPerformance | None:
        """Modifie un objectif existant"""
        try:
            objectif = session.exec(select(ObjectifPerformance).where(ObjectifPerformance.id == objectif_id)).first()
            if not objectif:
                return None

            # Mettre à jour les champs
            for field, value in objectif_data.items():
                if hasattr(objectif, field):
                    # Pour les champs optionnels (code, objectif_global_id, resultat_strategique_id, programme_id), permettre None
                    if field in ["code", "objectif_global_id", "resultat_strategique_id", "programme_id"]:
                        setattr(objectif, field, value)  # Permettre None pour supprimer/délier
                    elif value is not None:
                        if field in ["valeur_cible", "valeur_actuelle"]:
                            setattr(objectif, field, Decimal(str(value)))
                        elif field == "type_objectif":
                            # Normaliser le type_objectif (convertir en minuscules pour correspondre à l'enum)
                            type_obj_str = value
                            if isinstance(type_obj_str, str):
                                type_obj_str = type_obj_str.lower()
                            # Gérer les cas spéciaux (FINANCIER, RH, etc. restent en majuscules)
                            if type_obj_str not in ["global", "specifique"]:
                                type_obj_str = value.upper() if isinstance(value, str) else value
                            # Valider avec l'enum mais stocker la string
                            try:
                                TypeObjectif(type_obj_str)  # Validation
                                setattr(objectif, field, type_obj_str)  # Stocker directement la string
                            except ValueError:
                                logger.warning(f"⚠️ Type objectif invalide '{type_obj_str}', valeur non modifiée")
                        else:
                            setattr(objectif, field, value)

            # Recalculer la progression
            if objectif.valeur_cible and objectif.valeur_actuelle:
                if objectif.valeur_cible > 0:
                    objectif.progression_pourcentage = (objectif.valeur_actuelle / objectif.valeur_cible) * 100

                    # Mettre à jour le statut selon la progression
                    if objectif.progression_pourcentage >= 100:
                        objectif.statut = StatutObjectif.ATTEINT
                    elif objectif.progression_pourcentage > 0:
                        objectif.statut = StatutObjectif.EN_COURS
                    else:
                        objectif.statut = StatutObjectif.PLANIFIE

            # Vérifier si l'objectif est en retard
            if objectif.date_fin < date.today() and objectif.statut not in [
                StatutObjectif.ATTEINT,
                StatutObjectif.ANNULE,
            ]:
                objectif.statut = StatutObjectif.EN_RETARD

            objectif.updated_at = datetime.now()

            session.add(objectif)
            session.commit()
            session.refresh(objectif)

            logger.info(f"Objectif modifié: {objectif.titre} (ID: {objectif.id})")
            return objectif

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la modification de l'objectif {objectif_id}: {e}")
            return None

    @staticmethod
    def supprimer_objectif(session: Session, objectif_id: int) -> bool:
        """Supprime un objectif"""
        try:
            objectif = session.exec(select(ObjectifPerformance).where(ObjectifPerformance.id == objectif_id)).first()
            if not objectif:
                return False

            session.delete(objectif)
            session.commit()

            logger.info(f"Objectif supprimé: {objectif.titre} (ID: {objectif_id})")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la suppression de l'objectif {objectif_id}: {e}")
            return False

    @staticmethod
    def get_kpis_objectifs(session: Session) -> dict[str, Any]:
        """Récupère les KPIs des objectifs basés sur les valeurs réelles calculées en cascade"""
        try:
            # S'assurer que les valeurs actuelles sont à jour
            PerformanceService.calculer_valeurs_actuelles_cascade(session)
            
            # Total objectifs
            total_objectifs = session.exec(select(func.count(ObjectifPerformance.id))).one() or 0

            # Objectifs par statut
            objectifs_atteints = session.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.ATTEINT)
            ).one() or 0

            objectifs_en_cours = session.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.EN_COURS)
            ).one() or 0

            objectifs_en_retard = session.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.EN_RETARD)
            ).one() or 0

            # Taux de réalisation global basé sur les valeurs actuelles vs valeurs cibles
            objectifs_avec_valeurs = session.exec(
                select(ObjectifPerformance).where(
                    ObjectifPerformance.valeur_cible > 0
                )
            ).all()
            
            taux_realisation = 0
            if objectifs_avec_valeurs:
                taux_realisation_list = []
                for obj in objectifs_avec_valeurs:
                    if obj.valeur_cible and obj.valeur_cible > 0:
                        valeur_actuelle = obj.valeur_actuelle or Decimal('0')
                        taux = float(valeur_actuelle) / float(obj.valeur_cible) * 100
                        taux_realisation_list.append(min(taux, 100))  # Limiter à 100%
                
                if taux_realisation_list:
                    taux_realisation = sum(taux_realisation_list) / len(taux_realisation_list)
            elif total_objectifs > 0:
                # Fallback: utiliser le nombre d'objectifs atteints
                taux_realisation = (objectifs_atteints / total_objectifs) * 100

            # Progression moyenne basée sur les valeurs actuelles
            progression_moyenne = 0
            if objectifs_avec_valeurs:
                progression_list = []
                for obj in objectifs_avec_valeurs:
                    if obj.valeur_cible and obj.valeur_cible > 0:
                        valeur_actuelle = obj.valeur_actuelle or Decimal('0')
                        progression = float(valeur_actuelle) / float(obj.valeur_cible) * 100
                        progression_list.append(min(progression, 100))
                
                if progression_list:
                    progression_moyenne = sum(progression_list) / len(progression_list)
            else:
                # Fallback: utiliser progression_pourcentage
                progression_moyenne = (
                    session.exec(
                        select(func.avg(ObjectifPerformance.progression_pourcentage)).where(
                            ObjectifPerformance.statut.in_([StatutObjectif.EN_COURS, StatutObjectif.ATTEINT])
                        )
                    ).one()
                    or 0
                )

            return {
                "total_objectifs": total_objectifs,
                "objectifs_atteints": objectifs_atteints,
                "objectifs_en_cours": objectifs_en_cours,
                "objectifs_en_retard": objectifs_en_retard,
                "taux_realisation": round(float(taux_realisation), 1),
                "progression_moyenne": round(float(progression_moyenne), 1),
            }

        except Exception as e:
            logger.error(f"Erreur lors du calcul des KPIs objectifs: {e}")
            return {
                "total_objectifs": 0,
                "objectifs_atteints": 0,
                "objectifs_en_cours": 0,
                "objectifs_en_retard": 0,
                "taux_realisation": 0,
                "progression_moyenne": 0,
            }

    # ============================================
    # INDICATEURS DE PERFORMANCE
    # ============================================

    @staticmethod
    def creer_indicateur(
        session: Session, indicateur_data: dict[str, Any], created_by_id: int
    ) -> IndicateurPerformance:
        """Crée un nouvel indicateur de performance"""
        try:
            from datetime import datetime
            
            logger.info(f"🔍 [creer_indicateur] Données reçues: {list(indicateur_data.keys())}")
            logger.info(f"🔍 [creer_indicateur] cible_N_plus_1 = {indicateur_data.get('cible_N_plus_1')}")
            logger.info(f"🔍 [creer_indicateur] cible_N_plus_2 = {indicateur_data.get('cible_N_plus_2')}")
            logger.info(f"🔍 [creer_indicateur] annee = {indicateur_data.get('annee')}")
            
            # Si annee n'est pas fournie, utiliser l'année actuelle par défaut
            annee_value = indicateur_data.get("annee")
            if annee_value is None:
                annee_value = datetime.now().year
                logger.info(f"🔍 [creer_indicateur] annee non fournie, utilisation de l'année actuelle: {annee_value}")
            
            indicateur = IndicateurPerformance(
                objectif_id=indicateur_data["objectif_id"],
                nom=indicateur_data["nom"],
                description=indicateur_data.get("description"),
                formule_calcul=indicateur_data.get("formule_calcul"),
                categorie=indicateur_data.get("categorie", "OPERATIONNEL"),
                type_indicateur=indicateur_data.get("type_indicateur", "Nombre"),
                annee=annee_value,
                valeur_cible=indicateur_data.get("valeur_cible"),
                valeur_actuelle=indicateur_data.get("valeur_actuelle", Decimal(0)),
                unite=indicateur_data.get("unite_mesure", ""),
                seuil_alerte_bas=indicateur_data.get("seuil_alerte_min"),
                seuil_alerte_haut=indicateur_data.get("seuil_alerte_max"),
                frequence_maj=indicateur_data.get("frequence_mesure", "MENSUEL"),
                responsable_id=indicateur_data.get("responsable_id"),
                source_donnees=indicateur_data.get("source_donnees"),
                methode=indicateur_data.get("methode"),
                mode_collecte_donnees=indicateur_data.get("mode_collecte_donnees"),
                derniere_valeur_connue=indicateur_data.get("derniere_valeur_connue"),
                sens_appreciation=indicateur_data.get("sens_appreciation", "haut"),
                doc_justif=indicateur_data.get("doc_justif"),
                cible_N_plus_1=indicateur_data.get("cible_N_plus_1"),
                cible_N_plus_2=indicateur_data.get("cible_N_plus_2"),
                actif=indicateur_data.get("actif", True),
                created_by_id=created_by_id,
            )
            
            logger.info(f"🔍 [creer_indicateur] Objet IndicateurPerformance créé")
            logger.info(f"🔍 [creer_indicateur] indicateur.cible_N_plus_1 = {indicateur.cible_N_plus_1}")
            logger.info(f"🔍 [creer_indicateur] indicateur.cible_N_plus_2 = {indicateur.cible_N_plus_2}")

            logger.info(f"🔍 [creer_indicateur] Ajout de l'indicateur à la session...")
            session.add(indicateur)
            logger.info(f"🔍 [creer_indicateur] Commit de la session...")
            session.commit()
            logger.info(f"🔍 [creer_indicateur] Commit réussi, refresh de l'objet...")
            session.refresh(indicateur)

            logger.info(f"✅ Indicateur créé: {indicateur.nom} (ID: {indicateur.id})")
            
            # Recalculer les valeurs actuelles en cascade
            try:
                PerformanceService.calculer_valeurs_actuelles_cascade(session, indicateur_id=indicateur.id)
            except Exception as e:
                logger.warning(f"Erreur lors du calcul en cascade après création de l'indicateur {indicateur.id}: {e}")
            
            return indicateur

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erreur lors de la création de l'indicateur: {e}")
            logger.error(f"❌ Type d'erreur: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Traceback complet:\n{traceback.format_exc()}")
            raise

    @staticmethod
    def get_indicateurs(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        categorie: str | None = None,
        responsable_id: int | None = None,
        frequence_mesure: str | None = None,
        actif_only: bool = True,
    ) -> list[IndicateurPerformance]:
        """Récupère la liste des indicateurs avec filtres"""
        try:
            query = select(IndicateurPerformance)

            # Appliquer les filtres
            conditions = []
            if categorie:
                conditions.append(IndicateurPerformance.categorie == categorie)
            if responsable_id:
                conditions.append(IndicateurPerformance.responsable_id == responsable_id)
            if frequence_mesure:
                conditions.append(IndicateurPerformance.frequence_maj == frequence_mesure)
            if actif_only:
                conditions.append(IndicateurPerformance.actif)

            if conditions:
                query = query.where(and_(*conditions))

            # Tri par nom
            query = query.order_by(IndicateurPerformance.nom)

            # Pagination
            query = query.offset(skip).limit(limit)

            return list(session.exec(query))

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des indicateurs: {e}")
            return []

    @staticmethod
    def get_indicateur(session: Session, indicateur_id: int) -> IndicateurPerformance | None:
        """Récupère un indicateur par son ID"""
        try:
            return session.exec(select(IndicateurPerformance).where(IndicateurPerformance.id == indicateur_id)).first()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'indicateur {indicateur_id}: {e}")
            return None

    @staticmethod
    def modifier_indicateur(
        session: Session, indicateur_id: int, indicateur_data: dict[str, Any]
    ) -> IndicateurPerformance | None:
        """Modifie un indicateur existant"""
        try:
            indicateur = session.exec(
                select(IndicateurPerformance).where(IndicateurPerformance.id == indicateur_id)
            ).first()
            if not indicateur:
                return None

            # Mapper les noms de champs du formulaire vers le modèle
            field_mapping = {
                "unite_mesure": "unite",
                "seuil_alerte_min": "seuil_alerte_bas",
                "seuil_alerte_max": "seuil_alerte_haut",
                "frequence_mesure": "frequence_maj",
            }

            # Mettre à jour les champs
            for field, value in indicateur_data.items():
                # Mapper le nom du champ si nécessaire
                model_field = field_mapping.get(field, field)

                # Permettre la mise à jour même si value est None (pour doc_justif notamment)
                if hasattr(indicateur, model_field):
                    if value is not None or field == "doc_justif":
                        setattr(indicateur, model_field, value)

            indicateur.updated_at = datetime.now()

            session.add(indicateur)
            session.commit()
            session.refresh(indicateur)

            logger.info(f"Indicateur modifié: {indicateur.nom} (ID: {indicateur.id})")
            
            # Recalculer les valeurs actuelles en cascade
            try:
                PerformanceService.calculer_valeurs_actuelles_cascade(session, indicateur_id=indicateur_id)
            except Exception as e:
                logger.warning(f"Erreur lors du calcul en cascade après modification de l'indicateur {indicateur_id}: {e}")
            
            return indicateur

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la modification de l'indicateur {indicateur_id}: {e}")
            return None

    @staticmethod
    def supprimer_indicateur(session: Session, indicateur_id: int) -> bool:
        """Supprime un indicateur"""
        try:
            indicateur = session.exec(
                select(IndicateurPerformance).where(IndicateurPerformance.id == indicateur_id)
            ).first()
            if not indicateur:
                return False

            session.delete(indicateur)
            session.commit()

            logger.info(f"Indicateur supprimé: {indicateur.nom} (ID: {indicateur_id})")
            
            # Recalculer les valeurs actuelles en cascade après suppression
            try:
                PerformanceService.calculer_valeurs_actuelles_cascade(session)
            except Exception as e:
                logger.warning(f"Erreur lors du calcul en cascade après suppression de l'indicateur {indicateur_id}: {e}")
            
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la suppression de l'indicateur {indicateur_id}: {e}")
            return False

    # ============================================
    # ORIENTATIONS STRATÉGIQUES
    # ============================================

    @staticmethod
    def creer_orientation_strategique(
        session: Session, orientation_data: dict[str, Any], created_by_id: int
    ) -> OrientationStrategique:
        """Crée une nouvelle orientation stratégique"""
        try:
            orientation = OrientationStrategique(
                libelle=orientation_data["libelle"],
                description=orientation_data.get("description"),
                ordre=orientation_data.get("ordre"),
                actif=orientation_data.get("actif", True),
                created_by_id=created_by_id,
            )

            session.add(orientation)
            session.commit()
            session.refresh(orientation)

            logger.info(f"Orientation stratégique créée: {orientation.libelle} (ID: {orientation.id})")
            return orientation

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la création de l'orientation stratégique: {e}")
            raise

    @staticmethod
    def get_orientation_strategique(session: Session, orientation_id: int) -> OrientationStrategique | None:
        """Récupère une orientation stratégique par son ID"""
        try:
            return session.exec(
                select(OrientationStrategique).where(OrientationStrategique.id == orientation_id)
            ).first()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'orientation stratégique {orientation_id}: {e}")
            return None

    @staticmethod
    def get_orientations_strategiques(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        actif: bool | None = None,
    ) -> list[OrientationStrategique]:
        """Récupère la liste des orientations stratégiques avec filtres"""
        try:
            query = select(OrientationStrategique)

            if actif is not None:
                query = query.where(OrientationStrategique.actif == actif)

            query = query.order_by(OrientationStrategique.ordre.asc(), OrientationStrategique.libelle.asc())
            query = query.offset(skip).limit(limit)

            return list(session.exec(query))

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des orientations stratégiques: {e}")
            return []

    @staticmethod
    def modifier_orientation_strategique(
        session: Session, orientation_id: int, orientation_data: dict[str, Any]
    ) -> OrientationStrategique | None:
        """Modifie une orientation stratégique existante"""
        try:
            orientation = session.exec(
                select(OrientationStrategique).where(OrientationStrategique.id == orientation_id)
            ).first()
            if not orientation:
                return None

            for field, value in orientation_data.items():
                if hasattr(orientation, field) and value is not None:
                    setattr(orientation, field, value)

            orientation.updated_at = datetime.now()
            session.add(orientation)
            session.commit()
            session.refresh(orientation)

            logger.info(f"Orientation stratégique modifiée: {orientation.libelle} (ID: {orientation_id})")
            return orientation

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la modification de l'orientation stratégique {orientation_id}: {e}")
            return None

    @staticmethod
    def supprimer_orientation_strategique(session: Session, orientation_id: int) -> bool:
        """Supprime une orientation stratégique"""
        try:
            orientation = session.exec(
                select(OrientationStrategique).where(OrientationStrategique.id == orientation_id)
            ).first()
            if not orientation:
                return False

            session.delete(orientation)
            session.commit()

            logger.info(f"Orientation stratégique supprimée: {orientation.libelle} (ID: {orientation_id})")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la suppression de l'orientation stratégique {orientation_id}: {e}")
            return False

    # ============================================
    # RÉSULTATS STRATÉGIQUES
    # ============================================

    @staticmethod
    def creer_resultat_strategique(
        session: Session, resultat_data: dict[str, Any], created_by_id: int
    ) -> ResultatStrategique:
        """Crée un nouveau résultat stratégique"""
        try:
            resultat = ResultatStrategique(
                orientation_id=resultat_data["orientation_id"],
                libelle=resultat_data["libelle"],
                description=resultat_data.get("description"),
                ordre=resultat_data.get("ordre"),
                actif=resultat_data.get("actif", True),
                created_by_id=created_by_id,
            )

            session.add(resultat)
            session.commit()
            session.refresh(resultat)

            logger.info(f"Résultat stratégique créé: {resultat.libelle} (ID: {resultat.id})")
            return resultat

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la création du résultat stratégique: {e}")
            raise

    @staticmethod
    def get_resultat_strategique(session: Session, resultat_id: int) -> ResultatStrategique | None:
        """Récupère un résultat stratégique par son ID"""
        try:
            return session.exec(
                select(ResultatStrategique).where(ResultatStrategique.id == resultat_id)
            ).first()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résultat stratégique {resultat_id}: {e}")
            return None

    @staticmethod
    def get_resultats_strategiques(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        orientation_id: int | None = None,
        actif: bool | None = None,
    ) -> list[ResultatStrategique]:
        """Récupère la liste des résultats stratégiques avec filtres"""
        try:
            query = select(ResultatStrategique)

            conditions = []
            if orientation_id is not None:
                conditions.append(ResultatStrategique.orientation_id == orientation_id)
            if actif is not None:
                conditions.append(ResultatStrategique.actif == actif)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(ResultatStrategique.ordre.asc(), ResultatStrategique.libelle.asc())
            query = query.offset(skip).limit(limit)

            return list(session.exec(query))

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des résultats stratégiques: {e}")
            return []

    @staticmethod
    def modifier_resultat_strategique(
        session: Session, resultat_id: int, resultat_data: dict[str, Any]
    ) -> ResultatStrategique | None:
        """Modifie un résultat stratégique existant"""
        try:
            resultat = session.exec(
                select(ResultatStrategique).where(ResultatStrategique.id == resultat_id)
            ).first()
            if not resultat:
                return None

            for field, value in resultat_data.items():
                if hasattr(resultat, field) and value is not None:
                    setattr(resultat, field, value)

            resultat.updated_at = datetime.now()
            session.add(resultat)
            session.commit()
            session.refresh(resultat)

            logger.info(f"Résultat stratégique modifié: {resultat.libelle} (ID: {resultat_id})")
            return resultat

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la modification du résultat stratégique {resultat_id}: {e}")
            return None

    @staticmethod
    def supprimer_resultat_strategique(session: Session, resultat_id: int) -> bool:
        """Supprime un résultat stratégique"""
        try:
            resultat = session.exec(
                select(ResultatStrategique).where(ResultatStrategique.id == resultat_id)
            ).first()
            if not resultat:
                return False

            session.delete(resultat)
            session.commit()

            logger.info(f"Résultat stratégique supprimé: {resultat.libelle} (ID: {resultat_id})")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la suppression du résultat stratégique {resultat_id}: {e}")
            return False

    # ============================================
    # CALCUL DES VALEURS ACTUELLES EN CASCADE
    # ============================================

    @staticmethod
    def calculer_valeurs_actuelles_cascade(session: Session, indicateur_id: int | None = None) -> None:
        """
        Calcule les valeurs actuelles en cascade depuis les indicateurs jusqu'aux programmes.
        
        Hiérarchie :
        - OS = moyenne des valeurs actuelles des indicateurs associés
        - OG = moyenne des valeurs actuelles des OS associés
        - RS = moyenne des valeurs actuelles des OG associés
        - Orientation Stratégique = moyenne des valeurs actuelles des RS associés
        - Programme = moyenne des valeurs actuelles des orientations stratégiques associées
        
        Args:
            session: Session de base de données
            indicateur_id: ID de l'indicateur modifié (optionnel, pour optimiser le recalcul)
        """
        try:
            # 1. Calculer les valeurs des OS (Objectifs Spécifiques) = moyenne des indicateurs
            logger.info("🔄 Calcul des valeurs actuelles des OS (moyenne des indicateurs)...")
            os_list = session.exec(
                select(ObjectifPerformance).where(
                    ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
                )
            ).all()
            
            for os in os_list:
                # Récupérer tous les indicateurs associés à cet OS
                indicateurs = session.exec(
                    select(IndicateurPerformance).where(
                        IndicateurPerformance.objectif_id == os.id
                    )
                ).all()
                
                if indicateurs:
                    # Calculer la moyenne des valeurs actuelles normalisées (en tenant compte du sens_appreciation)
                    valeurs_normalisees = []
                    for ind in indicateurs:
                        if ind.valeur_actuelle is not None and ind.valeur_cible is not None and ind.valeur_cible > 0:
                            sens = getattr(ind, "sens_appreciation", "haut") or "haut"
                            
                            if sens == "haut":
                                # Pour "haut" : taux = (valeur_actuelle / valeur_cible) * 100
                                taux = float(ind.valeur_actuelle) / float(ind.valeur_cible) * 100
                            else:  # sens == "bas"
                                # Pour "bas" : taux = (valeur_cible / valeur_actuelle) * 100
                                # Si valeur_actuelle = 0, on considère comme 0% de réalisation
                                if ind.valeur_actuelle > 0:
                                    taux = float(ind.valeur_cible) / float(ind.valeur_actuelle) * 100
                                else:
                                    taux = 0
                            
                            # Normaliser le taux (limiter à 100% pour éviter les valeurs aberrantes)
                            taux_normalise = min(max(taux, 0), 100)
                            valeurs_normalisees.append(taux_normalise)
                    
                    if valeurs_normalisees:
                        # Calculer la moyenne des taux normalisés, puis convertir en valeur absolue
                        # en utilisant la valeur_cible de l'OS comme référence
                        moyenne_taux = sum(valeurs_normalisees) / len(valeurs_normalisees)
                        # Convertir le taux moyen en valeur absolue basée sur la valeur_cible de l'OS
                        if os.valeur_cible and os.valeur_cible > 0:
                            os.valeur_actuelle = Decimal(str(round(float(os.valeur_cible) * moyenne_taux / 100, 2)))
                        else:
                            # Si pas de valeur_cible pour l'OS, utiliser la moyenne des valeurs brutes
                            valeurs_brutes = [ind.valeur_actuelle for ind in indicateurs if ind.valeur_actuelle is not None]
                            if valeurs_brutes:
                                os.valeur_actuelle = Decimal(str(round(sum(valeurs_brutes) / len(valeurs_brutes), 2)))
                            else:
                                os.valeur_actuelle = Decimal('0')
                        logger.debug(f"  OS {os.code or os.id}: {os.valeur_actuelle} (moyenne normalisée de {len(valeurs_normalisees)} indicateurs, taux moyen: {moyenne_taux:.1f}%)")
                    else:
                        os.valeur_actuelle = Decimal('0')
                else:
                    os.valeur_actuelle = Decimal('0')
                session.add(os)
            
            session.commit()
            logger.info(f"✅ {len(os_list)} OS mis à jour")
            
            # 2. Calculer les valeurs des OG (Objectifs Globaux) = moyenne des OS associés
            logger.info("🔄 Calcul des valeurs actuelles des OG (moyenne des OS)...")
            og_list = session.exec(
                select(ObjectifPerformance).where(
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value
                )
            ).all()
            
            for og in og_list:
                # Récupérer tous les OS associés à cet OG
                os_associes = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.objectif_global_id == og.id,
                            ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
                        )
                    )
                ).all()
                
                if os_associes:
                    # Calculer la moyenne des valeurs actuelles des OS
                    valeurs = [os.valeur_actuelle for os in os_associes if os.valeur_actuelle is not None]
                    if valeurs:
                        moyenne = sum(valeurs) / len(valeurs)
                        og.valeur_actuelle = Decimal(str(round(moyenne, 2)))
                        logger.debug(f"  OG {og.code or og.id}: {og.valeur_actuelle} (moyenne de {len(valeurs)} OS)")
                    else:
                        og.valeur_actuelle = Decimal('0')
                else:
                    og.valeur_actuelle = Decimal('0')
                session.add(og)
            
            session.commit()
            logger.info(f"✅ {len(og_list)} OG mis à jour")
            
            # 3. Calculer les valeurs des RS (Résultats Stratégiques) = moyenne des OG associés
            logger.info("🔄 Calcul des valeurs actuelles des RS (moyenne des OG)...")
            rs_list = session.exec(select(ResultatStrategique)).all()
            
            for rs in rs_list:
                # Récupérer tous les OG associés à ce RS
                og_associes = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.resultat_strategique_id == rs.id,
                            ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value
                        )
                    )
                ).all()
                
                if og_associes:
                    # Calculer la moyenne des valeurs actuelles des OG
                    valeurs = [og.valeur_actuelle for og in og_associes if og.valeur_actuelle is not None]
                    if valeurs:
                        moyenne = sum(valeurs) / len(valeurs)
                        rs.valeur_actuelle = Decimal(str(round(moyenne, 2)))
                        logger.debug(f"  RS {rs.id}: {rs.valeur_actuelle} (moyenne de {len(valeurs)} OG)")
                    else:
                        rs.valeur_actuelle = Decimal('0')
                else:
                    rs.valeur_actuelle = Decimal('0')
                session.add(rs)
            
            session.commit()
            logger.info(f"✅ {len(rs_list)} RS mis à jour")
            
            # 4. Calculer les valeurs des Orientations Stratégiques = moyenne des RS associés
            logger.info("🔄 Calcul des valeurs actuelles des Orientations Stratégiques (moyenne des RS)...")
            orientations = session.exec(select(OrientationStrategique)).all()
            
            for orientation in orientations:
                # Récupérer tous les RS associés à cette orientation
                rs_associes = session.exec(
                    select(ResultatStrategique).where(
                        ResultatStrategique.orientation_id == orientation.id
                    )
                ).all()
                
                if rs_associes:
                    # Calculer la moyenne des valeurs actuelles des RS
                    valeurs = [rs.valeur_actuelle for rs in rs_associes if rs.valeur_actuelle is not None]
                    if valeurs:
                        moyenne = sum(valeurs) / len(valeurs)
                        orientation.valeur_actuelle = Decimal(str(round(moyenne, 2)))
                        logger.debug(f"  Orientation {orientation.id}: {orientation.valeur_actuelle} (moyenne de {len(valeurs)} RS)")
                    else:
                        orientation.valeur_actuelle = Decimal('0')
                else:
                    orientation.valeur_actuelle = Decimal('0')
                session.add(orientation)
            
            session.commit()
            logger.info(f"✅ {len(orientations)} Orientations Stratégiques mises à jour")
            
            # 5. Note: Pour les Programmes, on pourrait ajouter un champ valeur_actuelle si nécessaire
            # Pour l'instant, on calcule mais on ne stocke pas (car Programme n'a pas ce champ)
            logger.info("✅ Calcul en cascade terminé")
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erreur lors du calcul en cascade: {e}", exc_info=True)
            raise
