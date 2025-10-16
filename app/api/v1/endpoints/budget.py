# app/api/v1/endpoints/budget.py
"""
Endpoints pour la gestion budgétaire et les conférences budgétaires
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, RedirectResponse
from sqlmodel import Session, select, func, delete
from datetime import datetime, date
from pathlib import Path
from decimal import Decimal
import pandas as pd
import io
from io import BytesIO
import re
from collections import defaultdict
import unicodedata

from app.db.session import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.budget import (
    NatureDepense, Activite, FicheTechnique, LigneBudgetaire,
    DocumentBudget, HistoriqueBudget, ExecutionBudgetaire,
    ActionBudgetaire, ServiceBeneficiaire, ActiviteBudgetaire, LigneBudgetaireDetail,
    DocumentLigneBudgetaire,
    SigobeChargement, SigobeExecution, SigobeKpi
)
from app.models.personnel import Programme, Direction
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger
from app.services.activity_service import ActivityService

logger = get_logger(__name__)
router = APIRouter()


# ============================================
# DASHBOARD BUDGÉTAIRE
# ============================================

@router.get("/", response_class=HTMLResponse, name="budget_home")
def budget_home(
    request: Request,
    annee: Optional[int] = None,
    programme_id: Optional[int] = None,
    trimestre: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Dashboard principal du suivi budgétaire
    Utilise les données SIGOBE pour les KPIs
    """
    # Déterminer l'année à utiliser
    if not annee:
        # Si pas d'année spécifiée, chercher la dernière année disponible dans SIGOBE
        dernier_chargement_any = session.exec(
            select(SigobeChargement).order_by(SigobeChargement.annee.desc(), SigobeChargement.date_chargement.desc())
        ).first()
        
        if dernier_chargement_any:
            annee = dernier_chargement_any.annee
            logger.info(f"📅 Aucune année spécifiée, utilisation de la dernière année SIGOBE : {annee}")
        else:
            annee = datetime.now().year
            logger.warning(f"⚠️ Aucune donnée SIGOBE trouvée, utilisation de l'année courante : {annee}")
    
    # Récupérer le dernier chargement SIGOBE pour cette année
    chargement_query = select(SigobeChargement).where(SigobeChargement.annee == annee)
    if trimestre:
        chargement_query = chargement_query.where(SigobeChargement.trimestre == trimestre)
    
    dernier_chargement = session.exec(
        chargement_query.order_by(SigobeChargement.date_chargement.desc())
    ).first()
    
    logger.info(f"🔍 Dashboard SIGOBE - Année: {annee}, Chargement: {dernier_chargement.id if dernier_chargement else 'Aucun'}")
    
    # KPIs par défaut
    budget_vote_total = 0
    budget_actuel_total = 0
    engagements_total = 0
    mandats_emis_total = 0
    mandats_vises_total = 0
    mandats_pec_total = 0
    disponible_eng_total = 0
    taux_engagement = 0
    taux_mandatement_emis = 0
    taux_mandatement_vise = 0
    taux_mandatement_pec = 0
    taux_execution_global = 0
    
    exec_par_programme = {}
    exec_par_nature = {}
    
    if dernier_chargement:
        # Récupérer les KPIs globaux
        kpi_global = session.exec(
            select(SigobeKpi)
            .where(SigobeKpi.chargement_id == dernier_chargement.id)
            .where(SigobeKpi.dimension == "global")
        ).first()
        
        if kpi_global:
            budget_vote_total = float(kpi_global.budget_vote_total or 0)
            budget_actuel_total = float(kpi_global.budget_actuel_total or 0)
            engagements_total = float(kpi_global.engagements_total or 0)
            mandats_emis_total = float(kpi_global.mandats_total or 0)
            
            # Récupérer les totaux détaillés depuis SigobeExecution
            executions_sigobe = session.exec(
                select(SigobeExecution)
                .where(SigobeExecution.chargement_id == dernier_chargement.id)
            ).all()
            
            mandats_vises_total = sum(float(e.mandats_vise_cf or 0) for e in executions_sigobe)
            mandats_pec_total = sum(float(e.mandats_pec or 0) for e in executions_sigobe)
            disponible_eng_total = sum(float(e.disponible_eng or 0) for e in executions_sigobe)
            
            # Calculer les taux selon vos formules DAX
            # _Tx_Eng : DIVIDE(Engagements, Budget_Actuel)
            budg_select = budget_actuel_total or budget_vote_total
            taux_engagement = (engagements_total / budg_select * 100) if budg_select > 0 else 0
            
            # _Tx_Mandat_Emis : DIVIDE(Mandats_Emis, Engagements)
            taux_mandatement_emis = (mandats_emis_total / engagements_total * 100) if engagements_total > 0 else 0
            
            # _Tx_Mandat_Vise : DIVIDE(Mandats_Vise, Mandats_PEC)
            taux_mandatement_vise = (mandats_vises_total / mandats_pec_total * 100) if mandats_pec_total > 0 else 0
            
            # _Tx_Mandat_PEC : DIVIDE(Mandats_PEC, Mandats_Emis)
            taux_mandatement_pec = (mandats_pec_total / mandats_emis_total * 100) if mandats_emis_total > 0 else 0
            
            # _Tx_Exe.Global : DIVIDE(Disponible, Budget_Actuel)  
            taux_execution_global = (disponible_eng_total / budg_select * 100) if budg_select > 0 else 0
    
        # Récupérer les KPIs par programme
        if dernier_chargement:
            kpis_programmes = session.exec(
                select(SigobeKpi)
                .where(SigobeKpi.chargement_id == dernier_chargement.id)
                .where(SigobeKpi.dimension == "programme")
            ).all()
            
            for kpi in kpis_programmes:
                # Utiliser le libellé comme clé si le code est vide
                code = kpi.dimension_code or kpi.dimension_libelle or "INCONNU"
                exec_par_programme[code] = {
                    "libelle": kpi.dimension_libelle or code,
                    "budget": float(kpi.budget_actuel_total or 0),
                    "engagements": float(kpi.engagements_total or 0),
                    "mandats": float(kpi.mandats_total or 0),
                    "taux": float(kpi.taux_execution or 0)
                }
            
            # Récupérer les KPIs par nature
            kpis_natures = session.exec(
                select(SigobeKpi)
                .where(SigobeKpi.chargement_id == dernier_chargement.id)
                .where(SigobeKpi.dimension == "nature")
            ).all()
            
            for kpi in kpis_natures:
                # Utiliser le libellé comme clé si le code est vide
                code = kpi.dimension_code or kpi.dimension_libelle or "INCONNU"
                exec_par_nature[code] = {
                    "libelle": kpi.dimension_libelle or code,
                    "budget": float(kpi.budget_actuel_total or 0),
                    "engagements": float(kpi.engagements_total or 0),
                    "mandats": float(kpi.mandats_total or 0),
                    "taux": float(kpi.taux_execution or 0)
                }
    
    # Récupérer les programmes pour les filtres
    programmes = session.exec(select(Programme).where(Programme.actif == True)).all()
    
    # Récupérer les années disponibles dans SIGOBE
    annees_sigobe_query = select(SigobeChargement.annee).distinct().order_by(SigobeChargement.annee.desc())
    annees_sigobe = [a for a in session.exec(annees_sigobe_query).all()]
    
    # Calculer les variations par rapport à l'année précédente
    variation_engagement = None
    variation_mandatement_vise = None
    variation_mandatement_pec = None
    variation_execution_global = None
    taux_engagement_n1 = None
    taux_mandatement_vise_n1 = None
    taux_mandatement_pec_n1 = None
    taux_execution_global_n1 = None
    
    if annee and (annee - 1) in annees_sigobe:
        # Récupérer le dernier chargement de l'année N-1
        chargement_n1_query = select(SigobeChargement).where(SigobeChargement.annee == (annee - 1))
        if trimestre:
            chargement_n1_query = chargement_n1_query.where(SigobeChargement.trimestre == trimestre)
        
        chargement_n1 = session.exec(
            chargement_n1_query.order_by(SigobeChargement.date_chargement.desc())
        ).first()
        
        if chargement_n1:
            # Récupérer les KPIs globaux de N-1
            kpi_global_n1 = session.exec(
                select(SigobeKpi)
                .where(SigobeKpi.chargement_id == chargement_n1.id)
                .where(SigobeKpi.dimension == "global")
            ).first()
            
            if kpi_global_n1:
                # Récupérer les données brutes de N-1 pour appliquer les MÊMES formules que N
                executions_sigobe_n1 = session.exec(
                    select(SigobeExecution)
                    .where(SigobeExecution.chargement_id == chargement_n1.id)
                ).all()
                
                budget_actuel_n1 = float(kpi_global_n1.budget_actuel_total or 0)
                budget_vote_n1 = float(kpi_global_n1.budget_vote_total or 0)
                engagements_n1 = float(kpi_global_n1.engagements_total or 0)
                mandats_emis_n1 = float(kpi_global_n1.mandats_total or 0)
                
                mandats_vises_n1 = sum(float(e.mandats_vise_cf or 0) for e in executions_sigobe_n1)
                mandats_pec_n1 = sum(float(e.mandats_pec or 0) for e in executions_sigobe_n1)
                disponible_eng_n1 = sum(float(e.disponible_eng or 0) for e in executions_sigobe_n1)
                
                # Calculer les taux N-1 avec les MÊMES formules que N
                budg_select_n1 = budget_actuel_n1 or budget_vote_n1
                taux_engagement_n1 = (engagements_n1 / budg_select_n1 * 100) if budg_select_n1 > 0 else 0
                taux_mandatement_vise_n1 = (mandats_vises_n1 / mandats_pec_n1 * 100) if mandats_pec_n1 > 0 else 0
                taux_mandatement_pec_n1 = (mandats_pec_n1 / mandats_emis_n1 * 100) if mandats_emis_n1 > 0 else 0
                taux_execution_global_n1 = (disponible_eng_n1 / budg_select_n1 * 100) if budg_select_n1 > 0 else 0
                
                # Calculer les variations (différence absolue en points de pourcentage)
                variation_engagement = taux_engagement - taux_engagement_n1
                variation_mandatement_vise = taux_mandatement_vise - taux_mandatement_vise_n1
                variation_mandatement_pec = taux_mandatement_pec - taux_mandatement_pec_n1
                variation_execution_global = taux_execution_global - taux_execution_global_n1
    
    return templates.TemplateResponse(
        "pages/budget_dashboard.html",
        get_template_context(
            request,
            annee=annee,
            trimestre=trimestre,
            annees_disponibles=annees_sigobe,
            budget_vote_total=budget_vote_total,
            budget_actuel_total=budget_actuel_total,
            engagements_total=engagements_total,
            mandats_emis_total=mandats_emis_total,
            mandats_vises_total=mandats_vises_total,
            mandats_pec_total=mandats_pec_total,
            disponible_eng_total=disponible_eng_total,
            taux_engagement=round(taux_engagement, 2),
            taux_mandatement_emis=round(taux_mandatement_emis, 2),
            taux_mandatement_vise=round(taux_mandatement_vise, 2),
            taux_mandatement_pec=round(taux_mandatement_pec, 2),
            taux_execution_global=round(taux_execution_global, 2),
            exec_par_programme=exec_par_programme,
            exec_par_nature=exec_par_nature,
            programmes=programmes,
            dernier_chargement=dernier_chargement,
            # Variations N vs N-1
            variation_engagement=round(variation_engagement, 2) if variation_engagement is not None else None,
            variation_mandatement_vise=round(variation_mandatement_vise, 2) if variation_mandatement_vise is not None else None,
            variation_mandatement_pec=round(variation_mandatement_pec, 2) if variation_mandatement_pec is not None else None,
            variation_execution_global=round(variation_execution_global, 2) if variation_execution_global is not None else None,
            taux_engagement_n1=round(taux_engagement_n1, 2) if taux_engagement_n1 is not None else None,
            taux_mandatement_vise_n1=round(taux_mandatement_vise_n1, 2) if taux_mandatement_vise_n1 is not None else None,
            taux_mandatement_pec_n1=round(taux_mandatement_pec_n1, 2) if taux_mandatement_pec_n1 is not None else None,
            taux_execution_global_n1=round(taux_execution_global_n1, 2) if taux_execution_global_n1 is not None else None,
            current_user=current_user
        )
    )


# ============================================
# FICHES TECHNIQUES
# ============================================

@router.get("/fiches", response_class=HTMLResponse, name="budget_fiches")
def budget_fiches(
    request: Request,
    annee: Optional[int] = None,
):
    """Redirection vers la version hiérarchique des fiches"""
    # Rediriger vers la nouvelle version hiérarchique
    if annee:
        return RedirectResponse(url=f"/api/v1/budget/fiches/hierarchique?annee={annee}", status_code=303)
    else:
        return RedirectResponse(url="/api/v1/budget/fiches/hierarchique?annee=toutes", status_code=303)


@router.get("/fiches/hierarchique", response_class=HTMLResponse, name="budget_fiches_hierarchique")
def budget_fiches_hierarchique(
    request: Request,
    annee: Optional[str] = None,
    programme_id: Optional[str] = None,
    direction_id: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste des fiches techniques avec structure hiérarchique"""
    # Construire la requête avec filtres
    query = select(FicheTechnique).where(FicheTechnique.actif == True)
    
    # Filtre par année
    if annee and annee != "toutes":
        query = query.where(FicheTechnique.annee_budget == int(annee))
    
    # Filtre par programme
    if programme_id and programme_id != "tous":
        query = query.where(FicheTechnique.programme_id == int(programme_id))
    
    # Filtre par direction
    if direction_id and direction_id != "toutes":
        query = query.where(FicheTechnique.direction_id == int(direction_id))
    
    fiches = session.exec(query.order_by(FicheTechnique.created_at.desc())).all()
    
    # Valeurs sélectionnées pour l'affichage
    annee_selectionnee = annee if annee else "toutes"
    programme_selectionne = programme_id if programme_id else "tous"
    direction_selectionnee = direction_id if direction_id else "toutes"
    
    # Référentiels
    programmes_dict = {p.id: p for p in session.exec(select(Programme)).all()}
    directions_dict = {d.id: d for d in session.exec(select(Direction)).all()}
    
    # Listes pour les filtres
    programmes_list = session.exec(select(Programme).where(Programme.actif == True).order_by(Programme.code)).all()
    directions_list = session.exec(select(Direction).where(Direction.actif == True).order_by(Direction.code)).all()
    
    # Années disponibles
    annees_disponibles = session.exec(
        select(FicheTechnique.annee_budget).distinct().order_by(FicheTechnique.annee_budget.desc())
    ).all()
    
    return templates.TemplateResponse(
        "pages/budget_fiches_hierarchique.html",
        get_template_context(
            request,
            annee=annee_selectionnee,
            programme_id=programme_selectionne,
            direction_id=direction_selectionnee,
            fiches=fiches,
            programmes=programmes_dict,
            directions=directions_dict,
            programmes_list=programmes_list,
            directions_list=directions_list,
            annees_disponibles=annees_disponibles,
            current_user=current_user
        )
    )


@router.get("/fiches/nouveau", response_class=HTMLResponse, name="budget_fiche_nouveau")
def budget_fiche_nouveau(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de création de fiche technique"""
    programmes = session.exec(select(Programme).where(Programme.actif == True).order_by(Programme.code)).all()
    directions = session.exec(select(Direction).where(Direction.actif == True).order_by(Direction.libelle)).all()
    natures = session.exec(select(NatureDepense).where(NatureDepense.actif == True).order_by(NatureDepense.code)).all()
    activites = session.exec(select(Activite).where(Activite.actif == True).order_by(Activite.code)).all()
    
    return templates.TemplateResponse(
        "pages/budget_fiche_form.html",
        get_template_context(
            request,
            mode="create",
            programmes=programmes,
            directions=directions,
            natures=natures,
            activites=activites,
            current_user=current_user
        )
    )


@router.get("/fiches/{fiche_id}/edit", response_class=HTMLResponse, name="budget_fiche_edit")
def budget_fiche_edit(
    fiche_id: int,
):
    """Redirection vers la structure hiérarchique pour modifier les lignes"""
    # Une fiche technique ne se modifie pas directement, on modifie ses lignes via la structure
    return RedirectResponse(url=f"/api/v1/budget/fiches/{fiche_id}/structure", status_code=303)


@router.get("/fiches/{fiche_id}", response_class=HTMLResponse, name="budget_fiche_detail")
def budget_fiche_detail(
    fiche_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Détail d'une fiche technique"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche technique non trouvée")
    
    # Lignes budgétaires
    lignes = session.exec(
        select(LigneBudgetaire)
        .where(LigneBudgetaire.fiche_technique_id == fiche_id)
        .where(LigneBudgetaire.actif == True)
        .order_by(LigneBudgetaire.ordre)
    ).all()
    
    # Documents
    documents = session.exec(
        select(DocumentBudget)
        .where(DocumentBudget.fiche_technique_id == fiche_id)
        .where(DocumentBudget.actif == True)
        .order_by(DocumentBudget.uploaded_at.desc())
    ).all()
    
    # Historique
    historique = session.exec(
        select(HistoriqueBudget)
        .where(HistoriqueBudget.fiche_technique_id == fiche_id)
        .order_by(HistoriqueBudget.date_action.desc())
    ).all()
    
    # Référentiels
    programme = session.get(Programme, fiche.programme_id)
    direction = session.get(Direction, fiche.direction_id) if fiche.direction_id else None
    natures = {n.id: n for n in session.exec(select(NatureDepense)).all()}
    activites = {a.id: a for a in session.exec(select(Activite)).all()}
    
    return templates.TemplateResponse(
        "pages/budget_fiche_detail.html",
        get_template_context(
            request,
            fiche=fiche,
            lignes=lignes,
            documents=documents,
            historique=historique,
            programme=programme,
            direction=direction,
            natures=natures,
            activites=activites,
            current_user=current_user
        )
    )


# ============================================
# API - CRUD FICHES TECHNIQUES
# ============================================

@router.post("/api/fiches")
async def api_create_fiche(
    annee_budget: int = Form(...),
    programme_id: int = Form(...),
    direction_id: Optional[int] = Form(None),
    budget_anterieur: float = Form(0),
    enveloppe_demandee: float = Form(...),
    complement_demande: float = Form(0),
    engagement_etat: float = Form(0),
    financement_bailleurs: float = Form(0),
    note_justificative: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer une nouvelle fiche technique"""
    # Générer numéro de fiche
    count = session.exec(
        select(func.count(FicheTechnique.id))
        .where(FicheTechnique.annee_budget == annee_budget)
    ).one()
    
    prog = session.get(Programme, programme_id)
    numero_fiche = f"FT-{annee_budget}-{prog.code}-{count + 1:03d}"
    
    # Calculer le total
    budget_total = (
        Decimal(str(enveloppe_demandee)) +
        Decimal(str(complement_demande)) +
        Decimal(str(engagement_etat)) +
        Decimal(str(financement_bailleurs))
    )
    
    fiche = FicheTechnique(
        numero_fiche=numero_fiche,
        annee_budget=annee_budget,
        programme_id=programme_id,
        direction_id=direction_id,
        budget_anterieur=Decimal(str(budget_anterieur)),
        enveloppe_demandee=Decimal(str(enveloppe_demandee)),
        complement_demande=Decimal(str(complement_demande)),
        engagement_etat=Decimal(str(engagement_etat)),
        financement_bailleurs=Decimal(str(financement_bailleurs)),
        budget_total_demande=budget_total,
        note_justificative=note_justificative,
        created_by_user_id=current_user.id
    )
    
    session.add(fiche)
    session.commit()
    session.refresh(fiche)
    
    # Historique
    hist = HistoriqueBudget(
        fiche_technique_id=fiche.id,
        action="Création",
        nouveau_statut="Brouillon",
        montant_apres=budget_total,
        commentaire="Fiche technique créée",
        user_id=current_user.id
    )
    session.add(hist)
    session.commit()
    
    logger.info(f"✅ Fiche technique créée : {numero_fiche} par {current_user.email}")
    
    # Log activité
    ActivityService.log_user_activity(
        session=session,
        user=current_user,
        action_type="create",
        target_type="fiche_technique",
        description=f"Création de la fiche technique {numero_fiche} - Budget {annee_budget}",
        target_id=fiche.id,
        icon="📋"
    )
    
    return {"ok": True, "id": fiche.id, "numero": numero_fiche}


@router.delete("/api/fiches/{fiche_id}")
def api_delete_fiche(
    fiche_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une fiche technique et toute sa structure hiérarchique"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche non trouvée")
    
    try:
        # Supprimer dans l'ordre hiérarchique (du bas vers le haut)
        # 1. Supprimer les lignes budgétaires
        session.exec(
            delete(LigneBudgetaireDetail).where(LigneBudgetaireDetail.fiche_technique_id == fiche_id)
        )
        
        # 2. Supprimer les activités
        session.exec(
            delete(ActiviteBudgetaire).where(ActiviteBudgetaire.fiche_technique_id == fiche_id)
        )
        
        # 3. Supprimer les services
        session.exec(
            delete(ServiceBeneficiaire).where(ServiceBeneficiaire.fiche_technique_id == fiche_id)
        )
        
        # 4. Supprimer les actions
        session.exec(
            delete(ActionBudgetaire).where(ActionBudgetaire.fiche_technique_id == fiche_id)
        )
        
        # 5. Supprimer la fiche
        numero_fiche = fiche.numero_fiche
        session.delete(fiche)
        session.commit()
        
        logger.info(f"✅ Fiche {numero_fiche} supprimée par {current_user.email}")
        
        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="delete",
            target_type="fiche_technique",
            description=f"Suppression de la fiche technique {numero_fiche}",
            target_id=fiche_id,
            icon="🗑️"
        )
        
        return {"ok": True, "message": "Fiche supprimée avec succès"}
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression fiche {fiche_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


@router.post("/api/fiches/{fiche_id}/lignes")
def api_add_ligne(
    fiche_id: int,
    activite_id: Optional[int] = Form(None),
    nature_depense_id: int = Form(...),
    libelle: str = Form(...),
    budget_n_moins_1: float = Form(0),
    budget_demande: float = Form(...),
    justification: Optional[str] = Form(None),
    priorite: str = Form("Normale"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Ajouter une ligne budgétaire à une fiche"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche non trouvée")
    
    # Ordre = dernier + 1
    max_ordre = session.exec(
        select(func.max(LigneBudgetaire.ordre))
        .where(LigneBudgetaire.fiche_technique_id == fiche_id)
    ).one() or 0
    
    ligne = LigneBudgetaire(
        fiche_technique_id=fiche_id,
        activite_id=activite_id,
        nature_depense_id=nature_depense_id,
        libelle=libelle,
        budget_n_moins_1=Decimal(str(budget_n_moins_1)),
        budget_demande=Decimal(str(budget_demande)),
        justification=justification,
        priorite=priorite,
        ordre=max_ordre + 1
    )
    
    session.add(ligne)
    session.commit()
    
    logger.info(f"✅ Ligne budgétaire ajoutée à fiche {fiche_id}")
    return {"ok": True, "id": ligne.id}


@router.put("/api/fiches/{fiche_id}/lignes/{ligne_id}")
def api_update_ligne(
    fiche_id: int,
    ligne_id: int,
    libelle: Optional[str] = Form(None),
    budget_n_moins_1: Optional[float] = Form(None),
    budget_demande: Optional[float] = Form(None),
    budget_valide: Optional[float] = Form(None),
    justification: Optional[str] = Form(None),
    priorite: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier une ligne budgétaire"""
    ligne = session.get(LigneBudgetaire, ligne_id)
    if not ligne or ligne.fiche_technique_id != fiche_id:
        raise HTTPException(404, "Ligne non trouvée")
    
    if libelle: ligne.libelle = libelle
    if budget_n_moins_1 is not None: ligne.budget_n_moins_1 = Decimal(str(budget_n_moins_1))
    if budget_demande is not None: ligne.budget_demande = Decimal(str(budget_demande))
    if budget_valide is not None: ligne.budget_valide = Decimal(str(budget_valide))
    if justification: ligne.justification = justification
    if priorite: ligne.priorite = priorite
    
    ligne.updated_at = datetime.utcnow()
    session.add(ligne)
    session.commit()
    
    logger.info(f"✅ Ligne {ligne_id} mise à jour")
    return {"ok": True}


@router.delete("/api/fiches/{fiche_id}/lignes/{ligne_id}")
def api_delete_ligne(
    fiche_id: int,
    ligne_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une ligne budgétaire"""
    ligne = session.get(LigneBudgetaire, ligne_id)
    if not ligne or ligne.fiche_technique_id != fiche_id:
        raise HTTPException(404, "Ligne non trouvée")
    
    ligne.actif = False
    session.add(ligne)
    session.commit()
    
    logger.info(f"✅ Ligne {ligne_id} supprimée")
    return {"ok": True}


# ============================================
# UPLOAD DOCUMENTS
# ============================================

@router.get("/api/fiches/{fiche_id}/documents")
def api_get_documents_fiche(
    fiche_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupérer la liste des documents d'une fiche technique"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche non trouvée")
    
    documents = session.exec(
        select(DocumentBudget).where(DocumentBudget.fiche_technique_id == fiche_id)
    ).all()
    
    return {
        "ok": True,
        "documents": [
            {
                "id": doc.id,
                "nom_fichier": doc.nom_fichier,
                "filename": doc.nom_fichier,
                "description": doc.type_document,
                "taille_octets": doc.taille_octets,
                "created_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "date_upload": doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
            for doc in documents
        ]
    }


@router.post("/api/fiches/{fiche_id}/documents")
async def api_upload_document(
    fiche_id: int,
    fichier: UploadFile = File(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Uploader un document pour une fiche technique"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche non trouvée")
    
    # Créer le dossier
    docs_dir = Path(f"app/static/uploads/budget/fiches/{fiche_id}")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder le fichier
    file_path = docs_dir / fichier.filename
    content = await fichier.read()
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Enregistrer en BDD
    doc = DocumentBudget(
        fiche_technique_id=fiche_id,
        type_document=description or "Document général",
        nom_fichier=fichier.filename,
        file_path=f"/static/uploads/budget/fiches/{fiche_id}/{fichier.filename}",
        taille_octets=len(content),
        uploaded_by_user_id=current_user.id
    )
    
    session.add(doc)
    session.commit()
    
    logger.info(f"✅ Document uploadé : {fichier.filename} pour fiche {fiche_id}")
    return {"ok": True, "id": doc.id, "filename": fichier.filename}


@router.get("/api/fiches/{fiche_id}/documents/{document_id}/download")
def api_download_document_fiche(
    fiche_id: int,
    document_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Télécharger un document d'une fiche"""
    doc = session.get(DocumentBudget, document_id)
    if not doc or doc.fiche_technique_id != fiche_id:
        raise HTTPException(404, "Document non trouvé")
    
    file_path = Path(f"app{doc.file_path}")
    if not file_path.exists():
        raise HTTPException(404, "Fichier physique non trouvé")
    
    return FileResponse(
        path=file_path,
        filename=doc.nom_fichier,
        media_type='application/octet-stream'
    )


@router.delete("/api/fiches/{fiche_id}/documents/{document_id}")
def api_delete_document_fiche(
    fiche_id: int,
    document_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un document d'une fiche"""
    doc = session.get(DocumentBudget, document_id)
    if not doc or doc.fiche_technique_id != fiche_id:
        raise HTTPException(404, "Document non trouvé")
    
    try:
        # Supprimer le fichier physique
        file_path = Path(f"app{doc.file_path}")
        if file_path.exists():
            file_path.unlink()
            logger.info(f"📎 Fichier supprimé : {doc.nom_fichier}")
        
        # Supprimer de la BDD
        session.delete(doc)
        session.commit()
        
        logger.info(f"✅ Document {document_id} supprimé de la fiche {fiche_id}")
        return {"ok": True, "message": "Document supprimé avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression document {document_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


# ============================================
# CHANGEMENT DE STATUT
# ============================================

@router.put("/api/fiches/{fiche_id}/statut")
def api_changer_statut_fiche(
    fiche_id: int,
    nouveau_statut: str = Form(...),
    commentaire: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Changer le statut d'une fiche technique"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche technique non trouvée")
    
    # Valider le nouveau statut
    statuts_valides = ["Brouillon", "Soumis", "Validé", "Rejeté", "Approuvé"]
    if nouveau_statut not in statuts_valides:
        raise HTTPException(400, f"Statut invalide. Valeurs possibles : {', '.join(statuts_valides)}")
    
    try:
        ancien_statut = fiche.statut
        
        # Mettre à jour le statut
        fiche.statut = nouveau_statut
        fiche.updated_by_user_id = current_user.id
        
        # Mettre à jour les dates selon le statut
        from datetime import date
        if nouveau_statut == "Soumis" and not fiche.date_soumission:
            fiche.date_soumission = date.today()
        elif nouveau_statut in ["Validé", "Approuvé"] and not fiche.date_validation:
            fiche.date_validation = date.today()
        
        session.add(fiche)
        
        # Créer un historique du changement de statut
        historique = HistoriqueBudget(
            fiche_technique_id=fiche_id,
            action=f"Changement de statut: {ancien_statut} → {nouveau_statut}",
            ancien_statut=ancien_statut,
            nouveau_statut=nouveau_statut,
            commentaire=commentaire,
            user_id=current_user.id
        )
        session.add(historique)
        
        session.commit()
        
        logger.info(f"✅ Statut de la fiche {fiche_id} changé de '{ancien_statut}' à '{nouveau_statut}' par {current_user.email}")
        return {
            "ok": True,
            "message": f"Statut changé de '{ancien_statut}' à '{nouveau_statut}'",
            "ancien_statut": ancien_statut,
            "nouveau_statut": nouveau_statut
        }
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur changement statut fiche {fiche_id}: {e}")
        raise HTTPException(500, f"Erreur lors du changement de statut: {str(e)}")


# ============================================
# IMPORT EXCEL
# ============================================

@router.post("/api/import/activites")
async def api_import_activites_excel(
    fichier: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Importer des activités depuis un fichier Excel
    
    Format attendu:
    Code | Libelle | Programme | Direction | Nature | Description
    """
    try:
        # Lire le fichier Excel
        content = await fichier.read()
        df = pd.read_excel(io.BytesIO(content))
        
        # Vérifier les colonnes
        required_cols = ['Code', 'Libelle']
        if not all(col in df.columns for col in required_cols):
            raise HTTPException(400, f"Colonnes requises: {', '.join(required_cols)}")
        
        # Référentiels
        programmes = {p.code: p for p in session.exec(select(Programme)).all()}
        directions = {d.code: d for d in session.exec(select(Direction)).all()}
        natures = {n.code: n for n in session.exec(select(NatureDepense)).all()}
        
        count_created = 0
        count_updated = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                code = str(row['Code']).strip()
                libelle = str(row['Libelle']).strip()
                
                # Rechercher activité existante
                existing = session.exec(
                    select(Activite).where(Activite.code == code)
                ).first()
                
                # Programme, Direction, Nature (optionnels)
                prog_id = None
                if 'Programme' in row and pd.notna(row['Programme']):
                    prog_code = str(row['Programme']).strip()
                    if prog_code in programmes:
                        prog_id = programmes[prog_code].id
                
                dir_id = None
                if 'Direction' in row and pd.notna(row['Direction']):
                    dir_code = str(row['Direction']).strip()
                    if dir_code in directions:
                        dir_id = directions[dir_code].id
                
                nat_id = None
                if 'Nature' in row and pd.notna(row['Nature']):
                    nat_code = str(row['Nature']).strip()
                    if nat_code in natures:
                        nat_id = natures[nat_code].id
                
                desc = str(row['Description']) if 'Description' in row and pd.notna(row['Description']) else None
                
                if existing:
                    # Mise à jour
                    existing.libelle = libelle
                    existing.programme_id = prog_id
                    existing.direction_id = dir_id
                    existing.nature_depense_id = nat_id
                    existing.description = desc
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                    count_updated += 1
                else:
                    # Création
                    activite = Activite(
                        code=code,
                        libelle=libelle,
                        programme_id=prog_id,
                        direction_id=dir_id,
                        nature_depense_id=nat_id,
                        description=desc
                    )
                    session.add(activite)
                    count_created += 1
                    
            except Exception as e:
                errors.append(f"Ligne {idx + 2}: {str(e)}")
        
        session.commit()
        
        logger.info(f"✅ Import activités : {count_created} créées, {count_updated} mises à jour")
        
        return {
            "ok": True,
            "created": count_created,
            "updated": count_updated,
            "errors": errors
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur import Excel: {e}")
        raise HTTPException(500, f"Erreur lors de l'import: {str(e)}")


# ============================================
# EXPORT PDF
# ============================================

@router.get("/api/fiches/{fiche_id}/export/pdf")
def api_export_fiche_pdf(
    fiche_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Exporter une fiche technique en PDF avec ReportLab
    Génère un vrai PDF professionnel et téléchargeable
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from app.core.config import settings
    except ImportError:
        raise HTTPException(500, "ReportLab n'est pas installé. Exécutez: pip install reportlab")
    
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche technique non trouvée")
    
    # Récupérer la structure hiérarchique
    actions = session.exec(
        select(ActionBudgetaire)
        .where(ActionBudgetaire.fiche_technique_id == fiche_id)
        .order_by(ActionBudgetaire.ordre)
    ).all()
    
    for action in actions:
        services = session.exec(
            select(ServiceBeneficiaire)
            .where(ServiceBeneficiaire.action_id == action.id)
            .order_by(ServiceBeneficiaire.ordre)
        ).all()
        object.__setattr__(action, 'services', services)
        
        for service in services:
            activites = session.exec(
                select(ActiviteBudgetaire)
                .where(ActiviteBudgetaire.service_beneficiaire_id == service.id)
                .order_by(ActiviteBudgetaire.ordre)
            ).all()
            object.__setattr__(service, 'activites', activites)
            
            for activite in activites:
                lignes = session.exec(
                    select(LigneBudgetaireDetail)
                    .where(LigneBudgetaireDetail.activite_id == activite.id)
                    .order_by(LigneBudgetaireDetail.ordre)
                ).all()
                object.__setattr__(activite, 'lignes', lignes)
    
    from collections import defaultdict
    actions_par_nature = defaultdict(list)
    for action in actions:
        nature = action.nature_depense or "BIENS ET SERVICES"
        actions_par_nature[nature].append(action)
    
    programme = session.get(Programme, fiche.programme_id)
    
    # Fonction pour ajouter en-tête et pied de page
    def add_page_number(canvas, doc):
        """Ajouter en-tête et pied de page sur chaque page"""
        canvas.saveState()
        
        # En-tête sur chaque page
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(colors.HexColor('#2c3e50'))
        canvas.drawCentredString(
            landscape(A4)[0] / 2, 
            landscape(A4)[1] - 1.2*cm, 
            f"{fiche.numero_fiche} | Budget {fiche.annee_budget} | {programme.libelle[:50]}"
        )
        
        # Ligne de séparation en-tête
        canvas.setStrokeColor(colors.HexColor('#667eea'))
        canvas.setLineWidth(1)
        canvas.line(1*cm, landscape(A4)[1] - 1.5*cm, landscape(A4)[0] - 1*cm, landscape(A4)[1] - 1.5*cm)
        
        # Pied de page avec numéro de page
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        
        # Gauche : Date et utilisateur
        canvas.drawString(
            0.5*cm, 
            0.5*cm, 
            f"Édité le {fiche.created_at.strftime('%d/%m/%Y')} par {current_user.email}"
        )
        
        # Centre : Numéro de page
        canvas.drawCentredString(
            landscape(A4)[0] / 2,
            0.5*cm,
            f"Page {page_num}"
        )
        
        # Droite : Application
        canvas.drawRightString(
            landscape(A4)[0] - 0.5*cm,
            0.5*cm,
            settings.APP_NAME
        )
        
        # Ligne de séparation pied de page
        canvas.setStrokeColor(colors.HexColor('#667eea'))
        canvas.setLineWidth(1)
        canvas.line(0.5*cm, 0.8*cm, landscape(A4)[0] - 0.5*cm, 0.8*cm)
        
        canvas.restoreState()
    
    # Créer le PDF avec marges réduites
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm,
        title=f"Fiche Technique {fiche.numero_fiche}",
        author=current_user.email,
        subject=f"Budget {fiche.annee_budget} - {programme.libelle}"
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Style pour le titre
    titre_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Style pour les infos
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    # Construire le document
    elements = []
    
    # En-tête
    elements.append(Paragraph("📋 FICHE TECHNIQUE BUDGÉTAIRE HIÉRARCHIQUE", titre_style))
    elements.append(Paragraph(f"<b>{fiche.numero_fiche}</b> | Budget {fiche.annee_budget} | {fiche.statut}", info_style))
    elements.append(Paragraph(f"{programme.libelle} ({programme.code})", info_style))
    elements.append(Paragraph(f"<b>Budget Total :</b> {fiche.budget_total_demande:,.0f} FCFA", info_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Construire les données du tableau
    table_data = []
    
    # En-têtes
    headers = [
        'CODE ET LIBELLE',
        'BUDGET\nVOTÉ N\n(A)',
        'BUDGET\nACTUEL N\n(B)',
        'ENVELOPPE\nN+1\n(C)',
        'COMPLÉMENT\nSOLLICITÉ\n(D)',
        'BUDGET\nSOUHAITÉ\n(E=C+D)',
        'ENGAGEMENT\nÉTAT\n(F)',
        'AUTRE\nCOMPLÉMENT\n(G)',
        'PROJET\nBUDGET N+1\n(H=C+F+G)'
    ]
    table_data.append(headers)
    
    # Parcourir la hiérarchie
    for nature, actions_nature in actions_par_nature.items():
        # Header Nature avec fusion de colonnes (SPAN)
        nature_row = [nature.upper(), '', '', '', '', '', '', '', '']
        table_data.append(nature_row)
        
        for action in actions_nature:
            # Action avec texte qui peut se retourner à la ligne
            action_text = Paragraph(action.libelle.replace('- ', '').strip(), 
                                  ParagraphStyle('ActionText', fontSize=6, leftIndent=0))
            table_data.append([
                action_text,
                f"{action.budget_vote_n:,.0f}",
                f"{action.budget_actuel_n:,.0f}",
                f"{action.enveloppe_n_plus_1:,.0f}",
                f"{action.complement_solicite:,.0f}",
                f"{action.budget_souhaite:,.0f}",
                f"{action.engagement_etat:,.0f}",
                f"{action.autre_complement:,.0f}",
                f"{action.projet_budget_n_plus_1:,.0f}"
            ])
            
            for service in action.services:
                # Service avec fusion de colonnes et texte à gauche
                service_text = Paragraph(f"  {service.libelle.replace('- ', '').strip()}", 
                                       ParagraphStyle('ServiceText', fontSize=6, leftIndent=0.2*cm, alignment=TA_LEFT))
                service_row = [service_text, '', '', '', '', '', '', '', '']
                table_data.append(service_row)
                
                for activite in service.activites:
                    # Activité avec texte qui peut se retourner à la ligne
                    activite_text = Paragraph(f"    {activite.libelle.replace('- ', '').strip()}", 
                                            ParagraphStyle('ActiviteText', fontSize=6, leftIndent=0.4*cm))
                    table_data.append([
                        activite_text,
                        f"{activite.budget_vote_n:,.0f}",
                        f"{activite.budget_actuel_n:,.0f}",
                        f"{activite.enveloppe_n_plus_1:,.0f}",
                        f"{activite.complement_solicite:,.0f}",
                        f"{activite.budget_souhaite:,.0f}",
                        f"{activite.engagement_etat:,.0f}",
                        f"{activite.autre_complement:,.0f}",
                        f"{activite.projet_budget_n_plus_1:,.0f}"
                    ])
                    
                    # Lignes budgétaires avec texte qui peut se retourner à la ligne
                    for ligne in activite.lignes:
                        ligne_text = Paragraph(f"      {ligne.code} - {ligne.libelle}", 
                                             ParagraphStyle('LigneText', fontSize=6, leftIndent=0.6*cm))
                        table_data.append([
                            ligne_text,
                            f"{ligne.budget_vote_n:,.0f}",
                            f"{ligne.budget_actuel_n:,.0f}",
                            f"{ligne.enveloppe_n_plus_1:,.0f}",
                            f"{ligne.complement_solicite:,.0f}",
                            f"{ligne.budget_souhaite:,.0f}",
                            f"{ligne.engagement_etat:,.0f}",
                            f"{ligne.autre_complement:,.0f}",
                            f"{ligne.projet_budget_n_plus_1:,.0f}"
                        ])
                    
                    # Sous-total Activité avec police adaptée aux grandes valeurs
                    sous_total_activite = [
                        'SOUS-TOTAL ACTIVITÉ',
                        f"{activite.budget_vote_n:,.0f}",
                        f"{activite.budget_actuel_n:,.0f}",
                        f"{activite.enveloppe_n_plus_1:,.0f}",
                        f"{activite.complement_solicite:,.0f}",
                        f"{activite.budget_souhaite:,.0f}",
                        f"{activite.engagement_etat:,.0f}",
                        f"{activite.autre_complement:,.0f}",
                        f"{activite.projet_budget_n_plus_1:,.0f}"
                    ]
                    table_data.append(sous_total_activite)
                
                # Sous-total Service avec police adaptée aux grandes valeurs
                service_totals = {
                    'vote': sum(a.budget_vote_n for a in service.activites),
                    'actuel': sum(a.budget_actuel_n for a in service.activites),
                    'enveloppe': sum(a.enveloppe_n_plus_1 for a in service.activites),
                    'complement': sum(a.complement_solicite for a in service.activites),
                    'souhaite': sum(a.budget_souhaite for a in service.activites),
                    'engagement': sum(a.engagement_etat for a in service.activites),
                    'autre': sum(a.autre_complement for a in service.activites),
                    'projet': sum(a.projet_budget_n_plus_1 for a in service.activites)
                }
                sous_total_service = [
                    'SOUS-TOTAL SERVICE',
                    f"{service_totals['vote']:,.0f}",
                    f"{service_totals['actuel']:,.0f}",
                    f"{service_totals['enveloppe']:,.0f}",
                    f"{service_totals['complement']:,.0f}",
                    f"{service_totals['souhaite']:,.0f}",
                    f"{service_totals['engagement']:,.0f}",
                    f"{service_totals['autre']:,.0f}",
                    f"{service_totals['projet']:,.0f}"
                ]
                table_data.append(sous_total_service)
            
            # Sous-total Action
            table_data.append([
                'SOUS-TOTAL ACTION',
                f"{action.budget_vote_n:,.0f}",
                f"{action.budget_actuel_n:,.0f}",
                f"{action.enveloppe_n_plus_1:,.0f}",
                f"{action.complement_solicite:,.0f}",
                f"{action.budget_souhaite:,.0f}",
                f"{action.engagement_etat:,.0f}",
                f"{action.autre_complement:,.0f}",
                f"{action.projet_budget_n_plus_1:,.0f}"
            ])
        
        # Total Nature avec police adaptée aux grandes valeurs
        nature_totals = {
            'vote': sum(a.budget_vote_n for a in actions_nature),
            'actuel': sum(a.budget_actuel_n for a in actions_nature),
            'enveloppe': sum(a.enveloppe_n_plus_1 for a in actions_nature),
            'complement': sum(a.complement_solicite for a in actions_nature),
            'souhaite': sum(a.budget_souhaite for a in actions_nature),
            'engagement': sum(a.engagement_etat for a in actions_nature),
            'autre': sum(a.autre_complement for a in actions_nature),
            'projet': sum(a.projet_budget_n_plus_1 for a in actions_nature)
        }
        total_nature = [
            f'TOTAL {nature.upper()}',
            f"{nature_totals['vote']:,.0f}",
            f"{nature_totals['actuel']:,.0f}",
            f"{nature_totals['enveloppe']:,.0f}",
            f"{nature_totals['complement']:,.0f}",
            f"{nature_totals['souhaite']:,.0f}",
            f"{nature_totals['engagement']:,.0f}",
            f"{nature_totals['autre']:,.0f}",
            f"{nature_totals['projet']:,.0f}"
        ]
        table_data.append(total_nature)
    
    # Total Général avec police adaptée aux grandes valeurs
    total_general = {
        'vote': sum(sum(a.budget_vote_n for a in acts) for acts in actions_par_nature.values()),
        'actuel': sum(sum(a.budget_actuel_n for a in acts) for acts in actions_par_nature.values()),
        'enveloppe': sum(sum(a.enveloppe_n_plus_1 for a in acts) for acts in actions_par_nature.values()),
        'complement': sum(sum(a.complement_solicite for a in acts) for acts in actions_par_nature.values()),
        'souhaite': sum(sum(a.budget_souhaite for a in acts) for acts in actions_par_nature.values()),
        'engagement': sum(sum(a.engagement_etat for a in acts) for acts in actions_par_nature.values()),
        'autre': sum(sum(a.autre_complement for a in acts) for acts in actions_par_nature.values()),
        'projet': sum(sum(a.projet_budget_n_plus_1 for a in acts) for acts in actions_par_nature.values())
    }
    total_general_row = [
        'TOTAL GÉNÉRAL',
        f"{total_general['vote']:,.0f}",
        f"{total_general['actuel']:,.0f}",
        f"{total_general['enveloppe']:,.0f}",
        f"{total_general['complement']:,.0f}",
        f"{total_general['souhaite']:,.0f}",
        f"{total_general['engagement']:,.0f}",
        f"{total_general['autre']:,.0f}",
        f"{total_general['projet']:,.0f}"
    ]
    table_data.append(total_general_row)
    
    # Créer le tableau avec largeurs optimisées - colonne texte réduite
    col_widths = [7*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 3*cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Styles du tableau
    table_style = TableStyle([
        # En-têtes
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef8d4b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Toutes les colonnes centrées horizontalement
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        
        # Bordures
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        
        # Police générale avec taille réduite
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Centrage vertical pour toutes les cellules
        
        # Padding réduit pour économiser l'espace
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ])
    
    # Appliquer les couleurs selon le type de ligne
    row_index = 1  # Commencer après les headers
    for nature, actions_nature in actions_par_nature.items():
        # Header Nature (jaune or) avec fusion de colonnes
        table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#ffd700'))
        table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
        table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 8)
        table_style.add('ALIGN', (0, row_index), (-1, row_index), 'CENTER')
        table_style.add('SPAN', (0, row_index), (-1, row_index))  # Fusionner toutes les colonnes
        row_index += 1
        
        for action in actions_nature:
            # Action (bleu)
            table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#9bc2e6'))
            table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
            table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 8)
            row_index += 1
            
            for service in action.services:
                # Service (jaune) avec fusion de colonnes et texte à gauche
                table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#ffc000'))
                table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
                table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 6)  # Police hiérarchique
                table_style.add('ALIGN', (0, row_index), (-1, row_index), 'LEFT')  # Texte à gauche
                table_style.add('SPAN', (0, row_index), (-1, row_index))  # Fusionner toutes les colonnes
                row_index += 1
                
                for activite in service.activites:
                    # Activité (vert)
                    table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#92d050'))
                    table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
                    row_index += 1
                    
                    # Lignes (blanc)
                    for ligne in activite.lignes:
                        table_style.add('FONTSIZE', (0, row_index), (0, row_index), 6)
                        row_index += 1
                    
                    # Sous-total Activité (vert clair) avec police hiérarchique
                    table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#d4edda'))
                    table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
                    table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 6)  # Police hiérarchique
                    table_style.add('ALIGN', (0, row_index), (0, row_index), 'RIGHT')
                    row_index += 1
                
                # Sous-total Service (jaune clair) avec police hiérarchique
                table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#fff3cd'))
                table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
                table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 7)  # Police hiérarchique
                table_style.add('ALIGN', (0, row_index), (0, row_index), 'RIGHT')
                row_index += 1
            
            # Sous-total Action (bleu clair) avec police hiérarchique
            table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#cce5ff'))
            table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
            table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 8)  # Police hiérarchique
            table_style.add('ALIGN', (0, row_index), (0, row_index), 'RIGHT')
            row_index += 1
        
        # Total Nature (or) avec police hiérarchique
        table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#ffd700'))
        table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
        table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 9)  # Police hiérarchique
        table_style.add('ALIGN', (0, row_index), (0, row_index), 'RIGHT')
        row_index += 1
    
    # Total Général (rouge) avec police hiérarchique maximale
    table_style.add('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#dc3545'))
    table_style.add('TEXTCOLOR', (0, row_index), (-1, row_index), colors.white)
    table_style.add('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold')
    table_style.add('FONTSIZE', (0, row_index), (-1, row_index), 10)  # Police hiérarchique maximale
    table_style.add('ALIGN', (0, row_index), (0, row_index), 'RIGHT')
    
    table.setStyle(table_style)
    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 0.5*cm))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, textColor=colors.grey)
    elements.append(Paragraph(f"Document édité le : {fiche.created_at.strftime('%d/%m/%Y à %H:%M')}", footer_style))
    elements.append(Paragraph(f"Phase : {fiche.phase} | Statut : {fiche.statut}", footer_style))
    elements.append(Paragraph(settings.APP_NAME, footer_style))
    
    # Générer le PDF avec en-tête et pied de page
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    # Retourner le PDF
    buffer.seek(0)
    
    logger.info(f"✅ PDF ReportLab généré pour fiche {fiche.numero_fiche}")
    
    # Nettoyer le nom du programme pour le nom de fichier
    programme_nom_clean = programme.libelle.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Fiche_{programme_nom_clean}_{fiche.annee_budget}_{fiche.numero_fiche}.pdf"
        }
    )


# ============================================
# FICHES TECHNIQUES HIÉRARCHIQUES
# ============================================

@router.get("/fiches/{fiche_id}/structure", response_class=HTMLResponse, name="budget_fiche_structure")
def budget_fiche_structure(
    fiche_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Afficher la structure hiérarchique d'une fiche technique"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche technique non trouvée")
    
    # Recalculer les totaux pour s'assurer que tout est à jour
    _recalculer_totaux_hierarchie(fiche_id, session)
    
    # Recharger la fiche après recalcul
    session.expire(fiche)
    fiche = session.get(FicheTechnique, fiche_id)
    
    # Récupérer la structure hiérarchique
    actions = session.exec(
        select(ActionBudgetaire)
        .where(ActionBudgetaire.fiche_technique_id == fiche_id)
        .order_by(ActionBudgetaire.ordre)
    ).all()
    
    # Charger les services pour chaque action
    for action in actions:
        services = session.exec(
            select(ServiceBeneficiaire)
            .where(ServiceBeneficiaire.action_id == action.id)
            .order_by(ServiceBeneficiaire.ordre)
        ).all()
        object.__setattr__(action, 'services', services)
        
        # Charger les activités pour chaque service
        for service in services:
            activites = session.exec(
                select(ActiviteBudgetaire)
                .where(ActiviteBudgetaire.service_beneficiaire_id == service.id)
                .order_by(ActiviteBudgetaire.ordre)
            ).all()
            object.__setattr__(service, 'activites', activites)
            
            # Charger les lignes pour chaque activité
            for activite in activites:
                lignes = session.exec(
                    select(LigneBudgetaireDetail)
                    .where(LigneBudgetaireDetail.activite_id == activite.id)
                    .order_by(LigneBudgetaireDetail.ordre)
                ).all()
                object.__setattr__(activite, 'lignes', lignes)
    
    # Grouper les actions par nature de dépense
    from collections import defaultdict
    actions_par_nature = defaultdict(list)
    for action in actions:
        nature = action.nature_depense or "BIENS ET SERVICES"
        actions_par_nature[nature].append(action)
    
    # Référentiels
    programme = session.get(Programme, fiche.programme_id)
    direction = session.get(Direction, fiche.direction_id) if fiche.direction_id else None
    
    return templates.TemplateResponse(
        "pages/budget_fiche_structure.html",
        get_template_context(
            request,
            fiche=fiche,
            actions=actions,
            actions_par_nature=dict(actions_par_nature),
            programme=programme,
            direction=direction,
            current_user=current_user
        )
    )


@router.post("/api/charger-fiche")
async def api_charger_fiche(
    fichier: UploadFile = File(...),
    programme_id: int = Form(...),
    nom_fiche: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Charger et analyser une fiche technique depuis un fichier Excel/PDF
    """
    try:
        # Vérifier que le programme existe
        programme = session.get(Programme, programme_id)
        if not programme:
            raise HTTPException(400, "Programme non trouvé")
        
        # Lire le fichier
        content = await fichier.read()
        
        # Déterminer le type de fichier
        if fichier.filename.endswith('.pdf'):
            return await _analyser_fiche_pdf(content, nom_fiche, programme_id, session, current_user)
        elif fichier.filename.endswith(('.xlsx', '.xls')):
            return await _analyser_fiche_excel(content, nom_fiche, programme_id, session, current_user)
        else:
            raise HTTPException(400, "Format de fichier non supporté. Utilisez Excel (.xlsx, .xls) ou PDF (.pdf)")
            
    except Exception as e:
        logger.error(f"Erreur chargement fiche: {e}")
        raise HTTPException(500, f"Erreur lors du chargement: {str(e)}")


async def _analyser_fiche_excel(content: bytes, nom_fiche: Optional[str], programme_id: int, session: Session, current_user: User):
    """Analyser un fichier Excel de fiche technique"""
    try:
        # Lire le fichier Excel
        df = pd.read_excel(io.BytesIO(content))
        
        # Analyser la structure du fichier
        structure = _detecter_structure_excel(df)
        
        # Créer la fiche technique
        fiche = _creer_fiche_technique(structure, nom_fiche, programme_id, session, current_user)
        
        # Créer la structure hiérarchique
        result = _creer_structure_hierarchique(df, structure, fiche.id, session)
        
        logger.info(f"✅ Fiche technique chargée : {fiche.numero_fiche}")
        
        return {
            "ok": True,
            "fiche_numero": fiche.numero_fiche,
            "actions_count": result["actions_count"],
            "services_count": result["services_count"],
            "activites_count": result["activites_count"],
            "lignes_count": result["lignes_count"],
            "budget_total": float(result["budget_total"]),
            "errors": result["errors"]
        }
        
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Erreur analyse Excel: {str(e)}")


async def _analyser_fiche_pdf(content: bytes, nom_fiche: Optional[str], programme_id: int, session: Session, current_user: User):
    """Analyser un fichier PDF de fiche technique"""
    # Pour l'instant, on simule l'analyse PDF
    # Dans une vraie implémentation, on utiliserait PyPDF2 ou pdfplumber
    
    # Créer une fiche technique basique
    fiche = _creer_fiche_technique({
        "annee": 2025,
        "programme": "P01",
        "direction": "D01"
    }, nom_fiche, programme_id, session, current_user)
    
    return {
        "ok": True,
        "fiche_numero": fiche.numero_fiche,
        "actions_count": 0,
        "services_count": 0,
        "activites_count": 0,
        "lignes_count": 0,
        "budget_total": 0.0,
        "errors": ["Analyse PDF non encore implémentée - Fiche créée sans structure"]
    }


def _detecter_structure_excel(df: pd.DataFrame) -> dict:
    """Détecter la structure du fichier Excel avec années réelles"""
    import re
    
    structure = {
        "colonnes": {},
        "annee": 2025,
        "programme": "P01",
        "direction": "D01"
    }
    
    # Nettoyer les noms de colonnes (enlever \n et espaces superflus)
    df.columns = [str(col).replace('\n', ' ').strip() for col in df.columns]
    
    # Détecter les années dans les colonnes
    annees_detectees = set()
    for col in df.columns:
        col_str = str(col).upper()
        # Rechercher des années (2020-2030)
        annees = re.findall(r'20[2-3][0-9]', col_str)
        annees_detectees.update(annees)
    
    # Trier les années pour identifier N et N+1
    annees_triees = sorted(annees_detectees)
    annee_n = annees_triees[0] if len(annees_triees) > 0 else "2024"
    annee_n_plus_1 = annees_triees[1] if len(annees_triees) > 1 else "2025"
    
    # Patterns de colonnes avec années dynamiques (plus flexibles)
    colonnes_patterns = [
        (("CODE", "LIBELLE"), "code_libelle"),
        (("BUDGET", "VOTE", annee_n), "budget_vote_n"),  # Sans accent
        (("BUDGET", "ACTUEL", annee_n), "budget_actuel_n"),
        (("ENVELOPPE", annee_n_plus_1), "enveloppe_n_plus_1"),
        (("COMPLEMENT", "SOLLICITE"), "complement_solicite"),  # Sans accent
        (("BUDGET", "SOUHAITE"), "budget_souhaite"),  # Sans accent
        (("ENGAGEMENT", "ETAT"), "engagement_etat"),  # Sans accent
        (("AUTRE", "COMPLEMENT"), "autre_complement"),
        (("PROJET", "BUDGE", annee_n_plus_1), "projet_budget_n_plus_1"),  # "BUDGE" car "PROJET DE BUDGE"
        (("JUSTIFICATIFS",), "justificatifs"),
    ]
    
    # Détecter les colonnes
    for col in df.columns:
        col_upper = str(col).upper().replace('É', 'E').replace('È', 'E').replace('Ê', 'E')  # Enlever accents
        for patterns, field in colonnes_patterns:
            if all(p in col_upper for p in patterns):
                structure["colonnes"][field] = col
                break
    
    # Mettre à jour l'année du budget
    if annee_n_plus_1:
        structure["annee"] = int(annee_n_plus_1)
    
    return structure


def _creer_fiche_technique(structure: dict, nom_fiche: Optional[str], programme_id: int, session: Session, current_user: User) -> FicheTechnique:
    """Créer une nouvelle fiche technique"""
    # Générer numéro de fiche
    annee = structure.get("annee", 2025)
    count = session.exec(
        select(func.count(FicheTechnique.id))
        .where(FicheTechnique.annee_budget == annee)
    ).one()
    
    # Récupérer le programme sélectionné
    programme = session.get(Programme, programme_id)
    if not programme:
        raise HTTPException(400, "Programme non trouvé")
    
    numero_fiche = f"FT-{annee}-{programme.code}-{count + 1:03d}"
    
    fiche = FicheTechnique(
        numero_fiche=numero_fiche,
        annee_budget=annee,
        programme_id=programme.id,
        direction_id=None,  # À déterminer selon le contenu
        budget_total_demande=Decimal("0"),
        statut="Brouillon",
        phase="Conférence interne",
        created_by_user_id=current_user.id
    )
    
    session.add(fiche)
    session.commit()
    session.refresh(fiche)
    
    return fiche


def _creer_structure_hierarchique(df: pd.DataFrame, structure: dict, fiche_id: int, session: Session) -> dict:
    """Créer la structure hiérarchique à partir des données Excel"""
    actions_count = 0
    services_count = 0
    activites_count = 0
    lignes_count = 0
    budget_total = Decimal("0")
    errors = []
    
    current_nature = None
    current_action = None
    current_service = None
    current_activite = None
    
    logger.info(f"📊 Import de {len(df)} lignes depuis Excel...")
    
    for idx, row in df.iterrows():
        try:
            # Détecter le niveau hiérarchique
            code_libelle_col = structure["colonnes"].get("code_libelle")
            if not code_libelle_col or code_libelle_col not in row:
                continue
                
            code_libelle = str(row[code_libelle_col]).strip()
            if not code_libelle or code_libelle == "nan":
                continue
            
            logger.debug(f"Ligne {idx+1}: {code_libelle[:80]}")
            
            # Détecter le type de ligne
            # Nature de dépenses : doit être exactement l'une de ces valeurs (pas de chiffre au début)
            if (code_libelle.upper() in ["BIENS ET SERVICES", "PERSONNEL", "INVESTISSEMENT", "INVESTISSEMENTS", "TRANSFERTS", "4 - INVESTISSEMENTS"] or
                code_libelle.upper().startswith("TOTAL ")):
                # C'est une nature de dépenses ou un total - on réinitialise la hiérarchie
                if not code_libelle.upper().startswith("TOTAL "):
                    current_nature = code_libelle
                    logger.info(f"📌 Nouvelle nature de dépense: {current_nature}")
                current_action = None
                current_service = None
                current_activite = None
                
            elif code_libelle.strip().startswith("Action :") or code_libelle.strip().startswith("- Action :"):
                current_action = _creer_action(row, structure, fiche_id, current_nature, session)
                actions_count += 1
                current_service = None
                current_activite = None
                logger.debug(f"  → ACTION créée ({current_nature}): {code_libelle[:60]}")
                
            elif code_libelle.strip().startswith("Service Bénéficiaire :") or code_libelle.strip().startswith("- Service Bénéficiaire :"):
                if current_action:
                    current_service = _creer_service(row, structure, fiche_id, current_action.id, session)
                    services_count += 1
                    current_activite = None
                    logger.debug(f"    → SERVICE créé: {code_libelle[:60]}")
                else:
                    logger.warning(f"⚠️  Service sans action (ligne {idx+1}): {code_libelle[:60]}")
                
            elif code_libelle.strip().startswith("Activité :") or code_libelle.strip().startswith("- Activité :"):
                if current_service:
                    current_activite = _creer_activite(row, structure, fiche_id, current_service.id, session)
                    activites_count += 1
                    logger.debug(f"      → ACTIVITÉ créée: {code_libelle[:60]}")
                else:
                    logger.warning(f"⚠️  Activité sans service (ligne {idx+1}): {code_libelle[:60]}")
                    
            elif code_libelle.strip() and code_libelle.strip()[0].isdigit():
                # C'est une ligne budgétaire (commence par un numéro de compte)
                if current_activite:
                    ligne = _creer_ligne(row, structure, fiche_id, current_activite.id, session)
                    lignes_count += 1
                    budget_total += ligne.budget_souhaite
                    logger.debug(f"        → LIGNE créée: {code_libelle[:60]}")
                else:
                    logger.warning(f"⚠️  Ligne sans activité (ligne {idx+1}): {code_libelle[:60]}")
                    
        except Exception as e:
            errors.append(f"Ligne {idx + 2}: {str(e)}")
    
    logger.info(f"📊 Résumé import: {actions_count} actions, {services_count} services, {activites_count} activités, {lignes_count} lignes")
    
    # Recalculer tous les totaux de la hiérarchie
    _recalculer_totaux_hierarchie(fiche_id, session)
    
    # Mettre à jour le budget total de la fiche
    fiche = session.get(FicheTechnique, fiche_id)
    if fiche:
        fiche.budget_total_demande = budget_total
        session.add(fiche)
        session.commit()
    
    logger.info(f"✅ Import terminé: Budget total = {budget_total}")
    
    return {
        "actions_count": actions_count,
        "services_count": services_count,
        "activites_count": activites_count,
        "lignes_count": lignes_count,
        "budget_total": budget_total,
        "errors": errors
    }


def _creer_action(row, structure: dict, fiche_id: int, nature_depense: Optional[str], session: Session) -> ActionBudgetaire:
    """Créer une action budgétaire"""
    code_libelle_col = structure["colonnes"]["code_libelle"]
    libelle = str(row[code_libelle_col]).strip()
    
    # Extraire le code
    code = libelle.split()[1] if len(libelle.split()) > 1 else f"ACT_{len(session.exec(select(ActionBudgetaire)).all()) + 1}"
    
    action = ActionBudgetaire(
        fiche_technique_id=fiche_id,
        nature_depense=nature_depense,
        code=code,
        libelle=libelle,
        budget_vote_n=Decimal("0"),
        budget_actuel_n=Decimal("0"),
        enveloppe_n_plus_1=Decimal("0"),
        complement_solicite=Decimal("0"),
        budget_souhaite=Decimal("0"),
        engagement_etat=Decimal("0"),
        autre_complement=Decimal("0"),
        projet_budget_n_plus_1=Decimal("0"),
        justificatifs=None
    )
    
    session.add(action)
    session.commit()
    session.refresh(action)
    return action


def _creer_service(row, structure: dict, fiche_id: int, action_id: int, session: Session) -> ServiceBeneficiaire:
    """Créer un service bénéficiaire"""
    code_libelle_col = structure["colonnes"]["code_libelle"]
    libelle = str(row[code_libelle_col]).strip()
    
    # Extraire le code
    code = libelle.split(":")[1].strip().replace(" ", "_") if ":" in libelle else f"SRV_{len(session.exec(select(ServiceBeneficiaire)).all()) + 1}"
    
    service = ServiceBeneficiaire(
        fiche_technique_id=fiche_id,
        action_id=action_id,
        code=code,
        libelle=libelle
    )
    
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


def _creer_activite(row, structure: dict, fiche_id: int, service_id: int, session: Session) -> ActiviteBudgetaire:
    """Créer une activité budgétaire"""
    code_libelle_col = structure["colonnes"]["code_libelle"]
    libelle = str(row[code_libelle_col]).strip()
    
    # Extraire le code
    code = libelle.split()[1] if len(libelle.split()) > 1 else f"ACT_{len(session.exec(select(ActiviteBudgetaire)).all()) + 1}"
    
    activite = ActiviteBudgetaire(
        fiche_technique_id=fiche_id,
        service_beneficiaire_id=service_id,
        code=code,
        libelle=libelle,
        budget_vote_n=Decimal("0"),
        budget_actuel_n=Decimal("0"),
        enveloppe_n_plus_1=Decimal("0"),
        complement_solicite=Decimal("0"),
        budget_souhaite=Decimal("0"),
        engagement_etat=Decimal("0"),
        autre_complement=Decimal("0"),
        projet_budget_n_plus_1=Decimal("0"),
        justificatifs=None
    )
    
    session.add(activite)
    session.commit()
    session.refresh(activite)
    return activite


def _recalculer_totaux_hierarchie(fiche_id: int, session: Session):
    """Recalculer tous les totaux de la hiérarchie (des lignes vers le haut)"""
    
    # 1. Recalculer les totaux des Activités (somme de leurs lignes)
    activites = session.exec(
        select(ActiviteBudgetaire).where(ActiviteBudgetaire.fiche_technique_id == fiche_id)
    ).all()
    
    for activite in activites:
        lignes = session.exec(
            select(LigneBudgetaireDetail).where(LigneBudgetaireDetail.activite_id == activite.id)
        ).all()
        
        activite.budget_vote_n = sum(l.budget_vote_n for l in lignes)
        activite.budget_actuel_n = sum(l.budget_actuel_n for l in lignes)
        activite.enveloppe_n_plus_1 = sum(l.enveloppe_n_plus_1 for l in lignes)
        activite.complement_solicite = sum(l.complement_solicite for l in lignes)
        activite.budget_souhaite = sum(l.budget_souhaite for l in lignes)
        activite.engagement_etat = sum(l.engagement_etat for l in lignes)
        activite.autre_complement = sum(l.autre_complement for l in lignes)
        activite.projet_budget_n_plus_1 = sum(l.projet_budget_n_plus_1 for l in lignes)
        session.add(activite)
    
    session.commit()
    
    # 2. Recalculer les totaux des Actions (somme de leurs activités)
    actions = session.exec(
        select(ActionBudgetaire).where(ActionBudgetaire.fiche_technique_id == fiche_id)
    ).all()
    
    for action in actions:
        activites_action = session.exec(
            select(ActiviteBudgetaire)
            .join(ServiceBeneficiaire)
            .where(ServiceBeneficiaire.action_id == action.id)
        ).all()
        
        action.budget_vote_n = sum(a.budget_vote_n for a in activites_action)
        action.budget_actuel_n = sum(a.budget_actuel_n for a in activites_action)
        action.enveloppe_n_plus_1 = sum(a.enveloppe_n_plus_1 for a in activites_action)
        action.complement_solicite = sum(a.complement_solicite for a in activites_action)
        action.budget_souhaite = sum(a.budget_souhaite for a in activites_action)
        action.engagement_etat = sum(a.engagement_etat for a in activites_action)
        action.autre_complement = sum(a.autre_complement for a in activites_action)
        action.projet_budget_n_plus_1 = sum(a.projet_budget_n_plus_1 for a in activites_action)
        session.add(action)
    
    session.commit()
    
    # 3. Mettre à jour le budget total de la fiche
    # Rafraîchir les actions depuis la DB pour avoir les valeurs à jour
    session.expire_all()  # Force le rafraîchissement de tous les objets
    
    actions_fresh = session.exec(
        select(ActionBudgetaire).where(ActionBudgetaire.fiche_technique_id == fiche_id)
    ).all()
    
    fiche = session.get(FicheTechnique, fiche_id)
    if fiche:
        budget_total = sum(a.budget_souhaite for a in actions_fresh)
        fiche.budget_total_demande = budget_total
        session.add(fiche)
        session.commit()
        logger.info(f"📊 Budget total de la fiche {fiche_id} mis à jour: {budget_total:,.0f} FCFA (depuis {len(actions_fresh)} actions)")


def _creer_ligne(row, structure: dict, fiche_id: int, activite_id: int, session: Session) -> LigneBudgetaireDetail:
    """Créer une ligne budgétaire détaillée"""
    code_libelle_col = structure["colonnes"]["code_libelle"]
    libelle = str(row[code_libelle_col]).strip()
    
    # Extraire le code
    code = libelle.split()[0] if len(libelle.split()) > 0 else f"LIG_{len(session.exec(select(LigneBudgetaireDetail)).all()) + 1}"
    
    ligne = LigneBudgetaireDetail(
        fiche_technique_id=fiche_id,
        activite_id=activite_id,
        code=code,
        libelle=libelle,
        budget_vote_n=_get_montant(row, structure, "budget_vote_n"),
        budget_actuel_n=_get_montant(row, structure, "budget_actuel_n"),
        enveloppe_n_plus_1=_get_montant(row, structure, "enveloppe_n_plus_1"),
        complement_solicite=_get_montant(row, structure, "complement_solicite"),
        budget_souhaite=_get_montant(row, structure, "budget_souhaite"),
        engagement_etat=_get_montant(row, structure, "engagement_etat"),
        autre_complement=_get_montant(row, structure, "autre_complement"),
        projet_budget_n_plus_1=_get_montant(row, structure, "projet_budget_n_plus_1"),
        justificatifs=_get_texte(row, structure, "justificatifs")
    )
    
    session.add(ligne)
    session.commit()
    session.refresh(ligne)
    return ligne


def _get_montant(row, structure: dict, field: str) -> Decimal:
    """Extraire un montant d'une ligne Excel"""
    col = structure["colonnes"].get(field)
    if not col or col not in row:
        return Decimal("0")
    
    try:
        value = row[col]
        if pd.isna(value) or value == "":
            return Decimal("0")
        return Decimal(str(value).replace(",", "").replace(" ", ""))
    except:
        return Decimal("0")


def _get_texte(row, structure: dict, field: str) -> Optional[str]:
    """Extraire un texte d'une ligne Excel"""
    col = structure["colonnes"].get(field)
    if not col or col not in row:
        return None
    
    try:
        value = row[col]
        if pd.isna(value) or value == "":
            return None
        return str(value).strip()
    except:
        return None


# ============================================
# CRÉATION DES ÉLÉMENTS HIÉRARCHIQUES
# ============================================

@router.post("/api/actions")
async def api_create_action(
    fiche_id: int = Form(...),
    nature_depense: str = Form(...),
    code: str = Form(...),
    libelle: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer une nouvelle action"""
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche technique non trouvée")
    
    try:
        # Déterminer l'ordre
        max_ordre = session.exec(
            select(func.max(ActionBudgetaire.ordre))
            .where(ActionBudgetaire.fiche_technique_id == fiche.id)
        ).one() or 0
        
        action = ActionBudgetaire(
            fiche_technique_id=fiche.id,
            nature_depense=nature_depense,
            code=code,
            libelle=libelle,
            ordre=max_ordre + 1,
            budget_vote_n=Decimal("0"),
            budget_actuel_n=Decimal("0"),
            enveloppe_n_plus_1=Decimal("0"),
            complement_solicite=Decimal("0"),
            budget_souhaite=Decimal("0"),
            engagement_etat=Decimal("0"),
            autre_complement=Decimal("0"),
            projet_budget_n_plus_1=Decimal("0")
        )
        
        session.add(action)
        session.commit()
        session.refresh(action)
        
        logger.info(f"✅ Action {code} créée par {current_user.email}")
        return {"ok": True, "id": action.id, "message": "Action créée avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur création action: {e}")
        raise HTTPException(500, f"Erreur lors de la création: {str(e)}")


@router.post("/api/services")
async def api_create_service(
    action_id: int = Form(...),
    code: str = Form(...),
    libelle: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau service bénéficiaire"""
    action = session.get(ActionBudgetaire, action_id)
    if not action:
        raise HTTPException(404, "Action parente non trouvée")
    
    try:
        # Déterminer l'ordre
        max_ordre = session.exec(
            select(func.max(ServiceBeneficiaire.ordre))
            .where(ServiceBeneficiaire.action_id == action_id)
        ).one() or 0
        
        service = ServiceBeneficiaire(
            fiche_technique_id=action.fiche_technique_id,
            action_id=action_id,
            code=code,
            libelle=libelle,
            ordre=max_ordre + 1
        )
        
        session.add(service)
        session.commit()
        session.refresh(service)
        
        logger.info(f"✅ Service {code} créé par {current_user.email}")
        return {"ok": True, "id": service.id, "message": "Service créé avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur création service: {e}")
        raise HTTPException(500, f"Erreur lors de la création: {str(e)}")


@router.post("/api/activites")
async def api_create_activite(
    service_id: int = Form(...),
    code: str = Form(...),
    libelle: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer une nouvelle activité"""
    service = session.get(ServiceBeneficiaire, service_id)
    if not service:
        raise HTTPException(404, "Service parent non trouvé")
    
    try:
        # Déterminer l'ordre
        max_ordre = session.exec(
            select(func.max(ActiviteBudgetaire.ordre))
            .where(ActiviteBudgetaire.service_beneficiaire_id == service_id)
        ).one() or 0
        
        activite = ActiviteBudgetaire(
            fiche_technique_id=service.fiche_technique_id,
            service_beneficiaire_id=service_id,
            code=code,
            libelle=libelle,
            ordre=max_ordre + 1,
            budget_vote_n=Decimal("0"),
            budget_actuel_n=Decimal("0"),
            enveloppe_n_plus_1=Decimal("0"),
            complement_solicite=Decimal("0"),
            budget_souhaite=Decimal("0"),
            engagement_etat=Decimal("0"),
            autre_complement=Decimal("0"),
            projet_budget_n_plus_1=Decimal("0")
        )
        
        session.add(activite)
        session.commit()
        session.refresh(activite)
        
        logger.info(f"✅ Activité {code} créée par {current_user.email}")
        return {"ok": True, "id": activite.id, "message": "Activité créée avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur création activité: {e}")
        raise HTTPException(500, f"Erreur lors de la création: {str(e)}")


@router.post("/api/lignes")
async def api_create_ligne(
    activite_id: int = Form(...),
    code: str = Form(...),
    libelle: str = Form(...),
    budget_vote_n: float = Form(0),
    budget_actuel_n: float = Form(0),
    enveloppe_n_plus_1: float = Form(0),
    complement_solicite: float = Form(0),
    engagement_etat: float = Form(0),
    autre_complement: float = Form(0),
    justificatifs: Optional[str] = Form(None),
    documents: List[UploadFile] = File(default=[]),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer une nouvelle ligne budgétaire avec documents"""
    activite = session.get(ActiviteBudgetaire, activite_id)
    if not activite:
        raise HTTPException(404, "Activité parente non trouvée")
    
    try:
        # Récupérer les codes pour le renommage des fichiers
        service = session.get(ServiceBeneficiaire, activite.service_beneficiaire_id)
        action = session.get(ActionBudgetaire, service.action_id)
        
        # Déterminer l'ordre
        max_ordre = session.exec(
            select(func.max(LigneBudgetaireDetail.ordre))
            .where(LigneBudgetaireDetail.activite_id == activite_id)
        ).one() or 0
        
        # Créer la ligne budgétaire
        ligne = LigneBudgetaireDetail(
            fiche_technique_id=activite.fiche_technique_id,
            activite_id=activite_id,
            code=code,
            libelle=libelle,
            ordre=max_ordre + 1,
            budget_vote_n=Decimal(str(budget_vote_n)),
            budget_actuel_n=Decimal(str(budget_actuel_n)),
            enveloppe_n_plus_1=Decimal(str(enveloppe_n_plus_1)),
            complement_solicite=Decimal(str(complement_solicite)),
            engagement_etat=Decimal(str(engagement_etat)),
            autre_complement=Decimal(str(autre_complement)),
            justificatifs=justificatifs
        )
        
        # Calculer les champs dérivés
        ligne.budget_souhaite = ligne.enveloppe_n_plus_1 + ligne.complement_solicite
        ligne.projet_budget_n_plus_1 = ligne.enveloppe_n_plus_1 + ligne.engagement_etat + ligne.autre_complement
        
        session.add(ligne)
        session.commit()
        session.refresh(ligne)
        
        # Gérer l'upload des documents
        documents_count = 0
        if documents and len(documents) > 0 and documents[0].filename:
            docs_dir = Path(f"uploads/budget/lignes/{ligne.id}")
            docs_dir.mkdir(parents=True, exist_ok=True)
            
            for doc in documents:
                if doc.filename:
                    # Renommer le fichier selon le format : CodeAction_CodeActivité_CodeLigne_NomOriginal.ext
                    file_ext = Path(doc.filename).suffix
                    original_name = Path(doc.filename).stem
                    new_filename = f"{action.code}_{activite.code}_{code}_{original_name}{file_ext}"
                    
                    # Sauvegarder le fichier
                    file_path = docs_dir / new_filename
                    content = await doc.read()
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    # Enregistrer les métadonnées en base
                    doc_meta = DocumentLigneBudgetaire(
                        ligne_budgetaire_id=ligne.id,
                        fiche_technique_id=activite.fiche_technique_id,
                        nom_fichier_original=doc.filename,
                        nom_fichier_stocke=new_filename,
                        chemin_fichier=str(file_path),
                        type_fichier=file_ext,
                        taille_octets=len(content),
                        code_action=action.code,
                        code_activite=activite.code,
                        code_ligne=code,
                        uploaded_by_user_id=current_user.id
                    )
                    session.add(doc_meta)
                    
                    documents_count += 1
                    logger.info(f"📎 Document sauvegardé : {new_filename}")
            
            # Committer les métadonnées des documents
            session.commit()
        
        # Recalculer les totaux de toute la hiérarchie
        _recalculer_totaux_hierarchie(activite.fiche_technique_id, session)
        
        logger.info(f"✅ Ligne budgétaire {code} créée avec {documents_count} document(s) par {current_user.email}")
        return {
            "ok": True, 
            "id": ligne.id, 
            "documents_count": documents_count,
            "message": f"Ligne budgétaire créée avec {documents_count} document(s)"
        }
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur création ligne: {e}")
        raise HTTPException(500, f"Erreur lors de la création: {str(e)}")


# ============================================
# ÉDITION DES ÉLÉMENTS HIÉRARCHIQUES
# ============================================

@router.put("/api/actions/{action_id}")
def api_update_action(
    action_id: int,
    libelle: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier le libellé d'une action (les montants sont recalculés automatiquement)"""
    action = session.get(ActionBudgetaire, action_id)
    if not action:
        raise HTTPException(404, "Action non trouvée")
    
    try:
        action.libelle = libelle
        action.updated_at = datetime.utcnow()
        session.add(action)
        session.commit()
        
        logger.info(f"✅ Action {action_id} modifiée par {current_user.email}")
        return {"ok": True, "message": "Action modifiée avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur modification action {action_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la modification: {str(e)}")


@router.put("/api/services/{service_id}")
def api_update_service(
    service_id: int,
    libelle: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier le libellé d'un service (les montants sont recalculés automatiquement)"""
    service = session.get(ServiceBeneficiaire, service_id)
    if not service:
        raise HTTPException(404, "Service non trouvé")
    
    try:
        service.libelle = libelle
        service.updated_at = datetime.utcnow()
        session.add(service)
        session.commit()
        
        logger.info(f"✅ Service {service_id} modifié par {current_user.email}")
        return {"ok": True, "message": "Service modifié avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur modification service {service_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la modification: {str(e)}")


@router.put("/api/activites/{activite_id}")
def api_update_activite(
    activite_id: int,
    libelle: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier le libellé d'une activité (les montants sont recalculés automatiquement)"""
    activite = session.get(ActiviteBudgetaire, activite_id)
    if not activite:
        raise HTTPException(404, "Activité non trouvée")
    
    try:
        activite.libelle = libelle
        activite.updated_at = datetime.utcnow()
        session.add(activite)
        session.commit()
        
        logger.info(f"✅ Activité {activite_id} modifiée par {current_user.email}")
        return {"ok": True, "message": "Activité modifiée avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur modification activité {activite_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la modification: {str(e)}")


@router.put("/api/lignes/{ligne_id}")
def api_update_ligne(
    ligne_id: int,
    libelle: str = Form(...),
    budget_vote_n: Optional[float] = Form(None),
    budget_actuel_n: Optional[float] = Form(None),
    enveloppe_n_plus_1: Optional[float] = Form(None),
    complement_solicite: Optional[float] = Form(None),
    engagement_etat: Optional[float] = Form(None),
    autre_complement: Optional[float] = Form(None),
    justificatifs: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier une ligne budgétaire (libellé + montants)"""
    ligne = session.get(LigneBudgetaireDetail, ligne_id)
    if not ligne:
        raise HTTPException(404, "Ligne budgétaire non trouvée")
    
    try:
        # Mise à jour des champs
        ligne.libelle = libelle
        if budget_vote_n is not None:
            ligne.budget_vote_n = Decimal(str(budget_vote_n))
        if budget_actuel_n is not None:
            ligne.budget_actuel_n = Decimal(str(budget_actuel_n))
        if enveloppe_n_plus_1 is not None:
            ligne.enveloppe_n_plus_1 = Decimal(str(enveloppe_n_plus_1))
        if complement_solicite is not None:
            ligne.complement_solicite = Decimal(str(complement_solicite))
        if engagement_etat is not None:
            ligne.engagement_etat = Decimal(str(engagement_etat))
        if autre_complement is not None:
            ligne.autre_complement = Decimal(str(autre_complement))
        
        # Recalculer les champs dérivés
        ligne.budget_souhaite = ligne.enveloppe_n_plus_1 + ligne.complement_solicite
        ligne.projet_budget_n_plus_1 = ligne.enveloppe_n_plus_1 + ligne.engagement_etat + ligne.autre_complement
        
        if justificatifs is not None:
            ligne.justificatifs = justificatifs
        
        ligne.updated_at = datetime.utcnow()
        session.add(ligne)
        session.commit()
        
        # Recalculer les totaux de toute la hiérarchie
        _recalculer_totaux_hierarchie(ligne.fiche_technique_id, session)
        
        logger.info(f"✅ Ligne budgétaire {ligne_id} modifiée par {current_user.email}")
        return {"ok": True, "message": "Ligne budgétaire modifiée avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur modification ligne {ligne_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la modification: {str(e)}")


# ============================================
# SUPPRESSION DES ÉLÉMENTS HIÉRARCHIQUES
# ============================================

@router.delete("/api/actions/{action_id}")
def api_delete_action(
    action_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une action (uniquement si elle n'a pas d'enfants)"""
    action = session.get(ActionBudgetaire, action_id)
    if not action:
        raise HTTPException(404, "Action non trouvée")
    
    try:
        # Vérifier qu'il n'y a pas de services enfants
        services_count = session.exec(
            select(func.count(ServiceBeneficiaire.id))
            .where(ServiceBeneficiaire.action_id == action_id)
        ).one()
        
        if services_count > 0:
            raise HTTPException(
                400, 
                f"Impossible de supprimer cette action : elle contient {services_count} service(s). Veuillez d'abord supprimer tous les services enfants."
            )
        
        fiche_id = action.fiche_technique_id
        
        # Supprimer l'action (aucun enfant)
        session.delete(action)
        session.commit()
        
        # Recalculer les totaux
        _recalculer_totaux_hierarchie(fiche_id, session)
        
        logger.info(f"✅ Action {action_id} supprimée par {current_user.email}")
        return {"ok": True, "message": "Action supprimée avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression action {action_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


@router.delete("/api/services/{service_id}")
def api_delete_service(
    service_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un service (uniquement s'il n'a pas d'enfants)"""
    service = session.get(ServiceBeneficiaire, service_id)
    if not service:
        raise HTTPException(404, "Service non trouvé")
    
    try:
        # Vérifier qu'il n'y a pas d'activités enfants
        activites_count = session.exec(
            select(func.count(ActiviteBudgetaire.id))
            .where(ActiviteBudgetaire.service_beneficiaire_id == service_id)
        ).one()
        
        if activites_count > 0:
            raise HTTPException(
                400,
                f"Impossible de supprimer ce service : il contient {activites_count} activité(s). Veuillez d'abord supprimer toutes les activités enfants."
            )
        
        fiche_id = service.fiche_technique_id
        
        # Supprimer le service (aucun enfant)
        session.delete(service)
        session.commit()
        
        # Recalculer les totaux
        _recalculer_totaux_hierarchie(fiche_id, session)
        
        logger.info(f"✅ Service {service_id} supprimé par {current_user.email}")
        return {"ok": True, "message": "Service supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression service {service_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


@router.delete("/api/activites/{activite_id}")
def api_delete_activite(
    activite_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une activité (uniquement si elle n'a pas de lignes)"""
    activite = session.get(ActiviteBudgetaire, activite_id)
    if not activite:
        raise HTTPException(404, "Activité non trouvée")
    
    try:
        # Vérifier qu'il n'y a pas de lignes budgétaires enfants
        lignes_count = session.exec(
            select(func.count(LigneBudgetaireDetail.id))
            .where(LigneBudgetaireDetail.activite_id == activite_id)
        ).one()
        
        if lignes_count > 0:
            raise HTTPException(
                400,
                f"Impossible de supprimer cette activité : elle contient {lignes_count} ligne(s) budgétaire(s). Veuillez d'abord supprimer toutes les lignes enfants."
            )
        
        fiche_id = activite.fiche_technique_id
        
        # Supprimer l'activité (aucune ligne)
        session.delete(activite)
        session.commit()
        
        # Recalculer les totaux
        _recalculer_totaux_hierarchie(fiche_id, session)
        
        logger.info(f"✅ Activité {activite_id} supprimée par {current_user.email}")
        return {"ok": True, "message": "Activité supprimée avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression activité {activite_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


@router.delete("/api/lignes/{ligne_id}")
def api_delete_ligne(
    ligne_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une ligne budgétaire et ses documents"""
    ligne = session.get(LigneBudgetaireDetail, ligne_id)
    if not ligne:
        raise HTTPException(404, "Ligne budgétaire non trouvée")
    
    try:
        fiche_id = ligne.fiche_technique_id
        
        # Supprimer les documents associés
        documents = session.exec(
            select(DocumentLigneBudgetaire)
            .where(DocumentLigneBudgetaire.ligne_budgetaire_id == ligne_id)
        ).all()
        
        for doc in documents:
            # Supprimer le fichier physique
            try:
                file_path = Path(doc.chemin_fichier)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"📎 Fichier supprimé : {doc.nom_fichier_stocke}")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de supprimer le fichier {doc.chemin_fichier}: {e}")
            
            # Supprimer la métadonnée
            session.delete(doc)
        
        # Supprimer la ligne
        session.delete(ligne)
        session.commit()
        
        # Recalculer les totaux
        _recalculer_totaux_hierarchie(fiche_id, session)
        
        logger.info(f"✅ Ligne budgétaire {ligne_id} et ses documents supprimés par {current_user.email}")
        return {"ok": True, "message": "Ligne budgétaire supprimée avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression ligne {ligne_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


# ============================================
# GESTION DES DOCUMENTS DES LIGNES
# ============================================

@router.get("/api/lignes/{ligne_id}/documents")
def api_get_documents_ligne(
    ligne_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupérer la liste des documents d'une ligne budgétaire"""
    ligne = session.get(LigneBudgetaireDetail, ligne_id)
    if not ligne:
        raise HTTPException(404, "Ligne budgétaire non trouvée")
    
    documents = session.exec(
        select(DocumentLigneBudgetaire)
        .where(DocumentLigneBudgetaire.ligne_budgetaire_id == ligne_id)
        .where(DocumentLigneBudgetaire.actif == True)
        .order_by(DocumentLigneBudgetaire.uploaded_at.desc())
    ).all()
    
    return {
        "ok": True,
        "documents": [
            {
                "id": doc.id,
                "nom_original": doc.nom_fichier_original,
                "nom_stocke": doc.nom_fichier_stocke,
                "type": doc.type_fichier,
                "taille": doc.taille_octets,
                "url": f"/uploads/budget/lignes/{ligne_id}/{doc.nom_fichier_stocke}",
                "uploaded_at": doc.uploaded_at.isoformat()
            }
            for doc in documents
        ]
    }


@router.post("/api/lignes/{ligne_id}/documents")
async def api_add_documents_ligne(
    ligne_id: int,
    documents: List[UploadFile] = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Ajouter des documents à une ligne budgétaire existante"""
    ligne = session.get(LigneBudgetaireDetail, ligne_id)
    if not ligne:
        raise HTTPException(404, "Ligne budgétaire non trouvée")
    
    try:
        # Récupérer les codes pour le renommage
        activite = session.get(ActiviteBudgetaire, ligne.activite_id)
        service = session.get(ServiceBeneficiaire, activite.service_beneficiaire_id)
        action = session.get(ActionBudgetaire, service.action_id)
        
        docs_dir = Path(f"uploads/budget/lignes/{ligne_id}")
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        documents_count = 0
        for doc in documents:
            if doc.filename:
                # Renommer le fichier selon le format
                file_ext = Path(doc.filename).suffix
                original_name = Path(doc.filename).stem
                new_filename = f"{action.code}_{activite.code}_{ligne.code}_{original_name}{file_ext}"
                
                # Sauvegarder le fichier
                file_path = docs_dir / new_filename
                content = await doc.read()
                
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # Enregistrer les métadonnées
                doc_meta = DocumentLigneBudgetaire(
                    ligne_budgetaire_id=ligne_id,
                    fiche_technique_id=ligne.fiche_technique_id,
                    nom_fichier_original=doc.filename,
                    nom_fichier_stocke=new_filename,
                    chemin_fichier=str(file_path),
                    type_fichier=file_ext,
                    taille_octets=len(content),
                    code_action=action.code,
                    code_activite=activite.code,
                    code_ligne=ligne.code,
                    uploaded_by_user_id=current_user.id
                )
                session.add(doc_meta)
                documents_count += 1
                logger.info(f"📎 Document ajouté : {new_filename}")
        
        session.commit()
        
        logger.info(f"✅ {documents_count} document(s) ajouté(s) à la ligne {ligne_id}")
        return {
            "ok": True,
            "documents_count": documents_count,
            "message": f"{documents_count} document(s) ajouté(s) avec succès"
        }
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur ajout documents: {e}")
        raise HTTPException(500, f"Erreur lors de l'ajout: {str(e)}")


@router.delete("/api/lignes/{ligne_id}/documents/{document_id}")
def api_delete_document_ligne(
    ligne_id: int,
    document_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un document d'une ligne budgétaire"""
    doc = session.get(DocumentLigneBudgetaire, document_id)
    if not doc or doc.ligne_budgetaire_id != ligne_id:
        raise HTTPException(404, "Document non trouvé")
    
    try:
        # Supprimer le fichier physique
        file_path = Path(doc.chemin_fichier)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"📎 Fichier supprimé : {doc.nom_fichier_stocke}")
        
        # Supprimer la métadonnée
        session.delete(doc)
        session.commit()
        
        logger.info(f"✅ Document {document_id} supprimé par {current_user.email}")
        return {"ok": True, "message": "Document supprimé avec succès"}
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression document {document_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


# ============================================
# SIGOBE - Système d'Information de Gestion et d'Observation Budgétaire
# ============================================

# --- Helpers de parsing SIGOBE (inspirés de PowerQuery) ---

def remove_accents(text: str) -> str:
    """Supprime les accents d'un texte"""
    if not text:
        return ""
    
    replacements = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a', 'å': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ä': 'A', 'Ã': 'A', 'Å': 'A',
        'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Ö': 'O', 'Õ': 'O',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N'
    }
    
    for accent, replacement in replacements.items():
        text = text.replace(accent, replacement)
    
    # Remplacer nbsp par espace
    text = text.replace('\u00a0', ' ')
    
    return text


def normalize_text(text: str) -> str:
    """Normalise un texte : minuscules, sans accents, trim"""
    if not text or pd.isna(text):
        return ""
    text = str(text).strip()
    text = remove_accents(text)
    text = text.lower()
    return text


def parse_date_flexible(value) -> Optional[date]:
    """Parse une date de manière flexible (texte, nombre Excel, date)"""
    if pd.isna(value) or value is None:
        return None
    
    # Si déjà une date
    if isinstance(value, (date, datetime)):
        return value if isinstance(value, date) else value.date()
    
    # Si nombre (date Excel)
    try:
        if isinstance(value, (int, float)):
            return pd.to_datetime(value, origin='1899-12-30', unit='D').date()
    except:
        pass
    
    # Si texte
    try:
        text = str(value).strip().replace('.', '/').replace('-', '/')
        parsed = pd.to_datetime(text, format='%d/%m/%Y', errors='coerce')
        if pd.notna(parsed):
            return parsed.date()
    except:
        pass
    
    return None


def find_metadata_row(df: pd.DataFrame) -> Optional[dict]:
    """
    Trouve la ligne de métadonnées (Exercice/Année, Période, etc.)
    Inspiré de fxFindExerciceRow_Safe
    """
    search_terms = ['exercice', 'exercice:']
    
    for idx in range(min(20, len(df))):  # Scanner les 20 premières lignes
        row_values = df.iloc[idx].astype(str).str.lower().str.strip()
        
        for term in search_terms:
            if any(term in val for val in row_values if val):
                # Ligne trouvée, extraire les métadonnées
                row_data = df.iloc[idx]
                metadata = {}
                
                for col_idx, val in enumerate(row_data):
                    val_str = str(val).strip()
                    if ':' in val_str:
                        parts = val_str.split(':', 1)
                        key = normalize_text(parts[0])
                        value = parts[1].strip() if len(parts) > 1 else ""
                        
                        if 'exercice' in key or 'annee' in key:
                            metadata['annee'] = value
                        elif 'periode' in key:
                            metadata['periode'] = value
                        elif 'section' in key:
                            metadata['section'] = value
                        elif 'categorie' in key:
                            metadata['categorie'] = value
                        elif 'credit' in key or 'type' in key:
                            metadata['type_credit'] = value
                
                return metadata
    
    return None


def detect_hierarchy_depth(df: pd.DataFrame, start_row: int) -> int:
    """
    Détecte la profondeur de la hiérarchie (nombre de colonnes significatives)
    Inspiré de fxFirstEmptyInRow
    """
    if start_row >= len(df):
        return 6  # Par défaut
    
    row = df.iloc[start_row]
    
    # Compter les colonnes non vides
    non_empty = 0
    for val in row:
        if pd.notna(val) and str(val).strip() != '':
            non_empty += 1
        else:
            break  # Première colonne vide trouvée
    
    return max(3, min(6, non_empty))  # Entre 3 et 6


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomme automatiquement les colonnes financières
    Inspiré de fxTableStandardName_AutoMapping
    ⚠️ ORDRE IMPORTANT : Du plus spécifique au plus général !
    """
    # Ordre crucial : patterns spécifiques en premier
    standard_mapping = [
        # Mandats (spécifiques en premier !)
        (['vise cf', 'visé cf', 'vise'], 'Mandats_Vise_CF'),
        (['pec', 'prise en charge'], 'Mandats_Pec'),
        (['mandat emis', 'mandats emis'], 'Mandats_Emis'),  # Spécifique
        (['emis','emise'], 'Mandats_Emis'),  # Général (après les spécifiques)
        # Budget
        (['budget vote', 'budget voté'], 'Budget_Vote'),
        (['budget actuel','actuel'], 'Budget_Actuel'),
        (['vote'], 'Budget_Vote'),
        (['actuel'], 'Budget_Actuel'),
        
        # Engagements
        (['engagement', 'engagements', 'engag'], 'Engagements_Emis'),
        
        # Disponible
        (['disponible', 'dispo'], 'Disponible_Eng'),
    ]
    
    new_columns = []
    for col in df.columns:
        col_normalized = normalize_text(str(col))
        
        # Chercher une correspondance (du plus spécifique au plus général)
        matched = False
        for patterns, std_name in standard_mapping:
            for pattern in patterns:
                if pattern in col_normalized:
                    new_columns.append(std_name)
                    matched = True
                    break
            if matched:
                break
        
        if not matched:
            new_columns.append(col)
    
    df.columns = new_columns
    return df


def split_code_libelle(text: str) -> tuple:
    """
    Sépare code et libellé (ex: '2208401 Pilotage...' -> ('2208401', 'Pilotage...')).
    Le code doit être numérique, sinon pas de code.
    
    Exemples:
    - "2208401 Pilotage et Soutien" -> ("2208401", "Pilotage et Soutien")
    - "P01 Programme 01" -> ("P01", "Programme 01")
    - "Direction Générale" -> ("", "Direction Générale")
    - "Pilotage" -> ("", "Pilotage")
    """
    if not text or pd.isna(text):
        return ("", "")
    
    text = str(text).strip()
    parts = text.split(' ', 1)
    
    if len(parts) == 2:
        first_part = parts[0].strip()
        # Vérifier si le premier mot contient au moins un chiffre (code numérique)
        if any(c.isdigit() for c in first_part):
            # C'est un code numérique suivi d'un libellé
            return (first_part, parts[1].strip())
        else:
            # Pas de code numérique, tout est le libellé
            return ("", text)
    else:
        # Un seul mot, pas de séparation -> pas de code
        return ("", text)


@router.get("/sigobe", response_class=HTMLResponse, name="budget_sigobe")
def budget_sigobe(
    request: Request,
    annee: Optional[int] = None,
    trimestre: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page principale SIGOBE"""
    
    # Récupérer les chargements
    query = select(SigobeChargement).order_by(SigobeChargement.date_chargement.desc())
    
    if annee:
        query = query.where(SigobeChargement.annee == annee)
    if trimestre:
        query = query.where(SigobeChargement.trimestre == trimestre)
    
    chargements = session.exec(query).all()
    
    # Années disponibles
    annees_query = select(SigobeChargement.annee).distinct()
    annees_result = session.exec(annees_query).all()
    # Gérer le cas où c'est des int directs ou des tuples
    if annees_result and isinstance(annees_result[0], tuple):
        annees = sorted([a for (a,) in annees_result], reverse=True)
    else:
        annees = sorted(annees_result, reverse=True)
    
    # KPIs globaux (dernière période)
    kpis_global = None
    if chargements:
        dernier_chargement = chargements[0]
        kpis_global = session.exec(
            select(SigobeKpi)
            .where(SigobeKpi.chargement_id == dernier_chargement.id)
            .where(SigobeKpi.dimension == "global")
        ).first()
    
    return templates.TemplateResponse(
        "pages/budget_sigobe.html",
        get_template_context(
            request,
            chargements=chargements,
            annees=annees,
            annee_selected=annee,
            trimestre_selected=trimestre,
            kpis_global=kpis_global,
            current_user=current_user
        )
    )
@router.post("/api/sigobe/preview")
async def api_sigobe_preview(
    fichier: UploadFile = File(...),
    annee: int = Form(...),
    trimestre: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Prévisualisation d'un fichier SIGOBE (sans sauvegarde)
    Analyse le fichier et retourne un aperçu des données
    """
    try:
        content = await fichier.read()
        excel_file = BytesIO(content)
        
        # Réutiliser la même logique de parsing
        Result, Metadatafile, ColsToKeep = _parse_sigobe_file(excel_file, annee, trimestre)
        
        # Statistiques
        stats = {
            'nb_lignes': int(len(Result)),
            'nb_colonnes': int(len(Result.columns)),
            'colonnes': list(Result.columns),
            'colonnes_hierarchiques': list(ColsToKeep),
            'nb_programmes': int(Result['Programmes'].nunique()) if 'Programmes' in Result.columns else 0,
            'nb_actions': int(Result['Actions'].nunique()) if 'Actions' in Result.columns else 0,
            'metadata': {k: str(v) for k, v in Metadatafile.items()}  # Convertir en strings
        }
        
        # Aperçu des données (20 premières lignes)
        preview_data = []
        for idx, row in Result.head(20).iterrows():
            preview_data.append({
                col: str(row[col]) if pd.notna(row[col]) else ''
                for col in Result.columns
            })
        
        # Calcul des totaux préliminaires
        financial_cols = ['Budget_Vote', 'Budget_Actuel', 'Engagements_Emis', 'Mandats_Emis']
        totaux = {}
        
        for col in financial_cols:
            if col in Result.columns:
                total = Result[col].sum()
                totaux[col] = float(total)
        
        logger.info(f"✅ Prévisualisation : {stats['nb_lignes']} lignes, {stats['nb_programmes']} programmes")
        
        return {
            "ok": True,
            "stats": stats,
            "preview": preview_data,
            "totaux": totaux,
            "message": f"Fichier analysé : {stats['nb_lignes']} lignes prêtes à importer"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur prévisualisation SIGOBE : {e}")
        raise HTTPException(500, f"Erreur lors de l'analyse : {str(e)}")


def _parse_sigobe_file(excel_file: BytesIO, annee: int, trimestre: Optional[int]) -> tuple:
    """
    Parse un fichier SIGOBE et retourne (DataFrame nettoyé, Métadonnées, ColsToKeep)
    Fonction réutilisable pour preview et upload
    """
    # --- A. Charger le classeur et prendre la 1ʳᵉ feuille ---
    Source = pd.ExcelFile(excel_file)
    Raw = pd.read_excel(Source, sheet_name=0, header=None)
    
    logger.info(f"📊 [A] Classeur chargé, shape={Raw.shape}")
    
    # --- B. Métadonnées (robuste aux nulls) ---
    Metadatafile = find_metadata_row(Raw)
    if not Metadatafile:
        Metadatafile = {}
    
    if 'annee' not in Metadatafile or not Metadatafile['annee']:
        Metadatafile['annee'] = str(annee)
    
    logger.info(f"📋 [B] Métadonnées : {Metadatafile}")
    
    # --- C. Suppression des lignes 100 % vides ---
    NonEmpty = Raw.dropna(how='all')
    logger.info(f"🧹 [C] Lignes non vides : {len(NonEmpty)}")
    
    # --- D. Début des données (fxFirstEmptyFromBottom) ---
    first_col = NonEmpty.iloc[:, 0]
    empty_from_bottom_idx = None
    
    for i in range(len(first_col) - 1, -1, -1):
        val = first_col.iloc[i]
        if pd.isna(val) or str(val).strip() == '':
            empty_from_bottom_idx = i
            break
    
    if empty_from_bottom_idx is None:
        empty_from_bottom_idx = 0
    
    PosRaw = empty_from_bottom_idx + 1
    PosSafe = max(1, int(PosRaw))
    KeepFromPos = NonEmpty.iloc[PosSafe - 1:]
    
    logger.info(f"📍 [D] Ligne d'en-têtes : {empty_from_bottom_idx}, PosSafe={PosSafe}")
    
    # --- F. Promotion des en-têtes ---
    # ⚠️ D'abord promouvoir les en-têtes pour savoir combien de "Column" on a
    Promoted = KeepFromPos.copy()
    
    new_col_names = []
    col_counter = 1
    
    for i, col_val in enumerate(Promoted.iloc[0]):
        if pd.isna(col_val) or str(col_val).strip() == '' or str(col_val).lower() == 'nan':
            new_col_names.append(f"Column{col_counter}")
            col_counter += 1
        else:
            new_col_names.append(str(col_val).strip())
    
    Promoted.columns = new_col_names
    Promoted = Promoted.iloc[1:]
    Promoted = Promoted.reset_index(drop=True)
    
    logger.info(f"🏷️ [F] En-têtes promus : {list(Promoted.columns[:10])}")
    
    # --- E. Détermination du nombre de colonnes utiles (fxFirstNonEmptyInRow) ---
    # ⚠️ Compter le nombre de colonnes qui s'appellent "ColumnN" dans Promoted
    # Car ces colonnes correspondent aux colonnes hiérarchiques sans nom
    NbreCol_arenommer = sum(1 for col in Promoted.columns if col.startswith('Column'))
    
    logger.info(f"📏 [E] Nombre colonnes hiérarchiques (colonnes 'Column') : {NbreCol_arenommer}")
    
    # --- G. Sélection des lignes utiles (PivotCol) ---
    pivot_col_index = max(2, NbreCol_arenommer - 1)
    if pivot_col_index < len(Promoted.columns):
        PivotCol = Promoted.columns[pivot_col_index]
        OnlyData = Promoted[Promoted[PivotCol].notna() & (Promoted[PivotCol] != '')]
    else:
        OnlyData = Promoted
    
    logger.info(f"🎯 [G] Lignes après filtrage pivot : {len(OnlyData)}")
    
    # --- I. Renommage dynamique selon le niveau hiérarchique ---
    HierarchyCols = ["Programmes", "Actions", "Rprog", "Type_depense", "Activites", "Taches"]
    
    # Si on a 5 colonnes "Column", on veut renommer les 5
    # Donc DepthIndex = NbreCol_arenommer (pas -1)
    DepthIndex = min(max(NbreCol_arenommer, 1), 6)
    ColsToKeep = HierarchyCols[:DepthIndex]
    
    Pairs = {}
    for i, col_name in enumerate(ColsToKeep):
        column_name = f"Column{i+1}"
        if column_name in OnlyData.columns:
            Pairs[column_name] = col_name
    
    Base6 = OnlyData.rename(columns=Pairs)
    logger.info(f"🔤 [I] Renommage hiérarchique : {Pairs} → ColsToKeep={ColsToKeep}")
    
    # --- J. Suppression colonnes taux/ratio (AVANT mapping !) ---
    cols_to_drop = []
    
    for col in Base6.columns:
        # Protéger les colonnes hiérarchiques
        if any(col.startswith(h) for h in HierarchyCols):
            continue
        
        col_lower = normalize_text(str(col))
        
        # Règle 1 : nom contient "tx", "taux", "ratio", "%"
        if any(word in col_lower for word in ['tx', 'taux', 'ratio', '%', '(d=', 'd=']):
            cols_to_drop.append(col)
            continue
        
        # Règle 2 : valeurs numériques entre 0 et 1
        try:
            col_data = pd.to_numeric(Base6[col], errors='coerce')
            valid_vals = col_data.dropna()
            if len(valid_vals) > 0:
                if ((valid_vals >= 0) & (valid_vals <= 1)).all():
                    cols_to_drop.append(col)
        except:
            pass  # Si pas numérique, ignorer
    
    CleanRates = Base6.drop(columns=cols_to_drop, errors='ignore')
    logger.info(f"🗑️ [J] Colonnes taux/ratios supprimées : {cols_to_drop}")
    
    # --- K. Métadonnées (pas de fusion) ---
    WithMeta = CleanRates
    logger.info(f"📊 [K] Métadonnées conservées séparément")
    
    # --- L. Mapping automatique des colonnes financières ---
    Mapped = standardize_column_names(WithMeta)
    
    logger.info(f"🗺️ [L] Colonnes après mapping : {list(Mapped.columns)}")
    
    # --- M. Séparation des codes/libellés (SIMPLIFIÉ Python) ---
    # En Python : pas besoin de créer 2 colonnes puis supprimer/renommer
    # On applique directement : garder seulement le libellé (supprimer le code)
    Canon = Mapped.copy()
    
    for col in ColsToKeep:
        if col in Canon.columns:
            # Appliquer split_code_libelle et garder seulement le libellé (index 1)
            Canon[col] = Canon[col].apply(lambda x: split_code_libelle(x)[1] if pd.notna(x) else '')
    
    logger.info(f"✂️ [M] Codes supprimés, libellés conservés")
    
    # DEBUG : Exporter Canon en Excel pour inspection
    try:
        debug_path = Path(f"app/static/uploads/sigobe/debug_canon_{annee}.xlsx")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        Canon.to_excel(debug_path, index=False)
        logger.info(f"🐛 [DEBUG] Table Canon exportée : {debug_path}")
        logger.info(f"🐛 [DEBUG] Colonnes Canon : {list(Canon.columns)}")
        logger.info(f"🐛 [DEBUG] Shape Canon : {Canon.shape}")
        logger.info(f"🐛 [DEBUG] Dtypes Canon : {Canon.dtypes.to_dict()}")
    except Exception as e:
        logger.warning(f"⚠️ [DEBUG] Impossible d'exporter Canon : {e}")
    
    # --- N. Typage ---
    # 1) Colonnes numériques (si présentes)
    colsNum = ["Budget_Vote", "Budget_Actuel", "Engagements_Emis", 
               "Disponible_Eng", "Mandats_Emis", "Mandats_Vise_CF", "Mandats_Pec"]
    
    for col in colsNum:
        if col in Canon.columns:
            try:
                # Vérifier que c'est bien une Series et pas un DataFrame
                col_data = Canon[col]
                if isinstance(col_data, pd.Series):
                    Canon[col] = pd.to_numeric(col_data, errors='coerce').fillna(0)
                else:
                    logger.warning(f"⚠️ [N] {col} n'est pas une Series, ignoré")
            except Exception as e:
                logger.warning(f"⚠️ [N] Erreur typage numérique {col} : {e}")
    
    # 2) Textes : colonnes hiérarchiques seulement
    for col in ColsToKeep:
        if col in Canon.columns:
            try:
                col_data = Canon[col]
                if isinstance(col_data, pd.Series):
                    Canon[col] = col_data.fillna('').astype(str).str.strip()
                else:
                    logger.warning(f"⚠️ [N] {col} n'est pas une Series, ignoré")
            except Exception as e:
                logger.warning(f"⚠️ [N] Erreur typage texte {col} : {e}")
    
    Final = Canon
    logger.info(f"🔢 [N] Typage effectué")
    
    # --- O. Filtrage sur la dernière colonne hiérarchique ---
    LastKey = ColsToKeep[-1] if ColsToKeep else None
    
    if LastKey and LastKey in Final.columns:
        # Filtrer : garder seulement les lignes où LastKey n'est pas vide
        # Convertir en string pour la comparaison
        KeepRows = Final[Final[LastKey].notna() & (Final[LastKey].astype(str).str.strip() != '')]
    else:
        KeepRows = Final
    
    logger.info(f"🎯 [O] Filtrage final : {len(KeepRows)} lignes")
    
    # Retourner le DataFrame + métadonnées + colonnes hiérarchiques
    return (KeepRows, Metadatafile, ColsToKeep)


@router.post("/api/sigobe/upload")
async def api_sigobe_upload(
    fichier: UploadFile = File(...),
    annee: int = Form(...),
    trimestre: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Upload et analyse d'un fichier SIGOBE (Excel)
    Parser suivant SCRUPULEUSEMENT la logique fxInspectTable PowerQuery (étapes A→O)
    """
    try:
        content = await fichier.read()
        excel_file = BytesIO(content)
        
        # Parser le fichier (étapes A→O de PowerQuery)
        Result, Metadatafile, ColsToKeep = _parse_sigobe_file(excel_file, annee, trimestre)
        
        logger.info(f"✅ Parsing réussi : {len(Result)} lignes à importer")
        
        # Déterminer le libellé de période
        if trimestre:
            periode_libelle = f"T{trimestre} {annee}"
        else:
            periode_libelle = f"Annuel {annee}"
        
        # Sauvegarder le fichier physiquement (SEULEMENT si parsing OK)
        upload_dir = Path(f"app/static/uploads/sigobe/{annee}")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / fichier.filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"📁 Fichier sauvegardé : {file_path}")
        
        # 10. Créer l'enregistrement de chargement
        chargement = SigobeChargement(
            annee=annee,
            trimestre=trimestre,
            periode_libelle=periode_libelle,
            nom_fichier=fichier.filename,
            taille_octets=len(content),
            chemin_fichier=f"/uploads/sigobe/{annee}/{fichier.filename}",
            uploaded_by_user_id=current_user.id,
            statut="En cours"
        )
        
        session.add(chargement)
        session.commit()
        session.refresh(chargement)
        
        logger.info(f"✅ Chargement créé : ID={chargement.id}")
        
        # 11. Importer les lignes d'exécution depuis Result
        nb_lignes = 0
        programmes_set = set()
        actions_set = set()
        
        financial_columns = [
            'Budget_Vote', 'Budget_Actuel', 'Engagements_Emis',
            'Disponible_Eng', 'Mandats_Emis', 'Mandats_Vise_CF', 'Mandats_Pec'
        ]
        
        for idx, row in Result.iterrows():
            try:
                # Extraire les montants depuis Result (colonnes typées)
                montants = {}
                for col in financial_columns:
                    if col in Result.columns:
                        val = row[col]
                        if pd.notna(val):
                            try:
                                montants[col.lower()] = Decimal(str(val))
                            except:
                                montants[col.lower()] = Decimal('0')
                        else:
                            montants[col.lower()] = Decimal('0')
                    else:
                        montants[col.lower()] = Decimal('0')
                
                # Extraire les métadonnées de la ligne (si présentes)
                periode_val = row.get('Periode') if 'Periode' in Result.columns else None
                section_val = row.get('Section', '') if 'Section' in Result.columns else Metadatafile.get('section', '')
                categorie_val = row.get('Categorie', '') if 'Categorie' in Result.columns else Metadatafile.get('categorie', '')
                type_credit_val = row.get('Type_credit', '') if 'Type_credit' in Result.columns else Metadatafile.get('type_credit', '')
                
                # Créer la ligne d'exécution
                execution = SigobeExecution(
                    chargement_id=chargement.id,
                    annee=annee,
                    trimestre=trimestre,
                    periode=periode_val if isinstance(periode_val, date) else None,
                    section=str(section_val) if section_val else None,
                    categorie=str(categorie_val) if categorie_val else None,
                    type_credit=str(type_credit_val) if type_credit_val else None,
                    programmes=str(row.get('Programmes', '')) if 'Programmes' in Result.columns else '',
                    actions=str(row.get('Actions', '')) if 'Actions' in Result.columns else '',
                    rprog=str(row.get('Rprog', '')) if 'Rprog' in Result.columns else '',
                    type_depense=str(row.get('Type_depense', '')) if 'Type_depense' in Result.columns else '',
                    activites=str(row.get('Activites', '')) if 'Activites' in Result.columns else '',
                    taches=str(row.get('Taches', '')) if 'Taches' in Result.columns else '',
                    budget_vote=montants.get('budget_vote', 0),
                    budget_actuel=montants.get('budget_actuel', 0),
                    engagements_emis=montants.get('engagements_emis', 0),
                    disponible_eng=montants.get('disponible_eng', 0),
                    mandats_emis=montants.get('mandats_emis', 0),
                    mandats_vise_cf=montants.get('mandats_vise_cf', 0),
                    mandats_pec=montants.get('mandats_pec', 0)
                )
                
                session.add(execution)
                nb_lignes += 1
                
                # Collecter les programmes/actions uniques
                if row.get('Programmes'):
                    programmes_set.add(str(row.get('Programmes')))
                if row.get('Actions'):
                    actions_set.add(str(row.get('Actions')))
                
                # Commit par batch de 100
                if nb_lignes % 100 == 0:
                    session.commit()
                    logger.info(f"💾 {nb_lignes} lignes importées...")
            
            except Exception as e:
                logger.warning(f"⚠️ Erreur ligne {idx}: {e}")
                continue
        
        # Commit final
        session.commit()
        
        # 12. Mettre à jour le chargement
        chargement.nb_lignes_importees = nb_lignes
        chargement.nb_programmes = len(programmes_set)
        chargement.nb_actions = len(actions_set)
        chargement.statut = "Terminé"
        session.add(chargement)
        session.commit()
        
        logger.info(f"✅ Import terminé : {nb_lignes} lignes, {len(programmes_set)} programmes, {len(actions_set)} actions")
        
        # 13. Calculer les KPIs
        try:
            calcul_kpis_sigobe(chargement.id, session)
        except Exception as e:
            logger.error(f"❌ Erreur calcul KPIs : {e}")
        
        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="upload",
            target_type="sigobe",
            description=f"Import SIGOBE {periode_libelle} - {nb_lignes} lignes, {len(programmes_set)} programmes",
            target_id=chargement.id,
            icon="📊"
        )
        
        return {
            "ok": True,
            "chargement_id": chargement.id,
            "nb_lignes": nb_lignes,
            "nb_programmes": len(programmes_set),
            "nb_actions": len(actions_set),
            "message": f"Import réussi : {nb_lignes} lignes chargées"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur upload SIGOBE : {e}")
        
        # Marquer le chargement comme en erreur si créé
        if 'chargement' in locals():
            chargement.statut = "Erreur"
            chargement.message_erreur = str(e)
            session.add(chargement)
            session.commit()
        
        raise HTTPException(500, f"Erreur lors de l'import : {str(e)}")


def calcul_kpis_sigobe(chargement_id: int, session: Session):
    """Calcule les KPIs agrégés pour un chargement SIGOBE"""
    
    chargement = session.get(SigobeChargement, chargement_id)
    if not chargement:
        return
    
    # Récupérer toutes les données d'exécution
    executions = session.exec(
        select(SigobeExecution).where(SigobeExecution.chargement_id == chargement_id)
    ).all()
    
    if not executions:
        return
    
    # 1. KPI Global
    global_budget_vote = sum(e.budget_vote or 0 for e in executions)
    global_budget_actuel = sum(e.budget_actuel or 0 for e in executions)
    global_engagements = sum(e.engagements_emis or 0 for e in executions)
    global_mandats = sum(e.mandats_emis or 0 for e in executions)
    
    taux_engagement = (float(global_engagements) / float(global_budget_actuel) * 100) if global_budget_actuel > 0 else 0
    taux_mandatement = (float(global_mandats) / float(global_engagements) * 100) if global_engagements > 0 else 0
    taux_execution = (float(global_mandats) / float(global_budget_actuel) * 100) if global_budget_actuel > 0 else 0
    
    kpi_global = SigobeKpi(
        annee=chargement.annee,
        trimestre=chargement.trimestre,
        dimension="global",
        budget_vote_total=Decimal(str(global_budget_vote)),
        budget_actuel_total=Decimal(str(global_budget_actuel)),
        engagements_total=Decimal(str(global_engagements)),
        mandats_total=Decimal(str(global_mandats)),
        taux_engagement=Decimal(str(round(taux_engagement, 2))),
        taux_mandatement=Decimal(str(round(taux_mandatement, 2))),
        taux_execution=Decimal(str(round(taux_execution, 2))),
        chargement_id=chargement_id
    )
    
    session.add(kpi_global)
    
    # 2. KPIs par programme
    programmes_dict = defaultdict(lambda: {'budget_vote': 0, 'budget_actuel': 0, 'engagements': 0, 'mandats': 0})
    
    for e in executions:
        if e.programmes:
            programmes_dict[e.programmes]['budget_vote'] += e.budget_vote or 0
            programmes_dict[e.programmes]['budget_actuel'] += e.budget_actuel or 0
            programmes_dict[e.programmes]['engagements'] += e.engagements_emis or 0
            programmes_dict[e.programmes]['mandats'] += e.mandats_emis or 0
    
    for prog, data in programmes_dict.items():
        taux_eng = (float(data['engagements']) / float(data['budget_actuel']) * 100) if data['budget_actuel'] > 0 else 0
        taux_mand = (float(data['mandats']) / float(data['engagements']) * 100) if data['engagements'] > 0 else 0
        taux_exec = (float(data['mandats']) / float(data['budget_actuel']) * 100) if data['budget_actuel'] > 0 else 0
        
        code, libelle = split_code_libelle(prog)
        
        kpi_prog = SigobeKpi(
            annee=chargement.annee,
            trimestre=chargement.trimestre,
            dimension="programme",
            dimension_code=code,
            dimension_libelle=libelle,
            budget_vote_total=Decimal(str(data['budget_vote'])),
            budget_actuel_total=Decimal(str(data['budget_actuel'])),
            engagements_total=Decimal(str(data['engagements'])),
            mandats_total=Decimal(str(data['mandats'])),
            taux_engagement=Decimal(str(round(taux_eng, 2))),
            taux_mandatement=Decimal(str(round(taux_mand, 2))),
            taux_execution=Decimal(str(round(taux_exec, 2))),
            chargement_id=chargement_id
        )
        
        session.add(kpi_prog)
    
    # 3. KPIs par nature de dépense
    natures_dict = defaultdict(lambda: {'budget_vote': 0, 'budget_actuel': 0, 'engagements': 0, 'mandats': 0})
    
    for e in executions:
        if e.type_depense:
            natures_dict[e.type_depense]['budget_vote'] += e.budget_vote or 0
            natures_dict[e.type_depense]['budget_actuel'] += e.budget_actuel or 0
            natures_dict[e.type_depense]['engagements'] += e.engagements_emis or 0
            natures_dict[e.type_depense]['mandats'] += e.mandats_emis or 0
    
    for nature, data in natures_dict.items():
        taux_eng = (float(data['engagements']) / float(data['budget_actuel']) * 100) if data['budget_actuel'] > 0 else 0
        taux_mand = (float(data['mandats']) / float(data['engagements']) * 100) if data['engagements'] > 0 else 0
        taux_exec = (float(data['mandats']) / float(data['budget_actuel']) * 100) if data['budget_actuel'] > 0 else 0
        
        # Extraire le code court de la nature de dépense
        code_nature, libelle_nature = split_code_libelle(nature)
        
        # Si le code est vide ou identique au libellé, utiliser des abréviations standards
        if not code_nature or code_nature == libelle_nature:
            nature_lower = nature.lower()
            if 'bien' in nature_lower or 'service' in nature_lower:
                code_nature = 'BS'
            elif 'personnel' in nature_lower:
                code_nature = 'P'
            elif 'investissement' in nature_lower:
                code_nature = 'I'
            elif 'transfert' in nature_lower:
                code_nature = 'T'
            else:
                code_nature = nature[:3].upper()  # Prendre les 3 premières lettres
            libelle_nature = nature
        
        kpi_nature = SigobeKpi(
            annee=chargement.annee,
            trimestre=chargement.trimestre,
            dimension="nature",
            dimension_code=code_nature,
            dimension_libelle=libelle_nature,
            budget_vote_total=Decimal(str(data['budget_vote'])),
            budget_actuel_total=Decimal(str(data['budget_actuel'])),
            engagements_total=Decimal(str(data['engagements'])),
            mandats_total=Decimal(str(data['mandats'])),
            taux_engagement=Decimal(str(round(taux_eng, 2))),
            taux_mandatement=Decimal(str(round(taux_mand, 2))),
            taux_execution=Decimal(str(round(taux_exec, 2))),
            chargement_id=chargement_id
        )
        
        session.add(kpi_nature)
    
    session.commit()
    logger.info(f"✅ KPIs calculés : 1 global + {len(programmes_dict)} programmes + {len(natures_dict)} natures")


@router.delete("/api/sigobe/{chargement_id}")
def api_delete_sigobe(
    chargement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un chargement SIGOBE et toutes ses données"""
    chargement = session.get(SigobeChargement, chargement_id)
    if not chargement:
        raise HTTPException(404, "Chargement non trouvé")
    
    try:
        # Supprimer les KPIs
        session.exec(
            delete(SigobeKpi).where(SigobeKpi.chargement_id == chargement_id)
        )
        
        # Supprimer les exécutions
        session.exec(
            delete(SigobeExecution).where(SigobeExecution.chargement_id == chargement_id)
        )
        
        # Supprimer le chargement
        periode_libelle = chargement.periode_libelle
        session.delete(chargement)
        session.commit()
        
        logger.info(f"✅ Chargement SIGOBE {chargement_id} supprimé par {current_user.email}")
        
        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="delete",
            target_type="sigobe",
            description=f"Suppression du chargement SIGOBE {periode_libelle}",
            target_id=chargement_id,
            icon="🗑️"
        )
        
        return {"ok": True, "message": "Chargement supprimé avec succès"}
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur suppression chargement {chargement_id}: {e}")
        raise HTTPException(500, f"Erreur lors de la suppression: {str(e)}")


@router.get("/api/sigobe/{chargement_id}/kpis")
def api_get_kpis_sigobe(
    chargement_id: int,
    dimension: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupérer les KPIs d'un chargement SIGOBE"""
    
    query = select(SigobeKpi).where(SigobeKpi.chargement_id == chargement_id)
    
    if dimension:
        query = query.where(SigobeKpi.dimension == dimension)
    
    kpis = session.exec(query).all()
    
    return {
        "ok": True,
        "kpis": [
            {
                "id": kpi.id,
                "dimension": kpi.dimension,
                "dimension_code": kpi.dimension_code,
                "dimension_libelle": kpi.dimension_libelle,
                "budget_vote_total": float(kpi.budget_vote_total),
                "budget_actuel_total": float(kpi.budget_actuel_total),
                "engagements_total": float(kpi.engagements_total),
                "mandats_total": float(kpi.mandats_total),
                "taux_engagement": float(kpi.taux_engagement),
                "taux_mandatement": float(kpi.taux_mandatement),
                "taux_execution": float(kpi.taux_execution)
            }
            for kpi in kpis
        ]
    }

