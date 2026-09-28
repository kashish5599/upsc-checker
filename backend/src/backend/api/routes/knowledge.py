from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.knowledge.config import (
    KnowledgeConfigurationError,
    KnowledgeSettings,
    metadata_db_path_from_environment,
)
from backend.knowledge.ingestion import (
    KnowledgeDocumentError,
    KnowledgeIngestionError,
    KnowledgeIngestionService,
)
from backend.knowledge.repository import (
    DuplicateDocumentError,
    KnowledgeDocument,
    KnowledgeDocumentRepository,
)

router = APIRouter(tags=["knowledge"])


@lru_cache(maxsize=1)
def _repository() -> KnowledgeDocumentRepository:
    return KnowledgeDocumentRepository(metadata_db_path_from_environment())


@lru_cache(maxsize=1)
def _ingestion_service() -> KnowledgeIngestionService:
    return KnowledgeIngestionService(
        settings=KnowledgeSettings.from_environment(),
        repository=_repository(),
    )


def _document_response(document: KnowledgeDocument) -> dict[str, str | int]:
    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "title": document.title,
        "file_hash": document.file_hash,
        "page_count": document.page_count,
        "created_at": document.created_at,
    }


@router.post("/documents", status_code=201)
async def upload_knowledge_document(
    file: Annotated[UploadFile, File(...)],
) -> dict[str, str | int]:
    pdf_bytes = await file.read()
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a PDF.")

    try:
        document = await _ingestion_service().ingest(
            pdf_bytes=pdf_bytes,
            filename=file.filename,
        )
    except DuplicateDocumentError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(error),
                "document_id": error.document_id,
            },
        ) from error
    except KnowledgeConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except KnowledgeDocumentError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except KnowledgeIngestionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return _document_response(document)


@router.get("/documents")
def list_knowledge_documents() -> dict[str, list[dict[str, str | int]]]:
    return {"documents": [_document_response(document) for document in _repository().list_ingested()]}


@router.delete("/documents/{document_id}")
async def delete_knowledge_document(document_id: str) -> dict[str, str]:
    try:
        deleted = await _ingestion_service().delete(document_id)
    except KnowledgeConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="Could not delete vectors from Pinecone.") from error

    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    return {"document_id": document_id, "status": "deleted"}
