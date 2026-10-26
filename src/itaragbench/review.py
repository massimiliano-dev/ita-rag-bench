"""Terminal review UI for draft questions (accept / edit / reject).

The reviewer sees the question, the draft answer, every evidence span and the surrounding
text of the cited page(s), extracted from the official PDF (best available cached parser).
Decisions are written back to the JSONL file after every item (atomic replace).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from itaragbench.config import load_config
from itaragbench.dataset import Item, item_from_json, load_items, save_items, schema_errors
from itaragbench.manifest import load_manifest
from itaragbench.matching import normalize
from itaragbench.validate import cached_parses, page_window

PARSER_PREFERENCE = ("pymupdf", "docling", "pypdf")
BOLD, YEL, DIM, RST = "\033[1m", "\033[33m", "\033[2m", "\033[0m"


def _context(cfg_path: Path, item: Item, width: int = 1600) -> list[str]:
    cfg = load_config(cfg_path)
    blocks: list[str] = []
    for ref in item.references:
        parses = cached_parses(cfg, ref.doc_id)
        name = next((p for p in PARSER_PREFERENCE if p in parses and parses[p].text.strip()), None)
        if name is None:
            blocks.append(f"[{ref.doc_id} p.{ref.page}] no cached parse; run `itarag parse`")
            continue
        text = page_window(parses[name], ref.page, radius=0)
        low = normalize(text)
        snippet = text
        for ev in ref.evidence:
            key = normalize(ev)[:40]
            pos = low.find(key)
            if pos != -1:
                start = max(0, pos - width // 2)
                snippet = " ".join(text.split())[start : start + width]
                break
        else:
            snippet = " ".join(text.split())[:width]
        for ev in ref.evidence:
            snippet = snippet.replace(ev, f"{YEL}{ev}{RST}")
        blocks.append(f"{DIM}[{ref.doc_id} p.{ref.page}, via {name}]{RST}\n{snippet}")
    return blocks


def _show(item: Item, cfg_path: Path, docs: dict[str, str], idx: int, total: int) -> None:
    print("\n" + "=" * 78)
    print(f"{BOLD}{item.id}{RST}  [{idx}/{total}]  split={item.split}  category={item.category}")
    print(f"{BOLD}Domanda:{RST} {item.question}")
    print(f"{BOLD}Risposta:{RST} {item.answer}")
    for r in item.references:
        loc = f"art. {r.article}" + (f", comma {r.comma}" if r.comma else "")
        print(
            f"{BOLD}Fonte:{RST} {docs.get(r.doc_id, r.doc_id)} - {loc}, p. {r.page} "
            f"(match={r.match})"
        )
        for ev in r.evidence:
            print(f"   evidence: {YEL}{ev}{RST}")
    if item.references:
        print(f"{BOLD}Testo ufficiale (contesto):{RST}")
        for b in _context(cfg_path, item):
            print(b)


def _edit_json(item: Item) -> Item | None:
    editor = os.environ.get("EDITOR", "vi")
    if shutil.which(editor.split()[0]) is None:
        print(f"editor {editor!r} not found; set $EDITOR")
        return None
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(item.to_json(), fh, ensure_ascii=False, indent=2)
        tmp = Path(fh.name)
    try:
        subprocess.run([*editor.split(), str(tmp)], check=False)
        raw: dict[str, Any] = json.loads(tmp.read_text(encoding="utf-8"))
        return item_from_json(raw)
    except (ValueError, KeyError) as exc:
        print(f"invalid JSON, edit discarded: {exc}")
        return None
    finally:
        tmp.unlink(missing_ok=True)


def review_loop(
    path: Path,
    cfg_path: Path,
    *,
    reviewer: str | None,
    status: str = "draft",
    split: str | None = None,
    category: str | None = None,
    ask: Callable[[str], str] = input,
) -> None:
    items = load_items(path)
    cfg = load_config(cfg_path)
    manifest = load_manifest(cfg.manifest)
    docs = {d.id: d.act for d in manifest.documents}
    known = set(docs)
    todo = [
        i
        for i, it in enumerate(items)
        if it.status == status
        and (split is None or it.split == split)
        and (category is None or it.category == category)
    ]
    if not todo:
        print("nothing to review")
        return
    reviewer = reviewer or ask("Reviewer name/handle: ").strip()
    if not reviewer:
        print("a reviewer name is required")
        return
    for n, i in enumerate(todo, start=1):
        _show(items[i], cfg_path, docs, n, len(todo))
        while True:
            choice = ask("[a]ccept  [e]dit  [r]eject  [s]kip  [q]uit > ").strip().lower()
            now = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
            if choice in {"a", "r"}:
                it = items[i]
                it.status = "validated" if choice == "a" else "rejected"
                it.validated_by = reviewer
                it.validated_at = now
                note = ask("note (optional) > ").strip()
                it.review_notes = note or it.review_notes
                save_items(items, path)
                break
            if choice == "e":
                edited = _edit_json(items[i])
                if edited is None:
                    continue
                errs = schema_errors([edited], known)
                if errs:
                    print("\n".join(errs))
                    continue
                edited.status = "validated"
                edited.validated_by = reviewer
                edited.validated_at = now
                items[i] = edited
                save_items(items, path)
                break
            if choice == "s":
                break
            if choice == "q":
                return
