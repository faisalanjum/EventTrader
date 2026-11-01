# Production ETF Coverage in London Strategic Edge

Checked: 2026-07-19

## Bottom line

LSE does not provide enough of EventMarketDB's exact sector and industry
benchmarks.

| Production need | Required | Exact LSE ETFs | Coverage |
|---|---:|---:|---:|
| Sector benchmarks | 11 | 2: `XLE`, `XLF` | 18.18% |
| Industry benchmarks | 52 | 2: `GDX`, `SOXX` | 3.85% |
| Distinct benchmark tickers | 63 | 4 | 6.35% |

For the 783 companies used by the live Redis universe:

- 89 have their exact sector ETF on LSE;
- 33 have their exact industry ETF on LSE;
- **zero have both**.

LSE therefore cannot produce the existing stock + sector + industry + SPY
return object for any current company by itself.

“Covered” here means the exact same ETF ticker exists in LSE's ETF dataset
and returns price candles. A similar fund, index, commodity, option, or
European sector contract does not count.

## What production uses

The same active mapping was confirmed three ways:

1. `config/final_symbols.csv`: 783 companies, 11 sector ETFs, 52 industry
   benchmark tickers.
2. Live Redis, using one read-only `GET`: the same 783 companies and the same
   63 benchmark tickers.
3. Neo4j, using read-only queries: 796 company assignments, including 13 old
   companies no longer in the CSV, but the same 63 benchmark tickers.

The return path reads each company's two benchmark tickers from the Redis
universe and asks for four returns:

```text
company stock + sector ETF + industry ETF + SPY
```

The broad 83-symbol set in `utils/ETF_mappings.py` is only an ETF validation
allow-list. It is not the active company mapping. It contains 21 tickers not
used by the current universe and is missing one active mapping, `COMM`.

## How LSE was checked

The authenticated audit used the user's live key without saving it.

- Fetched the fresh 22,777-row LSE catalog.
- Confirmed that LSE lists only 25 ETF price symbols.
- Searched every required ticker across all 18 LSE data categories.
- Searched punctuation-only symbol aliases.
- Sent a normal latest-daily candle request for every required ticker.
- Sent a second request for every ticker explicitly pinned to the ETF
  dataset.
- For the four covered tickers, also requested a latest minute and the first
  dates overlapping the Massive graph.

This was 134 direct candle checks:

```text
63 normal daily + 63 ETF-only daily + 4 overlap daily + 4 latest minute
```

Repeat from the repository root:

```bash
LSE_API_KEY=your_key venv/bin/python \
  data/lse_massive_replacement/scripts/audit_production_etf_coverage.py \
  --live \
  --output-json data/lse_massive_replacement/results/production_etf_coverage_2026-07-19.json \
  --output-csv data/lse_massive_replacement/inventory/production_etf_coverage_2026-07-19.csv
```

For every one of the 59 missing tickers:

- the normal lookup returned HTTP 404;
- the ETF-only lookup returned HTTP 200 with zero rows;
- no exact ticker appeared under stocks, indices, options, or another data
  category;
- no punctuation-only alias appeared.

The result is therefore a real coverage gap, not merely a catalog label or
endpoint-routing problem.

## Sector ETFs

Company counts below use the current 783-company production universe.

| ETF | Sector | Companies | LSE result |
|---|---|---:|---|
| `XLB` | Basic Materials | 33 | Missing |
| `XLC` | Communication Services | 30 | Missing |
| `XLE` | Energy | 35 | Exact; history starts 2026-04-27 |
| `XLF` | Financial Services | 54 | Exact; history starts 2026-04-28 |
| `XLI` | Industrials | 108 | Missing |
| `XLK` | Technology | 158 | Missing |
| `XLP` | Consumer Defensive | 44 | Missing |
| `XLRE` | Real Estate | 35 | Missing |
| `XLU` | Utilities | 25 | Missing |
| `XLV` | Healthcare | 141 | Missing |
| `XLY` | Consumer Cyclical | 120 | Missing |

## Industry ETFs

Only these two are exact:

| ETF | Production groups | Companies | LSE history starts |
|---|---|---:|---|
| `GDX` | Gold | 1 | 2026-04-28 |
| `SOXX` | Communication Equipment; Semiconductor Equipment and Materials; Semiconductors | 32 | 2026-04-27 |

These 50 assigned industry tickers are missing:

```text
AMLP, CARZ, COMM, CRAK, EATZ, FCG, FDN, FTXR, GAMR, HACK,
IAI, IBB, IDU, IGV, IHE, IHF, IHI, INDS, ITA, ITB,
IYJ, IYM, IYR, IYT, IYW, IYZ, JETS, KIE, MOO, OIH,
PAVE, PBJ, PEJ, PHO, PKB, REM, REZ, SCHH, SLX, SRET,
TAN, VAW, VCR, VDC, VOX, XHB, XME, XOP, XPH, XRT
```

The exact company count and production group for every ticker are in
[`production_etf_coverage_2026-07-19.csv`](../inventory/production_etf_coverage_2026-07-19.csv).

## History is also too short

Even the four covered ETFs begin only on 2026-04-27 or 2026-04-28. The
production graph stores Massive daily prices from 2023-01-03 through
2026-04-27.

Only `XLE` and `SOXX` had an LSE daily candle on the graph's final date:

| ETF | Massive graph close, 2026-04-27 | LSE close | Difference |
|---|---:|---:|---:|
| `XLE` | 56.77 | 56.86 | +0.09 |
| `SOXX` | 455.41 | 455.06 | -0.35 |
| `GDX` | 92.59 | No LSE candle until 2026-04-28 | — |
| `XLF` | 51.81 | No LSE candle until 2026-04-28 | — |

The OHLC and volume fields also differed on the overlapping rows. The four
symbols therefore do not provide a historical replacement for the stored
Massive ETF records.

## Similar LSE symbols are not replacements

The wider catalog was searched by production group names. It found a few
related market series, but none can replace a missing ETF exactly:

- `DIA` is not `XLI`; the Dow 30 is not the U.S. industrial sector.
- `GLD`, spot gold, and gold futures are not a gold-miner equity ETF.
- Natural gas and oil prices are not oil-and-gas company ETFs.
- Europe 600 sector contracts have the wrong region and were stale in the
  fresh catalog.
- `SMH` and the PHLX Semiconductor Index are related to semiconductors, but
  production already has exact `SOXX` coverage.

LSE metadata lists no ETF holdings or weights dataset. Rebuilding the 59
missing funds from component stocks would therefore require an outside
holdings source, daily weights, corporate-action handling, and rebalancing.
That would create a different calculated product, not LSE data for the exact
ETF.

## Separate production issue: `COMM`

`COMM` is assigned to NYT as the Publishing industry benchmark, but it is not
a U.S. publishing ETF.

- SEC filings identify `COMM` as the former Nasdaq ticker for CommScope
  common stock.
- CommScope changed its ticker to `VISN` on 2026-01-14.
- `COMM` is the only active benchmark missing from the production ETF
  validation allow-list.
- Neo4j stores 760 price dates for `COMM`, while every other active benchmark
  has 831. Those rows are labeled as an Industry even though the ticker
  represented a company.

This likely means historical NYT “industry” returns used CommScope stock
prices. It is an existing production mapping problem, independent of LSE.
No production file or database was changed during this audit.

## Evidence

- [`production_etf_coverage_2026-07-19.json`](../results/production_etf_coverage_2026-07-19.json)
  — full catalog matches,
  every API response, live limits, history spans, company coverage, and
  possible-but-rejected name matches.
- [`production_etf_coverage_2026-07-19.csv`](../inventory/production_etf_coverage_2026-07-19.csv)
  — one row for each of the
  63 required benchmark tickers.
- [`neo4j_etf_inventory_2026-07-19.json`](../results/neo4j_etf_inventory_2026-07-19.json)
  — read-only graph assignments
  and covered-ETF price overlap.
- [`redis_etf_mapping_check_2026-07-19.json`](../results/redis_etf_mapping_check_2026-07-19.json)
  — read-only live Redis
  mapping confirmation.
- [`audit_production_etf_coverage.py`](../scripts/audit_production_etf_coverage.py)
  — repeatable, secret-safe audit.
- [`test_production_etf_coverage.py`](../tests/test_production_etf_coverage.py)
  — isolated classification and
  counting tests.
