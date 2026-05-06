# Goal 5 — Eliminate NR AUTO_OK wrong-writes (Rule G structural extension)

**Status**: ready to fire via `/goal` after verifier is git-committed.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_goal5_implementation.py` (hand-authored — Codex must NOT modify; checked via git diff).
**Pass criterion**: verifier exits 0.
**Honest claim**: Goal 5 closes the NR AUTO_OK wrong-write hole discovered after Goal 4. The Goal 4 NR audit (cleaned, persisted at `earnings-analysis/canary/quarter_resolver/audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json`) confirmed **587 wrong-auto-writes / 144 correct / 107 unclear out of 838 NR AUTO_OK rows** under Goal 4's resolver. Two bug classes account for ~99% of wrongs: (1) Q-only +1 same-event-advance, (2) FY-only +1 off-calendar FY-naming. Both classes already have working safety logic in Rule F's odd_52_53 branch — Goal 5 is a **minimal structural extension** that ports Rule F's two guards (24h direct-recent + XBRL/math FY-agreement) into the calendar-shaped branch where these wrongs occur. Goal 4's hard-locks are preserved (FCX, 9,943 oracle-scored, 0 WRONG). Cleaned NR oracle is the new hard-gate truth.

---

## North star

**Achieve 0 WRONG_AUTO_WROTE on the union of {Goal 4 oracle pool: 9,943 rows} ∪ {Goal 5 cleaned NR oracle: 731 scoreable rows}**, while preserving every row Goal 4 already proved correct (9,116 from G7 + 144 from cleaned NR ok = 9,260 proven-OK rows), without ticker tables, FY-convention maps, EX-99.1 string parsing, or LLM extraction. Fail-closing the cleaned NR wrong rows is acceptable and expected — fail-closing proven-OK rows is a regression.

---

## Pre-flight (you do this BEFORE firing /goal)

### 1. Compute the Goal 4 proven-OK baseline (one-shot, ~80 min)

This produces `earnings-analysis/canary/quarter_resolver/audit_evidence/goal4_proven_ok_baseline.csv` — the per-row registry of Goal 4's 9,116 proven-OK firings on the 9,943 oracle pool. The verifier's G7 hard-locks per-row preservation against this file.

```bash
cd /home/faisal/EventMarketDB
source venv/bin/activate
python3 earnings-analysis/canary/quarter_resolver/audit_evidence/sec_nr_auto_ok_audit/compute_goal4_baseline.py
# verify it produced ~9,116 rows
wc -l earnings-analysis/canary/quarter_resolver/audit_evidence/goal4_proven_ok_baseline.csv
```

### 2. Commit the verifier + audit evidence + prompt + baseline

```bash
git add earnings-analysis/canary/quarter_resolver/verify_goal5_implementation.py \
        earnings-analysis/canary/quarter_resolver/live_mode_audit.csv \
        earnings-analysis/canary/quarter_resolver/audit_evidence/sec_nr_auto_ok_audit/ \
        earnings-analysis/canary/quarter_resolver/audit_evidence/goal4_proven_ok_baseline.csv \
        .claude/plans/goal_5_prompt.md
git commit -m "wip(quarter-resolver): goal 5 verifier + prompt + cleaned NR audit + Goal 4 baseline"
git diff --quiet -- earnings-analysis/canary/quarter_resolver/verify_goal5_implementation.py && echo OK
```

### 3. Stash any unrelated dirty paths under `scripts/` before running the verifier

The verifier's G3 scope check fails if any `scripts/` file outside the allowed list is modified or untracked. Long-standing unrelated dirty paths (e.g., `scripts/earnings/compare_section.py`, `scripts/snapshot_xbrl_in_flight.py`) must be temporarily stashed before each verifier run, exactly as in Goal 4:

```bash
git stash push --include-untracked -m "pre-goal5-pending" -- \
    scripts/earnings/compare_section.py \
    scripts/snapshot_xbrl_in_flight.py
# (run verifier...)
git stash pop
```

---

## The /goal command (copy verbatim into Codex)

```
/goal Implement Goal 5 (close NR AUTO_OK wrong-write hole) exactly as specified in .claude/plans/goal_5_prompt.md, and keep iterating until earnings-analysis/canary/quarter_resolver/verify_goal5_implementation.py exits 0.
```

## Follow-up message (after Codex acknowledges)

```
Read .claude/plans/goal_5_prompt.md in full first. The Goal 1 corpus,
all five prior verifiers (Goals 1, 1.5, 2, 3, 4), the SEC audit
evidence (sec_52_53_audit AND sec_nr_auto_ok_audit), and Goal 4's
production code are reference truth. Production code MAY be modified
— but ONLY scripts/earnings/quarter_identity.py and the test files.
NO ticker allowlists/denylists, NO per-issuer FY-convention tables,
NO EX-99.1 string parsing, NO LLM/ML. Goal 4's Rule F is preserved
verbatim in the odd_52_53 branch; Goal 5 only extends the
calendar-shaped branch.
```

---

## CONTEXT (load-bearing facts; do NOT re-discover)

1. **Goal 4 is committed and verifier-passed.** It substituted Rule F into the odd_52_53 branch only. The calendar-shaped branch was preserved byte-faithful from Goal 3. The FCX bug is fixed (`0000831259-26-000021` → `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1`).

2. **NR AUTO_OK audit (Goal 4's blind spot):** Goal 1's NR set was 922 rows where two-source XBRL/fiscal_math agreement could not be established. 34 odd_52_53 NR rows were SEC-audited as part of Goal 4 evidence; the remaining 888 had no oracle. The Goal 4 resolver was run on those 888, produced AUTO_OK on 838 (50 fail-closed). A 10-bucket parallel review with strict critical-evidence rules + programmatic second-pass + manual flip-check produced **cleaned_all_verdicts.json**: **144 ok / 587 wrong / 107 unclear** (see `audit_evidence/sec_nr_auto_ok_audit/CLEANED_SUMMARY.md` for methodology).

3. **Wrong-row structural taxonomy** (cleaned, see `CLEANED_SUMMARY.md`):
   - **272 Q+1 same-FY** wrongs (resolver advanced one quarter past actual reporting quarter — same-event-advance bug; 266/267 resolver_Q ≡ audited_Q+1)
   - **235 FY+1 same-Q** wrongs (FY-naming drift on off-calendar fiscal years; resolver year-of-end vs issuer year-of-start)
   - **77 Q4→Q1 boundary** wrongs (off-calendar Q4→Q1 transitions where both FY+1 and Q-shift)
   - **3 anomalies** (1 dfy=2 dq=0; 1 dfy=0 dq=-1; 1 dfy=0 dq=2)

4. **Same bug classes already fail-closed/handled by Rule F in the odd_52_53 branch:**
   - Same-event 8-K (prior 10-Q filed within 24h before): Rule F uses prior XBRL FY/Q DIRECTLY (`rule_f_direct_recent_prior`)
   - XBRL FY ≠ math FY for non-recent prior: Rule F fail-closes (`rule_f_fail_closed_fy_disagreement`)

5. **Existing helpers** (use these, do NOT reinvent):
   - `fiscal_math.period_to_fiscal(year, month, day, fye_month, form_type)` → (fy, q)
   - `get_quarterly_filings.parse_xbrl_fiscal_identity(xbrl_year_focus, xbrl_period_focus)` → (fy, q) | None
   - `_period_end_is_calendar_shaped`, `_effective_fye_month`, `_advance_quarter` already in `quarter_identity.py`
   - `_PRIOR_QUERY` with PIT-bound `datetime(p.created) <= datetime($filed_8k)` — preserve

6. **Locked decisions** (do NOT relitigate):
   - **No ticker allowlists/denylists/FY-convention tables.** The cleaned-NR-summary's recommendation for a per-issuer FY table is rejected. Rule F's structural FY-agreement guard handles the FY-naming class.
   - **24h proximity threshold** (Rule F's direct-recent threshold) is empirically calibrated. Re-use; do not change.
   - **150-day long-gap threshold** (calendar-branch fail-close on prior >150 days). Preserve.
   - **8-K periodOfReport ≠ fiscal quarter end** (probe-disproven). Do NOT use.
   - **No EX-99.1 / 8-K body string parsing in production** (D8). Audits MAY use it as oracle; production MUST NOT.
   - **Fail-closed > wrong-write.** Always.

---

## ALGORITHM SCOPE (CRITICAL — read carefully)

**Goal 5 modifies ONLY the calendar-shaped branch of `resolve_quarter_via_prior_periodic`. Rule F's odd_52_53 branch is preserved verbatim. The Goal 3 prelude (cold-start, denylist, bad-context, effective_fye derivation) is preserved verbatim. Goal 4's destructive-write guard in the orchestrator is preserved verbatim.**

The calendar-shaped branch currently does:
```
gap_days check → period_to_fiscal(prior.period, effective_fye, form) → advance_one_quarter → AUTO_OK
```

This is correct for the 9,116 G7 rows. It is wrong for the cleaned-NR-wrong rows (272 Q+1 + 235 FY+1 + 77 boundary + 3 anomalies).

### Candidate matrix

**Candidate A — Goal 4 baseline (no change).** Reference for measuring improvement.

**Candidate B — Rule F-port (24h direct + FY-agreement fail-close).** In the calendar-shaped branch, before computing `period_to_fiscal` + advance:
```
# CRITICAL: hydrate prior XBRL before reading xbrl_year/xbrl_period.
# The pre-fetched `top` from _PRIOR_QUERY often has these as None (the
# OPTIONAL MATCH there only succeeds when there is exactly 1 distinct value).
# Rule F's odd_52_53 branch ALREADY calls _ensure_prior_xbrl at line 403; the
# calendar branch must do the same. Skipping this will cause Rule G to
# fail-close many rows that actually have valid XBRL in the DB.
top = _ensure_prior_xbrl(top, neo4j_session=neo4j_session)

seconds_between = (filed - prior_created).total_seconds()
is_recent = 0 <= seconds_between < 24 * 3600
xbrl_parsed = parse_xbrl_fiscal_identity(top.get("xbrl_year"), top.get("xbrl_period"))

if is_recent:
    if xbrl_parsed is None: return FAIL_CLOSED("rule_g_fail_closed_recent_no_xbrl_calendar")
    return AUTO_OK(xbrl_parsed[0], xbrl_parsed[1], "rule_g_direct_recent_prior_calendar")

# non-recent: compute math; if XBRL FY != math FY, fail-close
math_parsed = period_to_fiscal(period.year, period.month, period.day, effective_fye, form)
if xbrl_parsed is not None and math_parsed is not None:
    if str(xbrl_parsed[0]) != str(math_parsed[0]):
        return FAIL_CLOSED("rule_g_fail_closed_fy_disagreement_calendar")

# else: existing Goal 3 calendar advance unchanged
```

**Candidate C — Rule F-port stricter (24h direct only when XBRL/math agree).** Same as B (including the `_ensure_prior_xbrl` hydration) except the recent path requires XBRL/math agreement:
```
top = _ensure_prior_xbrl(top, neo4j_session=neo4j_session)  # same hydration as B
# ... (same is_recent + xbrl_parsed setup)
if is_recent:
    if xbrl_parsed is None: return FAIL_CLOSED("rule_g_strict_fail_closed_recent_no_xbrl_calendar")
    math_parsed = period_to_fiscal(period.year, period.month, period.day, effective_fye, form)
    if math_parsed is None or str(xbrl_parsed[0]) != str(math_parsed[0]) or str(xbrl_parsed[1]) != str(math_parsed[1]):
        return FAIL_CLOSED("rule_g_strict_fail_closed_recent_disagreement_calendar")
    return AUTO_OK(xbrl_parsed[0], xbrl_parsed[1], "rule_g_strict_direct_recent_prior_calendar")
# (non-recent: same as B)
```

**Candidates D and E — OPTIONAL, Codex-proposed.** Codex MAY propose up to **two** additional simple structural candidates IF the empirical matrix shows A/B/C cannot achieve the 0-WRONG hard gate. Constraints on D/E:
- NO ticker tables / allowlists / denylists / per-issuer FY maps
- NO EX-99.1 / 8-K body / press-release string parsing in production
- NO ML / LLM / sec-api.io
- Each candidate's logic must be explainable in **<10 lines of pseudocode**
- Source strings must follow the `rule_g_*` or `prior_periodic_projection_*` naming convention
- Must be deterministic (no randomness, no time-dependent thresholds beyond the existing 24h/150d)

If D/E candidates are proposed, document them in `GOAL5_REPORT.md` and include them in `goal5_candidate_audit.csv`.

### Selection rule

Pick the candidate that:
1. **Achieves 0 WRONG on cleaned NR oracle (731 scoreable rows: 144 ok ∪ 587 wrong; skip 107 unclear)** — HARD GATE
2. **Achieves 0 WRONG on Goal 4 oracle pool (9,943 rows)** — preserves Goal 4
3. **Preserves all 9,260 proven-OK rows as AUTO_OK with same (fy, q)** — preserves Goal 4 + cleaned NR OK
4. Among candidates passing 1+2+3: choose **highest fire rate** on cleaned NR (highest AUTO_OK count among the 731 scoreable rows)
5. Tie-break by **simplest diff** (fewest lines added vs Goal 4 baseline)

**If no candidate (including D/E proposals) achieves the hard gate, Goal 5 fails and Codex must report what specifically prevents 0 WRONG.** Do NOT relax the gate.

---

## OUTPUTS REQUIRED

### 1. Modified `scripts/earnings/quarter_identity.py`
- Implement the chosen candidate's logic in the calendar-shaped branch ONLY
- Rule F's odd_52_53 branch unchanged
- Goal 3 prelude unchanged
- All Goal 4 source strings preserved + new `rule_g_*` (or equivalent) sources for the chosen candidate's new code paths
- Public function `resolve_quarter_info(ticker, accession_8k, *, session=None)` signature unchanged

### 2. Test additions in `scripts/earnings/test_quarter_identity.py`
Required new test cases for whichever candidate is implemented:
- **Same-event calendar-shaped** (synthetic accession with prior 10-Q `created` within 24h before 8-K, calendar-shaped period): returns AUTO_OK with prior XBRL FY/Q (under B/C)
- **Calendar FY-disagreement** (synthetic ANF-like prior 10-K with XBRL FY != math FY): returns FAIL_CLOSED
- **Non-recent same-Q calendar advance** (existing Goal 4 row, no recent prior): unchanged behavior
- **A representative cleaned-NR-wrong row converted to FAIL_CLOSED**: e.g., ADM `0000007084-24-000010` (was wrong AUTO_OK; should now FAIL_CLOSED)
- **A representative cleaned-NR-ok row preserved**: e.g., HAS `0000046080-26-000016` (still AUTO_OK Q1 FY2026)
- **FCX preservation**: `0000831259-26-000021` still → Q1_FY2026 / AUTO_OK

All Goal 4 tests in `test_quarter_identity.py` and `test_quarter_identity_u64.py` MUST still pass.

### 3. `audit_evidence/sec_nr_auto_ok_audit/goal5_candidate_audit.csv` (aggregate)
Per-candidate **aggregate** empirical results on the cleaned NR oracle (731 scoreable rows). Required columns:
```
candidate, ok_count, wrong_count, fail_closed_count, fire_rate_pct, source_strings_added, lines_added_vs_goal4, notes
```
One row per candidate (A, B, C, plus D/E if proposed). Mark the chosen candidate by including the literal word `chosen` (or `winner`/`selected`/`implemented`) in its `notes` cell.

### 3a. `audit_evidence/sec_nr_auto_ok_audit/goal5_candidate_<X>_per_row.csv` (per-row, per candidate)
**One CSV per candidate**, named with the candidate letter: `goal5_candidate_A_per_row.csv`, `goal5_candidate_B_per_row.csv`, `goal5_candidate_C_per_row.csv` (and D/E if proposed). Each MUST contain one row for every cleaned-NR-scoreable row (731 rows: 144 ok ∪ 587 wrong; the 107 unclear are NOT included). Required columns:
```
accession_8k, ticker, candidate_outcome, candidate_fy, candidate_q
```
- `candidate_outcome` ∈ {`AUTO_OK`, `FAIL_CLOSED`}
- For `AUTO_OK` rows: `candidate_fy` and `candidate_q` are the candidate's output (e.g. `2026`, `Q1`)
- For `FAIL_CLOSED` rows: leave `candidate_fy` and `candidate_q` empty

The verifier independently joins these per-row CSVs against `cleaned_all_verdicts.json` and recomputes the aggregate `ok_count` / `wrong_count` / `fail_closed_count` for each candidate. **Per-row outputs are deterministic, so the aggregate CSV's reported counts must match the recomputed values exactly.** The verifier also runs the production resolver on the same 731 rows and rejects the chosen candidate if its per-row CSV diverges from runtime behavior on any single row. **This is what makes the "best candidate" claim independently verified, not self-reported.**

### 4. `GOAL5_REPORT.md`
- Mission summary (closing NR AUTO_OK wrong-write hole)
- Candidate matrix table with per-candidate scores
- Selection rationale (which candidate won + why)
- Before/after on representative wrongs (e.g., ADM, ADC, ANF)
- Before/after on representative cleaned-NR-OK rows (preservation proof)
- Honest caveats: 107 unclear rows are not gate-checked; live-mode behavior still unobserved

---

## DONE WHEN (the verifier decides)

```bash
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal5_implementation.py
```

Verifier hard-locks (every check must pass):

```
G1.   Verifier + immutable evidence inputs are git-clean (anti-tampering):
      verify_goal5_implementation.py, ground_truth.csv, needs_review.csv,
      live_mode_audit.csv, cleaned_all_verdicts.json,
      goal4_proven_ok_baseline.csv, sec_52_53_audit/all_verdicts.json,
      CLEANED_SUMMARY.md, validation_report.txt — all must be git-tracked
      AND clean vs HEAD. Codex MUST NOT modify any oracle/evidence input.
G2.   scripts/earnings/quarter_identity.py modified — old _STALE_MATCH_DAYS=150
      cascade still GONE; Goal 4's Rule F odd_52_53 sources preserved;
      at least one new rule_g_* (or equivalent) source string present in the
      calendar branch; NO ticker allowlist/denylist/FY-table patterns
G3.   No production code modified outside allowed paths
      (quarter_identity.py + test files); no EX-99.1 string parsing patterns
G4.   resolve_quarter_info importable; signature unchanged
G5.   FCX 0000831259-26-000021 → quarter_label == "Q1_FY2026" AND
      safety_action == "AUTO_OK" (Goal 4 fix preserved)
G6.   Cleaned NR oracle (audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json):
      ALL 587 cleaned-wrong rows → 0 WRONG_AUTO_WROTE (HARD-LOCKED).
      ALL 144 cleaned-ok rows → AUTO_OK with same (cleaned_audited_fy, cleaned_audited_q)
      (HARD-LOCKED, 100% preservation).
      107 unclear rows skipped.
G7.   Goal 4 oracle pool (9,909 GT + 34 SEC-audited NR = 9,943 oracle-scored rows):
      0 WRONG_AUTO_WROTE (HARD-LOCKED, Goal 4 baseline preserved).
      Baseline file MUST contain EXACTLY 9,116 rows with unique accessions
      (matches Goal 4's reported G7 count; tampering check).
      For EVERY row in audit_evidence/goal4_proven_ok_baseline.csv (9,116 rows):
      resolver MUST return AUTO_OK with the same (fy, q) — per-row HARD-LOCK.
      (This catches the silent regression where a candidate fail-closes some
      proven-OK rows and compensates by newly correcting others; aggregate
      count alone would not detect it.)
G8.   115 odd_52_53 set still produces EXACTLY 94 OK / 0 WRONG / 21 FAIL_CLOSED
      (Rule F preserved verbatim).
G9.   pytest scripts/earnings/test_quarter_identity.py exits 0
G10.  Existing PIT-safety tests (test_quarter_identity_u64.py) exit 0
G11.  Existing write-guard test (`pytest -k write_guard`) collects ≥1 + exits 0
      (Goal 4 destructive-write guard preserved)
G12.  Candidate matrix integrity (independent recompute, exact match):
      (a) goal5_candidate_audit.csv exists with rows for at least A, B, C
          and the chosen candidate (notes contains chosen/winner/selected/
          implemented).
      (b) goal5_candidate_<X>_per_row.csv exists for every candidate listed
          in the aggregate CSV; each per-row CSV has 731 rows covering every
          cleaned-NR-scoreable accession exactly once.
      (c) Verifier recomputes aggregate ok/wrong/fail_closed from each per-row
          CSV; reported aggregates MUST exactly equal recomputed values
          (per-row outputs are deterministic, no tolerance).
      (d) Chosen candidate's per-row CSV MUST exactly equal runtime resolver
          behavior on the 731 cleaned-NR-scoreable rows (zero divergence) —
          this proves the implemented production resolver IS the chosen
          candidate, not a different one.
      (e) Selection rule check: chosen candidate has wrong_count == 0 AND
          its ok_count is the maximum among 0-wrong candidates.
G13.  GOAL5_REPORT.md (if present) is non-empty and references "Rule G" (or
      equivalent), "cleaned NR oracle", "0 WRONG_AUTO_WROTE", and the chosen
      candidate by name
G14.  Cleaned NR fire rate reported (metric only, no threshold) in the verifier
      output
```

If ANY of G1-G12 fails, fix and re-run. **Zero wrong-auto-writes is the load-bearing safety bound.**

`--fast` flag: G7 samples 200 rows; G6 still runs ALL 731 scoreable cleaned NR rows (cheap enough to always run full).

---

## NON-GOALS (do NOT do these)

- Do NOT modify the verifier file (G1 catches it).
- Do NOT modify Rule F's odd_52_53 branch (G8 catches it — must still produce 94/0/21).
- Do NOT modify Goal 3's prelude (cold-start / denylist / bad-context / effective_fye derivation).
- Do NOT modify the orchestrator's destructive-write guard (G11 catches it).
- Do NOT add ticker allowlists, denylists, FY-convention tables, or per-issuer logic. (CLEANED_SUMMARY.md's per-issuer table recommendation is REJECTED — locked decision.)
- Do NOT add EX-99.1 / 8-K body / press-release string parsing in production code.
- Do NOT add ML / LLM / sec-api.io / external-network calls in production code path.
- Do NOT change the 24-hour proximity threshold or 150-day long-gap threshold.
- Do NOT modify the Goal 1 corpus, Goal 2/3 deliverables, or any prior-Goal artifact.
- Do NOT preserve any previously-removed legacy constant.
- Do NOT use 8-K's own periodOfReport as a quarter-end signal (probe-disproven).
- Do NOT relax the 0-WRONG hard gate. If no candidate achieves it, report failure honestly.

---

## OUT-OF-SCOPE / FUTURE

- Production deployment + post-deploy monitoring (separate phase).
- Re-validation of the FCX canary outputs after deploy (separate phase).
- Continuous calibration of the 24h / 150d thresholds (separate phase if drift observed).
- Audit of the 107 cleaned-NR unclear rows (separate phase if needed).
- Any handling of new bug classes that emerge from live deployment (separate phase).
