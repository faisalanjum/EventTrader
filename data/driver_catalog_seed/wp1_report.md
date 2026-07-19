# WP1 Report — regenerated cohort (A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL)

Manifest: `data/driver_catalog_seed/wp1_manifest.json` · code commit 02d1f07 ·
worklist slice sha `473bda9dcb0513a8…` · command: `venv/bin/python scripts/driver_seed/run_code_tier.py --tickers A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL --tag wp1`

## Mechanical compliance (safety checks — NOT precision; true P/R = WP4)
- value-token-in-quote: **352/352** = 100%
- quote-is-exact-source-substring: **352/352** = 100%
- fabricated (quote_source='xbrl_fact') records in THIS cohort: **0** (asserted)
- older part1–4 artifacts: **STALE/INVALID** (not regenerated)

## Coverage — three bases (they differ by design)
| base | count |
|---|---|
| raw vendor rows (pinned slice) | 1535 |
| unique targets (item_id) | 1535 |
| emitted source records (resolved) | 352 |

resolved 352 · residual 344 (unique targets 344) · abstain 1006
(reasons: {'derived_metric': 961, 'value_absent': 45}) · value-absent rows flagged sources_incomplete: 45

## Routes (resolved)
- T1-xbrl via 10k: 90
- T1-xbrl via 10q: 16
- T2-label via 10k: 120
- T2-label via 10q: 35
- T2-label via 8k: 91

## Value bands
- resolved: {'other': 321, 'decimal': 31}
- value-absent: {'other': 42, 'zero': 2, 'decimal': 1}

run summary: {"tag": "wp1", "records_resolved": 352, "residual": 344, "abstain": 1006, "company_periods": 25, "T1_xbrl": 106, "T2_label": 246, "pr_records": 91, "cp_no_filing": 0}
