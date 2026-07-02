# Step 4 — Isolated LLM Naming Proof — RESULTS (2026-06-20)

**Question:** can the LLM reader coin correct Driver names under the LOCKED naming
rules (Rules 0-8, `Consolidation/UnitExtraction.md`) — per-X in the NAME, no invented
bases, distinct per-X = distinct names — BEFORE we touch any production prompt?

**Method:** 3 fresh **blind** Opus readers (rules + quotes only; no answer key, no
grader, no catalog). Reader model = Opus 4.8 in-session (subscription; Fable
unavailable). Deterministic grader (`grade.py`) — self-validated first (perfect set →
GO 33/33; broken set → NO-GO, caught all 4 planted faults). Any flicker across the 3
runs = fail. Reader = the real `menu_build.js` contract (`driver_name` + evidence).

**Corpus (33):** 22 synthetic golden (every rule shape) + 5 real CAKE per-X quotes +
6 real CAKE no-per-X negatives.

## Result: GO — 100% across all 3 runs, no flicker

| Layer | Pass (all 3 readers) |
|---|---|
| golden | 22/22 = 100% |
| real per-X | 5/5 = 100% |
| real negatives (0 invented) | 6/6 = 100% |

- **Per-X in name:** `oil_price_per_barrel`, `..._per_tonne`, `..._per_mmbtu`, `..._per_pound`, `sales_per_square_foot`, `revenue_per_user`, `sales_per_location`, `sales_per_operating_week` — all readers.
- **Per-share (the Steps 1-3 danger):** `$0.50 per share` → `dividend_per_share`; `diluted/adjusted EPS` → `..._earnings_per_share`. Never a bare `dividend`/`eps`-less name.
- **Distinctness (Rule 3 / wrong-SAME_AS):** per_barrel ≠ per_tonne, brent ≠ wti — distinct names in every run.
- **No invented basis (Rule 6):** `average check` → `average_check` (NOT `..._per_check`); comps/traffic/menu-mix → no `_per_`.
- **fact_scope (Rule 0):** `First-quarter`/`April` comps → `comparable_sales` (period NOT in name).
- **Pure scale (Rule 5):** `$1.5 billion` → `revenue`; `60 basis points` → `operating_margin` (no unit/scale in name).
- Healthy independence: base wording varied (`oil_` vs `crude_oil_`, `sales_` vs `average_sales_`) but the per-X/qualifier RULE held every time.

## What this proves — and does NOT
- PROVES: the locked Rules 0-8, given to a blind Opus reader, produce correct per-X / qualifier names with 100% reliability on isolated naming decisions → **the prompt wording is sound and ready to wire into production.**
- Does NOT prove: full multi-driver CHUNK extraction (which-drivers-to-coin / dedup / skip-vague) — this isolates the NAMING decision only. Physical per-X is synthetic (no barrels in restaurant filings; rule is domain-neutral). Reader = Opus (re-validate if Fable returns).

## Files
- `corpus.json` (labeled) · `blind_quotes.json` (reader inputs, no labels) · `grade.py` (deterministic, ties into Steps 1-3 lint) · `reader_1.json` / `reader_2.json` / `reader_3.json` (the 3 blind runs).
- Run: `python3 grade.py --blind` then `python3 grade.py reader_1.json reader_2.json reader_3.json`.
