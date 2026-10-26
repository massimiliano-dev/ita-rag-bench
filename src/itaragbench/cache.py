"""On-disk caches keyed by content hashes. JSON and NPY only (no pickle)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from itaragbench.config import ParserSpec
from itaragbench.embedding.base import Embedder, FloatArray
from itaragbench.hashing import sha256_json, sha256_text
from itaragbench.manifest import Document
from itaragbench.parsing.backends import backend_version
from itaragbench.parsing.base import ParsedDocument, ParsedPage
from itaragbench.parsing.sandbox import SandboxError, SandboxLimits, run_parser


def parsed_cache_path(cache_dir: Path, spec: ParserSpec, doc: Document) -> Path:
    key = sha256_json(
        {
            "sha256": doc.sha256,
            "pages": doc.act_pages,
            "parser": spec.name,
            "version": backend_version(spec.name),
            "options": spec.options,
        }
    )[:24]
    return cache_dir / "parsed" / spec.name / f"{doc.id}-{key}.json"


def load_or_parse(
    cache_dir: Path, pdf_dir: Path, spec: ParserSpec, doc: Document, log: Any = print
) -> ParsedDocument:
    path = parsed_cache_path(cache_dir, spec, doc)
    if path.exists():
        return ParsedDocument.from_json(json.loads(path.read_text(encoding="utf-8")))
    pdf = pdf_dir / doc.filename
    if not pdf.exists():
        raise FileNotFoundError(f"{pdf} missing: run `itarag corpus fetch` first")
    first, last = doc.page_range
    log(f"[parse] {spec.name:8s} {doc.id} pages {first}-{last}")
    t0 = time.perf_counter()
    warnings: list[str] = []
    try:
        payload = _run_with_retry(spec, pdf, first, last, log)
        pages = [ParsedPage(int(p["page_no"]), str(p["text"])) for p in payload["pages"]]
        version = str(payload["parser_version"])
        seconds = float(payload["seconds"])
        if payload.get("peak_rss_mb"):
            warnings.append(f"peak_rss_mb={payload['peak_rss_mb']}")
    except Exception as exc:  # parser failure is a *result*, not a crash
        log(f"[parse] FAILED {spec.name} {doc.id}: {exc}")
        pages = [ParsedPage(n, "") for n in range(first, last + 1)]
        version = backend_version(spec.name)
        seconds = time.perf_counter() - t0
        warnings.append(f"parser_failed: {str(exc)[:500]}")
    parsed = ParsedDocument(doc.id, spec.name, version, pages, seconds, warnings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(parsed.to_json(), ensure_ascii=False), encoding="utf-8")
    return parsed


def _run_with_retry(
    spec: ParserSpec, pdf: Path, first: int, last: int, log: Any, retries: int = 1
) -> dict[str, Any]:
    """Crashes (e.g. a native segfault) are retried once; timeouts/memory kills are not."""
    limits = SandboxLimits(spec.timeout_s, spec.max_mb)
    for attempt in range(retries + 1):
        try:
            return run_parser(spec.name, pdf, first, last, limits, spec.options)
        except SandboxError as exc:
            msg = str(exc)
            if attempt >= retries or "timeout" in msg or "memory limit" in msg:
                raise
            log(f"[parse] retrying {spec.name} {pdf.name} after crash: {msg[:120]}")
    raise AssertionError("unreachable")


def embed_cached(
    cache_dir: Path, embedder: Embedder, texts: list[str], kind: str
) -> tuple[FloatArray, float, bool]:
    """Return (vectors, seconds_spent_originally, cache_hit)."""
    key = sha256_json(
        {
            "model": embedder.describe(),
            "kind": kind,
            "texts": [sha256_text(t) for t in texts],
        }
    )[:32]
    base = cache_dir / "emb" / key
    npy, meta = base.with_suffix(".npy"), base.with_suffix(".json")
    if npy.exists() and meta.exists():
        vecs = np.load(npy, allow_pickle=False)
        info = json.loads(meta.read_text(encoding="utf-8"))
        return vecs.astype(np.float32), float(info["seconds"]), True
    t0 = time.perf_counter()
    embed = embedder.embed_queries if kind == "query" else embedder.embed_passages
    vecs = embed(texts)
    seconds = time.perf_counter() - t0
    base.parent.mkdir(parents=True, exist_ok=True)
    np.save(npy, vecs, allow_pickle=False)
    meta.write_text(json.dumps({"seconds": seconds, "n": len(texts), "kind": kind}))
    return vecs, seconds, False
