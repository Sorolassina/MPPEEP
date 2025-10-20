"""
Service de génération de rapports de performance
Génère des rapports PDF, Excel, etc.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlmodel import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.performance import PrioriteObjectif, StatutObjectif, TypeObjectif
from app.models.system_settings import SystemSettings
from app.services.performance_service import PerformanceService

logger = get_logger(__name__)


class NumberedCanvas(canvas.Canvas):
    """Canvas personnalisé pour ajouter des numéros de page et en-têtes/pieds de page"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.footer_color = colors.HexColor("#036c1d")  # Sera mis à jour dynamiquement
        self.company_info = ""  # Informations de l'entreprise pour le footer

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Ajoute les numéros de page sur toutes les pages"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        """Dessine le numéro de page et le footer"""
        self.saveState()

        # Ligne de séparation en haut du footer
        self.setStrokeColor(self.footer_color)
        self.setLineWidth(1.5)
        self.line(2 * cm, 2.2 * cm, A4[0] - 2 * cm, 2.2 * cm)

        # Numéro de page (à droite)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.grey)
        page_num = f"Page {self._pageNumber} / {page_count}"
        self.drawRightString(A4[0] - 2 * cm, 1.5 * cm, page_num)

        # Informations de l'entreprise (à gauche)
        if self.company_info:
            self.setFont("Helvetica", 7)
            self.setFillColor(colors.grey)
            self.drawString(2 * cm, 1.5 * cm, self.company_info)

        # Titre du rapport (centré)
        # self.setFont('Helvetica-Bold', 8)
        # self.setFillColor(self.footer_color)
        # text_width = self.stringWidth("RAPPORT DE PERFORMANCE", 'Helvetica-Bold', 8)
        # self.drawString((A4[0] - text_width) / 2, 1*cm, "RAPPORT DE PERFORMANCE")

        self.restoreState()


class ReportGenerator:
    """Générateur de rapports de performance"""

    @staticmethod
    def _generate_sample_data(session: Session) -> None:
        """Génère des données factices si la base est vide"""
        from app.models.performance import IndicateurPerformance, ObjectifPerformance

        try:
            logger.info("📝 Génération de données factices pour le rapport...")

            # Objectifs factices
            objectifs = [
                ObjectifPerformance(
                    titre="Améliorer la satisfaction client",
                    description="Augmenter le taux de satisfaction client de 75% à 85%",
                    type_objectif=TypeObjectif.CLIENT,
                    priorite=PrioriteObjectif.HAUTE,
                    date_debut=date(2025, 1, 1),
                    date_fin=date(2025, 12, 31),
                    periode="2025",
                    valeur_cible=Decimal("85.0"),
                    valeur_actuelle=Decimal("82.0"),
                    unite="%",
                    responsable_id=1,
                    service_responsable="Service Client",
                    statut=StatutObjectif.EN_COURS,
                    progression_pourcentage=Decimal("70.0"),
                    commentaires="Exemple de données factices",
                    created_by_id=1,
                ),
                ObjectifPerformance(
                    titre="Réduire les coûts opérationnels",
                    description="Diminuer les coûts opérationnels de 15%",
                    type_objectif=TypeObjectif.FINANCIER,
                    priorite=PrioriteObjectif.CRITIQUE,
                    date_debut=date(2025, 1, 1),
                    date_fin=date(2025, 12, 31),
                    periode="2025",
                    valeur_cible=Decimal("15.0"),
                    valeur_actuelle=Decimal("12.5"),
                    unite="%",
                    responsable_id=1,
                    service_responsable="Direction Financière",
                    statut=StatutObjectif.EN_COURS,
                    progression_pourcentage=Decimal("83.3"),
                    commentaires="Exemple de données factices",
                    created_by_id=1,
                ),
                ObjectifPerformance(
                    titre="Atteindre certification ISO 9001",
                    description="Obtenir la certification ISO 9001:2015",
                    type_objectif=TypeObjectif.QUALITE,
                    priorite=PrioriteObjectif.CRITIQUE,
                    date_debut=date(2025, 1, 1),
                    date_fin=date(2025, 9, 30),
                    periode="Q1-Q3 2025",
                    valeur_cible=Decimal("1.0"),
                    valeur_actuelle=Decimal("1.0"),
                    unite="certification",
                    responsable_id=1,
                    service_responsable="Direction Qualité",
                    statut=StatutObjectif.ATTEINT,
                    progression_pourcentage=Decimal("100.0"),
                    commentaires="Exemple de données factices",
                    created_by_id=1,
                ),
            ]

            for obj in objectifs:
                session.add(obj)

            # Indicateurs factices
            indicateurs = [
                IndicateurPerformance(
                    nom="Taux de satisfaction client",
                    description="Pourcentage de clients satisfaits",
                    categorie="Qualité Service",
                    type_indicateur="Pourcentage",
                    valeur_cible=Decimal("85.0"),
                    valeur_actuelle=Decimal("82.0"),
                    unite="%",
                    frequence_maj="Trimestriel",
                    responsable_id=1,
                    service_responsable="Service Client",
                    actif=True,
                    created_by_id=1,
                ),
                IndicateurPerformance(
                    nom="Coût par unité produite",
                    description="Coût moyen de production",
                    categorie="Efficacité Opérationnelle",
                    type_indicateur="Montant",
                    valeur_cible=Decimal("45.0"),
                    valeur_actuelle=Decimal("48.5"),
                    unite="€",
                    frequence_maj="Mensuel",
                    responsable_id=1,
                    service_responsable="Production",
                    actif=True,
                    created_by_id=1,
                ),
                IndicateurPerformance(
                    nom="Délai moyen de livraison",
                    description="Temps entre commande et livraison",
                    categorie="Logistique",
                    type_indicateur="Temps",
                    valeur_cible=Decimal("3.0"),
                    valeur_actuelle=Decimal("2.8"),
                    unite="jours",
                    frequence_maj="Hebdomadaire",
                    responsable_id=1,
                    service_responsable="Logistique",
                    actif=True,
                    created_by_id=1,
                ),
            ]

            for ind in indicateurs:
                session.add(ind)

            session.commit()
            logger.info("✅ Données factices générées avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération des données factices: {e}")
            session.rollback()
            raise

    @staticmethod
    def generate_pdf_report(
        session: Session,
        report_type: str,
        period: str,
        date_debut: date | None = None,
        date_fin: date | None = None,
        user_name: str = "Utilisateur",
    ) -> BytesIO:
        """
        Génère un rapport PDF

        Args:
            session: Session de base de données
            report_type: Type de rapport (GLOBAL, OBJECTIFS, INDICATEURS, SYNTHESE)
            period: Période (CURRENT_MONTH, LAST_MONTH, etc.)
            date_debut: Date de début (si CUSTOM)
            date_fin: Date de fin (si CUSTOM)
            user_name: Nom de l'utilisateur qui génère le rapport

        Returns:
            BytesIO contenant le PDF généré
        """
        try:
            # Vérifier s'il y a des données, sinon générer des données factices
            objectifs_count = len(PerformanceService.get_objectifs(session, limit=1))
            if objectifs_count == 0:
                logger.warning("⚠️  Aucune donnée de performance trouvée. Génération de données factices...")
                ReportGenerator._generate_sample_data(session)

            # Récupérer les informations de l'entreprise
            system_settings = session.get(SystemSettings, 1)
            if not system_settings:
                system_settings = SystemSettings()  # Utiliser les valeurs par défaut

            # Nom de l'application
            application_name = settings.APP_NAME

            # Récupérer les couleurs dynamiques depuis la base
            PRIMARY_COLOR = colors.HexColor(system_settings.primary_color or "#ffd300")
            SECONDARY_COLOR = colors.HexColor(system_settings.secondary_color or "#036c1d")
            ACCENT_COLOR = colors.HexColor(system_settings.accent_color or "#e63600")

            # Créer le buffer pour le PDF
            buffer = BytesIO()

            # Créer le document PDF avec canvas personnalisé
            doc = SimpleDocTemplate(
                buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2.5 * cm, bottomMargin=3 * cm
            )

            # Styles professionnels
            styles = getSampleStyleSheet()

            # Style pour la page de couverture
            cover_title_style = ParagraphStyle(
                "CoverTitle",
                parent=styles["Heading1"],
                fontSize=32,
                textColor=colors.white,
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                leading=40,
            )

            cover_subtitle_style = ParagraphStyle(
                "CoverSubtitle",
                parent=styles["Normal"],
                fontSize=18,
                textColor=colors.white,
                spaceAfter=10,
                alignment=TA_CENTER,
                fontName="Helvetica",
            )

            # Styles pour le contenu
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=22,
                textColor=colors.HexColor("#1f2937"),
                spaceAfter=20,
                spaceBefore=10,
                alignment=TA_LEFT,
                fontName="Helvetica-Bold",
                borderWidth=2,
                borderColor=colors.HexColor("#667eea"),
                borderPadding=10,
                backColor=colors.HexColor("#f0f4ff"),
            )

            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#667eea"),
                spaceAfter=10,
                spaceBefore=15,
                fontName="Helvetica-Bold",
                borderWidth=0,
                leftIndent=0,
                borderPadding=5,
                backColor=colors.HexColor("#f9fafb"),
            )

            subheading_style = ParagraphStyle(
                "CustomSubHeading",
                parent=styles["Heading3"],
                fontSize=12,
                textColor=colors.HexColor("#374151"),
                spaceAfter=8,
                spaceBefore=10,
                fontName="Helvetica-Bold",
            )

            normal_style = ParagraphStyle(
                "CustomNormal",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#4b5563"),
                spaceAfter=6,
                leading=14,
            )

            # Contenu du document
            story = []

            # Calculer les dates selon la période
            dates = ReportGenerator._calculate_period_dates(period, date_debut, date_fin)

            # ========================================
            # PAGE DE COUVERTURE
            # ========================================

            # Spacer pour centrer verticalement
            story.append(Spacer(1, 0.5 * inch))

            # En-tête avec logo et nom de l'entreprise
            header_content = []

            # Logo (si disponible)
            logo_path = None
            if system_settings.logo_path:
                # Chercher le logo dans static ou uploads
                static_logo = Path("app/static") / system_settings.logo_path
                if static_logo.exists():
                    logo_path = str(static_logo)

            if logo_path:
                try:
                    logo = Image(logo_path, width=1.5 * inch, height=1.5 * inch)
                    logo.hAlign = "CENTER"
                    header_content.append(logo)
                    header_content.append(Spacer(1, 0.3 * inch))
                except:
                    pass

            # Nom de l'entreprise
            company_name = system_settings.company_name or "MPPEEP Dashboard"
            company_para = Paragraph(
                company_name.upper(),
                ParagraphStyle(
                    "CompanyName",
                    fontSize=24,
                    textColor=SECONDARY_COLOR,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    spaceAfter=10,
                ),
            )
            header_content.append(company_para)

            # Ajouter l'en-tête
            for elem in header_content:
                story.append(elem)

            story.append(Spacer(1, 0.3 * inch))
            # Description si disponible (après le nom, avec plus d'espace)
            if system_settings.company_description:
                desc_para = Paragraph(
                    system_settings.company_description,
                    ParagraphStyle(
                        "CompanyDesc",
                        fontSize=10,
                        textColor=colors.grey,
                        alignment=TA_CENTER,
                        fontName="Helvetica-Oblique",
                    ),
                )
                story.append(desc_para)
                story.append(Spacer(1, 0.2 * inch))
            else:
                story.append(Spacer(1, 0.2 * inch))

            # Grand titre du rapport avec fond vert
            title_data = [[Paragraph("RAPPORT DE PERFORMANCE", cover_title_style)]]
            title_table = Table(title_data, colWidths=[6.5 * inch])
            title_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SECONDARY_COLOR),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 25),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 25),
                    ]
                )
            )
            story.append(title_table)
            story.append(Spacer(1, 0.4 * inch))

            # Informations de période et génération
            info_style = ParagraphStyle(
                "CoverInfo", fontSize=11, textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER, leading=16
            )
            period_info = f"""
            <b>Période couverte</b><br/>
            {dates["debut"].strftime("%d %B %Y")} - {dates["fin"].strftime("%d %B %Y")}<br/>
            <br/>
            <b>Date de génération</b><br/>
            {datetime.now().strftime("%d %B %Y à %H:%M")}<br/>
            <br/>
            <b>Généré par</b><br/>
            {user_name}
            """

            info_data = [[Paragraph(period_info, info_style)]]
            info_table = Table(info_data, colWidths=[6.5 * inch])
            info_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 25),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 25),
                        ("BOX", (0, 0), (-1, -1), 2, SECONDARY_COLOR),
                    ]
                )
            )
            story.append(info_table)
            story.append(Spacer(1, 0.8 * inch))

            # Footer avec informations de contact
            footer_content = []
            footer_parts = []
            if system_settings.company_email:
                footer_parts.append(f"{system_settings.company_email}")
            if system_settings.company_phone:
                footer_parts.append(f"{system_settings.company_phone}")
            if system_settings.company_address:
                footer_parts.append(f"{system_settings.company_address}")

            if footer_parts:
                footer_text = "Source: " + application_name
                footer_para = Paragraph(
                    footer_text,
                    ParagraphStyle(
                        "Footer", fontSize=9, textColor=colors.white, alignment=TA_CENTER, fontName="Helvetica"
                    ),
                )
                footer_data = [[footer_para]]
                footer_table = Table(footer_data, colWidths=[6.5 * inch])
                footer_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_COLOR),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("TOPPADDING", (0, 0), (-1, -1), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ]
                    )
                )
                story.append(footer_table)

            # Saut de page après la couverture
            story.append(PageBreak())

            # ========================================
            # SOMMAIRE
            # ========================================

            story.append(Paragraph("TABLE DES MATIÈRES", title_style))
            story.append(Spacer(1, 0.3 * inch))

            # Créer le sommaire
            toc_data = [
                ["Section", "Page"],
            ]

            if report_type in ["GLOBAL", "OBJECTIFS"]:
                toc_data.append(["1. Objectifs de Performance", "3"])
            if report_type in ["GLOBAL", "INDICATEURS"]:
                toc_data.append(["2. Indicateurs de Performance", "..."])
            if report_type == "SYNTHESE":
                toc_data.append(["1. Synthèse Exécutive", "3"])

            toc_table = Table(toc_data, colWidths=[5 * inch, 1.5 * inch])
            toc_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), SECONDARY_COLOR),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("ALIGN", (1, 0), (1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 10),
                        ("PADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )

            story.append(toc_table)
            story.append(Spacer(1, 0.5 * inch))

            # Note sur le rapport
            note_style = ParagraphStyle(
                "Note",
                parent=normal_style,
                fontSize=9,
                textColor=colors.HexColor("#6b7280"),
                alignment=TA_JUSTIFY,
                leftIndent=10,
                rightIndent=10,
            )
            story.append(
                Paragraph(
                    "<i>Ce rapport présente une analyse détaillée de la performance organisationnelle "
                    "basée sur les données collectées durant la période spécifiée. Les indicateurs et "
                    "objectifs présentés reflètent l'état au moment de la génération du rapport.</i>",
                    note_style,
                )
            )

            # Grand espace avant le contenu (au lieu de PageBreak forcé pour éviter les pages blanches)
            story.append(Spacer(1, 1.5 * inch))

            # ========================================
            # CONTENU PRINCIPAL
            # ========================================

            # Contenu selon le type de rapport - Chaque section sur une nouvelle page
            if report_type in ["GLOBAL", "OBJECTIFS"]:
                story.append(PageBreak())  # Nouvelle page pour la section Objectifs
                story.extend(
                    ReportGenerator._generate_objectifs_section(
                        session,
                        dates["debut"],
                        dates["fin"],
                        heading_style,
                        normal_style,
                        SECONDARY_COLOR,
                        PRIMARY_COLOR,
                        ACCENT_COLOR,
                    )
                )

            if report_type in ["GLOBAL", "INDICATEURS"]:
                story.append(PageBreak())  # Nouvelle page pour la section Indicateurs
                story.extend(
                    ReportGenerator._generate_indicateurs_section(
                        session,
                        dates["debut"],
                        dates["fin"],
                        heading_style,
                        normal_style,
                        SECONDARY_COLOR,
                        PRIMARY_COLOR,
                        ACCENT_COLOR,
                    )
                )

            if report_type == "SYNTHESE":
                story.append(PageBreak())  # Nouvelle page pour la section Synthèse
                story.extend(
                    ReportGenerator._generate_synthese_section(
                        session,
                        dates["debut"],
                        dates["fin"],
                        heading_style,
                        normal_style,
                        SECONDARY_COLOR,
                        PRIMARY_COLOR,
                        ACCENT_COLOR,
                    )
                )

            # ========================================
            # ANALYSE COMPARATIVE (pour rapports périodiques)
            # ========================================
            if period in ["CURRENT_MONTH", "CURRENT_QUARTER", "CURRENT_YEAR"] and report_type != "SYNTHESE":
                story.extend(
                    ReportGenerator._generate_comparative_section(
                        session,
                        period,
                        dates,
                        report_type,
                        title_style,
                        heading_style,
                        normal_style,
                        SECONDARY_COLOR,
                        PRIMARY_COLOR,
                        ACCENT_COLOR,
                    )
                )

            # ========================================
            # NOTES ET COMMENTAIRES (pour tous les types sauf SYNTHESE)
            # ========================================
            if report_type != "SYNTHESE":
                story.extend(
                    ReportGenerator._generate_notes_section(
                        session, report_type, heading_style, normal_style, SECONDARY_COLOR, PRIMARY_COLOR, ACCENT_COLOR
                    )
                )

            # ========================================
            # CONCLUSION (pour tous les types)
            # ========================================
            story.extend(
                ReportGenerator._generate_conclusion_section(
                    session,
                    dates,
                    report_type,
                    title_style,
                    heading_style,
                    normal_style,
                    SECONDARY_COLOR,
                    PRIMARY_COLOR,
                    ACCENT_COLOR,
                    system_settings,
                )
            )

            # Pied de page
            story.append(Spacer(1, 0.5 * inch))
            story.append(
                Paragraph(
                    f"<i>Rapport généré automatiquement par {system_settings.company_name or 'MPPEEP Dashboard'} - {datetime.now().year}</i>",
                    ParagraphStyle(
                        "Footer", parent=normal_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER
                    ),
                )
            )

            # Construire le PDF avec le canvas personnalisé
            # Préparer les informations pour le footer
            footer_parts = []
            if system_settings.company_email:
                footer_parts.append(system_settings.company_email)
            if system_settings.company_phone:
                footer_parts.append(system_settings.company_phone)
            if system_settings.company_address:
                footer_parts.append(system_settings.company_address)
            company_footer_info = " | ".join(footer_parts)

            # Créer une classe de canvas avec les couleurs et infos configurées
            def make_canvas(*args, **kwargs):
                c = NumberedCanvas(*args, **kwargs)
                c.footer_color = SECONDARY_COLOR
                c.company_info = company_footer_info
                return c

            doc.build(story, canvasmaker=make_canvas)

            # Retourner au début du buffer
            buffer.seek(0)
            return buffer

        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport PDF: {e}")
            raise

    @staticmethod
    def _create_progress_bar(percentage: float, width: float = 4 * inch, height: float = 0.3 * inch) -> Table:
        """Crée une barre de progression visuelle"""
        # Déterminer la couleur selon le pourcentage
        if percentage >= 80:
            bar_color = colors.HexColor("#10b981")  # Vert
        elif percentage >= 60:
            bar_color = colors.HexColor("#f59e0b")  # Orange
        else:
            bar_color = colors.HexColor("#ef4444")  # Rouge

        # Calculer les largeurs
        filled_width = (percentage / 100) * width
        empty_width = width - filled_width

        # Créer une barre avec deux cellules (remplie + vide)
        if filled_width > 0 and empty_width > 0:
            bar_data = [["", ""]]
            bar_table = Table(bar_data, colWidths=[filled_width, empty_width], rowHeights=[height])
            bar_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), bar_color),
                        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#e5e7eb")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )
        elif filled_width >= width:
            # 100% rempli
            bar_data = [[""]]
            bar_table = Table(bar_data, colWidths=[width], rowHeights=[height])
            bar_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), bar_color),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )
        else:
            # Vide
            bar_data = [[""]]
            bar_table = Table(bar_data, colWidths=[width], rowHeights=[height])
            bar_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e5e7eb")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )

        return bar_table

    @staticmethod
    def _calculate_period_dates(period: str, date_debut: date | None, date_fin: date | None) -> dict[str, date]:
        """Calcule les dates de début et fin selon la période"""
        today = date.today()

        if period == "CUSTOM" and date_debut and date_fin:
            return {"debut": date_debut, "fin": date_fin}

        elif period == "CURRENT_MONTH":
            debut = today.replace(day=1)
            # Dernier jour du mois
            if today.month == 12:
                fin = today.replace(day=31)
            else:
                fin = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        elif period == "LAST_MONTH":
            fin = today.replace(day=1) - timedelta(days=1)
            debut = fin.replace(day=1)

        elif period == "CURRENT_QUARTER":
            quarter = (today.month - 1) // 3
            debut = today.replace(month=quarter * 3 + 1, day=1)
            fin = today

        elif period == "LAST_QUARTER":
            current_quarter = (today.month - 1) // 3
            if current_quarter == 0:
                last_quarter = 3
                year = today.year - 1
            else:
                last_quarter = current_quarter - 1
                year = today.year
            debut = date(year, last_quarter * 3 + 1, 1)
            fin = date(year, (last_quarter + 1) * 3, 1) - timedelta(days=1)

        elif period == "CURRENT_YEAR":
            debut = today.replace(month=1, day=1)
            fin = today

        elif period == "LAST_YEAR":
            debut = date(today.year - 1, 1, 1)
            fin = date(today.year - 1, 12, 31)

        else:
            debut = today.replace(day=1)
            fin = today

        return {"debut": debut, "fin": fin}

    @staticmethod
    def _get_report_type_label(report_type: str) -> str:
        """Retourne le libellé du type de rapport"""
        labels = {
            "GLOBAL": "Rapport Global de Performance",
            "OBJECTIFS": "Rapport sur les Objectifs",
            "INDICATEURS": "Rapport sur les Indicateurs",
            "SYNTHESE": "Synthèse Exécutive",
        }
        return labels.get(report_type, report_type)

    @staticmethod
    def _generate_objectifs_section(
        session: Session,
        date_debut: date,
        date_fin: date,
        heading_style,
        normal_style,
        secondary_color,
        primary_color,
        accent_color,
    ) -> list:
        """Génère la section objectifs du rapport"""
        story = []

        # Titre de section
        story.append(Paragraph("OBJECTIFS DE PERFORMANCE", heading_style))

        # Récupérer les objectifs
        objectifs = PerformanceService.get_objectifs(session, limit=1000)

        if not objectifs:
            story.append(Paragraph("Aucun objectif défini pour cette période.", normal_style))
            story.append(Spacer(1, 0.3 * inch))
            return story

        # KPIs des objectifs
        kpis = PerformanceService.get_kpis_objectifs(session)

        # Tableau récapitulatif avec design moderne
        data = [
            ["MÉTRIQUE", "VALEUR", "INDICATEUR"],
            ["Total objectifs", str(kpis.get("total_objectifs", 0)), ""],
            ["Objectifs atteints", str(kpis.get("objectifs_atteints", 0)), ""],
            ["Objectifs en cours", str(kpis.get("objectifs_en_cours", 0)), ""],
            ["Objectifs en retard", str(kpis.get("objectifs_en_retard", 0)), ""],
            ["Taux de réalisation", f"{kpis.get('taux_realisation', 0)}%", ""],
            ["Progression moyenne", f"{kpis.get('progression_moyenne', 0)}%", ""],
        ]

        table = Table(data, colWidths=[3.5 * inch, 2 * inch, 1 * inch])
        table.setStyle(
            TableStyle(
                [
                    # En-tête
                    ("BACKGROUND", (0, 0), (-1, 0), secondary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    # Corps
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("PADDING", (0, 1), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        story.append(KeepTogether([table]))
        story.append(Spacer(1, 0.4 * inch))

        # Graphique de taux de réalisation avec barre visuelle
        taux = kpis.get("taux_realisation", 0)
        story.append(
            Paragraph(
                f"<b>Taux de Réalisation Global: {taux}%</b>",
                ParagraphStyle(
                    "Bold",
                    parent=normal_style,
                    fontSize=11,
                    textColor=colors.HexColor("#1f2937"),
                    fontName="Helvetica-Bold",
                ),
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        # Barre de progression
        progress_bar = ReportGenerator._create_progress_bar(taux, width=6.5 * inch, height=0.4 * inch)
        story.append(KeepTogether([progress_bar]))
        story.append(Spacer(1, 0.4 * inch))

        # Détails par statut
        objectifs_par_statut = {}
        for obj in objectifs:
            # Utiliser .value si c'est un enum, sinon convertir en string
            if isinstance(obj.statut, StatutObjectif):
                statut = obj.statut.value
            else:
                statut = str(obj.statut) if obj.statut else "Non défini"

            if statut not in objectifs_par_statut:
                objectifs_par_statut[statut] = []
            objectifs_par_statut[statut].append(obj)

        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("📋 Détails par Statut", heading_style))

        # Tableau récapitulatif par statut
        for statut, objs in objectifs_par_statut.items():
            # Créer une liste pour regrouper header + objectifs
            statut_section = []

            # Couleur selon le statut
            if "ATTEINT" in statut.upper() or "TERMINÉ" in statut.upper():
                bg_color = colors.HexColor("#d1fae5")
                text_color = colors.HexColor("#065f46")
            elif "EN_COURS" in statut.upper():
                bg_color = colors.HexColor("#dbeafe")
                text_color = colors.HexColor("#1e40af")
            elif "RETARD" in statut.upper():
                bg_color = colors.HexColor("#fee2e2")
                text_color = colors.HexColor("#991b1b")
            else:
                bg_color = colors.HexColor("#f3f4f6")
                text_color = colors.HexColor("#374151")

            # En-tête de statut - Formatter le statut pour meilleure lisibilité
            statut_libelle = statut.replace("_", " ").title()
            statut_header = Table([[f"● {statut_libelle} ({len(objs)} objectifs)"]], colWidths=[6.5 * inch])
            statut_header.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                        ("TEXTCOLOR", (0, 0), (-1, -1), text_color),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 11),
                        ("PADDING", (0, 0), (-1, -1), 10),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ]
                )
            )
            statut_section.append(statut_header)
            statut_section.append(Spacer(1, 0.1 * inch))

            # Liste des objectifs de ce statut (limiter à 5 par statut)
            for obj in objs[:5]:
                obj_data = [
                    ["Objectif", obj.titre],
                    ["Description", obj.description or "N/A"],
                    ["Service", obj.service_responsable or "N/A"],
                    ["Progression", f"{obj.progression_pourcentage}%"],
                    ["Valeur actuelle", f"{obj.valeur_actuelle or 0} {obj.unite}"],
                    ["Valeur cible", f"{obj.valeur_cible or 0} {obj.unite}"],
                    ["Échéance", obj.date_fin.strftime("%d/%m/%Y") if obj.date_fin else "N/A"],
                ]

                obj_table = Table(obj_data, colWidths=[1.5 * inch, 5 * inch])
                obj_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f9fafb")),
                            ("BACKGROUND", (1, 0), (1, -1), colors.white),
                            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2937")),
                            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                            ("ALIGN", (1, 0), (1, -1), "LEFT"),
                            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("PADDING", (0, 0), (-1, -1), 6),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ]
                    )
                )

                statut_section.append(obj_table)
                statut_section.append(Spacer(1, 0.15 * inch))

            if len(objs) > 5:
                statut_section.append(
                    Paragraph(
                        f"<i>... et {len(objs) - 5} autre(s) objectif(s) avec le statut '{statut}'</i>", normal_style
                    )
                )

            # Ajouter toute la section de statut en un bloc
            story.append(KeepTogether(statut_section))
            story.append(Spacer(1, 0.2 * inch))

        return story

    @staticmethod
    def _generate_indicateurs_section(
        session: Session,
        date_debut: date,
        date_fin: date,
        heading_style,
        normal_style,
        secondary_color,
        primary_color,
        accent_color,
    ) -> list:
        """Génère la section indicateurs du rapport"""
        story = []

        # Titre de section
        story.append(Paragraph("INDICATEURS DE PERFORMANCE", heading_style))

        # Récupérer les indicateurs
        indicateurs = PerformanceService.get_indicateurs(session, limit=1000)

        if not indicateurs:
            story.append(Paragraph("Aucun indicateur défini pour cette période.", normal_style))
            story.append(Spacer(1, 0.3 * inch))
            return story

        # KPIs des indicateurs
        kpis_indicateurs = {"total": len(indicateurs), "par_categorie": {}, "par_frequence": {}}

        for ind in indicateurs:
            cat = ind.categorie or "Non catégorisé"
            freq = ind.frequence_maj or "Non définie"
            kpis_indicateurs["par_categorie"][cat] = kpis_indicateurs["par_categorie"].get(cat, 0) + 1
            kpis_indicateurs["par_frequence"][freq] = kpis_indicateurs["par_frequence"].get(freq, 0) + 1

        # Tableau récapitulatif avec design amélioré
        recap_data = [
            ["STATISTIQUES", "VALEUR"],
            ["Total indicateurs", str(kpis_indicateurs["total"])],
            ["Catégories distinctes", str(len(kpis_indicateurs["par_categorie"]))],
            ["Fréquences de mise à jour", str(len(kpis_indicateurs["par_frequence"]))],
        ]

        recap_table = Table(recap_data, colWidths=[4 * inch, 2.5 * inch])
        recap_table.setStyle(
            TableStyle(
                [
                    # En-tête
                    ("BACKGROUND", (0, 0), (-1, 0), secondary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                    ("PADDING", (0, 0), (-1, 0), 10),
                    # Corps
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1f2937")),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("PADDING", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        story.append(KeepTogether([recap_table]))
        story.append(Spacer(1, 0.3 * inch))

        # Détails par catégorie
        story.append(Paragraph("📊 Indicateurs par Catégorie", heading_style))

        for categorie, inds_cat in kpis_indicateurs["par_categorie"].items():
            cat_data = [[f"● {categorie}: {inds_cat} indicateur(s)"]]
            cat_table = Table(cat_data, colWidths=[6.5 * inch])
            cat_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e0f2fe")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0369a1")),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("PADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(cat_table)
            story.append(Spacer(1, 0.05 * inch))

        story.append(Spacer(1, 0.3 * inch))

        # Tableau détaillé des indicateurs (top 15)
        story.append(Paragraph("📋 Top 15 Indicateurs", heading_style))

        data = [["Indicateur", "Actuel", "Cible", "% Atteinte", "Catégorie"]]

        for ind in indicateurs[:15]:
            # Calculer le % d'atteinte
            if ind.valeur_cible and ind.valeur_cible > 0:
                pct_atteinte = (float(ind.valeur_actuelle or 0) / float(ind.valeur_cible)) * 100
                pct_str = f"{pct_atteinte:.1f}%"
            else:
                pct_str = "N/A"

            data.append(
                [
                    ind.nom[:40] + "..." if len(ind.nom) > 40 else ind.nom,
                    f"{ind.valeur_actuelle or 0}",
                    f"{ind.valeur_cible or 0}",
                    pct_str,
                    (ind.categorie or "N/A")[:15],
                ]
            )

        table = Table(data, colWidths=[2.3 * inch, 1 * inch, 1 * inch, 1 * inch, 1.2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), secondary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        story.append(KeepTogether([table]))
        story.append(Spacer(1, 0.3 * inch))

        return story

    @staticmethod
    def _generate_synthese_section(
        session: Session,
        date_debut: date,
        date_fin: date,
        heading_style,
        normal_style,
        secondary_color,
        primary_color,
        accent_color,
    ) -> list:
        """Génère une synthèse exécutive"""
        story = []

        # Titre
        story.append(Paragraph("SYNTHÈSE EXÉCUTIVE", heading_style))

        # KPIs globaux
        kpis_objectifs = PerformanceService.get_kpis_objectifs(session)

        # Vue d'ensemble
        story.append(
            Paragraph(
                "Vue d'Ensemble",
                ParagraphStyle("SubHeading", parent=heading_style, fontSize=14, textColor=colors.HexColor("#667eea")),
            )
        )

        overview_data = [
            ["MÉTRIQUES CLÉS", "VALEUR", "STATUT"],
            ["Total Objectifs", str(kpis_objectifs.get("total_objectifs", 0)), "ℹ"],
            ["Objectifs Atteints", str(kpis_objectifs.get("objectifs_atteints", 0)), ""],
            ["Objectifs En Cours", str(kpis_objectifs.get("objectifs_en_cours", 0)), ""],
            ["Objectifs En Retard", str(kpis_objectifs.get("objectifs_en_retard", 0)), ""],
            ["Taux de Réalisation", f"{kpis_objectifs.get('taux_realisation', 0)}%", ""],
            ["Progression Moyenne", f"{kpis_objectifs.get('progression_moyenne', 0)}%", ""],
        ]

        overview_table = Table(overview_data, colWidths=[3 * inch, 2 * inch, 1.5 * inch])
        overview_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), secondary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    # Coloration conditionnelle pour les lignes
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        story.append(KeepTogether([overview_table]))
        story.append(Spacer(1, 0.4 * inch))

        # Analyse et recommandations
        story.append(Paragraph("Analyse et Recommandations", heading_style))

        taux_real = kpis_objectifs.get("taux_realisation", 0)

        if taux_real >= 80:
            analyse_color = colors.HexColor("#d1fae5")
            analyse_text = f"""
            <b>Performance Excellente 🎉</b><br/><br/>
            Avec un taux de réalisation de <b>{taux_real}%</b>, l'organisation démontre
            une excellente capacité d'exécution. La progression moyenne de
            <b>{kpis_objectifs.get("progression_moyenne", 0)}%</b> confirme la dynamique positive.<br/><br/>
            <b>Recommandations:</b><br/>
            • Maintenir le rythme actuel<br/>
            • Documenter les bonnes pratiques<br/>
            • Partager les succès avec les équipes
            """
        elif taux_real >= 60:
            analyse_color = colors.HexColor("#fef3c7")
            analyse_text = f"""
            <b>Performance Satisfaisante ✅</b><br/><br/>
            Le taux de réalisation de <b>{taux_real}%</b> est acceptable mais peut être amélioré.
            <b>{kpis_objectifs.get("objectifs_en_retard", 0)} objectif(s)</b> nécessitent une attention particulière.<br/><br/>
            <b>Recommandations:</b><br/>
            • Analyser les objectifs en retard<br/>
            • Renforcer le suivi hebdomadaire<br/>
            • Identifier les obstacles récurrents
            """
        else:
            analyse_color = colors.HexColor("#fee2e2")
            analyse_text = f"""
            <b>Performance À Améliorer ⚠️</b><br/><br/>
            Le taux de réalisation de <b>{taux_real}%</b> indique des difficultés importantes.
            Sur <b>{kpis_objectifs.get("total_objectifs", 0)} objectifs</b>,
            seulement <b>{kpis_objectifs.get("objectifs_atteints", 0)}</b> sont atteints.<br/><br/>
            <b>Actions prioritaires:</b><br/>
            • Revue urgente des objectifs en retard<br/>
            • Réaffectation des ressources si nécessaire<br/>
            • Redéfinir les objectifs irréalistes<br/>
            • Renforcer l'accompagnement des équipes
            """

        analyse_table = Table([[Paragraph(analyse_text, normal_style)]], colWidths=[6.5 * inch])
        analyse_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), analyse_color),
                    ("PADDING", (0, 0), (-1, -1), 15),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ]
            )
        )

        story.append(KeepTogether([analyse_table]))
        story.append(Spacer(1, 0.3 * inch))

        return story

    @staticmethod
    def _generate_comparative_section(
        session: Session,
        period: str,
        dates: dict[str, date],
        report_type: str,
        title_style,
        heading_style,
        normal_style,
        secondary_color,
        primary_color,
        accent_color,
    ) -> list:
        """Génère l'analyse comparative avec la période précédente"""
        story = []

        # Calculer la période précédente
        if period == "CURRENT_MONTH":
            # Mois précédent
            prev_fin = dates["debut"] - timedelta(days=1)
            prev_debut = prev_fin.replace(day=1)
            period_label = "mois précédent"
        elif period == "CURRENT_QUARTER":
            # Trimestre précédent
            current_quarter = (dates["debut"].month - 1) // 3
            if current_quarter == 0:
                prev_quarter = 3
                year = dates["debut"].year - 1
            else:
                prev_quarter = current_quarter - 1
                year = dates["debut"].year
            prev_debut = date(year, prev_quarter * 3 + 1, 1)
            prev_fin = date(year, (prev_quarter + 1) * 3, 1) - timedelta(days=1)
            period_label = "trimestre précédent"
        elif period == "CURRENT_YEAR":
            # Année précédente
            prev_debut = date(dates["debut"].year - 1, 1, 1)
            prev_fin = date(dates["debut"].year - 1, 12, 31)
            period_label = "année précédente"
        else:
            return story  # Pas de comparaison pour d'autres périodes

        story.append(PageBreak())
        story.append(Paragraph("ANALYSE COMPARATIVE", title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Introduction
        intro_text = f"""
        Cette section compare les performances de la période actuelle
        ({dates["debut"].strftime("%d/%m/%Y")} - {dates["fin"].strftime("%d/%m/%Y")})
        avec la période précédente ({prev_debut.strftime("%d/%m/%Y")} - {prev_fin.strftime("%d/%m/%Y")}).
        """
        story.append(
            Paragraph(
                intro_text,
                ParagraphStyle(
                    "Intro",
                    parent=normal_style,
                    fontSize=9,
                    textColor=colors.HexColor("#6b7280"),
                    alignment=TA_JUSTIFY,
                    leftIndent=10,
                    rightIndent=10,
                ),
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Note: Pour une vraie comparaison, il faudrait des données historiques
        # Pour l'instant, affichons un message explicatif
        note_text = """
        <b>📊 Évolution des Indicateurs Clés</b><br/><br/>

        Cette analyse comparative nécessite un historique de données pour la période précédente.<br/>
        Les éléments suivants seront comparés dès que l'historique sera disponible :<br/><br/>

        • <b>Taux de réalisation</b> : Évolution entre les deux périodes<br/>
        • <b>Nombre d'objectifs atteints</b> : Comparaison et tendance<br/>
        • <b>Progression moyenne</b> : Amélioration ou régression<br/>
        • <b>Indicateurs clés</b> : Variations significatives<br/><br/>

        <i>💡 Astuce : Pour activer l'analyse comparative, assurez-vous de générer régulièrement
        des rapports pour constituer un historique de référence.</i>
        """

        note_para = Paragraph(note_text, normal_style)
        note_table = Table([[note_para]], colWidths=[6.5 * inch])
        note_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                    ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#3b82f6")),
                    ("PADDING", (0, 0), (-1, -1), 20),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(note_table)
        story.append(Spacer(1, 0.3 * inch))

        # Placeholder pour future implémentation avec vraies données
        # TODO: Récupérer les rapports précédents et calculer les évolutions

        return story

    @staticmethod
    def _generate_notes_section(
        session: Session, report_type: str, heading_style, normal_style, secondary_color, primary_color, accent_color
    ) -> list:
        """Génère la section des notes et commentaires terrain"""
        story = []

        # Récupérer les données
        objectifs = PerformanceService.get_objectifs(session, limit=1000)
        indicateurs = PerformanceService.get_indicateurs(session, limit=1000)

        # Filtrer ceux avec commentaires
        objectifs_avec_commentaires = [obj for obj in objectifs if obj.commentaires and obj.commentaires.strip()]
        indicateurs_avec_commentaires = [ind for ind in indicateurs if ind.commentaires and ind.commentaires.strip()]

        # Si aucun commentaire, ne pas afficher la section
        if not objectifs_avec_commentaires and not indicateurs_avec_commentaires:
            return story

        # Titre de la section
        story.append(PageBreak())

        # Utiliser un tableau pour le titre avec fond coloré
        title_para = Paragraph(
            "NOTES ET OBSERVATIONS TERRAIN",
            ParagraphStyle(
                "NoteTitle", fontSize=20, textColor=colors.white, alignment=TA_CENTER, fontName="Helvetica-Bold"
            ),
        )
        title_table = Table([[title_para]], colWidths=[6.5 * inch])
        title_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), secondary_color),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 15),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
                ]
            )
        )
        story.append(title_table)
        story.append(Spacer(1, 0.3 * inch))

        # Introduction
        intro_text = """
        Cette section compile les observations et commentaires terrain fournis par les responsables
        durant le suivi des objectifs et indicateurs. Ces retours sont essentiels pour comprendre
        le contexte et les défis rencontrés.
        """
        story.append(
            Paragraph(
                intro_text,
                ParagraphStyle(
                    "Intro",
                    parent=normal_style,
                    fontSize=9,
                    textColor=colors.HexColor("#6b7280"),
                    alignment=TA_JUSTIFY,
                    leftIndent=10,
                    rightIndent=10,
                ),
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Notes sur les objectifs (si type GLOBAL ou OBJECTIFS)
        if report_type in ["GLOBAL", "OBJECTIFS"] and objectifs_avec_commentaires:
            story.append(Paragraph("📝 Commentaires sur les Objectifs", heading_style))
            story.append(Spacer(1, 0.2 * inch))

            for obj in objectifs_avec_commentaires:
                # Statut formaté
                if isinstance(obj.statut, StatutObjectif):
                    statut = obj.statut.value.replace("_", " ").title()
                else:
                    statut = str(obj.statut).replace("_", " ").title() if obj.statut else "Non défini"

                note_data = [
                    [Paragraph(f"<b>{obj.titre}</b>", normal_style)],
                    [
                        Paragraph(
                            f"Statut: {statut} | Service: {obj.service_responsable or 'N/A'}",
                            ParagraphStyle("Meta", parent=normal_style, fontSize=8, textColor=colors.grey),
                        )
                    ],
                    [Paragraph(f"<i>💬 {obj.commentaires}</i>", normal_style)],
                ]
                note_table = Table(note_data, colWidths=[6.5 * inch])
                note_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
                            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0f9ff")),
                            ("BACKGROUND", (0, 2), (-1, 2), colors.white),
                            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bae6fd")),
                            ("PADDING", (0, 0), (-1, -1), 8),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]
                    )
                )
                story.append(KeepTogether([note_table]))
                story.append(Spacer(1, 0.15 * inch))

            story.append(Spacer(1, 0.3 * inch))

        # Notes sur les indicateurs (si type GLOBAL ou INDICATEURS)
        if report_type in ["GLOBAL", "INDICATEURS"] and indicateurs_avec_commentaires:
            story.append(Paragraph("📊 Commentaires sur les Indicateurs", heading_style))
            story.append(Spacer(1, 0.2 * inch))

            for ind in indicateurs_avec_commentaires:
                note_data = [
                    [Paragraph(f"<b>{ind.nom}</b>", normal_style)],
                    [
                        Paragraph(
                            f"Catégorie: {ind.categorie or 'N/A'} | Service: {ind.service_responsable or 'N/A'}",
                            ParagraphStyle("Meta", parent=normal_style, fontSize=8, textColor=colors.grey),
                        )
                    ],
                    [Paragraph(f"<i>💬 {ind.commentaires}</i>", normal_style)],
                ]
                note_table = Table(note_data, colWidths=[6.5 * inch])
                note_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef3c7")),
                            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fefce8")),
                            ("BACKGROUND", (0, 2), (-1, 2), colors.white),
                            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fde68a")),
                            ("PADDING", (0, 0), (-1, -1), 8),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]
                    )
                )
                story.append(KeepTogether([note_table]))
                story.append(Spacer(1, 0.15 * inch))

        return story

    @staticmethod
    def _generate_conclusion_section(
        session: Session,
        dates: dict[str, date],
        report_type: str,
        title_style,
        heading_style,
        normal_style,
        secondary_color,
        primary_color,
        accent_color,
        system_settings,
    ) -> list:
        """Génère la conclusion du rapport"""
        story = []

        story.append(PageBreak())
        story.append(Paragraph("CONCLUSION ET PERSPECTIVES", title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Récupérer les KPIs
        kpis = PerformanceService.get_kpis_objectifs(session)
        objectifs = PerformanceService.get_objectifs(session, limit=1000)
        indicateurs = PerformanceService.get_indicateurs(session, limit=1000)

        taux_real = kpis.get("taux_realisation", 0)
        prog_moy = kpis.get("progression_moyenne", 0)

        # Texte de conclusion selon le type de rapport
        if report_type == "GLOBAL":
            conclusion_intro = "Au terme de cette analyse globale de la performance organisationnelle"
        elif report_type == "OBJECTIFS":
            conclusion_intro = "Au terme de cette analyse des objectifs de performance"
        elif report_type == "INDICATEURS":
            conclusion_intro = "Au terme de cette analyse des indicateurs de performance"
        else:  # SYNTHESE
            conclusion_intro = "Au terme de cette synthèse exécutive"

        conclusion_text = f"""
        <b>Bilan de la période</b><br/><br/>

        {conclusion_intro}, pour la période du {dates["debut"].strftime("%d/%m/%Y")} au {dates["fin"].strftime("%d/%m/%Y")},
        nous observons les résultats suivants :<br/><br/>
        """

        if report_type in ["GLOBAL", "OBJECTIFS", "SYNTHESE"]:
            conclusion_text += f"""
            • Taux de réalisation global : <b>{taux_real}%</b><br/>
            • Progression moyenne : <b>{prog_moy}%</b><br/>
            • Objectifs atteints : <b>{kpis.get("objectifs_atteints", 0)}</b> sur <b>{kpis.get("total_objectifs", 0)}</b><br/>
            • Objectifs en cours : <b>{kpis.get("objectifs_en_cours", 0)}</b><br/>
            • Objectifs en retard : <b>{kpis.get("objectifs_en_retard", 0)}</b><br/><br/>
            """

        if report_type in ["GLOBAL", "INDICATEURS"]:
            conclusion_text += f"""
            • Nombre d'indicateurs suivis : <b>{len(indicateurs)}</b><br/>
            • Indicateurs actifs : <b>{sum(1 for i in indicateurs if i.actif)}</b><br/><br/>
            """

        # Appréciation globale
        if taux_real >= 80:
            appreciation = "La performance globale est <b>excellente</b> et démontre une forte capacité d'exécution de l'organisation."
        elif taux_real >= 60:
            appreciation = (
                "La performance globale est <b>satisfaisante</b>, avec des marges de progression identifiées."
            )
        else:
            appreciation = "La performance nécessite une <b>attention prioritaire</b> pour redresser la trajectoire."

        conclusion_text += appreciation

        conclusion_para = Paragraph(conclusion_text, normal_style)
        conclusion_table = Table([[conclusion_para]], colWidths=[6.5 * inch])
        conclusion_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
                    ("BOX", (0, 0), (-1, -1), 2, secondary_color),
                    ("PADDING", (0, 0), (-1, -1), 20),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(conclusion_table)
        story.append(Spacer(1, 0.4 * inch))

        # Recommandations stratégiques
        story.append(Paragraph("💡 Recommandations Stratégiques", heading_style))
        story.append(Spacer(1, 0.2 * inch))

        recommendations = []

        if taux_real < 60:
            recommendations.extend(
                [
                    "• Organiser une revue stratégique urgente des objectifs en retard",
                    "• Renforcer l'allocation des ressources sur les priorités critiques",
                    "• Mettre en place un suivi hebdomadaire renforcé avec reporting quotidien",
                    "• Identifier les blocages et mettre en place des plans d'action correctifs",
                ]
            )
        elif taux_real < 80:
            recommendations.extend(
                [
                    "• Analyser les causes des retards et mettre en place des actions correctives ciblées",
                    "• Maintenir le rythme actuel sur les objectifs en cours",
                    "• Capitaliser sur les réussites et identifier les facteurs de succès",
                    "• Renforcer l'accompagnement des équipes sur les objectifs critiques",
                ]
            )
        else:
            recommendations.extend(
                [
                    "• Documenter les facteurs de succès pour les reproduire",
                    "• Partager les bonnes pratiques avec l'ensemble de l'organisation",
                    "• Envisager des objectifs plus ambitieux pour la prochaine période",
                    "• Maintenir la dynamique positive et célébrer les succès",
                ]
            )

        # Recommandations basées sur les commentaires
        objectifs_avec_commentaires = [obj for obj in objectifs if obj.commentaires]
        indicateurs_avec_commentaires = [ind for ind in indicateurs if ind.commentaires]

        if objectifs_avec_commentaires or indicateurs_avec_commentaires:
            recommendations.append("• Prendre en compte les observations terrain mentionnées dans les commentaires")

        rec_text = "<br/>".join(recommendations)
        rec_para = Paragraph(rec_text, normal_style)
        rec_table = Table([[rec_para]], colWidths=[6.5 * inch])
        rec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
                    ("BOX", (0, 0), (-1, -1), 2, primary_color),
                    ("PADDING", (0, 0), (-1, -1), 15),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(rec_table)
        story.append(Spacer(1, 0.3 * inch))

        # Message de clôture
        closing_text = """
        <b>Prochaines étapes</b><br/><br/>
        Ce rapport servira de base pour :<br/>
        • La revue de performance avec les équipes concernées<br/>
        • L'ajustement des objectifs et des moyens alloués<br/>
        • La définition des priorités pour la période suivante<br/>
        • Le suivi des actions correctives et préventives
        """

        closing_para = Paragraph(closing_text, normal_style)
        closing_table = Table([[closing_para]], colWidths=[6.5 * inch])
        closing_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                    ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#10b981")),
                    ("PADDING", (0, 0), (-1, -1), 15),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(closing_table)

        return story
