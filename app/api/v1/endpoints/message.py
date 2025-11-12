"""
Endpoints pour la messagerie interne
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlmodel import Session, func, select

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_session
from app.models.message import Conversation, Message
from app.models.user import User
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/conversations", response_model=List[dict])
def list_conversations(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Liste toutes les conversations de l'utilisateur connecté
    Retourne les conversations triées par date de dernier message (plus récent en premier)
    """
    # Récupérer toutes les conversations où l'utilisateur est user1 ou user2
    conversations = session.exec(
        select(Conversation)
        .where(
            (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
        )
        .where(
            # Ne pas inclure les conversations archivées par l'utilisateur
            (
                ((Conversation.user1_id == current_user.id) & (Conversation.archived_user1 == False))
                | ((Conversation.user2_id == current_user.id) & (Conversation.archived_user2 == False))
            )
        )
        .order_by(Conversation.last_message_at.desc().nulls_last())
    ).all()
    
    result = []
    for conv in conversations:
        # Déterminer qui est l'autre utilisateur
        other_user_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
        other_user = session.get(User, other_user_id)
        
        # Déterminer le nombre de messages non lus pour cet utilisateur
        unread_count = conv.unread_count_user1 if conv.user1_id == current_user.id else conv.unread_count_user2
        
        result.append({
            "id": conv.id,
            "other_user_id": other_user_id,
            "other_user_name": other_user.full_name if other_user else "Utilisateur supprimé",
            "other_user_email": other_user.email if other_user else "",
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "last_message_preview": conv.last_message_preview or "",
            "unread_count": unread_count,
        })
    
    return result


@router.get("/conversations/{conversation_id}/messages", response_model=List[dict])
def get_messages(
    conversation_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère tous les messages d'une conversation
    """
    # Vérifier que l'utilisateur fait partie de cette conversation
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(404, "Conversation non trouvée")
    
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(403, "Accès non autorisé à cette conversation")
    
    # Récupérer les messages
    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    ).all()
    
    # Marquer les messages comme lus pour cet utilisateur
    unread_messages = [m for m in messages if m.receiver_id == current_user.id and not m.is_read]
    if unread_messages:
        for msg in unread_messages:
            msg.is_read = True
            msg.read_at = datetime.now()
        session.add_all(unread_messages)
        session.commit()
        
        # Mettre à jour le compteur de non lus dans la conversation
        if conversation.user1_id == current_user.id:
            conversation.unread_count_user1 = 0
        else:
            conversation.unread_count_user2 = 0
        session.add(conversation)
        session.commit()
    
    result = []
    for msg in messages:
        sender = session.get(User, msg.sender_id)
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": sender.full_name if sender else "Utilisateur supprimé",
            "receiver_id": msg.receiver_id,
            "content": msg.content,
            "is_read": msg.is_read,
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
            "attachment_path": msg.attachment_path,
            "created_at": msg.created_at.isoformat(),
            "is_own": msg.sender_id == current_user.id,
        })
    
    return result


@router.post("/send", response_model=dict)
async def create_message(
    receiver_id: int = Body(...),
    content: str = Body(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Crée un nouveau message ou une nouvelle conversation si elle n'existe pas
    """
    content = content.strip()
    
    if not content:
        raise HTTPException(400, "Le contenu du message ne peut pas être vide")
    
    if current_user.id == receiver_id:
        raise HTTPException(400, "Vous ne pouvez pas vous envoyer un message à vous-même")
    
    receiver = session.get(User, receiver_id)
    if not receiver:
        raise HTTPException(404, "Destinataire non trouvé")
    
    # Chercher une conversation existante entre ces deux utilisateurs
    conversation = session.exec(
        select(Conversation)
        .where(
            ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == receiver_id))
            | ((Conversation.user1_id == receiver_id) & (Conversation.user2_id == current_user.id))
        )
    ).first()
    
    # Si pas de conversation, en créer une nouvelle
    if not conversation:
        conversation = Conversation(
            user1_id=current_user.id,
            user2_id=receiver_id,
            unread_count_user1=0,
            unread_count_user2=0,
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
    
    # Créer le message
    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content.strip(),
        is_read=False,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    
    # Mettre à jour la conversation (dernier message, preview, compteur non lus)
    conversation.last_message_at = message.created_at
    conversation.last_message_preview = content[:200] if len(content) > 200 else content
    # Incrémenter le compteur de non lus pour le destinataire
    if conversation.user1_id == receiver_id:
        conversation.unread_count_user1 += 1
    else:
        conversation.unread_count_user2 += 1
    
    session.add(conversation)
    session.commit()
    
    logger.info(f"Message créé: {current_user.email} -> {receiver.email}")
    
    return {
        "ok": True,
        "message_id": message.id,
        "conversation_id": conversation.id,
    }


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Retourne le nombre total de messages non lus pour l'utilisateur connecté
    """
    conversations = session.exec(
        select(Conversation)
        .where(
            (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
        )
    ).all()
    
    total_unread = 0
    for conv in conversations:
        if conv.user1_id == current_user.id:
            total_unread += conv.unread_count_user1
        else:
            total_unread += conv.unread_count_user2
    
    return {"unread_count": total_unread}


@router.get("/users/search", response_model=List[dict])
def search_users(
    q: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Recherche des utilisateurs pour créer une nouvelle conversation
    Exclut l'utilisateur connecté
    """
    query = select(User).where(User.is_active == True).where(User.id != current_user.id)
    
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.where(
            (User.full_name.ilike(search_term)) | (User.email.ilike(search_term))
        )
    else:
        # Si pas de terme de recherche, retourner les 20 premiers utilisateurs actifs
        query = query.limit(20)
    
    users = session.exec(query.order_by(User.full_name.asc())).all()
    
    return [
        {
            "id": user.id,
            "full_name": user.full_name or user.email,
            "email": user.email,
        }
        for user in users
    ]

