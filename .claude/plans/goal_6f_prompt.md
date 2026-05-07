# Goal 6f - Research-only discovery beyond Candidate D

**Status**: draft research goal.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_goal_6f_research.py`.
**Production code**: must remain unchanged.

Goal 6f exists because Candidate D is safe enough to ship, but it still
fail-closes about 31 latest-per-ticker cases and leaves a few wrong-fires.
The simple Rule G2 idea, "trust XBRL FY on FY disagreement and advance", was
audited on 408 rows across 34 edge tickers and rejected: it saves many
fail-closures but creates new wrong AUTO_OK rows.

This goal is a bounded research loop to find a **truly structural,
generalizable** improvement over Candidate D without violating the locked
rules. It must start with failure analysis, not candidate tinkering.

Honest expectation: a negative result is likely and valuable. The 34-edge
audit showed that issuer iXBRL and public EX-99.1 naming can disagree within
the same issuer. If no structural signal bridges that channel gap without
creating new wrong AUTO_OK rows, the correct output is `KEEP_D`.

---

## The /goal command

```text
/goal Implement Goal 6f research-only candidate discovery exactly as specified in .claude/plans/goal_6f_prompt.md, and keep iterating until earnings-analysis/canary/quarter_resolver/verify_goal_6f_research.py exits 0.
```

## Follow-up message

```text
Read .claude/plans/goal_6f_prompt.md in full first. This is RESEARCH-ONLY.
Do not modify production code, tests, guidance code, fiscal_math, or any
orchestrator/guidance/learner/predictor file. You may only create or update
research artifacts under earnings-analysis/canary/quarter_resolver/:
  - goal6f_candidates.py
  - build_goal6f_outputs.py
  - goal6f_candidate_matrix.csv
  - goal6f_candidate_<ID>_per_row.csv
  - GOAL6F_REPORT.md

Use the committed evidence only as oracle labels for scoring. Candidate
features must be PIT-safe structural filing metadata only. No ticker tables,
no issuer lists, no sector/industry classes, no EX-99/press-release text
parsing, no external HTTP/API calls, no LLM/ML, and no arbitrary time
thresholds. The verifier enforces these constraints.
```

---

## Required phase order

Do these phases in order.

### Phase 1 - Failure model first

Before implementing any new candidate, write
`earnings-analysis/canary/quarter_resolver/GOAL6F_FAILURE_MODEL.md`.

It must diagnose:

1. why Candidate D fail-closes the 31 latest-per-ticker edge cases
2. why Candidate D still wrong-fires PHR/PINC/PRU and any similar rows
3. why G2 creates new wrong AUTO_OK rows
4. which failure classes need which missing signal to become safe
5. whether each missing signal exists inside the allowed feature set
6. which candidate families are justified by that diagnosis
7. which classes are irreducible under the locked rules, with concrete
   accession examples

If the model concludes that no allowed structural signal can separate a class,
say so directly. Do not invent a heuristic to fill that gap.

### Phase 2 - Candidate proposal

Only after the failure model exists, propose candidate families. Each family
must map to a named failure class from `GOAL6F_FAILURE_MODEL.md`.

### Phase 3 - Candidate scoring

Implement and score only candidates that obey the locked rules. If no
candidate is shippable, produce a verified `KEEP_D` result.

---

## Inputs already available

Use these files as immutable evidence and prior work:

- `earnings-analysis/canary/quarter_resolver/goal6a_d_measurement.csv`
  - Candidate D behavior on 10,674 scoreable rows.
  - Includes `oracle_fy`, `oracle_q`, `warm_start`, `latest_per_ticker`.
- `earnings-analysis/canary/quarter_resolver/audit_evidence/sec_34_edge_ticker_audit_2026-05-07/advance_xbrl_simulation.csv`
  - 408-row edge audit, including the rejected G2 variants.
- `earnings-analysis/canary/quarter_resolver/audit_evidence/sec_34_edge_ticker_audit_2026-05-07/master_truth.csv`
  - SEC truth for the 34 edge tickers.
- `earnings-analysis/canary/quarter_resolver/audit_evidence/sec_34_edge_ticker_audit_2026-05-07/validation_report.md`
  - Summary: G2 is promising but not shippable.
- `earnings-analysis/canary/quarter_resolver/audit_evidence/sec_34_edge_ticker_audit_2026-05-07/adversarial_review.json`
  - Second-pass review results. Treat failed adversarial rows as caveated.

Truth priority for scoring:

1. For rows in the 34-edge audit with Tier A/B SEC truth, use
   `sec_truth_fy/sec_truth_q` from `advance_xbrl_simulation.csv`.
2. For all other rows, use `oracle_fy/oracle_q` from
   `goal6a_d_measurement.csv`.
3. Tier C and unclear edge rows may be reported separately, but they cannot be
   used to justify a shippable candidate.

---

## Baselines you must include

Your matrix must include:

1. `D_BASELINE`
   - Exact Candidate D behavior from `goal6a_d_measurement.csv`.
   - The verifier hard-fails unless `(outcome, fy, q, source)` matches
     `goal6a_d_measurement.csv` exactly for every row.
2. `G2_CALENDAR_ONLY`
   - Existing rejected G2-calendar-only behavior from the edge audit, extended
     or marked unavailable outside the 34-edge set.
3. `G2_ALL_FY_DISAGREE`
   - Existing rejected G2-all behavior from the edge audit, extended or marked
     unavailable outside the 34-edge set.

You must also try at least **four new lock-respecting structural candidates**,
covering these directions unless you can prove a direction is impossible from
the available data:

1. **Multi-prior XBRL consistency**
   - Inspect the last several PIT-visible 10-Q/10-K filings.
   - Candidate may use only stable XBRL-vs-math offset patterns from those
     prior periodics.
   - Goal: test whether a stable issuer filing convention can safely recover
     D fail-closures.

2. **Period-end-day / calendar-shape signature**
   - Compute structural signatures from prior periodic `periodOfReport` dates:
     exact month-end, near-month-end, 52/53-week Saturday pattern, Q4 boundary
     behavior.
   - No industry/ticker mapping. No new thresholds beyond existing 24h/150d.
   - Goal: test whether calendar mechanics explain safe vs unsafe XBRL use.

3. **Current 8-K own XBRL facts, if present**
   - Some 8-K Reports may have their own XBRL DEI FY/Q facts.
   - Candidate may use only the 8-K Report's own PIT-visible XBRL facts, with
     the same denylist/proximity caution where applicable.
   - Goal: test whether direct current-filing XBRL avoids prior-projection
     ambiguity.

4. **Advance-result agreement gate**
   - Compute both `advance(prior_xbrl_fy/q)` and
     `advance(prior_math_fy/q)`.
   - AUTO_OK only when the advanced labels agree; otherwise fail-closed.
   - Goal: test whether D's FY-disagreement guard is too conservative before
     advance, while still refusing disagreement after advance.

Optional additional candidates are allowed, but they must obey the same rules.

---

## Hard locked rules

Candidates may NOT use:

- ticker allowlists, deny lists, or per-issuer maps
- CIK/company-name keyed dispatch
- sector, industry, SIC, GICS, NAICS, or any issuer-class proxy
- EX-99.1, 8-K body text, press-release headline text, or SEC document text as
  a runtime feature
- external HTTP/API calls, web search, sec-api, edgar libraries, OpenAI/Claude
  calls, embeddings, ML models, or learned classifiers
- CIK-keyed dispatch, even if CIK is already in the database
- non-PIT wall-clock features such as `datetime.now()` or `time.time()`
- future data after the 8-K filing timestamp
- the 8-K `periodOfReport` as a proxy for the fiscal quarter end
- arbitrary new thresholds like 3 days, 7 days, 30 days, 45 days, etc.

Allowed structural signals:

- PIT-visible prior 10-Q/10-K rows for the same company
- prior periodic `formType`, `created`, `periodOfReport`, XBRL FY/Q, math FY/Q
- company FYE month already available in Neo4j
- previous earnings 8-K timing available before the current 8-K
- filing sequence/cadence features that are computed from PIT-visible Reports
- existing thresholds only: 24h direct-recent and 150d long-gap
- deterministic transformations of the above

If you explore a disallowed idea for curiosity, mark it as
`DISALLOWED_RESEARCH_ONLY` and do not call it shippable.

---

## What "better than D" means

A candidate is **shippable** only if all of these are true:

1. Full 10,674-row scoreable set:
   - no new wrong AUTO_OK rows relative to D
   - total wrong AUTO_OK count is <= D's count
2. 34-edge Tier A/B set:
   - no new wrong AUTO_OK rows relative to D
   - recovers at least one D fail-closed row correctly
3. Latest-per-ticker set:
   - no new wrong AUTO_OK rows relative to D
   - wrong count is <= D's latest-per-ticker wrong count
4. Candidate uses only allowed structural features.
5. Candidate is explained in <= 10 lines of pseudocode.

If no candidate satisfies these, that is a valid outcome. The report should say
that Candidate D remains the best lock-respecting production algorithm.

---

## Required artifacts

Create these files under `earnings-analysis/canary/quarter_resolver/`.

### 0. `GOAL6F_FAILURE_MODEL.md`

Required before candidate building. Must include:

- `D_FAIL_CLOSED_TAXONOMY`
- `D_WRONG_FIRE_TAXONOMY`
- `G2_NEW_WRONG_TAXONOMY`
- `MISSING_SIGNAL_ANALYSIS`
- `ALLOWED_SIGNAL_INVENTORY`
- `CANDIDATE_FAMILIES_JUSTIFIED`
- `IRREDUCIBLE_CLASSES`
- `TRACTABLE_CLASSES`
- `EVIDENCE_ROWS`

### 1. `goal6f_candidates.py`

Research-only candidate implementations. Must include the exact marker:

```python
"""RESEARCH-ONLY Goal 6f candidates. Not imported by production."""
```

Candidate functions should have this shape:

```python
def candidate_<id>(ticker: str, accession_8k: str, *, neo4j_session) -> dict:
    return {
        "outcome": "AUTO_OK" or "FAIL_CLOSED",
        "fy": "2026" or "",
        "q": "Q1" or "",
        "source": "goal6f_<id>_<reason>",
    }
```

Do not import this file from production.

### 2. `build_goal6f_outputs.py`

Reproducible builder that scores all candidates and writes the CSV/report
artifacts. It may query Neo4j read-only. It must not fetch SEC documents or
read raw press-release text as candidate features.

### 3. `goal6f_candidate_matrix.csv`

Required columns:

```text
candidate_id,description,uses_banned_features,shippable,
full_correct,full_wrong,full_fail_closed,full_new_wrong_vs_d,
warm_correct,warm_wrong,warm_fail_closed,warm_new_wrong_vs_d,
latest_correct,latest_wrong,latest_fail_closed,latest_new_wrong_vs_d,
edge_ab_correct,edge_ab_wrong,edge_ab_fail_closed,edge_ab_new_wrong_vs_d,
edge_ab_recovered_correct_from_d_fc
```

### 4. `goal6f_candidate_<ID>_per_row.csv`

One file per candidate. Required columns:

```text
candidate_id,ticker,accession_8k,oracle_source,oracle_fy,oracle_q,
warm_start,latest_per_ticker,d_outcome,d_fy,d_q,d_source,
outcome,fy,q,source,correct,changed_vs_d,feature_notes
```

Each candidate per-row file must contain exactly the same 10,674 accession set
as `goal6a_d_measurement.csv`.

Column semantics:

- `correct` must be one of `true`, `false`, `fail_closed`
- `changed_vs_d` must be `true` iff `(outcome, fy, q)` differs from
  Candidate D on that same accession
- for 34-edge Tier A/B accessions, `oracle_fy/oracle_q` must be the SEC truth
  from the edge audit, not the older oracle value

### 5. `GOAL6F_REPORT.md`

Must include:

- a plain-English summary
- the candidate matrix table
- pseudocode for every candidate
- a section titled `STRUCTURAL_DIRECTIONS_TESTED` covering the four required
  directions above and their results
- for every new candidate, an explicit `TARGET_FAILURE_CLASS` line naming the
  failure-model class it attempts to fix
- why each rejected candidate failed
- explicit discussion of G2's failure mode
- a section titled `BANNED_FEATURES_AUDIT`
- exact decision flags:

```text
DECISION_FLAG_GOAL6F_FOUND_SHIPPABLE = yes|no
DECISION_FLAG_GOAL6F_BEST_CANDIDATE = <candidate_id or NONE>
DECISION_FLAG_GOAL6F_RECOMMENDATION = SHIP_CANDIDATE|KEEP_D|NEEDS_MORE_GT
```

---

## Completion rule

The goal is complete when:

```bash
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal_6f_research.py
```

exits 0.

If no safe candidate is found, do not force one. A verified `KEEP_D` result is
a successful research outcome.
