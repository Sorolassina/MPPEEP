"""
Endpoints API pour la gestion des fichiers
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, UploadFile, status
from fastapi import File as FastAPIFile
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.api.v1.endpoints.auth import get_current_user
from app.core.enums import FileStatus
from app.core.logging_config import get_logger
from app.db.session import get_session
from app.models.user import User
from app.schemas.file import (
    FileListResponse,
    FileProcessingStatus,
    FileResponse,
    FileStatistics,
    FileUpdate,
    FileUploadMetadata,
)
from app.services.activity_service import ActivityService
from app.services.excel_processor import ExcelProcessorService
from app.services.file_service import FileService
from app.templates import get_template_context, templates

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="fichiers")
def fichiers_page(request: Request):
    """Page de gestion des fichiers"""
    return templates.TemplateResponse("pages/fichiers.html", get_template_context(request))


def process_file_background(file_id: int, file_path: str, file_type: str, metadata: dict):
    """Tâche de fond pour traiter un fichier"""
    from app.db.session import engine

    try:
        with Session(engine) as session:
            # Mettre en traitement
            FileService.update_file_status(session, file_id, FileStatus.PROCESSING)

            # Traiter le fichier
            success, rows_processed, rows_failed, error_msg, processed_data = ExcelProcessorService.process_file(
                file_path, file_type, metadata
            )

            # Mettre à jour le statut
            if success:
                FileService.update_file_status(
                    session, file_id, FileStatus.PROCESSED, rows_processed=rows_processed, rows_failed=rows_failed
                )

                # Logger l'activité de traitement réussi
                db_file = FileService.get_file_by_id(session, file_id)
                if db_file:
                    ActivityService.log_activity(
                        db_session=session,
                        user_id=db_file.uploaded_by,
                        user_email="Système",
                        action_type="process",
                        target_type="file",
                        target_id=file_id,
                        description=(
                            f"Traitement terminé du fichier '{metadata.get('title', 'Fichier')}' : "
                            f"{rows_processed} lignes traitées avec succès"
                            f"{f', {rows_failed} échecs' if rows_failed > 0 else ''}"
                        ),
                        icon="✅",
                    )

                logger.info(f"✅ Fichier {file_id} traité avec succès")
            else:
                FileService.update_file_status(
                    session,
                    file_id,
                    FileStatus.ERROR,
                    rows_processed=rows_processed,
                    rows_failed=rows_failed,
                    error_message=error_msg,
                )

                # Logger l'activité d'erreur
                db_file = FileService.get_file_by_id(session, file_id)
                if db_file:
                    ActivityService.log_activity(
                        db_session=session,
                        user_id=db_file.uploaded_by,
                        user_email="Système",
                        action_type="error",
                        target_type="file",
                        target_id=file_id,
                        description=f"Échec du traitement du fichier '{metadata.get('title', 'Fichier')}' : {error_msg[:100]}",
                        icon="❌",
                    )

                logger.error(f"❌ Erreur traitement fichier {file_id}: {error_msg}")

    except Exception as e:
        logger.error(f"❌ Erreur critique traitement fichier {file_id}: {e}", exc_info=True)
        with Session(engine) as session:
            FileService.update_file_status(session, file_id, FileStatus.ERROR, error_message=str(e))


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED, name="upload_file")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = FastAPIFile(...),
    file_type: str = Form(...),
    program: str = Form(...),
    period: str = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload d'un fichier Excel avec métadonnées

    Le fichier sera sauvegardé et mis en file d'attente pour traitement
    """
    # Valider l'extension
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Seuls les fichiers Excel (.xlsx, .xls) sont acceptés"
        )

    # Valider la taille (max 50 MB)
    MAX_SIZE = 50 * 1024 * 1024  # 50 MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le fichier est trop volumineux (max {MAX_SIZE / (1024 * 1024)} MB)",
        )

    # Réinitialiser le curseur du fichier
    await file.seek(0)

    # Préparer les métadonnées
    metadata = {
        "file_type": file_type,
        "program": program,
        "period": period,
        "title": title,
        "description": description,
    }

    # Valider les métadonnées
    try:
        FileUploadMetadata(**metadata)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Métadonnées invalides: {e!s}")

    # Sauvegarder le fichier
    try:
        db_file = await FileService.save_file(session, file, metadata, current_user.id)

        # Lancer le traitement en arrière-plan
        background_tasks.add_task(process_file_background, db_file.id, db_file.file_path, db_file.file_type, metadata)

        # Logger l'activité avec détails
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="upload",
            target_type="file",
            target_id=db_file.id,
            description=(
                f"Upload du fichier '{db_file.title}' "
                f"(type: {db_file.file_type}, programme: {db_file.program}, "
                f"période: {db_file.period}, taille: {db_file.file_size_mb} MB)"
            ),
            icon="📤",
        )

        logger.info(f"✅ Fichier uploadé: ID={db_file.id}, User={current_user.email}")
        return db_file

    except Exception as e:
        logger.error(f"❌ Erreur upload fichier: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur lors de l'upload: {e!s}")


@router.get("/list_files", response_model=FileListResponse, name="list_files")
def list_files(
    skip: int = 0,
    limit: int = 100,
    file_type: str | None = None,
    status: str | None = None,
    program: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Liste tous les fichiers avec filtres optionnels
    """
    files = FileService.get_all_files(
        session, skip=skip, limit=limit, file_type=file_type, status=status, program=program
    )

    total = FileService.count_files(session, file_type=file_type, status=status, program=program)

    return {"total": total, "files": files}


@router.get("/get_file/{file_id}", response_model=FileResponse, name="get_file")
def get_file(file_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Récupère un fichier par son ID
    """
    db_file = FileService.get_file_by_id(session, file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")
    return db_file


@router.get("/get_file_status/{file_id}", response_model=FileProcessingStatus, name="get_file_status")
def get_file_status(
    file_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """
    Récupère le statut de traitement d'un fichier
    """
    db_file = FileService.get_file_by_id(session, file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    return {
        "file_id": db_file.id,
        "status": db_file.status,
        "rows_processed": db_file.rows_processed,
        "rows_failed": db_file.rows_failed,
        "processing_error": db_file.processing_error,
        "processed_at": db_file.processed_at,
    }


@router.patch("/update_file/{file_id}", response_model=FileResponse, name="update_file")
def update_file(
    file_id: int,
    file_update: FileUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Met à jour les métadonnées d'un fichier
    """
    # Préparer les métadonnées à mettre à jour
    metadata = {}
    if file_update.file_type is not None:
        metadata["file_type"] = file_update.file_type
    if file_update.program is not None:
        metadata["program"] = file_update.program
    if file_update.period is not None:
        metadata["period"] = file_update.period
    if file_update.title is not None:
        metadata["title"] = file_update.title
    if file_update.description is not None:
        metadata["description"] = file_update.description

    db_file = FileService.update_file_metadata(session, file_id, metadata)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    logger.info(f"✅ Fichier {file_id} mis à jour par {current_user.email}")
    return db_file


@router.post("/reprocess_file/{file_id}", response_model=FileResponse, name="reprocess_file")
def reprocess_file(
    file_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Relance le traitement d'un fichier
    """
    db_file = FileService.get_file_by_id(session, file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    # Préparer les métadonnées
    metadata = {
        "file_type": db_file.file_type,
        "program": db_file.program,
        "period": db_file.period,
        "title": db_file.title,
        "description": db_file.description,
    }

    # Lancer le traitement en arrière-plan
    background_tasks.add_task(process_file_background, db_file.id, db_file.file_path, db_file.file_type, metadata)

    logger.info(f"🔄 Retraitement du fichier {file_id} par {current_user.email}")
    return db_file


@router.post("/archive_file/{file_id}", response_model=FileResponse, name="archive_file")
def archive_file(file_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Archive un fichier
    """
    db_file = FileService.archive_file(session, file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    # Logger l'activité
    ActivityService.log_activity(
        db_session=session,
        user_id=current_user.id,
        user_email=current_user.email,
        user_full_name=current_user.full_name,
        action_type="archive",
        target_type="file",
        target_id=file_id,
        description=f"Archivage du fichier '{db_file.title}' (type: {db_file.file_type}, période: {db_file.period})",
        icon="📦",
    )

    logger.info(f"📦 Fichier {file_id} archivé par {current_user.email}")
    return db_file


@router.delete("/delete_file/{file_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_file")
def delete_file(file_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Supprime un fichier (base de données et fichier physique)
    """
    # Récupérer les infos du fichier avant suppression
    db_file = FileService.get_file_by_id(session, file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    # Sauvegarder les infos pour l'activité
    file_title = db_file.title
    file_type = db_file.file_type
    file_period = db_file.period

    # Supprimer le fichier
    success = FileService.delete_file(session, file_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    # Logger l'activité
    ActivityService.log_activity(
        db_session=session,
        user_id=current_user.id,
        user_email=current_user.email,
        user_full_name=current_user.full_name,
        action_type="delete",
        target_type="file",
        target_id=file_id,
        description=f"Suppression du fichier '{file_title}' (type: {file_type}, période: {file_period})",
        icon="🗑️",
    )

    logger.info(f"🗑️ Fichier {file_id} supprimé par {current_user.email}")
    return None


@router.get("/get_statistics", response_model=FileStatistics, name="get_statistics")
def get_statistics(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Récupère les statistiques des fichiers
    """
    stats = FileService.get_statistics(session)
    return stats


@router.get("/preview_file/{file_id}", name="preview_file")
def preview_file(
    file_id: int,
    nrows: int = 10,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère un aperçu d'un fichier Excel
    """
    db_file = FileService.get_file_by_id(session, file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    preview = ExcelProcessorService.get_file_preview(db_file.file_path, nrows)

    return {"file_id": file_id, "filename": db_file.original_filename, "preview": preview}


@router.post("/test-upload")
async def test_upload_file(
    request: Request,
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de test pour vérifier que l'upload de fichier fonctionne dans /files/
    """
    logger.info(f"🔍 [FILES] ===== TEST UPLOAD FILE REÇU =====")
    logger.info(f"🔍 [FILES] URL: {request.url}")
    logger.info(f"🔍 [FILES] Method: {request.method}")
    logger.info(f"🔍 [FILES] Headers: {dict(request.headers)}")
    logger.info(f"🔍 [FILES] Filename: {file.filename if file.filename else 'N/A'}")
    
    try:
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"✅ [FILES] Fichier reçu: {file.filename}, taille: {file_size} bytes")
        
        return {
            "success": True,
            "message": "Fichier reçu avec succès dans /files/",
            "filename": file.filename,
            "size": file_size,
            "user": current_user.email
        }
    except Exception as e:
        logger.error(f"❌ [FILES] Erreur dans test-upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du test: {str(e)}"
        )


@router.post("/test-chatbot-upload")
async def test_chatbot_upload_in_files(
    request: Request,
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Endpoint de test qui reproduit EXACTEMENT la logique de /chatbot/upload-document
    mais dans /files/ pour vérifier si le problème vient du chemin /chatbot/
    """
    from datetime import datetime
    from pathlib import Path
    from uuid import uuid4
    from app.core.path_config import path_config
    from app.services.document_extractor import DocumentExtractor
    from app.services.activity_service import ActivityService
    
    logger.info(f"🔍 [FILES] ===== TEST CHATBOT UPLOAD (dans /files/) =====")
    logger.info(f"🔍 [FILES] URL: {request.url}")
    logger.info(f"🔍 [FILES] Method: {request.method}")
    logger.info(f"🔍 [FILES] Headers: {dict(request.headers)}")
    
    try:
        logger.info(f"📤 [FILES] Upload de document reçu: {file.filename if file.filename else 'N/A'} par {current_user.email}")
        
        # Vérifier le type de fichier
        if not file.filename:
            logger.warning("⚠️ Nom de fichier manquant")
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        filename_lower = file.filename.lower()
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md']
        
        if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
            logger.warning(f"⚠️ Type de fichier non supporté: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non supporté. Types acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Vérifier la taille (max 10 MB)
        MAX_SIZE = 10 * 1024 * 1024  # 10 MB
        content = await file.read()
        file_size = len(content)
        logger.info(f"📊 [FILES] Taille du fichier: {file_size / 1024:.2f} KB")
        
        if file_size > MAX_SIZE:
            logger.warning(f"⚠️ Fichier trop volumineux: {file_size / (1024*1024):.2f} MB")
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux (max 10 MB, reçu {file_size / (1024*1024):.2f} MB)"
            )
        
        if not content:
            raise HTTPException(status_code=400, detail="Le fichier est vide.")
        
        # Générer un nom de fichier unique
        extension = Path(file.filename).suffix.lower()
        if not extension:
            extension = ".txt"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{uuid4().hex[:8]}{extension}"
        
        # Créer le dossier pour les documents (dans files/test au lieu de chatbot/documents)
        docs_dir = path_config.UPLOADS_DIR / "files" / "test"
        path_config.ensure_directory_exists(docs_dir)
        
        # Sauvegarder le fichier
        destination = docs_dir / unique_filename
        destination.write_bytes(content)
        
        # Générer les chemins relatifs et URL
        relative_path = f"files/test/{unique_filename}"
        file_url = path_config.get_file_url("uploads", relative_path)
        
        # Extraire le texte directement depuis le contenu
        logger.info(f"🔍 [FILES] Extraction du texte pour {file.filename}...")
        try:
            text = DocumentExtractor.extract_text_from_content(content, file.filename)
            logger.info(f"✅ [FILES] Texte extrait: {len(text) if text else 0} caractères")
        except Exception as e:
            logger.error(f"❌ [FILES] Erreur lors de l'extraction du texte: {e}", exc_info=True)
            if destination.exists():
                destination.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de l'extraction du texte: {str(e)}"
            )
        
        if not text or len(text.strip()) == 0:
            logger.warning(f"⚠️ [FILES] Document vide: {file.filename}")
            if destination.exists():
                destination.unlink()
            raise HTTPException(
                status_code=400,
                detail="Le document ne contient pas de texte extractible."
            )
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="upload",
            target_type="test_document",
            description=f"Test upload document (copie de chatbot) ({file.filename})",
            icon="📄",
        )
        
        logger.info(f"✅ [FILES] Document traité et sauvegardé: {file.filename} ({len(text)} caractères)")
        
        return {
            "success": True,
            "filename": file.filename,
            "saved_filename": unique_filename,
            "path": relative_path,
            "url": file_url,
            "file_size": file_size,
            "text": text,
            "text_length": len(text),
            "message": "✅ Test réussi ! L'endpoint fonctionne dans /files/"
        }
        
    except HTTPException as e:
        logger.error(f"❌ [FILES] HTTPException lors de l'upload: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ [FILES] Erreur inattendue lors de l'upload du document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement du document: {str(e)}"
        )