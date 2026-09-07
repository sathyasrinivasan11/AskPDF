"""PDF storage and PyMuPDF4LLM extraction."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import BinaryIO, Iterable

from .models import PageContent


def safe_filename(filename: str) -> str:
    """Normalize a user filename without allowing path traversal."""
    name = Path(filename or "document.pdf").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name or "document.pdf"


def document_id(filename: str, data: bytes) -> str:
    return hashlib.sha256(filename.encode() + b"\0" + data).hexdigest()[:24]


def save_uploaded_pdf(uploaded: BinaryIO, documents_dir: Path) -> tuple[str, Path]:
    data = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
    if not data or not data.startswith(b"%PDF"):
        raise ValueError("Only valid PDF files can be uploaded.")
    filename = safe_filename(getattr(uploaded, "name", "document.pdf"))
    doc_id = document_id(filename, data)
    documents_dir.mkdir(parents=True, exist_ok=True)
    path = documents_dir / f"{doc_id}_{filename}"
    if not path.exists():
        path.write_bytes(data)
    return doc_id, path


def _page_texts(pdf_path: Path) -> list[str]:
    import pymupdf4llm

    # page_chunks emits one markdown string per PDF page and keeps tables as
    # markdown where PyMuPDF4LLM can detect them.
    image_dir = pdf_path.parent / f"{pdf_path.stem}_images"
    try:
        pages = pymupdf4llm.to_markdown(
            str(pdf_path),
            page_chunks=True,
            write_images=True,
            image_path=str(image_dir),
        )
    except (TypeError, RuntimeError):
        # Older PyMuPDF4LLM releases may not support image_path for page
        # chunks. Text and tables are still valuable, so retry conservatively.
        pages = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    if isinstance(pages, str):
        return pages.split("\f")
    return [
        (item.get("text") if isinstance(item, dict) else str(item)) or ""
        for item in pages
    ]


def extract_pdf(pdf_path: Path, doc_id: str | None = None) -> list[PageContent]:
    """Extract page markdown and image counts; page numbers are one-based."""
    import fitz

    pdf_path = Path(pdf_path)
    raw = pdf_path.read_bytes()
    doc_id = doc_id or document_id(pdf_path.name, raw)
    texts = _page_texts(pdf_path)
    with fitz.open(pdf_path) as pdf:
        pages: list[PageContent] = []
        for number, text in enumerate(texts, start=1):
            image_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
            images = [str(item[0]) for item in pdf[number - 1].get_images(full=True)]
            images.extend(image_refs)
            pages.append(
                PageContent(
                    document_id=doc_id,
                    filename=pdf_path.name,
                    source_path=str(pdf_path.resolve()),
                    page=number,
                    markdown=text.strip(),
                    images=images,
                )
            )
        # Some versions can omit empty trailing pages from page_chunks.
        for number in range(len(pages) + 1, len(pdf) + 1):
            pages.append(
                PageContent(
                    document_id=doc_id,
                    filename=pdf_path.name,
                    source_path=str(pdf_path.resolve()),
                    page=number,
                    markdown="",
                )
            )
    return pages


def ingest_files(paths: Iterable[Path], data_dir: Path) -> list[PageContent]:
    """Copy PDFs into persistent storage and extract them."""
    documents_dir = data_dir / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    all_pages: list[PageContent] = []
    for source in paths:
        source = Path(source)
        data = source.read_bytes()
        doc_id = document_id(source.name, data)
        target = documents_dir / f"{doc_id}_{safe_filename(source.name)}"
        if not target.exists():
            shutil.copyfile(source, target)
        all_pages.extend(extract_pdf(target, doc_id))
    return all_pages
