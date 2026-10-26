"""Static leaderboard generator: the "official timetable" of a run.

Writes plain HTML with no JavaScript and no external hosts: ``<out>`` in Italian and ``<out dir>/en/``
in English, plus the self-hosted font in ``<out dir>/assets``. Every number comes from the run's
``summary.json`` / ``run.json``; the written conclusions come from ``findings.json`` when present.
"""

from __future__ import annotations

import html
import json
import shutil
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

ASSETS = Path(__file__).parent / "site_assets"
REPO = "https://github.com/massimiliano-dev/ita-rag-bench"

PARSERS = {"pypdf": "PY", "pymupdf": "MU", "docling": "DL"}
CHUNKERS = {"fixed": "FX", "recursive": "RC", "structure": "ST"}
SERVICES: list[tuple[str, str | None]] = [
    ("bm25", None),
    ("dense", "e5-base"),
    ("dense", "bge-m3"),
    ("hybrid", "e5-base"),
    ("hybrid", "bge-m3"),
]
SERVICE_CODES: dict[tuple[str, str | None], str] = {
    ("bm25", None): "BM",
    ("dense", "e5-base"): "E5",
    ("dense", "bge-m3"): "M3",
    ("hybrid", "e5-base"): "HE",
    ("hybrid", "bge-m3"): "HM",
}
# A single configuration's recall@5 has a 95% interval of about ±7 points on this dataset size:
# nothing closer than this is ranked, highlighted or called a winner.
NOISE = 0.07
CATEGORIES = ["fattuale", "multi_hop", "tabellare", "temporale"]
LANGS = ("it", "en")

S: dict[str, dict[str, str]] = {
    "it": {
        "title": "Cosa conta davvero nel RAG su documenti italiani",
        "doc_title": "ita-rag-bench · risultati",
        "lead": "Un banco di prova che misura l'intera pipeline di retrieval su leggi e decreti della "
        "Gazzetta Ufficiale: estrazione del testo dal PDF, divisione in chunk, embedding e ricerca. "
        "Non solo l'embedding.",
        "run": "Corsa",
        "valid": "Valido dal",
        "facts": "{docs} atti, {pages} pagine, {items} domande",
        "other_lang": "English",
        "other_lang_code": "en",
        "nav": "Sezioni",
        "nav_findings": "Conclusioni",
        "nav_timetable": "Orario",
        "nav_categories": "Per tipo di domanda",
        "nav_documents": "Per documento",
        "nav_costs": "Costi",
        "nav_method": "Metodo",
        "draft": "Tutte le {items} domande sono bozze scritte con l'aiuto di un LLM e non ancora "
        "validate da persone. Con {answerable} domande con risposta, il recall@5 di una singola "
        "configurazione ha un intervallo al 95% di circa ±7 punti: differenze più piccole sono rumore.",
        "draft_short": "domande in bozza, non ancora validate",
        "findings": "Conclusioni",
        "departures": "Le tre configurazioni più alte",
        "tie": "Le tre differiscono di {points} punti, meno dell'intervallo di ±7: con questi dati nessuna è significativamente migliore delle altre.",
        "no_tie": "La prima supera la terza di {points} punti, più dell'intervallo di ±7.",
        "table_tie": "Nessun valore si stacca dagli altri di più di 7 punti: nessuno è evidenziato.",
        "stop_parse": "Fermata 1 · Parsing e chunking",
        "ceiling_unit": "tetto: quota di passaggi interi in almeno un chunk",
        "stop_search": "Fermata 2 · Ricerca: recall@5, un servizio per riga",
        "line_strip": "Tabella 1 · Linea PDF › chunk › ricerca · 9 treni, 5 servizi",  # noqa: RUF001 (route separator)
        "service": "Servizio",
        "train": "Treno",
        "check_in": "Verifica nell'orario:",
        "timetable": "Orario: quanto recall resta a ogni fermata",
        "timetable_intro": "Ogni colonna è una linea, una coppia di parser e chunker; ogni treno è una linea con un servizio di ricerca e ha un codice unico, per esempio MU·FX·HM. "
        "Alla prima fermata, parsing e chunking insieme, si vede il tetto: la quota di passaggi di riferimento che finisce intera in almeno un chunk. "
        "Alla seconda fermata ogni riga è un servizio di ricerca alternativo. L'ultima riga è il recall perso nella ricerca.",
        "stop": "Fermata / servizio",
        "ceiling": "Tetto dopo parsing e chunking",
        "ceiling_short": "Tetto",
        "lost": "Perso nella ricerca (tetto − migliore)",  # noqa: RUF001 (typographic minus)
        "best_mark": "In giallo il valore più alto osservato; in grassetto il migliore di una riga solo se supera il secondo di più di 7 punti.",
        "ci_note": "Intervallo al 95% di circa ±7 punti per cella.",
        "legend": "Come leggere i codici",
        "categories": "Per tipo di domanda",
        "categories_intro": "Recall@5 medio sui nove treni, per servizio di ricerca. Le domande "
        "senza risposta ({unanswerable}) sono escluse: l'astensione si misurerà quando verrà "
        "aggiunta la generazione.",
        "category": "Tipo di domanda",
        "questions": "Domande",
        "small_n": "Campione piccolo: leggere con cautela.",
        "documents": "Per documento",
        "documents_intro": "Recall@5 con bge-m3 denso, media sui tre chunker, divisa per "
        "caratteristiche del PDF.",
        "parser": "Parser",
        "native": "PDF nativo",
        "scanned": "PDF scansionato",
        "with_tables": "Con tabelle",
        "without_tables": "Senza tabelle",
        "costs": "Costi",
        "costs_intro": "Tempi misurati su {pages} pagine (Apple M5, 32 GB).",
        "stage": "Componente",
        "operation": "Operazione",
        "time": "Tempo",
        "parse_time": "Estrazione del testo",
        "index_time": "Indicizzazione",
        "query_time": "Ricerca per domanda",
        "method": "Metodo e riproducibilità",
        "method_body": "Corpus: {docs} atti ufficiali scaricati dalla Gazzetta Ufficiale e "
        "verificati con SHA-256. Domande: {items} ({answerable} con risposta). Ogni risposta di "
        "riferimento è ancorata al testo ufficiale (documento, articolo, comma e passaggio "
        "testuale), non a un chunk: così un chunker non viene favorito rispetto a un altro.",
        "reproduce": "Per rieseguire la corsa:",
        "files": "Risultati completi, domanda per domanda:",
        "footer": "Progetto non ufficiale. Codice con licenza MIT; dataset con licenza CC BY 4.0. "
        "I testi degli atti sono della Gazzetta Ufficiale della Repubblica Italiana.",
        "source": "Sorgente su GitHub",
        "na": "—",
    },
    "en": {
        "title": "What really matters for RAG on Italian documents",
        "doc_title": "ita-rag-bench · results",
        "lead": "A benchmark that measures the whole retrieval pipeline on laws and decrees from the "
        "Italian Official Gazette: text extraction from the PDF, chunking, embeddings and search. "
        "Not just the embedding.",
        "run": "Run",
        "valid": "Valid from",
        "facts": "{docs} acts, {pages} pages, {items} questions",
        "other_lang": "Italiano",
        "other_lang_code": "it",
        "nav": "Sections",
        "nav_findings": "Findings",
        "nav_timetable": "Timetable",
        "nav_categories": "By question type",
        "nav_documents": "By document",
        "nav_costs": "Costs",
        "nav_method": "Method",
        "draft": "All {items} questions are drafts written with LLM help and not yet validated by "
        "people. With {answerable} answerable questions, one configuration's recall@5 has a 95% "
        "interval of about ±7 points: smaller differences are noise.",
        "draft_short": "draft questions, not yet validated",
        "findings": "Findings",
        "departures": "The three highest configurations",
        "tie": "The three differ by {points} points, less than the ±7 interval: with this data none is significantly better than the others.",
        "no_tie": "The first beats the third by {points} points, more than the ±7 interval.",
        "table_tie": "No value stands more than 7 points clear of the others, so none is highlighted.",
        "stop_parse": "Stop 1 · Parsing and chunking",
        "ceiling_unit": "ceiling: share of passages whole in at least one chunk",
        "stop_search": "Stop 2 · Search: recall@5, one service per row",
        "line_strip": "Table 1 · Line PDF › chunk › search · 9 trains, 5 services",  # noqa: RUF001 (route separator)
        "service": "Service",
        "train": "Train",
        "check_in": "Check in the timetable:",
        "timetable": "Timetable: how much recall is left at each stop",
        "timetable_intro": "Each column is a line, a parser and chunker pair; each train is a line with a search service and has a unique code, for example MU·FX·HM. "
        "The first stop, parsing and chunking together, shows the ceiling: the share of reference passages that end up whole in at least one chunk. "
        "At the second stop each row is an alternative search service. The last row is the recall lost in search.",
        "stop": "Stop / service",
        "ceiling": "Ceiling after parsing and chunking",
        "ceiling_short": "Ceiling",
        "lost": "Lost in search (ceiling − best)",  # noqa: RUF001 (typographic minus)
        "best_mark": "Yellow marks the highest observed value; bold marks a row's best only when it beats the runner-up by more than 7 points.",
        "ci_note": "95% interval of about ±7 points per cell.",
        "legend": "How to read the codes",
        "categories": "By question type",
        "categories_intro": "Mean recall@5 over the nine trains, by search service. Questions with "
        "no answer ({unanswerable}) are excluded: abstention will be measured once generation is "
        "added.",
        "category": "Question type",
        "questions": "Questions",
        "small_n": "Small sample: read with care.",
        "documents": "By document",
        "documents_intro": "Recall@5 with dense bge-m3, averaged over the three chunkers, split by "
        "PDF characteristics.",
        "parser": "Parser",
        "native": "Native PDF",
        "scanned": "Scanned PDF",
        "with_tables": "With tables",
        "without_tables": "Without tables",
        "costs": "Costs",
        "costs_intro": "Times measured on {pages} pages (Apple M5, 32 GB).",
        "stage": "Component",
        "operation": "Operation",
        "time": "Time",
        "parse_time": "Text extraction",
        "index_time": "Indexing",
        "query_time": "Search per question",
        "method": "Method and reproducibility",
        "method_body": "Corpus: {docs} official acts downloaded from the Official Gazette and "
        "verified with SHA-256. Questions: {items} ({answerable} answerable). Every reference "
        "answer is anchored to the official text (document, article, paragraph and passage), not "
        "to a chunk, so no chunker is favoured over another.",
        "reproduce": "To run it again:",
        "files": "Full results, question by question:",
        "footer": "Unofficial project. Code under the MIT licence; dataset under CC BY 4.0. Act "
        "texts are from the Gazzetta Ufficiale della Repubblica Italiana.",
        "source": "Source on GitHub",
        "na": "—",
    },
}

SERVICE_NAMES = {
    "it": {"bm25": "BM25", "dense": "Denso", "hybrid": "Ibrido"},
    "en": {"bm25": "BM25", "dense": "Dense", "hybrid": "Hybrid"},
}
CATEGORY_NAMES = {
    "it": {
        "fattuale": "Fattuale (un comma)",
        "multi_hop": "Multi-hop (due articoli o atti)",
        "tabellare": "Tabellare (una cella)",
        "temporale": "Temporale",
    },
    "en": {
        "fattuale": "Factual (one paragraph)",
        "multi_hop": "Multi-hop (two articles or acts)",
        "tabellare": "Table (one cell)",
        "temporale": "Temporal",
    },
}
MONTHS = {
    "it": [
        "gennaio",
        "febbraio",
        "marzo",
        "aprile",
        "maggio",
        "giugno",
        "luglio",
        "agosto",
        "settembre",
        "ottobre",
        "novembre",
        "dicembre",
    ],
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
}


def _latest_run(results: Path) -> Path:
    runs = sorted(p for p in results.iterdir() if (p / "summary.json").exists())
    if not runs:
        raise FileNotFoundError(f"no results with summary.json under {results}")
    return runs[-1]


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _num(value: float | None, lang: str, digits: int = 3) -> str:
    if value is None:
        return S[lang]["na"]
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if lang == "it" else text


def _seconds(value: float | None, lang: str) -> str:
    if value is None:
        return S[lang]["na"]
    digits = 0 if value >= 100 else 1
    return f"{_num(value, lang, digits)} s"


def _train(parser: str, chunker: str) -> str:
    return f"{PARSERS.get(parser, parser[:2].upper())}·{CHUNKERS.get(chunker, chunker[:2].upper())}"


def _full_code(parser: str, chunker: str, retriever: str, embedding: str | None) -> str:
    """Unique train number: line (parser·chunker) plus service, e.g. MU·FX·HM."""
    return f"{_train(parser, chunker)}·{SERVICE_CODES.get((retriever, embedding), retriever[:2].upper())}"


def _anchor(code: str) -> str:
    prefix = "cell-" if code.count("·") >= 2 else "train-"
    return prefix + code.replace("·", "-").lower()


def _service_label(retriever: str, embedding: str | None, lang: str) -> str:
    name = SERVICE_NAMES[lang].get(retriever, retriever)
    return f"{name} {embedding}" if embedding else name


def _date(created: str | None, lang: str) -> str:
    if not created:
        return S[lang]["na"]
    day = datetime.fromisoformat(created).date()
    month = MONTHS[lang][day.month - 1]
    return f"{day.day} {month} {day.year}" if lang == "it" else f"{month} {day.day}, {day.year}"


def _mean(values: Iterable[float | None]) -> float | None:
    real = [v for v in values if v is not None]
    return sum(real) / len(real) if real else None


def _separable_max(values: Iterable[float | None]) -> float | None:
    """The maximum, but only when it beats the runner-up by more than the noise interval."""
    real = sorted((v for v in values if v is not None), reverse=True)
    if len(real) < 2 or real[0] - real[1] < NOISE:
        return None
    return real[0]


def _points(value: float, lang: str) -> str:
    return _num(value * 100, lang, 1)


def _ci(lang: str) -> str:
    return f'<sup class="mark" title="{_e(S[lang]["ci_note"])}">‡</sup>'


class Run:
    """Lookups over one run's summary rows."""

    def __init__(self, summary: dict[str, Any], meta: dict[str, Any]) -> None:
        self.meta = meta
        self.rows: list[dict[str, Any]] = summary["rows"]
        self.trains = [(p, c) for p in PARSERS for c in CHUNKERS if self.find(p, c) is not None]

    def find(
        self, parser: str, chunker: str, retriever: str | None = None, embedding: str | None = None
    ) -> dict[str, Any] | None:
        for row in self.rows:
            if row["parser"] != parser or row["chunker"] != chunker:
                continue
            if retriever is not None and (
                row["retriever"] != retriever or row.get("embedding") != embedding
            ):
                continue
            return row
        return None

    def recall5(
        self, parser: str, chunker: str, retriever: str, embedding: str | None
    ) -> float | None:
        row = self.find(parser, chunker, retriever, embedding)
        return None if row is None else float(row["overall"]["recall@5"])

    def ceiling(self, parser: str, chunker: str) -> float | None:
        row = self.find(parser, chunker)
        if row is None:
            return None
        share = row.get("evidence_coverage", {}).get("overall", {}).get("share")
        return None if share is None else float(share)

    def ranked(self) -> list[tuple[float, str, str, str, str | None]]:
        options = []
        for p, c in self.trains:
            for retriever, embedding in SERVICES:
                value = self.recall5(p, c, retriever, embedding)
                if value is not None:
                    options.append((value, p, c, retriever, embedding))
        return sorted(options, key=lambda o: o[0], reverse=True)


def _masthead(run: Run, lang: str, prefix: str) -> str:
    s = S[lang]
    meta = run.meta
    dataset = meta.get("dataset", {})
    facts = s["facts"].format(
        docs=meta.get("corpus", {}).get("n_documents", "?"),
        pages=_pages(run),
        items=dataset.get("n_items", "?"),
    )
    other = s["other_lang_code"]
    other_href = f"{prefix}en/" if lang == "it" else f"{prefix}"
    nav = [
        ("findings", s["nav_findings"]),
        ("timetable", s["nav_timetable"]),
        ("categories", s["nav_categories"]),
        ("documents", s["nav_documents"]),
        ("costs", s["nav_costs"]),
        ("method", s["nav_method"]),
    ]
    links = "".join(f'<li><a href="#{a}">{_e(label)}</a></li>' for a, label in nav)
    return f"""<header class="masthead">
  <div class="masthead-row">
    <a class="wordmark" href="{_e(prefix + "en/" if lang == "en" else "./")}">ita-rag-bench</a>
    <p class="validity"><span>{_e(s["run"])} <b class="num">{_e(meta.get("run_id", ""))}</b></span>
      <span>{_e(s["valid"])} <b>{_e(_date(meta.get("created"), lang))}</b></span>
      <span>{_e(facts)}<a class="mark" href="#draft" aria-label="{_e(s["draft_short"])}">†</a></span></p>
    <a class="lang" href="{_e(other_href)}" hreflang="{other}" lang="{other}">{_e(s["other_lang"])}</a>
  </div>
  <nav aria-label="{_e(s["nav"])}"><ul>{links}</ul></nav>
</header>"""


def _pages(run: Run) -> int | str:
    parsers = run.meta.get("parsers", {})
    pages = [v.get("pages") for v in parsers.values() if v.get("pages")]
    return max(pages) if pages else "?"


def _departures(run: Run, lang: str, draft: str) -> str:
    """First-viewport board: the three highest trains and whether they can be told apart."""
    s = S[lang]
    top = run.ranked()[:3]
    rows = []
    for value, p, c, retriever, embedding in top:
        code = _full_code(p, c, retriever, embedding)
        rows.append(
            f'<tr><th scope="row"><a class="code" href="#{_anchor(code)}">{_e(code)}</a></th>'
            f"<td>{_e(_service_label(retriever, embedding, lang))}</td>"
            f'<td class="num">{_num(value, lang)}</td>'
            f'<td class="num">{_num(run.ceiling(p, c), lang)}</td></tr>'
        )
    verdict = ""
    if len(top) == 3:
        spread = top[0][0] - top[2][0]
        key = "tie" if spread < NOISE else "no_tie"
        verdict = f'<p class="verdict">{_e(s[key].format(points=_points(spread, lang)))}</p>'
    return f"""<aside class="departures" aria-labelledby="departures-h">
  <h2 id="departures-h">{_e(s["departures"])}</h2>
  <table>
    <thead><tr><th scope="col">{_e(s["train"])}</th><th scope="col">{_e(s["service"])}</th>
    <th scope="col" class="num">recall@5{_ci(lang)}</th><th scope="col" class="num">{_e(s["ceiling_short"])}</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  {verdict}
  <ul class="margin-notes">
    <li id="draft"><span class="mark" aria-hidden="true">†</span> {_e(draft)}</li>
    <li><span class="mark" aria-hidden="true">‡</span> {_e(s["ci_note"])}</li>
  </ul>
</aside>"""


def _codes(codes: Iterable[str]) -> str:
    return "".join(
        f'<li><a class="code" href="#{_anchor(code)}">{_e(code)}</a></li>' for code in codes
    )


def _headlines(findings: list[dict[str, Any]], lang: str) -> str:
    """The findings' titles in the opening column, each linked to its full text."""
    if not findings:
        return ""
    items = []
    for i, finding in enumerate(findings, start=1):
        text = finding.get(lang) or finding.get("en") or {}
        items.append(
            f'<li><a href="#finding-{i}">{_e(text.get("title", ""))}</a>'
            f'<ul class="codes">{_codes(finding.get("trains", []))}</ul></li>'
        )
    return f'<ol class="headlines">{"".join(items)}</ol>'


def _legend(lang: str) -> str:
    parts = (
        [f"{v} = {k}" for k, v in PARSERS.items()]
        + [f"{v} = {k}" for k, v in CHUNKERS.items()]
        + [f"{code} = {_service_label(r, e, lang)}" for (r, e), code in SERVICE_CODES.items()]
    )
    items = "".join(f"<li>{_e(p)}</li>" for p in parts)
    return f'<p class="legend-title">{_e(S[lang]["legend"])}</p><ul class="legend">{items}</ul>'


def _findings(findings: list[dict[str, Any]], lang: str) -> str:
    if not findings:
        return ""
    s = S[lang]
    items = []
    for i, finding in enumerate(findings, start=1):
        text = finding.get(lang) or finding.get("en") or {}
        codes = _codes(finding.get("trains", []))
        check = (
            f'<div class="check"><span>{_e(s["check_in"])}</span><ul class="codes">{codes}</ul></div>'
            if codes
            else ""
        )
        items.append(
            f'<li class="finding" id="finding-{i}"><h3>{_e(text.get("title", ""))}</h3>'
            f"<p>{_e(text.get('body', ''))}</p>{check}</li>"
        )
    return f"""<section id="findings" class="wide with-margin" aria-labelledby="findings-h">
  <div class="column"><h2 id="findings-h">{_e(s["findings"])}</h2><ol class="findings">{"".join(items)}</ol></div>
  <aside class="margin" aria-label="{_e(s["legend"])}">{_legend(lang)}</aside>
</section>"""


def _timetable(run: Run, lang: str) -> str:
    s = S[lang]
    cells: dict[tuple[int, int], float | None] = {}
    for si, (retriever, embedding) in enumerate(SERVICES):
        for ti, (p, c) in enumerate(run.trains):
            cells[(si, ti)] = run.recall5(p, c, retriever, embedding)
    real = {k: v for k, v in cells.items() if v is not None}
    best = max(real, key=lambda k: real[k]) if real else None

    head = "".join(
        f'<th scope="col" id="{_anchor(_train(p, c))}"><span class="code">{_e(_train(p, c))}</span>'
        f'<span class="sub">{_e(p)}<br>{_e(c)}</span></th>'
        for p, c in run.trains
    )
    ceilings = [run.ceiling(p, c) for p, c in run.trains]
    ceiling_top = _separable_max(ceilings)
    ceiling_row = "".join(
        f'<td class="num{" strong" if v is not None and v == ceiling_top else ""}">{_num(v, lang)}</td>'
        for v in ceilings
    )
    span = len(run.trains) + 1
    body = [
        f'<tr class="ceiling"><th scope="row">{_e(s["stop_parse"])}'
        f'<span class="unit">{_e(s["ceiling_unit"])}</span></th>{ceiling_row}</tr>',
        f'<tr class="group"><th scope="rowgroup" colspan="{span}">{_e(s["stop_search"])}{_ci(lang)}</th></tr>',
    ]
    for si, (retriever, embedding) in enumerate(SERVICES):
        row_values = [cells[(si, ti)] for ti in range(len(run.trains))]
        row_top = _separable_max(row_values)
        tds = []
        for ti, v in enumerate(row_values):
            classes = ["num"]
            if v is not None and v == row_top:
                classes.append("strong")
            if best == (si, ti):
                classes.append("best")
            p, c = run.trains[ti]
            cell_id = _anchor(_full_code(p, c, retriever, embedding))
            tds.append(f'<td id="{cell_id}" class="{" ".join(classes)}">{_num(v, lang)}</td>')
        code = SERVICE_CODES.get((retriever, embedding), "")
        label = _service_label(retriever, embedding, lang)
        body.append(
            f'<tr><th scope="row">{_e(label)}<span class="unit">{_e(code)}</span></th>{"".join(tds)}</tr>'
        )
    lost = []
    for ti, ceiling in enumerate(ceilings):
        column = [cells[(si, ti)] for si in range(len(SERVICES))]
        top = max((v for v in column if v is not None), default=None)
        lost.append(None if ceiling is None or top is None else ceiling - top)
    lost_row = "".join(f'<td class="num">{_num(v, lang)}</td>' for v in lost)
    body.append(f'<tr class="lost"><th scope="row">{_e(s["lost"])}</th>{lost_row}</tr>')

    return f"""<section id="timetable" class="wide" aria-labelledby="timetable-h">
  <h2 id="timetable-h">{_e(s["timetable"])}</h2>
  <p class="intro">{_e(s["timetable_intro"])}</p>
  <p class="line-strip">{_e(s["line_strip"])}</p>
  <div class="table-scroll" role="region" aria-labelledby="timetable-h" tabindex="0">
    <table class="timetable">
      <thead><tr><th scope="col" class="corner">{_e(s["stop"])}</th>{head}</tr></thead>
      <tbody>{"".join(body)}</tbody>
    </table>
  </div>
  <ul class="notes">
    <li><span class="hl">&nbsp;</span> {_e(s["best_mark"])}</li>
    <li><span class="mark">‡</span> {_e(s["ci_note"])}</li>
    <li><span class="mark">†</span> {_e(s["draft_short"])}.</li>
  </ul>
  {_legend(lang)}
</section>"""


def _table(
    section: str,
    title: str,
    intro: str,
    head: list[tuple[str, bool]],
    rows: list[tuple[str, list[str], list[float | None]]],
    lang: str,
    notes: str = "",
    rank_rows: bool = True,
) -> str:
    """A ruled table. Yellow and bold only mark values that stand clear of the noise interval."""
    flat = [v for _, _, vals in rows for v in vals]
    best = _separable_max(flat)
    ths = "".join(
        f'<th scope="col"{' class="num"' if numeric else ""}>{h}</th>' for h, numeric in head
    )
    trs = []
    marked = False
    for label, extra, vals in rows:
        top = _separable_max(vals) if rank_rows else None
        tds = "".join(f'<td class="num">{x}</td>' for x in extra)
        for v in vals:
            classes = ["num"]
            if v is not None and v == top:
                classes.append("strong")
            if v is not None and v == best and not marked:
                classes.append("best")
                marked = True
            tds += f'<td class="{" ".join(classes)}">{_num(v, lang)}</td>'
        trs.append(f'<tr><th scope="row">{label}</th>{tds}</tr>')
    tie = "" if best is not None else f'<p class="tie-note">{_e(S[lang]["table_tie"])}</p>'
    return f"""<section id="{section}" aria-labelledby="{section}-h">
  <h2 id="{section}-h">{_e(title)}</h2>
  <p class="intro">{_e(intro)}</p>
  <div class="table-scroll" role="region" aria-labelledby="{section}-h" tabindex="0">
    <table class="ruled"><thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table>
  </div>{tie}{notes}
</section>"""


def _categories(run: Run, lang: str) -> str:
    s = S[lang]
    counts = run.meta.get("dataset", {}).get("category_counts", {})
    head = [(_e(s["category"]), False), (_e(s["questions"]), True)] + [
        (_e(_service_label(r, e, lang)) + _ci(lang), True) for r, e in SERVICES
    ]
    rows = []
    for cat in CATEGORIES:
        vals = []
        for retriever, embedding in SERVICES:
            per = []
            for p, c in run.trains:
                row = run.find(p, c, retriever, embedding)
                value = (
                    None
                    if row is None
                    else row.get("per_category", {}).get(cat, {}).get("recall@5")
                )
                per.append(None if value is None else float(value))
            vals.append(_mean(per))
        n = counts.get(cat)
        mark = (
            ' <span class="mark" title="' + _e(s["small_n"]) + '">*</span>'
            if n is not None and n < 25
            else ""
        )
        rows.append(
            (
                _e(CATEGORY_NAMES[lang].get(cat, cat)) + mark,
                [_e(n if n is not None else s["na"])],
                vals,
            )
        )
    notes = f'<ul class="notes"><li><span class="mark">*</span> {_e(s["small_n"])}</li></ul>'
    intro = s["categories_intro"].format(
        unanswerable=run.meta.get("senza_risposta", {}).get("count", "?")
    )
    return _table("categories", s["categories"], intro, head, rows, lang, notes)


def _documents(run: Run, lang: str) -> str:
    s = S[lang]
    head = [(_e(s["parser"]), False)] + [
        (_e(s[key]) + _ci(lang), True)
        for key in ("native", "scanned", "with_tables", "without_tables")
    ]
    rows: list[tuple[str, list[str], list[float | None]]] = []
    for parser in PARSERS:
        groups: list[list[float | None]] = [[], [], [], []]
        for chunker in CHUNKERS:
            row = run.find(parser, chunker, "dense", "bge-m3")
            if row is None:
                continue
            chars = row.get("per_characteristic", {})
            for i, (key, value) in enumerate(
                [
                    ("pdf_quality", "native"),
                    ("pdf_quality", "scanned"),
                    ("has_tables", "True"),
                    ("has_tables", "False"),
                ]
            ):
                cell = chars.get(key, {}).get(value, {}).get("recall@5")
                groups[i].append(None if cell is None else float(cell))
        if any(groups):
            rows.append((_e(parser), [], [_mean(g) for g in groups]))
    return _table(
        "documents", s["documents"], s["documents_intro"], head, rows, lang, rank_rows=False
    )


def _costs(run: Run, lang: str) -> str:
    s = S[lang]
    lines = []
    for parser, info in run.meta.get("parsers", {}).items():
        lines.append(
            f'<tr><th scope="row">{_e(parser)}</th><td>{_e(s["parse_time"])}</td>'
            f'<td class="num">{_seconds(info.get("seconds"), lang)}</td></tr>'
        )
    for embedding in ("e5-base", "bge-m3"):
        dense = [
            r for r in run.rows if r["retriever"] == "dense" and r.get("embedding") == embedding
        ]
        index = _mean(float(r["timings"]["index_seconds"]) for r in dense if r.get("timings"))
        query = _mean(float(r["timings"]["query_ms"]) for r in dense if r.get("timings"))
        lines.append(
            f'<tr><th scope="row">{_e(embedding)}</th><td>{_e(s["index_time"])}</td>'
            f'<td class="num">{_seconds(index, lang)}</td></tr>'
        )
        lines.append(
            f'<tr><th scope="row">{_e(embedding)}</th><td>{_e(s["query_time"])}</td>'
            f'<td class="num">{_num(query, lang, 1)} ms</td></tr>'
        )
    intro = s["costs_intro"].format(pages=_pages(run))
    return f"""<section id="costs" aria-labelledby="costs-h">
  <h2 id="costs-h">{_e(s["costs"])}</h2>
  <p class="intro">{_e(intro)}</p>
  <div class="table-scroll" role="region" aria-labelledby="costs-h" tabindex="0">
    <table class="ruled"><thead><tr><th scope="col">{_e(s["stage"])}</th><th scope="col">{_e(s["operation"])}</th>
    <th scope="col">{_e(s["time"])}</th></tr></thead><tbody>{"".join(lines)}</tbody></table>
  </div>
</section>"""


def _method(run: Run, lang: str) -> str:
    s = S[lang]
    dataset = run.meta.get("dataset", {})
    body = s["method_body"].format(
        docs=run.meta.get("corpus", {}).get("n_documents", "?"),
        items=dataset.get("n_items", "?"),
        answerable=dataset.get("n_answerable", "?"),
    )
    run_id = run.meta.get("run_id", "")
    config = run.meta.get("config_name", "mvp")
    return f"""<section id="method" aria-labelledby="method-h">
  <h2 id="method-h">{_e(s["method"])}</h2>
  <p>{_e(body)}</p>
  <p>{_e(s["reproduce"])}</p>
  <pre><code>uv sync --all-extras
uv run itarag corpus fetch
uv run itarag run configs/{_e(config)}.yaml</code></pre>
  <p>{_e(s["files"])} <a href="{REPO}/tree/main/results/{_e(run_id)}">results/{_e(run_id)}</a></p>
</section>"""


def _page(run: Run, findings: list[dict[str, Any]], lang: str, prefix: str) -> str:
    s = S[lang]
    dataset = run.meta.get("dataset", {})
    draft = s["draft"].format(
        items=dataset.get("n_items", "?"), answerable=dataset.get("n_answerable", "?")
    )
    alternate = "en/" if lang == "it" else "../"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(s["doc_title"])}</title>
<meta name="description" content="{_e(s["lead"])}">
<meta name="color-scheme" content="light">
<link rel="alternate" hreflang="{s["other_lang_code"]}" href="{alternate}">
<link rel="preload" href="{prefix}assets/fonts/archivo-latin-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="{prefix}assets/icon.svg" type="image/svg+xml">
<style>{CSS.replace("__FONT__", prefix + "assets/fonts/archivo-latin-var.woff2")}</style>
</head>
<body>
<a class="skip" href="#main">{"Vai al contenuto" if lang == "it" else "Skip to content"}</a>
{_masthead(run, lang, prefix)}
<main id="main">
  <div class="opening">
    <div class="opening-text">
      <h1>{_e(s["title"])}</h1>
      <p class="lead">{_e(s["lead"])}</p>
      {_headlines(findings, lang)}
    </div>
    {_departures(run, lang, draft)}
  </div>
  {_findings(findings, lang)}
  {_timetable(run, lang)}
  {_categories(run, lang)}
  {_documents(run, lang)}
  {_costs(run, lang)}
  {_method(run, lang)}
</main>
<footer class="footer"><p>{_e(s["footer"])}</p><p><a href="{REPO}">{_e(s["source"])}</a></p></footer>
</body>
</html>
"""


def build_site(results: Path, out: Path, run_id: str | None = None) -> Path:
    """Write the Italian page to ``out`` and the English one to ``out.parent / 'en' / out.name``."""
    run_dir = results / run_id if run_id else _latest_run(results)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    findings_file = run_dir / "findings.json"
    findings: list[dict[str, Any]] = (
        json.loads(findings_file.read_text(encoding="utf-8")).get("findings", [])
        if findings_file.exists()
        else []
    )
    run = Run(summary, meta)
    root = out.parent
    root.mkdir(parents=True, exist_ok=True)
    out.write_text(_page(run, findings, "it", ""), encoding="utf-8")
    en = root / "en" / out.name
    en.parent.mkdir(parents=True, exist_ok=True)
    en.write_text(_page(run, findings, "en", "../"), encoding="utf-8")
    shutil.copytree(ASSETS, root / "assets", dirs_exist_ok=True)
    return out


CSS = r"""
@font-face {
  font-family: 'Archivo';
  src: url('__FONT__') format('woff2');
  font-weight: 100 900;
  font-stretch: 62% 125%;
  font-display: swap;
}
:root {
  --paper: #ffffff;
  --ink: #111418;
  --ink-2: #4a525c;
  --frame: #16357a;
  --frame-ink: #ffffff;
  --frame-ink-2: #c9d6f0;
  --rule: #c9ced6;
  --rule-strong: #111418;
  --tint: #eaf0fa;
  --marker: #ffd23f;
  --focus: #16357a;
  --face: 'Archivo', system-ui, sans-serif;
  --face-code: ui-monospace, 'SF Mono', Menlo, monospace;
  --measure: 40rem;
  color-scheme: light;
}
*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--face);
  font-size: 1.0625rem;
  line-height: 1.6;
}
::selection { background: var(--marker); color: var(--ink); }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
a { color: var(--frame); text-underline-offset: 3px; text-decoration-thickness: 1px; }
a:hover { text-decoration-thickness: 2px; }
h1, h2, h3 { font-stretch: 75%; line-height: 1.1; margin: 0; text-wrap: balance; }
p { margin: 0; }
.num, td.num { font-variant-numeric: tabular-nums; }
.skip { position: absolute; left: -999px; top: 0; background: var(--marker); color: var(--ink); padding: .5rem 1rem; }
.skip:focus { left: 1rem; z-index: 2; }

/* Masthead: the timetable cover */
.masthead { background: var(--frame); color: var(--frame-ink); }
.masthead-row {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem 2rem;
  max-width: 76rem; margin: 0 auto; padding: 1.25rem 1.5rem .75rem;
}
.wordmark { color: var(--frame-ink); font-weight: 800; font-stretch: 70%; font-size: 1.75rem; text-decoration: none; letter-spacing: -.01em; }
.validity { display: flex; flex-wrap: wrap; gap: .25rem 1.5rem; margin-right: auto; color: var(--frame-ink-2); font-size: .9375rem; }
.validity b { color: var(--frame-ink); font-weight: 600; }
.validity .mark, .masthead a.mark { color: var(--marker); text-decoration: none; margin-left: .15rem; }
.lang { color: var(--frame-ink); font-weight: 600; }
.masthead nav { border-top: 1px solid rgb(255 255 255 / .25); }
.masthead nav ul {
  display: flex; gap: 0; max-width: 76rem; margin: 0 auto; padding: 0 1.5rem;
  list-style: none; overflow-x: auto; scrollbar-width: none;
}
.masthead nav a {
  display: block; padding: .6rem 1rem .6rem 0; margin-right: 1rem; color: var(--frame-ink);
  font-stretch: 85%; font-weight: 600; white-space: nowrap; text-decoration: none;
}
.masthead nav a:hover { text-decoration: underline; }
.masthead :focus-visible { outline-color: var(--marker); }

/* Reading column */
main { max-width: 76rem; margin: 0 auto; padding: 0 1.5rem 4rem; }
.opening-text, main > section:not(.wide) { max-width: var(--measure); }
.opening { padding: 3rem 0 1rem; display: grid; gap: 2.5rem; }
@media (min-width: 1100px) {
  .opening { grid-template-columns: minmax(0, var(--measure)) minmax(20rem, 1fr); gap: 4rem; align-items: start; }
}
h1 { font-size: clamp(2.25rem, 4vw, 3.25rem); font-weight: 800; letter-spacing: -.015em; max-width: 20ch; }

/* First-viewport board: recommended departures */
/* Headed like a station departures board: a blue band, then the rows. */
.departures h2 {
  border: 0; margin: 0; padding: .6rem .75rem;
  background: var(--frame); color: var(--frame-ink); font-size: 1.25rem;
}
.departures table { width: 100%; }
.departures th, .departures td { padding: .55rem .5rem; vertical-align: middle; }
.departures thead th { font-size: .8125rem; font-weight: 600; color: var(--ink-2); }
.departures tbody td.num { font-size: 1.375rem; font-weight: 700; font-stretch: 75%; }
.departures tbody td.num:last-child { font-size: 1rem; font-weight: 500; color: var(--ink-2); }
.departures p { margin-top: .75rem; font-size: .8125rem; color: var(--ink-2); }
.lead { margin-top: 1.25rem; font-size: 1.25rem; line-height: 1.5; color: var(--ink-2); }
.draft {
  display: flex; gap: .75rem; margin-top: 2rem; padding: 1rem 0;
  border-top: 2px solid var(--rule-strong); border-bottom: 1px solid var(--rule);
  font-size: .9375rem; color: var(--ink-2);
}
.mark { font-weight: 700; color: var(--frame); }
.draft .mark { font-size: 1.25rem; line-height: 1.2; }
section { margin-top: 4rem; }
/* Data tables get the width they need; prose sections keep the reading measure. */
main > section#categories, main > section#documents { max-width: 60rem; }
h2 {
  font-size: 1.875rem; font-weight: 750; padding-top: .75rem;
  border-top: 2px solid var(--rule-strong); margin-bottom: 1rem;
}
.intro { color: var(--ink-2); margin-bottom: 1.5rem; }

/* Opening: finding headlines, then the board with its margin notes */
.headlines { list-style: none; margin: 1.75rem 0 0; padding: 0; border-top: 2px solid var(--rule-strong); }
.headlines > li { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: .25rem 1rem; padding: .65rem 0; border-bottom: 1px solid var(--rule); }
.headlines > li > a { color: var(--ink); font-weight: 700; font-stretch: 80%; font-size: 1.125rem; line-height: 1.3; text-decoration: none; flex: 1 1 18rem; }
.headlines > li > a:hover { text-decoration: underline; }
.verdict { margin-top: .75rem; font-size: 1rem; line-height: 1.5; }
.margin-notes { list-style: none; margin: 1.25rem 0 0; padding: .75rem 0 0; border-top: 1px solid var(--rule); font-size: .875rem; color: var(--ink-2); display: grid; gap: .5rem; }
.margin-notes .mark { margin-right: .25rem; }

/* Sections with a margin column: notes live where a timetable puts them */
@media (min-width: 1100px) {
  .with-margin { display: grid; grid-template-columns: minmax(0, var(--measure)) minmax(16rem, 1fr); gap: 4rem; align-items: start; }
  .with-margin .margin { position: sticky; top: 1.5rem; padding-top: 4.5rem; }
}
/* Below the margin breakpoint the legend is shown once, under the timetable. */
@media (max-width: 1099px) { .with-margin .margin { display: none; } }
.legend-title { font-weight: 700; font-stretch: 80%; margin-top: 1.25rem; }
.legend { list-style: none; margin: .5rem 0 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr)); gap: .15rem 1rem; font-size: .875rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.tie-note { margin-top: .75rem; font-size: .9375rem; }
sup.mark { font-size: .75em; margin-left: .1em; }

/* Findings */
.findings { list-style: none; margin: 0; padding: 0; counter-reset: f; }
.finding { padding: 1.5rem 0; border-bottom: 1px solid var(--rule); }
.finding h3 { font-size: 1.375rem; font-weight: 700; margin-bottom: .5rem; }
.finding p + .check { margin-top: .75rem; }
.check { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; font-size: .875rem; color: var(--ink-2); }
.codes { display: flex; flex-wrap: wrap; gap: .375rem; margin: 0; padding: 0; list-style: none; }

/* Train codes: the same everywhere */
.code {
  display: inline-block; padding: 0 .4rem; border: 1.5px solid currentColor; border-radius: 2px;
  font-weight: 700; font-stretch: 70%; font-size: .9375rem; letter-spacing: .03em; line-height: 1.5;
  font-variant-numeric: tabular-nums; text-decoration: none; color: var(--frame);
}
a.code:hover { background: var(--tint); }

/* Tables */
.table-scroll { overflow-x: auto; margin: 0 -1.5rem; padding: 0 1.5rem; }
.table-scroll:focus-visible { outline-offset: -3px; }
table { border-collapse: collapse; font-stretch: 87%; }
th, td { padding: .5rem .75rem; text-align: left; vertical-align: top; }
td.num { text-align: right; }
thead th { font-weight: 700; border-bottom: 2px solid var(--rule-strong); vertical-align: bottom; white-space: nowrap; }
th.num { text-align: right; }
tbody th { font-weight: 600; }
tbody tr { border-bottom: 1px solid var(--rule); }
.strong { font-weight: 800; }
td.best { background: var(--marker); }
.ruled { min-width: 100%; }

/* The timetable */
.timetable { min-width: 56rem; width: 100%; }
.timetable thead th { text-align: right; }
.timetable thead th.corner { text-align: left; }
.timetable thead .code { display: block; margin-left: auto; width: max-content; }
.timetable .sub { display: block; margin-top: .25rem; font-weight: 400; font-size: .75rem; color: var(--ink-2); line-height: 1.3; }
.timetable tbody th, .timetable thead th:first-child {
  position: sticky; left: 0; background: var(--paper); min-width: 13rem; z-index: 1;
}
.timetable tbody th .unit { display: block; font-weight: 400; font-size: .75rem; color: var(--ink-2); }
.timetable tr.ceiling { background: var(--tint); }
.timetable tr.ceiling th { background: var(--tint); }
.timetable tr.lost { border-top: 2px solid var(--rule-strong); color: var(--ink-2); }
.timetable tr.group th { position: static; background: var(--paper); padding-top: 1rem; font-weight: 700; font-stretch: 80%; border-bottom: 1px solid var(--rule-strong); }
/* Vertical hairlines between trains: the timetable's own grid */
.timetable td, .timetable thead th:not(.corner) { border-left: 1px solid var(--rule); }
.timetable td:target { outline: 3px solid var(--frame); outline-offset: -3px; background: var(--tint); }
.line-strip { margin: 0 0 .75rem; padding: .4rem .75rem; background: var(--frame); color: var(--frame-ink); font-weight: 600; font-stretch: 80%; font-size: .9375rem; }
.timetable td.best { box-shadow: inset 0 0 0 2px var(--ink); }


.notes { list-style: none; margin: 1rem 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: .5rem 1.75rem; font-size: .875rem; color: var(--ink-2); }
.notes .hl { display: inline-block; width: 1.75rem; height: .9rem; background: var(--marker); vertical-align: -.1rem; margin-right: .25rem; }


pre {
  margin: 1rem 0; padding: 1rem 1.25rem; overflow-x: auto;
  background: var(--tint); border-top: 2px solid var(--frame);
  font-family: var(--face-code); font-size: .875rem; line-height: 1.6;
}
#method p + p { margin-top: 1rem; }

.footer { background: var(--frame); color: var(--frame-ink-2); }
.footer p { max-width: 76rem; margin: 0 auto; padding: 1rem 1.5rem 0; font-size: .875rem; }
.footer p:last-child { padding-bottom: 1.5rem; }
.footer a { color: var(--frame-ink); }

@media (max-width: 640px) {
  .masthead-row { padding: 1rem 1rem .5rem; }
  .masthead nav ul, main { padding-left: 1rem; padding-right: 1rem; }
  .table-scroll { margin: 0 -1rem; padding: 0 1rem; }
  .opening { padding-top: 2.25rem; }
  .lead { font-size: 1.125rem; }
  .timetable tbody th, .timetable thead th:first-child { min-width: 9.5rem; }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
@media print {
  .masthead, .footer { background: none; color: var(--ink); }
  .masthead a, .footer a, .validity b { color: var(--ink); }
  .masthead nav, .skip { display: none; }
  .table-scroll { overflow: visible; }
}
"""
