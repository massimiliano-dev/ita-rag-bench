---
name: ita-rag-bench
description: The official timetable of an Italian RAG benchmark run, conclusions first and every number with its uncertainty.
colors:
  frame-blue: "#16357a"
  marker-yellow: "#ffd23f"
  paper: "#ffffff"
  ink: "#111418"
  ink-secondary: "#4a525c"
  frame-ink-soft: "#c9d6f0"
  rule-hairline: "#c9ced6"
  tint-blue: "#eaf0fa"
typography:
  display:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 4vw, 3.25rem)"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.015em"
    fontVariation: "'wdth' 75"
  headline:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 750
    lineHeight: 1.1
    fontVariation: "'wdth' 75"
  title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
    lineHeight: 1.1
    fontVariation: "'wdth' 75"
  finding-headline:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.3
    fontVariation: "'wdth' 80"
  lead:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  table:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 87"
  board-figure:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 75"
  code:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "0.03em"
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 70"
  note:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
  terminal:
    fontFamily: "ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "0.875rem"
    lineHeight: 1.6
rounded:
  code: "2px"
spacing:
  measure: "40rem"
  container: "76rem"
  gutter: "1.5rem"
  gutter-mobile: "1rem"
  section: "4rem"
  cell: "0.5rem 0.75rem"
components:
  masthead:
    backgroundColor: "{colors.frame-blue}"
    textColor: "{colors.paper}"
    padding: "1.25rem 1.5rem 0.75rem"
  train-code:
    textColor: "{colors.frame-blue}"
    typography: "{typography.code}"
    rounded: "{rounded.code}"
    padding: "0 0.4rem"
  train-code-hover:
    backgroundColor: "{colors.tint-blue}"
    textColor: "{colors.frame-blue}"
  board-header:
    backgroundColor: "{colors.frame-blue}"
    textColor: "{colors.paper}"
    padding: "0.6rem 0.75rem"
  line-strip:
    backgroundColor: "{colors.frame-blue}"
    textColor: "{colors.paper}"
    padding: "0.4rem 0.75rem"
  table-cell:
    textColor: "{colors.ink}"
    typography: "{typography.table}"
    padding: "{spacing.cell}"
  table-cell-highest:
    backgroundColor: "{colors.marker-yellow}"
    textColor: "{colors.ink}"
  ceiling-row:
    backgroundColor: "{colors.tint-blue}"
    textColor: "{colors.ink}"
  terminal-block:
    backgroundColor: "{colors.tint-blue}"
    textColor: "{colors.ink}"
    typography: "{typography.terminal}"
    padding: "1rem 1.25rem"
---

# Design System: ita-rag-bench

## Overview

**Creative North Star: "The Official Timetable"**

The leaderboard is an Italian railway timetable (Orario ufficiale FS) for a benchmark run. Every pipeline configuration is a train with a unique code, its stops are parsing and chunking, then search, and the grid shows how much recall is still on board at each stop. A blue masthead frames white paper and black ink; a condensed grotesk with tabular figures sets a ruled grid; footnote marks carry uncertainty; one yellow highlighter stroke per table points at the answer.

Density is that of a printed timetable: tight ruled rows, hairline columns, notes in the margin, nothing decorative. Honesty is part of the visual system, not just the copy. Emphasis (bold, yellow) is earned by a margin larger than the measurement noise, and doubt (draft questions, confidence intervals) is spoken in footnote marks, never in colour. Conclusions come first in a reading column; the full grid is one link away, addressed by the same train codes used in the prose.

The page is static HTML with no JavaScript; the language switch is a plain link between `/` (Italian) and `/en/` (English). The font is self-hosted; nothing loads from another host.

**Key Characteristics:**
- Blue frame (masthead, board header, line strip, footer) around white paper and black ink.
- One condensed variable grotesk (Archivo, width axis 70–87%) for everything but terminal commands.
- Train codes `line·service` (MU·FX·HM) used identically in text, tables and anchors.
- Ruled tables: 2px ink rule under headers, 1px hairlines between rows, vertical hairlines between trains.
- Footnote marks † (draft data) and ‡ (±7 point interval) keyed into headers and notes.
- At most one yellow marker per table, labelled as the highest observed value.

## Colors

A three-colour timetable print: institutional blue frame, black ink on white, and a single yellow highlighter.

### Primary
- **Timetable Blue** (frame-blue): the frame. Masthead, departures-board header band, timetable line strip, footer, links, train-code outlines, footnote marks, focus ring, the top rule of terminal blocks.

### Secondary
- **Highlighter Yellow** (marker-yellow): the single answer marker in a table cell, the swatch in the table notes, text selection, the skip link, and the † mark inside the blue masthead (where blue marks would vanish). Never a fill for chrome, never a status colour.

### Neutral
- **Paper** (paper): page ground and text on the blue frame.
- **Ink** (ink): body text, headings, 2px structural rules, the inset ring around the timetable's highest cell.
- **Secondary Ink** (ink-secondary): lead paragraph, intros, table sub-labels, notes, the "lost in search" row.
- **Frame Ink Soft** (frame-ink-soft): secondary text on blue (run metadata labels, footer prose).
- **Hairline** (rule-hairline): 1px row rules and vertical hairlines between trains.
- **Blue Tint** (tint-blue): the parsing-and-chunking ceiling row, train-code hover, targeted timetable cells, terminal blocks.

### Named Rules
**The One Marker Rule.** Each table carries at most one yellow cell. In the timetable it is the highest observed value and the notes say so ("highest observed"); in every other table it appears only when the top value beats the runner-up by more than the noise interval (NOISE = 0.07, 7 points). Otherwise no cell is yellow and an explicit tie note says why.

**The No Colour For Doubt Rule.** Uncertainty and draft status are never coloured, faded or badged. They are footnote marks: † for draft (LLM-assisted, unvalidated) questions, ‡ for the ±7 point 95% interval, attached to the header or figure they qualify and explained in the notes beneath.

## Typography

**Display Font:** Archivo variable (wdth 62–125, wght 100–900, self-hosted woff2, OFL) with system-ui, sans-serif
**Body Font:** Archivo, same file
**Label/Mono Font:** ui-monospace, SF Mono, Menlo (terminal commands only)

**Character:** One grotesk at several widths, the way a timetable uses one face at several condensations: headings and codes squeezed to 70–80% width, tables at 87%, prose at normal width.

### Hierarchy
- **Display** (800, clamp(2.25rem, 4vw, 3.25rem), 1.1, width 75%): the page title only, max 20ch, balanced.
- **Headline** (750, 1.875rem, 1.1, width 75%): section titles, always sitting on a 2px ink rule.
- **Title** (700, 1.375rem, width 75%): individual finding headings.
- **Finding headline** (700, 1.125rem, 1.3, width 80%): the first-viewport list of conclusions, each a link with its train codes.
- **Lead** (400, 1.25rem, 1.5, secondary ink; 1.125rem under 640px): the opening paragraph.
- **Body** (400, 1.0625rem, 1.6): prose within a 40rem measure.
- **Table** (400, width 87%, tabular figures): every data table; numerals right-aligned.
- **Board figure** (700, 1.375rem, width 75%, tabular): recall@5 on the departures board.
- **Code** (700, 0.9375rem, +0.03em, width 70%, tabular): train codes.
- **Note** (400, 0.875rem, secondary ink): margin notes, table notes, legend, footer.

### Named Rules
**The Tabular Figures Rule.** Every number that can sit above another number uses tabular figures and right alignment, so decimals line up down a column like departure times.

**The One Face Rule.** Hierarchy comes from width and weight on Archivo's axes, not from a second family. Monospace is reserved for shell commands.

## Layout

A centred 76rem container with 1.5rem gutters (1rem under 640px). Prose sections keep a 40rem reading measure; data sections (by category, by document) widen to 60rem; the timetable takes the full container and scrolls horizontally inside a focusable region (min width 56rem), with the stop column sticky on the left.

From 1100px the opening and the timetable section become two columns: the reading measure on the left and a margin column (min 16–20rem, 4rem gap) on the right. In the opening the margin holds the "three highest configurations" board and its margin notes († and ‡); in the timetable section it holds the code legend, sticky. Below 1100px the board stacks under the headlines and the margin legend is hidden in favour of the one under the timetable.

First viewport: masthead (wordmark, run id, "valid from" date, facts with †, language link), section nav, then title, lead, finding headlines with their codes, and the board. Sections are separated by 4rem and opened by a 2px ink rule over the heading.

## Elevation & Depth

Flat. There are no drop shadows; depth is printed: tonal rows (blue tint for the ceiling stop), 2px ink rules for structure, 1px hairlines for rows and train columns, and the blue frame as the only solid field. The one `box-shadow` in the build is an inset 2px ink ring around the timetable's highest cell, which reinforces the yellow for readers who cannot see it; it is a border, not elevation.

### Named Rules
**The Printed Depth Rule.** Separate things with rules and tints, never with shadows or floating cards.

## Shapes

Square. Tables, bands, the board and the draft notice have no radius and no outer box; they are bounded by rules. The only rounding is the 2px corner on train-code outlines (a 1.5px currentColor stroke), which reads as a stamped number plate. The favicon is a blue tile with three pale rules and a yellow cell, the timetable in miniature.

## Components

### Train Code
The signature. Outlined plate in Timetable Blue, condensed bold, tabular, letter-spaced. Codes are two-part for a line (parser·chunker: MU·FX) and three-part for a train (line·service: MU·FX·HM); every configuration has exactly one code. Parsers PY/MU/DL, chunkers FX/RC/ST, services BM/E5/M3/HE/HM. In prose and the board a code is a link to its timetable cell (`#cell-mu-fx-hm`) or column (`#train-mu-fx`); hover fills with Blue Tint; the targeted cell gets a 3px blue inset outline and tint.

### Masthead and Navigation
The timetable cover: a Timetable Blue band with the wordmark (800, 1.75rem, width 70%), run metadata in Frame Ink Soft with values in white, the † mark in yellow, and the language switch as a plain underlined link. Below a 25% white hairline, the section nav: white, width 85%, semibold, underline on hover, horizontally scrollable on narrow screens. Focus rings inside the band turn yellow.

### Departures Board
"The three highest configurations": a blue header band, then a ruled table of train code, service, recall@5 (board figure) and ceiling (secondary). Under it, either a tie note (spread below 7 points: none is significantly better) or a no-tie note, then margin notes for † and ‡.

### Timetable
Stops are row groups: Stop 1 (parsing and chunking ceiling, tinted row) and Stop 2 (one search service per row, ‡ on the group header). Trains are columns with their code and parser/chunker sub-labels, separated by vertical hairlines. A 2px ink rule opens the final "lost in search" row. Above the table, the blue line strip ("Table 1 · Line PDF › chunk › search · 9 trains, 5 services"). Beneath it, notes with the yellow swatch, ‡ and †, then the code legend.

### Ruled Tables
Header row on a 2px ink rule, rows on 1px hairlines, cells 0.5rem × 0.75rem, row headers semibold. Bold marks a row's best only when it beats the runner-up by more than 7 points; small samples carry a caution note.

### Draft Notice
Between a 2px ink rule and a hairline: a large blue † and the statement that all questions are drafts and the ±7 interval applies. It is the anchor (`#draft`) every † links to.

### Terminal Block
Blue-tint panel with a 2px blue top rule, monospace 0.875rem, for the reproduce commands.

## Do's and Don'ts

### Do:
- **Do** give every configuration its unique train code (line·service, e.g. MU·FX·HM) and use it identically in prose, boards, tables and anchors.
- **Do** mark a value bold or yellow only when it beats the runner-up by more than 7 points (NOISE = 0.07); otherwise write an explicit tie note.
- **Do** keep yellow to one cell per table and label it as the highest observed value.
- **Do** attach † (draft data) and ‡ (±7 interval) to the headers or figures they qualify, with the explanation in the notes.
- **Do** lay out data as a timetable: stops as row groups, trains as columns with vertical hairlines, the blue line strip above.
- **Do** keep the first viewport to title, lead, finding headlines with codes, and the three-highest board with its margin notes.
- **Do** ship static HTML with real tables and headers, a self-hosted font, and the language switch as a plain link.

### Don't:
- **Don't** colour, fade or badge uncertainty or draft status; use footnote marks.
- **Don't** heat-map tables or use more than one yellow marker in a table.
- **Don't** rank, bold or call a winner on differences within the ±7 point interval.
- **Don't** add JavaScript, sorting widgets or external hosts.
- **Don't** add drop shadows, rounded cards or a second typeface for display.
