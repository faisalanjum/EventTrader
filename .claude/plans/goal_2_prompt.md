# Goal 2 — Shadow Validator + Candidate Algorithm Proposals

**Status**: ready to fire via `/goal` after verifier is git-committed.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py` (hand-authored — Codex must NOT modify; checked via git diff).
**Pass criterion**: verifier exits 0.
**Honest claim**: Goal 2 measures the production resolver against the Goal 1 corpus AND evaluates ≥2 candidate replacements. The recommended candidate must be safe on FCX-shape rows; quarter correctness alone is not enough.

---

## Pre-flight (you do this BEFORE firing /goal)

```bash
cd /home/faisal/EventMarketDB
# Verifier must be committed so the git-diff freeze check has a baseline
git add earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py \
        .claude/plans/goal_2_prompt.md
git commit -m "wip(quarter-resolver): goal 2 verifier + prompt"
git diff --quiet -- earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py && echo OK
```

If the commit step is skipped, the verifier will fail at S1 with exit code 2.

---

## The /goal command (copy this verbatim into Codex)

```
/goal Run the shadow validator and propose candidate resolvers exactly as
specified in .claude/plans/goal_2_prompt.md, and keep iterating until
earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py exits 0.
```

## The follow-up message (after /goal acknowledges)

```
Read .claude/plans/goal_2_prompt.md in full first. The Goal 1 corpus at
earnings-analysis/canary/quarter_resolver/{ground_truth.csv, needs_review.csv}
is the benchmark — do not modify it. The Goal 1 verifier
(verify_ground_truth_corpus.py) and the Goal 2 verifier
(verify_shadow_validator.py) are immutable. Do not modify production code
in scripts/earnings/*.py. Stay within earnings-analysis/canary/quarter_resolver/
and /tmp/ for any scratch artifacts.
```

---

## Goal 2 mission

Two distinct deliverables, scored together:

**A. Shadow audit of the PRODUCTION resolver.**
Run `scripts.earnings.quarter_identity.resolve_quarter_info(ticker, accession)` on every one of the 10,831 corpus rows (9,909 GT + 922 NR). Compare its output to the corpus and produce a row-by-row scoreboard.

**B. Propose ≥2 candidate replacement resolvers as EXECUTABLE Python.**
Each candidate is a function in `candidate_algorithms.py` that consumes a SANITIZED row context (see CRITICAL CONSTRAINT below) and returns a structured dict with `(fy, q, source, safety_action)`. The verifier independently re-runs each candidate function on every row — using ONLY the sanitized subset — and compares to your claimed audit output.

> **CRITICAL CONSTRAINT — sanitized row context (anti-cheat)**
> When the verifier re-runs each candidate, it strips the corpus's "oracle" fields BEFORE passing the row in:
> - stripped (NEVER passed to candidate): `fy_xbrl`, `q_xbrl`, `fy_math`, `q_math`, `agreement`, `reason`
> - kept (the only keys the candidate sees): `accession_8k`, `ticker`, `filed_8k`, `period_of_report`, `fye_month`,
>   `matched_accession_periodic`, `periodic_created`, `form_type_periodic`
>
> Your candidate functions MUST work on ONLY the kept fields. They MUST NOT read `fy_xbrl/q_xbrl/fy_math/q_math/agreement/reason` from row_context — even if you populate those fields in the FULL corpus row when building `candidate_audit.csv`, the verifier will not pass them through, and the function's outputs WILL diverge from the CSV.
>
> When you build `candidate_audit.csv` you MAY pass the full corpus row to your candidate to compute claimed outputs, BUT your candidate's logic must produce identical output regardless of whether oracle fields are present. Easiest path: write the candidate to ignore oracle fields entirely. Self-test: assert `candidate(full_row) == candidate(sanitized_row)` for every accession before writing the CSV.
>
> If your algorithm needs XBRL fiscal identity, call `parse_xbrl_fiscal_identity` at runtime against the matched periodic. If your algorithm needs fiscal_math, call `period_to_fiscal(...)` directly. If your algorithm needs the NR reason, you cannot have it — by design, this is what the production runtime would face.

**Recommended candidate**: must explicitly fail closed on FCX-shape rows (NR.reason == "not_same_event_periodic"). Auto-resolving these rows is the bug we are eliminating.

---

## CONTEXT (do NOT spend budget rediscovering — confirmed facts)

1. **Goal 1 corpus** is at `earnings-analysis/canary/quarter_resolver/{ground_truth.csv, needs_review.csv}`. Total 10,831 rows = 9,909 GT + 922 NR. NR breakdown:
   - `not_same_event_periodic`: 495  ← FCX-shape live-mode rows
   - `xbrl_math_disagree`: 391       ← AAP/ACI extreme calendars + SEC tag errors
   - `proximity_rejected`: 26
   - `denylist`: 6
   - `no_xbrl`: 4
   - `no_fye`: 0
2. **Production resolver**: `scripts/earnings/quarter_identity.py:resolve_quarter_info(ticker, accession_8k, *, session=None)`. Returns dict including `quarter_label`, `period_of_report`, `quarter_identity_source`, `gaps`, `accession_periodic`, etc. The known bug: `_STALE_MATCH_DAYS=150` (line 36) silently accepts the previous quarter's 10-K as authoritative for live-mode 8-Ks (FCX Q1_FY2026 case). It does NOT have an explicit fail-closed mechanism — when it cannot resolve, it returns gaps; some downstream callers proceed anyway.
3. **The FCX harm fingerprint** (deterministic, no oracle needed):
   - Corpus row is in NR with `reason == "not_same_event_periodic"` (no same-event periodic exists in graph at PIT)
   - AND production_source ∈ {"matched_periodic_xbrl", "matched_periodic_fiscal_math"}
   - This means the resolver trusted the previous quarter's periodic. CLASSIFY: `WRONG_AUTO_WROTE`.
4. **Goal 1.5 audit** confirmed corpus is reliable: 199/200 ok, 0 wrong, 1 unclear (RH non-reliance restatement). Evidence in `earnings-analysis/canary/quarter_resolver/audit_evidence/`.
5. **Existing helpers** (re-use, do NOT reinvent):
   - `scripts.earnings.quarter_identity.resolve_quarter_info`
   - `fiscal_math.period_to_fiscal`
   - `get_quarterly_filings.parse_xbrl_fiscal_identity`
   - `get_quarterly_filings.should_use_xbrl_fiscal`
   - `get_quarterly_filings.XBRL_DENY_PERIODIC_ACCESSIONS`
   - `fye_month.get_fye_month`
6. **Neo4j is read-only**. Each candidate may need to query Neo4j for context not already in the row context; if so, it should accept the SANITIZED row context dict the verifier passes (and lazily query Neo4j only as needed). The verifier passes ONLY the sanitized subset (`accession_8k`, `ticker`, `filed_8k`, `period_of_report`, `fye_month`, `matched_accession_periodic`, `periodic_created`, `form_type_periodic`) — your candidate must work with just those keys. Oracle fields (`fy_xbrl`, `q_xbrl`, `fy_math`, `q_math`, `agreement`, `reason`) are NEVER passed to the candidate.

---

## OUTPUTS REQUIRED (all under earnings-analysis/canary/quarter_resolver/)

### 1. shadow_audit.csv

Schema (exactly these columns, in this order):

```
accession_8k, ticker, corpus_label,
corpus_fy, corpus_q,
production_fy, production_q, production_source,
production_quarter_verdict, production_safety_verdict
```

- `corpus_label`: "ground_truth" for GT rows; "needs_review:<reason>" for NR rows
- `corpus_fy, corpus_q`: filled for GT rows; empty for NR rows
- `production_fy, production_q, production_source`: what `resolve_quarter_info` returned (from `quarter_label` parse + `quarter_identity_source`); empty if no resolution
- `production_quarter_verdict`:
  - GT row: AGREE | BUG | NO_RESOLUTION
    - AGREE: production_fy == corpus_fy AND production_q == corpus_q
    - BUG: production resolved confidently but doesn't match corpus
    - NO_RESOLUTION: production returned no quarter_label (production_fy AND production_q both blank)
  - NR row: always N_A (no oracle)
- `production_safety_verdict`:
  - GT row: OK | WRONG_AUTO_WROTE
    - OK: production_quarter_verdict == AGREE
    - WRONG_AUTO_WROTE: production_quarter_verdict == BUG (resolved confidently to wrong quarter — would have written into wrong directory)
    - For NO_RESOLUTION on GT: also OK (resolver correctly didn't auto-write, just lacks oracle confidence)
  - NR row: CORRECT_FAIL_CLOSED | AUTO_ON_UNCERTAIN_ROW | WRONG_AUTO_WROTE
    - **NOTE**: NR rows always have production_quarter_verdict == N_A (no oracle).
      The fail-closed detector therefore keys on the production CSV's
      `production_fy` AND `production_q` BOTH being blank, NOT on
      `quarter_verdict == NO_RESOLUTION`.
    - CORRECT_FAIL_CLOSED: production_fy is blank AND production_q is blank
      (resolver returned no quarter_label — equivalent to refusing to write)
    - WRONG_AUTO_WROTE: corpus_label == "needs_review:not_same_event_periodic" AND production_source ∈ {matched_periodic_xbrl, matched_periodic_fiscal_math} (FCX harm fingerprint)
    - AUTO_ON_UNCERTAIN_ROW: production confidently emitted (fy, q) on any other NR row OR on not_same_event_periodic without matched_periodic_* source

Rows: 10,831 (one per corpus accession). No duplicates.

### 2. candidate_algorithms.py

Pure-Python module with ≥2 functions named `candidate_<name>` where `<name>` is a stable identifier (e.g., `quarter_equality`, `confidence_cascade`, `xbrl_only`). Each function signature:

```python
def candidate_<name>(row_context: dict) -> dict:
    """
    Args:
        row_context: a SANITIZED row dict (oracle fields stripped by the
                     verifier before invocation). Available keys:
                       accession_8k, ticker, filed_8k,
                       period_of_report, fye_month,
                       matched_accession_periodic, periodic_created,
                       form_type_periodic
                     NOT available (intentionally stripped to prevent
                     candidates from echoing the corpus answer):
                       fy_xbrl, q_xbrl, fy_math, q_math, agreement, reason

    Returns:
        {
            "fy": int | None,        # may be int or numeric str; verifier
                                     # compares as str (str(int))
            "q": "Q1" | "Q2" | "Q3" | "Q4" | None,
            "source": str,           # describes the algorithm's reasoning,
                                     # e.g., "two_source_agreement",
                                     # "fiscal_math_only", "fail_closed",
                                     # "matched_periodic_xbrl",
                                     # "matched_periodic_fiscal_math"
            "safety_action": "AUTO_OK" | "NEEDS_REVIEW"
                           | "FAIL_CLOSED" | "NO_RESOLUTION",
        }
    """
```

> **NOTE on building `candidate_audit.csv`**: when you compute the CSV in your /goal run, you MAY pass the FULL corpus row to your candidate (so verdict re-derivation is consistent), but your candidate's logic must NOT BRANCH on the oracle fields. The verifier will pass only the sanitized subset and require the same output. Easiest: write your candidate to ignore oracle fields entirely and just take its inputs from the kept fields. Test by calling your candidate with both the full corpus row AND `{k: v for k, v in row.items() if k in {accession_8k, ticker, filed_8k, period_of_report, fye_month, matched_accession_periodic, periodic_created, form_type_periodic}}` — outputs MUST be identical.

`safety_action` semantics:
- `AUTO_OK`: candidate is confident; downstream may write
- `NEEDS_REVIEW`: candidate produces (fy, q) BUT signals operator should review before write
- `FAIL_CLOSED`: candidate refuses to resolve; downstream MUST NOT write
- `NO_RESOLUTION`: candidate cannot determine — like FAIL_CLOSED but indicates structural lack of input rather than active refusal

The candidate functions MUST NOT call `resolve_quarter_info`. They are independent algorithm proposals, not wrappers. They may call `period_to_fiscal`, `parse_xbrl_fiscal_identity`, `should_use_xbrl_fiscal`, `get_fye_month`, and read `XBRL_DENY_PERIODIC_ACCESSIONS`.

The candidate functions MUST work on the SANITIZED row context (only the kept fields listed in the CRITICAL CONSTRAINT above) — if you need additional Neo4j context, fetch it inside the candidate using the `accession_8k` and write it into the candidate's docstring. Do NOT rely on `fy_xbrl/q_xbrl/fy_math/q_math/agreement/reason` being present in `row_context` — the verifier strips them.

**Suggested directions** (you may choose ANY 2+; do not feel constrained to these):
- Quarter-equality check: replace `_STALE_MATCH_DAYS` with a check that `period_to_fiscal(matched.period_of_report)` produces the same (fy, q) as `_map_event_to_quarter_end(filed_8k, fye_month)` would
- Confidence cascade: tier 2 (matched periodic XBRL) → tier 4 (fiscal_math) → fail_closed if disagreement
- Strict same-event: only resolve if `matched.created > filed_8k`, else fail_closed
- Hybrid with explicit safety_action policy per source tier

### 3. candidate_audit.csv

Schema:

```
accession_8k, ticker, corpus_label,
candidate_name, candidate_fy, candidate_q, candidate_source, candidate_safety_action,
candidate_quarter_verdict, candidate_safety_verdict
```

- One row per (accession, candidate) pair. Total rows = 10,831 × N_candidates.
- `candidate_quarter_verdict` and `candidate_safety_verdict` use the same enums as production_quarter_verdict / production_safety_verdict.
- The verifier independently calls each candidate function on the row context and asserts the CSV's claimed `candidate_fy/q/source/safety_action` values match what the function actually returns.

### 4. GOAL2_REPORT.md

Concise (700-1500 words) with:
- Production resolver baseline: count by verdict (AGREE / BUG / NO_RESOLUTION on GT; CORRECT_FAIL_CLOSED / AUTO_ON_UNCERTAIN_ROW / WRONG_AUTO_WROTE on NR). Highlight WRONG_AUTO_WROTE on the not_same_event_periodic subset (the FCX bug count).
- Per-candidate accuracy table: GT-AGREE rate, NR-CORRECT_FAIL_CLOSED rate, FCX-shape WRONG_AUTO_WROTE count (must be 0 for the recommended winner), AUTO_ON_UNCERTAIN_ROW rate on NR.
- **Recommended candidate**: explicit line in the format `Recommended candidate: <name>` matching one of your candidate function names. The recommended candidate MUST have:
  - Highest GT-AGREE rate (or tied for highest)
  - Name exists as a function in `candidate_algorithms.py` (S10b verifier check)
  - Has rows in `candidate_audit.csv` (S10b verifier check)
  - Zero WRONG_AUTO_WROTE on the not_same_event_periodic subset (S10 hard-fail applies to ALL candidates, not just the winner)
  - Zero AUTO_OK / AUTO_ON_UNCERTAIN_ROW on the not_same_event_periodic subset (S10b — winner-only stricter rule; the winner cannot auto-resolve FCX-shape rows even with a "safe" source)
  - Reasoning for the choice
- Residuals: rows neither production nor any candidate handles correctly; what would be needed to handle them (Goal 3 notes).

---

## DONE WHEN (the verifier decides — not you)

The verifier has TWO modes; Goal 2 is done only when BOTH pass:

```bash
# 1. Iteration mode (fast — used during /goal Ralph loops):
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py

# 2. Final sign-off mode (bulletproof — required to declare Goal 2 done):
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py --full
```

Both must exit 0.

- The default mode (stratified S6b) is FAST: iterates quickly during Codex's /goal loop. It exhaustively verifies the 495 FCX-shape rows but only stride-samples the rest. It's evadable for non-FCX rows by an adversarial agent reading this verifier.
- The `--full` mode runs `resolve_quarter_info()` against ALL 10,831 corpus rows. Slow but bulletproof. **The user (not Codex) will run `--full` once before signing off.**

The verifier checks (S1-S11 + S6b + S10b):

```
S1.   Verifier file is git-clean (catches tampering)
S2.   All 4 deliverables exist + non-empty
S3.   shadow_audit.csv schema EXACTLY matches REQUIRED_COLUMNS_SHADOW
      (ORDERED — column order enforced)
S4.   candidate_audit.csv schema EXACTLY matches REQUIRED_COLUMNS_CANDIDATE
      (ORDERED — column order enforced)
S5.   No duplicate accession_8k in shadow_audit.csv
S6.   shadow_audit covers all 10,831 corpus rows (no overlap, no missing)
S6b.  Independent production-resolver re-derivation (two modes):
      - default (stratified, fast — for /goal iteration):
        100% of FCX-shape NR (495 rows) + GT stride + other-NR stride
      - --full (bulletproof, REQUIRED for final sign-off):
        ALL 10,831 corpus rows
      Both modes call resolve_quarter_info() and assert shadow_audit.csv
      production_fy/q/source match. Catches faked production output.
      Codex is expected to pass the default mode; the user will run
      --full as the final acceptance gate.
S7.   Per-row invariants on shadow_audit: enum membership AND independent
      re-derivation of production_quarter_verdict & production_safety_verdict.
      The verifier computes what the verdicts SHOULD be from rules; CSV
      claims must match. Catches verdict-mislabeling.
S8.   candidate_algorithms.py importable, ≥2 candidate_<name> functions found
S9.   Each candidate has output for ALL 10,831 corpus rows (not partial).
      The verifier calls each candidate function on the SANITIZED row
      context (oracle fields stripped — see CRITICAL CONSTRAINT above)
      and asserts CSV's candidate_fy/q/source/safety_action match.
      The verifier ALSO independently re-derives candidate_quarter_verdict
      and candidate_safety_verdict; CSV claims must match.
S10.  FCX hard-fail (STRICT, ALL CANDIDATES): NO candidate (winner OR
      loser) may have ANY WRONG_AUTO_WROTE on the not_same_event_periodic
      subset (495 rows). If even one candidate emits the FCX harm
      fingerprint on these rows, hard fail. Stricter than the
      recommended-only rule below.
S10b. Recommended candidate (named in GOAL2_REPORT.md):
      (a) name MUST exist as a function in candidate_algorithms.py
      (b) name MUST have rows in candidate_audit.csv (>=1)
      (c) ZERO AUTO_OK / AUTO_ON_UNCERTAIN_ROW on the
          not_same_event_periodic subset (winner must explicitly fail
          closed on FCX-shape rows, not merely avoid the harmful
          auto-write).
S11.  GOAL2_REPORT.md non-empty, ≥500 bytes, references production / candidate / FCX / WRONG_AUTO_WROTE
```

If ANY check fails, fix the issue and re-run. Do not declare done until verifier exits 0.

---

## NON-GOALS (do not do these)

- Do NOT modify the verifier file (S1 will catch it).
- Do NOT modify any production code (scripts/earnings/*.py, .claude/skills/earnings-orchestrator/scripts/*.py).
- Do NOT modify the Goal 1 corpus (ground_truth.csv, needs_review.csv).
- Do NOT modify the Goal 1 verifier (verify_ground_truth_corpus.py).
- Do NOT use sec-api.io or any paid 3rd-party.
- Do NOT attempt EX-99.1 text mining.
- Do NOT design the production fix yet — that is Goal 3.
- Stay within earnings-analysis/canary/quarter_resolver/ and /tmp/.

---

## WORKFLOW HINTS

- Read the running plan AND the verifier script in full FIRST.
- Implement and run the production-resolver shadow audit first; this gives you the BUG / WRONG_AUTO_WROTE baselines.
- Then sketch ≥2 candidates that explicitly differ (e.g., one tier-2 only, one quarter-equality, one strict same-event-only). Avoid trivially-same candidates.
- Test each candidate on FCX `0000831259-26-000021` first — it must NOT auto-resolve, regardless of which candidate you pick. The corpus places it in NR/not_same_event_periodic.
- Run the verifier after each major change. Iterate until exit 0.
- For tie-breaking among candidates: prefer simpler (fewer LOC, fewer dependencies) and explicit (deterministic decision tree) over heuristic.

---

## OUT-OF-SCOPE / FUTURE

- Production fix design (Goal 3)
- Implementation in scripts/earnings/quarter_identity.py (Goal 4)
- Write-guard in the orchestrator (Goal 4)
- Goal 1.5 SEC EDGAR audit is already DONE (commit 04789af).
