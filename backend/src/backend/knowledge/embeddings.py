from __future__ import annotations

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.knowledge.config import KnowledgeSettings

KNOWLEDGE_EMBEDDING_DIMENSION = 768


def create_knowledge_embeddings(settings: KnowledgeSettings) -> GoogleGenerativeAIEmbeddings:
    """Build the shared LangChain embedding provider for the knowledge index."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
        output_dimensionality=KNOWLEDGE_EMBEDDING_DIMENSION,
    )
