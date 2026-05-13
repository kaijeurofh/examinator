"""Page-aware chunking with overlap.

The chunker groups consecutive pages until a target character budget is
reached, then emits a `Chunk` carrying both the concatenated text and the
``start_page`` / ``end_page`` range so the LLM can populate the mandatory
``source_page`` field on every generated question.

Overlap is implemented by repeating the trailing N characters of the previous
chunk in the next chunk's text (without changing the page range, since the
overlap is purely a continuity aid for the LLM). The total number of chunks
is capped to keep token cost and latency predictable.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from examinator.core.pdf_parser import PageText

DEFAULT_CHUNK_CHARS = 8_000
DEFAULT_OVERLAP_CHARS = 800
DEFAULT_MAX_CHUNKS = 8

# Hard floor on per-chunk character budget: below this, even short prompts get
# fragmented enough to lose coherence.
_MIN_CHUNK_CHARS = 500

# Cap on the doubling loop that re-balances chunk count. Doubling halves the
# count per iteration, so this is a safety net (O(log n) converges fast).
_MAX_REBALANCE_ITERATIONS = 10


@dataclass(frozen=True, slots=True)
class Chunk:
    """A page-aware chunk of study material."""

    index: int  # 0-based position in the chunk sequence
    start_page: int  # 1-based, inclusive
    end_page: int  # 1-based, inclusive
    text: str

    def header(self) -> str:
        """Human-readable header to prepend when sending the chunk to the LLM."""
        if self.start_page == self.end_page:
            return f"[Seite {self.start_page}]"
        return f"[Seiten {self.start_page}-{self.end_page}]"


def chunk_pages(
    pages: list[PageText],
    *,
    max_chars: int = DEFAULT_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> list[Chunk]:
    """Group pages into overlapping chunks bounded by `max_chars`.

    A single page that exceeds ``max_chars`` is emitted as one oversize chunk
    rather than split across page boundaries — the per-page ``source_page``
    invariant trumps the character budget.

    If the result exceeds ``max_chunks`` the chunks are re-balanced by
    inflating the character budget until the cap is met. This keeps cost
    predictable on large documents while still giving the LLM coverage.
    """
    if not pages:
        return []
    if max_chars < _MIN_CHUNK_CHARS:
        raise ValueError(f"max_chars must be >= {_MIN_CHUNK_CHARS}")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be in [0, max_chars)")
    if max_chunks < 1:
        raise ValueError("max_chunks must be >= 1")

    chunks = _build_chunks(pages, max_chars=max_chars, overlap_chars=overlap_chars)

    # Re-balance if we overshot. Doubling the budget halves chunk count, so a
    # tight loop converges in O(log n) iterations.
    iterations = 0
    while len(chunks) > max_chunks and iterations < _MAX_REBALANCE_ITERATIONS:
        max_chars *= 2
        overlap_chars = min(overlap_chars, max_chars - 1)
        chunks = _build_chunks(pages, max_chars=max_chars, overlap_chars=overlap_chars)
        iterations += 1
    return chunks[:max_chunks]


def _build_chunks(
    pages: list[PageText],
    *,
    max_chars: int,
    overlap_chars: int,
) -> list[Chunk]:
    raw: list[Chunk] = []
    buffer_pages: list[PageText] = []
    buffer_len = 0
    for page in pages:
        page_text = page.text
        # Reserve room for the page header in the concatenated text.
        page_payload_len = len(page_text) + 20
        if buffer_pages and buffer_len + page_payload_len > max_chars:
            raw.append(_emit(buffer_pages, len(raw)))
            buffer_pages = []
            buffer_len = 0
        buffer_pages.append(page)
        buffer_len += page_payload_len
    if buffer_pages:
        raw.append(_emit(buffer_pages, len(raw)))

    if overlap_chars == 0 or len(raw) <= 1:
        return raw

    overlapped: list[Chunk] = [raw[0]]
    for prev, curr in pairwise(raw):
        tail = prev.text[-overlap_chars:]
        overlapped.append(
            Chunk(
                index=curr.index,
                start_page=curr.start_page,
                end_page=curr.end_page,
                text=tail + "\n\n" + curr.text,
            )
        )
    return overlapped


def _emit(buffer_pages: list[PageText], index: int) -> Chunk:
    parts = [f"[Seite {p.page_number}]\n{p.text}" for p in buffer_pages]
    return Chunk(
        index=index,
        start_page=buffer_pages[0].page_number,
        end_page=buffer_pages[-1].page_number,
        text="\n\n".join(parts),
    )
