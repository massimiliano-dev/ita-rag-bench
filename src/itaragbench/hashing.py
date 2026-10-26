"""Content hashing helpers (sha256 everywhere, no pickle)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk_size):
            h.update(block)
    return h.hexdigest()


def sha256_json(obj: Any) -> str:
    """Stable hash of a JSON-serialisable object."""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))
