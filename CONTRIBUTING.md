# Contributing

Thanks for helping! Discussions and proposals in Italian or English are both welcome.

## Setup

```bash
uv python install 3.12
uv sync                          # light install (pypdf, BM25, fake embedder): enough for tests
uv sync --all-extras             # + PyMuPDF (AGPL), Docling, sentence-transformers/torch
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

Before opening a PR: all four commands green, no new dependency without a licence check, no PDFs,
model weights, caches or secrets committed.

## Add a parser

1. Write a backend in `src/itaragbench/parsing/backends.py`: `fn(pdf, first, last, options) ->
   list[(page_no, text)]` with **local imports** (heavy libraries must not be imported by the
   default install). Register it in `BACKENDS` with its distribution name (used for versioning).
2. If it is heavy or has a restrictive licence, add it as an optional extra in `pyproject.toml` and
   document the licence in the README and `SECURITY.md`.
3. Add it to a config under `parsers:` with `timeout_s` and `max_mb`. It will run in the sandboxed
   worker automatically; never parse PDFs in-process.
4. Never execute embedded content, never enable network access from the parser.

## Add a chunker

1. Implement the `Chunker` protocol (`name`, `chunk(ParsedDocument) -> list[Chunk]`, `params()`) in
   `src/itaragbench/chunking/`. Build chunks from character spans with `spans_to_chunks` so page
   numbers are computed consistently.
2. Register it in `make_chunker` and add unit tests (boundaries, page mapping, size limits).

## Add an embedding model

1. Add an entry under `embeddings:` in a config with `model`, a **full 40-character commit**
   `revision`, the model's required prefixes (`query_prefix`, `passage_prefix`) and
   `max_seq_length`. `trust_remote_code` is always `False`; models that need remote code are not
   accepted.
2. Check the model licence and that weights are available as safetensors where possible.

## Add a domain (e.g. technical docs, tenders)

1. **Licences first**: research the source terms, write them (with URLs and date) in
   `corpus/LICENSES.md`. Prefer sources that allow reuse; respect robots rules and bulk-download
   restrictions; never commit the PDFs.
2. Create `corpus/<domain>/manifest.yaml` (see the normativo one): id, title, official URL, source,
   licence, page range, characteristics labels. Add the host to `allowed_hosts`. Run
   `itarag corpus fetch --manifest ... --bootstrap` once to record hashes, then review them.
3. Write questions in `datasets/<domain>/questions.jsonl` following the schema in
   `DATASET_CARD.md`: chunker-independent references with verbatim evidence spans,
   `status: draft`, a dev/test split, ~10% `senza_risposta`. Run `itarag dataset validate`.
4. Have the questions **reviewed by a human** with `itarag review` before reporting results as
   validated.

## Review questions

```bash
uv run itarag review --reviewer <your-handle> --split dev
```

Accept, edit (opens `$EDITOR` on the JSON) or reject; decisions are saved after every item.
