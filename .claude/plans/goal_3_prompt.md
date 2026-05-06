# Goal 3 — Live-Mode Resolver Discovery + PIT-Safe Candidate Benchmark

**Status**: ready to fire via `/goal` after verifier is git-committed.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_live_mode_resolver.py` (hand-authored — Codex must NOT modify; checked via git diff).
**Pass criterion**: verifier exits 0.
**Honest claim**: Goal 3 discovers and benchmarks PIT-safe live-mode resolver candidates against the Goal 1 corpus. The verifier hard-fails ONLY on (a) future-data leakage in candidate code, (b) any wrong auto-write, (c) structural artifact issues. Achievable would_fire rate is REPORTED, not gated. The decision about whether the rate is acceptable for production is a human/strategic decision, made AFTER Goal 3, not by the verifier.

---

## North star (load-bearing)

**≥99.9% of live earnings 8-Ks must fire predictions correctly** in production. Goal 3's job is to discover whether that target is achievable with PIT-available signals only. If yes, propose the best candidate. If no, classify what's missing and surface the residual.

**Goal 3 is NOT permitted to assume the 99.9% target is achievable.** Empirical probe (2026-05-05) confirmed that 8-K's own `periodOfReport` field is the SEC Date of Report (= filing date), NOT the fiscal quarter end. Goal 2's recommended `periodic_fiscal_math` candidate relies on the matched periodic's `period_of_report`, which at PIT does not exist for ~85-90% of live 8-Ks (the same-quarter 10-Q hasn't filed yet). Therefore Goal 3 must benchmark live-available signals other than 8-K periodOfReport-as-quarter-end.

---

## Pre-flight (you do this BEFORE firing /goal)

```bash
cd /home/faisal/EventMarketDB
# Verifier must be committed so the git-diff freeze check has a baseline
git add earnings-analysis/canary/quarter_resolver/verify_live_mode_resolver.py \
        .claude/plans/goal_3_prompt.md
git commit -m "wip(quarter-resolver): goal 3 verifier + prompt"
git diff --quiet -- earnings-analysis/canary/quarter_resolver/verify_live_mode_resolver.py && echo OK
```

If the commit step is skipped, the verifier will fail at L1 with exit code 2.

---

## The /goal command (copy verbatim into Codex)

```
/goal Discover and benchmark PIT-safe live-mode resolver candidates exactly as specified in .claude/plans/goal_3_prompt.md, and keep iterating until earnings-analysis/canary/quarter_resolver/verify_live_mode_resolver.py exits 0.
```

## The follow-up message (after /goal acknowledges)

```
Read .claude/plans/goal_3_prompt.md in full first. The Goal 1 corpus at
earnings-analysis/canary/quarter_resolver/{ground_truth.csv, needs_review.csv}
is the benchmark — do not modify it. The Goal 1 verifier
(verify_ground_truth_corpus.py), the Goal 1.5 verifier
(verify_audit_packets.py), the Goal 2 verifier
(verify_shadow_validator.py), and the Goal 3 verifier
(verify_live_mode_resolver.py) are all immutable. Do not modify production
code in scripts/earnings/*.py. Stay within
earnings-analysis/canary/quarter_resolver/ and /tmp/ for any scratch artifacts.
The verifier has only one mode (no `--fast`/`--full` distinction); run it with no flags
each time. The 99.9% would_fire rate is the north star but NOT verifier-locked — surface
what's empirically achievable.
```

---

## Goal 3 mission

Empirically discover the best PIT-safe live-mode resolver. Two distinct deliverables:

**Universe contract (LOCKED — read carefully)**:

- **Scored correctness benchmark = 10,831 rows** (Goal 1 corpus = 9,909 GT + 922 NR). This is the ONLY universe where the verifier checks per-row correctness. Goal 1 GT rows have an oracle (corpus_fy/q); NR rows do not.
- **NR rows cannot prove correctness** — AUTO_OK on NR is `AUTO_ON_UNCERTAIN_ROW`, NEVER counts as a "correct" fire.
- The broader earnings 8-K universe (10,995 rows including `daily_stock IS NULL` filings) is REPORTING-ONLY context for prior-periodic availability — the verifier does NOT score those extra 164 rows. Do NOT claim live-mode correctness on 10,995; only on 10,831.

**A. Build a PIT-safe candidate benchmark.**
For every one of the **10,831 Goal 1 corpus rows**, simulate live-mode resolution at PIT (filed_8k timestamp). Each candidate function must work using ONLY data available at the moment the 8-K was filed:
- The 8-K's own filing timestamp (`filed_8k`)
- The 8-K's own ticker
- The 8-K's own accession_8k
- The company's `fye_month`
- Any Neo4j query the candidate wants to run, BUT only with PIT-bound clauses (`created <= filed_8k` or `created <= $filed_8k`).

**B. Mandatory candidates** (≥3 distinct functions required):
1. `candidate_live_prior_periodic_projection` — anchor on prior 10-Q/10-K, advance 1 quarter
2. `candidate_live_lag_window` — filing_date + FYE + reporting-lag heuristic (NO prior periodic dependency; serves as cold-start fallback)
3. `candidate_live_hybrid_agreement` — both A and B must agree → AUTO_OK; cold-start (B-only) → NEEDS_REVIEW; disagree → FAIL_CLOSED

The hybrid is expected to be the recommended winner, but the report MUST report each candidate's metrics SEPARATELY so we can see prior-periodic-only vs lag-window-only vs hybrid behavior independently.

**C. Recommend the best candidate based on empirical performance.**
The recommended candidate must:
- Have **zero WRONG_AUTO_WROTE** across all 10,831 corpus rows (the absolute safety bound — verifier hard-fails otherwise)
- Maximize would_fire rate AND correct_rate_on_gt
- Provide explicit residual classification: which rows fail closed, why, and what additional signal would be needed to resolve them

The 99.9% would_fire target is the north star, NOT a verifier hard-pass criterion. Goal 3's REPORT must explicitly state whether 99.9% is achievable AND show by FYE bucket / 52-53-week / Q4 / non-Dec-FYE breakdowns.

---

## CONTEXT (do NOT spend budget rediscovering — confirmed facts)

1. **Goal 1 corpus** at `earnings-analysis/canary/quarter_resolver/{ground_truth.csv, needs_review.csv}`. Total 10,831 rows = 9,909 GT + 922 NR. NR breakdown: not_same_event_periodic 495, xbrl_math_disagree 391, proximity_rejected 26, denylist 6, no_xbrl 4, no_fye 0.

2. **Empirical probe findings (2026-05-05)**:
   - **Probe 1 — 8-K `periodOfReport` is NOT fiscal quarter end**:
     - All 10,995 earnings 8-Ks have `periodOfReport` populated
     - 91.1% exactly equal the filing date (event-date semantics, NOT fiscal-period)
     - 6.5% within 1-5 days of filing date
     - Conclusion: do NOT use 8-K periodOfReport as a quarter-end signal.
   - **Probe 2 — prior periodic availability** (100-row random sample):
     - 95/100 have a prior 10-Q/10-K with `created < filed_8k` in the DB
     - 5/100 are cold-start (no prior periodic at PIT — typically recent IPOs)
     - Median days-since-prior: 85 (exactly one fiscal quarter)
     - p90: 98 days; max: 112 days
     - Conclusion: `prior_periodic_projection` works for ~95% of historical rows.
       Live-mode cold-start rate is probably <1% (limited to fresh IPOs).
       Cold-start MUST be handled by `lag_window` fallback or fail-closed.

3. **Goal 2's recommended candidate `periodic_fiscal_math`** (from `candidate_algorithms.py` already in repo) relies on `matched_accession_periodic` and `period_of_report` being populated. In Goal 1's corpus those are populated only for ground-truth rows where the same-event periodic exists. AT PIT FOR A LIVE 8-K, those fields are typically EMPTY because the same-quarter 10-Q hasn't filed yet. Therefore Goal 2's candidate is NOT a live-mode resolver — it's a retrospective safety policy. Goal 3 must build on different signals.

4. **PIT-safe live signals available**:
   - filed_8k (filing timestamp)
   - fye_month (company's fiscal year end month, queryable from Neo4j Entity node)
   - Previous earnings 8-Ks for the same company (any 8-K with `formType='8-K'`, `items` CONTAINS '2.02', `created < this.filed_8k`)
   - Cypher queries with PIT bounds (`created <= filed_8k`)
   - The reporting-lag heuristic (typical Q announcement filed ~20-50 days after Q-end)

5. **Production resolver bugs** (don't replicate):
   - `_STALE_MATCH_DAYS=150` accepts the previous quarter's 10-K as authoritative for live 8-Ks (the FCX bug)
   - No fail-closed mechanism (production always emits SOME quarter)

6. **Existing helpers** (re-use, do NOT reinvent):
   - `fye_month.get_fye_month(ticker, session)`
   - `fiscal_math.period_to_fiscal(year, month, day, fye_month, form_type)`
   - Neo4j Cypher with PIT filtering

7. **Neo4j is read-only**. Each candidate may query Neo4j for additional context. The verifier passes a SANITIZED row context to each candidate; the candidate is responsible for using the cutoff for any Neo4j queries.

8. **Sanitized row context — fields candidates MAY see**:
   - `accession_8k` (the 8-K's own accession)
   - `ticker`
   - `filed_8k` (used as PIT cutoff for any Neo4j query)
   - `fye_month`

   **Forbidden fields (verifier strips before invocation; AST-checked)**:
   - `fy_xbrl`, `q_xbrl`, `fy_math`, `q_math`, `agreement`, `reason` (oracle leakage from Goal 1 corpus)
   - `period_of_report`, `matched_accession_periodic`, `periodic_created`, `form_type_periodic` (future-data leakage from same-event periodic)

---

## OUTPUTS REQUIRED (all under earnings-analysis/canary/quarter_resolver/)

### 1. live_candidates.py

Pure-Python module with **exactly these three required candidate functions** (verifier hard-checks for these names):

- `candidate_live_prior_periodic_projection`
- `candidate_live_lag_window`
- `candidate_live_hybrid_agreement`

You MAY add additional `candidate_live_<other_name>` functions, but the three above are mandatory. Each function signature:

```python
def candidate_live_<name>(row_context: dict, *, neo4j_session) -> dict:
    """
    Args:
        row_context: SANITIZED dict with ONLY:
            accession_8k, ticker, filed_8k, fye_month
        neo4j_session: a neo4j Session (read-only). The candidate is
            responsible for using PIT-safe Cypher (`WHERE created <= $filed_8k`).

    Returns:
        {
            "fy": int | None,
            "q": "Q1" | "Q2" | "Q3" | "Q4" | None,
            "source": str,           # describes the algorithm's reasoning,
                                     # e.g., "lag_window_match",
                                     # "prior_periodic_projection_q3_to_q4",
                                     # "hybrid_disagreement_fail_closed"
            "safety_action": "AUTO_OK" | "NEEDS_REVIEW"
                           | "FAIL_CLOSED" | "NO_RESOLUTION",
        }
    """
```

`safety_action` semantics (same as Goal 2):
- `AUTO_OK`: candidate is confident; downstream may write
- `NEEDS_REVIEW`: candidate produces (fy, q) BUT signals operator should review
- `FAIL_CLOSED`: candidate refuses to resolve; downstream MUST NOT write
- `NO_RESOLUTION`: structural lack of input

The candidate functions MUST NOT:
- Call `resolve_quarter_info` (production wrapper)
- Read forbidden row_context fields (verifier sanitizes; AST-checks)
- Query Neo4j without PIT bounds (`created <= filed_8k` or equivalent)
- Use string-parsing of EX-99.1 or any document text (D8 veto)

The candidate functions MAY:
- Use `period_to_fiscal` from fiscal_math
- Use `get_fye_month` (or read fye_month from row_context)
- Run any Neo4j Cypher query with explicit PIT filtering

**Required candidate behavior specs** (these three names are mandatory; the verifier hard-checks for them):

- **`prior_periodic_projection`** (RECOMMENDED PRIMARY — strong candidate):
  1. Query Neo4j for the most recent prior 10-Q or 10-K for the same ticker with `created <= $filed_8k` (PIT-bound)
  2. Read prior periodic's `periodOfReport` (this IS the fiscal quarter end for periodics — unlike 8-Ks; empirically reliable per Goal 1)
  3. Compute `period_to_fiscal(prior.year, prior.month, prior.day, fye_month, prior.formType)` → `(fy_p, q_p)`
  4. Advance 1 quarter with FY rollover at Q4→Q1 → expected `(fy, q)` for this 8-K
  5. Filter out prior periodics in `XBRL_DENY_PERIODIC_ACCESSIONS` (denylisted XBRL) — fall back further or FAIL_CLOSED
  6. FAIL_CLOSED if no prior found, gap > 200 days, or formType is 8-K/A (amendment)

  Walk-through for FCX `0000831259-26-000021`: prior is Q4 FY2025 10-K with period_of_report 2025-12-31. fiscal_math → (2025, Q4). Advance → **(2026, Q1)** ← correct.

- **`lag_window`** (simple cross-check candidate):
  1. Compute the most recent calendar/fiscal quarter-end before `filed_8k` given `fye_month`
  2. Compute days_since_q_end
  3. If `5 <= days_since_q_end <= 90` → AUTO_OK with that quarter (the typical earnings reporting window)
  4. Else FAIL_CLOSED (off-cycle filing — restatement, late report, or anomaly)

- **`hybrid_agreement`** (likely the recommended winner):
  Run both `prior_periodic_projection` and `lag_window`. AUTO_OK only if both agree on (fy, q). If they disagree → FAIL_CLOSED (signal of edge case worth human review). If only one is available (cold start, etc.) → fail closed conservatively, OR use the available one with `safety_action=NEEDS_REVIEW`.

**Holes to specifically test against** (per ChatGPT's enumeration + Claude's addition):
1. Cold start — no prior periodic for new IPO/spinoff
2. Skip/irregular reporting — company missed a quarter
3. FYE changes — detect via Item 5.03 8-Ks
4. Restatements / 8-K amendments — don't advance sequence
5. Duplicate earnings 8-Ks within same quarter — dedup by 7-day proximity
6. 52/53-week filers — lag-window tolerates ±10 days
7. Long gaps (>200 days) — fail closed
8. Q4 vs annual report combined filings — handle correctly
9. Prior periodic in `XBRL_DENY_PERIODIC_ACCESSIONS` — filter out

(Codex may propose additional PIT-safe candidates beyond the three mandatory ones, but the three named candidates above MUST exist with those exact names.)

### 2. live_mode_audit.csv

Schema (exactly these columns, in this order):

```
accession_8k, ticker, corpus_label, corpus_fy, corpus_q,
candidate_name, candidate_fy, candidate_q, candidate_source, candidate_safety_action,
would_fire, correct, candidate_quarter_verdict, candidate_safety_verdict
```

- `corpus_label`: "ground_truth" or "needs_review:<reason>"
- `corpus_fy`, `corpus_q`: filled for GT rows; empty for NR rows (no oracle)
- `would_fire`: "true" if `candidate_safety_action == AUTO_OK`, "false" otherwise
- `correct`: only meaningful for GT rows; "true" if would_fire AND candidate_fy == corpus_fy AND candidate_q == corpus_q; "false" if would_fire AND wrong; empty for NR rows or non-firing rows
- `candidate_quarter_verdict`: AGREE | BUG | NO_RESOLUTION | N_A (same enum as Goal 2)
- `candidate_safety_verdict`: OK | WRONG_AUTO_WROTE | CORRECT_FAIL_CLOSED | AUTO_ON_UNCERTAIN_ROW

Rows: 10,831 × N_candidates (one per (accession, candidate)). With the 3 mandatory candidates, total ≥32,493.

### 3. LIVE_MODE_REPORT.md

Concise (1500-3000 words) with the following SECTIONS (use these exact headers; the verifier checks for them):

**## Universe Contract**
Explicit statement that scored correctness is on 10,831 Goal 1 corpus rows; 10,995 = total earnings 8-K universe but only 10,831 are scored. State that NR rows have no oracle and AUTO_OK on NR is `AUTO_ON_UNCERTAIN_ROW`, never "correct".

**## Prior-Periodic Availability**
Compute on the FULL 10,831 corpus (NOT a sample) and report:
- Total rows
- has_prior_periodic count + rate
- cold_start count + rate (no prior periodic with `created < filed_8k`)
- days-since-most-recent-prior: min, p50, p90, p99, max
- Cold-start sample (5-10 example accessions with CIK + ticker for human eyeball)
- (This statistic is what determines whether `prior_periodic_projection` is the right primary path. The 100-row sample said 95/100 — but Goal 3 must compute the full number.)

**## Per-Candidate Headline Metrics**
For each of the ≥3 candidates separately (NOT just the recommended one):
- would_fire_rate (% of 10,831)
- correct_rate_on_gt (% of 9,909 GT rows that AUTO_OK with correct fy/q)
- wrong_auto_write_count (must be 0 for verifier to pass)
- fail_closed_rate
- auto_on_uncertain_row_rate (rows where candidate AUTO_OK on NR — should be MINIMIZED)

**## Per-Bucket Breakdown** (for each candidate):
- FYE month (Dec, Mar, Jun, Sep, other)
- 52-53-week filers (subset)
- Q4 (annual report) special-case (often filed differently than Q1-Q3)
- non-Dec-FYE filers
- FCX-shape NR rows (495)
- Other-NR classes (xbrl_math_disagree, proximity_rejected, denylist, no_xbrl)
- Cold-start subset (no prior periodic at PIT)

**Recommended candidate**: explicit line `Recommended candidate: <name>` matching one of your candidate function names. The recommended candidate MUST have:
- Zero WRONG_AUTO_WROTE on any row (verifier hard-fails otherwise)
- Highest would_fire_rate among submitted candidates
- Highest correct_rate_on_gt (or tied for highest)
- Reasoning for the choice

**Achievability statement** — MUST be a single line at top level (not inside an inline sentence) matching the regex `^[#\s>\*\-]*Achievability\s*[:=]\s*(YES|PARTIAL|NO)\b`:

```
Achievability: YES        (best candidate hits ≥99.9% would_fire AND ≥99.9% correct_rate_on_gt — proceed to Goal 4)
Achievability: PARTIAL    (best candidate hits high rate but with concentrated residual class — Goal 4 implements PLUS residual handling)
Achievability: NO         (best candidate hits <99% — escalate per existing fallback in quarter-identity-resolver.md)
```

The verifier hard-fails if this exact line isn't present. Substring presence of YES/PARTIAL/NO elsewhere in prose is NOT sufficient.

**Residual analysis**: for each NR class and each not-firing-AUTO_OK row, classify why and what would be needed to resolve.

**Next-step signaling for Goal 4**:
- exact resolver tier ladder
- write-guard policy: which `safety_action` values permit destructive writes
- list of edge cases requiring orchestrator-level handling

### 4. PIT-safety internal sanity check (optional but recommended)

A small `pit_safety_check.py` that asserts your candidates do not see any field that would be unavailable at PIT. Output the assertion log. Saves verifier-iteration cycles by catching leakage before submission.

---

## DONE WHEN (the verifier decides — not you)

```bash
# Canonical sign-off (default — full mode):
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_live_mode_resolver.py
```

The verifier checks:

```
L1.   Verifier file is git-clean (catches Codex tampering)
L2.   All 3 deliverables exist + non-empty (live_candidates.py,
      live_mode_audit.csv, LIVE_MODE_REPORT.md)
L3.   live_mode_audit.csv schema matches REQUIRED_COLUMNS_LIVE_AUDIT (ordered)
L4.   live_candidates.py imports + has the three required candidate functions
      (prior_periodic_projection, lag_window, hybrid_agreement)
L5.   AST PIT-safety check: candidates do NOT reference forbidden fields
      (period_of_report, matched_accession_periodic, periodic_created,
       form_type_periodic, fy_xbrl, q_xbrl, fy_math, q_math, agreement,
       reason) AND any Neo4j Cypher in candidates includes a PIT bound
      (created <= filed_8k or equivalent)
L6.   Universe coverage: live_mode_audit.csv covers all 10,831 corpus rows
      (9,909 GT + 922 NR), no overlap, no missing
L7.   Independent re-derivation: verifier calls each candidate function
      against PIT-masked context for every corpus row; CSV claims
      (candidate_fy/q/source/safety_action/would_fire/correct/verdicts)
      must match what the function returns
L8.   ZERO WRONG_AUTO_WROTE across all candidates (THE ONLY safety threshold)
L9.   would_fire/correct/fail_closed rates REPORTED per candidate (no hard
      threshold) — verifier prints the rates as INFO; downstream gate is
      human review of LIVE_MODE_REPORT.md
L10.  Recommended candidate (named in LIVE_MODE_REPORT.md): exists in
      live_candidates.py + has rows in live_mode_audit.csv + zero
      WRONG_AUTO_WROTE
L11.  LIVE_MODE_REPORT.md non-empty + ≥1000 bytes + references "would_fire",
      "correct", "WRONG_AUTO_WROTE", "Recommended candidate", and the
      explicit YES/PARTIAL/NO achievability statement
```

If ANY L1-L8, L10, or L11 fails, fix and re-run. **L9 is informational ONLY** — verifier reports rates and exits 0 regardless of magnitude (the question of "is the rate good enough?" is a human/strategic decision in the next step, not a verifier-mechanical decision).

---

## NON-GOALS (do not do these)

- Do NOT modify any verifier file (L1 will catch it).
- Do NOT modify any production code (scripts/earnings/*.py, .claude/skills/earnings-orchestrator/scripts/*.py).
- Do NOT modify the Goal 1 corpus, Goal 2 deliverables, or any prior-Goal artifact.
- Do NOT use 8-K periodOfReport as a quarter-end signal (probe-disproven 2026-05-05).
- Do NOT use sec-api.io or any paid 3rd-party.
- Do NOT attempt EX-99.1 text mining.
- Do NOT design the production fix yet — that is Goal 4. Goal 3 is design + benchmark, not implementation.
- Do NOT hardcode the recommended candidate's would_fire ≥ 99.9% in the verifier or anywhere — that's the empirical question Goal 3 answers.

---

## WORKFLOW HINTS

- Read the running plan AND the verifier script in full FIRST.
- Start by implementing 2-3 candidates and running them on a small sample (e.g., 100 rows from each FYE bucket). Iterate the algorithms BEFORE scaling to all 10,831.
- Test each candidate explicitly on FCX `0000831259-26-000021`:
  - lag_window: filed 2026-04-23, FYE=12 → most-recent-quarter-end is 2026-03-31, 23 days before filing → within window → SHOULD return Q1_FY2026
  - sequence_projection: previous earnings 8-K for FCX likely announced Q4_FY2025 in late Jan/early Feb 2026 → next quarter is Q1_FY2026 → SHOULD return Q1_FY2026
  - hybrid_agreement: both agree on Q1_FY2026 → AUTO_OK with Q1_FY2026
- Run the verifier after each major change. Iterate until exit 0.
- For tie-breaking among candidates: prefer simpler (fewer LOC, fewer Neo4j queries), explicit (deterministic decision tree), and demonstrably PIT-safe.

---

## OUT-OF-SCOPE / FUTURE

- Production fix implementation (Goal 4)
- Resolver source code in scripts/earnings/quarter_identity.py (Goal 4)
- Orchestrator write-guard implementation (Goal 4)
- Production deployment (Goal 4 final step)

---

## Comparison to Goal 2

| Aspect | Goal 2 | Goal 3 |
|---|---|---|
| Question | What's the safe candidate for the FCX harm class? | What's the best PIT-safe live-mode resolver? |
| Mode | Retrospective (full corpus, all data visible) | PIT-simulated (only data ≤ filed_8k visible) |
| Recommended candidate uses | matched periodic + fiscal_math | live signals (filing date, prior 8-Ks, FYE) |
| Hard-locked threshold | 0 WRONG_AUTO_WROTE on FCX-shape | 0 WRONG_AUTO_WROTE on ALL rows |
| Soft-reported metrics | GT-AGREE rate, FCX safety | would_fire / correct / fail_closed by bucket |
| Achievable target known? | yes (FCX bug class is fail-closeable) | EMPIRICAL — Goal 3 answers it |

---

## Reminder on philosophy

Goal 3 is **discovery**, not declaration. It is allowed to come back with "the best PIT-safe candidate achieves only 95% would_fire — here are the residuals and what they need." That answer is acceptable AND verifier-passable. The decision about whether 95% is good enough for production happens AFTER Goal 3, with the residual classification informing the conversation.

The verifier hard-fails ONLY on: tampering, future-data leakage, wrong-auto-writes, structural artifact issues. Everything else is reported, not gated.
