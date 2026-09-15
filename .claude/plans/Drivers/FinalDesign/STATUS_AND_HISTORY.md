# Driver project — status and history

This is the **single general handover**: current progress, preserved decisions
and evidence locations. It does not define new Driver rules.
`FINAL_DESIGN.md` owns meaning, `ChannelContract.md` the active public boundary,
`15_CandidateFactPacket.md` the active internal packet, `BUILD_AND_OPERATIONS.md`
build/release procedure, and `LeftOverSteps/Steps.md` execution order.

**Read §1–2 for the current handover.** Sections 3–8 preserve decisions and
historical cross-references needed by live plans and tests. Their old “next,” “open”
and completion statements describe their dated snapshots, not new tasks.
Later owner rulings in Steps.md prevail. Communication and session startup
belong only in [Orchestration.md](LeftOverSteps/Orchestration.md).

## 1. Current handover — 2026-09-15

**Goal:** turn source reports into reusable business causes and exact,
source-backed facts. Models decide meaning; code checks evidence, numbers,
dates and identity. Production is not finished or activated.

**Stopped at Step 1 / A7 (EXP-5):** the corrected score and bounded error review
are published, but **A7 did not pass**. Grader uncertainty and observed answer
errors remain. The later selected-case/input-format diagnostics do not replace
the official score or prove the reader fault-free.

**Current project state: STOP AND WAIT** for the owner's next task. This
documentation-only update does not reopen A7, A8 or later steps.
The [experiment board](../experiments/WORKORDER_STATUS.md) retains package
receipts, not a second general work order.

### 1.1 Where the work lives

| Location | Published checkpoint before this documentation cleanup |
|---|---|
| Main: `/home/faisal/EventMarketDB`, branch `main` | `bd361f7364297b71c9bbaa10ef5c725942069ca1` |
| A7 work: `/home/faisal/EventMarketDB-driver-recovery`, branch `recovery/a3-a7-verified` | `b9376c0a0dcc7f871d1c37a1eebe1858421e8623` |

Recovery code/evidence is **not merged into main**. These two handover documents
are synchronized; that is not an implementation merge or deployment.
Session startup is separate from the worktree: follow Orchestration.md and
use the recovery path for A7 edits/tests, not main.

For newer tips, use `git rev-parse HEAD` in each worktree and
`git ls-remote origin refs/heads/main refs/heads/recovery/a3-a7-verified`.
Recovery has no configured upstream. Below, **A7** means the recovery
worktree's `a7_recovery/`; **U** means `A7/unit_2020_codex_check/`.

**Protect unrelated local work.** Main has settings changes, market-data
documentation, two old `receipts_827` inventories and deleted test-agent/skill
files. Recovery has an unrelated edit to
`A7/grader_20260909/harness_g1v3/build_inventory_review.py`
(SHA256 `2ec3bd338f7dce181ff6794790cf634c6f68e73217daef88a25e365731ee4ed2`).
Both trees have extensive untracked files. Never blanket-stage, clean or reset.
Frozen maps may contain old logical `/tmp` paths; the mapped evidence is
durable. Do not move it back or rewrite historical map pins.

### 1.2 Completed work and its proof

| Work | Delivered result / evidence |
|---|---|
| Deterministic foundation | Core source binding, arithmetic, periods, IDs, validation, fusion and no-write planning; Fiscal source fetching/relocation and slice-menu work. These do not constitute the production meaning reader or identity system. |
| Staged V2 bridge and original exam kit | `0edb1be8` / `0dd71956`, writes off. The August kit recorded 3,682 passes and 3,741 accounted identities, with 58 read-only tests and one unrun write probe separately pinned. Historical totals, not today's full suite. |
| A1–A3 preparation/recovery | A3 checkpoint `26836bb309542163b7a1a0da480905e396d3668d`. Reuse the 382 original answers: 191 items per run, two runs, 33 source events. Never repeat a successful answer merely to recover files or improve its score. |
| A4 recovery | `90925920d5f2675191edfe5f1285c239177ca453`. The older draft-fed key is historical, not the later independent source-only key. |
| A5 / A6 preparation | Published at `38e42d9a43d2ec1a9cf69e5c01b0c3a1af5010c3` / `cc7df9f41206c22604fa3736f4c97d120ee74dbc`. Saved answers are evaluated under their original served instructions. |
| Independent source-only key | `U/codex_lock2149_a/SIGNED_KEY.json`, SHA256 `4474bd7a330a0cb5c03aef09883053ce34d138bfd43ff4046671580b65591ee4`. 33 events, 191 rows, 165 expected facts, 34 controls, 10 exclusions, 44 abstentions; no open signing issues or exact duplicate key facts. Counts overlap and must not be summed. |
| Grading connection and final calculation | Raw capture, parser, normalizer, matching, independent judgments, real Core no-write route and scorer connected. Run/map: `U/FINAL_SCORE_COMMAND_2174.sh`, `map_final_grading_2174.tsv`. Result/cause/reuse package `8dacb463406a48e0179f269e87e145d8c5823564`: 99 no-write event routes, four completion loads, zero new model calls in the final calculation. |
| Later diagnostics | Original-prompt two-call probe: `A7/manual_probe_20260915/RESULT.md`, commit `c8188c5c6c6fd8c926526dda47f2095104115595`. Modified-input diagnosis and recovered native evidence: `A7/unit_input_diagnosis_20260915/`, commit `5fb3feef80f1d4c59dae47d538d158afcf2f413c`. Neither replaces the official test. |

The key lock, signing/producer receipts and finalization identities remain in
the signed package and frozen run map. The old “82 launched” / “206 lanes”
counts describe recovery schedules, not this final evaluation's denominator.

### 1.3 A7 result — completed calculation, not qualification

Official report: `U/codex_final_score2174_a/A7_CORRECTED_SCORE.json`,
SHA256 `966d14bc71ee487afdeff88a41fbf59ccf0e68c349a342c96a60aa0ff733a062`.

| Measure | First run (P1) | Second run (P2) | Strict combined result (UNION) |
|---|---:|---:|---:|
| Expected facts matched | 123/165 (74.55%) | 116/165 (70.30%) | 71/165 (43.03%) |
| Raw value/shape measure | 87.54% | 86.95% | 90.84% |
| State measure | 94.87% | 95.54% | 98.53% |
| Wrong-accept flags | 9 | 9 | 8 |
| Incomplete meaning judgments | 48 | 38 | 18 |
| Raw `key_miss` labels | 4 | 11 | 84 |
| PASS / safety result | false / FAIL | false / FAIL | false / FAIL |

**A match is not a fully correct answer.** P2's 116 matches include 100 the
code would accept, 13 held for dates and three rejected for units. Some accepted
facts still have meaning errors. UNION follows the frozen agreement/matching
rules, not a simple union of match counts. No column is production accuracy.

All 426 required grading questions are accounted for: 388 unaffected outcomes,
24 selected outcomes changed, 14 selected outcomes unchanged. The 104 incomplete
meaning judgments stay uncredited; they are not missing calls or permission to
reroll valid disagreements. All three reports say
`required_grading_unfinished=true`.

`U/FINAL_SCORE_FINDINGS_2174.md` and its linked cause/addendum records preserve
the exact findings. The bounded source review supports defects in 23 of 26
flagged records; three remain unconfirmed. Examples include missing Best Buy
Health scope and pre-tax measurement. Their existence does not by itself
separate input/prompt effects from model limitations. Grader false positives,
vague-quantity/range interpretation and a Boeing-option stage question remain
qualified. Many raw `key_miss` labels are contradicted by existing reference
cards, not proved missing-key facts. No replacement judgment was invented to
raise the score.

The separate original-prompt two-call probe restored Health in both replies.
One still duplicated the charge and omitted start dates; the other would pass
code checks. Both read a dash as prior zero, which the instructions did not
conclusively settle. No source loss between that saved prompt and those two
calls was found; the earlier HTML-to-text conversion was not covered.

#### 1.3.1 Later input diagnosis — verified findings and limits

Read `A7/unit_input_diagnosis_20260915/ANALYSIS.md`
(SHA256 `06c85ac40de6d2edb350fd7cea8156fb91056d9cf21f1127577d3cef6a2bac81`)
**with the qualifications here**, not as proof that most errors are unrelated
to the reader. `EVIDENCE_INDEX.json` inventories the full hashes, native
records, source dependencies and verification results.

* **Input binding:** 10 original prompts match their pins; removing the added
  grids/rule restores their headers. All 10 modified inputs parse and retain
  their quotes; four saved SEND files match, and 18 grids match the scripts'
  HTML-cell rendering. Four native `claude-sonnet-5` child records cover all
  511 lines of their respective inputs and contain the saved JSON replies and
  completed turns. No successful call was repeated.
* **Selected results:** four replies cover only two Best Buy targets. Both
  impairment replies include Health without duplicating the charge, but differ
  in name/end date; both revenue-mix replies agree on quarter/year-to-date
  values. Structure **and** a rule changed, so this does not isolate the cause
  or correct the official grades.
* **Formatting concern:** reproduced 3,196/3,751 matched labels without a newline
  in the preceding three characters, across 15 filings. A saved heading/data
  join is real. The 85.2% is this proxy, not the fraction of all lost boundaries
  or of A7 errors caused by formatting.
* **Grading variation:** 10 repeated records, 28 appearances, 70 record/field
  checks: 57 agree, 12 decided-versus-unresolved, one true-versus-false. Source,
  record and reference card agree; question IDs/batches differ. This is not a
  general one-in-five error rate or a 19% score-noise floor. Recorded
  format-only recoveries (93/141 attempts) are already applied, not calls owed.
* **Withdrawn/unproved claims:** the 88.3% cause attribution groups overlapping
  counters, not individually traced causes. D3's plain/encoded Health-token
  difference is already handled by `unit_2008/harness_g1v3/a1_reader.py`;
  official P1 already used the key token. Rule 6 already discusses duration
  windows, so D1 is a possible clarity gap, not total silence. Geometry v1
  counts any covering header; v3 constructs non-overlap by definition and
  ignores row spans. Neither proves a generally correct table parser.

The original analysis and Core's `ADDENDUM_2179.md` are preserved historical
bytes, including their stronger claims. Core withdrew/qualified those claims
in the later mailbox review. Codex also recovered the four native records and
the parser timing output that Core had mistakenly declared unavailable.
The latter records 30/30 parsed, 2,237 tables and a 0.73-second median; it was
recovered, not independently timed or treated as a correctness test.

Both selected original HTML filings and the six cited guidance-review files
are preserved. A 69-file hash roster identifies scale-test inputs; the other
HTML files and the newline test's database text remain external dependencies.
The original 31-entry manifest and later 36-entry manifest are both retained;
the complete inventory is EVIDENCE_INDEX.json. Historical materializer/pre-A2-
lock scratchpad files could not be identified by Core: no recovery/completion
claim is made, and they are not added as A7 prerequisites.

Next investigation, only when authorized: the table-format, prompt-clarity,
menu-ambiguity and grader-variation leads above. Do not erase observed errors,
declare the reader fault-free or promote the diagnostic parser on this evidence.

### 1.4 Verification, limits and model reuse

The published final package records **318 tests plus 29 subtests passed**,
including 15 offline model-reuse checks. The reporting fix first failed seven
tests with two passing controls, then passed nine focused tests and four
reversion mutations. Exact commands/results: `U/FINAL_REGRESSION_COMMAND_2176.sh`,
`OFFLINE_VERIFICATION_2176.json`, `FINAL_CHECKPOINT_REVIEW_2176.md`.
`FINAL_SCORE_TRACE_2174.json` reproduces 310 matched pairs and 16 measures per
run; it does not decide meaning.

`U/MODEL_REUSE_OFFLINE_REVIEW_2176.md` proves reuse of the grader/parser/no-write
route with unfamiliar supported offline input. **Changing a local model name
alone is not a verified launch.** The separate inference-host task still needs
prompt-capacity proof, actual returned model/completion capture and honest
attempt/resume receipts. No local model or inference engine was changed.
Follow `LeftOverSteps/QwenInference.md`; older handoffs are historical where
superseded. Frozen authority copies are in `U/snapshots_2176/`.

Production must not import experiment-harness code. Step 3 transfers approved
prompt/response responsibility to production ownership; the grader remains an
external evaluation tool, not code to embed in production.

Main's earlier documentation audit recorded 201 passes and three pre-existing
failures: generated-patch repeatability, its enclosing clean-proof check and
pin-inventory repeatability. Do not claim the whole main suite is green or
regenerate frozen proof merely to clear these findings. The consolidation
recorded 84 documentation/contract passes and the A7 regression above.
Historical A7 maps require their original documentation snapshot; later
document changes are not permission to overwrite their hashes.

The previous handover's two live documentation/contract checks passed on both
branches; 18 preserved Python files parsed and four native input/reply bindings
matched. These were documentation/evidence checks, not a fresh A7 qualification.
The September 7 graph census (Driver/DriverUpdate/DriverPeriod 0/0/0) is dated,
not a current guarantee. The live adapter refuses transactions; this work made
no database write or activation.

### 1.5 Remaining roadmap — advancement paused

| Step / part | Remaining result |
|---|---|
| 0 | Historical roadmap/status publication complete; this is routine status maintenance, not a new Step 0 or Step 13. |
| 1 A7 | Published FAIL with the limits above; any correction/change needs the next bounded owner-directed task. Reuse valid saved evidence. |
| 1 A8 | EXP-6 text/tagged-fact identity comparison not run; waits for EXP-5 PASS. |
| 1 B1–B7 | Catalog/identity lane unfinished. B1 parked for A7 priority (Codex archive 1445); NAME-16 remains a step7 lead. B2 catalog, B3 type key/stamping, B4 mini-catalog freeze, B5 routing key, B6 routing experiment, B7A pair-key and B7B identity experiment remain open. |
| 2 | Signed build decision for both Step 1 lanes. |
| 3 | Shared production meaning reader. |
| 4 | Production admission/reuse/create, type/family, links, continuity and recovery. |
| 5 | Complete V2 no-write proof, including validation-door/fusion ordering. |
| 6 | Atomic V2 promotion, caller migration and V1 removal; V1 is still active. |
| 7 | Production catalog/finalizer, safety and fitness qualification. |
| 8 | Remaining fact wiring, concept links, reads, withdrawals, verdict/DCM plans and dual-producer calibration. |
| 9A / 9B | Fiscal source-location certification; the 150-real-anchor gate waits for Step 11's first lawful records. Do not restore withdrawn certification artifacts. |
| 10 | Minimum operating layer; design overlap only where Steps permits, implementation after 8 and 9A. |
| 11 | Shadow, separately approved bounded graph setup/write, 9B and controlled rollout. |
| 12A / 12B / 12C | Consumer/Guidance retirement; 12B records the owner-frozen empty first-release channel set; native tagged-filing rollout remains last and gated. |
| 13 | Whole-system closure. |
| 14 | Dormant, never a prerequisite to 13. |

[Steps.md](LeftOverSteps/Steps.md) owns exact dependencies and approvals.
Do not infer completion from file/test counts or old time estimates.

### 1.6 Foundation and preserved audit leads

`driver/core/driver_write_cli.py` owns event dispatch; prepared-fact modules
own schemas; period/unit/ID/fusion/validator/writer modules own deterministic
checks. `driver_neo4j_adapter.py` is the fenced Report-only graph adapter.
Fiscal locates/copies sources, not meaning or identity. Legacy known-value
relocation and source-neutral tagged relocation retain their separate callers.
Catalog tools live under `.claude/plans/Drivers/workflows/`.

Arithmetic fixes `8255d4dc80988ce8490078cbbfa5f7f435817239` on main and
`c60defaa9a8f678b506cabe449c60a96fbca47cb` on recovery preserve exact negative
numbers and guidance midpoint comparisons; they are separate from the grader.

Keep these as leads at their existing step, not extra A7 tasks: same-fact
replay/member-edge enrichment needs source-rule adjudication if reached;
catalog tools must follow the count-free independent-identity-review ruling;
V2 production ownership/operating policy close later. The August test-collection
database read was real and fixed in fixtures; the earlier denial was withdrawn.
The source-routing owner was not replaced. Do not revive withdrawn suspicions
without new evidence. The full September 7 audit remains recoverable via §8.

### 1.7 Safe resumption

Follow [Orchestration.md](LeftOverSteps/Orchestration.md) for session launch,
worktree selection, runtime IDs, mailbox order, notification attachment,
goal reuse and the exact interrupt procedure. Its replacement prompts—not the
old one-use `CoreSessionPrompt.md`—are the startup instructions. Do not copy
historical session IDs or assume an old receiver belongs to a new session.

Read both current mailboxes: later receipts are in their archive chain, not
new project tasks, and notices from downtime are not replayed. The earlier
publication closed with Core 2176 replying to Codex 2180 in WAIT; re-read
rather than treating those numbers as current. An unfinished all-steps goal
does not override the owner's stop. No model call or roadmap advancement
follows merely from opening this file.

## 2. Design-status categories and settled scope

These categories preserve the design-to-build distinction behind the historical
records. §1.5 is the current execution list; the live roadmap owns each trigger.

* **Specified, still to build/prove:** production reader/identity, catalog
  finalization, remaining fact/link/read work, operations and rollout. Earlier
  internal writer and slice-menu code does not complete these integrations.
* **Ratified but not activated:** Admission Kernel v3.4 and the native tagged-
  filing design; operative mechanics are in BUILD §8.1/§8.2, original migration
  evidence in §7.1b. Their gates and dormant status remain in force.
* **Conditional, not automatic work:** OD-19, XC-16, model-role changes,
  caching/stability work and the broader OD-7 proposals, only at their existing
  reviewed triggers.
* **Owner choices only at their triggers:** optional metric text/action
  conditions, financial classification, later-channel charters and Track-C
  history-gap acceptance. Follow Steps.md's triggered-decision register and
  the active step, not an older OPEN list.
* **Already settled for the first release:** no fixed 786/796 catalog target;
  no cross-company slice comparison (FS-23), non-USD expansion, item-number
  taxonomy or third-party guidance; Step 12B's channel set is empty. Preserve
  later expansion questions as future work, not new approval requests.
* **Historical proposals only:** Bayes learner and Driver Genesis restructure.
* **Retired approaches stay retired:** Guidance replay, fixed-vocabulary
  Driver v1, eager/catalog-first live reuse, `slice=total`, alias layers,
  `long_range` scope, quiet `gp_UNDEF`, `evhash16`, cross-company slice
  recurrence, RavenPack vocabulary and materialize-all catalog sync. Model
  invocation follows the current runner policy in Steps.md.

The obsolete July OPEN/build lists are preserved in Git at
`bd361f7364297b71c9bbaa10ef5c725942069ca1:.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md`,
not repeated as current instructions. The generated status summary in
FINAL_DESIGN §10 predates later Steps.md rulings; it cannot reopen those choices.

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
Guard: `workflows/tests/test_perx_naming_residue.py`.
Historical rollout: the complete staged-V2 EXP-5 bundle was frozen on
2026-08-13 (`0dd71956`); the 2026-08-14 owner ruling then pre-authorized calls
within an independently reviewed bounded step. The former “STILL OPEN” and
“GO#1 uncalled” launch notes are historical; current EXP-5 work/results are §1.

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

## 6. Historical documentation issues — not a new backlog

The July consolidation's 24 stale-text findings and original missing-recipe
list remain in archived `CONSOLIDATION.md` §10.1 and BUILD §11. They describe
that snapshot; they are not all unresolved today. Old collision/hint/expectation
wording loses to the live rules, and “already built” in an old design sometimes
meant “specified,” not implemented. Current known failures are in §1.4;
remaining work and decision triggers are in §1.5/§2 and Steps.md.

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
| FS-05..24 | FINAL_DESIGN §5.2 | FS-09 separators also §5.1 · FS-14 menu + PIT · FS-15 kind ladder · FS-16/18 code-exact rules · FS-20 buckets · FS-21 member link · FS-22 RETIRED (row 37) · FS-23 deferred beyond first release (§2; Steps.md) |
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
| Open items | §1.5 remaining work + §2 settled scope/conditional choices; Steps.md owns current triggers | BUILD §11 retains design recipes; FINAL_DESIGN §10 is an older status mirror |

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

- **July consolidation closure:** the definitive result and tested hashes are
  in `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-16_phase5-final-run15.md`.
  That documentation phase is complete only if the record shows 10/10 PASS;
  it is not A7 or production qualification. Review rounds and owner decisions
  remain in the archived `CONSOLIDATION.md` §10.2/§16.
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
  recovery uses the current main communication instructions. That status
  consolidation did not authorize a new rule or roadmap resumption.
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
