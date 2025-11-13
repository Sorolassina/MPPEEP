 def _draw_chapter_one_page(cls, pdf: canvas.Canvas, width: float, height: float) -> None:
        """Dessine la page 5 avec le CHAPITRE I : DISPOSITIONS GÉNÉRALES."""
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
            spaceAfter=10,
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
        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=16,
            alignment=0,  # Gauche
            spaceAfter=8,
            spaceBefore=12,
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
        story.append(Paragraph("CHAPITRE I : DISPOSITIONS GÉNÉRALES", chapter_title_style))
        story.append(Spacer(1, 0.2 * cm))

        # Article 1 : Objet
        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT")
        article1_text = (
            f"La présente lettre d'engagement sur la performance a pour objet d'engager les différentes parties "
            f"à l'atteinte des objectifs et des résultats du programme « {programme} », "
            f"définis dans le Projet Annuel de Performance (PAP)."
        )
        story.append(Paragraph("Article 1 : Objet", article_title_style))
        story.append(Paragraph(article1_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # Article 2 : Nature de la lettre
        article2_text = (
            "La présente lettre d'engagement sur la performance de nature non juridique, "
            "est un engagement réciproque interne à l'Administration."
        )
        story.append(Paragraph("Article 2 : Nature de la lettre", article_title_style))
        story.append(Paragraph(article2_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # Article 3 : Obligations générales
        # Le MINISTRE s'engage à :
        minister_commitments = [
            "communiquer les orientations stratégiques du Ministère au RPROG-PORTEFEUILLE DE L'ETAT ;",
            "favoriser la mobilisation des ressources pour la mise en œuvre du programme « Portefeuille de l'État » ;",
            "favoriser toute mesure d'ordre organisationnel et/ou juridique facilitant l'accomplissement des missions confiées au Responsable de programme ;",
            "suivre les projets d'investissement du programme « Portefeuille de l'État » sur la base d'un plan pluriannuel d'investissement.",
        ]
        # Le RESPONSABLE DE PROGRAMME s'engage à :
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

        # Article 4 : Obligations spécifiques
        programme = cls.data.get("programme_intitule", "PORTEFEUILLE DE L'ETAT")
        article4_text = (
            f"Sans préjudice des obligations générales citées à l'article 3 de la présente lettre d'engagement, "
            f"le MINISTRE et le RESPONSABLE DE PROGRAMME « {programme} » peuvent adopter des mesures spécifiques "
            f"portant notamment sur la gestion des délais de production des DPPD-PAP, des RAP et de l'exécution "
            f"des diligences liées au programme, sur les conditions sociales et les méthodes de prise de décision."
        )
        story.append(Paragraph("Article 4 : Obligations spécifiques", article_title_style))
        story.append(Paragraph(article4_text, body_style))
        story.append(Spacer(1, 0.1 * cm))

        # Article 5 : Droits des parties
        article5_text = (
            "Les droits des différentes parties sont ceux qui sont garantis par les textes en vigueur."
        )
        story.append(Paragraph("Article 5 : Droits des parties", article_title_style))
        story.append(Paragraph(article5_text, body_style))

        # Gestion du débordement sur plusieurs pages
        import logging
        logger = logging.getLogger(__name__)
        
        page_num = 5
        frame_height = height - 2 * top_margin
        first_page = True
        logger.info(f"   🔄 CHAPITRE I: {len(story)} éléments à afficher")

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
            logger.info(f"   📝 CHAPITRE I page {page_num}: {story_length_before} éléments restants")
            
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
