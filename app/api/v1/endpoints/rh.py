# app/api/v1/endpoints/rh.py
from fastapi import APIRouter, Depends, Request, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session, select
from datetime import date
from typing import Optional
import os
import secrets
from pathlib import Path

# Imports locaux
from app.db.session import get_session
from app.models.rh import (
    Agent, Grade, ServiceDept,
    HRRequest, HRRequestBase, WorkflowStep, WorkflowHistory
)
from app.core.enums import RequestType, WorkflowState, ActeAdministratifType
from app.services.rh import RHService
from app.api.v1.endpoints.auth import get_current_user
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ============================================
# PAGES HTML
# ============================================

@router.get("/", response_class=HTMLResponse, name="rh_home")
def rh_home(request: Request, session: Session = Depends(get_session)):
    """
    Page principale RH avec KPIs, graphiques et liste des demandes
    """
    # Récupérer les 20 dernières demandes
    demandes = session.exec(
        select(HRRequest)
        .order_by(HRRequest.created_at.desc())
        .limit(20)
    ).all()
    
    return templates.TemplateResponse(
        "pages/rh.html",
        get_template_context(request, demandes=demandes, WorkflowState=WorkflowState)
    )


@router.get("/demandes/new", response_class=HTMLResponse, name="rh_new_demande")
def rh_new_demande(request: Request):
    """
    Formulaire de création d'une nouvelle demande
    """
    return templates.TemplateResponse(
        "pages/rh_demande_new.html",
        get_template_context(
            request,
            RequestType=RequestType,
            ActeAdministratifType=ActeAdministratifType
        )
    )


@router.get("/demandes/{request_id}", response_class=HTMLResponse, name="rh_demande_detail")
def rh_demande_detail(request: Request, request_id: int, session: Session = Depends(get_session)):
    """
    Détail d'une demande avec timeline et actions workflow
    """
    req = session.get(HRRequest, request_id)
    if not req:
        raise HTTPException(404, "Demande introuvable")
    
    # Récupérer l'historique
    history = session.exec(
        select(WorkflowHistory)
        .where(WorkflowHistory.request_id == request_id)
        .order_by(WorkflowHistory.acted_at)
    ).all()
    
    # Récupérer les prochaines étapes possibles
    next_steps = RHService.next_states_for(session, req.type, req.current_state)
    
    return templates.TemplateResponse(
        "pages/rh_demande_detail.html",
        get_template_context(
            request,
            req=req,
            history=history,
            next_steps=next_steps,
            WorkflowState=WorkflowState
        )
    )


@router.post("/demandes", response_class=HTMLResponse, name="rh_create_demande")
async def rh_create_demande(
    request: Request,
    session: Session = Depends(get_session),
    agent_id: int = Form(...),
    type: str = Form(...),
    objet: str = Form(...),
    motif: Optional[str] = Form(None),
    acte_type: Optional[str] = Form(None),
    date_debut: Optional[str] = Form(None),
    date_fin: Optional[str] = Form(None),
    nb_jours: Optional[float] = Form(None),
    document: Optional[UploadFile] = File(None),
):
    """
    Traitement du formulaire de création d'une demande
    Gère l'upload de document et le type d'acte spécifique
    """
    try:
        # Convertir le type en enum
        request_type = RequestType(type)
        
        # Gérer l'upload de fichier
        document_path = None
        document_filename = None
        
        if document and document.filename:
            # Créer le dossier uploads/rh si nécessaire
            upload_dir = Path("uploads/rh")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Générer un nom de fichier unique
            file_extension = Path(document.filename).suffix
            unique_filename = f"{secrets.token_hex(16)}{file_extension}"
            file_path = upload_dir / unique_filename
            
            # Sauvegarder le fichier
            with open(file_path, "wb") as buffer:
                content = await document.read()
                buffer.write(content)
            
            document_path = str(file_path)
            document_filename = document.filename
            
            logger.info(f"📁 Document uploadé : {document_filename} → {document_path}")
        
        # Créer le payload
        payload_data = {
            "type": request_type,
            "objet": objet,
            "motif": motif,
            "date_debut": date.fromisoformat(date_debut) if date_debut else None,
            "date_fin": date.fromisoformat(date_fin) if date_fin else None,
            "nb_jours": nb_jours,
            "acte_type": acte_type if acte_type else None,
            "document_joint": document_path,
            "document_filename": document_filename
        }
        
        payload = HRRequestBase(**payload_data)
        
        # Créer la demande
        req = HRRequest(**payload.model_dump(), agent_id=agent_id)
        session.add(req)
        session.commit()
        session.refresh(req)
        
        logger.info(f"✅ Demande créée : ID {req.id}, Type: {req.type}, Agent: {agent_id}")
        
        # Récupérer les prochaines étapes
        next_steps = RHService.next_states_for(session, req.type, req.current_state)
        
        # Rediriger vers la page de détail
        return templates.TemplateResponse(
            "pages/rh_demande_detail.html",
            get_template_context(
                request,
                req=req,
                history=[],
                next_steps=next_steps,
                WorkflowState=WorkflowState
            )
        )
    except Exception as e:
        logger.error(f"❌ Erreur création demande: {e}", exc_info=True)
        raise HTTPException(500, f"Erreur lors de la création de la demande: {str(e)}")


# ============================================
# API REST JSON
# ============================================

@router.get("/api/kpis")
def api_kpis(session: Session = Depends(get_session)):
    """
    KPIs RH (JSON)
    """
    return RHService.kpis(session)


@router.get("/api/evolution")
def api_evolution(session: Session = Depends(get_session)):
    """
    Évolution des effectifs par année (JSON)
    """
    return RHService.evolution_par_annee(session)


@router.get("/api/grade")
def api_par_grade(session: Session = Depends(get_session)):
    """
    Répartition par grade (JSON)
    """
    return RHService.repartition_par_grade(session)


@router.get("/api/service")
def api_par_service(session: Session = Depends(get_session)):
    """
    Répartition par service (JSON)
    """
    return RHService.repartition_par_service(session)


@router.get("/api/satisfaction-besoins")
def api_satisfaction_besoins(session: Session = Depends(get_session)):
    """
    Satisfaction des besoins (JSON)
    """
    return RHService.satisfaction_besoins(session)


@router.get("/api/demandes/{request_id}", response_model=HRRequest)
def api_get_demande(request_id: int, session: Session = Depends(get_session)):
    """
    Récupérer une demande (API JSON)
    """
    req = session.get(HRRequest, request_id)
    if not req:
        raise HTTPException(404, "Demande introuvable")
    return req


@router.post("/api/demandes", response_model=HRRequest)
def api_create_demande(
    payload: HRRequestBase,
    agent_id: int,
    session: Session = Depends(get_session)
):
    """
    Créer une demande via API JSON
    """
    req = HRRequest(**payload.model_dump(), agent_id=agent_id)
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


# ============================================
# WORKFLOW - TRANSITIONS
# ============================================

@router.post("/demandes/{request_id}/submit")
def submit_demande(
    request_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Soumettre une demande (passer de DRAFT à SUBMITTED)
    """
    try:
        updated = RHService.transition(
            session,
            request_id,
            WorkflowState.SUBMITTED,
            current_user.id,
            current_user.type_user  # ✅ Utiliser type_user au lieu de role
        )
        return {"ok": True, "state": updated.current_state}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/demandes/{request_id}/to/{to_state}")
def transition_demande(
    request_id: int,
    to_state: WorkflowState,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Faire avancer une demande dans le workflow
    """
    try:
        # TODO: Ajouter contrôle d'accès par rôle (N1/DRH/DG)
        updated = RHService.transition(
            session,
            request_id,
            to_state,
            current_user.id,
            current_user.type_user  # ✅ Utiliser type_user
        )
        return {"ok": True, "state": updated.current_state}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/demandes/{request_id}/advance")
def rh_demande_advance(
    request_id: int,
    to_state: WorkflowState,
    comment: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)  # ✅ Dépendance correcte
):
    """
    Avancer dans le workflow depuis la page détail (POST en JSON)
    """
    try:
        updated = RHService.transition(
            session,
            request_id,
            to_state,
            acted_by_user_id=current_user.id,
            acted_by_role=current_user.type_user,  # ✅ Utiliser type_user
            comment=comment
        )
        return {"ok": True, "state": updated.current_state}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ============================================
# CRUD RÉFÉRENTIELS (Agents, Grades, Services)
# ============================================

@router.get("/api/agents")
def api_list_agents(session: Session = Depends(get_session)):
    """
    Liste tous les agents
    """
    agents = session.exec(select(Agent)).all()
    return agents


@router.get("/api/grades")
def api_list_grades(session: Session = Depends(get_session)):
    """
    Liste tous les grades
    """
    grades = session.exec(select(Grade)).all()
    return grades


@router.get("/api/services")
def api_list_services(session: Session = Depends(get_session)):
    """
    Liste tous les services
    """
    services = session.exec(select(ServiceDept)).all()
    return services


@router.get("/api/demandes/list")
def api_list_demandes(
    session: Session = Depends(get_session)
):
    """
    Liste les demandes récentes (20 dernières)
    """
    try:
        demandes = session.exec(
            select(HRRequest)
            .order_by(HRRequest.created_at.desc())
            .limit(20)
        ).all()
        
        # Convertir en dict pour JSON
        result = []
        for d in demandes:
            result.append({
                "id": d.id,
                "agent_id": d.agent_id,
                "type": str(d.type) if d.type else "N/A",
                "objet": d.objet or "",
                "current_state": str(d.current_state) if d.current_state else "DRAFT",
                "current_assignee_role": d.current_assignee_role or "",
                "acte_type": d.acte_type or "",
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "has_document": bool(d.document_joint)
            })
        
        logger.info(f"📋 Liste demandes : {len(result)} résultats")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur liste demandes: {e}", exc_info=True)
        return []


@router.delete("/api/demandes/{request_id}")
def api_delete_demande(
    request_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Supprimer une demande (seulement si DRAFT ou si admin)
    """
    req = session.get(HRRequest, request_id)
    if not req:
        raise HTTPException(404, "Demande introuvable")
    
    # Vérifier les permissions
    # Seulement DRAFT ou admin peut supprimer
    if req.current_state != WorkflowState.DRAFT and not current_user.is_admin:
        raise HTTPException(403, "Impossible de supprimer une demande en cours de traitement")
    
    # Supprimer le document associé si présent
    if req.document_joint:
        try:
            file_path = Path(req.document_joint)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"🗑️ Document supprimé : {req.document_joint}")
        except Exception as e:
            logger.warning(f"⚠️ Impossible de supprimer le document : {e}")
    
    # Supprimer les entrées d'historique
    history_entries = session.exec(
        select(WorkflowHistory).where(WorkflowHistory.request_id == request_id)
    ).all()
    for entry in history_entries:
        session.delete(entry)
    
    # Supprimer la demande
    session.delete(req)
    session.commit()
    
    logger.info(f"✅ Demande supprimée : ID {request_id}")
    
    return {"ok": True, "message": "Demande supprimée avec succès"}
