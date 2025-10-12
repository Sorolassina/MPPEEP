# app/api/v1/endpoints/personnel.py
"""
Endpoints pour la gestion complète du personnel
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func, or_
from pathlib import Path
import secrets

from app.db.session import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.personnel import (
    AgentComplet, Programme, Direction, Service,
    GradeComplet, DocumentAgent, HistoriqueCarriere, EvaluationAgent
)
from app.core.enums import (
    PositionAdministrative, SituationFamiliale, 
    TypeDocument, GradeCategory
)
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger
from fastapi import Request

logger = get_logger(__name__)
router = APIRouter()


# ==========================================
# PAGES HTML
# ==========================================

@router.get("/", response_class=HTMLResponse, name="personnel_home")
def personnel_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Page principale de gestion du personnel
    Affiche les statistiques et la liste du personnel
    """
    # Statistiques
    total_agents = session.exec(select(func.count(AgentComplet.id))).one()
    agents_actifs = session.exec(
        select(func.count(AgentComplet.id)).where(AgentComplet.actif == True)
    ).one()
    
    # Agents par catégorie
    agents_par_categorie = {}
    for cat in GradeCategory:
        count = session.exec(
            select(func.count(AgentComplet.id))
            .join(GradeComplet, AgentComplet.grade_id == GradeComplet.id)
            .where(GradeComplet.categorie == cat)
            .where(AgentComplet.actif == True)
        ).one()
        agents_par_categorie[cat.name] = count
    
    # Récupérer les 20 derniers agents
    agents = session.exec(
        select(AgentComplet)
        .where(AgentComplet.actif == True)
        .order_by(AgentComplet.created_at.desc())
        .limit(20)
    ).all()
    
    return templates.TemplateResponse(
        "pages/personnel.html",
        get_template_context(
            request,
            total_agents=total_agents,
            agents_actifs=agents_actifs,
            agents_par_categorie=agents_par_categorie,
            agents=agents,
            current_user=current_user
        )
    )


@router.get("/nouveau", response_class=HTMLResponse, name="personnel_nouveau")
def personnel_nouveau(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de création d'un nouvel agent"""
    # Récupérer les référentiels
    grades = session.exec(
        select(GradeComplet).where(GradeComplet.actif == True).order_by(GradeComplet.code)
    ).all()
    
    services = session.exec(
        select(Service).where(Service.actif == True).order_by(Service.libelle)
    ).all()
    
    directions = session.exec(
        select(Direction).where(Direction.actif == True).order_by(Direction.libelle)
    ).all()
    
    programmes = session.exec(
        select(Programme).where(Programme.actif == True).order_by(Programme.libelle)
    ).all()
    
    return templates.TemplateResponse(
        "pages/personnel_form.html",
        get_template_context(
            request,
            mode="create",
            grades=grades,
            services=services,
            directions=directions,
            programmes=programmes,
            PositionAdministrative=PositionAdministrative,
            SituationFamiliale=SituationFamiliale,
            current_user=current_user
        )
    )


@router.get("/{agent_id}", response_class=HTMLResponse, name="personnel_detail")
def personnel_detail(
    agent_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de détail d'un agent"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    # Récupérer le grade
    grade = session.get(GradeComplet, agent.grade_id) if agent.grade_id else None
    
    # Récupérer le service/direction/programme
    service = session.get(Service, agent.service_id) if agent.service_id else None
    direction = session.get(Direction, agent.direction_id) if agent.direction_id else None
    programme = session.get(Programme, agent.programme_id) if agent.programme_id else None
    
    # Documents
    documents = session.exec(
        select(DocumentAgent)
        .where(DocumentAgent.agent_id == agent_id)
        .where(DocumentAgent.actif == True)
        .order_by(DocumentAgent.uploaded_at.desc())
    ).all()
    
    # Historique de carrière
    historique = session.exec(
        select(HistoriqueCarriere)
        .where(HistoriqueCarriere.agent_id == agent_id)
        .order_by(HistoriqueCarriere.date_evenement.desc())
    ).all()
    
    # Évaluations
    evaluations = session.exec(
        select(EvaluationAgent)
        .where(EvaluationAgent.agent_id == agent_id)
        .order_by(EvaluationAgent.annee.desc())
    ).all()
    
    return templates.TemplateResponse(
        "pages/personnel_detail.html",
        get_template_context(
            request,
            agent=agent,
            grade=grade,
            service=service,
            direction=direction,
            programme=programme,
            documents=documents,
            historique=historique,
            evaluations=evaluations,
            current_user=current_user
        )
    )


# ==========================================
# API ENDPOINTS - CRUD AGENTS
# ==========================================

@router.get("/api/agents", response_model=List[dict])
def api_list_agents(
    session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    actif: Optional[bool] = Query(None)
):
    """Liste des agents avec pagination et recherche"""
    query = select(AgentComplet)
    
    if search:
        query = query.where(
            or_(
                AgentComplet.matricule.contains(search),
                AgentComplet.nom.contains(search),
                AgentComplet.prenom.contains(search)
            )
        )
    
    if actif is not None:
        query = query.where(AgentComplet.actif == actif)
    
    query = query.order_by(AgentComplet.nom, AgentComplet.prenom)
    query = query.offset(skip).limit(limit)
    
    agents = session.exec(query).all()
    
    return [
        {
            "id": a.id,
            "matricule": a.matricule,
            "nom": a.nom,
            "prenom": a.prenom,
            "email": a.email_professionnel,
            "actif": a.actif
        }
        for a in agents
    ]


@router.post("/api/agents")
def api_create_agent(
    agent_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouvel agent"""
    try:
        # Vérifier que le matricule est unique
        existing = session.exec(
            select(AgentComplet).where(AgentComplet.matricule == agent_data.get("matricule"))
        ).first()
        
        if existing:
            raise HTTPException(400, "Ce matricule existe déjà")
        
        agent = AgentComplet(**agent_data)
        agent.created_by = current_user.id
        
        session.add(agent)
        session.commit()
        session.refresh(agent)
        
        logger.info(f"Agent créé: {agent.matricule} - {agent.nom} {agent.prenom}")
        
        return {"ok": True, "agent_id": agent.id}
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur création agent: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")


@router.get("/api/agents/{agent_id}")
def api_get_agent(
    agent_id: int,
    session: Session = Depends(get_session)
):
    """Récupérer un agent"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    
    return agent


@router.put("/api/agents/{agent_id}")
def api_update_agent(
    agent_id: int,
    agent_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un agent"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    
    try:
        # Mettre à jour les champs
        for key, value in agent_data.items():
            if hasattr(agent, key) and key not in ["id", "created_at", "created_by"]:
                setattr(agent, key, value)
        
        agent.updated_by = current_user.id
        
        session.add(agent)
        session.commit()
        session.refresh(agent)
        
        logger.info(f"Agent mis à jour: {agent.matricule}")
        
        return {"ok": True, "agent_id": agent.id}
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur mise à jour agent: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")


@router.delete("/api/agents/{agent_id}")
def api_delete_agent(
    agent_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Désactiver un agent (soft delete)"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    
    agent.actif = False
    agent.updated_by = current_user.id
    
    session.add(agent)
    session.commit()
    
    logger.info(f"Agent désactivé: {agent.matricule}")
    
    return {"ok": True}


# ==========================================
# API ENDPOINTS - STRUCTURE (Programme/Direction/Service)
# ==========================================

@router.get("/api/programmes", response_model=List[dict])
def api_list_programmes(session: Session = Depends(get_session)):
    """Liste des programmes"""
    programmes = session.exec(
        select(Programme).where(Programme.actif == True).order_by(Programme.libelle)
    ).all()
    
    return [{"id": p.id, "code": p.code, "libelle": p.libelle} for p in programmes]


@router.get("/api/directions", response_model=List[dict])
def api_list_directions(
    session: Session = Depends(get_session),
    programme_id: Optional[int] = Query(None)
):
    """Liste des directions"""
    query = select(Direction).where(Direction.actif == True)
    
    if programme_id:
        query = query.where(Direction.programme_id == programme_id)
    
    query = query.order_by(Direction.libelle)
    
    directions = session.exec(query).all()
    
    return [{"id": d.id, "code": d.code, "libelle": d.libelle, "programme_id": d.programme_id} for d in directions]


@router.get("/api/services", response_model=List[dict])
def api_list_services(
    session: Session = Depends(get_session),
    direction_id: Optional[int] = Query(None)
):
    """Liste des services"""
    query = select(Service).where(Service.actif == True)
    
    if direction_id:
        query = query.where(Service.direction_id == direction_id)
    
    query = query.order_by(Service.libelle)
    
    services = session.exec(query).all()
    
    return [{"id": s.id, "code": s.code, "libelle": s.libelle, "direction_id": s.direction_id} for s in services]


# ==========================================
# API ENDPOINTS - GRADES
# ==========================================

@router.get("/api/grades", response_model=List[dict])
def api_list_grades(
    session: Session = Depends(get_session),
    categorie: Optional[str] = Query(None)
):
    """Liste des grades"""
    query = select(GradeComplet).where(GradeComplet.actif == True)
    
    if categorie:
        query = query.where(GradeComplet.categorie == categorie)
    
    query = query.order_by(GradeComplet.code)
    
    grades = session.exec(query).all()
    
    return [
        {
            "id": g.id,
            "code": g.code,
            "libelle": g.libelle,
            "categorie": g.categorie.value if g.categorie else None
        }
        for g in grades
    ]


# ==========================================
# API ENDPOINTS - DOCUMENTS
# ==========================================

@router.post("/api/agents/{agent_id}/documents")
async def api_upload_document(
    agent_id: int,
    type_document: TypeDocument = Form(...),
    titre: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Uploader un document pour un agent"""
    # Vérifier que l'agent existe
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    
    try:
        # Créer le dossier de documents
        upload_dir = Path("uploads/personnel") / str(agent_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Générer un nom de fichier unique
        file_extension = Path(file.filename).suffix
        unique_filename = f"{secrets.token_hex(16)}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Sauvegarder le fichier
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Créer l'entrée en base
        document = DocumentAgent(
            agent_id=agent_id,
            type_document=type_document,
            titre=titre,
            description=description,
            file_path=str(file_path),
            file_name=file.filename,
            file_size=len(content),
            file_type=file.content_type,
            uploaded_by=current_user.id
        )
        
        session.add(document)
        session.commit()
        session.refresh(document)
        
        logger.info(f"Document uploadé pour agent {agent_id}: {titre}")
        
        return {"ok": True, "document_id": document.id}
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur upload document: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")


@router.delete("/api/documents/{document_id}")
def api_delete_document(
    document_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un document"""
    document = session.get(DocumentAgent, document_id)
    if not document:
        raise HTTPException(404, "Document non trouvé")
    
    document.actif = False
    session.add(document)
    session.commit()
    
    logger.info(f"Document désactivé: {document_id}")
    
    return {"ok": True}

