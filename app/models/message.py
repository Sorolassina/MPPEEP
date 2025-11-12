"""
Modèles pour la messagerie interne
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    """
    Conversation entre deux utilisateurs
    Une conversation est créée automatiquement lors du premier message
    """
    __tablename__ = "conversation"

    id: Optional[int] = Field(default=None, primary_key=True)
    user1_id: int = Field(foreign_key="user.id", index=True)  # Créateur de la conversation
    user2_id: int = Field(foreign_key="user.id", index=True)  # Destinataire
    
    # Dernière activité
    last_message_at: Optional[datetime] = Field(default=None)
    last_message_preview: Optional[str] = Field(default=None, max_length=200)
    
    # Messages non lus pour user1 et user2
    unread_count_user1: int = Field(default=0)
    unread_count_user2: int = Field(default=0)
    
    # Archivage (optionnel)
    archived_user1: bool = Field(default=False)
    archived_user2: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Message(SQLModel, table=True):
    """
    Message dans une conversation
    """
    __tablename__ = "message"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    
    sender_id: int = Field(foreign_key="user.id", index=True)  # Expéditeur
    receiver_id: int = Field(foreign_key="user.id", index=True)  # Destinataire
    
    content: str = Field()  # Contenu du message (texte)
    
    # Statut de lecture
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = Field(default=None)
    
    # Pièce jointe (optionnel - pour fichiers, images, etc.)
    attachment_path: Optional[str] = Field(default=None, max_length=500)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

