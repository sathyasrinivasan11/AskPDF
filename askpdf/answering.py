"""Citation-first answer synthesis using Gemini, with a conservative fallback."""

from __future__ import annotations

import os
from typing import Iterable

from .models import Answer, SearchResult


def citation_label(result: SearchResult) -> str:
    metadata = result.metadata
    return (
        f"{metadata.get('filename', 'document')} — "
        f"page {metadata.get('page', '?')}, section "
        f"{metadata.get('section', 'Document')}"
    )


def pdf_link(result: SearchResult) -> str:
    path = result.metadata.get("source_path", "")
    page = int(result.metadata.get("page", 1))
    # file:// is useful for a local Streamlit process; the download button is
    # rendered alongside it because browsers may restrict file URI navigation.
    from pathlib import Path

    return f"{Path(path).resolve().as_uri()}#page={page}"


def _context(results: Iterable[SearchResult]) -> str:
    return "\n\n".join(
        f"[{index}] {citation_label(item)}\n{item.text}"
        for index, item in enumerate(results, start=1)
    )


def _gemini(model: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY is not configured.")
    return ChatGoogleGenerativeAI(model=model, temperature=0)


def synthesize_answer(
    question: str,
    results: list[SearchResult],
    model: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> Answer:
    if not results:
        return Answer(
            text="I couldn't find that in the uploaded PDFs.",
            not_found=True,
        )
    history = "\n".join(
        f"{item.get('role', 'user').title()}: {item.get('content', '')}"
        for item in (conversation_history or [])[-6:]
    )
    prompt = f"""Answer the question using only the PDF excerpts below.
If the excerpts do not support an answer, say exactly: NOT_FOUND.
Do not use outside knowledge. Be concise and cite every factual claim with
the bracket number of its supporting excerpt, such as [1] or [2].

Conversation history (use only to understand follow-up questions):
{history or "(none)"}

Question: {question}

PDF excerpts:
{_context(results)}
"""
    response = _gemini(model).invoke(prompt)
    text = response.content if isinstance(response.content, str) else str(response.content)
    if text.strip().upper().startswith("NOT_FOUND"):
        return Answer(
            text="I couldn't find that in the uploaded PDFs.",
            citations=results,
            not_found=True,
        )
    return Answer(text=text, citations=results)


def general_knowledge_answer(
    question: str, model: str, conversation_history: list[dict[str, str]] | None = None
) -> Answer:
    history = "\n".join(
        f"{item.get('role', 'user').title()}: {item.get('content', '')}"
        for item in (conversation_history or [])[-6:]
    )
    response = _gemini(model).invoke(
        "Answer this question from general knowledge. State that this is not "
        "from the uploaded PDFs, and be concise.\n\n"
        f"Conversation history:\n{history or '(none)'}\n\nQuestion: {question}"
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    return Answer(text=text, used_general_knowledge=True)
