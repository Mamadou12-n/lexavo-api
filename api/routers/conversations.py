"""Router Conversations + User context."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from api.models import (
    CreateConversationRequest, ConversationResponse, ConversationListResponse,
    CreateMessageRequest, MessageResponse, MessageListResponse,
)
from api.auth import get_current_user as _get_current_user

log = logging.getLogger("api.conversations")

router = APIRouter(tags=["conversations"])


@router.get("/user/context")
def get_user_context_endpoint(current_user: Annotated[dict, Depends(_get_current_user)]):
    """Récupérer le contexte utilisateur (région, profession, langue)."""
    from api.database import get_user_context
    return get_user_context(current_user["id"])


@router.put("/user/context")
def update_user_context_endpoint(
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Mettre à jour le contexte utilisateur (région, profession, langue)."""
    from api.database import update_user_context
    return update_user_context(
        current_user["id"],
        region=body.get("region"),
        profession=body.get("profession"),
        language=body.get("language"),
    )


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    request: CreateConversationRequest,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Créer une nouvelle conversation."""
    from api.database import create_conversation as db_create_conv
    conv = db_create_conv(user_id=current_user["id"], title=request.title)
    return ConversationResponse(**conv)


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(current_user: Annotated[dict, Depends(_get_current_user)]):
    """Liste des conversations de l'utilisateur connecté."""
    from api.database import list_conversations as db_list_convs
    convs = db_list_convs(user_id=current_user["id"])
    return ConversationListResponse(
        conversations=[ConversationResponse(**c) for c in convs],
        total=len(convs),
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation_endpoint(
    conversation_id: int,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Supprimer une conversation et tous ses messages (cascade)."""
    from api.database import get_conversation_by_id, delete_conversation

    conv = get_conversation_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    if conv["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    delete_conversation(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
def get_messages(
    conversation_id: int,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Récupérer les messages d'une conversation."""
    from api.database import get_conversation_by_id, list_messages as db_list_msgs

    conv = get_conversation_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    if conv["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    msgs = db_list_msgs(conversation_id)
    return MessageListResponse(
        messages=[MessageResponse(**m) for m in msgs],
        total=len(msgs),
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
def add_message(
    conversation_id: int,
    request: CreateMessageRequest,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Ajouter un message à une conversation."""
    from api.database import get_conversation_by_id, create_message as db_create_msg

    conv = get_conversation_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    if conv["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    if request.role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="Role doit être 'user' ou 'assistant'.")

    msg = db_create_msg(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        sources_json=request.sources_json or "[]",
    )
    return MessageResponse(**msg)
