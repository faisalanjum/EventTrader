# STATUS_AND_HISTORY.md — the one mutable dashboard, supersession ledger, and crosswalk

> **Status: LIVE — consolidation Phases 1-5 EXECUTED (owner GO 2026-07-16); the definitive reader test's outcome, per-question grades, and tested hashes live in `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run15.md` — Phase 5 is COMPLETE ONLY IF that exact record shows 10/10 PASS. Review rounds + decision trail = the archived `CONSOLIDATION.md` §10.2/§16.** This file owns STATUS and HISTORY only — live rule
> wording stays in `FINAL_DESIGN.md`; procedures stay in `BUILD_AND_OPERATIONS.md`; channel duties stay in
> `ChannelContract.md`. Any status shown in another live file is a generated summary of THIS file. A status
> change edits this dashboard — and only if rule meaning changed through owner approval, the one owning rule
> section plus a new supersession row here.
>
> **Reading order (front door = `FINAL_DESIGN.md`):** FINAL_DESIGN → ChannelContract (adapters only) →
> BUILD_AND_OPERATIONS (builders/operators) → this file (what is open, replaced, or archived). Temporary fifth
> live file: `15_CandidateFactPacket.md` (owner-frozen v1.0 + the two 2026-07-15 owner amendments Q4/Q1-ext,
> current sha `aa7239ed…`).

## 1. Current handover — 2026-09-15

**Goal:** turn source reports into reusable business causes and exact,
source-backed facts. Models decide meaning; code checks evidence, numbers,
dates and identity. The production system is not finished or activated.

**Where we stopped:** Step 1, A7 (the fact-reading experiment, EXP-5). The
corrected calculation and bounded error review finished and were published,
but **A7 did not pass**. Grader uncertainty and genuine reader errors remain.
The later two-call diagnostic also finished; it did not change the official
score. The owner's latest boundary is **STOP AND WAIT after this documentation
consolidation**. Do not resume A7, A8 or later steps automatically.

This is the sole general handover. The [experiment board](../experiments/WORKORDER_STATUS.md)
keeps package states and historical receipts, not a second task narrative.
[Steps.md](LeftOverSteps/Steps.md) owns execution order; individual steps own
their detailed work. Dates and “next” instructions in older evidence describe
those past tasks, not today's authorization.

### 1.1 Where the work lives

| Location | Verified evidence base; not a claim that later documentation leaves HEAD unchanged |
|---|---|
| Main: `/home/faisal/EventMarketDB`, branch `main` | `2dc0ad39f30dba4756078573f5e80038465939cc`, tree `a45f8d0c2802e0d482ddefc5d330a4774d25a787` |
| Recovery: `/home/faisal/EventMarketDB-driver-recovery`, branch `recovery/a3-a7-verified` | Result commit `8dacb463406a48e0179f269e87e145d8c5823564`, tree `374ec3ca2a7f35b1844d3d285ea2f97ed533902e`; status follow-up `3340851ef2aa75817ff18b9beb73301b36370a39` |

Both branch tips above matched the actual remote on 2026-09-15 before this
consolidation. Recovery implementation/evidence is **not merged into main**.
Documentation synchronization is not an implementation merge or deployment.
Use `git rev-parse HEAD` and `git ls-remote origin refs/heads/main refs/heads/recovery/a3-a7-verified`
to establish newer tips; recovery has no configured upstream.

Below, **A7** means the recovery worktree's `a7_recovery/`; **U** means
`A7/unit_2020_codex_check/`. These evidence paths live on the recovery branch.
Its mapped runner preserves old logical paths; a `/tmp` name in a frozen map
does not mean the evidence should be moved back to temporary storage.

Protect unrelated local changes: main has changed settings, market-data
documentation, two old `receipts_827` inventories and deleted test-agent/skill
files. Recovery has an unrelated change in
`A7/grader_20260909/harness_g1v3/build_inventory_review.py`
(SHA256 `2ec3bd338f7dce181ff6794790cf634c6f68e73217daef88a25e365731ee4ed2`).
Both trees contain extensive untracked work. Never blanket-stage, clean,
reset or infer that every file belongs to this task.

### 1.2 Completed work and what its proof means

| Work | Delivered result / evidence |
|---|---|
| Earlier deterministic foundation | Core source binding, exact arithmetic, periods, IDs, validation, fusion and no-write planning; Fiscal fetch/relocation and slice-menu work. See §1.6 and the historical records below. This is not the production meaning reader or identity system. |
| V2 bridge and original exam kit | Published `0edb1be8` and `0dd71956`; staged, writes off. Original kit proof: 3,682 passed, zero failures/skips, 3,741 identities accounted; 58 read-only tests and one unrun write probe separately pinned. These are August snapshot results, not today's suite totals. |
| A1–A3 preparation and saved answers | Frozen independent reading/transport and durable recovery; A3 recovery checkpoint `26836bb309542163b7a1a0da480905e396d3668d`. Current evaluation preserves 382 original answers: 191 items in each of two runs, across 33 source events. No successful answer may be repeated merely to recover files or improve its score. |
| A4 key recovery | Original recovered package `90925920d5f2675191edfe5f1285c239177ca453`. That older draft-fed key is historical, not the blind key used for the later saved-answer evaluation. |
| A5 / A6 preparation | Recovered and published at `38e42d9a43d2ec1a9cf69e5c01b0c3a1af5010c3` / `cc7df9f41206c22604fa3736f4c97d120ee74dbc`. Later evaluation reuses answers under their actual original instructions, not unserved prompt clarifications. |
| New independent source-only key | Signed current key: `U/codex_lock2149_a/SIGNED_KEY.json`, SHA256 `4474bd7a330a0cb5c03aef09883053ce34d138bfd43ff4046671580b65591ee4`. 33 events, 191 rows, 165 expected facts, 34 controls, 10 exclusions, 44 abstentions; no open signing issues or exact duplicate key facts. These are different counts, not quantities to sum. |
| Grader and real connection | Existing raw capture, parser, source normalizer, matching, independent judgments, real Core no-write route and scorer connected. Exact current chain: `U/FINAL_SCORE_COMMAND_2174.sh` and `map_final_grading_2174.tsv`. No second scoring system or production import of experiment code. |
| Final A7 calculation and bounded cause review | Published result/cause/reuse package `8dacb463`; 99 no-write event routes, four completion loads, zero new model calls in the final calculation. Detailed results below. |
| Later selected-case diagnostic | Two fresh Sonnet readings of one Best Buy impairment target; [result and evidence](/home/faisal/EventMarketDB-driver-recovery/a7_recovery/manual_probe_20260915/RESULT.md), recovery commit `c8188c5c6c6fd8c926526dda47f2095104115595` (26 files, 848,873 bytes). Separate from the 382 answers and official grades. |

The independent key's lock is
`68270f4fd33f342e1b562dd700f789fb442fa0b4bbb1ec2b8cd83a6c1cb19737`;
its receipt is
`a54b8db1546c639801f60a7655e4eb6e867a3144a5ed88d6734288e98bd4671a`.
The saved producer receipt is
`8760b52712ac233826e98486dce043f86ae007ffaa373504ac8f761a2bc7fd0e`,
finalization
`2f15d98ffafe6b1b193fdb57e4b04de1158534499c126d4cc3dad495809c832f`.
The older “82 launched” / “206 lanes” counts are historical schedules, not the
denominator of this final evaluation.

### 1.3 Actual A7 result — finished calculation, not qualification

Official report: `U/codex_final_score2174_a/A7_CORRECTED_SCORE.json`,
SHA256 `966d14bc71ee487afdeff88a41fbf59ccf0e68c349a342c96a60aa0ff733a062`.

| Measure | First run (P1) | Second run (P2) | Strict combined result (UNION) |
|---|---:|---:|---:|
| Expected facts matched | 123/165 (74.55%) | 116/165 (70.30%) | 71/165 (43.03%) |
| Raw value/shape measure | 87.54% | 86.95% | 90.84% |
| State measure | 94.87% | 95.54% | 98.53% |
| Wrong-accept flags from scorer | 9 | 9 | 8 |
| Incomplete meaning judgments | 48 | 38 | 18 |
| Raw `key_miss` labels | 4 | 11 | 84 |
| PASS / safety result | false / FAIL | false / FAIL | false / FAIL |

**A match is not a fully correct answer.** In P2, the 116 matches include
100 facts the code would accept, 13 held for dates and three rejected for
units. Some mechanically accepted facts still have meaning errors. The strict
combined result follows its frozen agreement/matching rules; it is not a
simple union of the two match counts. None of these columns is an overall
“percentage correct” or a production accuracy claim.

All 426 required grading questions are accounted for: 388 unaffected outcomes
unchanged, 24 selected outcomes changed and 14 selected outcomes unchanged.
The 104 incomplete meaning judgments remain uncredited where unresolved;
they are not 104 missing calls or permission to reroll valid disagreements.
All three reports say `required_grading_unfinished=true`.

Read [FINAL_SCORE_FINDINGS_2174.md](/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2020_codex_check/FINAL_SCORE_FINDINGS_2174.md),
then its linked cause/addendum records for exact event/fact/field evidence.
The bounded source review supports defects in 23 of 26 flagged records; three
flags remain unconfirmed. Examples of genuine reader errors include omitted
Best Buy Health scope and omitted pre-tax measurement. Grader false-positive
leads, vague-quantity/range interpretation and a Boeing-option stage question
remain explicitly qualified. Many raw `key_miss` labels are contradicted by
existing reference cards; they are not proved missing-key facts. No qualified
replacement judgment was invented to improve the score.

The later two-call diagnostic restored Health scope in both replies. One
still duplicated the charge and omitted required start dates; the other would
pass code checks. Both interpreted a printed dash as prior zero, which the
served instructions did not conclusively settle. No source-context loss was
found. This selected known case is not an unseen test, A7 PASS or authority
to replace the original answers.

### 1.4 Verification, remaining limits and model reuse

The published final package records **318 tests plus 29 subtests passed**
(3.34 s), including 15 offline model-reuse checks. The reporting fix first
failed seven tests with two passing controls, then passed nine focused tests
and four executed reversion mutations. Exact commands/results:
`U/FINAL_REGRESSION_COMMAND_2176.sh`, `OFFLINE_VERIFICATION_2176.json`,
`FINAL_CHECKPOINT_REVIEW_2176.md`. Numeric replay
`FINAL_SCORE_TRACE_2174.json` reproduces 310 matched pairs and 16 measures
per run; it does not independently decide meaning.

[MODEL_REUSE_OFFLINE_REVIEW_2176.md](/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2020_codex_check/MODEL_REUSE_OFFLINE_REVIEW_2176.md)
proves the same grader/parser/no-write route works with unfamiliar supported
offline input. **Changing only a local model name is not yet a verified launch.**
The separate host-side task still needs exact prompt-capacity proof, actual
returned model/completion capture and honest attempt/resume receipts. No local
model was run and no inference engine/client was changed. Follow the current
`LeftOverSteps/QwenInference.md`; the older Qwen handoff is historical where
that document supersedes it. Evidence copies are in `U/snapshots_2176/`.

Keep the grader as an external evaluation tool. Production must not import
experiment-harness code. Later Step 3 moves the approved prompt/response
responsibility to production ownership; this does not require turning the
entire test harness into production software.

No current database census is claimed by this update. The September 7 audit
reported Driver/DriverUpdate/DriverPeriod = 0/0/0 and old Guidance =
548/8,432/237; those are dated observations, not present-day guarantees.
The live adapter still refuses transactions. No database write or activation
was performed by this work.

### 1.5 Remaining roadmap — all advancement currently paused

| Step / part | Actual position and remaining result |
|---|---|
| 0 | Starting roadmap/status published in August; historical starting identity is not today's HEAD. This update is routine status maintenance, not a new Step 0 or Step 13. |
| 1 A7 | Calculation/cause package delivered; FAIL with the limits above. Further corrections or a changed test require a new bounded owner-directed task; reuse valid saved evidence. |
| 1 A8 | Not run: EXP-6 text/tagged-fact identity comparison requires EXP-5 PASS. |
| 1 B1–B7 | Catalog/identity lane unfinished. B1 was parked for A7 priority (Codex archive 1445); NAME-16 finding remains a lead in step7. B2 catalog run, B3 type key/stamping, B4 mini-catalog freeze, B5 routing key, B6 routing experiment, B7A pair-key and B7B identity experiment remain unsigned/open. |
| 2 | No final signed build decision for both Step 1 lanes. Reconcile results, rules, model roles and allowed build scope only after its entry conditions. |
| 3 | Shared production meaning reader not completed; experimental saved/raw-response paths do not close it. |
| 4 | Production admission/reuse/create, type/family, links, continuity and recovery not completed. |
| 5 | Full V2 production reader + identity no-write proof not completed; close the named validation-door/fusion ordering requirement here. |
| 6 | V1 remains active; atomic V2 promotion, caller migration and V1 removal not done. |
| 7 | Production catalog/finalizer, safety and fitness qualification not completed. |
| 8 | Remaining fact wiring, concept links, reads, withdrawals, verdict/DCM plans and dual-producer calibration not completed. |
| 9A / 9B | Fiscal source-location certification unfinished; 150 real-anchor tagged-filing test waits for Step 11's lawful first records. Do not restore the withdrawn certification artifacts. |
| 10 | Minimum operating layer not completed; design may overlap only where Steps permits; implementation waits for 8 and 9A. |
| 11 | Shadow, separately approved bounded graph setup/write, 9B and controlled rollout not completed. |
| 12A / 12B / 12C | Consumer/Guidance retirement not done; 12B first-release channel set is owner-frozen empty, not an open charter task; native tagged-filing production/rollout remains last and gated. |
| 13 | Whole-system closure not reached. |
| 14 | Dormant; never a prerequisite to Step 13. |

The exact dependency graph and approvals remain in [Steps.md](LeftOverSteps/Steps.md).
The starting publications are `c8f228802` (roadmap) and `929d6ed05` (status).
Do not estimate overall completion from file counts, capability counts or
expired hourly estimates. First-release rulings already defer cross-company
slice comparison, non-USD support, item-number taxonomy and third-party
guidance; do not re-request those settled choices. Other choices are raised
only at their frozen trigger.

### 1.6 Preserved audit findings and history

The September 7 report's useful implementation map is retained here:
`driver/core/driver_write_cli.py` owns event dispatch; prepared-fact modules
own schemas; period/unit/ID/fusion/validator/writer modules own deterministic
mechanics; `driver_neo4j_adapter.py` is the fenced Report-only graph adapter.
Fiscal owns source finding/copying, not meaning or Driver identity. Legacy
known-value relocation and source-neutral tagged relocation have different
protected callers. Catalog tools remain under `.claude/plans/Drivers/workflows/`.

Arithmetic fixes `8255d4dc80988ce8490078cbbfa5f7f435817239` on main and
`c60defaa9a8f678b506cabe449c60a96fbca47cb` on recovery preserve exact
negative numbers and guidance midpoint comparisons. They are separate from
the A7 grader. The September 7 audit recorded 4,454 passes, one failure and
one skip across its scoped runs; those were not a whole-system pass.
Its 7 packet artifacts / 136 event occurrences / 743 items were not 743
source-code files or unique events. Its 31 capability groups were a component
inventory, not an effort percentage.

The August test-collection database read was real and was fixed in test
fixtures; the earlier denial was withdrawn. The source-routing owner was
not replaced. Preserve that correction when interpreting old green tests.

Remaining audit leads, not new tasks: same-fact replay/member-edge enrichment
requires source-rule adjudication if reached; current catalog tools must be
reconciled to the later count-free independent-identity-review ruling; V2
production ownership and operating policy close at their existing steps.
The older report's unconfirmed owner-approval questions do not override
recorded rulings in Steps. Withdrawn suspicions stay withdrawn unless new
evidence shows a regression.

Before this documentation edit, the applicable main checks produced
201 passes and three failures: the old generated patch differs from its
builder; its enclosing clean-proof test therefore also fails; the old pin
inventory differs from its generator. These are recorded pre-existing
baseline findings, not three new runtime defects. Do not silently regenerate
frozen proof or claim today's full suite is green.

Consolidation checks: 84 documentation/contract tests passed; the full affected
A7 regression passed 318 tests plus 29 subtests. The larger main check repeated
201 passes and the same three baseline failures. The old A7 command correctly
refuses changed documentation hashes; the fresh check used a separate map
with only the reviewed document-directory digest changed. Historical maps
remain immutable and require their original snapshot for reproduction.

The following preserved sections keep the original rule decisions and
33-source crosswalk. Their dated test counts and historical “next” wording
do not supersede this checkpoint. The September 7 audit and final A7 work
diary are recoverable in Git as specified in §8; raw evidence was not deleted.

### 1.7 Safe resumption

Read `AGENTS.md`, the Fiscal/Core guardrails, the live design and relevant
step, this checkpoint, then [Orchestration.md](LeftOverSteps/Orchestration.md)
before coordinating Core. Use that protocol, not copied chat instructions.
The old untracked `CoreSessionPrompt.md` is an August one-use handover, not
the current task or replacement-session prompt.
The current documented pair is Codex
`01a05829-3086-73e0-89c9-e5773b322d80` and Core
`5ae9b86b-f0f6-4449-beee-9cac7cfa7200`; verify rather than assume they persist.

Last reviewed exchange: Core 2174 replies to Codex 2178 and waits.
Their SHA256 values are respectively
`b8299efd8ac7cb288dfb8148ab11ea1e635b7f2b7c3ba984f76d69d02c8cf9f5`
and `b358056226b847887b1e580af4b7d8c9dc78291003780b200e51e4860d3f3d04`.
Current mailboxes matched their archives. Re-read both: downtime events are
not replayed. A replacement session must complete the protocol's handover;
ordinary compaction is not replacement. Reuse the single proven watcher and
existing goal; never reset sequences or send an acknowledgement of an
acknowledgement. The old all-steps goal is not achieved.

No model calls, Core task or roadmap advancement follows from opening this
file. The next action after this consolidation is to report the documented
state and wait for the owner. Any later authorized correction must preserve
original answers, full denominators, exact evidence and every miss/refusal.
Models decide meaning; code does deterministic work. Fix only reproduced
test defects at their one owner; do not tune measured reader errors into a
pass. Real writes, activation and destructive work retain their own approvals.

## 2. Lists by status

These are the preserved design-status categories. The September 15 execution
checkpoint above and later owner rulings in Steps.md supersede old open-item
or build-progress wording; they do not erase the historical rule record.

- THIS file owns the status lists (one-copy law); `FINAL_DESIGN.md` §10 is the GENERATED mirror. The master lists:
- **FINAL / BUILD-PENDING:** Track A remainder (fold/tree mirrors, finalizer, real folds, WP-FC-RUN, OD-6 fitness gate — never run) · UNIT-14 production wiring · PER-20 HAS_XBRL producer guard · full slice TABLE materialization (materializer-era; the step-7 PIT menu code IS built) · concept-linker vetoes C/D + PIT query build · Track B remainder (the internal writer/validators/fusion/CLI/audit + step-7 slice menu are BUILT `0d6c1d0`, dry-run only — remaining: S4 decomposer/kernel integration + public channel runtime, FS-18 step-7 menu-for-producers, write enablement behind the fitness gate) · read layer · verdict/DCM writer · channel adapters + certification · Track C execution · incremental refresh.
- **DESIGN-INCOMPLETE:** the production running layer (BUILD §7's runbook list). The OD-5 change scanner is a recommendation only.
- **CONDITIONAL:** OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · XBRL-native materializer + `09` rider (RATIFIED as design 2026-07-15; DORMANT until the P19 enablement proof plan — X-XL0-3 bars — every hard pre-gate pass, and the EXP-6 convergence evidence) · multi-run concept stability/caching (only if monitoring justifies).
- **OPEN (owner):** catalog 796-vs-786 + lifecycle/IPO · full model/cost policy beyond signed EXP-2 · FS-23 · 8-K item/content taxonomy only (earnings 8-K pairing is CLOSED by PER-21) · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement (part-2/news-channel) · **Driver financial classification (owner 2026-07-19): NO field approved — for now derive exact facts (company-specific XBRL linkage, monetary units); revisit before production Driver creation ONLY if a named consumer and a testable definition exist; otherwise the field stays absent.**
- **APPROVED WORKING DESIGN (owner 2026-07-15; not activated; gates/OFF-switches in force):** Admission Kernel v3.4 · XBRL-native materializer — integration COMPLETE (INT-2..INT-5, destination proof §7.1b); both originals archived 2026-07-15, byte-verified vs the Phase-1 manifest. The kernel bundle also settled two formerly-open/tracked items: G1 reuse-display rules (→ BUILD §8.1.3) · OD-7's born-complete/live-create CORE (→ BUILD §8.1; the broader OD-7 design stays UNRATIFIED — FINAL §4.2 Q5 note; the mis-name/mis-type exit + exact recipes land at the future OD-7 pass, BUILD §11.2).
- **CANDIDATE:** Bayes proposal · Driver Genesis restructure (rationale). Owner-question decision record = §4 below; the full decision text + verification trail = the archived `CONSOLIDATION.md` §10.2/§16 (`archive/2026-07-15_pre-consolidation/`).
- **Change law (owner 2026-07-15):** every future design correction updates the ONE owning live section and adds a short history entry here; no parallel live copies.
- **RETIRED (never a production path):** old Guidance replay plan (`13_Track_RetiredDesign.md` — GI stale-trap
  rows in its GI-07) · fixed-vocabulary Driver v1 · eager-reuse v2 · `slice=total` · alias layers · `long_range`
  scope value · `gp_UNDEF` quiet fallback · `evhash16` on DriverUpdate · FS-22 cross-company recurrence ·
  RavenPack import · catalog-first live reuse · SDK/OAuth metered concept invocation · OD-16 materialize-all
  catalog sync (owner ruling 2026-07-15, Q3).

## 3. The 43 supersession rows (terse; dead rule kept once for audit; current wording ONLY at the anchor)

| # | Subject | Dead rule | Current anchor (FINAL_DESIGN unless noted) |
|---:|---|---|---|
| 1 | Own company parts | brand/segment in the name | §3 NAME-10/11 |
| 2 | Measurement | adjusted/diluted in the name | §3 NAME-14 · §5.3 |
| 3 | Per-X | omit denominator / treat as unit | §3 NAME-13 · §6.1 |
| 4 | What makes an update | only a change qualifies | §1 · §4.2 |
| 5 | Evidence count | require >2 events | §4.2 |
| 6 | Verdict size | `magnitude` | §7.3 |
| 7 | Verdict allocation | shares must total 100% | §7.3 |
| 8 | Verdict storage | verdict node/property | §7.3 (edge) |
| 9 | Related flavors | no family link / merge as synonyms | §4.1 |
| 10 | Period model | guidance-only period | §6.2 |
| 11 | Slice kinds | 4 kinds + `store_type` | §5.2 |
| 12 | Slice identity | XBRL member ID | §5.1/§5.2/§8 |
| 13 | Concept linking | curated dictionary | §8 |
| 14 | RavenPack | Driver vocabulary | §4.3 (DU-11 context) |
| 15 | Model default | Fable two-pass reader | signed EXP-2 (BUILD §9) |
| 16 | Number shapes | stored `level_bound`; low-only point | §7.1 |
| 17 | Qualitative value | no qualitative field | §7.1 `value_text` |
| 18 | Fact hash | DriverUpdate `evhash16` | §5.1 · §7.3 |
| 19 | Confirmation | confirmation enum | §7.1 `company_confirmed` |
| 20 | Non-GAAP guard | name regex primary | §8 XC-05 (measurement set) |
| 21 | Live reuse | show catalog first | BUILD §4 (propose-first) |
| 22 | Concept invocation | SDK/OAuth metered | §8 (subscription only) |
| 23 | Missing period | quiet `gp_UNDEF` | §6.2 sentinels |
| 24 | Metric expectation | previous-guidance baseline on metric | §7.2 matrix |
| 25 | Whole-company slice | store `slice=total` | §5.1/§5.2 |
| 26 | Unit hints | one hint pair per item | §6.1 per-slot |
| 27 | Slice label drift | human alias files / confident alias | §5.2 · §9 |
| 28 | Slice menu | latest prior filing only | §5.2 union menu |
| 29 | Bare fact type | trust one classifier | §4.1 OD-2 |
| 30 | Collision hash | quote/value truncated hash | §5.1 OD-8 |
| 31 | Surprise arithmetic | above=beat, sign hard-fail | §4.3 · §7.1 (OD-13) |
| 32 | Loss values | positive loss magnitude / loss Drivers | §6.1 OD-12 |
| 33 | Sequential percent | all growth = YoY | §6.1 OD-11 |
| 34 | Guidance chronology: movement, amendments, withdrawal fan-out, Event/DCM overlap | movement stored from the write-time prior view; creation-only DCM single-target; open amendment handling | §9 + §7.3 |
| 35 | Measurement tokens | producer-final tokens; droppable | §5.3 OD-9 |
| 36 | Unit grouping | read-time family map / absorption | §6.1 OD-10 · §9 |
| 37 | Slice recurrence | cross-company recurrence identity | §5.2 (FS-22 retired) |
| 38 | Brand/slice test | external-brand heuristic | §3 NAME-11 |
| 39 | Wrong `SAME_AS` | never reopen automatically | §5.4 recovery |
| 40 | Entity names | ban every entity token | §3 NAME-11/16 carve-out |
| 41 | Token subset | permanent automatic refusal | §5.4 OD-19 (conditional) |
| 42 | Surprise scope | actual-only; no subtype slot | §5.1 OD-21 |
| 43 | FS-20 self-heal | automatic activity-based demotion ("auto-demote, no human") | §5.2 FS-20 (offline-only governed correction — R12) |

**Additions that are not reversals (each anchored in FINAL_DESIGN):** born-complete + latent-base exception
(§4.2) · OD-1 suffix admission (§4.1) · OD-2 metric-proof + first-fact pin scoped to bare names (§4.1/§4.2) ·
OD-3 blind local role test (§3 NAME-11) · OD-4 = FS-22 retirement, no slice-value recurrence rule (§5.2, row 37) ·
OD-5 scanner recommendation (BUILD §7) · OD-6 fitness gate (BUILD §4) · OD-7 live admission = its
born-complete/live-create CORE is ratified inside Admission Kernel v3.4 (owner 2026-07-15, NOT activated —
BUILD §8.1); the BROADER OD-7 design stays UNRATIFIED (FINAL §4.2 Q5 note) — the mis-name/mis-type exit after
facts exist + the exact born-complete/lazy-create recipes land at the future OD-7/live-admission pass (BUILD
§11.2) · OD-8 (§5.1) · OD-9 (§5.3) · OD-10 (§6.1/§9) · OD-11 (§6.1) · OD-12 (§6.1) · OD-13
(§4.3/§7.1) · OD-14 (§9) · OD-15 = near-synonym live races accepted as normal over-splits, no new locking (§4.2) ·
OD-16 resolved 2026-07-15 → lazy born-complete (§4.2) · OD-17 (§3) · OD-18 (§5.4; CLAIM separate, ships off) ·
OD-19 (§5.4) · OD-20 (§5.4) · OD-21 (§5.1/§6.2/§7) · K2 = fold repair stays per-pair, batched fold repair
deferred (BUILD §4) · frozen packet v1.0 + Channel Contract v1.0 (boundary files) · Track C full no-replay
reversal (BUILD §6).

## 4. Owner rulings record (through 2026-08-12)

> Owner rulings made after that date are recorded in
> `LeftOverSteps/Steps.md`, not here; this section is not a complete record of
> them.

Q1 `company_confirmed`: CORE derives from who-said-it evidence; unclear = SKIP (ruling's own content); `false`
stays reserved for explicitly-ALLOWED future third-party classes (enabling any class = part-2/news-channel
decision) → FINAL_DESIGN §7.1. · Q2 non-slice/elimination: NO change — frozen packet PARK+log stands; FS-20
auto-demotion is the drain → §3 OD-17. · Q3 catalog sync: resolution (b) — offline catalog + lazy born-complete
nodes (created in the same write when an ATTACH targets a card with no node yet — mechanics TO BE specified at
the future OD-7/live-admission pass, recipe not yet written, BUILD §11.2); OD-16 narrowed → §4.2. · Q4 XBRL packet shape: amendment APPLIED 2026-07-15 to ChannelContract + frozen
packet (`dimensions=[]` verified-empty; both axis+member; never fragments). · Q5 first-fact guard scoped to
bare names; suffix-proven lanes may be born `unknown` → §4.2. · R6 (round 16) `xbrl_internal_conflict` retry
trigger: retry ONLY when the affected report's parsed XBRL facts actually change; an amended filing is a NEW
report, never a silent rewrite → BUILD §8.2 recipe step 4. · R7 (2026-07-16) official reader-test Q3 amended:
"For each surprise, construct its required same-event home fact, state the home's driver_state, and show the
required family, period, period scope, slice, measurement, and normalized value/unit match." — supersedes the
archived CONSOLIDATION §14.3 item-3 text; design files and preamble otherwise unchanged. · R8 (2026-07-16, final closure + standing reader-test policy): (a) the proposed "hash only the three law files" rule is REJECTED — every reader test pins EVERY file it reads (BUILD and STATUS carry essential design mechanics and decisions); (b) routine build/status progress updates do NOT require a full reader-test rerun; changes to rules, contracts, operative mechanics, gates, owner decisions, crosswalks, or major release handoffs DO; (c) final closure = ONE fresh R7-amended reader test against ONE committed seven-file freeze — 10/10 + 7/7 exact hashes + explicit command-exit checks required, the record added AFTER the test without changing the seven tested files, the freeze-commit SHA recorded in the definitive record — then the documentation track RETIRES (run 14's record preserved as qualified historical evidence). Full decision text + verification trail:
the archived `CONSOLIDATION.md` §10.2/§16 (`archive/2026-07-15_pre-consolidation/CONSOLIDATION.md`, archived at Phase-5 step 7, 2026-07-16).
· **R9 (2026-07-17) FS-18 kind-scoping ruling:** the fold equality is WITHIN one company on the complete
`kind:norm(value)` token only; equal values under different kinds (incl. `unknown`) never fold or share a
member link; member-label normalization = the shared format-only normalizer, never stemming/suffix-stripping →
FINAL_DESIGN §5.2 FS-18. Basis: third-bot DB finding, independently reproduced + corrected by the core bot
(real exact-collision population: `international` 5 cos · `corporateandother` 4 · `other` 3 · `corporate`/`us`
2, same label on both geo+segment axes at one company; suffix-stripped collisions americas 21 / northamerica
19 / europe 11 / emea 10 are NOT at risk — stripping was already unlawful, archived 03 "no stemming"); the
archived original FS-18 was equally silent (under-spec closure, NOT a reversal — supersession row 12 not
reopened; FS-15 "kind never reconsidered" + the unknown-axis sentinel already pointed within-kind). A
CLARIFICATION, not a meaning change → no supersession row. Five pinned test cases land with the S3 step-7
menu/dedupe build (same-kind fold · cross-kind separate · unknown-vs-known separate · Europe≠EuropeSegment ·
same member on different axes = separate exact axis/member links). No migration; no production code today.
· **R10 (2026-07-17) THE S3.5 INTERNAL WRITER CONTRACT LOCKED (v3.6):** operative text = BUILD §11.4 item 4.
Converged through the owner's zero-based simplification (the CLI is INTERNAL until the decomposer/kernel —
the entire public channel runtime is ONE deferral to S4; ChannelContract v1.0 stays ACTIVE law, only its
software connection deferred) + five reviewer passes, every accepted point independently reproduced. Key
pins: PreparedFactV1 anchored to packet sha `aa7239ed…` Block 2 (schema review = the remaining gate before
the internal portion CLOSES; §11.4 stays PERMANENTLY PARTIAL until S4 regardless) · fusion fills nulls only,
ten-signature-slot disagreement prevents fusion, unfused → the full OD-8 ladder with no hashing promise,
permutation-identical · whole-event non-retried tx w/ in-tx recheck+reads+final-plan, flock single-writer ·
truthful outcomes (rollback reports zero written; REJECT beats PARK; date=source time, created=commit time) ·
write-ahead audit file prepared→committed/failed/dry_run = the interim park ledger · SOURCE_COMPANY_AMBIGUOUS
via the ownership relationship only · MEMBER_LINK_DEFERRED pre-plan until step 7. CLI build authorized.
· **R11 (2026-07-17) INTERIM period-scope labeling — explicitly NOT P14; P14 stays DORMANT:** a period
audit reproduced the exact-date branch labeling the same window `exact_range` while the SEC path said
`quarter` (breaks the OD-21 surprise↔home scope match; `period_scope` is in the §9 read-series key). The
ratified cure (the BUILD §8.2 **P14** date-anchored classifier + instant `period_scope=null`) is DORMANT
until the XBRL materializer enables — so the owner ruled an INTERIM fix in `driver_period_resolver.py`:
scope labeled from the item's own declared fields via ONE mapping (fq→quarter · half→half · month→monthly ·
long_range→exact_range · fy→annual · none→exact_range; declared ytd/ttm wins) — paths converge when fiscal
framing is supplied; frameless exact dates honestly stay exact_range — plus ONE strict period-shape check
on every path: conflicting/mixed/out-of-range fields, sentinel+dated/fiscal combos, incomplete long-range
(start-only; end-only = the proven "by 2030" shape, legal), and invalid dates all PARK, never crash; zero
values are validated (is-not-None), never treated as absent. A declared label contradicting the window
length PARKS; bands sized so the KNOWN TESTED calendars pass (52/53-wk, 4-4-5, KR 16-wk Q1 = 112d, COST
84d/119d, full-year Q4-YTD 365/371d, January-to-date ytd — no ytd minimum). Instants keep live-law scope
until the dormant bundle flips coordinated with the validators. At materializer enablement P14 replaces
ONLY the temporary labels/bands — the basic input validation is permanent.
· **R12 (2026-07-17) FS-20 lists APPROVED as code + automatic demotion SUPERSEDED:** the owner approved
the frozen slice-axis lists in `driver/core/slice_axis_frozen.py` — 12 hand-vetted pure hard-exclude
eliminations · 79 provisional members · exactly 7 proven non-slice axes; every unreviewed axis takes the
unknown→provisional sentinel path (the a:EndMarketsAxis lesson: 246 real Agilent end-market facts sat in
a censused "non-slice complement", which is deleted and banned); unseen elimination names are never
pre-frozen. The catalog's "self-heal: auto-demote, no human" line is SUPERSEDED: occurrence counts never
auto-demote; the structured exclusion logs are evidence for a governed OFFLINE update that simply moves a
proven-mistake qname from hard-exclude to provisional. Same ruling batch: XBRL member links verify
FACT-LEVEL (concept + time_type + exact dates + COMPLETE dimension set, `[]` included, entity-scoped,
numeric non-nil, misaligned context arrays fail closed; stored ends exclusive per the 2026-07-09 decode);
fusion never combines two different complete dimension sets (identical sets fold, None inherits, anything
else parks — a union would fabricate a set no real XBRL fact carries); the step-7 slice menu replaced the
`MEMBER_LINK_DEFERRED` fence with `MEMBER_LINK_INVALID` (§11.4 amended).
· **2026-07-16 (S3 GO):** owner approved the S3.1 cross-channel ID law — 7 decisions one-by-one (reject-not-
escape · 4-segment id w/ trailing colon on empty scope · `[A-Za-z0-9._-]` source charset case-preserved ·
readable-date `gp_` ids · the one text normalizer w/ park-on-empty · the one decimal canonicalizer · text-based
10-slot sha256 fingerprint) → BUILD §5 ID-shape entry; BUILD §11.3 closed; operative law =
`driver/core/driver_ids.py` + its frozen vector suite. Owner also blessed the build sequence (S3 writer stack →
S4 kernel day-1 + pilot → enrichment); ratification-vs-authorization wording never blocks the agreed sequence.
· **R13 (2026-07-18) earnings 8-K period authority CLOSED:** the owner locked exactly two files for earnings
8-K routing. Historical/backfill exact periodic-accession pairing belongs to
`.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`, with `quarter_identity.py` used only
as an `AUTO_OK` trust gate; its fiscal label/projected dates do not join historical documents. Live, before
the target periodic filing exists, belongs to `scripts/earnings/quarter_identity.py` alone. Missing or
ambiguous evidence parks. Any third/copied fiscal-label, projected-date, or filing-sequence matcher is
superseded and forbidden. This source-routing decision is distinct from Driver fact-window resolution
(FINAL_DESIGN PER-21; procedure = BUILD §3). The frozen packet stays byte-identical at `aa7239ed…`: its
"shared resolver is the sole period authority" phrase means the fact's own window only, never 8-K source
pairing. Per the standing R8 policy the recheck remains OWED: the 2026-07-22 first run's PASS was WITHDRAWN
on regrade (one exercise failed under the locked no-rescue rule; detail =
`archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-22_R8-PER21_CORRECTION.md`; the original
record is preserved unedited beside it). A fresh blank-context rerun is prepared; this obligation is
DISCHARGED only if `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-22_R8-PER21-run2.md`
records PASS 10/10 with 7/7 unchanged pins at the commit carrying this sentence.

**2026-08-11 — per-X naming form (NAME-13): UNIFORM SPELL-OUT.** The owner ruled the naming-form
deferral of 2026-07-25. Both deferred rules are REMOVED from live law: the sole `eps` canonical-name
exception, and the open-class "familiar acronyms" sentence that let any acronym already carrying its
denominator keep the short form. (Neither rule is reproduced here: the residue guard requires this
file to be free of the retired wording, so it is described, never quoted.) Every stated
business/physical per-X denominator is now
written out in the canonical Driver name; the families are `earnings_per_share` /
`_guidance` / `_surprise`, and `dps` resolves to `dividend_per_share`. An acronym whose expansion
cannot be verified is NOT coined and NOT guessed — the reader skips, and a name↔per_x conflict parks
at admission (ONE owning component; no interim validator was added). Source quotes are NEVER
rewritten; `per_x` stays the fact-level signal; the stored unit stays base (`usd`);
adjusted/basic/diluted stay in measurement (NAME-14 unchanged). Per-X ONLY — NAME-07 familiar
market/policy names and NAME-08 whole phrases (`ebitda`, `fcf`, `fed_rate`, `cogs`, `rpo`) are
untouched. The NAME-13 deferral note is superseded and its ⏸ markers are deleted from FINAL_DESIGN
§3/§10 and the three live prompt rulebooks. Evidence: `experiments/WORKORDER_STATUS.md` 2026-07-25
pack · EXP-2C 40-chunk replay (zero eps forms emitted, correct spell-out, quotes verbatim) · EXP-2D
acronym probe (zero acronyms kept as names, unverifiable acronym skipped, ARPA-agency trap passed).
Guard: `workflows/tests/test_perx_naming_residue.py`. STILL OPEN and deliberately NOT in this batch:
the EXP-5 item-contract regeneration (`exp5_item_contract.md:127` still serves the old sentence) and
the launch-manifest re-pin. CORRECTED 2026-08-11 (reviewer SEQ 957/959): these do NOT belong to the
Core contract-freeze step. The 2026-08-11 conclusion that the whole bundle was
switch-gated is **SUPERSEDED by the 2026-08-12 owner ruling below**. K-fields
GO#1 was gated on the complete bundle being regenerated, hash-frozen and proved
against the committed staged-V2 dry-run bridge. **That condition was satisfied
on 2026-08-13 (`0dd71956`), and GO#1 is still UNFIRED.** The bundle was the
TECHNICAL PREREQUISITE, not the authorization: satisfying it did not by itself
start any call. **SUPERSEDED 2026-08-14** — this entry ended by keeping GO#1
owner-gated pending fresh approval at the moment of the run. The `Steps.md`
owner ruling pre-authorizes every model call already bounded by a reviewed step,
so GO#1 now waits on Step 1 freezing its exact bounded plan and pinning Sonnet 5
at high effort, not on a further owner approval.

**2026-08-11 — STAGED CORE V2 PUBLIC CHANNEL CONTRACT FROZEN (not live).**
`FinalDesign/ChannelContractV2.md` sha256 `d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b`.
The separately versioned V2 PUBLIC contract governing every channel; Fiscal is the first
staged consumer. It publishes the full three-stage flow: Stage A the CHANNEL RAW EVENT
(envelope, text_parts supplied once, raw items, the XBRL bundle, and the four RETIRED
Fiscal-authored fields that are never accepted or defaulted); Stage B reader/Core
preparation; Stage C outcomes. DIMENSIONS ARE TWO STAGES, never one: the PUBLIC raw
`xbrl.dimensions` entry is exactly {axis, member} and the channel never invents
`slice_part`; only the INTERNAL `member_refs` triple carries it, derived by Core. The
Stage-A raw fields are NOT mechanically compared to code — that boundary is unbuilt, so
they are owned by this hash freeze and reviewer approval until Fiscal writes its own
boundary tests. The exact first-consumer raw profile is PUBLISHED as the
`staged_raw_channel` object inside the single CONTRACT-SURFACES block (event, text-part,
item, xbrl, nested `ix`, dimension and retired-field spellings, plus the unchanged
source_type vocabulary), and the never-send / source-completeness duties are retained. It is STAGED, not live: `ChannelContract.md` (v1.0) remains the live public
authority and `15_CandidateFactPacket.md` remains the live INTERNAL packet law.
The freeze is ENFORCEABLE, not prose: `driver/core/test_v2_attacks.py` compares every CURRENT
CODE-OWNED surface to its existing code owner AND proves this sha256 equals the
document's real bytes, so a silent edit to either side fails.
PROMOTION RULE — at the atomic V1->V2 switch, in ONE batch: this document is PROMOTED to
`ChannelContract.md`; `15_CandidateFactPacket.md` is SEPARATELY re-frozen to its own V2
packet law (a distinct internal contract, never a copy of this public one); every live caller
and `aa7239ed` pin is moved; the already-frozen V2 EXP-5 bundle is verified rather than
regenerated; and `ChannelContractV2.md` IS DELETED. Nothing was activated, written, fetched
or run by this freeze.

**2026-08-12 — EXP-5 TIMING: PRE-SWITCH PROOF (owner-ratified).** The
2026-08-11 switch-gated timing above is superseded. Exact order: commit and
freeze the staged-V2 dry-run bridge -> regenerate and freeze the complete EXP-5
bundle against that staged contract while V1 remains live -> lock K-fields and
run EXP-5, then EXP-6 -> build the real shared reader/decomposer and
admission/reuse kernel from the signed evidence -> prove the complete V2
no-write route -> perform the atomic V1->V2 switch. This is a timing ruling only:
it activates no V2 caller, authorizes no paid model call, changes no fact rule
or test bar, and permits no Neo4j write. A failure stops before activation.

## 5. Signed experiment decisions + remaining gates (authority = signed decision.json artifacts)

EXP-1 PASS 07-09 (O13 dimension binding owner-ratified) · EXP-0 PASS 07-10 (grader = 2× `claude-sonnet-5`
@effort=high; the (model,effort) pair binds) · WP-FC-EDITS `5db902f` 07-10 · WP-FA + O2 signed 07-10 · K-reader
v3 LOCKED 07-10 · EXP-2 PASS 07-11 (sonnet-5@high/40k/1-run). Current EXP-5:
corrected calculation completed, FAIL with grading limits (§1.3); source-only
K-fields key signed (§1.2). EXP-3/4, K-route/K-stamp/K-pairs.v2, WP-FC-RUN and
F-C freeze remain open; EXP-6 waits for EXP-5 PASS.
Standing gates: ra_0007 kernel-§6.1 review BEFORE K-pairs.v2; original Plan sha `51966848…7472` remains historical;
WorkOrder sha recorded, never pinned — authoritative record = `experiments/WORKORDER_STATUS.md`, re-recorded at
every edit incl. the Phase-5 21c re-point (board UPDATED at Phase-5 step 21c 2026-07-16 — the full hash chain recorded, its current line authoritative;
frozen original `4911a22f…` = archive MANIFEST). Artifacts:
`.claude/plans/Drivers/experiments/`.

Earlier PASS labels qualify their own tasks, not A7 or production. EXP-2's
selected reader matched 475/1,175 expected names (40.43%); its audited precision
sample was 51/60 (85%), not a complete accuracy census. EXP-1's 9,603 fixture
rows demonstrate deterministic materialization, not live activation. The
complete signed artifacts and dated board entries retain their original bars.

## 6. Known documentation/logic issues (open; no new authority)

- The 24 stale-text items (per-file) and the interim hazard rule: the archived `CONSOLIDATION.md` §10.1 + Phase-2 note.
  Biggest traps: `03`/`11`/`12` old collision text (OD-8 is current) · `04` one-hint-pair (per-slot is current) ·
  `09 §8`/`07 §D` expectation-baseline wording · stale experiment headers (signed artifacts win) ·
  `15` "already built" = "fully specified" (stale-item 11).
- Missing build recipes (packet lifecycle · born-complete transaction · machine contracts; ID namespaces
  CLOSED 2026-07-16 — owner-approved S3.1 ID law, BUILD §5/§11.3):
  BUILD §11.
- Truly open owner choices: FINAL_DESIGN §10 OPEN list.

## 7. Source crosswalk (33 files → destinations; every row re-verified at Phase 4/5)

**Phase 5 EXECUTED 2026-07-16 (owner GO):** every "archive" destination below is DONE — EXCEPT the two
deferred experiment files (the byte-pinned Plan + the WorkOrder, which archive only after the experiment
program migrates) — all 27 remaining
sources moved byte-verified vs the manifest (the two ratified-design originals had already moved 2026-07-15);
the three pre-amendment/frozen-original snapshots sit beside them.

| Source | Status | Destination |
|---|---|---|
| 00_Coverage / 01_Overview | stale summaries | FINAL_DESIGN §1-§2; archive |
| 02_DriverCatalog | rule owner | FINAL_DESIGN §3; archive |
| 03_Slices_FactScope | rule owner | FINAL_DESIGN §5; archive |
| 04_Units | rule owner | FINAL_DESIGN §6.1; archive |
| 05_Periods | rule owner | FINAL_DESIGN §6.2; BUILD §5; archive |
| 06_MetricFamily | rule owner | FINAL_DESIGN §4.1; archive |
| 07_DriverUpdate | rule owner (DU-13..18 replaced by 09) | FINAL_DESIGN §4.3/§7.3; archive |
| 08_XBRL_ConceptLinking | rule owner | FINAL_DESIGN §8; BUILD §5; archive |
| 09_DriverUpdate_Fields | field/read authority | FINAL_DESIGN §7/§9; archive |
| 10_BuildPipeline | Track A manual | BUILD §4; archive |
| 11_TrackB Census · 12_FactPipeline | normative census + build manual | FINAL_DESIGN (rules) + BUILD §5; archive |
| 13_TrackC (active) · 13_Track_RetiredDesign | retirement plan · retired history | BUILD §6 · archive (one pointer to its still-useful non-replay analysis: GI-31 `<=` rationale, 894-source reachability audit, 4 stated-mid outliers) |
| 14_BuildReadiness | stale checklist | BUILD + this file's dashboard; archive |
| 15_CandidateFactPacket | FROZEN v1.0 + the two 2026-07-15 owner amendments (Q4, Q1-ext) | temporary fifth live file (current sha `aa7239ed…`) |
| 66_IssuesToBeHandled | owner blocks + stale tail | rules → FINAL_DESIGN; status here; archive |
| 90_OpenItems · 95_Supersession · 99_Codex audit | status · 43-row ledger · history | this file §1-§3; archive (99 wholesale) |
| BayesProposal | unvetted proposal | BUILD §8.3 pointer; ARCHIVED directly in the dated archive 2026-07-16 ✓ |
| ChannelContract | ACTIVE live file | kept — the SOLE public channel authority under the one-copy law; amended 2026-07-15 (XBRL/evidence/provenance) and 2026-07-18 (PER-21 source-completeness pointer); current sha tracked in git + CONSOLIDATION §16 hash freeze |
| DriverGenesisRestructure | unapproved rationale | open charter questions in FINAL_DESIGN §10; archive |
| DriverPlan.html | stale study export | none (regenerate later from live docs); archive |
| FableAdmissionKernelDesign | **RATIFIED working design (owner 2026-07-15; not activated)** | full mechanics → BUILD §8.1 + law-grade parts → FINAL_DESIGN (destination proof §7.1b); **original ARCHIVED 2026-07-15, byte-verified — DONE** |
| FableContextPack · WorkflowContextPack | stale navigation/code maps | ARCHIVED 2026-07-16 ✓ (the Workflow pack's 21b live-code re-audit PASSED pre-move — 34-claim verdict table; its one load-bearing residue carried into BUILD §4; links repaired) |
| FableExperimentPlan · WorkOrder | pinned plan · runbook | BUILD §9; keep Plan byte-identical until program migrates; archive after. The Plan's frozen authority ladder (lines 4/257) resolves externally: its "lock candidates" were RATIFIED 2026-07-15 (operative mechanics = BUILD §8.1/§8.2; originals = archive evidence); its topic docs resolve to the archive paths with meaning carried by the four live files (step 21c note) |
| FablePrompt · FablePromptv2 | executed briefs | provenance entries only; archive |
| XBRLIntegrationDesign | **RATIFIED working design (owner 2026-07-15; DORMANT until P19 + gates + EXP-6)** | recipe + pin map + the ten amendments → BUILD §8.2 + owning law sections (gate-tagged); **original ARCHIVED 2026-07-15, byte-verified — DONE** |
| CONSOLIDATION.md | audit + migration map | MOVED into the dated archive at Phase-5 step 7 (2026-07-16) ✓ — never a fifth rule source |

### 7.1 Rule-ID crosswalk (every stable ID range → its one live anchor; §14.1 artifact)

Coverage law: every ID in a range maps to the range's DEFAULT anchor unless it appears in the exceptions
column — the map is total over every ID listed in the archived `CONSOLIDATION.md` §14.1.

| Rule IDs | Default anchor | Per-ID exceptions (exact) |
|---|---|---|
| NAME-01..19 | FINAL_DESIGN §3 (inline, own numbers) | — |
| FS-01..04, 27 | FINAL_DESIGN §5.1 | FS-03's old collision text dead → OD-8 (§5.1) |
| FS-05..24 | FINAL_DESIGN §5.2 | FS-09 separators also §5.1 · FS-14 menu + PIT · FS-15 kind ladder · FS-16/18 code-exact rules · FS-20 buckets · FS-21 member link · FS-22 RETIRED (row 37) · FS-23 OPEN (§2) |
| FS-25 | FINAL_DESIGN §5.3 | — |
| FS-26 | FINAL_DESIGN §5.4 | storage shapes + guards + recovery inline |
| UNIT-01..13 | FINAL_DESIGN §6.1 | UNIT-04 replaced by per-slot hints (row 26) · UNIT-08 per-X also §3 NAME-13 |
| UNIT-14 | BUILD §5 | build wiring only |
| PER-01..19 | FINAL_DESIGN §6.2 | — |
| PER-20 | BUILD §5 | resolver build + 21 tests |
| PER-21 | FINAL_DESIGN §6.2 | earnings 8-K routing procedure → BUILD §3; owner ruling R13 |
| MF-01..10, 12 | FINAL_DESIGN §4.1 | MF-05 latent anchors also §4.2 · MF-10 inheritance also §8 |
| MF-11 | FINAL_DESIGN §7.1 | `company_confirmed` |
| DU-01..07 | FINAL_DESIGN §4.1/§4.2 | DU-05/06/07 classifier content §4.1; prompt pin BUILD §4 |
| DU-08..12 | FINAL_DESIGN §4.3 | state vocabularies |
| DU-13..18 | FINAL_DESIGN §7.1 | explicitly REPLACED by `09`'s contract (banner row `07`) — shapes, DU-15 baseline, sign rule, value_text/conditions/confirmed |
| DU-19..24 | FINAL_DESIGN §7.3 | edges, verdict, DCM |
| XC-01..18 | FINAL_DESIGN §8 | XC-04..08 verbatim blocks inline · XC-16 CONDITIONAL · rollout/vetoes-build → BUILD §5 |
| PIPE-01..37 (+27a/27c/27d/31b) | BUILD §4 | PIPE-12 relay-trust + PIPE-15 run layout summarized in D1-D8/constants · PIPE-16 authority swap (prompts inline NAME rules) · PIPE-24/25/26/35 finalization/consumption inline · PIPE-32 A/B gate |
| FACT-01..36 (+14b/17b/18a/26b/26e/26f) | BUILD §5 | FACT-16 validators + §12 gates (F1-F9/P1-P8) inline · FACT-17b = the internal packet → BUILD §2 · law mirrored in FINAL_DESIGN §5/§7 |
| T1.1..T12.9 (census `11`) | per-group anchors in the T-table below | the census DUPLICATES `09`/`12` normatively; numbering retires at archive |
| GI-01..04 + active `13` §§0-15 | BUILD §6 | runbook/deletion/gates inline; §§12-15 are meta sections (cross-doc edit log, non-goals, minimalism proof, drafting record) with no rule IDs — covered by the §7 file-level row |
| Retired `13_Track` file's OWN GI-01..07 and GI-10..36 (a separate numbering from the active file's GI-01..04; **no GI-08 or GI-09 exist**) | history only — §2 RETIRED list | never live mechanics; still-useful non-replay analysis pointer in §7 crosswalk row |
| Track A D1..D8 | BUILD §4 | — |
| `66` D-1..D-13 | doc-debt history, resolved in place | archive only |
| OD-1..21 | per-ID anchors in the §3 additions list | all 21 individually anchored there |
| K2 | BUILD §4 | — |
| 43 supersession rows | §3 above | — |
| Contract clauses §1-§9 | ChannelContract.md (live; one section per clause: what-a-channel-is · flow · packet · never-send · submission · outcomes · ledger duties · never-list · onboarding) | — |
| Packet blocks 0-3 + Parts B/C/D | the live frozen packet (structure summarized BUILD §2) | — |
| Ratified design bundles (formerly candidates) | BUILD §8.1 (kernel mechanics whole) · §8.2 (XBRL recipe + pin map + amendments) = the OPERATIVE text; the archived originals are historical evidence only (destination proof §7.1b) | — |
| Open items | §2 OPEN list (mirrored FINAL_DESIGN §10) + BUILD §11 missing recipes | — |

### 7.1b Ratified-design destination proof (owner order 2026-07-15: every transferred item → its exact live anchor)

**Kernel (FableAdmissionKernelDesign.md → live anchors; BUILD §8.1.x unless noted):**

| Kernel section | Content | Live anchor |
|---|---|---|
| §1 strategy D1-D4 + 8 answers/3 amendments | anchor-first live-always | BUILD §8.1.1 |
| §2 decision flow (Stage 0-3, async, axiom C) | intake/router/arms/guards/provenance | BUILD §8.1.2 |
| §3 G1 display | cards, never-shown, verbatim instruction | BUILD §8.1.3 |
| §4 arms + the 8 park codes | ATTACH/ADOPT/CLAIM rules, park governance | BUILD §8.1.4 |
| §5 family policy | stamp/resolve functions, variant stamping, latents | BUILD §8.1.5 (+ FINAL_DESIGN §4.1/§4.2 law) |
| §6.1 LINK operation | pair assembly, auto-refusal taxonomy, the 5 checks, high-blast, apply/memo/head election, cache | BUILD §8.1.6 |
| §6.2 two triggers + ledger hygiene | CLAIM-off/shadow, sweep, deferred ledger | BUILD §8.1.6 |
| §6.3 frozen anchor | birth_quotes, refuted negatives, enrichment-OFF, re-freeze | BUILD §8.1.6 |
| §6.4 union-preview | abstain-only | BUILD §8.1.6 |
| §6.5 eligibility/establishment | BROAD/ESTABLISHED/CLAIM_FROZEN, in-tx read, single-company exception | BUILD §8.1.6 |
| §6.6 split-reconciliation lane | batch-grade re-judgment of mutual refusals | BUILD §8.1.6 |
| §7 validators V1-V14 | full meanings | BUILD §8.1.7 (V14 also FINAL_DESIGN §5.4) |
| §8.1-8.5 phases/seed/gauntlet/eligibility/contingency | sequence, S-A1..6, P1..P9, pass bar, BROAD-keyed features, ladder | BUILD §8.1.8 |
| §9 immune system | doctrine, falsifier (i)-(vii), audits, calibration stream, flow metrics, launch blockers | BUILD §8.1.9 (ATTACH-audit law in FINAL_DESIGN §5.4) |
| §10 recovery items 1-8 | provenance, signal-quarantine, 2-grader confirm, propagation, RecoveryEvent, wrong-quarantine, D4 scoping, disputed | BUILD §8.1.10 (+ FINAL_DESIGN §5.4 law) |
| §11.0/§11 model tiers | locked rule, tiers, owner defaults, P1-P7 deltas | BUILD §8.1.11 (principle in FINAL_DESIGN §1) |
| §12 experiments | S1-S4, X0-X9, X-G, X-IM, X-C | BUILD §8.1.12 |
| §13 rejected · §14 reject-conditions | terse load-bearing lists | BUILD §8.1.13 |
| §15.0 MVP split · §15 bundle · §16 residuals | day-1 core/deferred/coverage rule · six ratified items · five residuals | BUILD §8.1 (the three dedicated blocks) |

**XBRL (XBRLIntegrationDesign.md → live anchors):** §3 coverage five-conditions + §5.2 recipe steps 1-9 +
graph-verified formType literals → BUILD §8.2 recipe · §5.3 period classifier + P14 → BUILD §8.2 pin map + §5
dormant-amendment note · pins P1-P17/P19 (incl. P16) → BUILD §8.2 pin map · the ten amendments → their owning
sections, gate-tagged: (1)(3)(7)(9) → BUILD §5 validator note · (2) → BUILD §8.1.7 V9 · (4) → FINAL_DESIGN §8
rider line · (5) → BUILD §8.1.6 eligibility · (6) → FINAL_DESIGN §8 XC-18 · (8) → BUILD §8.1.9 falsifier ·
(10) → FINAL_DESIGN §9 collapse rank · TextBlock disposition + half-ULP gate + ConceptResolution schema +
graded reversal + kernel-dependency note → BUILD §8.2.

### 7.2 Census T-group anchors (per-group exact map; within a group, rules share the group anchor unless a per-rule exception is listed)

| T-group | Census topic | Exact live anchor(s) |
|---|---|---|
| T1 (T1.1-T1.8) | Mission constraints & laws | FINAL_DESIGN §1; exceptions: T1.4 producer-free id → §5.1 · T1.6 enrichment-never-identity → §8 · T1.7 FROM_SOURCE ≠ EXPLAINED_BY → §7.3 |
| T2 (§2 tables, no T-bullets) | The record — 24 stored fields | FINAL_DESIGN §7.1 |
| T3 (T3.1-T3.8) | Identity — id + fact_scope grammar | FINAL_DESIGN §5.1 (OD-8 replaces T3.4); T3.5 measurement → §5.3 · T3.6/T3.8 slices → §5.2 · T3.7 period-both-places → §6.2 |
| T4 (§4 edge table) | Edges & neighbor nodes | FINAL_DESIGN §7.3; HAS_PERIOD lane rules → §6.2 |
| T5 (T5.1-T5.5) | The verdict edge | FINAL_DESIGN §7.3 |
| T6 (T6.1-T6.5) | Lanes — type × state × field matrix | per rule: T6.1 fact_type definitions + verbatim classifier → FINAL_DESIGN §4.1 · T6.2 state lanes → §4.3 · T6.3 state-in-lane hard-fail → §4.3 (final line) · T6.4 per-lane matrix + OD-21 amendments → §7.2 (+ §5.1 for the `surprise=` slot) · T6.5 revisit triggers → §10 OPEN list |
| T7 (T7.1-T7.12) | DriverPeriod | FINAL_DESIGN §6.2; T7.12 build gates (PER-20) → BUILD §5 |
| T8 (T8.1-T8.10) | Units | FINAL_DESIGN §6.1; T8.10 build gate (UNIT-14) → BUILD §5 |
| T9 (T9.1-T9.9) | Slice & member at write time | FINAL_DESIGN §5.2 |
| T10 (T10.1-T10.8) | XBRL concept link | FINAL_DESIGN §8; rollout/veto build → BUILD §5 gate 4 |
| T11 (T11.1-T11.11) | Producer interface contract | FINAL_DESIGN §4.2 (T11.1 real-fact gate; T11.2 who-fills-what: channel submits raw, the core alone fills state+numbers after the gate — contract side: ChannelContract §1 "never creates, never names, never decides identity" + §4 never-send list) · §5.1 (T11.3 fusion + basis hint) · §6.1/§7.1 (T11.5 hints, T11.8 %-guidance basis, T11.10 rate-vs-level) · §9 (T11.4 slices-beat-mixed · T11.6 chronological processing + the code-served strict-`<` PIT prior view, guidance-lane-only, with §4.3's no-graph-read rule — contract side: ChannelContract §5 "submit events chronologically per company" · T11.7 fan-out · T11.9 policy routing · T11.11 one-update-per-source-time-statement, trajectory always derived never stored — writer-side law only, no contract-side content by design) · BUILD §5 (CLI order + PIT prior view) |
| T12 (T12.1-T12.9) | Read contract | FINAL_DESIGN §9; T12.6 series_unit law also §6.1 |

**External inbound citations (link sweep EXECUTED at Phase-5 step 8, 2026-07-16; repo-wide scan clean):** 12 files
cite exact FinalDesign filenames — the experiments board/handover/exhibits/keys/harness plus the engine prompts
`workflows/menu_build.js`, `reconcile.js`, `gate.js` (re-pointed: labels name FINAL_DESIGN §3 as authority with
archived-02 provenance; runtime archive reads removed round 22; NAME-17 synced to OD-21 round 23 — rulebook-sync
test `workflows/tests/test_rulebook_sync.py` guards drift; the Track A implementation gate — BUILD §4 — governs
any future run: verify every rule-bearing component vs the then-current law + a pinned current-law certification;
the old Restaurant runs' RULE-BEARING outputs are historical evidence only, with the raw-text chunk copies
excepted where the WorkOrder pins them — the exact scoping lives in BUILD §4). Stem scans reach 21; bare-word 22 incl. one `INDEX.md` name-collision
false positive. Both scans were re-run at the Phase-5 move (2026-07-16); every hit updated or validated — the
repo-wide broken-reference scan came back clean (card step 8).

## 8. Archive manifest + evidence pointers

- **September 15 status consolidation:** `DRIVER_STATUS_REPORT.md` was folded
  into §1 and removed; its full September 7 audit remains at
  `2dc0ad39f30dba4756078573f5e80038465939cc:.claude/plans/Drivers/FinalDesign/DRIVER_STATUS_REPORT.md`,
  SHA256 `68e636d5b7a485f2dd2c5ed8002c6ba9561409ee436f47f886d37d7e213c37f9`.
  The completed A7 diary was also folded here and removed; its exact final
  revision 254 remains at
  `3340851ef2aa75817ff18b9beb73301b36370a39:a7_recovery/A7_PREGRADING_WORK_ORDER.md`,
  SHA256 `b27f3c02415e5cebcc869739d9e13a985f815e352e7722848e244bb8ade5267f`.
  Read either with `git show <commit>:<path>`. Earlier frozen publication
  builders/manifests still refer to their historical work-order path: use
  their original committed snapshot, never repin them to this handover.
  No grading runtime or live test requires either deleted document. Original
  answers, keys, signed results, maps, manifests and mailbox archives remain.
  Main/recovery now share the already-approved partial-report Plan amendment;
  recovery uses the current main communication instructions. Neither is a
  new rule, new protocol or authorization to resume the roadmap.
- **The archive's contents, exactly (two distinct kinds — never conflate):** (a) **32 SOURCE COPIES** = 29
  source originals + 3 pre-amendment/frozen-original snapshots; (b) **EVIDENCE FILES, which are NOT source
  copies** = the audit file `CONSOLIDATION.md`, `MANIFEST.json`, `README.md`, and the `READER_TEST_RECORD_*`
  files. Source 33, the byte-pinned `FableExperimentPlan.md`, remains at the root (manifest-verified in place).
- **Freeze manifest:** `archive/2026-07-15_pre-consolidation/MANIFEST.json` — all 33 sources sha-256-pinned
  (11,320 lines / 1,362,208 bytes verified), git provenance, commits `49f1cd8`/`87bc150`. Owner-amended
  live-continuing files verify against post-amendment hashes: ChannelContract (see git for current after the
  2026-07-15 provenance one-liner) · packet `aa7239ed…`
  (recorded in the archived `CONSOLIDATION.md` §16).
- **Evidence/rejected-alternative pointers:** v1/v2 death evidence, unit proofs (117/117 · 29/29+7 · 3×33/33),
  concept-link proofs (31-co zero-wrong · 274-co 100%/~70%/98% + caveat) → BUILD §12. Bayes proposal → BUILD
  §8.3. Executed prompt briefs (FablePrompt/v2) → archive provenance. Experiment artifacts + signed decisions →
  `.claude/plans/Drivers/experiments/`. Relocation/harvest engine state (separate track) →
  `scripts/driver_seed/relocate_probe/STATE.md`.
