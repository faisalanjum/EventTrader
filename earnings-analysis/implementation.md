# Real-Time Prediction: Implementation Overview

## Current Flow

```
event-trader → Redis queues → xbrl-workers → report-enricher → Neo4j
```

## New Flow (Prediction)

```
1. event-trader detects 8-K Item 2.02
                 ↓
2. Enqueue to Redis: reports:queues:predict
                 ↓
3. prediction-worker (NEW)
   - Load learnings.md for company
   - Query Neo4j (point-in-time only)
   - Query Perplexity for consensus
   - Make prediction → Log to CSV/Neo4j
                 ↓
4. Wait 24 hours (returns not yet available)
                 ↓
5. reassessment-worker (NEW) or CronJob
   - Returns now in Neo4j
   - Compare prediction vs actual
   - Generate final report
   - Update learnings.md
   - Log accuracy
```

---

## Components Needed

| Component | Type | Purpose |
|-----------|------|---------|
| **Redis queue** | `reports:queues:predict` | Queue 8-K filings for prediction |
| **prediction-worker** | New Deployment | Makes predictions using Claude API |
| **reassessment-queue** | `reports:queues:reassess` | Queue filings ready for reassessment (24hr old) |
| **reassessment-worker** | New Deployment or CronJob | Compares predictions to actuals |
| **Prediction storage** | Neo4j node or CSV | Store predictions before outcome |
| **Point-in-time validator** | Python module | Enforce no future data leakage |

---

## Simplified Steps

1. **New Redis queue**: `reports:queues:predict`
2. **Modify event-trader**: Enqueue 8-K Item 2.02 to prediction queue
3. **New prediction-worker pod**: Calls Claude API, makes prediction, stores it
4. **Scheduled reassessment**: CronJob or separate queue that picks up 24hr-old predictions
5. **Storage**: Predictions in Neo4j (new node type) or filesystem

---

## Key Decision Points

| Decision | Options |
|----------|---------|
| **Claude API call** | Direct API vs MCP server vs local model |
| **Prediction storage** | Neo4j `(:Prediction)` node vs CSV on shared volume |
| **Reassessment trigger** | CronJob (scan for 24hr-old) vs delayed Redis message |
| **Learnings storage** | Filesystem (current) vs Neo4j |
