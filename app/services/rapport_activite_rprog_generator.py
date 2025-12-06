"""
Générateur de Rapport d'Activité du RPROG (Rapport de Programme).

Ce module génère un PDF de rapport d'activité en réutilisant les classes
et méthodes du Rapport Annuel de Performance (RAP) pour les pages de couverture,
sommaire, liste des tableaux et liste des figures.

Architecture modulaire :
- RPROGBaseGenerator : Classe de base avec constantes et utilitaires (hérite de RAPBaseGenerator)
- RPROGLayoutDrawer : Éléments de layout (cover, footer, background) - réutilise RAPLayoutDrawer
- RPROGContentDrawer : Contenu principal (sommaire, listes) - réutilise RAPContentDrawer
- RPROGPDFGenerator : Orchestrateur principal
"""
from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from PyPDF2 import PdfReader, PdfWriter

from app.services.rapport_annuel_performance_generator_modular import (
    RAPBaseGenerator,
    RAPLayoutDrawer,
    RAPContentDrawer,
    RAPPageManager,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CLASSE DE BASE - HÉRITE DU RAP
# ============================================================================

class RPROGBaseGenerator(RAPBaseGenerator):
    """
    Classe de base pour le Rapport d'Activité RPROG.
    
    Hérite de RAPBaseGenerator pour réutiliser toutes les constantes,
    compteurs et utilitaires. Peut être étendue avec des constantes
    spécifiques au RPROG si nécessaire.
    """
    
    # Données par défaut pour le RPROG
    DEFAULT_DATA = {
        "annee": 2024,
        "section": "SECTION 376",
        "ministere": "",
        "programme": "PROGRAMME PORTEFEUILLE DE L'ETAT",
        "periode": "PREMIER SEMESTRE",
        "titre_rapport": "RAPPORT D'ACTIVITES DU PREMIER SEMESTRE 2024\n\n« PROGRAMME PORTEFEUILLE DE L'ETAT »",
        "titre_annee": "AU TITRE DE L'ANNÉE",
        "date_publication": "",
        "logo_path": "",
        "responsable_programme": "",  # Ex: "Monsieur Jean DUPONT" ou "Madame Marie MARTIN"
    }


# ============================================================================
# GESTIONNAIRE DE LAYOUT - RÉUTILISE RAPLayoutDrawer
# ============================================================================

class RPROGLayoutDrawer(RAPLayoutDrawer):
    """
    Gestionnaire de layout pour le rapport RPROG.
    
    Réutilise directement les méthodes de RAPLayoutDrawer :
    - draw_cover_page()
    - draw_background_shapes()
    - draw_footer()
    
    Surcharge draw_cover_block() pour adapter le titre au format RPROG
    (sans concaténation du ministère, car le titre est déjà complet).
    Surcharge draw_header() pour augmenter la taille de la police du ministère.
    Surcharge draw_page_footer() pour afficher "Page X sur Y" au lieu de "Page X".
    """
    
    @classmethod
    def draw_page_footer(
        cls,
        pdf: canvas.Canvas,
        page_number: int,
        width: float,
        footer_margin: float,
        footer_height: float,
        right_margin: float,
        total_pages: int | None = None
    ) -> None:
        """
        Dessine le pied de page avec le numéro de page au format "Page X sur Y".
        
        Args:
            pdf: Le canvas PDF
            page_number: Numéro de la page actuelle
            width: Largeur de la page
            footer_margin: Marge du footer
            footer_height: Hauteur du footer
            right_margin: Marge droite
            total_pages: Nombre total de pages (si None, sera calculé automatiquement)
        """
        from reportlab.lib.units import cm
        
        # Si total_pages n'est pas fourni, essayer de le récupérer depuis les données
        if total_pages is None:
            total_pages = getattr(cls, '_total_pages', None)
        
        # Si toujours None, utiliser page_number comme fallback (sera mis à jour plus tard)
        if total_pages is None:
            total_pages = page_number
        
        # Position du texte (centré horizontalement)
        center_x = width / 2
        footer_y = footer_margin + (footer_height / 2)
        
        # Texte du footer : "Page X sur Y"
        footer_text = f"Page {page_number} sur {total_pages}"
        
        pdf.saveState()
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(cls.DARK_TEXT)
        pdf.drawCentredString(center_x, footer_y, footer_text)
        pdf.restoreState()
    
    @classmethod
    def draw_header(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine l'en-tête avec le titre République, le logo, la section et le ministère.
        
        Version adaptée pour le RPROG : taille de police du ministère augmentée.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        """
        from reportlab.lib.units import cm
        from textwrap import wrap
        from app.services.rapport_annuel_performance_generator_modular import RAPStylingManager
        
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
                from io import BytesIO
                from reportlab.lib.utils import ImageReader
                
                logo_width = 3.5 * cm
                logo_height = 3.5 * cm
                x_logo = center_x - logo_width / 2
                y_logo = current_y - logo_height

                logger.info(f"🖼️ Dessin du logo: {logo_path} à la position ({x_logo}, {y_logo})")
                
                # Essayer de charger le logo
                if logo_path.startswith("data:image"):
                    # Image encodée en base64
                    import base64
                    header, encoded = logo_path.split(",", 1)
                    image_data = base64.b64decode(encoded)
                    image_reader = ImageReader(BytesIO(image_data))
                    pdf.drawImage(
                        image_reader, x_logo, y_logo,
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
        _, section_source = RAPStylingManager._determine_data_source_for_canvas("section", section)
        _, ministere_source = RAPStylingManager._determine_data_source_for_canvas("ministere", ministere)
        
        # Calculer la hauteur du contenu
        section_height = 20  # Hauteur de la section (texte + espace)
        ministere_height = 0
        if ministere:
            ministere_lines = wrap(ministere, width=80)
            ministere_height = len(ministere_lines) * 18  # 18 points par ligne (augmenté de 16)
        
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
            # Taille de police augmentée pour le RPROG (13 au lieu de 11)
            pdf.setFont("Helvetica-BoldOblique", 13)
            # Utiliser la source déterminée pour la couleur (peut être user > db > default)
            ministere_color = RAPStylingManager._get_color_for_source(ministere_source)
            lines = wrap(ministere, width=80)
            line_height = 18  # Augmenté de 16 à 18 pour correspondre à la nouvelle taille de police
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
        
        # Stocker la position de la ligne pointillée du bas pour le positionnement du bloc central
        cls._dotted_line_bottom_y = bottom_line_y
        
        pdf.restoreState()
    
    @classmethod
    def draw_page_header(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """
        Dessine un en-tête simple pour les pages de contenu (sans logo, section, ministère).
        
        Cette méthode est utilisée pour les pages de contenu (introduction, activités, etc.)
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
        
        Version adaptée pour le RPROG : le titre est déjà complet et ne doit pas
        être concaténé avec le nom du ministère.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from app.services.rapport_annuel_performance_generator_modular import RAPStylingManager
        
        pdf.saveState()

        center_x = width / 2
        center_y = height / 2

        # ---------- BOÎTE ORANGE AVEC LE TITRE ----------
        # Dimensions de la boîte (plus large pour le mode paysage)
        box_margin_x = 3 * cm
        box_width = width - 6 * cm
        box_height = 3.0 * cm  # Hauteur réduite (était 5.5 cm)
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
        # Pour le RPROG, construire le titre automatiquement à partir de periode et programme
        # Accéder aux données via RPROGBaseGenerator.data (classe de base partagée)
        from app.services.rapport_activite_rprog_generator import RPROGBaseGenerator
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator
        
        # Essayer d'accéder aux données depuis différentes sources
        data = None
        if hasattr(RPROGBaseGenerator, 'data') and RPROGBaseGenerator.data:
            data = RPROGBaseGenerator.data
        elif hasattr(RAPBaseGenerator, 'data') and RAPBaseGenerator.data:
            data = RAPBaseGenerator.data
        elif hasattr(cls, 'data') and cls.data:
            data = cls.data
        else:
            data = {}
        
        titre_rapport = data.get("titre_rapport", "")
        periode = data.get("periode", "")
        programme = data.get("programme", "")
        annee = data.get("annee", "")
        titre_annee = data.get("titre_annee", "")
        responsable_programme = data.get("responsable_programme", "")
        
        # Log pour débogage
        logger.info(f"🔍 RPROG - Données disponibles: {list(data.keys()) if data else 'AUCUNE'}")
        logger.info(f"🔍 RPROG - Données reçues: periode={periode}, programme={programme}, annee={annee}, titre_rapport={titre_rapport[:50] if titre_rapport else 'VIDE'}")
        
        # Si le titre n'est pas fourni explicitement ou est vide, le construire à partir de periode et programme
        if not titre_rapport or not titre_rapport.strip():
            if periode and programme and annee:
                titre_rapport = f"RAPPORT D'ACTIVITES DU {periode} {annee}\n\n« {programme} »"
                logger.debug(f"✅ RPROG - Titre construit automatiquement: {titre_rapport[:100]}")
            elif periode and annee:
                # Si seulement periode et annee sont disponibles
                titre_rapport = f"RAPPORT D'ACTIVITES DU {periode} {annee}"
                logger.debug(f"✅ RPROG - Titre construit (sans programme): {titre_rapport}")
            else:
                logger.warning(f"⚠️ RPROG - Impossible de construire le titre: periode={periode}, programme={programme}, annee={annee}")
        
        # Déterminer la source de chaque donnée pour le styling
        _, titre_rapport_source = RAPStylingManager._determine_data_source_for_canvas("titre_rapport", titre_rapport)
        _, titre_annee_source = RAPStylingManager._determine_data_source_for_canvas("titre_annee", titre_annee)
        _, annee_source = RAPStylingManager._determine_data_source_for_canvas("annee", annee)
        
        # Toutes les données sont DB, utiliser l'italique
        should_use_italic = True
        
        # Log pour débogage
        logger.debug(f"🔍 RPROG - Titre rapport source: {titre_rapport_source}, Utiliser italique: {should_use_italic}")
        
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
            # Pour le RPROG, on veut préserver les retours à la ligne du titre
            # Diviser d'abord par les retours à la ligne existants
            paragraphs = text.split('\n')
            all_lines = []
            
            for para in paragraphs:
                if not para.strip():
                    # Ligne vide, l'ajouter telle quelle
                    all_lines.append("")
                    continue
                    
                words = para.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_width = pdf_canvas.stringWidth(test_line, font_name, font_size)
                    
                    if test_width <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            all_lines.append(current_line)
                        # Si un mot seul dépasse, on le coupe
                        if pdf_canvas.stringWidth(word, font_name, font_size) > max_width:
                            # Couper le mot
                            current_word = word
                            while pdf_canvas.stringWidth(current_word, font_name, font_size) > max_width:
                                # Trouver un point de coupure
                                for i in range(len(current_word), 0, -1):
                                    if pdf_canvas.stringWidth(current_word[:i], font_name, font_size) <= max_width:
                                        all_lines.append(current_word[:i])
                                        current_word = current_word[i:]
                                        break
                                else:
                                    # Si on ne peut pas couper proprement, prendre au moins un caractère
                                    all_lines.append(current_word[0])
                                    current_word = current_word[1:]
                            current_line = current_word
                        else:
                            current_line = word
                
                if current_line:
                    all_lines.append(current_line)
            
            return all_lines if all_lines else [text]
        
        # Titre principal (sur plusieurs lignes si nécessaire)
        font_size = 20  # Taille de police augmentée (était 16)
        # Choisir la police selon la source : BoldOblique pour DB (italique), Bold sinon
        if should_use_italic:
            font_name = "Helvetica-BoldOblique"
            logger.debug(f"✅ RPROG - Utilisation de Helvetica-BoldOblique pour le titre (italique)")
        else:
            font_name = "Helvetica-Bold"
            logger.debug(f"⚠️ RPROG - Utilisation de Helvetica-Bold pour le titre (pas d'italique)")
        line_height = 24  # Hauteur de ligne légèrement augmentée pour espacer les lignes (était 20)
        pdf.setFont(font_name, font_size)
        
        # Calculer la largeur maximale pour le texte
        max_text_width = text_area_width
        
        # Déterminer la couleur du titre (toutes les données sont DB, rouge)
        titre_color = RAPStylingManager._get_color_for_source("db")
        
        # Découper le titre en lignes (en préservant les retours à la ligne)
        if titre_rapport and titre_rapport.strip():
            logger.debug(f"📝 RPROG - Affichage du titre: {titre_rapport[:100]}")
            lines = wrap_text_to_width(pdf, titre_rapport.upper(), font_name, font_size, max_text_width)
            logger.debug(f"📝 RPROG - Nombre de lignes après découpage: {len(lines)}")
            
            # Filtrer les lignes vides pour le calcul de hauteur
            non_empty_lines = [l for l in lines if l and l.strip()]
            total_text_height = len(non_empty_lines) * line_height
            available_height = text_area_top - text_area_bottom
            
            # Si le texte est trop haut, réduire la taille de police
            if total_text_height > available_height - 30:  # 30 points pour le responsable en dessous
                font_size = 18  # Taille réduite augmentée (était 14)
                line_height = 20  # Hauteur de ligne légèrement augmentée (était 18)
                pdf.setFont(font_name, font_size)
                # Recalculer avec la nouvelle taille
                lines = wrap_text_to_width(pdf, titre_rapport.upper(), font_name, font_size, max_text_width)
                non_empty_lines = [l for l in lines if l and l.strip()]
                total_text_height = len(non_empty_lines) * line_height
            
            # Positionner le texte en haut de la zone disponible
            text_y = text_area_top - 0.8 * cm
            
            # Dessiner chaque ligne centrée avec la couleur appropriée
            # Ignorer les lignes vides pour réduire l'espacement
            pdf.saveState()
            pdf.setFillColor(titre_color)
            line_index = 0  # Index pour les lignes non vides uniquement
            for line in lines:
                if line and line.strip():  # Ne dessiner que les lignes non vides
                    pdf.drawCentredString(center_x, text_y - (line_index * line_height), line)
                    logger.debug(f"📝 RPROG - Ligne {line_index} dessinée à y={text_y - (line_index * line_height)}: {line[:50]}")
                    line_index += 1
            pdf.restoreState()
            
            text_y = text_y - (len(non_empty_lines) * line_height)
        else:
            logger.warning(f"⚠️ RPROG - Aucun titre à afficher! titre_rapport={titre_rapport}")
            text_y = text_area_top - 0.8 * cm
        
        pdf.restoreState()
        
        # Responsable de programme EN DEHORS de la boîte orange, juste en dessous
        if responsable_programme and responsable_programme.strip():
            # Positionner le texte juste en dessous de la boîte orange
            responsable_y = box_y - 1.2 * cm  # Espacement de 1.2 cm sous la boîte
            
            responsable_text = f"RESPONSABLE DE PROGRAMME : {responsable_programme.upper()}"
            # Utiliser la même couleur et police que le titre
            responsable_color = RAPStylingManager._get_color_for_source("db")
            
            # Choisir la police (italique comme le titre)
            if should_use_italic:
                responsable_font_name = "Helvetica-BoldOblique"
            else:
                responsable_font_name = "Helvetica-Bold"
            
            # Taille de police légèrement plus petite que le titre
            pdf.saveState()
            pdf.setFont(responsable_font_name, 11)
            pdf.setFillColor(responsable_color)
            pdf.drawCentredString(center_x, responsable_y, responsable_text)
            pdf.restoreState()
            logger.debug(f"📝 RPROG - Responsable de programme affiché en dehors du cadre: {responsable_text[:50]}")


# ============================================================================
# GESTIONNAIRE DE CONTENU - RÉUTILISE RAPContentDrawer
# ============================================================================

class RPROGContentDrawer(RAPContentDrawer):
    """
    Gestionnaire de contenu pour le rapport RPROG.
    
    Réutilise directement les méthodes de RAPContentDrawer :
    - draw_liste_tableaux()
    - draw_liste_graphiques()
    
    Surcharge draw_table_of_contents() pour créer un sommaire personnalisé
    avec la structure spécifique du rapport d'activité RPROG.
    """
    
    @classmethod
    def _find_rprog_pages_in_pdf(cls, pdf_reader: Any, nb_pages_sommaire: int = 0) -> dict[str, int]:
        """
        Trouve les numéros de page pour les sections RPROG en parcourant le PDF.
        
        Args:
            pdf_reader: Le PdfReader du PDF complet
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Dictionnaire avec les clés et les numéros de page trouvés
        """
        from PyPDF2 import PdfReader
        from app.services.rapport_annuel_performance_generator_modular import RAPPageManager
        
        pages_found = {}
        
        # Patterns de recherche pour les sections RPROG
        rprog_patterns = {
            "INTRODUCTION": "rprog_introduction",
            "1. REALISATIONS A MI-PARCOURS DU PROGRAMME": "rprog_realisations",
            "1.1. Les activités": "rprog_realisations_activites",
            "1.1 LES ACTIVITES": "rprog_realisations_activites",
            "LES ACTIVITES": "rprog_realisations_activites",
            "1.2. Les crédits budgétaires": "rprog_realisations_credits",
            "1.2 LES CREDITS BUDGETAIRES": "rprog_realisations_credits",
            "LES CREDITS BUDGETAIRES": "rprog_realisations_credits",
            "1.3. Les investissements": "rprog_realisations_investissements",
            "1.3 LES INVESTISSEMENTS": "rprog_realisations_investissements",
            "LES INVESTISSEMENTS": "rprog_realisations_investissements",
            "1.4. Les effectifs": "rprog_realisations_effectifs",
            "1.4 LES EFFECTIFS": "rprog_realisations_effectifs",
            "LES EFFECTIFS": "rprog_realisations_effectifs",
            "2. LA PERFORMANCE DU PROGRAMME": "rprog_performance",
            "2 LA PERFORMANCE DU PROGRAMME": "rprog_performance",
            "LA PERFORMANCE DU PROGRAMME": "rprog_performance",
            "3. DIFFICULTES ET SOLUTIONS": "rprog_difficultes",
            "3 DIFFICULTES ET SOLUTIONS": "rprog_difficultes",
            "DIFFICULTES ET SOLUTIONS": "rprog_difficultes",
            "3.1. Difficultés rencontrées": "rprog_difficultes_rencontrees",
            "3.1 DIFFICULTES RENCONTREES": "rprog_difficultes_rencontrees",
            "DIFFICULTES RENCONTREES": "rprog_difficultes_rencontrees",
            "3.2. Actions mises en œuvre ou solutions envisagées": "rprog_difficultes_solutions",
            "3.2 ACTIONS MISES EN ŒUVRE": "rprog_difficultes_solutions",
            "ACTIONS MISES EN ŒUVRE": "rprog_difficultes_solutions",
            "SOLUTIONS ENVISAGEES": "rprog_difficultes_solutions",
            "CONCLUSION": "rprog_conclusion",
        }
        
        # Parcourir le PDF pour trouver les patterns
        for page_num in range(1, len(pdf_reader.pages) + 1):
            try:
                page = pdf_reader.pages[page_num - 1]
                page_text = page.extract_text()
                if not page_text:
                    continue
                
                # Normaliser le texte de la page
                page_text_normalized = RAPPageManager.normalize_text_for_search(page_text)
                
                # Vérifier tous les patterns
                for pattern, key in rprog_patterns.items():
                    pattern_normalized = RAPPageManager.normalize_text_for_search(pattern)
                    if pattern_normalized in page_text_normalized:
                        # Enregistrer la première occurrence trouvée pour chaque clé
                        if key not in pages_found:
                            pages_found[key] = page_num + nb_pages_sommaire
                            logger.debug(f"   Page {page_num}: pattern '{pattern}' trouvé (key: {key})")
            
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du traitement de la page {page_num}: {e}")
                continue
        
        return pages_found
    
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
        Dessine la table des matières (sommaire) pour le rapport RPROG.
        
        Structure du sommaire :
        - INTRODUCTION
        - 1. REALISATIONS A MI-PARCOURS DU PROGRAMME
          - 1.1. Les activités
          - 1.2. Les crédits budgétaires
          - 1.3. Les investissements
          - 1.4. Les effectifs
        - 2. LA PERFORMANCE DU PROGRAMME
        - 3. DIFFICULTES ET SOLUTIONS
          - 3.1. Difficultés rencontrées
          - 3.2. Actions mises en œuvre ou solutions envisagées
        - CONCLUSION
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            pdf_reader_complet: Lecteur PDF complet (non utilisé pour le RPROG)
            nb_pages_sommaire: Nombre de pages du sommaire (non utilisé)
        
        Returns:
            Nombre de pages générées (toujours 1 pour le RPROG)
        """
        from reportlab.lib.units import cm
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPBaseGenerator, RAPPageManager
        
        # Le sommaire est une page simple sans en-tête complet
        # Seulement le titre "Table des matières" et le contenu
        # Le footer avec numéro de page sera dessiné à la fin avec draw_page_footer
        
        # Récupérer les numéros de page dynamiquement
        # Si un PDF complet est fourni, chercher les textes dedans
        # Sinon, utiliser les pages enregistrées avec register_page_position
        pages_found = {}
        if pdf_reader_complet:
            logger.info("🔍 Recherche des textes dans le PDF complet pour le sommaire RPROG...")
            # Chercher les patterns spécifiques au RPROG dans le PDF
            pages_found = cls._find_rprog_pages_in_pdf(pdf_reader_complet, nb_pages_sommaire)
            logger.info(f"✅ Pages trouvées dans le PDF pour RPROG: {pages_found}")
        
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
        intro_page = get_page("rprog_introduction", base_page)
        realisations_page = get_page("rprog_realisations", base_page + 1)
        activites_page = get_page("rprog_realisations_activites", realisations_page)
        credits_page = get_page("rprog_realisations_credits", realisations_page + 7)
        investissements_page = get_page("rprog_realisations_investissements", realisations_page + 9)
        effectifs_page = get_page("rprog_realisations_effectifs", investissements_page)
        performance_page = get_page("rprog_performance", realisations_page + 11)
        difficultes_page = get_page("rprog_difficultes", performance_page + 3)
        difficultes_rencontrees_page = get_page("rprog_difficultes_rencontrees", difficultes_page)
        difficultes_solutions_page = get_page("rprog_difficultes_solutions", difficultes_page)
        conclusion_page = get_page("rprog_conclusion", difficultes_page + 1)
        
        # Structure du sommaire RPROG avec pages dynamiques
        sommaire_items = [
            # (titre, page, niveau, sous_items)
            ("INTRODUCTION", intro_page, 1, []),
            ("1. REALISATIONS A MI-PARCOURS DU PROGRAMME", realisations_page, 1, [
                ("1.1. Les activités", activites_page, 2),
                ("1.2. Les crédits budgétaires", credits_page, 2),
                ("1.3. Les investissements", investissements_page, 2),
                ("1.4. Les effectifs", effectifs_page, 2),
            ]),
            ("2. LA PERFORMANCE DU PROGRAMME", performance_page, 1, []),
            ("3. DIFFICULTES ET SOLUTIONS", difficultes_page, 1, [
                ("3.1. Difficultés rencontrées", difficultes_rencontrees_page, 2),
                ("3.2. Actions mises en œuvre ou solutions envisagées", difficultes_solutions_page, 2),
            ]),
            ("CONCLUSION", conclusion_page, 1, []),
        ]
        
        # Position de départ (plus haut car pas d'en-tête)
        start_y = height - 60  # Position plus haute sans l'en-tête
        current_y = start_y
        left_margin = 3 * cm
        right_margin = width - 3 * cm
        line_height_main = 20  # Espacement pour les sections principales
        line_height_sub = 16   # Espacement pour les sous-sections
        
        # Couleur de texte (utiliser celle de la classe de base)
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Titre "Table des matières"
        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(dark_text_color)
        pdf.drawString(left_margin, current_y, "Table des matières")
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
        from reportlab.lib.units import cm
        RPROGLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=2,
            width=width,
            footer_margin=1.5 * cm,
            footer_height=1.5 * cm,
            right_margin=3 * cm,
            total_pages=getattr(cls, '_total_pages', None)
        )
        
        return 1
    
    @classmethod
    def _find_rprog_tableaux_in_pdf(cls, pdf_reader: Any, nb_pages_sommaire: int = 0) -> dict[int, tuple[int, str]]:
        """
        Trouve les numéros de page pour les tableaux RPROG en parcourant le PDF.
        
        Args:
            pdf_reader: Le PdfReader du PDF complet
            nb_pages_sommaire: Nombre de pages du sommaire (pour ajuster les numéros)
        
        Returns:
            Dictionnaire {numero_tableau: (page_num, titre)} avec les tableaux trouvés
        """
        import re
        from app.services.rapport_annuel_performance_generator_modular import RAPPageManager
        
        tableaux_pages = {}
        
        # Patterns de recherche pour les tableaux RPROG
        # Format: {numero: [patterns possibles]}
        rprog_tableaux_patterns = {
            1: [
                r"tableau\s*1\s*:",
                r"tableau\s*1\s*",
                "Mise en œuvre des activités",
                "MISE EN ŒUVRE DES ACTIVITES",
            ],
            2: [
                r"tableau\s*2\s*:",
                r"tableau\s*2\s*",
                "Exécution financière par action du programme",
                "EXECUTION FINANCIERE PAR ACTION",
            ],
            3: [
                r"tableau\s*3\s*:",
                r"tableau\s*3\s*",
                "Suivi des investissements du programme",
                "SUIVI DES INVESTISSEMENTS",
            ],
            4: [
                r"tableau\s*4\s*:",
                r"tableau\s*4\s*",
                "Evolution des effectifs du programme",
                "EVOLUTION DES EFFECTIFS",
            ],
            5: [
                r"tableau\s*5\s*:",
                r"tableau\s*5\s*",
                "Evolution des indicateurs du programme",
                "EVOLUTION DES INDICATEURS",
            ],
        }
        
        # Titres par défaut pour chaque tableau
        default_titres = {
            1: "Mise en œuvre des activités",
            2: "Exécution financière par action du programme",
            3: "Suivi des investissements du programme",
            4: "Evolution des effectifs du programme",
            5: "Evolution des indicateurs du programme",
        }
        
        # Parcourir le PDF pour trouver les tableaux
        for numero, patterns in rprog_tableaux_patterns.items():
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
                    logger.warning(f"⚠️ Erreur lors du traitement de la page {page_num} pour le Tableau {numero}: {e}")
                    continue
        
        return tableaux_pages
    
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
        Dessine la page de la liste des tableaux pour le rapport RPROG.
        
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
        top_margin = 3 * cm
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
            logger.info("🔍 Recherche des tableaux dans le PDF complet pour le RPROG...")
            tableaux_pages_found = cls._find_rprog_tableaux_in_pdf(pdf_reader_complet, nb_pages_sommaire)
            logger.info(f"✅ Tableaux trouvés dans le PDF pour RPROG: {len(tableaux_pages_found)} tableaux")
        
        # Construire la liste des tableaux
        tableaux_items = []
        
        # Tableaux RPROG par défaut
        default_tableaux = {
            1: "Mise en œuvre des activités",
            2: "Exécution financière par action du programme",
            3: "Suivi des investissements du programme",
            4: "Evolution des effectifs du programme",
            5: "Evolution des indicateurs du programme",
        }
        
        # Pages par défaut (seront remplacées si trouvées dynamiquement)
        default_pages = {
            1: 5,
            2: 12,
            3: 14,
            4: 14,
            5: 16,
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
                page_key = f"rprog_tableau_{numero}"
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
        
        # Pas d'en-tête de couverture sur la liste des tableaux (comme pour le sommaire)
        # Dessiner le titre "Liste des tableaux"
        current_y = start_y
        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(dark_text_color)
        pdf.drawString(left_margin, current_y, "Liste des tableaux")
        current_y -= 30
        
        # Dessiner les tableaux
        current_page = start_page
        for item in tableaux_items:
            if current_y < content_bottom:
                # Dessiner le footer de la page précédente avant de créer une nouvelle page
                RPROGLayoutDrawer.draw_page_footer(
                    pdf=pdf,
                    page_number=current_page,
                    width=width,
                    footer_margin=footer_margin,
                    footer_height=footer_height,
                    right_margin=right_margin,
                    total_pages=getattr(cls, '_total_pages', None)
                )
                
                # Nouvelle page si nécessaire
                pdf.showPage()
                # Pas d'en-tête de couverture sur les pages suivantes
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
        RPROGLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=current_page,
            width=width,
            footer_margin=footer_margin,
            footer_height=footer_height,
            right_margin=right_margin,
            total_pages=getattr(cls, '_total_pages', None)
        )
        
        return current_page + 1
    
    @classmethod
    def draw_introduction(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la page d'introduction du rapport RPROG.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après l'introduction
        """
        from reportlab.lib.units import cm
        from textwrap import wrap
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPBaseGenerator
        
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
        
        # Couleur de texte
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Dessiner l'en-tête (simple, sans éléments de couverture)
        RPROGLayoutDrawer.draw_page_header(pdf, width, height)
        
        # Titre "INTRODUCTION"
        current_y = start_y
        pdf.setFont("Helvetica-Bold", 16)
        pdf.setFillColor(dark_text_color)
        pdf.drawString(left_margin, current_y, "INTRODUCTION")
        current_y -= 30
        
        # Récupérer les données du programme
        data = cls.data if hasattr(cls, 'data') and cls.data else {}
        programme = data.get("programme", "PROGRAMME PORTEFEUille DE L'ETAT")
        annee = data.get("annee", 2024)
        
        # Texte d'introduction (par défaut ou depuis les données)
        introduction_text = data.get("introduction_text", "")
        
        # Si pas de texte personnalisé, utiliser le texte par défaut
        if not introduction_text:
            introduction_text = f"""Le programme « {programme} » est un programme opérationnel qui vise à assurer la gestion efficace du portefeuille de l'Etat à travers la coordination des activités de la DGPE et la mise en œuvre de son plan stratégique 2021-2025.

Conformément aux dispositions du décret n° 2023-963 du 06 décembre 2023 portant organisation du Ministère du Patrimoine, du Portefeuille de l'Etat et des Entreprises Publiques, le programme « {programme} » est constitué du Cabinet de la Direction Générale du Portefeuille de l'Etat, des Directions et Services rattachés suivants :

• la Direction Générale du Portefeuille de l'Etat
• la Direction du Portefeuille des Secteurs Primaire et Secondaire
• la Direction du Portefeuille du Secteur Tertiaire
• la Direction de la Stratégie et de l'Expertise
• la Direction des Affaires Juridiques
• la Direction des Ressources Humaines et de la Communication
• le Service de Gestion des Projets, de la Transformation, du Suivi et Evaluation
• le Service des Moyens Généraux
• le Service Système d'Information
• la Cellule de Gestion et d'Attribution des Marchés

Le cadre de performance du programme est bâti autour de trois (03) objectifs spécifiques dont l'atteinte passera par la mise en œuvre de trois (03) actions.

Pour la mise en œuvre de ses missions, le programme « {programme} » bénéficie d'un budget actuel de 5 309 800 777 FCFA dont 31 800 000 FCFA pour les dépenses de personnel, 3 278 000 777 FCFA pour les dépenses de biens et services et 2 000 000 000 FCFA pour les investissements."""
        
        # Fonction pour dessiner un paragraphe avec gestion des retours à la ligne
        def draw_paragraph(text: str, current_y_pos: float, font_name: str = "Helvetica", font_size: int = 11) -> float:
            """Dessine un paragraphe avec retour à la ligne automatique"""
            pdf.setFont(font_name, font_size)
            pdf.setFillColor(dark_text_color)
            
            # Séparer les paragraphes (lignes vides)
            paragraphs = text.split('\n\n')
            
            for para in paragraphs:
                if not para.strip():
                    current_y_pos -= 15  # Espacement pour ligne vide
                    continue
                
                # Gérer les listes à puces
                if para.strip().startswith('•'):
                    # C'est une liste à puces
                    lines = para.split('\n')
                    for line in lines:
                        if line.strip():
                            # Calculer la largeur disponible (avec indentation pour les puces)
                            indent = 0.5 * cm
                            wrap_width = int((available_width - indent) / (font_size * 0.6))
                            wrapped_lines = wrap(line.strip(), width=wrap_width)
                            
                            for wrapped_line in wrapped_lines:
                                if current_y_pos < content_bottom:
                                    # Nouvelle page si nécessaire
                                    pdf.showPage()
                                    RPROGLayoutDrawer.draw_page_header(pdf, width, height)
                                    current_y_pos = start_y
                                
                                # Dessiner la puce et le texte
                                pdf.drawString(left_margin, current_y_pos, "•")
                                pdf.drawString(left_margin + indent, current_y_pos, wrapped_line)
                                current_y_pos -= (font_size + 4)
                else:
                    # Paragraphe normal
                    wrap_width = int(available_width / (font_size * 0.6))
                    wrapped_lines = wrap(para.strip(), width=wrap_width)
                    
                    for wrapped_line in wrapped_lines:
                        if current_y_pos < content_bottom:
                            # Nouvelle page si nécessaire
                            pdf.showPage()
                            RPROGLayoutDrawer.draw_page_header(pdf, width, height)
                            current_y_pos = start_y
                        
                        pdf.drawString(left_margin, current_y_pos, wrapped_line)
                        current_y_pos -= (font_size + 4)
                
                # Espacement entre paragraphes
                current_y_pos -= 10
            
            return current_y_pos
        
        # Dessiner le texte d'introduction
        current_y = draw_paragraph(introduction_text, current_y, "Helvetica", 11)
        
        # Dessiner le pied de page
        RPROGLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=start_page,
            width=width,
            footer_margin=footer_margin,
            footer_height=footer_height,
            right_margin=right_margin,
            total_pages=getattr(cls, '_total_pages', None)
        )
        
        # Enregistrer la position de l'introduction
        RAPPageManager.register_page_position("rprog_introduction", start_page)
        
        return start_page + 1
    
    @classmethod
    def draw_realisations_activites(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la page "1.1. Les activités" avec le tableau de mise en œuvre des activités.
        
        Récupère les données depuis SuiviActivite et les affiche dans un tableau.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après cette section
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from textwrap import wrap
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPBaseGenerator, RAPPageManager
        from app.models.budget import SuiviActivite
        from sqlmodel import select
        
        # Marges
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        
        # Couleur de texte
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Récupérer les données
        data = cls.data if hasattr(cls, 'data') and cls.data else {}
        session = cls._db_session if hasattr(cls, '_db_session') and cls._db_session else None
        
        if not session:
            logger.warning("⚠️ Pas de session DB disponible pour récupérer les activités")
            # Créer une page vide avec juste le titre
            RPROGLayoutDrawer.draw_page_header(pdf, width, height)
            current_y = start_y
            pdf.setFont("Helvetica-Bold", 14)
            pdf.setFillColor(dark_text_color)
            pdf.drawString(left_margin, current_y, "1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME")
            current_y -= 25
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(left_margin, current_y, "1.1. Les activités")
            current_y -= 30
            
            RPROGLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=start_page,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin,
                total_pages=getattr(cls, '_total_pages', None)
            )
            RAPPageManager.register_page_position("rprog_realisations_activites", start_page)
            return start_page + 1
        
        # Récupérer les paramètres de filtrage
        programme = data.get("programme", "")
        annee = data.get("annee", 2024)
        periode = data.get("periode", "")
        
        # Construire la requête pour récupérer les activités
        query = select(SuiviActivite).where(SuiviActivite.annee == annee)
        
        # Filtrer par programme si fourni
        if programme:
            query = query.where(SuiviActivite.programme.ilike(f"%{programme}%"))
        
        # Filtrer par période si fournie (semestre)
        if periode and "SEMESTRE" in periode.upper():
            # Extraire le numéro du semestre (1 ou 2)
            if "PREMIER" in periode.upper() or "1" in periode:
                query = query.where(SuiviActivite.periode_type == "semestre")
                query = query.where(SuiviActivite.periode_valeur == 1)
            elif "DEUXIEME" in periode.upper() or "2" in periode:
                query = query.where(SuiviActivite.periode_type == "semestre")
                query = query.where(SuiviActivite.periode_valeur == 2)
        
        # Exécuter la requête
        suivis_activites = session.exec(query.order_by(
            SuiviActivite.action,
            SuiviActivite.code_activite,
            SuiviActivite.libelle_activite
        )).all()
        
        logger.info(f"📊 {len(suivis_activites)} activités trouvées pour le programme {programme}, année {annee}, période {periode}")
        
        # Dessiner l'en-tête
        RPROGLayoutDrawer.draw_page_header(pdf, width, height)
        
        # Titre de section
        current_y = start_y
        pdf.setFont("Helvetica-Bold", 14)
        pdf.setFillColor(dark_text_color)
        pdf.drawString(left_margin, current_y, "1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME")
        current_y -= 25
        
        # Sous-titre
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left_margin, current_y, "1.1. Les activités")
        current_y -= 30
        
        # Titre du tableau
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left_margin, current_y, "Tableau 1: Mise en œuvre des activités")
        current_y -= 25
        
        # Calculer les largeurs des colonnes
        # Ajustement pour donner plus d'espace à "Preuve de réalisation"
        col_widths = [
            available_width * 0.22,  # Action/Activités
            available_width * 0.13,  # Structures responsables
            available_width * 0.18,  # Résultat attendu
            available_width * 0.18,  # Résultat opérationnel
            available_width * 0.15,  # Preuve de réalisation (augmenté de 0.10 à 0.15)
            available_width * 0.14,  # Observations (augmenté de 0.10 à 0.14)
        ]
        
        # Grouper les activités par action
        activites_par_action = {}
        for suivi in suivis_activites:
            action_key = suivi.action or suivi.code_activite or "Sans action"
            if action_key not in activites_par_action:
                activites_par_action[action_key] = []
            activites_par_action[action_key].append(suivi)
        
        # Créer un style pour les paragraphes (pour le wrapping du texte)
        styles = getSampleStyleSheet()
        para_style = styles['Normal']
        para_style.fontName = 'Helvetica'
        para_style.fontSize = 8
        para_style.leading = 10
        para_style.alignment = 0  # LEFT
        
        # Créer un style pour les en-têtes (gras, centré)
        header_style = styles['Normal']
        header_style.fontName = 'Helvetica-Bold'
        header_style.fontSize = 9
        header_style.leading = 11
        header_style.alignment = 1  # CENTER
        
        # Construire les données du tableau avec Table et TableStyle (comme dans le RAP)
        table_data = []
        
        # Fonction helper pour créer un Paragraph avec wrapping
        def create_para(text, max_width=None):
            """Crée un Paragraph avec wrapping automatique"""
            if not text:
                return ""
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return ""
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Paragraph gère automatiquement le wrapping selon la largeur de la colonne
            # Pas besoin de tronquer, le wrapping se fera automatiquement
            return Paragraph(text, para_style)
        
        # Fonction helper pour créer un Paragraph d'en-tête avec wrapping
        def create_header_para(text, max_width=None):
            """Crée un Paragraph d'en-tête avec wrapping automatique"""
            if not text:
                return ""
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return ""
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Paragraph gère automatiquement le wrapping selon la largeur de la colonne
            return Paragraph(text, header_style)
        
        # Ligne d'en-tête avec Paragraph pour permettre le wrapping
        table_data.append([
            create_header_para("Action/Activités", col_widths[0]),
            create_header_para("Structures responsables", col_widths[1]),
            create_header_para("Résultat attendu", col_widths[2]),
            create_header_para("Résultat opérationnel", col_widths[3]),
            create_header_para("Preuve de réalisation", col_widths[4]),
            create_header_para("Observations", col_widths[5])
        ])
        
        # Parcourir les actions pour construire les lignes de données
        for action_key, activites in activites_par_action.items():
            if len(activites) > 0:
                first_activite = activites[0]
                action_code = first_activite.code_activite or ""
                action_libelle = first_activite.action or action_key
                header_text = f"{action_code} {action_libelle}" if action_code else action_libelle
                
                # Ligne d'en-tête de groupe (action) - fusionnée sur les 3 premières colonnes
                merged_width = col_widths[0] + col_widths[1] + col_widths[2]
                table_data.append([
                    create_para(header_text, merged_width),  # Colonnes 0-2 fusionnées
                    "",            # Colonne 1 (vide car fusionnée)
                    "",            # Colonne 2 (vide car fusionnée)
                    "",            # Colonne 3
                    "",            # Colonne 4
                    "",            # Colonne 5
                ])
                
                # Lignes d'activités
                for activite in activites:
                    # Formater les données
                    libelle = activite.libelle_activite or ""
                    structures = activite.structures_responsables or ""
                    resultat_attendu = activite.resultat_attendu or ""
                    resultat_operationnel = activite.resultat_operationnel or ""
                    preuve = activite.preuve_filename or (activite.preuve_realisation or "")
                    observations = activite.observations or "RAS"
                    
                    # Ligne d'activité avec Paragraph pour le wrapping
                    table_data.append([
                        create_para(libelle, col_widths[0]),
                        create_para(structures, col_widths[1]),
                        create_para(resultat_attendu, col_widths[2]),
                        create_para(resultat_operationnel, col_widths[3]),
                        create_para(preuve, col_widths[4]),  # Preuve de réalisation avec wrapping
                        create_para(observations, col_widths[5]),
                    ])
        
        # Si aucune activité trouvée
        if len(suivis_activites) == 0:
            # Calculer la largeur totale pour le message (fusionné sur toutes les colonnes)
            total_width = sum(col_widths)
            table_data.append([
                create_para("Aucune activité enregistrée pour cette période.", total_width),
                "", "", "", "", "",
            ])
        
        # Créer le tableau avec Table (comme dans le RAP)
        table = Table(table_data, colWidths=col_widths, repeatRows=1)  # Répéter la ligne d'en-tête
        
        # Créer le style du tableau avec TableStyle (comme dans le RAP)
        table_style = [
            # Bordures
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            
            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fbe4d5")),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            
            # Alignement des données
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            
            # Fonts pour les données
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        
        # Ajouter les styles pour les lignes d'en-tête de groupe (actions)
        current_row = 1  # Commence après la ligne d'en-tête
        for action_key, activites in activites_par_action.items():
            if len(activites) > 0:
                # Ligne d'en-tête de groupe (action) - fusionner colonnes 0-2
                table_style.append(("SPAN", (0, current_row), (2, current_row)))
                table_style.append(("BACKGROUND", (0, current_row), (2, current_row), colors.HexColor("#F5F5F5")))
                table_style.append(("FONTNAME", (0, current_row), (2, current_row), "Helvetica-Bold"))
                table_style.append(("FONTSIZE", (0, current_row), (2, current_row), 9))
                table_style.append(("ALIGN", (0, current_row), (2, current_row), "LEFT"))
                current_row += 1
                
                # Lignes d'activités
                current_row += len(activites)
        
        # Si aucune activité trouvée, fusionner toutes les colonnes du message
        if len(suivis_activites) == 0:
            # La ligne du message est à l'index 1 (après l'en-tête)
            table_style.append(("SPAN", (0, 1), (-1, 1)))  # Fusionner toutes les colonnes
            table_style.append(("ALIGN", (0, 1), (-1, 1), "CENTER"))  # Centrer le message
        
        # Appliquer le style au tableau
        table.setStyle(TableStyle(table_style))
        
        # Calculer la hauteur du tableau
        table.wrapOn(pdf, available_width, height)
        table_height = table._height
        
        # Dessiner le tableau sur le canvas
        table_y = current_y - table_height
        if table_y < content_bottom:
            # Si le tableau ne rentre pas sur la page, le dessiner sur une nouvelle page
            pdf.showPage()
            RPROGLayoutDrawer.draw_page_header(pdf, width, height)
            current_y = start_y - 25
            table.wrapOn(pdf, available_width, height)
            table_height = table._height
            table_y = current_y - table_height
        
        # Dessiner le tableau
        table.drawOn(pdf, left_margin, table_y)
        
        # Mettre à jour current_y pour le footer
        current_y = table_y - 10
        
        # Dessiner le pied de page
        RPROGLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=start_page,
            width=width,
            footer_margin=footer_margin,
            footer_height=footer_height,
            right_margin=right_margin,
            total_pages=getattr(cls, '_total_pages', None)
        )
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("rprog_realisations_activites", start_page)
        RAPPageManager.register_page_position("rprog_realisations", start_page)
        RAPPageManager.register_page_position("rprog_tableau_1", start_page)
        
        return start_page + 1
    
    @classmethod
    def draw_realisations_credits(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la page "1.2. Les crédits budgétaires" avec le tableau d'exécution financière.
        
        Utilise Table et TableStyle de reportlab.platypus (comme dans le RAP)
        pour gérer les fusions de cellules.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après cette section
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from decimal import Decimal
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator, RAPPageManager
        from app.models.budget import SigobeExecution
        from sqlmodel import select
        
        # Marges
        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 3 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        
        # Couleur de texte
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Récupérer les données
        data = cls.data if hasattr(cls, 'data') and cls.data else {}
        session = cls._db_session if hasattr(cls, '_db_session') and cls._db_session else None
        
        if not session:
            logger.warning("⚠️ Pas de session DB disponible pour récupérer les données SIGOBE")
            # Créer une page vide avec juste le titre
            RPROGLayoutDrawer.draw_page_header(pdf, width, height)
            current_y = start_y
            pdf.setFont("Helvetica-Bold", 14)
            pdf.setFillColor(dark_text_color)
            pdf.drawString(left_margin, current_y, "1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME")
            current_y -= 25
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(left_margin, current_y, "1.2. Les crédits budgétaires")
            current_y -= 30
            
            RPROGLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=start_page,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin,
                total_pages=getattr(cls, '_total_pages', None)
            )
            RAPPageManager.register_page_position("rprog_realisations_credits", start_page)
            return start_page + 1
        
        # Récupérer les paramètres de filtrage
        programme = data.get("programme", "")
        annee = data.get("annee", 2024)
        periode = data.get("periode", "")
        
        # Construire la requête pour récupérer les données SIGOBE
        query = select(SigobeExecution).where(SigobeExecution.annee == annee)
        
        # Filtrer par programme si fourni
        if programme:
            query = query.where(SigobeExecution.programmes.ilike(f"%{programme}%"))
        
        # Filtrer par période si fournie (semestre)
        if periode and "SEMESTRE" in periode.upper():
            # Extraire le numéro du semestre (1 ou 2)
            if "PREMIER" in periode.upper() or "1" in periode:
                # Semestre 1 = trimestres 1 et 2
                query = query.where(
                    (SigobeExecution.trimestre == 1) | (SigobeExecution.trimestre == 2)
                )
            elif "DEUXIEME" in periode.upper() or "2" in periode:
                # Semestre 2 = trimestres 3 et 4
                query = query.where(
                    (SigobeExecution.trimestre == 3) | (SigobeExecution.trimestre == 4)
                )
        
        # Exécuter la requête
        sigobe_data = session.exec(query.order_by(
            SigobeExecution.actions,
            SigobeExecution.activites,
            SigobeExecution.type_depense
        )).all()
        
        logger.info(f"📊 {len(sigobe_data)} lignes SIGOBE trouvées pour le programme {programme}, année {annee}, période {periode}")
        
        # Dessiner l'en-tête
        RPROGLayoutDrawer.draw_page_header(pdf, width, height)
        
        # Titre de section
        current_y = start_y
        pdf.setFont("Helvetica-Bold", 14)
        pdf.setFillColor(dark_text_color)
        pdf.drawString(left_margin, current_y, "1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME")
        current_y -= 25
        
        # Sous-titre
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(left_margin, current_y, "1.2. Les crédits budgétaires")
        current_y -= 30
        
        # Titre du tableau
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left_margin, current_y, "Tableau 2: Exécution financière par action du programme")
        current_y -= 25
        
        # Organiser les données par action et activité
        actions_data = {}
        
        for sigobe in sigobe_data:
            action_code = sigobe.actions or "Sans action"
            activite_code = sigobe.activites or ""
            activite_libelle = activite_code
            type_depense = sigobe.type_depense or ""
            
            # Normaliser le type de dépense
            type_normalized = ""
            if type_depense:
                type_upper = type_depense.upper()
                if "PERSONNEL" in type_upper:
                    type_normalized = "PERSONNEL"
                elif "BIENS" in type_upper and "SERVICES" in type_upper:
                    type_normalized = "BIENS_ET_SERVICES"
                elif "INVESTISSEMENT" in type_upper:
                    type_normalized = "INVESTISSEMENTS"
            
            if not type_normalized:
                continue
            
            # Initialiser la structure si nécessaire
            if action_code not in actions_data:
                actions_data[action_code] = {
                    "action_libelle": action_code,
                    "activites": {}
                }
            
            if activite_code not in actions_data[action_code]["activites"]:
                actions_data[action_code]["activites"][activite_code] = {
                    "activite_libelle": activite_libelle,
                    "types_depense": {
                        "PERSONNEL": {"programme": Decimal(0), "realise": Decimal(0)},
                        "BIENS_ET_SERVICES": {"programme": Decimal(0), "realise": Decimal(0)},
                        "INVESTISSEMENTS": {"programme": Decimal(0), "realise": Decimal(0)}
                    }
                }
            
            # Ajouter les montants
            budget_actuel = sigobe.budget_actuel or Decimal(0)
            mandats_pec = sigobe.mandats_pec or Decimal(0)
            
            actions_data[action_code]["activites"][activite_code]["types_depense"][type_normalized]["programme"] += budget_actuel
            actions_data[action_code]["activites"][activite_code]["types_depense"][type_normalized]["realise"] += mandats_pec
        
        # Calculer les largeurs des colonnes
        col_widths = [
            available_width * 0.25,  # Action/Activités (augmenté)
            available_width * 0.11,  # Personnel Programmé
            available_width * 0.11,  # Personnel Réalisé
            available_width * 0.11,  # Biens et services Programmé
            available_width * 0.11,  # Biens et services Réalisé
            available_width * 0.11,  # Investissements Programmé
            available_width * 0.11,  # Investissements Réalisé
            available_width * 0.09,  # Observations
        ]
        
        # Fonction pour formater un montant
        def format_montant(montant: Decimal) -> str:
            if montant == 0:
                return "0"
            return f"{int(montant):,}".replace(",", " ")
        
        # Créer un style pour les paragraphes (pour le wrapping du texte)
        styles = getSampleStyleSheet()
        para_style_table2 = styles['Normal']
        para_style_table2.fontName = 'Helvetica'
        para_style_table2.fontSize = 8
        para_style_table2.leading = 10
        para_style_table2.alignment = 0  # LEFT
        
        # Fonction helper pour créer un Paragraph avec wrapping
        def create_para_table2(text, max_width=None):
            """Crée un Paragraph avec wrapping automatique pour le Tableau 2"""
            if not text:
                return ""
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return ""
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Paragraph gère automatiquement le wrapping selon la largeur de la colonne
            return Paragraph(text, para_style_table2)
        
        # Construire les données du tableau avec Table et TableStyle (comme dans le RAP)
        table_data = []
        
        # Ligne 0 : Première ligne d'en-tête
        table_data.append([
            "Actions/Activités",
            "Personnel",
            "",
            "Biens et services",
            "",
            "Investissements",
            "",
            "Observations",
        ])
        
        # Ligne 1 : Deuxième ligne d'en-tête (Programmé/Réalisé)
        table_data.append([
            "",
            "Programmé",
            "Réalisé",
            "Programmé",
            "Réalisé",
            "Programmé",
            "Réalisé",
            "",
        ])
        
        # Parcourir les actions pour construire les lignes de données
        for action_code, action_data in actions_data.items():
            action_libelle = action_data["action_libelle"]
            activites = action_data["activites"]
            
            # Calculer les totaux pour cette action
            total_personnel_prog = Decimal(0)
            total_personnel_real = Decimal(0)
            total_biens_prog = Decimal(0)
            total_biens_real = Decimal(0)
            total_inv_prog = Decimal(0)
            total_inv_real = Decimal(0)
            
            # Ligne d'en-tête de groupe (action)
            table_data.append([
                action_libelle,
                "", "", "", "", "", "",
                "",
            ])
            
            # Lignes d'activités
            for activite_code, activite_data in activites.items():
                activite_libelle = activite_data["activite_libelle"]
                types_depense = activite_data["types_depense"]
                
                # Récupérer les montants
                personnel_prog = types_depense["PERSONNEL"]["programme"]
                personnel_real = types_depense["PERSONNEL"]["realise"]
                biens_prog = types_depense["BIENS_ET_SERVICES"]["programme"]
                biens_real = types_depense["BIENS_ET_SERVICES"]["realise"]
                inv_prog = types_depense["INVESTISSEMENTS"]["programme"]
                inv_real = types_depense["INVESTISSEMENTS"]["realise"]
                
                # Ajouter aux totaux
                total_personnel_prog += personnel_prog
                total_personnel_real += personnel_real
                total_biens_prog += biens_prog
                total_biens_real += biens_real
                total_inv_prog += inv_prog
                total_inv_real += inv_real
                
                # Ligne d'activité
                table_data.append([
                    activite_libelle,
                    format_montant(personnel_prog),
                    format_montant(personnel_real),
                    format_montant(biens_prog),
                    format_montant(biens_real),
                    format_montant(inv_prog),
                    format_montant(inv_real),
                    "",
                ])
            
            # Ligne de total pour cette action
            table_data.append([
                f"Total {action_libelle}",
                format_montant(total_personnel_prog),
                format_montant(total_personnel_real),
                format_montant(total_biens_prog),
                format_montant(total_biens_real),
                format_montant(total_inv_prog),
                format_montant(total_inv_real),
                "",
            ])
        
        # Si aucune donnée trouvée
        if len(actions_data) == 0:
            # Calculer la largeur totale pour le message (fusionné sur toutes les colonnes)
            total_width = sum(col_widths)
            table_data.append([
                create_para_table2("Aucune donnée d'exécution financière trouvée pour cette période.", total_width),
                "", "", "", "", "", "", "",
            ])
        
        # Créer le tableau avec Table (comme dans le RAP)
        table = Table(table_data, colWidths=col_widths, repeatRows=2)
        
        # Créer le style du tableau avec TableStyle (comme dans le RAP)
        table_style = [
            # Bordures
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            
            # En-têtes
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fbe4d5")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fbe4d5")),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, 1), 8),
            
            # Fusionner les cellules de l'en-tête (comme dans le RAP)
            ("SPAN", (1, 0), (2, 0)),  # Personnel
            ("SPAN", (3, 0), (4, 0)),  # Biens et services
            ("SPAN", (5, 0), (6, 0)),  # Investissements
            ("SPAN", (0, 0), (0, 1)),  # Actions/Activités
            ("SPAN", (7, 0), (7, 1)),  # Observations
            
            # Alignement des données
            ("ALIGN", (0, 2), (0, -1), "LEFT"),
            ("ALIGN", (1, 2), (6, -1), "RIGHT"),
            ("ALIGN", (7, 2), (7, -1), "LEFT"),
            ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
            
            # Fonts pour les données
            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 2), (-1, -1), 8),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        
        # Ajouter les styles pour les lignes d'en-tête de groupe (actions) et totaux
        current_row = 2  # Commence après les 2 lignes d'en-tête
        for action_code, action_data in actions_data.items():
            activites = action_data["activites"]
            num_activites = len(activites)
            
            # Ligne d'en-tête de groupe (action) - fusionner colonnes 0-6
            table_style.append(("SPAN", (0, current_row), (6, current_row)))
            table_style.append(("BACKGROUND", (0, current_row), (6, current_row), colors.HexColor("#F5F5F5")))
            table_style.append(("FONTNAME", (0, current_row), (6, current_row), "Helvetica-Bold"))
            table_style.append(("FONTSIZE", (0, current_row), (6, current_row), 9))
            table_style.append(("ALIGN", (0, current_row), (6, current_row), "LEFT"))
            current_row += 1
            
            # Lignes d'activités (styling déjà appliqué globalement)
            current_row += num_activites
            
            # Ligne de total - fusionner colonnes 0-6
            table_style.append(("SPAN", (0, current_row), (6, current_row)))
            table_style.append(("FONTNAME", (0, current_row), (6, current_row), "Helvetica-Bold"))
            table_style.append(("FONTSIZE", (0, current_row), (6, current_row), 8))
            table_style.append(("ALIGN", (0, current_row), (6, current_row), "LEFT"))
            current_row += 1
        
        # Si aucune donnée trouvée, fusionner toutes les colonnes du message
        if len(actions_data) == 0:
            # La ligne du message est à l'index 2 (après les 2 lignes d'en-tête)
            table_style.append(("SPAN", (0, 2), (-1, 2)))  # Fusionner toutes les colonnes
            table_style.append(("ALIGN", (0, 2), (-1, 2), "CENTER"))  # Centrer le message
        
        # Appliquer le style au tableau
        table.setStyle(TableStyle(table_style))
        
        # Calculer la hauteur du tableau (wrapping nécessaire)
        table.wrapOn(pdf, available_width, height)
        table_height = table._height
        
        # Dessiner le tableau sur le canvas
        table_y = current_y - table_height
        if table_y < content_bottom:
            # Si le tableau ne rentre pas, nouvelle page
            pdf.showPage()
            RPROGLayoutDrawer.draw_page_header(pdf, width, height)
            current_y = start_y - 60
            table.wrapOn(pdf, available_width, height)
            table_height = table._height
            table_y = current_y - table_height
        
        # Dessiner le tableau (la méthode drawOn gère automatiquement les fusions de cellules)
        table.drawOn(pdf, left_margin, table_y)
        
        # Dessiner le pied de page
        RPROGLayoutDrawer.draw_page_footer(
            pdf=pdf,
            page_number=start_page,
            width=width,
            footer_margin=footer_margin,
            footer_height=footer_height,
            right_margin=right_margin,
            total_pages=getattr(cls, '_total_pages', None)
        )
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("rprog_realisations_credits", start_page)
        RAPPageManager.register_page_position("rprog_tableau_2", start_page)
        
        return start_page + 1




# ============================================================================
# ORCHESTRATEUR PRINCIPAL - GÉNÉRATION COMPLÈTE DU PDF
# ============================================================================

class RPROGPDFGenerator(RPROGBaseGenerator):
    """
    Orchestrateur principal pour la génération du Rapport d'Activité RPROG.
    
    Cette classe coordonne la génération de toutes les pages du rapport :
    1. Couverture
    2. Sommaire
    3. Liste des tableaux
    4. Liste des figures
    5. Contenu principal (à implémenter selon les besoins)
    
    Réutilise les classes RAPLayoutDrawer et RAPContentDrawer pour
    les pages communes (couverture, sommaire, listes).
    """
    
    @classmethod
    def generate_pdf(cls, data: dict[str, Any], session=None) -> BytesIO:
        """
        Génère le PDF complet du Rapport d'Activité RPROG.
        
        Args:
            data: Dictionnaire contenant toutes les données du rapport
            session: Session de base de données (optionnel)
        
        Returns:
            BytesIO contenant le PDF généré
        """
        logger.info("📄 Début de la génération du Rapport d'Activité RPROG...")
        
        # Initialiser les données et la session
        # Les données doivent être définies dans la classe de base pour être accessibles
        # par toutes les classes qui héritent (RPROGLayoutDrawer, RPROGContentDrawer, etc.)
        # Comme RPROGBaseGenerator hérite de RAPBaseGenerator, on définit dans RAPBaseGenerator
        # pour que toutes les classes puissent y accéder via cls.data
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator
        RAPBaseGenerator.data = data
        RAPBaseGenerator._db_session = session
        # Aussi définir dans les classes RPROG pour compatibilité
        RPROGBaseGenerator.data = data
        RPROGBaseGenerator._db_session = session
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
        RPROGLayoutDrawer.draw_cover_page(cover_pdf, width, height)
        cover_pdf.save()
        cover_buffer.seek(0)
        
        # ====================================================================
        # 2. GÉNÉRER LE SOMMAIRE (sera régénéré après avec les bonnes pages)
        # ====================================================================
        logger.info("📄 Génération du sommaire temporaire...")
        sommaire_temp_buffer = BytesIO()
        sommaire_temp_pdf = canvas.Canvas(sommaire_temp_buffer, pagesize=landscape(A4))
        # Le sommaire sera régénéré après avec les bonnes pages
        sommaire_temp_pdf.save()
        sommaire_temp_buffer.seek(0)
        
        # Compter les pages du sommaire temporaire pour calculer le start_page de la liste des tableaux
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
        next_page = RPROGContentDrawer.draw_liste_tableaux(
            liste_tableaux_pdf, width, height, liste_tableaux_start_page,
            pdf_reader_complet=None, nb_pages_sommaire=0
        )
        liste_tableaux_pdf.save()
        liste_tableaux_buffer.seek(0)
        
        # Enregistrer la position de la liste des tableaux
        RAPPageManager.register_page_position("liste_tableaux", liste_tableaux_start_page)
        
        # ====================================================================
        # 4. GÉNÉRER L'INTRODUCTION
        # ====================================================================
        logger.info("📄 Génération de l'introduction...")
        introduction_buffer = BytesIO()
        introduction_pdf = canvas.Canvas(introduction_buffer, pagesize=landscape(A4))
        # L'introduction commence après la liste des tableaux
        introduction_start_page = next_page
        next_page = RPROGContentDrawer.draw_introduction(
            introduction_pdf, width, height, introduction_start_page
        )
        introduction_pdf.save()
        introduction_buffer.seek(0)
        
        # ====================================================================
        # 5. GÉNÉRER LA SECTION "1.1. LES ACTIVITÉS"
        # ====================================================================
        logger.info("📄 Génération de la section '1.1. Les activités'...")
        activites_buffer = BytesIO()
        activites_pdf = canvas.Canvas(activites_buffer, pagesize=landscape(A4))
        # La section activités commence après l'introduction
        activites_start_page = next_page
        next_page = RPROGContentDrawer.draw_realisations_activites(
            activites_pdf, width, height, activites_start_page
        )
        activites_pdf.save()
        activites_buffer.seek(0)
        
        # ====================================================================
        # 6. GÉNÉRER LA SECTION "1.2. LES CRÉDITS BUDGÉTAIRES"
        # ====================================================================
        logger.info("📄 Génération de la section '1.2. Les crédits budgétaires'...")
        credits_buffer = BytesIO()
        credits_pdf = canvas.Canvas(credits_buffer, pagesize=landscape(A4))
        # La section crédits commence après la section activités
        credits_start_page = next_page
        next_page = RPROGContentDrawer.draw_realisations_credits(
            credits_pdf, width, height, credits_start_page
        )
        credits_pdf.save()
        credits_buffer.seek(0)
        
        # ====================================================================
        # 7. GÉNÉRER LE CONTENU PRINCIPAL (autres sections)
        # ====================================================================
        # TODO: Implémenter la génération des autres sections du contenu principal
        # Pour l'instant, on crée juste une page vide pour la structure
        logger.info("📄 Génération du contenu principal (autres sections)...")
        content_buffer = BytesIO()
        content_pdf = canvas.Canvas(content_buffer, pagesize=landscape(A4))
        # TODO: Ajouter les autres sections ici (1.3, 1.4, 2, 3, Conclusion)
        content_pdf.save()
        content_buffer.seek(0)
        
        # ====================================================================
        # 6. GÉNÉRER LE SOMMAIRE FINAL (avec les bonnes pages)
        # ====================================================================
        logger.info("📄 Génération du sommaire final avec les pages correctes...")
        sommaire_buffer = BytesIO()
        sommaire_pdf = canvas.Canvas(sommaire_buffer, pagesize=landscape(A4))
        
        # Utiliser les pages enregistrées (déjà dans RAPPageManager._page_positions)
        
        RPROGContentDrawer.draw_table_of_contents(
            sommaire_pdf, width, height, pdf_reader_complet=None, nb_pages_sommaire=0
        )
        sommaire_pdf.save()
        sommaire_buffer.seek(0)
        
        # ====================================================================
        # 5. CALCULER LE NOMBRE TOTAL DE PAGES
        # ====================================================================
        # Compter les pages de chaque section pour calculer le total
        cover_reader = PdfReader(cover_buffer)
        sommaire_reader = PdfReader(sommaire_buffer)
        liste_tableaux_reader = PdfReader(liste_tableaux_buffer)
        introduction_reader = PdfReader(introduction_buffer)
        activites_reader = PdfReader(activites_buffer)
        credits_reader = PdfReader(credits_buffer)
        content_reader = PdfReader(content_buffer)
        
        total_pages = (
            len(cover_reader.pages) +
            len(sommaire_reader.pages) +
            len(liste_tableaux_reader.pages) +
            len(introduction_reader.pages) +
            len(activites_reader.pages) +
            len(credits_reader.pages) +
            len(content_reader.pages)
        )
        
        logger.info(f"📊 Nombre total de pages calculé: {total_pages}")
        
        # Stocker le total_pages dans la classe pour qu'il soit accessible dans les méthodes
        cls._total_pages = total_pages
        RPROGLayoutDrawer._total_pages = total_pages
        RPROGContentDrawer._total_pages = total_pages
        
        # ====================================================================
        # 6. RÉGÉNÉRER LES PDFs AVEC LE BON TOTAL_PAGES DANS LES FOOTERS
        # ====================================================================
        logger.info("🔄 Régénération des PDFs avec le bon total de pages...")
        
        # Régénérer le sommaire avec le bon total_pages
        sommaire_buffer = BytesIO()
        sommaire_pdf = canvas.Canvas(sommaire_buffer, pagesize=landscape(A4))
        RPROGContentDrawer.draw_table_of_contents(
            sommaire_pdf, width, height, pdf_reader_complet=None, nb_pages_sommaire=0
        )
        sommaire_pdf.save()
        sommaire_buffer.seek(0)
        
        # Calculer le numéro de page de départ de la liste des tableaux
        # Après la couverture (1 page) et le sommaire
        sommaire_reader_temp = PdfReader(sommaire_buffer)
        liste_tableaux_start_page = 1 + len(sommaire_reader_temp.pages) + 1  # Couverture (1) + sommaire + 1
        
        # Régénérer la liste des tableaux avec le bon total_pages et le bon start_page
        liste_tableaux_buffer = BytesIO()
        liste_tableaux_pdf = canvas.Canvas(liste_tableaux_buffer, pagesize=landscape(A4))
        RPROGContentDrawer.draw_liste_tableaux(
            liste_tableaux_pdf, width, height, liste_tableaux_start_page,
            pdf_reader_complet=None, nb_pages_sommaire=0
        )
        liste_tableaux_pdf.save()
        liste_tableaux_buffer.seek(0)
        
        # Régénérer l'introduction avec le bon total_pages
        introduction_buffer = BytesIO()
        introduction_pdf = canvas.Canvas(introduction_buffer, pagesize=landscape(A4))
        # Calculer le numéro de page de départ de l'introduction
        liste_tableaux_reader_temp = PdfReader(liste_tableaux_buffer)
        introduction_start_page = 1 + len(sommaire_reader_temp.pages) + len(liste_tableaux_reader_temp.pages) + 1
        RPROGContentDrawer.draw_introduction(
            introduction_pdf, width, height, introduction_start_page
        )
        introduction_pdf.save()
        introduction_buffer.seek(0)
        
        # Régénérer la section "1.1. Les activités" avec le bon total_pages
        activites_buffer = BytesIO()
        activites_pdf = canvas.Canvas(activites_buffer, pagesize=landscape(A4))
        # Calculer le numéro de page de départ
        introduction_reader_temp = PdfReader(introduction_buffer)
        activites_start_page = 1 + len(sommaire_reader_temp.pages) + len(liste_tableaux_reader_temp.pages) + len(introduction_reader_temp.pages) + 1
        RPROGContentDrawer.draw_realisations_activites(
            activites_pdf, width, height, activites_start_page
        )
        activites_pdf.save()
        activites_buffer.seek(0)
        
        # Régénérer la section "1.2. Les crédits budgétaires" avec le bon total_pages
        credits_buffer = BytesIO()
        credits_pdf = canvas.Canvas(credits_buffer, pagesize=landscape(A4))
        # Calculer le numéro de page de départ
        activites_reader_temp = PdfReader(activites_buffer)
        credits_start_page = 1 + len(sommaire_reader_temp.pages) + len(liste_tableaux_reader_temp.pages) + len(introduction_reader_temp.pages) + len(activites_reader_temp.pages) + 1
        RPROGContentDrawer.draw_realisations_credits(
            credits_pdf, width, height, credits_start_page
        )
        credits_pdf.save()
        credits_buffer.seek(0)
        
        # TODO: Régénérer les autres sections du contenu principal avec le bon total_pages
        # Pour l'instant, on garde le contenu tel quel
        
        # ====================================================================
        # 7. FUSIONNER TOUS LES PDFs DANS LE BON ORDRE
        # ====================================================================
        logger.info("📎 Fusion de tous les PDFs...")
        
        writer = PdfWriter()
        
        # 1. Couverture (page 1)
        cover_reader = PdfReader(cover_buffer)
        writer.add_page(cover_reader.pages[0])
        
        # 2. Sommaire (page 2+)
        sommaire_reader = PdfReader(sommaire_buffer)
        for page in sommaire_reader.pages:
            writer.add_page(page)
        
        # 3. Liste des tableaux
        liste_tableaux_reader = PdfReader(liste_tableaux_buffer)
        for page in liste_tableaux_reader.pages:
            writer.add_page(page)
        
        # 4. Introduction
        introduction_reader = PdfReader(introduction_buffer)
        for page in introduction_reader.pages:
            writer.add_page(page)
        
        # 5. Section "1.1. Les activités"
        activites_reader = PdfReader(activites_buffer)
        for page in activites_reader.pages:
            writer.add_page(page)
        
        # 6. Section "1.2. Les crédits budgétaires"
        credits_reader = PdfReader(credits_buffer)
        for page in credits_reader.pages:
            writer.add_page(page)
        
        # 7. Contenu principal (autres sections)
        content_reader = PdfReader(content_buffer)
        for page in content_reader.pages:
            writer.add_page(page)
        
        # Écrire le PDF final
        final_buffer = BytesIO()
        writer.write(final_buffer)
        final_buffer.seek(0)
        
        logger.info("✅ Génération du Rapport d'Activité RPROG terminée")
        
        return final_buffer

