from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def draw_checkbox(c, x, y, size=0.5*cm, checked=False):
    """Dessine une case à cocher à la position (x, y)."""
    c.rect(x, y, size, size)
    if checked:
        c.setLineWidth(2)
        c.line(x + 2, y + 2, x + size - 2, y + size - 2)
        c.line(x + 2, y + size - 2, x + size - 2, y + 2)
        c.setLineWidth(1)


def generate_fiche_indicateur(output_path: str, data: dict | None = None):
    """
    Génère une fiche signalétique d'indicateur.

    :param output_path: chemin du fichier PDF de sortie.
    :param data: dict optionnel avec les valeurs à injecter.
    """

    # Données par défaut (tu peux les adapter)
    default_data = {
        "ministere": "Ministère du Patrimoine, du Portefeuille de l’Etat et des Entreprises Publiques",
        "programme": "Administration Générale",
        "objectif": "OS 1 : Améliorer le cadre institutionnel du Ministère",
        "libelle_indicateur": "Taux de réalisation du PAS du programme Administration Générale",
        "definition": (
            "Cet indicateur permet d’évaluer le niveau de réalisation des activités des "
            "structures relevant du Cabinet du Ministre."
        ),
        "nature_qualitatif": False,
        "nature_quantitatif": True,
        "methode_calcul": "(Nombre d’activités du PAS du programme réalisées / nombre total "
                          "d’activités du PAS du programme prévues) x 100",
        "mode_routine": True,
        "mode_enquete": False,
        "mode_autre": False,
        "mode_autre_texte": "",
        "provenance_donnees": "Cabinet/DAF",
        "responsable_collecte": "Cabinet",
        "unite": "%",
        "periodicite_mensuelle": False,
        "periodicite_trimestrielle": False,
        "periodicite_semestrielle": True,
        "periodicite_annuelle": False,
        "derniere_valeur": "-",
        "cibles": {
            2026: "80",
            2027: "80",
            2028: "80",
        },
        "responsable_programme": "Administration Générale",
        "nom_responsable": "Monsieur SALL Adama",
        "signature": "",
    }

    if data:
        # on écrase les valeurs par défaut avec celles fournies
        for k, v in data.items():
            if k == "cibles":
                default_data["cibles"].update(v)
            else:
                default_data[k] = v

    d = default_data

    # Création du canvas
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # Marges
    left_margin = 1.5 * cm
    right_margin = 1.5 * cm
    top_margin = 1.5 * cm
    bottom_margin = 1.5 * cm

    # Zone principale
    x0 = left_margin
    y0 = bottom_margin
    w = width - left_margin - right_margin
    h = height - top_margin - bottom_margin

    # Cadre extérieur
    c.setLineWidth(1)
    c.rect(x0, y0, w, h)

    # Titre vert
    title_height = 1.2 * cm
    c.setFillColor(colors.lightgreen)
    c.rect(x0, height - top_margin - title_height, w, title_height, fill=1, stroke=1)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x0 + w / 2, height - top_margin - title_height / 2 - 4,
                        "FICHE SIGNALETIQUE D’INDICATEUR")

    # On travaille avec un curseur vertical (y) à l’intérieur du cadre
    current_y = height - top_margin - title_height - 0.4 * cm
    left_text = x0 + 0.4 * cm

    def draw_ligne_numero(num, texte, valeur, extra_y=0):
        nonlocal current_y
        box_height = 0.9 * cm + extra_y
        c.rect(x0, current_y - box_height, w, box_height, stroke=1, fill=0)
        c.setFont("Helvetica", 8.5)
        c.drawString(left_text, current_y - 0.3 * cm, f"{num}. {texte}")
        if valeur:
            c.setFont("Helvetica", 8)
            c.drawString(left_text + 2.5 * cm, current_y - 0.3 * cm, valeur)
        current_y -= box_height

    # 1. Ministère
    draw_ligne_numero(1, "Ministère :", d["ministere"])

    # 2. Programme
    draw_ligne_numero(2, "Programme 1 :", d["programme"])

    # 3. Objectif spécifique
    draw_ligne_numero(3, "Objectif spécifique :", d["objectif"])

    # 4. Libellé de l’indicateur
    draw_ligne_numero(4, "Libellé de l’indicateur :", d["libelle_indicateur"], extra_y=0.2 * cm)

    # 5. Définition de l’indicateur (bloc multiligne)
    # cadre pour le numéro + titre
    box5_title_h = 0.7 * cm
    c.rect(x0, current_y - box5_title_h - 2.0 * cm, w, box5_title_h + 2.0 * cm, stroke=1, fill=0)
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, current_y - 0.3 * cm, "5. Définition de l’indicateur")
    # Texte dans cadre
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    pstyle = styles["Normal"]
    pstyle.fontName = "Helvetica"
    pstyle.fontSize = 8
    pstyle.leading = 10
    p = Paragraph(d["definition"], pstyle)
    tw = w - 0.8 * cm
    aw = tw
    ah = 2.0 * cm - 0.3 * cm
    pw, ph = p.wrap(aw, ah)
    p.drawOn(c, left_text, current_y - box5_title_h - ph - 0.1 * cm)
    current_y -= (box5_title_h + 2.0 * cm)

    # 6. Nature de l’indicateur
    box6_h = 1.3 * cm
    c.rect(x0, current_y - box6_h, w, box6_h, stroke=1, fill=0)
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, current_y - 0.3 * cm, "6. Nature de l’indicateur")
    # cases 6.1 & 6.2
    c.drawString(left_text + 3.5 * cm, current_y - 0.3 * cm, "6.1. Qualitatif")
    draw_checkbox(c, left_text + 6.7 * cm, current_y - 0.65 * cm,
                  checked=d["nature_qualitatif"])
    c.drawString(left_text + 9.0 * cm, current_y - 0.3 * cm, "6.2. Quantitatif")
    draw_checkbox(c, left_text + 12.4 * cm, current_y - 0.65 * cm,
                  checked=d["nature_quantitatif"])
    current_y -= box6_h

    # 7. Méthode de calcul
    box7_title_h = 0.7 * cm
    inner_h = 2.0 * cm
    c.rect(x0, current_y - box7_title_h - inner_h, w, box7_title_h + inner_h, stroke=1, fill=0)
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, current_y - 0.3 * cm, "7. Méthode de calcul de l’indicateur")
    p2 = Paragraph(d["methode_calcul"], pstyle)
    pw, ph = p2.wrap(w - 0.8 * cm, inner_h - 0.4 * cm)
    p2.drawOn(c, left_text, current_y - box7_title_h - ph - 0.1 * cm)
    current_y -= (box7_title_h + inner_h)

    # 8. Sources de données
    box8_title_h = 0.7 * cm
    total_h_8 = box8_title_h + 2.4 * cm
    c.rect(x0, current_y - total_h_8, w, total_h_8, stroke=1, fill=0)
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, current_y - 0.3 * cm, "8. Sources de données")
    line_y = current_y - box8_title_h - 0.4 * cm

    # 8.1 Mode de collecte
    c.drawString(left_text, line_y, "8.1. Mode de collecte des données :")
    c.drawString(left_text + 5.5 * cm, line_y, "Routine")
    draw_checkbox(c, left_text + 7.5 * cm, line_y - 0.25 * cm,
                  checked=d["mode_routine"])
    c.drawString(left_text + 9.2 * cm, line_y, "Enquête")
    draw_checkbox(c, left_text + 11.0 * cm, line_y - 0.25 * cm,
                  checked=d["mode_enquete"])
    c.drawString(left_text + 12.8 * cm, line_y, "Autre à préciser :")
    # petite ligne de texte libre
    c.line(left_text + 16.5 * cm, line_y - 0.1 * cm, x0 + w - 0.4 * cm, line_y - 0.1 * cm)

    # 8.2 Provenance
    line_y -= 0.8 * cm
    c.drawString(left_text, line_y, "8.2. Provenance des données :")
    c.setFont("Helvetica", 8)
    c.drawString(left_text + 5.5 * cm, line_y, d["provenance_donnees"])

    # 8.3 Responsable de la collecte
    line_y -= 0.7 * cm
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, line_y, "8.3. Responsable de la collecte des données :")
    c.setFont("Helvetica", 8)
    c.drawString(left_text + 7.3 * cm, line_y, d["responsable_collecte"])

    current_y -= total_h_8

    # 9. Valeur de l’indicateur
    box9_title_h = 0.7 * cm
    total_h_9 = box9_title_h + 2.4 * cm
    c.rect(x0, current_y - total_h_9, w, total_h_9, stroke=1, fill=0)
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, current_y - 0.3 * cm, "9. Valeur de l’indicateur")
    line_y = current_y - box9_title_h - 0.4 * cm

    # 9.1 Unité de mesure
    c.drawString(left_text, line_y, "9.1. Unité de mesure")
    # petite case texte
    c.rect(left_text + 4.0 * cm, line_y - 0.3 * cm, 1.5 * cm, 0.7 * cm)
    c.setFont("Helvetica", 8)
    c.drawCentredString(left_text + 4.0 * cm + 0.75 * cm, line_y - 0.05 * cm, d["unite"])

    # 9.2 Périodicité
    line_y -= 0.8 * cm
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, line_y, "9.2. Périodicité :")
    c.drawString(left_text + 4.0 * cm, line_y, "Mensuelle")
    draw_checkbox(c, left_text + 7.1 * cm, line_y - 0.25 * cm,
                  checked=d["periodicite_mensuelle"])
    c.drawString(left_text + 8.5 * cm, line_y, "Trimestrielle")
    draw_checkbox(c, left_text + 12.0 * cm, line_y - 0.25 * cm,
                  checked=d["periodicite_trimestrielle"])
    line_y -= 0.7 * cm
    c.drawString(left_text + 4.0 * cm, line_y, "Semestrielle")
    draw_checkbox(c, left_text + 7.4 * cm, line_y - 0.25 * cm,
                  checked=d["periodicite_semestrielle"])
    c.drawString(left_text + 8.8 * cm, line_y, "Annuelle")
    draw_checkbox(c, left_text + 11.2 * cm, line_y - 0.25 * cm,
                  checked=d["periodicite_annuelle"])

    # 9.3 Dernière valeur connue
    line_y -= 0.8 * cm
    c.drawString(left_text, line_y, "9.3. Dernière valeur connue :")
    c.rect(left_text + 5.5 * cm, line_y - 0.3 * cm, 2.0 * cm, 0.7 * cm)
    c.setFont("Helvetica", 8)
    c.drawCentredString(left_text + 6.5 * cm, line_y - 0.05 * cm, d["derniere_valeur"])

    # 9.4 Cible fixée (ligne de cases pour années)
    line_y -= 0.8 * cm
    c.setFont("Helvetica", 8.5)
    c.drawString(left_text, line_y, "9.4. Cible fixée :")
    start_x = left_text + 4.0 * cm
    for year in sorted(d["cibles"].keys()):
        c.setFont("Helvetica", 8)
        c.drawString(start_x, line_y, str(year))
        c.rect(start_x + 2.2 * cm, line_y - 0.3 * cm, 1.4 * cm, 0.7 * cm)
        c.drawCentredString(start_x + 2.2 * cm + 0.7 * cm,
                            line_y - 0.05 * cm, d["cibles"][year])
        start_x += 4.2 * cm

    current_y -= total_h_9

    # Bande signature en bas
    footer_h = 2.0 * cm
    c.rect(x0, y0, w, footer_h, stroke=1, fill=0)

    col_w = w / 3.0
    # Responsables
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(x0 + col_w / 2, y0 + footer_h - 0.5 * cm,
                        "Responsable de Programme :")
    c.drawCentredString(x0 + 1.5 * col_w, y0 + footer_h - 0.5 * cm,
                        "Nom et prénoms :")
    c.drawCentredString(x0 + 2.5 * col_w, y0 + footer_h - 0.5 * cm,
                        "Signature")

    # Lignes de texte
    c.setFont("Helvetica", 8)
    c.drawCentredString(x0 + col_w / 2, y0 + 0.6 * cm, d["responsable_programme"])
    c.drawCentredString(x0 + 1.5 * col_w, y0 + 0.6 * cm, d["nom_responsable"])
    # zone de signature = vide

    # Numéro de page en bas à droite (optionnel)
    c.setFont("Helvetica", 8)
    c.drawRightString(width - right_margin, bottom_margin - 0.5 * cm, "1")

    c.showPage()
    c.save()


if __name__ == "__main__":
    generate_fiche_indicateur("fiche_indicateur_exemple.pdf")
    print("PDF généré : fiche_indicateur_exemple.pdf")
