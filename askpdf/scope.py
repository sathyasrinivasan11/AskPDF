"""Strict scope and query-intent decisions, kept deterministic and testable."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class QueryKind(str, Enum):
    ANSWERABLE = "answerable"
    AMBIGUOUS = "ambiguous"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class QueryDecision:
    kind: QueryKind
    clarification: str = ""


_AMBIGUOUS = (
    r"\b(it|this|that|they|them|these|those|the above|the document)\b",
    r"\bwhat about\b",
)
_GREETINGS = re.compile(r"^\s*(hi|hello|hey|thanks|thank you)[!. ]*$", re.I)


def classify_query(question: str) -> QueryDecision:
    """Classify obvious ambiguity before retrieval; never silently guess."""
    clean = " ".join(question.split())
    if not clean or _GREETINGS.fullmatch(clean):
        return QueryDecision(
            QueryKind.AMBIGUOUS,
            "What would you like to know about the uploaded PDFs?",
        )
    if len(clean.split()) < 2:
        return QueryDecision(
            QueryKind.AMBIGUOUS,
            "Could you ask a complete question and name the topic or document?",
        )
    if any(re.search(pattern, clean, re.I) for pattern in _AMBIGUOUS):
        return QueryDecision(
            QueryKind.AMBIGUOUS,
            "Which document, topic, or section does your question refer to?",
        )
    return QueryDecision(QueryKind.ANSWERABLE)


def should_use_general_knowledge(answer_found: bool, consent: bool) -> bool:
    """General knowledge is available only after an explicit yes/no consent."""
    return not answer_found and consent
