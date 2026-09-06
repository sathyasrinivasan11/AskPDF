"""Business logic for serving stored PDFs."""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse


def get_document_file(documents_dir: Path, document_id: str) -> FileResponse:
    matches = list(documents_dir.glob(f"{document_id}_*.pdf"))
    if not matches:
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(matches[0], media_type="application/pdf")
