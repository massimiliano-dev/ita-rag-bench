"""Static leaderboard generator (no external JS/CSS)."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _latest_run(results: Path) -> Path:
    runs = sorted(p for p in results.iterdir() if (p / "summary.json").exists())
    if not runs:
        raise FileNotFoundError(f"no results with summary.json under {results}")
    return runs[-1]


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "parser",
        "chunker",
        "embedding",
        "retriever",
        "overall",
        "per_category",
        "per_characteristic",
        "chunk_stats",
        "timings",
        "parse_seconds",
        "evidence_coverage",
    )
    return {k: row.get(k) for k in keep}


def build_site(results: Path, out: Path, run_id: str | None = None) -> Path:
    run_dir = results / run_id if run_id else _latest_run(results)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    data = {
        "run_id": summary["run_id"],
        "created": meta.get("created"),
        "dataset": meta.get("dataset"),
        "senza_risposta": meta.get("senza_risposta"),
        "corpus": meta.get("corpus"),
        "parsers": {
            k: {kk: v.get(kk) for kk in ("seconds", "pages", "near_empty_pages", "failed_docs")}
            for k, v in meta.get("parsers", {}).items()
        },
        "env": {
            "python": meta.get("environment", {}).get("python"),
            "platform": meta.get("environment", {}).get("platform"),
            "packages": meta.get("environment", {}).get("packages"),
        },
        "rows": [_compact(r) for r in summary["rows"]],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("__DATA__", payload).replace(
        "__RUN__", html.escape(str(summary["run_id"]))
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ita-rag-bench leaderboard</title>
<style>
:root{--bg:#fbfbf9;--fg:#1d1d1b;--muted:#6b6b66;--line:#e2e1dc;--accent:#0b6e4f;--warn-bg:#fff4d6;
--warn-fg:#6b4e00;--head:#f1f0ec;--best:#e3f2ea}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--muted:#a3a29b;--line:#34332f;
--accent:#5fd1a5;--warn-bg:#3a2f12;--warn-fg:#f3d68a;--head:#22221f;--best:#1f3a2e}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",
Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.15rem;margin:32px 0 8px}
.sub{color:var(--muted);margin:0 0 16px}
.warn{background:var(--warn-bg);color:var(--warn-fg);border-radius:8px;padding:12px 14px;margin:16px 0}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:12px 0}
label{font-size:.9rem;color:var(--muted)}select{font:inherit;padding:4px 6px;border-radius:6px;
border:1px solid var(--line);background:var(--bg);color:var(--fg)}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{background:var(--head);position:sticky;top:0;cursor:pointer;user-select:none;font-weight:600}
th:focus-visible{outline:2px solid var(--accent)}
td.l,th.l{text-align:left}tr:hover td{background:var(--head)}
td.best{background:var(--best);font-weight:600}
.small{font-size:.85rem;color:var(--muted)}
code{font-size:.85em}
</style>
</head>
<body>
<main>
<h1>ita-rag-bench</h1>
<p class="sub">End-to-end retrieval benchmark on Italian normative PDFs: parser &rarr; chunker &rarr;
embedding &rarr; retrieval. Run <code>__RUN__</code>.</p>
<div class="warn" id="warn"></div>

<h2>Leaderboard</h2>
<div class="controls">
<label>Retriever <select id="f-retr"></select></label>
<label>Parser <select id="f-parser"></select></label>
<label>Embedding <select id="f-emb"></select></label>
</div>
<div class="scroll"><table id="main"></table></div>
<p class="small">Click a column header to sort. Metrics on answerable questions only;
relevance = chunk contains the gold evidence span (normalised, or &ge;85% in-order token
alignment). <em>Ceiling</em> = share of gold references fully contained in at least one chunk
(parser + chunker upper bound, independent of the retriever). Best value per column highlighted.
Query latency is the batched mean per query.</p>

<h2>Recall@5 by question category</h2>
<div class="scroll"><table id="cat"></table></div>

<h2>Recall@5 by document characteristic</h2>
<div class="controls"><label>Characteristic <select id="f-char"></select></label></div>
<div class="scroll"><table id="char"></table></div>

<h2>Parsers</h2>
<div class="scroll"><table id="parsers"></table></div>

<h2>Run details</h2>
<div class="small" id="details"></div>
</main>
<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
"use strict";
const D=JSON.parse(document.getElementById("data").textContent);
const rows=D.rows;
const fmt=(v,d=3)=>v==null||isNaN(v)?"\u2013":Number(v).toFixed(d);
const esc=s=>String(s==null?"\u2013":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const uniq=a=>[...new Set(a)];
function opts(sel,vals,def){sel.innerHTML=["all",...vals].map(v=>`<option${v===def?" selected":""}>${esc(v)}</option>`).join("");}
const fr=document.getElementById("f-retr"),fp=document.getElementById("f-parser"),fe=document.getElementById("f-emb"),fc=document.getElementById("f-char");
opts(fr,uniq(rows.map(r=>r.retriever)),"all");opts(fp,uniq(rows.map(r=>r.parser)),"all");
opts(fe,uniq(rows.map(r=>r.embedding||"none")),"all");
fc.innerHTML=Object.keys(rows[0].per_characteristic||{}).map(k=>`<option>${esc(k)}</option>`).join("");
const ds=D.dataset||{};
document.getElementById("warn").innerHTML=`<strong>Draft questions.</strong> All ${esc(ds.n_items)} questions are machine-assisted drafts
(status: ${esc(JSON.stringify(ds.status_counts))}) not yet validated by a human. Single domain (Italian normative acts),
${esc((D.corpus||{}).n_documents)} documents. Treat numbers as preliminary.`;
const COLS=[["parser","Parser","l"],["chunker","Chunker","l"],["embedding","Embedding","l"],["retriever","Retriever","l"],
["recall@1","R@1"],["recall@5","R@5"],["recall@10","R@10"],["mrr@10","MRR@10"],["ndcg@10","nDCG@10"],
["ceiling","Ceiling"],["n_chunks","Chunks"],["mean_chunk_chars","Mean chars"],["index_seconds","Index s"],["query_ms","Query ms"]];
function val(r,k){if(k==="ceiling")return r.evidence_coverage?r.evidence_coverage.overall.share:null;if(k in r.overall)return r.overall[k];if(r.chunk_stats&&k in r.chunk_stats)return r.chunk_stats[k];
if(r.timings&&k in r.timings)return r.timings[k];const v=r[k];return v==null?"none":v;}
let sortKey="recall@5",sortDir=-1;
function filtered(){return rows.filter(r=>(fr.value==="all"||r.retriever===fr.value)&&(fp.value==="all"||r.parser===fp.value)&&(fe.value==="all"||(r.embedding||"none")===fe.value));}
function renderMain(){
 const rs=filtered().slice().sort((a,b)=>{const x=val(a,sortKey),y=val(b,sortKey);return (x>y?1:x<y?-1:0)*sortDir;});
 const best={};["recall@1","recall@5","recall@10","mrr@10","ndcg@10"].forEach(k=>best[k]=Math.max(...rs.map(r=>val(r,k))));
 let h="<thead><tr>"+COLS.map(([k,l,c])=>`<th tabindex="0" class="${c||""}" data-k="${k}" aria-sort="${k===sortKey?(sortDir>0?"ascending":"descending"):"none"}">${l}${k===sortKey?(sortDir>0?" ▲":" ▼"):""}</th>`).join("")+"</tr></thead><tbody>";
 for(const r of rs){h+="<tr>"+COLS.map(([k,,c])=>{const v=val(r,k);
  if(c==="l")return `<td class="l">${esc(v)}</td>`;
  const d=k==="n_chunks"?0:(k==="mean_chunk_chars"||k==="index_seconds"||k==="query_ms")?1:3;
  return `<td class="${best[k]!==undefined&&v===best[k]?"best":""}">${fmt(v,d)}</td>`;}).join("")+"</tr>";}
 document.getElementById("main").innerHTML=h+"</tbody>";
 document.querySelectorAll("#main th").forEach(th=>{const go=()=>{const k=th.dataset.k;if(k===sortKey)sortDir=-sortDir;else{sortKey=k;sortDir=-1;}renderMain();};
  th.onclick=go;th.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();go();}};});
 renderCat(rs);renderChar(rs);
}
function label(r){return `${r.parser} · ${r.chunker} · ${r.embedding||"\u2013"} · ${r.retriever}`;}
function renderCat(rs){const cats=Object.keys(rows[0].per_category);
 let h="<thead><tr><th class='l'>Configuration</th>"+cats.map(c=>`<th>${esc(c)} (n=${fmt(rows[0].per_category[c].n,0)})</th>`).join("")+"</tr></thead><tbody>";
 for(const r of rs)h+=`<tr><td class="l">${esc(label(r))}</td>`+cats.map(c=>`<td>${fmt(r.per_category[c]["recall@5"])}</td>`).join("")+"</tr>";
 document.getElementById("cat").innerHTML=h+"</tbody>";}
function renderChar(rs){const ch=fc.value;if(!ch)return;const vals=Object.keys(rows[0].per_characteristic[ch]);
 let h="<thead><tr><th class='l'>Configuration</th>"+vals.map(v=>`<th>${esc(ch)}=${esc(v)} (n=${fmt(rows[0].per_characteristic[ch][v].n,0)})</th>`).join("")+"</tr></thead><tbody>";
 for(const r of rs)h+=`<tr><td class="l">${esc(label(r))}</td>`+vals.map(v=>`<td>${fmt((r.per_characteristic[ch][v]||{})["recall@5"])}</td>`).join("")+"</tr>";
 document.getElementById("char").innerHTML=h+"</tbody>";}
function renderParsers(){let h="<thead><tr><th class='l'>Parser</th><th>Pages</th><th>Seconds</th><th>Near-empty pages</th><th class='l'>Failed documents</th></tr></thead><tbody>";
 for(const [k,v] of Object.entries(D.parsers))h+=`<tr><td class="l">${esc(k)}</td><td>${fmt(v.pages,0)}</td><td>${fmt(v.seconds,1)}</td><td>${fmt(v.near_empty_pages,0)}</td><td class="l">${esc((v.failed_docs||[]).join(", ")||"none")}</td></tr>`;
 document.getElementById("parsers").innerHTML=h+"</tbody>";}
const sr=D.senza_risposta||{};
document.getElementById("details").innerHTML=`Created ${esc(D.created)} · dataset sha256 <code>${esc((ds.sha256||"").slice(0,12))}</code> ·
corpus <code>${esc(((D.corpus||{}).documents_sha256||"").slice(0,12))}</code> · Python ${esc(D.env.python)} on ${esc(D.env.platform)}.<br>
Unanswerable questions (senza_risposta): ${esc(sr.count)} — ${esc(sr.note)}`;
[fr,fp,fe].forEach(s=>s.onchange=renderMain);fc.onchange=()=>renderChar(filtered());
renderMain();renderParsers();
})();
</script>
</body>
</html>
"""
