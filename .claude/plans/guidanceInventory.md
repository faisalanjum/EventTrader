# Guidance System — Implementation Spec

**Version**: 2.1 | 2026-02-19
**Status**: Architecture locked — implementation-ready
**Parent**: `earnings-orchestrator.md`
**Benchmark**: `sampleGuidance_byAgentTeams.md` (AAPL)
**Supersedes**: `guidanceInventory.md` v0 (file-centric), `guidanceWIP.md` v0.2 (pre-graph)

---

## Top Open Decisions (Pin)

These decisions are intentionally pinned at the top so they are resolved before implementation drift.

| Priority | Decision | What Must Be Decided | Status |
|---|---|---|---|
| P0 | Per-asset extraction treatment | Exact extraction policy per doc asset type (`8k`, `transcript`, `news`, `10q/10k`): scan scope, inclusion rules, exclusion rules, and citation expectations per asset. | OPEN |
| P0 | Trigger model for extraction | How guidance extraction is triggered end-to-end (SDK on-demand only, ingestion hook, or hybrid) and who owns orchestration boundaries. | OPEN |
| P0 | GAAP vs non-GAAP handling | `basis_raw` (verbatim) + `basis_norm` (`gaap`, `non_gaap`, `constant_currency`, `unknown`). Single chain, query-time partitioning. Default `unknown`. See §2, §8, §9. | RESOLVED |
| P1 | Taxonomy alignment | Align metric normalization between plan and extraction agent (`OpEx`, `Tax Rate`, `OINE`, `Services Revenue` vs `Operating Income`, `Net Income`) and lock one canonical v1 list. | OPEN |

---

## 1. Graph Schema

### Architecture Overview

**New nodes**: `Guidance` (generic metric tag), `GuidanceUpdate` (per-mention data point)
**Reused nodes**: `Context`, `Period`, `Company`, `Concept`, `Member`, `Dimension`

**Relationship map** (all from GuidanceUpdate unless noted):

| From | Rel | To | When |
|------|-----|----|------|
| GuidanceUpdate | UPDATES | Guidance | Always |
| GuidanceUpdate | IN_CONTEXT | Context | Always (company+period) |
| GuidanceUpdate | FROM_SOURCE | Report / Transcript / News | Always (provenance) |
| GuidanceUpdate | NEXT | GuidanceUpdate | If later update exists |
| GuidanceUpdate | PREVIOUS | GuidanceUpdate | If earlier update exists |
| GuidanceUpdate | MAPS_TO_MEMBER | Member | If confident segment match |
| GuidanceUpdate | MAPS_TO_DIMENSION | Dimension | If confident axis match |
| Guidance | MAPS_TO_CONCEPT | Concept | If confident XBRL match |
| Context | FOR_COMPANY | Company | Always (via cik) |
| Context | HAS_PERIOD | Period | Always |

### XBRL Parallel

| XBRL | Guidance | Role |
|------|----------|------|
| Concept | Guidance | Generic metric definition, not per-company |
| Fact | GuidanceUpdate | Per-mention data point with all values |
| Context | Context (reused!) | Company + period scoping |
| Fact→IN_CONTEXT→Context | GuidanceUpdate→IN_CONTEXT→Context | Same pattern |
| Fact→HAS_CONCEPT→Concept | GuidanceUpdate→UPDATES→Guidance | Same pattern |

### Node: Guidance

Generic, company-agnostic. "Revenue" is ONE node shared across all companies.

| Property | Type | Description |
|----------|------|-------------|
| `label` | String | Normalized metric name: "Revenue", "EPS", "Gross Margin", etc. |
| `aliases` | String[] | Alternate names: e.g., ["sales", "net revenue", "total revenue"] |
| `created_date` | String | ISO date when first detected |

| Relationship | Direction | Target | Condition |
|-------------|-----------|--------|-----------|
| `MAPS_TO_CONCEPT` | OUT | Concept | If confident XBRL concept match |

### Node: GuidanceUpdate

Per-mention data point. See §2 for full field list.

| Relationship | Direction | Target | Condition |
|-------------|-----------|--------|-----------|
| `UPDATES` | OUT | Guidance | Always (parent tag) |
| `FROM_SOURCE` | OUT | Report / Transcript / News | Always (provenance) |
| `IN_CONTEXT` | OUT | Context | Always (company + period) |
| `NEXT` | OUT | GuidanceUpdate | If later update exists |
| `PREVIOUS` | OUT | GuidanceUpdate | If earlier update exists |
| `MAPS_TO_MEMBER` | OUT | Member | If confident segment match |
| `MAPS_TO_DIMENSION` | OUT | Dimension | If confident axis match |

---

## 2. Extraction Fields

Every GuidanceUpdate node carries these properties:

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
| 9 | `unit` | String | `%`, `USD`, `B USD`, `M USD`, `% YoY` | `"B USD"` |
| 10 | `basis_norm` | String | `gaap`, `non_gaap`, `constant_currency`, `unknown` | `"non_gaap"` |
| 11 | `basis_raw` | String / null | Verbatim basis text from source | `"non-GAAP"`, `"adjusted"`, `"as reported"` |
| 12 | `derivation` | String | `explicit`, `calculated`, `point`, `implied` | `"explicit"` |
| 13 | `qualitative` | String / null | Non-numeric guidance text | `"low to mid single digits"` |
| 14 | `quote` | String | Max 500 chars, verbatim from source | `"We expect revenue between..."` |
| 15 | `section` | String | Location within source | `"CFO Prepared Remarks"` |
| 16 | `source_key` | String | Sub-document key | `"EX-99.1"`, `"full"`, `"title"`, `"MD&A"` |
| 17 | `conditions` | String / null | Conditional assumptions | `"assumes no further rate hikes"` |
| 18 | `source_type` | String | `8k`, `transcript`, `news`, `10q`, `10k` | `"transcript"` |
| 19 | `created` | String | ISO timestamp of node creation | `"2026-02-18T14:30:00Z"` |

**Basis rules**: Default `basis_norm` to `unknown` when source doesn't specify. `adjusted` → `non_gaap`. `as-reported` → `gaap`. Compound bases (e.g., "non-GAAP constant-currency") — pick the most salient qualifier for `basis_norm`, preserve full text in `basis_raw`. V2 can split into `accounting_basis` + `fx_basis` if needed.

**Rule**: No citation = no node. Every GuidanceUpdate must have `quote`, `FROM_SOURCE`, and `given_date`.

---

## 3. Source Processing

### Source Richness

| # | Source | Richness | Arrives | Extract? | Notes |
|---|--------|----------|---------|----------|-------|
| 1 | Transcript | Highest | t+1d to t+5d | YES — full scan (prepared remarks + Q&A) | Best source. AAPL: all guidance came from here. |
| 2 | 8-K EX-99.1 | High | t=0 | YES — outlook section, tables, footnotes | Official numbers. Some companies (AAPL): zero guidance. |
| 3 | News | Medium | t-1h to t+24h | YES — after Benzinga channel filter | Mixes company guidance with analyst estimates. |
| 4 | 10-Q/10-K MD&A | Low | t+25d to t+45d | YES — specific statements only | Skip boilerplate. Note new risk language. |
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

| Source | Scan | Extract | Do NOT extract |
|--------|------|---------|----------------|
| **8-K** | Outlook section → tables → footnotes | Forward-looking numbers, ranges, directional | Reported actuals, safe harbor boilerplate |
| **Transcript** | Everywhere: CFO remarks, Q&A, CEO remarks | All guidance: formal, segment color, caveats, bridges, conditions | — |
| **News** | Title + body (after channel filter) | Company guidance only (V1) | Analyst estimates ("Est $X", "consensus") — deferred |
| **10-Q/10-K** | MD&A only | Specific numbers/ranges/directional beyond boilerplate | Generic "we expect continued growth" boilerplate |

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
| `OpEx` | operating expenses, SG&A, R&D + SG&A |
| `Tax Rate` | effective tax rate, tax rate, provision for income taxes |
| `CapEx` | capital expenditures, capex, capital spending |
| `FCF` | free cash flow, operating cash flow minus capex |
| `OINE` | other income and expense, other income/expense net |
| `Services Revenue` | services, services revenue |

Aliases stored on Guidance node in `aliases[]` property.

---

## 5. Derivation Rules

| Derivation | When | Example |
|------------|------|---------|
| `explicit` | Company states exact number or range | "We expect revenue of $94-97B" |
| `calculated` | Derived from explicitly stated values | GM% = (guided gross profit) / (guided revenue) |
| `point` | Single number given, no range | "CapEx of approximately $2B" |
| `implied` | Inferred from qualitative or partial info | "low to mid single digits" → implied range |

---

## 6. Context Resolution

### Goal

Every GuidanceUpdate links to a Context node via `IN_CONTEXT`. The Context provides company + period scoping, exactly as XBRL uses it.

### Option A (CHOSEN): Reuse XBRL Context label

Create Context nodes **identical to XBRL Context** so future XBRL ingestion can reuse them.

| Context Property | Type | Source | Example |
|-----------------|------|--------|---------|
| `id` | String | Synthetic for guidance | `"guidance_320193_d_2025-09-28_2025-12-27"` |
| `u_id` | String | Canonical unique key | Same as `id` (XBRL-compatible) |
| `cik` | String | Company node | `"320193"` |
| `context_id` | String | Synthetic for guidance | `"guidance_320193_d_2025-09-28_2025-12-27"` |
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

### Resolution Steps

```
1. Determine FYE:
   get_derived_fye(ticker) from get_quarterly_filings.py:134

2. Determine fiscal period dates:
   period_to_fiscal() from get_quarterly_filings.py:61
   NOTE: This maps calendar→fiscal. Guidance also needs fiscal→calendar
   (e.g., "Q3 FY2025" → start_date, end_date). Need complementary
   function: fiscal_to_dates(fye_month, fiscal_year, fiscal_quarter) → (start, end).
   Derive from FYE month + quarter offset.

3. Search for existing Context:
   MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
   MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
   WHERE p.period_type = 'duration'
     AND p.start_date >= $approx_start - 7d
     AND p.start_date <= $approx_start + 7d
   RETURN ctx, p LIMIT 1

4. If found → reuse (link GuidanceUpdate→IN_CONTEXT→existing Context)
   If not found → CREATE Context + Period matching XBRL format exactly:
     CREATE (p:Period {id: $period_uid, u_id: $period_uid,
                       period_type: 'duration',
                       start_date: $start, end_date: $end})
     CREATE (ctx:Context {id: $ctx_id, u_id: $ctx_id,
                          cik: $cik, context_id: $ctx_id,
                          period_u_id: $period_uid,
                          member_u_ids: [], dimension_u_ids: []})
     CREATE (ctx)-[:HAS_PERIOD]->(p)
     CREATE (ctx)-[:FOR_COMPANY]->(company)
```

### Period Scenario Table

Every GuidanceUpdate MUST have `IN_CONTEXT`. Synthetic XBRL-identical Contexts are created for ALL scenarios:

| Scenario | Example text | period_u_id | start/end dates | Action |
|----------|-------------|-------------|-----------------|--------|
| **Specific quarter** | "Q3 FY2025" | `duration_2025-06-29_2025-09-27` | Exact fiscal dates | Reuse existing XBRL Context if match; else CREATE |
| **Annual** | "fiscal year 2025" | `duration_2024-09-29_2025-09-27` | Full fiscal year | Reuse existing XBRL Context if match; else CREATE |
| **Half year** | "second half" | `duration_2025-03-30_2025-09-27` | Best-effort from FYE | CREATE synthetic Context |
| **Vague future** | "next year" | Best-effort from FYE | Derived from fiscal calendar | CREATE synthetic Context |
| **Long-range** | "by 2028" | `duration_2028-01-01_2028-12-31` | Calendar year fallback | CREATE synthetic Context |
| **Medium-term** | "over the medium term" | `other_medium_term` | null / null | CREATE synthetic Context |
| **No period** | (implicit/unclear) | `undefined` | null / null | CREATE synthetic Context (cik still set) |

**Rule**: Every synthetic Context MUST be structurally identical to XBRL Contexts (same label, same properties, same relationships). Future XBRL ingestion can find and reuse them when the actual period arrives.

---

## 7. XBRL Matching

All three in V1. Use Neo4j queries + fulltext. Only link if confident.

### Guidance → Concept

```cypher
// Find which Revenue concept this company actually uses
MATCH (f:Fact)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)-[:REPORTS]->(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(co:Company {ticker: $ticker})
WHERE c.qname STARTS WITH 'us-gaap:Revenue'
  AND f.is_numeric = '1'
RETURN DISTINCT c.qname, c.label, count(f) AS usage
ORDER BY usage DESC LIMIT 3
```

Rule: If single dominant concept (>80% of facts), link. If ambiguous, skip.

### GuidanceUpdate → Member

```cypher
// Find segment members for this company
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
MATCH (f)-[:FACT_DIMENSION]->(d:Dimension)
MATCH (f)-[:REPORTS]->(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(co:Company {ticker: $ticker})
WHERE d.qname CONTAINS 'Segment'
RETURN DISTINCT m.qname, m.label, d.qname AS dimension, count(f) AS usage
ORDER BY usage DESC LIMIT 20
```

Rule: Match GuidanceUpdate.segment text against m.label. If clear match (e.g., "Services" → `aapl:ServicesMember`), link.

### GuidanceUpdate → Dimension

Link to the axis used by the matched Member. Typically `us-gaap:StatementBusinessSegmentsAxis` or company-specific equivalent.

### Fulltext Supplement

```cypher
CALL db.index.fulltext.queryNodes('concept_ft', $metric_name)
YIELD node, score
RETURN node.qname, node.label, score ORDER BY score DESC LIMIT 10
```

---

## 8. Linked List Mechanics

GuidanceUpdate nodes form a doubly-linked list, **strictly ordered by `given_date`** (chronological).

### Scope

The linked list chains ALL updates for the **same Guidance tag + same Company** (via Context.cik), ordered strictly by `given_date`. The chain spans across ALL periods — so one traversal gives the complete history of everything a company has said about a metric. A Revenue guidance update for AAPL FY2025 annual links NEXT to a Revenue update for AAPL Q3 FY2025 quarterly if it has a later `given_date`.

### Insertion

When creating a new GuidanceUpdate:

```cypher
// Find the latest existing update for this Guidance + Company (across ALL periods)
MATCH (prev:GuidanceUpdate)-[:UPDATES]->(g:Guidance {label: $label})
MATCH (prev)-[:IN_CONTEXT]->(ctx:Context {cik: $cik})
WHERE NOT EXISTS { (prev)-[:NEXT]->() }
  AND prev.given_date <= $new_given_date

// Link into chain
CREATE (prev)-[:NEXT]->(new_gu)
CREATE (new_gu)-[:PREVIOUS]->(prev)
```

If no existing update → this is the first in the chain (head node).

### Reading

**Latest value**: Follow chain to the node with no outgoing NEXT.
**History**: Traverse PREVIOUS from latest to earliest.
**Important**: The chain may contain mixed bases (GAAP and non-GAAP interleaved). Do NOT blindly compare consecutive `mid` values across the raw chain. Any deterministic comparison must filter/partition by `basis_norm` at query time first. The LLM consumer sees `basis_norm` on each row and handles context naturally.

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
OPTIONAL MATCH (g)-[:MAPS_TO_CONCEPT]->(con:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(m:Member)
RETURN g.label AS metric, con.qname AS xbrl_concept,
       gu.given_date, gu.period_type, gu.fiscal_year, gu.fiscal_quarter,
       gu.segment, gu.basis_norm, gu.basis_raw, gu.low, gu.mid, gu.high, gu.unit,
       gu.derivation, gu.qualitative, gu.quote, gu.section, gu.conditions,
       p.start_date, p.end_date,
       labels(src)[0] AS source_type, src.id AS source_id,
       m.label AS xbrl_member
ORDER BY g.label, gu.given_date
```

### Latest value per guidance tag + basis

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE gu.given_date <= $pit_date
WITH g, ctx, gu.basis_norm AS basis_norm, gu ORDER BY gu.given_date DESC
WITH g, ctx, basis_norm, collect(gu)[0] AS latest
MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
RETURN g.label AS metric, basis_norm, latest.basis_raw, latest.segment,
       latest.low, latest.mid, latest.high, latest.unit, latest.qualitative,
       latest.given_date, latest.fiscal_year, latest.fiscal_quarter,
       p.start_date, p.end_date
```

### Accuracy comparison (predictor runs this, not guidance system)

```cypher
// Guidance value
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)-[:MAPS_TO_CONCEPT]->(con:Concept)
MATCH (gu)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (ctx)-[:HAS_PERIOD]->(p:Period)
// XBRL actual for same concept + same company + overlapping period
MATCH (f:Fact)-[:HAS_CONCEPT]->(con)
MATCH (f)-[:IN_CONTEXT]->(fctx:Context)-[:FOR_COMPANY]->(c)
MATCH (fctx)-[:HAS_PERIOD]->(fp:Period)
WHERE fp.start_date = p.start_date AND fp.end_date = p.end_date
  AND f.is_numeric = '1'
RETURN g.label, gu.mid AS guided, toFloat(f.value) AS actual,
       toFloat(f.value) - gu.mid AS surprise
```

---

## 10. Trigger Integration

### V1: SDK on-demand

```
/guidance-inventory {TICKER} {SOURCE_TYPE} {SOURCE_ID}
```

| Parameter | Type | Examples |
|-----------|------|---------|
| `TICKER` | String | `AAPL`, `MSFT` |
| `SOURCE_TYPE` | Enum | `8k`, `transcript`, `news`, `10q`, `10k` |
| `SOURCE_ID` | String | `0001193125-25-000001`, `AAPL_2025-07-31T...`, `bzNews_50123456` |

### Extraction Steps

```
1. LOAD CONTEXT
   ├── get_derived_fye(ticker)
   ├── Query existing Guidance nodes:
   │     MATCH (g:Guidance)<-[:UPDATES]-(gu:GuidanceUpdate)
   │           -[:IN_CONTEXT]->(ctx)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
   │     RETURN DISTINCT g.label, g.id
   └── Fetch source content via QUERIES.md Cypher

2. LLM EXTRACTION (routed by SOURCE_TYPE)
   ├── Route to source-type extraction profile (§3 Per-Source Rules)
   │     8k       → scan outlook/tables/footnotes, skip actuals/boilerplate
   │     transcript → scan everything (CFO, Q&A, CEO), extract all guidance
   │     news      → channel-filter first, extract company guidance only
   │     10q/10k   → MD&A only, skip boilerplate
   ├── Feed: source content + existing Guidance tags for this company
   ├── Prompt: "Extract all guidance. For each, identify if existing tag or new."
   └── Apply quality filters (no citation = no node)

3. PER ITEM: WRITE TO GRAPH
   ├── MERGE Guidance node: MERGE (g:Guidance {label: $label})
   ├── Find/create Context (§6)
   ├── CREATE GuidanceUpdate with all properties (§2)
   ├── Link: (gu)-[:UPDATES]->(g)
   ├── Link: (gu)-[:FROM_SOURCE]->(source)
   ├── Link: (gu)-[:IN_CONTEXT]->(context)
   ├── Link into NEXT/PREVIOUS chain (§8)
   └── Link XBRL if confident (§7): Concept on Guidance, Member+Dimension on Update
```

### Initial Build (new company)

Process all historical sources chronologically (oldest first). Per earnings event: 8-K → news → transcript → 10-Q. Each extraction adds to the graph incrementally.

### Idempotency

Before creating a GuidanceUpdate, check:
```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src {id: $source_id})
MATCH (gu)-[:UPDATES]->(g:Guidance {label: $label})
RETURN gu
```
If exists → skip. Force flag available for re-extraction.

### Reprocessing

Delete all GuidanceUpdate nodes for a company → re-run initial build. Source documents remain in Neo4j.

---

## 11. Deferred Items

| Item | Status | Notes |
|------|--------|-------|
| Analyst estimate extraction (#35) | V2 | Extract with correct source attribution. Note "Est $X" = analyst, not company. |
| Accuracy tracking | Predictor's job | Compare Guidance vs XBRL Fact at prediction time (§9). |
| Investor day / presentations | When ingested | Any doc asset is a candidate. Not yet in pipeline. |
| Ingestion hook trigger | Future | Auto-fire extraction when new doc lands in Neo4j. V1 = SDK on-demand. |
| Perplexity gap-filling | Available | Last resort. Assume subscription. |
| Markdown generation | On demand | Generate readable report from graph if humans need it. Not stored. |
| Neo4j write access | Must verify | `mcp__neo4j-cypher__write_neo4j_cypher` needed in skill tools. |

---

## 12. Finalized Decisions

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Data store | Neo4j graph (not markdown file) |
| 2 | Guidance node | Generic concept, not per-company |
| 3 | GuidanceUpdate node | Per-mention, 19 fields as properties (includes `basis_norm` + `basis_raw`) |
| 4 | Company association | Through Context (cik→FOR_COMPANY→Company), not direct link |
| 5 | Linked list | NEXT/PREVIOUS on GuidanceUpdates, strictly by datetime, per Guidance+Company (spans all periods) |
| 6 | Action types | None — LLM determines from timeline |
| 7 | Supersession | None — latest in linked list is current |
| 8 | Anchor rule | None — first in timeline is implicit anchor |
| 9 | Source priority | None — process chronologically, attribute to source |
| 10 | Synthesis pass | None — graph structure handles it |
| 11 | Output format | Cypher query for predictor context (no markdown) |
| 12 | Trigger | Auto on every document ingestion (V1: SDK on-demand) |
| 13 | News filtering | Benzinga channels: Guidance, Earnings, Earnings Beats/Misses, Previews, Management |
| 14 | XBRL linking | Concept on Guidance; Member + Dimension on GuidanceUpdate. V1. Confident matches only. |
| 15 | Fiscal periods | Reuse `get_derived_fye()` + `period_to_fiscal()` (validation only), and add `fiscal_to_dates()` for fiscal→calendar conversion. |
| 16 | Metric normalization | Standard labels with aliases (§4) |
| 17 | Segment handling | Property on GuidanceUpdate + MAPS_TO_MEMBER if confident match |
| 18 | Analyst estimates | Deferred to V2. Note for future. |
| 19 | Accuracy tracking | Predictor's job, not guidance system |
| 20 | Execution mode | SDK-compatible, non-interactive |
| 21 | Missing data | Note for next round, not hard-fail |
| 22 | Context reuse | Same Context label as XBRL (Option A). Identical format so XBRL ingestion can reuse. |
| 23 | Basis tracking | `basis_norm` (`gaap`/`non_gaap`/`constant_currency`/`unknown`) + `basis_raw` (verbatim). Single chain per Guidance+Company. Default `unknown`. Query-time partitioning for deterministic reads. No blind consecutive comparison across mixed bases. |
| 24 | Per-asset extraction | Extraction MUST route by source type before LLM. Each doc asset has separate scan scope, inclusion/exclusion rules. |
| 25 | Metric normalization | V1 table sufficient; deeper expansion deferred until extraction calibration. |

---

## 13. Reusable Content

| Content | Source | Action |
|---------|--------|--------|
| `period_to_fiscal()` | `get_quarterly_filings.py:61` | Reuse directly (calendar→fiscal) |
| `get_derived_fye()` | `get_quarterly_filings.py:134` | Reuse directly |
| `fiscal_to_dates()` | NEW — must build | Reverse of period_to_fiscal: (fye_month, fy, fq) → (start_date, end_date) |
| Metric normalization | `guidance-extract.md:258-269` | Carry forward (§4) |
| Source extraction hints | `guidance-extract.md:146-199` | Carry forward (§3) |
| Derivation rules | `guidance-extract.md:229-237` | Carry forward (§5) |
| Segment rules | `guidance-extract.md:242-252` | Carry forward |
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

*v2.1 | 2026-02-19 | Adds basis split (`basis_norm` + `basis_raw`), per-asset extraction routing, query-time basis partitioning, no blind consecutive comparison. Resolves GAAP/non-GAAP P0.*
