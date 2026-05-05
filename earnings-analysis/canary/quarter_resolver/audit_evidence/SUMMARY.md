# Goal 1.5 SEC EDGAR Audit — Final Summary

**Result**: PASS (199 ok / 0 wrong / 1 unclear out of 200 packets, 0.5% unclear ≤ 5% threshold)
**Date**: 2026-05-05
**Method**: 6 parallel Claude subagents reading SEC EDGAR press release headers and comparing to corpus's `(xbrl.fy, xbrl.q)` claims for each packet.

## Final tally

| Bucket | Count | OK | Wrong | Unclear |
|---|---|---|---|---|
| boundary | 20 | 20 | 0 | 0 |
| denylist_adjacent | 20 | 19 | 0 | 1 |
| q4_10k | 20 | 20 | 0 | 0 |
| week_52_53 | 20 | 20 | 0 | 0 |
| non_dec_fye | 20 | 20 | 0 | 0 |
| random | 100 | 100 | 0 | 0 |
| **TOTAL** | **200** | **199** | **0** | **1** |

## Pass criteria (all met)

- `wrong == 0` ✓
- `unclear ≤ 5%` (≤10 of 200): actual 1 of 200 = 0.5% ✓

## The single unclear

`RH 0001558370-23-000847` (denylist_adjacent bucket): Item 4.02 non-reliance/restatement filing for prior fiscal 2022 quarters. Does not report a current-quarter earnings result. The 8-K's `items` field contains references to "2.02" causing it to pass the eligibility filter, but the filing itself is a restatement notice, not an earnings press release. **Not a corpus defect** — sampling-eligibility edge case for Item 4.02 + 2.02 combinations. Acceptable residual.

## Notes on the random bucket retry (CMCSA et al.)

First-pass output for the random bucket flagged 1 wrong + 5 unclear — all of which were script artifacts (regex/document-ranking gaps in the subagent's automation), NOT corpus errors. The subagent manually re-checked each against SEC EDGAR and confirmed:

| Ticker | Accession | Initial flag | Root cause | Final |
|---|---|---|---|---|
| CMCSA | 0001166691-23-000037 | wrong | Regex matched footnote "first quarter of 2023" | **ok** — headline says "3rd QUARTER 2023" |
| AMTX | 0001437749-23-021759 | unclear | EX-99.1 named `ex_554149.htm` — script missed it | **ok** — "Aemetis Reports Second Quarter 2023" |
| FIVN | 0001288847-25-000080 | unclear | EX-99.1 was a workforce-reduction memo; quarter info in 8-K body | **ok** — body says "quarter ended March 31, 2025" |
| LUV | 0000092380-25-000079 | unclear | Script picked supplemental data file before main earnings doc | **ok** — main doc says "FIRST QUARTER 2025 RESULTS" |
| MIRM | 0001759425-24-000037 | unclear | Doc named `mirm-20241112xexx991.htm` — ranking missed it | **ok** — "Mirum Pharmaceuticals Reports Third Quarter 2024" |
| TXG | 0001770787-25-000058 | unclear | Same naming issue as MIRM | **ok** — "10x Genomics Reports Third Quarter 2025" |

Final verdicts file (`/tmp/quarter_audit/verdicts_random.json`) reflects the manually-confirmed values: 100/0/0.

## FY-alignment cross-checks (the AAP/ACI risk pattern)

Two specific FY-alignment cases were explicitly cross-checked against the company's FYE month:

- **LRCX `0000707549-23-000005`** (non_dec_fye bucket): doc says "Six Months Ended December 25, 2022". LRCX has June FYE → Dec 25 2022 falls in fiscal H1 of FY2023 → reporting Q2 FY2023, matching corpus ✓
- All `week_52_53` bucket packets (20/20): each had explicit `Q<n> Fiscal Year <fy>` headline phrasing matching corpus claim ✓

No FY-alignment defects detected.

## Conclusion

**The ground-truth corpus (9,909 GT rows) is signed off**. Stratified human-style audit on 200 packets across 6 risk-targeted buckets found zero corpus defects. The 1 remaining unclear is a non-earnings-release filing that slipped past the eligibility filter — acceptable residual.

**Goal 1.5 PASS. Ready to proceed to Goal 2** (shadow validator + algorithm proposals).

## Verdict files (artifacts)

- `/tmp/quarter_audit/verdicts_boundary.json` (20/0/0)
- `/tmp/quarter_audit/verdicts_denylist_adjacent.json` (19/0/1)
- `/tmp/quarter_audit/verdicts_q4_10k.json` (20/0/0)
- `/tmp/quarter_audit/verdicts_week_52_53.json` (20/0/0)
- `/tmp/quarter_audit/verdicts_non_dec_fye.json` (20/0/0)
- `/tmp/quarter_audit/verdicts_random.json` (100/0/0, manually re-verified)
- `/tmp/quarter_audit/SUMMARY.md` (this file)
