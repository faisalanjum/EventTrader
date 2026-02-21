---
name: guidance-inventory
description: Graph-native guidance extraction reference. Defines schema, extraction fields, validation rules, ID computation, XBRL matching, and write patterns. Auto-loaded by guidance-extract agent.
allowed-tools: Read, Write, Grep, Glob, Skill, mcp__neo4j-cypher__read_neo4j_cypher, mcp__neo4j-cypher__write_neo4j_cypher, Bash
model: claude-opus-4-5-20251101
permissionMode: dontAsk
---

# Guidance Inventory — Core Reference

Graph-native guidance extraction system. Writes `Guidance` and `GuidanceUpdate` nodes to Neo4j. No markdown output, no file accumulation.

**Thinking**: ALWAYS use `ultrathink` for maximum reasoning depth when extracting and classifying guidance.

**Spec**: `.claude/plans/guidanceInventory.md` v2.3

## Table of Contents

1. [Graph Schema](#1-graph-schema)
2. [Extraction Fields](#2-extraction-fields)
3. [Deterministic IDs](#3-deterministic-ids)
4. [Metric Normalization](#4-metric-normalization)
5. [Derivation Rules](#5-derivation-rules)
6. [Basis Rules](#6-basis-rules)
7. [Segment Rules](#7-segment-rules)
8. [Unit Canonicalization](#8-unit-canonicalization)
9. [Period Resolution](#9-period-resolution)
10. [Context Resolution](#10-context-resolution)
11. [XBRL Matching](#11-xbrl-matching)
12. [Source Processing](#12-source-processing)
13. [Quality Filters](#13-quality-filters)
14. [Chronological Ordering](#14-chronological-ordering)
15. [Write Path](#15-write-path)
16. [Execution Modes](#16-execution-modes)
17. [Error Taxonomy](#17-error-taxonomy)
18. [Reference Files](#18-reference-files)

---

## 1. Graph Schema

### New Nodes

| Node | Role | XBRL Parallel |
|------|------|---------------|
| **Guidance** | Generic metric tag, company-agnostic | Concept |
| **GuidanceUpdate** | Per-mention data point with all values | Fact |

### Reused Nodes

`Context`, `Period`, `Unit`, `Company`, `Concept`, `Member`

### Relationship Map

| From | Rel | To | When |
|------|-----|----|------|
| GuidanceUpdate | UPDATES | Guidance | Always |
| GuidanceUpdate | IN_CONTEXT | Context | Always (company+period) |
| GuidanceUpdate | FROM_SOURCE | Report / Transcript / News | Always (provenance) |
| GuidanceUpdate | HAS_PERIOD | Period | Always (direct period shortcut) |
| GuidanceUpdate | HAS_UNIT | Unit | Always (canonical unit) |
| GuidanceUpdate | MAPS_TO_MEMBER | Member | 0..N confident segment matches |
| Context | FOR_COMPANY | Company | Always (via cik) |
| Context | HAS_PERIOD | Period | Always |

### Constraints

```cypher
CREATE CONSTRAINT guidance_id_unique IF NOT EXISTS
FOR (g:Guidance) REQUIRE g.id IS UNIQUE;

CREATE CONSTRAINT guidance_update_id_unique IF NOT EXISTS
FOR (gu:GuidanceUpdate) REQUIRE gu.id IS UNIQUE;
```

### Guidance Node Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | `guidance:{slug(label)}` |
| `label` | String | Normalized metric name |
| `aliases` | String[] | Alternate names |
| `created_date` | String | ISO date when first detected |

### GuidanceUpdate Node Properties

All 19 extraction fields (see [§2](#2-extraction-fields)) plus system identity properties:

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Deterministic key (see [§3](#3-deterministic-ids)) |
| `evhash16` | String | First 16 hex chars of evidence hash |
| `xbrl_qname` | String / null | Resolved XBRL concept qname (see [§11](#11-xbrl-matching)) |
| `unit_raw` | String / null | Verbatim unit text, only when `unit='unknown'` |

---

## 2. Extraction Fields

Every GuidanceUpdate carries these 19 properties. System identity properties (`id`, `evhash16`) are added at write time.

| # | Field | Type | Constraint | Example |
|---|-------|------|------------|---------|
| 1 | `given_date` | String | ISO date | `"2025-01-30"` |
| 2 | `period_type` | String | `quarter`, `annual`, `half`, `long-range`, `other` | `"quarter"` |
| 3 | `fiscal_year` | Integer | | `2025` |
| 4 | `fiscal_quarter` | Integer / null | 1-4; null for annual | `2` |
| 5 | `segment` | String | Default `"Total"` | `"Services"` |
| 6 | `low` | Float / null | | `94.0` |
| 7 | `mid` | Float / null | Computed if low+high given | `95.5` |
| 8 | `high` | Float / null | | `97.0` |
| 9 | `unit` | String | Canonical (see [§8](#8-unit-canonicalization)) | `"m_usd"` |
| 10 | `basis_norm` | String | `gaap`, `non_gaap`, `constant_currency`, `unknown` | `"non_gaap"` |
| 11 | `basis_raw` | String / null | Verbatim basis text | `"adjusted"` |
| 12 | `derivation` | String | See [§5](#5-derivation-rules) | `"calculated"` |
| 13 | `qualitative` | String / null | Non-numeric guidance text | `"low to mid single digits"` |
| 14 | `quote` | String | Max 500 chars, verbatim | `"We expect revenue between..."` |
| 15 | `section` | String | Location within source | `"CFO Prepared Remarks"` |
| 16 | `source_key` | String | Sub-document key | `"EX-99.1"`, `"full"`, `"title"`, `"MD&A"` |
| 17 | `conditions` | String / null | Conditional assumptions | `"assumes no further rate hikes"` |
| 18 | `source_type` | String | `8k`, `transcript`, `news`, `10q`, `10k` | `"transcript"` |
| 19 | `created` | String | ISO timestamp of node creation | `"2026-02-18T14:30:00Z"` |

**Rule**: No citation = no node. Every GuidanceUpdate MUST have `quote`, `FROM_SOURCE`, and `given_date`.

---

## 3. Deterministic IDs

No UUIDs, no sequences. All writes use `MERGE` on `id`.

### Guidance ID

```
guidance_id = "guidance:" + slug(label)
```

`slug()` = lowercase, trim, replace non-alphanumeric with `_`, collapse repeated `_`, trim edge `_`.

### GuidanceUpdate ID

```
guidance_update_id = "gu:" + source_id + ":" + label_slug + ":" + period_u_id
                     + ":" + basis_norm + ":" + segment_slug + ":" + evhash16
```

### Evidence Hash

```
evhash16 = sha256("{low}|{mid}|{high}|{unit}|{qualitative}|{conditions}")[:16]
```

Rules:
- Numeric parts: canonical decimal strings after unit normalization
- Aggregate currency metrics normalize to `m_usd` before hashing
- Per-share currency metrics (EPS, DPS) normalize to `usd`
- Percentages normalize to `percent` or `percent_yoy`
- `unit` is lowercase canonical enum value
- Text parts: lowercase + trimmed + whitespace-collapsed
- Nulls encoded as `.` (dot)

### Canonicalization Before ID Build

| Component | Rule |
|-----------|------|
| `source_id` | Trim whitespace. If contains `:`, replace with `_` for delimiter safety. |
| `label_slug` | `label.lower().replace(" ", "_")` |
| `segment_slug` | `segment.lower().replace(" ", "_")` (default `total`) |
| `basis_norm` | Enum as-is: `gaap\|non_gaap\|constant_currency\|unknown` |
| `period_u_id` | From resolved Context (e.g., `duration_2025-09-28_2025-12-27`) |

### Idempotency

- Same source + same slot + same values = same `id` (no-op)
- Same source + same metric but different period/basis/segment = different `id`
- Same source + same slot but changed values/conditions = different `id`

### Implementation

Use `guidance_ids.py:build_guidance_ids()` as single entry point. Do not duplicate ID logic.

---

## 4. Metric Normalization

12 canonical metrics. LLM creates new Guidance nodes for metrics not in this table.

| Standard Label | Variants |
|----------------|----------|
| `Revenue` | revenue, sales, net revenue, total revenue, net sales |
| `EPS` | EPS, earnings per share, diluted EPS |
| `Gross Margin` | gross margin, GM, gross profit margin |
| `Operating Margin` | operating margin, op margin |
| `Operating Income` | operating income, income from operations |
| `Net Income` | net income, net earnings, bottom line |
| `OpEx` | operating expenses, SG&A, R&D + SG&A |
| `Tax Rate` | effective tax rate, tax rate, provision for income taxes |
| `CapEx` | capital expenditures, capex, capital spending |
| `FCF` | free cash flow, operating cash flow minus capex |
| `OINE` | other income and expense, other income/expense net |
| `D&A` | depreciation and amortization, D&A, depreciation |

Aliases are stored on the Guidance node in `aliases[]`. Non-exhaustive — company-specific metrics (e.g., "Services Revenue" for AAPL) are created dynamically.

---

## 5. Derivation Rules

| Derivation | When | Example | Numeric Fields |
|------------|------|---------|----------------|
| `explicit` | Company states exact range | "revenue of $94-97B" | low, mid, high populated |
| `calculated` | Derived from stated values | GM% = guided gross profit / guided revenue | low, mid, high computed |
| `point` | Single number, no range | "CapEx of approximately $2B" | low = mid = high |
| `implied` | Qualitative or partial info | "low to mid single digits" | low/mid/high null; `qualitative` populated |
| `floor` | Lower bound only | "at least $150M" | `low=150`, mid/high null |
| `ceiling` | Upper bound only | "up to $500M" | `high=500`, low/mid null |
| `comparative` | Relative/anchor phrasing | "roughly in line with Q2" | Numeric fields null; anchor in `qualitative`/`conditions` |

Rules:
- `floor`/`ceiling` do NOT force fabricated midpoints
- `comparative` keeps numeric fields null unless explicitly stated
- When `derivation=calculated` and a range is given: `mid = (low + high) / 2`
- When `derivation=implied`: never invent numeric values

---

## 6. Basis Rules

### Assignment Rule

`basis_norm` is assigned ONLY when the basis qualifier is explicit in the same sentence/span as the guidance value. Otherwise default to `unknown`.

### Canonical Values

| basis_norm | Maps From |
|------------|-----------|
| `gaap` | GAAP, as reported, as-reported |
| `non_gaap` | non-GAAP, adjusted, excluding special items, core |
| `constant_currency` | constant currency, FX-neutral |
| `unknown` | No explicit qualifier in quote span |

### Tracking

- `basis_norm`: canonical enum value (stored, used in ID)
- `basis_raw`: verbatim qualifier text from source (stored, not in ID)

### Trap: Implicit Basis Switches

CFO may switch between GAAP and non-GAAP within the same paragraph. Each metric gets its own basis determination from its own quote span:

```
"On a GAAP basis, we expect EPS of $3.20. And revenue should be about $95 billion."
```

Here: EPS = `gaap`, Revenue = `unknown` (no explicit qualifier for revenue).

### Query-Time Safety

Mixed bases may appear in the same metric history. Never compare consecutive values without filtering by `basis_norm` first.

---

## 7. Segment Rules

### Defaults

- Default segment: `Total` (company-wide)
- Only assign segment when explicitly stated in source text
- Use exact wording from source for non-standard segments

### XBRL Member Matching

When segment is not `Total`, attempt to link to XBRL Member nodes:
1. Normalize both sides: lowercase, trim, remove tokens `member`/`segment`, light singularization (`services`->`service`, `products`->`product`)
2. Match against cached member labels (from warmup cache 2B in QUERIES.md)
3. Require exact unique normalized match
4. Write one `MAPS_TO_MEMBER` edge per confident match
5. Multiple members across different axes are valid (e.g., product + geography)
6. No confident match = no member edge (keep `segment='Total'` semantics)

---

## 8. Unit Canonicalization

### Canonical Units

```
usd, m_usd, percent, percent_yoy, percent_points, basis_points, x, count, unknown
```

### Alias Map

| Raw | Canonical |
|-----|-----------|
| `$`, `dollars`, `per share` | `usd` |
| `b usd`, `b_usd`, `billion` | `m_usd` |
| `m usd`, `million` | `m_usd` |
| `%`, `pct` | `percent` |
| `% yoy`, `yoy` | `percent_yoy` |
| `bps`, `bp` | `basis_points` |
| `% points`, `pp`, `percentage points` | `percent_points` |
| `times`, `ratio` | `x` |

### Scale Normalization

- Aggregate currency metrics (Revenue, Net Income, OpEx, CapEx, FCF, etc.) normalize to `m_usd`
- Per-share metrics (EPS, DPS) normalize to `usd`
- `$1.13B` and `1130 M USD` both → `1130` in `m_usd`
- Percentages → `percent` or `percent_yoy` only

### Unknown Handling

No alias match → `unit = 'unknown'`, raw unit preserved in `unit_raw` property on GuidanceUpdate. `unit_raw` is NOT part of `evhash16` (canonical `unit` is used).

### Implementation

Use `guidance_ids.py:canonicalize_unit()`. Adding new units: one entry in `CANONICAL_UNITS` + alias(es) in `UNIT_ALIASES` + test case.

---

## 9. Period Resolution

### Period Scenario Table

Every GuidanceUpdate MUST have `IN_CONTEXT`. Synthetic XBRL-identical Contexts are created for ALL scenarios:

| Scenario | Example Text | period_u_id | start/end | Action |
|----------|-------------|-------------|-----------|--------|
| Specific quarter | "Q3 FY2025" | `duration_2025-06-29_2025-09-27` | Exact fiscal dates | Reuse existing or CREATE |
| Annual | "fiscal year 2025" | `duration_2024-09-29_2025-09-27` | Full fiscal year | Reuse existing or CREATE |
| Half year | "second half" | `duration_2025-03-30_2025-09-27` | Best-effort from FYE | CREATE synthetic |
| Long-range (year) | "by 2028" | `other_long_range_2028` | null / null | CREATE synthetic |
| Long-range (span) | "2026 to 2028" | `other_long_range_2026_2028` | null / null | CREATE synthetic |
| Medium-term | "over the medium term" | `other_medium_term` | null / null | CREATE synthetic |
| No period | (implicit/unclear) | `undefined` | null / null | CREATE synthetic |

### Fiscal Date Resolution

Do NOT perform fiscal date math in the LLM. Use code-only path:

1. Pre-fetch Period nodes via QUERIES.md query 1C
2. Pipe to `fiscal_resolve.py` via Bash:
   ```bash
   echo '$periods_json' | python3 .claude/skills/earnings-orchestrator/scripts/fiscal_resolve.py \
     $TICKER $FISCAL_YEAR $FISCAL_QUARTER $FYE_MONTH
   ```
3. Returns: `{"start_date": "...", "end_date": "...", "period_u_id": "duration_...", "source": "lookup|fallback"}`

### Calendar-to-Fiscal Mapping

When source uses calendar names ("December quarter"), use FYE to determine fiscal quarter.

**Rule**: Q1 starts in FYE month + 1. When source says "Q1" or "Q2" explicitly, use as-is.

| FYE Month | Example | Q1 | Q2 | Q3 | Q4 |
|-----------|---------|----|----|----|----|
| 9 (Sep) | Apple | Oct-Dec | Jan-Mar | Apr-Jun | Jul-Sep |
| 12 (Dec) | Most | Jan-Mar | Apr-Jun | Jul-Sep | Oct-Dec |
| 6 (Jun) | Microsoft | Jul-Sep | Oct-Dec | Jan-Mar | Apr-Jun |

Apple FYE=Sep example: Q1=Oct-Dec, Q2=Jan-Mar, Q3=Apr-Jun, Q4=Jul-Sep.

---

## 10. Context Resolution

### Steps

```
1. FYE: Query 1B (QUERIES.md) → extract FYE month from periodOfReport
2. Period dates: fiscal_resolve.py (pre-fetched Period nodes + fiscal params)
3. Compute IDs:
   period_u_id = "duration_{start}_{end}" (or special: "other_medium_term", etc.)
   ctx_u_id = "guidance_{cik}_{period_u_id}"
4. MERGE Context + Period (via guidance_writer.py)
5. MERGE Unit (via guidance_writer.py)
```

### Context Properties

| Property | Type | Source |
|----------|------|--------|
| `id` / `u_id` / `context_id` | String | All set to `ctx_u_id` |
| `cik` | String | From Company node |
| `period_u_id` | String | From resolved period |
| `member_u_ids` | String[] | Empty for total |
| `dimension_u_ids` | String[] | Empty for total |

### Unit Node Properties

| Property | Type | Example |
|----------|------|---------|
| `id` / `u_id` | String | `guidance_unit_m_usd` |
| `canonical_unit` | String | `m_usd` |

Rule: `u_id = "guidance_unit_" + canonical_unit`. Do not reuse raw XBRL units when scale differs.

---

## 11. XBRL Matching

All linking is inline in the same extraction run. Mapping failures never block core writes.

### Concept Resolution (sets `xbrl_qname`)

No `MAPS_TO_CONCEPT` edge. Uses `xbrl_qname` string property on GuidanceUpdate.

**Why qname**: stable across taxonomy years. Same logical concept has separate Concept nodes per year, but qname never changes.

### Concept Pattern Map

| Guidance Label | qname include | qname exclude |
|----------------|---------------|---------------|
| `Revenue` | `Revenue` | `RemainingPerformanceObligation` |
| `EPS` | `EarningsPerShareDiluted` | — |
| `Gross Margin` | `GrossProfit` | — |
| `Operating Margin` | — | — (derived, no concept) |
| `Operating Income` | `OperatingIncomeLoss` | — |
| `Net Income` | `NetIncome`, `ProfitLoss` | — |
| `OpEx` | `OperatingExpenses` | — |
| `Tax Rate` | `EffectiveIncomeTaxRate` | — |
| `CapEx` | `PaymentsToAcquirePropertyPlantAndEquipment` | — |
| `FCF` | — | — (derived, no concept) |
| `OINE` | `OtherNonoperatingIncomeExpense` | — |
| `D&A` | `DepreciationAmortization` | — |

### Concept Resolution Gate

1. Pattern-match against concept usage cache (QUERIES.md query 2A)
2. Exactly one match → use it
3. Multiple matches → highest usage count wins
4. Zero matches → `xbrl_qname = null`
5. Mapping is **basis-independent** (GAAP, non-GAAP, unknown all get mapped)
6. Set via `ON CREATE SET` only

### Member Matching Gate

1. Extract segment candidates from quote/LLM output
2. Normalize both sides (see [§7](#7-segment-rules))
3. Match against member profile cache (QUERIES.md query 2B)
4. Write `MAPS_TO_MEMBER` edge only for confident matches
5. Allow 0..N member edges per GuidanceUpdate

### Warmup Caches

Run once per company per extraction run. See QUERIES.md queries 2A (concept cache) and 2B (member cache).

---

## 12. Source Processing

### Source Types and Richness

| Source | Richness | Extract? |
|--------|----------|----------|
| Transcript | Highest | YES — full scan (PR + Q&A) |
| 8-K EX-99.* + Item text | High | YES — outlook/tables/footnotes |
| News | Medium | YES — after channel filter |
| 10-Q/10-K MD&A | Low | YES — MD&A primary, bounded fallback |
| XBRL | None | NO — actuals only |

### Routing

Extraction MUST route by `source_type` before LLM processing. Each type has different scan scope and noise profiles. Per-source profiles in `reference/`:

| Source Type | Profile |
|-------------|---------|
| `transcript` | [PROFILE_TRANSCRIPT.md](reference/PROFILE_TRANSCRIPT.md) |
| `8k` | [PROFILE_8K.md](reference/PROFILE_8K.md) |
| `news` | [PROFILE_NEWS.md](reference/PROFILE_NEWS.md) |
| `10q`, `10k` | [PROFILE_10Q.md](reference/PROFILE_10Q.md) |

### Source Type Mapping

| source_type | source_key | given_date source |
|-------------|------------|-------------------|
| `8k` | `"EX-99.1"`, `"Item 2.02"`, `"Item 7.01"` | `r.created` |
| `transcript` | `"full"` | `t.conference_datetime` |
| `news` | `"title"` | `n.created` |
| `10q` | `"MD&A"` | `r.created` |
| `10k` | `"MD&A"` | `r.created` |

### Guidance Keywords

| Category | Keywords |
|----------|----------|
| Forward-looking | expects, anticipates, projects, forecasts, outlook, looking ahead |
| Guidance | guidance, range, target, between X and Y, approximately |
| Periods | Q1-Q4, full year, fiscal year, FY, for the quarter, second half |
| Metrics | EPS, earnings per share, revenue, sales, margin, income, cash flow |
| Revisions | raises, lowers, maintains, reaffirms, withdraws, narrows, widens |
| Qualitative | low single digits, double-digit, mid-teens, high single digits |
| Conditional | assumes, contingent on, excluding, subject to |

### Dedup Rule

Deterministic `GuidanceUpdate.id` enforces dedup. Same slot + same values → same ID → MERGE no-op. Changed values/qualifiers/conditions → different ID → new node.

---

## 13. Quality Filters

Applied AFTER extraction, BEFORE writing to graph:

| Filter | Rule |
|--------|------|
| **Forward-looking only** | Target period must be after source date. Past-period results are actuals, not guidance. |
| **Specificity required** | Qualitative guidance needs a quantitative anchor: "low single digits", "double-digit", "mid-teens". Skip vague terms ("significant", "strong") without magnitude. |
| **No fabricated numbers** | If guidance is qualitative, use `derivation=implied`/`comparative`. Never invent numeric values. |
| **Quote max 500 chars** | Truncate at sentence boundary with "..." if needed. |
| **100% recall priority** | When in doubt, extract it. False positives > missed guidance. |
| **News: company guidance only** | Ignore analyst estimates ("Est $X", "consensus $Y"). Extract only company-issued guidance. |

---

## 14. Chronological Ordering

GuidanceUpdate nodes do NOT maintain NEXT/PREVIOUS edges.

### Ordering Rule

All time-based reads MUST use:
```cypher
ORDER BY gu.given_date, gu.id
```
Or latest-first:
```cypher
ORDER BY gu.given_date DESC, gu.id DESC
```

No linked-list maintenance. No supersession chains. No action classification storage. Latest by `given_date` (tie-break `id`) is current. First in timeline is implicit anchor.

---

## 15. Write Path

### Extraction Pipeline

```
1. LOAD CONTEXT
   ├── Company + CIK (QUERIES.md 1A)
   ├── FYE from 10-K (QUERIES.md 1B)
   ├── Period pre-fetch (QUERIES.md 1C)
   ├── Warmup caches (QUERIES.md 2A, 2B)
   └── Existing Guidance tags (QUERIES.md 7A)

2. LLM EXTRACTION (routed by source_type profile)
   ├── Fetch source content (QUERIES.md §3-§6)
   ├── Route to per-source profile (reference/PROFILE_*.md)
   ├── Feed: source content + existing Guidance tags + member candidates
   └── Extract: quote, period intent, basis, metric, values, derivation, XBRL candidates

3. DETERMINISTIC VALIDATION (pre-write)
   ├── Canonicalize unit + numeric scale (guidance_ids.py)
   ├── Validate basis rule (explicit-only)
   ├── Resolve period_u_id (fiscal_resolve.py)
   ├── Resolve xbrl_qname from concept cache
   ├── Apply member confidence gate
   └── Uncertain? Keep core write, set xbrl_qname=null, skip member edges

4. PER ITEM: WRITE TO GRAPH (via guidance_writer.py)
   ├── Compute IDs (guidance_ids.py:build_guidance_ids)
   ├── MERGE Guidance node
   ├── MERGE Context + Period
   ├── MERGE Unit
   ├── MERGE GuidanceUpdate + all links
   └── Link XBRL members if confident
```

### Idempotency

Compute deterministic ID first, then MERGE. If node exists, treat as no-op. No pre-check queries needed.

### Reprocessing

Delete all GuidanceUpdates for a company (via `guidance_writer.py --purge`) → re-run initial build. Source documents remain in Neo4j.

---

## 16. Execution Modes

### Invocation

```
/guidance-inventory {TICKER} {SOURCE_TYPE} {SOURCE_ID}
/guidance-inventory {TICKER} initial
```

| Parameter | Type | Examples |
|-----------|------|---------|
| `TICKER` | String | `AAPL`, `MSFT` |
| `SOURCE_TYPE` | Enum | `8k`, `transcript`, `news`, `10q`, `10k`, `initial` |
| `SOURCE_ID` | String | `0001193125-25-000001`, `AAPL_2025-07-31T...`, `bzNews_50123456` |

### Mode Parameter

| Mode | Behavior |
|------|----------|
| `dry_run` (default) | Extract + validate + ID build. Log to stdout. No writes. |
| `shadow` | Same as dry_run + log exact MERGE Cypher with parameters. |
| `write` | Full execution. MERGE to Neo4j. |

### Two-Layer Write Gate

1. `MODE` parameter (per-invocation) → maps to `dry_run` in `write_guidance_item()`
2. `ENABLE_GUIDANCE_WRITES` (global feature flag, default `False`) → checked after dry_run, before write

Both must be permissive for writes to occur. `MODE=write` with `ENABLE_GUIDANCE_WRITES=False` still blocks.

### Must-Pass Gates Before Enabling Writes

1. `test_guidance_ids.py` passes
2. Shadow run on 3+ companies and 3+ source types
3. Idempotency: same source twice → zero new nodes on second run
4. Regression: existing ingest behavior unchanged
5. Canary: 1-2 tickers first, then full rollout

---

## 17. Error Taxonomy

| Error | When |
|-------|------|
| `SOURCE_NOT_FOUND` | No rows from source content query |
| `EMPTY_CONTENT` | Rows exist but content empty (rules per source type below) |
| `QUERY_FAILED` | Cypher error |
| `NO_GUIDANCE` | Content parsed, no forward-looking guidance found |
| `WRITE_FAILED` | Graph MERGE error |
| `VALIDATION_FAILED` | Missing citation, bad period, invalid unit |

### Empty-Content Rules per Source Type

| Source Type | Empty Condition |
|-------------|----------------|
| `8k` (exhibit/section/filing_text) | `strip() == ""` |
| `transcript` | BOTH `prepared_remarks` empty AND `qa_exchanges` empty |
| `news` | BOTH `title` and `body` empty |
| `10q`/`10k` | MD&A section `strip() == ""` |

### Handling

- `SOURCE_NOT_FOUND` or `EMPTY_CONTENT`: log error code + source details, return
- `NO_GUIDANCE`: acceptable — not all filings contain guidance
- `WRITE_FAILED`: log error, do not retry automatically
- `VALIDATION_FAILED`: log details, skip item, continue with remaining

---

## 18. Reference Files

| File | Purpose |
|------|---------|
| [QUERIES.md](QUERIES.md) | Read-only Cypher reference (~42 queries) |
| [reference/PROFILE_TRANSCRIPT.md](reference/PROFILE_TRANSCRIPT.md) | Transcript extraction profile |
| [reference/PROFILE_8K.md](reference/PROFILE_8K.md) | 8-K extraction profile |
| [reference/PROFILE_NEWS.md](reference/PROFILE_NEWS.md) | News extraction profile |
| [reference/PROFILE_10Q.md](reference/PROFILE_10Q.md) | 10-Q/10-K extraction profile |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `guidance_ids.py` | ID normalization, unit canonicalization, evhash16 |
| `fiscal_resolve.py` | Fiscal-to-calendar date resolution (CLI wrapper) |
| `guidance_writer.py` | Direct Cypher write path (MERGE patterns) |

---

*Version 2.2 | 2026-02-21 | Fixed: existing guidance query ref 8A→7A (was wrong section). Updated query count (~42). Prior: removed predictor refs, write path → guidance_writer.py, deleted FISCAL_CALENDAR.md.*
