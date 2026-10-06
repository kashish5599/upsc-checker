from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool, tool
from langchain_tavily import TavilySearch

from backend.knowledge.retrieval import KnowledgeRetrievalService


def build_evaluation_tools(
    static_retrieval: KnowledgeRetrievalService,
    tavily_search: TavilySearch,
) -> list[BaseTool]:
    @tool("retrieve_static_context")
    async def retrieve_static_context(query: str) -> str:
        """Search the curated UPSC knowledge base for stable concepts, constitutional provisions, theories, and historical or foundational facts relevant to the question. Use this only when the answer benefits from curated static knowledge; do not call it for facts that are only current or when the answer can be assessed without external context. If the results are empty or not useful, consider retrieve_current_context only when current web evidence could materially help. Call at most once per evaluation."""
        try:
            chunks = await static_retrieval.retrieve_context(query, top_k=8)
        except Exception as error:
            return json.dumps({"error": f"Static knowledge retrieval failed: {error}"})

        concise_chunks = [
            {
                "document": chunk.get("title") or chunk.get("filename") or chunk.get("document_id"),
                "document_id": chunk.get("document_id"),
                "pages": _page_label(chunk),
                "chapter": chunk.get("chapter"),
                "section": chunk.get("section"),
                "similarity_score": chunk.get("score"),
                "text": str(chunk.get("text", "")),
            }
            for chunk in chunks
        ]
        return json.dumps({"query": query, "results": concise_chunks}, ensure_ascii=False)

    @tool("retrieve_current_context")
    async def retrieve_current_context(query: str) -> str:
        """Search for recent UPSC-relevant policies, judgments, government developments, geopolitical events, current data, and contemporary examples. Use only when the question or an answer claim needs current or time-sensitive evidence. Prefer primary and authoritative government, court, regulator, and international-organization sources when available. Do not call it for stable textbook concepts; call at most once per evaluation."""
        search_query = (
            f"{query}. Prioritize primary and authoritative sources where available, "
            "including official government, court, regulator, and international organization sources."
        )
        try:
            response = await tavily_search.ainvoke(
                {"query": search_query}
            )
        except Exception as error:
            return json.dumps({"error": f"Current-affairs search failed: {error}"})

        if not isinstance(response, dict):
            return json.dumps({"query": query, "results": []}, ensure_ascii=False)

        sources = [
            {
                "title": result.get("title"),
                "url": result.get("url"),
                "relevance_score": result.get("score"),
                "content": str(result.get("content", ""))[:1_600],
            }
            for result in response.get("results", [])[:5]
            if isinstance(result, dict)
        ]
        return json.dumps({"query": query, "sources": sources}, ensure_ascii=False)

    return [retrieve_static_context, retrieve_current_context]


def _page_label(chunk: dict[str, Any]) -> str | None:
    start = chunk.get("page_start")
    end = chunk.get("page_end")
    if start is None and end is None:
        return None
    if start == end or end is None:
        return f"p. {start}"
    if start is None:
        return f"p. {end}"
    return f"pp. {start}–{end}"
