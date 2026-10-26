# ita-rag-bench

[![CI](https://github.com/massimiliano-dev/ita-rag-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/massimiliano-dev/ita-rag-bench/actions/workflows/ci.yml)
![license: MIT](https://img.shields.io/badge/code-MIT-blue) ![data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-green)

**An end-to-end RAG benchmark on real Italian domain documents.** It scores the *whole* retrieval
pipeline on the original PDFs, not just the embedding model:

```
official PDF ──► parser ──► chunker ──► embedding ──► retrieval (dense / BM25 / hybrid) ──► metrics
                (pypdf,     (fixed,     (e5-base,     (generation and LLM judging: later)
                 PyMuPDF,    recursive,  bge-m3)
                 Docling)    structure)
```

> ⚠️ **Results are on DRAFT questions.** The 150 questions were drafted with machine assistance and
> have **not yet been validated by a human** (`status: draft`). Single domain (Italian normative
> acts), 20 documents. Read the numbers as a first signal, not as a leaderboard to optimise.

## Why

Existing evaluations cover other layers of the stack:

- **MMTEB** (Enevoldsen et al., *MMTEB: Massive Multilingual Text Embedding Benchmark*, ICLR 2025,
  [arXiv:2502.13595](https://arxiv.org/abs/2502.13595)) evaluates **embedding models** on 500+ tasks
  in 250+ languages, filterable by language and domain. Its inputs are already-clean text.
- **ITA-Bench** (Moroni, Conia, Martelli, Navigli, *Towards a More Comprehensive Evaluation for
  Italian LLMs*, CLiC-it 2024, [ACL Anthology](https://aclanthology.org/2024.clicit-1.67/)) and
  **ItaEval** (Attanasio et al., *ItaEval and TweetyIta: A New Extensive Benchmark and
  Efficiency-First Language Model for Italian*, CLiC-it 2024,
  [ACL Anthology](https://aclanthology.org/2024.clicit-1.6/)) evaluate **LLMs** (understanding,
  knowledge, bias), not retrieval-augmented pipelines.
- Noviello & Tamburini (*Exploring Text-Embedding Retrieval Models for the Italian Language*,
  CLiC-it 2024, [ACL Anthology](https://aclanthology.org/2024.clicit-1.73/)) provide Italian
  retrieval data and models.

None of them starts from the PDF. The thesis this project wants to **test** (not assume): *in
production Italian RAG the problem is rarely the embedding; it is PDF parsing and chunking that
split a comma in half or lose a table row.*

## What is in the MVP

| | |
|---|---|
| Domain | `normativo`: 20 Italian acts (1990–2025), original issue PDFs of the *Gazzetta Ufficiale* |
| Questions | 150 in Italian (dev 50 / test 100): fattuale 87, multi_hop 20, tabellare 22, temporale 6, senza_risposta 15 |
| Parsers | `pypdf` (BSD), `pymupdf` (**AGPL-3.0**, optional extra), `docling` (MIT, optional extra; layout + TableFormer, OCR only for scanned pages) |
| Chunkers | `fixed` (200 whitespace tokens, 40 overlap), `recursive` (1200 chars, separators, 150 overlap), `structure` (Libro/Titolo/Capo/Articolo/comma regex, 1500-char cap, long articles split at comma boundaries with the article heading repeated) |
| Embeddings | `intfloat/multilingual-e5-base` (`query: ` / `passage: ` prefixes), `BAAI/bge-m3` (dense), both pinned by commit, `trust_remote_code=False`, Apple MPS when available |
| Retrieval | dense (exact cosine in numpy), BM25 (`bm25s`, Italian stopwords + Snowball stemmer), hybrid (reciprocal rank fusion, k=60) |
| Metrics | recall@1/5/10, MRR@10, nDCG@10 overall, per category and per document characteristic; chunks per doc, chunk length, indexing time, query latency |

### Corpus

| id | act | pages | length | tables | structure | PDF |
|---|---|---|---|---|---|---|
| `dm-2023-tasso-legale` | D.M. 29 novembre 2023 | 1 | short | no | other | native |
| `dm-2024-tasso-legale` | D.M. 10 dicembre 2024 | 1 | short | no | other | native |
| `dpr-2013-62` | D.P.R. 16 aprile 2013, n. 62 | 10 | medium | no | articoli-commi | native |
| `dpr-2023-81` | D.P.R. 13 giugno 2023, n. 81 | 4 | short | no | articoli-commi | native |
| `dlgs-2013-33` | D.Lgs. 14 marzo 2013, n. 33 | 37 | long | yes | capitoli | native |
| `l-2012-190` | L. 6 novembre 2012, n. 190 | 24 | medium | no | articoli-commi | native |
| `dlgs-2023-24` | D.Lgs. 10 marzo 2023, n. 24 | 33 | long | no | capitoli | native |
| `dlgs-2023-36` | D.Lgs. 31 marzo 2023, n. 36 | 254 | long | yes | capitoli | native |
| `dpr-2011-151` | D.P.R. 1 agosto 2011, n. 151 | 42 | long | yes | articoli-commi | native |
| `dpcm-2013-159` | D.P.C.M. 5 dicembre 2013, n. 159 | 26 | medium | yes | articoli-commi | native |
| `l-2025-132` | L. 23 settembre 2025, n. 132 | 29 | medium | no | capitoli | native |
| `dlgs-2024-138` | D.Lgs. 4 settembre 2024, n. 138 | 58 | long | yes | capitoli | native |
| `dlgs-2001-231` | D.Lgs. 8 giugno 2001, n. 231 | 23 | medium | no | capitoli | native |
| `l-2013-4` | L. 14 gennaio 2013, n. 4 | 6 | short | no | articoli-commi | native |
| `dlgs-2005-82` | D.Lgs. 7 marzo 2005, n. 82 | 44 | long | no | capitoli | native |
| `dm-2014-55` | D.M. 10 marzo 2014, n. 55 | 19 | medium | yes | capitoli | native |
| `dm-2022-147` | D.M. 13 agosto 2022, n. 147 | 14 | medium | yes | articoli-commi | native |
| `dlgs-2018-101` | D.Lgs. 10 agosto 2018, n. 101 | 44 | long | no | capitoli | native |
| `l-2017-81` | L. 22 maggio 2017, n. 81 | 20 | medium | no | capitoli | native |
| `l-1990-241` | L. 7 agosto 1990, n. 241 | 11 | medium | no | capitoli | scanned |

Licences and terms: [`corpus/LICENSES.md`](corpus/LICENSES.md). PDFs are **not** committed;
`itarag corpus fetch` downloads them politely (HTTPS, allowlisted host, ≥3 s between requests,
descriptive User-Agent) and verifies their SHA-256 against the manifest.

### Gold references are chunker independent

Each answerable question cites `doc_id`, `article`, `comma`, `page` and one or more **verbatim
evidence spans**. A retrieved chunk is relevant if it contains a span after normalisation (NFKC,
quotes and dashes unified, de-hyphenation across line breaks, markdown stripped, whitespace and case
folded) or, failing that, if an in-order token alignment covers **≥ 85 %** of the span (tolerating
running headers and page numbers inserted inside it). Recall counts covered references; nDCG gives
gain only to chunks that cover a *new* reference, so overlapping chunks cannot inflate scores.
`senza_risposta` questions are excluded from these metrics and only counted: abstention will be
measured once generation exists.

## First findings

Run `2026-10-26-mvp` (Apple M5, 32 GB, MPS; all 150 questions, of which 135 answerable; full
numbers in [`results/2026-10-26-mvp/`](results/2026-10-26-mvp/) and in the leaderboard
[`site/index.html`](site/index.html)).

**Caveats first.** The questions are **drafts** (not human-validated) and were drafted by reading the
PyMuPDF extraction, which may favour PyMuPDF. One domain, 20 documents, a single run. With 135
questions a single configuration's recall@5 has a 95 % bootstrap interval of about ±7 points, so
differences of a few points between two rows are noise. `tabellare` (22) and especially `temporale`
(6) are small.

Dense retrieval, recall@5 / MRR@10 (hybrid = dense + BM25 with RRF):

| parser | chunker | e5-base R@5 | e5-base MRR | bge-m3 R@5 | bge-m3 MRR | hybrid bge-m3 R@5 | ceiling* |
|---|---|---|---|---|---|---|---|
| pypdf | fixed | 0.533 | 0.508 | 0.656 | 0.542 | 0.723 | 0.865 |
| pypdf | recursive | 0.568 | 0.459 | 0.653 | 0.533 | 0.669 | 0.840 |
| pypdf | structure | 0.651 | 0.583 | 0.732 | 0.641 | 0.769 | 0.890 |
| pymupdf | fixed | 0.622 | 0.576 | 0.752 | 0.648 | 0.836 | 0.939 |
| pymupdf | recursive | 0.616 | 0.497 | 0.723 | 0.585 | 0.723 | 0.908 |
| pymupdf | structure | 0.702 | 0.614 | 0.773 | 0.672 | 0.802 | 0.939 |
| docling | fixed | 0.662 | 0.529 | 0.735 | 0.608 | 0.754 | 0.896 |
| docling | recursive | 0.596 | 0.520 | 0.673 | 0.621 | 0.728 | 0.896 |
| docling | structure | 0.714 | 0.618 | 0.780 | 0.670 | 0.784 | 0.902 |

\* *ceiling*: share of gold references fully contained in at least one chunk, i.e. the best any
retriever could do after parsing and chunking. BM25 alone: R@5 0.616–0.774 (best: PyMuPDF + fixed,
0.774).

1. **The thesis holds only partly.** Averaged over the other factors (dense, recall@5), moving from
   e5-base to bge-m3 is worth **+9.0 points** (paired bootstrap 95 % CI +5.0 to +13.5), moving from
   the recursive to the structure-aware chunker **+8.7** (+4.6 to +13.2), and from pypdf to PyMuPDF
   **+6.6** (+3.0 to +10.2). On average the embedding matters as much as chunking and more than the
   parser. In this data the embedding is not a minor factor.
2. **Parsing failures are rare but total.** Two documents decide most of the parser gap. For
   D.Lgs. 231/2001 (2001 typesetting), pypdf and Docling both emit glyph codes such as `/99/41 /105/108`
   instead of text: recall@5 is **0.00** with both and **0.90** with PyMuPDF. The 1990 issue
   (L. 241/1990) is a scan: pypdf and PyMuPDF get **0.00**, Docling with OCR **0.71**. Without these
   two documents the three parsers are within 4 points (0.68 / 0.71 / 0.73). pypdf also warns that
   it needs `fontTools`; installing it did not fix the 2001 fonts.
3. **Parsing + chunking set a hard ceiling.** Before any embedding, 6–16 % of the gold references
   are not contained in any single chunk: ceiling 0.84–0.89 with pypdf, 0.91–0.94 with PyMuPDF and
   0.90 with Docling. For the best dense configuration (PyMuPDF + structure + bge-m3, R@10 0.832,
   ceiling 0.939) about a third of the misses at 10 are unreachable. The structure-aware chunker
   raises the ceiling for single-comma questions (0.954 vs 0.908 for recursive with PyMuPDF) and
   is the best chunker for every retriever. It lowers the ceiling for table questions (0.773 vs
   0.864). Our guess, not yet checked case by case: the recursive fallback inside long annexes
   separates a row label from its value.
4. **Lexical retrieval is a strong baseline for legal Italian.** BM25 (Italian stemming and
   stopwords) on PyMuPDF + fixed chunks reaches R@5 **0.774**, on a par with the best dense
   configuration (0.780) and above every e5-base configuration. Hybrid RRF is the best overall:
   **0.836** (95 % CI 0.78–0.90) with PyMuPDF + fixed + bge-m3. For table questions BM25 does
   better than dense (0.73 vs 0.50 with PyMuPDF). Docling's Markdown tables did *not* help
   retrieval of table cells here (hybrid `tabellare` 0.54 vs 0.67 with PyMuPDF).
5. **Costs differ by orders of magnitude.** Parsing 700 pages took 5.9 s with PyMuPDF, 7.9 s with
   pypdf and 513 s with Docling (one process per document, model loading included). Indexing about
   3.5k chunks took about 80 s with e5-base and about 250 s with bge-m3 on MPS. Batched query
   latency was about 3 ms vs 9 ms per query. Docling crashed once (segfault, exit -11) on one
   document and succeeded on retry.

## Quick start

```bash
uv python install 3.12
uv sync --all-extras            # or plain `uv sync` for the light install (pypdf only)
uv run itarag corpus fetch      # ~90 MB, polite, sha256-verified
uv run itarag parse             # sandboxed parsing, cached as JSON
uv run itarag run --split dev   # writes results/<run-id>/
uv run itarag site              # builds site/index.html from the latest results
```

Other commands: `itarag corpus info`, `itarag dataset stats`, `itarag dataset validate`
(schema + every evidence span present in the official text), `itarag review` (terminal UI to
accept / edit / reject draft questions; writes `validated_by`/`validated_at`).

Everything is configured in [`configs/mvp.yaml`](configs/mvp.yaml). `configs/smoke.yaml` runs offline
with a fake embedder.

## Validating the questions (help wanted)

```bash
uv run itarag review --reviewer <your-handle> --split dev
```

The UI shows the question, the draft answer, the evidence spans and the surrounding official text of
the cited page. Until a meaningful share of questions is `validated`, every number in this repository
is about draft data.

## Repository layout

```
src/itaragbench/   fetch, parsing (sandboxed worker), chunking, embedding, retrieval, matching,
                   metrics, runner, review, site, cli
corpus/normativo/  manifest.yaml (committed), pdf/ (git-ignored)
datasets/          questions.jsonl (CC BY 4.0)
configs/           mvp.yaml, smoke.yaml
results/<run-id>/  run.json, summary.json, per_question/*.jsonl
site/index.html    static leaderboard (no external JS)
```

## Security and licences

Untrusted PDFs are parsed in a subprocess with a timeout, a memory watchdog and a scrubbed
environment; no pickle is used for caches; actions are pinned by SHA; dependencies are locked and
audited. See [`SECURITY.md`](SECURITY.md).

- Code: **MIT** ([`LICENSE`](LICENSE)). Datasets: **CC BY 4.0** ([`datasets/LICENSE.md`](datasets/LICENSE.md)).
- **PyMuPDF is AGPL-3.0**: it is an optional extra (`[pymupdf]`) and is never required by the
  default install. Docling (MIT) and sentence-transformers/torch are optional extras too.
- Source texts: official acts of the Italian State (art. 5 L. 633/1941), attributed to the
  *Gazzetta Ufficiale della Repubblica Italiana*. They are not authentic copies.

## Roadmap

Human validation of the questions; more domains (technical documentation, public tenders);
generation with abstention on `senza_risposta`; LLM-as-judge with human agreement checks;
point-in-time (multi-version) questions from Normattiva open data; more parsers and chunkers.

## Citation

See [`DATASET_CARD.md`](DATASET_CARD.md). Contributions welcome: [`CONTRIBUTING.md`](CONTRIBUTING.md).
