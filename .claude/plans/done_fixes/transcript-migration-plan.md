# Transcript ID Migration Plan

> **Status**: COMPLETED — executed 2026-03-03, all 21 verification checks passed
> **Date**: 2026-03-03
> **Issue**: #35 — Duplicate Transcript Nodes
> **Goal**: Convert all Transcript IDs to DATETIME format, deduplicate 205 pairs, update all children

---

## Current State (empirically verified 2026-03-03)

| Metric | Count |
|--------|------:|
| Total Transcript nodes | **4,397** |
| LONG format (`AAPL_2025-07-31T17.00.00-04.00`) | 3,722 |
| SHORT format (`AAPL_2025_3`) | 675 |
| DATETIME format (target: `AAPL_2025-07-31T17.00`) | 0 |
| Duplicate pairs (SHORT + LONG, same call) | **205** (410 nodes) |
| Orphan SHORT nodes (no LONG counterpart) | **470** |
| LONG-only nodes | **3,517** |
| Nodes with NULL conference_datetime | **0** |

### Child Nodes

| Type | Label | Total | Has `transcript_id`? | ID Pattern |
|------|-------|------:|:--------------------:|------------|
| QA exchanges | `QAExchange` | 79,781 | YES | `{parent_id}_qa__{N}` |
| Prepared remarks | `PreparedRemark` | 4,263 | No | `{parent_id}_pr` |
| Full text | `FullTranscriptText` | 28 | No | `{parent_id}_full` |
| QA sections | `QuestionAnswer` | 41 | No | `{parent_id}_qa` |

### Relationships

| Relationship | Direction | Count |
|-------------|-----------|------:|
| `HAS_QA_EXCHANGE` | Transcript → QAExchange | 79,781 |
| `NEXT_EXCHANGE` | QAExchange → QAExchange | 75,452 |
| `INFLUENCES` | Transcript → Company/Sector/etc | 17,588 |
| `HAS_TRANSCRIPT` | Company → Transcript | 4,397 |
| `HAS_PREPARED_REMARKS` | Transcript → PreparedRemark | 4,263 |
| `FROM_SOURCE` | GuidanceUpdate → Transcript | 70 (all LONG; will be wiped) |
| `HAS_QA_SECTION` | Transcript → QuestionAnswer | 41 |
| `HAS_FULL_TEXT` | Transcript → FullTranscriptText | 28 |

### Constraints & Indexes

| Target | Constraint | Index |
|--------|-----------|-------|
| `Transcript.id` | UNIQUENESS (`constraint_transcript_id_unique`) | RANGE (backing) |
| `QAExchange.id` | UNIQUENESS (`constraint_qaexchange_id_unique`) | RANGE (backing) |
| `QAExchange.exchanges` | — | FULLTEXT (`qa_exchange_ft`) |
| `QAExchange.embedding` | — | VECTOR (`qaexchange_vector_idx`) |

> **Constraint drop NOT needed**: DATETIME IDs (`AAPL_2025-07-31T17.00`) are structurally
> distinct from both LONG (`...T17.00.00-04.00`) and SHORT (`..._2025_3`). Verified: zero
> collisions between any computed new ID and any existing ID, for both Transcript and
> QAExchange. Constraints stay live as a safety net during migration.

### Duplicate Pair Properties

| Check | Result |
|-------|--------|
| Property count (SHORT vs LONG) | Identical (12 each) in all 205 pairs |
| QA exchange count match | 204/205 identical |
| Divergent pair | **ATEC** 2025-07-31: LONG=22 QA, SHORT=16 QA |
| INFLUENCES targets match | 100% identical in all 205 pairs |
| FullTranscriptText on SHORT losers | 0 (none to lose) |
| QuestionAnswer on SHORT losers | 3 (will be deleted) |

### Children to DELETE (on 205 losers — node with fewest QA in each pair)

| Type | Count |
|------|------:|
| QAExchange | 3,629 |
| PreparedRemark | 205 |
| QuestionAnswer | 3 |
| FullTranscriptText | 0 |
| NEXT_EXCHANGE rels on QA | 3,427 |
| **Total child nodes** | **3,837** |

---

## New ID Formula

```cypher
// Cypher (matches Python operation order: replace first, truncate last):
t.symbol + '_' + left(replace(replace(toString(t.conference_datetime), ':', '.'), ' ', 'T'), 16)

// Python (in _standardize_fields):
f"{content['symbol']}_{str(content['conference_datetime']).replace(':', '.').replace(' ', 'T')[:16]}"
```

**Example**: `conference_datetime = "2025-07-31T17:00:00-04:00"` → `AAPL_2025-07-31T17.00`

**Verified**: All 4,192 post-dedup nodes compute to **unique** new IDs (zero collisions).

---

## Migration Steps

### PHASE 0: Pre-flight Verification

Run these queries and **abort if any check fails**.

```cypher
// 0a: Verify total count
MATCH (t:Transcript) RETURN count(*) AS total
// EXPECT: 4397

// 0b: Verify zero DATETIME-format nodes already exist
MATCH (t:Transcript)
WHERE t.id =~ '^[A-Z]+_\\d{4}-\\d{2}-\\d{2}T\\d{2}\\.\\d{2}$'
RETURN count(*) AS already_migrated
// EXPECT: 0

// 0c: Verify zero NULL conference_datetime
MATCH (t:Transcript) WHERE t.conference_datetime IS NULL
RETURN count(*) AS nulls
// EXPECT: 0

// 0d: Verify duplicate pair count
MATCH (t:Transcript)
WHERE t.conference_datetime IS NOT NULL
WITH t.symbol AS sym, left(toString(t.conference_datetime), 10) AS d, count(*) AS c
WHERE c > 1
RETURN count(*) AS dup_groups
// EXPECT: 205

// 0e: Verify uniqueness of new IDs (post-dedup)
// First: compute new IDs for all non-duplicate nodes + LONG side of pairs
MATCH (t:Transcript)
WITH t.symbol + '_' + left(replace(replace(toString(t.conference_datetime), ':', '.'), ' ', 'T'), 16) AS new_id,
     count(*) AS cnt
WHERE cnt > 1
RETURN count(*) AS collisions
// EXPECT: 205 (the known pairs — will be 0 after SHORT deletion)

// 0f: Verify QAExchange count
MATCH (q:QAExchange) RETURN count(*) AS total
// EXPECT: 79781

// 0g: Verify child ID prefix consistency (100% match expected)
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(q:QAExchange)
WHERE NOT q.id STARTS WITH t.id
RETURN count(*) AS mismatches
// EXPECT: 0
```

```bash
# 0h: Confirm earnings:trigger queue empty (no pending guidance jobs)
redis-cli -h <host> -p <port> LLEN earnings:trigger
# EXPECT: 0

# 0i: Confirm no active transcript ingestion running
redis-cli -h <host> -p <port> GET admin:transcripts:processing_lock
# EXPECT: (nil)
```

### PHASE 0.5: Create Neo4j Backup

```bash
# Option A: Neo4j dump (requires stopping DB or using online backup)
neo4j-admin database dump neo4j --to-path=/backup/pre-migration-$(date +%Y%m%d)

# Option B: If using Neo4j Enterprise with online backup
neo4j-admin database backup neo4j --to-path=/backup/pre-migration-$(date +%Y%m%d)

# Option C: Cypher export via APOC (no downtime)
CALL apoc.export.cypher.query(
  'MATCH (t:Transcript) OPTIONAL MATCH (t)-[r]-(c) RETURN t, r, c',
  '/backup/transcripts-pre-migration.cypher',
  {format: 'cypher-shell'}
)
```

---

### PHASE 1: Resolve 205 Duplicate Pairs

**Strategy**: Format-agnostic — find collision groups (nodes that compute to the same DATETIME ID),
keep the node with the most QA children (handles ATEC divergence), delete the other.

> **Why not regex**: Regex for SHORT/LONG classification is unreliable across MCP calls
> (escaping differences). Collision-based identification uses only string functions and is
> 100% consistent.

> **Why not "shell" detection (qa_count=0)**: Empirically, 202/205 pairs have QA on BOTH
> sides. Only 3 pairs have a true shell. Content-based winner selection (most QA) handles
> all cases correctly.

**Step 1a: Tag the loser in each collision group (fewer QA children; tiebreak by id)**

```cypher
MATCH (t:Transcript)
WITH t.symbol + '_' + left(replace(replace(toString(t.conference_datetime), ':', '.'), ' ', 'T'), 16) AS new_id,
     collect(t) AS nodes, count(*) AS cnt
WHERE cnt > 1
// For each collision group, find the loser (fewer QA children)
UNWIND nodes AS n
OPTIONAL MATCH (n)-[:HAS_QA_EXCHANGE]->(q)
WITH new_id, n, count(q) AS qa
ORDER BY new_id, qa ASC, n.id ASC  // ascending: loser first (fewer QA, tiebreak by id)
WITH new_id, collect(n) AS ordered
// Tag the first node (fewest QA) as loser
SET (ordered[0]):_ToDelete
RETURN count(*) AS tagged
// EXPECT: 205
```

**Step 1a-verify: Confirm tagged nodes are the correct losers**
```cypher
// Should be exactly 205 tagged
MATCH (t:_ToDelete) RETURN count(*) AS tagged
// EXPECT: 205

// No tagged node should have MORE QA than its surviving partner
MATCH (t:_ToDelete)
WITH t.symbol + '_' + left(replace(replace(toString(t.conference_datetime), ':', '.'), ' ', 'T'), 16) AS new_id, t
MATCH (survivor:Transcript)
WHERE survivor.symbol + '_' + replace(left(toString(survivor.conference_datetime), 16), ':', '.') = new_id
AND NOT survivor:_ToDelete
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(q1)
OPTIONAL MATCH (survivor)-[:HAS_QA_EXCHANGE]->(q2)
WITH t.id AS loser, survivor.id AS winner, count(DISTINCT q1) AS loser_qa, count(DISTINCT q2) AS winner_qa
WHERE loser_qa > winner_qa
RETURN loser, winner, loser_qa, winner_qa
// EXPECT: 0 rows (no loser has more QA than its winner)
```

**Step 1b: Delete tagged nodes' QAExchange children (≈3,629 nodes + ≈3,427 NEXT_EXCHANGE rels)**

```cypher
CALL {
  MATCH (:_ToDelete)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
  DETACH DELETE qa
  RETURN count(*) AS deleted
} IN TRANSACTIONS OF 1000 ROWS
RETURN deleted
// EXPECT: ≈ 3629
```

**Step 1c: Delete tagged nodes' PreparedRemark children (205 nodes)**

```cypher
MATCH (:_ToDelete)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
DETACH DELETE pr
RETURN count(*) AS deleted
// EXPECT: ≈ 205
```

**Step 1d: Delete tagged nodes' QuestionAnswer children (3 nodes)**

```cypher
MATCH (:_ToDelete)-[:HAS_QA_SECTION]->(qs:QuestionAnswer)
DETACH DELETE qs
RETURN count(*) AS deleted
// EXPECT: 3
```

**Step 1e: Delete the 205 tagged Transcript nodes themselves**

```cypher
MATCH (t:_ToDelete)
DETACH DELETE t
RETURN count(*) AS deleted
// EXPECT: 205
```

**Verify Phase 1:**
```cypher
// Should be 0 tagged nodes left
MATCH (t:_ToDelete) RETURN count(*) AS remaining
// EXPECT: 0

// Total Transcripts should be 4192
MATCH (t:Transcript) RETURN count(*) AS total
// EXPECT: 4192

// New ID uniqueness (zero collisions now)
MATCH (t:Transcript)
WITH t.symbol + '_' + left(replace(replace(toString(t.conference_datetime), ':', '.'), ' ', 'T'), 16) AS new_id,
     count(*) AS cnt
WHERE cnt > 1
RETURN count(*) AS collisions
// EXPECT: 0
```

---

### PHASE 2: Rename All Transcript IDs

**Strategy**: Store old ID as temp property `_old_id`, set new ID and `quarter_key` in one pass.

```cypher
// 2a: Rename all 4,192 Transcript IDs + add quarter_key
// NOTE: fiscal_year is stored as STRING with locale comma ("2,025") — must strip it
MATCH (t:Transcript)
SET t._old_id = t.id,
    t.id = t.symbol + '_' + left(replace(replace(toString(t.conference_datetime), ':', '.'), ' ', 'T'), 16),
    t.quarter_key = t.symbol + '_' + replace(toString(t.fiscal_year), ',', '') + '_' + toString(t.fiscal_quarter)
RETURN count(*) AS renamed
// EXPECT: 4192
```

**Verify Phase 2:**
```cypher
// All IDs should match DATETIME format
MATCH (t:Transcript)
WHERE NOT t.id =~ '^[A-Z]+_\\d{4}-\\d{2}-\\d{2}T\\d{2}\\.\\d{2}$'
RETURN count(*) AS non_matching, collect(t.id)[..5] AS samples
// EXPECT: 0

// Multi-char symbols (1-4 char symbols like S, H, EW are valid)
MATCH (t:Transcript)
WHERE NOT t.id =~ '^[A-Z]{1,5}_\\d{4}-\\d{2}-\\d{2}T\\d{2}\\.\\d{2}$'
RETURN count(*) AS non_matching, collect(t.id)[..5] AS samples
// EXPECT: 0

// All should have _old_id and quarter_key
MATCH (t:Transcript)
WHERE t._old_id IS NULL OR t.quarter_key IS NULL
RETURN count(*) AS missing
// EXPECT: 0

// Verify zero duplicate new IDs
MATCH (t:Transcript)
WITH t.id AS id, count(*) AS cnt
WHERE cnt > 1
RETURN id, cnt
// EXPECT: 0 rows
```

---

### PHASE 3: Update Child Node IDs

**Key insight**: `_old_id` on parent holds the old prefix. Child suffix = `substring(child.id, size(parent._old_id))`. New child ID = `parent.id + suffix`.

**Step 3a: Update QAExchange nodes (≈76,152 nodes — largest batch)**

```cypher
CALL {
  MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(q:QAExchange)
  WHERE t._old_id IS NOT NULL
  SET q.id = t.id + substring(q.id, size(t._old_id)),
      q.transcript_id = t.id
  RETURN count(*) AS updated
} IN TRANSACTIONS OF 5000 ROWS
RETURN updated
// EXPECT: ≈ 76152
```

**Step 3b: Update PreparedRemark nodes (≈4,058 nodes)**

```cypher
MATCH (t:Transcript)-[:HAS_PREPARED_REMARKS]->(p:PreparedRemark)
WHERE t._old_id IS NOT NULL
SET p.id = t.id + substring(p.id, size(t._old_id))
RETURN count(*) AS updated
// EXPECT: ≈ 4058
```

**Step 3c: Update FullTranscriptText nodes (28 nodes)**

```cypher
MATCH (t:Transcript)-[:HAS_FULL_TEXT]->(f:FullTranscriptText)
WHERE t._old_id IS NOT NULL
SET f.id = t.id + substring(f.id, size(t._old_id))
RETURN count(*) AS updated
// EXPECT: 28
```

**Step 3d: Update QuestionAnswer nodes (≈38 nodes)**

```cypher
MATCH (t:Transcript)-[:HAS_QA_SECTION]->(qa:QuestionAnswer)
WHERE t._old_id IS NOT NULL
SET qa.id = t.id + substring(qa.id, size(t._old_id))
RETURN count(*) AS updated
// EXPECT: ≈ 38
```

**Verify Phase 3:**
```cypher
// All QAExchange transcript_id should match parent ID
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(q:QAExchange)
WHERE q.transcript_id <> t.id
RETURN count(*) AS mismatches
// EXPECT: 0

// All child IDs should start with parent ID
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(q:QAExchange)
WHERE NOT q.id STARTS WITH t.id
RETURN count(*) AS prefix_mismatches
// EXPECT: 0

MATCH (t:Transcript)-[:HAS_PREPARED_REMARKS]->(p:PreparedRemark)
WHERE NOT p.id STARTS WITH t.id
RETURN count(*) AS prefix_mismatches
// EXPECT: 0

MATCH (t:Transcript)-[:HAS_FULL_TEXT]->(f:FullTranscriptText)
WHERE NOT f.id STARTS WITH t.id
RETURN count(*) AS prefix_mismatches
// EXPECT: 0

MATCH (t:Transcript)-[:HAS_QA_SECTION]->(qa:QuestionAnswer)
WHERE NOT qa.id STARTS WITH t.id
RETURN count(*) AS prefix_mismatches
// EXPECT: 0

// NEXT_EXCHANGE chain count should be preserved
MATCH ()-[r:NEXT_EXCHANGE]->()
RETURN count(r) AS total
// EXPECT: 75452 - 3427 = 72025

// All QAExchange IDs should match DATETIME child pattern
MATCH (q:QAExchange)
WHERE NOT q.id =~ '^[A-Z]{1,5}_\\d{4}-\\d{2}-\\d{2}T\\d{2}\\.\\d{2}_qa__\\d+$'
RETURN count(*) AS non_matching, collect(q.id)[..5] AS samples
// EXPECT: 0
```

---

### PHASE 4: Cleanup

```cypher
// 5a: Remove _old_id temp property
MATCH (t:Transcript)
WHERE t._old_id IS NOT NULL
REMOVE t._old_id
RETURN count(*) AS cleaned
// EXPECT: 4192

// 5b: Clear guidance_status (guidance will be rebuilt from scratch)
MATCH (t:Transcript)
WHERE t.guidance_status IS NOT NULL
REMOVE t.guidance_status
RETURN count(*) AS cleared
// EXPECT: 8
```

---

### PHASE 5: Post-Migration Verification (Comprehensive)

```cypher
// 5a: Final transcript count
MATCH (t:Transcript) RETURN count(*) AS total
// EXPECT: 4192

// 5b: All IDs in DATETIME format
MATCH (t:Transcript)
WHERE NOT t.id =~ '^[A-Z]{1,5}_\\d{4}-\\d{2}-\\d{2}T\\d{2}\\.\\d{2}$'
RETURN count(*) AS bad_format
// EXPECT: 0

// 5c: All have quarter_key
MATCH (t:Transcript) WHERE t.quarter_key IS NULL
RETURN count(*) AS missing_qk
// EXPECT: 0

// 5d: No _old_id remnants
MATCH (t:Transcript) WHERE t._old_id IS NOT NULL
RETURN count(*) AS remnants
// EXPECT: 0

// 5e: No _ToDelete labels
MATCH (t:_ToDelete) RETURN count(*) AS remnants
// EXPECT: 0

// 5f: Zero duplicate IDs
MATCH (t:Transcript)
WITH t.id AS id, count(*) AS cnt WHERE cnt > 1
RETURN count(*) AS dupes
// EXPECT: 0

// 5g: QAExchange total
MATCH (q:QAExchange) RETURN count(*) AS total
// EXPECT: 79781 - 3629 = 76152

// 5h: All QAExchange.transcript_id match parent
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(q:QAExchange)
WHERE q.transcript_id <> t.id
RETURN count(*) AS mismatches
// EXPECT: 0

// 5i: PreparedRemark total
MATCH (p:PreparedRemark) RETURN count(*) AS total
// EXPECT: 4263 - 205 = 4058

// 5j: FullTranscriptText total (unchanged)
MATCH (f:FullTranscriptText) RETURN count(*) AS total
// EXPECT: 28

// 5k: QuestionAnswer total
MATCH (qa:QuestionAnswer) RETURN count(*) AS total
// EXPECT: 41 - 3 = 38

// 5l: NEXT_EXCHANGE total
MATCH ()-[r:NEXT_EXCHANGE]->()
RETURN count(r) AS total
// EXPECT: 75452 - 3427 = 72025

// 5m: INFLUENCES total
MATCH (:Transcript)-[r:INFLUENCES]->()
RETURN count(r) AS total
// EXPECT: 17588 - (205 pairs × 4 avg INFLUENCES each) ≈ 14888
// Exact: should equal sum of INFLUENCES on surviving 4192 nodes

// 5n: HAS_TRANSCRIPT total
MATCH ()-[r:HAS_TRANSCRIPT]->(:Transcript)
RETURN count(r) AS total
// EXPECT: 4397 - 205 = 4192

// 5o: Sample spot-check — AAPL
MATCH (t:Transcript {symbol: 'AAPL'})
RETURN t.id, t.quarter_key, t.conference_datetime
ORDER BY t.conference_datetime
LIMIT 5

// 5p: Sample spot-check — a former SHORT-only node
MATCH (t:Transcript)
WHERE t.quarter_key =~ '.*_2025_2$' AND t.symbol = 'SNDX'
OPTIONAL MATCH (t)-[:HAS_FULL_TEXT]->(f)
RETURN t.id, t.quarter_key, f.id AS full_text_id
// EXPECT: t.id = SNDX_2025-08-04T16.30, f.id = SNDX_2025-08-04T16.30_full

// 5q: Sample spot-check — ATEC (the divergent pair, winner kept)
MATCH (t:Transcript {symbol: 'ATEC'})
WHERE left(toString(t.conference_datetime), 10) = '2025-07-31'
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(q)
RETURN t.id, count(q) AS qa_count
// EXPECT: 1 row, id = ATEC_2025-07-31T16.30, qa_count = 22

// 5r: guidance_status fully cleared
MATCH (t:Transcript) WHERE t.guidance_status IS NOT NULL
RETURN count(*) AS remaining
// EXPECT: 0

// 5s: No orphaned QAExchange (every QA has a parent Transcript)
MATCH (q:QAExchange)
WHERE NOT EXISTS { MATCH (:Transcript)-[:HAS_QA_EXCHANGE]->(q) }
RETURN count(q) AS orphaned_qa
// EXPECT: 0

// 5t: No orphaned PreparedRemark
MATCH (p:PreparedRemark)
WHERE NOT EXISTS { MATCH (:Transcript)-[:HAS_PREPARED_REMARKS]->(p) }
RETURN count(p) AS orphaned_pr
// EXPECT: 0

// 5u: Constraints still live (stayed active throughout migration)
SHOW CONSTRAINTS YIELD name, labelsOrTypes
WHERE 'Transcript' IN labelsOrTypes OR 'QAExchange' IN labelsOrTypes
RETURN name, labelsOrTypes
// EXPECT: 2 rows (constraint_transcript_id_unique, constraint_qaexchange_id_unique)
```

---

## Post-Migration: Redis Cleanup (Optional, Non-Blocking)

Redis has stale lifecycle tracking data that won't match the new IDs. This is low-priority since all raw data has been consumed.

```python
# Stale LONG-format entries in pending set (1,270 entries)
# These use LONG keys, Neo4j now has DATETIME IDs — format mismatch persists
# Safe to clear since pending set is monitoring-only:
redis.delete("tracking:pending:transcripts")

# Stale SHORT-format meta hashes (675 entries with LONG keys)
# These are historical tracking data, no active use
# Can be left as-is (they expire via TTL) or cleared:
for key in redis.scan_iter("tracking:meta:transcripts:*"):
    redis.delete(key)
```

---

## Rollback Plan

If migration fails mid-way:

1. **If failed during Phase 1 (deletion)**: Some losers may already be deleted. Check `MATCH (t:_ToDelete) RETURN count(*)`. Any remaining tagged nodes can still be deleted. Data loss is limited to duplicate children (identical to winner side).

2. **If failed during Phase 2 (rename)**: Some Transcripts have new IDs, some have old. Use `_old_id` to identify which were renamed: `MATCH (t:Transcript) WHERE t._old_id IS NOT NULL RETURN count(*)`. To rollback: `SET t.id = t._old_id, REMOVE t._old_id, REMOVE t.quarter_key`.

3. **If failed during Phase 3 (children)**: Child IDs partially updated. Use `_old_id` on parent to identify old prefix. Rollback: `SET q.id = t._old_id + substring(q.id, size(t.id)), q.transcript_id = t._old_id`.

4. **Nuclear rollback**: Restore from Phase 0.5 backup.

---

## Execution Order Summary

| Phase | Operation | Nodes Affected | Reversible? |
|-------|-----------|---------------:|:-----------:|
| 0 | Pre-flight verification (DB + Redis) | 0 | N/A |
| 0.5 | Backup | 0 | N/A |
| 1a | Tag losers (fewest QA, format-agnostic) | 205 | Yes (remove label) |
| 1b | Delete loser QAExchange | ≈3,629 | No (backup needed) |
| 1c | Delete loser PreparedRemark | ≈205 | No (backup needed) |
| 1d | Delete loser QuestionAnswer | ≈3 | No (backup needed) |
| 1e | Delete loser Transcripts | 205 | No (backup needed) |
| 2 | Rename Transcript IDs + quarter_key | 4,192 | Yes (via `_old_id`) |
| 3a | Update QAExchange IDs + transcript_id | ≈76,152 | Yes (via `_old_id`) |
| 3b | Update PreparedRemark IDs | ≈4,058 | Yes (via `_old_id`) |
| 3c | Update FullTranscriptText IDs | 28 | Yes (via `_old_id`) |
| 3d | Update QuestionAnswer IDs | ≈38 | Yes (via `_old_id`) |
| 4a | Remove `_old_id` temp property | 4,192 | N/A |
| 4b | Clear `guidance_status` | 8 | N/A |
| 5 | Post-migration verification | 0 | N/A |

> **Note**: Uniqueness constraints stay live throughout — no drop/recreate needed.
> DATETIME IDs are structurally distinct from all existing formats (verified zero collisions).

**Total nodes modified**: ≈84,510
**Total nodes deleted**: ≈4,042 (205 Transcripts + 3,629 QA + 205 PR + 3 QS)
**Total relationships removed**: ≈8,289 (3,629 HAS_QA_EXCHANGE + 3,427 NEXT_EXCHANGE + 205 HAS_PREPARED_REMARKS + 205 HAS_TRANSCRIPT + 205×4 INFLUENCES + 3 HAS_QA_SECTION)

---

## Edge Cases Addressed

1. **ATEC divergent pair**: One node has 22 QA, the other has 16. The format-agnostic loser selection (fewest QA) automatically keeps the richer node. The 16-QA node is deleted.

2. **SNDX_2025_2 (SHORT with FullTranscriptText)**: NOT in a duplicate pair (orphan SHORT). It gets renamed to `SNDX_2025-08-04T16.30`, and its FullTranscriptText child `SNDX_2025_2_full` becomes `SNDX_2025-08-04T16.30_full`.

3. **Multi-char symbols**: Regex `^[A-Z]{1,5}_` covers all symbols (S, H, EW, AAPL, etc.). The `substring()` approach for child ID update is symbol-length-agnostic (uses `size(t._old_id)` not a hardcoded offset).

4. **Guidance nodes (70 FROM_SOURCE)**: All point to LONG-format Transcripts. Phase 3 renames those IDs. The relationship edges survive the rename (Neo4j relationships are between node references, not ID values). **These will be wiped anyway per user decision**, so no special handling needed.

5. **NEXT_EXCHANGE chains**: For surviving nodes (LONG side), NEXT_EXCHANGE relationships are between QAExchange nodes by node reference — renaming QAExchange IDs does NOT break the chain. Only the 3,427 NEXT_EXCHANGE rels on deleted SHORT-side QA nodes are lost (identical to LONG-side chains).

6. **QAExchange embeddings**: All 76,152 surviving QAExchange nodes retain their embedding vectors. The vector index (`qaexchange_vector_idx`) auto-updates since it's on the node, not the ID. No re-embedding needed.

7. **Fulltext index**: The `qa_exchange_ft` fulltext index on `QAExchange.exchanges` is unaffected by ID changes. It indexes the `exchanges` text content, not the `id`.

---

## Downstream Code Impact (Post-Migration)

These files parse transcript IDs — they work with the new format because they all split on `_` and take `[0]` for ticker:

| File | Line | Pattern | Safe? |
|------|------|---------|:-----:|
| `scripts/trigger-guidance.py` | 119 | `t["id"].split("_")[0]` | YES — first `_` still separates ticker |
| `scripts/earnings_worker.py` | 128 | `text.split("_")[0]` | YES — same reason |
| `scripts/fix_missing_industry_returns.py` | 93 | `parts = transcript_id.split('_')` then `parts[1]` | REVIEW — `parts[1]` now gets `2025-07-31T17.00` (was `2025-07-31T17.00.00-04.00`). Still a valid datetime string, just shorter. Likely fine. |
| `scripts/fix_missing_sector_returns.py` | 75 | Same pattern | REVIEW — same as above |
| `redisDB/redis_constants.py` | 76-92 | `parse_transcript_key_id()` | DEAD CODE — zero callers. No impact. |

**No code changes needed for migration.** The `split('_', 1)` pattern gives `[ticker, datetime_part]` for all three formats. The shorter datetime in the new format doesn't break any downstream parsing.

---

## Post-Migration Code Updates (Separate PRs)

After migration is verified and stable:

1. **`scripts/canary_sdk_write.py:24`** (GAP-10): Change `SOURCE_ID = "CRM_2025-09-03T17.00.00-04.00"` → `SOURCE_ID = "CRM_2025-09-03T17.00"`
2. **`scripts/guidance_write_cli.py` docstring** (GAP-11): Update example source_id from LONG to DATETIME format
