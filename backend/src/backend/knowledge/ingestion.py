from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langfuse import observe

from backend.knowledge.document_processing import (
    KnowledgeChunk,
    UnstructuredPdfProcessor,
)
from backend.knowledge.repository import (
    DuplicateDocumentError,
    KnowledgeDocument,
    KnowledgeDocumentRepository,
)
from backend.knowledge.config import KnowledgeSettings
from backend.knowledge.pinecone_store import PineconeKnowledgeStore
from dotenv import load_dotenv

load_dotenv()

class KnowledgeDocumentError(ValueError):
    """Raised for unusable knowledge documents or ingestion failures."""


class KnowledgeIngestionError(RuntimeError):
    """Raised when embeddings or vector indexing cannot complete."""

class KnowledgeIngestionService:
    def __init__(
        self,
        *,
        settings: KnowledgeSettings,
        repository: KnowledgeDocumentRepository,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._pdf_processor = UnstructuredPdfProcessor()
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
            output_dimensionality=768
        )
        self._vectors = PineconeKnowledgeStore(
            api_key=settings.pinecone_api_key,
            index_name=settings.pinecone_index_name,
            host=settings.pinecone_host,
        )

    async def ingest(
        self,
        *,
        pdf_bytes: bytes,
        filename: str,
    ) -> KnowledgeDocument:
        if not pdf_bytes.startswith(b"%PDF-"):
            raise KnowledgeDocumentError("The uploaded file is not a PDF.")

        filename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not filename:
            filename = "curated_document.pdf"
        title = Path(filename).stem.strip() or filename
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        duplicate = self._repository.get_by_hash(file_hash)
        if duplicate:
            raise DuplicateDocumentError(duplicate.document_id)

        try:
            processed_pdf = await asyncio.to_thread(self._pdf_processor.process, pdf_bytes)
        except ValueError as error:
            raise KnowledgeDocumentError(str(error)) from error
        except Exception as error:
            raise KnowledgeDocumentError("The PDF could not be partitioned.") from error

        chunks = processed_pdf.chunks
        if not chunks:
            raise KnowledgeDocumentError("The PDF contains no extractable text.")

        # debug_path = self._write_chunk_debug_file(filename, chunks)
        # print(f"Chunk debug file written to: {debug_path}")

        document_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        self._repository.create_processing(
            document_id=document_id,
            file_hash=file_hash,
            filename=filename,
            title=title,
            page_count=processed_pdf.page_count,
            created_at=created_at,
        )

        vectors_may_exist = False
        try:
            print("Starting embedding")
            embeddings = await self._embed_documents(
                texts=[chunk.text for chunk in chunks],
                title=title,
            )
            if len(embeddings) != len(chunks):
                raise KnowledgeDocumentError("The embedding service returned an incomplete result.")
            print("Embedding completed")
            vectors = [
                {
                    "id": f"{document_id}#{index:06d}",
                    "values": embedding,
                    "metadata": self._vector_metadata(
                        document_id=document_id,
                        filename=filename,
                        file_hash=file_hash,
                        title=title,
                        page_count=processed_pdf.page_count,
                        created_at=created_at,
                        chunk=chunk,
                    ),
                }
                for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            ]
            vectors_may_exist = True

            print("Pushing to pinecone")
            await asyncio.to_thread(self._vectors.upsert, vectors)
            self._repository.mark_ingested(document_id)
            print("Added to pinecone")
        except Exception as error:
            print(error)
            if vectors_may_exist:
                try:
                    await asyncio.to_thread(self._vectors.delete_document, document_id)
                except Exception as cleanup_error:
                    raise KnowledgeIngestionError(
                        "Ingestion failed and Pinecone cleanup also failed; the document remains reserved."
                    ) from cleanup_error
            self._repository.delete(document_id)
            if isinstance(error, KnowledgeDocumentError):
                raise
            raise KnowledgeIngestionError("The document could not be embedded and indexed.") from error

        document = self._repository.get(document_id)
        if document is None:
            raise KnowledgeDocumentError("The ingested document metadata could not be loaded.")
        return document

    @observe(
        name="knowledge-document-embeddings",
        as_type="embedding",
    )
    async def _embed_documents(self, *, texts: list[str], title: str) -> list[list[float]]:
        return await self._embeddings.aembed_documents(
            texts,
            task_type="RETRIEVAL_DOCUMENT",
            titles=[title] * len(texts),
            batch_size=100,
        )

    # @staticmethod
    # def _write_chunk_debug_file(filename: str, chunks: list[KnowledgeChunk]) -> Path:
    #     debug_dir = Path.cwd() / ".chunk_debug"
    #     debug_dir.mkdir(parents=True, exist_ok=True)

    #     safe_name = Path(filename).stem.strip() or "document"
    #     debug_path = debug_dir / f"{safe_name}_chunks.txt"

    #     with debug_path.open("w", encoding="utf-8") as handle:
    #         for index, chunk in enumerate(chunks, start=1):
    #             handle.write(f"--- Chunk {index} ---\n")
    #             if chunk.title:
    #                 handle.write(f"Title: {chunk.title}\n")
    #             if chunk.chapter:
    #                 handle.write(f"Chapter: {chunk.chapter}\n")
    #             if chunk.section:
    #                 handle.write(f"Section: {chunk.section}\n")
    #             if chunk.page_start is not None or chunk.page_end is not None:
    #                 start = chunk.page_start if chunk.page_start is not None else "?"
    #                 end = chunk.page_end if chunk.page_end is not None else "?"
    #                 handle.write(f"Pages: {start} - {end}\n")
    #             handle.write("\n")
    #             handle.write(chunk.text.strip())
    #             handle.write("\n\n")

    #     return debug_path

    async def delete(self, document_id: str) -> bool:
        if not self._repository.is_ingested(document_id):
            return False
        await asyncio.to_thread(self._vectors.delete_document, document_id)
        self._repository.delete(document_id)
        return True

    @staticmethod
    def _vector_metadata(
        *,
        document_id: str,
        filename: str,
        file_hash: str,
        title: str,
        page_count: int,
        created_at: str,
        chunk: KnowledgeChunk,
    ) -> dict[str, str | int]:
        metadata: dict[str, str | int] = {
            "document_id": document_id,
            "filename": filename,
            "title": title,
            "file_hash": file_hash,
            "page_count": page_count,
            "created_at": created_at,
            "text": chunk.text,
        }
        if chunk.page_start is not None:
            metadata["page_start"] = chunk.page_start
        if chunk.page_end is not None:
            metadata["page_end"] = chunk.page_end
        if chunk.chapter:
            metadata["chapter"] = chunk.chapter
        if chunk.section:
            metadata["section"] = chunk.section
        if chunk.title:
            metadata["chunk_title"] = chunk.title
        return metadata
