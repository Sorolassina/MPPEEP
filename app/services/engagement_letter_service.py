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



class EngagementLetterGenerator:
    """Générateur de lettre d'engagement opérationnel (couverture).
    Tous les réglages visuels (dimensions, couleurs, positions) sont regroupés
    par section pour faciliter les ajustements.
    """

    logger = logging.getLogger(__name__)

    PRIMARY_GREEN = colors.HexColor("#39791b")
    SECONDARY_GREEN = colors.HexColor("#609b4d")
    LIGHT_GREEN = colors.HexColor("#387722")
    
    PRIMARY_ORANGE = colors.HexColor("#F26D21")
    LIGHT_ORANGE = colors.HexColor("#ef9543")
    LIGHT_2_ORANGE=colors.HexColor("#ee863d")
    DARK_TEXT = colors.HexColor("#1F1F1F")

    DEFAULT_DATA = {
        "annee": 2025,
        "pays": "République de Côte d'Ivoire",
        "devise": "Union – Discipline – Travail",
        "programme_intitule": "ADMINISTRATION GENERALE",
        "bop_intitule": "Affaires Administratives et Financières",
        "rprog_nom": "Monsieur ADAMA SALL",
        "rprog_fonction": "Responsable du Programme",
        "rprog_photo": "images/Adama_SALL.jpeg",
        "rbop_nom": "Monsieur DIARRA Hamidou",
        "rbop_fonction": "Responsable du Budget Opérationnel de Programme",
        "rbop_photo": "images/Diarra_Hamidou.jpeg",
        "rbop_email": "hamidou@example.com",
        "logo_path": "images/logo.png",
        "annexe_fiche_id": None,
        "programme_code": None,
        "annexe_year": None,
    }

    STATIC_ANNEX_ACTIONS: list[dict[str, Any]] = [
        {
            "title": "Action 1 : Gestion des ressources humaines, matérielles et financières",
            "activities": [
                {
                    "code": "Activité 1.1",
                    "description": "Assurer les charges salariales de la Direction des Affaires Financières - MPPEEP",
                },
                {"code": "Activité 1.2", "description": "Equiper la DAAF"},
                {"code": "Activité 1.3", "description": "Mener des actions sociales en faveur du personnel"},
                {"code": "Activité 1.4", "description": "Gérer les ressources humaines du Ministère"},
                {
                    "code": "Activité 1.5",
                    "description": "Assurer le fonctionnement de la Fonction Financière du Ministère",
                },
                {
                    "code": "Activité 1.6",
                    "description": "Coordonner l'élaboration des rapports périodiques et des RAP du Ministère",
                },
                {"code": "Activité 1.7", "description": "Organiser le séminaire bilan de la DAAF"},
                {
                    "code": "Activité 1.8",
                    "description": "Identifier l'ensemble des postes de travail des structures du Ministère",
                },
                {
                    "code": "Activité 1.9",
                    "description": "Suivre l'exécution du budget et centraliser les informations financières et administratives du Ministère/MPPEEP",
                },
                {"code": "Activité 1.10", "description": "Gérer le Catalogue des Mesures Nouvelles/ MPPEEP"},
                {
                    "code": "Activité 1.11",
                    "description": "Mettre en œuvre le dialogue de gestion entre les acteurs de la chaîne programmatique/ MPPEEP",
                },
                {
                    "code": "Activité 1.12",
                    "description": "Assurer le suivi de la performance des programmes/ MPPEEP",
                },
                {
                    "code": "Activité 1.13",
                    "description": "Renforcer les capacités des acteurs budgétaires/ MPPEEP",
                },
                {
                    "code": "Activité 1.14",
                    "description": "Coordonner la participation des acteurs à la présentation du Budget du MPPEEP devant les chambres du Parlement",
                },
                {
                    "code": "Activité 1.15",
                    "description": "Organiser les conférences budgétaires internes du Ministère",
                },
                {
                    "code": "Activité 1.16",
                    "description": "Elaborer et suivre les lettres d'engagement sur la performance du Ministère",
                },
                {
                    "code": "Activité 1.17",
                    "description": "Coordonner les activités préparatoires des conférences de performance",
                },
                {"code": "Activité 1.18", "description": "DAF/Gestion des dépenses centralisées"},
                {
                    "code": "Activité 1.19",
                    "description": "Elaborer et suivre la mise en œuvre du DPPD-PAP",
                },
                {
                    "code": "Activité 1.20",
                    "description": "Elaborer le manuel de procédure de gestion des ressources humaines",
                },
                {"code": "Activité 1.21", "description": "Suivre la comptabilité des matières"},
            ],
        }
    ]

    STATIC_OPERATIONAL_RESULTS: list[dict[str, str]] = [
        {
            "activite": "Assurer les charges salariales de la Direction des Affaires Financières - MPPEEP",
            "resultats": "Le salaire des agents contractuels de la DAAF-MBPE est pris en charge",
            "indicateurs": "Mandats de paiement des dépenses de personnel",
            "responsable": "DAAF/SDP",
        },
        {
            "activite": "Equiper la DAAF",
            "resultats": "Les services de la DAAF sont équipés",
            "indicateurs": "Bons de livraison",
            "responsable": "DAAF/SDMC",
        },
        {
            "activite": "Mener des actions sociales en faveur du personnel",
            "resultats": "Les actions sociales en faveur du personnel organisées",
            "indicateurs": "Listes de présence et comptes rendus",
            "responsable": "DAAF/SDP",
        },
        {
            "activite": "Gérer les ressources humaines du Ministère",
            "resultats": "Les ressources humaines du Ministère sont gérées",
            "indicateurs": "Tirage SIGFAE",
            "responsable": "DAAF/SDP",
        },
        {
            "activite": "Assurer le fonctionnement de la Fonction Financière du Ministère",
            "resultats": "- Les séances de travail avec les acteurs budgétaires sont organisées<br/>- Des sessions de renforcement de capacités sont organisées.",
            "indicateurs": "Rapport d'activité DAAF<br/>Listes de présences",
            "responsable": "DAAF/SDMC",
        },
        {
            "activite": "Coordonner l'élaboration des rapports périodiques et des RAP du Ministère",
            "resultats": "Les Rapports Périodiques et le RAP du Ministère sont élaborés",
            "indicateurs": "Copies physiques des rapports",
            "responsable": "DAAF/SDB",
        },
        {
            "activite": "Organiser le séminaire bilan de la DAAF",
            "resultats": "Le séminaire bilan de la DAF est organisé",
            "indicateurs": "Listes de présence et comptes rendus",
            "responsable": "DAAF/SDP",
        },
        {
            "activite": "Identifier l'ensemble des postes de travail des structures du Ministère",
            "resultats": "Le Référentiel des Emplois et des Compétences (REC) est régulièrement mis à jour.",
            "indicateurs": "Document physique du REC",
            "responsable": "DAAF/SDP",
        },
        {
            "activite": "Suivre l'exécution du budget et centraliser les informations financières et administratives du Ministère/MPPEEP",
            "resultats": "- La situation d'exécution est périodiquement présentée au Cabinet ;<br/>- Des réunions sur la situation d'exécution sont organisées avec les acteurs budgétaires ;<br/>- Les demandes de réaménagement sollicités par les acteurs sont traitées.",
            "indicateurs": "Décision de réaménagement budgétaires<br/>Listes de présence<br/>Présentation PowerPoint",
            "responsable": "DAAF/SDB",
        },
        {
            "activite": "Gérer le Catalogue des Mesures Nouvelles/ MPPEEP",
            "resultats": "Les conférences internes de programmation des effectifs sont organisées ;<br/>Le Catalogue des Mesures Nouvelles est élaboré et transmis au MFP",
            "indicateurs": "Catalogue des Mesures Nouvelles<br/>Liste de présence et PV des conférences",
            "responsable": "DAAF/SDP",
        },
        {
            "activite": "Mettre en œuvre le dialogue de gestion entre les acteurs de la chaîne programmatique/ MPPEEP",
            "resultats": "- Les séances de travail avec les acteurs budgétaires sont organisées ;<br/>- Des sessions de renforcement de capacités sont organisées.",
            "indicateurs": "Listes de présence et comptes rendus",
            "responsable": "DAAF/SDB",
        },
        {
            "activite": "Assurer le suivi de la performance des programmes/ MPPEEP",
            "resultats": "Des réunions périodiques de suivi sont organisées ;<br/>Des sessions de renforcement de capacités des points focaux sont organisées.",
            "indicateurs": "Listes de présence et comptes rendus",
            "responsable": "DAAF/SDB",
        },
        {
            "activite": "Renforcer les capacités des acteurs budgétaires / MPPEEP",
            "resultats": "Des sessions de renforcement de capacités des acteurs budgétaires sont organisées",
            "indicateurs": "Nombre de sessions de renforcement de capacités des acteurs budgétaires organisées<br/>Listes de présence",
            "responsable": "DAAF/SDP",
        },
    ]

    @classmethod
    def generate_pdf(cls, data: dict[str, Any]) -> BytesIO:
        cls.data = {**cls.DEFAULT_DATA, **(data or {})}
        
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Important : l'ordre des appels détermine la superposition des éléments.
        cls._draw_background_shapes(pdf, width, height)
        cls._draw_header(pdf, width, height)
        cls._draw_cover_block(pdf, width, height)
        cls._draw_footer(pdf, width, height)

        pdf.showPage()

        cls._draw_signatories_page(pdf, width, height)

        pdf.showPage()

        cls._draw_preamble_page(pdf, width, height)

        pdf.showPage()

        cls._draw_chapter_one_page(pdf, width, height)

        pdf.showPage()

        cls._draw_chapter_two_page(pdf, width, height)

        pdf.showPage()

        cls._draw_signature_page(pdf, width, height)

        pdf.showPage()

        next_page = cls._draw_annex_matrice_page(pdf, start_page=7)

        pdf.showPage()
        cls._draw_annex_operational_results_page(pdf, start_page=next_page)

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
        """Dessine l'en-tête institutionnel (bloc ministère + devise + logo)."""
        pdf.saveState()

        # Texte institutionnel haut gauche (3 lignes)
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

        # Logo central si disponible
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
                        # Si la conversion échoue, on tente quand même de charger le fichier brut
                        pdf.drawImage(logo_path, x, y_logo, width=logo_width, height=logo_height, preserveAspectRatio=True)
                else:
                    pdf.drawImage(logo_path, x, y_logo, width=logo_width, height=logo_height, preserveAspectRatio=True)
            except Exception:
                pass

        # Bloc République (texte) sur la bannière verte
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
        margin_x = 1.4 * cm  # marge latérale du cadre extérieur
        margin_y = height / 2 - 5.5 * cm  # position verticale du bloc
        block_width = width - 2 * margin_x
        block_height = 9.8 * cm

        pdf.saveState()
        pdf.setLineWidth(3)
        pdf.setStrokeColor(cls.PRIMARY_ORANGE)
        pdf.rect(margin_x, margin_y, block_width, block_height, stroke=1, fill=0)

        pdf.setLineWidth(1.2)
        # Deuxième cadre : jouer sur (+4 / -8) pour agrandir ou réduire l'écart
        pdf.rect(margin_x + 4, margin_y + 4, block_width - 8, block_height - 8, stroke=1, fill=0)

        pdf.setFillColor(cls.DARK_TEXT)
        center_x = width / 2
        current_y = margin_y + block_height - 56  # point de départ pour les textes

        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawCentredString(center_x, current_y, "LETTRE D'ENGAGEMENT OPÉRATIONNEL")

        current_y -= 35  # espace entre le titre et la mention "CONCLU ENTRE"
        pdf.setFont("Helvetica", 13)
        pdf.drawCentredString(center_x, current_y, "CONCLU ENTRE")

        current_y -= 35  # espace avant le bloc RESPONSABLE PROGRAMME
        programme = cls.data.get("programme_intitule", "").strip()
        if programme:
            programme_text = f"LE RESPONSABLE DU PROGRAMME {programme.upper()}"
        else:
            programme_text = "LE RESPONSABLE DU PROGRAMME"
        pdf.setFont("Helvetica-Bold", 14)
        # Texte découpé automatiquement en plusieurs lignes centrées
        current_y = cls._draw_wrapped_centered_lines(
            pdf,
            programme_text,
            center_x,
            current_y,
            line_height=18,
            char_limit=48,
        )

        current_y -= 14  # espace entre le programme et le libellé "ET"
        pdf.setFont("Helvetica", 13)
        pdf.drawCentredString(center_x, current_y, "ET")

        current_y -= 26  # espace avant le bloc RESPONSABLE BOP
        base_text = "LE RESPONSABLE DU BUDGET OPÉRATIONNEL DE PROGRAMME"
        pdf.setFont("Helvetica-Bold", 14)
        current_y = cls._draw_wrapped_centered_lines(
            pdf,
            base_text,
            center_x,
            current_y,
            line_height=18,
            char_limit=52,
        )

        bop = cls.data.get("bop_intitule", "").strip()
        if bop:
            current_y -= 8  # espace avant l'intitulé du BOP
            label = f"« {bop.upper()} »"
            pdf.setFont("Helvetica-Bold", 14)
            cls._draw_wrapped_centered_lines(
                pdf,
                label,
                center_x,
                current_y,
                line_height=18,
                char_limit=48,
            )

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
        """Découpe le texte en lignes centrées sans débordement.

        Paramètres utiles :
        - `char_limit` : largeur approximative avant retour à la ligne.
        - `line_height` : interligne entre deux lignes générées.
        """
        if not text:
            return start_y

        lines = wrap(text, width=char_limit) or [text]
        y = start_y
        for line in lines:
            pdf.drawCentredString(center_x, y, line)  # affichage ligne par ligne
            y -= line_height  # prépare la hauteur pour la prochaine ligne
        return y

    @classmethod
    def _draw_footer(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine le bloc année en bas de page.

        Modifier `box_width`, `box_height`, `x` et `y` pour déplacer/redimensionner
        le cartouche de date.
        """
        pdf.saveState()
        box_width = 7 * cm  # largeur du cartouche année
        box_height = 1 * cm  # hauteur du cartouche
        x = width - box_width - 1.5 * cm  # marge droite
        y = 2.8 * cm  # marge depuis le bas

        # Ombres portées (gauche & bas) pour donner du relief
        shadow_color = colors.Color(0, 0, 0, alpha=0.30)
        pdf.setFillColor(shadow_color)
        pdf.setStrokeColor(shadow_color)
        pdf.rect(x - 3, y - 3, 3, box_height - 2, stroke=0, fill=1)  # ombre gauche affinée
        pdf.rect(x - 3, y - 3, box_width - 2, 3, stroke=0, fill=1)  # ombre bas affinée

        pdf.setDash(6, 4)  # motif pointillé (6 plein / 4 vide)
        pdf.setStrokeColor(cls.PRIMARY_ORANGE)
        pdf.setLineWidth(1.2)
        pdf.rect(x, y, box_width, box_height, stroke=1, fill=0)  # cadre sans angles arrondis

        pdf.setDash()  # retour à un tracé continu pour le texte
        pdf.setFillColor(colors.grey)
        pdf.setFont("Helvetica", 14)
        year = str(cls.data.get("annee", "") or "")
        # Texte centré dans le cartouche, fallback sur 2025 si non renseigné
        pdf.drawCentredString(x + box_width / 2, y + box_height / 2 - 4, year if year else "2025")

        pdf.restoreState()

    @classmethod
    def _draw_signatories_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page des signataires avec photos et informations."""
        pdf.saveState()

        def resolve_photo(path_key: str) -> str | None:
            raw = cls.data.get(path_key)
            if raw:
                resolved = cls._resolve_asset_path(raw)
                print(f"🛑 [DEBUG] photo key={path_key} raw={raw!r} -> resolved={resolved}")
                return resolved
            print(f"🛑 [DEBUG] photo key={path_key} has no value")
            return None

        def draw_person(photo_key: str, name_key: str, fonction_key: str, entite_key: str, top_y: float) -> float:
            photo_path = resolve_photo(photo_key)
            box_width = 8 * cm
            box_height = 8 * cm
            current_y = top_y

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
            entite = cls.data.get(entite_key)

            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawCentredString(width / 2, current_y, name)
            current_y -= 16

            pdf.setFont("Helvetica", 11)
            pdf.drawCentredString(width / 2, current_y, fonction)
            current_y -= 18

            if entite:
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawCentredString(width / 2, current_y, f"« {entite.upper()} »")
                current_y -= 18

            return current_y

        top_margin = height - 90
        current = draw_person("rprog_photo", "rprog_nom", "rprog_fonction", "programme_intitule", top_margin)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, current - 4, "Et")
        current -= 40

        current = draw_person("rbop_photo", "rbop_nom", "rbop_fonction", "bop_intitule", current)

        # Numéro de page
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "2")

        pdf.restoreState()

  

    @classmethod
    def _draw_preamble_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page du préambule (page 3)."""
        pdf.saveState()

        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        # Utilisation de Paragraph/Frame pour une justification complète
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, Spacer, KeepTogether

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PreambleTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=0,
            spaceAfter=12,
        )
        body_style = ParagraphStyle(
            "PreambleBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=4,
            spaceAfter=6,
        )
        bullet_style = ParagraphStyle(
            "PreambleBullet",
            parent=styles["Normal"],
            bulletFontName="Helvetica",
            bulletFontSize=11,
            fontName="Helvetica",
            fontSize=11,
            alignment=4,
            leading=16,
            leftIndent=30,
            bulletIndent=15,
        )

        story = []
        story.append(Paragraph("Préambule", title_style))

        paragraphs = [
            "La collecte et l'utilisation des fonds publics respectent les principes de l'État de droit que sont la légalité, la transparence, le contrôle démocratique et la responsabilité. Les institutions constitutionnelles, Ministères et secrétariats d'État, gardiens de ce bien commun, ont chacun leurs missions et responsabilités dans sa préservation et son usage pour le bien de tous.",
            "Les acteurs publics qui pilotent et gèrent les fonds publics acceptent les obligations d'intégrité et de rectitude à la mesure de la confiance qui leur est faite.",
            "Par ailleurs, dans le cadre de la mise en œuvre des politiques publiques, le Gouvernement assigne des missions aux différents Ministres et secrétaires d'État qui sont exécutées à travers des programmes.",
            "Dans la volonté de mettre en œuvre les actions et activités du programme, en vue de l'atteinte des objectifs spécifiques et des résultats qui contribuent à améliorer le bien-être économique et social des populations, des lettres d'engagement opérationnel sont signées entre le Responsable de Programme et les Responsables de Budget Opérationnel de Programme.",
        ]

        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, body_style))

        bop_title = cls.data.get("bop_intitule", "")
        decret_num = cls.data.get("decret_org_num", "")
        decret_date = cls.data.get("decret_org_date", "")

        story.append(
            Paragraph(
                f"Le Responsable de Budget Opérationnel de Programme « {bop_title} », conformément au décret n°{decret_num} du {decret_date} portant organisation du Ministère du Patrimoine, du Portefeuille de l'État et des Entreprises publiques, est chargé de :",
                body_style,
            )
        )

        bullet_points = [
            "coordonner les activités d'élaboration du budget, en liaison avec les Responsables de Programme ;",
            "coordonner les activités d'élaboration du Document de Programmation Pluriannuelle des Dépenses Projet Annuel de Performance, en liaison avec les Responsables de Programme ;",
            "coordonner les activités d'élaboration des Rapports Annuels de Performance, en liaison avec les Responsables de Programme ;",
            "coordonner les activités d'élaboration des lettres d'engagement de performance et opérationnelles ;",
            "assister les Responsables de Programme pour la mise en œuvre des outils de gestion et de suivi de la performance des programmes ;",
            "animer le dialogue de gestion entre le Ministre et les Responsables de Programme ;",
            "assurer la tenue de la comptabilité des matières mises à la disposition de la Direction ;",
        ]

        for point in bullet_points:
            story.append(Paragraph(point, bullet_style, bulletText="-"))

        from reportlab.platypus import Spacer
        story.append(Spacer(1, 6))
        story.append(Paragraph("De ce qui précède, il est conclu une lettre d'engagement opérationnel :", body_style))
        story.append(Paragraph("ENTRE :", body_style))

        programme = cls.data.get("programme_intitule", "ADMINISTRATION GENERALE").upper()
        rprog_decret_num = cls.data.get("decret_resp_num", "")
        rprog_decret_date = cls.data.get("decret_resp_date", "")
        bop_title = cls.data.get("bop_intitule", "Affaires Administratives et Financières")

        story.append(
            Paragraph(
                f"Le Responsable du Programme « {programme} » désigné par le décret n°{rprog_decret_num} du {rprog_decret_date} portant désignation des Responsables de programme des ministères, ci-après désigné « Le RPROG-{programme} », d'une part,",
                body_style,
            )
        )

        story.append(
            Paragraph(
                f"Le Responsable de Budget Opérationnel de Programme « {bop_title} » ci-après désigné « Le RBOP-DAAF » ; d'autre part,",
                body_style,
            )
        )

        story.append(
            Paragraph(
                "Ensemble désigné « les parties », conviennent de ce qui suit :",
                body_style,
            )
        )

        frame = Frame(
            left_margin,
            top_margin,
            available_width,
            height - 2 * top_margin,
            showBoundary=0,
        )

        frame.addFromList(story, pdf)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "3")
        pdf.restoreState()


    @classmethod
    def _draw_chapter_one_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page du Chapitre I (page 4)."""
        pdf.saveState()

        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, Spacer
        from reportlab.lib.enums import TA_JUSTIFY

        styles = getSampleStyleSheet()
        chapter_style = ParagraphStyle(
            "ChapterTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            spaceAfter=12,
        )
        article_style = ParagraphStyle(
            "ArticleTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "ArticleBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
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
        story.append(Paragraph("CHAPITRE I : DISPOSITIONS GENERALES", chapter_style))
        story.append(Paragraph("Article 1 : Objet", article_style))

        bop_title = cls.data.get("bop_intitule", "Affaires Administratives et Financières")
        programme = cls.data.get("programme_intitule", "ADMINISTRATION GENERALE")

        story.append(
            Paragraph(
                f"La présente lettre d'engagement opérationnel a pour objet d'engager les différentes parties à mettre en œuvre les actions et activités du Budget Opérationnel de Programme « {bop_title} » conformément à la stratégie définie dans le Document de Programmation Pluriannuelle des Dépenses - Projet Annuel de Performance (DPPD-PAP) annexé à la Loi de Finances.",
                body_style,
            )
        )
        story.append(
            Paragraph(
                f"Elle dérive de la lettre d'engagement signée entre le Responsable du Programme « {programme.upper()} » et le Ministre du Patrimoine, du Portefeuille de l'État et des Entreprises publiques.",
                body_style,
            )
        )

        story.append(Paragraph("Article 2 : Nature de la lettre", article_style))
        story.append(
            Paragraph(
                "La présente lettre est un engagement réciproque, de nature quasi-contractuelle interne à l'administration.",
                body_style,
            )
        )

        story.append(Paragraph("Article 3 : Obligations générales", article_style))

        story.append(
            Paragraph(
                f"Le Responsable de programme « {programme.upper()} » s'engage à :",
                body_style,
            )
        )
        rp_bullets = [
            "définir le périmètre du Budget Opérationnel de Programme (BOP);",
            "assister le Responsable du Budget Opérationnel de Programme (RBOP) dans la programmation des activités du BOP;",
            "assister le RBOP dans la répartition des crédits budgétaires du BOP;",
            "faciliter tous les mouvements de crédits du BOP;",
            "favoriser toute mesure d'ordre organisationnel et/ou juridique facilitant l'accomplissement des missions confiées au BOP;",
            "suivre la mise en œuvre des activités conduites par le RBOP, notamment celles relatives aux projets d'investissement en vue du respect des Autorisations d'Engagement (AE).",
        ]
        for bullet in rp_bullets:
            story.append(Paragraph(bullet, bullet_style, bulletText="-"))

        story.append(Spacer(2, 10))

        story.append(
            Paragraph(
                f"Le Responsable de Budget Opérationnel de Programme « {bop_title} », s'engage, en vertu de la présente lettre à :",
                body_style,
            )
        )
        rbop_bullets = [
            "mettre en place un dispositif permanent de collecte et de transmission des données et informations ;",
            "rendre compte au Responsable de programme de l'état d'avancement de la mise en œuvre des activités ;",
            "assurer la coordination des activités des Unités Opérationnelles ;",
            "entretenir, en bon père de famille, le patrimoine mis à sa disposition ;",
            "produire son rapport d'activités trimestriel.",
        ]
        for bullet in rbop_bullets:
            story.append(Paragraph(bullet, bullet_style, bulletText="-"))

        frame = Frame(
            left_margin,
            top_margin,
            available_width,
            height - 2 * top_margin,
            showBoundary=0,
        )
        frame.addFromList(story, pdf)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "4")

        pdf.restoreState()

    @classmethod
    def _draw_chapter_two_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page du Chapitre I (suite) et début du Chapitre II (page 5)."""
        pdf.saveState()

        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, Spacer
        from reportlab.lib.enums import TA_JUSTIFY

        styles = getSampleStyleSheet()
        article_style = ParagraphStyle(
            "ArticleTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            spaceAfter=6,
        )
        chapter_style = ParagraphStyle(
            "ChapterTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=10,
        )
        body_style = ParagraphStyle(
            "ArticleBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
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

        programme = cls.data.get("programme_intitule", "ADMINISTRATION GENERALE").upper()
        bop_title = cls.data.get("bop_intitule", "Affaires Administratives et Financières")

        story: list[Any] = []

        story.append(Paragraph("Article 4 : Obligations spécifiques", article_style))
        story.append(
            Paragraph(
                f"Sans préjudice des conditions générales citées à l'article 3, le Responsable de programme « {programme} » et le Responsable de Budget Opérationnel de Programme « {bop_title} », peuvent adopter des mesures spécifiques portant notamment sur la gestion des délais, les conditions sociales et les méthodes de prise de décisions.",
                body_style,
            )
        )
        story.append(
            Paragraph(
                "Les obligations spécifiques doivent être présentées dans les mêmes conditions que celles des obligations générales.",
                body_style,
            )
        )

        story.append(Paragraph("Article 5 : Obligations communes", article_style))
        story.append(
            Paragraph(
                "Les deux (2) parties, par la présente lettre, s'engagent à :",
                body_style,
            )
        )
        commons_bullets = [
            "coopérer à travers la communication et l'échange d'informations ;",
            "faire bon usage des informations échangées et de ne les diffuser à une tierce personne qu'après concertation.",
        ]
        for bullet in commons_bullets:
            story.append(Paragraph(bullet, bullet_style, bulletText="-"))

        story.append(Paragraph("Article 6 : Droits des parties", article_style))
        story.append(
            Paragraph(
                "Les droits des différentes parties sont ceux qui sont garantis par les textes en vigueur.",
                body_style,
            )
        )

        story.append(Paragraph("Article 7 : Suivi et évaluation de la lettre d'engagement opérationnel", article_style))
        story.append(
            Paragraph(
                "L'examen de l'état d'avancement dans la mise en œuvre des dispositions de la présente lettre d'engagement se fera par le biais de réunions mensuelles, assorties de compte-rendu.",
                body_style,
            )
        )
        story.append(
            Paragraph(
                "L'évaluation de la mise en œuvre de la lettre se fait à travers le Rapport d'activités trimestriel, produit au plus tard le 15 du mois suivant la fin du trimestre.",
                body_style,
            )
        )

        story.append(Paragraph("CHAPITRE II : DISPOSITIONS PARTICULIERES", chapter_style))

        story.append(Paragraph("Article 8 : Durée de la lettre d'engagement opérationnel", article_style))
        story.append(
            Paragraph(
                "La présente lettre d'engagement opérationnel est conclue pour une durée de un (1) an.",
                body_style,
            )
        )

        story.append(Paragraph("Article 9 : Conditions de résiliation", article_style))
        story.append(
            Paragraph(
                "La résiliation de la lettre d'engagement opérationnel intervient dans les cas ci-après :",
                body_style,
            )
        )
        termination_bullets = [
            "terme échu ;",
            "décès d'une des parties ;",
            "démission du Responsable de Budget Opérationnel de Programme ;",
            "faute de gestion du Responsable de Budget Opérationnel de Programme ;",
            "changement de la situation administrative d'une des parties ;",
            "non-respect des obligations au sens des articles 3 à 5 de la présente lettre.",
        ]
        for bullet in termination_bullets:
            story.append(Paragraph(bullet, bullet_style, bulletText="-"))

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
    def _draw_signature_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page de signatures et l'article 10 (page 6)."""
        pdf.saveState()

        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2.5 * cm
        available_width = width - left_margin - right_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Frame, Spacer
        from reportlab.lib.enums import TA_JUSTIFY

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

        story: list[Any] = []
        story.append(Paragraph("Article 10 : Date d'effet", article_style))
        story.append(
            Paragraph(
                "La présente lettre d'engagement opérationnel prend effet à compter de sa date de signature par les parties.",
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

        ville = cls.data.get("ville_signature", "Abidjan")
        pdf.setFont("Helvetica", 12)
        pdf.drawRightString(width - left_margin, height / 2 + 40, f"Fait à {ville}, le…………………………")

        # Zone de signature RBOP (gauche)
        bop_title = (cls.data.get("bop_intitule") or "Affaires Administratives et Financières").upper()
        rbop_nom = (cls.data.get("rbop_nom") or "Nom Prénom").upper()
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(left_margin + available_width * 0.25, height / 2 - 10, "Responsable de Budget Opérationnel de Programme")
        pdf.drawCentredString(left_margin + available_width * 0.25, height / 2 - 26, f"« {bop_title} »")
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(left_margin + available_width * 0.25, height / 2 - 90, rbop_nom)

        # Zone de signature RPROG (droite)
        programme = (cls.data.get("programme_intitule") or "ADMINISTRATION GENERALE").upper()
        rprog_nom = (cls.data.get("rprog_nom") or "Nom Prénom").upper()
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(left_margin + available_width * 0.75, height / 2 - 10, "Responsable du Programme")
        pdf.drawCentredString(left_margin + available_width * 0.75, height / 2 - 26, f"« {programme} »")
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(left_margin + available_width * 0.75, height / 2 - 90, rprog_nom)

        # Numéro de page
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 30, 25, "6")

        pdf.restoreState()

    @classmethod
    def _draw_annex_matrice_page(cls, pdf: canvas.Canvas, start_page: int) -> int:
        """Dessine la page d'annexe (matrice des activités) en orientation paysage.

        Args:
            pdf: Canvas courant.
            start_page: Numéro de page à afficher pour la première page de cette annexe.

        Returns:
            Numéro de page suivant à utiliser pour les annexes additionnelles.
        """
        page_width, page_height = landscape(A4)
        pdf.setPageSize((page_width, page_height))

        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm
        available_width = page_width - left_margin - right_margin
        available_height = page_height - top_margin - bottom_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Table, TableStyle

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            "AnnexHeader",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
        )
        section_style = ParagraphStyle(
            "AnnexSection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
        )
        column_header_style = ParagraphStyle(
            "AnnexColumnHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=12,
            alignment=1,
        )
        action_style = ParagraphStyle(
            "AnnexAction",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=12,
        )
        text_style = ParagraphStyle(
            "AnnexText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
        )
        total_style = ParagraphStyle(
            "AnnexTotal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=12,
            alignment=1,
        )

        actions_data = cls._get_annex_actions()

        head_rows = [
            [Paragraph("ANNEXE :", header_style)],
            [Paragraph("Annexe 1 : Matrice des activités du BOP-DAAF", section_style)],
        ]
        head_table = Table(head_rows, colWidths=[available_width])
        head_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        head_width, head_height = head_table.wrap(available_width, available_height)

        def draw_page_header(first_page: bool) -> tuple[float, float]:
            if not first_page:
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawRightString(page_width - 30, 25, str(draw_page_header.page_number))
                pdf.showPage()
                pdf.setPageSize((page_width, page_height))
                draw_page_header.page_number += 1

            head_table.drawOn(pdf, left_margin, page_height - top_margin - head_height)
            y_cursor = page_height - top_margin - head_height
            remaining = available_height - head_height
            return y_cursor, remaining

        draw_page_header.page_number = start_page
        y_cursor, remaining_height = draw_page_header(first_page=True)

        def render_table(table: Table) -> None:
            nonlocal y_cursor, remaining_height
            pending_tables = [table]
            while pending_tables:
                current = pending_tables.pop(0)
                width, height = current.wrap(available_width, remaining_height)

                if height <= remaining_height and height > 0:
                    current.drawOn(pdf, left_margin, y_cursor - height)
                    y_cursor -= height
                    remaining_height -= height
                    continue

                parts = current.split(available_width, remaining_height)
                if not parts:
                    y_cursor, remaining_height = draw_page_header(first_page=False)
                    pending_tables.insert(0, current)
                    continue

                first_part = parts[0]
                f_width, f_height = first_part.wrap(available_width, remaining_height)
                if f_height > 0:
                    first_part.drawOn(pdf, left_margin, y_cursor - f_height)
                    y_cursor -= f_height
                    remaining_height -= f_height
                y_cursor, remaining_height = draw_page_header(first_page=False)

                for extra_part in parts[1:]:
                    pending_tables.insert(0, extra_part)

        block_base_style = [
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        for action_index, action in enumerate(actions_data, start=1):
            block_rows = [
                [Paragraph("Actions / Activités", column_header_style)],
                [Paragraph(action["title"], action_style)],
            ]
            for activity_index, activity in enumerate(action["activities"], start=1):
                code_label = activity.get("code") or f"Activité {action_index}.{activity_index}"
                description = activity.get("description", "")
                text = f"<b>{code_label}</b> – {description}" if description else f"<b>{code_label}</b>"
                block_rows.append([Paragraph(text, text_style)])

            block_table = Table(block_rows, colWidths=[available_width], repeatRows=2)
            block_style = TableStyle(
                block_base_style
                + [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ffd966")),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f6b26b")),
                    ("ALIGN", (0, 1), (-1, 1), "LEFT"),
                    ("BACKGROUND", (0, 2), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
            block_table.setStyle(block_style)
            render_table(block_table)

        total_table = Table([[Paragraph("TOTAL", total_style)]], colWidths=[available_width])
        total_table.setStyle(
            TableStyle(
                block_base_style
                + [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#93c47d")),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ]
            )
        )
        render_table(total_table)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(page_width - 30, 25, str(draw_page_header.page_number))

        return draw_page_header.page_number + 1


    @classmethod
    def _get_annex_actions(cls) -> list[dict[str, Any]]:
        db_actions = cls._fetch_annex_actions_from_db()
        if db_actions:
            return db_actions
        cls.logger.debug("Aucune donnée d'annexe en base, utilisation du jeu statique par défaut")
        return cls.STATIC_ANNEX_ACTIONS

    @classmethod
    def _get_operational_results_annex(cls) -> list[dict[str, str]]:
        data = cls.data.get("annexe_operational_results")
        if isinstance(data, list) and data:
            return data
        return cls.STATIC_OPERATIONAL_RESULTS

    @classmethod
    def _fetch_annex_actions_from_db(cls) -> list[dict[str, Any]]:
        """Récupère dynamiquement les actions/activités depuis la base si disponible."""
        try:
            with Session(engine) as session:
                fiche_id = cls._resolve_annex_fiche_id(session)
                if not fiche_id:
                    cls.logger.debug("Impossible de résoudre la fiche technique pour l'annexe")
                    return []

                actions = session.exec(
                    select(ActionBudgetaire)
                    .where(ActionBudgetaire.fiche_technique_id == fiche_id)
                    .order_by(ActionBudgetaire.ordre, ActionBudgetaire.id)
                ).all()

                if not actions:
                    cls.logger.debug("Aucune action budgétaire trouvée pour la fiche %s", fiche_id)
                    return []

                annex_payload: list[dict[str, Any]] = []

                for idx, action in enumerate(actions, start=1):
                    services = session.exec(
                        select(ServiceBeneficiaire)
                        .where(ServiceBeneficiaire.action_id == action.id)
                        .order_by(ServiceBeneficiaire.ordre, ServiceBeneficiaire.id)
                    ).all()

                    service_ids = [srv.id for srv in services if srv.id is not None]
                    if not service_ids:
                        cls.logger.debug("Action %s sans service bénéficiaire", action.id)
                        continue

                    activities = session.exec(
                        select(ActiviteBudgetaire)
                        .where(ActiviteBudgetaire.service_beneficiaire_id.in_(service_ids))
                        .order_by(ActiviteBudgetaire.ordre, ActiviteBudgetaire.id)
                    ).all()

                    if not activities:
                        cls.logger.debug("Action %s sans activité budgétaire", action.id)
                        continue

                    service_map = {srv.id: srv for srv in services if srv.id is not None}
                    activities_payload: list[dict[str, Any]] = []

                    for activity_idx, activity in enumerate(activities, start=1):
                        code = (activity.code or "").strip()
                        if not code:
                            code = f"Activité {idx}.{activity_idx}"

                        description = (activity.libelle or "").strip()
                        service = service_map.get(activity.service_beneficiaire_id)
                        if service and service.libelle:
                            service_label = service.libelle.strip()
                            if service_label and service_label.lower() not in description.lower():
                                description = f"{description} ({service_label})" if description else service_label

                        activities_payload.append({"code": code, "description": description})

                    if not activities_payload:
                        continue

                    title = (action.libelle or "").strip()
                    if title:
                        title = f"Action {idx} : {title}"
                    else:
                        title = f"Action {idx}"

                    annex_payload.append({"title": title, "activities": activities_payload})

                return annex_payload

        except Exception as exc:
            cls.logger.error("Erreur lors de la récupération des actions d'annexe: %s", exc, exc_info=True)
            return []

    @classmethod
    def _resolve_annex_fiche_id(cls, session: Session) -> int | None:
        """Détermine la fiche technique à utiliser pour l'annexe."""
        explicit_fiche = cls.data.get("annexe_fiche_id")
        if explicit_fiche:
            fiche = session.get(FicheTechnique, explicit_fiche)
            if fiche:
                return fiche.id
            cls.logger.warning(
                "Fiche technique %s introuvable pour l'annexe, tentative de résolution automatique",
                explicit_fiche,
            )

        programme_id: int | None = None
        programme_code = cls.data.get("programme_code")
        programme_label = cls.data.get("programme_intitule")

        if programme_code:
            programme = session.exec(
                select(Programme).where(func.lower(Programme.code) == str(programme_code).lower())
            ).first()
            if programme:
                programme_id = programme.id

        if programme_id is None and programme_label:
            programme = session.exec(
                select(Programme).where(func.lower(Programme.libelle) == str(programme_label).lower())
            ).first()
            if programme:
                programme_id = programme.id

        if programme_id is None:
            cls.logger.debug("Programme introuvable pour l'annexe (%s / %s)", programme_code, programme_label)
            return None

        year = cls.data.get("annexe_year") or cls.data.get("annee")
        fiche_query = select(FicheTechnique).where(FicheTechnique.programme_id == programme_id)
        if year:
            try:
                fiche_query = fiche_query.where(FicheTechnique.annee_budget == int(year))
            except (TypeError, ValueError):
                pass

        fiche = session.exec(fiche_query.order_by(FicheTechnique.created_at.desc())).first()
        if fiche:
            return fiche.id

        cls.logger.debug(
            "Aucune fiche technique trouvée pour programme_id=%s et annee=%s", programme_id, year
        )
        return None


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

    @classmethod
    def _draw_annex_operational_results_page(cls, pdf: canvas.Canvas, start_page: int) -> int:
        """Dessine l'annexe opérationnelle (tableau des résultats) en orientation paysage.

        Args:
            pdf: Canvas courant.
            start_page: Numéro de page à utiliser pour la première page de cette annexe.

        Returns:
            Numéro de page suivant disponible.
        """

        page_width, page_height = landscape(A4)
        pdf.setPageSize((page_width, page_height))

        left_margin = 2 * cm
        right_margin = 2 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm
        available_width = page_width - left_margin - right_margin
        available_height = page_height - top_margin - bottom_margin

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, Table, TableStyle

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            "AnnexHeader2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
        )
        cell_style = ParagraphStyle(
            "AnnexCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
        )
        header_cell_style = ParagraphStyle(
            "AnnexHeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=1,
        )

        header_rows = [[Paragraph("Annexe 2 : Cadre de résultat opérationnel du BOP-DAAF", header_style)]]
        header_table = Table(header_rows, colWidths=[available_width])
        header_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        header_width, header_height = header_table.wrap(available_width, available_height)

        column_headers = [
            Paragraph("Activités", header_cell_style),
            Paragraph("Résultats attendus", header_cell_style),
            Paragraph("Indicateur d'activités", header_cell_style),
            Paragraph("Responsable d'activités (RUO)", header_cell_style),
        ]

        rows = [column_headers]
        for item in cls._get_operational_results_annex():
            rows.append(
                [
                    Paragraph(item.get("activite", ""), cell_style),
                    Paragraph(item.get("resultats", ""), cell_style),
                    Paragraph(item.get("indicateurs", ""), cell_style),
                    Paragraph(item.get("responsable", ""), cell_style),
                ]
            )

        col_widths = [
            available_width * 0.28,
            available_width * 0.27,
            available_width * 0.27,
            available_width * 0.18,
        ]

        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ffc000")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )

        def draw_page_header(first_page: bool) -> tuple[float, float]:
            if not first_page:
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawRightString(page_width - 30, 25, str(draw_page_header.page_number))
                pdf.showPage()
                pdf.setPageSize((page_width, page_height))
                draw_page_header.page_number += 1

            header_table.drawOn(pdf, left_margin, page_height - top_margin - header_height)
            y_cursor = page_height - top_margin - header_height - 8
            remaining = available_height - header_height - 8
            return y_cursor, remaining

        draw_page_header.page_number = start_page
        y_cursor, remaining_height = draw_page_header(first_page=True)

        pending_tables = [table]
        while pending_tables:
            current_table = pending_tables.pop(0)
            width, height = current_table.wrap(available_width, remaining_height)

            if height <= remaining_height and height > 0:
                current_table.drawOn(pdf, left_margin, y_cursor - height)
                y_cursor -= height
                remaining_height -= height
                continue

            parts = current_table.split(available_width, remaining_height)
            if not parts:
                y_cursor, remaining_height = draw_page_header(first_page=False)
                pending_tables.insert(0, current_table)
                continue

            first_part = parts[0]
            f_width, f_height = first_part.wrap(available_width, remaining_height)
            if f_height > 0:
                first_part.drawOn(pdf, left_margin, y_cursor - f_height)
                y_cursor -= f_height
                remaining_height -= f_height

            y_cursor, remaining_height = draw_page_header(first_page=False)
            for extra in parts[1:]:
                pending_tables.insert(0, extra)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(page_width - 30, 25, str(draw_page_header.page_number))

        return draw_page_header.page_number + 1


