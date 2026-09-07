"""Semantic embedding maintenance routes."""

from fastapi import APIRouter, HTTPException

from askpdf.api.dependencies import askpdf_service

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/embeddings")
def backfill_embeddings() -> dict:
    try:
        created = askpdf_service.backfill_embeddings()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Semantic embeddings could not be created. Check GOOGLE_API_KEY "
                "and network access to generativelanguage.googleapis.com."
            ),
        ) from exc
    return {
        "created_embeddings": created,
        "semantic_search_available": askpdf_service.semantic_search_available,
        "message": (
            "Existing chunks were preserved. Only missing embeddings were created."
        ),
    }
