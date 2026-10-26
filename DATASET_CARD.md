---
language:
  - it
license: cc-by-4.0
pretty_name: ita-rag-bench (normativo)
task_categories:
  - question-answering
  - text-retrieval
tags:
  - rag
  - retrieval
  - italian
  - legal
  - pdf-parsing
size_categories:
  - n<1K
---

# ita-rag-bench — normativo (DRAFT)

> **Status: draft.** All 150 items were written with machine assistance ("claude (assisted)") from
> the parsed official text and have **not yet been validated by a human** (`status: draft`,
> `validated_by: null`). Do not use them as ground truth for high-stakes conclusions until they are
> reviewed with `itarag review`. This card is prepared for a future Hugging Face upload; nothing has
> been uploaded. Before uploading, export one file per split (the `split` field) and add a
> `configs:` block pointing to them.

## Summary

Questions in Italian about 20 Italian normative acts (laws, legislative decrees, presidential and
ministerial decrees, 1990–2025), designed to evaluate **end-to-end retrieval** over the original PDFs
of the *Gazzetta Ufficiale*: PDF parsing, chunking, embedding and retrieval. Gold references are
**chunker independent** (document, article, comma, page and verbatim evidence spans), so any
pipeline can be scored.

## Composition

| split | fattuale | multi_hop | tabellare | temporale | senza_risposta | total |
|---|---|---|---|---|---|---|
| dev | 29 | 7 | 7 | 2 | 5 | 50 |
| test | 58 | 13 | 15 | 4 | 10 | 100 |
| all | 87 | 20 | 22 | 6 | 15 | 150 |

- `fattuale`: answer in one comma; `multi_hop`: two articles or two acts (11 cross-document);
  `tabellare`: answer in an annex table cell; `temporale`: which value/rule applies at a date (only 6:
  the corpus holds original versions, so point-in-time questions are limited to amending acts and
  entry-into-force rules; a proper multi-version setting is future work); `senza_risposta`: plausible
  in-domain questions not answerable from the corpus (abstention will be measured once generation is
  added).
- Documents and their characteristics (length, tables, structure, native vs scanned) are listed in
  `corpus/normativo/manifest.yaml`.

## Schema (one JSON object per line)

```json
{
  "id": "norm-001", "split": "dev|test",
  "category": "fattuale|multi_hop|tabellare|temporale|senza_risposta",
  "question": "...", "answer": "...",
  "references": [{"doc_id": "dlgs-2023-24", "article": "6", "comma": "2", "page": 12,
                  "evidence": ["verbatim span from the official text"], "match": "any|all"}],
  "status": "draft|validated|rejected", "generated_by": "claude (assisted)",
  "validated_by": null, "validated_at": null, "review_notes": null, "tags": ["deep_comma"]
}
```

`page` is the physical page of the issue PDF. `match: all` (used for table rows) means every span
(e.g. row label and value) must be in the same retrieved chunk.

## Relevance and metrics

A retrieved chunk is relevant to a reference if, after normalisation (Unicode NFKC, quotes/dashes
unified, de-hyphenation across line breaks, markdown stripped, whitespace collapsed, case folded),
it contains an evidence span; otherwise if an in-order token alignment covers at least **85%** of the
span tokens (tolerates running headers and page numbers inserted inside a span). Metrics: recall@1/5/10
(fraction of references covered), MRR@10, nDCG@10 with evidence-level gains.

## Construction

1. Source PDFs selected for variety (see `corpus/LICENSES.md`), downloaded politely and hashed.
2. Text extracted with PyMuPDF (Docling OCR for the scanned 1990 issue, checked against page images).
3. Questions, answers and evidence spans drafted with Claude; spans copied verbatim from the text,
   with official accents restored where old typesetting broke them; each span automatically
   verified to exist on the stated page in at least one parser's output (`itarag dataset validate`).
4. **Pending**: human validation.

## Known limitations

- Draft quality; single domain; 20 documents; Italian only.
- Original published versions of acts, not consolidated texts: several provisions have since been
  amended or repealed. Answers are correct with respect to the corpus, not necessarily current law.
- Short table values (e.g. "5.400,00") make `match: all` checks partly lexical.
- Questions were written by reading PyMuPDF output, which may slightly favour its text layout.

## Licence and attribution

CC BY 4.0. Evidence spans quote official acts of the Italian State (not protected by copyright,
art. 5 L. 633/1941), source: *Gazzetta Ufficiale della Repubblica Italiana*. Quoted texts are not
authentic copies; the only authentic text is the one published in the Gazzetta Ufficiale.

## Citation

```bibtex
@misc{polce2026itaragbench,
  author = {Polce, Massimiliano},
  title  = {ita-rag-bench: an end-to-end RAG benchmark on Italian domain documents},
  year   = {2026},
  url    = {https://github.com/massimiliano-dev/ita-rag-bench}
}
```
