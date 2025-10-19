# app/api/v1/endpoints/personnel.py
"""
Endpoints pour la gestion complète du personnel
"""
from typing import List, Optional
from datetime import datetime
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
from app.services.activity_service import ActivityService
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


@router.get("/{agent_id}/edit", response_class=HTMLResponse, name="personnel_edit")
def personnel_edit(
    agent_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page d'édition d'un agent"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    # Référentiels
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
            mode="edit",
            agent=agent,
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

@router.get("/api/agents", response_model=List[dict], name="list_agents_api")
def api_list_agents(
    session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
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
            "fonction": a.fonction,
            "actif": a.actif
        }
        for a in agents
    ]


@router.post("/api/agents", name="api_create_agent")
async def api_create_agent(
    matricule: str = Form(...),
    nom: str = Form(...),
    prenom: str = Form(...),
    numero_cni: Optional[str] = Form(None),
    numero_passeport: Optional[str] = Form(None),
    nom_jeune_fille: Optional[str] = Form(None),
    date_naissance: Optional[str] = Form(None),
    lieu_naissance: Optional[str] = Form(None),
    nationalite: Optional[str] = Form(None),
    sexe: Optional[str] = Form(None),
    situation_familiale: Optional[str] = Form(None),
    nombre_enfants: Optional[int] = Form(None),
    email_professionnel: Optional[str] = Form(None),
    email_personnel: Optional[str] = Form(None),
    telephone_1: Optional[str] = Form(None),
    telephone_2: Optional[str] = Form(None),
    adresse: Optional[str] = Form(None),
    ville: Optional[str] = Form(None),
    code_postal: Optional[str] = Form(None),
    date_recrutement: Optional[str] = Form(None),
    date_prise_service: Optional[str] = Form(None),
    date_depart_retraite_prevue: Optional[str] = Form(None),
    position_administrative: Optional[str] = Form(None),
    grade_id: Optional[int] = Form(None),
    echelon: Optional[int] = Form(None),
    indice: Optional[int] = Form(None),
    service_id: Optional[int] = Form(None),
    direction_id: Optional[int] = Form(None),
    programme_id: Optional[int] = Form(None),
    fonction: Optional[str] = Form(None),
    solde_conges_annuel: Optional[int] = Form(None),
    conges_annee_en_cours: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouvel agent avec photo optionnelle"""
    try:
        # Vérifier que le matricule est unique
        existing = session.exec(
            select(AgentComplet).where(AgentComplet.matricule == matricule)
        ).first()
        
        if existing:
            raise HTTPException(400, "Ce matricule existe déjà")
        
        # Préparer les données de l'agent
        agent_data = {
            "matricule": matricule,
            "nom": nom,
            "prenom": prenom,
            "numero_cni": numero_cni,
            "numero_passeport": numero_passeport,
            "nom_jeune_fille": nom_jeune_fille,
            "lieu_naissance": lieu_naissance,
            "nationalite": nationalite,
            "sexe": sexe,
            "situation_familiale": situation_familiale,
            "nombre_enfants": nombre_enfants,
            "email_professionnel": email_professionnel,
            "email_personnel": email_personnel,
            "telephone_1": telephone_1,
            "telephone_2": telephone_2,
            "adresse": adresse,
            "ville": ville,
            "code_postal": code_postal,
            "position_administrative": position_administrative,
            "grade_id": grade_id,
            "echelon": echelon,
            "indice": indice,
            "service_id": service_id,
            "direction_id": direction_id,
            "programme_id": programme_id,
            "fonction": fonction,
            "solde_conges_annuel": solde_conges_annuel,
            "conges_annee_en_cours": conges_annee_en_cours,
            "notes": notes
        }
        
        # Convertir les dates de string en date objects
        date_fields = ['date_naissance', 'date_recrutement', 'date_prise_service', 'date_depart_retraite_prevue']
        for field in date_fields:
            date_str = locals().get(field)
            if date_str:
                try:
                    agent_data[field] = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    agent_data[field] = None
            else:
                agent_data[field] = None
        
        # Gérer l'upload de photo
        photo_path = None
        if photo and photo.filename:
            # Créer le dossier pour les photos avec path_config
            from app.core.path_config import path_config
            photos_dir = path_config.UPLOADS_DIR / "photos" / "agents"
            photos_dir.mkdir(parents=True, exist_ok=True)
            
            # Générer un nom de fichier unique
            file_extension = photo.filename.split('.')[-1]
            unique_filename = f"{matricule}_{secrets.token_hex(8)}.{file_extension}"
            file_path = photos_dir / unique_filename
            
            # Sauvegarder le fichier
            content = await photo.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Générer l'URL avec ROOT_PATH
            relative_path = f"photos/agents/{unique_filename}"
            photo_path = path_config.get_file_url("uploads", relative_path)
            agent_data["photo_path"] = photo_path
        
        # Créer l'agent
        agent = AgentComplet(**agent_data)
        agent.created_by = current_user.id
        
        session.add(agent)
        session.commit()
        session.refresh(agent)
        
        logger.info(f"Agent créé: {agent.matricule} - {agent.nom} {agent.prenom}" + (" avec photo" if photo_path else ""))
        
        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="create",
            target_type="agent",
            description=f"Création de l'agent {agent.matricule} - {agent.nom} {agent.prenom}",
            target_id=agent.id,
            icon="👤"
        )
        
        return {"ok": True, "agent_id": agent.id}
        
    except HTTPException:
        # Re-lancer les HTTPException (erreurs de validation) sans modification
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur création agent: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")


@router.get("/api/agents/{agent_id}", name="get_agent_api")
def api_get_agent(
    agent_id: int,
    session: Session = Depends(get_session)
):
    """Récupérer un agent"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    
    return agent


@router.put("/api/agents/{agent_id}", name="api_update_agent")
async def api_update_agent(
    agent_id: int,
    matricule: Optional[str] = Form(None),
    nom: Optional[str] = Form(None),
    prenom: Optional[str] = Form(None),
    numero_cni: Optional[str] = Form(None),
    numero_passeport: Optional[str] = Form(None),
    nom_jeune_fille: Optional[str] = Form(None),
    date_naissance: Optional[str] = Form(None),
    lieu_naissance: Optional[str] = Form(None),
    nationalite: Optional[str] = Form(None),
    sexe: Optional[str] = Form(None),
    situation_familiale: Optional[str] = Form(None),
    nombre_enfants: Optional[int] = Form(None),
    email_professionnel: Optional[str] = Form(None),
    email_personnel: Optional[str] = Form(None),
    telephone_1: Optional[str] = Form(None),
    telephone_2: Optional[str] = Form(None),
    adresse: Optional[str] = Form(None),
    ville: Optional[str] = Form(None),
    code_postal: Optional[str] = Form(None),
    date_recrutement: Optional[str] = Form(None),
    date_prise_service: Optional[str] = Form(None),
    date_depart_retraite_prevue: Optional[str] = Form(None),
    position_administrative: Optional[str] = Form(None),
    grade_id: Optional[int] = Form(None),
    echelon: Optional[int] = Form(None),
    indice: Optional[int] = Form(None),
    service_id: Optional[int] = Form(None),
    direction_id: Optional[int] = Form(None),
    programme_id: Optional[int] = Form(None),
    fonction: Optional[str] = Form(None),
    solde_conges_annuel: Optional[int] = Form(None),
    conges_annee_en_cours: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un agent avec photo optionnelle"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    
    try:
        # Mettre à jour les champs fournis
        if matricule is not None: agent.matricule = matricule
        if nom is not None: agent.nom = nom
        if prenom is not None: agent.prenom = prenom
        if numero_cni is not None: agent.numero_cni = numero_cni
        if numero_passeport is not None: agent.numero_passeport = numero_passeport
        if nom_jeune_fille is not None: agent.nom_jeune_fille = nom_jeune_fille
        if lieu_naissance is not None: agent.lieu_naissance = lieu_naissance
        if nationalite is not None: agent.nationalite = nationalite
        if sexe is not None: agent.sexe = sexe
        if situation_familiale is not None: agent.situation_familiale = situation_familiale
        if nombre_enfants is not None: agent.nombre_enfants = nombre_enfants
        if email_professionnel is not None: agent.email_professionnel = email_professionnel
        if email_personnel is not None: agent.email_personnel = email_personnel
        if telephone_1 is not None: agent.telephone_1 = telephone_1
        if telephone_2 is not None: agent.telephone_2 = telephone_2
        if adresse is not None: agent.adresse = adresse
        if ville is not None: agent.ville = ville
        if code_postal is not None: agent.code_postal = code_postal
        if position_administrative is not None: agent.position_administrative = position_administrative
        if grade_id is not None: agent.grade_id = grade_id
        if echelon is not None: agent.echelon = echelon
        if indice is not None: agent.indice = indice
        if service_id is not None: agent.service_id = service_id
        if direction_id is not None: agent.direction_id = direction_id
        if programme_id is not None: agent.programme_id = programme_id
        if fonction is not None: agent.fonction = fonction
        if solde_conges_annuel is not None: agent.solde_conges_annuel = solde_conges_annuel
        if conges_annee_en_cours is not None: agent.conges_annee_en_cours = conges_annee_en_cours
        if notes is not None: agent.notes = notes
        
        # Convertir les dates
        date_fields = {
            'date_naissance': date_naissance,
            'date_recrutement': date_recrutement,
            'date_prise_service': date_prise_service,
            'date_depart_retraite_prevue': date_depart_retraite_prevue
        }
        for field_name, date_str in date_fields.items():
            if date_str:
                try:
                    setattr(agent, field_name, datetime.strptime(date_str, '%Y-%m-%d').date())
                except ValueError:
                    pass
        
        # Gérer la nouvelle photo
        if photo and photo.filename:
            from app.core.path_config import path_config
            
            # Supprimer l'ancienne photo si elle existe
            if agent.photo_path:
                # Extraire le chemin relatif de l'URL
                old_path = agent.photo_path.replace("/uploads/", "").replace(f"{settings.get_root_path}/uploads/", "")
                old_file = path_config.UPLOADS_DIR / old_path
                if old_file.exists():
                    old_file.unlink()
            
            # Sauvegarder la nouvelle photo
            photos_dir = path_config.UPLOADS_DIR / "photos" / "agents"
            photos_dir.mkdir(parents=True, exist_ok=True)
            
            file_extension = photo.filename.split('.')[-1]
            unique_filename = f"{agent.matricule}_{secrets.token_hex(8)}.{file_extension}"
            file_path = photos_dir / unique_filename
            
            content = await photo.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Générer l'URL avec ROOT_PATH
            relative_path = f"photos/agents/{unique_filename}"
            agent.photo_path = path_config.get_file_url("uploads", relative_path)
        
        agent.updated_by = current_user.id
        
        session.add(agent)
        session.commit()
        session.refresh(agent)
        
        logger.info(f"Agent mis à jour: {agent.matricule}")
        
        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="update",
            target_type="agent",
            description=f"Modification de l'agent {agent.matricule} - {agent.nom} {agent.prenom}",
            target_id=agent.id,
            icon="✏️"
        )
        
        return {"ok": True, "agent_id": agent.id}
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur mise à jour agent: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")


@router.delete("/api/agents/{agent_id}", name="delete_agent_api")
def api_delete_agent(
    agent_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Désactiver un agent (soft delete)"""
    agent = session.get(AgentComplet, agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    
    matricule = agent.matricule
    nom_complet = f"{agent.nom} {agent.prenom}"
    agent.actif = False
    agent.updated_by = current_user.id
    
    session.add(agent)
    session.commit()
    
    logger.info(f"Agent désactivé: {matricule}")
    
    # Log activité
    ActivityService.log_user_activity(
        session=session,
        user=current_user,
        action_type="delete",
        target_type="agent",
        description=f"Désactivation de l'agent {matricule} - {nom_complet}",
        target_id=agent_id,
        icon="🗑️"
    )
    
    return {"ok": True}


# ==========================================
# API ENDPOINTS - STRUCTURE (Programme/Direction/Service)
# ==========================================

@router.get("/api/programmes", response_model=List[dict], name="list_programmes_api")
def api_list_programmes(session: Session = Depends(get_session)):
    """Liste des programmes"""
    programmes = session.exec(
        select(Programme).where(Programme.actif == True).order_by(Programme.libelle)
    ).all()
    
    return [{"id": p.id, "code": p.code, "libelle": p.libelle} for p in programmes]


@router.get("/api/directions", response_model=List[dict], name="list_directions_api")
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


@router.get("/api/services", response_model=List[dict], name="get_services_api")
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

@router.get("/api/grades", response_model=List[dict], name="list_grades_api")
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

@router.post("/api/agents/{agent_id}/documents", name="upload_document_agent_api")
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


@router.delete("/api/documents/{document_id}", name="delete_document_agent_api")
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

