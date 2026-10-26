"""Command line interface: ``itarag``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="ita-rag-bench: end-to-end Italian RAG benchmark.", no_args_is_help=True)
corpus_app = typer.Typer(help="Corpus management.", no_args_is_help=True)
dataset_app = typer.Typer(help="Question dataset tools.", no_args_is_help=True)
app.add_typer(corpus_app, name="corpus")
app.add_typer(dataset_app, name="dataset")

ConfigOpt = Annotated[Path, typer.Option("--config", "-c", help="YAML config")]
DEFAULT_CONFIG = Path("configs/mvp.yaml")


@corpus_app.command("fetch")
def corpus_fetch(
    manifest: Annotated[Path, typer.Option(help="Manifest YAML")] = Path(
        "corpus/normativo/manifest.yaml"
    ),
    pdf_dir: Annotated[Path, typer.Option(help="Where PDFs are stored")] = Path(
        "corpus/normativo/pdf"
    ),
    only: Annotated[list[str] | None, typer.Option(help="Only these document ids")] = None,
    force: Annotated[bool, typer.Option(help="Re-download even if cached")] = False,
    bootstrap: Annotated[
        bool, typer.Option(help="Maintainers only: record sha256 for new documents")
    ] = False,
) -> None:
    """Download (politely) and verify the corpus PDFs listed in the manifest."""
    from itaragbench.fetch import FetchError, fetch_corpus
    from itaragbench.manifest import load_manifest, save_manifest

    m = load_manifest(manifest)
    try:
        results = fetch_corpus(m, pdf_dir, only=only, force=force, bootstrap=bootstrap)
    except FetchError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(1) from exc
    if bootstrap:
        save_manifest(m, manifest)
    typer.echo(f"{len(results)} documents verified.")


@corpus_app.command("info")
def corpus_info(
    manifest: Annotated[Path, typer.Option()] = Path("corpus/normativo/manifest.yaml"),
) -> None:
    """Print the corpus documents and their characteristics."""
    from itaragbench.manifest import load_manifest

    m = load_manifest(manifest)
    for d in m.documents:
        c = d.characteristics
        a, b = d.page_range
        typer.echo(
            f"{d.id:22s} pp.{a:>3}-{b:<3} {c.length:6s} tables={c.has_tables!s:5s} "
            f"{c.structure:14s} {c.pdf_quality:7s} {d.act}"
        )


@app.command()
def parse(
    config: ConfigOpt = DEFAULT_CONFIG,
    parser: Annotated[list[str] | None, typer.Option(help="Only these parsers")] = None,
    doc: Annotated[list[str] | None, typer.Option(help="Only these document ids")] = None,
) -> None:
    """Parse the corpus with the configured parsers (sandboxed, cached)."""
    from itaragbench.cache import load_or_parse
    from itaragbench.config import load_config
    from itaragbench.manifest import load_manifest
    from itaragbench.runner import verify_corpus

    cfg = load_config(config)
    m = load_manifest(cfg.manifest)
    docs = [d for d in m.documents if doc is None or d.id in doc]
    verify_corpus(docs, cfg.pdf_dir)
    for spec in cfg.parsers:
        if parser is not None and spec.name not in parser:
            continue
        for d in docs:
            pd = load_or_parse(cfg.cache_dir, cfg.pdf_dir, spec, d, typer.echo)
            typer.echo(f"{spec.name:8s} {d.id:22s} {len(pd.text):>8} chars {pd.seconds:7.1f}s")


@app.command()
def run(
    config: ConfigOpt = DEFAULT_CONFIG,
    split: Annotated[str, typer.Option(help="dev | test | all")] = "all",
    run_id: Annotated[str | None, typer.Option(help="Results sub-folder name")] = None,
    parser: Annotated[list[str] | None, typer.Option(help="Only these parsers")] = None,
    embedding: Annotated[list[str] | None, typer.Option(help="Only these embeddings")] = None,
) -> None:
    """Run the benchmark grid and write results/<run-id>/."""
    from itaragbench.config import load_config
    from itaragbench.runner import run_benchmark

    cfg = load_config(config)
    run_benchmark(
        cfg,
        split=split,
        run_id=run_id,
        only_parsers=parser,
        only_embeddings=embedding,
        log=typer.echo,
    )


@app.command()
def site(
    results: Annotated[Path, typer.Option(help="Results root")] = Path("results"),
    out: Annotated[Path, typer.Option(help="Output HTML")] = Path("site/index.html"),
    run_id: Annotated[str | None, typer.Option(help="Run to publish (default: latest)")] = None,
) -> None:
    """Build the static leaderboard from results JSON."""
    from itaragbench.site import build_site

    path = build_site(results, out, run_id)
    typer.echo(f"wrote {path}")


@dataset_app.command("validate")
def dataset_validate(
    config: ConfigOpt = DEFAULT_CONFIG,
    check_evidence: Annotated[
        bool, typer.Option(help="Check evidence spans against parsed text (needs cache)")
    ] = True,
    dataset: Annotated[Path | None, typer.Option(help="Override the dataset path")] = None,
) -> None:
    """Validate schema and (optionally) that every evidence span exists in the source text."""
    from itaragbench.config import load_config
    from itaragbench.validate import validate_dataset

    cfg = load_config(config)
    if dataset is not None:
        cfg.dataset = dataset
    errors = validate_dataset(cfg, check_evidence=check_evidence, log=typer.echo)
    if errors:
        for e in errors:
            typer.echo(f"ERROR {e}", err=True)
        raise typer.Exit(1)
    typer.echo("dataset OK")


@dataset_app.command("stats")
def dataset_stats(
    path: Annotated[Path, typer.Option()] = Path("datasets/normativo/questions.jsonl"),
) -> None:
    """Counts per split, category, status and document."""
    from collections import Counter

    from itaragbench.dataset import load_items

    items = load_items(path)
    typer.echo(f"items: {len(items)}")
    for label, key in (
        ("split", lambda it: it.split),
        ("category", lambda it: it.category),
        ("status", lambda it: it.status),
        ("split/category", lambda it: f"{it.split}/{it.category}"),
    ):
        c = Counter(key(it) for it in items)
        typer.echo(f"{label}: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
    docs = Counter(r.doc_id for it in items for r in it.references)
    typer.echo("references per document: " + ", ".join(f"{k}={v}" for k, v in sorted(docs.items())))


@app.command()
def review(
    path: Annotated[Path, typer.Option()] = Path("datasets/normativo/questions.jsonl"),
    config: ConfigOpt = DEFAULT_CONFIG,
    reviewer: Annotated[str | None, typer.Option(help="Your name or handle")] = None,
    status: Annotated[str, typer.Option(help="Review items with this status")] = "draft",
    split: Annotated[str | None, typer.Option(help="dev | test")] = None,
    category: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Interactive terminal review: accept / edit / reject draft questions."""
    from itaragbench.review import review_loop

    review_loop(path, config, reviewer=reviewer, status=status, split=split, category=category)


if __name__ == "__main__":
    app()
