"""Conversation routes."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from askpdf.api.dependencies import askpdf_service, conversation_store
from askpdf.api.schemas import ChatRequest
from askpdf.services.chat_service import answer_chat

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(request: ChatRequest) -> dict:
    conversation_id = request.conversation_id or str(uuid4())
    history = conversation_store.setdefault(conversation_id, [])
    try:
        payload = answer_chat(
            askpdf_service,
            request.message,
            conversation_id,
            history,
            request.allow_general_knowledge,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    history.extend(
        [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": payload["answer"]},
        ]
    )
    return payload
