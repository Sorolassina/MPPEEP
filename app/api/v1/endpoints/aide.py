# app/api/v1/endpoints/aide.py
"""
Endpoints pour le système d'aide
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.api.v1.endpoints.auth import get_current_user
from app.core.logging_config import get_logger
from app.db.session import get_session
from app.models.user import User
from app.templates import get_template_context, templates

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="aide_home")
def aide_home(
    request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """
    Page d'aide principale avec guides, FAQ, tutoriels
    """
    return templates.TemplateResponse("pages/aide.html", get_template_context(request, current_user=current_user))


@router.get("/guide/{section}", response_class=HTMLResponse, name="aide_guide")
def aide_guide(
    section: str,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Page de guide spécifique à une section
    """
    return templates.TemplateResponse(
        f"pages/aide_guide_{section}.html", get_template_context(request, section=section, current_user=current_user)
    )
