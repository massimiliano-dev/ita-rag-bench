"""Corpus manifest: the committed, auditable list of source documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

Length = Literal["short", "medium", "long"]
Structure = Literal["articoli-commi", "capitoli", "other"]
PdfQuality = Literal["native", "scanned"]


@dataclass
class Characteristics:
    length: Length
    has_tables: bool
    structure: Structure
    pdf_quality: PdfQuality


@dataclass
class Document:
    id: str
    title: str
    act: str
    url: str
    source: str
    license: str
    publication: str
    normattiva_urn: str
    retrieved: str | None
    sha256: str | None
    pdf_pages: int | None
    act_pages: list[int]
    characteristics: Characteristics
    notes: str = ""

    @property
    def filename(self) -> str:
        return f"{self.id}.pdf"

    @property
    def page_range(self) -> tuple[int, int]:
        """1-based inclusive physical page range of the act inside the PDF."""
        return (self.act_pages[0], self.act_pages[1])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Manifest:
    domain: str
    description: str
    user_agent: str
    allowed_hosts: list[str]
    min_interval_seconds: float
    max_documents: int
    max_bytes: int
    documents: list[Document] = field(default_factory=list)

    def get(self, doc_id: str) -> Document:
        for d in self.documents:
            if d.id == doc_id:
                return d
        raise KeyError(doc_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _doc_from_dict(raw: dict[str, Any]) -> Document:
    ch = raw["characteristics"]
    return Document(
        id=str(raw["id"]),
        title=str(raw["title"]),
        act=str(raw["act"]),
        url=str(raw["url"]),
        source=str(raw["source"]),
        license=str(raw["license"]),
        publication=str(raw["publication"]),
        normattiva_urn=str(raw.get("normattiva_urn", "")),
        retrieved=raw.get("retrieved"),
        sha256=raw.get("sha256"),
        pdf_pages=raw.get("pdf_pages"),
        act_pages=[int(p) for p in raw["act_pages"]],
        characteristics=Characteristics(
            length=ch["length"],
            has_tables=bool(ch["has_tables"]),
            structure=ch["structure"],
            pdf_quality=ch["pdf_quality"],
        ),
        notes=str(raw.get("notes", "")),
    )


def load_manifest(path: Path) -> Manifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    m = Manifest(
        domain=str(raw["domain"]),
        description=str(raw["description"]),
        user_agent=str(raw["user_agent"]),
        allowed_hosts=[str(h) for h in raw["allowed_hosts"]],
        min_interval_seconds=float(raw["min_interval_seconds"]),
        max_documents=int(raw["max_documents"]),
        max_bytes=int(raw["max_bytes"]),
        documents=[_doc_from_dict(d) for d in raw["documents"]],
    )
    if len(m.documents) > m.max_documents:
        raise ValueError(
            f"manifest lists {len(m.documents)} documents, max_documents is {m.max_documents}"
        )
    ids = [d.id for d in m.documents]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate document ids in manifest")
    return m


def save_manifest(m: Manifest, path: Path) -> None:
    text = yaml.safe_dump(m.to_dict(), sort_keys=False, allow_unicode=True, width=100)
    path.write_text(text, encoding="utf-8")
