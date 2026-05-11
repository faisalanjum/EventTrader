# EventMarketDB Learner Loop - Lesson Intelligence

## 0. Status, Round, and Requirement Coverage Matrix

Status: COMPLETE
Round: 14 complete after consecutive saturation
Last updated: 2026-05-11

Design-only guardrail: this goal may write only this plan file plus temporary judge files under `/tmp`. It does not edit production code, live corpus JSON, skill prompts, or existing plan files.

Operational-hardening pre-check: PASS. `.claude/plans/LearnerLoopPlan_OperationalHardening.md` exists and reports `Status: complete operational hardening plan`, `Round: 15 complete after consecutive saturation`, and `Current status: complete` (`.claude/plans/LearnerLoopPlan_OperationalHardening.md:3`, `.claude/plans/LearnerLoopPlan_OperationalHardening.md:4`, `.claude/plans/LearnerLoopPlan_OperationalHardening.md:796`). This plan therefore inlines the required operational substrate instead of treating that prior file as an implementation dependency.

Current source snapshot for drift checks, captured before this draft:

| Path | Size | Mtime epoch |
|---|---:|---:|
| `scripts/earnings/earnings_orchestrator.py` | 184712 | 1778077720 |
| `scripts/earnings/validate_learning.py` | 30511 | 1777902243 |
| `scripts/earnings/renderer/lessons.py` | 12847 | 1777906264 |
| `scripts/earnings/_text_utils.py` | 3717 | 1777910170 |
| `.claude/skills/earnings-prediction/SKILL.md` | 22297 | 1778253165 |
| `.claude/skills/earnings-learner/SKILL.md` | 26572 | 1778250654 |
| `earnings-analysis/learnings/global.json` | 6998 | 1777992410 |
| `earnings-analysis/learnings/ticker/FCX.json` | 21143 | 1777992410 |
| `.claude/plans/LearnerLoopPlan_OperationalHardening.md` | 109678 | 1778518284 |
| `.claude/plans/LearnerLoopPlan_SimplifiedQuality.md` | 58491 | 1778501656 |
| `.claude/plans/LearnerLoopPlan.md` | 100806 | 1778480337 |
| `.claude/plans/LearnerLoop.md` | 24392 | 1778474092 |
| `.claude/plans/lessons-lifecycle-playground.html` | 157666 | 1778241110 |

Event corpus snapshot for cited FCX evidence is recorded in Section 16. Any cited source or corpus path changing during judge rounds must change this status to CORPUS_DRIFT_DETECTED and stop for human acknowledgement.

Requirement coverage:

| Requirement | Coverage | Status |
|---|---|---|
| R1 no ambiguity about when lessons apply | Sections 3, 4, 6, 9, 14 define predicate traces, invalidator traces, and novice applicability test. | Complete in draft |
| R2 textbook-case application | Sections 3, 4, 6, 7 require all predicates true, invalidators false, mechanism chain present, and effect declared before high authority. | Complete in draft |
| R3 not too broad | Sections 7, 8, 10, 11 add false-positive audits, scope narrowing, candidate-transfer caps, and precision metrics. | Complete in draft |
| R4 not too narrow | Sections 7, 8, 10, 11 add missed-applicable audits, dormant/deadness separation, recall metrics, and candidate transfer. | Complete in draft |
| R5 formula-like mechanism | Sections 3, 4, 6 define `IF predicates AND NOT invalidators THEN expected_effect BECAUSE mechanism_chain`. | Complete in draft |
| R6 simple enough for non-expert predictor | Sections 3, 6, 9 require compact rendered fields, source IDs, conflict/no_call instructions, and no hidden market intuition. | Complete in draft |
| R7 lifecycle birth through transfer | Section 7 covers birth, validation, ranking, rendering, application, audit, promotion, refinement, retirement, and transfer. | Complete in draft |
| R8 re-examine hardcoded lifecycle | Sections 5 and 7 replace active/watch/retired authority with count-based evidence tiers, dormant/deadness, and deterministic replay/report gates. | Complete in draft |
| R9 lifecycle events create evidence | Sections 7, 10, 11, 13 route lifecycle events through sealed quality events and metrics. | Complete in draft |
| R10 reduce regression, define noise boundary | Sections 4, 11, 17 define probabilistic outcome limits and non-regression gates. | Complete in draft |
| R11 precise scope transfer | Section 8 defines ticker, peer (with legacy cross-ticker migration), sector, and macro with commodity/event-regime macro subtypes, proof, candidate transfer, and narrowing. | Complete in draft |
| R12 precision and recall | Sections 4, 8, 10, 11 track applicability precision, recall, false positives, false negatives, under-routing, and over-routing. | Complete in draft |
| R13 preserve operational hardening | Sections 2 and 13 inline PIT, source tuple, locks, quality event, provenance, migrations, replay/report, alerts, and tests. | Complete in draft |
| R14 allowed schema/prompt/ranking/lifecycle changes | Sections 6 through 13 specify changed schema, predictor/learner contracts, ranking, lifecycle scoring, scope, and metrics. | Complete in draft |
| R15 minimal practical local Python/JSON | Sections 6, 12, 13, 15 keep one artifact, one local script, validators, renderer/ranker, and no new service/database. | Complete in draft |

## 1. Current Implementation Baseline

The baseline is current code and current live corpus, not the prior design plans.

Prediction bundle and lesson rendering:

- `build_prediction_bundle` exists and attaches `learning_context` plus `evidence_source_catalog` (`scripts/earnings/earnings_orchestrator.py:196`, `scripts/earnings/earnings_orchestrator.py:260`, `scripts/earnings/earnings_orchestrator.py:280`). If the learning-context builder fails, it logs and falls back to empty lessons (`scripts/earnings/earnings_orchestrator.py:270`).
- `iter_labeled_lessons` is the shared L-number source for the renderer and source catalog; it walks ticker lessons first, then global lessons in `sector`, `macro`, `cross_ticker` order (`scripts/earnings/_text_utils.py:29`, `scripts/earnings/_text_utils.py:35`, `scripts/earnings/_text_utils.py:42`).
- `_render_learning_context` returns `ordered_lesson_texts` containing body only. Decoration, status, reviews, mechanism, applies_when, and invalid_if are excluded from the validator comparison (`scripts/earnings/renderer/lessons.py:180`, `scripts/earnings/renderer/lessons.py:184`, `scripts/earnings/renderer/lessons.py:214`).

Prediction validation:

- Current prediction schema is `prediction_result.v1` (`scripts/earnings/earnings_orchestrator.py:701`).
- `lesson_labels[]` is required, must match rendered lesson order when expected texts are supplied, and `confirmed`/`contradicted` labels cannot use the `no relevant evidence` sentinel (`scripts/earnings/earnings_orchestrator.py:744`, `scripts/earnings/earnings_orchestrator.py:774`, `scripts/earnings/earnings_orchestrator.py:786`).
- `key_drivers[].cites_lesson_indices` is required and may cite only `confirmed` lessons (`scripts/earnings/earnings_orchestrator.py:796`, `scripts/earnings/earnings_orchestrator.py:821`).
- `evidence_ledger[].source_id` must resolve against the bundle evidence source catalog in production validation (`scripts/earnings/earnings_orchestrator.py:844`, `scripts/earnings/earnings_orchestrator.py:858`, `scripts/earnings/earnings_orchestrator.py:874`).
- Current validation does not reject an all-irrelevant/all-sentinel lesson batch that still makes a directional call, as shown by FCX Q1: all six labels used `no relevant evidence`, no key driver cited a lesson, yet the prediction made a `short` call at confidence 48 (`earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:2`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:3`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:12`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:45`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:172`).

Learner validation and storage:

- Current learner schema is `attribution_result.v3` (`scripts/earnings/validate_learning.py:1`, `scripts/earnings/validate_learning.py:133`).
- Current learner lessons and global observations require `lesson`, `mechanism`, `applies_when`, `invalid_if`, and non-empty resolving `evidence_refs` (`scripts/earnings/validate_learning.py:21`, `scripts/earnings/validate_learning.py:501`, `scripts/earnings/validate_learning.py:523`, `scripts/earnings/validate_learning.py:539`).
- Current global scope routing validates `cross_ticker`, `sector`, and `macro`, rejects `scope_key`, requires `related_tickers` for cross-ticker, requires `target_sector` for sector, and rejects irrelevant routing fields on the other scopes (`scripts/earnings/validate_learning.py:322`, `scripts/earnings/validate_learning.py:348`, `scripts/earnings/validate_learning.py:355`, `scripts/earnings/validate_learning.py:407`, `scripts/earnings/validate_learning.py:431`).
- Current `lesson_audit[]` validates positional shape, `predictor_label`, `was_cited`, review/action enums, non-empty evidence refs, and replacement lesson shape for `action="refine"` (`scripts/earnings/validate_learning.py:542`, `scripts/earnings/validate_learning.py:556`, `scripts/earnings/validate_learning.py:571`, `scripts/earnings/validate_learning.py:587`, `scripts/earnings/validate_learning.py:597`, `scripts/earnings/validate_learning.py:601`).
- Cross-file learner validation enforces audit count, bundle lesson count, predictor label parity, cited parity, and lesson text parity (`scripts/earnings/earnings_orchestrator.py:2977`, `scripts/earnings/earnings_orchestrator.py:3004`, `scripts/earnings/earnings_orchestrator.py:3015`, `scripts/earnings/earnings_orchestrator.py:3041`).
- Ticker lesson rows are upserted atomically but without a ticker lock, while global lessons use `fcntl.flock`; current global D22 collision check runs before the flock (`scripts/earnings/earnings_orchestrator.py:1499`, `scripts/earnings/earnings_orchestrator.py:1559`, `scripts/earnings/earnings_orchestrator.py:1658`, `scripts/earnings/earnings_orchestrator.py:1667`).
- Learning finalization writes `learning/result.json` through `Path.write_text`, while prediction finalization uses `_atomic_write_json` (`scripts/earnings/earnings_orchestrator.py:3462`, `scripts/earnings/earnings_orchestrator.py:3535`).

Read-side lifecycle and routing:

- `build_learning_context` PIT-filters lessons by `source_pit_cutoff`, excludes same-quarter self-leaks, drops retired lessons before caps, and routes global lessons by scope (`scripts/earnings/earnings_orchestrator.py:2101`, `scripts/earnings/earnings_orchestrator.py:2162`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2300`, `scripts/earnings/earnings_orchestrator.py:2309`).
- Ticker rows and global buckets sort by recency and then cap ticker rows at 8, sector at 4, macro at 4, and cross-ticker at 2 (`scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352`).
- The playground confirms current Steps 1-13 behavior and calls Steps 14-16 proposals. It shows the current state machine as active/watch/retired, with retirement on `action in {retire, refine}` or `misled >= 3`, watch on `misled >= 2`, otherwise active (`.claude/plans/lessons-lifecycle-playground.html:1752`, `.claude/plans/lessons-lifecycle-playground.html:1444`, `.claude/plans/lessons-lifecycle-playground.html:1446`, `.claude/plans/lessons-lifecycle-playground.html:1448`).

Skills:

- The predictor skill tells the model to test `applies_when` and `invalid_if`, to use `no relevant evidence` only when no condition/signal appears, to cite only confirmed lessons, and to choose `no_call` when evidence does not support a real edge (`.claude/skills/earnings-prediction/SKILL.md:99`, `.claude/skills/earnings-prediction/SKILL.md:104`, `.claude/skills/earnings-prediction/SKILL.md:106`, `.claude/skills/earnings-prediction/SKILL.md:112`, `.claude/skills/earnings-prediction/SKILL.md:114`, `.claude/skills/earnings-prediction/SKILL.md:228`).
- The learner skill already asks for structured lessons with mechanism, applies_when, invalid_if, and evidence refs, urges narrower scope when uncertain, and defines `helped`, `misled`, `outweighed`, `missed`, and `neutral` audit reviews (`.claude/skills/earnings-learner/SKILL.md:82`, `.claude/skills/earnings-learner/SKILL.md:90`, `.claude/skills/earnings-learner/SKILL.md:101`, `.claude/skills/earnings-learner/SKILL.md:154`, `.claude/skills/earnings-learner/SKILL.md:158`).

Live FCX corpus:

- Q3 has prediction and learning JSON, with empty legacy lesson labels and an `attribution_result.v3` learner result (`earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:2`).
- Q4 has only bundle/rendered text and related filing markdown files; no Q4 prediction or learning JSON was found in the event directory snapshot.
- Despite that Q4 source gap, `earnings-analysis/learnings/ticker/FCX.json` contains Q4 ticker lessons and `earnings-analysis/learnings/global.json` contains a Q4 BasicMaterials sector lesson (`earnings-analysis/learnings/ticker/FCX.json:100`, `earnings-analysis/learnings/ticker/FCX.json:119`, `earnings-analysis/learnings/global.json:48`, `earnings-analysis/learnings/global.json:64`).
- Q1 bundle rendered Q4 and Q3 lessons plus allowed learner paths, including a Q4 learner result path that is absent on disk now (`earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5477`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5545`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5677`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5729`).
- No `learning/quality_event.json` exists for Q3, Q4, or Q1 in the inspected FCX event paths.
- There is no current `scripts/earnings/learning_metrics.py`; `find scripts/earnings -path '*learning_metrics.py' -print` returned no paths.

## 2. Preserved Operational Invariants

This plan preserves the accepted operational-hardening floor and treats it as the minimum safety substrate for lesson intelligence. The implementation roadmap in Section 13 restates these details so implementers do not need to open earlier plans.

1. PIT/no-leak filtering and same-quarter self-leak prevention remain. Future `build_learning_context` continues to require `source_pit_cutoff <= predictor.pit_cutoff`, excludes the current event's own lessons, and refuses historical learner mutation when PIT provenance would fall back to invocation time.
2. Source provenance caps remain. Missing-source lessons and audits can render only as low-authority or candidate context, cannot earn verified helped/misled credit, cannot promote, cannot retire another lesson, and cannot affect citation precision or Brier/lift metrics.
3. Anti-lazy prediction engagement remains and is strengthened. An all-irrelevant or all-not-testable lesson batch cannot support an unsupported directional call. `Direction` must be `no_call` unless at least two distinct key drivers each carry at least one resolving non-S10 evidence source ID and their union contains at least two distinct catalog source IDs; otherwise `long`/`short` is allowed only with low directional confidence in the closed band `51 <= confidence_score <= 55`.
4. Canonical event-level seal remains centered on `events/{quarter}/learning/quality_event.json` plus the protected `prediction_source_tuple`.
5. `earnings-analysis/learnings/*.json` remains a derived read model. It is not the ultimate source of truth. Replay/recovery rebuilds it from sealed events and source-complete legacy triples.
6. Replayability and deterministic recovery remain. A `learning/result.json` without a sealed quality event triggers deterministic recovery or refusal, not silent trust.
7. Atomic/idempotent mutation remains. All future mutation of event seal, ticker libraries, global library, and audit aggregation uses atomic JSON writes and exact upsert keys.
8. Lock order remains event lock, ticker locks in alphabetical ticker order, then global lock. D22 collision checks happen inside the relevant future locks.
9. Brier, calibration, no_call, citation, velocity, and blast-radius metrics remain prediction-quality signals.
10. The implementation remains local Python/JSON. No database, service, dashboard, trigger daemon, trading layer, vector store, or external durable state is added.
11. Production builder side effects are protected. The event `.learning.lock` is acquired before any production builder side effect, SDK invocation, source-artifact write/unlink, or `learning/result.json` read/write.
12. Source immutability guard covers the full `prediction_source_tuple`: `context_bundle.json`, full `context_bundle_rendered.txt`, `prediction/result.json`, `prediction/section_audit.json`, `learning/result.json`, `learning/quality_event.json`, rendered learning-context hash, lesson-set hash, and allowlisted prompt sidecars from related filings and prior learner reports.
13. Save-time `production_source_commitment` and canonical JSON serialization are pinned across save, predict validation, quality-event seal, replay-check, and backfill.
14. Process-local `EventArtifactIndex` is bounded and avoids full-corpus provenance rescans per lesson.
15. D19/D20/D22 gates remain: cross-file audit parity, body-only lesson labels, and lesson-ID collision checks inside future locks.
16. Migration classes remain source-complete legacy, missing-source, already-valid, failed-recovery, and human-decision.
17. Runbook behavior remains non-zero health exits plus `LEARNER_ALERT status=<state> ticker=<T> quarter=<Q> reason=<R>` for triage.
18. Evolution remains additive: future `prediction_result.v2` and `attribution_result.v4` extend current artifacts rather than replacing them with incompatible unplanned schemas.

## 3. Ideal Predictor Contract

A high-quality lesson is a small executable hypothesis:

`IF all observable applies_when predicates are present AND no observable invalid_if predicate is present THEN apply expected_effect BECAUSE mechanism_chain links setup -> anchor change -> participant interpretation -> price implication, VALID FOR a justified scope, WITH measured reliability/calibration/transfer evidence, UNTIL audits prove refine, narrow, widen, de-emphasize, or retire.`

The weak predictor sees a compact contract, not wisdom prose:

1. `applicability`: a list of bundle-checkable predicates. Each predicate has `predicate_id`, `field_path` or `source_id_pattern`, `operator`, `expected_value` or `range`, `units`, `missing_behavior`, and a short human label.
2. `invalidators`: same shape as predicates, but any true invalidator blocks citation and records `blocked_by_invalid_if`.
3. `expected_effect`: orthogonal fields, not one mixed enum. `direction_effect` is `long_bias`, `short_bias`, `no_call_bias`, or `none`; `confidence_delta_points` is one of `-20, -10, -5, 0, 5, 10, 20`; and `magnitude_bucket` is `small`, `medium`, `large`, or `unknown`. At least one of direction, confidence delta, or magnitude must be non-empty or the lesson is rejected as no-effect.
4. `mechanism_chain`: four short fields: `setup`, `anchor_change`, `participant_interpretation`, and `price_implication`.
5. `scope`: one of `ticker`, `peer`, `sector`, or `macro`, with routing key and transfer proof. Commodity and event-regime routes are represented in v0 as `macro_subtype: commodity:<key>` or `macro_subtype: event_regime:<key>` to avoid new routing branches.
6. `quality_summary`: transient, derived stats: citation precision, applicability precision/recall, freshness, transfer history, dormant count, and provenance state.
7. `source_ids`: source IDs for the predicates and mechanism, plus the sealed source event identity.

The predictor must output, per rendered lesson:

- `lesson_id`.
- `applicability_verdict`: exactly one of `applies`, `blocked_by_invalid_if`, `not_applicable`, or `not_testable_missing_data`.
- `predicate_trace[]`: predicate ID, verdict, resolving source IDs, observed value, and missing behavior.
- `invalidator_trace[]`: invalidator ID, verdict, resolving source IDs, and observed value.
- `influence`: exactly one of `none`, `cited`, `changed_direction`, `changed_confidence`, `caused_no_call`, `outweighed`, or `blocked`.
- `influence_reason`: one short source-grounded explanation.
- `conflict_handling`: no conflict, outweighed by stronger lesson, outweighed by non-lesson evidence, or unresolved conflict leading to `no_call`.

If the predictor cannot fill this from the bundle without market intuition, the lesson is not a high-authority reusable lesson. It must be rejected at birth, converted to a data/bundle-feature request, or authority-capped until the missing observable proxy exists.

## 4. Perfect Lesson Quality Definition

Perfect lesson quality is deterministic applicability plus probabilistic outcome measurement. A perfect lesson is not always right. It is unambiguous about when it applies, explicit about what it predicts, measured about how reliable it has been, and quickly corrected when measured behavior deteriorates.

| Quality property | Mechanical definition | Enforcement class | Metric/evidence | Failure mode |
|---|---|---|---|---|
| Applicability precision | When the lesson fires, the setup is truly present and invalidators are absent. | VALIDATOR, RENDERER/RANKER, PREDICTOR CONTRACT, METRICS/REPLAY | false-positive audit rate, blocked-invalidator correctness, verified misled due to predicate error | Broad lesson creates noisy false positives |
| Applicability recall | When a setup exists, the lesson reaches the predictor or is recorded as a missed-applicable lesson. | RENDERER/RANKER, LEARNER CONTRACT, METRICS/REPLAY | missed-applicable rate, candidate transfer hits, under-routing count | Useful lesson trapped in narrow scope or cap |
| Mechanism clarity | Lesson explains setup -> anchor change -> participant interpretation -> implication. | VALIDATOR, LEARNER CONTRACT, JUDGE/HUMAN ONLY | mechanism-chain completeness, judge score, audit root cause | Generic story or post-hoc slogan |
| Observable triggers | Predicates are detectable from saved bundle/source artifacts. | VALIDATOR, PREDICTOR CONTRACT, METRICS/REPLAY | predicate trace source-ID coverage | Vibes such as "management sounded worried" without proxy |
| Observable invalidators | Invalidators are specific enough to block false positives. | VALIDATOR, PREDICTOR CONTRACT, LEARNER CONTRACT | invalidator trigger precision, false positive clusters | Lesson keeps firing in known null regimes |
| Direction/magnitude usefulness | Expected direction, magnitude bucket/range effect, or confidence/no_call effect is explicit. | VALIDATOR, PREDICTOR CONTRACT, METRICS/REPLAY | Brier, high-confidence wrong rate, magnitude error when range exists | Predictor knows setup applies but not how to use it |
| Scope correctness | Lesson lives at narrowest sufficient scope and transfers only with proof. | VALIDATOR, RENDERER/RANKER, LEARNER CONTRACT, METRICS/REPLAY | transfer precision, false positives by scope, narrowing events | One ticker poisons sector/global memory |
| Influence/usefulness quality | A lesson credited with `changed_direction`, `changed_confidence`, or `caused_no_call` actually influenced the prediction and is later audited helped/misled/outweighed/missed. | PREDICTOR CONTRACT, LEARNER CONTRACT, METRICS/REPLAY | citation precision = helped / (helped + misled) for influenced lessons | Decorative citations or silent ignored lessons |
| Calibration contribution | Lesson improves Brier/reliability/no_call behavior versus comparable no-lesson cases. | METRICS/REPLAY | Brier lift, ECE, reliability bins, no_call usefulness | Story quality rises while prediction quality worsens |
| Lifecycle responsiveness | Good lessons promote quickly enough; bad/obsolete lessons refine, de-emphasize, narrow, or retire. | LEARNER CONTRACT, METRICS/REPLAY, VALIDATOR | time-to-first-helped, bad-lesson half-life, stale/dormant counts | Dead lessons consume caps or harmful lessons linger |
| Simplicity/compression | Predictor can apply without expert market intuition. | RENDERER/RANKER, PREDICTOR CONTRACT, JUDGE/HUMAN ONLY | novice applicability pass rate, predicate count/complexity | Lesson needs unstated finance knowledge |
| Novelty/non-obviousness | Lesson adds decision signal beyond generic beat/miss maxims. | LEARNER CONTRACT, JUDGE/HUMAN ONLY, METRICS/REPLAY | lift versus generic baseline, generic-text lint | Library fills with tautologies |
| Transfer value | Mechanism transfers beyond birth ticker only when causal setup and evidence transfer. | LEARNER CONTRACT, METRICS/REPLAY, VALIDATOR | transfer helped/misled, candidate-transfer promotion rate | Sector lessons fire everywhere or never travel |
| Replayability/PIT safety | Same prediction-time lesson set and applicability decision can be reconstructed later. | VALIDATOR, METRICS/REPLAY | source tuple hashes, quality-event seal, replay-check pass | Future leakage or source drift |

Market-noise boundary: Even a valid lesson can be outweighed by macro shocks, reflexivity, incomplete data, or unrelated event risk. Such cases are audited as verified `outweighed` only when the dominating force is source-grounded by a named external force or objective shock/range condition; unattributed noise earns no verified credit. The non-regression contract is measurable but probabilistic: over PIT-valid evaluation sets, promotion, retirement, and scope-broaden decisions must not worsen Brier, no_call usefulness, citation precision, or blast-radius guardrails beyond stated tolerances.

## 5. Failure Modes in Current Lessons and Lifecycle

1. Q1 all-sentinel laziness: current validation allowed all six FCX Q1 lessons to be labeled irrelevant with `no relevant evidence`, zero lesson citations, and a directional short call at confidence 48 (`earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:2`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:12`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:45`).
2. Q4 provenance gap: Q4 lessons are present in derived libraries but the Q4 event has no prediction or learner JSON; Q1 still carried a Q4 learner result path (`earnings-analysis/learnings/ticker/FCX.json:100`, `earnings-analysis/learnings/global.json:48`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5545`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5677`).
3. Recency ranking: current ticker and global paths sort by `attributed_at` before caps, so an unproven recent lesson can crowd out a better older one (`scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352`).
4. Broad sector promotion: current sector routing sends every `target_sector` match into future predictions, without independent transfer proof beyond learner prose (`scripts/earnings/validate_learning.py:407`, `scripts/earnings/validate_learning.py:421`).
5. Hardcoded status thresholds: current active/watch/retired behavior is driven by raw `misled` counts and `retire/refine` actions rather than marginal contribution, uncertainty, deadness, or scope-specific false positives (`.claude/plans/lessons-lifecycle-playground.html:1444`, `.claude/plans/lessons-lifecycle-playground.html:1446`, `.claude/plans/lessons-lifecycle-playground.html:1447`).
6. Dead lessons are not separated from bad lessons. Repeated correct non-application should lower rank or suggest under-routing review, not retire as harmful.
7. Vague mechanisms can pass current length/evidence validators. Current validators require string length and resolving refs, but cannot prove that the causal mechanism is formula-like or novice-usable (`scripts/earnings/validate_learning.py:501`, `scripts/earnings/validate_learning.py:529`).
8. Predicate truth is mostly prompt-enforced. The predictor skill asks the model to use applies_when/invalid_if, but production artifacts do not yet store predicate-by-predicate traces (`.claude/skills/earnings-prediction/SKILL.md:104`, `.claude/skills/earnings-prediction/SKILL.md:106`).
9. No explicit conflict contract. Opposing applicable lessons can coexist but current artifacts do not require the predictor to mark conflict, influence, or no_call due to unresolved lesson tension.
10. No direct marginal contribution evidence. Current `cites_lesson_indices` shows citation, not whether the lesson changed direction, confidence, magnitude, or no_call (`scripts/earnings/earnings_orchestrator.py:796`).

## 6. Minimal Target Lesson Architecture

The target is the smallest practical architecture: structured fields added to existing JSON artifacts, one deterministic applicability evaluator, richer but compact predictor/learner contracts, tier ranking before caps, and one local metrics/replay tool. It does not add a database, service, dashboard, trigger daemon, vector store, or trade machinery.

### 6.1 Lesson Hypothesis Schema

Future learner output remains JSON and evolves from current v3 structured lessons. Each predictor lesson and global observation becomes a `lesson_hypothesis.v1` object inside `attribution_result.v4` and derived cache rows:

- `lesson_id`: the only canonical lesson identity in v0, computed from normalized body, scope kind, and routing key as current code already does. Refinement that changes predicates, invalidators, expected effect, or scope must also change the human lesson body. Validator rejects same-body refinements whose executable payload differs, rather than adding a second ID.
- `lesson`: 1-2 sentence body for human display. It must be decision-relevant, not a generic maxim.
- `mechanism_chain`: `{setup, anchor_change, participant_interpretation, price_implication}`. Each field is short and source-grounded.
- `applies_when[]`: predicate objects.
- `invalid_if[]`: same predicate shape, interpreted as blockers. If any deterministic invalidator is true, the lesson cannot be cited.
- `expected_effect`: orthogonal and numeric enough for a weak predictor:
  - `direction_effect`: `long_bias`, `short_bias`, `no_call_bias`, or `none`.
  - `confidence_delta_points`: one of `-20, -10, -5, 0, 5, 10, 20`.
  - `magnitude_bucket`: `small`, `medium`, `large`, or `unknown`.
  - Validator derives confidence direction from `confidence_delta_points`: positive means confidence up, negative means confidence down, zero means no confidence effect.
  - Validator rejects no-effect lessons where direction is `none`, delta is `0`, and bucket is `unknown`.
- `scope`: `{kind, routing_key, macro_subtype, transfer_state}`. V0 `kind` is only `ticker`, `peer`, `sector`, or `macro`. `transfer_state` is closed enum `none`, `candidate_transfer`, or `proven_transfer`. V4 writes use `peer`; legacy `cross_ticker` rows are migration aliases only. Commodity and event-regime routing use `macro_subtype` values such as `commodity:copper` or `event_regime:quantified_warning_pt_reset`, avoiding new scope branches. There is no durable `scope_proof` field in v0; any human-readable proof text is render-only and derived from closed transfer fields.
- `lineage`: `parent_lesson_id`, `supersedes_reason`, and `refined_from_audit_key` for refinements.

Magnitude bucket mapping is global in v0: `small` means expected absolute effect `< 2pp`; `medium` means `2pp <= absolute effect <= 5pp`; `large` means `> 5pp`. This is deliberately not ticker- or volatility-scaled in v0. No lesson-level range-delta field is added in v0; range hit and magnitude error are computed from the prediction artifact's existing `expected_move_range_pct`.

Effect fields are orthogonal. Example: `{direction_effect: short_bias, confidence_delta_points: 10, magnitude_bucket: large}` means the setup supports a higher-confidence short call with a large expected move; `{direction_effect: short_bias, confidence_delta_points: -10, magnitude_bucket: large}` means the setup still leans short and large, but should reduce confidence because a known uncertainty is present. Vol-scaled magnitude buckets are deferred unless per-ticker `magnitude_error_pct` reports show measured calibration regression.

Predicate shape:

- `predicate_id`: unique within a single lesson. Refinement may reuse the same ID only when `operator`, `field_path` or `source_id_pattern`, and `units` are unchanged.
- All `applies_when[]` predicates are mandatory in v0. There are no optional predicates, weights, or quorum-style k-of-n predicates.
- Exactly one of `field_path` or `source_id_pattern`. `field_path` is a dotted-key subset rooted at the saved `context_bundle.json` version committed by `context_bundle_sha256`; no full JSONPath dependency is needed.
- `operator`: v0 enum `exists`, `equals`, `in`, `not_in`, `contains_any`, `not_contains_any`, `gte`, `lte`.
- `expected_value`.
- `units`: required only for numeric `gte`/`lte`; enum `usd`, `pct`, `bps`, `count`, `days`, or `ratio`.
- `source_ids`: one or more birth evidence refs.
- `missing_behavior`: `not_applicable`, `unknown`, or `requires_no_call`.
- `observable_status`: `deterministic`, `proxy_needed`, or `human_only`.

Operator semantics:

| Operator | Required fields | Semantics |
|---|---|---|
| `exists` | `field_path` or `source_id_pattern` | True when the field/path or source-pattern match exists. |
| `equals` | `expected_value` | True when normalized observed value equals expected value. |
| `in` / `not_in` | list `expected_value` | True when observed value is or is not in the list. |
| `contains_any` / `not_contains_any` | list `expected_value` | True when a list/text value contains or does not contain any expected item. |
| `gte` / `lte` | numeric `expected_value`, `units` | True when numeric observed value is above/below threshold. |

`between`, `within_days`, count, and percent-change predicates are expressed in v0 as two `gte`/`lte` predicates over bundle fields or precomputed bundle features. If no bundle field exists, the lesson emits a data/bundle-feature request or stays non-promotable.

Human-only predicates are allowed only as low-authority, non-promotable candidate lessons until converted to deterministic predicates or bundle-feature requests. A high-authority lesson must have all required applies_when predicates and invalidators as `observable_status=deterministic`.

### 6.2 Applicability Evaluator

Add one local deterministic evaluator used by renderer/ranker, prediction validation, learner audit, replay, and novice tests:

`evaluate_lesson_applicability(lesson, bundle, evidence_source_catalog) -> applicability_trace`

The trace records:

- `verdict`: exactly one of `applies`, `blocked_by_invalid_if`, `not_applicable`, or `not_testable_missing_data`.
- `predicate_trace[]` and `invalidator_trace[]`: ID, operator, observed value, source IDs, predicate-level `verdict`, missing behavior, and optional override object. Predicate-level verdict enum is `true`, `false`, `unknown`, or `missing`.
- `unknown_predicates[]`: predicates that require a future data/bundle feature.
- `requires_no_call`: true iff final verdict is exactly `not_testable_missing_data`, no mandatory `applies_when` predicate has predicate-level `verdict=false`, and at least one predicate has predicate-level `verdict=missing` with `missing_behavior=requires_no_call`.

Decision order is deterministic:

1. If any invalidator is true, verdict is `blocked_by_invalid_if` and `requires_no_call=false`.
2. Else if every `applies_when` predicate is true, verdict is `applies`.
3. Else if any mandatory `applies_when` predicate has predicate-level `verdict=false`, verdict is `not_applicable` and `requires_no_call=false`. Missing predicates may remain in `predicate_trace`, but they do not force no_call when the setup is already proven absent.
4. Else if any missing predicate has `missing_behavior=unknown` or `requires_no_call`, verdict is `not_testable_missing_data`.
5. Else verdict is `not_applicable`; predicates missing with `missing_behavior=not_applicable` or any remaining non-no_call condition stay in `predicate_trace`.

Renderer/ranker uses this trace before caps. The predictor must either accept the trace or explain a source-grounded override. Validation rejects unsupported overrides.

Evaluator output is the source of truth. A predictor trace must equal the evaluator trace unless the differing predicate or invalidator trace includes `predicate_override`: `{disagree_with_evaluator: true, override_verdict, override_reason: str <=240 chars, override_source_ids[]}`. `override_source_ids[]` must resolve against the bundle catalog and include at least one non-S10 source ID; S10-only overrides are invalid. Unsupported overrides fail prediction validation.

When a supported `predicate_override` flips a predicate or invalidator verdict, the predictor must recompute `applicability_verdict` using the same decision order over the overridden trace. Validation rejects any predictor `applicability_verdict` inconsistent with that recomputed overridden trace.

`requires_no_call=true` is a hard predictor obligation, not a hint. If any rendered lesson's final overridden trace still has `requires_no_call=true`, final prediction `direction` must be `no_call`; validation fails otherwise.

### 6.3 Rendering and Ranking

Future rendering still uses body-only D20 labels. The visible lesson block is compact:

- Marker line: `L<n>. [scope] [tier]`.
- Body block: `Lesson:`, `When:`, `Invalid if:`, `Effect:`, `Mechanism:`, `Why shown:`.
- Ordered lesson text remains body only so existing positional checks stay stable.

Potential conflict is auto-derived at render time. If two or more currently applicable lessons share the same normalized scope/routing key and have non-identical non-`none` `direction_effect` values, the renderer adds a short `Why shown:` note naming the conflicting L numbers. The predictor then records the actual resolution in `lesson_labels[].conflict_handling`; if unresolved conflict remains, final `direction` must be `no_call`.

Ranking is bucketed, not a learned formula:

1. Drop `blocked_by_invalid_if` and deterministic `not_applicable` lessons before caps unless debug/replay mode requests them.
2. Exact-scope applicable `proven` lessons rank first.
3. Exact-scope applicable `candidate` lessons rank next.
4. Candidate-transfer applicable lessons rank after exact-scope lessons.
5. `not_testable_missing_data` lessons render only when they require no_call or expose a key data gap; otherwise they do not consume caps.
6. Macro lessons, including `macro_subtype=commodity:*` or `macro_subtype=event_regime:*`, can outrank exact ticker/peer only when applicability is deterministic, provenance is complete, tier is strictly higher than the exact-scope alternative, and predictor records explicit conflict handling. Otherwise exact scope wins.
7. Deterministic tie-break: `source_pit_cutoff` descending, then `(source_ticker, quarter_label, lesson_id)`.

### 6.4 Authority Stats

Do not duplicate large persistent per-lesson stats in every cache row. Metrics derive from sealed quality events and are attached transiently during render/report through `EventArtifactIndex`.

Minimal derived stats:

- `verified_helped`
- `verified_misled`
- `verified_outweighed`
- `missed_should_have_applied`
- `correct_nonapplication`
- `dormant_nonapplication`
- `citation_precision`
- `applicability_precision`
- `applicability_recall`
- `transfer_precision`
- `transfer_recall`
- `last_applied_at`

Wilson/beta-binomial lower bounds are not authority gates in v0 because sample sizes are sparse. `learning_metrics.py` may report a Wilson lower bound only when `influenced_n >= 10`; below that, the field is `sample_too_small`.

## 7. Lesson Lifecycle Design

Lifecycle authority is derived from evidence. V0 keeps only three render tiers plus an exclusion flag and generic transient render warnings:

- `candidate`: default for new, unproven, source-complete, source-missing, or one-helped lessons.
- `proven`: high-authority evidence tier.
- `dormant`: lesson is not wrong, but has not found setup opportunities.
- `excluded`: boolean flag that removes a lesson before caps while preserving history. It is used for retirement, supersession, or missing-source hard failure.
- `_render_warnings[]`: transient render/report warnings limited to `risk_warning` and `outweighed_pressure`. Candidate-transfer and missing-data notices are derived at format time from `_render_tier`, `_render_provenance_complete`, and the applicability trace, not stored as warning values.

### Birth

A new lesson is eligible only if it has source-complete event provenance or is explicitly legacy-capped, bundle-checkable predicates, invalidators, mechanism chain, expected effect, narrow scope, and source refs for mechanism/predicate families. Reject generic, case-only, mixed-mechanism, no-effect, or unobservable lessons. If a missing observable is useful, emit a data lesson/bundle-feature request rather than a high-authority market lesson.

### First Authority

Source-complete new lessons may render immediately as `candidate` with low authority. Missing-source legacy lessons may render only as unproven/missing-provenance and cannot earn quality credit until source artifacts are restored or backfilled.

### Application

A lesson gets application credit only when deterministic predicates apply, invalidators are absent, and it was rendered or should have been rendered in the bounded PIT-valid opportunity pool. Positive usefulness credit requires predictor influence or a later missed-lesson audit showing it should have influenced the prediction.

### Audit

The learner emits one compact `audit_outcome` per rendered or missed-applicable lesson:

- `helped`: applied, influenced direction/confidence/no_call, and later evidence supports that influence.
- `misled`: applied or falsely confirmed, influenced the call, and the lesson mechanism/predicate/effect was wrong.
- `outweighed`: applied and logic was sound, but a stronger named external force or objective shock/range condition dominated. It must cite resolving source IDs for the dominating force. Unattributed market noise cannot be audited as verified `outweighed`; if artifacts cannot adjudicate the force, use `data_missing`, which earns no helped/misled/outweighed credit.
- `missed`: lesson was not cited/rendered or was treated as not applicable, but PIT evidence shows it should have applied and would have improved the call.
- `correct_nonapplication`: lesson did not apply and was correctly ignored.
- `dormant`: an opportunity window passed without a predicate match; deadness, not badness.
- `data_missing`: bundle or source/outcome artifacts lacked a required observable to adjudicate applicability or the claimed dominating force.

The existing review/action concepts remain for compatibility, but v4 validation treats `audit_outcome` as the single root-cause-compatible field for lifecycle scoring. It replaces the separate root-cause, marginal-contribution, and scope-recommendation enums from Round 0.

### Promotion

Promotion is count-based in v0:

- `proven` requires complete provenance, at least two `helped` audits where the lesson influenced the prediction, from two distinct future audit keys and two distinct future quarter labels, and zero `misled` audits since latest refinement.
- If either positive audit is missing-source, legacy-only, or not influenced, it does not count.
- `cited` influence is supportive only and does not count as an influenced helped audit for promotion; promotion-positive helped audits require `changed_direction`, `changed_confidence`, or `caused_no_call`.
- One helped audit is still `candidate`; the helped count appears in render stats but does not create a separate `promising` tier.
- `proven` promotion is blocked if lineage-level blast radius exceeds 25% of verified misled cited outcomes in the rolling 50 completed directional calls.
- `proven` promotion is blocked by two source-grounded `outweighed` influenced audits since the latest refinement unless a later helped audit shows the lesson recovered. Existing proven lessons with this pattern render with `_render_warnings[]` containing `outweighed_pressure` and rank below clean proven lessons until recovery.
- Non-regression for v0 promotion means deterministic replay/report checks pass: source tuple valid, live cache matches sealed events, no missing audit rows, no forged audit rows, `baseline_status=complete`, stable `comparable_event_set_sha256`, and no guardrail breach in the machine-readable quality gate. LLM ablation is not an authority gate in v0.

### De-emphasis and Dormancy

Define a PIT-valid opportunity as a future event in the bounded recall pool where the lesson is eligible by PIT and scope bucket. A lesson becomes `dormant` after eight PIT-valid opportunities or four future quarter labels, whichever comes first, with zero `applies` evaluator verdicts and no `data_missing` blocker. Dormancy lowers rank but does not count as misled or support retirement.

Low usefulness de-emphasis applies when a candidate is rendered at least five times, never influences, and has no missed/helped audit. It ranks below fresher candidates but remains available when cap pressure is low.

### Refinement

Refine rather than exclude when the mechanism is partly valid and the repair is specific: missing invalidator, missing applies_when predicate, scope too broad/narrow, or effect magnitude/confidence wrong. Refinement emits a new lesson body and therefore a new `lesson_id`; same-body predicate/effect/scope edits are rejected. Parent remains visible only if it still has a non-overlapping valid scope; otherwise parent gets `excluded=true` with `superseded_by`.

### Exclusion / Retirement

Automated exclusion requires measured harm:

- Two `misled` influenced audits from distinct future audit keys since latest refinement and zero helped audits in the same post-refinement window; or
- One `misled` influenced audit where predictor `confidence_score >= 70`, the lesson was primary influence, and learner evidence identifies a false predicate or missing invalidator; this adds transient `_render_warnings[]=["risk_warning"]`, not exclusion, until a second distinct event confirms harm.

Exclusion preserves source artifacts and history. No LLM output may directly retire a lesson; learner can only emit audit evidence and a suggested action. The lifecycle rule derives exclusion after validation and report checks.

### Transfer

Ticker-born lessons can travel only through candidate transfer:

- Predicate match in an independent peer, sector, or macro-subtype case can render as low-authority candidate transfer.
- High-authority non-ticker promotion always requires independent non-birth evidence. Commodity or event-regime strength may justify candidate rendering, never proven authority by itself.
- `sector` promotion requires at least two independent non-birth events from at least two destination tickers/source issuers that are different from the birth ticker/source issuer, zero transfer misled, and complete provenance.
- `peer` promotion requires a stored explicit peer list, destination ticker routing key, and either resolving source IDs proving the transmission link or a static allowlisted sector/industry mapping present in the prediction-time bundle.
- `macro_subtype=commodity:<key>` and `macro_subtype=event_regime:<key>` require the subtype key plus at least two deterministic predicates tied to source IDs. Broad unlabeled regimes are rejected at birth.
- Counted non-birth transfer evidence means source-complete helped audits with influence in `changed_direction`, `changed_confidence`, or `caused_no_call`, event identity different from the birth event, destination ticker/source issuer different from the birth ticker/source issuer, destination scope/key matching the proposed promoted scope, and `transfer_basis=independent_non_birth_evidence`.
- `peer` proven promotion requires at least two counted non-birth destination events whose destination tickers are in the stored peer list and are not the birth ticker, zero transfer misled, and complete provenance. If the birth ticker appears in a stored peer list, it is excluded from the counted destination set.
- `macro` proven promotion requires at least two counted non-birth destination events from at least two distinct non-birth destination tickers/source issuers matching the same `macro_subtype` predicates, zero transfer misled, and complete provenance.
- Transfer failures affect transfer authority and destination scope only. They do not poison the birth ticker's local reliability unless the same predicate/effect mechanism fails there too.

`broaden_candidate` is the explicit candidate-transfer discovery hook. The learner may emit action `broaden_candidate` only with destination scope, `transfer_basis`, transfer_evidence_refs, and routing fields (`related_tickers` for peer, `target_sector` for sector, or `macro_subtype` for macro). The aggregator writes a low-authority candidate-transfer row. Only these explicit candidate-transfer rows enter the bounded missed-applicable pool; v0 does not scan all ticker-born lessons against unrelated bundles.

`transfer_basis` is a closed enum: `predicate_match`, `sector_structural`, `peer_explicit_list`, `macro_subtype_predicate`, or `independent_non_birth_evidence`. `sector_structural` and `predicate_match` can create only candidate-transfer authority until later audits provide `independent_non_birth_evidence`; validators reject free-text transfer bases.

## 8. Scope and Transfer Design

Scope is both a routing boundary and a risk boundary. Predicates can surface candidate transfer, but authority follows proof.

V0 scope kinds:

- `ticker`: mechanism depends on company-specific operations, balance sheet, management cadence, or idiosyncratic event history.
- `peer`: specific named tickers with a shared transmission link. V4 storage and prompts use `peer`; legacy `cross_ticker` rows are mapped to `peer` during migration/backfill.
- `sector`: independent evidence across the sector or a mechanism structurally tied to sector accounting/valuation. Structural sector rationale can create only low-authority candidate rendering until independent non-birth evidence satisfies the promotion rule.
- `macro`: external macro variable, commodity, policy, rate, currency, or event regime measurable in the bundle. Commodity and event-regime travel through `macro_subtype`, not standalone scope kinds.

Precision/recall mechanics:

- Over-broad sector promotion is blocked without two independent non-birth events; no one-ticker sector proof.
- Candidate transfer is allowed when predicates match an independent bundle, but it ranks below exact-scope applicable lessons and cannot become high authority without transfer proof.
- Lessons that travel and mislead narrow by destination ticker, peer list, sector subset, or macro_subtype predicate cluster.
- Macro lessons cannot swamp ticker evidence; the ranker rule in Section 6.3 enforces exact-scope priority unless macro evidence and tier are strictly stronger.
- One ticker's noisy audit history cannot poison another ticker because metrics are stratified by birth scope and destination scope.
- `macro_subtype` values are normalized lowercase ASCII keys from a small validator allowlist. Initial v0 allowlist: `commodity:copper`, `commodity:gold`, `commodity:oil`, `commodity:gas`, `event_regime:quantified_warning_pt_reset`, `event_regime:fy_outlook_reset`, and `event_regime:delayed_dominant_driver`. Unknown commodity or event-regime keys are rejected or emitted as data/bundle-feature requests until a later plan adds them.

Bounded missed-applicable pool:

- exact ticker lessons for the current ticker;
- declared peer lessons where the current ticker is in `related_tickers`;
- same-sector lessons;
- macro lessons with matching `macro_subtype` key, if any;
- macro lessons with no subtype only when at least one deterministic predicate references current bundle source IDs.

The evaluator runs only over this PIT-filtered pool. There is no vector search, broad full-corpus predicate scan, or durable retrieval index in v0.

Bounded transfer pool:

- PIT-valid evaluator-applies opportunities where birth scope/key differs from destination scope/key, or `transfer_state` is `candidate_transfer` or `proven_transfer`.
- Includes only explicit candidate-transfer rows, declared peer rows where the destination ticker is in `related_tickers`, same-sector non-birth rows, and matching `macro_subtype` rows. For high-authority non-ticker promotion, counted transfer rows must use destination ticker/source issuer different from the birth ticker/source issuer.
- Excludes exact local ticker opportunities from transfer recall. Those remain in ordinary applicability recall.
- Transfer missed numerator is transfer `missed` over this bounded transfer pool, stratified by `routing_audit` and `routing_audit_detail`.

## 9. Predictor Use Contract

Future `prediction_result.v2` extends current prediction output.

Top-level additions:

- `context_bundle_sha256`
- `full_rendered_prompt_sha256`
- `lesson_set_sha256`: canonical JSON hash over the ordered rendered lesson set: `{lesson_id, body_normalized, mechanism_chain, applies_when, invalid_if, expected_effect, scope}` for every rendered lesson, using the Section 13.1 canonical serializer.
- `section_audit_sha256`
- `allowlisted_prompt_sidecars[]`
- `counter_thesis`: `{opposing_case_summary: str <=400 chars, opposing_case_source_ids: [str]}`. The summary is the strongest opposing directional case visible in the bundle; absence is encoded by setting `opposing_case_summary` to the literal string `"absent"` and `opposing_case_source_ids` to `[]`. If summary is not `"absent"` and final direction is not `no_call`, source IDs must be non-empty, resolve to the bundle catalog, and be non-S10. If final direction is `long` or `short` and `opposing_case_summary="absent"`, validation caps `confidence_score <= 60`.

Per `lesson_labels[]` additions:

- `lesson_id`
- `applicability_verdict`
- `predicate_trace[]`
- `invalidator_trace[]`
- `additional_engagement_source_ids[]`: required array, empty when no influence source IDs beyond predicate/invalidator traces are needed.
- `influence`: `none`, `cited`, `changed_direction`, `changed_confidence`, `caused_no_call`, `outweighed`, or `blocked`
- `conflict_handling`: `no_conflict`, `outweighed_by_lesson`, `outweighed_by_non_lesson_evidence`, or `unresolved_no_call`
- `influence_reason`: string <=240 chars

Per `key_drivers[]` additions:

- `evidence_source_ids[]`: resolving non-lesson evidence IDs.
- `lesson_influence[]`: cited lesson IDs and effect on direction/confidence/no_call.

Rules:

- `S10` means the lesson-rendering source-ID family produced from `bundle.learning_context` and `evidence_source_catalog` for prior lessons. V2 validation requires every evidence-catalog entry to expose `source_family`; S10 IDs are exactly entries with `source_family="lesson"` or `source_origin="learning_context"`. Valid `source_family` values are `lesson`, `filing`, `transcript`, `news`, `market_data`, and `derived_feature`; unknown families fail prediction validation. All non-lesson families are non-S10. S10 IDs are lesson-internal references. They never count as independent non-lesson evidence for the anti-lazy exception, counter-thesis support, or non-blocked influence credit. Example: `S10.L3` or a catalog row tagged `source_family=lesson` is S10; `FILING.8K.2026-01-23` tagged `source_family=filing` is non-S10.
- Only `applies` lessons with no true invalidator can be cited.
- `blocked` influence is required when verdict is `blocked_by_invalid_if`.
- `none` is required when the lesson is not applicable and did not influence the call.
- For overlapping influence cases, choose the highest-impact applicable value in this priority order: `blocked`, `caused_no_call`, `changed_direction`, `changed_confidence`, `outweighed`, `cited`, `none`. `changed_direction` is required when the lesson flips the final side or turns a would-be `no_call` into a directional call. `caused_no_call` is required when the lesson turns a would-be directional call into `no_call`. `changed_confidence` is required when the lesson changes final confidence by at least 5 points or moves the call across a Section 11 ECE confidence bin (`[0,20)`, `[20,40)`, `[40,60)`, `[60,80)`, `[80,100]`). `cited` is valid only when the lesson appears in `key_drivers[].lesson_influence` as source-grounded support and did not change final direction, no_call, or confidence by those thresholds. If a lesson influenced both direction and confidence, choose `changed_direction`.
- Validation derives `engagement_source_ids[]` as the union of resolving source IDs from predicate/invalidator traces plus `additional_engagement_source_ids[]`. `cited`, `changed_direction`, `changed_confidence`, `caused_no_call`, and `outweighed` require at least one resolving non-S10 derived engagement source ID.
- Influence compatibility by applicability verdict:
  - `applies`: may use `changed_direction`, `changed_confidence`, `caused_no_call`, `outweighed`, `cited`, or `none`, subject to the priority and source-ID rules above.
  - `blocked_by_invalid_if`: must use `blocked`; every other influence value is invalid.
  - `not_applicable`: must use `none`; every other influence value is invalid.
  - `not_testable_missing_data`: when final `direction=no_call`, every lesson whose final overridden trace has `requires_no_call=true` must use `caused_no_call`, even if multiple lessons independently require no_call. If final overridden trace has `requires_no_call=false`, it must use `none`. `cited`, `changed_direction`, `changed_confidence`, `outweighed`, and `blocked` are invalid for `not_testable_missing_data`.
- If any rendered lesson's final overridden applicability trace has `requires_no_call=true`, final `direction` must be `no_call`; validation fails otherwise. `confidence_score` is not capped by this rule when final direction is `no_call`.
- `confidence_score` for `long` or `short` must be an outcome-probability-like directional confidence in `[51,100]`; prediction validation rejects directional calls with `confidence_score <= 50`. `no_call` is excluded from directional Brier and has no directional probability semantics.
- `conflict_handling` is required for every lesson. Renderer notes identify potential conflicts; predictor `conflict_handling` records actual resolution. For any lesson with `applicability_verdict` in `{not_applicable, not_testable_missing_data, blocked_by_invalid_if}`, `conflict_handling` must be `no_conflict`. High-quality applicable conflict means at least two applicable lessons with deterministic applicability and complete provenance, where at least one has `_render_tier=proven` and the other has `_render_tier` in `{proven, candidate}`. If such lessons conflict and non-lesson evidence cannot resolve the conflict, choose `no_call` and use `unresolved_no_call`. For a lesson on the chosen side of a resolved conflict, `conflict_handling` must be `no_conflict`, meaning no other lesson or non-lesson evidence outweighed this lesson. For any lesson whose `direction_effect` was overridden by another applicable lesson or by non-lesson evidence, use `outweighed_by_lesson` or `outweighed_by_non_lesson_evidence` respectively.
- Anti-lazy decision table for the exact set of lessons appearing in `ordered_lesson_texts` body-only labels. `blocked_by_invalid_if` lessons rendered only in debug/replay mode are excluded from this denominator. Blocked lessons in production counted sets are non-applicable for directional support. When every counted lesson has `applicability_verdict` in `{not_applicable, not_testable_missing_data, blocked_by_invalid_if}`:
  - `direction` must be `no_call` unless at least two distinct `key_drivers[]` each carry at least one resolving non-S10 `evidence_source_id`, and the union of those resolving non-S10 IDs contains at least two distinct catalog source-ID strings.
  - Otherwise `direction` may be `long` or `short`, but `confidence_score` must be in the low directional band `51 <= confidence_score <= 55`.
  - Example fail: two key drivers both cite only `FILING.8K.1`; this is two drivers but one distinct source ID, so `no_call` is required. Example pass: driver A cites `FILING.8K.1` and driver B cites `TRANSCRIPT.QA.2`; direction is allowed but confidence is limited to 51-55.
- Lessons inform interpretation; they never replace current evidence.

## 10. Learner Audit Contract

Future `attribution_result.v4` extends current v3.

Lesson birth additions:

- Emit `lesson_hypothesis.v1` fields for each predictor lesson and global observation.
- Emit no lesson if predicates, invalidators, effect, scope, or mechanism are not observable enough.
- Emit data lessons for missing bundle observables instead of smuggling them into human-only lesson authority.
- Emit `transfer_basis` and `transfer_evidence_refs` for every non-ticker scope.

Audit additions per lesson:

- `lesson_id`
- `applicability_verdict_at_prediction`
- `learner_applicability_verdict`
- `audit_outcome`: `helped`, `misled`, `outweighed`, `missed`, `correct_nonapplication`, `dormant`, or `data_missing`
- `routing_audit`: `none`, `under_routed`, `over_routed`, `cap_excluded`, `candidate_transfer_hit`, or `candidate_transfer_miss`
- `routing_audit_detail`: required when `routing_audit != none`, omitted otherwise. Shape: `{birth_scope, birth_key, destination_scope, destination_key, macro_subtype, transfer_basis, expected_render_bucket, actual_render_bucket, cap_name, routing_source_ids[]}`. Within non-`none` routing-audit rows, `transfer_basis` is required only for transfer-related audits: `candidate_transfer_hit`, `candidate_transfer_miss`, destination scope/key different from birth scope/key, or lesson `transfer_state` in `{candidate_transfer, proven_transfer}`. Exact-scope `under_routed`, `over_routed`, and `cap_excluded` rows must omit `transfer_basis` or set it to null; validators reject fake transfer bases on exact-scope rows and exclude those rows from transfer-basis strata. Normal transfer successes with `routing_audit=none` omit `routing_audit_detail`; transfer reports derive their birth/destination scope/key, macro subtype, transfer state, and transfer basis from the canonical lesson row's closed fields plus the sealed auditor event or audit aggregation key. `cap_name` is nullable only when cap pressure did not cause the miss. `routing_source_ids[]` must resolve to non-S10 catalog IDs.
- Destination ticker and destination event identity for transfer counts are read from the sealed auditor event or audit aggregation key, not duplicated inside `routing_audit_detail`.
- `influence`: copied from predictor or inferred for a missed lesson
- `action`: `keep`, `refine`, `narrow`, `broaden_candidate`, `de_emphasize`, or `exclude_candidate`
- `outweighed_by`: required short label when `audit_outcome=outweighed`; omitted otherwise
- `reason`: string <=500 chars with resolving evidence refs for non-neutral outcomes
- `replacement_lesson` for refine, with a different body and therefore different `lesson_id`

Compatibility rules:

- Where `applicability_verdict_at_prediction` and `learner_applicability_verdict` disagree, `learner_applicability_verdict` governs audit-outcome qualification. A predictor `applies` that learner evidence downgrades to `not_applicable` or `blocked_by_invalid_if` is always a false-positive apply for applicability-precision metrics. It produces `misled` if the lesson influenced the call, else `correct_nonapplication` for audit-outcome bookkeeping only; applicability precision and specificity ignore `audit_outcome` and derive mechanically from the prediction-time versus learner applicability verdict pair.
- `helped` requires `learner_applicability_verdict=applies`, influence in `changed_direction/changed_confidence/caused_no_call`, outcome support, and resolving evidence. `cited` alone is supportive coverage and cannot create verified helped credit.
- `misled` requires influence plus wrong mechanism/predicate/effect, not merely an unlucky outcome.
- `outweighed` requires source-grounded `outweighed_by`, influence, and resolving evidence for the stronger force or objective shock/range condition. It does not count as helped, does not enter citation precision, and cannot be used when the only explanation is unattributed market noise.
- `missed` affects recall and ranking.
- `routing_audit=under_routed` requires `audit_outcome=missed` and `routing_audit_detail` showing the lesson should have appeared in the bounded pool or rendered set. `routing_audit=over_routed` requires `audit_outcome=misled` or `correct_nonapplication` and `routing_audit_detail` showing the destination scope/key was too broad. `cap_excluded` is assigned when the evaluator says applies in the bounded pool but the rank/cap excluded the lesson and must include `cap_name`. `candidate_transfer_hit` requires a candidate-transfer row that helped; `candidate_transfer_miss` requires candidate transfer that misled or was missed in the destination. `narrow` action requires `over_routed`; `broaden_candidate` requires `under_routed` or `candidate_transfer_hit`. Transfer reports derive routing-anomaly and candidate-transfer strata from transfer-related `routing_audit_detail` rows, and derive normal `routing_audit=none` transfer-success strata from canonical lesson fields plus the sealed auditor event or audit aggregation key.
- `correct_nonapplication` contributes to dormant/de-emphasis evidence and over-routing analysis. Specificity/negative applicability accuracy is computed from verdict pairs, not from `audit_outcome`: true negatives are rows where `applicability_verdict_at_prediction != applies` and `learner_applicability_verdict != applies`. Non-influential false-positive applies labelled `correct_nonapplication` remain false positives for applicability precision and are not true negatives.
- `dormant` affects only de-emphasis.
- `exclude_candidate` is a suggestion, not a direct retirement. Lifecycle rules derive exclusion.

## 11. Metrics and Replay Evaluation

Primary probabilistic metric:

- Directional Brier over completed directional calls only.
- For `long` or `short`, `p = confidence_score / 100`; prediction validation guarantees `0.51 <= p <= 1.00` by rejecting directional calls with `confidence_score <= 50`.
- Outcome is 1 if predicted direction matches actual direction, else 0.
- Brier is `(p - outcome)^2`.
- `no_call` is excluded from directional Brier and measured separately so abstention cannot game Brier. Every report shows `call_count`, `no_call_count`, `total_completed_events`, no_call rate, and no_call usefulness beside Brier.

No-call metric:

- `no_call_usefulness` is the fraction of no_call events whose realized absolute daily return is below the midpoint of that event's absolute expected range. Events without parseable range fall into `unknown_range`, not numerator.
- Every no_call table also reports parseable-range coverage, unknown-range denominator count, and expected-range width distribution so range artifact drift cannot masquerade as no_call improvement.
- `no_call_missed_opportunity_rate` is no_call events where later audit finds a PIT-valid applicable lesson and non-lesson evidence supported a call divided by all no_call events with source-complete learner audit.

Calibration:

- ECE uses five fixed confidence bins: `[0,20)`, `[20,40)`, `[40,60)`, `[60,80)`, `[80,100]`.
- A bin needs at least 10 completed directional calls to be reported as stable; sparse bins are shown but marked provisional and excluded from lifecycle gates.
- Baseline comparator is the frozen existing v1/v2 prediction artifacts from the same PIT-valid event set. Rolling prior 50 is descriptive context only, not a moving rerun baseline. Every quality report emits `baseline_status` (`complete`, `missing`, `incomplete`, or `event_set_changed`) and `comparable_event_set_sha256`. Promotion and scope broadening require `baseline_status=complete` and the same `comparable_event_set_sha256` as the gate input. If the frozen comparator is missing or incomplete, authority promotion/broadening fails closed; exclusion may still proceed from per-lesson measured harm plus replay health.

Citation and applicability metrics:

- Citation precision denominator: `verified_helped / (verified_helped + verified_misled)` for lessons that actually influenced prediction.
- `outweighed`, `correct_nonapplication`, and `dormant` are tracked separately.
- Applicability precision = true applicable uses / all `applies` verdicts later audited source-complete. True applicable uses are audited rows where `applicability_verdict_at_prediction=applies` and `learner_applicability_verdict=applies`; false-positive applies are audited rows where `applicability_verdict_at_prediction=applies` and the learner later downgrades to `not_applicable` or `blocked_by_invalid_if`, regardless of `audit_outcome` or influence. Specificity/negative applicability accuracy also derives from the verdict pair: true negatives require both prediction-time and learner verdicts to be non-`applies`. `correct_nonapplication` can describe audit bookkeeping, but it never overrides these denominator rules.
- `missed_applicable_rate` = `missed` / all PIT-valid evaluator-applies opportunities in the bounded pool, stratified by rendered, cap-excluded, under-routed, candidate-transfer, and not-testable.
- Applicability recall = `1 - missed_applicable_rate` on the same denominator.
- Transfer precision = verified helped influenced transfer uses / (verified helped influenced transfer uses + verified misled influenced transfer uses), restricted to opportunities in the bounded transfer pool. `outweighed` transfer uses are reported separately and never in the denominator.
- `transfer_missed_applicable_rate` = transfer `missed` / all PIT-valid evaluator-applies opportunities in the bounded transfer pool defined in Section 8. Transfer recall = `1 - transfer_missed_applicable_rate` on the same denominator.
- Transfer reports are stratified by birth scope/key, destination scope/key, `macro_subtype`, rendered, cap-excluded, under-routed, over-routed, candidate-transfer hit/miss, and transfer basis for transfer-related rows only. Exact-scope routing-audit rows report no transfer-basis stratum. Under-routing and over-routing strata come from `routing_audit`. For normal transfer successes with `routing_audit=none`, transfer-basis and destination strata derive from the canonical lesson row's closed transfer fields plus the sealed auditor event or audit aggregation key, not from `routing_audit_detail`.

Magnitude/return metric:

- Current prediction artifacts support range hit rate and magnitude bucket error through `expected_move_range_pct` and learner `magnitude_error_pct` (`.claude/skills/earnings-prediction/SKILL.md:195`, `.claude/skills/earnings-learner/SKILL.md:67`).
- V0 does not add calibrated return distributions or predicted-return error as an authority gate.

Marginal lesson contribution:

- Direct predictor-stamped influence is the only v0 authority evidence.
- LLM replay ablation and tournament evaluation are deferred, non-authoritative research tools. They cannot promote, retire, or broaden scope in v0.
- If future experiments use LLM ablation, they must record model/version, prompt hash, source tuple hashes, temperature/seed when available, at least three repeats, and a variance rule before any later goal can use them for authority. That is not part of the canonical v0 roadmap.

Non-regression:

- V0 promotion, exclusion, and scope-broadening require deterministic replay/report health: no source tuple drift, no cache-vs-canonical drift, no missing or forged audit rows, no human-decision source class, no all-sentinel validation breach, and no lineage-level blast-radius breach.
- `learning_metrics.py --quality-report --gate lifecycle` emits structured JSON with `gate_status` (`PASS`, `FAIL`, or `PROVISIONAL`), `baseline_status`, `comparable_event_set_sha256`, guardrail deltas, sparse-bin flags, and breach reasons. It exits non-zero on `FAIL`. Lifecycle code must consume this gate result before promotion, exclusion, or scope broadening; human-readable reports alone are not an authority gate.
- Guardrail tolerances for reports: Brier must not worsen by more than 0.03 on the comparable directional set, no_call usefulness must not regress by more than 5 percentage points, citation precision must not regress by more than 5 points, and high-confidence wrong-call rate must not rise by more than 3 points. Sparse reports below 30 completed events are smoke-only and cannot justify broad promotion.

## 12. Complexity Ledgers

Weight vocabulary: durable artifact type = 4, lock/concurrency primitive = 4, schema/major field group = 3, validator surface = 3, script/tool = 3, lifecycle state/status = 2, prompt-only rule = 1.

Ledger 1 - Design delta from SimplifiedQuality/OperationalHardening to LessonIntelligence:

| Item | Class | Weight | Benefit |
|---|---|---:|---|
| Keep `learning/quality_event.json` as sole canonical event seal | ALREADY-CODED IN DESIGN | 0 net | Preserves operational substrate without new artifact. |
| Keep event/ticker/global locks | ALREADY-CODED IN DESIGN | 0 net | Preserves atomicity/idempotency. |
| Add executable hypothesis schema fields | NET-NEW | 3 | Makes lessons formula-like and unambiguous. |
| Add deterministic applicability evaluator | NET-NEW | 3 | Enables novice applicability, ranking, audit, and replay. |
| Add predictor influence trace | PARTIAL | 3 | Turns citation into measurable marginal contribution. |
| Add compact learner lifecycle audit fields | PARTIAL | 3 | Separates helped/misled/outweighed/missed/dormant/transfer without extra root-cause and marginal-contribution enums. |
| Add macro subtype routing for commodity/event-regime | NET-NEW | 1 | Covers required transfer scopes without new scope branches. |
| Replace active/watch authority with derived tiers including dormant | PARTIAL | 2 | Separates badness from deadness and supports promotion/de-emphasis. |
| Add deterministic lifecycle thresholds and report gates | PARTIAL | 3 | Makes promotion, exclusion, dormancy, and scope broadening executable. |
| Add prompt text for predictor/learner contracts | PARTIAL | 2 | Two prompt-only rule groups, validator-backed where feasible. |
| Total net-positive lesson-intelligence delta |  | 20 | Round 1 cut `hypothesis_id`, standalone commodity/event-regime scopes, tournament/LLM ablation authority, Wilson gates, extra enums, and shingle near-clones. |

Operational-hardening latest Ledger 1 score is 60 (`.claude/plans/LearnerLoopPlan_OperationalHardening.md:186`, `.claude/plans/LearnerLoopPlan_OperationalHardening.md:197`). This plan keeps that substrate and adds 20 points focused on lesson intelligence. This remains net-positive versus the hardened target, so final convergence requires all four judges to explicitly accept that the increase is necessary and minimal for the lesson-intelligence objective.

Ledger 2 - Implementation delta from current code to LessonIntelligence:

| Change | Class | Current evidence | Smallest mechanism |
|---|---|---|---|
| Keep PIT and same-quarter guard | ALREADY-CODED | `scripts/earnings/earnings_orchestrator.py:2162`, `scripts/earnings/earnings_orchestrator.py:2224`, `scripts/earnings/earnings_orchestrator.py:2300` | Preserve in `build_learning_context`. |
| Keep D20 body-only labels | ALREADY-CODED | `scripts/earnings/_text_utils.py:29`, `scripts/earnings/renderer/lessons.py:214` | Preserve renderer/validator shared order. |
| Keep source-ID grounding | ALREADY-CODED | `scripts/earnings/earnings_orchestrator.py:844`, `scripts/earnings/earnings_orchestrator.py:874` | Extend to predicate traces and key drivers. |
| Keep structured mechanism/applies/invalid/evidence fields | ALREADY-CODED | `scripts/earnings/validate_learning.py:501`, `.claude/skills/earnings-learner/SKILL.md:82` | Convert strings to structured predicate arrays for v4. |
| Add prediction v2 engagement/influence/no_call validation | PARTIAL | Current validator at `scripts/earnings/earnings_orchestrator.py:658`; Q1 gap at `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8` | Extend existing validator. |
| Add quality-event seal and source tuple | NET-NEW | No quality_event in FCX events; recovery starts from existing result at `scripts/earnings/earnings_orchestrator.py:1205` | One event JSON, not manifest/drift chain. |
| Add production source commitment and immutability guard | NET-NEW | Current write/unlink path at `scripts/earnings/earnings_orchestrator.py:3824`, `scripts/earnings/earnings_orchestrator.py:3838` | Inline guard in orchestrator. |
| Add v4 executable lesson schema while preserving only `lesson_id` | NET-NEW | v3 validates strings at `scripts/earnings/validate_learning.py:501` | Extend validator and storage rows; body must change on executable refinement. |
| Add deterministic applicability evaluator | NET-NEW | Predicate truth currently prompt-side at `.claude/skills/earnings-prediction/SKILL.md:104` | Local helper used by render, validation, replay. |
| Add quality-tier utility ranking before caps | PARTIAL | Current recency sorts at `scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352` | Replace sort key; keep caps. |
| Add source/dynamic provenance caps | PARTIAL | Q4 missing-source rows in live cache | `EventArtifactIndex` check before render/tier/metrics. |
| Add macro subtype values for commodity/event-regime | NET-NEW | Current scopes at `scripts/earnings/validate_learning.py:342` | Keep scope enum small and route subtypes by predicates. |
| Add `learning_metrics.py` modes | NET-NEW | `find` found no script | One local script for report/replay/backfill and quality report; no v0 tournament authority. |
| Add prompt updates | PARTIAL | Current skills contain baseline contract | Add fields; validators enforce mechanical parts. |

## 13. Exact Future Change Plan From Current Code

This section is the binding implementation roadmap. It is self-contained and includes the operational-hardening substrate.

### 13.1 `scripts/earnings/earnings_orchestrator.py`

1. Add path helpers for `learning/quality_event.json` and event `.learning.lock`. Class: NET-NEW.
2. Implement canonical JSON serialization helper:
   - Deterministic pre-pass converts datetimes to ISO strings and Decimals to strings.
   - Hash uses `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`.
   - This exact helper is used for save-time commitment, predict validation, quality-event seal, replay-check, and backfill. Class: NET-NEW.
3. Add production source immutability guard:
   - Acquire event `.learning.lock` before any production builder side effect, related-filing sidecar creation, source-artifact write/unlink, SDK invocation, `prediction/result.json` write, `prediction/section_audit.json` write/unlink, or `learning/result.json` read/write.
   - Check `learning/quality_event.json`; if sealed, return no-op/already sealed before touching artifacts.
   - If save-only source tuple exists, validate `production_source_commitment` and reuse/no-op. Do not rebuild bundle/rendered prompt/sidecars.
   - If prediction exists but no quality event exists, validate/reuse. If invalid, emit `LEARNER_ALERT status=prediction_invalid_existing ...`, return `SKIPPED_HUMAN_DECISION`, and do not overwrite.
   - Explicit experiment output dirs are the only fresh-overwrite path.
   Class: NET-NEW. Current write/unlink evidence: `scripts/earnings/earnings_orchestrator.py:3824`, `scripts/earnings/earnings_orchestrator.py:3838`.
4. Add `production_source_commitment` inside saved `context_bundle.json` after rendered prompt and allowlisted sidecars exist:
   - Fields: `schema_version`, `context_bundle_payload_sha256` excluding the commitment field, `full_rendered_prompt_sha256`, sorted `allowlisted_prompt_sidecars[]`, `hash_origin: stamped_at_save_finalize`.
   - Exact-schema validation: no unknown keys, fixed primitive types, sorted sidecar list, origin enum validation, no free text.
   - Later save/predict/seal/replay/backfill recomputes and rejects any mismatch.
   Class: NET-NEW.
5. Extend prediction validation from v1 to v2:
   - Preserve current required fields and D20 checks.
   - Add context/full-rendered-prompt/section/sidecar/lesson-set hashes. Rendered learning-context hash stays in the quality-event source tuple and replay/report renderer-drift checks, not in `prediction_result.v2`.
   - Require evidence-catalog rows to expose closed-enum `source_family` or `source_origin` so S10 lesson-internal IDs can be classified mechanically.
   - Add `key_drivers[].evidence_source_ids` and require resolution against non-S10 source IDs for non-lesson evidence.
   - Add per-lesson applicability, predicate, invalidator, engagement, and influence fields.
   - Reject all-irrelevant/all-not-testable directional calls unless the non-lesson evidence exception is satisfied; otherwise require `no_call`. When the exception is satisfied, allow `long` or `short` only with `51 <= confidence_score <= 55`.
   - Reject every `long` or `short` prediction with `confidence_score <= 50` so directional Brier always uses a probability-like `p > 0.50`.
   - Reject unsupported predicate overrides and unsupported `confirmed` labels.
   Class: PARTIAL. Current validator evidence: `scripts/earnings/earnings_orchestrator.py:658`, `scripts/earnings/earnings_orchestrator.py:775`, `scripts/earnings/earnings_orchestrator.py:796`.
6. Extend prediction finalization:
   - Stamp `prediction_result.v2`.
   - Copy/verify committed bundle payload, full rendered prompt, section audit, rendered learning context, lesson set, and allowlisted sidecar hashes.
   - Use `_atomic_write_json` as today.
   Class: PARTIAL. Evidence: `scripts/earnings/earnings_orchestrator.py:3510`, `scripts/earnings/earnings_orchestrator.py:3535`.
7. Add `evaluate_lesson_applicability` helper:
   - Evaluates v0 predicate operators.
   - Produces predicate/invalidator traces.
   - Used by `build_learning_context`, validator, learner audit support, replay, and tests.
   Class: NET-NEW.
8. Extend `build_learning_context`:
   - Keep PIT and same-quarter guards.
   - Use `EventArtifactIndex` to cap missing-source rows/audits before authority, metrics, and high-priority rendering.
   - Evaluate applicability against current bundle when bundle is available.
   - Drop deterministic blocked/not-applicable lessons before caps, except in debug/replay modes.
   - Sort by the bucketed tier/scope rules in Section 6.3 before caps; keep caps bounded.
   - Attach transient `_render_tier`, `_render_provenance_complete`, `_render_applicability_trace`, `_render_quality_summary`, and auto-derived conflict notes.
   Class: PARTIAL. Evidence: `scripts/earnings/earnings_orchestrator.py:2101`, `scripts/earnings/earnings_orchestrator.py:2209`, `scripts/earnings/earnings_orchestrator.py:2352`.
9. Extend lesson identity:
   - Preserve `lesson_id` for legacy/body identity.
   - Do not add `hypothesis_id` in v0.
   - Refinement that changes executable fields must change the human body so the existing body/scope/routing hash changes.
   - D22 collision checks reject same `lesson_id` with different prompt-visible payload, and validator rejects same-body refinements with different predicate/effect/scope payload.
   Class: PARTIAL. Current body ID evidence: `scripts/earnings/earnings_orchestrator.py:1817`.
10. Implement quality event seal:
   - Path: `events/{quarter}/learning/quality_event.json`.
   - Schema: `learning_quality_event.v1`.
   - Fields: `status`, `event_identity`, `source_hashes`, `hash_origins`, `prediction_snapshot`, `outcome_snapshot`, `learning_snapshot`, `lifecycle_events`, `recovery_notes`, `recovery_attempts`, `last_recovery_at`.
   - `learning_snapshot` includes `applicability_trace` summaries; there is no standalone `applicability_snapshot`.
   - `source_hashes` covers the full protected source tuple: `context_bundle.json`, full `context_bundle_rendered.txt`, `prediction/result.json`, `prediction/section_audit.json`, `learning/result.json`, rendered learning-context hash, lesson-set hash, and sorted `{path, sha256}` for allowlisted prompt sidecars from `learning_context._allowed_learner_paths` and `inter_quarter_context._allowed_related_filing_paths`.
   - `learning/quality_event.json` is handled with a non-self-referential convention: the initial seal computes any quality-event content hash with the quality-event self-hash field omitted; replay/report may also record the on-disk quality-event file hash as an outer artifact, but that outer hash is not part of the sealed payload being hashed.
   - `hash_origins` enum is exactly `stamped_at_save_finalize`, `stamped_at_prediction_finalize`, `stamped_at_learning_finalize`, `computed_from_saved_prompt_artifact`, or `computed_at_backfill_current_renderer`.
   - `recovery_notes` is structured, not free prose: `steps_taken[]` enum values `legacy_backfill`, `deterministic_recovery`, `replayed_cache_writes`, or `operator_reset_seen`; plus `mismatch_fields[]`. Saved-prompt versus current-renderer provenance is derived from per-artifact `hash_origins`, not duplicated in `steps_taken[]`. It must be empty on normal new seals.
   - Seal only after prediction v2 validation, learner v4 validation, ticker/global appends, audit aggregation, row-projection validation, and source hash recompute all pass.
   - Only `status=sealed` gives completion/provenance credit.
   - `failed_recoverable` is atomic and retries cap at 3 before human decision.
   Class: NET-NEW.
11. Add deterministic recovery:
   - If `learning/result.json` exists without sealed quality event, validate sibling source tuple and learner result, recompute/verify hashes, replay derived writes under locks, and seal.
   - On mismatch, write/update `failed_recoverable` and emit alert.
   Class: NET-NEW. Current recovery evidence: `scripts/earnings/earnings_orchestrator.py:1207`.
12. Update mutation locking:
   - Lock order: event `.learning.lock`, ticker locks alphabetical, global lock.
   - Ticker D22 scan/upsert under ticker lock.
   - Global D22 scan/upsert under global lock.
   - Audit aggregation upserts by `(parent_lesson_id, auditor_ticker, auditor_quarter_label)`.
   - Recovery uses same order.
   Class: PARTIAL. Evidence: no ticker lock at `scripts/earnings/earnings_orchestrator.py:1499`, global lock at `scripts/earnings/earnings_orchestrator.py:1667`.
13. Add row-level provenance gates before rendering/tiering/metrics:
   - Reconstruct each expected prompt-visible ticker row from sealed `learning/result.json` plus `quality_event.learning_snapshot`.
   - Ticker lesson projection fields: `lesson_id`, lesson body, mechanism, applies_when predicates, invalid_if predicates, expected_effect, scope, routing key, evidence refs, `source_ticker`, `quarter_label`, `source_filed_8k`, `source_pit_cutoff`, `parent_lesson_id`, lineage/supersession fields, and emitted membership.
   - Ticker outer prompt-visible fields also bind: `direction_correct`, `actual_daily_pct`, `predicted_direction`, `predicted_confidence_score`, `primary_driver_summary`, `primary_driver_category`, `what_worked`, `what_failed`, `data_lessons`, and `why`.
   - Global row projection also binds `target_sector`, `related_tickers`, `macro_subtype`, source sector when present, source ticker, quarter label, source filed time, source PIT cutoff, parent/refinement lineage, and canonical audit history after audit verification.
   - For each live lesson, build the expected PIT-visible audit set from sealed auditor events keyed by `(parent_lesson_id, auditor_ticker, auditor_quarter_label)`. Live `audit_history` must have exact key-set equality and payload equality.
   - Audit payload equality covers review/audit_outcome, action, evidence refs, comment/reason, `was_cited`, PIT cutoff, predictor applicability verdict, learner applicability verdict, and compatibility fields.
   - Rows or audits failing membership, projection, or audit equality are untrusted drift: they earn zero helped/misled/citation/tier credit, cannot make a lesson proven, create a risk warning, or set `excluded`, and must be reported by `--replay-check` as `extra_live_row`, `missing_live_row`, or `hash_drift`.
   Class: NET-NEW, but required by operational-hardening substrate.
14. Use `_atomic_write_json` for learner result finalization. Class: PARTIAL. Evidence: current unsafe write at `scripts/earnings/earnings_orchestrator.py:3462`; atomic helper at `scripts/earnings/earnings_orchestrator.py:1444`.
15. Refuse historical learner mutation when PIT boundary is invocation time. Class: PARTIAL. Operational need from current PIT derivation comments at `scripts/earnings/earnings_orchestrator.py:953`.

### 13.2 `scripts/earnings/validate_learning.py`

1. Bump accepted schema to `attribution_result.v4` while supporting source-complete legacy v3 backfill in metrics tooling. Class: PARTIAL.
2. Validate `lesson_hypothesis.v1`:
   - Required `mechanism_chain`, `applies_when[]`, `invalid_if[]`, `expected_effect`, `scope`, `evidence_refs`, and enough fields to recompute existing `lesson_id`.
   - Validate predicate shape, operator enum, missing behavior enum, observable status enum, and source IDs.
   - Reject high-authority/promotable lessons with required human-only predicates.
   - Reject same-body executable refinements: if body is unchanged but predicates, invalidators, expected_effect, or scope differ from the parent, the replacement is invalid.
3. Validate expected effect:
   - Orthogonal `direction_effect`, numeric confidence delta enum, and magnitude bucket mapping.
   - Calibrated return distribution deferred.
4. Validate scope:
   - Existing legacy `cross_ticker` rows are mapped to v4 `peer` during migration/backfill.
   - V4 writes and prompts use `peer`, not `cross_ticker`.
   - Do not add standalone `commodity` or `event_regime` scopes in v0; validate `macro_subtype` instead.
   - Reject durable `scope_proof`; any proof text is derived render-only from closed transfer fields.
   - Require closed-enum `transfer_basis` and `transfer_evidence_refs` for non-ticker initial emission.
5. Validate audit:
   - Compact `audit_outcome` enum.
   - Compact `routing_audit` enum, required `routing_audit_detail` object when routing audit is non-`none`, conditional transfer-basis validation for transfer-related rows only, canonical lesson/event derivation for normal `routing_audit=none` transfer-success strata, and compatibility with `narrow`/`broaden_candidate`.
   - Outcome/action/influence compatibility.
   - Non-sentinel comment floor.
   - Refine requires one replacement lesson with changed body, recomputed `lesson_id`, and parent link.
   - Reject bare retire from LLM output.
   - Validate missed-applicable audits and under/over-routing evidence.

### 13.3 `scripts/earnings/renderer/lessons.py` and `_text_utils.py`

1. Preserve shared L numbering and body-only ordered lesson text. Class: ALREADY-CODED. Evidence: `scripts/earnings/_text_utils.py:29`, `scripts/earnings/renderer/lessons.py:214`.
2. Render compact hypothesis fields outside body:
   - `When:`
   - `Invalid if:`
   - `Effect:`
   - `Mechanism:`
   - `Why shown:`
3. Render source/provenance and tier markers in the marker line, never inside `lesson_text`.
4. Render candidate-transfer and unknown/missing-data warnings compactly.

### 13.4 `.claude/skills/earnings-prediction/SKILL.md`

1. Add v2 output fields for predicate trace, invalidator trace, additional engagement source IDs, compact influence enum, compact counter-thesis schema, and key-driver evidence source IDs.
2. Add rule that deterministic applicability trace from the bundle must be accepted unless a source-grounded override is provided.
3. Add conflict/no_call discipline: unresolved conflict among high-quality applicable lessons requires no_call.
4. Preserve existing rules that lessons inform interpretation but do not replace current evidence.

### 13.5 `.claude/skills/earnings-learner/SKILL.md`

1. Add v4 hypothesis output fields and examples.
2. Add birth rejection rules for generic, mixed, too narrow, too broad, unobservable, or no-effect lessons.
3. Add compact audit outcome/action decision tree.
4. Add transfer proof requirements.
5. Add refinement guidance: repair one observed failure mode, do not cosmetic-refine, avoid fork chaos.
6. Add deadness vs badness guidance.

### 13.6 `scripts/earnings/learning_metrics.py`

Add one local script with modes:

- `--quality-report`
- `--replay-check`
- `--backfill-legacy`

Shared `EventArtifactIndex`:

- Process-local, LRU-bounded at 4096 event entries.
- Indexes each event path, mtime, size, sha256 for the full prediction source tuple.
- Reconstructs canonical emitted lesson maps, prompt-visible row projections, audit-verdict maps, and expected PIT-visible audit sets.
- Invalidates entry on tuple artifact mtime/size change.
- No durable provenance cache.

Replay/report behavior:

- `--replay-check --all` scans sealed events and source-complete legacy triples, rebuilds expected ticker/global caches in memory, compares to live caches, exits non-zero on `extra_live_row`, `missing_live_row`, or `hash_drift`, and emits `LEARNER_ALERT status=replay_drift ...`.
- Non-blocking event-lock probe reports `in_flight_or_recovery_required` and exits non-zero rather than recording durable drift.
- `--quality-report --all` reports missing-source rows, failed recovery, invalid existing predictions, incomplete source tuples, all-sentinel prediction attempts, all-neutral audit batches, no_call usefulness, Brier trend, citation precision/coverage, applicability precision/recall, transfer precision/recall, and blast-radius breaches.
- `--quality-report --gate lifecycle` emits a machine-readable gate object with `gate_status`, `baseline_status`, `comparable_event_set_sha256`, guardrail deltas, sparse/provisional flags, and breach reasons. It exits non-zero on `gate_status=FAIL`; lifecycle promotion, exclusion, and broadening must consume this object.
- `--backfill-legacy` seals only source-complete legacy events, refuses invocation-time PIT and missing-source rows, and never calls an LLM.
- Tiny sibling utility `scripts/earnings/reset_failed_recoverable.py <event_path>` validates restored source artifacts under lock before deleting only failed quality events and never seals or bypasses validation.

Migration classes:

- Already-valid: sealed quality event with matching hashes.
- Source-complete legacy: full source tuple and legacy learner result; can backfill seal but cannot mint v4 verified credit from legacy audits.
- Missing-source: live cache row/audit lacks source tuple; render only unproven/candidate, no quality credit.
- Failed-recovery: artifacts exist but validation/hash/cross-file checks fail; write/report failed_recoverable and require repair.
- Human-decision: malformed/conflicting/ambiguous/incomplete artifacts; leave unproven until human maintenance.

FCX expected classification:

- Q3 source-complete legacy candidate: prediction, section audit, rendered bundle, related filings, and v3 learning exist.
- Q4 missing-source rows: cache rows exist but prediction/learning JSON absent.
- Q4 audits on Q3 lessons: missing-source audits; no tier/retirement/citation credit.
- Q1 all-sentinel directional output: future prediction v2 validation failure/human-decision unless repaired by valid prediction/learner path.

## 14. Test and Verification Plan

Validator tests:

- v4 learner treats every `applies_when[]` predicate as mandatory and rejects any optional/quorum predicate shape in v0.
- v2 prediction rejects all-sentinel/all-irrelevant/all-blocked directional calls unless at least two distinct key drivers each carry at least one resolving non-S10 evidence source ID and the union contains at least two distinct catalog source IDs.
- v2 prediction rejects unsupported predicate overrides, missing predicate traces, invalidator true with citation, unresolved evidence source IDs, illegal influence/source-ID combinations, free-form counter-thesis without source IDs, and decorative citations without influence.
- v2 prediction rejects S10-only predicate overrides and any directional call when a final rendered trace has `requires_no_call=true`.
- Shared applicability fixtures verify a false-plus-missing mix: one mandatory `applies_when` predicate with `verdict=false` plus another with predicate-level `verdict=missing` and `missing_behavior=requires_no_call` must produce final verdict `not_applicable`, `requires_no_call=false`, influence `none`, and no forced final `no_call`.
- v2 prediction rejects illegal applicability-verdict by influence combinations, including requiring `caused_no_call` for every `not_testable_missing_data` lesson whose final overridden trace has `requires_no_call=true` when final direction is `no_call`, and `none` when the trace has `requires_no_call=false`.
- v2 prediction requires conflict winners to use per-lesson `no_conflict` and conflict losers to use `outweighed_by_lesson` or `outweighed_by_non_lesson_evidence`.
- v2 prediction recomputes `applicability_verdict` from supported predicate overrides and rejects inconsistent verdicts.
- v2 prediction mechanically classifies S10 vs non-S10 from evidence-catalog closed-enum `source_family`/`source_origin`.
- v4 learner rejects missing mechanism-chain fields, invalid predicate operator, invalid operator companion fields, human-only high-authority predicate, no expected effect, missing transfer proof, invalid transfer basis, invalid routing audit, bare retire, orphan refinement, same-body executable refinement, and incompatible audit outcome/action.
- v4 learner rejects transfer-related routing audits without a valid `transfer_basis`, rejects fake transfer bases on exact-scope routing audits, and accepts exact-scope `under_routed`, `over_routed`, or `cap_excluded` rows with `transfer_basis` omitted/null.
- v4 learner uses `learner_applicability_verdict` to qualify audit outcomes when prediction-time and learner verdicts disagree.

Novice applicability harness:

- Input: one lesson hypothesis, one prediction-time bundle/source-artifact set, no market background, no future data.
- Run deterministic evaluator.
- Human or script outputs applicability verdict, predicate trace, invalidator trace, and source IDs.
- Assert exact match with production `applicability_trace`.
- Fixtures include deterministic pass, invalidator pass, missing data requiring no_call, human-only capped lesson, and unobservable lesson rejected at birth.

Renderer/ranker tests:

- Body-only ordered lesson text remains unchanged.
- Blocked/not-applicable lessons do not consume caps.
- Proven older lesson outranks unproven recent lesson.
- Candidate transfer appears below exact-scope applicable lessons.
- Macro lesson cannot outrank high-quality ticker/peer lesson unless deterministic applicability, complete provenance, strictly higher tier, and explicit conflict handling justify it.

Lifecycle tests:

- Birth rejects generic, mixed, unobservable, no-effect, and over-broad lessons.
- Promotion requires two distinct helped influenced audits, complete provenance, zero post-refinement misled audits, and deterministic replay/report health.
- Promotion and scope broadening fail closed when `baseline_status` is not `complete` or `comparable_event_set_sha256` changes; exclusion may proceed only from measured per-lesson harm plus replay health.
- `outweighed` requires a source-grounded external force or objective shock/range condition and two unrecovered source-grounded outweighed influenced audits block promotion.
- De-emphasis handles dormant lessons without marking them bad.
- Refinement creates a new body/new `lesson_id`, links parent, and prevents same-body executable edits.
- Retirement/exclusion requires measured harm under the v0 thresholds and deterministic replay/report health.

Scope tests:

- Ticker-born lesson reaches independent peer as low-authority candidate when predicates match.
- Sector lesson with nonmatching predicates is not rendered.
- `macro_subtype=commodity:<key>` lesson routes only when commodity key and price/curve predicate match.
- `macro_subtype=event_regime:<key>` lesson travels by setup predicates, not by ticker.
- False positives outside sub-industry narrow scope rather than globally retire valid sub-scope mechanism.
- Transfer basis accepts only `predicate_match`, `sector_structural`, `peer_explicit_list`, `macro_subtype_predicate`, or `independent_non_birth_evidence`.
- Transfer state accepts only `none`, `candidate_transfer`, or `proven_transfer`.
- `routing_audit` plus `routing_audit_detail` populates under-routed, over-routed, cap-excluded, candidate-transfer hit, and candidate-transfer miss strata, and enforces non-S10 source refs for under/over-routing.
- Bounded transfer pool excludes exact local ticker opportunities and includes only explicit candidate-transfer rows, declared peer rows, same-sector non-birth rows, and matching macro_subtype rows.
- Same-ticker later events cannot promote a ticker-born lesson to peer, sector, or macro authority; counted non-birth transfer evidence must come from destination tickers/source issuers different from the birth ticker/source issuer.
- Peer and macro proven promotion require at least two counted non-birth destination events from distinct non-birth destination tickers/source issuers matching the promoted peer list or macro_subtype predicates, zero transfer misled, and complete provenance.
- Validator rejects durable `scope_proof`; render-only proof summaries are derived from closed transfer fields.

Metrics/replay tests:

- Brier mapping for long/short confidence rejects directional `confidence_score <= 50` and proves monotonicity: for the same directional confidence, a correct call must have lower Brier than an incorrect call, including the anti-lazy exception band `51 <= confidence_score <= 55`.
- No_call usefulness and unknown-range denominator.
- Citation precision denominator excludes outweighed.
- Normal `routing_audit=none` transfer successes populate transfer-basis and destination strata from canonical lesson transfer fields plus the sealed auditor event or audit aggregation key.
- Applicability precision/recall from audits; denominator membership derives from prediction-time and learner applicability verdict pairs, so non-influential false-positive applies labelled `correct_nonapplication` still count as false positives and true negatives require both verdicts to be non-`applies`.
- Transfer precision/recall numerator and denominator match Section 11 and are stratified by birth scope/key, destination scope/key, macro_subtype, rendered/cap/routing/candidate-transfer buckets, and transfer basis.
- LLM ablation/tournament is not an authority gate in v0; if experimented with later, metadata and repeat-count rules must be reported separately.
- Blast radius groups parent lineage only in v0; no shingle or embedding similarity until a measured non-lineage near-clone incident.
- `--quality-report --gate lifecycle` emits structured JSON, exits non-zero on guardrail breach, reports baseline status and comparable event-set hash, and is consumed before lifecycle authority changes.

Operational tests:

- Event/ticker/global lock order cannot deadlock.
- Ticker/global D22 collision checks inside locks.
- Crash after learning result, ticker append, global append, audit aggregation, and quality seal converges or reports failed_recoverable without duplicates.
- Source tuple hash mismatch refuses seal and emits alert.
- Save-time commitment rejects unknown keys, wrong order, altered prompt sidecar, altered rendered prompt, and altered bundle payload.
- Q3 FCX source-complete legacy can be backfilled; Q4 FCX rows remain missing-source/unproven; Q1 all-sentinel prediction fails v2 anti-lazy validation.
- `--replay-check --all` exits non-zero and emits `LEARNER_ALERT` for extra/missing/hash drift.
- No v0 tournament mode is needed for authority; replay/report/backfill leave production artifacts unchanged except documented seals/recovery.

Passing-test status after Round 14 completion:

- PT1 Novice applicability: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT2 Committed prediction: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT3 Mechanism decomposition: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT4 Evidence-grounded predicates: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT5 Lift/non-regression lifecycle: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT6 Scope precision/recall: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT7 Predictor influence trace: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT8 Operational invariant preservation: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.
- PT9 Minimal implementation: PASS, judge-accepted in consecutive saturation Rounds 13 and 14.

## 15. Non-Goals and Rejected Ideas

Rejected for v0:

- Synthetic hindsight/back-attribution as authority for live lessons. Residual risk: sparse samples slow promotion, but authority remains honest.
- Multi-agent predictor debate as normal production. Residual risk: some conflicts remain hard, but conflict/no_call trace is cheaper.
- Broad micro-regime DSL. Residual risk: some nuanced predicates need data requests, but v0 stays maintainable.
- Vector database, embedding service, external database, dashboard, daemon, or queue.
- Trade execution, position sizing, trigger daemon expansion, or alert threshold changes.
- Tamper-proof blockchain/head-chain machinery. Local hash/replay checks are sufficient for current local filesystem scope.
- Persistent per-lesson stats duplicated everywhere. Derive from sealed event ledgers through `EventArtifactIndex`; add durable stats only if measured performance fails and judges approve.
- Automatic broad sector promotion from one ticker. Candidate transfer plus proof is safer.
- Automatic deletion of bad lessons. Exclude from rendering but preserve audit history.

Optional future simplification candidates, not canonical roadmap:

- Future `hypothesis_id` can be reconsidered only if same-body executable refinements prove necessary in real corpus maintenance. Residual risk in v0: authors must rewrite the body when the executable contract changes.
- Wilson/beta-binomial scoring is report-only below `influenced_n >= 10`. Residual risk: early promotion uses simple count thresholds, which are less statistically elegant but mechanically reproducible.
- Standalone commodity and event-regime scopes are deferred. V0 uses `macro_subtype`; residual risk is weaker reporting granularity until a real false-positive or under-routing cluster justifies scope expansion.

## 16. Judge Findings and Round-by-Round Consensus Log

Corpus/event file snapshot for cited FCX paths:

| Path | Size | Mtime epoch |
|---|---:|---:|
| `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json` | 361217 | 1778075845.7623757330 |
| `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle_rendered.txt` | 199075 | 1778075845.7623757330 |
| `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json` | 12821 | 1778076251.5310269840 |
| `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/section_audit.json` | 11985 | 1778076084.4163939720 |
| `earnings-analysis/Companies/FCX/events/Q3_FY2025/context_bundle.json` | 375951 | 1777989968.3766309640 |
| `earnings-analysis/Companies/FCX/events/Q3_FY2025/context_bundle_rendered.txt` | 182529 | 1777989968.3766309640 |
| `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json` | 9948 | 1777990375.2338035140 |
| `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/section_audit.json` | 14316 | 1777990231.1828141580 |
| `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json` | 23128 | 1777990989.0934343660 |
| `earnings-analysis/Companies/FCX/events/Q4_FY2025/context_bundle.json` | 370037 | 1778077515.9688725230 |
| `earnings-analysis/Companies/FCX/events/Q4_FY2025/context_bundle_rendered.txt` | 220680 | 1778077515.9688725230 |

Round log:

- Drift restat before Rounds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, and 14: core source snapshot in Section 0 and FCX corpus/event snapshot in this section matched exactly. No cited source or corpus path changed; no `CORPUS_DRIFT_DETECTED` stop was required.
- Round 0: Initial draft written. No judges run yet. Status remained ACTIVE. Known provisional issue: net-positive complexity over operational hardening needed explicit judge acceptance or simplification.
- Round 1 Judge A, Claude Opus 4.7, verdict REJECT. Main blockers: expected effect mixed direction and confidence; magnitude buckets lacked numeric anchors; predicate operator semantics lacked anchors; influence and influence_weight were incompatible; applicability verdicts overlapped; conflict detection was undefined; confidence delta and uncertainty lacked value spaces. Round 1 revision split direction/confidence effects, pinned magnitude buckets, simplified predicates/operators, collapsed applicability verdicts, dropped influence_weight, auto-derived conflicts, and added confidence caps/counter-thesis schema.
- Round 1 Judge B, Claude Opus 4.7, verdict REJECT. Main blockers: dual `lesson_id`/`hypothesis_id`, standalone commodity/event-regime scopes, tournament/LLM ablation in v0, enum proliferation, too many predicate operators, too many lifecycle tiers, Wilson/beta-binomial authority gates, optional schema fields, shingle near-clone logic, and verbose rendering. Round 1 revision cut `hypothesis_id`, collapsed commodity/event-regime into `macro_subtype`, removed tournament/LLM ablation from v0 authority, collapsed enums, reduced operators, reduced tiers, made Wilson report-only, removed optional fields, lineage-only blast radius, and compacted render blocks.
- Round 1 Judge C, Codex GPT-5.5 xhigh, verdict REJECT. Main blockers: lifecycle thresholds/non-regression constants undefined, ablation stochasticity uncontrolled, and Section 13 too lossy on operational substrate. Round 1 revision pinned promotion/dormancy/exclusion/report thresholds, removed LLM ablation as v0 authority, and inlined source tuple, hash origins, recovery notes, row projection fields, audit set equality, drift behavior, replay/report alerts, and migration classes into Section 13.
- Round 1 Judge D, Codex GPT-5.5 xhigh, verdict ACCEPT with should-fix findings. It required strict independent non-birth evidence for every high-authority non-ticker promotion, concrete macro/commodity precedence gates, explicit peer routing proof, canonical event-regime keys, and bounded missed-applicable search. Round 1 revision added all five.
- Round 2 Judge A, Claude Opus 4.7, verdict REJECT. Main blockers: conflict handling was promised but absent from the schema; anti-lazy all-irrelevant rule was ambiguous; S10 was undefined; evaluator override channel was missing; range delta and confidence-effect fields were ambiguous; influence enum needed priority rules. Round 2 revision added `conflict_handling`, rewrote anti-lazy as a two-row decision table, defined S10, added predicate override objects, dropped redundant/confusing effect fields, and added influence priority/source-ID rules.
- Round 2 Judge B, Claude Opus 4.7, verdict REJECT. Main should-fix items: remove redundant `confidence_effect`, unused `effect_uncertainty`, `range_delta_pct`, separate `outcome_noise`, stored `risky` tier, standalone `applicability_snapshot`, and peer/cross_ticker aliasing. Round 2 revision made confidence direction derivable from signed delta, removed unused effect/range fields, folded noise into `outweighed`, made risk a transient warning, folded applicability trace into `learning_snapshot`, and made v4 use `peer` while migrating legacy `cross_ticker`.
- Round 2 Judge C, Codex GPT-5.5 xhigh, verdict ACCEPT with should-fix metric clarifications. It wanted recall sign fixed, frozen baseline comparator, no-call range coverage reporting, and quality-event self-hash convention. Round 2 revision renamed missed rate and defined recall as `1 - missed_applicable_rate`, froze the baseline to existing artifacts, added range coverage/width reporting, and stated the self-hash convention.
- Round 2 Judge D, Codex GPT-5.5 xhigh, verdict ACCEPT with should-fix scope clarifications. It wanted recall sign fixed, explicit candidate-transfer rows, canonical macro_subtype keys, and structural sector rationale limited to candidate authority. Round 2 revision added all four.
- Round 3 Judge A, Claude Opus 4.7, verdict REJECT. Main blockers and should-fix items: anti-lazy source-ID counting still had two parses; predicate overrides did not say how to recompute `applicability_verdict`; S10 lacked a mechanical catalog classifier; high-quality conflict was undefined; `cited` versus `changed_confidence` was fuzzy; anti-lazy denominator was ambiguous. Round 3 revision rewrote anti-lazy as a counted two-key-driver/two-source-ID predicate with examples, made overrides recompute verdicts, required evidence-catalog `source_family`/`source_origin` for S10 classification, pinned high-quality conflict to deterministic complete-provenance lessons with at least one proven lesson, and made `cited` supportive/non-promotion-positive with a 5-point confidence threshold for `changed_confidence`.
- Round 3 Judge B, Claude Opus 4.7, verdict ACCEPT with nits. It suggested clarifying redundant hashes, simplifying counter-thesis, pinning `cited`, noting vol-agnostic magnitude buckets, and folding `risk_warning` into generic render warnings. Round 3 revision made `lesson_set_sha256` canonical while treating rendered learning-context hash as a renderer-drift tripwire, collapsed counter-thesis to opposing summary plus source IDs, pinned `cited`, documented vol-agnostic buckets as a measured-future refinement, and replaced first-class `risk_warning` with `_render_warnings[]`.
- Round 3 Judge C, Codex GPT-5.5 xhigh, verdict REJECT. Main should-fix items: non-regression baseline behavior was undefined when the frozen comparator was absent/incomplete or the comparable event set changed; `outweighed` could become a noise escape hatch; quality-report guardrails were advisory rather than an enforceable lifecycle gate. Round 3 revision added `baseline_status` and `comparable_event_set_sha256`, failed promotion/broadening closed when baselines are unavailable or event sets drift, required source-grounded `outweighed_by` evidence and blocked promotion after two unrecovered source-grounded outweighed influenced audits, and defined `learning_metrics.py --quality-report --gate lifecycle` as structured JSON with non-zero failure exit consumed by lifecycle code.
- Round 3 Judge D, Codex GPT-5, verdict ACCEPT with no findings. Scores were not all 5, so this is not a saturation round.
- Round 4 Judge A, Claude Opus 4.7, verdict REJECT. Main should-fix items: `applies_when` required/optional semantics were undefined; `changed_confidence` referenced fixed bins without binding them to Section 11; prediction-time versus learner applicability verdict disagreement did not say which governs audits; transfer_basis lacked a closed enum. Round 4 revision made all applies_when predicates mandatory in v0, bound confidence-bin crossing to Section 11 ECE bins, made learner applicability verdict govern audit qualification on disagreement, added a closed transfer_basis enum, capped absent counter-thesis directional confidence at 60, and pinned magnitude bucket boundaries.
- Round 4 Judge B, Claude Opus 4.7, verdict ACCEPT with nits. It suggested removing duplicate recovery step enum values, limiting `_render_warnings[]`, and moving reset out of metrics. Round 4 revision moved failed-recovery reset to a tiny sibling utility, removed duplicate recovery step values already derivable from `hash_origins`, and limited `_render_warnings[]` to `risk_warning` and `outweighed_pressure`.
- Round 4 Judge C, Codex GPT-5, verdict ACCEPT with no findings. Scores were not all 5, so this is not a saturation round.
- Round 4 Judge D, Codex GPT-5, verdict REJECT. Main should-fix items: transfer precision/recall lacked exact numerator/denominator/strata; under/over-routing metrics lacked an explicit field or derivation rule. Round 4 revision defined transfer precision and transfer recall over influenced transfer uses and bounded transfer opportunities, added required strata, and added compact `routing_audit` enum with source-ref and action compatibility rules.
- Round 5 Judge A, Claude Opus 4.7, verdict REJECT. Main should-fix items: influence compatibility did not cover `not_testable_missing_data` lessons that require no_call, and `conflict_handling` did not say how the winning side of a resolved conflict is labeled. Nits: close `source_family` enum and make unknown commodity keys explicitly rejected. Round 5 revision added an applicability-verdict by influence compatibility table, required `caused_no_call` only for missing-data lessons whose `requires_no_call` trace drove final no_call, clarified conflict winners use per-lesson `no_conflict`, added a closed `source_family` allowlist, and extended macro_subtype rejection to unknown commodity keys.
- Round 5 Judge B, Claude Opus 4.7, verdict ACCEPT with nits. It noted possible redundancy in `engagement_source_ids[]`, `rendered_learning_context_sha256`, and separate `reset_failed_recoverable.py`, but no blocker or should-fix findings. Round 5 revision trimmed the first two by deriving `engagement_source_ids[]` from traces plus required extra IDs and keeping rendered learning-context hash only in the quality-event/replay source tuple.
- Round 5 Judge C, Codex GPT-5, verdict ACCEPT with no findings, but `L_minimalism_implementability` scored 4, so this is not a saturation round.
- Round 5 Judge D, Codex GPT-5, verdict REJECT. Main should-fix items: bounded transfer pool was not canonical; `routing_audit` lacked structured detail fields needed for transfer strata; peer/macro non-birth evidence was not fully validator-countable. Round 5 revision defined `bounded_transfer_pool`, added required `routing_audit_detail`, defined counted non-birth transfer evidence, and added peer/macro proven-promotion count rules.
- Round 6 Judge A, Claude Opus 4.7, verdict REJECT. Main should-fix items: `requires_no_call=true` did not yet force final `direction=no_call`; predicate overrides could be justified with S10-only source IDs; blocked lessons mixed with not-applicable lessons bypassed anti-lazy. Nit: non-applicable/not-testable/blocked conflict handling should explicitly be `no_conflict`. Round 6 revision made `requires_no_call=true` a hard no_call validator obligation, required at least one non-S10 override source ID, counted production `blocked_by_invalid_if` lessons as non-applicable directional support for anti-lazy, and pinned non-applicable conflict handling to `no_conflict`.
- Round 6 Judge B, Claude Opus 4.7, verdict ACCEPT with all scores 5 and only nits. It noted unreachable `units=text` and an implicit `transfer_state` enum. Round 6 revision removed `text` from units and added closed transfer_state enum `none`, `candidate_transfer`, `proven_transfer`.
- Round 6 Judge C, Codex GPT-5, verdict ACCEPT with no findings, but all rubric scores were 4, so this is not a saturation round.
- Round 6 Judge D, Codex GPT-5, verdict ACCEPT with one nit and mostly 4 scores. Round 6 revision added that destination ticker and destination event identity are read from the sealed auditor event or audit aggregation key rather than duplicated in `routing_audit_detail`. This is not a saturation round.
- Round 7 Judge A, Claude Opus 4.7, verdict REJECT. Scores were all 5 except C=4 and G=4; PT1, PT3, PT5, PT6, PT8, and PT9 passed while PT2, PT4, and PT7 were provisional. Main should-fix items: `not_testable_missing_data` influence still used ambiguous "drove final no_call" wording when multiple missing-data lessons independently require no_call, and `requires_no_call` trace derivation omitted the predicate-level missing qualifier. Round 7 revision required every missing-data lesson whose final overridden trace has `requires_no_call=true` to use `caused_no_call` when final direction is `no_call`, required `none` when the trace is false, removed "drove" wording from the validator test, and defined `requires_no_call=true` as a final-verdict plus predicate-level missing condition.
- Round 7 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings.
- Round 7 Judge C, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings.
- Round 7 Judge D, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings.
- Round 7 is not a saturation round because Judge A rejected and introduced should-fix items. The revised plan must face another full judge round before any consecutive-saturation count can start.
- Round 8 Judge A, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings.
- Round 8 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings.
- Round 8 Judge C, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings.
- Round 8 Judge D, Codex GPT-5, verdict REJECT. Scores were all 5 except G=4, I=4, K=4, L=4, and N=4; PT1, PT3, PT4, PT5, and PT8 passed while PT2, PT6, PT7, and PT9 were provisional. Main should-fix items: `requires_no_call=true` remained over-broad for deterministically blocked or exact non-applicable lessons, and globally requiring `routing_audit_detail.transfer_basis` for every non-`none` routing audit forced fake transfer bases on exact-scope cap/under/over-routing rows. Round 8 revision narrowed `requires_no_call=true` to exactly `not_testable_missing_data` plus predicate-level missing `requires_no_call`, made `transfer_basis` required only for transfer-related routing audits, required omitted/null transfer basis for exact-scope routing audits, excluded exact-scope rows from transfer-basis strata, and added validator tests for both cases.
- Round 8 is not a saturation round because Judge D rejected and introduced should-fix items. The revised plan must face another full judge round before any consecutive-saturation count can start.
- Round 9 Judge A, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings. Its output included markdown fences despite the JSON-only instruction; the substantive verdict was ACCEPT.
- Round 9 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings. Its output included short prose plus a fenced JSON object despite the JSON-only instruction; the substantive verdict was ACCEPT.
- Round 9 Judge C, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, and no findings.
- Round 9 Judge D, Codex GPT-5, verdict REJECT. Scores were all 5 except A=4, E=4, G=4, and N=4; PT1, PT3, PT5, PT6, PT8, and PT9 passed while PT2, PT4, and PT7 were provisional. Main should-fix item: the decision order still routed a mixed false-plus-missing predicate set to `not_testable_missing_data`, allowing a lesson whose setup was already proven absent to force `no_call`. Round 9 revision made observed false mandatory `applies_when` predicates produce `not_applicable` with `requires_no_call=false` before missing-data handling, and added a shared applicability fixture for false plus missing `requires_no_call`.
- Round 9 is not a saturation round because Judge D rejected and introduced a should-fix item. The revised plan must face another full judge round before any consecutive-saturation count can start.
- Round 10 Judge A, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities.
- Round 10 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output included short prose plus a fenced JSON object despite the JSON-only instruction; the substantive verdict was ACCEPT.
- Round 10 Judge C, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities.
- Round 10 Judge D, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities.
- Round 10 is consecutive-saturation count 1 of 2. The plan cannot complete yet because the goal requires two consecutive saturation rounds.
- Round 11 Judge A, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities.
- Round 11 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities.
- Round 11 Judge C, Codex GPT-5, verdict REJECT. Scores were all 5 except A=4, H=4, J=3, and N=4; PT1, PT2, PT3, PT4, PT6, PT7, PT8, and PT9 passed while PT5 failed. Main blocker: directional Brier used `confidence_score / 100` even though directional calls below 50 were allowed, making wrong low-confidence calls score better than correct ones. Should-fix: `correct_nonapplication` could be read as affecting applicability precision even though it is a true negative. Round 11 revision made `long`/`short` validation reject `confidence_score <= 50`, changed the anti-lazy exception band to `51 <= confidence_score <= 55`, made unresolved high-quality conflicts require `no_call`, added Brier monotonicity tests including the anti-lazy band, and moved `correct_nonapplication` to specificity/negative applicability accuracy rather than applicability precision.
- Round 11 Judge D, Codex GPT-5, verdict REJECT. Scores were all 5 except E=4, I=4, L=4, and N=4; PT1, PT2, PT3, PT4, PT5, PT7, and PT8 passed while PT6 and PT9 were provisional. Main should-fix items: counted non-birth transfer evidence did not explicitly exclude the birth ticker/source issuer for high-authority non-ticker promotion, and durable `scope.scope_proof` was unconstrained cuttable schema. Round 11 revision required counted non-birth transfer evidence to use destination ticker/source issuer different from the birth ticker/source issuer, required peer/sector/macro proven promotion to use distinct non-birth destination tickers/source issuers, added same-ticker promotion rejection fixtures, and removed durable `scope_proof` in favor of render-only proof summaries derived from closed transfer fields.
- Round 11 is not a saturation round because Judges C and D rejected and introduced blocker/should-fix items. The consecutive-saturation count resets; the revised plan must face another full judge round before a new consecutive-saturation count can start.
- Round 12 Judge A, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, two nits, no blocker/should-fix findings, no new failure modes, and no simplification opportunities. Nits: the anti-lazy example still said `50-55` instead of `51-55`, and Section 17 had a stale PT9 provisional note.
- Round 12 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output included short prose plus a fenced JSON object and used noncanonical score-key names despite the prompt; the substantive verdict was ACCEPT.
- Round 12 Judge C, Codex GPT-5, verdict REJECT. Scores were all 5 except A=4, H=4, J=4, and N=4; PT1, PT3, PT4, PT6, PT7, PT8, and PT9 passed while PT2 and PT5 failed. Main should-fix items: the anti-lazy example still allowed `50-55`, and non-influential false-positive applies labelled `correct_nonapplication` could be read as both false positives and true negatives. Round 12 revision changed the example to `51-55` and made applicability precision, specificity, and negative applicability accuracy derive mechanically from prediction-time versus learner applicability verdict pairs, independent of `audit_outcome`.
- Round 12 Judge D, Codex GPT-5, verdict REJECT. Scores were all 5 except A=4, E=4, H=4, I=4, J=4, L=4, and N=4; PT1, PT3, PT4, PT7, and PT8 passed while PT2, PT5, PT6, and PT9 were provisional. Main should-fix items: the anti-lazy example still allowed `50-55`, and normal `proven_transfer` successes with `routing_audit=none` could lose transfer-basis/destination strata because `routing_audit_detail` is omitted. Round 12 revision changed the example to `51-55` and made normal `routing_audit=none` transfer-success strata derive from canonical lesson closed fields plus the sealed auditor event or audit aggregation key, keeping `routing_audit_detail` for routing anomalies and candidate-transfer hit/miss rows.
- Round 12 is not a saturation round because Judges C and D rejected and introduced should-fix items. The revised plan must face another full judge round before a new consecutive-saturation count can start.
- Round 13 Judge A, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output included short prose plus a fenced JSON object despite the JSON-only instruction; the substantive verdict was ACCEPT.
- Round 13 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output included short prose plus a fenced JSON object despite the JSON-only instruction; the substantive verdict was ACCEPT.
- Round 13 Judge C, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output used shortened PT keys, but every PT1-PT9 value was PASS and the substantive verdict was ACCEPT.
- Round 13 Judge D, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output used shortened PT keys and omitted `judge_id`, but every PT1-PT9 value was PASS and the substantive verdict was ACCEPT.
- Round 13 is consecutive-saturation count 1 of 2 after the Round 12 reset. The plan cannot complete yet because the goal requires two consecutive saturation rounds.
- Round 14 Judge A, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output included short prose before the JSON object despite the JSON-only instruction; the substantive verdict was ACCEPT.
- Round 14 Judge B, Claude Opus 4.7, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output included short prose plus a fenced JSON object despite the JSON-only instruction; the substantive verdict was ACCEPT.
- Round 14 Judge C, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output used shortened PT keys, but every PT1-PT9 value was PASS and the substantive verdict was ACCEPT.
- Round 14 Judge D, Codex GPT-5, verdict ACCEPT with all rubric scores 5, all PT1-PT9 PASS, no findings, no new failure modes, and no simplification opportunities. Its output used shortened PT keys, but every PT1-PT9 value was PASS and the substantive verdict was ACCEPT.
- Round 14 is consecutive-saturation count 2 of 2 after Round 13. Completion audit is now allowed.

## 17. Final Audit

Completion audit:

- Operational-hardening pre-check passed before this plan started, and Section 2 plus Section 13 inline the required operational substrate.
- Drift checks before Rounds 1 through 14 matched the frozen core-source and FCX corpus snapshots exactly. No `CORPUS_DRIFT_DETECTED` stop occurred.
- The plan had more than five judge rounds. Rounds 13 and 14 are two consecutive saturation rounds: every judge verdict was ACCEPT, every rubric score A-N was 5, every PT1-PT9 was PASS, and no judge reported blocker, should-fix, new failure mode, or simplification opportunity.
- R1-R15 are mapped in Section 0 and were rechecked by the final judge rounds.
- No production code, live corpus JSON, skill prompts, or existing plan files were edited. The only persistent artifact produced by this goal is `.claude/plans/LearnerLoopPlan_LessonIntelligence.md`; judge prompts/outputs stayed under `/tmp`.
- A weak predictor should have no material ambiguity left for deterministic high-authority lessons because predicates, invalidators, effect, source IDs, confidence semantics, conflict handling, no_call rules, and influence compatibility are explicit.
- The design improves lesson quality directly through executable hypothesis schema, deterministic applicability evaluation, lifecycle audit outcomes, scope transfer proof, and quality-tier ranking.
- The design connects lesson quality to prediction quality through Brier, no_call usefulness, citation precision, deterministic replay/report health, calibration, applicability precision/recall, transfer metrics, and structured lifecycle gates.
- The design preserves operational invariants: PIT/source tuple, locks, quality event, cache derivation, provenance, migration, replay/report, and alerts.
- The design is minimal and implementable as local Python/JSON schema, evaluator, renderer/ranker, prompt, validator, lifecycle, and report/replay changes. Rejected heavier machinery remains out of v0.
- Residual market uncertainty remains probabilistic. Source-grounded `outweighed` audits prevent punishing valid lessons for named unrelated shocks, but promotion/retirement still depends on finite samples and may be provisional in sparse regimes.

PT1 Novice applicability: PASS, judge-accepted.
PT2 Committed prediction: PASS, judge-accepted.
PT3 Mechanism decomposition: PASS, judge-accepted.
PT4 Evidence-grounded predicates: PASS, judge-accepted.
PT5 Lift/non-regression lifecycle: PASS, judge-accepted.
PT6 Scope precision/recall: PASS, judge-accepted.
PT7 Predictor influence trace: PASS, judge-accepted.
PT8 Operational invariant preservation: PASS, judge-accepted.
PT9 Minimal implementation: PASS, judge-accepted.
