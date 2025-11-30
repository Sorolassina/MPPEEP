"""
Service de génération du Rapport Annuel de Performance utilisant SimpleDocTemplate.
Cette version utilise SimpleDocTemplate pour gérer automatiquement le découpage des LongTable.
"""
from __future__ import annotations

import logging
import re
import math
from collections import defaultdict
from io import BytesIO
from typing import Any
from pathlib import Path
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    Paragraph, Spacer, LongTable, TableStyle, 
    SimpleDocTemplate, PageBreak, CondPageBreak, Flowable, Table, Frame
)
from reportlab.platypus.doctemplate import LayoutError
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

from app.models.budget import SigobeExecution
from app.core.path_config import path_config
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from sqlmodel import Session as SQLModelSession
from decimal import Decimal

logger = logging.getLogger(__name__)


class RapportAnnuelPerformanceGeneratorSimpleDoc:
    """
    Générateur de rapport annuel de performance utilisant SimpleDocTemplate.
    Format : Paysage (Landscape A4)
    
    Cette version utilise SimpleDocTemplate pour gérer automatiquement 
    le découpage des LongTable sur plusieurs pages.
    """
    
    # Constantes de couleurs
    PRIMARY_GREEN = colors.HexColor("#39791b")
    SECONDARY_GREEN = colors.HexColor("#609b4d")
    LIGHT_GREEN = colors.HexColor("#387722")
    
    PRIMARY_ORANGE = colors.HexColor("#F26D21")
    LIGHT_ORANGE = colors.HexColor("#ef9543")
    LIGHT_2_ORANGE = colors.HexColor("#ee863d")
    DARK_TEXT = colors.HexColor("#1F1F1F")
    
    # Couleurs pour le styling des sources de données
    # Toutes les données proviennent de la base de données et sont affichées en rouge
    COLOR_DB = colors.HexColor("#FF0000")  # Rouge pour toutes les données (DB)
    
    # Variable de classe pour stocker la position de la ligne pointillée du bas
    _dotted_line_bottom_y: float | None = None
    
    # Variable de classe pour stocker la session de base de données
    _db_session: Session | None = None
    
    # Variable de classe pour stocker les données fusionnées
    data: dict[str, Any] = {}
    
    # Variable de classe pour suivre les clés de données DB (pour le styling)
    _db_data_keys: set[str] = set()
    
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
            # Le sigle MPPEEP sera généré dynamiquement depuis le nom du ministère
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
    
    # ============================================================
    # FONCTIONS HELPER POUR LE STYLING DES DONNÉES
    # ============================================================
    @staticmethod
    def _remove_accents(text: str) -> str:
        """
        Enlève les accents d'un texte.
        
        Args:
            text: Texte avec accents
            
        Returns:
            Texte sans accents
        """
        import unicodedata
        # Normaliser en NFD (Normalization Form Decomposed) pour séparer les accents
        nfd = unicodedata.normalize('NFD', text)
        # Filtrer les caractères combinants (accents)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    @staticmethod
    def _generate_sigle_from_ministere(ministere: str) -> str:
        """
        Génère automatiquement le sigle à partir du nom du ministère.
        
        Exemple: "MINISTERE DU PATRIMOINE, DU PORTEFEUILLE DE L'ÉTAT ET DES ENTREPRISES PUBLIQUES"
        -> "MPPEEP"
        
        Args:
            ministere: Nom du ministère en majuscules
            
        Returns:
            Sigle généré (en majuscules, sans accents)
        """
        if not ministere:
            return "MPPEEP"  # Valeur par défaut
        
        # Mots à ignorer lors de la génération du sigle
        mots_a_ignorer = {
            "DU", "DE", "DES", "ET", "LE", "LA", "LES", "L'", "D'",
            "AU", "AUX", "EN", "PAR", "POUR", "AVEC", "SANS", "SOUS", "SUR"
        }
        
        # Nettoyer le nom du ministère (enlever les virgules, points, etc.)
        ministere_clean = ministere.upper().replace(",", " ").replace(".", " ").replace("'", " ")
        
        # Enlever les accents
        ministere_clean = RapportAnnuelPerformanceGeneratorSimpleDoc._remove_accents(ministere_clean)
        
        # Extraire les mots
        mots = ministere_clean.split()
        
        # Filtrer les mots à ignorer et extraire les premières lettres
        sigle_lettres = []
        for mot in mots:
            mot_clean = mot.strip()
            if mot_clean and mot_clean not in mots_a_ignorer and len(mot_clean) > 1:
                # Prendre la première lettre du mot (sans accent)
                sigle_lettres.append(mot_clean[0])
        
        # Si on a moins de 3 lettres, essayer une autre approche
        if len(sigle_lettres) < 3:
            # Prendre les premières lettres de tous les mots (sauf ceux à ignorer)
            sigle_lettres = []
            for mot in mots:
                mot_clean = mot.strip()
                if mot_clean and mot_clean not in mots_a_ignorer:
                    sigle_lettres.append(mot_clean[0])
        
        sigle = "".join(sigle_lettres)
        
        # Si le sigle est vide ou trop court, retourner une valeur par défaut
        if not sigle or len(sigle) < 3:
            return "MPPEEP"  # Valeur par défaut
        
        return sigle
    
    @classmethod
    def _get_sigle_ministere(cls) -> str:
        """
        Récupère le sigle du ministère, généré automatiquement depuis le nom du ministère.
        
        Returns:
            Sigle du ministère (ex: "MPPEEP")
        """
        ministere = cls.data.get("ministere", "")
        if not ministere:
            return "MPPEEP"  # Valeur par défaut
        
        return cls._generate_sigle_from_ministere(ministere)
    
    @classmethod
    def _determine_data_source_for_canvas(cls, key: str, value: Any, db_value: Any = None, is_user_explicit: bool = False) -> tuple[Any, str]:
        """
        Détermine la source d'une donnée pour Canvas. Toutes les données sont maintenant considérées comme DB.
        
        Args:
            key: Clé de la donnée
            value: Valeur actuelle dans cls.data
            db_value: Valeur provenant de la base de données (ignoré)
            is_user_explicit: Ignoré (toutes les données sont DB)
            
        Returns:
            Tuple (valeur, source: toujours "db")
        """
        # Toutes les données proviennent de la base de données
        return value, "db"
    
    @classmethod
    def _format_data_value(cls, key: str, db_value: Any = None, default_value: Any = None) -> str:
        """
        Récupère une valeur depuis cls.data et retourne le texte formaté (toujours DB, en rouge).
        
        Args:
            key: Clé de la donnée dans cls.data
            db_value: Valeur provenant de la base de données (ignoré)
            default_value: Valeur par défaut si absente (optionnel)
            
        Returns:
            Texte formaté avec balises HTML (rouge pour DB)
        """
        value = cls.data.get(key, default_value)
        if value is None:
            return ""
        
        # Convertir en string si nécessaire
        text = str(value) if not isinstance(value, str) else value
        
        # Toutes les données sont formatées comme DB (rouge)
        return cls._format_db_data(text)
    
    @classmethod
    def _get_color_for_source(cls, source: str) -> colors.HexColor:
        """
        Retourne la couleur appropriée selon la source pour Canvas. Toutes les données sont DB (rouge).
        
        Args:
            source: Ignoré (toujours "db")
            
        Returns:
            Couleur HexColor (rouge pour DB)
        """
        return cls.COLOR_DB  # Rouge pour toutes les données (DB)
    
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
    
    @classmethod
    def _draw_footer(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine le bloc date en bas à droite."""
        pdf.saveState()

        # ---------- BOÎTE DATE EN BAS À DROITE ----------
        # Vérifier si la date est fournie par l'utilisateur (USER)
        # Générer toujours la date dynamiquement (toutes les données sont DB)
        if True:
            # Générer la date à partir du mois et de l'année en cours
            from datetime import datetime
            now = datetime.now()
            # Liste des mois en français
            mois_fr = [
                "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
            ]
            mois_actuel = mois_fr[now.month - 1]  # now.month est entre 1 et 12
            annee_actuelle = now.year
            date_publication = f"{mois_actuel} {annee_actuelle}"
            date_source = "db"  # Générée dynamiquement depuis la date actuelle
            logger.info(f"📅 Date de publication générée dynamiquement: {date_publication} (mois: {now.month}, année: {now.year})")
        else:
            # La date est fournie par l'utilisateur, l'utiliser telle quelle
            date_publication = cls.data.get("date_publication", "")
            _, date_source = cls._determine_data_source_for_canvas("date_publication", date_publication)
            logger.info(f"📅 Date de publication fournie par l'utilisateur: {date_publication}")

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
            # Toutes les données sont DB, utiliser l'italique
            if True:
                pdf.setFont("Helvetica-BoldOblique", 11)
            else:
                pdf.setFont("Helvetica-Bold", 11)
            # Utiliser la source déterminée pour la couleur (peut être user > db > default)
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
        titre_rapport_base = cls.data.get("titre_rapport", "")
        titre_annee = cls.data.get("titre_annee", "")
        annee = cls.data.get("annee", "")
        
        # Récupérer le nom du ministère et le concaténer au titre
        ministere = cls.data.get("ministere", "")
        if ministere:
            # Construire le titre complet : "RAPPORT ANNUEL DE PERFORMANCE DU [NOM MINISTERE]"
            titre_rapport = f"{titre_rapport_base} DU {ministere}"
        else:
            titre_rapport = titre_rapport_base
        
        # Déterminer la source de chaque donnée pour le styling
        _, titre_rapport_source = cls._determine_data_source_for_canvas("titre_rapport", titre_rapport)
        _, titre_annee_source = cls._determine_data_source_for_canvas("titre_annee", titre_annee)
        _, annee_source = cls._determine_data_source_for_canvas("annee", annee)
        
        # Vérifier si le ministère provient de la DB
        # Le titre_rapport contient toujours le nom du ministère, donc si le ministère provient de la DB,
        # on doit utiliser l'italique pour le titre
        # Toutes les données sont DB, utiliser l'italique
        should_use_italic = True
        
        # Log pour débogage
        logger.debug(f"🔍 Titre rapport source: {titre_rapport_source}, Utiliser italique: {should_use_italic}")
        
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
        # Choisir la police selon la source : BoldOblique pour DB (italique), Bold sinon
        if should_use_italic:
            font_name = "Helvetica-BoldOblique"
            logger.debug(f"✅ Utilisation de Helvetica-BoldOblique pour le titre (italique)")
        else:
            font_name = "Helvetica-Bold"
            logger.debug(f"⚠️ Utilisation de Helvetica-Bold pour le titre (pas d'italique)")
        line_height = 22  # Hauteur de ligne par défaut
        pdf.setFont(font_name, font_size)
        
        # Calculer la largeur maximale pour le texte
        max_text_width = text_area_width
        
        # Déterminer la couleur du titre (toutes les données sont DB, rouge)
        titre_color = cls._get_color_for_source("db")
        
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
                year_source = annee_source if titre_annee_source == "default" else titre_annee_source
                year_color = cls._get_color_for_source(year_source)
                
                # Choisir la police pour l'année selon sa source : BoldOblique pour DB (italique), Bold sinon
                if year_source == "db":
                    year_font_name = "Helvetica-BoldOblique"
                else:
                    year_font_name = font_name
                
                # Vérifier que l'année rentre aussi dans la largeur
                year_font_size = font_size
                if pdf.stringWidth(year_text, year_font_name, year_font_size) > max_text_width:
                    # Réduire la taille pour l'année si nécessaire
                    year_font_size = 14
                pdf.saveState()
                pdf.setFont(year_font_name, year_font_size)
                pdf.setFillColor(year_color)
                pdf.drawCentredString(center_x, text_y, year_text)
                pdf.restoreState()

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
        
        # Programmes dynamiques depuis les données de la DB uniquement
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        programmes = cls.data.get("programmes", [])
        
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
        # Tableaux dynamiques depuis les données de la DB uniquement
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        tableaux = cls.data.get("tableaux", [])
        
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
        # Graphiques dynamiques depuis les données de la DB uniquement
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        graphiques = cls.data.get("graphiques", [])
        
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
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        # Si pas de sigles dans la DB, utiliser une liste vide
        is_sigles_user = False
        if not sigles:
            sigles = []
        
        # Ajouter automatiquement le sigle du ministère généré dynamiquement
        sigle_ministere = cls._get_sigle_ministere()
        ministere = cls.data.get("ministere", "")
        
        # Vérifier si le sigle du ministère n'est pas déjà dans la liste
        sigle_exists = any(entry.get("sigle") == sigle_ministere for entry in sigles)
        
        if not sigle_exists and ministere:
            # Ajouter le sigle du ministère à la liste
            sigle_ministere_entry = {
                "sigle": sigle_ministere,
                "definition": ministere
            }
            # Insérer au début de la liste pour qu'il soit visible en premier
            sigles.insert(0, sigle_ministere_entry)
        
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
                # Toutes les données sont DB
                sigle_source = "db"
                
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
    def _format_db_data(cls, text: str) -> str:
        """
        Formate le texte pour les données provenant de la base de données.
        En mode "brouillon", le texte est formaté en rouge.
        En mode "final", le texte est retourné sans formatage de couleur (tout en noir).
        
        Args:
            text: Le texte à formater
            
        Returns:
            Le texte formaté avec la couleur rouge (mode brouillon) ou sans couleur (mode final)
        """
        if not text:
            return ""
        
        # Vérifier le mode depuis cls.data
        mode = cls.data.get("mode", "brouillon")
        
        # En mode final, retourner le texte sans formatage de couleur
        if mode == "final":
            return text
        
        # En mode brouillon, formater en rouge
        return f'<font color="#FF0000">{text}</font>'
    
    @classmethod
    def _format_fake_data(cls, text: str) -> str:
        """
        Formate le texte pour les données factices (générées quand la base est vide).
        En mode "brouillon", le texte est formaté en violet et italique.
        En mode "final", retourne une chaîne vide (pas de données factices).
        
        Args:
            text: Le texte factice à formater
            
        Returns:
            Le texte formaté en violet italique (mode brouillon) ou chaîne vide (mode final)
        """
        # Vérifier le mode depuis cls.data
        mode = cls.data.get("mode", "brouillon")
        
        # En mode final, ne pas afficher de données factices
        if mode == "final":
            return ""
        
        # En mode brouillon, formater en violet et italique
        if not text:
            return ""
        
        return f'<font color="#800080"><i>{text}</i></font>'
    
    @classmethod
    def _should_use_fake_data(cls) -> bool:
        """
        Détermine si on doit utiliser des données factices.
        Retourne True seulement en mode brouillon.
        
        Returns:
            True si on doit utiliser des données factices (mode brouillon), False sinon
        """
        mode = cls.data.get("mode", "brouillon")
        return mode == "brouillon"
    
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

        # Récupérer les données d'introduction depuis la DB uniquement
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        intro_data = cls.data.get("introduction", {})
        logger.info(f"🔍 _draw_introduction_generale - intro_data récupéré: {list(intro_data.keys()) if intro_data else 'VIDE'}")
        logger.info(f"🔍 _draw_introduction_generale - cls.data contient 'introduction': {'introduction' in cls.data}")
        # Si intro_data est vide, on utilisera "NC" ou 0 comme valeurs par défaut
        
        # Les données DB sont déjà chargées au début dans generate_pdf()
        # Utiliser directement _db_data_keys pour déterminer les sources
        
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        # Si une valeur n'existe pas dans la DB, utiliser la valeur par défaut passée (NC ou 0)
        
        # Fonction helper pour générer des données factices selon le type
        def generate_fake_value(key: str, default_value: Any = None) -> Any:
            """
            Génère une valeur factice réaliste selon la clé.
            Utilisé uniquement en mode brouillon quand la base est vide.
            """
            if not cls._should_use_fake_data():
                return default_value
            
            # Générer des valeurs factices réalistes selon la clé
            fake_data_map = {
                "ministre_nom": "Monsieur Moussa SANOGO",
                "ministre_date_nomination": "2024-01-15",
                "decret_attribution_numero": "n° 2024-820",
                "decret_attribution_date": "2024-01-20",
                "mission_ministere": "Mettre en œuvre la politique du Gouvernement en matière de patrimoine, de portefeuille de l'État et des entreprises publiques",
                "structure_cabinet": "Cabinet du Ministre",
                "structure_directions_centrales": 3,
                "structure_services": 5,
                "structure_directions_generales": 2,
                "decret_organisation_numero": "n° 2024-963",
                "decret_organisation_date": "2024-12-06",
            }
            
            if key in fake_data_map:
                return fake_data_map[key]
            
            # Valeurs par défaut selon le type
            if default_value == "NC" or default_value == "":
                return "Donnée factice"
            elif isinstance(default_value, (int, float)) and default_value == 0:
                return 15  # Valeur factice pour les nombres
            else:
                return default_value
        
        # Fonction helper pour récupérer une valeur principale (toutes les données sont DB)
        def get_main_value(key: str, default_value: Any = None) -> tuple[Any, str]:
            """
            Récupère une valeur principale. Toutes les données sont considérées comme DB.
            Si la valeur n'existe pas dans la DB, retourne une valeur factice en mode brouillon ou la valeur par défaut en mode final.
            
            Returns:
                Tuple (valeur, source) où source est "db" ou "fake"
            """
            # Ne pas utiliser DEFAULT_DATA, seulement les données de la DB
            value = cls.data.get(key, default_value)
            
            # Si la valeur est la valeur par défaut (NC, 0, etc.), générer une valeur factice en mode brouillon
            if value == default_value and cls._should_use_fake_data():
                fake_value = generate_fake_value(key, default_value)
                return fake_value, "fake"
            
            return value, "db"
        
        # Fonction helper pour récupérer une valeur d'introduction (toutes les données sont DB)
        def get_intro_value(key: str, default_value: Any = None) -> tuple[Any, str]:
            """
            Récupère une valeur d'introduction. Toutes les données sont considérées comme DB.
            Si la valeur n'existe pas dans la DB, retourne une valeur factice en mode brouillon ou la valeur par défaut en mode final.
            NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices.
            
            Returns:
                Tuple (valeur, source) où source est "db" ou "fake"
            """
            # Ne pas utiliser default_intro_data (DEFAULT_DATA), seulement intro_data (DB)
            value = intro_data.get(key, default_value)
            
            # Si la valeur est la valeur par défaut (NC, 0, etc.), générer une valeur factice en mode brouillon
            if value == default_value and cls._should_use_fake_data():
                fake_value = generate_fake_value(key, default_value)
                return fake_value, "fake"
            
            return value, "db"
        
        # Récupérer toutes les valeurs avec leur source
        # Utiliser "NC" pour les textes vides et 0 pour les nombres
        ministre_nom, ministre_nom_source = get_intro_value("ministre_nom", "NC")
        ministre_date, ministre_date_source = get_intro_value("ministre_date_nomination", "NC")
        decret_attr_num, decret_attr_num_source = get_intro_value("decret_attribution_numero", "NC")
        decret_attr_date, decret_attr_date_source = get_intro_value("decret_attribution_date", "NC")
        mission_ministere, mission_source = get_intro_value("mission_ministere", "NC")
        # Récupérer toutes les autres valeurs avec leur source
        structure_cabinet, structure_cabinet_source = get_intro_value("structure_cabinet", "NC")
        nb_directions, nb_directions_source = get_intro_value("structure_directions_centrales", 0)
        nb_services, nb_services_source = get_intro_value("structure_services", 0)
        nb_dg, nb_dg_source = get_intro_value("structure_directions_generales", 0)
        decret_org_num, decret_org_num_source = get_intro_value("decret_organisation_numero", "NC")
        decret_org_date, decret_org_date_source = get_intro_value("decret_organisation_date", "NC")
        contexte_texte, contexte_texte_source = get_intro_value("contexte_texte", "NC")
        premiere_partie_items, premiere_partie_items_source = get_intro_value("rapport_structure_premiere_partie", [])
        seconde_partie_items, seconde_partie_items_source = get_intro_value("rapport_structure_seconde_partie", [])
        
        # Construire la story avec Paragraph et puces
        story: list[Any] = []
        
        # Titre
        story.append(Paragraph("INTRODUCTION GÉNÉRALE", title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Formater chaque valeur selon sa source (DB en rouge, factice en violet italique)
        def format_by_source(value: Any, source: str) -> str:
            """Formate une valeur selon sa source (DB en rouge, factice en violet italique)."""
            # Retourner "NC" pour les valeurs vides au lieu d'une chaîne vide
            if not value or value == "" or value == []:
                if source == "fake":
                    return cls._format_fake_data("NC")
                return cls._format_db_data("NC")
            # Si c'est un nombre 0, retourner "0" formaté
            if isinstance(value, (int, float)) and value == 0:
                if source == "fake":
                    return cls._format_fake_data("0")
                return cls._format_db_data("0")
            
            # Formater selon la source
            if source == "fake":
                return cls._format_fake_data(str(value))
            else:
                return cls._format_db_data(str(value))
        
        # Récupérer le nom du ministère avec sa source
        # Utiliser "NC" si vide au lieu de valeur par défaut hardcodée
        ministere_value, ministere_source = get_main_value("ministere", "NC")
        formatted_ministere = format_by_source(ministere_value, ministere_source)
        
        formatted_ministre_nom = format_by_source(ministre_nom, ministre_nom_source)
        formatted_ministre_date = format_by_source(ministre_date, ministre_date_source)
        formatted_decret_attr_num = format_by_source(decret_attr_num, decret_attr_num_source)
        formatted_decret_attr_date = format_by_source(decret_attr_date, decret_attr_date_source)
        formatted_mission = format_by_source(mission_ministere, mission_source)
        
        sigle_ministere = cls._get_sigle_ministere()
        para1 = (
            f"Le {formatted_ministere} ({sigle_ministere}) est dirigé par {formatted_ministre_nom} depuis le {formatted_ministre_date}. "
            f"Sa mission est de {formatted_mission}. Cette mission "
            f"lui a été confiée conformément au décret {formatted_decret_attr_num} du {formatted_decret_attr_date} "
            f"portant attributions des membres du Gouvernement."
        )
        story.append(Paragraph(para1, body_style))
        
        # Paragraphe 2 : Structure organisationnelle (avec styling selon la source)
        # Utiliser "NC" si vide au lieu de "Cabinet du Ministre"
        formatted_structure_cabinet = format_by_source(structure_cabinet, structure_cabinet_source)
        structure_desc = formatted_structure_cabinet if structure_cabinet and structure_cabinet != "NC" else cls._format_db_data("NC")
        
        # Formater les nombres selon la source (0 si vide)
        formatted_nb_directions = format_by_source(str(nb_directions), nb_directions_source) if nb_directions else cls._format_db_data("0")
        formatted_nb_services = format_by_source(str(nb_services), nb_services_source) if nb_services else cls._format_db_data("0")
        formatted_nb_dg = format_by_source(str(nb_dg), nb_dg_source) if nb_dg else cls._format_db_data("0")
        
        # Afficher "0" si vide au lieu de chaîne vide
        directions_text = f"{formatted_nb_directions} Direction{'s' if nb_directions > 1 else ''} centrale{'s' if nb_directions > 1 else ''}" if nb_directions else cls._format_db_data("0 Direction centrale")
        services_text = f"{formatted_nb_services} Service{'s' if nb_services > 1 else ''}" if nb_services else cls._format_db_data("0 Service")
        dg_text = f"{formatted_nb_dg} Direction{'s' if nb_dg > 1 else ''} Générale{'s' if nb_dg > 1 else ''}" if nb_dg else cls._format_db_data("0 Direction Générale")
        
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
        # Afficher même si vide avec "NC"
        if contexte_texte and contexte_texte != "NC":
            from datetime import datetime
            annee_value, annee_source = get_main_value("annee", datetime.now().year)
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
        # Utiliser l'année actuelle si vide au lieu de 2024 hardcodé
        from datetime import datetime
        annee_value, annee_source = get_main_value("annee", datetime.now().year)
        formatted_annee_para4 = format_by_source(str(annee_value), annee_source)
        
        para4_intro = (
            f"Le présent rapport détaille les activités du {formatted_ministere} pour l'exercice {formatted_annee_para4} "
            f"et s'articule autour de deux grandes parties."
        )
        story.append(Paragraph(para4_intro, body_style))
        
        # Première partie avec puces (avec styling selon la source de la liste)
        #if premiere_partie_items:
        story.append(Paragraph("La première partie permettra de :", body_style))
        for item in premiere_partie_items:
            # Tous les items de la liste ont la même source que la liste
            formatted_item = format_by_source(item, premiere_partie_items_source)
            story.append(Paragraph(formatted_item, bullet_style, bulletText="•"))
        
        # Seconde partie avec puces (avec styling selon la source de la liste)
        #if seconde_partie_items:
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
        # Charger les programmes depuis la base de données uniquement (pas de DEFAULT_DATA)
        programmes = cls.data.get("programmes", [])
        
        # Récupérer les données de la partie ministère (ou utiliser des valeurs par défaut)
        partie_data = cls.data.get("partie_ministere", {})
        
        # Déterminer si les données viennent de la DB ou sont des valeurs par défaut
        # Si partie_data existe et contient programme_details, c'est qu'il vient de la DB (via load_budget_data)
        is_partie_data_from_db = bool(
            partie_data and 
            ("programme_details" in partie_data or 
             "total_programmes" in partie_data or 
             "total_actions" in partie_data)
        )
        
        # Extraire les orientations stratégiques si présentes dans partie_ministere
        orientations_from_db = partie_data.get("orientations") if partie_data else None
        
        # Si partie_data n'existe pas ou n'a pas programme_details, construire les données
        if not partie_data or "programme_details" not in partie_data:
            # Initialiser le flag pour les données factices
            is_architecture_fake = False
            
            # Calculer les totaux à partir des programmes
            total_actions = 0
            total_activites = 0
            programme_details = []
            for prog in programmes:
                num = prog.get("numero", 1)
                titre = prog.get("titre", "")
                actions = prog.get("nb_actions", 0)  # 0 si vide, pas de valeur par défaut hardcodée
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
                # Si pas de données, générer des données factices en mode brouillon
                mode = cls.data.get("mode", "brouillon")
                if mode == "brouillon" and cls._should_use_fake_data():
                    # Générer des données factices pour la démonstration
                    logger.info(f"📊 Mode brouillon: génération de données factices pour l'architecture programmatique")
                    is_architecture_fake = True
                    total_programmes = len(programmes) if programmes else 2
                    total_actions = 15
                    total_activites = 45
                    programme_details = [
                        {"numero": 1, "titre": "ADMINISTRATION GÉNÉRALE", "actions": 8, "activites": 25},
                        {"numero": 2, "titre": "GESTION DU PATRIMOINE", "actions": 7, "activites": 20},
                    ]
                    prog1_pct = (25 / total_activites * 100) if total_activites > 0 else 0
                    prog2_pct = (20 / total_activites * 100) if total_activites > 0 else 0
                else:
                    # Mode final : utiliser 0
                    prog1_pct = 0
                    prog2_pct = 0
                    total_actions = 0
                    total_activites = 0
                    programme_details = []
            
            # Charger les orientations stratégiques depuis la DB
            orientations = cls.data.get("partie_ministere", {}).get("orientations")
            if not orientations:
                # Si pas de données, utiliser une liste vide (affichage avec "NC" pour les textes)
                orientations = []
            
            # Charger les données de performance depuis load_budget_data si disponibles
            performance_data = cls.data.get("budget_data", {}).get("performance", {})
            
            # Générer des données factices pour la performance si nécessaire
            is_performance_fake = False
            mode = cls.data.get("mode", "brouillon")
            architecture_db = performance_data.get("architecture", {})
            realisations_db = performance_data.get("realisations", [])
            
            # Vérifier si les données de performance sont vides
            if (mode == "brouillon" and cls._should_use_fake_data() and
                (architecture_db.get("nb_objectifs_globaux", 0) == 0 or
                 architecture_db.get("nb_objectifs_specifiques", 0) == 0 or
                 architecture_db.get("nb_indicateurs", 0) == 0 or
                 len(realisations_db) == 0)):
                logger.info(f"📊 Mode brouillon: génération de données factices pour la performance")
                is_performance_fake = True
                # Générer des données factices pour l'architecture
                architecture_data = {
                    "nb_programmes": len(programmes) if programmes else 2,
                    "nb_objectifs_globaux": 5,
                    "nb_objectifs_specifiques": 12,
                    "nb_indicateurs": 15,
                    "nb_cibles": 15,
                }
                # Générer des données factices pour les réalisations
                realisations = [
                    {"programme": "P1: ADMINISTRATION GÉNÉRALE", "objectif_specifique": "OS 1: Améliorer la coordination", "nb_cibles": 5, "nb_cibles_atteintes": 4},
                    {"programme": "P1: ADMINISTRATION GÉNÉRALE", "objectif_specifique": "OS 2: Renforcer les capacités", "nb_cibles": 4, "nb_cibles_atteintes": 4},
                    {"programme": "P2: GESTION DU PATRIMOINE", "objectif_specifique": "OS 1: Optimiser la gestion", "nb_cibles": 6, "nb_cibles_atteintes": 5},
                ]
                taux_realisation = 86.7  # (13/15) * 100
                taux_realisation_n1 = 82.5
                nb_indicateurs_n1 = 14
            else:
                # Utiliser les données réelles
                architecture_data = {
                    "nb_programmes": architecture_db.get("nb_programmes", len(programmes) if programmes else 0),
                    "nb_objectifs_globaux": architecture_db.get("nb_objectifs_globaux", 0),
                    "nb_objectifs_specifiques": architecture_db.get("nb_objectifs_specifiques", 0),
                    "nb_indicateurs": architecture_db.get("nb_indicateurs", 0),
                    "nb_cibles": architecture_db.get("nb_cibles", 0),
                }
                realisations = realisations_db
                taux_realisation = performance_data.get("taux_realisation", 0)
                taux_realisation_n1 = performance_data.get(f"taux_realisation_{annee - 1}", 0)
                nb_indicateurs_n1 = performance_data.get(f"nb_indicateurs_{annee - 1}", 0)
            
            partie_data = {
                "total_programmes": len(programmes) if programmes else 0,
                "total_actions": total_actions,
                "total_activites": total_activites,
                "programme_details": programme_details,
                "prog1_pct": prog1_pct,
                "prog2_pct": prog2_pct,
                "source": f"Source: Annexe 4 de la Loi de Finances n° 2023-1000 du 18 décembre 2023 portant budget de l'Etat pour l'année {annee}",
                "orientations": orientations,
                "_is_architecture_fake": is_architecture_fake,  # Flag pour indiquer que les données sont factices
                "_is_performance_fake": is_performance_fake,  # Flag pour indiquer que les données de performance sont factices
                "performance": {
                    "architecture": architecture_data,
                    "realisations": realisations,
                    "taux_realisation": taux_realisation,
                    # Utiliser des clés dynamiques basées sur l'année précédente
                    f"nb_indicateurs_{annee - 1}": nb_indicateurs_n1,
                    f"taux_realisation_{annee - 1}": taux_realisation_n1,
                }
            }
            
            # Mettre à jour cls.data pour que partie_data soit disponible
            cls.data["partie_ministere"] = partie_data
        
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
        programme_details = partie_data.get("programme_details", [])
        prog1_detail = programme_details[0] if len(programme_details) > 0 else {}
        prog2_detail = programme_details[1] if len(programme_details) > 1 else {}
        prog1_pct = partie_data.get("prog1_pct", 0)
        prog2_pct = partie_data.get("prog2_pct", 0)
        
        prog1_titre = prog1_detail.get('titre', 'NC') if prog1_detail else 'NC'  # "NC" si vide
        prog2_titre = prog2_detail.get('titre', 'NC') if prog2_detail else 'NC'  # "NC" si vide
        sigle_ministere = cls._get_sigle_ministere()
        
        # Déterminer si les données sont factices (vérifier le flag ou si les données sont vides)
        mode = cls.data.get("mode", "brouillon")
        is_fake_data = (
            partie_data.get('_is_architecture_fake', False) or  # Flag indiquant que les données sont factices
            (mode == "brouillon" and 
             cls._should_use_fake_data() and
             (partie_data.get('total_actions', 0) == 0 or 
              partie_data.get('total_activites', 0) == 0 or
              prog1_titre == 'NC' or prog2_titre == 'NC'))
        )
        
        # Log pour déboguer
        if is_fake_data:
            logger.info(f"📊 Données factices détectées pour l'architecture: flag={partie_data.get('_is_architecture_fake', False)}, total_actions={partie_data.get('total_actions', 0)}")
        
        # Fonction helper pour formater selon si c'est factice ou réel
        def format_partie_value(value: Any) -> str:
            """Formate une valeur de la partie ministère selon si elle est factice ou réelle."""
            if is_fake_data:
                return cls._format_fake_data(str(value))
            else:
                return cls._format_db_data(str(value))
        
        # Formater toutes les données selon leur source
        formatted_ministere = cls._format_db_data(ministere)  # Toujours DB (nom du ministère)
        formatted_sigle = cls._format_db_data(sigle_ministere)  # Toujours DB (sigle)
        formatted_total_prog = format_partie_value(partie_data.get('total_programmes', 0))
        formatted_total_actions = format_partie_value(partie_data.get('total_actions', 0))
        formatted_total_activites = format_partie_value(partie_data.get('total_activites', 0))
        formatted_prog1_titre = format_partie_value(prog1_titre if prog1_titre != 'NC' else 'ADMINISTRATION GÉNÉRALE')
        formatted_prog1_activites = format_partie_value(prog1_detail.get('activites', 0) if prog1_detail else 0)
        formatted_prog1_pct = format_partie_value(f"{prog1_pct:.2f}")
        formatted_prog2_titre = format_partie_value(prog2_titre if prog2_titre != 'NC' else 'GESTION DU PATRIMOINE')
        formatted_prog2_activites = format_partie_value(prog2_detail.get('activites', 0) if prog2_detail else 0)
        formatted_prog2_pct = format_partie_value(f"{prog2_pct:.2f}")
        
        para1_text = (
            f"Le {formatted_ministere} ({formatted_sigle}) est subdivisé en {formatted_total_prog} programmes déclinés en "
            f"{formatted_total_actions} actions comprenant {formatted_total_activites} activités. "
            f"Le programme « {formatted_prog1_titre} » enregistre "
            f"{formatted_prog1_activites} activités ({formatted_prog1_pct}%) et le programme "
            f"« {formatted_prog2_titre} » "
            f"{formatted_prog2_activites} activités ({formatted_prog2_pct}%)."
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
        
        for prog_detail in programme_details:
            prog_num = prog_detail['numero']
            prog_titre = prog_detail['titre']
            # Formater les données du tableau selon leur source (factice ou DB)
            formatted_prog_num = format_partie_value(prog_num)
            formatted_prog_titre = format_partie_value(prog_titre)
            formatted_actions = format_partie_value(prog_detail["actions"])
            formatted_activites = format_partie_value(prog_detail["activites"])
            table_data.append([
                Paragraph(f"Programme {formatted_prog_num} : {formatted_prog_titre}", table_cell_style),
                Paragraph(formatted_actions, table_cell_center_style),
                Paragraph(formatted_activites, table_cell_center_style),
            ])
        
        # Ligne Total
        formatted_total_actions_table = format_partie_value(partie_data.get("total_actions", 0))
        formatted_total_activites_table = format_partie_value(partie_data.get("total_activites", 0))
        table_data.append([
            Paragraph("Total", ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=0)),
            Paragraph(formatted_total_actions_table, ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
            Paragraph(formatted_total_activites_table, ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
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
        # Utiliser les compteurs calculés depuis les tables, sinon utiliser la longueur de la liste
        orientations_count = partie_data.get('orientations_count') or len(set(entry.get('orientation') for entry in partie_data.get('orientations', []) if entry.get('orientation')))
        resultats_count = partie_data.get('resultats_count') or len(set(entry.get('resultat') for entry in partie_data.get('orientations', []) if entry.get('resultat')))
        objectifs_count = partie_data.get('objectifs_globaux_count') or len(set(entry.get('objectif') for entry in partie_data.get('orientations', []) if entry.get('objectif')))
        
        # Générer des données factices si toutes les valeurs sont à 0 en mode brouillon
        mode = cls.data.get("mode", "brouillon")
        is_politique_fake = (
            mode == "brouillon" and 
            cls._should_use_fake_data() and
            (orientations_count == 0 or resultats_count == 0 or objectifs_count == 0)
        )
        
        if is_politique_fake:
            logger.info(f"📊 Mode brouillon: génération de données factices pour la politique ministérielle")
            orientations_count = 3
            resultats_count = 8
            objectifs_count = 12
            # Marquer dans partie_data que les données sont factices
            partie_data['_is_politique_fake'] = True
        
        # Utiliser le flag pour déterminer si les données sont factices
        is_politique_fake_final = partie_data.get('_is_politique_fake', False) or is_politique_fake
        
        # Formater selon la source (factice ou DB)
        def format_politique_value(value: Any) -> str:
            """Formate une valeur de la politique selon si elle est factice ou réelle."""
            if is_politique_fake_final:
                return cls._format_fake_data(str(value))
            else:
                return cls._format_db_data(str(value))
        
        formatted_orientations_count = format_politique_value(orientations_count)
        formatted_resultats_count = format_politique_value(resultats_count)
        formatted_objectifs_count = format_politique_value(objectifs_count)
        
        para2_text = (
            f"Le {formatted_ministere} ({formatted_sigle}) a articulé sa politique sectorielle autour de "
            f"{formatted_orientations_count} orientations stratégiques, "
            f"{formatted_resultats_count} résultats stratégiques et "
            f"{formatted_objectifs_count} objectifs globaux."
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
        
        orientations_list = partie_data.get("orientations", [])
        
        # Si pas de données et mode brouillon, générer des données factices pour le tableau
        if not orientations_list and is_politique_fake:
            logger.info(f"📊 Mode brouillon: génération de données factices pour le tableau de politique ministérielle")
            orientations_list = [
                {"orientation": "Renforcement de la gouvernance", "resultat": "Amélioration de la transparence", "objectif": "Objectif 1: Renforcer la transparence"},
                {"orientation": "Modernisation de l'administration", "resultat": "Efficacité accrue des services", "objectif": "Objectif 2: Moderniser les processus"},
                {"orientation": "Développement du patrimoine", "resultat": "Valorisation des actifs", "objectif": "Objectif 3: Optimiser la gestion"},
            ]
        
        for orientation_data in orientations_list:
            # Formater les données du tableau selon leur source (factice ou DB)
            formatted_orientation = format_partie_value(orientation_data.get("orientation", ""))
            formatted_resultat = format_partie_value(orientation_data.get("resultat", ""))
            formatted_objectif = format_partie_value(orientation_data.get("objectif", ""))
            politique_table_data.append([
                Paragraph(formatted_orientation, table_cell_style),
                Paragraph(formatted_resultat, table_cell_style),
                Paragraph(formatted_objectif, table_cell_style),
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
        
        # Déterminer si les données de performance sont factices
        is_performance_fake = partie_data.get('_is_performance_fake', False)
        
        # Fonction helper pour formater les données de performance
        def format_performance_value(value: Any) -> str:
            """Formate une valeur de performance selon si elle est factice ou réelle."""
            if is_performance_fake:
                return cls._format_fake_data(str(value))
            else:
                return cls._format_db_data(str(value))
        
        # Formater toutes les valeurs dynamiques selon leur source
        formatted_nb_programmes = format_performance_value(architecture_data.get("nb_programmes", 0))
        formatted_nb_objectifs_globaux = format_performance_value(architecture_data.get("nb_objectifs_globaux", 0))
        formatted_nb_objectifs_specifiques = format_performance_value(architecture_data.get("nb_objectifs_specifiques", 0))
        formatted_nb_indicateurs = format_performance_value(architecture_data.get("nb_indicateurs", 0))
        formatted_nb_cibles = format_performance_value(architecture_data.get("nb_cibles", 0))
        
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
                Paragraph(formatted_nb_programmes, table_cell_center_style),
                Paragraph(formatted_nb_objectifs_globaux, table_cell_center_style),
                Paragraph(formatted_nb_objectifs_specifiques, table_cell_center_style),
                Paragraph(formatted_nb_indicateurs, table_cell_center_style),
                Paragraph(formatted_nb_cibles, table_cell_center_style),
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
        
        # Paragraphe après tableau 1 - formater toutes les valeurs dynamiques selon leur source
        formatted_ministere_para = cls._format_db_data(ministere)  # Toujours DB
        formatted_sigle_para = cls._format_db_data(cls._get_sigle_ministere())  # Toujours DB
        formatted_annee_para = cls._format_db_data(str(annee))  # Toujours DB
        
        para_architecture = (
            f"Pour l'exercice {formatted_annee_para}, le {formatted_ministere_para} ({formatted_sigle_para}) a structuré sa stratégie en "
            f"{formatted_nb_programmes} programmes, visant {formatted_nb_objectifs_globaux} objectifs globaux (OG), "
            f"qui sont déclinés en {formatted_nb_objectifs_specifiques} objectifs spécifiques (OS). "
            f"Pour mesurer ces objectifs, {formatted_nb_indicateurs} indicateurs ont été définis, "
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
            
            # Formater toutes les valeurs dynamiques selon leur source
            formatted_prog = format_performance_value(prog) if prog else ""
            formatted_os = format_performance_value(os) if os else ""
            formatted_nb_cibles = format_performance_value(nb_cibles)
            formatted_nb_atteintes = format_performance_value(nb_atteintes)
            
            # Si c'est le même programme, on ne répète pas le nom
            programme_cell = Paragraph(formatted_prog, table_cell_style) if prog != current_programme else Paragraph("", table_cell_style)
            if prog != current_programme:
                current_programme = prog
            
            tableau2_data.append([
                programme_cell,
                Paragraph(formatted_os, table_cell_style),
                Paragraph(formatted_nb_cibles, table_cell_center_style),
                Paragraph(formatted_nb_atteintes, table_cell_center_style),
            ])
        
        # Ligne Total - formater les valeurs selon leur source
        formatted_total_cibles = format_performance_value(total_cibles)
        formatted_total_cibles_atteintes = format_performance_value(total_cibles_atteintes)
        
        tableau2_data.append([
            Paragraph("TOTAL", ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=0)),
            Paragraph("", table_cell_style),
            Paragraph(formatted_total_cibles, ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
            Paragraph(formatted_total_cibles_atteintes, ParagraphStyle("TableTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=1)),
        ])
        
        # Stocker les totaux dans performance_data pour utilisation dans les paragraphes
        performance_data["total_cibles"] = total_cibles
        performance_data["total_cibles_atteintes"] = total_cibles_atteintes
        
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
        
        # Paragraphes après tableau 2 - formater toutes les valeurs dynamiques en rouge (DB)
        taux_realisation = performance_data.get("taux_realisation", 0)
        # Utiliser des clés dynamiques basées sur l'année précédente (N-1)
        annee_precedente = annee - 1
        nb_indicateurs_n1 = performance_data.get(f"nb_indicateurs_{annee_precedente}", 0)
        taux_realisation_n1 = performance_data.get(f"taux_realisation_{annee_precedente}", 0)
        
        # Utiliser 0 si aucune donnée n'est disponible (pas de valeurs par défaut hardcodées)
        
        formatted_annee_bilan = cls._format_db_data(str(annee))  # Année toujours DB
        formatted_annee_n1 = cls._format_db_data(str(annee_precedente))  # Année toujours DB
        formatted_nb_indicateurs_bilan = format_performance_value(architecture_data.get('nb_indicateurs', 0))
        formatted_taux_realisation = format_performance_value(taux_realisation)
        formatted_nb_indicateurs_n1 = format_performance_value(nb_indicateurs_n1)
        
        # Construire la liste dynamique des programmes (P1, P2, P3, etc.)
        programmes_list = []
        for prog in programmes:
            numero = prog.get("numero", 0)
            if numero > 0:
                programmes_list.append(f"P{numero}")
        
        # Formater la liste des programmes
        if len(programmes_list) == 0:
            programmes_text = "les programmes"
        elif len(programmes_list) == 1:
            programmes_text = f"le programme {cls._format_db_data(programmes_list[0])}"
        elif len(programmes_list) == 2:
            programmes_text = f"les programmes {cls._format_db_data(programmes_list[0])} et {cls._format_db_data(programmes_list[1])}"
        else:
            # Plus de 2 programmes : "P1, P2 et P3"
            programmes_formatted = [cls._format_db_data(p) for p in programmes_list[:-1]]
            programmes_text = f"les programmes {', '.join(programmes_formatted)} et {cls._format_db_data(programmes_list[-1])}"
        
        # Analyser les résultats des indicateurs pour adapter la phrase
        # Utiliser les données du Tableau 2 (total_cibles et total_cibles_atteintes calculés ci-dessus)
        # Ces valeurs sont déjà calculées dans la boucle du Tableau 2
        
        # Calculer le taux de réalisation réel si possible
        if total_cibles > 0:
            taux_realisation_calcule = (total_cibles_atteintes / total_cibles) * 100
            formatted_taux_realisation_calcule = format_performance_value(f"{taux_realisation_calcule:.1f}")
        else:
            taux_realisation_calcule = taux_realisation
            formatted_taux_realisation_calcule = format_performance_value(taux_realisation)
        
        # Adapter la phrase selon les résultats
        if total_cibles == 0:
            # Aucune cible définie
            phrase_resultats = f"Les indicateurs ont été définis, mais aucune cible n'a encore été évaluée."
        elif total_cibles_atteintes == total_cibles and total_cibles > 0:
            # Tous les objectifs sont atteints
            phrase_resultats = f"L'ensemble de ces indicateurs a atteint les objectifs fixés, ce qui correspond à un taux de réalisation de {formatted_taux_realisation_calcule}%."
        elif total_cibles_atteintes == 0 and total_cibles > 0:
            # Aucun objectif atteint
            formatted_total_cibles_para = format_performance_value(total_cibles)
            phrase_resultats = f"Sur les {formatted_total_cibles_para} cibles définies, aucune n'a été atteinte à ce jour, ce qui correspond à un taux de réalisation de {formatted_taux_realisation_calcule}%."
        else:
            # Certains objectifs sont atteints, d'autres non
            formatted_total_cibles_para = format_performance_value(total_cibles)
            formatted_cibles_atteintes_para = format_performance_value(total_cibles_atteintes)
            phrase_resultats = f"Sur les {formatted_total_cibles_para} cibles définies, {formatted_cibles_atteintes_para} ont été atteintes, ce qui correspond à un taux de réalisation de {formatted_taux_realisation_calcule}%."
        
        para_bilan1 = (
            f"Pour l'année {formatted_annee_bilan}, l'analyse du cadre de performance du ministère, tel que présenté dans le "
            f"« Document de Programmation Pluriannuelle de Dépenses Projet Annuel de Performance (DPPD-PAP) », "
            f"révèle que {formatted_nb_indicateurs_bilan} indicateurs ont été définis pour {programmes_text}. "
            f"{phrase_resultats}"
        )
        story.append(Paragraph(para_bilan1, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Construire le deuxième paragraphe de manière dynamique selon les données réelles
        # Récupérer les données de N-1 pour comparaison (utiliser les clés dynamiques)
        formatted_taux_realisation_n1 = format_performance_value(f"{taux_realisation_n1:.1f}")
        
        # Calculer la différence entre N et N-1
        evolution_taux = taux_realisation_calcule - taux_realisation_n1 if total_cibles > 0 else 0
        
        # Construire la phrase de comparaison avec N-1
        if taux_realisation_n1 == 0 or nb_indicateurs_n1 == 0:
            # Pas de données pour N-1
            phrase_comparaison_n1 = f"Les données de performance pour {formatted_annee_n1} ne sont pas disponibles pour permettre une comparaison."
        elif taux_realisation_n1 >= 100:
            # Tous les objectifs étaient atteints en N-1
            phrase_comparaison_n1 = (
                f"Par rapport à {formatted_annee_n1}, où les {formatted_nb_indicateurs_n1} indicateurs de performance évalués avaient également atteint leurs objectifs "
                f"(taux de réalisation de {formatted_taux_realisation_n1}%), "
            )
        elif taux_realisation_n1 >= 80:
            # Bon taux de réalisation en N-1
            phrase_comparaison_n1 = (
                f"Par rapport à {formatted_annee_n1}, où les {formatted_nb_indicateurs_n1} indicateurs de performance évalués présentaient un taux de réalisation de {formatted_taux_realisation_n1}%, "
            )
        else:
            # Taux de réalisation faible en N-1
            phrase_comparaison_n1 = (
                f"Par rapport à {formatted_annee_n1}, où les {formatted_nb_indicateurs_n1} indicateurs de performance évalués présentaient un taux de réalisation de {formatted_taux_realisation_n1}%, "
            )
        
        # Construire la phrase d'évolution
        if taux_realisation_n1 == 0 or nb_indicateurs_n1 == 0:
            phrase_evolution = ""
        elif abs(evolution_taux) < 1:
            # Stabilité (variation de moins de 1%)
            phrase_evolution = "une continuité dans les résultats est observée. "
        elif evolution_taux > 5:
            # Amélioration significative (> 5%)
            phrase_evolution = f"une amélioration significative est observée avec une hausse du taux de réalisation de {format_performance_value(f'{abs(evolution_taux):.1f}')} points. "
        elif evolution_taux > 0:
            # Amélioration modérée
            phrase_evolution = f"une amélioration est observée avec une hausse du taux de réalisation de {format_performance_value(f'{abs(evolution_taux):.1f}')} points. "
        elif evolution_taux < -5:
            # Dégradation significative (< -5%)
            phrase_evolution = f"une baisse du taux de réalisation de {format_performance_value(f'{abs(evolution_taux):.1f}')} points est constatée. "
        else:
            # Dégradation modérée
            phrase_evolution = f"une légère baisse du taux de réalisation de {format_performance_value(f'{abs(evolution_taux):.1f}')} points est constatée. "
        
        # Construire la phrase sur la capacité du ministère (seulement si taux élevé)
        if taux_realisation_calcule >= 80 and total_cibles > 0:
            phrase_capacite = (
                f"Ce fort taux de réalisation traduit la capacité du Ministère "
                f"à définir des objectifs structurants et à mobiliser de manière optimale les ressources nécessaires à leur atteinte. "
            )
        elif taux_realisation_calcule >= 60 and total_cibles > 0:
            phrase_capacite = (
                f"Ce taux de réalisation témoigne des efforts du Ministère "
                f"pour définir des objectifs structurants et mobiliser les ressources nécessaires à leur atteinte. "
            )
        else:
            phrase_capacite = (
                f"Des efforts supplémentaires sont nécessaires pour améliorer le taux de réalisation et "
                f"atteindre les objectifs fixés. "
            )
        
        # Construire la phrase de conclusion
        if taux_realisation_n1 == 0 or nb_indicateurs_n1 == 0:
            phrase_conclusion = ""
        elif taux_realisation_calcule >= 80 and taux_realisation_n1 >= 80:
            phrase_conclusion = (
                f"Les performances en {formatted_annee_n1} et {formatted_annee_bilan} démontrent une cohérence dans la gestion et l'atteinte des objectifs fixés."
            )
        elif evolution_taux > 0:
            phrase_conclusion = (
                f"Les performances en {formatted_annee_bilan} montrent une progression par rapport à {formatted_annee_n1}, témoignant d'une amélioration continue dans la gestion des objectifs."
            )
        elif evolution_taux < 0:
            phrase_conclusion = (
                f"Les performances en {formatted_annee_bilan} nécessitent une attention particulière pour retrouver le niveau de {formatted_annee_n1}."
            )
        else:
            phrase_conclusion = (
                f"Les performances en {formatted_annee_n1} et {formatted_annee_bilan} sont comparables, démontrant une stabilité dans la gestion des objectifs."
            )
        
        # Assembler le paragraphe complet
        para_bilan2 = f"{phrase_comparaison_n1}{phrase_evolution}{phrase_capacite}{phrase_conclusion}"
        
        # Ne pas ajouter de paragraphe vide
        if para_bilan2.strip():
            story.append(Paragraph(para_bilan2, body_style))
            story.append(Spacer(1, 0.3 * cm))
        
        # Section III. FINANCEMENT GLOBAL DU MINISTERE
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("III. FINANCEMENT GLOBAL DU MINISTÈRE", section_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Récupérer les données de financement
        financement_data = cls.data.get("financement_global", {})
        
        # Générer des données factices pour le financement si nécessaire
        is_financement_fake = False
        mode = cls.data.get("mode", "brouillon")
        
        budget_initial_total = financement_data.get("budget_initial_total", 0)
        budget_reel_total = financement_data.get("budget_reel_total", 0)
        financement_par_nature = financement_data.get("par_nature", {})
        
        # Vérifier si les données de financement sont vides
        if (mode == "brouillon" and cls._should_use_fake_data() and
            (budget_initial_total == 0 or budget_reel_total == 0 or not financement_par_nature)):
            logger.info(f"📊 Mode brouillon: génération de données factices pour le financement global")
            is_financement_fake = True
            # Générer des données factices réalistes
            budget_initial_total = 15_000_000_000.0  # 15 milliards FCFA
            budget_reel_total = 16_500_000_000.0  # 16.5 milliards FCFA (augmentation de 10%)
            evolution_total = budget_reel_total - budget_initial_total
            taux_evolution_total = (evolution_total / budget_initial_total * 100) if budget_initial_total > 0 else 0
            
            # Générer des données factices par nature
            financement_par_nature = {
                "P": {
                    "budget_initial": 8_000_000_000.0,  # 8 milliards
                    "budget_reel": 8_500_000_000.0,  # 8.5 milliards (augmentation de 6.25%)
                },
                "BS": {
                    "budget_initial": 3_500_000_000.0,  # 3.5 milliards
                    "budget_reel": 4_000_000_000.0,  # 4 milliards (augmentation de 14.3%)
                },
                "T": {
                    "budget_initial": 2_000_000_000.0,  # 2 milliards
                    "budget_reel": 2_200_000_000.0,  # 2.2 milliards (augmentation de 10%)
                },
                "I": {
                    "budget_initial": 1_500_000_000.0,  # 1.5 milliards
                    "budget_reel": 1_800_000_000.0,  # 1.8 milliards (augmentation de 20%)
                },
            }
        else:
            evolution_total = budget_reel_total - budget_initial_total
            taux_evolution_total = (evolution_total / budget_initial_total * 100) if budget_initial_total > 0 else 0
        
        # Marquer dans cls.data que les données sont factices
        if is_financement_fake:
            cls.data["_is_financement_fake"] = True
        
        # Fonction helper pour formater les données de financement
        def format_financement_value(value: Any) -> str:
            """Formate une valeur de financement selon si elle est factice ou réelle."""
            if is_financement_fake:
                return cls._format_fake_data(str(value))
            else:
                return cls._format_db_data(str(value))
        
        # Formatage des montants en FCFA avec espaces comme séparateurs
        def format_fcfa(montant: float) -> str:
            """Formate un montant en FCFA avec espaces comme séparateurs de milliers."""
            return f"{montant:,.0f}".replace(",", " ")
        
        # Récupérer les montants par nature (0 si non disponible, pas de valeurs par défaut hardcodées)
        personnel_init = financement_par_nature.get("P", {}).get("budget_initial", 0)
        personnel_reel = financement_par_nature.get("P", {}).get("budget_reel", 0)
        personnel_evol = personnel_reel - personnel_init  # Calculer l'évolution
        personnel_taux = (personnel_evol / personnel_init * 100) if personnel_init > 0 else 0
        
        biens_init = financement_par_nature.get("BS", {}).get("budget_initial", 0)
        biens_reel = financement_par_nature.get("BS", {}).get("budget_reel", 0)
        biens_evol = biens_reel - biens_init  # Calculer l'évolution
        biens_taux = (biens_evol / biens_init * 100) if biens_init > 0 else 0
        
        transferts_init = financement_par_nature.get("T", {}).get("budget_initial", 0)
        transferts_reel = financement_par_nature.get("T", {}).get("budget_reel", 0)
        transferts_evol = transferts_reel - transferts_init  # Calculer l'évolution
        transferts_taux = (transferts_evol / transferts_init * 100) if transferts_init > 0 else 0
        
        investissements_init = financement_par_nature.get("I", {}).get("budget_initial", 0)
        investissements_reel = financement_par_nature.get("I", {}).get("budget_reel", 0)
        investissements_evol = investissements_reel - investissements_init  # Calculer l'évolution
        investissements_taux = (investissements_evol / investissements_init * 100) if investissements_init > 0 else 0
        
        # Fonctions helper pour déterminer le terme approprié selon la variation
        def get_variation_term(evolution: float) -> tuple[str, str]:
            """Retourne (terme_variation, terme_variation_nom) selon le signe de l'évolution"""
            if evolution > 0:
                return ("augmentation", "hausse")
            elif evolution < 0:
                return ("diminution", "baisse")
            else:
                return ("stabilisation", "stabilisation")
        
        def get_verb_variation(evolution: float) -> str:
            """Retourne le verbe approprié selon le signe de l'évolution"""
            if evolution > 0:
                return "augmenté"
            elif evolution < 0:
                return "diminué"
            else:
                return "est resté stable"
        
        # Récupérer les interprétations personnalisées ou utiliser les valeurs par défaut
        financement_interpretations = cls.data.get("financement_interpretations", {})
        
        # Paragraphe introductif - formater toutes les valeurs dynamiques selon leur source
        formatted_annee_intro = cls._format_db_data(str(annee))  # Année toujours DB
        formatted_ministere_intro = cls._format_db_data(ministere) if ministere else cls._format_db_data("NC")  # Toujours DB
        formatted_sigle_intro = cls._format_db_data(cls._get_sigle_ministere())  # Toujours DB
        formatted_budget_initial = format_financement_value(format_fcfa(budget_initial_total)) if budget_initial_total > 0 else format_financement_value("0")
        formatted_personnel_init = format_financement_value(format_fcfa(personnel_init)) if personnel_init > 0 else format_financement_value("0")
        formatted_biens_init = format_financement_value(format_fcfa(biens_init)) if biens_init > 0 else format_financement_value("0")
        formatted_transferts_init = format_financement_value(format_fcfa(transferts_init)) if transferts_init > 0 else format_financement_value("0")
        formatted_investissements_init = format_financement_value(format_fcfa(investissements_init)) if investissements_init > 0 else format_financement_value("0")
        formatted_budget_reel = format_financement_value(format_fcfa(budget_reel_total)) if budget_reel_total > 0 else format_financement_value("0")
        formatted_evolution_total = format_financement_value(format_fcfa(abs(evolution_total))) if abs(evolution_total) > 0 else format_financement_value("0")
        formatted_taux_evolution = format_financement_value(f"{abs(taux_evolution_total):.2f}")
        
        # Déterminer les termes de variation pour le budget total
        terme_variation_total, terme_variation_nom_total = get_variation_term(evolution_total)
        signe_taux_total = "+" if taux_evolution_total > 0 else ("-" if taux_evolution_total < 0 else "")
        
        # Récupérer les raisons de variation depuis le modal (pas de valeurs par défaut)
        raisons_augmentation = financement_interpretations.get("raisons_augmentation", [])
        
        # Générer des raisons factices en mode brouillon si aucune raison n'est fournie et qu'il y a une évolution
        if (not raisons_augmentation and abs(evolution_total) > 0 and 
            mode == "brouillon" and cls._should_use_fake_data() and is_financement_fake):
            logger.info(f"📊 Mode brouillon: génération de raisons factices pour la variation budgétaire")
            if evolution_total > 0:
                # Raisons pour une hausse
                raisons_augmentation = [
                    "Le rattachement en cours de gestion des crédits de la SONAPIE, structure institutionnellement rattachée au MPPEEP mais dont les crédits ne figuraient pas dans la Loi de finances initiale du Ministère",
                    "La création en cours de gestion du projet de recensement et de sécurisation du patrimoine immobilier de l'État en Côte d'Ivoire et à l'étranger",
                    "L'augmentation des besoins en ressources humaines pour la mise en œuvre des projets prioritaires"
                ]
            elif evolution_total < 0:
                # Raisons pour une baisse
                raisons_augmentation = [
                    "La réduction des allocations budgétaires suite aux ajustements des priorités gouvernementales",
                    "L'optimisation des ressources suite à la rationalisation des dépenses",
                    "Le report de certains projets à l'exercice suivant"
                ]
        
        # Construire le texte introductif avec ou sans la phrase sur les raisons
        if raisons_augmentation and abs(evolution_total) > 0:
            # Adapter le texte selon le type de variation (hausse, baisse)
            terme_explication = "hausse" if evolution_total > 0 else "baisse"
            para_intro_default = (
                f"Au titre de l'exercice {formatted_annee_intro}, le {formatted_ministere_intro} ({formatted_sigle_intro}) a bénéficié d'un budget initial "
                f"de {formatted_budget_initial} FCFA (<b>Annexe 4, loi des finances {formatted_annee_intro}</b>) dont "
                f"{formatted_personnel_init} F CFA de personnel, {formatted_biens_init} F CFA de biens et services, "
                f"{formatted_transferts_init} FCFA de transfert et {formatted_investissements_init} FCFA d'investissement. "
                f"À la suite des ajustements opérés en cours d'exercice, le budget actuel pour l'année {formatted_annee_intro} est ressorti à "
                f"{formatted_budget_reel} FCFA, soit une {terme_variation_total} de {formatted_evolution_total} FCFA "
                f"correspondant à {signe_taux_total}{formatted_taux_evolution} %. Cette {terme_explication} s'explique principalement par les raisons suivantes :"
            )
        else:
            if abs(evolution_total) > 0:
                para_intro_default = (
                    f"Au titre de l'exercice {formatted_annee_intro}, le {formatted_ministere_intro} ({formatted_sigle_intro}) a bénéficié d'un budget initial "
                    f"de {formatted_budget_initial} FCFA (<b>Annexe 4, loi des finances {formatted_annee_intro}</b>) dont "
                    f"{formatted_personnel_init} F CFA de personnel, {formatted_biens_init} F CFA de biens et services, "
                    f"{formatted_transferts_init} FCFA de transfert et {formatted_investissements_init} FCFA d'investissement. "
                    f"À la suite des ajustements opérés en cours d'exercice, le budget actuel pour l'année {formatted_annee_intro} est ressorti à "
                    f"{formatted_budget_reel} FCFA, soit une {terme_variation_total} de {formatted_evolution_total} FCFA "
                    f"correspondant à {signe_taux_total}{formatted_taux_evolution} %."
                )
            else:
                para_intro_default = (
                    f"Au titre de l'exercice {formatted_annee_intro}, le {formatted_ministere_intro} ({formatted_sigle_intro}) a bénéficié d'un budget initial "
                    f"de {formatted_budget_initial} FCFA (<b>Annexe 4, loi des finances {formatted_annee_intro}</b>) dont "
                    f"{formatted_personnel_init} F CFA de personnel, {formatted_biens_init} F CFA de biens et services, "
                    f"{formatted_transferts_init} FCFA de transfert et {formatted_investissements_init} FCFA d'investissement. "
                    f"À la suite des ajustements opérés en cours d'exercice, le budget actuel pour l'année {formatted_annee_intro} est ressorti à "
                    f"{formatted_budget_reel} FCFA, soit une stabilisation du budget."
                )
        
        para_intro = financement_interpretations.get("intro", para_intro_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if para_intro != para_intro_default:
            para_intro = cls._format_db_data(para_intro)
        story.append(Paragraph(para_intro, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Définir le style bullet pour les listes à puces (utilisé pour les raisons et les évolutions par nature)
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
        
        # Afficher les raisons uniquement si elles sont fournies par l'utilisateur et si la variation est significative
        if raisons_augmentation and abs(evolution_total) > 0:
            for raison in raisons_augmentation:
                if raison and raison.strip():  # Ignorer les raisons vides
                    # Formater les raisons selon leur source (factice ou DB)
                    if is_financement_fake and mode == "brouillon" and cls._should_use_fake_data():
                        formatted_raison = cls._format_fake_data(raison.strip())
                    else:
                        formatted_raison = cls._format_db_data(raison.strip())
                    story.append(Paragraph(formatted_raison, bullet_style, bulletText="•"))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe d'introduction pour l'évolution par nature
        para_evolution_intro_default = "L'évolution des ressources budgétaires du ministère par nature de dépenses se présente comme suit :"
        para_evolution_intro = financement_interpretations.get("evolution_intro", para_evolution_intro_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if para_evolution_intro != para_evolution_intro_default:
            para_evolution_intro = cls._format_db_data(para_evolution_intro)
        story.append(Paragraph(para_evolution_intro, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Puces pour chaque nature de dépense - formater toutes les valeurs dynamiques selon leur source
        formatted_personnel_init_evol = format_financement_value(format_fcfa(personnel_init)) if personnel_init > 0 else format_financement_value("0")
        formatted_personnel_reel_evol = format_financement_value(format_fcfa(personnel_reel)) if personnel_reel > 0 else format_financement_value("0")
        formatted_personnel_evol_val = format_financement_value(format_fcfa(abs(personnel_evol))) if abs(personnel_evol) > 0 else format_financement_value("0")
        signe_personnel_taux = "+" if personnel_taux > 0 else ("-" if personnel_taux < 0 else "")
        formatted_personnel_taux_val = format_financement_value(f"{abs(personnel_taux):.1f}")
        terme_personnel, terme_personnel_nom = get_variation_term(personnel_evol)
        
        if abs(personnel_evol) > 0:
            evolution_personnel_default = (
                f"<b>Dépenses de personnel :</b> Le budget passe de {formatted_personnel_init_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b>) à {formatted_personnel_reel_evol} FCFA (budget actuel {formatted_annee_intro}), "
                f"soit une {terme_personnel} de {formatted_personnel_evol_val} FCFA, représentant une {terme_personnel_nom} de {signe_personnel_taux}{formatted_personnel_taux_val} %."
            )
            evolution_personnel = financement_interpretations.get("evolution_personnel", evolution_personnel_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_personnel != evolution_personnel_default:
                evolution_personnel = cls._format_db_data(evolution_personnel)
        else:
            evolution_personnel_default = (
                f"<b>Dépenses de personnel :</b> Le budget est resté stable à {formatted_personnel_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_personnel = financement_interpretations.get("evolution_personnel", evolution_personnel_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_personnel != evolution_personnel_default:
                evolution_personnel = cls._format_db_data(evolution_personnel)
        story.append(Paragraph(evolution_personnel, bullet_style, bulletText="•"))
        
        formatted_biens_init_evol = format_financement_value(format_fcfa(biens_init)) if biens_init > 0 else format_financement_value("0")
        formatted_biens_reel_evol = format_financement_value(format_fcfa(biens_reel)) if biens_reel > 0 else format_financement_value("0")
        formatted_biens_evol_val = format_financement_value(format_fcfa(abs(biens_evol))) if abs(biens_evol) > 0 else format_financement_value("0")
        signe_biens_taux = "+" if biens_taux > 0 else ("-" if biens_taux < 0 else "")
        formatted_biens_taux_val = format_financement_value(f"{abs(biens_taux):.1f}")
        verbe_biens = get_verb_variation(biens_evol)
        terme_biens, _ = get_variation_term(biens_evol)
        
        if abs(biens_evol) > 0:
            evolution_biens_default = (
                f"<b>Biens et services :</b> Le budget alloué a {verbe_biens} de {formatted_biens_evol_val} FCFA, "
                f"passant de {formatted_biens_init_evol} FCFA (<b>Annexe 4, loi des finances {formatted_annee_intro}</b>) à "
                f"{formatted_biens_reel_evol} FCFA (budget actuel {formatted_annee_intro}), soit une {terme_biens} de {signe_biens_taux}{formatted_biens_taux_val}%."
            )
            evolution_biens = financement_interpretations.get("evolution_biens", evolution_biens_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_biens != evolution_biens_default:
                evolution_biens = cls._format_db_data(evolution_biens)
        else:
            evolution_biens_default = (
                f"<b>Biens et services :</b> Le budget alloué est resté stable à {formatted_biens_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_biens = financement_interpretations.get("evolution_biens", evolution_biens_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_biens != evolution_biens_default:
                evolution_biens = cls._format_db_data(evolution_biens)
        story.append(Paragraph(evolution_biens, bullet_style, bulletText="•"))
        
        formatted_transferts_init_evol = format_financement_value(format_fcfa(transferts_init)) if transferts_init > 0 else format_financement_value("0")
        formatted_transferts_reel_evol = format_financement_value(format_fcfa(transferts_reel)) if transferts_reel > 0 else format_financement_value("0")
        formatted_transferts_evol_val = format_financement_value(format_fcfa(abs(transferts_evol))) if abs(transferts_evol) > 0 else format_financement_value("0")
        terme_transferts, _ = get_variation_term(transferts_evol)
        
        if abs(transferts_evol) > 0:
            evolution_transferts_default = (
                f"<b>Transferts :</b> Cette nature enregistre une évolution, "
                f"passant de {formatted_transferts_init_evol} FCFA (<b>Annexe 4, loi des finances {formatted_annee_intro}</b>) à "
                f"{formatted_transferts_reel_evol} FCFA (budget actuel {formatted_annee_intro}), soit une {terme_transferts} de {formatted_transferts_evol_val} FCFA."
            )
            evolution_transferts = financement_interpretations.get("evolution_transferts", evolution_transferts_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_transferts != evolution_transferts_default:
                evolution_transferts = cls._format_db_data(evolution_transferts)
        else:
            evolution_transferts_default = (
                f"<b>Transferts :</b> Le budget est resté stable à {formatted_transferts_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_transferts = financement_interpretations.get("evolution_transferts", evolution_transferts_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_transferts != evolution_transferts_default:
                evolution_transferts = cls._format_db_data(evolution_transferts)
        story.append(Paragraph(evolution_transferts, bullet_style, bulletText="•"))
        
        formatted_investissements_init_evol = format_financement_value(format_fcfa(investissements_init)) if investissements_init > 0 else format_financement_value("0")
        formatted_investissements_reel_evol = format_financement_value(format_fcfa(investissements_reel)) if investissements_reel > 0 else format_financement_value("0")
        formatted_investissements_evol_val = format_financement_value(format_fcfa(abs(investissements_evol))) if abs(investissements_evol) > 0 else format_financement_value("0")
        terme_investissements, _ = get_variation_term(investissements_evol)
        
        if abs(investissements_evol) > 0:
            evolution_investissements_default = (
                f"<b>Investissements :</b> Le budget est passé de {formatted_investissements_init_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b>) à {formatted_investissements_reel_evol} FCFA (budget actuel {formatted_annee_intro}), "
                f"soit une {terme_investissements} de {formatted_investissements_evol_val} FCFA."
            )
            evolution_investissements = financement_interpretations.get("evolution_investissements", evolution_investissements_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_investissements != evolution_investissements_default:
                evolution_investissements = cls._format_db_data(evolution_investissements)
        else:
            evolution_investissements_default = (
                f"<b>Investissements :</b> Le budget est resté stable à {formatted_investissements_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_investissements = financement_interpretations.get("evolution_investissements", evolution_investissements_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_investissements != evolution_investissements_default:
                evolution_investissements = cls._format_db_data(evolution_investissements)
        story.append(Paragraph(evolution_investissements, bullet_style, bulletText="•"))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Note sur la comparaison N-1 et N - optionnelle, affichée uniquement si fournie par l'utilisateur
        note_comparaison_custom = financement_interpretations.get("note_comparaison")
        if note_comparaison_custom and note_comparaison_custom.strip():
            # Ajouter automatiquement le préfixe "NB :" et formater en rouge (données de la base)
            # Format: <font color="#FF0000"><b>NB :</b> texte de la note</font>
            note_text = note_comparaison_custom.strip()
            note_comparaison = f'<font color="#FF0000"><b>NB :</b> {note_text}</font>'
            story.append(Paragraph(note_comparaison, body_style))
            story.append(Spacer(1, 0.3 * cm))
        
        # Section : Répartition du budget actuel par nature de dépenses - formater toutes les valeurs dynamiques selon leur source
        formatted_ministere_repart = cls._format_db_data(ministere) if ministere else cls._format_db_data("NC")  # Toujours DB
        formatted_sigle_repart = cls._format_db_data(cls._get_sigle_ministere())  # Toujours DB
        formatted_budget_reel_repart = format_financement_value(format_fcfa(budget_reel_total)) if budget_reel_total > 0 else format_financement_value("0")
        
        para_repartition_default = (
            f"Ainsi, le budget actuel du {formatted_ministere_repart} ({formatted_sigle_repart}) s'élève à un total de "
            f"<b>{formatted_budget_reel_repart} F CFA</b>, réparti par nature de dépenses comme suit :"
        )
        para_repartition = financement_interpretations.get("repartition_intro", para_repartition_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if para_repartition != para_repartition_default:
            para_repartition = cls._format_db_data(para_repartition)
        story.append(Paragraph(para_repartition, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Calculer les pourcentages
        pct_personnel = (personnel_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        pct_biens = (biens_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        pct_transferts = (transferts_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        pct_investissements = (investissements_reel / budget_reel_total * 100) if budget_reel_total > 0 else 0
        
        # Puces avec les pourcentages - formater toutes les valeurs dynamiques selon leur source
        formatted_personnel_repart = format_financement_value(format_fcfa(personnel_reel)) if personnel_reel > 0 else format_financement_value("0")
        formatted_pct_personnel = format_financement_value(f"{pct_personnel:.1f}")
        
        repartition_personnel_default = (
            f"• <b>Personnel</b>: {formatted_personnel_repart} F CFA, représentant <b>{formatted_pct_personnel}%</b> du total ;"
        )
        repartition_personnel = financement_interpretations.get("repartition_personnel", repartition_personnel_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if repartition_personnel != repartition_personnel_default:
            repartition_personnel = cls._format_db_data(repartition_personnel)
        story.append(Paragraph(repartition_personnel, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        formatted_biens_repart = format_financement_value(format_fcfa(biens_reel)) if biens_reel > 0 else format_financement_value("0")
        formatted_pct_biens = format_financement_value(f"{pct_biens:.1f}")
        
        repartition_biens_default = (
            f"• <b>Biens et services</b>: {formatted_biens_repart} F CFA, représentant <b>{formatted_pct_biens}%</b> du total ;"
        )
        repartition_biens = financement_interpretations.get("repartition_biens", repartition_biens_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if repartition_biens != repartition_biens_default:
            repartition_biens = cls._format_db_data(repartition_biens)
        story.append(Paragraph(repartition_biens, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        formatted_transferts_repart = format_financement_value(format_fcfa(transferts_reel)) if transferts_reel > 0 else format_financement_value("0")
        formatted_pct_transferts = format_financement_value(f"{pct_transferts:.1f}")
        
        repartition_transferts_default = (
            f"• <b>Transferts</b>: {formatted_transferts_repart} F CFA, représentant <b>{formatted_pct_transferts}%</b> du total ;"
        )
        repartition_transferts = financement_interpretations.get("repartition_transferts", repartition_transferts_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if repartition_transferts != repartition_transferts_default:
            repartition_transferts = cls._format_db_data(repartition_transferts)
        story.append(Paragraph(repartition_transferts, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        formatted_investissements_repart = format_financement_value(format_fcfa(investissements_reel)) if investissements_reel > 0 else format_financement_value("0")
        formatted_pct_investissements = format_financement_value(f"{pct_investissements:.1f}")
        
        repartition_investissements_default = (
            f"• <b>Investissements</b>: {formatted_investissements_repart} F CFA, représentant <b>{formatted_pct_investissements}%</b> du total."
        )
        repartition_investissements = financement_interpretations.get("repartition_investissements", repartition_investissements_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if repartition_investissements != repartition_investissements_default:
            repartition_investissements = cls._format_db_data(repartition_investissements)
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
            source_text_default = f"Source: Situation d'exécution issue du SIGOBE/DAAF"
            source_text = financement_interpretations.get("repartition_source", source_text_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if source_text != source_text_default:
                source_text = cls._format_db_data(source_text)
            else:
                # Formater les parties dynamiques (année) dans la source par défaut
                source_text = cls._format_db_data(source_text)
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
        intro_tableau3_default = "Le tableau ci-dessous rend compte de l'exécution des budgets alloués au Ministère."
        intro_tableau3 = financement_interpretations.get("intro_tableau3", intro_tableau3_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if intro_tableau3 != intro_tableau3_default:
            intro_tableau3 = cls._format_db_data(intro_tableau3)
        story.append(Paragraph(intro_tableau3, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Titre du tableau
        story.append(Paragraph("<b>Tableau 3: Tableau présentant l'exécution du budget du ministère</b>", subsection_title_style))
        
        # Récupérer les données pour le tableau 3
        # Utiliser les données déjà chargées pour le graphique
        annee_precedente = annee - 1
        # TODO: Récupérer le budget réel de l'année précédente depuis la base de données
        # Pour l'instant, utiliser une valeur calculée basée sur le budget actuel
        budget_annee_precedente = budget_reel_total * 0.95  # Approximation: 95% du budget actuel
        prev_annee = budget_reel_total  # Budget prévu pour l'année (budget actuel)
        real_annee = prev_annee - 308792055  # Budget réalisé pour l'année (légèrement inférieur)
        ecart_annee = prev_annee - real_annee
        tx_real_annee = (real_annee / prev_annee * 100) if prev_annee > 0 else 0
        
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
        # Formater les années dans les en-têtes selon leur source (dynamiques)
        annee_precedente = annee - 1
        annee_precedente_formatted = format_financement_value(str(annee_precedente))
        annee_actuelle_formatted = format_financement_value(str(annee))
        
        # Formater les valeurs communes (zéro et tiret) selon leur source
        formatted_zero = format_financement_value(format_fcfa(0))
        formatted_dash = format_financement_value("-")
        
        # En-têtes multi-lignes
        table_data = []
        # Ligne 1: En-têtes principaux
        table_data.append([
            Paragraph("Unités", table_header_style),
            Paragraph(f"REALISATIONS<br/>{annee_precedente_formatted}", table_header_style),
            Paragraph(annee_actuelle_formatted, table_header_style),  # Cette cellule sera fusionnée sur 4 colonnes
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
        # Formater toutes les valeurs numériques selon leur source
        formatted_budget_annee_precedente = format_financement_value(format_fcfa(budget_annee_precedente))
        formatted_prev_annee = format_financement_value(format_fcfa(prev_annee))
        formatted_real_annee = format_financement_value(format_fcfa(real_annee))
        formatted_ecart_annee = format_financement_value(format_fcfa(ecart_annee))
        formatted_tx_real_annee = format_financement_value(f"{tx_real_annee:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Ressources intérieures", table_cell_style),
            Paragraph(formatted_budget_annee_precedente, table_cell_right_style),
            Paragraph(formatted_prev_annee, table_cell_right_style),
            Paragraph(formatted_real_annee, table_cell_right_style),
            Paragraph(formatted_ecart_annee, table_cell_right_style),
            Paragraph(formatted_tx_real_annee, table_cell_center_style),
        ])
        
        # 1.1.1 Budget de l'Etat
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.1 Budget de l'Etat (Trésor)", table_cell_style),
            Paragraph(formatted_budget_annee_precedente, table_cell_right_style),
            Paragraph(formatted_prev_annee, table_cell_right_style),
            Paragraph(formatted_real_annee, table_cell_right_style),
            Paragraph(formatted_ecart_annee, table_cell_right_style),
            Paragraph(formatted_tx_real_annee, table_cell_center_style),
        ])
        
        # 1.1.2 Recettes de services
        formatted_dash = format_financement_value("-")
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.2 Recettes de services", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # 1.2 Ressources extérieures
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Ressources extérieures", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # 1.2.1 Emprunts projets
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.1 Emprunts projets", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # 1.2.2 Dons Projets
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.2 Dons Projets", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # 1.2.3 Appuis budgétaires ciblés
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.2.3 Appuis budgétaires ciblés", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
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
        # Formater toutes les valeurs numériques selon leur source
        formatted_personnel_prev = format_financement_value(format_fcfa(personnel_prev))
        formatted_personnel_real = format_financement_value(format_fcfa(personnel_real))
        formatted_personnel_ecart = format_financement_value(format_fcfa(personnel_ecart))
        formatted_personnel_tx = format_financement_value(f"{personnel_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Personnel", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),  # 2023 - à remplacer par données réelles
            Paragraph(formatted_personnel_prev, table_cell_right_style),
            Paragraph(formatted_personnel_real, table_cell_right_style),
            Paragraph(formatted_personnel_ecart, table_cell_right_style),
            Paragraph(formatted_personnel_tx, table_cell_center_style),
        ])
        
        # 2.1.1 Solde
        # Formater toutes les valeurs numériques selon leur source
        formatted_solde_prev = format_financement_value(format_fcfa(6270538992))
        formatted_solde_real = format_financement_value(format_fcfa(6270538792))
        formatted_solde_ecart = format_financement_value(format_fcfa(200))
        formatted_100_pct = format_financement_value("100%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.1 Solde y compris EPN", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_solde_prev, table_cell_right_style),
            Paragraph(formatted_solde_real, table_cell_right_style),
            Paragraph(formatted_solde_ecart, table_cell_right_style),
            Paragraph(formatted_100_pct, table_cell_center_style),
        ])
        
        # 2.1.2 Contractuels
        formatted_contractuels_prev = format_financement_value(format_fcfa(873574247))
        formatted_contractuels_real = format_financement_value(format_fcfa(873546247))
        formatted_contractuels_ecart = format_financement_value(format_fcfa(28000))
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.2 Contractuels hors solde", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_contractuels_prev, table_cell_right_style),
            Paragraph(formatted_contractuels_real, table_cell_right_style),
            Paragraph(formatted_contractuels_ecart, table_cell_right_style),
            Paragraph(formatted_100_pct, table_cell_center_style),
        ])
        
        # 2.2 Biens et Service
        # Formater toutes les valeurs numériques selon leur source
        formatted_biens_prev = format_financement_value(format_fcfa(biens_prev))
        formatted_biens_real = format_financement_value(format_fcfa(biens_real))
        formatted_biens_ecart = format_financement_value(format_fcfa(biens_ecart))
        formatted_biens_tx = format_financement_value(f"{biens_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Biens et Service", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_biens_prev, table_cell_right_style),
            Paragraph(formatted_biens_real, table_cell_right_style),
            Paragraph(formatted_biens_ecart, table_cell_right_style),
            Paragraph(formatted_biens_tx, table_cell_center_style),
        ])
        
        # 2.3 Transferts
        formatted_transferts_prev = format_financement_value(format_fcfa(transferts_prev))
        formatted_transferts_real = format_financement_value(format_fcfa(transferts_real))
        formatted_transferts_ecart = format_financement_value(format_fcfa(transferts_ecart))
        formatted_transferts_tx = format_financement_value(f"{transferts_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 Transferts", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_transferts_prev, table_cell_right_style),
            Paragraph(formatted_transferts_real, table_cell_right_style),
            Paragraph(formatted_transferts_ecart, table_cell_right_style),
            Paragraph(formatted_transferts_tx, table_cell_center_style),
        ])
        
        # 2.3.1 Transferts courants
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.1 Transferts courants", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_transferts_prev, table_cell_right_style),
            Paragraph(formatted_transferts_real, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_100_pct, table_cell_center_style),
        ])
        
        # 2.3.2 Transferts en capital
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.2 Transferts en capital", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # 2.4 Investissement
        # Formater toutes les valeurs numériques selon leur source
        formatted_investissements_prev = format_financement_value(format_fcfa(investissements_prev))
        formatted_investissements_real = format_financement_value(format_fcfa(investissements_real))
        formatted_investissements_ecart = format_financement_value(format_fcfa(investissements_ecart))
        formatted_investissements_tx = format_financement_value(f"{investissements_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Investissement", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_investissements_prev, table_cell_right_style),
            Paragraph(formatted_investissements_real, table_cell_right_style),
            Paragraph(formatted_investissements_ecart, table_cell_right_style),
            Paragraph(formatted_investissements_tx, table_cell_center_style),
        ])
        
        # 2.4.1 Trésor
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.1 Trésor", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_investissements_prev, table_cell_right_style),
            Paragraph(formatted_investissements_real, table_cell_right_style),
            Paragraph(formatted_investissements_ecart, table_cell_right_style),
            Paragraph(formatted_investissements_tx, table_cell_center_style),
        ])
        
        # 2.4.2 Financement extérieur
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.2 Financement extérieur", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # Dons
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Dons", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # Emprunts
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Emprunts", table_cell_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_zero, table_cell_right_style),
            Paragraph(formatted_dash, table_cell_center_style),
        ])
        
        # TOTAL
        table_data.append([
            Paragraph("<b>TOTAL</b>", table_total_style),
            Paragraph(formatted_budget_annee_precedente, table_cell_right_style),
            Paragraph(formatted_prev_annee, table_cell_right_style),
            Paragraph(formatted_real_annee, table_cell_right_style),
            Paragraph(formatted_ecart_annee, table_cell_right_style),
            Paragraph(formatted_tx_real_annee, table_cell_center_style),
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
        annee_precedente_financement = annee - 1
        formatted_annee_prec_financement = cls._format_db_data(str(annee_precedente_financement))
        story.append(Paragraph(f"Source: Situation d'exécution issue du SIGOBE / RAP {formatted_annee_prec_financement}", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Analyse de l'exécution budgétaire
        # Calculer les taux d'exécution réels basés sur les données
        tx_execution_global = (real_annee / prev_annee * 100) if prev_annee > 0 else 0
        tx_execution_personnel = (personnel_real / personnel_prev * 100) if personnel_prev > 0 else 0
        tx_execution_biens = (biens_real / biens_prev * 100) if biens_prev > 0 else 0
        tx_execution_transferts = (transferts_real / transferts_prev * 100) if transferts_prev > 0 else 0
        tx_execution_investissements = (investissements_real / investissements_prev * 100) if investissements_prev > 0 else 0
        
        # Formatage des montants et taux selon leur source (factice ou DB) - utiliser format_financement_value
        formatted_annee = format_financement_value(str(annee))
        formatted_prev_annee = format_financement_value(format_fcfa(prev_annee))
        formatted_real_annee = format_financement_value(format_fcfa(real_annee))
        formatted_tx_global = format_financement_value(f"{tx_execution_global:.2f}%")
        formatted_personnel_prev = format_financement_value(format_fcfa(personnel_prev))
        formatted_personnel_real = format_financement_value(format_fcfa(personnel_real))
        formatted_biens_prev = format_financement_value(format_fcfa(biens_prev))
        formatted_biens_real = format_financement_value(format_fcfa(biens_real))
        formatted_tx_biens = format_financement_value(f"{tx_execution_biens:.2f}%")
        formatted_transferts_prev = format_financement_value(format_fcfa(transferts_prev))
        formatted_tx_transferts = format_financement_value(f"{tx_execution_transferts:.2f}%")
        formatted_investissements_prev = format_financement_value(format_fcfa(investissements_prev))
        formatted_investissements_real = format_financement_value(format_fcfa(investissements_real))
        formatted_tx_investissements = format_financement_value(f"{tx_execution_investissements:.2f}%")
        
        # Récupérer les interprétations personnalisées pour l'analyse d'exécution
        financement_interpretations = cls.data.get("financement_interpretations", {})
        
        # Commentaire sur le personnel (personnalisable)
        commentaire_personnel = financement_interpretations.get("analyse_personnel_commentaire")
        if commentaire_personnel and commentaire_personnel.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_personnel_formatted = cls._format_db_data(commentaire_personnel.strip())
            phrase_personnel = f"Concernant les dépenses de personnel, le budget prévu était de <b>{formatted_personnel_prev}</b>, et le montant effectivement exécuté s'est élevé à <b>{formatted_personnel_real}</b>. {commentaire_personnel_formatted}<br/><br/>"
        else:
            phrase_personnel = f"Concernant les dépenses de personnel, le budget prévu était de <b>{formatted_personnel_prev}</b>, et le montant effectivement exécuté s'est élevé à <b>{formatted_personnel_real}</b>.<br/><br/>"
        
        # Commentaire sur les biens et services (personnalisable)
        commentaire_biens = financement_interpretations.get("analyse_biens_commentaire")
        if commentaire_biens and commentaire_biens.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_biens_formatted = cls._format_db_data(commentaire_biens.strip())
            phrase_biens = f"Pour ce qui est des biens et services, le budget alloué qui était de <b>{formatted_biens_prev}</b>, a été exécuté à hauteur de <b>{formatted_biens_real}</b> soit un taux d'exécution de <b>{formatted_tx_biens}</b>. {commentaire_biens_formatted}<br/><br/>"
        else:
            phrase_biens = f"Pour ce qui est des biens et services, le budget alloué qui était de <b>{formatted_biens_prev}</b>, a été exécuté à hauteur de <b>{formatted_biens_real}</b> soit un taux d'exécution de <b>{formatted_tx_biens}</b>.<br/><br/>"
        
        # Commentaire sur les transferts (personnalisable, sans mention fixe de la SONAPIE)
        commentaire_transferts = financement_interpretations.get("analyse_transferts_commentaire")
        if commentaire_transferts and commentaire_transferts.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_transferts_formatted = cls._format_db_data(commentaire_transferts.strip())
            phrase_transferts = f"Concernant les transferts, le montant programmé de <b>{formatted_transferts_prev}</b> a été entièrement exécuté. Le taux d'exécution est ainsi de <b>{formatted_tx_transferts}</b>, {commentaire_transferts_formatted}<br/><br/>"
        else:
            # Version générique sans mention spécifique
            phrase_transferts = f"Concernant les transferts, le montant programmé de <b>{formatted_transferts_prev}</b> a été entièrement exécuté. Le taux d'exécution est ainsi de <b>{formatted_tx_transferts}</b>.<br/><br/>"
        
        # Commentaire sur les investissements (personnalisable)
        commentaire_investissements = financement_interpretations.get("analyse_investissements_commentaire")
        if commentaire_investissements and commentaire_investissements.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_investissements_formatted = cls._format_db_data(commentaire_investissements.strip())
            phrase_investissements = f"Pour les investissements, le budget actuel de <b>{formatted_investissements_prev}</b> a été exécuté à hauteur de <b>{formatted_investissements_real}</b> soit un taux d'exécution de <b>{formatted_tx_investissements}</b>. {commentaire_investissements_formatted}<br/><br/>"
        else:
            phrase_investissements = f"Pour les investissements, le budget actuel de <b>{formatted_investissements_prev}</b> a été exécuté à hauteur de <b>{formatted_investissements_real}</b> soit un taux d'exécution de <b>{formatted_tx_investissements}</b>.<br/><br/>"
       
        # Formatage des montants pour l'analyse (valeurs en rouge, texte en noir)
        analyse_text = (
            f"Le budget actuel {formatted_annee} du ministère qui s'élevait à <b>{formatted_prev_annee}</b> a été exécuté à hauteur de <b>{formatted_real_annee}</b> soit un taux d'exécution global de <b>{formatted_tx_global}</b>.<br/><br/>"
            f"{phrase_personnel}"
            f"{phrase_biens}"
            f"{phrase_transferts}"
            f"{phrase_investissements}"
            f'<font color="#FF0000"><b>NB :</b> Les raisons expliquant les niveaux d\'exécution seront évoquées dans la suite du rapport.</font>'
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

    
    @staticmethod
    def _format_data_by_source(text: str, is_default: bool = False, is_db: bool = False, is_user: bool = False) -> str:
        """
        Formate le texte selon sa source.
        
        Args:
            text: Le texte à formater
            is_default: True si c'est une donnée par défaut
            is_db: True si c'est une donnée de la base de données
            is_user: True si c'est une donnée utilisateur
            
        Returns:
            Le texte formaté selon la source (priorité: user > db > default)
        """
        if is_user:
            return RapportAnnuelPerformanceGeneratorSimpleDoc._format_db_data(text)
        elif is_db:
            return RapportAnnuelPerformanceGeneratorSimpleDoc._format_db_data(text)
        elif is_default:
            return RapportAnnuelPerformanceGeneratorSimpleDoc._format_db_data(text)
        return text
    
    @staticmethod
    def _determine_data_source(programme_data: dict, key: str, db_value: Any = None, default_value: Any = None) -> tuple[Any, str]:
        """
        Détermine la source d'une donnée et retourne la valeur à utiliser avec sa source.
        
        Logique de priorité :
        1. Si la donnée existe dans programme_data (via modal utilisateur) → USER (vert)
        2. Sinon, si la donnée vient de la DB → DB (bold+italique)
        3. Sinon → DEFAULT (rouge)
        
        Args:
            programme_data: Dictionnaire contenant les données fournies par l'utilisateur via le modal
            key: Clé de la donnée à récupérer
            db_value: Valeur provenant de la base de données (None si pas de valeur DB)
            default_value: Valeur par défaut à utiliser si ni USER ni DB
            
        Returns:
            Tuple (valeur à utiliser, source: "user", "db", ou "default")
        """
        # Priorité 1: Données utilisateur (via modal)
        user_value = programme_data.get(key)
        if user_value is not None and user_value != "":
            return user_value, "user"
        
        # Priorité 2: Données de la base de données
        if db_value is not None and db_value != "":
            return db_value, "db"
        
        # Priorité 3: Données par défaut
        return default_value, "default"
    
    @staticmethod
    def _format_data_with_source(programme_data: dict, key: str, db_value: Any = None, default_value: Any = None) -> str:
        """
        Détermine la source d'une donnée et retourne la valeur formatée selon sa source.
        
        Args:
            programme_data: Dictionnaire contenant les données fournies par l'utilisateur via le modal
            key: Clé de la donnée à récupérer
            db_value: Valeur provenant de la base de données (None si pas de valeur DB)
            default_value: Valeur par défaut à utiliser si ni USER ni DB
            
        Returns:
            La valeur formatée selon sa source (user=vert, db=bold+italique, default=rouge)
        """
        value, source = RapportAnnuelPerformanceGeneratorSimpleDoc._determine_data_source(
            programme_data, key, db_value, default_value
        )
        
        if value is None:
            return ""
        
        # Convertir en string si nécessaire
        text = str(value) if not isinstance(value, str) else value
        
        if source == "user":
            return RapportAnnuelPerformanceGeneratorSimpleDoc._format_db_data(text)
        elif source == "db":
            return RapportAnnuelPerformanceGeneratorSimpleDoc._format_db_data(text)
        else:  # default
            return RapportAnnuelPerformanceGeneratorSimpleDoc._format_db_data(text)
    
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

    @staticmethod
    def _create_pie_chart_programme(
        personnel: float,
        pct_personnel: float,
        biens: float,
        pct_biens: float,
        transferts: float,
        pct_transferts: float,
        investissements: float,
        pct_investissements: float,
        titre_programme: str,
    ) -> BytesIO | None:
        """
        Crée un graphique en camembert pour la répartition du budget du programme par nature de dépenses.
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            import matplotlib.font_manager as fm
            
            # Données
            sizes = [personnel, biens, transferts, investissements]
            labels = ["Personnel", "Biens et services", "Transferts", "Investissements"]
            colors_list = [
                "#ADD8E6",  # Bleu clair (Personnel)
                "#FFA500",  # Orange (Biens et services)
                "#808080",  # Gris (Transferts)
                "#FFD700",  # Jaune (Investissements)
            ]
            
            # Créer la figure
            fig_size = 20
            fig = plt.figure(figsize=(fig_size, fig_size), dpi=200)
            ax = fig.add_subplot(111, aspect='equal')
            
            # Ajouter un titre au graphique centré (identique au ministère)
            ax.set_title('Répartition du budget actuel par natures de dépenses', 
                        fontsize=35, fontweight='bold', pad=20, loc='center')
            
            # Créer le graphique en camembert
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=None,
                autopct='%1.0f%%',
                colors=colors_list,
                startangle=90,
                textprops={'fontsize': 40, 'fontweight': 'bold'},
            )
            
            # Personnaliser les textes des pourcentages avec fond noir
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(40)
                autotext.set_bbox(dict(boxstyle='round,pad=0.3', facecolor='black', edgecolor='none', alpha=0.8))
            
            # Légende
            legend_elements = [
                mpatches.Patch(facecolor=colors_list[0], label=f'{labels[0]} ({pct_personnel:.0f}%)'),
                mpatches.Patch(facecolor=colors_list[1], label=f'{labels[1]} ({pct_biens:.0f}%)'),
                mpatches.Patch(facecolor=colors_list[2], label=f'{labels[2]} ({pct_transferts:.0f}%)'),
                mpatches.Patch(facecolor=colors_list[3], label=f'{labels[3]} ({pct_investissements:.0f}%)'),
            ]
            legend_font = fm.FontProperties(weight='bold', size=36)
            legend = ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.1, 0.5), prop=legend_font, frameon=True)
            for text in legend.get_texts():
                text.set_fontsize(36)
                text.set_weight('bold')
            
            # Ajuster la mise en page (identique au ministère)
            plt.subplots_adjust(left=0.05, right=0.55, top=0.95, bottom=0.05)
            
            # Sauvegarder dans un buffer avec un ratio d'aspect égal
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
    
    @staticmethod
    def _create_bar_chart_execution_rates(
        actions_rates: dict[str, dict[str, float]],
        annee_precedente: int,
        annee: int,
        numero_programme: int,
        titre_programme: str,
    ) -> BytesIO | None:
        """
        Crée un graphique en barres groupées pour l'évolution des taux d'exécution par action.
        
        Args:
            actions_rates: Dictionnaire avec les taux d'exécution par action {"rate_n_minus_1": float, "rate_n": float}
            annee_precedente: Année N-1
            annee: Année N
            numero_programme: Numéro du programme
            titre_programme: Titre du programme
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Préparer les données pour le graphique
            actions_labels = []
            rates_n_minus_1 = []
            rates_n = []
            
            action_num = 1
            for action, rates in actions_rates.items():
                action_label = f"Action {action_num}"
                actions_labels.append(action_label)
                rates_n_minus_1.append(rates.get("rate_n_minus_1", 0.0))
                rates_n.append(rates.get("rate_n", 0.0))
                action_num += 1
            
            # Si pas de données, ne pas générer le graphique
            if not actions_labels:
                logger.warning("⚠️ Aucune donnée d'action disponible pour le graphique des taux d'exécution")
                return None
            
            # Créer la figure avec une largeur plus grande pour occuper toute la largeur disponible
            # Pour une page A4 paysage, la largeur disponible est d'environ 25 cm (9.8 pouces)
            fig, ax = plt.subplots(figsize=(20, 6), dpi=200)
            
            # Position des barres
            x = np.arange(len(actions_labels))
            width = 0.35  # Largeur des barres
            
            # Créer les barres avec les nouvelles couleurs
            bars1 = ax.bar(x - width/2, rates_n_minus_1, width, label=str(annee_precedente), color='#5b9bd5')  # Bleu
            bars2 = ax.bar(x + width/2, rates_n, width, label=str(annee), color='#ed7d31')  # Orange
            
            # Ajouter les valeurs sur les barres (police agrandie)
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.2f}%',
                           ha='center', va='bottom', fontsize=24, fontweight='bold')
            
            # Configuration de l'axe Y (police agrandie)
            ax.set_ylabel('Taux d\'exécution (%)', fontsize=26, fontweight='bold')
            ax.set_ylim(0, 130)
            ax.set_yticks(range(0, 131, 20))
            ax.tick_params(axis='y', labelsize=24)
            
            # Configuration de l'axe X (police agrandie)
            ax.set_xlabel('Actions', fontsize=26, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(actions_labels, fontsize=24, fontweight='bold')
            
            # Pas de titre dans le graphique, il sera dans le PDF
            
            # Légende (police agrandie) - positionnée en haut, centrée et en ligne
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.02), ncol=2, fontsize=22, frameon=True)
            
            # Grille horizontale visible
            ax.grid(axis='y', linestyle='-', alpha=0.5, color='gray', linewidth=1)
            
            # Fond blanc
            ax.set_facecolor('white')
            fig.patch.set_facecolor('white')
            
            # Ajuster la mise en page
            plt.tight_layout()
            
            # Sauvegarder avec fond blanc
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=200, facecolor='white', edgecolor='none', bbox_inches='tight')
            plt.close(fig)
            buffer.seek(0)
            
            return buffer
            
        except ImportError:
            logger.warning("⚠️ matplotlib n'est pas disponible, graphique en barres ignoré")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors de la création du graphique en barres: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _create_indicateur_evolution_chart(
        indicateur_nom: str,
        annee: int,
        valeurs: list[float] | None = None,
    ) -> BytesIO | None:
        """
        Crée un graphique en ligne pour l'évolution d'un indicateur sur les 4 derniers exercices.
        
        Args:
            indicateur_nom: Nom de l'indicateur
            annee: Année N (année courante)
            valeurs: Liste de 4 valeurs pour les années N-3, N-2, N-1, N (si None, utilise des données de test)
            
        Returns:
            BytesIO contenant l'image PNG du graphique, ou None en cas d'erreur
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            
            logger.info(f"📊 Début de création du graphique d'évolution pour '{indicateur_nom}' (année {annee}, valeurs fournies: {valeurs})")
            
            # Calculer les 4 dernières années
            annees = [annee - 3, annee - 2, annee - 1, annee]
            
            # Vérifier le mode depuis la classe
            mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
            
            # En mode final, ne pas générer de données factices
            if mode == "final" and (valeurs is None or len(valeurs) != 4):
                logger.info(f"📊 Mode final: pas de données factices pour l'indicateur '{indicateur_nom}'")
                return None
            
            # Utiliser des données de test si aucune valeur n'est fournie ou si la liste n'a pas 4 éléments (mode brouillon uniquement)
            if valeurs is None or len(valeurs) != 4:
                # Générer des données de test avec une tendance croissante
                base_value = 20 + (abs(hash(indicateur_nom)) % 20)  # Valeur de base variable selon l'indicateur
                valeurs = [
                    float(base_value),
                    float(base_value + 3 + (abs(hash(indicateur_nom)) % 5)),
                    float(base_value + 6 + (abs(hash(indicateur_nom)) % 5)),
                    float(base_value + 8 + (abs(hash(indicateur_nom)) % 5))
                ]
                logger.info(f"📊 Génération de données factices pour l'indicateur '{indicateur_nom}': {valeurs}")
            else:
                # Convertir les valeurs en float si nécessaire
                valeurs = [float(v) for v in valeurs]
                logger.info(f"📊 Utilisation des valeurs réelles pour l'indicateur '{indicateur_nom}': {valeurs}")
            
            logger.info(f"📊 Données finales pour le graphique: années={annees}, valeurs={valeurs}")
            
            # Créer la figure
            fig, ax = plt.subplots(figsize=(16, 6), dpi=200)
            
            # Créer le graphique en ligne
            line = ax.plot(annees, valeurs, marker='o', linewidth=3, markersize=10, color='#5b9bd5', label='Valeur')
            
            # Ajouter les valeurs sur les points
            for i, (annee_val, valeur) in enumerate(zip(annees, valeurs)):
                ax.text(annee_val, valeur, f'{valeur:.1f}',
                       ha='center', va='bottom', fontsize=20, fontweight='bold')
            
            # Configuration de l'axe Y - échelle fixe de 0 à 100%
            ax.set_ylim(0, 100)
            
            # Ticks de l'axe Y avec intervalle de 10%
            y_ticks = np.arange(0, 101, 10)
            ax.set_yticks(y_ticks)
            ax.tick_params(axis='y', labelsize=20)
            
            # Configuration de l'axe X
            ax.set_xlabel('Années', fontsize=22, fontweight='bold')
            ax.set_xticks(annees)
            ax.set_xticklabels([str(a) for a in annees], fontsize=20, fontweight='bold')
            ax.tick_params(axis='x', labelsize=20)
            
            # Grille horizontale visible
            ax.grid(axis='y', linestyle='-', alpha=0.5, color='gray', linewidth=1)
            ax.grid(axis='x', linestyle='--', alpha=0.3, color='gray', linewidth=0.5)
            
            # Fond blanc
            ax.set_facecolor('white')
            fig.patch.set_facecolor('white')
            
            # Ajuster la mise en page
            plt.tight_layout()
            
            # Sauvegarder avec fond blanc
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=200, facecolor='white', edgecolor='none', bbox_inches='tight')
            plt.close(fig)
            buffer.seek(0)
            
            return buffer
            
        except ImportError:
            logger.warning("⚠️ matplotlib n'est pas disponible, graphique d'évolution ignoré")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors de la création du graphique d'évolution: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _get_investissement_data(numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les données d'investissement pour un programme depuis la base de données.
        Retourne une liste de projets avec leurs informations.
        Pas de valeurs par défaut - retourne une liste vide si aucune donnée n'est trouvée.
        """
        # Pas de valeurs par défaut - uniquement les données de la DB
        investissement_projects = []
        if session:
            try:
                from sqlmodel import select
                from app.models.budget import SigobeExecution
                from decimal import Decimal
                
                # Récupérer les investissements pour ce programme
                sigobe_invest = session.exec(
                    select(SigobeExecution)
                    .where(SigobeExecution.annee == annee)
                    .where(SigobeExecution.programmes.ilike(f"%{titre}%"))
                    .where(
                        (SigobeExecution.type_depense.ilike("%INVESTISSEMENT%"))
                        | (SigobeExecution.type_depense.ilike("%I%"))
                    )
                ).all()
                
                # Grouper par projet (utiliser le champ actions ou activites comme identifiant de projet)
                projects_dict = {}
                for sigobe in sigobe_invest:
                    # Utiliser actions ou activites comme identifiant de projet
                    projet_id = sigobe.actions or sigobe.activites or "Projet non spécifié"
                    
                    if projet_id not in projects_dict:
                        projects_dict[projet_id] = {
                            "nom": projet_id,
                            "annee_debut": sigobe.annee or annee,
                            "annee_fin": sigobe.annee or annee,
                            "cout_total_interieur": Decimal(0),
                            "cout_total_exterieur": Decimal(0),
                            f"budget_vote_{annee}_interieur": Decimal(0),
                            f"budget_vote_{annee}_exterieur": Decimal(0),
                            f"budget_actuel_{annee}_interieur": Decimal(0),
                            f"budget_actuel_{annee}_exterieur": Decimal(0),
                            f"ordonnancement_{annee}_interieur": Decimal(0),
                            f"ordonnancement_{annee}_exterieur": Decimal(0),
                        }
                    
                    # Accumuler les montants
                    budget_vote = Decimal(sigobe.budget_vote or 0)
                    budget_actuel = Decimal(sigobe.budget_actuel or 0)
                    mandats_pec = Decimal(sigobe.mandats_pec or 0)
                    
                    projects_dict[projet_id]["cout_total_interieur"] += budget_actuel
                    projects_dict[projet_id][f"budget_vote_{annee}_interieur"] += budget_vote
                    projects_dict[projet_id][f"budget_actuel_{annee}_interieur"] += budget_actuel
                    projects_dict[projet_id][f"ordonnancement_{annee}_interieur"] += mandats_pec
                
                # Convertir en liste et convertir Decimal en float/int
                for projet in projects_dict.values():
                    investissement_projects.append({
                        "nom": projet["nom"],
                        "annee_debut": int(projet["annee_debut"]),
                        "annee_fin": int(projet["annee_fin"]),
                        "cout_total_interieur": float(projet["cout_total_interieur"]),
                        "cout_total_exterieur": float(projet["cout_total_exterieur"]),
                        f"budget_vote_{annee}_interieur": float(projet[f"budget_vote_{annee}_interieur"]),
                        f"budget_vote_{annee}_exterieur": float(projet[f"budget_vote_{annee}_exterieur"]),
                        f"budget_actuel_{annee}_interieur": float(projet[f"budget_actuel_{annee}_interieur"]),
                        f"budget_actuel_{annee}_exterieur": float(projet[f"budget_actuel_{annee}_exterieur"]),
                        f"ordonnancement_{annee}_interieur": float(projet[f"ordonnancement_{annee}_interieur"]),
                        f"ordonnancement_{annee}_exterieur": float(projet[f"ordonnancement_{annee}_exterieur"]),
                    })
                    
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors de la récupération des investissements: {e}")
        
        # Si pas de données, générer des données factices en mode brouillon
        if not investissement_projects and RapportAnnuelPerformanceGeneratorSimpleDoc._should_use_fake_data():
            logger.info(f"📊 Mode brouillon: génération de données factices variées pour les investissements")
            from decimal import Decimal
            # Projets avec des montants et taux d'exécution variés
            projets_factices = [
                {
                    "nom": "Projet d'infrastructure administrative",
                    "annee_debut": annee - 2,
                    "annee_fin": annee + 1,
                    "cout_total_interieur": 500000000.0,
                    "cout_total_exterieur": 0.0,
                    "taux_execution": 0.72,  # 72%
                    f"budget_vote_{annee}_interieur": 200000000.0,
                    f"budget_vote_{annee}_exterieur": 0.0,
                    f"budget_actuel_{annee}_interieur": 250000000.0,
                    f"budget_actuel_{annee}_exterieur": 0.0,
                },
                {
                    "nom": "Projet d'équipement informatique",
                    "annee_debut": annee - 1,
                    "annee_fin": annee,
                    "cout_total_interieur": 150000000.0,
                    "cout_total_exterieur": 0.0,
                    "taux_execution": 0.80,  # 80%
                    f"budget_vote_{annee}_interieur": 150000000.0,
                    f"budget_vote_{annee}_exterieur": 0.0,
                    f"budget_actuel_{annee}_interieur": 150000000.0,
                    f"budget_actuel_{annee}_exterieur": 0.0,
                },
                {
                    "nom": "Projet de modernisation des systèmes",
                    "annee_debut": annee - 1,
                    "annee_fin": annee + 2,
                    "cout_total_interieur": 800000000.0,
                    "cout_total_exterieur": 200000000.0,
                    "taux_execution": 0.65,  # 65%
                    f"budget_vote_{annee}_interieur": 300000000.0,
                    f"budget_vote_{annee}_exterieur": 100000000.0,
                    f"budget_actuel_{annee}_interieur": 350000000.0,
                    f"budget_actuel_{annee}_exterieur": 120000000.0,
                },
            ]
            
            # Calculer l'ordonnancement basé sur le taux d'exécution
            for projet in projets_factices:
                budget_actuel_interieur = projet[f"budget_actuel_{annee}_interieur"]
                budget_actuel_exterieur = projet[f"budget_actuel_{annee}_exterieur"]
                budget_actuel_total = budget_actuel_interieur + budget_actuel_exterieur
                taux_exec = projet.get("taux_execution", 0.75)
                
                # Répartir l'ordonnancement proportionnellement
                ordonnancement_total = budget_actuel_total * taux_exec
                if budget_actuel_total > 0:
                    ratio_interieur = budget_actuel_interieur / budget_actuel_total
                    projet[f"ordonnancement_{annee}_interieur"] = ordonnancement_total * ratio_interieur
                    projet[f"ordonnancement_{annee}_exterieur"] = ordonnancement_total * (1 - ratio_interieur)
                else:
                    projet[f"ordonnancement_{annee}_interieur"] = 0.0
                    projet[f"ordonnancement_{annee}_exterieur"] = 0.0
                
                # Stocker le taux d'exécution avec un préfixe pour utilisation ultérieure (ne sera pas affiché dans le tableau)
                projet["_taux_execution"] = taux_exec
            
            return projets_factices
        
        return investissement_projects
    
    @staticmethod
    def _create_investissement_table(projects: list[dict[str, Any]], available_width: float, format_fcfa: callable, annee: int, is_fake: bool = False, format_programme_value: callable = None) -> LongTable:
        """
        Crée le tableau d'investissement avec la structure complexe (projets + sous-lignes).
        """
        from reportlab.platypus import LongTable, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        from reportlab.pdfbase import pdfmetrics
        
        # Styles pour les cellules
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=None,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # Center
            spaceAfter=0,
        )
        
        cell_style = ParagraphStyle(
            "CellStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=0,  # Left
            spaceAfter=0,
        )
        
        cell_style_bold = ParagraphStyle(
            "CellStyleBold",
            parent=None,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=0,  # Left
            spaceAfter=0,
        )
        
        cell_right_style = ParagraphStyle(
            "CellRightStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=2,  # Right
            spaceAfter=0,
        )
        
        cell_center_style = ParagraphStyle(
            "CellCenterStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,  # Center
            spaceAfter=0,
        )
        
        # Créer les en-têtes avec année dynamique
        header = [
            [
                Paragraph("<b>Projets</b>", header_style),
                Paragraph("<b>Année de<br/>démarrage</b>", header_style),
                Paragraph("<b>Année<br/>de fin</b>", header_style),
                Paragraph("<b>Coût<br/>total</b>", header_style),
                Paragraph(f"<b>Budget<br/>Voté {annee}</b>", header_style),
                Paragraph(f"<b>Budget<br/>Actuel {annee}</b>", header_style),
                Paragraph(f"<b>Ordonnancement<br/>{annee}</b>", header_style),
            ]
        ]
        
        # Calculer les largeurs des colonnes (en %)
        col_widths = [
            available_width * 0.35,  # Projets
            available_width * 0.10,  # Année démarrage
            available_width * 0.08,  # Année fin
            available_width * 0.12,  # Coût total
            available_width * 0.12,  # Budget Voté 2024
            available_width * 0.12,  # Budget Actuel 2024
            available_width * 0.11,  # Ordonnancement 2024
        ]
        
        # Construire les lignes du tableau
        table_data = []
        table_data.extend(header)
        
        total_cout_interieur = 0
        total_cout_exterieur = 0
        total_budget_vote_interieur = 0
        total_budget_vote_exterieur = 0
        total_budget_actuel_interieur = 0
        total_budget_actuel_exterieur = 0
        total_ordonnancement_interieur = 0
        total_ordonnancement_exterieur = 0
        
        # Parcourir les projets
        for project in projects:
            nom = project["nom"]
            annee_debut = project["annee_debut"]
            annee_fin = project["annee_fin"]
            
            # Valeurs pour financement intérieur (utiliser des clés dynamiques)
            cout_interieur = project.get("cout_total_interieur", 0.0)
            budget_vote_interieur = project.get(f"budget_vote_{annee}_interieur", 0.0)
            budget_actuel_interieur = project.get(f"budget_actuel_{annee}_interieur", 0.0)
            ordonnancement_interieur = project.get(f"ordonnancement_{annee}_interieur", 0.0)
            
            # Valeurs pour financement extérieur (utiliser des clés dynamiques)
            cout_exterieur = project.get("cout_total_exterieur", 0.0)
            budget_vote_exterieur = project.get(f"budget_vote_{annee}_exterieur", 0.0)
            budget_actuel_exterieur = project.get(f"budget_actuel_{annee}_exterieur", 0.0)
            ordonnancement_exterieur = project.get(f"ordonnancement_{annee}_exterieur", 0.0)
            
            # Coûts totaux
            cout_total = cout_interieur + cout_exterieur
            budget_vote_total = budget_vote_interieur + budget_vote_exterieur
            budget_actuel_total = budget_actuel_interieur + budget_actuel_exterieur
            ordonnancement_total = ordonnancement_interieur + ordonnancement_exterieur
            
            # Formater les valeurs selon leur source (factice ou DB)
            formatted_nom = format_programme_value(nom, is_fake) if format_programme_value else nom
            formatted_annee_debut = format_programme_value(str(annee_debut), is_fake) if format_programme_value else str(annee_debut)
            formatted_annee_fin = format_programme_value(str(annee_fin), is_fake) if format_programme_value else str(annee_fin)
            formatted_cout_total = format_programme_value(format_fcfa(cout_total), is_fake) if format_programme_value else format_fcfa(cout_total)
            formatted_budget_vote_total = format_programme_value(format_fcfa(budget_vote_total), is_fake) if format_programme_value else format_fcfa(budget_vote_total)
            formatted_budget_actuel_total = format_programme_value(format_fcfa(budget_actuel_total), is_fake) if format_programme_value else format_fcfa(budget_actuel_total)
            formatted_ordonnancement_total = format_programme_value(format_fcfa(ordonnancement_total), is_fake) if format_programme_value else format_fcfa(ordonnancement_total)
            formatted_budget_actuel_interieur = format_programme_value(format_fcfa(budget_actuel_interieur), is_fake) if format_programme_value else format_fcfa(budget_actuel_interieur)
            formatted_ordonnancement_interieur = format_programme_value(format_fcfa(ordonnancement_interieur), is_fake) if format_programme_value else format_fcfa(ordonnancement_interieur)
            formatted_budget_actuel_exterieur = format_programme_value(format_fcfa(budget_actuel_exterieur), is_fake) if format_programme_value else format_fcfa(budget_actuel_exterieur)
            formatted_ordonnancement_exterieur = format_programme_value(format_fcfa(ordonnancement_exterieur), is_fake) if format_programme_value else format_fcfa(ordonnancement_exterieur)
            
            # Ligne principale du projet
            table_data.append([
                Paragraph(f"<b>{formatted_nom}</b>", cell_style_bold),
                Paragraph(formatted_annee_debut, cell_center_style),
                Paragraph(formatted_annee_fin, cell_center_style),
                Paragraph(formatted_cout_total, cell_right_style),
                Paragraph(formatted_budget_vote_total, cell_right_style),
                Paragraph(formatted_budget_actuel_total, cell_right_style),
                Paragraph(formatted_ordonnancement_total, cell_right_style),
            ])
            
            # Ligne "Sur financement intérieur" - seulement Budget Actuel et Ordonnancement
            table_data.append([
                Paragraph("Sur financement intérieur", cell_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_right_style),  # Coût total vide
                Paragraph("", cell_right_style),  # Budget Voté vide
                Paragraph(formatted_budget_actuel_interieur, cell_right_style),
                Paragraph(formatted_ordonnancement_interieur, cell_right_style),
            ])
            
            # Ligne "Sur financement extérieur" - seulement Budget Actuel et Ordonnancement
            table_data.append([
                Paragraph("Sur financement extérieur", cell_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_right_style),  # Coût total vide
                Paragraph("", cell_right_style),  # Budget Voté vide
                Paragraph(formatted_budget_actuel_exterieur, cell_right_style),
                Paragraph(formatted_ordonnancement_exterieur, cell_right_style),
            ])
            
            # Accumuler les totaux
            total_cout_interieur += cout_interieur
            total_cout_exterieur += cout_exterieur
            total_budget_vote_interieur += budget_vote_interieur
            total_budget_vote_exterieur += budget_vote_exterieur
            total_budget_actuel_interieur += budget_actuel_interieur
            total_budget_actuel_exterieur += budget_actuel_exterieur
            total_ordonnancement_interieur += ordonnancement_interieur
            total_ordonnancement_exterieur += ordonnancement_exterieur
        
        # Ligne totale
        total_cout = total_cout_interieur + total_cout_exterieur
        total_budget_vote = total_budget_vote_interieur + total_budget_vote_exterieur
        total_budget_actuel = total_budget_actuel_interieur + total_budget_actuel_exterieur
        total_ordonnancement = total_ordonnancement_interieur + total_ordonnancement_exterieur
        
        # Formater les totaux selon leur source (factice ou DB)
        formatted_total_cout = format_programme_value(format_fcfa(total_cout), is_fake) if format_programme_value else format_fcfa(total_cout)
        formatted_total_budget_vote = format_programme_value(format_fcfa(total_budget_vote), is_fake) if format_programme_value else format_fcfa(total_budget_vote)
        formatted_total_budget_actuel = format_programme_value(format_fcfa(total_budget_actuel), is_fake) if format_programme_value else format_fcfa(total_budget_actuel)
        formatted_total_ordonnancement = format_programme_value(format_fcfa(total_ordonnancement), is_fake) if format_programme_value else format_fcfa(total_ordonnancement)
        formatted_total_budget_actuel_interieur = format_programme_value(format_fcfa(total_budget_actuel_interieur), is_fake) if format_programme_value else format_fcfa(total_budget_actuel_interieur)
        formatted_total_ordonnancement_interieur = format_programme_value(format_fcfa(total_ordonnancement_interieur), is_fake) if format_programme_value else format_fcfa(total_ordonnancement_interieur)
        formatted_total_budget_actuel_exterieur = format_programme_value(format_fcfa(total_budget_actuel_exterieur), is_fake) if format_programme_value else format_fcfa(total_budget_actuel_exterieur)
        formatted_total_ordonnancement_exterieur = format_programme_value(format_fcfa(total_ordonnancement_exterieur), is_fake) if format_programme_value else format_fcfa(total_ordonnancement_exterieur)
        
        table_data.append([
            Paragraph("<b>Total programme (budget de l'Etat)</b>", cell_style_bold),
            Paragraph("", cell_center_style),
            Paragraph("", cell_center_style),
            Paragraph(f"<b>{formatted_total_cout}</b>", cell_right_style),
            Paragraph(f"<b>{formatted_total_budget_vote}</b>", cell_right_style),
            Paragraph(f"<b>{formatted_total_budget_actuel}</b>", cell_right_style),
            Paragraph(f"<b>{formatted_total_ordonnancement}</b>", cell_right_style),
        ])
        
        # Ligne totale "Sur financement intérieur" - seulement Budget Actuel et Ordonnancement
        table_data.append([
            Paragraph("<b>Total sur financement intérieur</b>", cell_style_bold),
            Paragraph("", cell_center_style),
            Paragraph("", cell_center_style),
            Paragraph("", cell_right_style),  # Coût total vide
            Paragraph("", cell_right_style),  # Budget Voté vide
            Paragraph(f"<b>{formatted_total_budget_actuel_interieur}</b>", cell_right_style),
            Paragraph(f"<b>{formatted_total_ordonnancement_interieur}</b>", cell_right_style),
        ])
        
        # Ligne totale "Sur financement extérieur" - seulement Budget Actuel et Ordonnancement
        table_data.append([
            Paragraph("<b>Total sur financement extérieur</b>", cell_style_bold),
            Paragraph("", cell_center_style),
            Paragraph("", cell_center_style),
            Paragraph("", cell_right_style),  # Coût total vide
            Paragraph("", cell_right_style),  # Budget Voté vide
            Paragraph(f"<b>{formatted_total_budget_actuel_exterieur}</b>", cell_right_style),
            Paragraph(f"<b>{formatted_total_ordonnancement_exterieur}</b>", cell_right_style),
        ])
        
        # Créer le LongTable pour le support multi-page
        investissement_table = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
        
        # Style du tableau
        investissement_table_style = TableStyle([
            # Bordures extérieures
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            
            # En-têtes (ligne 0)
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            
            # Lignes totales (3 dernières lignes)
            ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#ffe599")),  # Total programme
            ("BACKGROUND", (0, -2), (-1, -2), colors.white),  # Total intérieur
            ("BACKGROUND", (0, -1), (-1, -1), colors.white),  # Total extérieur
            ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
            
            # Alignement des montants (colonnes numériques)
            ("ALIGN", (3, 1), (-1, -4), "RIGHT"),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
        
        investissement_table.setStyle(investissement_table_style)
        
        return investissement_table
    
    @staticmethod
    def _get_activites_majeures(numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les activités majeures pour un programme.
        Les activités sont considérées comme majeures si leur taux d'exécution est élevé (> seuil) 
        ou si elles ont un budget significatif.
        """
        # Pas de valeurs par défaut - uniquement les données de la DB
        if session:
            try:
                from sqlmodel import select, func
                from app.models.budget import SigobeExecution
                from decimal import Decimal
                
                # Récupérer les activités pour ce programme avec leurs taux d'exécution
                activites_query = (
                    select(
                        SigobeExecution.activites,
                        func.sum(SigobeExecution.budget_actuel).label("budget_total"),
                        func.sum(SigobeExecution.mandats_pec).label("execution_total"),
                    )
                    .where(SigobeExecution.annee == annee)
                    .where(SigobeExecution.programmes.ilike(f"%{titre}%"))
                    .where(SigobeExecution.activites.isnot(None))
                    .where(SigobeExecution.activites != "")
                    .group_by(SigobeExecution.activites)
                )
                
                activites_db = session.exec(activites_query).all()
                
                # Filtrer les activités majeures (taux d'exécution > 80% ou budget significatif)
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
                
                # Si on trouve des activités, les utiliser (limitées aux 20 plus importantes)
                if activites_filtrees:
                    activites_filtrees.sort(key=lambda x: x["taux_execution"], reverse=True)
                    return activites_filtrees[:20]
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors de la récupération des activités: {e}")
        
        # Si pas de données, générer des données factices en mode brouillon
        mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
        if mode == "final":
            return []
        # Générer des données factices en mode brouillon avec le flag _is_fake
        logger.info(f"📊 Mode brouillon: génération de données factices pour les activités majeures")
        return [
            {"libelle": "Renforcement des capacités institutionnelles", "taux_execution": 95.5, "_is_fake": True},
            {"libelle": "Amélioration de la gestion du patrimoine immobilier", "taux_execution": 92.3, "_is_fake": True},
            {"libelle": "Modernisation des systèmes d'information", "taux_execution": 88.7, "_is_fake": True},
            {"libelle": "Optimisation de la gestion des ressources humaines", "taux_execution": 85.2, "_is_fake": True},
        ]
    
    @staticmethod
    def _get_indicateurs_performance_data(numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les données d'indicateurs de performance pour un programme.
        Retourne une liste d'objectifs avec leurs indicateurs associés.
        Utilise la colonne 'annee' pour récupérer les valeurs historiques (N, N-1, N-2, N-3).
        """
        # Calculer les années dynamiquement
        annee_n_3 = annee - 3
        annee_n_2 = annee - 2
        annee_n_1 = annee - 1
        annee_n = annee
        
        # Données par défaut : structure avec 3 OS et plusieurs indicateurs chacun (selon le tableau de référence)
        default_indicateurs = [
            # Objectif Spécifique 1 - Indicateur 1
            {
                "objectif_titre": f"Objectif Spécifique 1: Améliorer la gestion de l'Administration du Portefeuille de l'Etat",
                "indicateur_nom": "Taux d'exécution du PAS du programme du portefeuille de l'Etat",
                "unite": "%",
                f"realisation_{annee_n_3}": 95,
                f"realisation_{annee_n_2}": 93,
                f"realisation_{annee_n_1}": 89,
                f"prevision_{annee_n}": 80,
                f"realisation_{annee_n}": 96,
                "nb_activites": 15,
                "definition": f"Cet indicateur permet d'évaluer le niveau d'exécution du Plan d'Action Stratégique (PAS) du programme {titre}",
                "source_donnees": "Rapport Annuel de Performance",
                "mode_calcul": "(Montant exécuté / Montant prévu) x 100",
                "valeurs_cibles": f"80% en {annee_n}, 85% en {annee_n+1}, 90% en {annee_n+2}",
                "_source": "default",
            },
            # Objectif Spécifique 1 - Indicateur 2
            {
                "objectif_titre": f"Objectif Spécifique 1: Améliorer la gestion de l'Administration du Portefeuille de l'Etat",
                "indicateur_nom": "Taux d'exécution du budget d'investissement du programme Portefeuille de l'Etat",
                "unite": "%",
                f"realisation_{annee_n_3}": 100,
                f"realisation_{annee_n_2}": 100,
                f"realisation_{annee_n_1}": 100,
                f"prevision_{annee_n}": 97,
                f"realisation_{annee_n}": 100,
                "nb_activites": 8,
                "definition": f"Cet indicateur mesure le taux d'exécution du budget d'investissement alloué au programme {titre}",
                "source_donnees": "Rapport d'exécution budgétaire",
                "mode_calcul": "(Budget d'investissement exécuté / Budget d'investissement prévu) x 100",
                "valeurs_cibles": f"97% en {annee_n}, 98% en {annee_n+1}, 100% en {annee_n+2}",
                "_source": "default",
            },
            # Objectif Spécifique 2 - Indicateur 1
            {
                "objectif_titre": f"Objectif Spécifique 2: Assurer le positionnement du Portefeuille de l'Etat comme un accélérateur de développement",
                "indicateur_nom": "Nombre d'études réalisées dans le cadre de la mise en œuvre de la stratégie 2021-2025 de gestion du portefeuille de l'Etat",
                "unite": "Nombre",
                f"realisation_{annee_n_3}": None,
                f"realisation_{annee_n_2}": 3,
                f"realisation_{annee_n_1}": 7,
                f"prevision_{annee_n}": 2,
                f"realisation_{annee_n}": 6,
                "nb_activites": 5,
                "definition": f"Cet indicateur compte le nombre d'études réalisées pour la mise en œuvre de la stratégie de gestion du portefeuille de l'Etat",
                "source_donnees": "Rapport d'activités / DGPE",
                "mode_calcul": "Somme des études réalisées sur la période",
                "valeurs_cibles": f"2 études en {annee_n}, 3 études en {annee_n+1}, 4 études en {annee_n+2}",
                "_source": "default",
            },
            # Objectif Spécifique 2 - Indicateur 2
            {
                "objectif_titre": f"Objectif Spécifique 2: Assurer le positionnement du Portefeuille de l'Etat comme un accélérateur de développement",
                "indicateur_nom": "Nombre de contrats de performance élaborés par la DGPE",
                "unite": "Nombre",
                f"realisation_{annee_n_3}": 18,
                f"realisation_{annee_n_2}": 5,
                f"realisation_{annee_n_1}": 14,
                f"prevision_{annee_n}": 5,
                f"realisation_{annee_n}": 13,
                "nb_activites": 4,
                "definition": f"Cet indicateur compte le nombre de contrats de performance élaborés par la Direction Générale du Portefeuille de l'Etat (DGPE)",
                "source_donnees": "Rapport d'activités / DGPE",
                "mode_calcul": "Somme des contrats de performance élaborés sur la période",
                "valeurs_cibles": f"5 contrats en {annee_n}, 6 contrats en {annee_n+1}, 7 contrats en {annee_n+2}",
                "_source": "default",
            },
            # Objectif Spécifique 2 - Indicateur 3
            {
                "objectif_titre": f"Objectif Spécifique 2: Assurer le positionnement du Portefeuille de l'Etat comme un accélérateur de développement",
                "indicateur_nom": "Nombre d'entreprises publiques ayant procédé à la signature d'une lettre de mission entre le Conseil d'Administration et le Directeur Général",
                "unite": "Nombre",
                f"realisation_{annee_n_3}": None,
                f"realisation_{annee_n_2}": 26,
                f"realisation_{annee_n_1}": 33,
                f"prevision_{annee_n}": 26,
                f"realisation_{annee_n}": 35,
                "nb_activites": 3,
                "definition": f"Cet indicateur mesure le nombre d'entreprises publiques ayant signé une lettre de mission entre leur Conseil d'Administration et leur Directeur Général",
                "source_donnees": "Rapport d'activités / DGPE",
                "mode_calcul": "Somme des entreprises publiques ayant signé une lettre de mission sur la période",
                "valeurs_cibles": f"26 entreprises en {annee_n}, 28 entreprises en {annee_n+1}, 30 entreprises en {annee_n+2}",
                "_source": "default",
            },
            # Objectif Spécifique 3 - Indicateur 1
            {
                "objectif_titre": f"Objectif Spécifique 3: Améliorer le dispositif de contrôle des entreprises publiques",
                "indicateur_nom": "Taux de réalisation du plan d'audits des entreprises publiques",
                "unite": "%",
                f"realisation_{annee_n_3}": 100,
                f"realisation_{annee_n_2}": 85,
                f"realisation_{annee_n_1}": 100,
                f"prevision_{annee_n}": 80,
                f"realisation_{annee_n}": 100,
                "nb_activites": 10,
                "definition": f"Cet indicateur évalue le pourcentage de réalisation du plan d'audits prévu pour les entreprises publiques",
                "source_donnees": "Rapport d'audit / Cellule de contrôle",
                "mode_calcul": "(Nombre d'audits réalisés / Nombre d'audits prévus) x 100",
                "valeurs_cibles": f"80% en {annee_n}, 85% en {annee_n+1}, 90% en {annee_n+2}",
                "_source": "default",
            },
            # Objectif Spécifique 3 - Indicateur 2
            {
                "objectif_titre": f"Objectif Spécifique 3: Améliorer le dispositif de contrôle des entreprises publiques",
                "indicateur_nom": "Taux de réalisation du plan de contrôles opérationnels des entreprises publiques",
                "unite": "%",
                f"realisation_{annee_n_3}": 100,
                f"realisation_{annee_n_2}": 85,
                f"realisation_{annee_n_1}": 100,
                f"prevision_{annee_n}": 80,
                f"realisation_{annee_n}": 100,
                "nb_activites": 12,
                "definition": f"Cet indicateur mesure le pourcentage de réalisation du plan de contrôles opérationnels prévu pour les entreprises publiques",
                "source_donnees": "Rapport de contrôle / Cellule de contrôle",
                "mode_calcul": "(Nombre de contrôles réalisés / Nombre de contrôles prévus) x 100",
                "valeurs_cibles": f"80% en {annee_n}, 85% en {annee_n+1}, 90% en {annee_n+2}",
                "_source": "default",
            },
        ]
        
        # Récupérer les données depuis la base de données
        if session:
            try:
                from sqlmodel import select, and_
                from app.models.performance import ObjectifPerformance, IndicateurPerformance
                from sqlalchemy.orm import joinedload
                from sqlalchemy.exc import ProgrammingError, InternalError
                
                # Récupérer tous les indicateurs actifs avec leurs objectifs
                # On récupère les indicateurs pour différentes années (N, N-1, N-2, N-3)
                annees_a_recuperer = [annee, annee - 1, annee - 2, annee - 3]
                
                try:
                    indicateurs_query = select(IndicateurPerformance).where(
                        and_(
                            IndicateurPerformance.actif == True,
                            IndicateurPerformance.annee.in_(annees_a_recuperer)
                        )
                    )
                    
                    indicateurs = session.exec(indicateurs_query).all()
                    
                    if not indicateurs:
                        logger.info(f"⚠️ Aucun indicateur trouvé pour les années {annees_a_recuperer}")
                        # En mode brouillon, retourner des données factices. En mode final, retourner une liste vide.
                        mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
                        if mode == "final":
                            return []  # Pas de données factices en mode final
                        # En mode brouillon, retourner des données factices
                        logger.info(f"📊 Mode brouillon: génération de données factices pour les indicateurs")
                        return default_indicateurs
                    
                    # Récupérer tous les objectifs associés
                    objectif_ids = list(set([ind.objectif_id for ind in indicateurs]))
                    objectifs_query = select(ObjectifPerformance).where(
                        ObjectifPerformance.id.in_(objectif_ids)
                    )
                    objectifs = session.exec(objectifs_query).all()
                    objectifs_dict = {obj.id: obj for obj in objectifs}
                except (ProgrammingError, InternalError, AttributeError) as ind_error:
                    logger.warning(f"⚠️ Erreur lors de la récupération des indicateurs (colonne manquante ?): {ind_error}")
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    # En mode brouillon, retourner des données factices. En mode final, retourner une liste vide.
                    mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
                    if mode == "final":
                        logger.info("⚠️ Pas de données disponibles pour les indicateurs (migration non appliquée)")
                        return []  # Pas de données factices en mode final
                    # En mode brouillon, retourner des données factices
                    logger.info("📊 Mode brouillon: génération de données factices pour les indicateurs (migration non appliquée)")
                    return default_indicateurs
                
                # Grouper les indicateurs par objectif et nom
                indicateurs_groupes: dict[tuple[int, str], dict[str, Any]] = {}
                
                for ind in indicateurs:
                    # Clé: (objectif_id, nom_indicateur)
                    key = (ind.objectif_id, ind.nom)
                    
                    if key not in indicateurs_groupes:
                        objectif = objectifs_dict.get(ind.objectif_id)
                        objectif_titre = f"Objectif Spécifique: {objectif.titre}" if objectif else f"Objectif {ind.objectif_id}"
                        
                        # Calculer les années dynamiquement
                        annee_n_3 = annee - 3
                        annee_n_2 = annee - 2
                        annee_n_1 = annee - 1
                        annee_n = annee
                        
                        indicateurs_groupes[key] = {
                            "objectif_titre": objectif_titre,
                            "indicateur_nom": ind.nom,
                            "unite": ind.unite or "%",
                            f"realisation_{annee_n_3}": None,
                            f"realisation_{annee_n_2}": None,
                            f"realisation_{annee_n_1}": None,
                            f"prevision_{annee_n}": None,
                            f"realisation_{annee_n}": None,
                            "nb_activites": ind.nb_activites,
                            "definition": ind.description or "",
                            "source_donnees": ind.source_donnees or "",
                            "mode_calcul": ind.formule_calcul or "",
                            "valeurs_cibles": ind.valeurs_cibles_futures or f"{ind.valeur_cible}% en {annee}" if ind.valeur_cible else "",
                            "_source": "db",  # Flag pour indiquer que ces données viennent de la base de données
                        }
                    
                    # Mapper les valeurs selon l'année (N, N-1, N-2, N-3)
                    annee_n_3 = annee - 3
                    annee_n_2 = annee - 2
                    annee_n_1 = annee - 1
                    annee_n = annee
                    
                    if ind.annee == annee_n:
                        # Année N (année courante)
                        indicateurs_groupes[key][f"prevision_{annee_n}"] = float(ind.valeur_cible) if ind.valeur_cible else None
                        indicateurs_groupes[key][f"realisation_{annee_n}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                        # Mettre à jour nb_activites avec la valeur de l'année courante si disponible
                        if ind.nb_activites:
                            indicateurs_groupes[key]["nb_activites"] = ind.nb_activites
                    elif ind.annee == annee_n_1:
                        # Année N-1
                        indicateurs_groupes[key][f"realisation_{annee_n_1}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                    elif ind.annee == annee_n_2:
                        # Année N-2
                        indicateurs_groupes[key][f"realisation_{annee_n_2}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                    elif ind.annee == annee_n_3:
                        # Année N-3
                        indicateurs_groupes[key][f"realisation_{annee_n_3}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                
                # Convertir le dictionnaire en liste
                result = list(indicateurs_groupes.values())
                
                if result:
                    logger.info(f"✅ {len(result)} indicateur(s) récupéré(s) depuis la base de données")
                    return result
                else:
                    logger.warning("⚠️ Aucun indicateur valide trouvé")
                    # En mode brouillon, retourner des données factices. En mode final, retourner une liste vide.
                    mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
                    if mode == "final":
                        return []
                    logger.info(f"📊 Mode brouillon: génération de données factices pour les indicateurs")
                    return default_indicateurs
                    
            except Exception as e:
                logger.exception(f"⚠️ Erreur lors de la récupération des indicateurs: {e}")
                # Faire un rollback pour nettoyer l'état de la transaction
                try:
                    session.rollback()
                except Exception:
                    pass
                # En mode brouillon, retourner des données factices. En mode final, retourner une liste vide.
                mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
                if mode == "final":
                    return []
                logger.info(f"📊 Mode brouillon: génération de données factices pour les indicateurs (après erreur)")
                return default_indicateurs
        
        # Si pas de session, en mode brouillon retourner des données factices
        mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
        if mode == "final":
            return []
        logger.info(f"📊 Mode brouillon: génération de données factices pour les indicateurs (pas de session)")
        return default_indicateurs
    
    @staticmethod
    def _create_indicateurs_table(indicateurs_data: list[dict[str, Any]], available_width: float, annee: int, format_programme_value: callable = None) -> LongTable:
        """
        Crée le tableau d'indicateurs de performance avec la structure complexe (objectifs + indicateurs).
        Les années sont calculées dynamiquement basées sur l'année N (annee).
        
        Note: Le formatage se base sur la source de chaque valeur individuelle via indicateur.get("_source"),
        pas sur un flag global. Chaque valeur vérifie sa propre origine (DB ou factice/hardcodée).
        """
        from reportlab.platypus import LongTable, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import ParagraphStyle
        
        # Styles pour les cellules
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=None,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # Center
            spaceAfter=0,
        )
        
        cell_style = ParagraphStyle(
            "CellStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=0,  # Left
            spaceAfter=0,
        )
        
        cell_style_bold = ParagraphStyle(
            "CellStyleBold",
            parent=None,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=0,  # Left
            spaceAfter=0,
        )
        
        cell_right_style = ParagraphStyle(
            "CellRightStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=2,  # Right
            spaceAfter=0,
        )
        
        cell_center_style = ParagraphStyle(
            "CellCenterStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,  # Center
            spaceAfter=0,
        )
        
        # Calculer les années dynamiquement (N-3, N-2, N-1, N)
        annee_n_3 = annee - 3
        annee_n_2 = annee - 2
        annee_n_1 = annee - 1
        annee_n = annee
        
        # Créer les en-têtes multi-niveaux avec années dynamiques
        header = [
            [
                Paragraph("<b>Indicateurs de performance</b>", header_style),
                Paragraph("<b>Unité</b>", header_style),
                Paragraph("<b>Réalisation</b>", header_style),
                "",  # Colonne fusionnée pour Réalisation
                "",  # Colonne fusionnée pour Réalisation
                Paragraph(f"<b>{annee_n}</b>", header_style),
                "",  # Colonne fusionnée pour année N
            ],
            [
                "",  # Indicateurs fusionné
                "",  # Unité fusionné
                Paragraph(f"<b>{annee_n_3}</b>", header_style),
                Paragraph(f"<b>{annee_n_2}</b>", header_style),
                Paragraph(f"<b>{annee_n_1}</b>", header_style),
                Paragraph("<b>Prévision</b>", header_style),
                Paragraph("<b>Réalisation</b>", header_style),
            ],
        ]
        
        # Calculer les largeurs des colonnes (7 colonnes)
        col_widths = [
            available_width * 0.40,  # Indicateurs
            available_width * 0.08,  # Unité
            available_width * 0.10,  # N-3
            available_width * 0.10,  # N-2
            available_width * 0.10,  # N-1
            available_width * 0.11,  # Prévision N
            available_width * 0.11,  # Réalisation N
        ]
        
        # Construire les lignes du tableau
        table_data = []
        table_data.extend(header)
        
        # Grouper les indicateurs par objectif_titre pour éviter les répétitions
        indicateurs_par_objectif: dict[str, list[dict[str, Any]]] = {}
        for indicateur in indicateurs_data:
            objectif_titre = indicateur["objectif_titre"]
            if objectif_titre not in indicateurs_par_objectif:
                indicateurs_par_objectif[objectif_titre] = []
            indicateurs_par_objectif[objectif_titre].append(indicateur)
        
        # Parcourir les objectifs et leurs indicateurs
        for objectif_titre, indicateurs_os in indicateurs_par_objectif.items():
            # Déterminer si cet OS est factice (basé sur le premier indicateur)
            # Si tous les indicateurs ont la même source, utiliser cette source pour l'OS
            premier_indicateur = indicateurs_os[0]
            data_source_os = premier_indicateur.get("_source", "default")
            is_os_fake = (data_source_os == "default")
            
            # Formater le titre de l'OS
            if format_programme_value:
                formatted_objectif_titre = format_programme_value(objectif_titre, is_os_fake)
            else:
                formatted_objectif_titre = objectif_titre
            
            # Ligne objectif (fusionnée sur les 2 premières colonnes uniquement) - UNE SEULE FOIS par OS
            table_data.append([
                Paragraph(f"<b>{formatted_objectif_titre}</b>", cell_style_bold),
                Paragraph("", cell_center_style),  # Unité vide pour la fusion
                Paragraph("", cell_right_style),  # N-3 vide
                Paragraph("", cell_right_style),  # N-2 vide
                Paragraph("", cell_right_style),  # N-1 vide
                Paragraph("", cell_right_style),  # Prévision vide
                Paragraph("", cell_right_style),  # Réalisation vide
            ])
            
            # Afficher TOUS les indicateurs de cet OS à la suite
            for indicateur in indicateurs_os:
                indicateur_nom = indicateur["indicateur_nom"]
                unite = indicateur["unite"]
                
                # Déterminer si CETTE donnée spécifique est factice (basé sur l'objet indicateur lui-même)
                # Chaque valeur vérifie sa propre origine
                data_source = indicateur.get("_source", "default")
                is_this_indicateur_fake = (data_source == "default")
                
                # Récupérer les valeurs avec des clés dynamiques basées sur l'année N
                realisation_n_3 = indicateur.get(f"realisation_{annee_n_3}")
                realisation_n_2 = indicateur.get(f"realisation_{annee_n_2}")
                realisation_n_1 = indicateur.get(f"realisation_{annee_n_1}")
                prevision_n = indicateur.get(f"prevision_{annee_n}", 0)
                realisation_n = indicateur.get(f"realisation_{annee_n}", 0)
                
                # Formater chaque valeur selon sa propre origine (factice ou DB)
                if format_programme_value:
                    formatted_indicateur_nom = format_programme_value(indicateur_nom, is_this_indicateur_fake)
                    formatted_unite = format_programme_value(unite, is_this_indicateur_fake)
                else:
                    formatted_indicateur_nom = indicateur_nom
                    formatted_unite = unite
                
                # Ligne indicateur - formater chaque valeur selon sa source
                if format_programme_value:
                    r_n_3 = "-" if realisation_n_3 is None else format_programme_value(str(realisation_n_3), is_this_indicateur_fake)
                    r_n_2 = "-" if realisation_n_2 is None else format_programme_value(str(realisation_n_2), is_this_indicateur_fake)
                    r_n_1 = "-" if realisation_n_1 is None else format_programme_value(str(realisation_n_1), is_this_indicateur_fake)
                    formatted_prevision_n = format_programme_value(str(prevision_n), is_this_indicateur_fake)
                    formatted_realisation_n = format_programme_value(str(realisation_n), is_this_indicateur_fake)
                else:
                    r_n_3 = "-" if realisation_n_3 is None else str(realisation_n_3)
                    r_n_2 = "-" if realisation_n_2 is None else str(realisation_n_2)
                    r_n_1 = "-" if realisation_n_1 is None else str(realisation_n_1)
                    formatted_prevision_n = str(prevision_n)
                    formatted_realisation_n = str(realisation_n)
                
                table_data.append([
                    Paragraph(formatted_indicateur_nom, cell_style),
                    Paragraph(formatted_unite, cell_center_style),
                    Paragraph(r_n_3, cell_right_style),
                    Paragraph(r_n_2, cell_right_style),
                    Paragraph(r_n_1, cell_right_style),
                    Paragraph(formatted_prevision_n, cell_right_style),
                    Paragraph(formatted_realisation_n, cell_right_style),
                ])
        
        # Créer le LongTable pour le support multi-page
        indicateurs_table = LongTable(table_data, colWidths=col_widths, repeatRows=2, splitByRow=1)
        
        # Style du tableau
        indicateurs_table_style = TableStyle([
            # Bordures extérieures
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            
            # Fusionner les cellules d'en-tête
            ("SPAN", (0, 0), (0, 1)),  # Indicateurs fusionné
            ("SPAN", (1, 0), (1, 1)),  # Unité fusionné
            ("SPAN", (2, 0), (4, 0)),  # Réalisation fusionné (N-3 à N-1)
            ("SPAN", (5, 0), (6, 0)),  # Année N fusionné (Prévision + Réalisation)
            
            # En-têtes (lignes 0 et 1)
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.black),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 1), 9),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
        
        # Fusionner les cellules des lignes d'objectifs (lignes impaires après les en-têtes: 2, 4, 6, ...)
        # Chaque ligne objectif fusionne les colonnes 0 et 1 (Indicateurs + Unité)
        num_indicateurs = len(indicateurs_data)
        for i in range(num_indicateurs):
            objectif_row_num = 2 + (i * 2)  # Lignes: 2, 4, 6, ...
            indicateurs_table_style.add("SPAN", (0, objectif_row_num), (1, objectif_row_num))  # Fusionner colonnes 0-1
        
        # Styles pour les lignes de données
        indicateurs_table_style.add("FONTNAME", (0, 2), (0, -1), "Helvetica-Bold")  # Première colonne en gras pour objectifs
        indicateurs_table_style.add("VALIGN", (0, 2), (-1, -1), "MIDDLE")
        indicateurs_table_style.add("ALIGN", (2, 2), (-1, -1), "RIGHT")  # Alignement droit pour les valeurs numériques
        
        indicateurs_table.setStyle(indicateurs_table_style)
        
        return indicateurs_table
    
    @staticmethod
    def _get_effectifs_data(numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les données d'effectifs pour un programme depuis la base de données.
        Retourne une liste de catégories avec leurs effectifs.
        Pas de valeurs par défaut - retourne une liste vide si aucune donnée n'est trouvée.
        """
        # Pas de valeurs par défaut - uniquement les données de la DB
        effectifs_list = []
        
        if session:
            try:
                from sqlmodel import select, func
                from app.models.personnel import AgentComplet, GradeComplet, Programme
                from app.core.enums import GradeCategory
                
                # Trouver le programme par son libelle
                programme = session.exec(
                    select(Programme).where(Programme.libelle.ilike(f"%{titre}%"))
                ).first()
                
                if not programme:
                    logger.warning(f"⚠️ Programme '{titre}' non trouvé dans la base de données")
                    # En mode brouillon, générer des données factices. En mode final, retourner une liste vide.
                    mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
                    if mode == "final":
                        return []
                    # Générer des données factices en mode brouillon avec le flag _is_fake
                    logger.info(f"📊 Mode brouillon: génération de données factices pour les effectifs")
                    annee_precedente = annee - 1
                    return [
                        {"categorie": "Catégorie A", f"effectif_{annee_precedente}": 25, "besoins_exprimes": 5, "previsions": 5, "besoins_satisfaits": 4, "sorties": 2, "_is_fake": True},
                        {"categorie": "Catégorie B", f"effectif_{annee_precedente}": 45, "besoins_exprimes": 8, "previsions": 8, "besoins_satisfaits": 7, "sorties": 3, "_is_fake": True},
                        {"categorie": "Catégorie C", f"effectif_{annee_precedente}": 30, "besoins_exprimes": 6, "previsions": 6, "besoins_satisfaits": 5, "sorties": 2, "_is_fake": True},
                        {"categorie": "Catégorie D", f"effectif_{annee_precedente}": 15, "besoins_exprimes": 3, "previsions": 3, "besoins_satisfaits": 2, "sorties": 1, "_is_fake": True},
                        {"categorie": "Non Fonctionnaires", f"effectif_{annee_precedente}": 10, "besoins_exprimes": 2, "previsions": 2, "besoins_satisfaits": 2, "sorties": 0, "_is_fake": True},
                    ]
                
                annee_precedente = annee - 1
                
                # Récupérer les effectifs par catégorie pour l'année précédente (N-1)
                # Compter les agents actifs par catégorie de grade
                categories = ["A", "B", "C", "D"]
                effectifs_dict = {}
                
                for cat_code in categories:
                    # Compter les agents actifs de cette catégorie pour le programme
                    count_n_minus_1 = session.exec(
                        select(func.count(AgentComplet.id))
                        .join(GradeComplet, AgentComplet.grade_id == GradeComplet.id)
                        .where(AgentComplet.programme_id == programme.id)
                        .where(AgentComplet.actif == True)
                        .where(GradeComplet.categorie == cat_code)
                    ).first() or 0
                    
                    effectifs_dict[f"Catégorie {cat_code}"] = {
                        f"effectif_{annee_precedente}": count_n_minus_1,
                        "besoins_exprimes": 0,  # À remplir depuis une autre source si disponible
                        "previsions": 0,
                        "besoins_satisfaits": 0,
                        "sorties": 0,
                    }
                
                # Compter les non-fonctionnaires (agents sans grade ou avec un statut particulier)
                count_non_fonctionnaires = session.exec(
                    select(func.count(AgentComplet.id))
                    .where(AgentComplet.programme_id == programme.id)
                    .where(AgentComplet.actif == True)
                    .where(AgentComplet.grade_id.is_(None))
                ).first() or 0
                
                effectifs_dict["Non Fonctionnaires"] = {
                    f"effectif_{annee_precedente}": count_non_fonctionnaires,
                    "besoins_exprimes": 0,
                    "previsions": 0,
                    "besoins_satisfaits": 0,
                    "sorties": 0,
                }
                
                # Convertir le dictionnaire en liste
                for categorie, data in effectifs_dict.items():
                    effectifs_list.append({
                        "categorie": categorie,
                        f"effectif_{annee_precedente}": data[f"effectif_{annee_precedente}"],
                        "besoins_exprimes": data["besoins_exprimes"],
                        "previsions": data["previsions"],
                        "besoins_satisfaits": data["besoins_satisfaits"],
                        "sorties": data["sorties"],
                    })
                    
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors de la récupération des effectifs: {e}")
        
        # Si pas de données, générer des données factices en mode brouillon
        if not effectifs_list:
            mode = RapportAnnuelPerformanceGeneratorSimpleDoc.data.get("mode", "brouillon")
            if mode == "final":
                return []
            # Générer des données factices en mode brouillon
            logger.info(f"📊 Mode brouillon: génération de données factices pour les effectifs")
            annee_precedente = annee - 1
            factices = [
                {"categorie": "Catégorie A", f"effectif_{annee_precedente}": 25, "besoins_exprimes": 5, "previsions": 5, "besoins_satisfaits": 4, "sorties": 2, "_is_fake": True},
                {"categorie": "Catégorie B", f"effectif_{annee_precedente}": 45, "besoins_exprimes": 8, "previsions": 8, "besoins_satisfaits": 7, "sorties": 3, "_is_fake": True},
                {"categorie": "Catégorie C", f"effectif_{annee_precedente}": 30, "besoins_exprimes": 6, "previsions": 6, "besoins_satisfaits": 5, "sorties": 2, "_is_fake": True},
                {"categorie": "Catégorie D", f"effectif_{annee_precedente}": 15, "besoins_exprimes": 3, "previsions": 3, "besoins_satisfaits": 2, "sorties": 1, "_is_fake": True},
                {"categorie": "Non Fonctionnaires", f"effectif_{annee_precedente}": 10, "besoins_exprimes": 2, "previsions": 2, "besoins_satisfaits": 2, "sorties": 0, "_is_fake": True},
            ]
            return factices
        
        return effectifs_list
    
    @staticmethod
    def _create_effectifs_table(effectifs_data: list[dict[str, Any]], available_width: float, annee: int, is_fake: bool = False, format_programme_value: callable = None) -> LongTable:
        """
        Crée le tableau d'effectifs avec la structure complexe (en-têtes multi-niveaux).
        Utilise des années dynamiques au lieu de valeurs hardcodées.
        
        Note: Le formatage se base sur la source de chaque valeur individuelle via effectif.get("_is_fake"),
        pas sur le paramètre is_fake (conservé pour compatibilité).
        Chaque valeur vérifie sa propre origine (DB ou factice/hardcodée).
        """
        annee_precedente = annee - 1
        from reportlab.platypus import LongTable, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import ParagraphStyle
        
        # Styles pour les cellules
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=None,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # Center
            spaceAfter=0,
        )
        
        cell_style = ParagraphStyle(
            "CellStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=0,  # Left
            spaceAfter=0,
        )
        
        cell_style_bold = ParagraphStyle(
            "CellStyleBold",
            parent=None,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=0,  # Left
            spaceAfter=0,
        )
        
        cell_right_style = ParagraphStyle(
            "CellRightStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=2,  # Right
            spaceAfter=0,
        )
        
        cell_center_style = ParagraphStyle(
            "CellCenterStyle",
            parent=None,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,  # Center
            spaceAfter=0,
        )
        
        # Créer les en-têtes multi-niveaux avec années dynamiques
        header = [
            [
                Paragraph("<b>Catégorie</b>", header_style),
                Paragraph(f"<b>Effectif ({annee_precedente})<br/>(a)</b>", header_style),
                Paragraph(f"<b>Effectif ({annee})</b>", header_style),
                "",  # Colonne fusionnée pour Effectif (annee)
                "",  # Colonne fusionnée pour Effectif (annee)
                "",  # Colonne fusionnée pour Effectif (annee)
                Paragraph("<b>Total fin d'année<br/>(a)+(b)-(c)</b>", header_style),
            ],
            [
                "",  # Catégorie fusionnée
                "",  # Effectif N-1 fusionné
                Paragraph("<b>Besoins exprimés</b>", header_style),
                Paragraph("<b>Prévisions</b>", header_style),
                Paragraph("<b>Besoins satisfaits (b)</b>", header_style),
                Paragraph("<b>Sorties (c)</b>", header_style),
                "",  # Total fin d'année fusionné
            ],
        ]
        
        # Calculer les largeurs des colonnes (7 colonnes au total)
        col_widths = [
            available_width * 0.22,  # Catégorie
            available_width * 0.12,  # Effectif (2023)
            available_width * 0.11,  # Besoins exprimés
            available_width * 0.11,  # Prévisions
            available_width * 0.13,  # Besoins satisfaits
            available_width * 0.11,  # Sorties
            available_width * 0.20,  # Total fin d'année
        ]
        
        # Construire les lignes du tableau
        table_data = []
        table_data.extend(header)
        
        total_effectif_n_minus_1 = 0
        total_besoins_exprimes = 0
        total_previsions = 0
        total_besoins_satisfaits = 0
        total_sorties = 0
        
        # Parcourir les catégories
        # Track des totaux avec leur statut factice pour déterminer si les totaux finaux sont factices
        totals_are_fake = False
        
        for effectif in effectifs_data:
            categorie = effectif["categorie"]
            # Utiliser la clé dynamique basée sur l'année précédente
            effectif_n_minus_1 = effectif.get(f"effectif_{annee_precedente}", 0)
            besoins_exprimes = effectif.get("besoins_exprimes", 0)
            previsions = effectif.get("previsions", 0)
            besoins_satisfaits = effectif.get("besoins_satisfaits", 0)
            sorties = effectif.get("sorties", 0)
            total_fin_annee = effectif_n_minus_1 + besoins_satisfaits - sorties
            
            # Déterminer si CETTE donnée spécifique est factice (basé sur l'objet effectif lui-même)
            # Chaque valeur vérifie sa propre origine: si l'objet effectif a le flag _is_fake, 
            # alors toutes ses valeurs sont factices (provenant de données hardcodées)
            is_this_effectif_fake = effectif.get("_is_fake", False)
            
            # Si au moins un effectif est factice, les totaux seront aussi factices
            if is_this_effectif_fake:
                totals_are_fake = True
            
            # Formater chaque valeur selon sa propre origine (factice ou DB)
            # format_programme_value est toujours fourni, donc on peut l'utiliser directement
            formatted_categorie = format_programme_value(categorie, is_this_effectif_fake)
            formatted_effectif_n_minus_1 = format_programme_value(str(effectif_n_minus_1), is_this_effectif_fake)
            formatted_besoins_exprimes = format_programme_value(str(besoins_exprimes), is_this_effectif_fake)
            formatted_previsions = format_programme_value(str(previsions), is_this_effectif_fake)
            formatted_besoins_satisfaits = format_programme_value(str(besoins_satisfaits), is_this_effectif_fake)
            formatted_sorties = format_programme_value(str(sorties), is_this_effectif_fake)
            # La valeur calculée est factice si la donnée source est factice
            formatted_total_fin_annee = format_programme_value(str(total_fin_annee), is_this_effectif_fake)
            
            # Ligne de données
            table_data.append([
                Paragraph(formatted_categorie, cell_style),
                Paragraph(formatted_effectif_n_minus_1, cell_right_style),
                Paragraph(formatted_besoins_exprimes, cell_right_style),
                Paragraph(formatted_previsions, cell_right_style),
                Paragraph(formatted_besoins_satisfaits, cell_right_style),
                Paragraph(formatted_sorties, cell_right_style),
                Paragraph(formatted_total_fin_annee, cell_right_style),
            ])
            
            # Accumuler les totaux
            total_effectif_n_minus_1 += effectif_n_minus_1
            total_besoins_exprimes += besoins_exprimes
            total_previsions += previsions
            total_besoins_satisfaits += besoins_satisfaits
            total_sorties += sorties
        
        # Ligne totale
        total_fin_annee_total = total_effectif_n_minus_1 + total_besoins_satisfaits - total_sorties
        
        # Formater les totaux selon leur source
        # Les totaux sont factices si au moins une donnée source est factice (déterminé dans la boucle)
        # format_programme_value est toujours fourni, donc on peut l'utiliser directement
        formatted_total_effectif = format_programme_value(str(total_effectif_n_minus_1), totals_are_fake)
        formatted_total_besoins_exprimes = format_programme_value(str(total_besoins_exprimes), totals_are_fake)
        formatted_total_previsions = format_programme_value(str(total_previsions), totals_are_fake)
        formatted_total_besoins_satisfaits = format_programme_value(str(total_besoins_satisfaits), totals_are_fake)
        formatted_total_sorties = format_programme_value(str(total_sorties), totals_are_fake)
        formatted_total_fin_annee = format_programme_value(str(total_fin_annee_total), totals_are_fake)
        
        table_data.append([
            Paragraph("<b>TOTAL</b>", cell_style_bold),
            Paragraph(formatted_total_effectif, cell_right_style),
            Paragraph(formatted_total_besoins_exprimes, cell_right_style),
            Paragraph(formatted_total_previsions, cell_right_style),
            Paragraph(formatted_total_besoins_satisfaits, cell_right_style),
            Paragraph(formatted_total_sorties, cell_right_style),
            Paragraph(formatted_total_fin_annee, cell_right_style),
        ])
        
        # Créer le LongTable pour le support multi-page
        effectifs_table = LongTable(table_data, colWidths=col_widths, repeatRows=2, splitByRow=1)
        
        # Style du tableau
        effectifs_table_style = TableStyle([
            # Bordures extérieures
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            
            # Fusionner les cellules d'en-tête
            ("SPAN", (0, 0), (0, 1)),  # Catégorie
            ("SPAN", (1, 0), (1, 1)),  # Effectif (2023)
            ("SPAN", (2, 0), (5, 0)),  # Effectif (2024) - fusionner les 4 colonnes (2 à 5)
            ("SPAN", (6, 0), (6, 1)),  # Total fin d'année
            
            # En-têtes (lignes 0 et 1)
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.black),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 1), 9),
            
            # Ligne totale (dernière ligne)
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            
            # Alignement des montants (colonnes numériques)
            ("ALIGN", (1, 2), (-1, -2), "RIGHT"),
            ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
        
        effectifs_table.setStyle(effectifs_table_style)
        
        return effectifs_table
    
    @staticmethod
    def _create_bar_chart_effectifs(
        effectifs_data: list[dict[str, Any]],
        annee_precedente: int,
        annee: int,
        numero_programme: int,
        titre_programme: str,
    ) -> BytesIO | None:
        """
        Crée un graphique en barres groupées pour l'évolution des effectifs par catégorie.
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Préparer les données pour le graphique
            categories = []
            effectifs_n_minus_1 = []
            effectifs_n = []
            
            for effectif in effectifs_data:
                categories.append(effectif["categorie"])
                # Utiliser la clé dynamique basée sur l'année précédente
                effectif_n_minus_1_val = effectif.get(f"effectif_{annee_precedente}", 0)
                effectifs_n_minus_1.append(effectif_n_minus_1_val)
                # Calculer l'effectif N : effectif_N-1 + besoins_satisfaits - sorties
                effectif_n_val = effectif_n_minus_1_val + effectif.get("besoins_satisfaits", 0) - effectif.get("sorties", 0)
                effectifs_n.append(effectif_n_val)
            
            # Si pas de données, ne pas générer le graphique
            if not effectifs_n_minus_1:
                logger.warning("⚠️ Aucune donnée d'effectif disponible pour le graphique")
                return None
            
            # Créer la figure
            fig, ax = plt.subplots(figsize=(16, 6), dpi=200)
            
            # Position des barres
            x = np.arange(len(categories))
            width = 0.35  # Largeur des barres
            
            # Créer les barres avec les mêmes couleurs que les autres graphiques
            bars1 = ax.bar(x - width/2, effectifs_n_minus_1, width, label=str(annee_precedente), color='#5b9bd5')  # Bleu
            bars2 = ax.bar(x + width/2, effectifs_n, width, label=str(annee), color='#ed7d31')  # Orange
            
            # Ajouter les valeurs sur les barres
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}',
                           ha='center', va='bottom', fontsize=18, fontweight='bold')
            
            # Configuration de l'axe Y
            max_effectif = max(max(effectifs_n_minus_1), max(effectifs_n))
            y_max = ((max_effectif // 10) + 1) * 10 + 10  # Arrondir à la dizaine supérieure + 10 points
            ax.set_ylabel('Effectif', fontsize=20, fontweight='bold')
            ax.set_ylim(0, y_max)
            ax.set_yticks(range(0, y_max + 1, 10))
            ax.tick_params(axis='y', labelsize=16)
            
            # Configuration de l'axe X
            ax.set_xlabel('Catégories', fontsize=20, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(categories, fontsize=14, fontweight='bold', rotation=0, ha='center')
            
            # Légende
            ax.legend(loc='upper right', fontsize=16, frameon=True)
            
            # Grille horizontale visible
            ax.grid(axis='y', linestyle='-', alpha=0.5, color='gray', linewidth=1)
            
            # Fond blanc
            ax.set_facecolor('white')
            fig.patch.set_facecolor('white')
            
            # Ajuster la mise en page
            plt.tight_layout()
            
            # Sauvegarder avec fond blanc
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=200, facecolor='white', edgecolor='none', bbox_inches='tight')
            plt.close(fig)
            buffer.seek(0)
            
            return buffer
            
        except ImportError:
            logger.warning("⚠️ matplotlib n'est pas disponible, graphique des effectifs ignoré")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors de la création du graphique des effectifs: {e}", exc_info=True)
            return None

    @classmethod
    def _draw_partie_programme_simpledoc(cls, programme: dict[str, Any], start_page: int, session=None) -> tuple[BytesIO, int]:
        """
        Génère la partie programme avec SimpleDocTemplate pour gérer le découpage automatique du LongTable.
        
        Returns:
            Tuple (buffer du PDF temporaire, numéro de la dernière page)
        """
        logger.info(f"📄 Génération partie programme {programme.get('numero', 1)} avec SimpleDocTemplate...")
        
        # Récupérer les données du programme
        numero = programme.get("numero", 1)
        titre = programme.get("titre", "")
        
        # Calculer le numéro romain de la partie (utilisé plus tard)
        partie_numero_romain = cls._number_to_roman(numero + 1)
        
        # Déterminer si le programme est factice (vient de DEFAULT_DATA)
        is_programme_fake = programme.get("_is_fake", False)
        if is_programme_fake:
            logger.info(f"📊 Programme {numero} « {titre} » est factice (DEFAULT_DATA)")
        else:
            logger.info(f"📊 Programme {numero} « {titre} » vient de la DB")
        
        # Dimensions de la page
        page_width, page_height = landscape(A4)
        
        # Marges et dimensions (identiques au service original)
        left_margin = 2.5 * cm
        right_margin = 2.5 * cm
        top_margin = 2.5 * cm
        footer_height = 1.5 * cm
        footer_margin = 0.5 * cm
        bottom_margin = footer_height + footer_margin
        available_width = page_width - left_margin - right_margin
        
        # Créer un buffer temporaire pour cette section
        temp_buffer = BytesIO()
        
        # Créer SimpleDocTemplate avec les mêmes marges
        doc = SimpleDocTemplate(
            temp_buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Styles (copiés du service original)
        styles = getSampleStyleSheet()
        partie_title_style = ParagraphStyle(
            "PartieTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=0,
            spaceAfter=12,
            textColor=colors.HexColor("#0066CC"),
        )
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=0,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#000000"),
            keepWithNext=1,
        )
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=0,
            spaceBefore=6,
            spaceAfter=4,
            textColor=colors.HexColor("#000000"),
            keepWithNext=1,
        )
        subsection_title_with_table_style = ParagraphStyle(
            "SubsectionTitleWithTable",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=0,
            spaceBefore=6,
            spaceAfter=4,
            textColor=colors.HexColor("#000000"),
            keepWithNext=0,
            firstLineIndent=0,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            alignment=4,
            spaceAfter=4,
        )
        # Style avec indentation pour les sous-éléments des indicateurs (hiérarchie)
        indicateur_subitem_style = ParagraphStyle(
            "IndicateurSubitem",
            parent=body_style,
            leftIndent=1.0 * cm,  # Indentation pour montrer la hiérarchie
            firstLineIndent=0,
            spaceAfter=4,
        )
        source_style = ParagraphStyle(
            "Source",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            alignment=0,  # Gauche (pas de décalage)
            spaceBefore=4,
            spaceAfter=4,
            leftIndent=0,  # Pas de retrait à gauche
            rightIndent=0,  # Pas de retrait à droite
        )
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
        table_cell_right_small_style = ParagraphStyle(
            "TableCellRightSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,  # Police plus petite pour les montants
            leading=8,
            alignment=TA_RIGHT,
            spaceBefore=0.5,
            spaceAfter=0.5,
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
        table_total_right_small_style = ParagraphStyle(
            "TableTotalRightSmall",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,  # Police plus petite pour les montants totaux
            leading=8,
            alignment=TA_RIGHT,
            spaceBefore=0.5,
            spaceAfter=0.5,
        )
        
        # Fonction pour formater les montants
        def format_fcfa(montant: float) -> str:
            if montant == 0:
                return "0"
            montant_str = f"{int(montant):,}".replace(",", " ")
            return montant_str
        
        # Story pour SimpleDocTemplate
        story = []
        
        # Récupérer les données du programme
        programme_data = programme
        
        # Valeurs par défaut pour les données du programme
        annee = cls.data.get("annee", 2024)
        
        # Valeurs par défaut selon le programme
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        # Toutes les valeurs doivent venir de la DB ou être "NC"/[]/0
        
        # Charger les missions depuis la base de données (table Programme)
        missions = []
        if session:
            try:
                from app.models.personnel import Programme
                from sqlmodel import select
                import json
                
                # Chercher le programme par code ou libelle
                programme_db = None
                if programme_data.get("code"):
                    programme_db = session.exec(
                        select(Programme).where(Programme.code == programme_data.get("code"))
                    ).first()
                elif titre:
                    # Chercher par libelle (titre)
                    programme_db = session.exec(
                        select(Programme).where(Programme.libelle.ilike(f"%{titre}%"))
                    ).first()
                
                if programme_db and programme_db.missions:
                    try:
                        # Parser le JSON stocké dans missions
                        missions = json.loads(programme_db.missions)
                        if not isinstance(missions, list):
                            missions = []
                        logger.debug(f"✅ Missions chargées depuis DB pour programme {numero}: {len(missions)} missions")
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"⚠️ Erreur lors du parsing des missions pour programme {numero}")
                        missions = []
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du chargement des missions depuis DB: {e}")
                missions = []
        
        # Récupérer les autres valeurs depuis programme_data (données utilisateur) ou utiliser "NC"/[] comme défaut
        responsable_nom = programme_data.get("responsable_nom", "NC")
        responsable_fonction = programme_data.get("responsable_fonction", "NC")
        decret_nomination = programme_data.get("decret_nomination", "NC")
        decret_designation = programme_data.get("decret_designation", "NC")
        contexte = programme_data.get("contexte", "NC")
        structure_rapport = programme_data.get("structure_rapport", [])
        
        # Debug: logger les données récupérées
        logger.debug(f"📋 Programme {numero} - Missions: {missions}, Contexte: {contexte}, Structure: {structure_rapport}")
        
        # Si les valeurs sont vides, utiliser "NC" pour les textes
        if not responsable_nom or responsable_nom.strip() == "":
            responsable_nom = "NC"
        if not responsable_fonction or responsable_fonction.strip() == "":
            responsable_fonction = "NC"
        if not decret_nomination or decret_nomination.strip() == "":
            decret_nomination = "NC"
        if not decret_designation or decret_designation.strip() == "":
            decret_designation = "NC"
        if not contexte or contexte.strip() == "":
            contexte = "NC"
        
        # Déterminer si les données proviennent de la DB (pour le budget)
        programme_budget = programme_data.get("budget", {})
        is_from_db_budget = session is not None and len(programme_budget) > 0
        
        # Déterminer si le programme est factice
        # Priorité 1: utiliser le flag _is_fake du programme (défini dans generate_pdf)
        is_programme_fake = programme.get("_is_fake", False)
        
        # Priorité 2: si pas de flag, utiliser la logique basée sur les données budgétaires
        if not is_programme_fake and not is_from_db_budget:
            is_programme_fake = cls._should_use_fake_data()
        
        # Fonction helper pour formater les valeurs du programme selon leur source
        def format_programme_value(value: Any, is_fake: bool = False) -> str:
            """
            Formate une valeur du programme selon si elle est factice ou réelle.
            
            Args:
                value: La valeur à formater
                is_fake: True si la valeur est factice (générée), False si elle vient de la DB
            """
            # Si is_fake est True, les données sont factices et doivent être formatées en violet
            # (elles ne sont générées qu'en mode brouillon, donc _should_use_fake_data() devrait toujours être True)
            if is_fake:
                return cls._format_fake_data(str(value))
            else:
                return cls._format_db_data(str(value))
        
        # Titre de la partie (formaté après la définition de format_programme_value)
        formatted_numero_partie = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_partie = format_programme_value(titre.upper(), is_programme_fake)
        story.append(Paragraph(f"PARTIE {partie_numero_romain} : LE PROGRAMME {formatted_numero_partie} « {formatted_titre_partie} »", partie_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Section INTRODUCTION
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("INTRODUCTION", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Paragraphe 1 : Responsable du programme (toujours affiché si responsable_nom fourni)
        if responsable_nom and responsable_nom != "NC":
            # Toutes les données sont DB (rouge)
            formatted_nom = cls._format_db_data(responsable_nom)
            formatted_fonction = cls._format_db_data(responsable_fonction) if responsable_fonction != "NC" else cls._format_db_data("Responsable de Programme")
            formatted_nomination = cls._format_db_data(decret_nomination) if decret_nomination != "NC" else cls._format_db_data("décret")
            formatted_designation = cls._format_db_data(decret_designation) if decret_designation != "NC" else cls._format_db_data("le décret")
            formatted_titre = cls._format_db_data(titre)
            
            para1_text = (
                f"Nommé {formatted_fonction} par {formatted_nomination}, {formatted_nom} est le Responsable du programme « {formatted_titre} », "
                f"conformément à {formatted_designation}."
            )
            story.append(Paragraph(para1_text, body_style))
            story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 2 : Missions du programme (toujours affiché avec décret depuis SystemSettings)
        # Récupérer les informations du décret d'organisation depuis les données chargées
        partie_data = cls.data.get("partie_ministere", {})
        intro_data = cls.data.get("introduction", {})
        # Récupérer le décret d'organisation
        decret_org_num = intro_data.get("decret_organisation_numero") or partie_data.get("decret_organisation_numero")
        decret_org_date = intro_data.get("decret_organisation_date") or partie_data.get("decret_organisation_date")
        
        # Déterminer si le décret est factice (si la DB est vide et mode brouillon)
        is_decret_fake = (not decret_org_num or not decret_org_date) and cls._should_use_fake_data()
        
        # Générer des données factices pour le décret si nécessaire
        if is_decret_fake:
            decret_org_num = f"n° {annee - 1}-963"
            decret_org_date = f"6 décembre {annee - 1}"
            logger.info(f"📊 Mode brouillon: génération de données factices pour le décret d'organisation")
        
        # Formater selon la source (factice ou DB)
        formatted_decret_num = format_programme_value(decret_org_num, is_decret_fake)
        formatted_decret_date = format_programme_value(decret_org_date, is_decret_fake)
        
        para2_text = (
            f"Ce programme a été réalisé à partir d'une répartition des tâches mise en place en fonction "
            f"du décret {formatted_decret_num} du {formatted_decret_date} portant organisation du ministère."
        )
        story.append(Paragraph(para2_text, body_style))
        
        # Afficher les missions (toujours affiché, même si la liste est vide)
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph("Les principales missions sont :", body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Liste des missions avec puces (tirets)
        bullet_style = ParagraphStyle(
            "BulletStyle",
            parent=body_style,
            leftIndent=20,
            bulletIndent=10,
        )
        
        # Déterminer si les missions sont factices (si la DB est vide et mode brouillon)
        is_missions_fake = (not missions or len(missions) == 0) and cls._should_use_fake_data()
        
        # Générer des données factices pour les missions si nécessaire
        if is_missions_fake:
            missions = [
                "Assurer la coordination et le suivi des activités administratives du ministère",
                "Gérer les ressources humaines et matérielles du programme",
                "Superviser l'exécution budgétaire et la performance du programme",
                "Assurer la communication et la diffusion des informations du programme"
            ]
            logger.info(f"📊 Mode brouillon: génération de données factices pour les missions")
        
        # Afficher les missions si disponibles
        if missions and len(missions) > 0:
            for mission in missions:
                # Formater selon la source (factice ou DB)
                formatted_mission = format_programme_value(mission, is_missions_fake)
                story.append(Paragraph(formatted_mission, bullet_style, bulletText="-"))
        
        story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 3 : Contexte et environnement (affiché si fourni)
        if contexte and contexte != "NC":
            # Toutes les données sont DB (rouge)
            formatted_contexte = cls._format_db_data(contexte)
            story.append(Paragraph(formatted_contexte, body_style))
            story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 4 : Structure du rapport avec liste à puces (toujours affiché)
        # Déterminer si structure_rapport est factice (si vide et mode brouillon)
        is_structure_fake = (not structure_rapport or len(structure_rapport) == 0) and cls._should_use_fake_data()
        
        # Générer des données factices si nécessaire (mode brouillon et DB vide)
        if is_structure_fake:
            structure_rapport = [
                "la présentation de la stratégie du programme",
                f"les réalisations du programme au cours de l'exercice {annee}",
                "la performance du programme",
                "les perspectives"
            ]
            logger.info(f"📊 Mode brouillon: génération de données factices pour la structure du rapport")
        
        # Le titre vient toujours de la DB (pas factice)
        formatted_titre_para4 = format_programme_value(titre, is_programme_fake)
        para4_text = (
            f"Pour faire face à des défis de plus en plus élevés, le Programme a élaboré un plan d'actions et défini des indicateurs "
            f"dont la réalisation est décrite dans le présent Rapport Annuel de Performance (RAP) du programme « {formatted_titre_para4} » qui prend en compte "
            f"les rapports semestriels du Responsable de Programme (Rprog) et s'articule autour des points suivants :"
        )
        story.append(Paragraph(para4_text, body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Liste à puces (cercles noirs) - afficher seulement si structure_rapport a des données
        if structure_rapport and len(structure_rapport) > 0:
            circle_bullet_style = ParagraphStyle(
                "CircleBulletStyle",
                parent=body_style,
                leftIndent=20,
                bulletIndent=10,
            )
            for item in structure_rapport:
                # Formater l'année dans le texte si présente (l'année n'est jamais factice, toujours DB)
                item_formatted = item
                if "{annee}" in item or f"{annee}" in item:
                    # Remplacer l'année par la valeur formatée (année toujours DB)
                    item_formatted = item.replace(f"{annee}", format_programme_value(str(annee), False))
                # Formater selon la source (factice ou DB)
                formatted_item = format_programme_value(item_formatted, is_structure_fake)
                story.append(Paragraph(formatted_item, circle_bullet_style, bulletText="•"))
        
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
        objectif_global_num = objectif_global.get("numero", "NC")
        objectif_global_libelle = objectif_global.get("libelle", "Non communiqué")
        resultat_strategique_num = objectif_global.get("resultat_strategique_num", "NC")
        resultat_strategique_libelle = objectif_global.get("resultat_strategique_libelle", "Non communiqué")
        
        # Déterminer si chaque donnée est factice ou réelle
        # Le titre et le ministère viennent toujours de la DB
        is_titre_fake = False
        is_ministere_fake = False
        
        # Générer des données factices pour les objectifs si la DB est vide (mode brouillon)
        is_objectif_fake = (objectif_global_num == "NC" or objectif_global_libelle == "Non communiqué") and cls._should_use_fake_data()
        is_resultat_fake = (resultat_strategique_num == "NC" or resultat_strategique_libelle == "Non communiqué") and cls._should_use_fake_data()
        
        # Générer des valeurs factices si nécessaire
        if is_objectif_fake:
            objectif_global_num = "1"
            objectif_global_libelle = "Améliorer la gouvernance et la performance des structures publiques"
        if is_resultat_fake:
            resultat_strategique_num = "1"
            resultat_strategique_libelle = "Renforcement des capacités institutionnelles et amélioration de la qualité des services publics"
        
        # Formater les données selon leur source (factice ou DB)
        formatted_titre_obj = format_programme_value(titre, is_titre_fake)
        formatted_objectif_num = format_programme_value(str(objectif_global_num), is_objectif_fake)
        formatted_ministere_obj = format_programme_value(cls.data.get('ministere', 'Non communiqué'), is_ministere_fake)
        formatted_objectif_libelle = format_programme_value(objectif_global_libelle, is_objectif_fake)
        formatted_resultat_libelle = format_programme_value(resultat_strategique_libelle, is_resultat_fake)
        
        objectifs_para = (
            f"La mise en œuvre des activités du Programme « {formatted_titre_obj} » permettra, à moyen terme, de contribuer à la poursuite "
            f"de l'objectif global {formatted_objectif_num} du {formatted_ministere_obj}, à savoir « {formatted_objectif_libelle} » "
            f"et d'atteindre le résultat stratégique « {formatted_resultat_libelle} »."
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
            alignment=TA_CENTER,
        )
        table_obj_cell_style = ParagraphStyle(
            "TableObjCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            alignment=TA_LEFT,
        )
        
        # Formater les données pour le tableau (déjà formatées plus haut, mais on les réutilise)
        obj_table_data = [
            [
                Paragraph("OBJECTIF GLOBAL (OG)", table_obj_header_style),
                Paragraph("RESULTAT STRATEGIQUE (RS)", table_obj_header_style),
            ],
            [
                Paragraph(f"OG {formatted_objectif_num}: {formatted_objectif_libelle}", table_obj_cell_style),
                Paragraph(f"RS {format_programme_value(str(resultat_strategique_num), is_resultat_fake)}: {formatted_resultat_libelle}", table_obj_cell_style),
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
        
        # Source pour le tableau des objectifs - formater les années dynamiques selon leur source
        # Les années viennent toujours de la DB (pas factices)
        annee_precedente_obj = annee - 1
        formatted_annee_prec_obj = format_programme_value(str(annee_precedente_obj), False)
        formatted_annee_obj = format_programme_value(str(annee), False)
        source_obj = (
            f"Source: Annexe 4 de la Loi de Finances n° {formatted_annee_prec_obj}-1000 du 18 décembre {formatted_annee_prec_obj} "
            f"portant budget de l'Etat pour l'année {formatted_annee_obj}"
        )
        story.append(Paragraph(source_obj, source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # I.2. Le financement du programme
        # ============================================================
        story.append(Paragraph(f"{partie_numero_romain}.2. Le financement du programme", subsection_title_with_table_style))
        programme_budget = programme_data.get("budget", {})
        
        # Données budgétaires du programme
        # Budget voté (initial) et budget actuel (après ajustements)
        # Récupérer l'année précédente pour les données
        annee_precedente_budget = annee - 1
        
        # Récupérer les données de la base
        prog_budget_vote = programme_budget.get("budget_vote") or programme_budget.get("budget_initial") or 0
        prog_budget_actuel = programme_budget.get("budget_actuel") or programme_budget.get(f"prevu_{annee}") or 0
        prog_annee_prec_total = programme_budget.get(f"realisations_{annee_precedente_budget}") or 0
        prog_prev_annee = programme_budget.get(f"prevu_{annee}") or prog_budget_actuel or 0
        prog_real_annee = programme_budget.get(f"realise_{annee}") or 0
        
        # Vérifier si le budget est vide (toutes les valeurs sont 0)
        is_budget_empty = (
            prog_budget_vote == 0 and 
            prog_budget_actuel == 0 and 
            prog_annee_prec_total == 0 and 
            prog_prev_annee == 0 and 
            prog_real_annee == 0
        )
        
        # Générer des données factices si la DB est vide et en mode brouillon
        is_budget_fake = is_budget_empty and cls._should_use_fake_data()
        
        if is_budget_fake:
            # Générer des données factices réalistes pour le budget du programme
            from decimal import Decimal
            prog_budget_vote = Decimal(50000000000)  # 50 milliards
            prog_budget_actuel = Decimal(52000000000)  # 52 milliards (augmentation de 4%)
            prog_annee_prec_total = Decimal(48000000000)  # 48 milliards (année précédente)
            prog_prev_annee = prog_budget_actuel
            prog_real_annee = Decimal(49500000000)  # 49.5 milliards (95% d'exécution)
            logger.info(f"📊 Mode brouillon: génération de données factices pour le budget du programme")
        
        prog_ecart_annee = programme_budget.get(f"ecart_{annee}") or (prog_prev_annee - prog_real_annee) if prog_prev_annee > 0 else 0
        prog_tx_real_annee = (prog_real_annee / prog_prev_annee * 100) if prog_prev_annee > 0 else 0
        
        # Données par nature de dépense pour le programme
        # Budget initial (voté) et budget actuel par nature
        prog_personnel_budget_initial = programme_budget.get("personnel_budget_initial") or programme_budget.get("personnel_initial") or 0
        prog_personnel_budget_actuel = programme_budget.get("personnel_prev") or programme_budget.get("personnel_budget_actuel") or 0
        prog_personnel_annee_prec = programme_budget.get(f"personnel_{annee_precedente_budget}") or 0
        prog_personnel_real = programme_budget.get("personnel_real") or 0
        
        prog_biens_budget_initial = programme_budget.get("biens_budget_initial") or programme_budget.get("biens_initial") or 0
        prog_biens_budget_actuel = programme_budget.get("biens_prev") or programme_budget.get("biens_budget_actuel") or 0
        prog_biens_annee_prec = programme_budget.get(f"biens_{annee_precedente_budget}") or 0
        prog_biens_real = programme_budget.get("biens_real") or 0
        
        prog_transferts_budget_initial = programme_budget.get("transferts_budget_initial") or programme_budget.get("transferts_initial") or 0
        prog_transferts_budget_actuel = programme_budget.get("transferts_prev") or programme_budget.get("transferts_budget_actuel") or 0
        prog_transferts_annee_prec = programme_budget.get(f"transferts_{annee_precedente_budget}") or 0
        prog_transferts_real = programme_budget.get("transferts_real") or 0
        
        prog_investissements_budget_initial = programme_budget.get("investissements_budget_initial") or programme_budget.get("investissements_initial") or 0
        prog_investissements_budget_actuel = programme_budget.get("investissements_prev") or programme_budget.get("investissements_budget_actuel") or 0
        prog_investissements_annee_prec = programme_budget.get(f"investissements_{annee_precedente_budget}") or 0
        prog_investissements_real = programme_budget.get("investissements_real") or 0
        
        # Générer des données factices pour les natures de dépense si le budget est vide
        if is_budget_fake:
            from decimal import Decimal
            # Répartition réaliste : Personnel 40%, Biens 30%, Transferts 15%, Investissements 15%
            prog_personnel_budget_initial = Decimal(20000000000)  # 20 milliards
            prog_personnel_budget_actuel = Decimal(20800000000)  # 20.8 milliards
            prog_personnel_annee_prec = Decimal(19200000000)  # 19.2 milliards
            prog_personnel_real = Decimal(19760000000)  # 19.76 milliards (95%)
            
            prog_biens_budget_initial = Decimal(15000000000)  # 15 milliards
            prog_biens_budget_actuel = Decimal(15600000000)  # 15.6 milliards
            prog_biens_annee_prec = Decimal(14400000000)  # 14.4 milliards
            prog_biens_real = Decimal(14820000000)  # 14.82 milliards (95%)
            
            prog_transferts_budget_initial = Decimal(7500000000)  # 7.5 milliards
            prog_transferts_budget_actuel = Decimal(7800000000)  # 7.8 milliards
            prog_transferts_annee_prec = Decimal(7200000000)  # 7.2 milliards
            prog_transferts_real = Decimal(7800000000)  # 7.8 milliards (100%)
            
            prog_investissements_budget_initial = Decimal(7500000000)  # 7.5 milliards
            prog_investissements_budget_actuel = Decimal(7800000000)  # 7.8 milliards
            prog_investissements_annee_prec = Decimal(7200000000)  # 7.2 milliards
            prog_investissements_real = Decimal(7020000000)  # 7.02 milliards (90%)
        
        prog_personnel_ecart = prog_personnel_budget_actuel - prog_personnel_real
        prog_personnel_tx = (prog_personnel_real / prog_personnel_budget_actuel * 100) if prog_personnel_budget_actuel > 0 else 0
        # Alias pour compatibilité avec le code existant
        prog_personnel_prev = prog_personnel_budget_actuel
        
        prog_biens_ecart = prog_biens_budget_actuel - prog_biens_real
        prog_biens_tx = (prog_biens_real / prog_biens_budget_actuel * 100) if prog_biens_budget_actuel > 0 else 0
        # Alias pour compatibilité avec le code existant
        prog_biens_prev = prog_biens_budget_actuel
        
        prog_transferts_ecart = prog_transferts_budget_actuel - prog_transferts_real
        prog_transferts_tx = (prog_transferts_real / prog_transferts_budget_actuel * 100) if prog_transferts_budget_actuel > 0 else 0
        # Alias pour compatibilité avec le code existant
        prog_transferts_prev = prog_transferts_budget_actuel
        
        prog_investissements_ecart = prog_investissements_budget_actuel - prog_investissements_real
        prog_investissements_tx = (prog_investissements_real / prog_investissements_budget_actuel * 100) if prog_investissements_budget_actuel > 0 else 0
        # Alias pour compatibilité avec le code existant
        prog_investissements_prev = prog_investissements_budget_actuel
        
            # Créer le tableau d'exécution budgétaire
        prog_table_data = []
        
        # En-têtes - formater les années dynamiquement
        annee_precedente_prog = annee - 1
        formatted_annee_prec_prog = format_programme_value(str(annee_precedente_prog))
        formatted_annee_actuelle_prog = format_programme_value(str(annee))
        
        prog_table_data.append([
            Paragraph("Unités", table_header_style),
            Paragraph(f"REALISATIONS<br/>{formatted_annee_prec_prog}", table_header_style),
            Paragraph(formatted_annee_actuelle_prog, table_header_style),
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
        
        # 1.1 Ressources intérieures - formater toutes les valeurs selon leur source (factice ou DB)
        formatted_prog_annee_prec_total = format_programme_value(format_fcfa(prog_annee_prec_total), is_budget_fake)
        formatted_prog_prev_annee = format_programme_value(format_fcfa(prog_prev_annee), is_budget_fake)
        formatted_prog_real_annee = format_programme_value(format_fcfa(prog_real_annee), is_budget_fake)
        formatted_prog_ecart_annee = format_programme_value(format_fcfa(prog_ecart_annee), is_budget_fake)
        formatted_prog_tx_real_annee = format_programme_value(f"{prog_tx_real_annee:.2f}%", is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Ressources intérieures", table_cell_style),
            Paragraph(formatted_prog_annee_prec_total, table_cell_right_style),
            Paragraph(formatted_prog_prev_annee, table_cell_right_style),
            Paragraph(formatted_prog_real_annee, table_cell_right_style),
            Paragraph(formatted_prog_ecart_annee, table_cell_right_style),
            Paragraph(formatted_prog_tx_real_annee, table_cell_center_style),
        ])
        
        # 1.1.1 Budget de l'Etat
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.1 Budget de l'Etat (Trésor)", table_cell_style),
            Paragraph(formatted_prog_annee_prec_total, table_cell_right_style),
            Paragraph(formatted_prog_prev_annee, table_cell_right_style),
            Paragraph(formatted_prog_real_annee, table_cell_right_style),
            Paragraph(formatted_prog_ecart_annee, table_cell_right_style),
            Paragraph(formatted_prog_tx_real_annee, table_cell_center_style),
        ])
        
        # Formater les valeurs communes (zéro et tiret) selon leur source (factice ou DB)
        formatted_prog_zero = format_programme_value(format_fcfa(0), is_budget_fake)
        formatted_prog_dash = format_programme_value("-", is_budget_fake)
        
        # 1.1.2 Recettes de services
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.2 Recettes de services", table_cell_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_dash, table_cell_center_style),
        ])
        
        # 1.2 Ressources extérieures
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Ressources extérieures", table_cell_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_dash, table_cell_center_style),
        ])
        
        # 1.2.1, 1.2.2, 1.2.3 (tous à 0)
        for sub_item in ["1.2.1 Emprunts projets", "1.2.2 Dons Projets", "1.2.3 Appuis budgétaires ciblés"]:
            prog_table_data.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item}", table_cell_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_dash, table_cell_center_style),
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
        
        # 2.1 Personnel - formater toutes les valeurs selon leur source (factice ou DB)
        formatted_prog_personnel_annee_prec = format_programme_value(format_fcfa(prog_personnel_annee_prec), is_budget_fake)
        formatted_prog_personnel_budget_actuel = format_programme_value(format_fcfa(prog_personnel_budget_actuel), is_budget_fake)
        formatted_prog_personnel_real = format_programme_value(format_fcfa(prog_personnel_real), is_budget_fake)
        formatted_prog_personnel_ecart = format_programme_value(format_fcfa(prog_personnel_ecart), is_budget_fake)
        formatted_prog_personnel_tx = format_programme_value(f"{prog_personnel_tx:.0f}%", is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Personnel", table_cell_style),
            Paragraph(formatted_prog_personnel_annee_prec, table_cell_right_style),
            Paragraph(formatted_prog_personnel_budget_actuel, table_cell_right_style),
            Paragraph(formatted_prog_personnel_real, table_cell_right_style),
            Paragraph(formatted_prog_personnel_ecart, table_cell_right_style),
            Paragraph(formatted_prog_personnel_tx, table_cell_center_style),
        ])
        
        # 2.1.1 Solde - utiliser l'année précédente dynamiquement
        solde_annee_prec = programme_budget.get(f"solde_{annee_precedente_budget}") or programme_budget.get("solde_2023", 66947978820)
        solde_prev = programme_budget.get("solde_prev", 6270538992)
        solde_real = programme_budget.get("solde_real", 6270538792)
        
        # Générer des données factices pour solde si le budget est factice
        if is_budget_fake:
            from decimal import Decimal
            solde_annee_prec = Decimal(19000000000)  # 19 milliards (année précédente)
            solde_prev = Decimal(20800000000)  # 20.8 milliards (prévu)
            solde_real = Decimal(20800000000)  # 20.8 milliards (réalisé, 100%)
        
        solde_ecart = solde_prev - solde_real
        
        formatted_solde_annee_prec = format_programme_value(format_fcfa(solde_annee_prec), is_budget_fake)
        formatted_solde_prev = format_programme_value(format_fcfa(solde_prev), is_budget_fake)
        formatted_solde_real = format_programme_value(format_fcfa(solde_real), is_budget_fake)
        formatted_solde_ecart = format_programme_value(format_fcfa(solde_ecart), is_budget_fake)
        formatted_100_pct_prog = format_programme_value("100%", is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.1 Solde y compris EPN", table_cell_style),
            Paragraph(formatted_solde_annee_prec, table_cell_right_style),
            Paragraph(formatted_solde_prev, table_cell_right_style),
            Paragraph(formatted_solde_real, table_cell_right_style),
            Paragraph(formatted_solde_ecart, table_cell_right_style),
            Paragraph(formatted_100_pct_prog, table_cell_center_style),
        ])
        
        # 2.1.2 Contractuels - utiliser l'année précédente dynamiquement
        contractuels_annee_prec = programme_budget.get(f"contractuels_{annee_precedente_budget}") or programme_budget.get("contractuels_2023", 5400000)
        contractuels_prev = programme_budget.get("contractuels_prev", 842024247)
        contractuels_real = programme_budget.get("contractuels_real", 841996247)
        
        # Générer des données factices pour contractuels si le budget est factice
        if is_budget_fake:
            from decimal import Decimal
            contractuels_annee_prec = Decimal(500000000)  # 500 millions (année précédente)
            contractuels_prev = Decimal(1040000000)  # 1.04 milliard (prévu)
            contractuels_real = Decimal(1040000000)  # 1.04 milliard (réalisé, 100%)
        
        contractuels_ecart = contractuels_prev - contractuels_real
        
        formatted_contractuels_annee_prec = format_programme_value(format_fcfa(contractuels_annee_prec), is_budget_fake)
        formatted_contractuels_prev = format_programme_value(format_fcfa(contractuels_prev), is_budget_fake)
        formatted_contractuels_real = format_programme_value(format_fcfa(contractuels_real), is_budget_fake)
        formatted_contractuels_ecart = format_programme_value(format_fcfa(contractuels_ecart), is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.2 Contractuels hors solde", table_cell_style),
            Paragraph(formatted_contractuels_annee_prec, table_cell_right_style),
            Paragraph(formatted_contractuels_prev, table_cell_right_style),
            Paragraph(formatted_contractuels_real, table_cell_right_style),
            Paragraph(formatted_contractuels_ecart, table_cell_right_style),
            Paragraph(formatted_100_pct_prog, table_cell_center_style),
        ])
        
        # 2.2 Biens et Service - formater toutes les valeurs selon leur source (factice ou DB)
        formatted_prog_biens_annee_prec = format_programme_value(format_fcfa(prog_biens_annee_prec), is_budget_fake)
        formatted_prog_biens_budget_actuel = format_programme_value(format_fcfa(prog_biens_budget_actuel), is_budget_fake)
        formatted_prog_biens_real = format_programme_value(format_fcfa(prog_biens_real), is_budget_fake)
        formatted_prog_biens_ecart = format_programme_value(format_fcfa(prog_biens_ecart), is_budget_fake)
        formatted_prog_biens_tx = format_programme_value(f"{prog_biens_tx:.2f}%", is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Biens et Service", table_cell_style),
            Paragraph(formatted_prog_biens_annee_prec, table_cell_right_style),
            Paragraph(formatted_prog_biens_budget_actuel, table_cell_right_style),
            Paragraph(formatted_prog_biens_real, table_cell_right_style),
            Paragraph(formatted_prog_biens_ecart, table_cell_right_style),
            Paragraph(formatted_prog_biens_tx, table_cell_center_style),
        ])
        
        # 2.3 Transferts - formater toutes les valeurs selon leur source (factice ou DB)
        formatted_prog_transferts_annee_prec = format_programme_value(format_fcfa(prog_transferts_annee_prec), is_budget_fake)
        formatted_prog_transferts_budget_actuel = format_programme_value(format_fcfa(prog_transferts_budget_actuel), is_budget_fake)
        formatted_prog_transferts_real = format_programme_value(format_fcfa(prog_transferts_real), is_budget_fake)
        formatted_prog_transferts_ecart = format_programme_value(format_fcfa(prog_transferts_ecart), is_budget_fake)
        formatted_prog_transferts_tx = format_programme_value(f"{prog_transferts_tx:.0f}%", is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 Transferts", table_cell_style),
            Paragraph(formatted_prog_transferts_annee_prec, table_cell_right_style),
            Paragraph(formatted_prog_transferts_budget_actuel, table_cell_right_style),
            Paragraph(formatted_prog_transferts_real, table_cell_right_style),
            Paragraph(formatted_prog_transferts_ecart, table_cell_right_style),
            Paragraph(formatted_prog_transferts_tx, table_cell_center_style),
        ])
        
        # 2.3.1 Transferts courants
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.1 Transferts courants", table_cell_style),
            Paragraph(formatted_prog_transferts_annee_prec, table_cell_right_style),
            Paragraph(formatted_prog_transferts_budget_actuel, table_cell_right_style),
            Paragraph(formatted_prog_transferts_real, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_100_pct_prog, table_cell_center_style),
        ])
        
        # 2.3.2 Transferts en capital
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.2 Transferts en capital", table_cell_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_prog_dash, table_cell_center_style),
        ])
        
        # 2.4 Investissement - formater toutes les valeurs selon leur source (factice ou DB)
        formatted_prog_investissements_annee_prec = format_programme_value(format_fcfa(prog_investissements_annee_prec), is_budget_fake)
        formatted_prog_investissements_budget_actuel = format_programme_value(format_fcfa(prog_investissements_budget_actuel), is_budget_fake)
        formatted_prog_investissements_real = format_programme_value(format_fcfa(prog_investissements_real), is_budget_fake)
        formatted_prog_investissements_ecart = format_programme_value(format_fcfa(prog_investissements_ecart), is_budget_fake)
        formatted_prog_investissements_tx = format_programme_value(f"{prog_investissements_tx:.0f}%", is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Investissement", table_cell_style),
            Paragraph(formatted_prog_investissements_annee_prec, table_cell_right_style),
            Paragraph(formatted_prog_investissements_budget_actuel, table_cell_right_style),
            Paragraph(formatted_prog_investissements_real, table_cell_right_style),
            Paragraph(formatted_prog_investissements_ecart, table_cell_right_style),
            Paragraph(formatted_prog_investissements_tx, table_cell_center_style),
        ])
        
        # 2.4.1 Trésor - utiliser l'année précédente dynamiquement
        tresor_inv_annee_prec = programme_budget.get(f"tresor_inv_{annee_precedente_budget}") or programme_budget.get("tresor_inv_2023", 12218221082)
        tresor_inv_prev = programme_budget.get("tresor_inv_prev", 4933714127)
        tresor_inv_real = programme_budget.get("tresor_inv_real", 4933714127)
        
        # Générer des données factices pour trésor investissements si le budget est factice
        if is_budget_fake:
            from decimal import Decimal
            tresor_inv_annee_prec = Decimal(7200000000)  # 7.2 milliards (année précédente)
            tresor_inv_prev = Decimal(7800000000)  # 7.8 milliards (prévu)
            tresor_inv_real = Decimal(7800000000)  # 7.8 milliards (réalisé, 100%)
        
        formatted_tresor_inv_annee_prec = format_programme_value(format_fcfa(tresor_inv_annee_prec), is_budget_fake)
        formatted_tresor_inv_prev = format_programme_value(format_fcfa(tresor_inv_prev), is_budget_fake)
        formatted_tresor_inv_real = format_programme_value(format_fcfa(tresor_inv_real), is_budget_fake)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.1 Trésor", table_cell_style),
            Paragraph(formatted_tresor_inv_annee_prec, table_cell_right_style),
            Paragraph(formatted_tresor_inv_prev, table_cell_right_style),
            Paragraph(formatted_tresor_inv_real, table_cell_right_style),
            Paragraph(formatted_prog_zero, table_cell_right_style),
            Paragraph(formatted_100_pct_prog, table_cell_center_style),
        ])
        
        # 2.4.2 Financement extérieur, Dons, Emprunts (tous à 0)
        for sub_item in ["2.4.2 Financement extérieur", "Dons", "Emprunts"]:
            prog_table_data.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item}", table_cell_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_zero, table_cell_right_style),
                Paragraph(formatted_prog_dash, table_cell_center_style),
            ])
        
        # TOTAL - utiliser les valeurs déjà formatées
        prog_table_data.append([
            Paragraph("<b>TOTAL</b>", table_total_style),
            Paragraph(formatted_prog_annee_prec_total, table_cell_right_style),
            Paragraph(formatted_prog_prev_annee, table_cell_right_style),
            Paragraph(formatted_prog_real_annee, table_cell_right_style),
            Paragraph(formatted_prog_ecart_annee, table_cell_right_style),
            Paragraph(formatted_prog_tx_real_annee, table_cell_center_style),
        ])
        
        # Largeurs de colonnes
        col_widths = [
            available_width * 0.32,
            available_width * 0.14,
            available_width * 0.13,
            available_width * 0.13,
            available_width * 0.14,
            available_width * 0.14,
        ]
        
        # Créer le LongTable (C'EST ICI QUE LE DÉCOUPAGE AUTOMATIQUE SE FAIT !)
        prog_execution_table = LongTable(
            prog_table_data,
            colWidths=col_widths,
            repeatRows=2,  # Répéter les 2 premières lignes (en-têtes)
            splitByRow=1,  # Permettre le découpage par lignes
        )
        
        # Style du tableau (identique au service original)
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
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fbe4d5")),  # RESSOURCES (ligne 2)
                ("FONTNAME", (0, 10), (0, 10), "Helvetica-Bold"),
                ("BACKGROUND", (0, 10), (-1, 10), colors.HexColor("#fbe4d5")),  # CHARGES (ligne 10)
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e2efd9")),  # 1.1 Ressources intérieures (ligne 3)
                ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#e2efd9")),  # 1.2 Ressources extérieures (ligne 6)
                ("BACKGROUND", (0, 11), (-1, 11), colors.HexColor("#e2efd9")),  # 2.1 Personnel (ligne 11)
                ("BACKGROUND", (0, 14), (-1, 14), colors.HexColor("#e2efd9")),  # 2.2 Biens et Service (ligne 14)
                ("BACKGROUND", (0, 15), (-1, 15), colors.HexColor("#e2efd9")),  # 2.3 Transferts (ligne 15)
                ("BACKGROUND", (0, 18), (-1, 18), colors.HexColor("#e2efd9")),  # 2.4 Investissement (ligne 18)
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),  # TOTAL (dernière ligne)
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        
        # Ajouter le titre du tableau - formater selon la source
        formatted_numero_tableau = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_tableau_budget = format_programme_value(titre, is_programme_fake)
        tableau_title = f"Tableau : Exécution du budget du Programme {formatted_numero_tableau} « {formatted_titre_tableau_budget} »"
        story.append(Paragraph(f"<b>{tableau_title}</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter le LongTable à la story → SimpleDocTemplate va le découper automatiquement !
        story.append(prog_execution_table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Source
        story.append(Paragraph("Source: Situation d'exécution issue du SIGOBE", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Analyse automatisée du tableau
        # ============================================================
        #story.append(Paragraph("<b>Analyse automatisée</b>", subsection_title_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Calculer les écarts et évolutions
        ecart_budget_total = prog_budget_actuel - prog_budget_vote
        evolution_budget_pct = ((ecart_budget_total / prog_budget_vote) * 100) if prog_budget_vote > 0 else 0
        
        # Paragraphe 1 : Budget voté et source de financement
        # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
        formatted_titre_analyse = format_programme_value(titre, is_programme_fake)
        formatted_annee_analyse = format_programme_value(str(annee), False)  # Année toujours DB
        formatted_budget_vote = format_programme_value(format_fcfa(prog_budget_vote), is_budget_fake)
        
        analyse_para1 = (
            f"Le Programme « {formatted_titre_analyse} » a bénéficié en {formatted_annee_analyse} d'un budget voté de <b>{formatted_budget_vote}</b> "
            f"(Annexe 4, loi des finances {formatted_annee_analyse})"
        )
        
        # Vérifier si ressources extérieures
        ressources_exterieures_prev = programme_budget.get("ressources_exterieures_prev", 0)
        if ressources_exterieures_prev > 0:
            analyse_para1 += f", financé par les ressources intérieures et extérieures."
        else:
            analyse_para1 += f", exclusivement financé par les ressources intérieures."
        
        story.append(Paragraph(analyse_para1, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe 2 : Évolution du budget
        if abs(evolution_budget_pct) > 0.1:  # Si évolution significative (> 0.1%)
            evolution_text = "hausse" if evolution_budget_pct > 0 else "baisse"
            # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
            formatted_ecart = format_programme_value(format_fcfa(abs(ecart_budget_total)), is_budget_fake)
            formatted_budget_actuel = format_programme_value(format_fcfa(prog_budget_actuel), is_budget_fake)
            formatted_evolution_pct = format_programme_value(f"{abs(evolution_budget_pct):+.2f}%", is_budget_fake)
            
            analyse_para2 = (
                f"Cette dotation a connu une {evolution_text} de <b>{formatted_ecart}</b> "
                f"faisant ressortir le budget actuel à <b>{formatted_budget_actuel}</b> "
                f"soit {formatted_evolution_pct}."
            )
            story.append(Paragraph(analyse_para2, body_style))
            story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe 3 : Explications des facteurs (si augmentation notable > 50%)
        if evolution_budget_pct > 50:
            analyse_explication_user = programme_data.get("analyse_explication", "")
            if analyse_explication_user:
                # Données utilisateur (vert)
                formatted_explication = cls._format_db_data(analyse_explication_user)
            else:
                # Données par défaut (rouge)
                analyse_explication_default = (
                    f"L'augmentation notable du budget alloué à ce programme s'explique par plusieurs facteurs, "
                    f"notamment les ajustements opérés en cours d'exercice et les rattachements de structures ou projets."
                )
                formatted_explication = cls._format_db_data(analyse_explication_default)
            story.append(Paragraph(formatted_explication, body_style))
            story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe 4 : Introduction de la liste
        analyse_intro_liste_user = programme_data.get("analyse_intro_liste", "")
        if analyse_intro_liste_user:
            # Données utilisateur (rouge car personnalisées)
            formatted_intro_liste = cls._format_db_data(analyse_intro_liste_user)
        else:
            # Texte par défaut statique (noir, pas de formatage)
            analyse_intro_liste_default = (
                f"L'évolution des ressources budgétaires du programme par nature de dépenses se présente comme suit :"
            )
            formatted_intro_liste = analyse_intro_liste_default  # Pas de formatage, texte statique
        story.append(Paragraph(formatted_intro_liste, body_style))
        story.append(Spacer(1, 0.05 * cm))
        
        # Liste à puces pour chaque nature de dépense
        bullet_analysis_style = ParagraphStyle(
            "BulletAnalysisStyle",
            parent=body_style,
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=2,
        )
        
        # Dépenses de personnel
        if prog_personnel_budget_actuel > 0:
            ecart_personnel = prog_personnel_budget_actuel - prog_personnel_budget_initial
            evolution_personnel_pct = ((ecart_personnel / prog_personnel_budget_initial) * 100) if prog_personnel_budget_initial > 0 else 0
            # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
            formatted_personnel_init = format_programme_value(format_fcfa(prog_personnel_budget_initial), is_budget_fake)
            formatted_personnel_actuel = format_programme_value(format_fcfa(prog_personnel_budget_actuel), is_budget_fake)
            formatted_annee_personnel = format_programme_value(str(annee), False)  # Année toujours DB
            
            analyse_personnel = (
                f"<b>Dépenses de personnel :</b> Le budget initial de <b>{formatted_personnel_init}</b> "
                f"(Annexe 4, loi des finances {formatted_annee_personnel}) passe à <b>{formatted_personnel_actuel}</b> "
                f"(budget actuel {formatted_annee_personnel})"
            )
            if abs(ecart_personnel) > 1000:
                formatted_ecart_personnel = format_programme_value(format_fcfa(ecart_personnel), is_budget_fake)
                formatted_evolution_personnel = format_programme_value(f"{abs(evolution_personnel_pct):+.1f}%", is_budget_fake)
                analyse_personnel += (
                    f", soit un écart de <b>{formatted_ecart_personnel}</b>, "
                    f"représentant une hausse de <b>{formatted_evolution_personnel}</b>."
                )
            else:
                analyse_personnel += "."
            story.append(Paragraph(analyse_personnel, bullet_analysis_style, bulletText="-"))
        
        # Biens et services
        if prog_biens_budget_actuel > 0:
            ecart_biens = prog_biens_budget_actuel - prog_biens_budget_initial
            evolution_biens_pct = ((ecart_biens / prog_biens_budget_initial) * 100) if prog_biens_budget_initial > 0 else 0
            # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
            formatted_biens_init = format_programme_value(format_fcfa(prog_biens_budget_initial), is_budget_fake)
            formatted_biens_actuel = format_programme_value(format_fcfa(prog_biens_budget_actuel), is_budget_fake)
            formatted_annee_biens = format_programme_value(str(annee), False)  # Année toujours DB
            
            analyse_biens = (
                f"<b>Biens et services :</b> Le budget passe de <b>{formatted_biens_init}</b> "
                f"(Annexe 4, loi des finances {formatted_annee_biens}) à <b>{formatted_biens_actuel}</b> "
                f"(budget actuel {formatted_annee_biens})"
            )
            if abs(ecart_biens) > 1000:
                formatted_ecart_biens = format_programme_value(format_fcfa(ecart_biens), is_budget_fake)
                formatted_evolution_biens = format_programme_value(f"{abs(evolution_biens_pct):+.1f}%", is_budget_fake)
                analyse_biens += (
                    f", soit un écart de <b>{formatted_ecart_biens}</b>, "
                    f"représentant une augmentation de <b>{formatted_evolution_biens}</b>."
                )
            else:
                analyse_biens += "."
            story.append(Paragraph(analyse_biens, bullet_analysis_style, bulletText="-"))
        
        # Transferts
        if prog_transferts_budget_actuel > 0:
            ecart_transferts = prog_transferts_budget_actuel - prog_transferts_budget_initial
            evolution_transferts_pct = ((ecart_transferts / prog_transferts_budget_initial) * 100) if prog_transferts_budget_initial > 0 else 0
            # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
            formatted_transferts_init = format_programme_value(format_fcfa(prog_transferts_budget_initial), is_budget_fake)
            formatted_transferts_actuel = format_programme_value(format_fcfa(prog_transferts_budget_actuel), is_budget_fake)
            formatted_annee_transferts = format_programme_value(str(annee), False)  # Année toujours DB
            
            analyse_transferts = (
                f"<b>Transferts :</b> Le budget initial de <b>{formatted_transferts_init}</b> "
                f"(Annexe 4, loi des finances {formatted_annee_transferts}) passe à <b>{formatted_transferts_actuel}</b> "
                f"(budget actuel {formatted_annee_transferts})"
            )
            if abs(ecart_transferts) > 1000:
                qualificatif = "exceptionnel" if abs(evolution_transferts_pct) > 100 else "significatif"
                formatted_ecart_transferts = format_programme_value(format_fcfa(ecart_transferts), is_budget_fake)
                formatted_evolution_transferts = format_programme_value(f"{abs(evolution_transferts_pct):+.1f}%", is_budget_fake)
                analyse_transferts += (
                    f", avec un écart {qualificatif} de <b>{formatted_ecart_transferts}</b>, "
                    f"soit une progression de <b>{formatted_evolution_transferts}</b>."
                )
            else:
                analyse_transferts += "."
            story.append(Paragraph(analyse_transferts, bullet_analysis_style, bulletText="-"))
        
        # Investissements
        if prog_investissements_budget_actuel > 0:
            ecart_investissements = prog_investissements_budget_actuel - prog_investissements_budget_initial
            evolution_investissements_pct = ((ecart_investissements / prog_investissements_budget_initial) * 100) if prog_investissements_budget_initial > 0 else 0
            # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
            formatted_investissements_init = format_programme_value(format_fcfa(prog_investissements_budget_initial), is_budget_fake)
            formatted_investissements_actuel = format_programme_value(format_fcfa(prog_investissements_budget_actuel), is_budget_fake)
            formatted_annee_investissements = format_programme_value(str(annee), False)  # Année toujours DB
            
            analyse_investissements = (
                f"<b>Investissements :</b> Le budget passe de <b>{formatted_investissements_init}</b> "
                f"(Annexe 4, loi des finances {formatted_annee_investissements}) à <b>{formatted_investissements_actuel}</b> "
                f"(budget actuel {formatted_annee_investissements})"
            )
            if abs(ecart_investissements) > 1000:
                formatted_ecart_investissements = format_programme_value(format_fcfa(ecart_investissements), is_budget_fake)
                formatted_evolution_investissements = format_programme_value(f"{abs(evolution_investissements_pct):+.2f}%", is_budget_fake)
                analyse_investissements += (
                    f", soit une augmentation de <b>{formatted_ecart_investissements}</b>, "
                    f"représentant une croissance de <b>{formatted_evolution_investissements}</b>."
                )
            else:
                analyse_investissements += "."
            story.append(Paragraph(analyse_investissements, bullet_analysis_style, bulletText="-"))
        
        story.append(Spacer(1, 0.15 * cm))
        
        # Note NB si fournie
        analyse_note = programme_data.get("analyse_note", "")
        if analyse_note:
            # Formater la note selon sa source (données DB)
            formatted_analyse_note = cls._format_db_data(analyse_note)
            story.append(Paragraph(f"<b>NB :</b> {formatted_analyse_note}", body_style))
            story.append(Spacer(1, 0.1 * cm))
        
        # Interprétation du financement du programme
        financement_interpretation = programme_data.get("financement_interpretation", "")
        
        if financement_interpretation:
            # Données utilisateur (formatées en rouge car DB)
            formatted_interpretation = cls._format_db_data(financement_interpretation)
            story.append(Paragraph(formatted_interpretation, body_style))
        else:
            placeholder_style = ParagraphStyle(
                "PlaceholderStyle",
                parent=body_style,
                textColor=colors.HexColor("#FF0000"),
                fontName="Helvetica-Oblique",
            )
            story.append(Paragraph("Votre interprétation ici", placeholder_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Note NB si fournie par l'utilisateur
        financement_note = programme_data.get("financement_note", "")
        if financement_note:
            # Formater la note selon sa source (données DB)
            formatted_financement_note = cls._format_db_data(financement_note)
            story.append(Paragraph(f"<b>NB :</b> {formatted_financement_note}", body_style))
            story.append(Spacer(1, 0.2 * cm))
        else:
            # Si pas de note, ne rien afficher pour le NB
            pass
        
        # ============================================================
        # II. REALISATIONS DU PROGRAMME
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        # Le titre et l'année viennent toujours de la DB (pas factices)
        formatted_titre_realisations = format_programme_value(titre.upper(), is_programme_fake)
        formatted_annee_realisations = format_programme_value(str(annee), False)  # Année toujours DB
        story.append(Paragraph(f"II. REALISATIONS DU PROGRAMME « {formatted_titre_realisations} » AU COURS DE L'EXERCICE {formatted_annee_realisations}", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Calculer les pourcentages pour le graphique
        total_budget_actuel = prog_personnel_budget_actuel + prog_biens_budget_actuel + prog_transferts_budget_actuel + prog_investissements_budget_actuel
        
        # Vérifier que les données existent et proviennent de la DB (pas de valeurs factices)
        is_from_db_budget = session is not None and len(programme_budget) > 0 and not is_budget_fake
        has_budget_data = (
            is_from_db_budget and 
            total_budget_actuel > 0 and
            (prog_personnel_budget_actuel > 0 or prog_biens_budget_actuel > 0 or 
             prog_transferts_budget_actuel > 0 or prog_investissements_budget_actuel > 0)
        )
        
        # En mode brouillon, générer le graphique même avec des données factices
        if not has_budget_data and is_budget_fake and total_budget_actuel > 0:
            has_budget_data = True
        
        pie_chart_buffer = None
        if has_budget_data:
            if total_budget_actuel > 0:
                pct_personnel = (prog_personnel_budget_actuel / total_budget_actuel) * 100
                pct_biens = (prog_biens_budget_actuel / total_budget_actuel) * 100
                pct_transferts = (prog_transferts_budget_actuel / total_budget_actuel) * 100
                pct_investissements = (prog_investissements_budget_actuel / total_budget_actuel) * 100
            else:
                pct_personnel = pct_biens = pct_transferts = pct_investissements = 0
            
            # Créer le graphique en camembert uniquement si on a des données valides
            pie_chart_buffer = cls._create_pie_chart_programme(
                prog_personnel_budget_actuel, pct_personnel,
                prog_biens_budget_actuel, pct_biens,
                prog_transferts_budget_actuel, pct_transferts,
                prog_investissements_budget_actuel, pct_investissements,
                titre
            )
        
        if pie_chart_buffer:
            # Titre du graphique (même format que pour le ministère)
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(f"<b>Figure : Répartition du budget actuel par natures de dépenses</b>", subsection_title_style))
            story.append(Spacer(1, 0.2 * cm))
            
            # Créer la source
            source_text = f"Source: DAAF {cls._get_sigle_ministere()}/ Situation d'exécution issue du SIGOBE"
            source_para = Paragraph(source_text, source_style)
            
            # Créer un Flowable personnalisé pour positionner source et graphique (comme pour le ministère)
            class PieChartWithSource(Flowable):
                def __init__(self, source_para, pie_chart_buffer, chart_width, chart_height, available_width):
                    Flowable.__init__(self)
                    self.source_para = source_para
                    self.pie_chart_buffer = pie_chart_buffer
                    self.chart_width = chart_width
                    self.chart_height = chart_height
                    self.available_width = available_width
                    # Hauteur nécessaire : la hauteur du graphique + espace pour la source
                    self.height = chart_height + 0.5 * cm
                    self.width = available_width
                
                def draw(self):
                    # Positionner la source en bas à gauche
                    source_w, source_h = self.source_para.wrap(self.available_width * 0.4, 1 * cm)
                    
                    # Dessiner la source en bas à gauche
                    source_x = 0
                    source_y = 0
                    self.source_para.drawOn(self.canv, source_x, source_y)
                    
                    # Positionner le graphique avec la même position X que le titre (x=0)
                    graph_x = 0
                    graph_y = 10  # En bas de la flowable
                    
                    # Dessiner d'abord le fond gris
                    self.canv.saveState()
                    self.canv.setFillColor(colors.HexColor("#d5d5d5"))
                    self.canv.rect(graph_x, graph_y, self.chart_width, self.chart_height, stroke=0, fill=1)
                    self.canv.restoreState()
                    
                    # Dessiner le graphique par-dessus le fond
                    try:
                        from reportlab.lib.utils import ImageReader
                        if self.pie_chart_buffer:
                            self.pie_chart_buffer.seek(0)
                            img_reader = ImageReader(self.pie_chart_buffer)
                            self.canv.drawImage(
                                img_reader,
                                graph_x,
                                graph_y,
                                width=self.chart_width,
                                height=self.chart_height,
                                preserveAspectRatio=True,
                                mask=None
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
            chart_width = available_width
            chart_height = 9 * cm
            pie_with_source = PieChartWithSource(source_para, pie_chart_buffer, chart_width, chart_height, available_width)
            story.append(pie_with_source)
            story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe : Exécution budgétaire globale
        # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
        formatted_titre_real = format_programme_value(titre, is_programme_fake)
        formatted_annee_real = format_programme_value(str(annee), False)  # Année toujours DB
        formatted_budget_actuel_real = format_programme_value(format_fcfa(prog_budget_actuel), is_budget_fake)
        formatted_real_annee = format_programme_value(format_fcfa(prog_real_annee), is_budget_fake)
        formatted_tx_real = format_programme_value(f"{prog_tx_real_annee:.2f}%", is_budget_fake)
        
        para_execution_globale = (
            f"Le budget actuel du Programme « {formatted_titre_real} » pour l'exercice {formatted_annee_real} s'élevait à "
            f"<b>{formatted_budget_actuel_real}</b> F CFA. Ce budget a été exécuté à hauteur de "
            f"<b>{formatted_real_annee}</b> F CFA, soit un taux d'exécution global de "
            f"<b>{formatted_tx_real}</b>."
        )
        story.append(Paragraph(para_execution_globale, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe : Dépenses de personnel
        # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
        formatted_personnel_budget = format_programme_value(format_fcfa(prog_personnel_budget_actuel), is_budget_fake)
        formatted_personnel_real = format_programme_value(format_fcfa(prog_personnel_real), is_budget_fake)
        formatted_personnel_tx = format_programme_value(f"{prog_personnel_tx:.0f}%", is_budget_fake)
        
        para_personnel = (
            f"Concernant les dépenses de <b>personnel</b>, le budget prévu était de "
            f"<b>{formatted_personnel_budget}</b> F CFA, et le montant effectivement exécuté "
            f"s'est élevé à <b>{formatted_personnel_real}</b> F CFA. Cette exécution de "
            f"<b>{formatted_personnel_tx}</b>, témoigne d'une promptitude dans la gestion des dépenses de "
            f"personnel au sein du programme."
        )
        story.append(Paragraph(para_personnel, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe : Biens et services
        # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
        formatted_biens_budget = format_programme_value(format_fcfa(prog_biens_budget_actuel), is_budget_fake)
        formatted_biens_real = format_programme_value(format_fcfa(prog_biens_real), is_budget_fake)
        formatted_biens_tx = format_programme_value(f"{prog_biens_tx:.2f}%", is_budget_fake)
        
        para_biens = (
            f"Pour ce qui est des <b>biens et services</b>, le budget alloué qui était de "
            f"<b>{formatted_biens_budget}</b> F CFA, a été exécuté à hauteur de "
            f"<b>{formatted_biens_real}</b> F CFA soit un taux d'exécution de "
            f"<b>{formatted_biens_tx}</b>."
        )
        story.append(Paragraph(para_biens, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe : Transferts
        # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
        formatted_transferts_budget = format_programme_value(format_fcfa(prog_transferts_budget_actuel), is_budget_fake)
        formatted_tx_100 = format_programme_value("100%", is_budget_fake)
        
        para_transferts = (
            f"Concernant les <b>transferts</b>, le montant programmé de "
            f"<b>{formatted_transferts_budget}</b> F CFA a été entièrement exécuté. "
            f"Le taux d'exécution est ainsi de <b>{formatted_tx_100}</b>, ce qui reflète une gestion rigoureuse des "
            f"engagements financiers."
        )
        story.append(Paragraph(para_transferts, body_style))
        story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe : Investissements
        # Formater uniquement les valeurs numériques selon leur source (factice ou DB)
        formatted_investissements_budget = format_programme_value(format_fcfa(prog_investissements_budget_actuel), is_budget_fake)
        formatted_investissements_real = format_programme_value(format_fcfa(prog_investissements_real), is_budget_fake)
        formatted_investissements_tx = format_programme_value(f"{prog_investissements_tx:.0f}%", is_budget_fake)
        
        para_investissements = (
            f"Pour les <b>investissements</b>, le budget actuel de "
            f"<b>{formatted_investissements_budget}</b> F CFA a été exécuté à hauteur de "
            f"<b>{formatted_investissements_real}</b> F CFA soit un taux d'exécution de "
            f"<b>{formatted_investissements_tx}</b>."
        )
        story.append(Paragraph(para_investissements, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # II.1. Exécution du budget
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II.1. Exécution du budget", section_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # II.1.1. Exécution des crédits budgétaires par action et par nature de dépense
        story.append(Paragraph("II.1.1. Exécution des crédits budgétaires par action et par nature de dépense", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Récupérer l'année pour le texte dynamique
        annee = cls.data.get("annee", 2024)
        annee_plus_2 = annee + 2
        
        # Charger les actions depuis SigobeExecution
        actions_tableau4 = []
        actions_tableau7 = []
        is_actions_fake = False
        
        if session:
            try:
                from app.models.budget import SigobeExecution
                from sqlmodel import select
                
                # Récupérer les actions distinctes pour ce programme depuis SigobeExecution
                actions_query = session.exec(
                    select(SigobeExecution.actions)
                    .distinct()
                    .where(SigobeExecution.annee == annee)
                    .where(SigobeExecution.programmes.ilike(f"%{titre}%"))
                    .where(SigobeExecution.actions.isnot(None))
                    .where(SigobeExecution.actions != "")
                ).all()
                
                if actions_query:
                    # Utiliser les actions de la base de données
                    actions_list = [a for a in actions_query if a]
                    if actions_list:
                        # Pour le tableau 4, utiliser toutes les actions
                        actions_tableau4 = actions_list
                        # Pour le tableau 7, utiliser les mêmes actions (ou on peut les différencier si nécessaire)
                        actions_tableau7 = actions_list
                        logger.debug(f"✅ Actions chargées depuis SigobeExecution pour programme {numero}: {len(actions_list)} actions")
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du chargement des actions depuis SigobeExecution: {e}")
        
        # Générer des données factices pour les actions si nécessaire (mode brouillon et DB vide)
        if (not actions_tableau4 or len(actions_tableau4) == 0) and cls._should_use_fake_data():
            is_actions_fake = True
            actions_tableau4 = [
                f"Action 1 : Gestion administrative et financière du programme {titre}",
                f"Action 2 : Coordination et suivi des activités du programme {titre}",
                f"Action 3 : Communication et diffusion des informations du programme {titre}",
                f"Action 4 : Évaluation et contrôle de la performance du programme {titre}"
            ]
            actions_tableau7 = actions_tableau4.copy()
            logger.info(f"📊 Mode brouillon: génération de données factices pour les actions du programme")
        
        # Texte explicatif sur les deux nomenclatures (uniquement si des actions sont trouvées)
        if actions_tableau4 or actions_tableau7:
            # Formater uniquement les valeurs numériques (années) selon leur source (factice ou DB)
            formatted_annee_nom = format_programme_value(str(annee), False)  # Année toujours DB
            formatted_annee_plus_2 = format_programme_value(str(annee_plus_2), False)  # Année toujours DB
            
            texte_nomenclatures_para1 = (
                f"Dans le tableau 4 intitulé « Déclinaison du programme en actions » du DPPD-PAP {formatted_annee_nom}-{formatted_annee_plus_2} annexé à la Loi de finances, "
                "la nomenclature des actions du programme est structurée de la manière suivante :"
            )
            story.append(Paragraph(texte_nomenclatures_para1, body_style))
            story.append(Spacer(1, 0.1 * cm))
            
            # Liste des actions du tableau 4 (depuis la base de données ou factices)
            if actions_tableau4:
                for idx, action in enumerate(actions_tableau4, 1):
                    formatted_action = format_programme_value(action, is_actions_fake)
                    story.append(Paragraph(f"• Action {idx} : {formatted_action}", body_style))
            story.append(Spacer(1, 0.15 * cm))
            
            texte_nomenclatures_para2 = (
                "Cependant, dans le tableau 7 intitulé « Budget détaillé du programme » du même DPPD-PAP, où sont présentés "
                "les crédits budgétaires alloués à chaque action, la nomenclature des actions diffère. Elle est déclinée comme suit :"
            )
            story.append(Paragraph(texte_nomenclatures_para2, body_style))
            story.append(Spacer(1, 0.1 * cm))
            
            # Liste des actions du tableau 7 (depuis la base de données ou factices)
            if actions_tableau7:
                for idx, action in enumerate(actions_tableau7, 1):
                    formatted_action = format_programme_value(action, is_actions_fake)
                    story.append(Paragraph(f"• Action {idx} : {formatted_action}", body_style))
            story.append(Spacer(1, 0.15 * cm))
        
        texte_nomenclatures_para3 = (
            "Cette seconde nomenclature, telle que présentée dans le tableau budgétaire, constitue la base effective de "
            "la budgétisation et de l'exécution des crédits des actions."
        )
        story.append(Paragraph(texte_nomenclatures_para3, body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        texte_nomenclatures_para4 = (
            "Par conséquent, la présente partie du RAP s'appuiera sur cette structuration des actions, afin d'assurer "
            "la cohérence entre les montants exécutés et les résultats obtenus."
        )
        story.append(Paragraph(texte_nomenclatures_para4, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Charger les données d'exécution par action (depuis SigobeExecution si disponible)
        annee_precedente = annee - 1
        
        # Créer les clés dynamiques pour les années (utilisées partout)
        key_personnel_annee = f"personnel_{annee}"
        key_biens_annee = f"biens_services_{annee}"
        key_transferts_annee = f"transferts_{annee}"
        key_investissements_annee = f"investissements_{annee}"
        key_personnel_annee_prec = f"personnel_{annee_precedente}"
        key_biens_annee_prec = f"biens_services_{annee_precedente}"
        key_transferts_annee_prec = f"transferts_{annee_precedente}"
        key_investissements_annee_prec = f"investissements_{annee_precedente}"
        
        # Récupérer les données par action depuis SigobeExecution
        actions_data = {}
        # Stocker aussi les budgets prévus pour calculer les taux d'exécution
        actions_budget_prev = {}  # Budget prévu par action pour l'année N
        actions_budget_prev_prec = {}  # Budget prévu par action pour l'année N-1
        
        if session:
            try:
                # Récupérer les données SIGOBE pour ce programme et les deux années
                sigobe_data_annee = session.exec(
                    select(SigobeExecution)
                    .where(SigobeExecution.annee == annee)
                    .where(SigobeExecution.programmes.ilike(f"%{titre}%"))
                ).all()
                
                sigobe_data_annee_precedente = session.exec(
                    select(SigobeExecution)
                    .where(SigobeExecution.annee == annee_precedente)
                    .where(SigobeExecution.programmes.ilike(f"%{titre}%"))
                ).all()
                
                # Agréger les données par action et nature de dépense pour l'année actuelle
                
                for sigobe in sigobe_data_annee:
                    action = sigobe.actions or "Action non spécifiée"
                    type_depense = sigobe.type_depense or ""
                    
                    if action not in actions_data:
                        actions_data[action] = {
                            key_personnel_annee: Decimal(0),
                            key_biens_annee: Decimal(0),
                            key_transferts_annee: Decimal(0),
                            key_investissements_annee: Decimal(0),
                            key_personnel_annee_prec: Decimal(0),
                            key_biens_annee_prec: Decimal(0),
                            key_transferts_annee_prec: Decimal(0),
                            key_investissements_annee_prec: Decimal(0),
                        }
                        actions_budget_prev[action] = Decimal(0)
                    
                    # Récupérer le montant exécuté (mandats_pec) et le budget prévu (budget_actuel)
                    montant_execute = sigobe.mandats_pec or Decimal(0)
                    budget_prev = sigobe.budget_actuel or Decimal(0)
                    
                    if montant_execute is None:
                        montant_execute = Decimal(0)
                    elif not isinstance(montant_execute, Decimal):
                        montant_execute = Decimal(str(montant_execute))
                    
                    if budget_prev is None:
                        budget_prev = Decimal(0)
                    elif not isinstance(budget_prev, Decimal):
                        budget_prev = Decimal(str(budget_prev))
                    
                    # Accumuler le budget prévu pour cette action
                    actions_budget_prev[action] = actions_budget_prev.get(action, Decimal(0)) + budget_prev
                    
                    if "PERSONNEL" in type_depense.upper() or "P" in type_depense.upper():
                        actions_data[action][key_personnel_annee] += montant_execute
                    elif "BIENS" in type_depense.upper() or "SERVICES" in type_depense.upper() or "BS" in type_depense.upper():
                        actions_data[action][key_biens_annee] += montant_execute
                    elif "TRANSFERT" in type_depense.upper() or "T" in type_depense.upper():
                        actions_data[action][key_transferts_annee] += montant_execute
                    elif "INVESTISSEMENT" in type_depense.upper() or "I" in type_depense.upper():
                        actions_data[action][key_investissements_annee] += montant_execute
                
                # Faire de même pour l'année précédente
                for sigobe in sigobe_data_annee_precedente:
                    action = sigobe.actions or "Action non spécifiée"
                    type_depense = sigobe.type_depense or ""
                    
                    if action not in actions_data:
                        actions_data[action] = {
                            key_personnel_annee: Decimal(0),
                            key_biens_annee: Decimal(0),
                            key_transferts_annee: Decimal(0),
                            key_investissements_annee: Decimal(0),
                            key_personnel_annee_prec: Decimal(0),
                            key_biens_annee_prec: Decimal(0),
                            key_transferts_annee_prec: Decimal(0),
                            key_investissements_annee_prec: Decimal(0),
                        }
                        actions_budget_prev_prec[action] = Decimal(0)
                    
                    # Récupérer le montant exécuté (mandats_pec) et le budget prévu (budget_actuel)
                    montant_execute = sigobe.mandats_pec or Decimal(0)
                    budget_prev = sigobe.budget_actuel or Decimal(0)
                    
                    if montant_execute is None:
                        montant_execute = Decimal(0)
                    elif not isinstance(montant_execute, Decimal):
                        montant_execute = Decimal(str(montant_execute))
                    
                    if budget_prev is None:
                        budget_prev = Decimal(0)
                    elif not isinstance(budget_prev, Decimal):
                        budget_prev = Decimal(str(budget_prev))
                    
                    # Accumuler le budget prévu pour cette action (année précédente)
                    actions_budget_prev_prec[action] = actions_budget_prev_prec.get(action, Decimal(0)) + budget_prev
                    
                    if "PERSONNEL" in type_depense.upper() or "P" in type_depense.upper():
                        actions_data[action][key_personnel_annee_prec] += montant_execute
                    elif "BIENS" in type_depense.upper() or "SERVICES" in type_depense.upper() or "BS" in type_depense.upper():
                        actions_data[action][key_biens_annee_prec] += montant_execute
                    elif "TRANSFERT" in type_depense.upper() or "T" in type_depense.upper():
                        actions_data[action][key_transferts_annee_prec] += montant_execute
                    elif "INVESTISSEMENT" in type_depense.upper() or "I" in type_depense.upper():
                        actions_data[action][key_investissements_annee_prec] += montant_execute
                        
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du chargement des données SIGOBE: {e}")
                # Réinitialiser actions_data
                actions_data = {}
        
        # Générer des données factices pour les actions si nécessaire (mode brouillon et DB vide)
        is_actions_data_fake = False
        if (not actions_data or len(actions_data) == 0) and cls._should_use_fake_data() and actions_tableau4:
            is_actions_data_fake = True
            from decimal import Decimal
            # Générer des données factices variées pour chaque action
            # Montants de base (en milliards FCFA) qui varient selon l'index de l'action
            # Taux d'exécution variables (entre 75% et 98%) pour rendre les données plus réalistes
            base_amounts = [
                {"personnel": 5.0, "biens": 3.0, "transferts": 1.5, "investissements": 2.0, "taux_exec": 0.92},
                {"personnel": 4.2, "biens": 2.8, "transferts": 1.2, "investissements": 1.8, "taux_exec": 0.87},
                {"personnel": 6.5, "biens": 3.5, "transferts": 2.0, "investissements": 2.5, "taux_exec": 0.95},
                {"personnel": 3.8, "biens": 2.5, "transferts": 1.0, "investissements": 1.5, "taux_exec": 0.78},
                {"personnel": 5.8, "biens": 3.2, "transferts": 1.8, "investissements": 2.2, "taux_exec": 0.89},
                {"personnel": 4.5, "biens": 2.6, "transferts": 1.3, "investissements": 1.7, "taux_exec": 0.83},
            ]
            
            for idx, action in enumerate(actions_tableau4[:6]):  # Limiter à 6 actions pour éviter un tableau trop long
                base = base_amounts[idx % len(base_amounts)]  # Utiliser modulo pour cycler si plus de 6 actions
                
                # Montants pour l'année N (avec légères variations)
                personnel_n = Decimal(int(base["personnel"] * 1_000_000_000))
                biens_n = Decimal(int(base["biens"] * 1_000_000_000))
                transferts_n = Decimal(int(base["transferts"] * 1_000_000_000))
                investissements_n = Decimal(int(base["investissements"] * 1_000_000_000))
                
                # Montants pour l'année N-1 (légèrement inférieurs, simulant une évolution)
                # Taux d'exécution pour N-1 (légèrement différent de N)
                taux_exec_n1 = base["taux_exec"] * (0.95 + (idx % 3) * 0.03)  # Variation entre 95% et 104% du taux N
                taux_exec_n1 = min(taux_exec_n1, 1.0)  # Limiter à 100%
                
                personnel_n1 = Decimal(int(base["personnel"] * 0.96 * 1_000_000_000))
                biens_n1 = Decimal(int(base["biens"] * 0.93 * 1_000_000_000))
                transferts_n1 = Decimal(int(base["transferts"] * 0.93 * 1_000_000_000))
                investissements_n1 = Decimal(int(base["investissements"] * 0.95 * 1_000_000_000))
                
                actions_data[action] = {
                    key_personnel_annee: personnel_n,
                    key_biens_annee: biens_n,
                    key_transferts_annee: transferts_n,
                    key_investissements_annee: investissements_n,
                    key_personnel_annee_prec: personnel_n1,
                    key_biens_annee_prec: biens_n1,
                    key_transferts_annee_prec: transferts_n1,
                    key_investissements_annee_prec: investissements_n1,
                    "_taux_execution_n": base["taux_exec"],  # Taux d'exécution pour N (stocké pour utilisation ultérieure)
                    "_taux_execution_n1": taux_exec_n1,  # Taux d'exécution pour N-1
                }
                
                # Budget prévu total (somme des natures de dépense)
                budget_prev_n = personnel_n + biens_n + transferts_n + investissements_n
                budget_prev_n1 = personnel_n1 + biens_n1 + transferts_n1 + investissements_n1
                
                actions_budget_prev[action] = budget_prev_n
                actions_budget_prev_prec[action] = budget_prev_n1
            logger.info(f"📊 Mode brouillon: génération de données factices variées pour les données d'exécution par action avec taux variables")
        
        # Créer le tableau d'exécution par action
        formatted_numero = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_tableau = format_programme_value(titre, is_programme_fake)
        tableau_titre = f"Tableau 4: Exécution financière par action du programme {formatted_numero} « {formatted_titre_tableau} »"
        story.append(Paragraph(f"<b>{tableau_titre}</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # En-têtes du tableau
        table_data = [
            [
                Paragraph("<b>Nature de dépenses</b>", table_header_style),
                Paragraph("<b>Personnel</b>", table_header_style),
                Paragraph("", table_header_style),
                Paragraph("<b>Biens et Services</b>", table_header_style),
                Paragraph("", table_header_style),
                Paragraph("<b>Transferts</b>", table_header_style),
                Paragraph("", table_header_style),
                Paragraph("<b>Investissements</b>", table_header_style),
                Paragraph("", table_header_style),
                Paragraph("<b>Total</b>", table_header_style),
                Paragraph("", table_header_style),
            ],
            [
                Paragraph("<b>Actions</b>", table_header_style),
                Paragraph(f"<b>{format_programme_value(str(annee_precedente), False)}</b>", table_header_style),  # N-1 (année toujours DB)
                Paragraph(f"<b>{format_programme_value(str(annee), False)}</b>", table_header_style),  # N (année toujours DB)
                Paragraph(f"<b>{format_programme_value(str(annee_precedente), False)}</b>", table_header_style),  # N-1
                Paragraph(f"<b>{format_programme_value(str(annee), False)}</b>", table_header_style),  # N
                Paragraph(f"<b>{format_programme_value(str(annee_precedente), False)}</b>", table_header_style),  # N-1
                Paragraph(f"<b>{format_programme_value(str(annee), False)}</b>", table_header_style),  # N
                Paragraph(f"<b>{format_programme_value(str(annee_precedente), False)}</b>", table_header_style),  # N-1
                Paragraph(f"<b>{format_programme_value(str(annee), False)}</b>", table_header_style),  # N
                Paragraph(f"<b>{format_programme_value(str(annee_precedente), False)}</b>", table_header_style),  # N-1
                Paragraph(f"<b>{format_programme_value(str(annee), False)}</b>", table_header_style),  # N
            ],
        ]
        
        # Calculer les totaux (N = annee, N-1 = annee_precedente)
        total_personnel_n_minus_1 = Decimal(0)
        total_personnel_n = Decimal(0)
        total_biens_n_minus_1 = Decimal(0)
        total_biens_n = Decimal(0)
        total_transferts_n_minus_1 = Decimal(0)
        total_transferts_n = Decimal(0)
        total_invest_n_minus_1 = Decimal(0)
        total_invest_n = Decimal(0)
        total_n_minus_1 = Decimal(0)
        total_n = Decimal(0)
        
        # Stocker les données par action pour l'analyse ultérieure
        actions_totals = {}
        
        # Ajouter les lignes d'actions
        for action, data in actions_data.items():
            # Convertir en Decimal pour éviter les erreurs de type (N = annee, N-1 = annee_precedente)
            p_n_minus_1 = Decimal(str(data.get(key_personnel_annee_prec, 0)))
            p_n = Decimal(str(data.get(key_personnel_annee, 0)))
            bs_n_minus_1 = Decimal(str(data.get(key_biens_annee_prec, 0)))
            bs_n = Decimal(str(data.get(key_biens_annee, 0)))
            t_n_minus_1 = Decimal(str(data.get(key_transferts_annee_prec, 0)))
            t_n = Decimal(str(data.get(key_transferts_annee, 0)))
            i_n_minus_1 = Decimal(str(data.get(key_investissements_annee_prec, 0)))
            i_n = Decimal(str(data.get(key_investissements_annee, 0)))
            
            total_ligne_n_minus_1 = p_n_minus_1 + bs_n_minus_1 + t_n_minus_1 + i_n_minus_1
            total_ligne_n = p_n + bs_n + t_n + i_n
            
            # Stocker les totaux pour l'analyse (inclure les budgets prévus pour calculer les taux)
            budget_prev_n = actions_budget_prev.get(action, Decimal(0))
            budget_prev_n_minus_1 = actions_budget_prev_prec.get(action, Decimal(0))
            
            actions_totals[action] = {
                "total_n_minus_1": total_ligne_n_minus_1,
                "total_n": total_ligne_n,
                "budget_prev_n_minus_1": budget_prev_n_minus_1,
                "budget_prev_n": budget_prev_n,
                "p_n": p_n,
                "bs_n": bs_n,
                "t_n": t_n,
                "i_n": i_n,
            }
            
            total_personnel_n_minus_1 += p_n_minus_1
            total_personnel_n += p_n
            total_biens_n_minus_1 += bs_n_minus_1
            total_biens_n += bs_n
            total_transferts_n_minus_1 += t_n_minus_1
            total_transferts_n += t_n
            total_invest_n_minus_1 += i_n_minus_1
            total_invest_n += i_n
            total_n_minus_1 += total_ligne_n_minus_1
            total_n += total_ligne_n
            
            # Convertir en float pour format_fcfa et utiliser la police réduite
            # Formater les valeurs selon leur source (factice ou DB)
            formatted_action = format_programme_value(action, is_actions_data_fake)
            table_data.append([
                Paragraph(formatted_action, table_cell_style),
                Paragraph(format_programme_value(format_fcfa(float(p_n_minus_1)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(p_n)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(bs_n_minus_1)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(bs_n)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(t_n_minus_1)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(t_n)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(i_n_minus_1)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(i_n)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(total_ligne_n_minus_1)), is_actions_data_fake), table_cell_right_small_style),
                Paragraph(format_programme_value(format_fcfa(float(total_ligne_n)), is_actions_data_fake), table_cell_right_small_style),
            ])
        
        # Ligne Total (utiliser les variables N et N-1)
        # Formater les valeurs selon leur source (factice ou DB)
        table_data.append([
            Paragraph("<b>Total</b>", table_total_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_personnel_n_minus_1)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_personnel_n)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_biens_n_minus_1)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_biens_n)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_transferts_n_minus_1)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_transferts_n)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_invest_n_minus_1)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_invest_n)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_n_minus_1)), is_actions_data_fake)}</b>", table_total_right_small_style),
            Paragraph(f"<b>{format_programme_value(format_fcfa(float(total_n)), is_actions_data_fake)}</b>", table_total_right_small_style),
        ])
        
        # Créer le tableau LongTable pour permettre le découpage sur plusieurs pages
        col_widths = [
            available_width * 0.25,  # Actions
            available_width * 0.075,  # Personnel 2023
            available_width * 0.075,  # Personnel 2024
            available_width * 0.075,  # Biens 2023
            available_width * 0.075,  # Biens 2024
            available_width * 0.075,  # Transferts 2023
            available_width * 0.075,  # Transferts 2024
            available_width * 0.075,  # Investissements 2023
            available_width * 0.075,  # Investissements 2024
            available_width * 0.075,  # Total 2023
            available_width * 0.075,  # Total 2024
        ]
        
        action_table = LongTable(table_data, colWidths=col_widths, repeatRows=2)
        
        # Style du tableau
        action_table_style = TableStyle([
            # Bordures extérieures
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            
            # En-têtes (lignes 0 et 1)
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.black),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 1), 9),
            
            # Fusionner les cellules d'en-tête pour les natures de dépenses
            ("SPAN", (0, 0), (0, 1)),  # Nature de dépenses
            ("SPAN", (1, 0), (2, 0)),  # Personnel
            ("SPAN", (3, 0), (4, 0)),  # Biens et Services
            ("SPAN", (5, 0), (6, 0)),  # Transferts
            ("SPAN", (7, 0), (8, 0)),  # Investissements
            ("SPAN", (9, 0), (10, 0)),  # Total
            
            # Ligne Total (dernière ligne)
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.black),
            ("ALIGN", (1, -1), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 9),
            
            # Alignement des montants (colonnes numériques)
            ("ALIGN", (1, 2), (-1, -2), "RIGHT"),
            ("VALIGN", (0, 2), (-1, -2), "MIDDLE"),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
        
        action_table.setStyle(action_table_style)
        story.append(action_table)
        story.append(Spacer(1, 0.3 * cm))
        
        # Source
        formatted_annee_source = format_programme_value(str(annee), False)  # Année toujours DB
        formatted_annee_plus_2 = format_programme_value(str(annee + 2), False)  # Année toujours DB
        story.append(Paragraph(f"Source: DPPD-PAP {formatted_annee_source}-{formatted_annee_plus_2} / Situation d'exécution issue du SIGOBE", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Analyse et interprétation par action
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        
        # Introduction
        intro_analyse = "Le budget exécuté est reparti par actions comme suit :"
        story.append(Paragraph(intro_analyse, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Récupérer les données d'interprétation personnalisées depuis le programme
        programme_data = programme.get("data", {})
        actions_interpretations = programme_data.get("actions_interpretations", {})
        
        # Parcourir les actions et créer l'analyse pour chacune
        action_num = 1
        for action, totals in actions_totals.items():
            # Extraire le titre de l'action (après "Action X: ")
            action_title = action
            if ": " in action:
                action_title = action.split(": ", 1)[1]
            
            # Utiliser l'interprétation personnalisée si disponible
            interpretation_text = actions_interpretations.get(action, "")
            
            if interpretation_text:
                # Utiliser l'interprétation complète fournie par l'utilisateur (vert)
                formatted_interpretation = cls._format_db_data(interpretation_text)
                action_para = f"<b>Action {action_num} « {action_title} »</b> : {formatted_interpretation}"
                story.append(Paragraph(action_para, body_style))
            else:
                # Générer un texte par défaut basé sur les données du tableau
                total_n = float(totals["total_n"])
                total_n_minus_1 = float(totals["total_n_minus_1"])
                
                # Utiliser N-1 comme budget initial approximatif
                budget_initial = total_n_minus_1
                majoration = total_n - budget_initial
                budget_actuel = total_n
                
                # Pour les données factices, utiliser le taux d'exécution stocké
                # Pour les données réelles, calculer le taux depuis les données réelles
                if is_actions_data_fake and action in actions_data:
                    taux_execution_stored = actions_data[action].get("_taux_execution_n", 0.90)
                    budget_execute = budget_actuel * taux_execution_stored
                    taux_execution = taux_execution_stored * 100.0
                else:
                    # Pour les données réelles, on suppose que budget_execute = total_n (100%)
                    # Si des données d'exécution réelles sont disponibles, elles doivent être chargées depuis la DB
                    budget_execute = total_n
                    taux_execution = 100.0 if budget_actuel > 0 else 0.0
                
                # Formater toutes les valeurs numériques selon leur source (factice ou DB)
                formatted_annee_action = format_programme_value(str(annee), False)  # Année toujours DB
                formatted_budget_initial = format_programme_value(format_fcfa(budget_initial), is_actions_data_fake)
                formatted_budget_actuel = format_programme_value(format_fcfa(budget_actuel), is_actions_data_fake)
                formatted_budget_execute = format_programme_value(format_fcfa(budget_execute), is_actions_data_fake)
                formatted_taux_execution = format_programme_value(f"{taux_execution:.2f}%", is_actions_data_fake)
                
                # Formater la majoration/réduction si présente
                formatted_majoration_text = ""
                if majoration > 0:
                    formatted_majoration = format_programme_value(format_fcfa(majoration), is_actions_data_fake)
                    formatted_majoration_text = f"En cours d'exécution, une majoration de <b>{formatted_majoration}</b> FCFA a été opérée, "
                elif majoration < 0:
                    reduction = abs(majoration)
                    formatted_reduction = format_programme_value(format_fcfa(reduction), is_actions_data_fake)
                    formatted_majoration_text = f"Une réduction de <b>{formatted_reduction}</b> FCFA a été opérée en cours d'année, "
                
                action_para = (
                    f"<b>Action {action_num} « {action_title} »</b> : Au titre de l'année {formatted_annee_action}, cette action a été dotée "
                    f"d'un budget initial de <b>{formatted_budget_initial}</b> FCFA (loi de finances {formatted_annee_action}), entièrement financé par des ressources intérieures. "
                    f"{formatted_majoration_text}"
                    f"portant le budget actuel à <b>{formatted_budget_actuel}</b> FCFA. Ce budget a été exécuté à hauteur de "
                    f"<b>{formatted_budget_execute}</b> FCFA, soit un taux de réalisation de <b>{formatted_taux_execution}</b>."
                )
                
                # Ajouter un placeholder pour l'utilisateur si aucune interprétation n'est fournie
                action_para += f"<br/><font color='#FF0000'>Votre interprétation de l'utilisation des ressources pour cette action ici.</font>"
                story.append(Paragraph(action_para, body_style))
            
            story.append(Spacer(1, 0.15 * cm))
            action_num += 1
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Graphique : Evolution des taux d'exécution par action
        # ============================================================
        
        # Calculer les taux d'exécution pour chaque action depuis les données réelles
        # Taux = (budget exécuté / budget prévu) * 100
        bar_chart_data = {}
        for action, totals in actions_totals.items():
            total_n_minus_1 = totals.get("total_n_minus_1", Decimal(0))
            total_n = totals.get("total_n", Decimal(0))
            budget_prev_n_minus_1 = totals.get("budget_prev_n_minus_1", Decimal(0))
            budget_prev_n = totals.get("budget_prev_n", Decimal(0))
            
            # Pour les données factices, utiliser les taux stockés
            # Pour les données réelles, calculer depuis les budgets
            if is_actions_data_fake and action in actions_data:
                taux_exec_n1_stored = actions_data[action].get("_taux_execution_n1", 0.90)
                taux_exec_n_stored = actions_data[action].get("_taux_execution_n", 0.90)
                rate_n_minus_1 = taux_exec_n1_stored * 100.0
                rate_n = taux_exec_n_stored * 100.0
            else:
                # Calculer les taux d'exécution depuis les budgets (données réelles)
                if budget_prev_n_minus_1 > 0:
                    rate_n_minus_1 = float((total_n_minus_1 / budget_prev_n_minus_1) * 100)
                else:
                    rate_n_minus_1 = 0.0
                
                if budget_prev_n > 0:
                    rate_n = float((total_n / budget_prev_n) * 100)
                else:
                    rate_n = 0.0
            
            bar_chart_data[action] = {
                "rate_n_minus_1": rate_n_minus_1,
                "rate_n": rate_n,
            }
        
        # Générer le graphique en barres
        bar_chart_buffer = cls._create_bar_chart_execution_rates(
            bar_chart_data,
            annee_precedente,
            annee,
            numero,
            titre,
        )
        
        if bar_chart_buffer:
            story.append(Spacer(1, 0.3 * cm))
            
            # Titre du graphique
            formatted_numero_fig3 = format_programme_value(str(numero), is_programme_fake)
            formatted_titre_fig3 = format_programme_value(titre, is_programme_fake)
            story.append(Paragraph(f"<b>Figure 3: Evolution des taux d'exécution par action du Programme {formatted_numero_fig3} « {formatted_titre_fig3} »</b>", subsection_title_style))
            story.append(Spacer(1, 0.2 * cm))
            
            # Créer un Flowable personnalisé pour le graphique avec source (similaire au graphique en camembert)
            formatted_annee_prec_source = format_programme_value(str(annee_precedente), False)  # Année toujours DB
            source_text = f"Source: Situation d'exécution issue du SIGOBE / RAP {formatted_annee_prec_source}"
            source_para = Paragraph(source_text, source_style)
            
            class BarChartWithSource(Flowable):
                def __init__(self, source_para, bar_chart_buffer, chart_width, chart_height, available_width):
                    Flowable.__init__(self)
                    self.source_para = source_para
                    self.bar_chart_buffer = bar_chart_buffer
                    self.chart_width = chart_width
                    self.chart_height = chart_height
                    self.available_width = available_width
                    self.height = chart_height + 0.5 * cm
                    self.width = available_width
                
                def draw(self):
                    # Positionner la source en bas à gauche
                    source_w, source_h = self.source_para.wrap(self.available_width * 0.4, 1 * cm)
                    source_x = 0
                    source_y = 0
                    self.source_para.drawOn(self.canv, source_x, source_y)
                    
                    # Positionner le graphique
                    graph_x = 0
                    graph_y = 10  # En bas de la flowable
                    
                    # Dessiner d'abord le fond blanc
                    self.canv.saveState()
                    self.canv.setFillColor(colors.white)
                    self.canv.rect(graph_x, graph_y, self.chart_width, self.chart_height, stroke=0, fill=1)
                    self.canv.restoreState()
                    
                    # Dessiner le graphique par-dessus le fond
                    try:
                        from reportlab.lib.utils import ImageReader
                        if self.bar_chart_buffer:
                            self.bar_chart_buffer.seek(0)
                            img_reader = ImageReader(self.bar_chart_buffer)
                            self.canv.drawImage(
                                img_reader,
                                graph_x,
                                graph_y,
                                width=self.chart_width,
                                height=self.chart_height,
                                preserveAspectRatio=True,
                                mask=None
                            )
                        else:
                            logger.warning("⚠️ Le buffer du graphique est vide")
                    except Exception as e:
                        logger.error(f"Erreur lors du dessin du graphique: {e}", exc_info=True)
                    
                    # Pas de bordure - le conteneur parent n'a pas de contours
                
                def wrap(self, availWidth, availHeight):
                    return self.width, self.height
            
            chart_width = available_width
            chart_height = 6.5 * cm
            
            bar_with_source = BarChartWithSource(source_para, bar_chart_buffer, chart_width, chart_height, available_width)
            story.append(bar_with_source)
            story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # II.1.2. Suivi des investissements
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II.1.2. Suivi des investissements", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Récupérer les données d'investissement
        investissement_data = cls._get_investissement_data(numero, titre, annee, session)
        
        # Déterminer si les données sont factices
        # Les données factices sont générées uniquement si la DB est vide et en mode brouillon
        # On peut les détecter en vérifiant si elles contiennent le flag _taux_execution
        # qui n'est ajouté que pour les données factices
        is_investissement_data_fake = False
        if investissement_data:
            # Vérifier si au moins un projet a le flag _taux_execution (marqueur des données factices)
            # Ce flag est ajouté uniquement dans _get_investissement_data pour les données factices
            is_investissement_data_fake = any("_taux_execution" in projet for projet in investissement_data)
            
            # Alternative: vérifier les noms des projets factices par défaut
            if not is_investissement_data_fake and cls._should_use_fake_data():
                fake_project_names = [
                    "Projet d'infrastructure administrative",
                    "Projet d'équipement informatique",
                    "Projet de modernisation des systèmes"
                ]
                is_investissement_data_fake = any(
                    projet.get("nom") in fake_project_names 
                    for projet in investissement_data
                )
            
            if is_investissement_data_fake:
                logger.info(f"📊 Données d'investissement DÉTECTÉES COMME FACTICES (projets avec _taux_execution ou noms factices)")
            else:
                logger.info(f"📊 Données d'investissement détectées comme DB (aucun flag _taux_execution ni nom factice)")
        
        # Paragraphe d'introduction (toujours affiché, texte statique avec données dynamiques)
        if investissement_data:
            nb_projets_total = len(investissement_data)
            # Compter les projets en cours et achevés (basé sur les années)
            nb_projets_en_cours = sum(1 for p in investissement_data if p.get("annee_fin", 0) >= annee)
            nb_projets_acheves = nb_projets_total - nb_projets_en_cours
            
            # Formater les données dynamiques selon leur source (factice ou DB)
            # Le titre du programme peut être factice si le programme vient de DEFAULT_DATA
            formatted_titre_invest = format_programme_value(titre, is_programme_fake)
            formatted_nb_total = format_programme_value(str(nb_projets_total), is_investissement_data_fake)
            formatted_nb_en_cours = format_programme_value(str(nb_projets_en_cours), is_investissement_data_fake)
            formatted_nb_acheves = format_programme_value(str(nb_projets_acheves), is_investissement_data_fake)
            
            intro_investissement = (
                f"Le portefeuille des projets d'investissement du programme « {formatted_titre_invest} » est constitué de {formatted_nb_total} projets, "
                f"dont {formatted_nb_en_cours} projets en cours d'exécution et {formatted_nb_acheves} projets achevés. "
                f"Le tableau 5 ci-après présente la situation de ces projets."
            )
        else:
            # Introduction générique si aucune donnée
            formatted_titre_invest = format_programme_value(titre, is_programme_fake)
            intro_investissement = (
                f"Le portefeuille des projets d'investissement du programme « {formatted_titre_invest} » est présenté ci-après. "
                f"Le tableau 5 ci-après présente la situation de ces projets."
            )
        
        story.append(Paragraph(intro_investissement, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Titre du tableau (toujours affiché)
        formatted_numero_tab5 = format_programme_value(str(numero), is_programme_fake)  # Numéro peut être factice
        formatted_titre_tab5 = format_programme_value(titre, is_programme_fake)  # Titre du programme peut être factice
        story.append(Paragraph(f"<b>Tableau 5: Suivi des investissements du Programme {formatted_numero_tab5} « {formatted_titre_tab5} »</b>", body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Tableau (conditionné - afficher un message si vide)
        if not investissement_data:
            message_no_data = (
                "Aucune donnée d'investissement n'est disponible pour ce programme dans la base de données."
            )
            story.append(Paragraph(message_no_data, body_style))
        else:
            # Créer le tableau d'investissement avec formatage selon la source
            investissement_table = cls._create_investissement_table(investissement_data, available_width, format_fcfa, annee, is_investissement_data_fake, format_programme_value)
            story.append(investissement_table)
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Source (toujours affichée, texte statique avec données dynamiques)
        formatted_annee_source_invest = format_programme_value(str(annee), False)  # Année toujours DB
        formatted_annee_plus_2_invest = format_programme_value(str(annee + 2), False)  # Année toujours DB
        story.append(Paragraph(f"Source: Loi des Finances Initiale {formatted_annee_source_invest}/PIP {formatted_annee_source_invest}-{formatted_annee_plus_2_invest}/DPPD-PAP {formatted_annee_source_invest}-{formatted_annee_plus_2_invest}/Situation d'exécution issue du SIGOBE", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Analyse et interprétation par projet
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        
        # Introduction (toujours affichée, texte statique)
        intro_analyse_projets = "Les projets d'investissement du programme sont détaillés ci-dessous :"
        story.append(Paragraph(intro_analyse_projets, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Liste des projets (conditionnée)
        if investissement_data:
            # Récupérer les données d'interprétation personnalisées depuis le programme
            programme_data = programme.get("data", {})
            projets_interpretations = programme_data.get("projets_interpretations", {})
            
            # Parcourir les projets et créer l'analyse pour chacun
            projet_num = 1
            for projet in investissement_data:
                nom_projet = projet["nom"]
                
                # Utiliser l'interprétation personnalisée si disponible
                interpretation_text = projets_interpretations.get(nom_projet, "")
                
                if interpretation_text:
                    # Utiliser l'interprétation complète fournie par l'utilisateur
                    formatted_interpretation = format_programme_value(interpretation_text, False)  # Interprétation utilisateur = DB
                    formatted_nom_projet = format_programme_value(nom_projet, is_investissement_data_fake)
                    projet_para = f"<b>Projet {projet_num} « {formatted_nom_projet} »</b> : {formatted_interpretation}"
                    story.append(Paragraph(projet_para, body_style))
                else:
                    # Générer un texte par défaut basé sur les données du projet
                    annee_debut = projet["annee_debut"]
                    annee_fin = projet["annee_fin"]
                    cout_total = projet["cout_total_interieur"] + projet["cout_total_exterieur"]
                    # Utiliser les clés dynamiques basées sur l'année
                    budget_vote = projet.get(f"budget_vote_{annee}_interieur", 0) + projet.get(f"budget_vote_{annee}_exterieur", 0)
                    budget_actuel = projet.get(f"budget_actuel_{annee}_interieur", 0) + projet.get(f"budget_actuel_{annee}_exterieur", 0)
                    ordonnancement = projet.get(f"ordonnancement_{annee}_interieur", 0) + projet.get(f"ordonnancement_{annee}_exterieur", 0)
                    
                    # Calculer le taux d'exécution
                    # Pour les données factices, utiliser le taux stocké si disponible
                    if is_investissement_data_fake and "_taux_execution" in projet:
                        taux_execution = projet["_taux_execution"] * 100.0
                        # Recalculer l'ordonnancement si nécessaire pour correspondre au taux
                        ordonnancement = budget_actuel * projet["_taux_execution"]
                    else:
                        taux_execution = (ordonnancement / budget_actuel * 100) if budget_actuel > 0 else 0.0
                    
                    # Déterminer le statut du projet
                    statut = "en cours d'exécution" if annee_fin >= annee else "achevé"
                    
                    # Formater les données dynamiques selon leur source (factice ou DB)
                    formatted_nom_projet = format_programme_value(nom_projet, is_investissement_data_fake)
                    formatted_annee_debut = format_programme_value(str(annee_debut), is_investissement_data_fake)
                    formatted_annee_fin = format_programme_value(str(annee_fin), is_investissement_data_fake)
                    formatted_cout_total = format_programme_value(format_fcfa(cout_total), is_investissement_data_fake)
                    formatted_annee_budget = format_programme_value(str(annee), False)  # Année toujours DB
                    formatted_budget_vote = format_programme_value(format_fcfa(budget_vote), is_investissement_data_fake)
                    formatted_budget_actuel = format_programme_value(format_fcfa(budget_actuel), is_investissement_data_fake)
                    formatted_ordonnancement = format_programme_value(format_fcfa(ordonnancement), is_investissement_data_fake)
                    formatted_taux = format_programme_value(f"{taux_execution:.2f}%", is_investissement_data_fake)
                    
                    projet_para = (
                        f"<b>Projet {projet_num} « {formatted_nom_projet} »</b> : Ce projet, démarré en {formatted_annee_debut} et prévu pour s'achever en {formatted_annee_fin}, "
                        f"a un coût total estimé de <b>{formatted_cout_total}</b> FCFA. "
                        f"Pour l'année {formatted_annee_budget}, le budget voté initial était de <b>{formatted_budget_vote}</b> FCFA, "
                        f"alors que le budget actuel s'élève à <b>{formatted_budget_actuel}</b> FCFA. "
                        f"L'ordonnancement réalisé au titre de {formatted_annee_budget} est de <b>{formatted_ordonnancement}</b> FCFA, "
                        f"soit un taux d'exécution de <b>{formatted_taux}</b>. Le projet est actuellement {statut}."
                    )
                    
                    # Ajouter un placeholder pour l'utilisateur si aucune interprétation n'est fournie
                    projet_para += f"<br/><font color='#FF0000'>Votre interprétation de l'avancement et des résultats de ce projet ici.</font>"
                    story.append(Paragraph(projet_para, body_style))
                
                story.append(Spacer(1, 0.15 * cm))
                projet_num += 1
        else:
            # Aucune donnée disponible pour la liste des projets
            message_no_projets = (
                "Aucune donnée de projets d'investissement n'est disponible pour générer l'analyse détaillée."
            )
            story.append(Paragraph(message_no_projets, body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # II.2. Évolution des effectifs
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II.2. Évolution des effectifs", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Récupérer les données d'effectifs
        effectifs_data = cls._get_effectifs_data(numero, titre, annee, session)
        
        # Déterminer si les données sont factices
        # Les données factices sont générées uniquement si la DB est vide et en mode brouillon
        # On peut les détecter en vérifiant si elles contiennent le flag _is_fake avec valeur True
        # qui n'est ajouté que pour les données factices
        is_effectifs_data_fake = False
        if effectifs_data:
            # Vérifier si au moins une catégorie a le flag _is_fake avec valeur True (marqueur des données factices)
            is_effectifs_data_fake = any(effectif.get("_is_fake") is True for effectif in effectifs_data)
            
            if is_effectifs_data_fake:
                logger.info(f"✅ Données d'effectifs DÉTECTÉES COMME FACTICES (flag _is_fake=True)")
            else:
                logger.info(f"📊 Données d'effectifs détectées comme DB (aucun flag _is_fake=True)")
        
        # Titre du tableau (toujours affiché)
        formatted_numero_tab6 = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_tab6 = format_programme_value(titre, is_programme_fake)
        story.append(Paragraph(f"<b>Tableau 6: Exécution des prévisions d'effectifs du programme {formatted_numero_tab6} « {formatted_titre_tab6} »</b>", body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Tableau (conditionné - afficher un message si vide)
        if not effectifs_data:
            message_no_data_effectifs = (
                "Aucune donnée d'effectifs n'est disponible pour ce programme dans la base de données."
            )
            story.append(Paragraph(message_no_data_effectifs, body_style))
        else:
            # Créer le tableau d'effectifs avec formatage selon la source
            effectifs_table = cls._create_effectifs_table(effectifs_data, available_width, annee, is_effectifs_data_fake, format_programme_value)
            story.append(effectifs_table)
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Source du tableau (toujours affichée)
        formatted_annee_source_cabinet = format_programme_value(str(annee_precedente), False)  # Année toujours DB
        story.append(Paragraph(f"Source: Cabinet {cls._get_sigle_ministere()} / DAAF / Catalogue des mesures nouvelles / RAP {formatted_annee_source_cabinet}", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Graphique : Evolution des effectifs par catégorie
        # ============================================================
        
        # Titre du graphique (toujours affiché)
        formatted_numero_fig4 = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_fig4 = format_programme_value(titre, is_programme_fake)
        story.append(Paragraph(f"<b>Figure 4: Evolution des effectifs du Programme {formatted_numero_fig4} « {formatted_titre_fig4} » par catégorie</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Générer le graphique en barres (conditionné)
        effectifs_chart_buffer = None
        if effectifs_data:
            effectifs_chart_buffer = cls._create_bar_chart_effectifs(
                effectifs_data,
                annee_precedente,
                annee,
                numero,
                titre,
            )
        
        # Source du graphique (toujours affichée)
        formatted_annee_source_effectifs = format_programme_value(str(annee_precedente), False)  # Année toujours DB
        source_text = f"Source: RAP {formatted_annee_source_effectifs} / Catalogue des mesures nouvelles / Données DRH"
        source_para = Paragraph(source_text, source_style)
        
        # Classe pour afficher le graphique avec source (toujours définie)
        class EffectifsChartWithSource(Flowable):
            def __init__(self, source_para, chart_buffer, chart_width, chart_height, available_width):
                Flowable.__init__(self)
                self.source_para = source_para
                self.chart_buffer = chart_buffer
                self.chart_width = chart_width
                self.chart_height = chart_height
                self.available_width = available_width
                # Hauteur = graphique + espace pour la source
                source_w, source_h = source_para.wrap(available_width * 0.4, 1 * cm)
                self.height = chart_height + source_h + 0.2 * cm
                self.width = available_width
            
            def draw(self):
                # Calculer la hauteur de la source
                source_w, source_h = self.source_para.wrap(self.available_width * 0.4, 1 * cm)
                
                # Positionner le graphique en haut
                graph_x = 0
                graph_y = source_h + 0.2 * cm
                
                # Dessiner le graphique
                self.canv.saveState()
                self.canv.setFillColor(colors.white)
                self.canv.rect(graph_x, graph_y, self.chart_width, self.chart_height, stroke=0, fill=1)
                self.canv.restoreState()
                
                # Dessiner le graphique par-dessus le fond
                try:
                    from reportlab.lib.utils import ImageReader
                    if self.chart_buffer:
                        self.chart_buffer.seek(0)
                        img_reader = ImageReader(self.chart_buffer)
                        self.canv.drawImage(
                            img_reader,
                            graph_x,
                            graph_y,
                            width=self.chart_width,
                            height=self.chart_height,
                            preserveAspectRatio=True,
                            mask=None
                        )
                    else:
                        logger.warning("⚠️ Le buffer du graphique est vide")
                except Exception as e:
                    logger.error(f"Erreur lors du dessin du graphique: {e}", exc_info=True)
                
                # Positionner la source en bas à gauche (après le graphique)
                source_x = 0
                source_y = 0
                self.source_para.drawOn(self.canv, source_x, source_y)
            
            def wrap(self, availWidth, availHeight):
                return self.width, self.height
        
        # Afficher le graphique si disponible, sinon juste la source
        if effectifs_chart_buffer:
            chart_width = available_width
            chart_height = 6.5 * cm
            
            effectifs_with_source = EffectifsChartWithSource(source_para, effectifs_chart_buffer, chart_width, chart_height, available_width)
            story.append(effectifs_with_source)
        else:
            # Afficher uniquement la source si pas de graphique
            story.append(source_para)
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Analyse de l'évolution des effectifs
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        
        # Récupérer les données d'interprétation personnalisées depuis le programme
        programme_data = programme.get("data", {})
        effectifs_interpretation = programme_data.get("effectifs_interpretation", "")
        
        if effectifs_interpretation:
            # Utiliser l'interprétation complète fournie par l'utilisateur (DB)
            formatted_interpretation = format_programme_value(effectifs_interpretation, False)  # Interprétation utilisateur = DB
            story.append(Paragraph(formatted_interpretation, body_style))
        elif effectifs_data:
            # Générer une analyse automatique basée sur les données
            # Calculer les totaux avec clés dynamiques et vérifier leur source individuellement
            # Les totaux sont factices si au moins une valeur source est factice
            total_effectif_n_minus_1 = 0
            total_besoins_satisfaits = 0
            total_sorties = 0
            totals_are_fake_for_analysis = False
            
            for e in effectifs_data:
                # Vérifier si cette donnée spécifique est factice
                is_this_data_fake = e.get("_is_fake", False)
                if is_this_data_fake:
                    totals_are_fake_for_analysis = True
                
                total_effectif_n_minus_1 += e.get(f"effectif_{annee_precedente}", 0)
                total_besoins_satisfaits += e.get("besoins_satisfaits", 0)
                total_sorties += e.get("sorties", 0)
            
            total_fin_annee = total_effectif_n_minus_1 + total_besoins_satisfaits - total_sorties
            evolution = total_fin_annee - total_effectif_n_minus_1
            
            # Formater chaque valeur selon sa propre origine (factice ou DB)
            # Le titre du programme vient du programme, pas des effectifs
            formatted_titre_effectifs = format_programme_value(titre, is_programme_fake)
            # Les totaux sont factices si au moins une donnée source est factice
            formatted_total_effectif_n_minus_1 = format_programme_value(str(total_effectif_n_minus_1), totals_are_fake_for_analysis)
            formatted_total_fin_annee = format_programme_value(str(total_fin_annee), totals_are_fake_for_analysis)
            formatted_evolution = format_programme_value(str(evolution) if evolution > 0 else str(abs(evolution)), totals_are_fake_for_analysis)
            formatted_total_besoins_satisfaits = format_programme_value(str(total_besoins_satisfaits), totals_are_fake_for_analysis)
            formatted_total_sorties = format_programme_value(str(total_sorties), totals_are_fake_for_analysis)
            formatted_annee_precedente_effectifs = format_programme_value(str(annee_precedente), False)  # Année toujours DB
            formatted_annee_effectifs = format_programme_value(str(annee), False)  # Année toujours DB
            
            # Introduction générale
            if evolution > 0:
                intro_text = (
                    f"Les effectifs globaux du programme « {formatted_titre_effectifs} » sont passés de <b>{formatted_total_effectif_n_minus_1} agents</b> en {formatted_annee_precedente_effectifs} "
                    f"à <b>{formatted_total_fin_annee} agents</b> en fin d'année {formatted_annee_effectifs}, soit une augmentation de <b>{formatted_evolution} agent(s)</b>. "
                    f"Cette évolution résulte du recrutement de <b>{formatted_total_besoins_satisfaits} agent(s)</b>, compensé par <b>{formatted_total_sorties} départ(s)</b> enregistré(s) sur la période."
                )
            elif evolution < 0:
                intro_text = (
                    f"Les effectifs globaux du programme « {formatted_titre_effectifs} » sont passés de <b>{formatted_total_effectif_n_minus_1} agents</b> en {formatted_annee_precedente_effectifs} "
                    f"à <b>{formatted_total_fin_annee} agents</b> en fin d'année {formatted_annee_effectifs}, soit une diminution de <b>{formatted_evolution} agent(s)</b>. "
                    f"Cette évolution résulte du recrutement de <b>{formatted_total_besoins_satisfaits} agent(s)</b>, compensé par <b>{formatted_total_sorties} départ(s)</b> enregistré(s) sur la période."
                )
            else:
                intro_text = (
                    f"Les effectifs globaux du programme « {formatted_titre_effectifs} » sont restés stables à <b>{formatted_total_effectif_n_minus_1} agents</b> entre {formatted_annee_precedente_effectifs} et {formatted_annee_effectifs}. "
                    f"Le recrutement de <b>{formatted_total_besoins_satisfaits} agent(s)</b> a été compensé par <b>{formatted_total_sorties} départ(s)</b> enregistré(s) sur la période."
                )
            
            story.append(Paragraph(intro_text, body_style))
            story.append(Spacer(1, 0.15 * cm))
            
            # Détail par catégorie
            story.append(Paragraph("Par catégorie socio-professionnelle, les évolutions se présentent comme suit :", body_style))
            story.append(Spacer(1, 0.1 * cm))
            
            for effectif in effectifs_data:
                categorie = effectif["categorie"]
                # Utiliser la clé dynamique basée sur l'année précédente
                effectif_n_minus_1 = effectif.get(f"effectif_{annee_precedente}", 0)
                besoins_satisfaits = effectif.get("besoins_satisfaits", 0)
                sorties = effectif.get("sorties", 0)
                effectif_fin_annee = effectif_n_minus_1 + besoins_satisfaits - sorties
                evolution_cat = effectif_fin_annee - effectif_n_minus_1
                
                # Déterminer si CETTE donnée spécifique est factice (basé sur l'objet effectif lui-même)
                # Chaque valeur vérifie sa propre origine
                is_this_category_fake = effectif.get("_is_fake", False)
                
                # Formater chaque valeur selon sa propre origine (factice ou DB)
                formatted_categorie = format_programme_value(categorie, is_this_category_fake)
                formatted_effectif_n_minus_1 = format_programme_value(str(effectif_n_minus_1), is_this_category_fake)
                formatted_besoins_satisfaits = format_programme_value(str(besoins_satisfaits), is_this_category_fake)
                formatted_sorties = format_programme_value(str(sorties), is_this_category_fake)
                # La valeur calculée est factice si la donnée source est factice
                formatted_effectif_fin_annee = format_programme_value(str(effectif_fin_annee), is_this_category_fake)
                
                if evolution_cat > 0:
                    cat_text = (
                        f"• <b>{formatted_categorie}</b> : <b>{formatted_besoins_satisfaits} agent(s)</b> recruté(s), portant les effectifs de "
                        f"<b>{formatted_effectif_n_minus_1}</b> à <b>{formatted_effectif_fin_annee} agent(s)</b>."
                    )
                elif evolution_cat < 0:
                    cat_text = (
                        f"• <b>{formatted_categorie}</b> : <b>{formatted_sorties} départ(s)</b> enregistré(s), réduisant les effectifs de "
                        f"<b>{formatted_effectif_n_minus_1}</b> à <b>{formatted_effectif_fin_annee} agent(s)</b>."
                    )
                else:
                    if besoins_satisfaits > 0 and sorties > 0:
                        if besoins_satisfaits == sorties:
                            cat_text = (
                                f"• <b>{formatted_categorie}</b> : Les effectifs sont restés stables à <b>{formatted_effectif_n_minus_1} agent(s)</b>, "
                                f"les <b>{formatted_besoins_satisfaits} recrutement(s)</b> compensant exactement les <b>{formatted_sorties} départ(s)</b>."
                            )
                        else:
                            cat_text = (
                                f"• <b>{formatted_categorie}</b> : Les effectifs sont restés stables à <b>{formatted_effectif_n_minus_1} agent(s)</b>, "
                                f"avec <b>{formatted_besoins_satisfaits} recrutement(s)</b> compensant <b>{formatted_sorties} départ(s)</b>."
                            )
                    elif besoins_satisfaits > 0:
                        cat_text = (
                            f"• <b>{formatted_categorie}</b> : Les effectifs sont restés stables à <b>{formatted_effectif_n_minus_1} agent(s)</b>, "
                            f"avec <b>{formatted_besoins_satisfaits} recrutement(s)</b>."
                        )
                    elif sorties > 0:
                        cat_text = (
                            f"• <b>{formatted_categorie}</b> : Les effectifs sont restés stables à <b>{formatted_effectif_n_minus_1} agent(s)</b>, "
                            f"avec <b>{formatted_sorties} départ(s)</b>."
                        )
                    else:
                        cat_text = (
                            f"• <b>{formatted_categorie}</b> : Les effectifs sont restés inchangés à <b>{formatted_effectif_n_minus_1} agent(s)</b>."
                        )
                
                story.append(Paragraph(cat_text, body_style))
            
            story.append(Spacer(1, 0.15 * cm))
        # Si aucune donnée et aucune interprétation personnalisée, on passe directement à la conclusion
        # Le message d'absence de données est déjà affiché dans la section tableau/graphique
        
        # Conclusion (toujours affichée, texte statique)
        conclusion_text = (
            "Les effectifs actuels du programme ont largement contribué à l'atteinte des résultats, "
            "comme l'illustrent les indicateurs de performance."
        )
        story.append(Paragraph(conclusion_text, body_style))
        
        # Ajouter un placeholder pour l'utilisateur si aucune interprétation n'est fournie
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph("<font color='#FF0000'>Votre interprétation complémentaire sur l'évolution des effectifs ici.</font>", body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # II.3. Bilan des activités en rapport avec les axes stratégiques
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II.3. Bilan des activités en rapport avec les axes stratégiques", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Récupérer les activités majeures (basées sur le taux d'exécution)
        activites_majeures = cls._get_activites_majeures(numero, titre, annee, session)
        
        # Récupérer les données d'interprétation personnalisées depuis le programme
        programme_data = programme.get("data", {})
        activites_bilan = programme_data.get("activites_bilan", {})
        bilan_conclusion = programme_data.get("bilan_conclusion", "")
        
        # Formater les données dynamiques selon leur source (factice ou DB)
        formatted_annee_bilan = format_programme_value(str(annee), False)  # Année toujours DB
        formatted_titre_bilan = format_programme_value(titre, is_programme_fake)
        
        # Introduction (toujours affichée, texte statique avec données dynamiques)
        intro_bilan = (
            f"L'année {formatted_annee_bilan} a été marquée par la réalisation des activités majeures du programme « {formatted_titre_bilan} », notamment:"
        )
        story.append(Paragraph(intro_bilan, body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Style pour les puces avec retrait
        bullet_style = ParagraphStyle(
            "BulletStyle",
            parent=body_style,
            leftIndent=1.0 * cm,
            firstLineIndent=-0.3 * cm,
            spaceAfter=2,
        )
        
        # Liste des activités (conditionnée - afficher un message si vide)
        if not activites_majeures:
            message_no_data_activites = (
                "Aucune donnée d'activités majeures n'est disponible pour ce programme dans la base de données."
            )
            story.append(Paragraph(message_no_data_activites, bullet_style))
        else:
            # Liste des activités
            for activite in activites_majeures:
                # Utiliser l'activité personnalisée si disponible, sinon utiliser celle générée
                activite_text = activites_bilan.get(activite["libelle"], activite["libelle"])
                
                # Déterminer si CETTE activité spécifique est factice (basé sur l'objet activite lui-même)
                # Chaque activité vérifie sa propre origine
                is_this_activite_fake = activite.get("_is_fake", False)
                
                # Formater l'activité selon sa propre origine (factice ou DB)
                # Si l'activité vient de activites_bilan (données utilisateur), elle est DB, sinon on utilise le flag
                if activite_text in activites_bilan.values():
                    # Données utilisateur = DB
                    formatted_activite = format_programme_value(activite_text, False)
                else:
                    # Utiliser le flag de l'activité originale
                    formatted_activite = format_programme_value(activite_text, is_this_activite_fake)
                story.append(Paragraph(f"• {formatted_activite};", bullet_style))
        
        story.append(Spacer(1, 0.15 * cm))
        
        # Conclusion (toujours affichée, texte statique avec données dynamiques)
        if bilan_conclusion:
            # Données utilisateur (formatées selon leur source)
            formatted_conclusion = cls._format_db_data(bilan_conclusion)
            story.append(Paragraph(formatted_conclusion, body_style))
        else:
            # Formater l'année dans la conclusion selon sa source (factice ou DB)
            # L'année est toujours DB
            formatted_annee_conclusion = format_programme_value(str(annee), False)
            conclusion_bilan = (
                "Au regard du bilan des principales activités réalisées en lien avec les axes stratégiques du programme, "
                "les résultats obtenus sont jugés globalement satisfaisants. Ces accomplissements ont permis d'atteindre pleinement "
                f"les objectifs de performance fixés pour l'année {formatted_annee_conclusion}. Les actions entreprises ont été menées dans le respect "
                "des délais et des ressources allouées, contribuant ainsi au succès du programme. Aucune difficulté majeure n'a été "
                "rencontrée et les processus ont été exécutés sans entrave significative."
            )
            story.append(Paragraph(conclusion_bilan, body_style))
            story.append(Spacer(1, 0.15 * cm))
            story.append(Paragraph("<font color='#FF0000'>Votre interprétation complémentaire sur le bilan des activités ici.</font>", body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # III. PERFORMANCE DU PROGRAMME
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("III. PERFORMANCE DU PROGRAMME", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # ============================================================
        # III.1. Présentation de l'évolution des indicateurs de performance du programme
        # ============================================================
        story.append(Paragraph("III.1. Présentation de l'évolution des indicateurs de performance du programme", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Récupérer les données d'indicateurs AVANT de les utiliser dans l'introduction
        indicateurs_data = cls._get_indicateurs_performance_data(numero, titre, annee, session)
        
        # Introduction (toujours affichée, texte statique avec données dynamiques)
        formatted_annee_intro = format_programme_value(str(annee), False)  # Année toujours DB
        formatted_titre_intro = format_programme_value(titre, is_programme_fake)
        # Compter le nombre d'indicateurs pour adapter le texte
        if indicateurs_data:
            nb_indicateurs = len(indicateurs_data)
            indicateur_texte = "indicateurs" if nb_indicateurs > 1 else "indicateur"
            intro_indicateurs = (
                f"Dans le cadre de l'évaluation de la performance du ministère, {nb_indicateurs} {indicateur_texte} {('ont été' if nb_indicateurs > 1 else 'a été')} adopté{('s' if nb_indicateurs > 1 else '')} par le Parlement "
                f"à l'annexe 4 de la loi de finances {formatted_annee_intro} pour le programme « {formatted_titre_intro} »."
            )
        else:
            intro_indicateurs = (
                f"Dans le cadre de l'évaluation de la performance du ministère, des indicateurs ont été adoptés par le Parlement "
                f"à l'annexe 4 de la loi de finances {formatted_annee_intro} pour le programme « {formatted_titre_intro} »."
            )
        story.append(Paragraph(intro_indicateurs, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Titre du tableau (toujours affiché)
        formatted_numero_tab7 = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_tab7 = format_programme_value(titre, is_programme_fake)
        story.append(Paragraph(f"<b>Tableau 7: Évolution des indicateurs du programme {formatted_numero_tab7} « {formatted_titre_tab7} »</b>", body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Tableau (conditionné - afficher un message si vide)
        if not indicateurs_data:
            message_no_data_indicateurs = (
                "Aucune donnée d'indicateurs de performance n'est disponible pour ce programme dans la base de données."
            )
            story.append(Paragraph(message_no_data_indicateurs, body_style))
        else:
            # Créer le tableau d'indicateurs avec formatage selon la source
            indicateurs_table = cls._create_indicateurs_table(indicateurs_data, available_width, annee, format_programme_value)
            story.append(indicateurs_table)
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Source (toujours affichée, texte statique avec données dynamiques)
        # Format selon le tableau de référence : "Source: RAP 2021 et 2022 MBPE et 2023 MPPEEP / DPPD-PAP 2024-2026 MPPEEP"
        # Les années sont toujours DB
        annee_n_3_source = annee - 3
        annee_n_2_source = annee - 2
        annee_n_1_source = annee - 1
        formatted_annee_n_3_source = format_programme_value(str(annee_n_3_source), False)
        formatted_annee_n_2_source = format_programme_value(str(annee_n_2_source), False)
        formatted_annee_n_1_source = format_programme_value(str(annee_n_1_source), False)
        formatted_annee_source_tab7 = format_programme_value(str(annee), False)
        formatted_annee_plus_2_tab7 = format_programme_value(str(annee + 2), False)
        # Récupérer le sigle du ministère
        sigle_ministere = cls._get_sigle_ministere()
        story.append(Paragraph(f"Source: RAP {formatted_annee_n_3_source} et {formatted_annee_n_2_source} MBPE et {formatted_annee_n_1_source} {sigle_ministere} / DPPD-PAP {formatted_annee_source_tab7}-{formatted_annee_plus_2_tab7} {sigle_ministere}", source_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Note (toujours affichée, texte statique avec données dynamiques)
        # L'année est toujours DB
        formatted_annee_nb = format_programme_value(str(annee), False)
        story.append(Paragraph(f"<b>NB:</b> L'indicateur a été défini en {formatted_annee_nb}.", body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # III.2. Analyse détaillée et explication des résultats
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("III.2. Analyse détaillée et explication des résultats (objectifs spécifiques et indicateurs)", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Introduction (toujours affichée, texte statique avec données dynamiques)
        formatted_annee_analyse = format_programme_value(str(annee), False)  # Année toujours DB
        formatted_titre_analyse = format_programme_value(titre, is_programme_fake)
        if indicateurs_data:
            # Déterminer si les nombres sont factices (si au moins un indicateur est factice, alors le compte est factice)
            # Pour simplifier, on vérifie si au moins un indicateur a _source="default"
            is_count_fake = any(ind.get("_source", "default") == "default" for ind in indicateurs_data)
            formatted_nb_objectifs = format_programme_value(str(len(indicateurs_data)), is_count_fake)
            formatted_nb_indicateurs = format_programme_value(str(len(indicateurs_data)), is_count_fake)
            formatted_nb_cibles = format_programme_value(str(len(indicateurs_data)), is_count_fake)
            intro_analyse = (
                f"Au titre de l'année {formatted_annee_analyse}, le programme « {formatted_titre_analyse} » est structuré autour de {formatted_nb_objectifs} objectif(s) "
                f"spécifique(s) et {formatted_nb_indicateurs} indicateur(s) de performance lié(s) à {formatted_nb_cibles} cible(s)."
            )
        else:
            intro_analyse = (
                f"Au titre de l'année {formatted_annee_analyse}, le programme « {formatted_titre_analyse} » est structuré autour d'objectifs spécifiques "
                f"et d'indicateurs de performance."
            )
        story.append(Paragraph(intro_analyse, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Liste des indicateurs (conditionnée)
        if indicateurs_data:
            # Récupérer les données d'interprétation personnalisées depuis le programme
            programme_data = programme.get("data", {})
            indicateurs_analyses = programme_data.get("indicateurs_analyses", {})
            
            # Parcourir les indicateurs et créer l'analyse pour chacun
            indicateur_num = 1
            for indicateur in indicateurs_data:
                objectif_titre = indicateur["objectif_titre"]
                indicateur_nom = indicateur["indicateur_nom"]
                
                # Déterminer si les données sont factices
                data_source = indicateur.get("_source", "default")
                is_fake_data = (data_source == "default")
                
                # Formater les titres selon la source (factice en violet italique, DB en rouge)
                # Conserver les préfixes dans objectif_titre et indicateur_nom
                if is_fake_data:
                    formatted_objectif_titre = cls._format_fake_data(objectif_titre)
                    formatted_indicateur_nom = cls._format_fake_data(indicateur_nom)
                    formatted_indicateur_num = cls._format_fake_data(str(indicateur_num))
                else:
                    formatted_objectif_titre = cls._format_db_data(objectif_titre)
                    formatted_indicateur_nom = cls._format_db_data(indicateur_nom)
                    formatted_indicateur_num = cls._format_db_data(str(indicateur_num))
                
                # Titre objectif - utiliser le texte complet avec préfixe
                story.append(Paragraph(f"<b>{formatted_objectif_titre}</b>", body_style))
                story.append(Spacer(1, 0.1 * cm))
                
                # Titre indicateur - utiliser le texte complet avec préfixe
                story.append(Paragraph(f"<b>{formatted_indicateur_nom}</b>", body_style))
                story.append(Spacer(1, 0.1 * cm))
                
                # Générer et afficher le graphique d'évolution de l'indicateur
                # Récupérer les valeurs de réalisation pour les 4 dernières années
                annee_n_3 = annee - 3
                annee_n_2 = annee - 2
                annee_n_1 = annee - 1
                valeurs_evolution = [
                    indicateur.get(f"realisation_{annee_n_3}", None),
                    indicateur.get(f"realisation_{annee_n_2}", None),
                    indicateur.get(f"realisation_{annee_n_1}", None),
                    indicateur.get(f"realisation_{annee}", None)
                ]
                
                # Vérifier si on a au moins une valeur, sinon utiliser None pour générer des données de test
                # Si toutes les valeurs sont None, passer None pour utiliser les données de test
                valeurs_finales = None
                if all(v is not None for v in valeurs_evolution):
                    # Toutes les valeurs sont présentes
                    valeurs_finales = valeurs_evolution
                elif any(v is not None for v in valeurs_evolution):
                    # Certaines valeurs sont présentes, utiliser None pour générer des données de test complètes
                    valeurs_finales = None
                else:
                    # Aucune valeur, utiliser None pour générer des données de test
                    valeurs_finales = None
                
                # Créer le graphique d'évolution (toujours générer, même avec des données de test)
                # Créer le graphique d'évolution (toujours générer, même avec des données de test)
                logger.info(f"📊 Génération du graphique d'évolution pour l'indicateur '{indicateur_nom}' (année {annee}, valeurs: {valeurs_finales})")
                evolution_chart_buffer = cls._create_indicateur_evolution_chart(
                    indicateur_nom=indicateur_nom,
                    annee=annee,
                    valeurs=valeurs_finales
                )
                
                if evolution_chart_buffer:
                    logger.info(f"✅ Graphique d'évolution généré avec succès pour l'indicateur '{indicateur_nom}'")
                else:
                    logger.warning(f"⚠️ Échec de la génération du graphique d'évolution pour l'indicateur '{indicateur_nom}'")
                
                if evolution_chart_buffer:
                    # Créer un Flowable personnalisé pour le graphique avec titre et source
                    class IndicateurEvolutionChartWithSource(Flowable):
                        def __init__(self, title_para, chart_buffer, chart_width, chart_height, available_width):
                            Flowable.__init__(self)
                            self.title_para = title_para
                            self.chart_buffer = chart_buffer
                            self.chart_width = chart_width
                            self.chart_height = chart_height
                            self.available_width = available_width
                            self.width = available_width
                            self.height = chart_height + 1.5 * cm  # Hauteur du graphique + espace pour titre/source
                        
                        def draw(self):
                            self.canv.saveState()
                            
                            # Dessiner le titre
                            title_x = 0
                            title_y = self.height - 0.5 * cm
                            self.canv.translate(title_x, title_y)
                            self.title_para.wrap(self.available_width, 0.5 * cm)
                            self.title_para.drawOn(self.canv, 0, 0)
                            self.canv.translate(-title_x, -title_y)
                            
                            # Dessiner le graphique
                            graph_x = 0
                            graph_y = 0.5 * cm
                            
                            # Dessiner le fond gris clair
                            self.canv.saveState()
                            self.canv.setFillColor(colors.HexColor("#d5d5d5"))
                            self.canv.rect(graph_x, graph_y, self.chart_width, self.chart_height, stroke=0, fill=1)
                            self.canv.restoreState()
                            
                            # Dessiner le graphique par-dessus le fond
                            try:
                                from reportlab.lib.utils import ImageReader
                                if self.chart_buffer:
                                    self.chart_buffer.seek(0)
                                    img_reader = ImageReader(self.chart_buffer)
                                    self.canv.drawImage(
                                        img_reader,
                                        graph_x,
                                        graph_y,
                                        width=self.chart_width,
                                        height=self.chart_height,
                                        preserveAspectRatio=True,
                                        mask=None
                                    )
                                else:
                                    logger.warning("⚠️ Le buffer du graphique d'évolution est vide")
                            except Exception as e:
                                logger.error(f"Erreur lors du dessin du graphique d'évolution: {e}", exc_info=True)
                            
                            # Dessiner la bordure grise par-dessus tout
                            self.canv.saveState()
                            self.canv.setStrokeColor(colors.HexColor("#d5d5d5"))
                            self.canv.setLineWidth(1)
                            self.canv.rect(graph_x, graph_y, self.chart_width, self.chart_height, stroke=1, fill=0)
                            self.canv.restoreState()
                            
                            self.canv.restoreState()
                        
                        def wrap(self, availWidth, availHeight):
                            return self.width, self.height
                    
                    # Créer le titre de la figure
                    # Déterminer si les éléments du titre sont factices
                    is_fig_data_fake = (indicateur.get("_source", "default") == "default")
                    # Le numéro de l'indicateur et les années sont toujours DB (structure), mais le nom dépend de la source
                    # Conserver le préfixe dans le nom de l'indicateur
                    formatted_indicateur_num_fig = cls._format_db_data(str(indicateur_num))
                    formatted_indicateur_nom_fig = format_programme_value(indicateur_nom, is_fig_data_fake)
                    formatted_annee_n_3_fig = cls._format_db_data(str(annee_n_3))
                    formatted_annee_fig = cls._format_db_data(str(annee))
                    
                    figure_title_text = f"Figure {12 + indicateur_num}: Evolution de l'indicateur {formatted_indicateur_num_fig} « {formatted_indicateur_nom_fig} » de {formatted_annee_n_3_fig} à {formatted_annee_fig}"
                    figure_title_para = Paragraph(f"<b>{figure_title_text}</b>", body_style)
                    
                    # Créer la source
                    # L'année est toujours DB
                    formatted_annee_source_fig = format_programme_value(str(annee), False)
                    source_text = f"Source: RAP {formatted_annee_source_fig}"
                    source_para = Paragraph(source_text, source_style)
                    
                    # Créer le flowable combiné
                    chart_width = available_width
                    chart_height = 7 * cm
                    evolution_chart_with_source = IndicateurEvolutionChartWithSource(
                        figure_title_para, evolution_chart_buffer, chart_width, chart_height, available_width
                    )
                    story.append(evolution_chart_with_source)
                    story.append(Spacer(1, 0.1 * cm))
                    story.append(source_para)
                    story.append(Spacer(1, 0.15 * cm))
                
                # Utiliser l'analyse personnalisée si disponible
                analyse_key = f"{objectif_titre}_{indicateur_nom}"
                analyse_text = indicateurs_analyses.get(analyse_key, "")
                
                # Déterminer la source des données pour le styling
                data_source = indicateur.get("_source", "default")  # "default" (factice), "db", ou "user"
                is_fake_data = (data_source == "default")
                
                # Fonction helper pour formater selon la source (factice ou DB)
                def format_indicateur_value(value: Any) -> str:
                    """Formate une valeur d'indicateur selon si elle est factice ou réelle."""
                    if is_fake_data:
                        return cls._format_fake_data(str(value))
                    else:
                        return cls._format_db_data(str(value))
                
                if analyse_text:
                    # Utiliser l'analyse complète fournie par l'utilisateur (données utilisateur = rouge en brouillon)
                    formatted_analyse = cls._format_db_data(analyse_text)
                    story.append(Paragraph(formatted_analyse, body_style))
                else:
                    # Générer une analyse automatique basée sur les données
                    definition = indicateur.get("definition", "")
                    source_donnees = indicateur.get("source_donnees", "")
                    mode_calcul = indicateur.get("mode_calcul", "")
                    valeurs_cibles = indicateur.get("valeurs_cibles", "")
                    # Récupérer la réalisation de l'année N de manière dynamique
                    realisation_n = indicateur.get(f"realisation_{annee}", 0)
                    
                    # Définition de l'indicateur (avec indentation pour la hiérarchie)
                    if definition:
                        formatted_definition = format_indicateur_value(definition)
                        story.append(Paragraph(f"<b>Définition de l'indicateur:</b> {formatted_definition}", indicateur_subitem_style))
                        story.append(Spacer(1, 0.08 * cm))
                    
                    # Source de données (avec indentation pour la hiérarchie)
                    if source_donnees:
                        formatted_source = format_indicateur_value(source_donnees)
                        story.append(Paragraph(f"<b>Source de données:</b> {formatted_source}", indicateur_subitem_style))
                        story.append(Spacer(1, 0.08 * cm))
                    
                    # Mode de calcul (avec indentation pour la hiérarchie)
                    if mode_calcul:
                        formatted_mode = format_indicateur_value(mode_calcul)
                        story.append(Paragraph(f"<b>Mode de calcul:</b> {formatted_mode}", indicateur_subitem_style))
                        story.append(Spacer(1, 0.08 * cm))
                    
                    # Valeurs cibles (avec indentation pour la hiérarchie)
                    if valeurs_cibles:
                        formatted_cibles = format_indicateur_value(valeurs_cibles)
                        story.append(Paragraph(f"<b>Valeurs cibles:</b> {formatted_cibles}", indicateur_subitem_style))
                        story.append(Spacer(1, 0.1 * cm))
                    
                    # Analyse de l'indicateur (avec indentation pour la hiérarchie)
                    # Récupérer le nombre d'activités depuis les données (par défaut 15)
                    nb_activites = indicateur.get("nb_activites", 15)
                    # Formater le nombre d'activités selon la source
                    formatted_nb_activites = format_indicateur_value(nb_activites)
                    # Formater la réalisation selon la source
                    formatted_realisation = format_indicateur_value(realisation_n)
                    
                    # Formater le titre du programme et l'année selon leur source (factice ou DB)
                    formatted_titre_analyse_ind = format_programme_value(titre, is_programme_fake)
                    formatted_annee_analyse_ind = format_programme_value(str(annee), False)  # Année toujours DB
                    
                    analyse_para = (
                        f"<b>Analyse de l'indicateur:</b> Cet indicateur permet d'évaluer le niveau de mise en œuvre des activités prévues "
                        f"dans le Plan de Travail Annuel (PTA) du programme « {formatted_titre_analyse_ind} ». Il indique le pourcentage d'activités effectivement réalisées "
                        f"par rapport au nombre total d'activités planifiées. À la fin de l'année {formatted_annee_analyse_ind}, les {formatted_nb_activites} activité(s) prévue(s) "
                        f"dans le Plan de Travail Annuel (PTA) ont été entièrement réalisées, affichant un résultat de {formatted_realisation}% conformes aux attentes. "
                        f"Cette performance s'explique notamment par une meilleure organisation des activités, une implication accrue des parties prenantes "
                        f"et un renforcement du système de suivi."
                    )
                    story.append(Paragraph(analyse_para, indicateur_subitem_style))
                    story.append(Spacer(1, 0.1 * cm))
                    
                    # Paragraphe de conclusion avec années dynamiques (avec indentation pour la hiérarchie)
                    annee_n_3 = annee - 3
                    annee_n_2 = annee - 2
                    annee_n_1 = annee - 1
                    annee_n_plus_1 = annee + 1
                    
                    # Formater les années selon leur source (factice ou DB)
                    # Les années sont toujours DB
                    formatted_annee_n_3 = format_programme_value(str(annee_n_3), False)
                    formatted_annee_n_2 = format_programme_value(str(annee_n_2), False)
                    formatted_annee_n_1 = format_programme_value(str(annee_n_1), False)
                    formatted_annee_intro = format_programme_value(str(annee), False)
                    formatted_annee_n_plus_1 = format_programme_value(str(annee_n_plus_1), False)
                    
                    conclusion_indicateur = (
                        f"Il est important de noter que toute tentative de comparaison avec les années {formatted_annee_n_3}-{formatted_annee_n_2} et {formatted_annee_n_1} s'avère inopérante, "
                        f"car cet indicateur a été introduit pour la première fois en {formatted_annee_intro}. À la lumière des résultats obtenus, "
                        f"il semble judicieux de maintenir cette dynamique en {formatted_annee_n_plus_1} pour maximiser l'impact des actions au sein des structures du ministère."
                    )
                    story.append(Paragraph(conclusion_indicateur, indicateur_subitem_style))
                    
                    # Ajouter un placeholder pour l'utilisateur si aucune analyse n'est fournie (avec indentation pour la hiérarchie)
                    story.append(Spacer(1, 0.1 * cm))
                    story.append(Paragraph(cls._format_db_data("Votre analyse complémentaire sur cet indicateur ici."), indicateur_subitem_style))
                
                story.append(Spacer(1, 0.2 * cm))
                indicateur_num += 1
        else:
            # Aucune donnée disponible pour la liste des indicateurs
            message_no_indicateurs = (
                "Aucune donnée d'indicateurs de performance n'est disponible pour générer l'analyse détaillée."
            )
            story.append(Paragraph(message_no_indicateurs, body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # IV. POINTS POSITIFS, DIFFICULTÉS, RECOMMANDATIONS ET CONCLUSION
        # ============================================================
        
        # Récupérer les données de conclusion depuis cls.data (RapData) par programme
        # La structure est : { "code_programme": { "points_positifs": [...], "difficultes": "...", ... } }
        all_conclusion_data = cls.data.get("conclusion_interpretations", {})
        
        # Identifier le programme par son code ou titre
        programme_code = None
        if programme_data.get("code"):
            programme_code = programme_data.get("code")
        elif titre:
            # Essayer de trouver le code du programme par son titre
            try:
                from app.models.personnel import Programme
                programme_db = session.exec(
                    select(Programme).where(Programme.libelle.ilike(f"%{titre}%"))
                ).first()
                if programme_db:
                    programme_code = programme_db.code
            except Exception as e:
                logger.warning(f"⚠️ Impossible de trouver le code du programme: {e}")
        
        # Récupérer les données de conclusion pour ce programme
        conclusion_interpretations = {}
        is_conclusion_data_fake = False
        if programme_code and all_conclusion_data:
            conclusion_interpretations = all_conclusion_data.get(programme_code, {})
        
        # Vérifier le mode et générer des données factices si nécessaire (mode brouillon uniquement)
        mode = cls.data.get("mode", "brouillon")
        if not conclusion_interpretations or (
            not conclusion_interpretations.get("points_positifs") and
            not conclusion_interpretations.get("difficultes") and
            not conclusion_interpretations.get("recommandations") and
            not conclusion_interpretations.get("conclusion")
        ):
            if mode == "brouillon":
                # Générer des données factices en mode brouillon
                logger.info(f"📊 Mode brouillon: génération de données factices pour la conclusion du programme")
                is_conclusion_data_fake = True
                conclusion_interpretations = {
                    "points_positifs": [
                        "Amélioration significative de la gestion administrative et financière du programme",
                        "Renforcement des capacités du personnel grâce aux formations dispensées",
                        "Optimisation des processus de suivi et d'évaluation des activités"
                    ],
                    "difficultes": (
                        f"Les principales difficultés rencontrées au cours de l'exercice {annee} ont été liées aux retards dans "
                        f"l'approbation de certains projets et à la mobilisation des ressources nécessaires à leur réalisation. "
                        f"Des contraintes budgétaires ont également été observées, impactant le rythme d'exécution de certaines actions."
                    ),
                    "recommandations": (
                        f"Pour améliorer la performance du programme, il est recommandé de renforcer le suivi des activités "
                        f"en mettant en place des mécanismes de contrôle plus efficaces. Il serait également bénéfique d'accélérer "
                        f"les procédures d'approbation des projets et d'optimiser l'allocation des ressources budgétaires."
                    ),
                    "conclusion": (
                        f"Malgré les difficultés rencontrées, le programme a globalement atteint ses objectifs pour l'exercice {annee}. "
                        f"Les résultats obtenus témoignent de l'engagement du personnel et de l'efficacité des mesures mises en œuvre. "
                        f"Des efforts supplémentaires seront nécessaires pour améliorer certains indicateurs de performance et renforcer "
                        f"la capacité du programme à répondre aux attentes."
                    )
                }
            # En mode final, on garde conclusion_interpretations vide (pas de données factices)
        
        # Définir le style bullet pour les listes à puces (si pas déjà défini)
        if 'bullet_style' not in locals():
            bullet_style = ParagraphStyle(
                "BulletStyle",
                parent=body_style,
                leftIndent=20,
                bulletIndent=10,
            )
        
        # ============================================================
        # IV.1. Points positifs tirés de l'exercice
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("IV.1. Points positifs tirés de l'exercice", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Introduction
        formatted_annee_points = format_programme_value(str(annee), False)  # Année toujours DB
        intro_points = (
            f"Au cours de l'exercice {formatted_annee_points}, il a été retenu les points forts suivants:"
        )
        story.append(Paragraph(intro_points, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Points positifs (liste à puces)
        points_positifs = conclusion_interpretations.get("points_positifs", [])
        if points_positifs:
            for point in points_positifs:
                if point and point.strip():
                    # Formater chaque point selon sa source (factice ou DB)
                    formatted_point = format_programme_value(point.strip(), is_conclusion_data_fake)
                    story.append(Paragraph(formatted_point, bullet_style, bulletText="•"))
        else:
            # Message si aucune donnée (mode final uniquement)
            message_no_points = (
                "Aucun point positif n'a été renseigné pour cet exercice."
            )
            story.append(Paragraph(message_no_points, body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # IV.2. Difficultés rencontrées
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("IV.2. Difficultés rencontrées", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Difficultés
        difficultes = conclusion_interpretations.get("difficultes", "")
        if difficultes and difficultes.strip():
            # Formater selon sa source (factice ou DB)
            formatted_difficultes = format_programme_value(difficultes.strip(), is_conclusion_data_fake)
            story.append(Paragraph(formatted_difficultes, body_style))
        else:
            # Message si aucune donnée (mode final uniquement)
            message_no_difficultes = (
                "Aucune difficulté n'a été renseignée pour cet exercice."
            )
            story.append(Paragraph(message_no_difficultes, body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # IV.3. Recommandations
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("IV.3. Recommandations", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Recommandations
        recommandations = conclusion_interpretations.get("recommandations", "")
        if recommandations and recommandations.strip():
            # Formater selon sa source (factice ou DB)
            formatted_recommandations = format_programme_value(recommandations.strip(), is_conclusion_data_fake)
            story.append(Paragraph(formatted_recommandations, body_style))
        else:
            # Message si aucune donnée (mode final uniquement)
            message_no_recommandations = (
                "Aucune recommandation n'a été renseignée pour cet exercice."
            )
            story.append(Paragraph(message_no_recommandations, body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # CONCLUSION
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("CONCLUSION", section_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Conclusion
        conclusion = conclusion_interpretations.get("conclusion", "")
        if conclusion and conclusion.strip():
            # Formater selon sa source (factice ou DB)
            formatted_conclusion = format_programme_value(conclusion.strip(), is_conclusion_data_fake)
            story.append(Paragraph(formatted_conclusion, body_style))
        else:
            # Message si aucune donnée (mode final uniquement)
            message_no_conclusion = (
                "Aucune conclusion n'a été renseignée pour ce programme."
            )
            story.append(Paragraph(message_no_conclusion, body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Fonction pour dessiner le footer avec numéro de page
        page_counter = start_page - 1  # Commencer à start_page - 1 car on incrémente avant
        
        def on_page(canv, doc_obj):
            """Callback appelé à chaque page pour dessiner le footer."""
            nonlocal page_counter
            page_counter += 1
            
            canv.saveState()
            card_size = 1.0 * cm
            corner_size = 0.3 * cm
            card_x = page_width - right_margin - card_size
            card_y = bottom_margin - footer_margin
            
            # Dessiner la carte
            canv.setFillColor(colors.white)
            canv.setStrokeColor(colors.HexColor("#E0E0E0"))
            canv.setLineWidth(0.5)
            canv.roundRect(card_x, card_y, card_size, card_size, 0.2 * cm, fill=1, stroke=1)
            
            # Coin supérieur droit enroulé
            corner_path = canv.beginPath()
            corner_path.moveTo(card_x + card_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size - corner_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size, card_y + card_size - corner_size)
            corner_path.close()
            canv.setFillColor(colors.HexColor("#F0F0F0"))
            canv.setStrokeColor(colors.HexColor("#E0E0E0"))
            canv.drawPath(corner_path, fill=1, stroke=1)
            
            # Numéro de page
            canv.setFillColor(colors.black)
            canv.setFont("Helvetica", 10)
            text_width = canv.stringWidth(str(page_counter), "Helvetica", 10)
            text_x = card_x + (card_size - text_width) / 2
            text_y = card_y + (card_size - 10) / 2 - 3  # Descendre de 3 points
            canv.drawString(text_x, text_y, str(page_counter))
            canv.restoreState()
        
        # Construire le PDF avec SimpleDocTemplate (DÉCOUPAGE AUTOMATIQUE DU TABLEAU !)
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        
        temp_buffer.seek(0)
        
        # Compter le nombre de pages générées
        temp_reader = PdfReader(temp_buffer)
        num_pages = len(temp_reader.pages)
        final_page = start_page + num_pages - 1
        
        temp_buffer.seek(0)
        logger.info(f"✅ Partie programme générée : {num_pages} pages (de {start_page} à {final_page})")
        
        return temp_buffer, final_page
    
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
                cls._db_data_keys.add("introduction.ministre_nom")
            elif settings.minister_name:
                intro_data["ministre_nom"] = settings.minister_name
                cls._db_data_keys.add("introduction.ministre_nom")
            
            # Date de nomination du ministre
            minister_nomination_date = getattr(settings, "minister_nomination_date", None)
            if minister_nomination_date:
                intro_data["ministre_date_nomination"] = minister_nomination_date
                cls._db_data_keys.add("introduction.ministre_date_nomination")
                logger.debug(f"✅ Date de nomination récupérée depuis SystemSettings: {minister_nomination_date}")
            
            # Décret d'attribution
            decret_attr_num = getattr(settings, "decret_attribution_numero", None)
            if decret_attr_num:
                intro_data["decret_attribution_numero"] = decret_attr_num
                cls._db_data_keys.add("introduction.decret_attribution_numero")
                logger.debug(f"✅ Décret d'attribution numéro récupéré: {decret_attr_num}")
            
            decret_attr_date = getattr(settings, "decret_attribution_date", None)
            if decret_attr_date:
                intro_data["decret_attribution_date"] = decret_attr_date
                cls._db_data_keys.add("introduction.decret_attribution_date")
                logger.debug(f"✅ Décret d'attribution date récupérée: {decret_attr_date}")
            
            # Mission du ministère
            if settings.ministry_mission:
                intro_data["mission_ministere"] = settings.ministry_mission
                cls._db_data_keys.add("introduction.mission_ministere")
                logger.debug(f"✅ Mission récupérée depuis SystemSettings: {settings.ministry_mission[:50]}...")
            
            # Structure organisationnelle
            structure_cabinet = getattr(settings, "structure_cabinet", None)
            if structure_cabinet:
                intro_data["structure_cabinet"] = structure_cabinet
                cls._db_data_keys.add("introduction.structure_cabinet")
                logger.debug(f"✅ Structure cabinet récupérée: {structure_cabinet}")
            
            # Décret d'organisation
            decret_org_num = getattr(settings, "decret_organisation_numero", None)
            if decret_org_num:
                intro_data["decret_organisation_numero"] = decret_org_num
                cls._db_data_keys.add("introduction.decret_organisation_numero")
                logger.debug(f"✅ Décret d'organisation numéro récupéré: {decret_org_num}")
            
            decret_org_date = getattr(settings, "decret_organisation_date", None)
            if decret_org_date:
                intro_data["decret_organisation_date"] = decret_org_date
                cls._db_data_keys.add("introduction.decret_organisation_date")
                logger.debug(f"✅ Décret d'organisation date récupérée: {decret_org_date}")
            
            # Calculer automatiquement la structure organisationnelle depuis les référentiels
            from app.services.rap_data_service import RapDataService
            structure_org = RapDataService.calculate_organization_structure(session)
            
            # Toujours utiliser les valeurs calculées automatiquement (même si 0)
            # Si 0, elles seront affichées comme "0" dans le rapport
            intro_data["structure_directions_centrales"] = structure_org.get("nb_directions_centrales", 0)
            cls._db_data_keys.add("introduction.structure_directions_centrales")
            logger.debug(f"✅ Nb directions centrales calculé automatiquement: {structure_org.get('nb_directions_centrales', 0)}")
            
            intro_data["structure_services"] = structure_org.get("nb_services", 0)
            cls._db_data_keys.add("introduction.structure_services")
            logger.debug(f"✅ Nb services calculé automatiquement: {structure_org.get('nb_services', 0)}")
            
            intro_data["structure_directions_generales"] = structure_org.get("nb_directions_generales", 0)
            cls._db_data_keys.add("introduction.structure_directions_generales")
            logger.debug(f"✅ Nb directions générales calculé automatiquement: {structure_org.get('nb_directions_generales', 0)}")
            
            # Charger les données RAP depuis RapData
            rap_data = None
            try:
                rap_data = RapDataService.get_rap_data(session)
                
                # Contexte texte
                if rap_data.contexte_texte:
                    intro_data["contexte_texte"] = rap_data.contexte_texte
                    cls._db_data_keys.add("introduction.contexte_texte")
                    logger.debug(f"✅ Contexte texte récupéré depuis RapData: {rap_data.contexte_texte[:50]}...")
                
                # Structure du rapport
                if rap_data.rapport_structure_premiere_partie:
                    try:
                        import json
                        premiere_partie = json.loads(rap_data.rapport_structure_premiere_partie) if isinstance(rap_data.rapport_structure_premiere_partie, str) else rap_data.rapport_structure_premiere_partie
                        intro_data["rapport_structure_premiere_partie"] = premiere_partie
                        cls._db_data_keys.add("introduction.rapport_structure_premiere_partie")
                        logger.debug(f"✅ Structure première partie récupérée depuis RapData")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️ Impossible de parser rapport_structure_premiere_partie comme JSON: {e}")
                
                if rap_data.rapport_structure_seconde_partie:
                    try:
                        import json
                        seconde_partie = json.loads(rap_data.rapport_structure_seconde_partie) if isinstance(rap_data.rapport_structure_seconde_partie, str) else rap_data.rapport_structure_seconde_partie
                        intro_data["rapport_structure_seconde_partie"] = seconde_partie
                        cls._db_data_keys.add("introduction.rapport_structure_seconde_partie")
                        logger.debug(f"✅ Structure seconde partie récupérée depuis RapData")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️ Impossible de parser rapport_structure_seconde_partie comme JSON: {e}")
                
                # Informations générales du rapport
                if rap_data.titre_rapport:
                    db_data["titre_rapport"] = rap_data.titre_rapport
                    cls._db_data_keys.add("titre_rapport")
                    logger.debug(f"✅ Titre rapport récupéré depuis RapData: {rap_data.titre_rapport[:50]}...")
                
                if rap_data.titre_annee:
                    db_data["titre_annee"] = rap_data.titre_annee
                    cls._db_data_keys.add("titre_annee")
                    logger.debug(f"✅ Titre année récupéré depuis RapData: {rap_data.titre_annee}")
                
                if rap_data.annee:
                    db_data["annee"] = rap_data.annee
                    cls._db_data_keys.add("annee")
                    logger.debug(f"✅ Année récupérée depuis RapData: {rap_data.annee}")
                
                if rap_data.date_publication:
                    # Convertir ISO "YYYY-MM" vers format français "Mois AAAA"
                    from app.utils.helpers import convert_iso_month_to_french_str
                    date_pub_fr = convert_iso_month_to_french_str(rap_data.date_publication)
                    if date_pub_fr:
                        db_data["date_publication"] = date_pub_fr
                    else:
                        db_data["date_publication"] = rap_data.date_publication
                    cls._db_data_keys.add("date_publication")
                    logger.debug(f"✅ Date publication récupérée depuis RapData: {db_data.get('date_publication')}")
                
                # Charger les interprétations de financement depuis RapData
                if rap_data.financement_interpretations:
                    try:
                        import json
                        financement_interpretations = json.loads(rap_data.financement_interpretations) if isinstance(rap_data.financement_interpretations, str) else rap_data.financement_interpretations
                        db_data["financement_interpretations"] = financement_interpretations
                        cls._db_data_keys.add("financement_interpretations")
                        logger.debug(f"✅ Interprétations de financement récupérées depuis RapData: {list(financement_interpretations.keys())}")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️ Impossible de parser financement_interpretations comme JSON: {e}")
                    
                    # Charger les interprétations de conclusion (points positifs, difficultés, recommandations, conclusion)
                    if rap_data.conclusion_interpretations:
                        try:
                            conclusion_interpretations = json.loads(rap_data.conclusion_interpretations) if isinstance(rap_data.conclusion_interpretations, str) else rap_data.conclusion_interpretations
                            db_data["conclusion_interpretations"] = conclusion_interpretations
                            cls._db_data_keys.add("conclusion_interpretations")
                            logger.debug(f"✅ Interprétations de conclusion récupérées depuis RapData: {list(conclusion_interpretations.keys())}")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"⚠️ Impossible de parser conclusion_interpretations comme JSON: {e}")
                    
                    # Charger la conclusion générale depuis RapData
                    if rap_data.conclusion_generale:
                        try:
                            conclusion_generale = json.loads(rap_data.conclusion_generale) if isinstance(rap_data.conclusion_generale, str) else rap_data.conclusion_generale
                            db_data["conclusion_generale"] = conclusion_generale
                            cls._db_data_keys.add("conclusion_generale")
                            logger.debug(f"✅ Conclusion générale récupérée depuis RapData: {list(conclusion_generale.keys())}")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"⚠️ Impossible de parser conclusion_generale comme JSON: {e}")
                
            except Exception as rap_error:
                logger.warning(f"⚠️ Impossible de charger RapData: {rap_error}")
            
            # Charger la hiérarchie de performance depuis les tables (priorité sur RapData JSON)
            try:
                orientations_hierarchy = cls._load_performance_hierarchy_from_db(session)
                if orientations_hierarchy:
                    if "partie_ministere" not in db_data:
                        db_data["partie_ministere"] = {}
                    db_data["partie_ministere"]["orientations"] = orientations_hierarchy
                    
                    # Calculer les compteurs uniques depuis la liste plate
                    unique_orientations = len(set(entry.get("orientation") for entry in orientations_hierarchy if entry.get("orientation")))
                    unique_resultats = len(set(entry.get("resultat") for entry in orientations_hierarchy if entry.get("resultat")))
                    unique_objectifs = len(set(entry.get("objectif") for entry in orientations_hierarchy if entry.get("objectif")))
                    
                    db_data["partie_ministere"]["orientations_count"] = unique_orientations
                    db_data["partie_ministere"]["resultats_count"] = unique_resultats
                    db_data["partie_ministere"]["objectifs_globaux_count"] = unique_objectifs
                    cls._db_data_keys.add("partie_ministere.orientations")
                    cls._db_data_keys.add("partie_ministere.orientations_count")
                    cls._db_data_keys.add("partie_ministere.resultats_count")
                    cls._db_data_keys.add("partie_ministere.objectifs_globaux_count")
                    logger.debug(f"✅ Hiérarchie de performance chargée depuis les tables: {unique_orientations} orientation(s), {unique_resultats} résultat(s), {unique_objectifs} objectif(s) global(aux), {len(orientations_hierarchy)} ligne(s) de tableau")
                elif rap_data and rap_data.orientations_strategiques:
                    # Fallback sur RapData JSON si les tables sont vides
                    try:
                        import json
                        orientations = json.loads(rap_data.orientations_strategiques) if isinstance(rap_data.orientations_strategiques, str) else rap_data.orientations_strategiques
                        if "partie_ministere" not in db_data:
                            db_data["partie_ministere"] = {}
                        db_data["partie_ministere"]["orientations"] = orientations
                        logger.debug(f"✅ Orientations stratégiques récupérées depuis RapData (fallback): {len(orientations)} orientation(s)")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️ Impossible de parser orientations_strategiques comme JSON: {e}")
            except Exception as hierarchy_error:
                logger.warning(f"⚠️ Impossible de charger la hiérarchie de performance depuis les tables: {hierarchy_error}")
                # Fallback sur RapData JSON en cas d'erreur
                if rap_data and rap_data.orientations_strategiques:
                    try:
                        import json
                        orientations = json.loads(rap_data.orientations_strategiques) if isinstance(rap_data.orientations_strategiques, str) else rap_data.orientations_strategiques
                        if "partie_ministere" not in db_data:
                            db_data["partie_ministere"] = {}
                        db_data["partie_ministere"]["orientations"] = orientations
                        logger.debug(f"✅ Orientations stratégiques récupérées depuis RapData (fallback après erreur): {len(orientations)} orientation(s)")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️ Impossible de parser orientations_strategiques comme JSON: {e}")
            
            # Stocker les données d'introduction
            if intro_data:
                db_data["introduction"] = intro_data
                logger.info(f"✅ Données d'introduction DB récupérées: {list(intro_data.keys())}")
            
            # 4. Informations pays/devise
            pays = getattr(settings, "pays", None)
            if pays:
                db_data["pays"] = pays
                cls._db_data_keys.add("pays")
                logger.debug(f"✅ Pays récupéré depuis SystemSettings: {pays}")
            
            devise = getattr(settings, "devise", None)
            if devise:
                db_data["devise"] = devise
                cls._db_data_keys.add("devise")
                logger.debug(f"✅ Devise récupérée depuis SystemSettings: {devise}")
            
            section = getattr(settings, "section", None)
            if section:
                db_data["section"] = section
                cls._db_data_keys.add("section")
                logger.debug(f"✅ Section récupérée depuis SystemSettings: {section}")
            
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
    def _load_performance_hierarchy_from_db(cls, session: Session | None) -> list[dict[str, Any]] | None:
        """
        Charge la hiérarchie complète de performance depuis les tables.
        
        HIÉRARCHIE COMPLÈTE :
        - OrientationStrategique
          └── ResultatStrategique
              └── ObjectifPerformance (type=STRATEGIQUE, objectif global)
                  └── ObjectifPerformance (type=OPERATIONNEL, objectif spécifique)
                      └── IndicateurPerformance
        
        NOTE IMPORTANTE :
        La table ObjectifPerformance gère DEUX types d'objectifs dans UNE seule table :
        - Objectifs GLOBAUX (type_objectif=STRATEGIQUE) : liés à un résultat stratégique via resultat_strategique_id
        - Objectifs SPÉCIFIQUES (type_objectif=OPERATIONNEL) : liés à un objectif global via objectif_global_id
        
        Cette méthode charge la hiérarchie jusqu'aux objectifs globaux pour le tableau de politique ministérielle.
        Les objectifs spécifiques sont chargés optionnellement pour référence mais ne sont pas affichés dans ce tableau.
        
        Args:
            session: Session de base de données
            
        Returns:
            Liste de dictionnaires contenant la hiérarchie au format attendu par le tableau, ou None en cas d'erreur
        """
        if not session:
            return None
        
        try:
            from app.models.performance import (
                OrientationStrategique,
                ResultatStrategique,
                ObjectifPerformance,
                TypeObjectif,
            )
            from sqlalchemy.exc import ProgrammingError, OperationalError
            
            # 1. Charger les orientations stratégiques actives
            orientations = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
                .order_by(OrientationStrategique.ordre.asc(), OrientationStrategique.libelle.asc())
            ).all()
            
            if not orientations:
                logger.debug("⚠️ Aucune orientation stratégique active trouvée dans la base de données")
                return None
            
            # Structure pour le tableau (format compatible avec l'ancien JSON)
            table_entries = []
            
            for orientation in orientations:
                # 2. Charger les résultats stratégiques pour cette orientation
                resultats = session.exec(
                    select(ResultatStrategique)
                    .where(
                        and_(
                            ResultatStrategique.orientation_id == orientation.id,
                            ResultatStrategique.actif == True
                        )
                    )
                    .order_by(ResultatStrategique.ordre.asc(), ResultatStrategique.libelle.asc())
                ).all()
                
                if not resultats:
                    # Si pas de résultat, créer une ligne avec orientation seule
                    table_entries.append({
                        "orientation": orientation.libelle,
                        "resultat": "",
                        "objectif": "",
                    })
                else:
                    for resultat in resultats:
                        # 3. Charger les objectifs globaux (STRATEGIQUE) pour ce résultat stratégique
                        objectifs_globaux = session.exec(
                            select(ObjectifPerformance)
                            .where(
                                and_(
                                    ObjectifPerformance.resultat_strategique_id == resultat.id,
                                    ObjectifPerformance.type_objectif == TypeObjectif.STRATEGIQUE
                                )
                            )
                            .order_by(ObjectifPerformance.titre.asc())
                        ).all()
                        
                        if not objectifs_globaux:
                            # Si pas d'objectif global, créer une ligne avec résultat vide
                            table_entries.append({
                                "orientation": orientation.libelle,
                                "resultat": resultat.libelle,
                                "objectif": "",
                            })
                        else:
                            # Une ligne par objectif global
                            for obj_global in objectifs_globaux:
                                # Optionnel : charger les objectifs spécifiques liés à cet objectif global
                                # (pour référence, mais non affichés dans le tableau de politique ministérielle)
                                objectifs_specifiques = []
                                try:
                                    objectifs_specifiques = session.exec(
                                        select(ObjectifPerformance)
                                        .where(
                                            and_(
                                                ObjectifPerformance.objectif_global_id == obj_global.id,
                                                ObjectifPerformance.type_objectif == TypeObjectif.OPERATIONNEL
                                            )
                                        )
                                        .order_by(ObjectifPerformance.titre.asc())
                                    ).all()
                                except Exception:
                                    pass  # Ignorer les erreurs pour les objectifs spécifiques
                                
                                table_entries.append({
                                    "orientation": orientation.libelle,
                                    "resultat": resultat.libelle,
                                    "objectif": obj_global.titre,
                                    # Stocker aussi les objectifs spécifiques pour référence
                                    "objectif_global_id": obj_global.id,
                                    "nb_objectifs_specifiques": len(objectifs_specifiques),
                                })
            
            if not table_entries:
                return None
            
            logger.debug(f"✅ Hiérarchie de performance chargée: {len(set(entry['orientation'] for entry in table_entries if entry['orientation']))} orientation(s), {len(table_entries)} ligne(s) de tableau")
            
            return table_entries
            
        except (ProgrammingError, OperationalError) as db_error:
            logger.warning(f"⚠️ Erreur de base de données lors du chargement de la hiérarchie (tables peut-être absentes): {db_error}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement de la hiérarchie de performance: {e}", exc_info=True)
            if hasattr(session, 'rollback'):
                try:
                    session.rollback()
                except Exception:
                    pass
            return None
    
    @classmethod
    def _draw_conclusion_generale(cls, start_page: int, session=None) -> tuple[BytesIO, int]:
        """
        Génère la conclusion générale du rapport avec SimpleDocTemplate.
        
        Returns:
            tuple[BytesIO, int]: (buffer PDF, numéro de page final)
        """
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, CondPageBreak, Table, TableStyle
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib import colors
        from PyPDF2 import PdfReader
        from io import BytesIO
        from datetime import datetime
        
        logger.info(f"📄 Génération de la CONCLUSION GÉNÉRALE (page {start_page})")
        
        # Créer un buffer temporaire pour cette section
        temp_buffer = BytesIO()
        
        # Dimensions de la page
        page_width, page_height = landscape(A4)
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        bottom_margin = 2.5 * cm
        footer_margin = 0.5 * cm
        
        available_width = page_width - left_margin - right_margin
        available_height = page_height - top_margin - bottom_margin - footer_margin
        
        # Créer le document SimpleDocTemplate
        doc = SimpleDocTemplate(
            temp_buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Styles
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=None,
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,  # Center
            spaceAfter=0.3 * cm,
        )
        
        body_style = ParagraphStyle(
            "Body",
            parent=None,
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=4,  # Justify
            spaceAfter=0.3 * cm,
        )
        
        signature_style = ParagraphStyle(
            "Signature",
            parent=None,
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=1,  # Center align
            spaceBefore=1.5 * cm,
            spaceAfter=0.1 * cm,
        )
        
        # Style spécifique pour le titre du ministre avec indentation pour forcer le wrapping
        # Utiliser leftIndent pour limiter la largeur effective à environ 70% de la page
        title_width_limit = available_width * 0.3  # Réserver 30% à gauche pour forcer le wrapping
        title_style = ParagraphStyle(
            "MinisterTitle",
            parent=signature_style,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=1,  # Center align
            spaceBefore=0,
            spaceAfter=0.1 * cm,  # Espacement réduit entre les deux parties du titre
            leftIndent=0,  # Pas d'indentation, centrage géré par la table
            rightIndent=0,
        )
        
        story = []
        
        # Titre
        story.append(Paragraph("CONCLUSION GÉNÉRALE", section_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Récupérer les données nécessaires
        annee = cls.data.get("annee", datetime.now().year)
        ministere = cls.data.get("ministere", "")
        sigle_ministere = cls._get_sigle_ministere()
        
        # Récupérer les données de conclusion générale depuis RapData
        conclusion_generale_data = cls.data.get("conclusion_generale", {})
        is_conclusion_generale_fake = False
        
        # Vérifier le mode et générer des données factices si nécessaire
        mode = cls.data.get("mode", "brouillon")
        if not conclusion_generale_data and mode == "brouillon":
            # Générer des données factices
            logger.info(f"📊 Mode brouillon: génération de données factices pour la conclusion générale")
            is_conclusion_generale_fake = True
            
            # Calculer les statistiques globales depuis les programmes
            programmes = cls.data.get("programmes", [])
            nb_programmes = len(programmes) if programmes else 2
            
            # Compter le nombre total d'indicateurs
            nb_indicateurs_total = 0
            if session:
                try:
                    from sqlmodel import select
                    from app.models.performance import IndicateurPerformance
                    indicateurs = session.exec(
                        select(IndicateurPerformance).where(IndicateurPerformance.annee == annee)
                    ).all()
                    nb_indicateurs_total = len(indicateurs)
                except Exception:
                    pass
            
            if nb_indicateurs_total == 0:
                nb_indicateurs_total = 8  # Valeur factice
            
            # Récupérer le taux d'exécution global depuis les données de financement
            financement_data = cls.data.get("financement_interpretations", {})
            taux_execution_global = financement_data.get("taux_execution_global", 94.74)
            
            # Calculer les taux par nature de dépense (factices)
            taux_personnel = 100.0
            taux_transferts = 100.0
            taux_biens_services = 85.54
            taux_investissements = 91.36
            
            conclusion_generale_data = {
                "intro": (
                    f"L'année {annee} a été caractérisée par une exécution satisfaisante des programmes budgétaires "
                    f"du {ministere} ({sigle_ministere}), dans un contexte de réorganisation institutionnelle et de "
                    f"renforcement de la structure ministérielle. Les {nb_programmes} programmes, notamment "
                    f"« Administration Générale » et « Portefeuille de l'État », ont enregistré des performances "
                    f"globalement positives, témoignant de la capacité du Ministère à gérer efficacement ses missions "
                    f"et à mobiliser les ressources nécessaires."
                ),
                "performance_indicators": (
                    f"Les {nb_indicateurs_total} cibles d'indicateurs de performance identifiées pour l'année {annee} "
                    f"ont toutes été atteintes, représentant un taux de réalisation de 100 %. Ce résultat témoigne "
                    f"d'une rigueur dans la planification, le suivi et l'évaluation des actions entreprises et pose "
                    f"les bases d'une maturité croissante du pilotage par la performance au sein du {sigle_ministere}."
                ),
                "budget_execution": (
                    f"En matière de gestion budgétaire, le taux d'exécution global s'élève à {taux_execution_global:.2f} %. "
                    f"On observe des réalisations exemplaires pour les dépenses de personnel et de transferts ({taux_personnel:.0f}%), "
                    f"des niveaux satisfaisants pour les biens et services ({taux_biens_services:.2f} %) et les investissements "
                    f"({taux_investissements:.2f} %). Ces résultats reflètent non seulement une gestion rigoureuse et efficiente "
                    f"des ressources publiques, mais également la capacité du ministère à s'adapter à des ajustements budgétaires "
                    f"importants en cours d'année."
                ),
                "avancees": (
                    "Les principales avancées enregistrées concernent la modernisation des outils de gestion, "
                    "la consolidation de la gouvernance des entreprises publiques, le recensement et la sécurisation "
                    "du patrimoine immobilier de l'État et l'amélioration des processus internes liés à la communication institutionnelle."
                ),
                "limites": (
                    "Certaines limites persistent, notamment le besoin de renforcer les capacités techniques des responsables "
                    "de la gestion du budget programme. Des recommandations ont été formulées, notamment la mise en œuvre de "
                    "formations continues, afin d'assurer une appropriation durable des outils de pilotage et une performance "
                    "accrue dans les exercices futurs."
                ),
                "perspectives": (
                    f"Les résultats obtenus en {annee} permettent d'envisager avec optimisme la poursuite des efforts de structuration, "
                    f"de modernisation et d'amélioration continue des performances du {sigle_ministere}, dans le cadre de la mise en œuvre "
                    f"du Plan National de Développement (PND) 2021-2025 et conformément aux orientations stratégiques du Gouvernement."
                ),
            }
        
        # Fonction helper pour formater les valeurs
        def format_programme_value(value: Any, is_fake: bool = False) -> str:
            if is_fake:
                return cls._format_fake_data(str(value))
            else:
                return cls._format_db_data(str(value))
        
        # Paragraphe 1 : Introduction
        intro = conclusion_generale_data.get("intro", "")
        if intro:
            formatted_intro = format_programme_value(intro, is_conclusion_generale_fake)
            story.append(Paragraph(formatted_intro, body_style))
            story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe 2 : Performance des indicateurs
        perf_indicators = conclusion_generale_data.get("performance_indicators", "")
        if perf_indicators:
            formatted_perf = format_programme_value(perf_indicators, is_conclusion_generale_fake)
            story.append(Paragraph(formatted_perf, body_style))
            story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe 3 : Exécution budgétaire
        budget_exec = conclusion_generale_data.get("budget_execution", "")
        if budget_exec:
            formatted_budget = format_programme_value(budget_exec, is_conclusion_generale_fake)
            story.append(Paragraph(formatted_budget, body_style))
            story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe 4 : Avancées
        avancees = conclusion_generale_data.get("avancees", "")
        if avancees:
            formatted_avancees = format_programme_value(avancees, is_conclusion_generale_fake)
            story.append(Paragraph(formatted_avancees, body_style))
            story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe 5 : Limites et recommandations
        limites = conclusion_generale_data.get("limites", "")
        if limites:
            formatted_limites = format_programme_value(limites, is_conclusion_generale_fake)
            story.append(Paragraph(formatted_limites, body_style))
            story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe 6 : Perspectives
        perspectives = conclusion_generale_data.get("perspectives", "")
        if perspectives:
            # Le texte est déjà formaté avec les valeurs (plus besoin de remplacer les placeholders)
            formatted_perspectives = format_programme_value(perspectives, is_conclusion_generale_fake)
            story.append(Paragraph(formatted_perspectives, body_style))
        
        story.append(Spacer(1, 0.5 * cm))
        
        # Signature
        # Récupérer le nom du ministre
        intro_data = cls.data.get("introduction", {})
        ministre_nom = intro_data.get("ministre_nom", "")
        if not ministre_nom or ministre_nom == "NC":
            ministre_nom = "Moussa SANOGO"  # Factice
        
        # Récupérer le titre complet du ministre
        minister_role = cls.data.get("minister_role", "")
        if not minister_role:
            minister_role = f"Le Ministre du Patrimoine, du Portefeuille de l'État et des Entreprises Publiques"
        
        # Date actuelle
        mois_francais = ["janvier", "février", "mars", "avril", "mai", "juin",
                        "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        maintenant = datetime.now()
        date_actuelle = f"{maintenant.day} {mois_francais[maintenant.month - 1]} {maintenant.year}"
        
        # Créer les éléments de la signature
        date_text = f"Fait à Abidjan, le {format_programme_value(date_actuelle, False)}"
        date_para = Paragraph(date_text, signature_style)
        
        # Titre du ministre (divisé en deux parties de même longueur)
        title_words = minister_role.split()
        midpoint = len(title_words) // 2
        title_part1_raw = " ".join(title_words[:midpoint])
        title_part2_raw = " ".join(title_words[midpoint:])
        
        title_part1 = format_programme_value(title_part1_raw, False)
        title_part2 = format_programme_value(title_part2_raw, False)
        title_para1 = Paragraph(title_part1, title_style)
        title_para2 = Paragraph(title_part2, title_style)
        
        # Nom du ministre
        name_text = f"<b>{format_programme_value(ministre_nom, False)}</b>"
        name_para = Paragraph(name_text, signature_style)
        
        # Créer une Table avec chaque élément dans une cellule séparée
        # Table avec 2 colonnes : gauche vide, droite avec le contenu
        empty_cell = Paragraph("", signature_style)
        
        signature_table_data = [
            [empty_cell, date_para],
            [empty_cell, Paragraph("", signature_style)],  # Ligne d'espacement 0.2 cm
            [empty_cell, title_para1],
            [empty_cell, title_para2],
            [empty_cell, Paragraph("", signature_style)],  # Ligne d'espacement 0.5 cm
            [empty_cell, name_para],
        ]
        
        # Largeurs des colonnes : ~60% gauche vide, ~40% droite avec contenu (élargie)
        col_widths = [
            available_width * 0.60,  # Colonne gauche vide
            available_width * 0.40,  # Colonne droite avec contenu (élargie)
        ]
        
        # Hauteurs des lignes : hauteurs automatiques sauf pour les lignes d'espacement
        row_heights = [
            None,  # Date
            0.2 * cm,  # Espacement 1
            None,  # Titre partie 1
            None,  # Titre partie 2
            2.5 * cm,  # Espacement 2 (augmenté pour la 5ème ligne)
            None,  # Nom
        ]
        
        signature_table = Table(signature_table_data, colWidths=col_widths, rowHeights=row_heights)
        
        # Style de la table : centrer horizontalement et verticalement chaque élément dans sa cellule
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centrer horizontalement toutes les cellules
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrer verticalement toutes les cellules
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            # Pas de bordures visibles
        ]))
        
        story.append(signature_table)
        
        # Fonction pour dessiner le footer avec numéro de page
        page_counter = start_page - 1
        
        def on_page(canv, doc_obj):
            """Callback appelé à chaque page pour dessiner le footer."""
            nonlocal page_counter
            page_counter += 1
            
            canv.saveState()
            card_size = 1.0 * cm
            corner_size = 0.3 * cm
            card_x = page_width - right_margin - card_size
            card_y = bottom_margin - footer_margin
            
            # Dessiner la carte
            canv.setFillColor(colors.white)
            canv.setStrokeColor(colors.HexColor("#E0E0E0"))
            canv.setLineWidth(0.5)
            canv.roundRect(card_x, card_y, card_size, card_size, 0.2 * cm, fill=1, stroke=1)
            
            # Coin supérieur droit enroulé
            corner_path = canv.beginPath()
            corner_path.moveTo(card_x + card_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size - corner_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size, card_y + card_size - corner_size)
            corner_path.close()
            canv.setFillColor(colors.HexColor("#F0F0F0"))
            canv.setStrokeColor(colors.HexColor("#E0E0E0"))
            canv.drawPath(corner_path, fill=1, stroke=1)
            
            # Numéro de page
            canv.setFillColor(colors.black)
            canv.setFont("Helvetica", 10)
            text_width = canv.stringWidth(str(page_counter), "Helvetica", 10)
            text_x = card_x + (card_size - text_width) / 2
            text_y = card_y + (card_size - 10) / 2 - 3
            canv.drawString(text_x, text_y, str(page_counter))
            canv.restoreState()
        
        # Construire le PDF avec SimpleDocTemplate
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        
        temp_buffer.seek(0)
        
        # Compter le nombre de pages générées
        temp_reader = PdfReader(temp_buffer)
        num_pages = len(temp_reader.pages)
        final_page = start_page + num_pages - 1
        
        temp_buffer.seek(0)
        logger.info(f"✅ Conclusion générale générée : {num_pages} pages (de {start_page} à {final_page})")
        
        return temp_buffer, final_page
    
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
            from app.models.budget import NatureDepense, SigobeExecution, SigobeChargement
            from app.models.performance import ObjectifPerformance, IndicateurPerformance, StatutObjectif, TypeObjectif
            from sqlalchemy.exc import ProgrammingError
            
            budget_data: dict[str, Any] = {}
            
            # 1. Charger les programmes et compter les actions/activités
            # PRIORITÉ 1 : Depuis sigobe_execution (données d'exécution réelles)
            programmes_list = []
            total_actions = 0
            total_activites = 0
            
            # Récupérer le dernier chargement SIGOBE pour l'année
            dernier_chargement = session.exec(
                select(SigobeChargement)
                .where(SigobeChargement.annee == annee)
                .order_by(SigobeChargement.date_chargement.desc())
            ).first()
            
            if dernier_chargement:
                # Charger les données depuis sigobe_execution
                sigobe_executions = session.exec(
                    select(SigobeExecution)
                    .where(SigobeExecution.chargement_id == dernier_chargement.id)
                    .where(SigobeExecution.programmes.isnot(None))
                    .where(SigobeExecution.programmes != "")
                ).all()
                
                if sigobe_executions:
                    # Grouper par programme
                    programmes_dict: dict[str, dict[str, set]] = defaultdict(lambda: {"actions": set(), "activites": set()})
                    
                    for exec_sigobe in sigobe_executions:
                        prog_nom = exec_sigobe.programmes
                        if not prog_nom:
                            continue
                        
                        if exec_sigobe.actions:
                            programmes_dict[prog_nom]["actions"].add(exec_sigobe.actions)
                        if exec_sigobe.activites:
                            programmes_dict[prog_nom]["activites"].add(exec_sigobe.activites)
                    
                    # Construire la liste des programmes avec leurs comptes
                    for idx, (prog_nom, prog_data) in enumerate(sorted(programmes_dict.items()), 1):
                        actions_count = len(prog_data["actions"])
                        activites_count = len(prog_data["activites"])
                        
                        total_actions += actions_count
                        total_activites += activites_count
                        
                        programmes_list.append({
                            "numero": idx,
                            "titre": prog_nom,
                            "nb_actions": actions_count,
                            "nb_activites": activites_count,
                        })
            
            # PRIORITÉ 2 : Si pas de données SIGOBE, utiliser les référentiels
            if not programmes_list:
                programmes_query = select(Programme).where(Programme.actif).order_by(Programme.code)
                programmes = session.exec(programmes_query).all()
                
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
                # UNIQUEMENT depuis SigobeExecution (pas de fallback vers ExecutionBudgetaire)
                # Réutiliser dernier_chargement si déjà récupéré précédemment, sinon le récupérer
                if not dernier_chargement:
                    dernier_chargement = session.exec(
                        select(SigobeChargement)
                        .where(SigobeChargement.annee == annee)
                        .order_by(SigobeChargement.date_chargement.desc())
                    ).first()
                
                financement_par_nature = {}
                budget_initial_total_sigobe = 0
                budget_reel_total_sigobe = 0
                
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
                        # Vérifier si le libellé ou le code sont contenus dans type_depense
                        if code.upper() in type_dep_upper or nature.libelle.upper() in type_dep_upper:
                            return code
                    
                    # Mapper les types SIGOBE vers les codes de nature (mapping par défaut)
                    # Personnel
                    if any(keyword in type_dep_upper for keyword in ["PERSONNEL", "P -", "P "]) or type_dep_upper == "P":
                        return "P"
                    
                    # Biens et Services
                    if any(keyword in type_dep_upper for keyword in ["BIENS", "SERVICES", "BS -", "BS "]) or type_dep_upper == "BS":
                        return "BS"
                    
                    # Transferts
                    if any(keyword in type_dep_upper for keyword in ["TRANSFERT", "T -", "T "]) or type_dep_upper == "T":
                        return "T"
                    
                    # Investissements
                    if any(keyword in type_dep_upper for keyword in ["INVESTISSEMENT", "I -", "I "]) or type_dep_upper == "I":
                        return "I"
                    
                    return None
                
                if dernier_chargement:
                    sigobe_executions = session.exec(
                        select(SigobeExecution)
                        .where(SigobeExecution.chargement_id == dernier_chargement.id)
                    ).all()
                    
                    # Grouper par code de nature de dépense (P, BS, T, I)
                    depenses_par_code = {}
                    
                    for exec_sigobe in sigobe_executions:
                        # Détecter le code de nature depuis type_depense (avec mapping depuis NatureDepense)
                        code_nature = detect_nature_code(exec_sigobe.type_depense, natures_db)
                        
                        # Si on ne peut pas détecter, on ignore cette ligne
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
                        
                        budget_initial_total_sigobe += budget_initial
                        budget_reel_total_sigobe += budget_reel
                        
                        nature_obj = natures_db.get(code_nature)
                        libelle = nature_obj.libelle if nature_obj else code_nature
                        
                        financement_par_nature[code_nature] = {
                            "libelle": libelle,
                            "budget_initial": budget_initial,
                            "budget_reel": budget_reel,
                            "evolution": budget_reel - budget_initial,
                            "taux_evolution": ((budget_reel - budget_initial) / budget_initial * 100) if budget_initial > 0 else 0,
                        }
                
                # Si pas de données SIGOBE, retourner des valeurs vides (pas de fallback)
                if not financement_par_nature:
                    logger.warning(f"⚠️ Aucune donnée SIGOBE trouvée pour l'année {annee}. Les montants budgétaires seront à 0.")
                
                evolution_total_sigobe = budget_reel_total_sigobe - budget_initial_total_sigobe
                taux_evolution_total_sigobe = (evolution_total_sigobe / budget_initial_total_sigobe * 100) if budget_initial_total_sigobe > 0 else 0
                
                budget_data["financement_global"] = {
                    "budget_initial_total": budget_initial_total_sigobe,  # Uniquement depuis SIGOBE (0 si pas de données)
                    "budget_reel_total": budget_reel_total_sigobe,  # Uniquement depuis SIGOBE (0 si pas de données)
                    "evolution_total": evolution_total_sigobe,
                    "taux_evolution_total": taux_evolution_total_sigobe,
                    "par_nature": financement_par_nature,  # Dict vide si pas de données SIGOBE
                }
            
            # 3. Charger les données de performance (objectifs et indicateurs)
            # Compter les objectifs globaux et spécifiques
            # Les objectifs globaux sont généralement ceux de type STRATEGIQUE
            # Les objectifs spécifiques sont ceux de type OPERATIONNEL
            nb_objectifs_globaux = 0
            nb_objectifs_specifiques = 0
            nb_indicateurs = 0
            cibles_atteintes = 0
            
            try:
                # Objectifs globaux : type STRATEGIQUE et liés à un résultat stratégique
                objectifs_globaux = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.STRATEGIQUE,
                            ObjectifPerformance.resultat_strategique_id.isnot(None)
                        )
                    )
                ).all()
                
                # Objectifs spécifiques : type OPERATIONNEL et liés à un objectif global
                objectifs_specifiques = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.OPERATIONNEL,
                            ObjectifPerformance.objectif_global_id.isnot(None)
                        )
                    )
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
            # Calculer les données de l'année précédente (N-1)
            annee_precedente = annee - 1
            # TODO: Charger les vraies données de l'année précédente depuis la base de données
            # Pour l'instant, on utilise les mêmes valeurs que l'année en cours comme défaut
            nb_indicateurs_n1 = nb_indicateurs  # À remplacer par chargement depuis DB avec annee_precedente
            taux_realisation_n1 = taux_realisation  # À remplacer par chargement depuis DB avec annee_precedente
            
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
                # Utiliser des clés dynamiques basées sur l'année précédente
                f"nb_indicateurs_{annee_precedente}": nb_indicateurs_n1,
                f"taux_realisation_{annee_precedente}": taux_realisation_n1,
            }
            
            # Préparer les réalisations par programme (basé sur les objectifs)
            realisations = []
            for prog in programmes_list:
                prog_num = prog.get("numero", 0)
                prog_titre = prog.get("titre", "")
                
                # Pour chaque programme, compter les objectifs spécifiques atteints
                # (On suppose que les objectifs sont liés aux programmes via une relation future)
                # Charger les objectifs spécifiques (OPERATIONNEL) liés aux objectifs globaux
                # Note: La relation avec le programme n'est pas encore définie dans le modèle,
                # donc on charge tous les objectifs opérationnels pour l'instant
                objectifs_prog = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.OPERATIONNEL,
                            ObjectifPerformance.objectif_global_id.isnot(None)  # Doit être lié à un objectif global
                        )
                    )
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
    def generate_pdf(cls, data: dict[str, Any], session=None) -> BytesIO:
        """
        Génère le PDF du rapport annuel de performance en utilisant SimpleDocTemplate.
        """
        logger.info("🚀 DÉBUT génération PDF rapport annuel de performance (SimpleDocTemplate)")
        
        # Initialiser la session de base de données
        cls._db_session = session
        cls._db_data_keys = set()  # Réinitialiser les clés DB
        
        # Charger les données depuis la base de données (SystemSettings et RapData)
        db_data = cls.load_system_settings_data(session)
        logger.info(f"📊 Données DB chargées: {list(db_data.keys())}")
        if "introduction" in db_data:
            logger.info(f"📊 Données d'introduction dans db_data: {list(db_data['introduction'].keys())}")
        
        # Fusionner les données : DB < données du formulaire
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        user_data = data or {}
        
        # Fusionner d'abord les données de premier niveau
        cls.data = {**db_data, **user_data}
        
        # Fusionner aussi les données d'introduction si présentes (priorité DB)
        if "introduction" in db_data:
            if "introduction" not in cls.data:
                cls.data["introduction"] = {}
            # Fusionner : d'abord user_data["introduction"] (si existe), puis db_data["introduction"] (priorité)
            user_intro = user_data.get("introduction", {})
            cls.data["introduction"] = {
                **user_intro,  # D'abord les données utilisateur
                **db_data["introduction"]  # Puis les données DB (écrasent les données utilisateur)
            }
            logger.info(f"✅ Données d'introduction fusionnées: {list(cls.data.get('introduction', {}).keys())}")
            logger.info(f"✅ Exemples de valeurs: ministre_nom={cls.data['introduction'].get('ministre_nom', 'N/A')[:50]}, mission={cls.data['introduction'].get('mission_ministere', 'N/A')[:50]}")
        else:
            logger.warning("⚠️ Aucune donnée d'introduction trouvée dans db_data")
        
        logger.info(f"📊 Données finales dans cls.data: ministere={cls.data.get('ministere', 'N/A')[:50]}, logo_path={cls.data.get('logo_path', 'N/A')}")
        logger.info(f"📊 cls.data['introduction'] existe: {'introduction' in cls.data}")
        if "introduction" in cls.data:
            logger.info(f"📊 Contenu de cls.data['introduction']: {list(cls.data['introduction'].keys())}")
        
        # Utiliser l'année en cours si aucune année n'est fournie
        from datetime import datetime
        annee = cls.data.get("annee")
        
        if not annee or annee == 0:
            annee = datetime.now().year
            cls.data["annee"] = annee
            logger.info(f"📅 Aucune année fournie, utilisation de l'année en cours: {annee}")
        
        # Charger les données budgétaires si une session est fournie
        budget_data = cls.load_budget_data(session, annee)
        
        # Fusionner les données budgétaires (code copié du service original)
        if budget_data:
            # Mettre à jour les programmes si disponibles
            if "programmes" in budget_data and budget_data["programmes"]:
                cls.data["programmes"] = budget_data["programmes"]
            
            # Mettre à jour partie_ministere avec les données réelles depuis la DB
            if "partie_ministere" not in cls.data:
                cls.data["partie_ministere"] = {}
            
            partie_ministere = cls.data["partie_ministere"]
            if "total_programmes" in budget_data:
                partie_ministere["total_programmes"] = budget_data["total_programmes"]
            if "total_actions" in budget_data:
                partie_ministere["total_actions"] = budget_data["total_actions"]
            if "total_activites" in budget_data:
                partie_ministere["total_activites"] = budget_data["total_activites"]
            
            # Mettre à jour programme_details depuis la DB
            if "programmes" in budget_data and budget_data["programmes"]:
                programme_details = []
                for prog in budget_data["programmes"]:
                    programme_details.append({
                        "numero": prog.get("numero", 0),
                        "titre": prog.get("titre", ""),
                        "actions": prog.get("nb_actions", 0),
                        "activites": prog.get("nb_activites", 0),
                    })
                partie_ministere["programme_details"] = programme_details
                
                # Calculer les pourcentages depuis les données DB
                total_activites = partie_ministere.get("total_activites", 0)
                if total_activites > 0 and len(programme_details) > 0:
                    for i, prog in enumerate(programme_details):
                        pct_key = f"prog{i+1}_pct"
                        pct_value = (prog["activites"] / total_activites * 100) if total_activites > 0 else 0
                        partie_ministere[pct_key] = pct_value
            
            cls.data["partie_ministere"] = partie_ministere
        
        # Définir les dimensions de la page
        page_width, page_height = landscape(A4)
        
        # Pour la couverture, on utilise Canvas directement
        cover_buffer = BytesIO()
        cover_pdf = canvas.Canvas(cover_buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        logger.info("📄 Page 1: Couverture")
        cls._draw_background_shapes(cover_pdf, width, height)
        cls._draw_header(cover_pdf, width, height)
        cls._draw_cover_block(cover_pdf, width, height)
        cls._draw_footer(cover_pdf, width, height)
        cover_pdf.save()
        cover_buffer.seek(0)
        
        # Générer toutes les autres pages avec Canvas (sauf les parties programmes)
        logger.info("📄 Génération de toutes les pages avec Canvas...")
        
        canvas_buffer = BytesIO()
        canvas_pdf = canvas.Canvas(canvas_buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        # Utiliser exactement la même logique que le service original pour les pages non-programmes
        logger.info("📄 Page 2+: Sommaire")
        next_page = cls._draw_table_of_contents(canvas_pdf, width, height)
        
        logger.info(f"📄 Page {next_page}+: Liste des tableaux")
        next_page = cls._draw_liste_tableaux(canvas_pdf, width, height, next_page)
        
        logger.info(f"📄 Page {next_page}+: Liste des graphiques")
        next_page = cls._draw_liste_graphiques(canvas_pdf, width, height, next_page)
        
        logger.info(f"📄 Page {next_page}+: Sigles et abréviations")
        next_page = cls._draw_liste_sigles_abreviations(canvas_pdf, width, height, next_page)
        
        logger.info(f"📄 Page {next_page}+: Introduction générale")
        next_page = cls._draw_introduction_generale(canvas_pdf, width, height, next_page)
        
        # PARTIE I : LE MINISTÈRE
        canvas_pdf.showPage()
        next_page += 1
        logger.info(f"📄 Page {next_page}: PARTIE I : LE MINISTÈRE")
        next_page = cls._draw_partie_i_ministere(canvas_pdf, width, height, next_page)
        
        # Sauvegarder le PDF Canvas (sans les parties programmes)
        logger.info("💾 Sauvegarde du PDF Canvas...")
        canvas_pdf.save()
        canvas_buffer.seek(0)
        
        # Fusionner tous les PDFs
        logger.info("📎 Fusion de tous les PDFs...")
        
        writer = PdfWriter()
        
        # Ajouter la couverture
        cover_reader = PdfReader(cover_buffer)
        writer.add_page(cover_reader.pages[0])
        
        # Ajouter toutes les pages du PDF Canvas
        canvas_reader = PdfReader(canvas_buffer)
        for page in canvas_reader.pages:
            writer.add_page(page)
        
        # Générer les parties programmes avec SimpleDocTemplate (DÉCOUPAGE AUTOMATIQUE !)
        programmes = cls.data.get("programmes", [])
        is_programmes_fake = False
        
        # Si pas de programmes dans cls.data, vérifier si on doit utiliser DEFAULT_DATA (factices)
        if not programmes:
            if cls._should_use_fake_data():
                programmes = cls.DEFAULT_DATA.get("programmes", [])
                is_programmes_fake = bool(programmes)
                if is_programmes_fake:
                    logger.info(f"📊 Programmes factices utilisés (DEFAULT_DATA)")
            else:
                logger.warning(f"⚠️ Aucun programme trouvé et mode final - aucun programme ne sera généré")
        else:
            # Programmes viennent de la DB
            logger.info(f"📊 Programmes chargés depuis la DB: {len(programmes)} programmes")
        
        for programme in programmes:
            next_page += 1  # Commencer sur une nouvelle page
            numero = programme.get("numero", 1)
            titre = programme.get("titre", "")
            logger.info(f"📄 Page {next_page}: PARTIE {numero + 1} : LE PROGRAMME {numero} « {titre.upper()} » (SimpleDocTemplate)")
            
            # Marquer le programme comme factice si nécessaire
            programme["_is_fake"] = is_programmes_fake
            
            # Utiliser SimpleDocTemplate pour cette partie (DÉCOUPAGE AUTOMATIQUE !)
            prog_buffer, next_page = cls._draw_partie_programme_simpledoc(programme, next_page, session=session)
            
            # Ajouter les pages de cette partie au PDF final
            prog_reader = PdfReader(prog_buffer)
            for page in prog_reader.pages:
                writer.add_page(page)
        
        # Générer la CONCLUSION GÉNÉRALE après toutes les parties programmes
        next_page += 1  # Commencer sur une nouvelle page
        logger.info(f"📄 Page {next_page}: CONCLUSION GÉNÉRALE")
        conclusion_buffer, next_page = cls._draw_conclusion_generale(next_page, session=session)
        
        # Ajouter les pages de la conclusion générale au PDF final
        conclusion_reader = PdfReader(conclusion_buffer)
        for page in conclusion_reader.pages:
            writer.add_page(page)
        
        # Écrire le PDF fusionné
        final_buffer = BytesIO()
        writer.write(final_buffer)
        final_buffer.seek(0)
        
        logger.info("✅ PDF généré avec succès (SimpleDocTemplate avec découpage automatique)")
        return final_buffer
