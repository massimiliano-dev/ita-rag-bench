from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from itaragbench.fetch import FetchError, RateLimiter, check_url, fetch_corpus
from itaragbench.manifest import Characteristics, Document, Manifest

HOST = "www.gazzettaufficiale.it"


def _manifest(sha: str | None, n: int = 1) -> Manifest:
    docs = [
        Document(
            id=f"doc-{i}",
            title="t",
            act="a",
            url=f"https://{HOST}/eli/gu/x/{i}/sg/pdf",
            source="s",
            license="l",
            publication="p",
            normattiva_urn="",
            retrieved=None,
            sha256=sha,
            pdf_pages=None,
            act_pages=[1, 1],
            characteristics=Characteristics("short", False, "other", "native"),
        )
        for i in range(n)
    ]
    return Manifest("normativo", "d", "ua", [HOST], 2.0, 20, 1000, docs)


class FakeLimiter(RateLimiter):
    def __init__(self) -> None:
        super().__init__(2.0, clock=lambda: 0.0, sleep=lambda s: None)


def test_check_url_rules() -> None:
    check_url(f"https://{HOST}/a.pdf", [HOST])
    with pytest.raises(FetchError):
        check_url(f"http://{HOST}/a.pdf", [HOST])
    with pytest.raises(FetchError):
        check_url("https://evil.example.com/a.pdf", [HOST])


def test_rate_limiter_waits_at_least_two_seconds() -> None:
    now = [0.0]
    slept: list[float] = []

    def sleep(s: float) -> None:
        slept.append(s)
        now[0] += s

    rl = RateLimiter(2.0, clock=lambda: now[0], sleep=sleep)
    rl.wait()
    now[0] += 0.5
    rl.wait()
    assert slept == [pytest.approx(1.5)]
    with pytest.raises(ValueError):
        RateLimiter(1.0)


def test_fetch_verifies_sha256(tmp_path: Path) -> None:
    data = b"%PDF-1.4 fake"
    good = hashlib.sha256(data).hexdigest()
    res = fetch_corpus(
        _manifest(good),
        tmp_path,
        downloader=lambda u, m: data,
        limiter=FakeLimiter(),
        log=lambda s: None,
    )
    assert res[0].status == "downloaded"
    # second call is served from the verified cache, no download
    res = fetch_corpus(
        _manifest(good),
        tmp_path,
        downloader=lambda u, m: b"never",
        limiter=FakeLimiter(),
        log=lambda s: None,
    )
    assert res[0].status == "cached"


def test_fetch_rejects_hash_mismatch(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="sha256 mismatch"):
        fetch_corpus(
            _manifest("0" * 64),
            tmp_path,
            downloader=lambda u, m: b"%PDF-x",
            limiter=FakeLimiter(),
            log=lambda s: None,
        )
    assert not (tmp_path / "doc-0.pdf").exists()


def test_fetch_requires_hash_unless_bootstrap(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="no sha256"):
        fetch_corpus(
            _manifest(None),
            tmp_path,
            downloader=lambda u, m: b"%PDF-x",
            limiter=FakeLimiter(),
            log=lambda s: None,
        )
    m = _manifest(None)
    fetch_corpus(
        m,
        tmp_path,
        downloader=lambda u, m: b"%PDF-x",
        bootstrap=True,
        limiter=FakeLimiter(),
        log=lambda s: None,
    )
    assert m.documents[0].sha256 == hashlib.sha256(b"%PDF-x").hexdigest()


def test_fetch_never_exceeds_max_documents(tmp_path: Path) -> None:
    m = _manifest(None, n=3)
    m.max_documents = 2
    with pytest.raises(FetchError):
        fetch_corpus(
            m,
            tmp_path,
            downloader=lambda u, mm: b"%PDF-x",
            bootstrap=True,
            limiter=FakeLimiter(),
            log=lambda s: None,
        )
