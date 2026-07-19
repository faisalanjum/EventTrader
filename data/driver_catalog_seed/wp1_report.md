# WP1 Report — regenerated cohort (A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL)

Manifest (incl. output sha256s): `data/driver_catalog_seed/wp1_manifest.json` · slice sha `473bda9dcb0513a8…` ·
committed input slice: `data/driver_catalog_seed/wp1_worklist_slice.jsonl` (re-hashes to the same sha)
Command: `venv/bin/python scripts/driver_seed/run_code_tier.py --worklist data/driver_catalog_seed/wp1_worklist_slice.jsonl --tickers A,AA,AAL,AAPL,ABT,ACI,ACN,ADM,AEE,AFL --tag wp1` · verifier: `scripts/driver_seed/wp1_verify.py` (CHECK-ONLY default;
all checks finish before anything is written; `--record` stamps only after every assertion passed).

## Mechanical compliance (safety checks — NOT precision; true P/R = WP4)
- value-token-in-quote: **280/280** (asserted)
- quote-is-exact-source-substring: **280/280** (asserted, live re-fetch)
- fabricated quotes in THIS cohort: **0** (asserted) · older part1–4 artifacts: **STALE/INVALID**

## 8-K selection (round-15 matcher — the owner's two-file authority)
Historical pairing = `get_quarterly_filings.match_8k_to_periodic` (the shared structured matcher):
companion = the original 10-Q/K covering the most recently ENDED period at the 8-K's filing time,
lag-validated [-24h, +90d]; accept iff that accession EXACTLY equals the target AND
`quarter_identity` says AUTO_OK (trust gate only — labels and calculated dates are NEVER joined).
Unclear -> PARK at the matched target. The live lane (no companion yet) = quarter_identity alone
(S4 wiring). Resolver's own documented wrong-fire ceiling: 0.24% (quarter_identity.py:100-104).
**Pairing verification claim, stated exactly:** every ACCEPTED 8-K in this cohort
(24) is INDEPENDENTLY re-derived from the graph by this verifier. The
universe-wide sweep cross-checked 9,788 accepts with a convention-free heuristic (9 flags, all
adjudicated as checker false-alarms) and adjudicated 1,206 parks by class; parked 8-Ks carry NO
pin claim. (Reviewer's independent audit phrased it: 0 mismatches among 10,264 exact historical
pins; 730 lacked exact pins.) Zero-error remains a MEASURED claim (WP4), never assumed.

## Reconciliation by distinct raw-row id (asserted, BOTH directions)
raw rows 1535 (0 identical duplicates collapsed -> 1535 distinct) =
unique ids 1535; every id accounted for; ZERO invented extra ids; no id carries two
different (kpi,value).
Denominators: **1535 raw rows** (reconciliation basis) · **1400 unique
(ticker,kpi,period) targets** (coverage basis).

## Coverage
resolved 280 (routes: {('T1-xbrl', '10k'): 77, ('T2-label', '10k'): 93, ('T2-label', '8k'): 69, ('T1-xbrl', '10q'): 13, ('T2-label', '10q'): 28}) · residual 445 · abstain 997
(reasons: {'derived_metric': 961, 'value_absent': 36}; sources_incomplete-flagged: 2)
8-K gate verdicts (sources_ledger): {'uncertain': 48, 'other_period': 269, 'accept': 24}
sources: **25 target filings + 24 accepted 8-Ks**

## Outcomes by value band (every distinct raw row)
- **zero**: {'residual_only': 14, 'skip:derived_metric': 53, 'value_absent:value_absent': 2}
- **small**: {'skip:derived_metric': 80, 'residual_only': 18}
- **decimal**: {'skip:derived_metric': 828, 'resolved': 18, 'residual_only': 8, 'value_absent:value_absent': 1}
- **other**: {'residual_only': 272, 'value_absent:value_absent': 33, 'resolved': 208}

run summary: {"tag": "wp1", "records_resolved": 280, "residual": 445, "abstain": 997, "company_periods": 25, "T1_xbrl": 90, "T2_label": 190, "pr_records": 69, "cp_no_filing": 0, "duplicate_rows_collapsed": 0}
