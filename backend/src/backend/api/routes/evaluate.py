from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BeforeValidator

from backend.knowledge.config import KnowledgeConfigurationError, KnowledgeSettings
from backend.knowledge.retrieval import KnowledgeRetrievalError, KnowledgeRetrievalService
from backend.services.answer_pdf_preparation import AnswerPdfPreparationError, AnswerPdfPreparation
from backend.services.answer_segmentation import SegmentationError, segment_answer_copy

router = APIRouter()
answer_pdf_prep = AnswerPdfPreparation()

def _empty_reference_files(value: object) -> object:
    if value == "" or value == [""]:
        return None
    return value

async def _validate_pdf(upload: UploadFile, field_name: str) -> None:
    header = await upload.read(5)
    await upload.seek(0)
    if header != b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid PDF file.",
        )

@router.post("/evaluate")
async def evaluate(
    answer_copy: Annotated[UploadFile, File(...)],
    reference_files: Annotated[
        list[UploadFile] | None,
        BeforeValidator(_empty_reference_files),
        File(),
    ] = None,
    question_text: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    references = reference_files or []
    answer_bytes = await answer_copy.read()
    try:
        prepared_answer_copy = answer_pdf_prep.prepare(
            answer_bytes,
            answer_copy.filename or "answer_copy.pdf",
        )
    except AnswerPdfPreparationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for upload in references:
        await _validate_pdf(upload, "reference_files")

    try:
        QASegmentation = await segment_answer_copy(prepared_answer_copy)
    except SegmentationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    print(f"Completed question segmentation - ${QASegmentation.model_dump()}")
    if any(
        question.retrieval_query and question.retrieval_query.strip()
        for question in QASegmentation.questions
    ):
        try:
            retrieval = KnowledgeRetrievalService(
                settings=KnowledgeSettings.from_environment(),
            )
        except KnowledgeConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="The knowledge retrieval service is unavailable.",
            ) from error

        for question in QASegmentation.questions:
            if not question.retrieval_query or not question.retrieval_query.strip():
                continue
            try:
                question.context = await retrieval.retrieve_context(
                    question.retrieval_query,
                    top_k=12,
                )
                print(f"Retrieved context for {question.question_id} - {question.context}")
            except KnowledgeRetrievalError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error

    segmentation = QASegmentation.model_dump()

    return {
        "answer_file": {
            "filename": prepared_answer_copy.metadata.filename,
            "size_bytes": prepared_answer_copy.metadata.size_bytes,
            "page_count": prepared_answer_copy.metadata.page_count,
            "title": prepared_answer_copy.metadata.title,
            "author": prepared_answer_copy.metadata.author,
        },
        "rendered_pages": [
            {
                "page_number": page.page_number,
                "mime_type": page.mime_type,
                "encoding": "base64",
                # "image": base64.b64encode(page.image_bytes).decode("ascii"),
                "width": page.width,
                "height": page.height,
            }
            for page in prepared_answer_copy.pages
        ],
        "segmentation": segmentation,
        "reference_files": f"Recieved {len(references)} ref files",
        "question_text": f"Question recieved - {question_text}",
        "processing_status": "segmented",
    }
