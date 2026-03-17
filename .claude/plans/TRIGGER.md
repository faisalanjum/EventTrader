# Trade-Ready Earnings Scanner

**Status**: Phase 1+2 COMPLETE. Live in K8s since 2026-03-16.

Automated scanner polls 3 earnings calendar sources 4x/day, matches against our ~800-company universe, and accumulates a persistent Redis TradeReady list. Entries never expire — once a ticker is added, it stays forever.

---

## Architecture

```
K8s CronJob (4x/day, Sun–Fri, America/New_York)
  └─ scripts/trade_ready_scanner.py
       ├─ [PRIMARY]   Alpha Vantage EARNINGS_CALENDAR (1 bulk call → filter to next trading day)
       ├─ [SECONDARY]  earningscall.biz get_calendar(date) (1-2 calls: today + next trading day)
       ├─ [TIE-BREAK]  Yahoo Finance yfinance (only when sources disagree on date)
       ├─ Universe: Neo4j Company nodes (~796) → Redis → CSV fallback
       ├─ Merge, deduplicate, filter to universe
       └─ Write Redis (idempotent, append-only)
```

---

## Sources

| Role | Source | Calls/scan | Key field |
|---|---|---|---|
| **Primary** | Alpha Vantage `EARNINGS_CALENDAR` (paid) | 1 (bulk 3-month CSV, filter locally) | `time_of_day` (pre/post market) |
| **Secondary** | earningscall.biz `get_calendar(date)` | 1-2 (per date) | `conference_date` (exact call datetime) |
| **Tie-breaker** | Yahoo Finance `yfinance` | 0 usually, 1-5 on conflicts | `earnings_date` confirmation |

**Merge**: AV primary → earningscall adds `conference_date` + catches AV misses → Yahoo breaks date conflicts (2-of-3 majority wins, fallback: AV).

**API keys**: `ALPHAVANTAGE_API_KEY` and `EARNINGS_CALL_API_KEY` in `.env`.

---

## Redis Data Model (Persistent, No TTL, No Auto-Delete)

```
trade_ready:entries                          HASH — one key per ticker, grows monotonically
  LULU → {
    "ticker": "LULU",
    "earnings_date": "2026-03-17",
    "time_of_day": "post-market",
    "conference_date": "2026-03-17T16:30:00-04:00",
    "sources": ["alphavantage", "earningscall"],
    "date_agreement": 2,
    "added_at": "2026-03-16T23:20:18-04:00",
    "updated_at": "2026-03-16T23:29:03-04:00"
  }

trade_ready:by_date:2026-03-17               SET — {ASO, DOCU, HQY, LULU}
trade_ready:by_date:2026-03-18               SET — {FIVE, GIS, MU}
  (one set per earnings date, also persistent)

trade_ready:scan_log                         STRING — latest scan metadata only
```

Re-scans update `updated_at` and merge new data. `added_at` preserved from first discovery. Manual `--cleanup` available but never runs automatically.

---

## Schedule (Live)

| CronJob | Schedule (ET) | Purpose |
|---|---|---|
| `trade-ready-morning` | 7:00 AM Sun–Fri | Confirm today's reporters, catch overnight updates |
| `trade-ready-midday` | 12:00 PM Sun–Fri | Catch earningscall.biz mid-day refreshes |
| `trade-ready-close` | 4:30 PM Sun–Fri | End-of-day state, post-market additions |
| `trade-ready-evening` | 9:00 PM Sun–Fri | **Anchor scan** — APIs settled, tomorrow's list complete |

Sunday scans catch Monday pre-market. Saturday skipped. Each run: <15 seconds, 2-8 API calls.

Trading day logic uses `exchange_calendars` XNYS calendar (handles holidays, early closes).

---

## Files

| File | Purpose |
|---|---|
| `scripts/trade_ready_scanner.py` | Scanner script (~310 lines) |
| `k8s/processing/trade-ready-scanner.yaml` | 4 CronJob manifests |

## CLI

```bash
python3 scripts/trade_ready_scanner.py              # Scan + write Redis
python3 scripts/trade_ready_scanner.py --list        # Dry run (print only)
python3 scripts/trade_ready_scanner.py --show        # Show current list
python3 scripts/trade_ready_scanner.py --show --date 2026-03-17  # Filter by date
python3 scripts/trade_ready_scanner.py --source av   # Single source (av|ecall|yahoo)
python3 scripts/trade_ready_scanner.py --cleanup     # Manual purge of past entries
```

---

## Reliability

- CronJob specs persist in etcd (survive restarts)
- `backoffLimit: 3`, `startingDeadlineSeconds: 600`
- 4 scans/day = any single failure caught by next run
- 3 independent API sources = single source down doesn't block
- TradeReady list fully reconstructable from APIs if Redis loses it
- Idempotent: double-firing is harmless

---

## Phase 3 (Future)

1. 8-K filing detection → auto-trigger `earnings:trigger` queue for TradeReady tickers
2. Pre-warm extraction pipeline (guidance inventory, concept cache) for upcoming tickers
