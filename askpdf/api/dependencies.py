"""Shared FastAPI dependencies and process-local application state."""

from __future__ import annotations

from askpdf.config import settings
from askpdf.service import AskPDF

askpdf_service = AskPDF(settings)
conversation_store: dict[str, list[dict[str, str]]] = {}
