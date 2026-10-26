"""End-to-end on a generated PDF: sandboxed parse -> chunk -> fake embed -> BM25/RRF -> metrics."""

from __future__ import annotations

from pathlib import Path

import pytest

from itaragbench.chunking import make_chunker
from itaragbench.embedding.fake import FakeEmbedder
from itaragbench.matching import match_evidence
from itaragbench.metrics import score_question
from itaragbench.parsing.base import ParsedDocument, ParsedPage
from itaragbench.parsing.sandbox import SandboxError, SandboxLimits, run_parser
from itaragbench.retrieval.core import BM25Index, dense_search, rrf


def _parse(pdf: Path) -> ParsedDocument:
    payload = run_parser("pypdf", pdf, 1, 2, SandboxLimits(timeout_s=60, max_mb=1024))
    pages = [ParsedPage(int(p["page_no"]), str(p["text"])) for p in payload["pages"]]
    return ParsedDocument("tiny", "pypdf", payload["parser_version"], pages, payload["seconds"])


def test_sandboxed_parse_and_page_break_evidence(tiny_pdf: Path) -> None:
    doc = _parse(tiny_pdf)
    assert len(doc.pages) == 2 and "Art. 2." in doc.pages[1].text
    span = (
        "dieci anni dalla data di deposito presso l'archivio, salvo diversa disposizione "
        "del regolamento comunale"
    )
    # the comma straddles the page break and the running header sits in between
    assert match_evidence(span, doc.text).matched
    chunks = make_chunker("structure", {"max_chars": 1500}).chunk(doc)
    art1 = next(c for c in chunks if "Oggetto" in c.text)
    assert art1.page_start == 1 and art1.page_end == 2
    assert match_evidence(span, art1.text).matched


def test_sandbox_timeout(tiny_pdf: Path) -> None:
    with pytest.raises(SandboxError, match="timeout"):
        run_parser("pypdf", tiny_pdf, 1, 2, SandboxLimits(timeout_s=0.0, max_mb=1024))


def test_sandbox_reports_worker_failure(tmp_path: Path) -> None:
    bogus = tmp_path / "not.pdf"
    bogus.write_bytes(b"%PDF-1.4 garbage")
    with pytest.raises(SandboxError):
        run_parser("pypdf", bogus, 1, 1, SandboxLimits(timeout_s=60, max_mb=1024))


def test_retrieval_end_to_end(tiny_pdf: Path) -> None:
    doc = _parse(tiny_pdf)
    chunks = make_chunker("fixed", {"size": 30, "overlap": 5}).chunk(doc)
    texts = [c.text for c in chunks]
    q = ["Qual e' la sanzione per chi distrugge un documento di prova?"]
    emb = FakeEmbedder(dim=128)
    dense = dense_search(emb.embed_queries(q), emb.embed_passages(texts), k=5)
    bm = BM25Index()
    bm.fit(texts)
    sparse = bm.search(q, k=5)
    fused = rrf([dense[0], sparse[0]], k=5)
    evidence = "amministrativa pecuniaria da 500 a 5.000 euro"
    cov = [{0} if match_evidence(evidence, chunks[i].text).matched else set() for i, _ in fused]
    s = score_question("q", 1, cov, 10)
    assert s.first_rank is not None and s.first_rank <= 2


def test_sandbox_survives_chatty_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: >64 KB of warnings on stderr must not deadlock the worker."""
    from itaragbench.parsing import sandbox

    script = tmp_path / "chatty.py"
    script.write_text(
        "import sys, json\n"
        "sys.stderr.write('w' * 300_000)\n"
        "json.dump({'parser_version': 'x', 'seconds': 0, 'pages': []}, open(sys.argv[-1], 'w'))\n"
    )
    real_popen = sandbox.subprocess.Popen

    def fake_popen(cmd: list[str], **kw: object) -> object:
        out = cmd[cmd.index("--max-mb") - 1]
        return real_popen([cmd[0], str(script), out], **kw)  # type: ignore[call-overload]

    monkeypatch.setattr(sandbox.subprocess, "Popen", fake_popen)
    res = sandbox.run_parser("pypdf", tmp_path / "x.pdf", 1, 1, SandboxLimits(timeout_s=20))
    assert res["pages"] == []


def test_evaluator_memo_is_per_parser() -> None:
    """Regression: identical chunk positions from two parsers must not share relevance."""
    from itaragbench.chunking.base import Chunk
    from itaragbench.dataset import Item, Reference
    from itaragbench.manifest import Characteristics, Document
    from itaragbench.runner import Evaluator

    ref = Reference("d", "1", None, 1, ["la conservazione dei documenti di prova"])
    item = Item("q", "dev", "fattuale", "?", "!", [ref])
    doc = Document(
        "d",
        "t",
        "a",
        "https://x",
        "s",
        "l",
        "p",
        "",
        None,
        None,
        None,
        [1, 1],
        Characteristics("short", False, "other", "native"),
    )
    ev = Evaluator([item], {"d": doc}, 10)
    good = Chunk(
        "d::pymupdf::fixed::00000", "d", "disciplina la conservazione dei documenti di prova", 1, 1
    )
    bad = Chunk("d::pypdf::fixed::00000", "d", "/99/41 /105/108 /100/105", 1, 1)
    assert ev.covered(item, bad) == frozenset()
    assert ev.covered(item, good) == frozenset({0})
