# Corpus sources and terms of use

Reviewed on 2026-10-26 by the maintainers before downloading anything. This is a summary for
transparency, **not legal advice**. If you redistribute the corpus or derived data, re-check the
sources yourself.

## What we use

The 20 PDFs of the `normativo` domain are the **official issue PDFs of the Gazzetta Ufficiale della
Repubblica Italiana** (Serie Generale and Supplementi ordinari), downloaded from their ELI URLs
(`https://www.gazzettaufficiale.it/eli/gu/YYYY/MM/DD/NUM/sg/pdf`). Each manifest entry records the
URL, retrieval date, SHA-256 and the page range of the act inside the issue
(`corpus/normativo/manifest.yaml`). **The PDFs are not committed**: `itarag corpus fetch`
re-downloads and verifies them.

Why the Gazzetta Ufficiale and not Normattiva: the benchmark measures PDF parsing, so we need the
*native* typeset PDFs that practitioners actually receive (running headers, two-column notes,
hyphenation, tables in annexes, older typesetting, one scanned issue). Normattiva exports are
regenerated from a database and would hide exactly the problems we want to measure.

## Legal status of the texts

- **Italian Copyright Law, art. 5, L. 22 aprile 1941, n. 633**: "Le disposizioni di questa legge non
  si applicano ai testi degli atti ufficiali dello Stato e delle amministrazioni pubbliche, sia
  italiane che straniere." The texts of laws and decrees are therefore not protected by copyright.
  Commentary checked: https://brocardi.it/legge-diritto-autore/titolo-i/capo-i/art5.html
- The PDF files as a *database/publication* are produced by the Istituto Poligrafico e Zecca dello
  Stato (IPZS). We only fetch 20 individual issues (a non-substantial part of the archive) and do not
  redistribute the files.
- On www.gazzettaufficiale.it we did not find a page with explicit reuse terms or a licence for the
  PDFs (pages checked: "Guida all'uso" `caricaHtml?nomeTiles=modalitaConsultazione`, "F.A.Q."
  `caricaHtml?nomeTiles=faq`, "Formato Grafico PDF"). The site states that the digital Gazzetta is made
  available free of charge by the Ministry of Economy and Finance, with the Ministry of Justice and
  IPZS. `https://www.gazzettaufficiale.it/robots.txt` returned an HTML "page not found" (no robots
  rules published) on the review date.

## Normattiva (consulted, not used for the PDFs)

- Legal notice, https://www.normattiva.it/staticPage/legal : texts in Normattiva "non hanno carattere
  di ufficialità"; the only official text is the one printed in the Gazzetta Ufficiale; reproduction
  of the electronic texts is allowed "purché venga menzionata la fonte, il carattere non autentico e
  gratuito"; texts are provided "al solo scopo informativo".
- Open-data portal, https://dati.normattiva.it/Dati-disponibili (text read from the portal's page
  bundle because the page is rendered client-side): an experimental phase under "Creative Commons
  CC BY 4.0 NC", then CC BY 4.0 for the same data from 1 July 2025 to 31 December 2025, and, from
  **1 January 2026**, all acts (original, point-in-time and multi-version) downloadable and reusable
  under **Creative Commons CC BY 4.0** "e medesima paternità". Formats: AKN, XML, JSON, HTML, PDF,
  EPUB, RTF, URI, via pre-built collections or asynchronous search exports; the API specification
  (`/assets/come_fare_per/API_Normattiva_OpenData.pdf`) caps a search export at 7,000 acts.
- **Bulk download**: we were told that the Normattiva terms forbid massive/bulk downloading. We could
  not locate that clause in the pages above, but we act as if it applies: we do not crawl Normattiva
  at all. An automated request for `https://dati.normattiva.it/robots.txt` was answered by the IPZS
  protection system ("La pagina richiesta è stata bloccata dai sistemi di protezione del Poligrafico
  e Zecca dello Stato Italiano"), which confirms that automated access is actively filtered.
- `normattiva_urn` values in the manifest are identifiers built with the URN:NIR convention for
  reference only; the tool never dereferences them.

## How we download (enforced in `src/itaragbench/fetch.py`)

- HTTPS only; host allowlist `www.gazzettaufficiale.it` (redirects to other hosts are refused);
- at least 3 seconds between requests (`min_interval_seconds` in the manifest; code refuses < 2 s);
- a descriptive User-Agent with a link to this repository;
- never more than the documents listed in the manifest (`max_documents: 20`), max 40 MB per file,
  PDF magic-number and Content-Type checks, SHA-256 verification.

During construction we downloaded 21 issues in total: one issue (L. 9 gennaio 2004, n. 4, GU n. 13 of
17 January 2004) was replaced because its fonts carry no usable text layer for any of the three
parsers (custom encoding without a ToUnicode map); its file was deleted.

## Models (not part of the corpus)

- `intfloat/multilingual-e5-base` (MIT) and `BAAI/bge-m3` (MIT), pinned by commit in
  `configs/mvp.yaml`; Docling's layout/table models are downloaded from Hugging Face by Docling.
