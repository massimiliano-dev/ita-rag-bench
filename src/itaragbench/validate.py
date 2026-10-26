"""Dataset validation: schema + evidence spans present in the official text."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from itaragbench.cache import parsed_cache_path
from itaragbench.config import BenchConfig
from itaragbench.dataset import load_items, schema_errors
from itaragbench.manifest import load_manifest
from itaragbench.matching import match_evidence
from itaragbench.parsing.base import ParsedDocument


def cached_parses(cfg: BenchConfig, doc_id: str) -> dict[str, ParsedDocument]:
    m = load_manifest(cfg.manifest)
    doc = m.get(doc_id)
    out: dict[str, ParsedDocument] = {}
    for spec in cfg.parsers:
        p: Path = parsed_cache_path(cfg.cache_dir, spec, doc)
        if p.exists():
            out[spec.name] = ParsedDocument.from_json(json.loads(p.read_text(encoding="utf-8")))
    return out


def page_window(pd: ParsedDocument, page: int, radius: int = 1) -> str:
    return "\n".join(p.text for p in pd.pages if abs(p.page_no - page) <= radius)


def evidence_report(cfg: BenchConfig, doc_id: str, page: int, evidence: str) -> dict[str, str]:
    """For each cached parser: 'exact' | 'fuzzy' | 'doc' (elsewhere in the doc) | 'missing'."""
    out: dict[str, str] = {}
    for name, pd in cached_parses(cfg, doc_id).items():
        r = match_evidence(evidence, page_window(pd, page))
        if r.matched:
            out[name] = r.method
        else:
            out[name] = "doc" if match_evidence(evidence, pd.text).matched else "missing"
    return out


def validate_dataset(
    cfg: BenchConfig, *, check_evidence: bool = True, log: Callable[[str], None] = print
) -> list[str]:
    items = load_items(cfg.dataset)
    known = {d.id for d in load_manifest(cfg.manifest).documents}
    errors = schema_errors(items, known)
    if not check_evidence:
        return errors
    for it in items:
        for r in it.references:
            for ev in r.evidence:
                rep = evidence_report(cfg, r.doc_id, r.page, ev)
                if not rep:
                    errors.append(f"{it.id}: no cached parse for {r.doc_id} (run `itarag parse`)")
                    continue
                if not any(v in {"exact", "fuzzy"} for v in rep.values()):
                    where = "elsewhere in doc" if "doc" in rep.values() else "not found"
                    errors.append(f"{it.id}: evidence not on page {r.page} ({where}): {ev[:60]!r}")
    log(f"checked {len(items)} items")
    return errors
