"""
Générateur de Rapport du Cadre de Performance (CP).

Ce module génère un PDF de rapport du Cadre de Performance en réutilisant les classes
et méthodes du Rapport Annuel de Performance (RAP) pour les pages de couverture,
sommaire, liste des tableaux et liste des figures.

Architecture modulaire :
- CPBaseGenerator : Classe de base avec constantes et utilitaires (hérite de RAPBaseGenerator)
- CPLayoutDrawer : Éléments de layout (cover, footer, background) - réutilise RAPLayoutDrawer
- CPContentDrawer : Contenu principal (sommaire, listes) - réutilise RAPContentDrawer
- CPPDFGenerator : Orchestrateur principal
"""
from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, LongTable, Frame, Spacer, SimpleDocTemplate, SimpleDocTemplate
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PyPDF2 import PdfReader, PdfWriter

from app.services.rapport_annuel_performance_generator_modular import (
    RAPBaseGenerator,
    RAPLayoutDrawer,
    RAPContentDrawer,
    RAPPageManager,
    RAPStylingManager,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CLASSE DE BASE - HÉRITE DU RAP
# ============================================================================

class CPBaseGenerator(RAPBaseGenerator):
    """
    Classe de base pour le Rapport du Cadre de Performance (CP).
    
    Hérite de RAPBaseGenerator pour réutiliser toutes les constantes,
    compteurs et utilitaires. Peut être étendue avec des constantes
    spécifiques au CP si nécessaire.
    """
    
    # Données par défaut pour le CP
    DEFAULT_DATA = {
        "annee_debut": 2026,
        "annee_fin": 2028,
        "section": "SECTION 376",
        "ministere": "MINISTERE DU PATRIMOINE, DU PORTEFEUILLE DE L'ETAT ET DES ENTREPRISES PUBLIQUES",
        "titre_rapport": "DOCUMENT DE PRESENTATION DU CADRE DE PERFORMANCE",
        "titre_periode": "AU TITRE DE LA PERIODE",
        "date_publication": "Mars 2025",
        "logo_path": "",
        "cadre_global_commentaire": "Le Ministère du Patrimoine, du Portefeuille de l'État et des Entreprises Publiques (MPPEEP) a été créé à la faveur du remaniement ministériel du 17 octobre 2023. Ses missions sont définies par l'article 13 du décret 2023-820 portant attribution des membres du gouvernement. Le ministère est organisé par le décret n° 2023-963 du 6 décembre 2023 portant organisation du MPPEEP. Au regard de ces deux (2) décrets, le MPPEEP a identifié trois (3) programmes et défini trois (3) objectifs globaux auxquels sont rattachés neuf (9) objectifs spécifiques.",
    }


# ============================================================================
# GESTIONNAIRE DE LAYOUT - RÉUTILISE RAPLayoutDrawer
# ============================================================================

class CPLayoutDrawer(RAPLayoutDrawer):
    """
    Gestionnaire de layout pour le rapport CP.
    
    Réutilise directement les méthodes de RAPLayoutDrawer :
    - draw_cover_page()
    - draw_background_shapes()
    - draw_header()
    
    Surcharge draw_cover_block() pour adapter le titre au format CP
    (DOCUMENT DE PRESENTATION DU CADRE DE PERFORMANCE + période).
    Surcharge draw_footer() pour afficher la date dans le format requis.
    """
    
    @classmethod
    def draw_page_header(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine un en-tête simple pour les pages de contenu (sans logo, section, ministère).
        
        Cette méthode est utilisée pour les pages de contenu (cadre global, etc.)
        et ne dessine que les éléments nécessaires, pas les éléments de la couverture.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        """
        # Pour les pages de contenu, on ne dessine rien dans l'en-tête
        # ou on peut dessiner un en-tête minimal si nécessaire
        # Pour l'instant, on laisse vide car les pages de contenu n'ont pas besoin d'en-tête
        pass
    
    @classmethod
    def draw_cover_block(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine le bloc central avec le titre du rapport dans une boîte orange.
        
        Version adaptée pour le CP : 
        - Titre principal : "DOCUMENT DE PRESENTATION DU CADRE DE PERFORMANCE"
        - Sous-titre : "AU TITRE DE LA PERIODE [ANNEE_DEBUT]-[ANNEE_FIN]"
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        """
        from reportlab.lib.units import cm
        
        pdf.saveState()

        center_x = width / 2
        center_y = height / 2

        # ---------- BOÎTE ORANGE AVEC LE TITRE ----------
        # Dimensions de la boîte (plus large pour le mode paysage)
        box_margin_x = 3 * cm
        box_width = width - 6 * cm
        box_height = 4.5 * cm  # Hauteur réduite de 5.5 à 4.5 cm
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

        # Récupérer les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator
        
        # Essayer d'accéder aux données depuis différentes sources
        data = None
        if hasattr(CPBaseGenerator, 'data') and CPBaseGenerator.data:
            data = CPBaseGenerator.data
        elif hasattr(RAPBaseGenerator, 'data') and RAPBaseGenerator.data:
            data = RAPBaseGenerator.data
        elif hasattr(cls, 'data') and cls.data:
            data = cls.data
        else:
            data = {}
        
        titre_rapport = data.get("titre_rapport", "DOCUMENT DE PRESENTATION DU CADRE DE PERFORMANCE")
        titre_periode = data.get("titre_periode", "AU TITRE DE LA PERIODE")
        annee_debut = data.get("annee_debut", "")
        annee_fin = data.get("annee_fin", "")
        
        # Construire le texte de la période
        if annee_debut and annee_fin:
            periode_text = f"{titre_periode} {annee_debut}-{annee_fin}"
        elif annee_debut:
            periode_text = f"{titre_periode} {annee_debut}"
        else:
            periode_text = titre_periode
        
        # Log pour débogage
        logger.info(f"🔍 CP - Données disponibles: {list(data.keys()) if data else 'AUCUNE'}")
        logger.info(f"🔍 CP - Titre: {titre_rapport}, Période: {periode_text}")
        
        # Déterminer la source de chaque donnée pour le styling
        _, titre_rapport_source = RAPStylingManager._determine_data_source_for_canvas("titre_rapport", titre_rapport)
        _, periode_source = RAPStylingManager._determine_data_source_for_canvas("titre_periode", periode_text)
        
        # Toutes les données sont DB, utiliser l'italique
        should_use_italic = True
        
        # Marges intérieures de la boîte
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
        font_size = 20  # Augmenté de 16 à 20
        # Choisir la police selon la source : BoldOblique pour DB (italique), Bold sinon
        if should_use_italic:
            font_name = "Helvetica-BoldOblique"
            logger.debug(f"✅ Utilisation de Helvetica-BoldOblique pour le titre (italique)")
        else:
            font_name = "Helvetica-Bold"
            logger.debug(f"⚠️ Utilisation de Helvetica-Bold pour le titre (pas d'italique)")
        line_height = 26  # Hauteur de ligne augmentée de 22 à 26 pour correspondre à la police plus grande
        pdf.setFont(font_name, font_size)
        
        # Calculer la largeur maximale pour le texte
        max_text_width = text_area_width
        
        # Déterminer la couleur du titre (toutes les données sont DB, rouge)
        titre_color = RAPStylingManager._get_color_for_source("db")
        
        # Découper le titre en lignes (en majuscules pour la couverture)
        if titre_rapport:
            lines = wrap_text_to_width(pdf, titre_rapport.upper(), font_name, font_size, max_text_width)
            
            # Calculer la hauteur totale du titre
            titre_total_height = len(lines) * line_height
            
            # Calculer la position de départ pour centrer verticalement
            # On veut centrer le bloc titre + période dans la boîte
            periode_font_size = 20  # Augmenté de 18 à 20
            periode_line_height = 24  # Augmenté de 22 à 24 pour correspondre à la police plus grande
            periode_lines = wrap_text_to_width(pdf, periode_text.upper(), font_name, periode_font_size, max_text_width)
            periode_total_height = len(periode_lines) * periode_line_height
            
            # Espace entre le titre et la période
            espace_titre_periode = 0.3 * cm
            
            # Hauteur totale du contenu
            total_content_height = titre_total_height + espace_titre_periode + periode_total_height
            
            # Position de départ (centré verticalement dans la boîte)
            # Calculer le centre vertical de la zone de texte
            text_area_center_y = (text_area_top + text_area_bottom) / 2
            # Faire descendre le texte en soustrayant un offset
            offset_down = 0.5 * cm  # Décalage vers le bas
            start_y = text_area_center_y + (total_content_height / 2) - offset_down
            
            # Dessiner le titre
            current_y = start_y
            pdf.saveState()
            pdf.setFillColor(titre_color)
            for line in lines:
                text_x = text_area_left + (text_area_width - pdf.stringWidth(line, font_name, font_size)) / 2
                pdf.drawString(text_x, current_y, line)
                current_y -= line_height
            pdf.restoreState()
            
            # Ligne de séparation (petite ligne horizontale)
            line_y = current_y - espace_titre_periode / 2+0.7*cm
            line_length = 3 * cm
            line_x = center_x - line_length / 2
            pdf.setLineWidth(2.5)  # Augmenté de 1 à 2.5 pour une ligne plus épaisse
            pdf.setStrokeColor(cls.DARK_TEXT)
            pdf.line(line_x, line_y, line_x + line_length, line_y)
            
            # Dessiner la période
            current_y = current_y - espace_titre_periode
            pdf.saveState()
            pdf.setFont(font_name, periode_font_size)
            periode_color = RAPStylingManager._get_color_for_source(periode_source)
            pdf.setFillColor(periode_color)
            for line in periode_lines:
                text_x = text_area_left + (text_area_width - pdf.stringWidth(line, font_name, periode_font_size)) / 2
                pdf.drawString(text_x, current_y, line)
                current_y -= periode_line_height
            pdf.restoreState()
        else:
            logger.warning("⚠️ CP - Aucun titre de rapport fourni")

        pdf.restoreState()
    
    @classmethod
    def draw_footer(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine le bloc date en bas à droite de la page.
        
        Version adaptée pour le CP : affiche la date depuis les données
        (format: "Mars 2025" par exemple).
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        """
        from reportlab.lib.units import cm
        
        pdf.saveState()

        # ---------- BOÎTE DATE EN BAS À DROITE ----------
        # Récupérer la date depuis les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator
        
        # Essayer d'accéder aux données depuis différentes sources
        data = None
        if hasattr(CPBaseGenerator, 'data') and CPBaseGenerator.data:
            data = CPBaseGenerator.data
        elif hasattr(RAPBaseGenerator, 'data') and RAPBaseGenerator.data:
            data = RAPBaseGenerator.data
        elif hasattr(cls, 'data') and cls.data:
            data = cls.data
        else:
            data = {}
        
        date_publication = data.get("date_publication", "")
        
        # Si la date n'est pas fournie, générer dynamiquement
        if not date_publication:
            from datetime import datetime
            now = datetime.now()
            # Liste des mois en français
            mois_fr = [
                "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
            ]
            mois_actuel = mois_fr[now.month - 1]
            annee_actuelle = now.year
            date_publication = f"{mois_actuel} {annee_actuelle}"
            logger.info(f"📅 Date de publication générée dynamiquement: {date_publication}")
        else:
            logger.info(f"📅 Date de publication depuis les données: {date_publication}")
        
        date_source = "db"  # Générée depuis les données ou dynamiquement

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


# ============================================================================
# GESTIONNAIRE DE CONTENU - RÉUTILISE RAPContentDrawer
# ============================================================================

class CPContentDrawer(RAPContentDrawer):
    """
    Gestionnaire de contenu pour le rapport CP.
    
    Réutilise directement les méthodes de RAPContentDrawer pour :
    - draw_liste_graphiques()
    - draw_liste_sigles_abreviations()
    
    Surcharge draw_table_of_contents() et draw_liste_tableaux() pour adapter au format CP.
    """
    
    @classmethod
    def _find_cp_tableaux_in_pdf(cls, pdf_reader: Any, nb_pages_sommaire: int = 0) -> dict[int, tuple[int, str]]:
        """
        Trouve les numéros de page pour les tableaux CP en parcourant le PDF.
        
        Args:
            pdf_reader: Le PdfReader du PDF complet
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Dictionnaire {numero_tableau: (page_num, titre)} avec les tableaux trouvés
        """
        import re
        from app.services.rapport_annuel_performance_generator_modular import RAPPageManager
        
        tableaux_pages = {}
        
        # Récupérer les programmes depuis les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        programmes = CPBaseGenerator.data.get("programmes", [])
        
        # Patterns de recherche pour les tableaux CP
        # Format: {numero: [patterns possibles]}
        cp_tableaux_patterns = {
            1: [
                r"tableau\s*1\s*:",
                r"tableau\s*1\s*",
                "Cadre général de définition de la performance du ministère",
                "CADRE GENERAL DE DEFINITION DE LA PERFORMANCE",
            ],
            2: [
                r"tableau\s*2\s*:",
                r"tableau\s*2\s*",
                "Cartographie administrative des programmes",
                "CARTOGRAPHIE ADMINISTRATIVE DES PROGRAMMES",
            ],
        }
        
        # Ajouter les patterns pour les tableaux par programme (3 tableaux par programme)
        programme_num = 1
        for programme in programmes:  # Utiliser tous les programmes
            programme_libelle = programme.get("libelle", f"PROGRAMME {programme_num}") if isinstance(programme, dict) else (programme.libelle if hasattr(programme, "libelle") else f"PROGRAMME {programme_num}")
            
            # Tableau 3, 6, 9 : Cohérence entre objectifs et actions
            tableau_num = (programme_num - 1) * 3 + 3
            cp_tableaux_patterns[tableau_num] = [
                rf"tableau\s*{tableau_num}\s*:",
                rf"tableau\s*{tableau_num}\s*",
                f"Cohérence entre objectifs et actions du programme {programme_num}",
                f"COHERENCE ENTRE OBJECTIFS ET ACTIONS",
                programme_libelle.upper(),
            ]
            
            # Tableau 4, 7, 10 : Bilan de la performance
            tableau_num = (programme_num - 1) * 3 + 4
            cp_tableaux_patterns[tableau_num] = [
                rf"tableau\s*{tableau_num}\s*:",
                rf"tableau\s*{tableau_num}\s*",
                f"Bilan de la performance du programme {programme_num}",
                f"BILAN DE LA PERFORMANCE",
                programme_libelle.upper(),
            ]
            
            # Tableau 5, 8, 11 : Cadre de performance
            tableau_num = (programme_num - 1) * 3 + 5
            cp_tableaux_patterns[tableau_num] = [
                rf"tableau\s*{tableau_num}\s*:",
                rf"tableau\s*{tableau_num}\s*",
                f"Cadre de performance du programme {programme_num}",
                f"CADRE DE PERFORMANCE",
                programme_libelle.upper(),
            ]
            
            programme_num += 1
        
        # Titres par défaut pour chaque tableau
        default_titres = {
            1: "Cadre général de définition de la performance du ministère",
            2: "Cartographie administrative des programmes",
        }
        
        # Ajouter les titres par défaut pour les programmes
        programme_num = 1
        for programme in programmes:  # Utiliser tous les programmes
            programme_libelle = programme.get("libelle", f"PROGRAMME {programme_num}") if isinstance(programme, dict) else (programme.libelle if hasattr(programme, "libelle") else f"PROGRAMME {programme_num}")
            
            default_titres[(programme_num - 1) * 3 + 3] = f"Cohérence entre objectifs et actions du programme {programme_num} « {programme_libelle} »"
            default_titres[(programme_num - 1) * 3 + 4] = f"Bilan de la performance du programme {programme_num} « {programme_libelle} »"
            default_titres[(programme_num - 1) * 3 + 5] = f"Cadre de performance du programme {programme_num} « {programme_libelle} »"
            
            programme_num += 1
        
        # Parcourir le PDF pour trouver les tableaux
        for numero, patterns in cp_tableaux_patterns.items():
            for page_num in range(1, len(pdf_reader.pages) + 1):
                try:
                    page = pdf_reader.pages[page_num - 1]
                    page_text = page.extract_text()
                    if not page_text:
                        continue
                    
                    # Normaliser le texte de la page
                    page_text_normalized = RAPPageManager.normalize_text_for_search(page_text)
                    
                    # Vérifier tous les patterns pour ce tableau
                    found = False
                    for pattern in patterns:
                        if isinstance(pattern, str):
                            pattern_normalized = RAPPageManager.normalize_text_for_search(pattern)
                            if pattern_normalized in page_text_normalized:
                                found = True
                                break
                        else:
                            # Pattern regex
                            if re.search(pattern, page_text_normalized, re.IGNORECASE):
                                found = True
                                break
                    
                    if found:
                        # Extraire le titre du tableau
                        titre = RAPPageManager.extract_title_from_page_text(page_text, numero, "Tableau")
                        if not titre:
                            titre = default_titres.get(numero, f"Tableau {numero}")
                        
                        # Enregistrer la première occurrence trouvée pour chaque tableau
                        if numero not in tableaux_pages:
                            tableaux_pages[numero] = (page_num + nb_pages_sommaire, titre)
                            logger.debug(f"   Tableau {numero} trouvé à la page {page_num}: '{titre[:50]}...'")
                            break  # Passer au tableau suivant
            
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lors du traitement de la page {page_num} pour le tableau {numero}: {e}")
                    continue
        
        return tableaux_pages
    
    @classmethod
    def draw_table_of_contents(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        pdf_reader_complet: Any = None,
        nb_pages_sommaire: int = 0
    ) -> int:
        """
        Dessine la table des matières (sommaire) pour le rapport CP.
        
        Structure du sommaire :
        - I. CADRE GLOBAL DE PRESENTATION DE LA PERFORMANCE DU MINISTERE
        - II. PRESENTATION DE LA PERFORMANCE PAR PROGRAMME.
          - II.1. PROGRAMME 1 : ADMINISTRATION GENERALE.
          - II.2. PROGRAMME 2 : PORTEFEUILLE DE L'ETAT
          - II.3. PROGRAMME 3 : GESTION DES ÉTABLISSEMENTS PUBLICS NATIONAUX.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            pdf_reader_complet: Lecteur PDF complet (pour rechercher les pages)
            nb_pages_sommaire: Nombre de pages du sommaire
        
        Returns:
            Nombre de pages générées (toujours 1 pour le CP)
        """
        from reportlab.lib.units import cm
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator, RAPPageManager
        
        logger.info("📋 Dessin de la table des matières pour le CP...")
        
        # Récupérer les numéros de page dynamiquement
        # Si un PDF complet est fourni, chercher les textes dedans
        # Sinon, utiliser les pages enregistrées avec register_page_position
        pages_found = {}
        if pdf_reader_complet:
            logger.info("🔍 Recherche des textes dans le PDF complet pour le sommaire CP...")
            # TODO: Implémenter la recherche de pages dans le PDF si nécessaire
            # pages_found = cls._find_cp_pages_in_pdf(pdf_reader_complet, nb_pages_sommaire)
            logger.info(f"✅ Pages trouvées dans le PDF pour CP: {pages_found}")
        
        # Fonction helper pour récupérer une page dynamiquement
        def get_page(key: str, default: int) -> int:
            """Récupère le numéro de page depuis le PDF ou les positions enregistrées"""
            if pdf_reader_complet and key in pages_found:
                return pages_found[key]
            return RAPPageManager.get_page_position(key, default)
        
        # Calculer les pages de base (après le sommaire qui est à la page 2)
        # Le sommaire est à la page 2, donc le contenu commence à la page 3
        base_page = 3
        
        # Récupérer les pages dynamiquement pour chaque section
        # Pour l'instant, utiliser des valeurs par défaut basées sur la structure attendue
        cadre_global_page = get_page("cp_cadre_global", 4)
        presentation_programme_page = get_page("cp_presentation_programme", 7)
        
        # Récupérer les programmes depuis les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        programmes = CPBaseGenerator.data.get("programmes", [])
        
        # Structure du sommaire CP avec pages dynamiques
        sommaire_items = [
            # (titre, page, niveau, sous_items)
            ("I. CADRE GLOBAL DE PRESENTATION DE LA PERFORMANCE DU MINISTERE", cadre_global_page, 1, []),
        ]
        
        # Ajouter la section II avec les sous-programmes
        sous_programmes = []
        programme_page = presentation_programme_page
        for i, programme in enumerate(programmes, start=1):  # Utiliser tous les programmes
            programme_libelle = programme.get("libelle", f"PROGRAMME {i}") if isinstance(programme, dict) else (programme.libelle if hasattr(programme, "libelle") else f"PROGRAMME {i}")
            sous_programmes.append((
                f"II.{i}. {programme_libelle.upper()}",
                programme_page,
                2
            ))
            # Chaque programme prend environ 13 pages (20-7=13, 33-20=13)
            programme_page += 13
        
        # Si aucun programme n'est trouvé, utiliser les valeurs par défaut de l'image
        if not sous_programmes:
            sous_programmes = [
                ("II.1. PROGRAMME 1 : ADMINISTRATION GENERALE.", 7, 2),
                ("II.2. PROGRAMME 2 : PORTEFEUILLE DE L'ETAT", 20, 2),
                ("II.3. PROGRAMME 3 : GESTION DES ÉTABLISSEMENTS PUBLICS NATIONAUX.", 33, 2),
            ]
        
        sommaire_items.append((
            "II. PRESENTATION DE LA PERFORMANCE PAR PROGRAMME.",
            presentation_programme_page,
            1,
            sous_programmes
        ))
        
        # Position de départ (plus haut car pas d'en-tête)
        start_y = height - 60  # Position plus haute sans l'en-tête
        current_y = start_y
        left_margin = 3 * cm
        right_margin = width - 3 * cm
        line_height_main = 20  # Espacement pour les sections principales
        line_height_sub = 16   # Espacement pour les sous-sections
        
        # Couleur de texte (utiliser celle de la classe de base)
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Titre "TABLE DES MATIERES"
        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(dark_text_color)
        pdf.drawCentredString(width / 2, current_y, "TABLE DES MATIERES")
        current_y -= 30
        
        # Dessiner les items du sommaire
        pdf.setFont("Helvetica-Bold", 12)
        
        for item in sommaire_items:
            titre, page, niveau, sous_items = item
            
            # Section principale
            if niveau == 1:
                pdf.setFont("Helvetica-Bold", 12)
                pdf.setFillColor(dark_text_color)
                
                # Dessiner le titre
                pdf.drawString(left_margin, current_y, titre)
                
                # Dessiner les pointillés jusqu'au numéro de page
                page_text = str(page)
                page_width = pdf.stringWidth(page_text, "Helvetica-Bold", 12)
                page_x = right_margin - page_width
                
                # Calculer la position de fin du texte
                text_width = pdf.stringWidth(titre, "Helvetica-Bold", 12)
                dot_start_x = left_margin + text_width + 5
                dot_end_x = page_x - 5
                
                # Dessiner les pointillés
                if dot_end_x > dot_start_x:
                    pdf.setDash(2, 2)
                    pdf.setStrokeColor(dark_text_color)
                    pdf.line(dot_start_x, current_y - 3, dot_end_x, current_y - 3)
                    pdf.setDash()
                
                # Dessiner le numéro de page
                pdf.drawString(page_x, current_y, page_text)
                
                current_y -= line_height_main
            
            # Sous-sections
            if sous_items:
                pdf.setFont("Helvetica", 11)
                pdf.setFillColor(dark_text_color)
                
                for sous_titre, sous_page, sous_niveau in sous_items:
                    # Indentation pour les sous-sections
                    sub_left_margin = left_margin + 1 * cm
                    
                    # Dessiner le titre de la sous-section
                    pdf.drawString(sub_left_margin, current_y, sous_titre)
                    
                    # Dessiner les pointillés jusqu'au numéro de page
                    page_text = str(sous_page)
                    page_width = pdf.stringWidth(page_text, "Helvetica", 11)
                    page_x = right_margin - page_width
                    
                    # Calculer la position de fin du texte
                    text_width = pdf.stringWidth(sous_titre, "Helvetica", 11)
                    dot_start_x = sub_left_margin + text_width + 5
                    dot_end_x = page_x - 5
                    
                    # Dessiner les pointillés
                    if dot_end_x > dot_start_x:
                        pdf.setDash(2, 2)
                        pdf.setStrokeColor(dark_text_color)
                        pdf.line(dot_start_x, current_y - 3, dot_end_x, current_y - 3)
                        pdf.setDash()
                    
                    # Dessiner le numéro de page
                    pdf.drawString(page_x, current_y, page_text)
                    
                    current_y -= line_height_sub
        
        # Dessiner le pied de page avec le numéro de page
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer
        RAPLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=2,
            width=width,
            footer_margin=1.5 * cm,
            footer_height=1.5 * cm,
            right_margin=3 * cm
        )
        
        return 1
    
    @classmethod
    def draw_liste_tableaux(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int,
        pdf_reader_complet: Any = None,
        nb_pages_sommaire: int = 0
    ) -> int:
        """
        Dessine la page de la liste des tableaux pour le rapport CP.
        
        Utilise la recherche dynamique pour trouver les numéros de page des tableaux.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
            pdf_reader_complet: Lecteur PDF complet (optionnel, pour recherche dynamique)
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Le numéro de la page suivante après la liste des tableaux
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPPageManager, RAPBaseGenerator
        
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        line_spacing = 0.55 * cm
        
        # Couleur pour les éléments
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Récupérer les tableaux dynamiquement
        tableaux_pages_found = {}
        if pdf_reader_complet:
            logger.info("🔍 Recherche des tableaux dans le PDF complet pour le CP...")
            tableaux_pages_found = cls._find_cp_tableaux_in_pdf(pdf_reader_complet, nb_pages_sommaire)
            logger.info(f"✅ Tableaux trouvés dans le PDF pour CP: {len(tableaux_pages_found)} tableaux")
        
        # Construire la liste des tableaux
        tableaux_items = []
        
        # Récupérer les programmes depuis les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        programmes = CPBaseGenerator.data.get("programmes", [])
        
        # Tableaux CP par défaut
        default_tableaux = {
            1: "Cadre général de définition de la performance du ministère",
            2: "Cartographie administrative des programmes",
        }
        
        # Pages par défaut (seront remplacées si trouvées dynamiquement)
        default_pages = {
            1: 4,
            2: 5,
        }
        
        # Ajouter les tableaux par programme (3 tableaux par programme)
        programme_num = 1
        for programme in programmes:  # Utiliser tous les programmes
            programme_libelle = programme.get("libelle", f"PROGRAMME {programme_num}") if isinstance(programme, dict) else (programme.libelle if hasattr(programme, "libelle") else f"PROGRAMME {programme_num}")
            
            # Tableau 3, 6, 9 : Cohérence entre objectifs et actions
            tableau_num = (programme_num - 1) * 3 + 3
            default_tableaux[tableau_num] = f"Cohérence entre objectifs et actions du programme {programme_num} « {programme_libelle} »"
            default_pages[tableau_num] = 7 + (programme_num - 1) * 13  # 7, 20, 33
            
            # Tableau 4, 7, 10 : Bilan de la performance
            tableau_num = (programme_num - 1) * 3 + 4
            default_tableaux[tableau_num] = f"Bilan de la performance du programme {programme_num} « {programme_libelle} »"
            default_pages[tableau_num] = 8 + (programme_num - 1) * 13  # 8, 21, 34
            
            # Tableau 5, 8, 11 : Cadre de performance
            tableau_num = (programme_num - 1) * 3 + 5
            default_tableaux[tableau_num] = f"Cadre de performance du programme {programme_num} « {programme_libelle} »"
            default_pages[tableau_num] = 9 + (programme_num - 1) * 13  # 9, 22, 35 (mais l'image montre 24, donc ajuster)
            
            programme_num += 1
        
        # Ajuster les pages pour correspondre à l'image (Tableau 8 à la page 24 au lieu de 22)
        if 8 in default_pages:
            default_pages[8] = 24
        
        # Si aucun programme n'est trouvé, utiliser les valeurs par défaut de l'image
        if not programmes:
            default_tableaux = {
                1: "Cadre général de définition de la performance du ministère",
                2: "Cartographie administrative des programmes",
                3: "Cohérence entre objectifs et actions du programme 1 « Administration générale »",
                4: "Bilan de la performance du programme 1 « Administration générale »",
                5: "Cadre de performance du programme 1 « Administration générale »",
                6: "Cohérence entre objectifs et actions du programme 2 « Portefeuille de l'Etat »",
                7: "Bilan de la performance du programme 2 « Portefeuille de l'Etat »",
                8: "Cadre de performance du programme 2 « Portefeuille de l'Etat »",
                9: "Cohérence entre objectifs et actions du programme 3 « Gestion des Etablissements Publics Nationaux »",
                10: "Bilan de la performance du programme 3 « Gestion des Etablissements Publics Nationaux »",
                11: "Cadre de performance du programme 3 « Gestion des Etablissements Publics Nationaux »",
            }
            default_pages = {
                1: 4,
                2: 5,
                3: 7,
                4: 8,
                5: 9,
                6: 20,
                7: 21,
                8: 24,
                9: 33,
                10: 34,
                11: 35,
            }
        
        # Construire les items de la liste
        for numero in sorted(default_tableaux.keys()):
            titre = default_tableaux[numero]
            page = default_pages[numero]
            
            # Utiliser la page trouvée dynamiquement si disponible
            if numero in tableaux_pages_found:
                page, titre = tableaux_pages_found[numero]
            else:
                # Sinon, essayer de récupérer depuis les positions enregistrées
                page_key = f"cp_tableau_{numero}"
                registered_page = RAPPageManager.get_page_position(page_key, page)
                if registered_page != page:
                    page = registered_page
            
            tableau_text = f"Tableau {numero}: {titre}"
            tableaux_items.append({"text": tableau_text, "page": page, "level": 0, "bold": False})
        
        # Fonction helper pour dessiner une ligne
        def draw_tableau_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                current_y_pos = start_y
            line_spacing_val = line_spacing
            
            x_text = left_margin + (level * 1 * cm)
            x_page = width - right_margin - 1 * cm
            page_num_width = 2 * cm
            max_text_width = x_page - x_text - page_num_width
            
            pdf.saveState()
            
            pdf.setFillColor(dark_text_color)
            pdf.setStrokeColor(dark_text_color)
            
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
            
            # Dessiner le texte
            pdf.drawString(x_text, current_y_pos, text_to_draw)
            
            # Dessiner les pointillés jusqu'au numéro de page
            actual_text_width = pdf.stringWidth(text_to_draw, font, font_size)
            page_str = str(page) if page else "..."
            page_width = pdf.stringWidth(page_str, font, font_size)
            page_x = x_page
            
            dot_start_x = x_text + actual_text_width + 5
            dot_end_x = page_x - 5
            
            if dot_end_x > dot_start_x:
                pdf.setDash(2, 2)
                pdf.setLineWidth(1)
                pdf.line(dot_start_x, current_y_pos - 3, dot_end_x, current_y_pos - 3)
                pdf.setDash()
            
            # Dessiner le numéro de page
            pdf.drawRightString(page_x, current_y_pos, page_str)
            
            pdf.restoreState()
            
            return current_y_pos - line_spacing_val
        
        # Dessiner le titre "LISTE DES TABLEAUX" (centré)
        current_y = start_y
        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(dark_text_color)
        title_text = "LISTE DES TABLEAUX"
        title_width = pdf.stringWidth(title_text, "Helvetica-Bold", 16)
        title_x = (width - title_width) / 2  # Centrer horizontalement
        pdf.drawString(title_x, current_y, title_text)
        current_y -= 30
        
        # Dessiner les tableaux
        current_page = start_page
        for item in tableaux_items:
            if current_y < content_bottom:
                # Dessiner le footer de la page précédente avant de créer une nouvelle page
                RAPLayoutDrawer.draw_page_footer(
                    pdf=pdf,
                    page_number=current_page,
                    width=width,
                    footer_margin=footer_margin,
                    footer_height=footer_height,
                    right_margin=right_margin
                )
                
                # Nouvelle page si nécessaire
                pdf.showPage()
                current_y = start_y
                current_page += 1
            
            current_y = draw_tableau_line(
                item["text"],
                item["page"],
                item["level"],
                item["bold"],
                current_y
            )
        
        # Dessiner le pied de page de la dernière page
        RAPLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=current_page,
            width=width,
            footer_margin=footer_margin,
            footer_height=footer_height,
            right_margin=right_margin
        )
        
        return current_page + 1
    
    @classmethod
    def _find_cp_annexes_in_pdf(cls, pdf_reader: Any, nb_pages_sommaire: int = 0) -> dict[int, tuple[int, str]]:
        """
        Trouve les numéros de page pour les annexes CP en parcourant le PDF.
        
        Args:
            pdf_reader: Le PdfReader du PDF complet
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Dictionnaire {numero_annexe: (page_num, titre)} avec les annexes trouvées
        """
        import re
        from app.services.rapport_annuel_performance_generator_modular import RAPPageManager
        
        annexes_pages = {}
        
        # Récupérer les programmes depuis les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        programmes = CPBaseGenerator.data.get("programmes", [])
        
        # Patterns de recherche pour les annexes CP
        # Format: {numero: [patterns possibles]}
        cp_annexes_patterns = {}
        
        # Ajouter les patterns pour les annexes par programme (2 annexes par programme)
        programme_num = 1
        for programme in programmes:  # Utiliser tous les programmes
            programme_libelle = programme.get("libelle", f"PROGRAMME {programme_num}") if isinstance(programme, dict) else (programme.libelle if hasattr(programme, "libelle") else f"PROGRAMME {programme_num}")
            
            # Annexe 1, 3, 5 : Fiche signalétique des indicateurs
            annexe_num = (programme_num - 1) * 2 + 1
            cp_annexes_patterns[annexe_num] = [
                rf"annexe\s*{annexe_num}\s*:",
                rf"annexe\s*{annexe_num}\s*",
                f"Fiche signalétique des indicateurs du programme {programme_num}",
                f"FICHE SIGNALETIQUE DES INDICATEURS",
                programme_libelle.upper(),
            ]
            
            # Annexe 2, 4, 6 : Demande de modification de l'architecture programmatique
            annexe_num = (programme_num - 1) * 2 + 2
            cp_annexes_patterns[annexe_num] = [
                rf"annexe\s*{annexe_num}\s*:",
                rf"annexe\s*{annexe_num}\s*",
                f"Demande de modification de l'architecture programmatique du programme {programme_num}",
                f"DEMANDE DE MODIFICATION DE L'ARCHITECTURE PROGRAMMATIQUE",
                programme_libelle.upper(),
            ]
            
            programme_num += 1
        
        # Titres par défaut pour chaque annexe
        default_titres = {}
        
        # Ajouter les titres par défaut pour les programmes
        programme_num = 1
        for programme in programmes:  # Utiliser tous les programmes
            programme_libelle = programme.get("libelle", f"PROGRAMME {programme_num}") if isinstance(programme, dict) else (programme.libelle if hasattr(programme, "libelle") else f"PROGRAMME {programme_num}")
            
            default_titres[(programme_num - 1) * 2 + 1] = f"Fiche signalétique des indicateurs du programme {programme_num} « {programme_libelle} »"
            default_titres[(programme_num - 1) * 2 + 2] = f"Demande de modification de l'architecture programmatique du programme {programme_num} « {programme_libelle} »"
            
            programme_num += 1
        
        # Parcourir le PDF pour trouver les annexes
        for numero, patterns in cp_annexes_patterns.items():
            for page_num in range(1, len(pdf_reader.pages) + 1):
                try:
                    page = pdf_reader.pages[page_num - 1]
                    page_text = page.extract_text()
                    if not page_text:
                        continue
                    
                    # Normaliser le texte de la page
                    page_text_normalized = RAPPageManager.normalize_text_for_search(page_text)
                    
                    # Vérifier tous les patterns pour cette annexe
                    found = False
                    for pattern in patterns:
                        if isinstance(pattern, str):
                            pattern_normalized = RAPPageManager.normalize_text_for_search(pattern)
                            if pattern_normalized in page_text_normalized:
                                found = True
                                break
                        else:
                            # Pattern regex
                            if re.search(pattern, page_text_normalized, re.IGNORECASE):
                                found = True
                                break
                    
                    if found:
                        # Extraire le titre de l'annexe
                        titre = RAPPageManager.extract_title_from_page_text(page_text, numero, "Annexe")
                        if not titre:
                            titre = default_titres.get(numero, f"Annexe {numero}")
                        
                        # Enregistrer la première occurrence trouvée pour chaque annexe
                        if numero not in annexes_pages:
                            annexes_pages[numero] = (page_num + nb_pages_sommaire, titre)
                            logger.debug(f"   Annexe {numero} trouvée à la page {page_num}: '{titre[:50]}...'")
                            break  # Passer à l'annexe suivante
            
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lors du traitement de la page {page_num} pour l'annexe {numero}: {e}")
                    continue
        
        return annexes_pages
    
    @classmethod
    def draw_liste_annexes(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int,
        pdf_reader_complet: Any = None,
        nb_pages_sommaire: int = 0
    ) -> int:
        """
        Dessine la page de la liste des annexes pour le rapport CP.
        
        Utilise la recherche dynamique pour trouver les numéros de page des annexes.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
            pdf_reader_complet: Lecteur PDF complet (optionnel, pour recherche dynamique)
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Le numéro de la page suivante après la liste des annexes
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPPageManager, RAPBaseGenerator
        
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        line_spacing = 0.55 * cm
        
        # Couleur pour les éléments
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Récupérer les annexes dynamiquement
        annexes_pages_found = {}
        if pdf_reader_complet:
            logger.info("🔍 Recherche des annexes dans le PDF complet pour le CP...")
            annexes_pages_found = cls._find_cp_annexes_in_pdf(pdf_reader_complet, nb_pages_sommaire)
            logger.info(f"✅ Annexes trouvées dans le PDF pour CP: {len(annexes_pages_found)} annexes")
        
        # Construire la liste des annexes
        annexes_items = []
        
        # Récupérer les programmes depuis les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        programmes = CPBaseGenerator.data.get("programmes", [])
        
        # Annexes CP par défaut
        default_annexes = {}
        default_pages = {}
        
        # Ajouter les annexes par programme (2 annexes par programme)
        programme_num = 1
        for programme in programmes:  # Utiliser tous les programmes
            programme_libelle = programme.get("libelle", f"PROGRAMME {programme_num}") if isinstance(programme, dict) else (programme.libelle if hasattr(programme, "libelle") else f"PROGRAMME {programme_num}")
            
            # Annexe 1, 3, 5 : Fiche signalétique des indicateurs
            annexe_num = (programme_num - 1) * 2 + 1
            default_annexes[annexe_num] = f"Fiche signalétique des indicateurs du programme {programme_num} « {programme_libelle} »"
            default_pages[annexe_num] = 10 + (programme_num - 1) * 15  # 10, 25, 36 (approximatif)
            
            # Annexe 2, 4, 6 : Demande de modification de l'architecture programmatique
            annexe_num = (programme_num - 1) * 2 + 2
            default_annexes[annexe_num] = f"Demande de modification de l'architecture programmatique du programme {programme_num} « {programme_libelle} »"
            default_pages[annexe_num] = 17 + (programme_num - 1) * 14  # 17, 31, 38 (approximatif)
            
            programme_num += 1
        
        # Ajuster les pages pour correspondre à l'image
        if 3 in default_pages:
            default_pages[3] = 25
        if 4 in default_pages:
            default_pages[4] = 31
        if 5 in default_pages:
            default_pages[5] = 36
        if 6 in default_pages:
            default_pages[6] = 38
        
        # Si aucun programme n'est trouvé, utiliser les valeurs par défaut de l'image
        if not programmes:
            default_annexes = {
                1: "Fiche signalétique des indicateurs du programme 1 « Administration générale »",
                2: "Demande de modification de l'architecture programmatique du programme 1 « Administration générale»",
                3: "Fiche signalétique des indicateurs du programme 2 « Portefeuille de l'Etat »",
                4: "Demande de modification de l'architecture programmatique du programme 2 « Portefeuille de l'Etat »",
                5: "Fiches signalétiques des indicateurs du programme 3 « Gestion des Etablissements Publics Nationaux »",
                6: "Demande de modification de l'architecture programmatique du programme 3 Gestion des Etablissements Publics Nationaux",
            }
            default_pages = {
                1: 10,
                2: 17,
                3: 25,
                4: 31,
                5: 36,
                6: 38,
            }
        
        # Construire les items de la liste
        for numero in sorted(default_annexes.keys()):
            titre = default_annexes[numero]
            page = default_pages[numero]
            
            # Utiliser la page trouvée dynamiquement si disponible
            if numero in annexes_pages_found:
                page, titre = annexes_pages_found[numero]
            else:
                # Sinon, essayer de récupérer depuis les positions enregistrées
                page_key = f"cp_annexe_{numero}"
                registered_page = RAPPageManager.get_page_position(page_key, page)
                if registered_page != page:
                    page = registered_page
            
            annexe_text = f"ANNEXE {numero}: {titre}"
            annexes_items.append({"text": annexe_text, "page": page, "level": 0, "bold": False})
        
        # Fonction helper pour dessiner une ligne
        def draw_annexe_line(text: str, page: str | int, level: int = 0, bold: bool = False, current_y_pos: float = None):
            if current_y_pos is None:
                current_y_pos = start_y
            line_spacing_val = line_spacing
            
            x_text = left_margin + (level * 1 * cm)
            x_page = width - right_margin - 1 * cm
            page_num_width = 2 * cm
            max_text_width = x_page - x_text - page_num_width
            
            pdf.saveState()
            
            pdf.setFillColor(dark_text_color)
            pdf.setStrokeColor(dark_text_color)
            
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
            
            # Dessiner le texte
            pdf.drawString(x_text, current_y_pos, text_to_draw)
            
            # Dessiner les pointillés jusqu'au numéro de page
            actual_text_width = pdf.stringWidth(text_to_draw, font, font_size)
            page_str = str(page) if page else "..."
            page_width = pdf.stringWidth(page_str, font, font_size)
            page_x = x_page
            
            dot_start_x = x_text + actual_text_width + 5
            dot_end_x = page_x - 5
            
            if dot_end_x > dot_start_x:
                pdf.setDash(2, 2)
                pdf.setLineWidth(1)
                pdf.line(dot_start_x, current_y_pos - 3, dot_end_x, current_y_pos - 3)
                pdf.setDash()
            
            # Dessiner le numéro de page
            pdf.drawRightString(page_x, current_y_pos, page_str)
            
            pdf.restoreState()
            
            return current_y_pos - line_spacing_val
        
        # Dessiner le titre "LISTE DES ANNEXES" (centré)
        current_y = start_y
        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(dark_text_color)
        title_text = "LISTE DES ANNEXES"
        title_width = pdf.stringWidth(title_text, "Helvetica-Bold", 16)
        title_x = (width - title_width) / 2  # Centrer horizontalement
        pdf.drawString(title_x, current_y, title_text)
        current_y -= 30
        
        # Dessiner les annexes
        current_page = start_page
        for item in annexes_items:
            if current_y < content_bottom:
                # Dessiner le footer de la page précédente avant de créer une nouvelle page
                RAPLayoutDrawer.draw_page_footer(
                    pdf=pdf,
                    page_number=current_page,
                    width=width,
                    footer_margin=footer_margin,
                    footer_height=footer_height,
                    right_margin=right_margin
                )
                
                # Nouvelle page si nécessaire
                pdf.showPage()
                current_y = start_y
                current_page += 1
            
            current_y = draw_annexe_line(
                item["text"],
                item["page"],
                item["level"],
                item["bold"],
                current_y
            )
        
        # Dessiner le pied de page de la dernière page
        RAPLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=current_page,
            width=width,
            footer_margin=footer_margin,
            footer_height=footer_height,
            right_margin=right_margin
        )
        
        return current_page + 1
    
    @classmethod
    def draw_cadre_global(
        cls,
        width: float = None,
        height: float = None,
        start_page: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Dessine la page du cadre global de présentation de la performance du ministère.
        
        Contient :
        - Titre de section "I. CADRE GLOBAL DE PRESENTATION DE LA PERFORMANCE DU MINISTERE"
        - Tableau 1 : Cadre général de définition de la performance du ministère
        - Commentaire (depuis cadre_global_commentaire)
        
        Args:
            width: Largeur de la page (format paysage A4)
            height: Hauteur de la page (format paysage A4)
            start_page: Numéro de page de début
        
        Returns:
            Tuple (buffer, final_page) où buffer est le BytesIO du PDF généré
            et final_page est le numéro de la page suivante
        """
        from reportlab.lib.units import cm
        from app.services.rapport_annuel_performance_generator_modular import (
            RAPBaseGenerator, RAPLayoutDrawer, RAPPageManager
        )
        
        # Dimensions par défaut si non fournies
        if width is None or height is None:
            width, height = landscape(A4)
        
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        
        # Buffer pour le PDF
        buffer = BytesIO()
        
        # Récupérer les données
        from app.services.rapport_cadre_performance_generator import CPBaseGenerator
        data = CPBaseGenerator.data if hasattr(CPBaseGenerator, 'data') else {}
        session = CPBaseGenerator._db_session if hasattr(CPBaseGenerator, '_db_session') and CPBaseGenerator._db_session else None
        
        # Récupérer le commentaire
        cadre_global_commentaire = data.get("cadre_global_commentaire", "")
        mode = data.get("mode", "brouillon")
        annee_debut = data.get("annee_debut", 2026)
        annee_fin = data.get("annee_fin", 2028)
        
        # Styles
        story_styles = getSampleStyleSheet()
        
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=story_styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,  # LEFT
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        tableau_title_style = ParagraphStyle(
            "TableauTitle",
            parent=story_styles['Heading3'],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=0,  # LEFT
            spaceAfter=6,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=4,  # JUSTIFY
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Construire la story
        story = []
        
        # Titre de section
        story.append(Paragraph("I. CADRE GLOBAL DE PRESENTATION DE LA PERFORMANCE DU MINISTERE", section_title_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Titre du tableau
        tableau_num = cls.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_num} : Cadre général de définition de la performance du ministère", tableau_title_style))
        
        # Données du tableau (exemple avec données par défaut)
        # TODO: Récupérer les données réelles depuis la base de données ou les paramètres
        # Utiliser Paragraph pour les en-têtes pour permettre le retour à la ligne si nécessaire
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # CENTER
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        table_data = [
            [
                Paragraph("N°", header_style),
                Paragraph("OBJECTIFS<br/>GLOBAUX", header_style),  # Retour à la ligne pour éviter le débordement
                Paragraph("PROGRAMME<br/>CONCERNE", header_style),  # Retour à la ligne
                Paragraph("OBJECTIFS SPECIFIQUES<br/>PAR PROGRAMME", header_style)  # Retour à la ligne
            ],
        ]
        
        # Charger les données depuis la base de données
        objectifs_data = []
        
        if session:
            try:
                from app.models.performance import ObjectifPerformance, TypeObjectif
                from app.models.personnel import Programme
                from sqlmodel import select, and_
                from app.services.report_data_loader import ReportDataLoader
                
                logger.info("🔍 Chargement des objectifs globaux et spécifiques depuis la base de données...")
                
                # Récupérer tous les programmes
                programmes_query = select(Programme).order_by(Programme.code, Programme.libelle)
                programmes_list = session.exec(programmes_query).all()
                
                numero_og = 1
                for programme in programmes_list:
                    # Charger TOUS les objectifs globaux pour ce programme directement depuis la base
                    try:
                        logger.info(f"🔍 Chargement des objectifs globaux pour le programme: {programme.libelle} (ID: {programme.id})")
                        
                        # Récupérer TOUS les objectifs globaux du programme (sans filtre sur période)
                        og_query = select(ObjectifPerformance).where(
                            and_(
                                ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value,
                                ObjectifPerformance.programme_id == programme.id
                            )
                        ).order_by(ObjectifPerformance.code, ObjectifPerformance.id)
                        objectifs_globaux_db = session.exec(og_query).all()
                        
                        logger.info(f"📊 {len(objectifs_globaux_db)} objectifs globaux trouvés pour le programme {programme.libelle}")
                        
                        objectifs_globaux = []
                        for og in objectifs_globaux_db:
                            # Récupérer les objectifs spécifiques pour cet objectif global (filtrés par période)
                            os_query = select(ObjectifPerformance).where(
                                and_(
                                    ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value,
                                    ObjectifPerformance.objectif_global_id == og.id,
                                    ObjectifPerformance.periode.ilike(f"%{annee_debut}%")
                                )
                            ).order_by(ObjectifPerformance.code, ObjectifPerformance.id)
                            objectifs_specifiques = session.exec(os_query).all()
                            
                            logger.info(f"   - OG '{og.titre if hasattr(og, 'titre') else 'N/A'}': {len(objectifs_specifiques)} objectifs spécifiques")
                            
                            objectifs_globaux.append({
                                "objectif_global": og,
                                "objectifs_specifiques": objectifs_specifiques
                            })
                        
                        # Ajouter à objectifs_data
                        for og_data in objectifs_globaux:
                            og = og_data["objectif_global"]
                            os_list = og_data["objectifs_specifiques"]
                            
                            objectifs_data.append({
                                "numero": numero_og,
                                "objectif_global": og.titre if hasattr(og, 'titre') else str(og),
                                "programme": programme.libelle if hasattr(programme, 'libelle') else str(programme),
                                "objectifs_specifiques": [
                                    os.titre if hasattr(os, 'titre') else str(os)
                                    for os in os_list
                                ]
                            })
                            numero_og += 1
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur lors du chargement des données pour le programme {programme.libelle}: {e}")
                        continue
                
                logger.info(f"📊 {len(objectifs_data)} objectifs globaux chargés depuis la base de données")
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement des données depuis la base: {e}", exc_info=True)
        
        # Si aucune donnée chargée, utiliser les données par défaut
        if not objectifs_data:
            logger.warning("⚠️ Aucune donnée chargée depuis la base, utilisation des données par défaut")
            objectifs_data = [
                {
                    "numero": 1,
                    "objectif_global": "Renforcer la gouvernance du Ministère",
                    "programme": "Administration générale",
                    "objectifs_specifiques": [
                        "Améliorer le cadre institutionnel du Ministère",
                        "Améliorer la gestion des ressources humaines, matérielles et financières du Ministère",
                        "Assurer un meilleur suivi de la maintenance et des réhabilitations du patrimoine immobilier de l'Etat",
                        "Assurer une meilleure gestion du patrimoine immobilier de l'Etat"
                    ]
                },
                {
                    "numero": 2,
                    "objectif_global": "Améliorer la gestion du Portefeuille de l'Etat",
                    "programme": "Portefeuille de l'Etat",
                    "objectifs_specifiques": [
                        "Assurer la coordination de l'administration du Portefeuille de l'État",
                        "Améliorer la gouvernance des Entreprises Publiques",
                        "Améliorer le contrôle des Entreprises Publiques"
                    ]
                },
                {
                    "numero": 3,
                    "objectif_global": "Améliorer la gestion des Etablissements Publics Nationaux (EPN)",
                    "programme": "Etablissements Publics Nationaux",
                    "objectifs_specifiques": [
                        "Assurer la coordination de l'administration du programme EPN",
                        "Améliorer la gouvernance des EPN"
                    ]
                }
            ]
        
        # Fonction helper pour formater le texte selon le mode (rouge en brouillon, noir en final)
        is_final = mode == "final"
        placeholder = "" if is_final else "................."
        
        def format_text_for_mode(text, default_placeholder="................."):
            """Formate le texte en rouge (brouillon) ou noir (final), avec placeholder si vide"""
            # Si la valeur est None ou vide, utiliser le placeholder
            if text is None or (isinstance(text, str) and not text.strip()):
                if is_final:
                    return ""
                else:
                    return f'<font color="#FF0000">{default_placeholder}</font>'
            
            # Convertir le texte en string
            text_str = str(text)
            
            # Formater le texte normalement
            if is_final:
                return text_str
            else:
                # Échapper les caractères HTML spéciaux SAUF les balises <br/> et les balises de formatage qui doivent rester
                # Liste des balises HTML à préserver
                html_tags = [
                    ("<br/>", "___BR___"),
                    ("<br>", "___BR___"),
                    ("<b>", "___B_OPEN___"),
                    ("</b>", "___B_CLOSE___"),
                    ("<i>", "___I_OPEN___"),
                    ("</i>", "___I_CLOSE___"),
                    ("<u>", "___U_OPEN___"),
                    ("</u>", "___U_CLOSE___"),
                    ("<strong>", "___STRONG_OPEN___"),
                    ("</strong>", "___STRONG_CLOSE___"),
                    ("<em>", "___EM_OPEN___"),
                    ("</em>", "___EM_CLOSE___"),
                ]
                
                # Remplacer temporairement les balises HTML par des placeholders
                for tag, placeholder in html_tags:
                    text_str = text_str.replace(tag, placeholder)
                
                # Échapper les autres caractères HTML
                text_escaped = text_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                # Restaurer les balises HTML
                for tag, placeholder in html_tags:
                    text_escaped = text_escaped.replace(placeholder, tag)
                
                return f'<font color="#FF0000">{text_escaped}</font>'
        
        # Construire les lignes du tableau - chaque objectif spécifique dans sa propre ligne
        current_row = 1  # Commence après l'en-tête (ligne 0)
        spans_to_add = []  # Pour stocker les fusions de cellules
        
        for obj in objectifs_data:
            num_objectifs_specifiques = len(obj["objectifs_specifiques"])
            first_row_for_obj = current_row
            
            # Pour chaque objectif spécifique, créer une ligne
            # Si pas d'objectifs spécifiques, créer une ligne avec placeholder
            if not obj["objectifs_specifiques"] or len(obj["objectifs_specifiques"]) == 0:
                # Créer une ligne avec placeholder pour les objectifs spécifiques
                os_text_formatted = format_text_for_mode("", ".................")
                os_para = Paragraph(os_text_formatted, ParagraphStyle(
                    "ObjectifsSpecifiques",
                    parent=body_style,
                    fontSize=9,
                    leading=11,
                    alignment=0,  # LEFT
                    leftIndent=0,
                    rightIndent=0,
                ))
                
                # Première ligne avec N°, OBJECTIFS GLOBAUX et PROGRAMME
                objectif_global_formatted = format_text_for_mode(obj.get("objectif_global", ""))
                objectif_global_para = Paragraph(objectif_global_formatted, ParagraphStyle(
                    "ObjectifGlobal",
                    parent=body_style,
                    fontSize=9,
                    leading=11,
                    alignment=0,  # LEFT
                    leftIndent=0,
                    rightIndent=0,
                ))
                
                programme_formatted = format_text_for_mode(obj.get("programme", ""))
                programme_para = Paragraph(programme_formatted, ParagraphStyle(
                    "Programme",
                    parent=body_style,
                    fontSize=9,
                    leading=11,
                    alignment=0,  # LEFT
                    leftIndent=0,
                    rightIndent=0,
                ))
                
                numero_formatted = format_text_for_mode(str(obj.get("numero", "")))
                numero_para = Paragraph(numero_formatted, ParagraphStyle(
                    "Numero",
                    parent=body_style,
                    fontSize=9,
                    leading=11,
                    alignment=1,  # CENTER
                    leftIndent=0,
                    rightIndent=0,
                ))
                
                table_data.append([
                    numero_para,
                    objectif_global_para,
                    programme_para,
                    os_para
                ])
                current_row += 1
                continue
            
            for idx, os in enumerate(obj["objectifs_specifiques"]):
                # Formater chaque objectif spécifique avec une puce
                os_text = f"• {os}" if os else ""
                os_text_formatted = format_text_for_mode(os_text)
                os_para = Paragraph(os_text_formatted, ParagraphStyle(
                    "ObjectifsSpecifiques",
                    parent=body_style,
                    fontSize=9,
                    leading=11,
                    alignment=0,  # LEFT
                    leftIndent=0,
                    rightIndent=0,
                ))
                
                # Si c'est la première ligne de cet objectif global, inclure N°, OBJECTIFS GLOBAUX et PROGRAMME
                if idx == 0:
                    # Utiliser Paragraph pour OBJECTIFS GLOBAUX et PROGRAMME pour permettre le retour à la ligne
                    objectif_global_formatted = format_text_for_mode(obj["objectif_global"])
                    objectif_global_para = Paragraph(objectif_global_formatted, ParagraphStyle(
                        "ObjectifGlobal",
                        parent=body_style,
                        fontSize=9,
                        leading=11,
                        alignment=0,  # LEFT
                        leftIndent=0,
                        rightIndent=0,
                    ))
                    
                    programme_formatted = format_text_for_mode(obj["programme"])
                    programme_para = Paragraph(programme_formatted, ParagraphStyle(
                        "Programme",
                        parent=body_style,
                        fontSize=9,
                        leading=11,
                        alignment=0,  # LEFT
                        leftIndent=0,
                        rightIndent=0,
                    ))
                    
                    # Le numéro aussi en rouge en mode brouillon
                    numero_formatted = format_text_for_mode(str(obj["numero"]))
                    numero_para = Paragraph(numero_formatted, ParagraphStyle(
                        "Numero",
                        parent=body_style,
                        fontSize=9,
                        leading=11,
                        alignment=1,  # CENTER
                        leftIndent=0,
                        rightIndent=0,
                    ))
                    
                    table_data.append([
                        numero_para,
                        objectif_global_para,
                        programme_para,
                        os_para
                    ])
                else:
                    # Pour les lignes suivantes, laisser les 3 premières colonnes vides (seront fusionnées)
                    table_data.append([
                        "",  # N° - sera fusionné
                        "",  # OBJECTIFS GLOBAUX - sera fusionné
                        "",  # PROGRAMME CONCERNE - sera fusionné
                        os_para
                    ])
                
                current_row += 1
            
            # Enregistrer les fusions de cellules pour cet objectif global
            if num_objectifs_specifiques > 1:
                # Fusionner N° verticalement
                spans_to_add.append(("SPAN", (0, first_row_for_obj), (0, current_row - 1)))
                # Fusionner OBJECTIFS GLOBAUX verticalement
                spans_to_add.append(("SPAN", (1, first_row_for_obj), (1, current_row - 1)))
                # Fusionner PROGRAMME CONCERNE verticalement
                spans_to_add.append(("SPAN", (2, first_row_for_obj), (2, current_row - 1)))
        
        # Largeurs des colonnes (ajustées pour éviter le débordement)
        available_width = width - left_margin - right_margin
        col_widths = [
            1.5 * cm,  # N°
            5.5 * cm,  # OBJECTIFS GLOBAUX (augmenté pour plus d'espace)
            5 * cm,  # PROGRAMME CONCERNE (augmenté pour plus d'espace)
            available_width - 1.5 * cm - 5.5 * cm - 5 * cm  # OBJECTIFS SPECIFIQUES (reste)
        ]
        
        # Créer le LongTable pour permettre le découpage sur plusieurs pages
        table = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
        
        # Style du tableau
        table_style = [
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),  # Réduit de 10 à 9 pour éviter le débordement
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),  # Réduit de 4 à 3
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),  # Réduit de 4 à 3
            ("TOPPADDING", (0, 0), (-1, -1), 2),  # Réduit de 3 à 2
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),  # Réduit de 3 à 2
        ]
        
        # Ajouter les fusions de cellules
        for span in spans_to_add:
            table_style.append(span)
        
        # Alignement centré pour la colonne N°
        table_style.append(("ALIGN", (0, 1), (0, -1), "CENTER"))
        table_style.append(("VALIGN", (0, 1), (0, -1), "MIDDLE"))
        
        # Centrer verticalement les colonnes OBJECTIFS GLOBAUX (colonne 1) et PROGRAMME CONCERNE (colonne 2)
        table_style.append(("VALIGN", (1, 1), (1, -1), "MIDDLE"))  # OBJECTIFS GLOBAUX
        table_style.append(("VALIGN", (2, 1), (2, -1), "MIDDLE"))  # PROGRAMME CONCERNE
        
        table.setStyle(TableStyle(table_style))
        
        # Ajouter le tableau à la story
        story.append(table)
        story.append(Spacer(1, 0.5 * cm))
        
        # Ajouter le commentaire
        if cadre_global_commentaire and cadre_global_commentaire.strip():
            # Échapper les caractères spéciaux HTML
            commentaire_escaped = cadre_global_commentaire.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convertir les retours à la ligne en <br/>
            commentaire_html = commentaire_escaped.replace("\n", "<br/>")
            # En mode final, texte en noir ; en mode brouillon, texte en rouge
            if mode == "final":
                story.append(Paragraph("<b>Commentaire :</b>", ParagraphStyle(
                    "CommentaireLabel",
                    parent=body_style,
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    leading=14,
                    spaceAfter=6,
                    textColor=RAPBaseGenerator.DARK_TEXT
                )))
                story.append(Paragraph(commentaire_html, ParagraphStyle(
                    "CommentaireText",
                    parent=body_style,
                    fontSize=11,
                    leading=14,
                    alignment=4,  # JUSTIFY
                    spaceAfter=12,
                    textColor=RAPBaseGenerator.DARK_TEXT
                )))
            else:
                story.append(Paragraph("<font color=\"#FF0000\"><b>Commentaire :</b></font>", ParagraphStyle(
                    "CommentaireLabel",
                    parent=body_style,
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    leading=14,
                    spaceAfter=6
                )))
                commentaire_html_red = f"<font color=\"#FF0000\">{commentaire_html}</font>"
                story.append(Paragraph(commentaire_html_red, ParagraphStyle(
                    "CommentaireText",
                    parent=body_style,
                    fontSize=11,
                    leading=14,
                    alignment=4,  # JUSTIFY
                    spaceAfter=12
                )))
        else:
            # En mode final, ne pas afficher le placeholder
            if mode != "final":
                story.append(Paragraph("<font color=\"#FF0000\"><b>Commentaire :</b>..........................</font>", body_style))
        
        # Ajouter le Tableau 2 : Cartographie administrative des programmes
        story.append(Spacer(1, 0.5 * cm))
        tableau_num_2 = cls.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_num_2} : Cartographie administrative des programmes", tableau_title_style))
        
        # Charger les données de cartographie administrative depuis la base de données
        cartographie_data = []
        
        if session:
            try:
                from app.models.personnel import Programme, Direction, SousDirection, Service
                from sqlmodel import select, and_
                from app.services.report_data_loader import ReportDataLoader
                
                logger.info("🔍 Chargement des données de cartographie administrative depuis la base de données...")
                
                # Récupérer tous les programmes
                programmes_query = select(Programme).order_by(Programme.code, Programme.libelle)
                programmes_list_carto = session.exec(programmes_query).all()
                
                # Récupérer les données des organismes et projets depuis le formulaire
                organismes_tutelle_raw = data.get("organismes_tutelle", "")
                organismes_prives_ong_raw = data.get("organismes_prives_ong", "")
                projets_hors_pip_raw = data.get("projets_hors_pip", "")
                
                for programme in programmes_list_carto:
                    try:
                        # Charger les données du programme via ReportDataLoader
                        programmes_data = ReportDataLoader.load_data_programmes(
                            session,
                            programme_nom=programme.libelle,
                            annee=annee_debut,
                            include_sigobe_stats=False
                        )
                        programme_obj = programmes_data.get("programme")
                        
                        # Récupérer les directions et services
                        services_centraux = []
                        if programme_obj:
                            # Récupérer les directions
                            directions_query = select(Direction).where(
                                Direction.programme_id == programme_obj.id
                            ).order_by(Direction.libelle)
                            directions = session.exec(directions_query).all()
                            
                            for direction in directions:
                                services_centraux.append(direction.libelle if hasattr(direction, 'libelle') else str(direction))
                                
                                # Récupérer les sous-directions
                                sous_directions_query = select(SousDirection).where(
                                    SousDirection.direction_id == direction.id
                                ).order_by(SousDirection.libelle)
                                sous_directions = session.exec(sous_directions_query).all()
                                
                                for sous_direction in sous_directions:
                                    services_centraux.append(f"  {sous_direction.libelle if hasattr(sous_direction, 'libelle') else str(sous_direction)}")
                                    
                                    # Récupérer les services
                                    services_query = select(Service).where(
                                        Service.sous_direction_id == sous_direction.id
                                    ).order_by(Service.libelle)
                                    services = session.exec(services_query).all()
                                    
                                    for service in services:
                                        services_centraux.append(f"    {service.libelle if hasattr(service, 'libelle') else str(service)}")
                            
                            # Récupérer les services directement rattachés au programme (sans direction)
                            services_directs_query = select(Service).where(
                                and_(
                                    Service.programme_id == programme_obj.id,
                                    Service.direction_id.is_(None),
                                    Service.sous_direction_id.is_(None)
                                )
                            ).order_by(Service.libelle)
                            services_directs = session.exec(services_directs_query).all()
                            
                            for service in services_directs:
                                services_centraux.append(service.libelle if hasattr(service, 'libelle') else str(service))
                        
                        # Parser les organismes sous tutelle (format: "P1: Organisme1\nP2: Organisme2" ou juste "Organisme1\nOrganisme2")
                        organismes_tutelle = []
                        if organismes_tutelle_raw:
                            programme_code_upper = programme.code.upper() if hasattr(programme, 'code') and programme.code else ""
                            
                            for line in organismes_tutelle_raw.strip().split("\n"):
                                line = line.strip()
                                if not line:
                                    continue
                                
                                # Si la ligne contient ":", c'est le format "P1: Organisme" ou "P1: Administration: Organisme"
                                if ":" in line:
                                    parts = line.split(":", 1)
                                    if len(parts) == 2:
                                        prog_code = parts[0].strip().upper()
                                        org_name = parts[1].strip()
                                        
                                        # Vérifier si cet organisme appartient à ce programme
                                        # Comparer le code du programme (ex: "P1" avec "P1")
                                        if programme_code_upper and prog_code == programme_code_upper:
                                            organismes_tutelle.append(org_name)
                                        # Essayer de matcher par numéro de programme (ex: "P1" dans le code "P1")
                                        elif prog_code.startswith("P") and programme_code_upper:
                                            # Extraire le numéro du code (ex: "1" de "P1")
                                            try:
                                                prog_num_from_code = prog_code.replace("P", "").strip()
                                                # Vérifier si ce numéro est dans le code du programme
                                                if prog_num_from_code and prog_num_from_code in programme_code_upper:
                                                    organismes_tutelle.append(org_name)
                                            except:
                                                pass
                                else:
                                    # Si pas de ":", c'est juste un organisme (on l'ajoute pour tous les programmes ou on le met dans le premier)
                                    # Pour l'instant, on l'ajoute seulement si c'est le premier programme
                                    if programmes_list_carto and programme == programmes_list_carto[0]:
                                        organismes_tutelle.append(line)
                        
                        # Parser les organismes privés/ONG (format: "P1: ONG1\nP2: ONG2" ou juste "ONG1\nONG2")
                        organismes_prives_ong = []
                        if organismes_prives_ong_raw:
                            programme_code_upper = programme.code.upper() if hasattr(programme, 'code') and programme.code else ""
                            
                            for line in organismes_prives_ong_raw.strip().split("\n"):
                                line = line.strip()
                                if not line:
                                    continue
                                
                                # Si la ligne contient ":", c'est le format "P1: ONG"
                                if ":" in line:
                                    parts = line.split(":", 1)
                                    if len(parts) == 2:
                                        prog_code = parts[0].strip().upper()
                                        org_name = parts[1].strip()
                                        
                                        # Vérifier si cet organisme appartient à ce programme
                                        # Comparer le code du programme (ex: "P1" avec "P1")
                                        if programme_code_upper and prog_code == programme_code_upper:
                                            organismes_prives_ong.append(org_name)
                                        # Essayer de matcher par numéro de programme (ex: "P1" dans le code "P1")
                                        elif prog_code.startswith("P") and programme_code_upper:
                                            # Extraire le numéro du code (ex: "1" de "P1")
                                            try:
                                                prog_num_from_code = prog_code.replace("P", "").strip()
                                                # Vérifier si ce numéro est dans le code du programme
                                                if prog_num_from_code and prog_num_from_code in programme_code_upper:
                                                    organismes_prives_ong.append(org_name)
                                            except:
                                                pass
                                else:
                                    # Si pas de ":", c'est juste un organisme (on l'ajoute pour tous les programmes ou on le met dans le premier)
                                    # Pour l'instant, on l'ajoute seulement si c'est le premier programme
                                    if programmes_list_carto and programme == programmes_list_carto[0]:
                                        organismes_prives_ong.append(line)
                        
                        # Charger les projets PIP depuis sigobe_execution (type de dépense = investissements)
                        projets_pip = []
                        projets_hors_pip = []
                        
                        try:
                            from app.models.budget import SigobeExecution
                            
                            # Récupérer les investissements pour ce programme
                            sigobe_invest_query = select(SigobeExecution).where(
                                SigobeExecution.annee == annee_debut
                            ).where(
                                SigobeExecution.programmes.ilike(f"%{programme.libelle}%")
                            ).where(
                                (SigobeExecution.type_depense.ilike("%INVESTISSEMENT%"))
                                | (SigobeExecution.type_depense.ilike("%I%"))
                                | (SigobeExecution.type_depense == "I")
                            )
                            
                            sigobe_invest = session.exec(sigobe_invest_query).all()
                            
                            # Grouper par projet (utiliser le champ activites comme identifiant de projet)
                            projets_dict = {}
                            for sigobe in sigobe_invest:
                                # Utiliser uniquement le champ activites comme identifiant de projet
                                projet_id = sigobe.activites
                                
                                if projet_id and projet_id.strip():
                                    # Normaliser le nom du projet (enlever les doublons)
                                    projet_nom = projet_id.strip()
                                    
                                    # Vérifier si c'est un projet PIP (généralement les projets PIP ont un code spécifique)
                                    # Pour l'instant, on considère tous les investissements comme PIP
                                    # Les projets hors PIP seront identifiés différemment si nécessaire
                                    if projet_nom not in projets_dict:
                                        projets_dict[projet_nom] = True
                                        projets_pip.append(projet_nom)
                            
                            # Trier les projets par ordre alphabétique
                            projets_pip.sort()
                            
                            logger.info(f"📊 {len(projets_pip)} projets PIP trouvés pour le programme {programme.libelle}")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Erreur lors du chargement des projets PIP pour le programme {programme.libelle}: {e}")
                            projets_pip = []
                            projets_hors_pip = []
                        
                        # Parser les projets hors PIP depuis le formulaire (format: "P1: Projet1\nP2: Projet2")
                        if projets_hors_pip_raw:
                            programme_code_upper = programme.code.upper() if hasattr(programme, 'code') and programme.code else ""
                            
                            for line in projets_hors_pip_raw.strip().split("\n"):
                                line = line.strip()
                                if not line:
                                    continue
                                
                                # Si la ligne contient ":", c'est le format "P1: Projet"
                                if ":" in line:
                                    parts = line.split(":", 1)
                                    if len(parts) == 2:
                                        prog_code = parts[0].strip().upper()
                                        projet_nom = parts[1].strip()
                                        
                                        # Vérifier si ce projet appartient à ce programme
                                        # Comparer le code du programme (ex: "P1" avec "P1")
                                        if programme_code_upper and prog_code == programme_code_upper:
                                            projets_hors_pip.append(projet_nom)
                                        # Essayer de matcher par numéro de programme (ex: "P1" dans le code "P1")
                                        elif prog_code.startswith("P") and programme_code_upper:
                                            # Extraire le numéro du code (ex: "1" de "P1")
                                            try:
                                                prog_num_from_code = prog_code.replace("P", "").strip()
                                                # Vérifier si ce numéro est dans le code du programme
                                                if prog_num_from_code and prog_num_from_code in programme_code_upper:
                                                    projets_hors_pip.append(projet_nom)
                                            except:
                                                pass
                                else:
                                    # Si pas de ":", c'est juste un projet (on l'ajoute pour tous les programmes ou on le met dans le premier)
                                    # Pour l'instant, on l'ajoute seulement si c'est le premier programme
                                    if programmes_list_carto and programme == programmes_list_carto[0]:
                                        projets_hors_pip.append(line)
                        
                        # Trier les projets hors PIP par ordre alphabétique
                        projets_hors_pip.sort()
                        
                        cartographie_data.append({
                            "programme": f"{programme.code if hasattr(programme, 'code') else 'P'}: {programme.libelle if hasattr(programme, 'libelle') else str(programme)}",
                            "services_centraux": services_centraux,
                            "organismes_tutelle": organismes_tutelle,
                            "organismes_prives_ong": organismes_prives_ong,
                            "projets_pip": projets_pip,
                            "projets_hors_pip": projets_hors_pip
                        })
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur lors du chargement des données de cartographie pour le programme {programme.libelle}: {e}")
                        continue
                
                logger.info(f"📊 {len(cartographie_data)} programmes chargés pour la cartographie administrative")
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement des données de cartographie: {e}", exc_info=True)
        
        # Si aucune donnée chargée, créer une ligne vide avec "................"
        if not cartographie_data:
            logger.warning("⚠️ Aucune donnée de cartographie chargée")
            cartographie_data = [
                {
                    "programme": "................",
                    "services_centraux": [],
                    "organismes_tutelle": [],
                    "organismes_prives_ong": [],
                    "projets_pip": [],
                    "projets_hors_pip": []
                }
            ]
        
        # Construire les données du tableau 2
        table_data_2 = []
        
        # En-tête du tableau avec fusion pour PROJETS
        header_style_2 = ParagraphStyle(
            "HeaderStyle2",
            parent=story_styles['Normal'],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # CENTER
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Première ligne d'en-tête (6 colonnes au total)
        table_data_2.append([
            Paragraph("PROGRAMMES", header_style_2),
            Paragraph("SERVICES CENTRAUX<br/>ET REGIONAUX", header_style_2),
            Paragraph("ORGANISME SOUS TUTELLE<br/>DIRECTE (EPN, SODE, SEM)", header_style_2),
            Paragraph("ORGANISME PRIVE ET<br/>ONG SUBVENTIONNEES", header_style_2),
            Paragraph("PROJETS", header_style_2),  # Cette cellule sera fusionnée avec la suivante
            ""  # Placeholder pour la fusion
        ])
        
        # Deuxième ligne d'en-tête (sous-colonnes pour PROJETS)
        table_data_2.append([
            "",  # PROGRAMMES - fusionné verticalement
            "",  # SERVICES - fusionné verticalement
            "",  # ORGANISME TUTELLE - fusionné verticalement
            "",  # ORGANISME PRIVE - fusionné verticalement
            Paragraph("PIP", header_style_2),
            Paragraph("HORS PIP", header_style_2)
        ])
        
        # Construire les lignes de données
        for carto in cartographie_data:
            # Formater les listes en texte avec retours à la ligne et puces
            services_list = carto["services_centraux"] if carto["services_centraux"] else []
            services_text = "<br/>".join([f"• {service}" for service in services_list]) if services_list else "............................."
            
            organismes_tutelle_list = carto["organismes_tutelle"] if carto["organismes_tutelle"] else []
            organismes_tutelle_text = "<br/>".join([f"• {org}" for org in organismes_tutelle_list]) if organismes_tutelle_list else "............................."
            
            organismes_prives_list = carto["organismes_prives_ong"] if carto["organismes_prives_ong"] else []
            organismes_prives_text = "<br/>".join([f"• {org}" for org in organismes_prives_list]) if organismes_prives_list else "............................."
            
            projets_pip_list = carto["projets_pip"] if carto["projets_pip"] else []
            projets_pip_text = "<br/>".join([f"• {proj}" for proj in projets_pip_list]) if projets_pip_list else "............................."
            
            projets_hors_pip_list = carto["projets_hors_pip"] if carto["projets_hors_pip"] else []
            projets_hors_pip_text = "<br/>".join([f"• {proj}" for proj in projets_hors_pip_list]) if projets_hors_pip_list else "............................."
            
            # Formater avec format_text_for_mode
            programme_formatted = format_text_for_mode(carto["programme"])
            services_formatted = format_text_for_mode(services_text)
            organismes_tutelle_formatted = format_text_for_mode(organismes_tutelle_text)
            organismes_prives_formatted = format_text_for_mode(organismes_prives_text)
            projets_pip_formatted = format_text_for_mode(projets_pip_text)
            projets_hors_pip_formatted = format_text_for_mode(projets_hors_pip_text)
            
            # Créer les Paragraph
            programme_para = Paragraph(programme_formatted, ParagraphStyle(
                "ProgrammeCarto",
                parent=body_style,
                fontSize=9,
                leading=11,
                alignment=0,  # LEFT
                leftIndent=0,
                rightIndent=0,
            ))
            
            services_para = Paragraph(services_formatted, ParagraphStyle(
                "ServicesCarto",
                parent=body_style,
                fontSize=9,
                leading=11,
                alignment=0,  # LEFT
                leftIndent=0,
                rightIndent=0,
            ))
            
            organismes_tutelle_para = Paragraph(organismes_tutelle_formatted, ParagraphStyle(
                "OrganismesTutelle",
                parent=body_style,
                fontSize=9,
                leading=11,
                alignment=0,  # LEFT
                leftIndent=0,
                rightIndent=0,
            ))
            
            organismes_prives_para = Paragraph(organismes_prives_formatted, ParagraphStyle(
                "OrganismesPrives",
                parent=body_style,
                fontSize=9,
                leading=11,
                alignment=0,  # LEFT
                leftIndent=0,
                rightIndent=0,
            ))
            
            projets_pip_para = Paragraph(projets_pip_formatted, ParagraphStyle(
                "ProjetsPIP",
                parent=body_style,
                fontSize=9,
                leading=11,
                alignment=0,  # LEFT
                leftIndent=0,
                rightIndent=0,
            ))
            
            projets_hors_pip_para = Paragraph(projets_hors_pip_formatted, ParagraphStyle(
                "ProjetsHorsPIP",
                parent=body_style,
                fontSize=9,
                leading=11,
                alignment=0,  # LEFT
                leftIndent=0,
                rightIndent=0,
            ))
            
            table_data_2.append([
                programme_para,
                services_para,
                organismes_tutelle_para,
                organismes_prives_para,
                projets_pip_para,
                projets_hors_pip_para
            ])
        
        # Largeurs des colonnes pour le tableau 2 (augmenté pour SERVICES CENTRAUX ET REGIONAUX)
        available_width_2 = width - left_margin - right_margin
        col_widths_2 = [
            3 * cm,  # PROGRAMMES
            6 * cm,  # SERVICES CENTRAUX ET REGIONAUX (augmenté de 4.5 à 6 cm)
            3.5 * cm,  # ORGANISME SOUS TUTELLE DIRECTE
            3 * cm,  # ORGANISME PRIVE ET ONG SUBVENTIONNEES
            (available_width_2 - 3 * cm - 6 * cm - 3.5 * cm - 3 * cm) / 2,  # PROJETS PIP
            (available_width_2 - 3 * cm - 6 * cm - 3.5 * cm - 3 * cm) / 2,  # PROJETS HORS PIP
        ]
        
        # Créer le LongTable pour le tableau 2
        table_2 = LongTable(table_data_2, colWidths=col_widths_2, repeatRows=2, splitByRow=1)
        
        # Style du tableau 2
        table_style_2 = [
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),  # Les 2 premières lignes (en-têtes)
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 1), 9),
            ("ALIGN", (0, 2), (-1, -1), "LEFT"),
            ("VALIGN", (0, 2), (-1, -1), "TOP"),
            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 2), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        
        # Fusionner les cellules de la première ligne d'en-tête pour PROJETS
        table_style_2.append(("SPAN", (4, 0), (5, 0)))  # Fusionner PROJETS sur 2 colonnes (PIP et HORS PIP)
        
        # Fusionner les cellules verticalement pour les 4 premières colonnes (sur les 2 lignes d'en-tête)
        table_style_2.append(("SPAN", (0, 0), (0, 1)))  # PROGRAMMES - fusionné verticalement
        table_style_2.append(("SPAN", (1, 0), (1, 1)))  # SERVICES - fusionné verticalement
        table_style_2.append(("SPAN", (2, 0), (2, 1)))  # ORGANISME TUTELLE - fusionné verticalement
        table_style_2.append(("SPAN", (3, 0), (3, 1)))  # ORGANISME PRIVE - fusionné verticalement
        
        # Centrer verticalement la colonne PROGRAMMES (colonne 0)
        table_style_2.append(("VALIGN", (0, 2), (0, -1), "MIDDLE"))  # PROGRAMMES
        # Centrer verticalement les colonnes ORGANISME SOUS TUTELLE DIRECTE (colonne 2)
        table_style_2.append(("VALIGN", (2, 2), (2, -1), "MIDDLE"))
        # Centrer verticalement les colonnes ORGANISME PRIVE ET ONG SUBVENTIONNEES (colonne 3)
        table_style_2.append(("VALIGN", (3, 2), (3, -1), "MIDDLE"))
        # Centrer verticalement les colonnes PROJETS PIP (colonne 4)
        table_style_2.append(("VALIGN", (4, 2), (4, -1), "MIDDLE"))
        # Centrer verticalement les colonnes PROJETS HORS PIP (colonne 5)
        table_style_2.append(("VALIGN", (5, 2), (5, -1), "MIDDLE"))
        
        table_2.setStyle(TableStyle(table_style_2))
        
        # Ajouter le tableau 2 à la story
        story.append(table_2)
        
        # Ajouter le commentaire du tableau 2
        tableau2_commentaire = data.get("tableau2_commentaire", "")
        if tableau2_commentaire and tableau2_commentaire.strip():
            story.append(Spacer(1, 0.3 * cm))
            # Échapper les caractères spéciaux HTML
            commentaire2_escaped = tableau2_commentaire.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convertir les retours à la ligne en <br/>
            commentaire2_html = commentaire2_escaped.replace("\n", "<br/>")
            # En mode final, texte en noir ; en mode brouillon, texte en rouge
            if mode == "final":
                story.append(Paragraph("<b>Commentaire :</b>", ParagraphStyle(
                    "CommentaireLabel2",
                    parent=body_style,
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    leading=14,
                    spaceAfter=6,
                    textColor=RAPBaseGenerator.DARK_TEXT
                )))
                story.append(Paragraph(commentaire2_html, ParagraphStyle(
                    "CommentaireText2",
                    parent=body_style,
                    fontSize=11,
                    leading=14,
                    alignment=4,  # JUSTIFY
                    spaceAfter=12,
                    textColor=RAPBaseGenerator.DARK_TEXT
                )))
            else:
                story.append(Paragraph("<font color=\"#FF0000\"><b>Commentaire :</b></font>", ParagraphStyle(
                    "CommentaireLabel2",
                    parent=body_style,
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    leading=14,
                    spaceAfter=6
                )))
                commentaire2_html_red = f"<font color=\"#FF0000\">{commentaire2_html}</font>"
                story.append(Paragraph(commentaire2_html_red, ParagraphStyle(
                    "CommentaireText2",
                    parent=body_style,
                    fontSize=11,
                    leading=14,
                    alignment=4,  # JUSTIFY
                    spaceAfter=12
                )))
        else:
            # En mode final, ne pas afficher le placeholder
            if mode != "final":
                story.append(Spacer(1, 0.3 * cm))
                story.append(Paragraph("<font color=\"#FF0000\"><b>Commentaire :</b>..........................</font>", body_style))
        
        # Créer le SimpleDocTemplate
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        from app.services.rapport_cadre_performance_generator import CPLayoutDrawer
        
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            CPLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RAPLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            CPLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RAPLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin
            )
        
        # Construire le PDF
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        from PyPDF2 import PdfReader
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("cp_cadre_global", start_page)
        RAPPageManager.register_page_position(f"cp_tableau_{tableau_num}", start_page)
        RAPPageManager.register_page_position(f"cp_tableau_{tableau_num_2}", start_page)
        
        buffer.seek(0)
        return buffer, final_page
    
    @classmethod
    def draw_performance_par_programme(
        cls,
        width: float = None,
        height: float = None,
        start_page: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Dessine la section "II. PRESENTATION DE LA PERFORMANCE PAR PROGRAMME".
        
        Pour chaque programme, génère :
        - Titre "II.X. Programme X: [Nom]"
        - Objectif global
        - Tableau : Cohérence entre objectifs et actions du programme
        - Commentaire
        
        Args:
            width: Largeur de la page (format paysage A4)
            height: Hauteur de la page (format paysage A4)
            start_page: Numéro de page de début
        
        Returns:
            Tuple (buffer, final_page) où buffer est le BytesIO du PDF généré
            et final_page est le numéro de la page suivante
        """
        from reportlab.lib.units import cm
        from app.services.rapport_annuel_performance_generator_modular import (
            RAPBaseGenerator, RAPLayoutDrawer, RAPPageManager
        )
        from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph, Spacer
        
        # Récupérer les données
        data = CPBaseGenerator.data if hasattr(CPBaseGenerator, 'data') else {}
        session = CPBaseGenerator._db_session if hasattr(CPBaseGenerator, '_db_session') and CPBaseGenerator._db_session else None
        
        # Récupérer les paramètres
        mode = data.get("mode", "brouillon")
        annee_debut = data.get("annee_debut", 2026)
        programme_commentaire = data.get("programme_commentaire", "")
        cadre_performance_commentaire = data.get("cadre_performance_commentaire", "")
        
        # Dimensions de la page
        if width is None or height is None:
            width, height = landscape(A4)
        
        # Marges
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        bottom_margin = 2.5 * cm
        
        # Buffer pour le PDF
        buffer = BytesIO()
        story = []
        
        # Styles
        story_styles = getSampleStyleSheet()
        
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=story_styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT,
            alignment=0  # LEFT
        )
        
        programme_title_style = ParagraphStyle(
            "ProgrammeTitle",
            parent=story_styles['Heading2'],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            spaceAfter=8,
            textColor=RAPBaseGenerator.DARK_TEXT,
            alignment=0  # LEFT
        )
        
        objectif_global_style = ParagraphStyle(
            "ObjectifGlobal",
            parent=story_styles['Normal'],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceAfter=8,
            textColor=RAPBaseGenerator.DARK_TEXT,
            alignment=0  # LEFT
        )
        
        tableau_title_style = ParagraphStyle(
            "TableauTitle",
            parent=story_styles['Normal'],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            spaceAfter=6,
            textColor=RAPBaseGenerator.DARK_TEXT,
            alignment=0  # LEFT
        )
        
        body_style = story_styles['Normal']
        
        # Style centré pour les colonnes numériques (colonnes 2-6 du tableau Bilan)
        body_style_centered = ParagraphStyle(
            "BodyStyleCentered",
            parent=story_styles['Normal'],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=1  # CENTER
        )
        
        # Fonction pour formater le texte selon le mode
        def format_text_for_mode(text, default_placeholder="................."):
            """Formate le texte en rouge (brouillon) ou noir (final), avec placeholder si vide"""
            # Si la valeur est None ou vide, utiliser le placeholder
            if not text or (isinstance(text, str) and not text.strip()):
                text = default_placeholder
            
            # Échapper les caractères HTML spéciaux, mais préserver <br/> et les balises de formatage (<b>, </b>, <i>, </i>, etc.)
            text = str(text)
            
            # Liste des balises HTML à préserver
            html_tags = [
                ("<br/>", "___BR___"),
                ("<br>", "___BR___"),
                ("<b>", "___B_OPEN___"),
                ("</b>", "___B_CLOSE___"),
                ("<i>", "___I_OPEN___"),
                ("</i>", "___I_CLOSE___"),
                ("<u>", "___U_OPEN___"),
                ("</u>", "___U_CLOSE___"),
                ("<strong>", "___STRONG_OPEN___"),
                ("</strong>", "___STRONG_CLOSE___"),
                ("<em>", "___EM_OPEN___"),
                ("</em>", "___EM_CLOSE___"),
            ]
            
            # Remplacer temporairement les balises HTML par des placeholders
            for tag, placeholder in html_tags:
                text = text.replace(tag, placeholder)
            
            # Échapper les autres caractères HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Restaurer les balises HTML
            for tag, placeholder in html_tags:
                text = text.replace(placeholder, tag)
            
            # En mode brouillon, mettre en rouge
            if mode == "brouillon":
                return f'<font color="#FF0000">{text}</font>'
            else:
                return text
        
        # Titre de section
        logger.info("🔍 Début de la génération de la section 'II. PRESENTATION DE LA PERFORMANCE PAR PROGRAMME'")
        story.append(Paragraph("II. PRESENTATION DE LA PERFORMANCE PAR PROGRAMME", section_title_style))
        story.append(Spacer(1, 0.5 * cm))
        logger.info(f"📝 Titre de section ajouté à la story. Nombre d'éléments dans story: {len(story)}")
        
        # Charger les programmes depuis la base de données
        if session:
            logger.info("✅ Session de base de données disponible")
            try:
                from app.models.personnel import Programme
                from app.models.performance import ObjectifPerformance, TypeObjectif, IndicateurPerformance
                from app.models.budget import SigobeExecution
                from sqlmodel import select, and_, or_
                from sqlalchemy import func, extract
                from app.services.report_data_loader import ReportDataLoader
                
                logger.info("🔍 Chargement des programmes pour la présentation de la performance...")
                
                # Récupérer tous les programmes
                programmes_query = select(Programme).order_by(Programme.code, Programme.libelle)
                programmes_list = session.exec(programmes_query).all()
                logger.info(f"📊 {len(programmes_list)} programmes trouvés pour la présentation de la performance")
                
                if not programmes_list:
                    logger.warning("⚠️ Aucun programme trouvé dans la base de données")
                    story.append(Paragraph("Aucun programme trouvé dans la base de données.", body_style))
                
                numero_programme = 1
                for programme in programmes_list:
                    try:
                        logger.info(f"📊 Traitement du programme {numero_programme}: {programme.libelle} (ID: {programme.id})")
                        
                        # Titre du programme
                        programme_title = f"II.{numero_programme}. Programme {numero_programme}: {programme.libelle}"
                        logger.info(f"📝 Ajout du titre du programme: {programme_title}")
                        story.append(Paragraph(programme_title, programme_title_style))
                        story.append(Spacer(1, 0.3 * cm))
                        logger.info(f"📝 Titre ajouté. Nombre d'éléments dans story: {len(story)}")
                        
                        # Charger l'objectif global du programme (sans filtre sur période)
                        objectif_global = None
                        objectif_global_query = select(ObjectifPerformance).where(
                            and_(
                                ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value,
                                ObjectifPerformance.programme_id == programme.id
                            )
                        ).order_by(ObjectifPerformance.code, ObjectifPerformance.id)
                        objectifs_globaux = session.exec(objectif_global_query).all()
                        
                        if objectifs_globaux:
                            objectif_global = objectifs_globaux[0]  # Prendre le premier objectif global
                            objectif_global_text = f"Objectif global : {objectif_global.titre if hasattr(objectif_global, 'titre') else str(objectif_global)}"
                            logger.info(f"📝 Objectif global trouvé: {objectif_global_text}")
                            story.append(Paragraph(objectif_global_text, objectif_global_style))
                            story.append(Spacer(1, 0.3 * cm))
                            logger.info(f"📝 Objectif global ajouté. Nombre d'éléments dans story: {len(story)}")
                        else:
                            logger.warning(f"⚠️ Aucun objectif global trouvé pour le programme {programme.libelle}")
                        
                        # Charger les actions depuis SigobeExecution
                        actions_query = select(SigobeExecution.actions).distinct().where(
                            and_(
                                SigobeExecution.annee == annee_debut,
                                SigobeExecution.programmes.ilike(f"%{programme.libelle}%"),
                                SigobeExecution.actions.isnot(None),
                                SigobeExecution.actions != ""
                            )
                        )
                        actions_list = [a for a in session.exec(actions_query).all() if a and a.strip()]
                        logger.info(f"📊 {len(actions_list)} actions trouvées pour le programme {programme.libelle}")
                        if actions_list:
                            logger.info(f"📋 Liste des actions: {actions_list[:5]}...")  # Afficher les 5 premières
                        
                        # Charger les objectifs spécifiques et indicateurs (filtrés par période)
                        objectifs_specifiques = []
                        if objectif_global:
                            os_query = select(ObjectifPerformance).where(
                                and_(
                                    ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value,
                                    ObjectifPerformance.objectif_global_id == objectif_global.id,
                                    ObjectifPerformance.periode.ilike(f"%{annee_debut}%")
                                )
                            ).order_by(ObjectifPerformance.code, ObjectifPerformance.id)
                            objectifs_specifiques = session.exec(os_query).all()
                            logger.info(f"📊 {len(objectifs_specifiques)} objectifs spécifiques trouvés pour le programme {programme.libelle}")
                            if objectifs_specifiques:
                                for os in objectifs_specifiques:
                                    os_titre = os.titre if hasattr(os, 'titre') else str(os)
                                    logger.info(f"   - OS: {os_titre}")
                        else:
                            logger.warning(f"⚠️ Aucun objectif global pour le programme {programme.libelle}, donc pas d'objectifs spécifiques")
                        
                        # Créer le tableau
                        logger.info(f"🔨 Création du tableau pour le programme {programme.libelle}...")
                        tableau_num = cls.get_next_tableau_numero()
                        tableau_title = f"Tableau {tableau_num} : Cohérence entre objectifs et actions du programme {numero_programme} « {programme.libelle} »"
                        logger.info(f"📝 Ajout du titre du tableau: {tableau_title}")
                        story.append(Paragraph(tableau_title, tableau_title_style))
                        story.append(Spacer(1, 0.2 * cm))
                        logger.info(f"📝 Titre du tableau ajouté. Nombre d'éléments dans story: {len(story)}")
                        
                        # Construire les données du tableau
                        table_data = []
                        logger.info(f"🔨 Construction des données du tableau...")
                        
                        # En-tête
                        header_style = ParagraphStyle(
                            "HeaderStyle",
                            parent=body_style,
                            fontName="Helvetica-Bold",
                            fontSize=9,
                            leading=11,
                            alignment=1,  # CENTER
                            textColor=RAPBaseGenerator.DARK_TEXT
                        )
                        
                        table_data.append([
                            Paragraph("N°", header_style),
                            Paragraph("ACTIONS", header_style),
                            Paragraph("OBJECTIFS SPECIFIQUES", header_style),
                            Paragraph("INDICATEURS", header_style)
                        ])
                        
                        # Construire les lignes de données avec structure hiérarchique :
                        # - Une ligne principale par ACTION (avec cellules fusionnées)
                        #   - Pour chaque ACTION, plusieurs OS (sous-lignes)
                        #     - Pour chaque OS, plusieurs indicateurs (sous-sous-lignes)
                        numero_ligne = 1
                        logger.info(f"🔨 Construction des lignes de données hiérarchiques: {len(actions_list)} actions, {len(objectifs_specifiques)} OS")
                        
                        # Dictionnaire pour suivre les fusions de cellules
                        spans = []
                        current_row = 1  # Commence après l'en-tête (row 0)
                        
                        if actions_list:
                            logger.info(f"✅ Création de structure hiérarchique : Action -> OS -> Indicateurs")
                            for action_idx, action in enumerate(actions_list):
                                action_text = action if action else "............................."
                                action_formatted = format_text_for_mode(action_text)
                                action_para = Paragraph(action_formatted, ParagraphStyle(
                                    "Action",
                                    parent=body_style,
                                    fontSize=9,
                                    leading=11,
                                    alignment=0,  # LEFT
                                ))
                                
                                # Compter le nombre total de lignes pour cette action (OS + indicateurs)
                                total_rows_for_action = 0
                                os_data = []  # Stocker les données OS et indicateurs
                                
                                for os in objectifs_specifiques:
                                    os_code = os.code if hasattr(os, 'code') and os.code else ""
                                    os_titre = os.titre if hasattr(os, 'titre') else str(os)
                                    os_text = f"{os_code}: {os_titre}" if os_code else os_titre
                                    os_formatted = format_text_for_mode(os_text)
                                    os_para = Paragraph(os_formatted, ParagraphStyle(
                                        "ObjectifSpecifique",
                                        parent=body_style,
                                        fontSize=9,
                                        leading=11,
                                        alignment=0,  # LEFT
                                    ))
                                    
                                    # Charger les indicateurs pour cet objectif spécifique
                                    ind_query = select(IndicateurPerformance).where(
                                        and_(
                                            IndicateurPerformance.objectif_id == os.id,
                                            IndicateurPerformance.actif == True,
                                            IndicateurPerformance.annee == annee_debut
                                        )
                                    ).order_by(IndicateurPerformance.nom)
                                    indicateurs = session.exec(ind_query).all()
                                    
                                    if indicateurs:
                                        # Si on a des indicateurs, créer une ligne par indicateur
                                        for ind_idx, ind in enumerate(indicateurs):
                                            ind_nom = ind.nom if hasattr(ind, 'nom') else str(ind)
                                            ind_formatted = format_text_for_mode(ind_nom)
                                            ind_para = Paragraph(ind_formatted, ParagraphStyle(
                                                "Indicateur",
                                                parent=body_style,
                                                fontSize=9,
                                                leading=11,
                                                alignment=0,  # LEFT
                                            ))
                                            os_data.append({
                                                'os_id': os.id,  # ID de l'OS pour la détection
                                                'os_para': os_para,
                                                'ind_para': ind_para,
                                                'is_first_row_for_os': ind_idx == 0  # Première ligne de cet OS
                                            })
                                            total_rows_for_action += 1
                                    else:
                                        # Si pas d'indicateur, créer une ligne OS avec indicateur vide
                                        ind_formatted = format_text_for_mode(".............................")
                                        ind_para = Paragraph(ind_formatted, ParagraphStyle(
                                            "Indicateur",
                                            parent=body_style,
                                            fontSize=9,
                                            leading=11,
                                            alignment=0,  # LEFT
                                        ))
                                        os_data.append({
                                            'os_id': os.id,  # ID de l'OS pour la détection
                                            'os_para': os_para,
                                            'ind_para': ind_para,
                                            'is_first_row_for_os': True  # C'est la seule ligne pour cet OS
                                        })
                                        total_rows_for_action += 1
                                
                                # Si pas d'OS, créer une ligne vide pour l'action
                                if not os_data:
                                    os_formatted = format_text_for_mode(".............................")
                                    os_para = Paragraph(os_formatted, ParagraphStyle(
                                        "ObjectifSpecifique",
                                        parent=body_style,
                                        fontSize=9,
                                        leading=11,
                                        alignment=0,  # LEFT
                                    ))
                                    ind_formatted = format_text_for_mode(".............................")
                                    ind_para = Paragraph(ind_formatted, ParagraphStyle(
                                        "Indicateur",
                                        parent=body_style,
                                        fontSize=9,
                                        leading=11,
                                        alignment=0,  # LEFT
                                    ))
                                    os_data.append({
                                        'os_para': os_para,
                                        'ind_para': ind_para,
                                        'is_os_row': True
                                    })
                                    total_rows_for_action = 1
                                
                                # Créer les lignes pour cette action
                                action_row_start = current_row
                                last_os_id = None
                                os_span_start = None
                                
                                for os_item in os_data:
                                    # Détecter si c'est un nouveau OS (en comparant les IDs)
                                    is_new_os = (last_os_id is None or last_os_id != os_item['os_id'])
                                    
                                    if is_new_os:
                                        # Fermer le span OS précédent si nécessaire
                                        if os_span_start is not None and current_row > os_span_start:
                                            spans.append(('SPAN', (2, os_span_start), (2, current_row - 1)))  # Fusionner colonne OS (colonne 2)
                                        
                                        # Nouveau span OS
                                        os_span_start = current_row
                                        last_os_id = os_item['os_id']
                                    
                                    # Ajouter la ligne
                                    table_data.append([
                                        str(numero_ligne) if current_row == action_row_start else "",  # N° seulement sur la première ligne
                                        action_para if current_row == action_row_start else "",  # Action seulement sur la première ligne
                                        os_item['os_para'] if os_item['is_first_row_for_os'] else "",  # OS seulement sur la première ligne de cet OS
                                        os_item['ind_para']
                                    ])
                                    
                                    current_row += 1
                                
                                # Fermer le dernier span OS
                                if os_span_start is not None and current_row > os_span_start:
                                    spans.append(('SPAN', (2, os_span_start), (2, current_row - 1)))  # Fusionner colonne OS (colonne 2)
                                
                                # Fusionner les colonnes N° et ACTION pour toutes les lignes de cette action
                                if total_rows_for_action > 1:
                                    spans.append(('SPAN', (0, action_row_start), (0, action_row_start + total_rows_for_action - 1)))  # Fusionner colonne N° (colonne 0)
                                    spans.append(('SPAN', (1, action_row_start), (1, action_row_start + total_rows_for_action - 1)))  # Fusionner colonne ACTION (colonne 1)
                                
                                numero_ligne += 1
                            
                            logger.info(f"✅ {len(table_data) - 1} lignes créées avec structure hiérarchique")
                        else:
                            logger.info(f"⚠️ Aucune action trouvée, utilisation du mode 'une ligne par objectif spécifique'")
                            # Si aucune action, créer une ligne par objectif spécifique
                            if objectifs_specifiques:
                                logger.info(f"✅ Création de lignes pour {len(objectifs_specifiques)} objectifs spécifiques")
                                for os in objectifs_specifiques:
                                    os_code = os.code if hasattr(os, 'code') and os.code else ""
                                    os_titre = os.titre if hasattr(os, 'titre') else str(os)
                                    os_text = f"{os_code}: {os_titre}" if os_code else os_titre
                                    
                                    # Charger les indicateurs pour cet objectif spécifique
                                    ind_query = select(IndicateurPerformance).where(
                                        and_(
                                            IndicateurPerformance.objectif_id == os.id,
                                            IndicateurPerformance.actif == True,
                                            IndicateurPerformance.annee == annee_debut
                                        )
                                    ).order_by(IndicateurPerformance.nom)
                                    indicateurs = session.exec(ind_query).all()
                                    
                                    indicateurs_list = [ind.nom if hasattr(ind, 'nom') else str(ind) for ind in indicateurs]
                                    ind_text = "<br/>".join(indicateurs_list) if indicateurs_list else "............................."
                                    
                                    # Formater avec format_text_for_mode
                                    action_formatted = format_text_for_mode(".............................")
                                    os_formatted = format_text_for_mode(os_text)
                                    ind_formatted = format_text_for_mode(ind_text)
                                    
                                    # Créer les Paragraph
                                    action_para = Paragraph(action_formatted, ParagraphStyle(
                                        "Action",
                                        parent=body_style,
                                        fontSize=9,
                                        leading=11,
                                        alignment=0,  # LEFT
                                    ))
                                    
                                    os_para = Paragraph(os_formatted, ParagraphStyle(
                                        "ObjectifSpecifique",
                                        parent=body_style,
                                        fontSize=9,
                                        leading=11,
                                        alignment=0,  # LEFT
                                    ))
                                    
                                    ind_para = Paragraph(ind_formatted, ParagraphStyle(
                                        "Indicateur",
                                        parent=body_style,
                                        fontSize=9,
                                        leading=11,
                                        alignment=0,  # LEFT
                                    ))
                                    
                                    table_data.append([
                                        str(numero_ligne),
                                        action_para,
                                        os_para,
                                        ind_para
                                    ])
                                    
                                    numero_ligne += 1
                                logger.info(f"✅ {numero_ligne - 1} lignes créées pour les objectifs spécifiques")
                            else:
                                logger.warning(f"⚠️ Aucun objectif spécifique trouvé, création d'une ligne vide")
                                # Si ni actions ni OS, créer une ligne vide
                                table_data.append([
                                    "1",
                                    Paragraph(format_text_for_mode("............................."), body_style),
                                    Paragraph(format_text_for_mode("............................."), body_style),
                                    Paragraph(format_text_for_mode("............................."), body_style)
                                ])
                        
                        # Largeurs des colonnes
                        available_width = width - left_margin - right_margin
                        col_widths = [
                            1.5 * cm,  # N°
                            4 * cm,  # ACTIONS
                            5 * cm,  # OBJECTIFS SPECIFIQUES
                            available_width - 1.5 * cm - 4 * cm - 5 * cm  # INDICATEURS
                        ]
                        logger.info(f"🔨 Création du LongTable avec {len(table_data)} lignes (dont 1 en-tête)")
                        
                        # Créer le LongTable
                        table = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
                        logger.info(f"✅ LongTable créé avec succès")
                        
                        # Style du tableau
                        table_style = [
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
                            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                            ("VALIGN", (0, 1), (-1, -1), "TOP"),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 1), (-1, -1), 9),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Centrer la colonne N°
                            ("VALIGN", (0, 1), (0, -1), "MIDDLE"),  # Centrer verticalement la colonne N°
                            ("VALIGN", (1, 1), (1, -1), "MIDDLE"),  # Centrer verticalement la colonne ACTION (pour les cellules fusionnées)
                            ("VALIGN", (2, 1), (2, -1), "MIDDLE"),  # Centrer verticalement la colonne OS (pour les cellules fusionnées)
                            ("VALIGN", (3, 1), (3, -1), "MIDDLE"),  # Centrer verticalement la colonne INDICATEURS
                        ]
                        
                        # Ajouter les fusions de cellules (spans) si on a des actions
                        if actions_list and spans:
                            table_style.extend(spans)
                            logger.info(f"✅ {len(spans)} fusions de cellules ajoutées")
                        
                        table.setStyle(TableStyle(table_style))
                        logger.info(f"✅ Style appliqué au tableau pour le programme {programme.libelle} avec {len(table_data)} lignes (dont 1 en-tête)")
                        logger.info(f"📝 Ajout du tableau à la story. Nombre d'éléments avant: {len(story)}")
                        story.append(table)
                        story.append(Spacer(1, 0.3 * cm))
                        logger.info(f"✅ Tableau ajouté à la story. Nombre d'éléments après: {len(story)}")
                        
                        # Commentaire (placeholder pour l'instant)
                        if mode != "final":
                            story.append(Paragraph("<font color=\"#FF0000\"><b>Commentaire :</b>..........................</font>", body_style))
                        else:
                            # En mode final, ne pas afficher le placeholder
                            pass
                        
                        story.append(Spacer(1, 0.5 * cm))
                        
                        # ============================================================
                        # Tableau : Bilan de la performance du programme
                        # ============================================================
                        logger.info(f"🔨 Création du tableau 'Bilan de la performance' pour le programme {programme.libelle}...")
                        tableau_bilan_num = cls.get_next_tableau_numero()
                        tableau_bilan_title = f"Tableau {tableau_bilan_num} : Bilan de la performance du programme {numero_programme} « {programme.libelle} »"
                        logger.info(f"📝 Ajout du titre du tableau: {tableau_bilan_title}")
                        story.append(Paragraph(tableau_bilan_title, tableau_title_style))
                        story.append(Spacer(1, 0.2 * cm))
                        
                        # Construire les données du tableau "Bilan de la performance"
                        table_bilan_data = []
                        
                        # En-tête du tableau avec fusion pour "Bilan {annee_debut}"
                        # Structure : 7 colonnes (0-6), 2 lignes d'en-tête
                        # Ligne 0: "Bilan {annee_debut}" fusionné horizontalement sur colonnes 3-5 (ligne 0 seulement)
                        # Ligne 1: Sous-en-têtes "Prévision (a)", "Réalisation (b)", "Ecart (c) c = b-a" dans les colonnes 3, 4, 5
                        programme_col_header = f"Programme-{numero_programme}: {programme.libelle}"
                        header_row_1 = [
                            Paragraph(format_text_for_mode(programme_col_header), header_style),  # Colonne 0
                            Paragraph(format_text_for_mode("Indicateurs de performance"), header_style),  # Colonne 1
                            Paragraph(format_text_for_mode(f"Réalisation (RAP) {annee_debut - 1}"), header_style),  # Colonne 2
                            Paragraph(format_text_for_mode(f"Bilan {annee_debut}"), header_style),  # Colonne 3 - fusionné horizontalement sur colonnes 3-5, ligne 0 seulement
                            "",  # Colonne 4 - vide car fusionnée avec Bilan
                            "",  # Colonne 5 - vide car fusionnée avec Bilan
                            Paragraph(format_text_for_mode("Observations"), header_style),  # Colonne 6 - en-tête séparé
                        ]
                        header_row_2 = [
                            "",  # Colonne 0 - fusionné avec la ligne 1
                            "",  # Colonne 1 - fusionné avec la ligne 1
                            "",  # Colonne 2 - fusionné avec la ligne 1
                            Paragraph(format_text_for_mode("Prévision<br/>(a)"), header_style),  # Colonne 3 - sous-en-tête de Bilan
                            Paragraph(format_text_for_mode("Réalisation<br/>(b)"), header_style),  # Colonne 4 - sous-en-tête de Bilan
                            Paragraph(format_text_for_mode("Ecart (c)<br/>c = b-a"), header_style),  # Colonne 5 - sous-en-tête de Bilan
                            ""  # Colonne 6 - fusionné avec la ligne 1 (Observations)
                        ]
                        table_bilan_data.append(header_row_1)
                        table_bilan_data.append(header_row_2)
                        
                        # Remplir les données avec les objectifs spécifiques et leurs indicateurs
                        if objectifs_specifiques:
                            for os in objectifs_specifiques:
                                os_code = os.code if hasattr(os, 'code') and os.code else ""
                                os_titre = os.titre if hasattr(os, 'titre') else str(os)
                                os_text = f"{os_code}: {os_titre}" if os_code else os_titre
                                
                                # Charger les indicateurs pour cet OS (filtrés par année)
                                ind_query = select(IndicateurPerformance).where(
                                    and_(
                                        IndicateurPerformance.objectif_id == os.id,
                                        IndicateurPerformance.actif == True,
                                        IndicateurPerformance.annee == annee_debut
                                    )
                                ).order_by(IndicateurPerformance.nom)
                                indicateurs = session.exec(ind_query).all()
                                
                                if indicateurs:
                                    # Une ligne par indicateur
                                    for ind in indicateurs:
                                        # Réalisation année précédente (annee_debut - 1)
                                        realisation_prev = "-"
                                        if annee_debut > 1:
                                            ind_prev_query = select(IndicateurPerformance).where(
                                                and_(
                                                    IndicateurPerformance.objectif_id == os.id,
                                                    IndicateurPerformance.nom == ind.nom,
                                                    IndicateurPerformance.annee == annee_debut - 1
                                                )
                                            )
                                            ind_prev = session.exec(ind_prev_query).first()
                                            if ind_prev and ind_prev.valeur_actuelle is not None:
                                                unite = ind_prev.unite or ""
                                                if unite.lower() in ["%", "pourcentage"]:
                                                    realisation_prev = f"{float(ind_prev.valeur_actuelle):.0f}"
                                                else:
                                                    realisation_prev = f"{float(ind_prev.valeur_actuelle):.2f}"
                                        
                                        # Prévision (valeur_cible)
                                        prevision = "............................."
                                        if ind.valeur_cible is not None:
                                            unite = ind.unite or ""
                                            if unite.lower() in ["%", "pourcentage"]:
                                                prevision = f"{float(ind.valeur_cible):.0f}"
                                            else:
                                                prevision = f"{float(ind.valeur_cible):.2f}"
                                        
                                        # Réalisation (valeur_actuelle)
                                        realisation = "............................."
                                        if ind.valeur_actuelle is not None:
                                            unite = ind.unite or ""
                                            if unite.lower() in ["%", "pourcentage"]:
                                                realisation = f"{float(ind.valeur_actuelle):.0f}"
                                            else:
                                                realisation = f"{float(ind.valeur_actuelle):.2f}"
                                        
                                        # Ecart = réalisation - prévision
                                        ecart = "............................."
                                        if ind.valeur_actuelle is not None and ind.valeur_cible is not None:
                                            ecart_value = float(ind.valeur_actuelle) - float(ind.valeur_cible)
                                            unite = ind.unite or ""
                                            if unite.lower() in ["%", "pourcentage"]:
                                                ecart = f"{ecart_value:.0f}"
                                            else:
                                                ecart = f"{ecart_value:.2f}"
                                        
                                        # Observations
                                        observations = "............................."
                                        if ind.valeur_actuelle is not None and ind.valeur_cible is not None:
                                            if float(ind.valeur_actuelle) >= float(ind.valeur_cible):
                                                observations = "Cible atteinte"
                                            else:
                                                observations = "Cible non atteinte"
                                        
                                        # Formater selon le mode
                                        if mode == "brouillon":
                                            os_formatted = format_text_for_mode(os_text)
                                            ind_formatted = format_text_for_mode(ind.nom)
                                            realisation_prev_formatted = format_text_for_mode(realisation_prev)
                                            prevision_formatted = format_text_for_mode(prevision)
                                            realisation_formatted = format_text_for_mode(realisation)
                                            ecart_formatted = format_text_for_mode(ecart)
                                            observations_formatted = format_text_for_mode(observations)
                                        else:
                                            os_formatted = os_text
                                            ind_formatted = ind.nom
                                            realisation_prev_formatted = realisation_prev
                                            prevision_formatted = prevision
                                            realisation_formatted = realisation
                                            ecart_formatted = ecart
                                            observations_formatted = observations
                                        
                                        table_bilan_data.append([
                                            Paragraph(os_formatted, body_style) if ind == indicateurs[0] else "",  # Colonne 0: OS seulement sur la première ligne
                                            Paragraph(ind_formatted, body_style),  # Colonne 1: Indicateurs
                                            Paragraph(realisation_prev_formatted, body_style_centered),  # Colonne 2: Réalisation RAP année-1 (centré)
                                            Paragraph(prevision_formatted, body_style_centered),  # Colonne 3: Prévision (a) (centré)
                                            Paragraph(realisation_formatted, body_style_centered),  # Colonne 4: Réalisation (b) (centré)
                                            Paragraph(ecart_formatted, body_style_centered),  # Colonne 5: Ecart (c) (centré)
                                            Paragraph(observations_formatted, body_style_centered)  # Colonne 6: Observations (centré)
                                        ])
                                else:
                                    # Pas d'indicateur, créer une ligne avec placeholder
                                    os_formatted = format_text_for_mode(os_text) if mode == "brouillon" else os_text
                                    table_bilan_data.append([
                                        Paragraph(os_formatted, body_style),  # Colonne 0: OS
                                        Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),  # Colonne 1: Indicateurs
                                        Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 2: Réalisation RAP (centré)
                                        Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered),  # Colonne 3: Prévision (centré)
                                        Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered),  # Colonne 4: Réalisation (centré)
                                        Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered),  # Colonne 5: Ecart (centré)
                                        Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered)  # Colonne 6: Observations (centré)
                                    ])
                        else:
                            # Pas d'objectifs spécifiques
                            table_bilan_data.append([
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),  # Colonne 0: OS
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),  # Colonne 1: Indicateurs
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 2: Réalisation RAP (centré)
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered),  # Colonne 3: Prévision (centré)
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered),  # Colonne 4: Réalisation (centré)
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered),  # Colonne 5: Ecart (centré)
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style_centered)  # Colonne 6: Observations (centré)
                            ])
                        
                        # Largeurs des colonnes (7 colonnes au total : 0-6)
                        available_width_bilan = width - left_margin - right_margin
                        col_widths_bilan = [
                            5 * cm,  # Colonne 0: Programme-X (OS) - augmentée
                            6 * cm,  # Colonne 1: Indicateurs de performance - augmentée
                            2.8 * cm,  # Colonne 2: Réalisation (RAP) année précédente - légèrement augmentée
                            2 * cm,  # Colonne 3: Prévision (a) - sous-colonne de Bilan - légèrement augmentée
                            2 * cm,  # Colonne 4: Réalisation (b) - sous-colonne de Bilan - légèrement augmentée
                            2 * cm,  # Colonne 5: Ecart (c) - sous-colonne de Bilan - légèrement augmentée
                            available_width_bilan - 5 * cm - 6 * cm - 2.8 * cm - 2 * cm - 2 * cm - 2 * cm  # Colonne 6: Observations - réduite
                        ]
                        
                        # Créer le LongTable (2 lignes d'en-tête seulement)
                        table_bilan = LongTable(table_bilan_data, colWidths=col_widths_bilan, repeatRows=2, splitByRow=1)
                        
                        # Style du tableau (2 lignes d'en-tête)
                        table_bilan_style = [
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
                            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
                            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 1), 9),
                            ("ALIGN", (0, 2), (1, -1), "LEFT"),  # Colonnes 0-1 alignées à gauche
                            ("ALIGN", (2, 2), (-1, -1), "CENTER"),  # Colonnes 2-6 centrées horizontalement
                            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 2), (-1, -1), 9),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("VALIGN", (0, 2), (0, -1), "MIDDLE"),  # Centrer verticalement la colonne 0 (Programme-X)
                            ("VALIGN", (1, 2), (1, -1), "MIDDLE"),  # Centrer verticalement la colonne 1 (Indicateurs)
                            ("VALIGN", (2, 2), (2, -1), "MIDDLE"),  # Centrer verticalement la colonne 2 (Réalisation RAP)
                            ("VALIGN", (3, 2), (3, -1), "MIDDLE"),  # Centrer verticalement la colonne 3 (Prévision)
                            ("VALIGN", (4, 2), (4, -1), "MIDDLE"),  # Centrer verticalement la colonne 4 (Réalisation)
                            ("VALIGN", (5, 2), (5, -1), "MIDDLE"),  # Centrer verticalement la colonne 5 (Ecart)
                            ("VALIGN", (6, 2), (6, -1), "MIDDLE"),  # Centrer verticalement la colonne 6 (Observations)
                        ]
                        
                        # Fusions pour l'en-tête (2 lignes d'en-tête seulement)
                        # Fusionner "Bilan {annee_debut}" horizontalement sur les colonnes 3-5, ligne 0 seulement
                        table_bilan_style.append(('SPAN', (3, 0), (5, 0)))  # Fusionner "Bilan {annee_debut}" sur les colonnes 3-5, ligne 0 seulement
                        # Fusionner les autres colonnes sur les lignes 0-1 (2 lignes d'en-tête)
                        table_bilan_style.append(('SPAN', (0, 0), (0, 1)))  # Fusionner colonne 0 (Programme-X) sur lignes 0-1
                        table_bilan_style.append(('SPAN', (1, 0), (1, 1)))  # Fusionner colonne 1 (Indicateurs) sur lignes 0-1
                        table_bilan_style.append(('SPAN', (2, 0), (2, 1)))  # Fusionner colonne 2 (Réalisation RAP) sur lignes 0-1
                        table_bilan_style.append(('SPAN', (6, 0), (6, 1)))  # Fusionner colonne 6 (Observations) sur lignes 0-1
                        
                        # Fusionner les cellules OS pour les indicateurs du même OS
                        current_os_row = None
                        for row_idx in range(2, len(table_bilan_data)):  # Commencer à partir de la ligne 2 (après les 2 lignes d'en-tête)
                            if table_bilan_data[row_idx][0]:  # Si la cellule OS n'est pas vide
                                if current_os_row is not None and current_os_row < row_idx - 1:
                                    # Fusionner les cellules OS précédentes
                                    table_bilan_style.append(('SPAN', (0, current_os_row), (0, row_idx - 1)))
                                current_os_row = row_idx
                        
                        # Fusionner la dernière cellule OS si nécessaire
                        if current_os_row is not None and current_os_row < len(table_bilan_data) - 1:
                            table_bilan_style.append(('SPAN', (0, current_os_row), (0, len(table_bilan_data) - 1)))
                        
                        table_bilan.setStyle(TableStyle(table_bilan_style))
                        story.append(table_bilan)
                        story.append(Spacer(1, 0.3 * cm))
                        logger.info(f"✅ Tableau 'Bilan de la performance' ajouté pour le programme {programme.libelle}")
                        
                        # ============================================================
                        # Analyse des résultats du tableau
                        # ============================================================
                        story.append(Spacer(1, 0.5 * cm))
                        
                        # Commentaire avant l'analyse (depuis le modal)
                        if programme_commentaire and programme_commentaire.strip():
                            # Échapper les caractères spéciaux HTML
                            commentaire_escaped = programme_commentaire.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            # Convertir les retours à la ligne en <br/>
                            commentaire_html = commentaire_escaped.replace("\n", "<br/>")
                            # Formater selon le mode
                            if mode == "brouillon":
                                commentaire_formatted = format_text_for_mode(commentaire_html)
                            else:
                                commentaire_formatted = commentaire_html
                            story.append(Paragraph(commentaire_formatted, body_style))
                            story.append(Spacer(1, 0.3 * cm))
                        
                        # Titre de l'analyse
                        analyse_title = "L'analyse des résultats se présente comme suit :"
                        story.append(Paragraph(analyse_title, objectif_global_style))
                        story.append(Spacer(1, 0.3 * cm))
                        
                        # Collecter tous les indicateurs uniques du programme pour l'analyse
                        indicateurs_analyse = []
                        if objectifs_specifiques:
                            for os in objectifs_specifiques:
                                ind_query = select(IndicateurPerformance).where(
                                    and_(
                                        IndicateurPerformance.objectif_id == os.id,
                                        IndicateurPerformance.actif == True,
                                        IndicateurPerformance.annee == annee_debut
                                    )
                                ).order_by(IndicateurPerformance.nom)
                                indicateurs_os = session.exec(ind_query).all()
                                for ind in indicateurs_os:
                                    # Éviter les doublons
                                    if ind.id not in [i.id for i in indicateurs_analyse]:
                                        indicateurs_analyse.append(ind)
                        
                        # Style pour les éléments indentés de l'analyse
                        analyse_indented_style = ParagraphStyle(
                            "AnalyseIndented",
                            parent=body_style,
                            leftIndent=1 * cm,  # Indentation de 1 cm
                            spaceBefore=0,
                            spaceAfter=2
                        )
                        
                        # Générer l'analyse pour chaque indicateur
                        if indicateurs_analyse:
                            ind_num = 1
                            for ind in indicateurs_analyse:
                                # Titre de l'indicateur avec puce "-"
                                ind_title = f"- <b>Indicateur {ind_num} : {ind.nom}</b>"
                                story.append(Paragraph(format_text_for_mode(ind_title) if mode == "brouillon" else ind_title, body_style))
                                story.append(Spacer(1, 0.1 * cm))
                                
                                # Liste à puces indentées pour les détails de l'indicateur
                                analyse_items = []
                                
                                # Définition de l'indicateur
                                definition = ind.description or "Définition non disponible"
                                analyse_items.append(f"• <b>Définition de l'indicateur :</b> {definition}")
                                
                                # Source de données
                                source = ind.source_donnees or "Source non disponible"
                                analyse_items.append(f"• <b>Source de données :</b> {source}")
                                
                                # Mode de calcul
                                mode_calcul = ind.methode or ind.formule_calcul or "Mode de calcul non disponible"
                                analyse_items.append(f"• <b>Mode de calcul :</b> {mode_calcul}")
                                
                                # Valeurs cibles
                                valeurs_cibles = ind.valeurs_cibles_futures
                                if not valeurs_cibles:
                                    # Construire les valeurs cibles à partir des champs disponibles
                                    cibles_list = []
                                    if ind.valeur_cible is not None:
                                        unite = ind.unite or ""
                                        cible_str = f"{float(ind.valeur_cible):.0f}" if unite.lower() in ["%", "pourcentage"] else f"{float(ind.valeur_cible):.2f}"
                                        cibles_list.append(f"{cible_str}{unite} en {annee_debut}")
                                    if ind.cible_N_plus_1 is not None:
                                        unite = ind.unite or ""
                                        cible_str = f"{float(ind.cible_N_plus_1):.0f}" if unite.lower() in ["%", "pourcentage"] else f"{float(ind.cible_N_plus_1):.2f}"
                                        cibles_list.append(f"{cible_str}{unite} en {annee_debut + 1}")
                                    if ind.cible_N_plus_2 is not None:
                                        unite = ind.unite or ""
                                        cible_str = f"{float(ind.cible_N_plus_2):.0f}" if unite.lower() in ["%", "pourcentage"] else f"{float(ind.cible_N_plus_2):.2f}"
                                        cibles_list.append(f"{cible_str}{unite} en {annee_debut + 2}")
                                    valeurs_cibles = ", ".join(cibles_list) if cibles_list else "Valeurs cibles non disponibles"
                                analyse_items.append(f"• <b>Valeurs cibles :</b> {valeurs_cibles}")
                                
                                # Analyse de l'indicateur
                                analyse_text = "............................."
                                if ind.valeur_actuelle is not None and ind.valeur_cible is not None:
                                    unite = ind.unite or ""
                                    valeur_actuelle_str = f"{float(ind.valeur_actuelle):.0f}" if unite.lower() in ["%", "pourcentage"] else f"{float(ind.valeur_actuelle):.2f}"
                                    valeur_cible_str = f"{float(ind.valeur_cible):.0f}" if unite.lower() in ["%", "pourcentage"] else f"{float(ind.valeur_cible):.2f}"
                                    
                                    # Construire le texte d'analyse
                                    if ind.nb_activites is not None:
                                        # Cas spécial pour les indicateurs avec nombre d'activités (ex: taux de réalisation du PTA)
                                        # Calculer le nombre total d'actions prévues à partir du taux de réalisation
                                        nb_total_prevu = None
                                        if ind.valeur_actuelle is not None and float(ind.valeur_actuelle) > 0:
                                            # Si valeur_actuelle est un pourcentage, calculer le total
                                            if unite.lower() in ["%", "pourcentage"]:
                                                nb_total_prevu = int((ind.nb_activites * 100) / float(ind.valeur_actuelle))
                                            else:
                                                # Si ce n'est pas un pourcentage, utiliser valeur_cible comme référence
                                                if ind.valeur_cible is not None:
                                                    nb_total_prevu = int((ind.nb_activites * float(ind.valeur_cible)) / float(ind.valeur_actuelle)) if float(ind.valeur_actuelle) > 0 else ind.nb_activites
                                        
                                        if nb_total_prevu is not None:
                                            analyse_text = f"Au 31 décembre {annee_debut}, le Programme a réalisé {ind.nb_activites} actions sur les {nb_total_prevu} actions prévues dans son PTA"
                                        else:
                                            analyse_text = f"Au 31 décembre {annee_debut}, le Programme a réalisé {ind.nb_activites} actions"
                                        
                                        if ind.valeur_actuelle is not None:
                                            analyse_text += f", soit un taux de {valeur_actuelle_str}{unite}"
                                            if float(ind.valeur_actuelle) >= float(ind.valeur_cible):
                                                analyse_text += " (la cible a été atteinte)."
                                            else:
                                                analyse_text += " (la cible n'a pas été atteinte)."
                                    else:
                                        # Analyse standard
                                        analyse_text = f"Au 31 décembre {annee_debut}, la valeur réalisée est de {valeur_actuelle_str}{unite}"
                                        if float(ind.valeur_actuelle) >= float(ind.valeur_cible):
                                            analyse_text += f" pour une cible de {valeur_cible_str}{unite} (la cible a été atteinte)."
                                        else:
                                            analyse_text += f" pour une cible de {valeur_cible_str}{unite} (la cible n'a pas été atteinte)."
                                
                                analyse_items.append(f"• <b>Analyse de l'indicateur :</b> {analyse_text}")
                                
                                # Ajouter tous les éléments de l'analyse avec indentation
                                for item in analyse_items:
                                    item_formatted = format_text_for_mode(item) if mode == "brouillon" else item
                                    story.append(Paragraph(item_formatted, analyse_indented_style))
                                
                                story.append(Spacer(1, 0.3 * cm))
                                ind_num += 1
                        else:
                            # Aucun indicateur disponible
                            no_data_text = "Aucun indicateur disponible pour l'analyse."
                            story.append(Paragraph(format_text_for_mode(no_data_text) if mode == "brouillon" else no_data_text, body_style))
                        
                        # ============================================================
                        # Tableau "Cadre de performance du programme X"
                        # ============================================================
                        logger.info(f"🔨 Création du tableau 'Cadre de performance' pour le programme {programme.libelle}...")
                        logger.info(f"📊 objectifs_specifiques disponibles: {len(objectifs_specifiques) if objectifs_specifiques else 0}")
                        
                        story.append(Spacer(1, 0.5 * cm))
                        
                        # Titre du tableau
                        try:
                            tableau_cadre_num = cls.get_next_tableau_numero()
                            tableau_cadre_title = f"Tableau {tableau_cadre_num} : Cadre de performance du programme {numero_programme} « {programme.libelle} »"
                            logger.info(f"📝 Ajout du titre du tableau: {tableau_cadre_title}")
                            logger.info(f"📝 Vérification tableau_title_style: {tableau_title_style}")
                            titre_para = Paragraph(tableau_cadre_title, tableau_title_style)
                            logger.info(f"📝 Paragraph créé pour le titre. Type: {type(titre_para)}")
                            logger.info(f"📝 Nombre d'éléments dans story AVANT ajout du titre: {len(story)}")
                            story.append(titre_para)
                            logger.info(f"📝 Titre ajouté à la story. Nombre d'éléments APRÈS: {len(story)}")
                            logger.info(f"📝 Vérification: Le dernier élément de la story est: {type(story[-1]).__name__}")
                            story.append(Spacer(1, 0.2 * cm))
                            logger.info(f"📝 Spacer ajouté. Nombre d'éléments: {len(story)}")
                        except Exception as e:
                            logger.error(f"❌ Erreur lors de l'ajout du titre du tableau 'Cadre de performance': {e}", exc_info=True)
                            import traceback
                            logger.error(f"❌ Traceback complet: {traceback.format_exc()}")
                            # Ajouter un message d'erreur dans le PDF
                            story.append(Paragraph(f"Erreur lors de la génération du titre du tableau 'Cadre de performance': {str(e)}", body_style))
                        
                        # Préparer les données du tableau "Cadre de performance"
                        table_cadre_data = []
                        logger.info(f"📊 Initialisation de table_cadre_data. Nombre d'objectifs spécifiques: {len(objectifs_specifiques) if objectifs_specifiques else 0}")
                        
                        # En-tête du tableau (2 lignes)
                        # Ligne 0 : En-têtes principaux
                        table_cadre_data.append([
                            Paragraph(format_text_for_mode(f"Programme {numero_programme}: {programme.libelle}") if mode == "brouillon" else f"Programme {numero_programme}: {programme.libelle}", header_style),  # Colonne 0
                            Paragraph(format_text_for_mode("Indicateurs de performance"), header_style),  # Colonne 1
                            Paragraph(format_text_for_mode(f"Réalisation {annee_debut - 2}"), header_style),  # Colonne 2
                            Paragraph(format_text_for_mode(f"Affichage année {annee_debut - 1}"), header_style),  # Colonne 3
                            Paragraph(format_text_for_mode("Projections"), header_style),  # Colonne 4 - fusionné sur 3 colonnes
                            "",  # Colonne 5 - fusionné avec colonne 4
                            ""   # Colonne 6 - fusionné avec colonne 4
                        ])
                        
                        # Ligne 1 : Sous-en-têtes pour les projections
                        table_cadre_data.append([
                            "",  # Colonne 0 - fusionné avec ligne 0
                            "",  # Colonne 1 - fusionné avec ligne 0
                            "",  # Colonne 2 - fusionné avec ligne 0
                            "",  # Colonne 3 - fusionné avec ligne 0
                            Paragraph(format_text_for_mode(str(annee_debut)), header_style),  # Colonne 4
                            Paragraph(format_text_for_mode(str(annee_debut + 1)), header_style),  # Colonne 5
                            Paragraph(format_text_for_mode(str(annee_debut + 2)), header_style)  # Colonne 6
                        ])
                        
                        # Remplir les données du tableau
                        logger.info(f"📊 Vérification objectifs_specifiques: {objectifs_specifiques is not None}, longueur: {len(objectifs_specifiques) if objectifs_specifiques else 0}")
                        if objectifs_specifiques:
                            logger.info(f"📊 Traitement de {len(objectifs_specifiques)} objectifs spécifiques pour le tableau 'Cadre de performance'")
                            for os in objectifs_specifiques:
                                os_text = os.titre if hasattr(os, 'titre') else str(os)
                                logger.info(f"📊 Traitement de l'OS: {os_text}")
                                
                                # Charger les indicateurs pour cet OS (filtrés par année)
                                ind_query = select(IndicateurPerformance).where(
                                    and_(
                                        IndicateurPerformance.objectif_id == os.id,
                                        IndicateurPerformance.actif == True,
                                        IndicateurPerformance.annee == annee_debut
                                    )
                                ).order_by(IndicateurPerformance.nom)
                                indicateurs = session.exec(ind_query).all()
                                logger.info(f"📊 {len(indicateurs)} indicateurs trouvés pour l'OS '{os_text}'")
                                
                                if indicateurs:
                                    # Une ligne par indicateur
                                    for ind in indicateurs:
                                        # Réalisation année annee_debut - 2
                                        realisation_2024 = "-"
                                        if annee_debut - 2 >= 2000:
                                            ind_2024_query = select(IndicateurPerformance).where(
                                                and_(
                                                    IndicateurPerformance.objectif_id == os.id,
                                                    IndicateurPerformance.nom == ind.nom,
                                                    IndicateurPerformance.annee == annee_debut - 2
                                                )
                                            )
                                            ind_2024 = session.exec(ind_2024_query).first()
                                            if ind_2024 and ind_2024.valeur_actuelle is not None:
                                                unite = ind_2024.unite or ""
                                                if unite.lower() in ["%", "pourcentage"]:
                                                    realisation_2024 = f"{float(ind_2024.valeur_actuelle):.0f}{unite}"
                                                else:
                                                    realisation_2024 = f"{float(ind_2024.valeur_actuelle):.2f}{unite}"
                                        
                                        # Affichage année annee_debut - 1
                                        affichage_2025 = "-"
                                        if annee_debut - 1 >= 2000:
                                            ind_2025_query = select(IndicateurPerformance).where(
                                                and_(
                                                    IndicateurPerformance.objectif_id == os.id,
                                                    IndicateurPerformance.nom == ind.nom,
                                                    IndicateurPerformance.annee == annee_debut - 1
                                                )
                                            )
                                            ind_2025 = session.exec(ind_2025_query).first()
                                            if ind_2025 and ind_2025.valeur_actuelle is not None:
                                                unite = ind_2025.unite or ""
                                                if unite.lower() in ["%", "pourcentage"]:
                                                    affichage_2025 = f"{float(ind_2025.valeur_actuelle):.0f}{unite}"
                                                else:
                                                    affichage_2025 = f"{float(ind_2025.valeur_actuelle):.2f}{unite}"
                                        
                                        # Projections : annee_debut, annee_debut+1, annee_debut+2
                                        projection_2026 = "-"
                                        projection_2027 = "-"
                                        projection_2028 = "-"
                                        
                                        # Pour annee_debut : utiliser valeur_cible de l'indicateur de l'année annee_debut
                                        if ind.valeur_cible is not None:
                                            unite = ind.unite or ""
                                            if unite.lower() in ["%", "pourcentage"]:
                                                projection_2026 = f"{float(ind.valeur_cible):.0f}{unite}"
                                            else:
                                                projection_2026 = f"{float(ind.valeur_cible):.2f}{unite}"
                                        
                                        # Pour annee_debut+1 : utiliser cible_N_plus_1
                                        if ind.cible_N_plus_1 is not None:
                                            unite = ind.unite or ""
                                            if unite.lower() in ["%", "pourcentage"]:
                                                projection_2027 = f"{float(ind.cible_N_plus_1):.0f}{unite}"
                                            else:
                                                projection_2027 = f"{float(ind.cible_N_plus_1):.2f}{unite}"
                                        
                                        # Pour annee_debut+2 : utiliser cible_N_plus_2
                                        if ind.cible_N_plus_2 is not None:
                                            unite = ind.unite or ""
                                            if unite.lower() in ["%", "pourcentage"]:
                                                projection_2028 = f"{float(ind.cible_N_plus_2):.0f}{unite}"
                                            else:
                                                projection_2028 = f"{float(ind.cible_N_plus_2):.2f}{unite}"
                                        
                                        # Formater selon le mode
                                        if mode == "brouillon":
                                            os_formatted = format_text_for_mode(os_text) if ind == indicateurs[0] else ""
                                            ind_formatted = format_text_for_mode(ind.nom)
                                            realisation_2024_formatted = format_text_for_mode(realisation_2024)
                                            affichage_2025_formatted = format_text_for_mode(affichage_2025)
                                            projection_2026_formatted = format_text_for_mode(projection_2026)
                                            projection_2027_formatted = format_text_for_mode(projection_2027)
                                            projection_2028_formatted = format_text_for_mode(projection_2028)
                                        else:
                                            os_formatted = os_text if ind == indicateurs[0] else ""
                                            ind_formatted = ind.nom
                                            realisation_2024_formatted = realisation_2024
                                            affichage_2025_formatted = affichage_2025
                                            projection_2026_formatted = projection_2026
                                            projection_2027_formatted = projection_2027
                                            projection_2028_formatted = projection_2028
                                        
                                        table_cadre_data.append([
                                            Paragraph(os_formatted, body_style) if ind == indicateurs[0] else "",  # Colonne 0: OS seulement sur la première ligne
                                            Paragraph(ind_formatted, body_style),  # Colonne 1: Indicateurs
                                            Paragraph(realisation_2024_formatted, body_style_centered),  # Colonne 2: Réalisation annee_debut-2
                                            Paragraph(affichage_2025_formatted, body_style_centered),  # Colonne 3: Affichage annee_debut-1
                                            Paragraph(projection_2026_formatted, body_style_centered),  # Colonne 4: Projection annee_debut
                                            Paragraph(projection_2027_formatted, body_style_centered),  # Colonne 5: Projection annee_debut+1
                                            Paragraph(projection_2028_formatted, body_style_centered)  # Colonne 6: Projection annee_debut+2
                                        ])
                                else:
                                    # Pas d'indicateur, créer une ligne avec placeholder
                                    os_formatted = format_text_for_mode(os_text) if mode == "brouillon" else os_text
                                    table_cadre_data.append([
                                        Paragraph(os_formatted, body_style),  # Colonne 0: OS
                                        Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),  # Colonne 1: Indicateurs
                                        Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 2
                                        Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 3
                                        Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 4
                                        Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 5
                                        Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered)  # Colonne 6
                                    ])
                        else:
                            # Pas d'objectifs spécifiques
                            table_cadre_data.append([
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),  # Colonne 0: OS
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),  # Colonne 1: Indicateurs
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 2
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 3
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 4
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),  # Colonne 5
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered)  # Colonne 6
                            ])
                        
                        # Largeurs des colonnes (7 colonnes au total : 0-6)
                        available_width_cadre = width - left_margin - right_margin
                        # Calculer la largeur uniforme pour les 3 colonnes de projections
                        projections_total_width = available_width_cadre - 5.5 * cm - 7 * cm - 2 * cm - 2 * cm
                        projection_col_width = projections_total_width / 3
                        col_widths_cadre = [
                            5.5 * cm,  # Colonne 0: Programme-X (OS) - augmentée
                            7 * cm,  # Colonne 1: Indicateurs de performance - augmentée
                            2 * cm,  # Colonne 2: Réalisation annee_debut-2 - réduite
                            2 * cm,  # Colonne 3: Affichage annee_debut-1 - réduite
                            projection_col_width,  # Colonne 4: Projection annee_debut - largeur uniforme
                            projection_col_width,  # Colonne 5: Projection annee_debut+1 - largeur uniforme
                            projection_col_width  # Colonne 6: Projection annee_debut+2 - largeur uniforme
                        ]
                        logger.info(f"📊 Largeurs des colonnes du tableau 'Cadre de performance': {[f'{w/cm:.2f}cm' for w in col_widths_cadre]}")
                        logger.info(f"📊 Largeur totale disponible: {available_width_cadre/cm:.2f}cm, Largeur utilisée: {sum(col_widths_cadre)/cm:.2f}cm")
                        
                        # Créer le LongTable (2 lignes d'en-tête)
                        logger.info(f"📊 Création du LongTable avec {len(table_cadre_data)} lignes (dont 2 lignes d'en-tête)")
                        if len(table_cadre_data) < 2:
                            logger.warning(f"⚠️ Le tableau 'Cadre de performance' a moins de 2 lignes! Ajout d'une ligne vide par défaut.")
                            # Ajouter au moins une ligne de données si le tableau est vide
                            table_cadre_data.append([
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),
                                Paragraph(format_text_for_mode(".............................") if mode == "brouillon" else ".............................", body_style),
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered),
                                Paragraph(format_text_for_mode("-") if mode == "brouillon" else "-", body_style_centered)
                            ])
                        
                        table_cadre = LongTable(table_cadre_data, colWidths=col_widths_cadre, repeatRows=2, splitByRow=1)
                        
                        # Style du tableau (2 lignes d'en-tête)
                        table_cadre_style = [
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
                            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
                            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 1), 9),
                            ("ALIGN", (0, 2), (1, -1), "LEFT"),  # Colonnes 0-1 alignées à gauche
                            ("ALIGN", (2, 2), (-1, -1), "CENTER"),  # Colonnes 2-6 centrées horizontalement
                            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 2), (-1, -1), 9),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("VALIGN", (0, 2), (0, -1), "MIDDLE"),  # Centrer verticalement la colonne 0 (Programme-X)
                            ("VALIGN", (1, 2), (1, -1), "MIDDLE"),  # Centrer verticalement la colonne 1 (Indicateurs)
                            ("VALIGN", (2, 2), (2, -1), "MIDDLE"),  # Centrer verticalement la colonne 2
                            ("VALIGN", (3, 2), (3, -1), "MIDDLE"),  # Centrer verticalement la colonne 3
                            ("VALIGN", (4, 2), (4, -1), "MIDDLE"),  # Centrer verticalement la colonne 4
                            ("VALIGN", (5, 2), (5, -1), "MIDDLE"),  # Centrer verticalement la colonne 5
                            ("VALIGN", (6, 2), (6, -1), "MIDDLE"),  # Centrer verticalement la colonne 6
                        ]
                        
                        # Fusions pour l'en-tête (2 lignes d'en-tête)
                        # Fusionner "Projections" horizontalement sur les colonnes 4-6, ligne 0 seulement
                        table_cadre_style.append(('SPAN', (4, 0), (6, 0)))  # Fusionner "Projections" sur les colonnes 4-6, ligne 0 seulement
                        # Fusionner les autres colonnes sur les lignes 0-1 (2 lignes d'en-tête)
                        table_cadre_style.append(('SPAN', (0, 0), (0, 1)))  # Fusionner colonne 0 (Programme-X) sur lignes 0-1
                        table_cadre_style.append(('SPAN', (1, 0), (1, 1)))  # Fusionner colonne 1 (Indicateurs) sur lignes 0-1
                        table_cadre_style.append(('SPAN', (2, 0), (2, 1)))  # Fusionner colonne 2 (Réalisation) sur lignes 0-1
                        table_cadre_style.append(('SPAN', (3, 0), (3, 1)))  # Fusionner colonne 3 (Affichage) sur lignes 0-1
                        
                        # Fusionner les cellules OS pour les indicateurs du même OS
                        current_os_row_cadre = None
                        for row_idx in range(2, len(table_cadre_data)):  # Commencer à partir de la ligne 2 (après les 2 lignes d'en-tête)
                            if table_cadre_data[row_idx][0]:  # Si la cellule OS n'est pas vide
                                if current_os_row_cadre is not None and current_os_row_cadre < row_idx - 1:
                                    # Fusionner les cellules OS précédentes
                                    table_cadre_style.append(('SPAN', (0, current_os_row_cadre), (0, row_idx - 1)))
                                current_os_row_cadre = row_idx
                        
                        # Fusionner la dernière cellule OS si nécessaire
                        if current_os_row_cadre is not None and current_os_row_cadre < len(table_cadre_data) - 1:
                            table_cadre_style.append(('SPAN', (0, current_os_row_cadre), (0, len(table_cadre_data) - 1)))
                        
                        try:
                            table_cadre.setStyle(TableStyle(table_cadre_style))
                            logger.info(f"📊 Style appliqué au tableau. Nombre de lignes: {len(table_cadre_data)}")
                            logger.info(f"📊 Nombre d'éléments dans story AVANT ajout du tableau: {len(story)}")
                            story.append(table_cadre)
                            logger.info(f"📊 Nombre d'éléments dans story APRÈS ajout du tableau: {len(story)}")
                            story.append(Spacer(1, 0.3 * cm))
                            logger.info(f"📊 Nombre d'éléments dans story APRÈS ajout du Spacer: {len(story)}")
                            logger.info(f"✅ Tableau 'Cadre de performance' ajouté avec succès pour le programme {programme.libelle}")
                            logger.info(f"📊 Vérification: Les {len(story)} derniers éléments de la story sont:")
                            for i, elem in enumerate(story[-5:], start=len(story)-4):
                                logger.info(f"   [{i}] {type(elem).__name__}")
                        except Exception as e:
                            logger.error(f"❌ Erreur lors de l'ajout du tableau 'Cadre de performance': {e}", exc_info=True)
                            # Ajouter un message d'erreur dans le PDF
                            story.append(Paragraph(f"Erreur lors de la génération du tableau 'Cadre de performance': {str(e)}", body_style))
                        
                        # Commentaire après le tableau "Cadre de performance"
                        if cadre_performance_commentaire and cadre_performance_commentaire.strip():
                            story.append(Spacer(1, 0.2 * cm))
                            # Échapper les caractères spéciaux HTML
                            commentaire_cadre_escaped = cadre_performance_commentaire.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            # Convertir les retours à la ligne en <br/>
                            commentaire_cadre_html = commentaire_cadre_escaped.replace("\n", "<br/>")
                            # Formater selon le mode
                            if mode == "brouillon":
                                commentaire_cadre_formatted = format_text_for_mode(f"Commentaire : {commentaire_cadre_html}")
                            else:
                                commentaire_cadre_formatted = f"Commentaire : {commentaire_cadre_html}"
                            story.append(Paragraph(commentaire_cadre_formatted, body_style))
                            story.append(Spacer(1, 0.3 * cm))
                        
                        story.append(Spacer(1, 0.5 * cm))
                        logger.info(f"✅ Programme {numero_programme} ({programme.libelle}) traité avec succès. Nombre d'éléments dans story: {len(story)}")
                        
                        numero_programme += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Erreur lors du traitement du programme {programme.libelle}: {e}", exc_info=True)
                        continue
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement des programmes: {e}", exc_info=True)
        else:
            # Si pas de session, afficher un message
            logger.warning("⚠️ Aucune session de base de données disponible pour charger les programmes")
            story.append(Paragraph("Aucune donnée disponible.", body_style))
        
        # Vérifier que la story contient du contenu
        logger.info(f"📊 Vérification finale: {len(story)} éléments dans la story")
        if len(story) <= 1:  # Seulement le titre de section
            logger.warning("⚠️ Aucun contenu généré pour la section 'Performance par programme'")
            story.append(Paragraph("Aucune donnée disponible pour cette section.", body_style))
        else:
            logger.info(f"✅ La story contient {len(story)} éléments (titre + contenu)")
        
        # Créer le SimpleDocTemplate
        logger.info(f"🔨 Création du SimpleDocTemplate...")
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        from app.services.rapport_cadre_performance_generator import CPLayoutDrawer
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer
        
        footer_margin = bottom_margin
        footer_height = 1.5 * cm
        
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            CPLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RAPLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            CPLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RAPLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin
            )
        
        # Construire le PDF
        logger.info(f"📄 Génération du PDF pour 'Performance par programme' avec {len(story)} éléments dans la story")
        # Vérifier que le tableau "Cadre de performance" est bien dans la story
        tableau_cadre_found = False
        tableau_cadre_count = 0
        for i, elem in enumerate(story):
            if hasattr(elem, 'getContent') or (hasattr(elem, '__class__') and 'Table' in str(type(elem))):
                # C'est probablement un tableau
                logger.info(f"📊 Élément {i} de la story: {type(elem).__name__}")
                if 'LongTable' in str(type(elem)):
                    tableau_cadre_count += 1
            if isinstance(elem, Paragraph):
                # Essayer différentes méthodes pour obtenir le texte
                para_text = ""
                try:
                    if hasattr(elem, 'text'):
                        para_text = str(elem.text)
                    elif hasattr(elem, 'getPlainText'):
                        para_text = elem.getPlainText()
                    elif hasattr(elem, '_text'):
                        para_text = str(elem._text)
                    else:
                        # Essayer d'accéder au contenu brut
                        para_text = str(elem)
                except:
                    para_text = str(elem)
                
                if "Cadre de performance" in para_text:
                    tableau_cadre_found = True
                    logger.info(f"📊 Titre du tableau 'Cadre de performance' trouvé à l'index {i} de la story: {para_text[:100]}")
        if not tableau_cadre_found:
            logger.warning("⚠️ Le titre du tableau 'Cadre de performance' n'a pas été trouvé dans la story!")
        logger.info(f"📊 Nombre total de LongTable trouvés dans la story: {tableau_cadre_count}")
        
        try:
            doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
            logger.info("✅ doc.build() terminé avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur lors de doc.build(): {e}", exc_info=True)
            raise
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        from PyPDF2 import PdfReader
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        logger.info(f"✅ PDF 'Performance par programme' généré avec {num_pages} pages (de {start_page} à {final_page - 1})")
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("cp_performance_par_programme", start_page)
        
        buffer.seek(0)
        return buffer, final_page


# ============================================================================
# ORCHESTRATEUR PRINCIPAL - GÉNÉRATION COMPLÈTE DU PDF
# ============================================================================

class CPPDFGenerator(CPBaseGenerator):
    """
    Orchestrateur principal pour la génération du Rapport du Cadre de Performance (CP). 
    
    Cette classe coordonne la génération de toutes les pages du rapport :
    1. Couverture
    2. Sommaire (à implémenter)
    3. Liste des tableaux (à implémenter)
    4. Liste des figures (à implémenter)
    5. Contenu principal (à implémenter selon les besoins)
    
    Réutilise les classes RAPLayoutDrawer et RAPContentDrawer pour
    les pages communes (couverture, sommaire, listes).
    """
    
    @classmethod
    def generate_pdf(cls, data: dict[str, Any], session=None) -> BytesIO:
        """
        Génère le PDF complet du Rapport du Cadre de Performance (CP).
        
        Args:
            data: Dictionnaire contenant toutes les données du rapport
            session: Session de base de données (optionnel)
        
        Returns:
            BytesIO contenant le PDF généré
        """
        logger.info("📄 Début de la génération du Rapport du Cadre de Performance (CP)...")
        
        # Initialiser les données et la session
        # Les données doivent être définies dans la classe de base pour être accessibles
        # par toutes les classes qui héritent (CPLayoutDrawer, CPContentDrawer, etc.)
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator
        RAPBaseGenerator.data = data
        RAPBaseGenerator._db_session = session
        # Aussi définir dans les classes CP pour compatibilité
        CPBaseGenerator.data = data
        CPBaseGenerator._db_session = session
        cls.data = data
        cls._db_session = session
        
        # Réinitialiser les compteurs
        cls.reset_tableau_counter(1)
        cls.reset_figure_counter(1)
        cls._page_positions = {}
        cls._current_rendering_page = 1
        
        # Dimensions de la page (format paysage A4)
        width, height = landscape(A4)
        
        # ====================================================================
        # 1. GÉNÉRER LA COUVERTURE
        # ====================================================================
        logger.info("📄 Génération de la couverture...")
        cover_buffer = BytesIO()
        cover_pdf = canvas.Canvas(cover_buffer, pagesize=landscape(A4))
        CPLayoutDrawer.draw_cover_page(cover_pdf, width, height)
        cover_pdf.save()
        cover_buffer.seek(0)
        cover_reader = PdfReader(cover_buffer)
        
        logger.info("✅ Couverture générée avec succès")
        
        # ====================================================================
        # 2. GÉNÉRER LE SOMMAIRE TEMPORAIRE (sera régénéré après avec les bonnes pages)
        # ====================================================================
        logger.info("📄 Génération du sommaire temporaire...")
        sommaire_temp_buffer = BytesIO()
        sommaire_temp_pdf = canvas.Canvas(sommaire_temp_buffer, pagesize=landscape(A4))
        # Le sommaire sera régénéré après avec les bonnes pages
        sommaire_temp_pdf.save()
        sommaire_temp_buffer.seek(0)
        
        # Compter les pages du sommaire temporaire pour calculer le start_page du contenu
        sommaire_temp_reader = PdfReader(sommaire_temp_buffer)
        nb_pages_sommaire = len(sommaire_temp_reader.pages)
        
        # ====================================================================
        # 3. GÉNÉRER LA LISTE DES TABLEAUX
        # ====================================================================
        logger.info("📄 Génération de la liste des tableaux...")
        liste_tableaux_buffer = BytesIO()
        liste_tableaux_pdf = canvas.Canvas(liste_tableaux_buffer, pagesize=landscape(A4))
        # Le sommaire est à la page 2, donc la liste des tableaux commence après
        # Couverture (1 page) + Sommaire (nb_pages_sommaire pages) + 1
        liste_tableaux_start_page = 1 + nb_pages_sommaire + 1
        # Note: pdf_reader_complet sera disponible après la génération du contenu principal
        # Pour l'instant, on passe None et on utilisera les positions enregistrées
        next_page = CPContentDrawer.draw_liste_tableaux(
            liste_tableaux_pdf, width, height, liste_tableaux_start_page,
            pdf_reader_complet=None, nb_pages_sommaire=0
        )
        liste_tableaux_pdf.save()
        liste_tableaux_buffer.seek(0)
        liste_tableaux_reader = PdfReader(liste_tableaux_buffer)
        
        # Enregistrer la position de la liste des tableaux
        from app.services.rapport_annuel_performance_generator_modular import RAPPageManager
        RAPPageManager.register_page_position("liste_tableaux", liste_tableaux_start_page)
        
        # ====================================================================
        # 4. GÉNÉRER LA LISTE DES ANNEXES
        # ====================================================================
        logger.info("📄 Génération de la liste des annexes...")
        liste_annexes_buffer = BytesIO()
        liste_annexes_pdf = canvas.Canvas(liste_annexes_buffer, pagesize=landscape(A4))
        # La liste des annexes commence après la liste des tableaux
        liste_annexes_start_page = next_page
        next_page = CPContentDrawer.draw_liste_annexes(
            liste_annexes_pdf, width, height, liste_annexes_start_page,
            pdf_reader_complet=None, nb_pages_sommaire=0
        )
        liste_annexes_pdf.save()
        liste_annexes_buffer.seek(0)
        liste_annexes_reader = PdfReader(liste_annexes_buffer)
        
        # Enregistrer la position de la liste des annexes
        RAPPageManager.register_page_position("liste_annexes", liste_annexes_start_page)
        
        # ====================================================================
        # 5. GÉNÉRER LE CONTENU (sections, etc.)
        # ====================================================================
        logger.info("📄 Génération du contenu principal...")
        
        # Générer le cadre global de performance
        cadre_global_start_page = next_page
        cadre_global_buffer, next_page = CPContentDrawer.draw_cadre_global(
            width=width,
            height=height,
            start_page=cadre_global_start_page
        )
        cadre_global_reader = PdfReader(cadre_global_buffer)
        
        # Générer la section "II. PRESENTATION DE LA PERFORMANCE PAR PROGRAMME"
        performance_programme_start_page = next_page
        performance_programme_buffer, next_page = CPContentDrawer.draw_performance_par_programme(
            width=width,
            height=height,
            start_page=performance_programme_start_page
        )
        performance_programme_reader = PdfReader(performance_programme_buffer)
        
        # Fusionner tous les contenus dans un seul reader
        content_writer = PdfWriter()
        for page in cadre_global_reader.pages:
            content_writer.add_page(page)
        # Ajouter les pages de la section "Performance par programme"
        logger.info(f"📎 Ajout de {len(performance_programme_reader.pages)} pages de 'Performance par programme' au contenu")
        for page in performance_programme_reader.pages:
            content_writer.add_page(page)
        
        content_buffer = BytesIO()
        content_writer.write(content_buffer)
        content_buffer.seek(0)
        content_reader = PdfReader(content_buffer)
        logger.info(f"📊 Total de pages dans content_reader: {len(content_reader.pages)} (cadre global: {len(cadre_global_reader.pages)}, performance: {len(performance_programme_reader.pages)})")
        
        # ====================================================================
        # 6. CRÉER LE PDF COMPLET TEMPORAIRE POUR RECHERCHER LES PAGES
        # ====================================================================
        # Fusionner temporairement pour pouvoir rechercher les pages dans le PDF complet
        temp_writer = PdfWriter()
        temp_writer.add_page(cover_reader.pages[0])
        for page in sommaire_temp_reader.pages:
            temp_writer.add_page(page)
        for page in liste_tableaux_reader.pages:
            temp_writer.add_page(page)
        for page in liste_annexes_reader.pages:
            temp_writer.add_page(page)
        for page in content_reader.pages:
            temp_writer.add_page(page)
        
        temp_buffer = BytesIO()
        temp_writer.write(temp_buffer)
        temp_buffer.seek(0)
        pdf_reader_complet = PdfReader(temp_buffer)
        
        # ====================================================================
        # 7. RÉGÉNÉRER LE SOMMAIRE FINAL AVEC LES POSITIONS CORRECTES
        # ====================================================================
        logger.info("🔄 Régénération finale du sommaire avec les positions correctes de toutes les sections...")
        sommaire_buffer = BytesIO()
        sommaire_pdf = canvas.Canvas(sommaire_buffer, pagesize=landscape(A4))
        CPContentDrawer.draw_table_of_contents(
            sommaire_pdf, width, height, pdf_reader_complet=pdf_reader_complet, nb_pages_sommaire=nb_pages_sommaire
        )
        sommaire_pdf.save()
        sommaire_buffer.seek(0)
        sommaire_reader = PdfReader(sommaire_buffer)
        
        # ====================================================================
        # 8. FUSIONNER TOUS LES PDFs DANS LE BON ORDRE
        # ====================================================================
        logger.info("📎 Fusion de tous les PDFs...")
        final_buffer = BytesIO()
        writer = PdfWriter()
        
        # 1. Couverture (page 1)
        writer.add_page(cover_reader.pages[0])
        
        # 2. Sommaire (page 2+)
        for page in sommaire_reader.pages:
            writer.add_page(page)
        
        # 3. Liste des tableaux
        for page in liste_tableaux_reader.pages:
            writer.add_page(page)
        
        # 4. Liste des annexes
        for page in liste_annexes_reader.pages:
            writer.add_page(page)
        
        # 5. Contenu (sections, etc.)
        for page in content_reader.pages:
            writer.add_page(page)
        
        # 6. ANNEXES : Fiches signalétiques des indicateurs par programme
        logger.info("📄 Génération des annexes : Fiches signalétiques des indicateurs...")
        if session:
            try:
                from app.models.personnel import Programme
                from sqlmodel import select
                
                # Récupérer tous les programmes
                programmes_query = select(Programme).order_by(Programme.code, Programme.libelle)
                programmes_list = session.exec(programmes_query).all()
                logger.info(f"📊 {len(programmes_list)} programmes trouvés pour générer les fiches signalétiques")
                
                # Récupérer les paramètres nécessaires
                ministere = data.get("ministere", "Ministère du Patrimoine, de la Culture, de l'Artisanat et du Tourisme")
                annee_debut = data.get("annee_debut", 2026)
                annee_fin = data.get("annee_fin", annee_debut + 1)
                mode = data.get("mode", "brouillon")
                
                # Calculer la page de départ pour les annexes (après le contenu)
                annexe_start_page = 1 + len(sommaire_reader.pages) + len(liste_tableaux_reader.pages) + len(liste_annexes_reader.pages) + len(content_reader.pages)
                
                # Générer les fiches signalétiques pour chaque programme
                numero_programme = 1
                for programme in programmes_list:
                    # Calculer le numéro d'annexe : (programme_num - 1) * 2 + 1
                    # Programme 1 -> Annexe 1, Programme 2 -> Annexe 3, Programme 3 -> Annexe 5
                    annexe_num = (numero_programme - 1) * 2 + 1
                    
                    logger.info(f"📄 Génération des fiches signalétiques pour le programme {numero_programme} '{programme.libelle}' (Annexe {annexe_num}, page {annexe_start_page})...")
                    try:
                        fiche_buffer, final_page = CPFicheSignaletiqueDrawer.generate_fiches_signaletiques_programme(
                            programme=programme,
                            ministere=ministere,
                            annee_debut=annee_debut,
                            session=session,
                            mode=mode,
                            start_page=annexe_start_page,
                            numero_programme=numero_programme,
                            annexe_num=annexe_num
                        )
                        
                        # Ajouter les pages des fiches au PDF final
                        fiche_reader = PdfReader(fiche_buffer)
                        logger.info(f"📎 Ajout de {len(fiche_reader.pages)} pages de fiches signalétiques pour le programme '{programme.libelle}'")
                        for page in fiche_reader.pages:
                            writer.add_page(page)
                        
                        # Mettre à jour la page de départ pour l'annexe de modification
                        annexe_start_page = final_page
                        
                        # Générer l'annexe de modification après les fiches signalétiques
                        annexe_modif_num = (numero_programme - 1) * 2 + 2  # Annexe 2, 4, 6, ...
                        logger.info(f"📄 Génération de l'annexe de modification pour le programme {numero_programme} '{programme.libelle}' (Annexe {annexe_modif_num}, page {annexe_start_page})...")
                        try:
                            # Récupérer les modifications d'architecture depuis les données
                            modifications_architecture = data.get("modifications_architecture", [])
                            if isinstance(modifications_architecture, str):
                                import json
                                try:
                                    modifications_architecture = json.loads(modifications_architecture)
                                except:
                                    modifications_architecture = []
                            
                            modif_buffer, final_page_modif = CPFicheSignaletiqueDrawer.generate_annexe_modification_programme(
                                programme=programme,
                                annee_debut=annee_debut,
                                annee_fin=annee_fin,
                                session=session,
                                mode=mode,
                                start_page=annexe_start_page,
                                numero_programme=numero_programme,
                                annexe_num=annexe_modif_num,
                                modifications=modifications_architecture
                            )
                            
                            # Ajouter les pages de l'annexe de modification au PDF final
                            modif_reader = PdfReader(modif_buffer)
                            logger.info(f"📎 Ajout de {len(modif_reader.pages)} pages de l'annexe de modification pour le programme '{programme.libelle}'")
                            for page in modif_reader.pages:
                                writer.add_page(page)
                            
                            # Mettre à jour la page de départ pour le prochain programme
                            annexe_start_page = final_page_modif
                            logger.info(f"✅ Annexes générées pour le programme {numero_programme} '{programme.libelle}' (pages {annexe_start_page - len(fiche_reader.pages) - len(modif_reader.pages)} à {annexe_start_page - 1})")
                        except Exception as e:
                            logger.error(f"❌ Erreur lors de la génération de l'annexe de modification pour le programme {numero_programme} '{programme.libelle}': {e}", exc_info=True)
                            # Continuer même si l'annexe de modification échoue
                            annexe_start_page = final_page
                        
                        numero_programme += 1
                    except Exception as e:
                        logger.error(f"❌ Erreur lors de la génération des fiches signalétiques pour le programme {numero_programme} '{programme.libelle}': {e}", exc_info=True)
                        numero_programme += 1
                        continue
            except Exception as e:
                logger.error(f"❌ Erreur lors de la génération des annexes (fiches signalétiques): {e}", exc_info=True)
        else:
            logger.warning("⚠️ Aucune session disponible, les fiches signalétiques ne seront pas générées")
        
        writer.write(final_buffer)
        final_buffer.seek(0)
        
        logger.info("✅ PDF du Rapport du Cadre de Performance généré avec succès")
        
        return final_buffer


# ============================================================================
# CLASSE POUR DESSINER LA FICHE SIGNALÉTIQUE D'INDICATEUR
# ============================================================================

class CPFicheSignaletiqueDrawer(CPBaseGenerator):
    """
    Classe pour dessiner une fiche signalétique d'indicateur selon le modèle fourni.
    
    La fiche contient :
    - Titre "FICHE SIGNALETIQUE D'INDICATEUR" dans une bannière verte
    - Section 1: Ministère
    - Section 2: Programme
    - Section 3: Objectif spécifique
    - Section 4: Libellé de l'indicateur
    - Section 5: Définition de l'indicateur
    - Section 6: Nature de l'indicateur (Qualitatif/Quantitatif)
    - Section 7: Méthode de calcul
    - Section 8: Sources de données (Mode de collecte, Provenance, Responsable)
    - Section 9: Valeur de l'indicateur (Unité, Périodicité, Dernière valeur, Cibles)
    - Footer: Responsable de Programme, Nom et prénoms, Signature
    """
    
    # Couleurs
    LIGHT_GREEN = colors.HexColor("#90EE90")  # Bannière verte
    DARK_TEXT = colors.HexColor("#000000")
    GRAY_LINE = colors.HexColor("#808080")
    
    @classmethod
    def draw_checkbox(cls, pdf: canvas.Canvas, x: float, y: float, size: float = None, checked: bool = False) -> None:
        from reportlab.lib.units import cm
        if size is None:
            size = 0.3 * cm
        """
        Dessine une case à cocher.
        
        Args:
            pdf: Le canvas PDF
            x: Position X
            y: Position Y
            size: Taille de la case
            checked: Si True, dessine une croix dans la case
        """
        pdf.saveState()
        pdf.setStrokeColor(cls.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.rect(x, y, size, size, stroke=1, fill=0)
        
        if checked:
            # Dessiner une croix
            pdf.setLineWidth(1.5)
            margin = size * 0.2
            pdf.line(x + margin, y + margin, x + size - margin, y + size - margin)
            pdf.line(x + size - margin, y + margin, x + margin, y + size - margin)
        
        pdf.restoreState()
    
    @classmethod
    def draw_fiche_signaletique(
        cls,
        pdf: canvas.Canvas,
        indicateur,
        programme,
        objectif_specifique,
        ministere: str,
        annee_debut: int,
        width: float = None,
        height: float = None,
        mode: str = "brouillon",
        start_y: float = None,
        available_height: float = None,
        ajustement_hauteur_cadre: float = 0
    ) -> None:
        """
        Dessine une fiche signalétique d'indicateur complète.
        
        Cette méthode utilise FicheSignaletiqueGenerator pour le dessin réel.
        """
        from app.services.fiche_signaletique_generator import FicheSignaletiqueGenerator
        
        generator = FicheSignaletiqueGenerator(
            indicateur=indicateur,
            programme=programme,
            objectif_specifique=objectif_specifique,
            ministere=ministere,
            annee_debut=annee_debut,
            mode=mode
        )
        
        generator.draw_on_canvas(pdf, width, height, start_y=start_y, available_height=available_height, ajustement_hauteur_cadre=ajustement_hauteur_cadre)
    
    @classmethod
    def generate_fiches_signaletiques_programme(
        cls,
        programme,
        ministere: str,
        annee_debut: int,
        session=None,
        mode: str = "brouillon",
        start_page: int = 1,
        numero_programme: int = 1,
        annexe_num: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Génère toutes les fiches signalétiques d'indicateurs pour un programme.
        
        Args:
            programme: Objet Programme
            ministere: Nom du ministère
            annee_debut: Année de début pour les cibles
            session: Session de base de données
            mode: Mode "brouillon" ou "final"
            start_page: Numéro de page de début
        
        Returns:
            Tuple (buffer PDF, numéro de page final)
        """
        from reportlab.lib.pagesizes import A4
        from sqlmodel import select, and_
        from app.models.performance import ObjectifPerformance, IndicateurPerformance
        
        buffer = BytesIO()
        width, height = A4  # Format portrait pour les fiches
        pdf = canvas.Canvas(buffer, pagesize=A4)
        
        logger.info("=" * 80)
        logger.info("🚀 DÉBUT GÉNÉRATION FICHES SIGNALÉTIQUES POUR PROGRAMME")
        logger.info("=" * 80)
        logger.info(f"📐 Canvas initialisé - width={width}, height={height}, pagesize=A4")
        logger.info(f"📐 Programme ID: {getattr(programme, 'id', 'N/A') if programme else 'N/A'}")
        logger.info(f"📐 Programme libelle: {getattr(programme, 'libelle', 'N/A') if programme else 'N/A'}")
        logger.info(f"📐 Ministère: {ministere}")
        logger.info(f"📐 Année début: {annee_debut}")
        logger.info(f"📐 Mode: {mode}")
        logger.info(f"📐 Start page: {start_page}")
        logger.info(f"📐 Session disponible: {session is not None}")
        
        current_page = start_page
        
        if not session:
            logger.warning("⚠️ Aucune session de base de données disponible pour générer les fiches signalétiques")
            pdf.save()
            buffer.seek(0)
            return buffer, current_page
        
        try:
            # Récupérer l'objectif global du programme
            logger.info(f"🔍 Recherche de l'objectif global pour le programme ID {programme.id}")
            objectif_global_query = select(ObjectifPerformance).where(
                and_(
                    ObjectifPerformance.programme_id == programme.id,
                    ObjectifPerformance.type_objectif == "global"
                )
            )
            objectif_global = session.exec(objectif_global_query).first()
            logger.info(f"🔍 Objectif global trouvé: {objectif_global is not None}")
            if objectif_global:
                logger.info(f"🔍 Objectif global ID: {objectif_global.id}, titre: {getattr(objectif_global, 'titre', 'N/A')}")
            
            if not objectif_global:
                logger.warning(f"⚠️ Aucun objectif global trouvé pour le programme {programme.libelle}")
                pdf.save()
                buffer.seek(0)
                return buffer, current_page
            
            # Récupérer tous les objectifs spécifiques du programme (filtrés par période)
            logger.info(f"🔍 Recherche des objectifs spécifiques pour l'OG ID {objectif_global.id}, période {annee_debut}")
            os_query = select(ObjectifPerformance).where(
                and_(
                    ObjectifPerformance.objectif_global_id == objectif_global.id,
                    ObjectifPerformance.type_objectif == "specifique",
                    ObjectifPerformance.periode.ilike(f"%{annee_debut}%")
                )
            ).order_by(ObjectifPerformance.code, ObjectifPerformance.id)
            objectifs_specifiques = session.exec(os_query).all()
            logger.info(f"🔍 {len(objectifs_specifiques)} objectifs spécifiques trouvés")
            
            if not objectifs_specifiques:
                logger.warning(f"⚠️ Aucun objectif spécifique trouvé pour le programme {programme.libelle}")
                pdf.save()
                buffer.seek(0)
                return buffer, current_page
            
            # Collecter tous les indicateurs uniques du programme
            indicateurs_uniques = []
            indicateurs_ids_vus = set()
            
            for os in objectifs_specifiques:
                # Charger les indicateurs pour cet OS (tous les indicateurs actifs, pas seulement ceux de l'année)
                logger.info(f"🔍 Recherche des indicateurs pour l'OS ID {os.id} ({getattr(os, 'code', 'N/A')})")
                ind_query = select(IndicateurPerformance).where(
                    and_(
                        IndicateurPerformance.objectif_id == os.id,
                        IndicateurPerformance.actif == True
                    )
                ).order_by(IndicateurPerformance.nom)
                indicateurs = session.exec(ind_query).all()
                logger.info(f"🔍 {len(indicateurs)} indicateurs trouvés pour l'OS ID {os.id}")
                
                for ind in indicateurs:
                    # Éviter les doublons (un indicateur peut être lié à plusieurs OS)
                    if ind.id not in indicateurs_ids_vus:
                        indicateurs_uniques.append((ind, os))
                        indicateurs_ids_vus.add(ind.id)
                        logger.info(f"  ✅ Indicateur ajouté: ID {ind.id}, nom: {getattr(ind, 'nom', 'N/A')}")
                    else:
                        logger.info(f"  ⏭️ Indicateur ID {ind.id} déjà ajouté (doublon ignoré)")
            
            logger.info(f"📊 {len(indicateurs_uniques)} indicateurs uniques trouvés pour le programme {programme.libelle}")
            
            if not indicateurs_uniques:
                logger.warning(f"⚠️ Aucun indicateur trouvé pour générer les fiches signalétiques")
                pdf.save()
                buffer.seek(0)
                return buffer, current_page
            
            # Dessiner le titre de l'annexe avant les fiches
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.lib.utils import simpleSplit
            
            programme_libelle = getattr(programme, 'libelle', f'Programme {numero_programme}')
            titre_annexe = f"ANNEXE {annexe_num} : Fiche signalétique des indicateurs du programme {numero_programme} « {programme_libelle} »"
            
            pdf.saveState()
            font_size = 12  # Réduire la taille de la police
            pdf.setFont("Helvetica-Bold", font_size)
            pdf.setFillColor(colors.HexColor("#000000"))
            
            # Largeur disponible pour le titre (avec marges de 2 cm de chaque côté)
            max_width = width - 4 * cm
            
            # Diviser le titre en plusieurs lignes si nécessaire
            titre_lines = simpleSplit(titre_annexe, "Helvetica-Bold", font_size, max_width)
            
            # Centrer le titre verticalement et horizontalement
            line_height = font_size * 1.2  # Espacement entre les lignes
            total_height = len(titre_lines) * line_height
            titre_y = height - 2 * cm  # Position de départ (2 cm du haut)
            
            # Dessiner chaque ligne du titre, centrée horizontalement
            last_line_y = None
            for i, line in enumerate(titre_lines):
                line_width = pdf.stringWidth(line, "Helvetica-Bold", font_size)
                line_x = (width - line_width) / 2  # Centrer chaque ligne
                line_y = titre_y - (i * line_height)
                pdf.drawString(line_x, line_y, line)
                if i == len(titre_lines) - 1:
                    last_line_y = line_y  # Position Y de la dernière ligne
            
            pdf.restoreState()
            
            # Calculer la position du bas du titre (dernière ligne)
            # La position Y de drawString est la ligne de base, donc le bas de la ligne est environ à last_line_y - font_size * 0.2
            # Mais pour être sûr, on utilise simplement last_line_y comme référence
            if last_line_y is not None:
                # Le bas de la dernière ligne est environ à last_line_y - font_size * 0.2 (pour la descente)
                titre_bottom_y = last_line_y - font_size * 0.2
            else:
                titre_bottom_y = titre_y - total_height
            
            # Calculer la hauteur disponible pour la première fiche
            # Hauteur de page - position du bas du titre - marge inférieure - footer
            footer_height = 1.5 * cm
            footer_margin = 1.5 * cm
            bottom_margin = 0.5 * cm
            available_height_for_first_fiche = titre_bottom_y - footer_height - footer_margin - bottom_margin
            
            # Dessiner le numéro de page sur la page du titre
            from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer
            try:
                RAPLayoutDrawer.draw_page_footer(
                    pdf=pdf,
                    page_number=current_page,
                    width=width,
                    footer_margin=1.5 * cm,
                    footer_height=1.5 * cm,
                    right_margin=2 * cm
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du dessin du footer pour la page du titre {current_page}: {e}")
            
            logger.info(f"📝 Titre de l'annexe dessiné: {titre_annexe} (page {current_page})")
            logger.info(f"📐 Hauteur disponible pour la première fiche: {available_height_for_first_fiche} (hauteur totale: {height})")
            
            # Générer une fiche pour chaque indicateur
            for idx, (ind, os) in enumerate(indicateurs_uniques):
                # Pour la première fiche, on reste sur la même page que le titre
                # Pour les autres fiches, on crée une nouvelle page
                if idx > 0:
                    pdf.showPage()
                    # Incrémenter le numéro de page après le titre (seulement après la première fiche)
                    if idx == 1:
                        current_page += 1
                    else:
                        current_page += 1
                
                logger.info(f"📄 Génération de la fiche signalétique {idx + 1}/{len(indicateurs_uniques)} pour l'indicateur '{ind.nom}' (page {current_page})")
                
                # Pour la première fiche, calculer la position de départ après le titre
                # Pour les autres fiches, utiliser la hauteur complète et start_y=None
                if idx == 0:
                    # Position Y de départ de la fiche (juste après le titre avec un petit espacement)
                    espacement_apres_titre = 0.5 * cm
                    fiche_start_y = titre_bottom_y - espacement_apres_titre
                    # Ajustement de la hauteur du contour du cadre de la fiche
                    # Cette valeur sera soustraite de la hauteur disponible pour réduire la hauteur du contour
                    ajustement_hauteur_cadre = 25 * cm  # Ajuster cette valeur pour modifier la hauteur du cadre
                    # Pour la première fiche, on passe toujours la hauteur totale de la page
                    # et start_y pour indiquer où commencer, ainsi que la hauteur disponible et l'ajustement
                    fiche_height = height
                    fiche_available_height = available_height_for_first_fiche
                    logger.info(f"🔍=========================== DEBUG - Position Y du début de la première fiche:")
                    logger.info(f"   - titre_bottom_y: {titre_bottom_y}")
                    logger.info(f"   - espacement_apres_titre: {espacement_apres_titre}")
                    logger.info(f"   - fiche_start_y: {fiche_start_y}")
                    logger.info(f"   - ajustement_hauteur_cadre: {ajustement_hauteur_cadre}")
                    logger.info(f"   - available_height_for_first_fiche: {available_height_for_first_fiche}")
                    logger.info(f"   - height (page): {height}")
                else:
                    fiche_start_y = None
                    fiche_height = height
                    fiche_available_height = None
                
                # Log avant l'appel pour vérifier la valeur
                logger.info(f"🔍 DEBUG - Avant appel draw_fiche_signaletique: fiche_start_y={fiche_start_y}, fiche_height={fiche_height}")
                
                # Dessiner la fiche signalétique
                try:
                    cls.draw_fiche_signaletique(
                        pdf=pdf,
                        indicateur=ind,
                        programme=programme,
                        objectif_specifique=os,
                        ministere=ministere,
                        annee_debut=annee_debut,
                        width=width,
                        height=fiche_height,
                        mode=mode,
                        start_y=fiche_start_y,
                        available_height=fiche_available_height if idx == 0 else None,
                        ajustement_hauteur_cadre=ajustement_hauteur_cadre if idx == 0 else 0
                    )
                    logger.info(f"✅ Fiche signalétique dessinée pour l'indicateur '{ind.nom}'")
                except Exception as e:
                    logger.error(f"❌ Erreur lors du dessin de la fiche pour l'indicateur '{ind.nom}': {e}", exc_info=True)
                    continue
                
                # Dessiner le numéro de page
                from reportlab.lib.units import cm
                from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer
                try:
                    RAPLayoutDrawer.draw_page_footer(
                        pdf=pdf,
                        page_number=current_page,
                        width=width,
                        footer_margin=1.5 * cm,
                        footer_height=1.5 * cm,
                        right_margin=2 * cm
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lors du dessin du footer pour la page {current_page}: {e}")
                
                current_page += 1
                logger.info(f"✅ Fiche signalétique générée pour l'indicateur '{ind.nom}' (page {current_page - 1})")
            
            pdf.save()
            buffer.seek(0)
            
            logger.info(f"✅ {len(indicateurs_uniques)} fiches signalétiques générées pour le programme {programme.libelle}")
            
            return buffer, current_page
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération des fiches signalétiques pour le programme {programme.libelle}: {e}", exc_info=True)
            pdf.save()
            buffer.seek(0)
            return buffer, current_page
    
    @classmethod
    def generate_annexe_modification_programme(
        cls,
        programme,
        annee_debut: int,
        annee_fin: int,
        session=None,
        mode: str = "brouillon",
        start_page: int = 1,
        numero_programme: int = 1,
        annexe_num: int = 2,
        modifications: list = None
    ) -> tuple[BytesIO, int]:
        """
        Génère l'annexe de modification de l'architecture programmatique pour un programme.
        
        Args:
            programme: Objet Programme
            annee_debut: Année de début de la période
            annee_fin: Année de fin de la période
            session: Session de base de données
            mode: Mode de génération ("brouillon" ou "final")
            start_page: Numéro de page de départ
            numero_programme: Numéro du programme
            annexe_num: Numéro de l'annexe
            
        Returns:
            Tuple (buffer, final_page) contenant le PDF généré et le numéro de la dernière page
        """
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from io import BytesIO
        from PyPDF2 import PdfReader
        from sqlmodel import select, and_
        from app.models.personnel import Programme
        from app.models.budget import SigobeExecution
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator, RAPLayoutDrawer, RAPPageManager
        
        logger.info(f"📄 Génération de l'annexe de modification pour le programme {numero_programme} '{programme.libelle}' (Annexe {annexe_num})...")
        
        buffer = BytesIO()
        width, height = landscape(A4)
        
        # Marges
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        
        # Couleurs selon le mode
        text_color = colors.HexColor("#FF0000") if mode == "brouillon" else colors.HexColor("#000000")
        dark_text = colors.HexColor("#000000")
        
        # Créer les styles
        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=styles['Normal'],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # CENTER
            textColor=dark_text
        )
        
        cell_style = ParagraphStyle(
            "CellStyle",
            parent=styles['Normal'],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=0,  # LEFT
            textColor=text_color
        )
        
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=1,  # CENTER
            textColor=dark_text,
            spaceAfter=0.5 * cm
        )
        
        # Titre de l'annexe
        programme_libelle = getattr(programme, 'libelle', f'Programme {numero_programme}')
        titre_annexe = f"ANNEXE {annexe_num} : Demande de modification de l'architecture programmatique du programme {numero_programme} « {programme_libelle} »"
        
        # Story pour SimpleDocTemplate
        story = []
        story.append(Paragraph(titre_annexe, title_style))
        story.append(Spacer(1, 0.5 * cm))
        
        # Charger les données depuis la base
        table_data = []
        
        # Normaliser les modifications
        modifications = modifications or []
        if isinstance(modifications, str):
            import json
            try:
                modifications = json.loads(modifications)
            except:
                modifications = []
        
        # Créer des dictionnaires de mapping pour les modifications
        modif_programme = {}
        modif_actions = {}  # {code_ancien: {code_nouveau, libelle_nouveau}}
        modif_activites = {}  # {code_ancien: {code_nouveau, libelle_nouveau}}
        
        for mod in modifications:
            if not isinstance(mod, dict):
                continue
            
            mod_type = mod.get("type", "").lower()
            code_ancien = mod.get("code_ancien", "").strip()
            libelle_ancien = mod.get("libelle_ancien", "").strip()
            code_nouveau = mod.get("code_nouveau", "").strip()
            libelle_nouveau = mod.get("libelle_nouveau", "").strip()
            
            if mod_type == "programme":
                # Pour le programme, on stocke les nouvelles valeurs
                modif_programme = {
                    "code_nouveau": code_nouveau,
                    "libelle_nouveau": libelle_nouveau
                }
            elif mod_type == "action":
                # Pour les actions, on utilise le code ancien comme clé principale
                if code_ancien:
                    modif_actions[code_ancien] = {
                        "code_nouveau": code_nouveau,
                        "libelle_nouveau": libelle_nouveau,
                        "libelle_ancien": libelle_ancien  # Pour matching par libellé aussi
                    }
                # Aussi par libellé complet si pas de code
                if libelle_ancien and not code_ancien:
                    modif_actions[libelle_ancien.lower()] = {
                        "code_nouveau": code_nouveau,
                        "libelle_nouveau": libelle_nouveau,
                        "libelle_ancien": libelle_ancien
                    }
            elif mod_type == "activite":
                # Pour les activités, on utilise le code ancien comme clé principale
                if code_ancien:
                    modif_activites[code_ancien] = {
                        "code_nouveau": code_nouveau,
                        "libelle_nouveau": libelle_nouveau,
                        "libelle_ancien": libelle_ancien  # Pour matching par libellé aussi
                    }
                # Aussi par libellé complet si pas de code
                if libelle_ancien and not code_ancien:
                    modif_activites[libelle_ancien.lower()] = {
                        "code_nouveau": code_nouveau,
                        "libelle_nouveau": libelle_nouveau,
                        "libelle_ancien": libelle_ancien
                    }
        
        if session:
            try:
                # Récupérer le programme avec son code
                programme_obj = session.get(Programme, programme.id) if hasattr(programme, 'id') else programme
                programme_code = getattr(programme_obj, 'code', '')
                programme_libelle_db = getattr(programme_obj, 'libelle', programme_libelle)
                
                # Appliquer les modifications au programme
                programme_code_ancien = programme_code
                programme_libelle_ancien = programme_libelle_db
                programme_code_nouveau = modif_programme.get("code_nouveau", programme_code) if modif_programme else programme_code
                programme_libelle_nouveau = modif_programme.get("libelle_nouveau", programme_libelle_db) if modif_programme else programme_libelle_db
                
                # Charger les actions depuis SigobeExecution pour la période 2025-2027
                actions_query = select(
                    SigobeExecution.actions,
                    SigobeExecution.activites
                ).distinct().where(
                    and_(
                        SigobeExecution.annee == annee_debut,
                        SigobeExecution.programmes.ilike(f"%{programme_libelle_db}%"),
                        SigobeExecution.actions.isnot(None),
                        SigobeExecution.actions != ""
                    )
                )
                actions_data = session.exec(actions_query).all()
                
                # Organiser les données par action
                actions_dict = {}
                for action, activite in actions_data:
                    if action and action.strip():
                        if action not in actions_dict:
                            actions_dict[action] = []
                        if activite and activite.strip():
                            actions_dict[action].append(activite)
                
                # Construire les lignes du tableau
                # Ligne programme
                table_data.append([
                    f"{programme_code_ancien} {programme_libelle_ancien}",  # Codes et libellés programmes 2025-2027
                    programme_libelle_nouveau if programme_libelle_nouveau != programme_libelle_ancien else programme_libelle_ancien,  # Libellés programmes 2026-2028
                    "",  # Codes et libellés des Actions 2025-2027
                    "",  # Libellés Actions 2026-2028
                    ""   # Codes et libellés des activités 2026-2028
                ])
                
                # Lignes actions et activités
                for action_code_libelle, activites_list in actions_dict.items():
                    # Extraire le code et le libellé de l'action
                    action_parts = action_code_libelle.split(' ', 1)
                    action_code_ancien = action_parts[0] if len(action_parts) > 0 else ""
                    action_libelle_ancien = action_parts[1] if len(action_parts) > 1 else action_code_libelle
                    
                    # Appliquer les modifications à l'action
                    action_modif = None
                    if action_code_ancien in modif_actions:
                        action_modif = modif_actions[action_code_ancien]
                    elif action_libelle_ancien.lower() in modif_actions:
                        action_modif = modif_actions[action_libelle_ancien.lower()]
                    # Vérifier aussi par correspondance partielle du libellé
                    if not action_modif:
                        for key, modif in modif_actions.items():
                            if isinstance(modif, dict) and modif.get("libelle_ancien"):
                                if modif["libelle_ancien"].lower() in action_libelle_ancien.lower() or action_libelle_ancien.lower() in modif["libelle_ancien"].lower():
                                    action_modif = modif
                                    break
                    
                    action_code_nouveau = action_modif.get("code_nouveau", action_code_ancien) if action_modif else action_code_ancien
                    action_libelle_nouveau = action_modif.get("libelle_nouveau", action_libelle_ancien) if action_modif else action_libelle_ancien
                    
                    # Première ligne pour l'action
                    table_data.append([
                        "",  # Codes et libellés programmes 2025-2027
                        "",  # Libellés programmes 2026-2028
                        f"{action_code_ancien} {action_libelle_ancien}",  # Codes et libellés des Actions 2025-2027
                        action_libelle_nouveau,  # Libellés Actions 2026-2028
                        ""   # Codes et libellés des activités 2026-2028
                    ])
                    
                    # Lignes pour les activités
                    for activite in activites_list:
                        if activite and activite.strip():
                            # Extraire le code et le libellé de l'activité
                            activite_parts = activite.split(' ', 1)
                            activite_code_ancien = activite_parts[0] if len(activite_parts) > 0 else ""
                            activite_libelle_ancien = activite_parts[1] if len(activite_parts) > 1 else activite
                            
                            # Appliquer les modifications à l'activité
                            activite_modif = None
                            if activite_code_ancien in modif_activites:
                                activite_modif = modif_activites[activite_code_ancien]
                            elif activite_libelle_ancien.lower() in modif_activites:
                                activite_modif = modif_activites[activite_libelle_ancien.lower()]
                            # Vérifier aussi par correspondance partielle du libellé
                            if not activite_modif:
                                for key, modif in modif_activites.items():
                                    if isinstance(modif, dict) and modif.get("libelle_ancien"):
                                        if modif["libelle_ancien"].lower() in activite_libelle_ancien.lower() or activite_libelle_ancien.lower() in modif["libelle_ancien"].lower():
                                            activite_modif = modif
                                            break
                            
                            activite_code_nouveau = activite_modif.get("code_nouveau", activite_code_ancien) if activite_modif else activite_code_ancien
                            activite_libelle_nouveau = activite_modif.get("libelle_nouveau", activite_libelle_ancien) if activite_modif else activite_libelle_ancien
                            
                            table_data.append([
                                "",  # Codes et libellés programmes 2025-2027
                                "",  # Libellés programmes 2026-2028
                                "",  # Codes et libellés des Actions 2025-2027
                                "",  # Libellés Actions 2026-2028
                                f"{activite_code_nouveau} {activite_libelle_nouveau}"  # Codes et libellés des activités 2026-2028
                            ])
                
                # Si aucune donnée trouvée, ajouter une ligne vide
                if not table_data:
                    table_data.append([
                        ".............................",  # Codes et libellés programmes 2025-2027
                        ".............................",  # Libellés programmes 2026-2028
                        ".............................",  # Codes et libellés des Actions 2025-2027
                        ".............................",  # Libellés Actions 2026-2028
                        "............................."  # Codes et libellés des activités 2026-2028
                    ])
                    
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement des données pour l'annexe de modification: {e}", exc_info=True)
                table_data.append([
                    ".............................",  # Codes et libellés programmes 2025-2027
                    ".............................",  # Libellés programmes 2026-2028
                    ".............................",  # Codes et libellés des Actions 2025-2027
                    ".............................",  # Libellés Actions 2026-2028
                    "............................."  # Codes et libellés des activités 2026-2028
                ])
        else:
            # Pas de session, données par défaut
            table_data.append([
                ".............................",  # Codes et libellés programmes 2025-2027
                ".............................",  # Libellés programmes 2026-2028
                ".............................",  # Codes et libellés des Actions 2025-2027
                ".............................",  # Libellés Actions 2026-2028
                "............................."  # Codes et libellés des activités 2026-2028
            ])
        
        # En-têtes du tableau
        headers = [
            f"Codes et libellés programmes {annee_debut}-{annee_fin}",
            f"Libellés programmes {annee_debut+1}-{annee_fin+1}",
            f"Codes et libellés des Actions {annee_debut}-{annee_fin}",
            f"Libellés Actions {annee_debut+1}-{annee_fin+1}",
            f"Codes et libellés des activités {annee_debut+1}-{annee_fin+1}"
        ]
        
        # Préparer les données du tableau avec Paragraph pour le wrapping
        table_rows = []
        
        # En-têtes
        header_row = [Paragraph(header, header_style) for header in headers]
        table_rows.append(header_row)
        
        # Données
        for row in table_data:
            table_rows.append([Paragraph(cell if cell else "", cell_style) for cell in row])
        
        # Largeurs des colonnes
        available_width = width - left_margin - right_margin
        col_widths = [
            available_width * 0.2,  # Colonne 1
            available_width * 0.2,  # Colonne 2
            available_width * 0.2,  # Colonne 3
            available_width * 0.2,  # Colonne 4
            available_width * 0.2   # Colonne 5
        ]
        
        # Créer le LongTable
        from reportlab.platypus import LongTable
        table = LongTable(
            table_rows,
            colWidths=col_widths,
            repeatRows=1,  # Répéter la ligne d'en-tête sur chaque page
            splitByRow=1  # Permettre le découpage ligne par ligne
        )
        
        # Style du tableau
        table_style = TableStyle([
            # Bordures
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # En-têtes
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), dark_text),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            # Données
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])
        
        table.setStyle(table_style)
        
        # Ajouter le tableau à la story
        story.append(table)
        
        # Créer le SimpleDocTemplate
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        from app.services.rapport_cadre_performance_generator import CPLayoutDrawer
        
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            CPLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RAPLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            CPLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RAPLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin
            )
        
        # Construire le PDF
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        
        # Enregistrer la position de l'annexe
        RAPPageManager.register_page_position(f"cp_annexe_{annexe_num}", start_page)
        
        buffer.seek(0)
        
        logger.info(f"✅ Annexe de modification générée pour le programme {numero_programme} '{programme_libelle}' (pages {start_page} à {final_page - 1})")
        
        return buffer, final_page

