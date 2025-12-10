from contextlib import asynccontextmanager
from pickle import TRUE
import traceback

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
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
        
        # Préchauffage du chatbot Ollama en arrière-plan (non-bloquant)
        try:
            logger.info("🔥 Initialisation du préchauffage du chatbot Ollama...")
            # Importer et lancer le préchauffage en arrière-plan
            from app.services.chatbot_warmup_service import ChatbotWarmupService
            import asyncio
            import threading
            
            def warmup_background():
                """Lance le préchauffage dans un thread séparé"""
                try:
                    # Créer une nouvelle boucle d'événements pour ce thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # Exécuter le préchauffage
                    loop.run_until_complete(ChatbotWarmupService.warmup_model())
                    loop.close()
                except Exception as e:
                    logger.debug(f"⚠️ Préchauffage chatbot en arrière-plan: {e}")
            
            # Lancer le préchauffage dans un thread pour ne pas bloquer le démarrage
            warmup_thread = threading.Thread(target=warmup_background, daemon=True)
            warmup_thread.start()
            logger.info("✅ Préchauffage chatbot lancé en arrière-plan (thread séparé)")
        except Exception as e:
            logger.debug(f"⚠️ Préchauffage chatbot non disponible: {e}")
            # Ne pas bloquer le démarrage si le préchauffage échoue

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


# 3a) Gestionnaire d'erreur pour les erreurs HTTP 400 (Bad Request)
@subapp.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Gestionnaire pour les erreurs HTTP (400, 404, etc.)
    """
    # Log spécial pour les erreurs 400 sur les requêtes multipart
    if exc.status_code == 400:
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            logger.error(f"❌ ===== ERREUR 400 - PARSING MULTIPART ÉCHOUÉ =====")
            logger.error(f"❌ URL: {request.url.path}")
            logger.error(f"❌ Method: {request.method}")
            logger.error(f"❌ Content-Type: {content_type}")
            logger.error(f"❌ Content-Length: {request.headers.get('content-length', 'N/A')}")
            logger.error(f"❌ Detail: {exc.detail}")
            logger.error(f"❌ Headers: {dict(request.headers)}")
            logger.error(f"❌ ===== FIN ERREUR 400 =====")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail)}
    )


# 3b) Gestionnaire d'erreur personnalisé pour les erreurs de validation
@subapp.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Gestionnaire personnalisé pour les erreurs de validation FastAPI (422)
    Transforme les erreurs techniques en messages clairs pour l'utilisateur
    """
    logger.warning(f"⚠️ Erreur validation sur {request.url.path}: {exc.errors()}")
    
    # Log spécial pour les erreurs multipart
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        logger.error(f"❌ Erreur de parsing multipart sur {request.url.path}")
        logger.error(f"❌ Content-Type: {content_type}")
        logger.error(f"❌ Content-Length: {request.headers.get('content-length', 'N/A')}")
        logger.error(f"❌ Détails erreurs: {exc.errors()}")
        # Logger tous les headers pour diagnostic
        logger.error(f"❌ Tous les headers: {dict(request.headers)}")

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


# 3c) Gestionnaire d'erreur global pour toutes les exceptions non gérées
@subapp.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Gestionnaire global pour toutes les exceptions non gérées
    """
    # Log spécial pour les erreurs sur les requêtes multipart
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        logger.error(f"❌ ===== EXCEPTION NON GÉRÉE - PARSING MULTIPART =====")
        logger.error(f"❌ URL: {request.url.path}")
        logger.error(f"❌ Method: {request.method}")
        logger.error(f"❌ Content-Type: {content_type}")
        logger.error(f"❌ Content-Length: {request.headers.get('content-length', 'N/A')}")
        logger.error(f"❌ Type d'exception: {type(exc).__name__}")
        logger.error(f"❌ Message: {str(exc)}")
        logger.error(f"❌ Traceback:", exc_info=True)
        logger.error(f"❌ ===== FIN EXCEPTION =====")
    else:
        logger.error(f"❌ Exception non gérée: {type(exc).__name__}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erreur interne du serveur: {str(exc)}"}
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
    """Redirige vers la page de landing"""
    return RedirectResponse(url=str(request.url_for("landing_page")), status_code=303)


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
    from datetime import datetime
    from sqlmodel import func, select

    from app.db.session import get_session
    from app.core.enums import WorkflowState
    from app.models.personnel import AgentComplet
    from app.models.performance import ObjectifPerformance, StatutObjectif
    from app.models.rh import HRRequest
    from app.models.user import User
    from app.services.activity_service import ActivityService

    # Statistiques par défaut
    stats = {
        "users_count": 0,
        "items_count": 0,
        "completed_count": 0,
        "growth": 0,
        "performance_rate": 0,
        "objectifs_atteints": 0,
        "budget_progress": 0,
        "budget_alerts": 0,
        "rh_requests": 0,
        "rh_overdue": 0,
    }
    recent_activity = []

    try:
        db = next(get_session())

        # 1. Statistiques agents (Collaborateurs connectés)
        agents_count = db.exec(select(func.count(AgentComplet.id)).where(AgentComplet.actif == True)).first() or 0
        stats["users_count"] = agents_count

        # 2. Demandes RH en cours (Dossiers actifs en suivi)
        demandes_rh_en_cours = db.exec(
            select(func.count(HRRequest.id)).where(
                HRRequest.current_state.in_([
                    WorkflowState.SUBMITTED,
                    WorkflowState.VALIDATION_N1,
                    WorkflowState.VALIDATION_N2,
                    WorkflowState.VALIDATION_N3,
                    WorkflowState.VALIDATION_N4,
                    WorkflowState.VALIDATION_N5,
                    WorkflowState.VALIDATION_N6,
                ])
            )
        ).first() or 0
        stats["items_count"] = demandes_rh_en_cours

        # 3. Demandes RH archivées (Actions validées ce mois)
        from datetime import date
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if current_month_start.month == 12:
            next_month_start = current_month_start.replace(year=current_month_start.year + 1, month=1)
        else:
            next_month_start = current_month_start.replace(month=current_month_start.month + 1)
        
        demandes_archivees_mois = db.exec(
            select(func.count(HRRequest.id)).where(
                HRRequest.current_state == WorkflowState.ARCHIVED,
                HRRequest.updated_at >= current_month_start,
                HRRequest.updated_at < next_month_start,
            )
        ).first() or 0
        stats["completed_count"] = demandes_archivees_mois

        # 4. Performance - Objectifs
        total_objectifs = db.exec(select(func.count(ObjectifPerformance.id))).first() or 0
        objectifs_atteints = (
            db.exec(
                select(func.count(ObjectifPerformance.id)).where(ObjectifPerformance.statut == StatutObjectif.ATTEINT)
            ).first()
            or 0
        )
        performance_rate = round((objectifs_atteints / total_objectifs * 100), 1) if total_objectifs > 0 else 0
        stats["performance_rate"] = performance_rate
        stats["objectifs_atteints"] = objectifs_atteints

        # 5. Budget - Progression (taux d'exécution moyen depuis SigobeKpi)
        try:
            from app.models.budget import SigobeKpi
            
            # Récupérer le dernier KPI global disponible
            kpi_global = db.exec(
                select(SigobeKpi)
                .where(SigobeKpi.dimension == "global")
                .order_by(SigobeKpi.created_at.desc())
            ).first()
            
            if kpi_global and kpi_global.budget_actuel_total and kpi_global.budget_actuel_total > 0:
                # Calculer le taux d'exécution : (Mandats PEC / Budget Actuel) * 100
                if kpi_global.mandats_total:
                    budget_progress = round((float(kpi_global.mandats_total) / float(kpi_global.budget_actuel_total)) * 100, 1)
                else:
                    # Sinon, utiliser le taux d'engagement
                    if kpi_global.engagements_total:
                        budget_progress = round((float(kpi_global.engagements_total) / float(kpi_global.budget_actuel_total)) * 100, 1)
                    else:
                        budget_progress = 0
                stats["budget_progress"] = budget_progress
            else:
                stats["budget_progress"] = 0
            
            # Alertes budgétaires : programmes avec taux d'engagement > 90% ou taux d'exécution < 20%
            # Pour simplifier, on compte les programmes en alerte
            kpis_programmes = db.exec(
                select(SigobeKpi)
                .where(SigobeKpi.dimension == "programme")
                .order_by(SigobeKpi.created_at.desc())
            ).all()
            
            alertes_count = 0
            for kpi in kpis_programmes:
                if kpi.budget_actuel_total and kpi.budget_actuel_total > 0:
                    if kpi.engagements_total:
                        taux_engagement = (float(kpi.engagements_total) / float(kpi.budget_actuel_total)) * 100
                        if taux_engagement > 90:  # Taux d'engagement trop élevé
                            alertes_count += 1
                    if kpi.mandats_total:
                        taux_execution = (float(kpi.mandats_total) / float(kpi.budget_actuel_total)) * 100
                        if taux_execution < 20:  # Taux d'exécution trop faible
                            alertes_count += 1
            
            stats["budget_alerts"] = alertes_count
        except Exception:
            # Si les données budgétaires ne sont pas disponibles, utiliser 0
            stats["budget_progress"] = 0
            stats["budget_alerts"] = 0

        # 6. RH - Demandes
        total_demandes_rh = db.exec(select(func.count(HRRequest.id))).first() or 0
        stats["rh_requests"] = total_demandes_rh

        # Demandes en retard (demandes en cours depuis plus de 30 jours)
        from datetime import timedelta
        date_limite = datetime.now() - timedelta(days=30)
        demandes_en_retard = db.exec(
            select(func.count(HRRequest.id)).where(
                HRRequest.current_state.in_([
                    WorkflowState.SUBMITTED,
                    WorkflowState.VALIDATION_N1,
                    WorkflowState.VALIDATION_N2,
                    WorkflowState.VALIDATION_N3,
                    WorkflowState.VALIDATION_N4,
                    WorkflowState.VALIDATION_N5,
                    WorkflowState.VALIDATION_N6,
                ]),
                HRRequest.created_at < date_limite,
            )
        ).first() or 0
        stats["rh_overdue"] = demandes_en_retard

        # Charger les activités récentes
        recent_activity = ActivityService.get_recent_activities(db, limit=10, days=7)

    except Exception as e:
        # Logger l'erreur pour debug
        import logging
        logging.error(f"Erreur calcul stats accueil: {e}")
        pass  # Utiliser les valeurs par défaut

    return templates.TemplateResponse(
        "pages/accueil.html", get_template_context(request, stats=stats, recent_activity=recent_activity)
    )


# 8) Middleware de redirection pour forcer l'utilisation du préfixe en production
if root_path:
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class RootPathRedirectMiddleware(BaseHTTPMiddleware):
        """
        Middleware qui redirige toutes les requêtes sans préfixe vers le chemin avec préfixe
        En mode production, toutes les routes doivent passer par /mppeep
        """
        async def dispatch(self, request: Request, call_next):
            path = request.url.path
            
            # Si le chemin ne commence pas par root_path, rediriger
            if not path.startswith(root_path):
                # Ignorer les requêtes pour les ressources statiques si elles sont déjà bien préfixées
                # Construire la nouvelle URL avec le préfixe
                new_path = f"{root_path}{path}" if path != "/" else root_path
                new_url = f"{request.url.scheme}://{request.url.netloc}{new_path}"
                if request.url.query:
                    new_url = f"{new_url}?{request.url.query}"
                
                logger.warning(f"⚠️  Accès direct refusé: {path} → redirection vers {new_path}")
                return RedirectResponse(url=new_url, status_code=301)
            
            # Si le chemin commence déjà par root_path, continuer normalement
            return await call_next(request)
    
    # Ajouter le middleware AVANT le montage (il s'exécutera en premier)
    app.add_middleware(RootPathRedirectMiddleware)

# 9) Monter la sous-application avec le bon préfixe
mount_path = root_path if root_path else "/"
app.mount(mount_path, subapp)


if __name__ == "__main__":
    import uvicorn

    # Option recommandé : éviter que Uvicorn impose sa propre config logging
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_config=None,  # ⬅️ laisse ta config régner
        # log_level="info"  # facultatif : n’influe pas ta config Python
    )
