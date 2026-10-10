from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BeforeValidator

from backend.ai.config import EvaluationConfigurationError, EvaluationSettings
from backend.ai.evaluation import AnswerEvaluationService, EvaluationError
from backend.knowledge.config import KnowledgeConfigurationError, KnowledgeSettings
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

    no_questions_detected = not QASegmentation.questions
    if no_questions_detected:
        return {
            "pages": QASegmentation.model_dump(),
            "reference_files": f"Recieved {len(references)} ref files",
            "processing_status": "no_questions_detected",
        }

    question_results: list[dict[str, object]] = []
    try:
        evaluator = AnswerEvaluationService(
            evaluation_settings=EvaluationSettings.from_environment(),
            knowledge_settings=KnowledgeSettings.from_environment(),
        )
    except (EvaluationConfigurationError, KnowledgeConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="The answer evaluation service is unavailable.",
        ) from error

    for question in QASegmentation.questions:
        page_numbers = set(question.pages)
        answer_pages = tuple(
            page
            for page in prepared_answer_copy.pages
            if page.page_number in page_numbers
        )
        try:
            evaluation = await evaluator.evaluate(
                question=question,
                answer_pages=answer_pages,
            )
        except EvaluationError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        question_result = question.model_dump()
        question_result["evaluation"] = evaluation.model_dump()
        question_results.append(question_result)
        print(f"Evaluation result for question {question.question_id}: {evaluation.model_dump()}")

    segmentation = QASegmentation.model_dump()

    return {
        "pages": segmentation,
        "evaluation": question_results,
        "reference_files": f"Recieved {len(references)} ref files",
        "processing_status": "evaluated",
    }
