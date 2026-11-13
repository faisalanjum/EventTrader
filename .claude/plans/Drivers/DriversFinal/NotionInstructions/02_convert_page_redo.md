# Notion instruction 02 · redo the Convert page

Written by Fable for the Opus agent, 10 Nov 2026. It replaces instruction 01. The owner asked for: a direct link from the Prepare chart, start–end positions, and one clean picture of a whole document so that ways to slice it are obvious.

## What to do

**A. The page** https://app.notion.com/p/414a0a3f310681f78f6dc1c6bb42a118

1. Rename it from `What Convert returns` to `B · Convert`. Keep the icon 🟡 and full width.
2. Replace its content with "Page content" below, in that order.
3. Keep the existing toggle `One raw record per kind` and everything inside it unchanged, as the last block of the page.

**B. The page `1 · Prepare`** (id `3eca0a3f310681ffb36de687666c09f0`)

Make these four small edits in place. Do not replace the page content, so the chart stays in Preview mode.

1. Chart "The 5 parts": in box B change `<b>B · Convert</b>` to `<b>B · Convert ▸</b>`, and add this line at the end of the chart code:
   `click B "https://app.notion.com/p/414a0a3f310681f78f6dc1c6bb42a118" "B · Convert" _top`
2. The line under the chart: add ` · ▸ = opens its own page` at its end.
3. Parts table, row `B · Convert`: remove ` → What Convert returns` from the Job cell, and make the bold words `B · Convert` in the Part cell a link to the page.
4. The child-page block at the very bottom: move it into a new toggle titled `Part pages` (the same pattern as the `Step pages` toggle on Code Flow). The page must stay a child of `1 · Prepare`.

## Rules

- Change nothing else on any page.
- Add no words, pictures or sections beyond what is written here.
- If something cannot be done as written, do the nearest simple thing and say so.
- Reply with: what you did, and a short list of anything you did differently.

## Colours

- The kind word, wherever it appears in a Kind column: text blue · heading purple · table orange · image pink · field gray.
- In the strip table, give each row a light background by kind: heading purple · table orange · image pink · text none. If a row cannot be coloured, colour its Kind cell.

---

## Page content

← Back to (mention of `1 · Prepare`)

**Job:** turn each file of a filing into units that point back to their place in the original.

**Status:** 🟡 built and tested; not switched on.

### How it fits together

Code block, plain text:

```
1 filing   (AMG 8-K, 1 May 2023)
└─ 9 files
   ├─ press release        68 units    39 text · 9 heading · 16 table · 4 image
   ├─ main 8-K page        44 units    24 text · 9 heading · 11 table
   ├─ SEC summary page     55 units    55 table
   └─ 6 XML files         152 units    152 field

a unit  ─▶  a table holds cells  ─▶  a cell can hold an image
```

### The kinds of unit

Table with a header row:

| Kind | What it is | What ties it to other units |
|---|---|---|
| text | a run of words | `paragraph`: units with the same number were one paragraph |
| heading | words the tool guessed to be a heading | `level` (a guess) · `paragraph` |
| table | a grid of cells | every cell has its row, column and span |
| image | a picture | the table cell that holds it |
| field | one value in an XML file | its path inside the file |

Every unit also has an id and its position (start–end) in the original file.

### One whole document, unit by unit

The press release, top to bottom. The bar shows size. A table's position runs from its start tag to its last cell.

Table with a header row (68 rows; keep every row, in this order; the rows with no number are pictures listed under the table that holds them):

| # | Kind | Position | Size | Content |
|---|---|---|---|---|
| 1 | table | 400–2,923 | ▮ 3 of 25 cells | Exhibit 99.1 · Investor Relations: Media Relations: · Patricia Figueroa Ann I… |
|  | image | 1,067–1,192 |  | ↳ picture inside this table |
| 2 | text | 3,086–3,143 | ▮ 9 words | AMG Reports Financial and Operating Results for the First *(same paragraph as #3)* |
| 3 | heading | 3,375–3,390 | ▮ 3 words | Quarter of 2023 *(same paragraph as #2)* |
| 4 | heading | 3,712–3,780 | ▮▮ 12 words | Company reports EPS of $3.47, Economic EPS of $4.18 in first quarter |
| 5 | table | 3,957–6,205 | ▮ 3 of 18 cells | Net Income (controlling interest) of $135 million, Economic Net Income of $15… |
|  | image | 4,522–4,637 |  | ↳ picture inside this table |
|  | image | 5,058–5,173 |  | ↳ picture inside this table |
|  | image | 5,580–5,695 |  | ↳ picture inside this table |
| 6 | heading | 6,398–6,443 | ▮ 8 words | WEST PALM BEACH, FL, May 1, 2023 — *(same paragraph as #7)* |
| 7 | text | 6,560–6,689 | ▮▮ 19 words | Affiliated Managers Group, Inc. (NYSE: AMG) today reported its financial and… *(same paragraph as #6)* |
| 8 | heading | 6,898–6,968 | ▮▮ 11 words | Jay C. Horgen, President and Chief Executive Officer of AMG, said: |
| 9 | text | 7,095–7,312 | ▮▮▮ 32 words | “AMG reported Economic Earnings per share of $4.18 for the first quarter, ref… |
| 10 | text | 7,467–8,076 | ▮▮▮ 76 words | “Macroeconomic uncertainty is creating additional opportunities for alpha-ori… |
| 11 | text | 8,231–8,756 | ▮▮▮ 75 words | “With thirty years of experience in partnering with independent firms, our re… |
| 12 | table | 8,802–28,679 | ▮▮▮ 41 of 268 cells | FINANCIAL HIGHLIGHTS · Three Months Ended · (in millions, except as noted and… |
| 13 | text | 29,126–29,435 | ▮▮▮ 42 words | For additional information on our Supplemental Performance Measures, includin… |
| 14 | text | 29,993–30,235 | ▮ 3 words | - 1 - |
| 15 | text | 30,563–30,581 | ▮ 2 words | Capital Management |
| 16 | text | 30,709–31,042 | ▮▮▮ 55 words | During the first quarter of 2023, the Company continued to execute on the sev… |
| 17 | text | 31,198–31,207 | ▮ 2 words | About AMG |
| 18 | text | 31,361–32,441 | ▮▮▮▮ 142 words | AMG is a leading partner to independent investment management firms globally.… |
| 19 | heading | 33,615–33,667 | ▮ 6 words | Conference Call, Replay and Presentation Information |
| 20 | text | 33,794–34,051 | ▮▮▮ 37 words | A conference call will be held with AMG’s management at 8:30 a.m. Eastern tim… |
| 21 | text | 34,206–34,650 | ▮▮▮ 64 words | The conference call will also be available for replay beginning approximately… |
| 22 | text | 34,858–34,881 | ▮ 3 words | Financial Tables Follow |
| 23 | text | 35,200–35,442 | ▮ 3 words | - 2 - |
| 24 | table | 35,772–36,934 | ▮ 1 of 16 cells | ASSETS UNDER MANAGEMENT - STATEMENT OF CHANGES (in billions) |
| 25 | table | 37,007–59,496 | ▮▮▮▮ 70 of 153 cells | BY STRATEGY - QUARTER TO DATE · Alternatives · Global Equities · U.S. Equitie… |
| 26 | table | 59,569–78,147 | ▮▮▮▮ 58 of 127 cells | BY CLIENT TYPE - QUARTER TO DATE · Institutional · Retail · High Net Worth ·… |
| 27 | text | 78,574–78,816 | ▮ 3 words | - 3 - |
| 28 | table | 79,146–79,967 | ▮ 1 of 16 cells | CONSOLIDATED STATEMENTS OF INCOME |
| 29 | table | 79,996–108,374 | ▮▮▮▮ 70 of 273 cells | Three Months Ended · (in millions, except per share data) · 3/31/2022 · 3/31/… |
| 30 | table | 108,462–109,485 | ▮ 1 of 16 cells | RECONCILIATIONS OF SUPPLEMENTAL PERFORMANCE MEASURES(2) |
| 31 | table | 109,540–132,275 | ▮▮▮▮ 59 of 204 cells | Three Months Ended · (in millions, except per share data) · 3/31/2022 · 3/31/… |
| 32 | text | 132,508–132,545 | ▮ 5 words | See Notes for additional information. |
| 33 | text | 132,810–133,052 | ▮ 3 words | - 4 - |
| 34 | table | 133,383–134,197 | ▮ 1 of 16 cells | CONSOLIDATED BALANCE SHEET |
| 35 | table | 134,226–170,155 | ▮▮▮▮▮ 92 of 357 cells | Period Ended · (in millions) · 12/31/2022 · 3/31/2023 · Assets · Cash and cas… |
| 36 | text | 172,171–172,413 | ▮ 3 words | - 5 - |
| 37 | text | 172,819–172,824 | ▮ 1 word | Notes |
| 38 | text | 173,023–173,179 | ▮▮ 21 words | (1) Earnings per share (diluted) adjusts for the dilutive effect of the poten… |
| 39 | text | 173,406–173,756 | ▮▮▮ 51 words | We assume the settlement of all of our Redeemable non-controlling interests u… |
| 40 | text | 173,981–174,775 | ▮▮▮▮ 114 words | We had junior convertible securities outstanding during the periods presented… |
| 41 | text | 175,018–175,165 | ▮▮ 22 words | The following table provides a reconciliation of the numerator and denominato… |
| 42 | table | 175,209–190,064 | ▮▮▮ 38 of 165 cells | Three Months Ended · (in millions) · 3/31/2022 · 3/31/2023 · Numerator · Net… |
| 43 | text | 190,318–191,799 | ▮▮▮▮ 208 words | (2) As supplemental information, we provide non-GAAP performance measures of… |
| 44 | table | 191,844–222,338 | ▮▮▮▮▮ 103 of 239 cells | Year Ended December 31, · Three Months Ended · (in millions) · 2020 · 2021 ·… |
| 45 | text | 222,518–222,734 | ▮▮ 30 words | See our Q1 2023 investor presentation accessed via AMG's website at https://i… |
| 46 | text | 223,001–223,243 | ▮ 3 words | - 6 - |
| 47 | heading | 223,596–223,613 | ▮ 2 words | Notes (continued) |
| 48 | text | 223,820–224,631 | ▮▮▮▮ 109 words | Adjusted EBITDA (controlling interest) represents our performance before our… |
| 49 | text | 224,812–225,831 | ▮▮▮▮ 139 words | Under our Economic net income (controlling interest) definition, we adjust Ne… |
| 50 | text | 226,042–227,101 | ▮▮▮▮ 156 words | Economic earnings per share represents Economic net income (controlling inter… |
| 51 | heading | 227,309–227,408 | ▮▮ 12 words | The following table provides a reconciliation of Average shares outstanding (… |
| 52 | table | 227,506–234,702 | ▮▮ 16 of 88 cells | Three Months Ended · (in millions) · 3/31/2022 · 3/31/2023 · Average shares o… |
| 53 | text | 234,920–235,308 | ▮▮▮ 57 words | These non-GAAP performance measures are provided in addition to, but not as a… |
| 54 | text | 235,507–235,700 | ▮▮ 23 words | (3) The following table presents equity method earnings and equity method int… |
| 55 | table | 235,951–242,869 | ▮▮ 17 of 81 cells | Three Months Ended · (in millions) · 3/31/2022 · 3/31/2023 · Equity method ea… |
| 56 | text | 243,105–243,631 | ▮▮▮ 78 words | (4) For the three months ended March 31, 2023, gains on ordinary shares of EQ… |
| 57 | heading | 243,892–243,936 | ▮ 5 words | Forward-Looking Statements and Other Matters |
| 58 | text | 244,081–245,301 | ▮▮▮▮ 127 words | Certain matters discussed in this press release may constitute forward-lookin… |
| 59 | text | 245,597–245,839 | ▮ 3 words | - 7 - |
| 60 | heading | 246,193–246,249 | ▮ 6 words | Forward-Looking Statements and Other Matters (continued) |
| 61 | text | 246,394–246,667 | ▮▮▮ 38 words | securities or financial markets or in general economic conditions, pandemics… |
| 62 | text | 246,813–247,831 | ▮▮▮▮ 152 words | management firms, uncertainties relating to closing of pending investments or… |
| 63 | text | 248,005–248,314 | ▮▮▮ 46 words | From time to time, AMG may use its website as a distribution channel of mater… |
| 64 | text | 248,743–248,985 | ▮ 3 words | - 8 - |

**What the strip shows**

- Page numbers split it into pages: #14, #23, #27, #33, #36, #46, #59, #64.
- A one-cell table sits right above the big tables: #24, #28, #30, #34.
- A sentence that introduces a table sits right above it: #41, #51, #54.
- Numbered notes start at #38, #43, #54, #56.
- One title came back as two units (#2, #3). One sentence runs across a page break (#58, then #61 and #62).
- "heading" is a guess: "Capital Management" (#15) came back as text, "The following table provides…" (#51) as a heading.

### Inside one table

Unit #54, the sentence just above the table (give this paragraph a blue background):

"(3) The following table presents equity method earnings and equity method intangible amortization and impairments, which in aggregate form Equity method income (net):"

Unit #55, the table (no header row). Colour these cells:
- yellow background and bold: `$ 79.5`
- blue background: `Three Months Ended`, `(in millions)`, `3/31/2023`, `Equity method earnings`

| | Three Months Ended | |
|---|---|---|
| (in millions) | 3/31/2022 | 3/31/2023 |
| Equity method earnings | $ 71.9 | **$ 79.5** |
| Equity method intangible amortization and impairments | (23.3) | (20.9) |
| Equity method income (net) | $ 48.6 | $ 58.6 |

- To read the yellow number you need everything in blue: its row label, the heads above it, and the sentence before the table.
- In the file this table is 7 rows × 27 columns: 81 cells, 17 filled, the rest empty spacing. Each "$" has its own cell. The yellow number is row 3, column 9, position 239,325–239,329.

### How big other filings are

Main document only (table with a header row; make the last row bold):

| | Press release | 10-Q | 10-K |
|---|---|---|---|
| text | 39 | 232–516 | 1,143–1,311 |
| heading | 9 | 50–142 | 140–171 |
| table | 16 | 31–60 | 66–426 |
| image | 4 | 0–4 | 1–6 |
| all | 68 | 367–623 | 1,523–1,738 |

From 1 press release, 5 quarterly reports and 3 annual reports.

(then the existing toggle `One raw record per kind`, unchanged)
