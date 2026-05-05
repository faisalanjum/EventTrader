# Quarter Identity Resolver - Ground Truth And /goal Plan

Last updated: 2026-05-05

## Why This Exists

We hit a real production-relevant bug during the FCX learner canary:

- Input earnings 8-K: `FCX 0000831259-26-000021`, filed 2026-04-23.
- Correct event identity: `Q1_FY2026`, period ending 2026-03-31.
- Current resolver result: `Q4_FY2025`.
- Cause: the Q1 10-Q did not exist yet, so the resolver selected the most recent periodic filing, FCX's prior Q4 10-K, and the 150-day stale threshold treated it as close enough.

The quarter identity controls the event directory, PIT cutoff, prediction files, learning files, prior lessons, audit target, and library writes. If it is wrong, a live earnings run can write Q1 data into a Q4 folder, delete the wrong prediction artifact, and contaminate the lesson lifecycle.

The problem is not "fix FCX." The real problem is:

> Given an earnings 8-K accession, determine the fiscal quarter identity safely in both historical and live modes, and refuse destructive writes when the identity is not proven.

## /goal Operating Lesson

`/goal` should not be pointed at "figure out and fix the resolver" as one huge task.

Reason: `/goal` works best when the objective has:

- a scoped target
- a behavior contract
- explicit non-goals
- a verification path

For this resolver, the hard part is not editing code. The hard part is defining ground truth. Therefore we should use `/goal` in small stages:

1. Discover and define the ground-truth hierarchy.
2. Build a shadow validation corpus and evidence report.
3. Propose the minimal production algorithm and write guard.
4. Only after review, implement code and tests.

Important guardrail:

> The goal must produce evidence artifacts, not just a confident markdown explanation.

Acceptable artifacts include CSV/JSON mismatch reports, sampled accession evidence, exact Cypher/Python commands, test output, and a final pass/fail matrix.

## Ground Truth Hierarchy

There may not be a single automatic source that is literally 100% correct for every filing at the moment of the 8-K. Production-grade means auto-resolve when evidence is strong, otherwise fail closed before writing.

### Tier 1 - Same-event filing evidence

Best live ground truth IN THEORY — but currently constrained.

Use the 8-K's own attached earnings release, usually EX-99.1, and extract the period being announced:

- "quarter ended March 31, 2026"
- "three months ended March 31, 2026"
- financial table headers for the just-reported quarter
- annual vs quarterly language for Q4 cases

Why this matters:

- It exists at live trigger time.
- It is tied to the exact 8-K accession.
- It avoids waiting for a future 10-Q/10-K.

**User constraint (2026-05-05)**: string parsing of EX-99.1 is VETOED. Empirical reality from the conversation: regex extraction tops out at ~98-99% reliability (varied phrasing like "1Q26", "fiscal first quarter 2026", "13-week period ended..." for 52/53-week filers; year-transition ambiguity). Not 100%, and per the user not the path we take.

Implication for Goal 1: Tier 1 is OFF the candidate list unless Codex independently demonstrates a deterministic, non-fragile extraction (extremely unlikely without a LLM in the loop, which defeats the purpose). Plan should treat Tier 2 + Tier 3 + sequence checks as the practical truth set, with Tier 1 deferred to potential future enrichment only.

Open question for Goal 1 (revised):

- Can same-event evidence be obtained WITHOUT text parsing? (E.g., 8-K's own XBRL — though confirmed earlier this conversation it lacks fiscal_period tags.)
- If not, is it acceptable for live mode to rely on Tier 2 (matched periodic when same-quarter) + Tier 3 (sequence) + Tier 4 (fiscal_math) only, with Tier 1 as a fallback gated behind the write guard?

### Tier 2 - Same-quarter periodic XBRL

Best historical oracle after the matching 10-Q/10-K exists.

Use the matching periodic filing's:

- `dei:DocumentFiscalYearFocus`
- `dei:DocumentFiscalPeriodFocus`
- `periodOfReport`
- known XBRL denylist and proximity guard already present in the codebase

Strength:

- SEC/company-authored fiscal identity.
- Existing corpus validation already reports very high accuracy.

Limit:

- It is not available in live mode before the 10-Q/10-K is filed.
- It is not literally perfect; the repo already has known bad XBRL/denylist cases.
- It can be the wrong quarter if the resolver selects the previous periodic filing.

### Tier 3 - Sequence and calendar checks

Useful cross-checks, not standalone ground truth.

Examples:

- previous earnings 8-K sequence
- expected next quarter after previous event
- FYE month
- normal reporting lag window
- event filing date relative to computed quarter ends

This can identify suspicious cases, such as an 8-K filed in April being mapped to a December period for a calendar-year filer.

### Tier 4 - Fiscal math

Fallback heuristic only.

Fiscal math answers: "Given filing date and FYE month, which quarter-end is most plausible?"

It is useful in live mode, but it is not ground truth by itself because:

- fiscal-year naming conventions differ for some retailers and non-calendar filers
- early/late reporters can stress the window
- previous codebase notes show fiscal math trails XBRL truth on historical validation

## Production Principle

The final resolver should not pretend every case is equally certain.

It should return both identity and confidence/source, for example:

- `source = same_event_exhibit`
- `source = matched_periodic_xbrl`
- `source = sequence_plus_fiscal_math`
- `source = unresolved_needs_review`

And the orchestrator should have a write guard:

> Do not delete or overwrite an existing event directory unless quarter identity is proven or the user passes an explicit override.

This is the key safety fix. Even a mostly-correct resolver should not be allowed to silently destroy artifacts when the identity is ambiguous.

## Confidence Standard

This work should be better than any formula-only resolver, but it must not claim certainty it does not have.

Confidence ladder:

```text
Weakest:   pure fiscal formula
Better:    current resolver with periodic XBRL + heuristics
Best:      same-period periodic XBRL
           + fiscal_math agreement
           + sequence/calendar checks
           + denylist/proximity exclusions
           + NEEDS_REVIEW residual bucket
           + stratified SEC-linked audit packets
```

Target confidence:

- Historical benchmark corpus: conservatively ~99.5-99.9% accurate after deterministic filters and stratified audit.
- Live/no-periodic cases: must not be forced into the corpus; they are handled later by guarded resolver design and fail-closed behavior.
- Absolute 100% truth for every row is not honestly achievable automatically because SEC/company XBRL can be wrong and fiscal math can share edge-case blind spots.

Operational standard:

> Beyond reasonable operational doubt for benchmarking and resolver design, not beyond all possible doubt.

Remaining doubts are resolved by targeted SEC-linked audit, not by LLM eyeballing thousands of rows.

Audit approach:

1. Codex/Claude generates deterministic audit packets for risky and representative rows.
2. Each packet includes SEC accession URL, EX-99.1 snippet/table header for human eyes only, matched periodic accession, XBRL fiscal tags, period dates, fiscal math result, and sequence context.
3. Human/assistant reviewer marks each packet `ok`, `wrong`, or `unclear`.
4. Any `wrong` packet blocks Goal 1 sign-off until the root cause is understood and the corpus rule is fixed or the affected class is excluded.
5. Any `unclear` packet gets direct SEC filing review with more context before sign-off.

Goal 1 should remain deterministic corpus construction. The audit packets are Goal 1.5: they validate the corpus standard without turning the LLM into a slow manual reviewer for all 5,000+ rows.

## Proposed /goal Breakdown

### Goal 1 - Ground Truth Discovery Only

No production code changes.

Purpose:

- Build the strongest deterministic historical benchmark corpus available from allowed data sources.
- Separate same-event XBRL + fiscal_math agreement rows from all residual rows.
- Prove the construction process with an independent full-corpus verifier.

Non-purpose:

- Goal 1 does NOT solve live/no-periodic rows like FCX Q1 FY2026.
- Goal 1 does NOT use EX-99.1 parsing or LLM text extraction.
- Goal 1 does NOT propose or implement resolver fixes.

Completion criteria:

- `ground_truth.csv`, `needs_review.csv`, `build_corpus.py`, and `REPORT.md` exist under `earnings-analysis/canary/quarter_resolver/`.
- Every eligible earnings 8-K lands in exactly one of `ground_truth.csv` or `needs_review.csv`.
- `ground_truth.csv` contains only rows where same-event periodic XBRL, fiscal math from the periodic period, denylist/proximity checks, and structural timing all pass.
- `needs_review.csv` carries the canonical reason for every residual row.
- `verify_ground_truth_corpus.py` exits 0 after full-corpus independent re-derivation.

**Final /goal command + verifier**: see `.claude/plans/goal_1_prompt.md` and `earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py` (hand-written, git-committed, immutable during /goal execution).

Locked deliverable schema (from goal_1_prompt.md):
- `ground_truth.csv` — 13 columns including `matched_accession_periodic` (raw, NOT PIT-masked) and `periodic_created` (timestamp). Every row passes structural same-event constraint `periodic_created > filed_8k`.
- `needs_review.csv` — same columns + `reason ∈ {no_fye, not_same_event_periodic, no_xbrl, denylist, proximity_rejected, xbrl_math_disagree}`. Reason codes assigned in priority order (first match wins).
- `build_corpus.py` — deterministic, re-runnable, sorts before write.
- `REPORT.md` — concise breakdown + flagged anomalies.

Verifier enforces (in order):
- C1: verifier file is git-clean (anti-tampering)
- C2-C4: required deliverables exist, exact GT/NR schemas, no extra columns
- C5: no duplicate `accession_8k` inside GT or NR
- C6-C7: per-row invariants (incl. structural `periodic_created > filed_8k`, raw-accession DENY check, reason-code validity)
- C8: universe coverage `union(GT, NR) == eligible_universe`, no overlap, no missing
- C9: FULL re-derivation for every eligible row (no sampling): canonical classification, reason code, and copied metadata fields must match raw Neo4j + production helpers
- C10: GT row count ≥ 5,000

Goal 1.5 (post-Goal-1): see `.claude/plans/goal_1_5_prompt.md` and `earnings-analysis/canary/quarter_resolver/verify_audit_packets.py` — stratified ~150-200 audit packets across 6 buckets, structural packet verifier, human/assistant verdict gate. NOT LLM-at-scale judgment.

### Goal 2 - Shadow Validator Design

No production code changes unless explicitly approved.

Purpose:

- Turn the Goal 1 findings into a repeatable validator.
- Ensure the validator checks actual evidence, not old-vs-new agreement.

Completion criteria:

- Shadow validator can run over the corpus without SDK calls.
- It emits `AUTO_OK`, `BUG_FIXED`, `REGRESSION`, `NEEDS_REVIEW`, and `NO_EVIDENCE`.
- It uses historical XBRL only when the matched periodic is same-quarter.
- It does not allow "old resolver agrees" as proof.

### Goal 3 - Minimal Production Fix Design

No implementation until user approves the design.

Purpose:

- Decide the smallest code change that is both correct and safe.

Expected shape:

- Resolver logic that distinguishes same-quarter matched periodic from previous-quarter periodic.
- Same-event or sequence fallback for live mode if evidence is strong.
- `needs_review`/low-confidence source when evidence is not strong.
- Orchestrator write guard before unlinking or overwriting artifacts.
- Tests for FCX, normal historical rows, latest-live rows, and known edge cases.

### Goal 4 - Implementation

Only after Goals 1-3 are reviewed.

Completion criteria:

- Unit tests for resolver.
- Shadow corpus validator clean or every mismatch manually classified.
- Orchestrator refuses destructive writes for unproven identity.
- FCX Q1 FY2026 resolves or fails closed, but never writes into Q4.
- Full relevant earnings test suite passes.

## Current Working Hypothesis

The likely final answer is a hybrid:

1. If the 8-K/exhibit itself clearly names the reported period, use that.
2. Else if a same-quarter periodic XBRL filing exists, use XBRL fiscal identity.
3. Else if sequence plus fiscal math is internally consistent and not suspicious, allow a guarded live fallback.
4. Else return `NEEDS_REVIEW` and block destructive writes.

This is more honest than claiming 100% automatic resolution from fiscal math alone.

## Open Questions For Goal 1

- Do our stored 8-K/exhibit payloads consistently contain enough text/table structure to identify "quarter ended" dates?
- What is the true coverage of same-event evidence across the 10,995 earnings 8-Ks?
- Can Q4 vs annual release language be detected safely from the exhibit tables?
- How often does same-event exhibit evidence disagree with later XBRL?
- Which known XBRL denylist cases should remain exceptions?
- What exact resolver source values should permit artifact deletion/overwrite?

## References

- FCX canary issue note: `.claude/plans/fcx_canary_issues_2026-05-05.md`
- Current resolver: `scripts/earnings/quarter_identity.py`
- Existing corpus validator: `scripts/earnings/test_quarter_identity.py`
- Prior accuracy notes: `.claude/plans/prediction-system-v2.md`
- PIT/future periodic issue notes: `.claude/plans/earningsBundleRenderer.md`
- /goal operating guidance: https://ralphable.com/blog/codex-goal-command-ralph-loop-openai-built-in-autonomous-coding-agent-2026

---

## Appendix A — /goal research synthesis (2026-05-05)

Findings from external sources on how `/goal` actually works and how it fails. Used to design our verification.

### How /goal works internally (Ralph loop)

- Each turn after `pursuing` injects `continuation.md`.
- `continuation.md` decomposes the objective into requirements and asserts: **"Do not accept proxy signals as completion by themselves."**
- `budget_limit.md` fires on token exhaust; instructs graceful wrap, no false-completion.
- State transitions via structured `update_goal` tool call (machine-readable, not text-parsing).
- "The Ralph loop's intelligence is in the loop, not in the agent." → put rigor in verification, not in the prompt's eloquence.

### Documented failure modes

1. **Vague objectives** — "Garbage in, garbage out, autonomously."
2. **Proxy-signal acceptance** — "tests pass" ≠ "right behavior tested". Agent declares done, code is wrong.
3. **Open-ended exploration without success criteria** — agent burns budget on the wrong things.
4. **Hand-written prompts** that miss what the agent needs (humans underestimate context required).

### Best vs worst use cases (per article)

**Best**: multi-step deterministic work, bounded scope, verifiable by a runnable command, ≥3 turns expected.

**Worst**: single-turn work, open-ended exploration, high-stakes irreversible operations, subjective aesthetics, decisions requiring human architectural input.

**Decision heuristic**: *"If you can write the task as a passing test, use /goal. If you cannot, you probably want a chat, not a loop."*

### Implications for OUR task

The overall task ("find the perfect quarter resolver") is **NOT a single passing test** — it has judgment calls (algorithm choice, safety mechanism design, ground-truth construction). Running it as one /goal would risk false-success.

**The right move (which the existing breakdown above already does)**: decompose into Goals 1-4. Each Goal must be expressed such that an INDEPENDENT verifier script can decide pass/fail without trusting the agent's claims.

---

## Appendix B — Verification-script-must-be-independent principle

Critical risk we must mitigate: **the agent could write a verifier script that rubber-stamps its own output.**

### The rule

For every Goal in the breakdown, the **verifier script is hand-written by us** (or hand-reviewed before delegation). The agent's job is to produce output that passes OUR verifier. The verifier and the agent's main code path must NOT share helpers — otherwise a bug in the helper gets confirmed by both sides.

### Concrete pattern per Goal

| Goal | Agent produces | We hand-write the verifier that |
|---|---|---|
| Goal 1 (ground truth) | `ground_truth.csv` + `needs_review.csv` + `build_corpus.py` + `REPORT.md` | C1-C10 in `verify_ground_truth_corpus.py` — anti-tampering, deliverables, exact schemas, no duplicates, per-row invariants, universe coverage, FULL re-derivation across every eligible row (no sampling), row count |
| Goal 1.5 (audit packets) | `audit_packets.json` + `audit_packets.csv` + `SAMPLING_REPORT.md` | P1-P10 in `verify_audit_packets.py` — anti-tampering, deliverables, packet count + bucket distribution, schema, no duplicate accessions, cross-check against ground_truth.csv, well-formed SEC URLs, human_verdict unfilled |
| Goal 2 (shadow validator) | classifier output over the corpus | re-implements the classification rule from the spec on the FULL eligible universe (no sampling); asserts agent's labels match canonical labels for every row |
| Goal 3 (algorithm) | candidate algorithms in pseudocode | reviews structurally; we run them on the corpus ourselves |
| Goal 4 (impl) | code diff + test additions | runs the full pytest suite + shadow validator; asserts both green |

### Rule of thumb

If we cannot write a verifier in <30 minutes, the Goal is too vague. Sharpen the deliverable until a verifier becomes obvious.

---

## Appendix C — The "100% precision" question, answered

**Q (user)**: "How can /goal verify ground truth with 100% precision?"

**A**: It can't, in absolute terms. But it CAN achieve "rock-solid for our purposes" via:

1. **Multi-source agreement**: only rows where Tier 2 (XBRL fiscal focus) AND Tier 4 (fiscal_math from period_of_report) agree make the cut. Probability of two independent sources making the SAME error on the same row is very low for normal filers (~0.2%).
2. **Conservative exclusions**: rows where they disagree → `NEEDS_REVIEW` bucket, not ground truth. Never silently dropped.
3. **Existing safeguards reused**: `should_use_xbrl_fiscal` proximity guard + `XBRL_DENY_PERIODIC_ACCESSIONS` denylist filter known-bad XBRL.
4. **Determinism**: re-running the construction script produces identical output (verifier confirms).
5. **Independent verifier**: separate logic re-validates each row's claim from raw Neo4j without trusting the corpus file.
6. **Stratified manual audit**: human/assistant reviewer checks ~150-200 SEC-linked audit packets, weighted toward edge buckets, against original SEC filings.
7. **Acknowledged blind spots**: AAP/ACI extreme 52-week calendars where both XBRL and fiscal_math could be wrong-but-consistent. Pre-flagged in the corpus with `flag=extreme_calendar`, excluded from primary pass criteria, tracked separately.

**Result**: ground truth is "best-available, multi-source-confirmed, conservatively filtered, independently verifiable, human-audited" — strongest standard achievable without a paid 3rd-party AND without string parsing.

For Goal 1: agent must NOT claim "100% verified ground truth." Must claim "high-confidence ground truth with documented residuals." Verifier script enforces residuals are classified, not silently dropped.

---

## Appendix D — Additional risks log (R1-R6)

Extending the existing plan with risks specific to /goal autonomy:

- **R1 — Self-rubber-stamping verifiers**: Agent writes a verifier that always passes. Mitigation: we hand-write all verifier scripts BEFORE handing off to /goal. (See Appendix B.)
- **R2 — Sub-goal C ("propose algorithms") is not a passing test**: judgment-heavy. Mitigation: scope as "produce N distinct algorithm specs in this template; verifier checks structural completeness only; humans pick the winner."
- **R3 — Sub-goal E (safety mechanism) involves design judgment**: Mitigation: provide ChatGPT's accession-sentinel pattern as baseline; agent must either adopt or beat it (defined "beat" = prevents same threats with smaller surface).
- **R4 — AAP/ACI residuals dominate pass criteria**: Mitigation: pre-flag these tickers in the corpus; exclude from primary pass criterion; track separately.
- **R5 — /goal's `budget_limit.md` mid-investigation**: Mitigation: each sub-goal sized to fit a single goal session; CSVs and markdown artifacts persist across sessions.
- **R6 — Misuse of 8-K cover-page XBRL**: 8-K cover-page XBRL exists but doesn't reliably carry fiscal_period tags (entity-ID metadata only). Tell Codex this in the prompt's "background facts" so it doesn't waste budget chasing this dead path.

---

## Appendix E — Decisions LOCKED (2026-05-05, user-confirmed all defaults)

| # | Decision | LOCKED |
|---|---|---|
| D1 | Goal 1 scope | (b) — read-only Neo4j + scratch writes only to `earnings-analysis/canary/quarter_resolver/` and `/tmp/` |
| D2 | Number of /goal invocations | (a) — one /goal per Goal (4 total, each gated by human review) |
| D3 | Ground-truth corpus minimum row count | ≥5,000 rows of two-source agreement |
| D4 | Algorithm candidates | (b) ≥2 — forces comparison |
| D5 | Manual audit sample size (Goal 1.5) | ~150-200 stratified audit packets; Goal 1 verifier uses full-corpus re-derivation, no sampling |
| D6 | Pass-criterion strictness | ≥ ground-truth ceiling, residuals classified into NEEDS_REVIEW |
| D7 | Time budget per Goal | 1-2h per Goal, hard 4h cap |
| D8 | Tier 1 (EX-99.1) treatment | (a) fully off — per user 2026-05-05 |

---

## Appendix F — Master `/goal` prompt template

Before drafting the actual Goal 1 prompt, our template structure:

```
/goal <one-line mission>

CONTEXT
- 5-10 background facts (paths, prior findings, constraints)
- Pointer to this plan file

INPUTS AVAILABLE
- Existing modules / Neo4j queries / data sources

OUTPUTS REQUIRED
- Exact file path(s)
- Exact schema(s)
- Required artifact format

NON-GOALS
- What NOT to do (production code, paid APIs, etc.)

DONE WHEN (verifier-checkable)
- The independent verifier script at <path> exits 0
- Specific assertions the verifier makes
- Numerical thresholds the output must meet

OUT-OF-SCOPE / FUTURE
- Things to flag for follow-up but not address now
```

Each Goal in the breakdown above gets its own prompt filled in from this template, with the `DONE WHEN` block being the load-bearing piece.

---

## Status tracker (master)

- [x] First-principles articulation (sections "Why This Exists" + "Real Problem")
- [x] Ground-truth landscape mapped (sections "Ground Truth Hierarchy" + Appendix C)
- [x] Verification philosophy from /goal research (Appendices A + B)
- [x] Sub-goal decomposition draft (section "Proposed /goal Breakdown")
- [x] Tier 1 (EX-99.1) reconciled with user veto (revised inline)
- [x] Open decisions enumerated (Appendix E)
- [x] Decisions D1-D8 LOCKED with user (2026-05-05) — Appendix E
- [x] Goal 1 verifier hand-written (`earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py`)
- [x] Goal 1 verifier hardened: full-corpus re-derivation (no sampling), duplicate detection, all-deliverables enforcement, exact schema matching, anti-tampering git-clean check
- [x] Goal 1 prompt finalized (`.claude/plans/goal_1_prompt.md`)
- [x] Goal 1.5 prompt finalized (`.claude/plans/goal_1_5_prompt.md`)
- [x] Goal 1.5 verifier hand-written (`earnings-analysis/canary/quarter_resolver/verify_audit_packets.py`)
- [x] Verifier(s) committed to git (REQUIRED before /goal — verifier C1 will refuse to run otherwise)
- [ ] Goal 1 executed via /goal (Codex)
- [ ] Goal 1 verifier exits 0 (independent re-run by human)
- [ ] Goal 1.5 executed via /goal (Codex prepares packets)
- [ ] Goal 1.5 verifier exits 0 (packet structural check)
- [ ] Goal 1.5 human audit complete (~150-200 packets reviewed; 0 `wrong` verdicts)
- [ ] Goal 2 prompt finalized
- [ ] Goal 2 executed
- [ ] Goal 3 prompt finalized
- [ ] Goal 3 executed
- [ ] Goal 4 (implementation) prompt finalized — only after 1-3 reviewed
- [ ] Goal 4 executed
- [ ] FCX-style smoke test repeated under new resolver
- [ ] FCX canary outputs (Q3+Q4) re-validated under new resolver
- [ ] Production deploy + post-deploy monitor

---

## Conversation log (append as we iterate)

- 2026-05-05 14:23 — file created (0 bytes)
- 2026-05-05 ~14:25 — populated with ChatGPT-style structure (Why / Ground Truth Hierarchy / Goal breakdown / Working Hypothesis / Open Questions)
- 2026-05-05 14:30+ — Claude appended /goal research synthesis, verification-script independence principle, "100% precision" answer, risks log, open decisions, prompt template, master status tracker. Reconciled Tier 1 (string parsing) with user's earlier veto.
- 2026-05-05 — Next step: settle decisions D1-D8 (Appendix E), then hand-write Goal 1 verifier, then write Goal 1 prompt from template.
