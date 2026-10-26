# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/massimiliano-dev/ita-rag-bench/security/advisories/new)
rather than in a public issue. We aim to acknowledge reports within 7 days.

## Threat model and mitigations

### PDFs are untrusted input
Benchmark PDFs come from the internet and parsers are large native-code libraries.

- Every parser runs in a **separate process** (`python -I -m itaragbench.parsing.worker`) started with
  an **allowlisted environment** (no tokens, API keys or cloud credentials are passed), `stdin`
  closed, a throwaway working directory and its own process group.
- **Timeout** per document and **memory limit**: `RLIMIT_AS`/`RLIMIT_DATA` where the OS enforces
  them (Linux) plus a parent-side watchdog that polls the worker RSS and kills the whole process
  group when it exceeds `max_mb` (macOS ignores `RLIMIT_AS`). Limits are set per parser in
  `configs/*.yaml`. A crash is retried once; a timeout or memory kill is recorded as a parser
  failure, not retried.
- Parsers are only asked for text/layout. Embedded JavaScript, attachments, links and forms are never
  executed or followed. Docling runs with `enable_remote_services = False`.
- **No pickle** in this project: caches are JSON (parsed text) and NPY loaded with
  `allow_pickle=False` (embeddings); results are JSON/JSONL.

### Downloads
- `itarag corpus fetch`: HTTPS only, host allowlist (also enforced on redirects), Content-Type and
  `%PDF-` magic checks, size cap, polite rate limit (>= 2 s, manifest uses 3 s), and **SHA-256
  verification** against the committed manifest. The benchmark refuses to run on a PDF whose hash
  does not match.

### Supply chain
- Dependencies are locked in `uv.lock`; CI installs with `uv sync --locked` and runs `pip-audit`
  against the full lock file (optional extras included).
- GitHub Actions are **pinned by commit SHA**; workflows default to `permissions: contents: read`;
  checkout uses `persist-credentials: false`. Dependabot watches `uv` and `github-actions`.
  CodeQL scans Python and workflow files.
- Embedding models are pinned to a full **commit hash** and loaded with `trust_remote_code=False`.
  `BAAI/bge-m3` publishes its weights only as `pytorch_model.bin` (a pickle container): it is
  loaded by `transformers` through `torch.load(weights_only=True)`, which refuses arbitrary
  objects. If you prefer, swap in a safetensors-only model in your config.
- Docling downloads its layout/table models from Hugging Face on first use
  (`docling-project/docling-layout-heron`, `docling-project/docling-models`, Apache-2.0 /
  CDLA-Permissive-2.0); RapidOCR ships its default ONNX models inside the wheel and verifies any
  additional download by SHA-256. Run with `HF_HUB_OFFLINE=1` once the caches are warm.
- CI never downloads models or PDFs (fake embedder + generated PDF fixture).

### Licences
- Code: MIT. Data in `datasets/`: CC BY 4.0. Source texts: see `corpus/LICENSES.md`.
- **PyMuPDF is AGPL-3.0** and Docling pulls large third-party stacks: both are optional extras
  (`[pymupdf]`, `[docling]`) and are not needed for the default install. If you distribute a product
  that bundles PyMuPDF, AGPL obligations apply to you.

### Secrets
- The MVP needs **no API keys**. When LLM generation/judging is added, keys will be read only from
  environment variables, never from files in the repository; `.env*` files are git-ignored and are
  never passed to parser subprocesses.
