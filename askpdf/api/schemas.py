"""Pydantic models used by the HTTP API."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: str | None = None
    allow_general_knowledge: bool = False
