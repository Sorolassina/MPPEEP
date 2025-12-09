#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
longtable_demo.py

Exemple minimal pour générer un PDF contenant un LongTable
multi-pages avec ReportLab (en-tête répété + numérotation de pages).
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    LongTable,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet


def _add_page_number(canvas, doc):
    """
    Callback pour ajouter le numéro de page en pied de page.
    Utilisé par SimpleDocTemplate (onFirstPage / onLaterPages).
    """
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"

    canvas.saveState()
    canvas.setFont("Helvetica", 9)

    # Position en bas à droite
    width, height = A4
    x = width - 2 * cm
    y = 1.5 * cm
    canvas.drawRightString(x, y, text)

    canvas.restoreState()


def build_longtable_pdf(filename: str = "longtable_demo.pdf"):
    """
    Construit un PDF simple contenant un LongTable qui se découpe
    automatiquement sur plusieurs pages.
    """
    # Styles de texte
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_title = styles["Title"]

    # Création du document
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    story = []

    # Titre
    story.append(Paragraph("Démonstration d'un LongTable multi-pages", style_title))
    story.append(Spacer(1, 0.5 * cm))

    story.append(
        Paragraph(
            "Ce tableau est un LongTable. Il se découpe automatiquement sur plusieurs "
            "pages et répète la ligne d'en-tête.", style_normal
        )
    )
    story.append(Spacer(1, 0.8 * cm))

    # ----------------------------
    # 1) Construction des données
    # ----------------------------

    # En-tête
    data = [
        [
            "ID",
            "Nom de l'activité",
            "Catégorie",
            "Budget initial",
            "Budget exécuté",
            "Taux d'exécution (%)",
        ]
    ]

    # Lignes de données (on en met suffisamment pour forcer plusieurs pages)
    for i in range(1, 121):  # ~120 lignes pour être sûr de dépasser une page
        data.append(
            [
                str(i),
                f"Activité n°{i} - Libellé relativement long pour tester le wrapping",
                "Fonctionnement" if i % 2 == 0 else "Investissement",
                f"{100000 + i * 100:,.0f}".replace(",", " "),
                f"{80000 + i * 80:,.0f}".replace(",", " "),
                f"{(80 + i % 20):.1f}",
            ]
        )

    # Largeurs de colonnes (adaptées à la largeur de page A4 - marges)
    page_width, page_height = A4
    available_width = page_width - doc.leftMargin - doc.rightMargin

    col_widths = [
        available_width * 0.08,  # ID
        available_width * 0.32,  # Nom de l'activité
        available_width * 0.18,  # Catégorie
        available_width * 0.14,  # Budget initial
        available_width * 0.14,  # Budget exécuté
        available_width * 0.14,  # Taux %
    ]

    # ----------------------------
    # 2) Création du LongTable
    # ----------------------------

    table = LongTable(
        data,
        colWidths=col_widths,
        repeatRows=1,   # répéter la 1ère ligne (l'en-tête) sur chaque page
        splitByRow=1,   # autoriser le découpage par ligne
    )

    # Style du tableau
    table_style = TableStyle(
        [
            # Grille
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

            # En-tête
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#deeaf6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),

            # Corps du tableau
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),

            # Alignement spécifique
            ("ALIGN", (0, 1), (0, -1), "CENTER"),  # ID centré
            ("ALIGN", (3, 1), (5, -1), "RIGHT"),   # montants + taux à droite

            # Padding
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )

    table.setStyle(table_style)

    # Ajout du tableau à la story
    story.append(table)

    # Un petit espace après le tableau (optionnel)
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Fin du LongTable. Si vous voyez plusieurs pages avec l'en-tête répété et les numéros de page en bas, "
            "c'est que tout fonctionne correctement.",
            style_normal,
        )
    )

    # ----------------------------
    # 3) Génération du PDF
    # ----------------------------

    doc.build(
        story,
        onFirstPage=_add_page_number,
        onLaterPages=_add_page_number,
    )

    print(f"✅ PDF généré : {filename}")


if __name__ == "__main__":
    build_longtable_pdf()
