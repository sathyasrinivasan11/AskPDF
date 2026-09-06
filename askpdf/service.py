"""Application orchestration, keeping Streamlit event handling thin."""

from __future__ import annotations

from pathlib import Path

from .answering import general_knowledge_answer, synthesize_answer
from .chunking import chunk_pages
from .config import Settings
from .ingestion import extract_pdf, save_uploaded_pdf
from .models import Answer
from .retrieval import HybridIndex
from .scope import QueryKind, classify_query


class AskPDF:
    def __init__(self, settings: Settings):
        self.settings = settings
        settings.ensure_directories()
        self._embeddings = None
        self.index: HybridIndex | None = None

    def _get_index(self) -> HybridIndex:
        if self.index is None:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=self.settings.embedding_model
            )
            self.index = HybridIndex(
                self.settings.sqlite_path, self.settings.chroma_dir, self._embeddings
            )
        return self.index

    def ingest_upload(self, uploaded) -> int:
        doc_id, path = save_uploaded_pdf(uploaded, self.settings.documents_dir)
        pages = extract_pdf(path, doc_id)
        docs = chunk_pages(pages, self.settings.chunk_size, self.settings.chunk_overlap)
        return self._get_index().add_documents(docs)

    def ingest_paths(self, paths: list[Path]) -> int:
        total = 0
        for path in paths:
            class LocalUpload:
                name = path.name

                def getvalue(self):
                    return path.read_bytes()

            total += self.ingest_upload(LocalUpload())
        return total

    def ask(self, question: str, allow_general_knowledge: bool = False) -> Answer:
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
        answer = synthesize_answer(question, results, self.settings.chat_model)
        if answer.not_found and allow_general_knowledge:
            return general_knowledge_answer(question, self.settings.chat_model)
        return answer
