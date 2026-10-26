"""Dense, BM25 and hybrid (reciprocal rank fusion) retrieval over an in-memory chunk list."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from itaragbench.embedding.base import FloatArray

Ranking = list[tuple[int, float]]  # (chunk index, score), best first


def dense_search(query_vecs: FloatArray, passage_vecs: FloatArray, k: int) -> list[Ranking]:
    """Cosine similarity (vectors are L2-normalised) with exact top-k."""
    scores = query_vecs @ passage_vecs.T
    out: list[Ranking] = []
    k = min(k, passage_vecs.shape[0])
    for row in scores:
        idx = np.argpartition(-row, k - 1)[:k]
        idx = idx[np.argsort(-row[idx], kind="stable")]
        out.append([(int(i), float(row[i])) for i in idx])
    return out


@dataclass
class BM25Index:
    """BM25 with Italian Snowball stemming and Italian stopwords (bm25s + PyStemmer)."""

    k1: float = 1.5
    b: float = 0.75
    _retriever: Any = None
    _stemmer: Any = None
    _n: int = 0

    def fit(self, texts: list[str]) -> None:
        import bm25s
        import Stemmer

        self._stemmer = Stemmer.Stemmer("italian")
        toks = bm25s.tokenize(texts, stopwords="it", stemmer=self._stemmer, show_progress=False)
        self._retriever = bm25s.BM25(k1=self.k1, b=self.b)
        self._retriever.index(toks, show_progress=False)
        self._n = len(texts)

    def search(self, queries: list[str], k: int) -> list[Ranking]:
        import bm25s

        if self._retriever is None:
            raise RuntimeError("BM25Index.fit() must be called first")
        q = bm25s.tokenize(queries, stopwords="it", stemmer=self._stemmer, show_progress=False)
        k = min(k, self._n)
        docs, scores = self._retriever.retrieve(q, k=k, show_progress=False)
        out: list[Ranking] = []
        for d_row, s_row in zip(docs, scores, strict=True):
            out.append([(int(d), float(s)) for d, s in zip(d_row, s_row, strict=True)])
        return out

    def describe(self) -> dict[str, Any]:
        return {
            "kind": "bm25s",
            "k1": self.k1,
            "b": self.b,
            "stemmer": "snowball-italian",
            "stopwords": "bm25s it",
        }


def rrf(rankings: list[Ranking], k: int, rrf_k: int = 60) -> Ranking:
    """Reciprocal rank fusion: score = sum 1 / (rrf_k + rank)."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (idx, _) in enumerate(ranking, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank)
    ordered = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))
    return ordered[:k]
