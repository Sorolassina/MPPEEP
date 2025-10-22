import random
import string
from collections.abc import Iterable
from datetime import datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from app.core.logging_config import get_logger
from app.db.session import get_session
from app.models.user import User
from app.services.activity_service import ActivityService
from app.services.session_service import SESSION_COOKIE_NAME, SessionService
from app.services.user_service import UserService
from app.templates import get_template_context, templates

# Logger pour ce module
logger = get_logger(__name__)

router = APIRouter()

# Stockage temporaire des codes de récupération (en production, utiliser Redis ou la DB)
recovery_codes = {}


def generate_recovery_code() -> str:
    """Génère un code de récupération à 6 chiffres"""
    return "".join(random.choices(string.digits, k=6))


# ===== ROUTES DE LOGIN =====


@router.get("/login", response_class=HTMLResponse, name="login_page")
async def login_get(request: Request, error: str = None):
    """Affiche le formulaire de login"""
    return templates.TemplateResponse("auth/login.html", get_template_context(request, error=error))


@router.post("/login", response_class=HTMLResponse, name="login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False, alias="remember-me"),  # ⬅️ ici
    session: Session = Depends(get_session),
):
    """Traite la soumission du formulaire de login"""

    logger.info(f"Tentative de connexion pour l'utilisateur : {username}")

    # Utiliser le service pour authentifier
    user = UserService.authenticate(session, username, password)

    if not user:
        logger.warning(f"⚠️  Échec de connexion : identifiants incorrects pour {username}")
        return templates.TemplateResponse(
            "auth/login.html", get_template_context(request, error="Email ou mot de passe incorrect")
        )

    # Vérifier si le compte est actif
    if not user.is_active:
        logger.warning(f"⚠️  Tentative de connexion sur compte désactivé : {username}")
        return templates.TemplateResponse(
            "auth/login.html", get_template_context(request, error="Compte désactivé. Contactez l'administrateur.")
        )
    
    # Vérifier si l'utilisateur a accepté la charte de confidentialité
    from app.core.config import settings
    if settings.PRIVACY_POLICY_REQUIRED and not user.privacy_policy_accepted:
        logger.info(f"📋 Redirection vers charte de confidentialité pour {username}")
        # Créer une session temporaire pour rediriger vers la charte
        user_session_temp = SessionService.create_session(
            db_session=session,
            user=user,
            request=request,
            remember_me=False,
        )
        response = RedirectResponse(url=str(request.url_for("privacy_policy_page")), status_code=303)
        SessionService.set_session_cookie(
            response=response,
            session_token=user_session_temp.session_token,
            max_age=600,  # 10 minutes pour accepter la charte
        )
        return response

    # Si authentification réussie, rediriger vers l'accueil
    logger.info(f"✅ Connexion réussie pour l'utilisateur : {user.email} (ID: {user.id})")
    # --- Create session + cookie, en tenant compte de remember_me ---
    user_session = SessionService.create_session(
        db_session=session,
        user=user,
        request=request,
        remember_me=remember_me,  # ⬅️ ici
    )

    response = RedirectResponse(url=str(request.url_for("accueil")), status_code=303)

    # Durée du cookie alignée sur l'expiration de la session
    max_age = 24 * 60 * 60  # 24 heures par défaut
    if getattr(user_session, "expires_at", None):
        from datetime import datetime

        seconds = int((user_session.expires_at - datetime.now()).total_seconds())
        if seconds > 0:
            max_age = seconds

    SessionService.set_session_cookie(
        response=response,
        session_token=user_session.session_token,
        max_age=max_age,  # 24h par défaut, 7j si remember_me=True
    )

    # Logger l'activité de connexion
    try:
        ActivityService.log_activity(
            db_session=session,
            user_id=user.id,
            user_email=user.email,
            user_full_name=user.full_name,
            action_type="login",
            target_type="session",
            description=f"Connexion de {user.full_name or user.email}",
            icon="🔐",
        )
    except Exception as e:
        # Ne pas bloquer la connexion si le log échoue
        logger.warning(f"⚠️  Impossible de logger l'activité de connexion: {e}")

    logger.info(f"🔐 Session créée pour {user.email} | remember_me={remember_me}")
    return response


# ===== ROUTES DE RÉCUPÉRATION DE MOT DE PASSE =====


@router.get("/forgot-password", response_class=HTMLResponse, name="request_password_recovery_get")
async def forgot_password_get(request: Request):
    """Affiche le formulaire de mot de passe oublié"""
    return templates.TemplateResponse("auth/recovery/forgot.html", get_template_context(request))


@router.post("/forgot-password", response_class=HTMLResponse, name="request_password_recovery_post")
async def forgot_password_post(request: Request, email: str = Form(...), session: Session = Depends(get_session)):
    """Génère et envoie un code de récupération"""

    # Vérifier si l'utilisateur existe via le service
    user = UserService.get_by_email(session, email)

    if not user:
        # Pour des raisons de sécurité, ne pas révéler que l'email n'existe pas
        # Rediriger vers la page de vérification quand même
        pass
    else:
        # Générer le code
        code = generate_recovery_code()

        # Stocker le code avec expiration de 15 minutes
        recovery_codes[email] = {"code": code, "expires_at": datetime.now() + timedelta(minutes=15), "attempts": 0}

        # TODO: Envoyer le code par email
        print(f"🔑 Code de récupération pour {email}: {code}")

    # Rediriger vers la page de vérification
    verify_url = request.url_for("verify_recovery_code_get").include_query_params(email=email, success=True)
    return RedirectResponse(url=str(verify_url), status_code=303)


@router.get("/verify-code", response_class=HTMLResponse, name="verify_recovery_code_get")
async def verify_code_get(request: Request, email: str, success: bool = False):
    """Affiche le formulaire de vérification du code"""
    return templates.TemplateResponse(
        "auth/recovery/verify_code.html", get_template_context(request, email=email, success=success)
    )


@router.post("/verify-code", response_class=HTMLResponse, name="verify_recovery_code_post")
async def verify_code_post(request: Request, email: str = Form(...), code: str = Form(...)):
    """Vérifie le code de récupération"""

    # Vérifier si le code existe
    if email not in recovery_codes:
        return templates.TemplateResponse(
            "auth/recovery/verify_code.html",
            get_template_context(request, email=email, error="Code expiré ou invalide. Demandez un nouveau code."),
        )

    recovery_data = recovery_codes[email]

    # Vérifier l'expiration
    if datetime.now() > recovery_data["expires_at"]:
        del recovery_codes[email]
        return templates.TemplateResponse(
            "auth/recovery/verify_code.html",
            get_template_context(request, email=email, error="Code expiré. Demandez un nouveau code."),
        )

    # Limiter les tentatives
    if recovery_data["attempts"] >= 5:
        del recovery_codes[email]
        return templates.TemplateResponse(
            "auth/recovery/verify_code.html",
            get_template_context(request, email=email, error="Trop de tentatives. Demandez un nouveau code."),
        )

    # Vérifier le code
    if code != recovery_data["code"]:
        recovery_data["attempts"] += 1
        return templates.TemplateResponse(
            "auth/recovery/verify_code.html",
            get_template_context(
                request, email=email, error=f"Code incorrect. {5 - recovery_data['attempts']} tentatives restantes."
            ),
        )

    # Code valide, rediriger vers la page de réinitialisation
    reset_url = request.url_for("reset_password_get").include_query_params(email=email, code=code)
    return RedirectResponse(url=str(reset_url), status_code=303)


@router.get("/reset-password", response_class=HTMLResponse, name="reset_password_get")
async def reset_password_get(request: Request, email: str, code: str):
    """Affiche le formulaire de réinitialisation du mot de passe"""

    # Vérifier que le code est toujours valide
    if email not in recovery_codes or recovery_codes[email]["code"] != code:
        forgot_url = request.url_for("request_password_recovery_get")
        return RedirectResponse(url=str(forgot_url), status_code=303)

    return templates.TemplateResponse("auth/recovery/reset.html", get_template_context(request, email=email, code=code))


@router.post("/reset-password", response_class=HTMLResponse, name="reset_password_post")
async def reset_password_post(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_session),
):
    """Réinitialise le mot de passe"""

    # Vérifier que les mots de passe correspondent
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "auth/recovery/reset.html",
            get_template_context(request, email=email, code=code, error="Les mots de passe ne correspondent pas."),
        )

    # Vérifier que le code est toujours valide
    if email not in recovery_codes or recovery_codes[email]["code"] != code:
        return templates.TemplateResponse(
            "auth/recovery/reset.html",
            get_template_context(request, email=email, code=code, error="Code invalide ou expiré."),
        )

    # Récupérer l'utilisateur via le service
    user = UserService.get_by_email(session, email)

    if not user:
        return templates.TemplateResponse(
            "auth/recovery/reset.html",
            get_template_context(request, email=email, code=code, error="Utilisateur introuvable."),
        )

    # Mettre à jour le mot de passe via le service
    success = UserService.update_password(session, user, new_password)

    if not success:
        return templates.TemplateResponse(
            "auth/recovery/reset.html",
            get_template_context(
                request, email=email, code=code, error="Erreur lors de la mise à jour du mot de passe."
            ),
        )

    # Supprimer le code de récupération
    del recovery_codes[email]

    # Rediriger vers le login avec un message de succès
    login_url = request.url_for("login_page").include_query_params(password_reset="success")
    return RedirectResponse(url=str(login_url), status_code=303)


def get_current_user(
    db: Session = Depends(get_session),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = SessionService.get_user_from_session(db_session=db, session_token=session_token)
    if not user:
        # get_user_from_session() gère l’expiration, la désactivation, le refresh de last_activity
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid or expired")
    return user


def require_roles(*roles: Iterable[str]):
    def _dep(current_user: User = Depends(get_current_user)) -> User:
        # Adapte selon ton modèle: current_user.type_user / roles / permissions
        user_role = getattr(current_user, "type_user", None)
        if user_role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return _dep


# ===== ROUTE DE CHARTE DE CONFIDENTIALITÉ =====


@router.get("/privacy-policy", response_class=HTMLResponse, name="privacy_policy_page")
async def privacy_policy_get(
    request: Request,
    view: bool = False,  # Paramètre pour consultation simple
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db_session: Session = Depends(get_session),
):
    """Affiche la charte de confidentialité"""
    from app.core.config import settings
    from datetime import datetime
    
    # Mode consultation (depuis le footer) - ne nécessite pas de connexion
    if view:
        logger.info("📋 Consultation de la charte (mode lecture seule)")
        return templates.TemplateResponse(
            "auth/privacy_policy.html",
            get_template_context(
                request,
                privacy_version=settings.PRIVACY_POLICY_VERSION,
                current_date=datetime.now().strftime("%d/%m/%Y"),
                view_only=True,  # Mode lecture seule
            ),
        )
    
    # Mode acceptation (première connexion)
    # Vérifier que l'utilisateur est connecté (session temporaire créée au login)
    user = None
    if session_token:
        try:
            user = SessionService.get_user_from_session(db_session=db_session, session_token=session_token)
        except Exception as e:
            logger.warning(f"⚠️  Session invalide pour la charte: {e}")
    
    if not user:
        logger.warning("⚠️  Tentative d'accès à la charte sans session valide")
        return RedirectResponse(url=str(request.url_for("login_page")), status_code=303)
    
    # Si l'utilisateur a déjà accepté la charte, rediriger vers l'accueil
    if user.privacy_policy_accepted:
        logger.info(f"✅ Charte déjà acceptée pour {user.email}, redirection vers accueil")
        return RedirectResponse(url=str(request.url_for("accueil")), status_code=303)
    
    logger.info(f"📋 Affichage de la charte pour {user.email}")
    
    return templates.TemplateResponse(
        "auth/privacy_policy.html",
        get_template_context(
            request,
            privacy_version=settings.PRIVACY_POLICY_VERSION,
            current_date=datetime.now().strftime("%d/%m/%Y"),
        ),
    )


@router.post("/privacy-policy", response_class=HTMLResponse, name="accept_privacy_policy")
async def privacy_policy_post(
    request: Request,
    accept: bool = Form(False),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db_session: Session = Depends(get_session),
):
    """Enregistre l'acceptation de la charte"""
    from app.core.config import settings
    from datetime import datetime
    
    # Récupérer l'utilisateur
    user = None
    if session_token:
        try:
            user = SessionService.get_user_from_session(db_session=db_session, session_token=session_token)
        except Exception as e:
            logger.warning(f"⚠️  Session invalide lors de l'acceptation de la charte: {e}")
    
    if not user:
        logger.warning("⚠️  Tentative d'acceptation de la charte sans session valide")
        return RedirectResponse(url=str(request.url_for("login_page")), status_code=303)
    
    if not accept:
        logger.warning(f"⚠️  {user.email} n'a pas accepté la charte")
        return templates.TemplateResponse(
            "auth/privacy_policy.html",
            get_template_context(
                request,
                privacy_version=settings.PRIVACY_POLICY_VERSION,
                current_date=datetime.now().strftime("%d/%m/%Y"),
                error="Vous devez accepter la charte pour continuer",
            ),
        )
    
    # Enregistrer l'acceptation
    user.privacy_policy_accepted = True
    user.privacy_policy_accepted_at = datetime.now()
    user.privacy_policy_version = settings.PRIVACY_POLICY_VERSION
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    logger.info(f"✅ Charte acceptée par {user.email} (version {settings.PRIVACY_POLICY_VERSION})")
    
    # Logger l'activité
    try:
        ActivityService.log_activity(
            db_session=db_session,
            user_id=user.id,
            user_email=user.email,
            user_full_name=user.full_name,
            action_type="privacy_policy",
            target_type="user",
            description=f"Acceptation de la charte de confidentialité v{settings.PRIVACY_POLICY_VERSION}",
            icon="📋",
        )
    except Exception as e:
        logger.warning(f"⚠️  Impossible de logger l'acceptation de la charte: {e}")
    
    # Rediriger vers l'accueil
    return RedirectResponse(url=str(request.url_for("accueil")), status_code=303)


# ===== ROUTE DE DÉCONNEXION =====


@router.get("/logout", response_class=HTMLResponse, name="logout")
async def logout(
    request: Request,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db_session: Session = Depends(get_session),
):
    """Déconnexion de l'utilisateur"""

    logger.info(f"🚪 Tentative de déconnexion...")
    logger.info(f"   Cookie reçu: {session_token[:20] if session_token else 'AUCUN'}...")

    # Récupérer l'utilisateur avant de supprimer la session
    user = None
    try:
        user = SessionService.get_user_from_session(db_session=db_session, session_token=session_token)
        if user:
            logger.info(f"   Utilisateur: {user.email}")
    except Exception as e:
        logger.warning(f"⚠️  Erreur lors de la récupération de l'utilisateur: {e}")

    # Supprimer la session si elle existe
    session_deleted = False
    if session_token:
        session_deleted = SessionService.delete_session(db_session=db_session, session_token=session_token)
        if session_deleted:
            logger.info(f"✅ Session invalidée en base: {session_token[:10]}...")
        else:
            logger.warning(f"⚠️  Session introuvable en base: {session_token[:10]}...")
    else:
        logger.warning("⚠️  Aucun cookie de session trouvé - déconnexion sans session")

    # Logger l'activité de déconnexion
    if user:
        try:
            ActivityService.log_activity(
                db_session=db_session,
                user_id=user.id,
                user_email=user.email,
                user_full_name=user.full_name,
                action_type="logout",
                target_type="session",
                description=f"Déconnexion de {user.full_name or user.email}",
                icon="🚪",
            )
            logger.info(f"📝 Activité de déconnexion enregistrée pour {user.email}")
        except Exception as e:
            logger.warning(f"⚠️  Impossible de logger l'activité de déconnexion: {e}")

    # Créer la réponse de redirection
    login_url = request.url_for("login_page")
    redirect_response = RedirectResponse(url=str(login_url), status_code=303)

    # Supprimer le cookie de session
    SessionService.delete_session_cookie(redirect_response)
    logger.info("🍪 Cookie de session supprimé de la réponse")

    # Ajouter des headers pour empêcher le cache du navigateur
    redirect_response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    redirect_response.headers["Pragma"] = "no-cache"
    redirect_response.headers["Expires"] = "0"

    logger.info("✅ Déconnexion terminée - Redirection vers login")
    return redirect_response
