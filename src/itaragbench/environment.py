"""Capture the execution environment for reproducibility."""

from __future__ import annotations

import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

PACKAGES = (
    "ita-rag-bench",
    "pypdf",
    "pymupdf",
    "docling",
    "docling-core",
    "docling-ibm-models",
    "sentence-transformers",
    "transformers",
    "torch",
    "numpy",
    "bm25s",
    "pystemmer",
    "rapidocr",
)


def package_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for p in PACKAGES:
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            out[p] = None
    return out


def environment() -> dict[str, Any]:
    info: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": package_versions(),
    }
    try:
        import torch

        info["torch_mps_available"] = bool(torch.backends.mps.is_available())
        info["torch_cuda_available"] = bool(torch.cuda.is_available())
    except ImportError:
        pass
    return info
