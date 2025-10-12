from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.core.enums import FileType, FileStatus, ProgramType


class File(SQLModel, table=True):
    __tablename__ = "file"
    """
    Modèle pour la gestion des fichiers Excel
    
    Attributes:
        id: Identifiant unique
        original_filename: Nom original du fichier
        stored_filename: Nom du fichier stocké (renommé)
        file_path: Chemin complet du fichier
        file_type: Type de fichier (budget, dépenses, etc.)
        program: Programme concerné
        period: Période du fichier (ex: "2024-01", "Q1-2024", "2024")
        title: Titre descriptif du fichier
        description: Description optionnelle
        file_size: Taille du fichier en bytes
        mime_type: Type MIME du fichier
        status: Statut du traitement (uploaded, processing, processed, error)
        processing_error: Message d'erreur si échec
        rows_processed: Nombre de lignes traitées
        rows_failed: Nombre de lignes en échec
        uploaded_by: ID de l'utilisateur ayant uploadé
        processed_at: Date de traitement
        created_at: Date de création
        updated_at: Date de dernière modification
    """
    __tablename__ = "file"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Informations du fichier
    original_filename: str = Field(max_length=500)
    stored_filename: str = Field(max_length=500)
    file_path: str = Field(max_length=1000)
    file_size: int  # En bytes
    mime_type: str = Field(max_length=100, default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Métadonnées
    file_type: str = Field(default=FileType.AUTRE)  # Type de fichier
    program: str = Field(max_length=200)  # Programme concerné
    period: str = Field(max_length=50)  # Période (ex: "2024-01", "Q1-2024")
    title: str = Field(max_length=500)  # Titre descriptif
    description: Optional[str] = Field(default=None, max_length=2000)
    
    # Métadonnées additionnelles (JSON-like)
    metadata_json: Optional[str] = Field(default=None, max_length=5000)
    
    # Traitement
    status: str = Field(default=FileStatus.UPLOADED)
    processing_error: Optional[str] = Field(default=None, max_length=2000)
    rows_processed: int = Field(default=0)
    rows_failed: int = Field(default=0)
    processed_at: Optional[datetime] = None
    
    # Suivi
    uploaded_by: int = Field(foreign_key="user.id")  # ID de l'utilisateur
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_processed(self) -> bool:
        """Vérifie si le fichier a été traité avec succès"""
        return self.status == FileStatus.PROCESSED
    
    @property
    def has_error(self) -> bool:
        """Vérifie si le fichier a une erreur"""
        return self.status == FileStatus.ERROR
    
    @property
    def file_size_mb(self) -> float:
        """Retourne la taille en MB"""
        return round(self.file_size / (1024 * 1024), 2)

