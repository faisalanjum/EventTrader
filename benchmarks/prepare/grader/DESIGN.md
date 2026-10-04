# Prepare · Step 3, part 5 — the checker (grader) design

*Claude, 2026-10-03. Owner: "sure, go ahead" to writing this spec (chat, 2026-10-03). Status: **built 2026-10-03 in `benchmarks/prepare/grader/` (inside the repo, own folder): 100 unit tests green; the 7 real-original contract pairs + the 8-case supplement = 42/42 variants behave as required (`benchmarks/prepare/grader/checks/RESULTS.json`); not committed; Codex review pending.** Independent checker: Codex (part 5 rule: one builder, independent checker).*

**What it is:** a marking program. The frozen answer key is the answer sheet. The grader takes a conversion route's output, finds each answer's spot in the original file, and marks it: kept exactly, kept in the right row / column / section, or lost. It prints scores per split and per format.

**Why:** Step 4 picks the conversion tool by evidence (PrepareStep.md T1, Step 4: "code scores against the checked key, including omissions"). Without the grader the 457 answers cannot be used.

**Authority:** [Prepare-Step3.md](Prepare-Step3.md) part 5 and "What must be checked"; [PrepareStep.md](../PrepareStep.md) P14, P15, T1, Step 4, §4–5; the key's scoring contract `CLAUDE_KEY_README.md` (E1–E10) and Codex's `CONVERTER_COMPARISON.md` (both in the key package below). Owner rules: no company-specific code; minimal; ask before changes.

## 1. Inputs (all frozen, read-only)

| Input | Where |
|---|---|
| Key package **1134** (final; same records and hashes as 0729 — see `benchmarks/prepare/golden/PACKAGE.json`): `CLAUDE_ANSWER_KEY.json` (457 records, sha256 `007e4bd8…`), `CLAUDE_KEY_FLAGS.json` (5 excluded fields), `KEY_SUPPORT_MAP.json` + `KEY_SUPPORT_OVERRIDES.json` (where each answer piece sits in the original), `converter_checks/REGRESSION_CASES.json` (8 development cases: 5 UDR PDF cells, 3 Darden range cells) | `/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/FINAL_KEY_FOR_CODEX_20261003_0729/` |
| Target locations (`cell_anchor`, `table_anchor`, `block_anchor`) and source hashes | `packets/<id>/targets.json`, `bundled/packets/<id>/targets.json` beside the package |
| Splits per source file: development 72 files / stratified_control 41 / heldout 24 (targets 249 / 118 / 90) | `/home/faisal/prepare_work/step3_sample_20261002/case_catalog.csv` |
| Originals (137 files; hashes checked 2026-10-03: all match) | `packets/*/sources/`, `bundled/packets/*/sources/`; supplement sources under `trial_20261002_v3/` |

The grader verifies every source hash first; any mismatch stops that file with `INPUT_MISMATCH` (never substitutes).

## 2. The common route-output format (what the grader reads)

Tool outputs will change shape (owner, 2026-10-03). The grader therefore reads **one small format**; each route (tool + settings + adapter + linker) has a thin adapter that fills it. Raw tool output is kept beside it (CONVERTER_COMPARISON point 1). One JSON file per source file:

```json
{"schema": "prepare-route-output/1",
 "file_id": "0001140361-25-003207/form10q.htm", "sha256": "<original sha256>",
 "route": {"name": "docling-html", "tool": "docling", "version": "2.131.0", "settings": {"...": "..."},
           "adapter": "<name@sha>", "linker": "<name@sha or null>"},
 "status": "OK | FAILED | UNSUPPORTED | PARTIAL", "error": null, "seconds": 1.6,
 "units": [
  {"id": "u0", "kind": "heading", "level": 1, "text": "Item 2. Management's Discussion …", "anchor": {"byte_start": 100, "byte_end_exclusive": 160}},
  {"id": "u1", "kind": "text", "text": "…", "anchor": {"byte_start": 200, "byte_end_exclusive": 900},
   "links": [{"text": "Note 3", "href": "#n3", "to": "u7"}], "struck": ["words shown struck through"]},
  {"id": "u2", "kind": "table", "anchor": {"byte_start": 1000, "byte_end_exclusive": 9000}, "caption": ["Free Cash Flow"],
   "cells": [{"r": 0, "c": 1, "rs": 1, "cs": 2, "text": "December 28, 2024", "anchor": {"byte_start": 1200, "byte_end_exclusive": 1300}, "header": true},
             {"r": 3, "c": 1, "rs": 1, "cs": 1, "text": "(506", "anchor": {"byte_start": 5200, "byte_end_exclusive": 5300}, "markers": ["(1)"]}],
   "notes": ["u3"]},
  {"id": "u3", "kind": "footnote", "marker": "(1)", "text": "(1) Represents …", "anchor": {"byte_start": 9100, "byte_end_exclusive": 9400}},
  {"id": "u4", "kind": "image", "anchor": {"byte_start": 9500, "byte_end_exclusive": 9570}, "text": "text read from the picture, in order"},
  {"id": "u5", "kind": "field", "name": "{http://www.sec.gov/edgar/schedule13D}sharedDispositivePower",
   "path": ["{…}edgarSubmission", "{…}formData", "{…}reportingPersons", "{…}reportingPersonInfo"], "group": {"index": 2, "count": 3},
   "text": "0", "anchor": {"byte_start": 11000, "byte_end_exclusive": 11001}},
  {"id": "u6", "kind": "clutter", "text": "Page 4", "anchor": {"byte_start": 9800, "byte_end_exclusive": 9806}}
 ]}
```

- **Required** per unit: `id` (unique, stable for the same input), `kind`, `anchor`, and `text` (tables: `cells`, each with `r c rs cs text anchor`, row-major). Units in reading order.
- **Optional** (reported as "structure" when present): `level`, `header`, `caption`, `markers` (footnote marks kept apart from the number), `notes`, `marker`, `links`/`to`, `struck`, `name`/`path`/`group` (XML).
- **Kinds:** `heading text list_item caption footnote table image field clutter other`. `clutter` = dropped on purpose (page numbers, running banners); it counts as accounted for, not lost. A `clutter` unit counts only for the nothing-lost gate; it never satisfies any check in §5.
- **Anchors:** HTML/XML `{byte_start, byte_end_exclusive}` in the original's bytes; PDF `{page, region: [x0,y0,x1,y1]}` in points, 1-based page, top-left origin; picture files `{file, region}` in pixels, top-left origin. Same conventions as the key. A unit or cell that sits in several source places (a merged stacked header, a prose block printed over several lines) may carry a **list** of anchors.
- **Status:** `FAILED` (tool error) and `UNSUPPORTED` (format the route does not handle) count every target of that file as not converted; `PARTIAL` marks hand-made fixtures that cover only part of a file (the "nothing lost" gate is skipped for them).

## 3. Finding a target in the route output

| Anchor type | Overlap rule |
|---|---|
| bytes | ranges intersect |
| PDF page/region, picture file/region | same page (or file) and intersection area ≥ 50 % of the smaller box |

- A key **cell** → the route cells overlapping its `cell_anchor` (inside a table unit overlapping its `table_anchor`). A key **block** → the route units overlapping its `block_anchor`. None found → `UNRESOLVED` mapping = a miss for the route.
- Every other answer piece (row label, header line, title line, unit line, period phrase, footnote mark and note, reference, basis phrase) is found through **its own anchor** from `KEY_SUPPORT_MAP.json` (`model`/`inline`/`reviewed` anchors; for `search` pieces any listed occurrence counts for preservation and the `governing` one for association). Matching words anywhere in the file never counts.
- When a route split one source cell into several, or merged several into one: take all route cells overlapping the piece's anchors, in reading order, joined by one space.

## 4. Text comparison

`norm(s)`: collapse every run of whitespace (space, tab, newline, NBSP, zero-width, BOM, soft hyphen) to one space; trim; fold quote and dash glyphs only (E8: ‘’→', “”→", – — ‑ −→-); drop the key's `~~` marks; keep case, signs, parentheses, `%`, `$`, commas, unit case. Whitespace is **normalised, not deleted**: a word split by styling (`S tockholder`) does not match `Stockholder` (those cases were chosen for this).

- Cell-like pieces (value, labels, headers, title lines, corner, unit line, header-type period phrases, marks, range partner): `norm` **equality** with the overlapping cell(s).
- Phrase pieces (basis phrases, prose period phrases, reference phrases): `norm` **containment** in the overlapping unit(s).
- Value cell: equals `printed_value`, or equals `display_value` (symbol cells joined, e.g. `$(506)`), or equals `printed_value` with its symbol cells kept as adjacent cells in the same row. Equals `printed_value` + one of the target's own footnote marks glued (`10.674`) → **fail `marker_glued`**.
- Label/header pieces with one of the target's own marks glued → preserved, counted as `marker_in_label`.
- A field with accepted alternatives passes if **any** alternative passes. The 5 excluded fields are skipped and counted in every report.

## 5. Checks per target (T1 = preservation + association; code only, no AI)

| Key field | Preserved (text at its own spot) | Associated (place in the route's structure) | Folds allowed |
|---|---|---|---|
| `printed_value` / `display_value` | value text rule above | — | — |
| `row_label`, `row_context` texts | each piece | same table, same row (`r`); a wrapped or two-column label may be one cell or two | — |
| `header_path` pieces | each piece (stacked fragments joined or separate) | same table, above the value, column span covers the value's column | E1 |
| `table_title` lines, `corner_text`, `lead_in`, `unit_printed` | each piece | title: table caption, a top in-table row, or a unit before the table with no table between; corner: header area of the same table; lead-in: unit directly before the table; unit line: in the table or before it | E1, E2 |
| `section_path` headings | each heading unit, before the target | order kept; **recognised** as `heading` counted separately | E1, E2, E9 |
| `segment_or_basis` phrases | each phrase | inside the table → same table, above the value; else before the table or in its note | — |
| `periods` parts | each phrase | header-type parts: column coverage as headers; prose parts: preserved only | E4, E7 |
| `footnote_markers` | mark kept apart from the value (`markers` field or own cell/unit); `note_text` unit present | mark → note link (`notes`/`marker`) counted as **structure** | — |
| `range` (supplement) | partner value; connector text or Low/High headers | partner in the same row; source order kept (endpoints not flipped) | — |
| `references` | phrase inside the block; `href` equal when the key has one | `RESOLVED` target: a route unit exists at the key's target anchor; link `to` that unit counted as **structure** | E6 |
| structure `printed_text` | units overlapping the block, joined in order, `norm` equal | block order within the file kept | E8, E10 |
| structure `kind` | — | route kind maps to the key kind for `heading list_item footnote caption table paragraph(=text)`; `image metadata other` reported only | — |
| pictures / scanned pages (`kind: image`) | route text for that picture/page region `norm` equal to the transcription; otherwise word-error-rate and the missing/extra words are printed (E10: diagnostic). Strict in v1; any page-furniture waiver later, per record, reviewed. | — | E8 |
| XML (`field` units) | value text; `row_label` = local name; `header_path` = expanded parent names (prefixes may differ) | same group as the key's `row_context` identifiers (same reporting person) | — |

**Not graded here (Step 8, AI reader):** `value_kind`, `sign` (survives through the text), `marker_meaning`, `measure`, `unit_interpretation`, period `role`/`type`, range `role`. Reported as "not T1" so nobody mistakes silence for a pass.

**Target verdict:** `PASS` only if the value and every applicable preserved + associated check pass; otherwise `FAIL` with the failing checks; `UNRESOLVED` (not found at its spot); `NOT_CONVERTED` (file FAILED/UNSUPPORTED). Structure counts (headings recognised, notes linked, references linked) never flip a verdict; they rank routes.

## 6. Route-level gates (P14) — reported with numbers; a failing gate blocks ranking

| Gate | Check |
|---|---|
| Anchors tied to the original | every unit/cell has an anchor inside the file; HTML/XML: `norm` of the original's visible text at the anchor equals the unit text (honest anchors); PDF/picture: in bounds (text honesty is diagnostic) |
| Versioned IDs and run facts | `route` block complete (tool, version, settings, adapter, linker); unit ids unique |
| Reading order, exact text | top-level anchors non-decreasing in reading order (tables row-major inside); text exactness comes from §5 |
| Footnote marks apart from numbers | no `marker_glued` on any value |
| Nothing lost | visible characters of the original (per `anchor.py`'s visible-text map: comments, scripts, styles, `display:none` and `ix:hidden` removed) not inside any unit, cell or `clutter` anchor → listed as uncovered spans with their text, count and % per file; pass = 0 unaccounted |

Secondary facts echoed, never gates: seconds per file, output bytes, files OK/FAILED/UNSUPPORTED.

## 7. Output

- `results.jsonl`: one line per target × check: verdict, reason, key piece, route unit ids and anchors.
- `summary.md` + `summary.json`: (1) by split × format: targets, PASS, FAIL, UNRESOLVED, NOT_CONVERTED, excluded fields; (2) by field: preserved %, associated %, recognised %; (3) gates; (4) run facts. Held-out shows aggregates only unless `--heldout-detail` (for the checker, never for tool builders). The 8 supplement cases are reported in their own table, never mixed into the 457.

## 8. Proof that the grader itself is right (part 5)

1. **Repo tests** (`tests/driver/prepare/test_grade.py`, `test_anchor.py`; standard library; tiny synthetic HTML and XML fixtures with a hand-written key subset in the key's exact JSON shape and one hand-written correct route output): the correct output passes everything. Then one planted fault per check, each **must fail only its intended check**: changed digit · dropped value cell · value under the next column · value in the next row · parentheses/sign lost · `$` attached to another row · stacked-header fragment lost · header assigned to the next column · mark glued `10.674` · note dropped · heading dropped (fail) vs heading demoted to text (structure count only) · paragraph dropped (uncovered span + unresolved) · paragraphs reordered · struck text dropped · reference destination changed · XML prefix changed (must PASS) vs value moved to another person (must FAIL) · PDF number under another row/column (must FAIL) · missing page (unresolved) · two-column label as two cells (PASS) · range endpoints flipped · dishonest anchor (gate fails).
2. **The contract pairs on real originals** (CONVERTER_COMPARISON "Required checks"): Berry T05 `$(506)`, Aflac T03 stacked header, UDR P01 PDF cell, Darden C07–C09 range/footnote, one scanned page (bundle-030), Alpha Units XML T01, AMG T05 reference. Hand-made correct outputs (status `PARTIAL`) must pass; their damaged copies must fail for the stated reason. Lives beside the key package: `bulk_20261002/grader_checks/` (reads the frozen originals; run on demand; results recorded).
3. **Codex** inspects the code and tries its own planted faults before the grader is used to rank anything.

## 9. The linker (`driver/prepare/anchor.py`) — for routes that give no source positions

Docling on HTML gives no positions (study 2026-09-30); edgartools unknown. P14 requires anchors, so a shared, generic, text-only linker is part of the toolkit (allowed by T1: "linking evidence back to the original HTML cells (P20)"):

- `visible_text(raw)` → characters with byte spans: entities decoded once, comments/scripts/styles/head removed, `display:none` and `ix:hidden` subtrees removed (tag stack), block tags → one space, same cp1252 fallback as the key's scripts.
- `link(raw, units)` → fills anchors by **monotonic** search of each unit's (and cell's) whitespace-stripped, E8-folded text in that stream from a moving cursor; not found → `anchor: null` with the first mismatch shown (the tool changed the text) — such units can never match a target, which is the correct consequence; also returns the uncovered spans for the nothing-lost gate.
- It never adds, repairs or reorders text (contract point 4). Its own tests: reordered unit flagged; altered digit left unanchored; dropped paragraph uncovered; hidden text excluded; NBSP/entities handled; styled split word found.

## 10. Code home, size, order

| Piece | Path | Size (estimate) |
|---|---|---|
| grader | `driver/prepare/grade.py` (CLI: `python3 -m driver.prepare.grade --key <package dir> --route <dir of per-file json> --out <dir>`) | ~400 lines |
| visible text + linker | `driver/prepare/anchor.py` | ~150 lines |
| tests + fixtures | `tests/driver/prepare/test_grade.py`, `test_anchor.py`, `fixtures/grader/` | ~400 lines |
| real-original pairs | `prepare_work/step3_sample_20261002/bulk_20261002/grader_checks/` | small |

Order: tests and fixtures first, then the code until they pass; Codex review; then a **throw-away Docling-HTML adapter** (study venv, Docling 2.131) on 2–3 development files only, to confirm the format fits real output and the linker anchors it. No ranking, no held-out use, no tuning on any key record.

**Not built here:** production adapters (Step 4 builders); the inline-tag context check (P9 — separate, over tagged values, not in the key); replay/determinism (Step 7); a furniture waiver for page transcriptions; AI-reader scoring (Step 8). Part 6 (freeze) still needs the owner's final OK.

## 11. Rules added by the real-original pairs (2026-10-03) — all key- or guide-driven, none document-specific

| Real-document behaviour | Rule now in the grader |
|---|---|
| A footnote printed as the table's own last row | the note may be a unit **or a cell of any table**; a note row of the same table counts as linked |
| A mark raised by CSS (not `<sup>`) glued to a title/header/label | `same()`: text equal once **the target's own marks** are set aside → pass, flag `marker_in_text` (`marker_in_label` for labels) |
| Header line "X ($000s)" where the key splits the bracketed unit off (guide 3.5 rule 6) | `same()`: text equal once a **trailing bracketed phrase** is set aside → pass, flag `unit_phrase_split` |
| One key piece over several cells, or several pieces merged in one cell | `match_pieces()`: pieces aligned to cells in order, both directions, every cell consumed |
| Qualifier sentence printed after the table | outside the table, **preserved at the key's reviewed location** is the association; inside, it must sit above the value |
| "(continued)" in the key's heading | E2 folded on both sides (`heading_eq`) |
| Two PDF boxes in one row | `source_before()`: boxes sharing a row compare left to right, else page then top to bottom |
| A scanned page returned as text blocks, tables included | image targets join every non-clutter unit over the region in reading order |
| A symbol cell merged into the value cell (`$(506)`) | `unit_printed` found inside the value cell → pass, flag `in_value_cell` |

Controls for the pairs are built from the originals by `benchmarks/prepare/grader/checks/real_pairs.py` (HTML grid with colspan/rowspan and raised marks; PDF words from the file's own text layer; XML elements with expanded names). Two of its early fixtures were wrong and the grader's own gates caught them (an anchor off by one byte; two boxes overlapping) — the mechanical checks work in both directions.

## 12. Generality pass over all 457 targets (2026-10-03)

A read-only scan of every answer piece's location in the sample's HTML files (own table / another table / plain text)
showed what the 7 pairs never hit: headings carried by one-cell layout tables (126 anchors), titles in their own table
before the data table (25), footnotes laid out as tiny tables (12), header rows of a table continued across a page break
(10), lead-ins inside the table element (6), qualifier phrases in other tables (66). The grader therefore treats **any
text unit or any cell of any table** as a possible carrier of an answer piece (`Grader.carriers`), and judges placement by
**source order**: inside the value's table the carrier's row order must match the original's byte/box order; a header
found in an earlier table part counts as a continued table (flag `continued_table`) and must still cover the value's
columns; outside the table the key's reviewed location is the association. A value cell spanning columns is covered
when any of its columns is. Structure blocks inside a layout table are read from the overlapping cells (a heading that
comes back as a table cell fails `kind`: it lost its nature). Cells are indexed by first byte for speed.

## 13. Spike on real Docling output (2026-10-03) — the format fits

Three development HTML files through Docling 2.131 (HTML route, defaults) → a 60-line throw-away adapter → the shared
linker → the grader (`/home/faisal/prepare_work/grader_spike_docling_20261003/`). 25 targets: 23 pass; the two failures are
real route limits (no picture text on the HTML route; a styled bullet item labelled `text`). All gates pass; 0 visible
characters lost in 171,717; 5 unanchored items, all invisible in the originals (a synthetic title, an image file name).
Headings recognised 0/14 and notes linked 0/2: the known Docling-HTML gaps, now measured. One grader rule came out of
it: when several route units together cover one key block or note, they are joined **as the original prints them**
(nothing between adjacent pieces, a space where the original has one), read from the original's bytes, not assumed.
Not done here: ranking, held-out files, other tools — Step 4.

## 14. Organisation and limits set on 2026-10-03 (owner's requirements restated)

`anchor.py` finds text in the original · `grade.py` scores · `adapters/` turn one tool's output into the common format
(one small file per route, run under that tool's own environment; the grader stays standard-library) · `checks/` prove
the grader on real originals · `tests/` prove every rule. Memory of the visible-text map grows with visible characters,
not with markup (a 22 MB inline-XBRL 10-Q: 1.1 s, 48 MB peak). Every tolerance comes from the key record, the guide or
the original's bytes and is flagged in the output; no company names, no literals from filings, no per-case branches.
Route runs (route files, raw tool output, graded results) live outside the repo under `/home/faisal/prepare_work/grader_runs/`.

## 15. Rules added from the first two full development runs (2026-10-03)

Reading the failures of Docling-HTML and edgartools over all 60 development HTML files, one by one, separated tool
defects from grader strictness. Grader rules added (tests first), each from the key, the guide or the medium:

| Real layout | Rule |
|---|---|
| A heading laid out as two or three adjacent cells of a one-row table | a heading may equal the join of consecutive carriers |
| One source cell holds the title **and** the unit line / basis words the key records in other fields | `same()` may set aside the record's **own** other literal pieces (flag `joined_with_own_pieces`) |
| A note printed `(1) For…` where the key has `(1)For…` | the mark is set apart before comparing |
| A qualifier sentence split by the tool at a bold cross-reference | containment is checked in the joined carriers |
| A time-only section row in the label column (`Year ended December 31:`) | no column coverage demanded for label-column rows |
| A word broken or glued by the tool (`Ma nagement`) | still a failure, now reported as `spacing` so the cause is visible |

Linker: two passes — long texts (≥ 20 search characters) placed in reading order first, short texts only between
their anchored neighbours (a synthetic title "Document" or a word like "Target" can no longer drag the cursor);
nearest-earlier fallback is flagged `out_of_order`; the piecewise fallback was removed (no real user; it guessed).
Only pictures take a gap anchor; empty or control-only texts get none. Character classes (whitespace and format marks,
quotation marks, dashes, brackets) come from the Unicode database, not from hand lists; CSS that hides text
(display:none, visibility:hidden, opacity:0, font-size ≤ 1pt) is hidden text.

Tool facts measured so far (development HTML, both routes): no headings recognised; Docling breaks words at styled
spans in some filers' markup; neither tool links footnotes or resolves references; header colspans that stop short of the
value column fail association in both; pictures carry no text on the HTML routes.

## 16. Development scoreboard, 2026-10-03 (HTML files; provisional, no ranking)

60 development HTML files, 231 targets each route, after every rule in §15 and the title/own-pieces rule.
Docling-HTML: cells 112/171 pass, blocks 23/60; text lost 1,362 characters; ~232k characters of its text could
not be placed (its hyperlink text is duplicated in contracts — a tool text change, see the review folder).
edgartools: cells 125/171, blocks 19/60; text lost 362,823 characters (prose inside inline-XBRL wrappers; one
exhibit 84 % missing); honest anchors. Both: 0 headings recognised, 8 notes linked, 0 references linked; header colspans
that stop before the value column fail in both; XML and PDF targets not converted by either HTML route.
Runs: `/home/faisal/prepare_work/grader_runs/`. Review of the key package and contract: `/home/faisal/prepare_work/review_0729_claude/`.

## 17. Step 4 pieces built on the owner's GO (2026-10-03)

| Piece | File | What it does | Rules |
|---|---|---|---|
| Docling PDF route | `adapters/docling_pdf.py` | native PDFs: Docling's page boxes become the key's top-left regions (a block over two pages carries two anchors); HTML originals: headless-Chrome print → Docling → shared linker to the **original** bytes (the print is a derivative) | FAST tables, heading hierarchy on, OCR on (picture text) |
| Heading pre-step (P7) | `adapters/prestep_headings.py` | before an HTML tool runs, wraps lines the guide calls headings (short, standing alone, not a sentence, bold/underlined/capitals) in `<h2>`; visible characters untouched; anchors still point at the original | guide 2.1 only; no words of any filing |
| Screen-span step (P20) | `adapters/screen_grid.py` | renders the original in headless Chrome, measures every cell's box, derives screen columns from pixel edges and re-grids a route's cells by their byte anchors | guide 3.5 rule 3 ("a header covers the value when the value sits within the header's span on screen"); geometry only |

All three are route-side; the grader is unchanged by them. Runs under `/home/faisal/prepare_work/grader_runs/`:
`docling_pdf_dev_*`, `docling_html_headings_dev_*`, `*_screen_dev_*`.

## 18. Rules added from the heading/screen/PDF round (2026-10-03, later)

- Footnote text: the note's **body** (its own mark set apart) must sit at the note's anchor — alone, with a space the
  original lacks, split into pieces, or inside a "Notes:" block that holds several numbered notes (guide G4). Found on
  13 Docling targets (Levi, Lincoln, MetLife, a slide deck's notes block).
- Docling adapters use Docling's **own formatting flags**: superscript pieces are footnote marks, strikethrough pieces are
  struck text; hyperlinks are links. The mark-shape heuristic is gone from the adapters.

## 19. Codex's verdict on the 0729 review, re-derived (2026-10-03) — each rule checked against the requirements, then measured

Codex reviewed `prepare_work/review_0729_claude/` and asked for changes on five grading points. None was taken on authority;
each was re-derived and, where possible, measured on the real routes (`review_0729_claude/ROUND2_FOR_CODEX.md`).

- **Quotes (B1).** Fold only within a class: curly ↔ straight double, curly ↔ straight single. The earlier all-in-one fold was
  a bug of mine (the Unicode name of ASCII `"` has no "DOUBLE"); `6"` must never equal `6'`.
- **Wrong link (E6).** A reference whose explicit `to` points at a block that is not the destination fails with
  `wrong_link`; a missing `to` with the right destination elsewhere is only a structure miss (`reference_linked`).
- **Joining pieces (B4).** The key text decides, not the original's bytes: the ordered pieces must spell the key text; a piece
  boundary may not fall inside a word of the key; the spacing inside a piece must equal the key's (`Grader.pieces_match`,
  reasons `text` / `word_split` / `spacing`). Used by printed_text, lead-in, notes, basis and multi-cell headings. The
  byte-based separator rule is gone.
- **Time rows in the label column (B7).** A period part that is neither on the value's row nor over its column must be a
  row-group heading: above the value (`order`), with no label-only row between it and the value that is not the target's
  own label text (`scope`; own = row label, row context, basis, unit, title, corner, period parts). Measured on both
  screen-span routes: 49 such cells in development, 44 on the value's row, 5 above with only own rows between, 0 below,
  0 foreign — no development verdict changes; Codex's negative case (value moved under the other dated group) now fails.
- **Hidden text (B9).** Font size is no longer a hiding rule. Measured: the ≤1-pt rule hid **2.5 M characters of real text**
  in 69 development files, because `font-size:0` paragraph wrappers (lesl, pfgc exhibits) and
  `<FONT size="1" style="font-size:1pt;color:white">` wrappers (Arrowhead, exhibit41) have children that reset the size —
  font size is inherited and overridable, so a subtree rule is unsound. `display:none`, `visibility:hidden`, `opacity:0` and
  `ix:hidden` remain (no descendant can undo the first two in the sample; `visibility:visible` occurs 0 times in 69 files —
  a known, unbuilt limit). What they hide is counted per file (`hidden_chars` in the per-file facts) so nothing is dropped
  silently. All routes were re-linked from their saved raw output after this change.
- **Not changed.** Codex's remark that the scanned-page control copies the key transcription is true: that control tests
  joining and fault detection; OCR accuracy is the PDF route's word-error-rate measure.

## 20. Final contract alignment (2026-10-03, after package 1134) — the grader implements E1–E17 as frozen

The round-2 package `FINAL_KEY_FOR_CODEX_20261003_1134` froze the contract (`CONTRACT_DECISIONS_R2.json`, copied verbatim into
`benchmarks/prepare/golden/`). Three of its texts corrected my §19 rules; the code now follows the frozen text:

- **E12 pieces of one passage.** Unchanged: the pieces must spell the key text, spacing inside a piece must equal the key's, a
  lost space between words fails (`spacing`). Changed: a piece boundary inside a word is a fault **unless the pieces' own anchors
  prove adjacency in the source with nothing, not even a space, between them** — span-level output is faithful output; such joins
  are counted (`detail.fragmented`) so "unresolved joins stay explicit". Without that proof, `word_split` fails.
- **E15 time rows.** Changed: a label-column time heading's scope ends only at a **competing time heading the key knows** —
  a cell some record's period part anchors, or a label-only row whose text equals a period part of any record in the file. An
  unrelated label or lower-level subheading between the time row and the value no longer ends the scope (my §19 rule did, and
  the contract says it must not). Still: the heading must stand above the value (`order`); column-type parts must cover the
  value's column (`column`). Limit, stated: a competing group whose heading no record anchors and whose text matches no known
  period part is invisible to this rule.
- **E16 hidden text.** The visible-text scanner keeps an element stack: `display:none`, `opacity:0` and `<ix:hidden>` hide every
  descendant; `visibility:hidden` is inherited but a descendant with `visibility:visible` is visible again (0 occurrences in the
  69 development files; implemented because the contract and CSS say so). Font size is not a hiding rule. Hidden characters are
  counted per file (`hidden_chars`) and reported, never graded.
- **Key and code home.** Key = package 1134 (its 5 excluded fields come from `CLAUDE_KEY_FLAGS.json`, read by `load_key`); the
  grader lives in `benchmarks/prepare/grader/`, the key record in `benchmarks/prepare/golden/`; commands run from the repo root
  as `python3 -m benchmarks.prepare.grader.<module>`; `--key` defaults to the recorded package.
- **Linker: marks before the text (found by the first full run, 2026-10-03 12:05).** 93 Docling cells failed the honest-anchor gate because
  their superscript mark is printed *before* the cell text (`<SUP>1</SUP>Under the company name of…`, Articles of Association) or before
  the last piece, and the linker only extended an anchor over marks that follow the text. Now the search key is text+marks, then
  marks+text, then the text alone, and **the earliest start wins**: in a two-column layout where each column's mark precedes its text, the first
  column's text+mark would otherwise swallow the second column's leading mark (run 2 still showed 85 such cells; run 3 after this rule is the
  reported one). Final rule (run 5): the search tries marks+text, text+marks and the text alone (earliest start wins; the
  longer key on a tie), then every mark not yet covered is tried once right before the text (never past the window start) and once right
  after it — so a mark before and another after the same text are both covered, and no mark is counted twice. The honest-anchor gate matches: each
  reported mark is stripped once from whichever end of the anchored text it sits at, and the rest must be the cell text — so one mark
  before and one after the same text is honest. Cells whose mark is not adjacent at all stay flagged: that is the tool attaching a mark
  from elsewhere. A mark cut out of the *middle* of a
  text is still `not_in_source` — the route's text does not exist contiguously in the source, which is the honest answer. One real
  cell (`[__]` with marks 38 and 39, only 39 present) stays flagged: the tool attached a mark from elsewhere. Fairness note: this gate
  bit only Docling because only the Docling adapter reports marks from the tool's formatting; the fix is in the shared linker.
- **Proof after the change.** 116 unit tests, 42/42 real-original pairs; all routes re-linked and re-graded with the final code
  (`/home/faisal/prepare_work/grader_runs/final_1134_20261003.log`; final table in `REVIEW_HANDOVER.md`, run of 12:36; §16 is the
  earlier provisional board and is superseded by it).

## 21. Codex's independent grader review (2026-10-03, `prepare_work/grader_review_codex_20261003/`) — what changed

Codex found wrong passes and wrong failures with 27 synthetic probes, 22 development-original checks and 4 browser comparisons.
Each point was reproduced here first, then fixed with a test; their probe scripts were re-run against the live code afterwards
(`FABLE_RESPONSE.md` in their folder has the per-case outcomes). Numbers after the fixes: 139 unit tests, 48/48 real-original variants.

| Codex | Change made | Where |
|---|---|---|
| R1 missing content looked complete | a picture's gap anchor is flagged and never counts as coverage; a PARTIAL route, a file without a text layer, or stylesheet-dependent visibility leave coverage **not measured**, and a gate with any unmeasured file does not pass (`measured_pass` says what the measured files did); the Markdown says "not measured for …" instead of yes | `anchor.link`, `gates_for_file`, `run`, `markdown` |
| R2 positions not validated | text without a position counts as `unanchored` (gate fails); byte anchors must lie inside the file; PDF regions must lie on their page (routes declare `pages` sizes; without them the file is not measured); a route file naming another source is NOT_CONVERTED; the checking mode comes from the key's format, not the output's file name | `gates_for_file`, `run`, `RouteFile`, adapters declare `pages` |
| R3 text map vs browser | tags are lexed with quoted attributes (`title="a > b"`), only the `style` attribute is read for hiding and for `display`, a `display:block` span separates and a `display:inline` div does not; a document whose stylesheet rules can hide (`display:none`, `visibility:hidden`, `opacity:0` in `<style>`, or an external sheet) is **uncertain**: its coverage and anchor honesty are reported, not certified (0 of 69 development files) | `anchor._TOKEN/_STYLE/_DISPLAY/_SHEET`, `Visible.certain` |
| R4 contradictions passed | a note unit whose declared mark is not the key's mark fails (`wrong_note_link`); every explicit link for a phrase must point at the destination; E15 time scope now comes from the source mapping: the rows the route puts between the time heading and the value must lie between them in the source, and the heading must precede the value (`order`/`scope`) — no key date list, no hard-coded words; Codex's "unknown competing group" probe fails as it should | `footnotes`, `references`, `periods` |
| R5 XML namespace | the leaf's expanded name must be one the source prints for that path and local name (`namespace`); prefixes may differ, URIs may not | `grade_xml`, `xml_names` |
| R6 erased information | values compare piece by piece like every other field (`spell` → `pieces_match`): "1,9 70" across two cells fails with `spacing`, pieces at one grid position proven adjacent in the source pass (§23); a trailing bracket is set aside only when it, or the whole line, is one of the record's own pieces (E13); range partners likewise | `value`, `spell`, `same`, `own_bracket_off`, `range_` |
| R7 correct forms rejected | `kind` is a recognition count like `heading_recognised`, never a target failure; a within-word split whose pieces have only page regions is **unresolved** (`adjacency`), not a fault | `STRUCTURE`, `pieces_match`, `grade_structure` |
| R8 adapters measured different things | neither adapter re-sorts units: the gate measures the tool's reading order for both; Docling's furniture is a `layer`, excluded from the order count; a footnote or caption body the tool attached only to its table is emitted once, right after the table | `adapters/docling_html.py`, `adapters/docling_pdf.py` |
| R9 inputs and results | a source without a split assignment stops the run; gate details of any file holding a held-out target are counts only and `unresolved` ids are filtered; `run_facts` records key, manifest and catalog hashes and checks the key files against the frozen manifest; sources resolve through the manifest's `evidence_root`; converters read `load_sources` (files, hashes, splits — no answers) | `load_key`, `load_sources`, `evidence_root`, `run_facts`, adapters, `screen_grid` |

**E13 refinement after the run (13:51) — superseded by C8 (§22) and validated in §23:** the sibling-record borrowing introduced here
was removed in round 3; a title, header or corner cell may set aside only a line the key declares as this table's context, at an anchor
that reads the phrase inside the table. The SL Green ratio records keep failing until a package declares that context.

**Where I disagree, and why (stated for the next review):**
- *Whitespace in the honesty gate (R6, last point).* The gate certifies **position**: the source bytes at the anchor spell the claimed
  text. Whitespace differs legitimately between source bytes and rendered text (indentation, line breaks inside a cell), so the gate
  keeps comparing without whitespace; spacing damage is a text fault and is caught per target by the value and text checks. Making
  the gate whitespace-strict would flag honest routes on layout whitespace.
- *Stylesheet-hidden text (R3, case 3).* The scanner does not apply class rules and will not grow a CSS engine; such files are
  marked uncertain and their gates not measured. This is the "mark visibility unresolved" option from the review.
- *E14 explicit header association (R7).* The common format's grid **is** the declared representation today; geometry is a declared
  separate route. An explicit association field is not built until a tool offers one; this is a stated limit, not a hidden fail.

## 22. Codex's round 3 (2026-10-03, `grader_review_codex_20261003/ROUND3_CODEX.md`) — eight corrections, each reproduced first

| Codex | Change made (with a failing test first) | Where |
|---|---|---|
| C1 frozen inputs verified before reading | `verify_inputs` runs before anything is read: the key files must be pinned by `FINAL_MANIFEST.json` and match; every packet's `targets.json`/`manifest.json` pinned in `packets_sha256` must match; a manifest that pins nothing, or disagrees, **stops the run**; without a manifest the run is marked unverified (fixtures). Identities are recorded in `run_facts`. | `grade.verify_inputs`, `run` |
| C2 XML occurrence and value | `xml_element_at` (expat, byte positions) gives the expanded name of the element whose text the key's anchor covers — this occurrence, not a same-named sibling; a source that does not parse makes value and label **unresolved** (`input_invalid`), never a pass; XML values use the same boundary-preserving comparison (`1 0` ≠ `10`) | `grade.grade_xml`, `xml_element_at` |
| C3 visibility certainty | tags are parsed into attributes (first occurrence wins); only the `style` attribute's declarations count, the last declaration wins, `!important` is ignored; the `hidden` attribute hides unless `display` says otherwise; `<template>` content is never text; `visibility` inherits unless a child sets it; a stylesheet that declares `display`, `visibility` or `opacity` (or an external sheet) makes the file **uncertain** (gates not measured) | `anchor._ATTR/_DECL/_SHEET`, `Visible` |
| C4 unknown is not pass | files that were not graded (failed, unsupported, input mismatch) appear in every gate's `not_measured`, so a run whose only input failed passes no gate; a PDF route's own page sizes certify nothing: regions are **not measured** for honesty, their consistency with the declared sizes is reported apart (`bounds_inconsistent`) | `gates_for_file`, `run` |
| C5 boundaries outside sampled targets | at every anchored unit and cell the gate now also compares the text with its boundaries (whitespace collapsed, marks set aside): same characters with a lost or added word/number boundary count as `boundary` and fail the gate; the whitespace-free search stays the locator | `gates_for_file`, `marks_off` |
| C6 bounded joining | `fused` tracks reachable positions in the wanted string instead of building joins: 22 fragments cost nothing | `grade.fused` |
| C7 reference scope | only a reference's own edges (same phrase or href) can establish or contradict its destination; the fallback to unrelated links is gone | `grade.references` |
| C8 table context scope | the sibling rule is gone; a title/header/corner comparison may set aside a line only when the key declares it as **table context with a source anchor inside this table** (support entry `table_context` with pieces `{text, byte_ranges}`); the current frozen package declares none, so the SL Green ratio records keep failing until the next package carries the declaration | `Grader.__init__`, `table_title`, `header_path`, `corner_text` |

Also merged from the measured experiments (DOCLING_FEATURES.md, run B): **piecewise anchoring** for long units the exact search cannot
place (`link_flag: pieced`, `pieces`, `inserted_chars`; the gate certifies the matched blocks and counts the tool's insertions), the Docling
adapter reads a rich cell's **leaf** pieces through nested groups, and the EdgarTools adapter keeps a paragraph's **heading node** as a
heading unit plus the rest. Two refinements from the re-read: entity-safe XML chunk ends; CSS `inherit`/`unset` for visibility.

**Positions stated for the reviewer:** an empty or incomplete manifest refuses the run rather than reporting "unverified" (a broken frozen
package must not produce a report that reads like results); PDF position honesty stays unmeasured until an independent page geometry
exists (stdlib has none; the route's own sizes are self-consistency only); the boundary gate compares collapsed whitespace, never raw
indentation. Numbers after this round: 155 unit tests, 48/48 real-original variants; Codex's rounds 1–3 scripts re-run against this code
behave as expected (`FABLE_RESPONSE_R3.md`).

### 22a. Two rules sharpened by the third review pass (2026-10-03, after run 9)
- **Boundaries are words and numbers, not punctuation spacing.** Run 9's new `boundary` gate flagged 25,806 Docling and 8,609 EdgarTools
  places; reading them showed almost all were spaces beside punctuation or symbols ("December 31 , 2025", "( 973 )", "$ 37.81",
  "• Institutional") — whitespace reflow that E12 explicitly allows when word/number boundaries survive. One rule now serves the gate,
  the value join and the text comparisons: `boundary_equal(a, b)` = same characters once whitespace is removed **and** the same
  sequence of words and numbers (`\d(?:[\d.,]*\d)?|\w+`, Unicode categories, no word lists). So "Ma nagement", "6 50", "1,9 70" and
  "1 ,970" fail; "3.7 %" and "December 31 , 2025" pass. Consequences stated for the reviewer: Codex's development mutation on a percent
  value ("3.7%" → "3.7 %") now passes by this rule; 22 bare numeric fragments return False from `fused` (nothing proves they form one
  number). Pieces of one value cell that share a grid position and whose anchors prove source adjacency do spell the value (E12; §23 R4-5).
- **Linker: unambiguous texts first, repeated copies claimed once.** Run 9 left 298k characters uncovered on one contract exhibit whose
  identical signature pages a tool listed out of order; the old cursor walked onto the wrong copies. Now pass 1 anchors long texts that
  occur exactly once in the source (order-independent), pass 2 places the other long texts inside the window their anchored neighbours
  leave — an exact copy no other unit holds beats an approximate alignment, which beats the nearest earlier copy — and pass 3 places
  short texts in their window only (never far ahead by elimination). A unit placed before one the tool listed ahead of it is flagged
  `out_of_order` by position. Tests: three identical signature pages with the second heading emitted early are all covered once.

### 22b. Codex's round-4 preview (2026-10-03, relayed by the owner) — reproduced and closed before the formal note
- **Added text passed through the pieced linker.** "do not" inserted into a long paragraph no target covers was anchored piecewise with
  `inserted_chars` 5 and every gate still passed: the count was reported but not judged. Now any inserted character fails the anchor gate
  (`clean` requires `inserted_chars == 0`); the per-file counts stay. Text the tool adds is text the source cannot certify, whatever the
  size; rule lines and flattened table rows therefore cost EdgarTools the gate on the files where it adds them — correctly.
- **"Verified" overstated.** A run was verified when the key files and the pinned packets matched, although the split list
  (`case_catalog.csv`, which decides what is public) was only hashed, not pinned, and a packet pinned by its manifest alone left its
  target file unverified. Now: a packet pinned without `targets_sha256` stops the run; without a `catalog_sha256` in the frozen
  manifest the run proceeds but is reported **unverified: catalog not pinned** (`run_facts`). Package 1134 does not pin the catalog, so
  runs against it say so until the next package carries the hash — a key-side item alongside the table-context declaration.

## 23. Round 4 (2026-10-03, Codex's `ROUND4_CODEX.md`) — six findings, all reproduced, all closed

| Finding | Reproduced problem | Change | Proof |
|---|---|---|---|
| R4-1 pieced text passed | the insertion was counted but not judged (closed in §22b); the gate also trusted the unit's own `inserted_chars` (a tool reporting 0 passed) and skipped the boundary check inside blocks | the gate derives the insertion from the blocks (text length − block lengths), refuses malformed or overlapping `pieces` (`dishonest`) and checks each block's word/number boundaries (`boundary`) | tests: under-reported count, overlapping blocks, split word inside a block, deletion (0 inserted, source text uncovered), unchanged control; Codex `linker/*`: the three mutations fail `honest_anchors`, the control passes |
| R4-2 freeze check incomplete | pins of unconsumed packets counted; a packet name in two folders resolved to the unpinned copy; a pinned key file that was missing was skipped; an empty pin entry passed | one resolver, `packet_dir`, for loading and verification: the manifest's pinned path, else the one folder that exists, never a choice between two (two folders = refusal). `verify_inputs` resolves the packets the answer key names and requires `targets_sha256` for each at that path; a key file pinned and missing, or present and unpinned, stops the run | tests (four refusals + control); Codex `freeze/*`: four refusals with named reasons, control accepted |
| R4-3 visibility certified wrongly | five inline-CSS cases disagreed with Chrome while `certain` was true | attribute entities decoded; CSS comments stripped; `!important` beats a later plain declaration; `visibility` by the spec (hidden/collapse hide, visible shows; inherit, unset, absent or invalid keep the parent's); a hiding property given `var()`, `calc()` or an escape makes the file **unmeasured** — no CSS engine | test with Chrome-observed expectations; Codex browser probe 11/11 agree or unmeasured |
| R4-4 unbounded alignment | a 20k-character repetitive paragraph with one inserted character drove difflib past 2 s CPU (killed); on real output difflib was already slow: 188 s for the 24 pieced units of one EdgarTools file | anchor chaining in `piece`: the 20-grams unique in the text and unique in the source segment are anchors, the longest order-consistent chain of them is kept (longest increasing subsequence), each anchor is extended to its maximal run of equal characters. Measured on that file (346,487 characters): difflib 332,275 matched in 187.6 s; a left-to-right greedy re-sync 299,746 in 0.17 s (under-matches reordered notes); the chain 330,417 in 0.35 s. Over every pieced unit of the three linker routes (108 units, 463k characters) the chain matches more than the greedy pass on all three routes; 2 small units (705 and 662 characters of repeated phrases, one file) have no unique anchor and stay unanchored — stated. It never claims text the source lacks; what it misses is counted as insertion, never hidden | test: 20k repetitive text + 1 character → pieced, 2 blocks, 1 inserted (19 ms); earlier piecewise tests unchanged; Codex's probe 0.019 s |
| R4-5 faithful fragments rejected | `<span>12</span><span>34</span>` kept as two anchored pieces at one grid position failed `spacing` | values use `pieces_match` like every field, with one rule added for cells: pieces may join inside a word only when they share a grid position (two cells show two numbers whatever the bytes say) **and** their anchors prove source adjacency; page boxes only → `unresolved: adjacency`; range partners likewise | tests: same cell, adjacent → pass; two columns → `spacing`; anchors apart → `spacing`; PDF boxes → unresolved; split partner → pass; Codex `numeric_fragments/*` both pass |
| R4-6 context guard too loose | a `governing` span or any overlapping range admitted a phrase | admission needs `byte_ranges` that each lie inside the table anchor **and** read the phrase; `governing` is not evidence; anything else raises `ValueError` naming the record — a key defect stops the run instead of being guessed around | tests: literal anchor → admitted, the joined title passes; container cell, whole table, outside phrase, whole document → refused; Codex `table_context/*`: three refused, the valid one admitted |

Where this differs from the note's wording, stated: (1) a packet pinned at one path while a same-named folder exists at the other is
**refused** as ambiguous, not resolved to the pinned copy — a stray copy beside a frozen input is a defect to remove; (2) an invalid
context declaration **stops the run** rather than being quietly not admitted; (3) Codex's probe control shows `verified: false` under the
live grader because its synthetic manifest pins no catalog (§22b), not because a check failed. Stated limits: an invalid `display` value
(`display: nonsense`) is treated as a block for spacing where the browser ignores it; `<noscript>` content is read as visible;
colour-on-colour text is visible to this scanner (key-side question, Arrowhead). Documentation: README paths and test count corrected;
the superseded sibling-context and number-joining statements are rewritten in place (§21, §22a, R6) rather than contradicted below.

## 24. Round 5 (2026-10-03, Codex's `ROUND5_CODEX.md` on commit beb22d591) — four defects, all reproduced, all closed

| Finding | Reproduced problem | Change | Proof |
|---|---|---|---|
| R5-1 joins between mapped blocks | with every block reading its own text, an output could glue two words ("Revenueincreased."), split a number ("12 34") or reverse the source order ("Beta Alpha") and pass every gate | the pieced branch now also checks each transition: blocks must be in source order (else `dishonest`), and where both edge characters are letters or digits the output may have no boundary only if the source prints nothing between the two spans, and must have one otherwise (`boundary`). Boundaries beside punctuation or symbols stay reflow | tests: five cases incl. two controls; Codex `piece_joins/*`: controls pass, three mutations fail `honest_anchors` |
| R5-2 changed pinned catalog | a pinned `catalog_sha256` that did not match was treated like an absent pin: the run continued unverified and a split moved from held-out to development exposed detail | missing pin → explicitly unverified (unchanged); present and different → `ValueError` before any answer is loaded | test; Codex `catalog/*`: control verified, missing pin unverified, changed catalog refused |
| R5-3 CSS certified wrongly | seven inline-style cases disagreed with Chrome while certain: an invalid later value overrode a valid earlier one, `revert`/`revert-layer` were read as visible, a comment inside a name or value was removed by concatenation and invented a declaration | declarations are read in order and resolved per property; `display`/`visibility` values outside the CSS keyword lists, non-numeric `opacity`, `var()`, `calc()` and escapes make the file **unmeasured** instead of being guessed; `revert`/`revert-layer`/`inherit`/`unset` keep the parent's visibility; a comment is a token boundary (replaced by a space). No CSS engine. On the 116 HTML key sources no value triggers the unmeasured rule | test with Chrome-observed expectations (12 cases); Codex browser probe 10/10 agree or unmeasured |
| R5-4 PDF range partner | a partner split inside a number across page boxes gave `fail: partner` where `value` says `unresolved: adjacency` | `range_` returns `unresolved: adjacency` when only boxes could prove the join; a whole partner passes; wrong digits or a split across columns still fail | test; Codex `pdf_range/*` all four as expected |

Results after the round (run 15, regrade only — the linker did not change): identical to run 14 except one more `boundary` on EdgarTools (929) and three on
the PDF route (97), from the join check. 166 tests, 48/48 real pairs. Stated limits unchanged from §23.

## 25. Round 6 (2026-10-03, Codex's `ROUND6_CODEX.md` on the round-5 code) — three gaps in rounds 4–5 fixes, all reproduced, all closed

| Finding | Reproduced problem | Change | Proof |
|---|---|---|---|
| R6-1 join read only the gap | the §24 join check read the bytes *between* spans: a span that carried its own leading or trailing space made a kept space fail and a lost space pass; the letter-or-digit exemption let "12.34" → "12. 34" and "1,234" → "1, 234" through | one comparison for the whole pieced unit with the ordinary boundary rule (`boundary_equal`): the source read block by block (each span with its own whitespace, a separator wherever the source prints anything between two spans) against the output read block by block (a separator wherever the output prints anything between two blocks) — same words and numbers inside blocks and across every join; no hand exemptions; the source-order check stays | tests: 9 join cases (4 controls); Codex `join/*` all nine as expected |
| R6-2 unresolved hid a wrong row or order | a partner split by page boxes went straight to `unresolved: adjacency`, even on the wrong row or the wrong side of the target | row and endpoint order are checked first (provable from the boxes); `unresolved` only when the association holds and only the join is unprovable | tests; Codex `range/*` six as expected |
| R6-3 CSS still certified | `bad display:none` matched by suffix; `NaN`/`inf` accepted as numbers; `-0.1` not clamped; a stylesheet rule split by a comment missed by the detector | a declaration is one complete `name: value` (split on `;`, matched whole); a CSS number is `<number>`/`<percentage>` by grammar; opacity ≤ 0 hides (clamped); stylesheet detection strips comments first and looks for the hiding properties; everything else → unmeasured. 0 of 116 HTML key sources become unmeasured | test with Chrome-observed expectations; Codex browser 8/8 agree or unmeasured |

Results after the round (run 16, regrade only): identical to run 15. 166 tests, 48/48 real pairs, Codex rounds 4–6 scripts pass live.

## 26. Key package 2 and the ledger's key-side items (2026-10-03 20:14, owner's order "finish everything key-related end to end")

**Package `FINAL_KEY_FOR_CODEX_20261003_2014` supersedes 1134** (1134 untouched, read-only). Built with the package's own tools (`claude_support_map.py`,
`final_pass/freeze_package.py`), gate `VERIFY_PACKAGE.py` passes, `golden/check_package.py` passes, grader runs report `verified: true`.

| changed | what |
|---|---|
| `KEY_SUPPORT_OVERRIDES.json` → `KEY_SUPPORT_MAP.json` | 12 SL Green records (two filings, T02–T07) gain `table_context`: the title cell's lines "Unaudited" and "(Dollars in Thousands …)" anchored byte-for-byte; the regenerated map differs from 1134 in exactly those 12 slots |
| `FINAL_MANIFEST.json` | pins `case_catalog.csv` (`catalog_sha256`); `VERIFY_PACKAGE.py` checks it |
| `CONTRACT_DECISIONS_R3.json` (new, copied to `golden/`) | six clarifications, PROPOSED until Codex's check: C1 table context in the table or its title block · C2 change values' periods · C3 Arrowhead 1-pt text is content · C4 symbol spacing (Codex-approved in round 4) · C5 row-context headers in continued tables, a text printed twice · C6 lead-in across the source's own page furniture, contained whole |
| tooling | `claude_support_map.py` accepts the slot; `freeze_package.py` pins the catalog; `test_support_overrides.py` +2 tests |

Unchanged, proven by diff: the 457 answers (bytes), flags, pending, stamps, decisions, raw answers, every packet hash, the catalog (now pinned, not edited).
Left as reviewed: three change-column records carry `value`/`comparison` roles where guide 3.10 reads both `compared` (no direction printed); C2 treats both forms
alike, so no score depends on it — flagged for Codex.

**Grader changes that make the key items effective (each with a test, Codex's rounds 4–6 probes unchanged, 170 tests, 48/48 real pairs):**
- C1 `Grader.__init__`: a context piece is admitted inside the table **or its title block** (from the declared title's anchor to the table's end) — SL Green prints
  the title block in an outer cell above the nested data table; a phrase after the table, or a container, is still refused.
- C2 `periods`: for a value with a `compared` or `comparison` group the column-type parts must head columns of the same table above the value; the value's own
  column (the change column) is proven by `header_path`, which still fails when the value moves under a compared column.
- C5 `row_context`: every cell printing the item's text is considered (a row may print a company twice); the header may sit in the first part of a continued
  table, as `header_path` already allowed.
- C6 `lead_in`: units the route prints between the lead-in and its table are not a displacement when the source prints them there too (page furniture); a
  lead-in kept whole inside a larger unit counts as present (`contained`).

**Run 17 (regrade only, package 2):** EdgarTools + screen 134 → 159 cells — exactly the 12 + 6 + 5 + 2 targets above; Docling render 129 → 154. Of 231 HTML
development targets the best single route now passes 202 (87 %), the best pick per target 208, and 23 pass on no route: picture text 8, contract-exhibit
headings 8, footnote marks glued into cells 7 — all tool-side.

| route | HTML cells | HTML blocks | PDF targets | headings recognised | unanchored | boundary | inserted chars | uncovered chars (files) | reading-order breaks (files) | anchors not measured |
|---|---|---|---|---|---|---|---|---|---|---|
| Docling HTML | 138/171 | 44/60 | - | 0/155 | 1058 | 637 | 209 | 13,767 (13) | 9 (2) | 0 of 60 graded files |
| Docling HTML + screen | 144/171 | 44/60 | - | 0/155 | 1058 | 637 | 209 | 13,767 (13) | 9 (2) | 0 of 60 graded files |
| Docling HTML + headings | 140/171 | 39/60 | - | 104/150 | 1215 | 662 | 364 | 19,439 (22) | 29 (8) | 0 of 60 graded files |
| Docling HTML + headings + screen | 146/171 | 39/60 | - | 104/150 | 1215 | 662 | 364 | 19,439 (22) | 29 (8) | 0 of 60 graded files |
| edgartools HTML | 151/171 | 40/55 | - | 35/166 | 180 | 929 | 22,494 | 30,585 (41) | 15 (6) | 0 of 60 graded files |
| edgartools HTML + screen | 159/171 | 40/55 | - | 35/166 | 180 | 929 | 22,494 | 30,585 (41) | 15 (6) | 0 of 60 graded files |
| Docling HTML, browser render (no screen step) | 154/171 | 48/60 | - | 0/169 | 696 | 329 | 209 | 13,594 (11) | 0 (0) | 0 of 60 graded files |
| Docling PDF route (14 files) | 15/46 | 1/7 | 4/9 | 13/24 | 3179 | 97 | 1,782 | 46,391 (7) | 374 (16) | 9 of 17 graded files |

## 27. Round 7 and the package-2 verdict (2026-10-03 evening) — seven findings plus two corrections, all reproduced, all closed

**Codex's package-2 verdict** (`PACKAGE2_CODEX_VERDICT.md`): package integrity and the 12 context declarations **approved**; the three questioned period
roles **kept** (the originals state the direction in the surrounding text: Carnival's heading "2021 Compared to 2020", Duke's and Levi's discussions);
C3–C6 approved; two corrections, both applied:
- **C1 wording.** SL Green's title block is a *separate* layout table that closes 79 bytes before the data table opens — not a nested table as §26 and the
  test said. The rule is unchanged (context admitted between the declared title's anchor and the table's end; each line must read its anchor); the
  test now uses the real sibling layout first and the nested shape only as a second control. The frozen addendum text in package 2 keeps the wrong
  word "nested" in its C1 reason; the correction travels with the next package.
- **C2 group association.** "Same table, above the value" let year headings swapped into the other group pass. Now a compared column's heading must
  belong to the value's group: the headers above it that cover its column — leaving out the record's own period headings, which are time, not group —
  must include one that also covers the value's column; a heading with nothing but period headings above it stands in the table's top block. Codex's
  North/South reproducer: correct output passes, swapped headings fail `group`; Levi's three- and six-month groups are told apart the same way.

**Round 7** (`ROUND7_CODEX.md`, reviewed on eb96daa58):

| Finding | Reproduced problem | Change | Proof |
|---|---|---|---|
| R7-1 Docling adapter dropped raised-only cells | 64 nonempty cells in 3 files (a raised "(10)" alone in a cell) vanished because every superscript piece became a mark and nothing remained | a cell printed wholly raised keeps its text (the mark standing alone is the cell); rich cells also report struck pieces | adapter test; Codex's audit over all 60 saved outputs: 0 lost |
| R7-2 EdgarTools adapter shifted cells | rowspans expired only when a later cell visited the column: an empty or short row left them active, shifting 21 tables | occupancy by row (`until[column] = row + rowspan`) in the adapter and in `checks/real_pairs.py` | Codex's control (A spans 3, B spans 2, an empty row); Codex's independent occupancy audit: 0 shifted of 10,753 |
| R7-3 struck words became active | the key marks struck evidence `~~…~~`; the grader compared words only, so a lost or moved strike-through passed | `struck_kept`: the route's `struck` entries at that place must match the key's struck phrases, no more and no fewer; checked for `printed_text` and, through `field()`, for every cell field whose key text carries `~~` | tests: control passes, lost and wrong strike fail `struck`; Codex `strike/*` |
| R7-4 one boundary rule for every field | within-word fragments at one grid position failed in seven context fields (the checker inserted the space); a number split at a decimal point or comma across two columns passed | `merged()`: pieces at one grid position whose anchors touch are one cell, used by every cell comparison (`carriers`, `row_label`, `row_context`, `periods`, structure tables); `pieces_match` joins pieces as the reader meets them — a proven touching join as nothing, every other join as a space — and applies `boundary_equal` to the whole | tests: the seven-field matrix, eight numeric cases; Codex's two probe scripts all as expected |
| R7-5 unsupported browser behaviour certified | six more Chrome disagreements: `1.` as a number, `;` inside a quoted value, an escaped property name in a stylesheet, an unclosed `<p>`, a slash on `<div>`, a hidden `<br>` | CSS numbers by grammar (no trailing dot); declarations split outside quotes and parentheses; CSS escapes decoded in inline and stylesheet text; HTML implied end tags (`p`, `li`, `dt/dd`, `td/th`, `tr`, sections, `option`); a slash on a non-void HTML tag closes nothing; a hidden void element breaks nothing. **Supported subset**: inline `display`/`visibility`/`opacity` with keywords or numbers; stylesheets only detected; an implied end tag that drops unclosed hiding inline elements (the browser rebuilds them around the new block) makes the file **unmeasured** | test with Chrome-observed expectations (10 new cases); Codex's 9 cases agree or unmeasured; 0 of 116 corpus files become unmeasured |
| R7-6 exclusions on every path | the two `unit_interpretation` exclusions took the `not_t1` path and were not counted; XML and structure checks ignored exclusions | T4 fields report `excluded` when excluded; XML `value`/`row_label`/`header_path`/`row_context`/`unit_printed` and structure `printed_text` honour exclusions; the five excluded fields are counted | test; Codex `exclusion/*` |
| R7-7 coverage naming | the text map cannot prove a picture's content survived | gate `nothing_lost` states `measures: visible source text; picture content is not measured` and lists `pictures_not_measured` per file (count of `<img>`) | test; Codex `image/missing` |

Also: the `test_anchor` inline fixture had a `<div>` inside a hidden `<span>` inside a `<p>` — a shape the browser handles by rebuilding the hidden span
around the block; the fixture now nests a `<b>`, and that shape is a stated unmeasured case. 176 tests, 48/48 real pairs, Codex's rounds 4–7 scripts
and the C2 reproducer behave. Run 18 (re-link, regrid, regrade with the fixed adapters) is recorded in `REVIEW_HANDOVER.md`.

## 28. Round 8 and the first two tool tests (2026-10-03 22:00) — four shared-rule classes, all reproduced, all closed; glued marks and line-through settled

**Round 8** (`ROUND8_CODEX.md`, reviewed on eceec06a9):

| Finding | Reproduced problem | Change | Proof |
|---|---|---|---|
| R8-1 a table-wide title defeated the group rule | `same_group` accepted any header above the compared heading that also covered the value's column, so a title spanning both groups let swapped year headings pass | the innermost header row decides: among the headers above the heading that cover its column (the record's own period headings left out), only those in the lowest such row must cover the value's column; flat tables (nothing above) and multi-level groups unchanged | test: title/no title × correct/swapped; Codex `period/*` 4/4 |
| R8-2 strike-through compared by substring | `a in b or b in a` accepted `n`/`no` for `not` and `not a GAAP measure` for `not`; a one-cell layout table failed because the table unit, not its cell, was inspected | `struck_kept`: the key's struck phrases and the route's struck entries at that place, each concatenated whitespace-free in reading order, must be equal — a partly cancelled word, an extra cancelled word or a lost cancellation all fail; the items inspected are the text-bearing cells or units (a block laid out in a table is its cells), for `printed_text` and, through `field()`, every cell field | test (text units and cells, five wrong shapes); Codex `strike/*`, `strike_layout/*` 9/9 |
| R8-3 E12 depended on cells vs text units | the round-7 merge covered pieces at one grid position only; faithful text-unit fragments failed table title, printed unit, basis and period (two or seven units), the heading window tried two or three pieces only, and footnote, reference and range evidence split inside a word failed | pieces that touch in the source — cells at one grid position **or** text units — are read as one carrier **where the key reads them glued** (`reads_glued`, below); `merged_units` with the key text for structure blocks and range evidence; the heading window is bounded by the heading's own length (measured without "(continued)"), not by a piece count; a period part may be read across pieces the key spaces apart | test: six fields × whole/two/per-character units, the "(continued)" piece; Codex `unit_fragment` 18/18, `related_fragment` 6/6 |
| R8-4 three scanner certainties were wrong | a hidden `<tr>` with optional end tags stayed open (the implied close stopped at the nearest `<td>`); a hidden paragraph suppressed the boundary before the next shown one; an escaped `;` inside a custom property value split a declaration | implied end tags close every open element of those kinds down to the boundary (a new `<tr>` closes the open `<td>` **and** the open `<tr>`); a word boundary comes only from an element that itself shows; declarations are split before escapes are decoded; text written directly inside a table skeleton (which the browser moves before the table) makes the file uncertain | test with Chrome-observed expectations; Codex's 9 Chrome cases agree and are certain; 0 of 116 key sources uncertain |

**Key-driven gluing (the rule R8-3 settled on, after a false step).** The first round-8 code glued *every* pair of touching text units. Run 20 showed what
that costs on real filings: "Section 1.01" + "Defined Terms" touch in the bytes, yet the key — read from the rendered page, where CSS spaces them —
prints "Section 1.01 Defined Terms" (two credit-agreement headings lost); an empty picture unit touching "Financial Trends" swallowed the heading and
its kind (fifteen `heading_recognised` counts on the pre-step route, six on the PDF route); "•" + "depreciation" became "•depreciation" against a key
that prints the bullet with a space. Touching bytes prove only that the tool inserted nothing; the key is the authority on spacing (E12, as
`pieces_match` has held since round 7). So `reads_glued(left, right, key texts)` decides each join: take the longest context around the join (up to six
characters a side) that the key text contains at all — the key may begin or end inside a piece — and glue only if the key prints no space there; a piece
with no characters never glues. Proof: each shape above is a test that fails on the previous rule (re-proved from a copy of the code carrying the old
rule), and a per-target comparison of the committed round-7 grader against this one on the same route files shows **only pass gains, no pass lost** on
any of the eight routes (Docling routes +7 to +8 targets, EdgarTools +4, browser render +10; the three heading counts back at their round-7 values).

**Tool tests 1 and 2 (owner's order, in that sequence).**
- *Glued footnote marks (ledger class F):* the tools print "Covenants (1)", "features(1):", "fibrosis1,2", "EPS (1)" as one cell text; the key spells
  the text and lists the mark apart. The grader set marks aside only at the ends of a text. Now `without_marks` deletes the record's own marks wherever
  they stand — grouped with commas or spaces, glued to a word, before a colon — with the gap closing up, and never deletes a mark that is part of the key
  text itself ("1-stage"); `minus_marks_anywhere` does the same for basis containment (linear; a first, quadratic attempt stalled run 19, which was killed
  and replaced). Verdict: a **grader comparison gap**, not a tool fault — the text is faithful, the mark is printed there. No mark-related failure remains on
  any route.
- *Line-through (ledger class I):* three credit-agreement redlines strike deleted words with CSS `text-decoration: line-through`; Docling maps only
  `<s>`/`<del>`/`<strike>`, EdgarTools reports no strikes. New declared route step `adapters/source_formatting.py` (like the screen step): the scanner records
  struck runs (the three tags and CSS line-through, inherited by descendants) and the step writes them onto units and cells as `struck` by byte-anchor
  overlap, dropping a tool's own claim where the source prints nothing struck; text and anchors untouched. Run facts: items with struck text — Docling
  2,219, browser render 3,015, EdgarTools 1,628 over 60 files. Verdict: closed by a small step; `struck` failures on every route: 0.

**Also fixed on the way.** The screen step read another step's facts file as a route file (`KeyError: 'file_id'`; its outputs were complete, its own facts
were lost) — foreign JSON files are now copied through, and the three screen routes were rebuilt cleanly (run 21: numbers identical to run 20). A method
note: with `PYTHONPATH=/home/faisal/EventMarketDB` set in this shell and `benchmarks/__init__.py` present, a copy of the grader in another folder is never
the one imported — a regular package anywhere on `sys.path` beats a namespace copy found first — so every comparison run and every "fails without the
fix" proof here prints the module path it loaded and runs with `PYTHONPATH=`.

183 tests, 48/48 real pairs, Codex's rounds 4–8 scripts behave, 0 of 116 HTML key sources uncertain. Run 23 is recorded in `REVIEW_HANDOVER.md`; the
ledger's §10 names what remains (pictures 8, contract-exhibit headings 8, two key-side items).

## 29. Round 9 (2026-10-03 22:24, Codex's `ROUND9_CODEX.md` on bc75432e6) — four required changes, all reproduced, all closed

| Finding | Reproduced problem | Change | Proof |
|---|---|---|---|
| R9-1 the key chose the join | `reads_glued` (round 8) glued touching pieces only where the key printed no space: the same output read "Cashflow" against one key and stayed two pieces against "Cash flow" — the expected answer picked the reading | joins come from the output's mapping and the source alone: pieces whose anchors touch (cells at one grid position, text units) read as one, every other join as a space; a piece with no characters never glues; comparisons apply the boundary rule, so a digit–letter or symbol join the key spaces is reflow ("1.01Defined", "•depreciation"); where touching bytes meet inside what the key prints as two words — a boundary only the page could show (CSS) — the verdict is **unresolved**, never pass or fail (`pieces_match`; glued carriers remember their joins, `spaced()`, so every field tells that case from a real mismatch) | tests: the same output under two keys gives one reconstruction and verdicts pass/unresolved; a real source space fails; Codex `new_rule_probes` key_driven_join (both keys → "Cashflow"); on the corpus the unresolved case never arises |
| R9-2A the formatting step could add or remove strikes | any `line-through` declaration counted (a later `none` ignored); `<s style="text-decoration:none">` struck; a stylesheet strike was deleted from a correct converter claim | the decoration in force is the last `text-decoration`/`text-decoration-line` declaration (`!important` first); an `<s>`/`<del>`/`<strike>` with its own declaration follows it; a parent's strike does not reach an atomic inline-level or out-of-flow child (inline-block, inline-table, float, absolute); a child's `none` does not cancel; a stylesheet rule that strikes or forces a decoration, an unevaluated value, or an `<s>` the browser would reopen in the next block make struck text **uncertain** (`Visible.struck_certain`) and the step then leaves the converter's claims untouched; the step writes only phrases the item's text carries; the raw converter routes are kept and the step writes separate `+source-formatting` routes | 20 Chrome-checked shapes (middle-band pixel oracle: 18 agree, 2 uncertain, 0 wrong); Codex `formatting_browser` 12/12, `new_rule_probes` formatting 6/6; 0 of 116 key sources struck-uncertain |
| R9-2B another row's strike failed a label | `field()` expanded a table at the anchor to every cell, so a correctly struck "Cancelled" row failed the "Obsolete" label | only the cells at this field's own support anchors (alternatives alike); a block laid out in a table: its cells at the target's anchor | test (passes beside the other row; its own lost strike still fails); Codex `strike_scope_probes` 2/2 |
| R9-3 recursion | `without_marks` recursed once per character: a 500-character marked label raised RecursionError | a forward pass over the text (sets of reached states), no recursion, bounded work | test 50–2,000 characters, marks at the end and in the middle, a mark that is text, a changed word; Codex 15/15 |
| R9-4 literal `<` | any `<` opened a tag: `Cost < 1% and margin > 5%.` read `Cost 5%.` and was certain; a bare `<` kept its text but no strike flag, so `struck_runs()` raised IndexError | a `<` opens a tag only before a letter or a slash (`<!`, `<?` handled before); the literal-`<` path keeps text, offsets and strike flags aligned | tests (escaped and literal comparisons, trailing `<`, after a struck word, real tags); Codex `formatting_browser` text cases 6/6 |

Run 24 (raw converter routes re-linked from cached tool output; the formatting step and the screen step written into their own route folders; 12 routes
graded): the step adds exactly one cell per HTML route (the redlines' struck words) and the screen step its usual six to eight; browser render + formatting
163/171 cells, 49/60 blocks; EdgarTools + formatting + screen 163/171, 42/55. Of 231 HTML development targets the best single route passes 212, the best
pick 213, no route 18 (pictures 8, contract-exhibit headings 8, two key-side items). The committed round-7 grader on the same 12 route folders: pass gains
only (Docling +8, pre-step +7, EdgarTools +6, browser render +10), no pass lost, no new unresolved. 186 tests, 48/48 real pairs, Codex's rounds 4–9 scripts
behave (his `merged_units(units, [want])` call adapted to the live signature, which no longer takes the key). Method: every comparison run and proof prints the
module it loaded, with `PYTHONPATH=` (§28).
