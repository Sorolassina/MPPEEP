"""
Endpoints pour les pages légales (CGU, Mentions légales, etc.)
"""

from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templates import get_template_context, templates

router = APIRouter()


@router.get("/cgu", response_class=HTMLResponse, name="cgu_page")
async def cgu_page(request: Request):
    """Affiche les Conditions Générales d'Utilisation"""
    return templates.TemplateResponse(
        "legal/cgu.html",
        get_template_context(
            request,
            current_date=datetime.now().strftime("%d/%m/%Y"),
        ),
    )

