# Massive Replacement Audit

This folder is an isolated, read-only audit of whether London Strategic Edge
(LSE) or the project's existing Interactive Brokers (IBKR) connection can
replace Massive in EventMarketDB.

Permanent project location:
`data/lse_massive_replacement/`

## Decision

### Overall result after testing IBKR

IBKR is the best main source for future live U.S. stock-event prices. LSE is
not needed in the bot's core price path; it remains optional for a separate
macro display or a backup comparison.

The current evidence is:

- IBKR qualified 751 of the 783 configured stock tickers. One, `PINC`,
  resolves to a new ETF rather than the old company, leaving 750 intended
  company identities resolved. The remaining 32 tickers need removal,
  renaming, or a separate identity review.
- Of the 29 configured stocks missing from LSE, the three clearly current
  companies in the live check—`FCPT`, `LESL`, and `VNO`—all had live IBKR
  prices. `PINC` was the wrong reused identity.
- IBKR qualified and returned live bid and ask prices for 61 of the 63
  production sector and industry ETFs. `COMM` is an invalid production
  benchmark mapping, and `EATZ` stopped trading before liquidation in May
  2026.
- A ten-second pre-market test received 13 detailed live trades across
  `AAPL`, `SPY`, `XLK`, `SOXX`, and `XLE`, including price, size, exchange,
  time, conditions, and trade flags.
- Across five stored Massive event examples and 20 stock/benchmark return
  legs, 16 matched exactly after rounding to two decimals. Eighteen differed
  by no more than 0.01 percentage points. The two larger differences were in
  a thin 4:00–5:00 AM test: `IHI` differed by 0.02 and `ABT` by 0.28
  percentage points.
- All 624 tested daily returns matched exactly. Of 416 tested 14-day ATR
  windows, 324 matched at two decimals; the average ATR difference was
  0.00237 price units and the largest was 0.02071.

This is enough to recommend IBKR for the live event path:

```text
live stock + sector ETF + industry ETF + SPY
                         |
                         v
                 IBKR live stream
                         |
                         v
                save and calculate locally
```

It is not yet proof that IBKR can recreate every historical Massive value.
IBKR limits rapid one-second history requests, one-second bars are available
for only about six months, delisted symbols have no history, and the thin
4:00–5:00 AM case did not match exactly. Stored Massive data should remain
the reference for old calculations.

The existing EventMarketDB IBKR connection is a persistent TCP stream through
IB Gateway. It is not technically a WebSocket, but it pushes live updates
without polling. IBKR also offers a separate Client Portal WebSocket, which
this project does not currently use. The existing stream is the simpler
choice for this bot.

Current IBKR limits also matter:

- the account normally has 100 simultaneous market-data lines;
- with 100 lines, up to five detailed tick-by-tick streams can run at once;
- one event needs four streams, so its stock, sector ETF, industry ETF, and
  `SPY` fit;
- all 783 configured tickers cannot be streamed simultaneously;
- rapid historical requests must be scheduled and cached.

Recommended source roles:

| Need | Source |
|---|---|
| Future live stock and benchmark prices | IBKR |
| Pre-market and after-hours prices | IBKR |
| Old historical calculations | Stored Massive data |
| Optional macro display or backup comparison | LSE |

No production IBKR file, setting, subscription, order, Kubernetes object, or
database record was changed during these tests.

### LSE-only result

LSE cannot replace Massive as the only EventMarketDB source today. Its
regular-hours stock candles are promising, but required ETFs, daily values,
ATR, macro history, stored fields, feed rules, and data rights do not meet the
current system's needs.

The full 63-benchmark search is now complete. Four ETFs exist exactly on LSE.
Official-holdings baskets were strong under the normal 80% constituent-data
rule in both the 2023–2026 history and the recent live overlap for nine more.
Another 23 were strong in both periods only after relaxing constituent-weight
and/or target-date coverage. Twenty-one were partial or context-only, five
had no supported replacement, and `COMM` is an invalid existing production
mapping.

This creates a credible path for a hybrid regular-market return source, but
it does not recreate Massive's one-second event bars, pre-market or
after-hours ETF moves, official daily fields, or every required benchmark.
A 2026-07-20 U.S. pre-market check confirmed current-minute REST bars and
current NVDA WebSocket ticks. A regular-session load test, full feed
completeness, and the vendor's contractual real-time rights remain unproven.

Important test distinction: the long comparison ends on 2026-04-27, which is
also when LSE's current live stock collection begins for many symbols. A stock
with no older LSE archive can therefore still be available live now. The
audit keeps the three-year archive result and a separate 2026-04-28 through
2026-07-17 live-overlap result so that an archive gap is not mislabeled as a
current coverage gap.

## Safety boundary

- No EventMarketDB production source file is changed.
- No production database is written.
- Production code and databases may be read to document current behavior.
- All new scripts, downloaded samples, comparisons, and reports stay in this folder.
- No live API key or other secret is present in the final folder.

## Hourly timing re-check

The 2026-07-20 read-only re-check confirmed the exact production timing:

- all 257 current Redis records matched their saved hourly, session, and daily
  end times;
- all 386,998 News and filing return relationships with a saved Neo4j hourly
  schedule matched exactly;
- 9,373 Transcript relationships do not retain a saved schedule, so
  their end can only be reconstructed;
- 169 historical relationships expose an existing early-close bug: events
  between the early close and 4:00 PM were assigned that day's 4:00–5:00 AM
  window;
- Neo4j `relationship.created_at`, not the News node's sometimes-stale
  `created`, is the event time attached to the stored return.

The detailed evidence is
`results/return_timing_storage_reaudit_2026-07-20.json`.

## Main report

See [`docs/FINDINGS.md`](docs/FINDINGS.md).

The one-row-per-benchmark result is in
[`docs/ALL63_REPLACEMENT_MATRIX.md`](docs/ALL63_REPLACEMENT_MATRIX.md).
Its full numerical forms are:

- `results/all63_replacement_matrix_2026-07-19.json`
- `inventory/all63_replacement_matrix_2026-07-19.csv`

The larger local evidence sets, sizes, and checksums are recorded in
[`docs/LOCAL_ARTIFACTS.md`](docs/LOCAL_ARTIFACTS.md).

## Automatic split handling

Basket calculations do not contain hardcoded split symbols, dates, or ratios.
The isolated loader requests all LSE split records for the calculation
period. If LSE's 5,000-row response cap is reached, it divides the date range
automatically until every returned range is below the cap.

For 2023-01-03 through 2026-07-17, it loaded 11,188 split rows covering 8,953
symbols. A split factor is applied only when it reduces the raw close jump.
This corrects unadjusted candles while avoiding a second adjustment when LSE
already corrected older candles.

Future splits use the same path. When `--end` is omitted, the loader uses
today's date. A future production replacement would run this refresh daily or
at startup; no refresh job has been enabled in production.

```bash
LSE_API_KEY=your_key venv/bin/python \
  data/lse_massive_replacement/scripts/audit_lse_split_adjustments.py \
  --start 2023-01-03 \
  --cache-dir data/lse_massive_replacement/raw/reference_periods \
  --output data/lse_massive_replacement/results/lse_stock_splits_complete.json
```

Evidence:

- `results/lse_split_adjustment_summary_2026-07-19.json`
- `results/lse_stock_splits_complete_2023-01-03_to_2026-07-17.json`
- `scripts/audit_lse_split_adjustments.py`
- `tests/test_audit_lse_split_adjustments.py`
- `tests/test_run_proxy_pilot.py`

## Exact production ETF check

See
[`docs/PRODUCTION_ETF_COVERAGE.md`](docs/PRODUCTION_ETF_COVERAGE.md)
for the fresh per-ticker audit.

- Production uses 11 sector and 52 industry benchmark tickers.
- LSE has exact prices for only `XLE`, `XLF`, `GDX`, and `SOXX`.
- All 59 missing tickers were checked across the full catalog and through
  direct normal and ETF-only candle requests.
- Zero of the 783 current companies has both required benchmark ETFs on LSE.
- `COMM`, assigned as NYT's publishing benchmark, is actually a former
  CommScope company ticker and is a separate production mapping problem.
- `EATZ`, used by 14 restaurant companies, stopped trading on 2026-04-30 and
  was liquidated. It also needs a new production benchmark regardless of
  which price source is chosen.

## Recommended 17-signal U.S. stock context panel

Goal: help a trading bot decide whether a stock move may be coming from the
whole market, rates, credit, currencies, commodities, or another region
instead of company news alone.

This is the best default set for a general U.S. stock. The order is the
default importance; the bot should give more weight to a lower-ranked signal
when the company has a clear exposure to it.

| Rank | Indicator | LSE input or calculation | What it can explain |
|---:|---|---|---|
| 1 | Broad U.S. market | `ES.F` S&P 500 futures return | A market-wide move affecting nearly every stock; futures also cover most pre-market and after-hours periods |
| 2 | Scheduled macro shock | U.S. economic calendar | Fed decisions, inflation, jobs, GDP, and other releases that can suddenly move the whole market |
| 3 | Market fear | `VIX/USD` level and change | A fast rise is evidence of broad risk reduction rather than isolated company weakness |
| 4 | Long Treasury price shock | `USB10Y/USD` price return | A falling Treasury price normally means a rising long-term yield, which can pressure growth, real estate, and utilities |
| 5 | Short Treasury price shock | `USB02Y/USD` price return | A falling Treasury price normally means a rising 2Y yield and tighter expected Fed policy |
| 6 | Credit stress | `HYG` return | Financing stress affecting indebted, smaller, and economically sensitive companies |
| 7 | Growth versus market | `NQ.F` return minus `ES.F` return | Whether technology and long-duration growth stocks are being treated differently from the broad market |
| 8 | Daily yield-curve shape | Daily `US10YT=RR` yield minus `US2YT=RR` yield through REST | Banking conditions and changes in the market's growth or recession view |
| 9 | U.S. dollar | `DXY/USD` return | Foreign-revenue translation, import costs, and pressure on commodities |
| 10 | Small companies versus market | `US2000/USD` return minus `ES.F` return | Domestic growth, financing conditions, and risk appetite for smaller companies |
| 11 | Semiconductors versus market | `SMH` return minus `ES.F` return | Chip, hardware, AI, and electronics supply-chain pressure |
| 12 | Oil | `WTICO/USD` return | Energy-company revenue, inflation pressure, and costs for airlines, transport, chemicals, and consumers |
| 13 | Yen and carry-trade stress | `USD/JPY` return | A sharp fall means yen strength and can warn of global borrowing-position unwinds |
| 14 | Copper | `XCU/USD` return | Industrial demand, construction, China sensitivity, and the global growth cycle |
| 15 | Gold | `GC.F` gold-futures return | Fear, inflation, and real-rate pressure; it should be read with rates and the dollar |
| 16 | China | `CN50/USD` return | China demand, production, supply-chain, and policy shocks |
| 17 | Europe | `EU50/EUR` return | European demand and overnight risk for U.S. companies with European exposure |

### Why this fits the free live limit

The panel uses these 15 live macro symbols:

```text
ES.F, VIX/USD, USB10Y/USD, USB02Y/USD, HYG,
NQ.F, DXY/USD, US2000/USD, SMH, WTICO/USD,
USD/JPY, XCU/USD, GC.F, CN50/USD, EU50/EUR
```

The three relative-market indicators are calculated from those live inputs.
The actual yield curve and economic calendar are read through REST and use no
live subscription. This leaves the 16th simultaneous live slot for the stock
being traded.

Important rate rule: despite their dataset name, `USB02Y/USD` and
`USB10Y/USD` stream values near 103 and 109 with no percent unit. They are
Treasury **price-like inputs**, not yield percentages. Never subtract them to
make a yield curve. Use the daily percent-yield series `US2YT=RR` and
`US10YT=RR` for that calculation.

### Call limits and recommended frequency

For live prices, open one WebSocket connection, subscribe once, and keep it
open. Price updates then arrive automatically; there is no need to make a new
REST call for every update. The 15 macro symbols plus one traded stock use all
16 free live slots.

If REST polling is needed as a backup, the authenticated key allows 200 calls
per minute. One complete refresh requires 16 calls, so the absolute limit is:

```text
200 calls per minute / 16 symbols = 12.5 refreshes per minute
60 seconds / 12.5 = one refresh every 4.8 seconds
```

That maximum leaves no safe room for retries or the economic calendar. A
10-second REST backup is safer.

| Full-panel polling | Calls per minute | Calls in 24 hours | Calls in a 6.5-hour U.S. session |
|---|---:|---:|---:|
| Every 5 seconds | 192 | 276,480 | 74,880 |
| Every 10 seconds | 96 | 138,240 | 37,440 |
| Every minute | 16 | 23,040 | 6,240 |
| Every 5 minutes | 3.2 | 4,608 | 1,248 |

Recommended schedule:

- prices: continuous WebSocket updates;
- REST price backup: every 10 seconds only while needed;
- economic calendar: every 5 minutes normally and every 30 seconds near a
  known major release;
- slow economic and daily history: once after a new value is released.

REST and WebSocket traffic share the 15 GiB weekly and 50 GiB monthly data
allowances. Check `/vault/usage` regularly because the number of live ticks,
not merely the number of subscriptions, determines streaming usage. The
5,000-row request limit and five-export-per-hour limit matter for history, not
for the normal live-price loop.

### WebSocket ON/OFF switch

The isolated runner is
`scripts/macro_stream_switch.py`. Its saved switch is
`config/macro_stream.json`. The safe default and current state are **OFF**.
The API key is read from `LSE_API_KEY` only and is never saved.

From the repository root:

```bash
# Check the switch. This makes no network connection.
venv/bin/python data/lse_massive_replacement/scripts/macro_stream_switch.py status

# Allow connections, then run 15 macro symbols plus AAPL.
venv/bin/python data/lse_massive_replacement/scripts/macro_stream_switch.py on
LSE_API_KEY=your_key venv/bin/python \
  data/lse_massive_replacement/scripts/macro_stream_switch.py run AAPL

# Run this in another terminal to stop the active connection.
venv/bin/python data/lse_massive_replacement/scripts/macro_stream_switch.py off
```

For a short test, add `--max-seconds 30` or `--max-ticks 5`. The runner checks
the switch while connected, so changing it to OFF closes the WebSocket. A
missing or damaged switch file is also treated as OFF.

Live smoke test on 2026-07-19:

- started with the switch OFF;
- changed it to ON and subscribed to all 15 macro inputs plus AAPL;
- authenticated successfully and sent all 16 subscriptions with no server
  error;
- received five ticks, including current Sunday updates for the U.S. 2Y
  Treasury price input, Russell 2000, copper, and WTI;
- received one older China-index snapshot, proving that every tick must pass
  the timestamp-freshness check;
- ran a second live connection, changed the switch to OFF while it was active,
  and confirmed that it disconnected cleanly after 99 ticks;
- confirmed that another OFF run opened no connection.

This proves the switch, authentication, subscription count, tick delivery,
and clean OFF block. It does not yet prove AAPL's market-hours delay or that
all 15 macro inputs update continuously. The sanitized evidence is saved in
`results/macro_websocket_smoke_2026-07-19.json`.

### U.S. pre-market live check

At 6:13 AM Toronto/New York time on Monday, 2026-07-20:

- REST returned 6:13 AM one-minute bars for AAPL, NVDA, TSLA, and AMD when
  read about 21–22 seconds into that minute;
- the WebSocket authenticated with 16 subscriptions and delivered 15 current
  NVDA ticks during a 60-second run, with no error;
- a REST follow-up moved all four stocks to the 6:14 AM bar;
- one separately measured NVDA print reached the client about 3.0 seconds
  after its message timestamp;
- XLE also had pre-market bars, but its newest print was less frequent than
  the four stocks;
- the switch was OFF before the test and is OFF again.

This confirms that U.S. pre-market data is flowing through both interfaces
and that the tested stock messages were not timestamped 15 minutes behind.
It does not prove every trade is present, every symbol is equally fresh, or
that LSE grants contractual real-time production rights. Evidence:
`results/lse_us_premarket_live_probe_2026-07-20.json`.

### Live trades, quotes, and market depth — corrected finding

LSE has two different market-data WebSockets. The first check covered only
the official Python-client feed. A full check of the current website found a
second feed:

| Feed | What it covers | What the test received | Verdict |
|---|---|---|---|
| Official `data-ws` feed | Stocks and the wider catalog | Normal `tick` messages | Stock trades are usable as candidates; stock quotes are not |
| Website `ws` feed | 12 FX, index, gold, and silver symbols | Quotes, trade prints, snapshots, and depth updates | Live macro depth, but no stocks and no true L3 |

Three official-feed probes observed 202 pre-market messages across AAPL, AMD,
NVDA, and TSLA. All 202 had `bid == ask`; none had a positive spread. The
trade price equalled both fields on 194 messages and differed by one cent on
eight. There were no bid or ask sizes, exchange, sale condition, correction,
trade ID, or sequence fields. These are trade-like stock prints, not usable
top-of-book stock quotes and not a complete Massive-equivalent tape.

The same normal `tick` schema means something different for macro symbols. In
a mixed probe, all 133 EUR/USD, NAS100/USD, SPX500/USD, and XAU/USD messages
had a positive spread, `price == bid`, and volume 1. These are quote-like
updates. Code must therefore not assume that every LSE `tick` is the same
kind of market event.

The website feed accepted the same key with `l3_access: true` and a 16-symbol
limit. It delivered all of these 12 website-marked symbols:

```text
AUD/USD, DE30/EUR, EU50/EUR, EUR/USD, GBP/USD, NAS100/USD,
SPX500/USD, USD/CAD, USD/CHF, USD/JPY, XAG/USD, XAU/USD
```

It rejected AAPL and NVDA as unknown symbols. Its messages were:

```text
tick          -> bid, ask, price, volume, time
book_snapshot -> arrays of [price, size] bids and asks
depth         -> side, price, size, set/delete action, time
trade         -> price, size, buy/sell aggressor, time
```

This is price-level depth, normally called Level 2. It is not true Level 3,
because no order ID is present and the website itself stores one total size
per price. In the all-symbol probe, 30 of 120 snapshots were crossed: every
snapshot for USD/CAD, USD/CHF, and USD/JPY had a best bid above the best ask.
Also, 917 of 2,321 depth updates were older than the newest snapshot and 853
went backward in event time, with no sequence number to repair the order.
The feed also transforms raw futures prices onto the displayed macro symbol.
It is useful research data, but it is not a safe stock-book or exact exchange
book.

Quotes, snapshots, and depth appeared for all 12 symbols. Separate `trade`
messages appeared for 10 during the short sample; AUD/USD and USD/JPY had no
trade message in that window. That short silence does not prove those two
never publish trades. The saved result includes counts for every symbol.

The website code contains three other paths, none of which fixes the stock
gap:

- a public options-flow stream for option prints and options analytics, not
  stock quotes;
- real bid/ask quotes from a connected broker account, which cannot be used
  with the LSE data key alone;
- a BTC-only historical Level 2 profile. The standalone order-book pages use
  Binance demo data.

The public WebSocket documentation and official Python client do not document
the second website depth protocol. Full sanitized evidence is in
`results/lse_trade_quote_depth_probe_2026-07-20.json`.

Today's authenticated stream list still covers exactly 754 of the 783 current
EventMarketDB stocks. The same 29 are absent. The 754 can be selected
dynamically, but the free key streams only 16 symbols at once; it cannot watch
the whole universe simultaneously. Evidence:
`results/lse_live_tick_fields_and_universe_2026-07-20.json`.

### How the bot should judge an impact

For each signal, compare the move over the same 5-minute, 1-hour, session, and
daily windows as the stock. Measure the true daily yield series in percentage
points and every streamed price in percent. Compare each move with that
signal's normal movement for the same window.

Use this simple test:

```text
macro evidence =
unusual signal move × company exposure × matching timing × confirmation
```

A signal is evidence, not proof. The bot should call a move macro-related only
when the signal moved before or with the stock, the company is exposed to it,
and another related signal or a scheduled economic event supports the same
explanation.

Always check the latest timestamp. VIX, HYG, and SMH do not trade continuously;
when one is closed, an unchanged price means "stale," not "no risk."

For a strongly specialized stock, replace the least relevant global input.
For example, use `BTC/USD` for a crypto-linked stock or `NATGAS/USD` for a
natural-gas producer.

For historical calibration, use the long daily U.S. Treasury and USD
high-yield index series described in the main report. VIX and WTI remain the
two important short-history gaps. Live timing and completeness for all 15
symbols still require the planned market-session test.
