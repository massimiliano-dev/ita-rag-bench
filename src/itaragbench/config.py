"""Benchmark configuration (YAML)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ParserSpec:
    name: str
    timeout_s: float = 900.0
    max_mb: int = 4096
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchConfig:
    name: str
    domain: str
    manifest: Path
    pdf_dir: Path
    dataset: Path
    cache_dir: Path
    results_dir: Path
    k: int
    candidates: int
    rrf_k: int
    parsers: list[ParserSpec]
    chunkers: dict[str, dict[str, Any]]
    embeddings: dict[str, dict[str, Any]]
    retrievers: list[str]
    raw: dict[str, Any]


def load_config(path: Path, root: Path | None = None) -> BenchConfig:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    base = root or Path.cwd()

    def p(key: str) -> Path:
        v = Path(str(raw[key]))
        return v if v.is_absolute() else base / v

    parsers = [
        ParserSpec(
            name=name,
            timeout_s=float(spec.get("timeout_s", 900)),
            max_mb=int(spec.get("max_mb", 4096)),
            options=dict(spec.get("options", {})),
        )
        for name, spec in (raw.get("parsers") or {}).items()
    ]
    retrievers = [str(r) for r in raw.get("retrievers", ["dense", "bm25", "hybrid"])]
    for r in retrievers:
        if r not in {"dense", "bm25", "hybrid"}:
            raise ValueError(f"unknown retriever {r!r}")
    return BenchConfig(
        name=str(raw["name"]),
        domain=str(raw["domain"]),
        manifest=p("manifest"),
        pdf_dir=p("pdf_dir"),
        dataset=p("dataset"),
        cache_dir=p("cache_dir"),
        results_dir=p("results_dir"),
        k=int(raw.get("k", 10)),
        candidates=int(raw.get("candidates", 100)),
        rrf_k=int(raw.get("rrf_k", 60)),
        parsers=parsers,
        chunkers={str(k): dict(v or {}) for k, v in (raw.get("chunkers") or {}).items()},
        embeddings={str(k): dict(v) for k, v in (raw.get("embeddings") or {}).items()},
        retrievers=retrievers,
        raw=raw,
    )
