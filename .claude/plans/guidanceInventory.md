# Guidance System — Implementation Spec

**Version**: 2.2 | 2026-02-20
**Status**: Architecture locked — implementation-ready
**Parent**: `earnings-orchestrator.md`
**Benchmark**: `sampleGuidance_byAgentTeams.md` (AAPL)
**Supersedes**: `guidanceInventory.md` v0 (file-centric), `guidanceWIP.md` v0.2 (pre-graph)

---

## Top Open Decisions (Pin)

These decisions are intentionally pinned at the top so they are resolved before implementation drift.

| Priority | Decision | What Must Be Decided | Status |
|---|---|---|---|
| P0 | Per-asset extraction treatment | See §3 expanded table: scan scope, `given_date` source, `source_key`, dedup rule per asset. | RESOLVED |
| P0 | Trigger model for extraction | Auto-trigger per asset at asset-ready ingest; manual SDK modes retained for backfill/reprocess (`single`, `initial`). Extraction writes, prediction reads. See §10. | RESOLVED |
| P0 | GAAP vs non-GAAP handling | `basis_raw` (verbatim) + `basis_norm` (`gaap`, `non_gaap`, `constant_currency`, `unknown`). No linked-list dependency; query-time partitioning for deterministic comparisons. Default `unknown`. See §2, §8, §9. | RESOLVED |
| P1 | Taxonomy alignment | Merged canonical list (12 metrics). Company-specific metrics created dynamically by LLM. See §4. | RESOLVED |

### Build-First TODOs

- [x] `fiscal_to_dates()` — fiscal→calendar resolver. Implemented in `earnings-orchestrator/scripts/get_quarterly_filings.py`. Lookup-first from existing non-guidance XBRL Period nodes (classified via `period_to_fiscal()`), deterministic `_compute_fiscal_dates()` fallback for future periods not yet in XBRL.
- [ ] Build ID normalization utility — slugging, unit/scale canonicalization, `evhash16`, and `guidance_update_id` assembly.
- [x] `period_to_fiscal()` is already implemented and validated in `earnings-orchestrator/scripts/get_quarterly_filings.py`; reuse it as a validation/helper function only (no reimplementation).

---

## 1. Graph Schema

### Architecture Overview

**New nodes**: `Guidance` (generic metric tag), `GuidanceUpdate` (per-mention data point)
**Reused nodes**: `Context`, `Period`, `Unit`, `Company`, `Concept`, `Member`

**Relationship map** (all from GuidanceUpdate unless noted):

| From | Rel | To | When |
|------|-----|----|------|
| GuidanceUpdate | UPDATES | Guidance | Always |
| GuidanceUpdate | IN_CONTEXT | Context | Always (company+period) |
| GuidanceUpdate | FROM_SOURCE | Report / Transcript / News | Always (provenance) |
| GuidanceUpdate | HAS_PERIOD | Period | Always (same Period linked via Context) |
| GuidanceUpdate | HAS_UNIT | Unit | Always (canonical unit node) |
| GuidanceUpdate | MAPS_TO_MEMBER | Member | If one or more confident segment matches |
| Context | FOR_COMPANY | Company | Always (via cik) |
| Context | HAS_PERIOD | Period | Always |

### Required Constraints

```cypher
CREATE CONSTRAINT guidance_id_unique IF NOT EXISTS
FOR (g:Guidance) REQUIRE g.id IS UNIQUE;

CREATE CONSTRAINT guidance_update_id_unique IF NOT EXISTS
FOR (gu:GuidanceUpdate) REQUIRE gu.id IS UNIQUE;

CREATE CONSTRAINT context_uid_unique IF NOT EXISTS
FOR (ctx:Context) REQUIRE ctx.u_id IS UNIQUE;

CREATE CONSTRAINT period_uid_unique IF NOT EXISTS
FOR (p:Period) REQUIRE p.u_id IS UNIQUE;
```

### XBRL Parallel

| XBRL | Guidance | Role |
|------|----------|------|
| Concept | Guidance | Generic metric definition, not per-company |
| Fact | GuidanceUpdate | Per-mention data point with all values |
| Context | Context (reused!) | Company + period scoping |
| Fact→IN_CONTEXT→Context | GuidanceUpdate→IN_CONTEXT→Context | Same pattern |
| Fact→HAS_CONCEPT→Concept | GuidanceUpdate→UPDATES→Guidance + `xbrl_qname` property | Concept via qname join, not edge |
| Fact→HAS_PERIOD→Period | GuidanceUpdate→HAS_PERIOD→Period | Same direct period shortcut |
| Fact→HAS_UNIT→Unit | GuidanceUpdate→HAS_UNIT→Unit | Same pattern |

### XBRL Reuse Policy (Locked)

Use this policy to avoid drift during implementation:

| Node/Edge | Policy |
|---|---|
| `Context` | Reuse existing XBRL Context when deterministic key matches; otherwise create synthetic XBRL-compatible Context. |
| `Period` | Reuse existing XBRL Period when exact `u_id` match exists; otherwise create synthetic XBRL-compatible Period. |
| `Unit` | Use canonical guidance Unit nodes (for example `guidance_unit_m_usd`, `guidance_unit_usd`, `guidance_unit_percent`); do not directly reuse raw XBRL units when scale semantics differ. |
| `Concept` | No edge. Concept resolution uses `xbrl_qname` property on GuidanceUpdate + query-time qname join. |
| `Member` | Link `GuidanceUpdate -> Member` with 0..N confident matches. |
| `Dimension` / `Domain` | No direct linkage from guidance nodes in this design. |

### Node: Guidance

Conceptually parallel to XBRL `Concept`: generic, company-agnostic. "Revenue" is ONE node shared across all companies.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Deterministic key: `guidance:{slug(label)}` |
| `label` | String | Normalized metric name: "Revenue", "EPS", "Gross Margin", etc. |
| `aliases` | String[] | Alternate names: e.g., ["sales", "net revenue", "total revenue"] |
| `created_date` | String | ISO date when first detected |

Concept resolution uses `xbrl_qname` property on GuidanceUpdate (see §7), not an edge on Guidance. The Guidance node carries only the metric label and aliases.

### Node: GuidanceUpdate

Conceptually parallel to XBRL `Fact`: per-mention data point. See §2 for full field list.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Deterministic readable key: `gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}:{evhash16}` (see §2A) |
| `evhash16` | String | First 16 hex chars of evidence hash from value-bearing fields |
| `xbrl_qname` | String / null | Resolved XBRL concept qname (e.g., `us-gaap:Revenues`). Set at extraction time from concept cache. Null when no confident match. See §7. |

| Relationship | Direction | Target | Condition |
|-------------|-----------|--------|-----------|
| `UPDATES` | OUT | Guidance | Always (parent tag) |
| `FROM_SOURCE` | OUT | Report / Transcript / News | Always (provenance) |
| `IN_CONTEXT` | OUT | Context | Always (company + period) |
| `HAS_PERIOD` | OUT | Period | Always (resolved period) |
| `HAS_UNIT` | OUT | Unit | Always (canonical unit) |
| `MAPS_TO_MEMBER` | OUT | Member | If confident segment match (0..N) |

---

## 2. Extraction Fields

Every GuidanceUpdate node carries these extraction payload properties (19 fields). System identity properties (`id`, `evhash16`) are added at write time per §2A.

| # | Field | Type | Enum / Constraint | Example |
|---|-------|------|-------------------|---------|
| 1 | `given_date` | String | ISO date | `"2025-01-30"` |
| 2 | `period_type` | String | `quarter`, `annual`, `half`, `long-range`, `other` | `"quarter"` |
| 3 | `fiscal_year` | Integer | | `2025` |
| 4 | `fiscal_quarter` | Integer / null | 1-4; null for annual | `2` |
| 5 | `segment` | String | Default `"Total"` | `"Services"` |
| 6 | `low` | Float / null | | `94.0` |
| 7 | `mid` | Float / null | Computed if low+high given | `95.5` |
| 8 | `high` | Float / null | | `97.0` |
| 9 | `unit` | String | Canonical: `usd`, `m_usd`, `percent`, `percent_yoy`, `x`, `count`, `unknown` | `"m_usd"` |
| 10 | `basis_norm` | String | `gaap`, `non_gaap`, `constant_currency`, `unknown` | `"non_gaap"` |
| 11 | `basis_raw` | String / null | Verbatim basis text from source | `"non-GAAP"`, `"adjusted"`, `"as reported"` |
| 12 | `derivation` | String | `explicit`, `calculated`, `point`, `implied`, `floor`, `ceiling`, `comparative` | `"explicit"` |
| 13 | `qualitative` | String / null | Non-numeric guidance text | `"low to mid single digits"` |
| 14 | `quote` | String | Max 500 chars, verbatim from source | `"We expect revenue between..."` |
| 15 | `section` | String | Location within source | `"CFO Prepared Remarks"` |
| 16 | `source_key` | String | Sub-document key | `"EX-99.1"`, `"Item 2.02"`, `"full"`, `"title"`, `"MD&A"` |
| 17 | `conditions` | String / null | Conditional assumptions | `"assumes no further rate hikes"` |
| 18 | `source_type` | String | `8k`, `transcript`, `news`, `10q`, `10k` | `"transcript"` |
| 19 | `created` | String | ISO timestamp of node creation | `"2026-02-18T14:30:00Z"` |

**Basis rules**: `basis_norm` is assigned only when the basis qualifier is explicit for the same metric mention (same sentence/span as the quote). Otherwise default to `unknown`. `adjusted` → `non_gaap`; `as reported`/`as-reported` → `gaap`. Preserve verbatim qualifier in `basis_raw`.

**LLM + validator contract**:
- LLM proposes `basis_norm`, concept/member matches, and extracted values with quote evidence.
- Deterministic validator enforces canonicalization + confidence gates.
- If validation fails: keep core GuidanceUpdate write, fallback `basis_norm='unknown'`, and skip uncertain XBRL links.

**Rule**: No citation = no node. Every GuidanceUpdate must have `quote`, `FROM_SOURCE`, and `given_date`.

### 2A. Deterministic IDs and Idempotency (Required)

Universal rule: Guidance and GuidanceUpdate use deterministic IDs. No UUIDs, no sequences. Writes use `MERGE` on `id`.

Guidance ID:
- `guidance_id = "guidance:" + slug(label)`
- `slug()` = lowercase, trim, replace non-alphanumeric with `_`, collapse repeated `_`, trim edge `_`.

GuidanceUpdate ID (readable + deterministic):
- `guidance_update_id = "gu:" + source_id + ":" + label_slug + ":" + period_u_id + ":" + basis_norm + ":" + segment_slug + ":" + evhash16`
- `source_key` remains a stored property for provenance and is not part of the identity key.

Canonicalization before ID build:
- `source_id` uses the canonical source-node id as stored (trim whitespace only; do not slugify). If `source_id` contains `:`, replace `:` with `_` for delimiter safety.
- `label_slug = label.lower().replace(" ", "_")`
- `segment_slug = segment.lower().replace(" ", "_")` (default `total`)
- `basis_norm` uses enum as-is: `gaap|non_gaap|constant_currency|unknown`
- `period_u_id` comes from resolved Context (`duration_*`, `other_medium_term`, `undefined`, etc.) and is used directly in the ID.
- `evhash16 = sha256("{low}|{mid}|{high}|{unit}|{qualitative}|{conditions}")[:16]` where:
  - numeric parts (`low/mid/high`) are canonical decimal strings after unit normalization
  - aggregate currency metrics normalize to `m_usd` before hashing (`$1.13B` and `1130 M USD` both normalize to `1130|...|m_usd`)
  - per-share currency metrics (e.g., EPS/DPS) normalize to `usd`
  - percentages normalize to `percent` or `percent_yoy` only
  - `unit` is lowercase canonical enum value
  - text parts (`qualitative/conditions`) are lowercase + trimmed + whitespace-collapsed
- Nulls in hash input are encoded as `.` (dot).

Implementation rule:
- Do not duplicate ID logic across source extractors. Use one shared utility function (e.g., `build_guidance_ids_and_hashes(...)`) that performs normalization + `evhash16` + final `guidance_update_id`.

Implementation note:
- Context linkage still uses `IN_CONTEXT -> Context/Period` as canonical period grounding.

Expected behavior:
- Same source + same slot + same values => same `id` (idempotent no-op).
- Same source + same metric but different period/basis/segment => different `id`.
- Same source + same slot but changed values/conditions/qualitative => different `id`.
- Undefined/vague periods still work because `period_u_id` is still deterministic (`undefined`, `other_medium_term`, etc.).

---

## 3. Source Processing

### Source Richness

| # | Source | Richness | Arrives | Extract? | Notes |
|---|--------|----------|---------|----------|-------|
| 1 | Transcript | Highest | t+1d to t+5d | YES — full scan (prepared remarks + Q&A) | Best source. Rare fallback to full transcript text only when prepared/Q&A is missing or truncated. |
| 2 | 8-K EX-99.* + Item text | High | t=0 | YES — EX-99.* outlook/tables/footnotes + Item 2.02/7.01 text | Official numbers. Some companies (AAPL): zero guidance. |
| 3 | News | Medium | t-1h to t+24h | YES — after Benzinga channel filter | Mixes company guidance with analyst estimates. |
| 4 | 10-Q/10-K MD&A | Low | t+25d to t+45d | YES — MD&A primary, bounded fallback if needed | Skip boilerplate. Note new risk language. |
| 5 | XBRL | None | With 10-Q/10-K | NO — actuals only | Predictor uses for accuracy comparison. |
| 6 | Alpha Vantage | Reference | Always | NO — consensus, not guidance | Reference only. |
| 7 | Investor day | Variable | Infrequent | YES — when ingested | Not yet in pipeline. |

### News Channel Filter

Apply BEFORE LLM processing. Use Benzinga `channels` field (JSON string on News node).

| Channel | Count | Filter |
|---------|-------|--------|
| `Guidance` | 21,085 | PRIMARY |
| `Earnings` | 49,344 | PRIMARY |
| `Earnings Beats` | 5,784 | SECONDARY |
| `Earnings Misses` | 2,679 | SECONDARY |
| `Previews` | 587 | SECONDARY |
| `Management` | 4,409 | SECONDARY |

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE (n.channels CONTAINS 'Guidance' OR n.channels CONTAINS 'Earnings'
   OR n.channels CONTAINS 'Previews' OR n.channels CONTAINS 'Management')
  AND n.created >= $start_date AND n.created <= $end_date
RETURN n.id, n.title, n.created, n.channels
ORDER BY n.created
```

Supplementary fulltext search for maximum recall:
```cypher
CALL db.index.fulltext.queryNodes('news_ft', 'guidance OR outlook OR expects OR forecast')
YIELD node, score
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE node.created >= $start_date AND node.created <= $end_date
RETURN node.id, node.title, score ORDER BY score DESC LIMIT 20
```

Full channel/tag reference: `.claude/references/neo4j-news-fields.md`

### Per-Source Extraction Rules

Extraction MUST branch by `source_type` before LLM processing. Each doc asset type has different scan scope, inclusion/exclusion rules, and noise profiles. The extractor routes to the correct profile below based on `SOURCE_TYPE` parameter.

| Source | Scan | Extract | Do NOT extract | `given_date` | `source_key` | Dedup |
|--------|------|---------|----------------|-------------|-------------|-------|
| **8-K** | EX-99.* outlook → tables → footnotes + Item 2.02/7.01 text | Forward-looking numbers, ranges, directional | Pure actuals, pure safe-harbor boilerplate | `r.created` | Exhibit/item key (e.g., `"EX-99.1"`, `"Item 2.02"`) | Deterministic `GuidanceUpdate.id` (§2A) |
| **Transcript** | Everything: CFO, Q&A, CEO (rare fallback: full transcript text node only when prepared/Q&A missing/truncated) | All guidance: formal, segment, caveats, conditions | — | `t.conference_datetime` | `"full"` | Deterministic `GuidanceUpdate.id` (§2A) |
| **News** | Title + body (after channel filter) | Company guidance only | Analyst estimates ("Est $X", "consensus") | `n.created` | `"title"` | Deterministic `GuidanceUpdate.id` (§2A) |
| **10-Q/10-K** | MD&A primary; if zero guidance found, one bounded keyword-window pass in broader filing text | Specific numbers/ranges/directional | Boilerplate/legal/risk-heavy text | `r.created` | `"MD&A"` | Deterministic `GuidanceUpdate.id` (§2A) |

**Dedup rule**: Dedup is enforced by deterministic `GuidanceUpdate.id` (§2A). Same slot + same value payload merges; changed values/qualifiers/conditions create a new node.
**Safe-harbor proximity rule**: Filter disclaimer-only blocks, but do not blindly drop adjacent lines if they contain concrete guidance numbers/periods.

### Forward Guidance Full-Text Recall (All Assets)

Run a common recall pass for forward guidance on every asset, but only within that asset's scoped text from the table above.

- Step 1: Build searchable text from the scoped region only (`EX-99.*` + Item 2.02/7.01 text for 8-K, `MD&A` for 10-Q/10-K, transcript prepared remarks + Q&A, or filtered news title/body).
- Step 2: Find forward-guidance candidate windows with keyword hits (for example: `expects`, `guidance`, `outlook`, `forecast`, `target`, `range`, `raise`, `lower`, `maintain`, `reaffirm`).
- Step 3: Keep candidate windows only if at least one metric/period/value signal is present nearby.
- Step 4: Send candidate windows to LLM extractor.
- Step 5: If zero candidates, run one bounded fallback pass:
  - transcript: use full transcript text node only when prepared/Q&A is missing or truncated
  - 8-K: one broader pass across scoped 8-K text (`EX-99.*` + Item text)
  - 10-Q/10-K: one keyword-window pass in broader filing text excluding legal/risk-heavy sections

This recall step improves coverage; deterministic validation and write logic stay unchanged.

**News reaffirm/paraphrase guardrail**:
- If news language contains reaffirmation verbs (`reaffirm`, `maintain`, `keep`, `unchanged`), annotate reaffirmation in `conditions` (e.g., `reaffirmed`).
- Extract exact values stated in the source; do not rewrite values to prior guidance.
- Deterministic IDs + provenance preserve both history and source-level differences.

### Guidance Keywords

| Category | Keywords |
|----------|----------|
| Forward-looking | expects, anticipates, projects, forecasts, outlook |
| Guidance | guidance, range, target, between X and Y |
| Periods | Q1-Q4, full year, fiscal year, FY, for the quarter |
| Metrics | EPS, earnings per share, revenue, sales, margin, OpEx, CapEx |
| Revisions | raises, lowers, maintains, reaffirms, withdraws |

---

## 4. Metric Normalization

Variant names in source text → standard Guidance label.

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

This is a starting set, not exhaustive. The LLM creates new Guidance nodes for metrics not in this table (e.g., company-specific "Services Revenue" for AAPL). Aliases stored on Guidance node in `aliases[]`.

---

## 5. Derivation Rules

| Derivation | When | Example |
|------------|------|---------|
| `explicit` | Company states exact number or range | "We expect revenue of $94-97B" |
| `calculated` | Derived from explicitly stated values | GM% = (guided gross profit) / (guided revenue) |
| `point` | Single number given, no range | "CapEx of approximately $2B" |
| `implied` | Inferred from qualitative or partial info | "low to mid single digits" → implied range |
| `floor` | Lower bound only | "at least $150M" (`low=150`, `mid/high=null`) |
| `ceiling` | Upper bound only | "up to $500M" (`high=500`, `low/mid=null`) |
| `comparative` | Relative/anchor phrasing, no direct numeric value | "roughly in line with Q2", "mid-teens by FY27" |

Encoding rules:
- `floor`/`ceiling` do not force fabricated midpoints.
- `comparative` keeps numeric fields null unless explicitly stated; anchor meaning stays in `qualitative`/`conditions` and `quote`.

---

## 6. Context Resolution

### Goal

Every GuidanceUpdate links to:
- `IN_CONTEXT -> Context` (company + period scope)
- `HAS_PERIOD -> Period` (direct period edge for fast retrieval)
- `HAS_UNIT -> Unit` (direct canonical unit edge)

Context/Period structure is kept XBRL-compatible so future XBRL ingestion can reuse synthetic contexts.

### Option A (CHOSEN): Reuse XBRL Context label

Create Context nodes **identical to XBRL Context** so future XBRL ingestion can reuse them.

| Context Property | Type | Source | Example |
|-----------------|------|--------|---------|
| `id` | String | Synthetic for guidance | `"guidance_320193_duration_2025-09-28_2025-12-27"` |
| `u_id` | String | Canonical unique key | Same as `id` (XBRL-compatible) |
| `cik` | String | Company node | `"320193"` |
| `context_id` | String | Synthetic for guidance | `"guidance_320193_duration_2025-09-28_2025-12-27"` |
| `period_u_id` | String | Derived from fiscal dates | `"duration_2025-09-28_2025-12-27"` |
| `member_u_ids` | String[] | Empty for total, populated for segments | `[]` |
| `dimension_u_ids` | String[] | Empty for total, populated for segments | `[]` |

For synthetic guidance contexts: set `id = u_id = context_id`.

Must also create or match:
- `(:Context)-[:FOR_COMPANY]->(:Company)` — using cik
- `(:Context)-[:HAS_PERIOD]->(:Period)` — using period dates

### Period Node (reuse or create)

| Period Property | Type | Example |
|----------------|------|---------|
| `id` | String | `"duration_2025-09-28_2025-12-27"` |
| `u_id` | String | `"duration_2025-09-28_2025-12-27"` |
| `period_type` | String | `"duration"` or `"instant"` |
| `start_date` | String | `"2025-09-28"` |
| `end_date` | String | `"2025-12-27"` |

For synthetic guidance periods: set `id = u_id`.

### Unit Node (reuse or create)

| Unit Property | Type | Example |
|---------------|------|---------|
| `id` | String | `"guidance_unit_m_usd"` |
| `u_id` | String | `"guidance_unit_m_usd"` |
| `canonical_unit` | String | `"m_usd"` |

Unit resolution rule:
- Canonicalize `unit` first (§2A).
- Reuse only canonical guidance Unit nodes (for example `guidance_unit_m_usd`, `guidance_unit_percent`).
- Do not map normalized guidance units to raw XBRL units that imply different scale (for example raw `USD` vs normalized `m_usd`).
- Otherwise `MERGE` synthetic guidance unit: `u_id = "guidance_unit_" + canonical_unit`.

### Resolution Steps

```
1. Determine FYE:
   get_derived_fye(ticker) from get_quarterly_filings.py:365
   Resolve company first and read CIK from graph:
     MATCH (company:Company {ticker: $ticker})
     WITH company, company.cik AS cik
   Never accept CIK from external input.

2. Resolve fiscal period → calendar dates:
   fiscal_to_dates(session, ticker, fiscal_year, fiscal_quarter) → (start_date, end_date).
   Two-phase resolver:
    a) Lookup-first: query existing XBRL Period nodes for this company,
       classify each via period_to_fiscal() (get_quarterly_filings.py:66),
       return exact dates if match found. Best for 52/53-week calendars.
    b) Deterministic fallback (for future periods not yet in XBRL):
       compute from fye_month (via get_derived_fye()) + quarter offset
       via `_compute_fiscal_dates()`, with round-trip validation through
       `period_to_fiscal()`. For Q4, if FY exists but quarter candidates
       are sparse, anchor Q4 to FY end and infer quarter length from
       same-FY quarter-like periods (or FY/4 fallback).
   period_to_fiscal() role: validation/classification helper, not on write path.
   LLM must not perform fiscal date math; this step is code-only.

3. Search for existing Context:
   First compute deterministic `period_u_id` from resolved scenario:
     - duration periods: `duration_{start}_{end}`
     - medium/undefined: e.g., `other_medium_term`, `undefined`
   Then compute deterministic context key:
     - `ctx_u_id = "guidance_" + cik + "_" + period_u_id`
   Then match EXACTLY:
   MATCH (ctx:Context {u_id: $ctx_u_id})
   OPTIONAL MATCH (ctx)-[:HAS_PERIOD]->(p:Period {u_id: $period_u_id})
   RETURN ctx, p

4. If found → reuse (link GuidanceUpdate→IN_CONTEXT→existing Context)
   If not found → CREATE Context + Period matching XBRL format exactly:
     MATCH (company:Company {ticker: $ticker})
     WITH company, company.cik AS cik
     MERGE (p:Period {u_id: $period_u_id})
       ON CREATE SET p.id = $period_u_id,
                     p.period_type = $period_node_type,
                     p.start_date = $start,
                     p.end_date = $end
     MERGE (ctx:Context {u_id: $ctx_u_id})
       ON CREATE SET ctx.id = $ctx_u_id,
                     ctx.context_id = $ctx_u_id,
                     ctx.cik = cik,
                     ctx.period_u_id = $period_u_id,
                     ctx.member_u_ids = [],
                     ctx.dimension_u_ids = []
     MERGE (ctx)-[:HAS_PERIOD]->(p)
     MERGE (ctx)-[:FOR_COMPANY]->(company)
```

### Period Scenario Table

Every GuidanceUpdate MUST have `IN_CONTEXT`. Synthetic XBRL-identical Contexts are created for ALL scenarios:

| Scenario | Example text | period_u_id | start/end dates | Action |
|----------|-------------|-------------|-----------------|--------|
| **Specific quarter** | "Q3 FY2025" | `duration_2025-06-29_2025-09-27` | Exact fiscal dates | Reuse existing XBRL Context if match; else CREATE |
| **Annual** | "fiscal year 2025" | `duration_2024-09-29_2025-09-27` | Full fiscal year | Reuse existing XBRL Context if match; else CREATE |
| **Half year** | "second half" | `duration_2025-03-30_2025-09-27` | Best-effort from FYE | CREATE synthetic Context |
| **Vague future** | "next year" | Best-effort from FYE | Derived from fiscal calendar | CREATE synthetic Context |
| **Long-range** | "by 2028" | `other_long_range_2028` (or `other_long_range_2026_2028`) | null / null | CREATE synthetic Context |
| **Medium-term** | "over the medium term" | `other_medium_term` | null / null | CREATE synthetic Context |
| **No period** | (implicit/unclear) | `undefined` | null / null | CREATE synthetic Context (cik still set) |

**Rule**: Every synthetic Context MUST be structurally identical to XBRL Contexts (same label, same properties, same relationships). Future XBRL ingestion can find and reuse them when the actual period arrives.

---

## 7. XBRL Matching

All linking is inline in the same extraction run (no separate process). LLM may propose candidates, but only cache-backed candidates passing deterministic gates are written. Mapping failures never block core Guidance/GuidanceUpdate writes.

### Concept Resolution Design

**No `MAPS_TO_CONCEPT` edge.** Concept resolution uses a `xbrl_qname` string property on GuidanceUpdate.

Why `qname` (not `u_id` or edge):
- `qname` (e.g., `us-gaap:Revenues`) is stable across all taxonomy years. The same logical concept exists as separate Concept nodes per taxonomy year, but qname never changes.
- A property on GuidanceUpdate is naturally company-specific and handles concept transitions (if a company switches from `Revenues` to `RevenueFromContractWithCustomer`, old GuidanceUpdates keep the old qname, new ones get the new — but see Limitation below).
- No cross-company accumulation issues (unlike an edge on the shared Guidance node).
- Null when no confident match — no cleanup needed.

**Limitation**: The concept cache is built from the most recent 10-K + subsequent 10-Qs (not date-aware per extraction). Historical backfills for periods before a concept transition (e.g., pre-ASC 606) will get the current qname, not the historical one. This may cause accuracy comparisons to miss for those periods. Acceptable tradeoff vs. date-aware caching complexity.

### Warmup Caches (Run Once Per Company Per Extraction Run)

Concept cache — query the most recent 10-K plus all subsequent 10-Q filings for the company, **consolidated facts only** (no dimensional members). Scoped to the current taxonomy window so concept transitions (e.g., pre-ASC 606 `Revenues` → `RevenueFromContractWithCustomer`) resolve to the company's current qname:
```cypher
// Step 1: find most recent 10-K filing date
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE rk.formType = '10-K'
WITH c, rk ORDER BY rk.created DESC LIMIT 1
WITH c, rk.created AS last_10k_date
// Step 2: all facts from that 10-K + subsequent 10-Qs
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q']
  AND r.created >= last_10k_date
  AND f.is_numeric = '1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids = [])
WITH con.qname AS qname, count(f) AS usage
ORDER BY usage DESC
RETURN qname, usage
```

Member profile (Context-based; robust when FACT_MEMBER is sparse and CIK padding differs across node families):
```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE size(ctx.dimension_u_ids) > 0 AND size(ctx.member_u_ids) > 0
UNWIND range(0, size(ctx.member_u_ids)-1) AS i
WITH ctx.dimension_u_ids[i] AS dim_u_id, ctx.member_u_ids[i] AS mem_u_id
WHERE dim_u_id IS NOT NULL AND mem_u_id IS NOT NULL
  AND (
    dim_u_id CONTAINS 'Axis'
    OR dim_u_id CONTAINS 'Segment'
    OR dim_u_id CONTAINS 'Product'
    OR dim_u_id CONTAINS 'Geography'
    OR dim_u_id CONTAINS 'Region'
  )
WITH dim_u_id, mem_u_id,
     split(mem_u_id, ':')[0] AS mem_cik_raw
WITH dim_u_id, mem_u_id,
     CASE
       WHEN mem_cik_raw =~ '^[0-9]+$'
       THEN toString(toInteger(mem_cik_raw)) + substring(mem_u_id, size(mem_cik_raw))
       ELSE mem_u_id
     END AS mem_u_id_nopad
MATCH (m:Member)
WHERE m.u_id = mem_u_id OR m.u_id = mem_u_id_nopad
WITH m.qname AS member_qname,
     m.u_id AS member_u_id,
     m.label AS member_label,
     dim_u_id,
     split(dim_u_id, ':') AS dim_parts,
     count(*) AS usage
WITH member_qname,
     member_u_id,
     member_label,
     dim_u_id AS axis_u_id,
     dim_parts[size(dim_parts)-2] + ':' + dim_parts[size(dim_parts)-1] AS axis_qname,
     usage
ORDER BY member_qname, usage DESC
WITH member_qname,
     collect({
       member_u_id: member_u_id,
       member_label: member_label,
       axis_qname: axis_qname,
       axis_u_id: axis_u_id,
       usage: usage
     }) AS versions
RETURN member_qname,
       versions[0].member_u_id AS best_member_u_id,
       versions[0].member_label AS best_member_label,
       versions[0].axis_qname AS best_axis_qname,
       versions[0].axis_u_id AS best_axis_u_id,
       versions[0].usage AS best_usage,
       reduce(total = 0, v IN versions | total + v.usage) AS total_usage
```

Axis coverage rule:
- Axis detection is intentionally open-ended (`CONTAINS 'Axis'` plus broad business hints). Do not maintain a closed hardcoded axis list.
- Confidence-gated member matching is the safeguard against noisy or irrelevant axes.

### Concept Pattern Map (Canonical Metrics)

Use this static map to translate Guidance label to candidate XBRL qnames, then resolve to cached `best_concept_u_id`:

| Guidance Label | qname include pattern(s) | qname exclude pattern(s) | Link rule |
|---|---|---|---|
| `Revenue` | `Revenue` | `RemainingPerformanceObligation` | Link when confidence gate passes |
| `EPS` | `EarningsPerShareDiluted` | — | Link when confidence gate passes |
| `Gross Margin` | `GrossProfit` | — | Link as proxy |
| `Operating Margin` | — | — | No direct concept (derived) |
| `Operating Income` | `OperatingIncomeLoss` | — | Link when confidence gate passes |
| `Net Income` | `NetIncome`, `ProfitLoss` | — | Link when confidence gate passes |
| `OpEx` | `OperatingExpenses` | — | Link when confidence gate passes |
| `Tax Rate` | `EffectiveIncomeTaxRate` | — | Link when confidence gate passes |
| `CapEx` | `PaymentsToAcquirePropertyPlantAndEquipment` | — | Link when confidence gate passes |
| `FCF` | — | — | No direct concept (derived) |
| `OINE` | `OtherNonoperatingIncomeExpense` | — | Link when confidence gate passes |
| `D&A` | `DepreciationAmortization` | — | Link when confidence gate passes |

### Concept Resolution Gate (sets `gu.xbrl_qname`)

For each metric in the pattern map:
1. Find all qnames in the concept cache that match the include pattern(s) and exclude pattern(s).
2. If exactly one qname matches → use it.
3. If multiple match → pick the one with highest usage count from the cache.
4. If zero match → `xbrl_qname = null`.
5. Mapping is **basis-independent**: GAAP, non-GAAP, and unknown guidance all get mapped. Basis filtering happens at comparison query time, not at mapping time.
6. Set on GuidanceUpdate via `ON CREATE SET` only. No implicit re-extraction updates. If concept cache improves, update via a separate migration query, not through re-extraction.

Member links (`GuidanceUpdate -> Member`):
- Allow 0..N member links per GuidanceUpdate.
- Normalize both sides: lowercase, trim, remove tokens `member` and `segment`, and apply light singularization (`services`→`service`, `products`→`product`).
- Extract one or more segment candidates from quote/LLM output.
- For each candidate, require exact unique normalized match against cached deduped member labels (`best_member_label` per `member_qname`).
- Link one `MAPS_TO_MEMBER` edge per confidently matched member.
- Multiple confident members across different axes are valid in one update (example: product + geography).
- If no confident matches, keep `segment='Total'` semantics (company-wide/default) and write no member edge.

### Domain and Coverage Notes

- Do not create direct Domain links for Guidance/GuidanceUpdate.
- Domain is hierarchy metadata; for guidance use-cases, Member carries the actionable semantic granularity.
- Axis fields from warmup cache (`best_axis_qname`, `best_axis_u_id`) are for diagnostics only; no `MAPS_TO_AXIS`/dimension edge is written.
- Segment coverage varies by company and filing set; zero member links for a run is acceptable.

---

## 8. Chronological Ordering (No Linked List)

GuidanceUpdate nodes do **not** maintain NEXT/PREVIOUS edges.

### Ordering Rule

All time-based reads MUST use deterministic ordering:
- Primary: `given_date`
- Tie-breaker: `id`

Use:
```cypher
ORDER BY gu.given_date, gu.id
```
or latest-first:
```cypher
ORDER BY gu.given_date DESC, gu.id DESC
```

### Rationale

This avoids write-time chain maintenance complexity and keeps reads reliable for both chronological initial builds and out-of-order single-source backfills.

### Basis Safety

Mixed bases (GAAP and non-GAAP) may appear in the same metric history. Do not compare consecutive values unless partitioned/filtering by `basis_norm` first.

---

## 9. Predictor Query

Replaces markdown file passthrough. The predictor runs this Cypher at bundle assembly time.

### All guidance for a company (PIT-filtered)

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
WHERE gu.given_date <= $pit_date
MATCH (gu)-[:FROM_SOURCE]->(src)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(m:Member)
RETURN g.label AS metric, gu.xbrl_qname AS xbrl_concept,
       gu.given_date, gu.period_type, gu.fiscal_year, gu.fiscal_quarter,
       gu.segment, gu.basis_norm, gu.basis_raw, gu.low, gu.mid, gu.high, gu.unit,
       gu.derivation, gu.qualitative, gu.quote, gu.section, gu.conditions,
       p.start_date, p.end_date,
       labels(src)[0] AS source_type, src.id AS source_id,
       m.label AS xbrl_member
ORDER BY g.label, gu.given_date, gu.id
```

### Latest value per guidance tag + basis

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE gu.given_date <= $pit_date
WITH g, ctx, gu.basis_norm AS basis_norm, gu.segment AS segment, gu ORDER BY gu.given_date DESC, gu.id DESC
WITH g, ctx, basis_norm, segment, collect(gu)[0] AS latest
MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
RETURN g.label AS metric, basis_norm, segment, latest.basis_raw, latest.segment,
       latest.low, latest.mid, latest.high, latest.unit, latest.qualitative,
       latest.given_date, latest.fiscal_year, latest.fiscal_quarter,
       p.start_date, p.end_date
```

### Accuracy comparison (side note — predictor runs this, not guidance system)

Compares guidance values to XBRL actuals using `xbrl_qname` as the join key. This is NOT part of the extraction pipeline.

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
WHERE gu.xbrl_qname IS NOT NULL
// Strict mode: only GAAP-to-GAAP. Remove filter for proxy/flagged comparison.
  AND gu.basis_norm = 'gaap'
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept {qname: gu.xbrl_qname})
MATCH (f)-[:IN_CONTEXT]->(fctx:Context)-[:FOR_COMPANY]->(c)
MATCH (fctx)-[:HAS_PERIOD]->(fp:Period)
WHERE fp.start_date = p.start_date AND fp.end_date = p.end_date
  AND f.is_numeric = '1'
  AND (fctx.member_u_ids IS NULL OR fctx.member_u_ids = [])
// Deterministic tie-break if multiple facts match (e.g., restated values)
WITH g.label AS metric, gu.mid AS guided, toFloat(f.value) AS actual,
     gu.basis_norm, f.id AS fact_id
ORDER BY fact_id DESC
WITH metric, guided, collect(actual)[0] AS actual, basis_norm
RETURN metric, guided, actual, actual - guided AS surprise, basis_norm
```

---

## 10. Trigger Integration

### Auto Trigger (Primary) + SDK Manual Modes (Backfill/Reprocess)

Execution path: Claude SDK `query(...)` with `tools={'type':'preset','preset':'claude_code'}` runs Claude Code (loading `.claude/`), and slash command `/guidance-inventory ...` triggers the guidance skill chain.
`Task subagent_type=...` is agent/subagent spawning orchestration and is not the skill invocation path.

Primary execution:
- Auto-trigger per asset, immediately when asset-ready gate passes (canonical text fully extracted and persisted).
- Day-1 coverage: `8k`, `transcript`, `10q`, `10k`, `news` (all source types enabled).

Manual SDK modes (kept for backfill/reprocess):
**Single source**: Extract guidance from one specific document.
```
/guidance-inventory {TICKER} {SOURCE_TYPE} {SOURCE_ID}
```

**Initial build**: Process all historical sources for a company chronologically.
```
/guidance-inventory {TICKER} initial
```

| Parameter | Type | Examples |
|-----------|------|---------|
| `TICKER` | String | `AAPL`, `MSFT` |
| `SOURCE_TYPE` | Enum | `8k`, `transcript`, `news`, `10q`, `10k`, `initial` |
| `SOURCE_ID` | String | `0001193125-25-000001`, `AAPL_2025-07-31T...`, `bzNews_50123456` |

**Boundary**: Extraction writes to the graph. The orchestrator/predictor reads from it (§9). No coupling.

### Extraction Steps

```
1. LOAD CONTEXT
   ├── get_derived_fye(ticker)
   ├── Warmup XBRL caches once/company/run (§7):
   │     concept usage cache + member cache (with CIK pad normalization)
   ├── Query existing Guidance nodes:
   │     MATCH (g:Guidance)<-[:UPDATES]-(gu:GuidanceUpdate)
   │           -[:IN_CONTEXT]->(ctx)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
   │     RETURN DISTINCT g.label, g.id
   └── Fetch source content via QUERIES.md Cypher

2. LLM EXTRACTION (routed by SOURCE_TYPE)
   ├── Route to source-type extraction profile (§3 Per-Source Rules)
   │     8k       → scan EX-99.* outlook/tables/footnotes + Item 2.02/7.01 text, skip pure actuals/boilerplate
   │     transcript → scan everything (CFO, Q&A, CEO), extract all guidance
   │     news      → channel-filter first, extract company guidance only
   │     10q/10k   → MD&A primary; if zero guidance, one bounded fallback pass in broader filing text
   ├── Run forward-guidance full-text recall on scoped text (§3):
   │     build candidate windows from forward-guidance hits
   │     keep only windows with nearby metric/period/value signals
   │     fallback when recall returns zero:
   │       transcript → full transcript text node only if prepared/Q&A missing or truncated
   │       8k         → one broader pass across scoped 8-K text (EX-99.* + Item text)
   │       10q/10k    → one keyword-window pass excluding legal/risk-heavy sections
   ├── Feed: candidate windows (or fallback scoped text) + existing Guidance tags for this company
   │     + warmup member candidates (`member_label`, `member_qname`, `axis_qname`) so LLM can select 0..N members
   ├── Prompt: "Extract all guidance. For each item, return quote evidence, period intent,
   │            basis (explicit-only), metric tag, values, derivation (`explicit|calculated|point|implied|floor|ceiling|comparative`),
   │            and XBRL link candidates (including zero/one/many member candidates)."
   └── Apply quality filters (no citation = no node)

2.5 DETERMINISTIC VALIDATION (pre-write)
   ├── Canonicalize numeric scale + unit (§2A) before hashing
   ├── Validate basis rule: if qualifier not explicit in metric quote span → basis_norm = unknown
   ├── Resolve period_u_id via §6 (code-only fiscal math; supports 52/53-week fallback)
   ├── Resolve canonical unit + unit_u_id via §6 Unit rules
   ├── Resolve xbrl_qname from concept cache (§7): pattern match → highest usage → set or null
   ├── Apply member confidence gate (§7)
   └── If uncertain: keep core item write, set xbrl_qname=null, skip uncertain member edges

3. PER ITEM: WRITE TO GRAPH
   ├── Compute deterministic IDs via shared utility (§2A): `guidance_id`, `evhash16`, `guidance_update_id`
   ├── MERGE Guidance node: MERGE (g:Guidance {id: $guidance_id})
   │     ON CREATE SET g.label = $label, g.aliases = coalesce($aliases, []), g.created_date = toString(date())
   │     ON MATCH SET g.aliases = reduce(acc = [], a IN (coalesce(g.aliases, []) + coalesce($aliases, [])) |
   │       CASE WHEN a IS NULL OR a IN acc THEN acc ELSE acc + a END)
   ├── Find/create Context + Period (§6)
   ├── Find/create Unit (§6)
   ├── MERGE GuidanceUpdate node: MERGE (gu:GuidanceUpdate {id: $guidance_update_id})
   │     ON CREATE SET gu += $all_properties, gu.evhash16 = $evhash16, gu.xbrl_qname = $xbrl_qname
   ├── Link: (gu)-[:UPDATES]->(g)
   ├── Link: (gu)-[:FROM_SOURCE]->(source)
   ├── Link: (gu)-[:IN_CONTEXT]->(context)
   ├── Link: (gu)-[:HAS_PERIOD]->(period)
   ├── Link: (gu)-[:HAS_UNIT]->(unit)
   ├── No linked-list write step (ordering is query-time; §8)
   └── Link XBRL members if confident (§7): 0..N Member links on Update
```

### Initial Build (new company)

Process all historical sources chronologically (oldest first). Per earnings event: 8-K → news → transcript → 10-Q. Each extraction adds to the graph incrementally.

### Idempotency

Idempotency is ID-driven. Do not pre-check with a broad query. Compute deterministic ID (§2A), then:
```cypher
MERGE (gu:GuidanceUpdate {id: $guidance_update_id})
ON CREATE SET gu += $all_properties,
              gu.evhash16 = $evhash16
RETURN gu
```
If `MERGE` matches existing node, treat as duplicate/no-op. Force flag can still delete + re-extract.

### Reprocessing

Delete all GuidanceUpdate nodes for a company → re-run initial build. Source documents remain in Neo4j.

---

## 11. Deferred Items

| Item | Status | Notes |
|------|--------|-------|
| Analyst estimate extraction (#35) | Deferred | Extract with correct source attribution. Note "Est $X" = analyst, not company. |
| Accuracy tracking | Predictor's job | Compare Guidance vs XBRL Fact at prediction time (§9). |
| Investor day / presentations | When ingested | Any doc asset is a candidate. Not yet in pipeline. |
| Perplexity gap-filling | Available | Last resort. Assume subscription. |
| Markdown generation | On demand | Generate readable report from graph if humans need it. Not stored. |
| Neo4j write access | Must verify | `mcp__neo4j-cypher__write_neo4j_cypher` needed in skill tools. |
| Neo4j write infrastructure | Decided | Reuse `Neo4jManager` session/driver/retry plumbing. Write guidance nodes via direct Cypher MERGE (news.py pattern), NOT via `merge_nodes()`/`merge_relationships()` dataclass path. Avoids touching shared NodeType/RelationType enums and XBRL constraint infrastructure. See Decision #33. |

---

## 12. Finalized Decisions

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Data store | Neo4j graph (not markdown file) |
| 2 | Guidance node | Generic concept, not per-company |
| 3 | GuidanceUpdate node | Per-mention, 19 fields as properties (includes `basis_norm` + `basis_raw`) with direct `HAS_PERIOD` and `HAS_UNIT` edges |
| 4 | Company association | Through Context (cik→FOR_COMPANY→Company), not direct link |
| 5 | Ordering model | No linked list. Chronological ordering is query-time using `ORDER BY given_date, id` per Guidance+Company. |
| 6 | Action types | None stored — deterministic query-time derivation from timeline |
| 7 | Supersession | None — latest by `given_date` (tie-break `id`) is current |
| 8 | Anchor rule | None — first in timeline is implicit anchor |
| 9 | Source priority | None — process chronologically, attribute to source |
| 10 | Synthesis pass | None — graph structure handles it |
| 11 | Output format | Cypher query for predictor context (no markdown) |
| 12 | Trigger | Auto-trigger per asset at asset-ready ingest (primary). SDK `single`/`initial` retained for backfill/reprocess. Extraction writes, prediction reads. |
| 13 | News filtering | Benzinga channels: Guidance, Earnings, Earnings Beats/Misses, Previews, Management |
| 14 | XBRL linking | Concept via `xbrl_qname` property on GuidanceUpdate (no edge). Member via `MAPS_TO_MEMBER` edge on GuidanceUpdate (0..N). Dimension links dropped. Basis-independent mapping; basis filtering at query time. |
| 15 | Fiscal periods | Reuse `get_derived_fye()` + `period_to_fiscal()` (validation only), and add `fiscal_to_dates()` for fiscal→calendar conversion with deterministic 52/53-week fallback. |
| 16 | Metric normalization | 12-metric canonical list with aliases (§4). Non-exhaustive — LLM creates new Guidance nodes as needed. |
| 17 | Segment handling | Property on GuidanceUpdate + `MAPS_TO_MEMBER` with 0..N matches when confident; `Total` means company-wide/default semantics |
| 18 | Analyst estimates | Deferred. Note for future. |
| 19 | Accuracy tracking | Predictor's job, not guidance system |
| 20 | Execution mode | SDK-compatible, non-interactive |
| 21 | Missing data | Note for next round, not hard-fail |
| 22 | Context reuse | Same Context label as XBRL (Option A). Identical format so XBRL ingestion can reuse. |
| 23 | Basis tracking | `basis_norm` (`gaap`/`non_gaap`/`constant_currency`/`unknown`) + `basis_raw` (verbatim). Assign basis only when explicit in the same metric quote span; else `unknown`. |
| 24 | Per-asset extraction | Extraction MUST route by source type before LLM. Each doc asset has separate scan scope, inclusion/exclusion rules. |
| 25 | ~~Merged into #16~~ | — |
| 26 | Deterministic IDs | `Guidance.id = guidance:{label_slug}`. `GuidanceUpdate.id = gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}:{evhash16}` where `period_u_id` is taken directly from resolved Context and `evhash16 = sha256("{low}|{mid}|{high}|{unit}|{qualitative}|{conditions}")[:16]` using canonicalized numeric scale + unit (`usd`, `m_usd`, `percent`, `percent_yoy`, etc.). MERGE on `id`. |
| 27 | LLM governance | LLM proposes extraction + basis/link candidates; deterministic validator enforces canonicalization, basis rule, period resolution, and confidence gates pre-write. |
| 28 | Derivation enum | Extended to `floor`, `ceiling`, `comparative` to avoid fabricating values for one-sided or relative guidance. |
| 29 | News reaffirm guardrail | Reaffirm/maintain language in news sets reaffirm flag in `conditions`; extractor keeps exact source values (no tolerance-based rewrites). |
| 30 | Segment normalizer | Use light singularization + small synonym map for stable member matching (`services`→`service`, `products`→`product`). |
| 31 | Period/unit linkage | GuidanceUpdate always links to `Context`, direct `Period`, direct `Unit`, and exact source node. |
| 32 | XBRL node reuse policy | Reuse `Context`/`Period` when exact match; create synthetic XBRL-compatible when missing. Use canonical guidance Unit nodes (not raw XBRL units when scale differs). Concept resolved via `xbrl_qname` property (qname is stable across taxonomy years). Link `Member` when confident; no direct `Concept`/`Dimension`/`Domain` edges. |
| 33 | Neo4j write path | Reuse `Neo4jManager` session/driver/retry infrastructure only. Write guidance nodes via **direct Cypher MERGE** transactions (like `neograph/mixins/news.py`), not via the `merge_nodes()`/`merge_relationships()` dataclass path. Rationale: (1) `merge_relationships()` has a special `{key: source_id}` branch for `HAS_PERIOD`/`HAS_UNIT` coupled to XBRL relationship key constraints — guidance would work but creates unnecessary shared-surface coupling; (2) avoids adding entries to shared `NodeType`/`RelationType` enums which trigger constraint-creation loops and affect `get_neo4j_db_counts()` — unnecessary shared-surface coupling; (3) XBRL `Unit` class requires Arelle `ModelFact` — guidance units are trivial and better served by inline MERGE. Note: `:Guidance` label is clean — current XBRL guidance concepts are stored as `:Concept` with `category = "Guidance"`, not under the `:Guidance` label (0 nodes, verified). Reusable as-is: `Period` dataclass (`generate_id()` already produces `duration_{start}_{end}` matching guidance spec). Validation: all guidance nodes must have `id` prefix `guidance:`, all GuidanceUpdate nodes must have `id` prefix `gu:`. |

---

## 13. Reusable Content

| Content | Source | Action |
|---------|--------|--------|
| `period_to_fiscal()` | `get_quarterly_filings.py:66` | Reuse directly (calendar→fiscal) |
| `get_derived_fye()` | `get_quarterly_filings.py:370` | Reuse directly |
| `fiscal_to_dates()` | `get_quarterly_filings.py:196` | Fiscal→calendar resolver. Lookup-first from existing non-guidance Period nodes (via `period_to_fiscal()`), `_compute_fiscal_dates()` fallback for future periods. |
| Metric normalization | `guidance-extract.md:258-269` | Carry forward (§4) |
| `Neo4jManager` session/driver | `neograph/Neo4jManager.py` | Reuse session plumbing, retry decorators, `execute_cypher_query()`. Do NOT use `merge_nodes()`/`merge_relationships()` for guidance writes — use direct Cypher MERGE (Decision #33). |
| News write pattern | `neograph/mixins/news.py:278-329` | Reference pattern: direct `MERGE (n:Label {id: $id}) ON CREATE SET ... ON MATCH SET ...` via `self.manager.driver.session()`. Follow this for guidance. |
| `Period` dataclass | `XBRL/xbrl_basic_nodes.py:87` | Reuse directly — `generate_id()` produces `duration_{start}_{end}` matching guidance spec exactly. |
| Source extraction hints | `guidance-extract.md:146-199` | Carry forward (§3) |
| Derivation rules | `guidance-extract.md:229-237` | Carry forward (§5) |
| Segment rules | `guidance-extract.md:242-252` | Carry forward |
| ID normalization utility | NEW — must build | Single shared helper for slugging, unit/scale canonicalization, `evhash16`, and `guidance_update_id` assembly (§2A) |
| Cypher queries | `guidance-inventory/QUERIES.md` | Keep, fix labels |
| Fiscal calendar | `guidance-inventory/FISCAL_CALENDAR.md` | Keep as-is |
| Evidence standards | `evidence-standards/SKILL.md` | Load during extraction |
| AAPL benchmark | `sampleGuidance_byAgentTeams.md` | Quality target |

---

## 14. Files to Update (pending approval)

| File | Status | Action Needed |
|------|--------|---------------|
| `guidance-extract.md` (agent) | May be superseded | Align with graph-native; core logic reused, invocation changes |
| `guidance-inventory/SKILL.md` | Needs rewrite | New invocation contract, Neo4j write, updated model |
| `guidance-inventory/OUTPUT_TEMPLATE.md` | Likely superseded | No markdown output; graph-native |
| `guidance-inventory/QUERIES.md` | Keep | Fix "Via Skill" labels |
| `earnings-orchestrator.md` | Already updated | Step 0 removed, I5 = graph query |

---

*v2.2 | 2026-02-20 | Drop MAPS_TO_CONCEPT edge; use `xbrl_qname` property on GuidanceUpdate (qname stable across taxonomy years). Basis-independent concept mapping; basis filtering at query time. Null-safe consolidated filter. ON CREATE only for xbrl_qname (no implicit re-extraction updates). Accuracy query is side note with deterministic tie-break.*
