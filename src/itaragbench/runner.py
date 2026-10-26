"""Grid runner: parsers x chunkers x embeddings x retrievers -> results/<run-id>/."""

from __future__ import annotations

import datetime as dt
import json
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from itaragbench.cache import embed_cached, load_or_parse
from itaragbench.chunking import Chunk, make_chunker
from itaragbench.config import BenchConfig
from itaragbench.dataset import CATEGORIES, Item, load_items
from itaragbench.embedding.base import Embedder, make_embedder
from itaragbench.environment import environment
from itaragbench.hashing import sha256_file, sha256_json, sha256_text
from itaragbench.manifest import Document, load_manifest
from itaragbench.matching import TOKEN_OVERLAP_THRESHOLD, match_evidence
from itaragbench.metrics import QuestionScore, aggregate, score_question
from itaragbench.parsing.base import ParsedDocument
from itaragbench.retrieval.core import BM25Index, Ranking, dense_search, rrf

Log = Callable[[str], None]
NEAR_EMPTY_CHARS = 200  # a page with less extracted text is counted as (almost) empty
CHARACTERISTICS = ("length", "has_tables", "structure", "pdf_quality")


@dataclass
class Evaluator:
    items: list[Item]
    docs: dict[str, Document]
    k: int

    def __post_init__(self) -> None:
        self._memo: dict[tuple[str, str, str], frozenset[int]] = {}

    def covered(self, item: Item, chunk: Chunk) -> frozenset[int]:
        # chunk ids embed parser and chunker; the text hash makes the memo safe regardless
        key = (item.id, chunk.chunk_id, sha256_text(chunk.text))
        hit = self._memo.get(key)
        if hit is not None:
            return hit
        out = set()
        for ri, ref in enumerate(item.references):
            if ref.doc_id != chunk.doc_id:
                continue
            hits = (match_evidence(ev, chunk.text).matched for ev in ref.evidence)
            if all(hits) if ref.match == "all" else any(hits):
                out.add(ri)
        res = frozenset(out)
        self._memo[key] = res
        return res

    def coverage(self, chunks: list[Chunk]) -> dict[str, Any]:
        """Upper bound independent of the retriever: share of gold references that are fully
        contained in at least one chunk. A reference split across chunk boundaries (or lost by
        the parser) can never be retrieved, whatever the embedding."""
        by_doc: dict[str, list[Chunk]] = defaultdict(list)
        for c in chunks:
            by_doc[c.doc_id].append(c)
        hit: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for item in self.items:
            for ri, ref in enumerate(item.references):
                ok = any(ri in self.covered(item, c) for c in by_doc.get(ref.doc_id, []))
                for key in ("overall", item.category):
                    hit[key][0] += int(ok)
                    hit[key][1] += 1
        return {
            k: {"covered": v[0], "references": v[1], "share": v[0] / v[1]} for k, v in hit.items()
        }

    def evaluate(
        self, rankings: list[Ranking], chunks: list[Chunk]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        scores: list[tuple[Item, QuestionScore]] = []
        rows: list[dict[str, Any]] = []
        for item, ranking in zip(self.items, rankings, strict=True):
            if not item.answerable:
                continue
            top = [chunks[i] for i, _ in ranking[: self.k]]
            cov = [set(self.covered(item, c)) for c in top]
            qs = score_question(item.id, len(item.references), cov, self.k)
            scores.append((item, qs))
            rows.append(
                {
                    "id": item.id,
                    "split": item.split,
                    "category": item.category,
                    "first_rank": qs.first_rank,
                    "recall@1": qs.recall[1],
                    "recall@5": qs.recall[5],
                    "recall@10": qs.recall[10],
                    "ndcg@10": round(qs.ndcg, 4),
                    "top_chunks": [c.chunk_id for c in top[:3]],
                }
            )
        overall = aggregate([s for _, s in scores])
        per_cat = {
            cat: aggregate([s for it, s in scores if it.category == cat])
            for cat in CATEGORIES
            if cat != "senza_risposta"
        }
        per_char: dict[str, dict[str, dict[str, float]]] = {}
        for ch in CHARACTERISTICS:
            groups: dict[str, list[QuestionScore]] = defaultdict(list)
            for it, s in scores:
                d = self.docs[it.references[0].doc_id]
                groups[str(getattr(d.characteristics, ch))].append(s)
            per_char[ch] = {v: aggregate(g) for v, g in sorted(groups.items())}
        groups_doc: dict[str, list[QuestionScore]] = defaultdict(list)
        for it, s in scores:
            groups_doc[it.references[0].doc_id].append(s)
        per_doc = {d: aggregate(g) for d, g in sorted(groups_doc.items())}
        return (
            {
                "overall": overall,
                "per_category": per_cat,
                "per_characteristic": per_char,
                "per_document": per_doc,
            },
            rows,
        )


def _chunk_stats(chunks: list[Chunk], doc_ids: list[str]) -> dict[str, float]:
    per_doc: dict[str, int] = defaultdict(int)
    for c in chunks:
        per_doc[c.doc_id] += 1
    lens = [len(c.text) for c in chunks]
    return {
        "n_chunks": float(len(chunks)),
        "chunks_per_doc": mean(per_doc.get(d, 0) for d in doc_ids),
        "mean_chunk_chars": mean(lens) if lens else 0.0,
        "max_chunk_chars": float(max(lens) if lens else 0),
    }


def _parse_stats(parsed: dict[str, ParsedDocument]) -> dict[str, Any]:
    seconds = sum(p.seconds for p in parsed.values())
    pages = sum(len(p.pages) for p in parsed.values())
    empty = sum(
        1 for p in parsed.values() for pg in p.pages if len(pg.text.strip()) < NEAR_EMPTY_CHARS
    )
    failed = [p.doc_id for p in parsed.values() if any("parser_failed" in w for w in p.warnings)]
    return {
        "seconds": seconds,
        "pages": pages,
        "seconds_per_page": seconds / pages if pages else 0.0,
        "near_empty_pages": empty,
        "failed_docs": failed,
        "chars": sum(len(p.text) for p in parsed.values()),
        "versions": sorted({p.parser_version for p in parsed.values()}),
    }


def verify_corpus(docs: list[Document], pdf_dir: Path) -> None:
    for d in docs:
        pdf = pdf_dir / d.filename
        if not pdf.exists():
            raise FileNotFoundError(f"{pdf} missing: run `itarag corpus fetch`")
        if sha256_file(pdf) != d.sha256:
            raise ValueError(f"{d.id}: sha256 mismatch, refusing to run on an unverified file")


def run_benchmark(
    cfg: BenchConfig,
    *,
    split: str = "all",
    run_id: str | None = None,
    only_parsers: list[str] | None = None,
    only_embeddings: list[str] | None = None,
    log: Log = print,
) -> Path:
    manifest = load_manifest(cfg.manifest)
    docs = manifest.documents
    verify_corpus(docs, cfg.pdf_dir)
    doc_map = {d.id: d for d in docs}
    items_all = load_items(cfg.dataset)
    items = [it for it in items_all if split == "all" or it.split == split]
    if not items:
        raise ValueError("no questions selected")
    queries = [it.question for it in items]
    evaluator = Evaluator(items, doc_map, cfg.k)

    run_id = run_id or f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{cfg.name}-{split}"
    out_dir = cfg.results_dir / run_id
    (out_dir / "per_question").mkdir(parents=True, exist_ok=True)

    parsers = [p for p in cfg.parsers if only_parsers is None or p.name in only_parsers]
    emb_specs = {
        k: v for k, v in cfg.embeddings.items() if only_embeddings is None or k in only_embeddings
    }
    embedders: dict[str, Embedder] = {k: make_embedder(v) for k, v in emb_specs.items()}

    rows: list[dict[str, Any]] = []
    parse_summary: dict[str, Any] = {}
    t_run = time.perf_counter()
    for pspec in parsers:
        parsed = {d.id: load_or_parse(cfg.cache_dir, cfg.pdf_dir, pspec, d, log) for d in docs}
        pstats = _parse_stats(parsed)
        parse_summary[pspec.name] = pstats
        log(
            f"[parse] {pspec.name}: {pstats['pages']} pages, {pstats['seconds']:.1f}s, "
            f"near-empty pages {pstats['near_empty_pages']}, failed {pstats['failed_docs']}"
        )
        for cname, cparams in cfg.chunkers.items():
            chunker = make_chunker(cname, cparams)
            t0 = time.perf_counter()
            chunks = [c for d in docs for c in chunker.chunk(parsed[d.id])]
            chunk_s = time.perf_counter() - t0
            cstats = _chunk_stats(chunks, [d.id for d in docs])
            coverage = evaluator.coverage(chunks)
            texts = [c.text for c in chunks]
            log(f"[chunk] {pspec.name}/{cname}: {len(chunks)} chunks")
            base = {
                "parser": pspec.name,
                "chunker": cname,
                "chunker_params": chunker.params(),
                "chunk_stats": cstats,
                "evidence_coverage": coverage,
                "parse_seconds": pstats["seconds"],
                "chunk_seconds": chunk_s,
            }
            bm25_rank: list[Ranking] | None = None
            if "bm25" in cfg.retrievers or "hybrid" in cfg.retrievers:
                bm = BM25Index()
                t0 = time.perf_counter()
                bm.fit(texts)
                bm_index_s = time.perf_counter() - t0
                t0 = time.perf_counter()
                bm25_rank = bm.search(queries, cfg.candidates)
                bm_query_ms = (time.perf_counter() - t0) * 1000 / len(queries)
                if "bm25" in cfg.retrievers:
                    res, qrows = evaluator.evaluate(bm25_rank, chunks)
                    rows.append(
                        {
                            **base,
                            "embedding": None,
                            "retriever": "bm25",
                            **res,
                            "timings": {"index_seconds": bm_index_s, "query_ms": bm_query_ms},
                            "retriever_params": bm.describe(),
                        }
                    )
                    _write_rows(out_dir, pspec.name, cname, None, "bm25", qrows)
            for ename, embedder in embedders.items():
                pvecs, p_s, p_hit = embed_cached(cfg.cache_dir, embedder, texts, "passage")
                # queries are always re-embedded (after a warm-up call) so latency is measured
                embedder.embed_queries(queries[:1])
                t0 = time.perf_counter()
                qvecs = embedder.embed_queries(queries)
                t1 = time.perf_counter()
                dense_rank = dense_search(qvecs, pvecs, cfg.candidates)
                search_s = time.perf_counter() - t1
                q_embed_s = t1 - t0
                dense_ms = (q_embed_s + search_s) * 1000 / len(queries)
                log(
                    f"[embed] {pspec.name}/{cname}/{ename}: index {p_s:.1f}s"
                    f"{' (cached)' if p_hit else ''}"
                )
                emb_desc = embedder.describe()
                if "dense" in cfg.retrievers:
                    res, qrows = evaluator.evaluate(dense_rank, chunks)
                    rows.append(
                        {
                            **base,
                            "embedding": ename,
                            "embedding_model": emb_desc,
                            "retriever": "dense",
                            **res,
                            "timings": {"index_seconds": p_s, "query_ms": dense_ms},
                        }
                    )
                    _write_rows(out_dir, pspec.name, cname, ename, "dense", qrows)
                if "hybrid" in cfg.retrievers and bm25_rank is not None:
                    t0 = time.perf_counter()
                    hyb = [
                        rrf([d, b], cfg.candidates, cfg.rrf_k)
                        for d, b in zip(dense_rank, bm25_rank, strict=True)
                    ]
                    fuse_ms = (time.perf_counter() - t0) * 1000 / len(queries)
                    res, qrows = evaluator.evaluate(hyb, chunks)
                    rows.append(
                        {
                            **base,
                            "embedding": ename,
                            "embedding_model": emb_desc,
                            "retriever": "hybrid",
                            **res,
                            "timings": {
                                "index_seconds": p_s + bm_index_s,
                                "query_ms": dense_ms + bm_query_ms + fuse_ms,
                            },
                            "retriever_params": {"rrf_k": cfg.rrf_k, "candidates": cfg.candidates},
                        }
                    )
                    _write_rows(out_dir, pspec.name, cname, ename, "hybrid", qrows)
    unanswerable = [it for it in items if not it.answerable]
    run_meta = {
        "run_id": run_id,
        "created": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "config_name": cfg.name,
        "config": cfg.raw,
        "config_sha256": sha256_json(cfg.raw),
        "split": split,
        "dataset": {
            "path": str(cfg.dataset.name),
            "sha256": sha256_file(cfg.dataset),
            "n_items": len(items),
            "n_answerable": len(items) - len(unanswerable),
            "status_counts": _counts([it.status for it in items]),
            "category_counts": _counts([it.category for it in items]),
        },
        "senza_risposta": {
            "count": len(unanswerable),
            "note": "Excluded from retrieval metrics. Abstention will be measured once "
            "generation is added; retrieval always returns k chunks.",
        },
        "corpus": {
            "manifest_sha256": sha256_file(cfg.manifest),
            "documents_sha256": sha256_json([[d.id, d.sha256, d.act_pages] for d in docs]),
            "n_documents": len(docs),
        },
        "matching": {"token_overlap_threshold": TOKEN_OVERLAP_THRESHOLD},
        "parsers": parse_summary,
        "environment": environment(),
        "wall_seconds": time.perf_counter() - t_run,
    }
    (out_dir / "run.json").write_text(json.dumps(run_meta, indent=2, ensure_ascii=False))
    (out_dir / "summary.json").write_text(
        json.dumps({"run_id": run_id, "rows": rows}, indent=1, ensure_ascii=False)
    )
    log(f"[done] results in {out_dir}")
    return out_dir


def _counts(values: list[str]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for v in values:
        out[v] += 1
    return dict(sorted(out.items()))


def _write_rows(
    out_dir: Path,
    parser: str,
    chunker: str,
    emb: str | None,
    retr: str,
    rows: list[dict[str, Any]],
) -> None:
    name = f"{parser}__{chunker}__{emb or 'none'}__{retr}.jsonl"
    with (out_dir / "per_question" / name).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
