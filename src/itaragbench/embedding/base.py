"""Embedder protocol and factory."""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float32]


class Embedder(Protocol):
    name: str
    revision: str

    def embed_queries(self, texts: list[str]) -> FloatArray: ...

    def embed_passages(self, texts: list[str]) -> FloatArray: ...

    def describe(self) -> dict[str, Any]: ...


def l2_normalize(x: FloatArray) -> FloatArray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    out: FloatArray = (x / norms).astype(np.float32)
    return out


def make_embedder(spec: dict[str, Any]) -> Embedder:
    kind = spec.get("kind", "sentence-transformers")
    if kind == "fake":
        from itaragbench.embedding.fake import FakeEmbedder

        return FakeEmbedder(dim=int(spec.get("dim", 64)))
    if kind == "sentence-transformers":
        from itaragbench.embedding.st import SentenceTransformerEmbedder

        return SentenceTransformerEmbedder(
            model_id=str(spec["model"]),
            revision=str(spec["revision"]),
            query_prefix=str(spec.get("query_prefix", "")),
            passage_prefix=str(spec.get("passage_prefix", "")),
            max_seq_length=int(spec.get("max_seq_length", 512)),
            batch_size=int(spec.get("batch_size", 32)),
            device=spec.get("device"),
        )
    raise ValueError(f"unknown embedder kind {kind!r}")
