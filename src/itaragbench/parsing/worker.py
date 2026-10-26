"""Sandboxed parser worker: ``python -I -m itaragbench.parsing.worker <args>``.

It parses ONE PDF and writes JSON. It never executes embedded content: we only call
text/layout extraction APIs, JavaScript and attachments are ignored by all three
backends, and no network access is required for pypdf/pymupdf.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import resource
import sys
import time
from pathlib import Path

from itaragbench.parsing.backends import BACKENDS, backend_version


def _limit_memory(max_mb: int) -> None:
    limit = max_mb * 1024 * 1024
    for name in ("RLIMIT_AS", "RLIMIT_DATA"):
        res = getattr(resource, name, None)
        if res is None:
            continue
        # macOS does not enforce RLIMIT_AS; the parent RSS watchdog covers it.
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(res, (limit, limit))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("parser", choices=sorted(BACKENDS))
    ap.add_argument("pdf", type=Path)
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("out", type=Path)
    ap.add_argument("--max-mb", type=int, default=4096)
    ap.add_argument("--options", default="{}")
    args = ap.parse_args(argv)
    if args.max_mb > 0:
        _limit_memory(args.max_mb)
    fn, _ = BACKENDS[args.parser]
    t0 = time.perf_counter()
    pages = fn(args.pdf, args.first, args.last, json.loads(args.options))
    seconds = time.perf_counter() - t0
    payload = {
        "parser_version": backend_version(args.parser),
        "seconds": seconds,
        "pages": [{"page_no": n, "text": t} for n, t in pages],
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
