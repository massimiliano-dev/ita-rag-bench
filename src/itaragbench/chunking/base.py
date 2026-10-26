"""Chunk model and chunker factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from itaragbench.parsing.base import ParsedDocument


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    page_start: int
    page_end: int
    heading: str = ""


class Chunker(Protocol):
    name: str

    def chunk(self, doc: ParsedDocument) -> list[Chunk]: ...

    def params(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    prefix: str = ""


def spans_to_chunks(doc: ParsedDocument, spans: list[Span], chunker: str) -> list[Chunk]:
    text = doc.text
    chunks: list[Chunk] = []
    for sp in spans:
        body = text[sp.start : sp.end].strip()
        if not body:
            continue
        full = f"{sp.prefix}\n{body}" if sp.prefix else body
        chunks.append(
            Chunk(
                chunk_id=f"{doc.doc_id}::{doc.parser}::{chunker}::{len(chunks):05d}",
                doc_id=doc.doc_id,
                text=full,
                page_start=doc.page_at(sp.start),
                page_end=doc.page_at(max(sp.start, sp.end - 1)),
                heading=sp.prefix,
            )
        )
    return chunks


def make_chunker(name: str, params: dict[str, Any]) -> Chunker:
    from itaragbench.chunking.fixed import FixedTokenChunker
    from itaragbench.chunking.recursive import RecursiveChunker
    from itaragbench.chunking.structure import LegalStructureChunker

    if name == "fixed":
        return FixedTokenChunker(**params)
    if name == "recursive":
        return RecursiveChunker(**params)
    if name == "structure":
        return LegalStructureChunker(**params)
    raise ValueError(f"unknown chunker {name!r}")
