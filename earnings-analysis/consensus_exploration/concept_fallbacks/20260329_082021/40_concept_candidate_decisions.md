# Concept Candidate Decisions

Run: 2026-03-29, 772 tickers, 6,151 quarters, 31,744 null cases

## Phase 2 Survivors (reviewed candidates)

### 1. capex → us-gaap:PaymentsToAcquireProductiveAssets
- Coexistence classification: **different_metric**
- Coexistence pairs: 27 (16 tickers)
- Non-interference: not tested (failed coexistence)
- Final decision: **REJECT**
- Rationale: PaymentsToAcquireProductiveAssets is a broader concept that includes non-PPE
  productive assets. When coexisting with PaymentsToAcquirePropertyPlantAndEquipment,
  values are materially different.

### 2. depreciation_amortization → us-gaap:Depreciation
- Coexistence classification: **different_metric**
- Coexistence pairs: 626 (184 tickers)
- Non-interference: not tested (failed coexistence)
- Final decision: **REJECT**
- Rationale: Depreciation excludes amortization. Massive coexistence evidence (626 pairs)
  proves these are different metrics. Plan correctly flagged this as high-risk.

### 3. dividends_per_share → us-gaap:CommonStockDividendsPerShareCashPaid
- Coexistence classification: **different_metric**
- Coexistence pairs: 267 (52 tickers)
- Non-interference: not tested (failed coexistence)
- Final decision: **REJECT**
- Rationale: Declared vs paid timing difference. When both are reported in the same filing,
  they differ due to declaration-to-payment lag across quarter boundaries.

## Phase 2 Filtered Out (< 3 companies)

These candidates appeared in fewer than 3 companies where the primary was null,
meaning the current registry already covers nearly all cases:

- revenue → SalesRevenueNet (< 3 companies)
- cost_of_revenue → CostOfGoodsSold (< 3 companies)
- operating_cash_flow → NetCashProvidedByOperatingActivities (< 3 companies)
- capex → CapitalExpenditure (< 3 companies)

## Conclusion

No reviewed-candidate registry changes warranted from this run. The only prior
addition (IncomeLossFromContinuingOperationsPerDilutedShare for eps_diluted) was
validated via direct ABNB evidence and remains correct.

Corpus mining (Phase 3) not warranted — reviewed candidates cover all high-probability
synonyms, and the 4 filtered candidates confirm near-complete coverage for their metrics.
Future runs may discover new candidates as the filing universe grows.
