# EventMarketDB Learner Loop - Lesson Intelligence Minimal

## 0. Status, Round, and Pruning Summary

Status: COMPLETE
Round: 19 complete after two consecutive clean saturation rounds
Last updated: 2026-05-11

Finality pre-checks:

- PASS: `.claude/plans/LearnerLoopPlan_LessonIntelligence.md` reports `Status: COMPLETE` and `Round: 14 complete after consecutive saturation` at lines 5-6.
- PASS: `.claude/plans/LearnerLoopPlan_OperationalHardening.md` reports `Status: complete operational hardening plan` and `Round: 15 complete after consecutive saturation` at lines 3-4.

Allowed-artifact guardrail: this goal edits only this file plus temporary judge files under `/tmp`. It does not edit production code, live corpus files, prompt skill files, or existing plans.

Headline pruning result, completed after Round 19: the finalized LessonIntelligence v0 is strictly reduced by cutting stored `counter_thesis`, deferring `magnitude_bucket`, merging `macro_subtype` into `scope.routing_key`, deriving `transfer_state`, `transfer_basis`, transfer origin/destination fields, conflict handling, and routing cap/bucket report fields, merging candidate-transfer machinery into ordinary scoped lesson birth plus bounded-transfer proof from candidate scope, sealed auditor event identity, lineage, and transfer refs, making Brier/lift/statistical gates report-only until thresholds, deriving several prompt/validator fields instead of storing them, narrowing enums, deferring predicate overrides, and merging the reset utility into `learning_metrics.py`.

Source/corpus drift snapshot captured during this goal:

| Path | Size | Mtime epoch |
|---|---:|---:|
| `.claude/plans/LearnerLoopPlan_LessonIntelligence.md` | 134901 | 1778526437 |
| `.claude/plans/LearnerLoopPlan_OperationalHardening.md` | 109678 | 1778518284 |
| `.claude/plans/lessons-lifecycle-playground.html` | 157666 | 1778241110 |
| `scripts/earnings/earnings_orchestrator.py` | 184712 | 1778077720 |
| `scripts/earnings/validate_learning.py` | 30511 | 1777902243 |
| `scripts/earnings/renderer/lessons.py` | 12847 | 1777906264 |
| `scripts/earnings/_text_utils.py` | 3717 | 1777910170 |
| `.claude/skills/earnings-prediction/SKILL.md` | 22297 | 1778253165 |
| `.claude/skills/earnings-learner/SKILL.md` | 26572 | 1778250654 |
| `earnings-analysis/learnings/global.json` | 6998 | 1777992410 |
| `earnings-analysis/learnings/ticker/FCX.json` | 21143 | 1777992410 |
| `earnings-analysis/Companies/FCX/events/Q3_FY2025` | 4096 | 1777990376 |
| `earnings-analysis/Companies/FCX/events/Q4_FY2025` | 4096 | 1778077515 |
| `earnings-analysis/Companies/FCX/events/Q1_FY2026` | 4096 | 1778075992 |

Completion is not claimed until at least three rounds run, two consecutive saturation rounds are clean, all four judges accept with all rubric scores 5/5, malformed judge outputs are cleanly retried or recorded, and the final audit in Section 16 passes.

## 1. Baseline Inventory From Final LessonIntelligence

The finalized LessonIntelligence plan introduced or preserved these significant mechanisms on top of current code and operational hardening:

| Mechanism | Final input evidence | Baseline role |
|---|---|---|
| Operational hardening substrate: `quality_event.json`, source tuple, locks, derived caches, replay/report, alerts | LessonIntelligence lines 101-122 and OperationalHardening lines 15-18, 251-304, 363-380 | Non-cuttable Round 12 floor. |
| `lesson_hypothesis.v1` inside future `attribution_result.v4` and derived rows | LessonIntelligence lines 192-209 | Formula-like lesson object. |
| `mechanism_chain` four fields | LessonIntelligence lines 198-199 | Prevents vague story lessons. |
| Structured `applies_when[]` and `invalid_if[]` predicates | LessonIntelligence lines 200-201, 215-237 | Deterministic applicability. |
| `expected_effect` with `direction_effect`, `confidence_delta_points`, and `magnitude_bucket` | LessonIntelligence lines 202-212 | Direction/confidence/magnitude utility. |
| `scope.kind`, `routing_key`, `macro_subtype`, `transfer_state` | LessonIntelligence lines 207-208 | Scope and transfer routing. |
| `lineage` fields | LessonIntelligence line 209 | Refinement/supersession. |
| Deterministic applicability evaluator and override protocol | LessonIntelligence lines 240-267 | One evaluator for render, validation, audit, replay, novice tests. |
| Compact render block and quality-before-recency ranker | LessonIntelligence lines 269-287 | Keeps lessons visible only when useful. |
| Auto-derived potential conflict note plus predictor `conflict_handling` | LessonIntelligence lines 277 and 476 | Forces no_call for unresolved high-quality conflicts. |
| Derived authority stats: helped/misled/outweighed, citation precision, applicability precision/recall, transfer precision/recall | LessonIntelligence lines 289-308 | Usefulness metrics. |
| Derived lifecycle tiers: candidate/proven/dormant/excluded plus warnings | LessonIntelligence lines 310-318 | Replace active/watch/retired. |
| Birth, promotion, de-emphasis, dormancy, refinement, exclusion rules | LessonIntelligence lines 320-376 | Lifecycle authority. |
| Candidate-transfer machinery, `broaden_candidate`, `transfer_basis`, transfer pools | LessonIntelligence lines 377-430 | Avoid overbroad promotion and find useful transfer. |
| `prediction_result.v2` hashes, source-family/S10 classification, per-lesson traces, influence enum | LessonIntelligence lines 431-484 | Predictor engagement and anti-lazy behavior. |
| Top-level `counter_thesis` | LessonIntelligence lines 441-444 | Opposing directional evidence. |
| `attribution_result.v4` audit fields, `audit_outcome`, `routing_audit`, `routing_audit_detail`, action enum | LessonIntelligence lines 485-532 | Structured learner evidence. |
| Directional Brier, no_call, ECE/calibration, baseline comparator, citation/applicability/transfer metrics | LessonIntelligence lines 534-570 | Quality and non-regression measurement. |
| `learning_metrics.py` with replay, report, backfill, and reset utility | LessonIntelligence lines 759-798 | One local operational tool plus a tiny sibling reset utility in the finalized plan. |
| PT1-PT9 test plan | LessonIntelligence lines 799-890 | Passing lesson-quality gates. |

Current implementation baseline, from fresh reads in this goal:

- `build_prediction_bundle` adds `learning_context` and `evidence_source_catalog`, but a non-assertion learning-context failure falls back to empty lessons (`scripts/earnings/earnings_orchestrator.py:196`, `scripts/earnings/earnings_orchestrator.py:258`, `scripts/earnings/earnings_orchestrator.py:269`, `scripts/earnings/earnings_orchestrator.py:280`).
- Prediction validation is v1-shaped lesson-label validation: labels are `confirmed/contradicted/irrelevant`, body-position matching is enforced, confirmed-only lesson citations are enforced, and source IDs resolve against the catalog (`scripts/earnings/earnings_orchestrator.py:747`, `scripts/earnings/earnings_orchestrator.py:782`, `scripts/earnings/earnings_orchestrator.py:796`, `scripts/earnings/earnings_orchestrator.py:853`).
- Learner validation accepts only `attribution_result.v3`, with string fields for `lesson`, `mechanism`, `applies_when`, `invalid_if`, resolving `evidence_refs`, and v3 audit review/action enums (`scripts/earnings/validate_learning.py:1`, `scripts/earnings/validate_learning.py:133`, `scripts/earnings/validate_learning.py:501`, `scripts/earnings/validate_learning.py:542`).
- Current global scope validation supports `sector`, `macro`, and `cross_ticker`, rejects `scope_key`, and validates routing fields (`scripts/earnings/validate_learning.py:104`, `scripts/earnings/validate_learning.py:342`, `scripts/earnings/validate_learning.py:348`, `scripts/earnings/validate_learning.py:355`, `scripts/earnings/validate_learning.py:407`).
- Ticker writes are atomic but intentionally unlocked, while global writes use `fcntl.flock` with D22 collision checks before the lock (`scripts/earnings/earnings_orchestrator.py:1499`, `scripts/earnings/earnings_orchestrator.py:1559`, `scripts/earnings/earnings_orchestrator.py:1658`, `scripts/earnings/earnings_orchestrator.py:1667`).
- `build_learning_context` keeps PIT and same-quarter self-leak filters, then sorts by recency and caps ticker/sector/macro/cross-ticker rows (`scripts/earnings/earnings_orchestrator.py:2162`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352`, `scripts/earnings/earnings_orchestrator.py:2374`).
- Renderer/body matching already has a shared L-number source and body-only ordered text (`scripts/earnings/_text_utils.py:29`, `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:214`).
- Current skills already ask predictors to test `applies_when`/`invalid_if` and learners to emit structured lesson strings with evidence (`.claude/skills/earnings-prediction/SKILL.md:99`, `.claude/skills/earnings-prediction/SKILL.md:104`, `.claude/skills/earnings-prediction/SKILL.md:106`, `.claude/skills/earnings-learner/SKILL.md:82`, `.claude/skills/earnings-learner/SKILL.md:90`).
- No `scripts/earnings/learning_metrics.py` exists; `find scripts/earnings -path '*learning_metrics.py' -print` returned no paths in this run.

## 2. Non-Negotiable Floors

The minimal v0 keeps these floors exactly because cutting them reopens accepted failures or PT gates:

1. PT1-PT9 remain passing.
2. Round 12 operational-hardening invariants remain self-contained in this plan: PIT/no-leak, same-quarter self-leak prevention, canonical `quality_event.json`, full `prediction_source_tuple`, source provenance caps, atomic/idempotent mutation, event/ticker/global lock order, derived cache replay, row-level provenance equality, replay-check non-zero exits, runbook alerts, and additive schema evolution.
3. Lesson-as-executable-hypothesis remains: `IF applies_when AND NOT invalid_if THEN expected_effect BECAUSE mechanism_chain`.
4. Deterministic/observable applicability remains and feeds render, validator, learner audit, replay, and novice tests.
5. Brier, calibration, no_call, citation precision, applicability precision/recall, transfer precision/recall, velocity, and blast-radius metrics remain quality signals, but sparse statistical authority gates become `activate_after_threshold`.
6. Anti-lazy Q1 all-sentinel defense remains validator-enforced.
7. Q4 missing-source provenance cap remains validator/report/enforcement behavior.
8. Novice applicability test remains.
9. PIT/no-leak and same-quarter self-leak prevention remain.
10. This document is the self-contained roadmap.

PT floors:

- PT1 Novice applicability: deterministic evaluator plus fixtures.
- PT2 Committed prediction: anti-lazy directional/no_call validation and source-grounded key drivers.
- PT3 Mechanism decomposition: four-part mechanism and no-effect rejection.
- PT4 Evidence-grounded predicates: predicate/invalidator traces and resolving source IDs.
- PT5 Lift/non-regression lifecycle: deterministic replay/report health gates v0 authority; Brier/lift statistical gates are report-only until thresholds.
- PT6 Scope precision/recall: no broad authority without independent evidence, bounded pools, missed/over-applied audit evidence, and transfer reports.
- PT7 Predictor influence trace: compact influence enum plus key-driver lesson influence.
- PT8 Operational invariant preservation: Round 12 substrate inline.
- PT9 Minimal implementation: local Python/JSON, one evaluator, one metrics tool, no service/database/dashboard/vector index/tournament authority.

## 3. Mechanism Survival Matrix

| Mechanism | Writer | Reader | Store/derive/report | Failure mode prevented | PT/invariant link | Cost | Verdict | Smallest surviving form |
|---|---|---|---|---|---|---:|---|---|
| `quality_event.json` event seal | learner/backfill/recovery | replay/report/render provenance | stored | Q4 missing-source trust; replay unrecoverability | Round 12; PT8 | 4 | KEEP | One event JSON with source hashes, learning snapshot, lifecycle events, recovery status. |
| Full `prediction_source_tuple` | save/predict/learn | guard, validator, seal, replay | stored hashes | prompt/source drift and save-only overwrite | Round 12 | 3 | KEEP | Same tuple from OperationalHardening, including rendered prompt, section audit, allowlisted sidecars. |
| Event/ticker/global lock order | orchestrator/metrics | mutation/recovery | lock primitive | concurrent corruption and D22 races | Round 12 | 4 | KEEP | Event `.learning.lock`, ticker locks alphabetically, global lock. |
| Row-level prompt-visible provenance equality | metrics/render/replay | render, report, lifecycle | derived from sealed events | forged/mutated live cache rows/audits | Round 12; Q4 | 3 | KEEP | Process-local `EventArtifactIndex`; no durable registry. |
| Lesson ID only | learner/storage | renderer/replay | stored | dual-ID drift | PT9 | 0 | KEEP | Preserve existing computed `lesson_id`; no `hypothesis_id`. |
| `lesson_hypothesis.v1` object | learner | renderer/evaluator/validator | stored in v4 and derived cache | prose-only non-executable lessons | PT1-PT4 | 3 | KEEP | Store mechanism, predicates, invalidators, expected direction/confidence effect, scope, evidence refs. |
| `mechanism_chain` | learner | validator/predictor | stored | slogans and post-hoc lessons | PT3 | 3 | KEEP | Four short fields: setup, anchor_change, participant_interpretation, price_implication. |
| Structured `applies_when[]` | learner | evaluator/predictor/audit | stored | vague applicability and lazy skip | PT1, PT4 | 3 | KEEP | Mandatory predicate objects only; no optional/quorum predicates in v0. |
| Structured `invalid_if[]` | learner | evaluator/predictor/audit | stored | false positives in known null regimes | PT1, PT4 | 3 | KEEP | Same predicate shape as applies_when; any true invalidator blocks citation. |
| Predicate operators | learner | evaluator/validator | stored enum plus derived negation | untestable predicates | PT1, PT4 | 3 | SIMPLIFY | Keep `exists`, `equals`, `in_or_contains`, `gte`, `lte` plus boolean `negate`; no separate negative operators. |
| `observable_status` | learner | validator/report | stored in Round 3 draft | high-authority human-only lessons | PT1, PT4 | 1 | CUT | No stored field in v0. Closed predicate operators are deterministic by construction; human-only or unobservable lessons are rejected or become bundle-feature requests. |
| `expected_effect.direction_effect` | learner | predictor/metrics | stored | applicable lesson with no directional use | PT2, PT5 | 3 | KEEP | `long_bias`, `short_bias`, `no_call_bias`, `none`. |
| `expected_effect.confidence_effect` | learner | predictor/influence tests | stored | no way to measure confidence influence | PT7 | 1 | SIMPLIFY | `increase`, `decrease`, or `none`; exact point deltas defer until calibration evidence exists. |
| `magnitude_bucket` | learner | reports only in final design | stored in final; report-only/deferred here | overfit field current predictions cannot use well | PT9 | 3 | DEFER_TO_V1 | v0 derives magnitude/range quality from existing `expected_move_range_pct` and learner `magnitude_error_pct`; activate per-lesson buckets after measured range-calibration need. |
| `scope.kind` | learner | router/evaluator | stored | overbroad or under-routed lessons | PT6 | 3 | KEEP | `ticker`, `peer`, `sector`, `macro`; legacy `cross_ticker` maps to `peer` during migration/backfill. |
| `macro_subtype` field | learner | router/report | stored in final | macro over-routing | PT6 | 3 | MERGE | No separate field. Encode macro subtype as `scope.routing_key` values like `commodity:copper` or `event_regime:fy_outlook_reset`. |
| `transfer_state` enum | aggregator/learner | router/report | stored in final | broad authority without proof | PT6 | 2 | DERIVE | Derive candidate/proven transfer from birth scope, destination scope, source-complete non-birth helped audits, and current derived tier. |
| `scope_proof` text | learner | human | omitted in final already | unconstrained proof prose | PT9 | 0 | CUT | Keep cut: render proof summary is derived from closed fields and source IDs. |
| `lineage` fields | learner/refinement | lifecycle/replay | stored | unsafe same-body executable edits | PT5, Round 12 | 3 | SIMPLIFY | Keep `parent_lesson_id` and `refined_from_audit_key`; derive supersession reason from the audit chain. |
| Deterministic evaluator | local helper | renderer, validator, learner, replay, tests | derived trace | novice ambiguity and lazy application | PT1, PT4 | 3 | KEEP | One function in orchestrator/helper module; no service. |
| Predicate override protocol | predictor | validator/audit | stored in prediction trace in final | evaluator blind spots | PT4, PT7 | 3 | DEFER_TO_V1 | v0 evaluator is authoritative; blind spots become `not_testable_missing_data`, `no_call`, or learner bundle-feature requests. |
| `requires_no_call` | evaluator/predictor | validator | derived from trace | missing critical data ignored | PT2 | 1 | KEEP | Derived boolean; if true in the deterministic trace, final direction must be `no_call`. |
| Compact render block | renderer | predictor | prompt-only/rendered | hidden conditions | PT1, PT9 | 1 | KEEP | `When`, `Invalid if`, `Effect`, `Mechanism`, `Why shown`; body-only ordered text remains. |
| Quality-before-recency ranking | renderer | predictor | derived | unproven recent lesson crowds out useful older lesson | PT5, recency failure | 3 | KEEP | Bucketed sort before caps; no learned ranker. |
| Potential conflict detection | renderer | predictor/validator | derived | conflicting high-quality lessons yield arbitrary call | PT2, PT7 | 1 | KEEP | Auto-detect opposite applicable effects in same scope/key. |
| Per-lesson `conflict_handling` enum | predictor | validator/audit | stored in final | legalistic duplicate of influence and no_call | PT2, PT7 | 3 | DERIVE | No stored conflict field or array. Validator derives conflict sets from applicable opposing effects and enforces no_call unless key-driver evidence resolves conflict; loser influence uses `outweighed`. |
| Predictor `applicability_verdict`, predicate/invalidator traces | predictor | validator/learner/replay | stored | decorative citations | PT1, PT4, PT7 | 3 | KEEP | Required for every rendered lesson. |
| Predictor `influence` enum | predictor | learner/metrics | stored | citations not tied to usefulness | PT7 | 3 | KEEP | `none`, `cited`, `changed_direction`, `changed_confidence`, `caused_no_call`, `outweighed`, `blocked`. |
| `engagement_source_ids` | validator | validator/learner | derived | influence without current evidence | PT2, PT7 | 1 | DERIVE | Derive from predicate/invalidator traces plus `key_drivers[].evidence_source_ids`; no stored `additional_engagement_source_ids[]`. |
| `key_drivers[].evidence_source_ids` | predictor | validator/anti-lazy | stored | Q1 unsupported directional call | PT2 | 3 | KEEP | Non-S10 source IDs required for anti-lazy exception. |
| Top-level hashes in prediction v2 | predictor/finalizer | validator/seal/replay | stored | source drift | Round 12 | 3 | KEEP | Context bundle, full rendered prompt, section audit, sidecars, lesson set. |
| `counter_thesis` | predictor | validator/report | stored in final | duplicate opposing-case bookkeeping | PT2? weak | 3 | CUT | No stored field. Opposing-evidence absence is report-only; v0 authority keeps anti-lazy and non-S10 key-driver grounding. |
| `source_family`/S10 classification | catalog builder | validator | stored catalog enum | lesson-internal evidence counted as independent | PT2, PT7 | 2 | SIMPLIFY | Binary `lesson` or `non_lesson` is enough for v0; richer family taxonomy is v1 reporting. |
| `audit_outcome` | learner | lifecycle/metrics | stored | review/action ambiguity | PT5, PT7 | 3 | SIMPLIFY | `helped`, `misled`, `outweighed`, `missed`, `dormant`, or `data_missing`; derive correct non-application from verdict pairs. |
| Learner/predictor applicability verdict pair | learner | metrics | stored | precision metrics based on vibes | PT6 | 3 | KEEP | `applicability_verdict_at_prediction`, `learner_applicability_verdict`. |
| `routing_audit` enum | learner | metrics/report | stored | scope precision/recall invisible | PT6 | 3 | KEEP | Keep `none`, `under_routed`, `over_routed`, `cap_excluded`; derive transfer hit/miss from audit_outcome plus destination scope. |
| Minimal `routing_anomaly` object | learner | reports/replay | stored only when `routing_audit != none` | anomaly proof becoming prose-only | PT6 | 1 | SIMPLIFY | Store only destination scope/key and non-S10 routing source IDs; birth scope/key, expected/actual render bucket, and cap name derive from deterministic replay. |
| `transfer_basis` | learner | validator/report | stored in Round 3 draft | broad authority without proof | PT6 | 1 | DERIVE | No stored field. Derive candidate-only versus independent non-birth proof from transfer refs, sealed event identity, and counted future non-birth helped audits. |
| `broaden_candidate` action | learner | aggregator | action in final | useful transfer discovery | PT6 | 2 | MERGE | Remove from action enum; learner emits an ordinary low-authority non-ticker candidate lesson with transfer proof. |
| Candidate-transfer rows | aggregator | router/report | stored in final | under-routing recall | PT6 | 3 | DEFER_TO_V1 | v0 uses ordinary scoped candidate lessons plus missed/under_routed audit evidence. Dedicated transfer rows return only if recall reports prove under-routing remains. |
| Promotion thresholds | lifecycle | renderer | derived | premature authority | PT5, PT6 | 3 | KEEP | Two distinct future source-complete influenced helped audits, zero misled, replay health. |
| Brier/lift statistical authority gates | metrics/lifecycle | lifecycle | authority gate in final | sparse sample false precision | PT5 | 3 | SIMPLIFY | Report-only under 30 completed comparable directional events; `activate_after_threshold` after stable event count. |
| Deterministic replay/report health gate | metrics/lifecycle | lifecycle | authority gate | source/provenance regression | PT5, Round 12 | 3 | KEEP | Hard gate for promotion, exclusion, and broadening. |
| Applicability and transfer precision/recall metrics | metrics | report/lifecycle | derived | scope precision/recall unknown | PT6 | 3 | KEEP | Report quality signals; only deterministic missing/forged/provenance failures gate v0 authority before thresholds. |
| Dense transfer/report strata | metrics | report | report-only in final | analytics platform creep | PT9 | 3 | SIMPLIFY | Report birth scope/key, destination scope/key, routing issue, cap, transfer basis when present. No separate candidate hit/miss strata. |
| LLM ablation/tournament | metrics | research | deferred in final | overfit authority research | PT9 | 3 | DEFER_TO_V1 | Non-authoritative experimental appendix only; not in v0 tests or implementation steps. |
| `learning_metrics.py` | implementer | operator/lifecycle | script | replay/report gap | Round 12, PT5 | 3 | KEEP | One local script with replay, quality report, backfill, lifecycle gate, and reset mode. |
| Separate reset utility | implementer | operator | script in final | extra tool surface | PT9 | 3 | MERGE | `learning_metrics.py --reset-failed-recoverable <event_path>`. |
| `EventArtifactIndex` | metrics/render | replay/report/render | process-local derived | repeated full-corpus scans and provenance checks | Round 12 | 3 | KEEP | In-memory LRU, no durable cache. |
| PT tests for deferred features | test suite | CI/local | tests | v0 burden creep | PT9 | 3 | CUT | Move magnitude-bucket authority, candidate-transfer row, dense strata, tournament tests to v1 backlog. |
| `_render_warnings[]` | renderer | prompt/report | transient in final | stored warning drift | PT5 | 1 | DERIVE | No stored warning array; renderer derives risk/outweighed markers from audit history and lineage. |
| `predicate_id` | validator | evaluator/trace | stored in final | predicate trace identity | PT1, PT4 | 1 | DERIVE | Derive a stable predicate key from canonical predicate content; do not require a stored ID. |

## 4. Cutter Findings

Round 1 cutter position, before external judge review:

- Cut `counter_thesis`: it duplicates ordinary current-evidence key drivers, `evidence_ledger`, and anti-lazy non-S10 source validation. If final direction is directional with no opposing evidence, that is a prediction-quality problem handled by key-driver evidence and confidence validation, not a lesson-intelligence field.
- Defer `magnitude_bucket`: current prediction already has `expected_move_range_pct`, and learner v3 has `magnitude_error_pct` in prediction comparison fields (`scripts/earnings/validate_learning.py:91`). Per-lesson magnitude authority would add schema/test burden before usage is reliable.
- Merge `macro_subtype` into `scope.routing_key`: the safety property is a narrow measurable macro key, not a second field. `routing_key="commodity:copper"` or `routing_key="event_regime:fy_outlook_reset"` is enough, with the final plan's closed allowlist inlined below.
- Derive `transfer_state`: whether transfer is candidate/proven follows from source-complete non-birth audit evidence and derived tier. Storing it creates split-brain with lifecycle evidence.
- Merge candidate-transfer rows into ordinary scoped candidate lesson birth: the v0 need is low-authority transfer discovery with no broad authority. A separate row type plus `candidate_transfer_hit/miss` strata is analytics machinery.
- Preserve only a minimal routing anomaly object: pure derivation was too vague for PT6 under-routing/cap-exclusion proof, but the final `routing_audit_detail` object is still cut down to the fields needed to replay the anomaly.
- Derive engagement source IDs, predicate IDs, correct non-application, render warnings, de-emphasis, and transfer state instead of storing them.
- Narrow enums: binary S10 classification, five predicate operators plus negation, and three confidence-effect values. `observable_status` and stored `transfer_basis` are cut.
- Make Brier/lift gates sparse-sample report-only: deterministic replay/report health, provenance, and per-lesson harm are sufficient v0 authority gates. Statistical authority activates after threshold.
- Merge reset utility into `learning_metrics.py`: one local tool is enough.

Rejected cuts:

- Do not cut deterministic evaluator, predicate/invalidator traces, influence, anti-lazy non-S10 evidence, provenance caps, quality-event seal, row-level provenance equality, PIT/no-leak, or replay/report health gates. Each maps directly to Q1, Q4, PT1-PT8, or Round 12.

## 5. Preserver Findings

Round 1 preserver position, before external judge review:

- Q1 all-sentinel laziness is real: FCX Q1 had `direction="short"`, confidence 48, all six lessons `irrelevant` with `bundle_evidence="no relevant evidence"`, and no lesson citations (`earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:2`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:40`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:45`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:172`). Anti-lazy validation, source-family/S10 rules, key-driver source IDs, and influence traces must stay.
- Q4 provenance gap is real: the Q4 event directory currently has no prediction or learner JSON files in the snapshot, while Q4 rows exist in ticker/global learning caches (`earnings-analysis/learnings/ticker/FCX.json:100`, `earnings-analysis/learnings/global.json:48`). `quality_event.json`, source tuple, dynamic provenance caps, and row-level equality must stay.
- Recency crowd-out is real in current code: ticker and global lessons sort by `attributed_at` before caps (`scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352`). Quality-before-recency ranking must stay.
- Broad sector promotion risk is real: current sector routing only requires `target_sector` shape and matching normalized sector (`scripts/earnings/validate_learning.py:407`, `scripts/earnings/earnings_orchestrator.py:2319`, `scripts/earnings/earnings_orchestrator.py:2330`). Independent non-birth evidence for high-authority non-ticker promotion must stay.
- Conflict/no_call must survive, but the smallest form is a validator-derived conflict detector; no per-lesson `conflict_handling` and no stored `lesson_conflicts[]` are load-bearing if influence, final direction, and key-driver evidence preserve validation.
- PT5 can survive report-only sparse statistics if deterministic replay/report health remains a hard authority gate for promotion, exclusion, and broadening, with Brier/lift gates activating after thresholds.

## 6. Adjudication Log

Round 1 draft adjudication:

| Mechanism | Final status | Reason |
|---|---|---|
| Operational substrate, `quality_event.json`, source tuple, locks, row-level provenance, PIT/no-leak | KEPT | Non-negotiable Round 12 floor. |
| Executable lesson hypothesis, mechanism chain, predicates, invalidators, deterministic evaluator | KEPT | Directly required by PT1, PT3, PT4, novice applicability, anti-lazy. |
| `magnitude_bucket` | DEFERRED_TO_V1 | Current artifacts cannot use it well; range/magnitude quality remains derived/report-only. |
| `macro_subtype` field | MERGED | Store as `scope.routing_key`, not a separate field. |
| `transfer_state` enum | DERIVED | Candidate/proven transfer follows from evidence and tier. |
| Per-lesson `conflict_handling` | MERGED | Validator-derived conflict sets plus influence preserve unresolved no_call behavior. |
| `counter_thesis` | CUT | Duplicates key-driver evidence and anti-lazy support; missing opposing-evidence acknowledgement becomes report-only. |
| `routing_audit_detail` | SIMPLIFIED | Full object cut; minimal `routing_anomaly` survives only for under-routed, over-routed, and cap-excluded rows. Stored render buckets and cap name are derived by replay/report. |
| Candidate-transfer row type | DEFERRED_TO_V1 | Ordinary scoped candidate birth plus under-routing/missed audit covers v0. |
| `candidate_transfer_hit/miss` routing enum values | MERGED | Derive from transfer scope plus `audit_outcome`. |
| Brier/lift statistical authority gates | SIMPLIFIED | Report-only until threshold; deterministic replay/report gate remains hard. |
| Dense transfer precision/recall strata | SIMPLIFIED | Minimal report strata only. |
| Separate reset utility | MERGED | `learning_metrics.py --reset-failed-recoverable`. |
| Tests for cut/deferred mechanisms | CUT/MOVED_TO_V1 | v0 tests cover surviving mechanisms only. |
| `additional_engagement_source_ids[]` | DERIVED | No stored extra evidence channel; validator derives from traces plus key-driver evidence IDs. |
| `correct_nonapplication` audit outcome | DERIVED | Specificity/negative accuracy derives from prediction/learner verdict pairs. |
| `broaden_candidate` and `de_emphasize` actions | MERGED/DERIVED | Transfer candidate birth is ordinary non-ticker lesson birth; de-emphasis is lifecycle-derived. |
| `narrow` action | MERGED | Over-routing is represented by `routing_audit=over_routed`; the corrective action is `refine` with a strictly narrower replacement scope/key. |

## 7. Minimal Target Architecture

Every item in this section carries `v0`, `v1`, or `activate_after_threshold`.

### v0 Operational Substrate

- v0: `events/{quarter}/learning/quality_event.json` is the event seal. It is written atomically after prediction validation, learner validation, derived cache writes, audit aggregation, source-hash verification, and quality-event validation succeed.
- v0: `earnings-analysis/learnings/*.json` remains a derived read model. Rebuild/replay compares live rows against sealed events and source-complete legacy triples.
- v0: the protected `prediction_source_tuple` includes `context_bundle.json`, full `context_bundle_rendered.txt`, `prediction/result.json`, `prediction/section_audit.json`, `learning/result.json`, `learning/quality_event.json`, rendered learning-context hash, lesson-set hash, and allowlisted prompt-readable sidecars.
- v0: `learning/quality_event.json` uses the non-self-referential hash convention from the operational floor: compute any quality-event content hash with the quality-event self-hash field omitted. Replay/report may record the on-disk file hash as outer artifact metadata, but that outer hash is not part of the sealed payload being hashed.
- v0: source provenance caps prevent missing-source rows/audits from earning verified credit, promotion, exclusion authority, citation precision credit, Brier/lift credit, or high-authority rendering.
- v0: mutation lock order is event `.learning.lock`, ticker locks in alphabetical ticker order, then global lock. D22 collision checks run inside the relevant lock.
- v0: `EventArtifactIndex` is process-local and LRU-bounded. It caches source tuple hashes, emitted lesson projections, audit-verdict maps, and expected PIT-visible audit sets. It writes no durable registry.

### v0 Lesson Schema

`attribution_result.v4` and derived cache rows use one `lesson_hypothesis.v1` object:

- v0: `lesson_id`, computed from normalized body plus scope kind plus routing key.
- v0: `lesson`, a 1-2 sentence body.
- v0: `mechanism_chain`: `setup`, `anchor_change`, `participant_interpretation`, `price_implication`.
- v0: `applies_when[]`: mandatory predicate objects.
- v0: `invalid_if[]`: same predicate shape; any true invalidator blocks citation.
- v0: `expected_effect.direction_effect`: `long_bias`, `short_bias`, `no_call_bias`, `none`.
- v0: `expected_effect.confidence_effect`: `increase`, `decrease`, or `none`. Exact confidence point deltas are v1 because PT7 needs traceable confidence influence, not calibrated point arithmetic.
- v0: a lesson with `direction_effect=none` and `confidence_effect=none` is rejected at birth as no-effect; v0 does not use deferred magnitude fields to rescue a no-effect lesson.
- v1: `expected_effect.magnitude_bucket`. Until then, range/magnitude quality derives from prediction `expected_move_range_pct` and learner `magnitude_error_pct`.
- v0: `scope.kind`: `ticker`, `peer`, `sector`, `macro`.
- v0: `scope.routing_key`: ticker symbol, peer-list key, canonical sector, or macro key.
- v0: a peer-list key is the sorted, deduplicated, comma-joined ticker tuple for the declared peer set; any other peer key form is invalid.
- v0: allowed macro routing keys are exactly `commodity:copper`, `commodity:gold`, `commodity:oil`, `commodity:gas`, `event_regime:quantified_warning_pt_reset`, `event_regime:fy_outlook_reset`, and `event_regime:delayed_dominant_driver`. Unknown keys are rejected or become bundle-feature requests.
- v0: no stored `macro_subtype`; it is the macro `routing_key`.
- v0: no stored `transfer_state`; transfer authority derives from evidence.
- v0: transfer-state derivation is deterministic. Destination is the candidate lesson's own `scope.kind`/`scope.routing_key`. Birth context derives from the sealed co-emitted audit event identity for a fresh emit, and from `lineage.parent_lesson_id`'s prior `scope.kind`/`scope.routing_key` for an update or refinement. The sealed event identity is the `quality_event.json` identity from the v0 Operational Substrate, namely `(event_path, ticker, quarter_label)`. `none` means no non-ticker transfer proof or no destination change; `candidate_transfer` means a normal scoped candidate lesson has source-complete transfer proof but has not met the two-counted-helped-audit threshold defined in the non-ticker promotion rule; `proven_transfer` means that non-ticker promotion threshold is met. No row stores this enum or any separate birth/destination fields.
- v0: `lineage`: `parent_lesson_id` and `refined_from_audit_key`. Supersession reason derives from the referenced audit outcome and reason.

Predicate shape:

- v0: exactly one of `field_path` or `source_id_pattern`, `operator`, optional `negate`, `expected_value`, optional `units`, `source_ids[]`, and `missing_behavior`.
- v0: `predicate_key` is derived by validator/evaluator from canonical predicate content; it is not stored.
- v0: operators are `exists`, `equals`, `in_or_contains`, `gte`, and `lte`. `negate=true` expresses `not_in`/`not_contains_any`; `in_or_contains` operates on scalar, list, or text values.
- v0: `missing_behavior` is `not_applicable`, `unknown`, or `requires_no_call`.
- v0: all predicate operators are deterministic by construction. Human-only or unobservable claims are rejected at birth unless they can be expressed as supported `field_path` or `source_id_pattern` predicates; otherwise they become bundle-feature requests or v1 non-deterministic operator candidates.

### v0 Applicability

- v0: one deterministic `evaluate_lesson_applicability(lesson, bundle, evidence_source_catalog)` returns `verdict`, `predicate_trace[]`, `invalidator_trace[]`, `unknown_predicates[]`, and derived `requires_no_call`.
- v0: verdicts are exactly `applies`, `blocked_by_invalid_if`, `not_applicable`, `not_testable_missing_data`.
- v0 decision order:
  1. true invalidator -> `blocked_by_invalid_if`, `requires_no_call=false`;
  2. all applies predicates true -> `applies`;
  3. any mandatory applies predicate false -> `not_applicable`, `requires_no_call=false`;
  4. otherwise missing `unknown` or `requires_no_call` predicate -> `not_testable_missing_data`;
  5. otherwise `not_applicable`.
- v1: prediction-time predicate overrides. In v0, the deterministic evaluator is authoritative. If the evaluator cannot test a predicate from saved artifacts, the lesson is `not_testable_missing_data`, forces `no_call` when `missing_behavior=requires_no_call`, or becomes a learner bundle-feature request.
- v0: if any final rendered trace has `requires_no_call=true`, final direction must be `no_call`.

### v0 Prediction Contract

`prediction_result.v2` extends current v1:

- v0: top-level source hashes and lesson-set hash.
- v0: evidence catalog rows expose canonical closed-enum `source_family` with binary values `lesson` or `non_lesson`. Legacy `source_origin` is a backfill-only alias that is normalized into `source_family` before v0 validation. `S10` means lesson-internal/rendered-lesson source IDs; `non-S10` means current bundle or evidence-ledger source IDs independent of the lesson text. S10 lesson-internal sources never count as independent evidence.
- v0: `key_drivers[].direction`, `key_drivers[].evidence_source_ids[]`, and `key_drivers[].lesson_influence[]`. Direction remains `long` or `short` as in current v1 key drivers.
- v0: every `lesson_labels[]` row includes `lesson_id`, `applicability_verdict`, predicate/invalidator traces, `influence`, and `influence_reason`.
- v0: no `additional_engagement_source_ids[]`. Validation derives engagement sources from predicate/invalidator trace source IDs plus `key_drivers[].evidence_source_ids[]`.
- v0: no `counter_thesis`. Opposing evidence is ordinary key-driver/evidence-ledger material. Missing opposing-evidence acknowledgement on high-confidence directional calls is a quality-report warning, not an authority-changing validator rule.
- v0: that authority-free quality-report warning triggers for directional confidence >60 when no key driver with non-S10 source IDs has `direction` opposing the final direction. It is report-only: it does not reject, cap authority, count as PT2 coverage, or restore a stored counter-thesis object.
- v0: no stored `lesson_conflicts[]`. The validator derives conflict sets from rendered high-quality applicable lessons with opposing non-`none` direction effects. High-quality conflict means at least two currently applicable lessons with deterministic applicability and complete provenance, where at least one has `_render_tier=proven` and the other has `_render_tier` in `{proven, candidate}`. If conflict is unresolved by non-S10 key-driver evidence, final direction must be `no_call`; resolved losing lessons use `influence=outweighed`.
- v0 influence enum: `none`, `cited`, `changed_direction`, `changed_confidence`, `caused_no_call`, `outweighed`, `blocked`. `changed_confidence` is required when the lesson changes final confidence by at least 5 points; ECE bin authority is v1 and bins are not required for v0 influence classification.
- v0: `cap_matrix_v0` is fixed inline as ticker cap 8, sector cap 4, macro cap 4, peer cap 2. Renderer replay, anti-lazy counted-rendered-lesson checks, and `cap_excluded` derivation all consume this named matrix; it is not configurable in v0.
- v0 anti-lazy rule: when every counted rendered lesson is `not_applicable`, `not_testable_missing_data`, or `blocked_by_invalid_if`, direction must be `no_call` unless at least two distinct key drivers each have at least one resolving non-S10 source ID and the union contains at least two distinct source IDs. If the exception passes, `long` or `short` confidence must be in `51 <= confidence_score <= 55`. Counted rendered lessons use `cap_matrix_v0`.
- v0: directional `confidence_score` must be `51..100`; `no_call` has no Brier probability.

### v0 Learner Audit Contract

`attribution_result.v4` extends current v3:

- v0: each new lesson emits `lesson_hypothesis.v1`; generic, unobservable, overbroad, no-effect, or mixed-mechanism lessons are rejected.
- v0: audit rows include `lesson_id`, `applicability_verdict_at_prediction`, `learner_applicability_verdict`, `audit_outcome`, `routing_audit`, `influence`, `action`, `reason`, and resolving `evidence_refs`.
- v0: `audit_outcome` is `helped`, `misled`, `outweighed`, `missed`, `dormant`, or `data_missing`. Correct non-application is derived from verdict pairs.
- v0: when both `applicability_verdict_at_prediction` and `learner_applicability_verdict` are non-`applies` and `influence=none`, no audit row is emitted for correct non-application; specificity and negative applicability accuracy derive from the verdict pair.
- v0: `audit_outcome=dormant` is emitted only on the single audit event that triggers the derived lifecycle dormancy threshold: eight PIT-valid opportunities or four future-quarter labels with zero applies and no data-missing blocker. Ordinary correct non-application never emits a dormant row; it follows the no-row rule above.
- v0: `routing_audit` is `none`, `under_routed`, `over_routed`, or `cap_excluded`.
- v0: `routing_anomaly` is required only when `routing_audit != none`; it contains `destination_scope`, `destination_key`, and `routing_source_ids[]` resolving to non-S10 catalog IDs. `routing_source_ids[]` may share IDs with the audit row's `evidence_refs[]`, but it must independently resolve to non-S10 catalog IDs that prove destination scope/key relevance. The affected lesson's original scope/key derive from the canonical lesson row. Normal transfer successes with `routing_audit=none` derive strata from closed lesson fields and sealed auditor event identity.
- v0: replay/report derives `expected_render_bucket`, `actual_render_bucket`, and cap name from `cap_matrix_v0` and bucketed sort. For `cap_excluded`, the derived cap name is the first scope cap whose threshold the lesson exceeded.
- v0: `action` is `keep`, `refine`, or `exclude_candidate`. De-emphasis is lifecycle-derived. Over-routing correction uses `routing_audit=over_routed` plus `action=refine`, and the replacement lesson must have a strictly narrower destination scope/key than the parent.
- v0: transfer discovery emits or updates a normal low-authority non-ticker candidate lesson in the same learner result, not a `broaden_candidate` action and not a candidate-transfer row type.
- v0: non-ticker candidate birth requires resolving `transfer_evidence_refs[]`. The destination is the candidate lesson's own `lesson_hypothesis.v1.scope.kind`/`scope.routing_key`. The fresh-birth origin derives from the sealed co-emitted audit event identity, including auditor ticker and quarter label; update/refinement origin derives from `lineage.parent_lesson_id`'s prior `scope.kind`/`scope.routing_key`. Stored `birth_scope`, `birth_key`, `destination_scope`, and `destination_key` fields are invalid in v0 because they duplicate adjacent candidate scope, lineage, and sealed auditor identity. This keeps bounded transfer-pool membership replayable without scanning unrelated bundles.
- v0: no stored `transfer_basis`. Candidate-only versus independent non-birth proof derives from the transfer refs' source identity, sealed event identity, destination scope/key, and counted future non-birth helped audits.
- v0: `helped` promotion credit requires `learner_applicability_verdict=applies`, influence in `changed_direction`, `changed_confidence`, or `caused_no_call`, source-complete evidence, and outcome support.
- v0: `misled` requires influence plus wrong mechanism/predicate/effect.
- v0: `outweighed` requires a named source-grounded stronger force or objective shock/range condition and earns no helped/misled/citation precision credit.

### v0 Lifecycle

- v0 derived tiers: `candidate`, `proven`, `dormant`, and `excluded`.
- v0: new source-complete lessons render as low-authority `candidate`. Missing-source legacy lessons render only as unproven/missing-provenance and earn no quality credit.
- v0: `unproven` or `missing-provenance` is a render/provenance marker on a `candidate` row, not a fifth lifecycle tier.
- v0: `proven` requires complete provenance, two source-complete influenced `helped` audits from two distinct future audit keys and future quarter labels, zero `misled` since latest refinement, zero unrecovered source-grounded `outweighed` influenced audits since latest refinement, replay/report health PASS, and no blast-radius breach. Recovery from outweighed pressure requires a later source-complete helped audit on the same scope/key.
- v0: high-authority non-ticker promotion requires at least two counted non-birth destination events from at least two distinct non-birth destination tickers/source issuers, matching destination scope/key, complete provenance, zero transfer misled, and derived independent non-birth proof from transfer refs plus helped audits.
- v0: promotion and broadening fail closed on missing/incomplete source tuple, cache/canonical drift, missing/forged audit rows, human-decision source class, all-sentinel validation breach, or blast-radius breach.
- v0: blast-radius breach is self-contained and deterministic: no single lesson lineage family or near-clone cluster may account for more than 25% of verified misled cited outcomes in the rolling 50 completed directional calls. V0 retains the OperationalHardening near-clone rule as a derived local grouping, not stored state: start with `parent_lesson_id` lineage family when present; otherwise cluster by normalized lesson-body 5-token-shingle Jaccard similarity `>= 0.82` within the same scope/routing key. Normalization is lowercase ASCII, collapsed whitespace, and stripped trailing punctuation; the pairwise pass is bounded to PIT-visible lessons in one scope/routing key and cached only in process. Exact-body hash alone is not an acceptable fallback because paraphrased near-clones share blast-radius credit.
- activate_after_threshold: Brier/lift/ECE authority gates activate only after at least 30 completed comparable directional events and stable relevant bins. Before threshold they are report-only and cannot promote/broaden by themselves.
- v0: exclusion requires measured per-lesson harm plus replay/report health. Statistical uncertainty cannot block obvious safety exclusions when source-complete per-lesson harm is clean.
- v0: dormant after eight PIT-valid opportunities or four future quarter labels with zero applies and no data-missing blocker.
- v0: low-usefulness de-emphasis is derived when a candidate renders at least five times, never influences, and has no missed/helped audit; no learner action stores this.
- v0: bounded transfer pool membership is explicit and replayable: ordinary non-ticker candidate births enter the pool through candidate scope, transfer refs, and derived origin/destination; declared peers enter by peer list; same-sector non-birth rows enter by sector match; and macro rows enter by allowed macro routing key. Exact local ticker opportunities remain ordinary applicability recall, not transfer recall.
- v0: same-body executable refinements are invalid; refinement must emit a new body/new lesson ID and parent lineage.

### v0 Metrics and Tooling

- v0: one `scripts/earnings/learning_metrics.py` handles `--replay-check`, `--quality-report`, `--lifecycle-gate`, `--backfill-legacy`, and `--reset-failed-recoverable <event_path>`.
- v0: replay-check exits non-zero and emits `LEARNER_ALERT status=replay_drift ...` on extra live rows, missing live rows, hash drift, in-flight locks, failed recovery, or incomplete events.
- v0: quality report emits Brier, calibration/ECE with sparse flags, no_call usefulness and coverage, citation precision, applicability precision/recall, transfer precision/recall, velocity, blast-radius, missing-source, failed-recovery, human-decision, and all-sentinel counts.
- v0: lifecycle gate JSON reports deterministic health and sparse statistical fields. It exits non-zero on FAIL. Sparse Brier/lift fields are `PROVISIONAL`.
- v1: LLM ablation/tournament research remains non-authoritative and outside v0 tests.

## 8. Updated Complexity Ledgers

Weight vocabulary: durable artifact type = 4; lock/concurrency primitive = 4; schema/major field group = 3; validator surface = 3; script/tool = 3; lifecycle state/status = 2.

Ledger 1: finalized LessonIntelligence -> minimal target. Common operational-hardening substrate is counted in both columns so reductions come only from lesson-intelligence pruning.

| Mechanism group | Final LI weight | Minimal v0 weight | Delta | Pruning proof |
|---|---:|---:|---:|---|
| Operational seal/source tuple/locks/provenance/replay floors | 24 | 24 | 0 | Non-cuttable Round 12 floor. |
| Core executable hypothesis: mechanism, predicates, invalidators, direction/confidence effect, lineage | 15 | 11 | -4 | Confidence deltas, predicate IDs, `observable_status`, supersession prose, and wider enum values are cut or derived while the load-bearing hypothesis remains. |
| Magnitude bucket field/validator/tests | 3 | 0 | -3 | Deferred; range/magnitude reports derive from existing prediction/learner fields. |
| Scope field group with separate `macro_subtype` and `transfer_state` | 6 | 3 | -3 | Macro subtype merged into routing key; transfer state derived. |
| Deterministic evaluator and override validation | 6 | 3 | -3 | Evaluator remains; prediction-time override protocol is v1. |
| Predictor trace and influence | 9 | 6 | -3 | `additional_engagement_source_ids[]` is derived from traces plus key-driver evidence IDs. |
| Per-lesson conflict handling plus conflict tests | 3 | 0 | -3 | Fully derived by validator from applicable opposing effects, influence, and key-driver evidence. |
| `counter_thesis` schema/validator/prompt | 3 | 0 | -3 | Stored field and authority cap cut; report-only warning uses existing key-driver direction/source IDs. |
| Learner audit outcome/action core | 6 | 3 | -3 | `correct_nonapplication`, `de_emphasize`, `broaden_candidate`, and separate `narrow` are derived/merged. |
| Routing audit detail and transfer hit/miss strata | 9 | 1 | -8 | Full detail object cut; anomaly stores only destination scope/key plus source IDs, while render buckets and cap name derive by replay/report. |
| Candidate-transfer dedicated row/state machinery | 6 | 1 | -5 | Normal scoped candidate birth with explicit bounded-transfer proof; no transfer row type/state and no stored `transfer_basis`. |
| Statistical Brier/lift authority gates before threshold | 3 | 1 | -2 | Report-only until activation threshold. |
| Dense transfer/report analytics strata | 3 | 1 | -2 | Minimal raw counts/simple rates only until thresholds; dense strata v1. |
| `learning_metrics.py` plus separate reset utility | 6 | 3 | -3 | One script, reset is a mode. |
| Tests for deferred/cut features | 6 | 0 | -6 | Move to v1 backlog. |
| Total | 108 | 57 | -51 | 47.2% weighted reduction. |

Ledger 1 result: strict reduction of 51/108 = 47.2%, exceeding the 15% target. Lesson-intelligence-only reduction excluding the 24-point operational floor is 51/84 = 60.7%.

Ledger 2: current code -> minimal target.

| Change | Class | Current evidence | Smallest mechanism |
|---|---|---|---|
| Preserve PIT and same-quarter guards | ALREADY-CODED | `scripts/earnings/earnings_orchestrator.py:2162`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2300` | Keep in `build_learning_context`; fail closed for invocation-time historical learner mutation. |
| Preserve body-only lesson labels and shared L-number source | ALREADY-CODED | `scripts/earnings/_text_utils.py:29`, `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:214` | Keep renderer/order contract. |
| Preserve source-ID grounding | ALREADY-CODED/PARTIAL | `scripts/earnings/earnings_orchestrator.py:853`, `.claude/skills/earnings-learner/SKILL.md:78` | Extend to predicate traces and key drivers. |
| Preserve structured lesson prose fields | PARTIAL | `scripts/earnings/validate_learning.py:501`, `.claude/skills/earnings-learner/SKILL.md:82` | Convert strings to executable predicate arrays and mechanism_chain. |
| Add prediction v2 anti-lazy/influence validation | PARTIAL | Current lesson-label checks at `scripts/earnings/earnings_orchestrator.py:747`; Q1 gap at `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8` | Extend current validator, not new service. |
| Add quality event and source tuple | NET-NEW | Q4 missing-source rows visible in caches at `earnings-analysis/learnings/ticker/FCX.json:100`, `earnings-analysis/learnings/global.json:48` | One event JSON seal. |
| Add event/ticker/global locks | PARTIAL | Ticker no-lock at `scripts/earnings/earnings_orchestrator.py:1499`; global lock at `scripts/earnings/earnings_orchestrator.py:1667` | Add ticker locks and move D22 inside locks. |
| Add deterministic evaluator | NET-NEW | Predicate truth is prompt-side at `.claude/skills/earnings-prediction/SKILL.md:104` | One local helper used by render/validation/audit/replay/tests. |
| Add quality-before-recency ranking | PARTIAL | Recency sort at `scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352` | Replace sort key before existing caps. |
| Add row-level provenance gates | NET-NEW | Live caches currently render directly after PIT/scope filters | `EventArtifactIndex` reconstructs expected prompt-visible rows. |
| Add `learning_metrics.py` | NET-NEW | `find scripts/earnings -path '*learning_metrics.py' -print` returned no paths | One script with modes only. |
| Prompt updates | PARTIAL | Skills already contain baseline rules | Add v2/v4 fields and examples; validators enforce mechanical pieces. |

Net-new implementation cost is strictly smaller than finalized LessonIntelligence because it removes per-lesson conflict enum validation, stored conflict arrays, stored `counter_thesis`, per-lesson magnitude bucket, prediction-time predicate overrides, dedicated candidate-transfer row machinery, stored `transfer_state`, stored `transfer_basis`, stored `observable_status`, separate `macro_subtype`, separate reset utility, stored `additional_engagement_source_ids[]`, stored predicate IDs, stored `correct_nonapplication`, stored `de_emphasize`/`broaden_candidate`/`narrow` actions, stored routing cap/bucket replay outputs, wide enum values, and v0 tests for those features. It restores only a minimal anomaly object for non-none routing audits because Round 1 preservation review showed PT6 anomaly proof otherwise became prose-only.

## 9. PT1-PT9 Non-Regression Proof

| PT | Why it still passes after pruning |
|---|---|
| PT1 Novice applicability | The deterministic evaluator, predicate/invalidator schema, source IDs, and novice fixture harness are kept. Merging macro subtype into routing key and deferring magnitude does not affect applicability. |
| PT2 Committed prediction | Anti-lazy all-sentinel validation, non-S10 key-driver evidence, `requires_no_call`, confidence band 51-55, and conflict no_call stay. Cutting stored `counter_thesis` and the high-confidence opposing-evidence cap does not permit Q1-style unsupported calls because directional support still requires current non-S10 key-driver evidence; the opposing-evidence warning is authority-free quality-report output, not PT2 coverage. |
| PT3 Mechanism decomposition | Four-field `mechanism_chain` and no-effect rejection stay. |
| PT4 Evidence-grounded predicates | Predicate traces, invalidator traces, source-family/S10 classification, and evidence-ref resolution stay. Prediction-time overrides are v1. |
| PT5 Lift/non-regression lifecycle | Deterministic replay/report health remains hard gate for promotion, exclusion, and broadening. Brier/lift statistical gates are report-only while sparse and `activate_after_threshold` once the event count is sufficient, which the pruning prompt explicitly allows. |
| PT6 Scope precision/recall | High-authority non-ticker promotion still requires independent non-birth evidence. Under-routing, over-routing, cap exclusion, missed audits, bounded pools, and transfer precision/recall reports remain. Dedicated candidate-transfer rows are not required; minimal routing anomaly detail survives only where prose-only derivation would weaken replayable proof. |
| PT7 Predictor influence trace | Compact influence enum, key-driver lesson influence, derived engagement source union, and learner copied/inferred influence remain. Per-lesson conflict enum is merged, not deleted without replacement. |
| PT8 Operational invariant preservation | Round 12 substrate is kept verbatim: quality event, source tuple, locks, derived caches, row-level provenance, replay/report, migration classes, alerts. |
| PT9 Minimal implementation | v0 is smaller: fewer stored fields, fewer enums, fewer validator surfaces, one tool, no candidate-transfer row type, no counter-thesis, no magnitude bucket authority, no tournament authority. |

## 10. Round 12 Operational Invariant Preservation Proof

| Invariant | Minimal v0 preservation |
|---|---|
| PIT/no-leak and same-quarter self-leak | Already coded filters stay; same-quarter self-leak remains a hard read-side guard. |
| Source provenance caps | Missing-source rows/audits can render only low authority, cannot earn verified credit, cannot promote/exclude, and cannot affect citation/Brier/lift authority. |
| Canonical event seal | `learning/quality_event.json` remains the canonical ledger. |
| Derived caches | `learnings/*.json` remains rebuildable derived state; row equality checks compare prompt-visible projection to sealed events. |
| Replay/recovery | `learning_metrics.py --replay-check` and deterministic recovery remain. Missing seals trigger recovery or failed_recoverable, not silent trust. |
| Atomic/idempotent mutation | `_atomic_write_json`, event lock, ticker locks, global lock, and upsert keys remain. |
| Lock order | Event, ticker alphabetical, global. |
| D19/D20/D22 | Cross-file audit parity, body-only lesson matching, and ID collision checks remain; D22 moves inside locks. |
| Full source tuple | Full rendered prompt, section audit, sidecars, bundle, prediction, learner, quality event, lesson-set hash remain covered. |
| Save-time commitment | Exact-schema `production_source_commitment` remains. |
| EventArtifactIndex | Bounded process-local cache remains; no durable registry is added. |
| Migration classes | Already-valid, source-complete legacy, missing-source, failed-recovery, human-decision remain. |
| Alerts/runbook | Non-zero health exits and `LEARNER_ALERT status=<state> ticker=<T> quarter=<Q> reason=<R>` remain. |
| Additive schemas | `prediction_result.v2` and `attribution_result.v4` extend current artifacts. |

## 11. Failure Mode Coverage Matrix

| Failure mode | Surviving coverage |
|---|---|
| Q1 sentinel laziness | Required per-lesson applicability verdict/traces; anti-lazy all-non-applicable directional block; non-S10 key-driver evidence exception; confidence 51-55 cap; source-family/S10 classification. |
| Q4 provenance gap | `quality_event.json`, full source tuple, missing-source caps, row-level provenance equality, migration classes, replay-check drift exits. |
| Recency ranking crowd-out | Quality/applicability/tier ranking before caps; deterministic tiebreakers only after quality buckets. |
| Overbroad sector promotion | Non-ticker high authority requires independent non-birth evidence from distinct destination tickers/source issuers; structural sector proof is candidate-only. |
| Hardcoded active/watch/retired lifecycle | Derived `candidate/proven/dormant/excluded` tiers from audit evidence and replay health. |
| Scope under-routing | `missed` plus `under_routed`, bounded missed-applicable pool, normal scoped non-ticker candidate birth with transfer proof, transfer recall report. |
| Scope over-routing | `over_routed`, `action=refine` with strictly narrower replacement scope/key, non-birth promotion requirements, transfer precision report. |
| Decorative citations | Influence enum, key-driver lesson influence, non-S10 engagement source IDs, learner audit compatibility. |
| Missing critical data ignored | `requires_no_call` derived from missing predicates and hard final `no_call` obligation. |
| Prompt/source drift | Save-time source commitment, full source tuple hashes, row-level equality, replay-check hash drift. |
| Sparse statistical overconfidence | Brier/lift gates report-only until threshold; deterministic replay/provenance/per-lesson harm gates remain hard. |
| Legalistic conflict taxonomy | Validator-derived conflict set preserves unresolved conflict no_call without per-lesson conflict enum or stored conflict record. |

## 12. Deferred-to-V1 Backlog

The final two entries are v1 evaluation notes only. They intentionally keep the v0 fields as stored snapshots until their triggers prove the replay joins/scans are deterministic, cheap, and non-regressive.

| Mechanism | Reason deferred | Target form | Reconsider trigger |
|---|---|---|---|
| Per-lesson `magnitude_bucket` authority | Current prediction artifacts already have move range; per-lesson bucket adds schema/test burden before evidence. | Add only if range/magnitude calibration reports show per-lesson effect size is needed. | Two or more source-complete events where direction is right but magnitude error would have changed lesson ranking or no_call. |
| Dedicated candidate-transfer row type and stored `transfer_state` | Ordinary scoped non-ticker candidates with destination from candidate scope and origin from sealed auditor identity or lineage preserve v0 transfer discovery. | Add explicit transfer-discovery rows only if under-routing persists. | Transfer recall below target across at least 30 source-complete opportunities with evidence that ordinary scoped candidate birth is insufficient. |
| Full `routing_audit_detail` and candidate-transfer hit/miss strata | Minimal anomaly detail covers non-none routing proof; normal transfer successes derive from sealed event and closed fields. | Add only selected extra detail fields, not the full object. | Reports cannot reconstruct a required PT6 denominator from sealed artifacts plus minimal anomaly fields. |
| Stored `observable_status` or non-deterministic predicate operators | V0 operators are deterministic by construction, and unobservable lesson birth is rejected. | Add only with a named non-deterministic operator and strict no-promotion rules. | A source-complete failure proves a necessary predicate cannot be expressed as `field_path` or `source_id_pattern` plus closed operators. |
| Stored `transfer_basis` | Candidate-only versus independent non-birth proof derives from transfer refs, sealed event identity, and helped audit evidence. | Add only if derivation creates ambiguous promotion decisions. | A source-complete PT6 promotion/rejection case cannot be reproduced from refs and audit chain. |
| Prediction-time predicate overrides | A second authority path around the evaluator is too heavy for v0. | Source-grounded per-predicate override protocol. | A source-complete replay case proves evaluator false negatives cannot be fixed by source_id_pattern predicates or bundle-feature requests. |
| Stored conflict records | Conflict sets and resolution are derivable from lesson effects, applicability, final direction, influence, and key-driver evidence. | Stored `lesson_conflicts[]` or per-lesson conflict enum. | Validator-derived conflict checks cannot reproduce a needed PT2 no_call decision. |
| Opposing-evidence confidence cap | Counter-thesis authority behavior is not v0-essential beyond anti-lazy/source grounding. | Stored or derived high-confidence cap. | Source-complete high-confidence wrong calls cluster around ignored opposing evidence after anti-lazy validation is already satisfied. |
| Brier/lift authority gates below threshold | Sparse samples create false precision. | Activate statistical gate after threshold. | At least 30 completed comparable directional events with stable bins and complete frozen baseline. |
| LLM ablation/tournament authority | Non-deterministic and implementation-heavy. | Research mode only with model/prompt/hash/repeat metadata. | Separate goal after deterministic metrics prove insufficient. |
| Vol-scaled magnitude buckets | More precise but not v0-essential. | Per-ticker or volatility-normalized magnitude calibration. | Measured magnitude report regressions on source-complete events. |
| Separate reset utility | Extra tool surface. | None; reset stays a `learning_metrics.py` mode. | Never unless CLI ergonomics become a blocker. |
| Derive `applicability_verdict_at_prediction` from prediction artifact | V0 stores the audit-row verdict to avoid a cross-artifact join in metrics/replay. | Derive from `prediction_result.v2.lesson_labels[].applicability_verdict` by joining on event identity plus lesson ID if replay joins prove cheap and unambiguous. | Metrics replay proves the join is deterministic and cheaper than the audit-row snapshot. |
| Derive `lineage.refined_from_audit_key` from refine audit rows | V0 stores the direct pointer to avoid audit-table scans during replay and parent recovery. | Reconstruct by scanning audit rows with `action=refine` and replacement lesson identity. | Replay over source-complete audit chains proves the scan is cheap, unique, and does not weaken same-body refinement checks. |

## 13. Updated Exact Future Change Plan From Current Code

This section is the implementation roadmap. It is self-contained and does not require opening prior plans.

### `scripts/earnings/earnings_orchestrator.py`

1. ALREADY-CODED: keep `build_prediction_bundle` adding `learning_context` and `evidence_source_catalog` (`scripts/earnings/earnings_orchestrator.py:196`, `scripts/earnings/earnings_orchestrator.py:258`, `scripts/earnings/earnings_orchestrator.py:280`).
2. ALREADY-CODED: keep PIT and same-quarter self-leak filters in `build_learning_context` (`scripts/earnings/earnings_orchestrator.py:2162`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2300`).
3. PARTIAL: replace recency-first sorting with quality/applicability/tier bucket sorting before existing caps. Current recency sort and caps are at `scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352`, and `scripts/earnings/earnings_orchestrator.py:2374`.
4. NET-NEW: add path helpers for `learning/quality_event.json` and event `.learning.lock`.
5. NET-NEW: add canonical JSON serializer used by save commitment, prediction validation, quality-event seal, replay-check, and backfill: sorted keys, compact separators, no NaN, stable datetime/Decimal conversion.
6. NET-NEW: add production artifact immutability guard before any production builder side effect, related-filing sidecar creation, source-artifact write/unlink, SDK invocation, prediction finalization, or `learning/result.json` read/write. It acquires event `.learning.lock`, validates sealed or save-only tuples, refuses overwrite of sealed/invalid existing artifacts, and emits human-decision alerts.
7. NET-NEW: stamp exact-schema `production_source_commitment` in `context_bundle.json` after rendered prompt and allowlisted sidecars exist. It includes bundle payload hash excluding the commitment, full rendered prompt hash, sorted sidecars, and `hash_origin=stamped_at_save_finalize`.
8. PARTIAL: extend prediction validator from current v1 lesson-label checks to `prediction_result.v2`. Preserve shape, body-position, confirmed-only citation, and evidence ledger grounding (`scripts/earnings/earnings_orchestrator.py:747`, `scripts/earnings/earnings_orchestrator.py:782`, `scripts/earnings/earnings_orchestrator.py:796`, `scripts/earnings/earnings_orchestrator.py:853`).
9. NET-NEW: add v2 checks for hashes, binary S10/non-S10 classification, key-driver evidence IDs, per-lesson applicability traces, derived engagement-source union, influence compatibility, anti-lazy no_call/51-55 band, directional confidence >50, and validator-derived conflict/no_call checks. Anti-lazy counted lessons and `cap_excluded` derivation consume `cap_matrix_v0` from Section 7 and renderer step 6.
10. NET-NEW: do not implement stored `counter_thesis`, high-confidence opposing-evidence cap, per-lesson `conflict_handling`, stored `lesson_conflicts[]`, prediction-time predicate overrides, per-lesson `magnitude_bucket`, stored `additional_engagement_source_ids[]`, stored `transfer_state`, stored `transfer_basis`, stored `observable_status`, stored routing cap/bucket replay outputs, or full stored `routing_audit_detail`.
11. NET-NEW: implement `evaluate_lesson_applicability` with the v0 predicate operators and deterministic decision order. Use it in `build_learning_context`, prediction validation, learner audit support, replay, and novice tests.
12. NET-NEW: implement `quality_event.json` seal with source hashes, hash origins, prediction snapshot, outcome snapshot, learning snapshot, lifecycle events, structured recovery notes, recovery attempts, and last recovery timestamp. Only `status=sealed` gives provenance credit.
13. NET-NEW: deterministic recovery for `learning/result.json` without sealed quality event: validate siblings, recompute hashes, replay derived writes under locks, seal or write/update `failed_recoverable`.
14. PARTIAL: add ticker locks and move ticker/global D22 collision scans inside locks. Current ticker path says no lock at `scripts/earnings/earnings_orchestrator.py:1499`, and global D22 is outside lock at `scripts/earnings/earnings_orchestrator.py:1658`.
15. NET-NEW: audit aggregation upserts by `(parent_lesson_id, auditor_ticker, auditor_quarter_label)` under the same lock order.
16. NET-NEW: row-level provenance gates reconstruct expected prompt-visible ticker/global rows and exact PIT-visible audit sets from sealed events. Untrusted rows/audits earn zero authority and report drift.
17. PARTIAL: use `_atomic_write_json` for learner result finalization; current learning finalization is not covered by this read but OperationalHardening identified it as unsafe relative to prediction finalization.
18. PARTIAL: refuse historical learner mutation when PIT boundary is invocation time; invocation-time historical PIT is not replayable.

### `scripts/earnings/validate_learning.py`

1. PARTIAL: bump accepted schema from current `attribution_result.v3` (`scripts/earnings/validate_learning.py:133`) to `attribution_result.v4`, with source-complete legacy v3 accepted only by backfill tooling.
2. PARTIAL: convert current string lesson fields (`scripts/earnings/validate_learning.py:501`) into `lesson_hypothesis.v1` validation: `mechanism_chain`, `applies_when[]`, `invalid_if[]`, `expected_effect`, `scope`, and resolving evidence refs.
3. NET-NEW: validate predicate operator companion fields, boolean negation, missing behavior, and source refs. Reject optional/quorum predicates, stored `observable_status`, non-deterministic predicate operators, and any `predicate_override` field in v0.
4. NET-NEW: derive predicate keys from canonical predicate content; do not require stored `predicate_id`.
5. NET-NEW: validate expected effect direction/confidence effect. Reject no-effect lessons. Do not validate `magnitude_bucket` or exact confidence deltas in v0.
6. PARTIAL: map legacy `cross_ticker` to v4 `peer`; v4 writes use `peer`. Current valid scopes are at `scripts/earnings/validate_learning.py:104`.
7. NET-NEW: validate macro routing by `scope.routing_key` allowlist/predicate evidence, not separate `macro_subtype`.
8. NET-NEW: validate non-ticker candidate birth has candidate `scope.kind`/`scope.routing_key` in the non-ticker set and resolving `transfer_evidence_refs[]`. Derive fresh-birth origin from the sealed co-emitted audit event identity, and derive update/refinement origin from `lineage.parent_lesson_id`'s prior scope/routing key. Reject durable `scope_proof`, stored `transfer_basis`, and stored `birth_scope`/`birth_key`/`destination_scope`/`destination_key`.
9. PARTIAL: replace v3 `review/action` audit semantics (`scripts/earnings/validate_learning.py:107`, `scripts/earnings/validate_learning.py:542`) with v4 `audit_outcome`, simplified `routing_audit`, minimal anomaly detail compatibility, influence/action compatibility, non-sentinel reasons, refine body-change rule, and no bare retire. Reject separate `narrow`; over-routing correction is `action=refine` with a strictly narrower replacement scope/key.
10. NET-NEW: validate `under_routed`, `over_routed`, and `cap_excluded` using the minimal `routing_anomaly` object. Full `routing_audit_detail`, stored birth/destination transfer fields, stored expected/actual render buckets, stored cap name, and candidate-transfer hit/miss labels are invalid in v0.

### `scripts/earnings/renderer/lessons.py` and `scripts/earnings/_text_utils.py`

1. ALREADY-CODED: preserve shared L numbering and body-only ordered lesson text (`scripts/earnings/_text_utils.py:29`, `scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:214`).
2. PARTIAL: render compact fields outside the body: `When`, `Invalid if`, `Effect`, `Mechanism`, and `Why shown`.
3. NET-NEW: render tier/provenance/source markers in marker lines, not in body text.
4. NET-NEW: evaluate applicability before caps; drop deterministic blocked/not-applicable lessons except debug/replay. Render not-testable only when it forces no_call or exposes a key data gap.
5. NET-NEW: derive conflict notes from applicable lessons with opposing non-none effects in the same normalized scope/routing key.
6. NET-NEW: keep `cap_matrix_v0` inline and deterministic for replay/report derivation; renderer, validator anti-lazy checks, and `cap_excluded` derivation must reference the same named matrix.

### `.claude/skills/earnings-prediction/SKILL.md`

1. PARTIAL: preserve existing prompt rules to test `applies_when`/`invalid_if`, avoid lazy skip, use sentinel only for true irrelevance, and cite only confirmed lessons (`.claude/skills/earnings-prediction/SKILL.md:99`, `.claude/skills/earnings-prediction/SKILL.md:104`, `.claude/skills/earnings-prediction/SKILL.md:106`, `.claude/skills/earnings-prediction/SKILL.md:112`, `.claude/skills/earnings-prediction/SKILL.md:114`).
2. NET-NEW: add v2 fields for applicability traces, influence, key-driver evidence source IDs, and lesson influence. Do not add predicate overrides or stored conflict records.
3. NET-NEW: explicitly remove `counter_thesis`; opposing evidence belongs in normal key drivers and evidence IDs, with missing opposing-evidence acknowledgement reported but not authority-capping v0 predictions.
4. NET-NEW: teach anti-lazy all-non-applicable no_call rule and 51-55 directional exception band.
5. NET-NEW: teach unresolved high-quality lesson conflicts require no_call.

### `.claude/skills/earnings-learner/SKILL.md`

1. PARTIAL: preserve existing v3 structured lesson and evidence-ref discipline (`.claude/skills/earnings-learner/SKILL.md:82`, `.claude/skills/earnings-learner/SKILL.md:90`, `.claude/skills/earnings-learner/SKILL.md:94`, `.claude/skills/earnings-learner/SKILL.md:101`).
2. NET-NEW: add v4 `lesson_hypothesis.v1` examples, predicate objects, mechanism chain, direction/confidence effect, and scope/routing key.
3. NET-NEW: add birth rejection rules for generic, mixed, overbroad, unobservable, no-effect, or unsupported lessons.
4. NET-NEW: add simplified audit outcome/action decision tree. Do not add a separate `narrow`; use `refine` for over-routing corrections.
5. NET-NEW: teach ordinary non-ticker scoped candidate birth with candidate scope, transfer refs, and derived origin/destination; do not add `broaden_candidate`, stored `transfer_basis`, stored birth/destination fields, or a transfer row type.
6. NET-NEW: add refinement and dormancy guidance.

### `scripts/earnings/learning_metrics.py`

1. NET-NEW: create one local script with modes `--replay-check`, `--quality-report`, `--lifecycle-gate`, `--backfill-legacy`, and `--reset-failed-recoverable <event_path>`.
2. NET-NEW: implement process-local `EventArtifactIndex` with 4096-entry LRU, source tuple hashes, canonical row projections, emitted lesson maps, audit-verdict maps, and expected audit sets.
3. NET-NEW: `--replay-check --all` scans sealed events and source-complete legacy triples, compares expected caches to live caches, exits non-zero on drift/in-flight/recovery-needed, and emits `LEARNER_ALERT`.
4. NET-NEW: `--quality-report --all` reports missing source rows, failed recovery, human decisions, all-sentinel attempts, Brier/calibration sparse flags, no_call usefulness, citation precision, applicability precision/recall, transfer precision/recall, velocity, and blast radius.
5. NET-NEW: lifecycle gate JSON fails on deterministic health/provenance/blast-radius breaches; Brier/lift fields are `PROVISIONAL` until threshold.
6. NET-NEW: `--backfill-legacy` seals only source-complete legacy events, refuses invocation-time PIT and missing-source rows, and never calls an LLM.
7. NET-NEW: `--reset-failed-recoverable` validates restored sources under event lock before deleting only failed quality events. It never seals or bypasses validation.

### Migration classes

- v0 already-valid: sealed quality event with matching hashes.
- v0 source-complete legacy: full source tuple and v3 learner result; can backfill seal but cannot mint v4 verified credit from legacy audits.
- v0 missing-source: live row/audit lacks source tuple; render only unproven/candidate, no quality credit.
- v0 failed-recovery: artifacts exist but validation/hash/cross-file checks fail; write/report `failed_recoverable` and require repair.
- v0 human-decision: malformed/conflicting/ambiguous/incomplete artifacts; leave unproven until maintenance.

### FCX expected classification

- v0 Q3_FY2025: source-complete legacy candidate because prediction and v3 learning exist in the snapshot.
- v0 Q4_FY2025: missing-source rows because event directory has bundle/rendered/related filing files but no prediction or learning JSON in the snapshot, while cache rows exist.
- v0 Q1_FY2026: current prediction would fail future v2 anti-lazy validation due all lessons irrelevant/sentinel and no lesson citations with a directional call.

## 14. Updated Test Plan

V0 validator tests:

- One schema-strict rejection fixture is parameterized over the cut/deferred-field catalog: optional/quorum predicates, invalid operators or negation companions, missing evidence refs, stored `observable_status`, non-deterministic predicate operators, no-effect lessons, exact confidence deltas, stored predicate IDs, same-body executable refinements, durable `scope_proof`, standalone `macro_subtype`, stored `transfer_state`, stored `transfer_basis`, stored `birth_scope`, stored `birth_key`, stored `destination_scope`, stored `destination_key`, full stored `routing_audit_detail`, stored expected/actual render buckets, stored cap name, stored `correct_nonapplication`, `broaden_candidate`/`de_emphasize`/`narrow` actions, and bare retire.
- `prediction_result.v2` rejects all-sentinel/all-non-applicable directional calls unless the two-driver/two-source non-S10 exception passes, and then caps confidence at 51-55.
- `prediction_result.v2` rejects directional confidence <=50.
- `prediction_result.v2` reports, but does not reject, directional confidence >60 when no key driver with non-S10 source IDs has `direction` opposing the final direction.
- `prediction_result.v2` rejects stored `additional_engagement_source_ids[]`; engagement sources derive from traces and key-driver evidence IDs.
- `prediction_result.v2` rejects any prediction-time predicate override field, invalid influence/verdict combinations, missing traces, unresolved source IDs, invalid binary source family, and illegal citations.
- Shared applicability fixture proves false-plus-missing requires_no_call resolves to `not_applicable` and does not force no_call when a mandatory predicate is false.
- Conflict fixture proves derived unresolved high-quality conflict requires final `no_call`; resolved conflict requires non-S10 key-driver evidence and losing lesson `influence=outweighed`, without any stored conflict array.

V0 novice applicability tests:

- Deterministic pass.
- Invalidator true blocks.
- Missing data requiring no_call.
- Human-only or unobservable lesson is rejected at birth unless represented by supported deterministic predicates.

V0 renderer/ranker tests:

- Body-only ordered lesson text remains unchanged.
- Blocked/not-applicable lessons do not consume caps.
- Proven older lesson outranks unproven recent lesson.
- Ordinary scoped transfer candidate ranks below exact-scope applicable lesson.
- Macro routing key cannot swamp ticker/peer unless deterministic, complete provenance, and strictly higher tier justify conflict handling.

V0 lifecycle/scope tests:

- Promotion requires two distinct source-complete influenced helped audits, zero post-refinement misled, complete provenance, no drift, and no blast-radius breach.
- Promotion and broadening fail on missing source tuple, cache/canonical drift, missing/forged audit rows, failed recovery, human-decision source class, all-sentinel breach, or blast-radius breach.
- `audit_outcome=dormant` is emitted exactly once on the audit event that crosses the eight-PIT-opportunity or four-future-quarter threshold; earlier ordinary non-application events emit no audit row.
- Brier/lift sparse fields are report-only until threshold; lifecycle authority uses deterministic gate before threshold.
- Exclusion can proceed from measured source-complete per-lesson harm plus replay health even when Brier/lift samples are sparse.
- Non-ticker proven promotion requires counted non-birth evidence from distinct destination tickers/source issuers and matching destination scope/routing key.
- Non-ticker ordinary candidate birth requires non-ticker candidate scope and resolving transfer evidence refs, derives origin/destination from candidate scope, sealed auditor event identity, and lineage, rejects stored birth/destination fields, and enters the bounded transfer pool; no candidate-transfer row type or stored transfer-basis field exists in v0.
- `under_routed`, `over_routed`, and `cap_excluded` require the minimal `routing_anomaly` object and produce replayable scope precision/recall rows; one parameterized fixture covers the three anomaly types.
- Normal transfer successes with `routing_audit=none` derive destination and candidate-only/independent proof from canonical lesson fields, transfer refs, and sealed auditor event identity.

V0 metrics/replay/operational tests:

- Brier monotonicity for directional calls, including 51-55 anti-lazy exception band.
- No_call usefulness and unknown-range denominator.
- Citation precision excludes `outweighed`.
- Applicability precision/recall derive from prediction-time and learner verdict pairs, not audit prose.
- Transfer precision/recall derive from bounded pools, minimal routing anomaly fields, and simplified routing audit.
- `cap_matrix_v0` consistency: renderer replay, anti-lazy counted-rendered-lesson checks, and `cap_excluded` derivation all reference the same ticker 8 / sector 4 / macro 4 / peer 2 matrix.
- Blocking tests are limited to replay/provenance/locks/anti-lazy/conflict no_call/validator schema. Report-only Brier, no_call, calibration, and transfer metrics get schema and denominator smoke tests until activation thresholds are met.
- Event/ticker/global lock order cannot deadlock; D22 checks run inside locks.
- Crash after learner result, ticker append, global append, audit aggregation, or quality seal converges or reports `failed_recoverable` without duplicates.
- Save-time commitment rejects unknown keys, altered prompt sidecar, altered rendered prompt, and altered bundle payload.
- Replay-check exits non-zero and emits `LEARNER_ALERT` for extra rows, missing rows, hash drift, in-flight locks, failed recovery, and incomplete events.
- Q3 FCX can be backfilled as source-complete legacy; Q4 FCX remains missing-source/unproven; Q1 FCX fails v2 anti-lazy validation.

Moved to v1 backlog tests:

- Per-lesson magnitude bucket authority.
- Dedicated candidate-transfer row type and candidate-transfer hit/miss strata.
- Full stored `routing_audit_detail` object, stored render buckets, or stored cap name beyond the minimal anomaly fields.
- Prediction-time predicate overrides.
- Stored conflict records and authority-changing opposing-evidence caps.
- LLM ablation/tournament authority.
- Brier/lift authority gate below activation threshold.
- Separate reset utility.

## 15. Judge Findings and Round Log

Round 1 status: REJECTED and revised into Round 2.

Required judges:

- Judge A Cutter-Claude: valid JSON after approved rerun outside sandbox. Verdict REJECT. Scores: A4 B4 C5 D5 E4 F4 G5 H4 I5 J5. Main should-fix items: derive `_render_warnings[]`; derive `additional_engagement_source_ids[]`; derive `correct_nonapplication`; cut `lineage.supersedes_reason`; derive `de_emphasize`; merge/remove `broaden_candidate`; derive `predicate_id`; narrow predicate/source/transfer/confidence/observable enums. It also supported cuts to `counter_thesis`, `magnitude_bucket`, `macro_subtype`, `transfer_state`, full routing details, candidate-transfer rows, sparse statistical gates, and separate reset utility.
- Judge B Cutter-Codex: valid JSON. Verdict REJECT. Scores: A4 B2 C4 D5 E4 F3 G4 H2 I3 J4. Blockers: remaining schema fields with cheaper derivations (`routing_audit`, `broaden_candidate`, `lesson_conflicts`, `additional_engagement_source_ids`, predicate overrides) and oversized v0 tests. Accepted deferral/cuts for candidate-transfer rows, `counter_thesis`, `magnitude_bucket`, sparse Brier/lift gates, and separate reset utility. Round 2 accepts the derivable-field/test-surface cuts except where preservers identified a PT6 or PT4 floor.
- Judge C Preserver-Claude: first output contained prose plus JSON; one required JSON-only retry also contained prose before JSON. Recorded as `REJECT_MALFORMED` for Round 1. Its embedded advisory text accepted the main cuts and suggested enumerating macro routing keys and clarifying transfer-state derivation, but it is not counted as an ACCEPT.
- Judge D Preserver-Codex: valid JSON. Verdict REJECT. Scores: A5 B4 C3 D4 E4 F5 G4 H4 I5 J3. Blockers: PT6 transfer recall was not self-contained after deferring candidate-transfer rows, and deriving all routing detail made anomaly proof too prose-like. Should-fix: cutting `counter_thesis` needed validator-visible opposing-evidence discipline, status should be standard, and transfer tests needed the pruned denominator.

Round 1 synthesis applied in Round 2:

- CUT/DERIVE: `additional_engagement_source_ids[]`, stored `predicate_id`, `lineage.supersedes_reason`, `correct_nonapplication`, `de_emphasize`, `broaden_candidate` action, stored `_render_warnings[]`.
- SIMPLIFY: predicate operator enum to five operators plus negation; `observable_status` to deterministic/non-deterministic; `source_family` to lesson/non-lesson; `transfer_basis` to three values; exact confidence deltas to `confidence_effect`.
- PRESERVE SMALLER FORM: no candidate-transfer row type. Round 2 initially kept explicit birth/destination proof; later rounds derive transfer basis, and Round 16 derives birth/destination from candidate scope, sealed auditor identity, lineage, and transfer refs so bounded transfer-pool membership remains replayable.
- PRESERVE SMALLER FORM: no full `routing_audit_detail`, but minimal `routing_anomaly` survives for non-none routing audits to make under-routed/over-routed/cap-excluded proof machine-readable.
- PRESERVE SMALLER FORM: no stored `counter_thesis`, but high-confidence opposing-evidence cap derives from existing key-driver direction and non-S10 source IDs.

Round 2 status: draft prepared, judges not yet run.

Round 2 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 2 judging.

Round 2 status: REJECTED and revised into Round 3.

- Judge A Cutter-Claude: valid JSON. Verdict REJECT. Scores: A4 B4 C5 D5 E5 F5 G5 H4 I5 J5. Main should-fix items: derive stored `lesson_conflicts[]`; derive `routing_anomaly.birth_scope`, `birth_key`, and `cap_name`; collapse transfer-basis candidate values; reduce duplicated operational tests. It accepted/defended the main Round 2 cuts and preserved operational floors.
- Judge B Cutter-Codex: valid JSON. Verdict REJECT. Scores: A4 B3 C4 D5 E4 F4 G5 H3 I3 J4. Blockers: stored `lesson_conflicts[]`, prediction-time predicate overrides, derived opposing-evidence cap; should-fix items: trim routing anomaly fields, simplify non-ticker transfer candidate birth, separate blocking tests from report-smoke tests, and revisit `non_deterministic` predicate state.
- Judge C Preserver-Claude: first output malformed with prose before JSON; required JSON-only retry produced valid JSON. Verdict ACCEPT. Scores: A5 B5 C5 D5 E5 F5 G4 H5 I5 J5. Findings were nits: restate no-effect rejection under binary confidence effect, clarify conflict threshold, and require/preserve key-driver direction if using the derived opposing cap.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the ordinary non-ticker candidate birth replacement, minimal routing anomaly, derived transfer state, enum narrowing, and pruned tests as preserving PT1-PT9/Round 12.

Round 2 synthesis applied in Round 3:

- CUT/DERIVE: stored `lesson_conflicts[]`; validator derives high-quality conflicts and enforces no_call/resolution from existing lesson effects, applicability traces, key-driver evidence, final direction, and influence.
- DEFER_TO_V1: prediction-time predicate overrides. V0 evaluator is authoritative; missing/bad evaluator coverage becomes `not_testable_missing_data`, `no_call`, or a bundle-feature request.
- CUT: authority-changing opposing-evidence confidence cap. Missing opposing evidence on high-confidence calls becomes report-only because anti-lazy/source-grounding already covers the named Q1 blocker.
- SIMPLIFY: `routing_anomaly` no longer duplicates birth scope/key; those derive from the canonical lesson row. It keeps cap/render fields for now because preservers linked them to replayable PT6 anomaly proof.
- SIMPLIFY: `transfer_basis` collapsed to `candidate_only` versus `independent_non_birth_evidence`.
- SIMPLIFY: report-only metric tests are schema/denominator smoke tests until activation thresholds; blocking tests focus on replay/provenance/locks/anti-lazy/conflict/schema.

Round 3 status: REJECTED and revised into Round 4.

Round 3 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 3 judging.

- Judge A Cutter-Claude: valid JSON. Verdict REJECT. Scores: A4 B5 C5 D5 E5 F5 G5 H4 I5 J5. Should-fix items: derive stored `transfer_basis`, derive `routing_anomaly.cap_name`, cut `observable_status`, and merge `action=narrow` into `refine`. Nits: consolidate routing-audit tests into a parameterized fixture and rename the lifecycle gate CLI mode.
- Judge B Cutter-Codex: valid JSON. Verdict REJECT. Scores: A4 B3 C4 D5 E4 F4 G5 H3 I3 J4. Blockers: route anomaly still stored replay-derived render/cap fields, `candidate_only` transfer basis was a stored default, and `non_deterministic` observable status survived without v0 proof. Should-fix: remove stale v0 override wording and top-level conflict-record wording.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits: leave opposing-evidence cap report-only, add derivation pointers for transfer state, and keep the cap matrix visible where renderer/replay uses it.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted derived conflict sets, v1 predicate overrides, report-only opposing evidence, minimal routing anomaly, ordinary non-ticker candidate births, derived transfer state, merged macro subtype, and Round 12 floors.

Round 3 synthesis applied in Round 4:

- DERIVE: stored `transfer_basis`; candidate-only versus independent non-birth proof now derives from transfer refs, sealed event identity, destination scope/key, and counted future helped audits.
- DERIVE: stored routing anomaly replay outputs; `expected_render_bucket`, `actual_render_bucket`, and cap name now derive from deterministic renderer replay/report, while the stored anomaly keeps only destination scope/key and non-S10 routing source IDs.
- CUT: stored `observable_status`; v0 predicate operators are deterministic by construction, and human-only or unobservable lesson birth is rejected or becomes a bundle-feature request.
- MERGE: `action=narrow` into `action=refine` with `routing_audit=over_routed` and a strictly narrower replacement scope/key.
- CLEANUP: stale v0 references to override source IDs, top-level conflict records, and stored additional engagement source IDs are removed from the active roadmap/proof text.
- SIMPLIFY: `learning_metrics.py --quality-report --gate lifecycle` is renamed to `--lifecycle-gate`, and routing-audit tests are expressed as one parameterized anomaly fixture.

Round 4 status before judging: draft prepared.

Round 4 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 4 judging.

Round 4 status: REJECTED_MALFORMED on the Claude cutter leg and revised into Round 5.

- Judge A Cutter-Claude: first output contained prose before JSON and therefore was malformed. The required JSON-only retry produced an empty output, so Round 4 Judge A is recorded as `REJECT_MALFORMED`. The malformed advisory JSON was not counted as an ACCEPT; it flagged small fixable issues: Ledger 1 arithmetic, a missing inline S10 definition, and over-expanded forbidden-field test wording.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 4 cuts and derivations for routing anomaly fields, `transfer_basis`, `observable_status`, `action=narrow`, predicate overrides, conflict records, engagement-source IDs, `counter_thesis`, `macro_subtype`, `transfer_state`, candidate-transfer rows, `magnitude_bucket`, Brier/lift gates, reset utility, and v0 test pruning.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits only: add an explicit v0 `predicate_override` rejection note and cross-reference the single cap matrix from prediction validation.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 4 cuts as preserving PT1-PT9 and Round 12.

Round 4 synthesis applied in Round 5:

- FIX: Ledger 1 total now matches its rows: final 57, delta -51, 47.2% overall reduction and 60.7% lesson-intelligence-only reduction.
- CLARIFY: Section 7 defines S10/non-S10 inline; S10 means lesson-internal/rendered-lesson source IDs and never counts as independent evidence.
- CLARIFY: implementation steps explicitly reject `predicate_override` in v0.
- CLARIFY: prediction validation cross-references the single inline renderer cap matrix for anti-lazy counted lessons and `cap_excluded` derivation.
- SIMPLIFY: forbidden-field validation tests are one parameterized schema-strict fixture over the cut/deferred-field catalog.

Round 5 status: draft prepared, judges not yet run.

Round 5 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 5 judging.

Round 5 status: REJECTED_MALFORMED on the Claude cutter leg and revised into Round 6.

- Judge A Cutter-Claude: first output contained prose before JSON and therefore was malformed. The required JSON-only retry produced an empty output, so Round 5 Judge A is recorded as `REJECT_MALFORMED`. Its malformed advisory JSON was not counted as an ACCEPT; it otherwise showed ACCEPT/all scores 5 and only clarity nits.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It recomputed Ledger 1, verified the S10 definition, confirmed predicate overrides are v1, accepted cap-matrix derivation, and found no remaining cut/merge/derive/defer opportunities.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 4 fixes and stated no remaining v0 cuts, merges, derivations, or deferrals without regression.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 5 draft as preserving PT1-PT9 and Round 12.

Round 5 synthesis applied in Round 6:

- CLARIFY: the anti-lazy rule now explicitly states that counted rendered lessons use the same inline cap matrix as renderer replay and `cap_excluded` derivation.
- CLARIFY: non-ticker candidate birth no longer says vague "destination routing fields"; the destination scope/key pair is the destination routing proof.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, or test mechanism changed after Round 5; this pass only removes wording ambiguity from malformed Judge A's advisory text.

Round 6 status: draft prepared, judges not yet run.

Round 6 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 6 judging.

Round 6 status: ACCEPTED_WITH_NITS and revised into Round 7.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits: clarify `unproven/missing-provenance` as a provenance marker rather than a fifth lifecycle tier, and define peer-list key canonicalization.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It found no remaining v0 cuts, merges, derivations, or deferrals without regression.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 6 wording clarifications and preservation of PT1-PT9/Round 12.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 6 wording clarifications and preservation of PT1-PT9/Round 12.

Round 6 synthesis applied in Round 7:

- CLARIFY: peer-list routing keys are sorted, deduplicated, comma-joined ticker tuples; other peer key forms are invalid.
- CLARIFY: `unproven` and `missing-provenance` are render/provenance markers on `candidate`, not lifecycle tiers.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, or test mechanism changed after Round 6; this pass only addresses two cutter nits.

Round 7 status: draft prepared, judges not yet run.

Round 7 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 7 judging.

Round 7 status: ACCEPTED_WITH_NITS and revised into Round 8.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits: canonicalize `source_family` instead of allowing `source_origin` as an equivalent v0 field, and remove unused `prompt-only rule = 1` from the ledger vocabulary.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the peer-list canonicalization, candidate provenance marker, anti-lazy cap matrix, transfer replacement, predicate override deferral, counter-thesis cut, macro merge, transfer derivations, routing simplification, and test plan.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted all pruning decisions and preservation of PT1-PT9/Round 12.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted all pruning decisions and preservation of PT1-PT9/Round 12.

Round 7 synthesis applied in Round 8:

- CLARIFY: `source_family` is the canonical v0 field; legacy `source_origin` is only a backfill alias normalized before v0 validation.
- CLARIFY: unused `prompt-only rule = 1` was removed from the ledger weight vocabulary.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, or test mechanism changed after Round 7; this pass only addresses two cutter nits.

Round 8 status: draft prepared, judges not yet run.

Round 8 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 8 judging.

Round 8 status: ACCEPTED_WITH_NITS and revised into Round 9.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. One nit: clarify that `audit_outcome=dormant` is a single dormancy-trigger audit event, not an ordinary non-application row or a stored lifecycle hook.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the source-family canonicalization, peer-list key canonicalization, provenance marker wording, anti-lazy cap matrix, non-ticker transfer proof, transfer derivations, macro merge, predicate override deferral, counter-thesis cut, routing simplification, and pruned tests.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted all Round 8 cuts/merges/derivations/deferrals as preserving PT1-PT9, Q1/Q4 defenses, recency crowd-out fix, broad sector promotion guard, and Round 12.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the same pruning decisions and preservation of PT1-PT9/Round 12.

Round 8 synthesis applied in Round 9:

- CLARIFY: `audit_outcome=dormant` is emitted only on the one audit event that triggers the derived dormant tier, after eight PIT-valid opportunities or four future-quarter labels with zero applies and no data-missing blocker. Ordinary correct non-application still emits no row.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, or test mechanism changed after Round 8; this pass only addresses one cutter nit.

Round 9 status: draft prepared, judges not yet run.

Round 9 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 9 judging.

Round 9 status: REJECTED and revised into Round 10.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits: add a dormant-trigger lifecycle fixture and add an inline anchor for the two-counted-helped-audit transfer threshold.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the dormant clarification, all cuts/merges/derivations/deferrals, operational floor, anti-lazy Q1 defense, Q4 provenance caps, and PT1-PT9 coverage.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 9 dormant clarification and preservation of PT1-PT9/Round 12.
- Judge D Preserver-Codex: valid JSON. Verdict REJECT. Scores: A4 B5 C4 D3 E4 F5 G3 H4 I5 J4. Blocker: blast-radius breach was referenced as an authority gate but lacked a self-contained threshold/grouping rule. Should-fix: restore the quality-event non-self-referential hash convention in the active operational substrate.

Round 9 synthesis applied in Round 10:

- RESTORE: blast-radius breach definition is now explicit: more than 25% of verified misled cited outcomes in the rolling 50 completed directional calls for a single lesson lineage family or deterministic near-clone cluster; near-clone clustering is retained from OperationalHardening as a local derived grouping, not stored state.
- RESTORE: the quality-event non-self-referential hash convention is now stated in the v0 Operational Substrate, while the existing implementation-step convention remains.
- CLARIFY: transfer-state derivation now anchors `candidate_transfer` and `proven_transfer` to the non-ticker two-counted-helped-audit promotion threshold.
- TEST: Section 14 now includes the single-emission `audit_outcome=dormant` fixture requested by Judge A.
- NO PRODUCTION CHANGE: no code or corpus edits; only this plan and temporary judge files changed.

Round 10 status: draft prepared, judges not yet run.

Round 10 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 10 judging.

Round 10 status: ACCEPTED_WITH_NITS and revised into Round 11.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits: define `changed_confidence` without relying on parent-plan ECE-bin wording; leave `applicability_verdict_at_prediction` stored in v0 but flag possible v1 derivation; leave `lineage.refined_from_audit_key` stored in v0 but flag possible v1 derivation if replay scans prove cheap.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the restored quality-event hash convention, blast-radius threshold/grouping rule, dormant fixture, transfer threshold anchor, and all cuts/merges/derivations/deferrals.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 10 fixes and preservation of PT1-PT9/Round 12.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 10 fixes to the Round 9 rejection and found no remaining v0 cuts, merges, derivations, or deferrals without regression.

Round 10 synthesis applied in Round 11:

- CLARIFY: `changed_confidence` is now self-contained: a lesson changes final confidence by at least 5 points; ECE-bin authority remains v1 and is not needed for v0 influence classification.
- DEFER/EVALUATE: possible v1 derivation of `applicability_verdict_at_prediction` from `prediction_result.v2.lesson_labels[].applicability_verdict` is recorded, but v0 keeps the audit-row snapshot to avoid cross-artifact replay joins.
- DEFER/EVALUATE: possible v1 derivation of `lineage.refined_from_audit_key` from refine audit rows is recorded, but v0 keeps the direct pointer for replay efficiency and same-body refinement safety.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, or test mechanism changed after Round 10; this pass only addresses cutter nits and v1-evaluation notes.

Round 11 status: draft prepared, judges not yet run.

Round 11 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 11 judging.

Round 11 status: ACCEPTED_WITH_NITS and revised into Round 12.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits: the inline cap matrix was repeated in multiple consumers with mild drift risk; the two v1 derivation backlog notes for `applicability_verdict_at_prediction` and `lineage.refined_from_audit_key` should remain v1-only evaluation notes rather than v0 cuts.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 11's changed-confidence threshold, v1-evaluation backlog notes, all cuts/merges/derivations/deferrals, and preservation of PT1-PT9/Round 12.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 11's wording and found no remaining v0 cuts, merges, derivations, or deferrals without regression.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 11's wording and preservation of the operational substrate, anti-lazy Q1 defense, Q4 caps, PT6 transfer proof, and self-contained roadmap.

Round 11 synthesis applied in Round 12:

- CLARIFY: the renderer/validator cap constants are now named once as `cap_matrix_v0` (ticker 8, sector 4, macro 4, peer 2), and every consumer references that name.
- TEST: Section 14 now includes a `cap_matrix_v0` consistency assertion across renderer replay, anti-lazy counted-rendered-lesson checks, and `cap_excluded` derivation.
- CLARIFY: Section 12 states that the final two derivation entries are v1 evaluation notes only and intentionally keep the v0 fields stored until replay joins/scans prove deterministic, cheap, and non-regressive.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, or test mechanism changed after Round 11; this pass only addresses cutter nits.

Round 12 status: draft prepared, judges not yet run.

Round 12 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 12 judging.

Round 12 status: CLEAN SATURATION ROUND 1.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It found no remaining v0 cuts, merges, derivations, or deferrals without regression and accepted `cap_matrix_v0`, the v1-only derivation notes, all prior cuts/merges/derivations/deferrals, and the Round 12 floor.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted `cap_matrix_v0`, the cap-matrix consistency test, v1-only derivation notes, all pruning decisions, and preservation of PT1-PT9/Round 12.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 12's cap-matrix consolidation, v1-only derivation notes, and preservation of PT1-PT9, Q1/Q4 defenses, PT6 transfer/scope proof, and self-contained implementability.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 12's cap-matrix and v1-note fixes and found no remaining v0 cuts, merges, derivations, or deferrals without regression.

Round 12 synthesis applied in Round 13:

- NO CHANGE: Round 12 was a clean saturation round. No schema, lifecycle, authority, test, or roadmap mechanism changed for Round 13.
- SATURATION STATUS: one consecutive clean saturation round is complete; one more clean round is required before final completion.

Round 13 status: draft prepared, judges not yet run.

Round 13 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 13 judging.

Round 13 status: ACCEPTED_WITH_NITS and revised into Round 14.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It found no remaining v0 cuts, merges, derivations, or deferrals without regression.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 13 with all cuts/merges/derivations/deferrals, PT1-PT9, and Round 12 invariants preserved.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. One nit: anchor the report-only opposing-evidence warning in the v0 Prediction Contract so an implementer reading Section 7 sees the trigger directly.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 13 with PT1-PT9, Q1/Q4 defenses, PT6 transfer proof, and Round 12 invariants preserved.

Round 13 synthesis applied in Round 14:

- CLARIFY: the v0 Prediction Contract now anchors the existing report-only opposing-evidence warning trigger: directional confidence >60 with no opposing non-S10 key-driver evidence. The warning remains report-only and cannot reject, cap authority, or restore `counter_thesis`.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, or test mechanism changed after Round 13; this pass only addresses one preserver nit.
- SATURATION STATUS: Round 13 does not count as a clean saturation round because the valid accepting judge output included a nit. The consecutive clean streak resets; two clean rounds are still required.

Round 14 status: draft prepared, judges not yet run.

Round 14 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 14 judging.

Round 14 status: CLEAN SATURATION ROUND 1.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It found no remaining v0 cuts, merges, derivations, or deferrals without regression after the report-only opposing-evidence warning anchor.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It re-attacked every surviving mechanism and accepted the current cuts/merges/derivations/deferrals, `cap_matrix_v0`, v1-only derivation notes, PT1-PT9, and Round 12 floor.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 14 anchor without restoring `counter_thesis` or any authority-changing cap, and found PT1-PT9/Round 12 preserved.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the cuts to stored `counter_thesis`, `magnitude_bucket`, standalone `macro_subtype`, stored transfer fields, observable status, candidate-transfer rows, routing details, sparse gates, dense strata, and reset utility.

Round 14 synthesis applied in Round 15:

- NO CHANGE: Round 14 was a clean saturation round. No schema, lifecycle, authority, test, or roadmap mechanism changed for Round 15.
- SATURATION STATUS: one consecutive clean saturation round is complete after the Round 13 nit reset; one more clean round is required before final completion.

Round 15 status: draft prepared, judges not yet run.

Round 15 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 15 judging.

Round 15 status: REJECTED and revised into Round 16.

- Judge A Cutter-Claude: valid JSON. Verdict REJECT. Scores: A5 B4 C5 D5 E4 F4 G5 H5 I5 J5. Should-fix: derive non-ticker candidate-birth `birth_scope`, `birth_key`, `destination_scope`, and `destination_key` from candidate scope, sealed co-emitted audit identity, lineage, and transfer refs instead of storing duplicate fields. Nits: update the fixture so those four fields are rejected, and keep the opposing-evidence warning clearly authority-free rather than PT2 load-bearing.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It re-attacked all major surviving mechanisms and found no remaining cuts, merges, derivations, or deferrals without regression.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It found Round 15 preserved PT1-PT9, Round 12 invariants, and all agreed cuts/deferrals.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 15 state, including the report-only opposing-evidence warning, transfer derivations, `cap_matrix_v0`, and pruned tests.

Round 15 synthesis applied in Round 16:

- DERIVE: non-ticker candidate transfer origin/destination no longer stores `birth_scope`, `birth_key`, `destination_scope`, or `destination_key`. Destination derives from the candidate lesson's own scope/routing key; fresh origin derives from the sealed co-emitted audit event identity; update/refinement origin derives from `lineage.parent_lesson_id`'s prior scope/routing key; source-complete proof still requires resolving `transfer_evidence_refs[]`.
- TEST: the schema-strict rejection fixture now includes the four cut birth/destination fields, and the non-ticker candidate-birth fixture now requires candidate scope plus transfer refs while rejecting those stored fields.
- CLARIFY: the opposing-evidence warning is authority-free quality-report output only. It does not reject, cap authority, count as PT2 coverage, or restore `counter_thesis`.
- LEDGER NOTE: this cut is within the existing one-point minimal bounded-transfer proof row, so Ledger 1's weighted total remains 57. The proof is stricter but the coarse weighted accounting does not change.
- SATURATION STATUS: Round 15 rejected, so the consecutive clean streak resets; two clean rounds are still required.

Round 16 status: draft prepared, judges not yet run.

Round 16 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 16 judging.

Round 16 status: ACCEPTED_WITH_NITS and revised into Round 17.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. Findings were nits: clarify that `routing_source_ids[]` may overlap with audit `evidence_refs[]` but must independently prove destination scope/key relevance with non-S10 IDs, and anchor sealed audit identity to the existing `quality_event.json` identity rather than a new identity object.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 16 transfer-field derivation, forbidden-field tests, authority-free opposing-evidence warning, PT1-PT9 proof, and Round 12 floor.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 16's transfer tightening and all prior cuts/merges/derivations/deferrals without PT1-PT9 or Round 12 regression.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the derived transfer origin/destination, bounded transfer pool, minimal routing anomaly, authority-free warning, `cap_matrix_v0`, and v1-only derivation notes.

Round 16 synthesis applied in Round 17:

- CLARIFY: sealed co-emitted audit identity for transfer origin is the existing `quality_event.json` identity `(event_path, ticker, quarter_label)`, not a new stored identity object.
- CLARIFY: `routing_source_ids[]` may share IDs with audit `evidence_refs[]`, but must independently resolve to non-S10 catalog IDs proving destination scope/key relevance.
- NO MATERIAL CHANGE: no schema, lifecycle, authority, test, or roadmap mechanism changed after Round 16; this pass only addresses two cutter nits.
- SATURATION STATUS: Round 16 does not count as clean because the valid accepting judge output included nits. The consecutive clean streak resets; two clean rounds are still required.

Round 17 status: draft prepared, judges not yet run.

Round 17 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 17 judging.

Round 17 status: NOT CLEAN and revised into Round 18.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. It reported one no-fix nit confirming that Round 17 only contained the two Round 16 clarifications and that no new plan change was required. Because clean-score nit passes are not clean saturation, this still breaks the clean streak.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted all cuts/merges/derivations/deferrals, the transfer-origin derivation, forbidden birth/destination fields, authority-free warning, `cap_matrix_v0`, and Round 12 floor.
- Judge C Preserver-Claude: first output was malformed JSON. The required retry with `YOUR PRIOR OUTPUT WAS MALFORMED. EMIT ONLY THE REQUIRED JSON.` produced empty output and is recorded as `REJECT_MALFORMED`.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted the Round 17 transfer identity and routing-source clarifications, PT1-PT9, and Round 12 invariants.

Round 17 synthesis applied in Round 18:

- NO MATERIAL CHANGE: no schema, lifecycle, authority, test, roadmap, or audit mechanism changed after Round 17. The Round 17 plan already contained the Round 16 clarifications.
- JUDGE-HYGIENE NOTE: Round 18 judge prompts instruct judges not to use `findings[]` for no-op confirmations. If no actual plan change is required, `findings` must be empty.
- SATURATION STATUS: Round 17 does not count as clean because Judge A included a nit and Judge C was malformed after retry. The consecutive clean streak resets; two clean rounds are still required.

Round 18 status: draft prepared, judges not yet run.

Round 18 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 18 judging.

Round 18 status: CLEAN SATURATION ROUND 1.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It found no remaining v0 cuts, merges, derivations, or deferrals without regression.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It re-attacked all surviving mechanisms and accepted the transfer-origin derivation, forbidden birth/destination fields, authority-free warning, `cap_matrix_v0`, v1-only derivation notes, PT1-PT9, and Round 12 floor.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 18 with PT1-PT9 and Round 12 invariants preserved.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted transfer derivation, minimal routing proof, authority-free warning, cap matrix, v1 notes, and Round 12 floor.

Round 18 synthesis applied in Round 19:

- NO CHANGE: Round 18 was a clean saturation round. No schema, lifecycle, authority, test, roadmap, or audit mechanism changed for Round 19.
- SATURATION STATUS: one consecutive clean saturation round is complete; one more clean round is required before final completion.

Round 19 status: draft prepared, judges not yet run.

Round 19 drift check: PASS. The source/corpus mtimes and sizes for every cited non-output file still match the Section 0 snapshot before Round 19 judging.

Round 19 status: CLEAN SATURATION ROUND 2.

- Judge A Cutter-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It found no remaining v0 cuts, merges, derivations, or deferrals without regression.
- Judge B Cutter-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It re-attacked all surviving mechanisms, PT1-PT9, the `cap_matrix_v0`, v1-only derivation notes, transfer derivations, report-only sparse gates, and the Round 12 operational floor.
- Judge C Preserver-Claude: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted Round 19 with no PT1-PT9, replay, PIT, provenance, anti-lazy, scope-proof, or self-contained roadmap regression.
- Judge D Preserver-Codex: valid JSON. Verdict ACCEPT with all scores 5. No findings. It accepted derived transfer origin/destination, counter-thesis cut, magnitude deferral, macro merge, candidate-transfer row deferral, minimal routing anomaly, report-only sparse gates, `cap_matrix_v0`, v1 notes, and the Round 12 floor.

Completion synthesis:

- Rounds 18 and 19 are consecutive clean saturation rounds after the Round 17 malformed/not-clean reset.
- Minimum rounds requirement is satisfied.
- All four judges in both clean rounds produced valid JSON, verdict ACCEPT, all rubric scores 5/5, and `findings: []`.
- PT1-PT9 and Round 12 operational invariants are preserved.
- No remaining v0 cuts, merges, derivations, simplifications, or deferrals were identified without regression.
- Only this plan and temporary `/tmp` judge files changed.

## 16. Final Audit

Current audit status: COMPLETE. Round 19 completed the second consecutive clean saturation round.

- Is this strictly smaller than final LessonIntelligence? Yes. Ledger 1 records a 47.2% weighted reduction and a 60.7% reduction on the lesson-intelligence-only surface; the Round 18 and Round 19 clean judge panels accepted the reduction.
- What exactly was cut/merged/derived/deferred? Cut: stored `counter_thesis`, authority-changing opposing-evidence cap, stored `additional_engagement_source_ids[]`, stored `predicate_id`, stored `observable_status`, stored `birth_scope`, stored `birth_key`, stored `destination_scope`, stored `destination_key`, `lineage.supersedes_reason`, `correct_nonapplication`, `broaden_candidate` action, `de_emphasize` action, `narrow` action, stored `_render_warnings[]`, stored conflict records, stored routing cap/bucket replay outputs, and tests for cut/deferred mechanisms. Merged/simplified: `macro_subtype` into `scope.routing_key`, per-lesson conflict handling into validator-derived conflict checks, candidate-transfer hit/miss values into audit outcome plus candidate scope/source refs, separate reset utility into `learning_metrics.py`, full routing detail into minimal anomaly-only object, and wide enums into smaller closed enums. Derived: `transfer_state`, `transfer_basis`, transfer origin/destination, conflict sets, engagement source IDs, predicate keys, correct non-application, de-emphasis, render warnings, routing cap/bucket report fields, and opposing-evidence report warnings. Deferred: `magnitude_bucket`, prediction-time predicate overrides, dedicated candidate-transfer rows, dense strata, sparse statistical authority gates, LLM ablation/tournament.
- Do PT1-PT9 still pass? Yes. Both clean saturation rounds accepted PT1-PT9 preservation with no findings.
- Are Round 12 invariants preserved? Yes. Both clean saturation rounds accepted the quality event, full prediction source tuple, row-level provenance, replay/report, locks, alerts, and additive migration floor.
- Is the roadmap self-contained? Yes. The plan includes implementation steps, tests, migration classes, and failure coverage, and both clean saturation rounds accepted it.
- Were production/corpus/code files changed? No. Only this allowed plan file plus temporary judge prompt/output files under `/tmp` have been created/updated.
- Saturation gate: PASS. The plan ran more than the minimum three rounds, handled malformed output per rule, reset on nits/malformed output, and completed two consecutive clean saturation rounds in Rounds 18 and 19.
