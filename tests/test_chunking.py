from __future__ import annotations

from itaragbench.chunking import make_chunker
from itaragbench.chunking.structure import article_label
from itaragbench.parsing.base import ParsedDocument


def test_fixed_chunker_overlap(legal_doc: ParsedDocument) -> None:
    chunks = make_chunker("fixed", {"size": 50, "overlap": 10}).chunk(legal_doc)
    assert len(chunks) > 3
    first = chunks[0].text.split()
    second = chunks[1].text.split()
    assert first[-10:] == second[:10]
    assert all(len(c.text.split()) <= 50 for c in chunks)


def test_recursive_chunker_respects_size(legal_doc: ParsedDocument) -> None:
    chunks = make_chunker("recursive", {"max_chars": 400, "overlap_chars": 50}).chunk(legal_doc)
    assert all(len(c.text) <= 450 for c in chunks)
    assert chunks[0].page_start == 1 and chunks[-1].page_end == 2


def test_structure_chunker_splits_long_article_at_commi(legal_doc: ParsedDocument) -> None:
    chunks = make_chunker("structure", {"max_chars": 800}).chunk(legal_doc)
    art2 = [c for c in chunks if "Sanzioni amministrative" in c.text]
    assert len(art2) >= 3
    for c in art2:
        assert c.text.startswith("Art. 2.")  # heading kept in every part
        body = c.text.split("\n", 1)[1] if c.heading else c.text
        assert "Comma numero" in body
    # parts after the first start exactly at a comma boundary
    for c in art2[1:]:
        assert c.text.split("\n", 1)[1].lstrip()[0].isdigit()
    # the Capo heading stays with the article that follows it
    art1 = next(c for c in chunks if "Oggetto" in c.text)
    assert "Capo I" in art1.text


def test_structure_chunker_pages(legal_doc: ParsedDocument) -> None:
    chunks = make_chunker("structure", {"max_chars": 1500}).chunk(legal_doc)
    last = chunks[-1]
    assert "Entrata in vigore" in last.text
    assert last.page_start == 2


def test_article_label() -> None:
    assert article_label("Art. 12-bis.") == "12bis"
    assert article_label("Articolo 1.") == "1"
    assert article_label("## Art. 3") == "3"
    assert article_label("1. Il presente decreto") is None
