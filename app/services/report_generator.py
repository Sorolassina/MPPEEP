"""
Service de génération de rapports de performance
Génère des rapports PDF, Excel, etc.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import BytesIO
from sqlmodel import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image, KeepTogether, Frame, PageTemplate
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

from app.core.logging_config import get_logger
from app.services.performance_service import PerformanceService

logger = get_logger(__name__)


class ReportGenerator:
    """Générateur de rapports de performance"""
    
    @staticmethod
    def generate_pdf_report(
        session: Session,
        report_type: str,
        period: str,
        date_debut: Optional[date] = None,
        date_fin: Optional[date] = None,
        user_name: str = "Utilisateur"
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
            # Créer le buffer pour le PDF
            buffer = BytesIO()
            
            # Créer le document PDF
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#374151'),
                spaceAfter=12,
                spaceBefore=20,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#4b5563'),
                spaceAfter=6
            )
            
            # Contenu du document
            story = []
            
            # Calculer les dates selon la période
            dates = ReportGenerator._calculate_period_dates(period, date_debut, date_fin)
            
            # En-tête du rapport avec logo et informations
            # Titre principal
            story.append(Paragraph("📊 RAPPORT DE PERFORMANCE", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Tableau d'informations
            info_data = [
                ['Type de rapport', ReportGenerator._get_report_type_label(report_type)],
                ['Période couverte', f"Du {dates['debut'].strftime('%d/%m/%Y')} au {dates['fin'].strftime('%d/%m/%Y')}"],
                ['Date de génération', datetime.now().strftime('%d/%m/%Y à %H:%M')],
                ['Généré par', user_name]
            ]
            
            info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 0.5*inch))
            
            # Ligne de séparation
            line_data = [['─' * 100]]
            line_table = Table(line_data, colWidths=[6.5*inch])
            line_table.setStyle(TableStyle([
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#667eea')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
            ]))
            story.append(line_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Contenu selon le type de rapport
            if report_type in ['GLOBAL', 'OBJECTIFS']:
                story.extend(ReportGenerator._generate_objectifs_section(
                    session, dates['debut'], dates['fin'], heading_style, normal_style
                ))
            
            if report_type in ['GLOBAL', 'INDICATEURS']:
                story.extend(ReportGenerator._generate_indicateurs_section(
                    session, dates['debut'], dates['fin'], heading_style, normal_style
                ))
            
            if report_type == 'SYNTHESE':
                story.extend(ReportGenerator._generate_synthese_section(
                    session, dates['debut'], dates['fin'], heading_style, normal_style
                ))
            
            # Pied de page
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(
                f"<i>Rapport généré automatiquement par MPPEEP Dashboard - {datetime.now().year}</i>",
                ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
            ))
            
            # Construire le PDF
            doc.build(story)
            
            # Retourner au début du buffer
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport PDF: {e}")
            raise
    
    @staticmethod
    def _calculate_period_dates(period: str, date_debut: Optional[date], date_fin: Optional[date]) -> Dict[str, date]:
        """Calcule les dates de début et fin selon la période"""
        today = date.today()
        
        if period == 'CUSTOM' and date_debut and date_fin:
            return {'debut': date_debut, 'fin': date_fin}
        
        elif period == 'CURRENT_MONTH':
            debut = today.replace(day=1)
            # Dernier jour du mois
            if today.month == 12:
                fin = today.replace(day=31)
            else:
                fin = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        
        elif period == 'LAST_MONTH':
            fin = today.replace(day=1) - timedelta(days=1)
            debut = fin.replace(day=1)
        
        elif period == 'CURRENT_QUARTER':
            quarter = (today.month - 1) // 3
            debut = today.replace(month=quarter * 3 + 1, day=1)
            fin = today
        
        elif period == 'LAST_QUARTER':
            current_quarter = (today.month - 1) // 3
            if current_quarter == 0:
                last_quarter = 3
                year = today.year - 1
            else:
                last_quarter = current_quarter - 1
                year = today.year
            debut = date(year, last_quarter * 3 + 1, 1)
            fin = date(year, (last_quarter + 1) * 3, 1) - timedelta(days=1)
        
        elif period == 'CURRENT_YEAR':
            debut = today.replace(month=1, day=1)
            fin = today
        
        elif period == 'LAST_YEAR':
            debut = date(today.year - 1, 1, 1)
            fin = date(today.year - 1, 12, 31)
        
        else:
            debut = today.replace(day=1)
            fin = today
        
        return {'debut': debut, 'fin': fin}
    
    @staticmethod
    def _get_report_type_label(report_type: str) -> str:
        """Retourne le libellé du type de rapport"""
        labels = {
            'GLOBAL': 'Rapport Global de Performance',
            'OBJECTIFS': 'Rapport sur les Objectifs',
            'INDICATEURS': 'Rapport sur les Indicateurs',
            'SYNTHESE': 'Synthèse Exécutive'
        }
        return labels.get(report_type, report_type)
    
    @staticmethod
    def _generate_objectifs_section(
        session: Session, 
        date_debut: date, 
        date_fin: date,
        heading_style,
        normal_style
    ) -> List:
        """Génère la section objectifs du rapport"""
        story = []
        
        # Titre de section
        story.append(Paragraph("🎯 OBJECTIFS DE PERFORMANCE", heading_style))
        
        # Récupérer les objectifs
        objectifs = PerformanceService.get_objectifs(session, limit=1000)
        
        if not objectifs:
            story.append(Paragraph("Aucun objectif défini pour cette période.", normal_style))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        # KPIs des objectifs
        kpis = PerformanceService.get_kpis_objectifs(session)
        
        # Tableau récapitulatif
        data = [
            ['Métrique', 'Valeur'],
            ['Total objectifs', str(kpis.get('total_objectifs', 0))],
            ['Objectifs atteints', str(kpis.get('objectifs_atteints', 0))],
            ['Objectifs en cours', str(kpis.get('objectifs_en_cours', 0))],
            ['Objectifs en retard', str(kpis.get('objectifs_en_retard', 0))],
            ['Taux de réalisation', f"{kpis.get('taux_realisation', 0)}%"],
            ['Progression moyenne', f"{kpis.get('progression_moyenne', 0)}%"]
        ]
        
        table = Table(data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # Détails par statut
        objectifs_par_statut = {}
        for obj in objectifs:
            statut = obj.statut or 'Non défini'
            if statut not in objectifs_par_statut:
                objectifs_par_statut[statut] = []
            objectifs_par_statut[statut].append(obj)
        
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("📋 Détails par Statut", heading_style))
        
        # Tableau récapitulatif par statut
        for statut, objs in objectifs_par_statut.items():
            # Couleur selon le statut
            if 'ATTEINT' in statut.upper() or 'TERMINÉ' in statut.upper():
                bg_color = colors.HexColor('#d1fae5')
                text_color = colors.HexColor('#065f46')
            elif 'EN COURS' in statut.upper():
                bg_color = colors.HexColor('#dbeafe')
                text_color = colors.HexColor('#1e40af')
            elif 'RETARD' in statut.upper():
                bg_color = colors.HexColor('#fee2e2')
                text_color = colors.HexColor('#991b1b')
            else:
                bg_color = colors.HexColor('#f3f4f6')
                text_color = colors.HexColor('#374151')
            
            # En-tête de statut
            statut_header = Table([[f"● {statut} ({len(objs)} objectifs)"]], colWidths=[6.5*inch])
            statut_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('PADDING', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            story.append(statut_header)
            story.append(Spacer(1, 0.1*inch))
            
            # Liste des objectifs de ce statut (limiter à 5 par statut)
            for obj in objs[:5]:
                obj_data = [
                    ['Objectif', obj.titre],
                    ['Description', obj.description or 'N/A'],
                    ['Responsable', obj.responsable_nom or 'N/A'],
                    ['Service', obj.service_nom or 'N/A'],
                    ['Progression', f"{obj.progression_pourcentage}%"],
                    ['Valeur actuelle', f"{obj.valeur_actuelle or 0} {obj.unite}"],
                    ['Valeur cible', f"{obj.valeur_cible or 0} {obj.unite}"],
                    ['Échéance', obj.date_fin.strftime('%d/%m/%Y') if obj.date_fin else 'N/A']
                ]
                
                obj_table = Table(obj_data, colWidths=[1.5*inch, 5*inch])
                obj_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f9fafb')),
                    ('BACKGROUND', (1, 0), (1, -1), colors.white),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('PADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))
                
                story.append(obj_table)
                story.append(Spacer(1, 0.15*inch))
            
            if len(objs) > 5:
                story.append(Paragraph(
                    f"<i>... et {len(objs) - 5} autre(s) objectif(s) avec le statut '{statut}'</i>",
                    normal_style
                ))
            
            story.append(Spacer(1, 0.2*inch))
        
        return story
    
    @staticmethod
    def _generate_indicateurs_section(
        session: Session,
        date_debut: date,
        date_fin: date,
        heading_style,
        normal_style
    ) -> List:
        """Génère la section indicateurs du rapport"""
        story = []
        
        # Titre de section
        story.append(Paragraph("📊 INDICATEURS DE PERFORMANCE", heading_style))
        
        # Récupérer les indicateurs
        indicateurs = PerformanceService.get_indicateurs(session, limit=1000)
        
        if not indicateurs:
            story.append(Paragraph("Aucun indicateur défini pour cette période.", normal_style))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        # KPIs des indicateurs
        kpis_indicateurs = {
            'total': len(indicateurs),
            'par_categorie': {},
            'par_frequence': {}
        }
        
        for ind in indicateurs:
            cat = ind.categorie or 'Non catégorisé'
            freq = ind.frequence_maj or 'Non définie'
            kpis_indicateurs['par_categorie'][cat] = kpis_indicateurs['par_categorie'].get(cat, 0) + 1
            kpis_indicateurs['par_frequence'][freq] = kpis_indicateurs['par_frequence'].get(freq, 0) + 1
        
        # Tableau récapitulatif
        recap_data = [
            ['Total indicateurs', str(kpis_indicateurs['total'])],
            ['Catégories distinctes', str(len(kpis_indicateurs['par_categorie']))],
            ['Fréquences de mise à jour', str(len(kpis_indicateurs['par_frequence']))]
        ]
        
        recap_table = Table(recap_data, colWidths=[3*inch, 3.5*inch])
        recap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        story.append(recap_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Détails par catégorie
        story.append(Paragraph("📊 Indicateurs par Catégorie", heading_style))
        
        for categorie, inds_cat in kpis_indicateurs['par_categorie'].items():
            cat_data = [[f"● {categorie}: {inds_cat} indicateur(s)"]]
            cat_table = Table(cat_data, colWidths=[6.5*inch])
            cat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e0f2fe')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0369a1')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(cat_table)
            story.append(Spacer(1, 0.05*inch))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Tableau détaillé des indicateurs (top 15)
        story.append(Paragraph("📋 Top 15 Indicateurs", heading_style))
        
        data = [['Indicateur', 'Actuel', 'Cible', '% Atteinte', 'Catégorie']]
        
        for ind in indicateurs[:15]:
            # Calculer le % d'atteinte
            if ind.valeur_cible and ind.valeur_cible > 0:
                pct_atteinte = (float(ind.valeur_actuelle or 0) / float(ind.valeur_cible)) * 100
                pct_str = f"{pct_atteinte:.1f}%"
            else:
                pct_str = "N/A"
            
            data.append([
                ind.nom[:40] + '...' if len(ind.nom) > 40 else ind.nom,
                f"{ind.valeur_actuelle or 0}",
                f"{ind.valeur_cible or 0}",
                pct_str,
                (ind.categorie or 'N/A')[:15]
            ])
        
        table = Table(data, colWidths=[2.3*inch, 1*inch, 1*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    @staticmethod
    def _generate_synthese_section(
        session: Session,
        date_debut: date,
        date_fin: date,
        heading_style,
        normal_style
    ) -> List:
        """Génère une synthèse exécutive"""
        story = []
        
        # Titre
        story.append(Paragraph("📋 SYNTHÈSE EXÉCUTIVE", heading_style))
        
        # KPIs globaux
        kpis_objectifs = PerformanceService.get_kpis_objectifs(session)
        
        # Vue d'ensemble
        story.append(Paragraph("🎯 Vue d'Ensemble", 
            ParagraphStyle('SubHeading', parent=heading_style, fontSize=14, textColor=colors.HexColor('#667eea'))
        ))
        
        overview_data = [
            ['📊 MÉTRIQUES CLÉS', 'VALEUR', 'STATUT'],
            ['Total Objectifs', str(kpis_objectifs.get('total_objectifs', 0)), 'ℹ️'],
            ['Objectifs Atteints', str(kpis_objectifs.get('objectifs_atteints', 0)), '✅'],
            ['Objectifs En Cours', str(kpis_objectifs.get('objectifs_en_cours', 0)), '🔄'],
            ['Objectifs En Retard', str(kpis_objectifs.get('objectifs_en_retard', 0)), '⚠️'],
            ['Taux de Réalisation', f"{kpis_objectifs.get('taux_realisation', 0)}%", '📈'],
            ['Progression Moyenne', f"{kpis_objectifs.get('progression_moyenne', 0)}%", '📊']
        ]
        
        overview_table = Table(overview_data, colWidths=[3*inch, 2*inch, 1.5*inch])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Coloration conditionnelle pour les lignes
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(overview_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Analyse et recommandations
        story.append(Paragraph("💡 Analyse et Recommandations", heading_style))
        
        taux_real = kpis_objectifs.get('taux_realisation', 0)
        
        if taux_real >= 80:
            analyse_color = colors.HexColor('#d1fae5')
            analyse_text = f"""
            <b>Performance Excellente 🎉</b><br/><br/>
            Avec un taux de réalisation de <b>{taux_real}%</b>, l'organisation démontre 
            une excellente capacité d'exécution. La progression moyenne de 
            <b>{kpis_objectifs.get('progression_moyenne', 0)}%</b> confirme la dynamique positive.<br/><br/>
            <b>Recommandations:</b><br/>
            • Maintenir le rythme actuel<br/>
            • Documenter les bonnes pratiques<br/>
            • Partager les succès avec les équipes
            """
        elif taux_real >= 60:
            analyse_color = colors.HexColor('#fef3c7')
            analyse_text = f"""
            <b>Performance Satisfaisante ✅</b><br/><br/>
            Le taux de réalisation de <b>{taux_real}%</b> est acceptable mais peut être amélioré. 
            <b>{kpis_objectifs.get('objectifs_en_retard', 0)} objectif(s)</b> nécessitent une attention particulière.<br/><br/>
            <b>Recommandations:</b><br/>
            • Analyser les objectifs en retard<br/>
            • Renforcer le suivi hebdomadaire<br/>
            • Identifier les obstacles récurrents
            """
        else:
            analyse_color = colors.HexColor('#fee2e2')
            analyse_text = f"""
            <b>Performance À Améliorer ⚠️</b><br/><br/>
            Le taux de réalisation de <b>{taux_real}%</b> indique des difficultés importantes. 
            Sur <b>{kpis_objectifs.get('total_objectifs', 0)} objectifs</b>, 
            seulement <b>{kpis_objectifs.get('objectifs_atteints', 0)}</b> sont atteints.<br/><br/>
            <b>Actions prioritaires:</b><br/>
            • Revue urgente des objectifs en retard<br/>
            • Réaffectation des ressources si nécessaire<br/>
            • Redéfinir les objectifs irréalistes<br/>
            • Renforcer l'accompagnement des équipes
            """
        
        analyse_table = Table([[Paragraph(analyse_text, normal_style)]], colWidths=[6.5*inch])
        analyse_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), analyse_color),
            ('PADDING', (0, 0), (-1, -1), 15),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        
        story.append(analyse_table)
        story.append(Spacer(1, 0.3*inch))
        
        return story

