# Goal 1 Ground-Truth Corpus Report

Eligible universe size is 10,831 earnings 8-K rows, defined by `formType="8-K"`, `items CONTAINS "2.02"`, and a non-null `PRIMARY_FILER.daily_stock`. The generated corpus assigns every eligible accession to exactly one output file: 9,909 rows in `ground_truth.csv` and 922 rows in `needs_review.csv`.

`ground_truth.csv` contains only same-event historical rows where the matched 10-Q/10-K was filed after the 8-K, the periodic filing has parseable SEC XBRL fiscal focus tags, the periodic accession is not in the XBRL denylist, the XBRL/fiscal-math proximity guard accepts the pair, and the XBRL and fiscal-math identities agree. This is a high-confidence historical benchmark corpus, not a live-mode solution.

Needs-review breakdown:
- no_fye: 0
- not_same_event_periodic: 495
- no_xbrl: 4
- denylist: 6
- proximity_rejected: 26
- xbrl_math_disagree: 391

Ticker distribution is broad across the eligible universe. The most represented tickers are EQT (28), TSLA (28), FANG (28), NOG (27), ABBV (27), CF (26), TEX (25), ACMR (25), OXY (24), REGN (23). Ground-truth-heavy tickers include EQT (28), TSLA (28), FANG (27), NOG (27), ABBV (26), CF (26), ACMR (24), HOOD (23), while needs-review-heavy tickers include ACI (14), CNM (14), DKS (14), GME (14), KSS (14), LEVI (14), PEP (14), PVH (14). Sector distribution from available company metadata is led by Technology (2150), Healthcare (2051), ConsumerCyclical (1616), Industrials (1460), FinancialServices (736), ConsumerDefensive (597), Energy (538), BasicMaterials (485); rows without sector metadata are grouped as `Unknown`.

The main unusual finding is expected from the Goal 1 design: `not_same_event_periodic` rows are not defects in the historical ground-truth set. They are the FCX-shaped/live-mode cases where no later same-quarter periodic filing exists in the graph at the 8-K point-in-time, or the eligible 8-K is too recent for such a filing. Those rows remain classified residuals for Goal 2/3 handling and must fail closed rather than being forced into the benchmark.
