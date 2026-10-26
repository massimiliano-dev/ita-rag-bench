# Results

One folder per run (`itarag run --run-id <id>`):

- `run.json`: configuration (and its sha256), dataset and corpus hashes, status counts, parser
  statistics (time, failures, near-empty pages), environment (Python, platform, package versions,
  MPS/CUDA availability), wall time.
- `summary.json`: one row per (parser, chunker, embedding, retriever) with overall metrics,
  per-category metrics, per-document-characteristic metrics, per-document metrics, chunk
  statistics, chunker parameters, embedding model description (model id, pinned revision,
  prefixes, device) and timings (indexing seconds, mean query latency in ms).
- `per_question/<parser>__<chunker>__<embedding>__<retriever>.jsonl`: rank of the first relevant
  chunk, recall@1/5/10 and nDCG@10 per question, plus the ids of the top-3 chunks.

`senza_risposta` questions are excluded from all metrics and only counted (`run.json`).
Indexing times on cached runs report the time measured when the embedding cache entry was
created; query latency is re-measured on every run (batched over all queries, after a warm-up,
reported as mean ms per query).
The leaderboard (`site/index.html`) is built from the latest run with `itarag site`.
