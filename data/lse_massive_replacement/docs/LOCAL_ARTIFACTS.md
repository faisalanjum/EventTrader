# Local Audit Artifacts

The full working evidence remains under
`data/lse_massive_replacement/`; it is not in `/tmp`.

## Saved locally

| Folder | Size | Files | Contents |
|---|---:|---:|---|
| `raw/` | 314 MiB | 10,166 | LSE candles, reference caches, SEC/OpenFIGI downloads, and event samples |
| `results/` | 140 MiB | 102 | Detailed candidates, controls, manifests, and comparison reports |
| `inventory/` | 44 MiB | 49 | Holdings, ticker maps, catalogs, and final CSV tables |

These files were not deleted. New bulk market-data caches and large
reproducible intermediate reports are ignored by this folder's `.gitignore`
to avoid accidentally publishing licensed data or adding hundreds of
megabytes to normal Git history.

The scripts, runnable tests, documentation, final 63-row matrix, and production
ETF coverage table are kept in Git. Detailed JSON results and working maps remain
local. The historical IBKR test limitation is recorded below. A future run can rebuild the larger local
files from the documented sources.

## Important local checksums

```text
520cf7ccc92bdda9d8d19f88ad4fb28fb713a561059da9ea687e6cbbdd7e6810  results/lse_stock_splits_complete_2023-01-03_to_2026-07-17.json
2c788520a9dce3b5e69b63367f29f6b75604da0c01b5e00acbdcd99dde302de8  results/industry_non_strong_archive_coverage_sensitivity_2026-07-19.json
ad5475e9d1f6bfbfabc8bdcec2fbbc98df24f5c11123fffb5655f5e4ea2558f0  results/industry_non_strong_recent_coverage_sensitivity_2026-07-19.json
ae62700329ce033466a57d288e9300ebbc49b7ed74d6c555ef5cf8310e8899de  inventory/all60_mapped_sec_holdings_2022q4_2026q1.json
```

No API key is stored in these artifacts.

## Incomplete historical IBKR test

The July IBKR comparison test imports three helpers that are absent from this
checkout and its checked Git history: `audit_ibkr_live_gaps`,
`compare_ibkr_massive_daily`, and `compare_ibkr_massive_hourly`. Its unpublished
test source is preserved in the private cleanup keeper, not the runnable suite.
The saved July results remain historical evidence; this cleanup does not
reproduce or newly qualify those IBKR comparisons. No live IBKR service changed.
