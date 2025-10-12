from fastapi import APIRouter, Depends
from sqlmodel import select
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserCreate
from app.api.v1.endpoints.auth import require_roles

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
    return {"id": user.id, "email": user.email}

@router.get("/", response_model=list[dict])
def list_users(
    session=Depends(get_session),
    current_user=Depends(require_roles("admin"))
):
    results = session.exec(select(User)).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name} for u in results]
