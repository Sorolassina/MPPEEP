from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1 import api_router
from app.core.config import settings
from app.core.middleware import setup_middlewares
from app.core.logging_config import setup_logging, get_logger  # ⬅️ on importe setup_logging
from app.templates import templates, get_template_context

# 1) Init logging une seule fois, tout en haut
setup_logging()
logger = get_logger("mppeep.main")   # ou __name__

# 2) App FastAPI
root_path = settings.get_root_path  # Dynamique selon DEBUG/ENV
app = FastAPI(
    title=settings.APP_NAME, 
    root_path=root_path, 
    version=settings.ASSET_VERSION,
    openapi_url=f"{root_path}/openapi.json" if root_path else "/openapi.json",
    docs_url=f"{root_path}/docs" if root_path else "/docs",
    redoc_url=f"{root_path}/redoc" if root_path else "/redoc",
)

# 3) Middlewares
setup_middlewares(app, settings)

# 4) Événements de cycle de vie
@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Démarrage de l'application {settings.APP_NAME}")
    logger.info(f"📊 Environnement : {settings.ENV}")
    logger.info(f"🐛 Debug mode : {settings.DEBUG}")
    try:
        # Initialisation de la base de données principale
        from scripts.init_db import initialize_database
        logger.info("🗄️  Initialisation de la base de données...")
        initialize_database()
        logger.info("✅ Initialisation de la base terminée avec succès")
        
        # Initialisation du système RH
        logger.info("👥 Initialisation du système RH...")
        from app.core.logique_metier.rh_workflow import ensure_workflow_steps
        from app.db.session import get_session
        session = next(get_session())
        try:
            ensure_workflow_steps(session)
            logger.info("✅ Système RH initialisé avec succès")
        except Exception as rh_error:
            logger.warning(f"⚠️  Erreur initialisation RH: {rh_error}")
        finally:
            session.close()
         
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}", exc_info=True)
        logger.warning("⚠️  L'application démarre quand même...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Arrêt de l'application MPPEEP Dashboard")
    logger.info("🧹 Fermeture des connexions...")

# 5) Static & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 6) API
app.include_router(api_router, prefix="/api/v1")

# 7) Routes UI
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Redirige vers le favicon dans le dossier static"""
    from app.core.path_config import path_config
    favicon_url = path_config.get_file_url("static", "favicon.ico")
    return RedirectResponse(url=favicon_url)

@app.get("/version", response_class=JSONResponse, name="version")
def get_version():
    return JSONResponse({
        "version": app.version,
        "root_path": app.root_path,
        "app_name": app.title,
        "environment": settings.ENV,
        "debug": settings.DEBUG
    })

@app.get("/", name="read_root")
def read_root(request: Request):
    """Redirige vers la page de login"""
    return RedirectResponse(url=str(request.url_for("login_page")), status_code=303)

@app.get("/accueil", response_class=HTMLResponse, name="accueil")
def accueil(request: Request):
    from app.db.session import get_session
    from app.models.user import User
    from app.services.activity_service import ActivityService
    from sqlmodel import select, func
    
    # Statistiques
    stats = {"users_count": 0, "items_count": 0, "completed_count": 0, "growth": 0}
    recent_activity = []
    
    try:
        db = next(get_session())
        
        # Calculer les statistiques
        users_count = db.exec(select(func.count(User.id))).first()
        active_users_count = db.exec(select(func.count(User.id)).where(User.is_active == True)).first()
        admin_count = db.exec(select(func.count(User.id)).where(User.type_user == "admin")).first()
        
        stats = {
            "users_count": users_count or 0,
            "items_count": active_users_count or 0,
            "completed_count": admin_count or 0,
            "growth": 0  # À calculer selon vos besoins
        }
        
        # Charger les activités récentes
        recent_activity = ActivityService.get_recent_activities(db, limit=10, days=7)
        
    except Exception as e:
        pass  # Utiliser les valeurs par défaut
    
    return templates.TemplateResponse(
        "pages/accueil.html",
        get_template_context(
            request,
            stats=stats,
            recent_activity=recent_activity
        )
    )



if __name__ == "__main__":
    import uvicorn
    # Option recommandé : éviter que Uvicorn impose sa propre config logging
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_config=None,   # ⬅️ laisse ta config régner
        # log_level="info"  # facultatif : n’influe pas ta config Python
    )
