from __future__ import annotations
from backend.ai.question_detection import AnswerSegmentation, SegmentationError, generate_answer_copy_segmentation
from backend.services.answer_pdf_preparation import AnswerPdf

def _validate_result(result: AnswerSegmentation, page_count: int) -> None:
        covered_pages: set[int] = set()
        previous_start_page = 0

        for index, question in enumerate(result.questions, start=1):
            if question.question_id != f"Q{index}":
                raise SegmentationError("Question IDs must be sequential from Q1.")
            if question.start_page < previous_start_page:
                raise SegmentationError("Questions must be ordered by their start page.")
            if question.start_page not in question.pages:
                raise SegmentationError("Each question's start page must be in its page list.")
            if question.pages != sorted(set(question.pages)):
                raise SegmentationError("Question pages must be unique and in page order.")
            if any(page < 1 or page > page_count for page in question.pages):
                raise SegmentationError("A question references a page outside the document.")
            covered_pages.update(question.pages)
            previous_start_page = question.start_page

        excluded_numbers: set[int] = set()
        for excluded in result.excluded_pages:
            if not 1 <= excluded.page <= page_count:
                raise SegmentationError("An excluded page is outside the document.")
            if excluded.page in excluded_numbers:
                raise SegmentationError("An excluded page may only be listed once.")
            if excluded.page in covered_pages:
                raise SegmentationError("A page cannot be both answered and excluded.")
            excluded_numbers.add(excluded.page)

        expected_pages = set(range(1, page_count + 1))
        if covered_pages | excluded_numbers != expected_pages:
            raise SegmentationError("Every document page must be classified.")

async def segment_answer_copy(aw_copy: AnswerPdf) -> AnswerSegmentation:
    try:
        result = await generate_answer_copy_segmentation(
            pages = aw_copy.pages,
            page_count=aw_copy.metadata.page_count
        )
        print(f"Segmentation result - ${result}")
        _validate_result(result, aw_copy.metadata.page_count)
    except:
        raise

    return result

