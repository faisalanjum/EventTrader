# A7 grader: three-pass review and implementation plan

Status: THREE REVIEW PASSES COMPLETE — READY FOR OWNER VETTING.
This is not implementation authorization, a code approval, an A7 score,
or a claim that all requirements have passed tests.
Owner authorized analysis/planning only on 2026-09-09, after approving the
three-pass approach in conversation. Core stays paused. No new tests or model
calls are run during this review; only existing code, documents and evidence
are inspected. This temporary file is the only output being edited.

Decision: keep the existing grader architecture. Repair the bounded existing
owners in R1–R6, reproduce R7 before deciding its code change, then complete
the stated no-AI proof and independent review before the next model stage.
Sections 6–9 are the work order; appendices preserve exact evidence and
inventories for continuation after compaction.

## 0. Fixed scope and interpretation

Goal: the smallest complete, evidence-backed A7 grading path under the current
Step 1 requirements, with preserved outputs suitable for the later ordered
steps. Do not build a universal grader, production reader, identity service,
provider framework, scheduler, new proof framework, or later-step features.
Do not change a sample, key, score threshold or product meaning to improve a
result. Do not repeat a successful model call. Reproduce a claimed defect
before its eventual implementation; static concerns are not test results.

"Perfect" here means a decision-complete bounded plan, no knowingly omitted
required behavior, independent expected outcomes for the planned tests, and
explicit failure/uncertainty handling. It cannot mean a mathematical guarantee
that unseen code or future model output contains no possible error. Code
readiness and semantic/model qualification are separate gates.

Paths used below:

- MAIN = `/home/faisal/EventMarketDB` (read-only).
- REC = `/home/faisal/EventMarketDB-driver-recovery` (read-only in this task).
- H = `REC/a7_recovery/unit_1957/view/tree/harness_g1v3`.
- D = `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps`.
- E = `REC/a7_recovery/codex_a7_20260909` (previous frozen test evidence).
- Recovery branch = `recovery/a3-a7-verified`.
- Recovery HEAD = `1416bf946be4ef008f255bcef33ee14af387b455`.
- Recovery Git tree = `bc76fa84c09cdfbea6848a2c2bdd6ff940d82244`.
- Native-input candidate tree previously frozen at
  `28a8d99ff230fefbb858cab890e4ffbb9745cafc5388ae5b23720eff3ea8dc72`;
  an independent file manifest will be recorded below.
- E/CHECKPOINT_MANIFEST.tsv =
  `6563487f68778c272b81870feba3541c38c5d3f5b48bcd6f2599651072526ad7`.
- Core 1947 acknowledged Codex 1959 and is paused; no new mailbox instruction
  is needed or authorized for this analysis.

## 1. Review passes and evidence standard

### Pass 1 — reconstruct the actual code and requirements

Trace real entry points, imported and function-level dependencies, generated
launchers, saved evidence, finalization, scores and decisions. Read current
code rather than relying on comments or historic green totals. Then compare
with live step requirements and the product/experiment owners they cite.
Identify historic-only code and genuinely later work before proposing fixes.

### Pass 2 — adversarial correctness review

Challenge every required boundary with valid, malformed, missing, stale,
conflicting, repeated, reordered and interrupted cases. Distinguish a code
defect, unavailable test input, superseded test contract and unproved claim.
Each planned negative test requires a valid nearby control and an expected
answer independent of the implementation being tested. Reuse exact existing
proof where sufficient; a test that fails before its intended assertion does
not prove the behavior.

### Pass 3 — reduction and decision-complete handoff

Revisit each finding. Keep only changes required by current law or a
demonstrated current defect. Prefer correction at an existing owner to another
layer. Record rejected suggestions and reasons, the exact ordered work units,
test populations, stop conditions and release criteria. Do not turn code
tidying, unsupported possibilities, or historical file counts into blockers.

## 2. Main conclusions from the three passes

- `a7_g23_build.official_tier_decision` derives the producer/G1 population
  once, scores both required original arms and the union, and applies the
  three-state final gate. G2 asks about matched records; G3 asks about accepted
  unmatched records. G1 independently judges unresolved source-claim identity.
- These are separate required questions, not justification for three generic
  frameworks. G2/G3 reuse G1's existing capture/finalization lifecycle.
- The scorer's real route has writes disabled and a store that refuses a
  transaction. Production must not import this experiment harness; Step 3
  redirects the experiment to the eventual production reader owner instead.
- Old/current scorer coexistence was checked and cleared: the shared matching
  and routing helper bodies are identical. No consolidation is needed.
- R2 restores a stale accounting consumer to the already-existing full trace;
  R3 repairs a mutable source-context binding boundary; R4 reuses the existing
  no-replacement writer. None needs a new framework.
- R5 removes one G3 example answer. R6 makes the union threshold use exact
  counts. R7 gets a public-path interrupted-capture reproduction, with a code
  change only if the existing route does not already return a counted refusal.
- R1 repairs the proof environment and classifies all old failures. Every
  behavior change still needs its failing test before implementation; static
  reasoning here is not an executed exploit or a passing qualification.

## 3. Existing regression evidence: no blanket waiver

The previous comparison has 184 failed tests + 14 setup errors = 198 unique
failing/error identities, 905 passes, 2 skips and no collection errors on each
side. Zero new failures proves only that this patch added no failing IDs.
The full raw record and all IDs remain in E/COMPARISON.json and
E/regression_2/logs/attempt_codex_regression_2/REGRESSION_codex_regression_2.txt.

The independently read stopping causes are: missing imports 112, missing files
22, absent Node launcher 15, attempts to mutate read-only inputs 2, package/
freeze/era guard refusals 36, and assertion/helper/expected-exception mismatches
11. These total 198; they are not 198 proven application bugs. In particular,
89 checks stop on the same absent `driver.core.xbrl_attach` in the served sparse
test copy; the file exists in REC. Correct the isolated proof environment or
identify exact equivalent current proof; never loosen production checks or
simply declare the failures harmless because they predate the patch.

The complete per-test disposition is in Appendix C. These are classifications
of the first observed stopping cause, not proof that no deeper failure exists.

## 4. Authority, interpretation, and the later-step boundary

### 4.1 What was read and what governs

Read completely: AGENTS.md; Fiscal_Core_Review_Guardrails_2026-07-24.md;
Orchestration.md; Steps.md; step1.md; step2.md; step3.md; promptStandard.md;
CoreSessionPrompt.md. The guardrails are a continuity checklist, not a second
authority. CoreSessionPrompt.md contains an old one-use startup instruction;
it does not restart Step 0 or override the present owner-approved pause.

Read the purpose, prerequisites and scope sections of step4.md through
step14.md, against the complete sequence in Steps.md. This is a dependency
review, not a claim to have audited every later implementation requirement.
For the active grading decisions, read FINAL_DESIGN.md §§1–6 and the cited
meaning rules, FableExperimentWorkOrder.md §§1.5–1.8 and EXP-5/EXP-6,
FableExperimentPlan.md EXP-5 Addendum A, and the old scoring specification.
The old specification is historical: its retired matching or item-shape rules
cannot overrule the live amended Step 1 and work order.

Order of interpretation: the owner's explicit current instructions, then
the live ordered plan and its explicit amendments, then its cited product
and experiment rule owners. Archives prove what was instructed or done, not
new product law. A real conflict that affects safety is a named stop, not a
silent choice. The owner's explicit 6,000-call soft-target ruling supersedes
the old global forced-abort wording; it does not permit unplanned or uncounted
calls, new tiers, or bypassing the current package's bounded call plan.

### 4.2 What A7 must leave for the rest of the project

| Step | Required connection to this review | Work explicitly not added to A7 |
|---|---|---|
| 1, A3–A6 | Reuse accepted source, key, reader-kit and launch owners; a corrected key is separately reviewed and frozen | Re-run accepted drafts or reopen accepted work without a demonstrated dependency defect |
| 1, A7 | Trustworthy extraction experiment: exact saved answers, complete accounting, independent identity/meaning checks, real no-write route, honest scores | Universal grader, production deployment, automatic prompt tuning |
| 1, A8 | A passing A7 supplies text facts for the text-versus-tagged-filing test | Start twins before A7 passes; widen beyond lawful same-report pairs |
| 1, Lane B | Its earlier priority pause stays visible; it still must close under its own gates before Step 1 closes | Reopen NAME-16/catalog work while repairing A7 grading |
| 2 | Reconcile results and freeze only measured roles/settings/decisions | Treat a partial A7 code checkpoint as Step 1 completion |
| 3 | Move the reviewed reader/prompt owner into production; harness imports that production owner; replay exact four-field saved replies | Build a new reader now, make production import the harness, or rewrite raw replies through an adapter |
| 4 | Independent production identity/admission system | Add identity services or its model qualification to this experiment |
| 5 | Full Fiscal V2 no-write route and live company/calendar proof | Repair the whole Fiscal channel or silently substitute a new calendar into the frozen exam |
| 6 | Approved atomic V1→V2 no-write switch | Activate or partly switch production during A7 |
| 7 | Catalog refresh and identity repairs | General naming cleanup or catalog reclassification |
| 8 | Separate fact/enrichment/read/verdict calibration | Add future role-specific judges to G1/G2/G3 |
| 9A/9B | Fiscal finder qualification; real-record gate after Step 11's lawful first records | Live record creation or its 150-case gate now |
| 10 | Minimal production operations after its prerequisites | New scheduler, service, retries, queues or monitoring framework for A7 |
| 11 | Shadow and then separately gated real writes/activation | Database writes or deployment from a grader pass |
| 12A/B/C | Ordered consumer cutover, empty first-release later-channel scope, then native tagged-filing path | Extra channels, premature integration, old-Guidance cutover |
| 13 | Whole-project evidence closure | Claim all steps are done when A7 is done |
| 14 | Dormant until a future explicit ruling | Cost/tier optimization or alternative model work |

Existing shared numeric, period, identity and routing code must be used now.
Fixes to a shared production rule belong at that shared owner, with its tests;
test-run persistence or grader orchestration stays in the experiment. This is
the direct-transfer boundary: no duplicate production semantics now, but also
no claim that the whole experiment runner should become a production service.

## 5. Actual path and one owner for each rule

In plain words: verify the saved answer, identify which source fact it refers
to, check whether its meaning is right, run the real safety checks, then count
everything and decide whether the experiment passed.

| Boundary | Existing owner and entry | Input → required output |
|---|---|---|
| Producer identity | `a7_prepared_run.current`; `a7_g1_build.run_of` | Accepted external A6 pin + run → validated current run, or refusal |
| Raw answer preservation | `raw_transport`; G1 capture/binding functions | Actual returned bytes + exact attempt → immutable bytes, receipt and identity |
| Producer reply | `a1_reader.read_one` | Four-field reply + sole trusted input → validated facts/abstention/proposals; no invented provenance |
| One scheduled-answer record | `a7_g1_build.materialize` | Full frozen schedule + every saved attempt → one trace row per scheduled slot, including no answer |
| Key/reference evidence | Existing A4 signing/lock owners; `a7_key_correction.current_key`; `a7_reference_inventory` | Approved key → exact accepted fact inventory and raw reference evidence |
| Automatic identity matches | `driver.core.fact_match.match_facts`; current scorer's eligible/position helpers | Complete canonical records + exact source locators → unique one-to-one matches; all unresolved rows stay visible |
| G1: unresolved identity | `a7_g1_build` event questions, parser and `validate_merged` | Two blind relations → only agreed, uncontested one-to-one links; no value/name shortcut |
| Runtime execution and restart | `a7_g1_workflow_gate`; G1 freeze/publish/preflight/capture/finalize; `grade_batch.js` | Pinned candidate and ordered receipt → bound attempted, completed, invalid, failed and uncalled states |
| Durable completion | `audit_worker_access.g1_state_audit`; `a7_g1_complete_v2.evidence/complete` | Official state + transcript + exact whole raw answer → completed evidence, not merely parseable JSON |
| Grading populations | `a7_g23_run.populations` | Verified producer + G1 completion → final matched-pair G2 rows and route-accepted unmatched G3 rows |
| Source context | `a7_g23_build.load_verified_inputs/verified_event_context` | Run-bound source manifest → that event's exact text/calendar/menu; R3 repairs the remaining mutable-handle gap |
| G2: matched-fact meaning | `meaning_packet/read_meaning_reply/reconcile_meaning` | Every matched pair + raw evidence/context → per-aspect agreed true/false, otherwise unresolved |
| G3: accepted extra facts | `extras_packet/read_extras_reply/reconcile_extras` | Every accepted unmatched record + own-event raw evidence and comparison records → duplicate/key_miss/unsupported/null |
| Production checks | Current scorer `route_reply` → `driver_write_cli.run_event(..., enable_writes=False)` | Produced facts and producer-derived store, never key-built store → real route results and refusal codes |
| Complete output accounting | `a7_conservation`, consuming the materialized trace and route-owned results | Each source input and fact branch → exact outcome with preserved split/fusion/union origins; R2 restores this |
| Numerical score and decision | Bound `score_exp5_current.score_arm/score_union/final_gate` | Exact counts + qualified judgments + route outcomes → FAIL, INCONCLUSIVE, or PASS under unchanged bars |

G2/G3 reuse the G1 lifecycle. Their separate question types do not justify
separate transport engines, receipt formats, retry controllers or scorers.
Official scoring derives the population once per evaluation, validates G1
once, routes each actual `(arm, event)` once and validates each distinct
completion once. Preserve that existing evaluation-local reuse.

### 5.1 The real restart chain that must be executable

`prepared run → frozen candidate/prompts → root → reserved segment → published
script/receipt → preflight → actual Workflow return → separate raw captures →
official state/transcript audit → finalization → whole-run digest → completion
→ official score`.

Every arrow must execute from the served durable package, including imports
inside functions, generated JavaScript, key/candidate/receipt/finalization
owners and the production route. An import-only check or preloading a missing
dependency from the host is not this proof. Use the existing isolated runner
and map; do not build a new package manager or dependency system.

The bounded TEST proof runs the actual generated JavaScript with a fake model
return, then actual capture, audit, finalization, cold reload and scoring. It
must include both nonempty G2 and G3, not only a run where there are no meaning
questions. TEST judgments test plumbing, not semantic qualification.

Here a positive control means the machinery reaches the correct expected
decision, not that every fixture must return PASS. A nonempty G3 fixture may
correctly end in FAIL for unsupported/duplicate acceptance or INCONCLUSIVE
for a key miss. Also retain a genuinely clean passing fixture; do not weaken
the gate to manufacture a PASS for an intentionally unsafe test record.

### 5.2 Counts: derive them, never restore an old number as law

- Producer denominator = all scheduled `(packet, original arm)` slots in the
  accepted current plan, including controls and uncalled slots.
- Gold denominator = all current locked `du_worthy == true` facts, not just
  called events, matched facts or parseable replies.
- A grading *question* is one required decision. A *batch* groups questions
  into a prompt. A *lane* is one independent grader's scheduled call for that
  batch. Questions, batches, lanes and attempts are different counts.
- G1 comes from all unresolved identity populations after automatic matches.
  G2 comes from all final matched pairs after G1. G3 comes from all remaining
  accepted unmatched records after the same G1 decisions and actual route.
- Each required batch has two independent grader lanes. Count every authorized
  retry separately; empty question populations require zero fabricated calls.
- Count original arms and their lawful same-tier union separately. The union
  invents no new producer responses and never erases an original arm's error.
- The earlier 82 launched lanes, 206 historical required lanes, 156 old
  producer calls, and the 392-call TEST fixture are historical measurements,
  not the next run's denominator. Compute new totals only after its key and
  producer responses determine them.

## 6. Pass 1 findings and exact minimal remedies

Evidence labels: **OBSERVED** = visible in an existing raw executed result;
**STATIC** = reachable code and independent reasoning, not a new test result;
**CLEARED** = investigated and not a reason to change code. All behavioral
changes below still require a failing reproduction before the fix.

### R1 — Repair the served test/dependency setup, not production checks

Evidence: OBSERVED 198 stopping failures/errors (Appendix C). The current
regression map's line 68 serves `driver/core` from
`REC/a5_recovery/unit_1758/view/driver_core`, a sparse 16-file historical copy.
The current production tree has required missing modules. Native proof
`unit_1942/ledger/s2_g23_native_1942.py` preloads the recovery validator before
the harness, so that proof alone does not establish normal cold import order.

Action:

1. Keep the accepted historical A5/A6 snapshots immutable. Build the next
   TEST view with one explicit current production source root and its complete
   callable closure. Pin every served file and relevant generated artifact.
2. Include normal, nested and dotted imports, function-local imports, actual
   callbacks and generated-script reads. Use existing code/runner discovery,
   not just the 80-path import-only checkpoint or a hand-picked import list.
3. Run a positive current producer→G1→G2/G3→score path in a cold interpreter
   before paying for a broad regression. No host pre-import masking.
4. Fix test-local historical inputs and obsolete API expectations under
   Appendix C. An old fixture must either be valid in its explicit historical
   scope or have equivalent current behavioral proof. Do not monkeypatch the
   era/lock/signature guard globally to turn a historical fixture current.
5. Mutation fixtures copy only the needed input to a fresh durable writable
   TEST location. Never modify a frozen real source, receipt or raw answer.

The owner-requested fix `8255d4dc` is already present as cherry-pick
`c60defaa9a8f678b506cabe449c60a96fbca47cb`; the four changed files compare equal
to that commit. Do not cherry-pick again. Current validator SHA is
`4b90aa83595c48e530914c748c00c6c93036559782d7479138cce6eeb7a5dff5`;
the sparse old validator differs (`d7bdb4cfaf2f9aa2cc9cca7e974d8622e354b26ea25ed6235714021daa282f48`).
Serve the right current owner and run its exact-negative-number and guidance-
movement regressions. Do not rewrite historical A5 pins to conceal the change.

Done when: the actual cold path works, every first stopping cause has a named
disposition and the final in-scope suite has no unexplained failure. Equality
with the old failing baseline is not enough.

### R2 — Restore complete accounting from the existing saved-answer trace

Evidence: STATIC code disagreement with Step 1 A7 item 9, plus OBSERVED
`test_a7_trace_1471::test_every_status_and_route_outcome_is_conserved_exactly_once`
fails because `_branches_of` is missing.

`a7_conservation.contributions` still unpacks `effective_slots` as
`(ordinal, key, path, attempt)`; the current result is
`(ordinal, key, attempts, selected)`. It would open a list as a path. It also
reparses answers and walks the schedule again. `_terminal_of` reduces a split
to its strongest outcome, losing the other fact outcomes. Totals use the old
`G.REQUIRED` constant and derive arms from observed replies, so an uncalled
arm is not a complete denominator. Archive CODEX 1471/1472 already required
the one-trace/branch behavior; no surviving `_branches_of` implementation was
found in the searched recovery/experiment copies.

Action:

1. Make one bounded search for an exact surviving patch of this named owner
   in its durable workflow/transcript/archive history. Reuse it only after
   checking its dependencies and current contract. Do not restart a general
   A3–A7 recovery hunt or block on reconstructing every historical file.
2. Make `contributions` consume `G.materialize(run)` and its trace only.
   Preserve every scheduled packet, selected answer and all attempts,
   source/arm/packet identities, exact raw references, facts, abstentions,
   continuity proposals, and event fact positions.
3. Extend the existing conservation document with branch rows: one row per
   fact occurrence with its original position and route-owned outcome; a
   zero-fact input has exactly one terminal. Keep the packet row as the
   parent identity, not as a substitute for the branches.
4. Read route results through the existing scorer's `_rows_for_event` and
   route index map. Preserve split, dedup, fusion and union origin links.
   Never select the strongest outcome, infer a terminal from absence, or
   reroute an already-derived event merely to count it.
5. Derive expected packets/arms from the actual frozen schedule. Required
   arms with no answered slots still appear. Check exact identity sets,
   not count equality alone. Unknown/missing route outcomes create named
   blocking rows, not a quiet `zero_fact_terminal` or generic `other`.
6. Keep invalid, transport-refused, uncalled, explicit abstention, skipped,
   accepted/would-write, parked and rejected outcomes distinct. In this
   no-write test a route label `written` does not mean a database write.
   Derive the permitted route outcome vocabulary from the route owner; do
   not create a new semantic status engine.

Tests first: the real public `C.terminals(run)` with a lawful mixed split;
one arm wholly uncalled; all missing; invalid primary/valid retry with both
raw attempts; abstention only; lawful zero-fact producer outcome; duplicate,
fusion and union with all origins; a removed and an unknown route row. Verify
full identities, not just totals. Warm the materialized trace, seal evidence
reparse/schedule rewalk, then call the actual downstream entries with valid
current G1/input handles. Preserve legitimate whole-run digest reads.

For avoidance of doubt, the reader requires nonempty facts XOR exactly one
abstention. A continuity-only reply with neither is not a lawful exception.
"Zero-fact terminal" here means correct accounting for a valid abstention or
an invalid/refused/uncalled input; it does not authorize an empty successful
reader reply. Use the current explicit run handle, not the old default path.

Done when: every scheduled input and every produced fact occurrence is
accounted for exactly, no successful answer is reparsed or re-called merely
for accounting, and every missing/invalid outcome blocks the appropriate gate.

### R3 — Do not trust mutable rows under an old verified-manifest label

Evidence: STATIC reachable public path. `load_verified_inputs` returns a
mutable dictionary. `meaning_packet` checks its claimed manifest hash against
the run, but `verified_event_context` then trusts the dictionary's path/hash
rows. Changing both to different same-source bytes leaves the old claimed
manifest identity intact. `R.write(..., inputs=...)` is the supported public
entry and accepts that handle. Hashing the resulting prompt later proves the
wrong prompt was saved; it does not bind it to the original source manifest.

Action: keep `load_verified_inputs` as the one authority. Carry the original
manifest path in the existing input descriptor. At the context-loading
boundary, require the validated producer identity, re-read/verify that
manifest against `run.a5_manifest_sha256`, and use its derived source row,
not caller-modifiable cached rows. Retain the existing row fields for caller
compatibility, compare them exactly with the loader's new derivation and
refuse a mismatch before rendering; they are never the source of authority.
`meaning_packet` already has the run to pass. Root/path aliases are allowed
only when the approved bytes still match.
Do not add signatures, object registries, capabilities or a new context store.
Do not weaken source-ID checks. If repeated manifest reads are material,
reuse privately within the already-existing evaluation only after measurement;
do not pre-emptively build another cache.

Tests first: two independently valid input sets for the same source ID but
different text/calendar/menu; normal handle succeeds, modified row path+hash
under the original identity refuses through the public nonempty-G2 freeze;
foreign manifest, changed bytes, missing source, wrong event and missing file
refuse. Identical bytes under a valid durable alias remain a positive control.
Check both cold and existing warm paths. No model call is needed.

Done when: no supplied row map can replace the source bytes the producer was
frozen to read, and the normal actual packet still builds unchanged.

### R4 — Publish active consumed artifacts atomically and without replacement

Evidence: STATIC direct writes in G1 `write` and G23 `write/write_kind` use
`open(..., 'w')` for prompts and candidates. `B.write_atomic` checks existence
then renames, which can replace a file after the check. The outer fresh-run
directory protects ordinary invocations but not these supported public writers
or a partial interrupted build. Work-order §1.6 requires atomic consumed
artifacts; saved approved bytes must not be overwritten.

Action: use existing `raw_transport.write_new`, which already publishes with
fsync and a no-replacement link. Write prompts first and the candidate last;
keep the existing fresh-directory rule. Use the same owner for active G23
sidecars/reference publication where those paths can replace an approved file.
Do not mass-edit historical-only writers or build a transaction manager. A
partial candidate build is not evidence of a launched call; retain it and use
a fresh destination. Completed raw model answers are reused from their exact
durable identities, never regenerated to make a directory look clean.

Tests first: fresh write and re-derive control; second write against the same
destination leaves every original byte unchanged; interrupted prompt writing
does not expose a complete candidate; two independent publishers cannot replace
one another's candidate; restart cannot credit a partial file. Distinguish
immutability of approved artifacts from legitimate existing state progression.

Done when: active public writers cannot truncate or replace accepted bytes,
and downstream consumption still requires a complete verified candidate.

### R5 — Remove the G3 example answer, not its meaning rules

Evidence: STATIC `extras_rules` sets the sample bucket to `buckets[0]`, which
is `duplicate`. This unnecessarily shows an answer. The owner's instruction
requires generic workflow prompts without example answers that anchor a model.
G2 already uses schema placeholders.

Action: change only that value to a schema placeholder listing the existing
legal bucket choices plus null, derived from `extras_buckets`. Keep the actual
parser, uncertainty rule, source boundary and same-event comparison evidence.
No broader prompt rewrite, additional examples, or semantic word lists.

Tests: legal output vocabulary still comes from the scorer; placeholder is
not an answer; no answer-key conclusion enters the evidence; valid, null,
unknown-bucket and extra/missing-field replies retain their current outcomes.
Generated prompt hashes change, so publish a new candidate; never edit a
frozen prompt or rerun an already successful unchanged call.

Done when: G3 shows the required shape without choosing an answer for the model.

### R6 — Apply the union recall threshold to exact counts

Evidence: STATIC plus independent arithmetic. `score_arm` returns displayed
`recall = round(recall, 4)`, and `final_gate`'s `_leg` reads that display value
for the stricter union bar. `440/449 = 0.979955...`, below 98%, but displays
as 0.9800. The arm's own 95% PASS can therefore become an incorrect union
98% pass if the originals are below their single-run bar and other checks pass.
The old 209-fact key does not hit this boundary; no live requirement caps every
future admitted key below 449 facts. This is a small current-owner error, not
a reason for a new scoring framework.

Action: `_leg` uses the existing exact `matched` and `gold_n` counts for its
recall comparison; retain four-decimal values only for display. Use integer
cross multiplication for 95/100 and 98/100, with a nonempty denominator.
Derive that rational comparison from the existing threshold argument; do not
add a second list of thresholds or modify the historical pinned scorer.
Update test result builders to include the real score-result counts, not a
fallback to rounded values. Do not change any pass bar or other metric formula.

Tests first: actual score result with 440 of 449 matched, all other axes
lawful, single arms below 95% → no tier pass. Include an exact 98% union
control, immediately below/above both bars, zero denominator and the existing
safety/unknown veto combinations. Independent expected outcome is integer
arithmetic, not the gate being tested. The API accepts only real score-result
shape; missing counts must not silently restore the rounded path.

Done when: rounding cannot change a pass/fail decision; old displayed reports
remain displays and previously accepted exact cases still behave correctly.

### R7 — Account for a missing final error capture instead of indexing past it

Evidence: STATIC public finalizer path. `audit_worker_access.g1_state_audit`
indexes `expect['captures'][position]` for a last official row in error state
before its later result/final/capture length check. A missing corresponding
capture can raise IndexError. `G.finalize_segment` calls this audit directly;
its preceding receipt/preflight checks do not establish that capture count.
This is not a proven wrong acceptance; it is missing named failure accounting.

Action: first reproduce with an otherwise lawful interrupted/error-tail
fixture through `G.finalize_segment`. If the actual enclosing supported path
already produces the required named refusal, retain the test and make no code
change. Otherwise move/reuse the existing length/shape validation before the
indexed access. Return the existing problems/refusal structure, preserve the
attempt/raw evidence, and block completion. No blanket exception swallowing.

Tests: lawful last-error capture; last-error row with zero/short captures;
ordinary completed rows with missing captures; extra capture; non-last error;
matching restored capture. Verify correct counts and no credit, not just that
an exception occurred. Do not force a model retry to repair missing evidence.

Done when: interrupted evidence fails closed with a visible reason and can be
recovered from durable evidence without fabricating completion.

## 7. Pass 2 — Counter-review, rejected findings and adversarial proof

### 7.1 Challenges to the proposed work

| Challenge | Result after checking actual callers and live law |
|---|---|
| Could R1 be waived because baseline has the same failures? | No. That only proves no new failing IDs. Many tests never reach their assertion; actual no-write routing still needs its callable modules. |
| Does R2 duplicate a working accounting system? | No new system is proposed. The existing materialized trace already contains the necessary data; the stale conservation consumer must use it. |
| Is the mutable-input issue only an arbitrary private-helper attack? | No: the documented public G23 writer accepts the handle, and a same-source replacement passes its current hash-label check. A failing public-path test is still required before changing behavior. |
| Doesn't a fresh outer directory make R4 irrelevant? | It protects that invocation but not the callable writers or partial publication. Reusing the existing atomic writer closes the real boundary without a new mechanism. |
| Is a 449-fact threshold test speculative scope? | The scorer accepts populations of that size, fresh key size is derived rather than capped, and the rule is exact. Fix the existing comparison, not the domain. |
| Does R7 need a global error framework? | No. It is one ordering/length-check issue; a named existing refusal is enough. |
| Does all grader code need to be rewritten after these findings? | No. The correct matching, blind reconciliation, route and lifecycle owners remain in place. |

### 7.2 Investigated and cleared: do not turn these into work

1. **Old/current scorer coexistence.** Full diff and AST comparison found five
   changed functions (`invalid_response_stats`, `passes_official_bars`,
   `score_arm`, `score_union`, `final_gate`) and the seventh meaning aspect.
   The matching, identity, union construction and routing helpers used by the
   current path are identical. The bound current scorer supplies current
   scoring law; historical pins may retain the old scorer. Do not consolidate
   files merely because two versions exist.
2. **Seventh G2 aspect.** `record_matches_source` protects every production
   field, including wrong-source meaning not exhausted by narrower axes. It
   is required by zero confirmed-wrong accepted facts. Do not restore the old
   six-aspect test shape or remove it to make old tests pass.
3. **Known wrong plus unknown.** A confirmed false meaning aspect remains a
   safety failure even if another aspect is null/disputed. Unknown evidence
   alone remains inconclusive. Preserve this distinction; do not average votes.
4. **G1 relation handling.** Both graders must agree; contested degree/multiple
   identity candidates block credit. No observed basis for another matcher.
5. **Compact versus original key index.** `meaning_packet` already maps the
   scorer's accepted-row index back through `accepted_positions` for reference
   lookup. Do not redo the earlier index fix.
6. **Historical quote overrides/key ledger.** The approved-current reference
   path derives from its signed packet/fact evidence and does not apply old
   span overrides or the old v9 correction ledger. Historical frozen data is
   not automatically semantic hardcoding. Do not delete or apply it to a new key.
7. **Private bool/index concern.** Official reply parsers already reject bool
   and out-of-domain indices. Do not add duplicated checks to every internal
   helper unless a supported bypass is reproduced.
8. **Materialization cache.** It validates run identity before reuse, checks
   drift after reads and returns a deep copy. Preserve it; do not invent a
   global cache/signature registry. Private frozen reference reuse alone does
   not allow changed disk bytes to become new accepted truth.
9. **Three-field internal replay callback.** The staged production bridge is
   not the raw reader contract. The raw four-field reply is preserved. Step 3
   owns replacing this bridge with the adopted reader; no new raw adapter now.
10. **Repeated derivation.** Official tier scoring already shares the G1,
    route and completion derivations inside an evaluation. Do not optimize it
    by weakening revalidation across different evaluations or different pins.
11. **G3 full G2 contract.** No proven requirement to paste the entire G2
    field-validation prompt into the extras task. G3 already receives raw
    reference cards, the record's bound quote and same-event other records.
    Unknown source support stays null; a possible key miss blocks the result.
12. **Transcript stop marker.** Multiple response groups are handled by the
    existing transcript owner and official completion state. A new rigid
    single-marker rule would reject lawful recovery shapes. Do not add it.
13. **Historical calendar discrepancy.** Do not silently replace frozen exam
    context with a new live calendar. Step 5 owns the full Fiscal/calendar
    proof. A discovered erroneous current grading input must instead follow
    explicit source/key correction, with new pins, never hidden normalization.
14. **Counts and cost.** File counts, old lane counts and the global soft
    target are not correctness criteria by themselves. No repeated model call
    or new bookkeeping service is authorized just to produce a nicer count.

### 7.3 Required test matrix — reuse proof before adding tests

For each row, map existing exact tests/raw evidence first. Add only uncovered
cases; no redundant all-pairs expansion across unrelated dimensions. Finite
closed domains get complete coverage; open text/number domains get required
real examples plus boundaries and mutations. Expected results come from
frozen source evidence, independently constructed records or arithmetic.

| ID | Boundary and cases | Required observation / independent oracle |
|---|---|---|
| T01 | Current run identity: correct pin; changed run/key/prompt/manifest/runtime/era; missing required pin; historical fixture before/inside/after scope | Correct current control accepts; every altered identity refuses at the actual boundary; historical allowances do not leak |
| T02 | Four-field reader: all required keys; extra/missing fields; wrong source; empty/multiple abstention; facts plus abstention; valid split; proposal-only and malformed proposal; null/bool/index types | Exactly live one-item contract; no fact or proposal survives an invalid envelope; raw unchanged |
| T03 | Numeric/locator boundaries: signed high-precision negative values; Decimal/string/exponent forms as admitted; value/scale/evidence triples; wrong quote/part/occurrence; repeated equal quotes; percent/points/per-unit; exact/range/open bounds | Independent decimal arithmetic and exact source spans; no float rounding or value-only identity |
| T04 | Full producer schedule: answered/invalid/refused/uncalled, one wholly missing arm, selected retry with all attempts, controls and proposals | Exact expected identity set from the plan; every attempt counted; R2 branch accounting complete |
| T05 | Matching: order-free exact matches; same value/different claim; same name/different locator; duplicate gold, duplicate producer, canonical equal variants; reordered input; compact/original positions | Unique full-record matches only, no fact credits two key facts; duplicate/key uncertainty stays visible |
| T06 | G1 two relations: agreed link/no-link; null/disagreement; one-to-many/many-to-one; missing/extra/duplicate questions; invalid indices; all supported answer forms | Only agreed uncontested pairs are credited; every unresolved question accounted; nearby valid permutation control |
| T07 | G2 seven aspects: all 3×3 pairs of true/false/null per aspect; missing lane/question/aspect; one agreed false beside another null/disagreement | Exact agreement per aspect; false safety evidence is not lost; no majority, default or semantic retry |
| T08 | G3 all existing bucket/null pairs, repeated records, same record in two asked questions, other event records, unsupported quote, key miss | Same-event evidence only; duplicate→violation, unsupported accepted→wrong-accept failure, key_miss/null/disagreement→unresolved; never silently add gold |
| T09 | Prompt isolation: opaque IDs; raw reference evidence; no key labels/conclusions; no realized returns/future context; text attempts to issue instructions; correct event/calendar/menu | Exact source bindings and workflow boundary preserved; schema placeholders not example answers |
| T10 | Context-handle substitution and complete nonempty G2 freeze, cold/warm, same-source different input, valid aliases | R3 public-path reproduction and corrected refusal; correct original packet bytes retained |
| T11 | Real no-write route: split/fusion/duplicates/conflicting fact types, accepted/parked/skipped/rejected/missing result, own union route | Same production validators/period/unit owners; write attempt trips the existing no-write store; all origin/index identities remain visible |
| T12 | Transcript/result integrity: blank/malformed/refusal/error; terminal tail versus whole answer; valid multi-piece chain; reordered/duplicate/off-receipt/foreign agent or prompt; authorized native input versus wrong/missing payload | Whole raw bytes and official state/receipt identity must agree; valid JSON alone earns no credit; valid controls use genuine allowed transcript shapes |
| T13 | Retry/restart: uncalled tail, invalid primary then one valid retry, successful primary, two invalid replies, valid semantic null, same cached answer, no-progress/permission stop | At most the frozen permitted retry; never repeat success or retry semantic uncertainty; no third attempt; no duplicate credit or hidden miss |
| T14 | Error-tail missing/short/extra capture and restored lawful capture | R7 named refusal/accounting through actual finalizer; no crash mistaken for completion |
| T15 | Publication: fresh candidate, existing destination, interrupted partial write, competing publication; then cold resume | R4 old bytes unchanged, incomplete artifact unconsumed, fresh lawful candidate re-derives; raw success reused |
| T16 | Official artifact binding: foreign G1/G2/G3 completion, changed owner/hash/input, incomplete/extra population, missing required union/original, zero G2 or G3 legitimately owed | Full rederived population matches exact supplied completions; zero owed ≠ missing owed; no unchecked verdict map accepted |
| T17 | Score bars and precedence: 95%/98% exact boundaries, 98% pooled code/value accuracy, 95% state, 10% parks, 2% invalid, zero wrong lane/wrong accept/duplicate; zero denominators | Independently calculated counts/ratios, FAIL safety veto first, then INCONCLUSIVE missing evidence, then lawful recall OR; R6 no display rounding |
| T18 | Union/original reliability: union has own route, keeps both origins, same-tier only, original error cannot be rescued, key-linked versus diagnostic abstention | Formula unchanged; same input occurrence not double-credited, wrong originals still veto; every missed gold remains in recall denominator |
| T19 | Source→new key→producer→G1→G2/G3 real lifecycle with deterministic TEST replies and nonempty G2/G3 | Actual prepare, generated launcher, capture, source/final key lock, audit, persist/reload, score; missing native input refuses with nearby restored control |
| T20 | Final replay of exact available real evidence and full affected regressions in clean served snapshot | Existing real success hash unchanged; all 35 unlaunched source events remain missing; no synthetic answer described as real evidence; no unexplained failures |

The seven current G2 aspects are derived from the bound scorer at execution,
not maintained as a second schema in test code. The 3×3 matrix is nine
possible two-grader outcomes for each aspect; its expectation is simple exact
agreement, with the separate false-safety veto tested at the final gate.

Mutation checks must remove or invert the specific protection being claimed,
not merely alter a filename that triggers a different guard first. For every
changed owner: reproduce the failure, show the positive control, apply the
small fix, show the new negative test catches a removed/inverted fix, restore
the reviewed version and rerun its control. A mutation counts only if it
reaches the intended assertion. No blanket mutation percentage or new mutation
framework is required. Existing 204 input/carrier mutations are reused only
where their tested bytes, inputs and route are unchanged.

## 8. Pass 3 — Smallest complete work order

### 8.1 Scope reduction decisions

Keep R1–R6. R7 requires its actual public-path reproduction first; if the
existing path already gives the required counted refusal, keep the test and
cut the code change. These are bounded repairs/verification of current A7
owners. They do not authorize every hypothetical edge-case fix.

Cut: scorer consolidation, mass prompt rewrites, historical file cleanup,
new schema/validation layer, generic dependency resolver, stronger object
signatures, new retry scheduler, new evidence database, production reader or
identity work, full catalog audit, Step 14 optimization, redundant AI calls.

Do not use the 198 stopping failures as 198 implementation tasks. Repair the
small number of setup/fixture owners and rerun. A newly reached real behavior
failure is handled at its existing rule owner with a class-wide test; it is
not permission for an unrelated cleanup. A proposed change needs its live
requirement, failing scenario, smallest owner and necessary proof in this
file before it enters the work order.

### 8.2 Ordered work units after the owner vets this plan

| Unit | Exact deliverable | Exit check before next unit |
|---|---|---|
| W0 — Snapshot | Verify HEAD, branch, dirty/untracked inventory, current code/input pins and Core pause; choose a fresh durable TEST output inside REC | No overwrite; no main changes; no extra watcher/goal/Core process; reviewed baseline identities recorded |
| W1 — Usable proof environment | R1 current callable closure and test-local fixture repair; valid cold end-to-end control | Production modules served from intended current pins; no pre-import masking; positive reaches real route and nonempty G2/G3 |
| W2 — Complete accounting | R2 failing tests, trace-consuming fix and focused class-wide proof | Full schedule + branch/origin identity sets reconcile; no reparsing/re-call; all missing/error outcomes visible |
| W3 — Evidence boundaries | R3 and R4 failing tests and minimal existing-owner fixes; R7 reproduction and only needed guard repair | Trusted input cannot be substituted; accepted files cannot be replaced; error-tail evidence gets counted refusal |
| W4 — Prompt/decision precision | R5 schema-only G3 change; R6 exact-count threshold fix | Existing semantic rules/bars unchanged; generated prompt re-frozen; independent threshold tests pass |
| W5 — Complete no-AI qualification | T01–T20 gap closure using existing proof and new targeted tests; actual generated-lifecycle TEST run; current 31 harness modules + full affected dependency tests | No unexplained in-scope failure; no skipped required nonempty G2/G3 path; meaningful mutations reached intended checks |
| W6 — Review and code checkpoint | Freeze exact files, served map, generated artifacts, commands, raw stdout/stderr/exits, tests and inventory reconciliation; independent review | Only the complete verified code checkpoint may be staged/committed/pushed; no claim A7 has passed |
| W7 — Source/key evidence | Resume remaining lawful source review and key adjudication using saved success; separately freeze new approved key and exact experiment plan | Every source result qualified/accounted, inventory reconciled and A4 signing/lock owners pass; no unresolved key issue carried into scoring |
| W8 — Actual A7 | Fresh authorized producer sample under named correction, then G1, final G2/G3, exact official scoring and independent review | All A7 bars and evidence gates met, otherwise explicit FAIL/INCONCLUSIVE; A8 never starts on that result |

The implementation candidate is a fresh durable derivation of H, using the
existing snapshot/boundary tools, not an in-place edit of its reviewed frozen
history. Keep all test outputs inside a fresh REC directory. W1's positive
control establishes the dependency/lifecycle path; it does not demand that
the known R2 accounting failure be fixed before W2 can start.

Only one bounded task is active. Do not edit the measured code while a test
run is using it. Run focused tests during each change, and one complete final
affected regression on the frozen candidate; rerun affected coverage after
any subsequent change. The previous comparable run took about 10.6 minutes;
that is evidence for suite duration, not an estimate that all repair work is
ten minutes. Do not advertise another unsupported rolling completion ETA.
At each checkpoint report completed unit, concrete remaining unit, actual
blocker if any, and an estimate based on the just-measured work rather than
file counts or repeated guesses.

### 8.3 Required final test population, not a green-count shortcut

Start with all 31 current `H/test_*.py` modules listed in Appendix B; the old
30-module regression omitted `test_a7_g23_lifecycle_1464.py`. Its historical
fixture must be adapted or equivalently covered, not simply left excluded.

Add the complete existing test modules for every reached/changed production
owner and every external source/key/receipt/finalization dependency, selected
from live imports, callback reads, changed-file references and existing test
collection. This includes the already cherry-picked negative-number and
guidance-classification tests. Record the exact collected test IDs and command
before execution. Do not run unrelated experimental/model suites or broad
database jobs. Any required real-data claim uses preserved bound real
evidence or a read-only query only when the decision actually needs live data.

For each old failing ID Appendix C must end with one of:

- current test passed after setup or minimal behavior repair;
- historical-only contract isolated and passed in its lawful historical scope;
- obsolete test replaced by named current positive and negative/mutation proof
  of the same required behavior, with the removed expectation explained;
- explicit unresolved current requirement, which blocks code readiness.

Never declare the last category harmless, map every failure to "fixture",
or count an import/setup refusal as proof of the target behavior. Preserve
original raw logs and failed attempts beside the eventual passing proof.

### 8.4 Implementation stop and publication rules

- This planning approval does not authorize coding; return this completed
  plan for the owner's vetting first, as requested.
- During later implementation, stop the current work unit for an unknown
  authoritative rule, required identity drift, missing necessary evidence,
  or a change outside A7. Do not silently widen scope or manufacture a pass.
- No database write, live activation/deployment, destructive Git operation,
  Core launch/stop, new watcher, or production change is a normal A7 repair.
- Use the recovery branch/worktree. Do not work from dirty main or store
  accepted evidence only under `/tmp`. This plan is temporarily in `/tmp`
  only because the owner explicitly requested that location.
- Preserve raw successes and historical failing scores. Never edit their
  prompts, key identities, receipts or finalization in place.
- Independent approval cannot consist of the implementer declaring its own
  tests green. Submit the exact frozen checkpoint for the independent review
  required by Step 1, using the existing protocol if Core is later re-engaged.
  That handoff is a later action, not permission to wake Core during planning.
- The owner permits verified code checkpoints. Publish only the complete
  reviewed code/test/evidence slice; omit unrelated work and inconclusive
  semantic results. Commit exact reviewed bytes, then verify tree/commit and
  remote branch identity. Do not rewrite history or force-push under this plan.
- A non-AI code checkpoint may be verified and published while A7 is still
  UNMEASURED. An A7/EXP-5 publication claiming completion waits for the actual
  scored package and independent verification. These are different claims.

## 9. AI work remaining after the machinery passes

### 9.1 Preserve this successful call; do not repeat it

Saved source-review raw file:
`REC/a7_recovery/unit_1947/logs/real_source_review/replies/0000006201-26-000031.attempt1.complete.raw.json`

- raw SHA256: `625140d6eb637e029b885f356f3cb68a12ffb8c7ce1e8fded272e36b2471030b`;
- Workflow: `wf_b5890dc2-781`; agent: `a9dce3dc893074b40`;
- prompt SHA256: `04b30974b028f330a4573b6790d688e2f9932e1176135e96e75cd622e83bfecc`;
- official-state SHA256: `bd4e496f1cf6f508158532f3851dda21a9586c20324c5a05cfbe3734f272bf0b`;
- transcript SHA256: `8dcb3e0548a36939b1755f1b92801e5198c80649f939d9a2a8ab54a169b75962`.

It is a bound completed transport answer, not an approved answer key. Its
9 proposed exclusions, 11 additions, 4 open issues and quote-case discrepancy
still need the existing content adjudication. Another 35 source events are
unlaunched. Prior TEST fixtures prove missing-input/refusal handling, not that
these missing answers exist. Original A7 run 1773 remains FAIL; the fresh
sample remains UNMEASURED.

### 9.2 Exact remaining sequence

1. Verify the existing role qualification artifacts against the exact permitted
   Sonnet 5 high-effort runtime and current prompts before launch. A status
   board's "qualified" label is not the artifact. No fallback, alternate model
   or unqualified runtime; preserve valid prior qualification where unchanged.
2. Verify/reuse every compatible completed source-review result, starting with
   the exact one above. Launch only missing authorized source work. Raw first,
   exact source/input/model/attempt identity, existing transport, counted stops.
3. Feed the complete source reviews into the existing aggregate reconciliation
   and hard-review/signing/lock sequence (continuity leads: archives CODEX
   1335, 1337, 1340–1343). Reconcile every addition, exclusion and open issue
   against actual source evidence. Models judge meaning; code validates exact
   spans, IDs, shape and arithmetic. No post-hoc gold additions during scoring.
4. Freeze the resulting corrected source inventory/key and producer kit through
   the existing A4/A5/A6 owners. Rebuild generated artifacts twice, require
   identical bytes and exact counts. Keep previous versions as history.
5. Generate the authorized fresh producer answers only after that freeze.
   This is the named-correction/fresh-answer-sample path; the same 36 frozen
   events may be reused as the live amendment permits. It is not permission
   to rerun successful unchanged calls or select favorable answers.
6. Materialize the full scheduled trace, account all outcomes, derive G1 from
   the complete unmatched population, and run its two independent lanes per
   required batch. An old launched-lane count never becomes the denominator.
7. Validate/persist G1 completion; derive G2 and G3 from that exact producer,
   key and G1. Freeze their prompt/candidate/receipt identities, then obtain
   the required independent answers. Reuse the existing lifecycle and saved
   valid responses; do not ask questions when the derived population is empty.
8. Officially score both obligated original arms and the same-tier union with
   their own real no-write routes and full required response observations.
   Preserve every score, error, refusal, wait, disagreement, duplicate and miss.
9. Independent review of exact raw evidence and final counts decides A7 status.
   PASS opens A8. FAIL/INCONCLUSIVE stops Lane A under Step 1; neither means
   silently changing production, the key, the bars or the sample until it wins.

Invalid JSON/off-enum output gets only the single retry the frozen law permits,
with the same prompt. Valid semantic null or disagreement is a completed
answer with unresolved meaning, not malformed output and not a retry excuse.
Permission waits, uncalled slots and missing transcripts remain separately
visible. A durable journal mention alone never establishes a completed result.

### 9.3 Closeout checklist

The final code-readiness record includes reviewed file and whole-tree hashes,
explicit served maps, source/key/prompt/runtime identities, complete required
test inventory, each test's command/raw result/exit, every meaningful mutation
and positive control, remaining untested paths, and any semantic-only risk.

The later actual A7 result additionally includes raw model replies and official
transcripts/receipts; full required/called/completed/valid/adjudicated counts;
G1/G2/G3 exact populations; complete branch/origin accounting; both original
arm scores and the union; unchanged bars; every error/miss/refusal/wait;
confirmed-wrong accepted count; and the `3/N` 95% upper bound for every
zero-wrong-in-N claim. Report N as actually reviewed, not scheduled calls.

No-AI readiness is not a guarantee that future model replies are correct,
that the new key has no disputed content, or that A7 will pass. The required
guarantee of the machinery is narrower: unsupported, incomplete or wrong
evidence cannot be silently credited; it is preserved, counted and fails closed.


## Appendix A — Reviewed snapshot and code-derived owner inventory

The H path-relative manifest contains 88 files, excluding `__pycache__`,
`.pytest_cache` and `.pyc`. Sort relative paths; render each as
`<sha256>  <relative_path>\n`; SHA256 of those lines is
`3884426ad55e9d83f4690890b6188ef79403a7b9532fa67e0fb554a392b1a90f`.
This differs from the existing isolated-boundary tree hash because the
serialization differs; it is not evidence of drift. Keep both labeled.

### A.1 Exact file identities

The table includes complete active grader reads, relevant authority reads,
and upstream dependencies/evidence identified for the existing source/key
proof. A hash in this table does not claim every line of a large upstream
module or later step was read. Active G1/G2/G3, current scorer, prepared-run,
reference, conservation, key-correction, source-meta, reader and completion
owners were read fully; raw-transport and audit owners were read at their
active capture/input/transcript/publication/finalization boundaries. Upstream
A4/A5/A6 proof is reused where unchanged, not replaced by a hash alone.

| Path alias | Lines | SHA256 |
|---|---:|---|
| `H/a7_g1_build.py` | 2487 | `1fef8789ae0d0392b4c50d8c22b81feb6dbe97cbc3d2e5a66ff35964df24f7d7` |
| `H/a7_g23_build.py` | 1992 | `4fce0781e770ce48ca51b6d2b0a412b3357a49ba668160604a88eb39dc738b40` |
| `H/a7_g23_run.py` | 490 | `c247b909c51f23b34947c08891d97f2915c437d6b5779bd0070735e8e1979596` |
| `H/a7_g1_complete_v2.py` | 423 | `7a284f30296e698948155923c9ff1cc040eeba8b79dd0c3d22bbfade3a93250d` |
| `H/a7_g1_workflow_gate.py` | 497 | `e2386da5f64260acdc7da1a1b44c40c3fcad5a624affd3755b01448ce32d0703` |
| `H/a7_prepared_run.py` | 316 | `43dcbd35d95d31123741f77f81e41599497101807790649cf7b1167651130751` |
| `H/a7_reference_inventory.py` | 431 | `16eb1581255912092d5f97e545affd2700c6ebfdf683e858668f4402bc7b96b5` |
| `H/a7_conservation.py` | 204 | `921a24557d61505925a2ae81bef52d383069dbb6d5482833237179906fd3fe54` |
| `H/a7_key_correction.py` | 280 | `6ba1218c397191360ee4ea5705c26ce6d0ac6e3b7763baa716105f4d6c022235` |
| `H/a7_source_meta.py` | 262 | `4addd2f2e4b79bb292a8291a9cfbbcfd1efdc3d637b172ef40e1909275aa9d4a` |
| `H/a1_reader.py` | 344 | `98055e556fdb0324c022f8f14db5ec463b4486914df48bda72b6c519e731e649` |
| `H/raw_transport.py` | 1978 | `4d51412261aa9a496ca9a0c85d62547152f841e05a2b6fc484aa66af9e07ba0a` |
| `H/audit_worker_access.py` | 1514 | `dda9db0440a764711739fb533c8af65bce2a854da967b197b05067dd68026314` |
| `H/scorers/score_exp5.py` | 1545 | `dfe6b5ae3a215856d22ed1d15b49bbc2c1044e1352c046c1f1ae0da3391709c6` |
| `H/scorers/score_exp5_current.py` | 1690 | `0f769167dcac0bb634e57e6d30a030f569264f8be1c14cd6f83cab0385268e52` |
| `H/scorers/grade_batch.js` | 175 | `806a7560002a14ed5f3a4c79a78d85be0fac8abf773f8fdf9457c3d902e8abd6` |
| `H/build_a5_exp5_kit.py` | 780 | `8160bcd6246a38b7ebc9cdab1cbf31a8550fa6baec246228bfbd54eeba4a97b4` |
| `H/a6_launch_freeze.py` | 564 | `bbcba73d587a2bc2e8fc34ce27ba555065b52d89480783b2440568cede19c4b2` |
| `H/build_inventory_review.py` | 2281 | `ee03028747c662c319b238b05ed976d42427089ee1096c334b11d8b974f46825` |
| `H/build_launch_manifest.py` | 1233 | `fb327705f5703d344c413dff6c9f3ba1138cd0e8107898e08de43bdc87577567` |
| `H/build_kfields_key.py` | 1933 | `91862afd796cccb523f518ed75ab79383244aef6147ac1072068aa816e916000` |
| `H/build_kfields_final.py` | 4026 | `a0ab1138792ce2a7bfeded5b94f4b37f99c6562b003eace4494aa92098e68c05` |
| `H/build_kfields_hard_review.py` | 1268 | `7c5ac0ecac07b3f85f25cae9982f7921ee313405215bea42342a88def861c09e` |
| `H/kf_lint.py` | 290 | `920742cf099fc56ed5773aee6d75e7e7ae180de949a96e2af420faa2f6135c2b` |
| `MAIN/AGENTS.md` | 58 | `a2cff82f7f59ae5ce1447491ae82548f704c7adaed1c070aebceab3fece81f54` |
| `MAIN/.claude/plans/Drivers/WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md` | 176 | `e71212cf3b2a6e56643c1f570cd9605f2256f8d2f0a9fb3c089e02f772bef736` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Orchestration.md` | 344 | `704efcf20304a12358b838662fc314875457c43f9aa9e74557b5b686625d9237` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Steps.md` | 658 | `f9190144c071da3003c40b85d7b0064f2df7f16bc62aa9c44064d9ad16e88919` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step1.md` | 853 | `bc5a0043a743547b7e5117aed4bdede75de08031682d8e3cc37d0b70402579e1` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step2.md` | 699 | `de24932a95de48fc29499a30ee28e25e130a8791c51e61be477cf0b6ae3cd12e` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step3.md` | 474 | `99f16fe0bb714263a65d553f2e645a8b6204e4f302f7e3ddaf4b254adbeb3ee7` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step4.md` | 946 | `effed37278945a1586cc19130373c637dad26908ff42b0f9c758168d4280f492` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step5.md` | 698 | `bbf7b92be930ecae3d6a16bec3f878884dbbcfafff9d9dd1dda8e8e5f642af0a` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step6.md` | 609 | `94d81b479751c690ea012352d8964baaff23c562e829a70c45bdc45d2894a66c` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step7.md` | 940 | `49d0001fc1f1be2e300723ea2d9c74bfe8942371d75d61b0ea8596db7a65a82a` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step8.md` | 1067 | `6e36171803bb00cc6cb26f8cf4ce232f96ba54ded4e311d7420630a199a460cf` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step9.md` | 1069 | `7940919a9a8e585c65dd9cc32bbe0c0f420c184a736582276ce1368914d50499` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step10.md` | 1154 | `4663e1e5d9cc1cff5ba40888990967aaa10792b2fae410c175c618a15c2b8d50` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step11.md` | 464 | `780794709a36bab452ad9a88753431ad1f816c8aa7982ecc85c056c2b70ec3fb` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step12.md` | 731 | `64aa439bb1b8e80c40993905ae20d68c36408ad6d1c8e255357d5dd37f417c21` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step13.md` | 405 | `c8eac3b934bf1458a79bb31b430330241452655b311e85223374b04d20f660d5` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/step14.md` | 255 | `d86915917d4f548bc96eacb0e84aa80ce5c0bbb05f33d38f2dc48ac02f879755` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/promptStandard.md` | 114 | `b90b0cb6a7bf6ec605263a8387dd93921107624c32ec2aa8265d57c6e63e4910` |
| `MAIN/.claude/plans/Drivers/FinalDesign/LeftOverSteps/CoreSessionPrompt.md` | 103 | `34cc1ec9f76396ab41404591e7fb452c9b35600822aefd8eb0fea592b51de5e5` |
| `MAIN/.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md` | 316 | `4218d73abe6b98ef2ecd325aef8b5e49985101b122e457b39784dee677f32a0b` |
| `MAIN/.claude/plans/Drivers/FinalDesign/FableExperimentPlan.md` | 259 | `7d55a1c849d8ceeaf2b029264287552e9ea08a054bc6b8fb5d6dd347d6942592` |
| `MAIN/.claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md` | 850 | `e224cf14a1d60141c840fabfb73c18c8ee8e4361cedaf6d3cf27bcd3fee72410` |
| `REC/driver/core/fact_match.py` | 141 | `bf6f0c922ef1f443fa16b01c4d80d87b445895d48b7da5fa772964de21304497` |
| `REC/driver/core/driver_validators.py` | 643 | `4b90aa83595c48e530914c748c00c6c93036559782d7479138cce6eeb7a5dff5` |
| `REC/driver/relocation/inline_html.py` | 4412 | `c58c1af9d35950b98c9891a00a195a47d5b078e1b258509e14b07b66ffc7f9ea` |
| `REC/a7_recovery/unit_1957/map_codex_regression_2.tsv` | 107 | `182f3f9a3373fafeda1d139a615935b39359680da528d12dfa02da2cd3443923` |
| `REC/a7_recovery/unit_1957/ledger/a1_aligned_1957.py` | 152 | `397894e328d9986c1801cb0adc92e8f0ba82e07203c85b12719f4b01f663b232` |
| `REC/a7_recovery/unit_1942/ledger/s2_g23_native_1942.py` | 352 | `7af89f509b1751405be1afba45e41f3b4b1a64ef705ead82a43e5c4cdf027520` |
| `REC/a7_recovery/codex_a7_20260909/COMPARISON.json` | 463 | `f1ed64149d8e0053f850652c57094386e62e0bbf8f6902d056d20a0ed863476c` |
| `REC/a7_recovery/codex_a7_20260909/CHECKPOINT_MANIFEST.tsv` | 213 | `6563487f68778c272b81870feba3541c38c5d3f5b48bcd6f2599651072526ad7` |

### A.2 Active rule-owner functions and test-family obligations

This inventory was extracted from the live source AST, not a remembered
list of examples. Entries give `name @ start–end [if nodes/except handlers]`.
Class entries include nested methods in their counts. These are static
navigation/obligation counts, **not executed branch coverage**. During W5 map
each reachable decision/exception outcome in these functions to a collected
positive/negative test or an explicitly blocking open item. A zero `if` count
does not exempt a function with a public input/output contract or an exception
from a dependency. Do not inflate this into line-coverage work on unrelated
historic helpers. Table T01–T20 defines the required behavioral outcomes.

#### H/a7_g1_build.py

Required test families: T01,T04–T06,T12–T16,T19.

- `_required` @ 53–84 [1/0]
- `_a6` @ 107–123 [1/0]
- `_sha` @ 126–127 [0/0]
- `_sha_file` @ 130–131 [0/0]
- `_plain` @ 134–140 [1/0]
- `_pretty` @ 143–148 [1/0]
- `_finalization` @ 152–156 [0/0]
- `run_of` @ 159–215 [4/0]
- `effective_slots` @ 218–290 [7/0]
- `_approved_bound` @ 293–312 [1/0]
- `gold_by_event` @ 315–351 [5/0]
- `live_key` @ 354–364 [0/0]
- `_measured` @ 382–385 [0/0]
- `materialize` @ 388–571 [11/1]
- `_leg_rows` @ 575–598 [0/0]
- `_cross_check` @ 601–617 [1/0]
- `inventory` @ 620–669 [3/0]
- `internal_key` @ 673–679 [0/0]
- `question_id` @ 682–691 [0/0]
- `_display` @ 694–702 [0/0]
- `accepted_positions` @ 705–715 [0/0]
- `questions` @ 718–752 [1/0]
- `locator` @ 755–758 [0/0]
- `controls` @ 761–825 [5/0]
- `event_groups` @ 878–883 [0/0]
- `event_packet` @ 886–909 [1/0]
- `read_event_reply` @ 915–983 [13/1]
- `_components` @ 986–1005 [2/0]
- `event_credit` @ 1008–1065 [5/0]
- `terminal_categories` @ 1073–1096 [4/0]
- `expected_groups` @ 1099–1108 [0/0]
- `validate_merged` @ 1111–1151 [3/0]
- `_seg` @ 1178–1179 [0/0]
- `root_path` @ 1182–1183 [0/0]
- `receipt_path` @ 1186–1187 [0/0]
- `reservation_path` @ 1190–1191 [0/0]
- `state_path` @ 1194–1195 [0/0]
- `invocation_path` @ 1198–1199 [0/0]
- `script_path` @ 1202–1203 [0/0]
- `accounting_path` @ 1206–1207 [0/0]
- `finalization_path` @ 1210–1211 [0/0]
- `capture_name` @ 1214–1216 [0/0]
- `raw_stem` @ 1219–1226 [0/0]
- `_exists` @ 1229–1230 [0/0]
- `_ensure` @ 1233–1237 [1/0]
- `_write_new` @ 1240–1247 [0/0]
- `_read` @ 1250–1252 [0/0]
- `prior_g1_calls` @ 1268–1281 [0/0]
- `probe_calls` @ 1284–1293 [0/0]
- `all_prior_calls` @ 1296–1312 [0/0]
- `confirmed_duplicate_groups` @ 1315–1323 [0/0]
- `owner_hashes` @ 1326–1346 [0/0]
- `_bound_grading_scorer_sha` @ 1349–1359 [0/0]
- `live_output_limit` @ 1362–1363 [0/0]
- `prompt_tree_sha` @ 1366–1371 [0/0]
- `load_frozen` @ 1374–1383 [2/0]
- `freeze_root` @ 1387–1441 [6/1]
- `load_root` @ 1444–1455 [3/0]
- `segments` @ 1459–1466 [0/0]
- `segment_state` @ 1469–1474 [2/0]
- `_claimed` @ 1477–1484 [0/0]
- `_named_by_finalized` @ 1487–1496 [1/0]
- `lane_states` @ 1499–1519 [2/0]
- `latest_retry` @ 1522–1533 [2/0]
- `lifecycle_problems` @ 1536–1576 [9/0]
- `_parent_of` @ 1579–1589 [1/0]
- `_rows_for` @ 1592–1619 [2/0]
- `_bound_script` @ 1630–1651 [1/0]
- `publish_run` @ 1654–1732 [4/2]
- `load_receipt` @ 1736–1737 [0/0]
- `approved` @ 1741–1772 [5/1]
- `preflight` @ 1775–1835 [12/1]
- `record_official_state` @ 1838–1847 [1/0]
- `capture_results` @ 1851–1906 [4/0]
- `_captures_of` @ 1909–1914 [1/0]
- `_outcome_of` @ 1917–1950 [6/0]
- `account_segment` @ 1953–1986 [4/0]
- `whole_path` @ 1992–1993 [0/0]
- `bind_whole_answers` @ 1996–2021 [3/0]
- `whole_answers` @ 2024–2039 [2/0]
- `audit_official_state` @ 2042–2103 [4/0]
- `_capture_text` @ 2106–2114 [2/0]
- `register_task_kind` @ 2124–2131 [1/0]
- `task_kind` @ 2134–2137 [0/0]
- `binding_and_parser` @ 2140–2142 [0/0]
- `task_owners` @ 2145–2154 [3/0]
- `event_binding` @ 2157–2175 [1/0]
- `finalize_segment` @ 2178–2291 [12/0]
- `save_results` @ 2294–2306 [1/0]
- `launchers` @ 2309–2323 [0/0]
- `freeze` @ 2326–2432 [1/0]
- `write` @ 2435–2453 [3/0]

#### H/a7_g23_build.py

Required test families: T05–T11,T15–T18.

- `_sha` @ 53–54 [0/0]
- `_git` @ 57–58 [0/0]
- `bind_grading_scorer` @ 73–106 [4/0]
- `_scorer` @ 109–121 [1/0]
- `meaning_fields` @ 124–126 [0/0]
- `extras_buckets` @ 129–131 [0/0]
- `refuse` @ 140–182 [8/0]
- `_withheld` @ 186–195 [1/0]
- `g1_final` @ 198–279 [8/0]
- `resolutions` @ 282–296 [1/0]
- `_event_doc` @ 300–309 [0/0]
- `route_for` @ 312–329 [0/0]
- `event_meta` @ 332–339 [0/0]
- `matched_pairs` @ 343–375 [0/0]
- `extras_rows` @ 378–390 [1/0]
- `observed_responses` @ 393–423 [3/0]
- `score_leg` @ 426–436 [0/0]
- `g1_identity` @ 439–448 [0/0]
- `official_verdict_maps` @ 451–455 [0/0]
- `_verdict_maps_from` @ 458–630 [21/0]
- `_lifecycle` @ 633–646 [1/0]
- `_resolutions_from` @ 649–666 [2/0]
- `official_resolutions` @ 669–682 [0/0]
- `official_resolution` @ 685–702 [0/0]
- `official_safety_findings` @ 705–715 [0/0]
- `_safety_from` @ 718–742 [1/0]
- `score_leg_official` @ 745–755 [0/0]
- `_official_derivation` @ 758–782 [2/0]
- `_score_leg_bound` @ 785–847 [3/0]
- `official_tier_decision` @ 850–882 [0/0]
- `meaning_questions` @ 885–893 [0/0]
- `write_atomic` @ 896–913 [3/1]
- `meaning_contract` @ 963–1113 [0/0]
- `meaning_rules` @ 1116–1183 [1/0]
- `event_context` @ 1194–1214 [1/0]
- `load_verified_inputs` @ 1219–1248 [2/0]
- `verified_event_context` @ 1251–1272 [3/0]
- `meaning_question_id` @ 1275–1279 [0/0]
- `meaning_packet` @ 1282–1347 [7/0]
- `read_meaning_reply` @ 1350–1401 [8/1]
- `reconcile_meaning` @ 1404–1447 [5/0]
- `_inventory` @ 1473–1498 [1/0]
- `reference_card` @ 1501–1530 [5/0]
- `card_problems` @ 1533–1571 [9/0]
- `card_key` @ 1574–1576 [0/0]
- `non_unique_cards` @ 1579–1597 [2/0]
- `extras_rules` @ 1615–1663 [1/0]
- `extras_question_id` @ 1666–1668 [0/0]
- `extras_packet` @ 1671–1709 [0/0]
- `_required_context` @ 1712–1721 [1/0]
- `batch_packet` @ 1724–1773 [3/0]
- `read_extras_reply` @ 1776–1815 [7/1]
- `reconcile_extras` @ 1818–1838 [4/0]
- `pack_batches` @ 1853–1889 [6/0]
- `source_event` @ 1892–1895 [0/0]
- `batch_problems` @ 1898–1908 [2/0]
- `route_inventory` @ 1912–1959 [4/0]
- `precall_unresolved` @ 1963–1978 [0/0]
- `preflight_problems` @ 1981–1992 [0/0]

#### H/a7_g23_run.py

Required test families: T01,T06–T16,T19.

- `_sha` @ 42–43 [0/0]
- `populations` @ 52–148 [5/1]
- `_rows_and_prompts` @ 151–169 [0/0]
- `_g2_packet_for` @ 172–185 [0/0]
- `_g3_packet_for` @ 188–195 [0/0]
- `freeze` @ 198–350 [3/0]
- `kind_binding` @ 376–384 [1/0]
- `kind_candidate` @ 393–427 [0/0]
- `write_kind` @ 430–444 [1/0]
- `write` @ 447–475 [2/0]

#### H/a7_g1_complete_v2.py

Required test families: T06,T12–T16,T19.

- `select_attempt` @ 18–29 [1/0]
- `run_digest` @ 32–47 [0/0]
- `evidence` @ 50–195 [21/0]
- `relations_from_run` @ 198–201 [0/0]
- `lane_relations` @ 204–225 [2/0]
- `g23_identity` @ 232–243 [0/0]
- `complete_g23` @ 246–334 [6/0]
- `persist_g23` @ 337–344 [1/0]
- `load_g23` @ 347–372 [2/0]
- `complete` @ 375–423 [1/0]

#### H/a7_g1_workflow_gate.py

Required test families: T01,T12–T16,T19.

- `owner_sha256` @ 50–52 [0/0]
- `refusal_path` @ 55–56 [0/0]
- `_script_bytes` @ 60–71 [1/0]
- `_largest_prefix` @ 74–90 [4/0]
- `next_admissible` @ 93–116 [2/1]
- `_parent_records` @ 120–150 [4/1]
- `_states_naming` @ 153–187 [6/1]
- `_transcripts_for` @ 190–204 [4/0]
- `_no_output` @ 207–238 [4/0]
- `inspect_prelaunch_refusal` @ 241–374 [22/2]
- `_zero_capture_accounting` @ 377–395 [0/0]
- `_stable` @ 398–401 [0/0]
- `close_prelaunch_refusal` @ 404–497 [11/0]

#### H/a7_prepared_run.py

Required test families: T01,T04,T13,T16,T19.

- `_sha` @ 37–39 [0/0]
- `_read_json` @ 42–50 [1/1]
- `load` @ 53–177 [11/0]
- `_finalizations` @ 180–228 [6/0]
- `_executed` @ 231–242 [1/0]
- `require_current_era` @ 245–254 [1/0]
- `current` @ 257–276 [1/0]
- `current_era` @ 279–286 [0/0]
- `cli_run` @ 289–316 [6/0]

#### H/a7_reference_inventory.py

Required test families: T01,T03,T05,T09,T16,T19.

- `_sha` @ 87–88 [0/0]
- `_approved_reference_names` @ 91–105 [1/0]
- `_effective_origins` @ 108–143 [3/0]
- `_packets` @ 146–165 [0/0]
- `_values` @ 168–187 [2/0]
- `_ledger_sha` @ 190–192 [0/0]
- `build` @ 195–283 [10/0]
- `read` @ 296–324 [5/0]
- `expected_document` @ 327–356 [1/0]
- `_first_difference` @ 359–377 [3/0]
- `validate` @ 380–393 [1/0]
- `raw_value_occurrences` @ 395–413 [1/0]
- `write` @ 416–431 [2/1]

#### H/a7_conservation.py

Required test families: T04,T05,T11,T13,T18,T19.

- `contributions` @ 39–88 [2/0]
- `terminals` @ 91–122 [1/0]
- `dimensions` @ 125–158 [0/0]
- `_terminal_of` @ 161–175 [3/0]
- `_conservation_problems` @ 178–194 [3/0]

#### H/a7_key_correction.py

Required test families: T01,T03,T05,T09,T16.

- `fact_sha256` @ 59–61 [0/0]
- `required_suffix` @ 64–68 [0/0]
- `affected` @ 71–85 [0/0]
- `_period_rows` @ 88–97 [0/0]
- `load` @ 100–102 [0/0]
- `apply` @ 105–208 [16/0]
- `current_key` @ 211–264 [2/0]
- `write` @ 267–280 [2/1]

#### H/a7_source_meta.py

Required test families: T01,T09,T10,T11.

- `_inputs` @ 76–86 [1/0]
- `_read_session` @ 95–105 [1/0]
- `freeze` @ 108–228 [12/1]
- `load` @ 231–234 [0/0]
- `route_event` @ 237–262 [3/0]

#### H/a1_reader.py

Required test families: T02–T04,T09,T19.

- `A1ReaderError` @ 53–54 [0/0]
- `sparse_fact_keys` @ 57–62 [0/0]
- `item_defaults` @ 65–78 [3/0]
- `required_item_fields` @ 81–91 [0/0]
- `readable_menu` @ 96–125 [4/0]
- `restore_menu_pick` @ 128–134 [0/0]
- `_nonblank` @ 139–140 [0/0]
- `_exact` @ 143–153 [2/0]
- `read_one` @ 156–180 [3/1]
- `normalize` @ 183–275 [16/0]
- `validate` @ 278–338 [9/1]
- `owner_sha256` @ 341–344 [0/0]

#### H/raw_transport.py

Required test families: T01–T04,T12–T16,T19.

- `RawTransportError` @ 53–54 [0/0]
- `_raw_filename` @ 57–60 [0/0]
- `save_raw` @ 63–98 [2/1]
- `_reject_duplicate_keys` @ 101–112 [1/0]
- `_reject_nonstandard_constant` @ 115–119 [0/0]
- `unfence` @ 129–163 [5/0]
- `parse_reply` @ 166–170 [0/0]
- `parse_exact` @ 173–186 [0/1]
- `manifest_events` @ 198–206 [1/0]
- `prompt_pin` @ 209–223 [1/0]
- `prompt_evidence_problem` @ 226–243 [2/1]
- `_attempt_valid` @ 246–264 [2/1]
- `invalid_pairs` @ 267–312 [5/0]
- `schedule_from_manifest` @ 315–349 [2/0]
- `replies_from_result` @ 352–378 [4/0]
- `_ingest_by_schedule` @ 381–527 [15/2]
- `resolve_with_one_retry` @ 530–573 [4/0]
- `ingest_workflow_result` @ 577–719 [15/2]
- `a1_limits` @ 754–764 [0/0]
- `a1_schedule` @ 767–785 [0/0]
- `a1_ordinals` @ 788–792 [0/0]
- `a1_identity_problems` @ 795–810 [3/0]
- `a1_pair_problems` @ 813–837 [5/0]
- `a1_readable_rows` @ 840–866 [4/1]
- `a1_raw_bindings` @ 869–883 [0/0]
- `a1_raw_binding_problems` @ 886–926 [2/0]
- `save_or_reuse_raw` @ 929–959 [3/1]
- `a1_preserve` @ 962–980 [0/1]
- `a1_classify_rows` @ 983–1022 [6/0]
- `a1_classify` @ 1025–1043 [3/0]
- `a1_plan_for_run` @ 1058–1112 [7/1]
- `a1_plan_identity` @ 1115–1126 [0/0]
- `a1_expected_receipt` @ 1129–1164 [1/0]
- `_exact_keys` @ 1167–1179 [2/0]
- `a1_run_contract_problems` @ 1182–1241 [14/0]
- `_a1_child_problems` @ 1244–1277 [6/1]
- `_a1_keyed` @ 1280–1292 [1/0]
- `a1_primary_retry_keys` @ 1295–1304 [0/0]
- `a1_primary_evidence_problems` @ 1307–1310 [0/0]
- `a1_finalization_problems` @ 1313–1420 [28/0]
- `a1_ledger` @ 1423–1434 [2/0]
- `_pairs_of` @ 1443–1453 [2/0]
- `declared_lane_input` @ 1462–1468 [1/0]
- `approved_lane_input_problems` @ 1471–1508 [5/0]
- `approved_lane_input_fields` @ 1511–1520 [1/0]
- `_sha_file` @ 1523–1525 [0/0]
- `_fsync_dir` @ 1528–1533 [0/0]
- `write_new` @ 1536–1558 [0/1]
- `receipt_bytes` @ 1561–1568 [0/0]
- `_atomic_json` @ 1571–1578 [0/0]
- `a1_plan_path` @ 1581–1583 [0/0]
- `a1_plan` @ 1586–1588 [0/0]
- `a1_canonical_calls` @ 1591–1593 [0/0]
- `a1_projection` @ 1596–1598 [0/0]
- `a1_source_order` @ 1601–1608 [1/0]
- `a1_args_for` @ 1611–1630 [2/0]
- `a1_expected_args` @ 1633–1638 [0/0]
- `a1_retry_set` @ 1641–1647 [1/0]
- `a1_load_receipt_loosely` @ 1650–1672 [3/1]
- `_a1_publish` @ 1675–1768 [7/0]
- `a1_prepare_run` @ 1771–1773 [0/0]
- `a1_prepare_retry` @ 1776–1805 [4/1]
- `a1_finalize` @ 1808–1978 [12/4]

#### H/audit_worker_access.py

Required test families: T01,T09,T12–T16,T19.

- `_load` @ 121–123 [0/0]
- `_load_pinned` @ 126–147 [2/2]
- `_resumed_cached_row` @ 165–185 [3/1]
- `_same_published_script` @ 188–204 [3/1]
- `record_state` @ 207–246 [4/1]
- `_jsonl` @ 249–264 [1/1]
- `_blocks` @ 267–269 [0/0]
- `_text_of` @ 272–277 [1/0]
- `_role` @ 280–281 [0/0]
- `_lanes_in` @ 284–294 [1/1]
- `_same_model` @ 297–300 [0/0]
- `_rejection` @ 303–336 [5/0]
- `_preview_ok` @ 345–360 [2/0]
- `_next_is_input` @ 363–371 [1/0]
- `_LaterInput` @ 374–377 [0/0]
- `_input` @ 380–428 [7/0]
- `_expected_input` @ 431–464 [7/1]
- `_pairs` @ 467–479 [1/0]
- `_chain` @ 482–592 [10/0]
- `_official_location` @ 595–607 [2/0]
- `_armed` @ 610–620 [1/0]
- `audit` @ 623–1159 [75/3]
- `_g1_shape_problems` @ 1168–1203 [7/0]
- `_g1_transcript` @ 1206–1278 [12/0]
- `g1_state_audit` @ 1281–1494 [39/1]
- `main` @ 1496–1510 [1/0]

#### H/scorers/score_exp5_current.py

Required test families: T03–T08,T11,T16–T18.

- `_code_fields` @ 77–92 [0/0]
- `field_accounting` @ 98–117 [4/0]
- `_bucket` @ 151–181 [9/0]
- `_item` @ 184–189 [0/0]
- `ExactValueError` @ 192–193 [0/0]
- `_dec` @ 196–216 [5/0]
- `_canon_item_values` @ 219–251 [2/0]
- `_canon_level` @ 254–256 [0/0]
- `_meas_tokens` @ 259–261 [0/0]
- `_ev_key` @ 264–283 [2/0]
- `_shape_pair` @ 292–300 [0/0]
- `_base_driver` @ 312–315 [0/0]
- `_resolved_period` @ 318–324 [0/1]
- `_name_agrees` @ 327–333 [0/0]
- `_ReplayStore` @ 339–396 [0/0]
- `conflicting_driver_names` @ 399–417 [2/0]
- `facts_bearing` @ 420–423 [0/0]
- `_replay_drivers` @ 426–436 [1/0]
- `route_reply` @ 439–476 [2/0]
- `eligible_produced` @ 479–496 [0/0]
- `_to_v2_with_positions` @ 499–522 [0/0]
- `identity_key` @ 525–535 [0/0]
- `dedup_items` @ 538–553 [1/0]
- `classify_extras` @ 563–600 [2/0]
- `reconcile_rulings` @ 603–627 [2/0]
- `_locator` @ 633–641 [0/0]
- `classify_abstentions` @ 644–683 [1/0]
- `grade_unmatched` @ 686–745 [4/0]
- `_rows_for_event` @ 748–839 [11/0]
- `invalid_response_stats` @ 846–878 [2/0]
- `passes_official_bars` @ 881–919 [2/0]
- `score_arm` @ 922–1358 [32/0]
- `union_answer` @ 1361–1394 [0/0]
- `score_union` @ 1397–1430 [2/0]
- `presence_disagreement` @ 1433–1509 [4/0]
- `_leg` @ 1512–1533 [7/0]
- `final_gate` @ 1536–1609 [10/0]
- `project_replay_items` @ 1622–1655 [2/0]
- `replay_reader` @ 1658–1690 [1/0]

### A.3 External callable closure

The source/key path reaches the existing `build_inventory_review`,
`build_kfields_key`, `build_kfields_final`, `build_kfields_hard_review`,
`kf_lint`, `build_launch_manifest`, `build_a5_exp5_kit` and
`a6_launch_freeze` owners. Their frozen identities are above. The no-write
route reaches actual `driver.core` validators, prepared-fact builder, event
route, XBRL attach/adapter imports, period/ID/unit owners and relocation code.
The package must serve these from its declared current root. In particular,
explicit regression modules include `driver/core/test_exact_movement.py` and
`driver/relocation/test_exact_sign.py` from the already adopted fix.

Do not mistake top-level Python imports for this full runtime closure. The
actual cold W1 path, function-local imports, generated-script reads, existing
boundary map, and full affected test collection are the authority for its
final file list. A missing module required only by an obsolete test does not
justify resurrecting a retired runtime feature.

## Appendix B — Current harness tests and reusable executed evidence

### B.1 Current harness inventory

There are 31 `test_*.py` modules and 757 static test-function definitions.
Parametrized executions expand that count. These counts describe files,
not completion, correctness or a measured coverage percentage.

| H-relative module | Static test definitions |
|---|---:|
| `test_a1_invalid_response.py` | 21 |
| `test_a1_no_tools.py` | 4 |
| `test_a1_prompt_contract.py` | 5 |
| `test_a1_serial_transport.py` | 4 |
| `test_a5_contract_1401.py` | 22 |
| `test_a5_corrected_inventory_1514.py` | 5 |
| `test_a5_exp5_kit_1400.py` | 12 |
| `test_a5_final_lock_1513.py` | 5 |
| `test_a5_gate_1469.py` | 12 |
| `test_a5_launch_gate_1403.py` | 10 |
| `test_a5_route_1406.py` | 10 |
| `test_a6_final_lock_1515.py` | 8 |
| `test_a6_fixture_isolation_1768.py` | 3 |
| `test_a6_fixture_isolation_after_1768.py` | 1 |
| `test_a6_launch_freeze_1409.py` | 10 |
| `test_a6_locked_rows_1476.py` | 4 |
| `test_a7_cached_rows_1413.py` | 5 |
| `test_a7_closeout_integrity_1482.py` | 13 |
| `test_a7_corrections_1454.py` | 47 |
| `test_a7_current_1473.py` | 6 |
| `test_a7_g1_precall_freeze_1525.py` | 7 |
| `test_a7_g23_lifecycle_1464.py` | 42 |
| `test_a7_postrun_identity_1521.py` | 16 |
| `test_a7_postrun_identity_1521_recovery_1774.py` | 9 |
| `test_a7_raw_binding_1483.py` | 6 |
| `test_a7_runstates_1470.py` | 23 |
| `test_a7_source_correction_1487.py` | 15 |
| `test_a7_trace_1471.py` | 3 |
| `test_g1_cached_resume_1781.py` | 28 |
| `test_g1_declared_input_1792.py` | 17 |
| `test_harness_guards.py` | 384 |

### B.2 Existing evidence to retain and reuse, not rerun as model calls

| Saved proof | What it proves | What it does not prove |
|---|---|---|
| `E/handoffs_2/logs/attempt_codex_source_2/REAL_SOURCE_PROOF.json` | Exact one real source answer binds; each of 35 missing events counted; materialize/lock refuse partial run | Source answer content approved or all sources done |
| Same attempt's complete TEST fixture | 10/10 source materialize/finalize/lock proof; missing-input refusal and restored control | AI key truth or unseen model correctness |
| `E/producer_4/logs/attempt_codex_producer_4/` | Actual prepare/generated launcher/capture/audit/finalization for 392 TEST answers; 392 missing-input and 392 omitted-handoff refusals; raw retained; restored pass | A new successful 392-call AI experiment |
| `unit_1957` attempts `nat5`, `legG` | Existing 30/30 native/legacy drafting/finalization checks on the preserved tree | Current independent full grader regression |
| `unit_1957` attempt `mutF` | 204 preserved input/carrier refusal mutations | 204 proof obligations covered after unrelated source/owner changes |
| `unit_1957` attempt `carrA` | 12/12 preserved carrier checks | Source/key meaning qualification |
| `unit_1957` attempts `signA`, `signB`, `signC` | 4/4 valid, missing-input refusal, 4/4 restored signing path | Every future key can be signed regardless of unresolved content |
| `unit_1957` attempts `pvA2`, `pvB3` | 28 native-input mutation checks | Grader prompt content correctness |
| `E/BOUNDARY_PIN_PROOF.json` | Correct served input pin succeeds; changing only the approved-input source row gets expected host-boundary refusal | All callable modules are included in the sparse regression view |
| `unit_1942/ledger/s2_g23_native_1942.py` and its pinned outputs | Actual native G23 lifecycle/official-decision wiring, one G1 validation, 108 routes for its 36×3 population, distinct completion reuse | Semantic judgments are true; normal cold import closure is complete; every run has 108 routes |
| `E/regression_2/logs/attempt_codex_regression_2/REGRESSION_codex_regression_2.txt` | Actual 30-module candidate result, 905 passes/184 failures/14 setup errors/2 skips | A green suite or current G23 lifecycle coverage |

Prior failed setup attempts `handoffs_1`, `producer_1/2/3`, `regression_1`
and Core's stale-pin attempt remain history, not passing evidence. Preserve
all original stdout/stderr, commands, exits and exact inputs. Reuse evidence
only after comparing the relevant code/dependency/input/test identity and
assertion. Changed owners need fresh no-AI proof; unaffected actual AI outputs
must not be repeated just because code proof is rerun.

Baseline raw regression SHA256:
`b14c36406523f68978aff449ec8ce794e30bd3954dadfa32dd7a467c94d51e5b`.
Candidate raw regression SHA256:
`e58891a535fb0f912b799a7be0193b8ba67021105736b90b5fff21495a5898a0`.
Both child exits are 1. Baseline took 645.18 seconds; candidate 636.08 seconds.
The comparison's `delta_pass=true` means no new failure identities, not PASS.

## Appendix C — All 198 existing failing/error test identities

Source: the frozen candidate raw regression and `E/COMPARISON.json` identified
above. Each ID appears exactly once; the independently parsed set equals all
198 comparison IDs (no missing or extra IDs). The two identically named
postrun tests are disambiguated by their module paths and raw trace locations,
not counted twice as one test. Groups describe the first observed stopping
cause. They are NOT waivers and do NOT predict whether later assertions pass.

| Group | Count | Work unit |
|---|---:|---|
| P02 | 10 | W1/R1 |
| F01 | 17 | W1/R1 |
| F03 | 2 | W1/R1 |
| P03 | 6 | W1/R1 |
| P01 | 22 | W1/R1 |
| D01 | 108 | W1/R1 |
| D02 | 4 | W1/R1 |
| E01 | 3 | W1/R1 |
| E02 | 1 | W1/R1 |
| E03 | 1 | W1/R1 |
| E04 | 1 | W2/R2 |
| E05 | 1 | W1/R1 |
| E06 | 1 | W1/R1 |
| F02 | 20 | W1/R1 |
| E07 | 1 | W1/R1 |

Counts by the original stopping-error family remain: imports 112; missing
files 22; Node launcher exits 15; read-only mutation errors 2; explicit
package/freeze/era ValueErrors 36; other assertion/helper/expected-exception
mismatches 11. Total 198, including the 14 setup errors. The grouped actions
below combine causes that have the same minimal owner-level remedy.

### D01 — Current production dependency missing (108)

W1/R1: serve the complete pinned current production/test dependency closure, including function-local imports. Run the current positive route before these tests. Do not copy imports into the test or preload host modules to mask the missing package.

- `test_a7_corrections_1454.py::test_a_split_with_mixed_outcomes_loses_neither_branch`
- `test_a7_corrections_1454.py::test_defect1_control_lawful_suffixed_family_routes_and_bare_one_does_not`
- `test_a7_corrections_1454.py::test_defect3_an_incomplete_run_is_never_failed_by_spelling_alone`
- `test_a7_corrections_1454.py::test_defect3_control_lawful_synonym_passes_and_wrong_meaning_fails_safety`
- `test_a7_corrections_1454.py::test_defect3_the_route_refuses_a_malformed_name_and_accepts_a_lawful_one`
- `test_a7_corrections_1454.py::test_one_raw_input_with_two_facts_keeps_BOTH_branches`
- `test_a7_corrections_1454.py::test_rule5a_a_numberless_growth_basis_uses_level_unit`
- `test_a7_corrections_1454.py::test_rule6_an_exact_duration_window_is_all_or_nothing`
- `test_a7_corrections_1454.py::test_the_rejection_accounting_is_required_and_exactly_rederived`
- `test_harness_guards.py::test_1134_no_extras_input_is_LAWFULLY_complete_when_nothing_is_eligible`
- `test_harness_guards.py::test_1134_no_extras_verdict_for_an_accepted_extra_is_INCOMPLETE`
- `test_harness_guards.py::test_1134_score_union_FORWARDS_extras_verdicts`
- `test_harness_guards.py::test_1134_unrun_grading_with_unmatched_gold_cannot_PASS`
- `test_harness_guards.py::test_1135_a_produced_DUPLICATE_earns_no_recall_and_blocks_PASS`
- `test_harness_guards.py::test_1135_an_abstention_with_an_unsound_locator_is_REFUSED_upstream`
- `test_harness_guards.py::test_1136_an_answered_gold_row_cannot_ALSO_be_charged_to_an_abstention`
- `test_harness_guards.py::test_1136_the_duplicate_bucket_is_filled_from_the_identity_owner`
- `test_harness_guards.py::test_1139_a_grader_linked_surprise_is_not_ALSO_a_missing_twin`
- `test_harness_guards.py::test_1139_duplicate_gold_is_an_inconclusive_KEY_erratum_not_model_failure`
- `test_harness_guards.py::test_1140_a_gold_linked_abstention_does_NOT_answer_a_surprise_twin`
- `test_harness_guards.py::test_1140_a_pure_duplicate_key_erratum_is_None_not_False`
- `test_harness_guards.py::test_1140_a_real_hard_failure_still_returns_False`
- `test_harness_guards.py::test_1140_an_explicit_None_ruling_earns_no_potential_credit`
- `test_harness_guards.py::test_1140_unresolved_gold_WITH_enough_candidates_stays_PENDING`
- `test_harness_guards.py::test_1140_unresolved_gold_WITHOUT_candidates_is_a_definite_FAIL`
- `test_harness_guards.py::test_1141_a_SAME_event_candidate_still_raises_the_ceiling`
- `test_harness_guards.py::test_1141_a_spare_candidate_in_ANOTHER_event_cannot_raise_the_ceiling`
- `test_harness_guards.py::test_827B4_actual_surprise_finds_its_metric_home`
- `test_harness_guards.py::test_827B4_false_homes_must_park_not_pair[actual-fuel_cost-metric]`
- `test_harness_guards.py::test_827B4_false_homes_must_park_not_pair[guidance-revenue-guidance]`
- `test_harness_guards.py::test_827B4_guidance_surprise_finds_its_guidance_home`
- `test_harness_guards.py::test_ABST_a_diagnostic_abstention_is_charged_to_NEITHER_side`
- `test_harness_guards.py::test_ABST_a_gold_linked_abstention_is_charged_as_a_park`
- `test_harness_guards.py::test_ABST_the_split_is_the_LOCATOR_not_the_route_decision`
- `test_harness_guards.py::test_ADDA_a_false_meaning_verdict_on_an_accepted_fact_is_confirmed_wrong`
- `test_harness_guards.py::test_ADDA_a_refused_row_never_enters_the_accepted_fact_safety_count`
- `test_harness_guards.py::test_ADDA_all_correct_lawful_path_passes_safety`
- `test_harness_guards.py::test_ADDA_genuine_key_miss_is_INCONCLUSIVE_not_a_failure`
- `test_harness_guards.py::test_ADDA_malformed_extras_verdicts_block_PASS[verdicts0-extras_verdict_malformed]`
- `test_harness_guards.py::test_ADDA_malformed_extras_verdicts_block_PASS[verdicts1-extras_verdict_out_of_range]`
- `test_harness_guards.py::test_ADDA_malformed_extras_verdicts_block_PASS[verdicts2-extras_verdict_missing]`
- `test_harness_guards.py::test_ADDA_unsupported_extra_is_a_confirmed_wrong_ACCEPTED_fact`
- `test_harness_guards.py::test_B14_replay_through_the_real_run_event_keeps_the_index_relation[0-0-a lawful EMPTY whole-event answer]`
- `test_harness_guards.py::test_B14_replay_through_the_real_run_event_keeps_the_index_relation[0-1-an abstention only]`
- `test_harness_guards.py::test_B14_replay_through_the_real_run_event_keeps_the_index_relation[2-0-duplicate facts only]`
- `test_harness_guards.py::test_B14_replay_through_the_real_run_event_keeps_the_index_relation[2-1-facts and abstentions]`
- `test_harness_guards.py::test_B16_rejected_is_reported_with_its_real_code_never_renamed_parked`
- `test_harness_guards.py::test_B16_route_refuses_a_map_pointing_outside_the_result`
- `test_harness_guards.py::test_B16_route_refuses_duplicate_and_missing_outcome_indexes`
- `test_harness_guards.py::test_B16_route_refuses_event_set_mismatch[<lambda>-an EMPTY route hides every event]`
- `test_harness_guards.py::test_B16_route_refuses_event_set_mismatch[<lambda>-an EXTRA event was routed]`
- `test_harness_guards.py::test_CONTROL_door_scoped_field_remains_lawful_reader_output`
- `test_harness_guards.py::test_definite_failures_never_none`
- `test_harness_guards.py::test_empty_arm_is_definite_fail`
- `test_harness_guards.py::test_error_table_rule_grouped`
- `test_harness_guards.py::test_false_lane_verdict_increments_wrong_lane`
- `test_harness_guards.py::test_home_fact_correct_sibling_no_park`
- `test_harness_guards.py::test_home_fact_unrelated_driver_parks`
- `test_harness_guards.py::test_home_fact_value_mismatch_parks`
- `test_harness_guards.py::test_home_fact_wrong_period_parks`
- `test_harness_guards.py::test_home_numberless_sibling_pairing_is_enforced_by_the_route`
- `test_harness_guards.py::test_home_slice_must_match_through_the_PUBLIC_ROUTE`
- `test_harness_guards.py::test_home_value_shape_is_decided_by_the_PUBLIC_ROUTE[floor-parked-F9-a FLOOR lacks the matching high endpoint, so it is not a matching home]`
- `test_harness_guards.py::test_home_value_shape_is_decided_by_the_PUBLIC_ROUTE[point-written-None-equal point endpoints, unit, and the other \xa7153 identity fields]`
- `test_harness_guards.py::test_MUT_each_axis_moves_its_own_denominator[fact_type-kwargs0-lane]`
- `test_harness_guards.py::test_MUT_each_axis_moves_its_own_denominator[ordinary item field-kwargs2-field]`
- `test_harness_guards.py::test_MUT_each_axis_moves_its_own_denominator[per_x-kwargs1-field]`
- `test_harness_guards.py::test_MUT_each_axis_moves_its_own_denominator[slice MEMBERSHIP-kwargs5-field]`
- `test_harness_guards.py::test_MUT_each_axis_moves_its_own_denominator[slot scale_multiplier-kwargs4-field]`
- `test_harness_guards.py::test_MUT_each_axis_moves_its_own_denominator[slot value-kwargs3-field]`
- `test_harness_guards.py::test_MUT_equivalent_spellings_must_NOT_move_the_score[measurement SPELLING-kwargs1]`
- `test_harness_guards.py::test_MUT_equivalent_spellings_must_NOT_move_the_score[slice ORDER-kwargs0]`
- `test_harness_guards.py::test_MUT_invalid_grader_rulings_block_PASS[rulings0-ruling_out_of_range]`
- `test_harness_guards.py::test_MUT_invalid_grader_rulings_block_PASS[rulings1-ruling_missing]`
- `test_harness_guards.py::test_MUT_lawful_unchanged_pair_is_the_control`
- `test_harness_guards.py::test_MUT_one_produced_fact_cannot_be_ruled_onto_two_golds`
- `test_harness_guards.py::test_name_errors_never_dilute`
- `test_harness_guards.py::test_numberless_guidance_reaches_the_prior_unit_read_not_an_AttributeError[reaffirmed]`
- `test_harness_guards.py::test_numberless_guidance_reaches_the_prior_unit_read_not_an_AttributeError[withdrawn]`
- `test_harness_guards.py::test_numberless_home_without_a_quote_is_REFUSED_by_the_route`
- `test_harness_guards.py::test_replay_store_serves_EVERY_v2_lane_not_just_metric`
- `test_harness_guards.py::test_rule_bucket_actual_counts`
- `test_harness_guards.py::test_scorer_emits_ambiguous_for_grader`
- `test_harness_guards.py::test_scorer_parks_fiscal_only_future_surprise`
- `test_harness_guards.py::test_scorer_parks_grounded_surprise_without_home_sibling`
- `test_harness_guards.py::test_scorer_requires_complete_meta_per_event`
- `test_harness_guards.py::test_scorer_requires_event_meta`
- `test_harness_guards.py::test_scorer_union_recall_beats_single`
- `test_harness_guards.py::test_scorer_wrong_measurement_drops_accuracy`
- `test_harness_guards.py::test_scorer_wrong_slice_drops_accuracy`
- `test_harness_guards.py::test_state_accuracy_not_diluted`
- `test_harness_guards.py::test_step3_10_du_worthy_false_rows_never_enter_recall`
- `test_harness_guards.py::test_step3_11_a_cross_tier_union_is_REFUSED`
- `test_harness_guards.py::test_step3_11_a_same_tier_union_is_ALLOWED`
- `test_harness_guards.py::test_step3_11_recall_boundary_below_at_and_above[20-18-0.9-False]`
- `test_harness_guards.py::test_step3_11_recall_boundary_below_at_and_above[20-19-0.95-True]`
- `test_harness_guards.py::test_step3_11_recall_boundary_below_at_and_above[20-20-1.0-True]`
- `test_harness_guards.py::test_step3_11_score_arm_uses_that_same_bar_owner`
- `test_harness_guards.py::test_step3_3_a_bad_cik_FAILS_CLOSED_without_a_raw_exception[-empty]`
- `test_harness_guards.py::test_step3_3_a_bad_cik_FAILS_CLOSED_without_a_raw_exception[0000000001-mismatching registrant]`
- `test_harness_guards.py::test_step3_3_a_bad_cik_FAILS_CLOSED_without_a_raw_exception[None-missing]`
- `test_harness_guards.py::test_step3_3_a_bad_cik_FAILS_CLOSED_without_a_raw_exception[not-a-cik-malformed]`
- `test_harness_guards.py::test_step3_3_the_menu_probe_carries_the_MATCHED_company_cik`
- `test_harness_guards.py::test_step3_7_a_reader_exception_is_a_LOUD_failed_run_not_an_outcome`
- `test_harness_guards.py::test_step3_9_the_would_park_formula_is_kept_EXACTLY`
- `test_harness_guards.py::test_union_accepts_tie_resolutions`
- `test_harness_guards.py::test_unresolved_tie_blocks_pass`
- `test_harness_guards.py::test_wrong_driver_name_fails`

### D02 — Historical OD-1 probe module missing (4)

W1/R1: these four tests import retired probe a7_od1_admission; the active grader modules do not. Restore verified historical bytes only for an explicitly historical test scope, or replace a still-required assertion with named proof at the currently used key/admission owner. Do not implement a new OD-1 judge or start later catalog/admission work. Record any genuinely uncovered current requirement as blocking.

- `test_a7_corrections_1454.py::test_od1_door_accepts_plain_and_fenced_identically`
- `test_a7_corrections_1454.py::test_od1_door_refuses_an_evidence_phrase_that_is_not_in_the_quote`
- `test_a7_corrections_1454.py::test_od1_door_refuses_every_malformed_envelope`
- `test_a7_corrections_1454.py::test_od1_prompt_serves_only_the_four_permitted_fields`

### F01 — Required test artifact absent (17)

W1/R1: use the exact frozen artifact required by the fixture, recovered and hash-verified where available. For superseded prompt/manifest/inventory fixtures, port the same behavioral assertion to the matching current approved fixture. Never fabricate a historical proof, re-sign it under its old identity, or weaken the guard. The raw log names the exact missing path for each ID.

- `test_a7_corrections_1454.py::test_the_corrected_prompt_version_is_frozen_beside_its_predecessors`
- `test_a7_source_correction_1487.py::test_an_unowned_difference_REFUSES`
- `test_a7_source_correction_1487.py::test_an_unsupported_patch_REFUSES[claim outside the new quote-<lambda>-claim]`
- `test_a7_source_correction_1487.py::test_an_unsupported_patch_REFUSES[extra field-<lambda>-field]`
- `test_a7_source_correction_1487.py::test_an_unsupported_patch_REFUSES[invalid location (not unique)-<lambda>-occur]`
- `test_a7_source_correction_1487.py::test_an_unsupported_patch_REFUSES[missing source bytes-<lambda>-occur]`
- `test_a7_source_correction_1487.py::test_an_unsupported_patch_REFUSES[stale hash-<lambda>-stale]`
- `test_a7_source_correction_1487.py::test_an_unsupported_patch_REFUSES[stale target-<lambda>-stale]`
- `test_a7_source_correction_1487.py::test_double_build_is_deterministic_and_history_is_untouched`
- `test_a7_source_correction_1487.py::test_prepare_run_is_gated_by_the_lock_bound_preflight_which_refuses_today`
- `test_a7_source_correction_1487.py::test_prepare_run_writes_a_write_once_receipt_naming_exactly_the_targets`
- `test_a7_source_correction_1487.py::test_the_materialization_is_exactly_the_eleven`
- `test_a7_source_correction_1487.py::test_the_targeted_package_is_the_phase1_shape_with_only_approved_bytes`
- `test_harness_guards.py::test_frozen_proof_artifact_has_before_and_after`
- `test_harness_guards.py::test_no_scorer_runtime_imports_a_core_test_module`
- `test_harness_guards.py::test_step1_receipt_is_the_case_source`
- `test_harness_guards.py::test_step3_5_no_credential_machine_path_or_self_hash_is_bound`

### F02 — Old generated Node launcher absent (20)

W1/R1: restore the correct pinned historical generated launcher/manifest for an isolated old-arm test, or update its current-path equivalent through the existing generator. Includes 15 Node nonzero exits whose stderr is missing-launcher, and 5 direct missing-launcher errors. Do not hand-edit generated bytes, launch AI, or revive the retired five-arm configuration.

- `test_harness_guards.py::test_step3_12_the_gate_detects_a_mutation_in_every_protected_class[contract-harness/exp5_prompt_contract.manifest.json-bytes]`
- `test_harness_guards.py::test_step3_12_the_gate_detects_a_mutation_in_every_protected_class[source-keys/K-fields/draft_inputs/{first_input}-bytes]`
- `test_harness_guards.py::test_step3_12_the_gate_detects_a_mutation_in_every_protected_class[writes_disabled-harness/build_launch_manifest.py-made_calls]`
- `test_harness_guards.py::test_step3_12_two_independent_builds_are_byte_identical`
- `test_harness_guards.py::test_step3_5_a_lawful_run_input_set_still_yields_the_exact_156`
- `test_harness_guards.py::test_step3_5_the_committed_plan_still_carries_NO_lock_and_NO_frozen_ids`
- `test_harness_guards.py::test_step3_5_the_reader_launcher_executes_its_EXACT_156_schedule`
- `test_harness_guards.py::test_step3_5_the_runner_REFUSES_before_the_first_call[extra0-has not been reviewed]`
- `test_harness_guards.py::test_step3_5_the_runner_REFUSES_before_the_first_call[extra1-no K-fields lock supplied]`
- `test_harness_guards.py::test_step3_5_the_runner_REFUSES_before_the_first_call[extra2-does not match]`
- `test_harness_guards.py::test_step3_5_the_runner_REFUSES_before_the_first_call[extra3-no exact runtime model ID]`
- `test_harness_guards.py::test_step3_5_the_runner_REFUSES_before_the_first_call[extra4-ALIAS, not an exact runtime ID]`
- `test_harness_guards.py::test_step3_6_a_lawful_first_launch_triggers_NO_retry`
- `test_harness_guards.py::test_step3_6_a_MUTATED_prompt_is_caught_even_with_an_untouched_claim`
- `test_harness_guards.py::test_step3_6_a_second_invalid_answer_stops_with_no_third_launch`
- `test_harness_guards.py::test_step3_6_actual_bytes_match_the_pin_on_BOTH_phases`
- `test_harness_guards.py::test_step3_6_first_pass_rows_need_prompt_evidence_too`
- `test_harness_guards.py::test_step3_6_the_emitted_prompt_hash_equals_the_BYTES_ACTUALLY_SENT`
- `test_harness_guards.py::test_step3_6_the_REAL_launcher_retries_exactly_once_end_to_end`
- `test_harness_guards.py::test_step3_6_writes_happen_ONLY_at_an_ingest_measured_globally`

### F03 — Mutation attempted on a read-only frozen input (2)

W1/R1: copy only the required test input to a fresh durable writable TEST location, pin the original, and mutate the copy. Restore/control in that fixture. Never grant writes to the real frozen source or runtime lock.

- `test_a5_launch_gate_1403.py::test_frozen_source_byte_drift_arms_zero`
- `test_harness_guards.py::test_a1_preflight_is_GO_on_the_live_tree_and_needs_A2s_frozen_runtime`

### P01 — Hard-review fixture lacks its package (22)

W1/R1: supply the exact hard-review run AND its matching package/receipt/finalization bindings. Use a current signed positive fixture or valid isolated historical pair. The no-package refusal is correct; removing that requirement is not a fix.

- `test_a7_corrections_1454.py::test_an_unresolved_reference_stops_the_launch_before_any_call`
- `test_a7_corrections_1454.py::test_defect1_every_guidance_or_surprise_gold_row_carries_its_terminal_suffix`
- `test_a7_corrections_1454.py::test_defect1_no_event_reuses_one_driver_name_across_fact_types`
- `test_a7_corrections_1454.py::test_defect1_the_historical_key_is_preserved_with_its_bare_name_defect`
- `test_a7_corrections_1454.py::test_defect2_a_frozen_source_instant_sidecar_exists_for_every_event`
- `test_a7_corrections_1454.py::test_g2_door_accepts_the_four_lawful_answer_shapes`
- `test_a7_corrections_1454.py::test_g2_door_requires_exactly_the_complete_field_set`
- `test_a7_corrections_1454.py::test_g2_prompt_carries_the_live_rule_and_every_meaning_field`
- `test_a7_corrections_1454.py::test_g3_door_is_strict_and_never_crashes`
- `test_a7_corrections_1454.py::test_g3_prompt_defines_every_bucket_and_shows_valid_json`
- `test_a7_corrections_1454.py::test_g3_two_answers_must_agree_on_a_named_bucket`
- `test_a7_corrections_1454.py::test_quote_only_could_not_identify_a_claim_but_the_card_can`
- `test_a7_corrections_1454.py::test_the_applier_refuses_a_row_whose_bytes_moved`
- `test_a7_corrections_1454.py::test_the_ledger_covers_the_acted_population_exactly_once`
- `test_a7_corrections_1454.py::test_the_reference_card_is_a_structural_whitelist`
- `test_a7_current_1473.py::test_a_current_zero_call_run_reports_ONE_named_not_called_state`
- `test_a7_current_1473.py::test_mutation_after_a_WARM_INVENTORY_cache_refuses`
- `test_a7_current_1473.py::test_mutation_after_a_WARM_MATERIALIZATION_cache_refuses`
- `test_a7_runstates_1470.py::test_a_clean_primary_owing_no_retry_needs_no_retry_directory`
- `test_a7_runstates_1470.py::test_a_completed_retry_keeps_BOTH_attempts_and_selects_the_second`
- `test_a7_runstates_1470.py::test_freeze_needs_no_retry_file_when_none_is_owed`
- `test_a7_runstates_1470.py::test_g1_consumes_the_one_ledger_and_adds_nothing`

### P02 — Historical prepared-run freeze mismatch (10)

W1/R1: use a run whose actual prelaunch view matches its externally accepted pin, or correctly isolate a recovered historical fixture. Never replace expected hashes with newly measured bad bytes merely to satisfy a test.

- `test_a7_g1_precall_freeze_1525.py::test_candidate_and_prompt_tree_and_root_rebuild_byte_identically`
- `test_a7_g1_precall_freeze_1525.py::test_every_batch_binds_the_current_producer_and_one_same_event`
- `test_a7_g1_precall_freeze_1525.py::test_every_lane_occurs_exactly_once`
- `test_a7_g1_precall_freeze_1525.py::test_preflight_zero_problems_and_attempt1_budget_under_ceiling`
- `test_a7_g1_precall_freeze_1525.py::test_the_run_is_empty_and_resumable`
- `test_a7_g1_precall_freeze_1525.py::test_two_blind_lanes_are_blind_and_carry_no_answer`
- `test_a7_g1_precall_freeze_1525.py::test_workflow_groups_are_maximal_under_the_exact_byte_boundary`
- `test_a7_postrun_identity_1521_recovery_1774.py::test_completed_run_loads_against_accepted_freeze_and_reports_5612_once`
- `test_a7_postrun_identity_1521.py::test_completed_run_loads_against_accepted_freeze_and_reports_5612_once`
- `test_a7_postrun_identity_1521.py::test_grading_inventories_derive_twice_identically_with_zero_problems`

### P03 — Current-route pin/era expectation stale (6)

W1/R1: pass a complete valid current prepared-run handle and required external freeze pin to the positive control. Historical-era allowances must be test-local and undone. For error-order assertions, exercise one independent defect at a time; do not weaken the current pin/era guard.

- `test_a6_fixture_isolation_1768.py::test_1_outside_the_fixture_the_gate_refuses_the_old_era_run`
- `test_a6_fixture_isolation_1768.py::test_2_outside_the_fixture_the_gate_accepts_the_current_zero_call_run`
- `test_a6_fixture_isolation_1768.py::test_3_inside_the_fixture_the_old_era_is_permitted_and_still_fully_checked`
- `test_a6_fixture_isolation_after_1768.py::test_after_the_historical_module_the_refusal_returns`
- `test_a7_trace_1471.py::test_raw_drift_after_identity_capture_refuses`
- `test_a7_trace_1471.py::test_the_REAL_downstream_paths_consume_only_the_trace`

### E01 — G2 old wording/six-aspect expectations (3)

W1/R1 plus T07/T09: update exact tests to the current seven-aspect schema and actual uncertainty semantics, with a nearby valid control and false/unknown cases. Do not remove record_matches_source or change correct prose just to match a literal phrase.

- `test_a7_corrections_1454.py::test_g2_output_example_is_valid_json`
- `test_a7_corrections_1454.py::test_g2_prompt_defines_every_aspect_in_plain_words`
- `test_a7_corrections_1454.py::test_g2_two_graders_must_agree_per_aspect`

### E02 — Expected exception versus actual named G1-required refusal (1)

W1/R1: assert the public G23 entry's actual refusal/problem result for absent approved G1. It did not accept the old V1 path. Add the valid current G1/input control; no production behavior relaxation.

- `test_a7_current_1473.py::test_the_old_v1_run_refuses_at_every_live_entry[G23 freeze]`

### E03 — Raw drift rejected with different correct wording (1)

W1/R1: assert refusal on the isolated raw/run identity drift and zero credit, not an old sentence. Keep the unchanged valid run control and ensure no independent relocation/pin failure masks the intended test.

- `test_a7_runstates_1470.py::test_a_mutation_after_identity_capture_refuses_before_any_answer`

### E04 — Missing conservation branch owner (1)

W2/R2: genuine current accounting gap. Reproduce through C.terminals, restore the one-trace branch accounting, then retain both the branch helper check and actual public-path proof. Not eligible for an obsolete-fixture waiver.

- `test_a7_trace_1471.py::test_every_status_and_route_outcome_is_conserved_exactly_once`

### E05 — Durable alias fixture not exposed (1)

W1/R1: present the same exact approved file under both declared durable/served paths in the TEST map; positive alias accepts, different-byte alias refuses. Do not broaden read allowlists to arbitrary paths.

- `test_g1_cached_resume_1781.py::test_the_same_file_under_its_durable_path_is_accepted`

### E06 — Historical authority artifact absent (1)

W1/R1: restore the exact referenced historical authority solely for its generated-contract provenance test, or move the current builder test to its actual live owner with explicit equivalent proof. Do not invent an authority file or treat an old document as current law.

- `test_harness_guards.py::test_RED_contract_builder_reads_archived_authority`

### E07 — Generated artifacts differ from the committed expectation (1)

W1/R1: compare the exact generated file diff and pins. Regenerate twice through the existing owner under the matching current fixture; require deterministic equality and an explicit approved difference. If a real builder defect is reached, reproduce and fix that owner; do not silently bless all drift.

- `test_harness_guards.py::test_a1_the_whole_launch_double_builds_byte_identically`

After W5, preserve this original census and add each exact test's final
outcome or equivalent current proof. Do not erase the old failure history,
retitle setup errors as collection errors, or call this table evidence that
the implementation has been repaired. No tests were run to create this plan.

## Appendix D — Complete H file manifest at final reread

This is the complete 88-file manifest underlying the independent path-relative
hash in Appendix A. All entries were reread after the planning passes and the
manifest was unchanged. Appendices describe baseline bytes, not a repaired
candidate. Paths are relative to H.

```text
98055e556fdb0324c022f8f14db5ec463b4486914df48bda72b6c519e731e649  a1_reader.py
c534022d391e409f48ae65a0ded6bbf7eb428d4a92a00407646cad77f8ef794a  a2_runtime_freeze.json
bbcba73d587a2bc2e8fc34ce27ba555065b52d89480783b2440568cede19c4b2  a6_launch_freeze.py
921a24557d61505925a2ae81bef52d383069dbb6d5482833237179906fd3fe54  a7_conservation.py
1fef8789ae0d0392b4c50d8c22b81feb6dbe97cbc3d2e5a66ff35964df24f7d7  a7_g1_build.py
7a284f30296e698948155923c9ff1cc040eeba8b79dd0c3d22bbfade3a93250d  a7_g1_complete_v2.py
e2386da5f64260acdc7da1a1b44c40c3fcad5a624affd3755b01448ce32d0703  a7_g1_workflow_gate.py
4fce0781e770ce48ca51b6d2b0a412b3357a49ba668160604a88eb39dc738b40  a7_g23_build.py
c247b909c51f23b34947c08891d97f2915c437d6b5779bd0070735e8e1979596  a7_g23_run.py
6ba1218c397191360ee4ea5705c26ce6d0ac6e3b7763baa716105f4d6c022235  a7_key_correction.py
43dcbd35d95d31123741f77f81e41599497101807790649cf7b1167651130751  a7_prepared_run.py
16eb1581255912092d5f97e545affd2700c6ebfdf683e858668f4402bc7b96b5  a7_reference_inventory.py
4addd2f2e4b79bb292a8291a9cfbbcfd1efdc3d637b172ef40e1909275aa9d4a  a7_source_meta.py
dda9db0440a764711739fb533c8af65bce2a854da967b197b05067dd68026314  audit_worker_access.py
8160bcd6246a38b7ebc9cdab1cbf31a8550fa6baec246228bfbd54eeba4a97b4  build_a5_exp5_kit.py
ffbcab3d7c7cc4c461d6828608aa59ddcc21d7d4b12b41f9ed6420f27dc5ed2c  build_exp5_contract.py
b78a733cac842ca68125904dd7d52b66580ff5b30740d2664dbf5810511bdf42  build_final_lock.py
9d3644e0f1b316865188dfa21fd8d1650c73a8a426aa9137399139f209f26075  build_final_lock_v2.py
ee03028747c662c319b238b05ed976d42427089ee1096c334b11d8b974f46825  build_inventory_review.py
a0ab1138792ce2a7bfeded5b94f4b37f99c6562b003eace4494aa92098e68c05  build_kfields_final.py
fb7c820d765565cc19722938caeb8f8f5e4bdefa9c19a0443c48398fda20113d  build_kfields_final_targeted.py
7c5ac0ecac07b3f85f25cae9982f7921ee313405215bea42342a88def861c09e  build_kfields_hard_review.py
b7a72cab000ff3d2d70d76daae2abb89c6973101d4283079f7b721f3cc6176f3  build_kfields_hard_review_targeted.py
d4a0323a43ddd8e68487347652986dedf16a9ec2a277ca41d82a55db3d248ed4  build_kfields_hr_correction.py
d879dd2b9325488a7985b966d53d5db7f065a1ae4a4a89dce480ed08c285ce12  build_kfields_inputs.py
91862afd796cccb523f518ed75ab79383244aef6147ac1072068aa816e916000  build_kfields_key.py
0c1f335077926603011ee78a9ca63315ad158147bcf714dac36f185b88ad6588  build_kfields_key_targeted.py
fb327705f5703d344c413dff6c9f3ba1138cd0e8107898e08de43bdc87577567  build_launch_manifest.py
5022c97789f6502c917f2266980075e13b7f00a0e76fc4fcfa42b0830e162d04  conftest.py
d5830182899461c7a34f3eed3f3cc374a40412618f9c80e2047f029c6a933fb2  decision_rules_1387.txt
b76a9de31fb24cda3736b99ad9919c82fc0cb6d439c0b78bab58974bd5b29625  exp5_prompt_contract.manifest.json
c80f5c7f90fe3902f55f6a5e9c0bfaaa93454b1e31c2368e0938be4325fb005d  exp5_prompt_contract.manifest.v3.json
a13289a8a135fe7f26beaeef1168a219496f197345063c963e677fa7fa452fef  exp5_prompt_drafter.md
421613e2998cb29b4482507b2713bbf225dcd71bdbf61f7cf613871a4e25030c  exp5_prompt_drafter.v3.md
060d7c492d8a8717b75d31e54a52b3bf9c91fb95d54afe1df2cd5e0d8b8792cc  exp5_prompt_producer.md
b8bcbf0f4712218db1578cefbc3508e762b0db938c9fbf44996a98bc6e5f3f57  exp5_prompt_producer.v3.md
c5211a1f8e96b053d0c7688b138bea7cb7e502bb4e6ffdc7456bf194a6f94359  exp5_rev4_package.md
62a5c49ae71f323eff275e98ca60efaae18ca16ca6c15f447c10c9d5d8976154  exp5_rev4_package.v3.md
ff5bad90c6b808ef19613a961bb6616816eb1facff4d58c29ac7ca996ee3d018  g1_fake_state.py
ff4c3a06cbd534796d29f755531880641cb173697151af70ac892b64ad12cf78  key_lint.py
920742cf099fc56ed5773aee6d75e7e7ae180de949a96e2af420faa2f6135c2b  kf_lint.py
bf9323bc3bdc75a45a7381ac97cf0d4e1403f8754f5ac419abe1136f589c3070  launch_exp5_readers.manifest.json
dc9442f344b59fae521dd6a6f672f7f9d627e143e24920977415ff591c995494  launch_kfields_a1.bundle.json
368bf01cb205ccad7e9af90355ab124af5aca5b9efe3f702311f1f4f836b121b  launch_kfields_a1_slice.template.js
d65e4f877ebebfc22f51fb98c3af28ca24c3320772a73046cad90a8955133f28  launch_kfields_drafts.manifest.json
a925ba6ffce6ae14a47c942f5c660c626d13c1060910c2e79055680c7632dbca  owner_rulings_1383.txt
4d51412261aa9a496ca9a0c85d62547152f841e05a2b6fc484aa66af9e07ba0a  raw_transport.py
d5634c6991934a338ec6a236ff98e35cc0101e2ab67dd658cc32f3241be07ab3  run_launcher_fake.mjs
10ccf5263f6bfe61639258530bc19f786b6701306142e039b8179a67c8ff6a2a  run_reader_launcher_fake.mjs
806a7560002a14ed5f3a4c79a78d85be0fac8abf773f8fdf9457c3d902e8abd6  scorers/grade_batch.js
dfe6b5ae3a215856d22ed1d15b49bbc2c1044e1352c046c1f1ae0da3391709c6  scorers/score_exp5.py
0f769167dcac0bb634e57e6d30a030f569264f8be1c14cd6f83cab0385268e52  scorers/score_exp5_current.py
70f300e6b7fea73e1c9ed3c2537674e1c5929c44437de7bf05fcb4127937da82  slice_menu_probe.py
b580b4cd0207bc8f86af6be88b18e5abcd4806cb2537e2e86e78c15dd9470ec0  test_a1_invalid_response.py
84725b336b93b8204a9dd215740b10752cf2561115276078c37009b52a07e559  test_a1_no_tools.py
1b70368af7b63ebecc2a9ef346da017b45b7b5c5db9492ffda9e5ab874991c6a  test_a1_prompt_contract.py
a9930bd275118983c9364810f2560c95290ee354a8e10b2b1888119c0afaabc6  test_a1_serial_transport.py
523ede2853e8ac4b3ffe857e5b7fbc6775200f70ab4af8a173a31a92e78f9e67  test_a5_contract_1401.py
043dd796e63de10dae5ea826d4985000edaca45338351ace39c27ebb4a867635  test_a5_corrected_inventory_1514.py
230494722c01b7501a3bff9fb2c8cbe53949faf05ba475f7328bb166a58da6c8  test_a5_exp5_kit_1400.py
69330170ba6447d2eb30ff497a2cad9d016ae19e9762a03b14589f63eb1ade83  test_a5_final_lock_1513.py
e089811180312bf3dde877ab1431633d7962a98422c75e2b38aa4714be519bc0  test_a5_gate_1469.py
75c48d45c928b83c82084f1b40d7da00fee91a830254b9c286431627feee04a2  test_a5_launch_gate_1403.py
0125323ccb1b9601fa6ca2af9d7ed334080f36fcfc807371b7760cb7f2cb9a52  test_a5_route_1406.py
fe5638d879e8dc8983e1ed2b5c3e788577ef4f03e9c911d0b9ee30e5dab3a316  test_a6_final_lock_1515.py
45cf4561d6d4f423c2537a5c947d6296b414320971e4ba9a69176f42c87933b7  test_a6_fixture_isolation_1768.py
e80a0b3bffa3997749527257a06e8a18f2f4fd0af5eeec6c0f71d75a0455d778  test_a6_fixture_isolation_after_1768.py
83f7bc0387eea070b0ad310aaf21ca45b0c46b2e4063c5c5dc834bb483e7c1af  test_a6_launch_freeze_1409.py
c967001e8758afcfa49d704d48ca9723fa23a564fc596fd227c32f12ee37d7be  test_a6_locked_rows_1476.py
0df220f7926ec1ad9b4428abcbb3984cfc0af2ce0afef6368806424cfb74a053  test_a7_cached_rows_1413.py
e2fa3ec1bde051f051c73944a8ee33a8f49526f8d4ccf9b7d7540ed456ded03c  test_a7_closeout_integrity_1482.py
ef91e0ea9b822b25f00c1190a2f07fed3786bcfc034bb31b6e617dd71d9f5cd9  test_a7_corrections_1454.py
abe8692a07fe7ca8b54611c773479543d8c3ea994266a234ddb5f3aa88625fbd  test_a7_current_1473.py
5870caaff6ce149621faa381431c62fd3913f17eef45c787547e0c3772d0faa9  test_a7_g1_precall_freeze_1525.py
021f6170b47f387e8db2f2596d90af8a0a07c5187870dda3c7c38161d1aed847  test_a7_g23_lifecycle_1464.py
7f73b68155367a4275dba04690ced8d12146271e049040b8cf73e729477514ee  test_a7_postrun_identity_1521.py
fdac03d1da992cab73ba8520e02c0600e98656c14af3f8305d7e2caadab4dc5c  test_a7_postrun_identity_1521_recovery_1774.py
30583d313fd1efcd727d39e2c74f1fb4306a32ebaf75c348ccece31923110b49  test_a7_raw_binding_1483.py
fe585d9ad6a0a2608e0e37d4710d41ced6e561cb657f5a61d42bdbd516165c02  test_a7_runstates_1470.py
bccf746677b8ae4105129bc8a442de7c6172b841af4661d25ebe822b46771ba3  test_a7_source_correction_1487.py
3d5c5e125ae07454401e10d030e1d03dd4f915d83ed0dd05bda841f61b03082a  test_a7_trace_1471.py
5863c78e673a502e9a22a8c53132b345d67fb793cff828fad92b63b540b4c204  test_g1_cached_resume_1781.py
0cf34ca93459e494878b6048a22f176df71e81db5b6869f228bb0264e7533318  test_g1_declared_input_1792.py
292cda334e14449fd2d678650318219d2de5886e112dd555822e14d9965eb66c  test_harness_guards.py
0b669decd55e430fb86271378db177a0b1c2525eaa6ec6455dfbb22d7fdce6e0  v4_findings_1390.txt
11a086123f4081be6561839527625ed42773faa800226520f6b7e01d6d98a1d1  v5_findings_1394.txt
b9842d7db6d3454587fc6bda25ec9bec41c3183832010b2a3f6d5189dda43ef3  v6_findings_1396.txt
2e7ad8f1da440c5c8c4c19da45746e1a24bfdc07fad907afdbd011a60f402165  validate_benchmark_inventory.py
```

## Appendix E — Final planning review and handoff

### E.1 What changed between the three review passes

- Pass 1 traced the live producer/key/identity/meaning/lifecycle/score owners,
  compared the active requirements and later-step boundaries, and enumerated
  the existing regression failures. It found stale conservation code and
  candidate concerns in input binding, publication and final scoring.
- Pass 2 checked public caller paths and independent counterexamples. It
  confirmed the stale slot/branch accounting, mutable handle, direct writer
  and rounded union boundary concerns; identified the error-tail capture
  ordering check; and separated real behavior gaps from setup/fixture failures.
  It cleared old/current scorer coexistence, the compact-index mapping,
  historical reference overrides, existing cache behavior and broader prompt
  rewrites. It made the positive/negative/uncertainty test matrix explicit.
- Pass 3 challenged necessity again, reduced changes to the existing owners,
  kept the error-tail repair conditional on the public reproduction, fixed
  the plan's zero-fact wording so it cannot legalize an empty reply, and
  clarified that a valid TEST fixture can correctly end in FAIL/INCONCLUSIVE.
  It fixed the source-handle remedy to include exact rederived-row comparison,
  distinguished code-checkpoint publication from an A7 pass, and set the
  ordered work units and explicit cut list. No new framework is proposed.

### E.2 Final document checks

- 55 recorded authority/code/evidence file hashes were reread: zero drift.
- The full H manifest was reread: 88 files, same manifest SHA256.
- Recovery HEAD/tree/branch still match section 0; tracked index/worktree
  remain clean. Existing untracked work is not removed, staged or claimed.
- All 198 old failed/error IDs in Appendix C match the frozen comparison
  exactly: 198 unique IDs, none missing, none extra. Every group has a
  concrete action and retains its original failure status until W5.
- The current harness inventory is 31 modules / 757 static test definitions;
  this is explicitly not a claimed count of passing executions.
- The threshold counterexample was checked independently: 100×440 = 44000,
  while 98×449 = 44002; displayed 0.9800 cannot justify a 98% pass. A valid
  exact control is 441/450, where both products are 44100.
- No repository source file was edited, no test/model/Workflow was run, no
  Core command was sent, no watcher or goal was created/resumed, and nothing
  was staged, committed or pushed during this planning task. Only this plan
  file was written. Read-only code/hash/log/document inspection is not
  execution of the planned application tests.

### E.3 First implementation instruction, only after plan approval

Start W0, then W1. Preserve H and the exact real source answer. Use the existing
isolated durable test setup to serve the complete current callable path; fix
its fixture/mapping errors without weakening any guard. Establish a cold
producer→G1→nonempty G2/G3→official-decision TEST control and record the
remaining exact failures. Then proceed through W2–W6 in order. Do not launch
AI, wake Core or publish unverified work as a shortcut. W7 starts only after
the non-AI readiness and independent code-checkpoint gates are met.

The existing regression payload is
`REC/a7_recovery/unit_1957/ledger/a1_aligned_1957.py`. Reuse its isolated-run
pattern in the fresh candidate, not its stale exclusion or narrow top-level
import selection. The child invocation is the existing form:

```text
<isolated Python> -m pytest -q --no-header -rfE -p no:cacheprovider <frozen module list>
```

The module list is the deduplicated current population from section 8.3,
recorded before launch. Save both child stdout/stderr and the actual child
exit. The old payload exits 0 after saving a child failure; therefore a wrapper
exit 0 is never the verdict. Read the saved `child_exit` and raw pytest result.
Do not build another runner to correct this interpretation.

### E.4 Remaining limits, explicitly not waived

This review does not establish an executed public exploit for each static
concern, a passing affected regression, a reviewed new answer key, qualified
fresh model judgments, or a passing A7 score. Those are exactly the gated
implementation/evidence tasks above, not omitted requirements. No amount of
planning can honestly guarantee every unseen output is correct. The plan
requires zero observed wrong accepted facts/identities and measured recall
under the unchanged bars, plus fail-closed accounting for everything unknown.

Planning is complete and ready for the owner's requested vetting. Coding
remains paused until that vetting authorizes implementation.
