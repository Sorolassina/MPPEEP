from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Any
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from sqlmodel import Session, select
from sqlalchemy import func

from app.core.path_config import path_config
from app.db.session import engine
from app.models.budget import ActionBudgetaire, ActiviteBudgetaire, FicheTechnique, ServiceBeneficiaire
from app.models.personnel import Programme

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame, KeepTogether

from reportlab.lib.enums import TA_JUSTIFY


class PerformanceEngagementLetterGenerator:
    """Générateur de lettre d'engagement de performance.
    Tous les réglages visuels (dimensions, couleurs, positions) sont regroupés
    par section pour faciliter les ajustements.
    """

    logger = logging.getLogger(__name__)

    PRIMARY_GREEN = colors.HexColor("#39791b")
    SECONDARY_GREEN = colors.HexColor("#609b4d")
    LIGHT_GREEN = colors.HexColor("#387722")
    
    PRIMARY_ORANGE = colors.HexColor("#F26D21")
    LIGHT_ORANGE = colors.HexColor("#ef9543")
    LIGHT_2_ORANGE = colors.HexColor("#ee863d")
    DARK_TEXT = colors.HexColor("#1F1F1F")

    DEFAULT_DATA = {
        "annee": 2025,
        "pays": "République de Côte d'Ivoire",
        "devise": "Union – Discipline – Travail",
        "programme_intitule": "PORTEFEUILLE DE L'ETAT",
        "minister_civility": "Monsieur",
        "minister_nom": "MOUSSA SANOGO",
        "minister_fonction": "MINISTRE DU PATRIMOINE, DU PORTEFEUILLE DE L'ETAT ET DES ENTREPRISES PUBLIQUES",
        "minister_photo": "",
        "rprog_nom": "Monsieur ADAMA SALL",
        "rprog_fonction": "Responsable du Programme",
        "rprog_photo": "images/Adama_SALL.jpeg",
        "dg_nom": "BAMBA Seydou",
        "dg_fonction": "Directeur Général du Portefeuille de l'Etat",
        "logo_path": "images/logo.png",
        "ville_signature": "Abidjan",
        "date_signature": "",
    }

    @classmethod
    def generate_pdf(cls, data: dict[str, Any]) -> BytesIO:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("🚀 DÉBUT génération PDF lettre d'engagement de performance")
        cls.data = {**cls.DEFAULT_DATA, **(data or {})}
        
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        logger.info("📄 Page 1: Couverture")
        # Important : l'ordre des appels détermine la superposition des éléments.
        cls._draw_background_shapes(pdf, width, height)
        cls._draw_header(pdf, width, height)
        cls._draw_cover_block(pdf, width, height)
        cls._draw_footer(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Page 2: Signataires")
        cls._draw_signatories_page(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Page 3+: Préambule")
        # Pages de contenu - à compléter avec le contenu fourni par l'utilisateur
        cls._draw_preamble_page(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Page 4: Les Parties")
        cls._draw_parties_page(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Page 5+: CHAPITRE I")
        cls._draw_chapter_one_page(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Page 6+: CHAPITRE II")
        cls._draw_chapter_two_page(pdf, width, height)

        # Forcer une nouvelle page avant le CHAPITRE III
        pdf.showPage()

        logger.info("📄 Page 7+: CHAPITRE III")
        cls._draw_chapter_three_page(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Page 8: Signatures")
        cls._draw_signature_page(pdf, width, height)

        pdf.showPage()

        logger.info("📄 Annexes: Tableau de performance")
        # Annexes - à compléter avec le contenu fourni par l'utilisateur
        next_page = cls._draw_annex_matrice_page(pdf, start_page=9)

        
        logger.info("📄 Annexes: Matrice d'actions")
        cls._draw_annex_performance_results_page(pdf, start_page=next_page)

        logger.info("💾 Sauvegarde du PDF...")
        pdf.save()
        buffer.seek(0)
        logger.info("✅ FIN génération PDF - Succès!")
        return buffer

    @classmethod
    def _draw_background_shapes(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine les éléments décoratifs de fond (triangles, bandes, lignes)."""
        # Réutilise la même logique que EngagementLetterGenerator
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
            return

        ux, uy = dx / L, dy / L
        nx, ny = (uy, -ux)

        def pt_on_segment(t: float):
            return (start_x + t*dx, start_y + t*dy)

        def offset_point(pt, d: float):
            return (pt[0] + nx*d, pt[1] + ny*d)

        def draw_band_center(c_px, length_px, offset_px, thickness,
                     round_start=True, round_end=True,
                     extend_start_px=0, extend_end_px=0,
                     color=None, reverse=False, clamp=False):
            s_px = c_px - (length_px / 2.0)
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
            if not reverse:
                ax, ay = start_x, start_y
                dirx, diry = ux, uy
            else:
                ax, ay = end_x, end_y
                dirx, diry = -ux, -uy

            a0 = s_px - extend_start_px
            a1 = s_px + length_px + extend_end_px

            if clamp:
                a0 = max(0.0, min(L, a0))
                a1 = max(0.0, min(L, a1))

            cx0, cy0 = ax + dirx * a0, ax*0 + ay + diry * a0
            cx1, cy1 = ax + dirx * a1, ax*0 + ay + diry * a1

            rx_n, ry_n = nx * offset_px, ny * offset_px
            x0, y0 = cx0 + rx_n, cy0 + ry_n
            x1, y1 = cx1 + rx_n, cy1 + ry_n

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

        pdf.saveState()

        thickness = 8
        gap = -15
        band1_offset = gap + thickness/2
        band2_offset = band1_offset + 18
        offset = -10

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
            s_px = c_px - (length_px / 2.0)
            draw_band_slide_bl(
                s_px=s_px, length_px=length_px, offset_px=offset_px, thickness=thickness,
                round_start=round_start, round_end=round_end,
                extend_start_px=extend_start_px, extend_end_px=extend_end_px,
                color=color, reverse=reverse, clamp=clamp
            )

        tri_bl = pdf.beginPath()
        tri_bl.moveTo(0, 0)
        tri_bl.lineTo(0, 120)
        tri_bl.lineTo(220, 0)
        tri_bl.close()
        pdf.setFillColor(cls.PRIMARY_ORANGE)
        pdf.drawPath(tri_bl, stroke=0, fill=1)

        start2_x, start2_y = 0,   120
        end2_x,   end2_y   = 220, 0

        dx2, dy2 = end2_x - start2_x, end2_y - start2_y
        L2 = (dx2*dx2 + dy2*dy2) ** 0.5
        ux2, uy2 = dx2 / L2, dy2 / L2
        nx2, ny2 = (uy2, -ux2)

        pdf.saveState()

        def draw_band_slide_bl(s_px, length_px, offset_px, thickness,
                            round_start=True, round_end=True,
                            extend_start_px=0, extend_end_px=0,
                            color=None, reverse=False, clamp=False):
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

            cx0, cy0 = ax + dirx * a0, ay + diry * a0
            cx1, cy1 = ax + dirx * a1, ay + diry * a1

            x0, y0 = cx0 + nx2 * offset_px, cy0 + ny2 * offset_px
            x1, y1 = cx1 + nx2 * offset_px, cy1 + ny2 * offset_px

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

        thickness2 = 8
        gap2 = -15
        band1_offset2 = gap2 + thickness2/2
        band2_offset2 = band1_offset2 + 18
        offset2 = -10

        draw_band_slide_bl(
            s_px = 0.00 * L2,
            length_px = 0.30 * L2,
            offset_px = offset2,
            thickness = thickness2,
            round_start = True, round_end = True,
            extend_start_px = 20, extend_end_px = 4,
            color = cls.PRIMARY_ORANGE,
            reverse = False, clamp = False
        )

        draw_band_slide_bl(
            s_px = 0.00 * L2,
            length_px = 0.30 * L2,
            offset_px = offset2,
            thickness = thickness2,
            round_start = False, round_end = True,
            extend_start_px = 40, extend_end_px = 0,
            color = cls.PRIMARY_ORANGE,
            reverse = True, clamp = False
        )

        draw_band_slide_bl(
            s_px = 0.00 * L2,
            length_px = 2 * L2,
            offset_px = offset2+20,
            thickness = thickness2+13,
            round_start = False, round_end = True,
            extend_start_px = 0, extend_end_px = 0,
            color = cls.LIGHT_2_ORANGE,
            reverse = False, clamp = False
        )

        draw_band_slide_bl(
            s_px = 0.00 * L2,
            length_px = 0.30 * L2,
            offset_px = offset2+20,
            thickness = thickness2+13,
            round_start = False, round_end = True,
            extend_start_px = 40, extend_end_px = 30,
            color = cls.LIGHT_ORANGE,
            reverse = False, clamp = False
        )

        draw_band_center_bl(
            c_px = 0.5 * L2,
            length_px = 0.70 * L2,
            offset_px = offset2-10,
            thickness = thickness2,
            round_start = True, round_end = True,
            extend_start_px = 6, extend_end_px = 6,
            color = cls.LIGHT_ORANGE,
            reverse = False, clamp = False
        )

        pdf.restoreState()

    @classmethod
    def _draw_header(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine l'en-tête institutionnel (bloc ministère + devise + logo)."""
        pdf.saveState()

        header_lines = [
            "MINISTÈRE DU PATRIMOINE DU",
            "PORTEFEUILLE DE L'ÉTAT ET DES",
            "ENTREPRISES PUBLIQUES",
        ]
        pdf.setFont("Helvetica", 11)
        pdf.setFillColor(cls.DARK_TEXT)
        y = height - 30
        for line in header_lines:
            pdf.drawString(1 * cm, y, line)
            y -= 14

        logo_path = cls._resolve_asset_path("images/logo.webp")
        if logo_path:
            try:
                logo_width = 2.5 * cm
                logo_height = 2.5 * cm
                x = (width - logo_width) / 2
                y_logo = height - 85

                if logo_path.lower().endswith(".webp"):
                    try:
                        from PIL import Image

                        with Image.open(logo_path) as im:
                            im = im.convert("RGBA")
                            buffer = BytesIO()
                            im.save(buffer, format="PNG")
                            buffer.seek(0)
                            pdf.drawImage(ImageReader(buffer), x, y_logo, width=logo_width, height=logo_height, preserveAspectRatio=True, mask="auto")
                    except Exception:
                        pdf.drawImage(logo_path, x, y_logo, width=logo_width, height=logo_height, preserveAspectRatio=True)
                else:
                    pdf.drawImage(logo_path, x, y_logo, width=logo_width, height=logo_height, preserveAspectRatio=True)
            except Exception:
                pass

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(width - 170, height - 30, "République de Côte d'Ivoire")

        pdf.setFont("Helvetica", 9)
        motto = cls.data.get("devise", "")
        if not motto:
            motto = "Union – Discipline – Travail"
        pdf.drawString(width - 150, height - 40, motto)

        pdf.setLineWidth(1)
        pdf.setDash(4, 3)
        pdf.setStrokeColor(colors.white)
        pdf.line(width - 130, height - 50, width - 70, height - 50)
        pdf.setDash()

        pdf.restoreState()

    @classmethod
    def _draw_cover_block(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine le bloc central (double cadre + titres et responsables)."""
        margin_x = 1.4 * cm
        margin_y = height / 2 - 5.5 * cm
        block_width = width - 2 * margin_x
        block_height = 9.8 * cm

        pdf.saveState()
        pdf.setLineWidth(3)
        pdf.setStrokeColor(cls.PRIMARY_ORANGE)
        pdf.rect(margin_x, margin_y, block_width, block_height, stroke=1, fill=0)

        pdf.setLineWidth(1.2)
        pdf.rect(margin_x + 4, margin_y + 4, block_width - 8, block_height - 8, stroke=1, fill=0)

        pdf.setFillColor(cls.DARK_TEXT)
        center_x = width / 2
        current_y = margin_y + block_height - 56

        # Titre modifié pour performance
        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawCentredString(center_x, current_y, "LETTRE D'ENGAGEMENT SUR LA PERFORMANCE")

        current_y -= 35
        pdf.setFont("Helvetica", 13)
        pdf.drawCentredString(center_x, current_y, "CONCLUE ENTRE")

        current_y -= 35
        # Ministre
        minister_text = "LE MINISTRE DU PATRIMOINE, DU PORTEFEUILLE DE L'ETAT\nET DES ENTREPRISES PUBLIQUES"
        pdf.setFont("Helvetica-Bold", 14)
        current_y = cls._draw_wrapped_centered_lines(
            pdf,
            minister_text,
            center_x,
            current_y,
            line_height=18,
            char_limit=60,
        )

        current_y -= 14
        pdf.setFont("Helvetica", 13)
        pdf.drawCentredString(center_x, current_y, "ET")

        current_y -= 26
        # Responsable du Programme
        # Toujours afficher "LE RESPONSABLE DU PROGRAMME" sur une ligne
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(center_x, current_y, "LE RESPONSABLE DU PROGRAMME")
        current_y -= 18
        
        # Le nom du programme sur la ligne suivante (avec wrap si trop long)
        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT").strip().upper()
        programme_text = f"« {programme} »"
        # Diviser par nombre de caractères si le nom est trop long
        programme_lines = wrap(programme_text, width=40)  # Diviser à environ 40 caractères
        pdf.setFont("Helvetica-Bold", 14)
        for line in programme_lines:
            pdf.drawCentredString(center_x, current_y, line)
            current_y -= 18

        pdf.restoreState()

    @staticmethod
    def _draw_wrapped_centered_lines(
        pdf: canvas.Canvas,
        text: str,
        center_x: float,
        start_y: float,
        line_height: float,
        char_limit: int,
    ) -> float:
        """Découpe le texte en lignes centrées sans débordement."""
        if not text:
            return start_y

        lines = wrap(text, width=char_limit) or [text]
        y = start_y
        for line in lines:
            pdf.drawCentredString(center_x, y, line)
            y -= line_height
        return y

    @classmethod
    def _draw_footer(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine le bloc année en bas de page."""
        pdf.saveState()
        box_width = 7 * cm
        box_height = 1 * cm
        x = width - box_width - 1.5 * cm
        y = 2.8 * cm

        shadow_color = colors.Color(0, 0, 0, alpha=0.30)
        pdf.setFillColor(shadow_color)
        pdf.setStrokeColor(shadow_color)
        pdf.rect(x - 3, y - 3, 3, box_height - 2, stroke=0, fill=1)
        pdf.rect(x - 3, y - 3, box_width - 2, 3, stroke=0, fill=1)

        pdf.setDash(6, 4)
        pdf.setStrokeColor(cls.PRIMARY_ORANGE)
        pdf.setLineWidth(1.2)
        pdf.rect(x, y, box_width, box_height, stroke=1, fill=0)

        pdf.setDash()
        pdf.setFillColor(colors.grey)
        pdf.setFont("Helvetica", 14)
        year = str(cls.data.get("annee", "") or "")
        pdf.drawCentredString(x + box_width / 2, y + box_height / 2 - 4, year if year else "2025")

        pdf.restoreState()

    @classmethod
    def _draw_signatories_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page des signataires avec photos et informations."""
        pdf.saveState()

        def resolve_photo(path_key: str) -> str | None:
            raw = cls.data.get(path_key)
            if raw and raw.strip():
                resolved = cls._resolve_asset_path(raw)
                if resolved:
                    cls.logger.debug(f"Photo résolue pour {path_key}: {raw} -> {resolved}")
                else:
                    cls.logger.warning(f"Photo non trouvée pour {path_key}: {raw}")
                return resolved
            cls.logger.debug(f"Aucune photo fournie pour {path_key}")
            return None

        def draw_person(photo_key: str, name_key: str, fonction_key: str, entite_key: str = None, top_y: float = None) -> float:
            photo_path = resolve_photo(photo_key)
            box_width = 8 * cm
            box_height = 8 * cm
            current_y = top_y if top_y is not None else height - 90

            if photo_path:
                try:
                    pdf.drawImage(
                        photo_path,
                        (width - box_width) / 2,
                        current_y - box_height,
                        width=box_width,
                        height=box_height,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                    current_y -= box_height + 16
                except Exception:
                    current_y -= 16
            else:
                current_y -= 8

            name = (cls.data.get(name_key) or "Nom Prénom").upper()
            fonction = cls.data.get(fonction_key) or "Fonction"
            entite = cls.data.get(entite_key) if entite_key else None

            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawCentredString(width / 2, current_y, name)
            current_y -= 16

            # Gérer la fonction qui peut être sur plusieurs lignes
            fonction_upper = fonction.upper()
            # Diviser par nombre de caractères pour s'adapter à tout nom de ministère
            # Utiliser une largeur plus petite pour forcer le retour à la ligne
            wrap_width = 50
            fonction_lines = wrap(fonction_upper, width=wrap_width) if len(fonction_upper) > wrap_width else [fonction_upper]
            pdf.setFont("Helvetica", 11)
            for line in fonction_lines:
                pdf.drawCentredString(width / 2, current_y, line)
                current_y -= 16

            if entite:
                pdf.setFont("Helvetica-Bold", 11)
                # Gérer l'entité qui peut être sur plusieurs lignes
                entite_text = f"« {entite.upper()} »"
                entite_lines = wrap(entite_text, width=50) if len(entite_text) > 50 else [entite_text]
                for line in entite_lines:
                    pdf.drawCentredString(width / 2, current_y, line)
                    current_y -= 18

            return current_y

        # Ministre en haut
        top_margin = height - 90
        # Récupérer la civilité du ministre
        minister_civility = cls.data.get("minister_civility", "")
        minister_name = cls.data.get("minister_nom", "")
        # Construire le nom complet avec civilité
        if minister_civility and minister_name:
            full_name = f"{minister_civility.upper()} {minister_name.upper()}"
        else:
            full_name = minister_name.upper() if minister_name else "Nom Prénom"
        
        # Sauvegarder temporairement le nom complet
        original_name = cls.data.get("minister_nom")
        cls.data["minister_nom"] = full_name
        
        current = draw_person(
            "minister_photo",
            "minister_nom",
            "minister_fonction",
            entite_key=None,
            top_y=top_margin
        )
        
        # Restaurer le nom original
        if original_name:
            cls.data["minister_nom"] = original_name

        # "Et" entre les deux
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, current - 4, "Et")
        current -= 40

        # Responsable du Programme en bas
        current = draw_person(
            "rprog_photo",
            "rprog_nom",
            "rprog_fonction",
            "programme_intitule",
            current
        )

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "2")

        pdf.restoreState()

   
    @classmethod
    def _draw_preamble_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page du préambule avec gestion automatique du débordement."""
        # Marges et dimensions
        left_margin   = 2 * cm
        right_margin  = 2 * cm
        top_margin    = 2.5 * cm
        bottom_margin = 2 * cm
        available_width  = width  - left_margin - right_margin
        available_height = height - top_margin  - bottom_margin

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PreambleTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,          # gauche
            spaceAfter=12,
            underlineWidth=0.7,
            underlineOffset=-2
        )
        body_style = ParagraphStyle(
            "PreambleBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,  # justification
            spaceAfter=6,
        )
        bullet_style = ParagraphStyle(
            "PreambleBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            leftIndent=30,      # retrait du texte
            bulletIndent=15,    # position de la puce
            spaceAfter=4,
        )

        # Contenu
        story = []
        story.append(Paragraph("Préambule", title_style))

        paragraphs = [
            "La collecte et l'utilisation des fonds publics respectent les principes de l'État de droit que sont la légalité, la transparence, le contrôle démocratique et la responsabilité. Les institutions constitutionnelles, Ministères et secrétariats d'État, gardiens de ce bien commun, ont chacun leurs missions et responsabilités dans sa préservation et son usage pour le bien de tous.",
            "Les acteurs publics qui pilotent et gèrent les fonds publics acceptent les obligations d'intégrité et de rectitude à la mesure de la confiance qui leur est faite.",
            "Par ailleurs, dans le cadre de la mise en œuvre des politiques publiques, le Gouvernement assigne des missions aux différents Ministres et secrétaires d'État qui sont exécutées à travers des programmes.",
            "Dans la volonté de mettre en œuvre les actions et activités du programme, en vue de l'atteinte des objectifs spécifiques et des résultats qui contribuent à améliorer le bien-être économique et social des populations, des lettres d'engagement sont signées entre le Ministre et les Responsables de Programme.",
            "Le programme « Portefeuille de l'Etat » est institué pour améliorer la performance des entreprises publiques conformément aux objectifs stratégiques, économiques et sociaux de l'État.",
        ]
        for p in paragraphs:
            story.append(Paragraph(p, body_style))

        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT")
        story.append(Paragraph(f"À ce titre, le Programme « {programme} » est chargé :", body_style))

        bullet_points = [
            "d'élaborer et de mettre en œuvre une stratégie de portefeuille de l'État alignée sur les objectifs stratégiques, économiques et sociaux de l'État ;",
            "de proposer et d'assurer la mise en œuvre de la position actionnariale de l'État relative à la stratégie des entreprises et organismes du portefeuille de l'État ;",
            "d'exercer le contrôle financier et de coordonner le contrôle sur les entreprises publiques, les personnes morales de droit public à participation financière publique (droit national et international), les personnes morales de droit privé bénéficiant d'un soutien financier ou de garanties de l'État, les personnes morales de droit privé à statut particulier et les agences d'exécution ;",
            "d'analyser la situation économique et financière du portefeuille de l'État, et d'élaborer et de maintenir un système cohérent de mesure de sa performance ;",
            "de suivre l'endettement des entreprises publiques, des entreprises à participation financière publique, des personnes morales de droit privé bénéficiant d'un soutien financier ou de garanties de l'État, des personnes morales de droit privé à statut particulier et des agences d'exécution. Ce suivi comprend la tenue de statistiques consolidées sur leur dette, le service de la dette et le bénéfice moyen à long terme ;",
            "d'assurer le contrôle de la gestion économique et financière des entreprises publiques, des entreprises à participation publique, des personnes morales de droit privé bénéficiant d'un soutien financier ou de garanties de l'État, des personnes morales de droit privé à statut particulier et des agences d'exécution ;",
            "de conduire, pour le compte du Ministre chargé du Portefeuille de l'Etat, des contrôles et audits externes sur toute personne morale dotée de l'autonomie financière, bénéficiant du concours financier ou de la garantie de l'Etat ;",
            "d'assurer la préparation des plans de désengagement et de restructuration du portefeuille de l'Etat et en assurer la mise en œuvre, le cas échéant, en relation avec le comité de privatisation ;",
            "d'assurer le suivi de la mise en œuvre des opérations de privatisation le cas échéant, en relation avec le comité de privatisation, et de la post-privatisation ;",
            "d'assurer des missions de conseil et de vérification, notamment en matière juridique et financière, dans le respect des attributions des autres administrations intéressées ;",
            "d'assurer régulièrement l'information du Ministre chargé du Portefeuille de l'Etat sur la gestion et sur les résultats du portefeuille de l'Etat ;",
            "d'assurer le suivi de la gestion de la liquidation des sociétés d'Etat, des sociétés à participation financière publique, des agences d'exécution et des personnes morales de type particulier ;",
            "de définir et de s'assurer du respect des règles de gouvernance des sociétés d'Etat, des sociétés à participation financière publique, des personnes morales de type particulier et des agences d'exécution.",
        ]
        for point in bullet_points:
            story.append(Paragraph(point, bullet_style, bulletText="•"))

        # -------- Pagination avec Frame.addFromList --------
        import logging
        logger = logging.getLogger(__name__)
        
        page_num = 3
        first_page = True
        logger.info(f"   🔄 Préambule: {len(story)} éléments à afficher")

        while story:  # addFromList consomme 'story' en place
            # Nouveau "contexte" de page
            if not first_page:
                pdf.showPage()  # termine la page précédente

            pdf.saveState()
            # Pas de background spécial pour les pages de contenu (comme les autres pages)

            # Cadre de texte
            frame = Frame(
                left_margin,
                bottom_margin,
                available_width,
                available_height,
                showBoundary=0,  # passe à 1 pour débuguer les boîtes
            )

            # Sauvegarder la longueur avant pour détecter si quelque chose a été consommé
            story_length_before = len(story)
            logger.info(f"   📝 Préambule page {page_num}: {story_length_before} éléments restants")
            
            # Ajoute des flowables jusqu'à remplir la page
            frame.addFromList(story, pdf)

            # Numéro de page (si besoin)
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawRightString(width - 30, 25, str(page_num))

            pdf.restoreState()

            # Vérifier si du contenu a été consommé pour éviter une boucle infinie
            story_length_after = len(story)
            consumed = story_length_before - story_length_after
            logger.info(f"   ✅ Préambule page {page_num}: {consumed} éléments consommés, {story_length_after} restants")
            
            if story_length_after == story_length_before and story_length_before > 0:
                # Aucun élément n'a été consommé, sortir de la boucle pour éviter une boucle infinie
                logger.warning(f"   ⚠️ Préambule: Aucun élément consommé! Sortie de boucle pour éviter boucle infinie")
                break

            # Prépare la suivante
            page_num += 1
            first_page = False

    @classmethod
    def _draw_parties_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page 4 avec la section LES PARTIES."""
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, KeepTogether, Spacer

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PartiesTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=1,  # Centré
            spaceAfter=20,
        )
        body_style = ParagraphStyle(
            "PartiesBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=4,  # Justifié
            spaceAfter=12,
        )
        center_body_style = ParagraphStyle(
            "PartiesCenterBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=1,  # Centré
            spaceAfter=12,
        )

        story = []

        # Titre "LES PARTIES"
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("LES PARTIES", title_style))
        story.append(Spacer(1, 0.8 * cm))

        # Première partie : Le Ministère
        minister_civility = cls.data.get("minister_civility", "Monsieur")
        minister_nom = cls.data.get("minister_nom", "")
        minister_fonction = cls.data.get("minister_fonction", "")
        
        minister_text = (
            f"Le Ministère du Patrimoine, du Portefeuille de l'Etat et des Entreprises Publiques, "
            f"représenté par {minister_civility} {minister_nom}, {minister_fonction}, "
            f"désigné « le MINISTRE »"
        )
        story.append(Paragraph(minister_text, body_style))
        story.append(Spacer(1, 0.5 * cm))

        # "Et" centré
        story.append(Paragraph("Et", center_body_style))
        story.append(Spacer(1, 0.5 * cm))

        # Deuxième partie : La Direction Générale
        dg_nom = cls.data.get("dg_nom", "BAMBA Seydou")
        dg_fonction = cls.data.get("dg_fonction", "Directeur Général du Portefeuille de l'Etat")
        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT")
        
        dg_text = (
            f"La Direction Générale du Portefeuille de l'Etat représentée par "
            f"Monsieur {dg_nom}, {dg_fonction}, désigné « le RESPONSABLE DU PROGRAMME {programme} », "
            f"en abrégé « RPROG-{programme} »."
        )
        story.append(Paragraph(dg_text, body_style))
        story.append(Spacer(1, 1 * cm))

        # "Conviennent de ce qui suit :"
        story.append(Paragraph("Conviennent de ce qui suit :", body_style))

        # Gestion du débordement sur plusieurs pages (au cas où)
        import logging
        logger = logging.getLogger(__name__)
        
        page_num = 4
        frame_height = height - 2 * top_margin
        first_page = True
        logger.info(f"   🔄 Les Parties: {len(story)} éléments à afficher")

        while story:  # addFromList consomme 'story' en place
            # Nouveau "contexte" de page
            if not first_page:
                pdf.showPage()  # termine la page précédente

            pdf.saveState()

            # Cadre de texte
            frame = Frame(
                left_margin,
                top_margin,
                available_width,
                frame_height,
                showBoundary=0,
            )

            # Sauvegarder la longueur avant pour détecter si quelque chose a été consommé
            story_length_before = len(story)
            logger.info(f"   📝 Les Parties page {page_num}: {story_length_before} éléments restants")
            
            # Ajoute des flowables jusqu'à remplir la page
            frame.addFromList(story, pdf)

            # Numéro de page
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawRightString(width - 30, 25, str(page_num))

            pdf.restoreState()

            # Vérifier si du contenu a été consommé pour éviter une boucle infinie
            story_length_after = len(story)
            consumed = story_length_before - story_length_after
            logger.info(f"   ✅ Les Parties page {page_num}: {consumed} éléments consommés, {story_length_after} restants")
            
            if story_length_after == story_length_before and story_length_before > 0:
                # Aucun élément n'a été consommé, sortir de la boucle pour éviter une boucle infinie
                logger.warning(f"   ⚠️ Les Parties: Aucun élément consommé! Sortie de boucle pour éviter boucle infinie")
                break

            # Prépare la suivante
            page_num += 1
            first_page = False

    @classmethod
    def _draw_chapter_one_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, KeepTogether, Spacer

        # --- Marges & surface écrivable ---
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin
        frame_height = height - 2 * top_margin

        # --- Styles (tes styles, inchangés sauf keepWithNext laissé) ---
        styles = getSampleStyleSheet()
        chapter_title_style = ParagraphStyle(
            "ChapterTitle", parent=styles["Heading1"],
            fontName="Helvetica-Bold", fontSize=14, leading=18,
            alignment=0, spaceAfter=10, spaceBefore=0
        )
        article_title_style = ParagraphStyle(
            "ArticleTitle", parent=styles["Heading2"],
            fontName="Helvetica-Bold", fontSize=12, leading=16,
            alignment=0, spaceAfter=4, spaceBefore=6
        )
        body_style = ParagraphStyle(
            "ChapterBody", parent=styles["Normal"],
            fontName="Helvetica", fontSize=11, leading=16,
            alignment=4, spaceAfter=8
        )
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=11, leading=16,
            alignment=0, spaceAfter=8, spaceBefore=12
        )
        bullet_style = ParagraphStyle(
            "ChapterBullet", parent=styles["Normal"],
            bulletFontName="Helvetica", bulletFontSize=11,
            fontName="Helvetica", fontSize=11, alignment=4,
            leading=16, leftIndent=30, bulletIndent=15
        )

        # --- Helpers: articles non orphelins ---
        # On n'utilise plus KeepTogether car cela peut causer des problèmes de pagination
        # Le keepWithNext=1 dans article_title_style suffit pour garder le titre avec le contenu

        story = []

        # --- Titre chapitre ---
        story.append(Paragraph("CHAPITRE I : DISPOSITIONS GÉNÉRALES", chapter_title_style))
        story.append(Spacer(1, 0.2 * cm))

        # --- Article 1 ---
        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT")
        article1_text = (
            f"La présente lettre d'engagement sur la performance a pour objet d'engager les différentes parties "
            f"à l'atteinte des objectifs et des résultats du programme « {programme} », "
            f"définis dans le Projet Annuel de Performance (PAP)."
        )
        story.append(Paragraph("Article 1 : Objet", article_title_style))
        story.append(Paragraph(article1_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # --- Article 2 ---
        article2_text = (
            "La présente lettre d'engagement sur la performance de nature non juridique, "
            "est un engagement réciproque interne à l'Administration."
        )
        story.append(Paragraph("Article 2 : Nature de la lettre", article_title_style))
        story.append(Paragraph(article2_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # --- Article 3 (avec sous-sections + puces) ---
        minister_commitments = [
            "communiquer les orientations stratégiques du Ministère au RPROG-PORTEFEUILLE DE L'ETAT ;",
            "favoriser la mobilisation des ressources pour la mise en œuvre du programme « Portefeuille de l'État » ;",
            "favoriser toute mesure d'ordre organisationnel et/ou juridique facilitant l'accomplissement des missions confiées au Responsable de programme ;",
            "suivre les projets d'investissement du programme « Portefeuille de l'État » sur la base d'un plan pluriannuel d'investissement.",
        ]
        rprog_commitments = [
            "assurer le pilotage et la mise en œuvre du programme « Portefeuille de l'État » ;",
            "atteindre les résultats qui lui sont assignés sur la base des moyens humains, matériels et financiers mis à sa disposition ;",
            "améliorer le système de pilotage des entreprises ;",
            "améliorer le dispositif de contrôle des entreprises publiques ;",
            "optimiser le système d'information du portefeuille de l'État ;",
            "rendre compte au MINISTRE, de l'état d'avancement et de l'atteinte des objectifs et des résultats du Programme « Portefeuille de l'État » ;",
            "animer le dialogue de gestion avec les acteurs du Programme « Portefeuille de l'État » ;",
            "assurer la bonne gestion du patrimoine mis à sa disposition ;",
            "élaborer le Projet Annuel de Performance (PAP) ainsi que le Rapport Annuel de Performance (RAP) du programme « Portefeuille de l'État ».",
        ]

        story.append(Paragraph("Article 3 : Obligations générales", article_title_style))
        story.append(Paragraph("Le MINISTRE s'engage à :", subsection_title_style))
        for commitment in minister_commitments:
            story.append(Paragraph(commitment, bullet_style, bulletText="-"))
        story.append(Spacer(1, 0.1 * cm))

        story.append(Paragraph("Le RESPONSABLE DE PROGRAMME s'engage à :", subsection_title_style))
        for commitment in rprog_commitments:
            story.append(Paragraph(commitment, bullet_style, bulletText="-"))
        story.append(Spacer(1, 0.1 * cm))

        # --- Article 4 ---
        article4_text = (
            f"Sans préjudice des obligations générales citées à l'article 3 de la présente lettre d'engagement, "
            f"le MINISTRE et le RESPONSABLE DE PROGRAMME « {programme} » peuvent adopter des mesures spécifiques "
            f"portant notamment sur la gestion des délais de production des DPPD-PAP, des RAP et de l'exécution "
            f"des diligences liées au programme, sur les conditions sociales et les méthodes de prise de décision."
        )
        story.append(Paragraph("Article 4 : Obligations spécifiques", article_title_style))
        story.append(Paragraph(article4_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # --- Article 5 ---
        article5_text = "Les droits des différentes parties sont ceux qui sont garantis par les textes en vigueur."
        story.append(Paragraph("Article 5 : Droits des parties", article_title_style))
        story.append(Paragraph(article5_text, body_style))

        pdf.saveState()

        frame = Frame(
            left_margin,
            top_margin,
            available_width,
            height - 2 * top_margin,
            showBoundary=0,
        )
        frame.addFromList(story, pdf)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "5")

        pdf.restoreState()

    @classmethod
    def _draw_chapter_two_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page 6 avec le CHAPITRE II : DISPOSITIONS RELATIVES A LA PERFORMANCE."""
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, KeepTogether, Spacer

        styles = getSampleStyleSheet()
        chapter_title_style = ParagraphStyle(
            "ChapterTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,  # Gauche
            spaceAfter=20,
            textDecoration="underline",
        )
        article_title_style = ParagraphStyle(
            "ArticleTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=0,  # Gauche
            spaceAfter=4,
            spaceBefore=6,
            
            textDecoration="underline",
            keepWithNext=1,  # Garde le titre avec au moins une ligne du contenu suivant
        )
        body_style = ParagraphStyle(
            "ChapterBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=4,  # Justifié
            spaceAfter=8,
        )
        bullet_style = ParagraphStyle(
            "ChapterBullet",
            parent=styles["Normal"],
            bulletFontName="Helvetica",
            bulletFontSize=11,
            fontName="Helvetica",
            fontSize=11,
            alignment=4,  # Justifié
            leading=16,
            leftIndent=30,
            bulletIndent=15,
        )

        story = []

        # Titre du chapitre
        story.append(Paragraph("CHAPITRE II : DISPOSITIONS RELATIVES A LA PERFORMANCE", chapter_title_style))
        story.append(Spacer(1, 0.2 * cm))

        # Article 6 : Objectif stratégique
        article6_text = (
            "Les parties conviennent de l'objectif stratégique suivant : "
            "« Améliorer la gestion du portefeuille de l'État »."
        )
        story.append(Paragraph("Article 6 : Objectif stratégique", article_title_style))
        story.append(Paragraph(article6_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # Article 7 : Objectifs spécifiques
        specific_objectives = [
            "assurer la coordination de l'administration du portefeuille de l'État ;",
            "améliorer la gouvernance des entreprises publiques ;",
            "améliorer le contrôle des entreprises publiques.",
        ]
        story.append(Paragraph("Article 7 : Objectifs spécifiques", article_title_style))
        story.append(Paragraph("Les parties conviennent des objectifs spécifiques suivants :", body_style))
        for objective in specific_objectives:
            story.append(Paragraph(objective, bullet_style, bulletText="-"))
        story.append(Spacer(1, 0.1 * cm))

        # Article 8 : Indicateurs de performance
        performance_indicators = [
            "taux d'exécution du PAS du programme Portefeuille de l'État ;",
            "taux d'exécution du budget d'investissement du programme Portefeuille de l'État ;",
            "nombre de contrats de performance élaborés par la DGPE ;",
            "nombre d'entreprises publiques ayant procédé à la signature d'une lettre de mission entre le Conseil d'Administration et le Directeur Général ;",
            "taux de réalisation du plan d'audits des entreprises publiques ;",
            "taux de réalisation du plan de contrôles opérationnels des entreprises publiques.",
        ]
        conclusion_text = (
            "Les valeurs de référence et les cibles de ces indicateurs sont précisées dans un tableau de performance "
            "annexé à la présente lettre d'engagement."
        )
        story.append(Paragraph("Article 8 : Indicateurs de performance", article_title_style))
        story.append(Paragraph("Les parties conviennent des indicateurs suivants :", body_style))
        for indicator in performance_indicators:
            story.append(Paragraph(indicator, bullet_style, bulletText="-"))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(conclusion_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # Article 9 : Moyens de mise en œuvre
        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT")
        from datetime import datetime
        annee = cls.data.get("annee", datetime.now().year)
        
        article9_para1 = (
            f"Pour la mise en œuvre de la présente lettre d'engagement, le RESPONSABLE DE PROGRAMME "
            f"« {programme} » bénéficie de ressources mises à sa disposition par la Loi de Finances {annee}."
        )
        article9_para2 = (
            "En cas de contraintes pour la mise en œuvre des dispositions de l'alinéa 1 ci-dessus, "
            "celles-ci sont portées à la connaissance du MINISTRE."
        )
        story.append(Paragraph("Article 9 : Moyens de mise en œuvre", article_title_style))
        story.append(Paragraph(article9_para1, body_style))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(article9_para2, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # Article 10 : Suivi de la performance
        article10_para1 = (
            "Le suivi de l'état d'avancement de la mise en œuvre de la lettre d'engagement se fait notamment "
            "par des réunions périodiques, assorties de comptes rendus réguliers des informations liées aux indicateurs."
        )
        article10_para2 = (
            f"Pour ce qui est de l'évaluation de la performance du programme, elle se fait à travers deux rapports "
            f"semestriels d'activités et un Rapport Annuel de Performance (RAP), élaborés par le RESPONSABLE DE PROGRAMME "
            f"« {programme} » et transmis au Responsable de la Fonction Financière Ministérielle (RFFIM) pour consolidation, "
            f"avant leur transmission au MINISTRE pour adoption."
        )
        # Calculer les dates pour les rapports semestriels
        annee_suivante = annee + 1
        article10_para3 = (
            f"Le premier rapport semestriel d'activités du RPROG-{programme} parvient au RFFIM au plus tard "
            f"le 31 juillet {annee} et le second le 31 janvier {annee_suivante}."
        )
        article10_para4 = (
            f"Concernant le RAP, il est transmis au RFFIM, dans un délai de trois (3) mois après la clôture "
            f"de l'exercice budgétaire {annee}. Le RFFIM dispose, alors, de 30 jours pour le consolider avec les RAP "
            f"des autres programmes du ministère et les transmettre au MINISTRE pour validation."
        )
        article10_para5 = (
            f"La validation du RAP par le MINISTRE intervient avant la fin du mois de mai {annee_suivante}."
        )
        # Article 10 : Suivi de la performance
        # Le titre utilise keepWithNext=1 pour rester avec au moins une ligne du contenu
        story.append(Paragraph("Article 10 : Suivi de la performance", article_title_style))
        story.append(Paragraph(article10_para1, body_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(article10_para2, body_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(article10_para3, body_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(article10_para4, body_style))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(article10_para5, body_style))

        pdf.saveState()

        frame = Frame(
            left_margin,
            top_margin,
            available_width,
            height - 2 * top_margin,
            showBoundary=0,
        )
        frame.addFromList(story, pdf)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "6")

        pdf.restoreState()

    @classmethod
    def _draw_chapter_three_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine le CHAPITRE III (articles 11-12)."""
        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, Spacer

        styles = getSampleStyleSheet()
        chapter_title_style = ParagraphStyle(
            "ChapterTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,  # Gauche
            spaceAfter=20,
            textDecoration="underline",
        )
        article_title_style = ParagraphStyle(
            "ArticleTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=0,  # Gauche
            spaceAfter=10,
            spaceBefore=12,
            textDecoration="underline",
        )
        body_style = ParagraphStyle(
            "ChapterBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=4,  # Justifié
            spaceAfter=8,
        )
        bullet_style = ParagraphStyle(
            "ChapterBullet",
            parent=styles["Normal"],
            bulletFontName="Helvetica",
            bulletFontSize=11,
            fontName="Helvetica",
            fontSize=11,
            alignment=4,  # Justifié
            leading=16,
            leftIndent=30,
            bulletIndent=15,
        )

        story = []

        # Titre du chapitre
        story.append(Paragraph("CHAPITRE III : DISPOSITIONS PARTICULIÈRES", chapter_title_style))
        story.append(Spacer(1, 0.2 * cm))

        # Article 11 : Durée de la lettre d'engagement
        article11_text = (
            "La présente lettre d'engagement est conclue pour une durée d'une (1) année civile correspondant à l'année budgétaire."
        )
        story.append(Paragraph("Article 11 : Durée de la lettre d'engagement", article_title_style))
        story.append(Paragraph(article11_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # Article 12 : Révision de la lettre d'engagement
        article12_text = (
            "Les parties conviennent que la lettre d'engagement peut faire l'objet d'une révision, en cours d'exécution, "
            "dans les cas où des situations nouvelles sont de nature à modifier de manière substantielle les engagements "
            "pris par les parties."
        )
        story.append(Paragraph("Article 12 : Révision de la lettre d'engagement", article_title_style))
        story.append(Paragraph(article12_text, body_style))

        pdf.saveState()

        frame = Frame(
            left_margin,
            top_margin,
            available_width,
            height - 2 * top_margin,
            showBoundary=0,
        )
        frame.addFromList(story, pdf)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "7")

        pdf.restoreState()

    @classmethod
    def _draw_signature_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page de signatures avec les articles 13-14."""
        pdf.saveState()

        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, Spacer
        from reportlab.lib.enums import TA_JUSTIFY
        from textwrap import wrap

        styles = getSampleStyleSheet()
        article_style = ParagraphStyle(
            "ArticleTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "ArticleBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=60,
        )
        bullet_style = ParagraphStyle(
            "ArticleBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            leftIndent=30,
            bulletIndent=15,
        )

        story = []
        
        # Article 13 : Résiliation de la lettre d'engagement
        termination_conditions = [
            "l'expiration de la durée de la lettre d'engagement ;",
            "la démission du Responsable de programme ;",
            "le changement de la situation administrative de l'une des parties ;",
            "une faute de gestion du Responsable de programme ;",
            "le non-respect des obligations au sens des articles 3 et 4.",
        ]
        story.append(Paragraph("Article 13 : Résiliation de la lettre d'engagement", article_style))
        story.append(Paragraph("La résiliation de la lettre d'engagement intervient dans les cas ci-après :", body_style))
        for condition in termination_conditions:
            story.append(Paragraph(condition, bullet_style, bulletText="-"))

        # Article 14 : Date d'effet
        story.append(Paragraph("Article 14 : Date d'effet", article_style))
        story.append(
            Paragraph(
                "La présente lettre d'engagement prend effet à compter de sa date de signature par les parties.",
                body_style,
            )
        )

        frame_height = height - (2 * top_margin)
        frame = Frame(
            left_margin,
            top_margin,
            available_width,
            frame_height,
            showBoundary=0,
        )
        frame.addFromList(story, pdf)

        # Section de signatures (bas de page)
        ville = cls.data.get("ville_signature", "Abidjan")
        pdf.setFont("Helvetica", 12)
        pdf.drawRightString(width - left_margin, height / 2 + 40, f"Fait à {ville}, le…………………………")

        # Zone de signature Responsable du Programme (gauche)
        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT")
        rprog_nom = cls.data.get("rprog_nom", "Nom Prénom").upper()
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(left_margin + available_width * 0.25, height / 2 - 10, "Le Responsable du Programme")
        pdf.drawCentredString(left_margin + available_width * 0.25, height / 2 - 26, f"« {programme} »")
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(left_margin + available_width * 0.25, height / 2 - 90, rprog_nom)

        # Zone de signature Ministre (droite)
        minister_civility = cls.data.get("minister_civility", "Monsieur")
        minister_nom = cls.data.get("minister_nom", "MOUSSA SANOGO").upper()
        minister_fonction = cls.data.get("minister_fonction", "MINISTRE DU PATRIMOINE, DU PORTEFEUILLE DE L'ETAT ET DES ENTREPRISES PUBLIQUES")
        
        # Diviser la fonction du ministre en plusieurs lignes si nécessaire
        fonction_lines = wrap(minister_fonction, width=35)
        pdf.setFont("Helvetica", 11)
        y_pos = height / 2 - 10
        pdf.drawCentredString(left_margin + available_width * 0.75, y_pos, "Le Ministre du Patrimoine")
        y_pos -= 16
        if len(fonction_lines) > 1:
            pdf.drawCentredString(left_margin + available_width * 0.75, y_pos, "du Portefeuille de l'Etat")
            y_pos -= 16
            pdf.drawCentredString(left_margin + available_width * 0.75, y_pos, "et des Entreprises Publiques")
        else:
            pdf.drawCentredString(left_margin + available_width * 0.75, y_pos, minister_fonction)
        
        y_pos -= 30
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(left_margin + available_width * 0.75, y_pos, minister_nom)

        # Numéro de page
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "8")

        pdf.restoreState()

    @classmethod
    def _draw_annex_matrice_page(cls, pdf: canvas.Canvas, start_page: int) -> int:
        """Dessine l'annexe avec le tableau de performance en orientation paysage."""
        page_width, page_height = landscape(A4)
        pdf.setPageSize((page_width, page_height))

        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm
        available_width = page_width - left_margin - right_margin
        available_height = page_height - top_margin - bottom_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            "AnnexHeader",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=0,
        )
        section_style = ParagraphStyle(
            "AnnexSection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=0,
        )
        column_header_style = ParagraphStyle(
            "AnnexColumnHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # Centré
        )
        cell_style = ParagraphStyle(
            "AnnexCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=4,  # Justifié
        )
        cell_center_style = ParagraphStyle(
            "AnnexCellCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,  # Centré
        )
        objective_style = ParagraphStyle(
            "AnnexObjective",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=4,  # Justifié
        )

        annee = cls.data.get("annee", 2025)

        # En-tête
        head_rows = [
            [Paragraph("ANNEXE : DOCUMENT DE PRESENTATION DU CADRE DE PERFORMANCE", header_style)],
            [Paragraph(f"1. TABLEAU DE PERFORMANCE {annee}", section_style)],
        ]
        head_table = Table(head_rows, colWidths=[available_width])
        head_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        head_width, head_height = head_table.wrap(available_width, available_height)
        head_table.drawOn(pdf, left_margin, page_height - top_margin - head_height)
        y_cursor = page_height - top_margin - head_height - 0.5 * cm

        # Données du tableau
        table_data = []

        # En-tête du tableau
        header_row = [
            Paragraph("Objectifs spécifiques (OS)", column_header_style),
            Paragraph("Indicateurs de performance", column_header_style),
            Paragraph("Situation de référence 2023", column_header_style),
            Paragraph("Cibles", column_header_style),
            Paragraph("Cibles", column_header_style),
            Paragraph("Cibles", column_header_style),
            Paragraph("Méthode de calcul et moyen de vérification", column_header_style),
        ]
        table_data.append(header_row)

        # Sous-en-tête pour les cibles
        subheader_row = [
            Paragraph("", column_header_style),
            Paragraph("", column_header_style),
            Paragraph("", column_header_style),
            Paragraph(str(annee), column_header_style),
            Paragraph(str(annee + 1), column_header_style),
            Paragraph(str(annee + 2), column_header_style),
            Paragraph("", column_header_style),
        ]
        table_data.append(subheader_row)

        # OS 1
        table_data.append([
            Paragraph("OS 1 : Assurer la coordination de l'administration du Portefeuille de l'État", objective_style),
            Paragraph("1.1 Taux d'exécution du PAS du programme Portefeuille de l'État", cell_style),
            Paragraph("89%", cell_center_style),
            Paragraph("80%", cell_center_style),
            Paragraph("80%", cell_center_style),
            Paragraph("80%", cell_center_style),
            Paragraph("(Nombre d'activités du PAS du programme Portefeuille de l'État réalisées / Nombre d'activités du programme Portefeuille de l'État inscrites dans le PAS) x 100<br/>Sources : Rapports d'activités Cabinet / DGPE", cell_style),
        ])

        table_data.append([
            Paragraph("", cell_style),
            Paragraph("1.2 Taux d'exécution du budget d'investissement du programme Portefeuille de l'État", cell_style),
            Paragraph("100%", cell_center_style),
            Paragraph("97.5%", cell_center_style),
            Paragraph("98%", cell_center_style),
            Paragraph("99%", cell_center_style),
            Paragraph("(Montant mandats ordonnancés (investissements) du programme Portefeuille de l'État / Montant budget d'investissement du programme Portefeuille de l'État) x 100<br/>Source : Rapport d'activités DGPE", cell_style),
        ])

        # OS 2
        table_data.append([
            Paragraph("OS 2 : assurer le positionnement du Portefeuille de l'État comme un accélérateur de développement", objective_style),
            Paragraph("2.1 Nombre de contrats de performance élaborés par la DGPE", cell_style),
            Paragraph("14", cell_center_style),
            Paragraph("5", cell_center_style),
            Paragraph("5", cell_center_style),
            Paragraph("5", cell_center_style),
            Paragraph("Dénombrement<br/>Source : Rapport d'activités DGPE", cell_style),
        ])

        table_data.append([
            Paragraph("", cell_style),
            Paragraph("2.2 Nombre d'entreprises publiques ayant procédé à la signature d'une lettre de mission entre le Conseil d'Administration et le Directeur Général", cell_style),
            Paragraph("26", cell_center_style),
            Paragraph("30", cell_center_style),
            Paragraph("35", cell_center_style),
            Paragraph("37", cell_center_style),
            Paragraph("Dénombrement<br/>Source : Rapport d'activités DGPE", cell_style),
        ])

        # OS 3
        table_data.append([
            Paragraph("OS 3 : Améliorer le contrôle des Entreprises Publiques", objective_style),
            Paragraph("3.1 Taux de réalisation du plan d'audits des entreprises publiques", cell_style),
            Paragraph("100%", cell_center_style),
            Paragraph("82%", cell_center_style),
            Paragraph("85%", cell_center_style),
            Paragraph("87%", cell_center_style),
            Paragraph("(Nombre de missions d'audits des entreprises publiques réalisées / Nombre de missions d'audits des entreprises publiques prévues dans le plan annuel d'audit) x 100<br/>Source : Rapport d'activités DGPE", cell_style),
        ])

        # Calcul des largeurs de colonnes
        col_widths = [
            available_width * 0.20,  # Objectifs spécifiques
            available_width * 0.20,  # Indicateurs
            available_width * 0.08,  # Référence 2023
            available_width * 0.08,  # Cible année
            available_width * 0.08,  # Cible année+1
            available_width * 0.08,  # Cible année+2
            available_width * 0.28,  # Méthode de calcul
        ]

        # Créer le tableau
        performance_table = Table(table_data, colWidths=col_widths, repeatRows=2)
        performance_table.setStyle(
            TableStyle([
                # Bordures
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("LINEBELOW", (0, 0), (-1, 1), 1.5, colors.black),
                # En-têtes
                ("BACKGROUND", (0, 0), (-1, 1), colors.grey),
                ("BACKGROUND", (3, 0), (5, 0), colors.lightgrey),
                # Alignement
                ("ALIGN", (0, 0), (1, -1), "LEFT"),
                ("ALIGN", (2, 0), (5, -1), "CENTER"),
                ("ALIGN", (6, 0), (6, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                # Fusion des cellules pour les objectifs
                ("SPAN", (0, 2), (0, 3)),  # OS 1
                ("SPAN", (0, 4), (0, 5)),  # OS 2
                ("SPAN", (0, 6), (0, 6)),  # OS 3
            ])
        )

        # Dessiner le tableau
        table_width, table_height = performance_table.wrap(available_width, available_height - head_height - 0.5 * cm)
        performance_table.drawOn(pdf, left_margin, y_cursor - table_height)

        # Numéro de page
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(page_width - 30, 25, str(start_page))

        pdf.showPage()
        pdf.setPageSize(A4)
        return start_page + 1

    @classmethod
    def _draw_annex_performance_results_page(cls, pdf: canvas.Canvas, start_page: int) -> int:
        """Dessine l'annexe avec la matrice d'actions en orientation paysage."""
        page_width, page_height = landscape(A4)
        pdf.setPageSize((page_width, page_height))

        left_margin = 1.5 * cm
        right_margin = 1.5 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm
        available_width = page_width - left_margin - right_margin
        available_height = page_height - top_margin - bottom_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Table, TableStyle

        styles = getSampleStyleSheet()
        section_style = ParagraphStyle(
            "AnnexSection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=0,
        )
        column_header_style = ParagraphStyle(
            "AnnexColumnHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            alignment=1,  # Centré
        )
        cell_style = ParagraphStyle(
            "AnnexCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=4,  # Justifié
        )
        cell_center_style = ParagraphStyle(
            "AnnexCellCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=1,  # Centré
        )
        total_style = ParagraphStyle(
            "AnnexTotal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,  # Centré
        )

        annee = cls.data.get("annee", 2025)

        # En-tête
        head_rows = [
            [Paragraph(f"2. MATRICE D'ACTIONS {annee}", section_style)],
        ]
        head_table = Table(head_rows, colWidths=[available_width])
        head_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        head_width, head_height = head_table.wrap(available_width, available_height)
        head_table.drawOn(pdf, left_margin, page_height - top_margin - head_height)
        y_cursor = page_height - top_margin - head_height - 0.5 * cm

        # Données du tableau
        table_data = []

        # En-tête du tableau
        header_row = [
            Paragraph("Action", column_header_style),
            Paragraph("Personnel (a)", column_header_style),
            Paragraph("Biens et services (b)", column_header_style),
            Paragraph("Investissement (c)", column_header_style),
            Paragraph(f"Total {annee} (a+b+c)", column_header_style),
        ]
        table_data.append(header_row)

        # Lignes de données
        actions_data = [
            {
                "action": "Coordination des activités et optimisation du système d'information de la DGPE",
                "personnel": 31_800_000,
                "biens_services": 1_660_654_684,
                "investissement": 5_000_000_000,
            },
            {
                "action": "Gestion active du portefeuille de l'Etat",
                "personnel": 0,
                "biens_services": 456_997_244,
                "investissement": 0,
            },
            {
                "action": "Mise en place des systèmes de contrôle efficaces des entreprises publiques",
                "personnel": 0,
                "biens_services": 1_626_363_224,
                "investissement": 0,
            },
        ]

        # Calculer les totaux
        total_personnel = sum(a["personnel"] for a in actions_data)
        total_biens_services = sum(a["biens_services"] for a in actions_data)
        total_investissement = sum(a["investissement"] for a in actions_data)
        total_general = total_personnel + total_biens_services + total_investissement

        # Fonction pour formater les nombres avec espaces
        def format_number(num: int) -> str:
            return f"{num:,}".replace(",", " ")

        # Ajouter les lignes de données
        for action in actions_data:
            total_action = action["personnel"] + action["biens_services"] + action["investissement"]
            table_data.append([
                Paragraph(action["action"], cell_style),
                Paragraph(format_number(action["personnel"]), cell_center_style),
                Paragraph(format_number(action["biens_services"]), cell_center_style),
                Paragraph(format_number(action["investissement"]), cell_center_style),
                Paragraph(format_number(total_action), cell_center_style),
            ])

        # Ligne de total
        table_data.append([
            Paragraph("Total général", total_style),
            Paragraph(format_number(total_personnel), total_style),
            Paragraph(format_number(total_biens_services), total_style),
            Paragraph(format_number(total_investissement), total_style),
            Paragraph(format_number(total_general), total_style),
        ])

        # Calcul des largeurs de colonnes
        col_widths = [
            available_width * 0.40,  # Action
            available_width * 0.15,  # Personnel
            available_width * 0.15,  # Biens et services
            available_width * 0.15,  # Investissement
            available_width * 0.15,  # Total
        ]

        # Créer le tableau
        actions_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        actions_table.setStyle(
            TableStyle([
                # Bordures
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.black),
                ("LINEBELOW", (0, -2), (-1, -2), 1.5, colors.black),
                # En-tête
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                # Ligne de total
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                # Alignement
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )

        # Dessiner le tableau
        table_width, table_height = actions_table.wrap(available_width, available_height - head_height - 1 * cm)
        actions_table.drawOn(pdf, left_margin, y_cursor - table_height)

        # Source
        y_cursor = y_cursor - table_height - 0.5 * cm
        pdf.setFont("Helvetica", 9)
        pdf.drawString(left_margin, y_cursor, f"Source: Annexe 4 de la loi de finances relative au budget {annee}")

        # Numéro de page
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(page_width - 30, 25, str(start_page))

        pdf.showPage()
        pdf.setPageSize(A4)
        return start_page + 1

    @staticmethod
    def _resolve_asset_path(raw_path: str | None) -> str | None:
        if not raw_path:
            return None
        candidate = Path(raw_path)
        if candidate.is_absolute() and candidate.exists():
            return str(candidate)

        normalized = raw_path.lstrip("/")
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

        fallback = path_config.STATIC_DIR / normalized
        if fallback.exists():
            return str(fallback)

        return None

