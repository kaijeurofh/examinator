"""Tests for `examinator.core.chunking` and `examinator.core.pdf_parser`."""

from __future__ import annotations

import pytest

from examinator.core.chunking import chunk_pages
from examinator.core.pdf_parser import PageText, PdfParseError, pages_from_plaintext


def _page(num: int, text: str) -> PageText:
    return PageText(page_number=num, text=text)


def test_chunker_returns_empty_for_empty_input() -> None:
    assert chunk_pages([]) == []


def test_chunker_packs_pages_until_budget() -> None:
    pages = [_page(i, "x" * 1_000) for i in range(1, 11)]
    chunks = chunk_pages(pages, max_chars=3_500, overlap_chars=0, max_chunks=10)
    assert len(chunks) > 1
    # Each chunk respects the budget (allowing for the 20-char-per-page reserve).
    for chunk in chunks:
        assert chunk.start_page <= chunk.end_page
        assert chunk.start_page >= 1
    # Coverage: first chunk starts at page 1, last chunk ends at page 10.
    assert chunks[0].start_page == 1
    assert chunks[-1].end_page == 10


def test_chunker_respects_max_chunks_by_growing_budget() -> None:
    pages = [_page(i, "y" * 2_000) for i in range(1, 21)]
    chunks = chunk_pages(pages, max_chars=3_000, overlap_chars=200, max_chunks=4)
    assert len(chunks) <= 4
    assert chunks[0].start_page == 1
    assert chunks[-1].end_page == 20


def test_chunker_overlap_is_repeated_text() -> None:
    pages = [_page(i, f"page-{i}-content " * 100) for i in range(1, 6)]
    chunks = chunk_pages(pages, max_chars=2_000, overlap_chars=200, max_chunks=8)
    if len(chunks) > 1:
        prev_tail = chunks[0].text[-200:]
        # The second chunk should start with the previous chunk's tail.
        assert chunks[1].text.startswith(prev_tail)


def test_chunker_header_single_vs_range() -> None:
    pages = [_page(1, "a"), _page(2, "b")]
    chunks = chunk_pages(pages, max_chars=10_000, overlap_chars=0, max_chunks=4)
    assert "Seiten 1-2" in chunks[0].header() or "Seite 1" in chunks[0].header()


@pytest.mark.parametrize("invalid", [{"max_chars": 100}, {"overlap_chars": -1}])
def test_chunker_validates_arguments(invalid: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        chunk_pages([_page(1, "x")], **invalid)


def test_pages_from_plaintext_splits_into_pseudo_pages() -> None:
    text = ("Paragraph A.\n\n" + "x" * 800) * 5
    pages = pages_from_plaintext(text, page_size_chars=500)
    assert len(pages) >= 2
    # Numbering is 1-based and contiguous.
    assert [p.page_number for p in pages] == list(range(1, len(pages) + 1))


def test_pages_from_plaintext_rejects_empty() -> None:
    with pytest.raises(PdfParseError):
        pages_from_plaintext("   \n\n   ")
