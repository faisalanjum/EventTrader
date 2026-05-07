# Yellow-Ticker Verification

Research-only verification of the five "yellow" tickers from `AUTOPSY_FINAL.md`: ANF, CNM, DKS, PLCE, PVH.

## Bottom Line

The yellow claim is mostly correct, but needs refinement.

```text
9 canonical disputed G2/H2-wrong rows found:
  8 are audit-truth errors: ANF(2), DKS(5), PVH(1)
  1 is a real stale-prior-XBRL/data-quality miss: CNM(1)

PLCE has 0 Tier A/B disputed wrong rows in advance_xbrl_simulation.csv.
```

So H2 is stronger than Goal 6f suggested, but not by itself perfect. A production candidate would need:

1. H2-style issuer convention gate.
2. A stale-prior-XBRL sanity guard, which catches CNM's bad 10-K basis.
3. A cleaned/corrected SEC truth table for the ANF/DKS/PVH audit rows before any final scoring.

## Per-Row Verdicts

| Ticker | Accession | Old Audit Truth | G2/H2 Label | Verified Label | Verdict | Why |
|---|---|---:|---:|---:|---|---|
| ANF | `0001018840-23-000074` | Q2 FY2022 | Q2 FY2023 | Q2 FY2023 | audit truth error | EX-99.1 announces second quarter ended July 29, 2023; audit quote was a comparison/back-reference to 2022. Companion 10-Q XBRL is Q2 FY2023. |
| ANF | `0001018840-23-000086` | Q3 FY2022 | Q3 FY2023 | Q3 FY2023 | audit truth error | EX-99.1 announces third quarter ended October 28, 2023; audit quote was a prior-year comparison. Companion 10-Q XBRL is Q3 FY2023. |
| DKS | `0001089063-23-000122` | Q1 FY2023 | Q2 FY2023 | Q2 FY2023 | audit truth error | EX-99.1 announces second quarter ended July 29, 2023; audit quote came from a debt/footnote reference to Q1 2023. Companion 10-Q XBRL is Q2 FY2023. |
| DKS | `0001089063-23-000143` | Q3 FY2022 | Q3 FY2023 | Q3 FY2023 | audit truth error | EX-99.1 announces third quarter ended October 28, 2023; audit quote was prior-year comparison language. Companion 10-Q XBRL is Q3 FY2023. |
| DKS | `0001089063-24-000066` | Q1 FY2023 | Q1 FY2024 | Q1 FY2024 | audit truth error | EX-99.1 announces first quarter ended May 4, 2024; audit quote came from a square-footage/history table. Companion 10-Q XBRL is Q1 FY2024. |
| DKS | `0001089063-24-000109` | Q1 FY2023 | Q2 FY2024 | Q2 FY2024 | audit truth error | EX-99.1 announces second quarter ended August 3, 2024; audit quote came from the same historical square-footage table. Companion 10-Q XBRL is Q2 FY2024. |
| DKS | `0001089063-24-000118` | Q1 FY2023 | Q3 FY2024 | Q3 FY2024 | audit truth error | EX-99.1 announces third quarter ended November 2, 2024; audit quote came from the same historical square-footage table. Companion 10-Q XBRL is Q3 FY2024. |
| PVH | `0000078239-25-000084` | Q1 FY2025 | Q3 FY2025 | Q3 FY2025 | audit truth error | EX-99.1 headline announces 2025 third quarter results; audit quote was an impairment/tax reference to first quarter 2025. Companion 10-Q XBRL is Q3 FY2025. |
| CNM | `0001856525-25-000115` | Q1 FY2025 | Q1 FY2024 | Q1 FY2025 | real stale-XBRL miss | EX-99.1 and companion 10-Q both confirm Fiscal 2025 Q1. The prior 10-K used by G2 has `DocumentFiscalYearFocus=2023` despite period-of-report 2025-02-02, so XBRL advance produces Q1 FY2024. |

## PLCE

PLCE is not a disputed yellow row in the canonical simulation:

```text
Tier A/B rows: 7
G2-all correct: 7
G2-all wrong: 0
Tier C excluded row: 1
```

So PLCE should be moved out of "pending audit-truth-error verification" unless another artifact provides a concrete disputed row ID.

## Evidence Checked

- `advance_xbrl_simulation.csv`: identified changed G2 rows marked wrong.
- `master_truth.csv`: old truth label, evidence quote, companion filing metadata.
- `pit_prior_features.csv`: prior periodic basis used by D/G2.
- Cached raw SEC EX-99.1 HTML under `raw_sec/{accession}/`.
- Per-row raw evidence JSON under `tickers/{ticker}/raw_evidence/{accession}.json`.
- CNM prior 10-K raw HTML `raw_sec/0001856525-25-000081/cnm-20250202.htm`.

## Implication For H2

After correcting these rows conceptually:

- ANF/DKS/PVH no longer count against H2/G2.
- CNM still counts as a real unsafe row unless a stale-XBRL sanity guard is added.
- PLCE has no A/B wrong row to resolve.

This makes H2 worth a formal candidate/verifier, but not a direct production patch.

## The "+22 Warm-Start New Wrongs" Claim

I also checked the claim that H2 creates "+22 warm-start new wrongs."

In the canonical local `advance_xbrl_simulation.csv` filtered to Tier A/B rows where H2 would pass and G2-all changes D to wrong AUTO_OK, I find **21** rows, not 22:

```text
GIII: 12 real XBRL-vs-public-FY convention divergences
DKS:   5 audit-truth errors
ANF:   2 audit-truth errors
PVH:   1 audit-truth error
CNM:   1 real stale-prior-XBRL/data-quality miss
PLCE:  0 Tier A/B wrong rows in canonical simulation
```

Interpretation:

- **Raw H2/G2-all is not shippable as-is** because GIII creates real wrong AUTO_OK rows, and CNM exposes stale prior XBRL.
- The non-GIII/non-CNM yellow wrongs are not real resolver misses; they are audit-label errors caused by comparison/history references in the press release.
- A serious H2 candidate should score against a corrected truth table and include a stale-XBRL guard before claiming final accuracy.

`DECISION_FLAG_YELLOW_TICKER_VERIFICATION = h2_promising_with_cnm_stale_xbrl_guard_needed`
