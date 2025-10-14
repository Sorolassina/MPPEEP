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

from app.db.session import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.budget import (
    NatureDepense, Activite, FicheTechnique, LigneBudgetaire,
    DocumentBudget, HistoriqueBudget, ExecutionBudgetaire, ConferenceBudgetaire,
    ActionBudgetaire, ServiceBeneficiaire, ActiviteBudgetaire, LigneBudgetaireDetail
)
from app.models.personnel import Programme, Direction
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger

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
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Dashboard principal du suivi budgétaire
    """
    if not annee:
        annee = datetime.now().year
    
    # KPIs globaux
    execution = session.exec(
        select(ExecutionBudgetaire)
        .where(ExecutionBudgetaire.annee == annee)
    )
    
    if programme_id:
        execution = execution.where(ExecutionBudgetaire.programme_id == programme_id)
    
    executions = execution.all()
    
    # Calculs des totaux
    budget_total = sum(e.budget_vote for e in executions)
    engagements_total = sum(e.engagements for e in executions)
    mandats_vises_total = sum(e.mandats_vises for e in executions)
    mandats_pec_total = sum(e.mandats_pec for e in executions)
    disponible_total = budget_total - engagements_total
    
    # Taux
    taux_engagement = (engagements_total / budget_total * 100) if budget_total > 0 else 0
    taux_mandatement = (mandats_pec_total / budget_total * 100) if budget_total > 0 else 0
    taux_execution = taux_mandatement  # Simplification
    
    # Par programme
    programmes = session.exec(select(Programme).where(Programme.actif == True)).all()
    exec_par_programme = {}
    for prog in programmes:
        exec_prog = [e for e in executions if e.programme_id == prog.id]
        budget_prog = sum(e.budget_vote for e in exec_prog)
        mandats_prog = sum(e.mandats_pec for e in exec_prog)
        taux_prog = (mandats_prog / budget_prog * 100) if budget_prog > 0 else 0
        exec_par_programme[prog.code] = {
            "libelle": prog.libelle,
            "budget": budget_prog,
            "mandats": mandats_prog,
            "taux": round(taux_prog, 2)
        }
    
    # Par nature de dépense
    natures = session.exec(select(NatureDepense).where(NatureDepense.actif == True)).all()
    exec_par_nature = {}
    for nature in natures:
        exec_nat = [e for e in executions if e.nature_depense_id == nature.id]
        budget_nat = sum(e.budget_vote for e in exec_nat)
        mandats_nat = sum(e.mandats_pec for e in exec_nat)
        taux_nat = (mandats_nat / budget_nat * 100) if budget_nat > 0 else 0
        exec_par_nature[nature.code] = {
            "libelle": nature.libelle,
            "budget": budget_nat,
            "mandats": mandats_nat,
            "taux": round(taux_nat, 2)
        }
    
    return templates.TemplateResponse(
        "pages/budget_dashboard.html",
        get_template_context(
            request,
            annee=annee,
            budget_total=float(budget_total),
            engagements_total=float(engagements_total),
            mandats_vises_total=float(mandats_vises_total),
            mandats_pec_total=float(mandats_pec_total),
            disponible_total=float(disponible_total),
            taux_engagement=round(taux_engagement, 2),
            taux_mandatement=round(taux_mandatement, 2),
            taux_execution=round(taux_execution, 2),
            exec_par_programme=exec_par_programme,
            exec_par_nature=exec_par_nature,
            programmes=programmes,
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
        session.delete(fiche)
        session.commit()
        
        logger.info(f"✅ Fiche {fiche.numero_fiche} supprimée par {current_user.email}")
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

@router.post("/api/fiches/{fiche_id}/documents")
async def api_upload_document(
    fiche_id: int,
    type_document: str = Form(...),
    fichier: UploadFile = File(...),
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
        type_document=type_document,
        nom_fichier=fichier.filename,
        file_path=f"/static/uploads/budget/fiches/{fiche_id}/{fichier.filename}",
        taille_octets=len(content),
        uploaded_by_user_id=current_user.id
    )
    
    session.add(doc)
    session.commit()
    
    logger.info(f"✅ Document uploadé : {fichier.filename} pour fiche {fiche_id}")
    return {"ok": True, "id": doc.id, "filename": fichier.filename}


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
    Exporter une fiche technique en PDF
    Pour l'instant, génère un HTML imprimable
    """
    fiche = session.get(FicheTechnique, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche non trouvée")
    
    # Lignes budgétaires
    lignes = session.exec(
        select(LigneBudgetaire)
        .where(LigneBudgetaire.fiche_technique_id == fiche_id)
        .where(LigneBudgetaire.actif == True)
        .order_by(LigneBudgetaire.ordre)
    ).all()
    
    # Référentiels
    programme = session.get(Programme, fiche.programme_id)
    direction = session.get(Direction, fiche.direction_id) if fiche.direction_id else None
    natures = {n.id: n for n in session.exec(select(NatureDepense)).all()}
    activites = {a.id: a for a in session.exec(select(Activite)).all()}
    
    # Générer HTML pour impression
    from fastapi.responses import HTMLResponse
    from jinja2 import Template
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Fiche Technique {{ fiche.numero_fiche }}</title>
        <style>
            @page { size: A4; margin: 2cm; }
            body { font-family: Arial, sans-serif; font-size: 12px; }
            h1 { text-align: center; color: #333; }
            .header { text-align: center; margin-bottom: 30px; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background: #667eea; color: white; font-weight: bold; }
            .totaux { background: #f8f9fa; font-weight: bold; }
            .section { margin: 20px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #667eea; }
            .right { text-align: right; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>FICHE TECHNIQUE BUDGÉTAIRE</h1>
            <p><strong>{{ fiche.numero_fiche }}</strong></p>
            <p>Budget {{ fiche.annee_budget }}</p>
            <p>Programme: {{ programme.libelle }}</p>
            {% if direction %}<p>Direction: {{ direction.libelle }}</p>{% endif %}
        </div>
        
        <div class="section">
            <h3>Récapitulatif Budgétaire (FCFA)</h3>
            <table>
                <tr>
                    <th>Rubrique</th>
                    <th class="right">Montant</th>
                </tr>
                <tr>
                    <td>Budget Année Précédente ({{ fiche.annee_budget - 1 }})</td>
                    <td class="right">{{ "{:,.2f}".format(fiche.budget_anterieur) }}</td>
                </tr>
                <tr>
                    <td>Enveloppe Demandée</td>
                    <td class="right">{{ "{:,.2f}".format(fiche.enveloppe_demandee) }}</td>
                </tr>
                <tr>
                    <td>Compléments Demandés</td>
                    <td class="right">{{ "{:,.2f}".format(fiche.complement_demande) }}</td>
                </tr>
                <tr>
                    <td>Engagements de l'État</td>
                    <td class="right">{{ "{:,.2f}".format(fiche.engagement_etat) }}</td>
                </tr>
                <tr>
                    <td>Financement Bailleurs de Fonds</td>
                    <td class="right">{{ "{:,.2f}".format(fiche.financement_bailleurs) }}</td>
                </tr>
                <tr class="totaux">
                    <td><strong>BUDGET TOTAL DEMANDÉ</strong></td>
                    <td class="right"><strong>{{ "{:,.2f}".format(fiche.budget_total_demande) }}</strong></td>
                </tr>
            </table>
        </div>
        
        {% if lignes %}
        <div class="section">
            <h3>Détail des Dépenses</h3>
            <table>
                <tr>
                    <th>Nature</th>
                    <th>Libellé</th>
                    <th class="right">Budget N-1</th>
                    <th class="right">Demandé</th>
                    <th>Priorité</th>
                </tr>
                {% for ligne in lignes %}
                <tr>
                    <td>{{ natures[ligne.nature_depense_id].code }}</td>
                    <td>{{ ligne.libelle }}</td>
                    <td class="right">{{ "{:,.2f}".format(ligne.budget_n_moins_1) }}</td>
                    <td class="right">{{ "{:,.2f}".format(ligne.budget_demande) }}</td>
                    <td>{{ ligne.priorite }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}
        
        {% if fiche.note_justificative %}
        <div class="section">
            <h3>Note Justificative</h3>
            <p style="white-space: pre-wrap;">{{ fiche.note_justificative }}</p>
        </div>
        {% endif %}
        
        <div style="margin-top: 50px; text-align: right;">
            <p>Date d'édition: {{ fiche.created_at.strftime('%d/%m/%Y') }}</p>
            <p>Statut: {{ fiche.statut }}</p>
        </div>
        
        <script>
            window.onload = function() {
                window.print();
            }
        </script>
    </body>
    </html>
    """
    
    template = Template(html_template)
    html_content = template.render(
        fiche=fiche,
        lignes=lignes,
        programme=programme,
        direction=direction,
        natures=natures,
        activites=activites
    )
    
    return HTMLResponse(content=html_content)


# ============================================
# CONFÉRENCES BUDGÉTAIRES
# ============================================

@router.get("/conferences", response_class=HTMLResponse, name="budget_conferences")
def budget_conferences(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste des conférences budgétaires"""
    conferences = session.exec(
        select(ConferenceBudgetaire)
        .order_by(ConferenceBudgetaire.date_conference.desc())
    ).all()
    
    programmes = {p.id: p for p in session.exec(select(Programme)).all()}
    
    return templates.TemplateResponse(
        "pages/budget_conferences.html",
        get_template_context(
            request,
            conferences=conferences,
            programmes=programmes,
            current_user=current_user
        )
    )


@router.post("/api/conferences")
def api_create_conference(
    type_conference: str = Form(...),
    annee_budget: int = Form(...),
    programme_id: Optional[int] = Form(None),
    date_conference: str = Form(...),
    ordre_du_jour: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer une conférence budgétaire"""
    # Générer numéro
    count = session.exec(
        select(func.count(ConferenceBudgetaire.id))
        .where(ConferenceBudgetaire.annee_budget == annee_budget)
        .where(ConferenceBudgetaire.type_conference == type_conference)
    ).one()
    
    type_code = "INT" if type_conference == "Interne" else "MIN"
    numero = f"CB-{annee_budget}-{type_code}-{count + 1:03d}"
    
    conference = ConferenceBudgetaire(
        numero_conference=numero,
        type_conference=type_conference,
        annee_budget=annee_budget,
        programme_id=programme_id,
        date_conference=datetime.strptime(date_conference, '%Y-%m-%d').date(),
        ordre_du_jour=ordre_du_jour,
        organisateur_user_id=current_user.id
    )
    
    session.add(conference)
    session.commit()
    
    logger.info(f"✅ Conférence créée : {numero}")
    return {"ok": True, "id": conference.id, "numero": numero}


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

