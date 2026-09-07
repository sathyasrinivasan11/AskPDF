"""PDF ingestion routes."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from askpdf.api.dependencies import askpdf_service
from askpdf.services.ingestion_service import ingest_uploads

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/file")
async def ingest_file(
    files: Annotated[list[UploadFile], File(description="One to ten PDF files")],
) -> dict:
    return await ingest_uploads(askpdf_service, files)
