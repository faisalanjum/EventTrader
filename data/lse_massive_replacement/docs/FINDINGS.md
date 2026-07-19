# Massive to London Strategic Edge Replacement Audit

Status: historical, code, and database audit complete; U.S. live-stock timing
test pending the next market session
Started: 2026-07-19
Repository inspected read-only: `/home/faisal/EventMarketDB`

## Goal

Determine, with historical and live evidence, whether London Strategic Edge can replace the current 15-minute delayed Massive subscription without changing EventMarketDB's results or required behavior.

The test is stricter than API availability. The candidate source must supply every input and reproduce every output currently derived from Massive, including:

- hourly returns;
- daily returns;
- market-session returns;
- relative returns;
- any other direct or indirect calculation found during the code and database audit;
- Massive-specific aggregate behavior on which the code relies.

## Decision

London Strategic Edge cannot replace Massive as EventMarketDB's only data
source today.

Its one-second stock candles are promising for a smaller, regular-hours
stock-only use: all 79 tested regular-hours returns were within 0.01
percentage points of the stored Massive result. But the full replacement
fails independently on several required inputs:

- zero current companies have both required sector and industry ETFs on LSE;
- LSE daily returns matched only 30.6% of 7,466 real graph comparisons;
- only 19 of 3,866 production-style ATR values matched;
- five of nine macro indicator ETFs are missing and ETF history starts only
  in April 2026;
- daily VWAP and transaction count are absent;
- LSE's tape lacks the trade conditions and sequence data needed to reproduce
  Massive's official candles;
- the separate Massive SEC risk-factor data has no LSE replacement;
- LSE's delay, feed source, market rights, and commercial-use rights are not
  yet clear enough for production use.

The remaining market-open test can measure U.S. stock tick delay and gaps. It
cannot remove the historical, coverage, field, or legal blockers above.

## Safety boundary

- Production source files were read-only throughout the audit.
- All audit code and output are contained in
  `data/lse_massive_replacement/`, outside the production packages.
- All database checks are read-only.
- No secret is saved to disk.

## Acceptance approach

1. Find every Massive call, wrapper, setting, stored field, database location, and downstream calculation.
2. Trace each value from source response to final stored or served output.
3. Write an exact replacement requirement for each use.
4. Reproduce the current calculation unchanged in this folder.
5. Feed equivalent London Strategic Edge data into the reproduced calculation.
6. Compare both sources across a broad set of symbols, dates, market sessions, and known edge cases.
7. Separate harmless rounding differences from true data or behavior gaps.
8. Give a supported verdict for every use: compatible, compatible with normalization, missing, or not yet proven.

## Confirmed before this audit

- The candidate REST API authenticated successfully.
- Its catalog contained 3,979 stock symbols.
- Exact symbol matching covered 754 of the 783 unique symbols in `config/final_symbols.csv` (96.3%).
- Its WebSocket authenticated and emitted a live crypto tick on Sunday.
- A live U.S. stock tick has not yet been proven because the first live test ran while the stock market was closed.

## Main findings

Historical calculation tests show an important split: LSE one-second stock
candles can be extremely close to stored Massive returns during regular
hours, while LSE daily candles, after-hours returns, benchmark coverage, and
stored daily record fields are not exact.

The main blockers are:

1. LSE is missing most sector and industry benchmark ETFs.
2. LSE ETF history begins on 2026-04-27, while EventMarketDB stores Massive
   daily prices back to 2023-01-03.
3. LSE candle rows do not contain VWAP or trade count, but both fields exist
   on every one of the 708,971 stored `HAS_PRICE` relationships.
4. LSE's raw stock tape omits sale conditions, exchange, correction flags,
   sequence number, and separate exchange/SIP timestamps. Massive uses those
   trade facts to decide which trades can change open, high, low, close, and
   volume.
5. LSE's synchronous candle endpoint rejected exact timestamp filters and
   accepted dates only. EventMarketDB asks Massive for one-second bars around
   exact timestamps.
6. The project also uses Massive's separate SEC risk-factor product. LSE does
   not list an equivalent product.
7. In the direct stored-graph comparison, no daily volume matched across 7,476
   overlapping stock/date rows and only 30.6% of 7,466 daily returns matched
   after rounding to two decimals. A separate live-API comparison gave the
   similar result of 29.6% exact.
8. The current Massive key can still read minute and daily aggregates, but its
   one-second aggregate request now returns `NOT_AUTHORIZED`. Exact historical
   one-second testing therefore uses already stored Neo4j returns as the
   Massive reference.

These findings come from production-code inspection, read-only database
queries, authenticated API calls, and historical value comparisons rather
than marketing claims.

### Parked follow-up: LSE after-hours moves

The first daily comparison indicates that LSE daily bars can include
after-hours price moves that Massive's official daily process keeps separate.
In the AVGO case studied below, the LSE daily bar was exactly a UTC-calendar-
day rollup of its raw trades, so it captured the earnings move after the U.S.
close. That may be useful later as a new event signal.

This idea is deliberately outside the replacement test. LSE must first
reproduce the existing Massive-based outputs under the same Massive rules.
Only after exact matching is settled will the after-hours signal be explored.

## What the production code actually does

### Main event-return path

```text
event timestamp
    -> market-session window
    -> Massive one-second aggregate close at start and end
    -> (end close - start close) / start close * 100
    -> round to 2 decimals
    -> Redis
    -> Neo4j relationship properties
```

For each event and each time window, the same calculation is run for four
symbols:

1. the company stock;
2. its sector ETF;
3. its industry ETF;
4. SPY.

The database stores the four raw returns. "Relative" or "adjusted" returns are
calculated later by simple subtraction:

```text
stock return - benchmark return
```

This is not a compounded relative return.

### Exact Massive price rule

The method is named `get_last_trade`, but it does not call a last-trade
endpoint. It calls Massive's official aggregate endpoint with:

- multiplier: `1`;
- span: `second`;
- split adjustment: `true`;
- sort: descending;
- initial lookback: 300 seconds;
- maximum fallback: five days.

It returns the `close` of the newest qualifying one-second bar whose bar-open
time is at or before the requested timestamp. If there is no bar, it expands
the search backward. It does not restrict the query to regular market hours,
so pre-market and after-hours trades can be used.

This is **trade data, not quote data**. Bid, ask, midpoint, and last quote never
enter the production formula. Massive builds the one-second candle from trades
that pass its sale-condition rules. A candidate quote match would therefore be
the wrong test even if the quoted price happened to be close.

This behavior matters. A replacement must match all of these details:

- split adjustment;
- one-second bar construction;
- which trades are eligible for a bar;
- bar timestamp meaning;
- sparse periods with no trade;
- extended-hours coverage;
- fallback to an earlier trade.

Massive documents that stock aggregate bars are built from qualifying trades
and that no bar is emitted when no eligible trade exists.

#### Exact fallback sequence

The requested backward windows are:

```text
300, 600, 1,200, 2,400, 4,800, 9,600, 19,200, 38,400,
76,800, 153,600, 307,200 seconds
```

After a successful empty response, each next window ends where the previous
window began. Although the argument is named `max_days_back=5`, the final
request actually reaches 614,100 seconds, or 7 days 2 hours 35 minutes, behind
the target. The final window is not clamped to the stated five-day boundary.
This exact behavior is now covered by an isolated test against the live
production class.

The installed Massive Python client is version `1.14.4`. Its `get_aggs`
method performs one HTTP request and does not follow `next_url`. Production
sorts newest-first, so the first page still contains the newest usable bar.
The first request uses limit 5,000; later requests use 49,998.

If a request raises an exception, production doubles the window but does not
move the window end backward. At the maximum window, repeated non-
authorization exceptions can repeat the same request indefinitely. This is an
existing failure behavior, not a candidate-data rule.

#### One-second boundary nuance

The code compares the **bar start** with the target, not each trade inside the
bar. Massive snaps aggregate queries to full resolution boundaries. Therefore
a bar starting at `10:00:00` can be selected for a target inside that same
second, even though its close can reflect a later qualifying trade before
`10:00:01`. Exact replacement means reproducing this one-second candle rule,
not merely selecting the final raw trade timestamp at or before the target.

The current Massive key no longer authorizes the historical one-second
endpoint, so the size of this sub-second effect cannot presently be measured
against the live endpoint. The code behavior and endpoint snapping rule are
confirmed; direct value testing must use stored returns or restored second-
aggregate access.

#### Massive sale-condition rules

The authenticated Conditions endpoint returned 55 stock trade conditions.
Forty-one are sale conditions with consolidated aggregation rules:

| Consolidated rule | Conditions |
|---|---:|
| Updates open/close, high/low, and volume | 23 |
| Updates volume only | 10 |
| Updates high/low and volume, but not open/close | 5 |
| Updates none of those fields | 2 |
| Updates open/close and high/low, but not volume | 1 |

The remaining 14 returned rows are financial or short-sale status indicators
without OHLCV update rules. Examples that matter at session boundaries include
Closing Prints, Opening Prints, Corrected Consolidated Close, extended-hours
trades, odd lots, average-price trades, and out-of-sequence trades.

Massive explicitly says second, minute, hour, and daily bars are not one
uniform rollup:

- second bars use a dedicated process and need not roll up exactly to minutes;
- minute bars apply CTA/UTP sale-condition rules;
- hour bars roll up eligible minute bars;
- daily bars use a broader official-session process that can include late
  messages, corrections, and recovery data.

This is a central replacement requirement. Rebuilding daily values from
minute candles, or one-second values from an unlabelled raw tape, is not
guaranteed to reproduce Massive.

### Time windows

All times are converted to `America/New_York`. The XNYS exchange calendar
controls trading days, holidays, and early closes.

| Stored return | Start | End |
|---|---|---|
| Hourly | event time, except closed-market events start at 4:00 AM on the current or next trading day | start + 60 minutes; it is not clamped to a session boundary |
| Session, pre-market | exact event time | 9:35 AM |
| Session, regular market | exact event time | market close |
| Session, after-hours | exact event time | next trading day at 9:35 AM |
| Session, closed market | previous/current after-hours end | next/current trading day at 9:35 AM |
| Daily, pre/regular market | prior trading close | current trading close |
| Daily, after-hours | current trading close | next trading close |
| Daily, non-trading day | prior trading close | next trading close |

Regular market open is 9:30 AM. The code deliberately uses 9:35 AM for
session endpoints after the open. Normal pre-market starts at 4:00 AM and
normal after-hours ends at 8:00 PM. On an early-close day, the code treats
after-hours as ending at the early close.

Boundary checks matter:

- exactly 4:00 PM on a normal day is still classified as regular market;
- at exactly 4:00 PM the session start and end are both 4:00 PM, creating a
  zero-length session window; 4:00:01 PM is after-hours;
- exactly 8:00 PM is classified as closed;
- the hourly end is always start plus 60 minutes, even when that crosses a
  session boundary.

The calendar code correctly changes UTC offsets across daylight-saving
weekends. For example, a Friday after-hours event before the spring change
ends at Monday 9:35 AM with the new `-04:00` offset; the fall case changes back
to `-05:00`.

There is also an existing early-close edge case that an exact replacement
would inherit. For an event at 2:00 PM on the 2025-11-28 early-close day, the
session window runs from 8:00 PM on the prior regular trading day to 9:35 AM
on the early-close day. The hourly window starts at 4:00 AM that day. Both
windows end before the event. The daily window still uses the prior close and
that day's 1:00 PM close. This appears to be a production scheduling bug, but
changing it is outside this data-source audit.

### Delay behavior

The advertised Massive delay is 15 minutes. Production actually waits
17 minutes (`17 * 60 = 1,020` seconds), adding a two-minute safety buffer.
Both the scheduler and the price method enforce this delay.

Massive says a second bar is first emitted after a two-second wait and may be
revised for up to 15 minutes as late trades and FINRA data arrive. That
official behavior is consistent with the project's 15-minute delay plus
two-minute buffer. This is an inference about why 17 minutes was chosen, not a
comment found in the code.

Removing the delay changes when a return can be calculated. It does not
change the requested start/end timestamps or the formula.

## Other Massive uses found

### Daily price graph

For every trading date, production calls Massive's grouped daily-market
summary twice: once for the date and once for the prior trading date.
The calls use split-adjusted data and exclude OTC stocks.

For symbols present on both dates, the code stores:

- open;
- high;
- low;
- close;
- volume;
- VWAP;
- transaction count;
- aggregate timestamp;
- `daily_return`, rounded to two decimals from the two closing prices.

The target set is company stocks, unique sector ETFs, unique industry ETFs,
and SPY.

This path specifically uses the **grouped daily** endpoint, not Massive's
daily open/close endpoint. A live AVGO check for 2024-12-12 proved that the
distinction is material:

| Massive result | Open | High | Low | Close | Volume |
|---|---:|---:|---:|---:|---:|
| Grouped daily, used by production | 180.93 | 182.00 | 175.99 | 180.66 | 46,958,170 |
| Daily open/close endpoint | 180.93 | 182.00 | 175.99 | 180.66 | 46,967,170 |

The graph row matches grouped daily exactly, including VWAP `183.8315`,
transaction count `531,173`, and timestamp. The other endpoint's volume is
9,000 shares higher.

Massive's split-adjusted volume can be fractional. The real graph contains
38,744 fractional-volume rows across 826 symbols, or 5.46% of all stored price
rows. By contrast, all 7,788 raw LSE daily rows in the ten-symbol cache had
integer volume. A replacement must preserve the adjusted volume value, not
coerce it to an integer or assume raw share count.

The current Massive entitlement returns minute and daily bars, but custom
daily history is limited to the latest two years. A request beginning in 2023
returned no rows before 2024-07-19.

The graph loader has one existing partial-date behavior: if a date already has
even one `HAS_PRICE` relationship, the normal loader skips the whole date.
`repair_partial_price_dates.py` exists to fill such dates. A replacement must
preserve the complete symbol batch and not mistake “one row exists” for “the
date is complete.”

### Dividends

Massive dividend records are requested per ticker with a 1,000-row page and
manual `next_url` pagination. The wrapper formally checks ticker, declaration
date, and cash amount, but it also directly reads dividend type, ex-dividend
date, and frequency; a missing one causes that record to be skipped. Currency,
payment date, and record date are read as optional.

In the actual graph, all 4,556 Dividend nodes contain every one of these
fields. Exact replacement therefore needs the full payload, regardless of the
wrapper's weaker formal check. Date relationships use the **declaration
date**, not the ex-dividend date.

### Splits

Massive split records are turned into `Split` nodes with ticker, execution
date, split-from, and split-to values. They are also requested per ticker with
manual pagination. All 40 graph nodes contain all four values.

### Historical macro snapshot

The earnings macro builder calls Massive directly for:

- SPY one-minute and daily bars;
- VIXY, TLT, SHY, HYG, IWM, RSP, USO, UUP, and GLD daily bars;
- the company's sector ETF one-minute bars during regular-market events.

It derives open-to-event, last-60-minute, overnight, daily, 5-day, 20-day,
year-to-date, moving-average, and volume measures. A one-minute bar is used
only after its full 60 seconds have elapsed.

The exact rules are:

- a minute bar is eligible only when its start plus 60 seconds is at or before
  the point-in-time timestamp;
- percentage values are rounded to two decimals;
- before or during regular market, today's daily bar is excluded; after the
  close it is included;
- 5-day and 20-day returns compare the close 5 or 20 settled sessions back
  with the latest settled close;
- year-to-date compares the first settled close in the current calendar year
  with the latest settled close;
- 5-day and 20-day volume are arithmetic means, and their ratio is calculated;
- the intraday open is the first returned minute bar, with no 9:30 AM filter,
  so it can be the first extended-hours bar;
- the last-60-minute baseline is the latest fully settled minute bar ending at
  least 60 minutes before the point in time;
- after the close, a minute-derived current level is kept if available; daily
  close is only a fallback;
- 50-day and 200-day moving averages are arithmetic means of daily closes.

The sector ETF's 5-day graph value follows a different rule. It sums five
stored daily percentage returns rather than compounding them. The
`sector_vs_spy_5d` field then subtracts SPY's close-to-close 5-day return, so
the two sides use slightly different methods.

VIX is a separate exception: its historical value comes from Yahoo's prior
settled daily close, even after 4:00 PM, because VIX settles at 4:15 PM.

### ATR comparison

The ATR utility calls Massive daily adjusted bars and calculates each true
range as:

```text
max(high - low, abs(high - prior close), abs(low - prior close))
```

ATR is the arithmetic mean of the final N true ranges.

### Ticker checks and health checks

Production asks Massive for ticker details to accept active U.S. common
stocks. Known benchmark ETFs bypass this stock validation. A separate health
check probes an AAPL one-second aggregate and can stop ingestion after three
confirmed authorization failures.

For event returns, the company is validated before any of the four legs are
calculated. If the company fails the current active-common-stock check, the
method returns missing values for the company, sector, industry, and SPY
together—even if the three benchmark prices exist.

The related-companies method exists in the wrapper but no caller was found.

### SEC risk-factor product

`scripts/ingest_massive_risk_factors.py` uses a separate Massive endpoint:

- `/stocks/taxonomies/vX/risk-factors`;
- `/stocks/filings/vX/risk-factors`.

This is not price data. It supplies a 140-category taxonomy, filing-level
classifications, and supporting text. It must be treated as a separate
replacement requirement.

Several old repair scripts also mention Massive. Some are valid maintenance
tools; others import classes or call methods that no longer exist. They are
being recorded separately so dormant code is not confused with the live
pipeline.

## Real Neo4j inventory

All figures below came from read-only queries against the existing database
on 2026-07-19.

### Daily prices

| Item | Actual count |
|---|---:|
| `HAS_PRICE` relationships | 708,971 |
| Dates with prices | 831 |
| Date span | 2023-01-03 to 2026-04-27 |
| Distinct stored price symbols | 860 |
| Company price relationships | 655,858 |
| Sector price relationships | 9,141 |
| Industry price relationships | 43,141 |
| SPY price relationships | 831 |

Every one of the 708,971 relationships has all nine expected properties:
OHLC, volume, VWAP, transaction count, timestamp, and daily return.

The graph currently has 796 company nodes with price history. This is larger
than the current `final_symbols.csv` file, which contains 783 unique company
symbols, because the graph retains older names.

### Event returns

Raw Massive-derived event returns exist on 13 source/relationship/target
paths:

- News `INFLUENCES` Company, Sector, Industry, and MarketIndex;
- Report `PRIMARY_FILER` Company;
- Report `REFERENCED_IN` Company;
- Report `INFLUENCES` Sector, Industry, and MarketIndex;
- Transcript `INFLUENCES` Company, Sector, Industry, and MarketIndex.

The largest path is News to Company with 348,549 relationships carrying at
least one return value. Its stored event span is 2021-01-01 through
2026-04-27. Company relationships can carry all 12 raw fields:

```text
hourly/session/daily x stock/sector/industry/macro
```

Sector, industry, and market-index relationships carry their matching three
benchmark fields.

The source-level counts with a populated hourly stock return are:

| Source | Relationships | Distinct company symbols |
|---|---:|---:|
| News | 345,103 | 784 |
| Reports | 41,895 | 786 |
| Transcripts | 9,373 | 763 |

### Redis return state

The live Redis database was inspected with read-only commands. It had 57,722
keys in total and 6,934 keys matching return or return-tracking patterns.

| Namespace | Matching keys |
|---|---:|
| `news:withoutreturns:*` | 181 |
| `reports:withoutreturns:*` | 70 |
| `transcripts:withoutreturns:*` | 6 |
| `tracking:meta:news:*` | 126 |
| `tracking:meta:reports:*` | 6,547 |
| `tracking:meta:transcripts:*` | 1 |

Pending return queues contained 295 news members, 178 report members, and 13
transcript members. Their timestamps cluster from 2026-04-16 through
2026-04-28. No current `withreturns` payload keys were found. This is
consistent with the graph's price and return data stopping around
2026-04-27/28, but it does not by itself prove that the changed Massive
entitlement caused the stop.

### Corporate actions and risk factors

| Stored item | Nodes | Symbols | Date span |
|---|---:|---:|---|
| Dividends | 4,556 | 433 | 2023-01-03 to 2026-04-27 declaration dates |
| Splits | 40 | 38 | 2023-01-04 to 2026-02-09 execution dates |
| Massive risk classifications | 39,821 | 644 | 2023-01-17 to 2026-04-13 filing dates |
| Massive risk taxonomy categories | 140 | n/a | n/a |

All 39,821 risk classifications are marked `source = "massive"` and have
supporting text and embeddings.

The raw read-only inventory is saved at
`results/neo4j_inventory.json`.

## LSE contract and coverage findings

### Plan limits confirmed from the authenticated API

| Limit | Value |
|---|---:|
| Calls per minute | 200 |
| Rows per synchronous request | 5,000 |
| Concurrent vault operations | 2 |
| Bulk exports per hour | 5 |
| Weekly data | 15 GiB |
| Monthly data | 50 GiB |
| Historical-month limit | unlimited (`-1`) |

### Current company universe

For the 783 current company symbols:

- 754 are in LSE's stock dataset;
- 29 are absent;
- company coverage is 96.3%.

The 29 absent current companies are:

```text
ALEX, AMED, AXL, BIGC, BPMC, CFLT, DNB, EXAS, FCPT, GMS, HOLX,
IAS, JAMF, LESL, MMC, MPW, MRUS, NVEE, PINC, PX, REVG, SAGE,
SEE, SKX, SPR, TSE, VNO, VRNT, YMAB
```

The live candle endpoint returned a 404 for a tested absent company, HOLX,
confirming that catalog absence is a real data absence in that case.

### Full price universe required by the graph

| Group | Required | LSE candle symbols | Coverage |
|---|---:|---:|---:|
| Company symbols stored in the graph | 796 | 754 | 94.72% |
| Sector ETFs | 11 | 2 | 18.18% |
| Industry ETFs | 52 | 2 | 3.85% |
| SPY | 1 | 1 | 100% |
| All distinct stored price symbols | 860 | 759 | 88.26% |

The covered sector ETFs are XLE and XLF. The covered industry ETFs are GDX
and SOXX.

There is no current company for which both its assigned sector ETF and its
assigned industry ETF are available from LSE. Therefore, zero of the 783
current companies can produce the complete four-leg return object from LSE
alone. This matters because the Redis completion check requires every stock,
sector, industry, and macro leaf to be populated.

The live API returned a 404 for XLK, confirming that at least one
catalog-missing benchmark is also truly unavailable from the candle endpoint.

For the current required set of 783 companies, 11 sector ETFs, 52 industry
ETFs, and SPY, LSE covers 759 of 847 symbols, or 89.61%. For the larger set
actually retained in the graph, it covers 759 of 860, or 88.26%.

### Stock history depth

The catalog reports a `first_tick` for all 754 covered current companies.
Among them:

- 583 report a first tick on or before the graph's 2023-01-03 start;
- 171 report a first tick only on 2026-04-27 through 2026-04-29.

The catalog date is not sufficient proof that every advertised historical day
is complete. It is a warning that a large part of the covered symbol list may
have only recent history, and it must be checked at value level before
backfilling.

### ETF history depth

LSE's ETF catalog contains only 25 symbols. Their recorded history begins on
2026-04-27 or 2026-04-28.

#### Are more ETFs hidden under another name?

No. A fresh check of LSE's public Databank catalog on 2026-07-19 confirmed
exactly 25 ETF price symbols:

```text
ARKK, BITO, DIA, EEM, ETHA, GDX, GLD, HYG, IBIT, IWM, QQQ, SLV, SMH,
SOXL, SOXS, SOXX, SPY, SQQQ, TLT, TQQQ, TSLL, VOO, VTI, XLE, XLF
```

LSE uses `etf` as the internal dataset name and displays it as `ETFs`. Its
official client accepts either `etf` or `etfs`. There is no separate `fund`
or `funds` price dataset.

The whole catalog was checked, not only the ETF filter:

- none of the 25 ETF price symbols is duplicated under `stocks` or `index`;
- `options` contains option history for the same 25 ETF underlyings, but
  options data cannot replace the ETFs' own prices;
- all 59 sector and industry ETFs that EventMarketDB needs but that are
  missing from LSE's ETF list were searched across every LSE category;
- none of those 59 symbols appeared under stocks, indices, options, or any
  other category.

Therefore the missing benchmark coverage is real, not a naming problem.
LSE's own [API coverage page](https://londonstrategicedge.com/free-market-data-api/)
also describes the 25 as “index and sector funds.”

Authenticated tests returned:

- AAPL daily rows for January 2023;
- no SPY daily rows for January 2023;
- no XLE daily rows for January 2023;
- SPY and XLE daily rows beginning 2026-04-27.

This does not cover the graph's 2023-01-03 onward benchmark history.

One SPY and XLE daily response also included a Saturday row with zero volume
and a flat price. The production graph only creates prices on exchange
trading days, so a candidate adapter would have to filter these rows with the
same exchange calendar.

### Candle fields

LSE candle rows currently contain:

```text
symbol, timestamp, open, high, low, close, volume
```

They do not contain VWAP or transaction count. LSE's own current changelog
states that stock and ETF candles are split-adjusted, matching Massive's
current setting.

The absence of VWAP and transaction count prevents an exact replacement of
the daily `HAS_PRICE` record shape.

### Intraday query behavior

The installed LSE client documentation says start/end can be ISO timestamps.
The live server rejected values such as an exact UTC timestamp and replied
that dates must use `YYYY-MM-DD`.

Date-only one-second and one-minute queries do work when the end date is later
than the start date. This reveals two practical issues:

1. A one-second day can exceed the 5,000-row page limit.
2. There is no documented row cursor or timestamp-level page boundary on the
   synchronous endpoint.

Ascending order can reach the beginning of a day and descending order can
reach the end, but an arbitrary time in the middle may be unreachable without
a bulk export. The plan permits only five exports per hour.

LSE's one-minute rows are small enough to retrieve a full U.S. extended-hours
day in one request. One-second and raw-tick comparisons therefore used bulk
exports.

### “Live” status, source, and usage rights

LSE's [public API page](https://londonstrategicedge.com/free-market-data-api/)
calls the WebSocket feed live, and its
[data page](https://londonstrategicedge.com/data/) says ticks arrive when the
market prints them. The authenticated WebSocket did accept the key and emit a
Sunday crypto tick. This proves authentication and a working live transport,
not the delay or completeness of U.S. stock data.

The official client maps a normal live message to:

```text
symbol, price, bid, ask, volume, timestamp, name, replay
```

For Massive compatibility, only `price` can be the candidate trade price.
Using bid, ask, or midpoint would change the production meaning. The live
message still has no exchange, sale condition, correction state, sequence, or
separate participant/SIP timestamp.

The public API page states that one free key streams 16 symbols at a time. That
is far below the 783-company universe if every symbol must be watched
continuously. Dynamic event-only subscriptions may reduce the requirement, but
their capacity during overlapping events and their exact server enforcement
have not been tested. Replay can cover at most the prior 24 hours and does not
replace deep event-history queries.

Its [Terms of Service](https://londonstrategicedge.com/terms-of-service) state
that market data may be delayed and should not be relied on for time-sensitive
decisions. The same terms prohibit redistribution, resale, commercial
exploitation, and unapproved automated extraction. The public
[WebSocket page](https://londonstrategicedge.com/websocket-documentation/) does
not identify the stock source, venue set, SIP/consolidated status, correction
policy, or measured delay.

The public pages also show inconsistent counts and limits. One page says 3,987
stocks, the authenticated catalog returned 3,979, and another marketing page
claims a much larger stock count. A public data page says ten databank
downloads per hour, while the authenticated key reported five vault exports
per hour. The key's own limit response was used for testing.

Before production use, written confirmation is needed for:

1. whether U.S. stock ticks are truly real time or delayed;
2. the actual upstream source and included exchanges/reporting facilities;
3. whether it is a consolidated trade feed or a partial venue/feed;
4. sale-condition, correction, cancellation, and late-trade handling;
5. internal production storage, derived-value use, and any redistribution
   rights;
6. service level, retention, and change-notice commitments.

Until those answers exist, bypassing the Massive 15-minute restriction is a
possibility advertised by LSE, not a proven production fact.

The Python client is MIT licensed. That license covers the client software; it
does not override the separate service terms governing the market data.

#### Remaining market-open test

The next U.S. stock session should be used for one final transport test. It
will not write to production. The isolated test should:

1. subscribe to AAPL and SPY, then test 16 and 17 simultaneous symbols to
   measure the stated subscription limit;
2. record both local receipt time and LSE's tick timestamp without storing the
   API key;
3. measure delay, missing intervals, duplicate messages, out-of-order
   messages, reconnect behavior, and 24-hour replay behavior;
4. compare price and volume with an authorized consolidated real-time
   reference;
5. repeat around 9:30 AM, 4:00 PM, and a normal liquid period.

This test can establish observed delay and transport quality. It cannot prove
the upstream venue set, SIP status, trade-condition policy, correction policy,
or commercial data rights. Those points require written answers from LSE.

### Raw tick and one-second candle behavior

LSE's raw stock export contains only:

```text
timestamp, symbol, price, volume
```

It does not contain sale condition, exchange, correction or cancellation
state, sequence number, participant timestamp, SIP timestamp, or reporting
facility. Those missing facts prevent an independent reconstruction of
Massive's trade-eligibility rules.

For AVGO on 2024-12-12, LSE exported 333,839 raw ticks and 25,330 one-second
candles. The comparison found:

- every one-second timestamp existed in both forms;
- open, high, low, and volume matched the raw ticks in all 25,330 seconds;
- 394 closes differed from a simple “last row by timestamp” rollup;
- 1,308 seconds had more than one trade tied at the final microsecond;
- in every second, LSE's candle close was one of the prices tied at that final
  timestamp.

This means LSE's one-second candle is a direct rollup of its raw tape for this
case. The raw export still lacks the sequence field needed to choose the final
trade when timestamps tie. More importantly, neither form supplies the
conditions needed to reproduce Massive's official qualifying-trade rules.

### AVGO session reconstruction

AVGO on 2024-12-12 is a useful boundary case because earnings caused a large
after-hours move.

| Source/rule | Open | High | Low | Close | Volume |
|---|---:|---:|---:|---:|---:|
| Massive grouped daily / graph | 180.93 | 182.00 | 175.99 | 180.66 | 46,958,170 |
| LSE raw daily candle | 182.86 | 209.90 | 175.97 | 207.47 | 28,366,860 |
| LSE minutes filtered to 9:30 AM–4:00 PM ET | 181.00 | 182.00 | 175.97 | 180.91 | 13,679,578 |

Filtering LSE to the regular session reduces the close gap from $26.81 to
$0.25, but it does not make the result exact. LSE's raw daily row exactly
matches a UTC-calendar-day rollup of its own raw trades in this case, which is
why it includes the after-hours earnings move.

The official Massive close of $180.66 appears in LSE's tape, but the export
does not identify it as a closing print. The LSE second beginning 4:00 PM ET
has open `180.94`, high `180.99`, low `180.66`, close `180.87`, and volume
`5,887,359`; Massive's corresponding one-minute row has open `180.66`, high
`181.14`, low `180.01`, close `181.04`, and volume `412,017`.

LSE's full-day volume is 60.4% of Massive grouped volume, and its raw tick
count is about 62.8% of Massive's transaction count. That proves materially
different coverage or counting. The exports do not expose enough provenance
to identify the missing venues or exact cause.

### Corporate-action field mapping

LSE dividends include all core facts needed by the current graph:

| Current field | LSE field |
|---|---|
| ticker | `symbol` |
| cash amount | `dividend_amount` |
| declaration date | `declaration_date` |
| ex-dividend date | `effective_date` |
| payment date | `payment_date` |
| record date | `record_date` |
| type, currency, frequency | same meaning, but values need normalization |

The live sample mixed coded and normalized values in the same fields, for
example `CD` versus `Regular`, and `4` versus `Quarterly`. A normalizer is
required.

LSE split rows contain symbol, effective date, split-from, and split-to, which
map directly to the current split node after renaming effective date to
execution date.

Read-only graph rows were compared with LSE for every covered symbol that had
an action in the graph: 36 split symbols and 418 dividend symbols, or 454
endpoint-symbol requests. No endpoint failed or hit the row limit.

#### Split result

- The graph contains 40 splits.
- Thirty-eight are on LSE-covered symbols; two are on missing symbols.
- All 38 covered splits matched symbol, execution date, split-from, and
  split-to exactly after normalizing comma-formatted numbers.

LSE can supply the split payload for covered symbols in this observed range.
It still cannot supply the two actions on symbols absent from its catalog.

#### Dividend result

Using the core facts ticker, declaration date, and cash amount:

| Measure | Count |
|---|---:|
| Graph rows on LSE-covered symbols | 4,413 |
| Exact core matches | 3,997 |
| Missing graph rows | 416 |
| Match rate | 90.57% |
| Extra LSE rows in the graph date range | 1,508 |

Among the 3,997 core matches, optional fields were also usually close:
currency matched 3,992 times, type 3,993, ex-date 3,982, frequency 3,957,
payment date 3,983, and record date 3,982 after normalization.

There is a more serious storage issue. Production identifies a Dividend node
by ticker, declaration date, and dividend type; cash amount is not part of the
ID. LSE produced 45 duplicate IDs and every one had conflicting payloads,
with 89 rows beyond the first record. For example, one declaration can list
several future quarterly payments. In the current graph model those rows
would collide and later values could overwrite earlier ones.

Under the production ID:

- 4,333 of 4,413 graph IDs appeared in LSE;
- 3,993 overlapping IDs had at least one exact cash amount;
- 3,940 had an exact full payload;
- 80 graph IDs were absent;
- LSE had 1,083 extra IDs.

Therefore dividends are not a drop-in replacement. They need an explicit
record-selection rule and still leave unmatched values. In addition, 143
graph dividends are on symbols missing from LSE.

## Historical value comparisons

All comparisons in this section ran in the isolated folder. Neo4j was read
only, API calls were GET requests, and no production object was updated.

### Direct comparison with real stored daily rows

The ten cached LSE histories were compared directly with their real Neo4j
`HAS_PRICE` rows from 2023-01-03 through 2026-04-27. This avoids the current
Massive key's two-year history limit and uses the exact grouped-daily values
that production stored.

First, the graph itself was checked: all 8,300 stored `daily_return` values
matched a fresh calculation from each symbol's consecutive XNYS closes. This
proves the documented formula against real production data, not a fixture.

LSE then had 7,476 overlapping symbol/date rows. It was missing 834 graph rows,
including 830 of 831 TPG dates. The accuracy result was:

| Field | Exact rows | Mean absolute difference | 95th percentile |
|---|---:|---:|---:|
| Open | 1,104 / 7,476 | $0.684 | $2.86 |
| High | 1,678 / 7,476 | $0.367 | $1.83 |
| Low | 1,679 / 7,476 | $0.417 | $2.23 |
| Close | 3,171 / 7,476 | $0.403 | $2.42 |
| Volume | 0 / 7,476 | 34.74% relative | 92.12% relative |

For daily returns:

- 7,466 were comparable;
- 2,288, or 30.6%, matched at two decimals;
- mean absolute error was 0.565 percentage points;
- 95th-percentile error was 2.29 percentage points;
- maximum error was 15.97 percentage points.

Results varied sharply by symbol. CNS had 787 of 830 exact returns, while AVGO
had 9 of 830 and ZYME had 98 of 829. This makes a broad “close enough” rule
unsafe: accuracy depends on symbol and period.

As a control, the stored graph rows were compared with freshly fetched Massive
custom daily bars over the currently authorized two-year range:

- all 4,440 closes and lows matched exactly;
- all 4,430 comparable daily returns matched exactly;
- 4,439 opens and 4,436 highs matched;
- 3,838 of 4,440 volumes matched.

This control is important. It shows that the graph really is a reliable
Massive reference for close-based daily returns. The few high/open changes and
the larger number of volume changes also confirm Massive's warning that daily
data can be revised or differ by daily process. ATR uses high and low, so its
direct current-Massive comparison remains the authoritative ATR test.

### Raw daily API comparison

Ten stock symbols were selected to include liquid, thin, high-price, low-price,
and history-depth cases. All ten completed and produced 3,993 common
exchange-session dates.

| Field | Exact rows | Mean absolute difference | 95th percentile |
|---|---:|---:|---:|
| Open | 421 / 3,993 | $0.849 | $3.54 |
| High | 874 / 3,993 | $0.492 | $2.54 |
| Low | 865 / 3,993 | $0.501 | $2.58 |
| Close | 1,694 / 3,993 | $0.424 | $2.33 |
| Volume | 0 / 3,993 | 29.51% relative | 61.41% relative |

For the exact production daily-return formula:

- 3,983 consecutive-date returns were comparable;
- 1,180, or 29.6%, matched after rounding to two decimals;
- mean absolute error was 0.574 percentage points;
- 95th-percentile error was 2.29 percentage points;
- maximum error was 15.97 percentage points.

LSE also returned 312 rows on dates outside the XNYS trading calendar. They
were excluded before comparison. The result proves that filtering raw LSE
daily candles to exchange dates is necessary but not sufficient.

### Stored event-return comparison

The current Massive key cannot fetch historical one-second bars, so the
Massive reference is the value already stored in Neo4j. For each event the
test:

1. imported the production market-window calculation read-only;
2. used the exact production start and end timestamps;
3. selected the newest LSE one-second candle whose bar start was at or before
   each timestamp;
4. applied the unchanged percentage formula and two-decimal rounding;
5. verified that both timestamps were inside the exported data.

One basis point here means 0.01 percentage points.

#### Hourly stock returns

| Sample | Comparable | Exact | Within 1 basis point | Within 5 basis points | Largest error |
|---|---:|---:|---:|---:|---:|
| AAPL, 2023-06-05 events | 82 | 51 | 76 | 81 | 0.13 points |
| TSLA, 2023-01-25 events | 34 | 6 | 14 | 24 | 0.53 points |
| AVGO, 2024-12-12 after-hours events | 4 | 1 | 1 | 2 | 0.09 points |
| **Combined** | **120** | **58** | **91** | **107** | **0.53 points** |

The combined mean absolute error was 0.0223 percentage points. Regular-market
results were much stronger: all 79 comparable AAPL and TSLA regular-market
returns were within one basis point, and 51 were exact.

The error was less stable outside regular hours. TSLA after-hours had the
largest miss, 0.53 percentage points. That fits the broader evidence that
trade coverage and official print handling differ most around thin or special
trading periods.

#### Session stock returns

| Sample | Comparable | Exact | Within 1 basis point | Within 5 basis points | Largest error |
|---|---:|---:|---:|---:|---:|
| AAPL, 2023-06-05 events | 82 | 5 | 71 | 82 | 0.05 points |
| TSLA, 2023-01-25 pre/regular events | 13 | 0 | 2 | 7 | 0.10 points |
| **Combined** | **95** | **5** | **73** | **89** | **0.10 points** |

The combined mean absolute error was 0.0165 percentage points. The lower exact
count is expected because many events share a session endpoint but use
different start seconds: very small price differences can change the final
two-decimal return.

#### Daily stock-return spot check

Three AAPL event rows covered one unique close-to-next-close window. Every row
was within one basis point but none was exact: LSE gave `-0.24%` and the
stored Massive value was `-0.23%`. The earlier close-to-close window could not
be compared because its prior Friday start was outside the two exported days.

#### Meaning of these event tests

The regular-hours result is promising for a **partial stock-only use**. It is
not enough for replacement:

- many values are close but not exact;
- after-hours errors are larger;
- only a small number of symbols and days could be exported under the hourly
  limit;
- sale conditions and sequence fields remain unavailable;
- nearly all benchmark ETFs are missing, so sector, industry, SPY-relative
  complete objects cannot be generated for the universe.

Relative-return arithmetic itself needs no new market field; it is simple
subtraction. It still fails when the benchmark leg is absent or different.

### Macro snapshot comparison

The exact production formulas were run at 2026-07-17 4:30 PM ET, after the
close.

LSE covered only four of the nine Massive daily indicator ETFs: TLT, HYG, IWM,
and GLD. It was missing VIXY, SHY, RSP, USO, and UUP.

For SPY, Massive supplied 920 minute rows and 385 daily rows beginning
2025-01-02. LSE supplied 948 UTC-day minute rows, 947 after the project's
extended-hours time filter, and only 51 daily exchange-session rows beginning
2026-04-27.

Three intraday fields matched exactly after rounding:

| SPY field | Massive | LSE |
|---|---:|---:|
| Level at point in time | 742.81 | 742.81 |
| Open to point in time | -0.40% | -0.40% |
| Last 60 minutes | -0.05% | -0.05% |

The daily-derived fields did not:

| SPY field | Massive | LSE |
|---|---:|---:|
| Overnight gap | -0.65% | -0.44% |
| Today | -0.99% | -0.88% |
| Yesterday | -0.54% | -0.74% |
| 5-day | -1.54% | -1.64% |
| 20-day | 0.31% | 2.72% |
| 5-day average volume | 46,412,462 | 39,354,778 |
| 20-day average volume | 52,453,885 | 50,957,021 |
| 50-day average price | 744.38 | 740.54 |
| 200-day average price | 696.69 | unavailable |

The LSE helper calculated a value labelled year-to-date, but it was actually
the return from 2026-04-27 because earlier ETF history was absent. That value
must be rejected; it is not a valid year-to-date result.

The four supported indicator ETFs were close on some current levels and
one-day returns, but all lacked the year's start and 200 settled sessions.
Their apparent year-to-date differences ranged from 0.27 to 12.50 percentage
points. LSE therefore cannot build the full macro packet from its current ETF
history.

### ATR comparison

The exact 14-day production ATR formula was applied to all common dates in the
ten completed daily-symbol caches, using the current Massive custom-daily
endpoint that the ATR tool itself calls.

- 3,866 rolling windows were comparable;
- only 19, or 0.49%, matched after rounding to two decimals;
- mean absolute difference was 0.759 price units;
- 95th-percentile difference was 2.709 price units;
- mean relative difference was 27.45%.

Final-window examples:

| Symbol | Massive ATR | LSE ATR |
|---|---:|---:|
| A | 3.4750 | 3.7443 |
| AVGO | 12.5418 | 14.3029 |
| CNS | 1.9007 | 1.8893 |
| EPD | 0.6864 | 0.8221 |
| HP | 1.4020 | 1.6650 |
| LSTR | 5.1250 | 5.2407 |
| O | 0.9304 | 1.0943 |
| RGEN | 6.8839 | 7.4721 |
| ZYME | 1.0613 | 1.8150 |

Raw LSE daily bars are not compatible with the current Massive-based ATR.

For extra depth, the same ATR formula was also run against the real stored
grouped-daily graph rows back to 2023. Across 7,349 rolling windows, only 25
matched at two decimals. This is supporting evidence rather than the primary
ATR result because a few stored highs differ from a later custom-daily
refetch.

## Replacement decision by Massive use

This is the evidence-based decision, not a production migration plan.

| Massive use | LSE status | Reason |
|---|---|---|
| Stock one-second event return, regular hours | Promising partial match | All 79 tested regular-hour returns were within 1 basis point, but only 51 were exact and exact trade rules are unavailable |
| Stock one-second event return, extended hours | Not exact | Larger observed errors and different close/print behavior |
| Sector return leg | Missing for most symbols | Only 2 of 11 sector ETFs covered |
| Industry return leg | Missing for most symbols | Only 2 of 52 industry ETFs covered |
| Complete four-leg return object | Unavailable | Zero current companies have both required LSE benchmark ETFs |
| Relative returns | Unavailable as a complete feature | Arithmetic is simple, but required benchmark inputs are absent |
| Grouped daily price graph | Not compatible | Daily OHLCV differs; VWAP and transaction count absent |
| Daily stock return | Not exact | 30.6% exact across 7,466 direct graph comparisons; live API check was 29.6% |
| ATR | Not compatible | 19 of 3,866 windows exact at two decimals |
| SPY intraday macro fields | Partial match | Three tested fields exact at one point in time |
| Full macro snapshot | Unavailable | Five indicator ETFs absent; ETF history too short; daily fields differ |
| Splits | Compatible for covered symbols | 38 of 38 covered graph records matched |
| Dividends | Not drop-in | 90.57% core match plus missing, extra, and conflicting duplicate records |
| Active common-stock validation | Not proven equivalent | LSE catalog does not expose the same Massive ticker-status contract |
| Health probe | Can be redesigned, not matched | LSE can be probed, but the current check specifically tests Massive one-second authorization |
| Related companies | No live requirement found | Wrapper method has no caller |
| SEC risk factors | Missing | No LSE equivalent found |
| Historical graph backfill | Unavailable as one source | Missing symbols, missing ETFs, short ETF history, and missing stored fields |
| Live no-delay operation | Not yet accepted | Stock WebSocket authentication worked; a U.S. stock tick during market hours is not yet proven |

## Massive file and maintenance inventory

### Live or direct production paths

| File/path | Massive role |
|---|---|
| `eventtrader/keys.py` | Loads the Massive/Polygon key from `POLYGON_API_KEY` |
| `config/DataManagerCentral.py` | Sets and passes the 17-minute return delay |
| `scripts/run_event_trader.py` | Main launcher; blocks startup if the Massive one-second health probe fails |
| `eventReturns/polygonClass.py` | Ticker validation, one-second event prices, returns, grouped daily data, corporate actions, related companies |
| `eventReturns/EventReturnsManager.py` | Builds schedules and the stock/sector/industry/SPY return object |
| `eventReturns/ReturnsProcessor.py` | Waits for eligibility, computes values, and requires every return leaf |
| `redisDB/BaseProcessor.py` and source processors | Move pending news, report, and transcript payloads through return calculation |
| `neograph/Neo4jInitializer.py` | Loads grouped daily prices, dividends, and splits into the graph |
| `neograph/EventTraderNodes.py` | Defines Dividend and Split fields and their database IDs |
| `scripts/earnings/builders/adapters.py` | Routes historical macro builds to Massive by default; live builds default to Yahoo |
| `scripts/earnings/builders/macro_snapshot.py` | Direct Massive minute/daily macro calls and derived fields in Massive mode |
| `scripts/atr_compare_sources.py` | Direct Massive daily bars for ATR comparison |
| `utils/polygon_health.py` | AAPL one-second authorization/health probe |
| `scripts/ingest_massive_risk_factors.py` | Separate Massive taxonomy and SEC filing risk-factor endpoints |
| `scripts/driver_strategy_scan.py` | Reads Massive-derived risk classifications from Neo4j; it makes no Massive request |

`eventReturns/polygon_manager.py` appears unused: no caller was found.
`polygonClass.py` also contains a related-companies wrapper with no caller.
Other search hits in documentation, HTML diagrams, test fixtures, builder
tests, and `inter_quarter_context.py` are labels, examples, mocks, or timestamp
format notes; they do not make a market-data request.

### Repair and diagnostic scripts

These scripts are not all safe or current merely because they exist:

| Script group | Finding |
|---|---|
| `repair_partial_price_dates.py` | Uses the correct grouped daily method; can write graph rows unless `--dry-run` is used |
| `fix_null_returns_exact.py` | Uses the live return method and correct 1,020-second delay; writes graph properties unless dry-run |
| `fix_specific_relationship.py` | Uses the live method and 1,020-second delay; directly writes one graph relationship |
| `process_valid_tickers.py` | Validates with Massive, then runs the graph fixer with `dry_run=False` |
| `count_fixable_returns.py`, `find_valid_ticker_nulls.py`, `list_unfixable_tickers.py`, `validate_null_return_tickers.py` | Read graph data and call Massive ticker validation |
| `compare_with_production.py`, `verify_exact_methodology.py` | Diagnostic/read-oriented comparisons |
| `verify_returns_calculation.py` | Recomputes values but uses the stale 900-second delay |
| `reprocess_event_returns.py`, `recalculate_returns_simple.py` | Redis reprocessing tools that use the stale 900-second delay and can change Redis state |
| `fix_null_stock_returns.py` | Can change Redis and requeue events into the live Massive path; its “API check” only looks for an old stored return |
| `fix_null_returns_direct.py` | Broken: imports nonexistent `EventReturnsCalculator` and calls `EventReturnsManager` without its required arguments |
| `fix_missing_industry_returns.py` | Broken: imports `Polygon` but instantiates undefined `EventReturnsCalculator` |
| `fix_missing_sector_returns.py` | Broken: calls `get_daily_prices` and `get_price_at_time`, which the current wrapper does not provide |

No repair or diagnostic script was run by this audit.

## Official Massive behavior used in this audit

The most important vendor rules were checked against Massive's own material:

- [Custom aggregate bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- [Aggregate range snapping and limits](https://massive.com/blog/aggs-api-updates)
- [Aggregate bar delays](https://massive.com/blog/aggregate-bar-delays)
- [Late aggregate revisions](https://massive.com/knowledge-base/article/why-am-i-receiving-a-late-aggregate-bar-through-massives-websockets)
- [Stock trade condition codes](https://massive.com/docs/rest/stocks/market-operations/condition-codes)
- [Which trades update OHLCV](https://massive.com/knowledge-base/article/how-does-massive-create-the-open-high-low-close-volume-aggregate-bars)
- [Why second, minute, hour, and daily bars differ](https://massive.com/knowledge-base/article/how-does-massive-create-aggregate-bars)
- [Stock trade endpoint](https://massive.com/docs/rest/stocks/trades-quotes/trades)
- [Daily ticker summary](https://massive.com/docs/rest/stocks/aggregates/daily-ticker-summary)
- [Split-adjusted volume](https://massive.com/knowledge-base/article/why-does-volume-return-as-a-decimal-value-from-the-aggregates-endpoint)
- [Why vendor data can differ](https://massive.com/knowledge-base/article/why-is-massives-market-data-different-from-other-providers)

The replacement test follows the project's actual calls first. Vendor
documentation is used to explain behavior that the code depends on; it is not
used as a substitute for value-level comparison.

## Evidence files

- `results/neo4j_inventory.json` — real read-only database counts.
- `results/redis_inventory.json` — read-only return queue and tracking-key
  inventory.
- `results/lse_contract_probe.json` — first live contract probe.
- `results/lse_contract_probe_v2.json` — date-only and ETF-depth checks.
- `results/lse_contract_probe_v3.json` — valid intraday range checks.
- `results/massive_contract_probe.json` — current Massive entitlement, grouped
  daily, open/close, minute, and one-second response checks.
- `results/daily_api_comparison_sample10_complete.json` and
  `results/daily_api_pairs_sample10_complete.csv.gz` — daily OHLCV and return
  evidence for all ten symbols.
- `results/graph_daily_comparison_sample10.json` — direct real graph versus
  LSE comparison, stored-return validation, current Massive control, and
  full-period ATR evidence.
- `results/lse_session_reconstruction_avgo_2024-12-12.json` — raw daily versus
  exchange-session reconstruction.
- `results/lse_tick_analysis_avgo_2024-12-12.json` — raw-tape rollup and
  boundary analysis.
- `results/lse_tick_vs_one_second_avgo_2024-12-12.json` — exact tick-to-second
  candle comparison and tied-close analysis.
- `results/event_return_candidates.json` — read-only selection of stored graph
  events suitable for one-second testing.
- `results/event_hourly_lse_seconds_*.json`,
  `results/event_session_lse_seconds_*.json`, and
  `results/event_daily_lse_seconds_*.json` — stored Massive return versus LSE
  one-second results.
- `results/corporate_actions_comparison.json` — all covered graph splits and
  dividends versus LSE.
- `results/macro_inputs_comparison_2026-07-17.json` — exact macro-formula
  comparison.
- `results/atr14_cached_comparison_complete.json` — 3,866 rolling ATR
  comparisons.
- `inventory/lse_etf_catalog_2026-07-19.json` — complete current LSE ETF list
  and the cross-category hidden-ETF check.
- `tests/` — 28 isolated tests covering price selection, fallback windows,
  production semantics, session reconstruction, timezones, tied timestamps,
  corporate-action normalization, and macro calculations.
- `raw/lse-data-main/` — isolated snapshot of the official open-source LSE
  client used to verify endpoint paths and stated behavior.
- `raw/lse_tick_exports/` and `raw/lse_one_second_exports/` — isolated AVGO
  raw-tick and one-second exports. Processed AAPL and TSLA second-candle
  comparisons are saved under `results/`.

No production source file or production database was changed. This research
folder is the audit's only addition to EventMarketDB.
