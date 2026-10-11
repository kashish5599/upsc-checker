from __future__ import annotations

from typing import Any

from pinecone import Pinecone


class PineconeVectorStore:
    """Small namespace-aware wrapper around the configured Pinecone index."""

    def __init__(
        self,
        api_key: str,
        index_name: str,
        host: str,
        namespace: str = "",
    ) -> None:
        self._client = Pinecone(api_key=api_key)
        self._index = self._client.Index(index_name, host=host)
        self._namespace = namespace

    def upsert(self, vectors: list[dict[str, Any]]) -> None:
        for offset in range(0, len(vectors), 100):
            self._index.upsert(
                vectors=vectors[offset : offset + 100],
                namespace=self._namespace,
            )

    def delete_document(self, document_id: str) -> None:
        self._index.delete(
            filter={"document_id": {"$eq": document_id}},
            namespace=self._namespace,
        )

    def similarity_search(self, vector: list[float], top_k: int) -> list[Any]:
        response = self._index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            namespace=self._namespace,
        )
        return list(response.matches or [])
