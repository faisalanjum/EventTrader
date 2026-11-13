# Notion instruction 01 · create the page "What Convert returns"

Written by Fable for the Opus agent, 10 Nov 2026. Owner approved the content.

## What to do

1. Create one new page under `1 · Prepare` (id `3eca0a3f310681ffb36de687666c09f0`).
   - Title: `What Convert returns`
   - Icon: 🟡
   - Full width.
2. Fill it with the content in "Page content" below, in that order.
3. On `1 · Prepare`, in the parts table, row `B · Convert`, column `Job`: add a link to the new page at the end of the cell, written `→ What Convert returns`.

## Rules

- Change nothing else on `1 · Prepare` or on any other page.
- Add no words, pictures or sections beyond what is written here.
- If something cannot be done as written (a colour, a highlighted cell), do the nearest simple thing and say so.
- Reply with: the new page's link, and a short list of anything you did differently.

## Colours

Colour the kind word the same way everywhere it appears on the page:

| Kind | Colour |
|---|---|
| text | blue |
| heading | purple |
| table | orange |
| image | pink |
| field | gray |

---

## Page content

← Back to (mention of `1 · Prepare`)

Each file of a filing comes back as a list of **units**, in page order. Every unit has a kind, an id, its content and its position in the original file.

All examples are real: AMG's press release for the first quarter of 2023 (8-K of 1 May 2023).

### The five kinds

Table with a header row:

| Kind | Example | Position |
|---|---|---|
| text | "Affiliated Managers Group, Inc. (NYSE: AMG) today reported its financial and operating results for the first quarter of 2023." | 6560–6689 |
| heading | "Company reports EPS of $3.47, Economic EPS of $4.18 in first quarter" | 3712–3780 |
| table | a grid of cells (see below) | 237002–242550 |
| image | the AMG logo, inside a table cell | 1067–1192 |
| field | "Entity Address, State or Province" (XML files only) | 1807–2141 |

Position = where the unit sits in its original file, counted from the start of the file.

### A table is a grid of cells

How it looks in the press release (table with no header row; make the cell `$ 79.5` bold and, if possible, give it a yellow background):

| | Three Months Ended | |
|---|---|---|
| (in millions) | 3/31/2022 | 3/31/2023 |
| Equity method earnings | $ 71.9 | **$ 79.5** |
| Equity method intangible amortization and impairments | (23.3) | (20.9) |
| Equity method income (net) | $ 48.6 | $ 58.6 |

- The marked number comes back as: row 3 · column 9 · "79.5" · position 239325–239329.
- The table has 81 cells: 17 hold something, 64 are empty spacing. Each "$" is its own cell.

### Units come in page order

The first seven units of the press release (table with a header row):

| # | Kind | Starts at | Content |
|---|---|---|---|
| 1 | image | 1067 | logo (inside the next table) |
| 2 | table | 1429 | 25 cells |
| 3 | text | 3086 | "AMG Reports Financial and Operating Results for the First" |
| 4 | heading | 3375 | "Quarter of 2023" |
| 5 | heading | 3712 | "Company reports EPS of $3.47, Economic EPS of $4.18 in first quarter" |
| 6 | image | 4522 | bullet (inside the next table) |
| 7 | table | 4857 | 18 cells |

Positions only go up. Checked on all 68 units.

### How many units

Main document only (table with a header row; make the last row bold):

| | Press release | 10-Q | 10-K |
|---|---|---|---|
| text | 39 | 232–516 | 1,143–1,311 |
| heading | 9 | 50–142 | 140–171 |
| table | 16 | 31–60 | 66–426 |
| image | 4 | 0–4 | 1–6 |
| all | 68 | 367–623 | 1,523–1,738 |

From 1 press release, 5 quarterly reports and 3 annual reports.

### Toggle: "One raw record per kind"

Inside the toggle, first this line:

`anchor` = position in the original file · `r`, `c` = row, column · `rs`, `cs` = rows, columns spanned · "…" = trimmed.

Then five JSON code blocks, each with its kind word (coloured) on the line above it.

text

```json
{"anchor": {"byte_end_exclusive": 6689, "byte_start": 6560},
 "id": "u6", "kind": "text", "paragraph": 1,
 "text": "Affiliated Managers Group, Inc. (NYSE: AMG) today reported its financial and operating results for the first quarter of 2023."}
```

heading

```json
{"anchor": {"byte_end_exclusive": 3780, "byte_start": 3712},
 "id": "u3", "kind": "heading", "level": 1, "native_heading": "…",
 "text": "Company reports EPS of $3.47, Economic EPS of $4.18 in first quarter"}
```

table (the table, then one of its cells)

```json
{"anchor": {"byte_end_exclusive": 242550, "byte_start": 237002},
 "caption": [], "cells": "… 81 cells …",
 "id": "t54", "kind": "table", "row_group_tags": ["table"],
 "source_table": {"claims": 1, "tag_start": 235951}}
```

```json
{"anchor": {"byte_end_exclusive": 239329, "byte_start": 239325},
 "borders": [["top", "1px", "solid", "rgb(0, 0, 0)"]],
 "c": 9, "cs": 1, "grid": "screen", "header": false, "header_guess": false,
 "r": 3, "row_group": 0, "rs": 1,
 "source": {"byte_end_exclusive": 239342, "byte_start": 239124},
 "tag": "td", "text": "79.5"}
```

image

```json
{"alt": "amglogoa78a.jpg",
 "anchor": {"byte_end_exclusive": 1192, "byte_start": 1067},
 "cell": {"byte_end_exclusive": 1198, "byte_start": 987, "c": 0, "cs": 3, "r": 1, "rs": 3, "table": "t0"},
 "from": "source", "id": "p1067", "input": "…",
 "kind": "image", "src": "amglogoa78a.jpg", "text": ""}
```

field

```json
{"anchor": {"byte_end_exclusive": 2141, "byte_start": 1807},
 "group": {"at": 208, "count": 1, "index": 1},
 "id": "f0", "kind": "field",
 "name": "{http://www.xbrl.org/2003/linkbase}label", "path": "…",
 "siblings": {"count": 65, "index": 1},
 "text": "Entity Address, State or Province"}
```
