# RESTORE CONTEXT — Quarter Identity Resolver

Last updated: 2026-05-07

You are resuming a long quarter-resolver investigation in
`/home/faisal/EventMarketDB`. Read this file first, then read the running plan
at `.claude/plans/quarter-identity-resolver.md` and the safety contract at
`.claude/plans/refactor-safety-contract.md`. Do not re-litigate locked
decisions unless the user explicitly asks.

## Current State (TL;DR)

**Candidate D has shipped to production. Guidance fallback hardened. Goal 6f
research-only structural-discovery probe is running in Codex.**

- Latest local HEAD: `0552fd9` (Goal 6f audit-evidence inputs registered after verifier passed)
- Pushed to `origin/main` (HEAD == origin/main on the quarter-resolver branch)
- **Goal 6f COMPLETE**: verifier exited 0; `DECISION_FLAG_GOAL6F_RECOMMENDATION = KEEP_D`. All 4 new structural candidates rejected. D is the empirical structural ceiling under current locks + current data pipeline.
- Goal 6c production commit: `a61636a` (`scripts/earnings/quarter_identity.py` Candidate D guards)
- Goal 6c wording cleanup: `2f61810`
- Goal 6e guidance fallback: `be4c2cc` (`scripts/harvest_guidance_sessions.py` XBRL-first 10-Q/10-K fallback)
- Goal 6a measurement docs: `7f5ff25`
- Goal 6a artifacts: `230789f`
- Goal 5 NR audit + verifier + cleaned verdicts: `6e715d5`
- Goal 4 production code (still load-bearing through 6c): `e43cfc8`
- Goal 4 test rewrite: `5ff1619`
- Restore-context post-Goal-4: `9f263ac`

NOT yet:

- Production-deployed to running services. The k8s `extraction-worker`,
  earnings orchestrator pods, MCP servers etc. are still pulling whatever
  image was built before Goal 6c. They will pick up D + Goal 6e only after a
  fresh container build/rollout.
- `pre-goal6f-pending` stash (`stash@{0}`) popped. Goal 6f finished 2026-05-07
  in 1668s.
- 34-ticker SEC ground-truth audit converted into production code. Result
  was `DECISION_FLAG_RULE_G2 = promising_but_not_shippable`.

The FCX bug remains structurally fixed; nothing in 6c/6e/6f weakens the
guards Goal 4 introduced.

```
0000831259-26-000021 → Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1
```

## What changed since Goal 4 (compaction-safe summary)

Goal 4 closed the FCX class. Goal 5 then discovered Goal 4 had a *separate*
hole on rows it considered out-of-scope (NR AUTO_OK), which led to Goals
6a→6c→6e→6f. Read this section once and you can navigate the rest of the doc.

1. **Goal 5 found the NR-AUTO_OK hole**: Goal 4's "0 WRONG" was on its 9,943
   oracle-scored rows, NOT the 838 NR rows where Goal 4's resolver still
   *fired* AUTO_OK. SEC audit of those 838 rows showed **587 wrong-fires /
   144 correct / 107 unclear**. Goal 4 looked like a 100% precision win
   because it was scored only on rows where it *had* an oracle.
2. **Goal 5 ALSO surfaced ~7 candidate algorithms** (A-G plus variants).
   Codex tried Candidate E (light industry classifier) and it was rejected
   for violating the "no ticker / no industry / no SIC tables" lock.
3. **Goal 5 ended without shipping production code.** Cleaned verdicts
   live at `audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json`.
4. **Goal 6a measured Candidate D** (best lock-respecting candidate from
   Goal 5) on full corpus + warm-start + cold-start + latest-per-ticker.
   D met the ship bar: warm-start 96.08% correct / 0.24% wrong / 3.67%
   fail-closed; latest-per-ticker 95.65% correct / 0.38% wrong / 3.97%
   fail-closed. `DECISION_FLAG_SHIP_D_DIRECTLY = yes`.
5. **Goal 6c shipped D into `quarter_identity.py`.** Five new
   calendar-branch structural guards. Verifier exit 0; full pytest 1417
   passed; G8 per-row exact match against `goal6a_d_measurement.csv` on all
   10,674 rows. Push to origin.
6. **Goal 6e hardened the guidance 10-Q/10-K fallback** in
   `harvest_guidance_sessions.py`. Single extended Cypher returning
   accession + report_id + accession_no + XBRL DEI fields; XBRL-first with
   triple-check denylist (defends against schema drift) and
   `should_use_xbrl_fiscal` proximity guard before falling through to the
   existing math fallback. 61/61 tests pass.
7. **34-ticker SEC ground-truth audit** ran in parallel (separate Claude
   session). 408 rows × 34 tickers (the 31 D-fail-close + 3 D-wrong-fire
   "edge" tickers from Goal 6a's latest-per-ticker subset). Tier A+B
   coverage 400/408 = 98.0%. **`DECISION_FLAG_RULE_G2 = promising_but_not_shippable`**:
   G2-calendar-only flips 221 D-fail-closes to correct AUTO_OK but creates
   **37 new wrong AUTO_OK**; G2-all-fy-disagreement creates **39 new wrong
   AUTO_OK**. Empirical reason: iXBRL `DocumentFiscalYearFocus` uses
   year-of-start while EX-99.1 press releases use year-of-end on the
   off-calendar filers (GIII, BOX, WDAY, WMS, NTAP, NTNX, DKS, ANF). They
   *disagree* for the same filing.
8. **Goal 6f is research-only structural discovery beyond D.** Phase A
   demands a 9-section, ≥500-word `GOAL6F_FAILURE_MODEL.md` listing
   IRREDUCIBLE_CLASSES vs TRACTABLE_CLASSES with EVIDENCE_ROWS citations.
   Phase B requires ≥3 new structural candidates citing
   TARGET_FAILURE_CLASS, no production code touched. `KEEP_D` is a
   valid outcome and ~70% expected. Verifier has 8 gates incl. banned
   patterns (industry/sector/SIC/GICS/NAICS/CIK/EX-99/HTTP/ML/LLM/PIT-violation),
   D-baseline byte-match, shippable gate.

## The architectural finding that closes most "is there more left" questions

**iXBRL year-of-start vs EX-99.1 year-of-end divergence** is the irreducible
structural class for off-calendar (non-December FYE) filers.

- iXBRL `DocumentFiscalYearFocus` for an issuer with FYE January is filed
  under year-of-start convention: a 10-K covering Feb 2024 – Jan 2025 reports
  `FY=2024`.
- The same issuer's EX-99.1 press release announces the same period as
  `FY 2025` because the fiscal year *ends* in 2025.
- Both labels are "correct" for their audience but disagree on the wire.
- Any production rule that trusts `FY` from XBRL (G2 / advance-XBRL) will
  systematically wrong-write the year for these filers (~10% of issuers).
- D's "fail closed on FY disagreement" guard is what keeps wrong-writes near
  zero for this class — at the cost of fail-closed coverage.

What this means going forward:

- Under the locked constraints (no ticker tables, no industry classifiers,
  no SIC/GICS/NAICS dispatch, no EX-99.1 parsing in production, no external
  HTTP, no ML/LLM, no time thresholds beyond 24h/150d), **D is at or very
  near the structural ceiling**.
- The remaining ~4.4% of the universe (34/781 tickers as the latest-per-
  ticker proxy) cannot be auto-resolved structurally without one of the
  banned mechanisms. They must remain fail-closed.
- Goal 6f is checking whether *any* lock-respecting structural candidate
  beats D. Most likely outcome: `KEEP_D` (estimated ~70%). `SHIP_CANDIDATE`
  outcome would require a 9-section failure-model proof + per-row CSV
  byte-match against D + zero new wrong AUTO_OK.

## Goal Outcomes (chronological)

### Goal 1 — Ground Truth Corpus (commit fc83a1c)

Status: done and verifier-passed.

- Universe: 10,831 earnings 8-Ks
- GT: 9,909 rows (two-source agreement: same-event periodic XBRL == fiscal_math)
- NR: 922 rows
- NR breakdown: not_same_event_periodic 495, xbrl_math_disagree 391, proximity_rejected 26, denylist 6, no_xbrl 4, no_fye 0

**Important nuance**: Goal 1 GT is *high-confidence two-source agreement*,
NOT all manually SEC-read truth. Do not call every GT row "human/SEC audited".

### Goal 1.5 — Stratified SEC Audit (commits f2a0eb6, 04789af)

Status: done, PASS (199/200 ok, 0 wrong, 1 unclear).

The unclear row was RH 0001558370-23-000847 — Item 4.02 non-reliance/restatement.

### Goal 2 — Shadow Validator (commits b909a3f → 0813df2 → 72a7668 → dea1ef5)

Status: done and verifier-passed.

Production-today metrics on 10,831 rows:
- 9,909 GT-AGREE / 0 GT-BUG / 0 GT-NO_RESOLUTION
- **492 WRONG_AUTO_WROTE on `not_same_event_periodic`** — the FCX harm count
- 430 AUTO_ON_UNCERTAIN_ROW
- 0 CORRECT_FAIL_CLOSED (production never failed closed)

### Goal 3 — Live-Mode Candidate Benchmark (commit 0ae4d0e)

Status: done.

`prior_periodic_projection` selected as best current candidate; achievability
NO at 99.9% bar. Warm-start fire rate 98.67%, latest-per-ticker 97.95%.

**8-K periodOfReport probe**: 91.1% of 8-K `periodOfReport` exactly equal the
filing date (event-date semantics, NOT fiscal-period semantics).
**Conclusion: do NOT use 8-K periodOfReport as a quarter-end signal.**

### Goal 4 — Production Implementation (commit e43cfc8)

Status: done and verifier-passed.

Production files modified:
- `scripts/earnings/quarter_identity.py` (~80% rewrite, 740 lines)
- `scripts/earnings/earnings_orchestrator.py` (+65 lines for write-guard)
- `scripts/earnings/test_quarter_identity.py` (+227 lines)

Algorithm structure: prior_periodic_projection (Goal 3 byte-faithful) with
exactly one substitution — odd_52_53 branch → Rule F.

Rule F:
- prior <24h before 8-K → use prior XBRL FY/Q directly
  (`rule_f_direct_recent_prior`) — handles PEP/LEVI same-event pattern
- elif XBRL_FY ≠ math_FY → FAIL_CLOSED
  (`rule_f_fail_closed_fy_disagreement`) — handles KR/NTAP/SYNA naming
- else → advance XBRL FY/Q (`rule_f_advance_xbrl`) — handles AAP/PSTG

Orchestrator destructive-write guard (`enforce_quarter_identity_write_guard`)
refuses event-directory writes unless `safety_action == "AUTO_OK"`.

`_STALE_MATCH_DAYS=150` is gone. No ticker allowlists, denylists, or
per-issuer FY tables. Rule F is structural-only.

### Goal 4 verifier sign-off

Hand-written through 7 ChatGPT critique rounds. Key gates:
- G5 (115 odd_52_53): exactly 94 OK / 0 WRONG / 21 FAIL_CLOSED
- G6 (FCX): Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1
- G7 FULL: 9,116 OK / 0 WRONG / 827 FAIL_CLOSED on 9,943 oracle rows
- G7b: 9,860 / 9,860 firing rows preserved (no silent coverage shrink)
- G8/G9 pytest passes, including write-guard

### Goal 5 — NR AUTO_OK SEC audit (commit 6e715d5)

Status: research-only artifact + verifier; no production change.

`audit_evidence/sec_nr_auto_ok_audit/` holds 838-row claims set + cleaned
verdicts (10-bucket parallel review). Result: **144 ok / 587 wrong / 107
unclear** on rows where Goal 4's resolver fires AUTO_OK without an oracle.
This is what triggered Goals 6a→6c.

Goal 5 also produced `goal4_proven_ok_baseline.csv` (9,116 rows where Goal 4
*was proven* correct), which is the regression-protection set against any
Goal 6 candidate.

Codex tried Candidate E (light industry classifier) during Goal 5; rejected
for lock violation. Lesson: industry/sector lookups remain banned in
production code regardless of how light-touch they look.

### Goal 6a — Measurement-only benchmark (commit 7f5ff25 + artifacts 230789f)

Status: done. Artifacts at `earnings-analysis/canary/quarter_resolver/`:
- `goal6_candidates.py` (research-only D + E reconstruction)
- `goal6a_d_measurement.csv` (10,674 rows)
- `goal6a_e_measurement.csv` (10,674 rows)
- `GOAL6A_REPORT.md`

Candidate D (the lock-respecting candidate from Goal 5) measured by subset:

| subset | rows | correct% | wrong% | fc% |
|---|---:|---:|---:|---:|
| Full historical | 10674 | 88.92 | 0.22 | 10.86 |
| Warm-start | 9878 | 96.08 | 0.24 | 3.67 |
| Cold-start | 796 | 0.00 | 0.00 | 100.00 |
| Latest-per-ticker | 781 | 95.65 | 0.38 | 3.97 |

D regresses 64 of Goal 4's 9,116 baseline rows: 63 to FC + 1 to wrong.
`DECISION_FLAG_SHIP_D_DIRECTLY = yes`.

Candidate E was a research-only comparison; lower correct%, lower wrong%.
Not shipped (lock violation when it required industry features).

### Goal 6c — Ship D to production (commits a61636a + 2f61810)

Status: done, verifier-passed, **pushed**.

Codex implemented D's 5 calendar-branch structural guards in
`scripts/earnings/quarter_identity.py`:

- `rule_g_strict_direct_recent_prior_calendar`
- `rule_g_strict_fail_closed_recent_disagreement_calendar`
- `rule_g_fail_closed_fy_disagreement_calendar`
- `rule_g_fail_closed_no_prev_short_gap_calendar`
- `rule_g_fail_closed_same_filing_short_gap_calendar`

Helpers added: `_ensure_prior_xbrl`, `_within_existing_short_gap`,
`_same_filing_cycle_indicator`.

Production scope kept narrow: `quarter_identity.py` + tests only;
`fiscal_math.py`, `harvest_guidance_sessions.py`, and
`earnings_orchestrator.py` left untouched.

Verifier: 13 gates including G8 per-row exact match against
`goal6a_d_measurement.csv` on all 10,674 rows. Full pytest 1417 passed.

### Goal 6e — Guidance 10-Q/10-K fallback hardening (commit be4c2cc)

Status: done, **pushed**.

`scripts/harvest_guidance_sessions._derive_via_period_to_fiscal` now uses a
single extended Cypher returning `accession`, `report_id`, `accession_no`,
`period_of_report`, `filing_type`, `fiscal_year_end_month`,
`xbrl_period_focus`, `xbrl_year_focus`. Logic:

1. CASE WHEN size(matches) = 1 guard for XBRL multi-context safety
2. Triple-check denylist on (accession, report_id, accession_no) — defends
   against schema drift where a junk id leaks past one of the three
3. `should_use_xbrl_fiscal` proximity guard (±1 year/quarter)
4. Fall through to the existing math fallback (`period_to_fiscal`) on any
   failure

This change does NOT merge guidance target-period extraction with the 8-K
resolver. It only hardens the rare case where `Report.fiscal_quarter` /
`Report.fiscal_year` are NULL on a 10-Q/10-K, where the old code went
straight to math fallback even when the filing's own DEI XBRL had a clean
label.

61/61 tests pass. Strengthened denylist tests use XBRL=Q1_FY2023 +
math=Q1_FY2024 so they actually fail if the denylist guard regresses
(previously tautological with XBRL == math).

Reused Goal 4 helpers in `scripts/earnings/get_quarterly_filings.py`:
- `XBRL_DENY_PERIODIC_ACCESSIONS`
- `should_use_xbrl_fiscal`
- `parse_xbrl_fiscal_identity`

This is the single-source-of-truth pattern: 8-K path goes through
`resolve_quarter_info` and inherits future improvements; periodic path uses
its own stored label first; both share the low-level XBRL helpers.

### 34-ticker SEC audit (parallel session, 2026-05-07)

Status: research-only artifact at
`audit_evidence/sec_34_edge_ticker_audit_2026-05-07/`. Not committed as
ground-truth source-of-truth yet.

408 rows / 34 tickers (the 31 D-fail-close + 3 D-wrong-fire from Goal 6a's
latest-per-ticker subset). Tier A=334, B=66, C=7, unclear=1. AB coverage
98.0%.

D on Tier A+B: fail_closed=293, true=95, false=12.

**G2-calendar-only**: D fail-closes flipped → 221 correct, **37 wrong**;
new wrong AUTO_OK on AB = 37.

**G2-all-fy-disagreement**: D fail-closes flipped → 239 correct, **39 wrong**;
new wrong AUTO_OK on AB = 39.

`DECISION_FLAG_RULE_G2 = promising_but_not_shippable`.

Drivers of the 37-39 new wrongs (per-ticker): GIII (12), BOX (6), DKS (5),
WDAY (4), WMS (3), NTAP (2), NTNX (2), ANF (2), CNM (1), GBX (1), PVH (1).
All are off-calendar filers where iXBRL `FY` and EX-99.1 `FY` disagree by
±1 year.

### Goal 6f — Research-only structural discovery beyond D (commit 74dfe6d, audit-evidence registration 0552fd9)

Status: **COMPLETE 2026-05-07. Verdict: `KEEP_D`.** Verifier exited 0. Codex
runtime 1668s. All 7 candidates measured per-row across 10,674 rows; matrix
recomputed exactly by the verifier; report flags consistent.

Per-candidate verdicts:

| candidate | full_wrong | new_wrong_vs_D (full) | edge_AB_recovered | shippable |
|---|---:|---:|---:|---|
| D_BASELINE | 26 | 0 | 0 | (baseline) |
| G2_CALENDAR_ONLY | 64 | +38 | 221 | no |
| G2_ALL_FY_DISAGREE | 66 | +40 | 239 | no |
| MULTI_PRIOR_STABLE_OFFSET | 44 | +18 | 158 | no — closest miss |
| PERIOD_END_SHAPE_GATE | 66 | +40 | 176 | no |
| CURRENT_8K_OWN_XBRL | 26 | 0 | 0 | no — no-op (no DEI in features) |
| ADVANCE_RESULT_AGREEMENT | 26 | 0 | 0 | no — no-op (zero convergences) |

`DECISION_FLAG_GOAL6F_FOUND_SHIPPABLE = no`
`DECISION_FLAG_GOAL6F_BEST_CANDIDATE = NONE`
`DECISION_FLAG_GOAL6F_RECOMMENDATION = KEEP_D`

Sharper failure-class name from `GOAL6F_FAILURE_MODEL.md`: **"structural
ambiguity after FY disagreement"** — the same prior structural shape produces
both safe and unsafe rows; no allowed signal uniquely discriminates. The
iXBRL year-of-start vs EX-99.1 year-of-end divergence is the *consequence*;
this is the *mechanism*.

PHR/PINC/PRU latest-per-ticker wrong-fires (`0001412408-26-000084`,
`0001193125-25-114958`, `0001137774-26-000087`) classified as irreducible
without current-event text or current-8K DEI facts in the feature pipeline.

**Future research lead (data-layer, not resolver-rule)**: `CURRENT_8K_OWN_XBRL`
became a no-op only because the structured feature artifact lacks current-8K
DEI FY/Q facts. If the data pipeline ever exposes 8-K cover-page DEI, this
candidate becomes retestable.

Files:
- `.claude/plans/goal_6f_prompt.md` (333 lines, research-only mission)
- `earnings-analysis/canary/quarter_resolver/verify_goal_6f_research.py`
  (438 lines, 8-gate verifier)
- `earnings-analysis/canary/quarter_resolver/GOAL6F_FAILURE_MODEL.md`
  (Phase A: 9 sections, 184 lines)
- `earnings-analysis/canary/quarter_resolver/GOAL6F_REPORT.md`
  (verdict + matrix + per-candidate pseudocode + rejections)
- `earnings-analysis/canary/quarter_resolver/goal6f_candidates.py`
- `earnings-analysis/canary/quarter_resolver/build_goal6f_outputs.py`
- `earnings-analysis/canary/quarter_resolver/goal6f_candidate_matrix.csv`
- `earnings-analysis/canary/quarter_resolver/goal6f_candidate_*_per_row.csv`
  (7 files × 10,674 rows)

Files:
- `.claude/plans/goal_6f_prompt.md` (333 lines, research-only mission)
- `earnings-analysis/canary/quarter_resolver/verify_goal_6f_research.py`
  (438 lines, 8-gate verifier)

Verifier gates (all passed):
- G1: immutable inputs git-clean
- G2: production code untouched
- G3: research files isolated to research subtree
- G4: banned patterns regex (no industry/sector/SIC/GICS/NAICS/CIK/EX-99/HTTP/ML/LLM)
- G4b: failure model 9 sections + ≥500 words + IRREDUCIBLE_CLASSES + TRACTABLE_CLASSES + EVIDENCE_ROWS
- G5: per-row CSVs valid + D_BASELINE byte-match against `goal6a_d_measurement.csv`
- G6: matrix exact recompute + shippable gate
- G7: report flags consistent

## What remains (in order of priority)

### 1. Production deploy of Goal 6c + 6e to running services

Code is committed at `74dfe6d` and pushed to `origin/main`, but k8s pods,
the extraction-worker, MCP servers, etc. are still on whatever image was
built before Goal 6c. Required:

- Rebuild + roll out container images (see CLAUDE.md "Docker Hub deploy"
  reference)
- Smoke-test on a real live FCX 8-K (or any other 8-K) end-to-end via the
  pipeline
- Monitor for unexpected fail-closed spikes; remember warm-start FC rate
  should be ~3.67%

### 2. Pop `pre-goal6f-pending` stash

`stash@{0}` from before the Goal 6f run is still pending. Pop it to restore
the user's pending edits from before Codex ran:

```bash
git stash pop
```

### 3. Optional: 34-ticker audit promotion

The `sec_34_edge_ticker_audit_2026-05-07/` set is currently artifact-level.
Consider promoting verdict rows into the canonical audit registry alongside
Goal 1 GT, Goal 1.5 200-packet audit, and the 52/53 + NR AUTO_OK audits.

### 4. Optional: Cleanup of bug-corrupted `Q4_FY2025/` FCX directory

Pre-existing artifacts from when the buggy resolver mislabeled FCX Q1 8-K
still sit at `earnings-analysis/Companies/FCX/events/Q4_FY2025/`. Decide
delete vs archive — separate cleanup, not blocking.

### 5. Optional: Consolidated truth registry

User wants all hard-earned evidence in one canonical place:

```
earnings-analysis/canary/quarter_resolver/audit_evidence/SEC_AUDITED_QUARTER_GT.json
earnings-analysis/canary/quarter_resolver/audit_evidence/SEC_AUDITED_QUARTER_GT.csv
earnings-analysis/canary/quarter_resolver/audit_evidence/SEC_AUDITED_QUARTER_GT_SUMMARY.md
```

Sources to consolidate:
- Goal 1 GT/NR files
- Goal 1.5 200-packet audit
- 52/53 SEC audit
- Goal 5 NR AUTO_OK SEC audit (cleaned_all_verdicts.json)
- 34-ticker SEC audit

`truth_source_type` values:
- `two_source_agreement` — Goal 1 GT (high confidence, NOT manually SEC-read)
- `sec_manual_audit` — SEC/EX-99.1/8-K text manually audited
- `verifier_derived` — re-derived by immutable verifier, not SEC text
- `needs_review_no_oracle` — no independent label

## Honest accuracy claims (don't overclaim)

What's been **proven** (hard verifier evidence):

- **Goal 4 historical accuracy when firing**: 0 WRONG / 9,116 AUTO_OK /
  9,943 oracle-scored rows = 100% on its measured scope ✅
- **Candidate D measured warm-start**: 24/9878 wrong = 0.24% (improved
  precision but lower coverage than Goal 4 alone)
- **Candidate D regression delta vs Goal 4 baseline**: 9,052 preserved /
  63 newly fail-closed / 1 newly wrong (effectively a wash for the wrong
  count; trades coverage for fewer wrong-fires on NR rows Goal 4 couldn't
  see)
- **52/53-week regression test**: 94/0/21 on 115 odd_52_53 ✅
- **Currently-firing preservation (Goal 4 → 6c)**: maintained via
  G7b-equivalent and Goal 6c's per-row D_BASELINE match
- **FCX bug fix end-to-end**: Q1_FY2026 / AUTO_OK ✅
- **Guidance 10-Q/10-K XBRL-first fallback**: 61/61 tests including
  triple-check denylist defense ✅

What's **derived** (extrapolation):

- **34/781 = ~4.4% of universe is structurally fail-closed under D**
  (latest-per-ticker proxy)
- **iXBRL/EX-99 divergence is the irreducible class**

What's **NOT proven**:

- Live-mode behavior (no live 8-K has run on Goal 6c code in production)
- Cold-start (796 rows are 100% fail-closed by design)
- Future-unseen tickers (new IPOs, FYE switchers)
- (CLOSED 2026-05-07) Whether any lock-respecting structural candidate beats
  D — empirically rejected for all 4 new candidates tested in Goal 6f. D is
  the structural ceiling under current locks + current data pipeline.

## Locked decisions (don't relitigate)

| Decision | Locked rationale |
|---|---|
| No ticker allowlists/denylists/FY tables | Maintenance burden; doesn't generalize; rules must be self-detecting |
| No industry/sector/SIC/GICS/NAICS dispatch | Goal 5 Candidate E rejected this; lookups break the structural-only contract |
| No CIK-based dispatch | Same as above; CIK is just a per-issuer key |
| No EX-99.1 / press-release text parsing in production | D8 lock since 2026-05-05; allowed only as research ground truth |
| No external HTTP / SEC EDGAR live lookups in production | Same |
| No ML / LLM classifiers in production resolver | Locked |
| Rule F replaces ONLY the odd_52_53 branch | Goal 4 G7b hard-lock |
| Candidate D replaces ONLY the calendar-branch guards listed in 6c | Goal 6c per-row CSV byte-match against `goal6a_d_measurement.csv` |
| `_effective_fye_month` preserved | Goal 3 / Goal 4 source-string compatibility |
| Long-gap threshold = 150 days | Goal 3 calibration; do NOT confuse with old `_STALE_MATCH_DAYS=150` |
| 24-hour proximity threshold for direct-recent | Empirically calibrated for PEP/LEVI |
| 8-K periodOfReport ≠ fiscal quarter end | Probe-disproven 2026-05-05 |
| Guidance 10-Q/10-K fallback uses own filing's XBRL, NOT `resolve_quarter_info` | Goal 6e architectural separation |
| Guidance 8-K source-quarter labeling DOES use `resolve_quarter_info` | Same |
| 0 WRONG_AUTO_WROTE > 100% firing | Wrong-writes corrupt downstream artifacts |
| `KEEP_D` is a valid Goal 6f outcome | Verifier explicitly allows it |
| iXBRL year-of-start vs EX-99.1 year-of-end is irreducible under locks | Empirically established by the 34-ticker audit |

## Files to read first in a new session

1. `.claude/plans/restore-context.md` (this file)
2. `.claude/plans/refactor-safety-contract.md` (preservation contract)
3. `.claude/plans/quarter-identity-resolver.md` (master plan + status tracker)
4. `scripts/earnings/quarter_identity.py` (Goal 4 + 6c production)
5. `scripts/earnings/earnings_orchestrator.py` (write-guard at lines ~381-444)
6. `scripts/harvest_guidance_sessions.py` (Goal 6e XBRL-first fallback)
7. `scripts/earnings/test_quarter_identity.py` (Goal 4 + 6c tests)
8. `scripts/test_harvest_guidance_sessions.py` (Goal 6e tests)
9. `earnings-analysis/canary/quarter_resolver/verify_goal_6f_research.py`
   (Goal 6f verifier, 8 gates)
10. `.claude/plans/goal_6f_prompt.md` (Goal 6f mission spec)
11. `earnings-analysis/canary/quarter_resolver/GOAL6A_REPORT.md` (D measurement)
12. `earnings-analysis/canary/quarter_resolver/audit_evidence/sec_34_edge_ticker_audit_2026-05-07/DECISION_FLAG.md`
    (G2 rejection)

Do not read large CSVs end-to-end. Use `rg`, `head`, or small Python.

## Dirty worktree warning

Many unrelated dirty/untracked/deleted files from other work. Do NOT revert,
stash, delete, or commit them unless the user explicitly asks.

The `pre-goal6f-pending` stash exists at `stash@{0}` and must be popped
after Codex finishes:

```bash
git stash list   # confirm stash@{0} is "pre-goal6f-pending"
git stash pop    # restore the user's pending edits
```

For verifier scope-check passes, unrelated dirty files in `scripts/earnings/`
(specifically `compare_section.py` and `snapshot_xbrl_in_flight.py`) may
need temporary stashing.

## User preferences and interaction pattern

- Concise answers unless asking for deep review. "One line" means one line.
- "Perfect?" → independently verify; do NOT rubber-stamp Claude or ChatGPT.
- User uses ChatGPT/Codex/Claude as cross-checks; evaluate against files
  and verifier outputs.
- User values zero wrong-writes more than 100% firing rate.
- Hand-write all verifiers BEFORE handing off to /goal.
- No Co-Authored-By trailer in commits.
- Always get permission before modifying production code; show diff/plan first.
- Independent eval of ChatGPT critiques; flag overstatements; never rubber-stamp.

## Start-of-turn instruction

After reading this file, say briefly:

```
Context restored. HEAD 0552fd9, pushed to origin/main. Goal 6c (Candidate D)
and Goal 6e (guidance fallback) live in code. Goal 6f COMPLETE 2026-05-07:
verdict KEEP_D, all 4 new structural candidates rejected — D is the empirical
structural ceiling under current locks + current data pipeline. Open: k8s
production deploy of 6c+6e, pop pre-goal6f-pending stash, optional
truth-registry consolidation.
```

Then ask what the user wants next unless they already gave a concrete task.
