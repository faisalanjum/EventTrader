# BUG: Company fundamentals (shares_out, mkt_cap, employees) never updated

**Discovered**: 2026-03-04
**Status**: OPEN
**Severity**: Low — data is stale but not breaking anything

---

## Symptom

`shares_out`, `mkt_cap`, and `employees` on Company nodes reflect the values from initial graph setup and are never refreshed. For example AVGO shows `shares_out: 4,687,360,000` which may be outdated.

## Root Cause

`neograph/Neo4jInitializer._create_companies()` loads these from the static universe data (Redis/CSV) once during initialization. No periodic refresh exists.

## Files

- `neograph/Neo4jInitializer.py:367` — `_create_companies()` sets these fields once via MERGE
- Universe source: `admin:tradable_universe` in Redis
