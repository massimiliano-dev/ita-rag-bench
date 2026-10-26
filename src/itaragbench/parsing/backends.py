"""Parser backends. These functions run INSIDE the sandboxed worker process only.

Each backend returns a list of ``(page_no, text)`` for the inclusive 1-based page range
and the backend version string. Heavy imports are local so the default install stays light.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

PageList = list[tuple[int, str]]
Backend = Callable[[Path, int, int, dict[str, Any]], PageList]


def parse_pypdf(pdf: Path, first: int, last: int, options: dict[str, Any]) -> PageList:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf))
    out: PageList = []
    for page_no in range(first, last + 1):
        text = reader.pages[page_no - 1].extract_text() or ""
        out.append((page_no, text))
    return out


def parse_pymupdf(pdf: Path, first: int, last: int, options: dict[str, Any]) -> PageList:
    import pymupdf

    out: PageList = []
    with pymupdf.open(str(pdf)) as doc:
        for page_no in range(first, last + 1):
            page = doc[page_no - 1]
            out.append((page_no, str(page.get_text("text"))))
    return out


def parse_docling(pdf: Path, first: int, last: int, options: dict[str, Any]) -> PageList:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline = PdfPipelineOptions()
    pipeline.do_ocr = bool(options.get("do_ocr", True))
    pipeline.do_table_structure = bool(options.get("do_table_structure", True))
    pipeline.enable_remote_services = False  # never call external APIs
    if "ocr_lang" in options:
        pipeline.ocr_options.lang = list(options["ocr_lang"])
    # Docling only OCRs bitmap regions by default; scanned GU issues carry a tiny text overlay
    # ("COPIA TRATTA DA GURITEL") that suppresses OCR. Production-style policy: force full-page
    # OCR when the text layer is (almost) empty for the requested pages.
    min_chars = int(options.get("force_ocr_below_chars_per_page", 0))
    if (
        pipeline.do_ocr
        and min_chars > 0
        and _text_layer_chars_per_page(pdf, first, last) < min_chars
    ):
        pipeline.ocr_options.force_full_page_ocr = True
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )
    result = converter.convert(str(pdf), page_range=(first, last))
    doc = result.document
    out: PageList = []
    for page_no in range(first, last + 1):
        out.append((page_no, doc.export_to_markdown(page_no=page_no)))
    return out


def _text_layer_chars_per_page(pdf: Path, first: int, last: int) -> float:
    import pypdfium2

    doc = pypdfium2.PdfDocument(str(pdf))
    try:
        total = 0
        for page_no in range(first, last + 1):
            textpage = doc[page_no - 1].get_textpage()
            total += len(textpage.get_text_range().strip())
        return total / (last - first + 1)
    finally:
        doc.close()


BACKENDS: dict[str, tuple[Backend, str]] = {
    "pypdf": (parse_pypdf, "pypdf"),
    "pymupdf": (parse_pymupdf, "pymupdf"),
    "docling": (parse_docling, "docling"),
}


def backend_version(name: str) -> str:
    dist = BACKENDS[name][1]
    try:
        return f"{dist}=={version(dist)}"
    except Exception:  # pragma: no cover - not installed
        return f"{dist}==not-installed"
