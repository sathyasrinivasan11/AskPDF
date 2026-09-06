"""Business logic for the PDF ingestion endpoint."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile

from askpdf.service import AskPDF


async def ingest_uploads(service: AskPDF, uploads: list[UploadFile]) -> dict:
    if not uploads or len(uploads) > 10:
        raise HTTPException(status_code=400, detail="Upload between 1 and 10 PDF files.")

    indexed: list[dict] = []
    for upload in uploads:
        filename = upload.filename or "document.pdf"
        if upload.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{filename} is not a PDF.")
        data = await upload.read()

        class BackendUpload:
            name = filename

            def getvalue(self):
                return data

        try:
            chunks = service.ingest_upload(BackendUpload())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        indexed.append({"filename": filename, "chunks": chunks})
    return {"indexed": indexed, "total_chunks": sum(item["chunks"] for item in indexed)}
