from __future__ import annotations

from collections import Counter
from pathlib import Path

from itaragbench.dataset import CATEGORIES, Item, Reference, load_items, schema_errors
from itaragbench.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_committed_dataset_schema() -> None:
    items = load_items(ROOT / "datasets/normativo/questions.jsonl")
    known = {d.id for d in load_manifest(ROOT / "corpus/normativo/manifest.yaml").documents}
    assert schema_errors(items, known) == []
    assert len(items) == 150
    splits = Counter(it.split for it in items)
    assert splits["dev"] == 50
    cats = Counter(it.category for it in items)
    assert set(cats) <= set(CATEGORIES)
    assert 0.08 <= cats["senza_risposta"] / len(items) <= 0.12
    for it in items:
        assert it.generated_by == "claude (assisted)"
        if it.status == "draft":
            assert it.validated_by is None


def test_schema_errors_catch_problems() -> None:
    bad = Item(
        id="x",
        split="train",
        category="fattuale",
        question="q?",
        answer="a",
        references=[Reference("nope", "1", None, 1, ["short"])],
    )
    errs = schema_errors([bad], {"doc"})
    assert any("bad split" in e for e in errs)
    assert any("unknown doc_id" in e for e in errs)
    assert any("15 chars" in e for e in errs)
    unans = Item(
        id="y",
        split="dev",
        category="senza_risposta",
        question="q?",
        answer="-",
        references=[Reference("doc", None, None, 1, ["x" * 20])],
    )
    assert any("must not have references" in e for e in schema_errors([unans], {"doc"}))
