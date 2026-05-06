# Goal 4 NR AUTO_OK SEC Audit — CLEANED FINAL SUMMARY

> Cleaned ground truth derived from the prior `/tmp/quarter_nr_auto_ok_sec_audit/all_verdicts.json`
> via 10 parallel agent buckets + main-session second-pass programmatic + manual verification.
> Strict policy: **zero false-wrong** is more important than coverage. Any ambiguity → `unclear`.

## Headline counts

- Input rows: **838**
- Output rows: **838** (one row per input accession; no duplicates)

| | prior | cleaned |
|---|---:|---:|
| ok | 141 | 144 |
| wrong | 579 | 587 |
| unclear | 118 | 107 |
| **total** | **838** | **838** |

## Verdict transitions

| prior → cleaned | count |
|---|---:|
| ok → ok | 126 |
| ok → unclear | 14 |
| ok → wrong | 1 |
| unclear → ok | 12 |
| unclear → unclear | 71 |
| unclear → wrong | 35 |
| wrong → ok | 6 |
| wrong → unclear | 22 |
| wrong → wrong | 551 |

- Prior `wrong` rows downgraded to `unclear`: **22**
- Prior `wrong` rows reverted to `ok`: **6**
- Prior `unclear` rows promoted to `wrong`: **35**
- Prior `ok` rows flipped to `wrong`: **1**

## Per-resolver-source breakdown (cleaned)

| resolver_source | n | ok | wrong | unclear | wrong % |
|---|---:|---:|---:|---:|---:|
| `prior_periodic_projection_q1_to_q2` | 199 | 24 | 156 | 19 | 78.4% |
| `prior_periodic_projection_q1_to_q2_effective_fye_from_prior_10k` | 3 | 2 | 0 | 1 | 0.0% |
| `prior_periodic_projection_q2_to_q3` | 178 | 14 | 146 | 18 | 82.0% |
| `prior_periodic_projection_q2_to_q3_effective_fye_from_prior_10k` | 3 | 2 | 0 | 1 | 0.0% |
| `prior_periodic_projection_q3_to_q4` | 189 | 23 | 145 | 21 | 76.7% |
| `prior_periodic_projection_q4_to_q1` | 263 | 77 | 140 | 46 | 53.2% |
| `prior_periodic_projection_q4_to_q1_effective_fye_from_prior_10k` | 3 | 2 | 0 | 1 | 0.0% |

## Wrong-row mismatch shape

| shape | count |
|---|---:|
| Q+1 same FY (resolver advanced one quarter) | 272 |
| FY+1 same Q (FY-naming drift) | 235 |
| Q4→Q1 boundary +1Q +1FY | 77 |
| other dfy=2 dq=0 | 1 |
| other dfy=0 dq=-1 | 1 |
| other dfy=0 dq=2 | 1 |

Two dominant classes confirmed:
1. **Q-projection bug** — resolver advanced one quarter past actual reporting quarter. Classic pattern: 8-K is for Q3, resolver labels it Q4 (or wraps Q4→Q1+1FY).
2. **FY-naming drift** — issuer states "fiscal 2023", resolver writes FY2024 (year-of-end vs. year-of-start). Concentrated in retailers/apparel with January/February FY-end.

## False prior `wrong` rows downgraded by second-pass to `unclear`

Second-pass found **22** prior-wrong rows whose evidence was insufficient under strict rules:
- pattern-matched fragments without both quarter token and fiscal year in the same current-period sentence,
- year-only headlines on annual releases (e.g. CON EDISON "REPORTS 2022 EARNINGS" — calendar-year filer where the resolver advanced to next-year Q1),
- chosen quote came from a "compared to" / "prior year" / outlook context rather than a current-period sentence.

Examples of the eight rows that came from comparative or year-only text and were demoted to `unclear`:

| accession | ticker | prior quote (problematic) | downgrade reason |
|---|---|---|---|
| `0001018840-24-000012` | ANF | "basis. The additional week in fiscal 2023 benefited fourth quarter net sales by" | compared-to context, headline lacks year |
| `0001018840-25-000007` | ANF | "In fiscal 2024, we once again delivered (CEO body quote)" | CEO body quote lacks quarter token |
| `0001018840-26-000006` | ANF | "early January. Reflecting on fiscal 2025 (CEO body quote)" | CEO body quote lacks quarter token |
| `0001047862-23-000042` | ED | "REPORTS 2022 EARNINGS" | year-only headline, no Q4 explicit |
| `0001047862-24-000013` | ED | "REPORTS 2023 EARNINGS" | year-only headline, no Q4 explicit |
| `0001047862-25-000014` | ED | "REPORTS 2024 EARNINGS" | year-only headline, no Q4 explicit |
| `0001089063-25-000112` | DKS | "FY 2025 Guidance" | guidance/outlook fragment, not current-period |
| `0001104659-23-026119` | QURE | "Announces 2022 Financial Results" | year-only headline, no Q4 explicit |

## Examples of comparative-text false matches in prior verdicts

The prior audit's pattern-matcher could grab any "Q1 2022" / "first quarter of fiscal 2024" string anywhere in the document, even when the surrounding sentence said "compared to" or "in the prior year". The strict re-audit explicitly rejects matches whose preceding 180 characters contain comparison triggers (`compared to`, `prior year`, `vs.`, `year-over-year`, etc.). Where this rejection caused a verdict change, the row is now `unclear`.

## High-confidence real wrong classes

**587 clean wrong rows** survived second-pass programmatic verification. Each carries:
- non-empty `cleaned_audited_fy` and `cleaned_audited_q`,
- a verbatim 3–25-word `evidence_quote` that contains BOTH a quarter ordinal/Q-token AND the fiscal year exactly as stated by the issuer,
- the quote appears verbatim in the cached SEC raw text, and is not preceded (in the headline area) by a comparison trigger.

Top tickers by clean wrong count (≥10):

| ticker | wrong rows |
|---|---:|
| URI | 14 |
| LEVI | 13 |
| VNO | 13 |
| UTHR | 13 |
| AR | 13 |
| AWK | 13 |
| LAND | 13 |
| LOW | 12 |
| OXM | 12 |
| PVH | 12 |
| DLTR | 12 |
| BURL | 12 |
| DKS | 12 |
| ULTA | 12 |
| FIVE | 12 |
| KSS | 12 |
| GME | 12 |
| LULU | 12 |
| GRPN | 12 |
| BJ | 12 |
| CHWY | 12 |
| ASO | 12 |
| CNM | 12 |
| TEX | 11 |
| AYI | 11 |
| RH | 10 |
| OLLI | 10 |
| PINC | 10 |
| HTZ | 10 |

## Recommendation for Goal 5 verifier

Use this cleaned ground truth to gate the Goal 5 production verifier **only against rows where `final_verdict ∈ {ok, wrong}`**. Skip `unclear` rows entirely:

1. **OK rows (n=144)** — resolver claim verified by clean current-period SEC headline. Safe positive examples.
2. **Wrong rows (n=587)** — resolver claim contradicted by clean current-period SEC headline. The verifier MUST NOT AUTO_OK these. Negative examples for any classifier or rule check.
3. **Unclear rows (n=107)** — insufficient evidence under strict rules. Do NOT use as ground truth in either direction.

Concrete actions:
- The Goal 4 resolver `prior_periodic_projection_q*` (without `_effective_fye_from_prior_10k`) reliably mislabels both Q-projection and FY-naming drift cases. Goal 5 verifier should require explicit confirmation from the EX-99.1 / EX-99 / 8-K body current-period header before flipping `needs_review` → `auto_ok`.
- Per-issuer FY-naming convention table (year-of-start vs year-of-end) is needed for retail/apparel/Jan-FY-end issuers — without it the `FY+1 same Q` class continues to produce wrong labels for issuers like ANF, BJ, BURL, CHWY, DKS, DLTR, FIVE, GME, KSS, LEVI, LOW, LULU, OXM, PVH, ROST, ULTA.
- Non-earnings 8-Ks with Item 2.02 (Investor Day, share repurchase, M&A, recast, segment realignment, leadership transition) should be excluded from AUTO_OK by gating on explicit ordinal-quarter mention in the EX-99 headline.
- Annual-only releases with year-only headlines (e.g. CON EDISON "REPORTS 2024 EARNINGS") cannot be safely auto-classified by header alone — route via `_effective_fye_from_prior_10k` or keep as needs_review.

## Process notes

- 10 parallel review subagents, ~84 rows each, deterministic accession-sorted bucketing.
- Each subagent applied the same strict critical-evidence rules and emitted JSON to `agent_outputs/bucket_NN.json`.
- Main session aggregated, then ran a programmatic second-pass over every `wrong` row checking: verbatim-in-raw, Q+FY tokens present in quote, FY value appears in quote text, q-token matches `cleaned_audited_q`, no comparison trigger immediately preceding the quote (within 180 chars, except for headline-area quotes).
- 14 wrong rows failed those checks: 8 downgraded to `unclear` (false-wrong avoidance), 6 had their `evidence_quote` replaced with a verbatim headline (verdict kept).
- Manual re-check of the 1 `ok→wrong` flip (ARWR fiscal-Q2 mislabeled by resolver as fiscal-Q3) and the 6 `wrong→ok` flips (TOL, ROP, AIR, WDAY×3): all verified correct directly from cached raw text headlines.
- 20 random `ok` rows spot-checked; 1 (EW Q1 FY2026) had its quote refined to the headline+dateline form for explicit Q+FY co-presence; verdict unchanged.

## Files
- `cleaned_all_verdicts.json` — 838 rows in required schema
- `CLEANED_SUMMARY.md` — this file
- `validation_report.txt` — programmatic validation output
- `buckets/bucket_NN.json` — per-bucket inputs to subagents
- `agent_outputs/bucket_NN.json` — per-bucket subagent outputs
- `agent_aggregate_pre_second_pass.json` — pre-second-pass aggregate
- `agent_aggregate_post_second_pass.json` — post-second-pass aggregate
- `wrong_pass_issues.json` — programmatic-check issues that drove second-pass adjustments
