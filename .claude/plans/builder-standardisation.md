# Builder Standardisation Plan

**Created**: 2026-03-29
**Status**: DRAFT — verified against repo, decisions converged, pending approval before production code changes
**Scope**: 7 built `build_X()` functions for prediction-system-v2

---

## 0. Practicality Standard

This plan favors:

- Empirically validated correctness over aesthetic cleanup
- Adapter-first standardisation over invasive rewrites
- Reuse of proven fiscal logic over relocating code for neatness
- Deferring low-payoff churn when the last tiny accuracy gain would cost disproportionate risk

If we can get from "very likely correct" to "provably correct" with a small, testable change, we should do it. If the last tiny increment requires broad file moves, signature churn, or unproven abstractions, we should capture it as deferred rather than destabilize working builders.

---

## 1. Current State — Repo-Truth Inventory

| # | Function | File | Current signature | Return shape today | PIT input name | Accepts `quarter_info`? | Emits `source_mode`? | Main standardisation gap |
|---|----------|------|-------------------|--------------------|----------------|-------------------------|----------------------|--------------------------|
| 1 | `build_8k_packet` | `warmup_cache.py:463` | `(accession, ticker, out_path=None)` | **No packet return** (returns `None`) | N/A (accession is the anchor) | No | No | Calls `sys.exit(1)` on missing report; writes packet to disk but does not return it |
| 2 | `build_guidance_history` | `warmup_cache.py:707` | `(ticker, pit=None, out_path=None)` | **No packet return** (returns `None`) | `pit` | No | No | Writes JSON + prints rendered text, but does not return packet |
| 3 | `build_inter_quarter_context` | `warmup_cache.py:1472` | `(ticker, prev_8k_ts, context_cutoff_ts, out_path=None, context_cutoff_reason=None)` | **Returns tuple** `(out_path, rendered)` | Implicit (2 timestamps) | No | No | Packet written to disk; in-memory return contract differs from every other builder |
| 4 | `build_peer_earnings_snapshot` | `peer_earnings_snapshot.py:154` | `(ticker, pit_cutoff, window_start=None, top_n=5, out_path=None)` | Packet dict | `pit_cutoff` (required, positional) | No | No | Requires non-None cutoff even for live (would crash on `None`) |
| 5 | `build_macro_snapshot` | `macro_snapshot.py:384` | `(ticker, pit_cutoff, market_session=None, out_path=None, source='polygon')` | Packet dict | `pit_cutoff` (required, positional) | No | No (`source` only) | Requires non-None cutoff even for live (would crash on `None`) |
| 6 | `build_consensus` | `build_consensus.py:932` | `(ticker, quarter_info, as_of_ts=None, out_path=None)` | Packet dict | `as_of_ts` | Yes | Yes | Closest to target; `None` already means live |
| 7 | `build_prior_financials` | `build_prior_financials.py:1259` | `(ticker, quarter_info, as_of_ts=None, out_path=None, allow_yahoo=False)` | Packet dict | `as_of_ts` | Yes | Yes | Closest to target; `None` already means live |

### Immediate conclusions

1. The 7 builders are not equally "standardisation-ready". Builders #6 and #7 are close. Builders #1-#3 have broken return contracts (no dict, sys.exit, tuple). Builders #4-#5 require non-None timestamp even for live.
2. The most urgent standardisation issue is not function names. It is external contract consistency: call shape, return shape, side effects, and PIT parameter naming.
3. We should not move files first. File moves are optional cleanup, not a prerequisite for a safe orchestrator.
4. The 3 legacy builders in `warmup_cache.py` are entangled with local helpers, constants, and rendering functions. Extraction is surgery; wrappers are safe.
5. Fiscal logic should be centralized only where it is truly shared and already proven safe. We should not broaden Redis quarter-cache usage beyond `fiscal_year_end:{TICKER}.month_adj`.

---

## 2. Settled Design Decisions

### 2a. Naming convention: `pit_cutoff`

All references to `pit`, `pit_cutoff`, `as_of_ts`, `cutoff_ts`, `decision_ts` are unified to one name: **`pit_cutoff`**.

- External adapter API parameter: `pit_cutoff`
- Output packet field: `pit_cutoff`
- Internal legacy builders keep their native names; adapters translate.

### 2b. Live mode semantics: `pit_cutoff=None` means unrestricted

```
pit_cutoff: str | None = None

  None  → live mode, unrestricted (no PIT gate, all available data)
  str   → historical mode, PIT-gated (only data known by that timestamp)
```

**`source_mode` is derived, not passed as input:**
```python
source_mode = "historical" if pit_cutoff else "live"
```

Added to every output packet by the adapter. Not a parameter the orchestrator passes.

**Internal runtime anchors**: Builders #4 (peer) and #5 (macro) require a non-None timestamp — they'd crash on `None` (`fromisoformat(None)` → TypeError). When `pit_cutoff is None`, the adapter derives a runtime anchor:

```python
# Inside adapter, hidden from orchestrator
effective_cutoff = pit_cutoff or datetime.now(timezone.utc).isoformat()
```

This is an implementation detail of the adapter layer, not a design constraint. The orchestrator sees one clean API: `pit_cutoff=None` means live, period.

**Audit trail for temporal anchors**: When an adapter uses a temporal anchor for queries, it records that anchor in an `effective_cutoff_ts` field in the output packet. This is not universal — some builders don't use one:

| Builder | `effective_cutoff_ts` when live | `effective_cutoff_ts` when historical |
|---------|--------------------------------|--------------------------------------|
| 1. 8k_packet | `null` (accession-anchored, no temporal query) | `null` |
| 2. guidance_history | `null` (passes `pit=None`, no cutoff) | `pit_cutoff` |
| 3. inter_quarter_context | `filed_8k` (from `quarter_info`, used as window bound) | `pit_cutoff` |
| 4. peer_earnings_snapshot | derived `now()` | `pit_cutoff` |
| 5. macro_snapshot | derived `now()` | `pit_cutoff` |
| 6. consensus | `null` (passes `as_of_ts=None`, no cutoff) | `pit_cutoff` |
| 7. prior_financials | `null` (passes `as_of_ts=None`, no cutoff) | `pit_cutoff` |

The field means "actual temporal anchor used by this adapter, when one exists" — not a universal timestamp.

### 2c. Adapter-first, not extract-first

The safest standardisation path:

1. Keep underlying builder implementations where they are
2. Add thin adapters in `scripts/earnings/` with one normalized interface
3. Orchestrator calls only adapters
4. Refactor individual builders internally only after the adapter path is proven

This avoids mixing three kinds of risk in one shot: signature changes, file moves, logic changes.

### 2d. Wrapper-first for legacy builders

The 3 legacy builders in `warmup_cache.py` are importable (`if __name__ == '__main__'` guard exists at line 1953) but library-unfriendly:
- `build_8k_packet` calls `sys.exit(1)` and returns `None`
- `build_guidance_history` prints to stdout and returns `None`
- `build_inter_quarter_context` returns `(out_path, rendered)` tuple

Wrappers import from `warmup_cache.py`, call the legacy builder, read the packet from disk, normalize the return, and add `source_mode` + `pit_cutoff`. No logic copy, no file extraction.

Extraction deferred until: adapter path stable, tests exist, orchestrator integration done.

---

## 3. Phase 1 — Deep-Dive Review

**Goal**: line-by-line review of every builder and every shared dependency that can affect PIT safety, live behavior, and regression risk.

### 3a. Review checklist

For each of the 7 builders:

- [ ] Query correctness: every Neo4j/API query returns the intended slice, with no silent data loss from filters or joins
- [ ] Boundary correctness: all timestamp comparisons use the right inclusivity/exclusivity for the builder's purpose
- [ ] PIT safety: no future data leaks into historical mode
- [ ] Live behavior: no unnecessary historical restrictions are carried into live mode
- [ ] Return contract: importable builder returns a packet dict, not `None`, tuple, or process exit
- [ ] Side effects: printing/rendering/CLI concerns are separated from importable builder logic
- [ ] Error policy: critical failures raise or emit structured gaps; expected fallback failures may degrade gracefully but should not disappear silently
- [ ] Output schema: packet shape is stable and matches actual consumer needs
- [ ] Performance: no avoidable N+1 query patterns or repeated expensive lookups under parallel orchestration

### 3b. Builder-specific focus

| Builder | Special focus areas |
|---------|---------------------|
| 1. `build_8k_packet` | accession ownership check, fallback order (sections/exhibits/filing text), missing explicit return, `sys.exit(1)` inside builder body |
| 2. `build_guidance_history` | `gu.given_date <= pit` semantics, duplicate collapse rules, source-priority stability, printed text vs returned packet split |
| 3. `build_inter_quarter_context` | boundary exclusivity, `_build_forward_returns()` nulling logic, event ordering, replay-vs-rebuild semantics, tuple return |
| 4. `build_peer_earnings_snapshot` | peer scope and ranking, returns-schedule nulling, meaning of live cutoff, 45-day window practicality |
| 5. `build_macro_snapshot` | minute-bar PIT cutoff, session handling, VIX treatment, Benzinga subprocess dependence, weekend behavior, live source policy |
| 6. `build_consensus` | AV 3-source join, `_resolve_pub_ts()` same-day handling, live-only Yahoo fallback, provider-convention fiscal mapping, forward-estimate exclusion in historical |
| 7. `build_prior_financials` | XBRL/FSC layering, DEI vs `period_to_fiscal()` arbitration, denylist/proximity guard, Yahoo fallback constraints, backfill dependency, 52/53-week edge cases |

### 3c. Shared dependency review

These must be reviewed along with the 7 builders:

- `.claude/skills/earnings-orchestrator/scripts/fiscal_math.py`
- `scripts/sec_quarter_cache_loader.py`
- `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`
- `utils/market_session.py`
- any helper used by `macro_snapshot` for PIT headline fetches

---

## 4. Phase 2 — Validation Strategy

**Goal**: prove builder behavior with the lowest-risk test ladder, not just one giant integration script.

### 4a. Reality constraints

- It is Sunday, so we can validate many live code paths structurally, but not all market-open/session-sensitive behaviors empirically right now
- AlphaVantage free-tier budget is tight, so AV tests must be deliberately capped
- There is currently no dedicated regression suite for these 7 builders, so we should assume confidence is coming mostly from ad hoc usage plus design docs

### 4b. Test layers

#### Layer 1: Contract tests

No external calls beyond what is needed to import and execute against existing local infra.

Validate:

- importability
- current signature inventory
- actual return shape
- packet contains required fields
- adapters normalize legacy returns correctly
- no builder exits the process when called through the standardized path

#### Layer 2: Historical integration tests

Graph-backed tests on known quarters. These are the highest-value tests because PIT is the hardest failure mode.

Validate:

- historical packet is non-empty when coverage should exist
- same-day boundary handling
- before/after cutoff exclusion of known events
- amendments, guidance changes, and forward-return nulling
- fiscal labels on standard and 52/53-week companies

#### Layer 3: Differential PIT tests

For each selected quarter, run at least:

- `pit_cutoff = just before event`
- `pit_cutoff = exact event time`
- `pit_cutoff = just after event`

This is where most hidden leakage bugs show up.

#### Layer 4: External-source smoke tests

Minimal, deliberate calls only.

- `build_consensus`: cap AV to 1 historical smoke test and 1 live smoke test at most
- `build_macro_snapshot`: Yahoo live smoke is acceptable on Sunday for structural validation, but not enough to prove market-open behavior
- `build_prior_financials --allow-yahoo`: test only if needed for fallback behavior, not as the main correctness proof

#### Layer 5: Deferred market-hours live checks

Keep a short checklist for the next:

- pre-market window
- in-market window
- post-market earnings window

Some macro/market-session claims cannot be fully proven on a Sunday.

### 4c. Test ticker selection — LOCKED (from local Neo4j coverage scan)

| Ticker | Role | Why | Key properties |
|--------|------|-----|----------------|
| **FIVE** | Primary deep-validation | Strongest all-around: 39 reports, 11 XBRL, 468 GuidanceUpdates, 23/27 exhibit-rich 8-Ks, 15 industry peers | Jan FYE, quarter lengths 92/99 — good 52/53-week-style stress |
| **DOCU** | Rich standard path | Good "normal" control: 39 reports, 10 XBRL, 314 guidance updates, 19/27 exhibit-rich 8-Ks, 48 peers | Jan FYE, quarter lengths 90/91/93 |
| **CRM** | Sparse/no-guidance path | 0 guidance updates — validates graceful empty behavior. 36 reports, 11 XBRL, 23/25 exhibit-rich, 48 peers | Quarter lengths 90/91/93 |
| **COST** | Fiscal edge-case add-on | Non-standard fiscal calendar stress: Sep FYE, quarter lengths 85/113/120, only 4 peers, 0 guidance | 33 8-Ks with 28 exhibit-rich |

Notes from scan:
- MSFT absent or incomplete in local graph — avoid for builder testing
- 8-K graph schema uses `created`, `description`, `exhibit_contents`, `items` (not `filedAt`, `title`, `ex99_*`)

### 4d. Test harness recommendation

Build a harness, but keep it layered:

- `scripts/earnings/test_builder_contracts.py`
- `scripts/earnings/test_builder_integrations.py`

The harness should:

- write outputs under `/tmp/builder_validation/<timestamp>/`
- support `--allow-av`
- support `--allow-live-web`
- save before/after packet diffs for later standardisation validation

Do not rely on one monolithic script that tries to prove everything at once.

---

## 5. Phase 3 — Standardisation Strategy

**Goal**: normalize behavior with minimal regression risk.

### 5a. Function names

Current names are already good. **Do not rename anything.**

### 5b. Adapter contract

The orchestrator-facing adapter contract:

```python
def build_X(
    ticker: str,
    quarter_info: dict,
    pit_cutoff: str | None = None,
    out_path: str | None = None,
    **kwargs,
) -> dict:
    """
    pit_cutoff:
      None  → live mode, unrestricted
      str   → historical mode, PIT-gated

    Returns: packet dict with at minimum:
      - schema_version
      - ticker
      - pit_cutoff (echoed back, None for live)
      - effective_cutoff_ts (actual temporal anchor used by this adapter, when one exists — null for builders that don't use one)
      - source_mode ("live" or "historical", derived from pit_cutoff)
      - assembled_at (ISO8601)
    """
    ...
```

### 5c. `quarter_info` core fields

```python
{
    "accession_8k": str,        # the trigger filing
    "filed_8k": str,            # ISO8601 — when 8-K was filed
    "market_session": str,      # pre_market / in_market / post_market
    "period_of_report": str,    # YYYY-MM-DD — fiscal period end date
    "prev_8k_ts": str | None,   # ISO8601 — previous 8-K filing time
    "quarter_label": str | None, # e.g. "FY2026-Q1" (display only)
}
```

Notes:

- `quarter_label` is optional display metadata
- `prev_8k_ts` is optional at construction time, but required by the inter-quarter adapter
- `pit_cutoff` is a separate parameter, not inside `quarter_info`

### 5d. `out_path` collision rule

**Adapters must always pass orchestrator-owned unique output paths.** Current builder defaults use shared `/tmp` filenames keyed only by ticker or accession (e.g. `/tmp/earnings_guidance_{ticker}.json`), which collide under concurrent or overlapping runs.

The orchestrator generates a unique `run_id` per prediction and passes:
```python
out_path = f"/tmp/earnings/{run_id}/{builder_name}.json"
```

This eliminates race conditions between concurrent live predictions, overlapping historical backfills, and debugging runs.

### 5e. Adapter behavior per builder

| Builder | `pit_cutoff=None` (live) | `pit_cutoff=str` (historical) | Adapter mechanics |
|---------|--------------------------|-------------------------------|-------------------|
| 1. `build_8k_packet` | Ignored (accession IS the anchor) | Ignored (same) | Extract `accession_8k` from `quarter_info`. Call legacy builder. Catch `SystemExit` → raise `ValueError`. Load packet from `out_path`. Add `source_mode`, `pit_cutoff`. |
| 2. `build_guidance_history` | Pass `pit=None` to legacy | Pass `pit=pit_cutoff` | Call legacy builder. Load packet from `out_path`. Discard printed output. Add `source_mode`, `pit_cutoff`. |
| 3. `build_inter_quarter_context` | Pass `context_cutoff_ts=filed_8k` | Pass `context_cutoff_ts=pit_cutoff` | Extract `prev_8k_ts` + `filed_8k` from `quarter_info`. Call legacy builder. Discard rendered text. Load packet from `out_path`. Add `source_mode`, `pit_cutoff`. |
| 4. `build_peer_earnings_snapshot` | Derive `now()` as effective cutoff | Pass `pit_cutoff` directly | Call legacy builder with effective cutoff. Already returns packet dict. Add `source_mode`, `pit_cutoff` (original None, not derived). |
| 5. `build_macro_snapshot` | Derive `now()` as effective cutoff | Pass `pit_cutoff` directly | Call legacy builder with effective cutoff. Default source policy: `source='yahoo'` for live, `source='polygon'` for historical — overridable via `**kwargs`. Already returns packet dict. Add `source_mode`, `pit_cutoff`. |
| 6. `build_consensus` | Pass `as_of_ts=None` | Pass `as_of_ts=pit_cutoff` | Near-passthrough. Already returns packet dict with `source_mode`. Normalize `as_of_ts` → `pit_cutoff` in output. |
| 7. `build_prior_financials` | Pass `as_of_ts=None` | Pass `as_of_ts=pit_cutoff` | Near-passthrough. Already returns packet dict with `source_mode`. Normalize `as_of_ts` → `pit_cutoff` in output. |

**Key invariant**: The output packet always shows the ORIGINAL `pit_cutoff` value (`None` for live), never the derived runtime anchor. The derived anchor is an internal adapter detail.

### 5f. Native builder refactor order

Only after adapters and validation are green:

1. Make legacy builders return packet dicts directly
2. Remove `sys.exit()` from importable builder bodies
3. Separate rendering/CLI output from builder execution
4. Then consider native signature unification

Do **not** combine those with file extraction in the same change set.

### 5g. File-location policy

**Do not extract the 3 legacy builders out of `warmup_cache.py` yet.**

The legacy builders are entangled with local helpers and constants (`_fetch_8k_core`, `get_manager`, `QUERY_4G_META`, `QUERY_IQ_PRICES`, `_build_forward_returns`, `resolve_unit_groups`, etc.). Extraction means extracting or importing the entire dependency tree — that's surgery, not a simple file move.

Safer path:
- Thin wrappers in `scripts/earnings/` import from `warmup_cache.py`
- `warmup_cache.py` has `if __name__ == '__main__'` guard (line 1953) — importing is safe

Revisit extraction after: adapter path stable, tests exist, orchestrator integration done.

---

## 6. Shared Infrastructure

### 6a. What is worth centralizing now

Only centralize what is both:

- already duplicated
- already conceptually identical
- and low-risk to validate

**Best current candidate**:

- shared FYE month resolution helper used by `build_consensus` and `build_prior_financials`

### 6b. What should stay duplicated for now

Leave these alone unless testing proves the abstraction will help more than it hurts:

- JSON write helpers
- `assembled_at` helpers
- small envelope-building helpers
- per-builder Neo4j session setup

These are too small to justify shared abstractions right now.

### 6c. What should not be centralized yet

- moving `fiscal_math.py`
- extracting legacy builders from `warmup_cache.py`
- any shared "one-size-fits-all" temporal helper that blurs the differences between packet types

---

## 7. Fiscal Math Standardisation

This is the area where "reuse exactly what already works" matters most.

### 7a. Safe rule

From `sec_quarter_cache_loader.py`, builders may safely reuse:

- `fiscal_year_end:{TICKER}.month_adj`

Builders should **not** use for historical reconstruction:

- `fiscal_quarter:{TICKER}:{FY}:Q{N}`
- `fiscal_quarter_length:{TICKER}:Q{N}`

Reason:

- those are latest-state convenience caches
- historical builders need PIT-safe reconstruction
- `month_adj` is the one acceptable exception because fiscal year-end month is effectively static for our use case

### 7b. Canonical fiscal logic by builder

| Builder | What it actually needs |
|---------|------------------------|
| `build_consensus` | FYE month + `fiscal_math._compute_fiscal_dates()` and `period_to_fiscal()` for provider-convention mapping and Yahoo fallback |
| `build_prior_financials` | FYE month + DEI/XBRL identity + `period_to_fiscal()` fallback + denylist/proximity guard |
| Other 5 builders | no fiscal math standardisation work needed right now |

### 7c. Important non-goal

Do **not** force `build_consensus` to use the full `build_prior_financials` fiscal-identity stack unless testing proves it materially improves results.

Why:

- `build_consensus` is mapping provider data that already follows provider fiscal-date conventions
- `build_prior_financials` is reconstructing SEC filing identity under PIT constraints
- those are related but not identical problems

The right rule is:

- share the exact common pieces
- do not artificially unify logic that solves different data-shape problems

### 7d. Shared helper recommendation

Create a tiny shared helper only if it mirrors current behavior exactly:

```python
def get_fye_month(ticker: str, gaps: list) -> int | None:
    """
    Tiered: Redis month_adj -> sec_quarter_cache_loader.refresh_ticker() -> Yahoo lastFiscalYearEnd.
    No quarter-cache reads. No default-December guess.
    """
```

Important:

- no `fiscal_quarter:*` cache usage
- no `fiscal_quarter_length:*` cache usage
- no silent guess like "default to December"

If resolution fails, emit a gap exactly as the current builders do.

### 7e. `fiscal_math.py` location

**Do not move the canonical file yet.**

- Leave `.claude/skills/earnings-orchestrator/scripts/fiscal_math.py` as canonical
- If import convenience is needed, add a small repo-local shim or re-export module

Moving the file itself touches multiple consumers for little immediate payoff.

---

## 8. Documentation Updates

`prediction-system-v2.md` should be updated only after decisions are approved and implemented.

When that happens, update:

- builder inventory status
- the standard builder contract
- which builders are natively standardized vs adapter-standardized
- fiscal-math sharing decisions
- validation status and residual caveats

Do not mark the legacy builders as "fully standardized" until:

- return shapes are normalized
- importable builders no longer exit/print as part of normal operation
- validation evidence exists

---

## 9. Execution Order

```
Phase 1  forensic review         → findings, no production code changes
Phase 2  validation harness      → tests and evidence, still no production code changes
Phase 3  adapter standardisation → safe external contract first
Phase 4  native cleanup          → only after adapters/tests are solid
Phase 5  doc sync                → update prediction-system-v2.md and related docs
```

Each phase requires explicit approval before moving on to code changes.

---

## 10. Resolved Questions

| # | Question | Resolution |
|---|----------|------------|
| 1 | PIT parameter naming | **`pit_cutoff`** everywhere. Adapters translate to legacy names internally. |
| 2 | Live mode semantics | **`pit_cutoff=None` = unrestricted live**. Adapters derive runtime anchors for builders that need timestamps (4, 5). Derived anchor is internal — output packet shows `pit_cutoff: null`. |
| 3 | `source_mode` input vs derived | **Derived** from `pit_cutoff`. `"historical" if pit_cutoff else "live"`. Not an input parameter. |
| 4 | Adapter-first rollout | **Yes**. No extraction from `warmup_cache.py` until adapters + tests are solid. |
| 5 | Shared Redis reuse | **Only `fiscal_year_end:{TICKER}.month_adj`**. No quarter-cache reuse in historical builders. |
| 6 | `fiscal_math.py` location | **Stay in place**. Add shim only if needed for import convenience. |
| 7 | Legacy packet enrichment | **Yes** — adapters add `source_mode`, `pit_cutoff`, and `effective_cutoff_ts` on top of legacy packet output. |
| 8 | Validation targets | **LOCKED**: FIVE (primary), DOCU (standard), CRM (sparse/no-guidance), COST (fiscal edge). |
| 9 | Adapter function names | Same names `build_X` — adapters replace direct calls. |
| 10 | `quarter_info` shape | Orchestrator builds via `derive_quarter_from_accession()`. Fields: `accession_8k`, `filed_8k`, `market_session`, `period_of_report`, `prev_8k_ts`, `quarter_label`. |
| 11 | Parallel execution | `ThreadPoolExecutor(max_workers=9)`. All builders concurrent (~15-20s total). |
| 12 | `allow_yahoo` default | **`False`**. XBRL → FSC → gap is the default path. Override via kwarg when needed. |
| 13 | Historical `pit_cutoff` | Production orchestrator default: `= quarter_info["filed_8k"]`. Test harness may use other values (before/exact/after) for differential PIT validation. |
| 14 | Live `pit_cutoff` | Always `= None`. |
| 15 | Macro `source` default | `'yahoo'` for live, `'polygon'` for historical. Overridable via `**kwargs`. |
| 16 | `out_path` collision safety | Orchestrator passes unique paths: `/tmp/earnings/{run_id}/{builder_name}.json`. |
| 17 | `effective_cutoff_ts` | In output packet when a temporal anchor was used. `null` for builders that don't use one (8k_packet, guidance live, consensus live, prior_financials live). See §2b table for per-builder values. |

All questions resolved.

---

## 11. Phase 1 Findings (2026-03-29)

Line-by-line forensic review of all 7 builders + shared dependencies. Complete.

### 11a. Neo4j Timezone Inventory

| Field | Timezone | Format Example |
|-------|----------|----------------|
| `News.created` | America/New_York | `2026-03-26T10:09:16-04:00` |
| `Report.created` | America/New_York | `2025-02-26T16:03:55-05:00` |
| `returns_schedule` | America/New_York | `2026-03-26T11:09:16-04:00` |
| `GuidanceUpdate.given_date` | **UTC** | `2026-03-26T20:30:00Z` |

Eastern Time uses two offsets: `-05:00` (EST, Nov-Mar) and `-04:00` (EDT, Mar-Nov). This is correct. The guidance UTC mismatch is safe because builder #2 uses Neo4j `datetime()` comparison (timezone-aware), not string comparison.

### 11b. CRITICAL Findings (1)

**C1. Builder #3 (`inter_quarter_context`) — PIT nulling uses string comparison**
- **Location**: `warmup_cache.py` line 1181 — `if str(end_ts) > context_cutoff_ts:`
- **Risk**: If `end_ts` and `context_cutoff_ts` have different timezone offsets (e.g., `-04:00` vs `-05:00` across DST boundary, or UTC vs ET), the lexicographic string comparison gives wrong results. Could leak future returns into historical predictions.
- **Practical risk today**: LOW — both sides come from Neo4j in Eastern Time (100% of News/Report timestamps are ET, 0 UTC). The only danger is DST transition hours (~2 hours/year at 2 AM, when no earnings happen) or a non-standard caller passing UTC. Not an active leak today.
- **Fix**: Parse both timestamps as datetime objects before comparing. The `returns_schedule` already has exact end timestamps for each horizon — just needs proper datetime comparison instead of string comparison. ~5 lines of code. Trivial fix, eliminates theoretical risk entirely.

### 11c. HIGH Findings (5)

| # | Builder | Finding | Location |
|---|---------|---------|----------|
| H1 | #1 8k_packet | `sys.exit(1)` when accession/ticker not found | `warmup_cache.py:479` |
| H2 | #1 8k_packet | Returns `None` — no packet dict return | `warmup_cache.py:463-564` |
| H3 | #2 guidance_history | Returns `None` — no packet dict return | `warmup_cache.py:707-937` |
| H4 | #3 inter_quarter | Returns `(out_path, rendered)` tuple, not packet dict | `warmup_cache.py:1847` |
| H5 | #5 macro | Silent SPY data loss — all market metrics `None` with no warning flag in packet | `macro_snapshot.py:408-423` |

H2-H4 are already handled by the adapter-first design. H1 requires `SystemExit` catching in the adapter. H5 needs a structured gap/warning added to the packet.

### 11d. MEDIUM Findings (16)

| # | Builder | Finding | Location |
|---|---------|---------|----------|
| M1 | #2 guidance | Inner MATCH on GuidancePeriod may silently drop updates without period links | `warmup_cache.py:321, 346` |
| M2 | #2 guidance | PIT boundary uses `<=` (inclusive) — correct but convention undocumented | `warmup_cache.py:344` |
| M3 | #3 inter_quarter | Boundary day derivation via `[:10]` string slicing is timezone-unaware | `warmup_cache.py:1489-1490` |
| M4 | #3 inter_quarter | Cutoff-day OHLCV present even when `price_role='reference_only'` — downstream must check | `warmup_cache.py:1597-1601` |
| M5 | #3 inter_quarter | No validation on `created` field — None produces `"None"` day key | `warmup_cache.py:1604-1606` |
| M6 | #3 inter_quarter | Dividends/splits on boundary dates excluded (strict `>/<`). **Design choice, not bug** — date-only events have no timestamp, conservative exclusion is correct. Prices use `>=/ <=` because they have known settlement times. Document intended semantics. | `warmup_cache.py:1045-1046, 1061-1062` |
| M7 | #4 peer | Strict `<` on pit_cutoff excludes peers filed at exact timestamp. **Semantics choice** — "known strictly before" is defensible. | `peer_earnings_snapshot.py:38` |
| M8 | #4 peer | Ghost headline entries in Cypher collected then filtered downstream | `peer_earnings_snapshot.py:58-63` |
| M9 | #4 peer | `print()` to stdout (should be stderr) | `peer_earnings_snapshot.py:292` |
| M10 | #5 macro | Minute bar filtering excludes up to ~2 min before PIT. **Conservative by design** — requires entire 1-min bar to complete before cutoff. | `macro_snapshot.py:246` |
| M11 | #5 macro | VIX in PIT mode always previous day's close, even for in_market sessions. **Intentionally cautious**, not wrong. | `macro_snapshot.py:451-462` |
| M12 | #5 macro | `earlier` catalysts use tuples → serialize as JSON arrays, breaks dict convention | `macro_snapshot.py:585` |
| M13 | #5 macro | No explicit weekend/holiday handling (works by coincidence — no bars exist, so nothing over-included) | `macro_snapshot.py` |
| M14 | #5 macro | Polygon makes 11-12 API calls in ~5s. **Operational constraint** — exceeds free tier (5/min), paid tier fine. Document tier requirements, prefer Yahoo for Sunday/live smoke tests. | `macro_snapshot.py:407-439` |
| M15 | #6 consensus | `_get_classifier()` singleton race under ThreadPoolExecutor (benign) | `build_consensus.py:130-138` |
| M16 | #6 consensus | AV data values may be revised post-PIT (inherent to data source, not a code bug) | `build_consensus.py` |

### 11e. LOW Findings (11)

| # | Builder | Finding |
|---|---------|---------|
| L1 | #1 8k_packet | `print()` summary to stdout |
| L2 | #2 guidance | `render_guidance_text` produces `FYNone` if `fiscal_year` is None |
| L3 | #2 guidance | Dead code in `_format_value` (unreachable return) |
| L4 | #3 inter_quarter | Non-trading cutoff day gets `price_role: 'ordinary'` (misleading when price is None) |
| L5 | #3 inter_quarter | Multiple `print()` calls to stdout |
| L6 | #4 peer | Dead Cypher ORDER BY (re-sorted in Python) |
| L7 | #4 peer | Return type annotation lies (`list[dict]` vs actual `tuple`) |
| L8 | #5 macro | Hardcoded Benzinga channel list |
| L9 | #5 macro | yfinance VIX always fetched regardless of source setting |
| L10 | #6 consensus | `_load_env()` shared `os.environ` mutation from parallel threads (safe under GIL) |
| L11 | #7 prior_fin | `ZERO_FACT_DENYLIST` hardcoded (2 accessions) |

### 11f. Shared Infrastructure Findings

- **`_get_fye_month()`** duplicated identically in `build_consensus.py:262` and `build_prior_financials.py:250`. Both create independent Redis connections. Planned for centralization (§6a).
- **`_load_env()`** duplicated in multiple builders. Each modifies `os.environ` via `setdefault`. Safe under GIL but technically shared-state mutation.
- **`fiscal_math.py`** and **`get_quarterly_filings.py`** are correct and well-tested (99.1% accuracy across 549 filings).
- **`MarketSessionClassifier`** singleton in `build_consensus` is benign race under ThreadPoolExecutor.
- **`sec_quarter_cache_loader`** confirmed: only `fiscal_year_end:{TICKER}.month_adj` is PIT-safe.

### 11g. Must-Fix Before Phase 3

1. **C1**: Builder #3 PIT string comparison → proper datetime comparison (~5 lines)
2. **H5**: Builder #5 silent SPY data loss → add structured gap/warning to packet

### 11h. Handled by Adapter Layer (Phase 3)

- H1: `sys.exit(1)` → adapter catches `SystemExit`
- H2, H3, H4: Return contract normalization (read from disk, return dict)
- All stdout prints: adapter suppresses or redirects

### 11i. Design Choices to Document (not bugs)

- M6: Dividend/split boundary exclusion via strict `<` — conservative for date-only events (no timestamp precision). Intentional.
- M7: Peer strict `<` on pit_cutoff — "known strictly before" semantics. Defensible.
- M10: Minute bar ~2 min exclusion — requires complete bar before cutoff. Conservative by design.
- M11: VIX previous day's close for in_market PIT — intentionally cautious.
- M14: Polygon 11-12 calls per run — operational constraint, not code bug. Document paid-tier requirement.

### 11j. Timezone Rule (settled)

**Store timezone-aware timestamps. Compare as datetimes, never as strings.**

Do NOT migrate GuidanceUpdate from UTC to ET — Neo4j `datetime()` comparison handles cross-timezone correctly. The UTC storage is not a bug and migration is unnecessary churn. Render in America/New_York for human display only.
