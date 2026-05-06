# Goal 4 — Production Implementation: Rule F resolver + orchestrator write-guard

**Status**: ready to fire via `/goal` after verifier is git-committed.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py` (hand-authored — Codex must NOT modify; checked via git diff).
**Pass criterion**: verifier exits 0.
**Honest claim**: Goal 4 ships the empirically-proven Rule F resolver into `scripts/earnings/quarter_identity.py` plus a destructive-write guard in the orchestrator. The verifier hard-locks 0 WRONG_AUTO_WROTE on the GT set and exact 94/0/21 outcome on the 115 odd_52_53 test set.

---

## North star

Replace the FCX-bug-causing `_STALE_MATCH_DAYS=150` cascade with `prior_periodic_projection` + **Rule F** (52/53-week safety) + write-guard. **Zero verified WRONG_AUTO_WROTE across all rows that have an oracle: 9,909 GT (corpus xbrl/math agreement) + 34 SEC-audited NR rows = 9,943 oracle-scored rows.** The other 888 NR rows (no oracle) are run and rates reported, but cannot be truth-checked. Empirically projected ~99.6% live-fire on latest-per-ticker, 0% destructive writes on oracle-scored rows.

---

## Pre-flight (you do this BEFORE firing /goal)

```bash
cd /home/faisal/EventMarketDB
git add earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py \
        earnings-analysis/canary/quarter_resolver/audit_evidence/sec_52_53_audit/ \
        .claude/plans/goal_4_prompt.md
git commit -m "wip(quarter-resolver): goal 4 verifier + prompt + sec audit evidence"
git diff --quiet -- earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py && echo OK
```

---

## The /goal command (copy verbatim into Codex)

```
/goal Implement Rule F production resolver + orchestrator destructive-write guard exactly as specified in .claude/plans/goal_4_prompt.md, and keep iterating until earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py exits 0.
```

## Follow-up message (after Codex acknowledges)

```
Read .claude/plans/goal_4_prompt.md in full first. The Goal 1 corpus,
all four prior verifiers, and the SEC audit evidence are immutable.
Production code MAY be modified — but ONLY scripts/earnings/quarter_identity.py
and the orchestrator destructive-write entry points listed in the prompt.
No ticker allowlists, no ticker denylists, no per-issuer FY-convention tables,
no special PEP/KR/AAP logic. Rule F is the only NEW logic; existing safety
guards stay intact.
```

---

## CONTEXT (load-bearing facts; do NOT re-discover)

1. **Goal 3 produced `prior_periodic_projection`** (in `live_candidates.py`) — already verifier-passed at the candidate level. Goal 4 ports this into production code.

2. **Empirical Rule F result on 115 odd_52_53 test set** (committed at `audit_evidence/`):
   - Rule F: **94 OK / 0 WRONG / 21 FAIL_CLOSED**
   - Rule D (without FY agreement guard): 110 OK / 5 WRONG / 0 FAIL_CLOSED ← unsafe, 5 GT-violating wrongs
   - Rule B (XBRL only): 99 OK / 16 WRONG ← LEVI/PEP/KR/NTAP fail
   - Rule A (math only): 79 OK / 36 WRONG ← AAP/ACI/PEP/etc fail
   Rule F is the empirically-proven safest design.

3. **8-K periodOfReport ≠ fiscal quarter end** (probe-disproven 2026-05-05). Do NOT use 8-K's own periodOfReport as a quarter-end signal.

4. **Existing helpers** (use these, do NOT reinvent):
   - `fiscal_math.period_to_fiscal(year, month, day, fye_month, form_type)` → (fy, q)
   - `get_quarterly_filings.parse_xbrl_fiscal_identity(xbrl_year_focus, xbrl_period_focus)` → (fy, q) | None
   - `get_quarterly_filings.XBRL_DENY_PERIODIC_ACCESSIONS` (denylist set)
   - `fye_month.get_fye_month(ticker, session)`

5. **24-hour proximity threshold** is empirically calibrated (PEP/LEVI same-event 8-K filed within minutes/hours of the 10-Q). Do NOT change without re-running the rule matrix probe.

6. **Long-gap threshold = 150 days** (gap between prior periodic's `created` and 8-K's `filed_8k`). This is what Goal 3's `live_candidates.py` uses at line 185 — already proven by the Goal 3 verifier. **Different concept from production's old `_STALE_MATCH_DAYS=150`**: the old constant gated whether to ACCEPT a stale match (the FCX bug). The new 150-day gap is the LONG-GAP fail-closed threshold (refuse to advance from a prior >150 days old). Same number, opposite policy. **Use 150 days for the gap check.**

---

## ALGORITHM SCOPE (CRITICAL — read carefully)

**Goal 4's resolver = Goal 3's `_prior_periodic_projection` (in `live_candidates.py:154-207`) ported byte-faithfully into production, with EXACTLY ONE substitution: the `odd_52_53_week_prior_fail_closed` branch (line 180) is replaced by Rule F.**

All other Goal 3 logic must be preserved including:
- `_effective_fye_month(priors, fye_month)` — derives effective FYE from most recent calendar-shaped 10-K (line 144-151)
- The exact branch order: cold-start → effective_fye → top prior → denylist → bad-context → odd_52_53 (NOW Rule F) → gap → math
- Source string augmentation: `_effective_fye_from_prior_10k` appended when `effective_fye != fye_month` (line 205-206)
- Long-gap check (>150 days) ONLY on calendar-shaped flow (Goal 3 had it after the odd_52_53 fail-closed; Rule F's branch handles its own logic without this gap check, matching the empirically-tested 94/0/21 outcome)

`_effective_fye` MUST be passed to `period_to_fiscal` in BOTH branches (calendar-shaped path AND Rule F's odd-52/53 path) so the FY-agreement check uses the same effective FYE Goal 3 would have used.

Codex MAY port `_period_end_is_calendar_shaped`, `_effective_fye_month`, `_adjusted_fye_from_annual_period`, `_advance_quarter`, etc. byte-identical from `live_candidates.py` into `quarter_identity.py` (or import them, depending on the cleanest dependency direction). Do NOT reinvent.

## PSEUDOCODE (implement exactly — preserves Goal 3 structure with Rule F substitution)

```python
def resolve_quarter_via_prior_periodic(row_context, *, neo4j_session):
    """Goal 4 production resolver. Mirrors Goal 3 `_prior_periodic_projection`
    structure EXACTLY; only the odd_52_53 branch is replaced by Rule F."""

    # ── Goal 3 prelude (unchanged) ──
    fye_month = _parse_fye(row_context.get("fye_month"))
    if fye_month is None:
        return _result(None, None,
                       "prior_periodic_projection_no_fye", "NO_RESOLUTION")

    filed = _parse_datetime(row_context.get("filed_8k"))
    if filed is None:
        return _result(None, None,
                       "prior_periodic_projection_bad_filing_time", "NO_RESOLUTION")

    priors = _prior_rows(row_context, neo4j_session=neo4j_session)
    if not priors:
        return _result(None, None,
                       "prior_periodic_projection_no_prior", "FAIL_CLOSED")

    # ── Goal 3: effective FYE from prior 10-K (PRESERVE) ──
    effective_fye = _effective_fye_month(priors, fye_month)
    top = priors[0]

    if top.get("accession") in _DENY_PRIOR_ACCESSIONS:
        return _result(None, None,
                       "prior_periodic_projection_denylisted_prior_fail_closed",
                       "FAIL_CLOSED")

    period = _parse_date(top.get("period"))
    prior_created = _parse_datetime(top.get("created"))
    form = top.get("form") or ""
    if period is None or prior_created is None or form not in {"10-Q", "10-K"}:
        return _result(None, None,
                       "prior_periodic_projection_bad_prior_context",
                       "NO_RESOLUTION")

    # ── BRANCH: odd 52/53 vs calendar-shaped ──
    if not _period_end_is_calendar_shaped(period):
        # ═══════════════════════════════════════════════════════
        # ODD 52/53 — Rule F (NEW; replaces old fail-closed)
        # Empirically tested 94 OK / 0 WRONG / 21 FAIL_CLOSED on 115 set.
        # ═══════════════════════════════════════════════════════
        seconds_between = (filed - prior_created).total_seconds()
        is_recent = 0 <= seconds_between < 24 * 3600

        xbrl_parsed = parse_xbrl_fiscal_identity(
            top.get("xbrl_year"), top.get("xbrl_period")
        )

        if is_recent:
            # Same-event 8-K: prior 10-Q just filed; use its label directly.
            if xbrl_parsed is None:
                return _result(None, None,
                               "rule_f_fail_closed_recent_no_xbrl",
                               "FAIL_CLOSED")
            return _result(str(xbrl_parsed[0]), xbrl_parsed[1],
                           "rule_f_direct_recent_prior", "AUTO_OK")

        # Non-recent: must have BOTH XBRL and math signals AND they must agree.
        try:
            math_parsed = period_to_fiscal(
                period.year, period.month, period.day,
                effective_fye, form,        # use SAME effective FYE
            )
        except Exception:
            math_parsed = None

        if xbrl_parsed is None or math_parsed is None:
            return _result(None, None,
                           "rule_f_fail_closed_missing_signal",
                           "FAIL_CLOSED")
        if str(xbrl_parsed[0]) != str(math_parsed[0]):
            return _result(None, None,
                           "rule_f_fail_closed_fy_disagreement",
                           "FAIL_CLOSED")

        fy, q = _advance_quarter(int(xbrl_parsed[0]), str(xbrl_parsed[1]))
        return _result(fy, q, "rule_f_advance_xbrl", "AUTO_OK")

    # ═══════════════════════════════════════════════════════
    # CALENDAR-SHAPED PRIOR — Goal 3 behavior UNCHANGED.
    # Currently-firing 9,860 rows enter here. MUST NOT CHANGE.
    # ═══════════════════════════════════════════════════════
    gap_days = (filed.date() - prior_created.date()).days
    if gap_days < 0:
        return _result(None, None,
                       "prior_periodic_projection_future_prior_fail_closed",
                       "FAIL_CLOSED")
    if gap_days > 150:
        return _result(None, None,
                       "prior_periodic_projection_long_gap_fail_closed",
                       "FAIL_CLOSED")

    try:
        prior_fy, prior_q = period_to_fiscal(
            period.year, period.month, period.day,
            effective_fye, form,            # effective FYE preserved
        )
    except Exception:
        return _result(None, None,
                       "prior_periodic_projection_fiscal_math_error",
                       "NO_RESOLUTION")

    advanced = _advance_quarter(int(prior_fy), str(prior_q))
    if advanced is None:
        return _result(None, None,
                       "prior_periodic_projection_bad_prior_quarter",
                       "NO_RESOLUTION")

    fy, q = advanced
    source = f"prior_periodic_projection_{prior_q.lower()}_to_{q.lower()}"
    if effective_fye != fye_month:
        source += "_effective_fye_from_prior_10k"
    return _result(fy, q, source, "AUTO_OK")


def advance_one_quarter(fy, q):
    if q == 'FY':
        q = 'Q4'
    n = int(str(q).replace('Q', ''))
    if n == 4:
        return (int(fy) + 1, 'Q1')
    return (int(fy), f'Q{n+1}')
```

---

## OUTPUTS REQUIRED

### 1. Modified `scripts/earnings/quarter_identity.py`
- Replace the `_STALE_MATCH_DAYS=150` cascade with the Rule F resolver above
- Public function `resolve_quarter_info(ticker, accession_8k, *, session=None)` keeps its existing return shape (`quarter_label`, `quarter_identity_source`, etc.) — but the underlying logic is Rule F
- New `safety_action` field added to the return dict: `"AUTO_OK" | "FAIL_CLOSED"`
- All sources must match the Goal 3 preserved source contract plus Rule F:
  ```
  prior_periodic_projection_no_fye
  prior_periodic_projection_bad_filing_time
  prior_periodic_projection_no_prior
  prior_periodic_projection_denylisted_prior_fail_closed
  prior_periodic_projection_bad_prior_context
  prior_periodic_projection_future_prior_fail_closed
  prior_periodic_projection_long_gap_fail_closed
  prior_periodic_projection_fiscal_math_error
  prior_periodic_projection_bad_prior_quarter
  prior_periodic_projection_{prior_q}_to_{q}
  prior_periodic_projection_{prior_q}_to_{q}_effective_fye_from_prior_10k
  rule_f_direct_recent_prior
  rule_f_advance_xbrl
  rule_f_fail_closed_recent_no_xbrl
  rule_f_fail_closed_missing_signal
  rule_f_fail_closed_fy_disagreement
  ```

### 2. Orchestrator destructive-write guard
- Locate the orchestrator entry point that does directory writes for earnings 8-Ks (per existing codebase: `scripts/earnings/earnings_orchestrator.py` or similar)
- Add a guard: refuse to write/delete the event directory if `safety_action != "AUTO_OK"`
- For non-AUTO_OK cases: log the accession + reason, write to a quarantine path, surface via existing error-reporting channel

### 3. Test additions in `scripts/earnings/test_quarter_identity.py` (or new test file)
Required test cases (ALL MUST PASS):
- **FCX `0000831259-26-000021`** → returns Q1 FY2026 (the original bug)
- **PEP `0000077476-26-000019`** → returns Q1 FY2026 via direct-recent path (NOT advance)
- **LEVI `0000094845-24-000059`** → returns Q3 FY2024 via direct-recent path
- **AAP `0001158449-24-000236`** → returns Q3 FY2024 via XBRL advance (NOT math advance)
- **PSTG `0001628280-23-040217`** (empirically-verified GT-mismatch from rule-matrix probe) → correctly resolved by Rule F's XBRL path
- **KR `0001104659-25-019465`** → returns FAIL_CLOSED (FY disagreement)
- **NTAP `0001193125-25-297164`** → returns FAIL_CLOSED (FY disagreement)
- **Long-gap test**: synthetic accession with prior >150 days old → FAIL_CLOSED
- **Denylist test**: prior in XBRL_DENY_PERIODIC_ACCESSIONS → FAIL_CLOSED
- **Cold-start test**: ticker with no prior periodic → FAIL_CLOSED
- **Regression suite**: ALL 9,860 currently-firing accessions from Goal 3's `live_mode_audit.csv` (canonical sign-off) — all must return AUTO_OK with the same (fy, q). `--fast` mode samples 100 for iteration only. Rule F replaces ONLY the odd_52_53 branch, so currently-firing rows must be preserved (no fail-closed regressions in full mode).

### 4. (Optional) `GOAL4_REPORT.md`
- Brief summary of changes
- Before/after on FCX (production wrote Q4 FY2025; new resolver writes Q1 FY2026)
- Test counts, regression-suite pass

---

## DONE WHEN (the verifier decides)

```bash
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py
```

Verifier hard-locks (every check must pass):

```
G1.   Verifier file is git-clean (anti-tampering)
G2.   scripts/earnings/quarter_identity.py modified — old _STALE_MATCH_DAYS=150
      cascade GONE; new Rule F sources present in the source enum
G3.   No production code modified outside the allowed paths
      (quarter_identity.py + orchestrator entry point + test files)
G4.   resolve_quarter_info importable; signature unchanged
G5.   115 odd_52_53 set produces EXACTLY 94 OK / 0 WRONG / 21 FAIL_CLOSED
      (read accessions from audit_evidence/sec_52_53_audit/all_verdicts.json
       + Goal 1 GT subset)
G6.   FCX 0000831259-26-000021 → quarter_label == "Q1_FY2026" AND
      safety_action == "AUTO_OK" AND
      source == "prior_periodic_projection_q4_to_q1"
G7.   FULL-CORPUS SAFETY (default mode): runs new resolver on ALL
      9,909 GT rows + 34 SEC-audited NR rows = 9,943 oracle-scored rows.
      HARD-LOCKED: 0 WRONG_AUTO_WROTE.
      `--fast` mode samples 100 for iteration; bare command (no flags)
      is canonical sign-off and must run all 9,943.
      Note: the 888 unaudited NR rows are NOT truth-scored (no oracle),
      so the 0-wrong claim is on the 9,943 oracle-verified rows only.
G7b.  REGRESSION (default mode): all 9,860 currently-firing rows from
      Goal 3's live_mode_audit.csv must still AUTO_OK with the same
      (fy, q). HARD-LOCKED in full mode: 0 changed-OK AND 0 newly-fail-
      closed. Coverage cannot silently shrink. `--fast` mode samples
      100 (lenient on fail-closed due to sample bias).
G8.   pytest scripts/earnings/test_quarter_identity.py exits 0
G9.   Write-guard: `pytest -k write_guard` collects ≥1 test AND exits 0
      (verifier actually runs the pytest, not just lints the file)
G10.  GOAL4_REPORT.md (if produced) is non-empty and references "Rule F"
      + "FCX" + "0 WRONG_AUTO_WROTE"
```

If ANY of G1-G9 fails, fix and re-run. **Zero wrong-auto-writes is the load-bearing safety bound.**

---

## NON-GOALS (do NOT do these)

- Do NOT modify the verifier file (G1 catches it).
- Do NOT add ticker allowlists, denylists, FY-convention tables, or per-issuer logic.
- Do NOT change the 24-hour proximity threshold or 150-day long-gap threshold.
- Do NOT modify the Goal 1 corpus, Goal 2/3 deliverables, or any prior-Goal artifact.
- Do NOT touch any production code outside `quarter_identity.py` + the orchestrator's destructive-write entry point + the test files.
- Do NOT use 8-K's own periodOfReport as a quarter-end signal (probe-disproven).
- Do NOT preserve the old `_STALE_MATCH_DAYS=150` constant or any of its variants.
- Do NOT add EX-99.1 string parsing, sec-api.io, or LLM extraction.

---

## OUT-OF-SCOPE / FUTURE

- Production deployment + post-deploy monitoring (separate phase)
- Re-validation of the FCX canary outputs after deploy (separate phase)
- Continuous calibration of the 24h / 150d thresholds (separate phase if drift observed)
