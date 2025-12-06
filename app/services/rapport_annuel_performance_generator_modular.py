"""
Générateur modulaire de Rapport Annuel de Performance utilisant SimpleDocTemplate.

Ce module divise la génération du rapport en plusieurs composants spécialisés :
- RAPBaseGenerator : Classe de base avec constantes et utilitaires communs
- RAPDataLoader : Chargement des données depuis la base de données
- RAPPageManager : Gestion des pages (numérotation, positions, recherche)
- RAPStylingManager : Formatage et styling des données
- RAPFormattingManager : Mise en forme finale (prévention des orphelins)
- RAPLayoutDrawer : Éléments de layout (cover, footer, background)
- RAPContentDrawer : Contenu principal (introduction, partie I, conclusion)
- RAPTableDrawer : Gestion et dessin des tableaux
- RAPChartGenerator : Génération des graphiques
- RAPProgramSectionDrawer : Sections par programme
- RAPPDFGenerator : Orchestrateur principal

Cette architecture modulaire permet une meilleure maintenabilité et réutilisabilité
des composants pour d'autres types de rapports.
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


# ============================================================================
# FLOWABLES PERSONNALISÉS
# ============================================================================

class PageMarker(Flowable):
    """
    Flowable invisible qui enregistre la page où il est rendu.
    
    Utilisé pour tracker les positions des sections dans le PDF.
    Ce marqueur enregistre la page où IL EST RENDU, pas nécessairement
    la page où le Flowable précédent (comme un titre) a été rendu.
    
    Usage:
        marker = PageMarker("section_key")
        story.append(marker)
    """
    def __init__(self, key: str):
        Flowable.__init__(self)
        self.key = key
        self.width = 0
        self.height = 0
    
    def draw(self):
        """Enregistre la page actuelle pour cette clé."""
        try:
            logger.info(f"🔵 PageMarker.draw() appelé pour '{self.key}'")
            
            # Obtenir le numéro de page depuis la variable de classe
            # qui est mise à jour par SimpleDocTemplate callback
            from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator
            current_rendering_page = RAPBaseGenerator._current_rendering_page
            logger.info(f"🔵 PageMarker '{self.key}': _current_rendering_page = {current_rendering_page}")
            
            # Obtenir aussi depuis le canvas pour comparaison
            canvas_page_number = getattr(self.canv, '_pageNumber', None)
            logger.info(f"🔵 PageMarker '{self.key}': canvas._pageNumber = {canvas_page_number} (0-indexé)")
            
            page_num = current_rendering_page
            source = "_current_rendering_page"
            
            if page_num is None:
                # Fallback : essayer d'obtenir depuis le canvas
                canvas_page_0_indexed = getattr(self.canv, '_pageNumber', 0)
                page_num = canvas_page_0_indexed + 1
                source = "canvas._pageNumber (fallback)"
                logger.warning(f"⚠️ PageMarker '{self.key}': _current_rendering_page non défini, utilisation du canvas: {canvas_page_0_indexed} (0-indexé) → {page_num} (1-indexé)")
            
            logger.info(f"🔵 PageMarker '{self.key}': page_num final = {page_num} (source: {source})")
            
            # Enregistrer via RAPPageManager
            from app.services.rapport_annuel_performance_generator_modular import RAPPageManager
            RAPPageManager.register_page_position(self.key, page_num)
            logger.info(f"✅ PageMarker '{self.key}' ENREGISTRÉ à la page {page_num} (source: {source})")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'enregistrement de la page pour '{self.key}': {e}", exc_info=True)


class ParagraphWithMarker(Flowable):
    """
    Combinaison d'un Paragraph avec un PageMarker.
    
    Permet de rendre un paragraphe tout en enregistrant automatiquement
    la page où il apparaît.
    """
    def __init__(self, paragraph: Paragraph, marker_key: str, generator_class: type):
        Flowable.__init__(self)
        self.paragraph = paragraph
        self.marker_key = marker_key
        self.generator_class = generator_class
        self.width = 0
        self.height = 0
    
    def wrap(self, availWidth, availHeight):
        self.width, self.height = self.paragraph.wrap(availWidth, availHeight)
        return self.width, self.height
    
    def split(self, availWidth, availHeight):
        return []
    
    def draw(self):
        self.paragraph.drawOn(self.canv, 0, 0)


class TableTitleFlowable(Flowable):
    """
    Flowable personnalisé pour gérer automatiquement la numérotation des tableaux.
    
    Encapsule la logique de numérotation dans un composant réutilisable.
    Gère automatiquement l'incrémentation du compteur.
    
    Usage:
        title = TableTitleFlowable(
            title_text="Exécution financière par action du programme 1",
            style=subsection_title_style,
            generator_class=RAPTableDrawer
        )
        story.append(title)
    """
    def __init__(self, title_text: str, style: ParagraphStyle, generator_class: type):
        Flowable.__init__(self)
        self.title_text = title_text
        self.style = style
        self.generator_class = generator_class
        
        # Obtenir le numéro de tableau automatiquement
        self.tableau_numero = generator_class.get_next_tableau_numero()
        
        # Créer le Paragraph avec le titre complet
        full_title = f"Tableau {self.tableau_numero}: {title_text}"
        self.paragraph = Paragraph(full_title, style)
        
        # Initialiser les dimensions
        self.width = 0
        self.height = 0
    
    def wrap(self, availWidth, availHeight):
        """Détermine l'espace nécessaire pour le titre."""
        self.width, self.height = self.paragraph.wrap(availWidth, availHeight)
        return self.width, self.height
    
    def split(self, availWidth, availHeight):
        """Ne peut pas être divisé."""
        return []
    
    def draw(self):
        """Dessine le titre du tableau."""
        self.paragraph.drawOn(self.canv, 0, 0)
    
    def get_numero(self) -> int:
        """Retourne le numéro du tableau."""
        return self.tableau_numero


# ============================================================================
# CLASSE DE BASE - CONSTANTES ET UTILITAIRES COMMUNS
# ============================================================================

class RAPBaseGenerator:
    """
    Classe de base contenant les constantes, compteurs et utilitaires communs.
    
    Cette classe centralise :
    - Les constantes de couleurs
    - Les compteurs (tableaux, figures)
    - Les utilitaires de formatage de base
    - Les variables d'état partagées
    
    Utilisée comme classe parente pour toutes les autres classes du générateur.
    """
    
    # ========================================================================
    # CONSTANTES DE COULEURS
    # ========================================================================
    
    PRIMARY_GREEN = colors.HexColor("#39791b")
    SECONDARY_GREEN = colors.HexColor("#609b4d")
    LIGHT_GREEN = colors.HexColor("#387722")
    
    PRIMARY_ORANGE = colors.HexColor("#F26D21")
    LIGHT_ORANGE = colors.HexColor("#ef9543")
    LIGHT_2_ORANGE = colors.HexColor("#ee863d")
    DARK_TEXT = colors.HexColor("#1F1F1F")
    
    # Couleur pour les données provenant de la base de données
    COLOR_DB = colors.HexColor("#FF0000")  # Rouge pour toutes les données (DB)
    
    # ========================================================================
    # VARIABLES DE CLASSE - ÉTAT PARTAGÉ
    # ========================================================================
    
    # Position de la ligne pointillée du bas
    _dotted_line_bottom_y: float | None = None
    
    # Session de base de données
    _db_session: Session | None = None
    
    # Données fusionnées du rapport
    data: dict[str, Any] = {}
    
    # Clés de données DB (pour le styling)
    _db_data_keys: set[str] = set()
    
    # Positions réelles des pages
    _page_positions: dict[str, int] = {}
    
    # Numéro de page actuel pendant le rendu
    _current_rendering_page: int | None = None
    
    # Compteurs pour la numérotation continue
    _tableau_counter: int = 1
    _figure_counter: int = 1
    
    # ========================================================================
    # MÉTHODES DE GESTION DES COMPTEURS
    # ========================================================================
    
    @classmethod
    def get_next_tableau_numero(cls) -> int:
        """
        Retourne le prochain numéro de tableau et incrémente le compteur.
        
        Returns:
            Le numéro de tableau à utiliser
        """
        numero = cls._tableau_counter
        cls._tableau_counter += 1
        return numero
    
    @classmethod
    def reset_tableau_counter(cls, start_value: int = 1):
        """
        Réinitialise le compteur de tableaux.
        
        Args:
            start_value: Valeur de départ pour le compteur (par défaut 1)
        """
        cls._tableau_counter = start_value
    
    @classmethod
    def get_next_figure_numero(cls) -> int:
        """
        Retourne le prochain numéro de figure et incrémente le compteur.
        
        Returns:
            Le numéro de figure à utiliser
        """
        numero = cls._figure_counter
        cls._figure_counter += 1
        return numero
    
    @classmethod
    def reset_figure_counter(cls, start_value: int = 1):
        """
        Réinitialise le compteur de figures.
        
        Args:
            start_value: Valeur de départ pour le compteur (par défaut 1)
        """
        cls._figure_counter = start_value
    
    # ========================================================================
    # UTILITAIRES GÉNÉRAUX
    # ========================================================================
    
    @staticmethod
    def number_to_roman(n: int) -> str:
        """
        Convertit un nombre en chiffres romains.
        
        Args:
            n: Le nombre à convertir
        
        Returns:
            La représentation en chiffres romains
        
        Example:
            >>> number_to_roman(4)
            'IV'
            >>> number_to_roman(10)
            'X'
        """
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
        roman_num = ''
        i = 0
        while n > 0:
            for _ in range(n // val[i]):
                roman_num += syb[i]
                n -= val[i]
            i += 1
        return roman_num
    
    @staticmethod
    def remove_accents(text: str) -> str:
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
    def normalize_text_for_search(text: str) -> str:
        """
        Normalise un texte pour la recherche dans le PDF.
        Enlève les accents, les guillemets, normalise les espaces.
        Gère aussi les caractères dupliqués consécutifs (problème d'extraction PDF).
        
        Args:
            text: Texte à normaliser
            
        Returns:
            Texte normalisé (minuscules, sans accents, sans guillemets, espaces normalisés, sans caractères dupliqués)
        """
        import re
        if not text:
            return ""
        
        # Convertir en minuscules
        text = text.lower()
        
        # Enlever les accents
        text = RAPBaseGenerator.remove_accents(text)
        
        # Remplacer les guillemets par des espaces
        text = text.replace('«', ' ').replace('»', ' ').replace('"', ' ').replace("'", ' ')
        
        # Normaliser les espaces multiples en un seul espace
        text = re.sub(r'\s+', ' ', text)
        
        # Supprimer les caractères dupliqués consécutifs (lettres uniquement, pas les chiffres)
        # Ex: "financièree" -> "financiere", "budgett" -> "budget", "effectiifs" -> "effectifs"
        # Mais "11" reste "11", "22" reste "22", etc.
        # On utilise une regex qui ne supprime que les lettres (a-z, A-Z) dupliquées
        # Itérer plusieurs fois pour gérer les cas comme "cadrres" -> "cadres" (double 'r')
        # ou "financièree" -> "financiere" (double 'e')
        prev_text = ""
        while text != prev_text:
            prev_text = text
            text = re.sub(r'([a-zA-Z])\1+', r'\1', text)
        
        # Normaliser les apostrophes doubles
        text = text.replace("''", "'")
        
        # Enlever les espaces en début et fin
        text = text.strip()
        
        return text
    
    @classmethod
    def should_use_fake_data(cls) -> bool:
        """
        Détermine si on doit utiliser des données factices.
        
        Les données factices ne sont utilisées qu'en mode "brouillon"
        pour permettre de générer un aperçu du rapport même si la base
        de données est vide.
        
        Returns:
            True si on doit utiliser des données factices (mode brouillon), False sinon
        """
        mode = cls.data.get("mode", "brouillon")
        return mode == "brouillon"


# ============================================================================
# GESTIONNAIRE DE PAGES - NUMÉROTATION ET RECHERCHE
# ============================================================================

class RAPPageManager(RAPBaseGenerator):
    """
    Gestionnaire de pages pour le rapport.
    
    Responsabilités :
    - Enregistrement des positions des sections dans le PDF
    - Recherche de texte dans le PDF
    - Gestion de la numérotation des pages
    - Calcul des numéros de page pour le sommaire
    
    Cette classe centralise toute la logique de gestion des pages
    pour faciliter la maintenance et les modifications futures.
    """
    
    @classmethod
    def register_page_position(cls, key: str, page_number: int):
        """
        Enregistre la position d'une page pour une section donnée.
        
        Args:
            key: Clé identifiant la section (ex: "introduction_generale", "programme_1_start")
            page_number: Numéro de page (1-indexé)
        
        Example:
            >>> RAPPageManager.register_page_position("introduction_generale", 5)
            >>> RAPPageManager.get_page_position("introduction_generale")
            5
        """
        old_value = cls._page_positions.get(key)
        if old_value is not None:
            logger.warning(
                f"⚠️ register_page_position: La clé '{key}' existe déjà "
                f"avec la valeur {old_value}, remplacement par {page_number}"
            )
        else:
            logger.info(
                f"📍 register_page_position: Nouvelle clé '{key}' "
                f"enregistrée avec la page {page_number}"
            )
        
        cls._page_positions[key] = page_number
        
        logger.info(
            f"📍 État complet de _page_positions après enregistrement de '{key}' = {page_number}:"
        )
        logger.info(f"   {cls._page_positions}")
    
    @classmethod
    def get_page_position(cls, key: str, default: int = 0) -> int:
        """
        Récupère la position d'une page pour une section donnée.
        
        Args:
            key: Clé identifiant la section
            default: Valeur par défaut si la clé n'existe pas
        
        Returns:
            Le numéro de page ou la valeur par défaut
        """
        return cls._page_positions.get(key, default)
    
    @classmethod
    def find_text_in_pdf(
        cls, 
        pdf_reader: PdfReader, 
        search_text: str, 
        exact_match: bool = False
    ) -> int | None:
        """
        Recherche un texte dans un PDF et retourne le numéro de page où il apparaît.
        
        Cherche dans l'ordre des pages et retourne la première occurrence trouvée.
        Approche similaire à Word : on cherche le texte dans le PDF et on trouve sa page.
        
        Args:
            pdf_reader: Le PdfReader contenant les pages du PDF
            search_text: Le texte à rechercher (ex: "LISTE DES TABLEAUX")
            exact_match: Si True, recherche une correspondance exacte.
                        Si False, recherche une correspondance partielle (insensible à la casse)
        
        Returns:
            Le numéro de page (1-indexé) où le texte a été trouvé, ou None si non trouvé
        
        Example:
            >>> reader = PdfReader("document.pdf")
            >>> RAPPageManager.find_text_in_pdf(reader, "INTRODUCTION GÉNÉRALE")
            5
        """
        search_text_normalized = cls.normalize_text_for_search(search_text)
        
        logger.info(
            f"🔍 Recherche du texte: '{search_text}' "
            f"(normalisé: '{search_text_normalized}') dans {len(pdf_reader.pages)} pages"
        )
        
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            try:
                page_text = page.extract_text()
                if not page_text:
                    continue
                
                page_text_normalized = cls.normalize_text_for_search(page_text)
                
                if exact_match:
                    if search_text_normalized == page_text_normalized.strip():
                        logger.info(
                            f"✅ Texte trouvé exactement sur la page {page_num}: '{search_text}'"
                        )
                        logger.debug(
                            f"   Contenu de la page {page_num}: {page_text_normalized[:200]}"
                        )
                        return page_num
                else:
                    if search_text_normalized in page_text_normalized:
                        logger.info(f"✅ Texte trouvé sur la page {page_num}: '{search_text}'")
                        logger.info(
                            f"   📄 Contenu de la page {page_num} (début): "
                            f"{page_text_normalized[:200]}..."
                        )
                        return page_num
            except Exception as e:
                logger.warning(
                    f"⚠️ Erreur lors de l'extraction du texte de la page {page_num}: {e}"
                )
                continue
        
        logger.warning(f"⚠️ Texte non trouvé dans le PDF: '{search_text}'")
        logger.warning(f"   Texte normalisé recherché: '{search_text_normalized}'")
        
        # Log quelques pages pour aider au débogage
        logger.info(
            f"   📄 Analyse des premières pages du PDF "
            f"({len(pdf_reader.pages)} pages au total):"
        )
        pages_to_check = min(5, len(pdf_reader.pages))
        for i in range(pages_to_check):
            try:
                page = pdf_reader.pages[i]
                page_text = page.extract_text()
                if page_text:
                    page_text_normalized = " ".join(page_text.lower().split())
                    logger.info(f"      Page {i+1}: {page_text_normalized[:150]}...")
                else:
                    logger.info(f"      Page {i+1}: VIDE")
            except Exception as e:
                logger.warning(f"      Page {i+1}: ERREUR d'extraction - {e}")
        
        return None
    
    @classmethod
    def reset_page_tracking(cls):
        """
        Réinitialise le suivi des pages.
        
        Utile lors du début d'une nouvelle génération de rapport.
        """
        cls._page_positions = {}
        cls._current_rendering_page = None
        logger.info("🔄 Suivi des pages réinitialisé")
    
    @classmethod
    def find_text_in_pdf_with_range(
        cls,
        pdf_reader: PdfReader,
        search_text: str,
        start_page: int | None = None,
        end_page: int | None = None
    ) -> int | None:
        """
        Recherche un texte dans un PDF dans une plage de pages spécifique.
        
        Args:
            pdf_reader: Le PdfReader contenant les pages du PDF
            search_text: Le texte à rechercher
            start_page: Numéro de page de début (1-indexé, inclusif). Si None, commence à la page 1.
            end_page: Numéro de page de fin (1-indexé, inclusif). Si None, va jusqu'à la fin.
        
        Returns:
            Le numéro de page (1-indexé) où le texte a été trouvé, ou None si non trouvé
        """
        search_text_normalized = cls.normalize_text_for_search(search_text)
        
        start_idx = (start_page - 1) if start_page else 0
        end_idx = end_page if end_page else len(pdf_reader.pages)
        
        logger.debug(
            f"🔍 Recherche '{search_text}' dans plage pages "
            f"{start_page or 1}-{end_page or len(pdf_reader.pages)} "
            f"(indices {start_idx}-{end_idx})"
        )
        
        for page_num, page in enumerate(pdf_reader.pages[start_idx:end_idx], start=start_idx + 1):
            try:
                page_text = page.extract_text()
                if not page_text:
                    continue
                
                page_text_normalized = cls.normalize_text_for_search(page_text)
                
                if search_text_normalized in page_text_normalized:
                    logger.info(
                        f"✅ Texte trouvé sur la page {page_num} "
                        f"(dans plage {start_page or 1}-{end_page or 'fin'}): '{search_text}'"
                    )
                    logger.debug(f"   Extrait de la page {page_num}: {page_text_normalized[:200]}")
                    return page_num
            except Exception as e:
                logger.warning(
                    f"⚠️ Erreur lors de l'extraction du texte de la page {page_num}: {e}"
                )
                continue
        
        logger.debug(
            f"⚠️ Texte '{search_text}' non trouvé dans la plage "
            f"{start_page or 1}-{end_page or 'fin'}"
        )
        return None
    
    @classmethod
    def extract_title_from_page_text(
        cls,
        page_text: str,
        numero: int,
        type_label: str = "Tableau"
    ) -> str | None:
        """
        Extrait le titre complet d'un tableau ou d'une figure depuis le texte de la page.
        
        Args:
            page_text: Le texte brut de la page
            numero: Le numéro du tableau ou de la figure
            type_label: "Tableau" ou "Figure"
        
        Returns:
            Le titre extrait (sans le préfixe "Tableau X:" ou "Figure X:"), ou None si non trouvé
        """
        import re
        
        # Créer un pattern flexible qui cherche le type + numéro + ":" (insensible à la casse)
        type_pattern = type_label.lower()
        pattern = rf'{type_pattern}\s+{numero}\s*:'
        
        # Chercher le pattern dans le texte (insensible à la casse)
        match = re.search(pattern, page_text, re.IGNORECASE)
        if not match:
            return None
        
        # Extraire le texte après le match
        start_pos = match.end()
        remaining_text = page_text[start_pos:].strip()
        
        # Le titre peut s'étendre sur plusieurs lignes
        lines = remaining_text.split('\n')
        if lines:
            first_line = lines[0].strip()
            title_lines = [first_line]
            
            # Si la première ligne est courte, vérifier la ligne suivante
            if len(first_line) < 50 and len(lines) > 1:
                second_line = lines[1].strip()
                if second_line and (second_line[0].islower() or len(second_line) < 60):
                    title_lines.append(second_line)
            
            title = ' '.join(title_lines).strip()
            
            # Nettoyer le titre
            title = re.sub(r'\s+', ' ', title)
            title = title.rstrip('\r\n\t ')
            
            # Limiter la longueur
            if len(title) > 200:
                title = title[:200].rstrip()
            
            return title if title else None
        
        return None
    
    @classmethod
    def find_tableaux_and_graphiques_pages(
        cls,
        pdf_reader: PdfReader
    ) -> tuple[dict[int, tuple[int, str]], dict[int, tuple[int, str]]]:
        """
        Trouve les numéros de page réels et les titres des tableaux et graphiques dans le PDF.
        
        Recherche uniquement les numéros trouvés dans le PDF, puis extrait le titre complet
        et le numéro de page depuis la page trouvée. Exclut les pages des listes pour éviter
        de trouver les mentions plutôt que les occurrences réelles.
        
        Args:
            pdf_reader: Le PdfReader du PDF complet
        
        Returns:
            Tuple de deux dictionnaires:
            - tableaux_pages: {numero_tableau: (page_num, titre)}
            - graphiques_pages: {numero_graphique: (page_num, titre)}
        """
        import re
        
        tableaux_pages = {}
        graphiques_pages = {}
        
        logger.info("🔍 Recherche des pages des tableaux et graphiques dans le PDF...")
        logger.info(f"📄 PDF contient {len(pdf_reader.pages)} pages")
        
        # Déterminer les pages à exclure (pages des listes)
        exclude_pages = set()
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            try:
                page_text = page.extract_text()
                if page_text:
                    page_text_lower = page_text.lower()
                    if "liste des tableaux" in page_text_lower or "liste des graphiques" in page_text_lower:
                        exclude_pages.add(page_num)
                        logger.info(f"📋 Page {page_num} identifiée comme page de liste (à exclure)")
            except:
                continue
        
        logger.info(f"📋 Pages à exclure de la recherche: {exclude_pages}")
        
        # Collecter TOUS les numéros de tableaux et graphiques trouvés
        tableau_numeros = set()
        figure_numeros = set()
        
        logger.info("🔍 Détection de tous les numéros de tableaux et graphiques dans le PDF...")
        
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            if page_num in exclude_pages:
                continue
            
            try:
                page_text = page.extract_text()
                if not page_text:
                    continue
                
                page_text_normalized = cls.normalize_text_for_search(page_text)
                
                # Chercher tous les "tableau X:" dans cette page
                tableau_matches = re.findall(r'tableau\s+(\d+)\s*:', page_text_normalized, re.IGNORECASE)
                for match in tableau_matches:
                    num = int(match)
                    tableau_numeros.add(num)
                
                # Chercher tous les "figure X:" dans cette page
                figure_matches = re.findall(r'figure\s+(\d+)\s*:', page_text_normalized, re.IGNORECASE)
                for match in figure_matches:
                    num = int(match)
                    figure_numeros.add(num)
            
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors de l'analyse de la page {page_num}: {e}")
                continue
        
        # Trier les numéros
        tableau_numeros_sorted = sorted(tableau_numeros)
        figure_numeros_sorted = sorted(figure_numeros)
        
        logger.info(
            f"📊 Numéros détectés: Tableaux {tableau_numeros_sorted} ({len(tableau_numeros)}), "
            f"Figures {figure_numeros_sorted} ({len(figure_numeros)})"
        )
        
        # Rechercher uniquement les tableaux dont le numéro a été détecté
        logger.info(f"📋 Recherche de {len(tableau_numeros)} tableaux dans le PDF...")
        
        for numero in tableau_numeros_sorted:
            search_pattern = f"tableau\\s*{numero}\\s*:"
            logger.info(f"🔍 Recherche du Tableau {numero}: pattern '{search_pattern}'")
            
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                if page_num in exclude_pages:
                    continue
                
                try:
                    page_text = page.extract_text()
                    if not page_text:
                        continue
                    
                    page_text_normalized = cls.normalize_text_for_search(page_text)
                    
                    if re.search(search_pattern, page_text_normalized, re.IGNORECASE):
                        if numero not in tableaux_pages:
                            title = cls.extract_title_from_page_text(page_text, numero, "Tableau")
                            if title:
                                tableaux_pages[numero] = (page_num, title)
                                logger.info(f"✅ Tableau {numero} trouvé à la page {page_num}: '{title[:80]}...'")
                            else:
                                tableaux_pages[numero] = (page_num, f"Tableau {numero}")
                                logger.warning(
                                    f"⚠️ Tableau {numero} trouvé à la page {page_num} mais titre non extrait"
                                )
                            break
                
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lors de la recherche du Tableau {numero} sur la page {page_num}: {e}")
                    continue
            
            if numero not in tableaux_pages:
                logger.warning(f"⚠️ Tableau {numero} non trouvé")
        
        # Rechercher uniquement les graphiques dont le numéro a été détecté
        logger.info(f"📋 Recherche de {len(figure_numeros)} graphiques dans le PDF...")
        
        for numero in figure_numeros_sorted:
            search_pattern = f"figure\\s*{numero}\\s*:"
            logger.info(f"🔍 Recherche de la Figure {numero}: pattern '{search_pattern}'")
            
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                if page_num in exclude_pages:
                    continue
                
                try:
                    page_text = page.extract_text()
                    if not page_text:
                        continue
                    
                    page_text_normalized = cls.normalize_text_for_search(page_text)
                    
                    if re.search(search_pattern, page_text_normalized, re.IGNORECASE):
                        if numero not in graphiques_pages:
                            title = cls.extract_title_from_page_text(page_text, numero, "Figure")
                            if title:
                                graphiques_pages[numero] = (page_num, title)
                                logger.info(f"✅ Figure {numero} trouvée à la page {page_num}: '{title[:80]}...'")
                            else:
                                graphiques_pages[numero] = (page_num, f"Figure {numero}")
                                logger.warning(
                                    f"⚠️ Figure {numero} trouvée à la page {page_num} mais titre non extrait"
                                )
                            break
                
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lors de la recherche de la Figure {numero} sur la page {page_num}: {e}")
                    continue
            
            if numero not in graphiques_pages:
                logger.warning(f"⚠️ Figure {numero} non trouvée")
        
        logger.info(
            f"✅ Recherche terminée: {len(tableaux_pages)}/{len(tableau_numeros)} tableaux trouvés, "
            f"{len(graphiques_pages)}/{len(figure_numeros)} graphiques trouvés"
        )
        return tableaux_pages, graphiques_pages
    
    @classmethod
    def find_all_toc_pages(
        cls,
        pdf_reader: PdfReader,
        nb_pages_sommaire: int = 0
    ) -> dict[str, int]:
        """
        Trouve les numéros de page pour tous les éléments du sommaire en parcourant le PDF une seule fois.
        
        Approche optimisée : on parcourt le PDF du début à la fin, et à chaque fois qu'on rencontre
        un titre du sommaire, on l'enregistre dans le dictionnaire avec son numéro de page.
        
        Args:
            pdf_reader: Le PdfReader du PDF complet (sans sommaire)
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros de page)
        
        Returns:
            Dictionnaire avec les clés et les numéros de page trouvés
        """
        # La méthode est complètement implémentée ci-dessous
        pages_found = {}
        
        # Récupérer les programmes pour construire les patterns de recherche
        programmes = cls.data.get("programmes", [])
        if not programmes:
            programmes = getattr(cls, "DEFAULT_DATA", {}).get("programmes", [])
        
        # Construire tous les patterns à rechercher avec leurs clés
        # Format: {pattern_normalized: (key, is_program_specific)}
        search_patterns: dict[str, tuple[str, bool]] = {}
        
        # Patterns pour les sections principales (hors programmes)
        main_patterns = {
            "LISTE DES TABLEAUX": "liste_tableaux",
            "LISTE DES GRAPHIQUES": "liste_graphiques",
            "SIGLES ET ABRÉVIATIONS": "sigles_abreviations",
            "INTRODUCTION GÉNÉRALE": "introduction_generale",
            "PARTIE I : LE MINISTÈRE": "partie_i",
            "I. PRÉSENTATION GÉNÉRALE DU MINISTÈRE": "presentation_generale",
            "II. PERFORMANCE GÉNÉRALE DU MINISTÈRE": "performance_generale",
            "III. FINANCEMENT GLOBAL DU MINISTÈRE": "financement_global",
        }
        
        for pattern, key in main_patterns.items():
            pattern_normalized = cls.normalize_text_for_search(pattern)
            search_patterns[pattern_normalized] = (key, False)
        
        # Construire les patterns pour chaque programme
        annee = cls.data.get("annee", "")
        
        for idx, programme in enumerate(programmes):
            numero = programme.get("numero", 1)
            titre = programme.get("titre", "").strip().upper()
            partie_numero = numero + 1
            partie_romain = cls.number_to_roman(partie_numero)
            
            # Titre de partie (plusieurs variantes avec normalisation)
            partie_patterns = [
                f"PARTIE {partie_romain} : LE PROGRAMME {numero} « {titre} »",
                f"PARTIE {partie_numero} : LE PROGRAMME {numero} « {titre} »",
                f"PARTIE {partie_romain}: LE PROGRAMME {numero} « {titre} »",
                f"PARTIE {partie_romain} LE PROGRAMME {numero} {titre}",  # Sans guillemets
            ]
            for pattern in partie_patterns:
                pattern_normalized = cls.normalize_text_for_search(pattern)
                if pattern_normalized not in search_patterns:
                    search_patterns[pattern_normalized] = (f"programme_{numero}_start", True)
            
            # Sections du programme - chercher avec préfixes numériques pour être plus précis
            programme_sections = [
                ("I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", f"programme_{numero}_strategie"),
                ("II. RÉALISATIONS DU PROGRAMME", f"programme_{numero}_realisations"),
                ("III. PERFORMANCE DU PROGRAMME", f"programme_{numero}_performance"),
            ]
            
            # Ajouter aussi les patterns sans préfixe pour tolérance
            programme_sections_without_prefix = [
                ("PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", f"programme_{numero}_strategie"),
                ("RÉALISATIONS DU PROGRAMME", f"programme_{numero}_realisations"),
                ("PERFORMANCE DU PROGRAMME", f"programme_{numero}_performance"),
            ]
            
            # Ajouter d'abord les patterns avec préfixes (plus précis)
            for pattern, key in programme_sections:
                pattern_normalized = cls.normalize_text_for_search(pattern)
                if pattern_normalized not in search_patterns:
                    search_patterns[pattern_normalized] = (key, True)
            
            # Ajouter aussi les patterns sans préfixe comme fallback
            for pattern, key in programme_sections_without_prefix:
                pattern_normalized = cls.normalize_text_for_search(pattern)
                if pattern_normalized not in search_patterns:
                    search_patterns[pattern_normalized] = (key, True)
            
            if numero == 2:
                # Chercher avec préfixe "IV." d'abord, puis sans préfixe comme fallback
                perspectives_with_prefix = cls.normalize_text_for_search("IV. PERSPECTIVES")
                perspectives_normalized = cls.normalize_text_for_search("PERSPECTIVES")
                if perspectives_with_prefix not in search_patterns:
                    search_patterns[perspectives_with_prefix] = (f"programme_{numero}_perspectives", True)
                if perspectives_normalized not in search_patterns:
                    search_patterns[perspectives_normalized] = (f"programme_{numero}_perspectives", True)
        
        # Ajouter "CONCLUSION" - sera géré spécialement car elle peut apparaître plusieurs fois
        conclusion_normalized = cls.normalize_text_for_search("CONCLUSION")
        
        logger.info(f"🔍 Début du parcours unique du PDF ({len(pdf_reader.pages)} pages)")
        logger.info(f"📋 {len(search_patterns)} patterns à rechercher")
        
        # Structure pour stocker toutes les occurrences trouvées dans l'ordre
        # Format: liste de tuples (page_num, key, pattern_found)
        all_occurrences: list[tuple[int, str, str]] = []
        
        # Parcourir le PDF une seule fois, page par page
        for page_num in range(1, len(pdf_reader.pages) + 1):
            try:
                page = pdf_reader.pages[page_num - 1]
                page_text = page.extract_text()
                if not page_text:
                    continue
                
                # Normaliser le texte de la page (avec la même fonction que les patterns)
                page_text_normalized = cls.normalize_text_for_search(page_text)
                
                # Vérifier tous les patterns
                for pattern_normalized, (key, is_program_specific) in search_patterns.items():
                    # Vérifier si le pattern est dans la page
                    if pattern_normalized in page_text_normalized:
                        # Enregistrer cette occurrence (même si on l'a déjà vue)
                        all_occurrences.append((page_num, key, pattern_normalized))
                        logger.debug(f"   Page {page_num}: pattern '{pattern_normalized}' trouvé (key: {key})")
                
                # Vérifier aussi "CONCLUSION" (pas dans search_patterns car multiple occurrences)
                if conclusion_normalized in page_text_normalized:
                    all_occurrences.append((page_num, "CONCLUSION", conclusion_normalized))
                    logger.debug(f"   Page {page_num}: 'CONCLUSION' trouvé")
            
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du traitement de la page {page_num}: {e}")
                continue
        
        logger.info(f"📋 Total occurrences trouvées: {len(all_occurrences)}")
        
        # Maintenant, associer chaque occurrence au bon programme en fonction de l'ordre
        # D'abord, identifier les pages de début de chaque programme
        programme_start_pages = {}  # {num_programme: page_num}
        
        for page_num, key, pattern in all_occurrences:
            if key.startswith("programme_") and key.endswith("_start"):
                prog_num = int(key.split("_")[1])
                programme_start_pages[prog_num] = page_num
                pages_found[key] = page_num + nb_pages_sommaire
                logger.info(f"✅ {key} → page {pages_found[key]} (trouvée à {page_num})")
        
        # Enregistrer les sections principales (hors programmes)
        for page_num, key, pattern in all_occurrences:
            if not key.startswith("programme_"):
                if key not in pages_found:
                    pages_found[key] = page_num + nb_pages_sommaire
                    logger.info(f"✅ {key} → page {pages_found[key]} (trouvée à {page_num})")
        
        # Pour chaque section de programme, trouver la bonne occurrence en fonction de l'ordre
        sorted_programmes = sorted(programme_start_pages.items())
        
        # Grouper les occurrences par programme et type de section
        programme_section_occurrences = {}  # {(prog_num, section_type): [page_num, ...]}
        
        for page_num, key, pattern in all_occurrences:
            if key.startswith("programme_") and not key.endswith("_start"):
                # Extraire le type de section depuis la clé originale
                parts = key.split("_")
                if len(parts) >= 3:
                    section_type = "_".join(parts[2:])  # strategie, realisations, etc.
                    
                    # Trouver le programme dans lequel se trouve cette page
                    assigned_prog_num = None
                    for prog_idx, (prog_num, start_page) in enumerate(sorted_programmes):
                        # Vérifier si on est après le début de ce programme
                        if page_num >= start_page:
                            # Vérifier si on est avant le début du programme suivant
                            next_start_page = len(pdf_reader.pages) + 1
                            if prog_idx < len(sorted_programmes) - 1:
                                next_prog_num, next_start_page = sorted_programmes[prog_idx + 1]
                            
                            if page_num < next_start_page:
                                assigned_prog_num = prog_num
                                break
                    
                    if assigned_prog_num:
                        key_tuple = (assigned_prog_num, section_type)
                        if key_tuple not in programme_section_occurrences:
                            programme_section_occurrences[key_tuple] = []
                        programme_section_occurrences[key_tuple].append(page_num)
        
        # Pour chaque section, prendre la DERNIÈRE occurrence (la plus tardive)
        for (prog_num, section_type), page_nums in programme_section_occurrences.items():
            if page_nums:
                # Prendre la dernière occurrence (page la plus élevée)
                last_page = max(page_nums)
                correct_key = f"programme_{prog_num}_{section_type}"
                pages_found[correct_key] = last_page + nb_pages_sommaire
                logger.info(
                    f"✅ {correct_key} → page {pages_found[correct_key]} "
                    f"(trouvée à {last_page}, dernière occurrence sur {len(page_nums)} trouvées, "
                    f"associé au programme {prog_num})"
                )
        
        # Gérer les introductions des programmes
        for prog_num, start_page in programme_start_pages.items():
            strategie_key = f"programme_{prog_num}_strategie"
            intro_key = f"programme_{prog_num}_intro"
            
            # Déterminer la plage de recherche : du début du programme jusqu'à la stratégie
            strategie_page = None
            if strategie_key in pages_found:
                strategie_page = pages_found[strategie_key] - nb_pages_sommaire
            else:
                strategie_page = start_page + 5  # Chercher dans les 5 premières pages
            
            search_start = start_page
            search_end = min(strategie_page if strategie_page else start_page + 5, len(pdf_reader.pages) + 1)
            
            intro_found = False
            for page_num in range(search_start, search_end):
                try:
                    page = pdf_reader.pages[page_num - 1]
                    page_text = page.extract_text()
                    if page_text:
                        page_normalized = cls.normalize_text_for_search(page_text)
                        # Chercher "INTRODUCTION" comme titre
                        # Vérifier qu'il n'est pas suivi de "GÉNÉRALE"
                        if "introduction" in page_normalized:
                            if "introduction generale" not in page_normalized:
                                pages_found[intro_key] = page_num + nb_pages_sommaire
                                logger.info(
                                    f"✅ {intro_key} → page {pages_found[intro_key]} "
                                    f"(trouvée à {page_num}, dans plage {search_start}-{search_end})"
                                )
                                intro_found = True
                                break
                except:
                    continue
            
            if not intro_found:
                pages_found[intro_key] = start_page + nb_pages_sommaire
                logger.warning(
                    f"⚠️ {intro_key} → page {pages_found[intro_key]} "
                    f"(non trouvée, utilisation de la page de début du programme {start_page} comme fallback)"
                )
        
        # Gérer les conclusions (dernière occurrence dans chaque programme)
        conclusion_occurrences = [page_num for page_num, key, pattern in all_occurrences if key == "CONCLUSION"]
        
        for idx, (prog_num, start_page) in enumerate(sorted_programmes):
            conclusion_key = f"programme_{prog_num}_conclusion"
            
            # Déterminer la fin de la plage de ce programme
            next_start_page = len(pdf_reader.pages) + 1
            if idx < len(sorted_programmes) - 1:
                next_prog_num, next_start_page = sorted_programmes[idx + 1]
            
            # Trouver la dernière conclusion dans cette plage
            for page_num in conclusion_occurrences:
                if start_page <= page_num < next_start_page:
                    pages_found[conclusion_key] = page_num + nb_pages_sommaire
                    logger.info(
                        f"✅ {conclusion_key} → page {pages_found[conclusion_key]} "
                        f"(trouvée à {page_num}, dernière dans plage {start_page}-{next_start_page})"
                    )
        
        # Log des clés manquantes
        expected_keys = [
            "liste_tableaux", "liste_graphiques", "sigles_abreviations",
            "introduction_generale", "partie_i", "presentation_generale",
            "performance_generale", "financement_global",
        ]
        
        # Ajouter les clés attendues pour chaque programme
        for programme in programmes:
            numero = programme.get("numero", 1)
            expected_keys.extend([
                f"programme_{numero}_start",
                f"programme_{numero}_intro",
                f"programme_{numero}_strategie",
                f"programme_{numero}_realisations",
                f"programme_{numero}_performance",
                f"programme_{numero}_conclusion",
            ])
            if numero == 2:
                expected_keys.append(f"programme_{numero}_perspectives")
        
        missing_keys = [k for k in expected_keys if k not in pages_found]
        if missing_keys:
            logger.warning(f"⚠️ Clés non trouvées dans pages_found: {missing_keys}")
            logger.info(f"📋 Clés trouvées ({len(pages_found)}/{len(expected_keys)}): {list(pages_found.keys())}")
        else:
            logger.info(f"✅ Toutes les clés attendues ont été trouvées ({len(pages_found)} éléments)")
        
        logger.info(f"✅ Parcours terminé: {len(pages_found)} éléments trouvés")
        return pages_found


# ============================================================================
# GESTIONNAIRE DE STYLING - FORMATAGE ET STYLES
# ============================================================================

class RAPStylingManager(RAPBaseGenerator):
    """
    Gestionnaire de styling pour le rapport.
    
    Responsabilités :
    - Formatage des données selon leur source (DB, fake)
    - Formatage des montants monétaires (FCFA)
    - Formatage des valeurs de programme et partie
    - Génération des sigles
    - Gestion des couleurs selon les sources
    
    Cette classe centralise toute la logique de formatage pour garantir
    la cohérence visuelle dans tout le rapport.
    """
    
    @classmethod
    def format_db_data(cls, text: str) -> str:
        """
        Formate le texte pour les données provenant de la base de données.
        
        En mode "brouillon", le texte est formaté en rouge pour indiquer
        qu'il provient de la base de données.
        En mode "final", le texte est retourné sans formatage de couleur (tout en noir).
        
        Args:
            text: Le texte à formater
        
        Returns:
            Le texte formaté avec la couleur rouge (mode brouillon) ou sans couleur (mode final)
        
        Example:
            >>> RAPStylingManager.format_db_data("Ministère")
            '<font color="#FF0000">Ministère</font>'  # En mode brouillon
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
    def format_fake_data(cls, text: str) -> str:
        """
        Formate le texte pour les données factices (générées quand la base est vide).
        
        En mode "brouillon", le texte est formaté en violet et italique pour
        indiquer qu'il s'agit de données factices.
        En mode "final", retourne une chaîne vide (pas de données factices affichées).
        
        Args:
            text: Le texte factice à formater
        
        Returns:
            Le texte formaté en violet italique (mode brouillon) ou chaîne vide (mode final)
        
        Example:
            >>> RAPStylingManager.format_fake_data("Programme factice")
            '<font color="#800080"><i>Programme factice</i></font>'  # En mode brouillon
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
    def format_programme_value(cls, value: Any, is_fake: bool = False) -> str:
        """
        Formate une valeur du programme selon si elle est factice ou réelle.
        
        Cette fonction détermine automatiquement si la valeur doit être formatée
        comme une donnée de base de données (rouge) ou comme une donnée factice (violet italique).
        
        Args:
            value: La valeur à formater (peut être n'importe quel type, sera converti en string)
            is_fake: True si la valeur est factice (générée), False si elle vient de la DB
        
        Returns:
            Le texte formaté avec les balises HTML appropriées
        
        Example:
            >>> RAPStylingManager.format_programme_value("ADMINISTRATION GÉNÉRALE", False)
            '<font color="#FF0000">ADMINISTRATION GÉNÉRALE</font>'
            >>> RAPStylingManager.format_programme_value("Programme factice", True)
            '<font color="#800080"><i>Programme factice</i></font>'
        """
        # Si is_fake est True, les données sont factices et doivent être formatées en violet
        if is_fake:
            return cls.format_fake_data(str(value))
        else:
            return cls.format_db_data(str(value))
    
    @classmethod
    def format_partie_value(cls, value: Any, is_fake: bool = False) -> str:
        """
        Formate une valeur pour la Partie I du rapport (similaire à format_programme_value).
        
        Utilisé pour formater les valeurs dans la section "Partie I : Le Ministère".
        La logique est identique à format_programme_value pour maintenir la cohérence.
        
        Args:
            value: La valeur à formater
            is_fake: True si la valeur est factice, False si elle vient de la DB
        
        Returns:
            Le texte formaté avec les balises HTML appropriées
        """
        return cls.format_programme_value(value, is_fake)
    
    @classmethod
    def format_fcfa(cls, montant: float) -> str:
        """
        Formate un montant en FCFA avec espaces comme séparateurs de milliers.
        
        Les montants sont formatés avec des espaces pour séparer les milliers,
        facilitant la lecture des grandes sommes.
        
        Args:
            montant: Le montant à formater (en FCFA)
        
        Returns:
            Le montant formaté avec espaces comme séparateurs
        
        Example:
            >>> RAPStylingManager.format_fcfa(1000000)
            '1 000 000'
            >>> RAPStylingManager.format_fcfa(0)
            '0'
        """
        if montant == 0:
            return "0"
        
        # Formater avec virgules puis remplacer par des espaces
        montant_str = f"{int(montant):,}".replace(",", " ")
        return montant_str
    
    @classmethod
    def get_color_for_source(cls, source: str) -> colors.HexColor:
        """
        Retourne la couleur appropriée selon la source de la donnée.
        
        Dans l'implémentation actuelle, toutes les données proviennent
        de la base de données et sont formatées en rouge.
        
        Args:
            source: La source de la donnée (actuellement toujours "db")
        
        Returns:
            Couleur HexColor (rouge pour DB)
        """
        return cls.COLOR_DB  # Rouge pour toutes les données (DB)
    
    @staticmethod
    def generate_sigle_from_ministere(ministere: str) -> str:
        """
        Génère un sigle automatiquement depuis le nom du ministère.
        
        Le sigle est généré en prenant les initiales des mots significatifs,
        en excluant les articles et prépositions courantes.
        
        Args:
            ministere: Le nom complet du ministère
        
        Returns:
            Le sigle généré (en majuscules)
        
        Example:
            >>> RAPStylingManager.generate_sigle_from_ministere("Ministère du Budget")
            'MB'
            >>> RAPStylingManager.generate_sigle_from_ministere("Ministère du Patrimoine, du Portefeuille de l'État")
            'MPPPE'
        """
        if not ministere:
            return ""
        
        # Mots à exclure (articles, prépositions)
        mots_exclus = {
            "le", "la", "les", "du", "de", "des", "et", "d'", "de la",
            "au", "aux", "en", "pour", "dans", "sur", "avec", "par"
        }
        
        # Supprimer les accents pour faciliter le traitement
        import unicodedata
        ministere_normalized = unicodedata.normalize('NFD', ministere)
        ministere_normalized = ministere_normalized.encode('ascii', 'ignore').decode('ascii')
        
        # Diviser en mots et prendre les initiales
        mots = ministere_normalized.upper().split()
        sigle = ""
        
        for mot in mots:
            # Nettoyer le mot (enlever la ponctuation)
            mot_clean = ''.join(c for c in mot if c.isalnum())
            
            # Ignorer les mots vides ou exclus
            if not mot_clean or mot_clean.lower() in mots_exclus:
                continue
            
            # Prendre la première lettre
            if mot_clean:
                sigle += mot_clean[0]
        
        return sigle
    
    @classmethod
    def get_sigle_ministere(cls) -> str:
        """
        Récupère le sigle du ministère, généré automatiquement depuis le nom.
        
        Le sigle est généré depuis le nom du ministère stocké dans cls.data.
        Si le nom n'est pas disponible, retourne "MPPEEP" par défaut.
        
        Returns:
            Sigle du ministère (ex: "MPPEEP")
        """
        ministere = cls.data.get("ministere", "")
        if not ministere:
            return "MPPEEP"  # Valeur par défaut
        
        return cls.generate_sigle_from_ministere(ministere)
    
    @classmethod
    def _determine_data_source_for_canvas(cls, key: str, value: Any, db_value: Any = None, is_user_explicit: bool = False) -> tuple[Any, str]:
        """
        Détermine la source d'une donnée pour Canvas. Toutes les données sont maintenant considérées comme DB.
        
        Args:
            key: Clé de la donnée
            value: Valeur actuelle dans RAPBaseGenerator.data
            db_value: Valeur provenant de la base de données (ignoré)
            is_user_explicit: Ignoré (toutes les données sont DB)
            
        Returns:
            Tuple (valeur, source: toujours "db")
        """
        # Toutes les données proviennent de la base de données
        return value, "db"
    
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


# ============================================================================
# GESTIONNAIRE DE MISE EN FORME FINALE - PRÉVENTION DES ORPHELINS
# ============================================================================

class RAPFormattingManager(RAPBaseGenerator):
    """
    Gestionnaire de mise en forme finale pour le rapport.
    
    Responsabilités :
    - Prévention des orphelins (titres, tableaux, figures dans les 3 dernières lignes)
    - Gestion des espacements minimums avant les éléments importants
    - Formatage typographique final
    
    Règle typographique :
    Les 3 dernières lignes d'une page ne doivent pas contenir :
    - Un grand titre
    - Un sous-titre
    - Un nom de tableau
    - Un nom de figure
    
    Cette classe fournit des méthodes pour appliquer cette règle.
    """
    
    # ========================================================================
    # CONSTANTES - ESPACEMENT MINIMUM
    # ========================================================================
    
    # Hauteur minimum requise avant un titre/sous-titre/tableau/figure
    # Correspond à environ 3 lignes de texte (avec leading ~14pt)
    # 3 lignes × 14pt leading ≈ 42pt ≈ 1.5 cm
    MIN_SPACE_BEFORE_TITLE = 4.5 * cm  # Espace minimum avant un grand titre
    MIN_SPACE_BEFORE_SUBTITLE = 3.5 * cm  # Espace minimum avant un sous-titre
    MIN_SPACE_BEFORE_TABLE = 3.0 * cm  # Espace minimum avant un tableau
    MIN_SPACE_BEFORE_FIGURE = 3.0 * cm  # Espace minimum avant une figure
    
    # ========================================================================
    # MÉTHODES UTILITAIRES
    # ========================================================================
    
    @classmethod
    def add_orphan_protection_before_title(cls, story: list, is_main_title: bool = True) -> None:
        """
        Ajoute une protection contre les orphelins avant un grand titre.
        
        Utilise CondPageBreak pour forcer un saut de page si l'espace restant
        est insuffisant pour éviter que le titre ne se retrouve dans les 3 dernières lignes.
        
        Args:
            story: Liste des éléments du story où ajouter la protection
            is_main_title: Si True, c'est un grand titre (plus d'espace requis).
                          Si False, c'est un sous-titre.
        
        Usage:
            RAPFormattingManager.add_orphan_protection_before_title(story, is_main_title=True)
            story.append(Paragraph("PARTIE I : LE MINISTÈRE", title_style))
        """
        space_required = cls.MIN_SPACE_BEFORE_TITLE if is_main_title else cls.MIN_SPACE_BEFORE_SUBTITLE
        story.append(CondPageBreak(space_required))
        logger.debug(f"🛡️ Protection orphelin ajoutée: {space_required / cm:.1f} cm avant {'grand titre' if is_main_title else 'sous-titre'}")
    
    @classmethod
    def add_orphan_protection_before_table(cls, story: list) -> None:
        """
        Ajoute une protection contre les orphelins avant un tableau.
        
        Utilise CondPageBreak pour forcer un saut de page si l'espace restant
        est insuffisant pour éviter que le nom du tableau ne se retrouve dans les 3 dernières lignes.
        
        Args:
            story: Liste des éléments du story où ajouter la protection
        
        Usage:
            RAPFormattingManager.add_orphan_protection_before_table(story)
            story.append(table_title)
            story.append(table)
        """
        story.append(CondPageBreak(cls.MIN_SPACE_BEFORE_TABLE))
        logger.debug(f"🛡️ Protection orphelin ajoutée: {cls.MIN_SPACE_BEFORE_TABLE / cm:.1f} cm avant tableau")
    
    @classmethod
    def add_orphan_protection_before_figure(cls, story: list) -> None:
        """
        Ajoute une protection contre les orphelins avant une figure.
        
        Utilise CondPageBreak pour forcer un saut de page si l'espace restant
        est insuffisant pour éviter que le nom de la figure ne se retrouve dans les 3 dernières lignes.
        
        Args:
            story: Liste des éléments du story où ajouter la protection
        
        Usage:
            RAPFormattingManager.add_orphan_protection_before_figure(story)
            story.append(figure_title)
            story.append(figure)
        """
        story.append(CondPageBreak(cls.MIN_SPACE_BEFORE_FIGURE))
        logger.debug(f"🛡️ Protection orphelin ajoutée: {cls.MIN_SPACE_BEFORE_FIGURE / cm:.1f} cm avant figure")
    
    @classmethod
    def add_orphan_protection_before_element(cls, story: list, element_type: str = "title") -> None:
        """
        Ajoute une protection contre les orphelins avant un élément selon son type.
        
        Méthode générique qui choisit l'espace approprié selon le type d'élément.
        
        Args:
            story: Liste des éléments du story où ajouter la protection
            element_type: Type d'élément :
                         - "title" ou "main_title" : Grand titre
                         - "subtitle" : Sous-titre
                         - "table" : Tableau
                         - "figure" : Figure
        
        Usage:
            RAPFormattingManager.add_orphan_protection_before_element(story, "title")
        """
        if element_type in ("title", "main_title"):
            cls.add_orphan_protection_before_title(story, is_main_title=True)
        elif element_type == "subtitle":
            cls.add_orphan_protection_before_title(story, is_main_title=False)
        elif element_type == "table":
            cls.add_orphan_protection_before_table(story)
        elif element_type == "figure":
            cls.add_orphan_protection_before_figure(story)
        else:
            logger.warning(f"⚠️ Type d'élément non reconnu pour protection orphelin: {element_type}")
    
    @classmethod
    def is_title_element(cls, text: str) -> bool:
        """
        Vérifie si un texte est un titre (grand titre ou sous-titre).
        
        Args:
            text: Texte à vérifier
        
        Returns:
            True si le texte semble être un titre, False sinon
        """
        if not text:
            return False
        
        # Nettoyer le HTML pour vérifier le texte brut
        import re
        text_clean = re.sub(r'<[^>]+>', '', text)
        text_clean = text_clean.strip().upper()
        
        # Patterns typiques des titres
        title_patterns = [
            r'^PARTIE\s+[IVX]+',
            r'^[IVX]+\.\s+',
            r'^[A-Z][A-Z\s]+:',  # Titres en majuscules suivis de deux points
            r'^TABLEAU\s+\d+',
            r'^FIGURE\s+\d+',
            r'^INTRODUCTION',
            r'^CONCLUSION',
            r'^SOMMAIRE',
            r'^LISTE\s+DES',
        ]
        
        for pattern in title_patterns:
            if re.match(pattern, text_clean):
                return True
        
        return False
    
    @classmethod
    def is_table_or_figure_title(cls, text: str) -> bool:
        """
        Vérifie si un texte est un titre de tableau ou de figure.
        
        Args:
            text: Texte à vérifier
        
        Returns:
            True si le texte est un titre de tableau ou figure, False sinon
        """
        if not text:
            return False
        
        # Nettoyer le HTML
        import re
        text_clean = re.sub(r'<[^>]+>', '', text)
        text_clean = text_clean.strip().upper()
        
        # Patterns pour tableaux et figures
        patterns = [
            r'^TABLEAU\s+\d+',
            r'^FIGURE\s+\d+',
        ]
        
        for pattern in patterns:
            if re.match(pattern, text_clean):
                return True
        
        return False
    
    @classmethod
    def draw_reference_lines_for_last_lines(cls, pdf: canvas.Canvas, width: float, bottom_margin: float, footer_height: float, footer_margin: float, left_margin: float = 2 * cm, right_margin: float = 2 * cm) -> None:
        """
        Dessine des lignes de référence visuelles pour marquer la zone des 3 dernières lignes.
        
        Cette méthode dessine des lignes horizontales pointillées pour indiquer visuellement
        la zone où les titres, tableaux et figures ne doivent PAS apparaître (les 3 dernières lignes).
        
        Les lignes sont dessinées :
        - Une ligne supérieure à 3 lignes du bas de la zone de contenu
        - Une ligne inférieure à 1 ligne du bas de la zone de contenu
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            bottom_margin: Marge du bas de la page
            footer_height: Hauteur du footer
            footer_margin: Marge du footer depuis le bas
            left_margin: Marge gauche (par défaut 2 cm)
            right_margin: Marge droite (par défaut 2 cm)
        
        Note:
            Ces lignes sont des guides visuels pour vérifier que les éléments importants
            ne se retrouvent pas dans les 3 dernières lignes d'une page.
        """
        pdf.saveState()
        
        # Calculer la zone des 3 dernières lignes depuis le bas de la page
        # bottom_margin représente déjà la zone réservée pour le footer (footer_height + footer_margin)
        # La zone de contenu se termine à bottom_margin depuis le bas de la page
        
        # Hauteur d'une ligne de texte (approximativement 14pt de leading)
        # 14pt ≈ 0.493 cm, arrondi à 0.5 cm
        line_height = 0.5 * cm
        
        # Zone des 3 dernières lignes = 3 × hauteur de ligne
        three_lines_height = 3 * line_height
        
        # Position de la ligne supérieure de la zone interdite
        # (3 lignes au-dessus du bas de la zone de contenu = bottom_margin + 3 lignes)
        upper_line_y = bottom_margin + three_lines_height
        
        # Position de la ligne inférieure de la zone interdite
        # (juste au-dessus du bas de la zone de contenu = bottom_margin)
        lower_line_y = bottom_margin
        
        # Dessiner les lignes de référence (en pointillés rouges pour visibilité)
        pdf.setStrokeColor(colors.HexColor("#FF6B6B"))  # Rouge clair pour visibilité
        pdf.setLineWidth(0.5)
        pdf.setDash([3, 3])  # Pointillés
        
        # Ligne supérieure (début de la zone interdite)
        pdf.line(left_margin, upper_line_y, width - right_margin, upper_line_y)
        
        # Ligne inférieure (fin de la zone interdite)
        pdf.line(left_margin, lower_line_y, width - right_margin, lower_line_y)
        
        # Optionnel : Ajouter une zone de fond légèrement colorée pour plus de visibilité
        pdf.setFillColor(colors.HexColor("#FFE5E5"))  # Rouge très clair, presque transparent
        pdf.setFillAlpha(0.3)  # 30% d'opacité
        pdf.rect(
            left_margin,
            lower_line_y,
            width - left_margin - right_margin,
            three_lines_height,
            stroke=0,
            fill=1
        )
        pdf.setFillAlpha(1.0)  # Remettre à 100% pour la suite
        
        # Remettre le style de ligne à normal
        pdf.setDash()
        
        pdf.restoreState()
        
        logger.debug(f"📏 Lignes de référence dessinées: zone interdite de {lower_line_y / cm:.2f} cm à {upper_line_y / cm:.2f} cm")


# ============================================================================
# GESTIONNAIRE DE CHARGEMENT DE DONNÉES - BASE DE DONNÉES
# ============================================================================

class RAPDataLoader(RAPBaseGenerator):
    """
    Gestionnaire de chargement de données depuis la base de données.
    
    Responsabilités :
    - Chargement des paramètres système (SystemSettings)
    - Chargement des données RAP (RapData)
    - Chargement des données budgétaires (SigobeExecution)
    - Chargement des données de performance (hiérarchie complète)
    - Chargement des données spécifiques par programme :
      * Investissements
      * Activités majeures
      * Indicateurs de performance
      * Effectifs
    
    Cette classe centralise toute la logique d'accès à la base de données
    pour garantir la cohérence et faciliter la maintenance.
    
    Note importante :
    Toutes les méthodes de cette classe doivent marquer les données chargées
    dans cls._db_data_keys pour permettre le formatage approprié (rouge pour DB).
    """
    
    @classmethod
    def load_system_settings_data(cls, session: Session | None) -> dict[str, Any]:
        """
        Charge les données depuis SystemSettings et RapData.
        
        Cette méthode est la méthode principale de chargement des données.
        Elle charge :
        - Les paramètres système (nom du ministère, logo, etc.)
        - Les données d'introduction (ministre, décrets, mission, structure)
        - Les données RAP (titre, année, structures, interprétations)
        - La hiérarchie de performance (orientations stratégiques)
        
        Args:
            session: Session de base de données (peut être None)
        
        Returns:
            Dictionnaire contenant toutes les données chargées depuis la DB,
            organisées par sections (introduction, partie_ministere, etc.)
        
        Note:
            Toutes les clés de données chargées sont ajoutées à cls._db_data_keys
            pour le formatage approprié dans le rapport.
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
                orientations_hierarchy = cls.load_performance_hierarchy_from_db(session)
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
    def load_budget_data(cls, session: Session | None, annee: int) -> dict[str, Any]:
        """
        Charge les données budgétaires depuis la base de données.
        
        Cette méthode charge :
        - Les programmes avec leurs budgets
        - Les actions par programme
        - Les activités par action
        - Les données de performance (objectifs, indicateurs)
        
        Args:
            session: Session de base de données
            annee: Année pour laquelle charger les données
        
        Returns:
            Dictionnaire contenant :
            - programmes: Liste des programmes avec leurs budgets
            - partie_data: Données pour la partie I du rapport
            - performance: Données de performance globale
        
        Note:
            Cette méthode est très volumineuse (environ 500 lignes).
            Elle sera migrée progressivement depuis rapport_annuel_performance_service_simpledoc.py
            ligne 12273 - load_budget_data()
        """
        if not session:
            return {}
        
        try:
            from app.models.budget import ExecutionBudgetaire, ActionBudgetaire, ActiviteBudgetaire, FicheTechnique
            from app.models.personnel import Programme
            from app.models.budget import NatureDepense, SigobeExecution, SigobeChargement
            from app.models.performance import ObjectifPerformance, IndicateurPerformance, StatutObjectif, TypeObjectif
            from sqlalchemy.exc import ProgrammingError
            from decimal import Decimal
            
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
                taux_execution_avg = taux_mandatement_avg
                
                budget_data["execution"] = {
                    "total_budget_vote": total_budget_vote,
                    "total_engagements": total_engagements,
                    "total_mandats_pec": total_mandats_pec,
                    "taux_engagement": taux_engagement_avg,
                    "taux_mandatement": taux_mandatement_avg,
                    "taux_execution": taux_execution_avg,
                }
                
                # 2.1. Charger les données par nature de dépense pour le financement global
                # UNIQUEMENT depuis SigobeExecution
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
                
                if not financement_par_nature:
                    logger.warning(f"⚠️ Aucune donnée SIGOBE trouvée pour l'année {annee}. Les montants budgétaires seront à 0.")
                
                evolution_total_sigobe = budget_reel_total_sigobe - budget_initial_total_sigobe
                taux_evolution_total_sigobe = (evolution_total_sigobe / budget_initial_total_sigobe * 100) if budget_initial_total_sigobe > 0 else 0
                
                budget_data["financement_global"] = {
                    "budget_initial_total": budget_initial_total_sigobe,
                    "budget_reel_total": budget_reel_total_sigobe,
                    "evolution_total": evolution_total_sigobe,
                    "taux_evolution_total": taux_evolution_total_sigobe,
                    "par_nature": financement_par_nature,
                }
            
            # 3. Charger les données de performance (objectifs et indicateurs)
            nb_objectifs_globaux = 0
            nb_objectifs_specifiques = 0
            nb_indicateurs = 0
            cibles_atteintes = 0
            
            try:
                # Objectifs globaux : type GLOBAL (liés à un résultat stratégique)
                objectifs_globaux = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL,
                            ObjectifPerformance.resultat_strategique_id.isnot(None)
                        )
                    )
                ).all()
                
                # Objectifs spécifiques : type SPECIFIQUE (liés à un objectif global)
                objectifs_specifiques = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE,
                            ObjectifPerformance.objectif_global_id.isnot(None)
                        )
                    )
                ).all()
                
                nb_objectifs_globaux = len(objectifs_globaux)
                nb_objectifs_specifiques = len(objectifs_specifiques)
                
                # Compter les indicateurs
                try:
                    indicateurs = session.exec(
                        select(IndicateurPerformance).where(IndicateurPerformance.actif)
                    ).all()
                    nb_indicateurs = len(indicateurs)
                    
                    # Compter les cibles atteintes
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
            
            nb_cibles = nb_indicateurs
            
            # Calculer le taux de réalisation
            taux_realisation = (cibles_atteintes / nb_cibles * 100) if nb_cibles > 0 else 0
            
            # Calculer les données de l'année précédente (N-1)
            annee_precedente = annee - 1
            nb_indicateurs_n1 = nb_indicateurs  # À améliorer avec chargement depuis DB
            taux_realisation_n1 = taux_realisation  # À améliorer avec chargement depuis DB
            
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
                f"nb_indicateurs_{annee_precedente}": nb_indicateurs_n1,
                f"taux_realisation_{annee_precedente}": taux_realisation_n1,
            }
            
            # Préparer les réalisations par programme
            realisations = []
            for prog in programmes_list:
                prog_num = prog.get("numero", 0)
                prog_titre = prog.get("titre", "")
                
                objectifs_prog = session.exec(
                    select(ObjectifPerformance).where(
                        and_(
                            ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE,
                            ObjectifPerformance.objectif_global_id.isnot(None)
                        )
                    )
                ).first()
                
                if objectifs_prog:
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
                                "objectif_specifique": f"OS {prog_num}: Améliorer...",
                                "nb_cibles": nb_cibles_os,
                                "nb_cibles_atteintes": nb_cibles_atteintes_os,
                            })
                    except (ProgrammingError, AttributeError) as os_error:
                        logger.warning(f"⚠️ Erreur lors du chargement des indicateurs pour l'objectif: {os_error}")
                        try:
                            session.rollback()
                        except Exception:
                            pass
            
            if realisations:
                budget_data["performance"]["realisations"] = realisations
            
            logger.info(
                f"✅ Données budgétaires chargées: {len(programmes_list)} programmes, "
                f"{total_actions} actions, {total_activites} activités"
            )
            logger.info(
                f"✅ Données de performance chargées: {nb_objectifs_globaux} OG, "
                f"{nb_objectifs_specifiques} OS, {nb_indicateurs} indicateurs"
            )
            return budget_data
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données budgétaires: {e}", exc_info=True)
            return {}
    
    @classmethod
    def get_investissement_data(cls, numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les données d'investissement pour un programme depuis la base de données.
        
        Charge les projets d'investissement depuis SigobeExecution pour un programme donné.
        Groupe les données par projet et accumule les montants.
        
        Args:
            numero: Numéro du programme
            titre: Titre du programme (utilisé pour filtrer dans SigobeExecution)
            annee: Année pour laquelle charger les données
            session: Session de base de données
        
        Returns:
            Liste de dictionnaires contenant les projets d'investissement avec :
            - nom: Nom du projet
            - annee_debut: Année de début
            - annee_fin: Année de fin
            - cout_total_interieur/exterieur: Coûts totaux
            - budget_vote_X_interieur/exterieur: Budgets votés
            - budget_actuel_X_interieur/exterieur: Budgets actuels
            - ordonnancement_X_interieur/exterieur: Ordonnancements
        
        Note:
            Retourne une liste vide si aucune donnée n'est trouvée.
            En mode brouillon, des données factices peuvent être générées.
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
        if not investissement_projects and cls.should_use_fake_data():
            logger.info(f"📊 Mode brouillon: génération de données factices variées pour les investissements")
            return RAPFakeDataLoader.get_fake_investissements(annee)
        
        return investissement_projects
    
    @classmethod
    def get_activites_majeures(cls, numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les activités majeures pour un programme depuis la base de données.
        
        Les activités majeures sont déterminées par leur taux d'exécution.
        Seules les activités avec un taux d'exécution > 0 sont considérées.
        
        Args:
            numero: Numéro du programme
            titre: Titre du programme
            annee: Année pour laquelle charger les données
            session: Session de base de données
        
        Returns:
            Liste de dictionnaires contenant les activités majeures avec :
            - nom: Nom de l'activité
            - taux_execution: Taux d'exécution de l'activité
            - montant_budget: Montant budgétaire
        
        Note:
            Les activités sont triées par taux d'exécution décroissant.
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
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
        if mode == "final":
            return []
        # Générer des données factices en mode brouillon avec le flag _is_fake
        logger.info(f"📊 Mode brouillon: génération de données factices pour les activités majeures")
        return RAPFakeDataLoader.get_fake_activites_majeures()
    
    @classmethod
    def get_indicateurs_performance_data(cls, numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les indicateurs de performance pour un programme depuis la base de données.
        
        Charge la hiérarchie complète : Objectifs Spécifiques (OS) -> Indicateurs.
        Pour chaque indicateur, charge les valeurs historiques (N-3, N-2, N-1, N).
        
        Args:
            numero: Numéro du programme
            titre: Titre du programme
            annee: Année courante (N)
            session: Session de base de données
        
        Returns:
            Liste de dictionnaires contenant les indicateurs avec :
            - objectif_specifique: Nom de l'OS
            - indicateur_numero: Numéro de l'indicateur
            - indicateur_nom: Nom de l'indicateur
            - valeurs: Dict avec les valeurs pour chaque année (N-3, N-2, N-1, N)
            - cible: Valeur cible de l'indicateur
        
        Note:
            Les indicateurs sont organisés par OS.
            Les valeurs historiques sont chargées depuis la colonne 'annee' de IndicateurPerformance.
        """
        # Calculer les années dynamiquement
        annee_n_3 = annee - 3
        annee_n_2 = annee - 2
        annee_n_1 = annee - 1
        annee_n = annee
        
        # Données par défaut : structure avec 3 OS et plusieurs indicateurs chacun
        default_indicateurs = RAPFakeDataLoader.get_fake_indicateurs_performance(titre, annee)
        
        # Récupérer les données depuis la base de données
        if session:
            try:
                from sqlmodel import select, and_
                from app.models.performance import ObjectifPerformance, IndicateurPerformance
                from sqlalchemy.exc import ProgrammingError, InternalError
                
                # Récupérer tous les indicateurs actifs avec leurs objectifs
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
                        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
                        if mode == "final":
                            return []
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
                    mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
                    if mode == "final":
                        logger.info("⚠️ Pas de données disponibles pour les indicateurs (migration non appliquée)")
                        return []
                    logger.info("📊 Mode brouillon: génération de données factices pour les indicateurs (migration non appliquée)")
                    return default_indicateurs
                
                # Grouper les indicateurs par objectif et nom
                indicateurs_groupes: dict[tuple[int, str], dict[str, Any]] = {}
                
                for ind in indicateurs:
                    key = (ind.objectif_id, ind.nom)
                    
                    if key not in indicateurs_groupes:
                        objectif = objectifs_dict.get(ind.objectif_id)
                        objectif_titre = f"Objectif Spécifique: {objectif.titre}" if objectif else f"Objectif {ind.objectif_id}"
                        
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
                            "_source": "db",
                        }
                    
                    # Mapper les valeurs selon l'année (N, N-1, N-2, N-3)
                    if ind.annee == annee_n:
                        indicateurs_groupes[key][f"prevision_{annee_n}"] = float(ind.valeur_cible) if ind.valeur_cible else None
                        indicateurs_groupes[key][f"realisation_{annee_n}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                        if ind.nb_activites:
                            indicateurs_groupes[key]["nb_activites"] = ind.nb_activites
                    elif ind.annee == annee_n_1:
                        indicateurs_groupes[key][f"realisation_{annee_n_1}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                    elif ind.annee == annee_n_2:
                        indicateurs_groupes[key][f"realisation_{annee_n_2}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                    elif ind.annee == annee_n_3:
                        indicateurs_groupes[key][f"realisation_{annee_n_3}"] = float(ind.valeur_actuelle) if ind.valeur_actuelle else None
                
                # Convertir le dictionnaire en liste
                result = list(indicateurs_groupes.values())
                
                if result:
                    logger.info(f"✅ {len(result)} indicateur(s) récupéré(s) depuis la base de données")
                    return result
                else:
                    logger.warning("⚠️ Aucun indicateur valide trouvé")
                    mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
                    if mode == "final":
                        return []
                    logger.info(f"📊 Mode brouillon: génération de données factices pour les indicateurs")
                    return default_indicateurs
                    
            except Exception as e:
                logger.exception(f"⚠️ Erreur lors de la récupération des indicateurs: {e}")
                try:
                    session.rollback()
                except Exception:
                    pass
                mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
                if mode == "final":
                    return []
                logger.info(f"📊 Mode brouillon: génération de données factices pour les indicateurs (après erreur)")
                return default_indicateurs
        
        # Si pas de session, en mode brouillon retourner des données factices
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
        if mode == "final":
            return []
        logger.info(f"📊 Mode brouillon: génération de données factices pour les indicateurs (pas de session)")
        return default_indicateurs
    
    @classmethod
    def get_effectifs_data(cls, numero: int, titre: str, annee: int, session) -> list[dict[str, Any]]:
        """
        Récupère les données d'effectifs pour un programme depuis la base de données.
        
        Charge les effectifs par catégorie (Titulaires, Contractuels, etc.)
        pour les années N-1 et N.
        
        Args:
            numero: Numéro du programme
            titre: Titre du programme
            annee: Année courante (N)
            session: Session de base de données
        
        Returns:
            Liste de dictionnaires contenant les effectifs par catégorie avec :
            - categorie: Nom de la catégorie (Titulaires, Contractuels, etc.)
            - effectif_n_minus_1: Effectif pour l'année N-1
            - effectif_n: Effectif pour l'année N
            - evolution: Évolution entre N-1 et N
        
        Note:
            Les données sont chargées depuis AgentComplet et filtrées par programme.
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
                    mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
                    if mode == "final":
                        return []
                    # Générer des données factices en mode brouillon avec le flag _is_fake
                    logger.info(f"📊 Mode brouillon: génération de données factices pour les effectifs")
                    return RAPFakeDataLoader.get_fake_effectifs(annee)
                
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
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') else "brouillon"
            if mode == "final":
                return []
            # Générer des données factices en mode brouillon
            logger.info(f"📊 Mode brouillon: génération de données factices pour les effectifs")
            return RAPFakeDataLoader.get_fake_effectifs(annee)
        
        return effectifs_list
    
    @classmethod
    def load_performance_hierarchy_from_db(cls, session: Session | None) -> list[dict[str, Any]] | None:
        """
        Charge la hiérarchie complète de performance depuis les tables.
        
        HIÉRARCHIE COMPLÈTE :
        - OrientationStrategique
          └── ResultatStrategique
              └── ObjectifPerformance (type=GLOBAL, objectif global, lié à un résultat stratégique)
                  └── ObjectifPerformance (type=SPECIFIQUE, objectif spécifique, lié à un objectif global)
                      └── IndicateurPerformance
        
        Cette méthode charge la hiérarchie jusqu'aux objectifs globaux
        pour le tableau de politique ministérielle.
        
        Args:
            session: Session de base de données
        
        Returns:
            Liste de dictionnaires contenant la hiérarchie au format plat :
            - orientation: Nom de l'orientation stratégique
            - resultat: Nom du résultat stratégique
            - objectif: Nom de l'objectif global
            - objectif_specifique: Nom de l'objectif spécifique (optionnel)
            - indicateur: Nom de l'indicateur (optionnel)
        
        Note:
            La table ObjectifPerformance gère DEUX types d'objectifs :
            - Objectifs GLOBAUX (type_objectif=GLOBAL, liés à un résultat stratégique)
            - Objectifs SPÉCIFIQUES (type_objectif=SPECIFIQUE, liés à un objectif global)
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
                        # 3. Charger les objectifs globaux (GLOBAL) pour ce résultat stratégique
                        objectifs_globaux = session.exec(
                            select(ObjectifPerformance)
                            .where(
                                and_(
                                    ObjectifPerformance.resultat_strategique_id == resultat.id,
                                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL
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
                                objectifs_specifiques = []
                                try:
                                    objectifs_specifiques = session.exec(
                                        select(ObjectifPerformance)
                                        .where(
                                            and_(
                                                ObjectifPerformance.objectif_global_id == obj_global.id,
                                                ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE
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
                                    "objectif_global_id": obj_global.id,
                                    "nb_objectifs_specifiques": len(objectifs_specifiques),
                                })
            
            if not table_entries:
                return None
            
            logger.debug(
                f"✅ Hiérarchie de performance chargée: "
                f"{len(set(entry['orientation'] for entry in table_entries if entry['orientation']))} orientation(s), "
                f"{len(table_entries)} ligne(s) de tableau"
            )
            
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


# ============================================================================
# GESTIONNAIRE DE DONNÉES FACTICES - DONNÉES DE CHARGEMENT
# ============================================================================

class RAPFakeDataLoader(RAPBaseGenerator):
    """
    Gestionnaire de données factices pour le chargement.
    
    Cette classe regroupe toutes les données factices utilisées en mode brouillon
    lorsque la base de données est vide ou que les données ne sont pas disponibles.
    Cela permet d'avoir toutes les données factices en un seul endroit pour faciliter
    la maintenance et la modification.
    
    Responsabilités :
    - Fournir des données factices pour les investissements
    - Fournir des données factices pour les activités majeures
    - Fournir des données factices pour les indicateurs de performance
    - Fournir des données factices pour les effectifs
    - Fournir des données factices pour l'introduction
    """
    
    @staticmethod
    def get_fake_investissements(annee: int) -> list[dict[str, Any]]:
        """
        Retourne les données factices pour les investissements.
        
        Args:
            annee: Année courante pour calculer les dates dynamiquement
        
        Returns:
            Liste de dictionnaires contenant les projets d'investissement factices
        """
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
                "_is_fake": True,
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
                "_is_fake": True,
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
                "_is_fake": True,
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
            
            # Stocker le taux d'exécution
            projet["_taux_execution"] = taux_exec
        
        return projets_factices
    
    @staticmethod
    def get_fake_activites_majeures() -> list[dict[str, Any]]:
        """
        Retourne les données factices pour les activités majeures.
        
        Returns:
            Liste de dictionnaires contenant les activités majeures factices
        """
        return [
            {"libelle": "Renforcement des capacités institutionnelles", "taux_execution": 95.5, "_is_fake": True},
            {"libelle": "Amélioration de la gestion du patrimoine immobilier", "taux_execution": 92.3, "_is_fake": True},
            {"libelle": "Modernisation des systèmes d'information", "taux_execution": 88.7, "_is_fake": True},
            {"libelle": "Optimisation de la gestion des ressources humaines", "taux_execution": 85.2, "_is_fake": True},
        ]
    
    @staticmethod
    def get_fake_indicateurs_performance(titre: str, annee: int) -> list[dict[str, Any]]:
        """
        Retourne les données factices pour les indicateurs de performance.
        
        Args:
            titre: Titre du programme (utilisé dans les descriptions)
            annee: Année courante pour calculer les années dynamiquement
        
        Returns:
            Liste de dictionnaires contenant les indicateurs de performance factices
        """
        annee_n_3 = annee - 3
        annee_n_2 = annee - 2
        annee_n_1 = annee - 1
        annee_n = annee
        
        return [
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
    
    @staticmethod
    def get_fake_effectifs(annee: int) -> list[dict[str, Any]]:
        """
        Retourne les données factices pour les effectifs.
        
        Args:
            annee: Année courante pour calculer l'année précédente
        
        Returns:
            Liste de dictionnaires contenant les effectifs factices par catégorie
        """
        annee_precedente = annee - 1
        return [
            {"categorie": "Catégorie A", f"effectif_{annee_precedente}": 25, "besoins_exprimes": 5, "previsions": 5, "besoins_satisfaits": 4, "sorties": 2, "_is_fake": True},
            {"categorie": "Catégorie B", f"effectif_{annee_precedente}": 45, "besoins_exprimes": 8, "previsions": 8, "besoins_satisfaits": 7, "sorties": 3, "_is_fake": True},
            {"categorie": "Catégorie C", f"effectif_{annee_precedente}": 30, "besoins_exprimes": 6, "previsions": 6, "besoins_satisfaits": 5, "sorties": 2, "_is_fake": True},
            {"categorie": "Catégorie D", f"effectif_{annee_precedente}": 15, "besoins_exprimes": 3, "previsions": 3, "besoins_satisfaits": 2, "sorties": 1, "_is_fake": True},
            {"categorie": "Non Fonctionnaires", f"effectif_{annee_precedente}": 10, "besoins_exprimes": 2, "previsions": 2, "besoins_satisfaits": 2, "sorties": 0, "_is_fake": True},
        ]
    
    @staticmethod
    def get_fake_introduction_data() -> dict[str, Any]:
        """
        Retourne les données factices pour l'introduction.
        
        Returns:
            Dictionnaire contenant les données factices pour l'introduction
        """
        return {
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


# ============================================================================
# GESTIONNAIRE DE LAYOUT - ÉLÉMENTS DE MISE EN PAGE
# ============================================================================

class RAPLayoutDrawer(RAPBaseGenerator):
    """
    Gestionnaire de layout pour le rapport.
    
    Responsabilités :
    - Dessin de la page de couverture complète
    - Dessin des éléments de fond (background shapes)
    - Dessin des headers et footers
    - Gestion du positionnement des éléments décoratifs
    
    Cette classe centralise toute la logique de mise en page visuelle
    pour garantir la cohérence du design dans tout le rapport.
    """
    
    @classmethod
    def draw_cover_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine la page de couverture complète du rapport.
        
        Cette méthode orchestre le dessin de tous les éléments de la couverture :
        1. Les formes de fond (background shapes)
        2. L'en-tête (header) avec République, logo, section, ministère
        3. Le bloc central avec le titre du rapport
        4. Le footer avec la date
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        
        Note:
            Cette méthode est un wrapper qui appelle les autres méthodes
            de layout dans le bon ordre.
        """
        # Dessiner les éléments dans l'ordre
        cls.draw_background_shapes(pdf, width, height)
        cls.draw_header(pdf, width, height)
        cls.draw_cover_block(pdf, width, height)
        cls.draw_footer(pdf, width, height)
    
    @classmethod
    def draw_background_shapes(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine les éléments décoratifs de fond (triangles, bandes, lignes).
        
        Cette méthode dessine les formes géométriques qui servent de décoration
        en arrière-plan du rapport :
        - Triangle vert en haut à droite
        - Bande décoratives parallèles à l'hypoténuse du triangle
        - Triangle orange en bas à gauche
        - Bandes décoratives pour le triangle bas-gauche
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        
        Note:
            Cette méthode contient beaucoup de géométrie complexe pour les bandes.
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 6022 - _draw_background_shapes()
        """
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
        start_x, start_y = width, height - 140
        end_x, end_y = width - 220, height

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
            cx0, cy0 = ax + dirx * a0, ax*0 + ay + diry * a0
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
            if round_end: pdf.circle(x1, y1, r, stroke=0, fill=1)
            pdf.restoreState()

        # ---------- BANDES ----------
        pdf.saveState()

        thickness = 8                   # épaisseur visuelle des bandes
        gap = -15                       # "jour" voulu entre l'hypoténuse et la 1ère bande
        band1_offset = gap + thickness/2
        band2_offset = band1_offset + 18
        offset = -10

        # Bande 1 : deux segments, arrondis contrôlés
        draw_band_slide(s_px=0.00*L, length_px=0.30*L, offset_px=offset,
                thickness=thickness, round_start=False, round_end=True,
                extend_start_px=20, extend_end_px=0,
                color=cls.LIGHT_GREEN, reverse=False, clamp=False)

        draw_band_slide(s_px=0.00*L, length_px=0.30*L, offset_px=offset,
                thickness=thickness, round_start=False, round_end=True,
                extend_start_px=40, extend_end_px=0,
                color=cls.LIGHT_GREEN, reverse=True, clamp=False)

        draw_band_slide(s_px=0.00*L, length_px=0.30*L, offset_px=offset+20,
                thickness=thickness+10, round_start=False, round_end=True,
                extend_start_px=40, extend_end_px=30,
                color=cls.SECONDARY_GREEN, reverse=False, clamp=False)

        draw_band_center(c_px=0.50*L, length_px=0.50*L, offset_px=offset-10,
                thickness=thickness, round_start=True, round_end=True,
                extend_start_px=40, extend_end_px=30,
                color=cls.SECONDARY_GREEN, reverse=False, clamp=False)

        pdf.restoreState()

        # ---------- TRIANGLE BAS GAUCHE ----------

        def draw_band_center_bl(c_px, length_px, offset_px, thickness,
                        round_start=True, round_end=True,
                        extend_start_px=0, extend_end_px=0,
                        color=None, reverse=False, clamp=False):
            """
            Helper pour dessiner une bande centrée sur l'hypoténuse du triangle bas-gauche.
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
        start2_x, start2_y = 0, 120
        end2_x, end2_y = 220, 0

        dx2, dy2 = end2_x - start2_x, end2_y - start2_y
        L2 = (dx2*dx2 + dy2*dy2) ** 0.5
        ux2, uy2 = dx2 / L2, dy2 / L2
        # Normale qui pointe à l'intérieur du triangle bas-gauche
        nx2, ny2 = (uy2, -ux2)

        pdf.saveState()

        def draw_band_slide_bl(s_px, length_px, offset_px, thickness,
                            round_start=True, round_end=True,
                            extend_start_px=0, extend_end_px=0,
                            color=None, reverse=False, clamp=False):
            """
            Bande 'capsule' parallèle à l'hypoténuse du triangle bas-gauche.
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
        thickness2 = 8
        gap2 = -15
        band1_offset2 = gap2 + thickness2/2
        band2_offset2 = band1_offset2 + 18
        offset2 = -10

        # Bandes pour le triangle bas-gauche
        draw_band_slide_bl(
            s_px=0.00 * L2,
            length_px=0.30 * L2,
            offset_px=offset2,
            thickness=thickness2,
            round_start=True, round_end=True,
            extend_start_px=20, extend_end_px=4,
            color=cls.PRIMARY_ORANGE,
            reverse=False, clamp=False
        )

        draw_band_slide_bl(
            s_px=0.00 * L2,
            length_px=0.30 * L2,
            offset_px=offset2,
            thickness=thickness2,
            round_start=False, round_end=True,
            extend_start_px=40, extend_end_px=0,
            color=cls.PRIMARY_ORANGE,
            reverse=True, clamp=False
        )

        draw_band_slide_bl(
            s_px=0.00 * L2,
            length_px=2 * L2,
            offset_px=offset2+20,
            thickness=thickness2+13,
            round_start=False, round_end=True,
            extend_start_px=0, extend_end_px=0,
            color=cls.LIGHT_2_ORANGE,
            reverse=False, clamp=False
        )

        draw_band_slide_bl(
            s_px=0.00 * L2,
            length_px=0.30 * L2,
            offset_px=offset2+20,
            thickness=thickness2+13,
            round_start=False, round_end=True,
            extend_start_px=40, extend_end_px=30,
            color=cls.LIGHT_ORANGE,
            reverse=False, clamp=False
        )

        draw_band_center_bl(
            c_px=0.5 * L2,
            length_px=0.70 * L2,
            offset_px=offset2-10,
            thickness=thickness2,
            round_start=True, round_end=True,
            extend_start_px=6, extend_end_px=6,
            color=cls.LIGHT_ORANGE,
            reverse=False, clamp=False
        )

        pdf.restoreState()
    
    @classmethod
    def draw_header(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine l'en-tête avec le titre République, le logo, la section et le ministère.
        
        Cette méthode dessine :
        - Le titre "REPUBLIQUE DE COTE D'IVOIRE" en haut
        - L'emblème/logo au centre
        - La section (ex: "SECTION 376 :") entre deux lignes pointillées
        - Le nom du ministère en dessous (peut être sur plusieurs lignes)
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        
        Note:
            Cette méthode stocke la position de la ligne pointillée du bas dans
            cls._dotted_line_bottom_y pour permettre le positionnement correct
            du bloc central (cover_block).
        """
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
                from reportlab.lib.units import cm
                from io import BytesIO
                from reportlab.lib.utils import ImageReader
                from textwrap import wrap
                
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
        from textwrap import wrap
        from reportlab.lib.units import cm
        
        # D'abord, calculer la hauteur totale du contenu pour le centrer correctement
        section = cls.data.get("section", "SECTION 376")
        ministere = cls.data.get("ministere", "")
        
        # Déterminer la source de chaque donnée pour le styling
        _, section_source = RAPStylingManager._determine_data_source_for_canvas("section", section)
        _, ministere_source = RAPStylingManager._determine_data_source_for_canvas("ministere", ministere)
        
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
        section_color = RAPStylingManager._get_color_for_source(section_source)
        pdf.saveState()
        pdf.setFillColor(section_color)
        pdf.drawCentredString(center_x, content_current_y, section + " :")
        pdf.restoreState()
        content_current_y -= 20  # Espace après la section

        # ---------- MINISTÈRE ----------
        if ministere:
            # Toutes les données sont DB, utiliser l'italique
            pdf.setFont("Helvetica-BoldOblique", 11)
            # Utiliser la source déterminée pour la couleur (peut être user > db > default)
            ministere_color = RAPStylingManager._get_color_for_source(ministere_source)
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
        
        # Stocker la position de la ligne pointillée pour l'utiliser dans draw_cover_block
        cls._dotted_line_bottom_y = bottom_line_y
        
        # Mettre à jour current_y pour la suite
        current_y = bottom_line_y

        pdf.restoreState()
    
    @classmethod
    def draw_cover_block(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine le bloc central avec le titre du rapport dans une boîte orange.
        
        Cette méthode dessine :
        - Une grande boîte orange au centre de la page
        - Le titre du rapport à l'intérieur de la boîte
        - L'année du rapport en dessous du titre
        
        Le positionnement du bloc est calculé en fonction de la ligne pointillée
        dessinée par draw_header() pour éviter les chevauchements.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        
        Note:
            Utilise cls._dotted_line_bottom_y pour le positionnement.
            Le titre et l'année sont formatés selon leur source (DB = rouge).
        """
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
        if hasattr(cls, '_dotted_line_bottom_y') and cls._dotted_line_bottom_y is not None:
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
        _, titre_rapport_source = RAPStylingManager._determine_data_source_for_canvas("titre_rapport", titre_rapport)
        _, titre_annee_source = RAPStylingManager._determine_data_source_for_canvas("titre_annee", titre_annee)
        _, annee_source = RAPStylingManager._determine_data_source_for_canvas("annee", annee)
        
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
        titre_color = RAPStylingManager._get_color_for_source("db")
        
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
                year_color = RAPStylingManager._get_color_for_source(year_source)
                
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
    def draw_footer(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine le bloc date en bas à droite de la page.
        
        Cette méthode dessine :
        - Une petite boîte orange avec coins arrondis
        - La date de publication à l'intérieur (générée dynamiquement)
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        
        Note:
            La date est générée dynamiquement depuis la date actuelle.
            Elle est formatée comme une donnée DB (rouge).
        """
        pdf.saveState()

        # ---------- BOÎTE DATE EN BAS À DROITE ----------
        # Générer toujours la date dynamiquement (toutes les données sont DB)
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
        date_color = RAPStylingManager._get_color_for_source(date_source)
        pdf.setFillColor(date_color)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(
            box_x + box_width / 2,
            box_y + box_height / 2 - 4,
            date_publication
        )

        pdf.restoreState()
    
    @classmethod
    def draw_page_footer(
        cls,
        pdf: canvas.Canvas,
        page_number: int,
        width: float,
        footer_margin: float,
        footer_height: float,
        right_margin: float
    ) -> None:
        """
        Dessine le footer avec le numéro de page (design carte/page avec coin relevé).
        
        Cette méthode dessine un footer élégant avec :
        - Une ombre portée
        - Une carte blanche principale avec coin relevé (effet 3D)
        - Le numéro de page centré dans la carte
        - Une ligne de séparation
        
        Args:
            pdf: Le canvas PDF
            page_number: Le numéro de page à afficher
            width: La largeur de la page
            footer_margin: La marge du footer depuis le bas
            footer_height: La hauteur du footer
            right_margin: La marge droite de la page
        
        Note:
            Ce footer est utilisé sur toutes les pages du rapport (sauf la couverture).
            Le design avec coin relevé donne un aspect professionnel au document.
        """
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
    
    @staticmethod
    def _resolve_asset_path(logo_path: str) -> Path | None:
        """
        Résout le chemin d'un asset (logo, image) vers un chemin absolu valide.
        
        Cette méthode cherche le fichier dans plusieurs emplacements possibles :
        - Chemin absolu direct
        - Chemin relatif depuis le répertoire de base de l'application
        - Répertoires d'assets standards
        
        Args:
            logo_path: Le chemin du logo (peut être relatif ou absolu)
        
        Returns:
            Path absolu vers le fichier si trouvé, None sinon
        
        Note:
            Cette méthode gère également les fichiers WEBP qui nécessitent
            une conversion spéciale avec PIL.
        """
        raw_path = logo_path  # Utiliser logo_path comme raw_path pour compatibilité
        
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


# ============================================================================
# GESTIONNAIRE DE CONTENU - CONTENU PRINCIPAL DU RAPPORT
# ============================================================================

class RAPContentDrawer(RAPBaseGenerator):
    """
    Gestionnaire de contenu principal pour le rapport.
    
    Responsabilités :
    - Dessin de la table des matières (sommaire)
    - Dessin des listes (tableaux, graphiques, sigles)
    - Dessin de l'introduction générale
    - Dessin de la Partie I : Le Ministère
    - Dessin de la conclusion générale
    
    Cette classe centralise toute la logique de génération du contenu
    principal du rapport (hors sections par programme).
    """
    
    @classmethod
    def draw_table_of_contents(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        pdf_reader_complet: PdfReader | None = None,
        nb_pages_sommaire: int = 0
    ) -> int:
        """
        Dessine la page du sommaire (table of contents) avec support multi-pages.
        
        Cette méthode génère la table des matières complète en recherchant les titres
        dans le PDF généré (approche "Word-like") ou en utilisant les pages enregistrées.
        
        Structure fixe du sommaire :
        - Liste des tableaux
        - Liste des graphiques
        - Sigles et abréviations
        - Introduction générale
        - PARTIE I : LE MINISTÈRE
          - I.1. Présentation générale
          - I.2. Performance générale
          - I.3. Financement global
        - PARTIE II : LE PROGRAMME 1
          - (sections du programme)
        - PARTIE III : LE PROGRAMME 2
          - (sections du programme)
        - CONCLUSION GÉNÉRALE
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            pdf_reader_complet: PdfReader du PDF complet pour rechercher les pages (optionnel)
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Le numéro de la page suivante après le sommaire
        
        Note:
            La page du sommaire n'a pas de numéro de page dans le footer.
            Les numéros de page des sections sont déterminés dynamiquement.
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        
        logger.info("📋 Dessin de la table des matières...")
        
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
        toc_items = cls._build_toc_items_from_pdf_or_positions(
            pdf_reader_complet=pdf_reader_complet, 
            nb_pages_sommaire=nb_pages_sommaire
        )
        
        # Récupérer les programmes pour le log
        programmes = cls.data.get("programmes", [])
        
        # Log pour déboguer
        logger.info(f"📋 Sommaire: {len(toc_items)} éléments à afficher (programmes: {len(programmes)})")
        if len(toc_items) > 0:
            logger.info(f"📋 Premiers éléments: {[item['text'][:40] for item in toc_items[:5]]}")
        
        # Fonction helper pour dessiner une ligne du sommaire
        def draw_toc_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                raise ValueError("current_y_pos doit être fourni")
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
            
            # Tronquer le texte si nécessaire
            text_to_draw = text
            text_width = pdf.stringWidth(text, font, font_size)
            if text_width > max_text_width:
                # Tronquer le texte et ajouter "..."
                text_to_draw = text
                ellipsis_width = pdf.stringWidth("...", font, font_size)
                available_width_for_text = max_text_width - ellipsis_width
                
                # Réduire progressivement le texte jusqu'à ce qu'il rentre
                while pdf.stringWidth(text_to_draw, font, font_size) > available_width_for_text and len(text_to_draw) > 0:
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
        
        # Dessiner le sommaire avec pagination automatique
        page_num = 2  # Commence à la page 2 (après la couverture)
        first_page = True
        
        while toc_items or first_page:
            # Le canvas crée automatiquement une première page par défaut
            # Pour la première page, dessiner directement dessus
            # Pour les pages suivantes, créer une nouvelle page avec showPage()
            if not first_page:
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Sommaire (suite)")
            else:
                logger.info(f"📄 Page {page_num}: Sommaire")
            
            pdf.saveState()
            
            # Titre "SOMMAIRE" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(RAPBaseGenerator.DARK_TEXT)
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
            
            # Pas de footer (numéro de page) sur la page du sommaire
            
            pdf.restoreState()
            
            page_num += 1
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and toc_items:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        return page_num
    
    @classmethod
    def draw_liste_tableaux(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la page de la liste des tableaux avec support multi-pages.
        
        Cette méthode affiche tous les tableaux du rapport avec leurs numéros
        et leurs numéros de page. Les titres sont extraits dynamiquement du PDF.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après la liste des tableaux
        
        Note:
            Les tableaux sont numérotés de manière continue dans tout le rapport.
            Les titres sont extraits depuis le PDF généré pour garantir l'exactitude.
        """
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        line_spacing = 0.55 * cm

        # Couleur bleue pour tous les éléments
        blue_color = colors.HexColor("#0066CC")
        
        # Construire la liste des tableaux
        tableaux_items = []
        
        # Récupérer les tableaux depuis les données
        tableaux = cls.data.get("tableaux", [])
        
        # Vérifier si on a des pages trouvées dans le PDF (après génération)
        tableaux_pages_found = getattr(cls, "_tableaux_pages_found", {})
        
        # Helper pour extraire la page d'un tuple (page, titre) ou retourner directement la valeur
        def extract_page(value):
            if isinstance(value, tuple):
                return value[0]
            return value
        
        # Helper pour extraire le titre d'un tuple (page, titre) ou retourner None
        def extract_title(value):
            if isinstance(value, tuple) and len(value) >= 2:
                return value[1]
            return None
        
        # Si aucun tableau n'est disponible, créer des tableaux factices pour la liste
        if not tableaux:
            programmes = cls.data.get("programmes", [])
            if not programmes:
                programmes = [
                    {"numero": 1, "titre": "ADMINISTRATION GÉNÉRALE"},
                    {"numero": 2, "titre": "Portefeuille de l'État"}
                ]
            
            # Tableaux fixes du ministère
            tableaux = []
            for num in [2, 3, 4]:
                found_data = tableaux_pages_found.get(num)
                page = extract_page(found_data) if found_data else (8 if num == 2 else 9 if num == 3 else 10)
                titre = extract_title(found_data) if found_data else (
                    "Composantes des cadres de performance du ministère" if num == 2 else
                    "Réalisations du cadre de performance du ministère" if num == 3 else
                    "Tableau présentant l'exécution du budget du ministère"
                )
                tableaux.append({"numero": num, "titre": titre, "page": page})
            
            tableau_numero = 5
            
            for idx, programme in enumerate(programmes):
                numero = programme.get("numero", idx + 1)
                titre_prog = programme.get("titre", "")
                
                for tab_idx in range(4):
                    found_data = tableaux_pages_found.get(tableau_numero)
                    page = extract_page(found_data) if found_data else (16 + (idx * 17) + (tab_idx * 2))
                    
                    titre = extract_title(found_data)
                    if not titre:
                        default_titres = [
                            f"Exécution financière par action du programme {numero} « {titre_prog.upper()} »",
                            f"Suivi des investissements du Programme {numero} « {titre_prog.upper()} »",
                            f"Exécution des prévisions d'effectifs du programme {numero} « {titre_prog.upper()} »",
                            f"Évolution des indicateurs du programme {numero} « {titre_prog.upper()} »"
                        ]
                        titre = default_titres[tab_idx] if tab_idx < len(default_titres) else f"Tableau {tableau_numero}"
                    
                    tableaux.append({
                        "numero": tableau_numero,
                        "titre": titre,
                        "page": page
                    })
                    tableau_numero += 1
            
            logger.info(f"📋 Aucun tableau trouvé, utilisation de {len(tableaux)} tableaux factices pour la liste")
        
        for tableau in tableaux:
            numero = tableau.get("numero", 1)
            titre = tableau.get("titre", "")
            page = tableau.get("page", 0)
            
            tableau_text = f"Tableau {numero}: {titre}"
            tableaux_items.append({"text": tableau_text, "page": page, "level": 0, "bold": False})
        
        # Fonction helper pour dessiner une ligne
        def draw_tableau_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                current_y_pos = current_y
            line_spacing_val = line_spacing
            
            x_text = left_margin + (level * 1 * cm)
            x_page = width - right_margin - 1 * cm
            page_num_width = 2 * cm
            max_text_width = x_page - x_text - page_num_width
            
            pdf.saveState()
            
            pdf.setFillColor(blue_color)
            pdf.setStrokeColor(blue_color)
            
            font = "Helvetica-Bold" if bold else "Helvetica"
            font_size = 11 if level == 0 else 10 if level == 1 else 9
            
            pdf.setFont(font, font_size)
            
            text_to_draw = text
            text_width = pdf.stringWidth(text, font, font_size)
            if text_width > max_text_width:
                text_to_draw = text
                ellipsis_width = pdf.stringWidth("...", font, font_size)
                available_width = max_text_width - ellipsis_width
                
                while pdf.stringWidth(text_to_draw, font, font_size) > available_width and len(text_to_draw) > 0:
                    text_to_draw = text_to_draw[:-1]
                
                text_to_draw = text_to_draw + "..."
            
            pdf.drawString(x_text, current_y_pos, text_to_draw)
            
            actual_text_width = pdf.stringWidth(text_to_draw, font, font_size)
            pdf.setLineWidth(1)
            pdf.line(x_text, current_y_pos - 2, x_text + actual_text_width, current_y_pos - 2)
            
            page_str = str(page) if page else "..."
            pdf.drawRightString(x_page, current_y_pos, page_str)
            
            pdf.restoreState()
            
            return current_y_pos - line_spacing_val

        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            RAPLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_number,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin
            )

        # Dessiner la liste avec pagination automatique
        page_num = start_page
        first_page = True
        
        logger.info(f"🔍 DIAGNOSTIC _draw_liste_tableaux - Début avec start_page={start_page}, {len(tableaux_items)} tableaux à afficher")
        logger.info(f"🔢 NUMÉROTATION - _draw_liste_tableaux DÉBUT: start_page={start_page}")
        
        while tableaux_items or first_page:
            if not first_page:
                logger.info(f"🔢 NUMÉROTATION - showPage() appelé, nouvelle page {page_num}")
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Liste des tableaux (suite)")
            else:
                logger.info(f"🔢 NUMÉROTATION - Première page (pas de showPage), page_num={page_num}")
                logger.info(f"📄 Page {page_num}: Liste des tableaux")
            
            pdf.saveState()
            
            # Titre "LISTE DES TABLEAUX" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(cls.DARK_TEXT)
                pdf.setFont("Helvetica-Bold", 18)
                title_y = start_y
                pdf.drawString(left_margin, title_y, "LISTE DES TABLEAUX")
                # Enregistrer la page pour le sommaire
                RAPPageManager.register_page_position("liste_tableaux", page_num)
                current_y = title_y - 2 * cm
            else:
                current_y = start_y
            
            # Dessiner les éléments jusqu'à ce que la page soit pleine
            items_to_remove = []
            for item in tableaux_items:
                spacing_needed = line_spacing
                
                if current_y - spacing_needed < content_bottom:
                    break
                
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
            logger.info(f"🔢 NUMÉROTATION - Footer dessiné avec page_num={page_num}")
            draw_footer(page_num)
            
            pdf.restoreState()
            
            # Toujours incrémenter pour préparer la page suivante
            logger.info(f"🔢 NUMÉROTATION - page_num avant incrément: {page_num}")
            page_num += 1
            logger.info(f"🔢 NUMÉROTATION - page_num après incrément: {page_num}")
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and tableaux_items:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        logger.info(f"🔢 NUMÉROTATION - _draw_liste_tableaux FIN: retourne page_num={page_num} (page suivante)")
        return page_num
    
    @classmethod
    def draw_liste_graphiques(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la page de la liste des graphiques avec support multi-pages.
        
        Cette méthode affiche tous les graphiques du rapport avec leurs numéros
        et leurs numéros de page. Les titres sont extraits dynamiquement du PDF.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après la liste des graphiques
        
        Note:
            Les graphiques sont numérotés de manière continue dans tout le rapport.
            Les titres sont extraits depuis le PDF généré pour garantir l'exactitude.
        """
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        line_spacing = 0.55 * cm

        # Couleur bleue pour tous les éléments
        blue_color = colors.HexColor("#0066CC")
        
        # Construire la liste des graphiques
        graphiques_items = []
        
        # Récupérer les graphiques depuis les données
        graphiques = cls.data.get("graphiques", [])
        
        # Vérifier si on a des pages trouvées dans le PDF (après génération)
        graphiques_pages_found = getattr(cls, "_graphiques_pages_found", {})
        
        # Helper pour extraire la page d'un tuple (page, titre) ou retourner directement la valeur
        def extract_page(value):
            if isinstance(value, tuple):
                return value[0]
            return value
        
        # Helper pour extraire le titre d'un tuple (page, titre) ou retourner None
        def extract_title(value):
            if isinstance(value, tuple) and len(value) >= 2:
                return value[1]
            return None
        
        # Si aucun graphique n'est disponible, créer des graphiques factices pour la liste
        if not graphiques:
            programmes = cls.data.get("programmes", [])
            if not programmes:
                programmes = [
                    {"numero": 1, "titre": "ADMINISTRATION GÉNÉRALE"},
                    {"numero": 2, "titre": "Portefeuille de l'État"}
                ]
            
            # Figure 1: Graphique fixe du ministère
            found_data_1 = graphiques_pages_found.get(1)
            page_1 = extract_page(found_data_1) if found_data_1 else 10
            titre_1 = extract_title(found_data_1) if found_data_1 else "Répartition du budget actuel du Ministère par natures de dépenses"
            graphiques = [
                {"numero": 1, "titre": titre_1, "page": page_1}
            ]
            
            # Compteur pour les numéros de figures (commence à 2 car on a déjà la Figure 1)
            figure_numero = 2
            
            for idx, programme in enumerate(programmes):
                numero = programme.get("numero", idx + 1)
                titre_prog = programme.get("titre", "")
                
                # Créer les 3 graphiques par programme
                for fig_idx in range(3):
                    found_data = graphiques_pages_found.get(figure_numero)
                    page = extract_page(found_data) if found_data else (16 + (idx * 17) + (fig_idx * 3))
                    
                    # Utiliser le titre extrait si disponible, sinon utiliser un titre par défaut
                    titre = extract_title(found_data)
                    if not titre:
                        default_titres = [
                            f"Répartition du budget actuel du Programme {numero} « {titre_prog.upper()} » par nature de dépenses",
                            f"Evolution des taux d'exécution par action du Programme {numero} « {titre_prog.upper()} »",
                            f"Evolution des effectifs du Programme {numero} « {titre_prog.upper()} » par catégorie"
                        ]
                        titre = default_titres[fig_idx] if fig_idx < len(default_titres) else f"Figure {figure_numero}"
                    
                    graphiques.append({
                        "numero": figure_numero,
                        "titre": titre,
                        "page": page
                    })
                    figure_numero += 1
            
            logger.info(f"📋 Aucun graphique trouvé, utilisation de {len(graphiques)} graphiques factices pour la liste")
        
        for graphique in graphiques:
            numero = graphique.get("numero", 1)
            titre = graphique.get("titre", "")
            page = graphique.get("page", 0)
            
            graphique_text = f"Figure {numero}: {titre}"
            graphiques_items.append({"text": graphique_text, "page": page, "level": 0, "bold": False})
        
        # Fonction helper pour dessiner une ligne
        def draw_graphique_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                current_y_pos = current_y
            line_spacing_val = line_spacing
            
            x_text = left_margin + (level * 1 * cm)
            x_page = width - right_margin - 1 * cm
            page_num_width = 2 * cm
            max_text_width = x_page - x_text - page_num_width
            
            pdf.saveState()
            
            pdf.setFillColor(blue_color)
            pdf.setStrokeColor(blue_color)
            
            font = "Helvetica-Bold" if bold else "Helvetica"
            font_size = 11 if level == 0 else 10 if level == 1 else 9
            
            pdf.setFont(font, font_size)
            
            text_to_draw = text
            text_width = pdf.stringWidth(text, font, font_size)
            if text_width > max_text_width:
                text_to_draw = text
                ellipsis_width = pdf.stringWidth("...", font, font_size)
                available_width = max_text_width - ellipsis_width
                
                while pdf.stringWidth(text_to_draw, font, font_size) > available_width and len(text_to_draw) > 0:
                    text_to_draw = text_to_draw[:-1]
                
                text_to_draw = text_to_draw + "..."
            
            pdf.drawString(x_text, current_y_pos, text_to_draw)
            
            actual_text_width = pdf.stringWidth(text_to_draw, font, font_size)
            pdf.setLineWidth(1)
            pdf.line(x_text, current_y_pos - 2, x_text + actual_text_width, current_y_pos - 2)
            
            page_str = str(page) if page else "..."
            pdf.drawRightString(x_page, current_y_pos, page_str)
            
            pdf.restoreState()
            
            return current_y_pos - line_spacing_val

        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            RAPLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_number,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin
            )

        # Dessiner la liste avec pagination automatique
        logger.info(f"🔢 NUMÉROTATION - _draw_liste_graphiques DÉBUT: start_page={start_page}")
        page_num = start_page
        first_page = True
        
        while graphiques_items or first_page:
            if not first_page:
                logger.info(f"🔢 NUMÉROTATION - showPage() appelé, nouvelle page {page_num}")
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Liste des graphiques (suite)")
            else:
                logger.info(f"🔢 NUMÉROTATION - Première page graphiques (déjà créée dans generate_pdf), page_num={page_num}")
                logger.info(f"📄 Page {page_num}: Liste des graphiques")
            
            pdf.saveState()
            
            # Titre "LISTE DES GRAPHIQUES" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(cls.DARK_TEXT)
                pdf.setFont("Helvetica-Bold", 18)
                title_y = start_y
                pdf.drawString(left_margin, title_y, "LISTE DES GRAPHIQUES")
                # Enregistrer la page pour le sommaire
                RAPPageManager.register_page_position("liste_graphiques", page_num)
                current_y = title_y - 2 * cm
            else:
                current_y = start_y
            
            # Dessiner les éléments jusqu'à ce que la page soit pleine
            items_to_remove = []
            for item in graphiques_items:
                spacing_needed = line_spacing
                
                if current_y - spacing_needed < content_bottom:
                    break
                
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
            logger.info(f"🔢 NUMÉROTATION - Footer dessiné avec page_num={page_num}")
            draw_footer(page_num)
            
            pdf.restoreState()
            
            # Toujours incrémenter pour préparer la page suivante
            logger.info(f"🔢 NUMÉROTATION - page_num avant incrément: {page_num}")
            page_num += 1
            logger.info(f"🔢 NUMÉROTATION - page_num après incrément: {page_num}")
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and graphiques_items:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        logger.info(f"🔢 NUMÉROTATION - _draw_liste_graphiques FIN: retourne page_num={page_num} (page suivante)")
        return page_num
    
    @classmethod
    def draw_liste_sigles_abreviations(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la page de la liste des sigles et abréviations.
        
        Cette méthode affiche tous les sigles et abréviations utilisés dans le rapport.
        La liste est statique (prédéfinie) pour ce type de rapport.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après la liste des sigles
        
        Note:
            La liste des sigles est statique et ne provient pas de la base de données.
        """
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        line_spacing = 0.6 * cm

        # Couleur bleue pour tous les éléments
        blue_color = colors.HexColor("#0066CC")
        
        # Récupérer les sigles depuis les données
        sigles = cls.data.get("sigles", [])
        
        # Si aucun sigle n'est disponible, créer une liste statique de sigles factices
        if not sigles:
            sigles = [
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
            ]
            logger.info(f"📋 Aucun sigle trouvé, utilisation de {len(sigles)} sigles statiques pour la liste")
        
        # Ajouter automatiquement le sigle du ministère généré dynamiquement
        sigle_ministere = RAPStylingManager.get_sigle_ministere()
        ministere = cls.data.get("ministere", "")
        
        # Vérifier si le sigle du ministère n'est pas déjà dans la liste
        sigle_exists = any(entry.get("sigle") == sigle_ministere for entry in sigles)
        
        if not sigle_exists and ministere:
            sigle_ministere_entry = {
                "sigle": sigle_ministere,
                "definition": ministere
            }
            sigles.insert(0, sigle_ministere_entry)
        
        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_number: int):
            RAPLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_number,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin
            )

        # Fonction pour dessiner une entrée sigle/définition avec styling selon la source
        def draw_sigle_entry(sigle: str, definition: str, x: float, y: float, max_width: float, source: str = "default") -> float:
            """Dessine une entrée sigle/définition et retourne la nouvelle position Y."""
            pdf.saveState()
            
            # Déterminer la couleur selon la source
            sigle_color = RAPStylingManager._get_color_for_source(source)
            
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
        logger.info(f"🔢 NUMÉROTATION - _draw_liste_sigles_abreviations DÉBUT: start_page={start_page}")
        page_num = start_page
        first_page = True
        sigles_remaining = sigles.copy()
        
        while sigles_remaining or first_page:
            if not first_page:
                logger.info(f"🔢 NUMÉROTATION - showPage() appelé, nouvelle page {page_num}")
                pdf.showPage()
                logger.info(f"📄 Page {page_num}: Sigles et abréviations (suite)")
            else:
                logger.info(f"🔢 NUMÉROTATION - Première page sigles (déjà créée dans generate_pdf), page_num={page_num}")
                logger.info(f"📄 Page {page_num}: Sigles et abréviations")
            
            pdf.saveState()
            
            # Titre "SIGLES ET ABRÉVIATIONS" (seulement sur la première page)
            if first_page:
                pdf.setFillColor(cls.DARK_TEXT)
                pdf.setFont("Helvetica-Bold", 18)
                title_y = start_y
                pdf.drawString(left_margin, title_y, "SIGLES ET ABRÉVIATIONS")
                RAPPageManager.register_page_position("sigles_abreviations", page_num)
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
                
                # Toutes les données sont DB
                sigle_source = "db"
                
                # Vérifier si on a assez d'espace vertical pour une nouvelle ligne
                if current_y - line_spacing < content_bottom:
                    break
                
                # Dessiner l'entrée avec le styling selon la source
                current_y = draw_sigle_entry(sigle, definition, current_x, current_y, max_col_width, sigle_source)
                
                items_to_remove.append(sigle_entry)
            
            # Retirer les éléments déjà dessinés
            for item in items_to_remove:
                sigles_remaining.remove(item)
            
            # Dessiner le footer
            logger.info(f"🔢 NUMÉROTATION - Footer dessiné avec page_num={page_num}")
            draw_footer(page_num)
            
            pdf.restoreState()
            
            # Toujours incrémenter pour préparer la page suivante
            logger.info(f"🔢 NUMÉROTATION - page_num avant incrément: {page_num}")
            page_num += 1
            logger.info(f"🔢 NUMÉROTATION - page_num après incrément: {page_num}")
            first_page = False
            
            # Sécurité : éviter les boucles infinies
            if not items_to_remove and sigles_remaining:
                logger.warning("⚠️ Aucun élément n'a pu être dessiné, sortie de boucle")
                break
        
        logger.info(f"🔢 NUMÉROTATION - _draw_liste_sigles_abreviations FIN: retourne page_num={page_num} (page suivante)")
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
        from reportlab.platypus import Frame
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus.doctemplate import LayoutError
        
        logger.info(f"🔢 NUMÉROTATION - _render_multipage_story DÉBUT: page_num={page_num}, {len(story)} éléments dans story")
        first_page = True
        current_page = page_num

        while story:
            # La première page est déjà créée avant l'appel
            if not first_page:
                logger.info(f"🔢 NUMÉROTATION - showPage() dans _render_multipage_story, nouvelle page {current_page}")
                pdf.showPage()

            # Mettre à jour la variable de classe pour que les PageMarker puissent l'utiliser
            RAPBaseGenerator._current_rendering_page = current_page

            frame = Frame(
                frame_x,
                frame_y,
                frame_width,
                frame_height,
                showBoundary=0,  # passer à 1 pour déboguer
            )

            pdf.saveState()

            before = len(story)
            logger.info(f"🔢 NUMÉROTATION - Rendu page {current_page}: {before} éléments restants")
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
                logger.info(f"🔢 NUMÉROTATION - Footer pour page {current_page}")
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

            # Toujours incrémenter pour préparer la page suivante
            # On retourne la page suivante pour indiquer où commencer la prochaine section
            logger.info(f"🔢 NUMÉROTATION - page_num avant incrément: {current_page}")
            current_page += 1
            logger.info(f"🔢 NUMÉROTATION - page_num après incrément: {current_page}")
            first_page = False

        # Réinitialiser la variable de classe
        RAPBaseGenerator._current_rendering_page = None
        
        # Retourner la page suivante (pour indiquer où commencer la prochaine section)
        # Si la dernière page dessinée est N, on retourne N+1
        logger.info(f"🔢 NUMÉROTATION - _render_multipage_story FIN: retourne current_page={current_page} (page suivante après la dernière dessinée)")
        return current_page
    
    @classmethod
    def draw_introduction_generale(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la page d'introduction générale avec support multi-pages.
        
        Cette méthode génère l'introduction générale du rapport qui inclut :
        - Le contexte général
        - Les informations sur le ministre (nom, date de nomination, décret)
        - La mission du ministère
        - La structure organisationnelle
        - La structure du rapport
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après l'introduction
        
        Note:
            Les données proviennent de SystemSettings et RapData.
            Toutes les données sont formatées comme DB (rouge en mode brouillon).
            Les paragraphes sont justifiés et les puces sont gérées.
        """
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY
        from reportlab.platypus import Paragraph, Spacer
        from typing import Any
        
        logger.info(f"📝 Dessin de l'introduction générale (page {start_page})...")
        
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
            RAPLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_number,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin
            )

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
        intro_data = cls.data.get("introduction", {})
        logger.info(f"🔍 _draw_introduction_generale - intro_data récupéré: {list(intro_data.keys()) if intro_data else 'VIDE'}")
        logger.info(f"🔍 _draw_introduction_generale - cls.data contient 'introduction': {'introduction' in cls.data}")
        
        # Fonction helper pour générer des données factices selon le type
        def generate_fake_value(key: str, default_value: Any = None) -> Any:
            """Génère une valeur factice réaliste selon la clé."""
            if not RAPBaseGenerator.should_use_fake_data():
                return default_value
            
            # Générer des valeurs factices réalistes selon la clé
            fake_data_map = RAPFakeDataLoader.get_fake_introduction_data()
            
            if key in fake_data_map:
                return fake_data_map[key]
            
            # Valeurs par défaut selon le type
            if default_value == "NC" or default_value == "":
                return "Donnée factice"
            elif isinstance(default_value, (int, float)) and default_value == 0:
                return 15  # Valeur factice pour les nombres
            else:
                return default_value
        
        # Fonction helper pour récupérer une valeur principale
        def get_main_value(key: str, default_value: Any = None) -> tuple[Any, str]:
            """Récupère une valeur principale."""
            value = cls.data.get(key, default_value)
            
            # Si la valeur est la valeur par défaut (NC, 0, etc.), générer une valeur factice en mode brouillon
            if value == default_value and RAPBaseGenerator.should_use_fake_data():
                fake_value = generate_fake_value(key, default_value)
                return fake_value, "fake"
            
            return value, "db"
        
        # Fonction helper pour récupérer une valeur d'introduction
        def get_intro_value(key: str, default_value: Any = None) -> tuple[Any, str]:
            """Récupère une valeur d'introduction."""
            value = intro_data.get(key, default_value)
            
            # Si la valeur est la valeur par défaut (NC, 0, etc.), générer une valeur factice en mode brouillon
            if value == default_value and RAPBaseGenerator.should_use_fake_data():
                fake_value = generate_fake_value(key, default_value)
                return fake_value, "fake"
            
            return value, "db"
        
        # Récupérer toutes les valeurs avec leur source
        ministre_nom, ministre_nom_source = get_intro_value("ministre_nom", "NC")
        ministre_date, ministre_date_source = get_intro_value("ministre_date_nomination", "NC")
        decret_attr_num, decret_attr_num_source = get_intro_value("decret_attribution_numero", "NC")
        decret_attr_date, decret_attr_date_source = get_intro_value("decret_attribution_date", "NC")
        mission_ministere, mission_source = get_intro_value("mission_ministere", "NC")
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
        story.append(PageMarker("introduction_generale"))
        story.append(Paragraph("INTRODUCTION GÉNÉRALE", title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Formater chaque valeur selon sa source (DB en rouge, factice en violet italique)
        def format_by_source(value: Any, source: str) -> str:
            """Formate une valeur selon sa source."""
            # Retourner "NC" pour les valeurs vides
            if not value or value == "" or value == []:
                if source == "fake":
                    return RAPStylingManager.format_fake_data("NC")
                return RAPStylingManager.format_db_data("NC")
            # Si c'est un nombre 0, retourner "0" formaté
            if isinstance(value, (int, float)) and value == 0:
                if source == "fake":
                    return RAPStylingManager.format_fake_data("0")
                return RAPStylingManager.format_db_data("0")
            
            # Formater selon la source
            if source == "fake":
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
        # Récupérer le nom du ministère avec sa source
        ministere_value, ministere_source = get_main_value("ministere", "NC")
        formatted_ministere = format_by_source(ministere_value, ministere_source)
        
        formatted_ministre_nom = format_by_source(ministre_nom, ministre_nom_source)
        formatted_ministre_date = format_by_source(ministre_date, ministre_date_source)
        formatted_decret_attr_num = format_by_source(decret_attr_num, decret_attr_num_source)
        formatted_decret_attr_date = format_by_source(decret_attr_date, decret_attr_date_source)
        formatted_mission = format_by_source(mission_ministere, mission_source)
        
        sigle_ministere = RAPStylingManager.get_sigle_ministere()
        para1 = (
            f"Le {formatted_ministere} ({sigle_ministere}) est dirigé par {formatted_ministre_nom} depuis le {formatted_ministre_date}. "
            f"Sa mission est de {formatted_mission}. Cette mission "
            f"lui a été confiée conformément au décret {formatted_decret_attr_num} du {formatted_decret_attr_date} "
            f"portant attributions des membres du Gouvernement."
        )
        story.append(Paragraph(para1, body_style))
        
        # Paragraphe 2 : Structure organisationnelle
        formatted_structure_cabinet = format_by_source(structure_cabinet, structure_cabinet_source)
        structure_desc = formatted_structure_cabinet if structure_cabinet and structure_cabinet != "NC" else RAPStylingManager.format_db_data("NC")
        
        # Formater les nombres selon la source
        formatted_nb_directions = format_by_source(str(nb_directions), nb_directions_source) if nb_directions else RAPStylingManager.format_db_data("0")
        formatted_nb_services = format_by_source(str(nb_services), nb_services_source) if nb_services else RAPStylingManager.format_db_data("0")
        formatted_nb_dg = format_by_source(str(nb_dg), nb_dg_source) if nb_dg else RAPStylingManager.format_db_data("0")
        
        # Afficher "0" si vide
        directions_text = f"{formatted_nb_directions} Direction{'s' if nb_directions > 1 else ''} centrale{'s' if nb_directions > 1 else ''}" if nb_directions else RAPStylingManager.format_db_data("0 Direction centrale")
        services_text = f"{formatted_nb_services} Service{'s' if nb_services > 1 else ''}" if nb_services else RAPStylingManager.format_db_data("0 Service")
        dg_text = f"{formatted_nb_dg} Direction{'s' if nb_dg > 1 else ''} Générale{'s' if nb_dg > 1 else ''}" if nb_dg else RAPStylingManager.format_db_data("0 Direction Générale")
        
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
        
        # Paragraphe 3 : Contexte
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
        
        # Paragraphe 4 : Structure du rapport
        from datetime import datetime
        annee_value, annee_source = get_main_value("annee", datetime.now().year)
        formatted_annee_para4 = format_by_source(str(annee_value), annee_source)
        
        para4_intro = (
            f"Le présent rapport détaille les activités du {formatted_ministere} pour l'exercice {formatted_annee_para4} "
            f"et s'articule autour de deux grandes parties."
        )
        story.append(Paragraph(para4_intro, body_style))
        
        # Première partie avec puces
        story.append(Paragraph("La première partie permettra de :", body_style))
        for item in premiere_partie_items:
            formatted_item = format_by_source(item, premiere_partie_items_source)
            story.append(Paragraph(formatted_item, bullet_style, bulletText="•"))
        
        # Seconde partie avec puces
        story.append(Paragraph("La seconde partie abordera la performance de chaque programme à travers :", body_style))
        for item in seconde_partie_items:
            # Utiliser format_db_data pour l'année dans l'item
            annee_value, _ = get_main_value("annee", datetime.now().year)
            formatted_annee_in_item = RAPStylingManager.format_db_data(str(annee_value))
            formatted_item = item.format(annee=formatted_annee_in_item) if "{annee}" in item else item
            formatted_item_final = format_by_source(formatted_item, seconde_partie_items_source)
            story.append(Paragraph(formatted_item_final, bullet_style, bulletText="•"))
        
        logger.info(f"🔢 NUMÉROTATION - _draw_introduction_generale DÉBUT: start_page={start_page}")
        logger.info(f"📄 Page {start_page}: Introduction générale")
        
        # Rendre la story avec pagination automatique
        logger.info(f"🔢 NUMÉROTATION - AVANT _render_multipage_story pour introduction: start_page={start_page}")
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
        logger.info(f"🔢 NUMÉROTATION - APRÈS _render_multipage_story pour introduction: final_page={final_page}")
        logger.info(f"🔢 NUMÉROTATION - _draw_introduction_generale FIN: retourne final_page={final_page}")
        
        return final_page
    
    @classmethod
    def draw_partie_i_ministere(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la Partie I : Le Ministère avec support multi-pages.
        
        Cette méthode génère la première partie principale du rapport qui inclut :
        - I.1. Architecture programmatique du Ministère (avec tableau 1)
        - I.2. Performance générale du Ministère
          - II.1. Architecture du cadre de performance (avec tableau 2)
          - II.2. Bilan des données globales (avec tableau 3)
        - III. Financement global du Ministère (avec tableau 4 et figure 1)
          - III.1.1. Évolution du financement (avec tableau)
          - III.1.2. Suivi des investissements
          - III.2. Répartition par nature de dépenses (avec graphique)
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après la Partie I
        
        Note:
            Cette partie utilise SimpleDocTemplate pour gérer les tableaux longs.
            Les données proviennent de la base de données ou sont générées en mode brouillon.
        """
        logger.info(f"🔢 NUMÉROTATION - draw_partie_i_ministere DÉBUT: start_page={start_page}")
        
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
            RAPLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_number,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin
            )

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
                if mode == "brouillon" and RAPBaseGenerator.should_use_fake_data():
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
            if (mode == "brouillon" and RAPBaseGenerator.should_use_fake_data() and
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
        # Enregistrer la page AVANT le titre pour garantir que la page enregistrée est celle où le titre commence
        story.append(PageMarker("partie_i"))
        story.append(Paragraph("PARTIE I : LE MINISTÈRE", partie_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Section I. PRESENTATION GENERALE DU MINISTERE
        # Enregistrer la page AVANT le titre (après CondPageBreak s'il y en a un)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        # et le titre suivra sur la même page
        story.append(PageMarker("presentation_generale"))
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
        sigle_ministere = RAPStylingManager.get_sigle_ministere()
        
        # Déterminer si les données sont factices (vérifier le flag ou si les données sont vides)
        mode = cls.data.get("mode", "brouillon")
        is_fake_data = (
            partie_data.get('_is_architecture_fake', False) or  # Flag indiquant que les données sont factices
            (mode == "brouillon" and 
             RAPBaseGenerator.should_use_fake_data() and
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
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
        # Formater toutes les données selon leur source
        formatted_ministere = RAPStylingManager.format_db_data(ministere)  # Toujours DB (nom du ministère)
        formatted_sigle = RAPStylingManager.format_db_data(sigle_ministere)  # Toujours DB (sigle)
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
        
        # Tableau 1: Récapitulatif des actions et activités par programme
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
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_numero}: Récapitulatif des actions et activités par programme", subsection_title_style))
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
            RAPBaseGenerator.should_use_fake_data() and
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
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
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
        # Enregistrer la page AVANT le titre (après CondPageBreak)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        story.append(PageMarker("performance_generale"))
        story.append(Paragraph("II. PERFORMANCE GÉNÉRALE DU MINISTÈRE", section_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # II.1. Architecture du cadre de performance
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("II.1. Architecture du cadre de performance", subsection_title_style))
        
        # Tableau 2: Composantes des cadres de performance du ministère
        performance_data = partie_data.get("performance", {})
        architecture_data = performance_data.get("architecture", {})
        
        # Déterminer si les données de performance sont factices
        is_performance_fake = partie_data.get('_is_performance_fake', False)
        
        # Fonction helper pour formater les données de performance
        def format_performance_value(value: Any) -> str:
            """Formate une valeur de performance selon si elle est factice ou réelle."""
            if is_performance_fake:
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
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
        
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_numero}: Composantes des cadres de performance du ministère", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(tableau1)
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(partie_data.get("source", ""), source_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe après tableau 1 - formater toutes les valeurs dynamiques selon leur source
        formatted_ministere_para = RAPStylingManager.format_db_data(ministere)  # Toujours DB
        formatted_sigle_para = RAPStylingManager.format_db_data(RAPStylingManager.get_sigle_ministere())  # Toujours DB
        formatted_annee_para = RAPStylingManager.format_db_data(str(annee))  # Toujours DB
        
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
        
        # Tableau 3: Réalisations du cadre de performance du ministère
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
        
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_numero}: Réalisations du cadre de performance du ministère", subsection_title_style))
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
        
        formatted_annee_bilan = RAPStylingManager.format_db_data(str(annee))  # Année toujours DB
        formatted_annee_n1 = RAPStylingManager.format_db_data(str(annee_precedente))  # Année toujours DB
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
            programmes_text = f"le programme {RAPStylingManager.format_db_data(programmes_list[0])}"
        elif len(programmes_list) == 2:
            programmes_text = f"les programmes {RAPStylingManager.format_db_data(programmes_list[0])} et {RAPStylingManager.format_db_data(programmes_list[1])}"
        else:
            # Plus de 2 programmes : "P1, P2 et P3"
            programmes_formatted = [RAPStylingManager.format_db_data(p) for p in programmes_list[:-1]]
            programmes_text = f"les programmes {', '.join(programmes_formatted)} et {RAPStylingManager.format_db_data(programmes_list[-1])}"
        
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
        # Enregistrer la page AVANT le titre (après CondPageBreak)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        story.append(PageMarker("financement_global"))
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
        if (mode == "brouillon" and RAPBaseGenerator.should_use_fake_data() and
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
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
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
        formatted_annee_intro = RAPStylingManager.format_db_data(str(annee))  # Année toujours DB
        formatted_ministere_intro = RAPStylingManager.format_db_data(ministere) if ministere else RAPStylingManager.format_db_data("NC")  # Toujours DB
        formatted_sigle_intro = RAPStylingManager.format_db_data(RAPStylingManager.get_sigle_ministere())  # Toujours DB
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
            mode == "brouillon" and RAPBaseGenerator.should_use_fake_data() and is_financement_fake):
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
            para_intro = RAPStylingManager.format_db_data(para_intro)
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
                    if is_financement_fake and mode == "brouillon" and RAPBaseGenerator.should_use_fake_data():
                        formatted_raison = RAPStylingManager.format_fake_data(raison.strip())
                    else:
                        formatted_raison = RAPStylingManager.format_db_data(raison.strip())
                    story.append(Paragraph(formatted_raison, bullet_style, bulletText="•"))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Paragraphe d'introduction pour l'évolution par nature
        para_evolution_intro_default = "L'évolution des ressources budgétaires du ministère par nature de dépenses se présente comme suit :"
        para_evolution_intro = financement_interpretations.get("evolution_intro", para_evolution_intro_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if para_evolution_intro != para_evolution_intro_default:
            para_evolution_intro = RAPStylingManager.format_db_data(para_evolution_intro)
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
                evolution_personnel = RAPStylingManager.format_db_data(evolution_personnel)
        else:
            evolution_personnel_default = (
                f"<b>Dépenses de personnel :</b> Le budget est resté stable à {formatted_personnel_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_personnel = financement_interpretations.get("evolution_personnel", evolution_personnel_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_personnel != evolution_personnel_default:
                evolution_personnel = RAPStylingManager.format_db_data(evolution_personnel)
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
                evolution_biens = RAPStylingManager.format_db_data(evolution_biens)
        else:
            evolution_biens_default = (
                f"<b>Biens et services :</b> Le budget alloué est resté stable à {formatted_biens_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_biens = financement_interpretations.get("evolution_biens", evolution_biens_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_biens != evolution_biens_default:
                evolution_biens = RAPStylingManager.format_db_data(evolution_biens)
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
                evolution_transferts = RAPStylingManager.format_db_data(evolution_transferts)
        else:
            evolution_transferts_default = (
                f"<b>Transferts :</b> Le budget est resté stable à {formatted_transferts_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_transferts = financement_interpretations.get("evolution_transferts", evolution_transferts_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_transferts != evolution_transferts_default:
                evolution_transferts = RAPStylingManager.format_db_data(evolution_transferts)
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
                evolution_investissements = RAPStylingManager.format_db_data(evolution_investissements)
        else:
            evolution_investissements_default = (
                f"<b>Investissements :</b> Le budget est resté stable à {formatted_investissements_reel_evol} FCFA "
                f"(<b>Annexe 4, loi des finances {formatted_annee_intro}</b> et budget actuel {formatted_annee_intro})."
            )
            evolution_investissements = financement_interpretations.get("evolution_investissements", evolution_investissements_default)
            # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
            if evolution_investissements != evolution_investissements_default:
                evolution_investissements = RAPStylingManager.format_db_data(evolution_investissements)
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
        formatted_ministere_repart = RAPStylingManager.format_db_data(ministere) if ministere else RAPStylingManager.format_db_data("NC")  # Toujours DB
        formatted_sigle_repart = RAPStylingManager.format_db_data(RAPStylingManager.get_sigle_ministere())  # Toujours DB
        formatted_budget_reel_repart = format_financement_value(format_fcfa(budget_reel_total)) if budget_reel_total > 0 else format_financement_value("0")
        
        para_repartition_default = (
            f"Ainsi, le budget actuel du {formatted_ministere_repart} ({formatted_sigle_repart}) s'élève à un total de "
            f"<b>{formatted_budget_reel_repart} F CFA</b>, réparti par nature de dépenses comme suit :"
        )
        para_repartition = financement_interpretations.get("repartition_intro", para_repartition_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if para_repartition != para_repartition_default:
            para_repartition = RAPStylingManager.format_db_data(para_repartition)
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
            repartition_personnel = RAPStylingManager.format_db_data(repartition_personnel)
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
            repartition_biens = RAPStylingManager.format_db_data(repartition_biens)
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
            repartition_transferts = RAPStylingManager.format_db_data(repartition_transferts)
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
            repartition_investissements = RAPStylingManager.format_db_data(repartition_investissements)
        story.append(Paragraph(repartition_investissements, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Ajouter le graphique en camembert (Figure 1)
        story.append(Spacer(1, 0.3 * cm))
        figure_numero = RAPBaseGenerator.get_next_figure_numero()
        story.append(Paragraph(f"<b>Figure {figure_numero}: Répartition du budget actuel du Ministère par natures de dépenses</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Générer le graphique en camembert
        pie_chart_buffer = RAPChartGenerator.create_pie_chart_budget(
            personnel_reel, pct_personnel,
            biens_reel, pct_biens,
            transferts_reel, pct_transferts,
            investissements_reel, pct_investissements,
            titre_ministere=ministere
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
                source_text = RAPStylingManager.format_db_data(source_text)
            else:
                # Formater les parties dynamiques (année) dans la source par défaut
                source_text = RAPStylingManager.format_db_data(source_text)
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
                    
                    # Dessiner le graphique
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
                
                def wrap(self, availWidth, availHeight):
                    return self.width, self.height
            
            # Créer le flowable combiné
            pie_with_source = PieChartWithSource(source_para, pie_chart_buffer, chart_width, chart_height, available_width)
            story.append(pie_with_source)
            story.append(Spacer(1, 0.3 * cm))
        
        # Tableau 4: Tableau présentant l'exécution du budget du ministère
        story.append(CondPageBreak(5 * cm))
        story.append(Spacer(1, 0.3 * cm))
        intro_tableau3_default = "Le tableau ci-dessous rend compte de l'exécution des budgets alloués au Ministère."
        intro_tableau3 = financement_interpretations.get("intro_tableau3", intro_tableau3_default)
        # Si c'est un commentaire personnalisé (de la DB), le formater en rouge
        if intro_tableau3 != intro_tableau3_default:
            intro_tableau3 = RAPStylingManager.format_db_data(intro_tableau3)
        story.append(Paragraph(intro_tableau3, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Titre du tableau
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        story.append(Paragraph(f"<b>Tableau {tableau_numero}: Tableau présentant l'exécution du budget du ministère</b>", subsection_title_style))
        
        # Récupérer les données pour le tableau 3 depuis la base de données
        annee_precedente = annee - 1
        
        # Vérifier si on doit utiliser des données factices ou réelles
        is_tableau3_fake = is_financement_fake
        
        # Récupérer les données d'exécution depuis sigobe_execution pour l'année précédente et l'année courante
        budget_annee_precedente_realisation = 0
        budget_annee_prevue = 0
        budget_annee_realisee = 0
        
        personnel_n1_realisation = 0
        personnel_prev = 0
        personnel_real = 0
        
        biens_n1_realisation = 0
        biens_prev = 0
        biens_real_exec = 0
        
        transferts_n1_realisation = 0
        transferts_prev = 0
        transferts_real_exec = 0
        
        investissements_n1_realisation = 0
        investissements_prev = 0
        investissements_real_exec = 0
        
        # Si mode final et données vides, utiliser 0 partout (pas de données factices)
        if mode == "final" and not is_financement_fake and budget_reel_total == 0:
            logger.info(f"📊 Mode final avec base vide: toutes les valeurs du tableau 3 seront à 0")
            is_tableau3_fake = False
            # Toutes les variables restent à 0 (déjà initialisées)
        elif RAPBaseGenerator._db_session and not is_financement_fake:
            # Récupérer les vraies données depuis sigobe_execution
            try:
                from app.models.budget import SigobeExecution, SigobeChargement
                session = RAPBaseGenerator._db_session
                
                # Récupérer les chargements pour les deux années
                chargement_annee_precedente = session.exec(
                    select(SigobeChargement)
                    .where(SigobeChargement.annee == annee_precedente)
                    .order_by(SigobeChargement.date_chargement.desc())
                ).first()
                
                chargement_annee = session.exec(
                    select(SigobeChargement)
                    .where(SigobeChargement.annee == annee)
                    .order_by(SigobeChargement.date_chargement.desc())
                ).first()
                
                if chargement_annee_precedente:
                    # Données pour l'année précédente (réalisations)
                    sigobe_n1 = session.exec(
                        select(SigobeExecution)
                        .where(SigobeExecution.chargement_id == chargement_annee_precedente.id)
                    ).all()
                    
                    for exec_sigobe in sigobe_n1:
                        montant_execute = float(exec_sigobe.budget_execute or 0)
                        budget_annee_precedente_realisation += montant_execute
                        
                        # Par nature
                        type_dep = (exec_sigobe.type_depense or "").upper()
                        if "PERSONNEL" in type_dep or type_dep == "P":
                            personnel_n1_realisation += montant_execute
                        elif "BIENS" in type_dep or "SERVICES" in type_dep or type_dep == "BS":
                            biens_n1_realisation += montant_execute
                        elif "TRANSFERT" in type_dep or type_dep == "T":
                            transferts_n1_realisation += montant_execute
                        elif "INVESTISSEMENT" in type_dep or type_dep == "I":
                            investissements_n1_realisation += montant_execute
                
                if chargement_annee:
                    # Données pour l'année courante (prévu et réalisé)
                    sigobe_n = session.exec(
                        select(SigobeExecution)
                        .where(SigobeExecution.chargement_id == chargement_annee.id)
                    ).all()
                    
                    for exec_sigobe in sigobe_n:
                        budget_vote = float(exec_sigobe.budget_vote or 0)
                        budget_execute = float(exec_sigobe.budget_execute or 0)
                        
                        budget_annee_prevue += budget_vote
                        budget_annee_realisee += budget_execute
                        
                        # Par nature
                        type_dep = (exec_sigobe.type_depense or "").upper()
                        if "PERSONNEL" in type_dep or type_dep == "P":
                            personnel_prev += budget_vote
                            personnel_real += budget_execute
                        elif "BIENS" in type_dep or "SERVICES" in type_dep or type_dep == "BS":
                            biens_prev += budget_vote
                            biens_real_exec += budget_execute
                        elif "TRANSFERT" in type_dep or type_dep == "T":
                            transferts_prev += budget_vote
                            transferts_real_exec += budget_execute
                        elif "INVESTISSEMENT" in type_dep or type_dep == "I":
                            investissements_prev += budget_vote
                            investissements_real_exec += budget_execute
                
                logger.info(f"📊 Données tableau 3 chargées depuis DB: N-1={budget_annee_precedente_realisation}, N prévu={budget_annee_prevue}, N réalisé={budget_annee_realisee}")
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du chargement des données d'exécution pour le tableau 3: {e}")
                # En cas d'erreur, utiliser 0 (mode final)
                if mode == "final":
                    is_tableau3_fake = False
                    # Variables déjà à 0
                else:
                    is_tableau3_fake = True
        elif is_financement_fake:
            # Mode brouillon avec données factices
            is_tableau3_fake = True
            budget_annee_precedente_realisation = budget_reel_total * 0.95
            budget_annee_prevue = budget_reel_total
            budget_annee_realisee = budget_annee_prevue * 0.95  # 95% d'exécution
            
            personnel_n1_realisation = personnel_reel * 0.95
            personnel_prev = personnel_reel
            personnel_real = personnel_prev * 0.97  # 97% d'exécution
            
            biens_n1_realisation = biens_reel * 0.95
            biens_prev = biens_reel
            biens_real_exec = biens_prev * 0.90  # 90% d'exécution
            
            transferts_n1_realisation = transferts_reel
            transferts_prev = transferts_reel
            transferts_real_exec = transferts_prev  # 100% d'exécution
            
            investissements_n1_realisation = investissements_reel * 0.95
            investissements_prev = investissements_reel
            investissements_real_exec = investissements_prev * 0.85  # 85% d'exécution
        
        # Calculer les écarts et taux pour l'année courante (totaux)
        ecart_annee = budget_annee_prevue - budget_annee_realisee
        tx_real_annee = (budget_annee_realisee / budget_annee_prevue * 100) if budget_annee_prevue > 0 else 0
        
        # Calculer les écarts et taux par nature
        personnel_ecart = personnel_prev - personnel_real
        personnel_tx = (personnel_real / personnel_prev * 100) if personnel_prev > 0 else 0
        
        biens_ecart = biens_prev - biens_real_exec
        biens_tx = (biens_real_exec / biens_prev * 100) if biens_prev > 0 else 0
        
        transferts_ecart = transferts_prev - transferts_real_exec
        transferts_tx = (transferts_real_exec / transferts_prev * 100) if transferts_prev > 0 else 0
        
        investissements_ecart = investissements_prev - investissements_real_exec
        investissements_tx = (investissements_real_exec / investissements_prev * 100) if investissements_prev > 0 else 0
        
        # Fonction de formatage spécifique pour le tableau 3
        def format_tableau3_value(value: Any) -> str:
            """Formate une valeur du tableau 3 selon si elle est factice ou réelle."""
            if is_tableau3_fake:
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
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
        # Formater les années dans les en-têtes selon leur source (dynamiques - toujours DB)
        annee_precedente = annee - 1
        annee_precedente_formatted = RAPStylingManager.format_db_data(str(annee_precedente))
        annee_actuelle_formatted = RAPStylingManager.format_db_data(str(annee))
        
        # Formater les valeurs communes (zéro et tiret) selon leur source
        formatted_zero = format_tableau3_value(format_fcfa(0))
        formatted_dash = format_tableau3_value("-")
        
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
        formatted_budget_annee_precedente = format_tableau3_value(format_fcfa(budget_annee_precedente_realisation))
        formatted_prev_annee = format_tableau3_value(format_fcfa(budget_annee_prevue))
        formatted_real_annee = format_tableau3_value(format_fcfa(budget_annee_realisee))
        formatted_ecart_annee = format_tableau3_value(format_fcfa(ecart_annee))
        formatted_tx_real_annee = format_tableau3_value(f"{tx_real_annee:.2f}%")
        
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
        formatted_personnel_n1 = format_tableau3_value(format_fcfa(personnel_n1_realisation))
        formatted_personnel_prev = format_tableau3_value(format_fcfa(personnel_prev))
        formatted_personnel_real = format_tableau3_value(format_fcfa(personnel_real))
        formatted_personnel_ecart = format_tableau3_value(format_fcfa(personnel_ecart))
        formatted_personnel_tx = format_tableau3_value(f"{personnel_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Personnel", table_cell_style),
            Paragraph(formatted_personnel_n1, table_cell_right_style),
            Paragraph(formatted_personnel_prev, table_cell_right_style),
            Paragraph(formatted_personnel_real, table_cell_right_style),
            Paragraph(formatted_personnel_ecart, table_cell_right_style),
            Paragraph(formatted_personnel_tx, table_cell_center_style),
        ])
        
        # 2.1.1 Solde - Utiliser 0 si base vide, valeurs factices si mode brouillon
        solde_n1 = personnel_n1_realisation * 0.95 if is_tableau3_fake else 0
        solde_prev = personnel_prev * 0.95 if is_tableau3_fake else 0
        solde_real = personnel_real * 0.95 if is_tableau3_fake else 0
        solde_ecart = solde_prev - solde_real
        solde_tx = (solde_real / solde_prev * 100) if solde_prev > 0 else 0
        
        formatted_solde_n1 = format_tableau3_value(format_fcfa(solde_n1))
        formatted_solde_prev = format_tableau3_value(format_fcfa(solde_prev))
        formatted_solde_real = format_tableau3_value(format_fcfa(solde_real))
        formatted_solde_ecart = format_tableau3_value(format_fcfa(solde_ecart))
        formatted_solde_tx = format_tableau3_value(f"{solde_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.1 Solde y compris EPN", table_cell_style),
            Paragraph(formatted_solde_n1, table_cell_right_style),
            Paragraph(formatted_solde_prev, table_cell_right_style),
            Paragraph(formatted_solde_real, table_cell_right_style),
            Paragraph(formatted_solde_ecart, table_cell_right_style),
            Paragraph(formatted_solde_tx, table_cell_center_style),
        ])
        
        # 2.1.2 Contractuels - Utiliser 0 si base vide, valeurs factices si mode brouillon
        contractuels_n1 = personnel_n1_realisation * 0.05 if is_tableau3_fake else 0
        contractuels_prev = personnel_prev * 0.05 if is_tableau3_fake else 0
        contractuels_real = personnel_real * 0.05 if is_tableau3_fake else 0
        contractuels_ecart = contractuels_prev - contractuels_real
        contractuels_tx = (contractuels_real / contractuels_prev * 100) if contractuels_prev > 0 else 0
        
        formatted_contractuels_n1 = format_tableau3_value(format_fcfa(contractuels_n1))
        formatted_contractuels_prev = format_tableau3_value(format_fcfa(contractuels_prev))
        formatted_contractuels_real = format_tableau3_value(format_fcfa(contractuels_real))
        formatted_contractuels_ecart = format_tableau3_value(format_fcfa(contractuels_ecart))
        formatted_contractuels_tx = format_tableau3_value(f"{contractuels_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.2 Contractuels hors solde", table_cell_style),
            Paragraph(formatted_contractuels_n1, table_cell_right_style),
            Paragraph(formatted_contractuels_prev, table_cell_right_style),
            Paragraph(formatted_contractuels_real, table_cell_right_style),
            Paragraph(formatted_contractuels_ecart, table_cell_right_style),
            Paragraph(formatted_contractuels_tx, table_cell_center_style),
        ])
        
        # 2.2 Biens et Service
        # Formater toutes les valeurs numériques selon leur source
        formatted_biens_n1 = format_tableau3_value(format_fcfa(biens_n1_realisation))
        formatted_biens_prev = format_tableau3_value(format_fcfa(biens_prev))
        formatted_biens_real = format_tableau3_value(format_fcfa(biens_real_exec))
        formatted_biens_ecart = format_tableau3_value(format_fcfa(biens_ecart))
        formatted_biens_tx = format_tableau3_value(f"{biens_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Biens et Service", table_cell_style),
            Paragraph(formatted_biens_n1, table_cell_right_style),
            Paragraph(formatted_biens_prev, table_cell_right_style),
            Paragraph(formatted_biens_real, table_cell_right_style),
            Paragraph(formatted_biens_ecart, table_cell_right_style),
            Paragraph(formatted_biens_tx, table_cell_center_style),
        ])
        
        # 2.3 Transferts
        formatted_transferts_n1 = format_tableau3_value(format_fcfa(transferts_n1_realisation))
        formatted_transferts_prev = format_tableau3_value(format_fcfa(transferts_prev))
        formatted_transferts_real = format_tableau3_value(format_fcfa(transferts_real_exec))
        formatted_transferts_ecart = format_tableau3_value(format_fcfa(transferts_ecart))
        formatted_transferts_tx = format_tableau3_value(f"{transferts_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 Transferts", table_cell_style),
            Paragraph(formatted_transferts_n1, table_cell_right_style),
            Paragraph(formatted_transferts_prev, table_cell_right_style),
            Paragraph(formatted_transferts_real, table_cell_right_style),
            Paragraph(formatted_transferts_ecart, table_cell_right_style),
            Paragraph(formatted_transferts_tx, table_cell_center_style),
        ])
        
        # 2.3.1 Transferts courants - Utiliser les mêmes valeurs que les transferts totaux
        # Le taux est calculé basé sur transferts_prev et transferts_real_exec (déjà calculé dans transferts_tx)
        formatted_transferts_courants_tx = formatted_transferts_tx
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.1 Transferts courants", table_cell_style),
            Paragraph(formatted_transferts_n1, table_cell_right_style),
            Paragraph(formatted_transferts_prev, table_cell_right_style),
            Paragraph(formatted_transferts_real, table_cell_right_style),
            Paragraph(formatted_transferts_ecart, table_cell_right_style),
            Paragraph(formatted_transferts_courants_tx, table_cell_center_style),
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
        formatted_investissements_n1 = format_tableau3_value(format_fcfa(investissements_n1_realisation))
        formatted_investissements_prev = format_tableau3_value(format_fcfa(investissements_prev))
        formatted_investissements_real = format_tableau3_value(format_fcfa(investissements_real_exec))
        formatted_investissements_ecart = format_tableau3_value(format_fcfa(investissements_ecart))
        formatted_investissements_tx = format_tableau3_value(f"{investissements_tx:.2f}%")
        
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Investissement", table_cell_style),
            Paragraph(formatted_investissements_n1, table_cell_right_style),
            Paragraph(formatted_investissements_prev, table_cell_right_style),
            Paragraph(formatted_investissements_real, table_cell_right_style),
            Paragraph(formatted_investissements_ecart, table_cell_right_style),
            Paragraph(formatted_investissements_tx, table_cell_center_style),
        ])
        
        # 2.4.1 Trésor
        table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.1 Trésor", table_cell_style),
            Paragraph(formatted_investissements_n1, table_cell_right_style),
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
        formatted_annee_prec_financement = RAPStylingManager.format_db_data(str(annee_precedente_financement))
        story.append(Paragraph(f"Source: Situation d'exécution issue du SIGOBE / RAP {formatted_annee_prec_financement}", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Analyse de l'exécution budgétaire
        # Calculer les taux d'exécution réels basés sur les données
        tx_execution_global = (budget_annee_realisee / budget_annee_prevue * 100) if budget_annee_prevue > 0 else 0
        tx_execution_personnel = (personnel_real / personnel_prev * 100) if personnel_prev > 0 else 0
        tx_execution_biens = (biens_real_exec / biens_prev * 100) if biens_prev > 0 else 0
        tx_execution_transferts = (transferts_real_exec / transferts_prev * 100) if transferts_prev > 0 else 0
        tx_execution_investissements = (investissements_real_exec / investissements_prev * 100) if investissements_prev > 0 else 0
        
        # Formatage des montants et taux selon leur source (factice ou DB) - utiliser format_financement_value
        formatted_annee = format_financement_value(str(annee))
        formatted_prev_annee = format_financement_value(format_fcfa(budget_annee_prevue))
        formatted_real_annee = format_financement_value(format_fcfa(budget_annee_realisee))
        formatted_tx_global = format_financement_value(f"{tx_execution_global:.2f}%")
        formatted_personnel_prev = format_financement_value(format_fcfa(personnel_prev))
        formatted_personnel_real = format_financement_value(format_fcfa(personnel_real))
        formatted_biens_prev = format_financement_value(format_fcfa(biens_prev))
        formatted_biens_real = format_financement_value(format_fcfa(biens_real_exec))
        formatted_tx_biens = format_financement_value(f"{tx_execution_biens:.2f}%")
        formatted_transferts_prev = format_financement_value(format_fcfa(transferts_prev))
        formatted_tx_transferts = format_financement_value(f"{tx_execution_transferts:.2f}%")
        formatted_investissements_prev = format_financement_value(format_fcfa(investissements_prev))
        formatted_investissements_real = format_financement_value(format_fcfa(investissements_real_exec))
        formatted_tx_investissements = format_financement_value(f"{tx_execution_investissements:.2f}%")
        
        # Récupérer les interprétations personnalisées pour l'analyse d'exécution
        financement_interpretations = cls.data.get("financement_interpretations", {})
        
        # Commentaire sur le personnel (personnalisable)
        commentaire_personnel = financement_interpretations.get("analyse_personnel_commentaire")
        if commentaire_personnel and commentaire_personnel.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_personnel_formatted = RAPStylingManager.format_db_data(commentaire_personnel.strip())
            phrase_personnel = f"Concernant les dépenses de personnel, le budget prévu était de <b>{formatted_personnel_prev}</b>, et le montant effectivement exécuté s'est élevé à <b>{formatted_personnel_real}</b>. {commentaire_personnel_formatted}<br/><br/>"
        else:
            phrase_personnel = f"Concernant les dépenses de personnel, le budget prévu était de <b>{formatted_personnel_prev}</b>, et le montant effectivement exécuté s'est élevé à <b>{formatted_personnel_real}</b>.<br/><br/>"
        
        # Commentaire sur les biens et services (personnalisable)
        commentaire_biens = financement_interpretations.get("analyse_biens_commentaire")
        if commentaire_biens and commentaire_biens.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_biens_formatted = RAPStylingManager.format_db_data(commentaire_biens.strip())
            phrase_biens = f"Pour ce qui est des biens et services, le budget alloué qui était de <b>{formatted_biens_prev}</b>, a été exécuté à hauteur de <b>{formatted_biens_real}</b> soit un taux d'exécution de <b>{formatted_tx_biens}</b>. {commentaire_biens_formatted}<br/><br/>"
        else:
            phrase_biens = f"Pour ce qui est des biens et services, le budget alloué qui était de <b>{formatted_biens_prev}</b>, a été exécuté à hauteur de <b>{formatted_biens_real}</b> soit un taux d'exécution de <b>{formatted_tx_biens}</b>.<br/><br/>"
        
        # Commentaire sur les transferts (personnalisable, sans mention fixe de la SONAPIE)
        commentaire_transferts = financement_interpretations.get("analyse_transferts_commentaire")
        if commentaire_transferts and commentaire_transferts.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_transferts_formatted = RAPStylingManager.format_db_data(commentaire_transferts.strip())
            phrase_transferts = f"Concernant les transferts, le montant programmé de <b>{formatted_transferts_prev}</b> a été entièrement exécuté. Le taux d'exécution est ainsi de <b>{formatted_tx_transferts}</b>, {commentaire_transferts_formatted}<br/><br/>"
        else:
            # Version générique sans mention spécifique
            phrase_transferts = f"Concernant les transferts, le montant programmé de <b>{formatted_transferts_prev}</b> a été entièrement exécuté. Le taux d'exécution est ainsi de <b>{formatted_tx_transferts}</b>.<br/><br/>"
        
        # Commentaire sur les investissements (personnalisable)
        commentaire_investissements = financement_interpretations.get("analyse_investissements_commentaire")
        if commentaire_investissements and commentaire_investissements.strip():
            # Formater le commentaire personnalisé en rouge (données DB)
            commentaire_investissements_formatted = RAPStylingManager.format_db_data(commentaire_investissements.strip())
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
        logger.info(f"🔢 NUMÉROTATION - AVANT _render_multipage_story pour partie I: start_page={start_page}")
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
        logger.info(f"🔢 NUMÉROTATION - APRÈS _render_multipage_story pour partie I: final_page={final_page}")
        logger.info(f"🔢 NUMÉROTATION - draw_partie_i_ministere FIN: retourne final_page={final_page}")
        
        return final_page
    
    @classmethod
    def draw_conclusion_generale(
        cls,
        start_page: int,
        session=None
    ) -> tuple[BytesIO, int]:
        """
        Dessine la conclusion générale du rapport.
        
        Cette méthode génère la conclusion générale qui inclut :
        - Un résumé de l'année écoulée
        - Les points positifs
        - Les difficultés rencontrées
        - Les recommandations
        - La conclusion générale avec signature du ministre
        
        Args:
            start_page: Numéro de page de début
            session: Session de base de données (optionnel)
        
        Returns:
            Tuple (buffer du PDF temporaire, numéro de la dernière page + 1)
        
        Note:
            Cette méthode utilise SimpleDocTemplate pour gérer le contenu fluide.
            Les données proviennent de RapData (conclusion_interpretations, conclusion_generale).
            La signature du ministre est formatée avec gestion du wrap pour les titres longs.
        """
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, CondPageBreak, Table, TableStyle
        from reportlab.lib.styles import ParagraphStyle
        from datetime import datetime
        
        logger.info(f"📄 Génération de la CONCLUSION GÉNÉRALE (page {start_page})")
        
        # Créer un buffer temporaire pour cette section
        temp_buffer = BytesIO()
        
        # Dimensions de la page
        page_width, page_height = landscape(A4)
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        footer_height = 1.5 * cm
        footer_margin = 0.5 * cm
        bottom_margin = footer_height + footer_margin
        
        available_width = page_width - left_margin - right_margin
        available_height = page_height - top_margin - bottom_margin
        
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
        
        title_width_limit = available_width * 0.3
        title_style = ParagraphStyle(
            "MinisterTitle",
            parent=signature_style,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=1,  # Center align
            spaceBefore=0,
            spaceAfter=0.1 * cm,
            leftIndent=0,
            rightIndent=0,
        )
        
        story = []
        
        # Titre
        story.append(PageMarker("conclusion_generale"))
        story.append(Paragraph("CONCLUSION GÉNÉRALE", section_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Récupérer les données nécessaires
        annee = cls.data.get("annee", datetime.now().year)
        ministere = cls.data.get("ministere", "")
        sigle_ministere = RAPStylingManager.get_sigle_ministere()
        
        # Récupérer les données de conclusion générale depuis RapData
        conclusion_generale_data = cls.data.get("conclusion_generale", {})
        is_conclusion_generale_fake = False
        
        # Vérifier le mode et générer des données factices si nécessaire
        mode = cls.data.get("mode", "brouillon")
        if not conclusion_generale_data and mode == "brouillon":
            logger.info(f"📊 Mode brouillon: génération de données factices pour la conclusion générale")
            is_conclusion_generale_fake = True
            
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
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
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
            formatted_perspectives = format_programme_value(perspectives, is_conclusion_generale_fake)
            story.append(Paragraph(formatted_perspectives, body_style))
        
        story.append(Spacer(1, 0.5 * cm))
        
        # Signature
        intro_data = cls.data.get("introduction", {})
        ministre_nom = intro_data.get("ministre_nom", "")
        if not ministre_nom or ministre_nom == "NC":
            ministre_nom = "Moussa SANOGO"  # Factice
        
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
        empty_cell = Paragraph("", signature_style)
        
        signature_table_data = [
            [empty_cell, date_para],
            [empty_cell, Paragraph("", signature_style)],
            [empty_cell, title_para1],
            [empty_cell, title_para2],
            [empty_cell, Paragraph("", signature_style)],
            [empty_cell, name_para],
        ]
        
        col_widths = [
            available_width * 0.60,
            available_width * 0.40,
        ]
        
        row_heights = [
            None,
            0.2 * cm,
            None,
            None,
            2.5 * cm,
            None,
        ]
        
        signature_table = Table(signature_table_data, colWidths=col_widths, rowHeights=row_heights)
        
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(signature_table)
        
        # Fonction pour dessiner le footer avec numéro de page
        page_counter = start_page - 1
        
        def on_page(canv, doc_obj):
            """Callback appelé à chaque page pour dessiner le footer."""
            nonlocal page_counter
            page_counter += 1
            
            cls._current_rendering_page = page_counter
            canv._pageNumber = page_counter - 1
            
            canv.saveState()
            card_size = 1.0 * cm
            corner_size = 0.3 * cm
            card_x = page_width - right_margin - card_size
            card_y = bottom_margin - footer_margin
            
            canv.setFillColor(colors.white)
            canv.setStrokeColor(colors.HexColor("#E0E0E0"))
            canv.setLineWidth(0.5)
            canv.roundRect(card_x, card_y, card_size, card_size, 0.2 * cm, fill=1, stroke=1)
            
            corner_path = canv.beginPath()
            corner_path.moveTo(card_x + card_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size - corner_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size, card_y + card_size - corner_size)
            corner_path.close()
            canv.setFillColor(colors.HexColor("#F0F0F0"))
            canv.setStrokeColor(colors.HexColor("#E0E0E0"))
            canv.drawPath(corner_path, fill=1, stroke=1)
            
            canv.setFillColor(colors.black)
            canv.setFont("Helvetica", 10)
            text_width = canv.stringWidth(str(page_counter), "Helvetica", 10)
            text_x = card_x + (card_size - text_width) / 2
            text_y = card_y + (card_size - 10) / 2 - 3
            canv.drawString(text_x, text_y, str(page_counter))
            canv.restoreState()
            
        
        # Construire le PDF avec SimpleDocTemplate
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        
        cls._current_rendering_page = None
        
        temp_buffer.seek(0)
        
        temp_reader = PdfReader(temp_buffer)
        num_pages = len(temp_reader.pages)
        final_page = start_page + num_pages - 1
        
        temp_buffer.seek(0)
        logger.info(f"✅ Conclusion générale générée : {num_pages} pages (de {start_page} à {final_page})")
        
        return temp_buffer, final_page
    
    @classmethod
    def _build_toc_items_from_pdf_or_positions(
        cls,
        pdf_reader_complet: PdfReader | None = None,
        nb_pages_sommaire: int = 0
    ) -> list[dict[str, Any]]:
        """
        Construit la liste des éléments du sommaire depuis le PDF ou les positions enregistrées.
        
        Cette méthode utilise deux approches :
        1. Si un PDF complet est fourni : recherche les textes dans le PDF (approche "Word-like")
        2. Sinon : utilise les pages enregistrées avec PageMarker (approche par marqueurs)
        
        Args:
            pdf_reader_complet: PdfReader du PDF complet pour recherche de texte (optionnel)
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Liste de dictionnaires contenant les éléments du sommaire avec :
            - text: Texte de l'élément
            - page: Numéro de page
            - level: Niveau d'indentation (0 = principal, 1 = sous-section)
            - bold: Si le texte doit être en gras
        
        Note:
            La structure du sommaire est fixe et prédéfinie.
            Les numéros de page sont déterminés dynamiquement.
        """
        toc_items = []
        
        # Récupérer les programmes
        programmes = cls.data.get("programmes", [])
        annee = cls.data.get("annee", "")
        
        # Si aucun programme n'est disponible, créer des programmes factices pour le sommaire
        if not programmes:
            programmes = [
                {"numero": 1, "titre": "ADMINISTRATION GÉNÉRALE"},
                {"numero": 2, "titre": "Portefeuille de l'État"}
            ]
            logger.info("📋 Aucun programme trouvé, utilisation de programmes factices pour le sommaire")
        
        # Si un PDF complet est fourni, chercher les textes dedans (approche Word)
        # Sinon, utiliser les pages trouvées depuis cls._page_positions (qui contient les pages ajustées)
        if pdf_reader_complet:
            logger.info("🔍 Recherche des textes dans le PDF complet (approche Word)...")
            # Chercher dans le PDF (sans ajustement, car nb_pages_sommaire sera appliqué après)
            pages_found = RAPPageManager.find_all_toc_pages(pdf_reader_complet, nb_pages_sommaire=0)
            logger.info(f"✅ Pages trouvées dans le PDF: {pages_found}")
            
            logger.info(f"📄 Utilisation des pages SANS ajustement dans _build_toc_items (nb_pages_sommaire={nb_pages_sommaire} pages ignorées)")
            
            # 1. Éléments préliminaires
            toc_items.append({
                "text": "LISTE DES TABLEAUX", 
                "page": pages_found.get("liste_tableaux", 3), 
                "level": 0, 
                "bold": False
            })
            toc_items.append({
                "text": "LISTE DES GRAPHIQUES", 
                "page": pages_found.get("liste_graphiques", 3), 
                "level": 0, 
                "bold": False
            })
            toc_items.append({
                "text": "SIGLES ET ABRÉVIATIONS", 
                "page": pages_found.get("sigles_abreviations", 5), 
                "level": 0, 
                "bold": False
            })
            toc_items.append({
                "text": "INTRODUCTION GÉNÉRALE", 
                "page": pages_found.get("introduction_generale", 7), 
                "level": 0, 
                "bold": False
            })
            
            # 2. PARTIE I : LE MINISTÈRE
            partie_i_page = pages_found.get("partie_i", 8)
            toc_items.append({
                "text": "PARTIE I : LE MINISTÈRE", 
                "page": partie_i_page, 
                "level": 0, 
                "bold": True
            })
            toc_items.append({
                "text": "I. PRÉSENTATION GÉNÉRALE DU MINISTÈRE", 
                "page": pages_found.get("presentation_generale", partie_i_page), 
                "level": 1, 
                "bold": False
            })
            
            # Chercher les sous-sections de la Partie I
            performance_page = pages_found.get("performance_generale", partie_i_page + 1)
            financement_page = pages_found.get("financement_global", partie_i_page + 2)
            
            toc_items.append({
                "text": "II. PERFORMANCE GÉNÉRALE DU MINISTÈRE", 
                "page": performance_page, 
                "level": 1, 
                "bold": False
            })
            toc_items.append({
                "text": "III. FINANCEMENT GLOBAL DU MINISTÈRE", 
                "page": financement_page, 
                "level": 1, 
                "bold": False
            })
            
            # 3. Programmes
            for idx, programme in enumerate(programmes):
                numero = programme.get("numero", 1)
                titre = programme.get("titre", "")
                
                # Récupérer les pages trouvées pour ce programme
                pages = {
                    "start": pages_found.get(f"programme_{numero}_start", 13 + (idx * 17)),
                    "intro": pages_found.get(f"programme_{numero}_intro", 13 + (idx * 17)),
                    "strategie": pages_found.get(f"programme_{numero}_strategie", 14 + (idx * 17)),
                    "realisations": pages_found.get(f"programme_{numero}_realisations", 16 + (idx * 17)),
                    "performance": pages_found.get(f"programme_{numero}_performance", 24 + (idx * 17)),
                    "conclusion": pages_found.get(f"programme_{numero}_conclusion", 29 + (idx * 17))
                }
                
                # Ajouter PERSPECTIVES si disponible pour le programme 2
                if numero == 2:
                    pages["perspectives"] = pages_found.get(f"programme_{numero}_perspectives", 47)
                
                # Titre de la partie
                partie_text = f"PARTIE {numero + 1} : LE PROGRAMME {numero} « {titre.upper()} »"
                toc_items.append({
                    "text": partie_text, 
                    "page": pages["start"], 
                    "level": 0, 
                    "bold": True
                })
                
                # Structure fixe pour chaque programme
                toc_items.append({
                    "text": "INTRODUCTION", 
                    "page": pages["intro"], 
                    "level": 1, 
                    "bold": False
                })
                toc_items.append({
                    "text": "I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", 
                    "page": pages["strategie"], 
                    "level": 1, 
                    "bold": False
                })
                toc_items.append({
                    "text": f"II. RÉALISATIONS DU PROGRAMME « {titre.upper()} » AU COURS DE L'EXERCICE {annee}", 
                    "page": pages["realisations"], 
                    "level": 1, 
                    "bold": False
                })
                toc_items.append({
                    "text": "III. PERFORMANCE DU PROGRAMME", 
                    "page": pages["performance"], 
                    "level": 1, 
                    "bold": False
                })
                
                # IV. PERSPECTIVES - seulement pour le programme 2
                if "perspectives" in pages:
                    toc_items.append({
                        "text": "IV. PERSPECTIVES", 
                        "page": pages["perspectives"], 
                        "level": 1, 
                        "bold": False
                    })
                
                toc_items.append({
                    "text": "CONCLUSION", 
                    "page": pages["conclusion"], 
                    "level": 1, 
                    "bold": False
                })
        
        else:
            # Ancienne approche : utiliser les positions enregistrées
            logger.info("📋 Utilisation des positions enregistrées pour le sommaire...")
            
            # 1. Éléments préliminaires
            toc_items.append({
                "text": "LISTE DES TABLEAUX", 
                "page": RAPPageManager.get_page_position("liste_tableaux", 3), 
                "level": 0, 
                "bold": False
            })
            toc_items.append({
                "text": "LISTE DES GRAPHIQUES", 
                "page": RAPPageManager.get_page_position("liste_graphiques", 3), 
                "level": 0, 
                "bold": False
            })
            toc_items.append({
                "text": "SIGLES ET ABRÉVIATIONS", 
                "page": RAPPageManager.get_page_position("sigles_abreviations", 5), 
                "level": 0, 
                "bold": False
            })
            toc_items.append({
                "text": "INTRODUCTION GÉNÉRALE", 
                "page": RAPPageManager.get_page_position("introduction_generale", 7), 
                "level": 0, 
                "bold": False
            })
            
            # 2. PARTIE I : LE MINISTÈRE
            partie_i_page = RAPPageManager.get_page_position("partie_i", 8)
            toc_items.append({
                "text": "PARTIE I : LE MINISTÈRE", 
                "page": partie_i_page, 
                "level": 0, 
                "bold": True
            })
            toc_items.append({
                "text": "I. PRÉSENTATION GÉNÉRALE DU MINISTÈRE", 
                "page": partie_i_page, 
                "level": 1, 
                "bold": False
            })
            toc_items.append({
                "text": "II. PERFORMANCE GÉNÉRALE DU MINISTÈRE", 
                "page": partie_i_page + 1, 
                "level": 1, 
                "bold": False
            })
            toc_items.append({
                "text": "III. FINANCEMENT GLOBAL DU MINISTÈRE", 
                "page": partie_i_page + 2, 
                "level": 1, 
                "bold": False
            })
            
            # 3. Programmes
            for idx, programme in enumerate(programmes):
                numero = programme.get("numero", 1)
                titre = programme.get("titre", "")
                
                # Récupérer les pages calculées pour ce programme
                pages = {
                    "start": RAPPageManager.get_page_position(f"programme_{numero}_start", 13 + (idx * 17)),
                    "intro": RAPPageManager.get_page_position(f"programme_{numero}_intro", 13 + (idx * 17)),
                    "strategie": RAPPageManager.get_page_position(f"programme_{numero}_strategie", 14 + (idx * 17)),
                    "realisations": RAPPageManager.get_page_position(f"programme_{numero}_realisations", 16 + (idx * 17)),
                    "performance": RAPPageManager.get_page_position(f"programme_{numero}_performance", 24 + (idx * 17)),
                    "conclusion": RAPPageManager.get_page_position(f"programme_{numero}_conclusion", 29 + (idx * 17))
                }
                
                # Ajouter PERSPECTIVES si disponible pour le programme 2
                if numero == 2:
                    pages["perspectives"] = RAPPageManager.get_page_position(f"programme_{numero}_perspectives", 47)
                
                # Titre de la partie
                partie_text = f"PARTIE {numero + 1} : LE PROGRAMME {numero} « {titre.upper()} »"
                toc_items.append({
                    "text": partie_text, 
                    "page": pages["start"], 
                    "level": 0, 
                    "bold": True
                })
                
                # Structure fixe pour chaque programme
                toc_items.append({
                    "text": "INTRODUCTION", 
                    "page": pages["intro"], 
                    "level": 1, 
                    "bold": False
                })
                toc_items.append({
                    "text": "I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", 
                    "page": pages["strategie"], 
                    "level": 1, 
                    "bold": False
                })
                toc_items.append({
                    "text": f"II. RÉALISATIONS DU PROGRAMME « {titre.upper()} » AU COURS DE L'EXERCICE {annee}", 
                    "page": pages["realisations"], 
                    "level": 1, 
                    "bold": False
                })
                toc_items.append({
                    "text": "III. PERFORMANCE DU PROGRAMME", 
                    "page": pages["performance"], 
                    "level": 1, 
                    "bold": False
                })
                
                # IV. PERSPECTIVES - seulement pour le programme 2
                if "perspectives" in pages:
                    toc_items.append({
                        "text": "IV. PERSPECTIVES", 
                        "page": pages["perspectives"], 
                        "level": 1, 
                        "bold": False
                    })
                
                toc_items.append({
                    "text": "CONCLUSION", 
                    "page": pages["conclusion"], 
                    "level": 1, 
                    "bold": False
                })
        
        logger.info(f"📋 Sommaire: {len(toc_items)} éléments construits")
        return toc_items


# ============================================================================
# GESTIONNAIRE DE TABLEAUX - CRÉATION ET FORMATAGE DES TABLEAUX
# ============================================================================

class RAPTableDrawer(RAPBaseGenerator):
    """
    Gestionnaire de création et formatage des tableaux pour le rapport.
    
    Responsabilités :
    - Création des tableaux d'investissement
    - Création des tableaux d'indicateurs de performance
    - Création des tableaux d'effectifs
    - Formatage et styling des tableaux
    
    Cette classe centralise toute la logique de création de tableaux complexes
    pour garantir la cohérence visuelle dans tout le rapport.
    """
    
    @staticmethod
    def create_investissement_table(
        projects: list[dict[str, Any]],
        available_width: float,
        format_fcfa: callable,
        annee: int,
        is_fake: bool = False,
        format_programme_value: callable = None
    ) -> LongTable:
        """
        Crée le tableau d'investissement avec la structure complexe (projets + sous-lignes).
        
        Ce tableau affiche les projets d'investissement avec leurs informations :
        - Nom du projet
        - Années de début et fin
        - Coûts (intérieur/extérieur)
        - Budgets votés et actuels par année
        - Ordonnancements
        
        Args:
            projects: Liste des projets d'investissement
            available_width: Largeur disponible pour le tableau
            format_fcfa: Fonction pour formater les montants en FCFA
            annee: Année courante
            is_fake: True si les données sont factices
            format_programme_value: Fonction pour formater les valeurs selon leur source
        
        Returns:
            LongTable configuré avec toutes les données et styles
        
        Note:
            Ce tableau utilise une structure complexe avec des sous-lignes
            pour afficher les détails par projet.
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 6789 - _create_investissement_table()
        """
        from reportlab.platypus import LongTable, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        
        logger.info(f"📊 Création du tableau d'investissement ({len(projects)} projets)...")
        
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
        
        # Calculer les largeurs des colonnes
        col_widths = [
            available_width * 0.35,  # Projets
            available_width * 0.10,  # Année démarrage
            available_width * 0.08,  # Année fin
            available_width * 0.12,  # Coût total
            available_width * 0.12,  # Budget Voté
            available_width * 0.12,  # Budget Actuel
            available_width * 0.11,  # Ordonnancement
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
            
            # Valeurs pour financement intérieur
            cout_interieur = project.get("cout_total_interieur", 0.0)
            budget_vote_interieur = project.get(f"budget_vote_{annee}_interieur", 0.0)
            budget_actuel_interieur = project.get(f"budget_actuel_{annee}_interieur", 0.0)
            ordonnancement_interieur = project.get(f"ordonnancement_{annee}_interieur", 0.0)
            
            # Valeurs pour financement extérieur
            cout_exterieur = project.get("cout_total_exterieur", 0.0)
            budget_vote_exterieur = project.get(f"budget_vote_{annee}_exterieur", 0.0)
            budget_actuel_exterieur = project.get(f"budget_actuel_{annee}_exterieur", 0.0)
            ordonnancement_exterieur = project.get(f"ordonnancement_{annee}_exterieur", 0.0)
            
            # Coûts totaux
            cout_total = cout_interieur + cout_exterieur
            budget_vote_total = budget_vote_interieur + budget_vote_exterieur
            budget_actuel_total = budget_actuel_interieur + budget_actuel_exterieur
            ordonnancement_total = ordonnancement_interieur + ordonnancement_exterieur
            
            # Formater les valeurs selon leur source
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
            
            # Ligne "Sur financement intérieur"
            table_data.append([
                Paragraph("Sur financement intérieur", cell_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_right_style),
                Paragraph("", cell_right_style),
                Paragraph(formatted_budget_actuel_interieur, cell_right_style),
                Paragraph(formatted_ordonnancement_interieur, cell_right_style),
            ])
            
            # Ligne "Sur financement extérieur"
            table_data.append([
                Paragraph("Sur financement extérieur", cell_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_center_style),
                Paragraph("", cell_right_style),
                Paragraph("", cell_right_style),
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
        
        # Formater les totaux
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
        
        # Ligne totale "Sur financement intérieur"
        table_data.append([
            Paragraph("<b>Total sur financement intérieur</b>", cell_style_bold),
            Paragraph("", cell_center_style),
            Paragraph("", cell_center_style),
            Paragraph("", cell_right_style),
            Paragraph("", cell_right_style),
            Paragraph(f"<b>{formatted_total_budget_actuel_interieur}</b>", cell_right_style),
            Paragraph(f"<b>{formatted_total_ordonnancement_interieur}</b>", cell_right_style),
        ])
        
        # Ligne totale "Sur financement extérieur"
        table_data.append([
            Paragraph("<b>Total sur financement extérieur</b>", cell_style_bold),
            Paragraph("", cell_center_style),
            Paragraph("", cell_center_style),
            Paragraph("", cell_right_style),
            Paragraph("", cell_right_style),
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
            
            # Alignement des montants
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
    def create_indicateurs_table(
        indicateurs_data: list[dict[str, Any]],
        available_width: float,
        annee: int,
        format_programme_value: callable = None
    ) -> LongTable:
        """
        Crée le tableau d'évolution des indicateurs de performance.
        
        Ce tableau affiche les indicateurs par Objectif Spécifique (OS) avec :
        - Les valeurs historiques (N-3, N-2, N-1, N)
        - Les prévisions et réalisations pour chaque année
        - La source des données
        
        Args:
            indicateurs_data: Liste des indicateurs avec leurs valeurs historiques
            available_width: Largeur disponible pour le tableau
            annee: Année courante (N)
            format_programme_value: Fonction pour formater les valeurs selon leur source
        
        Returns:
            LongTable configuré avec tous les indicateurs et leurs valeurs
        
        Note:
            Les indicateurs sont organisés par OS (Objectif Spécifique).
            Chaque OS n'est mentionné qu'une seule fois, suivi de tous ses indicateurs.
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 7402 - _create_indicateurs_table()
        """
        from reportlab.platypus import LongTable, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        
        logger.info(f"📊 Création du tableau d'indicateurs ({len(indicateurs_data)} indicateurs)...")
        
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
            # Déterminer si cet OS est factice
            premier_indicateur = indicateurs_os[0]
            data_source_os = premier_indicateur.get("_source", "default")
            is_os_fake = (data_source_os == "default")
            
            # Formater le titre de l'OS
            if format_programme_value:
                formatted_objectif_titre = format_programme_value(objectif_titre, is_os_fake)
            else:
                formatted_objectif_titre = objectif_titre
            
            # Ligne objectif - UNE SEULE FOIS par OS
            table_data.append([
                Paragraph(f"<b>{formatted_objectif_titre}</b>", cell_style_bold),
                Paragraph("", cell_center_style),
                Paragraph("", cell_right_style),
                Paragraph("", cell_right_style),
                Paragraph("", cell_right_style),
                Paragraph("", cell_right_style),
                Paragraph("", cell_right_style),
            ])
            
            # Afficher TOUS les indicateurs de cet OS à la suite
            for indicateur in indicateurs_os:
                indicateur_nom = indicateur["indicateur_nom"]
                unite = indicateur["unite"]
                
                # Déterminer si CETTE donnée est factice
                data_source = indicateur.get("_source", "default")
                is_this_indicateur_fake = (data_source == "default")
                
                # Récupérer les valeurs avec des clés dynamiques
                realisation_n_3 = indicateur.get(f"realisation_{annee_n_3}")
                realisation_n_2 = indicateur.get(f"realisation_{annee_n_2}")
                realisation_n_1 = indicateur.get(f"realisation_{annee_n_1}")
                prevision_n = indicateur.get(f"prevision_{annee_n}", 0)
                realisation_n = indicateur.get(f"realisation_{annee_n}", 0)
                
                # Formater chaque valeur selon sa source
                if format_programme_value:
                    formatted_indicateur_nom = format_programme_value(indicateur_nom, is_this_indicateur_fake)
                    formatted_unite = format_programme_value(unite, is_this_indicateur_fake)
                    r_n_3 = "-" if realisation_n_3 is None else format_programme_value(str(realisation_n_3), is_this_indicateur_fake)
                    r_n_2 = "-" if realisation_n_2 is None else format_programme_value(str(realisation_n_2), is_this_indicateur_fake)
                    r_n_1 = "-" if realisation_n_1 is None else format_programme_value(str(realisation_n_1), is_this_indicateur_fake)
                    formatted_prevision_n = format_programme_value(str(prevision_n), is_this_indicateur_fake)
                    formatted_realisation_n = format_programme_value(str(realisation_n), is_this_indicateur_fake)
                else:
                    formatted_indicateur_nom = indicateur_nom
                    formatted_unite = unite
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
        
        # Fusionner les cellules des lignes d'objectifs
        # Calculer les indices des lignes d'objectifs correctement
        row_index = 2  # Commence après les 2 lignes d'en-tête
        for objectif_titre, indicateurs_os in indicateurs_par_objectif.items():
            # Fusionner les colonnes 0 et 1 pour la ligne objectif
            indicateurs_table_style.add("SPAN", (0, row_index), (1, row_index))
            # Passer à la ligne suivante (objectif) après avoir traité tous les indicateurs
            row_index += len(indicateurs_os) + 1  # +1 pour la ligne objectif elle-même
        
        # Styles pour les lignes de données
        indicateurs_table_style.add("VALIGN", (0, 2), (-1, -1), "MIDDLE")
        indicateurs_table_style.add("ALIGN", (2, 2), (-1, -1), "RIGHT")  # Alignement droit pour les valeurs numériques
        
        indicateurs_table.setStyle(indicateurs_table_style)
        
        return indicateurs_table
    
    @staticmethod
    def create_effectifs_table(
        effectifs_data: list[dict[str, Any]],
        available_width: float,
        annee: int,
        is_fake: bool = False,
        format_programme_value: callable = None
    ) -> LongTable:
        """
        Crée le tableau d'évolution des effectifs par catégorie.
        
        Ce tableau affiche les effectifs pour les années N-1 et N par catégorie :
        - Titulaires
        - Contractuels
        - Stagiaires
        - Total
        
        Args:
            effectifs_data: Liste des effectifs par catégorie
            available_width: Largeur disponible pour le tableau
            annee: Année courante (N)
            is_fake: True si les données sont factices
            format_programme_value: Fonction pour formater les valeurs selon leur source
        
        Returns:
            LongTable configuré avec tous les effectifs
        
        Note:
            Les effectifs sont chargés depuis AgentComplet.
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 7750 - _create_effectifs_table()
        """
        from reportlab.platypus import LongTable, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        
        logger.info(f"📊 Création du tableau d'effectifs ({len(effectifs_data)} catégories)...")
        
        annee_precedente = annee - 1
        
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
                "",  # Colonne fusionnée
                "",  # Colonne fusionnée
                "",  # Colonne fusionnée
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
        
        # Calculer les largeurs des colonnes (7 colonnes)
        col_widths = [
            available_width * 0.22,  # Catégorie
            available_width * 0.12,  # Effectif (N-1)
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
        totals_are_fake = False
        
        # Parcourir les catégories
        for effectif in effectifs_data:
            categorie = effectif["categorie"]
            effectif_n_minus_1 = effectif.get(f"effectif_{annee_precedente}", 0)
            besoins_exprimes = effectif.get("besoins_exprimes", 0)
            previsions = effectif.get("previsions", 0)
            besoins_satisfaits = effectif.get("besoins_satisfaits", 0)
            sorties = effectif.get("sorties", 0)
            total_fin_annee = effectif_n_minus_1 + besoins_satisfaits - sorties
            
            # Déterminer si cette donnée est factice
            is_this_effectif_fake = effectif.get("_is_fake", False)
            if is_this_effectif_fake:
                totals_are_fake = True
            
            # Formater chaque valeur selon sa source
            formatted_categorie = format_programme_value(categorie, is_this_effectif_fake)
            formatted_effectif_n_minus_1 = format_programme_value(str(effectif_n_minus_1), is_this_effectif_fake)
            formatted_besoins_exprimes = format_programme_value(str(besoins_exprimes), is_this_effectif_fake)
            formatted_previsions = format_programme_value(str(previsions), is_this_effectif_fake)
            formatted_besoins_satisfaits = format_programme_value(str(besoins_satisfaits), is_this_effectif_fake)
            formatted_sorties = format_programme_value(str(sorties), is_this_effectif_fake)
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
        
        # Formater les totaux
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
            ("SPAN", (1, 0), (1, 1)),  # Effectif (N-1)
            ("SPAN", (2, 0), (5, 0)),  # Effectif (N) - fusionner les 4 colonnes
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
            
            # Alignement des montants
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


# ============================================================================
# GESTIONNAIRE DE GRAPHIQUES - GÉNÉRATION DES GRAPHIQUES
# ============================================================================

class RAPChartGenerator(RAPBaseGenerator):
    """
    Gestionnaire de génération des graphiques pour le rapport.
    
    Responsabilités :
    - Génération de graphiques en camembert (pie charts) pour les budgets
    - Génération de graphiques en barres (bar charts) pour les taux d'exécution
    - Génération de graphiques en barres pour les effectifs
    - Génération de graphiques en ligne pour l'évolution des indicateurs
    
    Cette classe utilise matplotlib pour générer tous les graphiques
    qui seront intégrés dans le PDF.
    """
    
    @staticmethod
    def create_pie_chart_budget(
        personnel: float,
        pct_personnel: float,
        biens: float,
        pct_biens: float,
        transferts: float,
        pct_transferts: float,
        investissements: float,
        pct_investissements: float,
        titre_ministere: str,
    ) -> BytesIO | None:
        """
        Crée un graphique en camembert pour la répartition du budget du ministère.
        
        Ce graphique affiche la répartition du budget par nature de dépenses :
        - Personnel (bleu clair)
        - Biens et services (orange)
        - Transferts (gris)
        - Investissements (jaune)
        
        Args:
            personnel: Montant pour le personnel
            pct_personnel: Pourcentage du personnel
            biens: Montant pour les biens et services
            pct_biens: Pourcentage des biens
            transferts: Montant pour les transferts
            pct_transferts: Pourcentage des transferts
            investissements: Montant pour les investissements
            pct_investissements: Pourcentage des investissements
            titre_ministere: Titre du ministère pour le graphique
        
        Returns:
            BytesIO contenant l'image PNG du graphique, ou None en cas d'erreur
        
        Note:
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 5771 - _create_pie_chart_budget()
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # Backend sans interface graphique
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from reportlab.lib.units import cm
            
            logger.info("📊 Création du graphique en camembert (budget ministère)...")
            
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
            fig_size = 20  # Taille grande pour avoir une bonne résolution
            fig = plt.figure(figsize=(fig_size, fig_size), dpi=200)  # DPI élevé pour meilleure qualité
            ax = fig.add_subplot(111, aspect='equal')  # Force un ratio d'aspect égal pour un cercle parfait
            
            # Créer le graphique en camembert avec des textes plus grands
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=None,  # On mettra la légende à part
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
            legend_font = fm.FontProperties(weight='bold', size=36)
            legend = ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.1, 0.5), prop=legend_font, frameon=True)
            # S'assurer que la légende utilise bien la taille de police spécifiée
            for text in legend.get_texts():
                text.set_fontsize(36)
                text.set_weight('bold')
            
            # Ajuster la mise en page pour agrandir le graphique (réduire les marges)
            plt.subplots_adjust(left=0.05, right=0.55, top=0.95, bottom=0.05)
            
            # Sauvegarder dans un buffer avec un ratio d'aspect égal
            buffer = BytesIO()
            # Fond transparent
            plt.savefig(buffer, format='png', dpi=200, facecolor='white', edgecolor='none', bbox_inches='tight', transparent=True)
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
    def create_pie_chart_programme(
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
        Crée un graphique en camembert pour la répartition du budget d'un programme.
        
        Structure identique au graphique du ministère mais pour un programme spécifique.
        
        Args:
            personnel: Montant pour le personnel
            pct_personnel: Pourcentage du personnel
            biens: Montant pour les biens et services
            pct_biens: Pourcentage des biens
            transferts: Montant pour les transferts
            pct_transferts: Pourcentage des transferts
            investissements: Montant pour les investissements
            pct_investissements: Pourcentage des investissements
            titre_programme: Titre du programme
        
        Returns:
            BytesIO contenant l'image PNG du graphique, ou None en cas d'erreur
        
        Note:
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 6347 - _create_pie_chart_programme()
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # Backend sans interface graphique
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            import matplotlib.font_manager as fm
            
            logger.info(f"📊 Création du graphique en camembert (budget programme: {titre_programme[:30]}...)")
            
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
            
            # Ajuster la mise en page
            plt.subplots_adjust(left=0.05, right=0.55, top=0.95, bottom=0.05)
            
            # Sauvegarder dans un buffer avec un ratio d'aspect égal
            buffer = BytesIO()
            # Fond transparent
            plt.savefig(buffer, format='png', dpi=200, facecolor='white', edgecolor='none', bbox_inches='tight', transparent=True)
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
    def create_bar_chart_execution_rates(
        bar_chart_data: dict[str, dict[str, float]],
        annee_precedente: int,
        annee: int,
    ) -> BytesIO | None:
        """
        Crée un graphique en barres pour l'évolution des taux d'exécution par action.
        
        Ce graphique affiche les taux d'exécution pour chaque action sur deux années :
        - Année N-1 (barres d'une couleur)
        - Année N (barres d'une autre couleur)
        
        Args:
            bar_chart_data: Dictionnaire {nom_action: {rate_n_minus_1: float, rate_n: float}}
            annee_precedente: Année N-1
            annee: Année courante (N)
        
        Returns:
            BytesIO contenant l'image PNG du graphique, ou None en cas d'erreur
        
        Note:
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 6437 - _create_bar_chart_execution_rates()
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # Backend sans interface graphique
            import matplotlib.pyplot as plt
            import numpy as np
            
            logger.info(f"📊 Création du graphique en barres (taux d'exécution, {len(bar_chart_data)} actions)...")
            
            # Préparer les données pour le graphique
            actions_labels = []
            rates_n_minus_1 = []
            rates_n = []
            
            action_num = 1
            for action, rates in bar_chart_data.items():
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
            fig, ax = plt.subplots(figsize=(20, 6), dpi=200)
            
            # Position des barres
            x = np.arange(len(actions_labels))
            width = 0.35  # Largeur des barres
            
            # Créer les barres avec les couleurs spécifiées
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
    def create_bar_chart_effectifs(
        effectifs_data: list[dict[str, Any]],
        annee_precedente: int,
        annee: int,
        numero_programme: int,
        titre_programme: str,
    ) -> BytesIO | None:
        """
        Crée un graphique en barres pour l'évolution des effectifs par catégorie.
        
        Ce graphique affiche les effectifs par catégorie sur deux années :
        - Année N-1 (barres d'une couleur)
        - Année N (barres d'une autre couleur)
        
        Args:
            effectifs_data: Liste des effectifs par catégorie
            annee_precedente: Année N-1
            annee: Année courante (N)
            numero_programme: Numéro du programme
            titre_programme: Titre du programme
        
        Returns:
            BytesIO contenant l'image PNG du graphique, ou None en cas d'erreur
        
        Note:
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 7977 - _create_bar_chart_effectifs()
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # Backend sans interface graphique
            import matplotlib.pyplot as plt
            import numpy as np
            
            logger.info(f"📊 Création du graphique en barres (effectifs, programme {numero_programme})...")
            
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
            max_effectif = max(max(effectifs_n_minus_1), max(effectifs_n)) if effectifs_n_minus_1 and effectifs_n else 100
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
    
    @staticmethod
    def create_indicateur_evolution_chart(
        indicateur_nom: str,
        annee_n_3: int,
        annee_n_2: int,
        annee_n_1: int,
        annee: int,
        valeur_n_3: float | None,
        valeur_n_2: float | None,
        valeur_n_1: float | None,
        valeur_n: float | None,
        cible: float | None,
    ) -> BytesIO | None:
        """
        Crée un graphique en ligne pour l'évolution d'un indicateur sur les 4 derniers exercices.
        
        Ce graphique affiche :
        - L'évolution des valeurs réelles (N-3 à N)
        - La ligne de cible (si disponible)
        - L'échelle fixe de 0 à 100%
        
        Args:
            indicateur_nom: Nom de l'indicateur
            annee_n_3: Année N-3
            annee_n_2: Année N-2
            annee_n_1: Année N-1
            annee: Année courante (N)
            valeur_n_3: Valeur pour N-3 (peut être None)
            valeur_n_2: Valeur pour N-2 (peut être None)
            valeur_n_1: Valeur pour N-1 (peut être None)
            valeur_n: Valeur pour N (peut être None)
            cible: Valeur cible (peut être None)
        
        Returns:
            BytesIO contenant l'image PNG du graphique, ou None en cas d'erreur
        
        Note:
            L'échelle est fixe de 0 à 100% pour tous les indicateurs.
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 6540 - _create_indicateur_evolution_chart()
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # Backend sans interface graphique
            import matplotlib.pyplot as plt
            import numpy as np
            
            logger.info(f"📊 Création du graphique d'évolution (indicateur: {indicateur_nom[:30]}...)")
            
            # Construire la liste des années et valeurs
            annees = [annee_n_3, annee_n_2, annee_n_1, annee]
            valeurs_list = [valeur_n_3, valeur_n_2, valeur_n_1, valeur_n]
            
            # Filtrer les valeurs None et construire des listes parallèles
            annees_filtered = []
            valeurs_filtered = []
            for a, v in zip(annees, valeurs_list):
                if v is not None:
                    annees_filtered.append(a)
                    valeurs_filtered.append(float(v))
            
            # Si aucune valeur n'est disponible, ne pas générer le graphique
            if not valeurs_filtered:
                logger.warning(f"⚠️ Aucune valeur disponible pour l'indicateur '{indicateur_nom}'")
                return None
            
            # Créer la figure
            fig, ax = plt.subplots(figsize=(16, 6), dpi=200)
            
            # Créer le graphique en ligne
            line = ax.plot(annees_filtered, valeurs_filtered, marker='o', linewidth=3, markersize=10, color='#5b9bd5', label='Valeur')
            
            # Ajouter les valeurs sur les points
            for annee_val, valeur in zip(annees_filtered, valeurs_filtered):
                ax.text(annee_val, valeur, f'{valeur:.1f}',
                       ha='center', va='bottom', fontsize=20, fontweight='bold')
            
            # Ajouter la ligne de cible si disponible
            if cible is not None:
                ax.axhline(y=cible, color='red', linestyle='--', linewidth=2, label=f'Cible ({cible:.1f})')
            
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
            
            # Légende
            if cible is not None:
                ax.legend(loc='best', fontsize=16, frameon=True)
            
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


# ============================================================================
# GESTIONNAIRE DE SECTIONS PROGRAMME - SECTIONS PAR PROGRAMME
# ============================================================================

class RAPProgramSectionDrawer(RAPBaseGenerator):
    """
    Gestionnaire de génération des sections par programme.
    
    Responsabilités :
    - Génération complète de la partie d'un programme
    - Dessin de l'introduction du programme
    - Dessin des sections I, II, III, IV (si applicable)
    - Gestion des tableaux et graphiques par programme
    - Conclusion du programme
    
    Cette classe est l'une des plus volumineuses car chaque programme
    a une structure complexe avec de nombreuses sous-sections, tableaux et graphiques.
    """
    
    @classmethod
    def draw_partie_programme(
        cls,
        programme: dict[str, Any],
        start_page: int,
        session=None
    ) -> tuple[BytesIO, int]:
        """
        Génère la partie complète d'un programme avec SimpleDocTemplate.
        
        Cette méthode génère toutes les sections d'un programme :
        1. INTRODUCTION du programme
        2. I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME
           - Tableau 4 : Exécution financière par action
           - Figure 2 : Répartition du budget (camembert)
           - Figure 3 : Evolution des taux d'exécution (barres)
           - Tableau 5 : Suivi des investissements
        3. II. RÉALISATIONS DU PROGRAMME
           - Activités majeures
        4. III. PERFORMANCE DU PROGRAMME
           - Tableau 6 : Exécution des prévisions d'effectifs
           - Figure 4 : Evolution des effectifs (barres)
           - Tableau 7 : Évolution des indicateurs
           - Graphiques d'évolution des indicateurs
        5. IV. PERSPECTIVES (si programme 2)
        6. CONCLUSION du programme
        
        Args:
            programme: Dictionnaire contenant les données du programme
            start_page: Numéro de page de début
            session: Session de base de données (optionnel)
        
        Returns:
            Tuple (buffer du PDF temporaire, numéro de la dernière page + 1)
        
        Note:
            Cette méthode utilise SimpleDocTemplate pour gérer le découpage automatique.
            Les tableaux sont numérotés de manière continue dans tout le rapport.
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 8073 - _draw_partie_programme_simpledoc()
        """
        numero = programme.get("numero", 1)
        titre = programme.get("titre", "")
        logger.info(f"📄 Génération partie programme {numero} « {titre} » (page {start_page})...")
        
        # Calculer le numéro romain de la partie (utilisé plus tard)
        partie_numero_romain = RAPBaseGenerator.number_to_roman(numero + 1)
        
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
            is_programme_fake = RAPBaseGenerator.should_use_fake_data()
        
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
                return RAPStylingManager.format_fake_data(str(value))
            else:
                return RAPStylingManager.format_db_data(str(value))
        
        # Titre de la partie (formaté après la définition de format_programme_value)
        formatted_numero_partie = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_partie = format_programme_value(titre.upper(), is_programme_fake)
        # Enregistrer la page AVANT le titre pour garantir que la page enregistrée est celle où le titre commence
        story.append(PageMarker(f"programme_{numero}_start"))
        story.append(Paragraph(f"PARTIE {partie_numero_romain} : LE PROGRAMME {formatted_numero_partie} « {formatted_titre_partie} »", partie_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Section INTRODUCTION
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        # Enregistrer la page AVANT le titre (après CondPageBreak)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        story.append(PageMarker(f"programme_{numero}_intro"))
        story.append(Paragraph("INTRODUCTION", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Paragraphe 1 : Responsable du programme (toujours affiché si responsable_nom fourni)
        if responsable_nom and responsable_nom != "NC":
            # Toutes les données sont DB (rouge)
            formatted_nom = RAPStylingManager.format_db_data(responsable_nom)
            formatted_fonction = RAPStylingManager.format_db_data(responsable_fonction) if responsable_fonction != "NC" else RAPStylingManager.format_db_data("Responsable de Programme")
            formatted_nomination = RAPStylingManager.format_db_data(decret_nomination) if decret_nomination != "NC" else RAPStylingManager.format_db_data("décret")
            formatted_designation = RAPStylingManager.format_db_data(decret_designation) if decret_designation != "NC" else RAPStylingManager.format_db_data("le décret")
            formatted_titre = RAPStylingManager.format_db_data(titre)
            
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
        is_decret_fake = (not decret_org_num or not decret_org_date) and RAPBaseGenerator.should_use_fake_data()
        
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
        is_missions_fake = (not missions or len(missions) == 0) and RAPBaseGenerator.should_use_fake_data()
        
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
            formatted_contexte = RAPStylingManager.format_db_data(contexte)
            story.append(Paragraph(formatted_contexte, body_style))
            story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 4 : Structure du rapport avec liste à puces (toujours affiché)
        # Déterminer si structure_rapport est factice (si vide et mode brouillon)
        is_structure_fake = (not structure_rapport or len(structure_rapport) == 0) and RAPBaseGenerator.should_use_fake_data()
        
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
        # Enregistrer la page AVANT le titre (après CondPageBreak)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        story.append(PageMarker(f"programme_{numero}_strategie"))
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
        is_objectif_fake = (objectif_global_num == "NC" or objectif_global_libelle == "Non communiqué") and RAPBaseGenerator.should_use_fake_data()
        is_resultat_fake = (resultat_strategique_num == "NC" or resultat_strategique_libelle == "Non communiqué") and RAPBaseGenerator.should_use_fake_data()
        
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
        is_budget_fake = is_budget_empty and RAPBaseGenerator.should_use_fake_data()
        
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
                formatted_explication = RAPStylingManager.format_db_data(analyse_explication_user)
            else:
                # Données par défaut (rouge)
                analyse_explication_default = (
                    f"L'augmentation notable du budget alloué à ce programme s'explique par plusieurs facteurs, "
                    f"notamment les ajustements opérés en cours d'exercice et les rattachements de structures ou projets."
                )
                formatted_explication = RAPStylingManager.format_db_data(analyse_explication_default)
            story.append(Paragraph(formatted_explication, body_style))
            story.append(Spacer(1, 0.08 * cm))
        
        # Paragraphe 4 : Introduction de la liste
        analyse_intro_liste_user = programme_data.get("analyse_intro_liste", "")
        if analyse_intro_liste_user:
            # Données utilisateur (rouge car personnalisées)
            formatted_intro_liste = RAPStylingManager.format_db_data(analyse_intro_liste_user)
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
            formatted_analyse_note = RAPStylingManager.format_db_data(analyse_note)
            story.append(Paragraph(f"<b>NB :</b> {formatted_analyse_note}", body_style))
            story.append(Spacer(1, 0.1 * cm))
        
        # Interprétation du financement du programme
        financement_interpretation = programme_data.get("financement_interpretation", "")
        
        if financement_interpretation:
            # Données utilisateur (formatées en rouge car DB)
            formatted_interpretation = RAPStylingManager.format_db_data(financement_interpretation)
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
            formatted_financement_note = RAPStylingManager.format_db_data(financement_note)
            story.append(Paragraph(f"<b>NB :</b> {formatted_financement_note}", body_style))
            story.append(Spacer(1, 0.2 * cm))
        else:
            # Si pas de note, ne rien afficher pour le NB
            pass
        
        # ============================================================
        # II. REALISATIONS DU PROGRAMME
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        # Enregistrer la page AVANT le titre (après CondPageBreak)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        story.append(PageMarker(f"programme_{numero}_realisations"))
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
            pie_chart_buffer = RAPChartGenerator.create_pie_chart_programme(
                prog_personnel_budget_actuel, pct_personnel,
                prog_biens_budget_actuel, pct_biens,
                prog_transferts_budget_actuel, pct_transferts,
                prog_investissements_budget_actuel, pct_investissements,
                titre
            )
        
        if pie_chart_buffer:
            # Titre du graphique (même format que pour le ministère)
            story.append(Spacer(1, 0.3 * cm))
            figure_numero = RAPBaseGenerator.get_next_figure_numero()
            formatted_numero_fig = format_programme_value(str(numero), is_programme_fake)
            formatted_titre_fig = format_programme_value(titre, is_programme_fake)
            story.append(Paragraph(f"<b>Figure {figure_numero}: Répartition du budget actuel du Programme {formatted_numero_fig} « {formatted_titre_fig} » par nature de dépenses</b>", subsection_title_style))
            story.append(Spacer(1, 0.2 * cm))
            
            # Créer la source
            source_text = f"Source: DAAF {RAPStylingManager.get_sigle_ministere()}/ Situation d'exécution issue du SIGOBE"
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
                    
                    # Dessiner le graphique
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
        if (not actions_tableau4 or len(actions_tableau4) == 0) and RAPBaseGenerator.should_use_fake_data():
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
                    # Extraire le texte de l'action sans le préfixe "Action X :" s'il existe
                    action_text = action
                    # Supprimer le préfixe "Action X :" ou "Action X:" (avec ou sans espace après les deux points)
                    action_text = re.sub(r'^Action\s+\d+\s*:\s*', '', action_text, flags=re.IGNORECASE)
                    formatted_action = format_programme_value(action_text, is_actions_fake)
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
                    # Extraire le texte de l'action sans le préfixe "Action X :" s'il existe
                    action_text = action
                    # Supprimer le préfixe "Action X :" ou "Action X:" (avec ou sans espace après les deux points)
                    action_text = re.sub(r'^Action\s+\d+\s*:\s*', '', action_text, flags=re.IGNORECASE)
                    formatted_action = format_programme_value(action_text, is_actions_fake)
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
        if (not actions_data or len(actions_data) == 0) and RAPBaseGenerator.should_use_fake_data() and actions_tableau4:
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
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        tableau_titre = f"Tableau {tableau_numero}: Exécution financière par action du programme {formatted_numero} « {formatted_titre_tableau} »"
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
                formatted_interpretation = RAPStylingManager.format_db_data(interpretation_text)
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
        bar_chart_buffer = RAPChartGenerator.create_bar_chart_execution_rates(
            bar_chart_data,
            annee_precedente,
            annee,
        )
        
        if bar_chart_buffer:
            story.append(Spacer(1, 0.3 * cm))
            
            # Titre du graphique
            figure_numero = RAPBaseGenerator.get_next_figure_numero()
            formatted_numero_fig3 = format_programme_value(str(numero), is_programme_fake)
            formatted_titre_fig3 = format_programme_value(titre, is_programme_fake)
            story.append(Paragraph(f"<b>Figure {figure_numero}: Evolution des taux d'exécution par action du Programme {formatted_numero_fig3} « {formatted_titre_fig3} »</b>", subsection_title_style))
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
        investissement_data = RAPDataLoader.get_investissement_data(numero, titre, annee, session)
        
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
            if not is_investissement_data_fake and RAPBaseGenerator.should_use_fake_data():
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
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        story.append(Paragraph(f"<b>Tableau {tableau_numero}: Suivi des investissements du Programme {formatted_numero_tab5} « {formatted_titre_tab5} »</b>", body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Tableau (conditionné - afficher un message si vide)
        if not investissement_data:
            message_no_data = (
                "Aucune donnée d'investissement n'est disponible pour ce programme dans la base de données."
            )
            story.append(Paragraph(message_no_data, body_style))
        else:
            # Créer le tableau d'investissement avec formatage selon la source
            investissement_table = RAPTableDrawer.create_investissement_table(investissement_data, available_width, format_fcfa, annee, is_investissement_data_fake, format_programme_value)
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
        effectifs_data = RAPDataLoader.get_effectifs_data(numero, titre, annee, session)
        
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
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        story.append(Paragraph(f"<b>Tableau {tableau_numero}: Exécution des prévisions d'effectifs du programme {formatted_numero_tab6} « {formatted_titre_tab6} »</b>", body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Tableau (conditionné - afficher un message si vide)
        if not effectifs_data:
            message_no_data_effectifs = (
                "Aucune donnée d'effectifs n'est disponible pour ce programme dans la base de données."
            )
            story.append(Paragraph(message_no_data_effectifs, body_style))
        else:
            # Créer le tableau d'effectifs avec formatage selon la source
            effectifs_table = RAPTableDrawer.create_effectifs_table(effectifs_data, available_width, annee, is_effectifs_data_fake, format_programme_value)
            story.append(effectifs_table)
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Source du tableau (toujours affichée)
        formatted_annee_source_cabinet = format_programme_value(str(annee_precedente), False)  # Année toujours DB
        story.append(Paragraph(f"Source: Cabinet {RAPStylingManager.get_sigle_ministere()} / DAAF / Catalogue des mesures nouvelles / RAP {formatted_annee_source_cabinet}", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # Graphique : Evolution des effectifs par catégorie
        # ============================================================
        
        # Titre du graphique (toujours affiché)
        figure_numero = RAPBaseGenerator.get_next_figure_numero()
        formatted_numero_fig4 = format_programme_value(str(numero), is_programme_fake)
        formatted_titre_fig4 = format_programme_value(titre, is_programme_fake)
        story.append(Paragraph(f"<b>Figure {figure_numero}: Evolution des effectifs du Programme {formatted_numero_fig4} « {formatted_titre_fig4} » par catégorie</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Générer le graphique en barres (conditionné)
        effectifs_chart_buffer = None
        if effectifs_data:
            effectifs_chart_buffer = RAPChartGenerator.create_bar_chart_effectifs(
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
        activites_majeures = RAPDataLoader.get_activites_majeures(numero, titre, annee, session)
        
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
            formatted_conclusion = RAPStylingManager.format_db_data(bilan_conclusion)
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
        # Enregistrer la page AVANT le titre (après CondPageBreak)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        story.append(PageMarker(f"programme_{numero}_performance"))
        story.append(Paragraph("III. PERFORMANCE DU PROGRAMME", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # ============================================================
        # III.1. Présentation de l'évolution des indicateurs de performance du programme
        # ============================================================
        story.append(Paragraph("III.1. Présentation de l'évolution des indicateurs de performance du programme", subsection_title_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Récupérer les données d'indicateurs AVANT de les utiliser dans l'introduction
        indicateurs_data = RAPDataLoader.get_indicateurs_performance_data(numero, titre, annee, session)
        
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
        tableau_numero = RAPBaseGenerator.get_next_tableau_numero()
        story.append(Paragraph(f"<b>Tableau {tableau_numero}: Évolution des indicateurs du programme {formatted_numero_tab7} « {formatted_titre_tab7} »</b>", body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Tableau (conditionné - afficher un message si vide)
        if not indicateurs_data:
            message_no_data_indicateurs = (
                "Aucune donnée d'indicateurs de performance n'est disponible pour ce programme dans la base de données."
            )
            story.append(Paragraph(message_no_data_indicateurs, body_style))
        else:
            # Créer le tableau d'indicateurs avec formatage selon la source
            indicateurs_table = RAPTableDrawer.create_indicateurs_table(indicateurs_data, available_width, annee, format_programme_value)
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
        sigle_ministere = RAPStylingManager.get_sigle_ministere()
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
                    formatted_objectif_titre = RAPStylingManager.format_fake_data(objectif_titre)
                    formatted_indicateur_nom = RAPStylingManager.format_fake_data(indicateur_nom)
                    formatted_indicateur_num = RAPStylingManager.format_fake_data(str(indicateur_num))
                else:
                    formatted_objectif_titre = RAPStylingManager.format_db_data(objectif_titre)
                    formatted_indicateur_nom = RAPStylingManager.format_db_data(indicateur_nom)
                    formatted_indicateur_num = RAPStylingManager.format_db_data(str(indicateur_num))
                
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
                valeur_n_3 = indicateur.get(f"realisation_{annee_n_3}", None)
                valeur_n_2 = indicateur.get(f"realisation_{annee_n_2}", None)
                valeur_n_1 = indicateur.get(f"realisation_{annee_n_1}", None)
                valeur_n = indicateur.get(f"realisation_{annee}", None)
                
                # Récupérer la cible si disponible
                cible = indicateur.get("cible", None)
                
                # Créer le graphique d'évolution (toujours générer, même avec des données de test)
                logger.info(f"📊 Génération du graphique d'évolution pour l'indicateur '{indicateur_nom}' (année {annee}, valeurs: N-3={valeur_n_3}, N-2={valeur_n_2}, N-1={valeur_n_1}, N={valeur_n})")
                evolution_chart_buffer = RAPChartGenerator.create_indicateur_evolution_chart(
                    indicateur_nom=indicateur_nom,
                    annee_n_3=annee_n_3,
                    annee_n_2=annee_n_2,
                    annee_n_1=annee_n_1,
                    annee=annee,
                    valeur_n_3=valeur_n_3,
                    valeur_n_2=valeur_n_2,
                    valeur_n_1=valeur_n_1,
                    valeur_n=valeur_n,
                    cible=cible
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
                    formatted_indicateur_num_fig = RAPStylingManager.format_db_data(str(indicateur_num))
                    formatted_indicateur_nom_fig = format_programme_value(indicateur_nom, is_fig_data_fake)
                    formatted_annee_n_3_fig = RAPStylingManager.format_db_data(str(annee_n_3))
                    formatted_annee_fig = RAPStylingManager.format_db_data(str(annee))
                    
                    figure_numero = RAPBaseGenerator.get_next_figure_numero()
                    figure_title_text = f"Figure {figure_numero}: Evolution de l'indicateur {formatted_indicateur_num_fig} « {formatted_indicateur_nom_fig} » de {formatted_annee_n_3_fig} à {formatted_annee_fig}"
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
                        return RAPStylingManager.format_fake_data(str(value))
                    else:
                        return RAPStylingManager.format_db_data(str(value))
                
                if analyse_text:
                    # Utiliser l'analyse complète fournie par l'utilisateur (données utilisateur = rouge en brouillon)
                    formatted_analyse = RAPStylingManager.format_db_data(analyse_text)
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
                    story.append(Paragraph(RAPStylingManager.format_db_data("Votre analyse complémentaire sur cet indicateur ici."), indicateur_subitem_style))
                
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
        # Enregistrer la page AVANT le titre (après CondPageBreak)
        # Si CondPageBreak force une nouvelle page, le marqueur enregistrera cette nouvelle page
        story.append(PageMarker(f"programme_{numero}_conclusion"))
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
            
            # Mettre à jour la variable de classe pour que les PageMarker puissent l'utiliser
            cls._current_rendering_page = page_counter
            # Stocker aussi dans le canvas pour que les marqueurs puissent y accéder
            canv._pageNumber = page_counter - 1  # 0-indexé pour ReportLab
            
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
        
        # Réinitialiser la variable de classe après le build
        RAPBaseGenerator._current_rendering_page = None
        
        temp_buffer.seek(0)
        
        # Compter le nombre de pages générées
        temp_reader = PdfReader(temp_buffer)
        num_pages = len(temp_reader.pages)
        final_page = start_page + num_pages - 1
        
        temp_buffer.seek(0)
        logger.info(f"✅ Partie programme générée : {num_pages} pages (de {start_page} à {final_page})")
        
        return temp_buffer, final_page


# ============================================================================
# ORCHESTRATEUR PRINCIPAL - GÉNÉRATION COMPLÈTE DU PDF
# ============================================================================

class RAPPDFGenerator(RAPBaseGenerator):
    """
    Classe principale pour la génération du rapport annuel de performance.
    
    Cette classe hérite de RAPBaseGenerator et orchestre la génération complète
    du PDF en utilisant toutes les classes spécialisées via leurs méthodes de classe.
    
    Note: Toutes les autres classes (RAPPageManager, RAPStylingManager, etc.) héritent
    également de RAPBaseGenerator. Pour éviter les conflits MRO, RAPPDFGenerator
    n'hérite que de RAPBaseGenerator et appelle les méthodes des autres classes
    directement via leurs noms de classe (méthodes @classmethod).
    """
    
    # Valeurs par défaut pour la compatibilité avec l'ancien code
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
            {"numero": 1, "titre": "Répartition du budget actuel du Ministère par natures de dépenses", "page": 12},
            {"numero": 2, "titre": "Répartition du budget du programme 1 par natures de dépenses", "page": 17},
            {"numero": 3, "titre": "Evolution des taux d'exécution par action du Programme 1 « ADMINISTRATION GÉNÉRALE »", "page": 18},
            {"numero": 4, "titre": "Evolution des effectifs du Programme 1 « ADMINISTRATION GÉNÉRALE » par catégorie", "page": 22},
            {"numero": 5, "titre": "Evolution de l'indicateur 1 du programme 1", "page": 25},
            {"numero": 6, "titre": "Evolution de l'indicateur 2 du programme 1", "page": 26},
            {"numero": 7, "titre": "Evolution de l'indicateur 3 du programme 1", "page": 27},
            {"numero": 8, "titre": "Evolution de l'indicateur 4 du programme 1", "page": 28},
            {"numero": 9, "titre": "Répartition du budget du programme 2 par natures de dépenses", "page": 33},
            {"numero": 10, "titre": "Evolution des taux d'exécution par action du Programme 2 « PORTEFEUILLE DE L'ÉTAT »", "page": 34},
            {"numero": 11, "titre": "Evolution des effectifs du Programme 2 « PORTEFEUILLE DE L'ÉTAT » par catégorie", "page": 36},
            {"numero": 12, "titre": "Evolution de l'indicateur 1 du programme 2", "page": 39},
            {"numero": 13, "titre": "Evolution de l'indicateur 2 du programme 2", "page": 40},
            {"numero": 14, "titre": "Evolution de l'indicateur 3 du programme 2", "page": 41},
            {"numero": 15, "titre": "Evolution de l'indicateur 4 du programme 2", "page": 42},
        ],
    }
    
    @classmethod
    def generate_pdf(cls, data: dict[str, Any], session=None) -> BytesIO:
        """
        Génère le PDF complet du rapport annuel de performance.
        
        Cette méthode orchestre toute la génération du rapport en utilisant
        toutes les classes spécialisées héritées.
        
        Args:
            data: Dictionnaire contenant les données du formulaire (optionnel)
            session: Session de base de données (optionnel)
        
        Returns:
            BytesIO contenant le PDF complet du rapport
        
        Processus de génération :
        1. **Initialisation** : Réinitialise tous les compteurs et variables
        2. **Chargement des données** : Charge depuis SystemSettings et RapData (via RAPDataLoader)
        3. **Fusion des données** : Fusionne DB + données formulaire
        4. **Génération couverture** : Page de couverture (via RAPLayoutDrawer)
        5. **Génération contenu** : Listes, introduction, partie I (via RAPContentDrawer)
        6. **Génération programmes** : Partie par programme (via RAPProgramSectionDrawer)
        7. **Génération conclusion** : Conclusion générale (via RAPContentDrawer)
        8. **Fusion PDFs** : Fusionne toutes les parties
        9. **Génération sommaire** : Table des matières avec les vraies pages (via RAPPageManager)
        10. **Retour** : PDF final complet
        
        Note:
            Cette méthode est la méthode principale appelée depuis l'API.
            L'implémentation complète sera migrée depuis rapport_annuel_performance_service_simpledoc.py
            ligne 12665 - generate_pdf()
        """
        logger.info("🚀 DÉBUT génération PDF rapport annuel de performance (Modulaire)")
        
        # Initialiser la session de base de données
        RAPBaseGenerator._db_session = session
        RAPBaseGenerator._db_data_keys = set()  # Réinitialiser les clés DB
        RAPPageManager._page_positions = {}  # Réinitialiser les positions des pages
        RAPBaseGenerator._current_rendering_page = None  # Réinitialiser la page de rendu actuelle
        RAPBaseGenerator.reset_tableau_counter(1)  # Initialiser le compteur de tableaux à 1 pour une numérotation continue
        logger.info(f"📊 Compteur de tableaux initialisé à 1")
        RAPBaseGenerator.reset_figure_counter(1)  # Initialiser le compteur de figures à 1 pour une numérotation continue
        logger.info(f"📊 Compteur de figures initialisé à 1")
        
        # Charger les données depuis la base de données (SystemSettings et RapData)
        db_data = RAPDataLoader.load_system_settings_data(session)
        logger.info(f"📊 Données DB chargées: {list(db_data.keys())}")
        if "introduction" in db_data:
            logger.info(f"📊 Données d'introduction dans db_data: {list(db_data['introduction'].keys())}")
        
        # Fusionner les données : DB < données du formulaire
        # NE PAS utiliser DEFAULT_DATA pour éviter les valeurs factices
        user_data = data or {}
        
        # Fusionner d'abord les données de premier niveau
        RAPBaseGenerator.data = {**db_data, **user_data}
        
        # Fusionner aussi les données d'introduction si présentes (priorité DB)
        if "introduction" in db_data:
            if "introduction" not in RAPBaseGenerator.data:
                RAPBaseGenerator.data["introduction"] = {}
            # Fusionner : d'abord user_data["introduction"] (si existe), puis db_data["introduction"] (priorité)
            user_intro = user_data.get("introduction", {})
            RAPBaseGenerator.data["introduction"] = {
                **user_intro,  # D'abord les données utilisateur
                **db_data["introduction"]  # Puis les données DB (écrasent les données utilisateur)
            }
            logger.info(f"✅ Données d'introduction fusionnées: {list(RAPBaseGenerator.data.get('introduction', {}).keys())}")
            logger.info(f"✅ Exemples de valeurs: ministre_nom={RAPBaseGenerator.data['introduction'].get('ministre_nom', 'N/A')[:50]}, mission={RAPBaseGenerator.data['introduction'].get('mission_ministere', 'N/A')[:50]}")
        else:
            logger.warning("⚠️ Aucune donnée d'introduction trouvée dans db_data")
        
        logger.info(f"📊 Données finales dans RAPBaseGenerator.data: ministere={RAPBaseGenerator.data.get('ministere', 'N/A')[:50]}, logo_path={RAPBaseGenerator.data.get('logo_path', 'N/A')}")
        logger.info(f"📊 RAPBaseGenerator.data['introduction'] existe: {'introduction' in RAPBaseGenerator.data}")
        if "introduction" in RAPBaseGenerator.data:
            logger.info(f"📊 Contenu de RAPBaseGenerator.data['introduction']: {list(RAPBaseGenerator.data['introduction'].keys())}")
        
        # Utiliser l'année en cours si aucune année n'est fournie
        from datetime import datetime
        annee = RAPBaseGenerator.data.get("annee")
        
        if not annee or annee == 0:
            annee = datetime.now().year
            RAPBaseGenerator.data["annee"] = annee
            logger.info(f"📅 Aucune année fournie, utilisation de l'année en cours: {annee}")
        
        # Charger les données budgétaires si une session est fournie
        budget_data = RAPDataLoader.load_budget_data(session, annee)
        
        # Fusionner les données budgétaires (code copié du service original)
        if budget_data:
            # Mettre à jour les programmes si disponibles
            if "programmes" in budget_data and budget_data["programmes"]:
                RAPBaseGenerator.data["programmes"] = budget_data["programmes"]
            
            # Mettre à jour partie_ministere avec les données réelles depuis la DB
            if "partie_ministere" not in RAPBaseGenerator.data:
                RAPBaseGenerator.data["partie_ministere"] = {}
            
            partie_ministere = RAPBaseGenerator.data["partie_ministere"]
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
            
            RAPBaseGenerator.data["partie_ministere"] = partie_ministere
        
        # Définir les dimensions de la page
        page_width, page_height = landscape(A4)
        
        # Réinitialiser les positions de pages
        RAPPageManager._page_positions = {}
        
        # Pour la couverture, on utilise Canvas directement
        cover_buffer = BytesIO()
        cover_pdf = canvas.Canvas(cover_buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        logger.info("📄 Page 1: Couverture")
        RAPLayoutDrawer.draw_background_shapes(cover_pdf, width, height)
        RAPLayoutDrawer.draw_header(cover_pdf, width, height)
        RAPLayoutDrawer.draw_cover_block(cover_pdf, width, height)
        RAPLayoutDrawer.draw_footer(cover_pdf, width, height)
        cover_pdf.save()
        cover_buffer.seek(0)
        
        # ===================================================================
        # NOUVELLE APPROCHE (comme Word) : 
        # 1. Générer tout le PDF d'abord (sans sommaire)
        # 2. Chercher les textes dans le PDF généré pour trouver leurs pages
        # 3. Générer le sommaire avec les pages trouvées
        # 4. Fusionner : couverture + sommaire + contenu + programmes + conclusion
        # ===================================================================
        
        logger.info("📄 NOUVELLE APPROCHE : Génération du contenu complet d'abord (sans sommaire)...")
        
        # Récupérer les programmes depuis RAPBaseGenerator.data
        programmes = RAPBaseGenerator.data.get("programmes", [])
        
        # Si aucun programme n'est disponible, créer des programmes factices
        if not programmes:
            if RAPBaseGenerator.should_use_fake_data():
                programmes = cls.DEFAULT_DATA.get("programmes", [])
                logger.info(f"📊 Programmes factices utilisés (DEFAULT_DATA)")
            else:
                logger.warning(f"⚠️ Aucun programme trouvé et mode final - aucun programme ne sera généré")
        else:
            logger.info(f"📊 Programmes chargés depuis la DB: {len(programmes)} programmes")
        
        is_programmes_fake = bool(programmes and RAPBaseGenerator.should_use_fake_data())
        
        # Générer le CONTENU (sans sommaire) - les pages commencent à 2 (après la couverture)
        logger.info("📄 Génération du contenu (liste tableaux, graphiques, sigles, intro, partie I)...")
        content_buffer = BytesIO()
        content_pdf = canvas.Canvas(content_buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        # Commencer après la couverture (page 1) - SANS sommaire pour l'instant
        next_page = 2  # Page après la couverture
        logger.info(f"🔍 DIAGNOSTIC - next_page initial = {next_page} (après couverture, SANS sommaire)")
        
        # Note: canvas.Canvas crée déjà une première page par défaut (index 0) lorsqu'on l'initialise
        # Pas besoin d'appeler showPage() ici - _draw_liste_tableaux dessinera directement sur cette page
        
        # Générer la LISTE DES TABLEAUX
        logger.info(f"📄 Page {next_page}+: Liste des tableaux")
        next_page = RAPContentDrawer.draw_liste_tableaux(content_pdf, width, height, next_page)
        
        # Générer la LISTE DES GRAPHIQUES
        content_pdf.showPage()
        logger.info(f"📄 Page {next_page}+: Liste des graphiques")
        next_page = RAPContentDrawer.draw_liste_graphiques(content_pdf, width, height, next_page)
        
        # Générer SIGLES ET ABRÉVIATIONS
        content_pdf.showPage()
        logger.info(f"📄 Page {next_page}+: Sigles et abréviations")
        next_page = RAPContentDrawer.draw_liste_sigles_abreviations(content_pdf, width, height, next_page)
        
        # Générer INTRODUCTION GÉNÉRALE
        content_pdf.showPage()
        logger.info(f"📄 Page {next_page}+: Introduction générale")
        next_page = RAPContentDrawer.draw_introduction_generale(content_pdf, width, height, next_page)
        
        # PARTIE I : LE MINISTÈRE
        content_pdf.showPage()
        logger.info(f"📄 Page {next_page}: PARTIE I : LE MINISTÈRE")
        next_page = RAPContentDrawer.draw_partie_i_ministere(content_pdf, width, height, next_page)
        
        # Sauvegarder le contenu
        content_pdf.save()
        content_buffer.seek(0)
        
        # Générer les parties programmes
        programme_buffers = []
        logger.info(f"📄 Page {next_page}+: Génération des programmes...")
        
        for idx, programme in enumerate(programmes):
            if idx > 0:
                next_page += 1  # Nouvelle page pour chaque programme
            
            numero = programme.get("numero", 1)
            titre = programme.get("titre", "")
            logger.info(f"📄 Page {next_page}: PARTIE {numero + 1} : LE PROGRAMME {numero} « {titre.upper()} »")
            
            # Marquer le programme comme factice si nécessaire
            programme["_is_fake"] = is_programmes_fake
            
            # Utiliser SimpleDocTemplate pour cette partie
            prog_buffer, final_page = RAPProgramSectionDrawer.draw_partie_programme(programme, next_page, session=session)
            programme_buffers.append(prog_buffer)
            next_page = final_page
        
        # Générer la CONCLUSION GÉNÉRALE
        next_page += 1
        logger.info(f"📄 Page {next_page}: CONCLUSION GÉNÉRALE")
        conclusion_buffer, next_page = RAPContentDrawer.draw_conclusion_generale(next_page, session=session)
        
        # Fusionner tout dans un PDF temporaire (sans sommaire) pour chercher les textes
        logger.info("📄 Création d'un PDF temporaire complet (sans sommaire) pour chercher les textes...")
        temp_writer = PdfWriter()
        
        # Ajouter la couverture
        cover_reader = PdfReader(cover_buffer)
        temp_writer.add_page(cover_reader.pages[0])
        
        # Ajouter le contenu
        content_reader = PdfReader(content_buffer)
        content_pages_clean = []
        for page in content_reader.pages:
            page_text = page.extract_text().strip()
            if page_text:  # Seulement garder les pages avec du contenu
                content_pages_clean.append(page)
        for page in content_pages_clean:
            temp_writer.add_page(page)
        
        # Ajouter les programmes
        for prog_buffer in programme_buffers:
            prog_reader = PdfReader(prog_buffer)
            for page in prog_reader.pages:
                temp_writer.add_page(page)
        
        # Ajouter la conclusion
        conclusion_reader = PdfReader(conclusion_buffer)
        for page in conclusion_reader.pages:
            temp_writer.add_page(page)
        
        # Sauvegarder le PDF temporaire
        temp_pdf_buffer = BytesIO()
        temp_writer.write(temp_pdf_buffer)
        temp_pdf_buffer.seek(0)
        temp_pdf_reader = PdfReader(temp_pdf_buffer)
        
        logger.info(f"📄 PDF temporaire créé: {len(temp_pdf_reader.pages)} pages (sans sommaire)")
        
        # Chercher les vraies pages des tableaux et graphiques dans le PDF temporaire
        logger.info("🔍 Recherche des vraies pages des tableaux et graphiques dans le PDF temporaire...")
        tableaux_pages, graphiques_pages = RAPPageManager.find_tableaux_and_graphiques_pages(temp_pdf_reader)
        
        # Stocker les pages trouvées pour utilisation dans les fonctions de dessin
        RAPBaseGenerator._tableaux_pages_found = tableaux_pages
        RAPBaseGenerator._graphiques_pages_found = graphiques_pages
        
        # Mettre à jour les pages dans cls.data si trouvées (pour utilisation dans les fonctions)
        if tableaux_pages:
            if "tableaux" not in cls.data:
                cls.data["tableaux"] = []
            
            # Mettre à jour les pages et titres des tableaux existants
            for tableau in cls.data["tableaux"]:
                numero = tableau.get("numero")
                if numero and numero in tableaux_pages:
                    page_num, titre = tableaux_pages[numero]
                    tableau["page"] = page_num
                    tableau["titre"] = titre  # Mettre à jour le titre aussi
                    logger.info(f"✅ Tableau {numero} mis à jour: page {page_num}, titre: '{titre[:80]}...'")
        
        if graphiques_pages:
            if "graphiques" not in cls.data:
                cls.data["graphiques"] = []
            
            # Mettre à jour les pages et titres des graphiques existants
            for graphique in cls.data["graphiques"]:
                numero = graphique.get("numero")
                if numero and numero in graphiques_pages:
                    page_num, titre = graphiques_pages[numero]
                    graphique["page"] = page_num
                    graphique["titre"] = titre  # Mettre à jour le titre aussi
                    logger.info(f"✅ Graphique {numero} mis à jour: page {page_num}, titre: '{titre[:80]}...'")
        
        logger.info("✅ Pages des tableaux et graphiques trouvées et stockées dans cls.data")
        logger.info(f"📊 Récapitulatif - Tableaux pages trouvées: {tableaux_pages}")
        logger.info(f"📊 Récapitulatif - Graphiques pages trouvées: {graphiques_pages}")
        
        # Mettre à jour cls.data avec les vraies pages pour utilisation immédiate
        if tableaux_pages:
            logger.info(f"📝 Mise à jour de cls.data avec {len(tableaux_pages)} pages de tableaux...")
            # Reconstruire ou mettre à jour la liste des tableaux avec les vraies pages
            programmes = cls.data.get("programmes", [])
            if not programmes:
                programmes = cls.DEFAULT_DATA.get("programmes", [])
            
            # Créer la liste des tableaux avec les titres extraits du PDF
            if not cls.data.get("tableaux"):
                tableaux_list = []
                # Créer un tableau pour chaque numéro trouvé dans tableaux_pages
                for numero in sorted(tableaux_pages.keys()):
                    page_num, titre = tableaux_pages[numero]
                    tableaux_list.append({
                        "numero": numero,
                        "titre": titre,  # Utiliser le titre extrait du PDF
                        "page": page_num
                    })
                
                cls.data["tableaux"] = tableaux_list
                logger.info(f"✅ Liste des tableaux créée avec {len(tableaux_list)} éléments (titres extraits du PDF)")
            else:
                # Mettre à jour les pages et titres existants
                updated_count = 0
                for tableau in cls.data["tableaux"]:
                    numero = tableau.get("numero")
                    if numero and numero in tableaux_pages:
                        page_num, titre = tableaux_pages[numero]
                        old_page = tableau.get("page", "N/A")
                        old_titre = tableau.get("titre", "N/A")
                        tableau["page"] = page_num
                        tableau["titre"] = titre  # Mettre à jour le titre aussi
                        logger.info(f"   📝 Tableau {numero}: page {old_page} → {page_num}, titre: '{titre[:60]}...'")
                        updated_count += 1
                logger.info(f"✅ {updated_count} tableaux mis à jour dans cls.data (pages et titres)")
        
        if graphiques_pages:
            logger.info(f"📝 Mise à jour de cls.data avec {len(graphiques_pages)} pages de graphiques...")
            # Reconstruire ou mettre à jour la liste des graphiques avec les vraies pages
            programmes = cls.data.get("programmes", [])
            if not programmes:
                programmes = cls.DEFAULT_DATA.get("programmes", [])
            
            # Créer la liste des graphiques avec les titres extraits du PDF
            if not cls.data.get("graphiques"):
                graphiques_list = []
                # Créer un graphique pour chaque numéro trouvé dans graphiques_pages
                for numero in sorted(graphiques_pages.keys()):
                    page_num, titre = graphiques_pages[numero]
                    graphiques_list.append({
                        "numero": numero,
                        "titre": titre,  # Utiliser le titre extrait du PDF
                        "page": page_num
                    })
                
                cls.data["graphiques"] = graphiques_list
                logger.info(f"✅ Liste des graphiques créée avec {len(graphiques_list)} éléments (titres extraits du PDF)")
            else:
                # Mettre à jour les pages et titres existants
                updated_count = 0
                for graphique in cls.data["graphiques"]:
                    numero = graphique.get("numero")
                    if numero and numero in graphiques_pages:
                        page_num, titre = graphiques_pages[numero]
                        old_page = graphique.get("page", "N/A")
                        old_titre = graphique.get("titre", "N/A")
                        graphique["page"] = page_num
                        graphique["titre"] = titre  # Mettre à jour le titre aussi
                        logger.info(f"   📝 Graphique {numero}: page {old_page} → {page_num}, titre: '{titre[:60]}...'")
                        updated_count += 1
                logger.info(f"✅ {updated_count} graphiques mis à jour dans cls.data (pages et titres)")
        
        # Régénérer les buffers des listes avec les vraies pages
        if tableaux_pages or graphiques_pages:
            logger.info("📄 Régénération des buffers des listes avec les vraies pages trouvées...")
            logger.info(f"   - Tableaux pages disponibles: {tableaux_pages}")
            logger.info(f"   - Graphiques pages disponibles: {graphiques_pages}")
            
            # Régénérer le buffer de la liste des tableaux
            logger.info("📝 Régénération du buffer de la liste des tableaux...")
            liste_tableaux_buffer_new = BytesIO()
            liste_tableaux_pdf_new = canvas.Canvas(liste_tableaux_buffer_new, pagesize=landscape(A4))
            width, height = landscape(A4)
            liste_tableaux_start_page = RAPPageManager.get_page_position("liste_tableaux", 2)
            logger.info(f"   - Page de départ pour liste tableaux: {liste_tableaux_start_page}")
            logger.info(f"   - Tableaux dans cls.data: {len(cls.data.get('tableaux', []))}")
            for tab in cls.data.get('tableaux', []):
                logger.info(f"      Tableau {tab.get('numero')}: page {tab.get('page', 'N/A')}")
            RAPContentDrawer.draw_liste_tableaux(liste_tableaux_pdf_new, width, height, liste_tableaux_start_page)
            liste_tableaux_pdf_new.save()
            liste_tableaux_buffer_new.seek(0)
            liste_tableaux_reader_new = PdfReader(liste_tableaux_buffer_new)
            logger.info(f"✅ Liste des tableaux régénérée: {len(liste_tableaux_reader_new.pages)} page(s)")
            
            # Régénérer le buffer de la liste des graphiques
            logger.info("📝 Régénération du buffer de la liste des graphiques...")
            liste_graphiques_buffer_new = BytesIO()
            liste_graphiques_pdf_new = canvas.Canvas(liste_graphiques_buffer_new, pagesize=landscape(A4))
            width, height = landscape(A4)
            liste_graphiques_start_page = RAPPageManager.get_page_position("liste_graphiques", 3)
            logger.info(f"   - Page de départ pour liste graphiques: {liste_graphiques_start_page}")
            logger.info(f"   - Graphiques dans cls.data: {len(cls.data.get('graphiques', []))}")
            for graph in cls.data.get('graphiques', []):
                logger.info(f"      Graphique {graph.get('numero')}: page {graph.get('page', 'N/A')}")
            liste_graphiques_pdf_new.showPage()  # Créer la première page
            RAPContentDrawer.draw_liste_graphiques(liste_graphiques_pdf_new, width, height, liste_graphiques_start_page)
            liste_graphiques_pdf_new.save()
            liste_graphiques_buffer_new.seek(0)
            liste_graphiques_reader_new = PdfReader(liste_graphiques_buffer_new)
            logger.info(f"✅ Liste des graphiques régénérée: {len(liste_graphiques_reader_new.pages)} page(s)")
            
            # Extraire les autres sections de content_buffer (sigles, intro, partie I)
            logger.info("📄 Extraction des autres sections du content_buffer original...")
            content_buffer.seek(0)  # Réinitialiser le buffer avant lecture
            content_reader_old = PdfReader(content_buffer)
            content_pages_all = list(content_reader_old.pages)
            logger.info(f"   - Content buffer original contient {len(content_pages_all)} pages")
            
            # Trouver où commencent les autres sections en cherchant "SIGLES ET ABRÉVIATIONS"
            debut_autres_sections = 0
            for idx, page in enumerate(content_pages_all):
                try:
                    page_text = page.extract_text().strip().upper()
                    if "SIGLES" in page_text and "ABRÉVIATIONS" in page_text:
                        debut_autres_sections = idx
                        logger.info(f"   📄 Page {idx + 1} trouvée comme début des autres sections (SIGLES ET ABRÉVIATIONS)")
                        break
                except Exception as e:
                    logger.debug(f"   ⚠️ Erreur lors de l'extraction du texte de la page {idx + 1}: {e}")
                    continue
            
            if debut_autres_sections == 0:
                logger.warning("   ⚠️ Début des autres sections non trouvé, utilisation de toutes les pages")
            
            # Extraire les pages des autres sections (sigles, intro, partie I, etc.)
            autres_sections_pages = content_pages_all[debut_autres_sections:] if debut_autres_sections >= 0 else content_pages_all
            logger.info(f"   - {len(autres_sections_pages)} pages d'autres sections extraites (à partir de la page {debut_autres_sections + 1})")
            
            # Reconstruire content_buffer avec les nouvelles listes et les autres sections
            logger.info(f"📄 Reconstruction de content_buffer: {len(liste_tableaux_reader_new.pages)} pages liste tableaux + {len(liste_graphiques_reader_new.pages)} pages liste graphiques + {len(autres_sections_pages)} pages autres sections")
            content_buffer_rebuilt = BytesIO()
            content_writer = PdfWriter()
            
            # Ajouter les nouvelles listes
            for page in liste_tableaux_reader_new.pages:
                content_writer.add_page(page)
            for page in liste_graphiques_reader_new.pages:
                content_writer.add_page(page)
            
            # Ajouter les autres sections (sigles, intro, partie I, etc.)
            logger.info("   📝 Ajout des autres sections au nouveau content_buffer...")
            for idx, page in enumerate(autres_sections_pages):
                content_writer.add_page(page)
                if idx < 3:  # Log pour les 3 premières pages
                    logger.debug(f"      Page {idx + 1} ajoutée")
            
            content_writer.write(content_buffer_rebuilt)
            content_buffer_rebuilt.seek(0)
            
            # Vérifier le nouveau content_buffer
            content_reader_new = PdfReader(content_buffer_rebuilt)
            logger.info(f"✅ content_buffer reconstruit avec succès: {len(content_reader_new.pages)} pages au total")
            logger.info(f"   - Pages liste tableaux: {len(liste_tableaux_reader_new.pages)}")
            logger.info(f"   - Pages liste graphiques: {len(liste_graphiques_reader_new.pages)}")
            logger.info(f"   - Pages autres sections: {len(autres_sections_pages)}")
            logger.info(f"   - Total: {len(liste_tableaux_reader_new.pages) + len(liste_graphiques_reader_new.pages) + len(autres_sections_pages)} pages")
            
            content_buffer = content_buffer_rebuilt  # Remplacer l'ancien buffer
        
        # Les positions ont été enregistrées directement par les PageMarker pendant la génération
        # Utiliser directement ces positions (qui sont dans le contexte du PDF temporaire, sans sommaire)
        logger.info("🔍 Utilisation des positions enregistrées par les PageMarker...")
        logger.info(f"✅ Positions enregistrées par les marqueurs: {RAPPageManager._page_positions}")
        
        # Chercher dans le PDF temporaire pour les clés manquantes (fallback)
        pages_found_by_search = RAPPageManager.find_all_toc_pages(temp_pdf_reader, nb_pages_sommaire=0)
        logger.info(f"✅ Pages trouvées par recherche (fallback): {pages_found_by_search}")
        
        # Combiner : utiliser les positions enregistrées en priorité, puis la recherche comme fallback
        pages_found = RAPPageManager._page_positions.copy()
        for key, page_num in pages_found_by_search.items():
            if key not in pages_found:
                logger.info(f"⚠️ Clé '{key}' non trouvée dans les marqueurs, utilisation de la recherche: page {page_num}")
                pages_found[key] = page_num
            else:
                logger.info(f"✅ Clé '{key}' trouvée dans les marqueurs: page {pages_found[key]} (recherche: {page_num})")
        
        logger.info(f"✅ Pages finales combinées: {pages_found}")
        
        # Générer un sommaire temporaire pour connaître son nombre de pages
        # Utiliser les positions enregistrées (sans ajustement) pour le sommaire temporaire
        logger.info("📄 Génération temporaire du sommaire pour calculer son nombre de pages...")
        # Mettre à jour RAPPageManager._page_positions avec les pages trouvées (sans ajustement) pour le sommaire temporaire
        RAPPageManager._page_positions = pages_found.copy()
        sommaire_temp_buffer = BytesIO()
        sommaire_temp_pdf = canvas.Canvas(sommaire_temp_buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        RAPContentDrawer.draw_table_of_contents(sommaire_temp_pdf, width, height, pdf_reader_complet=None, nb_pages_sommaire=0)
        sommaire_temp_pdf.save()
        sommaire_temp_buffer.seek(0)
        
        # Compter le nombre de pages du sommaire
        sommaire_temp_reader = PdfReader(sommaire_temp_buffer)
        nb_pages_sommaire = len(sommaire_temp_reader.pages)
        logger.info(f"📄 Sommaire temporaire: {nb_pages_sommaire} pages générées")
        
        # DÉSACTIVÉ: Ajustement des pages trouvées en ajoutant le nombre de pages du sommaire
        # L'utilisateur veut tester sans cet ajustement
        # # Car le sommaire sera inséré après la couverture dans le PDF final
        # # Exemple: Si "LISTE DES TABLEAUX" est trouvé à la page 2 dans le PDF temporaire (page 1 = couverture)
        # #          Dans le PDF final: page 1 = couverture, page 2-3 = sommaire (2 pages), page 4 = LISTE DES TABLEAUX
        # #          Donc: 2 + 2 = 4 ✓
        # logger.info(f"📄 Ajustement des pages trouvées: ajout de {nb_pages_sommaire} pages (sommaire)")
        # logger.info(f"   Explication: Les pages trouvées sont dans un PDF qui commence à la page 1 (couverture)")
        # logger.info(f"   Dans le PDF final, le sommaire sera inséré après la couverture, donc toutes les pages suivantes sont décalées")
        # adjusted_pages_found = {}
        # for key, page_num in pages_found.items():
        #     adjusted_page = page_num + nb_pages_sommaire
        #     adjusted_pages_found[key] = adjusted_page
        #     logger.info(f"   {key}: page {page_num} (trouvée) + {nb_pages_sommaire} (sommaire) = {adjusted_page} (dans PDF final)")
        
        # Utiliser les pages SANS ajustement (telles qu'enregistrées par les marqueurs)
        logger.info(f"📄 Utilisation des pages SANS ajustement (nb_pages_sommaire={nb_pages_sommaire} pages ignorées)")
        logger.info(f"✅ Pages non ajustées (utilisées telles quelles): {pages_found}")
        
        # Générer le sommaire final avec les pages non ajustées
        logger.info("📄 Génération finale du sommaire avec les pages NON ajustées...")
        sommaire_buffer = BytesIO()
        sommaire_pdf = canvas.Canvas(sommaire_buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        # Utiliser les pages non ajustées pour le sommaire final
        # IMPORTANT: Les pages dans pages_found sont telles qu'enregistrées (SANS ajustement)
        RAPPageManager._page_positions = pages_found
        
        RAPContentDrawer.draw_table_of_contents(sommaire_pdf, width, height, pdf_reader_complet=None, nb_pages_sommaire=0)
        sommaire_pdf.save()
        sommaire_buffer.seek(0)
        
        # Fusionner tous les PDFs dans le bon ordre
        logger.info("📎 Fusion de tous les PDFs dans le bon ordre...")
        
        writer = PdfWriter()
        logger.info(f"🔍 DIAGNOSTIC - PdfWriter créé, nombre de pages actuel: {len(writer.pages)}")
        
        # 1. Ajouter la couverture (page 1)
        cover_reader = PdfReader(cover_buffer)
        logger.info(f"🔍 DIAGNOSTIC - Nombre de pages de la couverture: {len(cover_reader.pages)}")
        for i, page in enumerate(cover_reader.pages):
            page_text = page.extract_text().strip()
            logger.info(f"🔍 DIAGNOSTIC - Page {i+1} de la couverture: {len(page_text)} caractères - Début: {page_text[:50] if page_text else 'VIDE'}")
        writer.add_page(cover_reader.pages[0])
        logger.info(f"🔍 DIAGNOSTIC - Après ajout couverture, nombre de pages dans writer: {len(writer.pages)}")
        
        # 2. Ajouter le sommaire (page 2+)
        sommaire_reader = PdfReader(sommaire_buffer)
        sommaire_pages = list(sommaire_reader.pages)
        logger.info(f"📄 Sommaire: {len(sommaire_pages)} pages générées")
        
        # Vérifier et supprimer les pages vides du sommaire
        sommaire_pages_clean = []
        for i, page in enumerate(sommaire_pages):
            # Vérifier si la page est vide (approximation : vérifier la taille du contenu)
            page_text = page.extract_text().strip()
            if page_text:  # Seulement garder les pages avec du contenu (même la première)
                sommaire_pages_clean.append(page)
                logger.info(f"🔍 DIAGNOSTIC - Page sommaire {i+1} ajoutée ({len(page_text)} caractères)")
            else:
                logger.warning(f"⚠️ Page vide détectée dans le sommaire à l'index {i}, suppression")
        
        for page in sommaire_pages_clean:
            writer.add_page(page)
        
        # 3. Ajouter toutes les autres sections (liste tableaux, graphiques, sigles, intro, partie I)
        content_reader = PdfReader(content_buffer)
        content_pages = list(content_reader.pages)
        logger.info(f"📄 Contenu (liste tableaux, etc.): {len(content_pages)} pages générées")
        
        # LOGS DE DIAGNOSTIC DÉTAILLÉS pour chaque page du contenu
        logger.info(f"🔍 DIAGNOSTIC - Analyse détaillée des pages du contenu:")
        for i, page in enumerate(content_pages):
            page_text = page.extract_text().strip()
            page_size = len(page_text)
            logger.info(f"🔍 DIAGNOSTIC - Page contenu {i+1}/{len(content_pages)}: {page_size} caractères")
            if page_size > 0:
                logger.info(f"🔍 DIAGNOSTIC -   Premiers caractères: {page_text[:100]}")
            else:
                logger.warning(f"🔍 DIAGNOSTIC -   ⚠️ PAGE VIDE détectée à l'index {i}!")
        
        # Vérifier et supprimer les pages vides du contenu
        content_pages_clean = []
        for i, page in enumerate(content_pages):
            page_text = page.extract_text().strip()
            # NE PAS garder la première page si elle est vide - c'est une page vide à supprimer
            if page_text:  # Seulement garder les pages avec du contenu
                content_pages_clean.append(page)
                logger.info(f"🔍 DIAGNOSTIC - Page {i+1} ajoutée au PDF final ({len(page_text)} caractères)")
            else:
                logger.warning(f"⚠️ Page vide détectée dans le contenu à l'index {i}, suppression")
        
        logger.info(f"🔍 DIAGNOSTIC - Total pages contenu à ajouter: {len(content_pages_clean)} (sur {len(content_pages)} générées)")
        logger.info(f"🔍 DIAGNOSTIC - Nombre de pages dans writer avant ajout contenu: {len(writer.pages)}")
        for idx, page in enumerate(content_pages_clean):
            writer.add_page(page)
            logger.info(f"🔍 DIAGNOSTIC - Page contenu {idx+1}/{len(content_pages_clean)} ajoutée. Total pages dans writer: {len(writer.pages)}")
        logger.info(f"🔍 DIAGNOSTIC - Après ajout contenu, nombre total de pages dans writer: {len(writer.pages)}")
        
        # 4. Ajouter les parties programmes
        for prog_buffer in programme_buffers:
            prog_reader = PdfReader(prog_buffer)
            for page in prog_reader.pages:
                writer.add_page(page)
        
        # 5. Ajouter la conclusion générale
        conclusion_reader = PdfReader(conclusion_buffer)
        for page in conclusion_reader.pages:
            writer.add_page(page)
        
        # Écrire le PDF fusionné
        final_buffer = BytesIO()
        writer.write(final_buffer)
        final_buffer.seek(0)
        
        logger.info(f"✅ PDF généré avec succès. Positions de pages calculées: {RAPPageManager._page_positions}")
        return final_buffer


# ============================================================================
# ALIAS POUR COMPATIBILITÉ
# ============================================================================

# Pour maintenir la compatibilité avec le code existant, on peut créer un alias
RapportAnnuelPerformanceGeneratorSimpleDoc = RAPPDFGenerator

# Note: Le fichier est maintenant complet avec toutes les classes modulaires.
# Chaque classe a une responsabilité unique et bien définie.
# Les implémentations complètes peuvent être migrées progressivement depuis
# rapport_annuel_performance_service_simpledoc.py selon les besoins.


