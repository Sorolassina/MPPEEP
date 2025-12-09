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
import re
from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, LongTable, Frame, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
        # Vérifier le mode pour déterminer la couleur
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        if mode == "final":
            from reportlab.lib import colors
            section_color = colors.HexColor("#000000")  # Noir en mode final
        else:
            section_color = RAPStylingManager._get_color_for_source(section_source)  # Rouge en brouillon
        pdf.saveState()
        pdf.setFillColor(section_color)
        pdf.drawCentredString(center_x, content_current_y, section + " :")
        pdf.restoreState()
        content_current_y -= 20  # Espace après la section

        # ---------- MINISTÈRE ----------
        if ministere:
            # Taille de police augmentée pour le RPROG (13 au lieu de 11)
            pdf.setFont("Helvetica-BoldOblique", 13)
            # Vérifier le mode pour déterminer la couleur
            if mode == "final":
                from reportlab.lib import colors
                ministere_color = colors.HexColor("#000000")  # Noir en mode final
            else:
                ministere_color = RAPStylingManager._get_color_for_source(ministere_source)  # Rouge en brouillon
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
        
        # Déterminer la couleur du titre (rouge en brouillon, noir en final)
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else (RPROGBaseGenerator.data.get("mode", "brouillon") if hasattr(RPROGBaseGenerator, 'data') and RPROGBaseGenerator.data else "brouillon")
        if mode == "final":
            from reportlab.lib import colors
            titre_color = colors.HexColor("#000000")  # Noir en mode final
        else:
            titre_color = RAPStylingManager._get_color_for_source("db")  # Rouge en brouillon
        
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
            # Utiliser la même couleur et police que le titre (noir en final, rouge en brouillon)
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else (RPROGBaseGenerator.data.get("mode", "brouillon") if hasattr(RPROGBaseGenerator, 'data') and RPROGBaseGenerator.data else "brouillon")
            if mode == "final":
                from reportlab.lib import colors
                responsable_color = colors.HexColor("#000000")  # Noir en mode final
            else:
                responsable_color = RAPStylingManager._get_color_for_source("db")  # Rouge en brouillon
            
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
        
        # Récupérer la position de la liste des tableaux pour calculer l'introduction
        liste_tableaux_page = get_page("liste_tableaux", base_page)
        # L'introduction commence après la liste des tableaux
        # La liste des tableaux prend généralement 1 page, donc l'introduction commence à liste_tableaux_page + 1
        # Mais si la position de l'introduction est déjà enregistrée, elle sera utilisée
        intro_page_default = liste_tableaux_page + 1
        
        # Récupérer les pages dynamiquement pour chaque section
        intro_page = get_page("rprog_introduction", intro_page_default)
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
        """
        from reportlab.platypus import Frame, LongTable
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus.doctemplate import LayoutError

        logger.info(
            f"🔢 NUMÉROTATION - _render_multipage_story DÉBUT: "
            f"page_num={page_num}, {len(story)} éléments dans story"
        )
        logger.info(
            f"📏 FRAME INIT: x={frame_x:.2f}, y={frame_y:.2f}, "
            f"width={frame_width:.2f}, height={frame_height:.2f}"
        )

        first_page = True
        current_page = page_num
        max_iterations = 1000  # Protection contre les boucles infinies
        iteration_count = 0

        while story and iteration_count < max_iterations:
            iteration_count += 1

            # Mettre à jour la variable de classe pour que les PageMarker puissent l'utiliser
            RPROGBaseGenerator._current_rendering_page = current_page

            # La première page est déjà créée avant l'appel
            # Pour les pages suivantes, on ne crée la page QUE si on a encore des éléments à rendre
            if not first_page and len(story) > 0:
                logger.info(
                    f"🔢 NUMÉROTATION - showPage() dans _render_multipage_story, "
                    f"nouvelle page {current_page}"
                )
                pdf.showPage()
                # Redessiner l'en-tête sur les nouvelles pages
                RPROGLayoutDrawer.draw_page_header(
                    pdf,
                    page_width,
                    A4[1] if page_width < A4[1] else A4[0],
                )

            frame = Frame(
                frame_x,
                frame_y,
                frame_width,
                frame_height,
                showBoundary=0,  # Désactivé maintenant que le tableau s'affiche
            )

            logger.info(
                f"📏 FRAME PAGE {current_page}: x={frame_x:.2f}, y={frame_y:.2f}, "
                f"width={frame_width:.2f}, height={frame_height:.2f}"
            )

            pdf.saveState()

            before = len(story)
            logger.info(
                f"🔢 NUMÉROTATION - Rendu page {current_page} "
                f"(itération {iteration_count}): {before} éléments restants"
            )

            try:
                # IMPORTANT : Comme dans le RAP, on fait confiance à ReportLab pour gérer le LongTable
                # - LongTable peut se dessiner sur plusieurs pages
                # - Il reste dans 'story' tant qu'il n'est pas fini
                #   => len(story) peut rester identique d'une page à l'autre
                
                # IMPORTANT : Comme dans le RAP, on appelle directement frame.addFromList()
                # sans faire de wrap() préalable. ReportLab gère automatiquement la division
                # du LongTable avec splitByRow=1. Un appel à wrap() avant pourrait perturber
                # le processus de division automatique.
                frame.addFromList(story, pdf)
            except LayoutError as e:
                logger.error(
                    f"   ❌ LayoutError sur la page {current_page}: {e}. "
                    f"Arrêt du rendu pour éviter un blocage."
                )
                logger.error(f"   📋 Détails de l'erreur: {type(e).__name__}: {str(e)}")
                if story and isinstance(story[0], LongTable):
                    logger.warning(
                        "   ⚠️ LayoutError avec LongTable - probablement un problème de "
                        "hauteur disponible ou de SPAN."
                    )
                pdf.restoreState()
                break
            except Exception as e:
                logger.error(
                    f"   ❌ Exception inattendue lors du rendu sur la page "
                    f"{current_page}: {type(e).__name__}: {e}"
                )
                import traceback
                logger.error(f"   📋 Traceback: {traceback.format_exc()}")
                pdf.restoreState()
                break

            after = len(story)
            consumed = before - after
            logger.info(f"   ✅ Page {current_page}: {consumed} éléments consommés, {after} restants")
            
            # Vérifier si un LongTable est encore dans la story
            if story and isinstance(story[0], LongTable):
                logger.info(f"   📊 LongTable toujours présent dans story (pas encore terminé)")
                # Vérifier combien de lignes ont été rendues en inspectant le LongTable
                if hasattr(story[0], '_rowNos'):
                    logger.info(f"   📊 LongTable._rowNos: {story[0]._rowNos if hasattr(story[0], '_rowNos') else 'N/A'}")

            pdf.restoreState()

            # ⚠️ On NE TESTE PLUS (after == before)
            # Car pour LongTable, len(story) peut rester constant
            # tout en avançant dans le tableau.

            # Footer / numéro de page
            if show_page_number:
                logger.info(f"🔢 NUMÉROTATION - Footer pour page {current_page}")
                if draw_footer_func:
                    draw_footer_func(current_page)
                else:
                    from reportlab.lib.units import cm
                    footer_height = 2 * cm
                    footer_margin = 0.8 * cm
                    RPROGLayoutDrawer.draw_page_footer(
                        pdf=pdf,
                        page_number=current_page,
                        width=page_width,
                        footer_margin=footer_margin,
                        footer_height=footer_height,
                        right_margin=3 * cm,
                        total_pages=getattr(cls, '_total_pages', None),
                    )

            logger.info(f"🔢 NUMÉROTATION - page_num avant incrément: {current_page}")
            current_page += 1
            logger.info(f"🔢 NUMÉROTATION - page_num après incrément: {current_page}")
            first_page = False

        # Réinitialiser la variable de classe
        RPROGBaseGenerator._current_rendering_page = None

        logger.info(
            f"🔢 NUMÉROTATION - _render_multipage_story FIN: "
            f"retourne current_page={current_page} "
            f"(page suivante après la dernière dessinée)"
        )
        return current_page

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
        
        Utilise la story-based approach avec _render_multipage_story() comme le RAP.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après l'introduction
        """
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPBaseGenerator, RAPPageManager
        
        # Marges
        left_margin = 3 * cm
        right_margin = 3 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin
        
        # Dessiner l'en-tête (simple, sans éléments de couverture)
        RPROGLayoutDrawer.draw_page_header(pdf, width, height)
        
        # Créer les styles pour les paragraphes
        styles = getSampleStyleSheet()
        
        # Style pour le titre
        title_style = ParagraphStyle(
            "IntroTitle",
            parent=styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=0,  # LEFT
            spaceAfter=20,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Style pour le texte du corps
        body_style = ParagraphStyle(
            "IntroBody",
            parent=styles['Normal'],
            fontName="Helvetica",
            fontSize=12,  # Taille standard pour tout le document
            leading=15,  # Leading ajusté pour fontSize=12
            alignment=4,  # JUSTIFY
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Récupérer les données du programme
        data = cls.data if hasattr(cls, 'data') and cls.data else {}
        programme = data.get("programme", "PROGRAMME PORTEFEUILLE DE L'ETAT")
        annee = data.get("annee", 2024)
        
        # Fonction helper pour formater les nombres à 2 chiffres (04 au lieu de 4)
        def format_two_digits(value):
            """Formate un nombre à 2 chiffres (04 au lieu de 4 pour les nombres de 0 à 9)"""
            if not value or value == "":
                return ""
            try:
                num = int(value)
                return f"{num:02d}"  # Format à 2 chiffres avec zéro devant
            except (ValueError, TypeError):
                # Si ce n'est pas un nombre, retourner tel quel
                return str(value)
        
        # Fonction helper pour déterminer si on est en mode final (document final ou impression Word)
        def is_final_mode():
            """Retourne True si on est en mode final (pas de rouge, pas de placeholders)"""
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
            return mode == "final"
        
        # Fonction helper pour formater les valeurs dynamiques
        def format_dynamic_value(value, default_placeholder=".................."):
            """Formate une valeur dynamique (rouge en brouillon, noir en final, sans placeholder en final)"""
            final_mode = is_final_mode()
            if value is None or value == "":
                if final_mode:
                    # En mode final, retourner une chaîne vide au lieu du placeholder
                    return ""
                else:
                    # En mode brouillon, retourner le placeholder en rouge
                    return f'<font color="#FF0000">{default_placeholder}</font>'
            value_str = str(value)
            if final_mode:
                # En mode final, texte en noir
                return value_str
            else:
                # En mode brouillon, texte en rouge
                return f'<font color="#FF0000">{value_str}</font>'
        
        # Récupérer les valeurs dynamiques depuis les données (valeurs par défaut)
        plan_strategique = data.get("plan_strategique", "")
        nb_objectifs = data.get("nb_objectifs", "")
        nb_actions = data.get("nb_actions", "")
        budget_actuel = data.get("budget_actuel", "")
        depenses_personnel = data.get("depenses_personnel", "")
        depenses_biens_services = data.get("depenses_biens_services", "")
        investissements = data.get("investissements", "")
        numero_decret = data.get("numero_decret", "")
        date_decret = data.get("date_decret", "")
        ministere = data.get("ministere", "")
        services_directions = data.get("services_directions", [])
        
        # Récupérer le programme depuis la base de données pour les requêtes
        session = cls._db_session if hasattr(cls, '_db_session') and cls._db_session else None
        programme_obj = None
        missions = data.get("missions", "")  # Récupérer les missions depuis les données (ou vide par défaut)
        
        if not session:
            logger.warning("⚠️ Aucune session de base de données disponible. Les données dynamiques ne pourront pas être récupérées.")
        else:
            logger.info("✅ Session de base de données disponible")
        
        # Formater les valeurs en rouge
        programme_formatted = format_dynamic_value(programme)
        missions_formatted = format_dynamic_value(missions, "..............")
        plan_strategique_formatted = format_dynamic_value(plan_strategique, "..............")
        nb_objectifs_formatted = format_dynamic_value(nb_objectifs, "..............")
        nb_actions_formatted = format_dynamic_value(nb_actions, "..............")
        budget_actuel_formatted = format_dynamic_value(budget_actuel, "..............")
        depenses_personnel_formatted = format_dynamic_value(depenses_personnel, "..............")
        depenses_biens_services_formatted = format_dynamic_value(depenses_biens_services, "..............")
        investissements_formatted = format_dynamic_value(investissements, "..............")
        
        # Formater le numéro et la date du décret
        numero_decret_formatted = format_dynamic_value(numero_decret, "..............")
        date_decret_formatted = format_dynamic_value(date_decret, "..............")
        decret_complet_formatted = f"n° {numero_decret_formatted} du {date_decret_formatted}"
        
        # Formater le nom du ministère
        ministere_formatted = format_dynamic_value(ministere, "..............")
        
        # Récupérer la liste des services et directions depuis la base de données
        services_directions_list = []
        
        if session:
            try:
                from app.models.personnel import Direction, SousDirection, Service
                from sqlmodel import select, and_
                
                # Charger le programme via ReportDataLoader
                if programme:
                    logger.info("=" * 80)
                    logger.info("🔍 === DÉBUT CHARGEMENT PROGRAMME (ReportDataLoader) ===")
                    logger.info("=" * 80)
                    logger.info(f"🔍 Chargement du programme: '{programme}'")
                    
                    from app.services.report_data_loader import ReportDataLoader
                    
                    programmes_data = ReportDataLoader.load_data_programmes(
                        session, 
                        programme_nom=programme,
                        annee=annee,
                        include_sigobe_stats=False
                    )
                    programme_obj = programmes_data.get("programme")
                    
                    if programme_obj:
                        logger.info(f"✅ Programme '{programme}' trouvé avec ID: {programme_obj.id} | Code: {programme_obj.code} | Libellé: {programme_obj.libelle}")
                        
                        # Récupérer les missions du programme
                        if programme_obj.missions:
                            missions = programme_obj.missions
                            missions_formatted = format_dynamic_value(missions, "assurer la gestion efficace du portefeuille de l'Etat à travers la coordination des activités de la DGPE")
                            logger.info(f"🔄 missions_formatted mis à jour: '{missions_formatted[:80]}...'")
                        
                        logger.info("=" * 80)
                        logger.info("✅ === FIN CHARGEMENT PROGRAMME (SUCCÈS) ===")
                        logger.info("=" * 80)
                    else:
                        logger.warning(f"⚠️ Programme '{programme}' non trouvé dans la base de données")
                        logger.info("=" * 80)
                        logger.info("❌ === FIN CHARGEMENT PROGRAMME (NON TROUVÉ) ===")
                        logger.info("=" * 80)
                
                if programme_obj:
                    # Récupérer les directions directement rattachées au programme
                    directions_query = select(Direction).where(
                        and_(
                            Direction.programme_id == programme_obj.id,
                            Direction.actif == True
                        )
                    ).order_by(Direction.libelle)
                    directions = session.exec(directions_query).all()
                    
                    # Récupérer les sous-directions directement rattachées au programme
                    sous_directions_query = select(SousDirection).where(
                        and_(
                            SousDirection.programme_id == programme_obj.id,
                            SousDirection.actif == True
                        )
                    ).order_by(SousDirection.libelle)
                    sous_directions = session.exec(sous_directions_query).all()
                    
                    # Récupérer les services directement rattachés au programme
                    services_query = select(Service).where(
                        and_(
                            Service.programme_id == programme_obj.id,
                            Service.actif == True
                        )
                    ).order_by(Service.libelle)
                    services = session.exec(services_query).all()
                    
                    # Récupérer aussi les services rattachés aux directions du programme
                    if directions:
                        direction_ids = [d.id for d in directions if d.id is not None]
                        if direction_ids:
                            services_directions_query = select(Service).where(
                                and_(
                                    Service.direction_id.in_(direction_ids),
                                    Service.actif == True
                                )
                            ).order_by(Service.libelle)
                            services_via_directions = session.exec(services_directions_query).all()
                            # Ajouter les services qui ne sont pas déjà dans la liste
                            existing_service_ids = {s.id for s in services}
                            services.extend([s for s in services_via_directions if s.id not in existing_service_ids])
                    
                    # Récupérer aussi les services rattachés aux sous-directions du programme
                    if sous_directions:
                        sous_direction_ids = [sd.id for sd in sous_directions if sd.id is not None]
                        if sous_direction_ids:
                            services_sous_directions_query = select(Service).where(
                                and_(
                                    Service.sous_direction_id.in_(sous_direction_ids),
                                    Service.actif == True
                                )
                            ).order_by(Service.libelle)
                            services_via_sous_directions = session.exec(services_sous_directions_query).all()
                            # Ajouter les services qui ne sont pas déjà dans la liste
                            existing_service_ids = {s.id for s in services}
                            services.extend([s for s in services_via_sous_directions if s.id not in existing_service_ids])
                    
                    # Construire la liste formatée
                    for direction in directions:
                        if direction.libelle:
                            services_directions_list.append(f"la {direction.libelle}")
                    
                    for sous_direction in sous_directions:
                        if sous_direction.libelle:
                            services_directions_list.append(f"la {sous_direction.libelle}")
                    
                    for service in services:
                        if service.libelle:
                            # Déterminer l'article approprié (le/la) basé sur le libellé
                            libelle_lower = service.libelle.lower()
                            if libelle_lower.startswith(('direction', 'cellule')):
                                article = "la"
                            else:
                                article = "le"
                            services_directions_list.append(f"{article} {service.libelle}")
                    
                    logger.info(f"📊 {len(directions)} directions, {len(sous_directions)} sous-directions et {len(services)} services trouvés pour le programme {programme_obj.libelle}")
                
                # Charger nb_objectifs via ReportDataLoader.load_data_performance
                if programme_obj:
                    try:
                        logger.info("=" * 80)
                        logger.info("🎯 === DÉBUT CHARGEMENT nb_objectifs (ReportDataLoader) ===")
                        logger.info("=" * 80)
                        logger.info(f"🔍 Chargement des objectifs pour le programme: '{programme_obj.libelle}' (ID: {programme_obj.id})")
                        
                        from app.services.report_data_loader import ReportDataLoader
                        
                        performance_data = ReportDataLoader.load_data_performance(
                            session, 
                            annee, 
                            programme_id=programme_obj.id
                        )
                        objectifs_specifiques = performance_data.get("objectifs_specifiques", [])
                        nb_objectifs_count = len(objectifs_specifiques)
                        logger.info(f"📊 {nb_objectifs_count} objectifs spécifiques (OS) trouvés pour le programme")
                        
                        nb_objectifs = str(nb_objectifs_count) if nb_objectifs_count else ""
                        nb_objectifs = format_two_digits(nb_objectifs)
                        nb_objectifs_formatted = format_dynamic_value(nb_objectifs, "..............")
                        logger.info(f"🔄 nb_objectifs_formatted mis à jour: '{nb_objectifs_formatted}'")
                        logger.info("=" * 80)
                        logger.info(f"✅ === FIN CHARGEMENT nb_objectifs === (Résultat: {nb_objectifs})")
                        logger.info("=" * 80)
                    except Exception as e:
                        logger.error(f"❌ Erreur lors du chargement du nombre d'objectifs: {e}", exc_info=True)
                        if not nb_objectifs:
                            nb_objectifs = ""
                        else:
                            nb_objectifs = format_two_digits(nb_objectifs)
                        nb_objectifs_formatted = format_dynamic_value(nb_objectifs, "..............")
                        logger.info(f"🔄 nb_objectifs_formatted mis à jour après erreur: '{nb_objectifs_formatted}'")
                        logger.info("=" * 80)
                        logger.info(f"❌ === FIN CHARGEMENT nb_objectifs (ERREUR) === (Résultat: {nb_objectifs})")
                        logger.info("=" * 80)
                
                # Charger nb_actions via ReportDataLoader.load_data_sigobe
                if programme_obj and not nb_actions:
                    try:
                        logger.info("=" * 80)
                        logger.info("🎯 === DÉBUT CHARGEMENT nb_actions (ReportDataLoader) ===")
                        logger.info("=" * 80)
                        logger.info(f"🔍 Chargement des actions pour le programme: '{programme_obj.libelle}' (ID: {programme_obj.id})")
                        
                        from app.services.report_data_loader import ReportDataLoader
                        
                        sigobe_data = ReportDataLoader.load_data_sigobe(
                            session,
                            annee,
                            programme_nom=programme_obj.libelle or programme
                        )
                        executions = sigobe_data.get("executions", [])
                        
                        # Compter les actions distinctes
                        actions_set = set()
                        for exec in executions:
                            if exec.actions and str(exec.actions).strip():
                                actions_set.add(exec.actions.strip())
                        
                        nb_actions_count = len(actions_set)
                        logger.info(f"📊 {nb_actions_count} actions distinctes trouvées")
                        
                        if actions_set:
                            logger.info(f"🔍 DIAGNOSTIC: Liste des actions trouvées:")
                            for idx, action in enumerate(list(actions_set)[:10], 1):
                                logger.info(f"   {idx}. '{action}'")
                        
                        nb_actions = str(nb_actions_count) if nb_actions_count else ""
                        nb_actions = format_two_digits(nb_actions)
                        nb_actions_formatted = format_dynamic_value(nb_actions, "..............")
                        logger.info(f"🔄 nb_actions_formatted mis à jour: '{nb_actions_formatted}'")
                        logger.info("=" * 80)
                        logger.info(f"✅ === FIN CHARGEMENT nb_actions === (Résultat: {nb_actions})")
                        logger.info("=" * 80)
                    except Exception as e:
                        logger.error(f"❌ Erreur lors du chargement du nombre d'actions: {e}", exc_info=True)
                        if nb_actions:
                            nb_actions = format_two_digits(nb_actions)
                        nb_actions_formatted = format_dynamic_value(nb_actions, "..............")
                        logger.info("=" * 80)
                        logger.info(f"❌ === FIN CHARGEMENT nb_actions (ERREUR) === (Résultat: {nb_actions})")
                        logger.info("=" * 80)
                
                # Charger plan_strategique via ReportDataLoader.load_data_ministere
                if not plan_strategique:
                    try:
                        logger.info("🎯 Chargement du plan stratégique via ReportDataLoader...")
                        from app.services.report_data_loader import ReportDataLoader
                        
                        ministere_data = ReportDataLoader.load_data_ministere(session)
                        orientations = ministere_data.get("orientations", [])
                        if orientations:
                            plan_strategique = " ; ".join([o.libelle for o in orientations if o.libelle])
                            plan_strategique_formatted = format_dynamic_value(plan_strategique, "..............")
                            logger.info(f"🔄 plan_strategique_formatted mis à jour: '{plan_strategique_formatted[:50]}...'")
                            logger.info(f"📊 Plan stratégique récupéré: {len(orientations)} orientations")
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur lors du chargement du plan stratégique: {e}")
                        plan_strategique_formatted = format_dynamic_value(plan_strategique, "..............")
                
                # Charger budget_actuel, depenses_personnel, depenses_biens_services, investissements via ReportDataLoader.load_data_sigobe
                if programme_obj and (not budget_actuel or not depenses_personnel or not depenses_biens_services or not investissements):
                    try:
                        logger.info("=" * 80)
                        logger.info("🎯 === DÉBUT CHARGEMENT DÉPENSES ET BUDGET (ReportDataLoader) ===")
                        logger.info("=" * 80)
                        logger.info(f"🔍 Chargement des dépenses pour le programme: '{programme_obj.libelle}' (ID: {programme_obj.id})")
                        
                        from app.services.report_data_loader import ReportDataLoader
                        from decimal import Decimal
                        
                        # Charger les données SIGOBE
                        sigobe_data = ReportDataLoader.load_data_sigobe(
                            session,
                            annee,
                            programme_nom=programme_obj.libelle or programme
                        )
                        executions = sigobe_data.get("executions", [])
                        logger.info(f"📊 {len(executions)} exécutions SIGOBE trouvées pour le calcul des dépenses")
                        
                        # Fonction helper pour détecter le type de dépense
                        def is_personnel(type_depense: str | None) -> bool:
                            if not type_depense:
                                return False
                            type_dep_upper = type_depense.upper().strip()
                            return any(keyword in type_dep_upper for keyword in ["PERSONNEL", "P -", "P "]) or type_dep_upper == "P"
                        
                        def is_biens_services(type_depense: str | None) -> bool:
                            if not type_depense:
                                return False
                            type_dep_upper = type_depense.upper().strip()
                            return any(keyword in type_dep_upper for keyword in ["BIENS", "SERVICES", "BS -", "BS "]) or type_dep_upper == "BS"
                        
                        def is_investissement(type_depense: str | None) -> bool:
                            if not type_depense:
                                return False
                            type_dep_upper = type_depense.upper().strip()
                            return any(keyword in type_dep_upper for keyword in ["INVESTISSEMENT", "I -", "I "]) or type_dep_upper == "I"
                        
                        total_budget_actuel = Decimal(0)
                        total_personnel = Decimal(0)
                        total_biens_services = Decimal(0)
                        total_investissement = Decimal(0)
                        
                        for exec in executions:
                            budget_actuel_val = exec.budget_actuel or Decimal(0)
                            total_budget_actuel += budget_actuel_val
                            
                            # Catégoriser par type de dépense
                            if is_personnel(exec.type_depense):
                                total_personnel += budget_actuel_val
                            elif is_biens_services(exec.type_depense):
                                total_biens_services += budget_actuel_val
                            elif is_investissement(exec.type_depense):
                                total_investissement += budget_actuel_val
                        
                        logger.info(f"📊 Totaux calculés - Budget actuel: {total_budget_actuel}, Personnel: {total_personnel}, Biens/Services: {total_biens_services}, Investissements: {total_investissement}")
                        
                        # Formater les montants en FCFA avec séparateurs de milliers
                        def format_montant(montant: Decimal) -> str:
                            if montant == 0:
                                return ""
                            return f"{int(montant):,}".replace(",", " ")
                        
                        # Mettre à jour budget_actuel si non fourni
                        if not budget_actuel and total_budget_actuel > 0:
                            budget_actuel = format_montant(total_budget_actuel)
                            budget_actuel_formatted = format_dynamic_value(budget_actuel, "..............")
                            logger.info(f"🔄 budget_actuel_formatted mis à jour: '{budget_actuel_formatted}'")
                        
                        if not depenses_personnel and total_personnel > 0:
                            depenses_personnel = format_montant(total_personnel)
                            depenses_personnel_formatted = format_dynamic_value(depenses_personnel, "..............")
                            logger.info(f"🔄 depenses_personnel_formatted mis à jour: '{depenses_personnel_formatted}'")
                        if not depenses_biens_services and total_biens_services > 0:
                            depenses_biens_services = format_montant(total_biens_services)
                            depenses_biens_services_formatted = format_dynamic_value(depenses_biens_services, "..............")
                            logger.info(f"🔄 depenses_biens_services_formatted mis à jour: '{depenses_biens_services_formatted}'")
                        if not investissements and total_investissement > 0:
                            investissements = format_montant(total_investissement)
                            investissements_formatted = format_dynamic_value(investissements, "..............")
                            logger.info(f"🔄 investissements_formatted mis à jour: '{investissements_formatted}'")
                        
                        logger.info(f"📊 Dépenses récupérées - Budget actuel: {budget_actuel}, Personnel: {depenses_personnel}, Biens/Services: {depenses_biens_services}, Investissements: {investissements}")
                        logger.info("=" * 80)
                        logger.info(f"✅ === FIN CHARGEMENT DÉPENSES ET BUDGET ===")
                        logger.info("=" * 80)
                    except Exception as e:
                        logger.error(f"❌ Erreur lors du chargement des dépenses: {e}", exc_info=True)
                        budget_actuel_formatted = format_dynamic_value(budget_actuel, "..............")
                        depenses_personnel_formatted = format_dynamic_value(depenses_personnel, "..............")
                        depenses_biens_services_formatted = format_dynamic_value(depenses_biens_services, "..............")
                        investissements_formatted = format_dynamic_value(investissements, "..............")
                        logger.info("=" * 80)
                        logger.info(f"❌ === FIN CHARGEMENT DÉPENSES ET BUDGET (ERREUR) ===")
                        logger.info("=" * 80)
                
                if not programme_obj:
                    logger.warning(f"⚠️ Programme '{programme}' non trouvé dans la base de données")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la récupération des données: {e}", exc_info=True)
        
        # Formater la liste des services et directions
        services_directions_formatted = ""
        if services_directions_list:
            # Utiliser la liste récupérée depuis la base de données
            services_list = []
            for item in services_directions_list:
                services_list.append(f"• {format_dynamic_value(item, item)}")
            services_directions_formatted = "\n".join(services_list)
        elif services_directions and isinstance(services_directions, list) and len(services_directions) > 0:
            # Si une liste est fournie manuellement dans les données
            services_list = []
            for service in services_directions:
                if service and str(service).strip():
                    services_list.append(f"• {format_dynamic_value(service)}")
            services_directions_formatted = "\n".join(services_list)
        else:
            # Utiliser la liste par défaut avec formatage
            services_par_defaut = [
                "la Direction Générale du Portefeuille de l'Etat",
                "la Direction du Portefeuille des Secteurs Primaire et Secondaire",
                "la Direction du Portefeuille du Secteur Tertiaire",
                "la Direction de la Stratégie et de l'Expertise",
                "la Direction des Affaires Juridiques",
                "la Direction des Ressources Humaines et de la Communication",
                "le Service de Gestion des Projets, de la Transformation, du Suivi et Evaluation",
                "le Service des Moyens Généraux",
                "le Service Système d'Information",
                "la Cellule de Gestion et d'Attribution des Marchés"
            ]
            services_list = []
            for service in services_par_defaut:
                services_list.append(f"• {format_dynamic_value(service, service)}")
            services_directions_formatted = "\n".join(services_list)
        
        # Texte d'introduction (par défaut ou depuis les données)
        introduction_text = data.get("introduction_text", "")
        
        # Si pas de texte personnalisé, utiliser le texte par défaut avec valeurs formatées
        if not introduction_text:
            introduction_text = f"""Le programme « {programme_formatted} » est un programme opérationnel qui vise à {missions_formatted} et la mise en œuvre de son plan stratégique {plan_strategique_formatted}.

Conformément aux dispositions du décret {decret_complet_formatted} portant organisation du {ministere_formatted}, le programme « {programme_formatted} » est constitué du Cabinet de la Direction Générale du Portefeuille de l'Etat, des Directions et Services rattachés suivants :

{services_directions_formatted}

Le cadre de performance du programme est bâti autour de {nb_objectifs_formatted} objectifs spécifiques dont l'atteinte passera par la mise en œuvre de {nb_actions_formatted} actions.

Pour la mise en œuvre de ses missions, le programme « {programme_formatted} » bénéficie d'un budget actuel de {budget_actuel_formatted} FCFA dont {depenses_personnel_formatted} FCFA pour les dépenses de personnel, {depenses_biens_services_formatted} FCFA pour les dépenses de biens et services et {investissements_formatted} FCFA pour les investissements."""
        
        # Construire la story (comme dans le RAP)
        story = []
        
        # Ajouter le titre "INTRODUCTION"
        story.append(Paragraph("INTRODUCTION", title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Convertir le texte en Paragraphs (gérer les listes à puces et les paragraphes)
        # Le texte contient déjà des balises HTML pour les valeurs dynamiques en rouge
        # ReportLab Paragraph interprète le HTML, donc on ne doit pas échapper les balises
        paragraphs = introduction_text.split('\n\n')
        for para in paragraphs:
            if not para.strip():
                story.append(Spacer(1, 0.2 * cm))
                continue
            
            # Échapper uniquement le contenu texte (pas les balises HTML)
            # Utiliser une regex pour échapper uniquement le texte entre les balises
            import re
            
            # Séparer le texte en balises HTML et contenu texte
            # Fonction pour échapper le contenu texte uniquement
            def escape_text_content(text):
                """Échappe le contenu texte mais préserve les balises HTML"""
                # Remplacer temporairement les balises HTML
                tag_pattern = r'<[^>]+>'
                tags = []
                def replace_tag(match):
                    tags.append(match.group(0))
                    return f"__TAG_{len(tags)-1}__"
                
                text_with_tags_replaced = re.sub(tag_pattern, replace_tag, text)
                # Échapper le texte
                text_escaped = text_with_tags_replaced.replace("&", "&amp;")
                # Restaurer les balises
                for i, tag in enumerate(tags):
                    text_escaped = text_escaped.replace(f"__TAG_{i}__", tag)
                return text_escaped
            
            para_escaped = escape_text_content(para)
            
            # Convertir les listes à puces en HTML
            lines = para_escaped.split('\n')
            para_html = ""
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                if line_stripped.startswith('•'):
                    # Liste à puce
                    text = line_stripped[1:].strip()
                    para_html += f"&nbsp;&nbsp;&nbsp;&nbsp;• {text}<br/>"
                else:
                    para_html += f"{line_stripped} "
            
            if para_html:
                story.append(Paragraph(para_html, body_style))
                story.append(Spacer(1, 0.2 * cm))
        
        # Fonction pour dessiner le footer
        def draw_footer(page_num: int):
            """Dessine le footer pour chaque page"""
            RPROGLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_num,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin,
                total_pages=getattr(cls, '_total_pages', None)
            )
        
        # La page a déjà été créée dans generate_pdf avant l'appel
        # Rendre la story avec pagination automatique (comme dans le RAP)
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
        
        # Enregistrer la position de l'introduction
        RAPPageManager.register_page_position("rprog_introduction", start_page)
        
        return final_page
    
    @classmethod
    def draw_realisations_activites(
        cls,
        pdf: canvas.Canvas = None,
        width: float = None,
        height: float = None,
        start_page: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Génère la section "1.1. Les activités" avec le tableau de mise en œuvre des activités.
        
        Utilise SimpleDocTemplate pour gérer automatiquement le découpage du LongTable sur plusieurs pages.
        
        Args:
            pdf: Le canvas PDF (optionnel, pour compatibilité)
            width: Largeur de la page (optionnel, utilise A4 landscape par défaut)
            height: Hauteur de la page (optionnel, utilise A4 landscape par défaut)
            start_page: Numéro de page de début
        
        Returns:
            Tuple (BytesIO buffer, numéro de page final) - Le buffer contient le PDF généré
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import Paragraph, LongTable, TableStyle, Spacer, SimpleDocTemplate
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from textwrap import wrap
        from io import BytesIO
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPBaseGenerator, RAPPageManager
        from app.models.budget import SuiviActivite
        from sqlmodel import select, and_, or_
        
        # Utiliser A4 landscape par défaut si width/height non fournis
        if width is None or height is None:
            width, height = landscape(A4)
        
        # Marges
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        start_y = height - top_margin
        content_bottom = bottom_margin
        
        # Couleur de texte
        dark_text_color = RAPBaseGenerator.DARK_TEXT
        
        # Créer le buffer pour le PDF
        buffer = BytesIO()
        
        # Récupérer les données
        data = cls.data if hasattr(cls, 'data') and cls.data else {}
        session = cls._db_session if hasattr(cls, '_db_session') and cls._db_session else None
        
        if not session:
            logger.warning("⚠️ Pas de session DB disponible pour récupérer les activités")
            # Créer un PDF minimal avec SimpleDocTemplate
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=left_margin,
                rightMargin=right_margin,
                topMargin=top_margin,
                bottomMargin=bottom_margin,
            )
            
            story = []
            styles = getSampleStyleSheet()
            story.append(Paragraph("1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME", 
                                   ParagraphStyle('Title', parent=styles['Heading1'], 
                                                 fontName="Helvetica-Bold", fontSize=14)))
            story.append(Paragraph("1.1. Les activités", 
                                   ParagraphStyle('SubTitle', parent=styles['Heading2'], 
                                                 fontName="Helvetica-Bold", fontSize=12)))
            
            def on_first_page(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            def on_later_pages(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
            buffer.seek(0)
            
            from PyPDF2 import PdfReader
            reader = PdfReader(buffer)
            num_pages = len(reader.pages)
            RAPPageManager.register_page_position("rprog_realisations_activites", start_page)
            return buffer, start_page + num_pages
        
        # Récupérer les paramètres de filtrage
        programme = data.get("programme", "")
        annee = data.get("annee", 2024)
        periode = data.get("periode", "")
        
        # ============================================================
        # ÉTAPE 1: Récupérer les actions et activités via ReportDataLoader
        # ============================================================
        logger.info("=" * 80)
        logger.info("🔍 === DÉBUT CHARGEMENT ACTIONS/ACTIVITÉS (ReportDataLoader) ===")
        logger.info("=" * 80)
        
        # Charger les données SIGOBE via ReportDataLoader
        from app.services.report_data_loader import ReportDataLoader
        sigobe_data_result = ReportDataLoader.load_data_sigobe(
            session,
            annee,
            programme_nom=programme
        )
        sigobe_data_raw = sigobe_data_result.get("executions", [])
        
        # Filtrer par période si nécessaire (semestre)
        sigobe_data = []
        if periode and "SEMESTRE" in periode.upper():
            if "PREMIER" in periode.upper() or "1" in periode:
                sigobe_data = [e for e in sigobe_data_raw if e.trimestre in [1, 2]]
            elif "DEUXIEME" in periode.upper() or "2" in periode:
                sigobe_data = [e for e in sigobe_data_raw if e.trimestre in [3, 4]]
            else:
                sigobe_data = sigobe_data_raw
        else:
            sigobe_data = sigobe_data_raw
        
        logger.info(f"📊 {len(sigobe_data)} lignes SIGOBE trouvées après filtrage (programme: {programme}, année: {annee}, période: {periode})")
        
        # Construire la requête pour compatibilité avec le reste du code (mais utiliser les données déjà chargées)
        # Note: On garde la structure pour le traitement suivant, mais les données viennent de ReportDataLoader
        sigobe_query = None  # Plus besoin de requête, données déjà chargées
        
        # Filtrer pour avoir uniquement les lignes avec actions et activités non vides
        sigobe_data_filtered = [
            e for e in sigobe_data 
            if e.actions and str(e.actions).strip() 
            and e.activites and str(e.activites).strip()
        ]
        
        # Créer un dictionnaire pour grouper par action/activité (en gardant les IDs SIGOBE)
        sigobe_actions_activites = {}
        for sigobe_row in sigobe_data_filtered:
            action = (sigobe_row.actions or "").strip()
            activite = (sigobe_row.activites or "").strip()
            if action and activite:
                key = f"{action}|||{activite}"  # Séparateur unique pour éviter les collisions
                if key not in sigobe_actions_activites:
                    sigobe_actions_activites[key] = {
                        "action": action,
                        "activite": activite,
                        "sigobe_ids": []
                    }
                sigobe_actions_activites[key]["sigobe_ids"].append(sigobe_row.id)
        
        # Trier les clés pour avoir un ordre cohérent
        sigobe_actions_activites = dict(sorted(sigobe_actions_activites.items()))
        
        logger.info(f"📊 {len(sigobe_actions_activites)} combinaisons action/activité distinctes trouvées dans SIGOBE")
        if len(sigobe_actions_activites) == 0:
            logger.warning(f"⚠️ Aucune combinaison action/activité trouvée dans SIGOBE pour le programme '{programme}', année {annee}, période '{periode}'")
            logger.warning(f"⚠️ Données SIGOBE brutes chargées: {len(sigobe_data_raw)} lignes, après filtrage: {len(sigobe_data)} lignes, avec actions/activités: {len(sigobe_data_filtered)} lignes")
        logger.info("=" * 80)
        logger.info("✅ === FIN CHARGEMENT SIGOBE (ReportDataLoader) ===")
        logger.info("=" * 80)
        
        # ============================================================
        # ÉTAPE 2: Mapper vers SuiviActivite pour remplir les autres colonnes
        # ============================================================
        logger.info("=" * 80)
        logger.info("🔍 === DÉBUT MAPPING VERS SUIVI ACTIVITÉ ===")
        logger.info("=" * 80)
        
        # Créer une structure combinée pour le tableau
        activites_combinees = []
        
        # Si pas de données SIGOBE, créer un tableau vide avec message
        if len(sigobe_actions_activites) == 0:
            logger.warning(f"⚠️ Aucune donnée SIGOBE trouvée, le tableau sera créé avec un message d'absence de données")
        else:
            for key, sigobe_data in sigobe_actions_activites.items():
                action = sigobe_data["action"]
                activite = sigobe_data["activite"]
                sigobe_ids = sigobe_data["sigobe_ids"]
                
                # Chercher un SuiviActivite correspondant
                # Essayer d'abord par sigobe_execution_id
                suivi_activite = None
                for sigobe_id in sigobe_ids:
                    suivi_query = select(SuiviActivite).where(
                        and_(
                            SuiviActivite.sigobe_execution_id == sigobe_id,
                            SuiviActivite.annee == annee
                        )
                    )
                    suivi_activite = session.exec(suivi_query).first()
                    if suivi_activite:
                        break
                
                # Si pas trouvé par sigobe_execution_id, essayer par matching sur action/activité
                if not suivi_activite:
                    suivi_query = select(SuiviActivite).where(
                        and_(
                            or_(
                                SuiviActivite.action.ilike(f"%{action}%"),
                                SuiviActivite.libelle_activite.ilike(f"%{action}%")
                            ),
                            or_(
                                SuiviActivite.libelle_activite.ilike(f"%{activite}%"),
                                SuiviActivite.code_activite.ilike(f"%{activite}%")
                            ),
                            SuiviActivite.annee == annee
                        )
                    )
                    # Filtrer par période si fournie
                    if periode and "SEMESTRE" in periode.upper():
                        if "PREMIER" in periode.upper() or "1" in periode:
                            suivi_query = suivi_query.where(SuiviActivite.periode_type == "semestre")
                            suivi_query = suivi_query.where(SuiviActivite.periode_valeur == 1)
                        elif "DEUXIEME" in periode.upper() or "2" in periode:
                            suivi_query = suivi_query.where(SuiviActivite.periode_type == "semestre")
                            suivi_query = suivi_query.where(SuiviActivite.periode_valeur == 2)
                    
                    # Filtrer par programme si fourni
                    if programme:
                        suivi_query = suivi_query.where(SuiviActivite.programme.ilike(f"%{programme}%"))
                    
                    suivi_activite = session.exec(suivi_query).first()
                
                # Créer une entrée combinée
                # Gérer les valeurs None en les convertissant en chaînes vides
                def safe_get(attr, default=""):
                    """Récupère un attribut en gérant None"""
                    if not suivi_activite:
                        return default
                    value = getattr(suivi_activite, attr, None)
                    return str(value) if value is not None else default
                
                activite_combinee = {
                    "action": action,
                    "activite": activite,
                    "structures_responsables": safe_get("structures_responsables", ""),
                    "resultat_attendu": safe_get("resultat_attendu", ""),
                    "resultat_operationnel": safe_get("resultat_operationnel", ""),
                    "preuve_realisation": safe_get("preuve_filename", "") or safe_get("preuve_realisation", ""),
                    "observations": safe_get("observations", "RAS"),
                    "code_activite": safe_get("code_activite", "")
                }
                activites_combinees.append(activite_combinee)
        
        # Trier les activités combinées par action puis par activité (seulement si on a des données)
        if activites_combinees:
            activites_combinees.sort(key=lambda x: (x.get("action", ""), x.get("activite", "")))
        
        logger.info(f"📊 {len(activites_combinees)} activités combinées créées (SIGOBE + SuiviActivite)")
        if activites_combinees:
            logger.info(f"📋 Premières activités combinées:")
            for idx, act in enumerate(activites_combinees[:3], 1):
                logger.info(f"   {idx}. Action: '{act.get('action', 'N/A')}' | Activité: '{act.get('activite', 'N/A')}'")
                logger.info(f"      - Structures: '{act.get('structures_responsables', 'VIDE')[:50] if act.get('structures_responsables') else 'VIDE'}'")
                logger.info(f"      - Résultat attendu: '{act.get('resultat_attendu', 'VIDE')[:50] if act.get('resultat_attendu') else 'VIDE'}'")
                logger.info(f"      - Résultat opérationnel: '{act.get('resultat_operationnel', 'VIDE')[:50] if act.get('resultat_operationnel') else 'VIDE'}'")
                logger.info(f"      - Preuve: '{act.get('preuve_realisation', 'VIDE')[:50] if act.get('preuve_realisation') else 'VIDE'}'")
                logger.info(f"      - Observations: '{act.get('observations', 'VIDE')[:50] if act.get('observations') else 'VIDE'}'")
        logger.info("=" * 80)
        logger.info("✅ === FIN MAPPING SUIVI ACTIVITÉ ===")
        logger.info("=" * 80)
        
        # Calculer les largeurs des colonnes
        # Ajustement pour donner plus d'espace à "Preuve de réalisation" afin d'éviter la coupure de mots
        col_widths = [
            available_width * 0.21,  # Action/Activités (réduit de 0.22)
            available_width * 0.13,  # Structures responsables
            available_width * 0.17,  # Résultat attendu (réduit de 0.18)
            available_width * 0.17,  # Résultat opérationnel (réduit de 0.18)
            available_width * 0.18,  # Preuve de réalisation (augmenté de 0.15 à 0.18 pour éviter la coupure)
            available_width * 0.14,  # Observations
        ]
        
        # Grouper les activités combinées par action
        activites_par_action = {}
        for activite_combinee in activites_combinees:
            action_key = activite_combinee["action"] or "Sans action"
            if action_key not in activites_par_action:
                activites_par_action[action_key] = []
            activites_par_action[action_key].append(activite_combinee)
        
        logger.info(f"📊 {len(activites_par_action)} groupes d'actions créés")
        if activites_par_action:
            for action_key, activites in activites_par_action.items():
                logger.info(f"   - '{action_key}': {len(activites)} activité(s)")
        
        # Créer un style pour les paragraphes (pour le wrapping du texte)
        # Augmenter la taille de police pour tout le tableau
        styles = getSampleStyleSheet()
        para_style = ParagraphStyle(
            "ParaStyle",
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,  # Augmenté de 8 à 10
            leading=12,   # Augmenté proportionnellement (fontSize * 1.2)
            alignment=0,  # LEFT
            spaceBefore=1,
            spaceAfter=1,
        )
        
        # Créer un style pour les en-têtes (gras, centré)
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,  # Augmenté de 9 à 11 pour les en-têtes
            leading=13,   # Augmenté proportionnellement
            alignment=1,  # CENTER
            spaceBefore=2,
            spaceAfter=2,
        )
        
        # Style spécial pour les lignes d'action (en gras)
        action_header_style = ParagraphStyle(
            "ActionHeaderStyle",
            parent=styles['Normal'],
            fontName="Helvetica-Bold",  # En gras
            fontSize=10,  # Même taille que para_style mais en gras
            leading=12,
            alignment=0,  # LEFT
            spaceBefore=1,
            spaceAfter=1,
        )
        
        # Construire les données du tableau avec Table et TableStyle (comme dans le RAP)
        table_data = []
        
        # Fonction helper pour créer un Paragraph avec wrapping
        def create_para(text, max_width=None):
            """Crée un Paragraph avec wrapping automatique. Retourne TOUJOURS un Paragraph, même pour les cellules vides."""
            # TOUJOURS retourner un Paragraph, même pour les cellules vides
            # Cela assure la cohérence de type pour le LongTable
            if not text:
                return Paragraph("", para_style)
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return Paragraph("", para_style)
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Paragraph gère automatiquement le wrapping selon la largeur de la colonne
            # Pas besoin de tronquer, le wrapping se fera automatiquement
            return Paragraph(text, para_style)
        
        # Fonction helper pour créer un Paragraph d'en-tête avec wrapping
        def create_header_para(text, max_width=None):
            """Crée un Paragraph d'en-tête avec wrapping automatique. Retourne TOUJOURS un Paragraph, même pour les cellules vides."""
            # TOUJOURS retourner un Paragraph, même pour les cellules vides
            # Cela assure la cohérence de type pour le LongTable
            if not text:
                return Paragraph("", header_style)
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return Paragraph("", header_style)
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # ReportLab gère automatiquement le wrapping
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
        # TEST : Ne pas fusionner les lignes pour voir si cela permet au LongTable de démarrer
        # Les lignes fusionnées (SPAN) augmentent la hauteur minimale nécessaire car elles créent
        # des cellules plus larges qui peuvent nécessiter plusieurs lignes de texte
        for action_key, activites in activites_par_action.items():
            if len(activites) > 0:
                first_activite = activites[0]
                action_code = first_activite.get("code_activite", "") or ""
                action_libelle = first_activite.get("action", action_key) or action_key
                header_text = f"{action_code} {action_libelle}" if action_code else action_libelle
                
                # Mettre le texte d'action en gras - sera fusionné sur toutes les colonnes
                # Utiliser action_header_style pour le texte en gras
                action_text_para = Paragraph(header_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), action_header_style)
                # Mettre le texte dans la première colonne, les autres seront fusionnées via SPAN
                table_data.append([
                    action_text_para,  # Première colonne avec texte en gras
                    "",   # Colonne 2 (sera fusionnée)
                    "",   # Colonne 3 (sera fusionnée)
                    "",   # Colonne 4 (sera fusionnée)
                    "",   # Colonne 5 (sera fusionnée)
                    "",   # Colonne 6 (sera fusionnée)
                ])
                
                # Lignes d'activités
                for activite in activites:
                    # Formater les données depuis la structure combinée
                    # Remplacer les valeurs vides ou None par "..................." (seulement en mode brouillon)
                    mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
                    empty_placeholder = "" if mode == "final" else "..................."
                    
                    def get_value(key, default=""):
                        """Récupère une valeur et gère None/chaînes vides"""
                        value = activite.get(key, default)
                        if value is None:
                            return default
                        value_str = str(value).strip() if value else ""
                        return value_str if value_str else default
                    
                    libelle = get_value("activite", "")
                    structures = get_value("structures_responsables", empty_placeholder)
                    resultat_attendu = get_value("resultat_attendu", empty_placeholder)
                    resultat_operationnel = get_value("resultat_operationnel", empty_placeholder)
                    preuve = get_value("preuve_realisation", empty_placeholder)
                    observations = get_value("observations", "RAS")
                    # Pour les observations, si c'est vide ou "RAS", utiliser "RAS", sinon le placeholder si vraiment vide
                    if not observations or observations.strip() == "":
                        observations = "RAS"
                    elif observations.strip() == "RAS":
                        observations = "RAS"  # Garder "RAS"
                    
                    # Ligne d'activité avec Paragraph pour le wrapping
                    # Mettre en rouge tous les éléments dynamiques (y compris les placeholders) en mode brouillon seulement
                    def create_para_red(text, max_width=None):
                        """Crée un Paragraph avec texte en rouge (brouillon) ou noir (final) pour les éléments dynamiques"""
                        if not text:
                            return create_para("", max_width)
                        # Échapper les caractères spéciaux pour XML/HTML
                        text_escaped = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        # En mode final, texte en noir ; en mode brouillon, texte en rouge
                        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
                        if mode == "final":
                            return Paragraph(text_escaped, para_style)
                        else:
                            text_red = f'<font color="#FF0000">{text_escaped}</font>'
                            return Paragraph(text_red, para_style)
                    
                    table_data.append([
                        create_para_red(libelle, col_widths[0]) if libelle else create_para_red(empty_placeholder, col_widths[0]),
                        create_para_red(structures, col_widths[1]),
                        create_para_red(resultat_attendu, col_widths[2]),
                        create_para_red(resultat_operationnel, col_widths[3]),
                        create_para_red(preuve, col_widths[4]),  # Preuve de réalisation avec wrapping
                        create_para_red(observations, col_widths[5]),
                    ])
        
        # Si aucune activité trouvée
        if len(activites_combinees) == 0:
            # Calculer la largeur totale pour le message (fusionné sur toutes les colonnes)
            total_width = sum(col_widths)
            # Utiliser des Paragraph vides pour toutes les cellules vides
            empty_para = create_para("")
            table_data.append([
                create_para("Aucune activité enregistrée pour cette période.", total_width),
                empty_para, empty_para, empty_para, empty_para, empty_para,
            ])
        
        # Vérifier les dimensions avant création (comme dans le tableau 8)
        logger.info(f"📊 Tableau des activités: {len(table_data)} lignes")
        logger.info(f"📊 Largeur disponible: {available_width:.2f}")
        logger.info(f"📊 Largeurs colonnes: {[f'{w:.2f}' for w in col_widths]}")
        logger.info(f"📊 Somme largeurs colonnes: {sum(col_widths):.2f}")
        logger.info(f"📊 Différence: {(available_width - sum(col_widths)):.2f}")
        
        # S'assurer que la somme des largeurs ne dépasse pas la largeur disponible
        total_col_widths = sum(col_widths)
        if total_col_widths > available_width:
            logger.warning(f"⚠️ Les largeurs de colonnes ({total_col_widths:.2f}) dépassent la largeur disponible ({available_width:.2f})")
            # Ajuster proportionnellement
            scale_factor = available_width / total_col_widths
            col_widths = [w * scale_factor for w in col_widths]
            logger.info(f"📊 Largeurs ajustées: {[f'{w:.2f}' for w in col_widths]}, Somme: {sum(col_widths):.2f}")
        
        # Convertir toutes les chaînes vides et Paragraphs vides en Paragraphs avec "..................." pour LongTable
        # LongTable préfère que toutes les cellules soient des Flowables
        # Les cellules vides affichent "..................." pour indiquer l'absence de données
        # TEST : Plus de SPAN, donc toutes les cellules vides peuvent être converties normalement
        logger.info(f"🔄 Conversion des chaînes vides et Paragraphs vides en Paragraphs avec '...................' pour compatibilité LongTable")
        empty_cell_text = "..................."
        
        # Compter les cellules converties pour debugging
        converted_count = 0
        for row_idx, row in enumerate(table_data):
            for col_idx, cell in enumerate(row):
                # Pour toutes les cellules, convertir les chaînes vides en Paragraphs avec "..................."
                if isinstance(cell, str) and not cell:
                    table_data[row_idx][col_idx] = create_para(empty_cell_text)
                    converted_count += 1
                # Convertir aussi les Paragraphs vides (ceux avec texte vide) en Paragraphs avec "..................."
                elif isinstance(cell, Paragraph):
                    try:
                        # Extraire le texte brut du Paragraph pour vérifier s'il est vide
                        text_content = cell.getPlainText() if hasattr(cell, 'getPlainText') else str(cell)
                        if not text_content or text_content.strip() == "":
                            table_data[row_idx][col_idx] = create_para(empty_cell_text)
                            converted_count += 1
                    except:
                        # En cas d'erreur, remplacer par un Paragraph avec "..................." pour sécurité
                        table_data[row_idx][col_idx] = create_para(empty_cell_text)
                        converted_count += 1
        
        logger.info(f"✅ Conversion terminée - {converted_count} cellules converties")
        
        # Vérifier que toutes les cellules sont bien des Paragraphs (sauf None)
        para_count = 0
        str_count = 0
        none_count = 0
        for row in table_data[:3]:  # Vérifier seulement les 3 premières lignes pour les logs
            for cell in row:
                if isinstance(cell, Paragraph):
                    para_count += 1
                elif isinstance(cell, str):
                    str_count += 1
                elif cell is None:
                    none_count += 1
        logger.info(f"📊 Vérification des types de cellules (3 premières lignes): {para_count} Paragraphs, {str_count} strings, {none_count} None")
        
        # Créer le tableau avec LongTable pour permettre la division automatique sur plusieurs pages
        # LongTable est spécialement conçu pour les tableaux qui peuvent déborder sur plusieurs pages
        # IMPORTANT: splitByRow=1 permet le découpage par ligne, ce qui force le multi-pages
        logger.info(f"🔨 Création du LongTable avec {len(table_data)} lignes et {len(col_widths)} colonnes")
        logger.info(f"   - Paramètres: repeatRows=1 (répéter l'en-tête), splitByRow=1 (découpage par ligne)")
        try:
            # splitByRow=1 force le découpage ligne par ligne, permettant le multi-pages
            # repeatRows=1 répète la ligne d'en-tête sur chaque nouvelle page
            # Le LongTable se divisera automatiquement sur plusieurs pages si nécessaire
            table = LongTable(
                table_data, 
                colWidths=col_widths, 
                repeatRows=1,      # Répéter la ligne d'en-tête sur chaque page
                splitByRow=1       # Permettre le découpage ligne par ligne (FORCE le multi-pages)
            )
            logger.info(f"✅ LongTable créé avec succès (type: {type(table).__name__})")
            logger.info(f"   - Nombre de lignes dans le tableau: {len(table._cellvalues) if hasattr(table, '_cellvalues') else 'N/A'}")
            logger.info(f"   - Nombre de colonnes: {len(table._colWidths) if hasattr(table, '_colWidths') else 'N/A'}")
            logger.info(f"   - repeatRows: {table._repeatRows if hasattr(table, '_repeatRows') else 'N/A'}")
            logger.info(f"   - splitByRow: {table._splitByRow if hasattr(table, '_splitByRow') else 'N/A'}")
        except Exception as e:
            logger.error(f"❌ ERREUR lors de la création du LongTable: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        # Créer le style du tableau avec TableStyle (comme dans le RAP)
        table_style = [
            # Bordures
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            
            # En-tête - utiliser la même couleur que le RAP (#bdd6ee)
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),  # Augmenté de 9 à 11
            
            # Alignement des données
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            
            # Fonts pour les données
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),  # Augmenté de 8 à 10
            
            # Padding ajusté selon test_longtable.py qui fonctionne bien
            # Le test_longtable.py utilise (4, 4, 3, 3) mais nous réduisons légèrement
            # pour permettre au tableau de commencer juste après les titres
            ("LEFTPADDING", (0, 0), (-1, -1), 3),  # Augmenté de 2 à 3 (test utilise 4)
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),  # Augmenté de 2 à 3 (test utilise 4)
            ("TOPPADDING", (0, 0), (-1, -1), 2),    # Augmenté de 1 à 2 (test utilise 3)
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2), # Augmenté de 1 à 2 (test utilise 3)
        ]
        
        # Ajouter les styles pour les lignes d'en-tête de groupe (actions)
        # Fusionner toutes les colonnes pour chaque ligne d'action
        current_row = 1  # Commence après la ligne d'en-tête
        for action_key, activites in activites_par_action.items():
            if len(activites) > 0:
                # Fusionner toutes les colonnes de la ligne d'action
                table_style.append(("SPAN", (0, current_row), (-1, current_row)))  # Fusionner toutes les colonnes
                # Style pour les lignes d'action : fond gris et texte en gras
                table_style.append(("BACKGROUND", (0, current_row), (-1, current_row), colors.HexColor("#D3D3D3")))  # Toute la ligne en gris foncé
                table_style.append(("FONTNAME", (0, current_row), (-1, current_row), "Helvetica-Bold"))  # Toute la ligne en gras
                table_style.append(("FONTSIZE", (0, current_row), (-1, current_row), 10))  # Taille augmentée à 10
                table_style.append(("ALIGN", (0, current_row), (-1, current_row), "LEFT"))  # Alignement à gauche
                current_row += 1
                
                # Lignes d'activités
                current_row += len(activites)
        
        # Si aucune activité trouvée, fusionner toutes les colonnes du message
        if len(activites_combinees) == 0:
            # La ligne du message est à l'index 1 (après l'en-tête)
            table_style.append(("SPAN", (0, 1), (-1, 1)))  # Fusionner toutes les colonnes
            table_style.append(("ALIGN", (0, 1), (-1, 1), "CENTER"))  # Centrer le message
        
        # Appliquer le style au tableau
        logger.info(f"🎨 Application du style au tableau ({len(table_style)} règles)")
        try:
            table.setStyle(TableStyle(table_style))
            logger.info(f"✅ Style appliqué avec succès")
        except Exception as e:
            logger.error(f"❌ ERREUR lors de l'application du style: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        # Construire la story avec les titres et le tableau (comme dans le RAP)
        # ParagraphStyle est déjà importé en haut du fichier
        
        story_styles = getSampleStyleSheet()
        
        # Styles pour les titres
        # Réduire drastiquement les spaceAfter pour permettre au tableau de commencer juste après les titres
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=story_styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,  # LEFT
            spaceAfter=3,  # Réduit drastiquement pour permettre au tableau de commencer plus tôt
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=story_styles['Heading2'],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=0,  # LEFT
            spaceAfter=2,  # Réduit drastiquement
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        tableau_title_style = ParagraphStyle(
            "TableauTitle",
            parent=story_styles['Heading3'],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=0,  # LEFT
            spaceAfter=2,  # Réduit drastiquement - juste assez pour séparer le titre du tableau
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        source_style = ParagraphStyle(
            "SourceStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=11,
            alignment=0,  # LEFT
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Style pour le corps de texte
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica",
            fontSize=12,
            leading=15,
            alignment=4,  # JUSTIFY
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        story = []
        
        # Ajouter les titres de section
        story.append(Paragraph("1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME", section_title_style))
        story.append(Paragraph("1.1. Les activités", subsection_title_style))
        
        # Obtenir le numéro de tableau automatiquement
        tableau_num = cls.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_num}: Mise en œuvre des activités", tableau_title_style))
        # Pas de Spacer - le spaceAfter du tableau_title_style (2 points) suffit
        
        # Ajouter le tableau à la story
        logger.info(f"📋 Ajout du tableau à la story")
        logger.info(f"   - Type du tableau: {type(table).__name__}")
        logger.info(f"   - Story contient actuellement {len(story)} éléments")
        story.append(table)
        story.append(Spacer(1, 0.2 * cm))
        logger.info(f"✅ Tableau ajouté à la story. Story contient maintenant {len(story)} éléments")
        logger.info(f"   - Types des éléments dans story: {[type(elem).__name__ for elem in story]}")
        
        # Ajouter la source
        story.append(Paragraph("Source: SIGOBE (actions et activités) - Suivi des activités (autres colonnes)", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Ajouter les commentaires personnalisés si disponibles (ou des points si vide)
        activites_commentaires = data.get("activites_commentaires")
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        if activites_commentaires and activites_commentaires.strip():
            # Échapper les caractères spéciaux HTML
            commentaires_escaped = activites_commentaires.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convertir les retours à la ligne en <br/>
            commentaires_html = commentaires_escaped.replace("\n", "<br/>")
            # En mode final, texte en noir ; en mode brouillon, texte en rouge
            if mode == "final":
                story.append(Paragraph(commentaires_html, body_style))
            else:
                commentaires_html_red = f"<font color=\"#FF0000\">{commentaires_html}</font>"
                story.append(Paragraph(commentaires_html_red, body_style))
        else:
            # En mode final, ne pas afficher le placeholder
            if mode != "final":
                story.append(Paragraph("<font color=\"#FF0000\">Commentaire :..........................</font>", body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Créer le SimpleDocTemplate (comme dans test_longtable.py)
        logger.info(f"🔢 NUMÉROTATION - AVANT SimpleDocTemplate pour activités: start_page={start_page}")
        logger.info(f"📐 Dimensions: width={width:.2f}, height={height:.2f}, margins: L={left_margin:.2f}, R={right_margin:.2f}, T={top_margin:.2f}, B={bottom_margin:.2f}")
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        # Construire le PDF avec SimpleDocTemplate (comme dans test_longtable.py)
        logger.info(f"📋 Génération du PDF avec SimpleDocTemplate - {len(story)} éléments dans la story")
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        from PyPDF2 import PdfReader
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        
        logger.info(f"🔢 NUMÉROTATION - APRÈS SimpleDocTemplate pour activités: {num_pages} pages générées, final_page={final_page}")
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("rprog_realisations_activites", start_page)
        RAPPageManager.register_page_position("rprog_realisations", start_page)
        RAPPageManager.register_page_position("rprog_tableau_1", start_page)
        
        buffer.seek(0)
        return buffer, final_page
    
    @classmethod
    def draw_realisations_credits(
        cls,
        pdf: canvas.Canvas = None,
        width: float = None,
        height: float = None,
        start_page: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Génère la section "1.2. Les crédits budgétaires" avec le tableau d'exécution financière.
        
        Utilise SimpleDocTemplate pour gérer automatiquement le découpage du LongTable sur plusieurs pages.
        
        Args:
            pdf: Le canvas PDF (optionnel, pour compatibilité)
            width: Largeur de la page (optionnel, utilise A4 landscape par défaut)
            height: Hauteur de la page (optionnel, utilise A4 landscape par défaut)
            start_page: Numéro de page de début
        
        Returns:
            Tuple (BytesIO buffer, numéro de page final) - Le buffer contient le PDF généré
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import Paragraph, LongTable, TableStyle, Spacer, SimpleDocTemplate
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from decimal import Decimal
        from io import BytesIO
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator, RAPPageManager
        from app.models.budget import SigobeExecution
        from sqlmodel import select
        
        # Utiliser A4 landscape par défaut si width/height non fournis
        if width is None or height is None:
            width, height = landscape(A4)
        
        # Créer le buffer pour le PDF
        buffer = BytesIO()
        
        # Marges
        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
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
            # Créer un PDF minimal avec SimpleDocTemplate
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=left_margin,
                rightMargin=right_margin,
                topMargin=top_margin,
                bottomMargin=bottom_margin,
            )
            
            story = []
            styles = getSampleStyleSheet()
            story.append(Paragraph("1.2. Les crédits budgétaires", 
                                   ParagraphStyle('SubTitle', parent=styles['Heading2'], 
                                                 fontName="Helvetica-Bold", fontSize=12)))
            
            def on_first_page(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            def on_later_pages(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
            buffer.seek(0)
            
            from PyPDF2 import PdfReader
            reader = PdfReader(buffer)
            num_pages = len(reader.pages)
            RAPPageManager.register_page_position("rprog_realisations_credits", start_page)
            return buffer, start_page + num_pages
        
        # Récupérer les paramètres de filtrage
        programme = data.get("programme", "")
        annee = data.get("annee", 2024)
        periode = data.get("periode", "")
        
        # Charger les données SIGOBE via ReportDataLoader
        from app.services.report_data_loader import ReportDataLoader
        sigobe_data_result = ReportDataLoader.load_data_sigobe(
            session,
            annee,
            programme_nom=programme
        )
        sigobe_data_raw = sigobe_data_result.get("executions", [])
        
        # Filtrer par période si nécessaire (semestre)
        if periode and "SEMESTRE" in periode.upper():
            if "PREMIER" in periode.upper() or "1" in periode:
                sigobe_data = [e for e in sigobe_data_raw if e.trimestre in [1, 2]]
            elif "DEUXIEME" in periode.upper() or "2" in periode:
                sigobe_data = [e for e in sigobe_data_raw if e.trimestre in [3, 4]]
            else:
                sigobe_data = sigobe_data_raw
        else:
            sigobe_data = sigobe_data_raw
        
        # Trier les données
        sigobe_data.sort(key=lambda x: (
            x.actions or "",
            x.activites or "",
            x.type_depense or ""
        ))
        
        logger.info(f"📊 {len(sigobe_data)} lignes SIGOBE trouvées pour le programme {programme}, année {annee}, période {periode}")
        
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
            available_width * 0.23,  # Action/Activités (réduit de 0.25 à 0.24)
            available_width * 0.11,  # Personnel Programmé
            available_width * 0.11,  # Personnel Réalisé
            available_width * 0.11,  # Biens et services Programmé
            available_width * 0.11,  # Biens et services Réalisé
            available_width * 0.11,  # Investissements Programmé
            available_width * 0.11,  # Investissements Réalisé
            available_width * 0.11,  # Observations (augmenté de 0.09 à 0.10)
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
        para_style_table2.fontSize = 10  # Uniformisé avec le tableau des activités
        para_style_table2.leading = 12   # Augmenté proportionnellement
        para_style_table2.alignment = 0  # LEFT
        
        # Style pour les colonnes numériques (centré)
        para_style_table2_center = ParagraphStyle(
            "ParaTable2Center",
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            alignment=1,  # CENTER
        )
        
        # Style pour les en-têtes (centré, gras, avec wrapping)
        header_style_table2 = ParagraphStyle(
            "HeaderTable2",
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,  # Uniformisé avec le tableau des activités
            leading=13,   # Augmenté proportionnellement
            alignment=1,  # CENTER
            spaceBefore=2,
            spaceAfter=2,
        )
        
        # Fonction helper pour vérifier le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        
        # Fonction helper pour créer un Paragraph avec wrapping
        def create_para_table2(text, max_width=None, is_red=False, is_center=False):
            """Crée un Paragraph avec wrapping automatique pour le Tableau 2
            Si is_red=True, met le texte en rouge (brouillon) ou noir (final) pour indiquer qu'il est dynamique
            Si is_center=True, centre le texte (pour les colonnes numériques)"""
            if not text:
                return ""
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return ""
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Mettre en rouge si demandé (seulement en mode brouillon)
            if is_red and not is_final:
                text = f'<font color="#FF0000">{text}</font>'
            # Choisir le style selon l'alignement
            style = para_style_table2_center if is_center else para_style_table2
            # Paragraph gère automatiquement le wrapping selon la largeur de la colonne
            return Paragraph(text, style)
        
        # Fonction helper pour créer un Paragraph d'en-tête avec wrapping
        def create_header_para_table2(text, max_width=None):
            """Crée un Paragraph d'en-tête avec wrapping automatique pour le Tableau 2"""
            if not text:
                return ""
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return ""
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # ReportLab gère automatiquement le wrapping
            return Paragraph(text, header_style_table2)
        
        # Construire les données du tableau avec Table et TableStyle (comme dans le RAP)
        table_data = []
        
        # Fonction helper pour créer un Paragraph vide (pour les cellules vides des en-têtes)
        def create_empty_para():
            return Paragraph("", para_style_table2)
        
        # Ligne 0 : Première ligne d'en-tête (utiliser Paragraphs pour le wrapping correct)
        table_data.append([
            create_header_para_table2("Actions/Activités", col_widths[0]),
            create_header_para_table2("Personnel", col_widths[1]),
            create_empty_para(),
            create_header_para_table2("Biens et services", col_widths[3]),
            create_empty_para(),
            create_header_para_table2("Investissements", col_widths[5]),
            create_empty_para(),
            create_header_para_table2("Observations", col_widths[7]),
        ])
        
        # Ligne 1 : Deuxième ligne d'en-tête (Programmé/Réalisé) - utiliser Paragraphs
        table_data.append([
            create_empty_para(),
            create_header_para_table2("Programmé", col_widths[1]),
            create_header_para_table2("Réalisé", col_widths[2]),
            create_header_para_table2("Programmé", col_widths[3]),
            create_header_para_table2("Réalisé", col_widths[4]),
            create_header_para_table2("Programmé", col_widths[5]),
            create_header_para_table2("Réalisé", col_widths[6]),
            create_empty_para(),
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
            
            # Ligne d'en-tête de groupe (action) - en rouge car dynamique
            table_data.append([
                create_para_table2(action_libelle, is_red=True),
                create_empty_para(), create_empty_para(), create_empty_para(), 
                create_empty_para(), create_empty_para(), create_empty_para(),
                create_empty_para(),
            ])
            
            # Fonction helper pour formater les valeurs du tableau (définie une fois par action)
            def format_table_value(value):
                """Retourne la valeur formatée ou '............' si 0 ou None"""
                if value is None or (isinstance(value, Decimal) and value == 0):
                    return "............"
                return format_montant(value)
            
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
                
                # Ligne d'activité - tous les éléments en rouge car dynamiques
                # Les colonnes numériques (1-6) sont centrées
                table_data.append([
                    create_para_table2(activite_libelle, is_red=True),  # Activité avec wrapping et en rouge (gauche)
                    create_para_table2(format_table_value(personnel_prog), is_red=True, is_center=True),  # Centré
                    create_para_table2(format_table_value(personnel_real), is_red=True, is_center=True),  # Centré
                    create_para_table2(format_table_value(biens_prog), is_red=True, is_center=True),  # Centré
                    create_para_table2(format_table_value(biens_real), is_red=True, is_center=True),  # Centré
                    create_para_table2(format_table_value(inv_prog), is_red=True, is_center=True),  # Centré
                    create_para_table2(format_table_value(inv_real), is_red=True, is_center=True),  # Centré
                    create_para_table2("", is_red=False),  # Observations vide (gauche)
                ])
            
            # Ligne de total pour cette action - tous les éléments en rouge car dynamiques
            # Les colonnes numériques (1-6) sont centrées
            table_data.append([
                create_para_table2(f"Total {action_libelle}", is_red=True),  # Gauche
                create_para_table2(format_table_value(total_personnel_prog), is_red=True, is_center=True),  # Centré
                create_para_table2(format_table_value(total_personnel_real), is_red=True, is_center=True),  # Centré
                create_para_table2(format_table_value(total_biens_prog), is_red=True, is_center=True),  # Centré
                create_para_table2(format_table_value(total_biens_real), is_red=True, is_center=True),  # Centré
                create_para_table2(format_table_value(total_inv_prog), is_red=True, is_center=True),  # Centré
                create_para_table2(format_table_value(total_inv_real), is_red=True, is_center=True),  # Centré
                create_para_table2("", is_red=False),  # Observations vide (gauche)
            ])
        
        # Si aucune donnée trouvée
        if len(actions_data) == 0:
            # Calculer la largeur totale pour le message (fusionné sur toutes les colonnes)
            total_width = sum(col_widths)
            table_data.append([
                create_para_table2("Aucune donnée d'exécution financière trouvée pour cette période.", total_width),
                create_empty_para(), create_empty_para(), create_empty_para(), 
                create_empty_para(), create_empty_para(), create_empty_para(), create_empty_para(),
            ])
        
        # Créer le tableau avec LongTable pour permettre la division automatique sur plusieurs pages
        table = LongTable(table_data, colWidths=col_widths, repeatRows=2, splitByRow=1)
        
        # Créer le style du tableau avec TableStyle (comme dans le RAP)
        table_style = [
            # Bordures
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            
            # En-têtes - utiliser la même couleur que le RAP (#bdd6ee)
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#bdd6ee")),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),  # Uniformisé avec le tableau des activités
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, 1), 10),  # Uniformisé avec le tableau des activités
            
            # Fusionner les cellules de l'en-tête (comme dans le RAP)
            ("SPAN", (1, 0), (2, 0)),  # Personnel
            ("SPAN", (3, 0), (4, 0)),  # Biens et services
            ("SPAN", (5, 0), (6, 0)),  # Investissements
            ("SPAN", (0, 0), (0, 1)),  # Actions/Activités
            ("SPAN", (7, 0), (7, 1)),  # Observations
            
            # Alignement des données
            ("ALIGN", (0, 2), (0, -1), "LEFT"),  # Actions/Activités à gauche
            ("ALIGN", (1, 2), (6, -1), "CENTER"),  # Chiffres centrés
            ("ALIGN", (7, 2), (7, -1), "LEFT"),  # Observations à gauche
            ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
            
            # Fonts pour les données
            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 2), (-1, -1), 10),  # Uniformisé avec le tableau des activités
            
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
            
            # Ligne d'en-tête de groupe (action) - fusionner toutes les colonnes (0 à 7, y compris Observations)
            table_style.append(("SPAN", (0, current_row), (-1, current_row)))  # Fusionner toutes les colonnes
            table_style.append(("BACKGROUND", (0, current_row), (-1, current_row), colors.HexColor("#D3D3D3")))  # Gris plus foncé
            table_style.append(("FONTNAME", (0, current_row), (-1, current_row), "Helvetica-Bold"))
            table_style.append(("FONTSIZE", (0, current_row), (-1, current_row), 11))  # Uniformisé avec le tableau des activités
            table_style.append(("ALIGN", (0, current_row), (-1, current_row), "LEFT"))
            current_row += 1
            
            # Lignes d'activités (styling déjà appliqué globalement)
            current_row += num_activites
            
            # Ligne de total - ne pas fusionner, elle a des valeurs dans toutes les colonnes
            # Mais appliquer le style en gras pour toutes les colonnes
            table_style.append(("FONTNAME", (0, current_row), (-1, current_row), "Helvetica-Bold"))
            table_style.append(("FONTSIZE", (0, current_row), (-1, current_row), 10))  # Uniformisé avec le tableau des activités
            table_style.append(("ALIGN", (0, current_row), (0, current_row), "LEFT"))  # Première colonne à gauche
            table_style.append(("ALIGN", (1, current_row), (6, current_row), "CENTER"))  # Chiffres centrés
            current_row += 1
        
        # Si aucune donnée trouvée, fusionner toutes les colonnes du message
        if len(actions_data) == 0:
            # La ligne du message est à l'index 2 (après les 2 lignes d'en-tête)
            table_style.append(("SPAN", (0, 2), (-1, 2)))  # Fusionner toutes les colonnes
            table_style.append(("ALIGN", (0, 2), (-1, 2), "CENTER"))  # Centrer le message
        
        # Appliquer le style au tableau
        table.setStyle(TableStyle(table_style))
        
        # Calculer les totaux globaux pour l'analyse
        total_personnel_programme = Decimal(0)
        total_personnel_realise = Decimal(0)
        total_biens_programme = Decimal(0)
        total_biens_realise = Decimal(0)
        total_inv_programme = Decimal(0)
        total_inv_realise = Decimal(0)
        
        for action_data in actions_data.values():
            for activite_data in action_data["activites"].values():
                types_depense = activite_data["types_depense"]
                total_personnel_programme += types_depense["PERSONNEL"]["programme"]
                total_personnel_realise += types_depense["PERSONNEL"]["realise"]
                total_biens_programme += types_depense["BIENS_ET_SERVICES"]["programme"]
                total_biens_realise += types_depense["BIENS_ET_SERVICES"]["realise"]
                total_inv_programme += types_depense["INVESTISSEMENTS"]["programme"]
                total_inv_realise += types_depense["INVESTISSEMENTS"]["realise"]
        
        total_budget = total_personnel_programme + total_biens_programme + total_inv_programme
        total_realise = total_personnel_realise + total_biens_realise + total_inv_realise
        
        # Calculer les pourcentages
        taux_execution_global = (total_realise / total_budget * 100) if total_budget > 0 else Decimal(0)
        
        pct_personnel_programme = (total_personnel_programme / total_budget * 100) if total_budget > 0 else Decimal(0)
        pct_biens_programme = (total_biens_programme / total_budget * 100) if total_budget > 0 else Decimal(0)
        pct_inv_programme = (total_inv_programme / total_budget * 100) if total_budget > 0 else Decimal(0)
        
        pct_personnel_realise = (total_personnel_realise / total_personnel_programme * 100) if total_personnel_programme > 0 else Decimal(0)
        pct_biens_realise = (total_biens_realise / total_biens_programme * 100) if total_biens_programme > 0 else Decimal(0)
        pct_inv_realise = (total_inv_realise / total_inv_programme * 100) if total_inv_programme > 0 else Decimal(0)
        
        # Fonction pour formater un pourcentage
        def format_pourcentage(pct: Decimal) -> str:
            return f"{float(pct):.1f}".replace(".", ",")
        
        # Construire le texte d'analyse
        programme_nom = programme or "Le programme Portefeuille de l'Etat"
        
        # Déterminer la date de période selon la période spécifiée
        if periode:
            periode_upper = periode.upper()
            if "PREMIER" in periode_upper or "1" in periode:
                date_periode = f"30 juin {annee}"
            elif "DEUXIEME" in periode_upper or "2" in periode:
                date_periode = f"31 décembre {annee}"
            else:
                date_periode = periode
        else:
            date_periode = f"30 juin {annee}"
        
        # Fonction pour formater une valeur ou afficher "............"
        def format_value_or_placeholder(value, formatter_func):
            """Retourne la valeur formatée ou "............" si la valeur est absente/nulle"""
            if value is None or (isinstance(value, Decimal) and value == 0):
                return "............"
            return formatter_func(value)
        
        # Générer le texte d'analyse (toujours affiché, avec "..........." pour les valeurs absentes)
        budget_total_text = format_value_or_placeholder(total_budget if total_budget > 0 else None, format_montant)
        personnel_prog_text = format_value_or_placeholder(total_personnel_programme if total_personnel_programme > 0 else None, format_montant)
        personnel_prog_pct_text = format_value_or_placeholder(pct_personnel_programme if total_personnel_programme > 0 and total_budget > 0 else None, format_pourcentage)
        biens_prog_text = format_value_or_placeholder(total_biens_programme if total_biens_programme > 0 else None, format_montant)
        biens_prog_pct_text = format_value_or_placeholder(pct_biens_programme if total_biens_programme > 0 and total_budget > 0 else None, format_pourcentage)
        inv_prog_text = format_value_or_placeholder(total_inv_programme if total_inv_programme > 0 else None, format_montant)
        inv_prog_pct_text = format_value_or_placeholder(pct_inv_programme if total_inv_programme > 0 and total_budget > 0 else None, format_pourcentage)
        total_realise_text = format_value_or_placeholder(total_realise if total_realise > 0 else None, format_montant)
        taux_exec_text = format_value_or_placeholder(taux_execution_global if total_budget > 0 and total_realise > 0 else None, format_pourcentage)
        personnel_real_text = format_value_or_placeholder(total_personnel_realise if total_personnel_realise > 0 else None, format_montant)
        personnel_real_pct_text = format_value_or_placeholder(pct_personnel_realise if total_personnel_programme > 0 and total_personnel_realise > 0 else None, format_pourcentage)
        biens_real_text = format_value_or_placeholder(total_biens_realise if total_biens_realise > 0 else None, format_montant)
        biens_real_pct_text = format_value_or_placeholder(pct_biens_realise if total_biens_programme > 0 and total_biens_realise > 0 else None, format_pourcentage)
        inv_real_text = format_value_or_placeholder(total_inv_realise if total_inv_realise > 0 else None, format_montant)
        inv_real_pct_text = format_value_or_placeholder(pct_inv_realise if total_inv_programme > 0 and total_inv_realise > 0 else None, format_pourcentage)
        
        # Fonction helper pour formater le texte selon le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        def format_text_for_mode(text):
            """Formate le texte en rouge (brouillon) ou noir (final)"""
            if mode == "final":
                return str(text)
            else:
                return f'<font color="#FF0000">{text}</font>'
        
        # Mettre tous les éléments dynamiques en rouge (ou noir en mode final)
        programme_nom_red = format_text_for_mode(programme_nom)
        budget_total_text_red = format_text_for_mode(budget_total_text)
        annee_red = format_text_for_mode(annee)
        date_periode_red = format_text_for_mode(date_periode)
        personnel_prog_text_red = format_text_for_mode(personnel_prog_text)
        personnel_prog_pct_text_red = format_text_for_mode(personnel_prog_pct_text)
        biens_prog_text_red = format_text_for_mode(biens_prog_text)
        biens_prog_pct_text_red = format_text_for_mode(biens_prog_pct_text)
        inv_prog_text_red = format_text_for_mode(inv_prog_text)
        inv_prog_pct_text_red = format_text_for_mode(inv_prog_pct_text)
        total_realise_text_red = format_text_for_mode(total_realise_text)
        taux_exec_text_red = format_text_for_mode(taux_exec_text)
        personnel_real_text_red = format_text_for_mode(personnel_real_text)
        personnel_real_pct_text_red = format_text_for_mode(personnel_real_pct_text)
        biens_real_text_red = format_text_for_mode(biens_real_text)
        biens_real_pct_text_red = format_text_for_mode(biens_real_pct_text)
        inv_real_text_red = format_text_for_mode(inv_real_text)
        inv_real_pct_text_red = format_text_for_mode(inv_real_pct_text)
        
        # Convertir le texte d'analyse en HTML pour les Paragraphs
        analyse_html = f"""Le programme « {programme_nom_red} » dispose d'un budget total de <b>{budget_total_text_red}</b> FCFA pour l'année {annee_red}. Ce budget est exclusivement financé par des ressources intérieures.<br/><br/>

Répartition du budget initial par nature de dépenses :<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• Personnel : <b>{personnel_prog_text_red}</b> FCFA (<b>{personnel_prog_pct_text_red}%</b>)<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• Biens et services : <b>{biens_prog_text_red}</b> FCFA (<b>{biens_prog_pct_text_red}%</b>)<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• Investissements : <b>{inv_prog_text_red}</b> FCFA (<b>{inv_prog_pct_text_red}%</b>)<br/><br/>

Au {date_periode_red}, le montant total exécuté s'élève à <b>{total_realise_text_red}</b> FCFA, soit un taux d'exécution global de <b>{taux_exec_text_red}%</b> du budget total.<br/><br/>

Répartition de l'exécution par nature de dépenses :<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• Personnel : <b>{personnel_real_text_red}</b> FCFA (<b>{personnel_real_pct_text_red}%</b>)<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• Biens et services : <b>{biens_real_text_red}</b> FCFA (<b>{biens_real_pct_text_red}%</b>)<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• Investissements : <b>{inv_real_text_red}</b> FCFA (<b>{inv_real_pct_text_red}%</b>)"""
        
        # Construire la story avec les titres, le tableau et l'analyse (comme dans le RAP)
        from reportlab.lib.styles import ParagraphStyle
        
        story_styles = getSampleStyleSheet()
        
        # Styles pour les titres
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
        
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=story_styles['Heading2'],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=0,  # LEFT
            spaceAfter=10,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        tableau_title_style = ParagraphStyle(
            "TableauTitle",
            parent=story_styles['Heading3'],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=0,  # LEFT
            spaceAfter=8,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        source_style = ParagraphStyle(
            "SourceStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=11,
            alignment=0,  # LEFT
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica",
            fontSize=12,  # Taille standard pour tout le document
            leading=15,  # Leading ajusté pour fontSize=12
            alignment=4,  # JUSTIFY
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        story = []
        
        # Ajouter les titres de section
        # Le titre "1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME" n'apparaît que dans la première sous-section (1.1)
        story.append(Paragraph("1.2. Les crédits budgétaires", subsection_title_style))
        
        # Obtenir le numéro de tableau automatiquement
        tableau_num = cls.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_num}: Exécution financière par action du programme", tableau_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter le tableau à la story
        story.append(table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter la source
        story.append(Paragraph("Source: Situation d'exécution issue du SIGOBE", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Ajouter l'analyse
        story.append(Paragraph(analyse_html, body_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Ajouter les commentaires personnalisés si disponibles (ou des points si vide)
        credits_commentaires = data.get("credits_commentaires")
        if credits_commentaires and credits_commentaires.strip():
            # Échapper les caractères spéciaux HTML
            commentaires_escaped = credits_commentaires.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convertir les retours à la ligne en <br/>
            commentaires_html = commentaires_escaped.replace("\n", "<br/>")
            # Mettre en rouge (données dynamiques)
            # En mode final, texte en noir ; en mode brouillon, texte en rouge
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
            if mode == "final":
                story.append(Paragraph(commentaires_html, body_style))
            else:
                commentaires_html_red = f"<font color=\"#FF0000\">{commentaires_html}</font>"
                story.append(Paragraph(commentaires_html_red, body_style))
        else:
            # En mode final, ne pas afficher le placeholder
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
            if mode != "final":
                story.append(Paragraph("<font color=\"#FF0000\">Commentaire :..........................</font>", body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Créer le SimpleDocTemplate (comme pour draw_realisations_activites)
        logger.info(f"🔢 NUMÉROTATION - AVANT SimpleDocTemplate pour crédits: start_page={start_page}")
        logger.info(f"📐 Dimensions: width={width:.2f}, height={height:.2f}, margins: L={left_margin:.2f}, R={right_margin:.2f}, T={top_margin:.2f}, B={bottom_margin:.2f}")
        logger.info(f"🔢 NUMÉROTATION - Story crédits contient {len(story)} éléments")
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        # Construire le PDF avec SimpleDocTemplate
        logger.info(f"📋 Génération du PDF avec SimpleDocTemplate - {len(story)} éléments dans la story")
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        from PyPDF2 import PdfReader
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        
        logger.info(f"🔢 NUMÉROTATION - APRÈS SimpleDocTemplate pour crédits: {num_pages} pages générées, final_page={final_page}")
        logger.info(f"🔢 NUMÉROTATION - Nombre de pages générées pour crédits: {num_pages}")
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("rprog_realisations_credits", start_page)
        RAPPageManager.register_page_position("rprog_tableau_2", start_page)
        
        buffer.seek(0)
        return buffer, final_page

    @classmethod
    def draw_realisations_investissements(
        cls,
        pdf: canvas.Canvas = None,
        width: float = None,
        height: float = None,
        start_page: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Génère la section "1.3. Les investissements" avec le tableau de suivi des investissements.
        
        Utilise SimpleDocTemplate pour gérer automatiquement le découpage du LongTable sur plusieurs pages.
        
        Args:
            pdf: Le canvas PDF (optionnel, pour compatibilité)
            width: Largeur de la page (optionnel, utilise A4 landscape par défaut)
            height: Hauteur de la page (optionnel, utilise A4 landscape par défaut)
            start_page: Numéro de page de début
        
        Returns:
            Tuple (BytesIO buffer, numéro de page final) - Le buffer contient le PDF généré
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import Paragraph, LongTable, TableStyle, Spacer, SimpleDocTemplate
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from decimal import Decimal
        from io import BytesIO
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator, RAPPageManager
        from app.models.budget import SigobeExecution, SuiviInvestissement
        from sqlmodel import select, or_
        from datetime import datetime
        
        # Utiliser A4 landscape par défaut si width/height non fournis
        if width is None or height is None:
            width, height = landscape(A4)
        
        # Créer le buffer pour le PDF
        buffer = BytesIO()
        
        # Marges
        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
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
            logger.warning("⚠️ Pas de session DB disponible pour récupérer les données d'investissements")
            # Créer un PDF minimal avec SimpleDocTemplate
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=left_margin,
                rightMargin=right_margin,
                topMargin=top_margin,
                bottomMargin=bottom_margin,
            )
            
            story = []
            styles = getSampleStyleSheet()
            story.append(Paragraph("1.3. Les investissements", 
                                   ParagraphStyle('SubTitle', parent=styles['Heading2'], 
                                                 fontName="Helvetica-Bold", fontSize=12)))
            
            def on_first_page(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            def on_later_pages(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
            buffer.seek(0)
            
            from PyPDF2 import PdfReader
            reader = PdfReader(buffer)
            num_pages = len(reader.pages)
            RAPPageManager.register_page_position("rprog_realisations_investissements", start_page)
            return buffer, start_page + num_pages
        
        # Récupérer les paramètres de filtrage
        programme = data.get("programme", "")
        annee = data.get("annee", 2024)
        periode = data.get("periode", "")
        
        # Charger les données SIGOBE via ReportDataLoader
        from app.services.report_data_loader import ReportDataLoader
        sigobe_data_result = ReportDataLoader.load_data_sigobe(
            session,
            annee,
            programme_nom=programme
        )
        sigobe_data_raw = sigobe_data_result.get("executions", [])
        
        # Filtrer uniquement les investissements
        sigobe_data_filtered = [
            e for e in sigobe_data_raw 
            if e.type_depense and "INVESTISSEMENT" in e.type_depense.upper()
        ]
        
        # Filtrer par période si nécessaire (semestre)
        if periode and "SEMESTRE" in periode.upper():
            if "PREMIER" in periode.upper() or "1" in periode:
                sigobe_data = [e for e in sigobe_data_filtered if e.trimestre in [1, 2]]
            elif "DEUXIEME" in periode.upper() or "2" in periode:
                sigobe_data = [e for e in sigobe_data_filtered if e.trimestre in [3, 4]]
            else:
                sigobe_data = sigobe_data_filtered
        else:
            sigobe_data = sigobe_data_filtered
        
        # Trier les données
        sigobe_data.sort(key=lambda x: (x.actions or "", x.activites or ""))
        
        logger.info(f"📊 {len(sigobe_data)} lignes SIGOBE (investissements) trouvées pour le programme {programme}, année {annee}, période {periode}")
        
        # Récupérer les données de SuiviInvestissement via ReportDataLoader
        suivi_investissements_raw = sigobe_data_result.get("investissements", [])
        suivi_investissements = [
            si for si in suivi_investissements_raw
            if not programme or (si.programme and programme.upper() in si.programme.upper())
        ]
        
        logger.info(f"📊 {len(suivi_investissements)} suivis d'investissements trouvés pour le programme {programme}, année {annee}")
        
        # Créer un dictionnaire pour mapper les SuiviInvestissement par sigobe_execution_id
        suivi_by_sigobe_id = {}
        suivi_by_activite = {}  # Mapping par activité pour les cas sans sigobe_execution_id
        
        for suivi in suivi_investissements:
            if suivi.sigobe_execution_id:
                suivi_by_sigobe_id[suivi.sigobe_execution_id] = suivi
            # Aussi mapper par activité si disponible
            if suivi.action:
                key = f"{suivi.programme or ''}_{suivi.action}"
                if key not in suivi_by_activite:
                    suivi_by_activite[key] = []
                suivi_by_activite[key].append(suivi)
        
        # Organiser les données SIGOBE par activité et mapper avec SuiviInvestissement
        investissements_data = {}
        
        for sigobe in sigobe_data:
            activite_code = sigobe.activites or "Sans activité"
            activite_libelle = activite_code
            
            # Chercher un SuiviInvestissement correspondant
            suivi_inv = None
            if sigobe.id and sigobe.id in suivi_by_sigobe_id:
                suivi_inv = suivi_by_sigobe_id[sigobe.id]
            else:
                # Essayer de mapper par activité/programme
                key = f"{sigobe.programmes or ''}_{sigobe.actions or ''}"
                if key in suivi_by_activite and suivi_by_activite[key]:
                    # Prendre le premier match
                    suivi_inv = suivi_by_activite[key][0]
            
            # Utiliser l'activité comme clé (chaque activité = un projet d'investissement)
            if activite_code not in investissements_data:
                # Initialiser avec les données de SuiviInvestissement si disponibles, sinon avec SIGOBE
                if suivi_inv:
                    investissements_data[activite_code] = {
                        "libelle_projet": suivi_inv.libelle_projet or activite_libelle,
                        "cout_total_projet": suivi_inv.cout_total_projet or Decimal(0),
                        "budget_mobilise_anterieur": suivi_inv.budget_mobilise_anterieur or Decimal(0),
                        "credits_budgetaires_inscrits": suivi_inv.credits_budgetaires_inscrits or Decimal(0),
                        "variation": suivi_inv.variation,
                        "budget_actuel": Decimal(0),  # Sera rempli par SIGOBE
                        "prise_en_charge": Decimal(0),  # Sera rempli par SIGOBE
                        "taux_realisation_budgetaire": suivi_inv.taux_realisation_budgetaire,
                        "taux_realisation_physique": suivi_inv.taux_realisation_physique,
                        "annee_debut": suivi_inv.annee_debut,
                        "commentaire": suivi_inv.commentaire,
                        "financement_interieur": suivi_inv.financement_interieur or Decimal(0),
                        "financement_exterieur": suivi_inv.financement_exterieur or Decimal(0),
                    }
                else:
                    investissements_data[activite_code] = {
                        "libelle_projet": activite_libelle,
                        "cout_total_projet": Decimal(0),
                        "budget_mobilise_anterieur": Decimal(0),
                        "credits_budgetaires_inscrits": Decimal(0),
                        "variation": None,
                        "budget_actuel": Decimal(0),
                        "prise_en_charge": Decimal(0),
                        "taux_realisation_budgetaire": None,
                        "taux_realisation_physique": None,
                        "annee_debut": None,
                        "commentaire": None,
                        "financement_interieur": Decimal(0),
                        "financement_exterieur": Decimal(0),
                    }
            
            # Agréger les montants SIGOBE (budget_actuel et prise_en_charge)
            budget_actuel = sigobe.budget_actuel or Decimal(0)
            mandats_pec = sigobe.mandats_pec or Decimal(0)
            
            investissements_data[activite_code]["budget_actuel"] += budget_actuel
            investissements_data[activite_code]["prise_en_charge"] += mandats_pec
            
            # Si pas de crédits budgétaires inscrits depuis SuiviInvestissement, utiliser budget_actuel
            if investissements_data[activite_code]["credits_budgetaires_inscrits"] == 0:
                investissements_data[activite_code]["credits_budgetaires_inscrits"] += budget_actuel
        
        # Convertir en liste pour compatibilité avec le code existant
        investissements = []
        for activite_code, inv_data in investissements_data.items():
            # Créer un objet simple avec les attributs nécessaires
            class InvestissementData:
                def __init__(self, data):
                    self.libelle_projet = data["libelle_projet"]
                    self.cout_total_projet = data["cout_total_projet"]
                    self.budget_mobilise_anterieur = data["budget_mobilise_anterieur"]
                    self.credits_budgetaires_inscrits = data["credits_budgetaires_inscrits"]
                    self.variation = data["variation"]
                    self.budget_actuel = data["budget_actuel"]
                    self.prise_en_charge = data["prise_en_charge"]
                    # Calculer le taux de réalisation budgétaire si non fourni
                    if data["taux_realisation_budgetaire"] is not None:
                        self.taux_realisation_budgetaire = data["taux_realisation_budgetaire"]
                    elif data["budget_actuel"] > 0:
                        self.taux_realisation_budgetaire = (data["prise_en_charge"] / data["budget_actuel"] * Decimal(100))
                    else:
                        self.taux_realisation_budgetaire = None
                    self.taux_realisation_physique = data["taux_realisation_physique"]
                    self.annee_debut = data.get("annee_debut")
                    self.commentaire = data.get("commentaire")
                    self.financement_interieur = data.get("financement_interieur", Decimal(0))
                    self.financement_exterieur = data.get("financement_exterieur", Decimal(0))
            
            investissements.append(InvestissementData(inv_data))
        
        logger.info(f"📊 {len(investissements)} investissements organisés pour le tableau (combinés SIGOBE + SuiviInvestissement)")
        
        
        # Fonction pour formater un montant
        def format_montant(montant: Decimal | None) -> str:
            if montant is None or montant == 0:
                return "0"
            return f"{int(montant):,}".replace(",", " ")
        
        # Fonction pour formater une variation
        def format_variation(variation: Decimal | None) -> str:
            if variation is None:
                return "-"
            if variation == 0:
                return "-"
            if variation > 0:
                return f"+{format_montant(variation)}"
            return format_montant(variation)
        
        # Fonction pour formater un pourcentage
        def format_pourcentage(pct: Decimal | None) -> str:
            if pct is None:
                return "-"
            return f"{float(pct):.2f}".replace(".", ",")
        
        # Créer un style pour les paragraphes (pour le wrapping du texte)
        styles = getSampleStyleSheet()
        para_style_table3 = styles['Normal']
        para_style_table3.fontName = 'Helvetica'
        para_style_table3.fontSize = 10  # Uniformisé avec le tableau des activités
        para_style_table3.leading = 12   # Augmenté proportionnellement       
        para_style_table3.alignment = 0  # LEFT
        
        # Style spécifique pour la colonne 0 (Projets) - lignes de projets en GRAS avec alignement à gauche
        para_style_col0_bold = ParagraphStyle(
            "ParaTable3Col0Bold",
            parent=styles['Normal'],
            fontName='Helvetica-Bold',  # GRAS pour les lignes de projets
            fontSize=10,
            leading=12,
            alignment=0,  # LEFT - alignement à gauche explicite
        )
        
        # Style spécifique pour la colonne 0 (Projets) - lignes de pourcentages en normal avec alignement à gauche
        para_style_col0_normal = ParagraphStyle(
            "ParaTable3Col0Normal",
            parent=styles['Normal'],
            fontName='Helvetica',  # Normal pour les lignes de pourcentages
            fontSize=10,
            leading=12,
            alignment=0,  # LEFT - alignement à gauche explicite
        )
        
        # Style pour les en-têtes (réduit spécialement pour ce tableau)
        para_style_header = styles['Normal']
        para_style_header.fontName = 'Helvetica-Bold'
        para_style_header.fontSize = 9   # Réduit de 11 à 9 pour les en-têtes
        para_style_header.leading = 10   # Réduit proportionnellement
        para_style_header.alignment = 1  # CENTER
        
        # Fonction helper pour vérifier le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        
        # Fonction helper pour créer un Paragraph avec wrapping
        def create_para_table3(text, max_width=None, is_header=False, is_col0=False, is_col0_bold=False, is_red=False):
            """Crée un Paragraph avec wrapping automatique pour le Tableau 3
            Si is_col0=True, utilise le style spécifique pour la colonne 0 avec alignement à gauche
            Si is_col0_bold=True, utilise le style en gras pour les lignes de projets
            Si is_red=True, met le texte en rouge pour indiquer qu'il est dynamique"""
            if not text:
                return ""
            # Convertir en string et nettoyer
            text = str(text).strip()
            if not text:
                return ""
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Mettre en rouge si demandé (seulement en mode brouillon)
            if is_red and not is_final:
                text = f'<font color="#FF0000">{text}</font>'
            # Utiliser le style approprié
            if is_header:
                style = para_style_header
            elif is_col0_bold:
                style = para_style_col0_bold  # Gras pour les lignes de projets
            elif is_col0:
                style = para_style_col0_normal  # Normal pour les lignes de pourcentages
            else:
                style = para_style_table3
            # ReportLab gère automatiquement le wrapping
            return Paragraph(text, style)
        
        # Calculer les largeurs des colonnes (7 colonnes)
        col_widths = [
            available_width * 0.22,  # Projets
            available_width * 0.14,  # Coût total du projet
            available_width * 0.14,  # Budget déjà mobilisé
            available_width * 0.14,  # Crédits budgétaires inscrits
            available_width * 0.09,  # Variation
            available_width * 0.13,  # Budget Actuel
            available_width * 0.14,  # Prise en charge
        ]
        
        # Construire les données du tableau avec Table et TableStyle (comme dans le RAP)
        table_data = []
        
        # Ligne d'en-tête - utiliser Paragraphs pour permettre le wrapping
        table_data.append([
            create_para_table3("Projets", is_header=True),
            create_para_table3("Coût total du projet", is_header=True),
            create_para_table3("Budget déjà mobilisé au cours des exercices antérieurs", is_header=True),
            create_para_table3("Crédits budgétaires inscrits (LFI de l'année 2024)", is_header=True),
            create_para_table3("Variation (- ou +)", is_header=True),
            create_para_table3("Budget Actuel", is_header=True),
            create_para_table3("Prise en charge (à la fin de la période concernée)", is_header=True),
        ])
        
        # Calculer les totaux
        total_cout = Decimal(0)
        total_budget_mobilise = Decimal(0)
        total_credits_inscrits = Decimal(0)
        total_budget_actuel = Decimal(0)
        total_prise_en_charge = Decimal(0)
        total_financement_interieur = Decimal(0)
        total_financement_exterieur = Decimal(0)
        
        # Fonction helper pour formater les valeurs du tableau d'investissements (définie une fois)
        def format_table_value_inv(value, formatter_func):
            """Retourne la valeur formatée ou '............' si 0 ou None"""
            if value is None or (isinstance(value, Decimal) and value == 0):
                return "............"
            if isinstance(value, (int, float)) and value == 0:
                return "............"
            return formatter_func(value)
        
        # Parcourir les investissements pour construire les lignes de données
        for investissement in investissements:
            libelle = investissement.libelle_projet or ""
            cout_total = investissement.cout_total_projet or Decimal(0)
            budget_mobilise = investissement.budget_mobilise_anterieur or Decimal(0)
            credits_inscrits = investissement.credits_budgetaires_inscrits or Decimal(0)
            variation = investissement.variation
            budget_actuel = investissement.budget_actuel or Decimal(0)
            prise_en_charge = investissement.prise_en_charge or Decimal(0)
            taux_budgetaire = investissement.taux_realisation_budgetaire
            taux_physique = investissement.taux_realisation_physique
            
            # Ajouter aux totaux
            total_cout += cout_total
            total_budget_mobilise += budget_mobilise
            total_credits_inscrits += credits_inscrits
            total_budget_actuel += budget_actuel
            total_prise_en_charge += prise_en_charge
            total_financement_interieur += investissement.financement_interieur or Decimal(0)
            total_financement_exterieur += investissement.financement_exterieur or Decimal(0)
            
            # Ligne 1 : Détails du projet - tous les éléments en rouge car dynamiques
            table_data.append([
                create_para_table3(libelle, is_col0_bold=True, is_red=True),  # Colonne 0 avec style gras et rouge
                create_para_table3(format_table_value_inv(cout_total, format_montant), is_red=True),
                create_para_table3(format_table_value_inv(budget_mobilise, format_montant), is_red=True),
                create_para_table3(format_table_value_inv(credits_inscrits, format_montant), is_red=True),
                create_para_table3(format_variation(variation) if variation is not None else ("" if is_final else "............"), is_red=True),
                create_para_table3(format_table_value_inv(budget_actuel, format_montant), is_red=True),
                create_para_table3(format_table_value_inv(prise_en_charge, format_montant), is_red=True),
            ])
            
            # Ligne 2 : % réal budgétaire (colonne 0 = label, colonnes 1-6 fusionnées = pourcentage)
            taux_budgetaire_text = format_table_value_inv(taux_budgetaire, format_pourcentage)
            if taux_budgetaire_text != "............":
                taux_budgetaire_text = f"{taux_budgetaire_text}%"
            table_data.append([
                create_para_table3("% réal budgétaire", is_col0=True),  # Colonne 0 avec style normal (pas gras, pas rouge)
                create_para_table3(taux_budgetaire_text, is_red=True),  # Colonnes 1-6 fusionnées - pourcentage en rouge
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
            ])
            
            # Ligne 3 : % réal physique (colonne 0 = label, colonnes 1-6 fusionnées = pourcentage)
            taux_physique_text = format_table_value_inv(taux_physique, format_pourcentage)
            if taux_physique_text != "............":
                taux_physique_text = f"{taux_physique_text}%"
            table_data.append([
                create_para_table3("% réal physique", is_col0=True),  # Colonne 0 avec style normal (pas gras, pas rouge)
                create_para_table3(taux_physique_text, is_red=True),  # Colonnes 1-6 fusionnées - pourcentage en rouge
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
            ])
        
        # Calculer les pourcentages totaux
        taux_budgetaire_total = (total_prise_en_charge / total_budget_actuel * 100) if total_budget_actuel > 0 else None
        # Pour le taux physique, on prend la moyenne des taux physiques des projets
        taux_physiques = [inv.taux_realisation_physique for inv in investissements if inv.taux_realisation_physique is not None]
        taux_physique_total = sum(taux_physiques) / len(taux_physiques) if taux_physiques else None
        
        # Ligne de total
        if len(investissements) > 0:
            # Calculer le libellé du total (ex: "Total 22087 Portefeuille de l'Etat")
            programme_nom = programme or "Portefeuille de l'Etat"
            # Extraire le numéro du programme si présent (ex: "22087" de "22087 Portefeuille de l'Etat")
            programme_parts = programme_nom.split()
            programme_num = programme_parts[0] if programme_parts and programme_parts[0].isdigit() else ""
            total_libelle = f"Total {programme_num} {programme_nom}" if programme_num else f"Total {programme_nom}"
            
            # Ligne 1 : Détails du total - tous les éléments en rouge car dynamiques
            table_data.append([
                create_para_table3(total_libelle, is_col0_bold=True, is_red=True),  # Colonne 0 avec style gras et rouge
                create_para_table3(format_table_value_inv(total_cout, format_montant), is_red=True),
                create_para_table3(format_table_value_inv(total_budget_mobilise, format_montant), is_red=True),
                create_para_table3(format_table_value_inv(total_credits_inscrits, format_montant), is_red=True),
                create_para_table3("-", is_red=True),  # Variation totale (généralement non calculée)
                create_para_table3(format_table_value_inv(total_budget_actuel, format_montant), is_red=True),
                create_para_table3(format_table_value_inv(total_prise_en_charge, format_montant), is_red=True),
            ])
            
            # Ligne 2 : % réal budgétaire total (colonne 0 = label, colonnes 1-6 fusionnées = pourcentage)
            taux_budgetaire_total_text = format_table_value_inv(taux_budgetaire_total, format_pourcentage)
            if taux_budgetaire_total_text != "............":
                taux_budgetaire_total_text = f"{taux_budgetaire_total_text}%"
            table_data.append([
                create_para_table3("% réal budgétaire", is_col0=True),  # Colonne 0 avec style normal (pas gras, pas rouge)
                create_para_table3(taux_budgetaire_total_text, is_red=True),  # Colonnes 1-6 fusionnées - pourcentage en rouge
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
            ])
            
            # Ligne 3 : % réal physique total (colonne 0 = label, colonnes 1-6 fusionnées = pourcentage)
            taux_physique_total_text = format_table_value_inv(taux_physique_total, format_pourcentage)
            if taux_physique_total_text != "............":
                taux_physique_total_text = f"{taux_physique_total_text}%"
            table_data.append([
                create_para_table3("% réal physique", is_col0=True),  # Colonne 0 avec style normal (pas gras, pas rouge)
                create_para_table3(taux_physique_total_text, is_red=True),  # Colonnes 1-6 fusionnées - pourcentage en rouge
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
                "",  # Sera fusionné
            ])
        
        # Si aucune donnée trouvée
        if len(investissements) == 0:
            # Calculer la largeur totale pour le message (fusionné sur toutes les colonnes)
            total_width = sum(col_widths)
            table_data.append([
                create_para_table3("Aucun investissement enregistré pour cette période.", total_width),
                "", "", "", "", "", "",
            ])
        
        # Créer le tableau avec LongTable pour permettre la division automatique sur plusieurs pages
        # LongTable est spécialement conçu pour les tableaux qui peuvent déborder sur plusieurs pages
        table = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)  # Répéter la ligne d'en-tête et permettre le découpage
        
        # Créer le style du tableau avec TableStyle (comme dans le RAP)
        table_style = [
            # Bordures
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            
            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),  # Réduit de 11 à 9 pour les en-têtes
            
            # Alignement des données - IMPORTANT: l'ordre compte, les styles plus spécifiques doivent être ajoutés après
            ("ALIGN", (1, 1), (6, -1), "CENTER"),  # Chiffres (colonnes 1-6) centrés
            ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Projets (colonne 0) à gauche - après les autres pour avoir priorité
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            
            # Fonts pour les données
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),  # Uniformisé avec le tableau des activités
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        
        # Ajouter les styles pour les lignes de projets (fond gris) et fusionner les cellules des pourcentages
        if len(investissements) > 0:
            # Pour chaque projet (3 lignes chacune)
            for proj_idx in range(len(investissements)):
                # Ligne de base pour ce projet (après l'en-tête)
                base_row = 1 + (proj_idx * 3)
                
                # Fond gris et gras uniquement pour la ligne de détails du projet (ligne avec le libellé)
                row_details = base_row
                table_style.append(("BACKGROUND", (0, row_details), (-1, row_details), colors.HexColor("#D3D3D3")))  # Gris
                table_style.append(("FONTNAME", (0, row_details), (-1, row_details), "Helvetica-Bold"))  # Gras
                
                # S'assurer que les lignes de pourcentages ne sont PAS en gras (police normale)
                row_pct_budget = base_row + 1
                row_pct_physique = base_row + 2
                table_style.append(("FONTNAME", (0, row_pct_budget), (-1, row_pct_budget), "Helvetica"))  # Normal, pas gras
                table_style.append(("FONTNAME", (0, row_pct_physique), (-1, row_pct_physique), "Helvetica"))  # Normal, pas gras
                
                # Fusionner les cellules des lignes de pourcentages : colonnes 1-6 fusionnées
                # Ligne 2 : % réal budgétaire - fusionner colonnes 1-6
                table_style.append(("SPAN", (1, row_pct_budget), (6, row_pct_budget)))  # Fusionner colonnes 1-6
                table_style.append(("ALIGN", (0, row_pct_budget), (0, row_pct_budget), "LEFT"))  # Colonne 0 à gauche
                table_style.append(("ALIGN", (1, row_pct_budget), (6, row_pct_budget), "CENTER"))  # Centrer le pourcentage
                
                # Ligne 3 : % réal physique - fusionner colonnes 1-6
                table_style.append(("SPAN", (1, row_pct_physique), (6, row_pct_physique)))  # Fusionner colonnes 1-6
                table_style.append(("ALIGN", (0, row_pct_physique), (0, row_pct_physique), "LEFT"))  # Colonne 0 à gauche
                table_style.append(("ALIGN", (1, row_pct_physique), (6, row_pct_physique), "CENTER"))  # Centrer le pourcentage
        
        # Ajouter les styles pour les lignes de total (3 lignes : détails + % budgétaire + % physique)
        if len(investissements) > 0:
            # Calculer la première ligne du total (après tous les projets et leurs lignes de pourcentages)
            # Chaque projet a 3 lignes (détails + % budgétaire + % physique)
            total_start_row = 1 + (len(investissements) * 3)  # 1 pour l'en-tête + 3 lignes par projet
            
            # Appliquer le style aux 3 lignes du total
            for i in range(3):
                row = total_start_row + i
                table_style.append(("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"))
                table_style.append(("FONTSIZE", (0, row), (-1, row), 10))  # Uniformisé avec le tableau des activités
                table_style.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#f4b083")))  # Orange
            
            # Fusionner les cellules des lignes de pourcentages du total : colonnes 1-6 fusionnées
            # Ligne 2 du total : % réal budgétaire - fusionner colonnes 1-6
            row_pct_budget_total = total_start_row + 1
            table_style.append(("SPAN", (1, row_pct_budget_total), (6, row_pct_budget_total)))  # Fusionner colonnes 1-6
            table_style.append(("ALIGN", (0, row_pct_budget_total), (0, row_pct_budget_total), "LEFT"))  # Colonne 0 à gauche
            table_style.append(("ALIGN", (1, row_pct_budget_total), (6, row_pct_budget_total), "CENTER"))  # Centrer le pourcentage
            
            # Ligne 3 du total : % réal physique - fusionner colonnes 1-6
            row_pct_physique_total = total_start_row + 2
            table_style.append(("SPAN", (1, row_pct_physique_total), (6, row_pct_physique_total)))  # Fusionner colonnes 1-6
            table_style.append(("ALIGN", (0, row_pct_physique_total), (0, row_pct_physique_total), "LEFT"))  # Colonne 0 à gauche
            table_style.append(("ALIGN", (1, row_pct_physique_total), (6, row_pct_physique_total), "CENTER"))  # Centrer le pourcentage
        
        # Si aucune donnée trouvée, fusionner toutes les colonnes du message
        if len(investissements) == 0:
            # La ligne du message est à l'index 1 (après l'en-tête)
            table_style.append(("SPAN", (0, 1), (-1, 1)))  # Fusionner toutes les colonnes
            table_style.append(("ALIGN", (0, 1), (-1, 1), "CENTER"))  # Centrer le message
        
        # Appliquer le style au tableau
        table.setStyle(TableStyle(table_style))
        # Déterminer la date de période selon la période spécifiée
        periode = data.get("periode", "")
        if periode:
            periode_upper = periode.upper()
            if "PREMIER" in periode_upper or "1" in periode:
                date_periode = f"30-06-{annee}"
            elif "DEUXIEME" in periode_upper or "2" in periode:
                date_periode = f"31-12-{annee}"
            else:
                date_periode = datetime.now().strftime("%d-%m-%Y")
        else:
            date_periode = f"30-06-{annee}"
        
        source_text = f"Loi de Finances initiale {annee}/ Tirage SIGOBE ({date_periode})"
        
        # Générer le texte explicatif
        programme_nom = programme or "Portefeuille de l'Etat"
        
        # Vérifier si les données sont disponibles
        has_investissement_data = len(investissements) > 0 and (total_credits_inscrits > 0 or total_cout > 0)
        
        # Fonction helper pour vérifier le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        
        # Fonction helper pour formater les valeurs ou retourner des points
        def format_value_inv(value, formatter_func):
            """Retourne la valeur formatée ou '............' (brouillon) ou '' (final) si non disponible"""
            if not has_investissement_data or value is None or (isinstance(value, Decimal) and value == 0):
                return "" if is_final else "............"
            return formatter_func(value)
        
        # Fonction helper pour formater le texte selon le mode
        def format_text_for_mode(text):
            """Formate le texte en rouge (brouillon) ou noir (final)"""
            if is_final:
                return str(text)
            else:
                return f'<font color="#FF0000">{text}</font>'
        
        # Premier paragraphe (convertir en HTML pour Paragraph)
        credits_inscrits_text = format_value_inv(total_credits_inscrits, format_montant)
        # Mettre tous les éléments dynamiques en rouge (ou noir en mode final)
        credits_inscrits_text_red = format_text_for_mode(credits_inscrits_text)
        annee_red = format_text_for_mode(annee)
        programme_nom_red = format_text_for_mode(programme_nom)
        
        # Déterminer le type de financement de manière dynamique
        financement_interieur_val = total_financement_interieur or Decimal(0)
        financement_exterieur_val = total_financement_exterieur or Decimal(0)
        
        # Générer le texte de financement dynamique
        if financement_interieur_val > 0 and financement_exterieur_val > 0:
            # Financement mixte
            financement_interieur_text = format_montant(financement_interieur_val)
            financement_exterieur_text = format_montant(financement_exterieur_val)
            texte_financement = (
                f"Ce financement est financé par des ressources intérieures ({financement_interieur_text} FCFA) "
                f"et extérieures ({financement_exterieur_text} FCFA)."
            )
        elif financement_exterieur_val > 0:
            # Financement extérieur uniquement
            financement_exterieur_text = format_montant(financement_exterieur_val)
            texte_financement = (
                f"Ce financement est exclusivement financé par des ressources extérieures ({financement_exterieur_text} FCFA)."
            )
        else:
            # Financement intérieur uniquement (par défaut)
            texte_financement = 'Ce financement est exclusivement financé par des ressources intérieures.'
        
        # Appliquer le formatage selon le mode
        if not is_final:
            texte_financement = f'<font color="#FF0000">{texte_financement}</font>'
        
        # Vérifier s'il y a eu une variation
        # Si tous les investissements ont une variation à None ou 0, alors "aucune variation"
        has_variation = False
        if has_investissement_data:
            for inv in investissements:
                if inv.variation is not None and inv.variation != 0:
                    has_variation = True
                    break
        
        if has_variation:
            texte_variation = 'L\'allocation (dotation) a connu des variations au cours de la gestion.'
        else:
            texte_variation = 'L\'allocation (dotation) n\'a connu aucune variation au cours de la gestion.'
        
        # Appliquer le formatage selon le mode
        if not is_final:
            texte_variation = f'<font color="#FF0000">{texte_variation}</font>'
        
        texte_paragraphe_1_html = (
            f"Le programme « {programme_nom_red} » a bénéficié d'un budget d'investissement de "
            f"<b>{credits_inscrits_text_red}</b> FCFA au titre de la loi de finances de {annee_red}. "
            f"{texte_financement} "
            f"{texte_variation}"
        )
        
        # Deuxième paragraphe
        taux_exec_text = format_value_inv(taux_budgetaire_total, format_pourcentage)
        taux_physique_text = format_value_inv(taux_physique_total, format_pourcentage)
        cout_total_text = format_value_inv(total_cout, format_montant)
        
        # Déterminer le nom du projet principal
        projet_principal = "" if is_final else "............"
        if has_investissement_data and investissements:
            premier_investissement = investissements[0]
            projet_principal = premier_investissement.libelle_projet or ("" if is_final else "............")
        
        # Déterminer l'année de début des travaux
        annee_debut_travaux_text = "" if is_final else "............"
        if has_investissement_data:
            for inv in investissements:
                if inv.annee_debut:
                    annee_debut_travaux_text = str(inv.annee_debut)
                    break
        
        # Utiliser la date de période pour le texte
        if periode:
            periode_upper = periode.upper()
            if "PREMIER" in periode_upper or "1" in periode:
                date_periode_text = f"30 juin {annee}"
            elif "DEUXIEME" in periode_upper or "2" in periode:
                date_periode_text = f"31 décembre {annee}"
            else:
                date_periode_text = date_periode
        else:
            date_periode_text = f"30 juin {annee}"
        
        # Mettre tous les éléments dynamiques en rouge (ou noir en mode final)
        # Ajouter le signe % aux taux s'ils ne sont pas des placeholders
        placeholder = "" if is_final else "............"
        taux_exec_text_with_pct = f"{taux_exec_text}%" if taux_exec_text != placeholder and taux_exec_text else taux_exec_text
        taux_physique_text_with_pct = f"{taux_physique_text}%" if taux_physique_text != placeholder and taux_physique_text else taux_physique_text
        taux_exec_text_red = format_text_for_mode(taux_exec_text_with_pct)
        taux_physique_text_red = format_text_for_mode(taux_physique_text_with_pct)
        cout_total_text_red = format_text_for_mode(cout_total_text)
        projet_principal_red = format_text_for_mode(projet_principal)
        annee_debut_travaux_text_red = format_text_for_mode(annee_debut_travaux_text)
        date_periode_text_red = format_text_for_mode(date_periode_text)
        
        # Utiliser le commentaire comme interprétation si disponible, sinon utiliser le texte par défaut
        # Texte par défaut pour l'analyse globale
        texte_paragraphe_2_html = (
            f"Le budget d'investissement du programme a été exécuté à <b>{taux_exec_text_red}</b> au {date_periode_text_red}. "    
            )
        
        # Construire la story avec les titres, le tableau et l'analyse (comme dans le RAP)
        from reportlab.lib.styles import ParagraphStyle
        
        story_styles = getSampleStyleSheet()
        
        # Styles pour les titres
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
        
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=story_styles['Heading2'],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=0,  # LEFT
            spaceAfter=10,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        tableau_title_style = ParagraphStyle(
            "TableauTitle",
            parent=story_styles['Heading3'],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=0,  # LEFT
            spaceAfter=8,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        source_style = ParagraphStyle(
            "SourceStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=11,
            alignment=0,  # LEFT
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=story_styles['Normal'],
            fontName="Helvetica",
            fontSize=12,  # Taille standard pour tout le document
            leading=15,  # Leading ajusté pour fontSize=12
            alignment=4,  # JUSTIFY
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        story = []
        
        # Ajouter les titres de section
        # Le titre "1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME" n'apparaît que dans la première sous-section (1.1)
        story.append(Paragraph("1.3. Les investissements", subsection_title_style))
        
        # Obtenir le numéro de tableau automatiquement
        tableau_num = cls.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_num}: Suivi des investissements du programme", tableau_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter le tableau à la story
        story.append(table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter la source
        story.append(Paragraph(source_text, source_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Ajouter les paragraphes explicatifs (analyse globale)
        story.append(Paragraph(texte_paragraphe_1_html, body_style))
        story.append(Spacer(1, 0.05 * cm))
        story.append(Paragraph(texte_paragraphe_2_html, body_style))
        story.append(Spacer(1, 0.05 * cm))
        
        # Ajouter l'analyse par projet (pour TOUS les projets du tableau)
        if len(investissements) > 0:
            # Titre pour la section d'analyse par projet
            story.append(Paragraph("Cette situation a été possible grâce aux projets suivants :", subsection_title_style))
            story.append(Spacer(1, 0.08 * cm))
            
            # Fonction helper pour formater le texte selon le mode (définie une seule fois avant la boucle)
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
            is_final = mode == "final"
            def format_text_for_mode(text):
                """Formate le texte en rouge (brouillon) ou noir (final)"""
                if is_final:
                    return str(text)
                else:
                    return f'<font color="#FF0000">{text}</font>'
            
            # Pour chaque projet, créer une analyse basée sur ses données
            for inv in investissements:
                # Titre du projet
                projet_libelle = inv.libelle_projet or "Projet"
                projet_libelle_red = format_text_for_mode(projet_libelle)
                #story.append(Paragraph(f"<b>Projet : {projet_libelle_red}</b>", body_style))
                #story.append(Spacer(1, 0.1 * cm))
                
                # Générer l'analyse du projet basée sur ses données
                cout_projet = format_value_inv(inv.cout_total_projet, format_montant)
                cout_projet_red = format_text_for_mode(cout_projet)
                
                taux_budgetaire_projet = format_value_inv(inv.taux_realisation_budgetaire, format_pourcentage)
                taux_physique_projet = format_value_inv(inv.taux_realisation_physique, format_pourcentage)
                
                # Ajouter le signe % aux taux s'ils ne sont pas des placeholders
                placeholder = "" if is_final else "............"
                if taux_budgetaire_projet != placeholder and taux_budgetaire_projet:
                    taux_budgetaire_projet = f"{taux_budgetaire_projet}%"
                if taux_physique_projet != placeholder and taux_physique_projet:
                    taux_physique_projet = f"{taux_physique_projet}%"
                
                taux_budgetaire_projet_red = format_text_for_mode(taux_budgetaire_projet)
                taux_physique_projet_red = format_text_for_mode(taux_physique_projet)
                
                annee_debut_projet = str(inv.annee_debut) if inv.annee_debut else placeholder
                annee_debut_projet_red = format_text_for_mode(annee_debut_projet)
                
                # Texte d'analyse du projet
                analyse_projet_html = (
                    f"- Le coût total du projet « {projet_libelle_red} » est de <b>{cout_projet_red}</b> FCFA. "
                    f"Le taux de réalisation budgétaire est de <b>{taux_budgetaire_projet_red}</b> au {date_periode_text_red}. "
                    f"Les travaux ont démarré en {annee_debut_projet_red}. "
                    f"Les travaux en cours sont estimés à <b>{taux_physique_projet_red}</b> d'avancement physique au {date_periode_text_red}."
                )
                story.append(Paragraph(analyse_projet_html, body_style))
                
                # Ajouter le commentaire comme justification si disponible
                if inv.commentaire and inv.commentaire.strip():
                    story.append(Spacer(1, 0.1 * cm))
                    commentaire_projet = inv.commentaire.strip()
                    commentaire_projet_escaped = (
                        commentaire_projet
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    if is_final:
                        story.append(Paragraph(commentaire_projet_escaped, body_style))
                    else:
                        commentaire_projet_red = f'<font color="#FF0000">{commentaire_projet_escaped}</font>'
                        story.append(Paragraph(commentaire_projet_red, body_style))
                
                story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter les commentaires personnalisés si disponibles (ou des points si vide)
        investissements_commentaires = data.get("investissements_commentaires")
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        if investissements_commentaires and investissements_commentaires.strip():
            story.append(Spacer(1, 0.3 * cm))
            # Échapper les caractères spéciaux HTML
            commentaires_escaped = investissements_commentaires.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convertir les retours à la ligne en <br/>
            commentaires_html = commentaires_escaped.replace("\n", "<br/>")
            # En mode final, texte en noir ; en mode brouillon, texte en rouge
            if mode == "final":
                story.append(Paragraph(commentaires_html, body_style))
            else:
                commentaires_html_red = f"<font color=\"#FF0000\">{commentaires_html}</font>"
                story.append(Paragraph(commentaires_html_red, body_style))
        else:
            story.append(Spacer(1, 0.3 * cm))
            # Afficher des points si aucun commentaire
            story.append(Paragraph("<font color=\"#FF0000\">Commentaire :..........................</font>", body_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Créer le SimpleDocTemplate
        logger.info(f"🔢 NUMÉROTATION - AVANT SimpleDocTemplate pour investissements: start_page={start_page}")
        logger.info(f"📐 Dimensions: width={width:.2f}, height={height:.2f}, margins: L={left_margin:.2f}, R={right_margin:.2f}, T={top_margin:.2f}, B={bottom_margin:.2f}")
        logger.info(f"🔢 NUMÉROTATION - Story investissements contient {len(story)} éléments")
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        # Construire le PDF avec SimpleDocTemplate
        logger.info(f"📋 Génération du PDF avec SimpleDocTemplate - {len(story)} éléments dans la story")
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        from PyPDF2 import PdfReader
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        
        logger.info(f"🔢 NUMÉROTATION - APRÈS SimpleDocTemplate pour investissements: {num_pages} pages générées, final_page={final_page}")
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("rprog_realisations_investissements", start_page)
        RAPPageManager.register_page_position("rprog_tableau_3", start_page)
        
        buffer.seek(0)
        return buffer, final_page
    
    @classmethod
    def draw_realisations_effectifs(
        cls,
        pdf: canvas.Canvas = None,
        width: float = None,
        height: float = None,
        start_page: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Génère la section "1.4. Les effectifs" avec le tableau des effectifs et le graphique.
        
        Utilise SimpleDocTemplate pour gérer automatiquement le découpage du LongTable sur plusieurs pages.
        
        Args:
            pdf: Le canvas PDF (optionnel, pour compatibilité)
            width: Largeur de la page (optionnel, utilise A4 landscape par défaut)
            height: Hauteur de la page (optionnel, utilise A4 landscape par défaut)
            start_page: Numéro de page de début
        
        Returns:
            Tuple (BytesIO buffer, numéro de page final) - Le buffer contient le PDF généré
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import Paragraph, LongTable, TableStyle, Spacer, Image as RLImage, SimpleDocTemplate
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus.flowables import Image as FlowableImage
        from datetime import date
        from io import BytesIO
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator, RAPPageManager
        from app.models.personnel import AgentComplet, GradeComplet
        from app.core.enums import GradeCategory, PositionAdministrative
        from sqlmodel import select
        
        # Utiliser A4 landscape par défaut si width/height non fournis
        if width is None or height is None:
            width, height = landscape(A4)
        
        # Créer le buffer pour le PDF
        buffer = BytesIO()
        
        # Marges (identiques au tableau des investissements)
        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
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
            logger.warning("⚠️ Pas de session DB disponible pour récupérer les données d'effectifs")
            # Créer un PDF minimal avec SimpleDocTemplate
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=left_margin,
                rightMargin=right_margin,
                topMargin=top_margin,
                bottomMargin=bottom_margin,
            )
            
            story = []
            styles = getSampleStyleSheet()
            story.append(Paragraph("1.4. Les effectifs", 
                                   ParagraphStyle('SubTitle', parent=styles['Heading2'], 
                                                 fontName="Helvetica-Bold", fontSize=12)))
            
            def on_first_page(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            def on_later_pages(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
            buffer.seek(0)
            
            from PyPDF2 import PdfReader
            reader = PdfReader(buffer)
            num_pages = len(reader.pages)
            RAPPageManager.register_page_position("rprog_realisations_effectifs", start_page)
            return buffer, start_page + num_pages
        
        # Récupérer les paramètres de filtrage
        programme = data.get("programme", "")
        annee = data.get("annee", 2024)
        
        # Dates de référence
        date_debut = date(2023, 12, 31)  # 31/12/2023
        date_fin = date(2024, 6, 30)  # 30/06/2024
        
        # Récupérer tous les agents actifs
        # D'abord, vérifier combien d'agents existent au total
        total_agents = session.exec(select(AgentComplet)).all()
        logger.info(f"📊 Total d'agents dans la base: {len(total_agents)}")
        
        # Vérifier les agents actifs
        agents_actifs = session.exec(
            select(AgentComplet).where(AgentComplet.actif == True)
        ).all()
        logger.info(f"📊 Agents actifs: {len(agents_actifs)}")
        
        # Vérifier les agents en activité
        agents_en_activite = session.exec(
            select(AgentComplet).where(
                AgentComplet.position_administrative == PositionAdministrative.EN_ACTIVITE.value
            )
        ).all()
        logger.info(f"📊 Agents en activité: {len(agents_en_activite)}")
        
        # Log détaillé pour les premiers agents
        for agent in total_agents[:5]:  # Afficher les 5 premiers
            logger.info(f"  - Agent: {agent.nom} {agent.prenom} (ID: {agent.id})")
            logger.info(f"    Actif: {agent.actif}, Position: {agent.position_administrative}, Programme ID: {agent.programme_id}")
        
        query = select(AgentComplet).where(
            AgentComplet.actif == True,
            AgentComplet.position_administrative == PositionAdministrative.EN_ACTIVITE.value
        )
        
        # Filtrer par programme si fourni
        if programme:
            # Chercher le programme par son libellé pour obtenir son ID
            from app.models.personnel import Programme, Direction, SousDirection, Service
            programme_obj = session.exec(
                select(Programme).where(Programme.libelle.ilike(f"%{programme}%"))
            ).first()
            
            if programme_obj:
                logger.info(f"🔍 Programme trouvé: {programme_obj.libelle} (ID: {programme_obj.id})")
                
                # Vérifier combien d'agents ont ce programme_id directement
                agents_avec_programme = session.exec(
                    select(AgentComplet).where(AgentComplet.programme_id == programme_obj.id)
                ).all()
                logger.info(f"📊 Agents avec programme_id={programme_obj.id}: {len(agents_avec_programme)}")
                
                # Chercher les directions, sous-directions et services liés au programme
                directions = session.exec(
                    select(Direction).where(Direction.programme_id == programme_obj.id)
                ).all()
                direction_ids = [d.id for d in directions]
                logger.info(f"📊 Directions liées au programme: {len(directions)} (IDs: {direction_ids})")
                
                # Chercher les sous-directions liées au programme directement
                sous_directions_directes = session.exec(
                    select(SousDirection).where(SousDirection.programme_id == programme_obj.id)
                ).all()
                sous_direction_ids = [sd.id for sd in sous_directions_directes]
                
                # Chercher aussi les sous-directions liées aux directions du programme
                if direction_ids:
                    sous_directions_via_directions = session.exec(
                        select(SousDirection).where(SousDirection.direction_id.in_(direction_ids))
                    ).all()
                    sous_direction_ids.extend([sd.id for sd in sous_directions_via_directions])
                    sous_direction_ids = list(set(sous_direction_ids))  # Dédupliquer
                
                logger.info(f"📊 Sous-directions liées au programme: {len(sous_direction_ids)} (IDs: {sous_direction_ids})")
                
                # Chercher les services liés au programme directement
                services_directs = session.exec(
                    select(Service).where(Service.programme_id == programme_obj.id)
                ).all()
                service_ids = [s.id for s in services_directs]
                
                # Chercher les services liés aux directions du programme
                if direction_ids:
                    services_via_directions = session.exec(
                        select(Service).where(Service.direction_id.in_(direction_ids))
                    ).all()
                    service_ids.extend([s.id for s in services_via_directions])
                
                # Chercher les services liés aux sous-directions du programme
                if sous_direction_ids:
                    services_via_sous_directions = session.exec(
                        select(Service).where(Service.sous_direction_id.in_(sous_direction_ids))
                    ).all()
                    service_ids.extend([s.id for s in services_via_sous_directions])
                
                service_ids = list(set(service_ids))  # Dédupliquer
                logger.info(f"📊 Services liés au programme: {len(service_ids)} (IDs: {service_ids})")
                
                # Construire les conditions de recherche : programme_id OU direction_id OU sous_direction_id OU service_id
                from sqlmodel import or_
                search_conditions = [AgentComplet.programme_id == programme_obj.id]
                
                if direction_ids:
                    search_conditions.append(AgentComplet.direction_id.in_(direction_ids))
                if sous_direction_ids:
                    search_conditions.append(AgentComplet.sous_direction_id.in_(sous_direction_ids))
                if service_ids:
                    search_conditions.append(AgentComplet.service_id.in_(service_ids))
                
                # Filtrer par programme_id OU direction_id OU sous_direction_id OU service_id
                if len(search_conditions) > 1:
                    query = query.where(or_(*search_conditions))
                    logger.info(f"🔍 Recherche d'agents via programme_id OU direction_id OU sous_direction_id OU service_id")
                else:
                    query = query.where(AgentComplet.programme_id == programme_obj.id)
                    logger.info(f"🔍 Recherche d'agents via programme_id uniquement")
            else:
                logger.warning(f"⚠️ Programme '{programme}' non trouvé dans la base de données")
        else:
            logger.info("ℹ️ Aucun programme spécifié, récupération de tous les agents actifs")
        
        agents = session.exec(query).all()
        
        logger.info(f"📊 {len(agents)} agents trouvés pour le programme {programme}, année {annee}")
        
        # Log détaillé pour chaque agent
        for agent in agents:
            logger.info(f"  - Agent: {agent.nom} {agent.prenom} (Matricule: {agent.matricule})")
            logger.info(f"    Grade ID: {agent.grade_id}, Date recrutement: {agent.date_recrutement}, Date prise service: {agent.date_prise_service}")
            if agent.grade_id:
                grade = session.get(GradeComplet, agent.grade_id)
                if grade:
                    logger.info(f"    Grade: {grade.code} ({grade.libelle}), Catégorie: {grade.categorie}")
        
        # Calculer les effectifs par catégorie (A, B, C, D) en comptant par grade (avec échelon)
        effectifs_debut = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
            "Non fonctionnaires": 0
        }
        effectifs_fin = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
            "Non fonctionnaires": 0
        }
        entrees = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
            "Non fonctionnaires": 0
        }
        sorties = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
            "Non fonctionnaires": 0
        }
        
        # Pour chaque agent, déterminer sa catégorie depuis le grade (avec échelon)
        for agent in agents:
            # Déterminer la catégorie depuis le code du grade (qui contient l'échelon, ex: A1, A2, B1, etc.)
            categorie = "Non fonctionnaires"
            if agent.grade_id:
                grade = session.get(GradeComplet, agent.grade_id)
                if grade and grade.code:
                    # Extraire la lettre de la catégorie depuis le code (A1 -> A, B2 -> B, etc.)
                    # Le code du grade est de la forme "A1", "A2", "B1", etc.
                    grade_code = grade.code.strip()
                    if grade_code and len(grade_code) > 0:
                        # Prendre le premier caractère (la lettre de la catégorie)
                        categorie = grade_code[0].upper()
                        # Vérifier que c'est bien une catégorie valide (A, B, C, D)
                        if categorie not in ["A", "B", "C", "D"]:
                            categorie = "Non fonctionnaires"
                    logger.info(f"  Agent {agent.nom} {agent.prenom}: Grade code={grade_code}, Catégorie={categorie}")
                else:
                    logger.warning(f"  Agent {agent.nom} {agent.prenom}: Grade sans code")
            else:
                logger.info(f"  Agent {agent.nom} {agent.prenom}: Pas de grade_id, catégorie=Non fonctionnaires")
            
            # Déterminer si l'agent était présent au 31/12/2023
            date_recrutement = agent.date_recrutement
            date_prise_service = agent.date_prise_service or date_recrutement
            
            logger.info(f"  Agent {agent.nom} {agent.prenom}: Date recrutement={date_recrutement}, Date prise service={date_prise_service}")
            logger.info(f"  Dates de référence: date_debut={date_debut}, date_fin={date_fin}")
            
            # Si l'agent a été recruté avant ou le 31/12/2023, il compte dans effectifs_debut
            # Si pas de date, on considère qu'il était présent au début
            if not date_prise_service or date_prise_service <= date_debut:
                effectifs_debut[categorie] = effectifs_debut.get(categorie, 0) + 1
                logger.info(f"  → Compté dans effectifs_debut[{categorie}]")
            else:
                logger.info(f"  → NON compté dans effectifs_debut (date_prise_service={date_prise_service} > date_debut={date_debut})")
            
            # Si l'agent est présent au 30/06/2024, il compte dans effectifs_fin
            # Pour simplifier, on considère que tous les agents actifs sont présents
            # Si pas de date de recrutement ou si recruté avant/le 30/06/2024
            if not agent.date_recrutement or agent.date_recrutement <= date_fin:
                effectifs_fin[categorie] = effectifs_fin.get(categorie, 0) + 1
                logger.info(f"  → Compté dans effectifs_fin[{categorie}]")
                
                # Si recruté entre les deux dates, c'est une entrée
                if date_prise_service and date_debut < date_prise_service <= date_fin:
                    entrees[categorie] = entrees.get(categorie, 0) + 1
                    logger.info(f"  → Compté dans entrees[{categorie}]")
            else:
                logger.info(f"  → NON compté dans effectifs_fin (date_recrutement={agent.date_recrutement} > date_fin={date_fin})")
        
        logger.info(f"📊 Résultats du décompte:")
        logger.info(f"  effectifs_debut: {effectifs_debut}")
        logger.info(f"  effectifs_fin: {effectifs_fin}")
        logger.info(f"  entrees: {entrees}")
        logger.info(f"  sorties: {sorties}")
        
        # Calculer les sorties pour chaque catégorie
        for cat in ["A", "B", "C", "D", "Non fonctionnaires"]:
            sorties[cat] = max(0, effectifs_debut[cat] + entrees[cat] - effectifs_fin[cat])
        
        # Calculer les totaux
        total_debut = sum(effectifs_debut.values())
        total_fin = sum(effectifs_fin.values())
        total_entrees = sum(entrees.values())
        total_sorties = sum(sorties.values())
        
        # Vérifier si les données sont disponibles (si aucun agent trouvé ou données vides)
        has_data = len(agents) > 0 and (total_debut > 0 or total_fin > 0)
        logger.info(f"📊 has_data = {has_data} (agents: {len(agents)}, total_debut: {total_debut}, total_fin: {total_fin})")
        
        # Fonction helper pour formater les valeurs ou retourner des points
        def format_value(value):
            """Retourne la valeur formatée ou '............' si non disponible"""
            # Toujours afficher la valeur si elle est > 0, même si has_data est False
            if value is None or value == 0:
                return "............"
            return str(value)
        
        # Créer un style pour les paragraphes
        styles = getSampleStyleSheet()
        para_style_table4 = styles['Normal']
        para_style_table4.fontName = 'Helvetica'
        para_style_table4.fontSize = 10  # Uniformisé avec le tableau des activités
        para_style_table4.leading = 12   # Augmenté proportionnellement
        para_style_table4.alignment = 0  # LEFT
        
        # Style pour les en-têtes
        header_style = styles['Normal']
        header_style.fontName = 'Helvetica-Bold'
        header_style.fontSize = 11  # Uniformisé avec le tableau des activités
        header_style.leading = 13   # Augmenté proportionnellement
        header_style.alignment = 1  # CENTER
        
        # Style pour la première colonne dans les en-têtes (centré)
        header_style_col0 = styles['Normal']
        header_style_col0.fontName = 'Helvetica-Bold'
        header_style_col0.fontSize = 11
        header_style_col0.leading = 13
        header_style_col0.alignment = 1  # CENTER
        
        # Style pour les nombres (centré, pas en gras, rouge via HTML)
        number_style = ParagraphStyle(
            'NumberStyle',
            parent=styles['Normal'],
            fontName='Helvetica',  # Pas en gras
            fontSize=10,
            leading=12,
            alignment=1,  # CENTER
            leftIndent=0,
            rightIndent=0,
        )
        
        # Style pour la colonne Catégorie (aligné à gauche, en gras)
        category_style = ParagraphStyle(
            'CategoryStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',  # En gras
            fontSize=10,
            leading=12,
            alignment=0,  # LEFT
            leftIndent=0,
            rightIndent=0,
        )
        
        # Fonction helper pour créer un Paragraph
        def create_para_table4(text, is_header=False, is_col0=False, is_number=False):
            """Crée un Paragraph avec wrapping automatique pour le Tableau 4"""
            if not text:
                return ""
            text = str(text).strip()
            if not text:
                return ""
            # Échapper les caractères spéciaux pour XML/HTML
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Si c'est un nombre, mettre en rouge (brouillon) ou noir (final) avec des balises HTML
            if is_number:
                # Vérifier le mode
                mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
                if mode == "final":
                    # En mode final, pas de balise font (texte noir par défaut)
                    pass
                else:
                    # En mode brouillon, texte en rouge
                    text = f'<font color="#FF0000">{text}</font>'
            
            if is_header and is_col0:
                style = header_style_col0
            elif is_header:
                style = header_style
            elif is_number:
                style = number_style
            elif is_col0:
                style = category_style
            else:
                style = para_style_table4
            # ReportLab gère automatiquement le wrapping
            return Paragraph(text, style)
        
        # Calculer les largeurs des colonnes (5 colonnes au total)
        # Les pourcentages doivent totaliser 1.0 (100%)
        col_widths = [
            available_width * 0.25,  # Catégorie (25%)
            available_width * 0.20,  # Situation au 31/12/2023 (20%)
            available_width * 0.11,  # Variation - Entrées (11%)
            available_width * 0.11,  # Variation - Sorties (11%)
            available_width * 0.33,  # Situation au 30/06/2024 (33%)
        ]
        
        # Vérifier et ajuster les largeurs pour qu'elles correspondent exactement à available_width
        total_col_widths = sum(col_widths)
        if abs(total_col_widths - available_width) > 0.01:  # Tolérance de 0.01 point
            scale_factor = available_width / total_col_widths
            col_widths = [w * scale_factor for w in col_widths]
            logger.info(f"📊 Largeurs ajustées pour correspondre à available_width: {[f'{w:.2f}' for w in col_widths]}, Somme: {sum(col_widths):.2f}")
        
        logger.info(f"📊 Somme largeurs colonnes: {sum(col_widths):.2f}")
        logger.info(f"📊 available_width: {available_width:.2f}")
        logger.info(f"📊 Différence: {(available_width - sum(col_widths)):.2f}")
        
        # Construire les données du tableau
        table_data = []
        
        # Ligne d'en-tête principale (ligne 1)
        table_data.append([
            create_para_table4("Catégorie", is_header=True, is_col0=True),  # Première colonne alignée à gauche
            create_para_table4("Situation au 31/12/2023", is_header=True),
            create_para_table4("Variation", is_header=True),  # En-tête principal pour Variation (sera fusionné avec la colonne suivante)
            create_para_table4("", is_header=True),  # Cellule vide pour la fusion
            create_para_table4("Situation au 30/06/2024", is_header=True),
        ])
        
        # Ligne d'en-tête secondaire (ligne 2) - sous-en-têtes pour Variation
        table_data.append([
            create_para_table4("", is_header=True, is_col0=True),  # Vide (fusionné avec ligne 1) - première colonne alignée à gauche
            create_para_table4("", is_header=True),  # Vide (fusionné avec ligne 1)
            create_para_table4("Entrées", is_header=True),  # Sous-en-tête Entrées
            create_para_table4("Sorties", is_header=True),  # Sous-en-tête Sorties
            create_para_table4("", is_header=True),  # Vide (fusionné avec ligne 1)
        ])
        
        # Lignes de données - Afficher uniquement les catégories (A, B, C, D)
        categories_order = ["A", "B", "C", "D", "Non fonctionnaires"]
        category_labels = {
            "A": "Catégorie A",
            "B": "Catégorie B",
            "C": "Catégorie C",
            "D": "Catégorie D",
            "Non fonctionnaires": "Non fonctionnaires"
        }
        
        for cat in categories_order:
            table_data.append([
                create_para_table4(category_labels[cat], is_col0=True),  # Première colonne : texte normal, aligné à gauche
                create_para_table4(format_value(effectifs_debut[cat]), is_number=True),  # Nombres en rouge, centrés
                create_para_table4(format_value(entrees[cat]), is_number=True),
                create_para_table4(format_value(sorties[cat]), is_number=True),
                create_para_table4(format_value(effectifs_fin[cat]), is_number=True),
            ])
        
        # Ligne TOTAL - créer des styles spécifiques pour TOTAL (en gras)
        total_style_col0 = ParagraphStyle(
            'TotalStyleCol0',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',  # En gras
            fontSize=10,
            leading=12,
            alignment=0,  # LEFT
        )
        total_style_number = ParagraphStyle(
            'TotalStyleNumber',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',  # En gras
            fontSize=10,
            leading=12,
            alignment=1,  # CENTER
        )
        
        # Préparer les textes pour TOTAL avec couleur rouge
        total_debut_text = format_value(total_debut)
        total_entrees_text = format_value(total_entrees)
        total_sorties_text = format_value(total_sorties)
        total_fin_text = format_value(total_fin)
        
        # Fonction helper pour formater le texte selon le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        def format_text_for_mode(text):
            """Formate le texte en rouge (brouillon) ou noir (final)"""
            if is_final:
                return str(text)
            else:
                return f'<font color="#FF0000">{text}</font>'
        
        # Mettre les nombres en rouge (ou noir en mode final)
        total_debut_text = format_text_for_mode(total_debut_text)
        total_entrees_text = format_text_for_mode(total_entrees_text)
        total_sorties_text = format_text_for_mode(total_sorties_text)
        total_fin_text = format_text_for_mode(total_fin_text)
        
        # Ligne TOTAL
        table_data.append([
            Paragraph("TOTAL", total_style_col0),  # Première colonne alignée à gauche, en gras
            Paragraph(total_debut_text, total_style_number),  # Nombres en rouge, centrés, en gras
            Paragraph(total_entrees_text, total_style_number),
            Paragraph(total_sorties_text, total_style_number),
            Paragraph(total_fin_text, total_style_number),
        ])
        
        # Créer le tableau avec LongTable (2 lignes d'en-tête)
        table = LongTable(table_data, colWidths=col_widths, repeatRows=2, splitByRow=1)
        
        # Créer le style du tableau
        table_style = [
            # Bordures
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            
            # En-tête principal (ligne 0) - utiliser la même couleur que le RAP (#bdd6ee)
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.black),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
            
            # Fusionner les cellules de la ligne 0 pour "Variation" (colonnes 2 et 3)
            ("SPAN", (2, 0), (3, 0)),  # Fusionner "Variation" sur les colonnes 2-3
            
            # Fusionner les cellules vides de la ligne 1 avec la ligne 0
            ("SPAN", (0, 1), (0, 0)),  # Fusionner colonne 0 (Catégorie) sur les 2 lignes
            ("SPAN", (1, 1), (1, 0)),  # Fusionner colonne 1 (Situation au 31/12/2023) sur les 2 lignes
            ("SPAN", (4, 1), (4, 0)),  # Fusionner colonne 4 (Situation au 30/06/2024) sur les 2 lignes
            
            # Alignement vertical uniquement (les styles de texte sont dans les Paragraphs)
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            
            # Ligne TOTAL - background et couleur uniquement (les styles sont dans les Paragraphs)
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d9e1f2")),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.black),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        
        table.setStyle(TableStyle(table_style))
        
        # Générer le graphique en barres
        chart_buffer = cls._create_bar_chart_effectifs_rprog(
            effectifs_debut, effectifs_fin, categories_order, category_labels, date_debut, date_fin
        )
        
        # Construire la story avec les titres, le tableau, le graphique et l'analyse
        from reportlab.lib.styles import ParagraphStyle
        
        story_styles = getSampleStyleSheet()
        
        # Styles pour les titres
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=story_styles['Heading1'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=dark_text_color,
            spaceAfter=12,
            alignment=0  # LEFT
        )
        
        subsection_title_style = ParagraphStyle(
            'SubsectionTitle',
            parent=story_styles['Heading2'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=dark_text_color,
            spaceAfter=10,
            alignment=0  # LEFT
        )
        
        table_title_style = ParagraphStyle(
            'TableTitle',
            parent=story_styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=dark_text_color,
            spaceAfter=6,
            alignment=0  # LEFT
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=story_styles['Normal'],
            fontSize=12,  # Taille standard pour tout le document
            fontName='Helvetica',
            textColor=dark_text_color,
            spaceAfter=8,
            alignment=4,  # JUSTIFY
            leading=15  # Leading ajusté pour fontSize=12
        )
        
        source_style = ParagraphStyle(
            'Source',
            parent=story_styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Oblique',
            textColor=colors.grey,
            spaceAfter=6,
            alignment=0  # LEFT
        )
        
        # Construire la story
        story = []
        
        # Titre de sous-section
        # Le titre "1. RÉALISATIONS À MI-PARCOURS DU PROGRAMME" n'apparaît que dans la première sous-section (1.1)
        story.append(Paragraph("1.4. Les effectifs", subsection_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Titre du tableau
        story.append(Paragraph("Tableau 4: Evolution des effectifs du programme", table_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter le tableau
        story.append(table)
        story.append(Spacer(1, 0.3 * cm))
        
        # Source du tableau
        story.append(Paragraph("Source: SOGPE", source_style))
        story.append(Spacer(1, 0.4 * cm))
        
        # Ajouter le graphique si disponible
        if chart_buffer:
            # Calculer les dimensions du graphique
            chart_width = available_width
            chart_height = 8 * cm
            
            # Créer un Flowable pour le graphique
            chart_image = FlowableImage(chart_buffer, width=chart_width, height=chart_height)
            story.append(chart_image)
            story.append(Spacer(1, 0.3 * cm))
            
            # Source du graphique
            story.append(Paragraph("Source: SOGPE", source_style))
            story.append(Spacer(1, 0.4 * cm))
        
        # Texte d'analyse
        # Fonction helper pour formater les valeurs dans le texte
        # Fonction helper pour vérifier le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        
        def format_value_text(value):
            """Retourne la valeur formatée ou '............' (brouillon) ou '' (final) si non disponible"""
            if not has_data or value is None or value == 0:
                return "" if is_final else "............"
            return str(value)
        
        def format_percentage(value, total):
            """Retourne le pourcentage formaté ou '............' (brouillon) ou '' (final) si non disponible"""
            if not has_data or total is None or total == 0 or value is None or value == 0:
                return "" if is_final else "............"
            pct = (value / total * 100)
            return f"{pct:.0f}%"
        
        def format_agent_text(value, singular="agent", plural="agents"):
            """Retourne le texte formaté avec le nombre d'agents ou '............' (brouillon) ou '' (final) si non disponible"""
            if not has_data or value is None or value == 0:
                return "" if is_final else "............"
            agent_word = singular if value == 1 else plural
            return f"{value} {agent_word}"
        
        # Calculer les pourcentages (seulement si données disponibles)
        if has_data and total_fin > 0:
            pct_a_text = format_percentage(effectifs_fin["A"], total_fin)
            pct_b_text = format_percentage(effectifs_fin["B"], total_fin)
            pct_c_text = format_percentage(effectifs_fin["C"], total_fin)
            pct_d_text = format_percentage(effectifs_fin["D"], total_fin)
            pct_non_func_text = format_percentage(effectifs_fin["Non fonctionnaires"], total_fin)
        else:
            placeholder = "" if is_final else "............"
            pct_a_text = pct_b_text = pct_c_text = pct_d_text = pct_non_func_text = placeholder
        
        total_fin_text = format_value_text(total_fin)
        total_debut_text = format_value_text(total_debut)
        evolution_text = format_value_text(total_entrees - total_sorties) if has_data else ("" if is_final else "............")
        
        # Formater la date de début pour l'affichage
        mois_fr = ["janvier", "février", "mars", "avril", "mai", "juin", 
                   "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        date_debut_formatted = f"{date_debut.day} {mois_fr[date_debut.month - 1]} {date_debut.year}"
        
        # Calculer l'évolution réelle (différence entre fin et début)
        if has_data and total_debut is not None and total_fin is not None:
            evolution_reelle = total_fin - total_debut
            evolution_absolue = abs(evolution_reelle)
            evolution_absolue_text = format_value_text(evolution_absolue)
            
            if evolution_reelle > 0:
                if is_final:
                    evolution_phrase = f"une augmentation de son effectif de <b>{evolution_absolue_text}</b> agents"
                else:
                    evolution_phrase = f"une augmentation de son effectif de <b><font color=\"#FF0000\">{evolution_absolue_text}</font></b> agents"
            elif evolution_reelle < 0:
                if is_final:
                    evolution_phrase = f"une diminution de son effectif de <b>{evolution_absolue_text}</b> agents"
                else:
                    evolution_phrase = f"une diminution de son effectif de <b><font color=\"#FF0000\">{evolution_absolue_text}</font></b> agents"
            else:
                evolution_phrase = "aucune variation de son effectif"
        else:
            if is_final:
                evolution_phrase = f"une augmentation de son effectif de <b>{evolution_text}</b> agents"
            else:
                evolution_phrase = f"une augmentation de son effectif de <b><font color=\"#FF0000\">{evolution_text}</font></b> agents"
        
        # Construire dynamiquement la liste des entrées et sorties
        entrees_list = []
        for cat in categories_order:
            if has_data and entrees.get(cat, 0) > 0:
                entrees_text = format_agent_text(entrees[cat])
                entrees_text_red = entrees_text if is_final else f"<font color=\"#FF0000\">{entrees_text}</font>"
                if cat == "Non fonctionnaires":
                    entrees_list.append(f"{entrees_text_red} non fonctionnaires")
                else:
                    entrees_list.append(f"{entrees_text_red} de la catégorie {cat}")
        
        sorties_list = []
        for cat in categories_order:
            if has_data and sorties.get(cat, 0) > 0:
                sorties_text = format_agent_text(sorties[cat])
                sorties_text_red = sorties_text if is_final else f"<font color=\"#FF0000\">{sorties_text}</font>"
                if cat == "Non fonctionnaires":
                    sorties_list.append(f"{sorties_text_red} non fonctionnaires")
                else:
                    sorties_list.append(f"{sorties_text_red} de la catégorie {cat}")
        
        # Construire la phrase des entrées
        if entrees_list:
            if len(entrees_list) == 1:
                entrees_phrase = entrees_list[0]
            elif len(entrees_list) == 2:
                entrees_phrase = f"{entrees_list[0]} et {entrees_list[1]}"
            else:
                entrees_phrase = ", ".join(entrees_list[:-1]) + f" et {entrees_list[-1]}"
        else:
            entrees_phrase = "" if is_final else "<font color=\"#FF0000\">............</font>"
        
        # Construire la phrase des sorties
        if sorties_list:
            if len(sorties_list) == 1:
                sorties_phrase = sorties_list[0]
            elif len(sorties_list) == 2:
                sorties_phrase = f"{sorties_list[0]} et {sorties_list[1]}"
            else:
                sorties_phrase = ", ".join(sorties_list[:-1]) + f" et {sorties_list[-1]}"
        else:
            sorties_phrase = "" if is_final else "<font color=\"#FF0000\">............</font>"
        
        # Construire la phrase complète de l'évolution
        if entrees_list or sorties_list:
            if entrees_list and sorties_list:
                evolution_detail_phrase = f"l'entrée de {entrees_phrase}, contre la sortie de {sorties_phrase}"
            elif entrees_list:
                evolution_detail_phrase = f"l'entrée de {entrees_phrase}"
            else:
                evolution_detail_phrase = f"la sortie de {sorties_phrase}"
        else:
            evolution_detail_phrase = "" if is_final else "<font color=\"#FF0000\">............</font>"
        
        # Fonction helper pour formater le texte selon le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        def format_text_for_mode(text):
            """Formate le texte en rouge (brouillon) ou noir (final)"""
            if is_final:
                return str(text)
            else:
                return f'<font color="#FF0000">{text}</font>'
        
        # Mettre en rouge tous les éléments dynamiques (ou noir en mode final)
        total_fin_text_red = format_text_for_mode(total_fin_text)
        pct_a_text_red = format_text_for_mode(pct_a_text)
        pct_b_text_red = format_text_for_mode(pct_b_text)
        pct_c_text_red = format_text_for_mode(pct_c_text)
        pct_d_text_red = format_text_for_mode(pct_d_text)
        pct_non_func_text_red = format_text_for_mode(pct_non_func_text)
        date_debut_formatted_red = format_text_for_mode(date_debut_formatted)
        total_debut_text_red = format_text_for_mode(total_debut_text)
        
        texte_analyse_html = f"""Le programme compte à ce jour <b>{total_fin_text_red}</b> agents dont :<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• <b>{pct_a_text_red}</b> de catégorie A<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• <b>{pct_b_text_red}</b> de catégorie B<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• <b>{pct_c_text_red}</b> de catégorie C<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• <b>{pct_d_text_red}</b> de catégorie D<br/>
&nbsp;&nbsp;&nbsp;&nbsp;• <b>{pct_non_func_text_red}</b> de non fonctionnaires<br/><br/>

Comparativement à l'effectif au {date_debut_formatted_red} (<b>{total_debut_text_red}</b> agents), le programme a connu {evolution_phrase}.<br/><br/>

Cette évolution est due à {evolution_detail_phrase}."""
        
        story.append(Paragraph(texte_analyse_html, body_style))
        
        # Ajouter les commentaires personnalisés si disponibles (ou des points si vide)
        effectifs_commentaires = data.get("effectifs_commentaires")
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        if effectifs_commentaires and effectifs_commentaires.strip():
            story.append(Spacer(1, 0.3 * cm))
            # Échapper les caractères spéciaux HTML
            commentaires_escaped = effectifs_commentaires.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convertir les retours à la ligne en <br/>
            commentaires_html = commentaires_escaped.replace("\n", "<br/>")
            # En mode final, texte en noir ; en mode brouillon, texte en rouge
            if mode == "final":
                story.append(Paragraph(commentaires_html, body_style))
            else:
                commentaires_html_red = f"<font color=\"#FF0000\">{commentaires_html}</font>"
                story.append(Paragraph(commentaires_html_red, body_style))
        else:
            story.append(Spacer(1, 0.3 * cm))
            # Afficher des points si aucun commentaire
            story.append(Paragraph("<font color=\"#FF0000\">Commentaire :..........................</font>", body_style))
        
        # Créer le SimpleDocTemplate
        logger.info(f"🔢 NUMÉROTATION - AVANT SimpleDocTemplate pour effectifs: start_page={start_page}")
        logger.info(f"📐 Dimensions: width={width:.2f}, height={height:.2f}, margins: L={left_margin:.2f}, R={right_margin:.2f}, T={top_margin:.2f}, B={bottom_margin:.2f}")
        logger.info(f"🔢 NUMÉROTATION - Story effectifs contient {len(story)} éléments")
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        # Construire le PDF avec SimpleDocTemplate
        logger.info(f"📋 Génération du PDF avec SimpleDocTemplate - {len(story)} éléments dans la story")
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        from PyPDF2 import PdfReader
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        
        logger.info(f"🔢 NUMÉROTATION - APRÈS SimpleDocTemplate pour effectifs: {num_pages} pages générées, final_page={final_page}")
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("rprog_realisations_effectifs", start_page)
        RAPPageManager.register_page_position("rprog_tableau_4", start_page)
        
        buffer.seek(0)
        return buffer, final_page
    
    @staticmethod
    def _create_bar_chart_effectifs_rprog(
        effectifs_debut: dict,
        effectifs_fin: dict,
        categories_order: list,
        category_labels: dict,
        date_debut,
        date_fin
    ) -> BytesIO | None:
        """
        Crée un graphique en barres groupées pour l'évolution des effectifs entre deux dates.
        
        Args:
            effectifs_debut: Dictionnaire des effectifs à la date de début par catégorie
            effectifs_fin: Dictionnaire des effectifs à la date de fin par catégorie
            categories_order: Ordre des catégories à afficher
            category_labels: Libellés des catégories
            date_debut: Date de début pour le calcul des effectifs (objet date)
            date_fin: Date de fin pour le calcul des effectifs (objet date)
        
        Returns:
            BytesIO contenant l'image PNG du graphique, ou None en cas d'erreur
        """
        try:
            from datetime import date
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            
            logger.info("📊 Création du graphique en barres (effectifs RPROG)...")
            
            # Préparer les données pour le graphique
            categories = [category_labels.get(cat, cat) for cat in categories_order]
            effectifs_2023 = [effectifs_debut.get(cat, 0) for cat in categories_order]
            effectifs_2024 = [effectifs_fin.get(cat, 0) for cat in categories_order]
            
            # Si pas de données, ne pas générer le graphique
            if not effectifs_2023 and not effectifs_2024:
                logger.warning("⚠️ Aucune donnée d'effectif disponible pour le graphique")
                return None
            
            # Créer la figure
            fig, ax = plt.subplots(figsize=(16, 6), dpi=200)
            
            # Position des barres
            x = np.arange(len(categories))
            width = 0.3  # Largeur des barres (réduite pour créer un espace)
            gap = 0.05  # Espace entre les deux barres
            
            # Formater les dates pour les labels
            date_debut_str = date_debut.strftime("%d/%m/%Y")
            date_fin_str = date_fin.strftime("%d/%m/%Y")
            
            # Créer les barres avec les couleurs de l'image (bleu et jaune) avec espace entre elles
            bars1 = ax.bar(x - width/2 - gap/2, effectifs_2023, width, 
                          label=f"Situation au {date_debut_str}", color='#5b9bd5')  # Bleu
            bars2 = ax.bar(x + width/2 + gap/2, effectifs_2024, width, 
                          label=f"Situation au {date_fin_str}", color='#ffc000')  # Jaune
            
            # Ajouter les valeurs sur les barres
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:  # Ne pas afficher 0
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{int(height)}',
                               ha='center', va='bottom', fontsize=18)
            
            # Configuration de l'axe Y
            max_effectif = max(max(effectifs_2023, default=0), max(effectifs_2024, default=0))
            y_max = ((max_effectif // 10) + 1) * 10 + 10  # Arrondir à la dizaine supérieure + 10 points
            ax.set_ylim(0, y_max)
            ax.set_yticks(range(0, y_max + 1, 10))
            ax.tick_params(axis='y', labelsize=16)
            
            # Configuration de l'axe X avec plus d'espace pour éviter que la légende cache les labels
            ax.set_xticks(x)
            ax.set_xticklabels(categories, fontsize=14, rotation=0, ha='center')
            ax.tick_params(axis='x', pad=20)  # Augmenter l'espace entre les labels X et l'axe
            
            # Titre du graphique (dates dynamiques)
            titre = f'EVOLUTION DES EFFECTIFS ENTRE LE {date_debut_str} ET LE {date_fin_str}'
            ax.set_title(titre, fontsize=22, pad=20)
            
            # Légende en bas sur une seule ligne (bien plus basse pour ne pas cacher les labels X)
            ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.6), ncol=2, fontsize=16, frameon=True)
            
            # Grille horizontale visible
            ax.grid(axis='y', linestyle='-', alpha=0.5, color='gray', linewidth=1)
            
            # Fond blanc
            ax.set_facecolor('white')
            fig.patch.set_facecolor('white')
            
            # Ajuster la mise en page pour inclure la légende en bas avec beaucoup d'espace
            plt.tight_layout(rect=[0, 0.35, 1, 0.95])  # Réserver beaucoup d'espace en bas pour la légende
            # Ajustement supplémentaire pour garantir l'espace
            plt.subplots_adjust(bottom=0.50)
            
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
    def draw_performance_programme(
        cls,
        pdf: canvas.Canvas = None,
        width: float = None,
        height: float = None,
        start_page: int = 1
    ) -> tuple[BytesIO, int]:
        """
        Génère la section "2. La performance du programme" avec le tableau des indicateurs et l'analyse.
        
        Utilise SimpleDocTemplate pour gérer automatiquement le découpage du LongTable sur plusieurs pages.
        
        Args:
            pdf: Le canvas PDF (optionnel, pour compatibilité)
            width: Largeur de la page (optionnel, utilise A4 landscape par défaut)
            height: Hauteur de la page (optionnel, utilise A4 landscape par défaut)
            start_page: Numéro de page de début
        
        Returns:
            Tuple (BytesIO buffer, numéro de page final) - Le buffer contient le PDF généré
        """
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import Paragraph, LongTable, TableStyle, Spacer, SimpleDocTemplate
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        from app.services.rapport_annuel_performance_generator_modular import RAPBaseGenerator, RAPPageManager
        from app.models.performance import ObjectifPerformance, IndicateurPerformance, TypeObjectif
        from app.models.personnel import Programme
        from sqlmodel import select, and_, or_
        from decimal import Decimal
        from datetime import date
        
        # Utiliser A4 landscape par défaut si width/height non fournis
        if width is None or height is None:
            width, height = landscape(A4)
        
        # Créer le buffer pour le PDF
        buffer = BytesIO()
        
        # Marges
        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
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
            logger.warning("⚠️ Pas de session DB disponible pour récupérer les données de performance")
            # Créer un PDF minimal avec SimpleDocTemplate
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=left_margin,
                rightMargin=right_margin,
                topMargin=top_margin,
                bottomMargin=bottom_margin,
            )
            
            story = []
            styles = getSampleStyleSheet()
            story.append(Paragraph("2. LA PERFORMANCE DU PROGRAMME", 
                                   ParagraphStyle('Title', parent=styles['Heading1'], 
                                                 fontName="Helvetica-Bold", fontSize=14)))
            
            def on_first_page(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            def on_later_pages(canvas, doc):
                RPROGLayoutDrawer.draw_page_header(canvas, width, height)
                page_num = canvas.getPageNumber() + start_page - 1
                RPROGLayoutDrawer.draw_page_footer(
                    canvas, page_num, width, footer_margin, footer_height, right_margin,
                    getattr(cls, '_total_pages', None)
                )
            
            doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
            buffer.seek(0)
            
            from PyPDF2 import PdfReader
            reader = PdfReader(buffer)
            num_pages = len(reader.pages)
            RAPPageManager.register_page_position("rprog_performance", start_page)
            return buffer, start_page + num_pages
        
        # Récupérer les paramètres
        programme = data.get("programme", "")
        annee = data.get("annee", 2024)
        periode = data.get("periode", "")
        
        # Déterminer la date de période pour l'affichage
        if periode:
            periode_upper = periode.upper()
            if "PREMIER" in periode_upper or "1" in periode:
                date_periode_text = f"30 juin {annee}"
            elif "DEUXIEME" in periode_upper or "2" in periode:
                date_periode_text = f"31 décembre {annee}"
            else:
                date_periode_text = periode
        else:
            date_periode_text = f"30 juin {annee}"
        
        # Récupérer les données de performance via ReportDataLoader
        from app.services.report_data_loader import ReportDataLoader
        
        programme_id = None
        if programme:
            # Trouver le programme par son nom/libelle pour obtenir son ID
            programme_db = session.exec(
                select(Programme).where(
                    or_(
                        Programme.libelle.ilike(f"%{programme}%"),
                        Programme.code.ilike(f"%{programme}%")
                    )
                )
            ).first()
            
            if programme_db:
                programme_id = programme_db.id
                logger.info(f"📊 Programme '{programme}' trouvé avec ID: {programme_id}")
            else:
                logger.warning(f"⚠️ Programme '{programme}' non trouvé dans la base de données")
        
        # Charger les données de performance via ReportDataLoader
        performance_data = {}
        objectifs_avec_indicateurs = []
        
        if programme_id:
            try:
                logger.info(f"📊 Chargement des données de performance via ReportDataLoader pour le programme ID: {programme_id}, année: {annee}")
                performance_data = ReportDataLoader.load_data_performance(
                    session,
                    annee,
                    programme_id=programme_id
                )
                
                # Extraire les objectifs avec indicateurs depuis les données chargées
                # ReportDataLoader filtre déjà par année et actif, donc utiliser directement les données
                objectifs_avec_indicateurs_raw = performance_data.get("objectifs_avec_indicateurs", [])
                
                # S'assurer que la structure est correcte (liste de dict avec "objectif" et "indicateurs")
                objectifs_avec_indicateurs = []
                for obj_data in objectifs_avec_indicateurs_raw:
                    # Vérifier la structure
                    if isinstance(obj_data, dict):
                        objectif = obj_data.get("objectif")
                        indicateurs = obj_data.get("indicateurs", [])
                        # S'assurer que indicateurs est une liste
                        if not isinstance(indicateurs, list):
                            indicateurs = list(indicateurs) if indicateurs else []
                        
                        if objectif and indicateurs:
                            logger.info(f"📊 Objectif '{objectif.code if hasattr(objectif, 'code') else 'N/A'} {objectif.titre if hasattr(objectif, 'titre') else 'N/A'}': {len(indicateurs)} indicateurs")
                            objectifs_avec_indicateurs.append({
                                "objectif": objectif,
                                "indicateurs": indicateurs
                            })
                        else:
                            logger.warning(f"⚠️ Objectif ou indicateurs manquants dans obj_data: objectif={objectif is not None}, indicateurs={len(indicateurs) if isinstance(indicateurs, list) else 'N/A'}")
                    else:
                        logger.warning(f"⚠️ obj_data n'est pas un dictionnaire: {type(obj_data)}")
                
                logger.info(f"📊 {len(objectifs_avec_indicateurs)} objectifs avec indicateurs trouvés au total via ReportDataLoader (après validation)")
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement des données de performance via ReportDataLoader: {e}", exc_info=True)
                # Fallback sur l'ancienne méthode si ReportDataLoader échoue
                logger.warning("⚠️ Fallback sur l'ancienne méthode de chargement")
                objectifs_avec_indicateurs = []
        
        # Si ReportDataLoader n'a pas fonctionné ou si programme_id est None, utiliser l'ancienne méthode
        if not objectifs_avec_indicateurs and programme_id:
            logger.warning("⚠️ Aucune donnée via ReportDataLoader, utilisation de l'ancienne méthode")
            # Récupérer les objectifs globaux liés au programme (s'ils ont un programme_id)
            objectifs_globaux_ids = []
            query_og = select(ObjectifPerformance.id).where(
                and_(
                    ObjectifPerformance.type_objectif == TypeObjectif.GLOBAL.value,
                    ObjectifPerformance.programme_id == programme_id
                )
            )
            objectifs_globaux_ids = list(session.exec(query_og).all())
            logger.info(f"📊 {len(objectifs_globaux_ids)} objectifs globaux trouvés pour le programme {programme} (ID: {programme_id})")
            
            # Récupérer les objectifs spécifiques liés à ces objectifs globaux
            query_objectifs = select(ObjectifPerformance).where(
                ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE.value
            )
            
            if objectifs_globaux_ids:
                query_objectifs = query_objectifs.where(
                    ObjectifPerformance.objectif_global_id.in_(objectifs_globaux_ids)
                )
                logger.info(f"📊 Filtrage des objectifs spécifiques par {len(objectifs_globaux_ids)} objectifs globaux")
            else:
                logger.warning(f"⚠️ Aucun objectif global trouvé pour le programme '{programme}'. Récupération de tous les objectifs spécifiques.")
            
            objectifs = session.exec(query_objectifs.order_by(ObjectifPerformance.code, ObjectifPerformance.id)).all()
            logger.info(f"📊 {len(objectifs)} objectifs spécifiques trouvés pour le programme {programme}")
            
            # Récupérer les indicateurs pour chaque objectif (filtrés par année)
            for objectif in objectifs:
                query_indicateurs = select(IndicateurPerformance).where(
                    and_(
                        IndicateurPerformance.objectif_id == objectif.id,
                        IndicateurPerformance.actif == True,
                        IndicateurPerformance.annee == annee
                    )
                ).order_by(IndicateurPerformance.id)
                
                indicateurs = session.exec(query_indicateurs).all()
                
                if indicateurs:
                    logger.info(f"📊 Objectif '{objectif.code} {objectif.titre}': {len(indicateurs)} indicateurs pour l'année {annee}")
                    objectifs_avec_indicateurs.append({
                        "objectif": objectif,
                        "indicateurs": indicateurs
                    })
                else:
                    logger.debug(f"📊 Objectif '{objectif.code} {objectif.titre}': aucun indicateur actif pour l'année {annee}")
            
            logger.info(f"📊 {len(objectifs_avec_indicateurs)} objectifs avec indicateurs trouvés au total (méthode fallback)")
        
        # Vérifier si des données sont disponibles
        has_data = len(objectifs_avec_indicateurs) > 0
        
        # Créer les styles (avant la construction de l'analyse pour pouvoir les utiliser)
        styles = getSampleStyleSheet()
        story_styles = getSampleStyleSheet()
        
        # Couleur pour le texte (doit être défini avant les styles)
        dark_text_color = colors.HexColor("#333333")
        
        # Définir body_style pour l'analyse (doit être défini avant la construction de l'analyse)
        # Style de base pour l'analyse - TAILLE STANDARD 12pt pour tout le document
        body_style = ParagraphStyle(
            'Body',
            parent=story_styles['Normal'],
            fontSize=12,  # Taille standard pour tout le document
            fontName='Helvetica',
            textColor=dark_text_color,
            spaceAfter=8,
            alignment=4,  # JUSTIFY
            leading=15  # Leading ajusté pour fontSize=12
        )
        
        # Style pour les objectifs (sans retrait supplémentaire, mais en gras)
        objectif_style = ParagraphStyle(
            'Objectif',
            parent=body_style,
            fontSize=12,  # Taille standard 12pt
            fontName='Helvetica-Bold',
            leftIndent=0,
            spaceAfter=6,
            alignment=0  # LEFT
        )
        
        # Style pour les indicateurs (avec retrait pour montrer la hiérarchie)
        indicateur_style = ParagraphStyle(
            'Indicateur',
            parent=body_style,
            fontSize=12,  # Taille standard 12pt
            fontName='Helvetica',
            leftIndent=1 * cm,  # Retrait de 1 cm pour les indicateurs
            spaceAfter=4,
            alignment=0  # LEFT
        )
        
        # Style pour les colonnes alignées à gauche (colonne 0: Indicateurs, colonne 5: Observations)
        para_style_table5_left = ParagraphStyle(
            'Table5Left',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,  # Uniformisé avec le tableau des activités
            leading=12,   # Augmenté proportionnellement
            alignment=0  # LEFT
        )
        
        # Style pour les colonnes centrées (colonnes 1-4: Unité, Réalisation, Cible, Niveau)
        para_style_table5_center = ParagraphStyle(
            'Table5Center',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,  # Uniformisé avec le tableau des activités
            leading=12,   # Augmenté proportionnellement
            alignment=1  # CENTER
        )
        
        # Style pour les lignes d'objectifs (en gras)
        para_style_table5_objectif = ParagraphStyle(
            'Table5Objectif',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,  # Uniformisé avec le tableau des activités
            leading=13,   # Augmenté proportionnellement
            alignment=0  # LEFT
        )
        
        header_style = styles['Normal']
        header_style.fontName = 'Helvetica-Bold'
        header_style.fontSize = 11  # Uniformisé avec le tableau des activités
        header_style.leading = 13   # Augmenté proportionnellement
        header_style.alignment = 1  # CENTER
        
        # Fonction helper pour créer un Paragraph avec alignement approprié
        def create_para_table5(text, is_header=False, column_index=None, is_objectif_row=False):
            """Crée un Paragraph pour le Tableau 5 - TOUJOURS retourne un Paragraph (jamais de chaîne vide)
            
            Args:
                text: Le texte à afficher
                is_header: Si True, utilise le style d'en-tête
                column_index: Index de la colonne (0=Indicateurs, 1-4=centrées, 5=Observations)
                is_objectif_row: Si True, utilise le style en gras pour les lignes d'objectifs
            """
            if text is None:
                text = ""
            text = str(text).strip()
            if not text and not is_header:
                text = " "  # Les cellules vides doivent avoir au moins un espace pour être un Paragraph valide
            if not text and is_header:
                text = " "  # Les en-têtes ne doivent pas être vides
            
            # Échapper les caractères spéciaux pour XML/HTML, mais préserver les balises HTML valides
            # D'abord échapper les & qui ne font pas partie d'une entité HTML
            text = text.replace("&", "&amp;")
            # Puis restaurer les entités HTML valides
            text = text.replace("&amp;amp;", "&amp;")
            text = text.replace("&amp;lt;", "&lt;")
            text = text.replace("&amp;gt;", "&gt;")
            text = text.replace("&amp;quot;", "&quot;")
            text = text.replace("&amp;#", "&#")
            # Échapper seulement les < et > qui ne font pas partie de balises HTML valides
            # Pour préserver les balises <font>, on doit conserver les attributs
            import re
            # Stocker les balises <font> avec leurs attributs dans un dictionnaire
            font_tags = {}
            def replace_font_open(match):
                tag_id = f"___FONT_OPEN_{len(font_tags)}___"
                font_tags[tag_id] = match.group(0)  # Conserver la balise complète avec attributs
                return tag_id
            def replace_font_close(match):
                return "___FONT_CLOSE___"
            
            # Protéger les balises <font> et </font> avec leurs attributs
            text = re.sub(r'<font[^>]*>', replace_font_open, text)
            text = re.sub(r'</font>', replace_font_close, text)
            # Échapper les autres < et >
            text = text.replace("<", "&lt;").replace(">", "&gt;")
            # Restaurer les balises <font> complètes (avec attributs) et </font>
            for tag_id, original_tag in font_tags.items():
                text = text.replace(tag_id, original_tag)
            text = text.replace("___FONT_CLOSE___", "</font>")
            # ReportLab gère automatiquement le wrapping
            
            if is_header:
                style = header_style
            elif is_objectif_row:
                # Lignes d'objectifs : utiliser le style en gras
                style = para_style_table5_objectif
            elif column_index is not None:
                # Colonne 0 (Indicateurs) ou colonne 5 (Observations) : à gauche
                # Colonnes 1-4 : centrées
                if column_index == 0 or column_index == 5:
                    style = para_style_table5_left
                else:  # colonnes 1-4
                    style = para_style_table5_center
            else:
                # Par défaut, utiliser le style gauche
                style = para_style_table5_left
            
            return Paragraph(text, style)
        
        # Fonction helper pour vérifier le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        placeholder = "" if is_final else "............"
        
        # Fonction helper pour formater le texte selon le mode
        def format_text_for_mode(text):
            """Formate le texte en rouge (brouillon) ou noir (final)"""
            if is_final:
                return str(text)
            else:
                return f'<font color="#FF0000">{text}</font>'
        
        # Fonction pour formater les valeurs
        def format_value(value):
            """Retourne la valeur formatée ou '............' (brouillon) ou '' (final) si non disponible"""
            if not has_data or value is None:
                return placeholder
            if isinstance(value, Decimal):
                if value == 0:
                    return "0"
                # Formater avec 2 décimales si nécessaire
                if value % 1 == 0:
                    return str(int(value))
                return f"{float(value):.2f}".replace(".", ",")
            return str(value)
        
        def format_percentage_value(value):
            """Retourne le pourcentage formaté ou '............' (brouillon) ou '' (final) si non disponible"""
            if not has_data or value is None:
                return placeholder
            if isinstance(value, Decimal):
                if value == 0:
                    return "0"
                return f"{float(value):.2f}".replace(".", ",")
            return str(value)
        
        # Calculer les largeurs des colonnes
        col_widths = [
            available_width * 0.35,  # Indicateurs de performance
            available_width * 0.08,  # Unité
            available_width * 0.12,  # Réalisation 2022
            available_width * 0.12,  # Cible
            available_width * 0.15,  # Niveau de réalisation
            available_width * 0.18,  # Observations
        ]
        
        # Fonction helper pour vérifier le mode
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        is_final = mode == "final"
        
        # Fonction helper pour formater le texte selon le mode
        def format_text_for_mode(text):
            """Formate le texte en rouge (brouillon) ou noir (final)"""
            if is_final:
                return str(text)
            else:
                return f'<font color="#FF0000">{text}</font>'
        
        # Construire les données du tableau
        table_data = []
        
        # Ligne d'en-tête
        date_periode_text_red = format_text_for_mode(date_periode_text)
        table_data.append([
            create_para_table5("Indicateurs de performance", is_header=True, column_index=0),
            create_para_table5("Unité", is_header=True, column_index=1),
            create_para_table5("Réalisation 2022", is_header=True, column_index=2),
            create_para_table5("Cible", is_header=True, column_index=3),
            create_para_table5(f"Niveau de réalisation au {date_periode_text_red}", is_header=True, column_index=4),
            create_para_table5("Observations", is_header=True, column_index=5),
        ])
        
        # Fonction pour déterminer si la cible est atteinte
        def is_cible_atteinte(valeur_actuelle, valeur_cible):
            """Détermine si la cible est atteinte"""
            if not has_data or valeur_actuelle is None or valeur_cible is None:
                return None
            if isinstance(valeur_actuelle, Decimal) and isinstance(valeur_cible, Decimal):
                return valeur_actuelle >= valeur_cible
            try:
                return float(valeur_actuelle) >= float(valeur_cible)
            except (ValueError, TypeError):
                return None
        
        # Parcourir les objectifs et leurs indicateurs
        logger.info(f"🔍 DÉBUT construction tableau: {len(objectifs_avec_indicateurs)} objectifs à traiter")
        for obj_idx, obj_data in enumerate(objectifs_avec_indicateurs, 1):
            objectif = obj_data.get("objectif") if isinstance(obj_data, dict) else obj_data["objectif"]
            indicateurs = obj_data.get("indicateurs", []) if isinstance(obj_data, dict) else obj_data["indicateurs"]
            
            # S'assurer que indicateurs est itérable
            if not isinstance(indicateurs, list):
                indicateurs = list(indicateurs) if indicateurs else []
            
            logger.info(f"🔍 Objectif {obj_idx}: code={objectif.code if hasattr(objectif, 'code') else 'N/A'}, titre={objectif.titre[:50] if hasattr(objectif, 'titre') and objectif.titre else 'N/A'}, {len(indicateurs)} indicateurs")
            
            # Ligne d'en-tête de groupe (objectif) - Format : "Objectif spécifique 1 : {titre}"
            objectif_numero = obj_idx
            objectif_titre = objectif.titre if hasattr(objectif, 'titre') and objectif.titre else ""
            objectif_titre_red = format_text_for_mode(objectif_titre)
            objectif_text = f"Objectif spécifique {objectif_numero} : {objectif_titre_red}"
            
            logger.info(f"🔍 Ajout ligne objectif {obj_idx}: '{objectif_text[:50]}'")
            # Pour les lignes d'objectifs fusionnées, seule la première colonne doit avoir du contenu
            # Les autres colonnes seront fusionnées avec SPAN, donc on utilise des chaînes vides
            # (comme dans le tableau des activités) qui seront converties en Paragraphs plus tard
            table_data.append([
                create_para_table5(objectif_text, column_index=0, is_objectif_row=True),
                "",  # Chaîne vide pour fusion (sera convertie plus tard)
                "",  # Chaîne vide pour fusion
                "",  # Chaîne vide pour fusion
                "",  # Chaîne vide pour fusion
                "",  # Chaîne vide pour fusion
            ])
            
            # Lignes d'indicateurs
            logger.info(f"🔍 Ajout de {len(indicateurs)} lignes d'indicateurs pour objectif {obj_idx}")
            for indicateur_idx, indicateur in enumerate(indicateurs, 1):
                logger.info(f"🔍   Indicateur {indicateur_idx}/{len(indicateurs)}: {indicateur.nom[:50] if hasattr(indicateur, 'nom') and indicateur.nom else 'N/A'}")
                # Récupérer la réalisation 2022 (année N-2)
                annee_2022 = annee - 2
                realisation_2022 = None
                
                # Chercher l'indicateur pour 2022
                query_ind_2022 = select(IndicateurPerformance).where(
                    IndicateurPerformance.objectif_id == objectif.id,
                    IndicateurPerformance.nom == indicateur.nom,
                    IndicateurPerformance.annee == annee_2022
                )
                ind_2022 = session.exec(query_ind_2022).first()
                if ind_2022:
                    realisation_2022 = ind_2022.valeur_actuelle
                
                # Récupérer les valeurs actuelles
                valeur_cible = indicateur.valeur_cible
                valeur_actuelle = indicateur.valeur_actuelle
                
                # Déterminer les observations
                cible_atteinte = is_cible_atteinte(valeur_actuelle, valeur_cible)
                if cible_atteinte is None:
                    observations_text = placeholder
                elif cible_atteinte:
                    observations_text = "Cible atteinte"
                else:
                    observations_text = "Cible non atteinte"
                
                # Formater les valeurs selon l'unité
                unite = indicateur.unite or ""
                if unite.lower() in ["%", "pourcentage"]:
                    realisation_2022_text = format_percentage_value(realisation_2022)
                    cible_text = format_percentage_value(valeur_cible)
                    niveau_text = format_percentage_value(valeur_actuelle)
                else:
                    realisation_2022_text = format_value(realisation_2022)
                    cible_text = format_value(valeur_cible)
                    niveau_text = format_value(valeur_actuelle)
                
                # Mettre en rouge tous les éléments dynamiques (ou noir en mode final)
                indicateur_nom_red = format_text_for_mode(indicateur.nom)
                unite_red = format_text_for_mode(unite or placeholder)
                realisation_2022_text_red = format_text_for_mode(realisation_2022_text)
                cible_text_red = format_text_for_mode(cible_text)
                niveau_text_red = format_text_for_mode(niveau_text)
                observations_text_red = format_text_for_mode(observations_text)
                
                # Ligne d'indicateur
                logger.info(f"🔍     Ajout ligne indicateur: nom='{indicateur.nom[:30] if hasattr(indicateur, 'nom') else 'N/A'}', unite='{unite}', realisation_2022='{realisation_2022_text[:20]}', cible='{cible_text[:20]}', niveau='{niveau_text[:20]}', observations='{observations_text[:20]}'")
                table_data.append([
                    create_para_table5(indicateur_nom_red, column_index=0),
                    create_para_table5(unite_red, column_index=1),
                    create_para_table5(realisation_2022_text_red, column_index=2),
                    create_para_table5(cible_text_red, column_index=3),
                    create_para_table5(niveau_text_red, column_index=4),
                    create_para_table5(observations_text_red, column_index=5),
                ])
        
        logger.info(f"🔍 FIN construction tableau: {len(table_data)} lignes au total (en-tête + objectifs + indicateurs)")
        
        # Si aucune donnée trouvée
        if not has_data:
            # Ajouter une ligne avec le message (fusionné sur toutes les colonnes)
            # Utiliser une chaîne vide pour les colonnes vides, comme dans le tableau des investissements
            message_text = "Aucun indicateur de performance enregistré pour cette période."
            table_data.append([
                create_para_table5(message_text, column_index=0),
                "",  # Colonnes vides avec chaînes vides (pas de Paragraph)
                "",
                "",
                "",
                "",
            ])
        
        # Vérifier que le tableau a au moins les en-têtes
        logger.info(f"📊 Tableau de performance: {len(table_data)} lignes dans table_data (en-têtes inclus)")
        if len(table_data) < 2:
            logger.warning("⚠️ Le tableau de performance n'a pas assez de lignes. Ajout d'une ligne vide.")
            table_data.append([
                "",  # Utiliser chaînes vides pour les lignes complètement vides
                "",
                "",
                "",
                "",
                ""
            ])
        
        # Vérifier les dimensions avant création
        logger.info(f"📊 Tableau de performance: {len(table_data)} lignes")
        logger.info(f"📊 Largeur disponible: {available_width:.2f}")
        logger.info(f"📊 Largeurs colonnes: {[f'{w:.2f}' for w in col_widths]}")
        logger.info(f"📊 Somme largeurs colonnes: {sum(col_widths):.2f}")
        logger.info(f"📊 Différence: {(available_width - sum(col_widths)):.2f}")
        
        # S'assurer que la somme des largeurs ne dépasse pas la largeur disponible
        total_col_widths = sum(col_widths)
        if total_col_widths > available_width:
            logger.warning(f"⚠️ Les largeurs de colonnes ({total_col_widths:.2f}) dépassent la largeur disponible ({available_width:.2f})")
            # Ajuster proportionnellement
            scale_factor = available_width / total_col_widths
            col_widths = [w * scale_factor for w in col_widths]
            logger.info(f"📊 Largeurs ajustées: {[f'{w:.2f}' for w in col_widths]}, Somme: {sum(col_widths):.2f}")
        
        # Convertir toutes les chaînes vides en Paragraphs pour LongTable
        # LongTable préfère que toutes les cellules soient des Flowables
        # Même pour les colonnes fusionnées, on doit convertir en Paragraph (comme dans le tableau des activités)
        logger.info(f"🔄 Conversion des chaînes vides en Paragraphs (comme dans le tableau des activités)")
        converted_count = 0
        for row_idx, row in enumerate(table_data):
            for col_idx, cell in enumerate(row):
                if isinstance(cell, str) and not cell:
                    # Convertir les chaînes vides en Paragraphs avec un espace
                    # Utiliser le style approprié selon la colonne
                    table_data[row_idx][col_idx] = create_para_table5(" ", column_index=col_idx)
                    converted_count += 1
        logger.info(f"✅ Conversion terminée - {converted_count} cellules converties, {len(table_data)} lignes totales")
        logger.info(f"📊 Structure: 1 en-tête + {len(objectifs_avec_indicateurs)} objectifs + leurs indicateurs")
        
        # Vérification finale de la structure du tableau avant création
        logger.info(f"📊 VÉRIFICATION FINALE - Structure du tableau avant création:")
        logger.info(f"   - Total lignes: {len(table_data)}")
        logger.info(f"   - Ligne 0 (en-tête): {len(table_data[0]) if table_data else 0} colonnes")
        if len(table_data) > 1:
            logger.info(f"   - Ligne 1 (première ligne de données): {len(table_data[1]) if len(table_data) > 1 else 0} colonnes")
            logger.info(f"   - Type ligne 1, colonne 0: {type(table_data[1][0]) if len(table_data) > 1 and len(table_data[1]) > 0 else 'N/A'}")
        # Compter les lignes d'objectifs et d'indicateurs
        expected_rows = 1  # En-tête
        for obj_data in objectifs_avec_indicateurs:
            expected_rows += 1  # Ligne d'objectif
            expected_rows += len(obj_data.get("indicateurs", []))  # Lignes d'indicateurs
        logger.info(f"   - Lignes attendues: {expected_rows} (1 en-tête + objectifs + indicateurs)")
        logger.info(f"   - Lignes réelles: {len(table_data)}")
        
        # Créer le tableau avec LongTable
        try:
            logger.info(f"📊 Création du LongTable: {len(table_data)} lignes, {len(col_widths)} colonnes")
            logger.info(f"📊 Type du premier élément: {type(table_data[0][0]) if table_data else 'N/A'}")
            table = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
            logger.info(f"✅ Tableau de performance créé avec succès: {len(table_data)} lignes, {len(col_widths)} colonnes")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la création du tableau de performance: {e}", exc_info=True)
            # Créer un tableau minimal en cas d'erreur
            table_data_minimal = [
                [create_para_table5("Indicateurs de performance", is_header=True, column_index=0),
                 create_para_table5("Unité", is_header=True, column_index=1),
                 create_para_table5("Réalisation 2022", is_header=True, column_index=2),
                 create_para_table5("Cible", is_header=True, column_index=3),
                 create_para_table5(f"Niveau de réalisation au {date_periode_text}", is_header=True, column_index=4),
                 create_para_table5("Observations", is_header=True, column_index=5)],
                [create_para_table5("Aucun indicateur de performance enregistré pour cette période.", column_index=0),
                 create_para_table5(" ", column_index=1),
                 create_para_table5(" ", column_index=2),
                 create_para_table5(" ", column_index=3),
                 create_para_table5(" ", column_index=4),
                 create_para_table5(" ", column_index=5)]
            ]
            table = LongTable(table_data_minimal, colWidths=col_widths, repeatRows=1, splitByRow=1)
        
        # Créer le style du tableau
        table_style = [
            # Bordures
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            
            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            
            # Alignement par défaut (sera surchargé par les règles spécifiques pour les indicateurs)
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),  # Par défaut, tout à gauche
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        
        # Ajouter les styles pour les lignes d'en-tête de groupe (objectifs)
        current_row = 1  # Commence après l'en-tête
        logger.info(f"🎨 Application des styles: {len(objectifs_avec_indicateurs)} objectifs à styliser")
        for obj_idx, obj_data in enumerate(objectifs_avec_indicateurs, 1):
            indicateurs = obj_data["indicateurs"]
            num_indicateurs = len(indicateurs)
            logger.info(f"🎨 Objectif {obj_idx}: ligne {current_row}, {num_indicateurs} indicateurs à partir de la ligne {current_row + 1}")
            
            # Ligne d'en-tête de groupe (objectif) - Fusionner toutes les colonnes
            table_style.append(("SPAN", (0, current_row), (-1, current_row)))  # Fusionner toutes les colonnes
            table_style.append(("BACKGROUND", (0, current_row), (-1, current_row), colors.HexColor("#D3D3D3")))  # Fond gris foncé pour toute la ligne
            table_style.append(("FONTNAME", (0, current_row), (-1, current_row), "Helvetica-Bold"))  # Police en gras pour toute la ligne fusionnée
            table_style.append(("FONTSIZE", (0, current_row), (-1, current_row), 11))  # Taille uniformisée pour toute la ligne fusionnée
            table_style.append(("ALIGN", (0, current_row), (-1, current_row), "LEFT"))  # Aligner toute la ligne fusionnée à gauche
            current_row += 1
            
            # Lignes d'indicateurs - S'assurer qu'elles ne sont pas en gras et appliquer les alignements
            if num_indicateurs > 0:
                logger.info(f"🎨   Styles pour indicateurs: lignes {current_row} à {current_row + num_indicateurs - 1}")
                # Appliquer explicitement la police normale pour les lignes d'indicateurs
                table_style.append(("FONTNAME", (0, current_row), (-1, current_row + num_indicateurs - 1), "Helvetica"))
                table_style.append(("FONTSIZE", (0, current_row), (-1, current_row + num_indicateurs - 1), 10))  # Uniformisé avec le tableau des activités
                # Réappliquer les alignements pour les lignes d'indicateurs (après les styles de police)
                table_style.append(("ALIGN", (0, current_row), (0, current_row + num_indicateurs - 1), "LEFT"))  # Première colonne à gauche
                table_style.append(("ALIGN", (1, current_row), (4, current_row + num_indicateurs - 1), "CENTER"))  # Colonnes 1-4 centrées
                table_style.append(("ALIGN", (5, current_row), (5, current_row + num_indicateurs - 1), "LEFT"))  # Dernière colonne à gauche
            current_row += num_indicateurs
        logger.info(f"🎨 Styles appliqués: {len(table_style)} règles, dernière ligne stylisée: {current_row - 1}")
        
        # Si aucune donnée, fusionner toutes les colonnes du message
        if not has_data:
            table_style.append(("SPAN", (0, 1), (-1, 1)))
            table_style.append(("ALIGN", (0, 1), (-1, 1), "CENTER"))
        
        table.setStyle(TableStyle(table_style))
        
        # Construire l'analyse détaillée (seulement si des données sont disponibles)
        # Diviser l'analyse en plusieurs paragraphes pour permettre le rendu multi-pages
        analyse_paragraphs = []
        if has_data and len(objectifs_avec_indicateurs) > 0:
            # Paragraphe d'introduction
            analyse_paragraphs.append(Paragraph("<b>L'analyse des résultats se présente comme suit:</b>", body_style))
            analyse_paragraphs.append(Spacer(1, 0.3 * cm))
            
            # Fonction helper pour vérifier le mode (définie une fois avant la boucle)
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
            is_final = mode == "final"
            placeholder_analyse = "" if is_final else "............"
            
            # Fonction helper pour formater le texte selon le mode
            def format_text_for_mode(text):
                """Formate le texte en rouge (brouillon) ou noir (final)"""
                if is_final:
                    return str(text)
                else:
                    return f'<font color="#FF0000">{text}</font>'
            
            for obj_idx, obj_data in enumerate(objectifs_avec_indicateurs, 1):
                objectif = obj_data["objectif"]
                indicateurs = obj_data["indicateurs"]
                
                objectif_numero = obj_idx
                objectif_titre = objectif.titre if objectif.titre else ""
                objectif_titre_red = format_text_for_mode(objectif_titre)
                objectif_text = f"Objectif spécifique {objectif_numero} : {objectif_titre_red}"
                
                # Paragraphe pour l'objectif (avec style spécial, pas besoin de <b> car déjà en gras dans le style)
                analyse_paragraphs.append(Paragraph(objectif_text, objectif_style))
                analyse_paragraphs.append(Spacer(1, 0.15 * cm))
                
                for idx, indicateur in enumerate(indicateurs, 1):
                    # Récupérer la réalisation 2022
                    annee_2022 = annee - 2
                    query_ind_2022 = select(IndicateurPerformance).where(
                        IndicateurPerformance.objectif_id == objectif.id,
                        IndicateurPerformance.nom == indicateur.nom,
                        IndicateurPerformance.annee == annee_2022
                    )
                    ind_2022 = session.exec(query_ind_2022).first()
                    situation_ref = format_percentage_value(ind_2022.valeur_actuelle) if ind_2022 and ind_2022.valeur_actuelle else placeholder_analyse
                    situation_ref_red = format_text_for_mode(situation_ref)
                    
                    # Formater les valeurs cibles futures
                    if indicateur.valeurs_cibles_futures:
                        valeurs_cibles_text = format_text_for_mode(indicateur.valeurs_cibles_futures)
                    elif indicateur.cible_N_plus_1 or indicateur.cible_N_plus_2:
                        cibles = []
                        if indicateur.cible_N_plus_1:
                            cible_n1 = f"{format_percentage_value(indicateur.cible_N_plus_1)}% en {annee + 1}"
                            cibles.append(format_text_for_mode(cible_n1))
                        if indicateur.cible_N_plus_2:
                            cible_n2 = f"{format_percentage_value(indicateur.cible_N_plus_2)}% en {annee + 2}"
                            cibles.append(format_text_for_mode(cible_n2))
                        valeurs_cibles_text = "; ".join(cibles) if cibles else format_text_for_mode(placeholder_analyse)
                    else:
                        valeurs_cibles_text = format_text_for_mode(placeholder_analyse)
                    
                    # Formater la valeur actuelle pour l'analyse
                    valeur_actuelle_text = format_percentage_value(indicateur.valeur_actuelle) if indicateur.valeur_actuelle else placeholder_analyse
                    
                    # Mettre en rouge tous les éléments dynamiques (ou noir en mode final)
                    indicateur_nom_red = format_text_for_mode(indicateur.nom)
                    source_donnees_red = format_text_for_mode(indicateur.source_donnees or placeholder_analyse)
                    unite_text = indicateur.unite or ''
                    unite_red = format_text_for_mode(unite_text) if unite_text else ""
                    annee_2022_red = format_text_for_mode(annee_2022)
                    formule_calcul_red = format_text_for_mode(indicateur.formule_calcul or indicateur.methode or placeholder_analyse)
                    commentaires_red = format_text_for_mode(indicateur.commentaires or placeholder_analyse)
                    
                    # Construire la ligne de situation de référence avec gestion de l'unité vide
                    if unite_text:
                        situation_ref_line = f"{situation_ref_red}{unite_red} en {annee_2022_red}"
                    else:
                        situation_ref_line = f"{situation_ref_red} en {annee_2022_red}"
                    
                    # Paragraphe pour chaque indicateur (avec retrait)
                    # Ajouter une légère indentation supplémentaire pour les lignes détaillées
                    indicateur_html = (
                        f"<b>- Indicateur {idx}: {indicateur_nom_red}</b><br/>"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<b>. Source de données</b>: {source_donnees_red}<br/>"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<b>. Situation de référence</b>: {situation_ref_line}<br/>"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<b>. Mode de calcul</b>: {formule_calcul_red}<br/>"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<b>. Valeurs cibles</b>: {valeurs_cibles_text}<br/>"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;<b>. Analyse de l'indicateur</b>: {commentaires_red}"
                    )
                    analyse_paragraphs.append(Paragraph(indicateur_html, indicateur_style))
                    analyse_paragraphs.append(Spacer(1, 0.15 * cm))
            
            logger.info(f"📊 Analyse construite: {len(analyse_paragraphs)} paragraphes")
        else:
            logger.warning(f"⚠️ Analyse non construite: has_data={has_data}, objectifs_avec_indicateurs={len(objectifs_avec_indicateurs) if 'objectifs_avec_indicateurs' in locals() else 'N/A'}")
        
        # Construire la story
        # Note: story_styles et body_style sont déjà définis plus haut
        
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=story_styles['Heading1'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=dark_text_color,
            spaceAfter=12,
            alignment=0  # LEFT
        )
        
        table_title_style = ParagraphStyle(
            'TableTitle',
            parent=story_styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=dark_text_color,
            spaceAfter=6,
            alignment=0  # LEFT
        )
        
        source_style = ParagraphStyle(
            'Source',
            parent=story_styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Oblique',
            textColor=colors.grey,
            spaceAfter=6,
            alignment=0  # LEFT
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=story_styles['Normal'],
            fontSize=12,  # Taille standard pour tout le document
            fontName='Helvetica',
            textColor=dark_text_color,
            spaceAfter=8,
            alignment=4,  # JUSTIFY
            leading=15  # Leading ajusté pour fontSize=12
        )
        
        story = []
        
        # Titre de section
        story.append(Paragraph("2. LA PERFORMANCE DU PROGRAMME", section_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Titre du tableau
        tableau_num = cls.get_next_tableau_numero()
        story.append(Paragraph(f"Tableau {tableau_num}: Evolution des indicateurs du programme", table_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter le tableau (toujours affiché, même sans données - avec les en-têtes)
        logger.info(f"📊 Ajout du tableau de performance à la story: {len(table_data)} lignes")
        logger.info(f"📊 Type du tableau: {type(table)}")
        logger.info(f"📊 Tableau a {len(story)} éléments avant l'ajout du tableau")
        story.append(table)
        logger.info(f"✅ Tableau de performance ajouté à la story avec succès. Story contient maintenant {len(story)} éléments")
        story.append(Spacer(1, 0.3 * cm))
        
        # Source (toujours affichée, comme dans la table des investissements)
        story.append(Paragraph("Source: Système de suivi de la performance", source_style))
        story.append(Spacer(1, 0.4 * cm))
        
        # Ajouter l'analyse (seulement si des données sont disponibles)
        logger.info(f"📊 Vérification analyse: {len(analyse_paragraphs)} paragraphes, has_data={has_data}")
        if analyse_paragraphs:
            logger.info(f"📊 Ajout de l'analyse à la story ({len(analyse_paragraphs)} paragraphes)")
            try:
                # Ajouter tous les paragraphes de l'analyse à la story
                story.extend(analyse_paragraphs)
                logger.info(f"✅ Analyse ajoutée avec succès. Story contient maintenant {len(story)} éléments")
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'ajout de l'analyse à la story: {e}", exc_info=True)
        else:
            logger.warning(f"⚠️ Analyse non ajoutée: aucun paragraphe (has_data={has_data}, objectifs_avec_indicateurs={len(objectifs_avec_indicateurs)})")
        
        # Ajouter les commentaires personnalisés si disponibles (ou des points si vide)
        performance_commentaires = data.get("performance_commentaires")
        mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
        if performance_commentaires and performance_commentaires.strip():
            story.append(Spacer(1, 0.3 * cm))
            # Échapper les caractères spéciaux HTML
            commentaires_escaped = performance_commentaires.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convertir les retours à la ligne en <br/>
            commentaires_html = commentaires_escaped.replace("\n", "<br/>")
            # En mode final, texte en noir ; en mode brouillon, texte en rouge
            if mode == "final":
                story.append(Paragraph(commentaires_html, body_style))
            else:
                commentaires_html_red = f"<font color=\"#FF0000\">{commentaires_html}</font>"
                story.append(Paragraph(commentaires_html_red, body_style))
        else:
            story.append(Spacer(1, 0.3 * cm))
            # Afficher des points si aucun commentaire
            story.append(Paragraph("<font color=\"#FF0000\">Commentaire :..........................</font>", body_style))
        
        # Créer le SimpleDocTemplate
        logger.info(f"🔢 NUMÉROTATION - AVANT SimpleDocTemplate pour performance: start_page={start_page}")
        logger.info(f"📐 Dimensions: width={width:.2f}, height={height:.2f}, margins: L={left_margin:.2f}, R={right_margin:.2f}, T={top_margin:.2f}, B={bottom_margin:.2f}")
        logger.info(f"🔢 NUMÉROTATION - Story performance contient {len(story)} éléments")
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        
        # Fonctions de callback pour header/footer
        def on_first_page(canvas, doc):
            """Callback pour la première page"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        def on_later_pages(canvas, doc):
            """Callback pour les pages suivantes"""
            RPROGLayoutDrawer.draw_page_header(canvas, width, height)
            page_num = canvas.getPageNumber() + start_page - 1
            RPROGLayoutDrawer.draw_page_footer(
                canvas, page_num, width, footer_margin, footer_height, right_margin,
                getattr(cls, '_total_pages', None)
            )
        
        # Construire le PDF avec SimpleDocTemplate
        logger.info(f"📋 Génération du PDF avec SimpleDocTemplate - {len(story)} éléments dans la story")
        doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        
        # Calculer le nombre de pages générées
        buffer.seek(0)
        from PyPDF2 import PdfReader
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)
        final_page = start_page + num_pages
        
        logger.info(f"🔢 NUMÉROTATION - APRÈS SimpleDocTemplate pour performance: {num_pages} pages générées, final_page={final_page}")
        
        # Enregistrer les positions
        RAPPageManager.register_page_position("rprog_performance", start_page)
        RAPPageManager.register_page_position("rprog_tableau_5", start_page)
        
        buffer.seek(0)
        return buffer, final_page
    
    @classmethod
    def draw_difficultes_solutions(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la section "3. Difficultés et Solutions" avec deux sous-sections :
        - 3.1. Difficultés rencontrées
        - 3.2. Actions mises en œuvre ou solutions envisagées
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après cette section
        """
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPBaseGenerator, RAPPageManager
        
        # Marges (alignées avec la section Performance)
        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin
        
        # Dessiner l'en-tête
        RPROGLayoutDrawer.draw_page_header(pdf, width, height)
        
        # Créer les styles pour les paragraphes
        styles = getSampleStyleSheet()
        
        # Style pour le titre principal "3. Difficultés et Solutions"
        title_style = ParagraphStyle(
            "DifficultesTitle",
            parent=styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=0,  # LEFT
            spaceAfter=20,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Style pour les sous-titres (3.1, 3.2)
        subtitle_style = ParagraphStyle(
            "DifficultesSubtitle",
            parent=styles['Heading2'],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,  # LEFT
            spaceAfter=12,
            spaceBefore=15,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Style pour le texte du corps
        body_style = ParagraphStyle(
            "DifficultesBody",
            parent=styles['Normal'],
            fontName="Helvetica",
            fontSize=12,  # Taille standard pour tout le document
            leading=15,  # Leading ajusté pour fontSize=12
            alignment=4,  # JUSTIFY
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Style pour les listes à puces (avec espacement réduit)
        list_item_style = ParagraphStyle(
            "DifficultesListItem",
            parent=body_style,
            spaceAfter=4,  # Espacement réduit entre les éléments de liste
        )
        
        # Récupérer les données
        data = cls.data if hasattr(cls, 'data') and cls.data else {}
        
        # Récupérer les difficultés rencontrées (liste de chaînes ou texte)
        difficultes_rencontrees = data.get("difficultes_rencontrees", [])
        if isinstance(difficultes_rencontrees, str):
            # Si c'est une chaîne, la convertir en liste en séparant par les retours à la ligne
            difficultes_rencontrees = [d.strip() for d in difficultes_rencontrees.split('\n') if d.strip()]
        elif not isinstance(difficultes_rencontrees, list):
            difficultes_rencontrees = []
        
        # Récupérer les actions/solutions (liste de chaînes ou texte)
        actions_solutions = data.get("actions_solutions", [])
        if isinstance(actions_solutions, str):
            # Si c'est une chaîne, la convertir en liste en séparant par les retours à la ligne
            actions_solutions = [a.strip() for a in actions_solutions.split('\n') if a.strip()]
        elif not isinstance(actions_solutions, list):
            actions_solutions = []
        
        # Ne plus utiliser de données par défaut - afficher des points si aucune donnée n'est fournie
        
        # Construire la story
        story = []
        
        # Ajouter le titre principal "3. Difficultés et Solutions"
        story.append(Paragraph("3. Difficultés et Solutions", title_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # ===== Sous-section 3.1. Difficultés rencontrées =====
        story.append(Paragraph("3.1. Difficultés rencontrées", subtitle_style))
        
        # Texte d'introduction pour les difficultés (personnalisable)
        intro_difficultes = data.get("difficultes_intro", "Les difficultés rencontrées sont :")
        if not intro_difficultes or not intro_difficultes.strip():
            intro_difficultes = "Les difficultés rencontrées sont :"
        story.append(Paragraph(intro_difficultes, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter les difficultés comme liste à puces (puces et texte en rouge)
        if difficultes_rencontrees:
            for difficulte in difficultes_rencontrees:
                # Échapper les caractères spéciaux pour HTML/XML
                difficulte_escaped = difficulte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                # Formater comme une liste à puce avec la puce et le texte en rouge (ou noir en mode final)
                mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
                if mode == "final":
                    difficulte_html = f"&nbsp;&nbsp;&nbsp;&nbsp;• {difficulte_escaped}"
                else:
                    difficulte_html = f"&nbsp;&nbsp;&nbsp;&nbsp;<font color=\"#FF0000\">•</font> <font color=\"#FF0000\">{difficulte_escaped}</font>"
                story.append(Paragraph(difficulte_html, list_item_style))
        else:
            # En mode final, ne pas afficher le placeholder
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
            if mode != "final":
                story.append(Paragraph("<font color=\"#FF0000\">Commentaire :..........................</font>", body_style))
        
        story.append(Spacer(1, 0.2 * cm))
        
        # ===== Sous-section 3.2. Actions mises en œuvre ou solutions envisagées =====
        story.append(Paragraph("3.2. Actions mises en œuvre ou solutions envisagées", subtitle_style))
        
        # Texte d'introduction pour les actions/solutions (personnalisable)
        intro_actions = data.get("solutions_intro", "En matière de gestion du Portefeuille de l'Etat, les actions suivantes ont été menées sous l'impulsion du Ministre en charge du Portefeuille de l'Etat :")
        if not intro_actions or not intro_actions.strip():
            intro_actions = "En matière de gestion du Portefeuille de l'Etat, les actions suivantes ont été menées sous l'impulsion du Ministre en charge du Portefeuille de l'Etat :"
        story.append(Paragraph(intro_actions, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter les actions/solutions comme liste à puces (puces et texte en rouge)
        if actions_solutions:
            for action in actions_solutions:
                # Échapper les caractères spéciaux pour HTML/XML
                action_escaped = action.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                # Formater comme une liste à puce avec la puce et le texte en rouge (ou noir en mode final)
                mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
                if mode == "final":
                    action_html = f"&nbsp;&nbsp;&nbsp;&nbsp;• {action_escaped}"
                else:
                    action_html = f"&nbsp;&nbsp;&nbsp;&nbsp;<font color=\"#FF0000\">•</font> <font color=\"#FF0000\">{action_escaped}</font>"
                story.append(Paragraph(action_html, list_item_style))
        else:
            # En mode final, ne pas afficher le placeholder
            mode = cls.data.get("mode", "brouillon") if hasattr(cls, 'data') and cls.data else "brouillon"
            if mode != "final":
                story.append(Paragraph("<font color=\"#FF0000\">Commentaire :..........................</font>", body_style))
        
        # Fonction pour dessiner le footer
        def draw_footer(page_num: int):
            """Dessine le footer pour chaque page"""
            RPROGLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_num,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin,
                total_pages=getattr(cls, '_total_pages', None)
            )
        
        # Rendre la story avec pagination automatique
        logger.info(f"🔢 NUMÉROTATION - AVANT _render_multipage_story pour difficultes_solutions: start_page={start_page}")
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
        logger.info(f"🔢 NUMÉROTATION - APRÈS _render_multipage_story pour difficultes_solutions: final_page={final_page}")
        
        # Enregistrer les positions des pages
        RAPPageManager.register_page_position("rprog_difficultes", start_page)
        RAPPageManager.register_page_position("rprog_difficultes_rencontrees", start_page)
        RAPPageManager.register_page_position("rprog_difficultes_solutions", start_page)
        
        return final_page
    
    @classmethod
    def draw_conclusion(
        cls,
        pdf: canvas.Canvas,
        width: float,
        height: float,
        start_page: int
    ) -> int:
        """
        Dessine la section "CONCLUSION" du rapport RPROG.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page
            height: Hauteur de la page
            start_page: Numéro de page de début
        
        Returns:
            Le numéro de la page suivante après cette section
        """
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from app.services.rapport_annuel_performance_generator_modular import RAPLayoutDrawer, RAPBaseGenerator, RAPPageManager
        
        # Marges (alignées avec la section Performance)
        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
        footer_height = 2 * cm
        footer_margin = 0.8 * cm
        bottom_margin = footer_height + footer_margin
        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin
        
        # Dessiner l'en-tête
        RPROGLayoutDrawer.draw_page_header(pdf, width, height)
        
        # Créer les styles pour les paragraphes
        styles = getSampleStyleSheet()
        
        # Style pour le titre "CONCLUSION"
        title_style = ParagraphStyle(
            "ConclusionTitle",
            parent=styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,  # CENTER
            spaceAfter=20,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Style pour le texte du corps
        body_style = ParagraphStyle(
            "ConclusionBody",
            parent=styles['Normal'],
            fontName="Helvetica",
            fontSize=12,  # Taille standard pour tout le document
            leading=15,  # Leading ajusté pour fontSize=12
            alignment=4,  # JUSTIFY
            spaceAfter=12,
            textColor=RAPBaseGenerator.DARK_TEXT
        )
        
        # Récupérer les données
        data = cls.data if hasattr(cls, 'data') and cls.data else {}
        
        # Récupérer le texte de conclusion
        conclusion_text = data.get("conclusion_text", "")
        
        # Si pas de texte personnalisé, utiliser le texte par défaut
        if not conclusion_text:
            programme = data.get("programme", "Portefeuille de l'Etat")
            periode = data.get("periode", "1e semestre")
            annee = data.get("annee", 2024)
            
            # Déterminer la date de période pour l'affichage
            if periode:
                periode_upper = periode.upper()
                if "PREMIER" in periode_upper or "1" in periode:
                    date_periode_text = "30 juin"
                elif "DEUXIEME" in periode_upper or "2" in periode:
                    date_periode_text = "31 décembre"
                else:
                    date_periode_text = periode
            else:
                date_periode_text = "30 juin"
            
            # Récupérer les données de performance pour générer une conclusion dynamique
            session = cls._db_session if hasattr(cls, '_db_session') and cls._db_session else None
            nb_indicateurs = 6
            nb_cibles_atteintes = 1
            taux_execution = 30
            
            if session:
                try:
                    from app.models.performance import ObjectifPerformance, IndicateurPerformance, TypeObjectif
                    from app.models.personnel import Programme
                    from sqlmodel import select, and_
                    
                    # Récupérer le programme
                    programme_obj = session.exec(
                        select(Programme).where(Programme.libelle.ilike(f"%{programme}%"))
                    ).first()
                    
                    if programme_obj:
                        # Compter les indicateurs
                        query_indicateurs = select(IndicateurPerformance).join(
                            ObjectifPerformance
                        ).where(
                            and_(
                                ObjectifPerformance.programme_id == programme_obj.id,
                                ObjectifPerformance.type_objectif == TypeObjectif.SPECIFIQUE
                            )
                        )
                        indicateurs = session.exec(query_indicateurs).all()
                        nb_indicateurs = len(indicateurs) if indicateurs else 6
                        
                        # Compter les cibles atteintes (simplifié - on pourrait calculer plus précisément)
                        # Pour l'instant, on garde la valeur par défaut
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lors de la récupération des données pour la conclusion: {e}")
            
            conclusion_text = f"""En définitive, sur les cibles des six (6) indicateurs du programme « {programme} », une (1) cible a été atteinte au cours du {periode} de l'exercice {annee}. Les activités sont en cours pour l'atteinte des cinq (5) cibles restantes à fin décembre {annee}. Concernant l'exécution budgétaire au {date_periode_text} {annee}, le taux de réalisation est de {taux_execution}%."""
        
        # Construire la story
        story = []
        
        # Ajouter le titre "CONCLUSION"
        story.append(Paragraph("CONCLUSION", title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Convertir le texte en Paragraph
        # Échapper les caractères spéciaux pour HTML/XML
        conclusion_escaped = conclusion_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(conclusion_escaped, body_style))
        
        # Fonction pour dessiner le footer
        def draw_footer(page_num: int):
            """Dessine le footer pour chaque page"""
            RPROGLayoutDrawer.draw_page_footer(
                pdf=pdf,
                page_number=page_num,
                width=width,
                footer_margin=footer_margin,
                footer_height=footer_height,
                right_margin=right_margin,
                total_pages=getattr(cls, '_total_pages', None)
            )
        
        # Rendre la story avec pagination automatique
        logger.info(f"🔢 NUMÉROTATION - AVANT _render_multipage_story pour conclusion: start_page={start_page}")
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
        logger.info(f"🔢 NUMÉROTATION - APRÈS _render_multipage_story pour conclusion: final_page={final_page}")
        
        # Enregistrer la position de la conclusion
        RAPPageManager.register_page_position("rprog_conclusion", start_page)
        
        return final_page

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
        
        # Charger les données depuis RprogDataService si disponibles
        if session:
            try:
                from app.services.rprog_data_service import RprogDataService
                from app.models.personnel import Programme
                from sqlmodel import select
                
                # Récupérer le programme_id depuis le nom du programme
                programme_nom = data.get("programme")
                annee = data.get("annee")
                periode = data.get("periode")
                
                if programme_nom and annee and periode:
                    # Chercher le programme par nom
                    programme_query = select(Programme).where(
                        (Programme.libelle == programme_nom) | (Programme.code == programme_nom)
                    )
                    programme = session.exec(programme_query).first()
                    
                    if programme:
                        # Charger les données RPROG depuis la base (une seule ligne par programme)
                        rprog_data = RprogDataService.get_rprog_data(
                            db_session=session,
                            programme_id=programme.id
                        )
                        
                        if rprog_data:
                            # Fusionner les données chargées avec les données fournies (les données fournies ont priorité)
                            if rprog_data.difficultes_rencontrees:
                                data["difficultes_rencontrees"] = rprog_data.difficultes_rencontrees
                            if rprog_data.actions_solutions:
                                data["actions_solutions"] = rprog_data.actions_solutions
                            if rprog_data.difficultes_intro:
                                data["difficultes_intro"] = rprog_data.difficultes_intro
                            if rprog_data.solutions_intro:
                                data["solutions_intro"] = rprog_data.solutions_intro
                            if rprog_data.activites_commentaires:
                                data["activites_commentaires"] = rprog_data.activites_commentaires
                            if rprog_data.credits_commentaires:
                                data["credits_commentaires"] = rprog_data.credits_commentaires
                            if rprog_data.investissements_commentaires:
                                data["investissements_commentaires"] = rprog_data.investissements_commentaires
                            if rprog_data.effectifs_commentaires:
                                data["effectifs_commentaires"] = rprog_data.effectifs_commentaires
                            if rprog_data.performance_commentaires:
                                data["performance_commentaires"] = rprog_data.performance_commentaires
                            if rprog_data.conclusion_texte:
                                data["conclusion_texte"] = rprog_data.conclusion_texte
                            
                            logger.info(f"✅ Données RPROG chargées depuis la base pour programme_id={programme.id}, annee={annee}, periode={periode}")
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du chargement des données RPROG depuis la base: {e}")
        
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
        # La section activités commence après l'introduction
        activites_start_page = next_page
        activites_buffer, next_page = RPROGContentDrawer.draw_realisations_activites(
            start_page=activites_start_page
        )
        
        # ====================================================================
        # 6. GÉNÉRER LA SECTION "1.2. LES CRÉDITS BUDGÉTAIRES"
        # ====================================================================
        logger.info("📄 Génération de la section '1.2. Les crédits budgétaires'...")
        # La section crédits commence après la section activités
        credits_start_page = next_page
        credits_buffer, next_page = RPROGContentDrawer.draw_realisations_credits(
            start_page=credits_start_page
        )
        
        # ====================================================================
        # 6.5. GÉNÉRER LA SECTION "1.3. LES INVESTISSEMENTS"
        # ====================================================================
        logger.info("📄 Génération de la section '1.3. Les investissements'...")
        # La section investissements commence après la section crédits
        investissements_start_page = next_page
        investissements_buffer, next_page = RPROGContentDrawer.draw_realisations_investissements(
            start_page=investissements_start_page
        )
        
        # ====================================================================
        # 6.6. GÉNÉRER LA SECTION "1.4. LES EFFECTIFS"
        # ====================================================================
        logger.info("📄 Génération de la section '1.4. Les effectifs'...")
        # La section effectifs commence après la section investissements
        effectifs_start_page = next_page
        effectifs_buffer, next_page = RPROGContentDrawer.draw_realisations_effectifs(
            start_page=effectifs_start_page
        )
        
        # ====================================================================
        # 7. GÉNÉRER LA SECTION "2. LA PERFORMANCE DU PROGRAMME"
        # ====================================================================
        logger.info("📄 Génération de la section '2. La performance du programme'...")
        # La section performance commence après la section effectifs
        performance_start_page = next_page
        performance_buffer, next_page = RPROGContentDrawer.draw_performance_programme(
            start_page=performance_start_page
        )
        
        # ====================================================================
        # 8. GÉNÉRER LA SECTION "3. DIFFICULTÉS ET SOLUTIONS"
        # ====================================================================
        logger.info("📄 Génération de la section '3. Difficultés et Solutions'...")
        difficultes_buffer = BytesIO()
        difficultes_pdf = canvas.Canvas(difficultes_buffer, pagesize=landscape(A4))
        # La section difficultés commence après la section performance
        difficultes_start_page = next_page
        next_page = RPROGContentDrawer.draw_difficultes_solutions(
            difficultes_pdf, width, height, difficultes_start_page
        )
        difficultes_pdf.save()
        difficultes_buffer.seek(0)
        
        # ====================================================================
        # 9. GÉNÉRER LA SECTION "CONCLUSION"
        # ====================================================================
        logger.info("📄 Génération de la section 'Conclusion'...")
        conclusion_buffer = BytesIO()
        conclusion_pdf = canvas.Canvas(conclusion_buffer, pagesize=landscape(A4))
        # La section conclusion commence après la section difficultés
        conclusion_start_page = next_page
        next_page = RPROGContentDrawer.draw_conclusion(
            conclusion_pdf, width, height, conclusion_start_page
        )
        conclusion_pdf.save()
        conclusion_buffer.seek(0)
        
        # ====================================================================
        # 10. GÉNÉRER LE CONTENU PRINCIPAL (autres sections si nécessaire)
        # ====================================================================
        # Pour l'instant, on crée juste une page vide pour la structure
        logger.info("📄 Génération du contenu principal (autres sections)...")
        content_buffer = BytesIO()
        content_pdf = canvas.Canvas(content_buffer, pagesize=landscape(A4))
        # Pas d'autres sections pour l'instant
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
        # 5. NETTOYER LES PAGES VIDES ET CALCULER LE TOTAL RÉEL
        # ====================================================================
        logger.info("🔍 Nettoyage des pages vides et calcul du total réel...")
        
        # Fonction pour nettoyer les pages vides (comme dans le RAP)
        # Fonction pour nettoyer les pages vides (comme dans le RAP)
        def clean_empty_pages(pages, section_name):
            """Nettoie les pages vides d'une liste de pages PDF (comme dans le RAP)
            
            Une page est considérée comme vide si :
            - Elle ne contient aucun texte, ou
            - Elle ne contient que des numéros de page (footer), ou
            - Elle contient très peu de contenu (moins de 50 caractères après nettoyage)
            """
            logger.info(f"🔍 NETTOYAGE - Analyse de {len(pages)} pages pour la section '{section_name}'")
            cleaned_pages = []
            for i, page in enumerate(pages):
                try:
                    page_text = page.extract_text()
                    page_text_stripped = page_text.strip() if page_text else ""
                    text_length = len(page_text_stripped)
                    
                    # Logs détaillés pour chaque page
                    logger.info(f"🔍 NETTOYAGE - Page {section_name} {i+1}/{len(pages)}:")
                    logger.info(f"   - Texte brut (premiers 100 caractères): '{page_text[:100] if page_text else 'VIDE'}'")
                    logger.info(f"   - Texte nettoyé (premiers 100 caractères): '{page_text_stripped[:100] if page_text_stripped else 'VIDE'}'")
                    logger.info(f"   - Longueur du texte: {text_length} caractères")
                    
                    # Détecter si la page ne contient que le numéro de page (pattern: "Page X sur Y" ou similaire)
                    is_only_page_number = False
                    text_normalized = ""
                    if page_text_stripped:
                        # Pattern pour détecter uniquement des numéros de page (ex: "Page 8 sur 9", "8", etc.)
                        # Enlever les espaces et vérifier si ça ressemble à un numéro de page
                        text_normalized = re.sub(r'\s+', ' ', page_text_stripped).strip()
                        page_number_pattern = re.compile(r'^(Page\s+\d+\s+sur\s+\d+|Page\s+\d+|\d+)$', re.IGNORECASE)
                        if page_number_pattern.match(text_normalized):
                            is_only_page_number = True
                            logger.info(f"   - ⚠️ Page ne contient que le numéro de page: '{text_normalized}'")
                    
                    # Une page est considérée vide si :
                    # 1. Elle a moins de 50 caractères ET ne contient pas de mots significatifs, OU
                    # 2. Elle ne contient que le numéro de page
                    if text_length >= 50:
                        # Page avec suffisamment de contenu
                        cleaned_pages.append(page)
                        logger.info(f"   ✅ Page {section_name} {i+1} CONSERVÉE ({text_length} caractères - contenu significatif)")
                    elif text_length >= 10 and not is_only_page_number:
                        # Page avec peu de contenu mais pas seulement un numéro de page
                        # Vérifier s'il y a des mots significatifs (au moins 3 mots de plus de 2 caractères)
                        words = [w for w in page_text_stripped.split() if len(w) > 2]
                        if len(words) >= 3:
                            cleaned_pages.append(page)
                            logger.info(f"   ✅ Page {section_name} {i+1} CONSERVÉE ({text_length} caractères, {len(words)} mots significatifs)")
                        else:
                            logger.warning(f"   ❌ Page {section_name} {i+1} SUPPRIMÉE (peu de mots significatifs: {len(words)} mots, '{text_normalized[:100] if text_normalized else page_text_stripped[:100]}')")
                    else:
                        logger.warning(f"   ❌ Page {section_name} {i+1} SUPPRIMÉE (vide ou seulement numéro de page: {text_length} caractères)")
                        if page_text_stripped:
                            logger.warning(f"      Contenu détecté: '{page_text_stripped[:200]}'")
                except Exception as e:
                    logger.error(f"   ⚠️ Erreur lors de l'extraction du texte de la page {section_name} {i+1}: {e}")
                    # En cas d'erreur, on garde la page par sécurité
                    cleaned_pages.append(page)
                    logger.warning(f"   ⚠️ Page {section_name} {i+1} conservée par sécurité (erreur d'extraction)")
            
            logger.info(f"🔍 NETTOYAGE - Résultat pour '{section_name}': {len(cleaned_pages)} pages conservées sur {len(pages)} générées")
            if len(cleaned_pages) < len(pages):
                logger.warning(f"⚠️ NETTOYAGE - {len(pages) - len(cleaned_pages)} page(s) vide(s) supprimée(s) dans '{section_name}'")
            return cleaned_pages
        
        # Nettoyer les pages vides de chaque section
        cover_reader = PdfReader(cover_buffer)
        sommaire_reader = PdfReader(sommaire_buffer)
        sommaire_pages_clean = clean_empty_pages(sommaire_reader.pages, "sommaire")
        
        liste_tableaux_reader = PdfReader(liste_tableaux_buffer)
        liste_tableaux_pages_clean = clean_empty_pages(liste_tableaux_reader.pages, "liste_tableaux")
        
        introduction_reader = PdfReader(introduction_buffer)
        introduction_pages_clean = clean_empty_pages(introduction_reader.pages, "introduction")
        
        activites_reader = PdfReader(activites_buffer)
        activites_pages_clean = clean_empty_pages(activites_reader.pages, "activites")
        
        credits_reader = PdfReader(credits_buffer)
        credits_pages_clean = clean_empty_pages(credits_reader.pages, "credits")
        
        investissements_reader = PdfReader(investissements_buffer)
        investissements_pages_clean = clean_empty_pages(investissements_reader.pages, "investissements")
        
        effectifs_reader = PdfReader(effectifs_buffer)
        effectifs_pages_clean = clean_empty_pages(effectifs_reader.pages, "effectifs")
        
        performance_reader = PdfReader(performance_buffer)
        performance_pages_clean = clean_empty_pages(performance_reader.pages, "performance")
        
        difficultes_reader = PdfReader(difficultes_buffer)
        difficultes_pages_clean = clean_empty_pages(difficultes_reader.pages, "difficultes")
        
        conclusion_reader = PdfReader(conclusion_buffer)
        conclusion_pages_clean = clean_empty_pages(conclusion_reader.pages, "conclusion")
        
        content_reader = PdfReader(content_buffer)
        content_pages_clean = clean_empty_pages(content_reader.pages, "contenu")
        
        # Calculer le total réel après nettoyage
        total_pages = (
            len(cover_reader.pages) +
            len(sommaire_pages_clean) +
            len(liste_tableaux_pages_clean) +
            len(introduction_pages_clean) +
            len(activites_pages_clean) +
            len(credits_pages_clean) +
            len(investissements_pages_clean) +
            len(effectifs_pages_clean) +
            len(performance_pages_clean) +
            len(difficultes_pages_clean) +
            len(conclusion_pages_clean) +
            len(content_pages_clean)
        )
        
        logger.info(f"📊 Nombre total de pages calculé APRÈS nettoyage: {total_pages}")
        
        # Stocker le total_pages dans la classe pour qu'il soit accessible dans les méthodes
        cls._total_pages = total_pages
        RPROGLayoutDrawer._total_pages = total_pages
        RPROGContentDrawer._total_pages = total_pages
        
        # ====================================================================
        # 6. RÉGÉNÉRER LES PDFs AVEC LE BON TOTAL_PAGES DANS LES FOOTERS
        # ====================================================================
        logger.info("🔄 Régénération des PDFs avec le bon total de pages et les bons numéros de page de départ...")
        
        # Calculer les numéros de page de départ en utilisant les pages nettoyées
        current_page = 1  # Commence après la couverture
        
        # Calculer le nombre de pages du sommaire (on le régénérera à la fin après toutes les sections)
        # Pour l'instant, on utilise les pages nettoyées pour calculer le start_page suivant
        sommaire_reader_temp = PdfReader(sommaire_buffer)
        sommaire_pages_clean_temp = clean_empty_pages(sommaire_reader_temp.pages, "sommaire_temp")
        current_page += len(sommaire_pages_clean_temp)
        
        # Calculer le numéro de page de départ de la liste des tableaux
        liste_tableaux_start_page = current_page + 1
        
        # Régénérer la liste des tableaux avec le bon total_pages et le bon start_page
        liste_tableaux_buffer = BytesIO()
        liste_tableaux_pdf = canvas.Canvas(liste_tableaux_buffer, pagesize=landscape(A4))
        RPROGContentDrawer.draw_liste_tableaux(
            liste_tableaux_pdf, width, height, liste_tableaux_start_page,
            pdf_reader_complet=None, nb_pages_sommaire=0
        )
        liste_tableaux_pdf.save()
        liste_tableaux_buffer.seek(0)
        liste_tableaux_reader_temp = PdfReader(liste_tableaux_buffer)
        liste_tableaux_pages_clean_temp = clean_empty_pages(liste_tableaux_reader_temp.pages, "liste_tableaux_regeneré")
        current_page += len(liste_tableaux_pages_clean_temp)
        
        # Régénérer l'introduction avec le bon total_pages
        introduction_start_page = current_page + 1
        introduction_buffer = BytesIO()
        introduction_pdf = canvas.Canvas(introduction_buffer, pagesize=landscape(A4))
        RPROGContentDrawer.draw_introduction(
            introduction_pdf, width, height, introduction_start_page
        )
        introduction_pdf.save()
        introduction_buffer.seek(0)
        introduction_reader_temp = PdfReader(introduction_buffer)
        introduction_pages_clean_temp = clean_empty_pages(introduction_reader_temp.pages, "introduction_regeneré")
        current_page += len(introduction_pages_clean_temp)
        
        # Régénérer la section "1.1. Les activités" avec le bon total_pages
        activites_start_page = current_page + 1
        activites_buffer, _ = RPROGContentDrawer.draw_realisations_activites(
            start_page=activites_start_page
        )
        activites_reader_temp = PdfReader(activites_buffer)
        activites_pages_clean_temp = clean_empty_pages(activites_reader_temp.pages, "activites_regeneré")
        current_page += len(activites_pages_clean_temp)
        
        # Régénérer la section "1.2. Les crédits budgétaires" avec le bon total_pages
        credits_start_page = current_page + 1
        credits_buffer, _ = RPROGContentDrawer.draw_realisations_credits(
            start_page=credits_start_page
        )
        credits_reader_temp = PdfReader(credits_buffer)
        credits_pages_clean_temp = clean_empty_pages(credits_reader_temp.pages, "credits_regeneré")
        current_page += len(credits_pages_clean_temp)
        
        # Régénérer la section "1.3. Les investissements" avec le bon total_pages
        investissements_start_page = current_page + 1
        investissements_buffer, _ = RPROGContentDrawer.draw_realisations_investissements(
            start_page=investissements_start_page
        )
        investissements_reader_temp = PdfReader(investissements_buffer)
        investissements_pages_clean_temp = clean_empty_pages(investissements_reader_temp.pages, "investissements_regeneré")
        current_page += len(investissements_pages_clean_temp)
        
        # Régénérer la section "1.4. Les effectifs" avec le bon total_pages
        effectifs_start_page = current_page + 1
        effectifs_buffer, _ = RPROGContentDrawer.draw_realisations_effectifs(
            start_page=effectifs_start_page
        )
        effectifs_reader_temp = PdfReader(effectifs_buffer)
        effectifs_pages_clean_temp = clean_empty_pages(effectifs_reader_temp.pages, "effectifs_regeneré")
        current_page += len(effectifs_pages_clean_temp)
        
        # Régénérer la section "2. La performance du programme" avec le bon total_pages
        performance_start_page = current_page + 1
        performance_buffer, _ = RPROGContentDrawer.draw_performance_programme(
            start_page=performance_start_page
        )
        performance_reader_temp = PdfReader(performance_buffer)
        performance_pages_clean_temp = clean_empty_pages(performance_reader_temp.pages, "performance_regeneré")
        current_page += len(performance_pages_clean_temp)
        
        # Régénérer la section "3. Difficultés et Solutions" avec le bon total_pages
        difficultes_start_page = current_page + 1
        difficultes_buffer = BytesIO()
        difficultes_pdf = canvas.Canvas(difficultes_buffer, pagesize=landscape(A4))
        RPROGContentDrawer.draw_difficultes_solutions(
            difficultes_pdf, width, height, difficultes_start_page
        )
        difficultes_pdf.save()
        difficultes_buffer.seek(0)
        difficultes_reader_temp = PdfReader(difficultes_buffer)
        difficultes_pages_clean_temp = clean_empty_pages(difficultes_reader_temp.pages, "difficultes_regeneré")
        current_page += len(difficultes_pages_clean_temp)
        
        # Régénérer la section "CONCLUSION" avec le bon total_pages
        conclusion_start_page = current_page + 1
        conclusion_buffer = BytesIO()
        conclusion_pdf = canvas.Canvas(conclusion_buffer, pagesize=landscape(A4))
        RPROGContentDrawer.draw_conclusion(
            conclusion_pdf, width, height, conclusion_start_page
        )
        conclusion_pdf.save()
        conclusion_buffer.seek(0)
        conclusion_reader_temp = PdfReader(conclusion_buffer)
        conclusion_pages_clean_temp = clean_empty_pages(conclusion_reader_temp.pages, "conclusion_regeneré")
        current_page += len(conclusion_pages_clean_temp)
        
        # Mettre à jour les listes de pages nettoyées avec les versions régénérées
        sommaire_pages_clean = sommaire_pages_clean_temp
        liste_tableaux_pages_clean = liste_tableaux_pages_clean_temp
        introduction_pages_clean = introduction_pages_clean_temp
        activites_pages_clean = activites_pages_clean_temp
        credits_pages_clean = credits_pages_clean_temp
        investissements_pages_clean = investissements_pages_clean_temp
        effectifs_pages_clean = effectifs_pages_clean_temp
        performance_pages_clean = performance_pages_clean_temp
        difficultes_pages_clean = difficultes_pages_clean_temp
        conclusion_pages_clean = conclusion_pages_clean_temp
        
        # Recalculer le total après régénération (au cas où des pages vides auraient été supprimées)
        total_pages = (
            len(cover_reader.pages) +
            len(sommaire_pages_clean) +
            len(liste_tableaux_pages_clean) +
            len(introduction_pages_clean) +
            len(activites_pages_clean) +
            len(credits_pages_clean) +
            len(investissements_pages_clean) +
            len(effectifs_pages_clean) +
            len(performance_pages_clean) +
            len(difficultes_pages_clean) +
            len(conclusion_pages_clean) +
            len(content_pages_clean)
        )
        
        logger.info(f"📊 Nombre total de pages FINAL après régénération: {total_pages}")
        
        # Mettre à jour le total_pages dans les classes
        cls._total_pages = total_pages
        RPROGLayoutDrawer._total_pages = total_pages
        RPROGContentDrawer._total_pages = total_pages
        
        # Régénérer le sommaire EN DERNIER avec les bonnes positions de toutes les sections
        logger.info("🔄 Régénération finale du sommaire avec les positions correctes de toutes les sections...")
        sommaire_buffer = BytesIO()
        sommaire_pdf = canvas.Canvas(sommaire_buffer, pagesize=landscape(A4))
        RPROGContentDrawer.draw_table_of_contents(
            sommaire_pdf, width, height, pdf_reader_complet=None, nb_pages_sommaire=0
        )
        sommaire_pdf.save()
        sommaire_buffer.seek(0)
        sommaire_reader_temp = PdfReader(sommaire_buffer)
        sommaire_pages_clean_temp = clean_empty_pages(sommaire_reader_temp.pages, "sommaire_regeneré_final")
        
        # Mettre à jour la liste de pages nettoyées du sommaire avec la version finale
        sommaire_pages_clean = sommaire_pages_clean_temp
        
        # ====================================================================
        # 7. FUSIONNER TOUS LES PDFs DANS LE BON ORDRE
        # ====================================================================
        logger.info("📎 Fusion de tous les PDFs (pages déjà nettoyées)...")
        
        writer = PdfWriter()
        
        # 1. Couverture (page 1)
        writer.add_page(cover_reader.pages[0])
        
        # 2. Sommaire (page 2+)
        for page in sommaire_pages_clean:
            writer.add_page(page)
        
        # 3. Liste des tableaux
        for page in liste_tableaux_pages_clean:
            writer.add_page(page)
        
        # 4. Introduction
        for page in introduction_pages_clean:
            writer.add_page(page)
        
        # 5. Section "1.1. Les activités"
        for page in activites_pages_clean:
            writer.add_page(page)
        
        # 6. Section "1.2. Les crédits budgétaires"
        logger.info("=" * 80)
        logger.info("🔍 FUSION - TRAITEMENT DE LA SECTION CRÉDITS")
        logger.info("=" * 80)
        logger.info(f"🔍 FUSION - Section 'credits': {len(credits_pages_clean)} pages à ajouter")
        logger.info(f"🔍 FUSION - Nombre de pages dans writer AVANT ajout crédits: {len(writer.pages)}")
        for idx, page in enumerate(credits_pages_clean):
            writer.add_page(page)
            logger.info(f"🔍 FUSION - Page credits {idx+1}/{len(credits_pages_clean)} ajoutée au PDF final. Total pages dans writer: {len(writer.pages)}")
        logger.info(f"🔍 FUSION - Nombre de pages dans writer APRÈS ajout crédits: {len(writer.pages)}")
        logger.info("=" * 80)
        
        # 6.5. Section "1.3. Les investissements"
        logger.info(f"🔍 FUSION - Nombre de pages dans writer AVANT ajout investissements: {len(writer.pages)}")
        for idx, page in enumerate(investissements_pages_clean):
            writer.add_page(page)
            logger.info(f"🔍 FUSION - Page investissements {idx+1}/{len(investissements_pages_clean)} ajoutée. Total pages dans writer: {len(writer.pages)}")
        logger.info(f"🔍 FUSION - Nombre de pages dans writer APRÈS ajout investissements: {len(writer.pages)}")
        
        # 6.6. Section "1.4. Les effectifs"
        for page in effectifs_pages_clean:
            writer.add_page(page)
        
        # 7. Section "2. La performance du programme"
        for page in performance_pages_clean:
            writer.add_page(page)
        
        # 8. Section "3. Difficultés et Solutions"
        for page in difficultes_pages_clean:
            writer.add_page(page)
        
        # 9. Section "CONCLUSION"
        for page in conclusion_pages_clean:
            writer.add_page(page)
        
        # 10. Contenu principal (autres sections)
        for page in content_pages_clean:
            writer.add_page(page)
        
        # Écrire le PDF final
        logger.info("=" * 80)
        logger.info(f"🔍 NETTOYAGE - RÉSUMÉ FINAL: {len(writer.pages)} pages dans le PDF final")
        logger.info("=" * 80)
        
        try:
            final_buffer = BytesIO()
            writer.write(final_buffer)
            final_buffer.seek(0)
            
            # Vérifier que le PDF est valide
            if final_buffer.getvalue():
                try:
                    # Vérifier le PDF final pour détecter d'éventuelles pages vides
                    final_buffer_copy = BytesIO(final_buffer.getvalue())
                    final_buffer_copy.seek(0)
                    final_reader = PdfReader(final_buffer_copy)
                    logger.info(f"🔍 NETTOYAGE - Vérification du PDF final: {len(final_reader.pages)} pages")
                    for i, page in enumerate(final_reader.pages):
                        try:
                            page_text = page.extract_text().strip() if page.extract_text() else ""
                            text_length = len(page_text)
                            if text_length < 10:
                                logger.warning(f"🔍 NETTOYAGE - ⚠️ Page {i+1} du PDF final semble vide ({text_length} caractères): '{page_text[:100]}'")
                            else:
                                logger.info(f"🔍 NETTOYAGE - Page {i+1} du PDF final: {text_length} caractères")
                        except Exception as e:
                            logger.warning(f"🔍 NETTOYAGE - Erreur lors de la vérification de la page {i+1}: {e}")
                except Exception as e:
                    logger.error(f"⚠️ Erreur lors de la vérification du PDF final: {e}")
                finally:
                    # Réinitialiser le buffer pour le retour
                    final_buffer.seek(0)
            else:
                raise ValueError("Le buffer PDF est vide après écriture")
            
            logger.info("✅ Génération du Rapport d'Activité RPROG terminée")
            return final_buffer
            
        except Exception as e:
            logger.error(f"❌ ERREUR CRITIQUE lors de l'écriture du PDF final: {e}", exc_info=True)
            raise

