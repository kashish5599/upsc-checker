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
        """Search curated UPSC sources to verify stable domain knowledge, especially constitutional provisions and powers,
        legal doctrines, named judgments/case holdings, and foundational facts. Call this when a concrete legal or
        factual claim in the question or answer could materially affect scoring; do not accept a plausible-sounding
        case-law or constitutional claim without checking when retrieval can help. Do not use it for facts that are
        exclusively current. If results are empty, irrelevant, or insufficient, consider retrieve_current_context only
        if current web evidence could help. Call at most once per evaluation."""

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
        """Search for current UPSC-relevant policies, recent judgments, government developments, geopolitical events,
        current data, and contemporary examples. Use when a time-sensitive claim could materially affect scoring, or
        when static retrieval did not provide useful evidence and a current web source could verify the point. Prefer
        primary government, court, regulator, and international-organization sources. Do not use it for stable
        textbook concepts or merely to add citations. Call at most once per evaluation."""

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
