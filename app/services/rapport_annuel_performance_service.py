from __future__ import annotations

import logging
import math
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame, Spacer, Table, LongTable, TableStyle, KeepTogether, CondPageBreak, Image, Flowable
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER

from app.core.path_config import path_config
from sqlmodel import Session, select, func
from decimal import Decimal
from reportlab.platypus import Frame
from reportlab.platypus.doctemplate import LayoutError


logger = logging.getLogger(__name__)



class RapportAnnuelPerformanceGenerator:
    """
    Générateur de rapport annuel de performance.
    Format : Paysage (Landscape A4)
    """

    PRIMARY_GREEN = colors.HexColor("#39791b")
    SECONDARY_GREEN = colors.HexColor("#609b4d")
    LIGHT_GREEN = colors.HexColor("#387722")
    
    PRIMARY_ORANGE = colors.HexColor("#F26D21")
    LIGHT_ORANGE = colors.HexColor("#ef9543")
    LIGHT_2_ORANGE = colors.HexColor("#ee863d")
    DARK_TEXT = colors.HexColor("#1F1F1F")
    
    # Couleurs pour le styling des sources de données
    COLOR_USER = colors.HexColor("#00AA00")  # Vert pour données utilisateur
    COLOR_DEFAULT = colors.HexColor("#FF0000")  # Rouge pour données par défaut
    COLOR_DB = colors.HexColor("#0066CC")  # Bleu pour données de la base de données
    
    # Variable de classe pour stocker la position de la ligne pointillée du bas
    _dotted_line_bottom_y: float | None = None
    
    # Variable de classe pour stocker les données par défaut originales (avant modification)
    _original_default_data: dict[str, Any] | None = None
    
    # Variable de classe pour stocker les données provenant de la DB
    _db_data_keys: set[str] = set()
    
    # Variable de classe pour stocker les clés des données fournies par l'utilisateur via le modal
    _user_data_keys: set[str] = set()
    
    # Variable de classe pour stocker la session de base de données
    _db_session: Session | None = None
    
    # ============================================================
    # FONCTIONS HELPER POUR LE STYLING DES DONNÉES
    # ============================================================
    
    @classmethod
    def _determine_data_source_for_canvas(cls, key: str, value: Any, db_value: Any = None, is_user_explicit: bool = False) -> tuple[Any, str]:
        """
        Détermine la source d'une donnée pour Canvas et retourne la valeur avec sa source.
        
        Priorité : USER (via modal) > DB > DEFAULT
        
        Args:
            key: Clé de la donnée
            value: Valeur actuelle dans cls.data
            db_value: Valeur provenant de la base de données (None si pas de valeur DB)
            is_user_explicit: True si la donnée est explicitement fournie par l'utilisateur via modal
            
        Returns:
            Tuple (valeur, source: "user", "db", ou "default")
        """
        # Priorité 1: USER (données fournies via modal)
        if is_user_explicit or key in cls._user_data_keys:
            logger.debug(f"🔍 Source déterminée pour '{key}': USER")
            return value, "user"
        
        # Priorité 2: DB (données provenant de la base de données)
        if key in cls._db_data_keys:
            logger.debug(f"🔍 Source déterminée pour '{key}': DB (clé dans _db_data_keys)")
            return value, "db"
        
        if db_value is not None and value == db_value:
            logger.debug(f"🔍 Source déterminée pour '{key}': DB (valeur correspond à db_value)")
            return value, "db"
        
        # Priorité 3: DEFAULT (données par défaut)
        logger.debug(f"🔍 Source déterminée pour '{key}': DEFAULT (pas dans _user_data_keys ni _db_data_keys)")
        return value, "default"
    
    @classmethod
    def _get_color_for_source(cls, source: str) -> colors.HexColor:
        """
        Retourne la couleur appropriée selon la source pour Canvas.
        
        Args:
            source: "user", "db", ou "default"
            
        Returns:
            Couleur HexColor appropriée
        """
        if source == "user":
            return cls.COLOR_USER
        elif source == "db":
            return cls.COLOR_DB  # Bleu pour données de la base de données
        else:  # default
            return cls.COLOR_DEFAULT
    
    @classmethod
    def _format_text_for_canvas(cls, pdf: canvas.Canvas, text: str, key: str, db_value: Any = None, x: float = 0, y: float = 0, centered: bool = False) -> None:
        """
        Dessine le texte avec la couleur appropriée selon sa source pour Canvas.
        
        Args:
            pdf: Canvas PDF
            text: Texte à dessiner
            key: Clé de la donnée
            db_value: Valeur provenant de la base de données
            x: Position X
            y: Position Y
            centered: Si True, dessine centré
        """
        value, source = cls._determine_data_source_for_canvas(key, text, db_value)
        color = cls._get_color_for_source(source)
        
        pdf.saveState()
        pdf.setFillColor(color)
        
        # Pour DB, on garde la couleur noire (sera bold+italique dans Paragraph)
        # Mais pour Canvas, on peut aussi mettre en italique/bold si nécessaire
        if source == "db":
            pdf.setFont("Helvetica-Bold", pdf._fontname, pdf._fontsize)
            # Note: Canvas ne supporte pas facilement l'italique, donc on garde bold seulement
        
        if centered:
            pdf.drawCentredString(x, y, text)
        else:
            pdf.drawString(x, y, text)
        
        pdf.restoreState()
    
    @staticmethod
    def _format_default_data(text: str) -> str:
        """Formate le texte pour les données par défaut (en rouge) - pour Paragraph."""
        return f'<font color="#FF0000">{text}</font>'
    
    @staticmethod
    def _format_db_data(text: str) -> str:
        """Formate le texte pour les données provenant de la base de données (en bleu, bold + italique) - pour Paragraph."""
        return f'<font color="#0066CC"><b><i>{text}</i></b></font>'
    
    @staticmethod
    def _format_user_data(text: str) -> str:
        """Formate le texte pour les données insérées par l'utilisateur (en vert) - pour Paragraph."""
        return f'<font color="#00AA00">{text}</font>'
    
    @classmethod
    def _format_data_by_source(cls, text: str, key: str, db_value: Any = None) -> str:
        """
        Formate le texte selon sa source pour Paragraph.
        
        Args:
            text: Texte à formater
            key: Clé de la donnée
            db_value: Valeur provenant de la base de données
            
        Returns:
            Texte formaté avec balises HTML selon la source
        """
        value, source = cls._determine_data_source_for_canvas(key, text, db_value)
        
        if source == "user":
            return cls._format_user_data(text)
        elif source == "db":
            return cls._format_db_data(text)
        else:  # default
            return cls._format_default_data(text)
    
    @classmethod
    def _format_data_value(cls, key: str, db_value: Any = None, default_value: Any = None) -> str:
        """
        Récupère une valeur depuis cls.data et retourne le texte formaté selon sa source pour Paragraph.
        
        Args:
            key: Clé de la donnée dans cls.data
            db_value: Valeur provenant de la base de données (optionnel)
            default_value: Valeur par défaut si absente (optionnel)
            
        Returns:
            Texte formaté avec balises HTML selon la source (USER > DB > DEFAULT)
        """
        value = cls.data.get(key, default_value)
        if value is None:
            return ""
        
        # Convertir en string si nécessaire
        text = str(value) if not isinstance(value, str) else value
        
        return cls._format_data_by_source(text, key, db_value)

    DEFAULT_DATA = {
        "annee": 2024,
        "pays": "République de Côte d'Ivoire",
        "devise": "Union – Discipline – Travail",
        "section": "SECTION 376",
        "ministere": "MINISTERE DU PATRIMOINE, DU PORTEFEUILLE DE L'ÉTAT ET DES ENTREPRISES PUBLIQUES",
        "titre_rapport": "RAPPORT ANNUEL DE PERFORMANCE DU MINISTERE DU PATRIMOINE DU PORTEFEUILLE DE L'ÉTAT ET DES ENTREPRISES PUBLIQUES",
        "titre_annee": "AU TITRE DE L'ANNÉE",
        "date_publication": "Mai 2025",
        "logo_path": "images/logo.webp",
        "programmes": [
            {
                "numero": 1,
                "titre": "ADMINISTRATION GÉNÉRALE",
                "page_debut": 13,
                "sections": [
                    {"titre": "INTRODUCTION", "page": 13},
                    {"titre": "I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", "page": 14},
                    {"titre": "II. RÉALISATIONS DU PROGRAMME « ADMINISTRATION GÉNÉRALE » AU COURS DE L'EXERCICE 2024", "page": 16},
                    {"titre": "III. PERFORMANCE DU PROGRAMME", "page": 24},
                    {"titre": "CONCLUSION", "page": 29},
                ]
            },
            {
                "numero": 2,
                "titre": "PORTEFEUILLE DE L'ÉTAT",
                "page_debut": 30,
                "sections": [
                    {"titre": "INTRODUCTION", "page": 30},
                    {"titre": "I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", "page": 31},
                    {"titre": "II. RÉALISATIONS DU PROGRAMME « PORTEFEUILLE DE L'ÉTAT » AU COURS DE L'EXERCICE 2024", "page": 33},
                    {"titre": "III. PERFORMANCE DU PROGRAMME", "page": 38},
                    {"titre": "IV. PERSPECTIVES", "page": 47},
                    {"titre": "CONCLUSION", "page": 48},
                ]
            },
        ],
        "tableaux": [
            {"numero": 1, "titre": "Composantes des cadres de performance du ministère", "page": 9},
            {"numero": 2, "titre": "Réalisations du cadre de performance du ministère", "page": 9},
            {"numero": 3, "titre": "Tableau présentant l'exécution du budget du ministère", "page": 12},
            {"numero": 4, "titre": "Exécution financière par action du programme 1", "page": 17},
            {"numero": 5, "titre": "Exécution des investissements du programme 1", "page": 19},
            {"numero": 6, "titre": "Exécution des prévisions d'effectifs du programme 1", "page": 22},
            {"numero": 7, "titre": "Évolution des indicateurs du programme 1", "page": 24},
            {"numero": 8, "titre": "Exécution financière par action du programme 2 « Portefeuille de l'Etat »", "page": 33},
            {"numero": 9, "titre": "Exécution des investissements du programme 2 « Portefeuille de l'Etat »", "page": 35},
            {"numero": 10, "titre": "Exécution des prévisions d'effectifs du Programme 2 « Portefeuille de l'Etat »", "page": 36},
            {"numero": 11, "titre": "Évolution des indicateurs du programme 2 « Portefeuille de l'Etat »", "page": 38},
        ],
        "graphiques": [
            {"numero": 1, "titre": "Répartition du budget actuel par natures de dépenses", "page": 11},
            {"numero": 2, "titre": "Répartition du budget actuel du programme 1 « Administration Générale » par nature de dépenses", "page": 16},
            {"numero": 3, "titre": "Evolution des taux d'exécution par action du Programme 1 « Administration Générale »", "page": 19},
            {"numero": 4, "titre": "Evolution des effectifs du Programme 1 « Administration Générale » par catégorie", "page": 22},
            {"numero": 5, "titre": "Répartition du budget actuel du Programme 2 « Portefeuille de l'Etat » par nature de dépenses", "page": 32},
            {"numero": 6, "titre": "Evolution de l'exécution budgétaire par action du Programme 2 « Portefeuille de l'Etat »", "page": 34},
            {"numero": 7, "titre": "Evolution des effectifs du Programme 2 « Portefeuille de l'Etat » de 2023 à 2024", "page": 36},
            {"numero": 8, "titre": "Evolution du taux d'exécution du PAS du programme PE de 2021 à 2024", "page": 39},
            {"numero": 9, "titre": "Evolution du Taux d'exécution du budget d'investissement du programme Portefeuille de l'Etat de 2021 à 2024", "page": 40},
            {"numero": 10, "titre": "Evolution du nombre d'études réalisées dans le cadre de la mise en œuvre de la stratégie 2021-2025 de gestion du portefeuille de l'Etat de 2022 à 2024", "page": 41},
            {"numero": 11, "titre": "Evolution du nombre de contrats de performance élaborés par la DGPE de 2021 à 2024", "page": 42},
            {"numero": 12, "titre": "Evolution du nombre d'entreprises publiques ayant procédé à la signature d'une lettre de mission entre le Conseil d'Administration et le Directeur Général de 2022 à 2024", "page": 43},
            {"numero": 13, "titre": "Evolution du taux de réalisation du plan d'audits des entreprises publiques de 2021 à 2024", "page": 45},
            {"numero": 14, "titre": "Evolution du taux de réalisation du plan de contrôles opérationnels des entreprises publiques de 2021 à 2024", "page": 46},
        ],
        "sigles": [
            {"sigle": "ADERIZ", "definition": "Agence pour le Développement de la Filière Riz"},
            {"sigle": "AFOR", "definition": "Agence Foncière Rurale"},
            {"sigle": "AG", "definition": "Administration Générale"},
            {"sigle": "AGEF", "definition": "Agence de Gestion Foncière"},
            {"sigle": "AIGF", "definition": "Agence Ivoirienne de Gestion des Fréquences radioélectriques"},
            {"sigle": "ANADER", "definition": "Agence Nationale d'Appui au Développement Rural"},
            {"sigle": "ANSUT", "definition": "Agence Nationale du Service Universel des Télécommunications"},
            {"sigle": "CNRA", "definition": "Centre National de Recherche Agronomique"},
            {"sigle": "DG", "definition": "Directeur Général"},
            {"sigle": "DGPE", "definition": "Direction Générale du Portefeuille de l'État"},
            {"sigle": "DPPD-PAP", "definition": "Document de Programmation Pluriannuelle de Dépenses – Projet Annuel de Performance"},
            {"sigle": "EPN", "definition": "Établissement Public Nationaux"},
            {"sigle": "FIDA", "definition": "Fonds International de Développement Agricole"},
            {"sigle": "GESTOCI", "definition": "Société de Gestion des Stocks Pétroliers de Côte d'Ivoire"},
            {"sigle": "GUCE-CI", "definition": "Guichet Unique du Commerce Extérieur de Côte d'Ivoire"},
            {"sigle": "I2T", "definition": "Institut Ivoirien de Technologie"},
            {"sigle": "IFRS", "definition": "International Financial Reporting Standards (Normes internationales d'information financière)"},
            {"sigle": "INIE", "definition": "Institut National Ivoirien de l'Entreprise"},
            {"sigle": "LONACI", "definition": "Loterie Nationale de Côte d'Ivoire"},
            {"sigle": "MBPE", "definition": "Ministère du Budget et du Portefeuille de l'État"},
            {"sigle": "MPPEEP", "definition": "Ministère du Patrimoine, du Portefeuille de l'État et des Entreprises Publiques"},
            {"sigle": "OIC", "definition": "Office Ivoirien des Chargeurs"},
            {"sigle": "ONEP", "definition": "Office National de l'Eau Potable"},
            {"sigle": "PAS", "definition": "Programme d'Actions Stratégiques"},
            {"sigle": "PCA", "definition": "Président du Conseil d'Administration"},
            {"sigle": "PCI", "definition": "Patrimoine Culturel Immatériel"},
            {"sigle": "PETROCI", "definition": "Société Nationale d'Opérations Pétrolières de Côte d'Ivoire"},
            {"sigle": "PND", "definition": "Plan National de Développement"},
            {"sigle": "PTA", "definition": "Plan de Travail Annuel"},
            {"sigle": "RAP", "definition": "Rapport Annuel de Performance"},
            {"sigle": "RFFIM", "definition": "Responsable de la Fonction Financière Ministérielle"},
            {"sigle": "RProg", "definition": "Responsable de Programme"},
            {"sigle": "SGMT", "definition": "Société de Gestion du Grand Marché de Treichville"},
            {"sigle": "SIPF", "definition": "Société Ivoirienne de gestion du Patrimoine Ferroviaire"},
            {"sigle": "SNDI", "definition": "Système National de Développement de l'Information"},
            {"sigle": "SOCITA", "definition": "Société de Transformation Agricole"},
            {"sigle": "SODEFOR", "definition": "Société de Développement des Forêts"},
            {"sigle": "SODEMI", "definition": "Société pour le Développement Minier de la Côte d'Ivoire"},
            {"sigle": "SODEXA", "definition": "Société d'Exploitation et de Développement Aéroportuaire, Aéronautique et Météorologique"},
            {"sigle": "SOGEDI", "definition": "Société de Gestion et de Développement des Infrastructures Industrielles"},
            {"sigle": "SONAPIE", "definition": "Société Nationale de Gestion du Patrimoine Immobilier de l'État"},
            {"sigle": "SOTRA", "definition": "Société des Transports Abidjanais"},
        ],
        "introduction": {
            "ministre_nom": "Monsieur Moussa SANOGO",
            "ministre_date_nomination": "17 octobre 2023",
            "decret_attribution_numero": "n° 2023-820",
            "decret_attribution_date": "25 octobre 2023",
            "mission_ministere": "mettre en œuvre la politique du Gouvernement en matière de gestion du patrimoine, du portefeuille de l'État et des entreprises publiques",
            "structure_cabinet": "Cabinet du Ministre",
            "structure_directions_centrales": 3,
            "structure_services": 5,
            "structure_directions_generales": 2,
            "decret_organisation_numero": "n° 2023-963",
            "decret_organisation_date": "6 décembre 2023",
            "contexte_texte": (
                "Les activités de l'année {annee} se sont déroulées dans un contexte marqué par la réorganisation "
                "institutionnelle et la consolidation des acquis. À sa création, le {ministere} a hérité de programmes "
                "tels que « Administration Générale » et « Portefeuille de l'État », initialement gérés par l'ancien "
                "Ministère du Budget et du Portefeuille de l'État (MBPE). Cette transition a nécessité une reconfiguration "
                "progressive de l'organisation administrative du ministère et des instruments de gestion. À cet égard, "
                "le décret {decret_organisation_numero} du {decret_organisation_date} a été adopté pour affiner "
                "l'architecture institutionnelle du {ministere}, permettant ainsi la poursuite et la structuration des réformes entreprises."
            ),
            "rapport_structure_premiere_partie": [
                "faire la présentation générale des programmes du ministère",
                "rappeler la performance générale et le financement global du ministère"
            ],
            "rapport_structure_seconde_partie": [
                "la présentation de la stratégie du programme",
                "les réalisations du programme au cours de l'exercice {annee}",
                "la performance du programme",
                "les perspectives"
            ],
        },
    }

    @staticmethod
    def _resolve_asset_path(raw_path: str | None) -> str | None:
        """Résout un chemin relatif vers un chemin absolu."""
        if not raw_path:
            return None
        
        # Si le chemin est absolu et existe, le retourner tel quel
        candidate = Path(raw_path)
        if candidate.is_absolute() and candidate.exists():
            return str(candidate)
        
        # Normaliser le chemin en enlevant le slash initial
        normalized = raw_path.lstrip("/")
        
        # Vérifier selon le préfixe du chemin
        if normalized.startswith("static/"):
            static_path = path_config.get_physical_path("static", normalized[len("static/"):])
            if static_path.exists():
                return str(static_path)
        elif normalized.startswith("uploads/"):
            uploads_path = path_config.get_physical_path("uploads", normalized[len("uploads/"):])
            if uploads_path.exists():
                return str(uploads_path)
        elif normalized.startswith("media/"):
            media_path = path_config.get_physical_path("media", normalized[len("media/"):])
            if media_path.exists():
                return str(media_path)
        
        # Fallback : chercher dans STATIC_DIR
        fallback = path_config.STATIC_DIR / normalized
        if fallback.exists():
            return str(fallback)
        
        # Fallback supplémentaire : chercher dans STATIC_IMAGES_DIR si le chemin commence par "images/"
        if normalized.startswith("images/"):
            images_path = path_config.STATIC_IMAGES_DIR / normalized[len("images/"):]
            if images_path.exists():
                return str(images_path)
        
        return None

    @classmethod
    def load_system_settings_data(cls, session: Session | None) -> dict[str, Any]:
        """
        Charge les données depuis SystemSettings et les marque comme DB.
        
        Args:
            session: Session de base de données
            
        Returns:
            Dictionnaire contenant les données DB récupérées
        """
        db_data: dict[str, Any] = {}
        
        if not session:
            logger.warning("⚠️ Pas de session DB, impossible de charger SystemSettings")
            return db_data
        
        try:
            from app.services.system_settings_service import SystemSettingsService
            from app.db.session import engine
            from sqlmodel import Session as SQLModelSession
            
            # Essayer avec la session fournie
            settings = None
            try:
                settings = SystemSettingsService.get_settings(session)
            except Exception as session_error:
                logger.warning(f"⚠️ Erreur avec la session fournie: {session_error}, création d'une nouvelle session...")
                # Créer une nouvelle session propre pour récupérer SystemSettings
                try:
                    with SQLModelSession(engine) as new_session:
                        settings = SystemSettingsService.get_settings(new_session)
                        logger.info("✅ SystemSettings récupéré avec une nouvelle session")
                except Exception as new_session_error:
                    logger.error(f"❌ Impossible de récupérer SystemSettings même avec une nouvelle session: {new_session_error}")
                    return db_data
            if not settings:
                logger.warning("⚠️ SystemSettings non trouvé dans la base de données")
                return db_data
            
            logger.info(f"✅ SystemSettings récupéré: minister_role={settings.minister_role[:50] if settings.minister_role else None}, minister_name={settings.minister_name}, ministry_mission={settings.ministry_mission[:50] if settings.ministry_mission else None}")
            
            # 1. Nom du ministère : peut provenir de minister_role ou company_name
            if settings.minister_role:
                # Extraire le nom du ministère depuis minister_role
                minister_role_upper = settings.minister_role.upper().strip()
                if "MINISTRE" in minister_role_upper or "MINISTERE" in minister_role_upper:
                    ministere_name = minister_role_upper.replace("MINISTRE", "MINISTERE")
                    ministere_name = re.sub(r'\s+', ' ', ministere_name).strip()
                    db_data["ministere"] = ministere_name
                    cls._db_data_keys.add("ministere")
                    logger.debug(f"✅ Nom du ministère récupéré depuis minister_role: {ministere_name[:50]}...")
            
            # Si company_name contient le nom du ministère, l'utiliser aussi (si pas déjà récupéré)
            if not db_data.get("ministere") and settings.company_name:
                company_name_upper = settings.company_name.upper().strip()
                if "MINISTERE" in company_name_upper or "MPPEEP" in company_name_upper:
                    db_data["ministere"] = company_name_upper
                    cls._db_data_keys.add("ministere")
                    logger.debug(f"✅ Nom du ministère récupéré depuis company_name: {company_name_upper[:50]}...")
            
            # 2. Logo path
            if settings.logo_path:
                db_data["logo_path"] = settings.logo_path
                cls._db_data_keys.add("logo_path")
                logger.debug(f"✅ Logo path récupéré depuis SystemSettings: {settings.logo_path}")
            
            # 3. Données d'introduction
            intro_data: dict[str, Any] = {}
            
            # Nom du ministre
            if settings.minister_civility and settings.minister_name:
                intro_data["ministre_nom"] = f"{settings.minister_civility} {settings.minister_name}"
            elif settings.minister_name:
                intro_data["ministre_nom"] = settings.minister_name
            
            # Mission du ministère
            if settings.ministry_mission:
                intro_data["mission_ministere"] = settings.ministry_mission
            
            # Stocker les données d'introduction
            if intro_data:
                db_data["introduction"] = intro_data
                # Marquer chaque clé comme provenant de la DB
                for key in intro_data:
                    cls._db_data_keys.add(f"introduction.{key}")
                    logger.debug(f"✅ Donnée DB récupérée: introduction.{key} = {intro_data[key][:50]}...")
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Impossible de récupérer les données depuis SystemSettings: {error_msg}")
            logger.debug(f"   Type d'erreur: {type(e).__name__}")
            # Si c'est une erreur de transaction, on peut essayer de rollback
            if "transaction" in error_msg.lower() or "InFailedSqlTransaction" in error_msg:
                logger.warning("   💡 Erreur de transaction détectée, les données DB ne seront pas chargées")
            import traceback
            logger.debug(f"   Traceback: {traceback.format_exc()}")
        
        return db_data

    @classmethod
    def load_budget_data(cls, session: Session | None, annee: int) -> dict[str, Any]:
        """
        Charge les données budgétaires depuis la base de données pour enrichir le RAP.
        """
        if not session:
            return {}
        
        try:
            from app.models.budget import ExecutionBudgetaire, ActionBudgetaire, ActiviteBudgetaire, FicheTechnique
            from app.models.personnel import Programme
            
            budget_data: dict[str, Any] = {}
            
            # 1. Charger les programmes et compter les actions/activités
            programmes_query = select(Programme).where(Programme.actif).order_by(Programme.code)
            programmes = session.exec(programmes_query).all()
            
            programmes_list = []
            total_actions = 0
            total_activites = 0
            
            for prog in programmes:
                # Compter les actions budgétaires pour ce programme
                actions_count = session.exec(
                    select(func.count(ActionBudgetaire.id))
                    .join(FicheTechnique, ActionBudgetaire.fiche_technique_id == FicheTechnique.id)
                    .where(FicheTechnique.programme_id == prog.id)
                    .where(FicheTechnique.annee_budget == annee)
                ).first() or 0
                
                # Compter les activités budgétaires pour ce programme
                activites_count = session.exec(
                    select(func.count(ActiviteBudgetaire.id))
                    .join(FicheTechnique, ActiviteBudgetaire.fiche_technique_id == FicheTechnique.id)
                    .where(FicheTechnique.programme_id == prog.id)
                    .where(FicheTechnique.annee_budget == annee)
                ).first() or 0
                
                total_actions += actions_count
                total_activites += activites_count
                
                programmes_list.append({
                    "numero": len(programmes_list) + 1,
                    "titre": prog.libelle or prog.code,
                    "nb_actions": actions_count,
                    "nb_activites": activites_count,
                })
            
            budget_data["programmes"] = programmes_list
            budget_data["total_programmes"] = len(programmes_list)
            budget_data["total_actions"] = total_actions
            budget_data["total_activites"] = total_activites
            
            # 2. Charger les données d'exécution budgétaire pour l'année
            exec_budgetaires = session.exec(
                select(ExecutionBudgetaire)
                .where(ExecutionBudgetaire.annee == annee)
            ).all()
            
            if exec_budgetaires:
                # Agrégations globales
                total_budget_vote = sum(float(ex.budget_vote) for ex in exec_budgetaires)
                total_engagements = sum(float(ex.engagements) for ex in exec_budgetaires)
                total_mandats_pec = sum(float(ex.mandats_pec) for ex in exec_budgetaires)
                
                # Calculer les taux moyens
                taux_engagement_avg = (total_engagements / total_budget_vote * 100) if total_budget_vote > 0 else 0
                taux_mandatement_avg = (total_mandats_pec / total_budget_vote * 100) if total_budget_vote > 0 else 0
                taux_execution_avg = taux_mandatement_avg  # Utiliser le taux de mandatement comme taux d'exécution
                
                budget_data["execution"] = {
                    "total_budget_vote": total_budget_vote,
                    "total_engagements": total_engagements,
                    "total_mandats_pec": total_mandats_pec,
                    "taux_engagement": taux_engagement_avg,
                    "taux_mandatement": taux_mandatement_avg,
                    "taux_execution": taux_execution_avg,
                }
                
                # 2.1. Charger les données par nature de dépense pour le financement global
                from app.models.budget import NatureDepense, SigobeExecution, SigobeChargement
                
                # Essayer d'abord avec SigobeExecution (plus précis)
                dernier_chargement = session.exec(
                    select(SigobeChargement)
                    .where(SigobeChargement.annee == annee)
                    .order_by(SigobeChargement.date_chargement.desc())
                ).first()
                
                financement_par_nature = {}
                budget_initial_total_sigobe = 0
                budget_reel_total_sigobe = 0
                
                if dernier_chargement:
                    sigobe_executions = session.exec(
                        select(SigobeExecution)
                        .where(SigobeExecution.chargement_id == dernier_chargement.id)
                    ).all()
                    
                    # Grouper par nature de dépense (type_depense dans SigobeExecution)
                    depenses_par_type = {}
                    for exec_sigobe in sigobe_executions:
                        type_dep = exec_sigobe.type_depense or "INCONNU"
                        if type_dep not in depenses_par_type:
                            depenses_par_type[type_dep] = {
                                "budget_vote": 0,
                                "budget_actuel": 0,
                            }
                        
                        depenses_par_type[type_dep]["budget_vote"] += float(exec_sigobe.budget_vote or 0)
                        depenses_par_type[type_dep]["budget_actuel"] += float(exec_sigobe.budget_actuel or 0)
                    
                    # Mapper les types SIGOBE vers les codes de nature
                    mapping_types = {
                        "PERSONNEL": "P",
                        "P": "P",
                        "BIENS ET SERVICES": "BS",
                        "BS": "BS",
                        "TRANSFERTS": "T",
                        "T": "T",
                        "INVESTISSEMENTS": "I",
                        "I": "I",
                    }
                    
                    natures = {n.code: n for n in session.exec(select(NatureDepense)).all()}
                    
                    for type_dep, montants in depenses_par_type.items():
                        # Trouver le code de nature correspondant
                        code_nature = None
                        for key, code in mapping_types.items():
                            if key in type_dep.upper():
                                code_nature = code
                                break
                        
                        if not code_nature:
                            continue
                        
                        budget_initial = montants["budget_vote"]
                        budget_reel = montants["budget_actuel"]
                        
                        budget_initial_total_sigobe += budget_initial
                        budget_reel_total_sigobe += budget_reel
                        
                        nature_obj = natures.get(code_nature)
                        libelle = nature_obj.libelle if nature_obj else type_dep
                        
                        financement_par_nature[code_nature] = {
                            "libelle": libelle,
                            "budget_initial": budget_initial,
                            "budget_reel": budget_reel,
                            "evolution": budget_reel - budget_initial,
                            "taux_evolution": ((budget_reel - budget_initial) / budget_initial * 100) if budget_initial > 0 else 0,
                        }
                
                # Si pas de données SIGOBE, utiliser ExecutionBudgetaire
                if not financement_par_nature:
                    natures = {n.id: n for n in session.exec(select(NatureDepense)).all()}
                    
                    for nature_id, nature in natures.items():
                        exec_nature = [ex for ex in exec_budgetaires if ex.nature_depense_id == nature_id]
                        if exec_nature:
                            budget_initial = sum(float(ex.budget_vote) for ex in exec_nature)
                            budget_reel = sum(float(ex.budget_vote) for ex in exec_nature)
                            
                            financement_par_nature[nature.code] = {
                                "libelle": nature.libelle,
                                "budget_initial": budget_initial,
                                "budget_reel": budget_reel,
                                "evolution": budget_reel - budget_initial,
                                "taux_evolution": ((budget_reel - budget_initial) / budget_initial * 100) if budget_initial > 0 else 0,
                            }
                    
                    budget_initial_total_sigobe = total_budget_vote
                    budget_reel_total_sigobe = total_budget_vote
                
                evolution_total_sigobe = budget_reel_total_sigobe - budget_initial_total_sigobe
                taux_evolution_total_sigobe = (evolution_total_sigobe / budget_initial_total_sigobe * 100) if budget_initial_total_sigobe > 0 else 0
                
                budget_data["financement_global"] = {
                    "budget_initial_total": budget_initial_total_sigobe if budget_initial_total_sigobe > 0 else total_budget_vote,
                    "budget_reel_total": budget_reel_total_sigobe if budget_reel_total_sigobe > 0 else total_budget_vote,
                    "evolution_total": evolution_total_sigobe if budget_initial_total_sigobe > 0 else 0,
                    "taux_evolution_total": taux_evolution_total_sigobe if budget_initial_total_sigobe > 0 else 0,
                    "par_nature": financement_par_nature,
                }
            
            # 3. Charger les données de performance (objectifs et indicateurs)
            from app.models.performance import ObjectifPerformance, IndicateurPerformance, StatutObjectif
            from sqlalchemy.exc import ProgrammingError
            
            # Compter les objectifs globaux et spécifiques
            # Les objectifs globaux sont généralement ceux de type STRATEGIQUE
            # Les objectifs spécifiques sont ceux de type OPERATIONNEL
            nb_objectifs_globaux = 0
            nb_objectifs_specifiques = 0
            nb_indicateurs = 0
            cibles_atteintes = 0
            
            try:
                objectifs_globaux = session.exec(
                    select(ObjectifPerformance).where(ObjectifPerformance.type_objectif == "STRATEGIQUE")
                ).all()
                
                objectifs_specifiques = session.exec(
                    select(ObjectifPerformance).where(ObjectifPerformance.type_objectif == "OPERATIONNEL")
                ).all()
                
                nb_objectifs_globaux = len(objectifs_globaux)
                nb_objectifs_specifiques = len(objectifs_specifiques)
                
                # Compter les indicateurs - gérer le cas où objectif_id n'existe pas encore
                try:
                    indicateurs = session.exec(
                        select(IndicateurPerformance).where(IndicateurPerformance.actif)
                    ).all()
                    nb_indicateurs = len(indicateurs)
                    
                    # Compter les cibles atteintes (indicateurs avec valeur_actuelle >= valeur_cible)
                    for ind in indicateurs:
                        if ind.valeur_actuelle and ind.valeur_cible:
                            if float(ind.valeur_actuelle) >= float(ind.valeur_cible):
                                cibles_atteintes += 1
                except (ProgrammingError, AttributeError) as ind_error:
                    logger.warning(f"⚠️ Erreur lors du chargement des indicateurs (colonne manquante ?): {ind_error}")
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    nb_indicateurs = 0
                    cibles_atteintes = 0
                    
            except Exception as perf_error:
                logger.warning(f"⚠️ Erreur lors du chargement des données de performance: {perf_error}")
                try:
                    session.rollback()
                except Exception:
                    pass
            
            nb_cibles = nb_indicateurs  # Une cible par indicateur
            
            # Calculer le taux de réalisation
            taux_realisation = (cibles_atteintes / nb_cibles * 100) if nb_cibles > 0 else 0
            
            # Préparer les données de performance
            budget_data["performance"] = {
                "architecture": {
                    "nb_programmes": budget_data.get("total_programmes", 0),
                    "nb_objectifs_globaux": nb_objectifs_globaux,
                    "nb_objectifs_specifiques": nb_objectifs_specifiques,
                    "nb_indicateurs": nb_indicateurs,
                    "nb_cibles": nb_cibles,
                },
                "taux_realisation": round(taux_realisation, 2),
                "nb_cibles_atteintes": cibles_atteintes,
                "nb_indicateurs_2023": nb_indicateurs,  # Par défaut, on peut améliorer en chargeant l'année précédente
                "taux_realisation_2023": taux_realisation,  # Par défaut
            }
            
            # Préparer les réalisations par programme (basé sur les objectifs)
            realisations = []
            for prog in programmes_list:
                prog_num = prog.get("numero", 0)
                prog_titre = prog.get("titre", "")
                
                # Pour chaque programme, compter les objectifs spécifiques atteints
                # (On suppose que les objectifs sont liés aux programmes via une relation future)
                # Pour l'instant, on crée une entrée par programme
                objectifs_prog = session.exec(
                    select(ObjectifPerformance).where(ObjectifPerformance.type_objectif == "OPERATIONNEL")
                ).first()
                
                if objectifs_prog:
                    # Compter les indicateurs liés à cet objectif
                    try:
                        indicateurs_os = session.exec(
                            select(IndicateurPerformance).where(IndicateurPerformance.objectif_id == objectifs_prog.id)
                        ).all()
                        
                        nb_cibles_os = len(indicateurs_os)
                        nb_cibles_atteintes_os = sum(
                            1 for ind in indicateurs_os
                            if ind.valeur_actuelle and ind.valeur_cible and float(ind.valeur_actuelle) >= float(ind.valeur_cible)
                        )
                        
                        if nb_cibles_os > 0:
                            realisations.append({
                                "programme": f"P{prog_num}: {prog_titre}",
                                "objectif_specifique": f"OS {prog_num}: Améliorer...",  # À améliorer avec les vraies données
                                "nb_cibles": nb_cibles_os,
                                "nb_cibles_atteintes": nb_cibles_atteintes_os,
                            })
                    except (ProgrammingError, AttributeError) as os_error:
                        logger.warning(f"⚠️ Erreur lors du chargement des indicateurs pour l'objectif (colonne objectif_id manquante ?): {os_error}")
                        try:
                            session.rollback()
                        except Exception:
                            pass
                        # Ignorer cette erreur et continuer avec le programme suivant
                        pass
            
            if realisations:
                budget_data["performance"]["realisations"] = realisations
            
            logger.info(f"✅ Données budgétaires chargées: {len(programmes_list)} programmes, {total_actions} actions, {total_activites} activités")
            logger.info(f"✅ Données de performance chargées: {nb_objectifs_globaux} OG, {nb_objectifs_specifiques} OS, {nb_indicateurs} indicateurs")
            return budget_data
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données budgétaires: {e}", exc_info=True)
            return {}
    
    @classmethod
    def generate_pdf(cls, data: dict[str, Any], session: Session | None = None) -> BytesIO:
        """Génère le PDF du rapport annuel de performance."""
        logger.info("🚀 DÉBUT génération PDF rapport annuel de performance")
        
        # Sauvegarder les données par défaut pour comparaison
        cls._original_default_data = cls.DEFAULT_DATA.copy()
        
        # Initialiser les sets pour tracker les sources de données
        cls._user_data_keys = set()
        cls._db_data_keys = set()
        
        # Stocker la session pour utilisation dans les méthodes de dessin
        cls._db_session = session
        
        # ⚠️ IMPORTANT : Charger les données DB AVANT de marquer les données USER
        # pour que la priorité USER > DB soit respectée
        db_data = cls.load_system_settings_data(session)
        logger.info(f"📊 Données DB chargées: {list(db_data.keys())}")
        logger.info(f"📊 Clés marquées comme DB: {list(cls._db_data_keys)}")
        
        # Identifier les clés USER (fournies via modal, présentes dans data mais différentes de DEFAULT_DATA)
        user_data = data or {}
        for key, value in user_data.items():
            default_value = cls.DEFAULT_DATA.get(key)
            if default_value is None or value != default_value:
                # Si la valeur diffère de la valeur par défaut, c'est une donnée USER
                cls._user_data_keys.add(key)
        
        logger.info(f"📊 Clés marquées comme USER: {list(cls._user_data_keys)}")
        
        # Fusionner les données dans l'ordre de priorité : DEFAULT < DB < USER
        # L'ordre de fusion garantit que USER écrase DB et DB écrase DEFAULT
        cls.data = {**cls.DEFAULT_DATA, **db_data, **user_data}
        
        # Fusionner aussi les données d'introduction si présentes
        if "introduction" in db_data:
            if "introduction" not in cls.data:
                cls.data["introduction"] = {}
            cls.data["introduction"] = {**cls.data.get("introduction", {}), **db_data["introduction"]}
        
        logger.info(f"📊 Données finales dans cls.data: ministere={cls.data.get('ministere', 'N/A')[:50]}, logo_path={cls.data.get('logo_path', 'N/A')}")
        
        # Charger les données budgétaires si une session est fournie
        annee = cls.data.get("annee", 2024)
        budget_data = cls.load_budget_data(session, annee)
        
        # Fusionner les données budgétaires dans cls.data
        if budget_data:
            # Mettre à jour les programmes si disponibles
            if "programmes" in budget_data and budget_data["programmes"]:
                cls.data["programmes"] = budget_data["programmes"]
            
            # Mettre à jour partie_ministere avec les données réelles
            if "partie_ministere" not in cls.data:
                cls.data["partie_ministere"] = {}
            
            partie_ministere = cls.data["partie_ministere"]
            if "total_programmes" in budget_data:
                partie_ministere["total_programmes"] = budget_data["total_programmes"]
            if "total_actions" in budget_data:
                partie_ministere["total_actions"] = budget_data["total_actions"]
            if "total_activites" in budget_data:
                partie_ministere["total_activites"] = budget_data["total_activites"]
            
            # Mettre à jour programme_details
            if "programmes" in budget_data:
                programme_details = []
                for prog in budget_data["programmes"]:
                    programme_details.append({
                        "numero": prog.get("numero", 0),
                        "titre": prog.get("titre", ""),
                        "actions": prog.get("nb_actions", 0),
                        "activites": prog.get("nb_activites", 0),
                    })
                partie_ministere["programme_details"] = programme_details
                
                # Calculer les pourcentages
                total_activites = partie_ministere.get("total_activites", 0)
                if total_activites > 0 and len(programme_details) > 0:
                    for i, prog in enumerate(programme_details):
                        pct_key = f"prog{i+1}_pct"
                        pct_value = (prog["activites"] / total_activites * 100) if total_activites > 0 else 0
                        partie_ministere[pct_key] = pct_value
            
            cls.data["partie_ministere"] = partie_ministere
            
            # Mettre à jour les données de financement global
            if "financement_global" in budget_data:
                cls.data["financement_global"] = budget_data["financement_global"]
            
            # Mettre à jour les données de performance
            if "performance" in budget_data:
                # Fusionner les données de performance (architecture, réalisations, taux)
                if "performance" not in cls.data:
                    cls.data["performance"] = {}
                
                perf_data = cls.data["performance"]
                budget_perf = budget_data["performance"]
                
                # Fusionner l'architecture de performance
                if "architecture" in budget_perf:
                    perf_data["architecture"] = budget_perf["architecture"]
                
                # Fusionner les réalisations
                if "realisations" in budget_perf:
                    perf_data["realisations"] = budget_perf["realisations"]
                
                # Fusionner les taux
                if "taux_realisation" in budget_perf:
                    perf_data["taux_realisation"] = budget_perf["taux_realisation"]
                if "nb_cibles_atteintes" in budget_perf:
                    perf_data["nb_cibles_atteintes"] = budget_perf["nb_cibles_atteintes"]
                if "nb_indicateurs_2023" in budget_perf:
                    perf_data["nb_indicateurs_2023"] = budget_perf["nb_indicateurs_2023"]
                if "taux_realisation_2023" in budget_perf:
                    perf_data["taux_realisation_2023"] = budget_perf["taux_realisation_2023"]
                
                cls.data["performance"] = perf_data
        
        buffer = BytesIO()
        # Mode paysage : inverser width et height
        pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
        width, height = landscape(A4)  # width > height en paysage
        
        logger.info("📄 Page 1: Couverture")
        # Ordre des appels détermine la superposition des éléments
        cls._draw_background_shapes(pdf, width, height)
        cls._draw_header(pdf, width, height)
        cls._draw_cover_block(pdf, width, height)
        cls._draw_footer(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Page 2+: Sommaire")
        next_page = cls._draw_table_of_contents(pdf, width, height)

        logger.info(f"📄 Page {next_page}+: Liste des tableaux")
        next_page = cls._draw_liste_tableaux(pdf, width, height, next_page)

        logger.info(f"📄 Page {next_page}+: Liste des graphiques")
        next_page = cls._draw_liste_graphiques(pdf, width, height, next_page)

        logger.info(f"📄 Page {next_page}+: Sigles et abréviations")
        next_page = cls._draw_liste_sigles_abreviations(pdf, width, height, next_page)

        logger.info(f"📄 Page {next_page}+: Introduction générale")
        next_page = cls._draw_introduction_generale(pdf, width, height, next_page)

        # PARTIE I : LE MINISTÈRE (commence sur une nouvelle page)
        pdf.showPage()
        next_page += 1  # La page suivante après l'introduction
        logger.info(f"📄 Page {next_page}: PARTIE I : LE MINISTÈRE")
        next_page = cls._draw_partie_i_ministere(pdf, width, height, next_page)

        # PARTIE II, III, etc. : Les programmes (chaque partie commence sur une nouvelle page)
        programmes = cls.data.get("programmes", [])
        if not programmes:
            programmes = cls.DEFAULT_DATA.get("programmes", [])
        
        for programme in programmes:
            pdf.showPage()  # Nouvelle page avant chaque partie
            next_page += 1  # La page suivante
            numero = programme.get("numero", 1)
            titre = programme.get("titre", "")
            logger.info(f"📄 Page {next_page}: PARTIE {numero + 1} : LE PROGRAMME {numero} « {titre.upper()} »")
            next_page = cls._draw_partie_programme(pdf, width, height, next_page, programme)

        logger.info("💾 Sauvegarde du PDF...")
        pdf.save()
        buffer.seek(0)
        return buffer

    @classmethod
    def _draw_background_shapes(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine les éléments décoratifs de fond (triangles, bandes, lignes)."""

        # ---------- TRIANGLE ----------
        pdf.saveState()
        tri = pdf.beginPath()
        tri.moveTo(width, height)
        tri.lineTo(width, height - 140)
        tri.lineTo(width - 220, height)
        tri.close()
        pdf.setFillColor(cls.PRIMARY_GREEN)
        pdf.drawPath(tri, stroke=0, fill=1)

        # ---------- GÉOMÉTRIE HYPOTÉNUSE ----------
        start_x, start_y = width,        height - 140
        end_x,   end_y   = width - 220,  height

        dx, dy = end_x - start_x, end_y - start_y
        L = (dx*dx + dy*dy) ** 0.5
        if L == 0:
            pdf.restoreState()
            return  # sécurité

        ux, uy = dx / L, dy / L
        # Normale pointant VERS l'intérieur du triangle (haut-droite ici)
        nx, ny = (uy, -ux)

        def pt_on_segment(t: float):
            return (start_x + t*dx, start_y + t*dy)

        def offset_point(pt, d: float):
            return (pt[0] + nx*d, pt[1] + ny*d)

        def draw_band_center(c_px, length_px, offset_px, thickness,
                     round_start=True, round_end=True,
                     extend_start_px=0, extend_end_px=0,
                     color=None, reverse=False, clamp=False):
            """
            c_px        : position du CENTRE le long de l'hypoténuse (en points)
            length_px   : longueur de la bande (en points)
            offset_px   : écart perpendiculaire à l'hypoténuse
            thickness   : épaisseur visuelle
            """
            s_px = c_px - (length_px / 2.0)     # convertit centre -> début
            draw_band_slide(
                s_px=s_px, length_px=length_px, offset_px=offset_px, thickness=thickness,
                round_start=round_start, round_end=round_end,
                extend_start_px=extend_start_px, extend_end_px=extend_end_px,
                color=color, reverse=reverse, clamp=clamp
            )

        def draw_band_slide(s_px, length_px, offset_px, thickness,
                    round_start=False, round_end=False,
                    extend_start_px=0, extend_end_px=0,
                    color=None, reverse=False, clamp=False):
            """
            Bande 'capsule' placée par:
            - s_px       : position du DÉBUT le long de l'hypoténuse (en points)
            - length_px  : longueur de la bande le long de l'hypoténuse (en points)
            - offset_px  : distance perpendiculaire à l'hypoténuse (positif = vers l'intérieur du triangle si nx,ny sont corrects)
            - thickness  : épaisseur visuelle de la bande
            Options:
            - round_start / round_end : bouts arrondis sélectifs
            - extend_*_px            : prolonger/raccourcir indépendamment chaque extrémité
            - color                  : couleur de remplissage
            - reverse=True           : mesure s_px depuis END au lieu de START
            - clamp=True             : borne dans [0, L]
            Nécessite : start_x,start_y,end_x,end_y, ux,uy, nx,ny, L déjà calculés.
            """
            # Choix de l'ancrage (départ du repère s=0)
            if not reverse:
                ax, ay = start_x, start_y
                dirx, diry = ux, uy
            else:
                ax, ay = end_x, end_y
                dirx, diry = -ux, -uy

            # Distances le long de l'hypoténuse
            a0 = s_px - extend_start_px
            a1 = s_px + length_px + extend_end_px

            if clamp:
                a0 = max(0.0, min(L, a0))
                a1 = max(0.0, min(L, a1))

            # Points centraux sur la ligne, puis décalés perpendiculairement
            cx0, cy0 = ax + dirx * a0, ax*0 + ay + diry * a0  # (astuce pour lisibilité)
            cx1, cy1 = ax + dirx * a1, ax*0 + ay + diry * a1

            # Décalage perpendiculaire (normale) pour créer l'espace avec l'hypoténuse
            rx_n, ry_n = nx * offset_px, ny * offset_px
            x0, y0 = cx0 + rx_n, cy0 + ry_n
            x1, y1 = cx1 + rx_n, cy1 + ry_n

            # "Capsule" (rectangle + cercles)
            r = thickness / 2.0
            rx, ry = nx * r, ny * r

            path = pdf.beginPath()
            path.moveTo(x0 - rx, y0 - ry)
            path.lineTo(x1 - rx, y1 - ry)
            path.lineTo(x1 + rx, y1 + ry)
            path.lineTo(x0 + rx, y0 + ry)
            path.close()

            pdf.saveState()
            if color is not None:
                pdf.setFillColor(color)
            pdf.drawPath(path, stroke=0, fill=1)
            if round_start: pdf.circle(x0, y0, r, stroke=0, fill=1)
            if round_end:   pdf.circle(x1, y1, r, stroke=0, fill=1)
            pdf.restoreState()

        # ---------- (Optionnel) CLIP à l'intérieur du triangle ----------
        pdf.saveState()

        # ---------- BANDES ----------
        thickness = 8                   # épaisseur visuelle des bandes
        gap = -15                       # "jour" voulu entre l'hypoténuse et la 1ère bande
        band1_offset = gap + thickness/2
        band2_offset = band1_offset + 18
        offset = -10
                          # dépassement léger pour coller aux coins

        # Bande 1 : deux segments, arrondis contrôlés
        # Bande qui "glisse" : teste différentes positions s_px (0 → L)
        draw_band_slide(s_px=0.00*L, length_px=0.30*L, offset_px=offset,
                thickness=thickness, round_start=False, round_end=True,
                extend_start_px=20, extend_end_px=0,
                color=cls.LIGHT_GREEN, reverse=False, clamp=False)

        # Bande qui "glisse" : teste différentes positions s_px (0 → L)
        draw_band_slide(s_px=0.00*L, length_px=0.30*L, offset_px=offset,
                thickness=thickness, round_start=False, round_end=True,
                extend_start_px=40, extend_end_px=0,
                color=cls.LIGHT_GREEN, reverse=True, clamp=False)

        # Bande qui "glisse" : teste différentes positions s_px (0 → L)
        draw_band_slide(s_px=0.00*L, length_px=0.30*L, offset_px=offset+20,
                thickness=thickness+10, round_start=False, round_end=True,
                extend_start_px=40, extend_end_px=30,
                color=cls.SECONDARY_GREEN, reverse=False, clamp=False)

        # Bande qui "glisse" : teste différentes positions s_px (0 → L)
        draw_band_center(c_px=0.50*L, length_px=0.50*L, offset_px=offset-10,
                thickness=thickness, round_start=True, round_end=True,
                extend_start_px=40, extend_end_px=30,
                color=cls.SECONDARY_GREEN, reverse=False, clamp=False)

        pdf.restoreState()   # remet l'état de dessin initial


        # ---------- TRIANGLE BAS GAUCHE ----------

        def draw_band_center_bl(c_px, length_px, offset_px, thickness,
                        round_start=True, round_end=True,
                        extend_start_px=0, extend_end_px=0,
                        color=None, reverse=False, clamp=False):
            """
            Helper pour dessiner une bande centrée sur l'hypoténuse du triangle bas-gauche.

            c_px        : position du CENTRE le long de l'hypoténuse (en points)
            length_px   : longueur totale de la bande (en points)
            offset_px   : distance perpendiculaire à l'hypoténuse (positif = vers l'intérieur du triangle)
            thickness   : épaisseur visuelle
            """
            s_px = c_px - (length_px / 2.0)  # Convertit le centre -> début
            draw_band_slide_bl(
                s_px=s_px, length_px=length_px, offset_px=offset_px, thickness=thickness,
                round_start=round_start, round_end=round_end,
                extend_start_px=extend_start_px, extend_end_px=extend_end_px,
                color=color, reverse=reverse, clamp=clamp
            )

        # Remplissage
        tri_bl = pdf.beginPath()
        tri_bl.moveTo(0, 0)
        tri_bl.lineTo(0, 120)
        tri_bl.lineTo(220, 0)
        tri_bl.close()
        pdf.setFillColor(cls.PRIMARY_ORANGE)
        pdf.drawPath(tri_bl, stroke=0, fill=1)

        # Géométrie de l'hypoténuse (de (0,120) -> (220,0))
        start2_x, start2_y = 0,   120
        end2_x,   end2_y   = 220, 0

        dx2, dy2 = end2_x - start2_x, end2_y - start2_y
        L2 = (dx2*dx2 + dy2*dy2) ** 0.5
        ux2, uy2 = dx2 / L2, dy2 / L2              # direction le long de l'hypoténuse (↘)
        # Normale qui pointe à l'intérieur du triangle bas-gauche = vers le bas-gauche (−x, −y)
        nx2, ny2 = (uy2, -ux2)                     # ici ~(−, −)

        # (Optionnel) Clip pour garantir qu'aucun pixel ne déborde du triangle
        pdf.saveState()
        #clip2 = pdf.beginPath()
        #clip2.moveTo(0, 0); clip2.lineTo(0, 120); clip2.lineTo(220, 0); clip2.close()
        #pdf.clipPath(clip2, stroke=0, fill=0)

        def draw_band_slide_bl(s_px, length_px, offset_px, thickness,
                            round_start=True, round_end=True,
                            extend_start_px=0, extend_end_px=0,
                            color=None, reverse=False, clamp=False):
            """
            Bande 'capsule' parallèle à l'hypoténuse du triangle bas-gauche.
            s_px : position du DÉBUT le long de l'hypoténuse (en points, 0..L2)
            length_px : longueur de la bande le long de l'hypoténuse
            offset_px : écart perpendiculaire à l'hypoténuse (positif = vers l'intérieur du triangle)
            """
            # ancrage (depuis start2 ou depuis end2)
            if not reverse:
                ax, ay = start2_x, start2_y
                dirx, diry = ux2, uy2
            else:
                ax, ay = end2_x, end2_y
                dirx, diry = -ux2, -uy2

            a0 = s_px - extend_start_px
            a1 = s_px + length_px + extend_end_px
            if clamp:
                a0 = max(0.0, min(L2, a0))
                a1 = max(0.0, min(L2, a1))

            # centre de la bande le long de l'hypoténuse
            cx0, cy0 = ax + dirx * a0, ay + diry * a0
            cx1, cy1 = ax + dirx * a1, ay + diry * a1

            # décalage perpendiculaire (création du "jour")
            x0, y0 = cx0 + nx2 * offset_px, cy0 + ny2 * offset_px
            x1, y1 = cx1 + nx2 * offset_px, cy1 + ny2 * offset_px

            # capsule : rectangle + extrémités arrondies au choix
            r = thickness / 2.0
            rx, ry = nx2 * r, ny2 * r

            path = pdf.beginPath()
            path.moveTo(x0 - rx, y0 - ry)
            path.lineTo(x1 - rx, y1 - ry)
            path.lineTo(x1 + rx, y1 + ry)
            path.lineTo(x0 + rx, y0 + ry)
            path.close()

            pdf.saveState()
            if color is not None:
                pdf.setFillColor(color)
            pdf.drawPath(path, stroke=0, fill=1)
            if round_start:
                pdf.circle(x0, y0, r, stroke=0, fill=1)
            if round_end:
                pdf.circle(x1, y1, r, stroke=0, fill=1)
            pdf.restoreState()

        # ------- Paramètres visuels (identiques au triangle haut-droite) -------
        thickness2 = 8                   # épaisseur visuelle des bandes
        gap2 = -15                       # "jour" voulu entre l'hypoténuse et la 1ère bande
        band1_offset2 = gap2 + thickness2/2
        band2_offset2 = band1_offset2 + 18
        offset2 = -10

        # Exemples : deux bandes parallèles (remplacent tes pdf.line(...))
        # 1) bande "longue" proche de l'hypoténuse
        draw_band_slide_bl(
            s_px = 0.00 * L2,            # commence à ~5% de l'hypoténuse
            length_px = 0.30 * L2,       # longueur ~75%
            offset_px = offset2,
            thickness = thickness2,
            round_start = True, round_end = True,
            extend_start_px = 20, extend_end_px = 4,
            color = cls.PRIMARY_ORANGE,
            reverse = False, clamp = False
        )

        # 2) bande parallèle plus "profonde" (offset plus grand)
        draw_band_slide_bl(
            s_px = 0.00 * L2,
            length_px = 0.30 * L2,
            offset_px = offset2 ,
            thickness = thickness2,
            round_start = False, round_end = True,
            extend_start_px = 40, extend_end_px = 0,
            color = cls.PRIMARY_ORANGE,
            reverse = True, clamp = False
        )

        # 2) bande parallèle plus "profonde" (offset plus grand)
        draw_band_slide_bl(
            s_px = 0.00 * L2,
            length_px = 2 * L2,
            offset_px = offset2+20 ,
            thickness = thickness2+13,
            round_start = False, round_end = True,
            extend_start_px = 0, extend_end_px = 0,
            color = cls.LIGHT_2_ORANGE,
            reverse = False, clamp = False
        )

        # 2) bande parallèle plus "profonde" (offset plus grand)
        draw_band_slide_bl(
            s_px = 0.00 * L2,
            length_px = 0.30 * L2,
            offset_px = offset2+20 ,
            thickness = thickness2+13,
            round_start = False, round_end = True,
            extend_start_px = 40, extend_end_px = 30,
            color = cls.LIGHT_ORANGE,
            reverse = False, clamp = False
        )

        # 2) bande parallèle plus "profonde" (offset plus grand)
        draw_band_center_bl(
            c_px = 0.5 * L2,               # 50 % du long de l'hypoténuse
            length_px = 0.70 * L2,         # 40 % de la longueur totale
            offset_px = offset2-10,           # distance perpendiculaire
            thickness = thickness2,        # épaisseur
            round_start = True, round_end = True,
            extend_start_px = 6, extend_end_px = 6,
            color = cls.LIGHT_ORANGE,
            reverse = False, clamp = False
        )

        

        pdf.restoreState()  # fin du clip du triangle bas-gauche

    @classmethod
    def _draw_header(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine l'en-tête avec le titre République, le logo, la section et le ministère."""
        pdf.saveState()

        center_x = width / 2
        current_y = height - 40

        # ---------- TITRE "REPUBLIQUE DE COTE D'IVOIRE" ----------
        pdf.setFillColor(cls.DARK_TEXT)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(center_x, current_y, "REPUBLIQUE DE COTE D'IVOIRE")
        current_y -= 25  # Espace après le titre

        # ---------- EMBLÈME CENTRAL (après le titre) ----------
        # Logo/emblème au centre (si disponible)
        logo_raw_path = cls.data.get("logo_path", "")
        logger.info(f"🔍 Recherche du logo avec le chemin: {logo_raw_path}")
        logo_path = cls._resolve_asset_path(logo_raw_path)
        logger.info(f"🔍 Chemin résolu du logo: {logo_path}")
        
        if logo_path:
            try:
                logo_width = 3.5 * cm
                logo_height = 3.5 * cm
                x_logo = center_x - logo_width / 2
                y_logo = current_y - logo_height

                logger.info(f"🖼️ Dessin du logo: {logo_path} à la position ({x_logo}, {y_logo})")
                
                if logo_path.lower().endswith(".webp"):
                    try:
                        from PIL import Image
                        with Image.open(logo_path) as im:
                            im = im.convert("RGBA")
                            buffer = BytesIO()
                            im.save(buffer, format="PNG")
                            buffer.seek(0)
                            pdf.drawImage(
                                ImageReader(buffer),
                                x_logo, y_logo,
                                width=logo_width,
                                height=logo_height,
                                preserveAspectRatio=True,
                                mask="auto"
                            )
                            logger.info("✅ Logo WEBP chargé et dessiné avec succès")
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur avec WEBP, tentative normale: {e}")
                        pdf.drawImage(
                            logo_path, x_logo, y_logo,
                            width=logo_width,
                            height=logo_height,
                            preserveAspectRatio=True
                        )
                else:
                    pdf.drawImage(
                        logo_path, x_logo, y_logo,
                        width=logo_width,
                        height=logo_height,
                        preserveAspectRatio=True
                    )
                    logger.info("✅ Logo chargé et dessiné avec succès")
                
                # Ajuster la position pour continuer après le logo
                current_y = y_logo - 15
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement du logo: {e}", exc_info=True)
                current_y -= 80  # Espace si pas de logo
        else:
            logger.warning(f"⚠️ Logo non trouvé pour le chemin: {logo_raw_path}")
            current_y -= 80  # Espace si pas de logo

        # ---------- BLOC SECTION + MINISTÈRE (entre deux lignes pointillées) ----------
        # D'abord, calculer la hauteur totale du contenu pour le centrer correctement
        section = cls.data.get("section", "SECTION 376")
        ministere = cls.data.get("ministere", "")
        
        # Déterminer la source de chaque donnée pour le styling
        _, section_source = cls._determine_data_source_for_canvas("section", section)
        _, ministere_source = cls._determine_data_source_for_canvas("ministere", ministere)
        
        # Calculer la hauteur du contenu
        section_height = 20  # Hauteur de la section (texte + espace)
        ministere_height = 0
        if ministere:
            ministere_lines = wrap(ministere, width=80)
            ministere_height = len(ministere_lines) * 16  # 16 points par ligne
        
        total_content_height = section_height + ministere_height
        
        # Espacements fixes autour du contenu
        spacing = 0.5 * cm
        
        # Hauteur totale du bloc (contenu + espacements)
        total_block_height = total_content_height + (2 * spacing)
        
        # Position du centre vertical du bloc (par rapport à current_y)
        block_center_y = current_y - (total_block_height / 2)
        
        # Ligne pointillée au-dessus
        pdf.setLineWidth(1)
        pdf.setDash(4, 3)
        pdf.setStrokeColor(cls.DARK_TEXT)
        top_line_y = block_center_y + (total_content_height / 2) + spacing
        pdf.line(center_x - 120, top_line_y, center_x + 120, top_line_y)
        pdf.setDash()
        
        # Position de départ pour le contenu (centré verticalement)
        content_start_y = block_center_y + (total_content_height / 2)
        content_current_y = content_start_y
        
        # ---------- SECTION ----------
        pdf.setFont("Helvetica-Bold", 12)
        section_color = cls._get_color_for_source(section_source)
        pdf.saveState()
        pdf.setFillColor(section_color)
        pdf.drawCentredString(center_x, content_current_y, section + " :")
        pdf.restoreState()
        content_current_y -= 20  # Espace après la section

        # ---------- MINISTÈRE ----------
        if ministere:
            pdf.setFont("Helvetica-Bold", 11)
            ministere_color = cls._get_color_for_source(ministere_source)
            lines = wrap(ministere, width=80)
            line_height = 16
            pdf.saveState()
            pdf.setFillColor(ministere_color)
            for line in lines:
                pdf.drawCentredString(center_x, content_current_y, line)
                content_current_y -= line_height
            pdf.restoreState()
        
        # Ligne pointillée en dessous
        pdf.setLineWidth(1)
        pdf.setDash(4, 3)
        pdf.setStrokeColor(cls.DARK_TEXT)
        bottom_line_y = block_center_y - (total_content_height / 2) - spacing
        pdf.line(center_x - 120, bottom_line_y, center_x + 120, bottom_line_y)
        pdf.setDash()
        
        # Stocker la position de la ligne pointillée pour l'utiliser dans _draw_cover_block
        cls._dotted_line_bottom_y = bottom_line_y
        
        # Mettre à jour current_y pour la suite
        current_y = bottom_line_y

        pdf.restoreState()

    @classmethod
    def _draw_cover_block(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine le bloc central avec le titre du rapport dans une boîte orange."""
        pdf.saveState()

        center_x = width / 2
        center_y = height / 2

        # ---------- BOÎTE ORANGE AVEC LE TITRE ----------
        # Dimensions de la boîte (plus large pour le mode paysage)
        box_margin_x = 3 * cm
        box_width = width - 6 * cm
        box_height = 5.5 * cm  # Hauteur réduite
        box_x = box_margin_x
        
        # Espacement minimum entre la ligne pointillée du bas et le haut du cadre orange
        min_spacing_from_dotted_line = 1 * cm
        
        # Calculer la position du cadre en fonction de la ligne pointillée
        if cls._dotted_line_bottom_y is not None:
            # Position minimale du haut du cadre (bas de la ligne pointillée - espacement)
            min_frame_top_y = cls._dotted_line_bottom_y - min_spacing_from_dotted_line
            # Position du bas du cadre
            min_frame_bottom_y = min_frame_top_y - box_height
            
            # Position souhaitée (basée sur le centre)
            desired_box_y = center_y - box_height / 2 - 1.5 * cm
            desired_box_top_y = desired_box_y + box_height
            
            # Utiliser la position la plus basse entre celle souhaitée et celle minimale
            if desired_box_top_y > min_frame_top_y:
                # Si la position souhaitée serait trop proche, utiliser la position minimale
                box_y = min_frame_top_y - box_height
            else:
                box_y = desired_box_y
        else:
            # Si la ligne pointillée n'a pas été dessinée (ne devrait pas arriver), utiliser la position par défaut
            box_y = center_y - box_height / 2 - 2.5 * cm

        # Dessiner la boîte orange avec bordure épaisse
        pdf.setLineWidth(4)
        pdf.setStrokeColor(cls.PRIMARY_ORANGE)
        pdf.setFillColor(colors.white)
        pdf.rect(box_x, box_y, box_width, box_height, stroke=1, fill=1)

        # Texte du rapport dans la boîte avec marges appropriées
        titre_rapport = cls.data.get("titre_rapport", "")
        titre_annee = cls.data.get("titre_annee", "")
        annee = cls.data.get("annee", "")
        
        # Déterminer la source de chaque donnée pour le styling
        _, titre_rapport_source = cls._determine_data_source_for_canvas("titre_rapport", titre_rapport)
        _, titre_annee_source = cls._determine_data_source_for_canvas("titre_annee", titre_annee)
        _, annee_source = cls._determine_data_source_for_canvas("annee", annee)
        
        # Marges intérieures de la boîte (réduites)
        padding_top = 0.5 * cm
        padding_bottom = 0.5 * cm
        padding_left = 0.7 * cm
        padding_right = 0.7 * cm
        
        # Zone de texte disponible (en tenant compte de l'épaisseur de la bordure)
        border_width = 4  # Largeur de la bordure en points
        text_area_left = box_x + padding_left + border_width
        text_area_right = box_x + box_width - padding_right - border_width
        text_area_width = text_area_right - text_area_left
        text_area_top = box_y + box_height - padding_top - border_width
        text_area_bottom = box_y + padding_bottom + border_width
        
        # Fonction pour découper le texte selon la largeur disponible
        def wrap_text_to_width(pdf_canvas, text, font_name, font_size, max_width):
            """Découpe le texte en lignes qui rentrent dans la largeur max_width."""
            words = text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_width = pdf_canvas.stringWidth(test_line, font_name, font_size)
                
                if test_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    # Si un mot seul dépasse, on le coupe
                    if pdf_canvas.stringWidth(word, font_name, font_size) > max_width:
                        # Couper le mot
                        current_word = word
                        while pdf_canvas.stringWidth(current_word, font_name, font_size) > max_width:
                            # Trouver un point de coupure
                            for i in range(len(current_word), 0, -1):
                                if pdf_canvas.stringWidth(current_word[:i], font_name, font_size) <= max_width:
                                    lines.append(current_word[:i])
                                    current_word = current_word[i:]
                                    break
                            else:
                                # Si on ne peut pas couper proprement, prendre au moins un caractère
                                lines.append(current_word[0])
                                current_word = current_word[1:]
                        current_line = current_word
                    else:
                        current_line = word
            
            if current_line:
                lines.append(current_line)
            
            return lines if lines else [text]
        
        # Titre principal (sur plusieurs lignes si nécessaire)
        font_size = 16
        font_name = "Helvetica-Bold"
        line_height = 22  # Hauteur de ligne par défaut
        pdf.setFont(font_name, font_size)
        
        # Calculer la largeur maximale pour le texte
        max_text_width = text_area_width
        
        # Déterminer la couleur du titre selon sa source
        titre_color = cls._get_color_for_source(titre_rapport_source)
        
        # Découper le titre en lignes
        if titre_rapport:
            lines = wrap_text_to_width(pdf, titre_rapport.upper(), font_name, font_size, max_text_width)
            total_text_height = len(lines) * line_height
            available_height = text_area_top - text_area_bottom
            
            # Si le texte est trop haut, réduire la taille de police
            if total_text_height > available_height - 30:  # 30 points pour l'année en dessous
                font_size = 14
                line_height = 20
                pdf.setFont(font_name, font_size)
                # Recalculer avec la nouvelle taille
                lines = wrap_text_to_width(pdf, titre_rapport.upper(), font_name, font_size, max_text_width)
                total_text_height = len(lines) * line_height
            
            # Positionner le texte en haut de la zone disponible
            text_y = text_area_top - 0.8 * cm
            
            # Dessiner chaque ligne centrée avec la couleur appropriée
            pdf.saveState()
            pdf.setFillColor(titre_color)
            for i, line in enumerate(lines):
                pdf.drawCentredString(center_x, text_y - (i * line_height), line)
            pdf.restoreState()
            
            text_y = text_y - (len(lines) * line_height)
        else:
            text_y = text_area_top - 0.8 * cm
        
        # Année sous le titre (sur une ligne séparée)
        if titre_annee and annee:
            text_y -= 15
            # Vérifier qu'on ne dépasse pas le bas de la boîte
            if text_y >= text_area_bottom:
                year_text = f"{titre_annee.upper()} {annee}"
                # Déterminer la couleur de l'année (utiliser la source de l'année si titre_annee est par défaut)
                # Si titre_annee est USER, utiliser sa source, sinon utiliser celle de l'année
                year_color = cls._get_color_for_source(annee_source) if titre_annee_source == "default" else cls._get_color_for_source(titre_annee_source)
                
                # Vérifier que l'année rentre aussi dans la largeur
                if pdf.stringWidth(year_text, font_name, font_size) > max_text_width:
                    # Réduire la taille pour l'année si nécessaire
                    pdf.setFont(font_name, 14)
                pdf.saveState()
                pdf.setFillColor(year_color)
                pdf.drawCentredString(center_x, text_y, year_text)
                pdf.restoreState()

        pdf.restoreState()

    @classmethod
    def _draw_footer(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine le bloc date en bas à droite."""
        pdf.saveState()

        # ---------- BOÎTE DATE EN BAS À DROITE ----------
        date_publication = cls.data.get("date_publication", "")
        date_is_generated = False
        if not date_publication:
            # Générer la date à partir de l'année si non fournie
            annee = cls.data.get("annee", "")
            date_publication = f"Mai {int(annee) + 1}" if annee else "Mai 2025"
            date_is_generated = True
        
        # Déterminer la source de la date de publication pour le styling
        if date_is_generated:
            date_source = "default"
        else:
            _, date_source = cls._determine_data_source_for_canvas("date_publication", date_publication)

        box_width = 4 * cm
        box_height = 1.2 * cm
        box_x = width - box_width - 2 * cm
        box_y = 1.5 * cm

        # Boîte orange clair avec coins arrondis (simulés avec rectangle)
        pdf.setFillColor(cls.LIGHT_ORANGE)
        pdf.setStrokeColor(cls.PRIMARY_ORANGE)
        pdf.setLineWidth(1.5)
        pdf.roundRect(box_x, box_y, box_width, box_height, radius=5, stroke=1, fill=1)

        # Texte de la date centré avec couleur selon la source
        date_color = cls._get_color_for_source(date_source)
        pdf.setFillColor(date_color)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(
            box_x + box_width / 2,
            box_y + box_height / 2 - 4,
            date_publication
        )

        pdf.restoreState()

    @classmethod
    def _draw_table_of_contents(cls, pdf: canvas.Canvas, width: float, height: float) -> int:
        """Dessine la page du sommaire (table of contents) avec support multi-pages. Retourne le numéro de page suivant."""
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm  # Hauteur du footer
        footer_margin = 0.8 * cm  # Marge entre le contenu et le footer
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin  # Limite du contenu (avant le footer)
        line_spacing = 0.55 * cm  # Espacement entre les lignes

        # Couleur bleue pour tous les éléments
        blue_color = colors.HexColor("#0066CC")
        
        # Construire la liste des éléments du sommaire
        toc_items = []
        
        # Éléments fixes
        toc_items.append({"text": "LISTE DES TABLEAUX", "page": 3, "level": 0, "bold": False})
        toc_items.append({"text": "LISTE DES GRAPHIQUES", "page": 3, "level": 0, "bold": False})
        toc_items.append({"text": "SIGLES ET ABRÉVIATIONS", "page": 5, "level": 0, "bold": False})
        toc_items.append({"text": "INTRODUCTION GÉNÉRALE", "page": 7, "level": 0, "bold": False})
        
        # PARTIE I : LE MINISTÈRE
        toc_items.append({"text": "PARTIE I : LE MINISTÈRE", "page": 8, "level": 0, "bold": True})
        toc_items.append({"text": "I. PRÉSENTATION GÉNÉRALE DU MINISTÈRE", "page": 8, "level": 1, "bold": False})
        toc_items.append({"text": "II. PERFORMANCE GÉNÉRALE DU MINISTÈRE", "page": 9, "level": 1, "bold": False})
        toc_items.append({"text": "III. FINANCEMENT GLOBAL DU MINISTÈRE", "page": 10, "level": 1, "bold": False})
        
        # Programmes dynamiques depuis les données (ou valeurs par défaut)
        programmes = cls.data.get("programmes", [])
        if not programmes:
            # Utiliser les programmes par défaut si aucun n'est fourni
            programmes = cls.DEFAULT_DATA.get("programmes", [])
        
        for programme in programmes:
            numero = programme.get("numero", 1)
            titre = programme.get("titre", "")
            page_debut = programme.get("page_debut", 0)
            sections = programme.get("sections", [])
            
            # Titre de la partie (PARTIE II, III, etc. car PARTIE I est le ministère)
            partie_text = f"PARTIE {numero + 1} : LE PROGRAMME {numero} « {titre.upper()} »"
            toc_items.append({"text": partie_text, "page": page_debut, "level": 0, "bold": True})
            
            # Sections du programme
            for section in sections:
                section_titre = section.get("titre", "")
                section_page = section.get("page", page_debut)
                toc_items.append({"text": section_titre, "page": section_page, "level": 1, "bold": False})
        
        # Fonction helper pour dessiner une ligne du sommaire
        def draw_toc_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                current_y_pos = current_y
            line_spacing_val = line_spacing
            
            x_text = left_margin + (level * 1 * cm)  # Indentation selon le niveau
            x_page = width - right_margin - 1 * cm  # Position des numéros de page
            page_num_width = 2 * cm  # Espace réservé pour le numéro de page
            max_text_width = x_page - x_text - page_num_width  # Largeur maximale du texte
            
            pdf.saveState()
            
            # Toujours en bleu
            pdf.setFillColor(blue_color)
            pdf.setStrokeColor(blue_color)
            
            # Style du texte
            font = "Helvetica-Bold" if bold else "Helvetica"
            font_size = 11 if level == 0 else 10 if level == 1 else 9
            
            pdf.setFont(font, font_size)
            
            # Tronquer le texte si nécessaire pour éviter le chevauchement avec le numéro de page
            text_to_draw = text
            text_width = pdf.stringWidth(text, font, font_size)
            if text_width > max_text_width:
                # Tronquer le texte et ajouter "..."
                text_to_draw = text
                ellipsis_width = pdf.stringWidth("...", font, font_size)
                available_width = max_text_width - ellipsis_width
                
                # Réduire progressivement le texte jusqu'à ce qu'il rentre
                while pdf.stringWidth(text_to_draw, font, font_size) > available_width and len(text_to_draw) > 0:
                    text_to_draw = text_to_draw[:-1]
                
                text_to_draw = text_to_draw + "..."
            
            # Dessiner le texte
            pdf.drawString(x_text, current_y_pos, text_to_draw)
            
            # Toujours souligné
            actual_text_width = pdf.stringWidth(text_to_draw, font, font_size)
            pdf.setLineWidth(1)
            pdf.line(x_text, current_y_pos - 2, x_text + actual_text_width, current_y_pos - 2)
            
            # Dessiner le numéro de page (en bleu aussi, aligné à droite)
            page_str = str(page) if page else "..."
            pdf.drawRightString(x_page, current_y_pos, page_str)
            
            pdf.restoreState()
            
            return current_y_pos - line_spacing_val

        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            footer_y = footer_margin
            footer_center_y = footer_y + footer_height / 2
            
            # Numéro de page dans le footer (design carte/page avec coin relevé)
            page_num_box_size = 1.0 * cm
            page_num_x = width - right_margin - page_num_box_size
            page_num_y = footer_center_y - page_num_box_size / 2
            
            pdf.saveState()
            
            # Ombre portée
            pdf.setFillColor(colors.HexColor("#E0E0E0"))
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            shadow_offset = 2
            pdf.roundRect(
                page_num_x + shadow_offset,
                page_num_y - shadow_offset,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=0,
                fill=1
            )
            
            # Carte blanche principale
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(
                page_num_x,
                page_num_y,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=1,
                fill=1
            )
            
            # Coin relevé
            corner_size = 0.3 * cm
            corner_x = page_num_x + page_num_box_size - corner_size
            corner_y = page_num_y + page_num_box_size - corner_size
            
            pdf.setFillColor(colors.HexColor("#F5F5F5"))
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.3)
            corner_path = pdf.beginPath()
            corner_path.moveTo(corner_x, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, corner_y)
            corner_path.curveTo(corner_x + corner_size * 0.3, corner_y, corner_x, corner_y - corner_size * 0.3, corner_x, page_num_y + page_num_box_size - corner_size * 0.5)
            corner_path.close()
            pdf.drawPath(corner_path, stroke=1, fill=1)
            
            # Ligne de séparation
            pdf.setLineWidth(0.3)
            pdf.setStrokeColor(colors.HexColor("#AAAAAA"))
            pdf.line(corner_x, page_num_y + page_num_box_size - corner_size * 0.5, page_num_x + page_num_box_size, corner_y)
            
            # Numéro de page
            pdf.setFillColor(colors.HexColor("#666666"))
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(
                page_num_x + page_num_box_size / 2,
                page_num_y + page_num_box_size / 2 - 3,
                str(page_number)
            )
            
            pdf.restoreState()

        # Dessiner le sommaire avec pagination automatique
        page_num = 2  # Commence à la page 2 (après la couverture)
        first_page = True
        
        while toc_items or first_page:
            if not first_page:
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Sommaire (suite)")
            
            pdf.saveState()
            
            # Titre "SOMMAIRE" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(cls.DARK_TEXT)
                pdf.setFont("Helvetica-Bold", 18)
                title_y = start_y
                pdf.drawString(left_margin, title_y, "SOMMAIRE")
                current_y = title_y - 2 * cm
            else:
                current_y = start_y
            
            # Dessiner les éléments jusqu'à ce que la page soit pleine
            items_to_remove = []
            for item in toc_items:
                # Calculer l'espace nécessaire pour cet élément
                spacing_needed = line_spacing
                if item["level"] == 0 and item["bold"]:
                    spacing_needed += 0.15 * cm
                elif item["level"] == 0:
                    spacing_needed += 0.2 * cm
                
                # Vérifier si on a assez d'espace avant de dessiner
                if current_y - spacing_needed < content_bottom:
                    # Pas assez d'espace, passer à la page suivante
                    break
                
                # Dessiner l'élément
                current_y = draw_toc_line(
                    item["text"],
                    item["page"],
                    item["level"],
                    item["bold"],
                    current_y
                )
                
                # Espacement supplémentaire après les parties principales
                if item["level"] == 0 and item["bold"]:
                    current_y -= 0.15 * cm
                elif item["level"] == 0:
                    current_y -= 0.2 * cm
                
                items_to_remove.append(item)
            
            # Retirer les éléments déjà dessinés
            for item in items_to_remove:
                toc_items.remove(item)
            
            # Dessiner le footer
            draw_footer(page_num)
            
            pdf.restoreState()
            
            page_num += 1
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and toc_items:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        return page_num

    @classmethod
    def _draw_liste_tableaux(cls, pdf: canvas.Canvas, width: float, height: float, start_page: int) -> int:
        """Dessine la page de la liste des tableaux avec support multi-pages."""
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm  # Hauteur du footer
        footer_margin = 0.8 * cm  # Marge entre le contenu et le footer
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin  # Limite du contenu (avant le footer)
        line_spacing = 0.55 * cm  # Espacement entre les lignes

        # Couleur bleue pour tous les éléments
        blue_color = colors.HexColor("#0066CC")
        
        # Construire la liste des tableaux
        tableaux_items = []
        
        # Récupérer les tableaux depuis les données (ou valeurs par défaut)
        tableaux = cls.data.get("tableaux", [])
        if not tableaux:
            # Utiliser les tableaux par défaut si aucun n'est fourni
            tableaux = cls.DEFAULT_DATA.get("tableaux", [])
        
        for tableau in tableaux:
            numero = tableau.get("numero", 1)
            titre = tableau.get("titre", "")
            page = tableau.get("page", 0)
            
            # Format: "Tableau X: Titre"
            tableau_text = f"Tableau {numero}: {titre}"
            tableaux_items.append({"text": tableau_text, "page": page, "level": 0, "bold": False})
        
        # Fonction helper pour dessiner une ligne
        def draw_tableau_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                current_y_pos = current_y
            line_spacing_val = line_spacing
            
            x_text = left_margin + (level * 1 * cm)  # Indentation selon le niveau
            x_page = width - right_margin - 1 * cm  # Position des numéros de page
            page_num_width = 2 * cm  # Espace réservé pour le numéro de page
            max_text_width = x_page - x_text - page_num_width  # Largeur maximale du texte
            
            pdf.saveState()
            
            # Toujours en bleu
            pdf.setFillColor(blue_color)
            pdf.setStrokeColor(blue_color)
            
            # Style du texte
            font = "Helvetica-Bold" if bold else "Helvetica"
            font_size = 11 if level == 0 else 10 if level == 1 else 9
            
            pdf.setFont(font, font_size)
            
            # Tronquer le texte si nécessaire pour éviter le chevauchement avec le numéro de page
            text_to_draw = text
            text_width = pdf.stringWidth(text, font, font_size)
            if text_width > max_text_width:
                # Tronquer le texte et ajouter "..."
                text_to_draw = text
                ellipsis_width = pdf.stringWidth("...", font, font_size)
                available_width = max_text_width - ellipsis_width
                
                # Réduire progressivement le texte jusqu'à ce qu'il rentre
                while pdf.stringWidth(text_to_draw, font, font_size) > available_width and len(text_to_draw) > 0:
                    text_to_draw = text_to_draw[:-1]
                
                text_to_draw = text_to_draw + "..."
            
            # Dessiner le texte
            pdf.drawString(x_text, current_y_pos, text_to_draw)
            
            # Toujours souligné
            actual_text_width = pdf.stringWidth(text_to_draw, font, font_size)
            pdf.setLineWidth(1)
            pdf.line(x_text, current_y_pos - 2, x_text + actual_text_width, current_y_pos - 2)
            
            # Dessiner le numéro de page (en bleu aussi, aligné à droite)
            page_str = str(page) if page else "..."
            pdf.drawRightString(x_page, current_y_pos, page_str)
            
            pdf.restoreState()
            
            return current_y_pos - line_spacing_val

        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            footer_y = footer_margin
            footer_center_y = footer_y + footer_height / 2
            
            # Numéro de page dans le footer (design carte/page avec coin relevé)
            page_num_box_size = 1.0 * cm
            page_num_x = width - right_margin - page_num_box_size
            page_num_y = footer_center_y - page_num_box_size / 2
            
            pdf.saveState()
            
            # Ombre portée
            pdf.setFillColor(colors.HexColor("#E0E0E0"))
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            shadow_offset = 2
            pdf.roundRect(
                page_num_x + shadow_offset,
                page_num_y - shadow_offset,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=0,
                fill=1
            )
            
            # Carte blanche principale
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(
                page_num_x,
                page_num_y,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=1,
                fill=1
            )
            
            # Coin relevé
            corner_size = 0.3 * cm
            corner_x = page_num_x + page_num_box_size - corner_size
            corner_y = page_num_y + page_num_box_size - corner_size
            
            pdf.setFillColor(colors.HexColor("#F5F5F5"))
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.3)
            corner_path = pdf.beginPath()
            corner_path.moveTo(corner_x, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, corner_y)
            corner_path.curveTo(corner_x + corner_size * 0.3, corner_y, corner_x, corner_y - corner_size * 0.3, corner_x, page_num_y + page_num_box_size - corner_size * 0.5)
            corner_path.close()
            pdf.drawPath(corner_path, stroke=1, fill=1)
            
            # Ligne de séparation
            pdf.setLineWidth(0.3)
            pdf.setStrokeColor(colors.HexColor("#AAAAAA"))
            pdf.line(corner_x, page_num_y + page_num_box_size - corner_size * 0.5, page_num_x + page_num_box_size, corner_y)
            
            # Numéro de page
            pdf.setFillColor(colors.HexColor("#666666"))
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(
                page_num_x + page_num_box_size / 2,
                page_num_y + page_num_box_size / 2 - 3,
                str(page_number)
            )
            
            pdf.restoreState()

        # Dessiner la liste avec pagination automatique
        page_num = start_page
        first_page = True
        
        while tableaux_items or first_page:
            if first_page:
                # Créer la première page pour la liste des tableaux
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Liste des tableaux")
            else:
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Liste des tableaux (suite)")
            
            pdf.saveState()
            
            # Titre "LISTE DES TABLEAUX" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(cls.DARK_TEXT)
                pdf.setFont("Helvetica-Bold", 18)
                title_y = start_y
                pdf.drawString(left_margin, title_y, "LISTE DES TABLEAUX")
                current_y = title_y - 2 * cm
            else:
                current_y = start_y
            
            # Dessiner les éléments jusqu'à ce que la page soit pleine
            items_to_remove = []
            for item in tableaux_items:
                # Calculer l'espace nécessaire pour cet élément
                spacing_needed = line_spacing
                
                # Vérifier si on a assez d'espace avant de dessiner
                if current_y - spacing_needed < content_bottom:
                    # Pas assez d'espace, passer à la page suivante
                    break
                
                # Dessiner l'élément
                current_y = draw_tableau_line(
                    item["text"],
                    item["page"],
                    item["level"],
                    item["bold"],
                    current_y
                )
                
                items_to_remove.append(item)
            
            # Retirer les éléments déjà dessinés
            for item in items_to_remove:
                tableaux_items.remove(item)
            
            # Dessiner le footer
            draw_footer(page_num)
            
            pdf.restoreState()
            
            page_num += 1
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and tableaux_items:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        return page_num

    @classmethod
    def _draw_liste_graphiques(cls, pdf: canvas.Canvas, width: float, height: float, start_page: int) -> int:
        """Dessine la page de la liste des graphiques avec support multi-pages."""
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm  # Hauteur du footer
        footer_margin = 0.8 * cm  # Marge entre le contenu et le footer
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin  # Limite du contenu (avant le footer)
        line_spacing = 0.55 * cm  # Espacement entre les lignes

        # Couleur bleue pour tous les éléments
        blue_color = colors.HexColor("#0066CC")
        
        # Construire la liste des graphiques
        graphiques_items = []
        
        # Récupérer les graphiques depuis les données (ou valeurs par défaut)
        graphiques = cls.data.get("graphiques", [])
        if not graphiques:
            # Utiliser les graphiques par défaut si aucun n'est fourni
            graphiques = cls.DEFAULT_DATA.get("graphiques", [])
        
        for graphique in graphiques:
            numero = graphique.get("numero", 1)
            titre = graphique.get("titre", "")
            page = graphique.get("page", 0)
            
            # Format: "Figure X: Titre"
            graphique_text = f"Figure {numero}: {titre}"
            graphiques_items.append({"text": graphique_text, "page": page, "level": 0, "bold": False})
        
        # Fonction helper pour dessiner une ligne
        def draw_graphique_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                current_y_pos = current_y
            line_spacing_val = line_spacing
            
            x_text = left_margin + (level * 1 * cm)  # Indentation selon le niveau
            x_page = width - right_margin - 1 * cm  # Position des numéros de page
            page_num_width = 2 * cm  # Espace réservé pour le numéro de page
            max_text_width = x_page - x_text - page_num_width  # Largeur maximale du texte
            
            pdf.saveState()
            
            # Toujours en bleu
            pdf.setFillColor(blue_color)
            pdf.setStrokeColor(blue_color)
            
            # Style du texte
            font = "Helvetica-Bold" if bold else "Helvetica"
            font_size = 11 if level == 0 else 10 if level == 1 else 9
            
            pdf.setFont(font, font_size)
            
            # Tronquer le texte si nécessaire pour éviter le chevauchement avec le numéro de page
            text_to_draw = text
            text_width = pdf.stringWidth(text, font, font_size)
            if text_width > max_text_width:
                # Tronquer le texte et ajouter "..."
                text_to_draw = text
                ellipsis_width = pdf.stringWidth("...", font, font_size)
                available_width = max_text_width - ellipsis_width
                
                # Réduire progressivement le texte jusqu'à ce qu'il rentre
                while pdf.stringWidth(text_to_draw, font, font_size) > available_width and len(text_to_draw) > 0:
                    text_to_draw = text_to_draw[:-1]
                
                text_to_draw = text_to_draw + "..."
            
            # Dessiner le texte
            pdf.drawString(x_text, current_y_pos, text_to_draw)
            
            # Toujours souligné
            actual_text_width = pdf.stringWidth(text_to_draw, font, font_size)
            pdf.setLineWidth(1)
            pdf.line(x_text, current_y_pos - 2, x_text + actual_text_width, current_y_pos - 2)
            
            # Dessiner le numéro de page (en bleu aussi, aligné à droite)
            page_str = str(page) if page else "..."
            pdf.drawRightString(x_page, current_y_pos, page_str)
            
            pdf.restoreState()
            
            return current_y_pos - line_spacing_val

        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            footer_y = footer_margin
            footer_center_y = footer_y + footer_height / 2
            
            # Numéro de page dans le footer (design carte/page avec coin relevé)
            page_num_box_size = 1.0 * cm
            page_num_x = width - right_margin - page_num_box_size
            page_num_y = footer_center_y - page_num_box_size / 2
            
            pdf.saveState()
            
            # Ombre portée
            pdf.setFillColor(colors.HexColor("#E0E0E0"))
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            shadow_offset = 2
            pdf.roundRect(
                page_num_x + shadow_offset,
                page_num_y - shadow_offset,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=0,
                fill=1
            )
            
            # Carte blanche principale
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(
                page_num_x,
                page_num_y,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=1,
                fill=1
            )
            
            # Coin relevé
            corner_size = 0.3 * cm
            corner_x = page_num_x + page_num_box_size - corner_size
            corner_y = page_num_y + page_num_box_size - corner_size
            
            pdf.setFillColor(colors.HexColor("#F5F5F5"))
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.3)
            corner_path = pdf.beginPath()
            corner_path.moveTo(corner_x, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, corner_y)
            corner_path.curveTo(corner_x + corner_size * 0.3, corner_y, corner_x, corner_y - corner_size * 0.3, corner_x, page_num_y + page_num_box_size - corner_size * 0.5)
            corner_path.close()
            pdf.drawPath(corner_path, stroke=1, fill=1)
            
            # Ligne de séparation
            pdf.setLineWidth(0.3)
            pdf.setStrokeColor(colors.HexColor("#AAAAAA"))
            pdf.line(corner_x, page_num_y + page_num_box_size - corner_size * 0.5, page_num_x + page_num_box_size, corner_y)
            
            # Numéro de page
            pdf.setFillColor(colors.HexColor("#666666"))
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(
                page_num_x + page_num_box_size / 2,
                page_num_y + page_num_box_size / 2 - 3,
                str(page_number)
            )
            
            pdf.restoreState()

        # Dessiner la liste avec pagination automatique
        page_num = start_page
        first_page = True
        
        while graphiques_items or first_page:
            if first_page:
                # Créer la première page pour la liste des graphiques
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Liste des graphiques")
            else:
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Liste des graphiques (suite)")
            
            pdf.saveState()
            
            # Titre "LISTE DES GRAPHIQUES" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(cls.DARK_TEXT)
                pdf.setFont("Helvetica-Bold", 18)
                title_y = start_y
                pdf.drawString(left_margin, title_y, "LISTE DES GRAPHIQUES")
                current_y = title_y - 2 * cm
            else:
                current_y = start_y
            
            # Dessiner les éléments jusqu'à ce que la page soit pleine
            items_to_remove = []
            for item in graphiques_items:
                # Calculer l'espace nécessaire pour cet élément
                spacing_needed = line_spacing
                
                # Vérifier si on a assez d'espace avant de dessiner
                if current_y - spacing_needed < content_bottom:
                    # Pas assez d'espace, passer à la page suivante
                    break
                
                # Dessiner l'élément
                current_y = draw_graphique_line(
                    item["text"],
                    item["page"],
                    item["level"],
                    item["bold"],
                    current_y
                )
                
                items_to_remove.append(item)
            
            # Retirer les éléments déjà dessinés
            for item in items_to_remove:
                graphiques_items.remove(item)
            
            # Dessiner le footer
            draw_footer(page_num)
            
            pdf.restoreState()
            
            page_num += 1
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and graphiques_items:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        return page_num

    @classmethod
    def _draw_liste_sigles_abreviations(cls, pdf: canvas.Canvas, width: float, height: float, start_page: int) -> int:
        """Dessine la page des sigles et abréviations avec support multi-pages en une seule colonne."""
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm  # Hauteur du footer
        footer_margin = 0.8 * cm  # Marge entre le contenu et le footer
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin  # Limite du contenu (avant le footer)
        line_spacing = 0.6 * cm  # Espacement entre les lignes

        # Couleur bleue pour tous les éléments
        blue_color = colors.HexColor("#0066CC")
        
        # Récupérer les sigles depuis les données (ou valeurs par défaut)
        sigles = cls.data.get("sigles", [])
        default_sigles = cls.DEFAULT_DATA.get("sigles", [])
        
        # Déterminer si les sigles viennent de l'utilisateur ou sont par défaut
        is_sigles_user = "sigles" in cls._user_data_keys
        
        if not sigles:
            # Utiliser les sigles par défaut si aucun n'est fourni
            sigles = default_sigles
            is_sigles_user = False
        
        # Créer un set des sigles par défaut pour vérification rapide
        default_sigles_set = {entry.get("sigle"): entry.get("definition") for entry in default_sigles}
        
        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            footer_y = footer_margin
            footer_center_y = footer_y + footer_height / 2
            
            # Numéro de page dans le footer (design carte/page avec coin relevé)
            page_num_box_size = 1.0 * cm
            page_num_x = width - right_margin - page_num_box_size
            page_num_y = footer_center_y - page_num_box_size / 2
            
            pdf.saveState()
            
            # Ombre portée
            pdf.setFillColor(colors.HexColor("#E0E0E0"))
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            shadow_offset = 2
            pdf.roundRect(
                page_num_x + shadow_offset,
                page_num_y - shadow_offset,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=0,
                fill=1
            )
            
            # Carte blanche principale
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(
                page_num_x,
                page_num_y,
                page_num_box_size,
                page_num_box_size,
                radius=3,
                stroke=1,
                fill=1
            )
            
            # Coin relevé
            corner_size = 0.3 * cm
            corner_x = page_num_x + page_num_box_size - corner_size
            corner_y = page_num_y + page_num_box_size - corner_size
            
            pdf.setFillColor(colors.HexColor("#F5F5F5"))
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.3)
            corner_path = pdf.beginPath()
            corner_path.moveTo(corner_x, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, page_num_y + page_num_box_size)
            corner_path.lineTo(page_num_x + page_num_box_size, corner_y)
            corner_path.curveTo(corner_x + corner_size * 0.3, corner_y, corner_x, corner_y - corner_size * 0.3, corner_x, page_num_y + page_num_box_size - corner_size * 0.5)
            corner_path.close()
            pdf.drawPath(corner_path, stroke=1, fill=1)
            
            # Ligne de séparation
            pdf.setLineWidth(0.3)
            pdf.setStrokeColor(colors.HexColor("#AAAAAA"))
            pdf.line(corner_x, page_num_y + page_num_box_size - corner_size * 0.5, page_num_x + page_num_box_size, corner_y)
            
            # Numéro de page
            pdf.setFillColor(colors.HexColor("#666666"))
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(
                page_num_x + page_num_box_size / 2,
                page_num_y + page_num_box_size / 2 - 3,
                str(page_number)
            )
            
            pdf.restoreState()

        # Fonction pour dessiner une entrée sigle/définition avec styling selon la source
        def draw_sigle_entry(sigle: str, definition: str, x: float, y: float, max_width: float, source: str = "default") -> float:
            """
            Dessine une entrée sigle/définition et retourne la nouvelle position Y.
            
            Args:
                sigle: Le sigle à afficher
                definition: La définition du sigle
                x: Position X de départ
                y: Position Y de départ
                max_width: Largeur maximale disponible
                source: Source de la donnée ("user", "db", ou "default")
            """
            pdf.saveState()
            
            # Déterminer la couleur selon la source
            sigle_color = cls._get_color_for_source(source)
            
            font_size = 10
            pdf.setFont("Helvetica-Bold", font_size)
            pdf.setFillColor(sigle_color)
            
            # Calculer la largeur du sigle pour savoir où placer la définition
            sigle_width = pdf.stringWidth(sigle + " :", "Helvetica-Bold", font_size)
            definition_start_x = x + sigle_width + 0.3 * cm
            
            # Tronquer la définition si nécessaire
            available_def_width = max_width - (definition_start_x - x)
            definition_to_draw = definition
            pdf.setFont("Helvetica", font_size)
            def_width = pdf.stringWidth(definition, "Helvetica", font_size)
            
            if def_width > available_def_width:
                # Tronquer avec "..."
                ellipsis_width = pdf.stringWidth("...", "Helvetica", font_size)
                available_width_for_text = available_def_width - ellipsis_width
                while pdf.stringWidth(definition_to_draw, "Helvetica", font_size) > available_width_for_text and len(definition_to_draw) > 0:
                    definition_to_draw = definition_to_draw[:-1]
                definition_to_draw = definition_to_draw + "..."
            
            # Dessiner le sigle avec la couleur appropriée
            pdf.setFont("Helvetica-Bold", font_size)
            pdf.setFillColor(sigle_color)
            pdf.drawString(x, y, sigle + " :")
            
            # Dessiner la définition avec la même couleur que le sigle
            pdf.setFont("Helvetica", font_size)
            pdf.setFillColor(sigle_color)
            pdf.drawString(definition_start_x, y, definition_to_draw)
            
            pdf.restoreState()
            
            return y - line_spacing

        # Dessiner avec pagination automatique
        page_num = start_page
        first_page = True
        sigles_remaining = sigles.copy()
        
        while sigles_remaining or first_page:
            if first_page:
                # Créer la première page
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Sigles et abréviations")
            else:
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Sigles et abréviations (suite)")
            
            pdf.saveState()
            
            # Titre "SIGLES ET ABRÉVIATIONS" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(cls.DARK_TEXT)
                pdf.setFont("Helvetica-Bold", 18)
                title_y = start_y
                pdf.drawString(left_margin, title_y, "SIGLES ET ABRÉVIATIONS")
                current_y = title_y - 1.5 * cm
            else:
                current_y = start_y
            
            # Dessiner les sigles en une seule colonne
            current_x = left_margin
            max_col_width = available_width
            
            items_to_remove = []
            
            for sigle_entry in sigles_remaining:
                sigle = sigle_entry.get("sigle", "")
                definition = sigle_entry.get("definition", "")
                
                # Déterminer la source de ce sigle spécifique
                # Priorité : USER (via modal) > DEFAULT
                # Si les sigles sont fournis via le modal (is_sigles_user), ils sont tous USER
                # Sinon, ce sont des sigles par défaut
                if is_sigles_user:
                    # Les sigles viennent de l'utilisateur via le modal = USER (vert)
                    sigle_source = "user"
                else:
                    # Les sigles sont par défaut = DEFAULT (rouge)
                    sigle_source = "default"
                
                # Vérifier si on a assez d'espace vertical pour une nouvelle ligne
                if current_y - line_spacing < content_bottom:
                    # Plus d'espace sur cette page, passer à la page suivante
                    break
                
                # Dessiner l'entrée avec le styling selon la source
                current_y = draw_sigle_entry(sigle, definition, current_x, current_y, max_col_width, sigle_source)
                
                items_to_remove.append(sigle_entry)
            
            # Retirer les éléments déjà dessinés
            for item in items_to_remove:
                sigles_remaining.remove(item)
            
            # Dessiner le footer
            draw_footer(page_num)
            
            pdf.restoreState()
            
            page_num += 1
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and sigles_remaining:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        return page_num

    
    @classmethod
    def _render_multipage_story(
        cls,
        pdf: canvas.Canvas,
        story: list,
        *,
        page_num: int,
        frame_x: float,
        frame_y: float,
        frame_width: float,
        frame_height: float,
        page_width: float,
        show_page_number: bool = True,
        draw_footer_func=None,
    ) -> int:
        """
        Rendu multi-pages d'une liste de Flowables (story) dans un Frame.

        - Utilise Frame.addFromList comme SimpleDocTemplate
        - Gère la pagination manuellement (Canvas)
        - Supporte correctement LongTable sur plusieurs pages
        """
        import logging
        logger = logging.getLogger(__name__)

        first_page = True
        current_page = page_num

        while story:
            # La première page est déjà créée avant l'appel
            if not first_page:
                pdf.showPage()

            frame = Frame(
                frame_x,
                frame_y,
                frame_width,
                frame_height,
                showBoundary=0,  # passer à 1 pour déboguer
            )

            pdf.saveState()

            before = len(story)
            logger.info(f"   📝 Page {current_page}: {before} éléments restants")

            try:
                # IMPORTANT :
                # - LongTable peut se dessiner sur plusieurs pages
                # - Il reste dans 'story' tant qu'il n'est pas fini
                #   => len(story) peut rester identique d'une page à l'autre
                frame.addFromList(story, pdf)
            except LayoutError as e:
                logger.error(
                    f"   ❌ LayoutError sur la page {current_page}: {e}. "
                    f"Arrêt du rendu pour éviter un blocage."
                )
                pdf.restoreState()
                break

            after = len(story)
            consumed = before - after
            logger.info(f"   ✅ Page {current_page}: {consumed} éléments consommés, {after} restants")

            pdf.restoreState()

            # Footer / numéro de page
            if show_page_number:
                if draw_footer_func:
                    draw_footer_func(current_page)
                else:
                    pdf.saveState()
                    pdf.setFont("Helvetica-Bold", 12)
                    pdf.drawRightString(page_width - 30, 25, str(current_page))
                    pdf.restoreState()

            # ⚠️ On NE TESTE PLUS (after == before)
            # Car pour LongTable, len(story) peut rester constant
            # tout en avançant dans le tableau.

            current_page += 1
            first_page = False

        return current_page
    
    
    
    @classmethod
    def _draw_introduction_generale(cls, pdf: canvas.Canvas, width: float, height: float, start_page: int) -> int:
        """Dessine la page d'introduction générale avec support multi-pages, justification et puces."""
        # Marges et dimensions
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin

        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            footer_y = footer_height / 2
            page_num_box_size = 1.0 * cm
            page_num_x = width - right_margin - page_num_box_size
            page_num_y = footer_y - page_num_box_size / 2
            
            pdf.saveState()
            
            # Carte blanche avec coins arrondis
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(page_num_x, page_num_y, page_num_box_size, page_num_box_size, 3, stroke=1, fill=1)
            
            # Ombre subtile
            pdf.setFillColor(colors.HexColor("#E0E0E0"))
            pdf.roundRect(page_num_x + 0.05 * cm, page_num_y - 0.05 * cm, page_num_box_size, page_num_box_size, 3, stroke=0, fill=1)
            
            # Coins recourbés (coin supérieur droit)
            corner_size = 0.3 * cm
            corner_x = page_num_x + page_num_box_size - corner_size
            corner_y = page_num_y + page_num_box_size
            
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#AAAAAA"))
            pdf.setLineWidth(0.3)
            pdf.line(corner_x, page_num_y + page_num_box_size - corner_size * 0.5, page_num_x + page_num_box_size, corner_y)
            
            # Numéro de page
            pdf.setFillColor(colors.HexColor("#666666"))
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(
                page_num_x + page_num_box_size / 2,
                page_num_y + page_num_box_size / 2 - 3,
                str(page_number)
            )
            
            pdf.restoreState()

        # Styles pour les paragraphes
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "IntroductionTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=0,  # Gauche
            spaceAfter=20,
        )
        body_style = ParagraphStyle(
            "IntroductionBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
        )
        bullet_style = ParagraphStyle(
            "IntroductionBullet",
            parent=styles["Normal"],
            bulletFontName="Helvetica",
            bulletFontSize=11,
            fontName="Helvetica",
            fontSize=11,
            alignment=TA_JUSTIFY,
            leading=16,
            leftIndent=30,
            bulletIndent=15,
            spaceAfter=4,
        )

        # Récupérer les données d'introduction
        intro_data = cls.data.get("introduction", {})
        if not intro_data:
            intro_data = cls.DEFAULT_DATA.get("introduction", {})
        
        # Les données DB sont déjà chargées au début dans generate_pdf()
        # Utiliser directement _db_data_keys pour déterminer les sources
        
        # Récupérer les valeurs par défaut pour comparaison
        default_intro_data = cls.DEFAULT_DATA.get("introduction", {})
        
        # Fonction helper pour récupérer une valeur principale (ministere, annee, etc.) avec priorité USER > DB > DEFAULT
        def get_main_value(key: str, default_value: Any = None) -> tuple[Any, str]:
            """
            Récupère une valeur principale avec priorité USER > DB > DEFAULT.
            Utilise _db_data_keys qui est déjà initialisé au début de generate_pdf().
            
            Returns:
                Tuple (valeur, source) où source est "user", "db", ou "default"
            """
            value = cls.data.get(key, cls.DEFAULT_DATA.get(key, default_value))
            
            # Priorité 1: USER (via modal)
            if key in cls._user_data_keys:
                return value, "user"
            
            # Priorité 2: DB (SystemSettings - déjà chargé au début)
            if key in cls._db_data_keys:
                return value, "db"
            
            # Priorité 3: DEFAULT
            return value, "default"
        
        # Fonction helper pour récupérer une valeur d'introduction avec priorité USER > DB > DEFAULT
        def get_intro_value(key: str, default_value: Any = None) -> tuple[Any, str]:
            """
            Récupère une valeur d'introduction avec priorité USER > DB > DEFAULT.
            Utilise _db_data_keys qui est déjà initialisé au début de generate_pdf().
            
            Returns:
                Tuple (valeur, source) où source est "user", "db", ou "default"
            """
            value = intro_data.get(key, default_intro_data.get(key, default_value))
            intro_key = f"introduction.{key}"
            
            # Priorité 1: USER (via modal)
            if "introduction" in cls._user_data_keys:
                user_value = intro_data.get(key)
                if user_value is not None and user_value != "":
                    default_value_for_key = default_intro_data.get(key)
                    if default_value_for_key is None or user_value != default_value_for_key:
                        return user_value, "user"
            
            # Priorité 2: DB (SystemSettings - déjà chargé au début)
            if intro_key in cls._db_data_keys:
                return value, "db"
            
            # Priorité 3: DEFAULT
            return value, "default"
        
        # Récupérer toutes les valeurs avec leur source
        ministre_nom, ministre_nom_source = get_intro_value("ministre_nom", "")
        ministre_date, ministre_date_source = get_intro_value("ministre_date_nomination", "")
        decret_attr_num, decret_attr_num_source = get_intro_value("decret_attribution_numero", "")
        decret_attr_date, decret_attr_date_source = get_intro_value("decret_attribution_date", "")
        mission_ministere, mission_source = get_intro_value(
            "mission_ministere",
            "mettre en œuvre la politique du Gouvernement en matière de gestion du patrimoine, du portefeuille de l'État et des entreprises publiques"
        )
        # Récupérer toutes les autres valeurs avec leur source
        structure_cabinet, structure_cabinet_source = get_intro_value("structure_cabinet", "")
        nb_directions, nb_directions_source = get_intro_value("structure_directions_centrales", 0)
        nb_services, nb_services_source = get_intro_value("structure_services", 0)
        nb_dg, nb_dg_source = get_intro_value("structure_directions_generales", 0)
        decret_org_num, decret_org_num_source = get_intro_value("decret_organisation_numero", "")
        decret_org_date, decret_org_date_source = get_intro_value("decret_organisation_date", "")
        contexte_texte, contexte_texte_source = get_intro_value("contexte_texte", "")
        premiere_partie_items, premiere_partie_items_source = get_intro_value("rapport_structure_premiere_partie", [])
        seconde_partie_items, seconde_partie_items_source = get_intro_value("rapport_structure_seconde_partie", [])
        
        # Construire la story avec Paragraph et puces
        story: list[Any] = []
        
        # Titre
        story.append(Paragraph("INTRODUCTION GÉNÉRALE", title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Formater chaque valeur selon sa source déterminée par get_intro_value
        def format_by_source(value: Any, source: str) -> str:
            """Formate une valeur selon sa source."""
            if not value:
                return ""
            if source == "user":
                return cls._format_user_data(str(value))
            elif source == "db":
                return cls._format_db_data(str(value))
            else:  # default
                return cls._format_default_data(str(value))
        
        # Récupérer le nom du ministère avec sa source
        ministere_value, ministere_source = get_main_value("ministere", "MINISTERE DU PATRIMOINE, DU PORTEFEUILLE DE L'ÉTAT ET DES ENTREPRISES PUBLIQUES")
        formatted_ministere = format_by_source(ministere_value, ministere_source)
        
        formatted_ministre_nom = format_by_source(ministre_nom, ministre_nom_source)
        formatted_ministre_date = format_by_source(ministre_date, ministre_date_source)
        formatted_decret_attr_num = format_by_source(decret_attr_num, decret_attr_num_source)
        formatted_decret_attr_date = format_by_source(decret_attr_date, decret_attr_date_source)
        formatted_mission = format_by_source(mission_ministere, mission_source)
        
        para1 = (
            f"Le {formatted_ministere} (MPPEEP) est dirigé par {formatted_ministre_nom} depuis le {formatted_ministre_date}. "
            f"Sa mission est de {formatted_mission}. Cette mission "
            f"lui a été confiée conformément au décret {formatted_decret_attr_num} du {formatted_decret_attr_date} "
            f"portant attributions des membres du Gouvernement."
        )
        story.append(Paragraph(para1, body_style))
        
        # Paragraphe 2 : Structure organisationnelle (avec styling selon la source)
        formatted_structure_cabinet = format_by_source(structure_cabinet, structure_cabinet_source) if structure_cabinet else cls._format_default_data("Cabinet du Ministre")
        structure_desc = formatted_structure_cabinet if structure_cabinet else cls._format_default_data("Cabinet du Ministre")
        
        # Formater les nombres selon la source
        formatted_nb_directions = format_by_source(str(nb_directions), nb_directions_source) if nb_directions > 0 else ""
        formatted_nb_services = format_by_source(str(nb_services), nb_services_source) if nb_services > 0 else ""
        formatted_nb_dg = format_by_source(str(nb_dg), nb_dg_source) if nb_dg > 0 else ""
        
        directions_text = f"{formatted_nb_directions} Direction{'s' if nb_directions > 1 else ''} centrale{'s' if nb_directions > 1 else ''}" if nb_directions > 0 else ""
        services_text = f"{formatted_nb_services} Service{'s' if nb_services > 1 else ''}" if nb_services > 0 else ""
        dg_text = f"{formatted_nb_dg} Direction{'s' if nb_dg > 1 else ''} Générale{'s' if nb_dg > 1 else ''}" if nb_dg > 0 else ""
        
        structure_parts = [structure_desc]
        if directions_text:
            structure_parts.append(directions_text)
        if services_text:
            structure_parts.append(services_text)
        if dg_text:
            structure_parts.append(dg_text)
        
        structure_list = ", ".join(structure_parts[:-1])
        if len(structure_parts) > 1:
            structure_list += f" et {structure_parts[-1]}"
        else:
            structure_list = structure_parts[0]
        
        formatted_decret_org_num = format_by_source(decret_org_num, decret_org_num_source)
        formatted_decret_org_date = format_by_source(decret_org_date, decret_org_date_source)
        
        para2 = (
            f"Pour mener efficacement ses missions, le {formatted_ministere} s'appuie sur une organisation "
            f"administrative structurée autour du {structure_list}, conformément au décret "
            f"{formatted_decret_org_num} du {formatted_decret_org_date} portant organisation du ministère."
        )
        story.append(Paragraph(para2, body_style))
        
        # Paragraphe 3 : Contexte (avec styling selon la source)
        if contexte_texte:
            annee_value, annee_source = get_main_value("annee", 2024)
            formatted_annee_para3 = format_by_source(str(annee_value), annee_source)
            formatted_decret_org_num_para3 = format_by_source(decret_org_num, decret_org_num_source)
            formatted_decret_org_date_para3 = format_by_source(decret_org_date, decret_org_date_source)
            
            formatted_contexte = format_by_source(contexte_texte, contexte_texte_source)
            
            para3 = formatted_contexte.format(
                annee=formatted_annee_para3,
                ministere=formatted_ministere,
                decret_organisation_numero=formatted_decret_org_num_para3,
                decret_organisation_date=formatted_decret_org_date_para3
            )
            story.append(Paragraph(para3, body_style))
        
        # Paragraphe 4 : Structure du rapport (avec styling selon la source)
        annee_value, annee_source = get_main_value("annee", 2024)
        formatted_annee_para4 = format_by_source(str(annee_value), annee_source)
        
        para4_intro = (
            f"Le présent rapport détaille les activités du {formatted_ministere} pour l'exercice {formatted_annee_para4} "
            f"et s'articule autour de deux grandes parties."
        )
        story.append(Paragraph(para4_intro, body_style))
        
        # Première partie avec puces (avec styling selon la source de la liste)
        if premiere_partie_items:
            story.append(Paragraph("La première partie permettra de :", body_style))
            for item in premiere_partie_items:
                # Tous les items de la liste ont la même source que la liste
                formatted_item = format_by_source(item, premiere_partie_items_source)
                story.append(Paragraph(formatted_item, bullet_style, bulletText="•"))
        
        # Seconde partie avec puces (avec styling selon la source de la liste)
        if seconde_partie_items:
            story.append(Paragraph("La seconde partie abordera la performance de chaque programme à travers :", body_style))
            for item in seconde_partie_items:
                formatted_annee_in_item = cls._format_data_value("annee")
                formatted_item = item.format(annee=formatted_annee_in_item) if "{annee}" in item else item
                # Tous les items de la liste ont la même source que la liste
                formatted_item_final = format_by_source(formatted_item, seconde_partie_items_source)
                story.append(Paragraph(formatted_item_final, bullet_style, bulletText="•"))
        
        # Créer la première page
        pdf.showPage()
        logger.info(f"📄 Page {start_page}: Introduction générale")
        
        # Rendre la story avec pagination automatique
        final_page = cls._render_multipage_story(
            pdf,
            story,
            page_num=start_page,
            frame_x=left_margin,
            frame_y=bottom_margin,
            frame_width=available_width,
            frame_height=available_height,
            page_width=width,
            show_page_number=True,
            draw_footer_func=draw_footer,
        )
        
        return final_page

    @classmethod
    def _draw_partie_i_ministere(cls, pdf: canvas.Canvas, width: float, height: float, start_page: int) -> int:
        """Dessine la PARTIE I : LE MINISTÈRE avec support multi-pages."""
        # Marges et dimensions
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin

        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            footer_y = footer_height / 2
            page_num_box_size = 1.0 * cm
            page_num_x = width - right_margin - page_num_box_size
            page_num_y = footer_y - page_num_box_size / 2
            
            pdf.saveState()
            
            # Carte blanche avec coins arrondis
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#CCCCCC"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(page_num_x, page_num_y, page_num_box_size, page_num_box_size, 3, stroke=1, fill=1)
            
            # Ombre subtile
            pdf.setFillColor(colors.HexColor("#E0E0E0"))
            pdf.roundRect(page_num_x + 0.05 * cm, page_num_y - 0.05 * cm, page_num_box_size, page_num_box_size, 3, stroke=0, fill=1)
            
            # Coins recourbés (coin supérieur droit)
            corner_size = 0.3 * cm
            corner_x = page_num_x + page_num_box_size - corner_size
            corner_y = page_num_y + page_num_box_size
            
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#AAAAAA"))
            pdf.setLineWidth(0.3)
            pdf.line(corner_x, page_num_y + page_num_box_size - corner_size * 0.5, page_num_x + page_num_box_size, corner_y)
            
            # Numéro de page
            pdf.setFillColor(colors.HexColor("#666666"))
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(
                page_num_x + page_num_box_size / 2,
                page_num_y + page_num_box_size / 2 - 3,
                str(page_number)
            )
            
            pdf.restoreState()

        # Styles pour les paragraphes
        styles = getSampleStyleSheet()
        partie_title_style = ParagraphStyle(
            "PartieTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=0,  # Gauche
            spaceAfter=15,
        )
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,  # Gauche
            spaceAfter=6,
            spaceBefore=6,
        )
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=0,  # Gauche
            spaceAfter=5,
            spaceBefore=5,
        )
        body_style = ParagraphStyle(
            "PartieBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=5,
        )
        source_style = ParagraphStyle(
            "SourceStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=0,  # Gauche
            spaceAfter=5,
            leftIndent=0,
            textColor=colors.HexColor("#666666"),
        )
        
        # Récupérer les données
        ministere = cls.data.get("ministere", "")
        annee = cls.data.get("annee", 2024)
        programmes = cls.data.get("programmes", [])
        if not programmes:
            programmes = cls.DEFAULT_DATA.get("programmes", [])
        
        # Récupérer les données de la partie ministère (ou utiliser des valeurs par défaut)
        partie_data = cls.data.get("partie_ministere", {})
        if not partie_data:
            # Calculer les totaux à partir des programmes
            total_actions = 0
            total_activites = 0
            programme_details = []
            for prog in programmes:
                num = prog.get("numero", 1)
                titre = prog.get("titre", "")
                actions = prog.get("nb_actions", 3)  # Valeur par défaut
                activites = prog.get("nb_activites", 0)
                programme_details.append({
                    "numero": num,
                    "titre": titre,
                    "actions": actions,
                    "activites": activites,
                })
                total_actions += actions
                total_activites += activites
            
            # Calculer les pourcentages
            if total_activites > 0:
                prog1_pct = (programme_details[0]["activites"] / total_activites * 100) if len(programme_details) > 0 else 0
                prog2_pct = (programme_details[1]["activites"] / total_activites * 100) if len(programme_details) > 1 else 0
            else:
                prog1_pct = 55.17
                prog2_pct = 44.83
                total_actions = 6
                total_activites = 58
                programme_details = [
                    {"numero": 1, "titre": "Administration Générale", "actions": 3, "activites": 32},
                    {"numero": 2, "titre": "Portefeuille de l'Etat", "actions": 3, "activites": 26},
                ]
            
            partie_data = {
                "total_programmes": len(programmes) if programmes else 2,
                "total_actions": total_actions,
                "total_activites": total_activites,
                "programme_details": programme_details,
                "prog1_pct": prog1_pct,
                "prog2_pct": prog2_pct,
                "source": f"Source: Annexe 4 de la Loi de Finances n° 2023-1000 du 18 décembre 2023 portant budget de l'Etat pour l'année {annee}",
                "orientations": [
                    {
                        "orientation": "l'amélioration de la gouvernance liée au fonctionnement et à la qualité des services du Ministère.",
                        "resultat": "la gouvernance du secteur est améliorée",
                        "objectif": "améliorer la gouvernance du secteur"
                    },
                    {
                        "orientation": "l'amélioration de la compétitivité des entreprises publiques",
                        "resultat": "la gestion des entreprises publiques et parapubliques est améliorée",
                        "objectif": "assurer la gestion efficace du portefeuille de l'Etat"
                    }
                ],
                "performance": {
                    "architecture": {
                        "nb_programmes": 2,
                        "nb_objectifs_globaux": 2,
                        "nb_objectifs_specifiques": 4,
                        "nb_indicateurs": 8,
                        "nb_cibles": 8,
                    },
                    "realisations": [
                        {
                            "programme": "P1: Administration Générale",
                            "objectif_specifique": "OS 1: Améliorer la coordination et le fonctionnement des structures",
                            "nb_cibles": 1,
                            "nb_cibles_atteintes": 1,
                        },
                        {
                            "programme": "P2: Portefeuille de l'Etat",
                            "objectif_specifique": "OS 1:: Améliorer la gestion de l'administration du Portefeuille de l'État",
                            "nb_cibles": 2,
                            "nb_cibles_atteintes": 2,
                        },
                        {
                            "programme": "P2: Portefeuille de l'Etat",
                            "objectif_specifique": "OS 2: Assurer le positionnement du Portefeuille de l'État comme un accélérateur de développement",
                            "nb_cibles": 3,
                            "nb_cibles_atteintes": 3,
                        },
                        {
                            "programme": "P2: Portefeuille de l'Etat",
                            "objectif_specifique": "OS 3: Améliorer le dispositif de contrôle des entreprises publiques",
                            "nb_cibles": 2,
                            "nb_cibles_atteintes": 2,
                        },
                    ],
                    "taux_realisation": 100,
                    "nb_indicateurs_2023": 7,
                    "taux_realisation_2023": 100,
                }
            }
        
        # Construire la story
        story: list[Any] = []
        
        # Titre de la partie
        story.append(Paragraph("PARTIE I : LE MINISTÈRE", partie_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Section I. PRESENTATION GENERALE DU MINISTERE
        story.append(Paragraph("I. PRÉSENTATION GÉNÉRALE DU MINISTÈRE", section_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # I.1. Architecture programmatique du Ministère
        # Paragraphe introductif
        prog1_detail = partie_data["programme_details"][0] if len(partie_data["programme_details"]) > 0 else {}
        prog2_detail = partie_data["programme_details"][1] if len(partie_data["programme_details"]) > 1 else {}
        prog1_pct = partie_data.get("prog1_pct", 55.17)
        prog2_pct = partie_data.get("prog2_pct", 44.83)
        
        prog1_titre = prog1_detail.get('titre', 'Administration Générale')
        prog2_titre = prog2_detail.get('titre', 'Portefeuille de l\'Etat')
        para1_text = (
            f"Le {ministere} (MPPEEP) est subdivisé en {partie_data['total_programmes']} programmes déclinés en "
            f"{partie_data['total_actions']} actions comprenant {partie_data['total_activites']} activités. "
            f"Le programme « {prog1_titre} » enregistre "
            f"{prog1_detail.get('activites', 32)} activités ({prog1_pct:.2f}%) et le programme "
            f"« {prog2_titre} » "
            f"{prog2_detail.get('activites', 26)} activités ({prog2_pct:.2f}%)."
        )
        # Ajouter CondPageBreak pour éviter que le titre soit orphelin
        story.append(CondPageBreak(3 * cm))  # S'assure qu'il y a au moins 3 cm d'espace avant le titre
        story.append(Paragraph("I.1. Architecture programmatique du Ministère", subsection_title_style))
        story.append(Paragraph(para1_text, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Tableau : Récapitulatif des actions et activités par programme
        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=1,  # Centré
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=0,  # Gauche
        )
        table_cell_center_style = ParagraphStyle(
            "TableCellCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=1,  # Centré
        )
        
        # Données du tableau
        table_data = [
            [
                Paragraph("Programmes", table_header_style),
                Paragraph("Actions", table_header_style),
                Paragraph("Activités", table_header_style),
            ]
        ]
        
        for prog_detail in partie_data["programme_details"]:
            prog_num = prog_detail['numero']
            prog_titre = prog_detail['titre']
            table_data.append([
                Paragraph(f"Programme {prog_num} : {prog_titre}", table_cell_style),
                Paragraph(str(prog_detail["actions"]), table_cell_center_style),
                Paragraph(str(prog_detail["activites"]), table_cell_center_style),
            ])
        
        # Ligne Total
        table_data.append([
            Paragraph("Total", ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=0)),
            Paragraph(str(partie_data["total_actions"]), ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
            Paragraph(str(partie_data["total_activites"]), ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
        ])
        
        # Créer le tableau
        col_widths = [
            available_width * 0.60,  # Programmes
            available_width * 0.20,  # Actions
            available_width * 0.20,  # Activités
        ]
        
        # repeatRows=1 permet de répéter les en-têtes sur chaque page si le tableau est divisé
        recap_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        recap_table.setStyle(
            TableStyle([
                # Bordures
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                # En-têtes
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Première colonne à gauche
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),  # Autres colonnes centrées
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Ligne Total
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),
                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        
        # Ajouter le titre du tableau et le tableau ensemble
        story.append(Paragraph("Tableau : Récapitulatif des actions et activités par programme", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(recap_table)
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(partie_data.get("source", ""), source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # I.2. Politique ministérielle
        para2_text = (
            f"Le {ministere} (MPPEEP) a articulé sa politique sectorielle autour de "
            f"{len(partie_data.get('orientations', []))} orientations stratégiques, "
            f"{len(partie_data.get('orientations', []))} résultats stratégiques et "
            f"{len(partie_data.get('orientations', []))} objectifs globaux."
        )
        # Ajouter CondPageBreak pour éviter que le titre soit orphelin
        story.append(CondPageBreak(3 * cm))  # S'assure qu'il y a au moins 3 cm d'espace avant le titre
        story.append(Paragraph("I.2. Politique ministérielle", subsection_title_style))
        story.append(Paragraph(para2_text, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Tableau : Orientations stratégiques, Résultats stratégiques, Objectifs globaux
        politique_table_data = [
            [
                Paragraph("Orientations stratégiques", table_header_style),
                Paragraph("Résultats stratégiques", table_header_style),
                Paragraph("Objectifs globaux", table_header_style),
            ]
        ]
        
        for orientation_data in partie_data.get("orientations", []):
            politique_table_data.append([
                Paragraph(orientation_data.get("orientation", ""), table_cell_style),
                Paragraph(orientation_data.get("resultat", ""), table_cell_style),
                Paragraph(orientation_data.get("objectif", ""), table_cell_style),
            ])
        
        # Largeurs égales pour les trois colonnes
        politique_col_widths = [
            available_width / 3,
            available_width / 3,
            available_width / 3,
        ]
        
        # repeatRows=1 permet de répéter les en-têtes sur chaque page si le tableau est divisé
        politique_table = Table(politique_table_data, colWidths=politique_col_widths, repeatRows=1)
        politique_table.setStyle(
            TableStyle([
                # Bordures
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                # En-têtes
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        
        # Ajouter le tableau (sans titre car il n'y en a pas dans l'image)
        story.append(politique_table)
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(partie_data.get("source", ""), source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Section II. PERFORMANCE GENERALE DU MINISTERE
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II. PERFORMANCE GÉNÉRALE DU MINISTÈRE", section_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # II.1. Architecture du cadre de performance
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II.1. Architecture du cadre de performance", subsection_title_style))
        
        # Tableau 1: Composantes des cadres de performance du ministère
        performance_data = partie_data.get("performance", {})
        architecture_data = performance_data.get("architecture", {})
        
        tableau1_data = [
            [
                Paragraph("Composantes", table_header_style),
                Paragraph("Programmes", table_header_style),
                Paragraph("Objectifs globaux (OG)", table_header_style),
                Paragraph("Objectifs spécifiques (OS)", table_header_style),
                Paragraph("Indicateurs liés aux OS", table_header_style),
                Paragraph("Cibles liées aux indicateurs et OS", table_header_style),
            ],
            [
                Paragraph("Nombre", table_cell_style),
                Paragraph(str(architecture_data.get("nb_programmes", 2)), table_cell_center_style),
                Paragraph(str(architecture_data.get("nb_objectifs_globaux", 2)), table_cell_center_style),
                Paragraph(str(architecture_data.get("nb_objectifs_specifiques", 4)), table_cell_center_style),
                Paragraph(str(architecture_data.get("nb_indicateurs", 8)), table_cell_center_style),
                Paragraph(str(architecture_data.get("nb_cibles", 8)), table_cell_center_style),
            ]
        ]
        
        tableau1_col_widths = [
            available_width * 0.25,  # Composantes
            available_width * 0.15,  # Programmes
            available_width * 0.15,  # Objectifs globaux
            available_width * 0.15,  # Objectifs spécifiques
            available_width * 0.15,  # Indicateurs
            available_width * 0.15,  # Cibles
        ]
        
        # repeatRows=1 permet de répéter les en-têtes sur chaque page si le tableau est divisé
        tableau1 = Table(tableau1_data, colWidths=tableau1_col_widths, repeatRows=1)
        tableau1.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (0, 1), "LEFT"),
                ("ALIGN", (1, 1), (-1, 1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        
        story.append(Paragraph("Tableau 1: Composantes des cadres de performance du ministère", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(tableau1)
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(partie_data.get("source", ""), source_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe après tableau 1
        para_architecture = (
            f"Pour l'exercice {annee}, le {ministere} (MPPEEP) a structuré sa stratégie en "
            f"{architecture_data.get('nb_programmes', 2)} programmes, visant {architecture_data.get('nb_objectifs_globaux', 2)} objectifs globaux (OG), "
            f"qui sont déclinés en {architecture_data.get('nb_objectifs_specifiques', 4)} objectifs spécifiques (OS). "
            f"Pour mesurer ces objectifs, {architecture_data.get('nb_indicateurs', 8)} indicateurs ont été définis, "
            f"chacun étant associé à une cible précise permettant d'évaluer les progrès accomplis."
        )
        story.append(Paragraph(para_architecture, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # II.2. Bilan des données globales du cadre de performance
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II.2. Bilan des données globales du cadre de performance", subsection_title_style))
        
        # Tableau 2: Réalisations du cadre de performance du ministère
        realisations = performance_data.get("realisations", [])
        
        tableau2_data = [
            [
                Paragraph("Programmes (a)", table_header_style),
                Paragraph("Objectifs Spécifiques (OS) (b)", table_header_style),
                Paragraph("Nombre de cibles (c)", table_header_style),
                Paragraph("Nombre de cibles atteintes (d)", table_header_style),
            ]
        ]
        
        total_cibles = 0
        total_cibles_atteintes = 0
        current_programme = None
        
        for realisation in realisations:
            prog = realisation.get("programme", "")
            os = realisation.get("objectif_specifique", "")
            nb_cibles = realisation.get("nb_cibles", 0)
            nb_atteintes = realisation.get("nb_cibles_atteintes", 0)
            
            total_cibles += nb_cibles
            total_cibles_atteintes += nb_atteintes
            
            # Si c'est le même programme, on ne répète pas le nom
            programme_cell = Paragraph(prog, table_cell_style) if prog != current_programme else Paragraph("", table_cell_style)
            if prog != current_programme:
                current_programme = prog
            
            tableau2_data.append([
                programme_cell,
                Paragraph(os, table_cell_style),
                Paragraph(str(nb_cibles), table_cell_center_style),
                Paragraph(str(nb_atteintes), table_cell_center_style),
            ])
        
        # Ligne Total
        tableau2_data.append([
            Paragraph("TOTAL", ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=0)),
            Paragraph("", table_cell_style),
            Paragraph(str(total_cibles), ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
            Paragraph(str(total_cibles_atteintes), ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
        ])
        
        tableau2_col_widths = [
            available_width * 0.25,  # Programmes
            available_width * 0.45,  # Objectifs Spécifiques
            available_width * 0.15,  # Nombre de cibles
            available_width * 0.15,  # Nombre de cibles atteintes
        ]
        
        # repeatRows=1 permet de répéter les en-têtes sur chaque page si le tableau est divisé
        tableau2 = Table(tableau2_data, colWidths=tableau2_col_widths, repeatRows=1)
        tableau2.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (1, -2), "LEFT"),
                ("ALIGN", (2, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        
        story.append(Paragraph("Tableau 2: Réalisations du cadre de performance du ministère", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(tableau2)
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(partie_data.get("source", ""), source_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphes après tableau 2
        taux_realisation = performance_data.get("taux_realisation", 100)
        nb_indicateurs_2023 = performance_data.get("nb_indicateurs_2023", 7)
        taux_realisation_2023 = performance_data.get("taux_realisation_2023", 100)
        
        para_bilan1 = (
            f"Pour l'année {annee}, l'analyse du cadre de performance du ministère, tel que présenté dans le "
            f"« Document de Programmation Pluriannuelle de Dépenses Projet Annuel de Performance (DPPD-PAP) », "
            f"révèle que {architecture_data.get('nb_indicateurs', 8)} indicateurs ont été définis pour les programmes P1 et P2. "
            f"L'ensemble de ces indicateurs a atteint les objectifs fixés, ce qui correspond à un taux de réalisation de {taux_realisation}%."
        )
        story.append(Paragraph(para_bilan1, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        para_bilan2 = (
            f"Par rapport à {annee - 1}, où les {nb_indicateurs_2023} indicateurs de performance évalués avaient également atteint leurs objectifs, "
            f"une continuité dans les résultats est observée. Ce fort taux de réalisation traduit la capacité du Ministère "
            f"à définir des objectifs structurants et à mobiliser de manière optimale les ressources nécessaires à leur atteinte. "
            f"Les performances en {annee - 1} et {annee} démontrent une cohérence dans la gestion et l'atteinte des objectifs fixés."
        )
        story.append(Paragraph(para_bilan2, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Section III. FINANCEMENT GLOBAL DU MINISTERE
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("III. FINANCEMENT GLOBAL DU MINISTÈRE", section_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Récupérer les données de financement
        financement_data = cls.data.get("financement_global", {})
        budget_initial_total = financement_data.get("budget_initial_total", 18490983290)  # Valeur par défaut
        budget_reel_total = financement_data.get("budget_reel_total", 39793641653)  # Valeur par défaut
        evolution_total = budget_reel_total - budget_initial_total
        taux_evolution_total = (evolution_total / budget_initial_total * 100) if budget_initial_total > 0 else 0
        
        # Récupérer les données par nature
        financement_par_nature = financement_data.get("par_nature", {})
        
        # Données par défaut si aucune donnée n'est disponible
        if not financement_par_nature:
            financement_par_nature = {
                "P": {"libelle": "Personnel", "budget_initial": 6825256992, "budget_reel": 7144113239, "evolution": 318856247, "taux_evolution": 4.7},
                "BS": {"libelle": "Biens et Services", "budget_initial": 7494612762, "budget_reel": 9280897588, "evolution": 1786284826, "taux_evolution": 23.8},
                "T": {"libelle": "Transferts", "budget_initial": 671113536, "budget_reel": 14934916699, "evolution": 14263803163, "taux_evolution": 2125.9},
                "I": {"libelle": "Investissements", "budget_initial": 3500000000, "budget_reel": 8433714127, "evolution": 4933714127, "taux_evolution": 140.96},
            }
        
        # Formatage des montants en FCFA avec espaces comme séparateurs
        def format_fcfa(montant: float) -> str:
            """Formate un montant en FCFA avec espaces comme séparateurs de milliers."""
            return f"{montant:,.0f}".replace(",", " ")
        
        # Récupérer les montants par nature
        personnel_init = financement_par_nature.get("P", {}).get("budget_initial", 6825256992)
        personnel_reel = financement_par_nature.get("P", {}).get("budget_reel", 7144113239)
        personnel_evol = financement_par_nature.get("P", {}).get("evolution", 318856247)
        personnel_taux = financement_par_nature.get("P", {}).get("taux_evolution", 4.7)
        
        biens_init = financement_par_nature.get("BS", {}).get("budget_initial", 7494612762)
        biens_reel = financement_par_nature.get("BS", {}).get("budget_reel", 9280897588)
        biens_evol = financement_par_nature.get("BS", {}).get("evolution", 1786284826)
        biens_taux = financement_par_nature.get("BS", {}).get("taux_evolution", 23.8)
        
        transferts_init = financement_par_nature.get("T", {}).get("budget_initial", 671113536)
        transferts_reel = financement_par_nature.get("T", {}).get("budget_reel", 14934916699)
        transferts_evol = financement_par_nature.get("T", {}).get("evolution", 14263803163)
        
        investissements_init = financement_par_nature.get("I", {}).get("budget_initial", 3500000000)
        investissements_reel = financement_par_nature.get("I", {}).get("budget_reel", 8433714127)
        investissements_evol = financement_par_nature.get("I", {}).get("evolution", 4933714127)
        
        # Récupérer les interprétations personnalisées ou utiliser les valeurs par défaut
        financement_interpretations = cls.data.get("financement_interpretations", {})
        
        # Paragraphe introductif
        para_intro = financement_interpretations.get("intro", (
            f"Au titre de l'exercice {annee}, le {ministere} (MPPEEP) a bénéficié d'un budget initial "
            f"de {format_fcfa(budget_initial_total)} FCFA (<b>Annexe 4, loi des finances {annee}</b>) dont "
            f"{format_fcfa(personnel_init)} F CFA de personnel, {format_fcfa(biens_init)} F CFA de biens et services, "
            f"{format_fcfa(transferts_init)} FCFA de transfert et {format_fcfa(investissements_init)} FCFA d'investissement. "
            f"À la suite des ajustements opérés en cours d'exercice, le budget actuel pour l'année {annee} est ressorti à "
            f"{format_fcfa(budget_reel_total)} FCFA, soit une augmentation de {format_fcfa(abs(evolution_total))} FCFA "
            f"correspondant à {abs(taux_evolution_total):.2f} %. Cette hausse s'explique principalement par les raisons suivantes :"
        ))
        story.append(Paragraph(para_intro, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Puces pour les raisons de l'augmentation
        raisons_augmentation = financement_interpretations.get("raisons_augmentation", [
            "le rattachement en cours de gestion des crédits de la SONAPIE, structure institutionnellement rattachée au MPPEEP mais dont les crédits ne figuraient pas dans la Loi de finances initiale du Ministère ;",
            "la création en cours de gestion du projet de recensement et de sécurisation du patrimoine immobilier de l'Etat en Côte d'Ivoire et à l'étranger (Voir attestation n°070/SGG/CM du 13 mars 2024) ;",
        ])
        
        bullet_style = ParagraphStyle(
            "FinancementBullet",
            parent=styles["Normal"],
            bulletFontName="Helvetica",
            bulletFontSize=11,
            fontName="Helvetica",
            fontSize=11,
            alignment=TA_JUSTIFY,
            leading=16,
            leftIndent=30,
            bulletIndent=15,
            spaceAfter=4,
        )
        
        for raison in raisons_augmentation:
            story.append(Paragraph(raison, bullet_style, bulletText="•"))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe d'introduction pour l'évolution par nature
        para_evolution_intro = financement_interpretations.get("evolution_intro", 
            "L'évolution des ressources budgétaires du ministère par nature de dépenses se présente comme suit :"
        )
        story.append(Paragraph(para_evolution_intro, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Puces pour chaque nature de dépense
        evolution_personnel = financement_interpretations.get("evolution_personnel", (
            f"<b>Dépenses de personnel :</b> Le budget passe de {format_fcfa(personnel_init)} FCFA "
            f"(<b>Annexe 4, loi des finances {annee}</b>) à {format_fcfa(personnel_reel)} FCFA (budget actuel {annee}), "
            f"soit une augmentation de {format_fcfa(personnel_evol)} FCFA, représentant une hausse modérée de + {personnel_taux:.1f} %."
        ))
        story.append(Paragraph(evolution_personnel, bullet_style, bulletText="•"))
        
        evolution_biens = financement_interpretations.get("evolution_biens", (
            f"<b>Biens et services :</b> Le budget alloué a augmenté de {format_fcfa(biens_evol)} FCFA, "
            f"passant de {format_fcfa(biens_init)} FCFA (<b>Annexe 4, loi des finances {annee}</b>) à "
            f"{format_fcfa(biens_reel)} FCFA (budget actuel {annee}), soit une progression de +{biens_taux:.1f}%."
        ))
        story.append(Paragraph(evolution_biens, bullet_style, bulletText="•"))
        
        evolution_transferts = financement_interpretations.get("evolution_transferts", (
            f"<b>Transferts :</b> En raison du rattachement de la SONAPIE, cette nature enregistre une évolution exceptionnelle, "
            f"passant de {format_fcfa(transferts_init)} FCFA (<b>Annexe 4, loi des finances {annee}</b>) à "
            f"{format_fcfa(transferts_reel)} FCFA (budget actuel {annee}), soit une augmentation de {format_fcfa(transferts_evol)} FCFA."
        ))
        story.append(Paragraph(evolution_transferts, bullet_style, bulletText="•"))
        
        evolution_investissements = financement_interpretations.get("evolution_investissements", (
            f"<b>Investissements :</b> Le budget est passé de {format_fcfa(investissements_init)} FCFA "
            f"(<b>Annexe 4, loi des finances {annee}</b>) à {format_fcfa(investissements_reel)} FCFA (budget actuel {annee}), "
            f"soit une hausse de {format_fcfa(investissements_evol)} FCFA."
        ))
        story.append(Paragraph(evolution_investissements, bullet_style, bulletText="•"))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Note sur la comparaison 2023-2024
        note_comparaison = financement_interpretations.get("note_comparaison", (
            f"<b>NB :</b> Toute comparaison entre le financement global du ministère pour {annee - 1} et {annee} "
            f"est particulièrement délicate en raison des spécificités de l'exercice {annee - 1}. "
            f"Comme mentionné dans l'introduction, le MPPEEP a hérité de la gestion des programmes "
            f"« Administration Générale » et « Portefeuille de l'État », précédemment rattachés à l'ancien "
            f"Ministère du Budget et du Portefeuille de l'État (MBPE). "
            f"Alors que le programme « Portefeuille de l'État » a maintenu une certaine continuité dans ses "
            f"responsabilités entre {annee - 1} et {annee}, le programme « Administration Générale » a connu "
            f"une réduction significative de son périmètre, passant de cinq programmes opérationnels coordonnés "
            f"à un seul. Cette évolution a conduit à une forte contraction des crédits budgétaires associés, "
            f"rendant {annee - 1} moins pertinente comme base de référence pour analyser l'allocation globale du MPPEEP. "
            f"Par ailleurs, la structure budgétaire du ministère a progressivement gagné en cohérence, avec une "
            f"étape significative en {annee}, au cours de laquelle les ressources ont été mieux alignées avec "
            f"les nouvelles missions du MPPEEP."
        ))
        story.append(Paragraph(note_comparaison, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Section : Répartition du budget actuel par nature de dépenses
        para_repartition = financement_interpretations.get("repartition_intro", (
            f"Ainsi, le budget actuel du {ministere} (MPPEEP) s'élève à un total de "
            f"<b>{format_fcfa(budget_reel_total)} F CFA</b>, réparti par nature de dépenses comme suit :"
        ))
        story.append(Paragraph(para_repartition, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Calculer les pourcentages
        pct_personnel = (personnel_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        pct_biens = (biens_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        pct_transferts = (transferts_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        pct_investissements = (investissements_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        
        # Puces avec les pourcentages
        repartition_personnel = financement_interpretations.get("repartition_personnel", (
            f"• <b>Personnel</b>: {format_fcfa(personnel_reel)} F CFA, représentant <b>{pct_personnel:.1f}%</b> du total ;"
        ))
        story.append(Paragraph(repartition_personnel, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        repartition_biens = financement_interpretations.get("repartition_biens", (
            f"• <b>Biens et services</b>: {format_fcfa(biens_reel)} F CFA, représentant <b>{pct_biens:.1f}%</b> du total ;"
        ))
        story.append(Paragraph(repartition_biens, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        repartition_transferts = financement_interpretations.get("repartition_transferts", (
            f"• <b>Transferts</b>: {format_fcfa(transferts_reel)} F CFA, représentant <b>{pct_transferts:.1f}%</b> du total ;"
        ))
        story.append(Paragraph(repartition_transferts, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        repartition_investissements = financement_interpretations.get("repartition_investissements", (
            f"• <b>Investissements</b>: {format_fcfa(investissements_reel)} F CFA, représentant <b>{pct_investissements:.1f}%</b> du total."
        ))
        story.append(Paragraph(repartition_investissements, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Ajouter le graphique en camembert (Figure 1)
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(f"<b>Figure 1: Répartition du budget actuel du Ministère par natures de dépenses</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Générer le graphique en camembert
        pie_chart_buffer = cls._create_pie_chart_budget(
            personnel_reel, pct_personnel,
            biens_reel, pct_biens,
            transferts_reel, pct_transferts,
            investissements_reel, pct_investissements,
            width=12 * cm,
            height=12 * cm
        )
        
        if pie_chart_buffer:
            # Créer un tableau à deux colonnes : source à gauche, graphique à droite
            chart_width = available_width  # Largeur du graphique = 100% de la largeur disponible
            chart_height = 9 * cm  # Hauteur fixe (ne pas modifier)
            
            # Source (colonne gauche)
            source_text = financement_interpretations.get("repartition_source", 
                "Source: Situation d'exécution issue du SIGOBE/DAAF"
            )
            source_para = Paragraph(source_text, source_style)
            
            # Créer un Flowable personnalisé pour positionner source et graphique
            class PieChartWithSource(Flowable):
                def __init__(self, source_para, pie_chart_buffer, chart_width, chart_height, available_width):
                    Flowable.__init__(self)
                    self.source_para = source_para
                    self.pie_chart_buffer = pie_chart_buffer
                    self.chart_width = chart_width  # Largeur = 100% de available_width
                    self.chart_height = chart_height  # Hauteur fixe
                    self.available_width = available_width
                    # Hauteur nécessaire : la hauteur du graphique + espace pour la source
                    self.height = chart_height + 0.5 * cm
                    self.width = available_width
                
                def draw(self):
                    # Positionner la source en bas à gauche
                    # Calculer la hauteur de la source
                    source_w, source_h = self.source_para.wrap(self.available_width * 0.4, 1 * cm)
                    
                    # Dessiner la source en bas à gauche de cette flowable
                    source_x = 0
                    source_y = 0  # En bas de la flowable
                    self.source_para.drawOn(self.canv, source_x, source_y)
                    
                    # Positionner le graphique avec la même position X que le titre (x=0)
                    graph_x = 0  # Même position X que le titre "Figure 1"
                    graph_y = 10  # En bas de la flowable
                    
                    # Dessiner d'abord le fond gris
                    self.canv.saveState()
                    self.canv.setFillColor(colors.HexColor("#d5d5d5"))
                    self.canv.rect(graph_x, graph_y, self.chart_width, self.chart_height, stroke=0, fill=1)
                    self.canv.restoreState()
                    
                    # Dessiner le graphique par-dessus le fond
                    try:
                        from reportlab.lib.utils import ImageReader
                        # Vérifier que le buffer contient bien des données
                        if self.pie_chart_buffer:
                            self.pie_chart_buffer.seek(0)  # Remettre au début du buffer
                            img_reader = ImageReader(self.pie_chart_buffer)
                            self.canv.drawImage(
                                img_reader,
                                graph_x,
                                graph_y,
                                width=self.chart_width,
                                height=self.chart_height,
                                preserveAspectRatio=True,  # Préserver le ratio pour éviter l'étirement
                                mask=None  # Pas de masque de transparence
                            )
                        else:
                            logger.warning("⚠️ Le buffer du graphique est vide")
                    except Exception as e:
                        logger.error(f"Erreur lors du dessin du graphique: {e}", exc_info=True)
                    
                    # Dessiner la bordure grise par-dessus tout
                    self.canv.saveState()
                    self.canv.setStrokeColor(colors.HexColor("#d5d5d5"))
                    self.canv.setLineWidth(1)
                    self.canv.rect(graph_x, graph_y, self.chart_width, self.chart_height, stroke=1, fill=0)
                    self.canv.restoreState()
                
                def wrap(self, availWidth, availHeight):
                    return self.width, self.height
            
            # Créer le flowable combiné
            pie_with_source = PieChartWithSource(source_para, pie_chart_buffer, chart_width, chart_height, available_width)
            story.append(pie_with_source)
            story.append(Spacer(1, 0.3 * cm))
        
        # Tableau 3: Tableau présentant l'exécution du budget du ministère
        story.append(CondPageBreak(5 * cm))
        story.append(Spacer(1, 0.3 * cm))
        intro_tableau3 = "Le tableau ci-dessous rend compte de l'exécution des budgets alloués au Ministère."
        story.append(Paragraph(intro_tableau3, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Titre du tableau
        story.append(Paragraph("<b>Tableau 3: Tableau présentant l'exécution du budget du ministère</b>", subsection_title_style))
        
        # Récupérer les données pour le tableau 3
        # Utiliser les données déjà chargées pour le graphique
        annee_2023_total = 39484849598  # Valeur par défaut pour 2023, à remplacer par données réelles
        prev_2024 = budget_reel_total  # Budget prévu 2024 (budget actuel)
        real_2024 = prev_2024 - 308792055  # Budget réalisé 2024 (légèrement inférieur)
        ecart_2024 = prev_2024 - real_2024
        tx_real_2024 = (real_2024 / prev_2024 * 100) if prev_2024 > 0 else 0
        
        # Données par nature pour 2024 (déjà calculées)
        personnel_prev = personnel_reel
        personnel_real = personnel_prev - 28200
        personnel_ecart = personnel_prev - personnel_real
        personnel_tx = (personnel_real / personnel_prev * 100) if personnel_prev > 0 else 0
        
        biens_prev = biens_reel
        biens_real = biens_prev - 308763854
        biens_ecart = biens_prev - biens_real
        biens_tx = (biens_real / biens_prev * 100) if biens_prev > 0 else 0
        
        transferts_prev = transferts_reel
        transferts_real = transferts_prev
        transferts_ecart = 0
        transferts_tx = 100.0
        
        investissements_prev = investissements_reel
        investissements_real = investissements_prev - 1
        investissements_ecart = 1
        investissements_tx = (investissements_real / investissements_prev * 100) if investissements_prev > 0 else 0
        
        # Styles pour le tableau avec hauteur de lignes réduite
        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,  # Réduit de 11 à 10
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=2,
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,  # Réduit de 10 à 9
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_cell_center_style = ParagraphStyle(
            "TableCellCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,  # Réduit de 10 à 9
            alignment=TA_CENTER,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_cell_right_style = ParagraphStyle(
            "TableCellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,  # Réduit de 10 à 9
            alignment=2,  # RIGHT
            spaceBefore=1,
            spaceAfter=1,
        )
        table_subheader_style = ParagraphStyle(
            "TableSubheader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,  # Réduit de 10 à 9
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_total_style = ParagraphStyle(
            "TableTotal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,  # Réduit de 11 à 10
            alignment=TA_LEFT,
            spaceBefore=2,
            spaceAfter=2,
        )
        
        # Construire les données du tableau avec structure complexe
        # En-têtes multi-lignes
        table_data = []
        # Ligne 1: En-têtes principaux
        table_data.append([
            Paragraph("Unités", table_header_style),
            Paragraph("REALISATIONS<br/>2023", table_header_style),
            Paragraph("2024", table_header_style),  # Cette cellule sera fusionnée sur 4 colonnes
            Paragraph("", table_header_style),  # Vide car fusionné
            Paragraph("", table_header_style),  # Vide car fusionné
            Paragraph("", table_header_style),  # Vide car fusionné
        ])
        # Ligne 2: Sous-en-têtes pour 2024
        table_data.append([
            Paragraph("", table_header_style),  # Vide car fusionné avec ligne du dessus
            Paragraph("", table_header_style),  # Vide car fusionné avec ligne du dessus
            Paragraph("Prév.<br/>(P)", table_header_style),
            Paragraph("Réal<br/>(R)", table_header_style),
            Paragraph("Ecart<br/>(E) = (P)-(R)", table_header_style),
            Paragraph("Tx de réal<br/>= (R/P) x100", table_header_style),
        ])
        
        # RESSOURCES
        table_data.append([
            Paragraph("<b>RESSOURCES</b>", table_subheader_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
        ])
        
        # 1.1 Ressources intérieures
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Ressources intérieures", table_cell_style),
            Paragraph(format_fcfa(annee_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(real_2024), table_cell_right_style),
            Paragraph(format_fcfa(ecart_2024), table_cell_right_style),
            Paragraph(f"{tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # 1.1.1 Budget de l'Etat
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.1 Budget de l'Etat (Trésor)", table_cell_style),
            Paragraph(format_fcfa(annee_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(real_2024), table_cell_right_style),
            Paragraph(format_fcfa(ecart_2024), table_cell_right_style),
            Paragraph(f"{tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # 1.1.2 Recettes de services
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.2 Recettes de services", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2 Ressources extérieures
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Ressources extérieures", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2.1 Emprunts projets
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.1 Emprunts projets", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2.2 Dons Projets
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.2 Dons Projets", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2.3 Appuis budgétaires ciblés
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.3 Appuis budgétaires ciblés", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # CHARGES
        table_data.append([
            Paragraph("<b>CHARGES</b>", table_subheader_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
        ])
        
        # 2.1 Personnel
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Personnel", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),  # 2023 - à remplacer par données réelles
            Paragraph(format_fcfa(personnel_prev), table_cell_right_style),
            Paragraph(format_fcfa(personnel_real), table_cell_right_style),
            Paragraph(format_fcfa(personnel_ecart), table_cell_right_style),
            Paragraph(f"{personnel_tx:.2f}%", table_cell_center_style),
        ])
        
        # 2.1.1 Solde
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.1 Solde y compris EPN", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(6270538992), table_cell_right_style),
            Paragraph(format_fcfa(6270538792), table_cell_right_style),
            Paragraph(format_fcfa(200), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.1.2 Contractuels
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.2 Contractuels hors solde", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(873574247), table_cell_right_style),
            Paragraph(format_fcfa(873546247), table_cell_right_style),
            Paragraph(format_fcfa(28000), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.2 Biens et Service
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Biens et Service", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(biens_prev), table_cell_right_style),
            Paragraph(format_fcfa(biens_real), table_cell_right_style),
            Paragraph(format_fcfa(biens_ecart), table_cell_right_style),
            Paragraph(f"{biens_tx:.2f}%", table_cell_center_style),
        ])
        
        # 2.3 Transferts
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 Transferts", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(transferts_prev), table_cell_right_style),
            Paragraph(format_fcfa(transferts_real), table_cell_right_style),
            Paragraph(format_fcfa(transferts_ecart), table_cell_right_style),
            Paragraph(f"{transferts_tx:.2f}%", table_cell_center_style),
        ])
        
        # 2.3.1 Transferts courants
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.1 Transferts courants", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(transferts_prev), table_cell_right_style),
            Paragraph(format_fcfa(transferts_real), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.3.2 Transferts en capital
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.2 Transferts en capital", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 2.4 Investissement
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Investissement", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(investissements_prev), table_cell_right_style),
            Paragraph(format_fcfa(investissements_real), table_cell_right_style),
            Paragraph(format_fcfa(investissements_ecart), table_cell_right_style),
            Paragraph(f"{investissements_tx:.2f}%", table_cell_center_style),
        ])
        
        # 2.4.1 Trésor
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.1 Trésor", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(investissements_prev), table_cell_right_style),
            Paragraph(format_fcfa(investissements_real), table_cell_right_style),
            Paragraph(format_fcfa(investissements_ecart), table_cell_right_style),
            Paragraph(f"{investissements_tx:.2f}%", table_cell_center_style),
        ])
        
        # 2.4.2 Financement extérieur
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.2 Financement extérieur", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # Dons
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Dons", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # Emprunts
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Emprunts", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # TOTAL
        table_data.append([
            Paragraph("<b>TOTAL</b>", table_total_style),
            Paragraph(format_fcfa(annee_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(real_2024), table_cell_right_style),
            Paragraph(format_fcfa(ecart_2024), table_cell_right_style),
            Paragraph(f"{tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # Calcul des largeurs de colonnes - tableau plus large (somme = 1.0 pour utiliser toute la largeur)
        col_widths = [
            available_width * 0.32,  # Unités
            available_width * 0.14,  # 2023
            available_width * 0.13,  # Prév. (P)
            available_width * 0.13,  # Réal (R)
            available_width * 0.14,  # Ecart (E)
            available_width * 0.14,  # Tx de réal
        ]
        
        # Créer le tableau avec LongTable pour permettre la division automatique sur plusieurs pages
        # LongTable est spécialement conçu pour les tableaux qui peuvent déborder sur plusieurs pages
        execution_table = LongTable(
            table_data,
            colWidths=col_widths,
            repeatRows=2,    # répète les 2 premières lignes (en-têtes) sur chaque page
            splitByRow=1     # permet de couper proprement par lignes
        )
        execution_table.setStyle(
            TableStyle([
                # Bordures
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("LINEBELOW", (0, 1), (-1, 1), 1.5, colors.black),  # Ligne sous les sous-en-têtes
                # En-têtes
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
                # Fusion des cellules pour l'en-tête 2024
                ("SPAN", (2, 0), (5, 0)),  # Fusionner "2024" sur 4 colonnes
                ("SPAN", (0, 0), (0, 1)),  # Fusionner "Unités"
                ("SPAN", (1, 0), (1, 1)),  # Fusionner "REALISATIONS 2023"
                # Alignement du contenu
                ("ALIGN", (0, 2), (0, -1), "LEFT"),  # Première colonne à gauche
                ("ALIGN", (1, 2), (-1, -1), "RIGHT"),  # Colonnes numériques à droite
                ("ALIGN", (5, 2), (5, -1), "CENTER"),  # Colonne taux centrée
                ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
                # Styles pour les sous-en-têtes (RESSOURCES, CHARGES)
                # RESSOURCES est à la ligne 2 (après les 2 lignes d'en-têtes)
                ("FONTNAME", (0, 2), (0, 2), "Helvetica-Bold"),  # RESSOURCES
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fbe4d5")),  # Fond pour RESSOURCES
                # CHARGES - après suppression des sous-totaux et ajout des sous-lignes 1.2.x
                # Structure: 0=en-tête, 1=sous-en-têtes, 2=RESSOURCES, 3=1.1, 4=1.1.1, 5=1.1.2, 
                # 6=1.2, 7=1.2.1, 8=1.2.2, 9=1.2.3, 10=CHARGES, 11=2.1, 12=2.1.1, 13=2.1.2, 
                # 14=2.2, 15=2.3, 16=2.3.1, 17=2.3.2, 18=2.4, 19=2.4.1...
                ("FONTNAME", (0, 10), (0, 10), "Helvetica-Bold"),  # CHARGES
                ("BACKGROUND", (0, 10), (-1, 10), colors.HexColor("#fbe4d5")),  # Fond pour CHARGES
                # Lignes de niveau 2 (1.1, 1.2, 2.1, 2.2, 2.3, 2.4) avec fond vert clair
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e2efd9")),  # 1.1 Ressources intérieures (niveau 2)
                ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#e2efd9")),  # 1.2 Ressources extérieures (niveau 2)
                ("BACKGROUND", (0, 11), (-1, 11), colors.HexColor("#e2efd9")),  # 2.1 Personnel (niveau 2)
                ("BACKGROUND", (0, 14), (-1, 14), colors.HexColor("#e2efd9")),  # 2.2 Biens et Service (niveau 2)
                ("BACKGROUND", (0, 15), (-1, 15), colors.HexColor("#e2efd9")),  # 2.3 Transferts (niveau 2)
                ("BACKGROUND", (0, 18), (-1, 18), colors.HexColor("#e2efd9")),  # 2.4 Investissement (niveau 2)
                # Ligne TOTAL
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                # Padding réduit pour diminuer la hauteur des lignes
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        
        story.append(execution_table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Source
        story.append(Paragraph("Source: Situation d'exécution issue du SIGOBE / RAP 2023", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Analyse de l'exécution budgétaire
        # Calculer les taux d'exécution réels basés sur les données
        tx_execution_global = (real_2024 / prev_2024 * 100) if prev_2024 > 0 else 0
        tx_execution_personnel = (personnel_real / personnel_prev * 100) if personnel_prev > 0 else 0
        tx_execution_biens = (biens_real / biens_prev * 100) if biens_prev > 0 else 0
        tx_execution_transferts = (transferts_real / transferts_prev * 100) if transferts_prev > 0 else 0
        tx_execution_investissements = (investissements_real / investissements_prev * 100) if investissements_prev > 0 else 0
        
        # Formatage des montants pour l'analyse (en gras)
        analyse_text = (
            f"Le budget actuel 2024 du ministère qui s'élevait à <b>{format_fcfa(prev_2024)}</b> a été exécuté à hauteur de <b>{format_fcfa(real_2024)}</b> soit un taux d'exécution global de <b>{tx_execution_global:.2f}%</b>.<br/><br/>"
            f"Concernant les dépenses de personnel, le budget prévu était de <b>{format_fcfa(personnel_prev)}</b>, et le montant effectivement exécuté s'est élevé à <b>{format_fcfa(personnel_real)}</b>. Cette exécution de presque 100%, témoigne d'une promptitude dans la gestion des dépenses de personnel au sein du ministère.<br/><br/>"
            f"Pour ce qui est des biens et services, le budget alloué qui était de <b>{format_fcfa(biens_prev)}</b>, a été exécuté à hauteur de <b>{format_fcfa(biens_real)}</b> soit un taux d'exécution de <b>{tx_execution_biens:.2f}%</b>.<br/><br/>"
            f"Concernant les transferts, le montant programmé de <b>{format_fcfa(transferts_prev)}</b> a été entièrement exécuté. Le taux d'exécution est ainsi de <b>{tx_execution_transferts:.2f}%</b>, ce qui reflète une gestion rigoureuse des engagements financiers, notamment pour les subventions allouées à la SONAPIE.<br/><br/>"
            f"Pour les investissements, le budget actuel de <b>{format_fcfa(investissements_prev)}</b> a été exécuté à hauteur de <b>{format_fcfa(investissements_real)}</b> soit un taux d'exécution de <b>{tx_execution_investissements:.2f}%</b>.<br/><br/>"
            "<b>NB :</b> Les raisons expliquant les niveaux d'exécution seront évoquées dans la suite du rapport."
        )
        
        story.append(Paragraph(analyse_text, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # La page a déjà été créée dans generate_pdf avant l'appel
        # Rendre la story avec pagination automatique
        final_page = cls._render_multipage_story(
            pdf,
            story,
            page_num=start_page,
            frame_x=left_margin,
            frame_y=bottom_margin,
            frame_width=available_width,
            frame_height=available_height,
            page_width=width,
            show_page_number=True,
            draw_footer_func=draw_footer,
        )
        
        return final_page

    @classmethod
    def _create_pie_chart_budget(
        cls,
        personnel: float,
        pct_personnel: float,
        biens: float,
        pct_biens: float,
        transferts: float,
        pct_transferts: float,
        investissements: float,
        pct_investissements: float,
        width: float = 12 * cm,
        height: float = 12 * cm,
    ) -> BytesIO | None:
        """
        Crée un graphique en camembert pour la répartition du budget par nature de dépenses.
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # Backend sans interface graphique
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            
            # Données
            sizes = [personnel, biens, transferts, investissements]
            labels = ["Personnel", "Biens et services", "Transferts", "Investissements"]
            colors_list = [
                "#ADD8E6",  # Bleu clair (Personnel)
                "#FFA500",  # Orange (Biens et services)
                "#808080",  # Gris (Transferts)
                "#FFD700",  # Jaune (Investissements)
            ]
            
            # Créer la figure avec un ratio d'aspect égal pour un cercle parfait
            # Augmenter la taille pour agrandir l'image, labels et légendes
            fig_size = 20  # Taille grande pour avoir une bonne résolution
            fig = plt.figure(figsize=(fig_size, fig_size), dpi=200)  # DPI élevé pour meilleure qualité
            ax = fig.add_subplot(111, aspect='equal')  # Force un ratio d'aspect égal pour un cercle parfait
            
            # Ajouter un titre au graphique centré
            ax.set_title('Répartition du budget actuel du Ministère par natures de dépenses', 
                        fontsize=35, fontweight='bold', pad=20, loc='center')
            
            # Créer le graphique en camembert avec des textes plus grands
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=None,  # On mettra la légende à part
                autopct='%1.0f%%',
                colors=colors_list,
                startangle=90,
                textprops={'fontsize': 40, 'fontweight': 'bold'},  # Augmenté à 24 pour plus de lisibilité
            )
            
            # Personnaliser les textes des pourcentages avec fond noir
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(40)  # Augmenté à 24 pour plus de lisibilité
                # Ajouter un fond noir pour améliorer la lisibilité
                autotext.set_bbox(dict(boxstyle='round,pad=0.3', facecolor='black', edgecolor='none', alpha=0.8))
            
            # Ajouter la légende à droite avec une taille plus grande
            import matplotlib.font_manager as fm
            legend_elements = [
                mpatches.Patch(facecolor=colors_list[0], label=f'{labels[0]} ({pct_personnel:.0f}%)'),
                mpatches.Patch(facecolor=colors_list[1], label=f'{labels[1]} ({pct_biens:.0f}%)'),
                mpatches.Patch(facecolor=colors_list[2], label=f'{labels[2]} ({pct_transferts:.0f}%)'),
                mpatches.Patch(facecolor=colors_list[3], label=f'{labels[3]} ({pct_investissements:.0f}%)'),
            ]
            # Utiliser prop avec FontProperties pour un meilleur contrôle de la taille
            # Augmenter significativement la taille de la légende
            legend_font = fm.FontProperties(weight='bold', size=36)
            legend = ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.1, 0.5), prop=legend_font, frameon=True)
            # S'assurer que la légende utilise bien la taille de police spécifiée
            for text in legend.get_texts():
                text.set_fontsize(36)
                text.set_weight('bold')
            
            # Ajuster la mise en page pour agrandir le graphique (réduire les marges)
            # Utiliser subplots_adjust pour que le graphique occupe plus d'espace
            # Ajuster right pour laisser plus d'espace à la légende
            plt.subplots_adjust(left=0.05, right=0.55, top=0.95, bottom=0.05)
            
            # Sauvegarder dans un buffer avec un ratio d'aspect égal
            # Utiliser des dimensions fixes pour garantir un carré parfait
            # Augmenter le DPI pour une meilleure qualité quand redimensionné
            buffer = BytesIO()
            # Fond gris pour correspondre au cadre
            plt.savefig(buffer, format='png', dpi=200, facecolor='#d5d5d5', edgecolor='none', bbox_inches='tight')
            plt.close(fig)
            buffer.seek(0)
            
            return buffer
            
        except ImportError:
            logger.warning("⚠️ matplotlib n'est pas disponible, graphique en camembert ignoré")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors de la création du graphique en camembert: {e}", exc_info=True)
            return None
    
    class _ProportionalImage(Flowable):
        """Flowable personnalisé pour dessiner une image en préservant son ratio d'aspect (carré parfait)."""
        
        def __init__(self, img_buffer, size, hAlign='CENTER'):
            Flowable.__init__(self)
            self.img_buffer = img_buffer
            self.size = size
            self.hAlign = hAlign
        
        def draw(self):
            """Dessine l'image en préservant le ratio d'aspect avec des dimensions carrées."""
            from reportlab.lib.utils import ImageReader
            
            # Remettre le buffer au début
            self.img_buffer.seek(0)
            img_reader = ImageReader(self.img_buffer)
            
            # Calculer la position X selon l'alignement
            # Note: dans un tableau, _x est la position dans la cellule, pas la page entière
            if self.hAlign == 'CENTER':
                x = self.canv._x + (self.canv._availableWidth - self.size) / 2
            elif self.hAlign == 'RIGHT':
                x = self.canv._x + self.canv._availableWidth - self.size
            else:  # LEFT
                x = self.canv._x
            
            # Dessiner l'image avec des dimensions carrées et preserveAspectRatio
            # Cela garantit que l'image ne sera pas étirée
            self.canv.drawImage(
                img_reader,
                x,
                self.canv._y - self.size,
                width=self.size,
                height=self.size,
                preserveAspectRatio=True
            )
        
        def wrap(self, availWidth, availHeight):
            """Retourne les dimensions nécessaires pour l'image (carré)."""
            self.canv._availableWidth = availWidth  # Sauvegarder pour le calcul de position
            return self.size, self.size
    
    
    @classmethod
    def _draw_partie_programme(cls, pdf: canvas.Canvas, width: float, height: float, start_page: int, programme: dict[str, Any]) -> int:
        """
        Dessine une partie pour un programme donné avec support multi-pages.
        Structure standardisée qui sera identique pour tous les programmes.
        
        Args:
            pdf: Canvas ReportLab
            width: Largeur de la page (paysage)
            height: Hauteur de la page (paysage)
            start_page: Numéro de la page de départ
            programme: Dictionnaire contenant les données du programme
                - numero: Numéro du programme (1, 2, 3, ...)
                - titre: Titre du programme
                - autres données du programme...
        
        Returns:
            Numéro de la dernière page générée
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Récupérer les données du programme
        numero = programme.get("numero", 1)
        titre = programme.get("titre", "")
        
        # Marges et dimensions
        left_margin = 2.5 * cm
        right_margin = 2.5 * cm
        top_margin = 2.5 * cm
        footer_height = 1.5 * cm
        footer_margin = 0.5 * cm
        bottom_margin = footer_height + footer_margin  # Espace pour le footer en bas
        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin
        
        # Récupérer les styles
        styles = getSampleStyleSheet()
        
        # Créer des styles personnalisés similaires à ceux de la PARTIE I
        partie_title_style = ParagraphStyle(
            "PartieTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=0,  # Gauche
            spaceAfter=12,
            textColor=colors.HexColor("#0066CC"),  # Bleu
        )
        
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=0,  # Gauche
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#000000"),  # Noir
            keepWithNext=1,
        )
        
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=0,  # Gauche
            spaceBefore=6,
            spaceAfter=4,
            textColor=colors.HexColor("#000000"),  # Noir
            keepWithNext=1,  # Évite que le titre soit orphelin
        )
        
        # Style spécial pour les titres de sous-sections suivis d'un tableau
        # permet au titre de rester avec au moins le début du tableau
        subsection_title_with_table_style = ParagraphStyle(
            "SubsectionTitleWithTable",
            parent=styles["Normal"],  # Utiliser Normal au lieu de Heading3 pour éviter les espacements par défaut
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=0,  # Gauche
            spaceBefore=6,
            spaceAfter=4,  # Léger espace après le titre avant le tableau
            textColor=colors.HexColor("#000000"),  # Noir
            keepWithNext=0,  # Pas de keepWithNext pour permettre au tableau de commencer sur la même page
            firstLineIndent=0,
        )
        
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=4,  # Justifié
            spaceAfter=6,
        )
        
        source_style = ParagraphStyle(
            "Source",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            alignment=2,  # Droite
            spaceBefore=4,
            spaceAfter=4,
        )
        
        # Styles pour les tableaux (similaires à ceux de la partie III)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=2,
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_cell_center_style = ParagraphStyle(
            "TableCellCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            alignment=TA_CENTER,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_cell_right_style = ParagraphStyle(
            "TableCellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            alignment=TA_RIGHT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_subheader_style = ParagraphStyle(
            "TableSubheader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_total_style = ParagraphStyle(
            "TableTotal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,
            alignment=TA_LEFT,
            spaceBefore=2,
            spaceAfter=2,
        )
        
        # Fonction pour formater les montants en FCFA
        def format_fcfa(montant: float) -> str:
            """Formate un montant en FCFA avec séparateurs de milliers."""
            if montant == 0:
                return "0"
            montant_str = f"{int(montant):,}".replace(",", " ")
            return montant_str
        
        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_num: int) -> None:
            """Dessine le footer avec le numéro de page."""
            card_size = 1.0 * cm
            corner_size = 0.3 * cm
            card_x = width - right_margin - card_size
            card_y = bottom_margin - footer_margin
            
            # Dessiner la carte
            pdf.saveState()
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(card_x, card_y, card_size, card_size, 0.2 * cm, fill=1, stroke=1)
            
            # Coin supérieur droit enroulé
            corner_path = pdf.beginPath()
            corner_path.moveTo(card_x + card_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size - corner_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size, card_y + card_size - corner_size)
            corner_path.close()
            pdf.setFillColor(colors.HexColor("#F0F0F0"))
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            pdf.drawPath(corner_path, fill=1, stroke=1)
            
            # Numéro de page
            pdf.setFillColor(colors.black)
            pdf.setFont("Helvetica", 10)
            text_width = pdf.stringWidth(str(page_num), "Helvetica", 10)
            text_x = card_x + (card_size - text_width) / 2
            text_y = card_y + (card_size - 10) / 2
            pdf.drawString(text_x, text_y, str(page_num))
            pdf.restoreState()
        
        # Construire la story pour cette partie programme
        story: list[Any] = []
        
        # Déterminer le numéro de la partie (PARTIE II, III, IV, etc.)
        # La PARTIE I est "LE MINISTÈRE", donc les programmes commencent à PARTIE II
        partie_numero_romain = cls._number_to_roman(numero + 1)  # +1 car PARTIE I est le ministère
        
        # Titre de la partie
        story.append(Paragraph(f"PARTIE {partie_numero_romain} : LE PROGRAMME {numero} « {titre.upper()} »", partie_title_style))
        story.append(Spacer(1, 0.3 * cm))
        pdf.saveState()
        # Récupérer les données du programme depuis cls.data
        programme_data = programme  # Le programme est déjà passé en paramètre
        
        # Valeurs par défaut pour les données du programme
        annee = cls.data.get("annee", 2024)
        
        # Valeurs par défaut selon le programme
        default_intro_data = {
            1: {  # Programme 1: Administration Générale
                "responsable_nom": "Monsieur SALL Adama",
                "responsable_fonction": "Directeur de Cabinet du MBPE",
                "decret_nomination": "décret n° 2023-956 du 06 décembre 2023 portant nomination des Directeurs de Cabinets ministériels",
                "decret_designation": "le décret n° 2023_337 du 19 avril 2023 portant désignation des Responsables de programme des ministères",
                "missions": [
                    "La coordination, l'animation et la supervision des activités du Ministère;",
                    "La coordination des informations et des communications du Ministère;",
                    "La gestion des ressources humaines, matérielles et financières."
                ],
                "contexte": (
                    f"En {annee}, les activités du Programme « {titre} » se sont déroulées dans un environnement économique "
                    f"international relativement stable, mais également marqué par d'importants ajustements institutionnels. Ces derniers "
                    f"ont été impulsés par la mise en œuvre du décret n°2023-963 du 6 décembre 2023 portant organisation du ministère. "
                    f"Acteur clé de la dynamique des réformes institutionnelles, le Programme « {titre} » s'est affirmé comme un pilier "
                    f"structurant, en appui au bon fonctionnement des services du ministère et en contribuant de manière significative "
                    f"au renforcement de sa gouvernance."
                ),
                "structure_rapport": [
                    "la présentation de la stratégie du programme;",
                    "les réalisations du programme au cours de l'exercice 2024;",
                    "la performance du programme;",
                    "les perspectives."
                ]
            },
            2: {  # Programme 2: Portefeuille de l'Etat (valeurs par défaut génériques)
                "responsable_nom": "",
                "responsable_fonction": "Responsable de Programme",
                "decret_nomination": "décret",
                "decret_designation": "le décret",
                "missions": [],
                "contexte": "",
                "structure_rapport": [
                    "la présentation de la stratégie du programme;",
                    "les réalisations du programme au cours de l'exercice 2024;",
                    "la performance du programme;",
                    "les perspectives."
                ]
            }
        }
        
        # Utiliser les données du programme ou les valeurs par défaut
        intro_data = default_intro_data.get(numero, default_intro_data[2])  # Utiliser programme 2 comme fallback
        responsable_nom = programme_data.get("responsable_nom", intro_data.get("responsable_nom", ""))
        responsable_fonction = programme_data.get("responsable_fonction", intro_data.get("responsable_fonction", "Responsable de Programme"))
        decret_nomination = programme_data.get("decret_nomination", intro_data.get("decret_nomination", "décret"))
        decret_designation = programme_data.get("decret_designation", intro_data.get("decret_designation", "le décret"))
        missions = programme_data.get("missions", intro_data.get("missions", []))
        contexte = programme_data.get("contexte", intro_data.get("contexte", ""))
        structure_rapport = programme_data.get("structure_rapport", intro_data.get("structure_rapport", []))
        
        # Section INTRODUCTION
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("INTRODUCTION", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Paragraphe 1 : Responsable du programme
        if responsable_nom:
            para1_text = (
                f"Nommé {responsable_fonction} par {decret_nomination}, {responsable_nom} est le Responsable du programme « {titre} », "
                f"conformément à {decret_designation}."
            )
            story.append(Paragraph(para1_text, body_style))
            story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 2 : Missions du programme
        if missions:
            para2_text = (
                f"Ce programme a été réalisé à partir d'une répartition des tâches mise en place en fonction "
                f"du décret n° 2023-963 du 6 décembre 2023 portant organisation du ministère. Les principales missions sont :"
            )
            story.append(Paragraph(para2_text, body_style))
            story.append(Spacer(1, 0.1 * cm))
            
            # Liste des missions avec puces (tirets)
            bullet_style = ParagraphStyle(
                "BulletStyle",
                parent=body_style,
                leftIndent=20,
                bulletIndent=10,
            )
            for mission in missions:
                story.append(Paragraph(mission, bullet_style, bulletText="-"))
            story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 3 : Contexte et environnement
        if not contexte:
            contexte = (
                f"En {annee}, les activités du Programme « {titre} » se sont déroulées dans un environnement économique "
                f"international relativement stable, mais également marqué par d'importants ajustements institutionnels."
            )
        story.append(Paragraph(contexte, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 4 : Structure du rapport avec liste à puces
        if not structure_rapport:
            structure_rapport = [
                "la présentation de la stratégie du programme;",
                "les réalisations du programme au cours de l'exercice 2024;",
                "la performance du programme;",
                "les perspectives."
            ]
        
        para4_text = (
            f"Pour faire face à des défis de plus en plus élevés, le Programme a élaboré un plan d'actions et défini des indicateurs "
            f"dont la réalisation est décrite dans le présent Rapport Annuel de Performance (RAP) du programme « {titre} » qui prend en compte "
            f"les rapports semestriels du Responsable de Programme (Rprog) et s'articule autour des points suivants :"
        )
        story.append(Paragraph(para4_text, body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Liste à puces (cercles noirs)
        circle_bullet_style = ParagraphStyle(
            "CircleBulletStyle",
            parent=body_style,
            leftIndent=20,
            bulletIndent=10,
        )
        for item in structure_rapport:
            story.append(Paragraph(item, circle_bullet_style, bulletText="•"))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph(f"{partie_numero_romain}. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # ============================================================
        # I.1. Les objectifs du programme
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph(f"{partie_numero_romain}.1. Les objectifs du programme", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Paragraphe introductif sur les objectifs
        objectif_global = programme_data.get("objectif_global", {})
        objectif_global_num = objectif_global.get("numero", "1")
        objectif_global_libelle = objectif_global.get("libelle", "Améliorer la gouvernance du secteur")
        resultat_strategique_num = objectif_global.get("resultat_strategique_num", "1")
        resultat_strategique_libelle = objectif_global.get("resultat_strategique_libelle", "La gouvernance du secteur est améliorée")
        
        objectifs_para = (
            f"La mise en œuvre des activités du Programme « {titre} » permettra, à moyen terme, de contribuer à la poursuite "
            f"de l'objectif global {objectif_global_num} du {cls.data.get('ministere', 'MPPEEP')}, à savoir « {objectif_global_libelle} » "
            f"et d'atteindre le résultat stratégique « {resultat_strategique_libelle} »."
        )
        story.append(Paragraph(objectifs_para, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Tableau : Objectif global et résultats stratégiques
        table_obj_header_style = ParagraphStyle(
            "TableObjHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            alignment=1,  # Centré
        )
        table_obj_cell_style = ParagraphStyle(
            "TableObjCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            alignment=0,  # Gauche
        )
        
        obj_table_data = [
            [
                Paragraph("OBJECTIF GLOBAL (OG)", table_obj_header_style),
                Paragraph("RESULTAT STRATEGIQUE (RS)", table_obj_header_style),
            ],
            [
                Paragraph(f"OG {objectif_global_num}:: {objectif_global_libelle}", table_obj_cell_style),
                Paragraph(f"RS {resultat_strategique_num}: {resultat_strategique_libelle}", table_obj_cell_style),
            ],
        ]
        
        obj_col_widths = [available_width * 0.5, available_width * 0.5]
        obj_table = Table(obj_table_data, colWidths=obj_col_widths, repeatRows=1)
        obj_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (-1, 1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        
        story.append(obj_table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Source pour le tableau des objectifs
        annee = cls.data.get("annee", 2024)
        source_obj = (
            f"Source: Annexe 4 de la Loi de Finances n° {annee - 1}-1000 du 18 décembre {annee - 1} "
            f"portant budget de l'State pour l'année {annee}"
        )
        story.append(Paragraph(source_obj, source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # I.2. Le financement du programme
        # ============================================================
        # Ajouter le titre - pas de CondPageBreak pour permettre au tableau de commencer sur la même page
        # Le tableau suivra directement après le titre et sera automatiquement divisé si trop grand
        # Si le titre risque d'être orphelin, ReportLab le gérera naturellement avec keepWithNext
        titre_financement = Paragraph(f"{partie_numero_romain}.2. Le financement du programme", subsection_title_with_table_style)
        # Pas d'espace après le titre, le tableau suit directement
        
        # Récupérer les données budgétaires du programme
        # Les données peuvent venir de programme_data ou être calculées
        programme_budget = programme_data.get("budget", {})
        
        # Utiliser les données du programme ou des valeurs par défaut/calculées
        prog_2023_total = programme_budget.get("realisations_2023", 84410746315)
        prog_prev_2024 = programme_budget.get("prevu_2024", 32341752594)
        prog_real_2024 = programme_budget.get("realise_2024", 32048763906)
        prog_ecart_2024 = programme_budget.get("ecart_2024", prog_prev_2024 - prog_real_2024)
        prog_tx_real_2024 = (prog_real_2024 / prog_prev_2024 * 100) if prog_prev_2024 > 0 else 0
        
        # Données par nature de dépense pour le programme
        prog_personnel_2023 = programme_budget.get("personnel_2023", 66953378820)
        prog_personnel_prev = programme_budget.get("personnel_prev", 7112563239)
        prog_personnel_real = programme_budget.get("personnel_real", 7112535039)
        prog_personnel_ecart = prog_personnel_prev - prog_personnel_real
        prog_personnel_tx = (prog_personnel_real / prog_personnel_prev * 100) if prog_personnel_prev > 0 else 0
        
        prog_biens_2023 = programme_budget.get("biens_2023", 4612280028)
        prog_biens_prev = programme_budget.get("biens_prev", 5360558529)
        prog_biens_real = programme_budget.get("biens_real", 5067598041)
        prog_biens_ecart = prog_biens_prev - prog_biens_real
        prog_biens_tx = (prog_biens_real / prog_biens_prev * 100) if prog_biens_prev > 0 else 0
        
        prog_transferts_2023 = programme_budget.get("transferts_2023", 626866385)
        prog_transferts_prev = programme_budget.get("transferts_prev", 14934916699)
        prog_transferts_real = programme_budget.get("transferts_real", 14934916699)
        prog_transferts_ecart = 0
        prog_transferts_tx = 100.0
        
        prog_investissements_2023 = programme_budget.get("investissements_2023", 12218221082)
        prog_investissements_prev = programme_budget.get("investissements_prev", 4933714127)
        prog_investissements_real = programme_budget.get("investissements_real", 4933714127)
        prog_investissements_ecart = 0
        prog_investissements_tx = 100.0
        
        # Créer le tableau d'exécution budgétaire du programme (similaire au tableau 3)
        # On réutilise la même structure mais avec les données du programme
        prog_table_data = []
        
        # En-têtes
        prog_table_data.append([
            Paragraph("Unités", table_header_style),
            Paragraph("REALISATIONS<br/>2023", table_header_style),
            Paragraph("2024", table_header_style),
            Paragraph("", table_header_style),
            Paragraph("", table_header_style),
            Paragraph("", table_header_style),
        ])
        prog_table_data.append([
            Paragraph("", table_header_style),
            Paragraph("", table_header_style),
            Paragraph("Prév.<br/>(P)", table_header_style),
            Paragraph("Réal<br/>(R)", table_header_style),
            Paragraph("Ecart<br/>(E) = (P)-(R)", table_header_style),
            Paragraph("Tx de réal<br/>= (R/P) x100", table_header_style),
        ])
        
        # RESSOURCES
        prog_table_data.append([
            Paragraph("<b>RESSOURCES</b>", table_subheader_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
        ])
        
        # 1.1 Ressources intérieures
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Ressources intérieures", table_cell_style),
            Paragraph(format_fcfa(prog_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prog_prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_real_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_ecart_2024), table_cell_right_style),
            Paragraph(f"{prog_tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # 1.1.1 Budget de l'Etat
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.1 Budget de l'Etat (Trésor)", table_cell_style),
            Paragraph(format_fcfa(prog_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prog_prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_real_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_ecart_2024), table_cell_right_style),
            Paragraph(f"{prog_tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # 1.1.2 Recettes de services
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.2 Recettes de services", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2 Ressources extérieures
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Ressources extérieures", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2.1, 1.2.2, 1.2.3 (tous à 0)
        for sub_item in ["1.2.1 Emprunts projets", "1.2.2 Dons Projets", "1.2.3 Appuis budgétaires ciblés"]:
            prog_table_data.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item}", table_cell_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph("-", table_cell_center_style),
            ])
        
        # CHARGES
        prog_table_data.append([
            Paragraph("<b>CHARGES</b>", table_subheader_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
        ])
        
        # 2.1 Personnel
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Personnel", table_cell_style),
            Paragraph(format_fcfa(prog_personnel_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_personnel_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_personnel_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_personnel_ecart), table_cell_right_style),
            Paragraph(f"{prog_personnel_tx:.0f}%", table_cell_center_style),
        ])
        
        # 2.1.1 Solde
        solde_2023 = programme_budget.get("solde_2023", 66947978820)
        solde_prev = programme_budget.get("solde_prev", 6270538992)
        solde_real = programme_budget.get("solde_real", 6270538792)
        solde_ecart = solde_prev - solde_real
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.1 Solde y compris EPN", table_cell_style),
            Paragraph(format_fcfa(solde_2023), table_cell_right_style),
            Paragraph(format_fcfa(solde_prev), table_cell_right_style),
            Paragraph(format_fcfa(solde_real), table_cell_right_style),
            Paragraph(format_fcfa(solde_ecart), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.1.2 Contractuels
        contractuels_2023 = programme_budget.get("contractuels_2023", 5400000)
        contractuels_prev = programme_budget.get("contractuels_prev", 842024247)
        contractuels_real = programme_budget.get("contractuels_real", 841996247)
        contractuels_ecart = contractuels_prev - contractuels_real
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.2 Contractuels hors solde", table_cell_style),
            Paragraph(format_fcfa(contractuels_2023), table_cell_right_style),
            Paragraph(format_fcfa(contractuels_prev), table_cell_right_style),
            Paragraph(format_fcfa(contractuels_real), table_cell_right_style),
            Paragraph(format_fcfa(contractuels_ecart), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.2 Biens et Service
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Biens et Service", table_cell_style),
            Paragraph(format_fcfa(prog_biens_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_biens_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_biens_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_biens_ecart), table_cell_right_style),
            Paragraph(f"{prog_biens_tx:.2f}%", table_cell_center_style),
        ])
        
        # 2.3 Transferts
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 Transferts", table_cell_style),
            Paragraph(format_fcfa(prog_transferts_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_ecart), table_cell_right_style),
            Paragraph(f"{prog_transferts_tx:.0f}%", table_cell_center_style),
        ])
        
        # 2.3.1 Transferts courants
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.1 Transferts courants", table_cell_style),
            Paragraph(format_fcfa(prog_transferts_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_real), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.3.2 Transferts en capital
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.2 Transferts en capital", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 2.4 Investissement
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Investissement", table_cell_style),
            Paragraph(format_fcfa(prog_investissements_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_investissements_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_investissements_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_investissements_ecart), table_cell_right_style),
            Paragraph(f"{prog_investissements_tx:.0f}%", table_cell_center_style),
        ])
        
        # 2.4.1 Trésor
        tresor_inv_2023 = programme_budget.get("tresor_inv_2023", 12218221082)
        tresor_inv_prev = programme_budget.get("tresor_inv_prev", 4933714127)
        tresor_inv_real = programme_budget.get("tresor_inv_real", 4933714127)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.1 Trésor", table_cell_style),
            Paragraph(format_fcfa(tresor_inv_2023), table_cell_right_style),
            Paragraph(format_fcfa(tresor_inv_prev), table_cell_right_style),
            Paragraph(format_fcfa(tresor_inv_real), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.4.2 Financement extérieur, Dons, Emprunts (tous à 0)
        for sub_item in ["2.4.2 Financement extérieur", "Dons", "Emprunts"]:
            prog_table_data.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item}", table_cell_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph("-", table_cell_center_style),
            ])
        
        # TOTAL
        prog_table_data.append([
            Paragraph("<b>TOTAL</b>", table_total_style),
            Paragraph(format_fcfa(prog_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prog_prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_real_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_ecart_2024), table_cell_right_style),
            Paragraph(f"{prog_tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # Calcul des largeurs de colonnes pour le tableau
        col_widths = [
            available_width * 0.32,  # Unités
            available_width * 0.14,  # 2023
            available_width * 0.13,  # Prév. (P)
            available_width * 0.13,  # Réal (R)
            available_width * 0.14,  # Ecart (E)
            available_width * 0.14,  # Tx de réal
        ]
        
        # Créer le tableau avec LongTable pour permettre la division automatique sur plusieurs pages
        # LongTable est spécialement conçu pour les tableaux qui peuvent déborder sur plusieurs pages
        # repeatRows=2 permet de répéter les en-têtes sur chaque page
        prog_execution_table = LongTable(
            prog_table_data,
            colWidths=col_widths,
            repeatRows=2,    # répète les 2 premières lignes (en-têtes) sur chaque page
            splitByRow=1     # permet de couper proprement par lignes
        )
        prog_execution_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("LINEBELOW", (0, 1), (-1, 1), 1.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
                ("SPAN", (2, 0), (5, 0)),
                ("SPAN", (0, 0), (0, 1)),
                ("SPAN", (1, 0), (1, 1)),
                ("ALIGN", (0, 2), (0, -1), "LEFT"),
                ("ALIGN", (1, 2), (-1, -1), "RIGHT"),
                ("ALIGN", (5, 2), (5, -1), "CENTER"),
                ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 2), (0, 2), "Helvetica-Bold"),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fbe4d5")),
                ("FONTNAME", (0, 10), (0, 10), "Helvetica-Bold"),
                ("BACKGROUND", (0, 10), (-1, 10), colors.HexColor("#fbe4d5")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 11), (-1, 11), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 14), (-1, 14), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 15), (-1, 15), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 18), (-1, 18), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        
        # Ajouter le titre de section
        story.append(titre_financement)
        
        # Ajouter le titre du tableau juste avant le tableau (comme dans le demo)
        tableau_title = f"Tableau : Exécution du budget du Programme {numero} « {titre} »"
        story.append(Paragraph(f"<b>{tableau_title}</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter le tableau LongTable - il se divisera automatiquement sur plusieurs pages
        story.append(prog_execution_table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Source
        story.append(Paragraph("Source: Situation d'exécution issue du SIGOBE", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Interprétation du financement du programme
        # L'utilisateur peut fournir son interprétation, sinon afficher un placeholder en rouge
        financement_interpretation = programme_data.get("financement_interpretation", "")
        
        if financement_interpretation:
            # Afficher l'interprétation fournie par l'utilisateur
            # Le texte peut contenir du HTML pour le formatage (gras, italique, etc.)
            story.append(Paragraph(financement_interpretation, body_style))
        else:
            # Afficher un placeholder en rouge et en italique
            placeholder_style = ParagraphStyle(
                "PlaceholderStyle",
                parent=body_style,
                textColor=colors.HexColor("#FF0000"),  # Rouge
                fontName="Helvetica-Oblique",  # Italique
            )
            story.append(Paragraph("Votre interprétation ici", placeholder_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Note NB si fournie par l'utilisateur
        financement_note = programme_data.get("financement_note", "")
        if financement_note:
            story.append(Paragraph(f"<b>NB :</b> {financement_note}", body_style))
            story.append(Spacer(1, 0.2 * cm))
        else:
            # Placeholder pour la note en rouge
            placeholder_note_style = ParagraphStyle(
                "PlaceholderNoteStyle",
                parent=body_style,
                textColor=colors.HexColor("#FF0000"),  # Rouge
                fontName="Helvetica-Oblique",  # Italique
                spaceBefore=6,
            )
            story.append(Paragraph("<b>NB :</b> Votre interprétation ici", placeholder_note_style))
            story.append(Spacer(1, 0.2 * cm))
        
        
        # Cela permet à ReportLab de diviser correctement les tableaux longs sur plusieurs pages
        # Dans ReportLab, frame_y est la position Y du BAS du Frame (0,0 est en bas à gauche)
        # et le Frame monte vers le haut à partir de cette position
        final_page = cls._render_multipage_story(
            pdf,
            story,
            page_num=start_page,
            frame_x=left_margin,
            frame_y=bottom_margin,  # Commence depuis le bas (bottom_margin inclut déjà footer_height + footer_margin)
            frame_width=available_width,
            frame_height=available_height,  # Monte jusqu'en haut de la zone disponible (height - top_margin - bottom_margin)
            page_width=width,
            show_page_number=True,
            draw_footer_func=draw_footer,
        )
        
        return final_page
    
    @staticmethod
    def _number_to_roman(num: int) -> str:
        """Convertit un nombre en chiffres romains."""
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syb = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ""
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syb[i]
                num -= val[i]
            i += 1
        return roman_num

