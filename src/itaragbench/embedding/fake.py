"""Deterministic hashing embedder for tests: no model download, no network."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from itaragbench.embedding.base import FloatArray, l2_normalize

_TOK = re.compile(r"\w+", re.UNICODE)


@dataclass
class FakeEmbedder:
    dim: int = 64
    name: str = "fake-hashing"
    revision: str = "0"

    def _embed(self, texts: list[str]) -> FloatArray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in _TOK.findall(t.lower()):
                h = int.from_bytes(hashlib.sha256(tok.encode()).digest()[:8], "little")
                out[i, h % self.dim] += 1.0 if (h >> 32) & 1 else -1.0
        return l2_normalize(out)

    def embed_queries(self, texts: list[str]) -> FloatArray:
        return self._embed(texts)

    def embed_passages(self, texts: list[str]) -> FloatArray:
        return self._embed(texts)

    def describe(self) -> dict[str, Any]:
        return {"kind": "fake", "name": self.name, "dim": self.dim}
