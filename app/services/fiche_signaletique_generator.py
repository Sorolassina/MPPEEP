"""
Générateur de fiche signalétique d'indicateur.

Cette classe permet de générer une fiche signalétique d'indicateur de performance
selon un modèle standardisé. Elle est conçue pour être réutilisable par différents
services (CP, RAP, RPROG, etc.).

Usage:
    from app.services.fiche_signaletique_generator import FicheSignaletiqueGenerator
    
    generator = FicheSignaletiqueGenerator(
        indicateur=indicateur_obj,
        programme=programme_obj,
        objectif_specifique=os_obj,
        ministere="Ministère...",
        annee_debut=2026,
        mode="brouillon"
    )
    
    # Générer une fiche sur un canvas existant
    generator.draw_on_canvas(pdf_canvas, width, height)
    
    # Ou générer un PDF complet avec une seule fiche
    buffer = generator.generate_pdf()
"""

import logging
import re
from io import BytesIO
from typing import Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


class FicheSignaletiqueGenerator:
    """
    Générateur de fiche signalétique d'indicateur de performance.
    
    Cette classe prend en paramètre toutes les informations nécessaires
    et génère une fiche signalétique complète selon le modèle standardisé.
    """
    
    # Couleurs
    LIGHT_GREEN = colors.HexColor("#e2efda")  # Bannière verte
    DARK_TEXT = colors.HexColor("#000000")
    GRAY_LINE = colors.HexColor("#808080")
    
    def __init__(
        self,
        indicateur: Any,
        programme: Any,
        objectif_specifique: Any,
        ministere: str,
        annee_debut: int,
        mode: str = "brouillon"
    ):
        """
        Initialise le générateur de fiche signalétique.
        
        Args:
            indicateur: Objet IndicateurPerformance
            programme: Objet Programme
            objectif_specifique: Objet ObjectifPerformance (OS)
            ministere: Nom du ministère
            annee_debut: Année de début pour les cibles
            mode: Mode "brouillon" ou "final"
        """
        self.indicateur = indicateur
        self.programme = programme
        self.objectif_specifique = objectif_specifique
        self.ministere = ministere
        self.annee_debut = annee_debut
        self.mode = mode
        
        # Couleur du texte selon le mode
        self.text_color = colors.HexColor("#FF0000") if mode == "brouillon" else self.DARK_TEXT
    
    def _get_attr(self, obj: Any, attr: str, default: str = ".............................") -> str:
        """Helper pour récupérer un attribut avec valeur par défaut."""
        if obj is None:
            return default
        value = getattr(obj, attr, default) if hasattr(obj, attr) else default
        # Si la valeur est None ou une chaîne vide, retourner la valeur par défaut
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return default
        # Convertir en chaîne si ce n'est pas déjà le cas
        return str(value) if value else default
    
    def _format_text_for_mode(self, text: str) -> str:
        """Formate le texte selon le mode (rouge pour brouillon)."""
        if self.mode == "brouillon":
            # Temporairement remplacer les balises HTML pour ne pas les échapper
            placeholders = {}
            for tag in ['b', 'i', 'u', 'strong', 'em']:
                text = text.replace(f"<{tag}>", f"__START_{tag.upper()}__").replace(f"</{tag}>", f"__END_{tag.upper()}__")
            
            # Échapper les caractères spéciaux HTML
            text_escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Restaurer les balises HTML
            for tag in ['b', 'i', 'u', 'strong', 'em']:
                text_escaped = text_escaped.replace(f"__START_{tag.upper()}__", f"<{tag}>").replace(f"__END_{tag.upper()}__", f"</{tag}>")
            
            return f'<font color="#FF0000">{text_escaped}</font>'
        return text
    
    def _draw_checkbox(self, pdf: canvas.Canvas, x: float, y: float, size: float = None, checked: bool = False) -> None:
        """Dessine une case à cocher."""
        if size is None:
            size = 0.3 * cm
        
        pdf.saveState()
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.rect(x, y, size, size, stroke=1, fill=0)
        
        if checked:
            # Dessiner une croix
            pdf.setLineWidth(1.5)
            margin = size * 0.2
            pdf.line(x + margin, y + margin, x + size - margin, y + size - margin)
            pdf.line(x + size - margin, y + margin, x + margin, y + size - margin)
        
        pdf.restoreState()
    
    def draw_on_canvas(
        self,
        pdf: canvas.Canvas,
        width: float = None,
        height: float = None,
        start_y: float = None,
        available_height: float = None,
        ajustement_hauteur_cadre: float = 0
    ) -> None:
        """
        Dessine la fiche signalétique sur un canvas PDF existant.
        
        Args:
            pdf: Le canvas PDF
            width: Largeur de la page (par défaut A4 portrait)
            height: Hauteur de la page (par défaut A4 portrait)
            start_y: Position Y de départ pour le dessin (si None, utilise bottom_margin)
        """
        if width is None or height is None:
            width, height = A4  # Format portrait pour la fiche
        
        # Marges pour le contour
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm if start_y is None else start_y
        
        # Dimensions du contour
        contour_x = left_margin
        contour_y = bottom_margin
        contour_width = width - left_margin - right_margin
        # Si start_y est spécifié, le contour commence à start_y
        if start_y is not None:
            # Le contour doit s'arrêter avant le haut de la page (height - top_margin)
            # Donc la hauteur maximale possible est height - start_y - top_margin
            max_contour_height = height - start_y - top_margin
            
            # Si available_height est fourni, l'utiliser mais ne pas dépasser max_contour_height
            # available_height est la hauteur disponible depuis start_y jusqu'au footer
            if available_height is not None:
                contour_height_from_available = available_height - top_margin
                # On prend le minimum pour s'assurer que le contour ne dépasse pas le haut de la page
                contour_height = min(max_contour_height, contour_height_from_available)
            else:
                contour_height = max_contour_height
            
            # Appliquer l'ajustement de hauteur du cadre (soustraire pour réduire la hauteur)
            contour_height = contour_height - ajustement_hauteur_cadre
        else:
            contour_height = height - top_margin - bottom_margin
        
        logger.info(f"📐 Dessin de la fiche signalétique - width={width}, height={height}, start_y={start_y}")
        logger.info(f"📐 Contour: x={contour_x}, y={contour_y}, width={contour_width}, height={contour_height}")
        logger.info(f"📐 Marges: left={left_margin}, right={right_margin}, top={top_margin}, bottom={bottom_margin}")
        logger.info(f"📐 Indicateur: {self._get_attr(self.indicateur, 'nom', 'N/A')}")
        logger.info(f"📐 Programme: {self._get_attr(self.programme, 'libelle', 'N/A')}")
        
        # ====================================================================
        # CONTOUR DE LA FICHE
        # ====================================================================
        pdf.saveState()
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.rect(contour_x, contour_y, contour_width, contour_height, stroke=1, fill=0)
        pdf.restoreState()
        
        # Position de départ pour le contenu (on dessinera à l'intérieur du contour)
        # Le contenu doit commencer au haut du contour moins la marge supérieure
        if start_y is not None:
            # Le contour commence à contour_y (qui est start_y) et a une hauteur de contour_height
            # Le haut du contour est donc à contour_y + contour_height
            # Le contenu commence au haut du contour moins la marge supérieure
            current_y = contour_y  
        else:
            # Sans start_y, le contour commence en bas avec bottom_margin
            # Le haut du contour est à bottom_margin + contour_height
            # Le contenu commence au haut du contour moins la marge supérieure
            current_y = bottom_margin + contour_height 
        
        # ====================================================================
        # CADRE DU TITRE
        # ====================================================================
        # Dimensions du cadre du titre
        titre_box_margin = 0.5 * cm  # Marge intérieure du cadre
        titre_top_spacing = 0.2 * cm  # Espace entre le haut du contour et le cadre
        titre_box_x = contour_x + titre_box_margin
        titre_box_height = 1.3 * cm  # Hauteur réduite du cadre du titre
        titre_box_y = current_y - titre_top_spacing - titre_box_height
        titre_box_width = contour_width - 2 * titre_box_margin
        
        # Dessiner le rectangle avec bordure et fond vert pâle
        pdf.saveState()
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(2)  # Bordure fine
        pdf.setFillColor(self.LIGHT_GREEN)  # Fond vert pâle
        pdf.rect(titre_box_x, titre_box_y, titre_box_width, titre_box_height, stroke=1, fill=1)
        pdf.restoreState()
        
        # Dessiner le titre centré horizontalement et verticalement
        pdf.saveState()
        font_size = 12
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Texte noir
        title_text = "FICHE SIGNALETIQUE D'INDICATEUR"
        title_width = pdf.stringWidth(title_text, "Helvetica-Bold", font_size)
        title_x = titre_box_x + (titre_box_width - title_width) / 2  # Centré horizontalement
        # Centrage vertical : on utilise la hauteur de la police pour calculer la position
        # La position y de drawString est la ligne de base, donc on ajoute la moitié de la hauteur de police
        title_y = titre_box_y + (titre_box_height - font_size) / 2 + font_size * 0.3  # Centré verticalement
        pdf.drawString(title_x, title_y, title_text)
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        current_y = titre_box_y - 0.5 * cm
        
        # ====================================================================
        # CADRE DES INFORMATIONS GÉNÉRALES
        # ====================================================================
        # Dimensions du cadre des informations générales
        info_box_margin = 0.5 * cm  # Marge intérieure du cadre
        info_box_spacing = 0.1 * cm  # Espace réduit entre le titre et ce cadre
        info_box_x = contour_x + info_box_margin
        info_box_y = current_y - info_box_spacing
        info_box_width = contour_width - 2 * info_box_margin
        
        # Calculer la hauteur nécessaire (4 lignes avec espacement augmenté)
        line_height = 0.7 * cm  # Espacement augmenté entre les lignes
        padding_top = 0.15 * cm
        padding_bottom = 0.3 * cm
        text_x = info_box_x + 0.3 * cm
        max_text_width = info_box_width - 0.6 * cm  # Largeur disponible pour le texte
        
        # Préparer les données pour chaque ligne
        font_size = 9
        
        # 1. Ministère
        ministere_name = self.ministere if self.ministere else '.............................'
        # Convertir en title case (première lettre de chaque mot en majuscule)
        if ministere_name and ministere_name != '.............................':
            ministere_name = ministere_name.title()
        ministere_label = "1. Ministère:"
        ministere_value = ministere_name
        
        # 2. Programme
        programme_code = self._get_attr(self.programme, 'code', '1')
        programme_libelle = self._get_attr(self.programme, 'libelle', '.............................')
        programme_label = f"2. Programme {programme_code}:"
        programme_value = programme_libelle
        
        # 3. Objectif spécifique
        if self.objectif_specifique:
            os_code = self._get_attr(self.objectif_specifique, 'code', 'OS 1')
            os_titre = self._get_attr(self.objectif_specifique, 'titre', '.............................')
            os_label = "3. Objectif spécifique:"
            os_value = f"{os_code} : {os_titre}"
        else:
            os_label = "3. Objectif spécifique:"
            os_value = "............................."
        
        # 4. Libellé de l'indicateur
        indicateur_nom = self._get_attr(self.indicateur, 'nom', '.............................')
        indicateur_label = "4. Libellé de l'indicateur:"
        indicateur_value = indicateur_nom
        
        # Calculer la largeur des libellés en gras pour aligner les valeurs
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)
        label_widths = {
            'ministere': pdf.stringWidth(ministere_label, "Helvetica-Bold", font_size),
            'programme': pdf.stringWidth(programme_label, "Helvetica-Bold", font_size),
            'os': pdf.stringWidth(os_label, "Helvetica-Bold", font_size),
            'indicateur': pdf.stringWidth(indicateur_label, "Helvetica-Bold", font_size)
        }
        pdf.restoreState()
        
        # Calculer le nombre de lignes nécessaires pour chaque valeur
        pdf.saveState()
        pdf.setFont("Helvetica", font_size)
        max_label_width = max(label_widths.values())
        value_start_x = text_x + max_label_width + 0.2 * cm
        value_max_width = info_box_width - (value_start_x - info_box_x) - 0.3 * cm
        
        ministere_value_lines = simpleSplit(ministere_value, "Helvetica", font_size, value_max_width)
        programme_value_lines = simpleSplit(programme_value, "Helvetica", font_size, value_max_width)
        os_value_lines = simpleSplit(os_value, "Helvetica", font_size, value_max_width)
        indicateur_value_lines = simpleSplit(indicateur_value, "Helvetica", font_size, value_max_width)
        
        pdf.restoreState()
        
        # Calculer la hauteur totale nécessaire
        total_lines = max(len(ministere_value_lines), 1) + max(len(programme_value_lines), 1) + max(len(os_value_lines), 1) + max(len(indicateur_value_lines), 1)
        info_box_height = padding_top + (total_lines * line_height) + padding_bottom
        info_box_y = info_box_y - info_box_height
        
        # Dessiner le rectangle avec bordure noire
        pdf.saveState()
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.setFillColor(colors.white)  # Fond blanc
        pdf.rect(info_box_x, info_box_y, info_box_width, info_box_height, stroke=1, fill=1)
        pdf.restoreState()
        
        # Dessiner les informations
        pdf.saveState()
        
        # Position de départ pour le texte
        text_y = info_box_y + info_box_height - padding_top - line_height
        
        # Fonction helper pour dessiner libellé + valeur
        def draw_label_value(label, value_lines, label_width):
            nonlocal text_y
            current_line_y = text_y
            # Dessiner le libellé en gras (toujours en noir)
            pdf.setFont("Helvetica-Bold", font_size)
            pdf.setFillColor(self.DARK_TEXT)  # Labels toujours en noir
            pdf.drawString(text_x, current_line_y, label)
            # Dessiner la valeur en normal (rouge si brouillon)
            pdf.setFont("Helvetica", font_size)
            pdf.setFillColor(self.text_color)  # Valeurs en rouge si brouillon
            value_x = text_x + label_width + 0.2 * cm
            if value_lines:
                for i, value_line in enumerate(value_lines):
                    if i == 0:
                        pdf.drawString(value_x, current_line_y, value_line)
                    else:
                        current_line_y -= line_height
                        pdf.drawString(value_x, current_line_y, value_line)
                text_y = current_line_y - line_height
            else:
                text_y = current_line_y - line_height
        
        # 1. Ministère
        draw_label_value(ministere_label, ministere_value_lines, label_widths['ministere'])
        
        # 2. Programme
        draw_label_value(programme_label, programme_value_lines, label_widths['programme'])
        
        # 3. Objectif spécifique
        draw_label_value(os_label, os_value_lines, label_widths['os'])
        
        # 4. Libellé de l'indicateur
        draw_label_value(indicateur_label, indicateur_value_lines, label_widths['indicateur'])
        
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        current_y = info_box_y - 0.3 * cm
        
        # ====================================================================
        # SECTION 5: DÉFINITION DE L'INDICATEUR
        # ====================================================================
        section_spacing = 0.3 * cm
        definition_spacing = 0.2 * cm
        
        # Titre de la section (toujours en noir)
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Titre toujours en noir
        definition_title = "5. Définition de l'indicateur"
        pdf.drawString(text_x, current_y - section_spacing, definition_title)
        pdf.restoreState()
        
        # Position pour le cadre de définition
        definition_box_y = current_y - section_spacing - 0.4 * cm
        definition_box_margin = 0.5 * cm
        definition_box_x = contour_x + definition_box_margin
        definition_box_width = contour_width - 2 * definition_box_margin
        
        # Récupérer la définition
        definition_text = self._get_attr(self.indicateur, 'description', '.............................')
        if not definition_text or definition_text == '.............................':
            definition_text = '.............................'
        
        # Formater le texte : supprimer les espaces inutiles
        # Supprimer les espaces multiples et les espaces en début/fin
        definition_text = re.sub(r'\s+', ' ', definition_text).strip()
        
        # Calculer la hauteur nécessaire pour le texte avec un meilleur espacement
        definition_text_width = definition_box_width - 0.4 * cm  # Marge intérieure
        definition_lines = simpleSplit(definition_text, "Helvetica", font_size, definition_text_width)
        definition_padding = 0.3 * cm  # Padding augmenté
        line_spacing = 0.45 * cm  # Espacement entre les lignes amélioré
        definition_box_height = definition_padding * 2 + (len(definition_lines) * line_spacing)
        
        # S'assurer qu'il y a au moins une hauteur minimale
        if definition_box_height < 0.8 * cm:
            definition_box_height = 0.8 * cm
        
        definition_box_y = definition_box_y - definition_box_height
        
        # Dessiner le rectangle avec bordure noire
        pdf.saveState()
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.setFillColor(colors.white)  # Fond blanc
        pdf.rect(definition_box_x, definition_box_y, definition_box_width, definition_box_height, stroke=1, fill=1)
        pdf.restoreState()
        
        # Dessiner le texte de la définition avec justification
        pdf.saveState()
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(self.text_color)
        definition_text_x = definition_box_x + 0.2 * cm
        definition_text_y = definition_box_y + definition_box_height - definition_padding - 0.25 * cm
        
        for i, line in enumerate(definition_lines):
            # Justifier le texte (sauf pour la dernière ligne)
            if i < len(definition_lines) - 1 and len(line.strip()) > 0:
                # Calculer l'espace nécessaire pour justifier
                words = line.split()
                if len(words) > 1:
                    # Calculer la largeur du texte sans espaces supplémentaires
                    text_width = sum(pdf.stringWidth(word, "Helvetica", font_size) for word in words)
                    space_width = pdf.stringWidth(' ', "Helvetica", font_size)
                    total_spaces_width = (len(words) - 1) * space_width
                    total_text_width = text_width + total_spaces_width
                    
                    # Espace disponible
                    available_width = definition_text_width
                    
                    # Si le texte est plus court que l'espace disponible, justifier
                    if total_text_width < available_width and len(words) > 1:
                        extra_space = (available_width - total_text_width) / (len(words) - 1)
                        # Dessiner les mots avec espacement justifié
                        x_pos = definition_text_x
                        for j, word in enumerate(words):
                            pdf.drawString(x_pos, definition_text_y, word)
                            if j < len(words) - 1:
                                x_pos += pdf.stringWidth(word, "Helvetica", font_size) + space_width + extra_space
                    else:
                        pdf.drawString(definition_text_x, definition_text_y, line)
                else:
                    pdf.drawString(definition_text_x, definition_text_y, line)
            else:
                # Dernière ligne : alignement à gauche
                pdf.drawString(definition_text_x, definition_text_y, line)
            definition_text_y -= line_spacing
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        current_y = definition_box_y - 0.3 * cm
        
        # ====================================================================
        # SECTION 6: NATURE DE L'INDICATEUR
        # ====================================================================
        section_spacing = 0.3 * cm
        checkbox_size = 0.3 * cm
        checkbox_spacing = 0.3 * cm
        option_spacing = 1.5 * cm  # Espace entre les éléments
        
        # Position pour tout sur la même ligne
        option_y = current_y - section_spacing
        
        # Déterminer quelle option est sélectionnée
        categorie = self._get_attr(self.indicateur, 'categorie', '').lower()
        is_qualitatif = categorie == 'qualitatif'
        is_quantitatif = categorie == 'quantitatif'
        
        pdf.saveState()
        
        # Titre de la section (6. Nature de l'Indicateur) - toujours en noir
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Titre toujours en noir
        nature_title = "6. Nature de l'Indicateur"
        nature_x = text_x
        pdf.drawString(nature_x, option_y, nature_title)
        
        # 6.1. Qualitatif (label + checkbox côte à côte, sur la même ligne que le titre)
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(self.text_color)  # Valeurs en rouge si brouillon
        qualitatif_text = "6.1. Qualitatif"
        qualitatif_x = nature_x + pdf.stringWidth(nature_title, "Helvetica-Bold", font_size) + option_spacing
        pdf.drawString(qualitatif_x, option_y, qualitatif_text)
        
        # Checkbox pour Qualitatif (à côté du label)
        checkbox_x1 = qualitatif_x + pdf.stringWidth(qualitatif_text, "Helvetica", font_size) + checkbox_spacing
        checkbox_y = option_y - 0.1 * cm  # Aligné verticalement avec le texte
        self._draw_checkbox(pdf, checkbox_x1, checkbox_y, checkbox_size, checked=is_qualitatif)
        
        # 6.2. Quantitatif (label + checkbox côte à côte, sur la même ligne)
        quantitatif_text = "6.2. Quantitatif"
        quantitatif_x = checkbox_x1 + checkbox_size + option_spacing
        pdf.drawString(quantitatif_x, option_y, quantitatif_text)
        
        # Checkbox pour Quantitatif (à côté du label)
        checkbox_x2 = quantitatif_x + pdf.stringWidth(quantitatif_text, "Helvetica", font_size) + checkbox_spacing
        self._draw_checkbox(pdf, checkbox_x2, checkbox_y, checkbox_size, checked=is_quantitatif)
        
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        current_y = option_y - 0.5 * cm
        
        # ====================================================================
        # SECTION 7: MÉTHODE DE CALCUL DE L'INDICATEUR
        # ====================================================================
        section_spacing = 0.3 * cm
        definition_spacing = 0.2 * cm
        
        # Titre de la section (toujours en noir)
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Titre toujours en noir
        methode_title = "7. Méthode de calcul de l'Indicateur"
        pdf.drawString(text_x, current_y - section_spacing, methode_title)
        pdf.restoreState()
        
        # Position pour le cadre de méthode
        methode_box_y = current_y - section_spacing - 0.4 * cm
        methode_box_margin = 0.5 * cm
        methode_box_x = contour_x + methode_box_margin
        methode_box_width = contour_width - 2 * methode_box_margin
        
        # Récupérer la méthode de calcul
        methode_text = self._get_attr(self.indicateur, 'methode', None) or self._get_attr(self.indicateur, 'formule_calcul', None)
        if not methode_text or methode_text == '.............................':
            methode_text = '.............................'
        
        # Formater le texte : supprimer les espaces inutiles
        # Supprimer les espaces multiples et les espaces en début/fin
        methode_text = re.sub(r'\s+', ' ', methode_text).strip()
        
        # Calculer la hauteur nécessaire pour le texte avec un meilleur espacement
        methode_text_width = methode_box_width - 0.4 * cm  # Marge intérieure
        methode_lines = simpleSplit(methode_text, "Helvetica", font_size, methode_text_width)
        methode_padding = 0.3 * cm  # Padding augmenté
        line_spacing = 0.45 * cm  # Espacement entre les lignes amélioré
        methode_box_height = methode_padding * 2 + (len(methode_lines) * line_spacing)
        
        # S'assurer qu'il y a au moins une hauteur minimale
        if methode_box_height < 0.8 * cm:
            methode_box_height = 0.8 * cm
        
        methode_box_y = methode_box_y - methode_box_height
        
        # Dessiner le rectangle avec bordure noire
        pdf.saveState()
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.setFillColor(colors.white)  # Fond blanc
        pdf.rect(methode_box_x, methode_box_y, methode_box_width, methode_box_height, stroke=1, fill=1)
        pdf.restoreState()
        
        # Dessiner le texte de la méthode centré
        pdf.saveState()
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(self.text_color)
        methode_text_y = methode_box_y + methode_box_height - methode_padding - 0.25 * cm
        
        for i, line in enumerate(methode_lines):
            # Centrer chaque ligne
            line_width = pdf.stringWidth(line, "Helvetica", font_size)
            methode_text_x = methode_box_x + (methode_box_width - line_width) / 2
            pdf.drawString(methode_text_x, methode_text_y, line)
            methode_text_y -= line_spacing
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        current_y = methode_box_y - 0.3 * cm
        
        # ====================================================================
        # SECTION 8: SOURCES DE DONNÉES
        # ====================================================================
        section_spacing = 0.3 * cm
        
        # Label et valeur sur la même ligne
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        source_label = "8. Sources de données:"
        label_width = pdf.stringWidth(source_label, "Helvetica-Bold", font_size)
        pdf.drawString(text_x, current_y - section_spacing, source_label)
        
        # Valeur (en normal, rouge si brouillon)
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(self.text_color)  # Valeur en rouge si brouillon
        source_value = self._get_attr(self.indicateur, 'source_donnees', '.............................')
        value_x = text_x + label_width + 0.2 * cm
        max_value_width = contour_width - (value_x - contour_x) - 0.5 * cm
        
        # Gérer le retour à la ligne si nécessaire
        source_value_lines = simpleSplit(source_value, "Helvetica", font_size, max_value_width)
        if source_value_lines:
            pdf.drawString(value_x, current_y - section_spacing, source_value_lines[0])
            # Si plusieurs lignes, les dessiner en dessous
            if len(source_value_lines) > 1:
                for i, line in enumerate(source_value_lines[1:], 1):
                    pdf.drawString(value_x, current_y - section_spacing - (i * 0.4 * cm), line)
        
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        if len(source_value_lines) > 1:
            current_y = current_y - section_spacing - (len(source_value_lines) - 1) * 0.4 * cm - 0.4 * cm
        else:
            current_y = current_y - section_spacing - 0.4 * cm
        
        # ====================================================================
        # SECTION 8.1: MODE DE COLLECTE DES DONNÉES
        # ====================================================================
        subsection_spacing = 0.3 * cm
        checkbox_size = 0.3 * cm
        checkbox_spacing = 0.3 * cm
        option_spacing = 0.8 * cm  # Espace réduit entre les options
        
        # Position pour tout sur la même ligne
        option_y = current_y - 0.4 * cm
        
        # Déterminer quelle option est sélectionnée
        mode_collecte = self._get_attr(self.indicateur, 'mode_collecte_donnees', '').lower()
        is_routine = mode_collecte and 'routine' in str(mode_collecte).lower()
        is_enquete = mode_collecte and ('enquete' in str(mode_collecte).lower() or 'enquête' in str(mode_collecte).lower())
        is_autre = mode_collecte and mode_collecte.lower() not in ['routine', 'enquete', 'enquête'] and mode_collecte.strip() != ''
        
        pdf.saveState()
        
        # Titre de la sous-section (8.1. Mode de collecte des données :) sur la même ligne - toujours en noir
        pdf.setFont("Helvetica-Bold", font_size)  # Label en gras
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        mode_collecte_title = "8.1. Mode de collecte des données :"
        mode_collecte_x = text_x
        pdf.drawString(mode_collecte_x, option_y, mode_collecte_title)
        
        # Options en rouge si brouillon
        pdf.setFont("Helvetica", font_size)  # Valeurs en police normale
        pdf.setFillColor(self.text_color)  # Valeurs en rouge si brouillon
        
        # Option 1: Routine (sur la même ligne)
        routine_text = "Routine"
        routine_x = mode_collecte_x + pdf.stringWidth(mode_collecte_title, "Helvetica-Bold", font_size) + option_spacing
        pdf.drawString(routine_x, option_y, routine_text)
        
        # Checkbox pour Routine
        checkbox_x1 = routine_x + pdf.stringWidth(routine_text, "Helvetica", font_size) + checkbox_spacing
        checkbox_y = option_y - 0.1 * cm
        self._draw_checkbox(pdf, checkbox_x1, checkbox_y, checkbox_size, checked=is_routine)
        
        # Option 2: Enquête
        enquete_text = "Enquête"
        enquete_x = checkbox_x1 + checkbox_size + option_spacing
        pdf.drawString(enquete_x, option_y, enquete_text)
        
        # Checkbox pour Enquête
        checkbox_x2 = enquete_x + pdf.stringWidth(enquete_text, "Helvetica", font_size) + checkbox_spacing
        self._draw_checkbox(pdf, checkbox_x2, checkbox_y, checkbox_size, checked=is_enquete)
        
        # Option 3: Autre à préciser (sans checkbox, avec ligne pointillée)
        autre_text = "Autre à préciser :"
        autre_x = checkbox_x2 + checkbox_size + option_spacing
        pdf.drawString(autre_x, option_y, autre_text)
        
        # Ligne pointillée après "Autre à préciser :"
        ligne_x = autre_x + pdf.stringWidth(autre_text, "Helvetica", font_size) + 0.2 * cm
        ligne_width = contour_width - (ligne_x - contour_x) - 0.5 * cm
        ligne_y = option_y - 0.05 * cm
        
        # Dessiner une ligne pointillée
        pdf.setDash([2, 2])
        pdf.setLineWidth(0.5)
        pdf.line(ligne_x, ligne_y, ligne_x + ligne_width, ligne_y)
        pdf.setDash()  # Réinitialiser le style de ligne
        
        # Afficher la valeur si elle existe dans la base
        if is_autre and mode_collecte:
            autre_value = str(mode_collecte)
            pdf.drawString(ligne_x, option_y, autre_value)
        
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        current_y = option_y - 0.4 * cm
        
        # ====================================================================
        # SECTION 8.2: PROVENANCE DES DONNÉES
        # ====================================================================
        subsection_spacing = 0.3 * cm
        
        # Label et valeur sur la même ligne
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        provenance_label = "8.2. Provenance des données :"
        label_width = pdf.stringWidth(provenance_label, "Helvetica-Bold", font_size)
        pdf.drawString(text_x, current_y - 0.4 * cm, provenance_label)
        
        # Valeur (en normal, rouge si brouillon)
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(self.text_color)  # Valeur en rouge si brouillon
        provenance_value = self._get_attr(self.indicateur, 'source_donnees', '.............................')
        value_x = text_x + label_width + 0.2 * cm
        max_value_width = contour_width - (value_x - contour_x) - 0.5 * cm
        
        # Gérer le retour à la ligne si nécessaire
        provenance_value_lines = simpleSplit(provenance_value, "Helvetica", font_size, max_value_width)
        if provenance_value_lines:
            pdf.drawString(value_x, current_y - 0.4 * cm, provenance_value_lines[0])
            # Si plusieurs lignes, les dessiner en dessous
            if len(provenance_value_lines) > 1:
                for i, line in enumerate(provenance_value_lines[1:], 1):
                    pdf.drawString(value_x, current_y - 0.4 * cm - (i * 0.4 * cm), line)
        
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        if len(provenance_value_lines) > 1:
            current_y = current_y - 0.4 * cm - (len(provenance_value_lines) - 1) * 0.4 * cm - 0.4 * cm
        else:
            current_y = current_y - 0.4 * cm - 0.4 * cm
        
        # ====================================================================
        # SECTION 8.3: RESPONSABLE DE LA COLLECTE DES DONNÉES
        # ====================================================================
        subsection_spacing = 0.3 * cm
        
        # Label et valeur sur la même ligne
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        responsable_label = "8.3. Responsable de la collecte des données :"
        label_width = pdf.stringWidth(responsable_label, "Helvetica-Bold", font_size)
        pdf.drawString(text_x, current_y - 0.4 * cm, responsable_label)
        
        # Valeur (en normal, rouge si brouillon)
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(self.text_color)  # Valeur en rouge si brouillon
        responsable_value = self._get_attr(self.indicateur, 'service_responsable', '.............................')
        value_x = text_x + label_width + 0.2 * cm
        max_value_width = contour_width - (value_x - contour_x) - 0.5 * cm
        
        # Gérer le retour à la ligne si nécessaire
        responsable_value_lines = simpleSplit(responsable_value, "Helvetica", font_size, max_value_width)
        if responsable_value_lines:
            pdf.drawString(value_x, current_y - 0.4 * cm, responsable_value_lines[0])
            # Si plusieurs lignes, les dessiner en dessous
            if len(responsable_value_lines) > 1:
                for i, line in enumerate(responsable_value_lines[1:], 1):
                    pdf.drawString(value_x, current_y - 0.4 * cm - (i * 0.4 * cm), line)
        
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        if len(responsable_value_lines) > 1:
            current_y = current_y - 0.4 * cm - (len(responsable_value_lines) - 1) * 0.4 * cm - 0.4 * cm
        else:
            current_y = current_y - 0.4 * cm - 0.4 * cm
        
        # ====================================================================
        # SECTION 9: VALEUR DE L'INDICATEUR
        # ====================================================================
        section_spacing = 0.3 * cm
        checkbox_size = 0.3 * cm
        checkbox_spacing = 0.3 * cm
        box_height = 0.4 * cm
        box_padding = 0.1 * cm
        
        # Titre de la section (toujours en noir)
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.setFillColor(self.DARK_TEXT)  # Titre toujours en noir
        valeur_title = "9. Valeur de l'indicateur"
        pdf.drawString(text_x, current_y - 0.4 * cm, valeur_title)
        pdf.restoreState()
        
        current_y = current_y - 0.4 * cm - 0.4 * cm  # 0.4 cm avant le titre + 0.4 cm après
        
        # 9.1. Unité de mesure (0.4 cm avant)
        current_y -= 0.4 * cm
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)  # Label en gras
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        unite_label = "9.1. Unité de mesure :"
        pdf.drawString(text_x, current_y, unite_label)
        
        # Valeur en rouge si brouillon
        pdf.setFont("Helvetica", font_size)  # Valeur en police normale
        pdf.setFillColor(self.text_color)  # Valeur en rouge si brouillon
        
        # Boîte pour l'unité
        unite_value = self._get_attr(self.indicateur, 'unite', '%')
        unite_box_x = text_x + pdf.stringWidth(unite_label, "Helvetica-Bold", font_size) + 0.3 * cm
        unite_box_y = current_y - 0.1 * cm
        unite_box_width = 1.5 * cm
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.rect(unite_box_x, unite_box_y, unite_box_width, box_height, stroke=1, fill=0)
        # Centrer la valeur dans la boîte
        unite_text_width = pdf.stringWidth(unite_value, "Helvetica", font_size)
        unite_text_x = unite_box_x + (unite_box_width - unite_text_width) / 2
        pdf.drawString(unite_text_x, current_y, unite_value)
        pdf.restoreState()
        
        current_y -= 0.4 * cm  # 0.4 cm après 9.1
        
        # 9.2. Périodicité (0.4 cm avant)
        current_y -= 0.4 * cm
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)  # Label en gras
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        periodicite_label = "9.2. Périodicité :"
        pdf.drawString(text_x, current_y, periodicite_label)
        
        # Options en rouge si brouillon
        pdf.setFont("Helvetica", font_size)  # Valeurs en police normale
        pdf.setFillColor(self.text_color)  # Valeurs en rouge si brouillon
        
        # Options de périodicité sur la même ligne
        option_x = text_x + pdf.stringWidth(periodicite_label, "Helvetica-Bold", font_size) + 0.5 * cm
        option_spacing = 1.5 * cm
        
        frequence = self._get_attr(self.indicateur, 'frequence_maj', 'Annuelle').lower()
        is_mensuelle = 'mensuel' in frequence
        is_trimestrielle = 'trimestriel' in frequence
        is_semestrielle = 'semestriel' in frequence
        is_annuelle = 'annuel' in frequence
        
        # Mensuelle
        mensuelle_text = "Mensuelle"
        pdf.drawString(option_x, current_y, mensuelle_text)
        checkbox_x = option_x + pdf.stringWidth(mensuelle_text, "Helvetica", font_size) + checkbox_spacing
        checkbox_y = current_y - 0.1 * cm
        self._draw_checkbox(pdf, checkbox_x, checkbox_y, checkbox_size, checked=is_mensuelle)
        
        # Trimestrielle
        trim_x = checkbox_x + checkbox_size + option_spacing
        trim_text = "Trimestrielle"
        pdf.drawString(trim_x, current_y, trim_text)
        checkbox_x2 = trim_x + pdf.stringWidth(trim_text, "Helvetica", font_size) + checkbox_spacing
        self._draw_checkbox(pdf, checkbox_x2, checkbox_y, checkbox_size, checked=is_trimestrielle)
        
        # Semestrielle
        sem_x = checkbox_x2 + checkbox_size + option_spacing
        sem_text = "Semestrielle"
        pdf.drawString(sem_x, current_y, sem_text)
        checkbox_x3 = sem_x + pdf.stringWidth(sem_text, "Helvetica", font_size) + checkbox_spacing
        self._draw_checkbox(pdf, checkbox_x3, checkbox_y, checkbox_size, checked=is_semestrielle)
        
        # Annuelle
        ann_x = checkbox_x3 + checkbox_size + option_spacing
        ann_text = "Annuelle"
        pdf.drawString(ann_x, current_y, ann_text)
        checkbox_x4 = ann_x + pdf.stringWidth(ann_text, "Helvetica", font_size) + checkbox_spacing
        self._draw_checkbox(pdf, checkbox_x4, checkbox_y, checkbox_size, checked=is_annuelle)
        
        pdf.restoreState()
        
        current_y -= 0.4 * cm  # 0.4 cm après 9.2
        
        # 9.3. Dernière valeur connue (0.4 cm avant)
        current_y -= 0.4 * cm
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)  # Label en gras
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        derniere_valeur_label = "9.3. Dernière valeur connue :"
        pdf.drawString(text_x, current_y, derniere_valeur_label)
        
        # Valeur en rouge si brouillon
        pdf.setFont("Helvetica", font_size)  # Valeur en police normale
        pdf.setFillColor(self.text_color)  # Valeur en rouge si brouillon
        
        # Boîte pour la valeur
        derniere_valeur = self._get_attr(self.indicateur, 'derniere_valeur_connue', None) or self._get_attr(self.indicateur, 'valeur_actuelle', None)
        valeur_text = "-"
        if derniere_valeur is not None:
            unite_val = self._get_attr(self.indicateur, 'unite', '')
            try:
                if unite_val and unite_val.lower() in ["%", "pourcentage"]:
                    valeur_text = f"{float(derniere_valeur):.0f}{unite_val}"
                else:
                    valeur_text = f"{float(derniere_valeur):.2f}{unite_val}"
            except (ValueError, TypeError):
                valeur_text = str(derniere_valeur)
        
        valeur_box_x = text_x + pdf.stringWidth(derniere_valeur_label, "Helvetica-Bold", font_size) + 0.3 * cm
        valeur_box_y = current_y - 0.1 * cm
        valeur_box_width = 2 * cm
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.setLineWidth(1)
        pdf.rect(valeur_box_x, valeur_box_y, valeur_box_width, box_height, stroke=1, fill=0)
        # Centrer la valeur dans la boîte
        valeur_text_width = pdf.stringWidth(valeur_text, "Helvetica", font_size)
        valeur_text_x = valeur_box_x + (valeur_box_width - valeur_text_width) / 2
        pdf.drawString(valeur_text_x, current_y, valeur_text)
        pdf.restoreState()
        
        current_y -= 0.4 * cm  # 0.4 cm après 9.3
        
        # 9.4. Cible fixée (0.4 cm avant)
        current_y -= 0.4 * cm
        pdf.saveState()
        pdf.setFont("Helvetica-Bold", font_size)  # Label en gras
        pdf.setFillColor(self.DARK_TEXT)  # Label toujours en noir
        cible_label = "9.4. Cible fixée :"
        pdf.drawString(text_x, current_y, cible_label)
        
        # Valeurs en rouge si brouillon
        pdf.setFont("Helvetica", font_size)  # Valeurs en police normale
        pdf.setFillColor(self.text_color)  # Valeurs en rouge si brouillon
        
        # Cibles pour annee_debut, annee_debut+1, annee_debut+2
        annee_labels = [self.annee_debut, self.annee_debut + 1, self.annee_debut + 2]
        cible_values = []
        if self.indicateur:
            cible_values = [
                self._get_attr(self.indicateur, 'valeur_cible', None),
                self._get_attr(self.indicateur, 'cible_N_plus_1', None),
                self._get_attr(self.indicateur, 'cible_N_plus_2', None)
            ]
        else:
            cible_values = [None, None, None]
        
        unite_cible = self._get_attr(self.indicateur, 'unite', '%')
        cible_start_x = text_x + pdf.stringWidth(cible_label, "Helvetica-Bold", font_size) + 0.3 * cm
        cible_spacing = 4.5 * cm  # Espacement augmenté entre les différentes valeurs
        
        for i, (annee, cible) in enumerate(zip(annee_labels, cible_values)):
            # Label de l'année
            annee_x = cible_start_x + i * cible_spacing
            pdf.drawString(annee_x, current_y, str(annee))
            
            # Boîte pour la cible (avec espacement entre l'année et la valeur)
            cible_box_x = annee_x + 1 * cm
            cible_box_y = current_y - 0.1 * cm
            cible_box_width = 1.5 * cm
            pdf.setStrokeColor(self.DARK_TEXT)
            pdf.setLineWidth(1)
            pdf.rect(cible_box_x, cible_box_y, cible_box_width, box_height, stroke=1, fill=0)
            
            # Texte de la cible
            cible_text = "-"
            if cible is not None:
                try:
                    if unite_cible and unite_cible.lower() in ["%", "pourcentage"]:
                        cible_text = f"{float(cible):.0f}{unite_cible}"
                    else:
                        cible_text = f"{float(cible):.2f}{unite_cible}"
                except (ValueError, TypeError):
                    cible_text = str(cible)
            
            # Centrer la valeur dans la boîte
            cible_text_width = pdf.stringWidth(cible_text, "Helvetica", font_size)
            cible_text_x = cible_box_x + (cible_box_width - cible_text_width) / 2
            pdf.drawString(cible_text_x, current_y, cible_text)
        
        pdf.restoreState()
        
        # Mettre à jour la position pour le contenu suivant
        current_y -= 0.4 * cm
        
        # ====================================================================
        # FOOTER: BOÎTE DE SIGNATURE
        # ====================================================================
        footer_spacing = 2 * cm  # Espacement augmenté avec le point 9.4
        footer_y = current_y - footer_spacing
        
        # Dimensions du tableau footer (2 lignes mais sans ligne horizontale au milieu)
        footer_table_width = contour_width - 2 * info_box_margin
        footer_col_widths = [footer_table_width / 3, footer_table_width / 3, footer_table_width / 3]
        footer_row_height = 0.9 * cm  # Hauteur augmentée
        footer_table_height = footer_row_height * 2
        
        # Données du tableau (2 lignes)
        programme_libelle = self._get_attr(self.programme, 'libelle', '.............................')
        
        # Gérer les noms de programme longs avec retour à la ligne
        # Calculer la largeur disponible pour le texte du programme
        programme_cell_width = footer_col_widths[0] - 0.4 * cm  # Moins le padding
        programme_lines = simpleSplit(programme_libelle, "Helvetica", font_size, programme_cell_width)
        
        # Utiliser Paragraph pour gérer le texte multi-lignes
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        style = styles['Normal']
        style.fontName = 'Helvetica'
        style.fontSize = font_size
        style.textColor = self.text_color
        style.alignment = 1  # CENTER
        
        if len(programme_lines) > 1:
            programme_text = Paragraph("<br/>".join(programme_lines), style)
        else:
            programme_text = Paragraph(programme_libelle, style)
        
        footer_table_data = [
            [
                "Responsable de Programme :",
                "Nom et prénoms :",
                "Signature"
            ],
            [
                programme_text,
                ".............................",
                ""  # Ligne pointillée pour la signature
            ]
        ]
        
        # Ajuster la hauteur de la ligne si le programme a plusieurs lignes
        programme_row_height = footer_row_height
        if len(programme_lines) > 1:
            programme_row_height = max(footer_row_height, len(programme_lines) * 0.4 * cm + 0.2 * cm)
        
        # Créer le tableau
        footer_table = Table(footer_table_data, colWidths=footer_col_widths, rowHeights=[footer_row_height, programme_row_height])
        footer_table_height = footer_row_height + programme_row_height
        footer_table_style = TableStyle([
            # Bordures extérieures
            ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),  # Pas de ligne en dessous de la première ligne
            ("LINEABOVE", (0, 1), (-1, 1), 0, colors.white),  # Pas de ligne au-dessus de la deuxième ligne
            ("LINEBEFORE", (0, 0), (0, -1), 1, self.DARK_TEXT),  # Bordure gauche
            ("LINEAFTER", (-1, 0), (-1, -1), 1, self.DARK_TEXT),  # Bordure droite
            ("LINEABOVE", (0, 0), (-1, 0), 1, self.DARK_TEXT),  # Bordure du haut
            ("LINEBELOW", (0, -1), (-1, -1), 1, self.DARK_TEXT),  # Bordure du bas
            # Lignes verticales entre les colonnes
            ("LINEAFTER", (0, 0), (0, -1), 1, self.DARK_TEXT),
            ("LINEAFTER", (1, 0), (1, -1), 1, self.DARK_TEXT),
            # Alignement
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Styles de police
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), font_size),
            ("TEXTCOLOR", (0, 0), (-1, 0), self.DARK_TEXT),  # Labels toujours en noir
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, 1), font_size),
            ("TEXTCOLOR", (0, 1), (-1, 1), self.text_color),  # Valeurs en rouge si brouillon
            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 0.2 * cm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0.2 * cm),
            ("TOPPADDING", (0, 0), (-1, -1), 0.1 * cm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0.1 * cm),
        ])
        footer_table.setStyle(footer_table_style)
        
        # Dessiner le tableau footer
        footer_table.wrapOn(pdf, footer_table_width, footer_table_height)
        footer_table.drawOn(pdf, contour_x + info_box_margin, footer_y - footer_table_height)
        
        # Dessiner une ligne pointillée dans la cellule Signature (ligne 2, colonne 3)
        signature_cell_x = contour_x + info_box_margin + footer_col_widths[0] + footer_col_widths[1]
        signature_cell_y = footer_y - programme_row_height - programme_row_height / 2
        signature_line_width = footer_col_widths[2] - 0.4 * cm
        signature_line_x = signature_cell_x + 0.2 * cm
        
        pdf.saveState()
        pdf.setDash([2, 2])
        pdf.setLineWidth(0.5)
        pdf.setStrokeColor(self.DARK_TEXT)
        pdf.line(signature_line_x, signature_cell_y, signature_line_x + signature_line_width, signature_cell_y)
        pdf.setDash()
        pdf.restoreState()
    
    def generate_pdf(self) -> BytesIO:
        """
        Génère un PDF complet avec une seule fiche signalétique.
        
        Returns:
            BytesIO contenant le PDF généré
        """
        buffer = BytesIO()
        width, height = A4
        pdf = canvas.Canvas(buffer, pagesize=A4)
        
        self.draw_on_canvas(pdf, width, height)
        
        pdf.save()
        buffer.seek(0)
        
        return buffer

