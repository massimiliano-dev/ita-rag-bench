"""Generate a tiny, valid, text-based PDF without any third-party library."""

from __future__ import annotations

from pathlib import Path

HEADER = "GAZZETTA UFFICIALE DELLA REPUBBLICA ITALIANA Serie generale - n. 1"

PAGES = [
    [
        HEADER,
        "LEGGE 1 gennaio 2099, n. 1.",
        "Disposizioni di prova per il benchmark.",
        "Capo I",
        "PRINCIPI",
        "Art. 1.",
        "Oggetto",
        "1. La presente legge disciplina la conservazione dei documenti",
        "di prova presso gli archivi comunali.",
        "2. I documenti sono conservati per un periodo non inferiore a",
        "dieci anni dalla data di deposito presso l'archivio, salvo",
    ],
    [
        HEADER,
        "diversa disposizione del regolamento comunale.",
        "Art. 2.",
        "Sanzioni",
        "1. Chi distrugge un documento di prova e' punito con la sanzione",
        "amministrativa pecuniaria da 500 a 5.000 euro.",
        "Art. 3.",
        "Entrata in vigore",
        "1. La presente legge entra in vigore il giorno successivo a quello",
        "della sua pubblicazione nella Gazzetta Ufficiale.",
    ],
]


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(path: Path, pages: list[list[str]] | None = None) -> Path:
    pages = pages or PAGES
    objects: list[bytes] = []
    n_pages = len(pages)
    # 1 catalog, 2 pages, 3 font, then (page, content) pairs
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pages))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, lines in enumerate(pages):
        content_id = 5 + 2 * i
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        ops = ["BT", "/F1 10 Tf", "14 TL", "50 800 Td"]
        for ln in lines:
            ops.append(f"({_escape(ln)}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(bytes(out))
    return path
