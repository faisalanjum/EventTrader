# Guidance System — Implementation Spec

**Version**: 3.1 | 2026-02-24
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
| P1 | Instant period support | Supported via `period_type` in Period u_id. Agent classifies as `duration` or `instant`. See §6 Period Resolution. | RESOLVED |
| P2 | Fallback Period mismatch | Eliminated. Guidance Periods use fiscal-keyed separate namespace (`guidance_period_` prefix) with no calendar date computation. No collision with XBRL Period nodes. See §6. | RESOLVED |

### Build-First TODOs

- [x] `fiscal_to_dates()` — fiscal→calendar resolver. Implemented in `earnings-orchestrator/scripts/get_quarterly_filings.py`. Not used by guidance extraction (fiscal-keyed Periods eliminate date computation), but kept for future actuals comparison.
- [x] Build ID normalization utility — slugging, unit/scale canonicalization, `evhash16`, and `guidance_update_id` assembly. Implemented in `earnings-orchestrator/scripts/guidance_ids.py`. 60 tests passing.
- [x] `period_to_fiscal()` is already implemented and validated in `earnings-orchestrator/scripts/get_quarterly_filings.py`; reuse it as a validation/helper function only (no reimplementation).
- [x] Guidance writer module — direct Cypher write path (`guidance_writer.py` + 62 tests). Uses `execute_cypher_query()` with label-specific source MATCH, ticker-based company resolution, direct `FOR_COMPANY` edge, `OPTIONAL MATCH` for was_created detection, `reduce`-based alias dedupe, `UNWIND` member batching. Feature flag `ENABLE_GUIDANCE_WRITES = False` in `config/feature_flags.py`. Dry-run works independently of feature flag.
- [x] Add `build_period_u_id()` to `guidance_ids.py` — fiscal-keyed Period u_id construction. Drop `ctx_u_id` and `unit_u_id` from `build_guidance_ids()` return dict.

### Implementation Handoff (Next Bot)

Use this block as the execution contract so implementation can proceed without extra prompts.

**Mandatory read order (before coding):**
1. This file: §1, §2, §2A, §3, §6, §7, §10, §12, §13, §14 (completion status).
2. Completed reference docs (DO NOT rewrite — these are done):
   - `.claude/skills/guidance-inventory/SKILL.md` (v3.0)
   - `.claude/skills/guidance-inventory/QUERIES.md` (v2.10)
   - `.claude/skills/guidance-inventory/reference/PROFILE_*.md` (4 files)
3. `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py` + `test_guidance_ids.py`.
4. `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py` (`period_to_fiscal`, `get_derived_fye` — `fiscal_to_dates` not used by guidance extraction).
5. `neograph/mixins/news.py` and `neograph/Neo4jManager.py` (`execute_cypher_query`) for write pattern reuse.
6. `.claude/agents/guidance-extract.md` (current version — this is the file to rewrite, per §15A).

**Verify environment:** `python3 -m pytest .claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py test_fiscal_resolve.py test_guidance_writer.py test_guidance_write_cli.py` — all tests must pass before any changes (60 IDs + 29 fiscal + 62 writer + 18 CLI = 169).

**Non-negotiables:**
1. Do not modify `period_to_fiscal()` or `get_derived_fye()`.
2. Guidance writes must use direct Cypher `MERGE` via existing `Neo4jManager` session/driver plumbing (news.py pattern).
3. Do not use `merge_relationships()` or `create_relationships()` for guidance core writes.
4. Do not add guidance-specific `NodeType`/`RelationType` enum entries.
5. `GuidanceUpdate` write must use deterministic slot-based ID + `MERGE ... ON CREATE SET gu.created` + `SET` (all other props). Latest write wins — enables enrichment on rerun without duplicates.
6. `xbrl_qname` property + `MAPS_TO_CONCEPT` edge on `GuidanceUpdate` (both kept; property is stable cross-taxonomy fallback, edge is graph-native join).
7. Feature flag default must keep writes disabled until validation completes.
8. No citation = no node. Every GuidanceUpdate must have `quote`, `FROM_SOURCE`, and `given_date` (§2). Reject at validation, not silently skip.

**Implementation scope (minimal):**
1. Reuse `guidance_ids.py` as single source of truth for canonicalization + ID assembly.
2. Add guidance writer path using direct Cypher (Guidance, GuidanceUpdate, Period, core edges including direct FOR_COMPANY, optional 0..N member edges).
3. Add dry-run/shadow mode (extract + validate + ID build, no write).
4. Warmup caches (§7): concept usage cache + member cache queries, run once per company per extraction run. Needed for `xbrl_qname` resolution and `MAPS_TO_MEMBER` linking.

**Execution order (one source type at a time):**
1. AAPL transcript → extract → compare against `sampleGuidance_byAgentTeams.md` → fix until it matches. Dry-run first, then write to Neo4j.
2. 2-3 more companies on transcripts → fix edge cases.
3. 8-K EX-99.1 → same pattern (single company, compare, expand).
4. News → then 10-Q/10-K. One source type at a time, never all at once.

**Must-pass gates before enabling writes:**
1. `python3 .claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py`
2. Shadow run on at least 3 companies and 3 asset types (report/transcript/news), no DB writes.
3. Idempotency check: same source processed twice creates zero new `GuidanceUpdate` nodes on second run.
4. Regression check: existing report/news/transcript ingest behavior unchanged.
5. Canary enablement: 1-2 tickers first, then full rollout.

---

## 1. Graph Schema

### Architecture Overview

**Created by guidance**: `Guidance` (generic metric tag), `GuidanceUpdate` (per-mention data point), `Period` (fiscal-keyed, `guidance_period_` namespace)
**Reused from XBRL (MATCH only, never CREATE)**: `Company`, `Concept`, `Member`, `Report` / `Transcript` / `News`
**Removed**: `Context` (replaced by direct `FOR_COMPANY` edge), `Unit` (demoted to `canonical_unit` property on GuidanceUpdate)

**Relationship map** (6 edges, all from GuidanceUpdate):

| From | Rel | To | When |
|------|-----|----|------|
| GuidanceUpdate | UPDATES | Guidance | Always |
| GuidanceUpdate | FROM_SOURCE | Report / Transcript / News | Always (provenance) |
| GuidanceUpdate | FOR_COMPANY | Company | Always (direct, replaces Context path) |
| GuidanceUpdate | HAS_PERIOD | Period | Always (fiscal-keyed) |
| GuidanceUpdate | MAPS_TO_CONCEPT | Concept | If confident concept match (0..1) |
| GuidanceUpdate | MAPS_TO_MEMBER | Member | If one or more confident segment matches (0..N) |

### Required Constraints

```cypher
CREATE CONSTRAINT guidance_id_unique IF NOT EXISTS
FOR (g:Guidance) REQUIRE g.id IS UNIQUE;

CREATE CONSTRAINT guidance_update_id_unique IF NOT EXISTS
FOR (gu:GuidanceUpdate) REQUIRE gu.id IS UNIQUE;

-- Period constraint already exists from XBRL pipeline;
-- guidance_period_ namespace nodes are covered by it.
```

### XBRL Parallel

| XBRL | Guidance | Role |
|------|----------|------|
| Concept | Guidance | Generic metric definition, not per-company |
| Fact | GuidanceUpdate | Per-mention data point with all values |
| Fact→HAS_CONCEPT→Concept | GuidanceUpdate→MAPS_TO_CONCEPT→Concept + `xbrl_qname` property | Both edge (graph join) and property (cross-taxonomy fallback) |
| Fact→HAS_PERIOD→Period | GuidanceUpdate→HAS_PERIOD→Period | Both link to Period (different namespaces) |
| Fact→IN_CONTEXT→Context→FOR_COMPANY→Company | GuidanceUpdate→FOR_COMPANY→Company | Guidance links directly (no Context intermediary) |
| Fact→HAS_UNIT→Unit | GuidanceUpdate.canonical_unit property | Guidance demotes unit to property (9-value enum, not a graph relationship) |

### XBRL Bridge Policy (Locked)

Only Concept and Member are true XBRL bridge nodes. Everything else is guidance-internal:

| Node/Edge | Policy |
|---|---|
| `Concept` | `MAPS_TO_CONCEPT` edge (graph-native join) + `xbrl_qname` property (cross-taxonomy fallback). Edge points to best-match Concept from current taxonomy window. |
| `Member` | Link `GuidanceUpdate -> Member` with 0..N confident matches. |
| `Period` | **Separate namespace** — `guidance_period_` prefix, fiscal-keyed. No date computation, no collision with XBRL Period nodes. See §6. |
| `Company` | **Reused** — same node, direct `FOR_COMPANY` edge from GuidanceUpdate. |
| `Context` | **Removed** — replaced by direct `FOR_COMPANY` edge. Context was a 1:1 passthrough (one per GuidanceUpdate, `member_u_ids=[]`, `dimension_u_ids=[]`). XBRL Context groups hundreds of facts sharing the same company+period+dimensions tuple; guidance has no such sharing. |
| `Unit` | **Removed** — demoted to `canonical_unit` property on GuidanceUpdate. 9 canonical values is an enum, not a graph relationship. `guidance_unit_m_usd` would never join with XBRL's `iso4217:USD` (different scales, different namespaces). |
| `Dimension` / `Domain` | No direct linkage from guidance nodes in this design. |

**The join between guidance and actuals** requires matching on Concept (what metric) + Company (direct edge) + fiscal identity (`fiscal_year` + `fiscal_quarter` properties) + optionally Member (what segment). Concept is the primary XBRL bridge; fiscal identity matching replaces date-based Period joins.

**Why remove Context**: XBRL Context groups hundreds of facts sharing the same company+period+dimensions tuple. Guidance Context was always 1:1 with GuidanceUpdate (`member_u_ids=[]`, `dimension_u_ids=[]`), adding a hop without grouping benefit. The company link is now direct; the period link was already direct (`HAS_PERIOD`); segment is handled by `MAPS_TO_MEMBER` edges.

**Why remove Unit node**: 9 canonical unit values is an enum, not a graph relationship. `WHERE gu.canonical_unit = 'm_usd'` is equivalent to and faster than edge traversal. The XBRL-compatible shape we added (`is_divide`, `item_type`, `namespace`) was decoration no query would traverse. Scale conversion for actuals comparison (guidance `m_usd` vs XBRL raw USD) is Python-side arithmetic (`xbrl_value / 1_000_000`), not a graph join.

**Why keep m_usd (not raw USD)**: LLM extraction produces human-scale numbers ("$94B revenue" → 94000 in millions). Converting to raw (94000000000) adds a conversion step that can go wrong. Per-share stays in `usd` (EPS $1.50 → 1.50). Comparison with XBRL is Python-side: multiply by 1M.

### Node: Guidance

Conceptually parallel to XBRL `Concept`: generic, company-agnostic. "Revenue" is ONE node shared across all companies.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Deterministic key: `guidance:{slug(label)}` |
| `label` | String | Normalized metric name: "Revenue", "EPS", "Gross Margin", etc. |
| `aliases` | String[] | Alternate names: e.g., ["sales", "net revenue", "total revenue"] |
| `created_date` | String | ISO date when first detected |

Concept resolution uses both `MAPS_TO_CONCEPT` edge (graph-native join to XBRL Concept) and `xbrl_qname` property (cross-taxonomy fallback) on GuidanceUpdate. The Guidance node carries only the metric label and aliases.

### Node: GuidanceUpdate

Conceptually parallel to XBRL `Fact`: per-mention data point. See §2 for full field list.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Deterministic slot-based key: `gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}` (see §2A). evhash NOT in ID — slot alone is the identity. |
| `evhash16` | String | First 16 hex chars of evidence hash from value-bearing fields. Stored property for change detection, not part of identity key. |
| `xbrl_qname` | String / null | Resolved XBRL concept qname (e.g., `us-gaap:Revenues`). Set at extraction time from concept cache. Null when no confident match. See §7. |

| Relationship | Direction | Target | Condition |
|-------------|-----------|--------|-----------|
| `UPDATES` | OUT | Guidance | Always (parent tag) |
| `FROM_SOURCE` | OUT | Report / Transcript / News | Always (provenance) |
| `FOR_COMPANY` | OUT | Company | Always (direct company link) |
| `HAS_PERIOD` | OUT | Period | Always (fiscal-keyed period) |
| `MAPS_TO_CONCEPT` | OUT | Concept | If confident concept match (0..1) |
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
| 9 | `canonical_unit` | String | Canonical: `usd`, `m_usd`, `percent`, `percent_yoy`, `percent_points`, `basis_points`, `x`, `count`, `unknown` | `"m_usd"` |
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

GuidanceUpdate ID (slot-based, deterministic):
- `guidance_update_id = "gu:" + source_id + ":" + label_slug + ":" + period_u_id + ":" + basis_norm + ":" + segment_slug`
- The ID is the **slot** — it identifies WHAT guidance (label+segment), WHERE it came from (source), WHEN it targets (period), and on WHAT basis. evhash is NOT in the ID.
- `source_key` remains a stored property for provenance and is not part of the identity key.

Canonicalization before ID build:
- `source_id` uses the canonical source-node id as stored (trim whitespace only; do not slugify). If `source_id` contains `:`, replace `:` with `_` for delimiter safety.
- `label_slug = label.lower().replace(" ", "_")`
- `segment_slug = segment.lower().replace(" ", "_")` (default `total`)
- `basis_norm` uses enum as-is: `gaap|non_gaap|constant_currency|unknown`
- `period_u_id` comes from `guidance_ids.py:build_period_u_id()` (fiscal-keyed, e.g., `guidance_period_320193_duration_FY2025_Q1`) and is used directly in the ID.

Evidence hash (stored property, not in ID):
- `evhash16 = sha256("{low}|{mid}|{high}|{unit}|{qualitative}|{conditions}")[:16]` where:
  - numeric parts (`low/mid/high`) are canonical decimal strings after unit normalization
  - aggregate currency metrics normalize to `m_usd` before hashing (`$1.13B` and `1130 M USD` both normalize to `1130|...|m_usd`)
  - per-share currency metrics (e.g., EPS/DPS) normalize to `usd`
  - percentages normalize to `percent` or `percent_yoy` only
  - `unit` is lowercase canonical enum value
  - text parts (`qualitative/conditions`) are lowercase + trimmed + whitespace-collapsed
- Nulls in hash input are encoded as `.` (dot).
- **Why not in ID**: LLM paraphrasing varies between runs (qualitative text non-determinism) AND content migrates between `qualitative` and `conditions` fields. Both are evhash inputs, so evhash is unstable across runs. Keeping it in the ID caused duplicate nodes for the same guidance item. The slot components already uniquely identify every guidance item.

Implementation rule:
- Do not duplicate ID logic across source extractors. Use one shared utility function (`guidance_ids.py:build_guidance_ids()`) that performs normalization + `evhash16` + final `guidance_update_id`.

Implementation note:
- Period linkage uses `HAS_PERIOD -> Period` (fiscal-keyed). Company linkage uses direct `FOR_COMPANY -> Company`.

Expected behavior:
- Same source + same slot => same `id`. Properties updated via SET (latest write wins). Enables enrichment without duplicates.
- Same source + same metric but different period/basis/segment => different `id` (different slot).
- Same source + same slot but changed values/conditions/qualitative => **same `id`**, properties overwritten. evhash changes as a stored property for change detection.
- Different source + same metric/period/basis/segment => different `id` (different source in slot). Each source gets its own node.
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

**Dedup rule**: Dedup is enforced by deterministic slot-based `GuidanceUpdate.id` (§2A). Same slot = same node. MERGE + SET overwrites properties with latest data (enrichment). Changed values/qualifiers/conditions update the existing node, not create a new one. One write per slot per source — read ALL content first, synthesize richest version, write once.
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

## 6. Period Resolution

### Goal

Every GuidanceUpdate links to:
- `FOR_COMPANY -> Company` (direct company edge)
- `HAS_PERIOD -> Period` (fiscal-keyed period in `guidance_period_` namespace)

No Context node. No Unit node. No calendar date computation. No `fiscal_resolve.py` dependency at extraction time.

### Fiscal-Keyed Period Design

Period nodes use a separate `guidance_period_` namespace with fiscal identity as the key. This eliminates the 52/53-week calendar problem (23% of companies) and the forward-period mismatch problem entirely.

**u_id format**: `guidance_period_{cik}_{period_type}_{fiscal_key}`

| Scenario | Example text | u_id | Inputs |
|----------|-------------|------|--------|
| **Quarter (duration)** | "Q3 FY2025" | `guidance_period_320193_duration_FY2025_Q3` | cik + FY + Q |
| **Quarter (instant)** | "cash at end of Q1" | `guidance_period_320193_instant_FY2025_Q1` | cik + FY + Q + instant |
| **Annual (duration)** | "fiscal year 2025" | `guidance_period_320193_duration_FY2025` | cik + FY |
| **Annual (instant)** | "debt at year-end" | `guidance_period_320193_instant_FY2025` | cik + FY + instant |
| **Half year** | "second half" | `guidance_period_320193_duration_FY2025_H2` | cik + FY + half |
| **Long-range (year)** | "by 2028" | `guidance_period_320193_duration_LR_2028` | cik + target year |
| **Long-range (span)** | "2026 to 2028" | `guidance_period_320193_duration_LR_2026_2028` | cik + start/end year |
| **Medium-term** | "over the medium term" | `guidance_period_320193_duration_MT` | cik |
| **Undefined** | (implicit/unclear) | `guidance_period_320193_duration_UNDEF` | cik |

### Period Node Properties

| Property | Type | Example |
|----------|------|---------|
| `u_id` / `id` | String | `guidance_period_320193_duration_FY2025_Q1` |
| `period_type` | String | `"duration"` or `"instant"` |
| `fiscal_year` | Integer / null | `2025` |
| `fiscal_quarter` | Integer / null | `1` |
| `cik` | String | `"320193"` (unpadded) |

No `start_date`. No `end_date`. No date computation. Pure fiscal identity.

### Resolution Steps

```
1. Get CIK from Company node (QUERIES.md 1A):
     MATCH (company:Company {ticker: $ticker})
     WITH company, company.cik AS cik
   Never accept CIK from external input.

2. Get FYE month from 10-K (QUERIES.md 1B):
   Needed only for calendar-to-fiscal mapping (e.g., "December quarter" = Q1 for Apple).
   When source says "Q1" or "Q2" explicitly, use as-is.

3. Build period_u_id via guidance_ids.py:build_period_u_id():
   Simple string concatenation from (cik, period_type, fiscal_year, fiscal_quarter, ...).
   No fiscal_resolve.py. No date computation. No Phase 1/Phase 2 lookup.

4. MERGE Period node in core write query:
     MERGE (p:Period {u_id: $period_u_id})
       ON CREATE SET p.id = $period_u_id,
                     p.period_type = $period_type,
                     p.fiscal_year = $fiscal_year,
                     p.fiscal_quarter = $fiscal_quarter,
                     p.cik = toString(toInteger(company.cik))
```

### Why Fiscal-Keyed (Not Date-Based)

1. **Forward periods don't exist in XBRL yet** — the primary use case for guidance (forward-looking) means XBRL Period nodes for the target period haven't been filed yet. Date-based keys would require computing calendar dates from fiscal identity — exactly what `_compute_fiscal_dates()` does, and which is wrong by 1-6 days for 52/53-week companies.
2. **52/53-week calendar problem** — 177/771 companies (23%) use 52/53-week calendars where fiscal quarter boundaries don't fall on month boundaries. Date computation creates orphan Period nodes that never join with XBRL.
3. **Separate namespace eliminates collision** — `guidance_period_` prefix means guidance Periods never collide with XBRL Period nodes (which use `duration_{start}_{end}` format).
4. **Actuals comparison uses fiscal identity** — a future comparison process matches guidance to actuals via `fiscal_year` + `fiscal_quarter` + `xbrl_qname` + Company, not through shared Period nodes. Python classifies XBRL Period dates via `period_to_fiscal()` at comparison time.
5. **CIK in key because fiscal periods are company-specific** — AAPL FY2025 Q1 and DELL FY2025 Q1 have different date ranges (both Sep FYE but different calendar conventions).

### Calendar-to-Fiscal Mapping

When source uses calendar names ("December quarter"), use FYE to determine fiscal quarter.

**Rule**: Q1 starts in FYE month + 1. When source says "Q1" or "Q2" explicitly, use as-is.

| FYE Month | Example | Q1 | Q2 | Q3 | Q4 |
|-----------|---------|----|----|----|----|
| 9 (Sep) | Apple | Oct-Dec | Jan-Mar | Apr-Jun | Jul-Sep |
| 12 (Dec) | Most | Jan-Mar | Apr-Jun | Jul-Sep | Oct-Dec |
| 6 (Jun) | Microsoft | Jul-Sep | Oct-Dec | Jan-Mar | Apr-Jun |

---

## 7. XBRL Matching

All linking is inline in the same extraction run (no separate process). LLM may propose candidates, but only cache-backed candidates passing deterministic gates are written. Mapping failures never block core Guidance/GuidanceUpdate writes.

### Concept Resolution Design

**Dual approach**: `MAPS_TO_CONCEPT` edge (graph-native join) + `xbrl_qname` property (cross-taxonomy fallback). Both set at extraction time.

- **Edge** (`MAPS_TO_CONCEPT`): Points to the best-match Concept node from the company's current taxonomy window (the same node resolved from the concept cache). Enables direct graph traversal: `(gu)-[:MAPS_TO_CONCEPT]->(con:Concept)<-[:HAS_CONCEPT]-(f:Fact)`. This is the primary join between guidance and actuals — alongside Period and Company, it completes the match on what metric, what time, and who.
- **Property** (`xbrl_qname`): Stores `qname` string (e.g., `us-gaap:Revenues`) which is stable across all taxonomy years. Serves as cross-taxonomy-year fallback when the edge would miss due to taxonomy version differences (different Concept nodes for the same logical concept).
- Null/no-edge when no confident match — no cleanup needed.

**Limitation**: The concept cache is built from the most recent 10-K + subsequent 10-Qs (not date-aware per extraction). Historical backfills for periods before a concept transition (e.g., pre-ASC 606) will get the current qname/edge, not the historical one. The `xbrl_qname` property still enables string-based fallback joins for those periods. Acceptable tradeoff vs. date-aware caching complexity.

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
WITH DISTINCT dim_u_id, mem_u_id
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

### Concept Resolution Gate (sets `gu.xbrl_qname` + `MAPS_TO_CONCEPT` edge)

For each metric in the pattern map:
1. Find all qnames in the concept cache that match the include pattern(s) and exclude pattern(s).
2. If exactly one qname matches → use it.
3. If multiple match → pick the one with highest usage count from the cache.
4. If zero match → `xbrl_qname = null`, no edge.
5. Mapping is **basis-independent**: GAAP, non-GAAP, and unknown guidance all get mapped. Basis filtering happens at comparison query time, not at mapping time.
6. Set property + edge on GuidanceUpdate via `ON CREATE SET` / `MERGE` only. No implicit re-extraction updates. If concept cache improves, update via a separate migration query, not through re-extraction.
7. Edge target: `MATCH (con:Concept {qname: $resolved_qname})` from the concept cache. If multiple Concept nodes share the same qname (different taxonomy years), pick the one from the company's current taxonomy window (same filing set as the cache).

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
MATCH (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (gu)-[:HAS_PERIOD]->(p:Period)
WHERE gu.given_date <= $pit_date
MATCH (gu)-[:FROM_SOURCE]->(src)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(m:Member)
RETURN g.label AS metric, gu.xbrl_qname AS xbrl_concept,
       gu.given_date, gu.period_type, gu.fiscal_year, gu.fiscal_quarter,
       gu.segment, gu.basis_norm, gu.basis_raw, gu.low, gu.mid, gu.high,
       gu.canonical_unit, gu.derivation, gu.qualitative, gu.quote,
       gu.section, gu.conditions,
       labels(src)[0] AS source_type, src.id AS source_id,
       m.label AS xbrl_member
ORDER BY g.label, gu.given_date, gu.id
```

### Latest value per guidance tag + basis

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE gu.given_date <= $pit_date
WITH g, gu.basis_norm AS basis_norm, gu.segment AS segment, gu ORDER BY gu.given_date DESC, gu.id DESC
WITH g, basis_norm, segment, collect(gu)[0] AS latest
RETURN g.label AS metric, basis_norm, segment, latest.basis_raw, latest.segment,
       latest.low, latest.mid, latest.high, latest.canonical_unit, latest.qualitative,
       latest.given_date, latest.fiscal_year, latest.fiscal_quarter
```

### Accuracy comparison (side note — predictor runs this, not guidance system)

Compares guidance values to XBRL actuals using `xbrl_qname` + fiscal identity as the join key. This is NOT part of the extraction pipeline. Note: XBRL Fact periods use date-based keys; matching requires `period_to_fiscal()` classification on the XBRL side (Python-side, not in this Cypher).

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE gu.xbrl_qname IS NOT NULL
// Strict mode: only GAAP-to-GAAP. Remove filter for proxy/flagged comparison.
  AND gu.basis_norm = 'gaap'
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept {qname: gu.xbrl_qname})
MATCH (f)-[:IN_CONTEXT]->(fctx:Context)-[:FOR_COMPANY]->(c)
WHERE f.is_numeric = '1'
  AND (fctx.member_u_ids IS NULL OR fctx.member_u_ids = [])
// Fiscal identity matching done Python-side via period_to_fiscal() on XBRL Period dates
// matched against gu.fiscal_year + gu.fiscal_quarter
// Deterministic tie-break if multiple facts match (e.g., restated values)
WITH g.label AS metric, gu.mid AS guided, toFloat(f.value) AS actual,
     gu.basis_norm, gu.fiscal_year, gu.fiscal_quarter, f.id AS fact_id
ORDER BY fact_id DESC
WITH metric, guided, collect(actual)[0] AS actual, basis_norm,
     fiscal_year, fiscal_quarter
RETURN metric, guided, actual, actual - guided AS surprise, basis_norm,
       fiscal_year, fiscal_quarter
```

---

## 10. Trigger Integration

### Auto Trigger (Primary) + SDK Manual Modes (Backfill/Reprocess)

Execution path: Claude SDK `query(...)` with `tools={'type':'preset','preset':'claude_code'}` runs Claude Code (loading `.claude/`), and slash command `/guidance-inventory ...` triggers the guidance skill chain.
`Task subagent_type=...` is agent/subagent spawning orchestration and is not the skill invocation path.

Primary execution:
- Auto-trigger per asset, immediately when asset-ready gate passes (canonical text fully extracted and persisted).
- Day-1 coverage: `8k`, `transcript`, `10q`, `10k`, `news` (all source types enabled).

**SDK deployment note**: The guidance write path uses two independent Neo4j connections — MCP server (reads in Steps 1-2) and `guidance_write.sh` → `guidance_writer.py` (writes in Step 5). Both currently hardcode `bolt://localhost:30687`. For SDK deployment, ensure both derive their connection config from the same source (e.g., a single `.env` file or SDK-injected env vars) to prevent config drift between reads and writes.

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
   ├── Company + CIK (QUERIES.md 1A)
   ├── FYE from 10-K (QUERIES.md 1B)
   ├── Warmup XBRL caches once/company/run (§7):
   │     concept usage cache + member cache (with CIK pad normalization)
   ├── Query existing Guidance nodes:
   │     MATCH (g:Guidance)<-[:UPDATES]-(gu:GuidanceUpdate)
   │           -[:FOR_COMPANY]->(c:Company {ticker: $ticker})
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
   ├── Canonicalize numeric scale + canonical_unit (§2A) before hashing
   ├── Validate basis rule: if qualifier not explicit in metric quote span → basis_norm = unknown
   ├── Build period_u_id via guidance_ids.py:build_period_u_id() (§6 — string concatenation, no date math)
   ├── Resolve xbrl_qname from concept cache (§7): pattern match → highest usage → set or null
   ├── Apply member confidence gate (§7)
   └── If uncertain: keep core item write, set xbrl_qname=null, skip uncertain member edges

3. PER ITEM: WRITE TO GRAPH
   ├── Compute deterministic IDs via shared utility (§2A): `guidance_id`, `evhash16`, `guidance_update_id`
   ├── MERGE Guidance node: MERGE (g:Guidance {id: $guidance_id})
   │     ON CREATE SET g.label = $label, g.aliases = coalesce($aliases, []), g.created_date = toString(date())
   │     ON MATCH SET g.aliases = reduce(acc = [], a IN (coalesce(g.aliases, []) + coalesce($aliases, [])) |
   │       CASE WHEN a IS NULL OR a IN acc THEN acc ELSE acc + a END)
   ├── MERGE Period node (§6)
   ├── MERGE GuidanceUpdate node: MERGE (gu:GuidanceUpdate {id: $guidance_update_id})
   │     ON CREATE SET gu.created = $created_ts
   │     SET gu.evhash16 = $evhash16, gu.xbrl_qname = $xbrl_qname, gu += $all_properties
   │     // Slot-based ID + SET = latest write wins. Enrichment on rerun, no duplicates.
   ├── Link: (gu)-[:UPDATES]->(g)
   ├── Link: (gu)-[:FROM_SOURCE]->(source)
   ├── Link: (gu)-[:FOR_COMPANY]->(company)
   ├── Link: (gu)-[:HAS_PERIOD]->(period)
   ├── No linked-list write step (ordering is query-time; §8)
   ├── Link XBRL concept if confident (§7): MAPS_TO_CONCEPT edge (0..1)
   └── Link XBRL members if confident (§7): MAPS_TO_MEMBER edges (0..N)
```

### Initial Build (new company)

Process all historical sources chronologically (oldest first). Per earnings event: 8-K → news → transcript → 10-Q. Each extraction adds to the graph incrementally.

### Idempotency & Enrichment

Idempotency is slot-based. Do not pre-check with a broad query. Compute deterministic slot-based ID (§2A), then:
```cypher
MERGE (gu:GuidanceUpdate {id: $guidance_update_id})
  ON CREATE SET gu.created = $created_ts
  SET gu.evhash16 = $evhash16, gu += $all_properties
RETURN gu
```
- **First write**: MERGE creates node, ON CREATE SET stamps `created`, SET writes all properties.
- **Rerun/enrichment**: MERGE matches existing node (same slot), SET overwrites all properties with latest data. `created` preserved. No duplicates.
- **Self-healing**: Pipeline restarts (e.g., context compaction) are harmless — second pass writes to the same nodes as the first pass.

### Reprocessing

For normal reruns: just rerun. MERGE + SET overwrites properties automatically. Delete-before-rerun is only needed when the ID scheme itself changes (e.g., migration from evhash-in-ID to slot-only ID).

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
| 3 | GuidanceUpdate node | Per-mention, 19 fields as properties (includes `basis_norm` + `basis_raw`, `canonical_unit`) with direct `HAS_PERIOD` and `FOR_COMPANY` edges |
| 4 | Company association | Direct `FOR_COMPANY` edge from GuidanceUpdate to Company (Context removed) |
| 5 | Ordering model | No linked list. Chronological ordering is query-time using `ORDER BY given_date, id` per Guidance+Company. |
| 6 | Action types | None stored — deterministic query-time derivation from timeline |
| 7 | Supersession | None — latest by `given_date` (tie-break `id`) is current |
| 8 | Anchor rule | None — first in timeline is implicit anchor |
| 9 | Source priority | None — process chronologically, attribute to source |
| 10 | Synthesis pass | None — graph structure handles it |
| 11 | Output format | Cypher query for predictor context (no markdown) |
| 12 | Trigger | Auto-trigger per asset at asset-ready ingest (primary). SDK `single`/`initial` retained for backfill/reprocess. Extraction writes, prediction reads. |
| 13 | News filtering | Benzinga channels: Guidance, Earnings, Earnings Beats/Misses, Previews, Management |
| 14 | XBRL linking | Concept via `MAPS_TO_CONCEPT` edge (graph join) + `xbrl_qname` property (cross-taxonomy fallback) on GuidanceUpdate. Member via `MAPS_TO_MEMBER` edge (0..N). Dimension links dropped. Basis-independent mapping; basis filtering at query time. |
| 15 | Fiscal periods | Fiscal-keyed separate namespace (`guidance_period_` prefix). No date computation at extraction time. `get_derived_fye()` for FYE month only. `fiscal_to_dates()` / `fiscal_resolve.py` not used by extraction (kept for future actuals comparison). |
| 16 | Metric normalization | 12-metric canonical list with aliases (§4). Non-exhaustive — LLM creates new Guidance nodes as needed. |
| 17 | Segment handling | Property on GuidanceUpdate + `MAPS_TO_MEMBER` with 0..N matches when confident; `Total` means company-wide/default semantics |
| 18 | Analyst estimates | Deferred. Note for future. |
| 19 | Accuracy tracking | Predictor's job, not guidance system |
| 20 | Execution mode | SDK-compatible, non-interactive |
| 21 | Missing data | Note for next round, not hard-fail |
| 22 | Context removal | Context node removed. Was a 1:1 passthrough (one per GuidanceUpdate, `member_u_ids=[]`, `dimension_u_ids=[]`). Replaced by direct `FOR_COMPANY` edge. |
| 23 | Basis tracking | `basis_norm` (`gaap`/`non_gaap`/`constant_currency`/`unknown`) + `basis_raw` (verbatim). Assign basis only when explicit in the same metric quote span; else `unknown`. |
| 24 | Per-asset extraction | Extraction MUST route by source type before LLM. Each doc asset has separate scan scope, inclusion/exclusion rules. |
| 25 | ~~Merged into #16~~ | — |
| 26 | Deterministic IDs | `Guidance.id = guidance:{label_slug}`. `GuidanceUpdate.id = gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}` — slot-only, no evhash in ID. evhash16 is a stored property for change detection. MERGE on slot ID + SET all properties (latest write wins). Rationale: LLM text non-determinism made evhash unstable across runs, causing duplicate nodes for the same guidance item. |
| 27 | LLM governance | LLM proposes extraction + basis/link candidates; deterministic validator enforces canonicalization, basis rule, period resolution, and confidence gates pre-write. |
| 28 | Derivation enum | Extended to `floor`, `ceiling`, `comparative` to avoid fabricating values for one-sided or relative guidance. |
| 29 | News reaffirm guardrail | Reaffirm/maintain language in news sets reaffirm flag in `conditions`; extractor keeps exact source values (no tolerance-based rewrites). |
| 30 | Segment normalizer | Use light singularization + small synonym map for stable member matching (`services`→`service`, `products`→`product`). |
| 31 | Period/company linkage | GuidanceUpdate links directly to `Period` (fiscal-keyed), `Company` (direct `FOR_COMPANY`), and exact source node. No Context or Unit intermediaries. |
| 32 | XBRL bridge policy | Only `Concept` and `Member` are true XBRL bridges (`MAPS_TO_CONCEPT` 0..1, `MAPS_TO_MEMBER` 0..N). `Period` uses separate `guidance_period_` namespace. `Context` removed. `Unit` demoted to `canonical_unit` property. No direct `Dimension`/`Domain` edges. |
| 33 | Neo4j write path | Reuse `Neo4jManager` session/driver/retry infrastructure only. Write guidance nodes via **direct Cypher MERGE** transactions (like `neograph/mixins/news.py`), not via the `merge_nodes()`/`merge_relationships()` dataclass path. Rationale: (1) avoids shared-surface coupling with XBRL relationship key constraints; (2) avoids adding entries to shared `NodeType`/`RelationType` enums. Note: `:Guidance` label is clean — current XBRL guidance concepts are stored as `:Concept` with `category = "Guidance"`, not under the `:Guidance` label (0 nodes, verified). Validation: all guidance nodes must have `id` prefix `guidance:`, all GuidanceUpdate nodes must have `id` prefix `gu:`. |

---

## 13. Reusable Content

| Content | Source | Action |
|---------|--------|--------|
| `period_to_fiscal()` | `fiscal_math.py:13` | Reuse directly (calendar→fiscal) |
| `get_derived_fye()` | `get_quarterly_filings.py:244` | Reuse directly |
| `fiscal_to_dates()` | `get_quarterly_filings.py:67` | Not used by guidance extraction (fiscal-keyed Periods eliminate date computation). Kept for future actuals comparison process. |
| Metric normalization | `guidance-extract.md:258-269` | Carry forward (§4) |
| `Neo4jManager` session/driver | `neograph/Neo4jManager.py` | Reuse session plumbing, retry decorators, `execute_cypher_query()`. Do NOT use `merge_nodes()`/`merge_relationships()` for guidance writes — use direct Cypher MERGE (Decision #33). |
| News write pattern | `neograph/mixins/news.py:278-329` | Reference pattern: direct `MERGE (n:Label {id: $id}) ON CREATE SET ... ON MATCH SET ...` via `self.manager.driver.session()`. Follow this for guidance. |
| `Period` dataclass | `XBRL/xbrl_basic_nodes.py:87` | Not reused for guidance — guidance Periods use fiscal-keyed `guidance_period_` namespace (§6), not date-based `duration_{start}_{end}`. |
| Source extraction hints | `guidance-extract.md:146-199` | Carry forward (§3) |
| Derivation rules | `guidance-extract.md:229-237` | Carry forward (§5) |
| Segment rules | `guidance-extract.md:242-252` | Carry forward |
| ID normalization utility | `guidance_ids.py` | `build_guidance_ids()` — single entry point for slugging, unit/scale canonicalization, `evhash16`, and `guidance_update_id` assembly (§2A). `build_period_u_id()` — fiscal-keyed Period u_id construction (§6). 60 tests. |
| Cypher queries | `guidance-inventory/QUERIES.md` | Keep, fix labels |
| Fiscal calendar | `guidance-inventory/FISCAL_CALENDAR.md` | Deleted/superseded. Fiscal-keyed Periods (§6) eliminate date computation entirely. |
| Evidence standards | `evidence-standards/SKILL.md` | Load during extraction |
| AAPL benchmark | `sampleGuidance_byAgentTeams.md` | Quality target |

---

## 14. Files to Update

| File | Status | Action Taken / Needed |
|------|--------|----------------------|
| `guidance-extract.md` (agent) | **DONE** (v3.0) | Rewritten. Graph-native output, fiscal-keyed Periods, direct FOR_COMPANY, MAPS_TO_CONCEPT/MEMBER edges, script invocations for deterministic validation. |
| `guidance-inventory/SKILL.md` | **DONE** (v3.0) | Rewritten as reference doc. Schema, fields, validation, write patterns, XBRL matching. Removed predictor refs, dead file links. Write path references `guidance_writer.py`. |
| `guidance-inventory/QUERIES.md` | **DONE** (v2.10) | ~42 read-only queries. Source-fetch + warmup caches + fulltext. Fixed: 3B phantom null, null-date guards, MD&A apostrophe, QuestionAnswer types, 3C fallback, execution order. Writes go through `guidance_writer.py`. |
| `guidance-inventory/OUTPUT_TEMPLATE.md` | **DONE** (deleted) | Fully superseded by graph-native output. |
| `guidance-inventory/FISCAL_CALENDAR.md` | **DONE** (deleted) | Superseded by `fiscal_resolve.py` + SKILL.md §9. |
| `guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | **DONE** (v1.3) | Scan scope, speaker hierarchy, PR vs Q&A, QuestionAnswer fallback (3C), quote prefixes. |
| `guidance-inventory/reference/PROFILE_8K.md` | **DONE** (v1.1) | EX-99.* + Item 2.02/7.01, boilerplate exclusion, table handling, fetch order. |
| `guidance-inventory/reference/PROFILE_NEWS.md` | **DONE** (v1.1) | Channel filter, analyst exclusion, reaffirmation handling, title/body scan. |
| `guidance-inventory/reference/PROFILE_10Q.md` | **DONE** (v1.2) | MD&A primary (10-Q ~99%, 10-K ~98%), bounded fallback, 10-K apostrophe variant, forward-looking strictness. |
| `guidance_ids.py` | **DONE** (60 tests) | `build_guidance_ids()` + `build_period_u_id()` + unit canonicalization + evhash16. Fiscal-keyed Period u_id construction. |
| ~~`fiscal_resolve.py`~~ | **DELETED (2026-03-21)** | Was dead code with FYE bugs. Period resolution now in `guidance_write_cli.py` 4-step cascade (SEC cache + prediction + corrected FYE). |
| `guidance_writer.py` | **DONE** (62 tests) | v3.0 architecture: direct FOR_COMPANY edge, fiscal-keyed Period MERGE, canonical_unit property, MAPS_TO_CONCEPT edge (0..1), MAPS_TO_MEMBER edges (0..N). |
| `guidance_write_cli.py` | **DONE** (18 tests) | CLI wrapper: reads JSON, computes IDs via `build_guidance_ids()`, calls `write_guidance_batch()`. Concept inheritance (same label → same xbrl_qname). Supports `--dry-run` / `--write`. Overrides feature flag at runtime. |
| `guidance_write.sh` | **DONE** | Shell wrapper: activates venv, force-sets Neo4j env vars to match MCP server (`bolt://localhost:30687`), runs CLI. |
| `earnings-orchestrator.md` | **DONE** | Step 0 removed, I5 = graph query. |

**Next steps after §14**:
1. AAPL transcript dry-run validation (shadow mode, compare against `sampleGuidance_byAgentTeams.md`)
2. Shadow run on 3+ companies, 3+ source types → enable writes

---

## 15. Implementation Takeaways from Existing Files

Cross-reference audit of `guidance-extract.md` (agent, 365 lines) and `guidance-inventory/` (skill, 550 lines + 3 reference files) against this spec. All resolved before implementation to prevent drift.

### 15A. Architecture: One Agent + Core Skill + Per-Source Profiles

**Pattern**: Follows the existing DataSubAgent convention (agent aided by skill), adapted for read-write extraction.

| Component | File | Role |
|-----------|------|------|
| Agent | `.claude/agents/guidance-extract.md` | Rewritten. Routes by `source_type`. Fetch → extract → validate → write. |
| Core skill | `.claude/skills/guidance-inventory/SKILL.md` | Rewritten as reference doc auto-loaded by agent. Schema, fields, validation, write patterns, XBRL matching. |
| Transcript profile | `guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | Scan scope, speaker hierarchy, prepared remarks vs Q&A handling. |
| 8-K profile | `guidance-inventory/reference/PROFILE_8K.md` | EX-99.* + Item 2.02/7.01 scan, boilerplate exclusion, table handling. |
| News profile | `guidance-inventory/reference/PROFILE_NEWS.md` | Channel filter (applied pre-LLM), title/body, company-vs-analyst distinction. |
| 10-Q/10-K profile | `guidance-inventory/reference/PROFILE_10Q.md` | MD&A primary, bounded fallback, legal/risk exclusion. |
| Queries | `guidance-inventory/QUERIES.md` | Updated with agent's source-fetch queries + §7 warmup cache queries. |

**Agent tool requirements** (rewritten frontmatter):

```yaml
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher   # Source fetch + warmup caches
  - mcp__neo4j-cypher__write_neo4j_cypher   # Graph writes (MERGE pattern)
  - Bash                                     # Python utilities (guidance_ids.py, fiscal wrapper)
  - TaskList                                 # Task context (team workflows)
  - TaskGet
  - TaskUpdate
  - Write                                    # Dry-run output files
  - Read                                     # Source profiles + reference files
```

**Why one agent, not per-source agents**: 80% of logic is shared across all source types (validation, ID computation, Period resolution, XBRL matching, graph writes). Only scan scope and extraction hints vary (~20%). Multiple agents would duplicate the shared logic. The per-source profiles in `reference/` handle the 20% that varies.

### 15B. Source Content Queries (Carry Forward from Agent)

The agent's Cypher queries (lines 52-123) are the canonical source-fetch layer. QUERIES.md is incomplete:

| Query | In Agent? | In QUERIES.md? | Action |
|-------|-----------|---------------|--------|
| Exhibit content (`HAS_EXHIBIT → ExhibitContent`) | Yes (line 54) | Partial (line 64) | Update with agent's version |
| Section content (`HAS_SECTION → ExtractedSectionContent`) | Yes (line 60) | Missing | Add |
| Filing text (`HAS_FILING_TEXT → FilingTextContent`) | Yes (line 67) | Missing | Add |
| Structured transcript (prepared_remarks + Q&A) | Yes (lines 96-118) | Missing (only fulltext) | Add — critical for §3 |
| News content (title + body + pub_date) | Yes (line 122) | Missing | Add |
| Transcript fulltext search | — | Yes (line 110) | Keep as supplementary recall |

The agent's structured transcript query (returning `prepared_remarks` and `qa_exchanges` separately) is the most important carry-forward — it directly matches §3's "scan everything (prepared remarks + Q&A)" requirement. QUERIES.md only has fulltext search, which is a recall supplement, not the primary fetch.

### 15C. Per-Source Extraction Profiles

Content for `reference/` files, sourced from agent lines 146-199:

**PROFILE_TRANSCRIPT.md** (agent lines 151-166):
- Prepared remarks: JSON array of speaker statements with position markers
- Speaker hierarchy: CFO formal guidance (richest) > CEO strategic outlook > Q&A specifics
- Operator remarks: skip (procedural, no guidance)
- Q&A: analysts probe for details not in prepared remarks — segment-level, geographic, GAAP vs non-GAAP clarifications, "comfortable with consensus" implied guidance
- Duplicate resolution: one write per slot. Read ALL sections (PR + Q&A) first, synthesize the richest combined version per metric, then write once. Neither PR nor Q&A takes precedence.
- Quote prefix: `[Q&A]` for Q&A, `[PR]` for prepared remarks

**PROFILE_8K.md** (agent lines 147-148):
- Scan order: outlook/guidance sections first, then tables with projections, then footnotes
- GAAP vs non-GAAP: check footnotes for distinction — tables often have both columns
- Skip: pure actuals (past period results), safe-harbor boilerplate (but keep adjacent concrete guidance per §3 safe-harbor proximity rule)

**PROFILE_NEWS.md** (agent lines 170-187):
- Channel filter (§3): applied BEFORE LLM processing using Benzinga `channels` field
- Title: often contains complete guidance. Pattern: `{Company} {Expects/Revises/Reaffirms} {Metric} {Value or Range}`
- Body: may be empty (title has everything), or contains additional metrics/prior values
- Company guidance verbs: "expects", "revises", "reaffirms", "raises", "lowers" → EXTRACT
- Analyst estimates: "versus consensus of", "Est $X", "consensus" → DO NOT extract
- Prior values in news: "(Prior $57,000)" → context only, extract the NEW guidance
- Reaffirm language: annotate in `conditions` per §3 news guardrail

**PROFILE_10Q.md** (agent lines 188-198):
- MD&A primary scan scope
- Financial statement content: JSON structured data, look for footnotes/annotations mentioning expectations
- If zero guidance found in MD&A: one bounded keyword-window pass in broader filing text, excluding legal/risk-heavy sections
- Zero-guidance result: acceptable (not an error)

### 15D. Source Type Mapping (Agent → Spec)

Agent uses content-level types; spec uses filing-level types with `source_key` for content location:

| Agent `source_type` | Spec `source_type` | Spec `source_key` |
|---------------------|--------------------|--------------------|
| `exhibit` | `8k` | `"EX-99.1"`, `"EX-99.2"` |
| `section` (from 8-K) | `8k` | `"Item 2.02"`, `"Item 7.01"` |
| `section` (from 10-Q) | `10q` | `"MD&A"` |
| `section` (from 10-K) | `10k` | `"MD&A"` |
| `filing_text` | `8k`/`10q`/`10k` | Filing-dependent |
| `financial_stmt` | `10q`/`10k` | Statement type |
| `xbrl` | — | Not extracted (actuals only, §3 source #5) |
| `transcript` | `transcript` | `"full"` |
| `news` | `news` | `"title"` |

### 15E. Error Taxonomy (Carry Forward + Extend)

Carry forward from agent lines 131-139, add graph-write states:

| Error | Source | When |
|-------|--------|------|
| `SOURCE_NOT_FOUND` | Agent (line 133) | No rows from source content query |
| `EMPTY_CONTENT` | Agent (line 134) | Rows exist but content empty (per source-type rules from agent lines 135-139) |
| `QUERY_FAILED` | Agent (line 134) | Cypher error |
| `NO_GUIDANCE` | Agent (line 340) | Content parsed, no forward-looking guidance found |
| `WRITE_FAILED` | New | Graph MERGE error |
| `VALIDATION_FAILED` | New | Deterministic validation rejected item (missing citation, bad period, invalid unit) |

Empty-content rules per source type (from agent lines 135-139):
- `exhibit`, `section`, `filing_text`: `strip()==""` → `EMPTY_CONTENT`
- `transcript`: BOTH `prepared_remarks` empty AND `qa_exchanges` empty → `EMPTY_CONTENT`
- `news`: BOTH `title` and `body` empty → `EMPTY_CONTENT`

### 15F. Unit Extensibility (Registry Pattern)

Add `basis_points` and `percent_points` to the §2 canonical unit list. Use registry pattern in `guidance_ids.py`:

Updated §2 field 9 canonical values: `usd`, `m_usd`, `percent`, `percent_yoy`, `percent_points`, `basis_points`, `x`, `count`, `unknown`.

```python
CANONICAL_UNITS = {
    'usd', 'm_usd',                                              # Currency
    'percent', 'percent_yoy', 'percent_points', 'basis_points',  # Ratios
    'x', 'count', 'unknown',                                     # Other
}

UNIT_ALIASES = {
    '$': 'm_usd', 'dollars': 'm_usd',  # per-share labels (EPS/DPS) override to usd
    'b usd': 'm_usd', 'b_usd': 'm_usd', 'billion': 'm_usd',
    'm usd': 'm_usd', 'million': 'm_usd',
    '%': 'percent', 'pct': 'percent',
    '% yoy': 'percent_yoy', 'yoy': 'percent_yoy',
    'bps': 'basis_points', 'bp': 'basis_points',
    '% points': 'percent_points', 'pp': 'percent_points', 'percentage points': 'percent_points',
    'times': 'x', 'multiple': 'x',
}
```

**Method for adding new units as discovered**:
1. LLM proposes a raw unit string during extraction.
2. `canonicalize_unit()` checks `UNIT_ALIASES` → canonical form if matched.
3. No alias match → `canonical_unit = 'unknown'`, raw unit preserved in `unit_raw` property on GuidanceUpdate.
4. Periodic review: query `unit_raw` values on `unknown`-unit GuidanceUpdate nodes → identify patterns → add new canonical mappings.
5. Each addition: one entry in `CANONICAL_UNITS` + alias(es) in `UNIT_ALIASES` + test case in `test_guidance_ids.py`.

`unit_raw`: optional String property on GuidanceUpdate, populated ONLY when `canonical_unit = 'unknown'`. Contains verbatim unit text from source. Not part of the 19 extraction fields — set at validation time (§10 Step 2.5) from raw LLM output. Not included in `evhash16` computation (canonical `canonical_unit` is used in the hash).

Note: Unit is a property (`gu.canonical_unit`) on GuidanceUpdate, not a separate graph node. The registry pattern in `guidance_ids.py` is unchanged — it canonicalizes raw unit strings to one of 9 values. No Unit node MERGE is needed.

### 15G. Period Resolution (Simplified)

Under fiscal-keyed Period design (§6), the extraction pipeline no longer needs `fiscal_to_dates()`, `fiscal_resolve.py`, or date computation. Period u_id is built via `guidance_ids.py:build_period_u_id()` — simple string concatenation from (cik, period_type, fiscal_year, fiscal_quarter).

**What the agent still needs:**
1. **CIK** — from Company node (QUERIES.md 1A)
2. **FYE month** — from 10-K `periodOfReport` (QUERIES.md 1B), needed only for calendar-to-fiscal mapping (e.g., "December quarter" = Q1 for Apple)

**What's eliminated from extraction:**
- `fiscal_resolve.py` CLI wrapper (kept in codebase for future actuals comparison)
- QUERIES.md 1C (Period pre-fetch — only existed to feed `fiscal_resolve.py`)
- `_compute_fiscal_dates()` fallback (no calendar dates computed)
- Phase 1/Phase 2 lookup logic (one path: string concatenation)

`get_derived_fye()` does not need a bridge — its core query can be run directly via MCP and the FYE month extracted by the agent.

### 15H. Feature Flag / Dry-Run Mechanism

Skill argument on agent invocation: `MODE=dry_run|shadow|write`.

| Mode | Behavior |
|------|----------|
| `dry_run` (default) | Extract + validate + ID build. Log results to stdout. No graph writes. |
| `shadow` | Same as dry_run + log exact MERGE Cypher that WOULD execute (with parameters). |
| `write` | Full execution. MERGE to Neo4j. |

Default: `dry_run`. Satisfies Non-negotiable #7 ("Feature flag default must keep writes disabled").

**Two-layer write gate** (defense-in-depth, not competing mechanisms):
1. `MODE` parameter → per-invocation control at agent/skill level. Maps to `dry_run` parameter in `write_guidance_item()`.
2. `ENABLE_GUIDANCE_WRITES` → global feature flag in `config/feature_flags.py` (default `False`). Checked AFTER dry_run, BEFORE write.

Precedence in code (`guidance_writer.py:258-269`): `if dry_run → return` → `if not ENABLE_GUIDANCE_WRITES → skip` → execute write. Both must be permissive for writes to occur. `MODE=write` with `ENABLE_GUIDANCE_WRITES=False` still blocks writes (global gate wins).

Switch to `write` only after the must-pass gates in the Implementation Handoff are satisfied:
1. `test_guidance_ids.py` passes.
2. Shadow run on 3+ companies and 3+ source types.
3. Idempotency check (same source twice → zero new nodes on second run).
4. Regression check (existing ingest behavior unchanged).
5. Canary: 1-2 tickers first, then full rollout.

### 15I. LLM Prompt Content Sources

The agent's quality filters (lines 357-365) belong in the core SKILL.md:

| Filter | Agent Line | Spec Equivalent |
|--------|-----------|----------------|
| Forward-looking only (target period after source date) | 359 | Implicit in §2 (future period guidance) |
| Specificity required (quantitative anchor needed) | 360 | §5 `comparative` derivation handles the edge case |
| Quote max 500 chars (truncate at sentence boundary) | 364 | §2 field 14 |
| 100% recall priority (extract when in doubt) | 355 | Consistent with §3 recall pass |
| No fabricated numbers (qualitative = `implied`, no invented values) | 356 | §5 derivation rules |
| News: company guidance only (ignore analyst estimates) | 357 | §3 per-source rules |

### 15J. Items Fully Superseded (Do Not Carry Forward)

| Old Artifact | Spec Replacement | Status |
|-------------|-----------------|--------|
| Pipe-delimited TSV output (agent Step 4) | Direct MERGE to Neo4j (§10 Step 3) | Dead |
| `OUTPUT_TEMPLATE.md` | Graph-native, Cypher reads (§9) | Dead |
| Supersession chain (`superseded_by` links, SKILL.md lines 316-334) | Query-time `ORDER BY given_date, id` (§8, Decision #5) | Dead |
| Action classification storage (`INITIAL/RAISED/LOWERED`, SKILL.md lines 139-149) | Query-time derivation (Decision #6) | Dead |
| Cumulative markdown file model (`guidance-inventory.md`, SKILL.md lines 340-359) | Graph is the accumulator | Dead |
| Consensus comparison section (SKILL.md lines 227-233) | Predictor's job (Decision #19) | Dead |
| Beat/miss pattern tracking (SKILL.md lines 277-282) | Predictor's accuracy comparison (§9) | Dead |
| Entry ID format `FY25-EPS-001` (SKILL.md line 326) | Deterministic `guidance_update_id` from `guidance_ids.py` (§2A) | Dead |
| `GuidancePeriod`/`GuidanceEntry` Python dataclasses (SKILL.md lines 505-546) | GuidanceUpdate node properties (§2) | Dead |
| TSV file persistence (`gx/{TASK_ID}.tsv`, agent Step 3b) | Graph persistence | Dead |

### 15K. Items Correctly Carried Forward (Verified)

| Item | Agent/Skill Source | Spec Section | Verification |
|------|-------------------|-------------|-------------|
| Metric normalization (8→12 metrics) | Agent lines 258-269 | §4 (expanded) | All 8 originals preserved, 4 added |
| Segment rules (default `Total`) | Agent lines 240-252 | §7 member matching | Same semantics, XBRL Member linking added on top |
| Guidance keywords | Agent + QUERIES.md lines 190-200 | §3 keywords table | Identical |
| "No citation = no node" | SKILL.md line 310 | Non-negotiable #8 | Identical |
| News: company guidance only | Agent lines 181-184 | §3 news per-source rules | Identical |
| Quote max 500 chars | Agent line 364 | §2 field 14 | Identical |
| Forward-looking filter | Agent line 359 | §3 + §5 derivation | Same intent |
| FYE detection from 10-K periodOfReport | SKILL.md line 86, QUERIES.md line 31 | §6 Step 2, §13 | Same query, via MCP directly. Needed for calendar-to-fiscal mapping only. |
| Legacy fiscal calendar examples (AAPL/WMT/MSFT) | Deleted `FISCAL_CALENDAR.md` (archived) | §6 calendar-to-fiscal table | Useful as validation reference |
| Derivation rules (4 original values) | Agent lines 229-237 | §5 (extended to 7) | `explicit/calculated/point/implied` unchanged |
| Empty-content handling per source type | Agent lines 135-139 | §15E (this section) | Carried forward + extended |

---

---

## §16 — K8s Worker: Triggering Guidance Extraction

**Deployed**: `claude-code-worker` in `processing` namespace, KEDA scales 0→7 pods.

### Commands

```bash
# One specific transcript
python3 scripts/trigger-guidance.py --source-id ADBE_2025-06-12T17.00.00-04.00

# All unprocessed transcripts for one company (sequential on 1 pod)
python3 scripts/trigger-guidance.py CRM

# Multiple companies in parallel (1 pod per company, up to 7 pods)
python3 scripts/trigger-guidance.py CRM ADBE MSFT AAPL GOOGL

# Preview what would be queued (don't actually queue)
python3 scripts/trigger-guidance.py --list CRM ADBE

# Dry run (extract but don't write to Neo4j)
python3 scripts/trigger-guidance.py --mode dry_run CRM

# Re-process something already completed
python3 scripts/trigger-guidance.py --force --source-id ADBE_2025-06-12T17.00.00-04.00

# Re-process only failed items
python3 scripts/trigger-guidance.py --retry-failed ADBE

# Everything unprocessed in the database
python3 scripts/trigger-guidance.py --all

# Watch logs
kubectl logs -f -l app=claude-code-worker -n processing
```

### How it works

- Each company gets **one queue item** containing all its transcript IDs
- **One pod** processes all transcripts for a company **sequentially**
- **Multiple companies** → multiple queue items → KEDA scales pods **in parallel** (max 7)
- `ProcessingLog` node in Neo4j tracks status (`in_progress`/`completed`/`failed`) per transcript
- `dry_run` mode skips ProcessingLog — only `write` mode creates ledger entries

### Key files

| File | Purpose |
|------|---------|
| `scripts/trigger-guidance.py` | Queries Neo4j for unprocessed transcripts, pushes to Redis |
| `scripts/earnings_worker.py` | Redis queue consumer, invokes `/guidance-transcript` via SDK |
| `k8s/processing/claude-code-worker.yaml` | Deployment + KEDA ScaledObject |
| `scripts/canary_sdk.py` | Validates SDK + MCP + Skills in K8s pod |

---

*v3.0 | 2026-02-22 | Architecture simplification: Removed Context node (replaced by direct FOR_COMPANY edge). Removed Unit node (demoted to canonical_unit property on GuidanceUpdate). Redesigned Period as fiscal-keyed separate namespace (guidance_period_ prefix, no date computation). Added instant period support. Renamed field #9 from unit to canonical_unit. Updated §1 schema, §6 (Context Resolution → Period Resolution), §9 predictor queries, §10 extraction steps, Decisions #3/#4/#15/#22/#31/#32. Resolved P1 (instant) and P2 (period mismatch). Prior: v2.5 (MAPS_TO_CONCEPT dual approach, Unit XBRL shape).*
