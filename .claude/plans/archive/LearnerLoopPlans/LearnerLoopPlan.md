# EventMarketDB Learner Loop - Architecture Design Plan
Round: 10
Status: final design accepted
Last updated: 2026-05-11T02:18:52-04:00

## 1. Current Coded Model

Completion contract for this goal:

- Deliver a code-grounded model of the current Build -> Predict -> Learn -> Mutate -> Render loop.
- Verify the FCX Q3_FY2025 -> Q4_FY2025 -> Q1_FY2026 corpus path, including provenance gaps.
- Identify failure modes by stage and category, including F1-F6 plus newly discovered failures.
- Draft the smallest implementation-ready target architecture that makes the loop mechanically reliable, replayable, auditable, non-lazy, provenance-aware, and centered on self-learning.
- Persist this notebook after each round.
- Run four judge roles, collect well-formed JSON, resolve all non-nit findings, and do not mark complete unless all acceptance and review-diversity conditions are met.

Snapshot and drift status:

- Initial Round 1 snapshot captured the required code, skill, plan, live-learning, and FCX event paths. A Round 2 drift check on 2026-05-11 found the primary source/corpus mtimes unchanged for the relied-upon files: `scripts/earnings/earnings_orchestrator.py` remains `2026-05-06 10:28:40.826635549 -0400`; `scripts/earnings/validate_learning.py` remains `2026-05-04 09:44:03.579918685 -0400`; `scripts/earnings/renderer/lessons.py` remains `2026-05-04 10:51:04.202224770 -0400`; `scripts/earnings/_text_utils.py` remains `2026-05-04 11:56:10.593438215 -0400`; `.claude/skills/earnings-prediction/SKILL.md` remains `2026-05-08 11:12:45.332435612 -0400`; `.claude/skills/earnings-learner/SKILL.md` remains `2026-05-08 10:30:54.648345503 -0400`; `earnings-analysis/learnings/global.json` remains `2026-05-05 10:46:50.941820901 -0400`; `earnings-analysis/learnings/ticker/FCX.json` remains `2026-05-05 10:46:50.937820933 -0400`.
- Round 2 inventory confirms Q4 still has only `context_bundle.json`, `context_bundle_rendered.txt`, and two related filing files; there is still no Q4 `prediction/` or `learning/` artifact. Evidence: `earnings-analysis/Companies/FCX/events/Q4_FY2025/` inventory from Round 2 read.
- The worktree has many unrelated pre-existing changes outside this goal. This goal has modified no repo file except this notebook.

What is currently coded:

- Build stage: `build_prediction_bundle` validates quarter info, runs the seven builders, stamps `schema_version`, `ticker`, `quarter_info`, `pit_cutoff`, and `assembled_at`, then adds `learning_context` with `build_learning_context`. A non-assertion learning-context failure falls back to empty lessons and only logs a warning, which can mask memory-read failure as first-prediction-like state. Evidence: `scripts/earnings/earnings_orchestrator.py:196-280`.
- Predictor PIT: prediction/learning CLI defaults to `quarter_info["filed_8k"]` unless `--pit` or `--live` is supplied; learner derives its own PIT later. Evidence: `scripts/earnings/earnings_orchestrator.py:3688-3733`, `scripts/earnings/earnings_orchestrator.py:3781-3808`.
- Prediction validation requires `lesson_labels`, exact positional lesson text equality against renderer output, confirmed-only key-driver citations, and source-ID grounding through `evidence_source_catalog`. It forbids the exact `no relevant evidence` sentinel for confirmed/contradicted labels, but it does not reject an all-irrelevant all-sentinel batch. Evidence: `scripts/earnings/earnings_orchestrator.py:658-846`.
- Predictor skill requires one label per rendered L marker and says `no relevant evidence` is only for absent conditions/signals; the semantic discipline is prompt-only beyond the current validator gates. Evidence: `.claude/skills/earnings-prediction/SKILL.md:81-122`, `.claude/skills/earnings-prediction/SKILL.md:213-223`.
- Learner PIT uses a three-tier rule: next quarter filed timestamp, live-state filed timestamp, then current invocation time. Tier 3 depends on the current clock and is therefore non-replayable unless refused or explicitly quarantined. Evidence: `scripts/earnings/earnings_orchestrator.py:938-984`.
- Learner flow hard-gates on `prediction/result.json`, recovers if `learning/result.json` already exists, fetches actual return, derives learner PIT, invokes the learner, validates schema plus cross-file audit coverage, stamps metadata, appends ticker/global lessons, and aggregates audits. Evidence: `scripts/earnings/earnings_orchestrator.py:1133-1435`.
- Recovery can replay derived writes from an existing `learning/result.json`, sibling prediction, and bundle; it re-applies ticker/global appends and audit aggregation. This helps partial-write recovery but does not produce a sealed mutation manifest today. Evidence: `scripts/earnings/earnings_orchestrator.py:1205-1283`.
- `finalize_learning_result` currently rewrites `learning/result.json` with `Path.write_text`, then best-effort renders/harvests sidecars. Evidence: `scripts/earnings/earnings_orchestrator.py:3420-3474`.
- `finalize_prediction_result` writes prediction JSON atomically, then best-effort renders/harvests sidecars. Evidence: `scripts/earnings/earnings_orchestrator.py:3477-3544`.
- Ticker lesson appends stamp v3 lesson rows and upsert by `quarter_label`, but there is no ticker lock and D22 collision checks run before the atomic write. Evidence: `scripts/earnings/earnings_orchestrator.py:1463-1560`.
- Global lesson appends use `fcntl.flock`, but the D22 collision scan currently runs outside the global lock. Evidence: `scripts/earnings/earnings_orchestrator.py:1563-1694`.
- Lesson identity is `lsn_` plus sha256[:10] over normalized body, scope, and routing key. D22 scans for same ID/different content. Evidence: `scripts/earnings/earnings_orchestrator.py:1817-1898`.
- Status is a pure render-time function over PIT-visible `audit_history`: explicit `retire` or `refine` retires; recent misled count >=3 retires; recent misled count >=2 watches; otherwise active. The recent audit window is `LESSON_AUDIT_WINDOW = 5`. Evidence: `scripts/earnings/earnings_orchestrator.py:1776-1784`, `scripts/earnings/earnings_orchestrator.py:1900-1958`.
- Read/render view filters audit history by `audit_pit_cutoff`, computes status, drops retired lessons, and attaches `_render_status` plus `_render_audit_counts`. Evidence: `scripts/earnings/earnings_orchestrator.py:1961-2028`.
- Build-learning-context reads ticker/global stores, applies source PIT filtering, same-quarter self-leak guard, audit PIT filtering, status recomputation, retired-drop, scope routing, dedupe, recency sorting, and caps. Ticker caps are 8 source rows; global caps are sector 4, macro 4, cross 2. Evidence: `scripts/earnings/earnings_orchestrator.py:2101-2431`.
- Learner-result path decoration attaches `learner_result_path` only if source `learning/result.md` exists and asserts the current quarter is not allowed. Evidence: `scripts/earnings/earnings_orchestrator.py:2030-2099`.
- Renderer uses `iter_labeled_lessons` as the single L-numbering source, renders a `## Lessons To Label` block, and returns ordered lesson bodies only; decoration is excluded from `lesson_text`. Evidence: `scripts/earnings/_text_utils.py:29-79`, `scripts/earnings/renderer/lessons.py:180-229`.
- Renderer includes context-only source event data, `Data:` lines from `data_lessons`, `Why:`, and `learner_result` paths when present. Evidence: `scripts/earnings/renderer/lessons.py:229-296`.
- Learning validation is v3-only, requires structured predictor/global lessons, non-empty resolving `evidence_refs`, and `lesson_audit` shape. Audit `comment` remains free text and no root-cause enum exists. Evidence: `scripts/earnings/validate_learning.py:70-111`, `scripts/earnings/validate_learning.py:459-616`.
- Cross-file learner validation is orchestrator-only. It enforces audit count equals prediction label count, bundle lesson count equals labels count, audit index matches position, predictor label matches, `was_cited` matches prediction citations, and audit lesson text matches bundle body. Evidence: `scripts/earnings/earnings_orchestrator.py:2968-3099`.
- Audit aggregation upserts by `(auditor_ticker, auditor_quarter_label)` and applies audit entries to parent lessons; per-audit lookup/refinement failures are logged and skipped. Evidence: `scripts/earnings/earnings_orchestrator.py:2473-2488`, `scripts/earnings/earnings_orchestrator.py:2767-2963`.
- Learner skill says `lesson_audit` is required when prediction labels are non-empty and defines six review values plus three action values, but root-cause aggregation is still embedded in free text. Evidence: `.claude/skills/earnings-learner/SKILL.md:126-185`.
- Learner skill says global observations should default narrower when uncertain; current validator checks scope/routing shape but not transfer proof. Evidence: `.claude/skills/earnings-learner/SKILL.md:94-103`, `.claude/skills/earnings-learner/SKILL.md:191-260`, `scripts/earnings/validate_learning.py:322-443`.

Classification of useful but non-authoritative suggestions encountered in `.claude/plans/LearnerLoop.md`:

- Adversarial predictor debate: reject for v0. Validator-backed engagement fields and learner audit gates close the real lazy path with less complexity.
- Recursive/synthetic back-attribution: reject for v0 because it risks hindsight leakage and promotion from hypothetical tests.
- Micro-regime routing: simplify into explicit `applies_when`/`invalid_if` engagement plus evidence-tier ranking; defer hard regime filters.
- Tighten transfer/default narrower: adopt through `transfer_basis` and resolving evidence refs.
- Mechanism as causal chain: adopt as prompt guidance only; no new schema field.

## 2. Live FCX Corpus Evidence

Q3 birth:

- Q3 prediction has no prior lesson labels and no lesson citations, making it the seed prediction for this fresh library path. Evidence: `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json:1-28`.
- Q3 learner is `attribution_result.v3`, has learner PIT `2026-01-22T08:06:58-05:00` from `next_quarter`, and records actual FCX daily stock return `0.97`. Evidence: `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:1-20`.
- Q3 learner produced two ticker-scope `predictor_lessons`, three `data_lessons`, one BasicMaterials sector `global_observation`, and no `lesson_audit` because Q3 prediction had no prior labels. Evidence: `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:198-245`.
- `learnings/ticker/FCX.json` stores the Q3 row with two stamped ticker lessons and Q4 audit history on both. Evidence: `earnings-analysis/learnings/ticker/FCX.json:6-99`.
- `learnings/global.json` stores the Q3 BasicMaterials sector lesson with one Q4 neutral audit. Evidence: `earnings-analysis/learnings/global.json:5-46`.

Q3 lessons appearing in Q4:

- Q4 saved bundle learning context contains Q3 ticker lessons and Q3 sector lesson, all active, and the allowed learner path only points to Q3's learner result. Evidence: `earnings-analysis/Companies/FCX/events/Q4_FY2025/context_bundle.json:5260-5335`.
- Current disk inventory for Q4 contains only `context_bundle.json`, `context_bundle_rendered.txt`, and related filings; there is no `prediction/` or `learning/` file under `earnings-analysis/Companies/FCX/events/Q4_FY2025/`. Evidence: Round 2 filesystem inventory of `earnings-analysis/Companies/FCX/events/Q4_FY2025/`.

Q4 library mutation without source artifacts:

- Despite no Q4 prediction/learning artifacts on disk, `FCX.json` contains a Q4 row with two ticker lessons, source filed timestamp, source PIT cutoff, Q4 actual return, and learner-derived text. Evidence: `earnings-analysis/learnings/ticker/FCX.json:100-161`.
- `global.json` contains a Q4 BasicMaterials sector lesson sourced to Q4 and with no audit history. Evidence: `earnings-analysis/learnings/global.json:47-71`.
- Q3 lesson audit entries in `FCX.json` and `global.json` say their auditor quarter was Q4_FY2025 with `audit_pit_cutoff` `2026-04-23T08:09:07-04:00`, but the Q4 learner artifact that should explain those audits is missing. Evidence: `earnings-analysis/learnings/ticker/FCX.json:41-58`, `earnings-analysis/learnings/ticker/FCX.json:73-89`, `earnings-analysis/learnings/global.json:26-43`.

Q4 lessons appearing in Q1:

- Q1 saved bundle has predictor PIT `2026-04-23T08:09:07-04:00` and includes Q4 ticker lessons first, Q3 ticker lessons next, Q4 sector lesson, and Q3 sector lesson. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5472-5732`.
- Q1 saved bundle includes `_allowed_learner_paths` for both Q4 and Q3 learner result markdown, even though Q4 learner result markdown is no longer on disk. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5727-5732`, plus current Q4 filesystem inventory.
- Q1 prediction labeled all six lessons `irrelevant`, used exact `no relevant evidence` for all six, cited no lesson indices in all key drivers, and still produced a directional short with confidence 48. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:1-58`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:172-181`.

What the live JSON proves versus what is missing:

- Proved: Q3 prediction and learning artifacts exist and can explain Q3-born ticker/global lessons. Evidence: `earnings-analysis/Companies/FCX/events/Q3_FY2025/prediction/result.json:149-156`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:1-11`, `earnings-analysis/Companies/FCX/events/Q3_FY2025/learning/result.json:198-245`.
- Proved: Q4 library state exists and was visible to Q1. Evidence: `earnings-analysis/learnings/ticker/FCX.json:100-161`, `earnings-analysis/learnings/global.json:47-71`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5477-5732`.
- Missing: Q4 `prediction/result.json`, Q4 `learning/result.json`, Q4 `learning/result.md`, and Q4 `prediction/section_audit.json`. Therefore Q4 lessons and Q4 audits are not reconstructable from current source artifacts.
- Missing: Q1 learner/audit artifacts. Q1 has prediction artifacts but no `learning/` directory in the current event tree, so the all-irrelevant sentinel pattern has not yet been audited.

## 3. Failure Modes

Structural and validation failures:

- F1 anti-lazy predictor gap: all rendered lessons can be labeled irrelevant with the exact sentinel and zero citations because current validator only reserves that sentinel away from `confirmed` and `contradicted`. Evidence: `scripts/earnings/earnings_orchestrator.py:755-781`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/prediction/result.json:8-58`.
- F2 provenance gap: library mutations and audit histories can survive without source prediction/learning artifacts; saved bundles can carry stale learner paths. Evidence: `earnings-analysis/learnings/ticker/FCX.json:100-161`, `earnings-analysis/learnings/global.json:47-71`, `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5729-5732`.
- F3 recency-heavy ranking: current ticker rows and global buckets sort by `attributed_at` descending before caps; no helped/missed/proven quality tier exists. Evidence: `scripts/earnings/earnings_orchestrator.py:2202-2265`, `scripts/earnings/earnings_orchestrator.py:2352-2379`.
- F4 unstructured audit semantics: learner audit `comment` is a string and no root-cause enum exists. Evidence: `scripts/earnings/validate_learning.py:554-599`, `.claude/skills/earnings-learner/SKILL.md:130-181`.
- F5 over-broad global promotion: current prompt defaults narrower, but validator checks only shape/routing and not transfer proof. Evidence: `.claude/skills/earnings-learner/SKILL.md:94-103`, `scripts/earnings/validate_learning.py:322-443`.
- F6 data-lessons dead-letter risk: learner emits `data_lessons`, storage preserves them, and renderer prints them, but no mechanical backlog/review path turns repeated data needs into future behavior. Evidence: `.claude/skills/earnings-learner/SKILL.md:71-72`, `scripts/earnings/renderer/lessons.py:267-268`, `earnings-analysis/learnings/ticker/FCX.json:92-96`, `earnings-analysis/learnings/ticker/FCX.json:155-158`.
- F7 nondeterministic learner PIT fallback: historical learner tier 3 stamps current invocation time, which cannot be reconstructed later. Evidence: `scripts/earnings/earnings_orchestrator.py:943-984`.
- F8 derived library cannot be deterministically rebuilt today: appends and audits mutate `learnings/*.json`, but no replay verifier walks event artifacts and compares rebuilt library state to live state; Q4 proves this matters.
- F9 partial completion is not sealed by a manifest. Recovery can repair some partial writes, but automation cannot distinguish fully complete from derived-write-incomplete without re-running recovery. Evidence: `scripts/earnings/earnings_orchestrator.py:1205-1283`.
- F10 ticker concurrency risk: ticker lesson writes are atomic but unlocked, with a comment assuming single-ticker sequential processing. Evidence: `scripts/earnings/earnings_orchestrator.py:1487-1500`.
- F11 global D22 race risk: collision checks for global entries run outside the flock. Evidence: `scripts/earnings/earnings_orchestrator.py:1658-1668`.
- F12 sidecar/finalization non-atomicity: `finalize_learning_result` rewrites `learning/result.json` with `write_text`, not `_atomic_write_json`. Evidence: `scripts/earnings/earnings_orchestrator.py:3461-3464`.
- F13 audit aggregation skip risk: per-audit lookup/refinement failures are logged and skipped, so a run can succeed while one audited lesson was not mutated unless outcomes are sealed. Evidence: `scripts/earnings/earnings_orchestrator.py:2793-2806`, `scripts/earnings/earnings_orchestrator.py:2952-2962`.
- F14 saved-bundle replay drift: saved Q1 bundle contains a Q4 learner path that is missing now; replay from current source files can produce a different provenance surface. Evidence: `earnings-analysis/Companies/FCX/events/Q1_FY2026/context_bundle.json:5729-5732`.

Round 1 judge-discovered failures:

- F15 low-engagement learner audit promotion: a learner can structurally fill audits but give mass-neutral or cheap helped reviews unless the design requires verified audit evidence and rejects lazy audit batches. This can promote a lesson to top tier without real engagement. Evidence: Judge A Round 1; current validator audit shape at `scripts/earnings/validate_learning.py:554-599`.
- F16 bare-retire irreversibility: current `compute_status` retires on any visible `action=retire` or `action=refine`; a bare retire has no future rendered surface for correction and no child lesson. Evidence: `scripts/earnings/earnings_orchestrator.py:1937-1943`.
- F17 ambiguous required-vs-optional writes: current finalizers run best-effort sidecars, but the Round 1 sentinel design did not say whether sidecar failures block completion. Evidence: `scripts/earnings/earnings_orchestrator.py:3438-3441`, `scripts/earnings/earnings_orchestrator.py:3491-3495`.
- F18 replay total-order gap: Round 1 said chronological source order but did not define tie-breakers for same-time events or canonical JSON ordering.
- F19 bundle-hash gap: Round 1 did not specify that the prediction-time saved context bundle hash is recorded and rechecked at learning/replay time, even though F14 shows saved bundle drift matters.
- F20 wall-clock ranking tiebreaker: using `attributed_at` for same-tier ranking is vulnerable to clock skew; source PIT is the more replayable ordering key. Evidence: current `attributed_at` sorting at `scripts/earnings/earnings_orchestrator.py:2202-2265`, `scripts/earnings/earnings_orchestrator.py:2352-2379`.
- F21 schema-version ambiguity: adding prediction engagement, learner root cause, and transfer basis without version bumps can silently mix strict and legacy rows.
- F22 live-state PIT drift: learner PIT tier 2 can change if source filings are corrected later; replay needs to record and compare the originally resolved PIT. Evidence: `scripts/earnings/earnings_orchestrator.py:972-984`.
- F23 observability misses audit laziness: health counters must expose audit evidence-ref rates and all-neutral batch rates, not only prediction sentinel rates.
- F24 refinement-link ambiguity: current `action=refine` retires the parent, but no required successor pointer exists, so replay cannot prove which new lesson supersedes which parent when one run emits multiple refinements. Evidence: `scripts/earnings/earnings_orchestrator.py:1937-1943`, `scripts/earnings/validate_learning.py:554-599`.
- F25 same-event concurrency: library-level locks do not serialize the whole learner event critical section, so two learner runs can race on `learning/result.json`, derived writes, and manifest seal. Evidence: `scripts/earnings/earnings_orchestrator.py:1133-1435`.
- F26 manifest/quarantine validator gap: a sealed manifest or quarantine row must itself be validated before replay/render/report trusts it.
- F27 replay invocation cadence gap: a replay tool is insufficient unless called at learner success and in a documented local check path.
- F28 intra-event replay order gap: Round 2 defined inter-event ordering but not canonical ticker/global/audit ordering inside one sealed event.
- F29 learner audit-comment sentinel gap: Round 2 required non-sentinel comments but did not define the learner-side sentinel set or length floor.
- F30 non-ticker proof-count ambiguity: `distinct auditor_quarter_label` is ambiguous for sector/global lessons; promotion needs explicit distinct audit-key semantics.
- F31 renderer determinism gap: bundle/rendered hashes are only useful if identical JSON produces byte-identical rendered text.
- F32 next-quarter identity drift: learner PIT tier 1 must stamp the resolved next-quarter event identity so replay never re-discovers a different boundary.
- F33 redundant prediction rendered hash and warning fields: `context_bundle_rendered_sha256` and `prediction_artifact_warnings` duplicate other closure mechanisms.
- F34 over-broad root-cause enum: `not_learnable` and `outcome_noise` had no deterministic downstream distinction in Round 2.
- F35 undefined drift acknowledgment bypass: any replay/health unblock path other than restored artifacts or a validator-accepted quarantine record creates a hole in traceability.
- F36 replay drift block state gap: a failing `learning_replay.py --check` needs a local artifact that future learner runs consult, not only procedural language.
- F37 failed-unsealed rerun ambiguity: partial manifest diagnostics need recovery-mode semantics so normal reruns do not churn partial outcomes.
- F38 full-history misled guard gap: a bad lesson should not regain `proven` after old verified misled audits slide outside the recent window unless a refinement supersedes it.
- F39 render/tier duplication: after tier migration, `_render_status` and `_render_tier` should not both be canonical render health labels.
- F40 provenance reason over-granularity: render behavior is binary; artifact-specific missing paths can be reconstructed by the report.
- F41 root-cause enum overlap: `force_outweighed` and `outcome_noise` need collapse or deterministic divergence.
- F42 post-seal replay race: if manifest seal and replay check are separate, a crash between them can expose a trusted manifest before drift check writes a block.
- F43 audit-level quarantine gap: provenance-incomplete audit entries must be skipped by verified-audit tier/status predicates, not only provenance-incomplete lessons.
- F44 renderer surface drift: cutting rendered-bundle hashes requires a renderer version stamp so historical replay can detect changed prompt-visible rendering.
- F45 refinement fork risk: two later runs can refine the same parent into different children unless visible prior refinements block or redirect later refinements.
- F46 optional sidecar duplication: manifest `optional_writes[]` duplicates the merged report's corpus walk.
- F47 quarantine replay-treatment duplication: free-text `replay_treatment` duplicates deterministic behavior derived from quarantine `action`.
- F48 mixed learner outcome escape: `learning_outcome=mixed` is a catch-all that weakens all-neutral anti-lazy discipline.
- F49 cross-event refinement race: validation-time no-prior-refinement checks can pass concurrently before a library write lock re-checks parent state.
- F50 learner summary catch-all modes: `no_prior_lesson_signal`, `outcome_noise`, and `data_missing` need compatibility rules, or they become the new lazy batch escape.
- F51 sealed-pending ambiguity: an intermediate manifest state requires extra recovery semantics and is unnecessary if replay runs before the manifest is trusted.
- F52 quarantine lifecycle ambiguity: quarantine entries need active/resolved state and chain-head semantics so old entries cannot keep capping or mask new defects.
- F53 non-deterministic quarantine action: `awaiting_human` cannot cover drift or influence replay/tier/status because it has no deterministic treatment.
- F54 cross-event replay false drift: whole-library replay inside one event lock conflicts with concurrent event writes; sealing needs event-scoped delta replay, with full-library replay as a separate serialized gate.
- F55 no-manifest recovery gap: `learning/result.json` without manifest must force deterministic recovery/refusal, not a fresh LLM run.
- F56 replay drift block integrity gap: the drift block file needs schema validation or unreadable state must be treated as blocked.
- F57 renderer environment drift: renderer version must bind locale/timezone/JSON/line-ending environment, not only code.
- F58 storage row schema ambiguity: ticker/global lesson rows and audit-history entries need named schema versions for migration-safe tier predicates.
- F59 replay drift block append race: multiple event seals can append chained drift records concurrently unless the shared drift-block history has its own flock and repair path.
- F60 full-library replay quiescence gap: `learning_replay.py --check --all` can see ticker/global/audit writes mid-event unless it is ordered against all event seals by a replay-wide lock.
- F61 canonical array-order drift: concurrent shared-lock event seals can write logically identical ticker/global/audit arrays in completion order, while full-library replay rebuilds them in source order, causing false byte drift unless persistent arrays are canonicalized.
- F62 drift-block deletion bypass: treating absent `.replay_drift_block.json` as fresh state after manifests exist lets out-of-band deletion silently clear blocked sealing state.
- F63 replay drift tail truncation bypass: full-library replay can append drift records after the latest mutation manifest, so a separate local head anchor is needed to detect truncation back to the manifest-recorded head.

Over-engineering traps and cuts:

- Do not add a database, queue, service, dashboard, daemon, external monitor, or multi-agent predictor debate.
- Cut separate `prediction/complete.json`; prediction `result.json` is already atomic and can carry bundle-hash metadata.
- Cut separate `learning/complete.json`; the atomic existence of `learning/mutation_manifest.json` with `sealed_at` is the completion sentinel.
- Cut `_render_priority`; derive priority inline from `_render_tier`.
- Collapse `stale_neutral` into `unproven`; neutral count remains a report counter, not a tier.
- Replace provenance render decoration with `_render_provenance_complete: bool` only; reason classification lives in replay/report output and quarantine/manifest records.
- Cut a dedicated per-L source-map block; use existing source-event context plus compact marker/decorations.
- Merge `learning_health_report.py` and `data_lessons_report.py` into one local report tool with modes/subcommands.
- Cut `context_bundle_rendered_sha256`; keep `context_bundle_sha256` as the canonical prediction provenance hash and test renderer determinism separately.
- Cut `prediction_artifact_warnings`; let the merged report count optional prediction sidecar gaps.
- Collapse `not_learnable` into `outcome_noise` unless a later deterministic behavior justifies a separate enum.
- Collapse `force_outweighed` into `outcome_noise`; the deterministic behavior is the same: the lesson may be valid, but the market outcome is not mechanically learnable from that lesson.
- Cut `learner_engagement_summary` entirely; count parity and detailed causes remain enforced by cross-file validation and per-audit root causes.
- Drop `_render_status` as canonical render output after tier migration; keep `_render_tier` only as render health decoration.
- Move audit counts out of render decoration after tier migration; report can derive them from `audit_history`.
- Cut `_render_provenance_reason` entirely from render decoration.
- Cut manifest `optional_writes[]`; optional sidecar gaps are report-only.
- Cut quarantine `replay_treatment`; `action` drives deterministic replay/render behavior and `notes` carries human commentary.
- Cut `learning_outcome=mixed`; force a dominant outcome plus per-audit root causes.
- Cut `sealed_pending_replay`; manifest statuses are only `sealed` or `failed_unsealed`.
- Cut optional `engagement_note` and optional `no_learning_reason`; structured enums carry the mechanical signal.
- Cut prediction `lesson_engagement_summary`; all-irrelevant confidence discipline is checked directly against `direction`, `confidence_score`, and labels.
- Cut `learner_engagement_summary`; batch anti-laziness is derived from per-audit `root_cause`, `review`, `evidence_refs`, and same-run `data_lessons`.
- Cut `engagement_lesson_field`; `engagement_reason` already distinguishes applies-when vs invalid-if paths.
- Cut quarantine actions `awaiting_human` and `restored_artifacts_hash_match`; only active deterministic actions remain: `cap_unproven` and `exclude_from_rebuild`.

## 4. Judge Findings

Round 1 verdicts:

- Judge A, Claude Opus 4.7, adversarial: REJECT. Rubric D failed. Must-fix findings: learner anti-lazy audit gap; tier promotion gameable by low-evidence helped audits; bare-retire irreversibility; ambiguous sidecar/sentinel semantics; undefined replay ordering; missing prediction-time bundle hash. Should-fix findings: source PIT instead of wall-clock ranking; schema version bump; learner PIT drift detection; define tier audit window; ticker D22 inside ticker lock; audit-laziness health counters. Nit: normalize `data_lessons` strings rather than adding a second schema.
- Judge B, Claude Opus 4.7, minimal architecture: ACCEPT with should-fix cuts. Findings: cut separate prediction and learning completion artifacts; use `mutation_manifest` as sentinel; drop `_render_priority`; collapse `stale_neutral`; simplify provenance state to bool+reason; cut dedicated source map; merge health/data reports; make engagement_source_ids compatibility explicit; commit to refuse-and-skip for invocation-time PIT; skipped audits block manifest seal.
- Judge C, Codex GPT-5, invariant checker: ACCEPT. It accepted PIT, idempotency, replay, atomicity, identity, scope routing, cross-file parity, monotonicity, and provenance invariants as directionally covered by the Round 1 design.
- Judge D, Codex GPT-5, replay/ops: REJECT. Rubric A and G failed because current FCX Q4 mutations cannot be rebuilt and the Round 1 design lacked a mandatory quarantine/backfill artifact schema. Must-fix: Q4 missing-source rows are visible to Q1 and must not render as normal active memory. Should-fix: define replay tie-breaker and ensure invocation-time PIT cannot produce promotable memory.

Round 1 synthesis resolutions:

- A vs B on completion artifacts: adopt B's minimal cut while preserving A's bundle-hash requirement. Prediction `result.json` stores `context_bundle_sha256`; no `prediction/complete.json` and no rendered-bundle hash field. Learning uses `learning/mutation_manifest.json` as the sole sealed sentinel; no `learning/complete.json`.
- A vs B on provenance granularity: adopt B's bool+reason simplification. The reason string still lets health/replay group `missing_learning_result`, `missing_prediction_result`, `missing_bundle`, `legacy_unknown`, `quarantined_missing_artifact`, or `pit_drift`, but downstream behavior is binary: provenance incomplete caps tier at `unproven` and health reports it.
- A/D vs Round 1 on Q4 provenance: add a mandatory local quarantine/backfill schema. Until artifacts are restored or a quarantine record exists, health/replay fails; rendered missing-artifact lessons are capped and marked.
- A vs current retire semantics: do not allow explicit bare retire from the learner in v0. Explicit retirement must be superseding refinement, or it is rejected and handled through human quarantine. Misled-threshold retirement remains evidence-driven over verified audits.
- A/B on invocation-time PIT: commit to refuse-and-skip for new historical runs. Quarantine is for already-written legacy/non-replayable rows only.
- B on data lessons: do not add a new data lesson schema in v0. Normalize strings in the merged report by lowercase, whitespace collapse, punctuation normalization, and a small stop-word list.

Round 1 raw/stable judge artifacts:

- Claude Judge A prompt/output: `/tmp/eventmarketdb_judge_a_prompt.txt`, `/tmp/eventmarketdb_judge_a_output.json`.
- Claude Judge B prompt/output: `/tmp/eventmarketdb_judge_b_prompt.txt`, `/tmp/eventmarketdb_judge_b_output.json`.
- Judge C and D returned well-formed JSON through subagent notifications in this thread.

Round 2 verdicts:

- Judge A, Claude Opus 4.7, adversarial: ACCEPT after one malformed-output retry. It found no rubric failures and no must-fix findings, but gave should-fix hardening items: add explicit refinement successor links, event-scope learner locking, replay invocation cadence, quarantine write/validation contract, manifest validator, intra-event replay order, learner audit-comment sentinel set, explicit non-ticker proof-count semantics, renderer byte-determinism test, and stamped next-quarter identity.
- Judge B, Claude Opus 4.7, minimal architecture: ACCEPT. It recommended cuts: remove `context_bundle_rendered_sha256`, remove `prediction_artifact_warnings`, collapse `not_learnable` into `outcome_noise`, and derive quarantine paths instead of storing `affected_library_paths`.
- Judge C, Codex GPT-5 xhigh, invariant checker: ACCEPT. It accepted Round 2 invariant coverage and compatibility with existing module wiring.
- Judge D, Codex GPT-5, replay/ops: REJECT. Rubric A and G failed because current FCX Q4 rows and audits remain in the live libraries with no source artifacts and no actual `provenance_quarantine.json` corpus artifact. This goal forbids creating that corpus file, so Round 3 resolves the blocker by adding an explicit design-time provenance defect register in this notebook and requiring the future implementation to materialize the same entry before production health can pass.

Round 2 synthesis resolutions:

- A refinement-link finding: require `refined_to_lesson_id` on each `action=refine` audit and `parent_id` on the replacement lesson; validator computes/validates the target ID against same-run emitted lessons.
- A event-concurrency finding: add a per-event `.learning.lock` around the learner critical section and refuse rerun when a sealed manifest already exists unless explicitly in recovery mode.
- A replay-cadence finding: run `learning_replay.py --check` after each successful manifest seal and as a documented local CI/manual gate; non-zero drift blocks subsequent sealing.
- A quarantine/manifest validator findings: add `validate_mutation_manifest` and `validate_provenance_quarantine`; both replay and render/report must call them before trusting those artifacts.
- A intra-event ordering finding: replay applies ticker writes, then global writes, then audit applications sorted by `(parent_scope, parent_ticker, parent_lesson_id, auditor_ticker, auditor_quarter_label)`.
- A audit-comment sentinel finding: define a learner audit sentinel set and minimum comment length for verified audit credit.
- A proof-count finding: promotion uses distinct audit keys `(auditor_ticker, auditor_quarter_label)` and requires at least two distinct quarter labels for `proven`.
- A renderer/PIT findings: add renderer byte-determinism tests and stamp `pit_boundary_event_identity` for next-quarter/live-cycle PIT decisions.
- B cuts: remove redundant rendered bundle hash and prediction warning field; collapse root-cause enum; derive quarantine paths instead of storing them.
- D active-corpus blocker: the current FCX Q4 defect is explicitly marked in the design-time register below. The design does not claim the current live library is production-healthy until implementation creates the future quarantine artifact or restores Q4 source artifacts.
- D Round 3 blocker: remove all standalone `acknowledged` unblock language. Production health and subsequent sealing can pass only when drift is gone by restored/hash-matched artifacts or covered by a `validate_provenance_quarantine`-accepted quarantine entry.
- A Round 3 hardening: add persistent replay drift block artifact, failed-unsealed recovery semantics, full-history misled guard, explicit tier priority, and lock ordering.
- B Round 3 cuts: shrink learner engagement summary counts, drop `_render_status` after tier migration, simplify provenance reasons, and collapse `force_outweighed` into `outcome_noise`.

## 5. Minimal Target Architecture

Design principle: keep Python plus JSON files; make hidden shortcuts impossible or visible; make every mutation attributable to source artifacts; make replay deterministic; make lesson quality influence rendering before recency; cut components that duplicate closure signals.

What stays unchanged:

- Keep local modular Python and JSON files.
- Keep the core lesson content fields: `lesson`, `mechanism`, `applies_when`, `invalid_if`, `evidence_refs`.
- Keep ticker JSON and global JSON stores.
- Keep source PIT filtering, same-quarter self-leak guard, shared renderer L-order, D19 cross-file audit parity, D20 body-only label matching, D22 collision concept, active/watch/retired status, and audit-history upsert semantics.
- Keep `data_lessons` as operational text instructions; v0 reports them but does not auto-edit builders.

Target changes:

1. Prediction schema v2 with engagement evidence.
   - Surface: `validate_prediction_result`, prediction skill, `finalize_prediction_result`.
   - Contract: `prediction_result.v2` adds `context_bundle_sha256`, `renderer_version`, and per-label `engagement_reason` plus `engagement_source_ids`.
   - Compatibility: `condition_met` and `opposite_evidence` require non-empty `engagement_source_ids` resolving against `evidence_source_catalog`; `missing_precondition`, `invalid_if_triggered`, and `not_testable_no_bundle_signal` require empty source IDs and are distinguished entirely by `engagement_reason`. If every rendered lesson is irrelevant/not-testable, validator requires `direction == "no_call"` or `confidence_score` below a documented low-confidence threshold. No extra summary object is needed.
   - Validator rejects all-rendered-lessons all-irrelevant/all-sentinel/no-citation batches unless the not-testable/low-confidence-or-no-call rule is satisfied.
   - Enforcement: deterministic validator plus prompt instruction; semantic truthfulness remains learner-audited residual risk.
   - Closes: F1, F15, F19.

2. Learner schema v4 with verified audits and root cause.
   - Surface: `validate_learning.py`, learner skill, cross-file validator, audit aggregator.
   - Contract: `attribution_result.v4` keeps `lesson_audit[]` totality and adds required `root_cause` enum: `correct_nonapplication`, `lesson_bad`, `lesson_good_ignored`, `data_missing`, `outcome_noise`.
   - Current `lesson_audit[].evidence_refs` remains required and resolving; v4 makes it promotion-significant. Reviews `helped`, `missed`, and `misled` count as verified only when evidence refs resolve, `comment` passes the learner audit-comment gate, and root-cause/review/action compatibility passes.
   - Learner audit-comment gate: comments used for verified audit credit must be at least 40 non-whitespace characters after normalization and must not normalize to sentinel phrases such as `n/a`, `na`, `none`, `no comment`, `see above`, `same as above`, `nothing to add`, `nothing material`, `no signal`, `unclear`, or a single token.
   - No top-level learner engagement summary is needed. Batch outcome is derived mechanically from `lesson_audit[]`: all-neutral/all-correct-nonapplication is accepted only when every audit has root_cause `correct_nonapplication`; outcome-noise classification requires at least one audit with review `helped`, `missed`, or `misled` and resolving evidence refs; data-missing classification requires non-empty same-run `data_lessons` and at least one audit root_cause `data_missing`; learned-from-lessons classification requires at least one verified helped/missed/misled audit. Validator rejects lazy all-neutral batches by inspecting per-audit fields directly.
   - Explicit `action=retire` from the LLM is rejected. Bare retire requires a validated human quarantine decision using active `cap_unproven` or `exclude_from_rebuild`; it is not a new quarantine action enum and is not an LLM mutation. `action=refine` is the normal way to supersede a bad lesson.
   - Every `action=refine` audit must carry `refined_to_lesson_id`; the same learner result must emit exactly one replacement lesson with matching recomputed `lesson_id`, `parent_id` equal to the refined parent, and structurally distinct lesson text. The validator recomputes `expected_lesson_id` from each audited bundle body plus scope/routing, checks it against the audit's stamped `lesson_id`, and applies the same check to the same-run replacement's `refined_to_lesson_id`. The inverse is also enforced: every emitted `predictor_lessons[]` row with non-null `parent_id` must have exactly one same-run `lesson_audit[]` refine entry whose `refined_to_lesson_id` equals the row's recomputed `lesson_id` and whose audited parent equals `parent_id`; otherwise reject with `LESSON_PARENT_ORPHAN`. The replacement lesson is stored in the emitting/auditor event's target library according to its scope/routing; `parent_id` may reference a parent lesson in another ticker/global file, and replay reconstructs the chain by walking parent links across files. A learner run may refine a parent only if that parent has no prior PIT-visible refinement. If a prior successor exists, the learner must refine the current successor rather than fork the original parent. Quarantine affects tier/render trust but never erases a structural refinement successor for the no-fork check, so quarantined intermediate successors still count. The no-prior-refinement check is repeated inside the ticker/global write lock immediately before append, after re-reading the target library; this prevents concurrent cross-event refinement forks rather than merely detecting them after replay.
   - If the lock-time recheck fails with `REFINEMENT_FORK_CONFLICT`, the current run writes `failed_unsealed`, does not mutate the library, and reports recovery options: regenerate prediction context and rerun from the updated memory state, or add a validated quarantine entry. Recovery must not replay the same stale refinement blindly.
   - Enforcement: deterministic validator/cross-file gate plus skill instruction.
   - Closes: F4, F15, F16, F23.

3. Verified lesson tiers before caps.
   - Surface: replace `compute_status` with `compute_lesson_tier`, `_apply_render_view`, `build_learning_context` sort keys, renderer marker.
   - Contract: tier is transient render state over PIT-visible audit history after provenance caps. Tiers: `proven`, `promising`, `unproven`, `risky`. `retired` lessons are excluded before tier assignment, and there is no `stale_neutral` tier. After migration, `_render_tier` is the single canonical render health label; `_render_status` is removed from render output. Automatic misled-threshold retirement and watch/risky detection move into `compute_lesson_tier`'s pre-tier exclusion and risky-classification logic; the old separate `compute_status` helper is deleted.
   - Verified audit window: use `LESSON_AUDIT_WINDOW = 5` as the PIT-visible audit slice for tier and risky/retired decisions. Windowing applies to risky/retired so transient misled evidence does not permanently flag a lesson; promotion to `proven` uses full PIT-visible history since last refinement because evidence-driven supersession, not time, is the only valid way to clear verified misled for promotion. `verified_positive` is `helped` or `missed` with resolving audit evidence and compatible root cause; `verified_misled` is `misled` with resolving evidence.
   - Verified-audit predicates skip any audit whose `(auditor_ticker, auditor_quarter_label)` or parent lesson/audit key is covered by an active `validate_provenance_quarantine`-accepted entry with `action` `cap_unproven` or `exclude_from_rebuild`. Quarantined audits do not count for tier, risky, or retired decisions.
   - `proven`: provenance complete, at least two verified positives from distinct audit keys `(auditor_ticker, auditor_quarter_label)`, spanning at least two distinct quarter labels, and zero verified misled over the full PIT-visible audit history since the most recent refinement. A verified misled audit can only be cleared for future promotion by a refinement/supersession chain, not by time-window drift.
   - `promising`: provenance complete, one verified positive and zero verified misled in the window.
   - `risky`: watch-threshold behavior or any verified misled in the window.
   - `unproven`: everything else, including legacy audits lacking v4 root cause/evidence verification, missing provenance, neutral-only histories, and quarantined rows.
   - Ranking: sort by explicit tier priority `proven=0`, `promising=1`, `unproven=2`, `risky=3`; `retired` is excluded before caps. Within a tier, sort by `source_pit_cutoff` descending, then deterministic source tuple (`source_ticker`, `quarter_label`, `lesson_id`). `RISKY` lessons render after clean unproven lessons and carry a visible marker; they are still available as cautionary evidence unless tier logic excludes them as retired. `attributed_at` is display metadata, not an ordering authority.
   - Enforcement: deterministic code and renderer contract.
   - Closes: F3, F15, F20, F21.

4. Provenance complete bool plus reason.
   - Surface: `_decorate_with_learner_paths`, `_apply_render_view`, renderer marker, replay verifier.
   - Contract: render-view lessons receive `_render_provenance_complete: bool` only. The renderer emits `[provenance: missing]` from the bool; replay/report reconstruct reason classifications from manifests, quarantine entries, and corpus walk.
   - Missing/incomplete provenance caps tier at `unproven`; renderer marks `[provenance: missing]` without changing ordered lesson text.
   - Canonical provenance uses JSON artifacts and manifest hashes, not optional markdown sidecars. Existing `learning/result.md` remains human context only.
   - Enforcement: deterministic code/validator/replay.
   - Closes: F2, F14, F19.

5. Learning mutation manifest as the sole completion sentinel.
   - Surface: orchestrator success path after validation, library writes, and audit aggregation.
   - Contract: write `learning/mutation_manifest.json` atomically only after all required writes succeed. Presence of a manifest with `schema_version: learning_mutation_manifest.v1`, `sealed_at`, and `status: sealed` is the completion sentinel. There is no `learning/complete.json`.
   - Required writes: atomic `learning/result.json`; validation pass; ticker upsert or explicit no-op; global upsert/purge or explicit no-op; audit aggregation outcomes for every audit; event-scoped replay check inside the replay-wide shared lock and `.learning.lock`; manifest itself. The replay-wide shared lock, `.learning.lock`, and drift-block preflight begin before the first durable learner artifact write, including `learning/result.json`. A skipped audit blocks sealing and records `status: failed_unsealed` if a partial manifest is written for diagnostics. A normal rerun that sees `failed_unsealed` must switch to deterministic recovery mode or refuse with `RECOVERY_REQUIRED`; recovery may overwrite the partial manifest only after reusing the same source hashes and converging all required writes. Any `failed_unsealed` outcome is a health issue and increments the report counter.
   - A rerun that finds `learning/result.json` without a sealed `learning/mutation_manifest.json` must enter deterministic recovery mode or refuse with `RECOVERY_REQUIRED`. A fresh LLM run is allowed only when `learning/result.json` is absent.
   - Optional human sidecars (`learning/result.md`, `learning/thinking.md`, learner subagent files) are not stored in the manifest. The merged report finds optional sidecar gaps by corpus walk; canonical replay uses JSON plus hashes.
   - Manifest records event identity, source artifact paths and sha256 hashes, resolved learner PIT and boundary source, `pit_boundary_event_identity` (`ticker`, `quarter_label`, `filed_8k`) when the boundary comes from next-quarter or live-cycle state, prediction context-bundle hash copied from prediction v2, renderer version copied from prediction v2, lesson IDs emitted, refinement links, audit application outcomes, required write status, and `drift_block_chain_head_hash` after the seal-time drift-block read/append. Library paths are derived from ticker/scope/routing rather than stored. The prediction bundle hash in the manifest is copied from `prediction/result.json` at seal time, never recomputed from current bundle state; validators compare current/source hashes to detect drift.
   - Manifest sealing is single-write: under the replay-wide shared lock and `.learning.lock`, validate the drift block before any durable write, perform all required writes, run event-scoped replay against the candidate manifest/delta payload, validate the drift block again, then atomically write exactly one final manifest with the current drift-block chain head hash. Clean replay writes `status: sealed`; drift or incomplete writes atomically write `status: failed_unsealed` and `.replay_drift_block.json`. No `sealed_pending_replay` state exists, so downstream code never sees an ambiguous manifest.
   - `validate_mutation_manifest` is required before any code treats a manifest as sealed. It enforces required fields, 64-hex sha256 values, valid status enum (`sealed`, `failed_unsealed`), required write status shape, source hash consistency, renderer-version consistency, drift-block head pairing, and audit outcome counts matching rendered lesson/audit counts.
   - Enforcement: deterministic code and local JSON artifact.
   - Closes: F2, F8, F9, F13, F17, F19, F22.

6. Prediction result metadata instead of prediction completion sentinel.
   - Surface: `finalize_prediction_result`.
   - Contract: no `prediction/complete.json`. `prediction/result.json` remains atomic and carries `context_bundle_sha256` plus `renderer_version` from a single source-of-truth renderer constant. `renderer_version` includes the renderer code version and environment fingerprint in this canonical key order: `renderer_code=<const>;locale=C;tz=UTC;json=sort_keys,ensure_ascii,compact;py=<major.minor.micro>;eol=lf`. Runtime code sets POSIX/C locale, UTC timezone, deterministic JSON (`sort_keys=True`, `ensure_ascii=True`, compact separators), full Python micro version, and `\n` line endings before rendering. Optional prediction sidecar gaps are discovered by the merged report's corpus walk rather than persisted as `prediction_artifact_warnings`.
   - Learning halts with `PROVENANCE_DRIFT` if the current context bundle hash differs from the value stamped in prediction result. Replay also compares manifest hashes to prediction-stamped hashes.
   - Replay reports `renderer_drift` and caps affected lessons at `unproven` if the prediction/manifest renderer version no longer matches the active renderer version.
   - Enforcement: deterministic code.
   - Closes: F14, F19 while satisfying minimalism.

7. Deterministic replay/reconcile.
   - Surface: future `scripts/earnings/learning_replay.py`.
   - Contract: walk event learning manifests in stable order `(source_pit_cutoff, filed_8k, source_ticker, quarter_label, canonical_event_path)`. For legacy artifact replay, derive the same tuple from `learning/result.json` and bundle metadata where possible; otherwise classify `legacy_unknown`.
   - Rebuild into `/tmp` or requested output dir, write canonical JSON with sorted keys and deterministic list ordering, then compare live `learnings/*.json` to rebuilt state.
   - Storage canonicalization: every persisted array that replay compares is canonicalized with the same stable sort keys before atomic write and again inside the replay comparator for both live and rebuilt structures. Ticker quarter rows sort by `(source_pit_cutoff, filed_8k, source_ticker, quarter_label)`; `predictor_lessons` sort by `(source_pit_cutoff, source_ticker, quarter_label, lesson_id)`; global observation rows sort by `(scope, routing_key, transfer_basis, source_pit_cutoff, source_ticker, quarter_label, lesson_id)`, where `routing_key` is the deterministic scope bucket such as sector code, macro bucket, or cross-ticker target and `transfer_basis` is the proof type; `audit_history` sorts by `(audit_pit_cutoff, auditor_ticker, auditor_quarter_label, parent_scope, parent_ticker, parent_lesson_id)`. This makes concurrent event completion order irrelevant without making all event seals globally exclusive.
   - Intra-event replay order is fixed: ticker writes, then global writes, then audit applications sorted by `(parent_scope, parent_ticker, parent_lesson_id, auditor_ticker, auditor_quarter_label)`. Tests assert byte-stable output and byte-stable intermediate snapshots.
   - Report `provenance_gap`, `extra_live_row`, `missing_live_row`, `hash_drift`, `audit_drift`, `pit_drift`, `quarantined_row`, and `legacy_unknown` records.
   - Replay cadence: event seals acquire the replay-wide lock in shared mode before any durable learner artifact write, including `learning/result.json`, and hold it until the final manifest is written. Inside that gate and the same `.learning.lock` section as manifest sealing, run event-scoped `learning_replay.py --check --event <event>` before a manifest becomes trusted `sealed`. This check receives the in-memory or temporary candidate manifest/delta payload; that temporary payload is not a completion sentinel and does not reintroduce `sealed_pending_replay`. It validates only the candidate manifest's recorded lesson_ids, audit_keys, hashes, and derived row deltas, preventing concurrent events from creating false whole-library drift. Full-library `learning_replay.py --check --all` acquires the replay-wide lock in exclusive mode, so it waits for in-flight event seals to finish and blocks new event seals while it walks a quiescent corpus.
   - Any non-zero drift appends a record to `earnings-analysis/learnings/.replay_drift_block.json` with `blocked: true`, drift class, affected keys, timestamp, replay hash, and record hash. Every read-validate-append cycle of that file holds `.replay_drift_block.lock`, including event-scoped seal checks and `--check --all`; the same critical section atomically updates `earnings-analysis/learnings/.replay_drift_head.json` with only `schema_version` and the current `head_hash`. The manifest writer validates the drift block and head anchor before any durable learner write and again before final manifest write; final seal captures the head under `.replay_drift_block.lock` and immediately writes that captured value into the manifest. A concurrent append after that capture is a later valid head that forward-extends the manifest-recorded ancestor. Sealing is refused while the latest valid block record is blocked. Fresh systems with no mutation manifests and no head anchor must initialize a cleared genesis drift-block record plus matching head anchor under `.replay_drift_block.lock` before the first manifest is written; every manifest records a 64-hex head. If any sealed or failed-unsealed mutation manifest or drift-head anchor exists anywhere in the corpus, absent drift-block/head state is not fresh; the current drift-block head must match `.replay_drift_head.json` and forward-extend the head recorded by the most recent mutation manifest in replay sort order, or sealing refuses with `DRIFT_BLOCK_TAMPERING`. If the drift block or head anchor is absent-after-history, stale, unreadable, malformed, mismatched, or not a forward extension of that manifest head, normal sealing is refused; the defined recovery path is a quiescent full-library replay under the replay-wide exclusive lock plus drift-block lock that archives the bad/missing-state evidence with sha256 where available and rebuilds a fresh drift-block history and head anchor from mutation manifests plus current replay output. The block state may be cleared only by appending a clean replay record after artifacts are restored/hash-matched or every drift item is covered by a `validate_provenance_quarantine`-accepted deterministic quarantine entry. There is no standalone human acknowledgment bypass.
   - `validate_replay_drift_block` enforces schema version, append-only record shape, monotonic timestamps, required affected keys, replay hash format, a sha256 chain over prior record hash plus current record payload, pairing with `.replay_drift_head.json`, and ancestry from the latest mutation manifest's `drift_block_chain_head_hash`. The chain and head anchor detect out-of-band deletion, truncation, or partial file replacement, including full-library replay records appended after the latest mutation manifest; `.replay_drift_block.lock` prevents legitimate concurrent writers from forking the chain. The drift-block preflight is a short read-validate cycle under `.replay_drift_block.lock` released before ticker/global locks; later drift-block append/final validation follows the declared lock order. `validate_mutation_manifest` rejects manifests whose recorded drift-block head is not the current head at manifest write time or a valid historical ancestor during replay validation.
   - Run twice in tests and diff outputs byte-for-byte.
   - Enforcement: deterministic local verifier, not a service.
   - Closes: F8, F14, F18, F19, F22, F54, F56, F59, F60, F61, F62, F63.

8. Mandatory quarantine/backfill artifact for existing provenance defects.
   - Surface: future `earnings-analysis/learnings/provenance_quarantine.json` or equivalent local JSON consumed by replay/report/render. This is a future implementation artifact, not created in this design-only goal because the goal forbids production corpus edits.
   - Contract:
     - `schema_version: learning_provenance_quarantine.v1`.
     - `entries[]` fields: `defect_id`, `created_at`, `status`, `source_ticker`, `source_quarter_label`, `affected_lesson_ids`, `affected_audit_keys`, `reason`, `action`, `supersedes_defect_id`, optional `notes`.
     - `reason` enum includes `missing_source_artifacts`, `hash_drift`, `pit_drift`, `legacy_unknown`, `manual_backfill`.
     - `action` is required only for active entries; active action enum is only `cap_unproven` or `exclude_from_rebuild`. Resolved entries omit `action` or set it null and can never cover drift.
     - `status` enum is `active` or `resolved`; supersession is derived from `supersedes_defect_id`, not a separate status value.
   - Quarantine writes are append-only under atomic read-modify-write with a `provenance_quarantine.lock` flock. `validate_provenance_quarantine` enforces schema, enum values, affected key resolution, deterministic action handling, and `supersedes_defect_id` references before replay/render/report accepts an entry. It ignores optional `notes` for all deterministic behavior. It rejects forks where two entries supersede the same prior entry; the current status of a defect chain is the chain head, defined as the entry no later valid entry supersedes. Only active chain heads with action `cap_unproven` or `exclude_from_rebuild` cover drift and affect tier/status/replay. There is no `awaiting_human` covering action. Human review pending means no covering quarantine exists, so health/sealing remains blocked. Restoration is recorded by appending a `status=resolved` entry with `supersedes_defect_id` referencing the prior active defect after clean replay confirms restored hashes; resolved and non-head entries do not cover drift by themselves.
   - Health cannot pass while untraceable live rows exist without either restored artifacts hash-matching the manifest or a `validate_provenance_quarantine`-accepted active quarantine entry. Existing FCX Q4 rows require this before production trust. Human acknowledgment is not a separate state; it must be represented as a validated local quarantine entry.
   - Design-time FCX Q4 provenance defect register, explicit within this notebook because no corpus file may be created by this goal:

```json
{
  "schema_version": "learning_provenance_quarantine.v1-design-register",
  "entries": [
    {
      "defect_id": "fcx_q4_fy2025_missing_source_artifacts",
      "created_at": "2026-05-11T00:58:12-04:00",
      "status": "active",
      "source_ticker": "FCX",
      "source_quarter_label": "Q4_FY2025",
      "affected_lesson_ids": [
        "lsn_aa3bbf5a2f",
        "lsn_9715962817",
        "lsn_e7c3e06fa4"
      ],
      "affected_audit_keys": [
        {"parent_lesson_id": "lsn_bc0212da41", "auditor_ticker": "FCX", "auditor_quarter_label": "Q4_FY2025"},
        {"parent_lesson_id": "lsn_400487e13c", "auditor_ticker": "FCX", "auditor_quarter_label": "Q4_FY2025"},
        {"parent_lesson_id": "lsn_dc75ff5d86", "auditor_ticker": "FCX", "auditor_quarter_label": "Q4_FY2025"}
      ],
      "reason": "missing_source_artifacts",
      "action": "cap_unproven",
      "supersedes_defect_id": null,
      "notes": "Current disk has Q4 context_bundle files but no Q4 prediction/result.json or learning/result.json. action=cap_unproven deterministically caps Q4 emitted lessons at unproven, prevents Q4 audits from counting for tier/status, covers the known extra-live-row drift without trusting the row, and renders affected lessons as provenance-incomplete. Future implementation must materialize this entry in the quarantine artifact or restore hash-matching Q4 artifacts before production health can pass."
    }
  ]
}
```
   - Enforcement: deterministic replay/report gate plus human review for the quarantine decision.
   - Closes: F2, F8, F14, Judge D's recovery blocker.

9. Refuse invocation-time learner PIT for new historical mutation.
   - Surface: `derive_learner_pit`, `run_learner_for_quarter`, `validate_learning.py`.
   - Contract: if historical learner PIT would be `invocation_time`, the learner returns/skips `SKIPPED_NO_PIT_BOUNDARY` and does not mutate durable memory. Predictor `--live` is also refused for historical operations where the target quarter already has `filed_8k` in the past; replay verifies historical prediction `pit_cutoff == quarter_info["filed_8k"]` and emits `pit_drift` otherwise. There is no new non-replayable mutation path in v0.
   - Manifest records the resolved PIT and source for accepted runs. Replay re-derives PIT and reports `pit_drift` if the stored value differs; affected rows cap to `unproven` until reviewed.
   - Enforcement: deterministic code/validator.
   - Closes: F7, F22.

10. Tighten global promotion with transfer basis.
   - Surface: learner skill, `validate_learning.py`, `append_global_lessons`.
   - Contract: `global_observations[]` adds `transfer_basis` and `transfer_evidence_refs`; existing scope routing supplies the deterministic `routing_key` used for storage sort order. Scope-compatible bases: sector `direct_peer_evidence` or `sector_wide_mechanism_observed`; macro `market_wide_regime`; cross_ticker `named_transmission_link`.
   - Validator enforces presence, enum/scope compatibility, and non-empty resolving refs. If transfer proof is absent, the lesson must remain ticker scope.
   - Enforcement: deterministic shape/evidence-ref validation plus prompt-only semantic truthfulness audited later.
   - Closes: F5.

11. Merged local learning report.
   - Surface: future `scripts/earnings/learning_report.py` with modes such as `--health`, `--data-lessons`, and `--replay-summary`.
   - Contract: one corpus walk outputs local JSON/Markdown counters: citation rate, all-irrelevant rate, sentinel rate, lesson hit/miss/misled rates, audit evidence-ref resolving rate, all-neutral-audit-batch rate, tier distribution, provenance-gap count, quarantine count, replay drift count, replay drift block presence, consecutive failed-unsealed count, tier-window re-promotion attempts, data-lesson repeat groups, missing sealed manifests, optional sidecar warnings.
   - Data lesson grouping uses normalized strings only; no new data_lessons schema in v0.
   - Enforcement: deterministic local report; human review decides builder changes.
   - Closes: F6, F23.

12. Harden writes and locks.
   - Surface: `_atomic_write_json`, `append_ticker_lesson`, `append_global_lessons`, audit aggregation, quarantine writer.
   - Contract: use atomic write for finalized learner result; acquire a replay-wide gate and per-event `.learning.lock` for the full learner critical section; refuse a normal rerun when sealed manifest already exists; add ticker file locks; move ticker and global D22 collision scans inside their respective locked read-modify-write sections; a lock-time D22 same-ID/different-content collision rejects with `LESSON_ID_COLLISION`, writes `failed_unsealed`, and does not mutate the library; lock replay drift-block and quarantine writes; include per-audit mutation outcome in manifest; skipped audits block manifest seal.
   - Lock order: `.replay_all.lock` shared for event seals and exclusive for full-library `--check --all` is outermost, then per-event `.learning.lock`, then ticker file locks in alphabetical ticker-symbol order when multiple tickers are touched, then global flock, then `.replay_drift_block.lock`, then `provenance_quarantine.lock` innermost. Code must never acquire these in reverse order.
   - Enforcement: deterministic code.
   - Closes: F10, F11, F12, F13, F59, F60.

Invariant enforcement classification:

- Source lesson PIT visibility: deterministic code (`build_learning_context`).
- Audit PIT visibility: deterministic code (`_apply_render_view`).
- Same-quarter self-leak prevention: deterministic code (`build_learning_context`, learner path invariant).
- Prediction engagement evidence: deterministic validator plus skill; semantic truthfulness audited later.
- Learner audit engagement: deterministic validator/cross-file gate plus tier code; semantic truthfulness remains residual LLM risk.
- Mutation provenance: deterministic manifest, hash checks, replay verifier, and quarantine gate.
- Replay total order: deterministic replay code and canonical JSON writer.
- Lesson quality ranking: deterministic tier computation over verified audits.
- Scope promotion proof: deterministic schema/evidence-ref validation plus prompt semantics.
- Data lessons routing: deterministic report plus human review.
- Market prediction correctness: not guaranteed.

## 6. Exact Change Plan

Future edits, not implemented in this design-only goal:

1. `scripts/earnings/earnings_orchestrator.py`
   - Bump prediction output to `prediction_result.v2` in `finalize_prediction_result` and stamp context bundle hashes.
   - Extend `validate_prediction_result` for engagement fields, compatibility rules, all-sentinel rejection, source ID resolution, and confidence/no-call discipline.
   - Replace `compute_status` with `compute_lesson_tier`; use only verified PIT-visible audits in the last `LESSON_AUDIT_WINDOW`, fold watch/risky and retired exclusion into tier logic, and remove `_render_status` from render output.
   - Implement verified audit helpers: audit comment sentinel/length gate, verified positive/misled predicates, and distinct audit-key/quarter proof counting.
   - Extend `_apply_render_view` to attach `_render_tier` and `_render_provenance_complete`; do not attach `_render_priority`, `_render_status`, `_render_audit_counts`, or `_render_provenance_reason` after tier migration.
   - Update `build_learning_context` sorting to tier priority, `source_pit_cutoff`, deterministic source tuple; remove `attributed_at` as ranking authority.
   - Extend `_decorate_with_learner_paths` to check canonical JSON artifacts and manifest/provenance status; keep markdown paths optional for human context.
   - Add atomic `learning/mutation_manifest.json` writer after successful required writes; no `learning/complete.json`.
   - Add `validate_mutation_manifest` and call it before rerun recovery, replay, render/report, or sealed-manifest short-circuit trusts the manifest.
   - Add `.replay_drift_block.json` / `.replay_drift_head.json` read/write logic, `.replay_drift_block.lock`, and `validate_replay_drift_block`: replay appends a chained drift record on drift and atomically updates the `{schema_version, head_hash}` anchor under the lock; absent block/head is allowed only before any mutation manifest exists; manifest sealing refuses while the latest valid record is blocked, the block/head files are unreadable/malformed/mismatched, or the block head does not match the anchor and extend the latest manifest-recorded head; clean replay appends a cleared record only after restoration or validated deterministic quarantine coverage; tampered/malformed-block recovery archives the bad or missing state and rebuilds history plus head anchor from a quiescent full-library replay.
   - Use single-write sealing: under the replay-wide shared lock and `.learning.lock`, validate drift-block/head state before any durable learner artifact write, run event-scoped replay against the candidate manifest/delta payload, validate drift-block/head state again, then atomically write `sealed` or `failed_unsealed` with `drift_block_chain_head_hash`; never expose `sealed_pending_replay`.
   - Use event-scoped replay for in-lock sealing and serialized full-library replay for CI/manual checks; `learning_replay.py --check --all` takes the replay-wide lock exclusively so it never walks mid-event partial writes.
   - Canonicalize persistent ticker/global/audit arrays before atomic write using the replay sort keys so concurrent event completion order cannot create byte drift.
   - Use `_atomic_write_json` inside `finalize_learning_result`.
   - Add a replay-wide `.replay_all.lock`, per-event `.learning.lock`, ticker-level file locks, and move ticker/global D22 scans inside locks.
   - Make skipped audit aggregation outcomes block manifest sealing.
   - Stamp `pit_boundary_event_identity` for next-quarter/live-cycle learner PIT decisions and `renderer_version` with renderer environment fingerprint in prediction/manifest artifacts.
   - Refuse-and-skip historical learner runs whose PIT boundary would be `invocation_time`.

2. `scripts/earnings/validate_learning.py`
   - Bump learner schema to `attribution_result.v4`.
   - Require `root_cause` on `lesson_audit[]` and enforce review/action/root-cause compatibility.
   - Derive batch outcome from per-audit fields; no `learner_engagement_summary` is emitted.
   - Reject explicit bare `action=retire`; allow `refine` only with a same-run replacement lesson linked by `refined_to_lesson_id` and `parent_id`.
   - Recompute expected lesson IDs from audited rendered lesson body plus scope/routing and reject audit or replacement `lesson_id` mismatches before mutation; reject any non-null replacement `parent_id` without a matching same-run refine audit.
   - Reject refinement of a parent that already has a prior PIT-visible refinement; require refining the current successor instead. Repeat this no-prior-refinement check inside the ticker/global write lock immediately before append.
   - Enforce learner audit comment sentinel/length rules before an audit can count as verified.
   - Add `transfer_basis` and `transfer_evidence_refs` to `global_observations[]` with scope-specific compatibility and resolving refs.
   - Use the existing deterministic scope/routing bucket as `routing_key` for global sort order; do not add a separate transfer-key field.
   - Reject durable historical outputs with `pit_boundary_source == invocation_time`.

3. `scripts/earnings/renderer/lessons.py`
   - Render compact `[tier: ...]` and `[provenance: missing]` markers outside `ordered_lesson_texts`.
   - Cut the dedicated per-L source-map block; reuse current source-event context and optional learner-result path decoration.
   - Preserve D20 body-only matching.

4. `.claude/skills/earnings-prediction/SKILL.md`
   - Add engagement fields and compatibility rules without hardcoded examples.
   - Require every irrelevant lesson to identify missing precondition, triggered invalid_if, or not-testable-no-bundle-signal.
   - Require confirmed-but-not-cited lessons to explain noncitation.
   - Add confidence/no-call discipline when no proven/promising lesson confirms and non-lesson evidence is mixed.

5. `.claude/skills/earnings-learner/SKILL.md`
   - Add root-cause enum and compatibility table.
   - Do not emit `learner_engagement_summary`; derive batch discipline from per-audit `root_cause`, `review`, `evidence_refs`, and same-run `data_lessons`.
   - Replace theoretical sector promotion language with transfer-proof requirements.
   - Keep data lessons operational and tie `data_missing` root causes to `data_lessons`.
   - State that bare retire is not allowed; refine or keep with verified misled evidence.

6. `scripts/earnings/learning_replay.py`
   - Deterministic rebuild from sealed manifests and legacy artifacts into temp output.
   - Stable sort tuple: `(source_pit_cutoff, filed_8k, source_ticker, quarter_label, canonical_event_path)`.
   - Implement `--event` event-scoped delta check for manifest sealing and `--all` serialized full-library check for CI/manual replay.
   - Make `--event` consume a candidate manifest/delta payload while inside the event seal critical section; the temporary payload is not a sentinel.
   - Make `--all` acquire `.replay_all.lock` exclusively; event seals hold the same lock shared from before first durable mutation through final manifest write.
   - Stable intra-event order: ticker writes, global writes, then audit applies sorted by `(parent_scope, parent_ticker, parent_lesson_id, auditor_ticker, auditor_quarter_label)`.
   - Canonical JSON output with sorted keys and deterministic arrays; canonicalize both live and rebuilt structures before byte/hash comparison. Row-internal arrays are either preserved in source-artifact order when order is semantic, or canonicalized by named key/normalized value (`evidence_refs`, `transfer_evidence_refs`, and normalized `data_lessons`) before replay comparison.
   - Compare live and rebuilt libraries; consume quarantine file; emit drift/provenance records.
   - Expose `--check` for post-learner and local CI/manual gates; non-zero drift blocks later sealing.

7. `scripts/earnings/learning_report.py`
   - Merge health, data-lessons, and replay-summary reporting.
   - Include audit evidence-ref, duplicate audit-comment, all-neutral batch, replay drift block, consecutive failed-unsealed, optional sidecar gap, renderer drift, and tier-window re-promotion counters.
   - Normalize data lesson strings in-report rather than adding a schema.

8. `earnings-analysis/learnings/provenance_quarantine.json` future schema
   - Add only when implementing recovery/backfill. Do not create it during this design-only goal.
   - Add append-only atomic flocked writer and `validate_provenance_quarantine` before any entry covers a defect; no `awaiting_human` entry can cover drift.
   - Derive replay/render treatment from `action`; do not store free-text `replay_treatment`.
   - Require `action` only on active entries, use only `active`/`resolved` statuses, reject quarantine chain forks, and treat only active chain heads as drift-covering.
   - Consume it in replay/report/render so FCX Q4-style defects are visible and capped until restored or covered by a validated quarantine entry.
   - Materialize the design-time FCX Q4 register entry from Section 5.8 or restore hash-matching Q4 artifacts before production health can pass.

Migration/backfill:

- Existing Q4 FCX rows are `missing_source_artifacts` until artifacts are restored or a quarantine entry exists. They must cap to `unproven` and cannot promote.
- For this design-only goal, the FCX Q4 defect is explicitly marked in the Section 5.8 design-time register. Implementation must convert that register into the future quarantine artifact or restore the source artifacts; until then, the current live library is intentionally not claimed healthy.
- Existing v1/v3/v2 rows lacking engagement/root-cause/transfer fields are legacy. Replay/report classifies each exactly once as `legacy_unknown`, `missing_artifact`, or restored; no silent grandfathering into proven tiers.
- Schema bump path: `prediction_result.v2`, `attribution_result.v4`, `ticker_lesson_row.v2`, `global_observation_row.v2`, and `audit_history_entry.v2`. Read-side tier/provenance predicates branch on these explicit row schema versions, not field-presence sniffing.
- Add tests before any corpus migration.

Minimality justification:

- All changes stay in existing Python modules, JSON schemas, and local scripts.
- Separate completion JSON files were cut; the manifest and atomic prediction result carry the needed closure signals.
- No external infrastructure is required.
- Every added field/script closes a named failure: engagement closes F1; verified audits/root cause/refinement links close F4/F15/F16/F23/F24/F29/F30; manifest/replay/quarantine close F2/F8/F9/F13/F14/F17-F19/F22/F26-F28/F31/F32/F54/F56/F59-F63; tiers close F3/F20; transfer basis closes F5; merged report closes F6/F23; PIT skip closes F7; locks/atomicity close F10-F12/F25/F59-F61.

## 7. Verification Plan

Replay tests:

- Build a temp learning library from Q3 artifacts and verify it reproduces Q3-born lessons.
- Include current FCX Q4 library rows and assert replay reports them as extra live rows/missing-source defects unless a quarantine entry is supplied.
- Rebuild twice and assert byte-stable output.
- Assert replay ordering is stable for same-timestamp synthetic events using the full sort tuple.
- Assert replay intra-event order is stable and byte-identical at each step.
- Assert `validate_mutation_manifest` rejects missing hashes, malformed statuses, mismatched audit outcome counts, stale source hashes, and renderer-version mismatch.
- Assert prediction context-bundle hash mismatch triggers `PROVENANCE_DRIFT`.
- Assert renderer-version mismatch triggers `renderer_drift` and caps affected lessons at `unproven`.
- Assert `renderer_version` uses the canonical ordered format with full Python micro version and byte-identical output under the pinned environment.
- Assert stamped `pit_boundary_event_identity` is used at replay time and replay never re-discovers a different next quarter.
- Assert event-scoped `learning_replay.py --check --event` runs inside the replay-wide shared lock and `.learning.lock` before a manifest is written as trusted `sealed`; it validates a candidate manifest/delta payload, not an intermediate sentinel.
- Assert drift writes `failed_unsealed`, appends a validated `.replay_drift_block.json` record under `.replay_drift_block.lock`, and blocks subsequent manifest sealing until a clean replay after restoration or validated deterministic quarantine coverage appends a cleared record.
- Assert two concurrent drift writers serialize through `.replay_drift_block.lock` and produce a valid sha chain.
- Assert the first seal initializes a cleared genesis `.replay_drift_block.json` record and matching `.replay_drift_head.json` under `.replay_drift_block.lock`, and every manifest records a 64-hex `drift_block_chain_head_hash`.
- Assert `.replay_drift_head.json` contains only `schema_version` and `head_hash`, and final manifest sealing writes the captured head; a concurrent later append is accepted only as a forward extension.
- Assert absent `.replay_drift_block.json` or `.replay_drift_head.json` is treated as no prior records only before any mutation manifest exists; if any sealed or failed-unsealed manifest or drift-head anchor exists, absent state or a head that does not match the anchor and extend the head recorded by the most recent mutation manifest in replay sort order rejects with `DRIFT_BLOCK_TAMPERING`.
- Assert malformed, unreadable, deleted-after-history, stale-head, mismatched-head, or non-extending drift block/head state blocks normal sealing; recovery archives the bad/missing-state evidence and rebuilds a fresh drift-block history plus head anchor only under exclusive full-library replay plus drift-block lock.
- Assert full-library replay drift records appended after the latest mutation manifest cannot be truncated away because `.replay_drift_head.json` still points to the newer head.
- Assert whole-library `learning_replay.py --check --all` takes `.replay_all.lock` exclusively and cannot observe ticker/global/audit writes between an event's first durable mutation and final manifest write.
- Assert two event seals that complete in the reverse of replay source order still produce byte-identical live and rebuilt libraries because ticker quarter rows, predictor_lessons, global entries, and audit_history are canonicalized before write and before replay comparison.
- Assert row-internal arrays are deterministic: source-order-preserved arrays stay in source artifact order, while `evidence_refs`, `transfer_evidence_refs`, and normalized `data_lessons` canonicalize before replay comparison.

Prediction validation tests:

- Recreate Q1 all-irrelevant/sentinel/no-citation output and assert new validator rejects it.
- Assert all-`not_testable_no_bundle_signal` batches require `direction == "no_call"` or `confidence_score` below the documented low-confidence threshold.
- Assert `condition_met` and `opposite_evidence` require resolving engagement source IDs.
- Assert D20 positional lesson matching still rejects decorated marker/body drift.
- Assert confirmed-only citation rule still holds.

Learner validation tests:

- Missing `root_cause` rejects.
- Incompatible `root_cause`/`review`/`action` rejects.
- All-neutral audit batch rejects unless every audit is correct nonapplication/neutral from per-audit fields; no learner summary is required.
- Bare `action=retire` rejects; `refine` with valid replacement passes.
- `action=refine` without `refined_to_lesson_id`, with an unrelated replacement, or with duplicate same-run successors rejects.
- Audit or replacement lesson IDs that do not recompute from rendered body plus scope/routing reject with `LESSON_ID_MISMATCH`.
- A replacement lesson with non-null `parent_id` but no matching same-run refine audit rejects with `LESSON_PARENT_ORPHAN`.
- A second refinement of a parent with a prior PIT-visible refinement rejects unless it targets the current successor.
- Concurrent cross-event refinements re-check parent refinement state inside the ticker/global write lock; the second writer rejects rather than forking the parent.
- Per-audit batch compatibility rejects catch-all misuse: outcome-noise requires at least one verified non-neutral audit, and data-missing requires same-run data lessons.
- Audit comments that normalize to learner sentinel phrases or are shorter than the minimum verified length cannot count as verified promotion evidence.
- Missing `transfer_basis` or unresolved `transfer_evidence_refs` on global observations rejects.
- Historical `pit_boundary_source=invocation_time` rejects/skips without mutation.

FCX regression tests:

- Q3 prediction still passes as first-prediction after v2 migration/defaults.
- Q3 learning validates after v4 migration/defaults where appropriate.
- Q1 saved prediction fails new anti-lazy validation, proving F1 closure.
- Q1 context classifies Q4 lessons as missing-artifact/unproven until restored/quarantined.

Ranking/status tests:

- Proven/promising lessons outrank newer unproven lessons under caps.
- Legacy audits lacking root cause/evidence verification cannot create `proven` tier.
- Two verified positives from distinct future quarters are required for `proven`.
- Sector/global `proven` requires distinct `(auditor_ticker, auditor_quarter_label)` audit keys spanning at least two quarter labels.
- Quarantined audits, including the FCX Q4 audit keys in the Section 5.8 register, do not count for tier, risky, or retired decisions.
- Verified misled makes a lesson risky/watch and prevents proven rendering.
- Retired lessons remain dropped before caps; bare retire is not accepted from learner output.
- A quarantined refinement successor still counts as part of the structural no-fork refinement chain; quarantine affects tier/render trust, not parent-chain existence.

Recovery/idempotency tests:

- Crash after `learning/result.json` before ticker/global appends: rerun recovery writes exactly one row and one audit per key and seals one manifest.
- Crash after ticker append before global append: recovery converges to the same final library.
- Skipped audit aggregation blocks manifest seal and is retried idempotently.
- Concurrent global writes do not bypass D22 because collision scan occurs inside lock.
- Lock-time D22 same-ID/different-content collision rejects with `LESSON_ID_COLLISION`, writes `failed_unsealed`, and leaves the library unchanged.
- Concurrent ticker writes serialize through ticker lock and D22 inside lock; cross-ticker refinement/audit writes acquire multiple ticker locks in alphabetical order without deadlock.
- Concurrent same-event learner invocations serialize through `.learning.lock`; a sealed manifest causes normal rerun refusal.
- Optional sidecar failure is reported by corpus walk but is not stored in the manifest and does not block canonical replay.
- Quarantine writer uses flock and `validate_provenance_quarantine`; malformed quarantine entries, chain forks, resolved entries, and non-head entries do not cover defects.
- Renderer produces byte-identical output for byte-identical bundle JSON under fixed locale/time formatting.
- Render decoration contains only `_render_tier` and `_render_provenance_complete`; audit counts and provenance reasons are report/replay outputs.

Observability tests:

- Report counts Q1 sentinel rate as 6/6.
- Report counts Q4 provenance gap and/or quarantine record.
- Report recognizes the Section 5.8 FCX Q4 design-time register as the current explicit provenance defect marker for this design-only goal, and future implementation tests require the materialized quarantine artifact before health passes.
- Report counts audit evidence-ref resolving rate and all-neutral audit batch rate.
- Report counts replay drift block effective state from append-only history, any failed-unsealed manifests, duplicate audit-comment rate, optional sidecar gaps, renderer drift, and tier-window re-promotion attempts after prior verified misled audits.
- Report groups repeated options-implied straddle data lessons after string normalization.
- Replay report feeds health report's replay drift count.

## 8. Non-Goals

- No claim of guaranteed market prediction accuracy.
- No trade execution, position sizing, order placement, trade daemon, or trigger daemon expansion.
- No database, queue, service, dashboard, daemon, or external monitoring stack.
- No synthetic back-attribution for promotion.
- No hard machine-readable regime filter in v0.
- No automatic implementation of data lessons as new builders in v0.
- No code or production corpus changes in this design-validation goal.

## 9. Consensus Log

Round 1:

- Drafted v0 from direct code/corpus reading.
- Claude Code Opus 4.7 smoke test returned `CLAUDE_47_OK`.
- Judge A command: `claude -p "$(cat /tmp/eventmarketdb_judge_a_prompt.txt)" --model 'claude-opus-4-7[1m]' --effort max --no-session-persistence`. First attempt failed with `FailedToOpenSocket`; retry produced valid JSON but was launched before the unattended stable-output correction. The valid JSON was normalized into `/tmp/eventmarketdb_judge_a_output.json`.
- Judge B command: `claude -p "$(cat /tmp/eventmarketdb_judge_b_prompt.txt)" --model 'claude-opus-4-7[1m]' --effort max --no-session-persistence > /tmp/eventmarketdb_judge_b_output.json`. First sandbox attempt failed with `ConnectionRefused`; escalated stable command succeeded and produced valid JSON.
- Judge C: Codex subagent accepted.
- Judge D: Codex subagent rejected.
- Outcome: not converged. Non-nit findings synthesized into Round 2.

Round 2:

- Addressed Judge A must-fixes by adding verified audit promotion, all-neutral learner batch discipline, no bare retire, typed required/optional manifest writes, deterministic replay ordering, prediction-time bundle hashes, and source-PIT ranking.
- Addressed Judge B should-fixes by cutting separate completion JSON files, cutting `_render_priority`, collapsing `stale_neutral`, simplifying provenance to bool+reason, cutting dedicated source map, merging reports, making engagement-source compatibility explicit, and committing to refuse-and-skip invocation-time PIT.
- Addressed Judge D blockers by defining mandatory quarantine/backfill artifact schema and health/replay fail behavior for untraceable Q4-style rows.
- Judge A: first Round 2 output was malformed because it included a prose preface; stable A prompt was overwritten with the malformed warning and the exact stable command was rerun. Final A output is well-formed ACCEPT with should-fix findings.
- Judge B: well-formed ACCEPT with minimalism cuts.
- Judge C: well-formed ACCEPT.
- Judge D: well-formed REJECT on the active FCX Q4 corpus invariant because no production quarantine artifact exists and Q4 source artifacts are absent.
- Outcome: not converged. Round 2 findings synthesized into Round 3.

Round 3:

- Added refinement successor IDs, same-event lock, manifest/quarantine validators, replay cadence, intra-event order, learner audit-comment sentinels, explicit audit-key proof counting, renderer determinism tests, stamped PIT boundary event identity, and the Judge B cuts.
- Added an explicit design-time FCX Q4 provenance defect register in Section 5.8. Because the goal forbids creating production corpus files, this notebook is the current allowed provenance-defect marker; future implementation must materialize it in `provenance_quarantine.json` or restore Q4 artifacts before health passes.
- Judge A: well-formed ACCEPT with should-fix findings for persistent replay drift block, failed-unsealed recovery semantics, full-history misled guard, explicit tier priority, and lock ordering.
- Judge B: well-formed ACCEPT with minimalism cuts for learner summary counts, `_render_status`, provenance reason enum, and root-cause overlap.
- Judge C: well-formed ACCEPT.
- Judge D: well-formed REJECT because standalone `explicitly acknowledged` language remained as a bypass around validated quarantine/restoration.
- Outcome: not converged. Round 3 findings synthesized into Round 4.

Round 4:

- Removed standalone acknowledgment as an unblock path; only restored/hash-matched artifacts or a `validate_provenance_quarantine`-accepted entry can clear replay drift or let health/sealing proceed.
- Added persistent `.replay_drift_block.json`, failed-unsealed recovery semantics, full-history verified-misled guard, explicit tier priority, lock ordering, and Judge B minimalism cuts.
- Judge A: well-formed ACCEPT with should-fix findings for post-seal replay race, audit-level quarantine, renderer-version stamping, refinement forking, and nits for quarantine lifecycle/duplicate audit comments.
- Judge B: well-formed ACCEPT with minimalism cuts for render provenance reason, manifest optional writes, `learning_outcome=mixed`, redundant proven misled guard, free-text quarantine replay treatment, and engagement field enum.
- Judge C: well-formed ACCEPT.
- Judge D: well-formed ACCEPT.
- Outcome: not converged because A/B had unresolved non-nit should-fix findings. Round 4 findings synthesized into Round 5.

Round 5:

- Made replay check part of the manifest sealing critical section, then replaced `sealed_pending_replay` with single-write `sealed` or `failed_unsealed` manifest semantics.
- Added audit-level quarantine skip for tier/status, renderer version stamping and drift handling, refinement fork rejection, and the Round 4 Judge B minimization cuts.
- Judge A: well-formed ACCEPT with should-fix findings for cross-event refinement lock recheck, learner outcome compatibility, sealed-pending recovery, and quarantine lifecycle.
- Judge B: well-formed ACCEPT with nits only; the main micro-cut was removing `sealed_pending_replay`, plus optional free-text prediction/learner summary fields.
- Judge C: well-formed ACCEPT.
- Judge D: well-formed ACCEPT.
- Outcome: not converged because Judge A had unresolved non-nit should-fix findings. Round 5 findings synthesized into Round 6.

Round 6:

- Moved no-prior-refinement recheck inside the ticker/global write lock, tightened learner outcome compatibility, removed `sealed_pending_replay`, added append-only quarantine lifecycle, and removed optional free-text fields.
- Judge A: well-formed ACCEPT with should-fix findings for event-scoped replay, no-manifest recovery, drift-block validation, refinement-conflict recovery, renderer environment pinning, and storage row schema versions.
- Judge B: well-formed ACCEPT with minimization findings for prediction/learner summary fields and quarantine action values.
- Judge C: well-formed REJECT because `awaiting_human` could still count as deterministic quarantine coverage.
- Judge D: well-formed ACCEPT.
- Outcome: not converged. Round 6 findings synthesized into Round 7.

Round 7:

- Removed `awaiting_human` and `restored_artifacts_hash_match` quarantine actions, made event-scoped replay the in-lock seal check, added no-manifest recovery, validated drift-block history, pinned renderer environment into `renderer_version`, named storage row schemas, and cut prediction/learner summary fields.
- Judge A: well-formed REJECT with should-fix findings for concurrent `.replay_drift_block.json` append races and full-library replay seeing mid-event partial writes.
- Judge B: well-formed ACCEPT with nits only for internal `compute_status` ambiguity, drift-block chain justification, and renderer-version serialization format.
- Judge C: well-formed ACCEPT with nits only for bare-retire quarantine wording.
- Judge D: well-formed ACCEPT with nits only for candidate-manifest wording and active-only quarantine action semantics.
- Outcome: not converged. Round 7 findings synthesized into Round 8.

Round 8:

- Added replay-wide shared/exclusive lock semantics, drift-block flock/recovery semantics, candidate-manifest event replay wording, active-chain-head quarantine semantics, renderer-version canonical format with Python micro version, learner lesson-ID recomputation, cross-ticker refinement storage/lock ordering, and removal of the `compute_status` helper ambiguity.
- Judge A: well-formed REJECT with a should-fix finding for out-of-band deletion of `.replay_drift_block.json` silently clearing blocked sealing state.
- Judge B: well-formed ACCEPT with nits only for quarantine `superseded` status, drift-block chain minimality, and renderer-version future trimming.
- Judge C: well-formed REJECT because concurrent shared-lock event seals can permute persistent JSON array order relative to replay source order.
- Judge D: well-formed ACCEPT with nits only for drift-block preflight wording and lock-start wording.
- Outcome: not converged. Round 8 findings synthesized into Round 9.

Round 9:

- Added canonical persistent array sort keys and replay comparator canonicalization, made drift-block absence after any mutation manifest a `DRIFT_BLOCK_TAMPERING` refusal, stamped `drift_block_chain_head_hash` into manifests, added drift-block preflight before `learning/result.json`, and cut quarantine `superseded` status in favor of chain-head lineage.
- Judge A: well-formed ACCEPT with nit for inverse `parent_id`/refine-audit validation.
- Judge B: well-formed ACCEPT with nits only for transfer-key naming, manifest debug metadata, derived library paths, tier-window rationale, and optional quarantine notes.
- Judge C: well-formed ACCEPT with nits only for drift-block genesis, row-internal arrays, and drift-block preflight lock wording.
- Judge D: well-formed REJECT because full-library replay drift records appended after the latest mutation manifest need an independent head anchor to detect tail truncation.
- Outcome: not converged. Round 9 findings synthesized into Round 10.

Round 10:

- Added `.replay_drift_head.json` as the minimal head anchor updated under `.replay_drift_block.lock` on every drift-block append/clear, made first-seal genesis explicit, added parent/refine inverse validation, row-internal array canonicalization, drift-block preflight lock wording, tier-window rationale, and manifest/quarantine minimalism cuts.
- Judge A: well-formed ACCEPT with nits only for D22 collision error code, quarantine/refinement-chain wording, and predictor `--live` refusal for historical backfill.
- Judge B: well-formed ACCEPT with nits only for trimming `.replay_drift_head.json`, dropping unused manifest runtime metadata, and confirming parent/refine plus row-internal-array fixes.
- Judge C: well-formed ACCEPT with nits only for lock-order wording, quarantine action wording, and local-filesystem rollback residual risk.
- Judge D: well-formed ACCEPT with nits only for final head-capture wording and local-filesystem rollback residual risk.
- Outcome: converged. All four Round 10 judge roles returned well-formed ACCEPT verdicts with rubric A-J passing and no non-nit findings. Nits were incorporated in the final cleanup pass.

## 10. Final Reliability Check

Current answer to the final self-question:

Yes, complete for the design-validation goal. Round 10 passed four independent judge roles with well-formed ACCEPT verdicts, all rubric items A-J passing, and no non-nit findings. The final cleanup incorporated the accepted-judge nits without adding production code or corpus edits.

What Round 10 would guarantee if implemented and verified:

- No prediction can pass with a hidden all-sentinel lazy lesson skip.
- No learner can promote lessons through mass-neutral or low-evidence audit batches.
- Missing source artifacts become visible provenance defects and cap trust.
- Every sealed mutation points to source artifacts and a mutation manifest.
- Local replay can rebuild or flag library state from event artifacts and manifests in deterministic order.
- Full-library replay cannot observe mid-event partial writes, live array order cannot drift from replay source order, and drift-block history cannot fork, truncate, or be deleted to clear blocked state.
- Lesson visibility considers verified evidence quality before source recency.
- Global promotion requires transfer proof.
- Historical learner mutation cannot depend on current invocation time.
- Q4 FCX-style defects must be restored or quarantined before health passes.
- Current FCX Q4 is explicitly marked as a provenance defect in this notebook for the design-only phase; future production health still requires a materialized quarantine artifact or restored artifacts.

What it does not guarantee:

- It does not guarantee correct market calls.
- It does not guarantee an LLM's semantic engagement reason is truthful; it makes the reason inspectable, evidence-linked, and audit-targeted.
- It does not repair existing missing Q4 FCX artifacts by itself.
- It does not implement new data builders from data lessons.

Residual risks:

- Prompt-only semantic rules remain weaker than validators.
- Short hash IDs still need D22 and replay to defend against rare collision/corruption.
- Legacy rows need explicit classification during migration.
- Human review is still required to decide whether to restore or quarantine existing Q4 FCX defects.
- A coordinated rollback of both `.replay_drift_block.json` and `.replay_drift_head.json` to an older mutually consistent pair is outside what local JSON files can prove without an external anchor; the local design detects available-file tamper evidence and then requires exclusive full-library replay recovery.
