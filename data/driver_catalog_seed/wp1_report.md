# WP1 Report — regenerated cohort (A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL)

Manifest (incl. output sha256s): `data/driver_catalog_seed/wp1_manifest.json` · slice sha `473bda9dcb0513a8…`
Command: `venv/bin/python scripts/driver_seed/run_code_tier.py --tickers A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL --tag wp1` · verifier: `scripts/driver_seed/wp1_verify.py` (CHECK-ONLY by default;
this report is regenerated only by `--record`; all assertions passed or it would have crashed).

## Mechanical compliance (safety checks — NOT precision; true P/R = WP4)
- value-token-in-quote: **329/329**
- quote-is-exact-source-substring: **329/329**
- fabricated quotes in THIS cohort: **0** (asserted) · older part1–4 artifacts: **STALE/INVALID**

## Reconciliation by distinct raw-row id (asserted, BOTH directions)
raw rows 1535 (0 identical duplicates collapsed -> 1535 distinct) =
unique ids 1535; every id accounted for in resolved/residual/abstain; ZERO invented extra
ids; no id carries two different (kpi,value).
Denominators: **1535 raw rows** (reconciliation basis) · **1400 unique
(ticker,kpi,period) targets** (coverage basis).

## Coverage
resolved 329 (routes: {('T1-xbrl', '10k'): 88, ('T2-label', '8k'): 81, ('T1-xbrl', '10q'): 15, ('T2-label', '10k'): 111, ('T2-label', '10q'): 34}) · residual 410 · abstain 1006
(reasons: {'derived_metric': 961, 'value_absent': 45}; sources_incomplete-flagged: 4)
value bands (resolved): {'other': 298, 'decimal': 31}
8-K gate verdicts (sources_ledger): {'uncertain': 48, 'other_period': 269, 'accept': 24}
consulted/used source accessions pinned in manifest: 49

## 8-K selection honesty (round-14)
Selection = resolver AUTO_OK (its own benchmark documents a **0.24% warm-start wrong-fire
ceiling** — quarter_identity.py:100-104) AND pure STRUCTURAL PAIRING (the 8-K's certified prior
periodic == the target's predecessor, or the target itself for documented inversions) inside the
announcer window (period_end, next-period filing]. NO fiscal identities/labels anywhere — dei
conventions are inconsistent even within one company (WMS). Every accepted 8-K's pairing +
window is INDEPENDENTLY re-derived from the graph by this verifier (resolver's own prior query —
a different code path than the run's). Zero-error is a MEASURED claim (WP4), never assumed.

run summary: {"tag": "wp1", "records_resolved": 329, "residual": 410, "abstain": 1006, "company_periods": 25, "T1_xbrl": 103, "T2_label": 226, "pr_records": 81, "cp_no_filing": 0, "duplicate_rows_collapsed": 0}
