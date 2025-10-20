from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.logging_config import get_logger
from app.templates import get_template_context, templates

logger = get_logger(__name__)
router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", get_template_context(request))
