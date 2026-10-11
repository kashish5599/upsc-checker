from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from backend.knowledge.config import KnowledgeSettings
from backend.knowledge.embeddings import create_knowledge_embeddings
from backend.knowledge.pinecone_store import PineconeVectorStore

logger = logging.getLogger(__name__)

SIMILAR_TOPPER_QUESTIONS_K = 3
MIN_TOPPER_QUESTION_SCORE = 0.9
TOPPER_QUESTIONS_NAMESPACE = "topper-questions"


class SimilarTopperQuestionsService:
    """Find semantically similar questions from the curated topper-question corpus."""

    def __init__(self, *, settings: KnowledgeSettings) -> None:
        self._embeddings = create_knowledge_embeddings(settings)
        self._vectors = PineconeVectorStore(
            api_key=settings.pinecone_api_key,
            index_name=settings.pinecone_index_name,
            host=settings.pinecone_host,
            namespace=os.getenv(
                "TOPPER_QUESTIONS_NAMESPACE",
                TOPPER_QUESTIONS_NAMESPACE,
            ),
        )

    async def retrieve_similar_questions(
        self,
        query: str | None,
        top_k: int = SIMILAR_TOPPER_QUESTIONS_K,
    ) -> list[dict[str, Any]] | None:
        """Return relevant CSV-shaped matches, or None when retrieval fails."""
        if top_k < 1:
            raise ValueError("top_k must be a positive integer.")
        if not query or not query.strip():
            return []

        try:
            dense_vector = await self._embeddings.aembed_query(
                query.strip(),
                task_type="RETRIEVAL_QUERY",
            )
            matches = await asyncio.to_thread(
                self._vectors.similarity_search,
                dense_vector,
                top_k,
            )
        except Exception:
            logger.exception("Similar topper-question retrieval failed.")
            return None

        results: list[dict[str, Any]] = []
        print(f"All of the Retrieved matches before filtering - {matches}")
        for match in matches:
            metadata = _match_value(match, "metadata") or {}
            if not isinstance(metadata, dict):
                metadata = dict(metadata)
            question_text = metadata.get("question_text")
            raw_score = _match_value(match, "score")
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                continue
            if score < MIN_TOPPER_QUESTION_SCORE:
                continue
            if not isinstance(question_text, str) or not question_text.strip():
                continue

            result = {
                "topper": metadata.get("topper"),
                "coaching": metadata.get("coaching"),
                "subject": metadata.get("subject"),
                "page_number": metadata.get("page_number"),
                "question_text": question_text,
                "metadata": metadata.get("metadata"),
                "question_url": metadata.get("question_url"),
                "score": score,
            }
            results.append(result)

        return results[:top_k]


def _match_value(match: Any, key: str) -> Any:
    if isinstance(match, dict):
        return match.get(key)
    return getattr(match, key, None)
