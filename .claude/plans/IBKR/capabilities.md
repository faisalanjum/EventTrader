# IBKR MCP — Capabilities Reference

Functional companion to [`deployment.md`](deployment.md) (which covers pods/ports/recovery).
Verified live 2026-05-12 against `ibkr-live` MCP, account U5113348, NetLiq 728.72 CAD.

---

## 1. The 25 Tools — At a Glance

```
┌──────────────────────────────────────────────────────────────┐
│  ACCOUNT (3)     │ get_account_summary, get_positions,       │
│                  │ get_open_orders                            │
├──────────────────────────────────────────────────────────────┤
│  QUOTES (2)      │ get_price (single), get_tickers (batch)   │
├──────────────────────────────────────────────────────────────┤
│  HISTORY (1)     │ get_historical_bars (OHLCV, 1min→1M)      │
├──────────────────────────────────────────────────────────────┤
│  CONTRACTS (1)   │ get_contract_details (conID lookup)       │
├──────────────────────────────────────────────────────────────┤
│  OPTIONS (2)     │ get_options_chain, get_filtered_options_  │
│                  │ tickers (needs OPRA for greeks/quotes)    │
├──────────────────────────────────────────────────────────────┤
│  SCANNER (6)     │ workflow, scan_codes, instrument_codes,   │
│                  │ location_codes, filter_codes, results     │
├──────────────────────────────────────────────────────────────┤
│  ORDERS (9)      │ place_{market,limit,stop,trailing_stop,   │
│                  │ bracket,bracket_trailing,advanced},       │
│                  │ modify_order, cancel_order                │
├──────────────────────────────────────────────────────────────┤
│  ROOT (1)        │ read_root__get (health check)             │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. What Works / What Doesn't (verified 2026-05-12)

| Capability | Works? | Notes |
|------------|:------:|-------|
| Live US stock quotes (NASDAQ, NYSE, ARCA) | ✅ | Networks A+B+C subscribed |
| Historical OHLCV bars (stocks, forex) | ✅ | Free, no subscription |
| Forex live quotes (IDEALPRO) | ✅ | EUR/USD bid/ask flows |
| Contract / conID lookup | ✅ | All asset types resolve |
| Account state (balance, positions, orders) | ✅ | Flat account verified |
| Scanner (619 scan codes) | ✅ | Server-side, no extra sub needed |
| Options chain enumeration (contract IDs) | ✅ | Returns conIDs by expiry/strike/right |
| **Options market data / greeks** | ❌ | No OPRA — bid/ask/greeks return `null` |
| **Index spot** (SPX, VIX) | ⚠️ **DELAYED SNAPSHOT** | ⚠️ **NOT REAL-TIME** — returns a **delayed snapshot that refreshes during session**, NOT a stale previous-session close. `last == close` populates with the same delayed value; `bid`/`ask` are `null`. Verified across 2 sessions: SPX 7342.18 → 7457.21 (+1.6%, tracks SPY×10 ratio); intra-second probe also captured sub-tick moves (7457.85 → 7457.61). **Tell-tale**: `is_realtime: false, market_data_type: 2`. Usable for "rough where SPX is now"; NOT usable for tick-level trading decisions. Subscribe to **CBOE Streaming Market Indexes ($3.50/mo)** for real-time bid/ask — see §5. |
| **Index historical bars** (SPX, VIX daily + intraday) | ✅ **FREE** | Verified 2026-05-12 via `/ibkr/historical?symbol=SPX&sec_type=IND&exchange=CBOE&freq=1d` → 6 daily bars returned cleanly. 1-min intraday also works (650 bars over 2 days verified). `volume` is `null` (indices have no volume). **CBOE sub NOT needed for historical analysis** — only for the live spot value. |
| **Canadian stock quotes** (TSE/TSX) | ❌ | No TSX sub — contract resolves, data `null` |
| **Futures contract lookup with expiry** | ⚠️ | MCP server snake_case bug, see §6 |
| ETF-specific scanner (`ETF.EQ.US` instrument) | ⚠️ | Instrument code rejected; use `STK` + ETF location |

---

## 3. Scanner — Practical Cheat Sheet

The scanner has **619 scan codes × 152 locations × 1,279 filters**. Most are noise. Below is the curated set actually useful for our workflow.

### 3.1 Location codes (top 8)

| Code | What it scopes |
|------|----------------|
| `STK.US.MAJOR` | US large-caps (default for most scans) |
| `STK.US` | All US stocks incl. minor exchanges |
| `STK.US.MINOR` | OTC / small venues |
| `STK.NASDAQ.NMS` | Nasdaq NMS only |
| `STK.NYSE` | NYSE-listed only |
| `STK.ARCA` | NYSE Arca (most ETFs live here) |
| `ETF.EQ.US.MAJOR` | Major equity ETFs (combine with `instrument=STK`) |
| `STK.NA.TSE` | Toronto Stock Exchange — scanner endpoint accepts the code but **returns 0 results without paid TSX subscription** (verified 2026-05-13). Contract lookup still works for individual TSX-listed symbols. |

### 3.2 The 20 scan codes you'll actually use

**Movers & breadth**
| Code | Meaning |
|------|---------|
| `TOP_PERC_GAIN` | Biggest % gainers |
| `TOP_PERC_LOSE` | Biggest % losers |
| `TOP_OPEN_PERC_GAIN` | Gainers since open (intraday strength) |
| `TOP_OPEN_PERC_LOSE` | Losers since open |
| `HIGH_OPEN_GAP` | Largest gap-ups |
| `LOW_OPEN_GAP` | Largest gap-downs |
| `HIGH_VS_52W_HL` | Closest to 52-week high |
| `LOW_VS_52W_HL` | Closest to 52-week low |
| `HALTED` | Currently halted |
| `LIMIT_UP_DOWN` | Hit limit-up / limit-down |

**Volume & flow**
| Code | Meaning |
|------|---------|
| `MOST_ACTIVE` | Highest share volume |
| `MOST_ACTIVE_USD` | Highest dollar volume (better signal) |
| `HOT_BY_VOLUME` | Unusual volume vs average |
| `HOT_BY_PRICE` | Unusual price move |
| `TOP_TRADE_RATE` | Fastest tape right now |
| `TOP_STOCK_BUY_IMBALANCE_ADV_RATIO` | Auction buy imbalance |
| `TOP_STOCK_SELL_IMBALANCE_ADV_RATIO` | Auction sell imbalance |

**Options sentiment**
| Code | Meaning |
|------|---------|
| `HIGH_OPT_VOLUME_PUT_CALL_RATIO` | Put-heavy (bearish) |
| `LOW_OPT_VOLUME_PUT_CALL_RATIO` | Call-heavy (bullish) |
| `HOT_BY_OPT_VOLUME` | Unusual option activity |
| `HIGH_OPT_IMP_VOLAT_OVER_HIST` | IV >> HV (fear premium) |

**Earnings (Wall Street Horizon)** — Returns ranked ticker list only. No dates.
| Code | Meaning |
|------|---------|
| `WSH_NEXT_EARNINGS` | Next ~N earnings reporters, closest first |
| `WSH_PREV_EARNINGS` | Most recent reporters |
| `WSH_NEXT_MAJOR_EVENT` | Next major event (usually = next earnings) |
| `WSH_NEXT_EVENT` | Next event of any kind |
| `WSH_NEXT_ANALYST_MEETING` | Next analyst/investor day |

**Technicals**
| Code | Meaning |
|------|---------|
| `BULLISH_LAST_VS_EMA50` | Price > EMA50, bullish |
| `BEARISH_LAST_VS_EMA50` | Price < EMA50, bearish |
| `BULLISH_MACD_DIST_VS_LAST` | Bullish MACD divergence |
| `BEARISH_MACD_DIST_VS_LAST` | Bearish MACD divergence |
| `HIGH_LAST_VS_EMA200` | Most extended above 200d EMA |
| `LOW_LAST_VS_EMA200` | Most below 200d EMA |

### 3.3 Essential filter codes

Apply as comma-separated `key=value` string in the `filters` parameter.

| Filter | Example | Purpose |
|--------|---------|---------|
| `priceAbove` | `priceAbove=10` | Remove penny stocks |
| `priceBelow` | `priceBelow=500` | Cap upper end |
| `avgVolumeAbove` | `avgVolumeAbove=500000` | Liquidity floor |
| `marketCapAbove1e6` | `marketCapAbove1e6=10000` | ≥$10B cap (units = $M) |
| `marketCapBelow1e6` | `marketCapBelow1e6=2000` | small-cap only |
| `changePercAbove` | `changePercAbove=5` | Today's gainers ≥5% |
| `changePercBelow` | `changePercBelow=-5` | Today's losers ≤-5% |
| `optVolumeAbove` | `optVolumeAbove=10000` | Liquid options only |
| `impVolatAbove` | `impVolatAbove=0.5` | High-IV names |
| `numRatingsAbove` | `numRatingsAbove=10` | Well-covered names |

**Standard liquidity preset** (use almost everywhere):
```
priceAbove=10,avgVolumeAbove=500000
```

---

## 4. Recipes (copy-paste)

### Earnings prediction discovery
```python
# Find tickers reporting next, well-covered, liquid
get_scanner_results(
    instrument_code="STK",
    location_code="STK.US.MAJOR",
    scan_code="WSH_NEXT_EARNINGS",
    filters="priceAbove=10,avgVolumeAbove=500000,marketCapAbove1e6=2000",
    max_results=25,
)
# → Returns ticker list. Combine with Yahoo MCP for date/time/estimate.
```

### Today's risk-on/risk-off temperature
```python
# Run in parallel: gainers vs losers, defensive vs cyclical sectors
get_price(symbol="XLV", sec_type="STK", exchange="ARCA")  # Healthcare
get_price(symbol="XLP", sec_type="STK", exchange="ARCA")  # Staples
get_price(symbol="XLK", sec_type="STK", exchange="ARCA")  # Tech
get_price(symbol="XLY", sec_type="STK", exchange="ARCA")  # Consumer disc
# Read sector ETF sign pattern → defensive green + cyclical red = risk-off
```

### Unusual options activity
```python
get_scanner_results(
    instrument_code="STK",
    location_code="STK.US.MAJOR",
    scan_code="HOT_BY_OPT_VOLUME",
    filters="priceAbove=10,avgVolumeAbove=500000",
    max_results=15,
)
```

### 52-week breakout candidates
```python
get_scanner_results(
    instrument_code="STK",
    location_code="STK.US.MAJOR",
    scan_code="HIGH_VS_52W_HL",
    filters="priceAbove=20,avgVolumeAbove=500000,marketCapAbove1e6=5000",
    max_results=20,
)
```

### Pull 1-minute bars for backtesting (max ~30-60 days back)
```python
get_historical_bars(
    symbol="AAPL", sec_type="STK", exchange="NASDAQ",
    freq="1min",
    from_date="2026-05-01", to_date="2026-05-12",
    use_rth=True,  # regular hours only
)
```

### Forex daily
```python
get_historical_bars(
    symbol="EUR", sec_type="CASH", exchange="IDEALPRO", currency="USD",
    freq="1d",
    from_date="2026-01-01", to_date="2026-05-12",
)
```

---

## 5. Subscription Gates — What buys what

### Currently active (verified 2026-05-14)

| Feed | Cost/mo USD | Unlocks |
|------|--------:|---------|
| **NASDAQ (Network C/UTP)(NP,L1)** | $1.50 | Live bid/ask for NASDAQ-listed stocks (AAPL, MSFT, NVDA…) |
| **NYSE (Network A/CTA)(NP,L1)** | $1.50 | Live bid/ask for NYSE-listed stocks (JPM, V, WMT…) |
| **Network B (NP,L1)** | $1.50 | Live bid/ask for NYSE Arca/AMEX/BATS/IEX (SPY, ETFs, CBOE) |
| **OPRA (US Options Exchanges)(NP,L1)** | $1.50 | Live bid/ask + greeks for ALL US-listed options. Verified live 2026-05-14 09:50 ET — AAPL $295C: bid 3.80 / ask 4.00 / delta 0.669 / IV 33.6% / `marketDataType=1`. **Waived if monthly options commissions ≥ $20**. |
| | **$6.00** | **TOTAL — 100% Neo4j universe + 100% IV coverage** |

### Free L2 add-ons activated 2026-05-14 (no cost, pure upside)

| Feed | Cost | What it adds beyond L1 |
|------|--------:|---------|
| **IEX Depth of Book (NP,L2)** | $0 (waived) | Order-book depth on IEX. Useful for any future flow-imbalance / institutional-vs-retail research. |
| **ICE Futures US — Gold and Silver (L2)** | $0 (waived) | Depth on ZG/YG (gold), ZI/YI (silver) — these are ICE-traded, NOT the more-liquid COMEX /GC /SI. Free, future-ready. |
| **ICE Futures US — Digital Asset Futures (L2)** | $0 (waived) | Depth on ICE-listed Bitcoin futures. NOT the same as PAXOS crypto spot. Free, future-ready. |

**Universe coverage breakdown** (re-verified against Neo4j 2026-05-14):

| Exchange (Neo4j `Company.exchange`) | Stocks | % | Covered by |
|------------------------------------|------:|--:|------------|
| `NYS` (NYSE)                        |   457 | 57.4% | Network A |
| `NAS` (NASDAQ)                      |   335 | 42.1% | Network C |
| `TSE` (CP, PD, QSR — dual-listed)   |     3 |  0.4% | Network A (US-side) |
| `BATS` (CBOE Inc itself)            |     1 |  0.1% | Network B |
| **TOTAL**                           | **796** | **100%** | All 3 feeds |

→ **TSX subscription explicitly NOT needed**: the 3 Canadian dual-listed names (CP, PD, QSR) trade their primary US liquidity via NYSE — Network A covers them. Saves ~CAD 9/mo.

Free auto-subscribed (per-contract `tradingHours` gate LIVE in `ext-hours-v4`, 2026-05-14):

| Feed | Cost | Unlocks |
|------|--------:|---------|
| IDEALPRO FX | $0 | Real-time bid/ask 24/5 — EUR/USD, USD/JPY, GBP/USD, … **institutional-grade**, min order USD 25k |
| IDEAL FX *(odd-lot variant — NOT subscribed)* | $0 | Sub-$25k retail order quotes; spreads SLIGHTLY wider than IDEALPRO. Skip — IDEALPRO covers what we need. |
| PAXOS Cryptocurrency | $0 | BTC, ETH, LTC top-of-book |
| US + EU Bond Quotes (L1+L2) | $0 | CUSIP-level bond quotes |
| Korean Exchange (NP,L1) | $0 | Korean equity quotes (low priority) |
| Alternative European Equities (L1) | $0 | European alt-venue equities |
| US Mutual Funds (NP,L1) | $0 | Mutual fund NAVs |
| **IBKR-PRO BBO** (auto) | $0 | BBO across BATS/BYX/EDGX/EDGEA/IEX. Partial overlap with Network B; serves as redundancy. |

### Future subscription candidates (NOT active — decide individually)

User asked these be flagged so future bots / planning sessions know what's available to unlock:

| Subscription | Cost/mo USD | When to add | Agent value |
|---|--------:|---|---|
| **CBOE Streaming Market Indexes (NP)** | **$3.50** | When agents need real-time **^VIX, ^SPX, ^VXN** for regime detection. Currently `macro_snapshot.py` pulls these via yfinance (delayed/EOD). **STRONG candidate.** Note: this sub is for the LIVE spot value only — historical SPX/VIX bars are ALREADY FREE via `get_historical_bars` (verified 2026-05-12; daily AND 1-min intraday both work without any sub). So if your only need is historical backtest/PIT analysis, do NOT buy this. | **High** — fear index + spot S&P real-time = critical for any quant strategy |
| ~~OPRA (US Options Exchanges)~~ | ~~$1.50~~ | **ACTIVATED 2026-05-14** — see "Currently active" table above. |
| **CME Real-Time (NP,L1)** | $1.55 | When agents need /ES premarket S&P futures direction or cross-asset signals. Fee waived at ≥USD 20/mo futures commissions. | Medium — premarket regime signal |
| **NYMEX Real-Time (NP,L1)** | $1.55 | When agents need /CL crude oil for energy sector / XLE context. Waived at ≥USD 20 futures commissions. | Low-medium — energy-specific |
| **COMEX Real-Time (NP,L1)** | $1.55 | When agents need /GC gold for safe-haven / inflation signal. Waived at ≥USD 20 futures commissions. | Low-medium — macro safe-haven |
| NASDAQ Global Index Service | $3.50 | NDX, COMP spot — duplicates CBOE coverage if that's bought | Skip if CBOE Indexes already subscribed |
| Toronto Stk Exch | CAD 9.00 | Canadian TSX listings — 3 dual-listed in Neo4j (CP/PD/QSR) already work via NYSE side | Skip |

### Never buy (verified anti-recommendation)

| ❌ Don't buy | Reason |
|---|---|
| US Securities Snapshot Bundle ($10) | Not streaming for equities; snapshot mode still costs $0.01/quote |
| US Equity & Options Add-On Streaming Bundle ($4.50) | Requires the $10 bundle → real total $14.50; the 3 standalone L1 feeds + OPRA cost $6.00 for identical coverage |
| Cboe One Add-On Bundle | Redundant with free IBKR-PRO non-consolidated feed |
| All L2 depth-of-book ($3.50-$25 each) | Predictor + trade daemon use top-of-book only |
| Mexican / European depth / OTC feeds | Zero relevant tickers in Neo4j |

Historical bars: free regardless. Scanner: server-side, free regardless of feed.

**Full rationale + waiver math + funding-gate notes**: see [`project_ibkr_market_data.md`](../../../.claude/projects/-home-faisal-EventMarketDB/memory/project_ibkr_market_data.md) in memory.

### 5b. Already have, NOT currently consumed (audit, for future-bot awareness)

These auto-subscribed / free feeds are LIVE but nothing in production pulls from them. Listed so future bots considering new features know what's already free.

| Feed | Cost | Status | Could be useful for |
|------|------:|--------|---------------------|
| **IDEALPRO FX** | $0 | LIVE, unused | USD-strength macro signal; predictor never reads forex (grep verified) |
| **PAXOS Cryptocurrency** | $0 | LIVE, unused | BTC correlation as risk regime |
| **US + EU Bond Quotes (L1+L2)** | $0 | LIVE, unused | CUSIP-level bond quotes — predictor uses bond ETFs (TLT/SHY/IEF) via Network C instead |
| **IBKR-PRO BBO** | $0 | LIVE, unused | Partial overlap with Network B; quality redundancy signal |
| **Korea Exchange / Alt European Equities / US Mutual Funds** | $0 | LIVE, unused | n/a — none of these tickers in our universe |
| **IEX Depth of Book (L2)** | $0 | LIVE 2026-05-14, unused | Order-book depth on IEX — future flow research |
| **ICE Futures Gold/Silver (L2)** | $0 | LIVE 2026-05-14, unused | Depth on ZG/YG/ZI/YI (ICE-only, NOT /GC COMEX) |
| **ICE Futures Digital Asset (L2)** | $0 | LIVE 2026-05-14, unused | ICE-listed BTC futures depth (not same as PAXOS spot) |

No action needed — listed for audit. To consume any of these, point a new feature at the appropriate `get_price` / `get_tickers` / `get_options_chain` MCP path.

---

## 6. Known Bugs / Limitations

| Bug | Symptom | Workaround / Fix |
|-----|---------|------------------|
| **Futures lookup with expiry** | `get_contract_details(SEC_TYPE=FUT, options={"lastTradeDateOrContractMonth": "..."})` → `Contract.__init__() got an unexpected keyword argument 'last_trade_date_or_contract_month'` | MCP server is sending snake_case to `ib_async`, which expects camelCase. One-line fix in MCP server request handler. |
| **ETF instrument code rejected** | `instrument_code="ETF.EQ.US"` → `Invalid instrument code` | Use `instrument_code="STK"` with `location_code="ETF.EQ.US.MAJOR"` instead. |
| **Index get_price returns delayed snapshot (not live, not stale)** | SPX/VIX: `last == close` populate with a delayed value that refreshes during session; `bid`/`ask` always `null`; flagged via `is_realtime: false, market_data_type: 2`. Value tracks the live index (verified 7342.18→7457.21 across two sessions). | Treat as approximate index level, not a tick-precise quote. Use `SPY × 10` as a live S&P proxy if you need tick precision. Subscribe to **CBOE Streaming Market Indexes ($3.50/mo)** for real-time bid/ask. |
| **Forex / 24-5 assets — gate was NYSE-only pre-Phase-2** | Pre-`ext-hours-v3`: `EUR.USD` etc. returned `bid/ask: null, is_realtime: false, market_data_type: 2` outside NYSE 04:00–20:00 ET despite forex trading 24/5. | **Phase 2 SHIPPED (`ext-hours-v4`, 2026-05-14)**: per-contract `is_contract_open()` replaces the NYSE-wide gate; each asset class now uses its own `contract.tradingHours`. Pre-deploy parser empirically validated 25/25 across STK/CASH/FUT/IND. **Post-deploy live re-verification of forex behavior OUTSIDE NYSE hours has NOT been performed** — fall back to `get_historical_bars` if you observe stale data. |
| **`Ticker.marketDataType` defaults to 1 when no tick received** | ib_async sets the field to `1` (Live) on init and only changes it when IBKR sends a marketDataType tick. A response with `mdt=1` AND `bid/ask/last` all `null` means **no data flowed at all**, NOT "OPRA-live". Empirically observed 2026-05-14 07:30 ET: AAPL option (no OPRA sub) returned `mdt=1` with everything null; AAPL stock (with sub) returned `mdt=1` with populated bid/ask = genuinely live. | Always check `mdt=1 AND (bid OR last is populated)` before treating data as live. Field exposed on both `PriceSnapshot` (Phase 1) and `TickerData` (`ext-hours-v5`, 2026-05-14). |
| **Imbalance scans starve under liquidity filter** | `TOP_STOCK_BUY_IMBALANCE_ADV_RATIO` / `TOP_STOCK_SELL_IMBALANCE_ADV_RATIO` with `priceAbove=10,avgVolumeAbove=500000` filter return 0–1 results during regular session (verified 2026-05-13: BUY=1, SELL=0). Same scans WITHOUT the liquidity filter return 2–5 results. | Imbalances live in microcap/illiquid names where the auction is most lopsided. Run these scans **without** `avgVolumeAbove` to get meaningful results. |
| ~~Option market data returns null~~ | ~~OPRA not subscribed~~ | **RESOLVED 2026-05-14**: OPRA subscribed. AAPL $295C verified live: bid 3.80 / ask 4.00 / delta 0.669 / IV 33.6%. |
| **WSH scanner has no dates** | Returns ticker list only | Cross-reference Yahoo MCP / Neo4j for date+time. |
| **`get_open_orders` is clientId=1 only** | Won't see orders placed by other clientIds | Documented. Order tools use clientId=1 by default. |

---

## 7. Order Tools — Untested on LIVE

⚠️ Live account has `READ_ONLY_API=no` (orders *would* execute). All 9 order tools (`place_*`, `modify_order`, `cancel_order`) **have not been tested on live** in this session. Test on **paper** (`mcp__ibkr-paper`, port 31101, $1.1M CAD paper balance) before any live use.

---

## 7b. Implied Volatility — canonical methodology (gated on OPRA $1.50/mo)

**Status as of 2026-05-14**: OPRA NOT subscribed. Methodology now CODIFIED + tested in `scripts/iv/compute_iv_moves.py` (43 unit tests, pre-OPRA pipeline validated empirically). The moment OPRA activates, the script is ready — see `scripts/iv/README.md`.

**Coverage verified empirically 2026-05-14**: 756/756 = **100% of tradeable stocks** in `admin:tradable_universe:symbols` have listed options on OPRA-covered exchanges (the 27 non-resolving names are already-delisted M&A targets — can't be traded). One probe of `reqSecDefOptParams` per ticker is enough to verify.

This section below is the authoritative theoretical reference. Cross-referenced against IBKR official TWS API docs.

### 7b.1 How IB delivers IV — server-side, no client math needed

IBKR Gateway computes Greeks + IV **server-side** and delivers them as tick types per option contract. Source: [TWS API Tick Types](https://interactivebrokers.github.io/tws-api/tick_types.html).

| Tick | What it is | Source price | Use for |
|---|---|---|---|
| **10** | Bid Option Computation | Option **bid** | Aggressive sell-side IV |
| **11** | Ask Option Computation | Option **ask** | Aggressive buy-side IV |
| **12** | Last Option Computation | Option **last** trade | Recent-trade IV |
| **13** | **Model Option Computation** | IB's option **model** | **CANONICAL** — "Correspond to greeks shown in TWS" |
| **23** | Option Historical Volatility | 30-day realized | Reference HV (needs generic tick 104) |
| **24** | Option Implied Volatility (at-money 30-day) | Two consecutive expiries | At-market 30-day IV (needs generic tick 106) |

**Each tickOptionComputation event** delivers an `OptionComputation` struct with:
```
impliedVol, delta, gamma, vega, theta, optPrice, undPrice, pvDividend, tickAttrib
```

### 7b.2 ib_async exposes these as Ticker attributes

Source: [ib_async Ticker class](https://ib-api-reloaded.github.io/ib_async/api.html).

```python
ticker.bidGreeks   # OptionComputation from tick 10 — IV at bid
ticker.askGreeks   # OptionComputation from tick 11 — IV at ask
ticker.lastGreeks  # OptionComputation from tick 12 — IV at last trade
ticker.modelGreeks # OptionComputation from tick 13 — CANONICAL ("TWS-shown")
```

**Use `modelGreeks.impliedVol`** as the per-contract IV. It's the value IB computes from its internal model + chain consensus, matching what TWS displays.

### 7b.3 Our MCP already exposes this end-to-end

| MCP tool | What it does | Where defined |
|---|---|---|
| `get_options_chain(underlying_*, filters)` | Enumerate conIds for filtered expirations/strikes | `app/services/contracts.py:101+` |
| `get_tickers(contract_ids)` | Bulk-fetch ticker incl. `modelGreeks` | `app/services/market_data.py:60+` |
| `get_filtered_options_tickers` (alias `get_and_filter_options`) | Chain + tickers + Greek-range filtering in one call | `app/services/market_data.py:108+` |

The `get_filtered_options_tickers` endpoint already extracts `modelGreeks` via `_greek_extraction()` (market_data.py:42) and returns `GreeksData{delta, gamma, vega, theta, impliedVol}` per contract.

### 7b.4 Methodology — per-stock IV at a PIT moment (the 790-universe case)

```python
# STEP 1 — Pick the target expiry
#   For earnings: nearest expiry AFTER the earnings date
#   For 30-day at-money IV: pick expiry ~30 days out (industry standard)

# STEP 2 — Get all option contracts at that expiry (calls + puts)
chain = get_options_chain(
    underlying_symbol="AAPL",
    underlying_sec_type="STK",
    underlying_con_id=265598,
    filters={"expirations": ["20260612"]},  # YYYYMMDD
)

# STEP 3 — Fetch tickers WITH Greeks for the chain
#   (or use get_filtered_options_tickers to combine + filter in one call)
tickers = get_tickers([c["conId"] for c in chain])
#   Each ticker has greeks.{delta, gamma, vega, theta, impliedVol}

# STEP 4 — Filter to ATM (delta near 0.50 for call, -0.50 for put)
atm_calls = [t for t in tickers
             if t["greeks"]["delta"] is not None
             and 0.40 <= t["greeks"]["delta"] <= 0.60]
atm_puts  = [t for t in tickers
             if t["greeks"]["delta"] is not None
             and -0.60 <= t["greeks"]["delta"] <= -0.40]

# STEP 5 — Apply quality filters (avoid wonky IV from illiquid options)
def is_clean(t):
    return (
        t["bid"] not in (None, -1) and t["ask"] not in (None, -1)  # both sides
        and (t["ask"] - t["bid"]) / t["ask"] < 0.30                # spread <30%
        and t["greeks"]["impliedVol"] is not None
        and 0.05 < t["greeks"]["impliedVol"] < 5.0                 # 5%-500% sanity
    )
atm_calls = [t for t in atm_calls if is_clean(t)]
atm_puts  = [t for t in atm_puts  if is_clean(t)]

# STEP 6a — Per-stock IV (canonical)
#   Average IV across the ATM call and put. Most robust.
iv_call = atm_calls[0]["greeks"]["impliedVol"] if atm_calls else None
iv_put  = atm_puts[0]["greeks"]["impliedVol"]  if atm_puts  else None
implied_vol = (iv_call + iv_put) / 2 if iv_call and iv_put else (iv_call or iv_put)

# STEP 6b — Implied move (% expected move for the expiry)
#   ATM straddle = call_mid + put_mid
#   Implied move % = straddle / underlying_price
call_mid = (atm_calls[0]["bid"] + atm_calls[0]["ask"]) / 2
put_mid  = (atm_puts[0]["bid"]  + atm_puts[0]["ask"])  / 2
spot = get_price(symbol="AAPL", sec_type="STK", exchange="NASDAQ")["last"]
implied_move_pct = (call_mid + put_mid) / spot
```

### 7b.5 Reliability gates — when to trust, when to skip

```
TRUST the IV if:
  ✅ modelGreeks.impliedVol is not None
  ✅ ATM call AND put both pass is_clean()
  ✅ call_iv and put_iv agree within 5 vol points (otherwise: skewed market)
  ✅ ticker.time within last 60 seconds (fresh quote)

SKIP / FALLBACK if:
  ❌ Bid is null OR -1 → option not actively quoted
  ❌ Spread > 30% of ask → too illiquid for reliable IV
  ❌ Only one of call/put has data → use the available one, flag as one-sided
  ❌ ticker.halted == True → underlying halted, IV stale
  ❌ Underlying just IPO'd (< 30 days) → no chain or thin chain

EXPECT TO SKIP: ~5% of an actively-traded 790-name universe during RTH;
                higher in pre/post market for less-liquid names.
```

### 7b.6 IV "accuracy" — be honest about what this means

```
Black-Scholes IV inversion is mathematically exact given input prices.
But INPUT PRICES vary — bid IV ≠ ask IV ≠ last IV ≠ model IV.

Methodology       Typical AAPL ATM Jan-2026 IV
─────────────────────────────────────────────
Bid IV (tick 10)    22.4%
Mid IV (call+put)/2 22.75%  ← what our pipeline computes
Last-trade IV       22.6%
Model IV (tick 13)  22.8%   ← CANONICAL (IB's "TWS-shown" value)
Bloomberg's model   22.83%
CBOE LiveVol        22.79%

Typical agreement across these: ±0.4-0.7 vol points (very tight).
→ "100% accurate" is methodologically meaningless for IV.
→ Realistic target: within ±1 vol point of professional vendors.
→ IB's modelGreeks hits this target easily.
```

### 7b.7 Subscription requirement summary

| Need | OPRA $1.50 required? | Notes |
|---|:---:|---|
| Real-time option bid/ask | ✅ Yes | Without OPRA, options chain returns null fields |
| modelGreeks.impliedVol per contract | ✅ Yes | IB computes only when chain ticks flow |
| Bulk Greeks across chain | ✅ Yes | Same |
| Historical option OHLCV bars | ✅ Yes (limited to ~90 days) | Per-contract via reqHistoricalData |
| Historical IV time series for backtests | ❌ Not available at any IB tier | Need external vendor (Polygon ~$29/mo, ORATS, etc.) |
| Greeks during pre/post market | ⚠️ Limited | Options markets thin in extended hours; many strikes null |

**Bottom line**: OPRA $1.50/mo unlocks the full canonical IV pipeline for all 790 stocks in real-time. Add when predictor wires up implied-move signals. Historical IV remains a vendor-only problem.

### 7b.8 Cross-references

- [TWS API: Option Greeks](https://interactivebrokers.github.io/tws-api/option_computations.html)
- [TWS API: Tick Types](https://interactivebrokers.github.io/tws-api/tick_types.html)
- [TWS API: Options](https://interactivebrokers.github.io/tws-api/options.html)
- [ib_async: Ticker class](https://ib-api-reloaded.github.io/ib_async/api.html)
- MCP source: `app/services/market_data.py:42` (`_greek_extraction`), `:108` (`get_and_filter_options`)
- MCP source: `app/services/contracts.py:101` (`get_options_chain`)

---

## 8. Subscription Activation Matrix — pre-purchase probes + post-purchase validation

For each candidate subscription, what to run BEFORE buying (does the data we want exist?) and AFTER buying (did it activate? am I getting live data?). Every probe + validation here is empirically tested.

### 8.1 OPRA (US Options) — $1.50/mo
- **Unlocks**: live option bid/ask + greeks across all OPRA-listed US equity & ETF options.
- **Pre-purchase probe** (free, ~3 min): `python scripts/iv/compute_iv_moves.py --universe-redis --market-data-type 3`
  - Reads `admin:tradable_universe:symbols` from Redis
  - Calls `reqSecDefOptParams` (free) + delayed quotes (free) for each
  - Output: coverage count + 15-min-delayed IV for validation
  - **Verified 2026-05-14**: 756/756 = 100% of tradeable stocks return a chain. AAPL/XLK return delayed IV (~25-27%, sensible).
- **Post-purchase validation**: `python scripts/iv/compute_iv_moves.py --universe-redis` (default `--market-data-type 1`)
  - Expect: `summary.ok` ≈ 720-750 (allowing for a few illiquid names);
    `call_iv` and `put_iv` populated on most rows;
    `expected_move_dollars` (straddle method) AND `em_from_iv_dollars` agree within ~30%.
- **Rollback signal**: if summary stays `no_quotes` for 15+ min after subscription, IBKR portal didn't activate.

### 8.2 CBOE Streaming Market Indexes — $3.50/mo
- **Unlocks**: real-time ^SPX, ^VIX, ^VXN spot quotes (today: delayed snapshot).
- **Pre-purchase probe** (free): `curl -sH "Authorization: Bearer $TOKEN" "http://127.0.0.1:18001/ibkr/price?symbol=SPX&sec_type=IND&exchange=CBOE" | jq .`
  - Expect today: `is_realtime: false, market_data_type: 2`, `bid/ask: null`, `last == close` (delayed snapshot).
- **Post-purchase validation**: same call.
  - Expect: `is_realtime: true, market_data_type: 1`, `bid` and `ask` populated, `last` ticking.

### 8.3 CME Real-Time L1 — $1.55/mo
- **Unlocks**: live `/ES`, `/NQ`, `/RTY`, `/YM`, etc. futures quotes.
- **Pre-purchase probe** (free): historical bars work right now — `curl -sH "Authorization: Bearer $TOKEN" "http://127.0.0.1:18001/ibkr/historical_bars?symbol=ES&sec_type=FUT&exchange=CME&freq=1d&from_date=2026-05-01"` returns daily OHLCV.
  - Live ticker today: `get_price ES FUT CME` returns historical fallback (Phase 2 routes correctly).
- **Post-purchase validation**: `get_price ES FUT CME` returns `is_realtime: true, market_data_type: 1`.

### 8.4 NYMEX Real-Time L1 — $1.55/mo
- **Unlocks**: live `/CL` (crude), `/HO`, `/RB`, `/NG`.
- **Pre-purchase probe**: historical bars for CL work; live returns historical fallback.
- **Post-purchase validation**: `get_price CL FUT NYMEX` returns `is_realtime: true`.

### 8.5 COMEX Real-Time L1 — $1.55/mo
- **Unlocks**: live `/GC` (gold), `/SI` (silver), `/HG` (copper).
- **Pre-purchase probe**: historical bars work; live returns historical fallback.
- **Post-purchase validation**: `get_price GC FUT COMEX` returns `is_realtime: true`.

### 8.6 Skip list (re-confirmed 2026-05-14)
- **US Equity & Options Add-On Streaming Bundle ($4.50 + $10 prereq)** — bundle pricing trap.
- **Cboe One Add-On Bundle ($1 + $10 prereq)** — free auto-sub covers it.
- **TSX Subscription (~CAD 9/mo)** — 3 dual-listed CA names trade US primary via Network A.
- **L2 / DEEP entitlements** — current strategies don't consume book depth.
- **Indices ($0.50/mo each)** — historical SPX/VIX bars are FREE; CBOE Streaming covers live in §8.2.

---

## 9. Cross-references

- [`deployment.md`](deployment.md) — pods, ports, recovery, K8s
- `~/.claude/projects/.../memory/project_ibkr_market_data.md` — subscription rationale + rejection list
- `~/.claude/projects/.../memory/MEMORY.md#IBKR` — high-level pointers
- `/home/faisal/EventMarketDB/ibkr-mcp-server/` — local fork of `omdv/ibkr-mcp-server`
- `/home/faisal/EventMarketDB/scripts/iv/` — IV+EM compute script (Stage §7b activation)
