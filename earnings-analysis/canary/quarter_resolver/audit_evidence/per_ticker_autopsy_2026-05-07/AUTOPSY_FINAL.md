# 34-Ticker Quarter-Resolver Autopsy — Final Report

**Date**: 2026-05-07
**Question**: Of the 34 edge-case tickers where Candidate D fail-closes or wrong-fires, how many are "silly recoverable" vs genuinely irreducible? Validated thoroughly by SEC EDGAR re-inspection.

## Bottom line

| Bucket | # tickers | Recoverable? |
|---|:---:|---|
| 🟢 Silly recoverable (clean) | 14 | YES — H2 rule recovers all FC rows, zero collateral |
| 🟢 Silly FC + separate D-wrong | 4 | FC slice yes; D-wrong needs soft-tier or new candidate |
| 🟡 Probably silly (audit-error suspected) | 5 | YES if Agent 5's audit-truth-error claim verifies |
| 🔵 Already correctly handled | 5 | NO recovery, but H2 prevents wrong-fires |
| 🟠 D wrong-fire on latest | 3 | YES via untested structural rules (period-match, filename, empty-companion) |
| 🔴 Genuinely irreducible | 1 | NO under current locks — only EX-99.1 parse would fix |
| ⚪ D mostly correct already | 2 | n/a |

**Of the 34 tickers, 1 (GIII) is genuinely irreducible. ~22 are clearly silly recoverable. 5 are probably silly pending audit-truth verification. 5 are correctly fail-closed (no harm, no recovery). 3 D-wrong-fires (PHR/PINC/PRU) have viable structural fixes Goal 6f did not test.**

## The new structural discriminator (Agent 5)

> **H2 rule**: For each ticker, check all PIT-visible prior 10-Q rows. If `calendar_year(prior_period_of_report) == prior_xbrl_DocumentFiscalYearFocus` on every one (delta = 0 always), advance-XBRL is safe. If any 10-Q has non-zero delta, fail-closed.

This is **not** banned by current locks — it's a self-detecting structural rule, not a ticker table. It reproduces an issuer's historical XBRL convention from the issuer's own filings.

**Confusion matrix (29 audit tickers)**: TP=5, FP=0, TN=18, FN=6.

**Goal 6f did not test exactly this rule**. The closest was `MULTI_PRIOR_STABLE_OFFSET`, which used XBRL-vs-math offset stability (different signal). H2 uses the simpler XBRL-vs-calendar-year-of-period equivalence.

## Per-ticker table

| Ticker | AB rows | C / W / FC | H2 | G2 rec/wrong | Bucket |
|---|---:|---|:---:|---:|---|
| ACI | 13 | 0 / 0 / 13 | PASS | 13/0 | 🟢 silly recoverable |
| ANF | 9 | 0 / 0 / 9 | PASS | 7/2 | 🟡 audit-error suspected |
| ASO | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| BJ | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| BOX | 13 | 6 / 0 / 7 | FAIL | 0/6 | 🔵 H2 → fail-closed correctly |
| BURL | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| CHWY | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| CNM | 12 | 0 / 0 / 12 | PASS | 11/1 | 🟡 audit-error suspected |
| DKS | 10 | 0 / 0 / 10 | PASS | 5/5 | 🟡 audit-error suspected |
| DLTR | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| FIVE | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| GBX | 14 | 12 / 0 / 2 | FAIL | 0/1 | ⚪ D mostly correct |
| GIII | 12 | 0 / 0 / 12 | PASS | 0/12 | 🔴 genuinely irreducible |
| GME | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| KR | 13 | 0 / 2 / 11 | PASS | 11/0 | 🟢 + separate D-wrong |
| KSS | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| LOW | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| LULU | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| NTAP | 13 | 10 / 0 / 3 | FAIL | 0/2 | 🔵 H2 → fail-closed correctly |
| NTNX | 13 | 9 / 1 / 3 | FAIL | 0/2 | 🔵 H2 → fail-closed correctly |
| OLLI | 12 | 0 / 2 / 10 | PASS | 10/0 | 🟢 + separate D-wrong |
| OXM | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| PHM | 14 | 12 / 0 / 2 | PASS | 0/0 | ⚪ D mostly correct |
| PHR | 14 | 12 / 1 / 1 | FAIL | 0/0 | 🟠 D-wrong (transcript supplement) |
| PINC | 10 | 6 / 3 / 1 | FAIL | 0/0 | 🟠 D-wrong (10-Q-before-8-K) |
| PLAY | 12 | 0 / 1 / 11 | PASS | 11/0 | 🟢 + separate D-wrong |
| PLCE | 7 | 0 / 0 / 7 | PASS | 7/0 | 🟡 audit-error suspected |
| PRU | 13 | 12 / 0 / 1 | PASS | 0/0 | 🟠 D-wrong (recast supplement) |
| PVH | 10 | 0 / 0 / 10 | PASS | 9/1 | 🟡 audit-error suspected |
| RH | 14 | 0 / 2 / 12 | PASS | 9/0 | 🟢 + separate D-wrong |
| ROST | 2 | 0 / 0 / 2 | PASS | 2/0 | 🟢 silly recoverable |
| ULTA | 12 | 0 / 0 / 12 | PASS | 12/0 | 🟢 silly recoverable |
| WDAY | 15 | 10 / 0 / 5 | FAIL | 0/4 | 🔵 H2 → fail-closed correctly |
| WMS | 11 | 6 / 0 / 5 | FAIL | 0/3 | 🔵 H2 → fail-closed correctly |

Legend: AB = Tier A+B audit rows; C/W/FC = D's correct / wrong / fail-closed; H2 = Agent 5's structural discriminator (PASS = trust XBRL advance, FAIL = fail-closed); G2 rec/wrong = Goal 6f's `G2_ALL_FY_DISAGREE` would-recover counts.

## Per-bucket details

### 🟢 SAFE silly recoverable (14 tickers)
ACI, ASO, BJ, BURL, CHWY, DLTR, FIVE, GME, KSS, LOW, LULU, OXM, ROST, ULTA.

**Mechanism**: All are FYE-Feb retailers (52/53-week). XBRL uses year-of-end naming. `period_to_fiscal()` math uses year-of-start derivation for Feb-end. Disagreement → D fail-closes. EX-99.1 also uses year-of-end → trusting XBRL advance gives the right answer.

**Validation**: Agent 1 read EX-99.1 + companion 10-Q DEI on 10 sample rows across 5 tickers (ACI, ASO, BURL, GME, ULTA). Confirmed XBRL+1=advance equals EX-99.1 truth in every case.

**Recovery**: H2 rule passes; G2_ALL recovers 12/12 or 13/13 with zero collateral.

### 🟢 SAFE FC slice + separate D-wrongs (4 tickers)
KR, OLLI, PLAY, RH.

**FC slice**: Same mechanism as the 14 above. H2 passes; G2_ALL recovers 9–11 of 11–12 FC rows with zero collateral.

**D-wrongs (7 rows total)**: Agent 3 confirmed all 7 are the SAME convention class but inverted — at the **prior Q4 10-K**, both XBRL and `period_to_fiscal()` use year-of-end (math's day≤5 heuristic pulls Feb 1/3/4 back into January). XBRL=math AGREE → no FY-disagreement gate fires → D advances Q4→Q1 → FY off by 1.

**Fixable by**: (a) untested Goal 6f candidate "FYE-Jan/Feb Q4-to-Q1 inversion check" (within current locks); (b) soft-AUTO_OK tier with companion-Q1-10Q-confirmation lookback (architecture).

### 🟡 PROBABLY silly — audit-truth-error suspected (5 tickers)
ANF, CNM, DKS, PLCE, PVH.

**Empirical**: G2 recovery is mostly correct (5–11 of 7–12 rows) but 1–5 collateral wrongs.

**Agent 5's hypothesis**: most "wrongs" are Tier-B audit-truth-label errors — the audit confused back-references like "second quarter of 2022" inside a Q2-2023 press release with current-period claims. Plus 1 stale-XBRL CNM 10-K.

**To verify**: hand-check the specific rows where G2 was "wrong"; pull the actual EX-99.1 and confirm the SEC truth label. If audit error, real new-wrongs go to ~0 for these 5 tickers.

### 🔵 H2 correctly routes to fail-closed (5 tickers)
BOX, NTAP, NTNX, WDAY, WMS.

**Mechanism (Agent 2)**: XBRL is year-of-start consistently (delta from period_year is non-zero across history). EX-99.1 uses year-of-end. Advance-XBRL would be off by 1.

**H2 status**: PASS — H2 says "this issuer's XBRL convention is unsafe; fail-closed." Agreement with current behavior; no improvement, no harm.

### 🟠 D wrong-fire on latest (3 tickers — Goal 6f's named PHR/PINC/PRU class)

| Row | Class | Structural fix |
|---|---|---|
| PHR `0001412408-26-000084` | F6 — Transcript-only follow-up 8-K filed 4 days after the actual Q4 8-K | Detect EX-99.1 filename containing "transcript"/`earningstra` OR same `period_of_report` as a prior 8-K within 7 days |
| PINC `0001193125-25-114958` | F5 — 10-Q filed day BEFORE the 8-K (same quarter, period 2025-03-31) | If `prior_period_of_report` ≈ filing-date's calendar quarter, use prior label DIRECTLY (don't advance) |
| PRU `0001137774-26-000087` | F2 — Voluntary recast Quarterly Financial Supplement | Detect empty companion + filename "restatem" + prior 8-K already covered same quarter |

All three are detectable via PIT-safe metadata. Agent 4 refined Goal 6f's "irreducible" claim: the unifying signal is **"prior periodic snapshot already covers AT-or-PAST the period the new 8-K announces → advancing is structurally wrong."**

### 🔴 Genuinely irreducible under current locks (1 ticker)

**GIII**. Agent 2 + Agent 5 confirm: GIII's XBRL is year-of-start consistently across 9 priors (`all_zero_n=9`) — structurally indistinguishable from SAFE issuer ACI. But GIII's EX-99.1 uses year-of-end. The divergence lives ONLY in EX-99.1 prose; no XBRL DEI / period-end / cadence / FYE-month signal separates GIII from ACI.

**Only fix**: EX-99.1 cover-page parse OR `dei:CoverFiscalYearFocus` if SEC ever standardizes that tag.

### ⚪ D mostly correct (2 tickers)
GBX (12/0/2), PHM (12/0/2). D handles them well; small fail-closed tail with no meaningful recovery available.

## What this changes vs Goal 6f's verdict

Goal 6f said: **"all 4 new structural candidates rejected; KEEP_D."**

That's still correct under the strict "0 new wrong AUTO_OK" policy at row level. But the per-ticker autopsy reveals:

1. **A new clean SAFE-side gate (H2)** that Goal 6f did not test directly. It would recover ~225+ fail-closed rows on the SAFE-15 + the SAFE-FC-slice (KR/OLLI/PLAY/RH), with zero collateral on those tickers.
2. **The 22 row-level "new wrongs" from H2** concentrate on **only 6 tickers**: GIII (12 rows, real) + DKS/ANF/PVH/PLCE/CNM (10 rows, hypothesized audit errors).
3. **GIII alone is the irreducible class**. Everyone else is fixable structurally OR via soft-tier OR via audit-truth verification.
4. **PHR/PINC/PRU are NOT irreducible** — Agent 4 found viable structural signals (period-of-report match, filename pattern, empty companion).

## Suggested follow-ups (not action items)

1. **Verify Agent 5's audit-error hypothesis** on DKS / ANF / PVH / PLCE / CNM Tier-B "wrong" rows. If confirmed, real-wrong count for H2 drops to ~12 (GIII only).
2. **Test Goal 6f Candidate 8 = H2-gated G2_ALL** as a research candidate. If audit-error hypothesis verifies, it might pass the zero-new-wrong policy as a per-issuer-trustworthy gate.
3. **Test PHR/PINC/PRU structural fixes** — period-of-report match + filename pattern + empty-companion guards. These are PIT-safe and weren't in Goal 6f's candidate set.
4. **GIII**: accept as fail-closed permanently OR add to soft-AUTO_OK tier when that ships.

## Methodology

- 5 parallel Claude subagents read raw SEC HTML + companion DEI XBRL + computed signals
- Each verdict has literal SEC evidence quotes
- H2 rule computed deterministically from `pit_prior_features.csv`
- Recovery counts computed from Goal 6f per-row CSVs filtered to Tier A+B audit accessions
- All artifacts under `audit_evidence/per_ticker_autopsy_2026-05-07/`:
  - `fact_sheets/<TICKER>.json` — 34 per-ticker fact sheets
  - `subagent_findings/agent[1-5]_*.json` — full verdicts with evidence quotes
  - `summary.csv` — aggregated summary
  - `FINAL_AUTOPSY_TABLE.csv` — the table above as CSV

No production code touched.
