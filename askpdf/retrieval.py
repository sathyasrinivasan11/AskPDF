"""Persistent SQLite FTS5 + Chroma hybrid retrieval."""

from __future__ import annotations

import re
import sqlite3
from hashlib import sha1
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

from .models import SearchResult


def _terms(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]{2,}", text.lower())


def reciprocal_rank_fusion(
    lexical: list[SearchResult],
    vector: list[SearchResult],
    limit: int = 6,
    k: int = 60,
) -> list[SearchResult]:
    """Fuse ranked lists without making incomparable scores look equivalent."""
    by_key: dict[str, SearchResult] = {}
    fused: defaultdict[str, float] = defaultdict(float)
    for rank, item in enumerate(lexical):
        key = str(item.metadata.get("chunk_id", item.metadata))
        by_key[key] = item
        fused[key] += 1 / (k + rank + 1)
        item.lexical_score = 1 / (rank + 1)
    for rank, item in enumerate(vector):
        key = str(item.metadata.get("chunk_id", item.metadata))
        by_key[key] = item
        fused[key] += 1 / (k + rank + 1)
        item.vector_score = 1 / (rank + 1)
    return [
        SearchResult(
            text=by_key[key].text,
            metadata=by_key[key].metadata,
            score=score,
            lexical_score=by_key[key].lexical_score,
            vector_score=by_key[key].vector_score,
        )
        for key, score in sorted(fused.items(), key=lambda pair: pair[1], reverse=True)[
            :limit
        ]
    ]


class HybridIndex:
    """SQLite is the source of truth; Chroma is the persistent semantic index."""

    def __init__(self, sqlite_path: Path, chroma_dir: Path, embeddings=None):
        self.sqlite_path = Path(sqlite_path)
        self.chroma_dir = Path(chroma_dir)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._embeddings = embeddings
        self._vectorstore = None
        self._setup_sqlite()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _setup_sqlite(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY, text TEXT NOT NULL, document_id TEXT,
                filename TEXT, source_path TEXT, page INTEGER, section TEXT)"""
            )
            db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5("
                "chunk_id UNINDEXED, text, filename, section)"
            )

    def _store(self):
        if self._vectorstore is None:
            if self._embeddings is None:
                raise RuntimeError("An embeddings object is required for semantic search.")
            from langchain_chroma import Chroma

            self._vectorstore = Chroma(
                collection_name="askpdf_chunks",
                persist_directory=str(self.chroma_dir),
                embedding_function=self._embeddings,
            )
        return self._vectorstore

    def add_documents(self, documents: Iterable[Document]) -> int:
        docs = list(documents)
        if not docs:
            return 0
        ids: list[str] = []
        document_ids = {
            str(doc.metadata["document_id"])
            for doc in docs
            if doc.metadata.get("document_id")
        }
        # Re-indexing a document must replace its old chunks, including chunks
        # written by older versions of the ID scheme.
        store = self._store()
        with self._connect() as db:
            for document_id in document_ids:
                old_ids = [
                    row[0]
                    for row in db.execute(
                        "SELECT chunk_id FROM chunks WHERE document_id = ?",
                        (document_id,),
                    ).fetchall()
                ]
                db.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                for old_id in old_ids:
                    db.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (old_id,))
        if document_ids:
            store.delete(where={"document_id": {"$in": list(document_ids)}})

        with self._connect() as db:
            for index, doc in enumerate(docs):
                metadata = doc.metadata
                section_key = sha1(
                    str(metadata.get("section", "Document")).encode("utf-8")
                ).hexdigest()[:10]
                chunk_id = (
                    f"{metadata.get('document_id', 'doc')}:"
                    f"{metadata.get('page', 0)}:{section_key}:"
                    f"{metadata.get('chunk', index)}"
                )
                ids.append(chunk_id)
                db.execute(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        chunk_id,
                        doc.page_content,
                        metadata.get("document_id"),
                        metadata.get("filename"),
                        metadata.get("source_path"),
                        int(metadata.get("page", 1)),
                        metadata.get("section", "Document"),
                    ),
                )
                db.execute(
                    "INSERT INTO chunks_fts VALUES (?, ?, ?, ?)",
                    (
                        chunk_id,
                        doc.page_content,
                        metadata.get("filename", ""),
                        metadata.get("section", ""),
                    ),
                )
        # Chroma's current API persists automatically. IDs are unique even
        # when separate sections have the same page-local chunk number.
        store.add_documents(docs, ids=ids)
        return len(docs)

    def lexical_search(self, query: str, limit: int = 12) -> list[SearchResult]:
        terms = _terms(query)
        if not terms:
            return []
        # Quote tokens to avoid FTS syntax surprises from user input.
        match = " AND ".join(f'"{term}"' for term in terms)
        with self._connect() as db:
            rows = db.execute(
                """SELECT c.*, bm25(chunks_fts) AS rank
                   FROM chunks_fts JOIN chunks c USING(chunk_id)
                   WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?""",
                (match, limit),
            ).fetchall()
        return [
            SearchResult(
                text=row["text"],
                metadata={
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "filename": row["filename"],
                    "source_path": row["source_path"],
                    "page": row["page"],
                    "section": row["section"],
                },
                score=float(-row["rank"]),
            )
            for row in rows
        ]

    def vector_search(self, query: str, limit: int = 12) -> list[SearchResult]:
        docs_scores = self._store().similarity_search_with_relevance_scores(query, k=limit)
        return [
            SearchResult(
                text=doc.page_content,
                metadata=doc.metadata,
                score=float(score),
            )
            for doc, score in docs_scores
        ]

    def search(self, query: str, limit: int = 6) -> list[SearchResult]:
        return reciprocal_rank_fusion(
            self.lexical_search(query, limit * 2),
            self.vector_search(query, limit * 2),
            limit=limit,
        )

    def has_documents(self) -> bool:
        with self._connect() as db:
            return db.execute("SELECT 1 FROM chunks LIMIT 1").fetchone() is not None
