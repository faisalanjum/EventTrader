# Google Finance Scraper — Reference

Real-time US market data from Google Finance + Yahoo Finance. Zero API keys, zero cost.
Validated: 754 tickers, 3 pulls, 2,262 fetches, **zero failures**.

## Scripts

### `scripts/gf_scraper.py` — Base Google Finance parser

Parses `AF_initDataCallback` JSON from Google Finance HTML. No browser needed.

```bash
venv/bin/python3 scripts/gf_scraper.py                  # indices, movers, news + article text
venv/bin/python3 scripts/gf_scraper.py --json            # JSON output
venv/bin/python3 scripts/gf_scraper.py --no-articles     # skip article text
venv/bin/python3 scripts/gf_scraper.py --section market  # market only
```

### `scripts/gf_snapshot.py` — Full macro snapshot

Google Finance + Yahoo Finance combined. Source tag on every section.

```bash
venv/bin/python3 scripts/gf_snapshot.py               # full snapshot (~1.3s)
venv/bin/python3 scripts/gf_snapshot.py --lite         # Google only, skip Yahoo
venv/bin/python3 scripts/gf_snapshot.py --json         # JSON for bots
```

### `scripts/gf_snapshot.py --ticker` — Per-stock deep dive

1-min bars (pre-market/regular/after-hours), 8Q financials, key events + article text.

```bash
venv/bin/python3 scripts/gf_snapshot.py --ticker AAPL              # full dive (~0.5s)
venv/bin/python3 scripts/gf_snapshot.py --ticker GS:NYSE --json    # explicit exchange, JSON
```

### `scripts/gf_validate.py` — Bulk validation

Fetches all tickers, validates data, optionally re-fetches after delay to verify price updates.

```bash
venv/bin/python3 scripts/gf_validate.py                  # full 792 tickers + 60s re-fetch
venv/bin/python3 scripts/gf_validate.py --skip-pull2     # single pull
venv/bin/python3 scripts/gf_validate.py --sample 20      # quick test
```

Prereq: `/tmp/ticker_universe.csv` (ticker,gf_exchange). Generate from Neo4j.

## Validation (2026-04-09)

| Metric | Result |
|--------|--------|
| Tickers resolved | 754/792 (38 delisted) |
| Fetch success | 754/754 × 3 pulls = **100%** |
| Price changes detected | 96 (Pull 1→2), 31 (Pull 2→3) |
| Regular session bars | 99.7% coverage, avg 349 bars |
| After-hours bars | 99.5% coverage, avg 10 bars |
| Quarterly financials | 82.8% |
| Key events / news | 81.8% |
| Speed | 19 tickers/sec, 39s for all 754 |

## Data map

```
gf_scraper.py  ← Google Finance homepage → indices, movers, earnings, news
gf_snapshot.py ← Google + Yahoo           → + sectors, rates, commodities, FX, crypto, global
  --ticker     ← Google stock page        → 1-min bars (all sessions), financials, events
gf_validate.py ← bulk fetch + compare     → coverage report, price-change verification
```

## Dependencies

`trafilatura`, `yfinance`, `beautifulsoup4`, `lxml`, `requests` — all in venv.
