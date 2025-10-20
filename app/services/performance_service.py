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
    PrioriteObjectif,
    StatutObjectif,
    TypeObjectif,
)

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

            objectif = ObjectifPerformance(
                titre=objectif_data["titre"],
                description=objectif_data.get("description"),
                type_objectif=TypeObjectif(objectif_data.get("type_objectif", "OPERATIONNEL")),
                priorite=PrioriteObjectif(objectif_data.get("priorite", "NORMALE")),
                date_debut=objectif_data.get("date_debut", date.today()),
                date_fin=objectif_data["date_fin"],
                periode=objectif_data.get("periode", ""),
                valeur_cible=Decimal(str(objectif_data["valeur_cible"])),
                valeur_actuelle=Decimal(str(objectif_data.get("valeur_actuelle", 0))),
                unite=objectif_data.get("unite", ""),
                responsable_id=objectif_data["responsable_id"],
                service_responsable=objectif_data.get("service_responsable"),
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
            logger.error(f"Erreur lors de la création de l'objectif: {e}")
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
                conditions.append(ObjectifPerformance.type_objectif == type_objectif)

            if conditions:
                query = query.where(and_(*conditions))

            # Tri par date de création décroissante
            query = query.order_by(ObjectifPerformance.created_at.desc())

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
                if hasattr(objectif, field) and value is not None:
                    if field in ["valeur_cible", "valeur_actuelle"]:
                        setattr(objectif, field, Decimal(str(value)))
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
        """Récupère les KPIs des objectifs"""
        try:
            # Total objectifs
            total_objectifs = session.exec(select(func.count(ObjectifPerformance.id))).one()

            # Objectifs par statut
            objectifs_atteints = session.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.ATTEINT)
            ).one()

            objectifs_en_cours = session.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.EN_COURS)
            ).one()

            objectifs_en_retard = session.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.EN_RETARD)
            ).one()

            # Taux de réalisation global
            taux_realisation = 0
            if total_objectifs > 0:
                taux_realisation = (objectifs_atteints / total_objectifs) * 100

            # Progression moyenne
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
            indicateur = IndicateurPerformance(
                nom=indicateur_data["nom"],
                description=indicateur_data.get("description"),
                formule_calcul=indicateur_data.get("formule_calcul"),
                categorie=indicateur_data.get("categorie", "OPERATIONNEL"),
                type_indicateur=indicateur_data.get("type_indicateur", "Nombre"),
                valeur_cible=indicateur_data.get("valeur_cible"),
                valeur_actuelle=indicateur_data.get("valeur_actuelle", Decimal(0)),
                unite=indicateur_data.get("unite_mesure", ""),
                seuil_alerte_bas=indicateur_data.get("seuil_alerte_min"),
                seuil_alerte_haut=indicateur_data.get("seuil_alerte_max"),
                frequence_maj=indicateur_data.get("frequence_mesure", "MENSUEL"),
                responsable_id=indicateur_data["responsable_id"],
                source_donnees=indicateur_data.get("source_donnees"),
                actif=indicateur_data.get("actif", True),
                created_by_id=created_by_id,
            )

            session.add(indicateur)
            session.commit()
            session.refresh(indicateur)

            logger.info(f"Indicateur créé: {indicateur.nom} (ID: {indicateur.id})")
            return indicateur

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la création de l'indicateur: {e}")
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

                if hasattr(indicateur, model_field) and value is not None:
                    setattr(indicateur, model_field, value)

            indicateur.updated_at = datetime.now()

            session.add(indicateur)
            session.commit()
            session.refresh(indicateur)

            logger.info(f"Indicateur modifié: {indicateur.nom} (ID: {indicateur.id})")
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
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la suppression de l'indicateur {indicateur_id}: {e}")
            return False
