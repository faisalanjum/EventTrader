# Goal 6a — Measurement-only: Candidate D + E warm-start / latest-per-ticker benchmarks

**Status**: ready to fire via `/goal` after verifier is git-committed.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_goal_6a_measurement.py` (hand-authored — Codex must NOT modify; checked via git diff).
**Pass criterion**: verifier exits 0.
**Honest claim**: Goal 6a is a **measurement-only research goal**. It does not modify any production code. It re-implements Candidate D (best lock-respecting Goal 5 candidate) and Candidate E (industry-classifier Goal 5 candidate, included for policy comparison only) in a research-only file under `earnings-analysis/canary/quarter_resolver/`, runs both against the committed cleaned NR + Goal 4 oracle pool, and reports per-subset accuracy on full historical / warm-start / cold-start / latest-per-ticker subsets. The output informs whether to ship D (without further work) or whether Goal 6b discovery is required to recover more correct AUTO_OK rows.

---

## North star

**Measure Candidate D's correct-fire / wrong-fire / fail-closed rates on:**
- (a) full historical scoreable population (10,674 rows: 9,943 oracle pool + 731 cleaned NR scoreable)
- (b) warm-start subset (rows where a PIT-visible prior 10-Q/10-K exists at filing time)
- (c) cold-start subset (rows where no PIT-visible prior periodic exists — complement of warm-start)
- (d) latest-per-ticker live proxy (most-recent earnings 8-K per unique ticker)

**Also measure Candidate E** on the same subsets, for policy comparison only — E is NOT a shipping candidate.

**Decision input** for downstream goals: if D's warm-start correct-fire ≥ 95% AND wrong-fire < 1%, ship D directly. Otherwise, run Goal 6b discovery.

---

## Pre-flight (you do this BEFORE firing /goal)

### 1. Stash any unrelated dirty paths

The verifier's scope check fails on any modified production file. Stash long-standing unrelated paths:

```bash
git stash push --include-untracked -m "pre-goal6a-pending" -- \
    scripts/earnings/compare_section.py \
    scripts/snapshot_xbrl_in_flight.py
```

### 2. Commit verifier + prompt

```bash
git add earnings-analysis/canary/quarter_resolver/verify_goal_6a_measurement.py \
        .claude/plans/goal_6a_prompt.md
git commit -m "wip(quarter-resolver): goal 6a measurement-only verifier + prompt"
git diff --quiet -- earnings-analysis/canary/quarter_resolver/verify_goal_6a_measurement.py && echo OK
```

### 3. After Codex finishes, restore stash

```bash
git stash pop
```

---

## The /goal command (copy verbatim into Codex)

```
/goal Implement Goal 6a (measurement-only benchmark of Candidate D + E across full historical / warm-start / cold-start / latest-per-ticker subsets) exactly as specified in .claude/plans/goal_6a_prompt.md, and keep iterating until earnings-analysis/canary/quarter_resolver/verify_goal_6a_measurement.py exits 0.
```

## Follow-up message (after Codex acknowledges)

```
Read .claude/plans/goal_6a_prompt.md in full first. Goal 6a is
MEASUREMENT-ONLY. You MUST NOT modify any production file under
scripts/earnings/. Specifically:
  - DO NOT touch scripts/earnings/quarter_identity.py
  - DO NOT touch scripts/earnings/earnings_orchestrator.py
  - DO NOT touch scripts/earnings/test_quarter_identity.py
  - DO NOT touch scripts/earnings/test_quarter_identity_u64.py
The research file goal6_candidates.py lives ONLY under
earnings-analysis/canary/quarter_resolver/. It must NOT be imported
by any production code. The verifier hard-locks both invariants.
Goal 5's per-row CSVs are reference artifacts; they are NOT the
gating oracle. The oracle is cleaned_all_verdicts.json (cleaned NR
truth) + goal4_proven_ok_baseline.csv (Goal 4 proven-OK rows) +
ground_truth.csv (GT rows) + sec_52_53_audit/all_verdicts.json
(SEC-audited NR rows). Score Candidate D and Candidate E directly
against those oracles.
```

---

## CONTEXT (load-bearing facts)

1. **Production state today**: Goal 4 in `quarter_identity.py` (commit `e43cfc8` series, currently HEAD `6e715d5`). FCX bug fixed. 0 wrong-writes on 9,943 oracle-scored rows. 5.4% wrong-writes on the broader 10,831 corpus (concentrated on Jan-FYE retailers + same-event filers — see `audit_evidence/sec_nr_auto_ok_audit/CLEANED_SUMMARY.md`).

2. **Goal 5 outcome**: did not ship a production change. D was the best lock-respecting candidate (~0.10% wrong-fire on cleaned NR audited population). E was an industry-classifier candidate (~0% wrong-fire on cleaned NR but used `_*_RISK_INDUSTRIES` constants — rejected as a per-issuer-class proxy violating the locked decision). Per-row CSVs persist for both at `audit_evidence/sec_nr_auto_ok_audit/goal5_candidate_{D,E}_per_row.csv` — **REFERENCE ONLY, NOT TRUTH**.

3. **Why Goal 6a exists**: per-row CSVs from Goal 5 measured D / E only on 731 cleaned-NR-scoreable rows. We need their behavior on the full 10,674 scoreable population (9,943 oracle pool + 731 cleaned NR), partitioned by warm-start vs cold-start vs latest-per-ticker, to make a shipping decision.

4. **Locked decisions still apply**:
   - No ticker allowlists/denylists/per-issuer FY-convention tables
   - No EX-99.1 / 8-K body / press-release string parsing in production (Goal 6a research code may not include this either)
   - No new time thresholds beyond 24h / 150d
   - No ML / LLM / external API calls
   - 8-K periodOfReport ≠ fiscal quarter end (probe-disproven)

5. **Existing helpers** (use these in `goal6_candidates.py`, do NOT reinvent):
   - `fiscal_math.period_to_fiscal(year, month, day, fye_month, form_type)` → (fy, q)
   - `get_quarterly_filings.parse_xbrl_fiscal_identity(xbrl_year_focus, xbrl_period_focus)` → (fy, q) | None
   - `quarter_identity._period_end_is_calendar_shaped`, `_effective_fye_month`, `_advance_quarter`, `_ensure_prior_xbrl`, `_PRIOR_QUERY` (read-only — use the production helpers; do not modify them)

---

## CANDIDATE SPECIFICATIONS (for `goal6_candidates.py`)

### Candidate D (Goal 5's original best lock-respecting candidate, faithful reconstruction)

**Definition**: D is Goal 5's best lock-respecting candidate (audited at 474 ok / 11 wrong / 246 fc on the 731 cleaned-NR scoreable subset). It extends Goal 4's `resolve_quarter_via_prior_periodic` calendar-shaped branch with **five structural guards**, identified by these source strings (visible in Goal 5's `goal5_candidate_audit.csv` row D):

1. `rule_g_strict_direct_recent_prior_calendar` — strict 24h direct-recent (uses existing 24h threshold; XBRL must parse AND XBRL FY+Q agree with math FY+Q from prior period)
2. `rule_g_strict_fail_closed_recent_disagreement_calendar` — 24h prior but XBRL/math disagree → fail-closed
3. `rule_g_fail_closed_fy_disagreement_calendar` — non-recent prior with XBRL FY ≠ math FY → fail-closed
4. `rule_g_fail_closed_no_prev_short_gap_calendar` — no previous earnings 8-K exists for ticker AND prior is within "short gap" → fail-closed
5. `rule_g_fail_closed_same_filing_short_gap_calendar` — same-filing-cycle indicator (e.g., prior 10-Q period overlaps current 8-K's announced period) AND prior is within "short gap" → fail-closed

**Hard constraint on the "short gap" used by guards 4 and 5**: must reuse ONLY the existing locked thresholds (24h proximity OR 150d long-gap). NO new time thresholds (no 72h, no 7d, no 30d, no custom values).

If your reconstruction of guards 4 or 5 cannot be expressed using ONLY the existing 24h or 150d thresholds, then your variant is NOT Candidate D — it's a different candidate that violates the locked decision against new time thresholds. In that case, do NOT measure under the name "D"; either omit it or report under a different name (e.g., `D_with_extra_threshold`) and document the violation explicitly in `GOAL6A_REPORT.md`.

```python
def candidate_d(ticker: str, accession_8k: str, *, neo4j_session) -> dict:
    """Lock-respecting Candidate D = Goal 4 + 5 calendar-branch guards.

    Same calling shape as production resolve_quarter_info(ticker, accession_8k,
    *, session=None). Internally fetches its own row_context and priors
    using existing _QUERY / _PRIOR_QUERY patterns; do NOT take a pre-built
    row_context from the caller.

    Reconstructed faithfully from Goal 5's source-string list; the
    `*_short_gap_*` guards MUST use only the existing 24h proximity
    threshold or the existing 150d long-gap threshold.

    Returns: {"outcome": "AUTO_OK"|"FAIL_CLOSED",
              "fy": "<year>" or "",
              "q": "Q1"|"Q2"|"Q3"|"Q4" or "",
              "source": "<source string>"}
    """

    # 0. Fetch row_context + priors via existing _QUERY / _PRIOR_QUERY
    #    (read-only access to production helpers). This makes candidate_d
    #    self-contained and callable with the same signature as production.

    # 1. Run Goal 4's resolver up through the BRANCH point.
    #    Goal 3 prelude + Rule F's odd_52_53 branch are PRESERVED VERBATIM.

    # 2. In the calendar-shaped branch, BEFORE Goal 3's calendar advance:

    # ── hydrate prior XBRL (matches Rule F's pattern at line 403) ──
    top = _ensure_prior_xbrl(top, neo4j_session=neo4j_session)
    seconds_between = (filed - prior_created).total_seconds()
    is_recent = 0 <= seconds_between < 24 * 3600
    xbrl_parsed = parse_xbrl_fiscal_identity(top.get("xbrl_year"), top.get("xbrl_period"))
    math_parsed_prior = period_to_fiscal(period.year, period.month, period.day,
                                          effective_fye, form)

    # ── Guard 1+2: strict 24h direct-recent / recent-disagreement ──
    if is_recent:
        if xbrl_parsed is None or math_parsed_prior is None:
            return {"outcome": "FAIL_CLOSED", "fy": "", "q": "",
                    "source": "rule_g_strict_fail_closed_recent_disagreement_calendar"}
        if (str(xbrl_parsed[0]) != str(math_parsed_prior[0])
                or str(xbrl_parsed[1]) != str(math_parsed_prior[1])):
            return {"outcome": "FAIL_CLOSED", "fy": "", "q": "",
                    "source": "rule_g_strict_fail_closed_recent_disagreement_calendar"}
        return {"outcome": "AUTO_OK",
                "fy": str(xbrl_parsed[0]), "q": xbrl_parsed[1],
                "source": "rule_g_strict_direct_recent_prior_calendar"}

    # ── Guard 3: non-recent FY-disagreement ──
    if (xbrl_parsed is not None and math_parsed_prior is not None
            and str(xbrl_parsed[0]) != str(math_parsed_prior[0])):
        return {"outcome": "FAIL_CLOSED", "fy": "", "q": "",
                "source": "rule_g_fail_closed_fy_disagreement_calendar"}

    # ── Guard 4: no-previous-8-K + short gap (24h or 150d only) ──
    # Implementation note: "short gap" MUST reuse existing 24h OR 150d
    # threshold. If you need any other interval, this is NOT Candidate D.
    if no_previous_earnings_8k(...) and within_existing_threshold(...):
        return {"outcome": "FAIL_CLOSED", "fy": "", "q": "",
                "source": "rule_g_fail_closed_no_prev_short_gap_calendar"}

    # ── Guard 5: same-filing-cycle + short gap (24h or 150d only) ──
    if same_filing_cycle_indicator(...) and within_existing_threshold(...):
        return {"outcome": "FAIL_CLOSED", "fy": "", "q": "",
                "source": "rule_g_fail_closed_same_filing_short_gap_calendar"}

    # 3. Otherwise: fall through to Goal 3's existing calendar advance.
    #    Return AUTO_OK with the projected (fy, q) and source like
    #    "prior_periodic_projection_q4_to_q1".
```

This is **the original Goal 5 D**, NOT a redefinition. Measure it as is. If the reconstructed D differs from Goal 5's per-row CSV by more than a few rows due to ambiguity in the short_gap reconstruction, document the difference in `GOAL6A_REPORT.md` — the per-row CSV is reference, not truth.

### Candidate E (industry-classifier, comparison-only — DO NOT SHIP)

**Definition**: D's three guards + four hardcoded `_*_RISK_INDUSTRIES` sets keyed on `Company.industry_normalized`. These sets are taken from Goal 5's E (visible in Codex's Goal-5 diff) for measurement purposes ONLY:

```python
_RECENT_XBRL_RISK_INDUSTRIES = {"RentalAndLeasingServices"}
_JAN_ANNUAL_RISK_INDUSTRIES = {"DiscountStores", "Entertainment", "GroceryStores"}
_JAN_ANNUAL_TIGHT_PRIOR_LAG_INDUSTRIES = {"SpecialtyRetail"}
_SAME_FILING_RISK_INDUSTRIES = {"ScientificAndTechnicalInstruments"}
_ANNUAL_RESIDUAL_RISK_INDUSTRIES = {"InsuranceLife"}
```

**Reproduce E faithfully from Goal 5's source-string set** (visible in `goal5_candidate_audit.csv` row E): includes `rule_g_fail_closed_recent_industry_calendar`, `rule_g_fail_closed_jan_annual_industry_calendar`, etc. Codex may need to consult Goal 5's reverted diff via git history (`git log -p -- scripts/earnings/quarter_identity.py` from before the revert is unavailable since the diff was uncommitted) — fallback is to reconstruct E from the source-string list and the prompt's intent.

**Hard rule**: `goal6_candidates.py` documents E **explicitly as RESEARCH-ONLY, NOT a shipping candidate**. Source strings are namespaced under `candidate_e_*` so they cannot be confused with production. The verifier checks E exists for measurement but ALSO checks that E's source strings are NOT present in `scripts/earnings/quarter_identity.py`.

---

## SUBSET DEFINITIONS

**Total scoreable population** = 10,674 rows:
- 9,943 oracle pool: 9,909 GT rows (`ground_truth.csv` truth = `(fy_xbrl, q_xbrl)`) + 34 SEC-audited NR rows from `sec_52_53_audit/all_verdicts.json` (truth = `(audited_fy, audited_q)`)
- 731 cleaned NR scoreable: rows in `cleaned_all_verdicts.json` where `final_verdict ∈ {ok, wrong}` (truth = `(cleaned_audited_fy, cleaned_audited_q)`); the 107 unclear rows are excluded from scoring

**Subsets** (each row in the 10,674 population is classified into exactly one of these, except latest-per-ticker which is a separate filter):

1. **Warm-start** = rows where a prior 10-Q/10-K with `created <= filed_8k` exists in Neo4j (i.e., the production resolver's `_PRIOR_QUERY` returns at least one row). This is determinable at runtime from the existing query.

2. **Cold-start** = complement: rows where `_PRIOR_QUERY` returns zero priors. These are mostly 2023 corpus-edge rows where Goal 4 fail-closes via `prior_periodic_projection_no_prior`.

3. **Latest-per-ticker live proxy** = the most recent (by `filed_8k`) earnings 8-K per unique ticker, intersected with warm-start. This approximates the live arrival pattern (each ticker contributes its latest event once).

---

## OUTPUTS REQUIRED

### 1. `earnings-analysis/canary/quarter_resolver/goal6_candidates.py`
- Research-only module
- Defines `candidate_d(...)` and `candidate_e(...)` per the specifications above
- Module-level docstring states: "RESEARCH-ONLY. Not imported by production. Goal 6a measurement only."
- Imports allowed: `quarter_identity` (for read-only helpers), `fiscal_math`, `get_quarterly_filings`, neo4j driver
- MUST NOT have any side effect on production state

### 2. `earnings-analysis/canary/quarter_resolver/goal6a_d_measurement.csv`
Per-row outcome of Candidate D on every row in the 10,674-row scoreable population. Columns (generic — file name identifies D vs E):
```
accession_8k, ticker, oracle_source, oracle_fy, oracle_q,
warm_start, latest_per_ticker,
outcome, fy, q, source, correct
```
- `oracle_source` ∈ {`GT`, `SEC_5253`, `cleaned_NR`}
- `warm_start` ∈ {`true`, `false`}
- `latest_per_ticker` ∈ {`true`, `false`}
- `outcome` ∈ {`AUTO_OK`, `FAIL_CLOSED`}
- `fy`, `q` empty when `outcome = FAIL_CLOSED`
- `source` is the source string D returned (e.g. `rule_g_strict_direct_recent_prior_calendar`, `prior_periodic_projection_q4_to_q1`, etc.)
- `correct`: `true` if `outcome=AUTO_OK AND (fy, q) == (oracle_fy, oracle_q)`; `false` otherwise

### 3. `earnings-analysis/canary/quarter_resolver/goal6a_e_measurement.csv`
Same schema as #2 but for Candidate E. Identical row set.

### 2/3 candidate function signatures

Both `candidate_d` and `candidate_e` in `goal6_candidates.py` MUST expose this signature so the verifier's G8 can re-run them deterministically:

```python
def candidate_d(ticker: str, accession_8k: str, *, neo4j_session) -> dict:
    """Returns {outcome, fy, q, source}.

    outcome ∈ {"AUTO_OK", "FAIL_CLOSED"}
    fy, q are strings (e.g. "2026", "Q1") for AUTO_OK; "" for FAIL_CLOSED
    source is the matching source string written to the per-row CSV
    """

def candidate_e(ticker: str, accession_8k: str, *, neo4j_session) -> dict:
    """Same shape; namespaced under candidate_e_* internally; not for production."""
```

This signature mirrors production's `resolve_quarter_info(ticker, accession_8k, *, session=None)` and lets the verifier sample N rows, call the candidate, and exact-match against the CSV.

### 4. `earnings-analysis/canary/quarter_resolver/GOAL6A_REPORT.md`
Required tables:

**Table 1 — D measurement by subset:**

| subset | rows | correct_AUTO_OK | wrong_AUTO_OK | fail_closed | correct_pct | wrong_pct | fc_pct |
|---|---|---|---|---|---|---|---|
| Full historical | 10,674 | … | … | … | … | … | … |
| Warm-start | … | … | … | … | … | … | … |
| Cold-start | … | … | … | … | … | … | … |
| Latest-per-ticker | … | … | … | … | … | … | … |

**Table 2 — E measurement by subset** (same columns)

**Table 3 — D vs E delta on each subset** (correct_pct, wrong_pct deltas)

**Decision flags**: at the bottom of the report, state explicitly. ALL flags are **machine-readable** keys parsed by the verifier (G11 + G13) via exact regex match `^\s*<KEY>\s*=\s*<value>\s*$`. The verifier does NOT use permissive integer scanning anywhere — every reported number must appear as an explicit named flag. The verifier asserts each flag's value exactly equals its runtime recompute.

#### Subset raw counts (24 flags) — primary truth for tables 1 & 2

```
DECISION_FLAG_D_FULL_HISTORICAL_CORRECT = <int>
DECISION_FLAG_D_FULL_HISTORICAL_WRONG = <int>
DECISION_FLAG_D_FULL_HISTORICAL_FC = <int>
DECISION_FLAG_D_WARM_START_CORRECT = <int>
DECISION_FLAG_D_WARM_START_WRONG = <int>
DECISION_FLAG_D_WARM_START_FC = <int>
DECISION_FLAG_D_COLD_START_CORRECT = <int>
DECISION_FLAG_D_COLD_START_WRONG = <int>
DECISION_FLAG_D_COLD_START_FC = <int>
DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT = <int>
DECISION_FLAG_D_LATEST_PER_TICKER_WRONG = <int>
DECISION_FLAG_D_LATEST_PER_TICKER_FC = <int>

DECISION_FLAG_E_FULL_HISTORICAL_CORRECT = <int>
DECISION_FLAG_E_FULL_HISTORICAL_WRONG = <int>
DECISION_FLAG_E_FULL_HISTORICAL_FC = <int>
DECISION_FLAG_E_WARM_START_CORRECT = <int>
DECISION_FLAG_E_WARM_START_WRONG = <int>
DECISION_FLAG_E_WARM_START_FC = <int>
DECISION_FLAG_E_COLD_START_CORRECT = <int>
DECISION_FLAG_E_COLD_START_WRONG = <int>
DECISION_FLAG_E_COLD_START_FC = <int>
DECISION_FLAG_E_LATEST_PER_TICKER_CORRECT = <int>
DECISION_FLAG_E_LATEST_PER_TICKER_WRONG = <int>
DECISION_FLAG_E_LATEST_PER_TICKER_FC = <int>
```

#### Derived percentages (4 flags) — informational, must equal `100 * count / total`

```
DECISION_FLAG_D_WARM_START_CORRECT_PCT = <number>
DECISION_FLAG_D_WARM_START_WRONG_PCT = <number>
DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT_PCT = <number>
DECISION_FLAG_D_LATEST_PER_TICKER_WRONG_PCT = <number>
```

#### G9 measurement (3 flags) — Goal 4 baseline preservation

```
DECISION_FLAG_D_GOAL4_BASELINE_PRESERVED = <int>
DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_FC = <int>
DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_WRONG = <int>
```

#### G10 measurement (3 flags) — cleaned NR wrong subset

```
DECISION_FLAG_D_CLEANED_NR_WRONG_STILL_WRONG = <int>
DECISION_FLAG_D_CLEANED_NR_WRONG_FAIL_CLOSED = <int>
DECISION_FLAG_D_CLEANED_NR_WRONG_NOW_CORRECT = <int>
```

#### Ship decision (1 flag) — must satisfy the rule

```
DECISION_FLAG_SHIP_D_DIRECTLY = <"yes" | "no">
```

**Rule (verifier-checked exactly)**: `DECISION_FLAG_SHIP_D_DIRECTLY = "yes"` IF AND ONLY IF all four conditions hold, computed from the raw subset counts above (not from PCT flags, to avoid rounding ambiguity):

- D warm-start correct rate `(D_WARM_START_CORRECT / total)` ≥ 95.0%
- D warm-start wrong rate `(D_WARM_START_WRONG / total)` < 1.0%
- D latest-per-ticker correct rate ≥ 95.0%
- D latest-per-ticker wrong rate < 1.0%

The verifier independently derives `expected_ship` from these conditions and rejects the report if the reported `SHIP_D_DIRECTLY` value differs. Codex MUST NOT write `"yes"` unless all four conditions hold.

**Total: 35 explicit DECISION_FLAGs** (24 raw counts + 4 PCT + 6 measurement + 1 ship).

---

## DONE WHEN (the verifier decides)

```bash
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal_6a_measurement.py
```

Verifier hard-locks (every check must pass):

```
G1.   Verifier file is git-clean (anti-tampering)
G2.   Immutable evidence inputs are git-clean (cleaned_all_verdicts.json,
      goal4_proven_ok_baseline.csv, sec_52_53_audit/all_verdicts.json,
      ground_truth.csv, needs_review.csv, live_mode_audit.csv,
      CLEANED_SUMMARY.md, validation_report.txt)
G3.   ZERO production code changes:
        scripts/earnings/quarter_identity.py = unchanged at HEAD
        scripts/earnings/earnings_orchestrator.py = unchanged at HEAD
        scripts/earnings/test_quarter_identity.py = unchanged at HEAD
        scripts/earnings/test_quarter_identity_u64.py = unchanged at HEAD
      ANY diff in scripts/earnings/ outside test fixtures fails the gate.
G4.   goal6_candidates.py exists at canary path; module docstring contains
      "RESEARCH-ONLY"; module is NOT imported anywhere under scripts/.
G5.   E's industry-classifier source strings (e.g. rule_g_*_industry_*,
      rule_g_jan_annual_industry_*) are NOT present in scripts/earnings/
      quarter_identity.py (anti-leak from research into production).
G6.   goal6a_d_measurement.csv exists with required columns and exactly
      10,674 unique-accession rows.
G7.   goal6a_e_measurement.csv exists with required columns and exactly
      10,674 unique-accession rows; row set identical to D's.
G8.   Determinism (TRUE re-run): the verifier opens a Neo4j session,
      samples 50 rows from D's per-row CSV (fixed seed) and 50 rows
      from E's, calls candidate_d / candidate_e on each, and asserts
      the (outcome, fy, q, source) tuple matches the CSV row EXACTLY.
      Any mismatch fails. This proves the CSV is what the candidate
      actually produces, not a self-reported number.
G9.   D's measurement on the 9,116-row Goal 4 baseline subset is
      RECOMPUTED and reported (preserved / regressed-to-FC /
      regressed-to-wrong counts). The verifier does NOT fail on
      magnitude — it fails only if reported counts ≠ recomputed
      counts. Magnitude feeds the SHIP_D_DIRECTLY flag, not the gate.
G10.  D's measurement on the 587 cleaned-NR-wrong subset is
      RECOMPUTED and reported (still-wrong / now-fc / now-correct
      counts). The verifier does NOT fail because D has residual
      wrongs — it fails only if reported counts ≠ recomputed
      counts. Magnitude feeds the SHIP_D_DIRECTLY flag, not the gate.
G11.  GOAL6A_REPORT.md exists, contains Tables 1, 2, 3 with all
      required cells filled, and declares the
      DECISION_FLAG_SHIP_D_DIRECTLY value (yes/no).
G12.  Subset row counts reconcile:
        warm_start + cold_start = 10,674
        latest_per_ticker count == number of unique tickers in scoreable set
G13.  Aggregate counts in GOAL6A_REPORT.md exactly equal independent
      recompute from the per-row CSVs (no tolerance — deterministic).
      In addition, the explicit DECISION_FLAG keys for G9 baseline
      measurement (preserved / regressed-fc / regressed-wrong) and
      G10 cleaned-NR-wrong measurement (still-wrong / fc / now-correct)
      are parsed by exact key match and must equal the verifier's
      runtime recompute (no permissive integer scanning).
```

If ANY of G1-G13 fails, fix and re-run.

`--fast` flag: G6/G7 sample 100 rows for the determinism check. G9/G10 still run on full subsets (cheap relative to candidate execution).

---

## NON-GOALS (do NOT do these)

- Do NOT modify `scripts/earnings/quarter_identity.py` or any other production file (G3 catches it).
- Do NOT make `goal6_candidates.py` importable from production (G4 catches imports).
- Do NOT promote E's source strings into production (G5 catches it).
- Do NOT use Goal 5 per-row CSVs as the gating oracle. They are reference artifacts. The gating oracle is `cleaned_all_verdicts.json` + `goal4_proven_ok_baseline.csv` + `ground_truth.csv` + `sec_52_53_audit/all_verdicts.json`.
- Do NOT add ticker tables, FY-convention tables, EX-99.1 parsing, ML/LLM, or new time thresholds beyond 24h/150d.
- Do NOT ship a production patch. Goal 6a is measurement-only.
- Do NOT modify the verifier file (G1 catches it).
- Do NOT mark the goal complete unless verifier exits 0.

---

## OUT-OF-SCOPE / FUTURE

- Goal 6b discovery (only fires if 6a's DECISION_FLAG_SHIP_D_DIRECTLY = "no")
- Production implementation of D or any successor (separate goal)
- Production deployment + post-deploy monitoring (separate phase)
- Audit of the 107 cleaned-NR unclear rows (separate phase if needed)
