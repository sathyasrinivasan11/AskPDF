"""Small data structures shared by ingestion, retrieval, and the UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageContent:
    document_id: str
    filename: str
    source_path: str
    page: int
    markdown: str
    section: str = "Document"
    images: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    text: str
    metadata: dict[str, Any]
    score: float
    lexical_score: float = 0.0
    vector_score: float = 0.0


@dataclass
class Answer:
    text: str
    citations: list[SearchResult] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str = ""
    not_found: bool = False
    used_general_knowledge: bool = False
    conversation_id: str = ""
