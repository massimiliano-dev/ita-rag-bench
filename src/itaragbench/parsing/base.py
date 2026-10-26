"""Parsed document model shared by all parsers."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Any

PAGE_SEPARATOR = "\n\n"


@dataclass
class ParsedPage:
    page_no: int  # 1-based physical page number in the source PDF
    text: str


@dataclass
class ParsedDocument:
    doc_id: str
    parser: str
    parser_version: str
    pages: list[ParsedPage]
    seconds: float
    warnings: list[str] = field(default_factory=list)
    _offsets: list[int] = field(default_factory=list, repr=False)
    _text: str | None = field(default=None, repr=False)

    @property
    def text(self) -> str:
        if self._text is None:
            parts: list[str] = []
            offsets: list[int] = []
            pos = 0
            for i, p in enumerate(self.pages):
                if i > 0:
                    parts.append(PAGE_SEPARATOR)
                    pos += len(PAGE_SEPARATOR)
                offsets.append(pos)
                parts.append(p.text)
                pos += len(p.text)
            self._text = "".join(parts)
            self._offsets = offsets
        return self._text

    def page_at(self, char_offset: int) -> int:
        """Physical page number that contains ``char_offset`` of :attr:`text`."""
        _ = self.text
        if not self.pages:
            return 0
        idx = bisect.bisect_right(self._offsets, char_offset) - 1
        idx = max(0, min(idx, len(self.pages) - 1))
        return self.pages[idx].page_no

    def to_json(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "parser": self.parser,
            "parser_version": self.parser_version,
            "seconds": self.seconds,
            "warnings": self.warnings,
            "pages": [{"page_no": p.page_no, "text": p.text} for p in self.pages],
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> ParsedDocument:
        return cls(
            doc_id=str(raw["doc_id"]),
            parser=str(raw["parser"]),
            parser_version=str(raw["parser_version"]),
            pages=[ParsedPage(int(p["page_no"]), str(p["text"])) for p in raw["pages"]],
            seconds=float(raw["seconds"]),
            warnings=[str(w) for w in raw.get("warnings", [])],
        )
