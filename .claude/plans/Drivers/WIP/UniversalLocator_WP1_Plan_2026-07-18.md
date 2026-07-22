> ⛔ **SUPERSEDED-FOR-EXECUTION (2026-07-21):** The locked `UniversalLocator_Design_2026-07-18.md` is the BASE contract; `UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md` is the SOLE current execution amendment/work order (Phase 0-7; Batch B/C/D FROZEN). Reading order: locked Design v5.5 base (unchanged rules) -> FinalPlan (changes + current steps) -> Review Record (history). This file is history/evidence only — follow no execution instruction in it.

# WP1 Implementation Plan v2 — Exactness + Fresh Measurement (round-11 revisions folded; GO given)

**Parent:** the LOCKED Universal Locator design v5.5 (commit `ba0c629`). Scope = WP1 only.
**Hard no-list:** no prompts · no tokens · no new framework · no Core work · no locator build (WP2).
**Gates after every step:** full battery + `relocate_probe/regress.py` 28/28 + probe 13/13.
**Commit discipline (round 11):** failing tests stay UNCOMMITTED; tests + fixes land TOGETHER only
once Step 2 is green — main never carries a red battery (the core session shares it).

---

## Step 1 — RED battery (uncommitted until green)

In `scripts/driver_seed/` tests + the new utility's own tests:

| # | Case |
|---|---|
| 1 | labeled 38.3 / 86 / 0 resolve; generic ones abstain (3 already failing) |
| 2 | exact decimals: 2.34 never matches a 2.01 fact (tier1) nor rounds to "2" (xbrl_lane) |
| 3 | %-class guard: 86 (number) never accepts printed "86%" |
| 4 | no integer-rounded forms for fractionals: 2.34 never accepts "2%" (2.0 keeps "2%") |
| 5 | negatives/parentheses regression cover |
| 6 | **substring invariant: every emitted quote is an exact substring of a stored source text** — fixed at the producer (`link_lib.row_quote`/`scan_text` return raw slices; `_tidy` demoted to search-internal); joined table cells are AUDIT evidence only unless mapped back to one exact corpus slice |
| 7 | dates: normalize-once-by-known-format → exact equality; mixed-convention pair rejected; neighboring-period adversarial case |
| 8 | instant periods resolve (xbrl_lane) |
| 9 | **full concept qname incl. prefix: mismatch abstains** |
| 10 | **unit mismatch (USD vs shares) abstains** |
| 11 | zero findable when labeled; generic 0 abstains |

Done-bar: each new test FAILS first, for the right reason (watched).

## Step 2 — Smallest exact fixes

- New `driver/relocation/exact_numbers.py`: Decimal-exact forms + comparison; the one date decode
  (known-format normalize once → exact; unknown/mixed → abstain). Pure, no I/O, no channel imports.
- `link_lib.py`: `_tableforms` (no len≥3; decimal form; zero) · `value_forms` (zero; no
  integer-rounded fractional forms) · `value_ok` (%-vs-number class guard) · `exact_form` (zero) ·
  `tier1` (Decimal-exact compare; namespace-kept concept; unit compare) · **`row_quote`/`scan_text`
  emit raw corpus slices** (`_tidy` search-only).
- `relocate_probe/xbrl_lane.py`: Decimal-exact · instant branch · the date rule · full-qname + unit.
- `locate.py`: exact_cell rung emits a corpus-slice quote (cell data → audit field) or falls through.

Done-bar: battery green · regress 28/28 · probe 13/13 → **ONE commit: tests + fixes together.**

## Step 2b — Frozen before/after locator A/B (real regression; regress.py is not enough)

`regress.py` re-grades SAVED outputs — it never reruns the changed locator. Add a small pinned A/B
(a script, not a framework): run the deterministic resolve path (0 tokens) over a PINNED worklist
slice at the baseline commit and after the fixes; diff record-by-record via `item_id`.
Done-bar: every difference is attributable to a NAMED fix (new finds in the zero/small/decimal
bands, class-guard rejections); no unexplained losses. regress.py stays as the additional guard.

## Step 3 — Safe 8-K routing + full-accession text (before any regeneration)

- **Enumerate REAL 8-K accessions** for the ticker from the graph (no guessed date window even for
  candidates) → `resolve_quarter_info` each → keep ONLY `safety_action == AUTO_OK` **AND the
  returned `accession_periodic` exactly matching the selected 10-K/Q accession** (the exact join,
  not period arithmetic).
- A dropped/fail-closed 8-K is **NOT marked searched**: the company-period completeness stamp stays
  incomplete → value-absent rows stay PARKED (retryable), never terminal SKIP.
- For each ACCEPTED accession: fetch + deduplicate ALL stored sections, exhibits, and filing text.
- `item_id` carried through resolved / residual / abstain (one id, three paths).
- Tests: monkeypatched resolver (AUTO_OK+match kept · AUTO_OK+wrong-periodic dropped · FAIL_CLOSED
  dropped-and-parked · dedupe) + one live read-only smoke.

## Step 4 — Regenerate ONCE (0 tokens), fully pinned

Manifest BEFORE running (small file, committed with the results): exact tickers, periods, filing
IDs, the worklist slice hash, and the runnable command —
`venv/bin/python scripts/driver_seed/run_code_tier.py --tickers <pinned list> --tag <pinned tag>`
(`--tag` alone is invalid — it selects no work) → then `build_packets.py` on that tag.
Claim scope: **zero fabricated (`quote_source='xbrl_fact'`) records IN THE REGENERATED COHORT**;
older part1–4 artifacts are marked INVALID/stale, not "regenerated."

## Step 5 — Honest report (no precision/recall claims — those are WP4's)

- **Mechanical compliance** (not "precision"): value-token-in-quote = 100% of emitted records;
  quote-is-exact-source-substring = 100%.
- **Coverage counts** over three separately-reported bases (they differ): raw vendor rows ·
  unique (ticker, kpi, period) targets · emitted per-source records — split into
  resolved / residual / abstain(parked) / derived-skip, by source route and by value band
  (zero / small / decimal / other).
- True metric/period/unit precision and recall: explicitly deferred to WP4 certification.
- Deliverable: the manifest + report file (inputs, hashes, commands, counts).

**Tokens: 0. Return only at the completed WP1 gate or a named owner trigger** (regress floor
would drop · certified behavior beyond the mapped defects · anything touching D1–D14).
