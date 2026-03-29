# XBRL Worker Temporary Scale-Up for Backfill

**Created**: 2026-03-29
**Purpose**: Drain XBRL backlog (heavy=61, medium=164) during SEC report backfill
**Revert when**: Backfill completes (~43 chunks done) AND XBRL queues < 5

---

## Original Config (REVERT TO THIS)

```bash
# Heavy workers — replicas + KEDA
kubectl scale deploy -n processing xbrl-worker-heavy --replicas=2
kubectl patch scaledobject -n processing xbrl-worker-heavy-scaler --type merge -p '{"spec":{"maxReplicaCount":2}}'

# Heavy workers — memory limit back to 7Gi (was 7Gi → 10Gi → 12Gi during backfill)
kubectl patch deploy -n processing xbrl-worker-heavy --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"7Gi"}]'

# Medium workers — replicas + KEDA
kubectl scale deploy -n processing xbrl-worker-medium --replicas=3
kubectl patch scaledobject -n processing xbrl-worker-medium-scaler --type merge -p '{"spec":{"maxReplicaCount":3}}'
```

### Original Values (PRE-BACKFILL)
| | Replicas | KEDA Max | CPU Req/Limit | Mem Req/Limit |
|---|---|---|---|---|
| Heavy | 2 | 2 | 1500m/2500m | 4Gi/**7Gi** |
| Medium | 3 | 3 | 1500m/2500m | 5Gi/7Gi |

Note: Heavy mem limit was 7Gi → patched to 10Gi on 2026-03-28 due to OOM on large 10-K filings.

---

## Temporary Config (APPLIED 2026-03-29)

```bash
# Heavy workers: 2 → 3
kubectl scale deploy -n processing xbrl-worker-heavy --replicas=3
kubectl patch scaledobject -n processing xbrl-worker-heavy-scaler --type merge -p '{"spec":{"maxReplicaCount":3}}'

# Medium workers: 3 → 5
kubectl scale deploy -n processing xbrl-worker-medium --replicas=5
kubectl patch scaledobject -n processing xbrl-worker-medium-scaler --type merge -p '{"spec":{"maxReplicaCount":5}}'
```

### Temporary Values
| | Replicas | KEDA Max | CPU Req/Limit | Mem Req/Limit |
|---|---|---|---|---|
| Heavy | 3 | 3 | 1500m/2500m (unchanged) | 4Gi/10Gi (unchanged) |
| Medium | 5 | 5 | 1500m/2500m (unchanged) | 5Gi/7Gi (unchanged) |

---

## News Disabled for Backfill (SKIP_NEWS_BACKFILL)

Same pattern as SKIP_TRANSCRIPTS_BACKFILL. Search tag: `SKIP_NEWS_BACKFILL`

5 code locations (search `SKIP_NEWS_BACKFILL`):
- `config/DataManagerCentral.py` line ~690: commented out BenzingaNewsManager init
- `config/DataManagerCentral.py` line ~726: commented out process_news_data() (already-init path)
- `config/DataManagerCentral.py` line ~745: commented out process_news_data() (first-init path)
- `scripts/run_event_trader.py` line ~201: removed SOURCE_NEWS from sources
- `scripts/run_event_trader.py` line ~309: removed SOURCE_NEWS from sources_to_check

Revert: uncomment all 5 locations (search for SKIP_NEWS_BACKFILL)

Rationale: News already exists in Neo4j from live mode (2,447-7,945 articles/month).
Re-fetching during backfill is redundant — all deduped. Saves API calls + chunk time.
