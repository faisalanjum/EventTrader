# Ghost News Nodes from SEC Filings

**Created**: 2026-03-31
**Updated**: 2026-04-02
**Status**: OPEN — root cause proven, fix designed (4 lines in 3 files), not yet applied

**Discovered during**: Section 6 (Inter-Quarter Events) renderer testing (originally as part of CCL price gap investigation)
**Prior doc**: `archive/ccl-price-gap-and-ghost-news.md` (price gap portion: RESOLVED)

---

## Scope

| Metric | Value |
|--------|-------|
| Ghost News nodes | **6,693** |
| Date range | **2025-08-25 to 2026-03-27** (ongoing) |
| Have INFLUENCES rels? | **Yes — with real return data** (e.g., FMC -46.52%) |
| Titles | Empty string `''` (not NULL) |
| ID pattern | `bzNews_{SEC_accession}` e.g., `bzNews_0001104659-25-123226` |
| Monthly rate | ~700-1,700 new ghosts/month |

Monthly distribution:
```
2025-08:   34  |  2025-09:  462  |  2025-10: 1,144  |  2025-11: 1,277
2025-12:  685  |  2026-01:  673  |  2026-02: 1,680  |  2026-03:   738
```

**Impact on predictor**: Ghost News nodes have INFLUENCES relationships with real return data (extracted from the report payload). The predictor sees these as separate "news events" with significant returns — e.g., an FMC SEC filing appears as a ghost news event with -46.52% daily return. This actively pollutes the prediction signal, not just cosmetic noise.

---

## Root cause (proven, verified against live code 2026-04-02)

The news reconciliation code uses `self.event_trader_redis.source` (which is `'reports'` when news source is disabled) instead of hardcoding `RedisKeys.SOURCE_NEWS`. This causes it to scan report keys and create ghost News nodes from SEC filings.

**The active bug path** (`reconcile.py:37-112`):
```
reconcile.py:39  — scan pattern: reports:withreturns:* (should be news:*)
  |
reconcile.py:50  — manufacture: bzNews_{SEC_accession_number}
  |
reconcile.py:61  — check Neo4j: News node doesn't exist -> process it
  |
reconcile.py:73  — guard check: tracking:meta:news:... -> not found (metadata was
                   written to tracking:meta:reports:... by Bug #3) -> guard fails
  |
reconcile.py:95  — read data: reports:withreturns:{id} (should be news:*)
  |
reconcile.py:100 — call _process_deduplicated_news(bzNews_{accession}, report_json)
  |
news.py:172      — _create_news_node_from_data: title='' (report has no title field)
  |
news.py:182      — _prepare_entity_relationship_params: extracts symbols + returns from report
  |
news.py:257      — MERGE News node + INFLUENCES relationships with real return data
  |
news.py:241      — write metadata to tracking:meta:reports:... (Bug #3 -- wrong namespace)
```

**Four namespace coupling bugs:**

1. **`reconcile.py:39`** — scan pattern uses `self.event_trader_redis.source` ('reports') instead of `RedisKeys.SOURCE_NEWS`. Scans `reports:withreturns:*` instead of `news:withreturns:*`. **This is the active bug creating ghosts.**

2. **`reconcile.py:95`** — data read key uses `self.event_trader_redis.source` ('reports'). Reads report payloads and feeds them to `_process_deduplicated_news()`. **Must be fixed together with line 39.**

3. **`news.py:241`** — metadata write uses `self.event_trader_redis.source` ('reports'). Writes to `tracking:meta:reports:...` instead of `tracking:meta:news:...`. **Breaks the dedup guard** at `reconcile.py:73` which checks `tracking:meta:news:...`.

4. **`pubsub.py:254`** — news subscription uses `self.event_trader_redis.source` ('reports'). Subscribes to `reports:*` channels instead of `news:*`. **Dormant bug**: the handler routing at `pubsub.py:305` uses hardcoded `RedisKeys.SOURCE_NEWS` prefix check, so messages are correctly routed to report processing. Real impact: if news source is re-enabled, real-time news PubSub won't work.

**Verified NOT creating ghosts:**
- `pubsub.py:305-310` — handler routing is hardcoded to `SOURCE_NEWS`/`SOURCE_REPORTS`, correctly routes regardless of subscription bug
- `news.py:42` — `process_news_to_neo4j()` hardcodes `"news:withreturns:*"`, only processes actual news keys
- Report reconciliation (section 2, line 114+) — separate code, uses its own hardcoded `SOURCE_REPORTS`

---

## Fix (4 lines in 3 files + cleanup)

| File | Line | Old | New |
|------|------|-----|-----|
| `reconcile.py` | 39 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `reconcile.py` | 95 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `news.py` | 241 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `pubsub.py` | 254 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |

**Cleanup** (run after code fix, one-time):
```cypher
-- Delete 6,693 ghost News nodes + their INFLUENCES relationships
-- Pattern matches SEC accession format (10-2-6 digits), never matches Benzinga numeric IDs
MATCH (n:News)
WHERE n.title = '' AND n.id =~ 'bzNews_\\d{10}-\\d{2}-\\d{6}'
DETACH DELETE n
RETURN count(n) AS deleted
```

---

## Regression risk: zero

- `reconcile.py:39,95` — scans `news:*` keys. News source disabled, finds nothing, no ghost creation. When re-enabled, correctly processes news.
- `news.py:241` — metadata in correct namespace, dedup guard at line 73 works correctly.
- `pubsub.py:254` — subscribes to `news:*` channels. News disabled, no messages. Correct when re-enabled.
- Cleanup regex `\d{10}-\d{2}-\d{6}` only matches SEC accession IDs, never legitimate 8-digit Benzinga news IDs.
- Report reconciliation (section 2) untouched.
- No Report nodes are deleted or modified.

---

## Validation queries

```cypher
-- Verify zero ghost news remain (should return 0 after cleanup)
MATCH (n:News)
WHERE n.title = '' AND n.id =~ 'bzNews_\\d{10}-\\d{2}-\\d{6}'
RETURN count(n) AS ghost_count

-- Verify legitimate news unaffected
MATCH (n:News)
WHERE n.title <> '' AND n.title IS NOT NULL
RETURN count(n) AS legitimate_news_count

-- Verify no new ghosts created after fix (run after next reconciliation cycle)
MATCH (n:News)
WHERE n.title = ''
RETURN count(n) AS new_ghosts
```

---

## Priority

**Medium-High**. 6,693 ghost News nodes with real INFLUENCES return data actively pollute the prediction signal. Fix is 4 lines + one-time cleanup.
