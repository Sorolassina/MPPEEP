"""
Service pour la gestion des données du Rapport d'Activité RPROG
"""

from sqlmodel import Session, select
from app.models.rprog_data import RprogData
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RprogDataService:
    """
    Service pour gérer les données du RPROG
    """

    @staticmethod
    def get_rprog_data(
        db_session: Session,
        programme_id: int
    ) -> RprogData | None:
        """
        Récupère les données RPROG pour un programme donné
        Une seule ligne par programme (indépendamment de l'année/période)
        
        Args:
            db_session: Session de base de données
            programme_id: ID du programme
            
        Returns:
            Les données RPROG ou None si elles n'existent pas
        """
        rprog_data = db_session.exec(
            select(RprogData).where(
                RprogData.programme_id == programme_id
            )
        ).first()
        
        return rprog_data

    @staticmethod
    def get_or_create_rprog_data(
        db_session: Session,
        programme_id: int,
        user_id: int
    ) -> RprogData:
        """
        Récupère ou crée les données RPROG pour un programme donné
        Une seule ligne par programme (les données précédentes sont écrasées)
        
        Args:
            db_session: Session de base de données
            programme_id: ID du programme
            user_id: ID de l'utilisateur
            
        Returns:
            Les données RPROG (créées si elles n'existent pas)
        """
        rprog_data = RprogDataService.get_rprog_data(db_session, programme_id)
        
        if not rprog_data:
            logger.info(f"📄 Création des données RPROG pour programme_id={programme_id}")
            rprog_data = RprogData(
                programme_id=programme_id
            )
            rprog_data.update_timestamp(user_id)
            db_session.add(rprog_data)
            db_session.commit()
            db_session.refresh(rprog_data)
        
        return rprog_data

    @staticmethod
    def update_rprog_data(
        db_session: Session,
        programme_id: int,
        user_id: int,
        **kwargs
    ) -> RprogData:
        """
        Met à jour les données RPROG
        Une seule ligne par programme (écrase les données précédentes)
        
        Args:
            db_session: Session de base de données
            programme_id: ID du programme
            user_id: ID de l'utilisateur qui modifie
            **kwargs: Paramètres à mettre à jour
            
        Returns:
            Les données RPROG mises à jour
        """
        rprog_data = RprogDataService.get_or_create_rprog_data(
            db_session, programme_id, user_id
        )
        
        # Mettre à jour uniquement les champs fournis
        # Suivre EXACTEMENT la même logique que RapDataService
        for key, value in kwargs.items():
            if hasattr(rprog_data, key):
                setattr(rprog_data, key, value)
        
        # Mettre à jour le timestamp et l'utilisateur
        rprog_data.update_timestamp(user_id)
        
        db_session.add(rprog_data)
        db_session.commit()
        db_session.refresh(rprog_data)
        
        logger.info(f"✅ Données RPROG mises à jour par user #{user_id} (programme_id={programme_id})")
        
        return rprog_data

    @staticmethod
    def delete_rprog_data(
        db_session: Session,
        programme_id: int
    ) -> bool:
        """
        Supprime les données RPROG
        
        Args:
            db_session: Session de base de données
            programme_id: ID du programme
            
        Returns:
            True si supprimé, False si non trouvé
        """
        rprog_data = RprogDataService.get_rprog_data(db_session, programme_id)
        
        if rprog_data:
            db_session.delete(rprog_data)
            db_session.commit()
            logger.info(f"🗑️ Données RPROG supprimées (programme_id={programme_id})")
            return True
        
        return False

