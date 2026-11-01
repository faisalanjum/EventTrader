# EventMarketDB Learner Loop - Simplified Quality Design

Status: final design accepted
Round: 2
Last updated: 2026-05-11

Design-only guardrail: this notebook is the only repository file this goal may change. No production code, production corpus JSON, skills, or `earnings-analysis/` files are edited by this goal.

## 0. Current Coded Baseline vs Round 10 Design vs Simplified Target

This plan compares three different things and keeps them separate:

- Current coded baseline: the Python, skills, and JSON corpus on disk today.
- Round 10 baseline: the accepted design in `.claude/plans/LearnerLoopPlan.md`, not implemented production behavior.
- Simplified-quality target: this plan's future implementation design.

Current coded baseline, verified from file reads:

- `build_prediction_bundle` runs seven builders, stamps `schema_version`, `ticker`, `quarter_info`, `pit_cutoff`, and `assembled_at`, then adds `learning_context`. A non-assertion learning-context failure becomes empty lessons with a warning, which can mimic first-prediction state. Evidence: `scripts/earnings/earnings_orchestrator.py:196`, `scripts/earnings/earnings_orchestrator.py:241`, `scripts/earnings/earnings_orchestrator.py:258`, `scripts/earnings/earnings_orchestrator.py:269`.
- Prediction validation is `prediction_result.v1`. It requires `lesson_labels`, body-position matching, confirmed-only citations, and source-id grounding, but it only reserves `"no relevant evidence"` away from confirmed/contradicted labels and does not reject an all-irrelevant all-sentinel batch. Evidence: `scripts/earnings/earnings_orchestrator.py:658`, `scripts/earnings/earnings_orchestrator.py:701`, `scripts/earnings/earnings_orchestrator.py:755`, `scripts/earnings/earnings_orchestrator.py:775`, `scripts/earnings/earnings_orchestrator.py:796`, `scripts/earnings/earnings_orchestrator.py:853`.
- The predictor skill tells the model to test `applies_when` and `invalid_if`, cite confirmed lessons, and choose `no_call` when evidence does not support a call; that semantic discipline is stronger in prompt than in validator. Evidence: `.claude/skills/earnings-prediction/SKILL.md:81`, `.claude/skills/earnings-prediction/SKILL.md:99`, `.claude/skills/earnings-prediction/SKILL.md:106`, `.claude/skills/earnings-prediction/SKILL.md:213`, `.claude/skills/earnings-prediction/SKILL.md:227`.
- Learner PIT uses next-quarter filed time, live-cycle filed time, then current invocation time. Tier 3 is non-replayable for new historical mutations. Evidence: `scripts/earnings/earnings_orchestrator.py:938`, `scripts/earnings/earnings_orchestrator.py:965`, `scripts/earnings/earnings_orchestrator.py:972`, `scripts/earnings/earnings_orchestrator.py:983`.
- Learner execution gates on `prediction/result.json`, can recover from existing `learning/result.json`, validates schema and cross-file audit parity, then appends ticker/global lessons and aggregates audits. It does not create a sealed manifest or quality ledger. Evidence: `scripts/earnings/earnings_orchestrator.py:1133`, `scripts/earnings/earnings_orchestrator.py:1199`, `scripts/earnings/earnings_orchestrator.py:1205`, `scripts/earnings/earnings_orchestrator.py:1333`, `scripts/earnings/earnings_orchestrator.py:1398`, `scripts/earnings/earnings_orchestrator.py:1415`.
- Prediction result finalization is atomic. Learning result finalization rewrites JSON with `Path.write_text`, then renders/harvests sidecars best-effort. Evidence: `scripts/earnings/earnings_orchestrator.py:3420`, `scripts/earnings/earnings_orchestrator.py:3462`, `scripts/earnings/earnings_orchestrator.py:3477`, `scripts/earnings/earnings_orchestrator.py:3534`.
- Ticker lesson append is atomic but explicitly assumes no lock. Global append uses `fcntl.flock`, but D22 collision checks run before that lock. Evidence: `scripts/earnings/earnings_orchestrator.py:1487`, `scripts/earnings/earnings_orchestrator.py:1499`, `scripts/earnings/earnings_orchestrator.py:1559`, `scripts/earnings/earnings_orchestrator.py:1563`, `scripts/earnings/earnings_orchestrator.py:1658`, `scripts/earnings/earnings_orchestrator.py:1663`.
- Lesson IDs are deterministic `lsn_` hashes. Status is transient render state over PIT-visible audits: retire/refine or misled thresholds retire/watch; otherwise active. Evidence: `scripts/earnings/earnings_orchestrator.py:1817`, `scripts/earnings/earnings_orchestrator.py:1900`, `scripts/earnings/earnings_orchestrator.py:1937`, `scripts/earnings/earnings_orchestrator.py:1945`.
- `build_learning_context` filters by `source_pit_cutoff`, applies same-quarter self-leak guard, filters audit PIT, drops retired lessons, sorts by recency, and caps ticker/global lessons. Evidence: `scripts/earnings/earnings_orchestrator.py:2101`, `scripts/earnings/earnings_orchestrator.py:2159`, `scripts/earnings/earnings_orchestrator.py:2202`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2236`, `scripts/earnings/earnings_orchestrator.py:2352`.
- Renderer L numbering is centralized through `iter_labeled_lessons`; ordered lesson text contains the body only, excluding marker and decoration. Evidence: `scripts/earnings/_text_utils.py:29`, `scripts/earnings/_text_utils.py:35`, `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:209`, `scripts/earnings/renderer/lessons.py:214`.
- Learning validation is v3-only and already enforces structured lesson fields, non-empty resolving evidence refs, scope routing shape, and audit shape. It does not require transfer proof, root-cause enum, sharp audit semantics, or a replay-quality artifact. Evidence: `scripts/earnings/validate_learning.py:1`, `scripts/earnings/validate_learning.py:70`, `scripts/earnings/validate_learning.py:114`, `scripts/earnings/validate_learning.py:322`, `scripts/earnings/validate_learning.py:459`, `scripts/earnings/validate_learning.py:542`.
- Cross-file learner validation enforces audit count, index, label, citation, and lesson-text parity against prediction and bundle. Evidence: `scripts/earnings/earnings_orchestrator.py:2968`, `scripts/earnings/earnings_orchestrator.py:2993`, `scripts/earnings/earnings_orchestrator.py:3003`, `scripts/earnings/earnings_orchestrator.py:3019`.

Current FCX corpus evidence:

- Q3 prediction had no lesson labels and no lesson citations; Q3 learning is `attribution_result.v3`, PIT `next_quarter`, actual daily return `0.97`, two ticker lessons, three data lessons, one sector global lesson, and no prior lesson audit. Evidence: `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json:1`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:1`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:10`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:198`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:245`.
- `earnings-analysis/Companies/FCX/events/Q4_FY2025/` currently has only `context_bundle.json`, `context_bundle_rendered.txt`, `related_filings/0000831259-25-000052.md`, and `related_filings/0000831259-26-000002.md`. There is no Q4 prediction or learning source artifact on disk.
- Despite missing Q4 prediction/learning artifacts, `earnings-analysis/learnings/ticker/FCX.json` has a Q4 row with two ticker lessons, and `earnings-analysis/learnings/global.json` has a Q4 sector lesson. Evidence: `earnings-analysis/learnings/ticker/FCX.json:100`, `earnings-analysis/learnings/ticker/FCX.json:119`, `earnings-analysis/learnings/global.json:48`, `earnings-analysis/learnings/global.json:64`.
- Q3 lessons carry Q4 audit entries whose source Q4 learner artifact is absent. Evidence: `earnings-analysis/learnings/ticker/FCX.json:41`, `earnings-analysis/learnings/ticker/FCX.json:73`, `earnings-analysis/learnings/global.json:26`.
- Q1 saved bundle includes Q4 lessons and an allowed Q4 learner path even though that markdown does not exist now. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5477`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5545`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5650`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5729`.
- Q1 prediction labeled all six lessons irrelevant, used the exact sentinel for each, cited none, and still made a directional short call at confidence 48. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:1`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:40`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:172`.

Round 10 design baseline, not implemented:

- Proposed prediction v2 engagement evidence, learner v4 verified audits/root causes, verified lesson tiers, provenance bool, `learning/mutation_manifest.json`, prediction hash metadata, deterministic replay/reconcile, provenance quarantine file, PIT refusal, transfer basis, merged local report, and a broad lock/replay/drift-block system. Evidence: `.claude/plans/LearnerLoopPlan.md:251`, `.claude/plans/LearnerLoopPlan.md:259`, `.claude/plans/LearnerLoopPlan.md:271`, `.claude/plans/LearnerLoopPlan.md:292`, `.claude/plans/LearnerLoopPlan.md:312`, `.claude/plans/LearnerLoopPlan.md:383`, `.claude/plans/LearnerLoopPlan.md:390`.
- Round 10 converged with four judge accepts for the reliability-only design objective, but explicitly did not guarantee correct market calls or repair the Q4 FCX missing artifacts. Evidence: `.claude/plans/LearnerLoopPlan.md:695`, `.claude/plans/LearnerLoopPlan.md:702`, `.claude/plans/LearnerLoopPlan.md:724`.

Simplified-quality target:

- Keep the current Python/JSON architecture.
- Keep PIT filtering, self-leak guard, D20 body matching, D19 audit parity, source-id grounding, structured lesson fields, deterministic lesson IDs, atomic JSON writes, and local file locks where needed.
- Replace Round 10's manifest plus drift-block/head plus quarantine chain with one sealed per-event `learning/quality_event.json`.
- Detect missing source provenance dynamically from source artifact presence and event-quality ledgers; do not add a durable quarantine chain for v0. Missing-source rows are capped at `unproven` and excluded from quality credit until source artifacts are restored.
- Add the smallest prediction-quality stack: rolling Brier score as the primary metric, plus guardrails for accuracy, no_call discipline, citation precision, continual-learning trend, and bounded blast radius.
- Compute metrics and replay checks with one local script, future `scripts/earnings/learning_metrics.py`, instead of storing per-lesson stats or report state.

## 1. Round 10 Baseline

Round 10 is valuable as a failure-mode inventory and accepted reliability design, not as production reality. Its core mechanisms:

- Prediction v2: engagement reason/source IDs, key-driver source IDs, context-bundle hash, rendered learning-context hash, lesson-set hash.
- Learner v4: root causes, verified audit gates, refinement links, transfer proof.
- Lesson tiers: proven, promising, unproven, risky, retired.
- Provenance model: `_render_provenance_complete` plus replay/report reason derivation.
- Mutation closure: `learning/mutation_manifest.json` as completion sentinel.
- Replay system: event replay, full-library replay, replay-wide shared/exclusive lock, drift-block append file, drift-head anchor.
- Recovery controls: failed-unsealed manifests, no-manifest recovery refusal, quarantine file with active/resolved chain-head semantics.
- Reports: merged health/data/replay report.
- Locking: replay-wide lock, event lock, ticker locks, global lock, drift-block lock, quarantine lock.

The design is strong but over-rotated for a local JSON learner loop. It protects against deep corruption and tamper cases, but it creates persistent state mostly to protect other persistent state.

## 2. What Round 10 Got Right

Round 10 correctly identified the reliability properties that must survive simplification:

- Replayability: derived libraries must be reconstructable or visibly unreconstructable.
- PIT discipline: no lesson can become visible before it could have been learned.
- Idempotency: reruns must not duplicate rows or audits.
- Engagement evidence: the predictor cannot lazily wave away all lessons without testable rationale.
- Quality differentiation: lesson visibility must depend on verified performance, not only recency.
- Scope justification: global routing needs proof, not vibes.
- Recovery: partial writes must not be mistaken for complete learning.
- Observability: quality and failure modes must be measurable.
- Bounded blast radius: one lesson or near-clone cluster must not dominate misleading outcomes.
- Minimalism: stay in local Python and JSON; no service, DB, daemon, dashboard, trade system, or synthetic hindsight.

It also correctly centered the live FCX Q4 defect: library rows can survive without the source artifacts that should justify them.

## 3. What Round 10 Overcomplicated

Round 10 overcomplicated v0 in these places:

- Separate mutation manifest: useful, but its useful parts can be merged with prediction/lesson-quality metrics into a single per-event quality ledger.
- Replay drift block plus head anchor: robust against local tampering, but heavyweight. For v0, recompute replay/provenance health on every quality gate and refuse if unhealthy. Do not persist global drift state.
- Quarantine ledger chain/supersession: powerful but unnecessary if v0 uses the stricter rule that missing-source rows never earn quality credit and cannot become proven until source artifacts are restored.
- Replay-wide locks: not needed if full-library replay is a local check outside event mutation, and event mutation only needs same-event/ticker/global serialization.
- Renderer environment/version stamping: too broad. V0 stores `rendered_learning_context_sha256` over the exact prior-lessons text the predictor saw plus a semantic `lesson_set_sha256` over ordered lesson bodies and source IDs. This catches renderer drift without persisting Python/locale/timezone fingerprints.
- Multiple storage-row schema bumps: avoid. Compute per-lesson stats dynamically from event ledgers/audits; do not add durable row stats.
- Report/replay split: collapse into one local `learning_metrics.py`.
- Persistent per-lesson stats: avoid. They are derivable from event ledgers and audit histories.

Simplification does weaken protection against malicious local rollback of both source artifacts and ledgers. That residual risk is acceptable for v0 because EventMarketDB is a local file workflow, not a multi-tenant ledger. The design still catches ordinary Q4-style provenance gaps, replay drift from missing artifacts, lazy sentinel behavior, and bad-lesson pollution.

## 4. Complexity Budget Ledger

Weights:

- Durable artifact type = 4
- Lock/concurrency primitive = 4
- Schema version or major schema field group = 3
- Validator surface = 3
- Script/tool = 3
- Persistent state/status enum = 2
- Prompt-only rule = 1

Ledger 1 - Design Simplification, Round 10 vs simplified target:

| Category | Round 10 weighted items | Round 10 score | Simplified weighted items | Simplified score |
|---|---:|---:|---:|---:|
| Durable artifact types | mutation manifest, replay drift block, replay drift head, provenance quarantine, report output convention | 20 | `learning/quality_event.json` only; reports are generated to stdout or `/tmp` by default | 4 |
| Locks/concurrency primitives | replay-wide lock, event lock, ticker locks, global lock, drift-block lock, quarantine lock | 24 | event `.learning.lock`, ticker locks, global lock | 12 |
| Schema/major field groups | prediction v2, learner v4, manifest v1, drift-block schema, quarantine schema, row schema bumps, renderer environment version | 21 | prediction engagement/hash v2, learner audit-quality/refinement v4, quality event v1, metrics output schema | 12 |
| Validator surfaces | prediction engagement, learner audit/root cause, manifest, drift block, quarantine, replay, transfer proof, renderer version | 24 | prediction engagement, learner audit/root cause, quality event, dynamic provenance check, metrics/replay checks | 15 |
| Scripts/tools | `learning_replay.py`, `learning_report.py` | 6 | one `learning_metrics.py` with `--replay-check`, `--quality-report`, `--tournament` | 3 |
| Persistent state/status enums | manifest status, quarantine status/action, drift block state, root cause, tier, engagement reason | 12 | quality event status, root cause, tier, engagement reason | 8 |
| Prompt-only rules | engagement, root-cause discipline, transfer, calibration/no_call | 4 | causal-chain lesson rule, counter-thesis, calibration/no_call discipline | 3 |
| Total | | 111 | | 57 |

Ledger 1 verdict: material simplification. The target cuts 54 weighted points, mostly by replacing three persistent reliability artifacts and two artifact-protection mechanisms with one event ledger plus recomputed health.

Ledger 2 - Implementation Cost, current coded behavior vs simplified target:

| Change | Class | Evidence for current surface | Why needed |
|---|---|---|---|
| Keep PIT lesson filtering and same-quarter guard | ALREADY-CODED | `scripts/earnings/earnings_orchestrator.py:2159`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2300` | Preserves PIT discipline and self-leak prevention. |
| Keep D20 body-only positional lesson matching | ALREADY-CODED | `scripts/earnings/_text_utils.py:29`, `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:214`, `scripts/earnings/earnings_orchestrator.py:782` | Prevents renderer/validator drift and lesson-label spoofing. |
| Keep source-id grounding for prediction evidence ledger | ALREADY-CODED | `scripts/earnings/earnings_orchestrator.py:277`, `scripts/earnings/earnings_orchestrator.py:853` | Preserves citation provenance. |
| Keep structured learner lessons with mechanism/applies_when/invalid_if/evidence_refs | ALREADY-CODED | `scripts/earnings/validate_learning.py:459`, `scripts/earnings/validate_learning.py:501`, `.claude/skills/earnings-learner/SKILL.md:82` | Already enforces much of lesson-quality shape. |
| Extend prediction validation with engagement reason/source IDs, `key_drivers[].evidence_source_ids`, and all-sentinel/no_call discipline | PARTIAL | Existing validator at `scripts/earnings/earnings_orchestrator.py:658`; current key-driver citation shape at `scripts/earnings/earnings_orchestrator.py:796`; current sentinel limitation at `scripts/earnings/earnings_orchestrator.py:775`; Q1 failure at `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8` | Closes lazy predictor failure and makes strong non-lesson evidence mechanically checkable. |
| Stamp `context_bundle_sha256`, `rendered_learning_context_sha256`, and `lesson_set_sha256` in prediction result | PARTIAL | Prediction finalizer exists and writes metadata atomically at `scripts/earnings/earnings_orchestrator.py:3477`, `scripts/earnings/earnings_orchestrator.py:3509`, `scripts/earnings/earnings_orchestrator.py:3534` | Enables replay/provenance and rendered-context drift detection without renderer environment stamping. |
| Extend learner audit with root cause and verified-help/misled compatibility | PARTIAL | Existing audit shape at `scripts/earnings/validate_learning.py:542`; existing audit aggregation at `scripts/earnings/earnings_orchestrator.py:2767` | Makes lesson quality and citation precision measurable. |
| Dynamic provenance cap in `build_learning_context` | PARTIAL | Current learner-path decoration already checks sidecar existence at `scripts/earnings/earnings_orchestrator.py:2030`; Q4 missing source proves need | Prevents Q4-style rows from rendering as normal trusted memory. |
| Replace recency-first ranking with quality tier before caps | PARTIAL | Current recency sort at `scripts/earnings/earnings_orchestrator.py:2207`, `scripts/earnings/earnings_orchestrator.py:2352`; status helper exists at `scripts/earnings/earnings_orchestrator.py:1900` | Makes better lessons more likely to influence predictions. |
| Add ticker file locks and move D22 scans inside locks | PARTIAL | Atomic write exists at `scripts/earnings/earnings_orchestrator.py:1444`; ticker append lacks lock at `scripts/earnings/earnings_orchestrator.py:1499`; global flock exists at `scripts/earnings/earnings_orchestrator.py:1663` | Preserves idempotency/concurrency without replay-wide locks. |
| Use `_atomic_write_json` in `finalize_learning_result` | PARTIAL | Current learning finalizer uses `write_text` at `scripts/earnings/earnings_orchestrator.py:3462`; atomic helper exists at `scripts/earnings/earnings_orchestrator.py:1444` | Removes partial result write risk. |
| Add sealed `learning/quality_event.json` | NET-NEW | No current manifest/ledger exists; recovery only replays existing `learning/result.json` at `scripts/earnings/earnings_orchestrator.py:1205` | Replaces Round 10 manifest and provides metric inputs. |
| Add `scripts/earnings/learning_metrics.py` | NET-NEW | No current rolling metric/replay-quality script found in current file list | Provides Brier/ECE/no_call/citation/velocity/replay tournament measurement. |
| Add frozen replay tournament mode | NET-NEW | Current A/B scripts exist but no quality tournament for lessons was verified in this read | Needed to measure predictor usefulness without mutating production. |

Ledger 2 verdict: implementation cost is net-positive but bounded. The net-new pieces are one event artifact and one local tool. They directly close named failures and provide measurable lesson/prediction quality; the rest extends existing validators/finalizers/read paths.

## 5. Simplified Target Architecture

Principle: one source artifact per completed learning event should answer three questions:

- What did the predictor commit to?
- What did the learner decide after the outcome?
- What should future metrics/replay trust?

Target components:

1. Prediction result v2, small engagement extension.
   - Add per-label `engagement_reason` enum: `condition_met`, `opposite_evidence`, `missing_precondition`, `invalid_if_triggered`, `not_testable_no_bundle_signal`.
   - Add per-label `engagement_source_ids`.
   - Add `key_drivers[].evidence_source_ids` as a deterministic source-ID list separate from free-text `evidence`. Existing `cites_lesson_indices` remains only for prior-lesson citation.
   - Require `condition_met` and `opposite_evidence` to cite resolving source IDs from `evidence_source_catalog`, and those IDs must be non-S10 current-bundle evidence. A prior lesson source ID such as `#S10.lesson.L1` cannot prove that the current bundle condition is present.
   - Require `invalid_if_triggered` to name the invalidating condition in `bundle_evidence` and cite at least one non-S10 source ID showing the trigger. `missing_precondition` names the missing condition and uses empty source IDs unless a specific non-S10 absence marker exists. `not_testable_no_bundle_signal` uses empty source IDs and is treated as a data-coverage warning.
   - In every all-irrelevant/not-testable batch, `confidence_score <= 35` is mandatory. `direction` may be non-`no_call` only when at least two `key_drivers[]` carry non-empty, resolving, non-S10 `evidence_source_ids`; otherwise direction must be `no_call`. This exception is mechanical; free-text evidence or prose analysis never qualifies.
   - The two qualifying key drivers must cite at least two distinct non-S10 `evidence_source_catalog` IDs, not duplicate references to one source ID. A future hardening can require distinct bundle sections, but v0 enforces distinct IDs.
   - Stamp `context_bundle_sha256`, `rendered_learning_context_sha256`, and `lesson_set_sha256`. The rendered hash covers the exact prior-lessons learning-context text the predictor receives, including headers and tier/provenance markers. The lesson-set hash covers ordered lesson bodies plus their `evidence_source_catalog` source IDs. This replaces Round 10 renderer environment stamping while preserving lesson-section renderer-drift detection.
   - Accepted v0 trade-off: rendered drift outside the prior-lessons learning-context block is not separately hashed. It is covered only indirectly by `context_bundle_sha256` over JSON inputs plus existing renderer tests; this plan intentionally avoids Round 10's full renderer environment fingerprint.

2. Learner result v4, small audit-quality extension.
   - Add `root_cause` to each audit: `correct_nonapplication`, `lesson_helped`, `lesson_misled`, `lesson_good_ignored`, `data_missing`, `outcome_noise`.
   - A helped/misled/missed audit only counts as verified when evidence refs resolve, comment passes the anti-sentinel floor, and root-cause/review/action compatibility holds.
   - `outweighed` is an audit review meaning the lesson mechanism was real but other forces dominated the market outcome. It remains tracked separately and does not count as helped unless the learner verifies the lesson was directionally useful despite being outweighed.
   - Bare `retire` remains disallowed for LLM output in v0. Use `refine` or keep. Human removal is outside automated learner mutation.
   - Every `action=refine` audit must include `refined_to_lesson_id`; the same learner result must emit exactly one replacement lesson whose recomputed ID matches that value and whose `parent_id` equals the audited parent lesson ID. The validator recomputes expected IDs for parent and child and enforces the inverse relationship: every emitted replacement with `parent_id` must have exactly one same-run refine audit. A parent may be refined only if it has no prior PIT-visible refinement; the no-prior-refinement check is repeated inside the ticker/global write lock before append. This restores refinement lineage without adding a lineage artifact.
   - Transfer proof for global observations is required: `transfer_basis` and `transfer_evidence_refs`, scope-compatible and resolving. If proof is absent, lesson stays ticker-scope.

3. One sealed event-quality ledger.
   - Future path: `events/{quarter}/learning/quality_event.json`.
   - Status enum: `sealed` or `failed_recoverable`.
   - It is the sole completion sentinel for learning. No separate `mutation_manifest`, `complete.json`, drift block, drift head, or quarantine chain.
   - It is written with `_atomic_write_json` under the event `.learning.lock` only after the complete object validates. Only `status: sealed` counts as completion or provenance credit. Missing, unreadable, schema-invalid, hash-mismatched, or `failed_recoverable` ledgers force deterministic recovery or refusal.
   - It records event identity, prediction hash, context bundle hash, lesson-set hash, learner result hash, actual return snapshot, predicted direction/confidence/range, cited lesson IDs, engagement summaries, emitted lesson IDs, audit verdicts, required write outcomes, source artifact paths/hashes, and recovery notes.
   - `cited_lesson_ids` derive from confirmed `lesson_labels[]` that appear in `key_drivers[].cites_lesson_indices`; `emitted_lesson_ids` come from same-run learner `predictor_lessons[]` and `global_observations[]` after stamping.
   - Recovery and `learning_metrics.py --replay-check` verify every `emitted_lesson_id` recorded in a sealed quality event is present in the expected ticker/global library and that recorded audit verdicts match the expected audit history. Missing, renamed, or extra rows report as replay drift rather than silent acceptance.
   - It records metric primitives, not computed rolling metrics. Rolling metrics are derived by `learning_metrics.py`.
   - A rerun that sees sealed `quality_event.json` refuses normal mutation. There is no v0 override or `--force` path; sealed quality events are immutable except through deterministic recovery that proves the same source hashes. A rerun with `learning/result.json` but no sealed quality event enters deterministic recovery or refuses.
   - Deterministic recovery is deliberately narrow: validate the existing `learning/result.json` plus sibling prediction and bundle, verify `context_bundle_sha256`, `rendered_learning_context_sha256`, `lesson_set_sha256`, and learner-result hash against the prediction-stamped or recovery-computed values, re-run `append_ticker_lesson`, `append_global_lessons`, and audit aggregation under the event/ticker/global locks, then write sealed `quality_event.json` from those same source hashes. No new LLM run, no new artifact type, no extra convergence loop. Any hash mismatch or failed write produces `status: failed_recoverable` and refusal with `RECOVERY_REQUIRED`.

4. Dynamic provenance caps, no quarantine ledger in v0.
   - At render/build time, for each source lesson row, derive required source paths from `(source_ticker, quarter_label)`: context bundle, prediction result, learning result, and quality event.
   - Ticker-scope rows derive `source_ticker` from the ticker library filename when the lesson row itself lacks `source_ticker`; global rows use their stored `source_ticker`.
   - Provenance is complete only when the four canonical JSON artifacts exist: `context_bundle.json`, `prediction/result.json`, `learning/result.json`, and sealed `learning/quality_event.json`, and the hashes in `quality_event.json` match the source files. Human sidecars such as `learning/result.md` never count for provenance.
   - If required source artifacts are missing or hashes disagree, the lesson receives transient `_render_provenance_complete: false`, tier cap `unproven`, and zero quality-credit eligibility.
   - Missing-source audits do not count for tier, citation precision, or helped/misled stats. Implement `_audit_provenance_ok(audit, companies_dir)` and call it before tier/status or metrics code reads audit history. It resolves the auditor event's `learning/result.json` and sealed `quality_event.json`; miss, invalid ledger, or hash drift returns false.
   - Existing FCX Q4 rows therefore remain visible only as unproven/missing-provenance context until the source artifacts are restored. There is no manual whitelist artifact in v0.
   - Migration rule: existing valid legacy triples such as FCX Q3 can run a one-time deterministic backfill/recovery that reads `context_bundle.json`, `prediction/result.json`, and `learning/result.json`, validates the cross-file contract, replays required writes idempotently, and seals `quality_event.json`. Legacy rows without a sealed backfill stay unproven by design. FCX Q4 cannot be backfilled until missing prediction/learning artifacts are restored.
   - Legacy backfill hash preference: use a prediction-stamped rendered hash if present; otherwise use the saved `context_bundle_rendered.txt` prior-lessons slice as the best proxy for exact predictor input; only compute a current-render hash when the saved rendered text is unavailable, and then stamp `rendered_learning_context_recovery_computed: true`.
   - Provenance checking is per-call file existence plus hash comparison. If this becomes expensive, the only allowed optimization is an in-memory per-process cache keyed by `(source_ticker, quarter_label, file_mtime)`; no durable provenance cache.

5. Quality tiers before caps.
   - Replace render-status authority with tier authority: `proven`, `promising`, `unproven`, `risky`; retired/excluded lessons are dropped before caps.
   - Use the existing `LESSON_AUDIT_WINDOW = 5` for recent-window `promising`, `risky`, and retired/excluded decisions. Promotion to `proven` also checks full PIT-visible history since the latest validated refinement.
   - Audit key is exactly `(auditor_ticker, auditor_quarter_label)`. `proven`: provenance complete, at least two verified positives from distinct audit keys and two distinct future quarter labels, zero verified misled since latest refinement.
   - `promising`: one verified positive and no verified misled.
   - `risky`: any recent verified misled or repeated false confirmation.
   - `unproven`: legacy, neutral-only, missing provenance, or insufficient evidence.
   - Sort before caps by tier priority, then `source_pit_cutoff` descending, then deterministic source tuple. `attributed_at` is display metadata only.

6. One local metrics/replay tool.
   - Future script: `scripts/earnings/learning_metrics.py`.
   - Modes: `--quality-report`, `--replay-check`, `--tournament`.
   - Reads predictions, learning results, quality ledgers, bundles, and libraries. Writes reports to stdout or an explicit output path; no persistent state required.
   - Computes Brier, ECE, reliability bins, directional accuracy, no_call discipline, citation precision/coverage, per-lesson helped/misled, learning velocity, and blast-radius cluster metrics.

7. Minimal concurrency.
   - Keep same-event `.learning.lock`.
   - Add ticker file locks.
   - Keep global flock and move D22 checks inside the locked read-modify-write.
   - Lock order is always per-event `.learning.lock`, then ticker file locks acquired in alphabetical ticker-symbol order when multiple tickers are touched, then global flock. The alphabetical ticker-lock rule includes ticker locks acquired by audit aggregation for parent lessons stored in other ticker libraries, not only the current event's ticker append. Code must never acquire these in reverse order.
   - Do not add replay-wide, drift-block, or quarantine locks.

## 6. Lesson Quality Definition

A high-quality lesson is:

- Causal: setup -> expectation/anchor change -> participant response -> prediction implication.
- Future-verifiable from pre-event bundle evidence.
- Falsifiable through concrete `invalid_if` conditions.
- Decision-relevant for direction, confidence, or no_call.
- Evidence-backed with resolving refs directly tied to the mechanism.
- Scoped narrowly unless transfer proof exists.
- Non-obvious and non-generic.
- Not source-date/event-name specific.
- Reusable across genuinely similar future setups.
- Measurable after future outcomes.

Additional requirements:

- Bundle-detectable triggers: `applies_when` must name evidence the future bundle can detect.
- Sharp falsifiers: `invalid_if` must be concrete, not hedged.
- Direction/magnitude implication: the lesson clarifies whether it implies direction, material move, weak/no_call, or confidence adjustment.
- Correct scope: ticker/global promotion requires transfer evidence.
- Reuse proof: promotion depends on independent future usage, not birth-time plausibility.
- Not case-specific: source-only dates, one-off event names, and non-transferable details are rejected or capped.

## 7. Lesson Quality Enforcement

| Property | Enforcement |
|---|---|
| Causal mechanism | Existing deterministic length/field validator plus learner prompt; residual semantic risk remains. |
| Future-verifiable triggers | Prediction v2 engagement validator checks `engagement_reason` and source IDs; learner v4 audits verify later. |
| Sharp falsifiers | Prompt-only plus human review in report for vague `invalid_if`; deterministic length alone is not enough. |
| Decision relevance | Renderer contract and prediction validator require cited confirmed lessons to appear in key drivers; metrics report tracks cited lessons that helped/misled. |
| Evidence-backed | Existing deterministic evidence-ref validation in learner; prediction source-id grounding; quality event hash links. |
| Correct scope | Deterministic `transfer_basis`/`transfer_evidence_refs` validator for global observations. |
| Non-obvious/non-generic | Prompt-only plus report metric for generic phrase/near-clone flags; residual human review. |
| Not source-date/event-name specific | Prompt-only and report lint; deterministic validator can flag raw date/event-name patterns as warnings, not hard fail. |
| Reusable | Replay/report metric: citation coverage, reuse rate, time-to-first-helped. |
| Measurable | `quality_event.json` plus `learning_metrics.py` derive per-lesson helped/misled, citation precision, and blast radius. |
| Bundle-detectable applies_when | Prediction v2 engagement reason must map to bundle evidence or missing precondition; prompt-only for semantic truth. |
| Direction/magnitude implication | Learner skill requires implication; metrics infer from citation/call/no_call behavior; residual prompt-only risk. |
| Promotion proof | Deterministic tier logic over verified future audits; no birth-time promotion to proven. |

Residual risk: a model can still write plausible but semantically weak causal prose. The design does not pretend validators can solve that completely; it makes weak lessons measurable and prevents them from earning high trust without future evidence.

## 8. Prediction Quality Metrics

Primary metric:

- Rolling Brier score over completed events, recommended rolling 50 when enough data exists.
- For `long`/`short`, map `confidence_score / 100` to P(chosen_direction_correct). Binary outcome is 1 if chosen direction matches actual direction, else 0. Brier = `(p - outcome)^2`.
- `no_call` is scored separately under no_call discipline in v0. Every Brier table must show `call_count`, `no_call_count`, `total_completed_events`, no_call rate, and no_call usefulness beside Brier so abstention cannot make the primary metric look better by shrinking the scored call set. The design does not use multiclass Brier unless a later implementation explicitly defines no_call probabilities.

Guardrails and tolerances:

- Directional accuracy must not regress by more than 3 percentage points versus the current predictor over the same rolling window, unless Brier improves by at least 0.03 and no_call usefulness improves.
- no_call usefulness must not regress by more than 5 percentage points in avoided false-confidence events per no_call, measured against high-confidence wrong-call rate. High-confidence wrong means `confidence_score >= 70` and direction incorrect; the report may expose the threshold as a parameter, but 70 is the default gate.
- Citation precision must not regress by more than 5 percentage points. Default precision is `verified_helped / (verified_helped + verified_misled)`; outcome-noise/outweighed are tracked separately.
- Continual-learning trend must not regress: recent rolling 25 should not be worse than the prior comparable 25 by more than 0.03 Brier without an identified data/regime explanation.
- Bounded blast radius: no single lesson or near-clone cluster may account for more than 25% of verified misled cited outcomes in the rolling 50 window. A breach blocks prompt, tier-rule, or lesson-family promotion until the offending cluster is refined, capped, or excluded from promotion credit.

Trade-offs:

- Accuracy can conflict with no_call rate: more calls may raise hit count but worsen false-confidence rate.
- Calibration can reduce overconfident calls: better Brier may lower average confidence.
- Lesson breadth can reduce precision: broad global lessons increase coverage but can mislead unrelated setups.
- Citation rate can reduce citation precision: forcing more citations is bad if citations do not help.
- Learning velocity can reduce lesson quality: fast lesson promotion is harmful without verified future audits.

Six prediction-quality dimensions:

1. Directional accuracy.
   - Metrics: `direction_correct_rate`, hit rate by confidence bucket, hit rate by difficulty/mixed-signal bucket.
   - Baselines: random direction, always-long/market drift proxy, current predictor, no-lesson predictor.

2. Calibration.
   - Metrics: Brier score, expected calibration error, reliability bins, false-confidence rate.
   - Requirement: confidence becomes more honest, not merely higher.

3. no_call discipline.
   - Metrics: no_call rate, no_call usefulness, high-confidence wrong-call rate, optional opportunity-cost proxy versus call/no-call baseline.
   - `no_call` is good when it avoids unsupported direction or overconfidence; it is bad when it dodges clear high-quality evidence.

4. Citation and lesson-use quality.
   - Metrics: citation precision, citation coverage, per-lesson helped/misled, lesson reuse rate, false-citation rate.
   - Citation coverage = eventually-helpful available lessons cited when available / all eventually-helpful available lessons.

5. Continual learning velocity.
   - Metrics: time-to-first-helped, bad-lesson half-life from first verified misled to refine/unproven/risky, library quality distribution over time, tier transition rate, rolling recent-vs-prior trend.

6. Per-lesson quality.
   - Metrics: verified helped/misled, citation precision, coverage, reuse, clone-cluster blast radius, transfer success by scope, invalid_if trigger correctness.

## 9. Predictor Accuracy / Continual Learning Mechanisms

Minimal mechanisms to improve usefulness without promising market accuracy:

- Counter-thesis discipline in the predictor prompt: before direction resolution, name strongest long thesis, strongest short thesis, and why one wins or why `no_call` wins. This is prompt-only but measurable through no_call and calibration metrics.
- Engagement-backed lesson labels: every irrelevant label must state missing precondition, triggered invalid_if, or not-testable bundle gap; evidence-backed labels need source IDs.
- Lesson quality tiers affect order before caps, so verified lessons are more likely to be seen and weak/risky/missing-provenance lessons cannot dominate.
- Dynamic provenance caps prevent FCX Q4-style missing-source rows from earning quality credit or proven tier.
- Near-clone collapse in metrics and optional validator: citations from a near-duplicate cluster are counted as one contribution for blast-radius analysis; predictor should not stack confidence by citing duplicates.
- Confidence calibration report: `learning_metrics.py` emits reliability bins and recommended calibration notes, but does not auto-change prediction confidence.
- no_call discipline: all-not-testable lessons or unresolved counter-thesis forces `no_call` or low confidence. In all all-irrelevant/not-testable batches, confidence remains capped at 35 even when validator-checked non-S10 key-driver evidence permits a directional call.
- Data lessons feed reporting, not auto-builders. Repeated data gaps become human-prioritized implementation candidates.

## 10. Replay Tournament Evaluation Design

Purpose: measure whether changes improve prediction quality without mutating production libraries.

Required tournament design:

- Frozen bundle/library snapshots: copy selected event bundles and learning libraries to `/tmp` or a designated experiment directory. Production `earnings-analysis/learnings` is read-only during tournament.
- Temporal split: train/tune on earlier completed events, hold out later events. No event may use lessons born after its PIT cutoff.
- Predictor-vs-learner isolation: predictor variants run on frozen pre-event bundles; learner/audit variants run after outcomes and cannot feed back into the same holdout prediction.
- Repeated runs or variance handling: run each LLM variant at least three times where cost allows, or report single-run uncertainty and refuse promotion if variance swamps effect size.
- Baselines: random direction, always-long/market drift proxy, current prompt/current design, no-lesson predictor.
- Metrics: direction accuracy, no_call precision/usefulness, Brier, ECE, reliability bins, lesson citation rate, citation precision, citation coverage, lesson helped/misled rate, sentinel rate, confidence-vs-outcome calibration, prediction lift over no-lesson baseline, time-to-first-helped, bad-lesson half-life.
- Promotion rule: require Brier improvement of at least 0.03 over current predictor or a bootstrapped 95% confidence interval excluding zero, while guardrails do not regress beyond tolerances. no_call-usefulness regression beyond 5 percentage points blocks promotion even if Brier improves. A blast-radius breach blocks promotion even if aggregate Brier improves.
- Survivorship guard: ticker selection must include winners, losers, thin data, missing data, high-volatility, and quiet events; do not select only companies with rich lesson histories.
- Minimum sample: under 30 completed events is smoke-only; 30-49 is provisional; 50+ supports rolling-window promotion; 100+ preferred for cross-sector claims.
- No production mutation: tournament writes predictions, learning outputs, and metrics to experiment directories only.

## 11. Exact Future Change Plan

All changes below are future implementation work from the current coded system, not edits made by this design-only goal.

1. `scripts/earnings/earnings_orchestrator.py`
   - PARTIAL: extend `validate_prediction_result` from `prediction_result.v1` to v2 with `engagement_reason`, `engagement_source_ids`, `key_drivers[].evidence_source_ids`, all-sentinel/no_call rule, and source-ID compatibility. Current surface: `scripts/earnings/earnings_orchestrator.py:658`; current key-driver citation validation surface: `scripts/earnings/earnings_orchestrator.py:796`.
   - PARTIAL: extend `finalize_prediction_result` to stamp `context_bundle_sha256`, `rendered_learning_context_sha256`, and `lesson_set_sha256`. Current finalizer and atomic write: `scripts/earnings/earnings_orchestrator.py:3477`, `scripts/earnings/earnings_orchestrator.py:3534`.
   - PARTIAL: add dynamic provenance check in `build_learning_context` / `_decorate_with_learner_paths` using required JSON source artifacts, not markdown sidecars. Current decoration exists at `scripts/earnings/earnings_orchestrator.py:2030`.
   - PARTIAL: add `_audit_provenance_ok` and filter audit histories before tier/status and metric credit, so missing-source auditor events such as FCX Q4 cannot affect Q3 tier/status.
   - PARTIAL: replace recency authority with tier sort before caps. Current recency sorts: `scripts/earnings/earnings_orchestrator.py:2207`, `scripts/earnings/earnings_orchestrator.py:2352`.
   - PARTIAL: add event `.learning.lock`, ticker file locks, and move ticker/global D22 checks inside locked sections. Current ticker no-lock claim: `scripts/earnings/earnings_orchestrator.py:1499`; current global lock: `scripts/earnings/earnings_orchestrator.py:1663`. For ticker append, this means both adding the ticker lock and moving the existing pre-write D22 scan inside that locked read-modify-write.
   - PARTIAL: `_apply_audit_ticker`, `_append_lesson_row_to_ticker_quarter`, and ticker-scope `_register_replacement` use the same ticker lock and keep D22/no-prior-refinement checks inside it.
   - PARTIAL: make `finalize_learning_result` use `_atomic_write_json`. Current unsafe write: `scripts/earnings/earnings_orchestrator.py:3462`; helper: `scripts/earnings/earnings_orchestrator.py:1444`.
   - NET-NEW: write and validate `learning/quality_event.json` after required writes and audit aggregation; use as the sole completion sentinel only when `status: sealed`.
   - NET-NEW/PARTIAL: deterministic recovery path for `learning/result.json` without sealed `quality_event.json`; existing recovery re-applies derived writes but lacks a seal. Current recovery: `scripts/earnings/earnings_orchestrator.py:1205`. This recovery also provides one-time legacy backfill for valid existing prediction+bundle+learning triples.
   - PARTIAL: refuse new historical learner mutation when `derive_learner_pit` returns `invocation_time`; current tier exists at `scripts/earnings/earnings_orchestrator.py:983`.

2. `scripts/earnings/validate_learning.py`
   - PARTIAL: bump accepted schema to `attribution_result.v4` with `lesson_audit[].root_cause`, compatibility rules, and audit-comment sentinel floor. Current v3 wrapper: `scripts/earnings/validate_learning.py:114`; current audit shape: `scripts/earnings/validate_learning.py:542`.
   - PARTIAL: add refinement-lineage validation: `refined_to_lesson_id`, exactly one same-run replacement with matching `parent_id`, recomputed parent/child lesson IDs, inverse parent/refine check, and no-prior-refinement check repeated inside the write lock.
   - PARTIAL: keep existing structured lesson validation and evidence-ref resolution. Current checks: `scripts/earnings/validate_learning.py:501`, `scripts/earnings/validate_learning.py:529`, `scripts/earnings/validate_learning.py:597`.
   - PARTIAL: add `transfer_basis` and `transfer_evidence_refs` for global observations. Existing scope routing: `scripts/earnings/validate_learning.py:322`.
   - PARTIAL: reject bare `action=retire` from LLM output. Existing enum currently permits it: `scripts/earnings/validate_learning.py:107`, `scripts/earnings/validate_learning.py:587`.

3. `scripts/earnings/renderer/lessons.py`
   - PARTIAL: render compact `[tier: ...]` and `[provenance: missing]` markers outside ordered lesson bodies. Current ordered body-only contract: `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:214`.
   - PARTIAL: preserve current L-number single source through `iter_labeled_lessons`. Current generator: `scripts/earnings/_text_utils.py:29`.

4. `.claude/skills/earnings-prediction/SKILL.md`
   - PARTIAL: add engagement fields and counter-thesis/no_call calibration instructions. Current lesson-labeling and no_call rules: `.claude/skills/earnings-prediction/SKILL.md:81`, `.claude/skills/earnings-prediction/SKILL.md:106`, `.claude/skills/earnings-prediction/SKILL.md:227`.
   - PARTIAL: require explanation for confirmed but uncited lessons and all irrelevant labels by missing precondition/invalid_if/not-testable reason.

5. `.claude/skills/earnings-learner/SKILL.md`
   - PARTIAL: add root-cause enum and verified-audit compatibility. Current lesson audit protocol: `.claude/skills/earnings-learner/SKILL.md:126`.
   - PARTIAL: replace broad transfer advice with required transfer proof. Current narrow-scope advice: `.claude/skills/earnings-learner/SKILL.md:94`.
   - PARTIAL: prohibit bare retire; prefer refine or keep with verified misled evidence. Current retire allowed: `.claude/skills/earnings-learner/SKILL.md:161`.

6. `scripts/earnings/learning_metrics.py`
   - NET-NEW: implement `--quality-report`, `--replay-check`, and `--tournament`.
   - NET-NEW: compute rolling Brier, ECE, reliability bins, directional accuracy, no_call usefulness, citation precision/coverage, per-lesson hit/misled, time-to-first-helped, bad-lesson half-life, tier distribution, provenance gaps, sentinel rate, near-clone blast radius.
   - NET-NEW: replay-check reconstructs expected library rows from sealed quality events and legacy source artifacts where possible; it reports extra live rows such as FCX Q4 missing-source rows rather than storing a drift block.
   - NET-NEW: legacy backfill mode seals quality events for source-complete historical triples only after validation; missing-source legacy rows remain unproven.
   - Scope cap: this remains one local read-only reporting/evaluation script except for explicit experiment/backfill outputs. It reads JSON files and libraries only, writes to stdout or an explicit output path, has no daemon mode, performs no Neo4j writes, and creates no persistent metrics cache. The only allowed cache is the section 5.4 in-memory provenance cache keyed by `(source_ticker, quarter_label, file_mtime)`. Any future persistent metrics store requires a separate goal.
   - `--tournament` must validate its output path before any write and refuse if the output path overlaps `earnings-analysis/learnings` or any production `earnings-analysis/Companies/*/events/*` directory.

7. Future tests
   - PARTIAL/NET-NEW: add focused tests for Q1 all-sentinel rejection, Q4 missing-source dynamic cap, Brier/ECE calculation, quality-event recovery, no-call discipline, transfer proof, and tournament no-mutation guarantee.

## 12. What Was Cut, Kept, Added, Deferred

Cut from Round 10:

- Separate `learning/mutation_manifest.json`.
- `.replay_drift_block.json`.
- `.replay_drift_head.json`.
- Quarantine chain/supersession mechanics.
- Replay-wide lock.
- Drift-block and quarantine locks.
- Renderer environment fingerprint.
- Row schema bumps for per-lesson stats.
- Persistent per-lesson stats.
- Separate replay and report scripts.
- `learning/complete.json` and `prediction/complete.json`.

Kept:

- Local Python and JSON.
- PIT filtering and same-quarter self-leak guard.
- D20 body-only matching.
- D19 cross-file audit parity.
- Evidence-source catalog grounding.
- Structured lesson fields.
- Deterministic lesson IDs and D22 collision idea.
- Atomic JSON writes.
- Event/ticker/global lock discipline where it directly protects writes.
- Verified lesson-quality promotion concept.
- Transfer proof concept.

Added:

- `learning/quality_event.json` as one sealed event ledger and metric primitive.
- Brier score as primary rolling quality metric.
- ECE/reliability/no_call/citation/velocity/blast-radius metric stack.
- `rendered_learning_context_sha256` plus `lesson_set_sha256` instead of renderer environment stamping.
- Dynamic provenance caps without durable quarantine.
- One local `learning_metrics.py` for reports, replay check, and tournament.

Deferred:

- External dashboards/services/databases.
- Trade execution or P&L optimization.
- Synthetic hindsight or recursive back-attribution.
- Automatic builder implementation from data lessons.
- Multiclass Brier including no_call probabilities.
- Tamper-proof external anchors for local file rollback.

## 13. Judge Findings and Consensus Log

Round 1 draft status:

- Direct source reads completed for objective prompt, Round 10 plan, current orchestrator/validator/renderer/skills, and FCX Q3/Q4/Q1 corpus evidence.
- First simplified target drafted in this notebook.
- Claude Judge A and B first sandbox attempts wrote `FailedToOpenSocket` API errors to `/tmp/eventmarketdb_quality_judge_a_output.json` and `/tmp/eventmarketdb_quality_judge_b_output.json`; the same stable commands were rerun outside the sandbox.
- Judge C, Codex GPT-5.5 xhigh, implementation/invariant: REJECT. Must-fix C1: all-sentinel/no_call exception was not mechanically enforceable because current key drivers lack source IDs and S10 lesson IDs could be used circularly. Should-fix C2: legacy migration/backfill for `quality_event.json` was underspecified. Should-fix C3: `quality_event.json` needed explicit atomic write and sealed-only status semantics. Nits: ticker-scope source_ticker fallback and exact Q4 inventory paths.
- Judge D, Codex GPT-5.5 xhigh, lesson-quality/predictive-edge: ACCEPT. Nits: always report no_call metrics beside Brier and make blast-radius breaches block promotion.
- Judge B, Claude Opus 4.7, minimal architecture: first rerun produced useful ACCEPT content but malformed output because it included a prose preface before JSON. Per protocol, B requires a JSON-only retry.
- Judge A, Claude Opus 4.7, adversarial reliability: first rerun produced useful REJECT content but malformed output because it included prose and a fenced JSON block. Must-fix A1 refinement lineage, A2 audit provenance filtering, A3 rendered-context drift, and A4 lock order. Should-fix A5 all-irrelevant confidence cap, A6 hash-gated recovery, and A7 canonical JSON provenance predicate. Per protocol, A requires a JSON-only retry.
- Round 1 revision addressed C1-C3, Judge A blockers, Judge B nits, and Judge D nits by adding `key_drivers[].evidence_source_ids`, non-S10 engagement proof, mandatory all-irrelevant confidence cap, rendered learning-context hash, refinement lineage validation, audit-provenance filtering, sealed-only atomic quality-event semantics, hash-gated deterministic recovery, canonical JSON provenance rules, legacy backfill, exact Q4 file inventory, mandatory no_call companion metrics, blast-radius promotion blocking, explicit lock order, metrics-script scope caps, provenance-cache bounds, and explicit audit-key definition.

Round 2 final judge state:

- Judge A, Claude Opus 4.7 JSON-only retry: ACCEPT. Rubric scores: A4/B5/C4/D5/E4/F5/G4/H5/I4/J5. Complexity, lesson quality, and prediction quality all PASS. Nits AN1-AN4 were incorporated in the final cleanup.
- Judge B, Claude Opus 4.7 JSON-only retry: ACCEPT. Rubric scores: A4/B5/C5/D5/E5/F4/G4/H5/I5/J5. Complexity, lesson quality, and prediction quality all PASS. Nits BN1-BN4 were incorporated in the final cleanup.
- Judge C, Codex GPT-5.5 xhigh rerun: ACCEPT. Rubric scores: A4/B5/C4/D5/E5/F5/G4/H5/I4/J5. Complexity, lesson quality, and prediction quality all PASS. Nits CN1-CN2 were incorporated in the final cleanup.
- Judge D, Codex GPT-5.5 xhigh rerun: ACCEPT. Rubric scores: A4/B5/C4/D5/E5/F5/G4/H5/I5/J4. Complexity, lesson quality, and prediction quality all PASS. Nits DN1-DN2 were incorporated in the final cleanup.

## 14. Final Reliability and Quality Check

Final audit:

- Replayability: preserved by sealed quality events plus replay-check; weaker than Round 10 against local tamper, acceptable for v0 if judges agree.
- PIT discipline: preserved by existing filters and new refusal of invocation-time historical learner mutation.
- Idempotency: preserved by sealed quality event, existing upsert semantics, event/ticker/global locks.
- Engagement evidence: improved through prediction v2 engagement reasons/source IDs and all-sentinel/no_call discipline.
- Quality differentiation: improved through verified tiers and metrics.
- Scope justification: improved through transfer proof.
- Recovery: simplified to deterministic recovery from `learning/result.json` plus source hashes into one quality event; no drift chain.
- Observability: improved by Brier/ECE/no_call/citation/velocity metrics.
- Bounded blast radius: measured through near-clone cluster misled share and citation share.
- Minimalism: substantially lower Round 10 ledger score; implementation cost is still net-positive but concentrated in one artifact and one tool.

Completion condition is met for this design-only goal. The final design is materially simpler than Round 10 in Ledger 1, honest about real implementation cost from current code in Ledger 2, stronger on lesson quality and prediction-quality measurement, explicit about Brier as the primary metric and guardrails as non-regression constraints, implementation-ready as a future delta from current code, accepted by all four judges, and still safe against Q1-style lazy sentinel behavior and Q4-style provenance gaps.
