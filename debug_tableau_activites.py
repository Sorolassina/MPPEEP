"""
Script de débogage pour le tableau des activités RPROG
Permet de tester la création du tableau et d'identifier les problèmes
"""

import sys
import logging
from io import BytesIO
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, LongTable, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_tableau.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def test_tableau_creation():
    """Teste la création du tableau avec différents scénarios"""
    
    logger.info("=" * 80)
    logger.info("🧪 TEST DE CRÉATION DU TABLEAU D'ACTIVITÉS")
    logger.info("=" * 80)
    
    # Dimensions de la page
    width, height = A4
    left_margin = 2 * cm
    right_margin = 2 * cm
    available_width = width - left_margin - right_margin
    
    # Largeurs des colonnes
    col_widths = [
        available_width * 0.22,  # Action/Activités
        available_width * 0.13,  # Structures responsables
        available_width * 0.18,  # Résultat attendu
        available_width * 0.18,  # Résultat opérationnel
        available_width * 0.15,  # Preuve de réalisation
        available_width * 0.14,  # Observations
    ]
    
    logger.info(f"📐 Largeurs des colonnes: {[f'{w:.2f}' for w in col_widths]}")
    logger.info(f"📐 Largeur totale: {sum(col_widths):.2f}")
    
    # Créer les styles
    styles = getSampleStyleSheet()
    
    para_style = styles['Normal']
    para_style.fontName = 'Helvetica'
    para_style.fontSize = 8
    para_style.leading = 10
    para_style.alignment = 0  # LEFT
    
    header_style = styles['Normal']
    header_style.fontName = 'Helvetica-Bold'
    header_style.fontSize = 9
    header_style.leading = 11
    header_style.alignment = 1  # CENTER
    
    def create_para(text, max_width=None):
        """Crée un Paragraph avec wrapping automatique"""
        if not text:
            return Paragraph("", para_style)  # ⚠️ TOUJOURS retourner un Paragraph
        text = str(text).strip()
        if not text:
            return Paragraph("", para_style)  # ⚠️ TOUJOURS retourner un Paragraph
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(text, para_style)
    
    def create_header_para(text, max_width=None):
        """Crée un Paragraph d'en-tête avec wrapping automatique"""
        if not text:
            return Paragraph("", header_style)  # ⚠️ TOUJOURS retourner un Paragraph
        text = str(text).strip()
        if not text:
            return Paragraph("", header_style)  # ⚠️ TOUJOURS retourner un Paragraph
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(text, header_style)
    
    # TEST 1: Tableau avec données de test
    logger.info("\n" + "=" * 80)
    logger.info("📋 TEST 1: Création d'un tableau avec données de test")
    logger.info("=" * 80)
    
    table_data = []
    
    # Ligne d'en-tête
    logger.info("✅ Ajout de la ligne d'en-tête")
    table_data.append([
        create_header_para("Action/Activités", col_widths[0]),
        create_header_para("Structures responsables", col_widths[1]),
        create_header_para("Résultat attendu", col_widths[2]),
        create_header_para("Résultat opérationnel", col_widths[3]),
        create_header_para("Preuve de réalisation", col_widths[4]),
        create_header_para("Observations", col_widths[5])
    ])
    
    # Vérifier les types
    logger.info(f"📊 Types des cellules d'en-tête: {[type(cell).__name__ for cell in table_data[0]]}")
    
    # Ajouter quelques lignes de données de test
    test_data = [
        ("Action 1", "Activité 1.1", "Structure A", "Résultat 1", "Opérationnel 1", "Preuve 1", "Observation 1"),
        ("Action 1", "Activité 1.2", "Structure B", "Résultat 2", "Opérationnel 2", "Preuve 2", "Observation 2"),
        ("Action 2", "Activité 2.1", "Structure C", "Résultat 3", "Opérationnel 3", "Preuve 3", "Observation 3"),
    ]
    
    # Grouper par action
    activites_par_action = {}
    for action, activite, struct, res_att, res_op, preuve, obs in test_data:
        if action not in activites_par_action:
            activites_par_action[action] = []
        activites_par_action[action].append({
            "action": action,
            "activite": activite,
            "structures_responsables": struct,
            "resultat_attendu": res_att,
            "resultat_operationnel": res_op,
            "preuve_realisation": preuve,
            "observations": obs,
        })
    
    logger.info(f"📊 {len(activites_par_action)} groupes d'actions créés")
    
    current_row = 1
    for action_key, activites in activites_par_action.items():
        # Ligne d'en-tête de groupe (action)
        logger.info(f"✅ Ajout de la ligne d'en-tête pour l'action: '{action_key}'")
        merged_width = col_widths[0] + col_widths[1] + col_widths[2]
        header_text = f"{action_key}"
        
        # ⚠️ UTILISER DES PARAGRAPH VIDES POUR LES CELLULES VIDES
        empty_para = create_para("")
        table_data.append([
            create_para(header_text, merged_width),
            empty_para,  # Colonne 1 (vide car fusionnée)
            empty_para,  # Colonne 2 (vide car fusionnée)
            empty_para,  # Colonne 3
            empty_para,  # Colonne 4
            empty_para,  # Colonne 5
        ])
        logger.info(f"   Types des cellules: {[type(cell).__name__ for cell in table_data[-1]]}")
        
        # Lignes d'activités
        for activite in activites:
            logger.info(f"   ✅ Ajout de l'activité: '{activite['activite']}'")
            table_data.append([
                create_para(activite["activite"], col_widths[0]),
                create_para(activite["structures_responsables"], col_widths[1]),
                create_para(activite["resultat_attendu"], col_widths[2]),
                create_para(activite["resultat_operationnel"], col_widths[3]),
                create_para(activite["preuve_realisation"], col_widths[4]),
                create_para(activite["observations"], col_widths[5]),
            ])
            logger.info(f"      Types des cellules: {[type(cell).__name__ for cell in table_data[-1]]}")
    
    logger.info(f"\n📊 Total: {len(table_data)} lignes créées")
    
    # Vérifier que toutes les lignes ont le bon nombre de colonnes
    num_cols = len(col_widths)
    for idx, row in enumerate(table_data):
        if len(row) != num_cols:
            logger.error(f"❌ ERREUR: Ligne {idx} a {len(row)} colonnes au lieu de {num_cols}")
            logger.error(f"   Types: {[type(cell).__name__ for cell in row]}")
        else:
            # Vérifier les types
            types_in_row = [type(cell).__name__ for cell in row]
            if "str" in types_in_row and "Paragraph" in types_in_row:
                logger.warning(f"⚠️ Ligne {idx} a des types mixtes (str et Paragraph): {types_in_row}")
            elif "str" in types_in_row:
                logger.warning(f"⚠️ Ligne {idx} contient des chaînes: {types_in_row}")
    
    # Créer le LongTable
    logger.info("\n" + "=" * 80)
    logger.info("🔨 Création du LongTable")
    logger.info("=" * 80)
    
    try:
        table = LongTable(table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
        logger.info(f"✅ LongTable créé avec succès")
        logger.info(f"   - Nombre de lignes: {len(table._cellvalues)}")
        logger.info(f"   - Nombre de colonnes: {len(table._colWidths)}")
    except Exception as e:
        logger.error(f"❌ ERREUR lors de la création du LongTable: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    # Créer le style
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
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    
    # Ajouter les styles pour les lignes d'en-tête de groupe
    current_row = 1
    for action_key, activites in activites_par_action.items():
        if len(activites) > 0:
            table_style.append(("SPAN", (0, current_row), (2, current_row)))
            table_style.append(("BACKGROUND", (0, current_row), (2, current_row), colors.HexColor("#F5F5F5")))
            table_style.append(("FONTNAME", (0, current_row), (2, current_row), "Helvetica-Bold"))
            table_style.append(("FONTSIZE", (0, current_row), (2, current_row), 9))
            table_style.append(("ALIGN", (0, current_row), (2, current_row), "LEFT"))
            current_row += 1
            current_row += len(activites)
    
    try:
        table.setStyle(TableStyle(table_style))
        logger.info(f"✅ Style appliqué avec succès ({len(table_style)} règles)")
    except Exception as e:
        logger.error(f"❌ ERREUR lors de l'application du style: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    # TEST 2: Rendu dans un PDF de test
    logger.info("\n" + "=" * 80)
    logger.info("📄 TEST 2: Rendu dans un PDF de test")
    logger.info("=" * 80)
    
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    
    # Créer une story
    story = []
    story.append(Paragraph("TEST DU TABLEAU D'ACTIVITÉS", ParagraphStyle(
        "TestTitle",
        parent=styles['Heading1'],
        fontName="Helvetica-Bold",
        fontSize=16,
        alignment=0,
    )))
    story.append(Spacer(1, 0.5 * cm))
    story.append(table)
    
    # Rendre la story
    from reportlab.platypus import Frame
    from reportlab.platypus.doctemplate import LayoutError
    
    top_margin = 2 * cm
    bottom_margin = 2 * cm
    frame_x = left_margin
    frame_y = bottom_margin
    frame_width = available_width
    frame_height = height - top_margin - bottom_margin
    
    logger.info(f"📐 Frame: x={frame_x}, y={frame_y}, width={frame_width}, height={frame_height}")
    
    frame = Frame(frame_x, frame_y, frame_width, frame_height, showBoundary=0)
    
    try:
        logger.info("🔄 Tentative de rendu...")
        pdf.saveState()
        frame.addFromList(story, pdf)
        pdf.restoreState()
        logger.info("✅ Rendu réussi!")
    except LayoutError as e:
        logger.error(f"❌ LayoutError: {e}")
        pdf.restoreState()
        return False
    except Exception as e:
        logger.error(f"❌ Exception: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        pdf.restoreState()
        return False
    
    pdf.showPage()
    pdf.save()
    
    # Sauvegarder le PDF de test
    with open("test_tableau_activites.pdf", "wb") as f:
        f.write(buffer.getvalue())
    
    logger.info("✅ PDF de test créé: test_tableau_activites.pdf")
    logger.info("=" * 80)
    logger.info("✅ TOUS LES TESTS SONT PASSÉS")
    logger.info("=" * 80)
    
    return True


if __name__ == "__main__":
    success = test_tableau_creation()
    sys.exit(0 if success else 1)

