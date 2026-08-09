# Massive Replacement Data-Source Audit

Status: LSE audit and first IBKR live/historical comparison complete
Started: 2026-07-19
Repository inspected read-only: `/home/faisal/EventMarketDB`

## Goal

Determine, with historical and live evidence, whether London Strategic Edge
or the project's existing Interactive Brokers connection can replace the
current 15-minute delayed Massive subscription without changing
EventMarketDB's results or required behavior.

The test is stricter than API availability. The candidate source must supply every input and reproduce every output currently derived from Massive, including:

- hourly returns;
- daily returns;
- market-session returns;
- relative returns;
- any other direct or indirect calculation found during the code and database audit;
- Massive-specific aggregate behavior on which the code relies.

## Overall decision after IBKR testing

For future live U.S. stock-event prices, use IBKR as the main source. LSE is
not required in the bot's core price path. It can remain an optional source
for a separate macro display or a backup comparison.

IBKR is a much closer match to Massive than LSE:

| Requirement | IBKR evidence | Result |
|---|---|---|
| Configured stock identities | 751 of 783 tickers qualified; `PINC` is a reused ticker for the wrong security | 750 intended identities resolved; 32 need cleanup or further identity review |
| LSE's current-stock gaps | `FCPT`, `LESL`, and `VNO` had live IBKR bid/ask prices | All three clearly current gaps filled |
| 63 production benchmarks | 61 qualified with live bid/ask prices | All still-valid benchmark symbols covered |
| Detailed live trades | 13 trades across five symbols in ten pre-market seconds | Passed |
| Initial event returns | 16 of 20 exact; 18 of 20 within 0.01 percentage points | Strong except thin 4:00–5:00 AM case |
| Daily returns | 624 of 624 exact at two decimals | Passed in this sample |
| 14-day ATR | 324 of 416 exact at two decimals | Close, but not exact |

The two unresolved benchmark symbols are not normal source-coverage misses:

- `COMM` is not a publishing ETF. It is an invalid production mapping that
  points to the former CommScope stock ticker.
- `EATZ` was a real restaurant ETF, but its last trading day was 2026-04-30
  and it was liquidated in May 2026. A current replacement benchmark must be
  chosen separately.

The five event examples covered pre-market, regular hours, normal
after-hours, late after-hours, and a closed-market 4:00–5:00 AM window. They
contained the stock, sector ETF, industry ETF, and `SPY`, for 20 comparison
legs in total:

- 16 matched the stored Massive return exactly after rounding to two
  decimals;
- 18 differed by no more than 0.01 percentage points;
- late after-hours matched all four legs exactly, including the fallback to
  the last available 7:59:59 PM trade when the requested end was after
  trading stopped;
- the thin 4:00–5:00 AM example differed by 0.02 percentage points for `IHI`
  and 0.28 for `ABT`.

The daily pilot requested 20 representative stocks. Sixteen had matching
stored graph dates, producing 640 common dates and 624 daily returns. Every
daily return matched at two decimals. Of 2,560 open, high, low, and close
fields, 2,260 matched at two decimals. Of 416 rolling ATR windows, 324
matched at two decimals; the average absolute difference was 0.00237 price
units and the maximum was 0.02071.

### Live connection and limits

The current EventMarketDB connection uses the TWS/IB Gateway API. It is a
persistent TCP socket, not a standard WebSocket, but IBKR pushes new prices
and trades through it continuously. This is already installed and was the
path tested here.

IBKR also offers a Client Portal WebSocket. It is not currently used by this
project and is not needed merely to receive streaming data. Current IBKR
documentation says Web API market-data subscriptions must be renewed every
ten minutes.

The tested live connection returned market-data type 1, meaning live rather
than delayed, for all qualifying sample securities. The detailed trade test
returned exact time, price, size, exchange, special conditions, and IBKR
trade flags. It proves top-of-book prices and detailed trades; it does not
prove full order-by-order market depth.

Operational limits prevent a simple whole-universe stream:

- the default allowance is 100 simultaneous market-data lines;
- at 100 lines, five tick-by-tick streams can run at once;
- one event's stock, sector ETF, industry ETF, and `SPY` require four, so one
  complete event fits;
- rapid bars of 30 seconds or less are subject to IBKR pacing limits,
  including no more than 60 requests in ten minutes;
- one-second historical bars are available for only about six months;
- historical data is unavailable for securities that no longer trade.

The practical design is to keep a small live IBKR stream for active event
symbols and their three benchmarks, save those updates locally, and calculate
returns from the saved stream. Old stored Massive data remains the historical
reference. LSE is optional and should not be a required dependency.

Official IBKR references:

- [IBKR API transport choices](https://ibkrcampus.com/api)
- [TWS API TCP socket and historical-data rules](https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/)
- [Market-data subscriptions and line limits](https://ibkrcampus.com/campus/ibkr-api-page/market-data-subscriptions/)
- [Client Portal WebSocket](https://ibkrcampus.com/campus/ibkr-api-page/cpapi-v1/)

### Safety

All IBKR connections used separate client IDs, read-only mode, and no account
or order startup requests. Every live subscription was cancelled and every
test connection was closed. No production IBKR code or configuration,
subscription, order, Kubernetes object, Redis record, or Neo4j record was
changed. One historical test reached IBKR's temporary request-speed limit;
that changed no persistent setting or code.

## LSE-only decision

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
- LSE's feed source, completeness, contractual delay guarantee, market
  rights, and commercial-use rights are not clear enough for production use.

The 2026-07-20 pre-market test proved that current U.S. stock data flows
through both interfaces in that sample. A regular-session load test can still
measure delay and gaps under heavier trading. Neither test can remove the
historical, coverage, field, or legal blockers above.

There is now a second, narrower finding: exact LSE ETFs plus baskets of
official fund holdings can closely reproduce regular-market daily closes for
part of the 63-benchmark set. Nine baskets passed the normal 80%
constituent-data rule in both the long history and recent overlap. Another 23
passed in both periods only when constituent-weight and/or target-date
coverage was relaxed. This could support a hybrid regular-close source, but
it is not proof of an event-time, pre-market, or after-hours replacement.

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
- On Monday at 6:13 AM ET, REST returned current-minute bars for four U.S.
  stocks and the WebSocket delivered 15 current NVDA ticks in 60 seconds.

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

## Sector and industry substitute results

### All 63 production benchmarks

Every required benchmark now has a final evidence row:

| Result | Benchmarks |
|---|---:|
| Exact LSE ETF for recent/live use | 4 |
| Basket strong under the normal 80% rule in both periods | 9 |
| Basket strong in both periods only under relaxed coverage | 23 |
| Partial or context-only basket evidence | 21 |
| No supported replacement | 5 |
| Invalid existing production mapping: `COMM` | 1 |

The nine normal-rule basket candidates are `IAI`, `ITB`, `IYT`, `VCR`,
`VDC`, `XLC`, `XLK`, `XLP`, and `XLY`. The four exact recent ETFs are `GDX`,
`SOXX`, `XLE`, and `XLF`.

None of the 63 rows proves a complete Massive replacement. The basket table
tests regular U.S. closes. Real event-window testing was much weaker before
the open and after the close, and the exact ETF tests used minute candles
rather than Massive-equivalent one-second official bars.

The full table and every numerical source are in:

- `docs/ALL63_REPLACEMENT_MATRIX.md`
- `results/all63_replacement_matrix_2026-07-19.json`
- `inventory/all63_replacement_matrix_2026-07-19.csv`
- `scripts/build_all63_replacement_matrix.py`

### Automatic past and future split handling

No split symbol, date, or ratio is hardcoded. Before calculating constituent
returns, the isolated loader requests the complete LSE `stock_splits` table
for all symbols in the requested period.

The first 2023-01-03 through 2026-07-17 request returned exactly 5,000 rows
and stopped at 2024-04-10, proving it was capped. The loader now detects that
condition and divides the period automatically. It produced three complete
ranges containing 3,720, 3,214, and 4,254 rows: 11,188 split rows for 8,953
symbols in total.

For each symbol and effective date, the candidate factor is
`split_to / split_from`. It is applied only when it makes the close-to-close
jump smaller. This corrects a raw unadjusted split while avoiding a second
adjustment when an older LSE candle is already adjusted.

The two large-return/date matches in the tested data were:

- `DD`, 1-for-3 reverse split on 2026-06-24. Its raw LSE close return was
  +195.16%. Correcting it raised the recent `XLB` basket to 0.9976
  correlation, 0.9979 beta, and 0.065 percentage-point average error. It also
  materially improved `VAW`.
- `SEM`, LSE ratio `125 -> 232` on 2024-11-26. The same general rule corrects
  its raw discontinuity. In the older large-move sample, 17 other split
  records were already adjusted by LSE and were left unchanged.

Future dates use the same code. If `--end` is omitted, the loader uses today's
date, so a daily or startup refresh will discover newly effective splits
without a code change. No such job has been enabled in production.

Evidence:

- `results/lse_split_adjustment_summary_2026-07-19.json`
- `results/lse_stock_splits_complete_2023-01-03_to_2026-07-17.json`
- `raw/reference_periods/stock_splits/`
- `scripts/audit_lse_split_adjustments.py`
- `tests/test_audit_lse_split_adjustments.py`
- `tests/test_run_proxy_pilot.py`

### Initial four-fund pilot

The first four benchmark pilots now pass the strict numerical screen over
almost the full production history from 2023-01-03 through 2026-04-27.

Method:

1. Use each fund's official quarterly SEC N-PORT holdings, not today's
   holdings applied to old years.
2. Select the top 20 holdings for that quarter.
3. Calculate each stock's return from the LSE hourly bar ending at the
   official 4:00 p.m. New York close.
4. Require prices for at least 80% of the selected top-20 weight on a day.
5. Renormalize the available selected weight and compare the result with the
   stored Massive-derived ETF return.

| Benchmark | Return days | Correlation | Beta | Average error | Tracking error | Same direction | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| IGV | 829 | 0.9850 | 1.0115 | 0.211 pp | 4.39 pp/year | 94.2% | strong |
| SOXX | 829 | 0.9970 | 1.0206 | 0.137 pp | 2.84 pp/year | 96.5% | strong |
| XLE | 829 | 0.9918 | 0.9845 | 0.115 pp | 2.80 pp/year | 95.7% | strong |
| XLK | 830 | 0.9927 | 1.0117 | 0.129 pp | 2.86 pp/year | 95.3% | strong |

The held-out 2025–2026 period also passed for all four funds. This is strong
evidence that an official-holdings basket is a viable substitute method, not
just a fit to one old period.

Important limits:

- “80% available” means 80% of the selected top-20 weight, not 80% of the
  entire fund. The top 20 captured 74.2%–81.0% of IGV, 89.9%–91.5% of SOXX,
  96.4%–98.1% of XLE, and 77.5%–84.2% of XLK across the tested quarters.
- Several valid stock symbols have little or no old LSE candle history.
  Lowering the selected-weight requirement from 90% to 80% retained almost
  every day and still passed the strict error screen.
- A bulk LSE export did not recover the missing history: DDOG's catalog says
  its raw span begins in 2019, but a 2023–2026 hourly export contained only
  11 bars on 2026-04-27, and a raw-tick export for 2025-01-03 contained zero
  rows. Catalog “coverage” therefore must not be treated as continuous
  historical coverage.
- N-PORT holdings are filed after their report date. Using report-date
  holdings is valid for retrospective reconstruction but would be
  look-ahead information in a live historical simulation. A live replacement
  should use issuer holdings available at that time.
- Daily price drift between quarterly snapshots was tested. It helped XLK
  slightly, was neutral for XLE, and made IGV and SOXX slightly worse.
  Fixed quarter-end weights are therefore the simpler current winner.
- The direct LSE `SOX/USD` series remains the best historical SOXX substitute:
  784 days, 0.9956 correlation, 1.007 beta, and 0.130 percentage-point average
  error. It is not safe for live use now: its latest catalog tick was
  2026-06-30, while other U.S. market series were current through 2026-07-17.
- The exact LSE `SOXX` and `XLE` ETF feeds were current through the latest
  completed U.S. session on 2026-07-17. Exact ETFs should be preferred over a
  substitute whenever they are present and fresh.

### Official fund identities and holdings

The 63 production benchmark labels were checked against the SEC's official
mutual-fund ticker file before any substitute was built:

- 60 labels map uniquely to a current SEC fund series and share class;
- `HACK` and `GAMR` are real funds, but both moved to new SEC registrations
  in 2023, so their old and new registrations must be joined;
- `COMM` is not an ETF. It is a former CommScope stock ticker and the
  production NYT-to-`COMM` assignment is invalid.
- `EATZ` was a valid restaurant ETF, but it is no longer a live benchmark.
  Its [official SEC liquidation notice](https://www.sec.gov/Archives/edgar/data/1408970/000182912626003345/advisorshares-eatz_497.htm)
  set April 30, 2026 as its last trading day and May 7, 2026 as its expected
  liquidation date. Massive consequently returned only three daily bars in
  the 2026-04-28 through 2026-07-17 control period.

Official quarterly SEC N-PORT holdings were downloaded for all 60 directly
mapped funds and for both registrations of `HACK` and `GAMR`. The requested
2022-Q4 through 2026-Q1 snapshots completed with no filing-download errors.
After correcting the quarter search to include October, November, and
December report dates, 59 funds have all 14 requested snapshots and `INDS`
has 13.
Each saved holding keeps the SEC fund identity, report date, security
identity, value, weight, currency, and source filing.

This solves fund identity and historical holdings provenance. It does not
guarantee that LSE carries each holding or its old prices.

`EATZ` now requires a production benchmark decision independent of the data
source. Fourteen current production companies use it. `PEJ` was the closest
existing production ETF tested as a direct replacement, but its 831-day
correlation with `EATZ` was only 0.7947 and its average return difference was
0.611 percentage points, so it is not an exact substitute. A maintained
restaurant-stock basket is the more faithful research candidate; changing
the production mapping is outside this isolated audit.

### All 11 broad sectors

`XLE` and `XLF` exist exactly on LSE for recent/live use. The other nine were
rebuilt from up to 50 official holdings. All nine were numerically strong
over the long history under the best tested coverage level:

| Sector | Selected-weight floor | Return days | Correlation | Beta | Average error |
|---|---:|---:|---:|---:|---:|
| XLB | 65% | 829 | 0.9905 | 1.0073 | 0.106 pp |
| XLC | 80% | 829 | 0.9896 | 0.9963 | 0.114 pp |
| XLI | 75% | 829 | 0.9929 | 0.9887 | 0.091 pp |
| XLK | 50% | 830 | 0.9980 | 1.0137 | 0.061 pp |
| XLP | 50% | 830 | 0.9829 | 0.9949 | 0.090 pp |
| XLRE | 50% | 830 | 0.9891 | 0.9897 | 0.106 pp |
| XLU | 75% | 829 | 0.9927 | 1.0125 | 0.074 pp |
| XLV | 50% | 830 | 0.9924 | 1.0104 | 0.077 pp |
| XLY | 50% | 830 | 0.9960 | 1.0267 | 0.096 pp |

The coverage column is crucial. Only `XLC`, `XLK`, `XLP`, and `XLY` passed
the normal rule in both the long and recent periods. The other five needed
lower selected weight and/or the outage-adjusted recent date rule, so they
remain diagnostic candidates rather than production-ready replacements.

In the recent 2026-04-28 through 2026-07-17 test, all nine had strong
numerical matches when the feed-wide outages were allowed. Correlations were
0.9841–0.9983 and average errors were 0.048–0.230 percentage points. `XLB`
was corrected using DuPont's LSE split row and reached 0.9976 correlation,
0.9979 beta, and 0.065 percentage-point average error. A live design still
needs a daily completeness check and a fallback source.

### Long archive versus current live coverage

The long basket comparison runs from 2023-01-03 through 2026-04-27. The LSE
catalog shows that its current live collection began on 2026-04-27 for many
U.S. stocks. This creates two different questions:

- **Old archive:** did LSE preserve enough hourly candles to reproduce the
  last three years?
- **Current replacement:** does LSE carry enough holdings from 2026-04-28
  onward to build the benchmark now?

These must not be combined. For example, valid catalog symbols such as
`COIN`, `JEF`, `MKTX`, `NDAQ`, `RJF`, and `TSCO` returned only the 11 hourly
bars from 2026-04-27 in the long request. That proves the older archive is
missing; it does not prove those stocks are absent from the current live
feed.

The corrected top-50 map for the 40 deeper industry tests contains 1,297
unique stock symbols. Of those, 1,277 (98.46%) are in LSE's current stock
catalog. The 20 absent symbols are retained as explicit gaps rather than
silently replaced. Per-fund weight coverage still matters more than this
simple symbol count.

The remaining holding names were also compared with every LSE stock name.
Simple fuzzy matching was unsafe: its four nominally high-confidence results
were false look-alikes such as Neoen versus Neogen and Triton versus Titan.
No fuzzy suggestion was applied. A stricter OpenFIGI check did safely recover
the two Liberty Global share classes `LBTYA` and `LBTYK` from
currency-suffixed identifier records. The final top-50 map now resolves
1,368 of 1,848 historical holding identities, or 88.59% of their combined
selected weight; 480 remain explicit, mostly foreign-heavy gaps.

The audit completed a separate 2026-04-28 through 2026-07-17 comparison for
every industry fund that did not pass the strict long-history test. It uses
fresh Massive daily controls, the corrected SEC holdings, and LSE candles
only from the actual live-overlap period.

An archive-only sensitivity test confirms that missing old candles, rather
than a bad basket formula, are the main problem for many funds. Of the 40
deeper industry tests:

| Required available selected weight | Strong | Context only | Reject |
|---:|---:|---:|---:|
| Normal decision rule: at least 80% | 4 | 0 | 36 |
| Diagnostic sensitivity: as low as 50% | 18 | 13 | 9 |

The 18 strong low-coverage results were `FCG`, `FDN`, `FTXR`, `IHF`, `IHI`,
`IYJ`, `IYR`, `KIE`, `OIH`, `PAVE`, `PHO`, `SCHH`, `VAW`, `VCR`, `VDC`,
`VOX`, `XHB`, and `XOP`. The nine rejects were `CARZ`, `CRAK`, `GDX`, `INDS`,
`MOO`, `REM`, `SLX`, `SRET`, and `TAN`.

This sensitivity is diagnostic only. A close match made from 50% of selected
holdings is evidence that the construction method works; it is not enough to
approve a production replacement. The current-period test keeps the normal
80% rule.

The completed current-period test is materially better than the old archive,
but it also proves that live completeness needs a fallback:

| 40 deeper industry funds, 2026-04-28 to 2026-07-17 | Strong | Context only | Reject |
|---|---:|---:|---:|
| Normal rule: at least 80% selected weight and 80% of target days | 8 | 4 | 28 |
| Diagnostic: selected weight as low as 50% and 75% of target days | 20 | 14 | 6 |

The relaxed diagnostic recovered 12 additional strong results and 10
additional context results. Eight funds had no day reaching 80%
selected-weight coverage: `CARZ`, `CRAK`, `INDS`, `MOO`, `REM`, `SLX`,
`SRET`, and `TAN`. `EATZ` is separately unusable because it liquidated.

The eight normal-rule strong results were `FTXR`, `OIH`, `VCR`, `VDC`, `VOX`,
`XHB`, `XME`, and `XOP`. Their average return differences ranged from 0.076
to 0.206 percentage points. The normal-rule context results were `AMLP`,
`FDN`, `IBB`, and `XPH`. Automatic split handling moved `VAW` from context
to strong in the relaxed-coverage diagnostic.

Close-time availability across all 1,297 queried stocks explains much of the
difference:

- 819,518 recent hourly rows were downloaded with zero request errors;
- the median symbol had an exact U.S. close on 50 of 56 sessions, producing
  only 45 consecutive-session return dates;
- `2026-05-14`, `2026-06-17`, and `2026-06-18` had zero exact U.S. close bars
  across all 1,297 symbols;
- `2026-05-15` had only 96 symbols with a close;
- `2026-06-11` through `2026-06-16` also had unusually broad partial gaps;
- 40 symbols had no U.S.-close candle at all. This group includes both absent
  or delisted U.S. names and foreign listings whose local market closes before
  the U.S. ETF.

Foreign listings expose a method limit, not merely a missing-data bug. A
U.S.-listed global ETF can continue trading after its Japanese, Korean,
Australian, or European holdings have closed. A holdings basket cannot
reproduce that U.S. intraday move from stale local shares. Daily local-close
reconstruction would also need correct local exchange calendars and currency
conversion. Global funds such as `CRAK`, `MOO`, `SRET`, and `TAN` therefore
remain poor basket-only replacement candidates.

### HACK and GAMR registration transitions

The old and new SEC registrations for `HACK` and `GAMR` were joined before
testing; using only the current registration would have lost their earlier
holdings.

- `HACK` is promising. With at least 75% of its selected top-20 weight, the
  long test had 804 days, 0.9845 correlation, 1.0032 beta, and 0.180
  percentage-point average error: a strong numerical result. At the normal
  80% weight rule, it remained numerically strong but had only 643 days and
  missed the history-completeness rule.
- In the current live overlap, `HACK` remained close but context-level:
  42 days, 0.9898 correlation, 0.9712 beta, and 0.216 percentage-point average
  error at 75% selected weight. At 80% weight it had 41 days, one short of the
  outage-adjusted completeness rule.
- `GAMR` is not a safe basket substitute. Much of the fund consists of
  foreign game companies. Its minimum mapped top-20 weight was only 19.86%.
  The long result rejected, and the current result was merely context-level
  even after allowing only 50% selected weight. It had no usable current day
  at 75% or 80% weight.

Evidence:

- `inventory/amplify_hack_gamr_sec_holdings_2022q4_2026q1.json`
- `inventory/amplify_hack_gamr_top20_ticker_map_v2_2026-07-19.json`
- `results/amplify_hack_gamr_top20_historical_baskets_2026-07-19.json`
- `results/amplify_hack_gamr_recent_baskets_2026-07-19.json`

Current and sensitivity evidence files:

- `results/industry_non_strong_recent_massive_targets_2026-04-28_to_2026-07-17.json`
- `results/industry_non_strong_recent_lse_hourly_manifest_2026-07-19.json`
- `results/industry_non_strong_recent_historical_baskets_2026-07-19.json`
- `results/industry_non_strong_archive_coverage_sensitivity_2026-07-19.json`
- `results/industry_non_strong_recent_coverage_sensitivity_2026-07-19.json`
- `results/industry_non_strong_recent_close_coverage_2026-07-19.json`

Sector evidence:

- `results/sector_top20_historical_baskets_2026-07-19.json`
- `results/sector_xli_xlp_xlv_top50_historical_baskets_2026-07-19.json`
- `results/sector_xli_xlp_xlre_xlv_top50_historical_baskets_2026-07-19.json`
- `results/xlre_recent_top50_basket_2026-04-28_to_2026-07-17.json`
- `inventory/all60_mapped_sec_holdings_2022q4_2026q1.json`
- `inventory/amplify_hack_gamr_sec_holdings_2022q4_2026q1.json`

### Full 63-benchmark direct-series search

Every production benchmark was compared with every plausible LSE market
series before building more baskets:

- 142 commodity, currency-index, ETF, futures, index, interest-rate, and
  volatility series were checked;
- 8,946 benchmark-to-series pairs were tested with daily data;
- only nine LSE series had at least 500 usable return days;
- those nine were then rebuilt from 110,029 hourly rows at the exact
  4:00 p.m. New York close.

Only one direct historical substitute passed the strict screen:

| Production benchmark | LSE series | Return days | Correlation | Beta | Average error | Verdict |
|---|---|---:|---:|---:|---:|---|
| SOXX | `SOX/USD` | 782 | 0.9970 | 1.0072 | 0.122 pp | strong |

That result is not live-safe by itself because `SOX/USD` stopped updating on
2026-06-30. The Nasdaq 100, Nasdaq Composite, and Nasdaq 100 futures were
useful broad technology context for IYW and XLK, but their beta and error were
too different to replace either ETF. No other benchmark had a strong or
context-level direct match.

Bottom line: searching harder for a differently named direct market series
does not solve the benchmark gap. Historical holdings baskets are needed for
62 of the 63 benchmarks. For current live data, the four exact LSE ETFs
`GDX`, `SOXX`, `XLE`, and `XLF` remain preferable whenever their data is
fresh.

Direct-screen evidence:

- `results/all63_market_series_daily_screen_2026-07-19.json`
- `results/all63_long_market_regular_close_screen_2026-07-19.json`
- `results/all63_benchmark_targets_2023-01-03_to_2026-04-27.json`

### Exact ETF daily and intraday overlap

LSE's raw daily ETF candles did not match Massive. Across 94 exact-ETF return
pairs for SOXX and XLE, their average error was 0.701 percentage points. This
is the same after-hours/calendar-day problem already found for stocks.

Using the LSE hourly bar ending at the official 4:00 p.m. close fixed it:

| Exact ETF | Return days | Correlation | Beta | Average error | Same direction |
|---|---:|---:|---:|---:|---:|
| SOXX | 42 | 0.9991 | 0.9969 | 0.115 pp | 100% |
| XLE | 45 | 0.9992 | 1.0078 | 0.050 pp | 100% |

Eight minute-level cases were then tested, including the largest recent daily
moves. Pooled comparisons against Massive minute candles were:

| Return window | Comparisons | Correlation | Beta | Average error |
|---|---:|---:|---:|---:|
| 5 minutes | 2,554 | 0.9959 | 1.0016 | 0.0132 pp |
| 60 minutes | 2,171 | 0.9995 | 0.9996 | 0.0130 pp |
| From each minute to 4:00 p.m. | 2,325 | 0.9997 | 0.9834 | 0.0383 pp |

The values are excellent when data exists, but availability is not perfect:

- one SOXX case stopped at 1:57 p.m. instead of 4:00 p.m.;
- one XLE case returned no minute rows;
- three other cases missed between one and seven regular-session minutes.

The test now rejects an incomplete final close instead of silently treating
the last available minute as 4:00 p.m. A production design therefore needs a
freshness/completeness gate and a fallback source. These are minute-candle
comparisons; they do not prove exact equivalence to Massive's production
one-second event-return candles.

Intraday evidence:

- `results/exact_etf_daily_overlap_2026-04-28_to_2026-07-17.json`
- `results/exact_etf_regular_close_overlap_2026-04-28_to_2026-07-17.json`
- `results/exact_etf_intraday_pilot_2026-07-19.json`

### Holdings baskets on real event windows

Daily-close matching is not enough for EventMarketDB. The same historical
holdings method was therefore tested on 122 real stored events from the graph:

- 82 AAPL events on 2023-06-05, using `XLK` and `IYW`;
- four AVGO events on 2024-12-12, using `XLK` and `SOXX`;
- 36 TSLA events on 2023-01-25, using `XLY` and `CARZ`.

For each event, the exact production hourly and session endpoints were kept.
Each holding used the latest LSE one-minute close at or before each endpoint,
with the same maximum backward age as Massive. The final candidate was rounded
to two decimals and compared with the stored Massive-derived benchmark return.

| Market period and window | Usable / attempted | Correlation | Beta | Average error |
|---|---:|---:|---:|---:|
| Regular market, hourly | 152 / 158 | 0.9365 | 0.9385 | 0.080 pp |
| Regular market, session | 152 / 158 | 0.9865 | 1.0327 | 0.135 pp |
| Pre-market, hourly | 19 / 26 | 0.3307 | 0.2088 | 0.189 pp |
| Pre-market, session | 19 / 26 | 0.1203 | 0.0835 | 0.596 pp |
| After-hours, hourly | 34 / 56 | 0.8837 | 1.0114 | 0.187 pp |
| After-hours into next open | 34 / 56 | 0.9216 | 1.0574 | 0.382 pp |

The regular-market result is encouraging: 304 of 316 comparisons were usable,
with a pooled 0.108 percentage-point average error. It also exposes an
important limit. Outside regular hours, an ETF can trade while many of its
underlying stocks are stale. A holdings basket therefore does not reliably
reproduce the ETF's own pre-market or after-hours return even when its daily
close match is excellent.

After correcting the SEC quarter search, `CARZ` did have a valid
2022-12-30 holdings snapshot before the January 2023 event. Re-running the
test still produced zero usable `CARZ` comparisons: its mapped/trading
constituents never reached the required 80% weight at the tested endpoints.
This confirms that the failure is real coverage and foreign-market timing,
not a missing filing. `XLK` was the strongest tested intraday basket: all 172
hourly/session comparisons were usable, with 0.077 and 0.089
percentage-point average error respectively. Results for the other funds were
more sensitive to the event session.

This is a one-minute approximation. A minute close can contain trades later
in the same minute, whereas production uses one-second Massive candles. The
result proves that regular-market holdings baskets are plausible, not that
they exactly reproduce one-second benchmark returns. Outside regular hours,
the evidence rejects a basket-only replacement without an exact ETF or
another live benchmark source.

Event-window evidence:

- `results/event_basket_lse_minutes_manifest_2026-07-19.json`
- `results/event_basket_comparison_2026-07-19.json`

Historical basket evidence:

- `results/proxy_pilot_daily_results_2026-07-19.json`
- `inventory/proxy_pilot_sec_holdings_2022q4_2026q1.json`
- `inventory/proxy_pilot_sec_ticker_map.json`
- `results/proxy_pilot_lse_hourly_manifest_2026-07-19.json`
- `results/proxy_pilot_lse_deep_DDOG_1h_2026-07-19.json`
- `results/proxy_pilot_lse_deep_DDOG_tick_2025-01-03.json`

Direct-series and holdings-basket screening now cover all 63 production
benchmarks. The remaining live test is U.S. market-hours latency and
completeness. It cannot by itself solve the event-time, outside-hours, daily
field, historical, or legal gaps already documented.

### Parked follow-up: LSE after-hours moves

The first daily comparison indicates that LSE daily bars can include
after-hours price moves that Massive's official daily process keeps separate.
In the AVGO case studied below, the LSE daily bar was exactly a UTC-calendar-
day rollup of its raw trades, so it captured the earnings move after the U.S.
close. That may be useful later as a new event signal.

This idea remains deliberately outside the replacement test. The current
evidence says basket-only outside-hours replacement is not reliable. LSE's
separate after-hours move may still be useful later as a new signal rather
than as a claim that it matches Massive.

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
- nominal maximum fallback: five days, with the code overshooting that limit
  as described below.

It returns `agg.close`, the close of the newest qualifying one-second bar whose bar-open
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
bar. Massive documents `t` as the start of the aggregate window and documents
that aggregate `from` and `to` values are snapped to resolution boundaries.
Applied to a one-second request, a bar starting at `10:00:00` can therefore be
selected for a target in that second, even though its close can reflect a
later qualifying trade before `10:00:01`. This last sentence is an inference
from the documented snapping rule and the production selector. The isolated
test proves that production selects such a returned bar; the current
entitlement cannot value-test a historical second request directly.

Exact replacement must reproduce this one-second candle rule, not merely pick
the final raw trade timestamp at or before the event.

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

Real Redis examples checked on 2026-07-20 make the rule concrete:

| Event | Rebuilt hourly start | Saved hourly end | Meaning |
|---|---|---|---|
| Pre-market at 9:01:33 AM | 9:01:33 AM | 10:01:33 AM | Crosses the 9:30 AM open |
| After-hours at 4:00:35 PM | 4:00:35 PM | 5:00:35 PM | Exact event-based hour |
| Late after-hours at 7:30:22 PM | 7:30:22 PM | 8:30:22 PM | Crosses the 8:00 PM extended-hours end |
| Closed market at 2:19:52 AM | 4:00:00 AM | 5:00:00 AM | Starts at that day's pre-market open |

The 8:30 PM time in the third row is the **requested endpoint**, not proof of
an 8:30 PM trade. Massive emits no aggregate when there is no qualifying
trade. `get_last_trade` then searches backward and can use the final eligible
bar at or before 8:00 PM. Stock, sector ETF, industry ETF, and SPY each search
independently, so thin extended-hours legs can use different actual bar
times. Redis and Neo4j do not save those selected bar timestamps; they save
the requested schedule and the final return only.

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

The exact early-close boundary is also different from a normal close. On an
early-close day, **1:00:00 PM itself is classified closed** because the first
check uses `timestamp >= post_market_end`. From 1:00 PM through 3:59:59 PM,
the code's `hour >= 16` check is false, so it incorrectly chooses 4:00–5:00 AM
that same day. At 4:00 PM or later it instead chooses the next trading day's
4:00–5:00 AM window.

### Direct Redis and Neo4j timing re-audit

The 2026-07-20 read-only re-audit checked the stores directly and imported the
current production calendar helper without changing it.

Redis currently retains 257 return records:

- 181 News, 70 filings, and 6 transcripts;
- all 257 saved market-session labels matched;
- all 257 hourly, session, and daily saved end times matched the current
  production calculation;
- 249 hourly starts were the exact event time;
- 8 closed-market events moved forward to a 4:00 AM start.

Neo4j was checked at the return-relationship level because return values live
on relationships:

| Source | Return relationships | Saved hourly schedule | Exact matches |
|---|---:|---:|---:|
| News | 345,103 | 345,103 | 345,103 |
| Filing | 41,895 | 41,895 | 41,895 |
| Transcript | 9,373 | 0 | Not directly checkable |
| **Total** | **396,371** | **386,998** | **386,998** |

There were zero saved-hourly-end mismatches among the 386,998 relationships
that retain a schedule. The Transcript graph path saved
`relationship.created_at` and return values but did not copy
`market_session` or `returns_schedule` onto Transcript nodes. Their windows
can be reconstructed, but the historical end cannot be compared with a saved
endpoint.

For exact graph reconstruction, `relationship.created_at` is the source of
truth. Ninety-seven News nodes have a different `node.created` value. The
News merge keeps the node's first `created` value, while every later processed
version overwrites the node schedule and the relationship's `created_at` and
return fields. In all 345,103 News relationships, the relationship time
matched the saved session and hourly schedule. Using the stale node time had
created 76 apparent schedule mismatches; using the timestamp stored beside
the return reduced that count to zero.

The same full scan found:

- 385,268 relationships whose hourly start equals the event time;
- 10,934 closed-market relationships whose start is a later 4:00 AM;
- 169 relationships—157 News and 12 filings—whose 4:00–5:00 AM hourly window
  ends before the event because of the early-close bug above.

No separate start-price time, end-price time, or selected Massive bar time is
stored. Start/end requests must be rebuilt from `relationship.created_at` and
the production rules. The sanitized evidence is
`results/return_timing_storage_reaudit_2026-07-20.json`.

### Delay behavior

The advertised Massive delay is 15 minutes. Production actually waits
17 minutes (`17 * 60 = 1,020` seconds), adding a two-minute safety buffer.
Both the scheduler and the price method enforce this delay.

Massive says a second bar is first emitted after a two-second wait and may be
revised for up to 15 minutes as late trades and FINRA data arrive. That
official behavior is consistent with the project's 15-minute delay plus
two-minute buffer. This is an inference about why 17 minutes was chosen, not a
comment found in the code.

Massive also says a trade arriving after that 15-minute buffer is not added to
the second bar until end-of-day processing. Therefore, a return saved at
end-plus-17-minutes can legitimately differ from the same historical Massive
bar fetched after end of day. This matters when treating stored returns as
the reference for a replacement test.

The Redis sorted-set score is normally saved end plus 1,020 seconds. In the
stopped April queue, 368 retained scores still matched that rule. Another 87
had been moved later by the production authorization-failure retry guard, and
31 queue members no longer had a payload. Those retry scores change when work
is attempted; they do not change the requested price window.

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

### Separate macro-panel coverage

This is separate from the existing Massive-compatible macro calculations.
It asks whether LSE can support a clearer panel showing the current market
and economic setting.

The authenticated catalog on 2026-07-19 contains every input in the proposed
core panel:

| Question | LSE input | Catalog history |
|---|---|---|
| Broad U.S. market | S&P 500 and Nasdaq 100 | February 2023 onward |
| Market fear | VIX | July 2026 onward |
| Intraday Treasury direction | U.S. 2Y, 5Y, 10Y, and 30Y price-like inputs | June 30, 2026 onward |
| Actual Treasury yields | Daily U.S. benchmark yields, including 2Y and 10Y | January 2010 onward |
| Yield curve | Daily U.S. 10Y percent yield minus 2Y percent yield | January 2010 onward |
| Dollar | DXY dollar index | June 30, 2026 onward |
| Oil | WTI crude | April 27, 2026 onward |
| Gold | Spot gold | April 27, 2026 onward |
| U.S. credit risk | HYG for live movement; USD Liquid High Yield Index for daily history | HYG from April 2026; credit index from 2010 |

That is **10 of 10 proposed signal concepts available**. However, the
intraday Treasury symbols are prices near 100 with blank units, not percent
yields. The real yield curve is therefore daily, not live. The published
free-key limit is 16 simultaneous streamed symbols. REST snapshots are not
limited to those same 16 simultaneous symbols.

The distinction was confirmed during the live switch test:
`USB02Y/USD` printed near 103 and `USB10Y/USD` near 109, while the daily
`US2YT=RR` and `US10YT=RR` series carried values near 4 percent and explicitly
used the unit `percent`. The two price-like streams can show intraday rate
direction because Treasury price and yield normally move oppositely, but
their values must never be treated as yields or subtracted to make a curve.

The wider catalog provides:

| Area | Coverage |
|---|---|
| Government rates | 88 daily yield series across the U.S., Canada, U.K., Germany, France, Italy, Spain, Japan, and Australia; most begin in 2010 |
| Bonds and credit | 202 government bond series, 192 individual corporate bonds, and 79 credit indexes; 21 credit indexes are U.S./USD |
| Currencies | 62 pairs covering 21 currencies; most begin in September 2009, plus 63 forward-rate series |
| Stock indexes | 19 indexes across 13 countries or regions: six U.S., nine European, and four Asia-Pacific |
| Commodities | 23 spot instruments, including WTI, Brent, gold, silver, copper, natural gas, and agricultural products |
| Economic conditions | 14,724 series across 194 countries or territories; 13,943 have at least ten years of history |

History quality is uneven:

- the price-based intraday panel overlaps only from July 1, 2026 because VIX,
  DXY, and the Treasury price feeds are new;
- the exact 10Y-minus-2Y yield curve is available only at daily frequency;
- long daily Treasury and credit series go back about 16 years;
- the 62 currency pairs mostly go back about 17 years;
- S&P 500, Nasdaq 100, and gold futures provide about ten years of usable
  directional history;
- a dollar index can be reconstructed from the long-history currency pairs;
- no long LSE VIX or WTI price history was found.

Using those longer substitutes, 8 of the 10 panel signals have roughly ten
years or more of history. VIX and WTI remain the two historical gaps.
Substitutes such as futures or a reconstructed dollar index are suitable for
new macro context, but they are not exact replacements for the old ETF
calculations.

The authenticated key grants the required candle, series, and export access,
and catalog timestamps were current through the latest market session. This
does not yet prove the live delay or completeness of each macro stream. A
market-session capture must measure the selected incoming symbols before the
panel is described as confirmed real time.

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

### Exhaustive production ETF recheck

A second, stricter check on 2026-07-19 confirmed the active benchmark mapping
from all three production sources:

- `config/final_symbols.csv`: 783 companies;
- live Redis, using one read-only `GET`: the same 783 companies and ETF
  assignments;
- Neo4j, using read-only queries: 796 companies, including 13 old companies,
  but the same 11 sector and 52 industry benchmark tickers.

The authenticated LSE check then made 134 candle requests: a normal and an
ETF-only request for every one of the 63 required tickers, plus a latest
minute and first-overlap daily request for the four covered tickers.

For all 59 missing tickers, the normal request returned 404 and the ETF-only
request returned 200 with no rows. None appeared under another LSE category
or a punctuation-only alias.

| Current company coverage | Companies |
|---|---:|
| Exact sector ETF available | 89 of 783 |
| Exact industry ETF available | 33 of 783 |
| Both exact ETFs available | 0 of 783 |

The wider catalog produced only text-related, non-equivalent ideas such as
`DIA` for industrials, European sector contracts, or commodities for
oil-and-gas groups. LSE metadata has no ETF holdings or weights dataset, so
the missing funds cannot be rebuilt exactly from LSE reference data.

The recheck also found a separate production issue: NYT is assigned `COMM`
as its Publishing benchmark. SEC filings show that `COMM` was CommScope
common stock, not a publishing ETF, and that the company changed its ticker
to `VISN` on 2026-01-14. `COMM` is also missing from the production ETF
validation allow-list. Neo4j contains 760 `COMM` price dates labeled as an
Industry, versus 831 for every other required benchmark. No production data
was changed.

The full 63-row result, company counts, exact endpoint evidence, and rejected
alternatives are in
[`PRODUCTION_ETF_COVERAGE.md`](PRODUCTION_ETF_COVERAGE.md).

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

#### Monday U.S. pre-market timing check

At 6:13 AM ET on 2026-07-20, the isolated test queried live one-minute REST
candles for AAPL, NVDA, TSLA, AMD, and XLE. AAPL, NVDA, TSLA, and AMD all had
a 6:13 AM bar when queried about 21–22 seconds into that minute. XLE's latest
bar was 6:10 AM, which can reflect less frequent pre-market trading.

The existing controlled WebSocket then subscribed to 15 macro symbols plus
NVDA. It authenticated, delivered 156 total messages and 15 current NVDA
ticks in 60 seconds, and reported no error. The final NVDA timestamp was
10:14:22.522 UTC and the run finished at 10:14:22.809 UTC. A follow-up REST
call showed new 6:14 AM bars for all four stocks. A separate 25-second receipt
test saw one NVDA print arrive 2.97 seconds after its message timestamp.

This proves that U.S. pre-market stock data was actively flowing through both
REST and WebSocket and was not timestamped 15 minutes behind in this sample.
It does not prove every eligible trade is present, normal-session performance,
or a contractual real-time guarantee. The switch was returned to OFF. The
sanitized evidence is
`results/lse_us_premarket_live_probe_2026-07-20.json`.

#### Trade, quote, and order-book content

A first raw WebSocket probe observed 67 pre-market messages across AAPL,
NVDA, TSLA, and AMD. Two follow-up probes raised the stock total to 202.
Every stock message had exactly these fields:

```text
ask, bid, price, symbol, ts, type, volume
```

This is live tick-level content rather than only one-minute candles. Price,
volume, and timestamp are trade-like print fields. It is not a complete
Massive-compatible trade tape because exchange, sale condition, correction,
cancellation, sequence, and trade ID are absent.

The fields named `bid` and `ask` were equal on all 202 stock messages and had
a positive spread on none. The trade price equalled both fields on 194
messages. On eight, the trade price differed from the still-equal fields by
one cent. There were no bid or ask sizes. This confirms that the values are
not an actionable stock quote, while also showing that they are not always
simple copies of that message's trade price.

The normal tick schema is asset-class dependent. A mixed official-feed probe
also observed 133 messages across EUR/USD, NAS100/USD, SPX500/USD, and
XAU/USD. All 133 had a positive spread, `price == bid`, and volume 1. Those
messages behave like quote updates rather than stock trade prints. A consumer
must not assign one meaning to every LSE `tick`.

##### Second website WebSocket

The earlier conclusion that no depth was available was incomplete. The
public reference and official `lse-data` 0.14.0 client expose no Level 2 or
Level 3 method, but the current LSE website uses a second, undocumented
WebSocket:

```text
wss://ws.londonstrategicedge.com
```

It accepted the same key and returned:

```text
status=ok, tier=Registered, max_symbols=16, l3_access=true
```

The website's live market table marks exactly 12 instruments for this feed:

| Display symbol | Website source-contract label |
|---|---|
| AUD/USD | 6AM6 |
| DE30/EUR | FDAX0626 |
| EU50/EUR | FESX0626 |
| EUR/USD | 6EM6 |
| GBP/USD | 6BM6 |
| NAS100/USD | NQM6 |
| SPX500/USD | ESM6 |
| USD/CAD | 6CM6 |
| USD/CHF | 6SM6 |
| USD/JPY | 6JM6 |
| XAG/USD | SIM6 |
| XAU/USD | GCM6 |

All 12 delivered normal ticks, book snapshots, and depth updates in the live
test. AAPL and NVDA were rejected with `INVALID_SYMBOL`. No U.S. stock is
marked for this path.

The observed message contracts were:

```text
tick          -> bid, ask, price, volume, ts
book_snapshot -> bids and asks as [price, size]
depth         -> side, price, raw_price, size, set/delete action, ts
trade         -> price, raw_price, size, buy/sell aggressor, ts
```

This is market-by-price depth, normally called Level 2. It is not true
order-by-order Level 3: no order identifier appeared, snapshots aggregate one
size at each price, and updates replace or delete that price's size. LSE's
internal names `l3_access`, `live_l3_data`, and `subscribeToL3` do not change
the delivered schema.

The all-symbol run received 181 quote ticks, 120 snapshots, 2,321 depth
updates, and 104 trade prints. All 181 quote ticks had a positive spread,
`price == bid`, and volume 1. The depth data had material defects:

- Quotes, snapshots, and depth appeared for all 12 symbols. Separate trade
  messages appeared for 10; AUD/USD and USD/JPY had none during the short
  sample. That does not prove those two never publish trades.

- 30 of 120 snapshots were crossed. Every snapshot for USD/CAD, USD/CHF, and
  USD/JPY had best bid above best ask.
- 917 depth updates, or 39.5%, carried an event time older than the newest
  snapshot.
- 853 updates, or 36.8%, went backward versus the prior depth event for that
  symbol.
- No sequence field exists to recover deterministic order.
- `raw_price` and displayed `price` differ by a changing symbol-specific
  amount. The feed is mapping a futures book onto a cash, CFD, or FX display
  symbol rather than delivering the raw book for that displayed instrument.
- On 2026-07-20 the website still labeled all 12 sources with June 2026
  contract codes. That may be stale metadata; it needs vendor confirmation.

The current website stores these updates exactly as one map entry per price,
so it would also apply old, out-of-order updates unless a newer snapshot
overwrites them. This path is useful for experimental macro order-flow
context, but it is not safe as a stock quote feed, stock order book, or exact
exchange book.

##### Other trade and quote paths

A search of all 124 current website code chunks found no other free stock
quote or stock-depth interface. It found:

- `wss://api.londonstrategicedge.com/ws/options-flow/`, a public options
  stream. An eight-second pre-market test connected without an authentication
  message and received GEX, max-pain, put/call-ratio, and skew updates. The
  website also handles `flow` messages containing option prints. This is not
  a stock quote feed.
- broker runtime quote endpoints with real bid, ask, and last fields. They
  require a connected broker login and session token and cannot be used with
  the LSE data key alone.
- `/l2_ob_profile_1m`, a BTC/USD-only historical price-level profile in the
  current chart.
- standalone order-book pages that connect directly to Binance EURUSDT or
  BTCUSDT depth and trades. They are demos, not evidence of LSE stock depth.

The authenticated vault metadata lists no quote, order-book, depth, L2, or L3
dataset. Historical stock exports contain only timestamp, symbol, price, and
volume.

The corrected sanitized evidence is
`results/lse_trade_quote_depth_probe_2026-07-20.json`. The earlier
`results/lse_live_tick_fields_and_universe_2026-07-20.json` remains valid for
the official stock stream and universe count, but not as a platform-wide
depth conclusion.

The same authentication response listed 4,308 streamable instruments across
all asset classes. Exact comparison with the current 783-company file found
754 stocks present and 29 absent, unchanged from the REST catalog audit. The
free 16-symbol simultaneous limit also means the 754 cannot all be watched at
once. Sanitized evidence:
`results/lse_live_tick_fields_and_universe_2026-07-20.json`.

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

Breaking the same saved rows out by market period gives:

| Market period | Comparable | Exact | Within 0.01 points | Within 0.05 points | Average error | Largest error |
|---|---:|---:|---:|---:|---:|---:|
| Regular hours | 79 | 51 | 79 | 79 | 0.0035 points | 0.01 points |
| Pre-market | 13 | 4 | 6 | 13 | 0.0169 points | 0.05 points |
| After-hours | 27 | 3 | 6 | 15 | 0.0759 points | 0.53 points |

The pre-market sample was close but less exact than regular hours.
After-hours was materially weaker; TSLA had the largest miss at 0.53
percentage points. This fits the broader evidence that trade coverage and
official print handling differ most around thin or special trading periods.

These are return-level comparisons against Massive-derived values already
stored in Neo4j. The raw Massive start and end trades were not stored, so this
does not compare every LSE print directly against every Massive print.

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

For pre-market events, all 13 comparable session returns were within 0.05
percentage points, with a 0.018-point average error and 0.05-point maximum.
Only two after-hours-to-next-open session returns were comparable because the
limited exports did not cover most next-session endpoints; both were within
0.05 points, which is too small a sample for a firm conclusion.

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
| Live no-delay operation | Pre-market sample passed; not production accepted | Current REST bars and NVDA WebSocket ticks were observed at 6:13 AM ET; feed completeness, regular-session load, source rules, and contractual rights remain unproven |

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
- `results/neo4j_etf_inventory_2026-07-19.json` — current sector and industry
  assignments plus the first LSE-covered ETF overlap date.
- `results/redis_inventory.json` — read-only return queue and tracking-key
  inventory.
- `results/return_timing_storage_reaudit_2026-07-20.json` — all 396,371
  Neo4j return relationships, all 257 retained Redis return records, exact
  reconstructed hourly windows, saved-end checks, queue-delay checks, stale
  News-node timestamps, and early-close failures.
- `results/redis_etf_mapping_check_2026-07-19.json` — one read-only live Redis
  check confirming the active 783-company ETF mapping.
- `results/lse_contract_probe.json` — first live contract probe.
- `results/lse_contract_probe_v2.json` — date-only and ETF-depth checks.
- `results/lse_contract_probe_v3.json` — valid intraday range checks.
- `results/macro_websocket_smoke_2026-07-19.json` — sanitized 16-symbol
  authentication, tick, active-OFF, freshness, and Treasury-field evidence.
- `results/lse_us_premarket_live_probe_2026-07-20.json` — current-minute U.S.
  pre-market REST bars, NVDA WebSocket ticks, receipt-lag sample, and final
  OFF-switch evidence.
- `results/lse_live_tick_fields_and_universe_2026-07-20.json` — raw stock
  tick fields, quote-field behavior, official-client depth-method check, and
  current exact 754-of-783 stream-symbol comparison.
- `results/lse_trade_quote_depth_probe_2026-07-20.json` — corrected
  two-WebSocket assessment, per-symbol quote/trade/depth counts, delivered
  schemas, depth-ordering defects, and all other website market-data paths.
- `results/ibkr_contract_universe_2026-07-20.json` — read-only qualification
  of all 783 configured stock tickers.
- `results/ibkr_live_gap_coverage_2026-07-20.json` — live IBKR prices for LSE
  stock gaps, all 63 required benchmarks, and control symbols.
- `results/ibkr_live_tick_by_tick_2026-07-20.json` — detailed live trade
  samples for one stock and four production benchmarks.
- `results/ibkr_massive_hourly_pilot_2026-07-20.json` — pre-market,
  regular-hours, and after-hours one-second return comparisons.
- `results/ibkr_massive_late_afterhours_2026-07-20.json` — exact late
  after-hours fallback comparison.
- `results/ibkr_massive_closed_market_2026-07-20.json` — thin 4:00–5:00 AM
  comparison and its two mismatches.
- `results/ibkr_massive_daily_atr_pilot_2026-07-20.json` — daily return,
  daily OHLC, and ATR comparison.
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
- `results/production_etf_coverage_2026-07-19.json` and
  `inventory/production_etf_coverage_2026-07-19.csv` — fresh catalog,
  all 134 direct required-ETF candle checks, company counts, and one row per
  production benchmark.
- `scripts/audit_return_timing_storage.py` and
  `tests/test_audit_return_timing_storage.py` — repeatable read-only Redis and
  Neo4j timing audit plus focused storage/timing tests.
- `tests/` — isolated tests covering price selection, fallback windows,
  production semantics, session reconstruction, timezones, tied timestamps,
  corporate-action normalization, macro calculations, stream safety, and ETF
  coverage classification.
- `raw/lse-data-main/` — isolated snapshot of the official open-source LSE
  client used to verify endpoint paths and stated behavior.
- `raw/lse_tick_exports/` and `raw/lse_one_second_exports/` — isolated AVGO
  raw-tick and one-second exports. Processed AAPL and TSLA second-candle
  comparisons are saved under `results/`.

No production source file or production database was changed. This research
folder is the audit's only addition to EventMarketDB.
