"""
Routes d'administration
Gestion des utilisateurs, paramètres système, etc.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session, select
from typing import List, Dict, Optional

from app.db.session import get_session
from app.models.user import User
from app.models.system_settings import SystemSettings
from app.templates import templates, get_template_context
from app.api.v1.endpoints.auth import require_roles
from app.core.logging_config import get_logger
from app.core.security import get_password_hash
from app.core.enums import UserType
from app.core.path_config import path_config
from app.services.system_settings_service import SystemSettingsService
from app.services.activity_service import ActivityService

logger = get_logger(__name__)

router = APIRouter()


@router.get("/gestion-utilisateurs", response_class=HTMLResponse, name="gestion_utilisateurs")
def gestion_utilisateurs(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """
    Page de gestion des utilisateurs (admin seulement)
    
    Args:
        request: Requête FastAPI
        session: Session de base de données
        current_user: Utilisateur connecté (doit être admin)
    
    Returns:
        Template HTML avec la liste des utilisateurs
    """
    logger.info(f"👤 Accès page gestion utilisateurs par {current_user.email}")
    
    # Récupérer tous les utilisateurs
    users = []
    try:
        all_users = session.exec(select(User)).all()
        # Convertir en dicts pour éviter les problèmes de session SQLAlchemy
        users = [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "type_user": u.type_user,
                "is_active": u.is_active,
                "profile_picture": u.profile_picture,
                "created_at": u.created_at
            }
            for u in all_users
        ]
        logger.info(f"📊 {len(users)} utilisateurs récupérés")
    except Exception as e:
        logger.error(f"❌ Erreur récupération utilisateurs: {e}")
    
    return templates.TemplateResponse(
        "pages/gestion_utilisateurs.html",
        get_template_context(request, users=users)
    )


@router.get("/parametres-systeme", response_class=HTMLResponse, name="parametres_systeme")
def parametres_systeme(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """
    Page des paramètres système (admin seulement)
    
    Args:
        request: Requête FastAPI
        session: Session de base de données
        current_user: Utilisateur connecté (doit être admin)
    
    Returns:
        Template HTML des paramètres système
    """
    logger.info(f"⚙️  Accès paramètres système par {current_user.email}")
    
    # Récupérer les paramètres actuels
    settings = SystemSettingsService.get_settings_as_dict(session)
    
    return templates.TemplateResponse(
        "pages/parametres_systeme.html",
        get_template_context(request, settings=settings)
    )


@router.get("/gestion-utilisateurs/aide", response_class=HTMLResponse, name="aide_utilisateurs")
def aide_utilisateurs(request: Request):
    """Page d'aide pour la gestion des utilisateurs"""
    return templates.TemplateResponse(
        "pages/aide_utilisateurs.html",
        get_template_context(request)
    )


@router.get("/parametres-systeme/aide", response_class=HTMLResponse, name="aide_parametres")
def aide_parametres(request: Request):
    """Page d'aide pour les paramètres système"""
    return templates.TemplateResponse(
        "pages/aide_parametres.html",
        get_template_context(request)
    )


@router.get("/rapports", response_class=HTMLResponse, name="rapports")
def rapports(
    request: Request,
    current_user: User = Depends(require_roles("admin", "moderator"))
):
    """
    Page des rapports (admin et modérateur)
    
    Args:
        request: Requête FastAPI
        current_user: Utilisateur connecté (admin ou moderator)
    
    Returns:
        Template HTML des rapports
    """
    logger.info(f"📊 Accès rapports par {current_user.email}")
    
    # TODO: Implémenter la page des rapports
    return templates.TemplateResponse(
        "pages/rapports.html",
        get_template_context(
            request,
            message="Page en développement"
        )
    )



# ===== CRUD UTILISATEURS =====

@router.post("/users/create", name="create_user_api")
async def create_user(
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    type_user: str = Form("user"),
    is_active: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """Créer un nouveau utilisateur"""
    try:
        # Vérifier si l'email existe déjà
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Un utilisateur avec cet email existe déjà"}
            )
        
        # Créer l'utilisateur
        new_user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            type_user=type_user,
            is_active=(is_active == "on")  # Checkbox envoie "on" si coché
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="user",
            target_id=new_user.id,
            description=f"Création de l'utilisateur {full_name} ({email})"
        )
        
        logger.info(f"✅ Utilisateur créé: {email} par {current_user.email}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Utilisateur {email} créé avec succès",
                "user": {
                    "id": new_user.id,
                    "email": new_user.email,
                    "full_name": new_user.full_name
                }
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur création utilisateur: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.post("/users/{user_id}/update", name="update_user_api")
async def update_user(
    user_id: int,
    email: str = Form(...),
    full_name: str = Form(...),
    type_user: str = Form(...),
    is_active: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """Mettre à jour un utilisateur"""
    try:
        user = session.get(User, user_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Utilisateur non trouvé"}
            )
        
        # Vérifier si l'email est déjà utilisé par un autre utilisateur
        if email != user.email:
            existing = session.exec(select(User).where(User.email == email)).first()
            if existing:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Cet email est déjà utilisé"}
                )
        
        # Mettre à jour les champs
        user.email = email
        user.full_name = full_name
        user.type_user = type_user
        user.is_active = (is_active == "on")  # Checkbox envoie "on" si coché, None sinon
        
        # Mettre à jour le mot de passe si fourni
        if password and password.strip():
            user.hashed_password = get_password_hash(password)
        
        session.add(user)
        session.commit()
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="user",
            target_id=user.id,
            description=f"Modification de l'utilisateur {full_name} ({email})"
        )
        
        logger.info(f"✏️  Utilisateur modifié: {email} par {current_user.email}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Utilisateur {email} modifié avec succès"
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur modification utilisateur: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.post("/users/{user_id}/delete", name="delete_user_api")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """Supprimer un utilisateur"""
    try:
        user = session.get(User, user_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Utilisateur non trouvé"}
            )
        
        # Empêcher la suppression de son propre compte
        if user.id == current_user.id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Vous ne pouvez pas supprimer votre propre compte"}
            )
        
        email = user.email
        full_name = user.full_name
        
        # Logger l'activité AVANT de supprimer
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="delete",
            target_type="user",
            target_id=user.id,
            description=f"Suppression de l'utilisateur {full_name or email} ({email})"
        )
        
        session.delete(user)
        session.commit()
        
        logger.info(f"🗑️  Utilisateur supprimé: {email} par {current_user.email}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Utilisateur {email} supprimé avec succès"
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur suppression utilisateur: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.get("/users/{user_id}/get", name="get_user_api")
async def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """Récupérer les détails d'un utilisateur"""
    try:
        user = session.get(User, user_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Utilisateur non trouvé"}
            )
        
        return JSONResponse(
            content={
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "type_user": user.type_user,
                    "is_active": user.is_active,
                    "profile_picture": user.profile_picture
                }
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur récupération utilisateur: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.post("/users/{user_id}/upload-photo", name="upload_user_photo_api")
async def upload_user_photo(
    user_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """Upload de la photo de profil d'un utilisateur"""
    try:
        import aiofiles
        from pathlib import Path
        from datetime import datetime
        
        user = session.get(User, user_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Utilisateur non trouvé"}
            )
        
        # Récupérer le fichier
        form = await request.form()
        photo_file = form.get('photo')
        
        if not photo_file or not hasattr(photo_file, 'filename'):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Aucun fichier fourni"}
            )
        
        # Vérifier le type de fichier
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_ext = Path(photo_file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Format non supporté (JPG, PNG, GIF, WEBP uniquement)"}
            )
        
        # Vérifier la taille (2MB max pour les photos de profil)
        content = await photo_file.read()
        if len(content) > 2 * 1024 * 1024:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Fichier trop volumineux (max 2MB)"}
            )
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"profile_{user_id}_{timestamp}{file_ext}"
        
        # Créer le dossier uploads/profiles s'il n'existe pas
        profiles_dir = path_config.UPLOADS_DIR / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder le fichier
        file_path = profiles_dir / new_filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Supprimer l'ancienne photo si elle existe
        if user.profile_picture:
            old_path = path_config.UPLOADS_DIR / user.profile_picture
            if old_path.exists():
                old_path.unlink()
        
        # Mettre à jour l'utilisateur
        relative_path = f"profiles/{new_filename}"
        user.profile_picture = relative_path
        session.add(user)
        session.commit()
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="upload",
            target_type="profile_picture",
            target_id=user.id,
            description=f"Upload de la photo de profil pour {user.full_name or user.email}",
            icon="📸"
        )
        
        logger.info(f"📸 Photo de profil uploadée pour {user.email} par {current_user.email}")
        
        # Générer l'URL avec ROOT_PATH si nécessaire
        photo_url = path_config.get_file_url("uploads", relative_path)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Photo de profil uploadée avec succès",
                "photo_url": photo_url
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur upload photo: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )



# ===== GESTION PARAMÈTRES SYSTÈME =====

@router.post("/settings/update", name="update_settings_api")
async def update_system_settings(
    company_name: str = Form(...),
    company_description: Optional[str] = Form(None),
    company_email: Optional[str] = Form(None),
    company_phone: Optional[str] = Form(None),
    company_address: Optional[str] = Form(None),
    primary_color: str = Form("#ffd300"),
    secondary_color: str = Form("#036c1d"),
    accent_color: str = Form("#e63600"),
    footer_text: Optional[str] = Form(None),
    maintenance_mode: Optional[str] = Form(None),
    allow_registration: Optional[str] = Form(None),
    max_upload_size_mb: int = Form(10),
    session_timeout_minutes: int = Form(30),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """Mettre à jour les paramètres système"""
    try:
        settings_data = {
            "company_name": company_name,
            "company_description": company_description,
            "company_email": company_email,
            "company_phone": company_phone,
            "company_address": company_address,
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "accent_color": accent_color,
            "footer_text": footer_text,
            "maintenance_mode": (maintenance_mode == "on"),
            "allow_registration": (allow_registration == "on"),
            "max_upload_size_mb": max_upload_size_mb,
            "session_timeout_minutes": session_timeout_minutes,
        }
        
        SystemSettingsService.update_settings(
            db_session=session,
            user_id=current_user.id,
            **settings_data
        )
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="settings",
            target_type="system",
            description=f"Mise à jour des paramètres système",
            icon="⚙️"
        )
        
        logger.info(f"⚙️  Paramètres système mis à jour par {current_user.email}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Paramètres système mis à jour avec succès"
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur mise à jour paramètres: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.post("/settings/upload-logo", name="upload_logo_api")
async def upload_logo(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("admin"))
):
    """Upload d'un nouveau logo"""
    try:
        from fastapi import UploadFile, File
        import aiofiles
        from pathlib import Path
        
        # Récupérer le fichier
        form = await request.form()
        logo_file = form.get('logo')
        
        if not logo_file or not hasattr(logo_file, 'filename'):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Aucun fichier fourni"}
            )
        
        # Vérifier le type de fichier
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_ext = Path(logo_file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Format de fichier non supporté"}
            )
        
        # Nom de fichier fixe : logo + extension
        new_filename = f"logo{file_ext}"
        
        # Sauvegarder le fichier
        logo_dir = path_config.STATIC_IMAGES_DIR
        logo_dir.mkdir(parents=True, exist_ok=True)
        file_path = logo_dir / new_filename
        
        # Supprimer TOUS les anciens logos (logo.png, logo.jpg, etc.)
        for old_logo in logo_dir.glob("logo.*"):
            try:
                old_logo.unlink()
                logger.info(f"🗑️ Ancien logo supprimé: {old_logo.name}")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de supprimer l'ancien logo {old_logo.name}: {e}")
        
        # Lire et écrire le nouveau fichier
        content = await logo_file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Mettre à jour les paramètres
        logo_relative_path = f"images/{new_filename}"
        SystemSettingsService.update_settings(
            db_session=session,
            user_id=current_user.id,
            logo_path=logo_relative_path
        )
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="upload",
            target_type="logo",
            description=f"Upload du logo entreprise ({new_filename})",
            icon="🖼️"
        )
        
        logger.info(f"📁 Logo uploadé: {new_filename} par {current_user.email}")
        
        # Générer l'URL avec ROOT_PATH si nécessaire
        logo_url = path_config.get_file_url("static", logo_relative_path)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Logo uploadé avec succès",
                "logo_url": logo_url
            }
        )
    except Exception as e:
        logger.error(f"❌ Erreur upload logo: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


# Export du router
__all__ = ["router"]


