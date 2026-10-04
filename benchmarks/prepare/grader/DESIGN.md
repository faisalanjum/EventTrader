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
- **Optional** (reported as "structure" when present): `level`, `header`, `caption`, `markers` (footnote marks kept apart from the number), `notes`, `marker`, `links`/`to`, `struck`, `name`/`path`/`group`/`siblings`/`mixed`/`within` (XML: the containing instance, the element's own place, prose around child fields, the prose unit a field stands within). An `anchor` is one place or a list of places (a unit over several pages or boxes, a cell pieced from several spans); a page place is `{page, region}` and may carry `charspan: [start, end)` — the characters of the unit's text that lie at that place (Docling's `prov.charspan`), the only way the grader learns which words sit on which page (§37–§38). A page group converted again marks a unit that still straddles it `incomplete` (§36).
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

## 30. Tool test 3 — contract-exhibit headings (2026-10-03 23:05): a grader gap, not a tool gap

The ledger's class C (8 targets in three credit agreements) was described as "bold/centred paragraphs no tool reads as headings". Looking at what the
routes emit at the key's anchors: both tools carry every heading's text; the failing level is always the last one, a **run-in heading** — "Section 1.01
Defined Terms." continues into its paragraph in the same block — which the tools print in pieces (Docling: `Section 1.01` · `Defined Terms` · `. As used in
this Agreement…`; EdgarTools: heading `Section 1.01` · text `Defined Terms. As used…`), glued in the bytes ("1.01Defined") or parted by no-break spaces. The
run-in rule (guide V18) still demanded one carrier whose text starts with the heading, spaces exact. It now reads consecutive carriers as the source prints
them (touching → nothing, else a space) and compares the prefix by the boundary rule — the same generalisation every other field received in rounds 7–9 —
while a changed number still fails. Test: Docling's three-piece shape, EdgarTools' shape, the no-break-space shape, the negative.

Run 25 (regrade of the 12 route folders): all 8 class-C targets pass on at least one route; browser render + formatting 165/171 cells, 52/60 blocks;
EdgarTools + formatting + screen 168/171, 45/55; best single route 217 of 231, best pick 221, no route 10 = pictures 8 + the two key-side items. The
committed round-7 grader on the same folders: pass gains only (the new section-path passes are run-ins, so `heading_recognised` — a structure count —
records them as not recognised). 187 tests. Heading **recognition** by the tools stays as measured (EdgarTools calls `Section 1.01` a heading, neither tool
the two-line `ARTICLE I / DEFINITIONS`); it is a structure count, not a pass rule, and is the honest remaining tool-side fact for this class.

## 31. Round 10 (2026-10-03 23:21, Codex's `ROUND10_CODEX.md` on c20e08a94 and 5c1b6fe21) — four required fixes, all reproduced, all closed; XML note corrected

| Finding | Reproduced problem | Change | Proof |
|---|---|---|---|
| R10-1 the formatting step could still add or remove a strike | seven Chrome shapes certified wrongly: a sheet rule `s{text-decoration:none}` (a sheet can *remove* a strike), `revert` (the tag's default), an invalid value (`bogus`, dropped by the browser), a valid earlier declaration followed by an invalid one, invalid line-token combinations, `underline`/`none` sheet overrides | only **resolved** decoration values count: `none`, `initial`/`unset` (not inherited → none), `revert`/`revert-layer` (the tag's default), and combinations of the line keywords with a line style; anything else (colours, lengths, `inherit`, functions, invalid tokens) is UNKNOWN — skipped like the browser skips an invalid declaration, and the file's struck text becomes uncertain. Two certainties: `struck_certain` (no sheet rule touches decorations at all) allows writing a strike; `plain_certain` (no sheet rule can add or force one) allows dropping a converter's claim; otherwise the converter's own claim stands | tests (sheet `none` → run uncertain but plain certain; sheet `line-through` → neither; `revert`, `initial`, `bogus`, `line-through;bogus`, `line-through none`); Codex `remaining_browser` 12/12 preserved; 20-shape oracle 0 wrong; census: 2 of 116 key sources carry sheet decoration rules |
| R10-2 an invented cancellation passed | `struck_kept` returned true whenever the key marked nothing, so a route striking "not" in a plain passage, or a plain label, passed with clean gates | both directions, scoped: the route's struck phrases that lie inside the field's own text must equal the key's marks — empty when the key marks nothing; a strike elsewhere in a shared unit is not this field's | tests (plain passage + invented "not"; plain label + invented strike; lost strike still fails); Codex `remaining_probes` plain_* 4/4 |
| R10-3 a hidden literal `<` leaked | the lone-`<` branch appended text before the hidden check: `<div hidden>Secret < 1</div>` showed `<`, certain, and charged the converter with an uncovered character | a lone `<` takes the ordinary text path: visibility, hidden-character count, positions, strike flag | tests (`hidden`, `display:none`, `visibility:hidden`: text "Shown", 8 hidden characters); Codex's three hidden variants and both controls |
| R10-4 the ambiguous-join verdict was uneven | touching "Cash"+"flow" under "Cash flow": header, title, row context said unresolved; the row label said fail; the run-in branch said missing | the row label compares the spaced reading of merged cells for the unresolved verdict like every other field; the run-in branch builds the spaced reading of its window (`spaced()` for every touching join) and reports unresolved when only that reading starts with the heading | tests (row label pass/unresolved/fail; run-in heading with its paragraph pass/unresolved); Codex `remaining_probes` 12/12, `run_in_probes` 13/13 |

**Found by run 26, fixed with R10-2:** "EXHIBIT A" printed four times in a redline exhibit (0000764065-24-000206); the key's anchors name all four, and at the last one the "A" is struck (a changed letter). The invented-strike check read every occurrence the key pointed at and failed the plain heading that had matched. Now each field reports the carriers that matched (`self.matched`: section path, lead-in, title, unit, basis, header path, row label, corner) and the struck check reads those; glued runs keep every piece's object (`parts`). Test: the two-occurrence shape, pass; the same strike on the matched heading, fail.

**XML note corrected (Codex's offline check, confirmed):** `Schedule13D.parse_xml` keeps its typed lists in source order (all 8 reporting persons), so positions within such a list are derivable; element names, paths and offsets remain absent. `edgar.xmltools.parse_xml` returns an lxml tree with expanded namespace names (256/256 elements) but no byte offsets and parses with `recover=True` — a truncated document comes back as a tree. Both feature notes carry the correction; the candidate stays a small wrapper over a standard XML parser without recovery.

**Then run 27 showed the mirror image:** a lead-in spread over several pieces, its struck word in a middle piece — recording only the last piece as matched
dropped the strike and failed two correct lead-ins on the browser render. The matched set now covers every piece the match used (the lead-in's carriers,
the unit phrase's carriers, a heading's piece window, a run-in window). Test: the three-piece lead-in passes with its strike, fails without it.

Run 28 (formatting step re-applied under the two certainties, screen routes rebuilt, 12 route folders regraded): every number equals run 25 — browser render +
formatting 165/171 cells, 52/60 blocks; EdgarTools + formatting + screen 168/171, 45/55; best single route 217 of 231, best pick 221, no route 10 (pictures 8,
two key-side items; the third key-side item, Carnival's three-line header, is in the ledger). The committed round-7 grader on the same folders: pass gains only,
no pass lost, no new unresolved. Round 10 changed no corpus verdict; it removed wrong certainties (2 of 116 key sources carry stylesheet decoration rules and now
keep the converter's own strike claims) and closed the invented-strike hole. 191 tests, 48/48 real pairs, Codex's rounds 4–10 scripts behave, 20-shape Chrome
oracle 0 wrong.

## 32. XML route built and graded; picture OCR measured; Docling rows (2026-10-04 00:15, agreement points 2, 4 and 5)

**XML (point 4).** `adapters/xml_fields.py` (45 lines, standard library): the strict expat parser with namespace processing; one `field` unit per leaf element
that carries text — expanded name `{namespace}local`, the ancestors' expanded names, the place among same-named siblings of the nearest repeated ancestor
("2 of 8"), the text, and the byte span from the element's own start tag to the end of its text (so the key's anchors on the tag name and on the text both fall
inside). No field list, nothing inferred; a truncated or malformed document raises and the route file says FAILED with the parser's message (Codex's
`recover=True` finding is the reason: recovery is not completeness). Entities and CDATA sections are character data. Run on the three development forms:
209 / 225 / 367 fields, a millisecond each; graded: **9 of 9 development XML cells pass**, anchors honest (0 dishonest), nothing uncovered. Two grader gaps
surfaced and were fixed with tests: an XML unit may be the element's own name (`percentOfClass`, anchored on its tag) as periods already allowed, not only a
printed text; and the scanner's HTML skip list (`<title>` is the document title in HTML) and `<[!…]>` markup rule do not apply to XML — a `<title>` element is
text there and a CDATA section is character data. Both are confined to XML mode. EdgarTools' `Schedule13D.parse_xml` and `xmltools.parse_xml` remain
documented as a semantic cross-check (typed fields in source order, an lxml tree without offsets); the route itself needs neither.

**Pictures (point 5, test 4).** The eight picture-text targets are HTML exhibits made of page images; the image files are present locally for the development
exhibits (23/23, 4/4, 2/2). Docling's own OCR (RapidOCR, the only engine installed offline; EasyOCR and Tesseract are not) on the 23 pages of
`0000049071-24-000040`: 94 s, 8,796 words; the key's block (493 words, kind image) scored **0.146** — but that figure was 1 − matched words / reference words over all 23 pages, an
unmatched-reference fraction, not a word error rate (Codex N3); remeasured on the block's own image with the real word error rate: **0.144** (§34). That is a
measurement, not a route: at a word error rate of 0.144 the exact-text rule fails; the options are a better engine (an install the owner decides), the vision pipeline measured
earlier (156 s/page, misreads), or a contract decision on picture text. Recorded in the ledger as class A's first number.

**Docling rows (point 2).** `DOCLING_FEATURES.md` now carries the same rows as the EdgarTools table, measured on the same files: hyperlinks kept (82/84 vs 0),
pictures kept (56/56 vs 3), the same blindness to CSS strike-through and to the "raised-top" footnote marks these filers use (0 super/subscript pieces where the
source has none `<sup>`), no character offsets, 3.8 s / 545 MB plain and ~80 s render on the 6.8 MB 10-K.

193 tests, 48/48 real pairs; Codex's rounds 4–10 scripts behave.

## 33. Run 29 — the EdgarTools route's own losses (2026-10-04 00:52): one adapter gap, one grader gap, both closed

**What run 28 showed (agreement point 6; `FABLE_ROUTE_NOTE_20261004.md`).** EdgarTools + formatting + screen passed 213 of the 231 HTML development
targets, the browser render + formatting 217; the render recovered 7 targets and lost 3. Key-free escalation triggers from the cheap route's own gates do
not predict the 7 ("any fault" escalates 46 of 60 files for +4 targets; "uncovered > 100" 29 files for +3). Of the 7: 3 page numbers (EdgarTools drops
them by design since 5.54.0 — a contract question, not a route fault), and four blocks charged below.

**Grader gap — a table that spans a block does not carry it.** EdgarTools flattens a nested layout table into one `table` unit whose span covers 2.4 MB of
the source; a footnote block inside that span has its own text unit that matched the key exactly, yet `grade_structure` read the block from the table
unit's cells (all elsewhere) and failed it. Rule now: a table unit counts as carrying a block only when one of its cells overlaps the block's anchor; when
every unit at the anchor is such a table the old reading stays, so a block laid out inside a real table is still read from that table. Measured with the
committed grader on the same route folders (`PYTHONPATH` cleared, loaded path printed): it recovers 0001104659-23-055027 T01 on the Docling HTML routes,
0001040971-25-000027 T01 and 0001040971-24-000028 T01 on the printed-HTML PDF route, and 0000815097-23-000012 T03 and 0001053507-23-000023 T05 on the
EdgarTools route; no other verdict moves. Test: a block inside a table unit's span whose cells lie elsewhere.

**Adapter gap — our walk stopped at a paragraph.** `adapters/edgartools_html.py::dump` treated every `ParagraphNode` as a leaf; a paragraph that holds
`ContainerNode` children (EdgarTools' own tree keeps the blocks as their own nodes) came out as one unit of up to 60,000 characters, and those characters
were the route's 22,494 "inserted" ones — ours, not the library's. A paragraph that holds blocks is now walked like a container: inline runs become text
units (spacing from the library's `has_tail_whitespace`), block children are walked, a heading-only child keeps the run-in handling. No library option
covers this (`merge_adjacent_nodes=False` changes nothing: tested). Measured by running the committed adapter again and grading both outputs with this
grader: the new walk recovers 0001140361-25-003207 T01 and 0000950170-23-061206 T01 and turns the six picture blocks the giant units used to cover from
FAIL into UNRESOLVED — nothing is emitted at their place any more, which is the truthful record (§33 below on denominators).

**Run 29 (12 routes regraded; development split).** EdgarTools + formatting + screen: cells 168/171 unchanged; blocks 45 → 49 of 60, 0 failures, 11
unresolved; inserted characters 22,494 → 7; uncovered 30,585 → 22,030 characters (41 files: the page numbers and headers it drops). Docling HTML routes
+1 block each (the grader gap); printed-HTML PDF blocks 1 → 3 of 8; browser render unchanged (51 / 52). Best single HTML route **217 of 231 — EdgarTools +
formatting + screen now ties the browser render + formatting** at 1.4 s against ~80 s per file; best pick per target 221; no route 10 (8 pictures, 2
key-side items). The round-7 grader re-run on the same 12 route folders: only FAIL → PASS flips, no pass lost.

**Denominators.** The 11 unresolved EdgarTools blocks are the 3 page numbers ("12", "9", "12") and the 8 picture blocks: the route emits nothing at their
place, which the grader records as UNRESOLVED (a dropped block is not graded — `test_dropped_paragraph_is_unresolved_and_counted_as_lost`; the
uncovered gate counts its characters; a picture's text is not in the HTML at all, so for pictures only the verdict records the loss). The results tables
now count unresolved targets in every denominator, as Codex asked ("45/55 is 45 passes, 10 failures and 5 unresolved out of 60"): EdgarTools' row reads
49/60 (11 unresolved), not 49/49.

194 tests, 48/48 real pairs.

## 34. Round 11 (2026-10-04 01:00, Codex's `ROUND11_CODEX.md` on 44c442cad and bba2530b8) — four grader classes and three XML/picture findings, all reproduced, all closed

**What Codex found (all reproduced live first: his r11 scripts pointed at the repository, loaded paths printed).** R11-1 the formatter certified the wrong
decoration in five Chrome cases (a style keyword in the line longhand, two styles, a repeated line keyword, an invalid later declaration, a sheet `inherit`
into an atomic child); R11-2 `value()` never ran the strike check, so an invented cancellation of the number passed (eight development-supplement targets);
R11-3 `struck_kept` dropped a strike longer than the field ("Ownership remains." over the heading "Ownership") through its text filter; R11-4 basis kept only
the first piece of a joined phrase, periods and footnotes never handed their carriers to the strike check; N1 the XML scanner read CDATA as markup, decoded
`&amp;` inside CDATA and honoured HTML hiding attributes; N2 two first holdings of two persons shared `path` + "1 of 2", so a wrong name borrowed the other
person's context; N3 the picture figure was 1 − matched/reference over all 23 pages, not a word error rate.

**Decoration grammar (`anchor.py::decoration(value, prop)`, `sheet_can_strike`).** Validity is checked per property: the line longhand takes line
keywords only; the shorthand takes each keyword once, one style at most, `none` alone. A declaration the grammar proves invalid is dropped and the one
before it stays in force, with no uncertainty (that is what the browser does); a token the scanner does not evaluate (a colour, a length, a function) still
makes the file uncertain. Inline `inherit` copies the parent's own computed line — the frame now carries the element's own line beside the propagated
one — so it reaches an atomic box. A stylesheet certifies "nothing struck here" only when every decoration value in it is provably strike-free (line
keywords other than line-through, style keywords, initial, unset, no `!important`); `inherit`, `revert`, functions, colours and unknown tokens cannot.
Chrome: Codex's ten cases 10/10 (were 5/10); the 20-shape oracle unchanged. On the corpus nothing moved: the four formatting steps write the same struck
items as before (2,219 / 2,219 / 3,015 / 1,629), 0 uncertain files.

**The field's own run (`grade.py::struck_kept(key_texts, items, anchors, vis)`).** The text filter is gone. Each key string is one run of the matched
items' joined search text; a route strike counts for the part of it inside that run — a strike crossing the field's boundary is seen, a strike elsewhere in
a shared unit is not. The run is the one the key's anchor names (the anchor's byte mapped through the scanner to the item's text, where that text is the
source's at its own place), else the only run; when the key's search pieces name several occurrences and the readings disagree the verdict is
**unresolved**. A route strike whose text repeats inside its item carries no position, so the source's own formatting places it when the scanner is
certain: if the source strikes the other place and not this one, the claim is that one; if the source strikes neither, the claim lands on the field (an
invented strike fails, Codex's `strike_equals_field`). Readings are judged per key string (a string without a run keeps the old text rule; a definite
failure on any string is a failure; an open reading is unresolved). `value()` now sends the very cells that spelled the value through the same check;
`basis` keeps every piece of a joined phrase; `periods`, `footnotes` and `range_` record the carriers they used. Audit from the live code (corrected in round
12): row_label, header_path, table_title, corner_text, lead_in, section_path, unit_printed, basis, periods, footnotes, range, row_context and the in-value unit
record what they matched; the caption shortcut of `table_title` (a table's own `caption`, not a unit) still relies on `field()`'s anchor fallback.

**XML (`anchor.py::xml_chars`, `adapters/xml_fields.py`, `grade_xml`).** The scanner reads XML through the strict standard parser's character data with
byte spans: CDATA literal, entity and character references decoded (every character of a reference shares the reference's bytes), attributes never text or
hiding, an element boundary a word boundary, a document that does not parse certifies nothing; `_TOKEN_XML` and the CDATA branch are gone. The route
names the containing instance by the byte of its start tag (`group.at`) and `same_group` compares that; an element whose own text holds inline elements is
one field read whole (its inner elements are formatting, not fields); repeated leaves report their own place (`siblings`); attribute values are not read and
their count travels as `not_read` in the route file and the grader's per-file facts. Three development forms regenerated: 209 / 225 / 367 fields, 9 of 9
cells pass, 0 dishonest anchors, nothing uncovered, `not_read` empty (these forms carry no attribute values).

**Word error rate (`grade.py::wer`) and the picture number.** `wer` is the edit rate (substitutions + deletions + insertions over the reference's words;
Codex's control `revenue was flat elsewhere rose` vs `revenue rose` = 1.5). The block of `0000049071-24-000040` was remeasured on its own image (slide 11,
the one `<img>` inside the key's anchor), full OCR text and inputs saved under `prepare_work/docling_deepdive_20261003/ocr_region_20261004/`: **0.144**
(455 OCR words against 492 reference words, 5.8 s); the neighbouring slides as controls score 0.986 and 0.882. §32's 0.146 is relabelled.

**Run 30 (formatting and screen steps re-run, XML regenerated, 13 routes regraded).** Every HTML number is identical to run 29 (EdgarTools + formatting +
screen 168/171 and 49/60 with 11 unresolved; browser render + formatting 165/171 and 52/60; best single route 217 of 231, best pick 221, no route 10);
XML 9/9; printed-HTML PDF unchanged. The round-7 grader on the same 13 route folders: 0 passes lost. The committed run-29 grader re-run on the same 13 route folders against this one: no target flips and no change in any check-row count on any route — round 11 changes no corpus verdict, the corpus holds none of the shapes it corrects, and no new unresolved strike reading appears.

Tests 194 → 202 (value both ways; the crossing strike with the anchor naming the occurrence, both occurrences named → unresolved, the source placing the
strike; basis / period / note / range carriers; the five Chrome decoration cases and controls; XML character data; XML instances; unread attributes; the
word error rate). Codex's r4–r11 scripts, the Chrome probes and the 20-shape oracle re-run: as expected. The three key-side questions were read from the
originals and recorded with the smallest corrections (ledger §16): the "(in millions)" line is printed inside the header cell, "Adjusted" stands over the
EPS columns only and nothing stands over "Growth", Carnival's header cell holds three `<br>`-separated lines. The five failed native-PDF blocks were traced
through the cached output (ledger §17): three are OCR quality on scanned pages, one an unreadable text layer (a font without a usable ToUnicode map — forced
page OCR is the justified experiment), one a paragraph joined across a page break (a contract question); none is a table failure.

## 35. The PDF route's own gate: a parse-POOR page is read again by OCR (2026-10-04 02:15; Codex's step 4 and agreement point 6)

**Evidence first (ledger §17).** Of the five failed native-PDF development blocks none is a table failure: three are RapidOCR misreads on scanned
pages, one is a paragraph joined across a page break (a contract question), and one is an **unreadable text layer** — the Adobe "unofficial" 10-Q's
font has no usable ToUnicode map, so every character comes out shifted (`pdftotext` reads the same mojibake). Converting that page alone with OCR
mode FULL_PAGE reads the block perfectly (word error 1.000 → 0.000, 6.9 s). Docling's own confidence report marks exactly that page: `parse_score`
(the 10th-percentile score of the digital text cells) is 0.0, grade POOR, while the other eight block pages score 1.0 or n/a (scanned) with grades
EXCELLENT (`prepare_work/docling_deepdive_20261003/pdf_confidence_20261004/`). The confidence does not see OCR misreads (ocr_score 0.98–0.99 on the
three scanned pages), so it is a trigger for the unreadable-layer case only.

**The rule (`adapters/docling_pdf.py::poor_parse_pages`, `spliced`).** After the first conversion, every page whose parse grade is POOR — judged by
Docling's own grade scale through its public model, no threshold of ours — is converted again alone with the same pipeline and OCR mode FULL_PAGE;
its units take the page's place in the first pass's order, ids prefixed by the page; a unit anchored on several pages goes when any of them is
re-read; the route file records `reread.full_page_ocr_pages`, the facts `reread_pages`, the settings the rule. Printed HTML is our own print (a
readable layer) and is not re-read. The re-read documents are cached beside the first pass so `--reuse-raw` replays them. Test: the splice keeps the
tool's order, drops the unreadable and the spanning unit, keeps ids unique, and is the identity when nothing is re-read.

**Run 31 (the nine native PDFs converted again; the printed-HTML files untouched).** The rule fired on one document only — the Adobe 10-Q, all 54 pages parse-POOR, re-read in 254 s for the whole file — and on none of the other eight (0 pages: no false trigger; the nine files took 1,191 s in all). The block's text now passes (`printed_text` pass, was word error 1.0), but the target still fails on its section path: RapidOCR drops every capital L on this font ("PART IFINANCIA INFORMATION", "CONSO IDATED"), so the heading is not found — the next fault is the engine's reading, not the layer. Native PDF stays 4 of 9 at the target level; the other eight blocks keep their verdicts (their word errors now read by the real metric: 0.043, 0.082, 0.044, and 4.343 for the page-break block, whose unit is thirty times its text).

Tests 203. This is the first escalation inside a route: cheap default, the route's own gate, one measured recovery; the browser render for HTML
stays off because its gains were not predictable from gates (§33).

## 36. Round 12 (2026-10-04 04:15, Codex's `ROUND12_CODEX.md` on 15c42c278) — seven findings, all reproduced, all closed; the route stays a candidate

**What Codex found (all reproduced live first, his scripts pointed at the repository).** R12-1 the shared unit builder skipped a table's attached notes that
were also listed among the table's children (65 attached items in three development PDFs had no unit; 39 texts nowhere in the output); R12-2 `spliced`
dropped a unit spanning a re-read page and another, appended a re-read page the first pass had nothing on at the end (1, 3, 2), and left `notes`
pointing at old ids; R12-3 a `PARTIAL_SUCCESS` conversion became route `OK`, `--reuse-raw` after a crashed re-read reported OK with no re-read, and
`--reuse-raw --no-ocr` reused full-page OCR while declaring `ocr: false`; R12-4 the XML run summary kept only the last file; R12-5 an XML unit could be
supplied by another holding; R12-6 the scanner put a space at every XML element boundary (`123` read `1 2 3`) and a parent with text of its own erased
its children's field identities; R12-7 an invented strike over a marked label (`Total(1) revenue`) slipped past the text fallback.

**Attachments once, at their place (`docling_html.py::to_units`).** The walk descends into a table's children (captions and notes in the tool's own
order); the attachment loop emits only what the walk never reaches, computed with the walk's own rules (rich-cell groups excluded); each item once.
Audit on the nine cached development PDFs: 0 attached items without a unit (was 65).

**Page groups, order, nothing dropped (`docling_pdf.py::reread_groups`, `spliced`).** The parse-POOR pages are closed over first-pass units that span
further pages and converted again as contiguous page groups, so a paragraph across a page break is read again whole. The splice keeps the first pass's
order, puts each group where the first pass reaches its first page (also for a page it had nothing on), drops a unit only when all its pages are
re-read, keeps a unit that would still straddle (marked `incomplete`), and renames re-read ids with every reference between them.

**Partial stays partial; a cache is reused only whole (`docling_html.py::route_status`, `docling_pdf.py::main`).** Only `SUCCESS` is OK; a partial
conversion or re-read is PARTIAL with the tool's errors; a failure or an unknown cached outcome is FAILED. Each conversion writes `raw/<file>.meta.json`
(source sha256, settings, status, errors, required and completed re-read groups); `--reuse-raw` refuses a cache with no record, other bytes, other
settings or missing re-reads — FAILED with the reason — and otherwise carries the cached outcome. The HTML adapter maps and carries statuses the same
way. The existing caches had no record, so run 32 converted the Docling HTML and PDF routes again.

**XML (`xml_fields.py`, `anchor.py::xml_chars`, `grade_xml`).** The run summary keeps every file (the per-file unread dictionary no longer shadows it).
The scanner adds no character at an element boundary: XML text is the character data alone. A parent with text of its own around child elements is
read whole as prose (`mixed`) and its children stay fields of their own — nothing lost, no identity erased; the prose unit overlaps its children. The
key records no source support for XML `unit_printed`, so support is the containing instance: a unit counts from the same instance (`group.at`) or from
outside every repeated ancestor (the document's shared context, a security title); another holding's word cannot stand in.

**Strikes over a marked label (`grade.py::struck_kept(…, markers)`).** The record's own footnote marks are set aside first with a position map; the
field is the run of the remaining characters and a strike is judged on the field's own characters inside it (a strike on the mark alone is not the
field's). Audit corrected: row_context and the in-value unit record their carriers; the caption shortcut keeps the anchor fallback.

**Run 32.** Run 32 (04:22–05:01: the two Docling HTML routes converted again with their statuses recorded — 60/60 SUCCESS each — the render route re-adapted from its raw output, the PDF route's 14 files converted again under the new rules, XML regenerated, formatting and screen steps re-run, 13 routes regraded): every HTML number is identical to run 29 (EdgarTools + formatting + screen 168/171 and 49/60 with 11 unresolved; browser render + formatting 165/171 and 52/60; best single route 217/231, best pick 221, no route 10); XML 9/9 with all three files in the run summary; the Adobe document re-read as one 54-page group; native PDF 4/9 — the attachments emitted now add text units but no development verdict moved. Run 33 (05:03, the owner's page-break rule (e) in the grader, regrade only): the continued paragraph of `0000950170-24-131547` passes with the `continued` flag → **native PDF 5/9**; nothing else moved; the round-7 grader on the same 13 route folders: 0 passes lost. The PDF route folder now holds 19 route files (14 converted in run 32, 5 printed-HTML files of the 2026-10-03 experiment left as they were), hence the wider printed-HTML columns in its row.

Tests 203 → 208 (the owner's rule (e) included: a unit anchored on several pages, the key's page among them, that carries the block's text in order passes with the flag `continued`; `grade.py::continuous`; the within-unit page split is not verified until the route carries per-page character spans). Codex's five round-12 scripts and the r4–r11 probes re-run: as expected (the documented `3.7 %` tolerance aside). The route proposal
is corrected to a candidate: no net gain against the render (each 217/231, each recovers 3 the other misses, union 220, best 221), the complete-route
time ≈ 7.7 min per 60 files, page numbers a route loss under the active contract until the key side changes it, pictures under the frozen contract
until the owner's rule enters the next package.

## 37. Round 13 (2026-10-04 05:33, Codex's `ROUND13_CODEX.md` on 5658a7c89) — five corrections, all reproduced, all closed; package 3 staged on his build order

**What Codex found (all reproduced live first, his scripts pointed at the repository: `codex_probes_live/r13_*`).** C1 a cached conversion could revive a
stale success: the PDF adapter wrote the base output before the re-read and left the old record beside it, so a crash in the re-read followed by
`--reuse-raw` reported OK over a half-finished output; the HTML adapter reused a plain-mode cache under `--prestep-headings` and a cache of other source
bytes, and a reused PDF output was labelled with the installed version instead of its producing one. C2 the owner's page-break rule (e) accepted a
paragraph whose text the tool mapped to another page, and passed when no mapping existed at all — the mapping condition of decision (e) was stated as a
limit, not implemented, although Docling already writes `prov[].charspan` per page. C3 `grade_xml` ignored the key's declared source place of a unit
(`support.unit_printed`): a unit removed from its holding was supplied by an unrelated unique branch or by a comment of the same holding. C4 the XML route
emitted a prose parent after the fields inside it (a reading-order break on every mixed element, and the texts read twice when joined). C5 the re-read id
renamer rewrote every equal string, source text and hrefs included.

**A cache is a record of the run that produced it (`adapters/cache.py`, used by `docling_pdf.py` and `docling_html.py`).** The record beside the raw
output names the source bytes, the producing version and settings, every output file with its own hash, and the run's outcome. It is removed before any
output is written again and written only after every output is saved, so a crash between leaves no record and no stale success. Reuse checks the record
against the files on disk (other bytes, other settings, a changed or missing output, no version: refused, FAILED with the reason) and keeps the producing
version on the route and in the facts — a newer installed tool never relabels an old conversion. The PDF route's records from run 32 were completed once
(`grader_next/migrate_cache_records.py`: the producing version from the run's facts and the hash of every output, only where the record is newer than
all its outputs, as the old writer wrote it last) so run 34 could re-adapt the saved output without converting again; HTML caches have no record yet and
are reconverted when next needed.

**The page-break rule reads the tool's own mapping (`docling_pdf.py::mapped`, `anchors_from_boxes`; `grade.py::continuous`).** Each page anchor of a
unit carries the span of the text it holds (`charspan`) when the tool's spans are consistent (inside the text, in page order); inconsistent spans are
dropped, the pages stay. The rule passes only when the part of the unit mapped to the key's page contains the key's text in order (`continued`); a unit
over several pages without a mapping is **unresolved** (`page_map`); a mapping that puts the text elsewhere fails. The real case (`0000950170-24-131547`,
item `#/texts/304`, page 35 `[0,1026)`, page 36 `[1027,1239)`) passes on its page-36 span: native PDF stays 5/9 on evidence, not on a page list.

**An XML unit is read where the key says (`grade_xml`).** With declared support anchors, the field read there must carry the word (pass), another
word there fails (`text`), no field there fails (`missing`); with no declared place, a word of the same instance is **unresolved** (`support`: no
association with the value is shown) and a word elsewhere fails. All nine development XML cells carry declared anchors (model support); they pass by
them. The document-level shortcut (`count == 1`) is gone.

**XML units in source order with explicit containment (`xml_fields.py::units_of`; `gates_for_file`).** Units stand in source order (a prose parent
before the fields inside it); each field inside prose names the prose unit it stands `within`. The reading stream is the units held by no other, each
source character once; field lookups see every unit. The gate checks the declaration (a `within` unit must follow its holder and lie inside its bytes,
else dishonest) and keeps the order check over every unit, so swapped fields inside prose still break order.

**References only (`docling_pdf.py::spliced`).** The renamer touches `id`, `notes` and `links[].to`; text, captions, cell values and hrefs keep their bytes.

**Run 34 (05:53–05:58; PDF route re-adapted from its saved output through the completed records, XML regenerated, 13 routes regraded, round-7 A/B).**
Every HTML number equals run 33 (EdgarTools + formatting + screen 168/171, 49/60 with 11 unresolved; render + formatting 165/171, 52/60; best single
route 217/231, best pick 221, no route 10); XML 9/9 with every unit bound to its declared place; native PDF 5/9 with the continued paragraph passing on
its page mapping; the PDF facts carry the producing version; round-7 grader on the same folders: 0 passes lost. Tests 208 → 211. Codex's r4–r13 probe
scripts: as expected (`r10_xml_capability_check.py` needs the EdgarTools environment: exit 0 there).

**Package 3, staged on Codex's build order (`prepare_work/grader_review_codex_20261003/package3_build.py`, reproducible; the folder
`bulk_20261002/FINAL_KEY_FOR_CODEX_20261004_0557`, read-only).** A full copy of package 2 beside it (same evidence root); the staged `claude_build_key.py` and
`claude_support_map.py` read packets and raw answers through the manifest's declared, hash-checked evidence root (the frozen copies assumed the bulk
folder as working directory); the unchanged three-row batch applied through `claude_decide.py`; the key rebuilt — 457 records, 0 pending, exactly three
changed and only their `header_path`; Codex's reviewed Park header pointer (8 spans, source hash checked) in `KEY_SUPPORT_OVERRIDES.json`; the support
map regenerated (Park `reviewed`, Aflac `search` 1 hit, Carnival `model`; 0 searched pieces missing); the three records re-verified and stamped;
`CONTRACT_DECISIONS_R4.json` (the owner's decisions (a)–(e) in Codex's wording: E10 picture text, E10 page numbers with the three declared exclusions
and their reviewed anchors, E12 continuous paragraphs, E17 XML-route exception, the OCR adoption rule) mirrored in the README E-rules and the
comparison contract; the manifest written last (`final_pass/make_manifest.py`: packets, raw answers, regression evidence and the catalog re-hashed and
required equal to package 2; `contract_declarations` names the R4 file) and the gate run: 103 files, 37 packets, 1881 packet files, 296 raw answers, 457
stamps current, no mismatch; the frozen support tests (11) and regression cases (8) pass. Package 2, the repository pointer and the golden copies are
untouched until Codex's verification.

**The grader reads a package's declarations (`grade.py::declare`, `critical`; `verify_inputs` pins the declarations file too).** A target the package
excludes by a reviewed source anchor (page numbers) is **EXCLUDED** — one row, nothing graded, counted apart in every summary, never a pass; the
declaration must name the key target, its file, the file's bytes and the target's own anchor, else the run stops. A block the key declares an image is
**APPROXIMATE** when its text was converted: the row carries the word error rate and the critical tokens that differ — numbers with sign, parentheses,
currency and percent, tokens holding digits, unit words, and a negation read with the word it governs — compared position by position when both texts hold
as many critical tokens (two swapped values both show) and by ordered alignment otherwise; exact OCR is still not a pass; a dropped picture stays
unresolved; the other checks of the block (section path, references) stay strict. Package 2 declares nothing and grades as before.

## 38. Round 14 (2026-10-04 06:23, Codex's `ROUND14_CODEX.md` on 625fec468; package 3 approved) — five grading gaps, all reproduced, all closed by class

**Method this round (owner, 06:30: no rushing, think independently, three line-by-line iterations at least, test every item).** Every claim and demand of the
review went into a ledger (`grader_review_codex_20261003/R14_LEDGER.md`) before any edit; his 18 boundary cases were reproduced on the live code
first (`codex_probes_live/r14_boundary_probes.py <repo-root>`); each finding was traced to the assumption behind it and every other place that
assumption lives was changed with it; every new control was shown to fail on 625fec468 (a throwaway worktree) and pass after; the saved outputs were
regraded on package 2 and previewed on package 3 and every changed number explained against frozen copies of the previous outputs; three self-review
passes over the full touched functions (false pass; false fail or unresolved; docs ↔ code ↔ tests ↔ numbers).

**What Codex found (all reproduced).** R14-1 the page-break rule was applied only as a rescue after an exact match failed, so a unit whose text was
exactly the key's passed although its mapping put the words on another page; and it searched every span on the key's page, not the span at the key's
region. R14-2 `grade_xml` took the first field overlapping the key's position — with units in source order that is the prose parent, so a value inside
prose failed value, label and path. R14-3 the approximate branch swallowed a wrong-page mapping; an order fault left a picture `APPROXIMATE`; the gate
trusted the route's `image` label (bounds unchecked, text uncertified) while a `text` unit with the same reading counted dishonest. R14-4 a declared
page-number block left out counted as required-content loss. R14-5 `critical` kept `$` only and a short unit list, so a changed unit word or currency
symbol beside a number reported no critical difference; S/D/I counts were missing; the Markdown table had no `approximate` column.

**Mapping before acceptance (`grade.py::mapped_part`, `grade_structure`).** For every unit at the key's anchor, the text the grader compares is the
part the route maps to the key's place — page and region — taken before any comparison: a unit at one place, or one whose places the key's anchor all
overlaps, a table (its cells carry their own places) or a unit placed by bytes (the gate certifies its text block by block) contributes its whole text;
a unit over several page places of which the key overlaps some contributes the characters its `charspan`s map there (validated again in the grader:
integer bounds inside the text, in order, none reaching back); with no valid mapping the block is **unresolved** (`page_map`) whatever the text says.
The owner's rule (e) is then: the mapped part holds the key's text in order (`continued`). Words that exist in the unit but are mapped elsewhere fail
with their own reason, `page` — a contradiction, not a transcription difference. The reference phrase and the word error rate read the mapped parts too.

**The field that owns the position (`owners`; `grade_xml`, `unit_printed`).** Among the field units at the key's position, the innermost — a unit inside
which no other of them lies — is the one graded; the same bytes claimed by several fields is an ambiguity reported `unresolved`, never a choice by the
wanted value; a missing child leaves its prose parent to be judged as what it is (value, label and path fail — no silent stand-in). Declared
`unit_printed` anchors resolve through the same rule.

**Leniency replaces only the transcription comparison (`grade_structure`, the verdict loop, `RouteFile`, `picture_at`, `gates_for_file`).** A declared
image block is `APPROXIMATE` only when the comparison failed on the words themselves (`text`, `word_split`) or passed; a wrong place (`page`), a strike,
an unknown mapping, references, section path and order keep their strict outcome, and an order failure now outranks `APPROXIMATE` in the target
verdict. A byte anchor outside the source or malformed is marked in `RouteFile`: it locates nothing (the unit carries no target) and the gate counts it
dishonest, for every kind of unit. The gate decides what a picture is from the source — `<img` or `<svg` at the anchor and no visible text there — never
from the route's label: the same reading as a `text` unit gets the same verdict and the same gate; ordinary source text relabelled `image` is still
certified against the bytes; picture text without any position counts unanchored. An empty reading is `APPROXIMATE` with zero words recovered, stated
as such; a missing unit stays unresolved.

**Declared exclusions apart (`gates_for_file(…, excluded)`).** Raw coverage is kept; required-content coverage subtracts only the declared exclusions'
own bytes; the characters so subtracted are reported per file as `excluded_chars`. An undeclared footer or any other text left out remains a loss.

**The reading, described in full (`reading_units`, `critical`, `wer_counts`).** Reading units of an OCR text: a currency or sign symbol joined to its
number (`€20`, `20%`), a number joined to the word that follows it — its unit or qualifier (`10 shares`, `20 million`; deliberately also an ordinary
word, so a changed word beside a number counts as critical), a negation joined to the word it governs (`not buy`). `critical` returns every aligned
edit span (`edits`: reference tokens → output tokens, nothing filtered), the critical differences (tokens holding a digit, a Unicode currency or sign
character, or a negation; position by position when both texts hold as many, by the alignment otherwise) and the other differences, kept for review
and never declared harmless; the unit-name list is gone. `wer_counts` gives reference words, recovered, substituted, deleted and inserted from one
minimal edit table (the rate is unchanged in value); the approximate row carries all of it; the per-check Markdown table shows `approximate`.

**Verification.** 214 tests (six new controls fail on 625fec468, pass now; the adjacency test's '9' piece moved one byte later, an empty span being no
position at all). Codex's r4–r14 scripts: 38/38 as expected; his 18 boundary cases: every one as he required (wrong page `fail page`, right region
`pass continued`, mixed XML child all pass, picture controls `APPROXIMATE`, bad bounds `UNRESOLVED` + dishonest, reversed order `FAIL ['order']`, the
dropped footer `measured_pass` with `excluded_chars` 1, every critical case flagged with its edit). 48/48 original-document variants. Run 34b (package
2, regrade of the same 13 route folders): **0 verdict flips, every gate number identical** to run 34 (the only summary difference: the two zero-valued
verdict keys the declarations added after run 34); round-7 grader: 0 passes lost. Package-3 preview on the same saved outputs: 0 verdict flips; the
three page-number files now report `excluded_chars` 1, 2 and 2 and their required loss drops by exactly that.

## 39. Round 15 (2026-10-04 07:03, Codex's `ROUND15_CODEX.md` on 81f62ce1a; package 3 still approved, still staged) — six defects, all reproduced, all closed by class

**Method this round (owner, 07:14: an independent audit before his findings, at least three line-by-line passes with distinct purposes, every behaviour
tested, root causes not symptoms, evidence or a stated gap for every conclusion).** From his six one-line headlines alone, before his file was opened,
the whole grader, every adapter and the scanner were read again and probed (`grader_review_codex_20261003/R15_SELF_AUDIT.md`, hashed 07:26,
`codex_probes_live/r15_self_audit_probes.py`): all six mechanisms found; three sibling instances he names were not (`R15_LEDGER.md` S9). Then his
two probe scripts re-run live, a ledger of every claim and demand, each defect fixed at its class with every sibling found by grep, every new control
shown red on 81f62ce1a (a throwaway worktree) and green after, a mutation check (each changed condition inverted on a copy of the package: 34 of 34
make the suite fail), the standard-library tracer over the suite and over the 48 originals (every changed line executed; the eighteen unexecuted lines
of `grade.py` are untouched branches, listed in the response), the saved outputs regraded on package 2 and previewed on package 3 with every change
explained down to the field row, and five lenses (trust, wrong-but-passes, right-but-fails, field flow, agreement) over every function on the path until
a cycle found nothing: the second cycle found three refinements of my own, the third none.

**What Codex found (all reproduced).** R15-1 `contains` returned on a plain substring, so `Revenue 10` was found in `Revenue 100`, `10.5` and
`10,000`, `not own` in `cannot own`: a mapped continuation and a period year passed with a changed number. R15-2 two blocks of one paragraph mapped
into one unit: the earlier failed `order` because equal unit indexes read as an inversion, and a reversed mapping gave the same verdicts. R15-3
position validation covered byte spans only, and only some consumers: an XML unit at `[-1, beyond the end)` was dishonest yet still carried
`unit_printed`; a context field at `{}` still proved the person; `{}` and an end-only anchor passed the gate as clean; a region holding a string
crashed the run; a huge or negative box located the key's box. R15-4 `picture_at` searched the raw bytes, so an `<img` inside a comment, a script,
an attribute or a hidden subtree made a picture, and invented text there escaped certification; the picture count was `count(b'<img')`. R15-5 the
EdgarTools adapter reused its saved dump with no record: stamped with the installed version, kept after the source changed. R15-6 the heading
pre-step cut the start tag at the first `>`, inside a quoted attribute.

**Whole words and numbers (`contains`, `mark_in`, and every caller).** A phrase is printed inside a text only when a stretch of the text spells it by
the boundary rule and begins and ends where a word or number of the text does: positions strictly inside a `_TOKEN_WORDS` token are no cut points,
so `note 1` is not in `note 10`, `250` not in `1,250`, `not own` not in `cannot own`, while `(Revenue 10).`, `3.7 %` and `$1,250` keep their
matches. The same rule now reads the reference phrase (`references`, both readings), the unit printed inside the value's own cells (`unit_printed`)
and the XML unit text (`grade_xml`). A footnote mark may be glued to a word (`Revenue1`, `2015(1)`), so for marks only numbers cut
(`contains(…, marker=True)`: `1` is not printed in `2015`, `1,000` or `1.5`), and a comma group made only of the record's own marks (`1,2`) is
marks, not a number (both rules Codex's, taken from his worktree; my first rule read only the neighbouring characters and let `1,000` through).

**Order inside one unit (`inner_position`, the verdict loop).** Between units the route's order decides as before. When one unit carries two blocks,
the route's own data orders them: the interval of characters its mapping puts at each block's place, or the interval of its cells in the table's grid
order (two cells at one grid position keep the route's listing order); the pairs to compare come from `source_before`, so two boxes side by side on
one row are compared too; a contradiction with the source fails both and outranks any other reading; no readable order — whole texts, no mapping — is
`unresolved` (`internal_order`), which outranks `APPROXIMATE`. The key never orders the blocks. (The interval form, the `source_before` pairing and the
failure precedence are Codex's, taken from his worktree; my first version used the first offset only and left a block whose neighbour's text had
failed without an order check — positions are the route's claims whatever the text says, so his rule is the right one.)

**A position that cannot be true is no position (`RouteFile.possible`, `cells_in`, `placed`, the gate).** Every span of every unit and cell is tested
at load: a byte span is integers with `0 <= start < end <= length`; a page box is four finite numbers with left < right and top < bottom from 0, a
positive integer page that the route's declared sizes name when it declares any, inside that size; a declared size that is no size declares nothing;
a span of neither kind, or failing its own kind's test, and any anchor value that is no list of places at all (a string, a number) is impossible. Such an
item loses its anchor (`_claimed` keeps the claim for the gate): it locates nothing, overlaps nothing, no consumer can crash on a malformed box, and only
placed cells (`cells_in`) and placed units (`placed`) are evidence in any lookup by text — row context, header rows, period columns, the XML instance's
fields and `unit_printed` lookups, text fallbacks. The gate counts text at an impossible position `dishonest` (whatever flag the route gives it: `gap`
exempts no text; a table's own impossible envelope too), a textless item there `unplaced` (a picture the linker gave an empty gap: no claim, no
coverage, reported apart), and among them the page boxes also under `bounds_inconsistent` — the key kept with that meaning, visible as such (Codex's
wording); its one real case is a zero-width box holding one letter in `udr…ex99d2.pdf`, dishonest now.

**Pictures the reader sees (`Visible.pictures`, `picture_at`, the count).** The scanner records the byte span of every `img`/`svg` opening tag it
shows: tokens inside comments, scripts, styles, templates or attribute values never reach it; a tag under `display:none`, `opacity:0`, `hidden` or
`ix:hidden` is not shown; a void element's own `visibility` is read (`visibility:hidden` hides it, `visibility:visible` shows it under a hidden parent).
`picture_at` asks whether such a tag starts inside the anchor and no visible text lies there — only where visibility is certain; under a stylesheet rule
nothing is shown for certain and `pictures` is `None` (Codex's condition). The scanner now parses each distinct style string once (his cache).

**EdgarTools cache (`adapters/edgartools_html.py`).** The same record protocol as the Docling adapters: `begin` before parsing, `save` after the dump
with source bytes, producing version, settings, output hash and outcome, `reuse` on `--reuse-raw` refusing other bytes, other settings, a changed
output, no record or a record whose outcome is not OK; the route carries the producing version. Existing conversions were not re-run (Codex: no relabelling).

**Compared with Codex's own fixes (his worktree `prepare_work/tool_selection_20261004/code`, snapshot 08:31, never touched).** His grader and this one
over the same 13 saved routes: identical verdicts and identical field rows; the only gate difference is the textless pictures in empty linker gaps (his
`dishonest`, here `unplaced`). His thirteen grader-scope controls pass on this code. Taken from his: the marker rule, the comma groups, the order
intervals and pairing, string anchors as false claims, finite coordinates, the table envelope, `bounds_inconsistent` as impossible boxes, pictures under
certain visibility, the cache outcome check, the style cache. Kept here: the anchor set to None at load (his keep-and-filter variant leaves a malformed
box reachable by `source_before` in `lead_in`), the undeclared-page rule, `unplaced`. Not taken (his wider scope, adapters only): the linker's picture
placement by source tag, the XML element tree and external-entity refusal, the screen-grid tokenizer.

**Heading pre-step (`adapters/prestep_headings.py`).** The start tag's extent comes from the parser (`get_starttag_text()`), recorded when the tag
opens; the first `>` is never searched.

**Verification.** 222 tests (eight new, four extended; ten red on 81f62ce1a, green after; one adapted helper green on both). His `deep_probes.py` and
`browser_and_siblings.py` live on the fixed code: every case as he requires (containment 9/9, anchors 7/7, pictures, XML bad anchor `FAIL`, merged
`PASS`/`PASS`, reversed `FAIL`/`FAIL`, EdgarTools reuse refused); his thirteen grader-scope controls from his own worktree green here; his r14
boundary cases byte-identical to the round-14 output; his Docling cache follow-ups unchanged; 48/48 originals. Run 34c (package 2, regrade of the
same 13 route folders): **0 verdict flips, 0 field-row changes**; one detail changed (a failed block's word error rate, its carrying table no longer
counting unplaced cells); gates: `unplaced` 1–29 in seven HTML files of the Docling routes (textless pictures in empty gaps, formerly skipped), the
PDF route's one zero-width box dishonest and its order breaks 434 → 433; round-7 grader: 0 passes lost. Package-3 preview on the same saved
outputs: 0 verdict flips, 0 field-row changes, the same gate changes. Mutation checks 43/43; tracer: every changed line executed by the suite.
