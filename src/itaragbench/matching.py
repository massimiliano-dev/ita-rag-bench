"""Chunker-independent relevance: does a chunk contain a gold evidence span?

Step 1 - normalisation (applied to both span and chunk):
  Unicode NFKC (ligatures such as "ﬁ" -> "fi"), soft hyphens removed, typographic quotes and
  apostrophes unified, de-hyphenation across line breaks ("pro-\\ngramma" -> "programma"),
  markdown emphasis/table pipes removed, whitespace collapsed, case folded.
Step 2 - exact substring test on the normalised strings.
Step 3 - fallback for text interrupted by page furniture (running headers, page numbers) or
  small extraction glitches: token-level local alignment. Span tokens must be matched IN ORDER
  inside the chunk; extra chunk tokens inside the matched region cost only ``GAP_PENALTY`` each,
  so a 20-token running header inserted in the middle of a span is tolerated. The chunk is
  relevant if aligned span tokens / span tokens >= ``TOKEN_OVERLAP_THRESHOLD`` (0.85).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

TOKEN_OVERLAP_THRESHOLD = 0.85
GAP_PENALTY = 0.05  # cost of an extra chunk token inside the aligned region
MIN_SPAN_TOKENS_FOR_FUZZY = 6

_QUOTES = str.maketrans(
    {
        0x2018: "'",  # left single quotation mark
        0x2019: "'",  # right single quotation mark
        0x02BC: "'",  # modifier letter apostrophe
        0x0060: "'",  # grave accent used as apostrophe
        0x00B4: "'",  # acute accent used as apostrophe
        0x201C: '"',
        0x201D: '"',
        0x00AB: '"',  # guillemets
        0x00BB: '"',
        0x2013: "-",  # en dash
        0x2014: "-",  # em dash
        0x2212: "-",  # minus sign
        0x00A0: " ",  # no-break space
        0x00AD: None,  # soft hyphen
    }
)
_DEHYPHEN = re.compile(r"(\w)-\s*\n\s*(\w)")
_MD = re.compile(r"[*_#|>]+")
_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"\w+", re.UNICODE)


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    t = _DEHYPHEN.sub(r"\1\2", t)
    t = _MD.sub(" ", t)
    t = _WS.sub(" ", t)
    return t.strip().casefold()


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


def alignment_ratio(span_toks: list[str], chunk_toks: list[str]) -> float:
    """Semi-global alignment of ``span_toks`` inside ``chunk_toks``.

    The alignment may start and end anywhere in the chunk (free leading/trailing chunk tokens).
    Scoring: +1 per matched span token, -1 per skipped span token, ``-GAP_PENALTY`` per chunk
    token skipped *inside* the aligned region. Returns matched / len(span) for the best path.
    """
    n, m = len(span_toks), len(chunk_toks)
    if n == 0 or m == 0:
        return 0.0
    prev_s = [0.0] * (m + 1)
    prev_k = [0] * (m + 1)
    for i in range(1, n + 1):
        a = span_toks[i - 1]
        cur_s = [-float(i)] + [0.0] * m
        cur_k = [0] * (m + 1)
        for j in range(1, m + 1):
            best, k = prev_s[j] - 1.0, prev_k[j]  # skip span token
            if a == chunk_toks[j - 1]:
                cand = prev_s[j - 1] + 1.0
                if cand > best:
                    best, k = cand, prev_k[j - 1] + 1
            cand = cur_s[j - 1] - GAP_PENALTY  # skip chunk token inside the region
            if cand > best:
                best, k = cand, cur_k[j - 1]
            cur_s[j], cur_k[j] = best, k
        prev_s, prev_k = cur_s, cur_k
    j_best = max(range(m + 1), key=lambda j: prev_s[j])
    return prev_k[j_best] / n


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    method: str  # "exact" | "fuzzy" | "none"
    score: float


def match_evidence(evidence: str, chunk_text: str) -> MatchResult:
    ev = normalize(evidence)
    ch = normalize(chunk_text)
    if ev and ev in ch:
        return MatchResult(True, "exact", 1.0)
    ev_t = _TOKEN.findall(ev)
    if len(ev_t) < MIN_SPAN_TOKENS_FOR_FUZZY:
        return MatchResult(False, "none", 0.0)
    ch_t = _TOKEN.findall(ch)
    # cheap prefilter on bag-of-tokens coverage
    cc = Counter(ch_t)
    ec = Counter(ev_t)
    covered = sum(min(c, cc[t]) for t, c in ec.items()) / len(ev_t)
    if covered < TOKEN_OVERLAP_THRESHOLD:
        return MatchResult(False, "none", covered)
    ratio = alignment_ratio(ev_t, ch_t)
    return MatchResult(ratio >= TOKEN_OVERLAP_THRESHOLD, "fuzzy", ratio)
