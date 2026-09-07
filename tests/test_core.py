from askpdf.answering import citation_label, pdf_link
from askpdf.chunking import sectionize
from askpdf.models import SearchResult
from askpdf.retrieval import reciprocal_rank_fusion
from askpdf.scope import QueryKind, classify_query, should_use_general_knowledge
from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_core.documents import Document
from askpdf.retrieval import HybridIndex


def result(chunk_id: str, score: float = 1) -> SearchResult:
    return SearchResult(
        text=chunk_id,
        metadata={
            "chunk_id": chunk_id,
            "filename": "guide.pdf",
            "source_path": "/work/data/guide.pdf",
            "page": 3,
            "section": "Overview",
        },
        score=score,
    )


def test_sectionize_retains_headings():
    blocks = sectionize("# Intro\nhello\n## Details\nworld")
    assert blocks == [("Intro", "hello"), ("Details", "world")]


def test_rrf_prefers_items_in_both_rankings():
    fused = reciprocal_rank_fusion([result("a"), result("b")], [result("b"), result("c")])
    assert fused[0].metadata["chunk_id"] == "b"


def test_scope_is_conservative():
    assert classify_query("What about it?").kind is QueryKind.AMBIGUOUS
    assert classify_query("What is the retention policy?").kind is QueryKind.ANSWERABLE
    assert should_use_general_knowledge(False, False) is False
    assert should_use_general_knowledge(False, True) is True


def test_citation_has_exact_page_and_section():
    item = result("x")
    assert "page 3" in citation_label(item)
    assert pdf_link(item).endswith("guide.pdf#page=3")


def test_embedding_backfill_uses_existing_chunk_ids_without_duplicates():
    class FakeStore:
        def __init__(self):
            self.ids = set()

        def get(self, ids, include):
            return {"ids": [item for item in ids if item in self.ids]}

        def delete(self, **kwargs):
            self.ids.clear()

        def add_documents(self, documents, ids):
            assert len(ids) == len(set(ids))
            self.ids.update(ids)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        index = HybridIndex(root / "docs.sqlite3", root / "chroma", embeddings=object())
        index._vectorstore = FakeStore()
        documents = [
            Document(
                page_content="existing chunk",
                metadata={
                    "document_id": "doc",
                    "filename": "guide.pdf",
                    "source_path": str(root / "guide.pdf"),
                    "page": 1,
                    "section": "Overview",
                    "chunk": 0,
                },
            )
        ]
        index.add_documents(documents)
        index._vectorstore.ids.clear()
        index._semantic_search_enabled = False
        created = index.backfill_embeddings()
        assert created == 1
        assert index.backfill_embeddings() == 0
