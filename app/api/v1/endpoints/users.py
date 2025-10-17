from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import select, Session
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserCreate
from app.api.v1.endpoints.auth import require_roles
from app.services.activity_service import ActivityService

router = APIRouter()

@router.post("/", response_model=dict)
def create_user(
    payload: UserCreate, 
    session=Depends(get_session), 
    current_user= Depends(require_roles("admin"))
):
    user = User(email=payload.email, full_name=payload.full_name)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Logger l'activité
    ActivityService.log_activity(
        db_session=session,
        user_id=current_user.id,
        user_email=current_user.email,
        user_full_name=current_user.full_name,
        action_type="create",
        target_type="user",
        target_id=user.id,
        description=f"Création de l'utilisateur {user.full_name} ({user.email})",
        icon="👤"
    )
    
    return {"id": user.id, "email": user.email}

@router.get("/", response_model=list[dict])
def list_users(
    session: Session = Depends(get_session),
    current_user=Depends(require_roles("admin"))
):
    results = session.exec(select(User)).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name} for u in results]

@router.get("/by-service/{service_id}", response_model=list[dict])
def list_users_by_service(
    service_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(require_roles("admin", "user"))
):
    """Récupère les utilisateurs liés à un agent d'un service donné"""
    from app.models.personnel import AgentComplet
    
    # Récupérer les users qui ont un agent_id lié au service
    query = (
        select(User, AgentComplet)
        .join(AgentComplet, User.agent_id == AgentComplet.id, isouter=False)
        .where(AgentComplet.service_id == service_id)
        .where(User.is_active == True)
    )
    
    results = session.exec(query).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name or f"{agent.prenom} {agent.nom}",
            "agent_id": user.agent_id,
            "service_id": agent.service_id
        }
        for user, agent in results
    ]
