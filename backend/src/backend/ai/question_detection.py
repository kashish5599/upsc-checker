from __future__ import annotations

import base64
from typing import TypeVar, Literal

from backend.services.answer_pdf_preparation import RenderedPage
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from pydantic import BaseModel, ConfigDict, Field
from langfuse.langchain import CallbackHandler
from dotenv import load_dotenv

load_dotenv()

VISION_MODEL="gemini-3.5-flash-lite"

TModel = TypeVar("TModel", bound=BaseModel)
langfuse_handler = CallbackHandler()

class SegmentedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question_id: str = Field(description="Sequential identifier such as Q1 or Q2.")
    question_text: str | None = Field(
        description="Printed question wording, copied exactly when legible; otherwise null."
    )
    start_page: int = Field(description="One-based page where this answer begins.", ge=1)
    pages: list[int] = Field(
        min_length=1,
        description="One-based pages containing this question's answer, in page order.",
    )

class ExcludedPage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    page: int = Field(ge=1)
    reason: Literal["blank", "instruction", "unrelated", "no_answer_content"]


class AnswerSegmentation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    questions: list[SegmentedQuestion]
    excluded_pages: list[ExcludedPage]


class SegmentationError(ValueError):
    """Raised when the structured result is inconsistent with the source pages."""


_SEGMENTATION_PROMPT = """Segment the supplied answer-copy pages into question answers.

For each distinct answer, identify its first page and group every continuation page
with it. Create question IDs Q1, Q2, ... in the order answers begin. A question may
continue across multiple pages. If two answers appear on the same page, that page
may appear in both page lists. Extract only printed question wording visible in the
images, exactly as printed; do not transcribe the handwritten answer. Use null when
no printed wording is visible or it cannot be read confidently.

Ignore blank pages, instructions, and unrelated content by placing them in
excluded_pages with the most appropriate reason. Do not exclude a page containing
any answer. Every source page must either occur in at least one question's pages or
once in excluded_pages. Use the supplied one-based page numbers. Return only data
matching the required JSON schema; do not add commentary."""


async def generate_answer_copy_segmentation(pages: tuple[RenderedPage, ...], page_count: int) -> TModel:
    prompt=(
        f"{_SEGMENTATION_PROMPT}\n\n"
        f"This answer copy contains {page_count} pages."
    )
    model = ChatGoogleGenerativeAI(
        model=VISION_MODEL,
        temperature=0
    ).with_structured_output(AnswerSegmentation, method="json_schema")
    content: list[dict[str, str]] = []

    for page in pages:
        encoded_image = base64.b64encode(page.image_bytes).decode("ascii")
        content.extend(
            [
                {"type": "text", "text": f"Answer-copy page {page.page_number} follows:"},
                {
                    "type": "image_url",
                    "image_url": f"data:{page.mime_type};base64,{encoded_image}",
                },
            ]
        )
    content.append({"type": "text", "text": prompt})

    try:
        response = await model.ainvoke(
            [HumanMessage(content=content)],
            config={"callbacks": [langfuse_handler]}
        )
    except Exception as error:
        raise SegmentationError("Gemini failed to segment the answer-copy pages.") from error

    try:
        if isinstance(response, AnswerSegmentation):
            return response
        return AnswerSegmentation.model_validate(response)
    except Exception as error:
        raise SegmentationError("Gemini returned invalid structured output.") from error