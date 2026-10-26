"""Polite, verifiable corpus downloader.

Rules enforced here (see corpus/LICENSES.md and SECURITY.md):

* HTTPS only, and only to hosts in the manifest allowlist (redirects included);
* a descriptive User-Agent;
* at least ``min_interval_seconds`` between two requests (default 2 s);
* never more documents than the manifest lists (hard cap ``max_documents``);
* a maximum response size and a PDF magic-number check;
* every file is verified against the sha256 recorded in the manifest.
"""

from __future__ import annotations

import datetime as dt
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http.client import HTTPMessage
from pathlib import Path
from typing import IO
from urllib.parse import urlparse

from itaragbench.hashing import sha256_bytes, sha256_file
from itaragbench.manifest import Document, Manifest


class FetchError(RuntimeError):
    pass


def check_url(url: str, allowed_hosts: list[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise FetchError(f"refusing non-HTTPS URL: {url}")
    host = (parsed.hostname or "").lower()
    if host not in {h.lower() for h in allowed_hosts}:
        raise FetchError(f"host {host!r} is not in the allowlist {allowed_hosts}")


class _AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: list[str]) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        check_url(newurl, self.allowed_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RateLimiter:
    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if min_interval < 2.0:
            raise ValueError("min_interval must be at least 2 seconds")
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last is not None:
            delta = now - self._last
            if delta < self.min_interval:
                self._sleep(self.min_interval - delta)
        self._last = self._clock()


@dataclass
class FetchResult:
    doc_id: str
    path: Path
    sha256: str
    status: str  # "cached" | "downloaded" | "bootstrapped"


def _download(url: str, manifest: Manifest, timeout: float = 60.0) -> bytes:
    check_url(url, manifest.allowed_hosts)
    opener = urllib.request.build_opener(_AllowlistRedirectHandler(manifest.allowed_hosts))
    req = urllib.request.Request(  # noqa: S310 - scheme checked by check_url
        url,
        headers={"User-Agent": manifest.user_agent, "Accept": "application/pdf"},
    )
    with opener.open(req, timeout=timeout) as resp:
        final_url = resp.geturl()
        check_url(final_url, manifest.allowed_hosts)
        ctype = resp.headers.get("Content-Type", "")
        if "pdf" not in ctype.lower():
            raise FetchError(f"unexpected Content-Type {ctype!r} for {url}")
        declared = resp.headers.get("Content-Length")
        if declared is not None and int(declared) > manifest.max_bytes:
            raise FetchError(f"{url} is {declared} bytes, above max_bytes")
        data: bytes = resp.read(manifest.max_bytes + 1)
    if len(data) > manifest.max_bytes:
        raise FetchError(f"{url} exceeds max_bytes={manifest.max_bytes}")
    if not data.startswith(b"%PDF-"):
        raise FetchError(f"{url} did not return a PDF (bad magic number)")
    return data


def fetch_corpus(
    manifest: Manifest,
    pdf_dir: Path,
    *,
    only: list[str] | None = None,
    bootstrap: bool = False,
    force: bool = False,
    log: Callable[[str], None] = print,
    downloader: Callable[[str, Manifest], bytes] = _download,
    limiter: RateLimiter | None = None,
) -> list[FetchResult]:
    """Download (if needed) and verify every document of the manifest.

    ``bootstrap=True`` is only for maintainers adding a new document: it records the
    sha256 of a document that has none yet. Normal use refuses documents without a hash.
    """
    pdf_dir.mkdir(parents=True, exist_ok=True)
    docs: list[Document] = [d for d in manifest.documents if only is None or d.id in only]
    if len(docs) > manifest.max_documents:
        raise FetchError("refusing to fetch more documents than max_documents")
    limiter = limiter or RateLimiter(manifest.min_interval_seconds)
    results: list[FetchResult] = []
    for doc in docs:
        check_url(doc.url, manifest.allowed_hosts)
        target = pdf_dir / doc.filename
        if doc.sha256 is None and not bootstrap:
            raise FetchError(f"{doc.id}: no sha256 in manifest (use --bootstrap as maintainer)")
        if target.exists() and not force:
            digest = sha256_file(target)
            if doc.sha256 is None or digest == doc.sha256:
                if doc.sha256 is None:
                    doc.sha256 = digest
                    doc.retrieved = doc.retrieved or dt.date.today().isoformat()
                    results.append(FetchResult(doc.id, target, digest, "bootstrapped"))
                else:
                    results.append(FetchResult(doc.id, target, digest, "cached"))
                log(f"[ok]   {doc.id} (cached, sha256 verified)")
                continue
            log(f"[warn] {doc.id}: cached file hash mismatch, re-downloading")
        limiter.wait()
        log(f"[get]  {doc.id} <- {doc.url}")
        data = downloader(doc.url, manifest)
        digest = sha256_bytes(data)
        if doc.sha256 is not None and digest != doc.sha256:
            raise FetchError(
                f"{doc.id}: sha256 mismatch (expected {doc.sha256}, got {digest}). "
                "The publisher may have re-issued the file; review before updating the manifest."
            )
        tmp = target.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(target)
        status = "downloaded"
        if doc.sha256 is None:
            doc.sha256 = digest
            doc.retrieved = dt.date.today().isoformat()
            status = "bootstrapped"
        results.append(FetchResult(doc.id, target, digest, status))
        log(f"[ok]   {doc.id} ({len(data)} bytes, sha256 {digest[:12]}...)")
    return results
