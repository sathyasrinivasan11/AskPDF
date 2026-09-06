"""Section-aware chunking with page metadata preserved."""

from __future__ import annotations

import re
from typing import Iterable

from langchain_core.documents import Document

from .models import PageContent

HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")


def sectionize(markdown: str, default: str = "Document") -> list[tuple[str, str]]:
    """Return ``(section, text)`` blocks, retaining heading names."""
    blocks: list[tuple[str, str]] = []
    current = default
    lines: list[str] = []
    for line in markdown.splitlines():
        match = HEADING.match(line)
        if match:
            if "\n".join(lines).strip():
                blocks.append((current, "\n".join(lines).strip()))
            current = match.group(2).strip()
            lines = []
        else:
            lines.append(line)
    if "\n".join(lines).strip():
        blocks.append((current, "\n".join(lines).strip()))
    return blocks or [(default, markdown.strip())]


def chunk_pages(
    pages: Iterable[PageContent], chunk_size: int = 1200, chunk_overlap: int = 180
) -> list[Document]:
    """Split page sections while never dropping page/document provenance."""
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller")
    # Imported lazily enough that pure helpers remain easy to use in small scripts.
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    result: list[Document] = []
    for page in pages:
        for section, text in sectionize(page.markdown, page.section):
            for piece_index, piece in enumerate(splitter.split_text(text)):
                if not piece.strip():
                    continue
                result.append(
                    Document(
                        page_content=piece,
                        metadata={
                            "document_id": page.document_id,
                            "filename": page.filename,
                            "source_path": page.source_path,
                            "page": page.page,
                            "section": section or "Document",
                            "chunk": piece_index,
                            "images": page.images,
                        },
                    )
                )
    return result
