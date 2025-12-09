"""
Service pour la gestion des données du Rapport Annuel de Performance (RAP)
"""

from sqlmodel import Session, select, or_
from sqlalchemy import func
from app.models.rap_data import RapData
from app.models.personnel import Direction, Service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RapDataService:
    """
    Service pour gérer les données du RAP
    """

    @staticmethod
    def get_rap_data(db_session: Session) -> RapData:
        """
        Récupère les données RAP (singleton - toujours ID 1)
        
        Args:
            db_session: Session de base de données
            
        Returns:
            Les données RAP (créées si elles n'existent pas)
        """
        rap_data = db_session.get(RapData, 1)
        
        if not rap_data:
            logger.info("📄 Création des données RAP par défaut")
            rap_data = RapData(id=1)
            db_session.add(rap_data)
            db_session.commit()
            db_session.refresh(rap_data)
        
        return rap_data

    @staticmethod
    def update_rap_data(db_session: Session, user_id: int, **kwargs) -> RapData:
        """
        Met à jour les données RAP
        
        Args:
            db_session: Session de base de données
            user_id: ID de l'utilisateur qui modifie
            **kwargs: Paramètres à mettre à jour
            
        Returns:
            Les données RAP mises à jour
        """
        rap_data = RapDataService.get_rap_data(db_session)
        
        # Mettre à jour uniquement les champs fournis
        for key, value in kwargs.items():
            if hasattr(rap_data, key):
                setattr(rap_data, key, value)
        
        # Mettre à jour le timestamp et l'utilisateur
        rap_data.update_timestamp(user_id)
        
        db_session.add(rap_data)
        db_session.commit()
        db_session.refresh(rap_data)
        
        logger.info(f"✅ Données RAP mises à jour par user #{user_id}")
        
        return rap_data

    @staticmethod
    def calculate_organization_structure(db_session: Session) -> dict[str, int]:
        """
        Calcule automatiquement la structure organisationnelle depuis les référentiels.
        
        Args:
            db_session: Session de base de données
            
        Returns:
            Dictionnaire avec:
            - nb_directions_centrales: Nombre de directions centrales actives
            - nb_directions_generales: Nombre de directions générales actives
            - nb_services: Nombre de services actifs
        """
        try:
            # Compter les directions centrales (type="CENTRALE" ou "centrale" et actif=True)
            # Utiliser func.upper() pour normaliser la comparaison (insensible à la casse)
            # Note: func.upper() convertit en majuscules, donc "centrale" devient "CENTRALE"
            directions_centrales_query = select(Direction).where(
                Direction.actif == True,
                func.upper(func.coalesce(Direction.type, '')) == "CENTRALE"
            )
            directions_centrales = list(db_session.exec(directions_centrales_query).all())
            nb_directions_centrales = len(directions_centrales) if directions_centrales else 0
            
            # Compter les directions générales (type="GENERALE", "GÉNÉRALE", "générale" ou "générale" et actif=True)
            # Utiliser or_ avec plusieurs variantes possibles
            # Note: "GÉNÉRALE" avec accent et "GENERALE" sans accent sont deux valeurs différentes
            # Utiliser func.upper() pour chaque variante pour gérer la casse
            directions_generales_query = select(Direction).where(
                Direction.actif == True,
                or_(
                    func.upper(func.coalesce(Direction.type, '')) == "GÉNÉRALE",
                    func.upper(func.coalesce(Direction.type, '')) == "GENERALE"
                )
            )
            directions_generales = list(db_session.exec(directions_generales_query).all())
            nb_directions_generales = len(directions_generales) if directions_generales else 0
            
            # Compter les services actifs
            services_query = select(Service).where(Service.actif == True)
            services = db_session.exec(services_query).all()
            nb_services = len(services) if services else 0
            
            result = {
                "nb_directions_centrales": nb_directions_centrales,
                "nb_directions_generales": nb_directions_generales,
                "nb_services": nb_services,
            }
            
            logger.debug(
                f"📊 Structure organisationnelle calculée: "
                f"{nb_directions_centrales} directions centrales, "
                f"{nb_directions_generales} directions générales, "
                f"{nb_services} services"
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors du calcul de la structure organisationnelle: {e}")
            # Retourner des valeurs par défaut en cas d'erreur
            return {
                "nb_directions_centrales": 0,
                "nb_directions_generales": 0,
                "nb_services": 0,
            }

