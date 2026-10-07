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
- **Optional** (reported as "structure" when present): `level`, `header`, `caption`, `markers` (footnote marks kept apart from the number), `notes`, `marker`, `links`/`to`, `struck`, `struck_at` (where in `text` the source strikes, `[[start, end), …]`; the formatting step writes it where exact, §47), `name`/`path`/`group`/`siblings`/`mixed`/`within` (XML: the containing instance, the element's own place, prose around child fields, the prose unit a field stands within). An `anchor` is one place or a list of places (a unit over several pages or boxes, a cell pieced from several spans); a page place is `{page, region}` and may carry `charspan: [start, end)` — the characters of the unit's text that lie at that place (Docling's `prov.charspan`), the only way the grader learns which words sit on which page (§37–§38). A page group converted again marks a unit that still straddles it `incomplete` (§36).
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

## 40. Round 16 (2026-10-04 11:55, Codex's `CODEX_REVIEW_R15.md` on 9e6919f4b; package 3 still approved, still staged) — three classes, all reproduced, each closed with the siblings an own audit found

**Method.** As round 15: an audit of my own from his three headlines before his file was opened (`grader_review_codex_20261003/R16_SELF_AUDIT.md`, hashed
12:02; probes `codex_probes_live/r16_self_audit_probes.py`), his three probe scripts re-run live, a ledger (`R16_LEDGER.md`), every new control red on
9e6919f4b (throwaway worktree) and green after, a mutation run on a copy (`r16_mutations.py`: the round-15 conditions still in the code and every
round-16 condition, 115 of 115 red), the tracer over the suite, the 13 saved routes regraded with every gate value, file row, target and result row
compared, and browser facts for every HTML rule this round relies on (`codex_probes_live/r16/r16_browser_facts.py/.json`: local headless Chrome, every
request aborted). The audit found his three mechanisms and seven siblings (one of them a control he recorded without promoting it); of his own cases
it missed the commented-out stylesheet and had the zero-area picture by size attribute only. Two more siblings came out of the third pass (a byte span
alone in a PDF, a sign before a currency symbol).

**What Codex found (all reproduced).** R16-1 `contains` cut only inside the digit token, so `10 million` was printed in `-10 million`, `−10 million`,
`+10 million`, and `5 million` in `.5 million`, `-.5 million`: a mapped continuation passed with the wrong sign or value. R16-2 `possible` admitted a
page box with no page, or a null one, also where the route declares its pages: the unit stayed placed and supplied a table title by text, while the
same box on an undeclared page did not. R16-3 `picture_at` answered False wherever visibility is uncertain, so an exact reading of a shown picture
was compared with the empty text layer and counted `dishonest` once any stylesheet stood in the file — even a commented-out one, because the sheets
were searched in the raw bytes; and a picture with no area (`width:0;height:0`, a zero SVG viewport) kept the picture exemption for invented text.

**A number is printed with its sign and its point (`number_spans`, `cut_points`, and every place that cuts text).** One primitive names the positions
strictly inside a number as printed: the digits with their separators, a leading point (`.5`; a point glued to a word is the word's: `No.5`), and a
sign before them — `-`/`+`, glyphs folded, glued or spaced (the spacing rule moves whitespace around a sign, so `- 10` is `-10`), with a currency
symbol (Unicode class) between sign and digits (`-$10`) — unless a word or number is glued before the sign (`COVID-19`, `5-10`) or a number stands
before it (`5 - 10`, a range). Nothing may begin or end there: a contained stretch (`contains`: `10` is not printed in `-10`, nor `5` in `.5`, nor
`$10` in `-$10`; a stretch that itself begins with a sign or a point must begin a number of the text, so `-10` is not printed in `5-10`), a deleted
footnote mark (`without_marks`, `minus_marks_anywhere`, `minus_markers`: the mark `1` is not cut out of `215`; before, `Revenue 215` read as the key's
`Revenue 25`), a removed own piece (`same`: `2015` is not removed from `12015`). The lead-in's own containment regex is gone: it reads `contains`
(`250 million` was found in `1,250 million`). A comma group of the record's own marks is marks (moved into the primitive). Deliberately unchanged, and
tested as such: an unsigned number and its symbol are separate pieces (`10` in `10%`, `10 million` in `$10 million`: the key itself splits printed and
display values; Codex's probe records them as contract questions, not defects); parentheses stay separable (a year, a mark and an accounting negative
look alike in prose; cell values are compared exactly elsewhere); the gate still strips a mark the route reports apart from a number (`10.67` + `4`
over `10.67⁴` is honest characters; whether the split is right is the value check's question, `marker_glued`). Stated consequence: a spaced dash
before a number reads as its sign, so an unsigned key phrase that begins at that number is not contained — a visible fail, never a pass.

**The source's format fixes the kind of position (`RouteFile.possible`, the gate).** A box names its canvas: in a PDF a positive integer page (one of
the declared pages when the route declares any), also when the place carries byte fields; elsewhere a picture file (`{file, region}`, the contract's
third kind) and no page. A PDF is addressed by page boxes: a byte span alone is no place in one (it dodged every box check, stood as placed evidence,
and the gate called the file measured and clean). Bytes in a source with no text layer are certified by nothing: the file's anchors are not measured.

**A picture is shown, may be shown, or is not there (`Visible.pictures`, `picture_at`, the gate).** The inventory holds `(start, end, shown)` for every
`img`/`svg` in a subtree the reader sees: `True`; `False` when its width or height is zero (size attributes read as declarations the style attribute
beats); `None` when its size is not known — a value this scanner does not evaluate (`calc()`, `inherit`, a bare or negative CSS number, an unknown
unit, a malformed attribute), a `min-`/`max-` declaration, or any stylesheet that may size it (an unreadable sheet, a `width`/`height` rule: a sheet
rule beats the size attributes). `picture_at`: text the reader sees at the bytes → `False`; a picture tag touching the bytes (not only starting inside
them) → `True` when the file's visibility is certain and the picture is shown, `None` when either is unknown, `False` for none or one with no area.
The gate skips a reading of a picture that is or may be shown, and for `None` reports the file's anchors not measured — uncertainty is never a
mismatch and never a certificate; a tag that is certainly no picture is compared as text, as before. `pictures` counts the pictures shown or possibly
shown. Stylesheets are read from the scanner's own tokens (a comment's content is none; inside `<head>` too), keeping a `<style>`'s own `<!-- -->`,
which CSS ignores. Read from the same browser evidence: SVG presentation attributes (`display`, `visibility`, `opacity`; the style beats them; an HTML
element has none), a self-closing tag in SVG/MathML content closes its element (before, `<svg …/>` hid everything after it), and the elements the
browser's own sheet never shows (`datalist`, `noembed`, `noframes`, `rp`, a `dialog` without `open` — an author `display` shows them again;
`noscript` never, where scripts run); a closed `<details>` shows its summary only and is not followed: the file is uncertain.

**Limits kept, stated.** Hiding by other CSS (clipping, off-screen positions, transforms, zero-size ancestors) is outside the model for text and
pictures alike; pictures carried by `object`, `embed`, `input type=image`, CSS backgrounds or `canvas` are not in the inventory (EDGAR documents use
`img`); HTML inside `<foreignObject>` is not followed; the order between a picture-file box and bytes is undefined by the contract (no saved route
emits file boxes: a question for the picture lane). `Visible.pictures` changed shape (two fields → three): adapters outside this folder that read it
must follow.

**Verification.** 225 tests (three new, one changed; exactly those four red on 9e6919f4b, 221 green on both). Codex's three scripts on the fixed code:
containment 5/5 required cases now fail as he requires (47/50; the other three are his percent and currency probes), pages missing/null/undeclared/
zero refused and the declared page passes, pictures: unknown visibility not measured and clean, zero area and zero viewport compared as text, the
commented-out sheet certain, every hidden/comment/script/attribute control as before. His round-15 scripts (deep, browser and siblings, boundary,
follow-up) give byte-identical output. Mutations 115/115 red. Tracer: every changed line executed (grade.py 46 of 46 executable, anchor.py 32 of 32).
48/48 originals. Run 34d (package 2, the same 13 route folders): **0 verdict flips, 0 field-row changes, 0 changes in any gate value, file row or
result row**; package-3 preview (5 routes): the same; round-7 guard identical; grading time unchanged (2 min 05 s for the 13 routes). The development
sources hold no stylesheet, no zero-size picture and no SVG (60 files, 732 pictures, 724 with both sizes), so the picture rules change nothing measured.

## 41. Round 17 (2026-10-04 14:15, Codex's `CODEX_REVIEW_R16.md` on 511a16e0e; package 3 still approved, still staged) — five wider classes, all reproduced, closed; two of round 16's own rules withdrawn; a final pass against Chrome and the real texts closed more of the same two classes

**Method.** As rounds 15–16: an audit of my own from the headlines the owner relayed, before his file was opened (`grader_review_codex_20261003/
R17_SELF_AUDIT.md`, hashed 14:21; probes under `codex_probes_live/r17/`, read-only while he was still checking); then his file three times, his
patch, his eight regression tests and his probes run against this code, every new control red on 511a16e0e and green after, a mutation run on a
copy, the tracer, every earlier round's probe replayed with each difference explained, and the 13 saved routes regraded with every gate value, file
row, target and result row compared. The audit had four of his five classes (page declarations, the deleted characters and the file they occur in,
the sign rule on real texts, picture identity in outline); it did not have C4's breadth.
*Final pass.* C4 and C5 are open-ended classes — "HTML the scanner does not follow", "a dash the text cannot read" — and examples do not close
such a class. So before hand-over both were tested against evidence instead: the scanner against local Chrome (every request aborted) on every
element of the HTML Standard's index, current and obsolete, and on 148 shapes around raw text, the head, the parser's moves, tables and files
with no doctype (`codex_probes_live/r17/final_pass/fp_all_cases.py`: 286 cases; a case passes when the scanner's text and line breaks are the
browser's, or the scanner says uncertain); the sign rule against the census of every dash or plus before a number in the texts the development
routes hand the grader (`r17_dash_census.json`). At 511a16e0e the scanner was certain and wrong on 95 of the 286; three shapes of the sign rule
still guessed. Both are closed below. None of these constructs occurs in the 60 development originals (census in `final_pass/`), so no saved
result moves; they matter for filings not yet seen.

**C1 — an unusable page declaration is still a declaration (`RouteFile.__init__`, `possible`).** Round 16 kept only the usable entries and then asked
"does the route declare any?" of that filtered map: `{"1": null}`, a size as an object or as strings, a key that is no number — all read as "declares
nothing", and every page and size went unchecked. Now `pages_declared` records that a non-empty declaration was supplied; usable entries are a
positive decimal page number with two finite positive numbers; when a declaration exists a box must lie on a usable entry (his patch). Added: a
declaration that is no object (a list, a string, a number) and a key such as `²` no longer stop the run. An empty or absent declaration is none, as
before (located, never measured).

**C2 — the source's character references are read as the browser reads them (`text_reference`, the scanner's three text uses).** Python's
`html.unescape` deletes numeric references to control characters and non-characters; the HTML parser keeps the character. One development original
(`0000879407-25-000007/a9912025-09x10arrowheadc.htm`, slides with a 1pt text layer) holds 18,146 such references; the tools keep the characters, so
their units could not be placed there. The helper is his: the standard decoder's result, and for a numeric reference it wrongly empties, the scalar;
one token, never decoded twice. Used for visible text, the hidden count and the text-in-a-table rule.

**C3 — the same picture is the same whole identifier (`_ratio`).** Base names were compared, so `assets/original/chart.png` overlapped
`assets/unrelated/chart.png` (his patch: exact identifiers; an alias needs a verified asset mapping, not a guess). No saved route emits picture boxes.

**C4 — what the scanner cannot judge is not measured (`html_tokens`, `Visible`, `picture_at`, the gate).** Four parts.
*Raw text.* The content of `textarea`, `xmp`, `plaintext`, `iframe`, `noembed`, `noframes`, `noscript` (and an unclosed `script`, `style`,
`title`) is literal text, never child tags: his worktree's tokenizer, adapted to keep round 16's stylesheets-from-tokens (`textarea`: text with
references decoded; `xmp`, `plaintext`: literal text; the others: not rendered). An apparent `<img>` in there is no picture. An unclosed `<style>`
is CSS to the end of the source and is read as a sheet. `noscript` is raw text where scripts run — the reading this scanner states; read as tags,
a comment or an attribute holding `</noscript>` hid the rest of the page (final pass).
*Beyond the subset.* SVG/MathML content and an inline `content-visibility` other than `visible` make the file uncertain — their rendering is not
modelled (round 16's SVG presentation attributes and self-closing rule are withdrawn: a half-model asserted what it could not prove, e.g. `hidden`
on an `<svg>` hides nothing, a `<p>` breaks out of a hidden one). Under an uncertain reading the gate counts nothing that depends on the reading —
no mismatch, no boundary fault, no insertion, no omission; impossible positions and text without a position are counted as before.
*The edge of the scanner's scope (final pass; each rule a class with its Chrome facts).*
(a) Content the page does not flow as its text (`UNMODELLED`): besides SVG and MathML, a `<template>` (its fragment nests and may never close) and
the fallback content of `audio`, `video`, `canvas`, `meter`, `progress`, `select`, `object` — Chrome prints none of it, the scanner read it as
text: uncertain.
(b) What is skipped as never rendered can be shown or moved. A `display` the author gives a `script`, `style`, `title` or `noframes` shows its
literal text (`SHOWN_BY_DISPLAY`; a `<head>` too, for what it holds): uncertain. `iframe`, `noembed`, `noscript` stay unshown whatever their
display (Chrome). A `<head>` is skipped whole only while it holds nothing but comments, closed `title`/`style`/`script` elements and
`meta`/`link`/`base` tags (`_HEAD_SAFE`); text or elements the parser moves into the body, or a `<title/>` an HTML parser reads to the end of the
source, make the file uncertain — the scanner's own reading keeps the body.
(c) Elements the browser starts on a line of their own: 19 names missing from `BLOCK` (`aside` … `xmp`; the sweep) — the scanner glued words the
page prints apart.
(d) The parser's own rules. A `</p>` that closes no paragraph is an empty paragraph and a `</br>` a `<br>`: a break (two development originals
hold nine such `</p>`, all between blocks: no reading changes). A table part with no open table is dropped by the parser: uncertain. In a file
with no doctype — 58 of the 60 development originals — a table does not close the open paragraph, so what that paragraph itself hides or strikes
reaches the table; with a doctype it does not: the reading depends on the mode, so a hiding paragraph left open before a table is uncertain (a
striking one: struck text uncertain). An element that is no part of a table, opened directly inside one, is moved out by the parser while the rows
stay, so what it hides or strikes does not reach them: uncertain when it changes either (one that changes nothing, `<table><font size=2><tr>`,
reads the same and stays certain).
*Pictures.* Round 16 judged a picture's size (shown / zero / unknown). Chrome shows that a zero box does not prove absence (visible overflow) and
that a normal-looking picture can be clipped, scaled to nothing or hidden by its container: no size rule short of a layout engine is right. So the
size grammar is withdrawn and the inventory is again byte spans of `img`/`svg` tags in subtrees the contract's hiding rules leave shown; a unit's
text at such a tag (and no visible text there) is a reading of a picture and is **not measured** — the file's anchors are reported not measured,
never a mismatch and never a certificate; a textless unit there leaves nothing unmeasured. A tag starts inside the span, as in round 15.
Consequence, stated: a correct route that carries a picture reading can no longer pass the honest-anchors gate for that file (the fixture's HTML
file is now listed not measured); no saved route places text at a picture, so no saved result changes.

**C5 — a dash before a number is settled by the source, never guessed (`numbers`, `splits`, `contains`, `Grader.printed`).** Real development
texts: `Preferred stock – 10,000,000 shares authorized:`, `1.01% - 2.00%`, `EURIBOR + 3.8%`, `- 2 -`, `Results from Operations – 2023 compared
to 2022`; round 16 read each dash as a minus and rejected the positive phrase. The text alone settles three cases, and only these: a dash or plus
glued to a word or number on its left **joins or ranges** (`COVID-19`, `5-10`) — no part of the number; one that touches the number with nothing
before it but a space or an opening bracket, and no number before that, is its **sign** (`-10`, `of -10`, `(-10)`, `-$10`); one standing free
between two numbers **ranges** (`5 - 10`, `2023 - $111,528`). Every other shape is **undecided**: free-standing before the number (`stock –
10,000,000`, `1.01% - 2.00%`), glued to other punctuation (`11%-63%`, `2'-0-methoxyethyl`, `(206)-392-5040`, `x=-10`, `$-10`), or touching the
number after another number (`n.d. -23 -18` is a list of signed values, `US2007 -0287831` a broken join, `0.79% -3.27%` either) — the census holds
each shape with more than one meaning, or its sibling. The first version of this round still guessed three of them (a join for any glued
punctuation, a sign after a currency symbol, a sign after a number and a space); the final pass moved them to undecided. `contains` returns True,
False or None (printed only if that dash is no sign). `Grader.printed` asks the source: where the key's own span prints exactly the phrase, a
dash or plus stands before it in the source, and the route's text prints that same stretch — the source's dash through the phrase — the route kept
the source's text: printed; where the source prints none there, or another one (the route's plus for the source's dash), the route's is its own:
not printed; with no such span, no source text (a PDF, a field found by text) or an uncertain reading, the field's verdict is `unresolved`
(`numeric_boundary`), never a guessed negative and never a pass. Every phrase comparison goes through it (lead-ins, periods, qualifiers, units,
notes and marks, range evidence, references, XML units; the mapped page continuation resolves `numeric_boundary` directly — a page box has no
source text). One predicate (`splits`) replaces round 16's edge positions: a stretch takes a word or a number whole or not at all — its sign, its
point, its digits — and a currency symbol between sign and digits stays a piece of its own (`$` is printed in `-$506`; round 16 lost that).

**Known, not changed (reported to Codex).** References without their semicolon (`&#150 `, `&nbsp `) are not decoded though Chrome decodes them, and
cp1252 bytes 0x81/8D/8F/90/9D read as U+FFFD (0 development cases each); a route file malformed beyond anchors and page declarations (a null text, a
cell that is no object) stops the run with a Python error — loud, never a wrong verdict; field checks that read source adjacency are not conditioned
on the scanner's certainty (no development file is uncertain); with scripts off a browser shows `noscript` content (the scanner states scripts on);
hiding by clipping, positions or transforms is outside the model for text; closing tags that cross a table cell or another scope boundary are not
followed (the development originals nest cleanly: census); only Chrome was asked. Four of the 286 cases differ on purpose: struck elements (`del`,
`s`, `strike`) are read apart from their neighbours where the browser prints them in the line (the contract's redline rule), and a `<textarea>`'s
text is read as the box shows it though `innerText` leaves a control's value out. A dash that touches its number after a word, at the start or
after an opening bracket is its sign even where the key's own span starts after it (the source is not asked: his control); no development key
phrase begins there. The saved routes were linked with the old scanner: linked again on this one, the Arrowhead file's 8–9 unplaced units are
placed (EdgarTools 0 characters uncovered) — an adapter step for Codex to order, not done here.

**Verification (on the final code).** 229 tests (five new, four changed; exactly those nine red on 511a16e0e, 220 green on both). His eight
regression tests pass; his remaining-cases probe reports no raw-text pseudo-picture and no visible SVG text vanishing; against his 58 saved Chrome
observations the scanner is certain and wrong nowhere under scripting on, and no invented picture reading is measured and clean (the one difference
of the 58 is `noscript` with scripting off); his 13 real paragraphs: 7 printed by the text alone, 6 undecided by the text and printed once the
source is asked, none rejected. The 286 Chrome cases: 220 the same, 62 uncertain, 4 different on purpose, **0 certain and different** (95 at
511a16e0e). Earlier probes: every difference from their saved outputs is the picture rule — 4 values in the round-15 deep probes
(`anchors_measured` for a picture reading) and 7 rows of his round-15 picture probe; his percent/currency probes unchanged (47/50); the final pass
changed none of them. Mutations 242 of 242 red (51 earlier conditions still in the code, 191 of this round). Tracer: every changed line executed (grade.py 81 of 81 executable, anchor.py 66 of 66).
48/48 originals. Run 34f (package 2, the same 13 route folders, the final code): against run 34d **0 verdict flips, 0 result-row changes**; one
gate value changes in the eleven HTML routes — the Arrowhead file's uncovered text, 3 spans and 8,754 characters → 10 spans and 24,059, the
characters the scanner now sees there and no saved unit covers; run 34e (this round before the final pass) and run 34f are byte-identical in
every graded file; the package-3 preview shows the same; round-7 guard identical; grading time 2 min 13 s (2 min 05 s before).

## 42. Round 18 (2026-10-05 02:57, Codex's `CODEX_REVIEW_R17.md` on 3cd06bcaf; package 3 still approved, still staged) — four classes, all reproduced, all closed; the scanner's reading rebuilt against the browser, exhaustively, and against real filings; three independent reviews of this round's own changes closed too

**Method.** As rounds 15–17 — an audit of my own before his file was opened (`grader_review_codex_20261003/R18_SELF_AUDIT.md`), his file, his 13
regression methods run against this code (22 failing sub-cases on 3cd06bcaf, none after) — and, because the owner asked that this be the last round,
instruments that do not depend on anybody's list of examples:
1. *The browser, at random and exhaustively.* Local Chrome (every request aborted) prints documents nobody chose; a page passes when the scanner's
   words are the browser's or the scanner says uncertain. Six random generators (`codex_probes_live/r18/r18_fuzz*_facts.py`: broken markup;
   well-formed trees of the elements and styles filings use; runs of white-space and line atoms; a wider vocabulary; the document's own
   html/head/body scaffolding; the CSS of a style string, of a sheet, and half-finished character references) — 1,180,000 pages. Random pages kept
   finding one more fault where three rare things met, so three instruments are exhaustive instead: every pair of 20 boxes, nested and side by
   side, with every white-space text around them (`r18_grid2_facts.py`, 1,152,000 pages); **every CSS property Chrome lists** (694), with every
   value of a wide vocabulary it accepts (11,308 pairs), on an element in 26 roles, inline and as a sheet rule, and every attribute of the HTML
   standard and of the old presentational set with 25 values on 16 kinds of element (`r18_props_facts.py`, 586,635 pages); and one page per word
   of every list in the scanner (`r18_words_facts.py`). With the grids of chosen shapes and the pages aimed at single conditions
   (`r18_targeted_facts.py`): 2,931,643 pages, graded by `run_all_facts.sh` in a minute.
2. *The agreed differences, checked by the browser too* (below, C1): `r18_grid3_facts.py` (794,880 pages), `r18_agreed_print.py`,
   `r18_explain_differences.py`.
3. *Real filings.* 22,483 HTML documents of 1,003 saved filings (no held-out filing among them) were counted for every construct a rule is about
   (`r18_census_*.py`; their bytes: every one is ASCII, `r18_census_encoding.py`), read by the committed scanner and by the new one
   (`r18_real_certainty.py`), and — the 60 development originals and the real documents the two scanners read differently — compared with Chrome
   word by word. The censuses decided the scope: exact where real filings need it, "uncertain" for what none of them holds.
4. *Every earlier finding.* Each issue of rounds 2–17 (146) replayed against the final code (`scratch18/all_rounds_*/replay_*.py`).
5. *Three independent reviews of this round's own changes* by a second model with its own probes: of `grade.py` (`scratch18/grade_review/`, nine
   findings, four of them introduced by the first version of this round's C2 fix), and of the later code — the scanner
   (`scratch18/review_scanner_2/rerun_current.py`: 40 pages in ten classes, a crash, a quadratic time) and `grade.py` again
   (`scratch18/review_grade_2/`, 17 probe files). All closed below, or stated.
6. *A mechanical mutation check.* Every condition on a changed line altered one at a time on the syntax tree (`r18_mutate_ast.py`); the survivors
   were closed with tests whose expectations are the browser's (`tests/fixtures/browser_pages_r18.json`) or the rules', or argued one by one.

**C1 — a reading the scanner has not modelled is never certified (`anchor.py`).** His four forms (a quoted `>` in the opening tag of a displayed
raw-text element, a reference without its semicolon, a closing tag crossing a cell, a null byte) are four faces of one fault: the scanner certified
readings of markup it did not follow. The rule now: **certain means the browser's text; anything else says uncertain** — and the browser decides
which is which, not a list of examples.
*Tokens.* A tag is followed only in the plain form every tokenizer cuts the same way (`_TAG`); a comment ends as the standard says; an element
taken whole (`script`, `style`, `title`, `template`) is certain only with a plain opening tag, a plain style and no author `display`, and one never
closed runs to the end as one token, like a tag that never ends (the parser drops the rest; looking for its end from every later `<` took minutes
on 100 KB); a null character, a reference the browser decodes without its semicolon: uncertain. A numeric reference is its digits only (`&#1a;`
is U+0001 and `a;`), of any length (`text_reference` no longer crashes on more digits than Python converts: U+FFFD, leading zeros set aside).
The line feed the parser drops right after `<pre>`, `<listing>` and `<textarea>` is not read.
*The tree.* `html`, `head` and `body` tags open and close nothing; one that hides, strikes, is given a display other than block or a `hidden`
attribute (a repeated `<body>` hands its attributes over one by one) is not followed. A closing tag that passes other open elements is followed
only where the parser simply closes them. Opening tags close what the standard says they close (`_IMPLIED`); an element opened inside its like and
a table that would close a paragraph: uncertain. An element the parser moves out of a table: uncertain when it hides, changes kept white space, or
is a formatting element with a box of its own (the parser opens those again inside the cells, `_FORMATTING`). A `<form>` (the parser keeps a
pointer of its own for it), a `<slot>`: not modelled. 26,603 `</tr>` over an open `td` in the development originals stay certain — his control.
*Styles.* A style string is read only when it is plain (`_PLAIN`: printable ASCII, no backslash, bracket, brace or `@`, every quote a string that
ends on its line, parentheses closed and not nested, every `&` a complete known reference); a comment is a token boundary, runs to the end when
never closed, and a string or `url()` holds none. `display`, `visibility`, `opacity`, `content-visibility`, `position`, `float` and `white-space`
are evaluated (not `pre-line`); a value outside the known keywords, or a declaration of a property that changes the text without being evaluated
(`_UNREAD`: `all`, `content`, `appearance`, `-webkit-text-security`, `white-space-collapse`, `-webkit-opacity` — what was left when every
property Chrome lists was tried), is uncertain. A sheet rule on any of these is uncertain; a sheet is read twice, comments set aside and kept, so
neither a rule a comment splits nor one inside what only looks like a comment is missed. The `align` attribute floats a picture or a frame; a
popover an author's display shows is out of the flow.
*Layout that changes the words.* Children of a flex or grid container are lines of their own; an inline box stands in its line, and white space
the browser drops at its edges is not certified; a box out of the flow, an author's table box or a paragraph given an inline display is a line of
its own, certified only when it has that line to itself; an invisible block keeps its line; text after invisible text that ended with white space
or with a kept line feed, and kept white space, follow the browser; what is removed (`display:none`) ends no line and keeps no white space
apart; a `</p>` or `</br>` that closes nothing is the empty paragraph or the break the parser makes of it; white space alone between the children
of a flex, grid or table box is not shown.
*Bytes.* Beyond ASCII the reading is certified only as plain UTF-8 — no byte-order mark, no `<meta>` naming another encoding, no fallback to
windows-1252 — the cases where Chrome, opening the same bytes as a local file, decodes as the scanner does (13 situations tried).
*Left unmodelled on purpose* (`UNMODELLED`, says uncertain): SVG, MathML, templates, media and form controls with fallback content, ruby, `button`,
`dialog`, `legend`, `marquee`, `wbr`, `slot`, `form`.
*The readings that differ from `innerText` on purpose — now each checked by the browser.* Each has a meaning Chrome itself can print, made inside
the browser on the parsed page (`AGREED_JS`): a `<textarea>` is the inline box of its text that the browser's own sheet says it is (one the author
gives a display: uncertain); **a zero opacity hides in place** — everything under it invisible, every box where it was, like
`visibility:hidden` (it used to be read as removed, which glued the words around an invisible block); `<ix:hidden>` is removed (contract); text
beside an inline table keeps its break (Chrome's text with the table set as a block); letter case under `text-transform` is not read. **Struck
text is read apart from its neighbours, and no longer by a line break:** an element that strikes used to be a block for every layout rule — so an
invisible block or an inline box inside it was thought to have a line to itself — and its boundary stood even where it struck nothing it showed.
Its two boundaries are now recorded during the scan and set in after it (`apart`), only next to a struck character; the layout rules never see
them. The check (`r18_explain_differences.py`): a certified page's letters are those of Chrome's agreed text, and its word breaks differ only
next to a character the scanner marks as struck. On the grid of these six boxes with the 20 others (794,880 pages) and on every certified page of
the other families that differs from Chrome's plain text (2,343): no exception.
*Cost on real filings.* Of 3,351 real documents the committed scanner certified, 19 are now uncertain (14 by the layout rules — a word on the
line of a box that must have it to itself, mostly `display:table-cell` rows; 2 backslash font names; 2 tags written `"alt=`; 1 table closing a
paragraph) and 3,332 stay certain; none is newly certified; all 60 development originals and all 35 stratified-control originals stay certain.
Nothing added after the first comparison with Chrome (the exhaustive grids, the property sweep, the reviews' findings) changed the text read
from one real document (all 22,483); two documents came back to certain when three conditions no page needed were taken out, and read exactly
as Chrome prints them (`r18_two_docs_vs_chrome_pass13.json`).
*Less code where the evidence allowed.* The mutation check named conditions no page needed; each was taken out and all 3.7 million pages run
again (none certified wrongly; 13,669 more of the same 2,930,187 pages certified): a void element out of the flow, a picture or field after an inline box, the line an
inline box stands in, white space after a whole element, and four redundant operands.

**C2 — a join the source cannot settle is neither proved nor disproved (`Grader.adjacent`, `both`, `spaced`, `runs`, `pieces_match`,
`struck_kept`; consumers `carriers`, `merged`, `merged_units`, run-in `section_path`).** `adjacent` has three answers. A certain reading proves
touching or apart. Under an uncertain reading only what needs no reading is proved: where no tag (and no null byte) stands between two pieces
their bytes settle it — characters between them: apart; the two meeting inside one run of text: touching. Every other join is unknown, and a
target that meets one is graded under both readings (`both`): a check the two judge alike stands; one they judge differently — or only one of
them writes — is `unresolved` (`adjacency`).
*The key has no say (round 9, R9-1), and neither has the route.* A first version let two units that were each a whole piece of the key stay apart
without asking: the same output passed in an uncertain file and was unresolved where the source proved the pieces touching. Withdrawn. A second
let the route's own text between two pieces prove them apart: a route that keeps text the page hides was then failed for pieces that touch on the
page, where the certain twin of the same file passes. Withdrawn too. Consequence, stated: in an uncertain file two pieces of a key in two units
with markup between them are `unresolved` — read as touching they are one text. (Every development and stratified-control original is certain;
2 of 21 held-out HTML originals are not.)
*One join closed and the next open.* The other reading of a glued run used to put a space at every join. `spaced(items, want)` closes the joins
the key prints closed — the key's characters located in the text, at every place they stand whole, or, where a mark the key does not print
stands among them, by the longest runs the two share; it only tells `unresolved` from `fail`, it never passes. Where a check looks for one
carrier equal to the key's text (`section_path`, `unit_printed`), every run of its parts is asked (`runs`): read the other way, a piece that
touches it is a carrier of its own (`1.` beside `Busi` + `ness`). `pieces_match` got the same exactness.
*Recognition rows.* A structure count the two readings judge differently is left open and never decides a target (`verdict_of`).
Strike placement that only the source's map could settle is `unresolved`/`struck` under an uncertain map (`struck_kept`).

**C3 — proved > open > failed (`Grader.printed`, `field`, `basis`, XML `unit_printed`).** An open dash proves nothing: read strictly it is not
printed, so a carrier that proves the phrase wins; only when nothing is proved is the field read leniently, and a pass that needs that is
`unresolved` (`numeric_boundary`). From the reviews: the same order among accepted values; a strike lost or invented fails under either reading
of the dash; and the source arbitrates a dash only over the route's text at that place (`at_place`) — the place running from what the source
prints before the phrase through the phrase, so a route that cuts its text right at the dash still prints it; a text that is plainly wrong at a
place answers nothing for another that is open; and texts that lie both at a place the source signs and at one it does not decide nothing
(inside one unit no place can be told from another): open, never a pass.

**C4 — an absent value is never an agreement.** Page declarations: absent, `null` and `{}` declare nothing; every other value is a declaration
and must validate (`pages_declared`). The same class elsewhere: an XML field that names no instance (`group.at`) is in none; the run-facts block
must be an object.

**Known, not changed (reported to Codex).** (1) In an uncertain file, consecutive whole pieces of a key with markup between them are
`unresolved` (R9-1 kept; three probes of the first review ask for a pass). (2) One unit that prints the phrase at a signed and at an unsigned
place of the key with a dash of its own is `unresolved`, not `fail` (the second review asks for a failure: nothing in a unit tells its places
apart). (3) The scan takes time with the square of the nesting depth (16,000 open `<div>`: 8 s; real filings nest tens deep). (4) Whether a
character the scanner marks as struck is painted struck is not re-checked here beyond round 9's Chrome cases.

**Verification (on the final code: `anchor.py` f5cabd79a823a52c, `grade.py` 05c078edf8605972 (the copy every run measured, 2c7dc6c4c818ca6e, differs in one docstring only: same syntax tree)).** 242 unit tests, with 250 pages local Chrome
printed as sub-tests (`tests/fixtures/browser_pages_r18.json`: 162 the scanner must certify and read as Chrome does, 88 it must not certify — each
tells the scanner from a one-change variant of it). The scanner against Chrome: 2,931,643 pages in 14 families, no crash, 1,575,759 certified,
2,343 of them different from Chrome's plain text and every one equal to Chrome's agreed text (struck 244 + 51, textarea 1,238, zero opacity
741, letter case 58, ix:hidden 11); the grid of agreed differences: 794,880 pages, 439,630 certified, 0 exceptions. Real filings: above. His 13
regression methods: 13/13. C2/C3 probes in their strict mode: 27/27 methods. Every issue of rounds 2–17 replayed (`scratch18/final_runs/`):
129 hold, 11 changed by a later rule (quoted there), 6 not code or not checkable without the key; 0 regressed. The first review's probes: 48 of 51
as required (3 by design, above); the second's: all but the one-unit dash (by design); the scanner review's 40 pages: every one read as Chrome
reads it or not certified. 48/48 real-original variants. Mutations, mechanical (`r18_mutate_ast_final.json`): 1,288 on every changed line of
the two files, 1,198 red; the other 90 are classed one by one in `R18_MUTATION_RESIDUE.md` (31 words of lists copied whole from the HTML
standard, guards and resets of earlier rounds, and 9 scanner conditions no page of 1.1 million could tell from their variant). Regrade of the 13
saved route folders by a frozen copy of this code against run 34f (`scratch18/regrade_final/`): 0 verdict flips, 0 result-row changes, every
graded file byte-identical but one summary, where 23 snippets of uncovered text differ in white space only (positioned `%` signs are lines of
their own now). Re-link sweep (60 HTML files x 11 routes, `scratch18/relink_pass12/`): only the Arrowhead file's links change; dry run of its
re-link: the uncovered text falls from 24,059 characters to 0 (edgartools routes) and 232 (docling routes), units without a place from 8–9 to
0–1; the official re-link is made from the commit, so that its provenance names it.

## 43. Round 19 (2026-10-05 11:36, Codex's `CODEX_REVIEW_R18.md` on 27c49c6ea, and his `CODEX_REVIEW_R19.md` and `CODEX_REVIEW_R19_QUICK_FOLLOWUP.md` on the versions of this fix; round 18's four corrections pass and its three judgment calls are approved; package 3 still approved, still staged) — three remaining gaps, all reproduced, closed with his patch; the siblings an own sweep, its checks and an independent review found closed with them

**Method.** As before: an audit of my own before his file was opened (the hint was one sentence: a CSS setting makes Chrome show plain text the
scanner certifies as struck), his file, his 13 new regression methods run against this code (`round18_codex/probes/regressions.py`: 10 methods,
45 sub-cases failing or crashing on 27c49c6ea, none after), each of his guards looked at as a class, an independent review of the result (a second
model, its own probes), and everything that passed before run again. Built and proved in a copy (`grader_review_codex_20261003/scratch19/`), the
served code untouched until it was whole.

**N1 — an attribute the parser decodes and the scanner read as written.** `rel="style&#115;heet"` loads a sheet: the scanner's link test read
the raw tag, so a page whose sheet hides text was certified as unstyled, and "nothing struck" was certified under a sheet that strikes;
`align="&#108;eft"` floats a picture the scanner read in the line. As he wrote it: an `&` in a link's `rel`, or in the `align` of an element
it floats, makes the file uncertain. The class is these two: the style string was and stays decoded, `hidden` with any value is uncertain
already, `popover` and `open` are read by presence, no other attribute's value is read — but for the one below.
*Its sibling, from the review:* a `<meta http-equiv>` instructs the browser, and two instructions change what it shows: a content security
policy turns the style attributes and sheets off (Chrome prints the text a `display:none` hides; each page in a tab of its own, for a policy
stays with its tab), and a refresh sends it to another page (Chrome then prints that page: 10 becomes 20 — Codex R19 N3, reproduced with the
destination served from memory; a version of this round had let the refresh through on a test whose content was no working refresh). A page
that carries either, or writes its `http-equiv` with a reference, is uncertain. Every other instruction — default-style, content-language, the
cache and compatibility ones old filings carry — changes nothing Chrome prints and withdraws nothing (all 973 documents of the census that carry one say
`Content-Type`).

**N2 — a line the element cannot paint.** `<s style="display:contents">` has no box of its own and paints no line; the scanner certified a strike.
As he wrote it: such an element with a strike of its own withdraws the file's strike certificates (a `contents` child of struck text is struck by
its parent's line: certified, as Chrome paints it).
*Its sibling, from the review:* `<table align="left">` is a float (the old way, as for a picture), and a parent's line does not reach into a
float: the text of such a table inside struck text was certified struck. A table joins the elements an `align` floats (4 real documents float a
table so, none inside struck text: every reading is unchanged).

**N3 — the XML reader.** It certified a reading without the text of an external entity it never read; characters at no bytes (an expanded
entity arrives as several events at the reference's first byte); characters of a UTF-16 or windows-1252 text at bytes that are not theirs (equal
*length* was taken for equal bytes); and it crashed on an encoding the parser does not know — so did the cell grader, which asks the same parser
for the element's name. His guards are in: an external entity reference or an unknown encoding refuses the document; a chunk is placed byte by
byte only when its bytes *are* its UTF-8; the cell grader leaves `value` and `row_label` `unresolved` (`source_reading`) when the reading is not
certified. Differences from his patch, each found by probing the same class, each stricter:
1. *Parameter entities are read as declared* (`xml_parser`: `SetParamEntityParsing`), by both of the grader's readers — the scanner and the
   cell grader's `xml_element_at`, which read one document with two settings: a default a parameter entity declares (`<!ATTLIST v xmlns CDATA
   'urn:a'>`) names an element's namespace, and the cell grader, leaving it unread, took `v` for `{urn:a}v` (Codex, on the first version of
   this round). Left unread — the parser's default — it skipped `%p;` in silence and
   bound a later declaration of the same name: `<!ENTITY % p "<!ENTITY e 'A'>"> %p; <!ENTITY e "B">` in a standalone document read "B",
   certified, where a parser that reads the declarations prints "A" (the review; libxml2). Read, an internal one is expanded where it stands, and
   everything outside the document — the external subset, an external parameter entity — is asked for by the same handler as an external
   general entity, and refused. His separate test of the DOCTYPE is thereby unneeded and gone.
2. *A reference the parser passes over* (`SkippedEntityHandler`): where a document has parameter entities, a reference to an entity nothing
   declares is no error to the parser; it left the text out in silence. Refused.
3. *One rule for a chunk that is not its own bytes:* it is exactly one reference, or one line ending the parser reads as a line feed — else
   nothing is certified. His two lines (no empty span; several characters must begin at an `&`) let one character before a reference that
   expands to nothing take the reference's bytes as its own. Under the rule his empty-span line can decide nothing (the mutation check showed
   it), so it is gone.
4. *A refused document reads as nothing:* the characters read before the refusal were left in the text.

*Changed on purpose, his rule against his own earlier one:* XML text beyond ASCII in ISO-8859-1 or UTF-16 was certified — the right words,
at bytes that were not their characters' (his round-12 probe R12-6a asked for the words, certified). It is not certified now: the rule HTML has
had since round 18 (beyond ASCII, only UTF-8). ASCII text under any single-byte declaration stays certified. Every one of 4,377 real XML
documents is ASCII, declared UTF-8 or US-ASCII; none has a DOCTYPE (`r19_real_census.py`).

**What the own audit found** — the strike's *paint* (`codex_probes_live/r18/r18_strike_paint_facts.py`: every property Chrome lists x every value
it accepts on the striking element, a child, a block child, the parent, and beside a CSS line-through; Chrome paints each page with and without
the strike; 68,146 pages), read before his file:
- `display:contents` on the striking element — his N2.
- *`writing-mode` on a child of struck text: no line on it.* The cause is not paint. A writing mode other than its parent's makes an element in
  the line a box of its own lines (an inline-block), a parent's line does not reach into such a box — and the box drops the white space inside
  its edges: `x<span style="writing-mode:vertical-rl"> net </span>y` prints `xnety`; the scanner certified `x net y`. The every-property sweep
  of round 18 could not see it: none of its 25 page shapes had white space inside an element's edges and none outside. `r19_edges_facts.py`
  adds 8 such shapes (every property x value, inline with and without a doctype, and as a sheet rule: 271,392 pages): the writing mode, under
  its two listed names, is the only property that reads differently, and only on an element in the line. And Chrome accepts names it does not
  list on the style object the sweeps took their names from: `r19_hidden_facts.py` asks it for every listed name under 13 prefixes — nine
  `-epub-` aliases, `-epub-writing-mode` among them (82 pairs on all 33 shapes: 7,544 pages; no other of the nine changes a reading beyond
  letter case). The rule (`_MODE`): a writing mode declared on an element in the line, or by a sheet rule (which elements it reaches is not
  followed), makes the file uncertain; on a block it changes nothing and nothing is withdrawn — a first version refused every declaration, and
  the review brought a real 10-K (Workiva) that turns its table headings with `writing-mode:vertical-rl` on a block: read as Chrome prints it,
  certified before and after. None of the 22,483 documents of the rehearsal download declares one.
- *A strike that may not be seen* (Codex R19 N2: the formatting step would write a strike nobody sees, and an active term would read as
  cancelled). After the fixes above 47 pages of the 68,146 showed a certified strike where the picture does not change when the strike is
  removed. A second method (`r19_strike_second.py`: the line painted red) finds the line on 42 of them — the first method is blind where line
  and background are one colour, or the word is pushed out of the window. The other 5 are two classes, both guarded now; the sweep is left with
  no certified strike that neither method sees.
  *Its colour.* A strike takes its own colour, else its element's text colour — the fill colour where one is given
  (`-webkit-text-fill-color`: found here, Chrome's picture) — and the letters inside may be coloured again
  (`<s style="color:transparent"><span style="color:#000">`). So a `color`, `text-decoration-color` or `-webkit-text-fill-color` that may paint
  nothing, declared anywhere in the file, inline or in a sheet, withdraws its strike certificates (`_SEEN`, `_LINE`). What surely paints is what
  filings write: a colour name, three or six hex digits, `rgb()`/`rgba()` in the comma form with no alpha or the literal alpha 1. Any other
  alpha is not evaluated (his list: Chrome reads `-1`, `-20%`, `0e0`, `1e-999` as none; a first version tested for a written zero). All 47
  real documents with struck text keep their certificates (5 of them write `rgba(…,1)`).
  *Its length.* Struck letters a negative `letter-spacing` sets on one spot have a line of no length, and a box `contain` gives no size paints
  nothing in it. Certificates are withdrawn where struck text stands under such a declaration — on its element or on one above it, the only
  ways either reaches it (`_ROOM`, the `loose` flag of an open element; a spacing that is `normal` or not negative takes no room; a sheet rule
  on either reaches who knows what and withdraws them for the file). **This differs from his patch**, which withdraws them for any file that
  declares a `letter-spacing` or a `contain` anywhere: that takes the certificates of 6 key originals (3 development, 3 held-out by count) whose
  strikes Chrome paints — one a development redline with 130 struck characters, where other runs are tightened by a tenth of a point. Under
  the rule here every key original reads as before, and all 67 of his focused checks pass. He took the rule (`CODEX_REVIEW_R19_QUICK_FOLLOWUP.md`)
  and showed two ways the spacing reaches struck text that the open elements do not show — both reproduced here in Chrome before his fix was
  read: declared on the page's own elements (`<body style="letter-spacing:-1em">`: html, head and body open nothing in this scanner), and on
  a formatting element left open at the end of a paragraph, a list item or a table, which the browser opens again for what follows
  (`<p><b style="letter-spacing:-1em">one</p><p><s>net</s></p>`). The first is closed with his line (a root with such a declaration withdraws
  the file's strike certificates). The second with one line where elements end (`leave`): a formatting element dropped unclosed while under
  such a declaration withdraws them — **not his two lines**, which made the whole file's *text* uncertain for any element so dropped (its
  words are not in doubt, and Chrome opens only formatting elements again: after `<p><span style="letter-spacing:-1em">a</p>` the next strike
  is painted) and withdrew the certificates for an element the parser moves out of a table whether or not it stays open. His 4 new methods
  (13 sub-cases failing before) pass; every key original and every real document that names a spacing reads as before under either version.
  He read this line too and accepted both narrower rules (`CODEX_GATE_R19.md`: APPROVE on the hashes below).
  *Stated, not followed:* text clipped by several declarations together (a fixed height with `overflow:hidden`, a `clip-path`) is read as
  text — the browser's own text — and its strike with it.
- *Scripts.* A script changes the page after it is read (`<span id="n">10</span>` with a script that writes 99: Chrome prints 99, the scanner
  certified 10 — Codex). Not run, and since no reading of the page can then be vouched for, a page that carries one is uncertain: a `<script>`
  element of any type, an event attribute (`on…`), a document set into the page (`srcdoc`, an `iframe` or `embed` with a `src`: it can script
  its parent). Six rows of earlier tests that certified a page with a script were turned (a twin without the script keeps each test's point),
  and one saved browser page was printed again without its script. No certified real document and no key original carries one; the 587 of
  695 further real files that do are pages of EDGAR's own viewer, uncertain before.

**Known, not changed.** Clipping, above. The XML route's adapter (`adapters/xml_fields.py`) reports a document that is not well-formed as
FAILED but would stop on an encoding the parser does not know, and reads parameter entities the parser's own way (a converter's faults, for the
grader to report, not grading faults; no such file exists; the adapter is not changed in this gate, as his review of round 18 says).

**Verification (on the final code: `anchor.py` bfd03f71ff96f7f5, `grade.py` 1ae1490aa6d6c6c3; a frozen copy, `scratch19/frozen_final`, by one script, `scratch19/final_evidence.sh`).** 244 unit tests (two new methods and rows in seven old ones: his 13 methods of round 18 and the cases of his three round-19 probe files and his quick follow-up ported, the
siblings and the review's findings beside them); his own files, run from a copy: 13 methods of round 18, 67 focused methods of round 19, 4 of the
quick follow-up, 13 of round 17 — all pass. Mutations, mechanical (`r18_mutate_ast.py`, every condition on a changed line): 133, 133 red —
earlier passes left 5 green, and each was a finding: two code lines of N3 (his empty-span line; a DOCTYPE test that read an empty system identifier as none), a
needless condition, and two missing tests (a cell graded with no source at all; a root with a harmless style). The scanner against the saved Chrome pages of round 18:
2,931,643 pages — the same text on the same 2,521,306, no crash, and no page newly certified; 1,573,152 certified, 2,607 fewer: 2,113 that
carry a script, an event attribute or a framed document and 494 that declare a writing mode on an element in the line or in a sheet; the
certified differences fall from 2,343 to 2,212 (131 were script pages), each equal to Chrome's agreed text; the grid of agreed differences:
794,880 pages, 0 exceptions. The new sweeps: 278,936 pages, 229 certified and different, all of them letter case under `text-transform` (and
its `-epub-` name) or a zero opacity. Strike paint: 68,146 pages, no certified strike that neither method sees; floated tables in struck
text, 31 pages, 18 pages of lines that may not be seen and 31 of spacing on roots and reopened elements: no certified strike Chrome does
not paint. Real filings, the committed scanner beside
this one (`r19_real_census.py`): 22,483 HTML documents — the whole reading identical in every one (the 3,332 certified, both strike
certificates, the text, every byte span, every struck character; 47 documents hold struck text); 4,377 XML documents — all certified before
and after, every character and byte span identical; the 126 HTML and XML originals of the key, held-out by count only, on the final code
(`scratch19/evidence/key_originals_final.txt`): the whole reading
identical in every one. Regrade of the 13 saved route folders by the frozen copy against run 34f (`scratch19/regrade_final/`): 0 verdict
flips, 0 result-row changes, and all 39 graded files byte-identical to round 18's regrade. Every issue of rounds 2–17 replayed: 128 hold, 12
changed by a later rule (the twelfth is R12-6a above), 6 not code or not checkable without the key; 0 regressed. C2/C3 probes, strict: 27/27
methods. The reviews' probes of round 18: as then (48 of 51 with the 3 by design; the second review's rows and the scanner review's 40 pages
unchanged). 48/48 real-original variants. The independent review of this round (`scratch19/review_r19/`): five findings (three fixed, the
real 10-K kept certified, scripts guarded since); clean on about 70 XML cases, 453 declared encodings, 30,000 random XML documents, chunk edges
of the parser, 252 `display:contents` strike claims, twelve properties beside the writing mode, and 1,138 further real HTML files (on the version of 08:50).

## 44. Package 3 active; run 35, the official baseline (2026-10-05; Codex: `CODEX_GATE_R19.md` and `CODEX_RUN35_VERDICT.md`, both APPROVE)

**The pointer.** `golden/PACKAGE.json` names package 3 (`FINAL_KEY_FOR_CODEX_20261004_0557`: key 41d5c68db597e48c, manifest 39a5df74a1176ce1, contract addendum R4), the
package approved in round 14 and unchanged since (`9ccfd7c19`; `golden/check_package.py`: 21 recorded files, 5 verbatim copies, 457 stamps current). The grader's code is
round 19's (`c96ec20bd`), byte for byte.

**One file linked again, in a tree of its own.** The scanner of round 18 reads 15,498 referenced control characters of the Arrowhead exhibit that the saved routes, linked
by the older scanner, did not cover. All 13 saved route folders were copied to `prepare_work/grader_runs/run35_20261005/`; in the 11 HTML routes that one file's five link
fields were stripped and `anchor.link` run again by a pinned export of `c96ec20bd` — every tool field asserted identical, the other 71 files of each route byte copies,
the old folders and their graded results untouched (hashes; `ROUTE_PROVENANCE.json` per route, `RUN35.json` for the run). Uncovered text of that file: 24,059
characters → 0 (EdgarTools routes), → 232 (Docling routes). Linking every HTML file of the 11 routes again changes this file only (660 files × routes).

**Run 35 and its causes.** The 13 route folders graded against package 3, and two controls: package 2 with the new routes (0 verdict flips, 0 check rows — the re-link
alone changes no grade) and package 3 with the old routes (80 flips, 256 rows — the same as run 35). The 80 are the package's declared changes: 39 exclusions (three
page-number blocks), 19 pictures `FAIL → APPROXIMATE`, 22 corrected-header passes; 8 further rows change their explanation only. The numbers are in
`REVIEW_HANDOVER.md` ("current: package 3, official run 35"); the earlier ones there are history.

**The real-original check reads the active package** (`checks/real_pairs.py`), so two of its expectations were made to hold under any package: (1) its scanned-page
case expected a pass or a failure of the words of a block package 3 declares a picture's text — it now follows the key's declaration: declared approximate, the verdict
must be `APPROXIMATE` and the approximate row must report the planted damage (none; the deleted words; the critical "not"; the disorder); strict otherwise. (2) Its
reading-order test asked only that the gate was not passed, which a one-file route never does (the other files are not measured): it now asks for a break in the damaged
file itself and for none in every valid control (Codex's patch; with the order detector switched off the test fails). 48/48 under package 3 and under package 2.

## 45. The worktree merge, groups 1 and 2 (2026-10-05; Codex's six groups of `CODEX_RUN35_VERDICT.md`; Fable implements, Codex reviews each; run 35 stays the baseline)

Codex's worktree (`prepare_work/tool_selection_20261004/code`, 38 changed files) is merged group by group; nothing is copied whole, and each piece is measured on the
saved development routes before it is kept. The worktree itself is only read.

**Group 1 — the linker finds the items that carry a text once (`0d10d0256`; `CODEX_MERGE_G1_VERDICT.md`: APPROVE).** `anchor.link` asked every item again, at each
placement, whether it carries the same text (time with the square of the items); the index `same_text` is built once. All 660 development route files of run 35 link to
the same bytes, the 13 routes regrade to the 39 graded files of run 35, 4,000 repeated-text cases read alike; link time on two 60-file routes 280.0 s → 72.2 s and
263.8 s → 68.6 s, peak memory unchanged.

**Group 2 — a table is placed in its own table, a row in its own row.** *The defect.* The linker placed a short text between its anchored neighbours wherever those
words stood next. A table cell that reads like a cell of another table, or of another row, was then tied to the wrong one whenever the tool's order and the source's
differ (a header row the tool lists first, a moved row, a repeated label). On the EdgarTools development route 224 of 73,366 table rows had their cells in several rows
of the source, 50 tables had cells in another table, 172 cells had no place at all; the steps that read the links inherit it — the screen step set those cells in the
wrong row or column. Two failures of run 35 were this, not the tool: Carnival's header years 2017–2022 stood linked in the twin table before theirs
(`bundle-015/0000815097-23-000012:T05`, the one failing cell of the best route), Levi's repeated period labels in reverse column order (`bundle-009/0000094845-24-000045:T01`, `T02`).

*The rule (`anchor.table_places`).* A table of the tool is tied to a table of the source when both hold the same texts, each as often, and no other table on either side
does. Its cells are then placed only where a cell of that source table reads as they do. Where the tool kept the table's rows — the same rows by their texts — a row whose
texts single it out is tied to its source row: its cells stand in that row, a text the row holds twice in the row's order. Such cells have one place and are placed first,
whatever order the tool lists them in; the others are placed as before, between their neighbours, but only at their table's cells; one left without a place takes the first
of its places that is free. The places of a tied table are kept for its cells: no other item takes one — a paragraph the tool lists before its table took a cell's
place, and the cell, left with none, was pieced together on the paragraph, outside its table (Codex G2-C1). So every cell of a tied table that has text stands exactly
at one of its places: on 20,000 random sources (186,463 such cells, `g2_fuzz_tied.py`) none is lost, pieced, doubled or displaced by another unit — the first
candidate lost 621 and pieced 30; a guard on the piecing alone turns those 30 into losses. Texts are the only evidence: two tables that read alike, two rows that read alike, are not told apart and are taken in order as before; a table
whose cells the tool changed, merged or dropped is not tied and is placed as before. No name, number or word of any document stands in the rule.

*The source's tables are the scanner's own record (`Visible.tables`)*: every table in order, its rows, each row the byte spans of its own cells — a nested table is a
table of its own, a cell outside any row stands in the row the parser makes for it, comments, scripts, quoted attributes and raw text hold no cell (the worktree's
tokenizer cases, asked of the scanner). The scanner reads nothing differently: on 22,483 real HTML documents and 4,377 XML documents its whole reading (certainties,
text, byte spans, struck characters) is the same as before. The record is the worktree's own reader's (an `HTMLParser` pass) and a plain search for cell tags on all
22,423 documents of the rehearsal download (440,294 tables, 9,449,984 cells), and Chrome's own tree on the 60 development originals (951,927 cells: table, row, text).
A second reader of HTML was not taken over.

*A position that was a mark's* (Codex G2-R2; in main since the marks were added). `place` gave back, as an item's position, the start of a mark it had found before a
text found alone; the check that a copy is already held looks at the text's own start, so a second unit that reads the same was given the same copy and the
other copy stayed uncovered — for any unit with marks on both sides, in a table or not. The anchor still takes the marks in; the position given back is the
text's own. On 20,000 random sources with marks raised inside cells, in cells beside them and on paragraphs (`g2_fuzz_marks.py`; 96,723 units declaring marks): 83
anchors held by two units and 25 places by two cells before, none after; no saved route changes.

*The screen step reads the same record* (`adapters/screen_grid.py`; Codex G2-C3, his proposal): its plain search for cell tags ended a cell that has no end tag at the
next cell tag anywhere — a paragraph after the table lay in the table's last cell — and lost the outer cell after a table inside it. `tag_cells` marks and bounds the
scanner's cells; `apply` walks from an inner cell to the cell it stands in (the worktree's seven consumer cases, kept as written). No saved route changes by it (all
route files of the 11 routes: the same bytes); the step reads the source once more — `tag_cells` on the 60 originals 1.6 s → 48.9 s, about 0.8 s a file — which a
pipeline that scans a file once for linking, formatting and the screen does not pay.

*What the worktree's rule did that this one does not.* It tied a row of the tool to a row of the source when the source held one such row — whatever the tool's other
rows were: on the saved screen route 20 cells lost the place they had; and it tied two tables of the tool to one table of the source. Both are tests now
(`test_rows_the_tool_did_not_keep…`, `test_two_tables_of_the_tool…`), with the row order of a text held twice (`test_a_text_twice_in_a_row…`).

*Measured on the development routes* (the candidate against run 35; the 11 HTML routes built again from the four base routes — links, then the formatting step, then the
screen step in local Chrome with every request aborted; the same rebuild with main's code and the saved links gives run 35's folders back, file for file):

| | EdgarTools (base route) | EdgarTools + formatting + screen | Docling (base route) |
|---|---|---|---|
| table cells without a place | 172 → 0 | 172 → 0 | 511 → 504 |
| rows of the tool with cells in several rows of the browser's tree | 224 → 12 | 65 → 0 | 19 → 12 |
| tables of the tool with cells in several tables | 50 → 0 | 50 → 0 | 6 → 0 |
| rows in one browser row, not in the tool's column order | 51 → 47 | 3 → 3 | 47 → 47 |

Every changed record (3,204 over the 11 routes, by unit and cell number) was checked against Chrome's tree by a checker that takes nothing from the linker
(`g2_oracle2.py`, after Codex G2-C2): cell bounds from another reader, each confirmed against what Chrome shows for the cell (951,927 of 951,927), every piece of an
anchor whole inside its cell and reading the cell's text there, and the row judged by the browser rows that *read* as the tool's row — not by where the candidate put
the row's other cells; an anchor over several cells must have every visible character in a bounded cell of one table, and a pieced one must read the parts of the text it
declares, in order (Codex G2-R2: both were accepted too easily; neither occurs in the saved routes — the corrected checker classifies every record as before). Of the 2,952 changed cell records none stands worse than before: 1,955 moved or placed, 997 the same place with another flag; the 234 changed
table envelopes are the span of their cells. On the EdgarTools route, cells in a browser row that does not read as their row: 292 → 7, outside every cell 17 → 0
(with the screen step 17 → 0 and 17 → 0); the 7 are in two tables the rule does not tie, unchanged since run 35 and flagged. One Docling cell, a page number set as
a table of one cell, is doubtful before and after (now in no cell at all). No cell lost a place. Of the EdgarTools route's 10,162 tables with cells 9,137 are tied, 1,004 read like another source table (not told apart), 21 read like none; of their
342,465 cells 324,150 have one place. Grades: three targets `FAIL → PASS` (ten check rows: the two failures above) and nothing else in 13 routes — the best route's
cells 170/171 → 171/171 on this development sample, which proves nothing about other documents; the PDF and XML routes regrade to the same bytes. Link time +1 to 6 %
over three measurements (the last: 72.4 s → 73.3 s, 69.2 s → 70.7 s on 60 files), peak memory +31 to 33 MB. Run 35 remains the official baseline: these numbers are the evidence for the change, not a new run.

*Stated, not hidden.* (1) Equal texts in exactly one table on either side are evidence, not proof: a tool that drops one of two tables and changes the other to read
exactly as the dropped one would be tied to the wrong table. (2) Tables, rows and cells that read alike are taken in order, as before (5,461 of 329,611 cells in tied
tables). (3) Cells of tables the rule does not tie are placed as before: 7 (EdgarTools) and 12 (Docling) stand in a row that does not read as theirs, as in run 35. (4) The `out_of_order` flag — read by no grading rule — moves with the places: 784 records lose it at the same place, 384 gain it; a cell can still get it from
a neighbour the tool lists after it and the source prints before it, as before this change. (5) A short text the tool lists before a table and that reads as one of its cells
never takes the cell's place; if its own place lies beyond its window it stays without one (`not_in_source`), where the two were swapped before. (6) A table inside a
table stands in none of the 3,297 real filing documents looked at (only in the SEC's viewer pages): the screen step's handling of it rests on its tests. (7) The route
files get no new field: the worktree's `source_table` had no reader (Codex: omit).

Tests: 281 (37 new: `tests/test_table_sources.py`, `tests/test_screen_grid_tokenizer.py`). Mutations of every condition on a changed line: 111, 103 red; the eight
green ones change no result (the pass for short texts re-asking a long one it would fail again; the first pass's search direction for a cell with one place; in the
piecing, an item asked whether it is itself before it has a place; in the screen step, a cell counted as standing in the cell that ends where it begins, and two
bounds of the walk that the test after it repeats).

## 46. The worktree merge, group 3 — pictures kept and placed; the tool's heading evidence (2026-10-05; Codex's `CODEX_MERGE_G3_DECISIONS.md`)

**The defect.** 26 of the 60 development originals show pictures: 732 picture tags. The EdgarTools routes carried none of them: the adapter read a paragraph as one run
of text, and a picture inside it — no text to add to the run — was dropped with the paragraph's structure (0 image units in the saved routes, 0 picture nodes in the
saved parses). The Docling routes carried 622 picture units, each "placed" in the whole gap between its neighbours — a place that certifies nothing, shared by every
picture of a scanned document.

**The adapter** (`adapters/edgartools_html.py`; the worktree's lines). A picture node makes its paragraph a branch, like any block, and becomes a unit with the `src`
the tool gives: 615 units in 23 files. Nothing else moves: in all 60 files every other unit — text, cells, anchors, flags — is as before, its number in the list aside.
The tool's own evidence for a heading (how it found it, its confidence, its style) travels with the heading unit as `native_heading`: a claim, read by no grading rule
(8,040 heading units, 4.2 MB). The saved parse records what it keeps (`retain_pictures`, `retain_native_heading_evidence`): a parse saved before pictures were kept
answers to other settings and is refused (all 60 old parses, tried). **Not taken: the tool's inline-XBRL fields** — 79,664 fields in 19 files, 215 MB, the route
folder 3.9 times its size, because a text-block field carries its whole note a second time, detached from its bytes; nothing reads them, the source's own `ix:` tags
keep them with exact bytes (Codex's decision 3; where preparation uses numeric tags it keeps their metadata and source associations once per source — not done here).

**The scanner** keeps, for each picture tag it lists as shown, its `src` as the parser reads the attribute (`Visible.picture_sources`, `attribute_value`): character
references decoded once, by the attribute rules of the HTML Standard — a named one without its semicolon stays as written before a letter, a digit or `=`. Compared as
written, `a&amp;b.png` was not the tool's `a&b.png`: the picture stayed without a place, or stood at another tag that spelled the name plainly (Codex G3-C1; his
function). It reads 27,869 spellings as Chrome does; none of the 732 real names holds an `&`, and no route changes by it.

**The linker: a picture unit stands at its own picture tag, or nowhere** (the worktree's rule as written; Codex's decision 1). The tag the unit names by its `src`, when
one shown tag carries it; among several that carry it, or for a unit that names none, the only one between the unit's anchored neighbours; and no tag twice. Anything
else has no place (`ambiguous_image_location`): as many tags as units between the same neighbours is no identity, and no picture is given the next free tag. The gap
between neighbours is no longer an anchor. EdgarTools: 615 of 615 units at their tag (613 named by a `src` that occurs once, 2 by `src` and neighbours), every tag
carrying the named `src`, none held twice. Docling names no resource (its HTML reader gives none under any option of the benchmark's version — Codex's test): 539 of
622 placed, 83 without a place, 77 of them the pages of scanned documents.

**All 732 accounted for** (`PICTURE_INVENTORY_*.json`, from every source, also one with no picture unit): EdgarTools 615 held by one unit each, **117 held by none**
(107 in files that have picture units; 10 in three files that have none: `amgq12023ex991.htm` 4, `tm2312962d1_ex10-3.htm` 5, `duk-20240331.htm` 1); Docling 539 and
193. A picture no unit holds is a line of the inventory, never a unit.

**Grades against group 2, 13 routes: only the picture blocks move.** EdgarTools (3 routes): the 8 picture targets `UNRESOLVED` → 2 `APPROXIMATE`, 6 `FAIL` — the picture
is there and nothing reads it (`printed_text` approximate with every word missing; `references: phrase`; three also `section_path: missing`). Docling (8 routes): 3
picture targets `FAIL → UNRESOLVED` — their units have no place. No cell and no text block changes; the PDF and XML routes regrade to the same bytes; the count of
textless items at a place that cannot be true (pictures in an empty gap) falls to none.

**Not here: the pictures' text.** Reading pictures is a separate tool, built only on the owner's go (`DriversFinal/PrepareTools.md`, "Image OCR (Oct 5)"); it fills
picture units by file name. The earlier picture-reading run is not restarted; its saved work stays as evidence. Until then the six failures above are failures.

**Parked with the PDF stage:** the worktree's Docling list-marker and margin lines (`docling_html.py`, two test files). Docling's HTML output holds no margin label and
no marker the rule would restore (171,369 texts); all their effect is on PDF (442 page headers, 1,070 footers, 239 markers).

*Stated.* (1) The linker places by the scanner's inventory also where the scanner's reading is uncertain (a tag it does not follow); the grader certifies no picture
count there. (2) An unnamed picture the tool lists away from where the source shows it has no place, even when it is the source's only picture. (3) The grader's rules
for a route's own `gap` flag stay: a route may still carry one; the linker makes none. (4) Route files +5.9 % (EdgarTools). Times of the one fresh conversion beside the control's, 60 files: the tool 51.71 s → 53.21 s, the adapter with its
linking 72.10 s → 79.41 s — single runs on a shared machine, neither a measured slowdown nor a proof of none. (5) The name was the tool's claim, compared with the source's — and EdgarTools
rewrites the file's text before it parses it (runs of spaces, a space before a point, a space added after a point before a capital letter, `&amp;amp;`, zero-width
characters), so a name it changed found no tag, or the tag of another picture that bore the changed name: with and without text neighbours, with and without
the other picture's unit, 24 wrong placements in 64 (Codex G3-C2; his cases). **The tool no longer sees a name, and the tag decides the place.** The scanner
records where every picture tag writes its `src`, shown or hidden (`Visible.picture_names`: the value's byte span and the name as the parser reads it); the
adapter hands the tool the source with each name replaced by a code it cannot alter and no written name can impersonate — the source's own SHA-256 prefix and
the tag's first byte (`codes`, `named`) —; each picture unit names the tag its code stands for (`tag`) and the linker places it there if that tag is shown, else
nowhere — no name and no neighbour decides for a unit of this route, so a hidden tag that names a shown tag's resource stands for nothing, and a unit whose
`src` is no code of this source (a tag the scanner does not list, inside `<template>`; a name the tool made up) is placed nowhere and keeps the tool's name
(Codex's follow-up: the restored name alone let a hidden picture take the shown tag, and a template picture its name). The name is given back after the
linking; the linker reads the source once for both (`link(vis=…)`). Codex's 64 + 140 placements (hidden and shown copies of one resource, both orders, either
unit alone, with and without neighbours, template pictures, a name shaped like a code, repeated shown resources): every shown picture at its own tag, every
other unit unplaced. Of 5,973 picture names in 22,483 real
documents none was touched by the tool's rules (letters, digits, `.`, `_`, `-`, no capital): the 60-file route's files are the same apart from the recorded
seconds and the settings label. A reader of pictures takes the name from the source tag.

Tests: 316 (35 new: the name protection and the tag's identity (10), the worktree's `test_edgar_images.py`, `test_image_sources.py` — one case rewritten for this scanner after asking Chrome: a raw-text opening tag
that ends inside a quoted attribute is not followed, and a `<head>` written so shows both pictures —, its heading cases of `test_edgar_metadata.py`, one case for
each condition of the picture rule and of the heading rule, and the attribute cases). Mutations of every condition on a changed line: 82, 79 red; green: the two
labels of the saved parse's settings, and the picture test on units listed after a picture, which have no place yet.

## 47. The worktree merge, group 5 — the exact places of struck text; the redline join in the boundary gate; what stays parked, with its measure (2026-10-05; Codex's `CODEX_MERGE_G3_G4_REPLY.md`, item 5)

**Measured first (the 13 routes of §46, development files only).** No graded target of the best route (EdgarTools + formatting + screen: cells 171/171, the six
failing blocks pictures) fails for spacing, struck text or hidden text, so the worktree's five pieces of this group were measured against the document-wide gates:

| What the gates count | best route | Docling's best |
|---|---:|---:|
| word-boundary faults (`honest_anchors.boundary`: the source's characters, a word or number boundary lost or added) | 921 items in 22 files, 1,385 faulty gaps | 662 in 38 |
| … struck text printed glued to its neighbour: the scanner reads a redline apart (§36), the tool prints the page (`TheExcept`) | 1,234 gaps, 6 redline exhibits | 0 |
| … a space the tool adds inside a word or a number across inline markup (`CORP ORATION` over an `ix:` tag; `no t`) | 136 gaps in 16 files, 7 inside numbers | 1,128 |
| … a real space the tool drops | 15 | 1 |
| text printed with no place in the visible source | 0 of 400,943 items | 42 items of hidden text (475 characters), 1,140 found nowhere as one run (picture names, drawn text) |
| items with struck phrases (`struck`) | 1,629 in 8 files — in 639 the phrase stands more than once in the item's text | 2,219 |

**Ported: the exact places — `grade.struck_at`, written by the formatting step as `struck_at`.** Ranges `[start, end)` of the item's text (code points) the
source prints struck through, from the scanner's own maps: the search form at the item's places (`flat`, `s`, `e`) against the text's search form, the struck flag of
each character (`Visible.struck_flat`, a derived map made on first use); a run of struck characters is one range per word (white space is never covered). Written
only where the decoration is certified (`struck_certain` — which the scanner gives only where `plain_certain` holds, since `sheet_can_strike` runs over the same
decoration rules; a test guards the implication), every place of the item is a byte span, the places do not overlap, and the text is the source's text at its
places in the comparison form; else the field is absent and the phrases stay as the wider claim. A converter's own `struck_at` is dropped where the source shows
otherwise, kept only where nothing can be certified (as `struck`). **The boundary gate** no longer counts a join the source's own strike-through delimits
(`redline_apart`): when the item's `struck_at` equals the scanner's answer and the text read apart at those places gives the source's words and numbers, the two
runs are two words — a forged, shifted or subdivided claim is simply not the answer and excuses nothing; spacing inside a run still counts. Nothing else of the
grader reads the field: no verdict, key or strike comparison changes (`struck_kept` places a repeated phrase by the source already).

Why this and not the worktree's shape (`source_richtext.exact_struck_ranges`, `decorated_boundary`; its tests carried, re-aimed at this field): (1) one reading
instead of two — the gate's twenty lines of validation become "equals the scanner's answer"; (2) the comparison form aligns the text, not the literal characters —
Docling folds quotes and dashes: 2,218 of its 2,219 struck items get places, 1,909 by literal characters; (3) `struck_certain` alone, proved sufficient;
(4) a list of pairs: no status strings, no second copy of the byte spans (the item's anchor and the scanner give them), an absent field where no exact answer exists.

**Checked.** Chrome 147 on the 8 real files with struck text (scripts off, no request): 5,517,935 characters identical to Chrome's text, 92,393 struck on both
sides, 0 disagreements (`g5_browser_struck.py`). Two computations, one answer: on every item of every HTML route the places and the phrases name the same
characters in the same order (1,629 / 2,218 / 2,219 / 3,015 items; 18,107–18,422 ranges, none over white space). Grades of the 13 routes against §46: **0 target
flips, 0 field rows changed**; `honest_anchors.boundary` on the best route 921 → **136** (in 21 files: clf 147 → 0, pfgc 208 → 10, lesl 153 → 2 and 25 → 2,
tm2312962d1 ex10-2 115 → 8 and ex10-3 158 → 6, ss3397139 8 → 1), Docling render + formatting 329 → 250, the Docling HTML routes unchanged (637, 662: Docling
reads redlines apart itself). Route files: the EdgarTools formatting route 78 MB → 78 MB. Codex's review of the candidate (`CODEX_MERGE_G356_VERDICT.md`) found two
slips, both reproduced and taken as he wrote them: the text's positions were counted character by character while the comparison form drops the key's
`~~` marks as pairs — a text printing `~~old~~new` got `[0, 3)` (`~~o`), now `[2, 5)` (the map is built with the same pair removal); and a claim's ends were
accepted by equality, which in Python makes `[True, 3]` and `[1.0, 3.0]` equal to `[1, 3]` — now only integers are the answer. No saved route prints the marks
with a `struck_at`; no saved claim had such ends. Mutations of every condition on a changed line: 44, 43 red; green: the cache of the text's positions
(`own or …`, made once per item). Tests 347 (31 new: this field's 13, the worktree's `test_r15_boundaries.py` 13 — one case adapted:
a page with an `<svg>` or a `<script>` is not certified since §43, its picture count not measured, nothing on it counted dishonest — and
`test_source_numeric_references.py` 3, as written).

**Parked, with the evidence (the return point: the step that fixes production text, with a browser pass it already pays for).** `source_boundaries` — a space the
tool added removed on browser proof (same line, touching glyphs, nothing between in the DOM): 136 gaps on the best route, 1,128 on Docling's; it needs a DOM-to-byte
map and a browser pass (the worktree: parse5 + Chrome), which this merge does not add (Codex, group 4). The 15 spaces the tool drops no step restores.
`source_visibility` — hidden text cut from the source before the tool parses it: nothing to cut on the best route (EdgarTools prints none of the 2,522,773 hidden
characters of the 60 files), 42 small items on Docling's; parked with the Docling route. Their tests (`test_source_boundaries.py` 4, `test_source_visibility.py` 2)
with them. `source_formatting.py` of the worktree and `source_richtext.py`: merged in substance, above.

## 48. The worktree merge, group 6 — the XML route reads with the grader's own parser (2026-10-05; Codex's `CODEX_MERGE_G3_G4_REPLY.md`, item 5)

**Measured first.** The key's XML sources are forms (schedule 13D/G primary documents): the 3 development files hold 975 elements and **0 attributes**, no DOCTYPE,
no entity declaration. The 4,377 real XML documents of the §43 census hold 8,811,964 attributes — all in the XBRL companion files (`_lab`, `_pre`, `_def`, `_cal`,
`_htm.xml`, `FilingSummary.xml`: `type`, `label`, `id`, `href`, `contextRef`, `unitRef`, `decimals` …), whose data the project already keeps structured; no DOCTYPE, no
entity declaration, no external reference, one CDATA section among them (`g6_xml_census.py`).

**What was wrong, found by the worktree's cases and reproduced:** the route adapter built its own parser (`expat.ParserCreate`), not the grader's (`anchor.xml_parser`,
§43: "one parser setting for both readers") — so a document that needs something outside itself (an external subset, an external general or parameter entity) was
read **silently without it** (`<r>1&e;</r>` with `e` external → the field `1`, status OK) where the scanner refuses to certify; and an element the parser makes from
an entity's text (`<!ENTITY e "<b>2</b>">`) got the position `{44, 44}` — a span of no bytes, a claim of a place that is none.

**Ported (`adapters/xml_fields.py`, 3 lines):** the route's parser is `xml_parser(namespace_separator='}')` — nothing external is fetched, and the document is
FAILED with the parser's own message when it would be needed; an element whose end stands at or before its start tag (markup from an entity) fails the document
("has no source position") rather than being placed. The same reading as before on every real document: the 3 development route files byte-identical to run 35's
(seconds aside); the 4,374 real XML documents of the census give the same units before and after (`g6_route_census.py`), 0 failures either way.

**Carried tests** (`test_xml_route_reading.py`, 5, the worktree's `test_xml_evidence.py` re-aimed at this adapter, and Codex's batch case): external content refused; internal entities and
CDATA read as written; markup from an entity refused and an empty element shown to be no such case; a UTF-16 source — the worktree asked for its positions; since
§42 a character is placed at its own bytes or not at all: the route still reads it, the scanner certifies none of it, and a UTF-8 source places each character.
Mutations on the changed lines: 2, 2 red. Tests 352.

**Parked, with the evidence (the return point: a Prepare step that reads an XML type carrying attributes).** The worktree's `xml_elements` — the ordered element tree
with attributes and namespace declarations beside the units, and its test case: nothing to keep in the key's forms (0 attributes), and the attribute-bearing XML of
the corpus is XBRL the project holds elsewhere. The route keeps saying what it leaves unread (`not_read`); the attribute census covers the 4,377 XML documents of the
saved rehearsal download, not the whole collection, and whether every attribute value already stands in the database was not checked. **The worktree's wider
exception set was right and is taken** (Codex G6-1, reproduced): an unsupported encoding — `utf-7`, `shift_jis`, `UTF-32`, an unknown name — makes the parser
raise `ValueError` or `LookupError`, not `ExpatError`, and the route's loop caught only the latter: one such file stopped the whole batch. Now the file is FAILED
("XML parse failed: …") and the next is read; four bad-first/good-second cases.

## 49. Run 36 — the consolidated baseline after the worktree merge (2026-10-05; Codex: `CODEX_MERGE_G356_VERDICT.md`, `CODEX_RUN36_VERDICT.md`, both APPROVE)

**What it is.** Commit `b18f3743d` (groups 1, 2, 3, 5, 6 of the worktree merged, §45–§48; group 4 — links — deferred to Prepare Step 5), package 3
(`FINAL_KEY_FOR_CODEX_20261004_0557`), the 13 routes built afresh by a frozen copy of that commit's code and graded by it:
`prepare_work/grader_runs/run36_20261005/` (`RUN36.json`; `code_b18f3743d/`; `graded/` = the frozen grades every later comparison starts from;
`DIFF_run35_vs_run36.txt`). Run 35 and every earlier run tree are untouched. Codex's audit: `grader_review_codex_20261003/run36_codex_20261005/`.

**Against run 35:** 51 target changes and nothing else in 13 routes — 3 cells `FAIL → PASS` (group 2), 48 picture blocks (group 3: 24 `FAIL → UNRESOLVED`,
6 `UNRESOLVED → APPROXIMATE`, 18 `UNRESOLVED → FAIL` — pictures preserved and placed at their own tag, their text still unread). Development scores, best HTML
route (EdgarTools + formatting + screen): **cells 171/171**; blocks 49 pass, 2 approximate, 6 fail (pictures), 3 excluded (page numbers, package 3); XML 9/9.
Document-wide on that route: `honest_anchors.boundary` 136 items in 21 files (921 in run 35), `inserted_chars` 0, `unanchored` 0, `reading_order` breaks 0.

**What it does not say** (the next work, in order): (1) uncovered source text in 38 files — 4,744 runs, 11,192 characters, of which 4,682 runs are digits only
and most of the rest roman-numeral page numbers and "Table of Contents" footers: each to be checked against its original and either covered by an approved
exclusion at its proven place or restored — never all called facts, never all called furniture; (2) the 136 word-boundary flags — a space the tool adds inside a
word across inline markup (129) or a number (7), to be fixed generically where a source-backed join proves it, reusing the screen pass; (3) the stratified-control
targets, never converted (65 HTML cells, 35 HTML blocks, 18 XML values), scored apart, with full preparation time and peak memory; (4) then one held-out run on
a frozen candidate; (5) corpus-wide automatic checks, a supplement to the original-backed ones. Picture text, PDF and the deferred links stay explicit and apart.

## 50. After run 36 — the uncovered text and the word-boundary flags, checked against the originals (2026-10-06; Codex's `CODEX_RUN36_VERDICT.md`, item 3)

**The uncovered text, run by run** (`prepare_work/coverage_20261005/`; best route, 38 files, 4,744 runs, 11,192 characters): 4,586 runs are digits standing
at a page break, 47 roman numerals there, 8 "Table of Contents" footer links, 72 digits the crude context test put in a table cell but which stand at page breaks
too (duk, etr, met: the page-number spans of those filers), 29 digits elsewhere — **4,741 runs of page furniture EdgarTools drops on purpose, and three runs of
text** (`form10q.htm`: the cover page's period-end date and file number, the word "Exhibits" of "Item 6. Exhibits"). The furniture stays counted, not exempted:
the key's approved exclusions (three page-number blocks) are applied at their places and nothing else is called a page number; a reader needs none of it.

**The three runs are one defect of the tool, reproduced:** a `<div>` EdgarTools takes for a heading is read only up to its first inline element — `Item 1A.
<a name="x"></a>Risk Factors` comes back as `Item 1A.`, `Note 3. <a id="x"></a>Debt and …` as `Note 3.`, `For the quarterly period ended <ix:nonNumeric …>December
28, 2024</ix:nonNumeric>` as `For the quarterly period ended`; inside a `<p>`, or with the text in spans, nothing is lost. One of the 60 files writes its titles
so; the form is common in filings. **Fixed at the boundary for anchors (`named`):** the source the tool is given has its anchors that hold nothing removed — an
`<a>` with no content renders nothing (white space inside is content and stays; a link with text stays; a tag with a `>` in a quoted attribute is left as it
is). Measured on the 60 files: the title back, 0 target changes, boundary flags 921 → 919, nothing else moves; the tool's own `links` are untouched (an empty link
has no text). The two cover-page facts stay lost: the inline element there is the fact's own tag, which cannot be removed; they stand in the database's XBRL;
the defect goes to the tool. Settings `empty_anchors: removed` (older caches refused).

**The 136 word-boundary flags** (`BOUNDARY_CASES.json`): every one a space the tool's own paragraph text puts inside a word or number across inline markup — 81
in one file's "Table of Contents" footer links split by `<a>` tags, the rest over `<font>`, `<i>`, `<u>`, `<sup>` and `ix:` tags in contract exhibits and iXBRL
prose (`CORP ORATION`, `no t material`, `October 2 4, 2024`); 7 inside numbers. **Fixed where the page proves it (the screen step, which already renders every
file):** `grade.tool_spaces` names, per item, each white-space run the text puts between two characters the source prints touching as one word or number
(the text is the source's at its places, no white space and no break between the two in the scanner's reading, a space there would cut one token in two); the
step wraps the two characters in inline spans of their own (`data-j`), beside the cell marks, and asks Chrome for their boxes; a space is removed only when the
two boxes stand on one line (tops and bottoms within a pixel) and touch (the right box begins where the left one ends, within 0.75 px) — a gap the page's styles
make, another line, a missing box, keep the space. The item records `joins` (`[[start, end, gap]]` in the text as it was). Results on the 60 files: EdgarTools
best route 154 added spaces found, **134 joined**, boundary flags **136 → 20** in 7 files (3 superscript footnote digits the page raises — rightly kept —,
the rest redline-adjacent), uncovered unchanged; Docling best route 1,193 found, 1,090 joined, flags 662 → 110; **17 Docling targets `FAIL → PASS`**
(section paths the split headings had failed on, `bundle-010`, `bundle-018`, `bundle-023`), 0 changes in any other route, no target lost; the whole stack
against run 35: 68 changes = the 51 of §49 + these 17. The screen step's time over 60 files 123.8 → 144.1 s. Tests 360 (+7: the finder's places and refusals,
the tagging beside the cell marks, the join and every way it declines); mutations on the changed lines 47, 41 red (green: the settings labels, the CLI's
`settings or {}` guard).

**Still open, stated:** 20 flags on the best route (above); the cover-page facts of a heading-like `<div>` (the tool); 4,741 runs of furniture reported as
uncovered, by design; the tool-dropped spaces (15) no step restores. Next (Codex's order): the stratified-control targets, never converted; then one held-out run.

## 51. Codex's review of §50 (`CODEX_COVERAGE_CONTROL_VERDICT.md`): four corrections, the uncovered text re-audited by its source, and the control sample's classes (2026-10-06)

**C1 — an anchor is empty by the tokenizer's word.** The regex of §50 could take real text between two comments for emptiness (`<a><!--one-->10 million<!--two--></a>`
lost "10 million"). Now `without_empty_anchors` walks the scanner's own tokens (`anchor._TOKEN`): an `<a>` start tag in the plain form, comment tokens only,
then `</a>` — and nothing else — is removed; a comment ends at its own `-->`; an anchor written inside a script, a title or a quoted attribute is no tag to the
tokenizer and stays; so does one with a quote astray, which the scanner does not follow either. The source the tool is given is returned decoded (`named`).

**C2 — the gap characters are marked with comments, and the page's own ranges are measured.** A wrapping `<span>`, however unstyled, is an element: a page rule
such as `span:first-child{margin-right:-12px}` moved the measured boxes (Codex's reproduction: a 12 px gap read as 0 and joined). Now the screen step puts
`<!--j:n.0-->` / `<!--j:n.1-->` right before the two characters — a comment is no element, no stylesheet rule or structural selector sees it — and Chrome
measures a `Range` over the character that follows each comment. The same reproduction keeps its 12 px; touching letters still join; the cell marks stay
attributes on the cells. One character can end one gap and begin the next (a letter-spaced heading: `Pol<font>i</font>cy`): its two marks stand side by side,
and the script steps over marks to the text (a first version took the next mark for the text and measured nothing — 100 of Docling's joins and one
target lost against the first joins build; `tests/test_screen_joins.py::Measuring`, in Chrome, offline; skipped where playwright is not installed).

**C3 — a joined item's struck places are read again.** `join(gaps, boxes, vis)` calls `grade.struck_at` on every item whose text it changed, and drops a
`struck_at` it cannot re-read (no reading given) rather than leave a place pointing at another character; 50 saved items across three routes had stale
places. `joins` stays the record of the text as it was.

**C4 — the uncovered text, re-audited by its actual source occurrence, and two causes found at their owners.** Codex read six of the "table cell" runs in Chrome:
financial cells of one exhibit, not furniture. The audit now classes each run by the scanner's own cell spans (`prepare_work/coverage_20261005/fix/uncovered_audit.py`):
of 4,744 runs, 3,844 stand in page-break blocks, 221 in other blocks, 669 in table cells — 663 of those in one-text tables (the page-number footers of two
exhibits, each a table of its own) and **6 in data tables**, all in `exhibit992-4q25earningsrel.htm`. Traced: (a) "10.8" was placed at bytes reading
"10.1 | 0.82" — the linker's flat search had matched a short text across two cells. **The linker never places a text across cells now** except as whole cells
(`cell`, `edge`, `same`, `whole` in `link()`): a value cell and its sign cell the tool merged ("10.7 %") may stand together; a part of one cell and the start of the
next may not; a pieced block stops at a cell's edge. (b) The five dashes were taken by copies: the exhibit hides a "%" beside each value for alignment
(`visibility:hidden`), the tool printed it ("8.2 %"), and its visible "%" cell became a copy placed out of order — 646 cells of that table were out of order.
**The scanner records the byte spans of hidden text (`Visible.hidden`) and the adapter leaves it out of what the tool is shown** when the reading is certain:
0 out-of-order cells there now, all six runs covered. The reading is unchanged (22,483 HTML + 4,377 XML real documents, identical). The earlier claim that the
tool prints no hidden text was wrong: it prints it inside units it can still place.

**The inline-XBRL wrappers are left out of what the tool is shown.** The two cover facts the tool lost (§50: the inline element that cuts a heading-like
`<div>` short was the fact's own `ix:` tag) are back; the wrappers present nothing (iXBRL: inline, no presentation of their own) and the tool's XBRL extraction
is not used here (§46, decision 3). On the 60 files: 0 target changes, boundary flags 918 → 902 on the base route, 0 unanchored. One structure row moved:
`bundle-020 T01`'s `kind` (a paragraph the tool now opens with a "contextual" heading — that paragraph holds none of the constructs touched; the tool's
heading heuristic reads the document as a whole); the text is intact and the target's verdict unchanged. Stated, not hidden.

**Results, the corrected candidate (all 13 routes rebuilt; `prepare_work/control_20261006/build_all` + `build_screen4`):** against run 36, 17 Docling targets
`FAIL → PASS` (the joins; the same 17 as the first joins build) and the one `kind` row above, nothing else; against the first joins build 0 target flips.
Best route: cells 171/171, blocks 49/2/6/3, `boundary` **18** in 4 files — 3 spaces the page shows (superscript marks), 15 spaces the tool dropped or
changed in two exhibits (its own paragraph text; stated) —, `inserted_chars` 0, `unanchored` 0; the tool's added spaces 135, joined 115 (Docling 883 of 982,
1,090 of 1,193); every joined item's `struck_at` re-read exact (0 stale of 193); uncovered 4,735 runs / 11,015 characters, none in a data table, none text;
no pieced block crosses a cell edge (0 of 400 in the 11 HTML routes). Tests 370; mutations of every condition on a changed line 157, 133 red (green: the
settings labels, the CLI's `settings or {}` guard, pre-existing operands of touched grader lines, two conditions of the block-extension loop, `b >= 0` in
`whole` (unreachable: a ≤ b), and the backward extension's cell check, whose forward twin is red — a case that reaches it alone is contrived; a 20-character
match across a cell edge is accepted as the match's own evidence, stated).

**The control sample (§FABLE_CONTROL: 35 HTML documents, 6 XML; first conversion 58 of 65 cells, 34 of 35 blocks + 1 approximate, 18 of 18 XML values), its seven
failing cells read against the originals, four classes:**
1. *A table continued over a page break* (elf ×2): the second `<table>` carries the same heading and lead-in; the grader's title rule counted the first part as
   "another table between". `continued()`: an intervening table whose header row repeats the target's is the same table's earlier part; a table unit with no
   cells counts for nothing. A grading defect: the output was the page's.
2. *A table unit with no cells* (shak): 764 such units in the 60 development files (spacer tables), one standing between a title and its table. The adapter
   emits no table unit without a cell with text.
3. *A corner of several stub columns* (indi ×2): the key writes it as its pieces (`Name | Type of Benefit`); `corner_text` now takes the pieces like
   `row_label` does.
4. *A row label carried down a block* (indi): a stub cell printed once for several rows, no rowspan; `carried()`: a stub above the row still labels it when
   nothing stands in its columns in any row between. Both with the key's anchors and by text.
Not changed, stated: mur T05 (a header with its footnote marks "2,3" and a unit line "(in thousands)" the record does not own: the grader's E13 rule and the
record, not the route) and twst T02 (a "%" column the key reads as 2025's while the printed "2025" header spans only the amount columns: the key reads past
the printed header). **Control after: 63 of 65 cells, 34 of 35 blocks + 1 approximate, 18 of 18.** These control documents are regression cases now; the
held-out set is the untouched exam. Development: no target lost.

## 52. Codex's gate of §51 (`CODEX_COVERAGE_R2_VERDICT.md`): five changes, each at its owner (2026-10-06)

**C1 — the tool's heading reading, fixed at its boundary; the inline-XBRL wrappers stay.** §51 left every `ix:` tag out of what the tool reads. Codex: a
wrapper may carry presentation (`<ix:nonFraction style="display:block">10</ix:nonFraction>20` breaks the line in the browser) and that removal did not
depend on the scanner's certainty — true; §51's wording was wrong on that point. The cause of the lost cover facts was never the wrappers but the tool's
reading of a block it takes for a heading: `DocumentBuilder._get_element_text` reads a block only to its first child element, and a HeadingNode is terminal.
`whole_headings()` (the adapter, applied where the tool is imported) re-reads such a block as the tool reads an `<h1>` — every descendant's text, stripped
and space-joined — for **block** elements only: an inline run the tool takes for a heading (a bold `<font>` inside a sentence) is already read whole with its
white space, and re-read as a block it lost the space before it (a first version: 331 words glued in the 60 files' legal exhibits, best-route boundary flags
18 → 349). The wrappers are given to the tool as written. Measured against §51's candidate: the two cover facts stay (`Commission File Number 001-35672`,
`For the quarterly period ended December 28, 2024`, one heading each in the file; in a bare synthetic case the tool takes the fact itself for a heading —
its case-sensitive skip list does not match the lower-cased tag — and the two parts stand as two units; stated), `bundle-020 T01`'s `kind` row is back to pass (the removal had caused it), 0 target flips.
The empty-anchor removal stays, on a smaller footing than §50 gave it: with the heading fix in place the anchors' own effect, measured by leaving them in
(`cand_r3c`), is one file of 60 — the tool breaks the heading's word around an anchor inside it (`Be<a id><!--Anchor--></a>rry` → `Be` / `rry`, 2 base-route
flags the screen step joins); 71 files read identically. A first reading of the 331 glued words as the anchors' doing was wrong: they were the inline
re-read above. The tool itself glues `Total <ix:nonFraction
style="display:block">10</ix:nonFraction>20` into `1020` with or without the wrapper (it holds the tag inline whatever its style): the boundary gate reports
it; not ours to fix here.

**C2 — a chained block keeps a cell only whole.** `piece()` checked its first seed and the extensions, not a later 20-character seed: `10.82 million for
reporting period` was read from `10.1 | 0.82 million …` with `inserted_chars` 0 (Codex's reproduction; the same hole §51 had stated). A block over several
cells now loses the part of a cell at either end (the `cell`/`edge` indexes already built; Codex's tested substitution): the `1` becomes the tool's own
character, the whole cell stays. Refusing every seed across an edge was tried and rejected (by both of us): it lost the valid flattened `$341 | $408` table.
0 such blocks in the 60 files (§51), so no development record moves.

**C3 — a continued table is excused only where the source order agrees.** `continued()` alone let a title listed before an unrelated table with the same
header row pass. The excuse now also requires the title's source place before the intervening table and that table's before the target (`source_before`,
as the lead-in check reads order). The page-break continuation keeps passing; the displaced title fails `placement`.

**C4 — a table with no text cell but a caption is its caption.** `to_units` dropped it with the spacer tables; it is a `caption` unit now, linked like any text.

**C5 — grouped marks and the record's own unit phrase compose.** `same()` allowed `Programs2,3` (marks glued) and `Programs (in thousands)` (an owned unit
phrase) each alone; together they failed. `without_marks(own_bracket_off(got, own), want, markers)` → `unit_phrase_split`; an undeclared unit, an unknown
mark, extra words or a changed number still fail. Murphy T05 needs, besides, its printed `(in thousands)` declared as anchored table-header context in the
**next** key package (bytes [1214178, 1214192) of its original; package 3 stays frozen): not done here.

**Staged for the key record, not changed:** twst T02 — the printed `2025` header spans the amount column, not the `%` column beside it; the key reads `2025`
as the `%` cell's period. The question for the record: is that an interpreted year association, outside the printed-span rule the T1 check tests? Until
dispositioned the failure stays visible; the year is not removed from the output, no header is stretched, no issuer exception.

Tests 374 (+4: the chain and its two mirrors — a block ending inside a cell, a seed over two cell ends —, the displaced title and a same-header table listed
between but placed after, the caption, the composition; `tests/test_whole_headings.py`, under the tool's environment, covers the block heading, the inline run
kept whole with its space, the anchor and the `<h2>` controls; skipped without the tool).

## 53. Codex's gate of §52 (`CODEX_COVERAGE_R3_VERDICT.md`): the anchors stay, the heading is read at the tool's own construction; the exam runner (2026-10-06)

**A — the empty-anchor removal is withdrawn; the heading fix moves to its cause.** Codex: an empty `<a>` can be laid out as a block (`style="display:block"`,
a stylesheet) and break the line — removed, `10` / `20` glued into `1020`; and §52's "one file, one broken word" was incomplete: with the anchors left in,
**seven section headings** of that file (Items 2, 3, 4; Part II Items 1, 1A, 2, 5) became ordinary text. Both reproduced. The cause: for a block whose text
begins after an element holding nothing (`<div><a id="Item3"><!--Anchor--></a>Item 3. …</div>`), the tool's detector recognises the heading, its node factory
reads the block's direct text, finds none, and falls through to a paragraph; §52's `whole_headings` acted only after a `HeadingNode` existed. Now the tool's
own `<h1>` reader is applied at two moments, both the tool's own decisions: **(a)** as the tool reads the block it is deciding on — only a block of inline runs
(its own `_is_text_only_container`), laid out as a block, not a table or list part, no table or picture inside, **and only where its text begins after an
element holding nothing**; **(b)** a heading the tool made from a block's leading text, read whole after the fact (as §52), again not where a table or picture
stands inside. An inline run the tool takes for a heading and a block laid out inline keep the tool's reading.

Measured on the 95 development + control originals against §52's candidate (`prepare_work/coverage_20261005/r3/ACCOUNT_r6.txt`, every unit by kind and text):
**71 of 72 development files and all 41 control files identical**; in `form10q` the seven headings are headings again and the four company-name lines carry
the tool's break at the anchor inside the word (`Be` / `rry`; 2 base-route boundary flags, joined by the screen step: best route unchanged at 18). Tables
10,162 = 10,162, pictures 615 = 615, cells equal; 0 target flips in the three EdgarTools routes; control 63 of 65, structure counts unchanged.

**A wider rule, measured and not taken:** (a) without its "text begins after an element holding nothing" condition honours the tool's detector on every
bold block made of runs (`<div><font>Aflac Japan</font></div>`): 3,723 text units of the 60 files and 1,355 of the control become headings, `heading_recognised`
35 → 48 of 178 and 32 → 45 of 90, `kind` 18 → 19 of 35 — and 2 base-route targets flip in the letter-spaced file (the screen step repairs them), best-route
boundary flags 18 → 30, "Table of Contents" page-top links and "See accompanying Notes…" lines become headings. The tool's own decisions, a larger change to
what the reader is told is a heading: a separate decision (`r3/build_r5`, `ctl_r5`, `ACCOUNT_r5.txt`), not this one. A first wide version without the
table-part guard had read table rows as headings (542 tables lost in 60 files): caught by the unit accounting, never a candidate.

Stated: the tool breaks a word at an inline empty anchor (`Be` / `rry`); the stylesheet-driven block anchor reads `10` / `20` in the tool whatever the
stylesheet says (it holds `a` inline), which here agrees with the browser; the tool's own terminal heading over a block that holds a table (`Totals` over a
one-row table) swallows the table before and after — not made worse, not fixed. Chrome controls in `tests/test_whole_headings.py` (the tool's environment):
the leading anchor, the anchor after the number, the cover line after a short bold block, the block anchor's break kept, `Revenue` / `20` kept, the inline
underlined runs, a bold line wrapped in a run (stays text), a container of blocks (two units), empty blocks, a link with text, text between comments,
`<h2>`, the table and picture guards, idempotence. The flip-check's greens on the narrowing conditions of (a) are the population measurement above, not unit
cases: the detector's decision depends on the surrounding document, so a one-block case cannot make it fire.

**B — the exam runner** (`prepare_work/heldout_exam/run_heldout.sh`, Codex's four faults): the frozen copy now holds `benchmarks/__init__.py`,
`benchmarks/prepare/__init__.py`, the grader and `golden/PACKAGE.json`; each of the three interpreters must import the grader from inside the frozen copy
(the Chrome venv holds the live repository as an editable install — asserted) and `grade --help` must run there; the key is read from the frozen pointer,
checked against the pinned package and passed to every step; one atomic claim (`mkdir CLAIM`) after an offline preflight, a root holding any exam folder or
claim refuses; the installed tools' versions, Chromium's, and every frozen file's hash are recorded (`FROZEN.txt`); the counts come from the grader's own
aggregate (`summary.by_split_format[split]`). Smoke-tested in a separate root on the control split (the development sequence end to end: 63 of 65, 18 of
18, nonempty aggregate), with one and with two prior folders (refused), and with two simultaneous launches (one claim, one refusal). Settings label
`headings: detected blocks read whole`; `empty_anchors` gone — a raw parse saved under the old settings is not reused.

## 54. After the first held-out exam: the released set's failure classes, two fixes at their owners (2026-10-06)

The exam (`prepare_work/heldout_exam/exam_20261006_1340_ed79cbcc7`, commit `ed79cbcc7`, key package 3): HTML cells 50 PASS / 13 FAIL / 1 UNRESOLVED of
64, blocks 16 / 4 / 1 of 21, XML 3 of 3; its scores do not change and it is not rerun. The owner released its 24 documents for diagnosis
(`heldout_exam/RELEASE_20261006.md`) and a fresh untouched set was reserved first (`NEXT_EXAM_RESERVATION.md`: 30 documents, 28 unused issuers). The
inventory (`heldout_exam/diagnosis_20261006/FAILURE_INVENTORY.md`) accounts for every one of the 19 targets in twelve classes; two were defects of this code:

**The scanner withheld a redline's strikes (`anchor.decoration`).** A credit-agreement amendment writes its insertions `text-decoration: underline double
#0000ff` and `underline solid #ff0000`. The shorthand's colour was "a value this scanner does not evaluate" → UNKNOWN → `struck_certain` False for the file →
the formatting step wrote no `struck` → every struck field of five targets failed and 117 boundary flags stood. Now a colour that surely paints (`_SEEN`,
the test the longhand `text-decoration-color` already passes through) is set aside and the lines are read: no `line-through` means no strike whatever the
colour; `line-through red` is a strike that paints; `line-through transparent`, two colours, functions stay unknown (CSS Text Decoration 3: the shorthand is
`<line> || <style> || <color>`). One target FAIL → PASS, 16 field rows pass, the file's flags 117 → 1. The only file of the whole key with such a shorthand;
development and control unchanged. The earlier test line that fixed `line-through red` as "uncertain either way" is replaced: the design choice changed.

**`row_context` read a stacked header one cell at a time (grader).** A column headed `Filing` over `Date`: the key names it `Filing Date`; `header_path`
reads stacked cells joined, `row_context` did not. Now the column's header cells, top down, are also compared joined; one cell alone still counts; another
column's cell is never joined in. One target FAIL → PASS. A reproduced contract defect, versioned here; the exam's score stands.

The other ten classes: nine targets are the key's (a display anchor over the unit cell only — six; a space the record drops between struck and inserted
text — two; a unit line printed in a header cell the record does not own — one, Murphy's class; a period read across the printed span — one, Twist's class):
staged for the next key package, package 3 untouched. Five `section_path` misses are headings with no element of their own (lines between `<br>`s, a styled
span after breaks, a slide's text layer, a title inside a picture): the structure gap, unchanged. Notes and references: not built. One press release is
pictures only. One file is uncertain to the scanner, which records no reason: a diagnostic field is wanted for the corpus checks.

## 55. Every picture the source shows stands in the output (the OCR review's image-delivery gap, r12; 2026-10-06)

The OCR review (`ocr_real336_development_review_20261006/r12/FABLE_IMAGE_DELIVERY.md`) counted, in the 120 documents its pictures come from, **1,508
shown picture occurrences and 386 with no unit in the EdgarTools route — 385 inside table cells, one inline in a span**; reproduced (its `image_audit.py`
on `c02e5351e`). The cause is the tool's, before our dump: its table strategy reads a cell's text and does not descend into it for pictures, and a run it
handles as text only keeps no picture either — the 15 occurrences of the review's selected files are already absent from `root.walk()`'s ImageNodes.

Fixed at the adapter boundary, not in the tool's traversal: `with_every_picture(units, vis)` (called by `route_for` after linking) gives every shown
picture tag that no unit stands at a unit of its own from the scanner's inventory — `vis.pictures`, the same visibility state as the text: a hidden copy
gets none and lends no identity — with the tag's own name, an anchor on the tag, `from: source`, and inserted **before the first unit that starts after
the tag**: the tool's units keep their order, ids and content (proved below), a picture in a cell follows (or, in the table's first rows, precedes) the
table unit whose text starts at its first text cell, an inline picture follows its paragraph. The cell it stands in: the scanner's innermost cell span,
the table unit that holds a cell of the same source table, and the row and column of that unit's cell in the picture's own cell where there is one. The
same bytes shown twice are two occurrences, two units; the OCR stream fills them by file name, one reading reused. Route settings record `pictures:
every shown tag`; the tool's cached parse is unchanged (its settings are not touched).

Measured (`prepare_work/image_delivery_20261006/`):
| | OCR review's 120 documents | the key's 116 HTML documents (development, control, released held-out) |
|---|---:|---:|
| shown picture occurrences | 1,508 | 1,529 |
| … standing at the tool's own unit | 1,122 | 1,312 |
| … added from the source | **386** (385 in cells) | **217** (208 in cells) |
| … in cells tied to their table unit / to a route cell | 332 / 23 | 205 / 18 |
| tool picture units with no place (double-count risk) | 0 | 0 |
| every shown tag exactly once | 120 of 120 | 116 of 116 |
| the committed units (ids, kinds, texts, anchors, order) changed | 0 documents | 0 documents |
The review's own audit on the candidate: **1,508 of 1,508 delivered, 0 missing** (was 386); its 15 selected missing occurrences delivered. The OCR
handoff consumer rerun on the review's five cases against routes made by this adapter: **6 occurrences, 0 delivery failures** (was 5 and AMG's chart);
the repeated bytes in two documents still read once and placed twice with two contexts.

Stated: a picture keeps the tool's reading order around it, so a logo in a table's first row stands before the table unit and a picture beside a value
after it — the cell span says where it is; a tool picture unit naming a hidden tag stays unplaced as before (none in the 236 documents). Tests 379 (the
picture-name helper now checks the completion on every one of its cases; `tests/test_every_picture.py`: an image-only cell, a picture among a cell's
text, nested inline markup, a hidden copy, the same bytes shown twice, nested tables, the document's first cell, the tool's own units unchanged, nothing to add).

## 56. Codex's independent review of §54 (`CODEX_HELDOUT_R1_VERDICT.md`): his tested patch, integrated onto §55; my counts corrected (2026-10-06)

Codex reviewed `c02e5351e` independently and found two of its rules unsafe; his tested patch (`prepare_work/heldout_independent_20261006/CODEX_CANDIDATE.patch`,
against `c02e5351e`) is applied here unchanged for `anchor.py`, `grade.py`, `adapters/screen_grid.py` and his two test files, and merged by hand into the
§55 adapter (`split_lines` after linking, before `with_every_picture`; his inline-fact reading inside `whole_headings`). Each finding was reproduced first:
- **`anchor.decoration`**: my §54 rule set aside any word `_SEEN` accepts — any lower-case word — so `line-through garbage`, which Chrome drops as a whole,
  was certified as a strike, and `none garbage` could cancel a real `<s>` (checked in Chrome: `line-through garbage` paints no line). Now only one valid
  opaque hex colour is set aside; names stay unevaluated (no colour-name list). Added here: hex digits in either case (`#ABC`, which Chrome strikes).
- **`Grader.row_context`**: my stacked-header join could borrow a header word from a body row; the single-cell branch had the same weakness. Now header
  cells must lie on the field's declared support, in source and table order, and the cancellation check reads the header and value that matched. His three
  tests fail on `c02e5351e`, pass here.
- **`Grader.value` / the period group**: a unit letter in the next column, anchored by the record as its own unit (`0.9` | `x`), joins without a space
  (reflow); a period sharing its cell with the record's own anchored measure is that period's heading, not a competing group (EEFT's 2023 stays).
- **`struck_kept`, `basis`, `anchors_of`**: exact struck places are used when they equal the source's and the claimed struck text; a basis phrase's
  association is proved at its governing occurrence, preservation still at every listed one.
- **The adapter**: `split_lines` splits a unit at source-certified `<br>` breaks only (certain reading, text equal to the source run, no tables, pictures,
  links or referenced units; strikes and joins re-read downstream) — three section boundaries were hidden in one unit; no text becomes a heading. And the
  tool's reading of an inline-XBRL text fact (`ix:nonNumeric`, `ix:continuation`) holding inline children reads them whole: **two cybersecurity paragraphs
  of the SPG 10-K (778 characters) were lost** (reproduced; recovered); a fact holding blocks, tables, pictures or links keeps the tool's traversal.
- **The screen step and `Grader.adjacent`**: in an uncertain file only, each unit's first and last character is measured in the render already made
  (`endpoints_of`, `screen_endpoints`); `screen_boundary` takes visible boxes apart on one line, or on different lines, as proof of separation — touching,
  hidden, transparent or impossible boxes prove nothing. Added here: `measure()` aborts every request of its page itself (the harnesses did it so far;
  the exam runner called the step directly — no document in the key or the corpus sample holds an absolute URL a page would load, 0 requests seen).
- **`grade_structure`**: every declared `printed_text` alternative goes through the check: a picture target's text existed only in alternatives, and
  the empty field compared with the empty picture unit as zero error — **my §54 inventory called that block "WER > 0, no critical word lost"; it was an
  empty comparison** (now: 11 reference words missing, still approximate).

**My counts corrected.** The released set converted again by `c02e5351e` read **51/64 cells and 17/21 blocks**, not "50, unchanged as targets": AEP T02
passes — `heading_recognised` is informative, never a target gate (§54's handoff and the inventory said otherwise; the commit message of `c02e5351e` too).
And "85 % of real HTML documents uncertain" counted EDGAR's own XBRL viewer pages (`R1.htm`…: 19,480 of 22,833 HTML documents in the local sample, all
with scripts); the filer's own documents are 3,353, **3,328 (99.3 %) read with certainty**.

**Results (`prepare_work/heldout_r2_20261006/`):** the 11 saved Docling, PDF and XML routes and the 3 control routes regraded or rebuilt: 0 target, 0
field changes; development EdgarTools routes rebuilt: 0 target, 0 field changes (best route: one exhibit's 10 boundary flags gone; four base-route flags
the screen step joins); released set (24 documents, development evidence since §54): **frozen key 54/64 cells, blocks 18 / 2 / 1; with the ten reviewed
key corrections applied in memory 64/64 cells, blocks 18 pass, 2 fail, 1 approximate** (the three picture-related blocks) — Codex's figures exactly;
pictures: the OCR review's 120 documents still 1,508 of 1,508 at their own tag. The ten corrections go into the next key package through the decision log
and support builder; package 3 and the exam stay as they are.

**Package 4** (`FINAL_KEY_FOR_CODEX_20261006_1753`, built by `prepare_work/package4_20261006/package4_build.py`; manifest `554a41d6…`, key `3c6d68cf…`): the
ten corrections through the normal mechanisms, each checked against its original first (`check_corrections.py`: file hashes, the scanner's text at every
anchor — "0.9" + "x", "(in millions)", "Category" + "4.", the NXST cell "Third Amendment Effective Date Term B-5 Loans"): two `segment_or_basis` decisions
(`claude_decide.py`; exactly those two records changed, one item each), eight reviewed support declarations (`claude_support_map.py`: exactly those slots
moved, plus the two decided fields' own search support), the two changed records verified again and stamped (457 of 457 current), the R4 contract
declarations carried forward, the manifest last, `VERIFY_PACKAGE.py` clean, the overrides' own test 11/11. Graded with it, the released set gives the
in-memory replay's 1,335 rows exactly: 64/64 cells, blocks 18 / 2 / 1. The repository's pointer stays on package 3 until Codex's gate.

**The corpus check of the merged code** (`prepare_work/corpus_checks_20261006/`: the 1,016 local filings, 3,353 filer HTML documents, EDGAR's own pages
apart), against `f83117fbf`: cells, pictures (5,762 shown, 799 added, 0 unplaced), dishonest, inserted, duplicate ids and order breaks unchanged; uncovered
text 69,762 → 68,198 characters — four documents gain a paragraph lost inside a nested inline fact (SPG's 10-K, two 8-K/A amendment paragraphs, an RH
10-Q); unanchored units 3 → 2; units +1,127, diffed unit by unit on 59 documents: 189 splits at certified `<br>` (233 units → 551, kinds kept), 179 merges
(560 → 208: a sentence no longer broken at its inline facts — 44 of them had a false heading in the middle, "As of | March 31, 2023, | and …"), 18 kind
changes (note titles inside a text block now headings, cover-page facts now text), 7 text changes (the recoveries). Base-route word-boundary flags
2,315 → 2,285: 19 documents fewer (a line break the tool glued, "ARTICLE IDefinitions", now two lines), 13 more — the tool's inline reader space-joins the
parts of a fact by its own design (its preprocessor strips the white space next to tags): "S IGNIFICANT", "i n", "CO 2". The screen step joins them where
Chrome shows the two characters touching — except where the two boxes' tops differed: small capitals (a 10 pt "S" beside an 8 pt "IGNIFICANT") stayed apart,
15 in one 10-K.

**`screen_grid.join`: one baseline, not one box height.** Two characters stand on one line when their boxes' bottoms agree within a pixel; their tops may
differ, a smaller font on the same baseline. Measured in Chrome: small capitals 10/8 pt — tops 3 px apart, bottoms 1; a raised mark ($5¹) — bottoms
6.4 px apart; a lowered one (CO₂) — 2.7 px: both keep their space (a rule "one box inside the other" would have joined a small raised mark into "$51":
not taken). Key documents: 0 joins changed (development 140, control 6, released 77), every route byte-identical, 0 target and 0 field changes. Corpus
(every flagged document, formatting then the screen step, offline): 2,285 base flags in 168 documents → **131 after the screen step** (`f83117fbf`: 2,315 in 175 → 249; no document has more than before; joins 970 → 1,207; 0 errors, 0 requests) — 77 of the 118 fewer by the baseline join alone, 41 by the `<br>` split. The 131 left, each recorded at the gate (`boundary_detail.py`, `classify_flags.py`): 68 a space after the period of a number ("$0. 69": the period in a `<font>` of its own; the gap finder judges a space from its two characters only, so it never measures these — a separate, older class), 45 a list glyph the source glues to its item ("oThe": the tool's space is the reader's), 13 a space the source shows that the tool lost (older), 3 a raised mark kept apart, 2 other. Tests: the old rule's "another top" case now joins; a Chrome case
with small capitals, a raised and a lowered mark (two failures under the old rule).

## 58. The screen step measures a space beside a number's own separator (2026-10-06; the corpus's remaining flags, §56)

Of the 131 word-boundary flags the corpus kept after the screen step, 68 (17 documents) were one class: a space the tool printed beside the period or
comma inside a number — "$0. 69" for "$0.69", the period set in a `<font>` of its own. `tool_spaces` judged a space from its two characters alone:
"." and "6" look like reflow at punctuation, so the screen step never measured it, while the gate's tokens read "0.69" as one number and flagged it.
Now each side is read with the neighbour the source prints touching it (no white space between, by the scanner's own text positions): a space is
measured when it cuts a token of that window as the gate's tokens read it, or when its two characters are a word's or a number's, as before — nothing
measured before stops being measured. Chrome still decides every join (one baseline, touching), so a separator the page sets apart — a list number
with a margin, "2. 4.650% Notes" — keeps its space. A first version read the neighbours across the source's white space ("57." and the "3" of the next
sentence as "57.3") and joined spaces before a sentence's period: harmless, but not this rule — not taken. Key documents: 0 target, 0 field changes,
the same joins (one more space measured in the released set, not joined). Corpus (the 168 flagged documents, formatting then the screen step, offline): flags left 131 → 75, no document worse; joins 1,207 → 1,288; 55 of the 68 joined; the 13 kept are a list number the page sets apart ("2. 4.650% Senior Notes") or a raised mark after a period ("2024.¹") — the reader's space. Tests: the finder on separators, a digit-letter pair and
reflow at punctuation; Chrome on the 10-K's own markup (joined) and a list number set apart (kept) — three failures under the old rule.

## 59. An inline-XBRL element that holds blocks is a container: a footnote's table stays a table (2026-10-06; Codex, after §56–§58)

The corpus's joined years and amounts ("Nine Months Ended October 31, 2025202420252024", "Pension and other benefits adjustments23 (24)95") had
one cause: EdgarTools lists `ix:footnote` among its "inline elements for simple values", so a footnote holding a `<div>` and a table was read as one
string — every cell's text run into the next. The tool already decides the right thing for the two sibling tags, `ix:nonNumeric` and
`ix:continuation`: holding a block (`div`, `p`, `table`, a block element), they are containers, and the tool's own traversal builds the table. That rule
now covers every inline-XBRL element the tool treats as an inline value (`whole_headings`' `creating`): a footnote of inline runs keeps the tool's own
inline reading. Measured: the whole local corpus (1,016 filings, 3,353 filer HTML documents) — exactly two documents change, the two with joined numbers: a text unit each becomes a table (+69 cells), boundary flags 2,285 → 2,283, every other gate unchanged; key documents (development, control, released; base, formatted and screened routes): 0 target, 0 field, 0 gate changes, one development route changed (a footnote holding a separator line and a note: two units now, "$ 17.1  million" — spacing E12 allows); tests 396 (393 without playwright); real-original variants 48/48; the new case fails under the tool as installed (`text`, not `table`).
