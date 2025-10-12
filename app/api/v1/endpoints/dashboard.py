from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import HTMLResponse
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(
        "pages/dashboard.html",
        get_template_context(
            request
        )
    )
