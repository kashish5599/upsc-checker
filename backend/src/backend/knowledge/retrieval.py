from __future__ import annotations

import asyncio
from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.knowledge.config import KnowledgeSettings
from backend.knowledge.pinecone_store import PineconeKnowledgeStore

MIN_SIMILARITY_SCORE = 0.69


class KnowledgeRetrievalError(RuntimeError):
    """Raised when question embedding or Pinecone retrieval cannot complete."""


class KnowledgeRetrievalService:
    """Retrieve question-specific context through dense vector similarity."""

    def __init__(self, *, settings: KnowledgeSettings) -> None:
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
            output_dimensionality=768,
        )
        self._vectors = PineconeKnowledgeStore(
            api_key=settings.pinecone_api_key,
            index_name=settings.pinecone_index_name,
            host=settings.pinecone_host,
        )

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        """Return Pinecone's top dense matches with their stored metadata."""
        if top_k < 1:
            raise ValueError("top_k must be a positive integer.")
        query = query.strip()
        if not query:
            return []

        try:
            dense_vector = await self._embeddings.aembed_query(
                query,
                task_type="RETRIEVAL_QUERY",
            )
        except Exception as error:
            raise KnowledgeRetrievalError("The question could not be embedded.") from error

        try:
            matches = await asyncio.to_thread(
                self._vectors.similarity_search,
                dense_vector,
                top_k,
            )
        except Exception as error:
            raise KnowledgeRetrievalError("The knowledge index could not be searched.") from error

        print(f"Retrieved matches - {matches}")
        contexts = [
            context
            for match in matches
            if (context := _context(match))
            and context["score"] >= MIN_SIMILARITY_SCORE
        ]

        print(f"Filtered contexts - {contexts}")
        return contexts[:top_k]


def _context(match: Any) -> dict[str, Any] | None:
    metadata = _match_value(match, "metadata") or {}
    if not isinstance(metadata, dict):
        metadata = dict(metadata)

    document_id = metadata.get("document_id")
    text = metadata.get("text")
    if not document_id or not isinstance(text, str) or not text.strip():
        return None

    raw_score = _match_value(match, "score")
    try:
        score = float(raw_score) if raw_score is not None else 0.0
    except (TypeError, ValueError):
        score = 0.0

    return {
        **metadata,
        "document_id": str(document_id),
        "text": text,
        "score": score,
    }


def _match_value(match: Any, key: str) -> Any:
    if isinstance(match, dict):
        return match.get(key)
    return getattr(match, key, None)
