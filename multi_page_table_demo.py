from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm


def build_pdf(filename: str = "tableau_multi_pages.pdf") -> None:
    """
    Génère un PDF avec un tableau (LongTable) qui se répartit automatiquement
    sur plusieurs pages, avec répétition de l'entête.
    """
    # 👉 Document en paysage (comme ton cas)
    page_width, page_height = landscape(A4)

    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # --------- Titre du document ----------
    story.append(Paragraph("Exemple de tableau multi-pages avec ReportLab", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph(
        "Ce document illustre un <b>LongTable</b> qui se découpe automatiquement "
        "sur plusieurs pages, avec l'entête répétée à chaque page.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5 * cm))

    # --------- Données du tableau ----------
    # En-tête
    header = [
        "N°",
        "Libellé",
        "Colonne 3",
        "Colonne 4",
        "Colonne 5",
        "Colonne 6"
    ]

    data = [header]

    # Générer beaucoup de lignes pour forcer plusieurs pages
    for i in range(1, 200):
        data.append([
            str(i),
            f"Ligne de test numéro {i} avec un libellé un peu long pour voir le wrapping.",
            f"Valeur {i}-3",
            f"Valeur {i}-4",
            f"Valeur {i}-5",
            f"Valeur {i}-6",
        ])

    # Largeurs de colonnes (adaptées à la largeur utilisable)
    available_width = page_width - doc.leftMargin - doc.rightMargin
    col_widths = [
        available_width * 0.07,   # N°
        available_width * 0.38,   # Libellé
        available_width * 0.11,   # Col 3
        available_width * 0.11,   # Col 4
        available_width * 0.16,   # Col 5
        available_width * 0.17,   # Col 6
    ]

    # --------- Création du LongTable ----------
    table = LongTable(
        data,
        colWidths=col_widths,
        repeatRows=1,  # répète la première ligne (header) à chaque page
        splitByRow=1,  # permet de couper proprement par lignes
    )

    table_style = TableStyle([
        # Grille générale
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

        # En-tête
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),

        # Corps du tableau
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),

        # Alignements spécifiques
        ("ALIGN", (0, 1), (0, -1), "CENTER"),   # N°
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),   # Colonnes numériques

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])

    table.setStyle(table_style)

    # Titre du tableau
    story.append(Paragraph("<b>Tableau 1 : Exemple d'exécution budgétaire</b>", styles["Heading3"]))
    story.append(Spacer(1, 0.2 * cm))

    # On ajoute la table à la story → SimpleDocTemplate gère la pagination
    story.append(table)

    # Un petit texte après le tableau (pour montrer que ça continue)
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Texte ajouté après le tableau pour montrer que la génération se poursuit "
        "même après plusieurs pages de table.",
        styles["Normal"]
    ))

    # --------- Fonctions de numérotation de pages ----------
    def _on_page(canvas, doc_obj):
        # Numéro de page en bas à droite
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        text = f"Page {doc_obj.page}"
        canvas.drawRightString(page_width - 2 * cm, 1.0 * cm, text)
        canvas.restoreState()

    # Build du document
    doc.build(
        story,
        onFirstPage=_on_page,
        onLaterPages=_on_page,
    )

    print(f"✅ PDF généré : {filename}")


if __name__ == "__main__":
    build_pdf()
