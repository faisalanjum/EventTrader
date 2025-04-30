# 🔗 Function-to-Redis-Action Mapping Table

This table lists every function responsible for **populating**, **moving**, or **deleting** Redis keys and queues across the ingestion system. It is organized by data source and follows the Live and Historical flows.

---

## 🗞️ Benzinga News (Live & Historical)

| Function | Redis Action | Redis Keys / Patterns | File | Flow |
|---------|---------------|------------------------|------|------|
| `RedisClient.set_news()` | `SET`, `LPUSH` | `news:benzinga:live:raw:{id}.{updated}`, `news:benzinga:queues:raw` | `redisDB/redisClasses.py` (called from `bz_websocket.py`) | Live |
| `RedisClient.set_news_batch()` | `SET`, `LPUSH` | `news:hist:raw:{id}.{updated}`, `news:queues:raw` | `redisDB/redisClasses.py` (called from `bz_restAPI.py`) | Historical |
| `BaseProcessor.process_all_items()` | `GET`, `SET`, `LPUSH`, `PUBLISH`, `DEL` | `news:queues:raw` → `news:benzinga:{live\|hist}:processed:{id}.{updated}`, `news:benzinga:queues:processed`, `news:benzinga:live:processed` | `redisDB/BaseProcessor.py` (inherited by `NewsProcessor.py`) | Both |
| `EventReturnsManager.process_event_metadata()` | Adds metadata | `metadata.event`, `metadata.returns_schedule`, `metadata.instruments` | `eventReturns/EventReturnsManager.py` | Both |
| `ReturnsProcessor._process_returns()` | `SET`, `ZADD`, `DEL` | `news:withreturns:{id}`, `news:withoutreturns:{id}`, `news:pending_returns` | `eventReturns/ReturnsProcessor.py` | Both |
| `ReturnsProcessor._process_pending_returns()` | `ZRANGE`, `GET`, `SET`, `ZREM` | `news:pending_returns`, `news:withoutreturns:{id}` → `news:withreturns:{id}` | `eventReturns/ReturnsProcessor.py` | Both |

---

## 📈 SEC Reports (Live & Historical)

| Function | Redis Action | Redis Keys / Patterns | File | Flow |
|---------|---------------|------------------------|------|------|
| `RedisClient.set_filing()` | `SET`, `LPUSH` | `reports:live:raw:{accessionNo}.{filedAt}`, `reports:queues:raw` | `redisDB/redisClasses.py` (called from `sec_websocket.py`) | Live |
| `RedisClient.set_filing()` | `SET`, `LPUSH`, `SET` | `reports:hist:raw:{accessionNo}.{filedAt}`, `reports:queues:raw`, `batch:reports:{from}-{to}:fetch_complete` | `redisDB/redisClasses.py` (called from `sec_restAPI.py`) | Historical |
| `BaseProcessor.process_all_items()` | `GET`, `SET`, `LPUSH`, `PUBLISH`, `DEL` | `reports:queues:raw` → `reports:{live\|hist}:processed:{accessionNo}.{filedAt}`, `reports:queues:processed`, `reports:live:processed` | `redisDB/BaseProcessor.py` (inherited by `ReportProcessor.py`) | Both |
| `EventReturnsManager.process_event_metadata()` | Adds metadata | `metadata.event`, `metadata.returns_schedule`, `metadata.instruments` | `eventReturns/EventReturnsManager.py` | Both |
| `ReturnsProcessor._process_returns()` | `SET`, `ZADD`, `DEL` | `reports:withreturns:{id}`, `reports:withoutreturns:{id}`, `reports:pending_returns` | `eventReturns/ReturnsProcessor.py` | Both |
| `ReturnsProcessor._process_pending_returns()` | `ZRANGE`, `GET`, `SET`, `ZREM` | `reports:pending_returns`, `reports:withoutreturns:{id}` → `reports:withreturns:{id}` | `eventReturns/ReturnsProcessor.py` | Both |

---

## 🗣️ Transcripts (Live & Historical)

| Function | Redis Action | Redis Keys / Patterns | File | Flow |
|---------|---------------|------------------------|------|------|
| `EarningsCallProcessor.store_transcript_in_redis()` | `SET`, `LPUSH` | `transcripts:{live\|hist}:raw:{symbol}_{timestamp}`, `transcripts:queues:raw` | `transcripts/EarningsCallTranscripts.py` | Both |
| `TranscriptProcessor._process_scheduled_items()` → `_handle_transcript_found()` / `_schedule_transcript_retry()` | `ZREM`, `SADD`, `DEL`, `PUBLISH` | `admin:transcripts:schedule`, `admin:transcripts:processed`, `admin:transcripts:notifications` | `redisDB/TranscriptProcessor.py` | Both |
| `BaseProcessor.process_all_items()` | `GET`, `SET`, `LPUSH`, `DEL` | `transcripts:queues:raw` → `transcripts:{live\|hist}:processed:{symbol}_{timestamp}`, `transcripts:queues:processed` | `redisDB/BaseProcessor.py` (inherited by `TranscriptProcessor.py`) | Both |
| `TranscriptProcessor._handle_transcript_found()` | `DEL` | `transcripts:{live|hist}:raw:{symbol}_{timestamp}` | `redisDB/TranscriptProcessor.py` | Both |
| `EventReturnsManager.process_event_metadata()` | Adds metadata | `metadata.event`, `metadata.returns_schedule`, `metadata.instruments` | `eventReturns/EventReturnsManager.py` | Both |
| `ReturnsProcessor._process_returns()` | `SET` | `transcripts:withreturns:{id}`, `transcripts:withoutreturns:{id}` | `eventReturns/ReturnsProcessor.py` | Both |

---

## 🔄 Cross-Cutting Functions

| Function | Redis Action | Redis Keys / Patterns | File | Purpose |
|---------|---------------|------------------------|------|---------|
| `reconcile_missing_items()` | `SCAN`, `GET`, `DEL`, `LPUSH` | `{source}:withreturns:*` | `neograph/mixins/reconcile.py` | Verifies Neo4j ingestion, deletes or requeues |
| `Neo4jProcessor._handle_ingestion_success()` | `DEL` | `{source}:withreturns:{id}` | `neograph/mixins/pubsub.py` | Deletes item once Neo4j confirms write |
| `StatsTracker.increment()` | `INCR`, `EXPIRE` | `admin:operations:{type}:{id}` | `utils/stats_tracker.py` | Tracks fetch/process metrics |
| `RedisClient.get_symbols()` | `SMEMBERS` | `admin:tradable_universe:symbols` | `redisDB/redisClasses.py` | Gets set of valid symbols for filtering |
| `RedisClient.get_stock_universe()` | `GET` | `admin:tradable_universe:stock_universe` | `redisDB/redisClasses.py` | Gets DataFrame of universe metadata |
| `RedisClient.set_json()` | `SET` | `admin:*` various admin keys | `redisDB/redisClasses.py` | Stores JSON data for admin purposes |
| `RedisClient.batch_delete_keys()` | `DEL` (multiple) | Various patterns | `redisDB/redisClasses.py` | Batch deletion for cleanup |

---

## 📊 Admin & Monitoring Functions

| Function | Redis Action | Redis Keys / Patterns | File | Purpose |
|---------|---------------|------------------------|------|---------|
| `_log_downtime()` | `SET` | `admin:websocket_downtime:{source}:{timestamp}` | `benzinga/bz_websocket.py`, `secReports/sec_websocket.py` | Tracks WebSocket connection issues |
| `disconnect()` | `SET` | `admin:{news\|reports}:shutdown_state` | `benzinga/bz_websocket.py`, `secReports/sec_websocket.py` | Saves state before clean shutdown |
| `connect()` | `GET`, `SET` | `admin:backfill:{news\|reports}_restart_gap` | `benzinga/bz_websocket.py`, `secReports/sec_websocket.py` | Detects restarts and logs gaps |
| `_on_message()` | `SET` | `admin:{news\|reports}:last_message_time` | `benzinga/bz_websocket.py`, `secReports/sec_websocket.py` | Tracks last received message |
| `EventTraderRedis.initialize_stock_universe()` | `SET`, `SADD` | `admin:tradable_universe:stock_universe`, `admin:tradable_universe:symbols` | `redisDB/redisClasses.py` | Initializes tradable universe |
| `RedisClient.clear()` | `DEL`, `SCAN` | Various patterns based on prefix | `redisDB/redisClasses.py` | Clears Redis data with preservation options |

---
