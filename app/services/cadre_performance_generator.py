# app/services/cadre_performance_generator.py
"""
Service de génération du cadre de performance
Génère un PDF récapitulatif des cadres de performance par programme ou pour tout le ministère
"""

from io import BytesIO
from typing import Any
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlmodel import Session, select, and_

from app.core.logging_config import get_logger
from app.models.performance import (
    ObjectifPerformance,
    IndicateurPerformance,
    TypeObjectif,
    ResultatStrategique,
    OrientationStrategique,
)
from app.models.personnel import Programme

logger = get_logger(__name__)


class CadrePerformanceFakeDataLoader:
    """
    Gestionnaire de données factices pour le cadre de performance.
    
    Cette classe regroupe toutes les données factices utilisées en mode brouillon
    lorsque la base de données est vide ou que les données ne sont pas disponibles.
    """
    
    @staticmethod
    def get_fake_cadre_performance_data(annee_reference: int, annee_redaction: int) -> dict[str, Any]:
        """
        Retourne les données factices pour le cadre de performance.
        
        Args:
            annee_reference: Année de référence (année de base fixe, ex: 2021)
            annee_redaction: Année de rédaction (N) - période de rédaction
        
        Returns:
            Dictionnaire contenant les données factices structurées
        """
        annee_n = annee_redaction  # N = année de rédaction
        annee_n1 = annee_redaction + 1
        annee_n2 = annee_redaction + 2
        
        return {
            "annee_reference": annee_reference,
            "annee_redaction": annee_redaction,
            "programmes": [
                {
                    "id": 1,
                    "code": "P1",
                    "libelle": "ADMINISTRATION GÉNÉRALE",
                    "objectifs_globaux": [
                        {
                            "id": 1,
                            "titre": "Assurer le pilotage des activités du Ministère",
                            "description": "Objectif global pour le pilotage",
                            "objectifs_specifiques": [
                                {
                                    "id": 1,
                                    "titre": "OS 1: Assurer une meilleure coordination et animation des activités du Ministère",
                                    "description": "Objectif spécifique de coordination",
                                    "indicateurs": [
                                        {
                                            "id": 1,
                                            "nom": "Taux de réalisation des activités du CONAFIP relevant du cabinet du MBPE",
                                            "unite": "",
                                            "valeur_reference": 80.7,
                                            f"cible_{annee_n}": 80,
                                            f"cible_{annee_n1}": 80,
                                            f"cible_{annee_n2}": 80,
                                            "mode_calcul": "Nombre d'activités couvertes/ nombre d'activités prévues",
                                            "source_verification": "Rapport CONAFIP/Cabinet",
                                        },
                                        {
                                            "id": 2,
                                            "nom": "Taux de réalisation du PAS du programme AG",
                                            "unite": "%",
                                            "valeur_reference": None,
                                            f"cible_{annee_n}": 80,
                                            f"cible_{annee_n1}": 80,
                                            f"cible_{annee_n2}": 80,
                                            "mode_calcul": "Nombre d'activités (DAAF/DCF) réalisées/ nombre d'activités (DAAF/DCF) prévues",
                                            "source_verification": "Rapport PAS DAAF/DCF",
                                        },
                                        {
                                            "id": 3,
                                            "nom": "Taux de participation aux réunions de coordination interministérielle",
                                            "unite": "%",
                                            "valeur_reference": 75.5,
                                            f"cible_{annee_n}": 85,
                                            f"cible_{annee_n1}": 90,
                                            f"cible_{annee_n2}": 95,
                                            "mode_calcul": "Nombre de réunions auxquelles le Ministère a participé / nombre de réunions convoquées",
                                            "source_verification": "Procès-verbaux des réunions",
                                        },
                                    ],
                                },
                                {
                                    "id": 2,
                                    "titre": "OS 2: Assurer une meilleure gestion des ressources humaines, matérielles et financières",
                                    "description": "Objectif spécifique de gestion",
                                    "indicateurs": [
                                        {
                                            "id": 4,
                                            "nom": "Taux de couverture des besoins en personnel des programmes",
                                            "unite": "%",
                                            "valeur_reference": 100.0,
                                            f"cible_{annee_n}": 80,
                                            f"cible_{annee_n1}": 85,
                                            f"cible_{annee_n2}": 95,
                                            "mode_calcul": "Nombre d'agents affectés / nombre d'agents sollicités par les RPROG",
                                            "source_verification": "Rapport d'activité de la DAAF",
                                        },
                                        {
                                            "id": 5,
                                            "nom": "Taux d'exécution du budget du programme Administration Générale",
                                            "unite": "",
                                            "valeur_reference": 99.86,
                                            f"cible_{annee_n}": 70,
                                            f"cible_{annee_n1}": 70,
                                            f"cible_{annee_n2}": 70,
                                            "mode_calcul": "Mandats ordonnancés/ Budget actuel",
                                            "source_verification": "Rapport d'activité de la DAAF",
                                        },
                                        {
                                            "id": 6,
                                            "nom": "Taux de disponibilité des équipements informatiques",
                                            "unite": "%",
                                            "valeur_reference": 88.2,
                                            f"cible_{annee_n}": 90,
                                            f"cible_{annee_n1}": 92,
                                            f"cible_{annee_n2}": 95,
                                            "mode_calcul": "Nombre d'équipements fonctionnels / nombre total d'équipements",
                                            "source_verification": "Rapport technique DSI",
                                        },
                                    ],
                                },
                                {
                                    "id": 3,
                                    "titre": "OS 3: Assurer le contrôle de l'exécution du budget de l'Etat",
                                    "description": "Objectif spécifique de contrôle",
                                    "indicateurs": [
                                        {
                                            "id": 7,
                                            "nom": "Délai moyen de traitement des dossiers soumis au visa du CF",
                                            "unite": "jours ouvrés",
                                            "valeur_reference": 5,
                                            f"cible_{annee_n}": 6,
                                            f"cible_{annee_n1}": 6,
                                            f"cible_{annee_n2}": 6,
                                            "mode_calcul": "Somme des délais de traitement des dossiers reçus / nombre total de dossiers reçus",
                                            "source_verification": "Rapport d'activité de la DCF",
                                        },
                                        {
                                            "id": 8,
                                            "nom": "Taux de conformité des dossiers soumis au visa",
                                            "unite": "%",
                                            "valeur_reference": 92.5,
                                            f"cible_{annee_n}": 95,
                                            f"cible_{annee_n1}": 96,
                                            f"cible_{annee_n2}": 98,
                                            "mode_calcul": "Nombre de dossiers conformes / nombre total de dossiers reçus",
                                            "source_verification": "Rapport d'activité de la DCF",
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "id": 2,
                            "titre": "Renforcer la transparence et la redevabilité",
                            "description": "Objectif global pour la transparence",
                            "objectifs_specifiques": [
                                {
                                    "id": 10,
                                    "titre": "OS 1: Améliorer la communication et l'information du public",
                                    "description": "Objectif spécifique de communication",
                                    "indicateurs": [
                                        {
                                            "id": 24,
                                            "nom": "Taux de publication des rapports d'activité",
                                            "unite": "%",
                                            "valeur_reference": 85.5,
                                            f"cible_{annee_n}": 90,
                                            f"cible_{annee_n1}": 95,
                                            f"cible_{annee_n2}": 100,
                                            "mode_calcul": "Nombre de rapports publiés / nombre de rapports prévus",
                                            "source_verification": "Site web du Ministère",
                                        },
                                        {
                                            "id": 25,
                                            "nom": "Nombre de communiqués de presse publiés",
                                            "unite": "communiqués",
                                            "valeur_reference": 45,
                                            f"cible_{annee_n}": 50,
                                            f"cible_{annee_n1}": 55,
                                            f"cible_{annee_n2}": 60,
                                            "mode_calcul": "Nombre total de communiqués publiés",
                                            "source_verification": "Rapport de la Direction de la Communication",
                                        },
                                    ],
                                },
                                {
                                    "id": 11,
                                    "titre": "OS 2: Renforcer la participation citoyenne",
                                    "description": "Objectif spécifique de participation",
                                    "indicateurs": [
                                        {
                                            "id": 26,
                                            "nom": "Nombre de consultations publiques organisées",
                                            "unite": "consultations",
                                            "valeur_reference": 8,
                                            f"cible_{annee_n}": 10,
                                            f"cible_{annee_n1}": 12,
                                            f"cible_{annee_n2}": 15,
                                            "mode_calcul": "Nombre total de consultations organisées",
                                            "source_verification": "Rapport de la Direction de la Participation Citoyenne",
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": 2,
                    "code": "P2",
                    "libelle": "PLANIFICATION ET SUIVI DES POLITIQUES PUBLIQUES",
                    "objectifs_globaux": [
                        {
                            "id": 2,
                            "titre": "Améliorer la qualité de la planification et du suivi des politiques publiques",
                            "description": "Objectif global pour la planification",
                            "objectifs_specifiques": [
                                {
                                    "id": 4,
                                    "titre": "OS 1: Renforcer les capacités de planification stratégique",
                                    "description": "Objectif spécifique de planification",
                                    "indicateurs": [
                                        {
                                            "id": 9,
                                            "nom": "Taux de réalisation des plans stratégiques sectoriels",
                                            "unite": "%",
                                            "valeur_reference": 78.3,
                                            f"cible_{annee_n}": 85,
                                            f"cible_{annee_n1}": 88,
                                            f"cible_{annee_n2}": 90,
                                            "mode_calcul": "Nombre de plans stratégiques réalisés / nombre de plans prévus",
                                            "source_verification": "Rapport de suivi des plans stratégiques",
                                        },
                                        {
                                            "id": 10,
                                            "nom": "Nombre de sessions de formation en planification stratégique organisées",
                                            "unite": "sessions",
                                            "valeur_reference": 12,
                                            f"cible_{annee_n}": 15,
                                            f"cible_{annee_n1}": 18,
                                            f"cible_{annee_n2}": 20,
                                            "mode_calcul": "Nombre total de sessions organisées",
                                            "source_verification": "Rapport d'activité de la Direction de la Planification",
                                        },
                                        {
                                            "id": 11,
                                            "nom": "Taux de mise à jour des indicateurs de suivi",
                                            "unite": "%",
                                            "valeur_reference": 65.0,
                                            f"cible_{annee_n}": 75,
                                            f"cible_{annee_n1}": 80,
                                            f"cible_{annee_n2}": 85,
                                            "mode_calcul": "Nombre d'indicateurs mis à jour / nombre total d'indicateurs",
                                            "source_verification": "Base de données des indicateurs",
                                        },
                                    ],
                                },
                                {
                                    "id": 5,
                                    "titre": "OS 2: Améliorer le suivi et l'évaluation des politiques publiques",
                                    "description": "Objectif spécifique de suivi",
                                    "indicateurs": [
                                        {
                                            "id": 12,
                                            "nom": "Taux de réalisation des évaluations de politiques publiques",
                                            "unite": "%",
                                            "valeur_reference": 70.5,
                                            f"cible_{annee_n}": 80,
                                            f"cible_{annee_n1}": 85,
                                            f"cible_{annee_n2}": 90,
                                            "mode_calcul": "Nombre d'évaluations réalisées / nombre d'évaluations prévues",
                                            "source_verification": "Rapport d'évaluation des politiques publiques",
                                        },
                                        {
                                            "id": 13,
                                            "nom": "Délai moyen de production des rapports de suivi",
                                            "unite": "jours",
                                            "valeur_reference": 45,
                                            f"cible_{annee_n}": 40,
                                            f"cible_{annee_n1}": 35,
                                            f"cible_{annee_n2}": 30,
                                            "mode_calcul": "Somme des délais de production / nombre de rapports produits",
                                            "source_verification": "Rapport d'activité de la Direction de l'Évaluation",
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": 3,
                    "code": "P3",
                    "libelle": "DÉVELOPPEMENT DES RESSOURCES HUMAINES",
                    "objectifs_globaux": [
                        {
                            "id": 3,
                            "titre": "Renforcer les capacités et améliorer la gestion des ressources humaines",
                            "description": "Objectif global pour les RH",
                            "objectifs_specifiques": [
                                {
                                    "id": 6,
                                    "titre": "OS 1: Améliorer le recrutement et la formation du personnel",
                                    "description": "Objectif spécifique de recrutement",
                                    "indicateurs": [
                                        {
                                            "id": 14,
                                            "nom": "Taux de recrutement des postes vacants",
                                            "unite": "%",
                                            "valeur_reference": 68.5,
                                            f"cible_{annee_n}": 75,
                                            f"cible_{annee_n1}": 80,
                                            f"cible_{annee_n2}": 85,
                                            "mode_calcul": "Nombre de postes pourvus / nombre de postes vacants",
                                            "source_verification": "Rapport de la Direction des Ressources Humaines",
                                        },
                                        {
                                            "id": 15,
                                            "nom": "Taux de participation aux formations continues",
                                            "unite": "%",
                                            "valeur_reference": 55.2,
                                            f"cible_{annee_n}": 65,
                                            f"cible_{annee_n1}": 70,
                                            f"cible_{annee_n2}": 75,
                                            "mode_calcul": "Nombre d'agents formés / nombre total d'agents",
                                            "source_verification": "Rapport de formation de la DRH",
                                        },
                                        {
                                            "id": 16,
                                            "nom": "Nombre de sessions de formation organisées",
                                            "unite": "sessions",
                                            "valeur_reference": 45,
                                            f"cible_{annee_n}": 50,
                                            f"cible_{annee_n1}": 55,
                                            f"cible_{annee_n2}": 60,
                                            "mode_calcul": "Nombre total de sessions organisées",
                                            "source_verification": "Rapport d'activité de la DRH",
                                        },
                                    ],
                                },
                                {
                                    "id": 7,
                                    "titre": "OS 2: Améliorer la gestion de carrière et la motivation du personnel",
                                    "description": "Objectif spécifique de gestion de carrière",
                                    "indicateurs": [
                                        {
                                            "id": 17,
                                            "nom": "Taux de satisfaction du personnel",
                                            "unite": "%",
                                            "valeur_reference": 72.8,
                                            f"cible_{annee_n}": 75,
                                            f"cible_{annee_n1}": 78,
                                            f"cible_{annee_n2}": 80,
                                            "mode_calcul": "Nombre de personnes satisfaites / nombre total de personnes interrogées",
                                            "source_verification": "Enquête de satisfaction du personnel",
                                        },
                                        {
                                            "id": 18,
                                            "nom": "Taux de rotation du personnel",
                                            "unite": "%",
                                            "valeur_reference": 8.5,
                                            f"cible_{annee_n}": 7,
                                            f"cible_{annee_n1}": 6,
                                            f"cible_{annee_n2}": 5,
                                            "mode_calcul": "Nombre de départs / effectif moyen",
                                            "source_verification": "Rapport de la DRH",
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "id": 5,
                            "titre": "Améliorer le bien-être et la qualité de vie au travail",
                            "description": "Objectif global pour le bien-être",
                            "objectifs_specifiques": [
                                {
                                    "id": 13,
                                    "titre": "OS 1: Promouvoir la santé et la sécurité au travail",
                                    "description": "Objectif spécifique de santé",
                                    "indicateurs": [
                                        {
                                            "id": 29,
                                            "nom": "Taux d'accidents du travail",
                                            "unite": "%",
                                            "valeur_reference": 2.5,
                                            f"cible_{annee_n}": 2.0,
                                            f"cible_{annee_n1}": 1.5,
                                            f"cible_{annee_n2}": 1.0,
                                            "mode_calcul": "Nombre d'accidents / nombre total d'heures travaillées x 1000",
                                            "source_verification": "Rapport de la Direction de la Sécurité",
                                        },
                                        {
                                            "id": 30,
                                            "nom": "Taux de participation aux formations de sécurité",
                                            "unite": "%",
                                            "valeur_reference": 68.0,
                                            f"cible_{annee_n}": 75,
                                            f"cible_{annee_n1}": 80,
                                            f"cible_{annee_n2}": 85,
                                            "mode_calcul": "Nombre d'agents formés / nombre total d'agents",
                                            "source_verification": "Rapport de formation",
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": 4,
                    "code": "P4",
                    "libelle": "MODERNISATION ET INNOVATION",
                    "objectifs_globaux": [
                        {
                            "id": 4,
                            "titre": "Moderniser les systèmes et promouvoir l'innovation",
                            "description": "Objectif global pour la modernisation",
                            "objectifs_specifiques": [
                                {
                                    "id": 8,
                                    "titre": "OS 1: Digitaliser les processus administratifs",
                                    "description": "Objectif spécifique de digitalisation",
                                    "indicateurs": [
                                        {
                                            "id": 19,
                                            "nom": "Taux de digitalisation des procédures",
                                            "unite": "%",
                                            "valeur_reference": 45.5,
                                            f"cible_{annee_n}": 55,
                                            f"cible_{annee_n1}": 65,
                                            f"cible_{annee_n2}": 75,
                                            "mode_calcul": "Nombre de procédures digitalisées / nombre total de procédures",
                                            "source_verification": "Rapport de la Direction des Systèmes d'Information",
                                        },
                                        {
                                            "id": 20,
                                            "nom": "Taux d'utilisation des services en ligne",
                                            "unite": "%",
                                            "valeur_reference": 38.2,
                                            f"cible_{annee_n}": 50,
                                            f"cible_{annee_n1}": 60,
                                            f"cible_{annee_n2}": 70,
                                            "mode_calcul": "Nombre de transactions en ligne / nombre total de transactions",
                                            "source_verification": "Statistiques de la plateforme en ligne",
                                        },
                                        {
                                            "id": 21,
                                            "nom": "Nombre de nouveaux services numériques mis en place",
                                            "unite": "services",
                                            "valeur_reference": 5,
                                            f"cible_{annee_n}": 8,
                                            f"cible_{annee_n1}": 10,
                                            f"cible_{annee_n2}": 12,
                                            "mode_calcul": "Nombre total de nouveaux services lancés",
                                            "source_verification": "Rapport d'activité de la DSI",
                                        },
                                    ],
                                },
                                {
                                    "id": 9,
                                    "titre": "OS 2: Améliorer l'efficacité opérationnelle",
                                    "description": "Objectif spécifique d'efficacité",
                                    "indicateurs": [
                                        {
                                            "id": 22,
                                            "nom": "Taux de réduction des délais de traitement",
                                            "unite": "%",
                                            "valeur_reference": 15.3,
                                            f"cible_{annee_n}": 20,
                                            f"cible_{annee_n1}": 25,
                                            f"cible_{annee_n2}": 30,
                                            "mode_calcul": "(Délai initial - Délai actuel) / Délai initial x 100",
                                            "source_verification": "Rapport d'activité des services",
                                        },
                                        {
                                            "id": 23,
                                            "nom": "Taux de satisfaction des usagers",
                                            "unite": "%",
                                            "valeur_reference": 68.5,
                                            f"cible_{annee_n}": 75,
                                            f"cible_{annee_n1}": 80,
                                            f"cible_{annee_n2}": 85,
                                            "mode_calcul": "Nombre d'usagers satisfaits / nombre total d'usagers interrogés",
                                            "source_verification": "Enquête de satisfaction",
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "id": 6,
                            "titre": "Promouvoir l'innovation technologique",
                            "description": "Objectif global pour l'innovation",
                            "objectifs_specifiques": [
                                {
                                    "id": 14,
                                    "titre": "OS 1: Développer les solutions innovantes",
                                    "description": "Objectif spécifique d'innovation",
                                    "indicateurs": [
                                        {
                                            "id": 31,
                                            "nom": "Nombre de projets d'innovation lancés",
                                            "unite": "projets",
                                            "valeur_reference": 8,
                                            f"cible_{annee_n}": 10,
                                            f"cible_{annee_n1}": 12,
                                            f"cible_{annee_n2}": 15,
                                            "mode_calcul": "Nombre total de projets lancés",
                                            "source_verification": "Rapport de la Direction de l'Innovation",
                                        },
                                        {
                                            "id": 32,
                                            "nom": "Taux d'adoption des nouvelles technologies",
                                            "unite": "%",
                                            "valeur_reference": 55.5,
                                            f"cible_{annee_n}": 65,
                                            f"cible_{annee_n1}": 75,
                                            f"cible_{annee_n2}": 85,
                                            "mode_calcul": "Nombre de services utilisant les nouvelles technologies / nombre total de services",
                                            "source_verification": "Rapport technique",
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }


class CadrePerformanceGenerator:
    """Générateur de cadre de performance"""

    @staticmethod
    def should_use_fake_data(mode: str = "brouillon") -> bool:
        """
        Détermine si on doit utiliser des données factices.
        
        Les données factices ne sont utilisées qu'en mode "brouillon"
        pour permettre de générer un aperçu du cadre même si la base
        de données est vide.
        
        Args:
            mode: Mode de génération ("brouillon" ou "final")
        
        Returns:
            True si on doit utiliser des données factices (mode brouillon), False sinon
        """
        return mode == "brouillon"
    
    @staticmethod
    def load_performance_framework_data(
        session: Session,
        programme_id: int | None = None,
        annee_reference: int | None = None,
        annee_redaction: int | None = None,
        mode: str = "brouillon"
    ) -> dict[str, Any]:
        """
        Charge les données du cadre de performance depuis la base de données.
        
        Args:
            session: Session de base de données
            programme_id: ID du programme (None pour tout le ministère)
            annee_reference: Année de référence (année de base fixe, ex: 2021) - année à partir de laquelle on a commencé à mesurer
            annee_redaction: Année de rédaction (N) - période de rédaction du rapport
            mode: Mode de génération ("brouillon" ou "final")
        
        Returns:
            Dictionnaire contenant les données structurées :
            - annee_reference: Année de référence (année de base)
            - annee_redaction: Année de rédaction (N)
            - programmes: Liste des programmes avec leurs cadres de performance
            - objectifs_globaux: Liste des objectifs globaux
            - objectifs_specifiques: Liste des objectifs spécifiques par objectif global
            - indicateurs: Liste des indicateurs par objectif spécifique
        """
        from datetime import datetime
        
        if annee_reference is None:
            annee_reference = 2021  # Année de base par défaut
        if annee_redaction is None:
            annee_redaction = datetime.now().year  # N = année courante
        
        data: dict[str, Any] = {
            "annee_reference": annee_reference,
            "annee_redaction": annee_redaction,
            "programmes": [],
        }
        
        # En mode brouillon, utiliser des données factices si pas de données
        use_fake_data = CadrePerformanceGenerator.should_use_fake_data(mode)
        
        try:
            # Si programme_id est spécifié, charger uniquement ce programme
            if programme_id:
                programme = session.exec(
                    select(Programme).where(Programme.id == programme_id)
                ).first()
                
                if programme:
                    programme_data = CadrePerformanceGenerator._load_programme_framework(
                        session, programme, annee_reference, annee_redaction
                    )
                    if programme_data:
                        data["programmes"].append(programme_data)
            else:
                # Charger tous les programmes actifs
                programmes = session.exec(
                    select(Programme).where(Programme.actif == True).order_by(Programme.code)
                ).all()
                
                for programme in programmes:
                    programme_data = CadrePerformanceGenerator._load_programme_framework(
                        session, programme, annee_reference, annee_redaction
                    )
                    if programme_data:
                        data["programmes"].append(programme_data)
            
            logger.info(f"✅ Cadre de performance chargé: {len(data['programmes'])} programme(s)")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du cadre de performance: {e}")
        
        # Si pas de données et mode brouillon, utiliser des données factices
        if not data["programmes"] and use_fake_data:
            logger.info(f"📊 Mode brouillon: génération de données factices pour le cadre de performance")
            fake_data = CadrePerformanceFakeDataLoader.get_fake_cadre_performance_data(
                annee_reference, annee_redaction
            )
            
            # Filtrer par programme si nécessaire
            if programme_id:
                fake_data["programmes"] = [
                    p for p in fake_data["programmes"] 
                    if p.get("id") == programme_id
                ]
            
            return fake_data
        
        # En mode final, retourner les données même si vides
        return data
    
    @staticmethod
    def _load_programme_framework(
        session: Session,
        programme: Programme,
        annee_reference: int,
        annee_redaction: int
    ) -> dict[str, Any] | None:
        """Charge le cadre de performance pour un programme spécifique"""
        try:
            # Charger les objectifs globaux (GLOBAL) liés à ce programme
            # Pour l'instant, on charge tous les objectifs globaux
            # TODO: Filtrer par programme si une relation existe
            
            objectifs_globaux_query = select(ObjectifPerformance).where(
                and_(
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL,
                    ObjectifPerformance.resultat_strategique_id.isnot(None)
                )
            ).order_by(ObjectifPerformance.titre)
            objectifs_globaux = session.exec(objectifs_globaux_query).all()
            
            if not objectifs_globaux:
                return None
            
            programme_data = {
                "id": programme.id,
                "code": programme.code,
                "libelle": programme.libelle or programme.code,
                "objectifs_globaux": [],
            }
            
            # Pour chaque objectif global, charger les objectifs spécifiques et leurs indicateurs
            for obj_global in objectifs_globaux:
                # Charger les objectifs spécifiques (SPECIFIQUE) liés à cet objectif global
                objectifs_specifiques_query = select(ObjectifPerformance).where(
                    and_(
                        ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE,
                        ObjectifPerformance.objectif_global_id == obj_global.id
                    )
                ).order_by(ObjectifPerformance.titre)
                objectifs_specifiques = session.exec(objectifs_specifiques_query).all()
                
                obj_global_data = {
                    "id": obj_global.id,
                    "titre": obj_global.titre,
                    "description": obj_global.description,
                    "objectifs_specifiques": [],
                }
                
                # Pour chaque objectif spécifique, charger les indicateurs
                for obj_spec in objectifs_specifiques:
                    # Charger les indicateurs pour cet objectif spécifique
                    # On charge les indicateurs de l'année de rédaction (N) pour obtenir les cibles
                    indicateurs_query = select(IndicateurPerformance).where(
                        and_(
                            IndicateurPerformance.objectif_id == obj_spec.id,
                            IndicateurPerformance.actif == True,
                            IndicateurPerformance.annee == annee_redaction
                        )
                    ).order_by(IndicateurPerformance.nom)
                    indicateurs = session.exec(indicateurs_query).all()
                    
                    obj_spec_data = {
                        "id": obj_spec.id,
                        "titre": obj_spec.titre,
                        "description": obj_spec.description,
                        "indicateurs": [],
                    }
                    
                    # Charger les données de chaque indicateur
                    for ind in indicateurs:
                        # Parser les valeurs cibles futures (format: "80% en 2024, 85% en 2025, 90% en 2026")
                        # Utiliser les années dynamiques basées sur l'année de rédaction (N)
                        annee_n = annee_redaction  # N = année de rédaction
                        annee_n1 = annee_redaction + 1
                        annee_n2 = annee_redaction + 2
                        
                        cible_n = None
                        cible_n1 = None
                        cible_n2 = None
                        
                        if ind.valeurs_cibles_futures:
                            import re
                            # Extraire les valeurs pour chaque année (dynamique)
                            pattern_n = rf'(\d+(?:[.,]\d+)?)\s*%?\s*en\s*{annee_n}'
                            pattern_n1 = rf'(\d+(?:[.,]\d+)?)\s*%?\s*en\s*{annee_n1}'
                            pattern_n2 = rf'(\d+(?:[.,]\d+)?)\s*%?\s*en\s*{annee_n2}'
                            
                            match_n = re.search(pattern_n, ind.valeurs_cibles_futures, re.IGNORECASE)
                            match_n1 = re.search(pattern_n1, ind.valeurs_cibles_futures, re.IGNORECASE)
                            match_n2 = re.search(pattern_n2, ind.valeurs_cibles_futures, re.IGNORECASE)
                            
                            if match_n:
                                cible_n = float(match_n.group(1).replace(',', '.'))
                            if match_n1:
                                cible_n1 = float(match_n1.group(1).replace(',', '.'))
                            if match_n2:
                                cible_n2 = float(match_n2.group(1).replace(',', '.'))
                        
                        # Charger la valeur de référence pour l'année de référence (année de base fixe)
                        valeur_reference = None
                        
                        # Chercher l'indicateur pour l'année de référence (année de base fixe)
                        ind_ref_query = select(IndicateurPerformance).where(
                            and_(
                                IndicateurPerformance.objectif_id == obj_spec.id,
                                IndicateurPerformance.nom == ind.nom,
                                IndicateurPerformance.annee == annee_reference
                            )
                        )
                        ind_ref = session.exec(ind_ref_query).first()
                        if ind_ref and ind_ref.valeur_actuelle:
                            valeur_reference = float(ind_ref.valeur_actuelle)
                        
                        indicateur_data = {
                            "id": ind.id,
                            "nom": ind.nom,
                            "unite": ind.unite or "",
                            "valeur_reference": valeur_reference,
                            f"cible_{annee_n}": cible_n,
                            f"cible_{annee_n1}": cible_n1,
                            f"cible_{annee_n2}": cible_n2,
                            "mode_calcul": ind.formule_calcul or "",
                            "source_verification": ind.source_donnees or "",
                        }
                        
                        obj_spec_data["indicateurs"].append(indicateur_data)
                    
                    obj_global_data["objectifs_specifiques"].append(obj_spec_data)
                
                programme_data["objectifs_globaux"].append(obj_global_data)
            
            return programme_data
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du cadre pour programme {programme.id}: {e}")
            return None
    
    @staticmethod
    def generate_pdf(
        session: Session,
        programme_id: int | None = None,
        annee_reference: int | None = None,
        annee_redaction: int | None = None,
        titre: str | None = None,
        mode: str = "brouillon"
    ) -> BytesIO:
        """
        Génère le PDF du cadre de performance.
        
        Args:
            session: Session de base de données
            programme_id: ID du programme (None pour tout le ministère)
            annee_reference: Année de référence (N) pour laquelle on réalise le cadre
            annee_redaction: Année de rédaction du rapport
            titre: Titre personnalisé du rapport
            mode: Mode de génération ("brouillon" ou "final")
        
        Returns:
            Buffer BytesIO contenant le PDF
        """
        buffer = BytesIO()
        
        # Créer le document en mode paysage avec marges réduites pour agrandir le tableau
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=1*cm,  # Réduit de 1.5cm à 1cm
            leftMargin=1*cm,   # Réduit de 1.5cm à 1cm
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        # Charger les données
        data = CadrePerformanceGenerator.load_performance_framework_data(
            session, programme_id, annee_reference, annee_redaction, mode
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=30,
            alignment=1,  # Centré
        )
        
        # Construire le contenu
        story = []
        
        # Titre
        if titre:
            story.append(Paragraph(titre, title_style))
        else:
            if programme_id:
                programme = session.exec(
                    select(Programme).where(Programme.id == programme_id)
                ).first()
                titre_rapport = f"Cadre de Performance - {programme.libelle if programme else 'Programme'}"
            else:
                titre_rapport = "TABLEAU RECAPITULATIFS DES CADRES DE PERFORMANCE DU MINISTERE"
            story.append(Paragraph(titre_rapport, title_style))
        
        story.append(Spacer(1, 0.5*cm))
        
        # Pour chaque programme, créer un tableau
        for programme_data in data["programmes"]:
            programme_libelle = programme_data["libelle"]
            
            # Titre du programme
            programme_title = Paragraph(
                f"<b>PROGRAMME « {programme_libelle.upper()} »</b>",
                styles['Heading2']
            )
            story.append(programme_title)
            story.append(Spacer(1, 0.3*cm))
            
            # Calculer les années dynamiquement (une fois par programme)
            annee_reference = data.get("annee_reference", 2021)  # Année de base fixe (ex: 2021)
            annee_redaction = data.get("annee_redaction", 2024)  # N = année de rédaction
            annee_n = annee_redaction  # N = année de rédaction
            annee_n1 = annee_redaction + 1
            annee_n2 = annee_redaction + 2
            
            # Créer un seul tableau pour tous les objectifs globaux du programme
            table_data = []
            
            # En-tête du tableau avec deux lignes : une pour les titres principaux, une pour les années des cibles
            header_style = ParagraphStyle(
                'HeaderStyle',
                parent=styles['Normal'],
                fontSize=8,
                fontName='Helvetica-Bold',
                alignment=1,  # Centré
                leading=10,
            )
            
            # Première ligne d'en-tête
            header_row1 = [
                Paragraph("Objectifs<br/>Spécifiques", header_style),
                Paragraph("Indicateurs de<br/>performance", header_style),
                Paragraph("Unité", header_style),
                Paragraph(f"Situation de<br/>référence {annee_reference}", header_style),
                Paragraph("Cibles", header_style),  # Fusionné sur 3 colonnes
                "",  # Vide pour la fusion
                "",  # Vide pour la fusion
                Paragraph("Mode de<br/>calcul", header_style),
                Paragraph("Source de<br/>vérification", header_style),
            ]
            table_data.append(header_row1)
            
            # Deuxième ligne d'en-tête (années des cibles) - ordre croissant de la plus faible à N
            # Les années sont déjà dans l'ordre : annee_n < annee_n1 < annee_n2
            header_row2 = [
                "",  # Vide pour Objectifs Spécifiques
                "",  # Vide pour Indicateurs
                "",  # Vide pour Unité
                "",  # Vide pour Situation de référence
                Paragraph(str(annee_n), header_style),  # Année N (la plus faible)
                Paragraph(str(annee_n1), header_style),  # Année N+1
                Paragraph(str(annee_n2), header_style),  # Année N+2 (la plus élevée)
                "",  # Vide pour Mode de calcul
                "",  # Vide pour Source
            ]
            table_data.append(header_row2)
            
            # Style pour les cellules de données (police réduite) - défini une fois
            cell_style = ParagraphStyle(
                'CellStyle',
                parent=styles['Normal'],
                fontSize=7,
                leading=9,
            )
            
            # Stocker les informations de fusion pour les objectifs spécifiques
            # Format: (row_start, row_end, obj_spec_titre)
            fusion_info = []
            
            # Index de ligne commence après les deux lignes d'en-tête
            row_index = 2  # Commence après l'en-tête ligne 1 (0) et ligne 2 (1)
            
            # Pour chaque objectif global du programme
            for obj_global in programme_data["objectifs_globaux"]:
                # Ligne de rappel de l'objectif global (fusionnée sur toutes les colonnes)
                obj_global_rappel = [
                    Paragraph(f"<b>Objectif global : {obj_global['titre']}</b>", cell_style),
                    "", "", "", "", "", "", "", ""  # Cellules vides pour la fusion
                ]
                table_data.append(obj_global_rappel)
                row_index += 1  # Incrémenter après chaque rappel d'objectif global
                
                # Pour chaque objectif spécifique de cet objectif global
                for obj_spec in obj_global["objectifs_specifiques"]:
                    obj_spec_titre = obj_spec["titre"]
                    nb_indicateurs = len(obj_spec["indicateurs"])
                    
                    if nb_indicateurs > 0:
                        # Enregistrer la position de départ pour la fusion
                        row_start = row_index
                        row_end = row_index + nb_indicateurs - 1
                        fusion_info.append((row_start, row_end, obj_spec_titre))
                        
                        # Pour chaque indicateur
                        for idx, ind in enumerate(obj_spec["indicateurs"]):
                            row = []
                            
                            # Objectif spécifique (sera fusionné plus tard)
                            # On met le texte seulement sur la première ligne, les autres seront vides
                            if idx == 0:
                                row.append(Paragraph(obj_spec_titre, cell_style))
                            else:
                                row.append("")  # Cellule vide pour la fusion
                            
                            # Indicateur
                            row.append(Paragraph(ind["nom"], cell_style))
                            
                            # Unité
                            row.append(ind["unite"] or "")
                            
                            # Situation de référence (année de référence fixe)
                            ref_value = ind.get("valeur_reference", None)
                            row.append(str(ref_value) if ref_value is not None else "-")
                            
                            # Cibles (utiliser les années dynamiques N, N+1, N+2)
                            cible_n = ind.get(f"cible_{annee_n}", None)
                            cible_n1 = ind.get(f"cible_{annee_n1}", None)
                            cible_n2 = ind.get(f"cible_{annee_n2}", None)
                            row.append(str(cible_n) if cible_n is not None else "-")
                            row.append(str(cible_n1) if cible_n1 is not None else "-")
                            row.append(str(cible_n2) if cible_n2 is not None else "-")
                            
                            # Mode de calcul
                            row.append(Paragraph(ind["mode_calcul"] or "", cell_style))
                            
                            # Source de vérification
                            row.append(Paragraph(ind["source_verification"] or "", cell_style))
                            
                            table_data.append(row)
                            row_index += 1
            
            # Créer le tableau avec des largeurs agrandies (après avoir traité tous les objectifs globaux)
            if len(table_data) > 1:  # Si on a au moins l'en-tête et une ligne de données
                    table = Table(table_data, colWidths=[
                        4*cm,  # Objectifs spécifiques (agrandi)
                        5*cm,  # Indicateurs (agrandi)
                        1.8*cm,  # Unité (agrandi)
                        2.5*cm,  # Situation de référence (année de référence) (agrandi)
                        1.8*cm,  # Cible N (agrandi)
                        1.8*cm,  # Cible N+1 (agrandi)
                        1.8*cm,  # Cible N+2 (agrandi)
                        3.5*cm,  # Mode de calcul (agrandi)
                        3*cm,  # Source (agrandi)
                    ])
                    
                    # Construire le style du tableau avec les fusions dynamiques
                    table_style = [
                        # Première ligne d'en-tête (ligne 0)
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fbbf24')),  # Jaune
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        
                        # Fusionner "Cibles" sur les colonnes 4, 5, 6 (ligne 0)
                        ('SPAN', (4, 0), (6, 0)),  # Fusionner Cibles sur 3 colonnes
                        
                        # Fusionner les cellules vides de la ligne 0 pour les colonnes qui n'ont pas besoin d'être séparées
                        ('SPAN', (0, 0), (0, 1)),  # Objectifs Spécifiques fusionné sur 2 lignes
                        ('SPAN', (1, 0), (1, 1)),  # Indicateurs fusionné sur 2 lignes
                        ('SPAN', (2, 0), (2, 1)),  # Unité fusionné sur 2 lignes
                        ('SPAN', (3, 0), (3, 1)),  # Situation de référence fusionné sur 2 lignes
                        ('SPAN', (7, 0), (7, 1)),  # Mode de calcul fusionné sur 2 lignes
                        ('SPAN', (8, 0), (8, 1)),  # Source fusionné sur 2 lignes
                        
                        # Deuxième ligne d'en-tête (ligne 1) - années des cibles
                        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fbbf24')),  # Jaune
                        ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
                        ('ALIGN', (4, 1), (6, 1), 'CENTER'),  # Centrer les années
                        ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
                        ('TOPPADDING', (0, 1), (-1, 1), 8),
                        
                        # Colonnes "Mode de calcul" et "Source" (vert) - pour les en-têtes
                        ('BACKGROUND', (7, 0), (8, 0), colors.HexColor('#10b981')),  # Vert pour l'en-tête ligne 1
                        ('BACKGROUND', (7, 1), (8, 1), colors.HexColor('#10b981')),  # Vert pour l'en-tête ligne 2
                        
                        # Bordures
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 3), (-1, -1), 'MIDDLE'),  # Alignement vertical au centre pour toutes les cellules de données (à partir de la ligne 3)
                        
                        # Alignement horizontal
                        ('ALIGN', (2, 3), (6, -1), 'CENTER'),  # Unité, référence et cibles centrées (à partir de la ligne 3)
                        ('ALIGN', (0, 3), (1, -1), 'LEFT'),  # Textes à gauche (à partir de la ligne 3)
                        ('ALIGN', (7, 3), (8, -1), 'LEFT'),  # Mode de calcul et source à gauche (à partir de la ligne 3)
                        
                        # Padding réduit pour les cellules de données (à partir de la ligne 2)
                        ('BOTTOMPADDING', (0, 2), (-1, -1), 4),
                        ('TOPPADDING', (0, 2), (-1, -1), 4),
                        ('LEFTPADDING', (0, 2), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 2), (-1, -1), 4),
                    ]
                    
                    # Ajouter les fusions pour les lignes de rappel des objectifs globaux
                    # On doit trouver toutes les lignes qui sont des rappels d'objectifs globaux
                    current_row = 2  # Commence après les deux lignes d'en-tête
                    for obj_global in programme_data["objectifs_globaux"]:
                        table_style.append(('SPAN', (0, current_row), (-1, current_row)))  # Fusionner toutes les colonnes
                        table_style.append(('BACKGROUND', (0, current_row), (-1, current_row), colors.HexColor('#fef3c7')))  # Jaune clair
                        table_style.append(('ALIGN', (0, current_row), (-1, current_row), 'LEFT'))
                        table_style.append(('BOTTOMPADDING', (0, current_row), (-1, current_row), 6))
                        table_style.append(('TOPPADDING', (0, current_row), (-1, current_row), 6))
                        current_row += 1
                        # Compter les lignes de données pour cet objectif global
                        for obj_spec in obj_global["objectifs_specifiques"]:
                            current_row += len(obj_spec["indicateurs"])
                    
                    # Ajouter les fusions pour les objectifs spécifiques qui ont plusieurs indicateurs
                    for row_start, row_end, obj_spec_titre in fusion_info:
                        if row_end > row_start:  # Fusionner seulement s'il y a plus d'une ligne
                            table_style.append(('SPAN', (0, row_start), (0, row_end)))  # Fusionner la colonne 0 (objectif spécifique)
                            table_style.append(('VALIGN', (0, row_start), (0, row_end), 'MIDDLE'))  # Alignement vertical au centre
                    
                    # Ajouter le style vert pour les colonnes Mode de calcul et Source (après les en-têtes)
                    # On doit trouver la première ligne de données (après tous les rappels d'objectifs globaux)
                    first_data_row = 2 + len(programme_data["objectifs_globaux"])  # Après les en-têtes et les rappels
                    table_style.append(('BACKGROUND', (7, first_data_row), (8, -1), colors.HexColor('#d1fae5')))  # Vert clair pour les données
                    
                    # Appliquer le style au tableau
                    table.setStyle(TableStyle(table_style))
                    
                    story.append(table)
                    story.append(Spacer(1, 0.5*cm))
            
            # Saut de page entre les programmes
            if programme_data != data["programmes"][-1]:
                story.append(PageBreak())
        
        # Construire le PDF
        doc.build(story)
        buffer.seek(0)
        
        logger.info(f"✅ PDF du cadre de performance généré")
        return buffer