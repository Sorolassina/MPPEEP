"""
Endpoints génériques pour la gestion des demandes dans tous les modules
Utilise le système de workflow personnalisé
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select

from app.api.v1.endpoints.auth import get_current_user
from app.core.enums import WorkflowState
from app.core.logging_config import get_logger
from app.db.session import get_session
from app.models.generic_request import GenericRequest, GenericWorkflowHistory
from app.models.personnel import AgentComplet
from app.models.user import User
from app.models.workflow_config import RequestTypeCustom
from app.services.activity_service import ActivityService
from app.services.generic_request_service import GenericRequestService
from app.templates import get_template_context, templates

logger = get_logger(__name__)

router = APIRouter()


@router.get("/{module}/list", response_class=HTMLResponse, name="generic_requests_list")
def generic_requests_list(
    request: Request,
    module: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Liste des demandes pour un module donné
    """
    # Vérifier l'accès au module
    if not current_user.can_access_module(module) and not current_user.is_guest:
        from fastapi.responses import RedirectResponse

        return RedirectResponse(
            url=request.url_for("access_denied").include_query_params(module=module), status_code=302
        )

    # Récupérer les demandes en attente de validation par l'utilisateur
    pending_requests = GenericRequestService.get_pending_requests_for_user(session, current_user.id, module)

    # Récupérer aussi les 20 dernières demandes pour vue d'ensemble
    all_demandes = (
        session.exec(select(GenericRequest).where(GenericRequest.module == module).order_by(GenericRequest.created_at.desc()).limit(20))
        .all()
    )

    # Données de démonstration pour les invités
    if current_user.is_guest:
        all_demandes = []
        pending_requests = []

    return templates.TemplateResponse(
        "pages/generic_requests_list.html",
        get_template_context(
            request,
            module=module,
            demandes=all_demandes,
            pending_requests=pending_requests,
            WorkflowState=WorkflowState,
            current_user=current_user,
        ),
    )


@router.get("/{module}/new", response_class=HTMLResponse, name="generic_request_new")
def generic_request_new(
    request: Request,
    module: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Formulaire de création d'une nouvelle demande pour un module
    Charge les types de demandes personnalisés pour ce module
    """
    # Récupérer l'agent correspondant à l'utilisateur connecté
    agent = None
    if current_user.agent_id:
        agent = session.get(AgentComplet, current_user.agent_id)

    # Récupérer les types de demandes personnalisés actifs pour ce module
    # On utilise la catégorie pour filtrer par module
    request_types = session.exec(
        select(RequestTypeCustom)
        .where(RequestTypeCustom.actif)
        .where(RequestTypeCustom.categorie == module.upper())
        .order_by(RequestTypeCustom.ordre_affichage)
    ).all()

    # Si aucun type trouvé pour ce module, récupérer tous les types actifs
    if not request_types:
        request_types = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.actif).order_by(RequestTypeCustom.ordre_affichage)
        ).all()

    return templates.TemplateResponse(
        "pages/generic_request_new.html",
        get_template_context(
            request,
            module=module,
            agent=agent,
            request_types=request_types,
            current_user=current_user,
        ),
    )


@router.get("/{module}/{request_id}/detail", response_class=HTMLResponse, name="generic_request_detail")
def generic_request_detail(
    request: Request,
    module: str,
    request_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Détail d'une demande avec timeline et actions workflow
    """
    req = session.get(GenericRequest, request_id)
    if not req:
        raise HTTPException(404, "Demande introuvable")

    # Vérifier que la demande appartient au module
    if req.module != module:
        raise HTTPException(404, "Demande introuvable pour ce module")

    # Récupérer l'historique
    history = (
        session.exec(
            select(GenericWorkflowHistory)
            .where(GenericWorkflowHistory.request_id == request_id)
            .order_by(GenericWorkflowHistory.acted_at)
        )
        .all()
    )

    # Récupérer les prochaines étapes possibles
    next_steps = GenericRequestService.next_states_for(session, request_id)

    # Récupérer le circuit complet avec les validateurs
    workflow_circuit = GenericRequestService.get_workflow_circuit(session, request_id)
    workflow_info = GenericRequestService.get_workflow_info(session, request_id)

    return templates.TemplateResponse(
        "pages/generic_request_detail.html",
        get_template_context(
            request,
            module=module,
            req=req,
            history=history,
            next_steps=next_steps,
            workflow_circuit=workflow_circuit,
            workflow_info=workflow_info,
            WorkflowState=WorkflowState,
            current_user=current_user,
        ),
    )


@router.post("/{module}/create", response_class=JSONResponse, name="generic_request_create")
def generic_request_create(
    module: str,
    agent_id: int = Form(...),
    type: str = Form(...),
    objet: str = Form(...),
    motif: str | None = Form(None),
    description: str | None = Form(None),
    date_debut: str | None = Form(None),
    date_fin: str | None = Form(None),
    donnees_metier: str | None = Form(None),
    document: UploadFile | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Création d'une nouvelle demande
    """
    from datetime import date as date_type
    from pathlib import Path

    from app.core.config import settings

    # Récupérer l'agent correspondant à l'utilisateur
    # Utiliser agent_id du formulaire si fourni, sinon utiliser current_user.agent_id
    final_agent_id = agent_id if agent_id else current_user.agent_id
    
    if not final_agent_id:
        raise HTTPException(400, "Aucun agent associé à votre compte")

    agent = session.get(AgentComplet, final_agent_id)
    if not agent:
        raise HTTPException(400, "Agent introuvable")
    
    # Vérifier que l'agent appartient bien à l'utilisateur (sécurité)
    if agent.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(403, "Vous n'êtes pas autorisé à créer une demande pour cet agent")

    # Vérifier que le type de demande existe et est actif
    request_type = session.exec(
        select(RequestTypeCustom).where(RequestTypeCustom.code == type).where(RequestTypeCustom.actif)
    ).first()

    if not request_type:
        raise HTTPException(400, "Type de demande invalide ou inactif")

    # Traiter le document si fourni
    document_path = None
    document_filename = None
    if document:
        try:
            upload_dir = Path(settings.UPLOAD_DIR) / "demandes" / module
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Générer un nom de fichier unique
            file_extension = Path(document.filename).suffix if document.filename else ""
            unique_filename = f"{current_user.id}_{int(datetime.now().timestamp())}{file_extension}"
            file_path = upload_dir / unique_filename

            # Sauvegarder le fichier
            with open(file_path, "wb") as f:
                content = document.file.read()
                f.write(content)

            document_path = str(file_path.relative_to(settings.UPLOAD_DIR))
            document_filename = document.filename
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du document: {e}")
            raise HTTPException(500, "Erreur lors de la sauvegarde du document")

    # Parser les dates
    date_debut_parsed = None
    date_fin_parsed = None
    if date_debut:
        try:
            date_debut_parsed = date_type.fromisoformat(date_debut)
        except ValueError:
            pass
    if date_fin:
        try:
            date_fin_parsed = date_type.fromisoformat(date_fin)
        except ValueError:
            pass

    # Créer la demande
    new_request = GenericRequest(
        module=module,
        type=type,
        objet=objet,
        motif=motif,
        description=description,
        date_debut=date_debut_parsed,
        date_fin=date_fin_parsed,
        donnees_metier=donnees_metier,
        document_joint=document_path,
        document_filename=document_filename,
        demandeur_id=agent.id,
        demandeur_user_id=current_user.id,
        current_state=WorkflowState.DRAFT,
    )

    session.add(new_request)
    session.commit()
    session.refresh(new_request)

    # Enregistrer l'activité
    ActivityService.log_activity(
        session,
        user_id=current_user.id,
        action="CREATE",
        entity_type="GenericRequest",
        entity_id=new_request.id,
        details=f"Création d'une demande {type} dans le module {module}",
    )

    return JSONResponse(
        {
            "success": True,
            "message": "Demande créée avec succès",
            "request_id": new_request.id,
        }
    )


@router.post("/{module}/{request_id}/transition", response_class=JSONResponse, name="generic_request_transition")
def generic_request_transition(
    module: str,
    request_id: int,
    to_state: str = Form(...),
    comment: str | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Effectue une transition de workflow pour une demande
    """
    # Récupérer la demande
    req = session.get(GenericRequest, request_id)
    if not req:
        raise HTTPException(404, "Demande introuvable")

    # Vérifier que la demande appartient au module
    if req.module != module:
        raise HTTPException(404, "Demande introuvable pour ce module")

    # Convertir l'état
    try:
        to_state_enum = WorkflowState(to_state)
    except ValueError:
        raise HTTPException(400, f"État invalide: {to_state}")

    # Récupérer l'agent correspondant à l'utilisateur
    if not current_user.agent_id:
        raise HTTPException(400, "Aucun agent associé à votre compte")

    # Déterminer le rôle de l'utilisateur
    acted_by_role = "AGENT"  # Par défaut
    # TODO: Déterminer le rôle réel basé sur les rôles personnalisés

    # Effectuer la transition
    try:
        updated_request = GenericRequestService.transition(
            session=session,
            request_id=request_id,
            to_state=to_state_enum,
            acted_by_user_id=current_user.id,
            acted_by_role=acted_by_role,
            comment=comment,
        )

        # Enregistrer l'activité
        ActivityService.log_activity(
            session,
            user_id=current_user.id,
            action="TRANSITION",
            entity_type="GenericRequest",
            entity_id=request_id,
            details=f"Transition de {req.current_state} vers {to_state_enum}",
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Transition effectuée avec succès",
                "request": {
                    "id": updated_request.id,
                    "current_state": updated_request.current_state.value,
                },
            }
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{module}/{request_id}/next-states", response_class=JSONResponse, name="generic_request_next_states")
def generic_request_next_states(
    module: str,
    request_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère les prochains états possibles pour une demande
    """
    req = session.get(GenericRequest, request_id)
    if not req:
        raise HTTPException(404, "Demande introuvable")

    # Vérifier que la demande appartient au module
    if req.module != module:
        raise HTTPException(404, "Demande introuvable pour ce module")

    next_steps = GenericRequestService.next_states_for(session, request_id)

    return JSONResponse(
        {
            "success": True,
            "next_states": [{"to_state": step["to_state"].value, "from_state": step["from_state"].value} for step in next_steps],
        }
    )

