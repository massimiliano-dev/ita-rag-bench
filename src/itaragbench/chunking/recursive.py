"""Recursive character splitter (separator hierarchy), similar in spirit to common RAG kits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from itaragbench.chunking.base import Chunk, Span, spans_to_chunks
from itaragbench.parsing.base import ParsedDocument

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "; ", " "]


def split_recursive(
    text: str, start: int, end: int, max_chars: int, separators: list[str]
) -> list[tuple[int, int]]:
    """Split text[start:end] into pieces of at most ``max_chars`` (absolute offsets)."""
    if end - start <= max_chars:
        return [(start, end)]
    for sep_i, sep in enumerate(separators):
        cuts: list[int] = []
        pos = text.find(sep, start, end)
        while pos != -1:
            cuts.append(pos + len(sep))
            pos = text.find(sep, pos + len(sep), end)
        if not cuts:
            continue
        pieces: list[tuple[int, int]] = []
        bounds = [start, *[c for c in cuts if start < c < end], end]
        cur_start = bounds[0]
        prev = bounds[0]
        for b in bounds[1:]:
            if b - cur_start > max_chars and prev > cur_start:
                pieces.append((cur_start, prev))
                cur_start = prev
            prev = b
        pieces.append((cur_start, end))
        out: list[tuple[int, int]] = []
        for s, e in pieces:
            if e - s > max_chars:
                out.extend(split_recursive(text, s, e, max_chars, separators[sep_i + 1 :]))
            else:
                out.append((s, e))
        return out
    # no separator at all: hard cut
    return [(s, min(s + max_chars, end)) for s in range(start, end, max_chars)]


@dataclass
class RecursiveChunker:
    max_chars: int = 1200
    overlap_chars: int = 150
    separators: list[str] = field(default_factory=lambda: list(DEFAULT_SEPARATORS))
    name: str = "recursive"

    def params(self) -> dict[str, Any]:
        return {
            "max_chars": self.max_chars,
            "overlap_chars": self.overlap_chars,
            "separators": self.separators,
        }

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        text = doc.text
        pieces = split_recursive(text, 0, len(text), self.max_chars, self.separators)
        spans: list[Span] = []
        for s, e in pieces:
            s2 = max(0, s - self.overlap_chars) if spans else s
            if s2 != s:
                # snap overlap start to a word boundary
                ws = text.find(" ", s2, s)
                s2 = ws + 1 if ws != -1 else s
            spans.append(Span(s2, e))
        return spans_to_chunks(doc, spans, self.name)
