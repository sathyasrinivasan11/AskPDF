"""Stored document routes."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from askpdf.api.dependencies import askpdf_service
from askpdf.services.document_service import get_document_file

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}/file")
def document_file(document_id: str) -> FileResponse:
    return get_document_file(askpdf_service.settings.documents_dir, document_id)
