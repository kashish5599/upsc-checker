from __future__ import annotations

import base64
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BeforeValidator

from backend.services.answer_pdf_preparation import AnswerPdfPreparationError, AnswerPdfPreparation

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
        prepared_answer = answer_pdf_prep.prepare(
            answer_bytes,
            answer_copy.filename or "answer_copy.pdf",
        )
    except AnswerPdfPreparationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for upload in references:
        await _validate_pdf(upload, "reference_files")

    return {
        "answer_file": {
            "filename": prepared_answer.metadata.filename,
            "size_bytes": prepared_answer.metadata.size_bytes,
            "page_count": prepared_answer.metadata.page_count,
            "title": prepared_answer.metadata.title,
            "author": prepared_answer.metadata.author,
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
            for page in prepared_answer.pages
        ],
        "reference_files": f"Recieved {len(references)} ref files",
        "question_text": f"Question recieved - {question_text}",
        "processing_status": "prepared",
    }
