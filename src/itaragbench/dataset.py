"""Question-answer dataset (JSONL) with chunker-independent gold references."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

CATEGORIES = ("fattuale", "multi_hop", "tabellare", "temporale", "senza_risposta")
SPLITS = ("dev", "test")
STATUSES = ("draft", "validated", "rejected")

Category = Literal["fattuale", "multi_hop", "tabellare", "temporale", "senza_risposta"]


@dataclass
class Reference:
    doc_id: str
    article: str | None
    comma: str | None
    page: int
    evidence: list[str]
    match: str = "any"  # "any": one span suffices; "all": every span must be in the chunk


@dataclass
class Item:
    id: str
    split: str
    category: str
    question: str
    answer: str
    references: list[Reference]
    status: str = "draft"
    generated_by: str = "claude (assisted)"
    validated_by: str | None = None
    validated_at: str | None = None
    review_notes: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def answerable(self) -> bool:
        return self.category != "senza_risposta"

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def item_from_json(raw: dict[str, Any]) -> Item:
    refs = [
        Reference(
            doc_id=str(r["doc_id"]),
            article=None if r.get("article") is None else str(r["article"]),
            comma=None if r.get("comma") is None else str(r["comma"]),
            page=int(r["page"]),
            evidence=[str(e) for e in r["evidence"]],
            match=str(r.get("match", "any")),
        )
        for r in raw.get("references", [])
    ]
    return Item(
        id=str(raw["id"]),
        split=str(raw["split"]),
        category=str(raw["category"]),
        question=str(raw["question"]),
        answer=str(raw["answer"]),
        references=refs,
        status=str(raw.get("status", "draft")),
        generated_by=str(raw.get("generated_by", "claude (assisted)")),
        validated_by=raw.get("validated_by"),
        validated_at=raw.get("validated_at"),
        review_notes=raw.get("review_notes"),
        tags=[str(t) for t in raw.get("tags", [])],
    )


def load_items(path: Path) -> list[Item]:
    items: list[Item] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(item_from_json(json.loads(line)))
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"{path}:{n}: invalid item: {exc}") from exc
    return items


def save_items(items: list[Item], path: Path) -> None:
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it.to_json(), ensure_ascii=False) + "\n")
    tmp.replace(path)


def schema_errors(items: list[Item], known_docs: set[str]) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    for it in items:
        where = it.id
        if it.id in seen:
            errs.append(f"{where}: duplicate id")
        seen.add(it.id)
        if it.split not in SPLITS:
            errs.append(f"{where}: bad split {it.split!r}")
        if it.category not in CATEGORIES:
            errs.append(f"{where}: bad category {it.category!r}")
        if it.status not in STATUSES:
            errs.append(f"{where}: bad status {it.status!r}")
        if not it.question.strip():
            errs.append(f"{where}: empty question")
        if it.status == "draft" and it.validated_by is not None:
            errs.append(f"{where}: draft items must have validated_by = null")
        if it.category == "senza_risposta":
            if it.references:
                errs.append(f"{where}: senza_risposta items must not have references")
            continue
        if not it.references:
            errs.append(f"{where}: answerable item without references")
        if it.category == "multi_hop" and len(it.references) < 2:
            errs.append(f"{where}: multi_hop needs at least two references")
        for r in it.references:
            if r.doc_id not in known_docs:
                errs.append(f"{where}: unknown doc_id {r.doc_id!r}")
            if r.match not in {"any", "all"}:
                errs.append(f"{where}: match must be 'any' or 'all'")
            if not r.evidence or max(len(e.strip()) for e in r.evidence) < 15:
                errs.append(f"{where}: at least one evidence span must be >= 15 chars")
            if any(len(e.strip()) < 2 for e in r.evidence):
                errs.append(f"{where}: empty evidence span")
            if r.match == "any" and any(len(e.strip()) < 15 for e in r.evidence):
                errs.append(f"{where}: with match='any' every span must be >= 15 chars")
    return errs
