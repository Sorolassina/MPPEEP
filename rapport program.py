@classmethod
    def _draw_partie_programme(cls, pdf: canvas.Canvas, width: float, height: float, start_page: int, programme: dict[str, Any]) -> int:
        """
        Dessine une partie pour un programme donné avec support multi-pages.
        Structure standardisée qui sera identique pour tous les programmes.
        
        Args:
            pdf: Canvas ReportLab
            width: Largeur de la page (paysage)
            height: Hauteur de la page (paysage)
            start_page: Numéro de la page de départ
            programme: Dictionnaire contenant les données du programme
                - numero: Numéro du programme (1, 2, 3, ...)
                - titre: Titre du programme
                - autres données du programme...
        
        Returns:
            Numéro de la dernière page générée
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Récupérer les données du programme
        numero = programme.get("numero", 1)
        titre = programme.get("titre", "")
        
        # Marges et dimensions
        left_margin = 2.5 * cm
        right_margin = 2.5 * cm
        top_margin = 2.5 * cm
        footer_height = 1.5 * cm
        footer_margin = 0.5 * cm
        bottom_margin = footer_height + footer_margin  # Espace pour le footer en bas
        available_width = width - left_margin - right_margin
        available_height = height - top_margin - bottom_margin
        
        # Récupérer les styles
        styles = getSampleStyleSheet()
        
        # Créer des styles personnalisés similaires à ceux de la PARTIE I
        partie_title_style = ParagraphStyle(
            "PartieTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=0,  # Gauche
            spaceAfter=12,
            textColor=colors.HexColor("#0066CC"),  # Bleu
        )
        
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=0,  # Gauche
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#000000"),  # Noir
            keepWithNext=1,
        )
        
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=0,  # Gauche
            spaceBefore=6,
            spaceAfter=4,
            textColor=colors.HexColor("#000000"),  # Noir
            keepWithNext=1,  # Évite que le titre soit orphelin
        )
        
        # Style spécial pour les titres de sous-sections suivis d'un tableau
        # permet au titre de rester avec au moins le début du tableau
        subsection_title_with_table_style = ParagraphStyle(
            "SubsectionTitleWithTable",
            parent=styles["Normal"],  # Utiliser Normal au lieu de Heading3 pour éviter les espacements par défaut
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=0,  # Gauche
            spaceBefore=6,
            spaceAfter=4,  # Léger espace après le titre avant le tableau
            textColor=colors.HexColor("#000000"),  # Noir
            keepWithNext=0,  # Pas de keepWithNext pour permettre au tableau de commencer sur la même page
            firstLineIndent=0,
        )
        
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=4,  # Justifié
            spaceAfter=6,
        )
        
        source_style = ParagraphStyle(
            "Source",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            alignment=2,  # Droite
            spaceBefore=4,
            spaceAfter=4,
        )
        
        # Styles pour les tableaux (similaires à ceux de la partie III)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=2,
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_cell_center_style = ParagraphStyle(
            "TableCellCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            alignment=TA_CENTER,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_cell_right_style = ParagraphStyle(
            "TableCellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            alignment=TA_RIGHT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_subheader_style = ParagraphStyle(
            "TableSubheader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=TA_LEFT,
            spaceBefore=1,
            spaceAfter=1,
        )
        table_total_style = ParagraphStyle(
            "TableTotal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,
            alignment=TA_LEFT,
            spaceBefore=2,
            spaceAfter=2,
        )
        
        # Fonction pour formater les montants en FCFA
        def format_fcfa(montant: float) -> str:
            """Formate un montant en FCFA avec séparateurs de milliers."""
            if montant == 0:
                return "0"
            montant_str = f"{int(montant):,}".replace(",", " ")
            return montant_str
        
        # Fonction pour dessiner le footer avec numéro de page
        def draw_footer(page_num: int) -> None:
            """Dessine le footer avec le numéro de page."""
            card_size = 1.0 * cm
            corner_size = 0.3 * cm
            card_x = width - right_margin - card_size
            card_y = bottom_margin - footer_margin
            
            # Dessiner la carte
            pdf.saveState()
            pdf.setFillColor(colors.white)
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            pdf.setLineWidth(0.5)
            pdf.roundRect(card_x, card_y, card_size, card_size, 0.2 * cm, fill=1, stroke=1)
            
            # Coin supérieur droit enroulé
            corner_path = pdf.beginPath()
            corner_path.moveTo(card_x + card_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size - corner_size, card_y + card_size)
            corner_path.lineTo(card_x + card_size, card_y + card_size - corner_size)
            corner_path.close()
            pdf.setFillColor(colors.HexColor("#F0F0F0"))
            pdf.setStrokeColor(colors.HexColor("#E0E0E0"))
            pdf.drawPath(corner_path, fill=1, stroke=1)
            
            # Numéro de page
            pdf.setFillColor(colors.black)
            pdf.setFont("Helvetica", 10)
            text_width = pdf.stringWidth(str(page_num), "Helvetica", 10)
            text_x = card_x + (card_size - text_width) / 2
            text_y = card_y + (card_size - 10) / 2
            pdf.drawString(text_x, text_y, str(page_num))
            pdf.restoreState()
        
        # Construire la story pour cette partie programme
        story: list[Any] = []
        
        # Déterminer le numéro de la partie (PARTIE II, III, IV, etc.)
        # La PARTIE I est "LE MINISTÈRE", donc les programmes commencent à PARTIE II
        partie_numero_romain = cls._number_to_roman(numero + 1)  # +1 car PARTIE I est le ministère
        
        # Titre de la partie
        story.append(Paragraph(f"PARTIE {partie_numero_romain} : LE PROGRAMME {numero} « {titre.upper()} »", partie_title_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Récupérer les données du programme depuis cls.data
        programme_data = programme  # Le programme est déjà passé en paramètre
        
        # Valeurs par défaut pour les données du programme
        annee = cls.data.get("annee", 2024)
        
        # Valeurs par défaut selon le programme
        default_intro_data = {
            1: {  # Programme 1: Administration Générale
                "responsable_nom": "Monsieur SALL Adama",
                "responsable_fonction": "Directeur de Cabinet du MBPE",
                "decret_nomination": "décret n° 2023-956 du 06 décembre 2023 portant nomination des Directeurs de Cabinets ministériels",
                "decret_designation": "le décret n° 2023_337 du 19 avril 2023 portant désignation des Responsables de programme des ministères",
                "missions": [
                    "La coordination, l'animation et la supervision des activités du Ministère;",
                    "La coordination des informations et des communications du Ministère;",
                    "La gestion des ressources humaines, matérielles et financières."
                ],
                "contexte": (
                    f"En {annee}, les activités du Programme « {titre} » se sont déroulées dans un environnement économique "
                    f"international relativement stable, mais également marqué par d'importants ajustements institutionnels. Ces derniers "
                    f"ont été impulsés par la mise en œuvre du décret n°2023-963 du 6 décembre 2023 portant organisation du ministère. "
                    f"Acteur clé de la dynamique des réformes institutionnelles, le Programme « {titre} » s'est affirmé comme un pilier "
                    f"structurant, en appui au bon fonctionnement des services du ministère et en contribuant de manière significative "
                    f"au renforcement de sa gouvernance."
                ),
                "structure_rapport": [
                    "la présentation de la stratégie du programme;",
                    "les réalisations du programme au cours de l'exercice 2024;",
                    "la performance du programme;",
                    "les perspectives."
                ]
            },
            2: {  # Programme 2: Portefeuille de l'Etat (valeurs par défaut génériques)
                "responsable_nom": "",
                "responsable_fonction": "Responsable de Programme",
                "decret_nomination": "décret",
                "decret_designation": "le décret",
                "missions": [],
                "contexte": "",
                "structure_rapport": [
                    "la présentation de la stratégie du programme;",
                    "les réalisations du programme au cours de l'exercice 2024;",
                    "la performance du programme;",
                    "les perspectives."
                ]
            }
        }
        
        # Utiliser les données du programme ou les valeurs par défaut
        intro_data = default_intro_data.get(numero, default_intro_data[2])  # Utiliser programme 2 comme fallback
        responsable_nom = programme_data.get("responsable_nom", intro_data.get("responsable_nom", ""))
        responsable_fonction = programme_data.get("responsable_fonction", intro_data.get("responsable_fonction", "Responsable de Programme"))
        decret_nomination = programme_data.get("decret_nomination", intro_data.get("decret_nomination", "décret"))
        decret_designation = programme_data.get("decret_designation", intro_data.get("decret_designation", "le décret"))
        missions = programme_data.get("missions", intro_data.get("missions", []))
        contexte = programme_data.get("contexte", intro_data.get("contexte", ""))
        structure_rapport = programme_data.get("structure_rapport", intro_data.get("structure_rapport", []))
        
        # Section INTRODUCTION
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph("INTRODUCTION", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Paragraphe 1 : Responsable du programme
        if responsable_nom:
            para1_text = (
                f"Nommé {responsable_fonction} par {decret_nomination}, {responsable_nom} est le Responsable du programme « {titre} », "
                f"conformément à {decret_designation}."
            )
            story.append(Paragraph(para1_text, body_style))
            story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 2 : Missions du programme
        if missions:
            para2_text = (
                f"Ce programme a été réalisé à partir d'une répartition des tâches mise en place en fonction "
                f"du décret n° 2023-963 du 6 décembre 2023 portant organisation du ministère. Les principales missions sont :"
            )
            story.append(Paragraph(para2_text, body_style))
            story.append(Spacer(1, 0.1 * cm))
            
            # Liste des missions avec puces (tirets)
            bullet_style = ParagraphStyle(
                "BulletStyle",
                parent=body_style,
                leftIndent=20,
                bulletIndent=10,
            )
            for mission in missions:
                story.append(Paragraph(mission, bullet_style, bulletText="-"))
            story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 3 : Contexte et environnement
        if not contexte:
            contexte = (
                f"En {annee}, les activités du Programme « {titre} » se sont déroulées dans un environnement économique "
                f"international relativement stable, mais également marqué par d'importants ajustements institutionnels."
            )
        story.append(Paragraph(contexte, body_style))
        story.append(Spacer(1, 0.15 * cm))
        
        # Paragraphe 4 : Structure du rapport avec liste à puces
        if not structure_rapport:
            structure_rapport = [
                "la présentation de la stratégie du programme;",
                "les réalisations du programme au cours de l'exercice 2024;",
                "la performance du programme;",
                "les perspectives."
            ]
        
        para4_text = (
            f"Pour faire face à des défis de plus en plus élevés, le Programme a élaboré un plan d'actions et défini des indicateurs "
            f"dont la réalisation est décrite dans le présent Rapport Annuel de Performance (RAP) du programme « {titre} » qui prend en compte "
            f"les rapports semestriels du Responsable de Programme (Rprog) et s'articule autour des points suivants :"
        )
        story.append(Paragraph(para4_text, body_style))
        story.append(Spacer(1, 0.1 * cm))
        
        # Liste à puces (cercles noirs)
        circle_bullet_style = ParagraphStyle(
            "CircleBulletStyle",
            parent=body_style,
            leftIndent=20,
            bulletIndent=10,
        )
        for item in structure_rapport:
            story.append(Paragraph(item, circle_bullet_style, bulletText="•"))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # I. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph(f"{partie_numero_romain}. PRÉSENTATION DE LA STRATÉGIE DU PROGRAMME", section_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # ============================================================
        # I.1. Les objectifs du programme
        # ============================================================
        story.append(CondPageBreak(3 * cm))
        story.append(Paragraph(f"{partie_numero_romain}.1. Les objectifs du programme", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Paragraphe introductif sur les objectifs
        objectif_global = programme_data.get("objectif_global", {})
        objectif_global_num = objectif_global.get("numero", "1")
        objectif_global_libelle = objectif_global.get("libelle", "Améliorer la gouvernance du secteur")
        resultat_strategique_num = objectif_global.get("resultat_strategique_num", "1")
        resultat_strategique_libelle = objectif_global.get("resultat_strategique_libelle", "La gouvernance du secteur est améliorée")
        
        objectifs_para = (
            f"La mise en œuvre des activités du Programme « {titre} » permettra, à moyen terme, de contribuer à la poursuite "
            f"de l'objectif global {objectif_global_num} du {cls.data.get('ministere', 'MPPEEP')}, à savoir « {objectif_global_libelle} » "
            f"et d'atteindre le résultat stratégique « {resultat_strategique_libelle} »."
        )
        story.append(Paragraph(objectifs_para, body_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Tableau : Objectif global et résultats stratégiques
        table_obj_header_style = ParagraphStyle(
            "TableObjHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            alignment=1,  # Centré
        )
        table_obj_cell_style = ParagraphStyle(
            "TableObjCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            alignment=0,  # Gauche
        )
        
        obj_table_data = [
            [
                Paragraph("OBJECTIF GLOBAL (OG)", table_obj_header_style),
                Paragraph("RESULTAT STRATEGIQUE (RS)", table_obj_header_style),
            ],
            [
                Paragraph(f"OG {objectif_global_num}:: {objectif_global_libelle}", table_obj_cell_style),
                Paragraph(f"RS {resultat_strategique_num}: {resultat_strategique_libelle}", table_obj_cell_style),
            ],
        ]
        
        obj_col_widths = [available_width * 0.5, available_width * 0.5]
        obj_table = Table(obj_table_data, colWidths=obj_col_widths, repeatRows=1)
        obj_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (-1, 1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        
        story.append(obj_table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Source pour le tableau des objectifs
        annee = cls.data.get("annee", 2024)
        source_obj = (
            f"Source: Annexe 4 de la Loi de Finances n° {annee - 1}-1000 du 18 décembre {annee - 1} "
            f"portant budget de l'State pour l'année {annee}"
        )
        story.append(Paragraph(source_obj, source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # ============================================================
        # I.2. Le financement du programme
        # ============================================================
        # Ajouter le titre - pas de CondPageBreak pour permettre au tableau de commencer sur la même page
        # Le tableau suivra directement après le titre et sera automatiquement divisé si trop grand
        # Si le titre risque d'être orphelin, ReportLab le gérera naturellement avec keepWithNext
        titre_financement = Paragraph(f"{partie_numero_romain}.2. Le financement du programme", subsection_title_with_table_style)
        # Pas d'espace après le titre, le tableau suit directement
        
        # Récupérer les données budgétaires du programme
        # Les données peuvent venir de programme_data ou être calculées
        programme_budget = programme_data.get("budget", {})
        
        # Utiliser les données du programme ou des valeurs par défaut/calculées
        prog_2023_total = programme_budget.get("realisations_2023", 84410746315)
        prog_prev_2024 = programme_budget.get("prevu_2024", 32341752594)
        prog_real_2024 = programme_budget.get("realise_2024", 32048763906)
        prog_ecart_2024 = programme_budget.get("ecart_2024", prog_prev_2024 - prog_real_2024)
        prog_tx_real_2024 = (prog_real_2024 / prog_prev_2024 * 100) if prog_prev_2024 > 0 else 0
        
        # Données par nature de dépense pour le programme
        prog_personnel_2023 = programme_budget.get("personnel_2023", 66953378820)
        prog_personnel_prev = programme_budget.get("personnel_prev", 7112563239)
        prog_personnel_real = programme_budget.get("personnel_real", 7112535039)
        prog_personnel_ecart = prog_personnel_prev - prog_personnel_real
        prog_personnel_tx = (prog_personnel_real / prog_personnel_prev * 100) if prog_personnel_prev > 0 else 0
        
        prog_biens_2023 = programme_budget.get("biens_2023", 4612280028)
        prog_biens_prev = programme_budget.get("biens_prev", 5360558529)
        prog_biens_real = programme_budget.get("biens_real", 5067598041)
        prog_biens_ecart = prog_biens_prev - prog_biens_real
        prog_biens_tx = (prog_biens_real / prog_biens_prev * 100) if prog_biens_prev > 0 else 0
        
        prog_transferts_2023 = programme_budget.get("transferts_2023", 626866385)
        prog_transferts_prev = programme_budget.get("transferts_prev", 14934916699)
        prog_transferts_real = programme_budget.get("transferts_real", 14934916699)
        prog_transferts_ecart = 0
        prog_transferts_tx = 100.0
        
        prog_investissements_2023 = programme_budget.get("investissements_2023", 12218221082)
        prog_investissements_prev = programme_budget.get("investissements_prev", 4933714127)
        prog_investissements_real = programme_budget.get("investissements_real", 4933714127)
        prog_investissements_ecart = 0
        prog_investissements_tx = 100.0
        
        # Créer le tableau d'exécution budgétaire du programme (similaire au tableau 3)
        # On réutilise la même structure mais avec les données du programme
        prog_table_data = []
        
        # En-têtes
        prog_table_data.append([
            Paragraph("Unités", table_header_style),
            Paragraph("REALISATIONS<br/>2023", table_header_style),
            Paragraph("2024", table_header_style),
            Paragraph("", table_header_style),
            Paragraph("", table_header_style),
            Paragraph("", table_header_style),
        ])
        prog_table_data.append([
            Paragraph("", table_header_style),
            Paragraph("", table_header_style),
            Paragraph("Prév.<br/>(P)", table_header_style),
            Paragraph("Réal<br/>(R)", table_header_style),
            Paragraph("Ecart<br/>(E) = (P)-(R)", table_header_style),
            Paragraph("Tx de réal<br/>= (R/P) x100", table_header_style),
        ])
        
        # RESSOURCES
        prog_table_data.append([
            Paragraph("<b>RESSOURCES</b>", table_subheader_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
        ])
        
        # 1.1 Ressources intérieures
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Ressources intérieures", table_cell_style),
            Paragraph(format_fcfa(prog_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prog_prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_real_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_ecart_2024), table_cell_right_style),
            Paragraph(f"{prog_tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # 1.1.1 Budget de l'Etat
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.1 Budget de l'Etat (Trésor)", table_cell_style),
            Paragraph(format_fcfa(prog_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prog_prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_real_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_ecart_2024), table_cell_right_style),
            Paragraph(f"{prog_tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # 1.1.2 Recettes de services
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.2 Recettes de services", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2 Ressources extérieures
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Ressources extérieures", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 1.2.1, 1.2.2, 1.2.3 (tous à 0)
        for sub_item in ["1.2.1 Emprunts projets", "1.2.2 Dons Projets", "1.2.3 Appuis budgétaires ciblés"]:
            prog_table_data.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item}", table_cell_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph("-", table_cell_center_style),
            ])
        
        # CHARGES
        prog_table_data.append([
            Paragraph("<b>CHARGES</b>", table_subheader_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
            Paragraph("", table_cell_center_style),
        ])
        
        # 2.1 Personnel
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Personnel", table_cell_style),
            Paragraph(format_fcfa(prog_personnel_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_personnel_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_personnel_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_personnel_ecart), table_cell_right_style),
            Paragraph(f"{prog_personnel_tx:.0f}%", table_cell_center_style),
        ])
        
        # 2.1.1 Solde
        solde_2023 = programme_budget.get("solde_2023", 66947978820)
        solde_prev = programme_budget.get("solde_prev", 6270538992)
        solde_real = programme_budget.get("solde_real", 6270538792)
        solde_ecart = solde_prev - solde_real
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.1 Solde y compris EPN", table_cell_style),
            Paragraph(format_fcfa(solde_2023), table_cell_right_style),
            Paragraph(format_fcfa(solde_prev), table_cell_right_style),
            Paragraph(format_fcfa(solde_real), table_cell_right_style),
            Paragraph(format_fcfa(solde_ecart), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.1.2 Contractuels
        contractuels_2023 = programme_budget.get("contractuels_2023", 5400000)
        contractuels_prev = programme_budget.get("contractuels_prev", 842024247)
        contractuels_real = programme_budget.get("contractuels_real", 841996247)
        contractuels_ecart = contractuels_prev - contractuels_real
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1.2 Contractuels hors solde", table_cell_style),
            Paragraph(format_fcfa(contractuels_2023), table_cell_right_style),
            Paragraph(format_fcfa(contractuels_prev), table_cell_right_style),
            Paragraph(format_fcfa(contractuels_real), table_cell_right_style),
            Paragraph(format_fcfa(contractuels_ecart), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.2 Biens et Service
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Biens et Service", table_cell_style),
            Paragraph(format_fcfa(prog_biens_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_biens_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_biens_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_biens_ecart), table_cell_right_style),
            Paragraph(f"{prog_biens_tx:.2f}%", table_cell_center_style),
        ])
        
        # 2.3 Transferts
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 Transferts", table_cell_style),
            Paragraph(format_fcfa(prog_transferts_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_ecart), table_cell_right_style),
            Paragraph(f"{prog_transferts_tx:.0f}%", table_cell_center_style),
        ])
        
        # 2.3.1 Transferts courants
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.1 Transferts courants", table_cell_style),
            Paragraph(format_fcfa(prog_transferts_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_transferts_real), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.3.2 Transferts en capital
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.3.2 Transferts en capital", table_cell_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("-", table_cell_center_style),
        ])
        
        # 2.4 Investissement
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Investissement", table_cell_style),
            Paragraph(format_fcfa(prog_investissements_2023), table_cell_right_style),
            Paragraph(format_fcfa(prog_investissements_prev), table_cell_right_style),
            Paragraph(format_fcfa(prog_investissements_real), table_cell_right_style),
            Paragraph(format_fcfa(prog_investissements_ecart), table_cell_right_style),
            Paragraph(f"{prog_investissements_tx:.0f}%", table_cell_center_style),
        ])
        
        # 2.4.1 Trésor
        tresor_inv_2023 = programme_budget.get("tresor_inv_2023", 12218221082)
        tresor_inv_prev = programme_budget.get("tresor_inv_prev", 4933714127)
        tresor_inv_real = programme_budget.get("tresor_inv_real", 4933714127)
        
        prog_table_data.append([
            Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.4.1 Trésor", table_cell_style),
            Paragraph(format_fcfa(tresor_inv_2023), table_cell_right_style),
            Paragraph(format_fcfa(tresor_inv_prev), table_cell_right_style),
            Paragraph(format_fcfa(tresor_inv_real), table_cell_right_style),
            Paragraph(format_fcfa(0), table_cell_right_style),
            Paragraph("100%", table_cell_center_style),
        ])
        
        # 2.4.2 Financement extérieur, Dons, Emprunts (tous à 0)
        for sub_item in ["2.4.2 Financement extérieur", "Dons", "Emprunts"]:
            prog_table_data.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{sub_item}", table_cell_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph(format_fcfa(0), table_cell_right_style),
                Paragraph("-", table_cell_center_style),
            ])
        
        # TOTAL
        prog_table_data.append([
            Paragraph("<b>TOTAL</b>", table_total_style),
            Paragraph(format_fcfa(prog_2023_total), table_cell_right_style),
            Paragraph(format_fcfa(prog_prev_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_real_2024), table_cell_right_style),
            Paragraph(format_fcfa(prog_ecart_2024), table_cell_right_style),
            Paragraph(f"{prog_tx_real_2024:.2f}%", table_cell_center_style),
        ])
        
        # Calcul des largeurs de colonnes pour le tableau
        col_widths = [
            available_width * 0.32,  # Unités
            available_width * 0.14,  # 2023
            available_width * 0.13,  # Prév. (P)
            available_width * 0.13,  # Réal (R)
            available_width * 0.14,  # Ecart (E)
            available_width * 0.14,  # Tx de réal
        ]
        
        # Créer le tableau avec LongTable pour permettre la division automatique sur plusieurs pages
        # LongTable est spécialement conçu pour les tableaux qui peuvent déborder sur plusieurs pages
        # repeatRows=2 permet de répéter les en-têtes sur chaque page
        prog_execution_table = LongTable(
            prog_table_data,
            colWidths=col_widths,
            repeatRows=2,    # répète les 2 premières lignes (en-têtes) sur chaque page
            splitByRow=1     # permet de couper proprement par lignes
        )
        prog_execution_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("LINEBELOW", (0, 1), (-1, 1), 1.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#bdd6ee")),
                ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
                ("SPAN", (2, 0), (5, 0)),
                ("SPAN", (0, 0), (0, 1)),
                ("SPAN", (1, 0), (1, 1)),
                ("ALIGN", (0, 2), (0, -1), "LEFT"),
                ("ALIGN", (1, 2), (-1, -1), "RIGHT"),
                ("ALIGN", (5, 2), (5, -1), "CENTER"),
                ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 2), (0, 2), "Helvetica-Bold"),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fbe4d5")),
                ("FONTNAME", (0, 10), (0, 10), "Helvetica-Bold"),
                ("BACKGROUND", (0, 10), (-1, 10), colors.HexColor("#fbe4d5")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 11), (-1, 11), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 14), (-1, 14), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 15), (-1, 15), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, 18), (-1, 18), colors.HexColor("#e2efd9")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ffe599")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        
        # Ajouter le titre de section
        story.append(titre_financement)
        
        # Ajouter le titre du tableau juste avant le tableau (comme dans le demo)
        tableau_title = f"Tableau : Exécution du budget du Programme {numero} « {titre} »"
        story.append(Paragraph(f"<b>{tableau_title}</b>", subsection_title_style))
        story.append(Spacer(1, 0.2 * cm))
        
        # Ajouter le tableau LongTable - il se divisera automatiquement sur plusieurs pages
        story.append(prog_execution_table)
        story.append(Spacer(1, 0.2 * cm))
        
        # Source
        story.append(Paragraph("Source: Situation d'exécution issue du SIGOBE", source_style))
        story.append(Spacer(1, 0.3 * cm))
        
        # Interprétation du financement du programme
        # L'utilisateur peut fournir son interprétation, sinon afficher un placeholder en rouge
        financement_interpretation = programme_data.get("financement_interpretation", "")
        
        if financement_interpretation:
            # Afficher l'interprétation fournie par l'utilisateur
            # Le texte peut contenir du HTML pour le formatage (gras, italique, etc.)
            story.append(Paragraph(financement_interpretation, body_style))
        else:
            # Afficher un placeholder en rouge et en italique
            placeholder_style = ParagraphStyle(
                "PlaceholderStyle",
                parent=body_style,
                textColor=colors.HexColor("#FF0000"),  # Rouge
                fontName="Helvetica-Oblique",  # Italique
            )
            story.append(Paragraph("Votre interprétation ici", placeholder_style))
        
        story.append(Spacer(1, 0.3 * cm))
        
        # Note NB si fournie par l'utilisateur
        financement_note = programme_data.get("financement_note", "")
        if financement_note:
            story.append(Paragraph(f"<b>NB :</b> {financement_note}", body_style))
            story.append(Spacer(1, 0.2 * cm))
        else:
            # Placeholder pour la note en rouge
            placeholder_note_style = ParagraphStyle(
                "PlaceholderNoteStyle",
                parent=body_style,
                textColor=colors.HexColor("#FF0000"),  # Rouge
                fontName="Helvetica-Oblique",  # Italique
                spaceBefore=6,
            )
            story.append(Paragraph("<b>NB :</b> Votre interprétation ici", placeholder_note_style))
            story.append(Spacer(1, 0.2 * cm))
        
        
        # Cela permet à ReportLab de diviser correctement les tableaux longs sur plusieurs pages
        # Dans ReportLab, frame_y est la position Y du BAS du Frame (0,0 est en bas à gauche)
        # et le Frame monte vers le haut à partir de cette position
        final_page = cls._render_multipage_story(
            pdf,
            story,
            page_num=start_page,
            frame_x=left_margin,
            frame_y=bottom_margin,  # Commence depuis le bas (bottom_margin inclut déjà footer_height + footer_margin)
            frame_width=available_width,
            frame_height=available_height,  # Monte jusqu'en haut de la zone disponible (height - top_margin - bottom_margin)
            page_width=width,
            show_page_number=True,
            draw_footer_func=draw_footer,
        )
        
        return final_page