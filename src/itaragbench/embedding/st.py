"""sentence-transformers wrapper with pinned revisions and no remote code."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from itaragbench.embedding.base import FloatArray, l2_normalize


def pick_device(requested: str | None = None) -> str:
    if requested:
        return requested
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@dataclass
class SentenceTransformerEmbedder:
    model_id: str
    revision: str
    query_prefix: str = ""
    passage_prefix: str = ""
    max_seq_length: int = 512
    batch_size: int = 32
    device: str | None = None
    name: str = field(init=False)
    _model: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.name = self.model_id
        if len(self.revision) != 40:
            raise ValueError(f"{self.model_id}: revision must be a full 40-char commit hash")

    def _load(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self.device = pick_device(self.device)
            self._model = SentenceTransformer(
                self.model_id,
                revision=self.revision,
                device=self.device,
                trust_remote_code=False,
            )
            self._model.max_seq_length = self.max_seq_length
        return self._model

    def _encode(self, texts: list[str]) -> FloatArray:
        model = self._load()
        vecs = model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return l2_normalize(np.asarray(vecs, dtype=np.float32))

    def embed_queries(self, texts: list[str]) -> FloatArray:
        return self._encode([self.query_prefix + t for t in texts])

    def embed_passages(self, texts: list[str]) -> FloatArray:
        return self._encode([self.passage_prefix + t for t in texts])

    def describe(self) -> dict[str, Any]:
        return {
            "kind": "sentence-transformers",
            "model": self.model_id,
            "revision": self.revision,
            "query_prefix": self.query_prefix,
            "passage_prefix": self.passage_prefix,
            "max_seq_length": self.max_seq_length,
            "device": self.device,
            "trust_remote_code": False,
        }
