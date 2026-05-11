# EventMarketDB Learner Loop - Operational Hardening

Status: complete operational hardening plan
Round: 15 complete after consecutive saturation
Last updated: 2026-05-11

Design-only guardrail: this file is the only repository file this goal may change. This goal does not edit production code, production corpus JSON, existing skills, or `earnings-analysis/`.

## Completion Objective

Harden the accepted Round 11 simplified-quality learner-loop design for unattended local operation across roughly 200 tickers and quarterly cycles, while keeping it materially simpler than the Round 10 reliability benchmark. The target remains a production-grade Python/JSON design, not an implementation in this turn and not a claim of guaranteed market prediction accuracy.

Concrete success criteria:

- `events/{quarter}/learning/quality_event.json` plus event artifacts are canonical.
- `earnings-analysis/learnings/*.json` remains a derived cache.
- One local `scripts/earnings/learning_metrics.py` handles replay check, quality report, and tournament evaluation.
- No replay drift-block/head chain, mutation manifest, durable quarantine ledger, database, service, dashboard, trade daemon, or trigger expansion unless judges prove the simplified design fails.
- The plan covers replayability, PIT discipline, idempotency, engagement evidence, quality differentiation, scope proof, recovery, observability, bounded blast radius, minimalism, performance/scale, migration completeness, test depth, and operational integration.
- At least five judge rounds must run before completion, and two consecutive saturation rounds must have all four judges scoring A-N as 5/5 with ACCEPT and no non-nit findings.

## 1. Current Code Baseline

Current implementation baseline, verified from direct reads in this round:

- `build_prediction_bundle` runs the bundle builders, stamps `schema_version`, `ticker`, `quarter_info`, `pit_cutoff`, `assembled_at`, and `learning_context`, then attaches `evidence_source_catalog`. A non-assertion learning-context failure falls back to empty lessons. Evidence: `scripts/earnings/earnings_orchestrator.py:196`, `scripts/earnings/earnings_orchestrator.py:241`, `scripts/earnings/earnings_orchestrator.py:258`, `scripts/earnings/earnings_orchestrator.py:269`, `scripts/earnings/earnings_orchestrator.py:277`.
- Prediction validation is `prediction_result.v1`; it requires `lesson_labels`, body-position matching, confirmed-only `cites_lesson_indices`, analysis quote suppression for non-confirmed lessons, and `evidence_ledger.source_id` grounding. It does not reject an all-irrelevant all-sentinel prediction that still makes a directional call. Evidence: `scripts/earnings/earnings_orchestrator.py:658`, `scripts/earnings/earnings_orchestrator.py:701`, `scripts/earnings/earnings_orchestrator.py:755`, `scripts/earnings/earnings_orchestrator.py:775`, `scripts/earnings/earnings_orchestrator.py:796`, `scripts/earnings/earnings_orchestrator.py:853`.
- The predictor skill already requires testing `applies_when` and `invalid_if`, cites only confirmed lessons, and says unsupported evidence should become `no_call`; the strongest semantics are still prompt-side. Evidence: `.claude/skills/earnings-prediction/SKILL.md:81`, `.claude/skills/earnings-prediction/SKILL.md:99`, `.claude/skills/earnings-prediction/SKILL.md:106`, `.claude/skills/earnings-prediction/SKILL.md:213`, `.claude/skills/earnings-prediction/SKILL.md:227`.
- Learner PIT uses next-quarter filed time, live-cycle filed time, then current invocation time. Tier 3 is non-replayable for historical learning. Evidence: `scripts/earnings/earnings_orchestrator.py:938`, `scripts/earnings/earnings_orchestrator.py:965`, `scripts/earnings/earnings_orchestrator.py:972`, `scripts/earnings/earnings_orchestrator.py:983`.
- Learner execution gates on `prediction/result.json`, can recover from an existing `learning/result.json`, validates schema plus cross-file audit parity, appends ticker/global lessons, and aggregates audits. It has no sealed event-quality ledger. Evidence: `scripts/earnings/earnings_orchestrator.py:1133`, `scripts/earnings/earnings_orchestrator.py:1199`, `scripts/earnings/earnings_orchestrator.py:1205`, `scripts/earnings/earnings_orchestrator.py:1333`, `scripts/earnings/earnings_orchestrator.py:1398`, `scripts/earnings/earnings_orchestrator.py:1415`.
- Prediction finalization uses `_atomic_write_json`; learning finalization rewrites `learning/result.json` with `Path.write_text`. The current CLI/main path writes `context_bundle.json` and `context_bundle_rendered.txt`, unlinks existing `prediction/result.json` and `section_audit.json`, then finalizes a new prediction before any sealed quality-event guard exists. Evidence: `scripts/earnings/earnings_orchestrator.py:3420`, `scripts/earnings/earnings_orchestrator.py:3462`, `scripts/earnings/earnings_orchestrator.py:3477`, `scripts/earnings/earnings_orchestrator.py:3534`, `scripts/earnings/earnings_orchestrator.py:3823`, `scripts/earnings/earnings_orchestrator.py:3836`, `scripts/earnings/earnings_orchestrator.py:3838`, `scripts/earnings/earnings_orchestrator.py:3863`.
- Production `--save`/`--predict` passes `related_filings_dir` into `run_core_flow`; the inter-quarter builder creates allowlisted `events/{quarter}/related_filings/{accession}.md` sidecars before the later bundle write block. The predictor skill explicitly permits reading allowlisted related-filing and prior-learner sidecars. Evidence: `scripts/earnings/earnings_orchestrator.py:3793`, `scripts/earnings/earnings_orchestrator.py:3802`, `scripts/earnings/builders/inter_quarter_context.py:921`, `scripts/earnings/builders/inter_quarter_context.py:983`, `scripts/earnings/builders/inter_quarter_context.py:1117`, `scripts/earnings/builders/inter_quarter_context.py:1155`, `.claude/skills/earnings-prediction/SKILL.md:27`, `.claude/skills/earnings-prediction/SKILL.md:33`.
- Ticker lesson append is atomic but explicitly assumes no lock. Global append uses `fcntl.flock`, but the D22 collision scan happens before the lock. Evidence: `scripts/earnings/earnings_orchestrator.py:1487`, `scripts/earnings/earnings_orchestrator.py:1499`, `scripts/earnings/earnings_orchestrator.py:1559`, `scripts/earnings/earnings_orchestrator.py:1658`, `scripts/earnings/earnings_orchestrator.py:1663`.
- Lesson IDs are deterministic hashes over normalized body, scope, and routing key. Current status is transient active/watch/retired over PIT-visible audits; recency, not quality tier, drives render caps. Evidence: `scripts/earnings/earnings_orchestrator.py:1817`, `scripts/earnings/earnings_orchestrator.py:1900`, `scripts/earnings/earnings_orchestrator.py:2207`, `scripts/earnings/earnings_orchestrator.py:2352`.
- `build_learning_context` filters by `source_pit_cutoff`, applies same-quarter self-leak guard, filters audit PIT, drops retired lessons, sorts by recency, and caps ticker/global rows. Evidence: `scripts/earnings/earnings_orchestrator.py:2101`, `scripts/earnings/earnings_orchestrator.py:2159`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2236`, `scripts/earnings/earnings_orchestrator.py:2352`.
- Learner-path decoration currently exposes `learning/result.md` sidecars to prediction. Canonical learning provenance remains JSON-led, but any explicitly allowlisted sidecar that the predictor may read must be hashed as part of the current prediction source tuple. Evidence: `scripts/earnings/earnings_orchestrator.py:2030`, `scripts/earnings/earnings_orchestrator.py:2068`, `scripts/earnings/earnings_orchestrator.py:2071`.
- Renderer L-numbering and validator lesson order share `iter_labeled_lessons`; ordered lesson text contains body only. Evidence: `scripts/earnings/_text_utils.py:29`, `scripts/earnings/_text_utils.py:35`, `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:209`, `scripts/earnings/renderer/lessons.py:214`.
- Learning validation is v3-only and enforces structured lesson fields, non-empty resolving evidence refs, global scope routing shape, and audit shape, but not root-cause compatibility, transfer proof, sealed event replay, or quality metrics. Evidence: `scripts/earnings/validate_learning.py:70`, `scripts/earnings/validate_learning.py:107`, `scripts/earnings/validate_learning.py:322`, `scripts/earnings/validate_learning.py:459`, `scripts/earnings/validate_learning.py:501`, `scripts/earnings/validate_learning.py:542`, `scripts/earnings/validate_learning.py:597`.
- Cross-file learner validation enforces audit count, index, predictor label, `was_cited`, and lesson-text parity against prediction and bundle. Evidence: `scripts/earnings/earnings_orchestrator.py:2968`, `scripts/earnings/earnings_orchestrator.py:2996`, `scripts/earnings/earnings_orchestrator.py:3003`, `scripts/earnings/earnings_orchestrator.py:3019`, `scripts/earnings/earnings_orchestrator.py:3041`.
- There is currently no `scripts/earnings/learning_metrics.py` on disk; `find . -path '*learning_metrics.py' -print` returned no paths.

Live FCX corpus evidence:

- Q4_FY2025 currently has only `context_bundle.json`, `context_bundle_rendered.txt`, and two related filing markdown files; there is no Q4 prediction or learning JSON artifact on disk.
- Despite that, `earnings-analysis/learnings/ticker/FCX.json` contains a Q4 row with two ticker lessons and `earnings-analysis/learnings/global.json` contains a Q4 BasicMaterials sector lesson. Evidence: `earnings-analysis/learnings/ticker/FCX.json:100`, `earnings-analysis/learnings/ticker/FCX.json:119`, `earnings-analysis/learnings/global.json:48`, `earnings-analysis/learnings/global.json:64`.
- Q3 lessons carry Q4 audit entries whose source learner artifact is absent. Evidence: `earnings-analysis/learnings/ticker/FCX.json:41`, `earnings-analysis/learnings/ticker/FCX.json:73`, `earnings-analysis/learnings/global.json:26`.
- Q1 saved bundle included Q4 lessons and an allowed Q4 learner markdown path even though the Q4 markdown path is absent now. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5477`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5545`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5650`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5729`.
- Q1 prediction labeled all six lessons irrelevant, used the exact sentinel for every label, cited no lesson, and still made a short call at confidence 48. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:1`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:40`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:172`.
- Q3 is source-complete legacy: prediction exists with empty lesson labels, learning is `attribution_result.v3`, learner PIT is `next_quarter`, actual daily return is present, and lessons/audits can be traced to source files. Evidence: `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json:1`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:1`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:10`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:198`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:228`.

## 2. Round 10 Reliability Benchmark

Round 10 is the reliability benchmark, not current implementation. It proposed prediction v2 engagement, learner v4 verified audits/root causes, mutation manifests, replay scripts, provenance quarantine, replay drift block/head, replay-wide locks, renderer environment fingerprints, and merged reporting. It converged for a broader reliability-only design but accepted much more persistent state than the simplified target needs.

Benchmark properties to preserve:

- Replayability: derived libraries are rebuildable or visibly unrebuildable.
- PIT discipline: lessons cannot become visible before their source event could have been learned.
- Idempotency: reruns do not duplicate rows or audits.
- Engagement evidence: predictor and learner cannot lazily skip rendered lessons.
- Quality differentiation: verified lessons outrank fresh but unproven lessons.
- Scope justification: global/cross-ticker lessons need transfer proof.
- Recovery: partial writes are not mistaken for complete learning.
- Observability: quality and failure modes are measurable.
- Bounded blast radius: one lesson or near-clone cluster cannot dominate misleading outcomes.

Round 10 components intentionally cut unless judges force them back:

- Separate `learning/mutation_manifest.json`.
- Replay drift block and drift head chain.
- Durable provenance quarantine chain.
- Replay-wide lock as a routine primitive.
- Persistent per-lesson stats and report state.
- Renderer environment fingerprint.
- Separate replay/report scripts.
- External service, database, queue, dashboard, daemon, or trading scope.

## 3. Round 11 Simplified-Quality Baseline

Round 11 accepted the simplifying idea:

- Event artifacts plus `learning/quality_event.json` are canonical.
- `learnings/*.json` is a recoverable derived cache.
- Missing-source rows are capped dynamically at unproven and earn zero quality credit.
- One local `learning_metrics.py` handles replay/report/tournament.
- Brier score is the primary prediction-quality metric, with directional accuracy, no_call usefulness, citation precision, continual-learning trend, and blast-radius guardrails.
- Lesson quality remains causal, future-verifiable, falsifiable, decision-relevant, evidence-backed, scoped, non-generic, reusable, and measurable.

Round 12 hardens Round 11 without reverting to Round 10:

- Make the `quality_event.json` schema a real seal and recovery contract.
- Add lock order and in-flight semantics for unattended concurrent learner runs.
- Define migration states for the live corpus.
- Expand tests and runbook to production operations.
- Add scale expectations for roughly 200 tickers across quarterly cycles.
- Clarify exact future implementation deltas from current code.

## 4. Operational Hardening Findings

Findings to close:

- F1: Q1-style lazy all-sentinel prediction is currently validator-legal.
- F2: Q4-style missing-source library rows and audits can remain visible as normal context.
- F3: Recency-first caps can hide older verified lessons behind new unproven rows.
- F4: Learner audit semantics are under-typed; root cause and compatibility are not deterministic.
- F5: Global lessons need transfer proof beyond routing shape.
- F6: Derived writes lack a sealed event ledger for replay/recovery and metrics.
- F7: Historical learner PIT fallback to invocation time is non-replayable.
- F8: Ticker/global concurrency is weaker than unattended multi-ticker operation needs.
- F9: Learning result finalization is not atomic.
- F10: `learning_metrics.py` does not exist yet.
- F11: Migration from current live corpus is not currently classified into source-complete, missing-source, already-valid, failed-recovery, and human-decision states.
- F12: Operational integration and runbook need to say what humans do when provenance/recovery fails.
- F13: The event lock must be acquired before any `learning/result.json` read or write. A lock acquired after SDK invocation still permits concurrent same-event result races.
- F14: Dynamic provenance checks can become O(lesson or audit references times source files) unless each process builds a bounded event-artifact index and reuses it.
- F15: Legacy backfill needs hash-origin metadata; a rendered-learning-context hash computed during backfill is weaker than one stamped at prediction finalization.
- F16: Near-clone blast-radius rules require a deterministic cluster key, not prompt-only judgment.
- F17: `failed_recoverable` can loop forever in unattended operation unless retries and human-decision escalation are part of the same quality-event contract.
- F18: The quality-event immutability guard must start before production `--save`/`--predict` writes or unlinks source artifacts. Guarding only the learner path can detect drift after a rerun but cannot recover overwritten source bytes.
- F19: The protected prediction source tuple must cover the full rendered prompt, section-audit artifact, and every explicitly allowlisted prompt-readable sidecar, not only JSON files and prior-lessons hash.
- F20: Save-only production artifacts and existing v2-invalid predictions need explicit human-decision handling; otherwise the immutability guard can create a silent stuck state.
- F21: Save-only production tuples need a save-time hash authority before `prediction/result.json` or `quality_event.json` exists, or prompt-readable edits between `--save` and first `--predict` can be canonized.
- F22: `EventArtifactIndex` must index the full `prediction_source_tuple`, not only JSON files, or the source-tuple expansion either escapes fast provenance checks or causes repeated sidecar hashing at scale.
- F23: Save-time bundle-payload hashes need a pinned canonical JSON routine shared by save, predict, seal, replay, and backfill; otherwise byte-equivalent JSON data can false-drift.
- F24: Save-time hash origins must survive into prediction and quality-event artifacts as `stamped_at_save_finalize`, or reports cannot prove hashes came from the pre-prediction commitment.
- F25: Because `production_source_commitment` lives inside prompt-readable `context_bundle.json` but is excluded from `context_bundle_payload_sha256`, the commitment object itself must be exact-schema and recomputed or unknown prompt-like fields can bypass the payload hash.
- F26: Dynamic provenance must be row-level as well as artifact-level. A fabricated or mutated live cache lesson/audit cannot inherit trust merely by pointing at a sealed source event.
- F27: Row provenance must bind the full prompt-visible live-cache projection, not only identity fields. A row with canonical lesson ID/body/source fields but mutated `mechanism`, `applies_when`, `invalid_if`, `evidence_refs`, ticker context, routing display fields, or audit text can still alter the predictor prompt unless those fields match the canonical sealed event projection before rendering.
- F28: Audit provenance must require exact PIT-visible audit-set equality, not only validation of audits that remain present. A deleted canonical misled audit can otherwise suppress risky status, review markers, metrics, and blast-radius counts until replay-check.

Constraints kept:

- No durable quarantine ledger in v0. Dynamic provenance caps are stricter and simpler: missing-source rows never become proven and never earn quality credit until source artifacts are restored and sealed.
- No drift-block/head chain. Replay health is recomputed from canonical event artifacts and live derived caches. Local tamper rollback of all source artifacts plus ledgers remains residual risk accepted for a local filesystem workflow.
- No expansion into trigger/trade scope. The learner loop may be called by the current orchestrator or future trigger context, but it does not place trades or expand trigger decisions.

## 5. Strict Rubric A-N Scores

Round 1 external judge scores:

| Rubric | Judge A | Judge B | Judge C | Judge D | Round 1 outcome |
|---|---:|---:|---:|---:|---|
| A. Replayability | 4 | 5 | 5 | 5 | REJECT: replay-check in-flight probing underspecified. |
| B. PIT discipline | 5 | 5 | 5 | 5 | Pass. |
| C. Idempotency | 4 | 5 | 4 | 5 | REJECT: event lock must start before SDK result writes; cross-ticker audit lock order and audit upsert keys need clarity. |
| D. Engagement evidence | 5 | 5 | 5 | 5 | Pass. |
| E. Quality differentiation | 5 | 5 | 5 | 5 | Pass. |
| F. Scope justification | 5 | 5 | 5 | 5 | Pass. |
| G. Recovery | 4 | 5 | 4 | 5 | REJECT: failed-recoverable retry state and legacy hash-origin policy needed. |
| H. Observability | 5 | 5 | 5 | 5 | Pass, contingent on operational alert/log fixes under N. |
| I. Bounded blast radius | 4 | 5 | 5 | 5 | REJECT: deterministic near-clone clustering needed. |
| J. Minimalism | 5 | 5 | 5 | 5 | Pass. |
| K. Performance / scale | 4 | 4 | 4 | 4 | REJECT: 200-ticker scale contract and bounded index/cache test needed. |
| L. Migration completeness | 4 | 4 | 5 | 5 | REJECT: live FCX classification and source-complete legacy backfill ownership needed. |
| M. Test depth | 5 | 5 | 5 | 4 | REJECT: performance benchmark and edge recovery tests needed. |
| N. Operational integration | 4 | 5 | 4 | 5 | REJECT: scheduling, logs, exit codes, and orchestrator backpressure needed. |

Round 1 verdict: all four judges rejected. The rest of this revision incorporates the smallest fixes without adding Round 10's manifest, drift-block/head chain, durable quarantine ledger, database, daemon, dashboard, or trading scope. Completion still requires at least five total judge rounds and two consecutive all-5 ACCEPT saturation rounds.

Round 2 verdict: Judges B, C, and D accepted with all A-N scores at 5/5. Judge A rejected with only rubric I at 4/5 because the exact-hash-only near-clone fallback was too weak. This revision removes that fallback and requires deterministic shingled near-clone clustering in v0.

Round 3 verdict: Judges B, C, and D accepted with all A-N scores at 5/5. Judge A rejected with only rubric A at 4/5 because replay-check drift detection did not have an explicit non-zero exit and alert handoff for cache-vs-canonical drift. This revision makes `--replay-check` exit non-zero and emit `LEARNER_ALERT status=replay_drift` for extra live rows, missing live rows, and hash drift, without adding durable drift state.

Round 5 verdict: Judges A, B, and D accepted with all A-N scores at 5/5 after JSON-only retry where needed. Judge C rejected with A/C/G/M/N at 4/5 because production bundle and prediction writes could overwrite source artifacts before the learner-side sealed-event guard. This revision moves the immutability guard to the first production write/unlink boundary. A malformed B output also identified two recovery-note booleans derivable from `hash_origins`; they are deleted as a simplification.

Round 6 verdict: Judges A, B, and D accepted with all A-N scores at 5/5 after JSON-only retry where needed, but Judge C rejected with source-tuple and save-only lifecycle blockers. This revision defines one protected `prediction_source_tuple`, moves the guard before related-filing sidecar creation, seals the full rendered prompt/section audit/allowlisted sidecar hashes, and adds human-decision handling for invalid existing predictions.

Round 7 verdict: Judges A and B accepted with all A-N scores at 5/5 after JSON-only retry where needed, but Judges C and D rejected. This revision adds a save-time `production_source_commitment` inside `context_bundle.json` and widens `EventArtifactIndex` to cache every artifact in the full `prediction_source_tuple`.

Round 8 verdict: Judges B and D accepted, while Judges A and C rejected with narrow schema blockers. This revision pins canonical JSON serialization for `context_bundle_payload_sha256`, adds `stamped_at_save_finalize` to the origin enum, and requires prediction/quality-event artifacts to preserve that save-time origin.

## 6. Complexity Ledgers

Weights:

- Durable artifact type = 4
- Lock/concurrency primitive = 4
- Schema version or major schema field group = 3
- Validator surface = 3
- Script/tool = 3
- Persistent state/status enum = 2
- Prompt-only rule = 1

Ledger 1 - Round 10 benchmark to hardened target:

| Category | Round 10 weighted items | Round 10 score | Hardened target weighted items | Hardened score |
|---|---:|---:|---:|---:|
| Durable artifact types | mutation manifest, drift block, drift head, provenance quarantine, report state | 20 | `learning/quality_event.json` only; reports are stdout or explicit experiment outputs | 4 |
| Locks/concurrency primitives | replay-wide, event, ticker, global, drift-block, quarantine | 24 | event `.learning.lock`, ticker locks, global lock | 12 |
| Schema/major field groups | prediction v2, learner v4, manifest, drift block, quarantine, row stats, renderer environment | 21 | prediction engagement/hash v2, source commitment in context bundle, learner audit-quality v4, quality event v1, metrics output | 15 |
| Validator surfaces | prediction, learner, manifest, drift block, quarantine, replay, transfer, renderer environment | 24 | prediction, learner, quality event, dynamic provenance, metrics/replay | 15 |
| Scripts/tools | replay, report | 6 | one `learning_metrics.py` with `--replay-check`, `--quality-report`, `--tournament`, `--backfill-legacy`, `--reset-failed-recoverable` | 3 |
| Persistent state/status enums | manifest status, quarantine status/action, drift state, root cause, tier, engagement | 12 | quality event status, root cause, tier, engagement | 8 |
| Prompt-only rules | engagement, root-cause discipline, transfer, calibration | 4 | counter-thesis, lesson causality, calibration/no_call | 3 |
| Total |  | 111 |  | 60 |

Ledger 1 verdict: materially simpler than Round 10 by 51 weighted points, mostly by cutting the manifest/drift/quarantine chain and collapsing replay/report/tournament into one tool.

Ledger 2 - Current code to hardened target:

| Change | Class | Current evidence | Need |
|---|---|---|---|
| Keep PIT lesson filtering and same-quarter guard | ALREADY-CODED | `scripts/earnings/earnings_orchestrator.py:2159`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2300` | Preserves PIT visibility. |
| Keep D20 body-only positional lesson matching | ALREADY-CODED | `scripts/earnings/_text_utils.py:29`, `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:214`, `scripts/earnings/earnings_orchestrator.py:782` | Prevents marker/body drift and spoofed labels. |
| Keep source-ID grounding | ALREADY-CODED | `scripts/earnings/earnings_orchestrator.py:277`, `scripts/earnings/earnings_orchestrator.py:853` | Grounds prediction evidence. |
| Keep structured learner lesson fields and evidence refs | ALREADY-CODED | `scripts/earnings/validate_learning.py:501`, `scripts/earnings/validate_learning.py:529`, `.claude/skills/earnings-learner/SKILL.md:82` | Keeps lesson quality shape. |
| Prediction v2 engagement reason/source IDs and all-sentinel discipline | PARTIAL | Validator surface at `scripts/earnings/earnings_orchestrator.py:658`; current sentinel gap at `scripts/earnings/earnings_orchestrator.py:775`; Q1 failure at `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8` | Closes lazy prediction. |
| Stamp context, rendered-learning-context, and lesson-set hashes | PARTIAL | `finalize_prediction_result` at `scripts/earnings/earnings_orchestrator.py:3477`; atomic write at `scripts/earnings/earnings_orchestrator.py:3534` | Enables replay and renderer-drift checks without full renderer environment state. |
| Learner v4 root cause, audit compatibility, refinement lineage | PARTIAL | Current audit shape at `scripts/earnings/validate_learning.py:542`; current refine support at `scripts/earnings/validate_learning.py:601`; current retire enum at `scripts/earnings/validate_learning.py:107` | Makes lesson quality mechanically auditable. |
| Transfer proof for global observations | PARTIAL | Current scope routing at `scripts/earnings/validate_learning.py:322`; prompt narrow-scope advice at `.claude/skills/earnings-learner/SKILL.md:94` | Prevents over-broad global routing. |
| Dynamic provenance cap in learning context | PARTIAL | Current markdown path decoration at `scripts/earnings/earnings_orchestrator.py:2030`; Q4 missing-source rows prove need | Prevents unproven source gaps from earning trust. |
| Quality tier sort before caps | PARTIAL | Current recency sorts at `scripts/earnings/earnings_orchestrator.py:2207`, `scripts/earnings/earnings_orchestrator.py:2352` | Keeps verified lessons visible. |
| Ticker/event locks and D22 inside locks | PARTIAL | Ticker no-lock at `scripts/earnings/earnings_orchestrator.py:1499`; global lock at `scripts/earnings/earnings_orchestrator.py:1663`; global D22 outside lock at `scripts/earnings/earnings_orchestrator.py:1658` | Multi-ticker unattended safety. |
| Atomic learning result finalization | PARTIAL | Unsafe write at `scripts/earnings/earnings_orchestrator.py:3462`; atomic helper at `scripts/earnings/earnings_orchestrator.py:1444` | Avoids partial learner JSON. |
| `learning/quality_event.json` | NET-NEW | No current ledger; recovery starts at `scripts/earnings/earnings_orchestrator.py:1205` | Single seal, recovery, and metric primitive. |
| `scripts/earnings/learning_metrics.py` | NET-NEW | `find . -path '*learning_metrics.py' -print` found none | Replay/report/tournament tool. |

## 7. Hardened Target Architecture

Principle: one completed learning event should answer what the predictor committed to, what the learner decided after outcome, and what future metrics/replay may trust.

### Prediction Result v2

Add small deterministic engagement and hash fields:

- `schema_version: prediction_result.v2`.
- `context_bundle_sha256` over saved `context_bundle.json`.
- `full_rendered_prompt_sha256` over saved `context_bundle_rendered.txt`.
- `rendered_learning_context_sha256` over the exact prior-lessons block rendered to the predictor.
- `lesson_set_sha256` over ordered lesson bodies plus source IDs.
- `section_audit_sha256` over `prediction/section_audit.json` after predictor audit write.
- `allowlisted_prompt_sidecars[]`: sorted `{path, sha256}` entries for every prompt-readable sidecar explicitly allowlisted in the saved bundle.
- Per `lesson_labels[]`: `engagement_reason` enum and `engagement_source_ids`.
- Per `key_drivers[]`: `evidence_source_ids` list separate from prose `evidence`.

Engagement rules:

- `condition_met` and `opposite_evidence` require non-empty, resolving, non-S10 source IDs from the current bundle.
- `invalid_if_triggered` names the invalidating condition and cites at least one non-S10 source ID.
- `missing_precondition` names the missing precondition and may have empty source IDs.
- `not_testable_no_bundle_signal` uses empty source IDs and counts as a data-coverage warning.
- In an all-irrelevant or all-not-testable batch, `confidence_score <= 35` is mandatory. A directional call is allowed only when at least two `key_drivers[]` contain non-empty resolving non-S10 `evidence_source_ids` spanning at least two distinct source IDs; otherwise `direction` must be `no_call`.
- Free-text evidence never qualifies for this exception.

### Production Artifact Immutability Guard

Production event artifacts are protected before the first production write or unlink, not only when learner mutation begins:

- The guard covers production `--save`, `--predict`, `--predict --learn`, and live-trigger paths that would write or unlink `context_bundle.json`, `context_bundle_rendered.txt`, `prediction/result.json`, `prediction/section_audit.json`, allowlisted prompt sidecars, or `learning/result.json`.
- Dry in-memory inspections and explicit experiment output directories are outside this production guard, but they must not write under production event directories or production learning libraries.
- Before any covered write, unlink, or builder call that can create allowlisted prompt sidecars, resolve prediction and learning paths through the same path helpers, acquire the event `.learning.lock`, and inspect `learning/quality_event.json` plus the existing prediction source tuple.
- If `quality_event.json` is `sealed`, exit or return `already_sealed` before touching bundle, rendered bundle, prediction, section-audit, learner, ticker, or global artifacts.
- The `prediction_source_tuple` is the single source set used by this guard, prediction validation, quality-event source hashes, replay-check, recovery, migration, and `--quality-report`: `context_bundle.json`, full `context_bundle_rendered.txt`, `prediction/result.json` when present, `prediction/section_audit.json` when present, `learning/result.json` when present, and every explicit prompt-readable sidecar path in `learning_context._allowed_learner_paths` and `inter_quarter_context._allowed_related_filing_paths`. Human markdown outside these allowlists never counts.
- Source hashes store both individual core file hashes and `allowlisted_prompt_sidecars[]` as sorted `{path, sha256}` entries. This hashes only prompt-readable production sidecars, not the whole event directory.
- Production `--save` and the first production build stamp a `production_source_commitment` object inside `context_bundle.json` under the event lock after `context_bundle_rendered.txt` and allowlisted sidecars exist. It contains `context_bundle_payload_sha256` over canonical bundle JSON excluding the commitment field, `full_rendered_prompt_sha256`, sorted `allowlisted_prompt_sidecars[]`, and `hash_origin: stamped_at_save_finalize`. The final `context_bundle_sha256` used later is over the saved bundle including the commitment.
- Canonical bundle serialization for `context_bundle_payload_sha256` is `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")` after a deterministic pre-pass that converts datetimes and Decimals to ISO/string values so `default=str` is never invoked. The same helper is used for save-time stamping, predict-time validation, seal-time recompute, replay-check verification, and `--backfill-legacy`.
- `production_source_commitment` is a strict exact-schema object: no unknown keys, no free-text fields, fixed primitive types, sorted sidecar path order, and hash-origin enum validation. On every save-only no-op, predict, seal, replay, and backfill path, recompute the expected commitment object from the bundle payload excluding the commitment field, rendered prompt bytes, and allowlisted sidecars; reject if the actual object has any extra key, missing key, wrong type, wrong order, or mismatched value.
- The production guard validates `production_source_commitment` for any save-only tuple before no-op, prediction, or learning. Missing or schema-invalid commitment on legacy save-only tuples is human-decision or missing-source, not a reason to silently rehash current bytes.
- `prediction_result.v2` and `quality_event.json` copy or verify the committed save-time hashes for bundle payload, full rendered prompt, and prompt sidecars with `hash_origin: stamped_at_save_finalize`; they do not invent those values at prediction finalization.
- If `prediction/result.json` already exists and no sealed quality event exists, normal production mode validates and reuses the existing prediction source tuple. It must not overwrite the bundle, rendered bundle, prediction result, section audit, or allowlisted sidecars. Fresh predictor overwrites belong only in explicit experiment output.
- If `prediction/result.json` exists, no sealed quality event exists, and v2 validation fails, the guard does not overwrite or unlink. It emits `LEARNER_ALERT status=prediction_invalid_existing ticker=<T> quarter=<Q> reason=<schema_v2_violation>`, returns future `LearnerOutcome.SKIPPED_HUMAN_DECISION`, and is counted by `--quality-report --all` under `human_decision_required_count`.
- If a save-only production tuple exists without `prediction/result.json`, later production `--save` must reuse/no-op, and production `--predict` must consume that saved tuple without rebuilding bundle, rendered text, or allowlisted sidecars. If the saved tuple is incomplete or hash-mismatched, emit `LEARNER_ALERT status=prediction_source_incomplete ...` and return `SKIPPED_HUMAN_DECISION`.
- If no production source tuple exists, normal production mode may build/write the bundle, rendered bundle, related-filing sidecars, run the predictor, finalize prediction v2, validate it, and stamp hashes while holding the event lock through prediction finalization. A prediction-only run may release the event lock after validation; a predict-and-learn run may keep it through learner seal.

### Learner Result v4

Add verified audit quality without adding a second learner artifact:

- `schema_version: attribution_result.v4`.
- `lesson_audit[].root_cause` enum: `correct_nonapplication`, `lesson_helped`, `lesson_misled`, `lesson_good_ignored`, `data_missing`, `outcome_noise`.
- Verified audit credit requires resolving evidence refs, non-sentinel comment, review/action/root-cause compatibility, and audit provenance OK.
- `action=retire` is rejected from LLM output. Evidence-driven risk/retirement is tier logic; human removal is outside automated learner mutation.
- `action=refine` requires `refined_to_lesson_id`; the same result emits exactly one replacement lesson whose recomputed ID matches and whose `parent_id` equals the audited parent. The no-prior-refinement check is repeated inside the ticker/global write lock before append.
- Global observations require `transfer_basis` and `transfer_evidence_refs`, scope-compatible and resolving. Without proof, the lesson stays ticker-scope.

### Quality Event Ledger

Future path: `events/{quarter}/learning/quality_event.json`.

Schema summary:

- `schema_version: learning_quality_event.v1`.
- `status: sealed | failed_recoverable`.
- `event_identity`: ticker, quarter_label, accession, filed_8k, event path.
- `source_hashes`: context bundle, full rendered prompt, prediction result, section audit, allowlisted prompt sidecars, learning result, rendered learning context, and lesson set.
- `hash_origins`: per-hash origin enum `stamped_at_save_finalize`, `stamped_at_prediction_finalize`, `stamped_at_learning_finalize`, `computed_from_saved_prompt_artifact`, or `computed_at_backfill_current_renderer`.
- `prediction_snapshot`: direction, confidence, expected range, confidence bucket, key-driver source IDs, cited lesson IDs, no_call flag.
- `outcome_snapshot`: actual return fields used for metrics.
- `learning_snapshot`: emitted lesson IDs, global observation IDs, audit keys, refinement links, root causes, required write outcomes.
- Source paths are derived from `event_identity` through path helpers and from explicit prompt-sidecar allowlists in the saved bundle. At seal time, recompute on-disk SHA-256 for the whole `prediction_source_tuple` and refuse seal if any value differs from the corresponding stamped `source_hashes` entry.
- `recovery_notes`: structured object, not free prose. It contains `steps_taken[]` enum values (`legacy_backfill`, `deterministic_recovery`, `replayed_cache_writes`, `used_saved_prompt_artifact`, `used_current_renderer`, `operator_reset_seen`) and `mismatch_fields[]`. It must be empty on normal new seals. Renderer fallback intent is derived from `hash_origins.rendered_learning_context_sha256`, not duplicated in booleans.
- `recovery_attempts`: integer, default 0. Used only for `failed_recoverable`.
- `last_recovery_at`: ISO8601 timestamp or null. Used only for `failed_recoverable`.

Seal semantics:

- The event `.learning.lock` is shared by predictor and learner production paths. It is acquired before any production build-side sidecar creation, artifact write/unlink, read, recovery, SDK invocation, or write involving `learning/result.json`. While holding the event lock, code re-checks sealed `quality_event.json`, existing prediction source tuple, existing `learning/result.json`, recovery, SDK invocation, finalization, ticker/global writes, audit aggregation, and quality-event seal.
- Written atomically under event `.learning.lock` after learning validation, ticker/global appends, audit aggregation, and quality-event validation all succeed. `failed_recoverable` writes and `recovery_attempts`/`last_recovery_at` updates use the same atomic JSON helper.
- Only `status: sealed` counts as completion and provenance credit.
- Missing, unreadable, invalid, hash-mismatched, or `failed_recoverable` quality events force deterministic recovery or refusal.
- A rerun that sees sealed quality event refuses normal mutation. No `--force` path exists in v0.
- A rerun that sees `learning/result.json` but no sealed quality event enters deterministic recovery: validate sibling prediction/bundle/learning result, verify or compute hashes, re-run derived writes idempotently under event/ticker/global locks, and seal the same source hashes. Any mismatch produces `failed_recoverable` and `RECOVERY_REQUIRED`.
- Every failed deterministic recovery increments `recovery_attempts` and stamps `last_recovery_at`. A successful recovery resets `recovery_attempts` to 0 and flips status to `sealed`.
- `run_learner_for_quarter` skips recovery re-entry when `status=failed_recoverable` and persisted `recovery_attempts >= 3`, including after process restart, returning future `LearnerOutcome.SKIPPED_HUMAN_DECISION`. `learning_metrics.py --quality-report` lists these events under `human_decision_required_count`.

### Derived Libraries

`earnings-analysis/learnings/ticker/*.json` and `earnings-analysis/learnings/global.json` are caches:

- Upsert by event key remains idempotent.
- Cache rows are trusted only when their source event has canonical JSON artifacts and sealed quality event matching hashes.
- Missing-source rows remain renderable only as unproven context and never earn quality credit.
- Replay-check can rebuild expected cache state from sealed quality events and source-complete legacy triples.

### Dynamic Provenance Caps

At render/build/report time, derive required source files from `(source_ticker, quarter_label)`:

- `context_bundle.json`
- `context_bundle_rendered.txt`
- `prediction/result.json`
- `prediction/section_audit.json`
- allowlisted prompt sidecars listed in the saved bundle
- `learning/result.json`
- `learning/quality_event.json`

Artifact provenance is complete only when all required JSON artifacts, the full rendered prompt, and every explicitly allowlisted prompt sidecar exist, the quality event is sealed, and recorded hashes match source files. Human markdown outside the prompt allowlists never counts for provenance.

Row provenance is checked after artifact provenance and before render/tier/metric credit:

- Each live cache lesson row must match a canonical prompt-visible cache projection reconstructed from the source event's sealed `learning/result.json` plus `quality_event.learning_snapshot`, not only the lesson identity. The projection includes `lesson_id`, lesson body, normalized body hash or recomputed lesson-ID inputs, `mechanism`, `applies_when`, `invalid_if`, `evidence_refs`, scope, routing key, `source_ticker`, `quarter_label`, `source_filed_8k`, `source_pit_cutoff`, `parent_id`, refinement lineage, and emitted/global membership.
- Ticker quarter rows also bind the outer prompt-visible event context used by `build_learning_context` and `renderer/lessons.py`: `direction_correct`, `actual_daily_pct`, `predicted_direction`, `predicted_confidence_score`, `primary_driver_summary`, `primary_driver_category`, `what_worked`, `what_failed`, `data_lessons`, and `why`.
- Global rows also bind prompt-visible routing/display fields: `target_sector`, `related_tickers`, source sector when present, source ticker, quarter label, source filed time, source PIT cutoff, parent/refinement lineage, and canonical audit history after audit verification.
- For each live lesson before render/tier/metrics, build the expected PIT-visible audit set from sealed auditor events in `EventArtifactIndex`, keyed by `(parent_lesson_id, auditor_ticker, auditor_quarter_label)`. The live `audit_history` must have exact key-set equality plus payload equality with that expected set for both ticker and global lessons. Missing, extra, or mutated audits immediately fail audit provenance for the affected lesson; a deleted verified-misled audit cannot make a lesson look active/proven.
- Each live audit row payload must match the canonical audit payload from the auditor event's sealed quality event before it can affect tier/status/metrics: review/verdict, root cause, action, evidence summary/refs, comment, `was_cited`, PIT cutoff, and compatibility fields.
- Unknown or changed live-cache fields that are rendered, tier-relevant, metric-relevant, or audit-relevant are drift even if the lesson ID and body still match. Transient computed fields such as `_render_status`, `_render_audit_counts`, and a recomputed `learner_result_path` stay outside the stored-row projection and are derived only after row provenance passes.
- Rows or audits that fail membership, projection, or audit-set checks are treated as untrusted live drift for rendering and scoring immediately; they earn zero helped/misled/citation/tier credit and cannot make a lesson proven, risky, or retired. `--replay-check` still reports them as `extra_live_row`, `missing_live_row`, or `hash_drift`.
- `EventArtifactIndex` parses and caches per-event canonical prompt-visible row projections, emitted-lesson maps, audit-verdict maps, and expected PIT-visible audit sets once per event, reusing the full `prediction_source_tuple` hashes. It may store an in-memory canonical projection hash for each expected live row and audit set, but no durable row registry, audit registry, quarantine ledger, drift chain, or replay-wide lock is added.

Effects:

- Missing or mismatched source caps tier at `unproven`.
- Missing-source emitted lessons earn zero helped/misled/citation credit.
- Missing-source audits do not count for tier, risky/retired, citation precision, or metrics.
- Non-canonical live cache rows, prompt-visible field mutations, forged/mutated audits, and missing canonical audits fail row provenance even when their event artifacts are sealed.
- FCX Q4 emitted lessons and Q4 audits stay unproven/missing-provenance until source artifacts are restored and a quality event can be sealed.
- Runtime code uses a process-local `EventArtifactIndex` built once per `learning_metrics.py` invocation and reused by `--quality-report`, `--replay-check`, `--tournament`, and `--backfill-legacy`. The index maps `(source_ticker, quarter_label)` to canonical event paths plus one entry per `prediction_source_tuple` artifact: context bundle, full rendered prompt, prediction result, section audit, learning result, quality event, and every allowlisted prompt sidecar. Each entry carries path, mtime, size, and sha256. It is LRU-bounded at 4096 event entries and invalidates an event entry when any tuple artifact mtime or size changes.
- `build_learning_context` may build or receive the same process-local provenance index for a single predictor bundle build. It must not re-hash the same event artifacts once per lesson or audit.
- No durable provenance cache is allowed.

### Tiers Before Caps

Transient render tier replaces recency authority:

- `proven`: provenance complete, at least two verified positives from distinct `(auditor_ticker, auditor_quarter_label)` audit keys spanning at least two future quarter labels, and zero verified misled since latest refinement.
- `promising`: one verified positive, no verified misled, provenance complete.
- `unproven`: legacy, missing-source, neutral-only, insufficient evidence, or failed recovery.
- `risky`: any recent verified misled or repeated false-confirmation pattern.
- `retired/excluded`: dropped before caps.

Sort before caps by tier priority, then `source_pit_cutoff` descending, then deterministic tuple `(source_ticker, quarter_label, lesson_id)`. `attributed_at` is display metadata only.

### Minimal Concurrency

Lock order:

1. Event `.learning.lock`.
2. Ticker file locks in alphabetical ticker order.
3. Global lessons lock.

Rules:

- Same event learner invocations serialize on `.learning.lock`, and the lock starts before any `learning/result.json` read or write.
- Ticker file locks are acquired in alphabetical ticker-symbol order when multiple tickers are touched. The alphabetical ticker-lock rule includes ticker locks acquired by audit aggregation for parent lessons stored in other ticker libraries, not only the current event's ticker append. Code must never acquire these in reverse order.
- Ticker D22 collision scan and upsert happen inside ticker lock.
- Global D22 collision scan and upsert happen inside global lock.
- Audit aggregation upserts by exact audit key `(parent_lesson_id, auditor_ticker, auditor_quarter_label)` and replaces an existing audit for that key rather than appending a duplicate. Recovery re-application is therefore idempotent.
- Recovery uses the same lock order.
- No replay-wide lock in v0. `learning_metrics.py --replay-check --all` should run when learner workers are quiescent. It also uses a non-blocking `fcntl` probe on each event `.learning.lock`; a locked event, a `learning/result.json` without sealed quality event, or a `failed_recoverable` quality event reports `in_flight_or_recovery_required` and exits non-zero rather than storing drift state.
- `learning_metrics.py --replay-check --event` and `--replay-check --all` also exit non-zero on any cache-vs-canonical drift discovered by rebuilding from sealed quality events: `extra_live_row`, `missing_live_row`, or `hash_drift` between sealed event IDs/hashes and live ticker/global rows. Each drift event emits `LEARNER_ALERT status=replay_drift ticker=<T> quarter=<Q> reason=<extra_live_row|missing_live_row|hash_drift>` to stderr. No durable drift-block state is written.

### Performance and Scale Contract

Target corpus assumption for v0:

- 200 tickers.
- 4 quarterly cycles per year.
- 3-year hot retention in normal reports, or about 2,400 event directories.
- Up to 12 rendered lesson bodies per prediction after caps and up to 5 PIT-visible audits per lesson in hot-path tier checks.
- `learning_metrics.py --quality-report --all` and `--replay-check --all` may scan all hot-retention event directories once and build one `EventArtifactIndex`; they must not perform per-lesson full-corpus rescans.

Runtime budgets on a local SSD-class workstation:

- `build_learning_context` p95 under 500 ms on the synthetic 200-ticker fixture after warm process-local index setup; cold single-event build should remain under 2 seconds.
- `learning_metrics.py --quality-report --all` p95 under 30 seconds for the 2,400-event hot-retention fixture.
- `learning_metrics.py --replay-check --all` p95 under 60 seconds for the same fixture.
- If these budgets fail, implementation must first optimize single-pass indexing and in-memory hashing reuse. It must not add durable metrics caches, databases, services, drift chains, or quarantine ledgers.

## 8. Lesson and Prediction Quality Guarantees

Lesson-quality properties and enforcement:

| Property | Enforcement |
|---|---|
| Causal | Prompt and learner validator field floor; human review residual risk. |
| Future-verifiable | Deterministic `applies_when`/`invalid_if` fields plus future audit metrics. |
| Falsifiable | Validator requires invalidation condition length; metrics track verified misled/missed. |
| Decision-relevant | Learner prompt and report metrics: citation coverage, time-to-first-helped, no_call impact. |
| Evidence-backed | Deterministic evidence-ref resolution for emitted lessons, audits, and transfer proof. |
| Correctly scoped | Deterministic scope routing plus transfer proof; human semantic residual risk. |
| Non-generic | Prompt and report lint warnings; not a hard deterministic gate. |
| Non-case-specific | Prompt and report lint warnings; overly date/name-specific text is warning, not hard fail. |
| Reusable | Replay/report metrics: reuse rate, citation precision, helped/misled over future events. |
| Measurable | `quality_event.json` plus `learning_metrics.py` derive metrics. |

Prediction metrics:

- Primary: rolling Brier score over completed directional calls. For `long`/`short`, `p = confidence_score / 100`, outcome is 1 if direction was correct, 0 otherwise.
- `no_call` is reported beside Brier, not hidden from it. Every Brier table includes `call_count`, `no_call_count`, `total_completed_events`, no_call rate, and no_call usefulness. `no_call_usefulness` is the fraction of no_call events whose realized absolute daily return is below the midpoint of that event's absolute expected range; events without a parseable range fall into an `unknown_range` denominator bucket, not the numerator.
- Guardrails: directional accuracy, high-confidence wrong-call rate, no_call usefulness, citation precision/coverage, continual-learning trend, and near-clone blast-radius share.
- Blast-radius rule: no single lesson or near-clone cluster may account for more than 25% of verified misled cited outcomes in the rolling 50-event window; breach blocks promotion of that lesson family.
- Near-clone cluster key is deterministic in v0: start with `parent_id` lineage family when present; otherwise cluster by normalized lesson body 5-token-shingle Jaccard similarity >= 0.82 within the same scope/routing key. Normalization is lowercase ASCII, collapsed whitespace, and stripped trailing punctuation. The pairwise pass is local to PIT-visible lessons within one scope/routing key, bounded by the rendered/library bucket size, computed once per quality-report or promotion-gate invocation, and cached only in process. Exact-body hash alone is not an acceptable fallback because paraphrased near-clones must share blast-radius credit.
- No metric is allowed to claim guaranteed market accuracy. Metrics measure calibration, usefulness, and whether the learner loop is improving its own evidence discipline.

## 9. Migration and Backfill Plan

Migration classifies every existing corpus row exactly once:

1. Already-valid rows:
   - Future rows with sealed `quality_event.json` and matching source hashes.
   - Treated as canonical for replay/metrics.

2. Source-complete legacy rows:
   - Have the full `prediction_source_tuple` and `learning/result.json`, but no quality event.
   - Example: FCX Q3 appears source-complete from current reads.
   - Backfill path: validate prediction, bundle, and learning; run cross-file audit parity; compute source hashes; idempotently verify cache rows; write sealed `quality_event.json`.
   - Legacy rendered-hash policy: prefer a prediction-stamped `rendered_learning_context_sha256`; if absent, extract and hash the prior-lessons slice from saved `context_bundle_rendered.txt` using the byte span from `## Lessons To Label` through the following top-level `## ` heading; if that is unavailable, hash current-renderer output and set `hash_origins.rendered_learning_context_sha256 = computed_at_backfill_current_renderer`. Replay/report derive the weaker recovery-computed status from `hash_origins`.
   - Legacy prompt-source policy: if saved `context_bundle_rendered.txt`, `prediction/section_audit.json`, or allowlisted prompt sidecars exist, hash them as `computed_from_saved_prompt_artifact`; if allowlisted prompt sidecars are missing, classify as missing-source or failed-recovery rather than silently sealing a weaker tuple.
   - Legacy prediction v1 and learner v3 fields remain legacy; they can be sealed as historical source-complete but cannot mint `proven` credit unless future audits meet v4 verified criteria.

3. Missing-source rows:
   - Live cache rows whose source prediction/learning/quality-event artifacts are missing.
   - Example: FCX Q4 rows and Q4 audits.
   - Behavior: render as unproven/missing-provenance only, earn zero quality credit, and appear in `learning_metrics.py --quality-report` until artifacts are restored.
   - No durable quarantine ledger is added. The dynamic cap is recomputed every run.

4. Failed-recovery rows:
   - Have some artifacts, but validation/hash/cross-file checks fail.
   - Behavior: write or report `failed_recoverable`; refuse normal mutation; runbook requires artifact restoration or human decision.

5. Human-decision rows:
   - Malformed JSON, conflicting duplicate IDs, ambiguous parent/refinement lineage, existing v2-invalid prediction artifacts, incomplete save-only source tuples, or rows whose source cannot be reconstructed but may contain useful human knowledge.
   - Behavior: leave unproven by default. A human can restore missing artifacts, manually remove bad cache rows in a separate maintenance task, or accept indefinite unproven visibility. No automatic promotion.

Backfill order:

- Walk event directories by `(source_pit_cutoff, filed_8k, ticker, quarter_label, path)`.
- `learning_metrics.py --backfill-legacy` owns one-time deterministic sealing for source-complete triples. It writes `quality_event.json` only for source-complete legacy events, refuses missing-source and invocation-time PIT events, and emits the same migration summary counts as `--quality-report`.
- Never run a new LLM call during backfill.
- Refuse backfill for historical learners whose PIT source would be `invocation_time`.
- Produce migration summary counts: source-complete, missing-source, already-valid, failed-recovery, human-decision, legacy_backfill_recovery_computed_hashes, missing_source_unprovable_events, and human_decision_required.

Live FCX classification from current reads:

| Corpus item | Present source artifacts | Migration class | Resulting trust |
|---|---|---|---|
| FCX Q3_FY2025 prediction | `prediction/result.json`, `prediction/section_audit.json`, rendered bundle, and allowlisted related-filing sidecars exist; `lesson_labels` is empty legacy shape | Source-complete legacy candidate with Q3 learning | Can be backfilled/sealed; no v4 verified audit credit at birth. |
| FCX Q3_FY2025 learning | `learning/result.json` exists and is `attribution_result.v3` | Source-complete legacy candidate | Can seal a legacy quality event using legacy hash-origin policy. |
| FCX Q3-born lessons | Source Q3 prediction tuple, bundle, and learning exist | Source-complete legacy after backfill | Unproven/promising/proven depends only on future v4 verified audits; legacy Q4 audits do not count until their provenance is restored. |
| Q3 lesson audits with auditor Q4_FY2025 | Auditor Q4 `prediction/result.json` and `learning/result.json` are absent | Missing-source audit rows | Do not count for tier, risky/retired, citation precision, or quality credit. |
| FCX Q4_FY2025 ticker lessons | Q4 has bundle/rendered text and related filings, but no prediction/learning JSON | Missing-source rows | Renderable only as unproven/missing-provenance; unprovable until source artifacts are restored. |
| FCX Q4_FY2025 global lesson | Same Q4 source gap | Missing-source row | Same unproven/missing-provenance treatment. |
| FCX Q1_FY2026 prediction | Prediction exists; current output is all-sentinel with directional short | Human-decision / failed-validation under v2 | Fails future prediction v2 anti-lazy validation; not backfilled as a quality event without a valid learner/outcome path. |
| Any event with `learning/result.json` present, no `quality_event.json`, and deleted prediction or bundle | Incomplete sibling source set | Failed-recovery if source loss is detectable; otherwise human-decision | No quality credit; requires artifact restoration or manual corpus maintenance outside this design goal. |

## 10. Test Plan

Required future tests:

- Concurrency: same-event double learner run serializes; ticker and global D22 scans happen inside locks; concurrent recovery remains idempotent; lock order cannot deadlock when multiple tickers are touched.
- Lock order: event lock before ticker locks before global lock; tests assert reverse acquisition is not used, including audit aggregation that touches parent lessons stored in other ticker libraries.
- Malformed inputs: invalid quality event, unreadable JSON, wrong schema, bad hash, wrong status, malformed audit, non-object prediction/bundle, missing source IDs. Seal refuses when on-disk SHA-256 recompute disagrees with stamped `source_hashes`; tests assert replay/report/backfill derive event artifact paths through `get_learning_paths` rather than ad hoc string concatenation.
- Replay determinism: rebuild twice into temp dirs and compare byte-stable output; canonical sort handles same timestamp ties; extra live rows such as FCX Q4 report as missing-source drift; non-blocking event-lock probe reports in-flight events instead of false drift. Mutating one cached lesson body after seal makes `--replay-check` exit non-zero and emit `LEARNER_ALERT status=replay_drift ... reason=hash_drift`; deleting or adding a live cache row emits `missing_live_row` or `extra_live_row`.
- Migration/backfill: source-complete legacy Q3 seals; Q4 missing-source refuses backfill and caps unproven; failed-recovery produces deterministic status; legacy rendered-hash origin is stamped and counted.
- Provenance gaps: missing `prediction/result.json`, `context_bundle_rendered.txt`, `prediction/section_audit.json`, allowlisted prompt sidecar, `learning/result.json`, missing quality event, and hash mismatch all cap tier and audit credit.
- Metrics correctness: Brier, ECE/reliability bins, no_call usefulness, citation precision/coverage, per-lesson helped/misled, time-to-first-helped, bad-lesson half-life, near-clone blast radius.
- Near-clone blast radius: inject five paraphrased lessons with the same flawed mechanism and same scope/routing key but different wording/order; assert 5-token-shingle Jaccard clustering groups them into one family and blocks promotion when combined verified-misled cited share exceeds 25%.
- Scale/performance: synthetic 200-ticker, 2,400-event fixture asserts `build_learning_context`, `--quality-report --all`, and `--replay-check --all` stay within the Section 7 budgets; test fails if provenance hashing becomes per-lesson full-corpus rescans or the LRU exceeds 4096 entries. A sidecar mutation fixture proves replay/report detect an allowlisted prompt-sidecar hash drift while hashing each tuple artifact at most once per event per process.
- Tournament no-mutation: `--tournament` refuses production output paths and leaves `earnings-analysis/learnings` and production event dirs unchanged.
- Prediction anti-laziness: current Q1 all-sentinel/no-citation directional output fails v2 validation.
- Source immutability: production `--save`, `--predict`, `--predict --learn`, and live-trigger reruns after save-only source tuple creation, prediction finalization, or quality-event seal leave `context_bundle.json`, full `context_bundle_rendered.txt`, `prediction/result.json`, `prediction/section_audit.json`, and allowlisted prompt sidecar hashes and mtimes unchanged. Tests assert no builder-side sidecar write and no unlink path fires under a sealed event or an existing production prediction source tuple, and explicit experiment output remains the only fresh-predictor overwrite path.
- Save-time commitment: production `--save` writes `production_source_commitment` inside `context_bundle.json`; a later `--predict` must reject/no-op when `context_bundle_payload_sha256`, `full_rendered_prompt_sha256`, or any allowlisted sidecar hash no longer matches the commitment.
- Commitment schema closure: inject an unknown prompt-like field inside `production_source_commitment` after `--save`; production `--predict`, replay-check, and backfill must emit `LEARNER_ALERT status=prediction_source_incomplete` or equivalent, refuse to run the predictor/seal, and leave artifacts untouched.
- Canonicalization: reorder bundle dictionaries, include datetimes and Decimals, and verify the shared canonical bundle serialization helper produces byte-identical `context_bundle_payload_sha256` at save, predict validation, quality-event seal, replay-check, and backfill. Tests assert no call path uses `default=str` for this hash.
- Save-origin preservation: production `--save`, then `--predict`, then learner seal must preserve `stamped_at_save_finalize` for committed bundle payload, full rendered prompt, and allowlisted sidecar hashes in both `prediction_result.v2` and `learning/quality_event.json`.
- Prompt-source drift: mutate, delete, or rerun-overwrite full `context_bundle_rendered.txt`, `prediction/section_audit.json`, an allowlisted related filing sidecar, and an allowlisted prior learner sidecar after save/prediction/seal; replay-check or production rerun must fail/no-op visibly rather than silently sealing. For the after-save-only case, expected hashes come from `production_source_commitment` in `context_bundle.json`.
- Row provenance: add a live cache lesson row pointing at a source-complete sealed event, mutate a live lesson body, mutate prompt-visible fields while preserving lesson ID/body/source fields, forge an audit row, and delete a canonical audit row; `build_learning_context` must cap/exclude them before render, caps, and metrics, while `--replay-check` still emits `extra_live_row`, `missing_live_row`, or `hash_drift`.
- Prompt-visible projection drift: mutate `mechanism`, `applies_when`, `invalid_if`, `evidence_refs`, `primary_driver_summary`, `what_worked`, `what_failed`, `data_lessons`, `why`, `target_sector`, `related_tickers`, and audit comment/evidence refs on a sealed source-complete live row while preserving `lesson_id` and lesson body; the row must fail row provenance before it can affect the rendered prompt.
- Audit set equality: delete a verified-misled audit from a sealed source-complete live row while preserving every remaining audit row; the lesson must not become proven, avoid risky/retired status, alter prompt review markers, improve citation metrics, or lower near-clone blast-radius counts before replay-check.
- Invalid existing prediction: a v2-invalid existing `prediction/result.json` with no sealed quality event emits `LEARNER_ALERT status=prediction_invalid_existing`, increments `human_decision_required_count`, returns `SKIPPED_HUMAN_DECISION`, and does not overwrite source artifacts.
- Learner audit quality: missing root cause, incompatible review/root-cause/action, sentinel comments, bare retire, orphan refinement, duplicate refinement, missing transfer proof all reject.
- Tiering: verified `proven` outranks newer unproven; missing-source audits do not count; verified misled blocks proven until refinement.
- Recovery: crash after learning result, after ticker append, after global append, after audit aggregation, and during quality-event atomic seal all converge or report failed_recoverable without duplicate rows. ENOSPC/temp-write failure during quality-event seal leaves no trusted sealed event.
- Operational runbook: simulated provenance failure produces a human-readable action list with exact source event, affected lesson IDs, allowed recovery paths, exit code, and `LEARNER_ALERT` line. Simulated restored-artifact reset verifies `--reset-failed-recoverable` validates restored artifacts and sibling hashes before deletion, leaves the failed quality event intact on failed validation, deletes only a failed quality event under lock after successful validation, logs `LEARNER_OPERATOR_RESET`, and lets deterministic recovery restart from zero attempts without bypassing validation.

## 11. Operational Runbook

Normal unattended learner event:

1. Resolve production prediction and learning paths.
2. Before any production builder side effect, write, or unlink, acquire event `.learning.lock` and check `learning/quality_event.json`.
3. If the quality event is sealed, return `already_sealed` without touching bundle, prediction, learner, ticker, or global artifacts.
4. If a save-only source tuple exists without `prediction/result.json`, validate `production_source_commitment` in `context_bundle.json`, then reuse it for prediction or no-op for another `--save`; do not rebuild it.
5. If `prediction/result.json` already exists and no sealed quality event exists, validate and reuse the existing prediction source tuple instead of overwriting it. If validation fails, emit `LEARNER_ALERT status=prediction_invalid_existing`, return `SKIPPED_HUMAN_DECISION`, and wait for human action.
6. If no production source tuple exists, build/write the prediction bundle, allowlisted sidecars, stamp `production_source_commitment`, run the predictor, finalize prediction v2, and validate engagement evidence while holding the event lock through prediction finalization.
7. Run deterministic recovery if `learning/result.json` already exists without a sealed quality event; otherwise run learner only after outcome is available and PIT boundary is replayable.
8. Validate learner v4 and cross-file audit parity.
9. Append ticker/global cache rows under file locks.
10. Aggregate audits under the same lock discipline.
11. Validate and atomically seal `learning/quality_event.json`.
12. Run `learning_metrics.py --replay-check --event <event>` as a post-seal local check.

Daily or batch health:

- A local cron/systemd-user timer or equivalent operator scheduler runs `learning_metrics.py --quality-report --all` once per active trading day after the expected learner batch window.
- The report writes to stdout and appends one JSON line to `logs/learning_metrics_quality_YYYYMMDD.jsonl`. This log path is future implementation output, not created by this design goal.
- `learning_metrics.py --quality-report --all` exits non-zero when `failed_recoverable_count > 0`, `human_decision_required_count > 0`, or `blast_radius_breach_count > 0`.
- Both the orchestrator and `learning_metrics.py` emit one-line stderr alerts for human triage: `LEARNER_ALERT status=<state> ticker=<T> quarter=<Q> reason=<R>`.
- Run `learning_metrics.py --replay-check --all` only when workers are quiescent; if an event lock or incomplete event is detected, retry after backoff rather than recording durable drift state. If replay detects cache-vs-canonical drift against sealed quality events, it exits non-zero and emits `LEARNER_ALERT status=replay_drift ...`.
- Review counts for missing-source rows, failed-recoverable events, invalid existing predictions, incomplete save-only source tuples, all-sentinel prediction attempts, all-neutral audit batches, no_call usefulness, Brier trend, and blast-radius breaches.

Recovery/provenance failure:

- Missing source artifact: restore the full `prediction_source_tuple` plus `learning/result.json`, then run deterministic backfill/seal. If artifacts cannot be restored, leave row unproven; do not manually mark proven.
- Hash mismatch: stop normal mutation for that event, inspect whether artifact was edited, restore from backup or classify as failed-recovery.
- Prediction validation failure with existing artifacts: do not overwrite in unattended mode. The operator may manually remove `prediction/result.json` and `prediction/section_audit.json`; the next unattended `--predict` consumes the existing saved source tuple and writes a fresh prediction. If the saved source tuple itself is incomplete or wrong, the operator may remove the saved tuple and allow a new production build, or use explicit experiment output. This remains a human-decision class; no `--force` or `--reset-failed-prediction` path exists in v0.
- Failed recovery: deterministic recovery may retry until persisted `recovery_attempts >= 3`. At that point the event is counted under human-decision required, emits `LEARNER_ALERT`, and stays unproven until separately repaired.
- After a human restores source artifacts for a `failed_recoverable` event with `recovery_attempts >= 3`, the operator can run `learning_metrics.py --reset-failed-recoverable <event_path>`. The command acquires the event `.learning.lock`, verifies the event is still `failed_recoverable`, validates the restored source artifacts and sibling hashes first, then atomically deletes only `learning/quality_event.json`. If source artifacts still fail validation, it exits non-zero and leaves the failed quality event intact. On successful reset it appends `LEARNER_OPERATOR_RESET ticker=<T> quarter=<Q> attempts_cleared=<N>` to the existing JSONL quality log. The next orchestrator cycle or `--backfill-legacy` re-enters deterministic recovery with `recovery_attempts=0`. This is not a `--force` path: it cannot seal, promote, or bypass hash checks.
- Q4 FCX-style defect: no source artifacts means no quality credit. The row can remain visible as unproven context, but audits from that event do not count.
- Tournament or prompt changes: run tournament in experiment output only. Promotion requires Brier improvement or statistically meaningful no_call/calibration improvement without guardrail regression.

Operational integration:

- Current orchestrator integration point is `run_learner_for_quarter`, which already gates on prediction result and owns derived writes. Future implementation adds seal/recovery logic there without changing trigger or trade scope. Evidence: `scripts/earnings/earnings_orchestrator.py:1133`, `scripts/earnings/earnings_orchestrator.py:1199`, `scripts/earnings/earnings_orchestrator.py:1398`, `scripts/earnings/earnings_orchestrator.py:1415`.
- Planned trigger context may call the predictor/learner path, but this design only governs local learning memory and metrics. It does not add trade execution, position sizing, alert thresholds, or trigger selection.

## 12. Exact Future Change Plan from Current Code

Future edits, not made by this design goal:

1. `scripts/earnings/earnings_orchestrator.py`
   - Extend `validate_prediction_result` to v2 engagement, all-sentinel/no_call, and key-driver source-ID rules.
   - Extend bundle/save finalization to stamp `production_source_commitment` in `context_bundle.json` after rendered text and allowlisted prompt sidecars exist, using `context_bundle_payload_sha256` over bundle JSON excluding the commitment field.
   - Add one shared canonical bundle serialization helper for `context_bundle_payload_sha256`, reused by save, predict validation, quality-event seal, replay-check, and backfill.
   - Add strict validation and deterministic recomputation for the entire `production_source_commitment` object, rejecting any unknown key, wrong primitive type, unsorted sidecar path list, bad origin enum, or mismatched value before prediction or sealing.
   - Extend `finalize_prediction_result` to stamp or verify context, full rendered prompt, rendered-learning-context, section-audit, allowlisted prompt-sidecar, and lesson-set hashes from the committed production source tuple.
   - Add a production artifact immutability guard before `run_core_flow` can receive `related_filings_dir` and before `write_json`, `write_text`, `unlink`, predictor SDK output, or prediction finalization can touch `context_bundle.json`, `context_bundle_rendered.txt`, `prediction/result.json`, `prediction/section_audit.json`, allowlisted prompt sidecars, or `learning/result.json` in a production event directory. The guard acquires the event `.learning.lock`, exits no-op on sealed quality events, reuses an existing production prediction source tuple, handles save-only tuples, emits human-decision alerts for invalid existing predictions, and permits fresh predictor overwrites only in explicit experiment output.
   - Refuse historical learner mutation when `derive_learner_pit` returns `invocation_time`.
   - Use `_atomic_write_json` in `finalize_learning_result`.
   - Add `quality_event_path` and `learning_lock_path` from `get_learning_paths`.
   - Add event `.learning.lock` acquired before any production source-artifact build/write/unlink or `learning/result.json` read/write; add ticker file locks; move ticker/global D22 scans inside locks.
   - Make audit aggregation upsert by `(parent_lesson_id, auditor_ticker, auditor_quarter_label)` and acquire any cross-ticker parent library locks in alphabetical ticker order.
   - Add dynamic source provenance checks in `build_learning_context` and audit-tier predicates.
   - Add row-level canonical prompt-visible projection checks before rendering/tiering live cache rows or audit histories, using canonical emitted-lesson, row-projection, audit maps, and expected PIT-visible audit sets derived from sealed event artifacts.
   - Replace recency authority with quality-tier sort before caps.
   - Write and validate `learning/quality_event.json`, including hash origins, structured recovery notes, recovery attempts, and last recovery timestamp.
   - Add deterministic recovery for `learning/result.json` without sealed quality event.
   - Add non-blocking event-lock probe behavior for replay-check and report in-flight/recovery-required state.

2. `scripts/earnings/validate_learning.py`
   - Bump to `attribution_result.v4`.
   - Require root-cause enum and compatibility.
   - Reject bare retire.
   - Enforce refinement lineage and no-fork checks.
   - Add transfer proof fields for global observations.
   - Add audit comment sentinel/length floor for verified credit.

3. `scripts/earnings/renderer/lessons.py` and `_text_utils.py`
   - Render compact tier/provenance markers outside ordered lesson body.
   - Preserve body-only ordered lesson text and shared L numbering.

4. `.claude/skills/earnings-prediction/SKILL.md`
   - Add engagement fields, counter-thesis/no_call discipline, and confirmed-but-uncited rationale.

5. `.claude/skills/earnings-learner/SKILL.md`
   - Add root-cause compatibility, transfer proof, no bare retire, and evidence-backed refinement guidance.

6. `scripts/earnings/learning_metrics.py`
   - Add `--quality-report`, `--replay-check`, `--tournament`, `--backfill-legacy`, and `--reset-failed-recoverable`.
   - `--backfill-legacy` acquires the event `.learning.lock` before validating, writing, or sealing a legacy quality event, and uses the same event/ticker/global lock order as deterministic recovery.
   - Add process-local `EventArtifactIndex` reused across report/replay/tournament/backfill modes, LRU-bounded at 4096 event entries, indexing every `prediction_source_tuple` artifact plus canonical prompt-visible row projections, emitted-lesson maps, audit-verdict maps, and expected PIT-visible audit sets, and invalidated by any tuple artifact mtime/size change.
   - Add deterministic near-clone clustering for quality-report and promotion gates: parent lineage first, then normalized 5-token-shingle Jaccard >= 0.82 inside a scope/routing bucket. No persistent cluster registry.
   - Add fixed JSONL report output, non-zero exit-code contract, and `LEARNER_ALERT` stderr lines for failed recovery, invalid existing predictions, incomplete source tuples, human-decision-required, and blast-radius breaches.
   - Make replay-check exit non-zero and emit `LEARNER_ALERT status=replay_drift` for `extra_live_row`, `missing_live_row`, and `hash_drift` between sealed quality events and live derived caches.
   - Add `--reset-failed-recoverable <event_path>` as the only operator unstick path for repaired failed events; it validates restored sources before deleting only failed quality events under event lock, logs `LEARNER_OPERATOR_RESET`, and never bypasses validation or seals an event.
   - Keep it local/read-only by default; write only to stdout or explicit output paths.
   - Refuse tournament outputs under production learning libraries or production event dirs.

## 13. What Was Cut, Kept, Added, Deferred

Cut from Round 10:

- Mutation manifest.
- Drift block/head chain.
- Durable provenance quarantine ledger.
- Replay-wide lock as a routine primitive.
- Persistent per-lesson stats.
- Separate replay and report scripts.
- Renderer environment fingerprint.
- External service/database/dashboard/daemon.

Kept:

- Local Python and JSON.
- PIT filtering and same-quarter guard.
- D19 cross-file audit parity.
- D20 body-only lesson labels.
- Evidence-source grounding.
- Structured lesson fields.
- Deterministic lesson IDs and D22 collision concept.
- Atomic JSON writes where needed.
- Brier as primary prediction-quality metric.

Added:

- One sealed `quality_event.json`.
- Prediction engagement source IDs and key-driver source IDs.
- Learner root-cause compatibility and refinement lineage.
- Dynamic provenance caps for source gaps.
- Quality tiers before caps.
- One `learning_metrics.py` for replay/report/tournament/backfill/reset plus a bounded in-memory `EventArtifactIndex`.
- Migration classes and runbook.
- Operator-visible JSONL report output, exit-code contract, and `LEARNER_ALERT` line format.
- Production source-artifact immutability guard before predictor/bundle writes or unlinks.
- Single `prediction_source_tuple` covering full rendered prompt, section audit, and allowlisted prompt sidecars.

Deferred:

- Tamper-proof external anchors.
- Durable quarantine override ledger.
- Synthetic hindsight/back-attribution.
- Automatic builder creation from data lessons.
- Trade execution or trigger expansion.

## 14. Judge Findings and Round-by-Round Consensus Log

Round 0:

- Objective read from `/tmp/eventmarketdb_round12_operational_hardening_goal_prompt.txt`.
- Source plans read: `.claude/plans/LearnerLoopPlan_SimplifiedQuality.md` and `.claude/plans/LearnerLoopPlan.md`.
- Direct code/corpus evidence re-read after compaction: orchestrator, validation, renderer, prediction skill, learner skill, FCX Q3/Q4/Q1 files, file list, and status.
- Claude Opus 4.7 smoke test returned `CLAUDE_47_OK`.
- This draft creates the initial hardened target for Round 1 judging.

Round 1:

- Judge A first sandbox command failed with `FailedToOpenSocket`; the same stable command was rerun outside the sandbox. First successful A output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C4 D5 E5 F5 G4 H5 I4 J5 K4 L4 M5 N4. Blockers: failed-recoverable retry loop, deterministic near-clone definition, legacy hash origin, operator scheduling/alert/backpressure, cross-ticker audit lock order and audit upsert key, replay-check event-lock probe, provenance scale bounds.
- Judge B first sandbox command failed with `FailedToOpenSocket`; the same stable command was rerun outside the sandbox. First successful B output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict REJECT. Scores: A5 B5 C5 D5 E5 F5 G5 H5 I5 J5 K4 L4 M5 N5. Blockers: scale/cache bounds and live FCX row classification. Useful malformed-output findings also flagged cross-ticker audit locks, `--backfill-legacy` ownership, and report exit/log contracts; those were incorporated because they overlap A/C/D findings.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A5 B5 C4 D5 E5 F5 G4 H5 I5 J5 K4 L5 M5 N4. Blockers: event lock must start before SDK writes `learning/result.json`; batch metrics/replay need a bounded event-artifact index.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A5 B5 C5 D5 E5 F5 G5 H5 I5 J5 K4 L5 M4 N5. Blockers: concrete 200-ticker scale contract and synthetic performance test.
- Round 1 synthesis added: pre-SDK event locking; quality-event recovery attempts and last recovery timestamp; `SKIPPED_HUMAN_DECISION`; deterministic near-clone cluster key; legacy hash-origin and saved-rendered-slice policy; `EventArtifactIndex` with 4096-entry LRU; performance budgets; live FCX classification table; `--backfill-legacy`; non-blocking event-lock probe; audit upsert key; cross-ticker audit lock ordering; JSONL report path, non-zero exit contract, and `LEARNER_ALERT` stderr format.
- Round 1 is not a saturation round.

Round 2:

- Judge A first Round 2 output was malformed because it included prose and fenced JSON; one JSON-only retry produced well-formed JSON. Verdict REJECT. Scores: A5 B5 C5 D5 E5 F5 G5 H5 I4 J5 K5 L5 M5 N5. Blocker: `near_clone_mode: exact_hash_only` would let paraphrased bad lessons avoid the 25% blast-radius cap.
- Judge B first Round 2 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It warned against unnecessary Round 10 machinery and accepted the one-artifact/one-tool shape.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It verified pre-SDK event locking, failed-recoverable bounding, EventArtifactIndex, legacy hash origins, FCX classification, audit upsert/lock order, replay in-flight detection, and learning_metrics surfaces.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It verified Brier/no_call/citation metrics, missing-source credit caps, legacy hash origins, deterministic near-clone direction, and scale budgets.
- Round 2 synthesis removed the exact-hash-only near-clone fallback and made deterministic 5-token-shingle Jaccard clustering required in v0. It also clarified that `recovery_attempts >= 3` is persisted across restarts and added `learning_metrics.py --reset-failed-recoverable <event_path>` as the under-lock operator reset path for repaired failed events, because the malformed A output exposed a real unstick gap even though the valid retry did not keep it as a blocker.
- Round 2 is not a saturation round because Judge A rejected.

Round 3:

- Judge A, Claude Opus 4.7, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C5 D5 E5 F5 G5 H5 I5 J5 K5 L5 M5 N5. Blocker: replay-check had detection for cache-vs-canonical drift but no explicit non-zero exit code or `LEARNER_ALERT` for `extra_live_row`, `missing_live_row`, or `hash_drift`.
- Judge B, Claude Opus 4.7, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It found no remaining minimalism cuts and warned against Round 10 machinery.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It verified the near-clone and failed-recoverable reset fixes.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It accepted the metrics, FCX classification, no_call/citation/Brier, and scale surfaces.
- Round 3 synthesis added explicit replay-check non-zero exit and `LEARNER_ALERT status=replay_drift` semantics for `extra_live_row`, `missing_live_row`, and `hash_drift`, plus a matching test.
- Round 3 is not a saturation round because Judge A rejected.

Round 4:

- Judge A, Claude Opus 4.7 JSON-only retry, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It found no blocker, but noted two operational nits: reset should validate restored sources before deleting a failed quality event, and backfill should explicitly acquire the event `.learning.lock`.
- Judge B first Round 4 output was malformed because it included prose and fenced JSON, but it identified a real minimalism cut: `provenance_inputs` duplicated `source_hashes` plus paths derived from `event_identity`. The plan removed `provenance_inputs`, made seal-time hash recompute the validation step, and added a test that path resolution flows through `get_learning_paths`.
- Judge B JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It accepted the `provenance_inputs` cut and found no new simplification opportunity.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It verified replay-drift exit/alert semantics without durable drift state.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It verified replay-drift, near-clone, no_call/citation/Brier, missing-source, and scale surfaces.
- Round 4 is not counted as saturation because accepted nit-level findings changed the plan after the final judge reads. The next clean round can become the first saturation round.

Round 5:

- Judge A first Round 5 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It attacked lazy prediction, force reset, cross-ticker locks, failed recovery, PIT fallback, replay drift, near-clone blast radius, FCX missing-source credit, scale, retire mutation, and tournament pollution.
- Judge B first Round 5 output was malformed because it included prose before JSON; it flagged the two `recovery_notes` rendered-hash booleans as derivable from `hash_origins`. One JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. The malformed-output simplification was still incorporated by deleting the booleans.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C4 D5 E5 F5 G4 H5 I5 J5 K5 L5 M4 N4. Blocker: the immutability guard started at learner mutation, while current production `--save`/`--predict` can write bundle artifacts and unlink prediction artifacts before checking a sealed quality event or existing prediction tuple.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It attacked FCX missing-source rows/audits, Q1 all-sentinel directional prediction, near-clone paraphrases, 200-ticker scale, and optional JSONL configurability.
- Round 5 synthesis added the production artifact immutability guard before any production write/unlink of bundle, rendered bundle, prediction, section audit, or learner artifacts; it also added rerun tests and updated the runbook/future-change checklist. Round 5 is not a saturation round because Judge C rejected and the plan changed afterward.

Round 6:

- Judge A first Round 6 output was malformed because it included prose and fenced JSON; it flagged an existing v2-invalid prediction stuck behind the immutability guard with no alert/counter/operator path. One JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. The malformed-output finding was still incorporated because it exposed a real human-decision gap.
- Judge B first Round 6 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It tried to cut hash origins, recovery notes, reset, migration classes, EventArtifactIndex bounds, and alert formats, and found no minimalism cut.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C4 D4 E5 F5 G4 H4 I5 J5 K5 L4 M4 N4. Blockers: protected source tuple omitted the full rendered prompt, section audit, and prompt-readable related filing sidecars; save-only production bundles could still be overwritten before prediction existed.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It accepted the Round 5 artifact immutability guard and re-attacked FCX missing-source, Q1 all-sentinel, near-clone, and scale surfaces.
- Round 6 synthesis defined `prediction_source_tuple`, moved the guard before builder sidecar creation, added full rendered prompt/section audit/allowlisted prompt-sidecar hashes, covered save-only source tuples, and added invalid-existing-prediction human-decision handling. Round 6 is not a saturation round because Judge C rejected and the plan changed afterward.

Round 7:

- Judge A first Round 7 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It attacked save/predict tuple drift, lazy predictions, near-clones, failed recovery, cross-ticker locks, replay drift, and tournament mutation.
- Judge B first Round 7 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It tried to cut the Round 6 source-tuple hashes, hash origins, recovery notes, reset path, and EventArtifactIndex, and accepted the minimal shape.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C4 D5 E5 F5 G4 H4 I5 J5 K5 L5 M4 N4. Blocker: save-only tuples had no authoritative save-time hash commitment before prediction or quality event existed.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A5 B5 C5 D5 E5 F5 G5 H5 I5 J5 K4 L5 M4 N5. Blocker: EventArtifactIndex still covered only the old source JSON set instead of the full `prediction_source_tuple`.
- Round 7 synthesis added `production_source_commitment` inside `context_bundle.json`, required prediction/quality-event hashes to verify that commitment, widened `EventArtifactIndex` to every tuple artifact, and added hash-once sidecar drift tests. Round 7 is not a saturation round because Judges C and D rejected and the plan changed afterward.

Round 8:

- Judge A, Claude Opus 4.7, produced well-formed JSON with prose before it. Verdict REJECT. Scores: A4 B5 C5 D5 E5 F5 G5 H5 I5 J5 K5 L5 M5 N5. Blocker: `context_bundle_payload_sha256` needed an exact canonical JSON serialization routine because current `_atomic_write_json` does not sort keys.
- Judge B, Claude Opus 4.7, produced well-formed JSON with prose/fence before it. Verdict ACCEPT. Scores: all A-N 5/5. It accepted `production_source_commitment` and full-tuple `EventArtifactIndex` as minimal, and warned against splitting the commitment into a new artifact.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C5 D5 E5 F5 G4 H4 I5 J5 K5 L4 M4 N5. Blocker: `production_source_commitment` used `stamped_at_save_finalize`, but quality-event `hash_origins` did not allow that origin, so save-time authority could be erased later.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It accepted the save-time commitment and full-tuple EventArtifactIndex scale fix.
- Round 8 synthesis pinned canonical bundle serialization, added `stamped_at_save_finalize` to `hash_origins`, required origin preservation through prediction and quality-event seal, and added matching canonicalization/origin tests. Round 8 is not a saturation round because Judges A and C rejected and the plan changed afterward.

Round 9:

- Judge A first Round 9 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It attacked save-time commitment, canonicalization, hash origins, failed-recoverable reset, cross-ticker locks, invalid predictions, FCX missing-source rows, near-clones, scale, and tournament mutation.
- Judge B first Round 9 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It tried to cut source hashes, section audit hashing, save-origin preservation, reset, hash origins, EventArtifactIndex bounds, replay alerts, and tests; every cut reopened a named guarantee.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked save-only replay, canonicalization, `stamped_at_save_finalize`, prompt-source drift, lazy prediction, missing-source rows, recovery loops, locks, replay drift, near-clones, tournament mutation, and scale.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked FCX missing-source rows, save-only drift, full tuple coverage, canonical serialization, near-clone blast radius, and 200-ticker scale.
- Round 9 is saturation round 1: all four judges accepted, every rubric A-N scored 5/5, no non-nit findings were added, no new failure modes were found, and no simplification opportunity remained. Completion still requires one more consecutive saturation round with no plan changes.

Round 10:

- Judge A first Round 10 output was malformed because it included prose and fenced JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It attacked commitment placement, canonicalization, hash origins, reset, recovery attempts, anti-lazy validation, replay probes, locks, audit upsert keys, near-clones, prompt-sidecar hashing, invalid predictions, backfill, tournament, and operational alerts.
- Judge B first Round 10 output was malformed because it included prose before JSON; one JSON-only retry produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It tried to cut canonical bundle serialization, save-origin preservation, full-tuple indexing, section-audit hashing, reset, recovery attempts, human-decision outcomes, near-clone clustering, cross-ticker locks, and report exit codes.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B4 C5 D5 E5 F5 G4 H4 I5 J5 K5 L5 M4 N5. Blocker: `production_source_commitment` was excluded from `context_bundle_payload_sha256` but remained prompt-visible inside `BUNDLE_PATH`; without exact-schema validation and deterministic recomputation of the commitment object, unknown prompt-like keys could bypass the payload hash.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It accepted canonicalization, save-origin preservation, full-tuple provenance, FCX handling, recovery, and 200-ticker scale.
- Round 10 synthesis made `production_source_commitment` an exact-schema object, required recomputing the whole expected commitment on save-only no-op, predict, seal, replay, and backfill paths, and added an unknown-key injection test. Round 10 is not a saturation round because Judge C rejected and the plan changed afterward. The previous Round 9 saturation candidate no longer forms a consecutive pair with the final revised plan.

Round 11:

- Judge A, Claude Opus 4.7, first output was malformed because it included prose before JSON. The embedded JSON verdict was ACCEPT with all A-N scores at 5/5. It attacked exact-schema commitment recomputation, canonical bundle serialization, stamped save-origin preservation, full-tuple sidecar hashing, lazy predictions, missing-source rows, near-clones, failed recovery, lock order, and replay-drift alerts, and found no blocker.
- Judge B, Claude Opus 4.7, first output was malformed because it included prose before JSON. The embedded JSON verdict was ACCEPT with all A-N scores at 5/5. It tried to cut the commitment artifact, rendered-learning-context hash, hash origins, reset path, recovery attempts, LRU bound, ticker-lock order, tournament mode, sidecar hashes, and section-audit hash; each cut reopened a named guarantee.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C5 D5 E4 F5 G4 H5 I4 J5 K5 L5 M4 N4. Blocker: dynamic provenance was artifact-level but not row-level, so a fabricated or mutated live cache lesson or audit could point at a valid sealed source event and inherit trust before replay-check was run.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It accepted exact-schema commitment closure, canonical serialization, save-origin preservation, full-tuple EventArtifactIndex, FCX handling, recovery, and 200-ticker scale.
- Round 11 synthesis added row-level canonical membership checks before rendering, tiering, and metrics. Live lesson rows must match sealed event emitted-lesson membership and deterministic lesson inputs; audit rows must match canonical audit keys and payloads from sealed auditor events; `EventArtifactIndex` now parses per-event emitted-lesson and audit-verdict maps once per process. Round 11 is not a saturation round because Judge C rejected and the plan changed afterward.

Round 12:

- Judge A, Claude Opus 4.7, was launched but produced a zero-byte output after an extended wait and was stopped after Judge C had already produced a blocking rejection. No Round 12 Judge A verdict is counted.
- Judge B, Claude Opus 4.7, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It tried to cut row-level canonical membership, the in-bundle commitment, canonical serialization, save-origin distinctions, EventArtifactIndex bounds, reset, lock tiers, section-audit hashing, sidecar hashing, recovery attempts, backfill mode, alert format, event-lock probe, and separate hash-path tests; each cut reopened a named guarantee.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C5 D5 E4 F5 G4 H4 I4 J5 K5 L4 M4 N5. Blocker: the Round 11 row-level provenance fix bound lesson identity and membership but not the full prompt-visible live-cache payload. A row could preserve canonical lesson ID, body, routing, ticker, quarter, and PIT cutoff while mutating `mechanism`, `applies_when`, `invalid_if`, `evidence_refs`, ticker context fields such as `data_lessons` and `why`, global routing display fields, or audit text before rendering.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked row-level cache forgery, FCX missing-source rows, Q1 lazy prediction, commitment injection, canonical serialization, save-origin preservation, full-tuple scale, and prior overengineering cuts.
- Round 12 synthesis expands row provenance from identity/membership to a canonical prompt-visible cache projection reconstructed from sealed event artifacts. The projection binds every stored field that can affect rendering, tiering, metrics, or audit credit while keeping transient render fields derived in memory. `EventArtifactIndex` may cache per-row canonical projection hashes in process only. Round 12 is not a saturation round because Judge C rejected and the plan changed afterward.

Round 13:

- Judge A, Claude Opus 4.7, was launched but produced a zero-byte output after an extended wait and was stopped after Judge D had already produced a blocking rejection. No Round 13 Judge A verdict is counted.
- Judge B, Claude Opus 4.7, produced malformed output because it included prose and a fenced JSON object. The embedded JSON verdict was ACCEPT with all A-N scores at 5/5. It tried to cut the save-time commitment, full-tuple EventArtifactIndex, prompt-visible row projection, hash-origin distinctions, rendered-learning-context hash, section-audit hash, per-ticker locks, reset path, alerts, engagement validation, sidecar allowlists, near-clone clustering, and LRU bound; each cut reopened a named guarantee.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked prompt-visible live-cache row projection against current renderer fields, FCX missing-source rows/audits, Q1 lazy prediction, commitment injection, canonical serialization, full-tuple EventArtifactIndex scale, and prior simplification cuts.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict REJECT. Scores: A4 B5 C5 D5 E4 F5 G5 H5 I4 J5 K5 L5 M4 N5. Blocker: row-level provenance checked existing live audit rows but did not explicitly require exact set equality against every PIT-visible canonical audit expected from sealed auditor events. Deleting a canonical verified-misled audit could suppress risky status, prompt review markers, metrics, and blast-radius counts until replay-check.
- Round 13 synthesis adds exact PIT-visible audit-set equality before render, tiering, metrics, and prompt review markers. For each live lesson, `EventArtifactIndex` derives the expected audit key set and payloads from sealed auditor events; live `audit_history` must match exactly. Missing, extra, or mutated audits fail audit provenance immediately and remain replay-check drift. Round 13 is not a saturation round because Judge D rejected and the plan changed afterward.

Round 14:

- Judge A, Claude Opus 4.7, produced well-formed JSON from an inline no-tool prompt after two path-reading attempts stalled with zero-byte outputs. Verdict ACCEPT. Scores: all A-N 5/5. It attacked lazy predictions, forged/mutated live rows, prompt-visible field mutations, forged/deleted audits, failed auditor seals, commitment injection, canonical serialization drift, save-origin erasure, prompt/section-audit/sidecar drift, EventArtifactIndex scale, cross-ticker deadlocks, invalid existing predictions, save-only drift, failed recovery loops, replay drift, near-clones, tournament mutation, and backfill source gaps.
- Judge B, Claude Opus 4.7, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked audit-set equality, prompt-visible projection drift, exact-schema commitment closure, canonical serialization, save-origin preservation, full-tuple EventArtifactIndex, immutability guard placement, lock order, recovery bounding, near-clone clustering, scale budgets, and migration classification; no cut survived without reopening a prior guarantee.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked the audit-set-equality fix against live FCX-style audit rows, prompt-visible renderer fields, save-only source drift, commitment injection, canonical serialization, save-origin preservation, full-tuple scale, and prior simplification cuts.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked deleted verified-misled audits, forged/extra/mutated audits, duplicate audit keys, prompt-visible row projections, row-level membership, commitment exact-schema closure, canonical serialization, save-origin preservation, full-tuple EventArtifactIndex, reset, alerts, sidecars, and near-clones.
- Round 14 is saturation round 1 for the Round 13 revised design: all four judges accepted, every rubric A-N scored 5/5, no non-nit findings were added, no new failure modes were found, and no simplification opportunity remained. Completion still requires one more consecutive clean saturation round with no design changes.

Round 15:

- Judge A, Claude Opus 4.7, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked fabricated live rows, deleted verified-misled audits, forged/mutated audits, commitment unknown-key injection, canonical serialization drift, save-origin erasure, prompt/section-audit/sidecar drift, EventArtifactIndex scale, lazy all-sentinel predictions, failed recovery loops, cross-ticker deadlocks, production overwrite paths, legacy save-only tuples, near-clones, tournament mutation, replay drift, historical PIT fallback, and operator alerts.
- Judge B, Claude Opus 4.7, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It tried to cut canonical serialization, save-time commitment, exact-schema commitment closure, save-origin preservation, full-tuple EventArtifactIndex, row-level projection, prompt-visible field binding, exact audit-set equality, reset, recovery attempts, LRU bound, near-clone clustering, lock order, replay alerts, hash-origin distinctions, sidecar hashing, section-audit hash, event-lock probe, migration classes, backfill locks, and test depth; each cut reopened a prior named failure.
- Judge C, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked deleted canonical audits, prompt-visible cache projection drift, row-level membership forgery, commitment injection, canonical serialization, save-origin preservation, full-tuple EventArtifactIndex scope and scale, and prior simplification cuts.
- Judge D, Codex GPT-5.5 xhigh, produced well-formed JSON. Verdict ACCEPT. Scores: all A-N 5/5. It re-attacked exact PIT-visible audit-set equality, canonical prompt-visible projections, row-level membership, commitment exact-schema closure, canonical serialization, save-origin preservation, full-tuple EventArtifactIndex, FCX-style missing-source rows, Q1-style all-sentinel predictions, sidecar hashing, section-audit hashing, reset, recovery attempts, hash origins, and near-clones.
- Round 15 is saturation round 2 and confirms Round 14 without design changes: all four judges accepted, every rubric A-N scored 5/5, no non-nit findings were added, no new failure modes were found, and no simplification opportunity remained.

## 15. Saturation Evidence

Achieved after the Round 13 revision.

Consecutive clean rounds: Round 14 and Round 15 are saturation rounds 1 and 2 for the revised plan, with no design changes between them.

Required before completion:

- At least five judge rounds: satisfied by Rounds 1-10.
- Two consecutive saturation rounds: satisfied by Rounds 14 and 15.
- Every judge scores every rubric item A-N as 5/5: satisfied in Rounds 14 and 15.
- Every judge accepts: satisfied in Rounds 14 and 15.
- No non-nit findings, no new failure modes, no new simplification opportunities: satisfied in Rounds 14 and 15.
- Every judge states what it attacked or tried to cut and why nothing material remains: satisfied in Rounds 14 and 15.

## 16. Final Reliability, Quality, and Minimalism Check

Current status: complete.

The final design preserves Round 11 simplification while hardening unattended operation. Completion evidence now maps to the objective:

- Canonical event artifacts: `events/{quarter}/learning/quality_event.json` plus the protected `prediction_source_tuple` are the canonical source set.
- Derived caches: `earnings-analysis/learnings/*.json` remains derived and must match sealed event projections, including exact PIT-visible audit sets.
- One local tool: `scripts/earnings/learning_metrics.py` owns replay-check, quality-report, tournament, backfill, and failed-recovery reset.
- Round 10 machinery remains cut: no mutation manifest, drift block/head chain, durable quarantine ledger, database, service, dashboard, daemon, trade scope, or routine replay-wide lock.
- Operational guarantees are covered: replayability, PIT discipline, idempotency, engagement evidence, quality differentiation, scope proof, recovery, observability, bounded blast radius, minimalism, 200-ticker scale, migration completeness, test depth, and runbook integration.
- Saturation is real: at least five judge rounds were run, and Rounds 14 and 15 are consecutive all-5 ACCEPT saturation rounds across two Claude Opus 4.7 judges and two Codex judges per round.
