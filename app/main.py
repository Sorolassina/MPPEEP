from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.logging_config import get_logger, setup_logging  # ⬅️ on importe setup_logging
from app.core.middleware import setup_middlewares
from app.templates import get_template_context, templates

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

# 1) Init logging une seule fois, tout en haut
setup_logging()
logger = get_logger("mppeep.main")  # ou __name__


# 2) Lifespan events (remplace @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application (startup/shutdown)"""
    # Startup
    logger.info(f"🚀 Démarrage de l'application {settings.APP_NAME}")
    logger.info(f"📊 Environnement : {settings.ENV}")
    logger.info(f"🐛 Debug mode : {settings.DEBUG}")
    try:
        # Initialisation de la base de données principale
        from scripts.init_db import initialize_database

        logger.info("🗄️  Initialisation de la base de données...")
        initialize_database()
        logger.info("✅ Initialisation de la base terminée avec succès")

        logger.info("✅ Système RH : Workflows personnalisés activés")
        
        # Démarrer le planificateur de tâches (nettoyage automatique)
        from app.core.scheduler import start_scheduler
        
        logger.info("⏰ Démarrage du planificateur de tâches...")
        start_scheduler()
        logger.info("✅ Planificateur de tâches démarré")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}", exc_info=True)
        logger.warning("⚠️  L'application démarre quand même...")

    yield  # Application running

    # Shutdown
    logger.info("👋 Arrêt de l'application MPPEEP Dashboard")
    logger.info("🧹 Fermeture des connexions...")
    
    # Arrêter le planificateur
    try:
        from app.core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.error(f"❌ Erreur arrêt scheduler: {e}")


# 3) App FastAPI
root_path = settings.get_root_path  # Dynamique selon DEBUG/ENV

# Créer l'application principale
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.ASSET_VERSION,
    lifespan=lifespan,
)

# Créer une sous-application pour les routes
subapp = FastAPI(
    title=settings.APP_NAME,
    version=settings.ASSET_VERSION,
    openapi_url=f"{root_path}/openapi.json" if root_path else "/openapi.json",
    docs_url=f"{root_path}/docs" if root_path else "/docs",
    redoc_url=f"{root_path}/redoc" if root_path else "/redoc",
)


# 3) Gestionnaire d'erreur personnalisé pour les erreurs de validation
@subapp.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Gestionnaire personnalisé pour les erreurs de validation FastAPI (422)
    Transforme les erreurs techniques en messages clairs pour l'utilisateur
    """
    logger.warning(f"⚠️ Erreur validation sur {request.url.path}: {exc.errors()}")

    # Construire un message d'erreur détaillé
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # Ignorer "body" ou "query"
        error_type = error["type"]
        error_msg = error["msg"]

        # Messages personnalisés selon le type d'erreur
        if error_type == "missing":
            error_details.append(f"Le champ '{field}' est obligatoire")
        elif error_type == "type_error.integer":
            error_details.append(f"Le champ '{field}' doit être un nombre entier")
        elif error_type == "type_error.str":
            error_details.append(f"Le champ '{field}' doit être du texte")
        elif error_type == "value_error":
            error_details.append(f"Le champ '{field}' a une valeur invalide: {error_msg}")
        else:
            error_details.append(f"Erreur dans le champ '{field}': {error_msg}")

    # Message principal
    main_message = "Erreur de validation des données"
    if len(error_details) == 1:
        main_message = error_details[0]
    else:
        main_message = "Plusieurs erreurs détectées:\n• " + "\n• ".join(error_details)

    return JSONResponse(
        status_code=422,
        content={
            "detail": main_message,
            "errors": error_details,
            "field_errors": {error["loc"][-1]: error["msg"] for error in exc.errors()},
        },
    )


# 4) Middlewares
setup_middlewares(subapp, settings)


# 5) Static & templates
subapp.mount("/static", StaticFiles(directory="app/static"), name="static")
subapp.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 6) API
subapp.include_router(api_router, prefix="/api/v1")


# 7) Routes UI
@subapp.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Redirige vers le favicon dans le dossier static"""
    from app.core.path_config import path_config

    favicon_url = path_config.get_file_url("static", "favicon.ico")
    return RedirectResponse(url=favicon_url)


@subapp.get("/version", response_class=JSONResponse, name="version")
def get_version():
    return JSONResponse(
        {
            "version": subapp.version,
            "root_path": root_path,
            "app_name": subapp.title,
            "environment": settings.ENV,
            "debug": settings.DEBUG,
        }
    )


@subapp.get("/", name="read_root")
def read_root(request: Request):
    """Redirige vers la page de login"""
    return RedirectResponse(url=str(request.url_for("login_page")), status_code=303)


@subapp.get("/access-denied", response_class=HTMLResponse, name="access_denied")
def access_denied(request: Request, module: str = "module", current_user: User = Depends(get_current_user)):
    """
    Page d'erreur d'accès refusé
    """
    return templates.TemplateResponse(
        "pages/access_denied.html", 
        get_template_context(request, module=module, current_user=current_user)
    )

@subapp.get("/accueil", response_class=HTMLResponse, name="accueil")
def accueil(request: Request, current_user: User = Depends(get_current_user)):
    from sqlmodel import func, select

    from app.db.session import get_session
    from app.models.user import User
    from app.services.activity_service import ActivityService

    # Statistiques
    stats = {"users_count": 0, "items_count": 0, "completed_count": 0, "growth": 0}
    recent_activity = []

    try:
        db = next(get_session())

        # Calculer les statistiques
        users_count = db.exec(select(func.count(User.id))).first()
        active_users_count = db.exec(select(func.count(User.id)).where(User.is_active)).first()
        admin_count = db.exec(select(func.count(User.id)).where(User.type_user == "admin")).first()

        stats = {
            "users_count": users_count or 0,
            "items_count": active_users_count or 0,
            "completed_count": admin_count or 0,
            "growth": 0,  # À calculer selon vos besoins
        }

        # Charger les activités récentes
        recent_activity = ActivityService.get_recent_activities(db, limit=10, days=7)

    except Exception:
        pass  # Utiliser les valeurs par défaut

    return templates.TemplateResponse(
        "pages/accueil.html", get_template_context(request, stats=stats, recent_activity=recent_activity)
    )


# 8) Monter la sous-application avec le bon préfixe
mount_path = root_path if root_path else "/"
app.mount(mount_path, subapp)


if __name__ == "__main__":
    import uvicorn

    # Option recommandé : éviter que Uvicorn impose sa propre config logging
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9000,
        reload=False,
        log_config=None,  # ⬅️ laisse ta config régner
        # log_level="info"  # facultatif : n’influe pas ta config Python
    )
