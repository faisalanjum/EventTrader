# Goal 6a Measurement Report

Goal 6a is measurement-only. No production files under `scripts/earnings/` are modified by these artifacts.

## Table 1 - D Measurement By Subset

| subset | rows | correct_AUTO_OK | wrong_AUTO_OK | fail_closed | correct_pct | wrong_pct | fc_pct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full historical | 10674 | 9491 | 24 | 1159 | 88.916995% | 0.224845% | 10.858160% |
| Warm-start | 9878 | 9491 | 24 | 363 | 96.082203% | 0.242964% | 3.674833% |
| Cold-start | 796 | 0 | 0 | 796 | 0.000000% | 0.000000% | 100.000000% |
| Latest-per-ticker | 781 | 747 | 3 | 31 | 95.646607% | 0.384123% | 3.969270% |

## Table 2 - E Measurement By Subset

| subset | rows | correct_AUTO_OK | wrong_AUTO_OK | fail_closed | correct_pct | wrong_pct | fc_pct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full historical | 10674 | 9446 | 20 | 1208 | 88.495409% | 0.187371% | 11.317219% |
| Warm-start | 9878 | 9446 | 20 | 412 | 95.626645% | 0.202470% | 4.170885% |
| Cold-start | 796 | 0 | 0 | 796 | 0.000000% | 0.000000% | 100.000000% |
| Latest-per-ticker | 781 | 745 | 2 | 34 | 95.390525% | 0.256082% | 4.353393% |

## Table 3 - D vs E Delta

| subset | d_correct_pct | e_correct_pct | delta_correct_pct_e_minus_d | d_wrong_pct | e_wrong_pct | delta_wrong_pct_e_minus_d |
|---|---:|---:|---:|---:|---:|---:|
| Full historical | 88.916995% | 88.495409% | -0.421585% | 0.224845% | 0.187371% | -0.037474% |
| Warm-start | 96.082203% | 95.626645% | -0.455558% | 0.242964% | 0.202470% | -0.040494% |
| Cold-start | 0.000000% | 0.000000% | 0.000000% | 0.000000% | 0.000000% | 0.000000% |
| Latest-per-ticker | 95.646607% | 95.390525% | -0.256082% | 0.384123% | 0.256082% | -0.128041% |

## Notes

Candidate D is measured as a research-only reconstruction using the allowed 24h and 150d thresholds.
Candidate E is a research-only policy comparison and is not a shipping candidate.

## Decision Flags

DECISION_FLAG_D_CLEANED_NR_WRONG_FAIL_CLOSED = 234
DECISION_FLAG_D_CLEANED_NR_WRONG_NOW_CORRECT = 330
DECISION_FLAG_D_CLEANED_NR_WRONG_STILL_WRONG = 23
DECISION_FLAG_D_COLD_START_CORRECT = 0
DECISION_FLAG_D_COLD_START_FC = 796
DECISION_FLAG_D_COLD_START_WRONG = 0
DECISION_FLAG_D_FULL_HISTORICAL_CORRECT = 9491
DECISION_FLAG_D_FULL_HISTORICAL_FC = 1159
DECISION_FLAG_D_FULL_HISTORICAL_WRONG = 24
DECISION_FLAG_D_GOAL4_BASELINE_PRESERVED = 9052
DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_FC = 63
DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_WRONG = 1
DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT = 747
DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT_PCT = 95.646607
DECISION_FLAG_D_LATEST_PER_TICKER_FC = 31
DECISION_FLAG_D_LATEST_PER_TICKER_WRONG = 3
DECISION_FLAG_D_LATEST_PER_TICKER_WRONG_PCT = 0.384123
DECISION_FLAG_D_WARM_START_CORRECT = 9491
DECISION_FLAG_D_WARM_START_CORRECT_PCT = 96.082203
DECISION_FLAG_D_WARM_START_FC = 363
DECISION_FLAG_D_WARM_START_WRONG = 24
DECISION_FLAG_D_WARM_START_WRONG_PCT = 0.242964
DECISION_FLAG_E_COLD_START_CORRECT = 0
DECISION_FLAG_E_COLD_START_FC = 796
DECISION_FLAG_E_COLD_START_WRONG = 0
DECISION_FLAG_E_FULL_HISTORICAL_CORRECT = 9446
DECISION_FLAG_E_FULL_HISTORICAL_FC = 1208
DECISION_FLAG_E_FULL_HISTORICAL_WRONG = 20
DECISION_FLAG_E_LATEST_PER_TICKER_CORRECT = 745
DECISION_FLAG_E_LATEST_PER_TICKER_FC = 34
DECISION_FLAG_E_LATEST_PER_TICKER_WRONG = 2
DECISION_FLAG_E_WARM_START_CORRECT = 9446
DECISION_FLAG_E_WARM_START_FC = 412
DECISION_FLAG_E_WARM_START_WRONG = 20
DECISION_FLAG_SHIP_D_DIRECTLY = yes
