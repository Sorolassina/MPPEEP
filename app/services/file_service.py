"""
Service de gestion des fichiers
Gère les opérations CRUD et le stockage des fichiers
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlmodel import Session, select

from app.core.enums import FileStatus
from app.core.logging_config import get_logger
from app.core.path_config import path_config
from app.models.file import File

logger = get_logger(__name__)


class FileService:
    """Service pour gérer les fichiers"""

    # Dossiers de stockage (depuis path_config)
    RAW_DIR = path_config.UPLOADS_FILES_RAW_DIR
    PROCESSED_DIR = path_config.UPLOADS_FILES_PROCESSED_DIR
    ARCHIVE_DIR = path_config.UPLOADS_FILES_ARCHIVE_DIR

    @classmethod
    def _ensure_directories(cls):
        """Vérifie que les dossiers nécessaires existent (normalement déjà créés au démarrage)"""
        # Les dossiers sont déjà créés par path_config au démarrage
        # On vérifie juste au cas où
        path_config.ensure_directory_exists(cls.RAW_DIR)
        path_config.ensure_directory_exists(cls.PROCESSED_DIR)
        path_config.ensure_directory_exists(cls.ARCHIVE_DIR)
        logger.debug("✅ Dossiers de fichiers vérifiés")

    @classmethod
    def _generate_stored_filename(cls, metadata: dict, original_filename: str) -> str:
        """
        Génère le nom du fichier stocké basé sur les métadonnées
        Format: {file_type}_{program}_{period}_{timestamp}.xlsx
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = Path(original_filename).suffix

        # Nettoyer les noms (enlever espaces et caractères spéciaux)
        file_type = metadata.get("file_type", "autre").replace(" ", "_")
        program = metadata.get("program", "unknown").replace(" ", "_")
        period = metadata.get("period", "unknown").replace(" ", "_")

        stored_name = f"{file_type}_{program}_{period}_{timestamp}{extension}"
        return stored_name

    @classmethod
    async def save_file(cls, session: Session, upload_file: UploadFile, metadata: dict, uploaded_by: int) -> File:
        """
        Sauvegarde un fichier et crée l'entrée en base de données

        Args:
            session: Session de base de données
            upload_file: Fichier uploadé
            metadata: Métadonnées du fichier
            uploaded_by: ID de l'utilisateur

        Returns:
            File: Objet File créé
        """
        cls._ensure_directories()

        # Générer le nom de fichier stocké
        stored_filename = cls._generate_stored_filename(metadata, upload_file.filename)
        file_path = cls.RAW_DIR / stored_filename

        # Sauvegarder le fichier physiquement
        try:
            with open(file_path, "wb") as buffer:
                content = await upload_file.read()
                buffer.write(content)

            file_size = os.path.getsize(file_path)
            logger.info(f"✅ Fichier sauvegardé: {stored_filename} ({file_size} bytes)")

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde du fichier: {e}")
            raise

        # Créer l'entrée en base de données
        db_file = File(
            original_filename=upload_file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=upload_file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_type=metadata.get("file_type"),
            program=metadata.get("program"),
            period=metadata.get("period"),
            title=metadata.get("title"),
            description=metadata.get("description"),
            status=FileStatus.UPLOADED,
            uploaded_by=uploaded_by,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        session.add(db_file)
        session.commit()
        session.refresh(db_file)

        logger.info(f"✅ Fichier créé en DB: ID={db_file.id}")
        return db_file

    @classmethod
    def get_file_by_id(cls, session: Session, file_id: int) -> File | None:
        """Récupère un fichier par son ID"""
        statement = select(File).where(File.id == file_id)
        return session.exec(statement).first()

    @classmethod
    def get_all_files(
        cls,
        session: Session,
        skip: int = 0,
        limit: int = 100,
        file_type: str | None = None,
        status: str | None = None,
        program: str | None = None,
    ) -> list[File]:
        """
        Récupère tous les fichiers avec filtres optionnels
        """
        statement = select(File)

        if file_type:
            statement = statement.where(File.file_type == file_type)
        if status:
            statement = statement.where(File.status == status)
        if program:
            statement = statement.where(File.program == program)

        statement = statement.offset(skip).limit(limit).order_by(File.created_at.desc())
        return list(session.exec(statement).all())

    @classmethod
    def count_files(
        cls, session: Session, file_type: str | None = None, status: str | None = None, program: str | None = None
    ) -> int:
        """Compte les fichiers avec filtres optionnels"""
        statement = select(File)

        if file_type:
            statement = statement.where(File.file_type == file_type)
        if status:
            statement = statement.where(File.status == status)
        if program:
            statement = statement.where(File.program == program)

        return len(list(session.exec(statement).all()))

    @classmethod
    def update_file_status(
        cls,
        session: Session,
        file_id: int,
        status: str,
        rows_processed: int = 0,
        rows_failed: int = 0,
        error_message: str | None = None,
    ) -> File | None:
        """Met à jour le statut de traitement d'un fichier"""
        db_file = cls.get_file_by_id(session, file_id)
        if not db_file:
            return None

        db_file.status = status
        db_file.rows_processed = rows_processed
        db_file.rows_failed = rows_failed
        db_file.processing_error = error_message
        db_file.updated_at = datetime.now()

        if status == FileStatus.PROCESSED:
            db_file.processed_at = datetime.now()

        session.add(db_file)
        session.commit()
        session.refresh(db_file)

        logger.info(f"✅ Statut du fichier {file_id} mis à jour: {status}")
        return db_file

    @classmethod
    def update_file_metadata(cls, session: Session, file_id: int, metadata: dict) -> File | None:
        """Met à jour les métadonnées d'un fichier"""
        db_file = cls.get_file_by_id(session, file_id)
        if not db_file:
            return None

        # Mettre à jour les champs fournis
        if "file_type" in metadata:
            db_file.file_type = metadata["file_type"]
        if "program" in metadata:
            db_file.program = metadata["program"]
        if "period" in metadata:
            db_file.period = metadata["period"]
        if "title" in metadata:
            db_file.title = metadata["title"]
        if "description" in metadata:
            db_file.description = metadata["description"]

        db_file.updated_at = datetime.now()

        session.add(db_file)
        session.commit()
        session.refresh(db_file)

        logger.info(f"✅ Métadonnées du fichier {file_id} mises à jour")
        return db_file

    @classmethod
    def delete_file(cls, session: Session, file_id: int) -> bool:
        """Supprime un fichier (base de données et fichier physique)"""
        db_file = cls.get_file_by_id(session, file_id)
        if not db_file:
            return False

        # Supprimer le fichier physique
        try:
            file_path = Path(db_file.file_path)
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"✅ Fichier physique supprimé: {file_path}")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la suppression du fichier physique: {e}")

        # Supprimer l'entrée en DB
        session.delete(db_file)
        session.commit()

        logger.info(f"✅ Fichier {file_id} supprimé de la DB")
        return True

    @classmethod
    def archive_file(cls, session: Session, file_id: int) -> File | None:
        """Archive un fichier (déplace vers le dossier archive)"""
        db_file = cls.get_file_by_id(session, file_id)
        if not db_file:
            return None

        cls._ensure_directories()

        # Déplacer le fichier physique
        try:
            old_path = Path(db_file.file_path)
            new_path = cls.ARCHIVE_DIR / db_file.stored_filename

            if old_path.exists():
                shutil.move(str(old_path), str(new_path))
                logger.info(f"✅ Fichier déplacé vers archive: {new_path}")

            # Mettre à jour le chemin et le statut
            db_file.file_path = str(new_path)
            db_file.status = FileStatus.ARCHIVED
            db_file.updated_at = datetime.now()

            session.add(db_file)
            session.commit()
            session.refresh(db_file)

            return db_file

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'archivage du fichier: {e}")
            return None

    @classmethod
    def get_statistics(cls, session: Session) -> dict:
        """Récupère les statistiques des fichiers"""
        all_files = cls.get_all_files(session, limit=1000)

        # Compter par statut
        files_by_status = {}
        for status in FileStatus:
            files_by_status[status.value] = sum(1 for f in all_files if f.status == status.value)

        # Compter par type
        files_by_type = {}
        for file in all_files:
            files_by_type[file.file_type] = files_by_type.get(file.file_type, 0) + 1

        # Compter par programme
        files_by_program = {}
        for file in all_files:
            files_by_program[file.program] = files_by_program.get(file.program, 0) + 1

        # Taille totale
        total_size_mb = sum(f.file_size for f in all_files) / (1024 * 1024)

        # Fichiers récents
        recent_uploads = sorted(all_files, key=lambda x: x.created_at, reverse=True)[:10]

        return {
            "total_files": len(all_files),
            "files_by_status": files_by_status,
            "files_by_type": files_by_type,
            "files_by_program": files_by_program,
            "total_size_mb": round(total_size_mb, 2),
            "recent_uploads": recent_uploads,
        }
