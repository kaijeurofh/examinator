"""Convert input material into a list of pages with 1-based page numbers.

Two sources are supported:

* **PDF** via `pypdf` — text extraction page-by-page, mirroring the document's
  natural pagination.
* **Plain text** (e.g. paste from clipboard) — split into pseudo-pages of
  configurable character size so the chunker and LLM still see page metadata
  and can populate the mandatory `source_page` field.

OCR for scanned PDFs is intentionally out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError, PyPdfError

# Reasonably-sized pseudo page for plain-text inputs; balances chunk size
# against page granularity for the `source_page` field.
_DEFAULT_PSEUDO_PAGE_CHARS = 3_000

# Hard floor on pseudo-page size: below this the snap-to-paragraph heuristic
# loses headroom and pages get split mid-sentence.
_MIN_PSEUDO_PAGE_CHARS = 200


class PdfParseError(RuntimeError):
    """Raised when the input PDF cannot be read or is empty."""


@dataclass(frozen=True, slots=True)
class PageText:
    """Text content of a single source page."""

    page_number: int  # 1-based
    text: str

    @property
    def length(self) -> int:
        return len(self.text)


def extract_pages_from_pdf(stream: BinaryIO) -> list[PageText]:
    """Extract text from a PDF stream, one entry per page.

    Empty pages are preserved (with empty `text`) so the page numbering
    stays aligned with the original document.
    """
    try:
        reader = PdfReader(stream)
    except (PdfReadError, PyPdfError, OSError, ValueError) as exc:
        raise PdfParseError(f"Could not read PDF: {exc}") from exc

    pages: list[PageText] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except (PdfReadError, PyPdfError, ValueError, KeyError) as exc:
            # A single corrupted page should not nuke the whole extraction.
            raw = f"[Seite konnte nicht extrahiert werden: {exc}]"
        pages.append(PageText(page_number=idx, text=_normalise(raw)))

    if not pages:
        raise PdfParseError("PDF contains no pages.")
    if all(p.length == 0 for p in pages):
        raise PdfParseError(
            "No text could be extracted from the PDF (scanned PDF? OCR is not supported)."
        )
    return pages


def extract_pages_from_bytes(data: bytes) -> list[PageText]:
    """Convenience wrapper for in-memory bytes (FastAPI's UploadFile.read())."""
    return extract_pages_from_pdf(BytesIO(data))


def pages_from_plaintext(
    text: str,
    page_size_chars: int = _DEFAULT_PSEUDO_PAGE_CHARS,
) -> list[PageText]:
    """Split a plain-text input into pseudo-pages of roughly equal size.

    Pseudo-pages always end on a paragraph break when one is available within
    the last 20% of the slice; this keeps each `source_page` semantically
    coherent and avoids splitting mid-sentence.
    """
    if page_size_chars < _MIN_PSEUDO_PAGE_CHARS:
        raise ValueError(f"page_size_chars must be >= {_MIN_PSEUDO_PAGE_CHARS}")
    cleaned = _normalise(text)
    if not cleaned:
        raise PdfParseError("No text content provided.")

    pages: list[PageText] = []
    start = 0
    page_num = 1
    n = len(cleaned)
    while start < n:
        end = min(start + page_size_chars, n)
        if end < n:
            # Try to snap to a paragraph break inside the last 20% of the slice.
            slack = page_size_chars // 5
            window = cleaned[end - slack : end]
            break_idx = window.rfind("\n\n")
            if break_idx != -1:
                end = end - slack + break_idx
        pages.append(PageText(page_number=page_num, text=cleaned[start:end].strip()))
        page_num += 1
        start = end
    return pages


def _normalise(text: str) -> str:
    """Collapse Windows line endings and strip trailing whitespace per line."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()
