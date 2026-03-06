# Guidance-Specific Queries (S7, S8B, S10)

Queries specific to guidance extraction: existing guidance lookup, guidance node counts, and extraction keywords.

---

## 7. Existing Guidance Lookup

Query existing guidance graph nodes before extraction to provide context to LLM.

### 7A. Existing Guidance Tags for Company

```cypher
MATCH (g:Guidance)<-[:UPDATES]-(gu:GuidanceUpdate)
      -[:FOR_COMPANY]->(c:Company {ticker: $ticker})
RETURN DISTINCT g.label, g.id
```
**Usage**: Feed existing Guidance labels to LLM so it reuses canonical metric names rather than creating duplicates.

### 7B. Latest Guidance per Metric

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WITH g, gu ORDER BY gu.given_date DESC, gu.id DESC
WITH g, collect(gu)[0] AS latest
RETURN g.label, latest.given_date, latest.low, latest.mid, latest.high,
       latest.canonical_unit, latest.basis_norm, latest.segment,
       latest.fiscal_year, latest.fiscal_quarter
```

### 7C. Check Existing GuidanceUpdate by ID

Idempotency check — compute ID first, then verify it doesn't already exist.

```cypher
MATCH (gu:GuidanceUpdate {id: $guidance_update_id})
RETURN gu.id, gu.given_date, gu.evhash16
```

### 7D. All GuidanceUpdates for Source

Check what guidance was already extracted from a specific source document.

```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src)
WHERE src.id = $source_id
MATCH (gu)-[:UPDATES]->(g:Guidance)
RETURN g.label, gu.id, gu.given_date, gu.low, gu.mid, gu.high,
       gu.canonical_unit, gu.basis_norm, gu.segment
ORDER BY g.label
```

### 7E. Full GuidanceUpdate Readback for Source

Reads back all properties of existing GuidanceUpdates from a source. Used by `guidance-qa-enrich` to load Phase 1 items as base for Q&A enrichment.

```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src)
WHERE src.id = $source_id
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(c:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(m:Member)
RETURN g.label, g.id AS guidance_id,
       gu.id, gu.evhash16, gu.given_date, gu.period_scope,
       gu.time_type, gu.fiscal_year, gu.fiscal_quarter, gu.segment,
       gu.low, gu.mid, gu.high, gu.canonical_unit,
       gu.basis_norm, gu.basis_raw, gu.derivation,
       gu.qualitative, gu.quote, gu.section,
       gu.source_key, gu.source_type, gu.conditions,
       gu.xbrl_qname, gu.unit_raw,
       gp.u_id AS period_u_id,
       gp.start_date AS gp_start_date, gp.end_date AS gp_end_date,
       collect(DISTINCT m.u_id) AS member_u_ids
ORDER BY g.label, gu.segment
```

### 7F. Prior-Transcript Guidance Baseline (Completeness Check)

Returns all labels this company has ever guided on via transcripts, with frequency and recency. Used by `guidance-qa-enrich` to detect missing items after Q&A processing.

```cypher
MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance),
      (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker}),
      (gu)-[:FROM_SOURCE]->(t:Transcript)
WHERE gu.given_date < $current_given_date
WITH g.label AS label,
     max(gu.given_date) AS last_seen,
     count(DISTINCT gu.given_date) AS frequency
RETURN label, last_seen, frequency
ORDER BY frequency DESC
```

**Usage**: After Step 4 Q&A processing, compare current extraction labels against this baseline. Any previously-guided label absent from the current set triggers a targeted re-scan of Q&A exchanges for that metric.

---

## 8B. Existing Guidance Node Count

```cypher
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (gu)-[:UPDATES]->(g:Guidance)
RETURN count(DISTINCT g) AS guidance_tags,
       count(gu) AS guidance_updates,
       min(gu.given_date) AS earliest,
       max(gu.given_date) AS latest
```

---

## 10. Guidance Extraction Keywords

When searching via fulltext or scanning content, use these terms:

| Category | Keywords |
|----------|----------|
| **Forward-looking** | expects, anticipates, projects, forecasts, outlook, looking ahead |
| **Guidance** | guidance, range, target, between X and Y, approximately |
| **Periods** | Q1-Q4, full year, fiscal year, FY, for the quarter, second half |
| **Metrics** | EPS, earnings per share, revenue, sales, margin, income, cash flow |
| **Revisions** | raises, lowers, maintains, reaffirms, withdraws, narrows, widens |
| **Qualitative** | low single digits, double-digit, mid-teens, high single digits |
| **Conditional** | assumes, contingent on, excluding, subject to |

**Fulltext query construction**: Combine with OR for broad recall:
```
guidance OR outlook OR expects OR anticipates OR "full year" OR "fiscal year"
```
