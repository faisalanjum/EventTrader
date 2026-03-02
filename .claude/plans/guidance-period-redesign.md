# Guidance Period Redesign — Finalized Design + Implementation Plan

*Version 3.0 | 2026-02-26 | All decisions locked. Implementation plan reviewed and approved.*

---

## Core Concept

Replace the current fiscal-keyed, company-specific `Period` node with a new **`GuidancePeriod`** node that is a pure calendar window, company-agnostic.

**Current:** `guidance_period_320193_duration_FY2025_Q3` — tied to CIK, fiscal semantics, duration/instant type
**New:** `gp_2025-04-01_2025-06-30` — just calendar dates, shared across any company covering that window

**Why:**
1. **Cross-company comparability** — "all guidance targeting Oct-Dec 2024" is one node traversal, not per-company fiscal translation
2. **Clean separation** — calendar window (GuidancePeriod) vs fiscal label (GuidanceUpdate) vs measurement type (GuidanceUpdate.time_type) are untangled
3. **No more `period_type` collision** — currently means different things on Period vs GuidanceUpdate

---

## Decisions — LOCKED

### D1. GuidancePeriod is calendar-based, company-agnostic

```
GuidancePeriod
  u_id:       "gp_2025-04-01_2025-06-30"   (or sentinel: "gp_MT")
  start_date: "2025-04-01"                  (null for sentinels)
  end_date:   "2025-06-30"                  (null for sentinels)
```

No CIK, no fiscal_year, no fiscal_quarter, no period_type on this node.

#### GuidancePeriod property table

| Property | Type | Notes |
|---|---|---|
| `u_id` | String | `gp_{start}_{end}` for calendar periods, `gp_ST`/`gp_MT`/`gp_LT`/`gp_UNDEF` for sentinels |
| `id` | String | Same as `u_id` (convention for consistency with other node types) |
| `start_date` | String / null | ISO date (YYYY-MM-DD), null for sentinels |
| `end_date` | String / null | ISO date (YYYY-MM-DD), null for sentinels |

That's it — 3 meaningful properties. Intentionally minimal.

### D2. Sentinel nodes — HAS_PERIOD is ALWAYS required

**Cardinality constraint: each GuidanceUpdate has exactly ONE HAS_PERIOD edge.** This is the structural guarantee that prevents instant ambiguity (an instant at Jun 30 linking to Q3, H2, or annual). Enforced by the write path — `guidance_writer.py` does a single `MERGE (gu)-[:HAS_PERIOD]->(gp)` per GuidanceUpdate, never multiple.

When calendar dates are not determinable, the edge points to a sentinel node.

| Sentinel u_id | Label | Definition | Example text |
|---|---|---|---|
| `gp_ST` | Short-term | Near-term, but specific quarter/month unknown | "in the near term", "over the coming months" |
| `gp_MT` | Medium-term | ~1-5 years, no specific dates | "over the medium term", "over the next few years" |
| `gp_LT` | Long-term | 5+ years or permanent structural target, no dates | "long-term target", "over the next decade", "long-term margin model of 38-40%" |
| `gp_UNDEF` | Undefined | Cannot determine any timeframe | "we will continue to invest" (no horizon) |

Sentinel properties: `u_id` as above, `start_date: null`, `end_date: null`.

**Pre-create all 4 sentinels** in the constraints function alongside the uniqueness constraint on `GuidancePeriod.id`. They are fixed, global, and few.

### D3. Instant nodes are separate — start_date == end_date

Duration and instant measurements get **different** GuidancePeriod nodes. An instant is a single date point.

| Type | u_id | start_date | end_date |
|---|---|---|---|
| Duration Q3 (revenue) | `gp_2025-04-01_2025-06-30` | 2025-04-01 | 2025-06-30 |
| Instant end-of-Q3 (cash balance) | `gp_2025-06-30_2025-06-30` | 2025-06-30 | 2025-06-30 |

**Why separate:** Without this, an instant at Jun 30 could ambiguously share with Q3 duration, H2 duration, or annual duration. Separate nodes eliminate that class of ambiguity. The GuidanceUpdate's `time_type` still records the measurement semantics.

**Dependency:** Instant node creation requires `_compute_fiscal_dates()` to get the quarter end date. See D8 (SOLVED).

### D4. time_type field — defaults to "duration"

| Value | Meaning | Frequency |
|---|---|---|
| `duration` | Metric measured over a date range (revenue, EPS, margins, CapEx, growth) | ~99% of guidance |
| `instant` | Metric measured at a point in time (cash balance, debt outstanding, share count) | Extremely rare |

**Default is `duration`.** The agent only sets `instant` when the metric label is a known balance-sheet item. Known instant labels (exhaustive for now):
- cash_and_equivalents, total_debt, long_term_debt, shares_outstanding, book_value, net_debt

This is a lookup, not a judgment call — keeps the LLM focused.

### D5. GU ID format — keep embedding period_u_id

```
gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}
```

The `period_u_id` stays embedded in the composite ID. Calendar dates in the u_id (`gp_2025-04-01_2025-06-30`) are stable and won't change format again. Human-readable IDs are valuable for debugging.

Example new ID:
```
gu:AAPL_2023-11-03T17.00.00-04.00:revenue:gp_2023-10-01_2023-12-31:unknown:total
```

For sentinel-linked items:
```
gu:AAPL_2025-01-30T17.00.00-05.00:capex:gp_MT:unknown:total
```

### D6. Clean slate migration

All 31 existing GuidanceUpdate nodes and 7 Period nodes will be deleted and re-extracted from scratch. No migration Cypher needed. No backward compatibility concerns.

### D7. The period_type collision — resolved via rename

| Current | New name | Location | Values | Meaning |
|---|---|---|---|---|
| `GuidanceUpdate.period_type` | `period_scope` | GuidanceUpdate | See D9 enum | Fiscal granularity |
| `Period.period_type` | `time_type` | GuidanceUpdate | duration, instant | Flow vs point-in-time |

GuidancePeriod itself has NO type field — it's just a calendar window (or sentinel).

### D8. Calendar date resolution — SOLVED, use `_compute_fiscal_dates()` always

**No new function needed.** `_compute_fiscal_dates(fye_month, fiscal_year, fiscal_quarter)` from `get_quarterly_filings.py` already does fiscal-to-calendar conversion using month boundaries. 29/29 tests passing in `test_fiscal_resolve.py`.

**Decision: GuidancePeriod ALWAYS uses month-boundary dates.** Never XBRL exact dates.

Why not use `fiscal_resolve.py` Phase 1 (XBRL Period lookup)?
- **Dual-node risk**: If guidance is extracted before a 10-Q is filed, fallback gives `gp_2023-10-01_2023-12-31`. After the 10-Q loads, XBRL lookup gives `gp_2023-10-01_2023-12-30`. Two nodes for the same quarter, one day apart. Unacceptable.
- **Month boundaries are deterministic**: Same fiscal inputs -> same dates, regardless of when extraction runs or whether XBRL data exists.
- **Cross-company sharing works**: Two companies with same FYE month get identical dates, even if their exact 4-5-4 calendars differ by a day.
- **1-3 day approximation is irrelevant for guidance**: "We expect Q1 revenue of $89-93B" is about the quarter, not whether it ends Dec 30 or Dec 31.

**What this means for the pipeline:**
- **Extract `period_to_fiscal()`, `_normalize_fiscal_quarter()`, and `_compute_fiscal_dates()` into new `fiscal_math.py`** — pure stdlib, zero external dependencies. Then `get_quarterly_filings.py`, `fiscal_resolve.py` (drops its fragile `sys.modules` stub hack), and `guidance_ids.py` all import cleanly from `fiscal_math.py`. One-time extraction, every future consumer gets a clean import. Chosen over duplicating the stub hack (which breaks silently if `get_quarterly_filings.py` adds imports).
- No DB lookup needed for date resolution — pure math
- `fiscal_resolve.py` Phase 1 stays available for other use cases (XBRL filing matching) but is NOT used for GuidancePeriod

**For instant nodes:** `_compute_fiscal_dates()` gives the quarter's end date. Instant GuidancePeriod: `start_date = end_date = quarter_end_date`.

**Half-year and monthly — composition, not modification:** `_compute_fiscal_dates()` handles Q1-Q4 and FY but not `half` or `monthly`. These are solved in `build_guidance_period_id()` by composing existing calls:

```python
# Half-year: compose from two quarter calls (no _compute_fiscal_dates modification)
if half == 1:
    start = _compute_fiscal_dates(fye, fy, "Q1")[0]
    end   = _compute_fiscal_dates(fye, fy, "Q2")[1]
elif half == 2:
    start = _compute_fiscal_dates(fye, fy, "Q3")[0]
    end   = _compute_fiscal_dates(fye, fy, "Q4")[1]

# Monthly: no FYE needed — "March" is March regardless of fiscal calendar
from calendar import monthrange
start = f"{year}-{month:02d}-01"
end   = f"{year}-{month:02d}-{monthrange(year, month)[1]}"
```

**Calendar period override:** When text explicitly says "calendar year" or "calendar quarter" (rare — ~1% of items, mostly news), the LLM sets `calendar_override: true`. Python overrides FYE to 12:

```python
fye = 12 if item.get('calendar_override') else company_fye_month
start, end = _compute_fiscal_dates(fye, fiscal_year, fiscal_quarter)
```

No second code path, no separate calendar math function. A calendar year IS a fiscal year with FYE=December — `_compute_fiscal_dates(12, 2026, "FY")` -> `2026-01-01` to `2026-12-31`. This was chosen over two alternative approaches (a separate `is_calendar` branch with manual Jan-based math, or routing through `fiscal_resolve.py` for fiscal and a trivial function for calendar) because both alternatives create parallel code paths for what is fundamentally the same computation with one different input. Cross-company sharing also works correctly: AAPL and INTC both saying "calendar year 2026" produce the same `gp_2026-01-01_2026-12-31`.

### D9. Guidance-to-XBRL comparison — RESOLVED

GuidancePeriod dates won't match XBRL Period dates (month boundaries vs 4-5-4 calendar). **Doesn't matter — never join on dates.** Beat/miss comparison joins on `ticker + fiscal_year + fiscal_quarter + xbrl_qname`. At query time, classify XBRL Period nodes via `period_to_fiscal()` (99.1% accuracy, 549 filings validated). Both sides have fiscal fields; no bridging, no fuzzy matching needed.

---

## period_scope — Exhaustive Enum (9 values)

### Full mapping: period_scope <-> GuidancePeriod type

| `period_scope` | GuidancePeriod | Sentinel? | Example u_id | Example text |
|---|---|---|---|---|
| `quarter` | Real calendar dates | No | `gp_2025-04-01_2025-06-30` | "Q3 revenue of $85B" |
| `annual` | Real calendar dates | No | `gp_2024-10-01_2025-09-30` | "FY2025 CapEx of $30B" |
| `half` | Real calendar dates | No | `gp_2025-04-01_2025-09-30` | "Second half margin expansion" |
| `monthly` | Real calendar dates | No | `gp_2025-03-01_2025-03-31` | "March same-store sales" |
| `long_range` | Real calendar dates | No | `gp_2026-01-01_2028-12-31` | "By 2028", "2026-2028 target" |
| `short_term` | Sentinel | `gp_ST` | `gp_ST` | "In the near term", "coming months" |
| `medium_term` | Sentinel | `gp_MT` | `gp_MT` | "Over the medium term" |
| `long_term` | Sentinel | `gp_LT` | `gp_LT` | "Long-term target model of 38-40%" |
| `undefined` | Sentinel | `gp_UNDEF` | `gp_UNDEF` | "Going forward" (no temporal anchor) |

**Rule: first 5 require `_compute_fiscal_dates()` (D8). Last 4 always use sentinels with null dates.**

**`long_range` vs `long_term` disambiguation:** These sound similar but the distinction is simple — `long_range` has determinable dates ("by 2028" -> `gp_2028-01-01_2028-12-31`), `long_term` does not ("long-term margin model" -> `gp_LT`). If you can extract a year, it's `long_range`. If not, it's `long_term`.

### Resolution Priority Rule

> **Always use the most specific `period_scope` with determinable calendar dates. Sentinel only when dates are genuinely not determinable from context.**

- "In the near term" + earnings call is Jan 2026 -> agent SHOULD try to resolve to Q1/Q2 2026 (`quarter`). Only fall to `gp_ST` if truly unresolvable.
- "By 2028" -> `long_range` with `gp_2028-01-01_2028-12-31`, NOT `gp_LT`
- "Over the long run" (no year) -> `gp_LT`
- "Long-term margin model of 38-40%" -> `gp_LT` (permanent structural target, no dates)

### Fiscal Context Rule

> **In earnings calls and SEC filings, ALL period references are fiscal unless explicitly stated as calendar.** "Second half of the year" = fiscal H2 (Apr-Sep for AAPL FYE Sep), NOT calendar H2 (Jul-Dec). "Next quarter" = the next fiscal quarter. Only use calendar interpretation when the text explicitly says "calendar year" or "calendar quarter."

### Boundary Classification Examples (for agent prompt calibration)

| Text | Classification | Rationale |
|---|---|---|
| "Over the next several years" | `medium_term` -> `gp_MT` | ~2-5yr horizon, no specific year |
| "By the end of the decade" | `long_range` -> `gp_2029-01-01_2029-12-31` | "End of decade" = 2029; has determinable year |
| "Over the next decade" | `long_term` -> `gp_LT` | ~10yr, too vague for dates |
| "In the near term" (Q1 call, Q2 unmentioned) | `short_term` -> `gp_ST` | Can't pin to specific quarter |
| "In the near term" (Q1 call, context implies Q2) | `quarter` -> real dates | Context resolves it |
| "Long-term gross margin model of 38-40%" | `long_term` -> `gp_LT` | Permanent target, no timeframe |
| "We expect FY2028 revenue of $X" | `long_range` -> `gp_...` | Has fiscal year -> has dates |

### Sub-period routing rules (period_scope is a CLOSED enum)

When a CFO references a granularity finer than or misaligned with the 9 values above, route to a field on the parent item:

| CFO says | Route to | Example |
|---|---|---|
| Monthly detail ("strong December") | `conditions` on parent quarter item | Revenue(Q1): conditions = "strong December demand" |
| "Rest of year" (e.g., Q2-Q4) | `annual` scope + conditions | Revenue(FY2025): conditions = "remaining three quarters" |
| "Next two quarters" / arbitrary span | `half` if H1/H2 aligned; else `annual` + conditions | If Q3+Q4=H2, use half. If Q2+Q3, use annual + conditions |
| "Next 12 months" (calendar, not fiscal) | `annual`, approximate to nearest FY | Map to FY covering majority of the 12-month window |
| "Holiday season" / "back to school" | `conditions` on parent quarter | Revenue(Q1): conditions = "holiday season strength" |
| Weekly / daily references | `conditions` on parent quarter | Never a standalone scope |

**Principle:** `period_scope` is a closed 9-value enum. Any time reference that doesn't cleanly map goes into `conditions` or `qualitative` on the parent item. The agent must never invent new scope values.

---

## LLM vs Python Responsibility Split

To keep the LLM focused and maximize determinism:

### LLM extraction fields (from transcript/filing text):

| Field | Type | When to set | Example |
|---|---|---|---|
| `fiscal_year` | int / null | When text mentions a fiscal year | `2025` |
| `fiscal_quarter` | int / null | When text mentions a specific quarter (1-4) | `3` |
| `half` | int / null | When text mentions H1 or H2 (1 or 2) | `2` |
| `month` | int / null | When text mentions a specific month (1-12) | `3` for March |
| `long_range_start_year` | int / null | Start year of a multi-year span | `2026` for "2026 to 2028" |
| `long_range_end_year` | int / null | End year of a span, or single target year | `2028` for "by 2028" or "2026 to 2028" |
| `calendar_override` | bool | Only when text explicitly says "calendar year/quarter" | `true` |
| `sentinel_class` | string / null | Only when NO fiscal fields are extractable | `short_term`, `medium_term`, `long_term`, `undefined` |
| `time_type` | string / null | Only when label is in known instant set (D4) | `instant` (defaults to `duration` if omitted) |

**Rules:**
- Set as many fiscal fields as the text supports. "Q3 FY2025" -> `fiscal_year: 2025, fiscal_quarter: 3`. "FY2025" -> `fiscal_year: 2025` only.
- For "by 2028" (single target year): `long_range_end_year: 2028`, no start year.
- For "2026 to 2028" (span): `long_range_start_year: 2026, long_range_end_year: 2028`.
- `sentinel_class` is ONLY set when ALL fiscal fields are null. This is a 4-way judgment call — the only LLM judgment in the period pipeline.
- `calendar_override` and `time_type` are independent of all other fields.

### Python routing logic (fiscal fields -> period_scope -> calendar dates):

Python evaluates the LLM fields in this order. First match wins:

```
1. sentinel_class is set?          -> period_scope = sentinel_class
                                      u_id = gp_{sentinel_class abbreviation}

2. long_range_end_year is set?     -> period_scope = "long_range"
                                      if long_range_start_year:
                                        start = _compute_fiscal_dates(fye, start_year, "FY")[0]
                                      else:
                                        start = _compute_fiscal_dates(fye, end_year, "FY")[0]
                                      end = _compute_fiscal_dates(fye, end_year, "FY")[1]

3. month is set?                   -> period_scope = "monthly"
                                      start = {year}-{month}-01
                                      end = {year}-{month}-{last_day}

4. half is set?                    -> period_scope = "half"
                                      if half == 1: start=Q1_start, end=Q2_end
                                      if half == 2: start=Q3_start, end=Q4_end

5. fiscal_quarter is set?          -> period_scope = "quarter"
                                      start, end = _compute_fiscal_dates(fye, fy, Qn)

6. fiscal_year is set (no quarter) -> period_scope = "annual"
                                      start, end = _compute_fiscal_dates(fye, fy, "FY")

7. fallthrough (none matched)     -> period_scope = "undefined"
                                      u_id = "gp_UNDEF"
                                      (log warning: unexpected — LLM should have set sentinel_class)
```

At every step, `fye = 12 if calendar_override else company_fye_month`.

For instant items (`time_type == "instant"` or `label_slug in KNOWN_INSTANT_LABELS`): after computing dates, set `start_date = end_date` (the period's end date becomes the point-in-time).

### What the LLM never does:
- Compute `period_scope` for date-bearing items (Python determines it from fiscal fields)
- Compute calendar dates
- Build IDs or u_ids
- Make the sentinel classification when fiscal fields ARE present (Python handles everything)

---

## GuidancePeriod Examples

### Calendar periods (real dates)

| Scenario | u_id | start_date | end_date | GU.period_scope | GU.time_type |
|---|---|---|---|---|---|
| AAPL Q1 FY2024 (Oct-Dec 2023) | `gp_2023-10-01_2023-12-31` | 2023-10-01 | 2023-12-31 | quarter | duration |
| AAPL Q3 FY2025 (Apr-Jun 2025) | `gp_2025-04-01_2025-06-30` | 2025-04-01 | 2025-06-30 | quarter | duration |
| AAPL FY2025 (Oct 2024-Sep 2025) | `gp_2024-10-01_2025-09-30` | 2024-10-01 | 2025-09-30 | annual | duration |
| H2 FY2025 AAPL (Apr-Sep 2025) | `gp_2025-04-01_2025-09-30` | 2025-04-01 | 2025-09-30 | half | duration |
| "By 2028" | `gp_2028-01-01_2028-12-31` | 2028-01-01 | 2028-12-31 | long_range | duration |
| "2026 to 2028" span | `gp_2026-01-01_2028-12-31` | 2026-01-01 | 2028-12-31 | long_range | duration |
| Cash balance end-of-Q3 (instant) | `gp_2025-06-30_2025-06-30` | 2025-06-30 | 2025-06-30 | quarter | instant |

### Cross-company sharing

```
AAPL guides Oct-Dec 2024 revenue (their Q1 FY2025):
  GuidanceUpdate: fiscal_year=2025, fiscal_quarter=1, period_scope="quarter"
  HAS_PERIOD -> gp_2024-10-01_2024-12-31

INTC guides Oct-Dec 2024 revenue (their Q4 FY2024):
  GuidanceUpdate: fiscal_year=2024, fiscal_quarter=4, period_scope="quarter"
  HAS_PERIOD -> gp_2024-10-01_2024-12-31  <- SAME NODE
```

### Sentinel periods (no dates)

| Scenario | u_id | GU.period_scope |
|---|---|---|
| "Over the medium term" CapEx growth | `gp_MT` | medium_term |
| "Long-term margin model 38-40%" | `gp_LT` | long_term |
| "In the near term" (unresolvable) | `gp_ST` | short_term |
| "Going forward" (no context) | `gp_UNDEF` | undefined |

---

## Sentinel Node Design

### Properties

```cypher
// Pre-created, immutable
(:GuidancePeriod {u_id: 'gp_ST',    id: 'gp_ST',    start_date: null, end_date: null})
(:GuidancePeriod {u_id: 'gp_MT',    id: 'gp_MT',    start_date: null, end_date: null})
(:GuidancePeriod {u_id: 'gp_LT',    id: 'gp_LT',    start_date: null, end_date: null})
(:GuidancePeriod {u_id: 'gp_UNDEF', id: 'gp_UNDEF', start_date: null, end_date: null})
```

### Query guards

Any date-range query MUST handle null dates:
```cypher
// BAD: drops all sentinel-linked guidance
WHERE gp.start_date >= '2025-01-01'

// GOOD: explicit null guard
WHERE gp.start_date IS NOT NULL AND gp.start_date >= '2025-01-01'
```

### Known trade-offs

1. **Supernode at scale**: `gp_MT` accumulates HAS_PERIOD edges from all companies. Always add a company filter: `MATCH (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})`. Neo4j handles millions of edges per node, so this is a distant concern.
2. **Cross-company sharing is meaningless for sentinels**: Sharing `gp_MT` just means "both are vague." No analytical value, but no harm.
3. **u_id format break**: Calendar periods use `gp_{date}_{date}`, sentinels use `gp_XX`. Code checking sentinel status: `u_id IN ['gp_ST', 'gp_MT', 'gp_LT', 'gp_UNDEF']` or `start_date IS NULL`.
4. **Boundary subjectivity** (ST vs MT vs LT): Inherent to natural language. Mitigated by the resolution priority rule (prefer real dates) and calibration examples in agent prompt. Two agents may classify "next several years" differently, but this only affects the ~1% of items that reach sentinel classification.

---

## Implementation Plan

### Baseline: 169 tests passing across 4 suites (60 + 62 + 29 + 18)

### Files Touched

| # | File | Action | Risk |
|---|------|--------|------|
| 1 | `scripts/fiscal_math.py` | CREATE — extract 3 pure functions | Zero (new file) |
| 2 | `scripts/get_quarterly_filings.py` | EDIT — import 3 functions from fiscal_math.py | Low (thin import swap) |
| 3 | `scripts/fiscal_resolve.py` | EDIT — drop stub hack, import from fiscal_math.py | Low (same functions, cleaner import) |
| 4 | `scripts/guidance_ids.py` | EDIT — add `build_guidance_period_id()`, keep `build_period_u_id()` deprecated | Medium (core ID logic) |
| 5 | `scripts/guidance_writer.py` | EDIT — MERGE GuidancePeriod, add period_scope+time_type, sentinel pre-creation | Medium (Cypher template) |
| 6 | `scripts/guidance_write_cli.py` | EDIT — period routing plumbing, fye_month support | Low (plumbing) |
| 7a | `QUERIES.md` | EDIT — query 7E only: Period -> GuidancePeriod | Low (documentation) |
| 7b | `SKILL.md` (guidance-inventory) | EDIT — schema, fields, enum updates | Low (documentation) |
| 7c | `agents/guidance-extract.md` | EDIT — LLM field table, routing, sentinel rules | Low (prompt text) |
| 7d | `agents/guidance-qa-enrich.md` | EDIT — same scope as 7c (build_period_u_id refs, 7E format, payload) | Low (prompt text) |
| 8a | `scripts/test_guidance_ids.py` | EDIT — add ~15 new tests for build_guidance_period_id() | Required |
| 8b | `scripts/test_guidance_writer.py` | EDIT — update assertions for GuidancePeriod | Required |
| 8c | `scripts/test_guidance_write_cli.py` | EDIT — update test items, add routing test | Required |

All file paths relative to `.claude/skills/earnings-orchestrator/` (scripts) or `.claude/skills/guidance-inventory/` (QUERIES/SKILL) or `.claude/` (agents).

### Files NOT Touched (and why)

- **`guidance_write.sh`** — shell wrapper, no logic. Calls guidance_write_cli.py unchanged.
- **`guidance-transcript.md`** — orchestrator skill, just dispatches to guidance-extract agent. No changes needed.
- **`test_fiscal_resolve.py`** — imports `_compute_fiscal_dates` from `get_quarterly_filings`, which re-exports from `fiscal_math`. All 29 tests pass unchanged. Verified: Python re-exports imported names.
- **`neo4j-schema/SKILL.md`** — point-in-time snapshot from 2026-01-04. Predates entire guidance system (Guidance/GuidanceUpdate also absent). No guidance agent loads it. Follow-up task when schema snapshot is refreshed.

---

### Step 1: Create `fiscal_math.py`

**File**: `scripts/fiscal_math.py`

**What**: Extract 3 pure functions verbatim from `get_quarterly_filings.py`:
- `period_to_fiscal()` (lines 66-136) — fiscal year/quarter classification from period dates
- `_normalize_fiscal_quarter()` (lines 139-152) — input normalization (Q1/Q2/Q3/Q4/FY)
- `_compute_fiscal_dates()` (lines 155-193) — fiscal-to-calendar month-boundary computation

**Imports**: `from datetime import date` + `import calendar`. Nothing else. Pure stdlib, zero external dependencies.

**Why**: Both `guidance_ids.py` (new `build_guidance_period_id()`) and `fiscal_resolve.py` need these functions. Currently `fiscal_resolve.py` uses a fragile `sys.modules` stub hack (lines 31-39) to import them from `get_quarterly_filings.py` without triggering its `neo4j`/`dotenv` top-level imports. Extracting eliminates the hack. If `get_quarterly_filings.py` ever adds imports, the stub breaks silently — `fiscal_math.py` has no such risk.

**Regression risk**: Zero. New file, nothing imports from it yet.

### Step 2: Update `get_quarterly_filings.py`

**What**: Remove the 3 function definitions (lines 66-193). Replace with imports from `fiscal_math.py`.

**Before**: 3 function definitions totaling ~130 lines.

**After**:
```python
from fiscal_math import period_to_fiscal, _normalize_fiscal_quarter, _compute_fiscal_dates
```

**Why all 3**: `get_quarterly_filings.py` calls `period_to_fiscal` at lines 252, 253, 357, 492 and `_compute_fiscal_dates` at line 213. All 3 must be imported.

**Regression test**: Run `test_fiscal_resolve.py` (29 tests). It imports `_compute_fiscal_dates` from `get_quarterly_filings` and `resolve` from `fiscal_resolve` — both exercise the extracted functions transitively.

**Regression risk**: Very low. Same functions, same behavior, different module origin.

### Step 3: Update `fiscal_resolve.py`

**What**: Remove the `sys.modules` stub hack (lines 31-39), `import types` (line 28), and the import from `get_quarterly_filings.py` (lines 42-47). Replace with clean import from `fiscal_math.py`.

**Before** (lines 28-47):
```python
import types
...
for _mod_name in ('dotenv', 'neo4j'):
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        ...
        sys.modules[_mod_name] = _stub

sys.path.insert(0, "...")
from get_quarterly_filings import (
    period_to_fiscal, _compute_fiscal_dates, _normalize_fiscal_quarter,
)
```

**After**:
```python
from fiscal_math import period_to_fiscal, _compute_fiscal_dates, _normalize_fiscal_quarter
```

**Regression test**: Run `test_fiscal_resolve.py` — all 29 tests must pass.

### Step 4: Update `guidance_ids.py` — new `build_guidance_period_id()`

**What**:
1. Add `from fiscal_math import _compute_fiscal_dates` at top
2. Add constants: `KNOWN_INSTANT_LABELS` (D4 set), `SENTINEL_MAP` (4 sentinels)
3. Add new function `build_guidance_period_id()` — the 6-step Python routing logic + Step 7 fallthrough
4. **Keep `build_period_u_id()` intact** — mark `# DEPRECATED` but do not delete. Costs nothing, prevents mid-implementation breakage.

**New function**:
```python
KNOWN_INSTANT_LABELS = {
    'cash_and_equivalents', 'total_debt', 'long_term_debt',
    'shares_outstanding', 'book_value', 'net_debt',
}

SENTINEL_MAP = {
    'short_term': 'gp_ST',
    'medium_term': 'gp_MT',
    'long_term': 'gp_LT',
    'undefined': 'gp_UNDEF',
}

def build_guidance_period_id(
    *, fye_month, fiscal_year=None, fiscal_quarter=None,
    half=None, month=None,
    long_range_start_year=None, long_range_end_year=None,
    calendar_override=False, sentinel_class=None,
    time_type=None, label_slug=None,
) -> dict:
    """
    Python routing logic: LLM extraction fields -> period_scope + calendar dates + u_id.
    Returns: {u_id, start_date, end_date, period_scope, time_type}
    """
```

Implements the 7-step routing (6 from plan + defensive fallthrough to `gp_UNDEF`).

**`build_guidance_ids()` — no signature change.** It already accepts `period_u_id` as a string. New `gp_` format IDs flow through unchanged.

**Regression**: All 60 existing tests pass (they use `build_period_u_id()` which is untouched). New tests added in 8a.

### Step 5: Update `guidance_writer.py`

**(5a) `_build_core_query()`** — Change Period MERGE to GuidancePeriod:

Before (lines 107-113):
```cypher
MERGE (p:Period {u_id: $period_u_id})
  ON CREATE SET p.id = $period_u_id,
                p.period_type = $period_node_type,
                p.fiscal_year = $fiscal_year,
                p.fiscal_quarter = $fiscal_quarter,
                p.cik = toString(toInteger(company.cik))
```

After:
```cypher
MERGE (gp:GuidancePeriod {id: $period_u_id})
  ON CREATE SET gp.u_id = $period_u_id,
                gp.start_date = $gp_start_date,
                gp.end_date = $gp_end_date
```

Also: `MERGE (gu)-[:HAS_PERIOD]->(p)` -> `MERGE (gu)-[:HAS_PERIOD]->(gp)`. RETURN references `gp`.

**Note:** MERGE on `{id:}` aligns GuidancePeriod with Guidance and GuidanceUpdate (both MERGE on `id`). The constraint's implicit index on `id` is used for MERGE lookup. `u_id` is populated via ON CREATE SET for backward-compatible queries.

**(5b) GuidanceUpdate SET block** — Rename `gu.period_type` to `gu.period_scope`. Add `gu.time_type`:
```cypher
      gu.period_scope = $period_scope,
      gu.time_type = $time_type,
```

**(5c) `_build_params()`** — Update parameter assembly:
- Add: `gp_start_date`, `gp_end_date`, `period_scope`, `time_type`
- Remove: `period_node_type` (no longer on the period node)
- Rename: key `period_type` -> `period_scope`
- Keep: `fiscal_year`, `fiscal_quarter` (still on GuidanceUpdate)

**(5d) `create_guidance_constraints()`** — Add GuidancePeriod constraint + sentinel pre-creation:

Constraint named `guidance_period_id_unique` on `gp.id` (matching naming convention of `guidance_id_unique` and `guidance_update_id_unique`):
```python
("CREATE CONSTRAINT guidance_period_id_unique IF NOT EXISTS "
 "FOR (gp:GuidancePeriod) REQUIRE gp.id IS UNIQUE"),
```

Pre-create 4 sentinels (idempotent MERGE):
```python
("MERGE (gp:GuidancePeriod {id: 'gp_ST'}) "
 "SET gp.u_id = 'gp_ST', gp.start_date = null, gp.end_date = null"),
# ... gp_MT, gp_LT, gp_UNDEF
```

### Step 6: Update `guidance_write_cli.py`

**(6a)** Accept optional `fye_month` in top-level JSON payload (alongside `source_id`, `source_type`, `ticker`). Only needed when items lack pre-computed `period_u_id`.

**(6b)** In `_ensure_ids()`: if item has no `period_u_id` but has LLM fields (`fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_start_year`, `long_range_end_year`, `calendar_override`, `sentinel_class`, `time_type`), call `build_guidance_period_id()` to compute it. Store resulting `u_id` as `period_u_id`, plus `period_scope`, `time_type`, `gp_start_date`, `gp_end_date` on the item.

**(6c)** Import `build_guidance_period_id` alongside existing imports.

**Regression**: Existing tests use `period_u_id` already set on items. The new routing only triggers when `guidance_update_id` is missing AND `period_u_id` is missing.

### Step 7: Documentation updates

**(7a) QUERIES.md — Query 7E only.**

Lines 62/81 (queries 1C/1D) reference XBRL `Context->Period` — NOT guidance nodes. Must NOT change.

Query 7E (line 542) changes:
- `MATCH (gu)-[:HAS_PERIOD]->(p:Period)` -> `MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)`
- RETURN: `p.u_id AS period_u_id` -> `gp.u_id AS period_u_id`
- RETURN: remove `p.period_type AS period_node_type` (gone from period node)
- RETURN: `gu.period_type` -> `gu.period_scope`
- RETURN: add `gu.time_type`

**(7b) SKILL.md (guidance-inventory):**
- §1: Schema — `GuidancePeriod` replaces `Period` in guidance graph. Update node table, relationship map (`HAS_PERIOD -> GuidancePeriod`).
- §2: Extraction fields — `period_type` (field #2) -> `period_scope` with new enum values. Add `time_type` field.
- §3: Deterministic IDs — `period_u_id` format is now `gp_YYYY-MM-DD_YYYY-MM-DD` or `gp_XX` sentinel. Update canonicalization table.
- §9: Period Resolution — replace fiscal-keyed table with `period_scope` enum table + Python routing logic reference.
- §10: Steps — `build_guidance_period_id()` replaces `build_period_u_id()`.
- §15: Write path — `GuidancePeriod` in pipeline diagram.

**(7c) `agents/guidance-extract.md`:**
- Step 3 (LLM extraction): replace current `period_type`/`fiscal_year`/`fiscal_quarter` with the 9-field LLM extraction table.
- Step 4 (deterministic validation): replace `build_period_u_id()` Bash invocation with `build_guidance_period_id()`. Or note that the CLI handles period routing when item lacks `period_u_id` (Step 6b).
- Add: sentinel classification rules, resolution priority rule, boundary examples, known instant labels, fiscal context rule.
- JSON payload format: add new LLM fields (`sentinel_class`, `calendar_override`, `time_type`, `half`, `month`, `long_range_start_year`, `long_range_end_year`). Remove `period_node_type`. Add `fye_month` at top level.

**(7d) `agents/guidance-qa-enrich.md`:**
- Step 2: 7E readback now returns `gp.u_id AS period_u_id`, `gu.period_scope`, `gu.time_type` (no `p.period_type AS period_node_type`).
- Step 6 (lines 116-124): replace `build_period_u_id()` Bash invocation with `build_guidance_period_id()` for new Q&A-only items.
- JSON payload: same format changes as 7c.

### Step 8: Test updates

**(8a) `test_guidance_ids.py`** — Keep all 60 existing tests. Add new tests for `build_guidance_period_id()`:
- Quarter Dec FYE -> `gp_2025-01-01_2025-03-31`, period_scope=quarter, time_type=duration
- Quarter Sep FYE (AAPL Q1 FY2025) -> `gp_2024-10-01_2024-12-31`
- Annual Sep FYE -> `gp_2024-10-01_2025-09-30`
- Half H2 Sep FYE -> `gp_2025-04-01_2025-09-30`
- Monthly March -> `gp_2025-03-01_2025-03-31`
- Long range single year -> `gp_2028-01-01_2028-12-31`
- Long range span -> `gp_2026-01-01_2028-12-31`
- Each sentinel (4 tests) -> `gp_ST`, `gp_MT`, `gp_LT`, `gp_UNDEF`
- Instant label detection -> `cash_and_equivalents` -> time_type=instant, start_date=end_date
- Calendar override -> forces FYE=12 regardless of input
- Fallthrough (all nulls, no sentinel_class) -> `gp_UNDEF` (defensive)
- Default time_type -> duration when omitted

**(8b) `test_guidance_writer.py`** — Update assertions:
- `_make_item()` defaults: `period_u_id` -> `gp_2025-04-01_2025-06-30`, add `period_scope: 'quarter'`, `time_type: 'duration'`, `gp_start_date: '2025-04-01'`, `gp_end_date: '2025-06-30'`. Remove `period_node_type`.
- `test_query_period_fiscal_keyed` -> rename to `test_query_period_calendar_based`: assert `GuidancePeriod` label, `gp_start_date`, `gp_end_date`, no `p.cik`, no `p.fiscal_year`.
- `test_query_contains_all_gu_properties` -> add `gu.period_scope`, `gu.time_type`, remove `gu.period_type`.
- `test_params_no_date_fields` -> INVERT: assert `gp_start_date` and `gp_end_date` ARE in params.
- `test_params_defaults` -> add `period_scope`, `time_type` defaults.
- `test_create_constraints` -> assert 3 constraints + 4 sentinels = 7 calls total.
- Add: `test_sentinel_period_write` — item with `gp_MT` period, null dates.

**(8c) `test_guidance_write_cli.py`** — Update test items:
- `_make_raw_item()`: update `period_u_id` from `guidance_period_320193_duration_FY2025_Q1` to `gp_2024-10-01_2024-12-31`.
- Add: test for LLM-field routing (item with `fiscal_year`/`fiscal_quarter` but no `period_u_id` -> CLI computes `gp_` ID via `build_guidance_period_id()`).

**(8d) `test_fiscal_resolve.py`** — No changes. Import paths work transitively.

### Step 9: Run all tests, verify 0 failures

All 4 test suites must pass. Expected: ~184 tests (169 existing + ~15 new), 0 failures.

### ~~Step 10: DB cleanup~~ — DONE (2026-02-26)

Deleted 31 GuidanceUpdate, 11 Guidance, 7 guidance-specific Period nodes (162 relationships). All 9,919 XBRL Period nodes verified untouched. **Skip this step.** Sentinel creation will happen via `create_guidance_constraints()` when Step 5d lands.

---

### Execution Order

| Order | Steps | Test Gate | Pass criteria |
|-------|-------|-----------|---------------|
| 1 | Step 1 (fiscal_math.py) | None | New file, no dependents yet |
| 2 | Step 2 (get_quarterly_filings.py) | `test_fiscal_resolve.py` | 29/29 |
| 3 | Step 3 (fiscal_resolve.py) | `test_fiscal_resolve.py` | 29/29 |
| 4 | Step 4 + 8a (guidance_ids.py + tests) | `test_guidance_ids.py` | 60 old + ~15 new / 0 fail |
| 5 | Step 5 + 8b (guidance_writer.py + tests) | `test_guidance_writer.py` | ~63 / 0 fail |
| 6 | Step 6 + 8c (guidance_write_cli.py + tests) | `test_guidance_write_cli.py` | ~20 / 0 fail |
| 7 | Step 7 (QUERIES.md, SKILL.md, agents) | Manual review | — |
| 8 | Step 9 (full run) | All 4 suites | ~184 / 0 fail |
| 9 | Step 10 (DB cleanup) | Cypher verification | 4 sentinels exist |

Each step is independently testable. If any step breaks, stop and fix before proceeding.

---

### What This Does NOT Change

- No changes to source content queries (QUERIES.md §3-§6, queries 1C/1D)
- No changes to concept/member edge logic — stays identical
- No changes to feature flag mechanism
- No changes to `guidance_write.sh` — just a shell wrapper
- No changes to `guidance-transcript.md` — just dispatches to the agent
- `build_period_u_id()` is NOT deleted — kept deprecated for backward compatibility

### Follow-up Tasks (post-implementation)

1. **Update `guidanceInventory.md`** (SKILL.md v3.0 spec) — §1/§2/§3/§6/§9/§10/§15 to match new code. Track to prevent spec divergence.
2. **Refresh `neo4j-schema/SKILL.md`** — move Guidance/GuidanceUpdate out of IGNORE section, add GuidancePeriod. Next schema snapshot refresh.
3. **Phase 2: Clean slate re-extraction** — re-extract all 5 AAPL sources using new pipeline, validate against known values.

---

## Open Items

1. ~~**fiscal_to_calendar**~~ — **RESOLVED.** Use `_compute_fiscal_dates()` always. See D8.
2. ~~**Approximate vs exact dates**~~ — **RESOLVED.** Always approximate for GuidancePeriod. Beat/miss joins on fiscal fields via `period_to_fiscal()`, never dates. See D9.
3. ~~**"By fiscal 2028"**~~ — **RESOLVED.** LLM outputs `long_range_end_year: 2028`. Python routing step 2 computes `_compute_fiscal_dates(fye, 2028, "FY")`. See Python routing logic.
4. ~~**Agent extraction flow details**~~ — **RESOLVED.** LLM extraction field table + Python routing decision tree fully specified above.
5. ~~**Agent prompt wording**~~ — **RESOLVED.** Implementation Step 7c/7d.

All design items resolved. Implementation plan locked and complete (Steps 1-10 done, 194 tests passing).

---

## Known Issue: `anyOf` Schema API 400 — Built-in Agent Types Broken

**Date discovered**: 2026-02-26 (during implementation audit)

**Symptom**: Built-in agent types (`Explore`, `Plan`, `general-purpose`) spawned via Task tool crash immediately with:
```
API Error: 400 tools.20.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level
```

**Root cause (5-layer causal chain)**:

1. **API constraint**: Anthropic Messages API forbids `oneOf`/`allOf`/`anyOf` at the top level of tool `input_schema`. This is by design, not a bug.

2. **Bad MCP schemas**: Perplexity MCP v0.14.0 (`@perplexity-ai/mcp-server`) defines tool schemas with `anyOf` at the top level. Valid JSON Schema, but violates the Anthropic API restriction. AlphaVantage HTTP MCP may also be affected.

3. **Main thread vs subagent divergence**: In the main thread, MCP tools are deferred via ToolSearch — bad schemas never reach the API upfront. In subagents, Claude Code assembles a **complete tool array at spawn time** including ALL registered MCP schemas. If any schema has `anyOf`, the entire API request is rejected before the agent executes a single instruction.

4. **Built-in agents are uncontrollable**: Custom agents (like `guidance-extract`) have `.md` frontmatter where a `tools:` field can whitelist only clean tools, excluding bad MCP. Built-in agent types (`Explore`, `Plan`, `general-purpose`) have NO user-editable frontmatter — their tool sets are defined internally. They always inherit all MCP tools, so they always crash when bad MCP servers are registered.

5. **Session snapshot is immutable**: Agent frontmatter is captured at session start. Mid-session edits require a fresh session to take effect.

**Why it's not fixed upstream**: 15+ GitHub issues filed (#4886, #5973, #10606, #3940, #4753, #4295, etc.). Most closed as "not planned" or "duplicate". MCP Core added partial schema sanitization (2026-01-13) but it doesn't cover the subagent spawn path.

**Impact on this project**:

| Agent type | Has `tools:` field? | Affected? |
|-----------|--------------------|-----------|
| `guidance-extract` (custom) | Yes | No — works fine |
| `guidance-qa-enrich` (custom) | Yes | No — works fine |
| Data sub-agents (custom) | Yes | No — work fine |
| `Explore` / `Plan` / `general-purpose` (built-in) | No | **Yes — always crashes** |

**Workarounds**:
1. Use direct tools (Read/Grep/Glob) from main thread instead of spawning built-in agents
2. For complex searches, create custom agents with explicit `tools:` fields excluding bad MCP
3. Disable Perplexity/AlphaVantage MCP before spawning built-in agents
4. Downgrade Perplexity MCP to pre-v0.13.0

**Cross-reference**: Full research in `earnings-analysis/test-outputs/research-anyof-bug.txt`. Infrastructure notes in `.claude/plans/Infrastructure.md` §anyOf.
