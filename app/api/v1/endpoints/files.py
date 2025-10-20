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
