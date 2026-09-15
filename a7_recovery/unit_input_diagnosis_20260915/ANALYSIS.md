# A7 input diagnosis — the reader is not the failure

Owner-directed session, 2026-09-15. Core + owner. Four subscription calls total.
Nothing published was modified. No A7 artifact, key, score, grader or answer was touched.

---

## 1. The claim

**Every A7 error we were able to trace came from the INPUT or the SPEC, not from the
reader's judgment.** Flattened tables, rules the key applies but never states, and a
menu that disagrees with the key. We did not find a single error that required the
reader to be smarter.

Classifying P1's whole error table by cause (section 6a) puts **88.3% of the real error
mass** on input/spec defects or on grading that never finished, and leaves **11.7%**
in a "reader judgment, not yet traced" bucket that we did not examine — not one we
examined and attributed to the reader.

The working hypothesis we are handing you: **with unambiguous inputs and the missing
rules written down, these errors are fixable.** It is stated as a hypothesis because
we tested 2 packets, not 165.

Two supporting claims, both measured:

- **The served text destroys 85.2% of table row boundaries.** The structure is intact
  in the original filing; it is lost between the filing and the prompt.
- **The grader answers the same question differently about 1 time in 5** (repeatability
  **0.8143**), so the score cannot resolve a change smaller than that noise.

---

## 2. What the A7 task actually is (correction to an earlier shared assumption)

Each packet is HEAD + one item slice. The item slice names ONE target and carries a
verbatim quote. The served rules say:

> The complete event is CONTEXT so you
> can interpret that target correctly; it is NOT a request to find other facts.
> Interpret that target only.

So `recall 0.7455` / 42 unmatched gold rows are **interpretation** outcomes, not
search failures. The reader is pointed at each claim.

Verify: `a7_recovery/unit_1983/run/launch/kfields_a1_<accession>.attempt1.js`,
constants `HEAD`, `ITEMS`, `PROMPT_SHA`. All 10 reconstructed prompts for the two
cached events hash-match their pinned `PROMPT_SHA` entries (10/10).

---

## 3. Measured: the served text loses table structure

`scripts/weld_production.py` -> `results/WELD_PRODUCTION.txt`

Compares each filing's original HTML grid against `ExtractedSectionContent.content`
in Neo4j (what the prompt is built from).

```
filings measured : 15   (15 distinct filers)
row labels       : 3751
boundary LOST    : 3196  (85.2%)
```

Per filing the loss runs 0.9% to 99.7%; 13 of 15 are above 88%.

Concrete instance, Best Buy `0000764478-25-000057`, Domestic Segment table — a section
heading and the next row's label are welded into one string with no separator:

```
served : ... 4.0 % 4.0 % Selected Online Revenue Data Total online revenue $ 2,823 ...
original HTML:
   r12  Selected Online Revenue Data            <- heading row, alone
   r13  Total online revenue | $ 2,823 | ...    <- data row
```

In that one table 6 of 12 row labels keep a `\n\n` separator and 6 do not, so no rule
keyed on line breaks can recover it. The information is gone before the reader sees it.

---

## 4. Measured: the structure is recoverable, cheaply

Original filing HTML is cached at
`scripts/driver_seed/relocate_probe/inline_html_cache/<accession>.htm`
(1,769 filings, 4.3 GB) — but **only 2 of the 33 events in the A7 key are present**
(`0000006201-26-000032`, `0000764478-25-000057`, covering 9 of 165 gold rows).

- `docling 2.66.0` is already installed in `/home/faisal/EventMarketDB/venv`.
  30 filings from 30 filers: **30/30 parsed, 0 failures, 2,237 tables, median 0.73 s**.
- `scripts/geom_ambiguity.py` -> `results/GEOMETRY.txt`. Across 25 filings /
  1,186 tables / **43,037 figures**, each figure's column is **forced by colspan
  geometry in 96.91%** of cases; **3.09%** fall under no header cell and are the only
  genuinely undecidable placements. Recommended handling: emit them flagged, never guessed.
- `scripts/two_parsers.py` -> `results/TWO_PARSERS.txt`. Two independent toolchains
  (lxml and docling) over the Best Buy Domestic Segment table produce **48 = 48
  identical facts**, so the recovered grid is verified, not asserted.

Also note: Neo4j already stores exact XBRL for the audited statements
(`FinancialStatementContent.value`, concept -> `{period:{startDate,endDate}, unitRef, value}`).
Domestic segment revenue `8878000000` is already there. It does **not** carry the MD&A-only
figures (`2823000000`, `8258000000`) and carries **no percentages** (searched `"pure"`,
`0.233` -> 0 rows).

---

## 5. The controlled test

Two real packets rebuilt with the table grid **added** to the served evidence
(original bytes untouched — removing the insertions returns the original byte-for-byte,
asserted in `scripts/repair_final.py`), plus one new rule `0a` explaining the grid
(`scripts/add_rule.py`). Original rules, original schema, scored against the real key.

Pre-send verification (`scripts/verify_all.py`, `scripts/verify_final.py`):
10/10 assembled prompts valid JSON · 10/10 item quotes still resolve in the source ·
0 original numbers lost · 18/18 grids equal a real HTML table exactly ·
9/9 gold answer values present.

Four calls, Sonnet, 2 packets x 2 runs. Raw outputs in `runs/`.

| packet | target | runs identical | fields correct vs key |
|---|---|---|---|
| `#048` | `revenue_mix` — quote was four bare percentages, no header | **yes** | 27 of 31, both runs |
| `#045` | `asset_impairment` | no (2 fields) | 8 of ~15 |

What the repair fixed, both runs:

- **Best Buy Health slice now found** (the original P2 omission that prompted this work).
- **One record emitted, not two** (the original duplicate-window error is gone).
- **`#048` column assignment correct**: 31.8 vs 31.4 read as the quarter, 32.1 vs 31.2
  as the nine months — from a quote that carried no header at all.

---

## 6. Every remaining mismatch traces to the exam, not the reader

`scripts/verify_defects.py` -> `results/DEFECTS.txt`

**D1 — the key applies a period-window rule the served rules never state.**
The gold note for `revenue_mix` says it closed the window with an inferred
`period_start_date: "2025-02-02"`. Searched the served rules:
`all-or-nothing` 0 · `all or nothing` 0 · `both dates` 0 · `start and end` 0 ·
`close the window` 0 · `requires both` 0.
This one rule accounts for `mismatch:period_end_date` 30 + `mismatch:period_start_date` 15 +
`park:PERIOD_UNRESOLVED` 19 in P1's error table.

**D2 — the menu offers two interchangeable tokens for one business part.**
The served menu contains **both** `segment:domestic` and `segment:domesticsegment`
(and both `segment:international` and `segment:internationalsegment`). The key uses
`segment:domestic`. Nothing in the served text distinguishes them.

**D3 — the menu and the key encode the same slice differently.**
```
menu shows  : unknown:us-gaap:ReportingUnitAxis__bestbuyhealth          (in the served prompt)
key expects : unknown:xbrlaxis_75732d676161703a5265706f7274696e67556e697441786973__bestbuyhealth
              hex decodes to "us-gaap:ReportingUnitAxis"                (NOT in the served prompt)
```
The served rule is: "(1) reuse a menu value when the meaning is the SAME — cite it as
the menu's reference token string, exactly as the menu shows it". The reader complied
and the key scores it wrong. Worth auditing how much of `mismatch:slice` 21 (P1) /
19 (P2) is this.

Also unresolved and never stated anywhere in the served rules: what a table dash
(`$ -`) means. Four independent readings all read it as 0 / prior_year; the key reads
it as "no stated number".

`driver_name` differences are lawful synonyms — counted as
`name_spelling_differences` (45/41/22) and never gated.

---

## 6a. Every P1 error family mapped to a cause

`A7_CORRECTED_SCORE.json` -> `results.P1.error_table`. 349 entries; 41 are
`abstention:diagnostic`, which the scorer charges to neither side, leaving **308 real**.
Every remaining code is classified — **nothing is unclassified**.

| cause | entries | share | status |
|---|---|---|---|
| D1 unstated period-window rule | 88 | 28.6% | **TRACED** — 0 hits for the rule in the served text |
| column / value placement (forced by grid geometry) | 71 | 23.1% | **TRACED** — 96.91% of figures column-forced once structure is restored |
| D4 unstated same-name / two-lane rejection | 44 | 14.3% | **TRACED** — rule is in the scorer, not in the served rules |
| D5 unstated dash / blank-cell meaning | 29 | 9.4% | **TRACED** — 0 hits; 4 independent readings all chose the same wrong reading |
| D2/D3 menu vs key (slice) | 22 | 7.1% | **TRACED** — duplicate tokens + hex/plain encoding split |
| grading never finished (48 verdicts missing) | 18 | 5.8% | **TRACED** — `wrong_lane` fires on UNANSWERED gold rows |
| reader judgment | 36 | 11.7% | **NOT EXAMINED** — mostly `measurement-OD-9` (21) |

**88.3% traced away from the reader. 0% examined and attributed to the reader.**

D4 detail, since it is the second-largest single code: `score_exp5_current.py:399`
`conflicting_driver_names()` rejects a NAME the reply gives two different `fact_type`s,
and rejection kills **every** fact bearing that name, not just the conflicting one. The
served rules say only "within YOUR answer, one meaning gets exactly ONE name" — the
converse. One slip can therefore cost several facts.

---

## 7. The grader is not repeatable

`a7_recovery/unit_2113_guidance_review/FINDINGS_2113.json` (sha256 `ecd8d9b1...`):

```
records asked more than once : 10        askings : 28
record x aspect cells        : 70
identical across askings     : 57
decided BOTH ways            : 1
decided once, unresolved elsewhere : 12
rate                         : 0.8143
```

One record (`operating_margin` / `record_matches_source` / `0000027904-26-000020`) was
ruled True, False and UNRESOLVED across three askings of the same question.

**Consequence:** any intervention whose effect is smaller than ~19% grader noise cannot
be measured by the current score. Recommend fixing grader repeatability before
re-measuring anything else.

Related and already recorded: the grader prompt ends with an output template whose
values are quoted (`"<true | false | null>"`); the model copied the quotes, the strict
parser refused them, and **93 attempts needed recovery** — prompt-induced, not model error.

---

## 8. Error-mass context (from the published score, unchanged)

`a7_recovery/unit_2020_codex_check/codex_final_score2174_a/A7_CORRECTED_SCORE.json`

P1 error_table totals 349 entries, of which **41 are `abstention:diagnostic`**, which the
scorer itself charges to neither side (`score_exp5_current.py` ~line 1074). Of the 308
remaining, grouping by family:

```
period / date family        88  (25.2%)   <- D1
driver-name rejection       44  (12.6%)
slice                       22  ( 6.3%)   <- D2, D3
```
In UNION the period family rises to 35.4% while name rejection falls to 1.3%.

---

## 9. What this does NOT claim

- **n is small.** 4 calls, 2 packets, one filing's two targets. This is a diagnosis,
  not a new measurement, and not a score.
- **Only 2 of the 33 key events have cached original HTML** (9 of 165 gold rows). The
  other 31 would need fetching from EDGAR (reachable, HTTP 200) before any full re-run.
- **The repair is not a pure input swap.** It adds ~8k chars of grid plus one new rule,
  so a re-run is "same key, same schema, better-structured evidence", not the original exam.
- **Run-to-run variance is still real**: `#045` differed between two identical calls on
  `driver_name` and `period_end_date` — and that second field is the difference between
  a usable record and a parked one.
- No claim that fixing D1-D3 produces a PASS. `confirmed_wrong_accepted` is 9/9/8 and any
  value above 0 is a definite fail on its own.

---

## 10. Reproduce

```bash
V=/home/faisal/EventMarketDB/venv/bin/python
U=/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_input_diagnosis_20260915
$V $U/scripts/weld_production.py     # 85.2% of row boundaries lost, 15 filers
$V $U/scripts/geom_ambiguity.py      # 96.91% of figures column-forced by geometry
$V $U/scripts/two_parsers.py         # lxml vs docling: 48 == 48
$V $U/scripts/verify_defects.py      # D1, D2, D3 against the served bytes
$V $U/scripts/verify_final.py        # 10/10 JSON, 10/10 quotes, 9/9 gold values
```

All 30 artifacts are hashed in `MANIFEST.txt` (sha256, first 16 hex).
