"""Fixed-size chunker over whitespace tokens with overlap."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from itaragbench.chunking.base import Chunk, Span, spans_to_chunks
from itaragbench.parsing.base import ParsedDocument

_TOKEN = re.compile(r"\S+")


@dataclass
class FixedTokenChunker:
    """Windows of ``size`` whitespace-delimited tokens, sliding by ``size - overlap``.

    Tokens are whitespace tokens (not model sub-words) so the chunker is model independent.
    """

    size: int = 200
    overlap: int = 40
    name: str = "fixed"

    def __post_init__(self) -> None:
        if not 0 <= self.overlap < self.size:
            raise ValueError("overlap must be in [0, size)")

    def params(self) -> dict[str, Any]:
        return {"size": self.size, "overlap": self.overlap, "unit": "whitespace-token"}

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        toks = [(m.start(), m.end()) for m in _TOKEN.finditer(doc.text)]
        spans: list[Span] = []
        step = self.size - self.overlap
        i = 0
        while i < len(toks):
            j = min(i + self.size, len(toks))
            spans.append(Span(toks[i][0], toks[j - 1][1]))
            if j == len(toks):
                break
            i += step
        return spans_to_chunks(doc, spans, self.name)
