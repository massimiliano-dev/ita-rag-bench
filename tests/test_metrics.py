from __future__ import annotations

import math

import pytest

from itaragbench.metrics import aggregate, score_question


def test_single_reference_rank3() -> None:
    s = score_question("q", 1, [set(), set(), {0}, {0}])
    assert s.first_rank == 3
    assert s.recall == {1: 0.0, 5: 1.0, 10: 1.0}
    assert s.rr == pytest.approx(1 / 3)
    assert s.ndcg == pytest.approx(1 / math.log2(4))


def test_duplicates_do_not_inflate() -> None:
    s = score_question("q", 1, [{0}, {0}, {0}])
    assert s.ndcg == pytest.approx(1.0)


def test_multi_hop_partial() -> None:
    s = score_question("q", 2, [{0}, set(), set(), set(), set(), {1}])
    assert s.recall[1] == 0.5 and s.recall[5] == 0.5 and s.recall[10] == 1.0
    assert 0 < s.ndcg < 1


def test_no_hit() -> None:
    s = score_question("q", 1, [set()] * 10)
    assert s.first_rank is None and s.rr == 0.0 and s.ndcg == 0.0


def test_one_chunk_covering_two_refs_is_capped() -> None:
    assert score_question("q", 2, [{0, 1}]).ndcg == 1.0


def test_aggregate() -> None:
    a = aggregate([score_question("a", 1, [{0}]), score_question("b", 1, [set()])])
    assert a["recall@1"] == 0.5 and a["mrr@10"] == 0.5 and a["n"] == 2
