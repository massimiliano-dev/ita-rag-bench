"""Retrieval metrics with evidence-level (chunker-independent) relevance.

For a question with gold references R and a ranked list of chunks:
* recall@k  = |references covered by the top-k chunks| / |R|
* MRR@10    = 1 / rank of the first chunk covering any reference (0 if none in top 10)
* nDCG@10   = DCG where a chunk gains 1 only if it covers a reference not covered by a
              higher-ranked chunk; IDCG assumes the |R| references at the top ranks.
Duplicated/overlapping chunks therefore cannot inflate scores, and the ideal does not
depend on how many chunks a chunker produced.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

KS = (1, 5, 10)


@dataclass
class QuestionScore:
    qid: str
    first_rank: int | None
    recall: dict[int, float]
    rr: float
    ndcg: float


def score_question(
    qid: str, n_refs: int, covered: Sequence[set[int]], k_max: int = 10
) -> QuestionScore:
    """``covered[i]`` is the set of reference indices covered by the chunk at rank i+1."""
    if n_refs <= 0:
        raise ValueError("score_question needs at least one reference")
    seen: set[int] = set()
    first_rank: int | None = None
    dcg = 0.0
    cum: list[int] = []
    for rank, refs in enumerate(covered[:k_max], start=1):
        if refs and first_rank is None:
            first_rank = rank
        new = refs - seen
        if new:
            dcg += len(new) / math.log2(rank + 1)
            seen |= new
        cum.append(len(seen))
    recall = {k: (cum[min(k, len(cum)) - 1] / n_refs if cum else 0.0) for k in KS}
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(n_refs, k_max) + 1))
    rr = 1.0 / first_rank if first_rank is not None else 0.0
    # a single chunk covering several references can beat the per-rank ideal: cap at 1
    return QuestionScore(qid, first_rank, recall, rr, min(1.0, dcg / idcg))


def aggregate(scores: Sequence[QuestionScore]) -> dict[str, float]:
    if not scores:
        return {"n": 0}
    out: dict[str, float] = {"n": float(len(scores))}
    for k in KS:
        out[f"recall@{k}"] = mean(s.recall[k] for s in scores)
    out["mrr@10"] = mean(s.rr for s in scores)
    out["ndcg@10"] = mean(s.ndcg for s in scores)
    return out
