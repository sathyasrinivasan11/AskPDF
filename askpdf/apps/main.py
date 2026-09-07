"""AskPDF FastAPI application entrypoint."""

from fastapi import FastAPI

from askpdf.api.chat import router as chat_router
from askpdf.api.documents import router as documents_router
from askpdf.api.embeddings import router as embeddings_router
from askpdf.api.health import router as health_router
from askpdf.api.ingestion import router as ingestion_router

app = FastAPI(title="AskPDF API", version="1.0.0")
app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(embeddings_router)
