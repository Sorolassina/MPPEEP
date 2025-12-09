# app/api/v1/endpoints/performance.py
"""
Routes pour le module Performance
Système de gestion de la performance organisationnelle
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from typing import Any
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile, File as FastAPIFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlmodel import Session, select

from app.api.v1.endpoints.auth import require_roles, get_current_user
from app.core.logging_config import get_logger
from app.core.permission_decorators import require_data_access, require_module_dep
from app.db.session import get_session
from app.models.user import User
from app.models.personnel import Programme
from app.models.performance import (
    IndicateurPerformance,
    ObjectifPerformance,
    OrientationStrategique,
    RapportPerformance,
    ResultatStrategique,
    StatutObjectif,
)
from app.services.activity_service import ActivityService
from app.core.path_config import path_config
from app.services.performance_service import PerformanceService
from app.services.engagement_letter_service import EngagementLetterGenerator
from app.services.performance_engagement_letter_service import PerformanceEngagementLetterGenerator
from app.services.rapport_annuel_performance_generator_modular import RAPPDFGenerator
from app.services.report_generator import ReportGenerator
from app.services.cadre_performance_generator import CadrePerformanceGenerator

logger = get_logger(__name__)

router = APIRouter()


@router.get("/aide", response_class=HTMLResponse, name="aide_performance")
def aide_performance(request: Request):
    """Page d'aide pour le module Performance"""
    from app.templates import get_template_context, templates

    return templates.TemplateResponse("pages/aide_performance.html", get_template_context(request))


@router.get("", response_class=HTMLResponse, name="performance_home")
def performance_home(
    request: Request, 
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page d'accueil du module Performance"""
    # Vérifier l'accès au module Performance
    if not current_user.can_access_module("performance") and not current_user.is_guest:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=request.url_for("access_denied").include_query_params(module="performance"), status_code=302)
    
    try:
        from sqlmodel import func
        from decimal import Decimal

        from app.templates import get_template_context, templates
        from app.services.performance_service import PerformanceService

        # S'assurer que les valeurs actuelles sont à jour (calcul en cascade)
        # Note: Le calcul en cascade est aussi appelé dans get_kpis_objectifs, mais on le fait ici
        # pour garantir que les valeurs sont à jour avant de calculer les KPIs
        try:
            PerformanceService.calculer_valeurs_actuelles_cascade(db)
        except Exception as e:
            logger.warning(f"Erreur lors du calcul en cascade des valeurs actuelles: {e}")

        # Calculer les vrais KPIs depuis la base de données

        # Total objectifs
        total_objectifs = db.exec(select(func.count(ObjectifPerformance.id))).one() or 0

        # Objectifs atteints (statut = ATTEINT)
        objectifs_atteints = (
            db.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.ATTEINT)
            ).one()
            or 0
        )

        # Objectifs en cours
        objectifs_en_cours = (
            db.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.EN_COURS)
            ).one()
            or 0
        )

        # Objectifs en retard
        objectifs_en_retard = (
            db.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.EN_RETARD)
            ).one()
            or 0
        )

        # Total indicateurs
        total_indicateurs = db.exec(select(func.count(IndicateurPerformance.id))).one() or 0

        # Indicateurs en alerte (ceux qui n'ont pas atteint la cible)
        # Tenir compte du sens_appreciation :
        # - "haut" : alerte si valeur_actuelle < valeur_cible
        # - "bas" : alerte si valeur_actuelle > valeur_cible
        from sqlalchemy import or_, and_
        indicateurs_alerte = (
            db.exec(
                select(func.count(IndicateurPerformance.id)).where(
                    and_(
                        IndicateurPerformance.valeur_cible.isnot(None),
                        IndicateurPerformance.valeur_actuelle.isnot(None),
                        or_(
                            and_(
                                or_(
                                    IndicateurPerformance.sens_appreciation == "haut",
                                    IndicateurPerformance.sens_appreciation.is_(None)
                                ),
                                IndicateurPerformance.valeur_actuelle < IndicateurPerformance.valeur_cible
                            ),
                            and_(
                                IndicateurPerformance.sens_appreciation == "bas",
                                IndicateurPerformance.valeur_actuelle > IndicateurPerformance.valeur_cible
                            )
                        )
                    )
                )
            ).one()
            or 0
        )

        # Taux de réalisation moyen basé sur les valeurs actuelles vs valeurs cibles
        # Calculer la moyenne des taux de réalisation de tous les objectifs
        objectifs_avec_valeurs = db.exec(
            select(ObjectifPerformance).where(
                ObjectifPerformance.valeur_cible > 0
            )
        ).all()
        
        if objectifs_avec_valeurs:
            taux_realisation_list = []
            for obj in objectifs_avec_valeurs:
                if obj.valeur_cible and obj.valeur_cible > 0:
                    valeur_actuelle = obj.valeur_actuelle or Decimal('0')
                    taux = float(valeur_actuelle) / float(obj.valeur_cible) * 100
                    taux_realisation_list.append(min(taux, 100))  # Limiter à 100%
            
            if taux_realisation_list:
                taux_realisation = round(sum(taux_realisation_list) / len(taux_realisation_list), 1)
            else:
                taux_realisation = 0
        else:
            # Fallback: utiliser le nombre d'objectifs atteints
            if total_objectifs > 0:
                taux_realisation = round((objectifs_atteints / total_objectifs) * 100, 1)
            else:
                taux_realisation = 0

        # Score global basé sur le taux de réalisation moyen
        score_global = round(taux_realisation / 10, 1) if taux_realisation > 0 else 0

        # Nombre de rapports générés
        total_rapports = db.exec(select(func.count(RapportPerformance.id))).one() or 0

        # Données de démonstration pour les invités
        if current_user.is_guest:
            total_objectifs = 25
            objectifs_atteints = 18
            objectifs_en_cours = 5
            objectifs_en_retard = 2
            total_indicateurs = 45
            indicateurs_alerte = 8
            taux_realisation = 72.0
            score_global = 7.2
            total_rapports = 12

        context = get_template_context(request)

        # Récupérer les paramètres système pour les valeurs par défaut
        from app.services.system_settings_service import SystemSettingsService
        system_settings = SystemSettingsService.get_settings(db)

        current_year = datetime.now().year
        today_formatted = datetime.now().strftime("%d/%m/%Y")
        engagement_defaults = {
            "annee": EngagementLetterGenerator.DEFAULT_DATA.get("annee", current_year),
            "pays": EngagementLetterGenerator.DEFAULT_DATA.get("pays", ""),
            "devise": EngagementLetterGenerator.DEFAULT_DATA.get("devise", ""),
            "ministere": "Ministère du Patrimoine, du Portefeuille de l'État et des Entreprises Publiques",
            "ville": "Abidjan",
            "date": today_formatted,
            "programme": EngagementLetterGenerator.DEFAULT_DATA.get("programme_intitule", ""),
            "bop": EngagementLetterGenerator.DEFAULT_DATA.get("bop_intitule", ""),
            "rprog_nom": EngagementLetterGenerator.DEFAULT_DATA.get("rprog_nom", ""),
            "rprog_fonction": EngagementLetterGenerator.DEFAULT_DATA.get("rprog_fonction", ""),
            "rprog_photo": EngagementLetterGenerator.DEFAULT_DATA.get("rprog_photo", ""),
            "rbop_nom": EngagementLetterGenerator.DEFAULT_DATA.get("rbop_nom", ""),
            "rbop_fonction": EngagementLetterGenerator.DEFAULT_DATA.get("rbop_fonction", ""),
            "rbop_photo": EngagementLetterGenerator.DEFAULT_DATA.get("rbop_photo", ""),
            "decret_org_num": "",
            "decret_org_date": "",
            "decret_resp_num": "",
            "decret_resp_date": "",
            "logo_path": EngagementLetterGenerator.DEFAULT_DATA.get("logo_path", ""),
        }
        
        # Valeurs par défaut pour la lettre d'engagement de performance
        # Récupérer les valeurs du ministre depuis SystemSettings
        minister_civility_from_settings = system_settings.minister_civility or ""
        minister_name_from_settings = system_settings.minister_name or ""
        minister_role_from_settings = system_settings.minister_role or ""
        minister_photo_from_settings = system_settings.minister_photo or ""
        logo_path_from_settings = system_settings.logo_path or ""
        
        performance_engagement_defaults = {
            "annee": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("annee", current_year),
            "pays": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("pays", ""),
            "devise": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("devise", ""),
            "programme": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("programme_intitule", ""),
            "minister_civility": minister_civility_from_settings if minister_civility_from_settings else PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("minister_civility", ""),
            "minister_nom": minister_name_from_settings.upper() if minister_name_from_settings else PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("minister_nom", ""),
            "minister_fonction": minister_role_from_settings.upper() if minister_role_from_settings else PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("minister_fonction", ""),
            "minister_photo": minister_photo_from_settings if minister_photo_from_settings else PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("minister_photo", ""),
            "rprog_nom": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("rprog_nom", ""),
            "rprog_fonction": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("rprog_fonction", ""),
            "rprog_photo": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("rprog_photo", ""),
            "logo_path": logo_path_from_settings if logo_path_from_settings else PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("logo_path", ""),
            "ville": PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("ville_signature", "Abidjan"),
            "date": today_formatted,
        }

        # Valeurs par défaut pour le rapport annuel de performance
        rapport_annuel_defaults = {
            "annee": RAPPDFGenerator.DEFAULT_DATA.get("annee", current_year - 1),
            "section": RAPPDFGenerator.DEFAULT_DATA.get("section", "SECTION 376"),
            "ministere": RAPPDFGenerator.DEFAULT_DATA.get("ministere", ""),
            "titre_rapport": RAPPDFGenerator.DEFAULT_DATA.get("titre_rapport", ""),
            "titre_annee": RAPPDFGenerator.DEFAULT_DATA.get("titre_annee", "AU TITRE DE L'ANNÉE"),
            "date_publication": RAPPDFGenerator.DEFAULT_DATA.get("date_publication", ""),
            "logo_path": logo_path_from_settings if logo_path_from_settings else RAPPDFGenerator.DEFAULT_DATA.get("logo_path", ""),
        }
        # Générer la date de publication si non définie
        if not rapport_annuel_defaults.get("date_publication"):
            rapport_annuel_defaults["date_publication"] = datetime.now().strftime("%Y-%m")

        context.update(
            {
                "page_title": "Performance",
                "module_name": "Performance",
                "module_description": "Système de gestion de la performance organisationnelle",
                "kpis": {
                    "taux_realisation": taux_realisation,
                    "objectifs_atteints": objectifs_atteints,
                    "total_objectifs": total_objectifs,
                    "objectifs_en_cours": objectifs_en_cours,
                    "objectifs_en_retard": objectifs_en_retard,
                    "indicateurs_alerte": indicateurs_alerte,
                    "total_indicateurs": total_indicateurs,
                    "score_global": score_global,
                    "total_rapports": total_rapports,
                },
                "current_user": current_user,
                "engagement_defaults": engagement_defaults,
                "performance_engagement_defaults": performance_engagement_defaults,
                "rapport_annuel_defaults": rapport_annuel_defaults,
            }
        )

        return templates.TemplateResponse("pages/performance_home.html", context)

    except Exception as e:
        logger.error(f"Erreur lors du chargement de la page Performance: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/dashboard", response_class=HTMLResponse, name="performance_dashboard")
def performance_dashboard(request: Request, db: Session = Depends(get_session)):
    """Tableau de bord Performance"""
    try:
        from app.templates import get_template_context, templates

        context = get_template_context(request)
        context.update(
            {
                "page_title": "Tableau de Bord Performance",
                "module_name": "Performance",
                "module_description": "Indicateurs et métriques de performance",
            }
        )

        return templates.TemplateResponse("pages/performance_dashboard.html", context)

    except Exception as e:
        logger.error(f"Erreur lors du chargement du dashboard Performance: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/lettres-engagement/pdf",
    response_class=StreamingResponse,
    name="performance_lettres_engagement_pdf",
)
def generate_lettre_engagement_pdf(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Génère la couverture de la lettre d'engagement opérationnel."""
    try:
        data: dict[str, Any] = {}

        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            data[target_key] = transform(value) if transform else value

        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("pays", "pays")
        optional_param("devise", "devise")
        optional_param("ministere", "ministere")
        optional_param("ville", "ville_signature")
        optional_param("date", "date_signature")
        optional_param("programme", "programme_intitule")
        optional_param("bop", "bop_intitule")
        optional_param("rprog_nom", "rprog_nom")
        optional_param("rprog_fonction", "rprog_fonction")
        optional_param("rprog_photo", "rprog_photo")
        optional_param("rbop_nom", "rbop_nom")
        optional_param("rbop_fonction", "rbop_fonction")
        optional_param("rbop_photo", "rbop_photo")
        optional_param("decret_org_num", "decret_org_num")
        optional_param("decret_org_date", "decret_org_date")
        optional_param("decret_resp_num", "decret_resp_num")
        optional_param("decret_resp_date", "decret_resp_date")
        optional_param("logo_path", "logo_path")

        pdf_buffer = EngagementLetterGenerator.generate_pdf(data)

        year = data.get("annee", EngagementLetterGenerator.DEFAULT_DATA.get("annee", "2025"))

        headers = {
            "Content-Disposition": f"inline; filename=lettre_engagement_{year}.pdf",
        }
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
    except Exception as exc:
        logger.exception("Erreur génération lettre d'engagement: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de la lettre d'engagement")


@router.get(
    "/lettres-engagement/docx",
    response_class=StreamingResponse,
    name="performance_lettres_engagement_docx",
)
def generate_lettre_engagement_docx(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Génère la lettre d'engagement opérationnel et la convertit en document Word (.docx).
    
    Cette fonctionnalité permet aux utilisateurs de modifier la lettre dans Word
    au cas où ils souhaiteraient y apporter des modifications.
    
    Le processus :
    1. Génère le PDF de la lettre (même processus que /pdf)
    2. Convertit le PDF en Word via Adobe PDF Services
    3. Retourne le document Word pour téléchargement
    """
    try:
        from app.services.pdf_to_word_service import PDFToWordService
        
        # Récupérer les paramètres de conversion
        use_ocr = request.query_params.get("ocr", "false").lower() == "true"
        
        data: dict[str, Any] = {}

        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            data[target_key] = transform(value) if transform else value

        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("pays", "pays")
        optional_param("devise", "devise")
        optional_param("ministere", "ministere")
        optional_param("ville", "ville_signature")
        optional_param("date", "date_signature")
        optional_param("programme", "programme_intitule")
        optional_param("bop", "bop_intitule")
        optional_param("rprog_nom", "rprog_nom")
        optional_param("rprog_fonction", "rprog_fonction")
        optional_param("rprog_photo", "rprog_photo")
        optional_param("rbop_nom", "rbop_nom")
        optional_param("rbop_fonction", "rbop_fonction")
        optional_param("rbop_photo", "rbop_photo")
        optional_param("decret_org_num", "decret_org_num")
        optional_param("decret_org_date", "decret_org_date")
        optional_param("decret_resp_num", "decret_resp_num")
        optional_param("decret_resp_date", "decret_resp_date")
        optional_param("logo_path", "logo_path")

        # Étape 1: Générer le PDF
        logger.info("📄 Génération du PDF de la lettre d'engagement...")
        pdf_buffer = EngagementLetterGenerator.generate_pdf(data)

        # Étape 2: Convertir le PDF en Word
        logger.info("🔄 Conversion PDF → Word en cours...")
        word_buffer = PDFToWordService.convert_pdf_to_word(pdf_buffer, use_ocr=use_ocr)

        year = data.get("annee", EngagementLetterGenerator.DEFAULT_DATA.get("annee", "2025"))

        headers = {
            "Content-Disposition": f"attachment; filename=lettre_engagement_{year}.docx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        
        logger.info("✅ Document Word généré avec succès")
        return StreamingResponse(word_buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)
        
    except ValueError as e:
        # Erreur de configuration (credentials manquants)
        logger.error(f"❌ Erreur de configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration manquante pour la conversion PDF → Word: {e}"
        )
    except ImportError as e:
        # SDK non installé
        logger.error(f"❌ SDK non installé: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Le SDK Adobe PDF Services n'est pas installé. Installez-le avec: pip install pdfservices-sdk"
        )
    except Exception as exc:
        logger.exception("Erreur conversion lettre d'engagement en Word: %s", exc)
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la conversion de la lettre d'engagement en Word: {str(exc)}"
        )


@router.get(
    "/lettres-engagement-performance/pdf",
    response_class=StreamingResponse,
    name="performance_lettres_engagement_performance_pdf",
)
def generate_lettre_engagement_performance_pdf(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Génère la lettre d'engagement de performance."""
    try:
        data: dict[str, Any] = {}

        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            data[target_key] = transform(value) if transform else value

        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("pays", "pays")
        optional_param("devise", "devise")
        optional_param("programme", "programme_intitule")
        optional_param("minister_civility", "minister_civility")
        optional_param("minister_nom", "minister_nom")
        optional_param("minister_fonction", "minister_fonction")
        optional_param("minister_photo", "minister_photo")
        optional_param("dg_nom", "dg_nom")
        optional_param("dg_fonction", "dg_fonction")
        optional_param("rprog_nom", "rprog_nom")
        optional_param("rprog_fonction", "rprog_fonction")
        optional_param("rprog_photo", "rprog_photo")
        optional_param("logo_path", "logo_path")
        optional_param("ville", "ville_signature")
        optional_param("date", "date_signature")

        pdf_buffer = PerformanceEngagementLetterGenerator.generate_pdf(data)

        year = data.get("annee", PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("annee", "2025"))

        headers = {
            "Content-Disposition": f"inline; filename=lettre_engagement_performance_{year}.pdf",
        }
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
    except Exception as exc:
        logger.exception("Erreur génération lettre d'engagement de performance: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de la lettre d'engagement de performance")


@router.get(
    "/lettres-engagement-performance/docx",
    response_class=StreamingResponse,
    name="performance_lettres_engagement_performance_docx",
)
def generate_lettre_engagement_performance_docx(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Génère la lettre d'engagement de performance et la convertit en document Word (.docx).
    
    Cette fonctionnalité permet aux utilisateurs de modifier la lettre dans Word
    au cas où ils souhaiteraient y apporter des modifications.
    
    Le processus :
    1. Génère le PDF de la lettre (même processus que /pdf)
    2. Convertit le PDF en Word via Adobe PDF Services
    3. Retourne le document Word pour téléchargement
    """
    try:
        from app.services.pdf_to_word_service import PDFToWordService
        
        # Récupérer les paramètres de conversion
        use_ocr = request.query_params.get("ocr", "false").lower() == "true"
        
        data: dict[str, Any] = {}

        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            data[target_key] = transform(value) if transform else value

        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("pays", "pays")
        optional_param("devise", "devise")
        optional_param("programme", "programme_intitule")
        optional_param("minister_civility", "minister_civility")
        optional_param("minister_nom", "minister_nom")
        optional_param("minister_fonction", "minister_fonction")
        optional_param("minister_photo", "minister_photo")
        optional_param("dg_nom", "dg_nom")
        optional_param("dg_fonction", "dg_fonction")
        optional_param("rprog_nom", "rprog_nom")
        optional_param("rprog_fonction", "rprog_fonction")
        optional_param("rprog_photo", "rprog_photo")
        optional_param("logo_path", "logo_path")
        optional_param("ville", "ville_signature")
        optional_param("date", "date_signature")

        # Étape 1: Générer le PDF
        logger.info("📄 Génération du PDF de la lettre d'engagement de performance...")
        pdf_buffer = PerformanceEngagementLetterGenerator.generate_pdf(data)

        # Étape 2: Convertir le PDF en Word
        logger.info("🔄 Conversion PDF → Word en cours...")
        word_buffer = PDFToWordService.convert_pdf_to_word(pdf_buffer, use_ocr=use_ocr)

        year = data.get("annee", PerformanceEngagementLetterGenerator.DEFAULT_DATA.get("annee", "2025"))

        headers = {
            "Content-Disposition": f"attachment; filename=lettre_engagement_performance_{year}.docx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        
        logger.info("✅ Document Word généré avec succès")
        return StreamingResponse(word_buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)
        
    except ValueError as e:
        # Erreur de configuration (credentials manquants)
        logger.error(f"❌ Erreur de configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration manquante pour la conversion PDF → Word: {e}"
        )
    except ImportError as e:
        # SDK non installé
        logger.error(f"❌ SDK non installé: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Le SDK Adobe PDF Services n'est pas installé. Installez-le avec: pip install pdfservices-sdk"
        )
    except Exception as exc:
        logger.exception("Erreur conversion lettre d'engagement de performance en Word: %s", exc)
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la conversion de la lettre d'engagement de performance en Word: {str(exc)}"
        )


@router.get(
    "/cadre-performance/pdf",
    response_class=StreamingResponse,
    name="performance_cadre_performance_pdf",
)
def generate_cadre_performance_pdf(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Génère le cadre de performance en PDF."""
    try:
        # Récupérer les paramètres
        programme_id = request.query_params.get("programme_id")
        programme_id = int(programme_id) if programme_id and programme_id.isdigit() else None
        
        annee_reference = request.query_params.get("annee_reference")
        annee_reference = int(annee_reference) if annee_reference and annee_reference.isdigit() else None
        
        annee_redaction = request.query_params.get("annee_redaction")
        annee_redaction = int(annee_redaction) if annee_redaction and annee_redaction.isdigit() else None
        
        titre = request.query_params.get("titre")
        
        mode = request.query_params.get("mode", "brouillon")
        mode = mode if mode in ["brouillon", "final"] else "brouillon"
        
        # Générer le PDF
        pdf_buffer = CadrePerformanceGenerator.generate_pdf(
            session=db,
            programme_id=programme_id,
            annee_reference=annee_reference,
            annee_redaction=annee_redaction,
            titre=titre,
            mode=mode
        )
        
        # Nom du fichier
        if programme_id:
            programme = db.exec(
                select(Programme).where(Programme.id == programme_id)
            ).first()
            filename = f"cadre_performance_{programme.code if programme else programme_id}.pdf"
        else:
            filename = "cadre_performance_ministere.pdf"
        
        headers = {
            "Content-Disposition": f"inline; filename={filename}",
        }
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
    except Exception as exc:
        logger.exception("Erreur génération cadre de performance: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du cadre de performance")


@router.get(
    "/cadre-performance/docx",
    response_class=StreamingResponse,
    name="performance_cadre_performance_docx",
)
def generate_cadre_performance_docx(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Génère le cadre de performance et le convertit en document Word (.docx).
    
    Cette fonctionnalité permet aux utilisateurs de modifier le cadre dans Word
    au cas où ils souhaiteraient y apporter des modifications.
    """
    try:
        from app.services.pdf_to_word_service import PDFToWordService
        
        # Récupérer les paramètres de conversion
        use_ocr = request.query_params.get("ocr", "false").lower() == "true"
        
        # Récupérer les paramètres
        programme_id = request.query_params.get("programme_id")
        programme_id = int(programme_id) if programme_id and programme_id.isdigit() else None
        
        annee_reference = request.query_params.get("annee_reference")
        annee_reference = int(annee_reference) if annee_reference and annee_reference.isdigit() else None
        
        annee_redaction = request.query_params.get("annee_redaction")
        annee_redaction = int(annee_redaction) if annee_redaction and annee_redaction.isdigit() else None
        
        titre = request.query_params.get("titre")
        
        mode = request.query_params.get("mode", "brouillon")
        mode = mode if mode in ["brouillon", "final"] else "brouillon"
        
        # Étape 1: Générer le PDF
        logger.info("📄 Génération du PDF du cadre de performance...")
        pdf_buffer = CadrePerformanceGenerator.generate_pdf(
            session=db,
            programme_id=programme_id,
            annee_reference=annee_reference,
            annee_redaction=annee_redaction,
            titre=titre,
            mode=mode
        )
        
        # Étape 2: Convertir le PDF en Word
        logger.info("🔄 Conversion PDF → Word en cours...")
        word_buffer = PDFToWordService.convert_pdf_to_word(pdf_buffer, use_ocr=use_ocr)
        
        # Nom du fichier
        if programme_id:
            programme = db.exec(
                select(Programme).where(Programme.id == programme_id)
            ).first()
            filename = f"cadre_performance_{programme.code if programme else programme_id}.docx"
        else:
            filename = "cadre_performance_ministere.docx"
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        
        logger.info("✅ Document Word généré avec succès")
        return StreamingResponse(word_buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)
        
    except ValueError as e:
        logger.error(f"❌ Erreur de configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration manquante pour la conversion PDF → Word: {e}"
        )
    except ImportError as e:
        logger.error(f"❌ SDK non installé: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Le SDK Adobe PDF Services n'est pas installé. Installez-le avec: pip install pdfservices-sdk"
        )
    except Exception as exc:
        logger.exception("Erreur conversion cadre de performance en Word: %s", exc)
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la conversion du cadre de performance en Word: {str(exc)}"
        )


@router.get(
    "/api/rapport-annuel-performance/rap-data",
    response_class=JSONResponse,
    name="get_rap_data_api",
)
def get_rap_data_api(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Récupère toutes les données du Rapport Annuel de Performance (RAP) depuis la base de données"""
    try:
        import json
        from app.services.rap_data_service import RapDataService
        from app.services.system_settings_service import SystemSettingsService
        
        def _parse_financement_interpretations(financement_json: str | None) -> dict:
            """Parse les interprétations de financement depuis JSON"""
            if not financement_json:
                return {}
            try:
                return json.loads(financement_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        
        def _parse_conclusion_interpretations(conclusion_json: str | None) -> dict:
            """Parse les interprétations de conclusion depuis JSON"""
            if not conclusion_json:
                return {}
            try:
                return json.loads(conclusion_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        
        # Charger RapData
        rap_data = RapDataService.get_rap_data(db)
        
        # Parser les interprétations de financement
        financement_data = _parse_financement_interpretations(rap_data.financement_interpretations)
        
        # Parser les interprétations de conclusion
        conclusion_data = _parse_conclusion_interpretations(rap_data.conclusion_interpretations)
        
        # Charger SystemSettings pour les données d'introduction
        settings = SystemSettingsService.get_settings(db)
        
        # Construire le nom complet du ministre
        ministre_nom = ""
        if settings.minister_civility and settings.minister_name:
            ministre_nom = f"{settings.minister_civility} {settings.minister_name}"
        elif settings.minister_name:
            ministre_nom = settings.minister_name
        
        # Calculer la structure organisationnelle
        structure_org = RapDataService.calculate_organization_structure(db)
        
        # Extraire le nom du ministère
        ministere = ""
        if settings.minister_role:
            minister_role_upper = settings.minister_role.upper().strip()
            if "MINISTRE" in minister_role_upper or "MINISTERE" in minister_role_upper:
                ministere = minister_role_upper.replace("MINISTRE", "MINISTERE")
                import re
                ministere = re.sub(r'\s+', ' ', ministere).strip()
        elif settings.company_name:
            company_name_upper = settings.company_name.upper().strip()
            if "MINISTERE" in company_name_upper or "MPPEEP" in company_name_upper:
                ministere = company_name_upper
        
        # Générer l'année par défaut (année en cours ou précédente)
        from datetime import datetime
        current_year = datetime.now().year
        default_annee = current_year
        
        # Récupérer l'année depuis les paramètres si disponible (à implémenter si nécessaire)
        # Pour l'instant, on utilise l'année en cours comme défaut
        
        # Générer la date de publication par défaut (mois actuel et année) en format ISO "YYYY-MM"
        now = datetime.now()
        default_date_publication = now.strftime("%Y-%m")
        
        # Récupérer les informations générales du rapport depuis RapData
        if rap_data.annee:
            default_annee = rap_data.annee
        
        if rap_data.date_publication:
            # Garder le format ISO "YYYY-MM" pour les champs HTML de type "month"
            # Si la date est déjà en format ISO, l'utiliser directement
            if re.match(r'^\d{4}-\d{2}$', rap_data.date_publication.strip()):
                default_date_publication = rap_data.date_publication.strip()
            else:
                # Si la date est en format français, la convertir en ISO
                from app.utils.helpers import convert_french_month_to_iso_str
                iso_date = convert_french_month_to_iso_str(rap_data.date_publication)
                if iso_date:
                    default_date_publication = iso_date
                else:
                    # Fallback: utiliser la valeur telle quelle
                    default_date_publication = rap_data.date_publication.strip()
        
        return {
            "success": True,
            "data": {
                # Données RapData
                "contexte_texte": rap_data.contexte_texte or "",
                "rapport_structure_premiere_partie": rap_data.rapport_structure_premiere_partie or "",
                "rapport_structure_seconde_partie": rap_data.rapport_structure_seconde_partie or "",
                
                # Données d'introduction depuis SystemSettings
                "ministre_nom": ministre_nom,
                "ministre_date_nomination": getattr(settings, "minister_nomination_date", "") or "",
                "decret_attribution_numero": getattr(settings, "decret_attribution_numero", "") or "",
                "decret_attribution_date": getattr(settings, "decret_attribution_date", "") or "",
                "mission_ministere": settings.ministry_mission or "",
                "structure_cabinet": getattr(settings, "structure_cabinet", "") or "",
                "decret_organisation_numero": getattr(settings, "decret_organisation_numero", "") or "",
                "decret_organisation_date": getattr(settings, "decret_organisation_date", "") or "",
                
                # Structure organisationnelle calculée automatiquement
                "nb_directions_centrales": structure_org.get("nb_directions_centrales", 0),
                "nb_services": structure_org.get("nb_services", 0),
                "nb_directions_generales": structure_org.get("nb_directions_generales", 0),
                
                # Informations générales
                "ministere": ministere,
                "section": getattr(settings, "section", "") or "",
                "annee": default_annee,  # Année depuis DB ou année en cours
                "pays": getattr(settings, "pays", "") or "",
                "devise": getattr(settings, "devise", "") or "",
                "logo_path": settings.logo_path or "",
                "date_publication": default_date_publication,  # Date de publication depuis RapData ou mois actuel
                "titre_rapport": rap_data.titre_rapport or "",  # Titre depuis RapData
                "titre_annee": rap_data.titre_annee or "AU TITRE DE L'ANNÉE",  # Titre année depuis RapData
                
                # Données de financement (interprétations personnalisées)
                "financement_interpretations": financement_data,
                "financement_raisons": "\n".join(financement_data.get("raisons_augmentation", [])),
                "financement_note_comparaison": financement_data.get("note_comparaison", ""),
                "financement_analyse_personnel": financement_data.get("analyse_personnel_commentaire", ""),
                "financement_analyse_biens": financement_data.get("analyse_biens_commentaire", ""),
                "financement_analyse_transferts": financement_data.get("analyse_transferts_commentaire", ""),
                "financement_analyse_investissements": financement_data.get("analyse_investissements_commentaire", ""),
                # Données de conclusion par programme (structure: { "code_programme": { "points_positifs": [...], ... } })
                "conclusion_interpretations": conclusion_data,
            }
        }
    except Exception as e:
        logger.error(f"❌ Erreur récupération données RAP: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post(
    "/api/rapport-annuel-performance/save",
    response_class=JSONResponse,
    name="save_rap_data_api",
)
def save_rap_data_api(
    # Données RapData
    rap_contexte_texte: str | None = Form(None),
    rap_rapport_structure_premiere_partie: str | None = Form(None),
    rap_rapport_structure_seconde_partie: str | None = Form(None),
    # Données d'introduction pour SystemSettings
    rap_ministre_nom: str | None = Form(None),
    rap_ministre_date_nomination: str | None = Form(None),
    rap_decret_attribution_numero: str | None = Form(None),
    rap_decret_attribution_date: str | None = Form(None),
    rap_mission_ministere: str | None = Form(None),
    rap_structure_cabinet: str | None = Form(None),
    rap_decret_organisation_numero: str | None = Form(None),
    rap_decret_organisation_date: str | None = Form(None),
    # Informations générales pour SystemSettings
    rap_section: str | None = Form(None),
    rap_ministere: str | None = Form(None),
    rap_logo_path: str | None = Form(None),
    # Informations générales pour le rapport lui-même (non SystemSettings)
    annee: int | None = Form(None),
    titre_rapport: str | None = Form(None),
    titre_annee: str | None = Form(None),
    date_publication: str | None = Form(None),
    # Données de financement (interprétations personnalisées)
    rap_financement_raisons: str | None = Form(None),
    rap_financement_note_comparaison: str | None = Form(None),
    rap_financement_analyse_personnel: str | None = Form(None),
    rap_financement_analyse_biens: str | None = Form(None),
    rap_financement_analyse_transferts: str | None = Form(None),
    rap_financement_analyse_investissements: str | None = Form(None),
    # Données de conclusion par programme (points positifs, difficultés, recommandations, conclusion)
    rap_conclusion_programme_code: str | None = Form(None),
    rap_conclusion_points_positifs: str | None = Form(None),
    rap_conclusion_difficultes: str | None = Form(None),
    rap_conclusion_recommandations: str | None = Form(None),
    rap_conclusion_conclusion: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Sauvegarde toutes les données du RAP dans la base de données (RapData + SystemSettings)"""
    try:
        from app.services.rap_data_service import RapDataService
        from app.services.system_settings_service import SystemSettingsService
        from app.services.activity_service import ActivityService
        
        user_id = current_user.id if hasattr(current_user, "id") else 1
        
        # 1. Sauvegarder dans RapData
        rap_data_params = {}
        if rap_contexte_texte is not None and rap_contexte_texte.strip():
            rap_data_params["contexte_texte"] = rap_contexte_texte.strip()
        if rap_rapport_structure_premiere_partie is not None and rap_rapport_structure_premiere_partie.strip():
            rap_data_params["rapport_structure_premiere_partie"] = rap_rapport_structure_premiere_partie.strip()
        if rap_rapport_structure_seconde_partie is not None and rap_rapport_structure_seconde_partie.strip():
            rap_data_params["rapport_structure_seconde_partie"] = rap_rapport_structure_seconde_partie.strip()
        
        # Ajouter les informations générales du rapport dans RapData
        if annee is not None:
            rap_data_params["annee"] = annee
        if titre_rapport is not None and titre_rapport.strip():
            rap_data_params["titre_rapport"] = titre_rapport.strip()
        if titre_annee is not None and titre_annee.strip():
            rap_data_params["titre_annee"] = titre_annee.strip()
        if date_publication is not None and date_publication.strip():
            # Convertir le format français "Mois AAAA" vers ISO "AAAA-MM" si nécessaire
            from app.utils.helpers import convert_french_month_to_iso_str
            iso_date = convert_french_month_to_iso_str(date_publication.strip())
            if iso_date:
                rap_data_params["date_publication"] = iso_date
            else:
                rap_data_params["date_publication"] = date_publication.strip()
        elif date_publication is None or not date_publication.strip():
            # Si vide, utiliser le mois et l'année actuels
            from datetime import datetime
            now = datetime.now()
            rap_data_params["date_publication"] = now.strftime("%Y-%m")
        
        # Construire le dictionnaire des interprétations de financement
        import json
        financement_interpretations = {}
        if rap_financement_raisons and rap_financement_raisons.strip():
            # Convertir la liste de raisons (une par ligne) en tableau
            raisons_list = [r.strip() for r in rap_financement_raisons.strip().split("\n") if r.strip()]
            if raisons_list:
                financement_interpretations["raisons_augmentation"] = raisons_list
        if rap_financement_note_comparaison and rap_financement_note_comparaison.strip():
            financement_interpretations["note_comparaison"] = rap_financement_note_comparaison.strip()
        if rap_financement_analyse_personnel and rap_financement_analyse_personnel.strip():
            financement_interpretations["analyse_personnel_commentaire"] = rap_financement_analyse_personnel.strip()
        if rap_financement_analyse_biens and rap_financement_analyse_biens.strip():
            financement_interpretations["analyse_biens_commentaire"] = rap_financement_analyse_biens.strip()
        if rap_financement_analyse_transferts and rap_financement_analyse_transferts.strip():
            financement_interpretations["analyse_transferts_commentaire"] = rap_financement_analyse_transferts.strip()
        if rap_financement_analyse_investissements and rap_financement_analyse_investissements.strip():
            financement_interpretations["analyse_investissements_commentaire"] = rap_financement_analyse_investissements.strip()
        
        # Sauvegarder les interprétations de financement en JSON
        if financement_interpretations:
            rap_data_params["financement_interpretations"] = json.dumps(financement_interpretations, ensure_ascii=False)
        
        # Construire les interprétations de conclusion par programme
        # Charger les données existantes pour préserver les autres programmes
        existing_conclusion_data = {}
        rap_data_existing = RapDataService.get_rap_data(db)
        if rap_data_existing.conclusion_interpretations:
            try:
                existing_conclusion_data = json.loads(rap_data_existing.conclusion_interpretations) if isinstance(rap_data_existing.conclusion_interpretations, str) else rap_data_existing.conclusion_interpretations
            except (json.JSONDecodeError, TypeError):
                existing_conclusion_data = {}
        
        # Ajouter/mettre à jour les données pour le programme sélectionné
        if rap_conclusion_programme_code:
            programme_data = {}
            if rap_conclusion_points_positifs and rap_conclusion_points_positifs.strip():
                # Convertir la liste de points positifs (une par ligne) en tableau
                points_list = [p.strip() for p in rap_conclusion_points_positifs.strip().split("\n") if p.strip()]
                if points_list:
                    programme_data["points_positifs"] = points_list
            if rap_conclusion_difficultes and rap_conclusion_difficultes.strip():
                programme_data["difficultes"] = rap_conclusion_difficultes.strip()
            if rap_conclusion_recommandations and rap_conclusion_recommandations.strip():
                programme_data["recommandations"] = rap_conclusion_recommandations.strip()
            if rap_conclusion_conclusion and rap_conclusion_conclusion.strip():
                programme_data["conclusion"] = rap_conclusion_conclusion.strip()
            
            # Mettre à jour les données pour ce programme
            if programme_data:
                existing_conclusion_data[rap_conclusion_programme_code] = programme_data
        
        # Sauvegarder les interprétations de conclusion en JSON (structure par programme)
        if existing_conclusion_data:
            rap_data_params["conclusion_interpretations"] = json.dumps(existing_conclusion_data, ensure_ascii=False)
        
        if rap_data_params:
            RapDataService.update_rap_data(db_session=db, user_id=user_id, **rap_data_params)
            logger.info(f"✅ Données RapData sauvegardées par {current_user.email}")
        
        # 2. Sauvegarder dans SystemSettings (données d'introduction)
        settings_params = {}
        
        # Parser le nom du ministre (civilité + nom)
        if rap_ministre_nom and rap_ministre_nom.strip():
            ministre_parts = rap_ministre_nom.strip().split(" ", 1)
            if len(ministre_parts) >= 2:
                settings_params["minister_civility"] = ministre_parts[0]
                settings_params["minister_name"] = ministre_parts[1]
            else:
                settings_params["minister_name"] = rap_ministre_nom.strip()
        
        if rap_ministre_date_nomination and rap_ministre_date_nomination.strip():
            settings_params["minister_nomination_date"] = rap_ministre_date_nomination.strip()
        if rap_decret_attribution_numero and rap_decret_attribution_numero.strip():
            settings_params["decret_attribution_numero"] = rap_decret_attribution_numero.strip()
        if rap_decret_attribution_date and rap_decret_attribution_date.strip():
            settings_params["decret_attribution_date"] = rap_decret_attribution_date.strip()
        if rap_mission_ministere and rap_mission_ministere.strip():
            settings_params["ministry_mission"] = rap_mission_ministere.strip()
        if rap_structure_cabinet and rap_structure_cabinet.strip():
            settings_params["structure_cabinet"] = rap_structure_cabinet.strip()
        if rap_decret_organisation_numero and rap_decret_organisation_numero.strip():
            settings_params["decret_organisation_numero"] = rap_decret_organisation_numero.strip()
        if rap_decret_organisation_date and rap_decret_organisation_date.strip():
            settings_params["decret_organisation_date"] = rap_decret_organisation_date.strip()
        
        # Informations générales
        if rap_section and rap_section.strip():
            settings_params["section"] = rap_section.strip()
        if rap_ministere and rap_ministere.strip():
            # Extraire le nom du ministère pour minister_role ou company_name
            ministere_upper = rap_ministere.strip().upper()
            if "MINISTERE" in ministere_upper:
                settings_params["minister_role"] = ministere_upper.replace("MINISTERE", "MINISTRE")
                settings_params["company_name"] = ministere_upper
        if rap_logo_path and rap_logo_path.strip():
            settings_params["logo_path"] = rap_logo_path.strip()
        
        if settings_params:
            SystemSettingsService.update_settings(db_session=db, user_id=user_id, **settings_params)
            logger.info(f"✅ Données SystemSettings sauvegardées par {current_user.email}")
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=user_id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="rap_data",
            description="Sauvegarde des données du Rapport Annuel de Performance",
            icon="💾",
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Données sauvegardées avec succès. Le rapport sera généré avec ces données."
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde données RAP: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get(
    "/rapport-activite-rprog/pdf",
    response_class=StreamingResponse,
    name="performance_rapport_activite_rprog_pdf",
)
def generate_rapport_activite_rprog_pdf(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Génère le rapport d'activité RPROG en mode paysage.
    Les données sont chargées depuis la base de données."""
    try:
        from app.services.rapport_activite_rprog_generator import (
            RPROGPDFGenerator
        )
        from app.services.system_settings_service import SystemSettingsService
        from datetime import datetime
        
        data: dict[str, Any] = {}
        
        # Récupérer les paramètres généraux du formulaire
        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            final_value = transform(value) if transform else value
            data[target_key] = final_value
        
        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("section", "section")
        optional_param("ministere", "ministere")
        optional_param("programme", "programme")
        optional_param("periode", "periode")
        optional_param("titre_rapport", "titre_rapport")
        optional_param("titre_annee", "titre_annee")
        optional_param("date_publication", "date_publication")
        optional_param("logo_path", "logo_path")
        optional_param("responsable_programme", "responsable_programme")
        
        # Récupérer le mode depuis les paramètres de requête (brouillon ou final)
        mode_param = request.query_params.get("mode", "brouillon")
        data["mode"] = mode_param if mode_param in ["brouillon", "final"] else "brouillon"
        
        # Récupérer les paramètres système pour les valeurs par défaut
        system_settings = SystemSettingsService.get_settings_as_dict(db)
        logo_path_from_settings = system_settings.get("logo_path", "")
        current_year = datetime.now().year
        
        # Appliquer les valeurs par défaut si non fournies
        if "annee" not in data:
            data["annee"] = RPROGPDFGenerator.DEFAULT_DATA.get("annee", current_year - 1)
        if "section" not in data:
            data["section"] = RPROGPDFGenerator.DEFAULT_DATA.get("section", "SECTION 376")
        if "ministere" not in data:
            data["ministere"] = system_settings.get("ministere", RPROGPDFGenerator.DEFAULT_DATA.get("ministere", ""))
        if "programme" not in data:
            data["programme"] = RPROGPDFGenerator.DEFAULT_DATA.get("programme", "PROGRAMME PORTEFEUILLE DE L'ETAT")
        if "periode" not in data:
            data["periode"] = RPROGPDFGenerator.DEFAULT_DATA.get("periode", "PREMIER SEMESTRE")
        if "titre_rapport" not in data:
            data["titre_rapport"] = RPROGPDFGenerator.DEFAULT_DATA.get("titre_rapport", "RAPPORT D'ACTIVITÉ")
        if "titre_annee" not in data:
            data["titre_annee"] = RPROGPDFGenerator.DEFAULT_DATA.get("titre_annee", "AU TITRE DE L'ANNÉE")
        if "date_publication" not in data:
            data["date_publication"] = datetime.now().strftime("%Y-%m")
        if "logo_path" not in data:
            data["logo_path"] = logo_path_from_settings if logo_path_from_settings else RPROGPDFGenerator.DEFAULT_DATA.get("logo_path", "")
        if "responsable_programme" not in data:
            data["responsable_programme"] = RPROGPDFGenerator.DEFAULT_DATA.get("responsable_programme", "")
        
        # Générer le PDF avec les données
        pdf_buffer = RPROGPDFGenerator.generate_pdf(data, session=db)
        
        year = data.get("annee", 2024)
        filename = f"rapport_activite_rprog_{year}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport RPROG: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du rapport: {str(e)}"
        )


@router.get(
    "/rapport-activite-rprog/docx",
    response_class=StreamingResponse,
    name="performance_rapport_activite_rprog_docx",
)
def generate_rapport_activite_rprog_docx(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Génère le rapport d'activité RPROG et le convertit en document Word (.docx).
    
    Cette fonctionnalité permet aux utilisateurs de modifier le rapport dans Word
    au cas où ils souhaiteraient y apporter des modifications.
    
    Le processus :
    1. Génère le PDF du rapport (même processus que /rapport-activite-rprog/pdf)
    2. Convertit le PDF en Word via Adobe PDF Services
    3. Retourne le document Word pour téléchargement
    """
    try:
        from app.services.rapport_activite_rprog_generator import (
            RPROGPDFGenerator
        )
        from app.services.pdf_to_word_service import PDFToWordService
        from app.services.system_settings_service import SystemSettingsService
        from datetime import datetime
        
        # Récupérer les paramètres de conversion
        use_ocr = request.query_params.get("ocr", "false").lower() == "true"
        
        data: dict[str, Any] = {}
        
        # Récupérer les paramètres généraux du formulaire
        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            final_value = transform(value) if transform else value
            data[target_key] = final_value
        
        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("section", "section")
        optional_param("ministere", "ministere")
        optional_param("programme", "programme")
        optional_param("periode", "periode")
        optional_param("titre_rapport", "titre_rapport")
        optional_param("titre_annee", "titre_annee")
        optional_param("date_publication", "date_publication")
        optional_param("logo_path", "logo_path")
        optional_param("responsable_programme", "responsable_programme")
        
        # Récupérer le mode depuis les paramètres de requête (brouillon ou final)
        mode_param = request.query_params.get("mode", "brouillon")
        data["mode"] = mode_param if mode_param in ["brouillon", "final"] else "brouillon"
        
        # Récupérer les paramètres système pour les valeurs par défaut
        system_settings = SystemSettingsService.get_settings_as_dict(db)
        logo_path_from_settings = system_settings.get("logo_path", "")
        current_year = datetime.now().year
        
        # Appliquer les valeurs par défaut si non fournies
        if "annee" not in data:
            data["annee"] = RPROGPDFGenerator.DEFAULT_DATA.get("annee", current_year - 1)
        if "section" not in data:
            data["section"] = RPROGPDFGenerator.DEFAULT_DATA.get("section", "SECTION 376")
        if "ministere" not in data:
            data["ministere"] = system_settings.get("ministere", RPROGPDFGenerator.DEFAULT_DATA.get("ministere", ""))
        if "programme" not in data:
            data["programme"] = RPROGPDFGenerator.DEFAULT_DATA.get("programme", "PROGRAMME PORTEFEUILLE DE L'ETAT")
        if "periode" not in data:
            data["periode"] = RPROGPDFGenerator.DEFAULT_DATA.get("periode", "PREMIER SEMESTRE")
        if "titre_rapport" not in data:
            data["titre_rapport"] = RPROGPDFGenerator.DEFAULT_DATA.get("titre_rapport", "RAPPORT D'ACTIVITÉ")
        if "titre_annee" not in data:
            data["titre_annee"] = RPROGPDFGenerator.DEFAULT_DATA.get("titre_annee", "AU TITRE DE L'ANNÉE")
        if "date_publication" not in data:
            data["date_publication"] = datetime.now().strftime("%Y-%m")
        if "logo_path" not in data:
            data["logo_path"] = logo_path_from_settings if logo_path_from_settings else RPROGPDFGenerator.DEFAULT_DATA.get("logo_path", "")
        if "responsable_programme" not in data:
            data["responsable_programme"] = RPROGPDFGenerator.DEFAULT_DATA.get("responsable_programme", "")
        
        # Étape 1: Générer le PDF
        logger.info("📄 Génération du PDF du rapport RPROG...")
        pdf_buffer = RPROGPDFGenerator.generate_pdf(data, session=db)
        
        # Étape 2: Convertir le PDF en Word
        logger.info("🔄 Conversion PDF → Word en cours...")
        word_buffer = PDFToWordService.convert_pdf_to_word(pdf_buffer, use_ocr=use_ocr)
        
        year = data.get("annee", 2024)
        mode_label = "brouillon" if data.get("mode") == "brouillon" else "final"
        
        headers = {
            "Content-Disposition": f"attachment; filename=rapport_activite_rprog_{year}_{mode_label}.docx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        
        logger.info("✅ Document Word RPROG généré avec succès")
        
        return StreamingResponse(
            iter([word_buffer.getvalue()]),
            headers=headers,
        )
    except Exception as e:
        logger.error(f"❌ Erreur génération Word RPROG: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du document Word: {str(e)}")


@router.get(
    "/rprog-data",
    response_class=JSONResponse,
    name="get_rprog_data_api",
)
def get_rprog_data_api(
    programme_id: int = Query(..., description="ID du programme"),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Récupère les données RPROG pour un programme donné (une seule ligne par programme)"""
    try:
        from app.services.rprog_data_service import RprogDataService
        
        rprog_data = RprogDataService.get_rprog_data(
            db_session=db,
            programme_id=programme_id
        )
        
        if not rprog_data:
            return JSONResponse(
                content={
                    "success": True,
                    "data": None,
                    "message": "Aucune donnée trouvée pour ces paramètres"
                }
            )
        
        # Convertir en dictionnaire
        data_dict = {
            "id": rprog_data.id,
            "programme_id": rprog_data.programme_id,
            "annee": rprog_data.annee,
            "periode": rprog_data.periode,
            "titre_rapport": rprog_data.titre_rapport,
            "section": rprog_data.section,
            "ministere": rprog_data.ministere,
            "date_publication": rprog_data.date_publication,
            "responsable_programme": rprog_data.responsable_programme,
            "logo_path": rprog_data.logo_path,
            "activites_commentaires": rprog_data.activites_commentaires,
            "credits_commentaires": rprog_data.credits_commentaires,
            "investissements_commentaires": rprog_data.investissements_commentaires,
            "effectifs_commentaires": rprog_data.effectifs_commentaires,
            "performance_commentaires": rprog_data.performance_commentaires,
            "difficultes_intro": rprog_data.difficultes_intro,
            "difficultes_rencontrees": rprog_data.difficultes_rencontrees,
            "solutions_intro": rprog_data.solutions_intro,
            "actions_solutions": rprog_data.actions_solutions,
            "conclusion_texte": rprog_data.conclusion_texte,
        }
        
        return JSONResponse(
            content={
                "success": True,
                "data": data_dict
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur récupération données RPROG: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post(
    "/rprog-data",
    response_class=JSONResponse,
    name="save_rprog_data_api",
)
async def save_rprog_data_api(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Sauvegarde les données RPROG dans la base de données"""
    try:
        from app.services.rprog_data_service import RprogDataService
        from app.services.activity_service import ActivityService
        import json
        
        # Récupérer les données depuis le body JSON
        body = await request.json()
        logger.info(f"📥 Données reçues pour sauvegarde RPROG: programme_id={body.get('programme_id')}")
        
        programme_id = body.get("programme_id")
        
        if not programme_id:
            logger.warning(f"⚠️ Données manquantes: programme_id={programme_id}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "programme_id est requis"}
            )
        
        # Récupérer annee et periode si fournis (stockés mais ne font pas partie de la clé unique)
        annee = body.get("annee")
        periode = body.get("periode")
        
        user_id = current_user.id if hasattr(current_user, "id") else 1
        
        # Préparer les paramètres de mise à jour
        # Suivre EXACTEMENT la même logique que RAP
        update_params = {}
        
        # Informations générales (même logique que RAP: vérifier is not None and .strip())
        if "section" in body:
            section_value = body["section"]
            if section_value is not None and section_value.strip():
                update_params["section"] = section_value.strip()
        if "ministere" in body:
            ministere_value = body["ministere"]
            if ministere_value is not None and ministere_value.strip():
                update_params["ministere"] = ministere_value.strip()
        if "date_publication" in body:
            date_value = body["date_publication"]
            if date_value is not None and date_value.strip():
                update_params["date_publication"] = date_value.strip()
        if "titre_rapport" in body:
            titre_value = body["titre_rapport"]
            if titre_value is not None and titre_value.strip():
                update_params["titre_rapport"] = titre_value.strip()
        if "responsable_programme" in body:
            responsable_value = body["responsable_programme"]
            if responsable_value is not None and responsable_value.strip():
                update_params["responsable_programme"] = responsable_value.strip()
        if "logo_path" in body:
            logo_value = body["logo_path"]
            if logo_value is not None and logo_value.strip():
                update_params["logo_path"] = logo_value.strip()
        
        # Commentaires par section (même logique que RAP)
        if "activites_commentaires" in body:
            activites_value = body["activites_commentaires"]
            if activites_value is not None and activites_value.strip():
                update_params["activites_commentaires"] = activites_value.strip()
        if "credits_commentaires" in body:
            credits_value = body["credits_commentaires"]
            if credits_value is not None and credits_value.strip():
                update_params["credits_commentaires"] = credits_value.strip()
        if "investissements_commentaires" in body:
            investissements_value = body["investissements_commentaires"]
            if investissements_value is not None and investissements_value.strip():
                update_params["investissements_commentaires"] = investissements_value.strip()
        if "effectifs_commentaires" in body:
            effectifs_value = body["effectifs_commentaires"]
            if effectifs_value is not None and effectifs_value.strip():
                update_params["effectifs_commentaires"] = effectifs_value.strip()
        if "performance_commentaires" in body:
            performance_value = body["performance_commentaires"]
            if performance_value is not None and performance_value.strip():
                update_params["performance_commentaires"] = performance_value.strip()
        
        # Difficultés et solutions (même logique que RAP)
        if "difficultes_intro" in body:
            difficultes_intro_value = body["difficultes_intro"]
            if difficultes_intro_value is not None and difficultes_intro_value.strip():
                update_params["difficultes_intro"] = difficultes_intro_value.strip()
        if "difficultes_rencontrees" in body:
            difficultes_value = body["difficultes_rencontrees"]
            if difficultes_value is not None and difficultes_value.strip():
                update_params["difficultes_rencontrees"] = difficultes_value.strip()
        if "solutions_intro" in body:
            solutions_intro_value = body["solutions_intro"]
            if solutions_intro_value is not None and solutions_intro_value.strip():
                update_params["solutions_intro"] = solutions_intro_value.strip()
        if "actions_solutions" in body:
            actions_value = body["actions_solutions"]
            if actions_value is not None and actions_value.strip():
                update_params["actions_solutions"] = actions_value.strip()
        
        # Conclusion (même logique que RAP)
        if "conclusion_texte" in body:
            conclusion_value = body["conclusion_texte"]
            if conclusion_value is not None and conclusion_value.strip():
                update_params["conclusion_texte"] = conclusion_value.strip()
        
        # Mettre à jour ou créer les données (même logique que RAP: vérifier si update_params n'est pas vide)
        if update_params:
            RprogDataService.update_rprog_data(
                db_session=db,
                programme_id=programme_id,
                user_id=user_id,
                **update_params
            )
            logger.info(f"✅ Données RPROG sauvegardées par {current_user.email}")
        
        # Logger l'activité (même logique que RAP: toujours logger)
        ActivityService.log_activity(
            db_session=db,
            user_id=user_id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="rprog_data",
            description=f"Sauvegarde des données RPROG pour programme_id={programme_id}",
            icon="💾",
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Données sauvegardées avec succès. Le rapport sera généré avec ces données."
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde données RPROG: {e}", exc_info=True)
        # Vérifier si c'est une erreur de table manquante
        error_message = str(e)
        if "does not exist" in error_message or "no such table" in error_message.lower() or "relation" in error_message.lower():
            error_message = f"La table rprog_data n'existe pas encore. Veuillez exécuter la migration de la base de données. Erreur: {error_message}"
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": error_message}
        )
        
    except ValueError as e:
        # Erreur de configuration (credentials manquants)
        logger.error(f"❌ Erreur de configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration manquante pour la conversion PDF → Word: {e}"
        )
    except ImportError as e:
        # SDK non installé
        logger.error(f"❌ SDK non installé: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"SDK de conversion PDF → Word non installé: {e}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport RPROG en Word: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du rapport Word: {str(e)}"
        )


@router.get(
    "/rapport-annuel-performance/pdf-simpledoc",
    response_class=StreamingResponse,
    name="performance_rapport_annuel_pdf_simpledoc",
)
def generate_rapport_annuel_performance_pdf_simpledoc(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Génère le rapport annuel de performance en mode paysage avec le module modulaire.
    Les données sont chargées depuis la base de données (RapData + SystemSettings)."""
    try:
        from app.services.rapport_annuel_performance_generator_modular import (
            RAPPDFGenerator
        )
        
        data: dict[str, Any] = {}
        
        # Récupérer uniquement les paramètres généraux du formulaire (année, titre, etc.)
        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            final_value = transform(value) if transform else value
            data[target_key] = final_value
        
        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("pays", "pays")
        optional_param("devise", "devise")
        optional_param("section", "section")
        optional_param("ministere", "ministere")
        optional_param("titre_rapport", "titre_rapport")
        optional_param("titre_annee", "titre_annee")
        optional_param("date_publication", "date_publication")
        optional_param("logo_path", "logo_path")
        
        # Récupérer le mode depuis les paramètres de requête (brouillon ou final)
        mode_param = request.query_params.get("mode", "brouillon")
        data["mode"] = mode_param if mode_param in ["brouillon", "final"] else "brouillon"
        
        # Les données d'introduction et RAP sont chargées automatiquement depuis la base
        # via load_system_settings_data() dans generate_pdf()
        
        # Générer le PDF avec les données (chargées depuis la DB)
        pdf_buffer = RAPPDFGenerator.generate_pdf(data, session=db)
        
        year = data.get("annee", 2024)
        mode_label = "brouillon" if data.get("mode") == "brouillon" else "final"
        mode = data.get("mode", "brouillon")
        
        # Enregistrer dans l'historique si mode final
        if mode == "final":
            try:
                from app.services.rapport_annuel_performance_generator_modular import RAPDataLoader
                from datetime import date
                
                # Récupérer les statistiques depuis les données de performance
                budget_data = RAPDataLoader.load_budget_data(db, year)
                performance_data = budget_data.get("performance", {})
                architecture_data = performance_data.get("architecture", {})
                
                # Calculer les dates de période (année complète)
                date_debut = date(year, 1, 1)
                date_fin = date(year, 12, 31)
                
                # Nom du fichier
                filename = f"rapport_annuel_performance_{year}_final.pdf"
                
                # Récupérer le nom de l'utilisateur
                user_name = (
                    current_user.full_name
                    if hasattr(current_user, "full_name") and current_user.full_name
                    else current_user.email
                    if hasattr(current_user, "email")
                    else "Utilisateur"
                )
                
                # Créer un enregistrement dans l'historique
                rapport = RapportPerformance(
                    titre=data.get("titre_rapport", f"Rapport Annuel de Performance {year}"),
                    description=f"Rapport Annuel de Performance pour l'année {year}",
                    type_rapport="RAP",  # Rapport Annuel de Performance
                    format_fichier="PDF",
                    periode=f"ANNEE_{year}",
                    date_debut=date_debut,
                    date_fin=date_fin,
                    fichier_nom=filename,
                    fichier_taille=len(pdf_buffer.getvalue()),
                    nb_objectifs=architecture_data.get("nb_objectifs_globaux", 0) + architecture_data.get("nb_objectifs_specifiques", 0),
                    nb_indicateurs=architecture_data.get("nb_indicateurs", 0),
                    taux_realisation=performance_data.get("taux_realisation", 0),
                    created_by_id=current_user.id if hasattr(current_user, "id") else 1,
                    created_by_nom=user_name,
                )
                db.add(rapport)
                db.commit()
                db.refresh(rapport)
                
                # Logger l'activité
                ActivityService.log_activity(
                    db_session=db,
                    user_id=current_user.id if hasattr(current_user, "id") else 1,
                    user_email=current_user.email if hasattr(current_user, "email") else "user@system",
                    user_full_name=user_name,
                    action_type="generate",
                    target_type="rapport_performance",
                    description=f"Génération du Rapport Annuel de Performance (PDF) pour l'année {year}",
                    icon="📋",
                )
                
                logger.info(f"✅ Rapport Annuel de Performance enregistré dans l'historique (ID: {rapport.id})")
            except Exception as hist_error:
                # Ne pas bloquer la génération si l'enregistrement échoue
                logger.warning(f"⚠️ Erreur lors de l'enregistrement dans l'historique: {hist_error}")
        
        headers = {
            "Content-Disposition": f"inline; filename=rapport_annuel_performance_{year}_{mode_label}.pdf",
        }
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
    except Exception as exc:
        logger.exception("Erreur génération rapport annuel de performance (Module modulaire): %s", exc)
        raise HTTPException(
            status_code=500, 
            detail="Erreur lors de la génération du rapport annuel de performance (Module modulaire)"
        )


@router.get(
    "/rapport-annuel-performance/docx-simpledoc",
    response_class=StreamingResponse,
    name="performance_rapport_annuel_docx_simpledoc",
)
def generate_rapport_annuel_performance_docx_simpledoc(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Génère le rapport annuel de performance et le convertit en document Word (.docx).
    
    Cette fonctionnalité permet aux utilisateurs de modifier le rapport dans Word
    au cas où ils souhaiteraient y apporter des modifications.
    
    Le processus :
    1. Génère le PDF du rapport (même processus que /pdf-simpledoc)
    2. Convertit le PDF en Word via Adobe PDF Services
    3. Retourne le document Word pour téléchargement
    """
    try:
        from app.services.rapport_annuel_performance_generator_modular import (
            RAPPDFGenerator
        )
        from app.services.pdf_to_word_service import PDFToWordService
        
        # Récupérer les paramètres de conversion
        use_ocr = request.query_params.get("ocr", "false").lower() == "true"
        
        data: dict[str, Any] = {}
        
        # Récupérer uniquement les paramètres généraux du formulaire (année, titre, etc.)
        def optional_param(param: str, target_key: str, transform=None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            final_value = transform(value) if transform else value
            data[target_key] = final_value
        
        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("pays", "pays")
        optional_param("devise", "devise")
        optional_param("section", "section")
        optional_param("ministere", "ministere")
        optional_param("titre_rapport", "titre_rapport")
        optional_param("titre_annee", "titre_annee")
        optional_param("date_publication", "date_publication")
        optional_param("logo_path", "logo_path")
        
        # Récupérer le mode depuis les paramètres de requête (brouillon ou final)
        mode_param = request.query_params.get("mode", "brouillon")
        data["mode"] = mode_param if mode_param in ["brouillon", "final"] else "brouillon"
        
        # Étape 1: Générer le PDF
        logger.info("📄 Génération du PDF du rapport...")
        pdf_buffer = RAPPDFGenerator.generate_pdf(data, session=db)
        
        # Étape 2: Convertir le PDF en Word
        logger.info("🔄 Conversion PDF → Word en cours...")
        word_buffer = PDFToWordService.convert_pdf_to_word(pdf_buffer, use_ocr=use_ocr)
        
        year = data.get("annee", 2024)
        mode_label = "brouillon" if data.get("mode") == "brouillon" else "final"
        mode = data.get("mode", "brouillon")
        
        # Enregistrer dans l'historique si mode final
        if mode == "final":
            try:
                from app.services.rapport_annuel_performance_generator_modular import RAPDataLoader
                from datetime import date
                
                # Récupérer les statistiques depuis les données de performance
                budget_data = RAPDataLoader.load_budget_data(db, year)
                performance_data = budget_data.get("performance", {})
                architecture_data = performance_data.get("architecture", {})
                
                # Calculer les dates de période (année complète)
                date_debut = date(year, 1, 1)
                date_fin = date(year, 12, 31)
                
                # Nom du fichier
                filename = f"rapport_annuel_performance_{year}_final.docx"
                
                # Récupérer le nom de l'utilisateur
                user_name = (
                    current_user.full_name
                    if hasattr(current_user, "full_name") and current_user.full_name
                    else current_user.email
                    if hasattr(current_user, "email")
                    else "Utilisateur"
                )
                
                # Créer un enregistrement dans l'historique
                rapport = RapportPerformance(
                    titre=data.get("titre_rapport", f"Rapport Annuel de Performance {year}"),
                    description=f"Rapport Annuel de Performance pour l'année {year} (format Word)",
                    type_rapport="RAP",  # Rapport Annuel de Performance
                    format_fichier="DOCX",
                    periode=f"ANNEE_{year}",
                    date_debut=date_debut,
                    date_fin=date_fin,
                    fichier_nom=filename,
                    fichier_taille=len(word_buffer.getvalue()),
                    nb_objectifs=architecture_data.get("nb_objectifs_globaux", 0) + architecture_data.get("nb_objectifs_specifiques", 0),
                    nb_indicateurs=architecture_data.get("nb_indicateurs", 0),
                    taux_realisation=performance_data.get("taux_realisation", 0),
                    created_by_id=current_user.id if hasattr(current_user, "id") else 1,
                    created_by_nom=user_name,
                )
                db.add(rapport)
                db.commit()
                db.refresh(rapport)
                
                # Logger l'activité
                ActivityService.log_activity(
                    db_session=db,
                    user_id=current_user.id if hasattr(current_user, "id") else 1,
                    user_email=current_user.email if hasattr(current_user, "email") else "user@system",
                    user_full_name=user_name,
                    action_type="generate",
                    target_type="rapport_performance",
                    description=f"Génération du Rapport Annuel de Performance (Word) pour l'année {year}",
                    icon="📋",
                )
                
                logger.info(f"✅ Rapport Annuel de Performance (Word) enregistré dans l'historique (ID: {rapport.id})")
            except Exception as hist_error:
                # Ne pas bloquer la génération si l'enregistrement échoue
                logger.warning(f"⚠️ Erreur lors de l'enregistrement dans l'historique: {hist_error}")
        
        headers = {
            "Content-Disposition": f"attachment; filename=rapport_annuel_performance_{year}_{mode_label}.docx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        
        logger.info("✅ Document Word généré avec succès")
        return StreamingResponse(word_buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)
        
    except ValueError as e:
        # Erreur de configuration (credentials manquants)
        logger.error(f"❌ Erreur de configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration manquante pour la conversion PDF → Word: {e}"
        )
    except ImportError as e:
        # SDK non installé
        logger.error(f"❌ SDK non installé: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Le SDK Adobe PDF Services n'est pas installé. Installez-le avec: pip install pdfservices-sdk"
        )
    except Exception as exc:
        logger.exception("Erreur conversion rapport annuel de performance en Word: %s", exc)
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la conversion du rapport en Word: {str(exc)}"
        )


@router.get(
    "/rapport-annuel-performance/pdf",
    response_class=StreamingResponse,
    name="performance_rapport_annuel_pdf",
)
def generate_rapport_annuel_performance_pdf(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Génère le rapport annuel de performance en mode paysage."""
    try:
        data: dict[str, Any] = {}

        def optional_param(param: str, target_key: str, transform=None, target_dict: dict[str, Any] | None = None) -> None:
            value = request.query_params.get(param)
            if value is None or value == "":
                return
            final_value = transform(value) if transform else value
            if target_dict is not None:
                target_dict[target_key] = final_value
            else:
                data[target_key] = final_value

        optional_param("annee", "annee", lambda v: int(v) if v.isdigit() else v)
        optional_param("pays", "pays")
        optional_param("devise", "devise")
        optional_param("section", "section")
        optional_param("ministere", "ministere")
        optional_param("titre_rapport", "titre_rapport")
        optional_param("titre_annee", "titre_annee")
        optional_param("date_publication", "date_publication")
        optional_param("logo_path", "logo_path")
        
        # Paramètres d'introduction générale
        intro_data: dict[str, Any] = {}
        optional_param("intro_ministre_nom", "ministre_nom", target_dict=intro_data)
        optional_param("intro_ministre_date_nomination", "ministre_date_nomination", target_dict=intro_data)
        optional_param("intro_decret_attribution_numero", "decret_attribution_numero", target_dict=intro_data)
        optional_param("intro_decret_attribution_date", "decret_attribution_date", target_dict=intro_data)
        optional_param("intro_structure_cabinet", "structure_cabinet", target_dict=intro_data)
        optional_param("intro_structure_directions_centrales", "structure_directions_centrales", lambda v: int(v) if v.isdigit() else None, target_dict=intro_data)
        optional_param("intro_structure_services", "structure_services", lambda v: int(v) if v.isdigit() else None, target_dict=intro_data)
        optional_param("intro_structure_directions_generales", "structure_directions_generales", lambda v: int(v) if v.isdigit() else None, target_dict=intro_data)
        optional_param("intro_decret_organisation_numero", "decret_organisation_numero", target_dict=intro_data)
        optional_param("intro_decret_organisation_date", "decret_organisation_date", target_dict=intro_data)
        optional_param("intro_contexte_texte", "contexte_texte", target_dict=intro_data)
        
        if intro_data:
            data["introduction"] = intro_data
        
        # Paramètres pour le financement global (interprétations personnalisées)
        financement_interpretations: dict[str, Any] = {}
        optional_param("financement_intro", "intro", target_dict=financement_interpretations)
        optional_param("financement_raison_1", "raison_1", target_dict=financement_interpretations)
        optional_param("financement_raison_2", "raison_2", target_dict=financement_interpretations)
        optional_param("financement_evolution_intro", "evolution_intro", target_dict=financement_interpretations)
        optional_param("financement_evolution_personnel", "evolution_personnel", target_dict=financement_interpretations)
        optional_param("financement_evolution_biens", "evolution_biens", target_dict=financement_interpretations)
        optional_param("financement_evolution_transferts", "evolution_transferts", target_dict=financement_interpretations)
        optional_param("financement_evolution_investissements", "evolution_investissements", target_dict=financement_interpretations)
        optional_param("financement_note_comparaison", "note_comparaison", target_dict=financement_interpretations)
        
        # Construire la liste des raisons si fournies
        if financement_interpretations:
            raisons = []
            if "raison_1" in financement_interpretations:
                raisons.append(financement_interpretations["raison_1"])
            if "raison_2" in financement_interpretations:
                raisons.append(financement_interpretations["raison_2"])
            if raisons:
                financement_interpretations["raisons_augmentation"] = raisons
            data["financement_interpretations"] = financement_interpretations

        # Passer la session de base de données pour charger les données budgétaires
        pdf_buffer = RAPPDFGenerator.generate_pdf(data, session=db)

        year = data.get("annee", RAPPDFGenerator.DEFAULT_DATA.get("annee", "2024"))

        headers = {
            "Content-Disposition": f"inline; filename=rapport_annuel_performance_{year}.pdf",
        }
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
    except Exception as exc:
        logger.exception("Erreur génération rapport annuel de performance: %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du rapport annuel de performance")


@router.post("/api/lettres-engagement/upload-photo", name="upload_engagement_photo")
async def upload_engagement_photo(
    photo: UploadFile = FastAPIFile(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Upload d'une photo (responsable programme, responsable BOP ou logo) pour la lettre d'engagement."""

    allowed_content_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
    max_size_bytes = 5 * 1024 * 1024  # 5 MB

    if photo.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="Formats acceptés : JPG, PNG ou WEBP")

    content = await photo.read()
    if not content:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")

    if len(content) > max_size_bytes:
        raise HTTPException(status_code=400, detail="La photo dépasse la taille maximale de 5 MB.")

    extension = Path(photo.filename or "").suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        extension = ".jpg" if photo.content_type in {"image/jpeg", "image/jpg"} else ".png"

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{extension}"
    photos_dir = path_config.UPLOADS_DIR / "performance" / "engagement"
    path_config.ensure_directory_exists(photos_dir)

    destination = photos_dir / filename
    destination.write_bytes(content)

    relative_path = f"uploads/performance/engagement/{filename}"
    file_url = path_config.get_file_url("uploads", f"performance/engagement/{filename}")

    ActivityService.log_activity(
        db_session=session,
        user_id=current_user.id,
        user_email=current_user.email,
        user_full_name=current_user.full_name,
        action_type="upload",
        target_type="lettre_engagement_photo",
        description=f"Upload d'une photo pour la lettre d'engagement ({photo.filename})",
        icon="🖼️",
    )

    return JSONResponse(
        {
            "success": True,
            "message": "Photo importée avec succès",
            "path": relative_path,
            "relative_path": relative_path,  # Alias pour compatibilité
            "url": file_url,
        }
    )


@router.get("/objectifs", response_class=HTMLResponse, name="performance_objectifs")
def performance_objectifs(request: Request, db: Session = Depends(get_session)):
    """Gestion des objectifs de performance"""
    try:
        from app.templates import get_template_context, templates

        context = get_template_context(request)
        context.update(
            {
                "page_title": "Objectifs de Performance",
                "module_name": "Performance",
                "module_description": "Définition et suivi des objectifs",
            }
        )

        return templates.TemplateResponse("pages/performance_objectifs.html", context)

    except Exception as e:
        logger.error(f"Erreur lors du chargement des objectifs Performance: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/indicateurs", response_class=HTMLResponse, name="performance_indicateurs")
def performance_indicateurs(request: Request, db: Session = Depends(get_session)):
    """Gestion des indicateurs de performance"""
    try:
        from app.templates import get_template_context, templates

        context = get_template_context(request)
        context.update(
            {
                "page_title": "Indicateurs de Performance",
                "module_name": "Performance",
                "module_description": "Configuration et suivi des KPIs",
            }
        )

        return templates.TemplateResponse("pages/performance_indicateurs.html", context)

    except Exception as e:
        logger.error(f"Erreur lors du chargement des indicateurs Performance: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/rapports", response_class=HTMLResponse, name="performance_rapports")
def performance_rapports(request: Request, db: Session = Depends(get_session)):
    """Rapports de performance"""
    try:
        from app.templates import get_template_context, templates
        from app.services.system_settings_service import SystemSettingsService
        from datetime import datetime

        context = get_template_context(request)
        
        # Récupérer les paramètres système
        system_settings = SystemSettingsService.get_settings_as_dict(db)
        logo_path_from_settings = system_settings.get("logo_path", "")
        current_year = datetime.now().year
        
        # Valeurs par défaut pour le rapport annuel de performance
        rapport_annuel_defaults = {
            "annee": RAPPDFGenerator.DEFAULT_DATA.get("annee", current_year - 1),
            "section": RAPPDFGenerator.DEFAULT_DATA.get("section", "SECTION 376"),
            "ministere": RAPPDFGenerator.DEFAULT_DATA.get("ministere", ""),
            "titre_rapport": RAPPDFGenerator.DEFAULT_DATA.get("titre_rapport", ""),
            "titre_annee": RAPPDFGenerator.DEFAULT_DATA.get("titre_annee", "AU TITRE DE L'ANNÉE"),
            "date_publication": RAPPDFGenerator.DEFAULT_DATA.get("date_publication", ""),
            "logo_path": logo_path_from_settings if logo_path_from_settings else RAPPDFGenerator.DEFAULT_DATA.get("logo_path", ""),
        }
        # Générer la date de publication si non définie
        if not rapport_annuel_defaults.get("date_publication"):
            rapport_annuel_defaults["date_publication"] = datetime.now().strftime("%Y-%m")
        
        # Récupérer la liste des programmes pour le cadre de performance
        programmes = db.exec(
            select(Programme).where(Programme.actif == True).order_by(Programme.code)
        ).all()
        programmes_list = [
            {"id": prog.id, "code": prog.code, "libelle": prog.libelle or prog.code}
            for prog in programmes
        ]
        
        context.update(
            {
                "page_title": "Rapports de Performance",
                "module_name": "Performance",
                "module_description": "Analyse et reporting des performances",
                "rapport_annuel_defaults": rapport_annuel_defaults,
                "programmes": programmes_list,
            }
        )

        return templates.TemplateResponse("pages/performance_rapports.html", context)

    except Exception as e:
        logger.error(f"Erreur lors du chargement des rapports Performance: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ============================================
# ROUTES CRUD OBJECTIFS
# ============================================


@router.get("/api/objectifs", response_class=JSONResponse)
def get_objectifs_api(
    db: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    statut: str | None = Query(None),
    responsable_id: int | None = Query(None),
    type_objectif: str | None = Query(None),
):
    """API: Récupère la liste des objectifs"""
    try:
        objectifs = PerformanceService.get_objectifs(
            session=db,
            skip=skip,
            limit=limit,
            statut=statut,
            responsable_id=responsable_id,
            type_objectif=type_objectif,
        )

        return {
            "success": True,
            "data": [
                {
                    "id": obj.id,
                    "code": obj.code,
                    "titre": obj.titre,
                    "description": obj.description,
                    "type_objectif": obj.type_objectif,
                    "priorite": obj.priorite,
                    "date_debut": obj.date_debut.isoformat(),
                    "date_fin": obj.date_fin.isoformat(),
                    "periode": obj.periode,
                    "valeur_cible": float(obj.valeur_cible),
                    "valeur_actuelle": float(obj.valeur_actuelle),
                    "unite": obj.unite,
                    "responsable_id": obj.responsable_id,
                    "service_responsable": obj.service_responsable,
                    "resultat_strategique_id": obj.resultat_strategique_id,
                    "programme_id": obj.programme_id,
                    "objectif_global_id": obj.objectif_global_id,
                    "statut": obj.statut,
                    "progression_pourcentage": float(obj.progression_pourcentage) if obj.progression_pourcentage else 0,
                    "commentaires": obj.commentaires,
                    "created_at": obj.created_at.isoformat(),
                    "updated_at": obj.updated_at.isoformat(),
                }
                for obj in objectifs
            ],
        }

    except Exception as e:
        logger.error(f"Erreur API get_objectifs: {e}")
        return {"success": False, "error": "Erreur lors de la récupération des objectifs"}


@router.get("/api/objectifs/{objectif_id}", response_class=JSONResponse)
def get_objectif_api(objectif_id: int, db: Session = Depends(get_session)):
    """API: Récupère un objectif par ID"""
    try:
        objectif = PerformanceService.get_objectif(db, objectif_id)
        if not objectif:
            return {"success": False, "error": "Objectif non trouvé"}

        return {
            "success": True,
            "data": {
                "id": objectif.id,
                "code": objectif.code,
                "titre": objectif.titre,
                "description": objectif.description,
                "type_objectif": objectif.type_objectif,
                "priorite": objectif.priorite,
                "date_debut": objectif.date_debut.isoformat(),
                "date_fin": objectif.date_fin.isoformat(),
                "periode": objectif.periode,
                "valeur_cible": float(objectif.valeur_cible),
                "valeur_actuelle": float(objectif.valeur_actuelle),
                "unite": objectif.unite,
                "responsable_id": objectif.responsable_id,
                "service_responsable": objectif.service_responsable,
                "resultat_strategique_id": objectif.resultat_strategique_id,
                "programme_id": objectif.programme_id,
                "objectif_global_id": objectif.objectif_global_id,
                "statut": objectif.statut,
                "progression_pourcentage": float(objectif.progression_pourcentage)
                if objectif.progression_pourcentage
                else 0,
                "indicateurs_associes": objectif.indicateurs_associes,
                "commentaires": objectif.commentaires,
                "notes_internes": objectif.notes_internes,
                "created_at": objectif.created_at.isoformat(),
                "updated_at": objectif.updated_at.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Erreur API get_objectif: {e}")
        return {"success": False, "error": "Erreur lors de la récupération de l'objectif"}


@router.post("/api/objectifs", response_class=JSONResponse)
def create_objectif_api(
    code: str | None = Form(None),
    titre: str = Form(...),
    description: str | None = Form(None),
    type_objectif: str = Form("specifique"),
    priorite: str = Form("NORMALE"),
    date_debut: str = Form(...),
    date_fin: str = Form(...),
    periode: str = Form(...),
    valeur_cible: str = Form(...),
    valeur_actuelle: str = Form("0"),
    unite: str = Form(...),
    responsable_id: int | None = Form(None),
    service_responsable: str | None = Form(None),
    resultat_strategique_id: int | None = Form(None),
    programme_id: int | None = Form(None),
    objectif_global_id: int | None = Form(None),
    indicateurs_associes: str | None = Form(None),
    commentaires: str | None = Form(None),
    notes_internes: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user=Depends(require_roles("admin", "user")),
):
    """API: Crée un nouvel objectif"""
    try:
        logger.info(f"📥 Création d'objectif - Données reçues:")
        logger.info(f"  - code: {code} (type: {type(code)})")
        logger.info(f"  - titre: {titre}")
        logger.info(f"  - type_objectif: {type_objectif}")
        logger.info(f"  - resultat_strategique_id: {resultat_strategique_id}")
        logger.info(f"  - objectif_global_id: {objectif_global_id}")
        logger.info(f"  - responsable_id: {responsable_id}")
        
        # Traiter le code : si fourni et non vide, le nettoyer, sinon None
        code_value = None
        if code and isinstance(code, str) and code.strip():
            code_value = code.strip()
        logger.info(f"  - code_value traité: {code_value}")
        
        objectif_data = {
            "code": code_value,
            "titre": titre,
            "description": description,
            "type_objectif": type_objectif,
            "priorite": priorite,
            "date_debut": datetime.fromisoformat(date_debut).date(),
            "date_fin": datetime.fromisoformat(date_fin).date(),
            "periode": periode,
            "valeur_cible": valeur_cible,
            "valeur_actuelle": valeur_actuelle,
            "unite": unite,
            "responsable_id": responsable_id if responsable_id else None,
            "service_responsable": service_responsable,
            "resultat_strategique_id": int(resultat_strategique_id) if resultat_strategique_id and str(resultat_strategique_id).strip() else None,
            "programme_id": int(programme_id) if programme_id and str(programme_id).strip() else None,
            "objectif_global_id": int(objectif_global_id) if objectif_global_id and str(objectif_global_id).strip() else None,
            "indicateurs_associes": indicateurs_associes,
            "commentaires": commentaires,
            "notes_internes": notes_internes,
        }
        
        logger.info(f"📦 Données préparées pour creer_objectif: {objectif_data}")

        objectif = PerformanceService.creer_objectif(db, objectif_data, current_user.id)
        logger.info(f"✅ Objectif créé avec succès: ID={objectif.id}, titre={objectif.titre}")

        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="objectif_performance",
            target_id=objectif.id,
            description=f"Création de l'objectif '{titre}'",
            icon="🎯",
        )

        return {
            "success": True,
            "message": "Objectif créé avec succès",
            "data": {"id": objectif.id, "titre": objectif.titre},
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Erreur API create_objectif: {e}")
        logger.error(f"Détails de l'erreur:\n{error_details}")
        return {"success": False, "error": f"Erreur lors de la création de l'objectif: {str(e)}"}


@router.put("/api/objectifs/{objectif_id}", response_class=JSONResponse)
def update_objectif_api(
    objectif_id: int,
    code: str | None = Form(None),
    titre: str | None = Form(None),
    description: str | None = Form(None),
    type_objectif: str | None = Form(None),
    priorite: str | None = Form(None),
    date_debut: str | None = Form(None),
    date_fin: str | None = Form(None),
    periode: str | None = Form(None),
    valeur_cible: str | None = Form(None),
    valeur_actuelle: str | None = Form(None),
    unite: str | None = Form(None),
    responsable_id: int | None = Form(None),
    service_responsable: str | None = Form(None),
    resultat_strategique_id: int | None = Form(None),
    programme_id: int | None = Form(None),
    objectif_global_id: int | None = Form(None),
    statut: str | None = Form(None),
    indicateurs_associes: str | None = Form(None),
    commentaires: str | None = Form(None),
    notes_internes: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user=Depends(require_roles("admin", "user")),
):
    """API: Modifie un objectif existant"""
    try:
        # Récupérer l'objectif existant pour connaître son type
        existing_objectif = db.exec(select(ObjectifPerformance).where(ObjectifPerformance.id == objectif_id)).first()
        if not existing_objectif:
            return {"success": False, "error": "Objectif non trouvé"}
        
        objectif_data = {}

        # Construire le dictionnaire avec seulement les champs fournis
        # Pour le code : toujours traiter s'il est fourni (même vide, pour permettre de le supprimer)
        # Si code est None, c'est que le champ n'a pas été envoyé, on ne le modifie pas
        # Si code est une chaîne vide "", on le convertit en None pour le supprimer
        # IMPORTANT: Avec optionalFieldsToKeep, le code est toujours envoyé (même vide), donc code ne sera jamais None
        # mais pourra être une chaîne vide ""
        if code is not None:
            # Si c'est une chaîne vide ou ne contient que des espaces, mettre à None
            if isinstance(code, str):
                code_cleaned = code.strip()
                objectif_data["code"] = code_cleaned if code_cleaned else None
            else:
                objectif_data["code"] = code
        # Si code n'est pas dans objectif_data, on ne le modifie pas (garde la valeur existante)
        if titre is not None:
            objectif_data["titre"] = titre
        if description is not None:
            objectif_data["description"] = description
        if type_objectif is not None:
            objectif_data["type_objectif"] = type_objectif
        if priorite is not None:
            objectif_data["priorite"] = priorite
        if date_debut is not None:
            objectif_data["date_debut"] = datetime.fromisoformat(date_debut).date()
        if date_fin is not None:
            objectif_data["date_fin"] = datetime.fromisoformat(date_fin).date()
        if periode is not None:
            objectif_data["periode"] = periode
        if valeur_cible is not None:
            objectif_data["valeur_cible"] = valeur_cible
        if valeur_actuelle is not None:
            objectif_data["valeur_actuelle"] = valeur_actuelle
        if unite is not None:
            objectif_data["unite"] = unite
        if responsable_id is not None:
            objectif_data["responsable_id"] = responsable_id
        if service_responsable is not None:
            objectif_data["service_responsable"] = service_responsable
        
        # Déterminer le type d'objectif (utiliser celui fourni ou celui existant)
        current_type = type_objectif or existing_objectif.type_objectif
        
        # Gérer resultat_strategique_id : toujours traiter si c'est un objectif global
        # (pour permettre de le mettre à None si nécessaire)
        if current_type and (current_type.lower() == 'global' or current_type == 'GLOBAL'):
            # Convertir en int si c'est une chaîne non vide, sinon None
            if isinstance(resultat_strategique_id, str):
                if resultat_strategique_id.strip() == '' or resultat_strategique_id.strip() == 'null':
                    objectif_data["resultat_strategique_id"] = None
                else:
                    try:
                        objectif_data["resultat_strategique_id"] = int(resultat_strategique_id) if resultat_strategique_id else None
                    except (ValueError, TypeError):
                        objectif_data["resultat_strategique_id"] = None
            elif resultat_strategique_id is not None:
                objectif_data["resultat_strategique_id"] = int(resultat_strategique_id)
            else:
                objectif_data["resultat_strategique_id"] = None
            # Gérer programme_id pour les objectifs globaux
            # Toujours traiter programme_id s'il est fourni (même vide, pour permettre de le mettre à None)
            if programme_id is not None:
                if isinstance(programme_id, str):
                    if programme_id.strip() == '' or programme_id.strip() == 'null':
                        objectif_data["programme_id"] = None
                    else:
                        try:
                            objectif_data["programme_id"] = int(programme_id) if programme_id else None
                        except (ValueError, TypeError):
                            objectif_data["programme_id"] = None
                else:
                    # programme_id est un int ou None
                    objectif_data["programme_id"] = int(programme_id) if programme_id else None
        else:
            # Pour les autres types, mettre à None si fourni explicitement
            if programme_id is not None:
                objectif_data["programme_id"] = None
        
        # Gérer objectif_global_id : toujours traiter si c'est un objectif spécifique
        # (pour permettre de le mettre à None si nécessaire)
        if current_type and (current_type.lower() == 'specifique' or current_type == 'SPECIFIQUE'):
            # Convertir en int si c'est une chaîne non vide, sinon None
            if isinstance(objectif_global_id, str):
                if objectif_global_id.strip() == '' or objectif_global_id.strip() == 'null':
                    objectif_data["objectif_global_id"] = None
                else:
                    try:
                        objectif_data["objectif_global_id"] = int(objectif_global_id) if objectif_global_id else None
                    except (ValueError, TypeError):
                        objectif_data["objectif_global_id"] = None
            elif objectif_global_id is not None:
                objectif_data["objectif_global_id"] = int(objectif_global_id)
            else:
                # Si le champ n'a pas été envoyé mais que c'est une modification d'un OS,
                # on ne le modifie pas (on garde la valeur existante)
                pass
        
        if statut is not None:
            objectif_data["statut"] = statut
        if indicateurs_associes is not None:
            objectif_data["indicateurs_associes"] = indicateurs_associes
        if commentaires is not None:
            objectif_data["commentaires"] = commentaires
        if notes_internes is not None:
            objectif_data["notes_internes"] = notes_internes

        logger.info(f"📥 Modification d'objectif - Données préparées: {objectif_data}")
        logger.info(f"  - type_objectif: {current_type}")
        logger.info(f"  - code reçu: {code}, traité: {objectif_data.get('code')}")
        logger.info(f"  - objectif_global_id reçu: {objectif_global_id}, traité: {objectif_data.get('objectif_global_id')}")
        logger.info(f"  - resultat_strategique_id reçu: {resultat_strategique_id}, traité: {objectif_data.get('resultat_strategique_id')}")

        objectif = PerformanceService.modifier_objectif(db, objectif_id, objectif_data)

        if not objectif:
            return {"success": False, "error": "Objectif non trouvé"}

        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="objectif_performance",
            target_id=objectif.id,
            description=f"Modification de l'objectif '{objectif.titre}'",
            icon="✏️",
        )

        return {
            "success": True,
            "message": "Objectif modifié avec succès",
            "data": {"id": objectif.id, "titre": objectif.titre},
        }

    except Exception as e:
        logger.error(f"Erreur API update_objectif: {e}")
        return {"success": False, "error": "Erreur lors de la modification de l'objectif"}


@router.delete("/api/objectifs/{objectif_id}", response_class=JSONResponse)
def delete_objectif_api(
    objectif_id: int, db: Session = Depends(get_session), current_user=Depends(require_roles("admin", "user"))
):
    """API: Supprime un objectif"""
    try:
        # Récupérer l'objectif avant de le supprimer pour logger
        objectif = PerformanceService.get_objectif(db, objectif_id)
        if not objectif:
            return {"success": False, "error": "Objectif non trouvé"}

        objectif_titre = objectif.titre

        success = PerformanceService.supprimer_objectif(db, objectif_id)

        if not success:
            return {"success": False, "error": "Erreur lors de la suppression"}

        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="delete",
            target_type="objectif_performance",
            target_id=objectif_id,
            description=f"Suppression de l'objectif '{objectif_titre}'",
            icon="🗑️",
        )

        return {"success": True, "message": "Objectif supprimé avec succès"}

    except Exception as e:
        logger.error(f"Erreur API delete_objectif: {e}")
        return {"success": False, "error": "Erreur lors de la suppression de l'objectif"}


@router.get("/api/objectifs/kpis", response_class=JSONResponse)
def get_objectifs_kpis_api(db: Session = Depends(get_session)):
    """API: Récupère les KPIs des objectifs"""
    try:
        kpis = PerformanceService.get_kpis_objectifs(db)
        return {"success": True, "data": kpis}

    except Exception as e:
        logger.error(f"Erreur API get_objectifs_kpis: {e}")
        return {"success": False, "error": "Erreur lors du calcul des KPIs"}


# ============================================
# ROUTES CRUD INDICATEURS
# ============================================


@router.get("/api/indicateurs", response_class=JSONResponse, name="get_indicateurs_api")
def get_indicateurs_api(
    db: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    categorie: str | None = Query(None),
    responsable_id: int | None = Query(None),
    frequence_mesure: str | None = Query(None),
):
    """API: Récupère la liste des indicateurs"""
    try:
        indicateurs = PerformanceService.get_indicateurs(
            session=db,
            skip=skip,
            limit=limit,
            categorie=categorie,
            responsable_id=responsable_id,
            frequence_mesure=frequence_mesure,
        )

        # Convertir les objets SQLModel en dictionnaires
        indicateurs_dict = [
            {
                "id": ind.id,
                "objectif_id": ind.objectif_id,
                "nom": ind.nom,
                "description": ind.description,
                "categorie": ind.categorie,
                "frequence_mesure": ind.frequence_maj,
                "annee": ind.annee,
                "valeur_cible": float(ind.valeur_cible) if ind.valeur_cible else 0,
                "valeur_actuelle": float(ind.valeur_actuelle) if ind.valeur_actuelle else 0,
                "unite_mesure": ind.unite,
                "seuil_alerte_min": float(ind.seuil_alerte_bas) if ind.seuil_alerte_bas else None,
                "seuil_alerte_max": float(ind.seuil_alerte_haut) if ind.seuil_alerte_haut else None,
                "responsable_id": ind.responsable_id,
                "service_responsable": getattr(ind, "service_responsable", None),
                "source_donnees": ind.source_donnees,
                "methode": getattr(ind, "methode", None),
                "mode_collecte_donnees": getattr(ind, "mode_collecte_donnees", None),
                "derniere_valeur_connue": float(ind.derniere_valeur_connue) if getattr(ind, "derniere_valeur_connue", None) else None,
                "sens_appreciation": getattr(ind, "sens_appreciation", "haut"),
                "doc_justif": getattr(ind, "doc_justif", None),
                "cible_N_plus_1": float(ind.cible_N_plus_1) if getattr(ind, "cible_N_plus_1", None) else None,
                "cible_N_plus_2": float(ind.cible_N_plus_2) if getattr(ind, "cible_N_plus_2", None) else None,
                "commentaires": getattr(ind, "commentaires", None),
                "created_at": ind.created_at.isoformat() if ind.created_at else None,
                "updated_at": ind.updated_at.isoformat() if ind.updated_at else None,
            }
            for ind in indicateurs
        ]

        return {"success": True, "data": indicateurs_dict, "count": len(indicateurs_dict)}

    except Exception as e:
        logger.error(f"Erreur API get_indicateurs: {e}")
        return {"success": False, "error": "Erreur lors de la récupération des indicateurs"}


@router.get("/api/indicateurs/{indicateur_id}", response_class=JSONResponse)
def get_indicateur_api(indicateur_id: int, db: Session = Depends(get_session)):
    """API: Récupère un indicateur par ID"""
    try:
        indicateur = PerformanceService.get_indicateur(db, indicateur_id)
        if not indicateur:
            return {"success": False, "error": "Indicateur non trouvé"}

        indicateur_dict = {
            "id": indicateur.id,
            "objectif_id": indicateur.objectif_id,
            "nom": indicateur.nom,
            "description": indicateur.description,
            "categorie": indicateur.categorie,
            "frequence_mesure": indicateur.frequence_maj,
            "annee": indicateur.annee,
            "valeur_cible": float(indicateur.valeur_cible) if indicateur.valeur_cible else 0,
            "valeur_actuelle": float(indicateur.valeur_actuelle) if indicateur.valeur_actuelle else 0,
            "unite_mesure": indicateur.unite,
            "seuil_alerte_min": float(indicateur.seuil_alerte_bas) if indicateur.seuil_alerte_bas else None,
            "seuil_alerte_max": float(indicateur.seuil_alerte_haut) if indicateur.seuil_alerte_haut else None,
            "responsable_id": indicateur.responsable_id,
            "service_responsable": getattr(indicateur, "service_responsable", None),
            "source_donnees": indicateur.source_donnees,
            "methode": getattr(indicateur, "methode", None),
            "mode_collecte_donnees": getattr(indicateur, "mode_collecte_donnees", None),
            "derniere_valeur_connue": float(indicateur.derniere_valeur_connue) if getattr(indicateur, "derniere_valeur_connue", None) else None,
            "sens_appreciation": getattr(indicateur, "sens_appreciation", "haut"),
            "doc_justif": getattr(indicateur, "doc_justif", None),
            "cible_N_plus_1": float(indicateur.cible_N_plus_1) if getattr(indicateur, "cible_N_plus_1", None) else None,
            "cible_N_plus_2": float(indicateur.cible_N_plus_2) if getattr(indicateur, "cible_N_plus_2", None) else None,
            "commentaires": getattr(indicateur, "commentaires", None),
        }

        return {"success": True, "data": indicateur_dict}

    except Exception as e:
        logger.error(f"Erreur API get_indicateur: {e}")
        return {"success": False, "error": "Erreur lors de la récupération de l'indicateur"}


@router.post("/api/indicateurs", response_class=JSONResponse, name="create_indicateur_api")
async def create_indicateur_api(
    objectif_id: int = Form(...),
    nom: str = Form(...),
    description: str | None = Form(None),
    categorie: str = Form("OPERATIONNEL"),
    frequence_mesure: str = Form("MENSUEL"),
    annee: int = Form(...),
    valeur_cible: str = Form(...),
    valeur_actuelle: str = Form("0"),
    unite_mesure: str = Form(...),
    seuil_alerte_min: str | None = Form(None),
    seuil_alerte_max: str | None = Form(None),
    responsable_id: int | None = Form(None),
    service_responsable: str | None = Form(None),
    source_donnees: str | None = Form(None),
    methode: str | None = Form(None),
    mode_collecte_donnees: str | None = Form(None),
    derniere_valeur_connue: str | None = Form(None),
    sens_appreciation: str | None = Form(None),
    cible_N_plus_1: str | None = Form(None),
    cible_N_plus_2: str | None = Form(None),
    doc_justif_file: UploadFile | None = FastAPIFile(None),
    commentaires: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user: dict = Depends(require_roles("admin", "user")),
):
    """API: Crée un nouvel indicateur"""
    try:
        logger.info(f"🔍 [create_indicateur_api] Données reçues du formulaire:")
        logger.info(f"   - cible_N_plus_1 (raw): {cible_N_plus_1}")
        logger.info(f"   - cible_N_plus_2 (raw): {cible_N_plus_2}")
        
        cible_n1_value = Decimal(cible_N_plus_1) if cible_N_plus_1 and cible_N_plus_1.strip() else None
        cible_n2_value = Decimal(cible_N_plus_2) if cible_N_plus_2 and cible_N_plus_2.strip() else None
        
        logger.info(f"🔍 [create_indicateur_api] Valeurs converties:")
        logger.info(f"   - cible_N_plus_1 (Decimal): {cible_n1_value}")
        logger.info(f"   - cible_N_plus_2 (Decimal): {cible_n2_value}")
        
        # Gérer l'upload du document justificatif
        doc_justif_path = None
        valeur_actuelle_decimal = Decimal(valeur_actuelle) if valeur_actuelle and valeur_actuelle.strip() else Decimal(0)
        
        # Validation : si valeur_actuelle != 0, alors doc_justif doit être fourni
        if valeur_actuelle_decimal != 0 and not doc_justif_file:
            raise HTTPException(
                status_code=400,
                detail="Un document justificatif est requis lorsque la valeur actuelle est différente de 0. Cela permet de justifier la valeur renseignée et de détecter d'éventuels biais."
            )
        
        if doc_justif_file and doc_justif_file.filename:
            try:
                # Créer le dossier pour les documents justificatifs
                docs_dir = path_config.UPLOADS_DIR / "performance" / "indicateurs" / "doc_justif"
                path_config.ensure_directory_exists(docs_dir)
                
                # Générer un nom de fichier unique
                file_extension = Path(doc_justif_file.filename).suffix
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{file_extension}"
                file_path = docs_dir / unique_filename
                
                # Sauvegarder le fichier
                content = await doc_justif_file.read()
                file_path.write_bytes(content)
                
                # Stocker le chemin relatif
                doc_justif_path = f"uploads/performance/indicateurs/doc_justif/{unique_filename}"
                logger.info(f"✅ Document justificatif uploadé: {doc_justif_path}")
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'upload du document justificatif: {e}")
                raise HTTPException(status_code=500, detail=f"Erreur lors de l'upload du document justificatif: {e}")
        
        indicateur_data = {
            "objectif_id": objectif_id,
            "nom": nom,
            "description": description,
            "categorie": categorie,
            "frequence_mesure": frequence_mesure,
            "annee": annee,
            "valeur_cible": Decimal(valeur_cible),
            "valeur_actuelle": Decimal(valeur_actuelle) if valeur_actuelle else Decimal(0),
            "unite_mesure": unite_mesure,
            "seuil_alerte_min": Decimal(seuil_alerte_min) if seuil_alerte_min else None,
            "seuil_alerte_max": Decimal(seuil_alerte_max) if seuil_alerte_max else None,
            "responsable_id": responsable_id,
            "service_responsable": service_responsable,
            "source_donnees": source_donnees,
            "methode": methode.strip() if methode and methode.strip() else None,
            "mode_collecte_donnees": mode_collecte_donnees.strip() if mode_collecte_donnees and mode_collecte_donnees.strip() else None,
            "derniere_valeur_connue": Decimal(derniere_valeur_connue) if derniere_valeur_connue and derniere_valeur_connue.strip() else None,
            "sens_appreciation": sens_appreciation.strip().lower() if sens_appreciation and sens_appreciation.strip() else "haut",
            "doc_justif": doc_justif_path,
            "cible_N_plus_1": cible_n1_value,
            "cible_N_plus_2": cible_n2_value,
            "commentaires": commentaires,
        }
        
        logger.info(f"🔍 [create_indicateur_api] indicateur_data final: {list(indicateur_data.keys())}")
        logger.info(f"🔍 [create_indicateur_api] indicateur_data['cible_N_plus_1'] = {indicateur_data.get('cible_N_plus_1')}")
        logger.info(f"🔍 [create_indicateur_api] indicateur_data['cible_N_plus_2'] = {indicateur_data.get('cible_N_plus_2')}")

        # Récupérer l'ID utilisateur (current_user est un objet User)
        user_id = current_user.id if hasattr(current_user, "id") else current_user.get("user_id", 1)

        indicateur = PerformanceService.creer_indicateur(
            session=db, indicateur_data=indicateur_data, created_by_id=user_id
        )

        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=current_user.id if hasattr(current_user, "id") else user_id,
            user_email=current_user.email if hasattr(current_user, "email") else "user@system",
            user_full_name=current_user.full_name if hasattr(current_user, "full_name") else None,
            action_type="create",
            target_type="indicateur_performance",
            target_id=indicateur.id,
            description=f"Création de l'indicateur '{nom}'",
            icon="📊",
        )

        return {"success": True, "message": "Indicateur créé avec succès", "data": {"id": indicateur.id}}

    except Exception as e:
        logger.error(f"Erreur API create_indicateur: {e}")
        return {"success": False, "error": "Erreur lors de la création de l'indicateur"}


@router.put("/api/indicateurs/{indicateur_id}", response_class=JSONResponse)
async def update_indicateur_api(
    indicateur_id: int,
    objectif_id: int | None = Form(None),
    nom: str | None = Form(None),
    description: str | None = Form(None),
    categorie: str | None = Form(None),
    frequence_mesure: str | None = Form(None),
    annee: int | None = Form(None),
    valeur_cible: str | None = Form(None),
    valeur_actuelle: str | None = Form(None),
    unite_mesure: str | None = Form(None),
    seuil_alerte_min: str | None = Form(None),
    seuil_alerte_max: str | None = Form(None),
    responsable_id: int | None = Form(None),
    service_responsable: str | None = Form(None),
    source_donnees: str | None = Form(None),
    methode: str | None = Form(None),
    mode_collecte_donnees: str | None = Form(None),
    derniere_valeur_connue: str | None = Form(None),
    sens_appreciation: str | None = Form(None),
    cible_N_plus_1: str | None = Form(None),
    cible_N_plus_2: str | None = Form(None),
    doc_justif_file: UploadFile | None = FastAPIFile(None),
    doc_justif_delete: str | None = Form(None),
    commentaires: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user: dict = Depends(require_roles("admin", "user")),
):
    """API: Modifie un indicateur existant"""
    try:
        # Récupérer l'indicateur existant pour vérifier la valeur actuelle actuelle
        indicateur_existant = db.exec(
            select(IndicateurPerformance).where(IndicateurPerformance.id == indicateur_id)
        ).first()
        
        if not indicateur_existant:
            return {"success": False, "error": "Indicateur non trouvé"}
        
        # Gérer l'upload du document justificatif
        doc_justif_path = None
        valeur_actuelle_decimal = None
        
        if valeur_actuelle is not None:
            valeur_actuelle_decimal = Decimal(valeur_actuelle) if valeur_actuelle and valeur_actuelle.strip() else Decimal(0)
            
            # Si on demande la suppression du document existant
            if doc_justif_delete == "1":
                doc_justif_path = None
            # Si un nouveau fichier est fourni, l'utiliser
            elif doc_justif_file and doc_justif_file.filename:
                try:
                    docs_dir = path_config.UPLOADS_DIR / "performance" / "indicateurs" / "doc_justif"
                    path_config.ensure_directory_exists(docs_dir)
                    
                    file_extension = Path(doc_justif_file.filename).suffix
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{file_extension}"
                    file_path = docs_dir / unique_filename
                    
                    content = await doc_justif_file.read()
                    file_path.write_bytes(content)
                    
                    doc_justif_path = f"uploads/performance/indicateurs/doc_justif/{unique_filename}"
                    logger.info(f"✅ Document justificatif uploadé: {doc_justif_path}")
                except Exception as e:
                    logger.error(f"❌ Erreur lors de l'upload du document justificatif: {e}")
                    raise HTTPException(status_code=500, detail=f"Erreur lors de l'upload du document justificatif: {e}")
            # Validation : si valeur_actuelle != 0, alors doc_justif doit être fourni (nouveau ou existant)
            elif valeur_actuelle_decimal != 0:
                # Vérifier si un document existe déjà
                if not indicateur_existant.doc_justif:
                    raise HTTPException(
                        status_code=400,
                        detail="Un document justificatif est requis lorsque la valeur actuelle est différente de 0. Cela permet de justifier la valeur renseignée et de détecter d'éventuels biais."
                    )
                else:
                    # Conserver le document existant
                    doc_justif_path = indicateur_existant.doc_justif
        
        indicateur_data = {}

        if objectif_id is not None:
            indicateur_data["objectif_id"] = objectif_id
        if nom is not None:
            indicateur_data["nom"] = nom
        if description is not None:
            indicateur_data["description"] = description
        if categorie is not None:
            indicateur_data["categorie"] = categorie
        if frequence_mesure is not None:
            indicateur_data["frequence_mesure"] = frequence_mesure
        if annee is not None:
            indicateur_data["annee"] = annee
        if valeur_cible is not None:
            indicateur_data["valeur_cible"] = Decimal(valeur_cible)
        if valeur_actuelle is not None:
            indicateur_data["valeur_actuelle"] = Decimal(valeur_actuelle)
        if unite_mesure is not None:
            indicateur_data["unite_mesure"] = unite_mesure
        if seuil_alerte_min is not None:
            indicateur_data["seuil_alerte_min"] = Decimal(seuil_alerte_min) if seuil_alerte_min else None
        if seuil_alerte_max is not None:
            indicateur_data["seuil_alerte_max"] = Decimal(seuil_alerte_max) if seuil_alerte_max else None
        if responsable_id is not None:
            indicateur_data["responsable_id"] = responsable_id
        if service_responsable is not None:
            indicateur_data["service_responsable"] = service_responsable
        if source_donnees is not None:
            indicateur_data["source_donnees"] = source_donnees
        if methode is not None:
            indicateur_data["methode"] = methode.strip() if methode and methode.strip() else None
        if mode_collecte_donnees is not None:
            indicateur_data["mode_collecte_donnees"] = mode_collecte_donnees.strip() if mode_collecte_donnees and mode_collecte_donnees.strip() else None
        if derniere_valeur_connue is not None:
            indicateur_data["derniere_valeur_connue"] = Decimal(derniere_valeur_connue) if derniere_valeur_connue and derniere_valeur_connue.strip() else None
        if sens_appreciation is not None:
            indicateur_data["sens_appreciation"] = sens_appreciation.strip().lower() if sens_appreciation and sens_appreciation.strip() else "haut"
        if doc_justif_path is not None or doc_justif_delete == "1":
            # Mettre à jour doc_justif si un nouveau fichier a été uploadé ou si on demande la suppression
            indicateur_data["doc_justif"] = None if doc_justif_delete == "1" else doc_justif_path
        if cible_N_plus_1 is not None:
            indicateur_data["cible_N_plus_1"] = Decimal(cible_N_plus_1) if cible_N_plus_1 and cible_N_plus_1.strip() else None
        if cible_N_plus_2 is not None:
            indicateur_data["cible_N_plus_2"] = Decimal(cible_N_plus_2) if cible_N_plus_2 and cible_N_plus_2.strip() else None
        if commentaires is not None:
            indicateur_data["commentaires"] = commentaires

        indicateur = PerformanceService.modifier_indicateur(db, indicateur_id, indicateur_data)

        if not indicateur:
            return {"success": False, "error": "Indicateur non trouvé"}

        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=current_user.id if hasattr(current_user, "id") else 1,
            user_email=current_user.email if hasattr(current_user, "email") else "user@system",
            user_full_name=current_user.full_name if hasattr(current_user, "full_name") else None,
            action_type="update",
            target_type="indicateur_performance",
            target_id=indicateur.id,
            description=f"Modification de l'indicateur '{indicateur.nom}'",
            icon="✏️",
        )

        return {"success": True, "message": "Indicateur modifié avec succès", "data": {"id": indicateur.id}}

    except Exception as e:
        logger.error(f"Erreur API update_indicateur: {e}")
        return {"success": False, "error": "Erreur lors de la modification de l'indicateur"}


@router.delete("/api/indicateurs/{indicateur_id}", response_class=JSONResponse, name="delete_indicateur_api")
def delete_indicateur_api(
    indicateur_id: int, db: Session = Depends(get_session), current_user=Depends(require_roles("admin", "user"))
):
    """API: Supprime un indicateur"""
    try:
        # Récupérer l'indicateur avant de le supprimer pour logger
        indicateur = PerformanceService.get_indicateur(db, indicateur_id)
        if not indicateur:
            return {"success": False, "error": "Indicateur non trouvé"}

        indicateur_nom = indicateur.nom

        success = PerformanceService.supprimer_indicateur(db, indicateur_id)

        if not success:
            return {"success": False, "error": "Erreur lors de la suppression"}

        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=current_user.id if hasattr(current_user, "id") else 1,
            user_email=current_user.email if hasattr(current_user, "email") else "user@system",
            user_full_name=current_user.full_name if hasattr(current_user, "full_name") else None,
            action_type="delete",
            target_type="indicateur_performance",
            target_id=indicateur_id,
            description=f"Suppression de l'indicateur '{indicateur_nom}'",
            icon="🗑️",
        )

        return {"success": True, "message": "Indicateur supprimé avec succès"}

    except Exception as e:
        logger.error(f"Erreur API delete_indicateur: {e}")
        return {"success": False, "error": "Erreur lors de la suppression de l'indicateur"}


# ============================================
# ROUTES GÉNÉRATION DE RAPPORTS
# ============================================


@router.post("/api/rapports/generate", name="generate_report_api")
def generate_report_api(
    report_type: str = Form(...),
    period: str = Form(...),
    format: str = Form("PDF"),
    date_debut: str | None = Form(None),
    date_fin: str | None = Form(None),
    db: Session = Depends(get_session),
    current_user=Depends(require_roles("admin", "user")),
):
    """API: Génère un rapport de performance"""
    try:
        # Convertir les dates si fournies
        debut = datetime.strptime(date_debut, "%Y-%m-%d").date() if date_debut else None
        fin = datetime.strptime(date_fin, "%Y-%m-%d").date() if date_fin else None

        # Récupérer le nom de l'utilisateur
        user_name = (
            current_user.full_name
            if hasattr(current_user, "full_name") and current_user.full_name
            else current_user.email
            if hasattr(current_user, "email")
            else "Utilisateur"
        )

        # Générer le rapport selon le format
        if format == "PDF":
            pdf_buffer = ReportGenerator.generate_pdf_report(
                session=db, report_type=report_type, period=period, date_debut=debut, date_fin=fin, user_name=user_name
            )

            # Nom du fichier
            filename = f"rapport_performance_{report_type.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            # Calculer les dates selon la période
            dates = ReportGenerator._calculate_period_dates(period, debut, fin)

            # Récupérer les KPIs pour les statistiques
            kpis = PerformanceService.get_kpis_objectifs(db)
            objectifs = PerformanceService.get_objectifs(db, limit=1000)
            indicateurs = PerformanceService.get_indicateurs(db, limit=1000)

            # Créer un enregistrement dans l'historique
            rapport = RapportPerformance(
                titre=f"Rapport {report_type} - {dates['debut'].strftime('%d/%m/%Y')} au {dates['fin'].strftime('%d/%m/%Y')}",
                description="Rapport de performance généré automatiquement",
                type_rapport=report_type,
                format_fichier=format,
                periode=period,
                date_debut=dates["debut"],
                date_fin=dates["fin"],
                fichier_nom=filename,
                fichier_taille=len(pdf_buffer.getvalue()),
                nb_objectifs=len(objectifs),
                nb_indicateurs=len(indicateurs),
                taux_realisation=kpis.get("taux_realisation", 0),
                created_by_id=current_user.id if hasattr(current_user, "id") else 1,
                created_by_nom=user_name,
            )
            db.add(rapport)
            db.commit()
            db.refresh(rapport)

            # Logger l'activité
            ActivityService.log_activity(
                db_session=db,
                user_id=current_user.id if hasattr(current_user, "id") else 1,
                user_email=current_user.email if hasattr(current_user, "email") else "user@system",
                user_full_name=current_user.full_name if hasattr(current_user, "full_name") else None,
                action_type="generate",
                target_type="rapport_performance",
                description=f"Génération d'un rapport {report_type} ({format}) pour la période {period}",
                icon="📋",
            )

            return StreamingResponse(
                pdf_buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        else:
            return {"success": False, "error": f"Format {format} non encore implémenté. Utilisez PDF pour l'instant."}

    except Exception as e:
        logger.error(f"Erreur API generate_report: {e}")
        return {"success": False, "error": f"Erreur lors de la génération du rapport: {e!s}"}


@router.get("/api/rapports/historique", name="get_rapports_historique")
def get_rapports_historique(db: Session = Depends(get_session), current_user=Depends(require_roles("admin", "user"))):
    """API: Récupère l'historique des rapports générés"""
    try:
        # Récupérer les 50 derniers rapports
        rapports = db.exec(select(RapportPerformance).order_by(RapportPerformance.created_at.desc()).limit(50)).all()

        # Convertir en dictionnaire
        rapports_data = []
        for rapport in rapports:
            rapports_data.append(
                {
                    "id": rapport.id,
                    "titre": rapport.titre,
                    "description": rapport.description,
                    "type_rapport": rapport.type_rapport,
                    "format_fichier": rapport.format_fichier,
                    "periode": rapport.periode,
                    "date_debut": rapport.date_debut.strftime("%Y-%m-%d"),
                    "date_fin": rapport.date_fin.strftime("%Y-%m-%d"),
                    "fichier_nom": rapport.fichier_nom,
                    "fichier_taille": rapport.fichier_taille,
                    "nb_objectifs": rapport.nb_objectifs,
                    "nb_indicateurs": rapport.nb_indicateurs,
                    "taux_realisation": float(rapport.taux_realisation) if rapport.taux_realisation else 0,
                    "created_at": rapport.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "created_by_nom": rapport.created_by_nom,
                }
            )

        return {"success": True, "rapports": rapports_data, "total": len(rapports_data)}

    except Exception as e:
        logger.error(f"Erreur API get_rapports_historique: {e}")
        return {"success": False, "error": f"Erreur lors de la récupération de l'historique: {e!s}"}


@router.delete("/api/rapports/{rapport_id}", name="delete_rapport_api")
def delete_rapport_api(
    rapport_id: int, db: Session = Depends(get_session), current_user=Depends(require_roles("admin", "user"))
):
    """API: Supprime un rapport de l'historique"""
    try:
        # Récupérer le rapport
        rapport = db.get(RapportPerformance, rapport_id)

        if not rapport:
            return {"success": False, "error": "Rapport non trouvé"}

        # Supprimer le rapport
        db.delete(rapport)
        db.commit()

        # Logger l'activité
        ActivityService.log_activity(
            db_session=db,
            user_id=current_user.id if hasattr(current_user, "id") else 1,
            user_email=current_user.email if hasattr(current_user, "email") else "user@system",
            user_full_name=current_user.full_name if hasattr(current_user, "full_name") else None,
            action_type="delete",
            target_type="rapport_performance",
            description=f"Suppression du rapport: {rapport.titre}",
            icon="🗑️",
        )

        return {"success": True, "message": "Rapport supprimé avec succès"}

    except Exception as e:
        logger.error(f"Erreur API delete_rapport: {e}")
        return {"success": False, "error": f"Erreur lors de la suppression du rapport: {e!s}"}


# ============================================
# ROUTES HTML ORIENTATIONS STRATÉGIQUES
# ============================================


@router.get("/orientations", response_class=HTMLResponse, name="performance_orientations")
def performance_orientations(request: Request, db: Session = Depends(get_session)):
    """Gestion des orientations stratégiques"""
    try:
        from app.templates import get_template_context, templates

        context = get_template_context(request)
        context.update(
            {
                "page_title": "Orientations Stratégiques",
                "module_name": "Performance",
                "module_description": "Définition et suivi des orientations stratégiques",
            }
        )

        return templates.TemplateResponse("pages/performance_orientations.html", context)

    except Exception as e:
        logger.error(f"Erreur lors du chargement des orientations stratégiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ============================================
# ROUTES HTML RÉSULTATS STRATÉGIQUES
# ============================================


@router.get("/resultats", response_class=HTMLResponse, name="performance_resultats")
def performance_resultats(request: Request, db: Session = Depends(get_session)):
    """Gestion des résultats stratégiques"""
    try:
        from app.templates import get_template_context, templates

        context = get_template_context(request)
        context.update(
            {
                "page_title": "Résultats Stratégiques",
                "module_name": "Performance",
                "module_description": "Définition et suivi des résultats stratégiques",
            }
        )

        return templates.TemplateResponse("pages/performance_resultats.html", context)

    except Exception as e:
        logger.error(f"Erreur lors du chargement des résultats stratégiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ============================================
# ROUTES CRUD ORIENTATIONS STRATÉGIQUES
# ============================================


@router.get("/api/orientations", response_class=JSONResponse, name="get_orientations_api")
def get_orientations_api(
    db: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    actif: bool | None = Query(None),
):
    """API: Récupère la liste des orientations stratégiques"""
    try:
        orientations = PerformanceService.get_orientations_strategiques(
            session=db,
            skip=skip,
            limit=limit,
            actif=actif,
        )

        return {
            "success": True,
            "data": [
                {
                    "id": orient.id,
                    "libelle": orient.libelle,
                    "description": orient.description,
                    "ordre": orient.ordre,
                    "actif": orient.actif,
                    "created_at": orient.created_at.isoformat(),
                    "updated_at": orient.updated_at.isoformat(),
                }
                for orient in orientations
            ],
        }

    except Exception as e:
        logger.error(f"Erreur API get_orientations: {e}")
        return {"success": False, "error": "Erreur lors de la récupération des orientations stratégiques"}


@router.get("/api/orientations/{orientation_id}", response_class=JSONResponse, name="get_orientation_api")
def get_orientation_api(orientation_id: int, db: Session = Depends(get_session)):
    """API: Récupère une orientation stratégique par son ID"""
    try:
        orientation = PerformanceService.get_orientation_strategique(session=db, orientation_id=orientation_id)
        if not orientation:
            return {"success": False, "error": "Orientation stratégique non trouvée"}

        return {
            "success": True,
            "data": {
                "id": orientation.id,
                "libelle": orientation.libelle,
                "description": orientation.description,
                "ordre": orientation.ordre,
                "actif": orientation.actif,
                "created_at": orientation.created_at.isoformat(),
                "updated_at": orientation.updated_at.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Erreur API get_orientation: {e}")
        return {"success": False, "error": "Erreur lors de la récupération de l'orientation stratégique"}


@router.post("/api/orientations", response_class=JSONResponse, name="create_orientation_api")
def create_orientation_api(
    libelle: str = Form(...),
    description: str | None = Form(None),
    ordre: int | None = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """API: Crée une nouvelle orientation stratégique"""
    try:
        orientation_data = {
            "libelle": libelle,
            "description": description,
            "ordre": ordre,
            "actif": actif,
        }

        orientation = PerformanceService.creer_orientation_strategique(
            session=session, orientation_data=orientation_data, created_by_id=current_user.id
        )

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="orientation_strategique",
            description=f"Création de l'orientation stratégique: {orientation.libelle}",
            icon="📋",
        )

        return {
            "success": True,
            "message": "Orientation stratégique créée avec succès",
            "data": {
                "id": orientation.id,
                "libelle": orientation.libelle,
            },
        }

    except Exception as e:
        logger.error(f"Erreur API create_orientation: {e}")
        return {"success": False, "error": f"Erreur lors de la création de l'orientation stratégique: {e!s}"}


@router.post("/api/orientations/{orientation_id}", response_class=JSONResponse, name="update_orientation_api")
def update_orientation_api(
    orientation_id: int,
    libelle: str = Form(...),
    description: str | None = Form(None),
    ordre: int | None = Form(None),
    actif: bool = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """API: Modifie une orientation stratégique"""
    try:
        orientation_data = {
            "libelle": libelle,
            "description": description,
            "ordre": ordre,
            "actif": actif,
        }

        orientation = PerformanceService.modifier_orientation_strategique(
            session=session, orientation_id=orientation_id, orientation_data=orientation_data
        )

        if not orientation:
            return {"success": False, "error": "Orientation stratégique non trouvée"}

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="orientation_strategique",
            description=f"Modification de l'orientation stratégique: {orientation.libelle}",
            icon="📋",
        )

        return {
            "success": True,
            "message": "Orientation stratégique modifiée avec succès",
            "data": {
                "id": orientation.id,
                "libelle": orientation.libelle,
            },
        }

    except Exception as e:
        logger.error(f"Erreur API update_orientation: {e}")
        return {"success": False, "error": f"Erreur lors de la modification de l'orientation stratégique: {e!s}"}


@router.delete("/api/orientations/{orientation_id}", response_class=JSONResponse, name="delete_orientation_api")
def delete_orientation_api(
    orientation_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """API: Supprime une orientation stratégique"""
    try:
        orientation = PerformanceService.get_orientation_strategique(session=session, orientation_id=orientation_id)
        if not orientation:
            return {"success": False, "error": "Orientation stratégique non trouvée"}

        success = PerformanceService.supprimer_orientation_strategique(session=session, orientation_id=orientation_id)

        if not success:
            return {"success": False, "error": "Erreur lors de la suppression de l'orientation stratégique"}

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="delete",
            target_type="orientation_strategique",
            description=f"Suppression de l'orientation stratégique: {orientation.libelle}",
            icon="📋",
        )

        return {"success": True, "message": "Orientation stratégique supprimée avec succès"}

    except Exception as e:
        logger.error(f"Erreur API delete_orientation: {e}")
        return {"success": False, "error": f"Erreur lors de la suppression de l'orientation stratégique: {e!s}"}


# ============================================
# ROUTES CRUD RÉSULTATS STRATÉGIQUES
# ============================================


@router.get("/api/resultats", response_class=JSONResponse, name="get_resultats_api")
def get_resultats_api(
    db: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    orientation_id: int | None = Query(None),
    actif: bool | None = Query(None),
):
    """API: Récupère la liste des résultats stratégiques"""
    try:
        resultats = PerformanceService.get_resultats_strategiques(
            session=db,
            skip=skip,
            limit=limit,
            orientation_id=orientation_id,
            actif=actif,
        )

        return {
            "success": True,
            "data": [
                {
                    "id": resultat.id,
                    "orientation_id": resultat.orientation_id,
                    "libelle": resultat.libelle,
                    "description": resultat.description,
                    "ordre": resultat.ordre,
                    "actif": resultat.actif,
                    "created_at": resultat.created_at.isoformat(),
                    "updated_at": resultat.updated_at.isoformat(),
                }
                for resultat in resultats
            ],
        }

    except Exception as e:
        logger.error(f"Erreur API get_resultats: {e}")
        return {"success": False, "error": "Erreur lors de la récupération des résultats stratégiques"}


@router.get("/api/resultats/{resultat_id}", response_class=JSONResponse, name="get_resultat_api")
def get_resultat_api(resultat_id: int, db: Session = Depends(get_session)):
    """API: Récupère un résultat stratégique par son ID"""
    try:
        resultat = PerformanceService.get_resultat_strategique(session=db, resultat_id=resultat_id)
        if not resultat:
            return {"success": False, "error": "Résultat stratégique non trouvé"}

        return {
            "success": True,
            "data": {
                "id": resultat.id,
                "orientation_id": resultat.orientation_id,
                "libelle": resultat.libelle,
                "description": resultat.description,
                "ordre": resultat.ordre,
                "actif": resultat.actif,
                "created_at": resultat.created_at.isoformat(),
                "updated_at": resultat.updated_at.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Erreur API get_resultat: {e}")
        return {"success": False, "error": "Erreur lors de la récupération du résultat stratégique"}


@router.post("/api/resultats", response_class=JSONResponse, name="create_resultat_api")
def create_resultat_api(
    orientation_id: int = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    ordre: int | None = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """API: Crée un nouveau résultat stratégique"""
    try:
        resultat_data = {
            "orientation_id": orientation_id,
            "libelle": libelle,
            "description": description,
            "ordre": ordre,
            "actif": actif,
        }

        resultat = PerformanceService.creer_resultat_strategique(
            session=session, resultat_data=resultat_data, created_by_id=current_user.id
        )

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="resultat_strategique",
            description=f"Création du résultat stratégique: {resultat.libelle}",
            icon="📋",
        )

        return {
            "success": True,
            "message": "Résultat stratégique créé avec succès",
            "data": {
                "id": resultat.id,
                "libelle": resultat.libelle,
            },
        }

    except Exception as e:
        logger.error(f"Erreur API create_resultat: {e}")
        return {"success": False, "error": f"Erreur lors de la création du résultat stratégique: {e!s}"}


@router.post("/api/resultats/{resultat_id}", response_class=JSONResponse, name="update_resultat_api")
def update_resultat_api(
    resultat_id: int,
    orientation_id: int = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    ordre: int | None = Form(None),
    actif: bool = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """API: Modifie un résultat stratégique"""
    try:
        resultat_data = {
            "orientation_id": orientation_id,
            "libelle": libelle,
            "description": description,
            "ordre": ordre,
            "actif": actif,
        }

        resultat = PerformanceService.modifier_resultat_strategique(
            session=session, resultat_id=resultat_id, resultat_data=resultat_data
        )

        if not resultat:
            return {"success": False, "error": "Résultat stratégique non trouvé"}

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="resultat_strategique",
            description=f"Modification du résultat stratégique: {resultat.libelle}",
            icon="📋",
        )

        return {
            "success": True,
            "message": "Résultat stratégique modifié avec succès",
            "data": {
                "id": resultat.id,
                "libelle": resultat.libelle,
            },
        }

    except Exception as e:
        logger.error(f"Erreur API update_resultat: {e}")
        return {"success": False, "error": f"Erreur lors de la modification du résultat stratégique: {e!s}"}


@router.delete("/api/resultats/{resultat_id}", response_class=JSONResponse, name="delete_resultat_api")
def delete_resultat_api(
    resultat_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """API: Supprime un résultat stratégique"""
    try:
        resultat = PerformanceService.get_resultat_strategique(session=session, resultat_id=resultat_id)
        if not resultat:
            return {"success": False, "error": "Résultat stratégique non trouvé"}

        success = PerformanceService.supprimer_resultat_strategique(session=session, resultat_id=resultat_id)

        if not success:
            return {"success": False, "error": "Erreur lors de la suppression du résultat stratégique"}

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="delete",
            target_type="resultat_strategique",
            description=f"Suppression du résultat stratégique: {resultat.libelle}",
            icon="📋",
        )

        return {"success": True, "message": "Résultat stratégique supprimé avec succès"}

    except Exception as e:
        logger.error(f"Erreur API delete_resultat: {e}")
        return {"success": False, "error": f"Erreur lors de la suppression du résultat stratégique: {e!s}"}
