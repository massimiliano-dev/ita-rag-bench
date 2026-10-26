"""Structure-aware chunker for Italian normative texts.

Sections start at article headings (``Art. 6.``, ``Articolo 12-bis``) and annex headings
(``ALLEGATO I``); a preceding hierarchy heading (Libro/Parte/Titolo/Capo/Sezione) is kept with
the article that follows it. Articles longer than ``max_chars`` are split at *comma* boundaries
(``1.``, ``2-bis.`` at line start) and every part repeats the article heading, so a retrieved
chunk always says which article it belongs to. A single comma longer than ``max_chars`` falls
back to the recursive splitter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from itaragbench.chunking.base import Chunk, Span, spans_to_chunks
from itaragbench.chunking.recursive import DEFAULT_SEPARATORS, split_recursive
from itaragbench.parsing.base import ParsedDocument

_LATIN = r"(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|nonies|decies)"
_MD = r"(?:[#>*_\-\s]*)"
ARTICLE_RE = re.compile(
    rf"^{_MD}(?:Art\.|Articolo)\s*(\d+(?:\s*-?\s*{_LATIN})?)\s*\.?\s*(?:\*\*|__)?\s*(.{{0,100}})$",
    re.IGNORECASE,
)
HIER_RE = re.compile(
    rf"^{_MD}(LIBRO|PARTE|TITOLO|CAPO|SEZIONE)\s+([IVXLCDM]+|[0-9]+|UNICO|PRIMO|SECONDO)\b",
    re.IGNORECASE,
)
ANNEX_RE = re.compile(rf"^{_MD}(ALLEGATO|ANNEX|TABELLA)\b(.{{0,80}})$")
COMMA_RE = re.compile(rf"^{_MD}(\d{{1,3}}(?:\s*-\s*{_LATIN})?)\s*\.\s+\S")


@dataclass
class _Line:
    start: int
    end: int
    text: str


def _lines(text: str) -> list[_Line]:
    out: list[_Line] = []
    pos = 0
    for raw in text.split("\n"):
        out.append(_Line(pos, pos + len(raw), raw.strip()))
        pos += len(raw) + 1
    return out


def article_label(line: str) -> str | None:
    m = ARTICLE_RE.match(line)
    if not m:
        return None
    return re.sub(r"\s+|-", "", m.group(1)).lower()


@dataclass
class LegalStructureChunker:
    max_chars: int = 1500
    min_chars: int = 80
    name: str = "structure"

    def params(self) -> dict[str, Any]:
        return {"max_chars": self.max_chars, "min_chars": self.min_chars}

    # ------------------------------------------------------------------ helpers
    def _boundaries(self, lines: list[_Line]) -> list[tuple[int, str]]:
        """Return (line_index, kind) of section starts; kind in {article, annex}."""
        starts: list[tuple[int, str]] = []
        for i, ln in enumerate(lines):
            if len(ln.text) > 140 or not ln.text:
                continue
            kind = None
            if ARTICLE_RE.match(ln.text):
                kind = "article"
            elif ANNEX_RE.match(ln.text):
                kind = "annex"
            if kind is None:
                continue
            j = i
            k = i - 1
            steps = 0
            while k >= 0 and steps < 6:
                t = lines[k].text
                if not t:
                    k -= 1
                    continue
                if len(t) > 100:
                    break
                if HIER_RE.match(t):
                    j = k
                k -= 1
                steps += 1
            if starts and j <= starts[-1][0]:
                j = i
            starts.append((j, kind))
        return starts

    def _heading(self, lines: list[_Line], first: int, last: int) -> str:
        """Article heading (+ rubric) found in lines[first:last]."""
        for i in range(first, min(last, first + 8)):
            t = lines[i].text
            if ARTICLE_RE.match(t) or ANNEX_RE.match(t):
                head = t
                nxt = next(
                    (lines[k].text for k in range(i + 1, min(last, i + 4)) if lines[k].text),
                    "",
                )
                if nxt and len(nxt) < 120 and not COMMA_RE.match(nxt):
                    head = f"{head} {nxt}"
                return head[:200]
        return ""

    def _split_article(self, text: str, lines: list[_Line], a: int, b: int) -> list[Span]:
        start, end = lines[a].start, lines[b - 1].end if b > a else lines[a].end
        if end - start <= self.max_chars:
            return [Span(start, end)]
        heading = self._heading(lines, a, b)
        comma_starts = [lines[i].start for i in range(a + 1, b) if COMMA_RE.match(lines[i].text)]
        bounds = [start, *comma_starts, end]
        units = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
        spans: list[Span] = []
        cur_s, cur_e = units[0]
        for s, e in units[1:]:
            if e - cur_s <= self.max_chars:
                cur_e = e
            else:
                spans.extend(self._emit(text, cur_s, cur_e, heading, first=not spans))
                cur_s, cur_e = s, e
        spans.extend(self._emit(text, cur_s, cur_e, heading, first=not spans))
        return spans

    def _emit(self, text: str, s: int, e: int, heading: str, first: bool) -> list[Span]:
        budget = self.max_chars - (0 if first else len(heading) + 1)
        budget = max(budget, self.max_chars // 2)
        pieces = split_recursive(text, s, e, budget, DEFAULT_SEPARATORS)
        out: list[Span] = []
        for idx, (ps, pe) in enumerate(pieces):
            prefix = "" if (first and idx == 0) else heading
            out.append(Span(ps, pe, prefix))
        return out

    # ------------------------------------------------------------------ main
    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        text = doc.text
        lines = _lines(text)
        starts = self._boundaries(lines)
        spans: list[Span] = []
        first_line = starts[0][0] if starts else len(lines)
        if first_line > 0:
            pre_end = lines[first_line - 1].end
            for s, e in split_recursive(text, 0, pre_end, self.max_chars, DEFAULT_SEPARATORS):
                spans.append(Span(s, e))
        for n, (a, _kind) in enumerate(starts):
            b = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
            if b <= a:
                continue
            spans.extend(self._split_article(text, lines, a, b))
        # merge tiny spans (e.g. heading-only fragments) into the following span
        merged: list[Span] = []
        carry: Span | None = None
        for sp in spans:
            if carry is not None:
                sp = Span(carry.start, sp.end, sp.prefix if sp.prefix else carry.prefix)
                carry = None
            if len(text[sp.start : sp.end].strip()) < self.min_chars:
                carry = sp
                continue
            merged.append(sp)
        if carry is not None:
            if merged:
                last = merged.pop()
                merged.append(Span(last.start, carry.end, last.prefix))
            else:
                merged.append(carry)
        return spans_to_chunks(doc, merged, self.name)
