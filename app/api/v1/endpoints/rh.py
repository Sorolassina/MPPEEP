# app/api/v1/endpoints/rh.py
import secrets
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.api.v1.endpoints.auth import get_current_user
from app.core.enums import ActeAdministratifType, RequestType, WorkflowState
from app.core.logging_config import get_logger

# Imports locaux
from app.db.session import get_session
from app.models.personnel import Service
from app.models.rh import Agent, Grade, HRRequest, HRRequestBase, WorkflowHistory
from app.models.user import User
from app.services.activity_service import ActivityService
from app.services.rh import RHService
from app.templates import get_template_context, templates

logger = get_logger(__name__)

router = APIRouter()

# ============================================
# PAGES HTML
# ============================================


@router.get("/", response_class=HTMLResponse, name="rh_home")
def rh_home(request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Page principale RH avec KPIs, graphiques et liste des demandes
    Filtre les demandes selon les rôles personnalisés de l'utilisateur
    """
    from app.services.hierarchy_service import HierarchyService

    # Récupérer les demandes en attente de validation par l'utilisateur (nouvelle logique)
    pending_requests = HierarchyService.get_pending_requests_for_user(session, current_user.id)

    # Récupérer aussi les 20 dernières demandes pour vue d'ensemble
    all_demandes = session.exec(select(HRRequest).order_by(HRRequest.created_at.desc()).limit(20)).all()

    return templates.TemplateResponse(
        "pages/rh.html",
        get_template_context(
            request, demandes=all_demandes, pending_requests=pending_requests, WorkflowState=WorkflowState
        ),
    )


@router.get("/demandes/new", response_class=HTMLResponse, name="rh_new_demande")
def rh_new_demande(
    request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """
    Formulaire de création d'une nouvelle demande
    Charge les types de demandes personnalisés depuis la configuration
    """
    from app.models.personnel import AgentComplet
    from app.models.workflow_config import RequestTypeCustom

    # Récupérer l'agent correspondant à l'utilisateur connecté
    agent = None
    if current_user.agent_id:
        agent = session.get(AgentComplet, current_user.agent_id)

    # Récupérer les types de demandes personnalisés actifs
    request_types = session.exec(
        select(RequestTypeCustom)
        .where(RequestTypeCustom.actif)
        .order_by(RequestTypeCustom.categorie, RequestTypeCustom.ordre_affichage)
    ).all()

    # Grouper par catégorie pour un meilleur affichage
    types_by_category = {}
    for rt in request_types:
        cat = rt.categorie or "Autre"
        if cat not in types_by_category:
            types_by_category[cat] = []
        types_by_category[cat].append(rt)

    return templates.TemplateResponse(
        "pages/rh_demande_new.html",
        get_template_context(
            request,
            RequestType=RequestType,  # Garde pour compatibilité si utilisé ailleurs
            ActeAdministratifType=ActeAdministratifType,
            request_types_custom=request_types,
            types_by_category=types_by_category,
            agent=agent,  # Agent de l'utilisateur connecté
            current_user=current_user,
        ),
    )


@router.get("/demandes/{request_id}", response_class=HTMLResponse, name="rh_demande_detail")
def rh_demande_detail(request: Request, request_id: int, session: Session = Depends(get_session)):
    """
    Détail d'une demande avec timeline et actions workflow
    """
    from app.services.hierarchy_service import HierarchyService

    req = session.get(HRRequest, request_id)
    if not req:
        raise HTTPException(404, "Demande introuvable")

    # Récupérer l'historique
    history = session.exec(
        select(WorkflowHistory).where(WorkflowHistory.request_id == request_id).order_by(WorkflowHistory.acted_at)
    ).all()

    # Récupérer les prochaines étapes possibles (nouvelle logique)
    next_steps = RHService.next_states_for(session, request_id)

    # Récupérer le circuit complet avec les validateurs
    workflow_circuit = HierarchyService.get_workflow_circuit(session, request_id)
    workflow_info = HierarchyService.get_workflow_info(session, request_id)

    return templates.TemplateResponse(
        "pages/rh_demande_detail.html",
        get_template_context(
            request,
            req=req,
            history=history,
            next_steps=next_steps,
            workflow_circuit=workflow_circuit,
            workflow_info=workflow_info,
            WorkflowState=WorkflowState,
        ),
    )


@router.post("/demandes", response_class=HTMLResponse, name="rh_create_demande")
async def rh_create_demande(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    agent_id: int = Form(...),
    type: str = Form(...),
    objet: str = Form(...),
    motif: str | None = Form(None),
    acte_type: str | None = Form(None),
    date_debut: str | None = Form(None),
    date_fin: str | None = Form(None),
    nb_jours: str | None = Form(None),  # Reçu comme string pour gérer les valeurs vides
    document: UploadFile | None = File(None),
):
    """
    Traitement du formulaire de création d'une demande
    Gère l'upload de document et le type d'acte spécifique
    """
    try:
        from app.models.workflow_config import RequestTypeCustom

        # Vérifier que le type de demande existe et est actif
        request_type_config = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.code == type).where(RequestTypeCustom.actif)
        ).first()

        if not request_type_config:
            raise HTTPException(400, f"Type de demande '{type}' introuvable ou inactif")

        # Utiliser directement le code (plus besoin d'enum)
        request_type = type

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

        # Nettoyer les champs : convertir les chaînes vides en None
        # Cela résout le problème de parsing pour les actes administratifs
        if date_debut and date_debut.strip() == "":
            date_debut = None
        if date_fin and date_fin.strip() == "":
            date_fin = None
        if acte_type and acte_type.strip() == "":
            acte_type = None

        # Convertir nb_jours : string -> float, en gérant les valeurs vides
        nb_jours_float = None
        if nb_jours and nb_jours.strip():
            try:
                nb_jours_float = float(nb_jours)
            except ValueError:
                nb_jours_float = None

        # Créer le payload
        payload_data = {
            "type": request_type,
            "objet": objet,
            "motif": motif,
            "date_debut": date.fromisoformat(date_debut) if date_debut else None,
            "date_fin": date.fromisoformat(date_fin) if date_fin else None,
            "nb_jours": nb_jours_float,
            "acte_type": acte_type if acte_type else None,
            "document_joint": document_path,
            "document_filename": document_filename,
        }

        payload = HRRequestBase(**payload_data)

        # Créer la demande
        req = HRRequest(**payload.model_dump(), agent_id=agent_id)
        session.add(req)
        session.commit()
        session.refresh(req)

        logger.info(f"✅ Demande créée : ID {req.id}, Type: {req.type}, Agent: {agent_id}")

        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="create",
            target_type="demande_rh",
            description=f"Création d'une demande RH - {req.type} : {objet}",
            target_id=req.id,
            icon="📝",
        )

        # Récupérer les prochaines étapes (nouvelle signature)
        next_steps = RHService.next_states_for(session, req.id)

        # Rediriger vers la page de détail
        return templates.TemplateResponse(
            "pages/rh_demande_detail.html",
            get_template_context(request, req=req, history=[], next_steps=next_steps, WorkflowState=WorkflowState),
        )
    except Exception as e:
        logger.error(f"❌ Erreur création demande: {e}", exc_info=True)
        raise HTTPException(500, f"Erreur lors de la création de la demande: {e!s}")


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
def api_create_demande(payload: HRRequestBase, agent_id: int, session: Session = Depends(get_session)):
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
def submit_demande(request_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    """
    Soumettre une demande (passer de DRAFT à SUBMITTED)
    """
    try:
        updated = RHService.transition(
            session,
            request_id,
            WorkflowState.SUBMITTED,
            current_user.id,
            current_user.type_user,  # ✅ Utiliser type_user au lieu de role
        )
        return {"ok": True, "state": updated.current_state}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/demandes/{request_id}/to/{to_state}")
def transition_demande(
    request_id: int,
    to_state: WorkflowState,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """
    Faire avancer une demande dans le workflow
    """
    try:
        # TODO: Ajouter contrôle d'accès par rôle (N1/N2/DRH/DAF)
        updated = RHService.transition(
            session,
            request_id,
            to_state,
            current_user.id,
            current_user.type_user,  # ✅ Utiliser type_user
        )
        return {"ok": True, "state": updated.current_state}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/demandes/{request_id}/advance")
def rh_demande_advance(
    request_id: int,
    to_state: WorkflowState,
    comment: str | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),  # ✅ Dépendance correcte
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
            comment=comment,
        )

        # Log activité
        ActivityService.log_user_activity(
            session=session,
            user=current_user,
            action_type="update",
            target_type="demande_rh",
            description=f"Transition de la demande #{request_id} vers {to_state.value}",
            target_id=request_id,
            icon="✅",
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
    services = session.exec(select(Service)).all()
    return services


@router.get("/api/demandes/list")
def api_list_demandes(session: Session = Depends(get_session)):
    """
    Liste les demandes récentes (20 dernières)
    """
    try:
        demandes = session.exec(select(HRRequest).order_by(HRRequest.created_at.desc()).limit(20)).all()

        # Convertir en dict pour JSON
        result = []
        for d in demandes:
            result.append(
                {
                    "id": d.id,
                    "agent_id": d.agent_id,
                    "type": str(d.type) if d.type else "N/A",
                    "objet": d.objet or "",
                    "current_state": str(d.current_state) if d.current_state else "DRAFT",
                    "current_assignee_role": d.current_assignee_role or "",
                    "acte_type": d.acte_type or "",
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "has_document": bool(d.document_joint),
                }
            )

        logger.info(f"📋 Liste demandes : {len(result)} résultats")
        return result

    except Exception as e:
        logger.error(f"❌ Erreur liste demandes: {e}", exc_info=True)
        return []


@router.delete("/api/demandes/{request_id}")
def api_delete_demande(
    request_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)
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
    history_entries = session.exec(select(WorkflowHistory).where(WorkflowHistory.request_id == request_id)).all()
    for entry in history_entries:
        session.delete(entry)

    # Supprimer la demande
    type_demande = req.type
    objet_demande = req.objet
    session.delete(req)
    session.commit()

    logger.info(f"✅ Demande supprimée : ID {request_id}")

    # Log activité
    ActivityService.log_user_activity(
        session=session,
        user=current_user,
        action_type="delete",
        target_type="demande_rh",
        description=f"Suppression d'une demande RH - {type_demande} : {objet_demande}",
        target_id=request_id,
        icon="🗑️",
    )

    return {"ok": True, "message": "Demande supprimée avec succès"}
