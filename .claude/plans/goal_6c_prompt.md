# Goal 6c — D production implementation (calendar-branch Rule G)

**Status**: ready to fire via `/goal` after verifier is git-committed.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_goal_6c_implementation.py` (hand-authored — Codex must NOT modify; checked via git diff).
**Pass criterion**: verifier exits 0.
**Honest claim**: Goal 6c ports Candidate D (Goal 6a's measured best lock-respecting candidate) into `scripts/earnings/quarter_identity.py`. All Goal 4 invariants are preserved (Rule F's odd_52_53 branch unchanged, FCX fix preserved, write-guard untouched). D adds five structural guards to the calendar-shaped branch of `resolve_quarter_via_prior_periodic`. The implementation must produce **byte-exact per-row outputs matching `goal6a_d_measurement.csv`** on all 10,674 audited scoreable rows — that file is the immutable spec.

---

## North star

**Production resolver, after Goal 6c, must produce per-row outputs identical to `earnings-analysis/canary/quarter_resolver/goal6a_d_measurement.csv` on all 10,674 audited rows.** Goal 6a is the ground truth for D's behavior; Goal 6c just makes production match it.

---

## Pre-flight (you do this BEFORE firing /goal)

### 1. Stash unrelated dirty paths

```bash
git stash push --include-untracked -m "pre-goal6c-pending" -- \
    scripts/earnings/compare_section.py \
    scripts/snapshot_xbrl_in_flight.py
```

### 2. Commit verifier + prompt

```bash
git add earnings-analysis/canary/quarter_resolver/verify_goal_6c_implementation.py \
        .claude/plans/goal_6c_prompt.md
git commit -m "wip(quarter-resolver): goal 6c verifier + prompt"
git diff --quiet -- earnings-analysis/canary/quarter_resolver/verify_goal_6c_implementation.py && echo OK
```

### 3. After Codex finishes, restore stash

```bash
git stash pop
```

---

## The /goal command (copy verbatim into Codex)

```
/goal Implement Goal 6c (port Candidate D into production quarter_identity.py) exactly as specified in .claude/plans/goal_6c_prompt.md, and keep iterating until earnings-analysis/canary/quarter_resolver/verify_goal_6c_implementation.py exits 0.
```

## Follow-up message (after Codex acknowledges)

```
Read .claude/plans/goal_6c_prompt.md in full first. Goal 6c modifies
ONLY:
  - scripts/earnings/quarter_identity.py (D's 5 guards in the
    calendar-shaped branch of resolve_quarter_via_prior_periodic)
  - scripts/earnings/test_quarter_identity.py (new tests)
  - scripts/earnings/test_quarter_identity_u64.py (new PIT-safety
    tests if needed)

DO NOT touch:
  - fiscal_math.py (pure math, breaks Class 3 consumers)
  - earnings_orchestrator.py (write-guard already in place from Goal 4)
  - Any guidance / harvest / daemon / extraction file
  - goal6_candidates.py (research-only, do not import from production)

Goal 4's hard-locks remain: FCX → Q1_FY2026/AUTO_OK, 115 odd_52_53 →
94/0/21 under Rule F, write-guard preserved. The new D logic adds
guards in the calendar-shaped branch only (Rule F's odd_52_53 branch
is preserved verbatim, Goal 3 prelude is preserved verbatim).

The spec is `goal6a_d_measurement.csv`: production D must produce
byte-exact per-row outputs matching that file on all 10,674 audited
rows. Codex must NOT introduce new behavior beyond what that file
encodes.
```

---

## CONTEXT (load-bearing facts; do NOT re-discover)

1. **Production today** is Goal 4 (commit `e43cfc8` series, currently HEAD `7f5ff25`). Goal 4 verifier hard-locks 0 WRONG_AUTO_WROTE on 9,943 oracle-scored rows. FCX bug fixed.

2. **Goal 6a measured Candidate D** on 10,674 audited rows (9,943 oracle + 731 cleaned NR scoreable). Outcome:
   - Warm-start (9,878 rows): **96.08%** correct, **0.24%** wrong, 3.67% fail-closed
   - Latest-per-ticker (781): **95.65%** correct, **0.38%** wrong, 3.97% fail-closed
   - Goal 4 baseline (9,116): **9,052 preserved**, 63 regressed-to-fc, **1 regressed-to-wrong**
   - Cleaned NR-wrong (587): **23 still-wrong, 234 fail-closed, 330 now-correct**
   - `DECISION_FLAG_SHIP_D_DIRECTLY = yes` (verifier-derived)

3. **D's specification (5 calendar-branch guards)**, identified by source strings (Goal 6a's `goal6_candidates.py` is the executable reference):

   ```
   rule_g_strict_direct_recent_prior_calendar
   rule_g_strict_fail_closed_recent_disagreement_calendar
   rule_g_fail_closed_fy_disagreement_calendar
   rule_g_fail_closed_no_prev_short_gap_calendar
   rule_g_fail_closed_same_filing_short_gap_calendar
   ```

   Constraints (all D guards):
   - Use ONLY existing 24h proximity threshold OR existing 150d long-gap threshold (no new time thresholds)
   - No ticker / industry / sector signals
   - No EX-99 / 8-K body / external string parsing
   - No ML / LLM
   - Pure structural reasoning over (filed_8k, prior_created, prev_8k_ts, XBRL year/period, math FY/Q from prior period, calendar shape)

4. **Existing helpers in `quarter_identity.py`** (production code):
   - `_ensure_prior_xbrl(prior, *, neo4j_session)` — hydrates xbrl_year/xbrl_period from DB on demand (Rule F already calls this at line 403)
   - `_period_end_is_calendar_shaped(period)`, `_effective_fye_month(priors, fye_month)`, `_advance_quarter`, `_parse_datetime`, `_parse_date`, etc.
   - `parse_xbrl_fiscal_identity(xbrl_year, xbrl_period)` from `get_quarterly_filings`
   - `period_to_fiscal(year, month, day, fye_month, form_type)` from `fiscal_math`

5. **Goal 4 source strings (must be preserved verbatim)**:
   - Goal 3 prelude (9): `prior_periodic_projection_no_fye`, `prior_periodic_projection_bad_filing_time`, `prior_periodic_projection_no_prior`, `prior_periodic_projection_denylisted_prior_fail_closed`, `prior_periodic_projection_bad_prior_context`, `prior_periodic_projection_future_prior_fail_closed`, `prior_periodic_projection_long_gap_fail_closed`, `prior_periodic_projection_fiscal_math_error`, `prior_periodic_projection_bad_prior_quarter`
   - Rule F (5): `rule_f_direct_recent_prior`, `rule_f_advance_xbrl`, `rule_f_fail_closed_recent_no_xbrl`, `rule_f_fail_closed_missing_signal`, `rule_f_fail_closed_fy_disagreement`
   - Calendar advance (existing): `prior_periodic_projection_qN_to_qM` and `_effective_fye_from_prior_10k` augmentation

   **Total existing source strings: 14 + variable advance sources. All preserved.**

6. **5 new source strings (D adds)**: `rule_g_strict_direct_recent_prior_calendar`, `rule_g_strict_fail_closed_recent_disagreement_calendar`, `rule_g_fail_closed_fy_disagreement_calendar`, `rule_g_fail_closed_no_prev_short_gap_calendar`, `rule_g_fail_closed_same_filing_short_gap_calendar`

7. **Locked decisions still apply** (do NOT relitigate):
   - No ticker allowlists/denylists/per-issuer FY-convention tables
   - No industry/sector classifier rules (E-class is rejected)
   - No EX-99.1 / press-release / 8-K body string parsing in production
   - No new time thresholds beyond 24h / 150d
   - Goal 4's destructive-write guard in orchestrator preserved (do NOT modify orchestrator)

---

## ALGORITHM SCOPE (CRITICAL — read carefully)

**Goal 6c modifies ONLY the calendar-shaped branch of `resolve_quarter_via_prior_periodic`. Rule F's odd_52_53 branch is preserved verbatim. The Goal 3 prelude (cold-start, denylist, bad-context, effective_fye derivation, future-prior, long-gap) is preserved verbatim.**

The current calendar-shaped branch (Goal 4) does:
```
gap_days check (>150 fail) → period_to_fiscal(prior.period, effective_fye, form) → advance_one_quarter → AUTO_OK
```

After Goal 6c, the calendar-shaped branch does:
```
1. Existing future-prior + long-gap fail-close (preserved)
2. Hydrate prior XBRL: top = _ensure_prior_xbrl(top, neo4j_session=neo4j_session)
3. Compute is_recent (24h), xbrl_parsed, math_parsed_prior
4. Guard 1+2 — strict 24h:
   if is_recent:
     if xbrl_parsed is None or math_parsed_prior is None:
        FAIL_CLOSED("rule_g_strict_fail_closed_recent_disagreement_calendar")
     if (xbrl FY != math FY) or (xbrl Q != math Q):
        FAIL_CLOSED("rule_g_strict_fail_closed_recent_disagreement_calendar")
     return AUTO_OK(xbrl FY, xbrl Q, "rule_g_strict_direct_recent_prior_calendar")
5. Guard 3 — non-recent FY-disagreement:
   if (xbrl_parsed is not None and math_parsed_prior is not None
       and str(xbrl FY) != str(math FY)):
      FAIL_CLOSED("rule_g_fail_closed_fy_disagreement_calendar")
6. Guard 4 — no-prev-8K + short-gap:
   if no prev_8k_ts AND _within_existing_short_gap(filed, prior_created):
      FAIL_CLOSED("rule_g_fail_closed_no_prev_short_gap_calendar")
   where _within_existing_short_gap = (0 <= seconds_between < 24h) OR
                                       (0 <= gap_days <= 150)
7. Guard 5 — same-filing-cycle + short-gap:
   if _same_filing_cycle_indicator(prev_8k_ts, prior_created, filed)
      AND _within_existing_short_gap(filed, prior_created):
      FAIL_CLOSED("rule_g_fail_closed_same_filing_short_gap_calendar")
   where _same_filing_cycle_indicator =
      (prev_8k_ts < prior_created <= filed) AND
      (0 <= seconds_between(filed, prior_created) < 24h)
8. Otherwise: existing Goal 3 calendar advance (period_to_fiscal → _advance_quarter
   → AUTO_OK with "prior_periodic_projection_qN_to_qM" + optional
   "_effective_fye_from_prior_10k" augmentation)
```

**Reference implementation**: `earnings-analysis/canary/quarter_resolver/goal6_candidates.py::_calendar_branch_with_candidate_guards` (with `candidate_e=False`). DO NOT IMPORT this from production — re-implement equivalently inline. The canary file exists for measurement; production is its own implementation.

---

## OUTPUTS REQUIRED

### 1. Modified `scripts/earnings/quarter_identity.py`
- 5 new D guards in the calendar-shaped branch only
- Goal 4's Rule F odd_52_53 branch preserved verbatim
- Goal 3 prelude preserved verbatim
- All 14 existing source strings still present + 5 new D source strings
- Public function `resolve_quarter_info(ticker, accession_8k, *, session=None)` signature unchanged
- `safety_action` field still in return dict

### 2. Test additions in `scripts/earnings/test_quarter_identity.py`
Required new test cases (synthetic fixtures + representative real accessions):
- **Strict direct-recent**: synthetic same-event 10-Q filed within 24h, calendar-shaped, XBRL/math agree → AUTO_OK with `rule_g_strict_direct_recent_prior_calendar`
- **Strict recent-disagreement**: synthetic 24h prior with XBRL/math FY mismatch → FAIL_CLOSED with `rule_g_strict_fail_closed_recent_disagreement_calendar`
- **Non-recent FY-disagreement**: synthetic ANF-like prior (XBRL FY ≠ math FY, non-recent) → FAIL_CLOSED with `rule_g_fail_closed_fy_disagreement_calendar`
- **No-prev-8K short-gap**: synthetic prior <24h, no previous earnings 8-K → FAIL_CLOSED with `rule_g_fail_closed_no_prev_short_gap_calendar`
- **Same-filing-cycle short-gap**: synthetic prior <24h, prev 8-K filed BEFORE prior_created → FAIL_CLOSED with `rule_g_fail_closed_same_filing_short_gap_calendar`
- **FCX preservation**: `0000831259-26-000021` still resolves to `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1` (Goal 4 fix maintained)
- **Cleaned-NR-wrong representative**: ADM `0000007084-24-000010` now FAIL_CLOSED or correctly-fires (per goal6a_d_measurement.csv)
- **Cleaned-NR-OK representative**: HAS `0000046080-26-000016` still AUTO_OK Q1 FY2026

All Goal 4 / Goal 5 tests in `test_quarter_identity.py` and `test_quarter_identity_u64.py` MUST still pass.

### 3. (Optional) `GOAL6C_REPORT.md`
- Brief summary
- Confirmation that production matches `goal6a_d_measurement.csv` on all 10,674 rows
- Honest caveats: 24 wrongs remain (23 cleaned-NR + 1 baseline regression); these are documented, expected, and below the 1% threshold

---

## DONE WHEN (the verifier decides)

```bash
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal_6c_implementation.py
```

Verifier hard-locks (every check must pass):

```
G1.   Verifier file + immutable evidence inputs are git-clean
      (verifier, goal6a_d_measurement.csv, cleaned_all_verdicts.json,
       goal4_proven_ok_baseline.csv, sec_52_53_audit/all_verdicts.json,
       ground_truth.csv, needs_review.csv, live_mode_audit.csv)
G2.   scripts/earnings/quarter_identity.py modified — old _STALE_MATCH_DAYS=150
      still GONE; Goal 4 Rule F odd_52_53 sources preserved verbatim;
      ALL 9 Goal 3 prelude sources preserved; ALL 5 new D source strings
      present in the calendar branch
G3.   No production code modified outside allowed paths
      (quarter_identity.py + test_quarter_identity.py +
       test_quarter_identity_u64.py only); orchestrator + fiscal_math +
       guidance files unchanged
G4.   resolve_quarter_info importable; signature unchanged
G5.   FCX 0000831259-26-000021 → Q1_FY2026 / AUTO_OK /
      prior_periodic_projection_q4_to_q1 (Goal 4 fix preserved)
G6.   115 odd_52_53 set still produces EXACTLY 94 OK / 0 WRONG /
      21 FAIL_CLOSED (Rule F preserved)
G7.   No banned patterns in production: no ticker tables, no industry/
      sector keyed constants, no EX-99 / press-release string parsing,
      no external HTTP/sec-api calls
G8.   Production resolver per-row matches goal6a_d_measurement.csv on
      ALL 10,674 audited scoreable rows — exact (outcome, fy, q, source)
      match. NO tolerance. (This is the load-bearing gate: production D
      must equal Goal 6a's measured D exactly.)
G9.   pytest scripts/earnings/test_quarter_identity.py exits 0
G10.  pytest scripts/earnings/test_quarter_identity_u64.py exits 0
G11.  pytest -k write_guard collects ≥1 + exits 0 (Goal 4
      destructive-write guard preserved)
G12.  GOAL6C_REPORT.md (if present) is non-empty + has required
      keywords ("Candidate D", "goal6a_d_measurement", "10,674")
```

If ANY of G1-G11 fails, fix and re-run.

`--fast` flag: G8 samples 200 rows from `goal6a_d_measurement.csv` instead of full 10,674. Bare command = canonical sign-off.

---

## NON-GOALS (do NOT do these)

- Do NOT modify the verifier file (G1 catches it).
- Do NOT modify Rule F's odd_52_53 branch (G6 catches it via 94/0/21).
- Do NOT modify Goal 3's prelude (G2 catches it via missing source strings).
- Do NOT modify the orchestrator's destructive-write guard (G3 + G11 catch it).
- Do NOT touch `fiscal_math.py` — it's pure math used by Class 2/3 consumers.
- Do NOT touch any guidance / harvest / daemon / extraction file. They pick up D automatically via `resolve_quarter_info` lazy import.
- Do NOT import `goal6_candidates.py` from production. It's research-only.
- Do NOT add ticker allowlists, denylists, FY-convention tables, or per-issuer/industry logic.
- Do NOT add EX-99.1 / 8-K body / press-release string parsing in production.
- Do NOT add ML / LLM / sec-api.io / external-network calls in production code path.
- Do NOT change the 24-hour proximity threshold or 150-day long-gap threshold.
- Do NOT relax G8 (per-row exact match against goal6a_d_measurement.csv). If production D differs from Goal 6a's measured D, that's a regression.

---

## OUT-OF-SCOPE / FUTURE

- Production deployment + post-deploy monitoring (separate phase)
- Re-validation of FCX canary outputs after deploy (separate phase)
- Audit of 107 cleaned-NR unclear rows (separate phase if needed)
- Goal 6b discovery to push correct-fire above 96.1% (only if operational signal demands it)
- Class 2 (10-Q/10-K NULL fallback) FY-naming bug — separate goal if/when it surfaces operationally
