from __future__ import annotations

from dataclasses import dataclass

import pymupdf


@dataclass(frozen=True)
class RenderedPage:
    """A rendered PDF page. Page numbers are one-based for display and tracing."""

    page_number: int
    image_bytes: bytes
    mime_type: str
    width: int
    height: int


@dataclass(frozen=True)
class PdfMetadata:
    filename: str
    size_bytes: int
    page_count: int
    title: str | None
    author: str | None


@dataclass(frozen=True)
class AnswerPdf:
    metadata: PdfMetadata
    pages: tuple[RenderedPage, ...]


class AnswerPdfPreparationError(ValueError):
    """Raised when an input cannot be read as a renderable PDF document."""


class AnswerPdfPreparation:
    """Validate a PDF and render its pages as ordered PNG images."""

    def __init__(self, dpi: int = 300) -> None:
        if dpi <= 0:
            raise ValueError("dpi must be a positive integer")
        self.dpi = dpi

    def prepare(self, pdf_bytes: bytes, filename: str) -> AnswerPdf:
        if not pdf_bytes.startswith(b"%PDF-"):
            raise AnswerPdfPreparationError("The uploaded file does not have a PDF signature.")

        try:
            with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
                page_count = document.page_count
                if page_count < 1:
                    raise AnswerPdfPreparationError("The PDF does not contain any pages.")

                #Extract the Answer copy as images of pages
                pages = tuple(
                    self._render_page(document.load_page(index), index + 1)
                    for index in range(page_count)
                )
                document_metadata = document.metadata or {}
                metadata = PdfMetadata(
                    filename=filename,
                    size_bytes=len(pdf_bytes),
                    page_count=page_count,
                    title=document_metadata.get("title") or None,
                    author=document_metadata.get("author") or None,
                )
        except AnswerPdfPreparationError:
            raise
        except (pymupdf.FileDataError, pymupdf.EmptyFileError, RuntimeError, ValueError) as error:
            raise AnswerPdfPreparationError("The uploaded file is not a readable PDF.") from error

        return AnswerPdf(metadata=metadata, pages=pages)

    def _render_page(self, page: pymupdf.Page, page_number: int) -> RenderedPage:
        pixmap = page.get_pixmap(dpi=self.dpi, colorspace=pymupdf.csRGB, alpha=False)
        return RenderedPage(
            page_number=page_number,
            image_bytes=pixmap.tobytes("png"),
            mime_type="image/png",
            width=pixmap.width,
            height=pixmap.height,
        )
