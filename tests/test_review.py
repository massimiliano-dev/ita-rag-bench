from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from itaragbench.dataset import load_items, save_items
from itaragbench.review import review_loop

ROOT = Path(__file__).resolve().parents[1]


def _answers(seq: list[str]) -> Iterator[str]:
    yield from seq


def test_review_accept_reject_quit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    items = load_items(ROOT / "datasets/normativo/questions.jsonl")[:3]
    path = tmp_path / "q.jsonl"
    save_items(items, path)
    answers = _answers(["a", "looks right", "r", "wrong page", "q"])
    review_loop(
        path, ROOT / "configs/mvp.yaml", reviewer="tester", ask=lambda prompt: next(answers)
    )
    out = load_items(path)
    assert out[0].status == "validated" and out[0].validated_by == "tester"
    assert out[0].review_notes == "looks right" and out[0].validated_at
    assert out[1].status == "rejected" and out[1].review_notes == "wrong page"
    assert out[2].status == "draft" and out[2].validated_by is None
