# Guidance Extraction Contract

Core schema, fields, validation rules, and write path for guidance extraction. Loaded as reference by extraction agents.

# Guidance Inventory — Core Reference

Graph-native guidance extraction system. Writes `Guidance` and `GuidanceUpdate` nodes to Neo4j. No markdown output, no file accumulation.

**Thinking**: ALWAYS use `ultrathink` for maximum reasoning depth when extracting and classifying guidance.

**NON-EXHAUSTIVE LISTS**: Every list in this document (metrics, keywords, concepts, instant labels) is a starting set of common examples — NOT a filter. Extract guidance for ANY metric you find, even if unlisted. Create new labels freely. Set `xbrl_qname=null` when no concept matches.


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
10. [Company + Period Resolution](#10-company--period-resolution-v30)
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

### Nodes

**Created by guidance**: `Guidance` (generic metric tag), `GuidanceUpdate` (per-mention data point), `GuidancePeriod` (calendar-based, `gp_` namespace)
**Reused (MATCH only)**: `Company`, `Concept`, `Member`, `Report` / `Transcript` / `News`
**Removed**: `Context` (replaced by direct `FOR_COMPANY` edge), `Unit` (demoted to `canonical_unit` property)

### Relationship Map (6 edges)

| From | Rel | To | When |
|------|-----|----|------|
| GuidanceUpdate | UPDATES | Guidance | Always |
| GuidanceUpdate | FROM_SOURCE | Report / Transcript / News | Always (provenance) |
| GuidanceUpdate | FOR_COMPANY | Company | Always (direct, replaces Context) |
| GuidanceUpdate | HAS_PERIOD | GuidancePeriod | Always (calendar-based, 1:1 cardinality) |
| GuidanceUpdate | MAPS_TO_CONCEPT | Concept | 0..1 when xbrl_qname resolves |
| GuidanceUpdate | MAPS_TO_MEMBER | Member | 0..N confident segment matches |

### Constraints

```cypher
CREATE CONSTRAINT guidance_id_unique IF NOT EXISTS
FOR (g:Guidance) REQUIRE g.id IS UNIQUE;

CREATE CONSTRAINT guidance_update_id_unique IF NOT EXISTS
FOR (gu:GuidanceUpdate) REQUIRE gu.id IS UNIQUE;

CREATE CONSTRAINT guidance_period_id_unique IF NOT EXISTS
FOR (gp:GuidancePeriod) REQUIRE gp.id IS UNIQUE;
```

Sentinel nodes (pre-created via `create_guidance_constraints()`):
```cypher
(:GuidancePeriod {id: 'gp_ST',    u_id: 'gp_ST',    start_date: null, end_date: null})
(:GuidancePeriod {id: 'gp_MT',    u_id: 'gp_MT',    start_date: null, end_date: null})
(:GuidancePeriod {id: 'gp_LT',    u_id: 'gp_LT',    start_date: null, end_date: null})
(:GuidancePeriod {id: 'gp_UNDEF', u_id: 'gp_UNDEF', start_date: null, end_date: null})
```

### Guidance Node Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | `guidance:{slug(label)}` |
| `label` | String | Normalized metric name |
| `aliases` | String[] | Alternate names |
| `created_date` | String | ISO date when first detected |

### GuidanceUpdate Node Properties

All 20 extraction fields (see [S2](#2-extraction-fields)) plus system identity properties:

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Deterministic key (see [S3](#3-deterministic-ids)) |
| `evhash16` | String | First 16 hex chars of evidence hash |
| `xbrl_qname` | String / null | Resolved XBRL concept qname (see [S11](#11-xbrl-matching)) |
| `concept_family_qname` | String / null | Canonical XBRL concept family anchor (CLI-computed, do not set) |
| `unit_raw` | String / null | Verbatim unit text, only when `canonical_unit='unknown'` |
| `label` | String | Metric name (denormalized from Guidance parent) |
| `label_slug` | String | `slug(label)` — enables `WHERE gu.label_slug = 'revenue'` without JOIN |
| `segment_slug` | String | `slug(segment)` — enables `WHERE gu.segment_slug = 'iphone'` |
| `source_refs` | String[] | IDs of sub-source nodes (per intersection file). Empty array if none. |

---

## 2. Extraction Fields

Every GuidanceUpdate carries these 20 properties. System identity properties (`id`, `evhash16`) are added at write time.

| # | Field | Type | Constraint | Example |
|---|-------|------|------------|---------|
| 1 | `given_date` | String | ISO timestamp (UTC), derived from source node at write time | `"2025-01-30T21:05:54Z"` |
| 2 | `period_scope` | String | `quarter`, `annual`, `half`, `monthly`, `long_range`, `short_term`, `medium_term`, `long_term`, `undefined` | `"quarter"` |
| 3 | `time_type` | String | `duration` (default ~99%), `instant` (balance-sheet items only) | `"duration"` |
| 4 | `fiscal_year` | Integer | | `2025` |
| 5 | `fiscal_quarter` | Integer / null | 1-4; null for annual | `2` |
| 6 | `segment` | String | Default `"Total"` | `"Services"` |
| 7 | `low` | Float / null | | `94.0` |
| 8 | `mid` | Float / null | Computed if low+high given | `95.5` |
| 9 | `high` | Float / null | | `97.0` |
| 10 | `canonical_unit` | String | Canonical: `usd`, `m_usd`, `percent`, `percent_yoy`, `percent_points`, `basis_points`, `x`, `count`, `unknown` (see [S8](#8-unit-canonicalization)) | `"m_usd"` |
| 11 | `basis_norm` | String | `gaap`, `non_gaap`, `constant_currency`, `unknown` | `"non_gaap"` |
| 12 | `basis_raw` | String / null | Verbatim basis text | `"adjusted"` |
| 13 | `derivation` | String | See [S5](#5-derivation-rules) | `"calculated"` |
| 14 | `qualitative` | String / null | What management expects (the prediction itself) | `"low to mid single digits"` |
| 15 | `quote` | String | Max 500 chars, verbatim | `"We expect revenue between..."` |
| 16 | `section` | String | Location within source | `"{section_identifier}"` |
| 17 | `source_key` | String | Sub-document key | `"{per intersection file}"` |
| 18 | `conditions` | String / null | Stated "if/assuming/excluding" caveats that qualify it | `"assumes no further rate hikes"` |
| 19 | `source_type` | String | Matches `{ASSET}`. Extensible — add values as new source types are created. | `"transcript"` |
| 20 | `created` | String | ISO timestamp of node creation | `"2026-02-18T14:30:00Z"` |

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
                     + ":" + basis_norm + ":" + segment_slug
```

The ID is the **slot** — it identifies WHICH guidance item, not WHAT it says. One node per metric per source per period per basis per segment. No value hash in the ID.

### Evidence Hash (stored property, not in ID)

```
evhash16 = sha256("{low}|{mid}|{high}|{unit}|{qualitative}|{conditions}")[:16]
```

Stored as `gu.evhash16` property for query-time change detection across sources. NOT part of `guidance_update_id`.

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
| `period_u_id` | Calendar-based: `gp_YYYY-MM-DD_YYYY-MM-DD` or sentinel `gp_ST`/`gp_MT`/`gp_LT`/`gp_UNDEF` |

### Idempotency & Enrichment

- Same source + same slot = same `id` → MERGE matches → SET updates properties (latest write wins)
- Same source + same metric but different period/basis/segment = different `id`
- Different source + same metric = different `id` (different `source_id`)
- Re-run with richer data → same ID → properties overwritten with better values

### Implementation

Use `guidance_ids.py:build_guidance_ids()` as single entry point. Do not duplicate ID logic.

---

## 4. Metric Normalization

12 canonical metrics below are common examples — create new base metrics freely for any company-specific or industry-specific metric not listed here.

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

Aliases are stored on the Guidance node in `aliases[]`. Non-exhaustive — new base metrics not in this table (e.g., "Installed Base", "ARPU") are created as-is with `segment="Total"` (see "No qualifier" in Metric Decomposition below).

### Metric Decomposition

When source text qualifies a metric, split into `label` (the base metric) + `segment` (the qualifier):

**Decompose** when the qualifier names a business dimension — a product, geography, business unit, or customer type:
- "iPhone Revenue" → `label="Revenue"`, `segment="iPhone"`
- "North America Operating Income" → `label="Operating Income"`, `segment="North America"`
- "Cloud Services Gross Margin" → `label="Gross Margin"`, `segment="Cloud Services"`

**Do NOT decompose** when the qualifier is an accounting or measurement modifier — it changes *what* is being measured, not *who/where*:
- "Cost of Revenue" → `label="Cost of Revenue"`, `segment="Total"` (different metric than Revenue)
- "Adjusted EBITDA" → `label="Adjusted EBITDA"`, `segment="Total"`
- "Pro Forma EPS" → `label="Pro Forma EPS"`, `segment="Total"`

**No qualifier** — just "Revenue" or "EPS" — set label to the metric as-is, `segment="Total"`.

**Simple test**: Could you have this metric for iPhone AND for Total? If yes, the prefix is a segment — decompose. If the prefix changes the financial definition, keep it whole.

**No-match is OK**: If a qualifier doesn't match any Member node, still decompose. Member matching (S7) handles no-match gracefully.

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

- Default segment: `Total` (company-wide, no qualifier)
- Assign segment when source text qualifies a metric with any dimensional qualifier (product, geography, business unit, etc.)

### Extraction

After decomposition (S4), each qualifier becomes a segment label. Set `member_u_ids: []` — the CLI resolves members at write time (see below).

### Member Matching (CLI-Owned)

Member resolution is handled entirely by `guidance_write_cli.py` at write time. Agents set `member_u_ids: []`.

**How it works**:
1. Warmup builds a CIK-based member map (`/tmp/member_map_{TICKER}.json`) — all `Member` nodes for the company by CIK prefix
2. CLI normalizes each item's `segment` text: lowercase, strip whitespace, remove `member`/`segment` tokens, light singularization (`services`→`service`, `products`→`product`, `accessories`→`accessory`)
3. Exact normalized match → populates `member_u_ids` with matching `u_id`(s)
4. No match → no edge. Segment text preserved regardless.
5. In write mode, if precomputed map is missing, falls back to live CIK query (self-healing)

### Multi-Axis

- Members from different axes (e.g., product + geography) are valid together
- `segment` stores human-readable text; `member_u_ids` stores graph links — they're related but independent

---

## 8. Unit Canonicalization

### Canonical Units

```
usd, m_usd, percent, percent_yoy, percent_points, basis_points, x, count, unknown
```

### Alias Map

| Raw | Canonical |
|-----|-----------|
| `$`, `dollars` | `m_usd` (per-share labels like EPS/DPS override to `usd`) |
| `b usd`, `b_usd`, `billion` | `m_usd` |
| `m usd`, `million` | `m_usd` |
| `%`, `pct` | `percent` |
| `% yoy`, `yoy` | `percent_yoy` |
| `bps`, `bp` | `basis_points` |
| `% points`, `pp`, `percentage points` | `percent_points` |
| `times`, `multiple` | `x` |

### Scale Normalization

- Aggregate currency metrics (Revenue, Net Income, OpEx, CapEx, FCF, etc.) normalize to `m_usd`
- Per-share metrics (EPS, DPS) normalize to `usd`
- Share-count metrics (e.g. `Diluted Share Count`, `Share Count`, `Shares Outstanding`) normalize to absolute `count`
- `$1.13B` and `1130 M USD` both → `1130` in `m_usd`
- `4.94 billion shares` → `4940000000` in `count`
- Percentages → `percent` or `percent_yoy` only

### Unknown Handling

No alias match → `canonical_unit = 'unknown'`, raw unit preserved in `unit_raw` property on GuidanceUpdate. `unit_raw` is NOT part of `evhash16` (canonical `canonical_unit` is used).

### Implementation

Use `guidance_ids.py:canonicalize_unit()`. Adding new units: one entry in `CANONICAL_UNITS` + alias(es) in `UNIT_ALIASES` + test case.

---

## 9. Period Resolution

### GuidancePeriod — Calendar-Based, Company-Agnostic

Every GuidanceUpdate has exactly ONE `HAS_PERIOD` edge to a `GuidancePeriod` node. GuidancePeriod uses calendar dates (month boundaries), not fiscal keys. Company-agnostic — two companies covering the same calendar window share the same node.

### period_scope Enum (9 values)

| `period_scope` | GuidancePeriod | Example u_id | Example text |
|---|---|---|---|
| `quarter` | Real calendar dates | `gp_2025-04-01_2025-06-30` | "Q3 revenue of $85B" |
| `annual` | Real calendar dates | `gp_2024-10-01_2025-09-30` | "FY2025 CapEx of $30B" |
| `half` | Real calendar dates | `gp_2025-04-01_2025-09-30` | "Second half margin expansion" |
| `monthly` | Real calendar dates | `gp_2025-03-01_2025-03-31` | "March same-store sales" |
| `long_range` | Real calendar dates | `gp_2026-01-01_2028-12-31` | "By 2028", "2026-2028 target" |
| `short_term` | Sentinel `gp_ST` | `gp_ST` | "In the near term" |
| `medium_term` | Sentinel `gp_MT` | `gp_MT` | "Over the medium term" |
| `long_term` | Sentinel `gp_LT` | `gp_LT` | "Long-term target model of 38-40%" |
| `undefined` | Sentinel `gp_UNDEF` | `gp_UNDEF` | "Going forward" (no temporal anchor) |

First 5 require `_compute_fiscal_dates()`. Last 4 always use sentinels with null dates.

### Python Routing (LLM fields -> period_scope -> calendar dates)

Python evaluates LLM extraction fields in priority order. First match wins:

1. `sentinel_class` set? -> `period_scope = sentinel_class`, `u_id = gp_{abbreviation}`
2. `long_range_end_year` set? -> `period_scope = "long_range"`, compute via `_compute_fiscal_dates()`
3. `month` set? -> `period_scope = "monthly"`, `{year}-{month}-01` to `{year}-{month}-{last_day}`
4. `half` set? -> `period_scope = "half"`, compose from two quarter calls
5. `fiscal_quarter` set? -> `period_scope = "quarter"`, `_compute_fiscal_dates(fye, fy, Qn)`
6. `fiscal_year` set (no quarter)? -> `period_scope = "annual"`, `_compute_fiscal_dates(fye, fy, "FY")`
7. Fallthrough -> `period_scope = "undefined"`, `u_id = "gp_UNDEF"`

At every step: `fye = 12 if calendar_override else company_fye_month`.

For instant items (`time_type == "instant"` or label in known instant set): `start_date = end_date` (period's end date).

Implementation: `guidance_ids.py:build_guidance_period_id()`. Do NOT build period IDs manually.

### GuidancePeriod Node Properties

| Property | Type | Notes |
|---|---|---|
| `id` | String | Same as `u_id` (MERGE key, has uniqueness constraint) |
| `u_id` | String | `gp_{start}_{end}` or `gp_ST`/`gp_MT`/`gp_LT`/`gp_UNDEF` |
| `start_date` | String / null | ISO date, null for sentinels |
| `end_date` | String / null | ISO date, null for sentinels |

### Fiscal Context Rule

In earnings calls and SEC filings, ALL period references are fiscal unless explicitly stated as calendar. "Second half" = fiscal H2. Only use calendar interpretation when text explicitly says "calendar year/quarter" — set `calendar_override: true`.

### Calendar-to-Fiscal Mapping

**Rule**: Q1 starts in FYE month + 1. When source says "Q1" or "Q2" explicitly, use as-is.

| FYE Month | Example | Q1 | Q2 | Q3 | Q4 |
|-----------|---------|----|----|----|----|
| 9 (Sep) | Apple | Oct-Dec | Jan-Mar | Apr-Jun | Jul-Sep |
| 12 (Dec) | Most | Jan-Mar | Apr-Jun | Jul-Sep | Oct-Dec |
| 6 (Jun) | Microsoft | Jul-Sep | Oct-Dec | Jan-Mar | Apr-Jun |

---

## 10. Company + Period Resolution (v3.1)

### Architecture (v3.1 — GuidancePeriod)

No Context node. No Unit node. Direct edges from GuidanceUpdate:

- `FOR_COMPANY` → Company (matched by ticker, replaces IN_CONTEXT → Context → FOR_COMPANY)
- `HAS_PERIOD` → GuidancePeriod (calendar-based, `gp_` namespace)
- `canonical_unit` is a property on GuidanceUpdate (not a separate node)

### Steps

```
1. FYE: Query 1B (queries-common.md) → extract FYE month from periodOfReport
2. Period: build_guidance_period_id(fye_month, fiscal_year, fiscal_quarter, ...) → gp_ format
   - Or: pass LLM fields in JSON payload, CLI computes period via _ensure_period()
3. Unit: canonicalize_unit(unit_raw, label_slug) → stored as gu.canonical_unit property
4. MERGE GuidancePeriod + GuidanceUpdate + edges (via guidance_writer.py)
```

---

## 11. XBRL Matching

All linking is inline in the same extraction run. Mapping failures never block core writes.

### Concept Resolution (sets `xbrl_qname` + `MAPS_TO_CONCEPT` edge)

Dual approach: `MAPS_TO_CONCEPT` edge (graph-native join to XBRL Concept) + `xbrl_qname` property (cross-taxonomy fallback). Both set at extraction time.

**Why both**: The edge enables graph-native joins between guidance and actuals via Concept nodes. The `xbrl_qname` property provides a stable cross-taxonomy fallback — same logical concept has separate Concept nodes per year, but qname never changes. If no Concept node matches, the edge is silently skipped (MATCH fails) but `xbrl_qname` is still written.

### Concept Family (sets `concept_family_qname` — CLI-computed)

For derived/composite metrics that have no exact XBRL concept (EBITDA, FCF, margins, growth rates), the CLI computes `concept_family_qname`: the canonical XBRL concept this metric most closely relates to. Resolution: direct table lookup → suffix strip (`_growth`, `_change`, `_yoy`) → prefix strip (`adjusted_`, `non_gaap_`, etc.) → fallback to `xbrl_qname` → null. Agents do not set this property.

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

This maps the 12 common metrics. For metrics not in this table, use the cache fallback below.

### Concept Resolution Gate

**Two-tier matching** — pattern map first, then cache fallback:

1. **Tier 1 — Pattern map**: Match extracted label against the table above. If a row matches, search concept cache qnames for the include pattern (excluding the exclude pattern). Pick highest usage if multiple matches.
2. **Tier 2 — Cache fallback**: For metrics not in the table, search concept cache `label` and `qname` for a match to the same base business metric. Use a fallback match only when there is exactly one clearly plausible candidate. Do not use fallback for derived/growth/rate/margin/comparative metrics unless the underlying concept is explicitly obvious. If ambiguous or no clear single candidate, set `xbrl_qname = null`.
3. Multiple matches → highest usage count wins
4. Zero matches after both tiers → `xbrl_qname = null`
5. Mapping is **basis-independent** (GAAP, non-GAAP, unknown all get mapped)
6. Set via `ON CREATE SET` only
7. Concept resolution uses the **base metric label** after S4 decomposition, not the qualified name

### Member Matching Gate (CLI-Owned)

Member resolution is entirely CLI-side. Agents extract `segment` text and set `member_u_ids: []`. The CLI:
1. Loads precomputed CIK-based member map (built during warmup, all company Members)
2. Normalizes segment text (see [S7](#7-segment-rules))
3. Matches against normalized member labels
4. Writes `MAPS_TO_MEMBER` edge only for confident matches
5. Allows 0..N member edges per GuidanceUpdate

### Warmup Caches

Run once per company per extraction run. See queries-common.md queries 2A (concept cache), 2B (member diagnostic cache), and Member Map (CIK-based authoritative member lookup).

---

## 12. Source Processing

### Source Types and Richness

Source richness varies by asset type — see asset profiles for characteristics. XBRL contains actuals only (no forward guidance).

### Routing

Extraction MUST route by asset type before LLM processing. Per-source profiles loaded at slot 3 via `assets/{ASSET}.md`.

### Source Type Mapping

Source field mappings (source_key, given_date, source_refs) are defined per asset in the intersection file (slot 4).

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

These keywords are common signals, not an exhaustive filter. Extract guidance regardless of whether the source text uses these specific words.

### Dedup Rule

Deterministic slot-based `GuidanceUpdate.id` enforces dedup. Same slot = same ID → MERGE + SET updates properties.

**Two-pass assets**: Primary pass writes items, enrichment pass updates via MERGE+SET. The enrichment intersection file defines secondary content scope.

**All other source types**: Read all content first, extract the richest version per metric, write once per slot.

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
| **Factors are conditions, not items** | If a forward-looking statement quantifies a factor affecting another guided metric (e.g., FX headwind, week count, commodity cost tailwind), capture it in that metric's `conditions` field — not as a standalone item. A factor already captured in a metric's `conditions` field is already extracted — do not also create a standalone item for it. |
| **Corporate announcements** | Do NOT extract capital allocation announcements (buyback authorizations, investment programs, facility plans) — these belong to the `announcement` extraction type. Dividend-per-share guidance IS extractable. |

---

## 14. Chronological Ordering

GuidanceUpdate nodes do NOT maintain NEXT/PREVIOUS edges.

### Ordering Rule

All time-based reads MUST use:
```cypher
ORDER BY datetime(gu.given_date), gu.id
```
Or latest-first:
```cypher
ORDER BY datetime(gu.given_date) DESC, gu.id DESC
```

No linked-list maintenance. No supersession chains. No action classification storage. Latest by `given_date` (tie-break `id`) is current. First in timeline is implicit anchor.

---

## 15. Write Path

### Extraction Pipeline

```
1. LOAD CONTEXT
   ├── Company + CIK (queries-common.md 1A)
   ├── FYE from 10-K (queries-common.md 1B)
   ├── Warmup caches (queries-common.md 2A, 2B)
   └── Existing Guidance tags (guidance-queries.md 7A)

2. LLM EXTRACTION (routed by asset profile)
   ├── Fetch source content (asset-specific query files)
   ├── Route to per-asset profile (assets/*.md)
   ├── Feed: source content + existing Guidance tags + member candidates
   └── Extract: quote, period intent, basis, metric, values, derivation, XBRL candidates

3. DETERMINISTIC VALIDATION (pre-write)
   ├── Canonicalize unit + numeric scale (guidance_ids.py)
   ├── Validate basis rule (explicit-only)
   ├── Build period via build_guidance_period_id() or pass LLM fields for CLI routing
   ├── Resolve xbrl_qname from concept cache
   ├── Compute concept_family_qname (concept_resolver.py:resolve_concept_family)
   ├── Apply member confidence gate
   └── Uncertain? Keep core write, set xbrl_qname=null, skip member edges

4. PER ITEM: WRITE TO GRAPH (via guidance_writer.py)
   ├── Compute IDs (guidance_ids.py:build_guidance_ids)
   ├── MERGE Guidance node
   ├── MERGE GuidancePeriod (calendar-based, gp_ namespace)
   ├── MERGE GuidanceUpdate + edges (UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD)
   └── Link XBRL concept + members if confident
```

### Idempotency & Enrichment

Compute deterministic slot-based ID first, then MERGE + SET. If node exists, properties are updated with latest extraction (latest write wins). No pre-check queries needed. No delete-before-rerun needed.

### Reprocessing

Only needed if you want to remove ALL prior extractions and start fresh. Delete all GuidanceUpdates for a company → re-run initial build. Source documents remain in Neo4j. For normal re-runs, MERGE + SET handles enrichment automatically.

---

## 16. Execution Modes

### Invocation

```
/extract {TICKER} {ASSET} {SOURCE_ID} TYPE=guidance MODE=write
/extract {TICKER} {ASSET} {SOURCE_ID} TYPE=guidance MODE=dry_run
```

| Parameter | Type | Examples |
|-----------|------|---------|
| `TICKER` | String | `AAPL`, `MSFT` |
| `ASSET` | Enum | Extensible. Current: `transcript`, `8k`, `news`, `10q`, `10k` |
| `SOURCE_ID` | String | `AAPL_2025-07-31T17.00.00-04.00`, `0001193125-25-000001`, `bzNews_50123456` |
| `TYPE` | Enum | `guidance` |
| `MODE` | Enum | `write`, `dry_run` |

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

Empty-content conditions are defined per asset in the asset profile (slot 3).

### Handling

- `SOURCE_NOT_FOUND` or `EMPTY_CONTENT`: log error code + source details, return
- `NO_GUIDANCE`: acceptable — not all filings contain guidance
- `WRITE_FAILED`: log error, do not retry automatically
- `VALIDATION_FAILED`: log details, skip item, continue with remaining

---

## 18. Reference Files

| Pattern | Purpose |
|---------|---------|
| `assets/{ASSET}.md` | Asset profiles |
| `assets/{ASSET}-queries.md` | Asset-specific queries |
| `types/{TYPE}/assets/{ASSET}-{pass}.md` | Intersection files |
| `types/{TYPE}/{TYPE}-queries.md` | Type-specific queries |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `guidance_ids.py` | ID normalization, unit canonicalization, evhash16, `build_guidance_period_id()`, `build_period_u_id()` (deprecated) |
| `guidance_writer.py` | Direct Cypher write path (MERGE patterns, param assembly, validation) |
| `guidance_write_cli.py` | CLI entry point: reads JSON, computes IDs, calls `guidance_writer.py` |
| `guidance_write.sh` | Shell wrapper: activates venv, sets Neo4j env vars matching MCP server |

---

## Member Resolution Architecture (2026-03-11)

Member resolution is **fully CLI-owned**. Agents extract `segment` text and set `member_u_ids: []`.

### Pipeline
1. **Warmup** (`warmup_cache.py`): CIK-based query fetches ALL Member nodes for the company → builds normalized label→u_id map → `/tmp/member_map_{TICKER}.json`
2. **CLI** (`guidance_write_cli.py`): loads precomputed map, normalizes each item's segment, resolves matches
3. **Write-mode fallback**: if precomputed map missing (warmup skipped, /tmp cleaned), CLI builds map via live CIK query (self-healing)
4. **Dry-run**: uses precomputed map only (no Neo4j needed). Graceful skip if map missing.

### Why CLI-Owned
- Agent-side member matching from Query 2B was limited to context-derived members (~30-40% coverage)
- CIK-based lookup is comprehensive (all company Members, 2-3x more)
- Eliminates E4d truncation risk (large cache reads hitting output limits)
- Deterministic Python normalization is more reliable than LLM-side matching

---

*Version 3.1 | 2026-02-26 | v3.1: GuidancePeriod replaces Period — calendar-based (gp_ namespace), company-agnostic, with sentinel nodes (gp_ST/MT/LT/UNDEF). period_type renamed to period_scope (9-value enum). Added time_type field (duration/instant). build_guidance_period_id() replaces build_period_u_id(). fiscal_math.py extracted for clean imports. Prior: v3.0 (removed Context/Unit nodes, 6 edges, fiscal-keyed Period). v2.5 (MAPS_TO_CONCEPT). v2.3 (metric decomposition, segment rules).*
