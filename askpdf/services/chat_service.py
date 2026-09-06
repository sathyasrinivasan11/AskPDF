"""Business logic and response mapping for the chat endpoint."""

from __future__ import annotations

from askpdf.answering import citation_label
from askpdf.service import AskPDF


def answer_chat(
    service: AskPDF,
    message: str,
    conversation_id: str,
    history: list[dict[str, str]],
    allow_general_knowledge: bool,
) -> dict:
    answer = service.ask(
        message,
        allow_general_knowledge=allow_general_knowledge,
        conversation_history=history,
    )
    return {
        "answer": answer.text,
        "conversation_id": conversation_id,
        "needs_clarification": answer.needs_clarification,
        "clarification_question": answer.clarification_question,
        "not_found": answer.not_found,
        "used_general_knowledge": answer.used_general_knowledge,
        "citations": [_citation_payload(result) for result in answer.citations],
    }


def _citation_payload(result) -> dict:
    metadata = result.metadata
    page = metadata.get("page", 1)
    document_id = metadata.get("document_id", "")
    return {
        "label": citation_label(result),
        "filename": metadata.get("filename", "document.pdf"),
        "page": page,
        "section": metadata.get("section", "Document"),
        "document_id": document_id,
        "url": f"/documents/{document_id}/file#page={page}",
    }
