# RESTORE CONTEXT — Quarter Identity Resolver

Last updated: 2026-05-06

You are resuming a long quarter-resolver investigation in
`/home/faisal/EventMarketDB`. Read this file first, then read the running plan
at `.claude/plans/quarter-identity-resolver.md`. Do not re-litigate locked
decisions unless the user explicitly asks.

## Current State (TL;DR)

**Goal 4 is implemented, verifier-passed, committed locally, and the test suite is fully clean.**

- Latest local HEAD: `5ff1619` (test_quarter_identity_u64.py rewrite for Goal 4 architecture)
- Goal 4 production commit: `e43cfc8` (modifies `quarter_identity.py`, `earnings_orchestrator.py`, `test_quarter_identity.py` only)
- Goal 4 prompt+verifier+SEC audit evidence: `fb03a9e`
- Plan tracker update: `580425c`
- **NOT yet pushed to origin/main** (8 commits ahead). Push is gated by user decision.
- **NOT yet deployed to running services** (k8s pods, MCP servers still on OLD buggy code).

The FCX bug is structurally fixed in committed code:

```
0000831259-26-000021 → Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1
```

Production `_STALE_MATCH_DAYS=150` cascade is gone; replaced by `prior_periodic_projection` + Rule F + orchestrator destructive-write guard.

## Verifier sign-off (Goal 4 canonical bare verifier exited 0)

```bash
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py
```

Key gates passed:
- **G5** (115 odd_52_53 rows): exactly `94 OK / 0 WRONG / 21 FAIL_CLOSED` (Rule F deterministic outcome)
- **G6** (FCX `0000831259-26-000021`): `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1` — note the source is the calendar-shaped advance, NOT a Rule F source (FCX FYE=12; prior 10-K period 2025-12-31 is calendar-shaped)
- **G7 FULL**: `9116 OK / 0 WRONG / 827 FAIL_CLOSED` across 9,943 oracle-scored rows (9,909 GT + 34 SEC-audited NR). **0 WRONG_AUTO_WROTE is hard-locked.**
- **G7b FULL**: `9860/9860` Goal-3 currently-firing rows preserved exactly (0 changed-OK, 0 newly-fail-closed). Rule F replaces ONLY the odd_52_53 branch.
- **G8** (pytest): test_quarter_identity.py — 12/12 passing
- **G9** (pytest -k write_guard): 2/2 passing — actually runs the test, not just lints the file

Trustworthiness audit (8 checks) all clean:
1. All 5 verifiers + Goal-N corpus/artifacts unchanged
2. Codex's stash cleanly dropped (only user's pre-existing stashes remain)
3. User WIP (`compare_section.py`, `snapshot_xbrl_in_flight.py`) restored
4. Production scope: only 3 files modified (in `ALLOWED_PROD_MODIFICATIONS`)
5. `_STALE_MATCH_DAYS=150` gone; all 14 source strings present (9 Goal-3 preserved + 5 Rule F); `_effective_fye_month` preserved
6. FCX direct test → Q1_FY2026 / AUTO_OK
7. pytest test_quarter_identity.py — 12 passed
8. Diff scope: 832 insertions / 200 deletions across 3 files

## Original Problem (the FCX bug)

`scripts/earnings/quarter_identity.py` used `_STALE_MATCH_DAYS=150`, which silently accepted the previous quarter's 10-K as authoritative for a live 8-K before the same-quarter 10-Q/10-K existed. FCX Q1 FY2026 `0000831259-26-000021` was mislabeled as `Q4_FY2025`, causing the orchestrator to write into the wrong event directory and overwrite/delete the real Q4 prediction.

Goal 4 fixed this in production by replacing the old stale-match cascade with PIT-visible prior-periodic projection plus Rule F for odd 52/53-week filers and an orchestrator destructive-write guard.

## Goal Outcomes

### Goal 1 — Ground Truth Corpus (commit fc83a1c)

Status: done and verifier-passed.

Files: `ground_truth.csv`, `needs_review.csv`, `build_corpus.py`, `REPORT.md`

- Universe: 10,831 earnings 8-Ks
- GT: 9,909 rows (two-source agreement: same-event periodic XBRL == fiscal_math)
- NR: 922 rows
- NR breakdown: not_same_event_periodic 495, xbrl_math_disagree 391, proximity_rejected 26, denylist 6, no_xbrl 4, no_fye 0

Verifier: `verify_ground_truth_corpus.py` (C1-C10, full-corpus re-derivation). Patched at commit 59fb681 (C9 accession_8k false-positive fix).

**Important nuance**: Goal 1 GT is *high-confidence two-source agreement*, NOT all manually SEC-read truth. Do not call every GT row "human/SEC audited".

### Goal 1.5 — Stratified SEC Audit (commits f2a0eb6, 04789af)

Status: done, PASS (199/200 ok, 0 wrong, 1 unclear).

Files: `audit_packets.json`, `audit_packets.csv`, `SAMPLING_REPORT.md`, `audit_evidence/SUMMARY.md` + 7 verdict JSON files.

The unclear row was RH 0001558370-23-000847 — Item 4.02 non-reliance/restatement filing, not a current-quarter earnings release. Sampling-eligibility edge case, not a corpus defect.

### Goal 2 — Shadow Validator (commits b909a3f → 0813df2 → 72a7668 → dea1ef5)

Status: done and verifier-passed.

Deliverables: `shadow_audit.csv`, `candidate_algorithms.py`, `candidate_audit.csv`, `GOAL2_REPORT.md`.

Production today (measured by Goal 2 verifier on 10,831):
- 9,909 GT-AGREE / 0 GT-BUG / 0 GT-NO_RESOLUTION
- **492 WRONG_AUTO_WROTE on `not_same_event_periodic`** — the FCX harm count
- 430 AUTO_ON_UNCERTAIN_ROW (other-NR confident auto-resolves)
- 0 CORRECT_FAIL_CLOSED (production never fails closed)

Verifier was rewritten through 5 ChatGPT critique rounds (R6-R8); final design inverted the default so bare command = FULL 10,831-row re-derivation (canonical sign-off), `--fast` = stratified opt-in for iteration.

### Goal 3 — Live-Mode Candidate Benchmark (commit 0ae4d0e)

Status: done and verifier-passed via Codex /goal.

Deliverables: `live_candidates.py`, `live_mode_audit.csv`, `LIVE_MODE_REPORT.md`.

Codex's recommended candidate: `prior_periodic_projection`. Achievability: NO (best candidate hits 91.03% on full corpus, not 99.9%).

**Empirical follow-up analysis (2026-05-06): warm-start hypothesis CONFIRMED.**

- Full-corpus fire rate **91.03%** is inflated by **838 cold-start rows from 2023** (DB history starts there; 3 in 2024, 1 in 2025, 0 in 2026).
- **Warm-start fire rate: 98.67%** (9,860 / 9,993 rows where prior periodic existed at PIT)
- **Latest-per-ticker fire rate: 97.95%** (765 / 781 unique tickers' most-recent 8-Ks)
- Year-cohort warm-start rates: 2023=98.94%, 2024=98.79%, 2025=98.50%, 2026=98.16% — stable
- Production today **verified-wrong rate: 4.54%** (492/10,831), not 9% (3.97% additional is AUTO_ON_UNCERTAIN_ROW — uncertain class, not measurably wrong)
- Warm-start residuals (133 rows): **115 × 52/53-week** + 9 × long-gap + 9 × denylisted-prior
- Latest-per-ticker residuals (16 rows): 14 × 52/53-week + 2 × long-gap (DLR, PHM)

**8-K periodOfReport probe (2026-05-05) — CRITICAL FINDING:**
- All 10,995 earnings 8-Ks have `periodOfReport` populated
- 91.1% exactly equal the filing date (event-date semantics, NOT fiscal-period semantics)
- 6.5% within 1-5 days of filing date
- **Conclusion: do NOT use 8-K periodOfReport as a quarter-end signal.** Live resolver must use PIT-visible prior 10-Q/10-K and project forward.

### Goal 4 — Production Implementation (commit e43cfc8)

Status: done, verifier-passed, committed, **NOT pushed/deployed**.

Production files changed in `e43cfc8`:
- `scripts/earnings/quarter_identity.py` (740 lines: 80% rewrite)
- `scripts/earnings/earnings_orchestrator.py` (+65 lines for write-guard)
- `scripts/earnings/test_quarter_identity.py` (+227 lines for 12 new tests)

**Algorithm structure (mirrors Goal 3 `_prior_periodic_projection` byte-faithfully with EXACTLY ONE substitution: odd_52_53 branch → Rule F):**

```python
def resolve_quarter_via_prior_periodic(row_context, *, neo4j_session):
    # 1. Goal 3 prelude: parse fye_month, filed; get priors
    # 2. _effective_fye_month(priors, fye_month) — derive effective FYE
    #    from most recent calendar-shaped 10-K (PRESERVED from Goal 3)
    # 3. denylist check (XBRL_DENY_PERIODIC_ACCESSIONS)
    # 4. bad-context check
    # 5. BRANCH on _period_end_is_calendar_shaped(prior.period):
    #    - NORMAL CALENDAR-SHAPED → Goal 3 path UNCHANGED
    #      (currently-firing 9,860 rows enter here and must NOT change)
    #      → period_to_fiscal(..., effective_fye, ...) → advance_one_quarter
    #      → source `prior_periodic_projection_qN_to_qM`
    #         + `_effective_fye_from_prior_10k` if effective ≠ fye_month
    #    - ODD 52/53 SHAPE → Rule F (NEW; replaces old fail-closed):
    #      * if (filed - prior_created) within 24h → use prior XBRL FY/Q
    #        DIRECTLY (source `rule_f_direct_recent_prior`)
    #        — handles PEP/LEVI same-event 10-Q-then-8-K
    #      * elif XBRL_FY != math_FY → FAIL_CLOSED
    #        (source `rule_f_fail_closed_fy_disagreement`)
    #        — handles KR/NTAP/SYNA naming-convention disagreement
    #      * else → advance XBRL FY/Q (source `rule_f_advance_xbrl`)
    #        — handles AAP/PSTG extreme calendars where math FY is wrong
    # 6. Long-gap check (>150 days) ONLY in calendar-shaped branch
    # 7. Cold-start, future-prior, fiscal-math errors → fail closed
```

Orchestrator destructive-write guard (`enforce_quarter_identity_write_guard`):
- Refuses event-directory writes unless `safety_action == "AUTO_OK"`
- Writes a quarantine JSON record to `<ticker>/quarter_identity_quarantine/`
- Wired into main flow before any `--save` / `--predict` / `--learn`

**No ticker allowlists, no ticker denylists, no per-issuer FY-convention table, no special PEP/KR/AAP logic. Rule F is structural-only.**

### Goal 4 verifier (commit fb03a9e)

Hand-written through **7 ChatGPT critique rounds**. Each independently re-evaluated by Claude per feedback rule. Hardenings landed:

- R1: long-gap threshold 200d → 150d (silent change reverted to match Goal 3 `live_candidates.py:185`)
- R2: FULL-mode G7 hard-lock added (was sample-only)
- R3: G9 actually runs `pytest -k write_guard` (was string-lint only)
- R4: G2 banned ticker-allowlist/denylist/FY-table patterns via regex scan
- R5: G2 requires ALL Rule F + Goal 3 sources, not just ≥4
- R6: pseudocode rewritten — Rule F replaces ONLY odd_52_53; Goal 3 logic byte-preserved including `_effective_fye_month` and `_effective_fye_from_prior_10k` augmentation
- R7: G7b 9,860 firing rows preservation hard-lock (catches silent coverage shrink); FCX G6 expects `prior_periodic_projection_q4_to_q1` (calendar-shaped, not Rule F)

The verifier has a `--fast` flag for iteration; bare command = canonical full sign-off.

## Rule F evidence and the candidate-rule matrix probe

The 52/53-week issue was the last load-bearing residual before Goal 4. Decision lineage:

1. **Approach A (math + advance)**: 79 OK / 36 WRONG on 115 — unsafe, AAP/PSTG/ACI/PEP fail
2. **Approach B (XBRL + advance)**: 99 OK / 16 WRONG — LEVI/PEP/KR/NTAP fail
3. **Approach C (math FY + XBRL Q + advance)**: 88 OK / 27 WRONG
4. **Rule D (direct-24h + B fallback)**: 110 OK / 5 WRONG — best accuracy but **5 GT-violating wrongs** (KR×2, NTAP×2, SYNA×1, all FY-off-by-one)
5. **Rule E (direct-24h + C fallback)**: 99 OK / 16 WRONG
6. **Rule F (D + FY-agreement guard)**: **94 OK / 0 WRONG / 21 FAIL_CLOSED** ✅ **WINNER**
7. **Rule G (D + use-math-on-disagree)**: 99 OK / 16 WRONG (regresses on ACI)

Rule F's safety contract: "fail-closed on ambiguity" — when XBRL FY ≠ math FY for a non-recent prior, refuse to guess. This trades 16 OK firings (rules B/D would have gotten right by accident) for 0 wrong-auto-writes.

Manual SEC audit covered 34 odd-52/53 NR rows under `/tmp/quarter_52_53_sec_audit/`, persisted in repo at:

```
earnings-analysis/canary/quarter_resolver/audit_evidence/sec_52_53_audit/all_verdicts.json
```

Key audit findings:
- **PEP** (10/10 wrong under XBRL+advance) — same-event prior filed minutes before 8-K → use direct, not advance
- **LEVI** (1/1 wrong) — same pattern; Q3 not Q4
- **NTAP** (1 wrong) — XBRL FY off by 1 year; needs FY-agreement guard
- **AAP, PSTG** — fiscal_math+advance gets wrong FY on extreme calendars
- **ACI/KR/PLAY** — handled correctly by Rule F's direct-recent path

## FCX end-to-end smoke test (2026-05-06)

Pre-deploy validation under new resolver (no production deploy yet):

```bash
venv/bin/python scripts/earnings/earnings_orchestrator.py \
  FCX 0000831259-26-000021 --predict --save
```

Result:
- Resolver: `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1` ✅
- 7 builders done in 19.7s, 0 failed
- Bundle written to `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json` ✅ (correct directory)
- The pre-existing bug-corrupted `Q4_FY2025/` directory was NOT touched (write-guard was not invoked here because the resolver returned the correct quarter)
- Predictor LLM call ran to completion

**This is the load-bearing proof that the FCX bug fix works end-to-end at the resolver+orchestrator layer.**

## FCX canary re-validation (all 14 historical events, 2026-05-06)

Per-event resolver outcomes under Goal 4 code:

```
10 OK             — match prior labels
 1 FAIL_CLOSED    — Q4_FY2022 (acc 23-000004) cold-start; oldest event,
                    no prior periodic in DB at PIT
 3 MISMATCH       — but ALL 3 are CORRECTIONS of OLD buggy labels:
   - Q4_FY2023 (acc 25-000002, filed 2025) → new resolver says Q4_FY2024
     (correct: 2025 filing announces FY ending Dec 2024)
   - 8K_..._25-000011 (no quarter assigned in old event.json)
     → new resolver says Q1_FY2025 (correct)
   - 8K_..._26-000021 (the FCX bug accession; old event.json had no
     quarter because the bug had wrong-labeled it)
     → new resolver says Q1_FY2026 (the fix we set out to make)
```

**Zero regressions.** All 13 events with clean prior labels match; the 3 "mismatches" are corrections.

## Test suite hygiene (commit 5ff1619)

After Goal 4, full pytest scripts/earnings/ exposed 11 stale failures in `test_quarter_identity_u64.py`. The failures asserted OLD architecture details that Goal 4 intentionally removed:

- Cypher `CASE WHEN` accession masking pattern
- returning both raw `matched_accession_periodic` and gated `accession_periodic`
- stale-match → fiscal_math fallback
- source strings starting with `matched_periodic` / `fiscal_math`

**Action taken**: rewrote `test_quarter_identity_u64.py` (NOT deleted) to test the SAME safety property under the new architecture. 13 new tests across 4 classes:

- **CypherPitSafetyTests** — static guards on `_QUERY` and `_PRIOR_QUERY` PIT bounds; absence of `_STALE_MATCH_DAYS=150`; absence of old CASE WHEN mask
- **FailClosedBehaviorTests** — no-prior, long-gap, future-prior all FAIL_CLOSED with documented sources; accession_periodic stays empty
- **CalendarShapedAutoOkTests** — calendar-shaped prior advances Q4→Q1 with FY rollover; accession_periodic NOT exposed for projection paths (it's a projection, not same-event)
- **RuleFDirectRecentTests** — odd-52/53 prior <24h before 8-K → AUTO_OK via `rule_f_direct_recent_prior`; accession_periodic IS populated (same-event)

**Result: full pytest scripts/earnings/ now 1395 passed / 0 failed / 14 skipped.**

No production code change required. Only the test file was modified.

**Nuance**: `prior_periodic_projection_future_prior_fail_closed` source exists ONLY in the calendar-shaped branch. Odd 52/53 future-prior cases are normally impossible through the real PIT-bounded query; the test verifies future-prior fail-closed on the calendar branch where that source actually lives.

## What remains (in order of priority)

### 1. Production deploy (separate operational phase)

Code is committed at `e43cfc8` + `5ff1619` but NOT yet:
- Pushed to `origin/main` (8 commits ahead)
- Deployed to running services (k8s pods, MCP servers still on OLD buggy code)

User decision pending. Recommended canary-first deploy with monitoring.

### 2. Cleanup of bug-corrupted `Q4_FY2025/` directory

Pre-existing artifacts from when the buggy resolver mislabeled the FCX Q1 8-K still sit at `earnings-analysis/Companies/FCX/events/Q4_FY2025/`. Decide whether to delete/archive — separate cleanup, not blocking deploy.

### 3. (Optional) NR AUTO_OK SEC audit — 888 unaudited rows

Of the 922 NR rows, 34 odd 52/53 NR rows have SEC audit evidence. The remaining 888 NR rows have no oracle. If the new Goal 4 resolver auto-fires on any of them, those firings are unverified.

Recommended approach (from prior planning):
1. Load `needs_review.csv`
2. Exclude accessions in `audit_evidence/sec_52_53_audit/all_verdicts.json`
3. Run current `resolve_quarter_info(ticker, accession_8k)` on remaining NR
4. Write claims under `/tmp/quarter_nr_auto_ok_sec_audit/`
5. SEC-audit ONLY `AUTO_OK` + non-empty `quarter_label` rows (fail-closed rows can't wrong-write)
6. Use SEC EDGAR text/EX-99.1/8-K body as truth; do not defer to corpus/XBRL
7. Produce manifest + per-bucket verdicts + `all_verdicts.json` + `SUMMARY.md`
8. PASS only if wrong == 0

### 4. (Optional) Consolidated truth registry

User wants all hard-earned evidence in one canonical place, not scattered across `/tmp` and multiple audit folders.

Create after the NR AUTO_OK audit finishes:

```
earnings-analysis/canary/quarter_resolver/audit_evidence/SEC_AUDITED_QUARTER_GT.json
earnings-analysis/canary/quarter_resolver/audit_evidence/SEC_AUDITED_QUARTER_GT.csv
earnings-analysis/canary/quarter_resolver/audit_evidence/SEC_AUDITED_QUARTER_GT_SUMMARY.md
```

Each row should include:
- `accession_8k`, `ticker`, `audited_fy`, `audited_q`, `truth_source_type`, `audit_source_batch`, `evidence_url`, `evidence_quote`, `document_type`, `evidence_method`, `verdict`, `confidence`, `audit_date`, `reasoning`, `notes`

`truth_source_type` values:
- `two_source_agreement` — Goal 1 GT (high confidence, NOT manually SEC-read)
- `sec_manual_audit` — SEC/EX-99.1/8-K text manually audited
- `verifier_derived` — re-derived by immutable verifier, not SEC text
- `needs_review_no_oracle` — no independent label

Sources to consolidate:
- Goal 1 GT/NR files
- Goal 1.5 200-packet audit
- 52/53 SEC audit
- NR AUTO_OK SEC audit (when done)

After creating, update `quarter-identity-resolver.md` and this `restore-context.md`.

## Honest accuracy claims (don't overclaim)

What's been **proven** (hard verifier evidence):

- **Historical accuracy when firing**: 0 WRONG out of 9,116 AUTO_OK on 9,943 oracle-scored rows = **100%** ✅ (G7 hard-locked)
- **52/53-week regression test**: 94/0/21 on 115 odd_52_53 ✅
- **Currently-firing preservation**: 9,860/9,860 ✅ (G7b)
- **FCX bug fix**: end-to-end pipeline writes Q1_FY2026/ ✅

What's **derived** (extrapolation from data):

- **Warm-start firing frequency**: ~99.2-99.6% (Goal 3's 98.67% baseline + Rule F unlocks 94 of the 115 odd_52_53)
- **Latest-per-ticker firing frequency**: ~99.6%

What's **NOT proven**:

- Live-mode behavior (no live event has run on new code)
- 888 unaudited NR rows (no oracle)
- Future-unseen tickers (new IPOs, FYE switchers, etc.)
- Concurrency/timing edge cases under production load

For the FCX bug specifically: **fully proven fixed in committed code.** Broader accuracy claims have empirical support but require live-mode observation to fully validate.

## Files to read first in a new session

Read in this order:

1. `.claude/plans/restore-context.md` (this file)
2. `.claude/plans/quarter-identity-resolver.md`
3. `scripts/earnings/quarter_identity.py` (Goal 4 production)
4. `scripts/earnings/earnings_orchestrator.py` (write-guard at lines ~381-444 + ~3711-3713)
5. `scripts/earnings/test_quarter_identity.py` (12 Goal 4 tests)
6. `scripts/earnings/test_quarter_identity_u64.py` (13 PIT-safety regression tests)
7. `earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py` (immutable verifier)
8. If working on truth consolidation: `earnings-analysis/canary/quarter_resolver/audit_evidence/`

Do not read the large CSVs end-to-end unless needed. Use `rg`, `head`, or small Python scripts.

## Dirty worktree warning

The worktree has many unrelated dirty/untracked/deleted files from other work. Do NOT revert, stash, delete, or commit them unless the user explicitly asks.

Known unrelated dirty paths recently observed:

- `scripts/earnings/compare_section.py` (long-standing M)
- `scripts/snapshot_xbrl_in_flight.py` (long-standing ??)
- `scripts/earnings/earnings_orchestrator.py` and `scripts/earnings/test_lesson_status_transitions.py` may contain unrelated lesson-status/cap-telemetry edits after Goal 4 (note: commit `d35177f` has user's separate cap-binding work)
- many `.claude/agents/test-*` and `.claude/skills/test-*` deletions
- many untracked `.claude/plans/*` and archive paths

Goal 4 production changes are already committed locally; do not re-stage unrelated files into quarter-resolver commits.

For the canonical Goal 4 verifier to pass G3 (scope check), unrelated dirty files in `scripts/earnings/` (specifically `compare_section.py` and `snapshot_xbrl_in_flight.py`) must be temporarily stashed:

```bash
git stash push --include-untracked -m "pre-goal4-pending" -- \
    scripts/earnings/compare_section.py scripts/snapshot_xbrl_in_flight.py
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py
git stash pop
```

## Key locked decisions (don't relitigate)

| Decision | Locked rationale |
|---|---|
| No ticker allowlists/denylists/FY-tables in production | Maintenance burden; doesn't generalize to new tickers; Rule F's runtime checks are self-detecting |
| Rule F replaces ONLY the odd_52_53 branch | Currently-firing 9,860 rows didn't hit that branch and must be preserved (G7b hard-lock) |
| `_effective_fye_month` preserved from Goal 3 | Goal 3 uses it; tests rely on `_effective_fye_from_prior_10k` source augmentation |
| Long-gap threshold = 150 days | What Goal 3's `live_candidates.py:185` uses; verifier-proven safe; do NOT confuse with old `_STALE_MATCH_DAYS=150` (different concept, opposite policy) |
| 24-hour proximity threshold for Rule F direct-recent | Empirically calibrated for PEP/LEVI same-event pattern |
| 8-K periodOfReport ≠ fiscal quarter end | Probe-disproven 2026-05-05; do NOT use as quarter signal |
| EX-99.1 string parsing VETOED | D8 lock; Goal 4 does not need it (achievable via Rule F) |
| Manual SEC audits OK for truth verification | Production code has no text parsing; humans/subagents may SEC-audit for ground truth |
| 0 WRONG_AUTO_WROTE > 100% firing rate | Fail-closed is acceptable; wrong-writes corrupt downstream artifacts |

## User preferences and interaction pattern

- User wants concise answers unless asking for deep review
- If user says "one line", answer in one line
- If user asks "perfect?", independently verify; do NOT rubber-stamp Claude or ChatGPT
- User uses ChatGPT/Codex/Claude as cross-checks; evaluate claims against files and verifier outputs
- User values zero wrong-writes more than 100% firing
- Avoid overengineering; final accepted resolver is structural Rule F
- Do NOT propose EX-99.1 regex/LLM extraction as production logic

## Start-of-turn instruction

After reading this file, say briefly:

```
Context restored. Goal 4 implemented + verifier-passed + tests clean at HEAD 5ff1619 (production: e43cfc8). Open threads: production deploy, optional NR AUTO_OK SEC audit, optional consolidated truth registry. 8 commits ahead of origin/main; not yet pushed/deployed.
```

Then ask what the user wants next unless they already gave a concrete task.
