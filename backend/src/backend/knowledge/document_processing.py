from __future__ import annotations

import math
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from unstructured.chunking.title import chunk_by_title
from unstructured.partition.pdf import partition_pdf


# Unstructured chunk sizes are character based. At roughly four characters per
# token, these settings target about 1,000 tokens with a 125-token split overlap.
_MAX_CHARACTERS = 4_800
_SOFT_MAX_CHARACTERS = 4_000
_OVERLAP_CHARACTERS = 500
_COMBINE_UNDER_CHARACTERS = 3_000

_PUBLISHER_JUNK = re.compile(
    r"^(?:©|copyright\b|all rights reserved\b|isbn\b|printed\s+(?:by|at|in)\b|"
    r"published\s+by\b|publisher\s*:)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class KnowledgeChunk:
    """Chunk text and source metadata produced by Unstructured."""

    text: str
    page_start: int | None
    page_end: int | None
    chapter: str | None = None
    section: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class ProcessedKnowledgePdf:
    page_count: int
    chunks: list[KnowledgeChunk]


class UnstructuredPdfProcessor:
    """Partition, lightly clean, and chunk a curated PDF with Unstructured."""

    def process(self, pdf_bytes: bytes) -> ProcessedKnowledgePdf:
        elements = partition_pdf(file=BytesIO(pdf_bytes), strategy="fast")
        if not elements:
            raise ValueError("The PDF contains no extractable text.")

        page_numbers = [
            page
            for element in elements
            if (page := _page_number(element)) is not None
        ]
        page_count = max(page_numbers, default=0)
        if page_count == 0:
            raise ValueError("The PDF contains no extractable text.")

        chunks = chunk_by_title(
            elements,
            max_characters=_MAX_CHARACTERS,
            new_after_n_chars=_SOFT_MAX_CHARACTERS,
            combine_text_under_n_chars=_COMBINE_UNDER_CHARACTERS,
            overlap=_OVERLAP_CHARACTERS,
            overlap_all=False,
            multipage_sections=True,
        )
        result = [chunk for element in chunks if (chunk := _to_knowledge_chunk(element))]
        if not result:
            raise ValueError("The PDF contains no extractable text.")
        return ProcessedKnowledgePdf(page_count=page_count, chunks=result)

def _to_knowledge_chunk(element: Any) -> KnowledgeChunk | None:
    text = _text(element)
    if not text:
        return None

    metadata = _metadata_dict(element)
    source_elements = getattr(getattr(element, "metadata", None), "orig_elements", None)
    if not isinstance(source_elements, (list, tuple)) or not source_elements:
        source_elements = [element]

    source_metadata = [_metadata_dict(source) for source in source_elements]
    page_numbers = [
        int(page)
        for values in source_metadata
        if (page := values.get("page_number")) is not None
        and str(page).isdigit()
    ]
    if not page_numbers:
        page = metadata.get("page_number")
        if page is not None and str(page).isdigit():
            page_numbers = [int(page)]

    titles = [
        _text(source)
        for source in source_elements
        if str(getattr(source, "category", "")).casefold() == "title" and _text(source)
    ]
    title = _first_value(metadata.get("title"), titles[0] if titles else None)
    chapter = _first_value(
        metadata.get("chapter"),
        *(values.get("chapter") for values in source_metadata),
    )
    section = _first_value(
        metadata.get("section"),
        *(values.get("section") for values in source_metadata),
    )

    return KnowledgeChunk(
        text=text,
        page_start=min(page_numbers) if page_numbers else None,
        page_end=max(page_numbers) if page_numbers else None,
        chapter=chapter,
        section=section,
        title=title,
    )


def _metadata_dict(element: Any) -> dict[str, Any]:
    metadata = getattr(element, "metadata", None)
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    if isinstance(metadata, dict):
        return metadata
    return {}


def _page_number(element: Any) -> int | None:
    value = _metadata_dict(element).get("page_number")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _text(element: Any) -> str:
    return str(getattr(element, "text", "") or "").strip()

def _first_value(*values: Any) -> str | None:
    return next((str(value).strip() for value in values if value and str(value).strip()), None)
