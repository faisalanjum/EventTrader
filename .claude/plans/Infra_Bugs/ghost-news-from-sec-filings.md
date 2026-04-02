# Ghost News Nodes from SEC Filings

**Created**: 2026-03-31
**Updated**: 2026-04-02
**Status**: RESOLVED — code fix applied, Neo4j + Redis cleanup complete, verified clean

**Discovered during**: Section 6 (Inter-Quarter Events) renderer testing (originally as part of CCL price gap investigation)
**Prior doc**: `archive/ccl-price-gap-and-ghost-news.md` (price gap portion: RESOLVED)

---

## Resolution Summary (2026-04-02)

**Code fix**: 5 lines in 3 files — replaced `self.event_trader_redis.source` with `RedisKeys.SOURCE_NEWS` in all news-specific code paths.

**Cleanup performed**:

| Target | Deleted | Verified remaining |
|--------|---------|-------------------|
| Ghost News nodes (Neo4j) | 6,694 | **0** |
| Ghost INFLUENCES relationships (Neo4j) | 26,840 | **0** |
| Wrong numeric `tracking:meta:reports:*` entries (Redis) | 1,333 | **0** |
| Stale `tracking:pending:news` members (Redis) | 1,333 | **0** of the bug-related ones |

**Unaffected**:

| Target | Count | Status |
|--------|-------|--------|
| Legitimate News nodes (Neo4j) | 344,532 | Untouched |
| Report nodes (Neo4j) | 38,834 | Untouched |
| Legitimate accession `tracking:meta:reports:*` (Redis) | 8,729 | Untouched |
| Remaining `tracking:pending:news` members (Redis) | 1,852 | Separate bug — see `pending-set-orphan-accumulation.md` |

---

## Scope (pre-fix state)

| Metric | Value |
|--------|-------|
| Ghost News nodes | **6,694** |
| Legitimate News nodes | **344,532** (unaffected) |
| Ghost percentage | **1.9%** of all News nodes |
| Date range | **2025-08-25 to 2026-03-27** |
| Have INFLUENCES rels? | **Yes — 26,840 total edges** |
| INFLUENCES targets | Company (6,758) + MarketIndex (6,694) + Sector (6,694) + Industry (6,694) |
| INFLUENCES distribution | 6,630 ghosts with 4 edges; 64 ghosts with 5 edges (2 Companies) |
| Titles | Empty string `''` (not NULL) |
| Content fields | body, teaser, url all empty `''` |
| Metadata fields | channels, tags, authors all empty JSON `"[]"` |
| Pipeline metadata | created, market_session, returns_schedule all populated |
| ID pattern | `bzNews_{SEC_accession}` e.g., `bzNews_0001104659-25-123226` |
| ID collision risk | **Zero** — SEC accession has hyphens; Benzinga IDs are pure digits |
| Monthly rate | ~700-1,700 new ghosts/month |
| Redis residue | 1,333 wrongly namespaced `tracking:meta:reports:{benzinga_id}` entries |
| Redis residue timing | All 1,333 stamped `inserted_into_neo4j_at: 2026-03-29` |

Monthly distribution (ghost `created` dates reflect original filing dates, not insertion time):
```
2025-08:   34  |  2025-09:  462  |  2025-10: 1,144  |  2025-11: 1,277
2025-12:  685  |  2026-01:  673  |  2026-02: 1,680  |  2026-03:   739
```

**Impact on predictor**: Ghost News nodes had INFLUENCES relationships with real return data (extracted from report payloads). The predictor saw these as separate "news events" with significant returns — e.g., an FMC SEC filing appeared as a ghost news event with -46.52% daily return. This actively polluted the prediction signal.

**Ghost-Report cross-reference confirmed**: Sampled ghosts share identical accession numbers and timestamps with real Report nodes (e.g., ghost `bzNews_0000002488-25-000147` ↔ Report `0000002488-25-000147`, both `created: 2025-08-25T16:07:00-04:00`, Report has description "Form 8-K - Current report - Item 5.02" while ghost title is empty).

---

## Root cause (proven, independently verified from first principles 2026-04-02)

### The architectural defect

The news processing code used `self.event_trader_redis.source` (a dynamic property) instead of the hardcoded constant `RedisKeys.SOURCE_NEWS`. At runtime, this property equalled `'reports'` because:

1. `config/DataManagerCentral.py` disables news backfill and only initializes `self.sources['reports']`
2. `initialize_neo4j()` iterates `self.sources` and picks the first available source's Redis client — which is the reports client
3. `Neo4jProcessor` stores this as `self.event_trader_redis`, inheriting `source == 'reports'`

This is a namespace coupling bug: code that should always operate on the `'news'` namespace instead deferred to whichever source happened to be initialized first.

**Note**: Sections 2 and 3 of reconcile.py (reports and transcripts) already hardcode their respective `SOURCE_REPORTS` and `SOURCE_TRANSCRIPTS` constants correctly. Only the news paths had this bug.

### The active bug path (reconcile.py Section 1, lines 37-112)

Ran every `PUBSUB_RECONCILIATION_INTERVAL` seconds:

```
reconcile.py:39  — scan pattern: reports:withreturns:* (should be news:*)
  |
reconcile.py:49  — manufacture: bzNews_{SEC_accession_number}
  |
reconcile.py:61  — check Neo4j: News node doesn't exist -> "missing"
  |
reconcile.py:73  — guard check: tracking:meta:news:... -> not found
                   (metadata was written to tracking:meta:reports:... by Bug #3)
                   -> guard fails, proceeds
  |
reconcile.py:95  — read data: reports:withreturns:{id} (should be news:*)
  |
reconcile.py:100 — call _process_deduplicated_news(bzNews_{accession}, report_json)
  |
news.py:377      — _create_news_node_from_data: title=news_data.get('title','')
                   report has no title field -> empty string
  |
news.py:344-347  — _create_influences_relationships: extracts symbols + returns
                   from report -> creates Company/Sector/Industry/MarketIndex edges
                   (succeeds because utility.py:15 _extract_symbols_from_data and
                   utility.py:178 _prepare_entity_relationship_params are designed
                   to accept both news and report payloads)
  |
news.py:241      — write metadata to tracking:meta:reports:... (Bug #3 — wrong namespace)
                   next cycle's guard at line 73 will fail again, but Neo4j node
                   now exists so line 66 dedup prevents duplicate creation
```

### Five namespace coupling bugs (all fixed)

| # | File | Line | What it did wrong | Status |
|---|------|------|--------------------|--------|
| 1 | `reconcile.py` | 39 | Scan pattern used `'reports'` → scanned `reports:withreturns:*` instead of `news:withreturns:*` | **FIXED** |
| 2 | `reconcile.py` | 95 | Data read used `'reports'` → read report payloads, fed to `_process_deduplicated_news()` | **FIXED** |
| 3 | `news.py` | 241 | Metadata write used `'reports'` → wrote to `tracking:meta:reports:...` instead of `tracking:meta:news:...` → broke dedup guard at reconcile.py:73 | **FIXED** |
| 4 | `pubsub.py` | 254 | News subscription used `'reports'` → subscribed to `reports:*` channels instead of `news:*` → duplicated report subscription | **FIXED** |
| 5 | `pubsub.py` | 49 | News data key used `'reports'` → read from `reports:{namespace}:{item_id}` instead of `news:{namespace}:{item_id}` | **FIXED** |

Bug #5 was not in the original 4-line analysis. It was unreachable because bug #4 prevented subscription to news channels. However, fixing #4 without fixing #5 would have caused real-time news processing to silently fail when news is re-enabled (data lookup miss → "No data found for news" warning).

### Verified NOT creating ghosts (unchanged code paths)

- `pubsub.py:305-310` — handler routing hardcodes `RedisKeys.SOURCE_NEWS`/`SOURCE_REPORTS` prefix checks → messages routed correctly regardless of subscription bug
- `news.py:42` — `process_news_to_neo4j()` hardcodes `"news:withreturns:*"` literal → only processes actual news keys
- `reconcile.py:114-206` — Section 2 (reports) hardcodes `RedisKeys.SOURCE_REPORTS` throughout → unaffected
- `reconcile.py:209-291` — Section 3 (transcripts) hardcodes `RedisKeys.SOURCE_TRANSCRIPTS` throughout → unaffected
- `pubsub.py:98-102` — report data key in PubSub handler hardcodes `RedisKeys.SOURCE_REPORTS` → correct
- `pubsub.py:148-152` — transcript data key in PubSub handler hardcodes `RedisKeys.SOURCE_TRANSCRIPTS` → correct
- `RedisClient.get()` (`redisClasses.py:320-322`) — does NOT add prefix; passes key as-is to `self.client.get(key)` → key construction at bug sites was the sole source of the namespace error

### Complete `self.event_trader_redis.source` usage inventory (post-fix)

```
neograph/mixins/pubsub.py:304     — COMMENTED OUT (already replaced by hardcoded SOURCE_NEWS at line 305)
```

No active usages remain. All 5 bug sites now use `RedisKeys.SOURCE_NEWS`.

---

## Fix applied (5 lines in 3 files)

| File | Line | Old | New |
|------|------|-----|-----|
| `reconcile.py` | 39 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `reconcile.py` | 95 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `news.py` | 241 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `pubsub.py` | 254 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |
| `pubsub.py` | 49 | `self.event_trader_redis.source` | `RedisKeys.SOURCE_NEWS` |

**Why hardcode**: This makes the news code paths consistent with the existing pattern. Sections 2 and 3 of reconcile.py already hardcode `SOURCE_REPORTS` and `SOURCE_TRANSCRIPTS`. The batch methods `process_reports_to_neo4j()` and `process_transcripts_to_neo4j()` do the same. The bug existed precisely because the news paths used a dynamic property while the others used constants.

---

## Cleanup performed (2026-04-02)

### A. Neo4j cleanup

```cypher
MATCH (n:News)
WHERE n.title = '' AND n.id =~ 'bzNews_\\d{10}-\\d{2}-\\d{6}'
DETACH DELETE n
-- Result: 6,694 nodes deleted, 26,840 relationships deleted
```

### B. Redis cleanup

1. **Deleted 1,333 wrongly namespaced `tracking:meta:reports:{benzinga_numeric_id}`** entries — distinguished from legitimate report meta by digits-only base ID (Benzinga) vs hyphenated accession (SEC). All 8,729 legitimate accession-style entries preserved.

2. **Removed 1,333 corresponding stale `tracking:pending:news` members** — these had `tracking:meta:news:{id}` format in the pending set but their actual metadata was written to `tracking:meta:reports:{id}` by bug #3, so they would never have been resolved.

### C. Post-cleanup verification (all passed)

| Check | Result |
|-------|--------|
| Ghost News nodes (empty title) | **0** |
| News with SEC accession IDs | **0** |
| Legitimate News nodes | **344,532** (unchanged) |
| Orphaned INFLUENCES relationships | **0** |
| Report nodes | **38,834** (untouched) |
| Wrong numeric `tracking:meta:reports:*` | **0** |
| Legitimate accession `tracking:meta:reports:*` | **8,729** (untouched) |
| Spot-check of deleted IDs (meta + pending) | **0 still present** |
| `news:withreturns:*` keys | **0** (no ghost fuel) |

---

## Regression risk: zero

**reconcile.py:39,95** (scan + read):
- After fix: scans `news:withreturns:*` / `news:withoutreturns:*`. News source disabled → zero keys found → loop body never executes → ghost creation stopped immediately. When news re-enabled → correctly processes news keys. Report reconciliation (Section 2, line 114+) is entirely separate code using hardcoded `SOURCE_REPORTS` → unaffected.

**news.py:241** (metadata write):
- After fix: writes to `tracking:meta:news:{id}`. Guard at `reconcile.py:73` checks `tracking:meta:news:{id}` (already hardcoded) → dedup now works. No code reads ghost metadata at `tracking:meta:reports:{bzNews_accession}` — report metadata uses different ID formats (raw accession, no `bzNews_` prefix). All three callers of `_process_deduplicated_news` (`news.py:105` batch, `pubsub.py:67` PubSub, `reconcile.py:100` reconcile) process news data → `SOURCE_NEWS` metadata is correct for all.

**pubsub.py:254** (subscription):
- After fix: subscribes to `news:withreturns` / `news:withoutreturns`. Report channels still subscribed at lines 261-264 (hardcoded) → unaffected. News disabled → no messages on news channels → no effect. Removes duplicate report channel subscription (harmless).

**pubsub.py:49** (data key):
- After fix: reads from `news:{namespace}:{item_id}`. Only reachable when `content_type == 'news'` (line 46), which requires a message on a `news:*` channel (line 305). News disabled → no news messages → unreachable. When news re-enabled → correctly reads news data.

---

## Remaining related work

- **1,852 stale `tracking:pending:news` members** unrelated to this bug — tracked in `pending-set-orphan-accumulation.md`
- **19 `reports:withreturns:*` keys** in Redis — handled by Section 2 report reconciliation (unrelated, working correctly)
