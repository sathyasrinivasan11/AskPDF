"""Application orchestration, keeping Streamlit event handling thin."""

from __future__ import annotations

from pathlib import Path
import logging

from .answering import general_knowledge_answer, synthesize_answer
from .chunking import chunk_pages
from .config import Settings
from .ingestion import extract_pdf, save_uploaded_pdf
from .models import Answer
from .retrieval import HybridIndex
from .scope import QueryKind, classify_query

logger = logging.getLogger(__name__)


class AskPDF:
    def __init__(self, settings: Settings):
        self.settings = settings
        settings.ensure_directories()
        self._embeddings = None
        self.index: HybridIndex | None = None

    def _get_index(self) -> HybridIndex:
        if self.index is None:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                self._embeddings = GoogleGenerativeAIEmbeddings(
                    model=self.settings.embedding_model
                )
            except Exception as exc:
                # PDF ingestion can still provide reliable exact-term search
                # through SQLite FTS5 when Gemini is not configured or reachable.
                logger.warning(
                    "Gemini embeddings unavailable; using lexical retrieval: %s", exc
                )
            self.index = HybridIndex(
                self.settings.sqlite_path, self.settings.chroma_dir, self._embeddings
            )
        elif self._embeddings is None:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                self._embeddings = GoogleGenerativeAIEmbeddings(
                    model=self.settings.embedding_model
                )
                self.index._embeddings = self._embeddings
                self.index._semantic_search_enabled = True
            except Exception:
                pass
        return self.index

    def ingest_upload(self, uploaded) -> int:
        doc_id, path = save_uploaded_pdf(uploaded, self.settings.documents_dir)
        pages = extract_pdf(path, doc_id)
        docs = chunk_pages(pages, self.settings.chunk_size, self.settings.chunk_overlap)
        return self._get_index().add_documents(docs)

    @property
    def semantic_search_available(self) -> bool:
        return self.index is not None and self.index.semantic_search_available

    @property
    def semantic_search_error(self) -> str:
        return self.index.semantic_search_error if self.index else ""

    def backfill_embeddings(self) -> int:
        """Backfill missing vectors without changing SQLite chunks."""
        index = self._get_index()
        try:
            return index.backfill_embeddings()
        except Exception as exc:
            index._semantic_search_enabled = False
            index._semantic_search_error = str(exc)
            raise

    def ingest_paths(self, paths: list[Path]) -> int:
        total = 0
        for path in paths:
            class LocalUpload:
                name = path.name

                def getvalue(self):
                    return path.read_bytes()

            total += self.ingest_upload(LocalUpload())
        return total

    def ask(
        self,
        question: str,
        allow_general_knowledge: bool = False,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> Answer:
        decision = classify_query(question)
        if decision.kind is QueryKind.AMBIGUOUS:
            return Answer(
                text=decision.clarification,
                needs_clarification=True,
                clarification_question=decision.clarification,
            )
        index = self._get_index()
        if not index.has_documents():
            return Answer(
                text="No PDFs are indexed yet. Upload at least one PDF first.",
                not_found=True,
            )
        results = index.search(question, self.settings.top_k)
        answer = synthesize_answer(
            question, results, self.settings.chat_model, conversation_history
        )
        if answer.not_found and allow_general_knowledge:
            return general_knowledge_answer(
                question, self.settings.chat_model, conversation_history
            )
        return answer
