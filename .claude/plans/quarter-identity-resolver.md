# Quarter Identity Resolver - Final Context

Last updated: 2026-05-07

## Current State Snapshot (2026-05-07)

Production status:

- Goal 6c shipped Candidate D into `scripts/earnings/quarter_identity.py` and was pushed (`a61636a`, followed by wording/doc cleanup `2f61810`).
- Goal 6e guidance fallback hardening shipped and was pushed (`be4c2cc`): the rare 10-Q/10-K guidance source-quarter fallback now prefers own-filing XBRL only when denylist/proximity guards pass, then falls back to math.
- Goal 6f research completed with `KEEP_D`; no lock-respecting structural candidate beat D without adding wrong AUTO_OK rows.
- Goal 6g shipped and was pushed (`237f53c`): a narrow audited 18-issuer `TRUST_XBRL_ADVANCE` bucket recovers known-safe calendar-FY-disagreement fail-closures without adding wrong AUTO_OK rows.
- Post-6g centralization pass completed: runtime 8-K consumers now route through `quarter_identity.resolve_quarter_info()`, and periodic 10-Q/10-K fallback consumers route through `get_quarterly_filings.choose_periodic_fiscal_identity()`.
- The final durable truth file is `data/quarter_identity_ground_truth.csv`. Old canary/verifier/audit scaffolding can be deleted after this context is consolidated.

Final Goal 6g measured behavior:

| Subset | Correct-fire | Wrong-fire | Fail-closed |
|---|---:|---:|---:|
| Full historical scoreable (10,674) | 9,673 | 24 | 977 |
| Warm-start historical (9,878) | 9,673 (97.92%) | 24 (0.24%) | 181 (1.83%) |
| Cold-start (796) | 0 | 0 | 796 (100%) |
| Latest-per-ticker live proxy (781) | 764 (97.82%) | 3 (0.38%) | 14 (1.79%) |

Operational meaning:

- Cold-start / fail-closed rows do not auto-write event bundles. The orchestrator write guard refuses destructive writes unless `safety_action == "AUTO_OK"`.
- Prediction/learner/live earnings runs through `earnings_orchestrator.py` are protected by that guard.
- Guidance extraction is separate. Only guidance **source-quarter harvesting** for 8-Ks uses `resolve_quarter_info()` automatically; guidance target-period construction does not.

What triggered Goals 6a→6f (the Goal 5 hole):

- Goal 4's "0 WRONG / 9,116 AUTO_OK / 9,943 oracle" was on its measured oracle scope. It did NOT score the 838 NR rows where Goal 4 still fired AUTO_OK.
- Goal 5 SEC-audited those 838 NR-AUTO_OK rows: `144 correct / 587 wrong / 107 unclear`.
- Goal 5 surfaced 7 candidate algorithms (A-G + variants); only Candidate D respected the structural-only locks. Codex tried Candidate E (industry classifier) and it was rejected.
- Goal 5 itself shipped no production code — only artifacts. It was the input to Goal 6a measurement → Goal 6c production.

Rejected path:

- A 34-edge-ticker SEC audit (408 historical 8-Ks) tested future Rule G2: "trust XBRL FY/Q on FY-disagreement and advance."
- Result: `DECISION_FLAG_RULE_G2 = promising_but_not_shippable`.
- Tier A+B rows: D = `95 correct / 12 wrong / 293 fail-closed`; G2-calendar-only = `316 correct / 49 wrong / 35 fail-closed`; G2-all = `334 correct / 51 wrong / 15 fail-closed`.
- G2 saves many fail-closures but creates 37-39 new wrong AUTO_OK rows. Do not ship blind XBRL-trust.
- Failure clusters include GIII, BOX, WDAY, WMS, NTAP, NTNX, DKS, ANF, where issuer iXBRL FY naming and public EX-99.1 FY naming diverge.

The architectural finding (named, so future-you doesn't rediscover it):

- **iXBRL year-of-start vs EX-99.1 year-of-end divergence**. iXBRL `DocumentFiscalYearFocus` for an FYE-January issuer reports `FY=2024` for a 10-K covering Feb 2024 – Jan 2025; the same issuer's EX-99.1 press release calls the same period `FY 2025`.
- Both labels are "correct" for their audience. They disagree on the wire.
- Any production rule that trusts XBRL `FY` will systematically wrong-write the year for ~10% of off-calendar issuers. D's `rule_f_fail_closed_fy_disagreement` (Goal 4) and the calendar-branch `rule_g_fail_closed_*_calendar` guards (Goal 6c) intentionally fail-closed on this class.
- Under the old strict structural locks (no issuer bucket at all), this divergence was the **irreducible structural class**. ~4.4% of the universe (34/781 latest-per-ticker proxy) was unresolvable and had to remain fail-closed.
- This was the load-bearing reason `KEEP_D` was the correct Goal 6f outcome.
- Goal 6g made one deliberate exception: an audited 18-issuer uniform bucket where the same XBRL-advance rule held across each issuer's history. That reduced latest-per-ticker fail-closed rows from 31 to 14 without changing the wrong-fire count.

Goal 6f research result:

- Goal 6f diagnosed D/G2 failures first, then tested multi-prior XBRL consistency, period-end/calendar-shape signatures, current 8-K own XBRL facts, and advance-result agreement.
- **Result (2026-05-07)**: `DECISION_FLAG_GOAL6F_RECOMMENDATION = KEEP_D`. Verifier passed; 4 new structural candidates tested + rejected; commit `0552fd9` registered the immutable audit-evidence inputs.
- The failure-class name from the failure model: "structural ambiguity after FY disagreement" — the same prior structural shape produces both safe and unsafe rows; no allowed signal uniquely discriminates under the old no-issuer-bucket lock.
- Goal 6g intentionally relaxed that lock once, for exactly 18 audited issuers whose rule held across their time series. Do not expand this bucket without a new audit/verifier.

Final production files to keep:

- `scripts/earnings/quarter_identity.py` — final resolver and Goal 6g audited bucket.
- `scripts/earnings/test_quarter_identity.py` and `scripts/earnings/test_quarter_identity_u64.py` — resolver/write-guard regression tests.
- `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py` — shared XBRL parsing/proximity/denylist helpers.
- `scripts/harvest_guidance_sessions.py` and `scripts/test_harvest_guidance_sessions.py` — guidance periodic fallback hardening.
- `scripts/earnings/get_earnings.py` — legacy 8-K listing now uses the canonical 8-K resolver, not coarse calendar math.
- `scripts/earnings/builders/prior_financials.py` — prior-financial fiscal labels now use the shared periodic-filing chooser instead of local fallback copies.
- `data/quarter_identity_ground_truth.csv` — durable ground-truth corpus kept after canary cleanup.

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

Implemented state after Goals 4/6c:

- `resolve_quarter_info(ticker, accession_8k)` returns a dict. Trust `quarter_label` only when `safety_action == "AUTO_OK"`.
- The orchestrator write guard blocks destructive event-directory writes on `FAIL_CLOSED`.
- Do not bypass the resolver with a plain fiscal-math formula for earnings 8-Ks.

## Consumer Map And Centralization Status

This section consolidates the repo-wide consumer audit. It answers: which code
paths resolve earnings 8-K quarter identity, periodic 10-Q/10-K fiscal
identity, or fiscal calendar dates, and will future canonical helper changes
flow into them?

Canonical modules:

- `scripts/earnings/quarter_identity.py`
  - Canonical earnings 8-K quarter identity resolver.
  - Public API: `resolve_quarter_info(ticker, accession_8k, *, session=None)`.
  - Use only for earnings 8-Ks.
- `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`
  - Shared periodic-filing helpers:
    - `parse_xbrl_fiscal_identity`
    - `should_use_xbrl_fiscal`
    - `choose_periodic_fiscal_identity`
    - `XBRL_DENY_PERIODIC_ACCESSIONS`
    - `fiscal_to_dates`
- `.claude/skills/earnings-orchestrator/scripts/fiscal_math.py`
  - Pure fiscal math:
    - `period_to_fiscal`
    - `_compute_fiscal_dates`

Important architecture distinction:

- `resolve_quarter_info()` answers: "which fiscal quarter is this earnings
  8-K announcing?"
- Periodic 10-Q/10-K filings usually carry their own fiscal labels. They use
  direct `Report.fiscal_quarter/fiscal_year`, then shared periodic XBRL helpers
  if those fields are missing.
- Guidance target-period construction is not source-quarter resolution. It
  builds calendar `GuidancePeriod` dates from already extracted
  `fiscal_year/fiscal_quarter` fields.
- Transcript fiscal labels come from the transcript event provider
  (`event.year`, `event.quarter`). The inline transcript helper derives only
  secondary `calendar_year/calendar_quarter` display fields from those fiscal
  labels.

### Canonical 8-K Quarter Identity Consumers

These call `quarter_identity.resolve_quarter_info()` and therefore benefit from
future changes to `quarter_identity.py`:

- `scripts/earnings/earnings_orchestrator.py`
  - Resolves `quarter_info` for prediction/learner/orchestrator flow.
  - Destructive-write guard blocks writes unless `safety_action == "AUTO_OK"`.
- `scripts/earnings/compare_section.py`
  - Resolves quarter identity for section comparison tooling.
- `scripts/earnings/render_section.py`
  - Resolves quarter identity for section rendering tooling.
- `scripts/harvest_guidance_sessions.py`
  - For `asset == "8k"`, lazy-imports and calls `resolve_quarter_info()`.
- `scripts/earnings/get_earnings.py`
  - Fiscal labels for earnings 8-K listings now come from
    `resolve_quarter_info()`, not old `calculate_fiscal_period()` calendar
    math.

Tests:

- `scripts/earnings/test_quarter_identity.py`
- `scripts/earnings/test_quarter_identity_u64.py`
- `scripts/test_harvest_guidance_sessions.py`
- `scripts/earnings/test_get_earnings_centralized.py`

### Canonical Periodic 10-Q/10-K Fiscal Identity Consumers

These use `get_quarterly_filings.choose_periodic_fiscal_identity()` and
therefore benefit from future changes to the shared periodic XBRL safety gate:

- `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`
  - Defines `choose_periodic_fiscal_identity()`.
  - `get_earnings_with_10q()` uses it for matched 10-Q/10-K labels.
- `scripts/harvest_guidance_sessions.py`
  - For `asset in ("10q", "10k")`: first reads
    `Report.fiscal_quarter/fiscal_year`; if missing,
    `_derive_via_period_to_fiscal()` computes math fallback and calls
    `choose_periodic_fiscal_identity()`.
  - Do not replace this with `resolve_quarter_info()`. This path labels the
    periodic filing itself, not an earnings 8-K.
- `scripts/earnings/builders/prior_financials.py`
  - `_get_fiscal_labels()` imports `choose_periodic_fiscal_identity()`
    directly.
  - Local fallback copies of `parse_xbrl_fiscal_identity()` and
    `should_use_xbrl_fiscal()` were removed.
- `.claude/skills/earnings-orchestrator/scripts/event_json_manifest.py`
  - Calls `get_earnings_with_10q()`, so it picks up the helper through that
    function.

Tests:

- `scripts/earnings/test_quarter_identity.py`
  - Direct helper tests for safe XBRL use, denylist fallback, and invalid XBRL
    fallback.
- `scripts/test_harvest_guidance_sessions.py`
  - Guidance 10-Q/10-K fallback behavior.
- `scripts/earnings/test_builders_prior_financials.py`
  - Prior-financial helper routing, denylist, no-FYE XBRL fallback, and math
    fallback.

### Canonical Fiscal Date / Target-Period Consumers

These do not resolve source quarter identity. They convert known fiscal labels
to dates or compute fiscal labels for periodic periods:

- `scripts/earnings/builders/consensus.py`
  - Uses `period_to_fiscal()` and `_compute_fiscal_dates()`.
- `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py`
  - Uses `_compute_fiscal_dates()` for `GuidancePeriod` IDs/dates.
- `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py`
  - Uses Redis SEC quarter cache first, then `build_guidance_period_id()`.
- `scripts/sec_quarter_cache_loader.py`
  - Builds Redis SEC quarter cache from SEC company concept data.

These should not call `resolve_quarter_info()`.

### Remaining Inline / Non-Canonical Math

These are still present after centralization. They do not undermine the
earnings/report quarter resolver, but they should stay documented:

- `transcripts/EarningsCallTranscripts.py`
  - `calendar_to_fiscal()` is dead code; no production callers found.
  - `fiscal_to_calendar()` is live, but inverse/display-only:
    `fiscal_year/fiscal_quarter` come from the transcript provider, and this
    helper derives secondary `calendar_year/calendar_quarter` fields.
  - Do not replace it with `resolve_quarter_info()`. If centralizing it later,
    first add a canonical inverse helper such as
    `fiscal_to_calendar(fy, fq, fye_month)` to `fiscal_math.py`, then prove
    byte-equivalence with tests.
- `scripts/earnings/utils.py`
  - `calculate_fiscal_period()` has zero non-self Python callers after
    `get_earnings.py` moved to `resolve_quarter_info()`.
  - `calendar_to_fiscal()` is only used by that orphan helper.
  - Treat both as dead compatibility code; do not add new callers.
- `drivers/8K_XBRL_Linking/FinalScripts/xbrl_catalog.py`
  - Driver/exploration utility with inline fiscal calendar display math.
  - Called by its own `test_pipeline.py`; not an orchestrated production
    earnings/guidance write path.
  - If this driver is ever promoted to a write path, refactor its
    calendar-to-fiscal math to `period_to_fiscal()` and add a canonical inverse
    helper for its fiscal-to-calendar display mapping.

Validation from the centralization pass:

- `calculate_fiscal_period()` has no remaining production callers.
- Removed local fallback helpers no longer appear:
  `_parse_xbrl_fiscal_identity_fallback`,
  `_should_use_xbrl_fiscal_fallback`.
- Full local earnings suite passed after the pass:
  `1419 passed, 14 skipped, 43 subtests passed`.

## Consolidated Preservation Contract

This section replaces the old standalone `refactor-safety-contract.md` and
`restore-context.md` files. Keep it short, but treat it as load-bearing before
editing earnings/refactor/guidance code.

### Quarter Identity And Guidance

- `resolve_quarter_info(ticker, accession_8k)` is the earnings 8-K resolver. It is PIT-safe and may query prior 10-Q/10-K metadata; it is not pure fiscal math.
- Callers must trust `quarter_label` only when `safety_action == "AUTO_OK"`.
- Cold-start and unsafe cases must fail closed. Wrong-write prevention is more important than 100% firing.
- FCX `0000831259-26-000021` must remain `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1`.
- Rule F odd 52/53-week regression must remain `94 OK / 0 WRONG / 21 FAIL_CLOSED`.
- Goal 6g's `TRUST_XBRL_ADVANCE` is the only approved issuer bucket. It is a uniform issuer-level rule for 18 audited issuers, not a per-period exception table. Do not expand it without fresh SEC-backed evidence and tests.
- Do not add industry/sector/SIC/GICS/NAICS dispatch, EX-99.1 runtime parsing, external HTTP/API calls, ML/LLM classifiers, or arbitrary new thresholds.
- Guidance has two fiscal-identity concepts: source-quarter labeling and extracted guidance target periods. Do not merge them.
- Guidance 8-K source-quarter harvesting uses `resolve_quarter_info()` and picks up future 8-K resolver improvements.
- Guidance 10-Q/10-K fallback is separate: use stored `Report.fiscal_quarter/fiscal_year`, then own-filing XBRL with denylist/proximity guards, then math fallback. Do not swap the 8-K resolver into this periodic fallback.
- Changes to `parse_xbrl_fiscal_identity`, `should_use_xbrl_fiscal`, or `XBRL_DENY_PERIODIC_ACCESSIONS` can affect both the resolver and guidance periodic fallback. Changes to `resolve_quarter_info()` affect 8-K consumers only.

### Bundle, Evidence, And Lessons

- Rendered text remains the predictor's primary reasoning surface. JSON remains verification/structure, not the primary predictor surface.
- `context_bundle.json` schema is append-only for this audit surface. Do not rename or remove existing fields casually.
- `--save-dir` must stay run-scoped. Do not restore shared `/tmp/context_bundle.json` or `Path(save_dir).parent` behavior.
- `evidence_source_catalog` IDs are event-scoped: `SRC:<ticker>:<quarter_label>:<accession_8k>#<location>`.
- Production validation must enforce expected source-id membership and reject empty evidence ledgers.
- Keep rendered `N{i}` and `F{i}` aliases and raw `event_ref` anchors; the predictor sees the rendered aliases, and raw anchors preserve traceability.
- `prediction_validated` must gate result quarantine. Do not let a later ledger/cleanup exception quarantine a validated result.
- `iter_labeled_lessons()` in `_text_utils.py` is the shared source of truth for renderer `L#` ordering and catalog lesson anchors.
- Do not dedupe duplicate lesson bodies across scopes. Positional labels are intentional.
- Empty learning context still renders the outer prior-lessons section and "No prior lessons available..." message.
- Golden render fixtures are not bloat. Full/section/degraded goldens and targeted tests catch different regressions.

### Required Local Checks

For ordinary earnings refactors:

```bash
venv/bin/python -m pytest scripts/earnings -q
venv/bin/python -m scripts.earnings.tests._capture_golden full
venv/bin/python -m scripts.earnings.tests._capture_golden sections
venv/bin/python -m scripts.earnings.tests._capture_golden degraded
git diff -- scripts/earnings/tests/fixtures/golden_renders scripts/earnings/tests/fixtures/golden_bundles
```

For quarter-identity changes, also run the focused resolver tests:

```bash
venv/bin/python -m pytest scripts/earnings/test_quarter_identity.py scripts/earnings/test_quarter_identity_u64.py -q
```

After cleanup removes the old canary verifiers, this file, the resolver tests,
and `data/quarter_identity_ground_truth.csv` are the durable references.

### New Session Bootstrap

If a future session needs quarter-resolver context, read only these first:

1. This file.
2. `scripts/earnings/quarter_identity.py`.
3. `scripts/earnings/test_quarter_identity.py`.
4. `scripts/earnings/test_quarter_identity_u64.py`.
5. `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`.
6. `scripts/harvest_guidance_sessions.py` and `scripts/test_harvest_guidance_sessions.py` if guidance is involved.
7. `data/quarter_identity_ground_truth.csv` only with `head`, `rg`, or small scripts; do not read the whole CSV into chat.

Dirty-worktree rule: this repo often has unrelated modified/deleted/untracked
files. Do not revert, stash, delete, or commit them unless the user explicitly
asks. Scope commits by explicit path.

User preference: concise answers by default; independently verify Claude/Codex
claims before signing off; prioritize zero wrong-writes over maximum firing
rate; no `Co-Authored-By` trailer in commits.

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

Fallback if later goals shake confidence:

- If Goal 2/3/4 exposes surprising disagreement patterns that the deterministic verifiers cannot explain, or if the full Goal 2 verifier fails in a way that points back to corpus quality rather than resolver logic, do NOT keep tuning formulas blindly.
- Instead, expand Goal 1.5 into a larger manual SEC EDGAR audit using subagents: target ~2,000 stratified reports, weighted toward the failing buckets/patterns rather than uniform random sampling.
- The expanded audit should keep the same verdict discipline (`ok` / `wrong` / `unclear`), short SEC evidence quotes, exact accession/document URLs, and a hard stop on any `wrong` until root cause is understood.
- This is a fallback only, not the default path. Current 200-packet audit remains sufficient unless later full-corpus work reveals new doubt.

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

### Goal 3 - Live-mode resolver discovery (REVISED 2026-05-05)

**North star (locked)**: ≥99.9% of live earnings 8-Ks must fire predictions correctly. Goal 3 is investigative — discover whether that target is empirically achievable with live-available signals only, and benchmark candidates that maximize fire-rate while keeping wrong-auto-writes at 0.

**Why Goal 3 was reframed**: Goal 2 produced `periodic_fiscal_math` which is safe (zero WRONG_AUTO_WROTE on FCX-shape, 100% GT-AGREE retrospectively) but RELIES on the matched periodic's `period_of_report`. At PIT for live 8-Ks, that field is empty (the same-quarter 10-Q hasn't filed yet). Shipping `periodic_fiscal_math` as the production fix would block ~85-90% of live earnings predictions. Empirical probe (2026-05-05) confirmed 8-K's own `periodOfReport` is the SEC Date of Report (= filing date), NOT the fiscal quarter end:

```
Total earnings 8-Ks:                    10,995
periodOfReport populated:               10,995 (100%)
periodOfReport == filing date:          10,012 (91.1%)
periodOfReport within 1-5 days of filing: 716 (6.5%)
```

So Tier B (8-K's own periodOfReport → fiscal_math) is dead. Goal 3 must benchmark alternatives.

**Goal 3 method**: empirical, not declarative. Same investigative pattern as Goal 1.

PIT-safe candidate algorithms to benchmark (verifier-mandated, exact names):
- **A. `prior_periodic_projection`**: query Neo4j for the most recent prior 10-Q/10-K (created < filed_8k) → its `period_of_report` IS a fiscal quarter end (unlike 8-K periodOfReport) → compute `period_to_fiscal(...)` → advance one quarter (with FY rollover at Q4→Q1) → expected (fy, q). FAIL_CLOSED on cold start, gap >200 days, or denylisted prior accession.
- **B. `lag_window`**: filing_date + fye_month → most-recent-quarter-end + reporting-lag-window check (5-90 days). No prior-periodic dependency — serves as cold-start fallback.
- **C. `hybrid_agreement`**: A and B must agree → AUTO_OK; cold-start (B-only) → NEEDS_REVIEW; disagree → FAIL_CLOSED. Likely the recommended winner.
- All three are MANDATORY. Codex may propose additional candidates beyond these.

PIT-safety enforcement: candidate input is sanitized — must NOT see corpus oracle fields (`fy_xbrl`, `q_xbrl`, `fy_math`, `q_math`, `agreement`, `reason`) NOR matched-periodic fields (`period_of_report`, `matched_accession_periodic`, `periodic_created`, `form_type_periodic`). Allowed fields: `accession_8k`, `ticker`, `filed_8k`, `fye_month`. Candidate may query Neo4j BUT only with PIT-bound clauses (`created <= filed_8k`).

Goal 3 deliverables:
- `live_candidates.py` — executable Python with the **three mandatory candidates** named `candidate_live_prior_periodic_projection`, `candidate_live_lag_window`, `candidate_live_hybrid_agreement`. Codex may add additional `candidate_live_<other_name>` functions, but the three named ones are required.
- `live_mode_audit.csv` — full corpus × N_candidates audit with would_fire/correct/wrong-write rates
- `LIVE_MODE_REPORT.md` — per-candidate breakdown by FYE bucket / 52-53-week / Q4 / non-Dec-FYE; recommended candidate + reasoning
- `verify_live_mode_resolver.py` — hand-written verifier (immutable during /goal)

Goal 3 verifier hard-locks (the only ones):
- L1 git-clean
- L2-L4 deliverables exist + schemas match + the three mandatory candidates ({prior_periodic_projection, lag_window, hybrid_agreement}) importable
- L5 AST PIT-safety: candidates do NOT reference forbidden fields
- L6 universe coverage
- L7 independent re-derivation against PIT-masked context
- **L8 zero WRONG_AUTO_WROTE across all candidates (THE ONLY safety threshold)**
- L10 recommended candidate exists + has rows
- L11 report content sanity

Goal 3 verifier soft-reports (informational, not pass/fail):
- would_fire rate per candidate
- correct rate per candidate
- fail_closed rate per candidate
- per-FYE-bucket breakdown
- residual classification

The 99.9% target is **NOT verifier-hard-locked**. Goal 3's job is to PROVE whether that target is achievable. If the best candidate empirically achieves <99.9%, Goal 3's REPORT must classify the residuals and explain what additional signal would be needed (escalation to expanded audit, write-guard policy adjustments, etc.).

**Goal 3 result (2026-05-06)**:

- Verifier-passed artifacts: `live_candidates.py`, `live_mode_audit.csv`, `LIVE_MODE_REPORT.md`.
- Required candidates benchmarked: `prior_periodic_projection`, `lag_window`, `hybrid_agreement`.
- Recommended candidate: `prior_periodic_projection`.
- Full scored corpus: 10,831 rows = 9,909 GT + 922 NR.
- Full scored corpus result for `prior_periodic_projection`: 9,860 / 10,831 AUTO_OK = **91.03%** would-fire, **0 WRONG_AUTO_WROTE**.
- Warm-start historical PIT subset (exclude `no_prior` DB-history cold starts): 9,860 / 9,993 AUTO_OK = **98.67%**, **0 wrong-writes**. Scaled to ~10,000 reports: ~9,867 fire, ~133 defer, ~0 wrong.
- GT-only warm-start subset: 9,022 / 9,113 AUTO_OK with correct fiscal label = **99.00%**, **0 wrong-writes**.
- Latest-per-ticker live-like subset: 765 / 781 AUTO_OK = **97.95%**, **0 WRONG_AUTO_WROTE**. Scaled to ~10,000 reports: ~9,795 fire, ~205 defer, ~0 wrong.
- Latest-per-ticker residuals: 16 non-fires = 14 odd 52/53-week / odd fiscal-calendar prior-period shapes + 2 long-gap/stale-prior cases.
- Interpretation: the 91% full-corpus number is pessimistic for actual operations because 838 failures are early DB-history cold starts (mostly 2023). For warm-start historical replay and actual live today, the practical baseline is roughly **98-99% auto-fire with zero wrong-writes** before special handling.
- Achievability: current simple candidate does **not** prove 99.9%. The likely path to 99%+ is targeted 52/53-week / odd fiscal-calendar handling plus existing long-gap / denylist fail-closed guards. Do not revisit EX-99.1 / LLM extraction unless these deterministic residual fixes fail.

**Goal 3 non-goals**:
- No production code changes (resolver fix lives in Goal 4)
- No EX-99.1 string parsing (D8 veto)
- No assumption that 8-K periodOfReport carries fiscal quarter end (probe-disproven 2026-05-05)

**Goal 3 follow-on path**:
- Minimum viable Goal 4: implement `prior_periodic_projection` + destructive-write guard. Expected practical coverage: ~98-99% auto-fire, 0 wrong-writes, with remaining rows deferred.
- Recommended Goal 4 scope: include a focused 52/53-week / odd fiscal-calendar enhancement if a quick verifier/probe proves it raises coverage without introducing wrong-writes.
- Do NOT add EX-99.1 / LLM parsing in Goal 4; that remains out of scope unless deterministic residual handling fails.

### Goal 4 - Implementation

Only after Goals 1-3 are reviewed.

Completion criteria:

- Unit tests for resolver.
- Shadow corpus validator clean or every mismatch manually classified.
- Orchestrator refuses destructive writes for unproven identity.
- FCX Q1 FY2026 resolves or fails closed, but never writes into Q4.
- Warm-start historical PIT and latest-per-ticker live-like metrics are reported after the implementation.
- `prior_periodic_projection` is the primary live-mode resolver tier; `NEEDS_REVIEW` / `FAIL_CLOSED` / `NO_RESOLUTION` must block destructive writes.
- 52/53-week / odd fiscal-calendar residual handling is either implemented and verifier-proven, or explicitly deferred with expected coverage impact.
- Full relevant earnings test suite passes.

## Working Hypothesis (historical, pre-implementation)

> **Status**: This was the working hypothesis at the start of the project (2026-05-05). It is preserved here as historical context. The shipped resolver is described in the Snapshot section at the top of this file plus the Status tracker. Do not treat this as forward-looking — Goals 4 and 6c implemented and refined this hypothesis.

The likely final answer is a guarded prior-periodic projection resolver:

1. For live / PIT replay, use the most recent PIT-available prior 10-Q/10-K for the same company, derive its fiscal identity, and advance one quarter.
2. Apply deterministic guards: no prior periodic, stale/long gap, denylisted prior accession, odd 52/53-week / fiscal-calendar shape unless specifically handled.
3. Permit destructive writes only when `safety_action == AUTO_OK`.
4. Return `NEEDS_REVIEW`, `FAIL_CLOSED`, or `NO_RESOLUTION` for unproven identity; these must not create or overwrite event directories or prediction artifacts.

Historical retrospective mode may still use same-event periodic evidence when it exists, but live-mode and PIT replay must not rely on the future same-quarter 10-Q/10-K.

## Open Questions For Goal 1 (historical — Goal 1 closed at commit `fc83a1c`)

> **Status**: These were the open questions when Goal 1 was scoped. Goals 1 and 1.5 closed all of them; preserved here as historical context. Tier 1 (EX-99.1 string parsing) is locked OFF (D8); Tier 2/3/4 are reflected in the shipped resolver.

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

1. **Multi-source agreement**: only rows where Tier 2 (XBRL fiscal focus) AND Tier 4 (fiscal_math from period_of_report) agree make the cut. Probability of two independent sources making the SAME error on the same row is very low for normal filers (~0.2%). **Caveat (added 2026-05-07)**: this independence assumption holds for the Goal 1 GT corpus on calendar-year filers, but does NOT generalize to "trust XBRL when XBRL disagrees with math" on residual rows. The 34-edge-ticker SEC audit established that for off-calendar issuers (FYE January / February / August / etc.), iXBRL `DocumentFiscalYearFocus` uses year-of-start convention while EX-99.1 press releases use year-of-end — the two are *systematically biased* relative to each other, not independent errors. Two-source XBRL+math agreement remains a strong filter for the GT corpus; XBRL-trust on disagreement (proposed Rule G2) is empirically unsafe and was rejected. See the Snapshot section "The architectural finding" at the top of this file.
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
- [x] Goal 1 executed via /goal (Codex) — commit fc83a1c (9909 GT + 922 NR / 10831)
- [x] Goal 1 verifier exits 0 (independent re-run by human) — commit 59fb681 patched C9 accession_8k false-positive
- [x] Goal 1.5 executed via /goal (Codex prepares packets) — commit f2a0eb6 (200 stratified packets)
- [x] Goal 1.5 verifier exits 0 (packet structural check)
- [x] Goal 1.5 human audit complete — commit 04789af (199/200 ok, 0 wrong, 1 unclear; <5% threshold met)
- [x] Goal 2 prompt finalized (`.claude/plans/goal_2_prompt.md`)
- [x] Goal 2 verifier hand-written (`earnings-analysis/canary/quarter_resolver/verify_shadow_validator.py`) — commits b909a3f / 0813df2 / 72a7668 / dea1ef5; default mode = FULL 10,831-row re-derivation, --fast = stratified iteration shortcut (FCX-shape exhaustive + GT/other-NR stride)
- [x] Goal 2 executed via /goal (Codex) — completed 2026-05-05; deliverables ready for commit
- [x] Goal 2 verifier exits 0 in default (full) mode — Codex's run + Claude's independent --fast re-confirmation both pass
- [x] Goal 2 trustworthiness audit (14 checks) passed — no production-code modifications, corpus byte-identical to fc83a1c, all 3 verifiers git-clean, every report number re-derived from CSVs
- [x] Goal 3 reframed (2026-05-05) — north star locked at ≥99.9% live-fire rate; empirical 8-K periodOfReport probe confirmed Tier B (8-K periodOfReport → fiscal_math) is dead because periodOfReport=filing date, not fiscal quarter end
- [x] Goal 3 prompt finalized (`.claude/plans/goal_3_prompt.md`) — committed 0ae4d0e
- [x] Goal 3 verifier hand-written (`earnings-analysis/canary/quarter_resolver/verify_live_mode_resolver.py`) — committed 0ae4d0e
- [x] Goal 3 prompt + verifier reviewed by user, committed to git
- [x] Goal 3 executed via /goal — verifier exited 0; artifacts: `live_candidates.py`, `live_mode_audit.csv`, `LIVE_MODE_REPORT.md`
- [x] Goal 3 trustworthiness audit — CSV metrics independently re-derived; protected verifier/corpus files clean; production code not modified by Goal 3
- [x] Goal 3 follow-up empirical analysis (2026-05-06) — warm-start hypothesis CONFIRMED:
      - Full-corpus fire rate **91.03%** is inflated by **838 cold-start rows** (834 are 2023 — DB history starts there; 3 in 2024, 1 in 2025, 0 in 2026)
      - **Warm-start fire rate: 98.67%** (9,860 / 9,993 rows where prior periodic existed at PIT)
      - **Latest-per-ticker fire rate: 97.95%** (765 / 781 unique tickers' most-recent 8-Ks)
      - Year-cohort warm-start rates: 2023=98.94%, 2024=98.79%, 2025=98.50%, 2026=98.16% — stable
      - Production today **verified-wrong rate: 4.54%** (492/10,831 WRONG_AUTO_WROTE); another 3.97% AUTO_ON_UNCERTAIN_ROW (uncertain class, not measurably wrong)
      - Warm-start residuals (133 rows): 115 × 52/53-week + 9 × long-gap + 9 × denylisted-prior
      - Latest-per-ticker residuals (16 rows): 14 × 52/53-week + 2 × long-gap (DLR, PHM)
      - Recommended Goal 4 Scope 2 = `prior_periodic_projection` + 52/53-week handling + long-gap/denylist guard + orchestrator write-guard. Projected ~99.8% live-fire rate (UNPROVEN until Goal 4 verifier confirms; per ChatGPT correction, do not claim 99.9% as fact yet)
      - D8 (EX-99.1 parsing) NOT revisited — not needed if Scope 2 hits projected rate
- [x] Goal 4 (implementation) prompt + verifier finalized — committed fb03a9e (Rule F substitution into Goal 3 byte-faithful port; 7 rounds of ChatGPT critique applied: scope clarification, full-corpus G7, write-guard pytest enforcement, ban ticker tables, _effective_fye preservation, etc.)
- [x] Goal 4 executed via Codex /goal — production code committed e43cfc8 (~52 min wall time; modified scripts/earnings/quarter_identity.py + earnings_orchestrator.py + test_quarter_identity.py only)
- [x] Goal 4 verifier exits 0 in canonical FULL mode — G5 (115 → 94/0/21), G6 (FCX → Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1), G7 (9,116 OK / 0 WRONG / 827 FC on 9,943 oracle rows), G7b (9,860/9,860 firing rows preserved), G8/G9 pytest passes
- [x] Goal 4 trustworthiness audit (8 checks) — production scope clean, _STALE_MATCH_DAYS=150 removed, all 14 expected source strings present, _effective_fye_month preserved, no ticker tables, write-guard wired into orchestrator main flow, FCX direct test confirms Q1_FY2026 / AUTO_OK
- [x] FCX end-to-end smoke test under new resolver — 2026-05-06: pipeline writes Q1_FY2026/context_bundle.json (correct directory); Q4_FY2025/ NOT touched (the bug-corrupted directory from before Goal 4 remains as evidence of what the bug DID; can be cleaned separately)
- [x] FCX canary re-validation (all 14 historical events) — 2026-05-06: 10/14 match prior labels; 1 fail-closed (Q4_FY2022 cold-start, oldest event); 3 "mismatches" all CORRECTIONS of OLD buggy labels in event.json (Q4_FY2023→Q4_FY2024, two unlabeled bug-victim events now resolve correctly). Zero regressions.
- [x] Goal 6a measurement-only benchmark — Candidate D meets ship bar: warm-start 96.08% correct / 0.24% wrong / 3.67% fail-closed; latest-per-ticker 95.65% correct / 0.38% wrong / 3.97% fail-closed; `DECISION_FLAG_SHIP_D_DIRECTLY = yes`.
- [x] Goal 6c production implementation — Candidate D ported to `quarter_identity.py`, verifier passed, committed/pushed (`a61636a`; wording cleanup `2f61810`). Production scope: `quarter_identity.py` + tests only; fiscal_math/guidance/orchestrator locked.
- [x] Goal 6e guidance fallback hardening — `harvest_guidance_sessions.py` 10-Q/10-K NULL fiscal-label fallback now uses own-filing XBRL with denylist/proximity/triple-check before math fallback; tests 61/61 passed; committed/pushed (`be4c2cc`).
- [x] 34-edge-ticker SEC audit complete — 408 rows / 34 tickers; Tier A+B coverage 400/408; Rule G2 rejected as not shippable because it creates 37-39 new wrong AUTO_OK rows.
- [x] Goal 6f prompt + verifier committed/pushed (`74dfe6d`) — research-only structural discovery beyond D; requires failure model first; no production changes.
- [x] Goal 6f execution / review (2026-05-07) — verifier exited 0; commit `0552fd9` registered 5 immutable audit-evidence inputs. `DECISION_FLAG_GOAL6F_RECOMMENDATION = KEEP_D`. All 4 new structural candidates rejected: `MULTI_PRIOR_STABLE_OFFSET` (+17 new wrongs / 158 recoveries), `PERIOD_END_SHAPE_GATE` (+39 new wrongs), `CURRENT_8K_OWN_XBRL` (no-op — feature pipeline lacks current-8K DEI facts), `ADVANCE_RESULT_AGREEMENT` (no-op — zero edge convergences). G2 baselines also re-rejected (+37 / +39 new wrongs). D was the empirical ceiling under the old no-issuer-bucket lock.
- [x] Goal 6g final production override — committed/pushed `237f53c`; 18 audited issuers in `TRUST_XBRL_ADVANCE`; 182 rows flip `FAIL_CLOSED -> AUTO_OK_CORRECT`; zero new wrongs; final warm-start `97.92% correct / 0.24% wrong / 1.83% fail-closed`; latest-per-ticker `97.82% correct / 0.38% wrong / 1.79% fail-closed`.
- [x] Durable truth corpus preserved in `data/quarter_identity_ground_truth.csv` — canary artifacts can be removed after this doc consolidation.
- [ ] Production deploy + post-deploy monitor for Goal 6c + 6e + 6g.

---

## Conversation log (append as we iterate)

- 2026-05-05 14:23 — file created (0 bytes)
- 2026-05-05 ~14:25 — populated with ChatGPT-style structure (Why / Ground Truth Hierarchy / Goal breakdown / Working Hypothesis / Open Questions)
- 2026-05-05 14:30+ — Claude appended /goal research synthesis, verification-script independence principle, "100% precision" answer, risks log, open decisions, prompt template, master status tracker. Reconciled Tier 1 (string parsing) with user's earlier veto.
- 2026-05-05 — Decisions D1-D8 LOCKED. Goal 1 verifier hand-written + committed. Goal 1 fired via /goal; Codex hit C9 false-positive on accession_8k (Codex correctly flagged WITHOUT modifying verifier — verifier-clean confirmed). Claude patched verifier (commit 59fb681), Codex resumed, Goal 1 passed verifier (commit fc83a1c).
- 2026-05-05 — Goal 1.5 prompt + verifier hand-written + committed. Goal 1.5 packets built via /goal (commit f2a0eb6). 6 parallel Claude subagents audited 200 SEC EDGAR packets; final verdict 199 ok / 0 wrong / 1 unclear (RH 4.02 restatement, sampling-eligibility edge). Goal 1.5 PASS, evidence committed (04789af).
- 2026-05-05 — Goal 2 prompt + verifier hand-written through 5 rounds of ChatGPT critique (each independently re-evaluated by Claude per feedback rule):
    R6: 5 critical defects fixed — S6b dead code, undefined candidate verdict helpers, recommended-name not validated, 30-row random sample → stratified, S10 vs S10b clarification.
    R7: NR fail-closed scoring fixed — was always returning AUTO_ON_UNCERTAIN_ROW because qv==NO_RESOLUTION is dead on NR (qv always N_A); now keys on blank prod_fy AND blank prod_q.
    R8: prompt aligned with verifier (NR fail-closed wording, sanitized-context-only, "or has gaps" removed since CSV has no gaps column).
    Final design decision: invert default — bare verifier = FULL 10,831-row re-derivation (canonical sign-off); `--fast` = stratified opt-in for Codex iteration only. Removes "verifier passed" ambiguity. Commits b909a3f → 0813df2 → 72a7668 → dea1ef5.
- 2026-05-05 — Goal 2 fired via /goal. Codex iterating on builder + deliverables. Builder script (`build_goal2_outputs.py`) being polished in-loop for progress observability — within Codex's allowed scratch zone, not modifying verifier or production code.
- 2026-05-06 — Goal 3 completed via /goal. `prior_periodic_projection` selected as best current candidate: full corpus 91.03% AUTO_OK / 0 WRONG_AUTO_WROTE; warm-start historical PIT 98.67% AUTO_OK / 0 wrong-writes; latest-per-ticker live-like 97.95% AUTO_OK / 0 wrong-writes. Residuals are concentrated: latest-per-ticker has 14 odd 52/53-week / odd fiscal-calendar failures and 2 long-gap failures. Conclusion: prior-periodic projection is the new core algorithm, but 99.9% is not proven yet; next step is Goal 4 design with write-guard and a focused 52/53-week residual probe/enhancement.
- 2026-05-06 — Goal 4 prompt + verifier hand-written through 7 rounds of ChatGPT critique (each independently re-evaluated by Claude per feedback rule):
    R1: long-gap threshold 200d → 150d (reverted silent change to match Goal 3 candidate line 185)
    R2: full-corpus G7 hard-lock added (was sample-only)
    R3: G9 actually runs `pytest -k write_guard` (was string-lint only)
    R4: G2 banned ticker-allowlist/denylist patterns (structural-only)
    R5: G2 requires ALL Rule F + Goal 3 sources, not just ≥4
    R6: pseudocode rewritten — Rule F replaces ONLY odd_52_53 branch; Goal 3 logic byte-preserved including _effective_fye_month + _effective_fye_from_prior_10k augmentation
    R7: G7b 9,860 firing rows preservation hard-lock (catches silent coverage shrink); FCX G6 expects calendar-shaped source `prior_periodic_projection_q4_to_q1` (not Rule F)
    Empirical Rule F probe (2026-05-06) on 115 odd_52_53 + 34 SEC-audited NR rows: 94 OK / 0 WRONG / 21 FAIL_CLOSED.
- 2026-05-06 — 52/53 candidate-rule matrix probe: tested rules A-E; only Rule F (D + FY-disagreement guard) gave 0 WRONG. SEC-audit found PEP/LEVI same-event pattern (10-Q filed minutes before 8-K → use prior label directly, no advance) + KR/NTAP/SYNA naming-convention class (XBRL FY ≠ math FY → fail closed). Empirical taxonomy: ~25 verified-safe 52/53 tickers + AAP/PSTG GT-mismatch denylist + ACI/LEVI/PEP/PLAY NR-only.
- 2026-05-06 — Goal 4 fired via Codex /goal. Codex ported Goal 3 _prior_periodic_projection byte-faithfully into scripts/earnings/quarter_identity.py with Rule F substitution; added orchestrator destructive-write guard; 12 pytest cases pass; canonical full verifier exited 0 (after temporary stash of unrelated dirty paths compare_section.py + snapshot_xbrl_in_flight.py). Production commit e43cfc8.
- 2026-05-06 — FCX end-to-end smoke + canary re-validation passed under new resolver. The FCX bug is fixed: 0000831259-26-000021 returns Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1.
- 2026-05-07 — Goal 6a measured Candidate D: warm-start 96.08% correct / 0.24% wrong / 3.67% fail-closed; latest-per-ticker 95.65% correct / 0.38% wrong / 3.97% fail-closed. Goal 6c shipped D to production (`a61636a`, cleanup `2f61810`).
- 2026-05-07 — Goal 6e shipped guidance 10-Q/10-K rare fallback hardening (`be4c2cc`): own-filing XBRL can override math only with denylist + proximity + triple-check guard. This does not merge guidance target-period extraction with earnings 8-K resolver.
- 2026-05-07 — 34-edge-ticker SEC audit completed: G2 XBRL-trust variants are promising but not shippable due to 37-39 new wrong AUTO_OK rows on Tier A+B evidence. Goal 6f prompt/verifier committed/pushed (`74dfe6d`) to force failure-model-first structural research. `KEEP_D` is an acceptable verified outcome.
- 2026-05-07 — Goal 6f Codex run completed in 1668s; verifier exited 0; commit `0552fd9` registered 5 immutable audit-evidence files (`DECISION_FLAG.md`, `advance_xbrl_simulation.csv`, `adversarial_review.json`, `master_truth.csv`, `validation_report.md`). 7 candidates tested (D + 2 G2 + 4 new structural); all 4 new candidates rejected. `DECISION_FLAG_GOAL6F_RECOMMENDATION = KEEP_D`. Closest near-miss `MULTI_PRIOR_STABLE_OFFSET` recovered 158 fail-closed Tier A/B rows but added 17 new wrongs — fails the zero-new-wrong policy. PHR/PINC/PRU latest-per-ticker wrong-fires (3 rows) classified as irreducible without current-event text or current-8K DEI facts.
- 2026-05-07 — Goal 6g shipped final audited-issuer override (`237f53c`, pushed): 18 issuers in `TRUST_XBRL_ADVANCE`, uniform issuer-level rule only, 182 rows recovered from fail-closed to correct AUTO_OK, zero new wrongs. Final metrics from `goal6g_baseline.csv`: warm-start 9,673/24/181 = 97.92% correct / 0.24% wrong / 1.83% fail-closed; latest-per-ticker 764/3/14 = 97.82% correct / 0.38% wrong / 1.79% fail-closed.
- 2026-05-07 — Cleanup decision: preserve `data/quarter_identity_ground_truth.csv` as the durable corpus, keep production resolver/tests/shared helpers, and remove old canary/verifier/goal-prompt scaffolding. This file now absorbs the non-duplicate context from `restore-context.md` and `refactor-safety-contract.md`.
- Next step: production deploy of Goal 6c+6e+6g to k8s services; cleanup old canary/prompt docs after this consolidated context is committed.
