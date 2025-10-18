"""
API pour l'administration des workflows
Permet de configurer les circuits de validation via l'interface web
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.db.session import get_session
from app.models.workflow_config import (
    WorkflowTemplate,
    WorkflowTemplateStep,
    RequestTypeCustom,
    CustomRole,
    WorkflowDirection,
    WorkflowRoleType
)
from app.services.workflow_config_service import WorkflowConfigService
from app.api.v1.endpoints.auth import get_current_user
from app.templates import templates, get_template_context


router = APIRouter(prefix="/workflow-config", tags=["Workflow Configuration"])


# ═══════════════════════════════════════════════════════════
# INTERFACE WEB
# ═══════════════════════════════════════════════════════════

@router.get("/", response_class=HTMLResponse, name="workflow_config_home")
def workflow_config_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Page d'accueil de la configuration des workflows
    """
    # Vérifier que l'utilisateur est admin
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    # Récupérer tous les templates
    templates_list = session.exec(
        select(WorkflowTemplate).order_by(WorkflowTemplate.nom)
    ).all()
    
    # Récupérer tous les types de demandes
    request_types = session.exec(
        select(RequestTypeCustom).order_by(RequestTypeCustom.categorie, RequestTypeCustom.ordre_affichage)
    ).all()
    
    # Récupérer tous les rôles personnalisés
    custom_roles = session.exec(
        select(CustomRole).where(CustomRole.actif == True).order_by(CustomRole.libelle)
    ).all()
    
    return templates.TemplateResponse(
        "pages/workflow_configuration.html",
        get_template_context(
            request,
            templates=templates_list,
            request_types=request_types,
            custom_roles=custom_roles,
            WorkflowDirection=WorkflowDirection,
            WorkflowRoleType=WorkflowRoleType
        )
    )


# ═══════════════════════════════════════════════════════════
# API - TEMPLATES
# ═══════════════════════════════════════════════════════════

@router.post("/api/templates", name="api_create_workflow_template")
async def create_workflow_template(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Crée un nouveau template de workflow"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    # Récupérer les données du formulaire
    data = await request.json()
    
    try:
        template = WorkflowConfigService.create_template(
            session=session,
            code=data.get('code'),
            nom=data.get('nom'),
            description=data.get('description'),
            direction=WorkflowDirection(data.get('direction', 'ASCENDANT')),
            icone=data.get('icone', '📄'),
            couleur=data.get('couleur', '#3498db'),
            user_id=current_user.id
        )
        
        # Créer les étapes du template
        steps = data.get('steps', [])
        for step_data in steps:
            WorkflowConfigService.add_step_to_template(
                session=session,
                template_id=template.id,
                role_type=WorkflowRoleType(step_data.get('role_type')),
                order_index=step_data.get('order_index'),
                obligatoire=True,
                peut_rejeter=True,
                user_id=current_user.id
            )
        
        return {"ok": True, "template_id": template.id, "message": "Template créé avec succès"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la création : {str(e)}")


@router.get("/api/templates", name="api_list_workflow_templates")
def list_workflow_templates(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Liste tous les templates de workflow"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    templates = session.exec(
        select(WorkflowTemplate).order_by(WorkflowTemplate.nom)
    ).all()
    
    return [
        {
            "id": t.id,
            "code": t.code,
            "nom": t.nom,
            "description": t.description,
            "direction": t.direction.value,
            "icone": t.icone,
            "couleur": t.couleur,
            "actif": t.actif,
            "est_systeme": t.est_systeme
        }
        for t in templates
    ]


@router.get("/api/templates/{template_id}/steps", name="api_get_template_steps")
def get_template_steps(
    template_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Récupère les étapes d'un template"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    steps = WorkflowConfigService.get_template_steps(session, template_id)
    
    return [
        {
            "id": s.id,
            "order_index": s.order_index,
            "role_type": s.role_type.value,
            "custom_role_name": s.custom_role_name,
            "obligatoire": s.obligatoire,
            "peut_rejeter": s.peut_rejeter,
            "delai_jours": s.delai_jours
        }
        for s in steps
    ]


@router.post("/api/templates/{template_id}/steps", name="api_add_template_step")
async def add_template_step(
    template_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Ajoute une étape à un template"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    data = await request.json()
    
    try:
        step = WorkflowConfigService.add_step_to_template(
            session=session,
            template_id=template_id,
            role_type=WorkflowRoleType(data.get('role_type')),
            order_index=data.get('order_index'),
            custom_role_name=data.get('custom_role_name'),
            obligatoire=data.get('obligatoire', True),
            peut_rejeter=data.get('peut_rejeter', True),
            delai_jours=data.get('delai_jours'),
            user_id=current_user.id
        )
        
        return {"ok": True, "step_id": step.id, "message": "Étape ajoutée avec succès"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de l'ajout : {str(e)}")


@router.put("/api/templates/{template_id}", name="api_update_workflow_template")
async def update_workflow_template(
    template_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Met à jour un template de workflow"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    data = await request.json()
    
    try:
        # Récupérer le template
        template = session.get(WorkflowTemplate, template_id)
        if not template:
            raise ValueError("Template introuvable")
        
        if template.est_systeme:
            raise ValueError("Impossible de modifier un template système")
        
        # Mettre à jour les champs
        template.nom = data.get('nom', template.nom)
        template.description = data.get('description', template.description)
        template.direction = WorkflowDirection(data.get('direction', template.direction))
        template.icone = data.get('icone', template.icone)
        template.couleur = data.get('couleur', template.couleur)
        template.updated_at = datetime.utcnow()
        template.updated_by = current_user.id
        
        session.add(template)
        
        # Supprimer les anciennes étapes
        old_steps = session.exec(
            select(WorkflowTemplateStep).where(WorkflowTemplateStep.template_id == template_id)
        ).all()
        for step in old_steps:
            session.delete(step)
        
        # Créer les nouvelles étapes
        steps = data.get('steps', [])
        for step_data in steps:
            new_step = WorkflowTemplateStep(
                template_id=template_id,
                role_type=WorkflowRoleType(step_data.get('role_type')),
                order_index=step_data.get('order_index'),
                obligatoire=True,
                peut_rejeter=True
            )
            session.add(new_step)
        
        session.commit()
        session.refresh(template)
        
        return {"ok": True, "template_id": template.id, "message": "Template mis à jour avec succès"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la mise à jour : {str(e)}")


@router.get("/api/templates/{template_id}/preview", name="api_preview_workflow_template")
def preview_workflow_template(
    template_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Génère un aperçu visuel d'un workflow"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    preview = WorkflowConfigService.get_workflow_preview(session, template_id)
    return preview


@router.delete("/api/templates/{template_id}", name="api_delete_workflow_template")
def delete_workflow_template(
    template_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Désactive un template (soft delete)"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    try:
        WorkflowConfigService.delete_template(session, template_id, current_user.id)
        return {"ok": True, "message": "Template désactivé avec succès"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la désactivation : {str(e)}")


@router.delete("/api/templates/{template_id}/permanent", name="api_delete_workflow_template_permanent")
def delete_workflow_template_permanent(
    template_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Supprime définitivement un template (hard delete)"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    try:
        WorkflowConfigService.delete_template_permanently(session, template_id, current_user.id)
        return {"ok": True, "message": "Template supprimé définitivement"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la suppression : {str(e)}")


# ═══════════════════════════════════════════════════════════
# API - TYPES DE DEMANDES
# ═══════════════════════════════════════════════════════════

@router.post("/api/request-types", name="api_create_request_type")
async def create_request_type(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Crée un nouveau type de demande"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    data = await request.json()
    
    try:
        request_type = WorkflowConfigService.create_request_type(
            session=session,
            code=data.get('code'),
            libelle=data.get('libelle'),
            workflow_template_id=data.get('workflow_template_id'),
            description=data.get('description'),
            categorie=data.get('categorie', 'Autre'),
            champs_formulaire=data.get('champs_formulaire'),
            document_obligatoire=data.get('document_obligatoire', False),
            necessite_validation_rh=data.get('necessite_validation_rh', False),
            necessite_validation_daf=data.get('necessite_validation_daf', False),
            user_id=current_user.id
        )
        
        return {"ok": True, "request_type_id": request_type.id, "message": "Type de demande créé avec succès"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la création : {str(e)}")


@router.get("/api/request-types", name="api_list_request_types")
def list_request_types(
    categorie: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Liste tous les types de demandes"""
    request_types = WorkflowConfigService.get_active_request_types(session, categorie)
    
    return [
        {
            "id": rt.id,
            "code": rt.code,
            "libelle": rt.libelle,
            "description": rt.description,
            "categorie": rt.categorie,
            "workflow_template_id": rt.workflow_template_id,
            "icone": rt.icone,
            "couleur": rt.couleur,
            "actif": rt.actif,
            "document_obligatoire": rt.document_obligatoire,
            "necessite_validation_rh": rt.necessite_validation_rh,
            "necessite_validation_daf": rt.necessite_validation_daf,
            "est_systeme": rt.est_systeme
        }
        for rt in request_types
    ]


@router.put("/api/request-types/{request_type_id}", name="api_update_request_type")
async def update_request_type(
    request_type_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Met à jour un type de demande existant"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    data = await request.json()
    
    try:
        # Récupérer le type de demande
        request_type = session.get(RequestTypeCustom, request_type_id)
        if not request_type:
            raise HTTPException(404, "Type de demande introuvable")
        
        # Ne pas permettre de modifier les types système
        if request_type.est_systeme:
            raise HTTPException(403, "Les types système ne peuvent pas être modifiés")
        
        # Mettre à jour les champs
        if 'code' in data:
            request_type.code = data['code']
        if 'libelle' in data:
            request_type.libelle = data['libelle']
        if 'description' in data:
            request_type.description = data['description']
        if 'workflow_template_id' in data:
            request_type.workflow_template_id = data['workflow_template_id']
        if 'categorie' in data:
            request_type.categorie = data['categorie']
        if 'champs_formulaire' in data:
            request_type.champs_formulaire = data['champs_formulaire']
        if 'document_obligatoire' in data:
            request_type.document_obligatoire = data['document_obligatoire']
        if 'necessite_validation_rh' in data:
            request_type.necessite_validation_rh = data['necessite_validation_rh']
        if 'necessite_validation_daf' in data:
            request_type.necessite_validation_daf = data['necessite_validation_daf']
        
        session.add(request_type)
        session.commit()
        session.refresh(request_type)
        
        return {"ok": True, "message": "Type de demande modifié avec succès"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la modification : {str(e)}")


@router.delete("/api/request-types/{request_type_id}", name="api_delete_request_type")
async def delete_request_type(
    request_type_id: int,
    permanent: bool = False,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Désactive ou supprime définitivement un type de demande"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    try:
        request_type = session.get(RequestTypeCustom, request_type_id)
        if not request_type:
            raise HTTPException(404, "Type de demande introuvable")
        
        # Ne pas permettre de supprimer les types système
        if request_type.est_systeme:
            raise HTTPException(403, "Les types système ne peuvent pas être supprimés")
        
        if permanent:
            # Suppression définitive
            session.delete(request_type)
            message = "Type de demande supprimé définitivement"
        else:
            # Soft delete
            request_type.actif = False
            session.add(request_type)
            message = "Type de demande désactivé"
        
        session.commit()
        
        return {"ok": True, "message": message}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la suppression : {str(e)}")


# ═══════════════════════════════════════════════════════════
# API - RÔLES PERSONNALISÉS
# ═══════════════════════════════════════════════════════════

@router.post("/api/custom-roles", name="api_create_custom_role")
async def create_custom_role(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Crée un rôle personnalisé"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    data = await request.json()
    
    try:
        role = WorkflowConfigService.create_custom_role(
            session=session,
            code=data.get('code'),
            libelle=data.get('libelle'),
            description=data.get('description'),
            user_id=current_user.id
        )
        
        return {"ok": True, "role_id": role.id, "message": "Rôle créé avec succès"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la création : {str(e)}")


@router.get("/api/custom-roles", name="api_list_custom_roles")
def list_custom_roles(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Liste tous les rôles personnalisés actifs"""
    roles = session.exec(
        select(CustomRole).where(CustomRole.actif == True)
    ).all()
    
    return [
        {
            "id": role.id,
            "code": role.code,
            "libelle": role.libelle,
            "description": role.description,
            "actif": role.actif,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None
        }
        for role in roles
    ]


@router.put("/api/custom-roles/{role_id}", name="api_update_custom_role")
async def update_custom_role(
    role_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Met à jour un rôle personnalisé"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    data = await request.json()
    
    try:
        role = session.get(CustomRole, role_id)
        if not role:
            raise HTTPException(404, "Rôle introuvable")
        
        # Mettre à jour les champs
        if 'code' in data:
            role.code = data['code']
        if 'libelle' in data:
            role.libelle = data['libelle']
        if 'description' in data:
            role.description = data['description']
        
        role.updated_at = datetime.now()
        
        session.add(role)
        session.commit()
        session.refresh(role)
        
        return {"ok": True, "message": "Rôle modifié avec succès"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la modification : {str(e)}")


@router.delete("/api/custom-roles/{role_id}", name="api_delete_custom_role")
async def delete_custom_role(
    role_id: int,
    permanent: bool = False,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Désactive ou supprime définitivement un rôle personnalisé"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    try:
        role = session.get(CustomRole, role_id)
        if not role:
            raise HTTPException(404, "Rôle introuvable")
        
        if permanent:
            # Suppression définitive
            session.delete(role)
            message = "Rôle supprimé définitivement"
        else:
            # Soft delete
            role.actif = False
            role.updated_at = datetime.now()
            session.add(role)
            message = "Rôle désactivé"
        
        session.commit()
        
        return {"ok": True, "message": message}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la suppression : {str(e)}")


@router.post("/api/custom-roles/{role_id}/assign", name="api_assign_custom_role")
async def assign_custom_role(
    role_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Attribue un rôle à un agent"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    data = await request.json()
    
    try:
        assignment = WorkflowConfigService.assign_role_to_agent(
            session=session,
            custom_role_id=role_id,
            agent_id=data.get('agent_id'),
            date_fin=data.get('date_fin'),
            user_id=current_user.id
        )
        
        return {"ok": True, "assignment_id": assignment.id, "message": "Rôle attribué avec succès"}
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de l'attribution : {str(e)}")


# ═══════════════════════════════════════════════════════════
# INITIALISATION
# ═══════════════════════════════════════════════════════════

@router.post("/api/initialize-system-workflows", name="api_initialize_system_workflows")
def initialize_system_workflows(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Initialise les workflows système de base"""
    if current_user.type_user != "admin":
        raise HTTPException(403, "Accès réservé aux administrateurs")
    
    try:
        WorkflowConfigService.initialize_system_workflows(session)
        return {"ok": True, "message": "Workflows système initialisés avec succès"}
    except Exception as e:
        raise HTTPException(500, f"Erreur lors de l'initialisation : {str(e)}")

