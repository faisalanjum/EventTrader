# Unit-reuse empirical findings (2026-06-18)

> **⏫ UPDATE 2026-06-20:** the resolver is now the production-grade `unit_resolver.py` and the corpus
> follows the locked per-X-in-name rule (117 cases). Re-run: **hints-on 117/117 (unit+value+lint)**,
> independently/adversarially verified (real residual on subtype/scaling/count/lint; no fudged
> expectations; `€M→unknown` is the only true enum gap — safe under-merge). **One honest limit:** a
> bare-`$` price-like fact (dividend/EPS) with no `price_like` hint AND no per-share NAME defaults to
> `m_usd` label-only (dangerous), and the per-X lint can't see it (no `/`). → minimal 100%-reliable
> fix: make `money_mode_hint` (aggregate vs price_like) MANDATORY for every money fact, not best-effort.

**Question:** can a DriverUpdate borrow the EXACT guidance unit methodology, for ALL fact_types — possible? downsides?
**Method:** standalone `unit_extract.py` IMPORTS the real production `guidance_ids.py` (sha256-verified, zero re-implementation). Ran a 115-case cross-fact_type corpus. All numbers below were re-run by hand.

## The numbers (real runs)

| Path | Overall | metric | surprise | guidance | action_event |
|---|---|---|---|---|---|
| V1 `canonicalize_unit` (label-only) | 62/115 = **54%** | 21/48 | 14/20 | 17/25 | 10/22 |
| V2 resolver, **no hints** | 80/115 = **70%** | 26/48 | 19/20 | 21/25 | 14/22 |
| **V2 + correct kind hint (production path)** | **108/115 = 94%** | 42/48 = 88% | **20/20 = 100%** | 24/25 = 96% | **22/22 = 100%** |

- Run: `/usr/bin/python3 run_probe.py` (label-only) and `run_probe_hints.py` (hints-on).
- Import proof printed at runtime: `guidance_ids.__file__ = .../earnings-orchestrator/scripts/guidance_ids.py`.

## Verdict

**YES — borrowable for all 4 fact_types, via V2 + the producer supplying a coarse unit-kind hint** (the same contract guidance extraction already uses). The literal **V1 is too weak (54%)** — it can't read `$B`, `per share`, `2.5x`. V2-no-hints (70%) even **regresses vs V1 on 16 count cases** (returns `unknown` for `stores`/`employees`). The hint closes the gap to 94%.

## Correction (validated 2026-06-18) — physical-unit prices are NOT a dead end

My first pass called `$/barrel` → `unknown` (the 9-enum has no per-barrel slot). **That expectation was WRONG** — confirmed by re-running the real code:
- The Driver ontology puts the **denominator in the driver NAME**; the unit stays the **base** (`usd`) — exactly like EPS = `$/share` → `usd`.
- `fuel_cost_per_barrel` + `$/barrel` → **`usd`** (resolver already does it — the name's `per` token triggers price-like). `sales_per_square_foot` + `$/sq ft` → `usd`. Verified live.
- A name LACKING the denominator (`oil_price` + `$/barrel`) falls back to aggregate `m_usd` → **flag for rename** (or pass `money_mode_hint='price_like'`). Do **NOT** add a blanket `$/physical → unknown` guard.
- The lone `system_units` + `'x'` case was a **bad test expectation** (now removed).

Net: with the **denominator-in-name rule + the kind/money_mode hint**, there is **no irreducible physical-unit failure** for well-named drivers. Only truly unclassifiable units (no enum home at all) land in `unknown`.

## Two VALUE-layer traps (not unit-class; a unit-only check passes them silently)

1. `cents` on an aggregate-money driver → **ValueError, scaled_value=None** (crash/null).
2. glued `$1.5B` (no space) → silently **drops the ×1000 scale** (1.5 instead of 1500). Emit `$ B` / `billion`.

## What must change

- **Catalog-creation side: NO unit fields** — but the catalog still creates the **complete Driver class** (`driver_name` + `fact_type` + optional links). `fact_type` is value-free; units are a per-fact, producer-time concern. Naming rule that matters downstream: a **per-X driver must carry the denominator in the name** (`fuel_cost_per_barrel`, not `fuel_cost`; `... per share`, not `.../share` — slug turns `/`→`_`, killing the token). Flag per-X sources whose name lacks the denominator for rename.
- **DriverUpdate producer side:** (1) use **V2**, not V1; (2) **always emit `unit_kind_hint`** (+ `money_mode_hint` when money) — same contract guidance uses; (3) emit a **clean `unit_raw`** token, never a glued `$1.5B`; (4) never emit `cents` on aggregate money; (5) call the **shared `unit_resolver.py`** (below), which adds a denominator lint, glued-`$B` normalization, and explicit cents/pre-scaled error surfacing — all **without editing** production `guidance_ids.py`; (6) the calibration gate must assert **scaled value**, not just the unit string.

## Files

**Production-grade (the deliverable — validated 2026-06-18, all tests pass):**
- `unit_resolver.py` — the **shared** resolver for guidance AND driver. Imports the REAL `guidance_ids` (sha256 `2552309c…`), reproduces production V2 exactly (`_compute_v2`), self-locating (no hardcoded path), no fake IDs, surfaces errors, denominator lint, glued-`$B` fix. API: `resolve_unit(name, unit_raw, value, *, unit_kind_hint, money_mode_hint, quote, xbrl_qname, strict)` + `resolve_driverupdate_units(...)` (separate `level_*` / `change_*` calls). Run: `python3 unit_resolver.py` (prints provenance + smoke).
- `test_unit_resolver.py` — 25 cases asserting **unit AND value** + glued-fix + cents-surfaced + denominator-lint + level/change + **production-parity**. Run: `python3 test_unit_resolver.py` → **ALL PASS**.

**Probe (evidence only — NOT production; superseded by `unit_resolver.py`):**
- `unit_extract.py`, `cases.json`, `run_probe.py`, `run_probe_hints.py`, `RESULTS.md` — the exploratory 115-case probe (hardcoded path, fake IDs, silent recovery). Kept as the empirical evidence trail.
