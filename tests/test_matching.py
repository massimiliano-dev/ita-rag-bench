from __future__ import annotations

from itaragbench.matching import (
    TOKEN_OVERLAP_THRESHOLD,
    alignment_ratio,
    match_evidence,
    normalize,
    tokens,
)

SPAN = (
    "Il presente decreto entra in vigore il giorno successivo a quello della sua "
    "pubblicazione nella Gazzetta Ufficiale"
)


def test_normalize_nfkc_quotes_hyphen_case() -> None:
    assert normalize("Co\ufb01nanziamento") == "cofinanziamento"  # ligature
    assert normalize("dell\u2019ente") == "dell'ente"
    assert normalize("pro-\ngramma  TRIENNALE") == "programma triennale"
    assert normalize("\u00abtesto\u00bb") == '"testo"'
    assert normalize("a\u00a0b\u00adc") == "a bc"


def test_exact_after_normalisation() -> None:
    chunk = (
        "Art. 3.\nIL PRESENTE decreto entra in vigore il giorno succes-\nsivo a quello "
        "della sua pubblicazione nella Gazzetta Ufficiale."
    )
    r = match_evidence(SPAN, chunk)
    assert r.matched and r.method == "exact"


def test_span_split_across_page_break_with_running_header() -> None:
    chunk = (
        "Il presente decreto entra in vigore il giorno successivo\n"
        "GAZZETTA UFFICIALE DELLA REPUBBLICA ITALIANA Serie generale - n. 63 15-3-2023\n"
        "— 12 —\n"
        "a quello della sua pubblica-\nzione nella Gazzetta Ufficiale."
    )
    r = match_evidence(SPAN, chunk)
    assert r.matched and r.method == "fuzzy" and r.score == 1.0


def test_markdown_table_cells_match() -> None:
    span = "Officine per la riparazione di veicoli a motore"
    chunk = "| 53 | **Officine per la riparazione** di veicoli a motore | fino a 9 | oltre 9 |"
    assert match_evidence(span, chunk).matched


def test_partial_span_is_not_relevant() -> None:
    r = match_evidence(SPAN, "Il presente decreto entra in vigore il giorno successivo")
    assert not r.matched


def test_scrambled_tokens_do_not_match() -> None:
    scrambled = " ".join(reversed(tokens(SPAN)))
    assert not match_evidence(SPAN, scrambled).matched


def test_one_wrong_token_is_tolerated_but_many_are_not() -> None:
    long_span = SPAN + " della Repubblica italiana"
    one_off = long_span.replace("decreto", "decret0")
    assert match_evidence(long_span, one_off).matched
    many_off = "Il presente regolamento si applica dal mese successivo alla data di adozione"
    assert not match_evidence(long_span, many_off).matched


def test_short_spans_require_exact_match() -> None:
    assert not match_evidence("art. 41, c. 6", "art 41 comma 6").matched
    assert match_evidence("Art. 41, c. 6", "vedi art. 41, c. 6 del decreto").matched


def test_alignment_ratio_bounds() -> None:
    assert alignment_ratio([], ["a"]) == 0.0
    assert alignment_ratio(["a", "b"], ["x", "a", "y", "b"]) == 1.0
    assert 0.0 < TOKEN_OVERLAP_THRESHOLD < 1.0
