# WP1 Report — regenerated cohort (A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL)

Manifest (incl. output sha256s): `data/driver_catalog_seed/wp1_manifest.json` · slice sha `473bda9dcb0513a8…`
Command: `venv/bin/python scripts/driver_seed/run_code_tier.py --tickers A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL --tag wp1` · verifier: `scripts/driver_seed/wp1_verify.py` (this file regenerates
this report; all assertions passed or it would have crashed).

## Mechanical compliance (safety checks — NOT precision; true P/R = WP4)
- value-token-in-quote: **389/389**
- quote-is-exact-source-substring: **389/389**
- fabricated quotes in THIS cohort: **0** (asserted) · older part1–4 artifacts: **STALE/INVALID**

## Reconciliation by distinct raw-row id (asserted)
raw rows 1535 = unique ids 1535; every id accounted for in
resolved/residual/abstain; no id carries two different (kpi,value).

## Coverage
resolved 389 (routes: {('T1-xbrl', '10k'): 89, ('T2-label', '8k'): 129, ('T1-xbrl', '10q'): 16, ('T2-label', '10k'): 120, ('T2-label', '10q'): 35}) · residual 353 · abstain 1006
(reasons: {'derived_metric': 961, 'value_absent': 45}; sources_incomplete-flagged: 45)
value bands (resolved): {'other': 358, 'decimal': 31}

run summary: {"tag": "wp1", "records_resolved": 389, "residual": 353, "abstain": 1006, "company_periods": 25, "T1_xbrl": 105, "T2_label": 284, "pr_records": 129, "cp_no_filing": 0}
