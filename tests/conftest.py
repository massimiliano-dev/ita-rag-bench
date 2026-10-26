from __future__ import annotations

from pathlib import Path

import pytest

from itaragbench.parsing.base import ParsedDocument, ParsedPage
from tests.pdf_fixture import build_pdf


@pytest.fixture
def tiny_pdf(tmp_path: Path) -> Path:
    return build_pdf(tmp_path / "tiny.pdf")


@pytest.fixture
def legal_doc() -> ParsedDocument:
    p1 = (
        "LEGGE 1 gennaio 2099, n. 1.\nCapo I\nPRINCIPI\nArt. 1.\nOggetto\n"
        "1. La presente legge disciplina la conservazione dei documenti di prova.\n"
        "2. I documenti sono conservati per un periodo non inferiore a dieci anni.\n"
    )
    long_commi = "".join(
        f"{i}. Comma numero {i} che contiene un testo abbastanza lungo da riempire spazio "
        f"e verificare la suddivisione dell'articolo ai confini dei commi, ripetuto. \n"
        for i in range(1, 30)
    )
    p2 = "Art. 2.\nSanzioni amministrative\n" + long_commi + "Art. 3.\nEntrata in vigore\n1. Ok.\n"
    return ParsedDocument("doc-a", "test", "0", [ParsedPage(1, p1), ParsedPage(2, p2)], 0.0)
