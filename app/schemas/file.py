from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from app.core.enums import FileType, FileStatus, ProgramType


class FileUploadMetadata(BaseModel):
    """
    Schéma pour les métadonnées lors de l'upload d'un fichier
    """
    file_type: str = Field(..., description="Type de fichier")
    program: str = Field(..., min_length=1, max_length=200, description="Programme concerné")
    period: str = Field(..., min_length=1, max_length=50, description="Période (ex: 2024-01)")
    title: str = Field(..., min_length=1, max_length=500, description="Titre du fichier")
    description: Optional[str] = Field(None, max_length=2000, description="Description optionnelle")
    
    @validator('file_type')
    def validate_file_type(cls, v):
        """Valide que le type de fichier est dans la liste"""
        valid_types = [ft.value for ft in FileType]
        if v not in valid_types:
            raise ValueError(f"Type de fichier invalide. Doit être parmi: {', '.join(valid_types)}")
        return v
    
    @validator('period')
    def validate_period(cls, v):
        """Valide le format de la période"""
        if not v or len(v.strip()) == 0:
            raise ValueError("La période est obligatoire")
        return v.strip()


class FileResponse(BaseModel):
    """
    Schéma de réponse pour un fichier
    """
    id: int
    original_filename: str
    stored_filename: str
    file_size: int
    file_size_mb: float
    mime_type: str
    file_type: str
    program: str
    period: str
    title: str
    description: Optional[str]
    status: str
    processing_error: Optional[str]
    rows_processed: int
    rows_failed: int
    uploaded_by: int
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """
    Schéma de réponse pour la liste des fichiers
    """
    total: int
    files: list[FileResponse]


class FileProcessingStatus(BaseModel):
    """
    Schéma pour le statut de traitement d'un fichier
    """
    file_id: int
    status: str
    rows_processed: int
    rows_failed: int
    processing_error: Optional[str]
    processed_at: Optional[datetime]


class FileUpdate(BaseModel):
    """
    Schéma pour la mise à jour des métadonnées d'un fichier
    """
    file_type: Optional[str] = None
    program: Optional[str] = None
    period: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    @validator('file_type')
    def validate_file_type(cls, v):
        """Valide que le type de fichier est dans la liste"""
        if v is not None:
            valid_types = [ft.value for ft in FileType]
            if v not in valid_types:
                raise ValueError(f"Type de fichier invalide. Doit être parmi: {', '.join(valid_types)}")
        return v


class FileStatistics(BaseModel):
    """
    Schéma pour les statistiques des fichiers
    """
    total_files: int
    files_by_status: dict[str, int]
    files_by_type: dict[str, int]
    files_by_program: dict[str, int]
    total_size_mb: float
    recent_uploads: list[FileResponse]

