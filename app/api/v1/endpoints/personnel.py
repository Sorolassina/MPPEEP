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
import re

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

@router.get("/aide", response_class=HTMLResponse, name="aide_personnel")
def aide_personnel(request: Request):
    """Page d'aide pour le module Personnel"""
    return templates.TemplateResponse(
        "pages/aide_personnel.html",
        get_template_context(request)
    )


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
    date_recrutement: str = Form(...),  # Obligatoire
    date_prise_service: str = Form(...),  # Obligatoire
    grade_id: str = Form(...),  # Obligatoire
    programme_id: str = Form(...),  # Obligatoire
    direction_id: str = Form(...),  # Obligatoire
    service_id: str = Form(...),  # Obligatoire
    fonction: str = Form(...),  # Obligatoire
    numero_cni: Optional[str] = Form(None),
    numero_passeport: Optional[str] = Form(None),
    nom_jeune_fille: Optional[str] = Form(None),
    date_naissance: Optional[str] = Form(None),
    lieu_naissance: Optional[str] = Form(None),
    nationalite: Optional[str] = Form(None),
    sexe: Optional[str] = Form(None),
    situation_familiale: Optional[str] = Form(None),
    nombre_enfants: Optional[str] = Form(None),  # Reçu comme string du formulaire
    email_professionnel: Optional[str] = Form(None),
    email_personnel: Optional[str] = Form(None),
    telephone_1: Optional[str] = Form(None),
    telephone_2: Optional[str] = Form(None),
    adresse: Optional[str] = Form(None),
    ville: Optional[str] = Form(None),
    code_postal: Optional[str] = Form(None),
    date_depart_retraite_prevue: Optional[str] = Form(None),
    position_administrative: Optional[str] = Form(None),
    echelon: Optional[str] = Form(None),  # Reçu comme string du formulaire
    indice: Optional[str] = Form(None),  # Reçu comme string du formulaire
    solde_conges_annuel: Optional[str] = Form(None),  # Reçu comme string du formulaire
    conges_annee_en_cours: Optional[str] = Form(None),  # Reçu comme string du formulaire
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouvel agent avec photo optionnelle"""
    
    def parse_int_or_none(value: Optional[str]) -> Optional[int]:
        """Convertit une chaîne en int, retourne None si vide ou invalide"""
        if value is None or value == "" or value.strip() == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def clean_str_or_none(value: Optional[str]) -> Optional[str]:
        """Convertit une chaîne vide en None, retourne la valeur sinon"""
        if value is None or value == "" or value.strip() == "":
            return None
        return value.strip()
    
    def validate_email(email: str) -> bool:
        """Valide le format d'un email"""
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return re.match(email_regex, email) is not None
    
    try:
        # Log des données reçues pour debug
        logger.info(f"📝 Création agent - Matricule: {matricule}, Nom: {nom}, Prénom: {prenom}")
        
        # Convertir les champs numériques obligatoires
        grade_id_int = int(grade_id) if grade_id and grade_id.strip() else None
        programme_id_int = int(programme_id) if programme_id and programme_id.strip() else None
        direction_id_int = int(direction_id) if direction_id and direction_id.strip() else None
        service_id_int = int(service_id) if service_id and service_id.strip() else None
        
        # Convertir les champs numériques optionnels
        nombre_enfants_int = parse_int_or_none(nombre_enfants)
        echelon_int = parse_int_or_none(echelon)
        indice_int = parse_int_or_none(indice)
        solde_conges_annuel_int = parse_int_or_none(solde_conges_annuel)
        conges_annee_en_cours_int = parse_int_or_none(conges_annee_en_cours)
        
        # Nettoyer les champs texte optionnels (convertir "" en None)
        numero_cni = clean_str_or_none(numero_cni)
        numero_passeport = clean_str_or_none(numero_passeport)
        nom_jeune_fille = clean_str_or_none(nom_jeune_fille)
        date_naissance = clean_str_or_none(date_naissance)
        lieu_naissance = clean_str_or_none(lieu_naissance)
        nationalite = clean_str_or_none(nationalite)
        sexe = clean_str_or_none(sexe)
        situation_familiale = clean_str_or_none(situation_familiale)
        email_professionnel = clean_str_or_none(email_professionnel)
        email_personnel = clean_str_or_none(email_personnel)
        telephone_1 = clean_str_or_none(telephone_1)
        telephone_2 = clean_str_or_none(telephone_2)
        adresse = clean_str_or_none(adresse)
        ville = clean_str_or_none(ville)
        code_postal = clean_str_or_none(code_postal)
        # date_recrutement, date_prise_service, fonction, grade_id, programme_id, direction_id, service_id sont obligatoires
        date_depart_retraite_prevue = clean_str_or_none(date_depart_retraite_prevue)
        position_administrative = clean_str_or_none(position_administrative)
        notes = clean_str_or_none(notes)
        
        # Valider les champs obligatoires
        if not date_recrutement or date_recrutement.strip() == "":
            raise HTTPException(400, "Le champ 'Date de recrutement' est obligatoire")
        
        if not date_prise_service or date_prise_service.strip() == "":
            raise HTTPException(400, "Le champ 'Date de prise de service' est obligatoire")
        
        if not grade_id_int:
            raise HTTPException(400, "Le champ 'Grade' est obligatoire")
        
        if not programme_id_int:
            raise HTTPException(400, "Le champ 'Programme' est obligatoire")
        
        if not direction_id_int:
            raise HTTPException(400, "Le champ 'Direction' est obligatoire")
        
        if not service_id_int:
            raise HTTPException(400, "Le champ 'Service' est obligatoire")
        
        if not fonction or fonction.strip() == "":
            raise HTTPException(400, "Le champ 'Fonction' est obligatoire")
        
        # Valider les emails s'ils sont remplis
        if email_professionnel and not validate_email(email_professionnel):
            raise HTTPException(400, "L'email professionnel n'est pas valide. Format attendu: exemple@domaine.com")
        
        if email_personnel and not validate_email(email_personnel):
            raise HTTPException(400, "L'email personnel n'est pas valide. Format attendu: exemple@domaine.com")
        
        # Vérifier que le matricule est unique
        existing = session.exec(
            select(AgentComplet).where(AgentComplet.matricule == matricule)
        ).first()
        
        if existing:
            logger.warning(f"⚠️ Matricule {matricule} existe déjà")
            raise HTTPException(400, "Ce matricule existe déjà")
        
        # Préparer les données de l'agent (utiliser les versions converties pour les entiers)
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
            "nombre_enfants": nombre_enfants_int,
            "email_professionnel": email_professionnel,
            "email_personnel": email_personnel,
            "telephone_1": telephone_1,
            "telephone_2": telephone_2,
            "adresse": adresse,
            "ville": ville,
            "code_postal": code_postal,
            "position_administrative": position_administrative,
            "grade_id": grade_id_int,
            "echelon": echelon_int,
            "indice": indice_int,
            "service_id": service_id_int,
            "direction_id": direction_id_int,
            "programme_id": programme_id_int,
            "fonction": fonction,
            "solde_conges_annuel": solde_conges_annuel_int,
            "conges_annee_en_cours": conges_annee_en_cours_int,
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
        
    except HTTPException as e:
        # Re-lancer les HTTPException (erreurs de validation) sans modification
        session.rollback()
        logger.warning(f"⚠️ Erreur validation agent: {e.detail}")
        raise
    except ValueError as e:
        # Erreur de validation (ex: enum invalide)
        session.rollback()
        error_msg = str(e)
        
        # Extraire les informations utiles pour l'utilisateur
        if "is not among the defined enum values" in error_msg:
            # Parser le message d'erreur pour extraire le nom du champ et les valeurs possibles
            if "Enum name:" in error_msg:
                parts = error_msg.split("Enum name:")
                if len(parts) > 1:
                    enum_info = parts[1].split(".")
                    field_name = enum_info[0].strip()
                    
                    # Mapper les noms de champs techniques aux noms français
                    field_names_fr = {
                        "situationfamiliale": "Situation familiale",
                        "sexe": "Sexe",
                        "positionadministrative": "Position administrative"
                    }
                    
                    field_name_fr = field_names_fr.get(field_name.lower(), field_name)
                    
                    # Extraire les valeurs possibles si disponibles
                    if "Possible values:" in error_msg:
                        values_part = error_msg.split("Possible values:")[1].strip()
                        user_message = f"Le champ '{field_name_fr}' a une valeur invalide. Veuillez sélectionner une valeur dans la liste déroulante."
                    else:
                        user_message = f"Le champ '{field_name_fr}' a une valeur invalide."
                else:
                    user_message = "Une valeur sélectionnée est invalide. Veuillez vérifier tous les champs."
            else:
                user_message = "Une valeur sélectionnée est invalide. Veuillez vérifier tous les champs."
        else:
            user_message = f"Erreur de validation: {error_msg}"
        
        logger.warning(f"⚠️ Erreur validation enum: {error_msg}")
        raise HTTPException(400, user_message)
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur création agent: {e}")
        raise HTTPException(500, f"Erreur serveur: {str(e)}")


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


@router.post("/api/agents/{agent_id}/create-user", name="api_create_user_from_agent")
async def api_create_user_from_agent(
    agent_id: int,
    request_body: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Créer un compte utilisateur pour un agent
    
    Args:
        agent_id: ID de l'agent
        request_body: Corps JSON avec l'email et optionnellement le password
    
    Returns:
        Informations du compte créé avec mot de passe (fourni ou généré)
    """
    email = request_body.get('email', '').strip()
    custom_password = request_body.get('password', '').strip()
    
    if not email:
        raise HTTPException(400, "L'email est obligatoire")
    
    # Valider le format email
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        raise HTTPException(400, "Format email invalide")
    
    # Valider le mot de passe personnalisé s'il est fourni
    if custom_password and len(custom_password) < 8:
        raise HTTPException(400, "Le mot de passe doit contenir au moins 8 caractères")
    
    try:
        # Vérifier que l'agent existe
        agent = session.get(AgentComplet, agent_id)
        if not agent:
            raise HTTPException(404, "Agent non trouvé")
        
        # Vérifier que l'agent n'a pas déjà un compte utilisateur
        if agent.user_id:
            existing_user = session.get(User, agent.user_id)
            if existing_user:
                raise HTTPException(400, f"Cet agent a déjà un compte utilisateur ({existing_user.email})")
        
        # Vérifier que l'email n'est pas déjà utilisé
        existing_user = session.exec(
            select(User).where(User.email == email)
        ).first()
        
        if existing_user:
            raise HTTPException(400, "Cet email est déjà utilisé par un autre compte")
        
        # Utiliser le mot de passe fourni ou en générer un
        if custom_password:
            password_to_use = custom_password
            password_was_generated = False
        else:
            password_to_use = secrets.token_urlsafe(12)
            password_was_generated = True
        
        # Créer l'utilisateur
        from app.core.security import get_password_hash
        
        new_user = User(
            email=email,
            full_name=f"{agent.prenom} {agent.nom}",
            hashed_password=get_password_hash(password_to_use),
            is_active=True,
            is_superuser=False,
            type_user="user",  # Type par défaut
            agent_id=agent.id,
            profile_picture=agent.photo_path
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        # Mettre à jour l'agent avec l'ID du user
        agent.user_id = new_user.id
        session.add(agent)
        session.commit()
        
        logger.info(f"✅ Compte utilisateur créé pour l'agent {agent.matricule} - Email: {email}")
        
        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="create",
            target_type="user",
            description=f"Création compte utilisateur pour {agent.prenom} {agent.nom} ({agent.matricule})",
            target_id=new_user.id,
            icon="👤➕"
        )
        
        return {
            "ok": True,
            "user_id": new_user.id,
            "email": email,
            "temporary_password": password_to_use,
            "password_was_generated": password_was_generated,
            "agent_id": agent.id
        }
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur création utilisateur: {e}")
        raise HTTPException(500, f"Erreur serveur: {str(e)}")


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

