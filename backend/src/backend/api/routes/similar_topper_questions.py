from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Query

from backend.knowledge.config import KnowledgeSettings
from backend.knowledge.topper_questions import SimilarTopperQuestionsService

router = APIRouter(tags=["topper questions"])
logger = logging.getLogger(__name__)


@router.get("/similar-topper-questions")
async def get_similar_topper_questions(
    question_text: Annotated[str, Query(min_length=1)],
) -> list[dict[str, Any]] | None:
    """Retrieve highly similar topper questions for a detected question."""
    try:
        service = SimilarTopperQuestionsService(
            settings=KnowledgeSettings.from_environment(),
        )
    except Exception:
        logger.exception("Could not initialize similar topper-question retrieval.")
        return None

    return await service.retrieve_similar_questions(question_text)
