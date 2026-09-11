# Next A5/A6 reuse gate — read-only evidence, not a completed packet

Historical pre-implementation notes. The current candidate, completed TEST
evidence and remaining approval gates are recorded in `WORK_LOG.md`.

Core remains on Codex2005, collecting66 primary reviews. Do not send a new
task before its one terminal reply or interrupt valid calls for these notes.
The source-key code handoff is frozen in unit2005; its Core review is pending.

The live Step1 A5/A6 and Plan A7 evidence-reuse amendment require a SEPARATE
evaluation binding over the unchanged original answers, not an A5 new-run
preparation and not a relabelled original run. The real key must be independently
locked before an actual evaluation packet is approved. No A5/A6 implementation,
real freeze, grading or model call was performed in this unit.

## Reproduced boundary

`probe_saved_answer_entry.py`, `attempt_codex_reuse_entry2006_b`, exit0:

- Original A3 plan SHA ff259bac38c5b939f99aed05c026661b62af8d2c8ffedfe2fb6d91c3754409ce.
- Original receipt SHA8760b52712ac233826e98486dce043f86ae007ffaa373504ac8f761a2bc7fd0e.
- Original closeout SHA2f15d98ffafe6b1b193fdb57e4b04de1158534499c126d4cc3dad495809c832f.
-36 events,191 items,382 scheduled/382 primary-valid/0 missing; existing
  receipt-contract and closeout validators both return no problems.
- The original run has no plan directory and its original plan has no `arms`
  field. This is lawful for its original A3 transport door.
- The current `a7_prepared_run.load` refuses at `has no plan/`: it requires an
  A5 new-producer manifest and re-derived A6 pre-launch freeze. The TEST-signed
  key itself passes its A5/G1 consumers (unit2005); the missing piece is the
  separate saved-answer evaluation identity, not an answer or key failure.
- Stdout SHA dcebe1df14d996970585ec3cf70b59565a782d7875184cc304929d6f99cdc7fc.

Attempt a stopped on a TEST script's wrong receipt-constant module; corrected
to K.RECEIPT_NAME. That setup error is not the reproduced boundary above.

`probe_saved_answer_proof.py`, `attempt_codex_reuse_proof2006_a`, exit0,
independently re-ran the actual native/transcript auditor and whole primary/
retry reader on the live original store:33 native workflow states,382 returned
rows,382 proved answers,382 served, no audit/primary-retry/raw-binding problem.
Every answer hash is retained in that output; stdout SHA
42e9725476b5c96726a5ec7482727b3736302105d196ec931b618dc9e3caefbe.
The33 workflow containers hold382 independent model replies; do not confuse
container count with answer or call count.

## Bounded remaining decisions at that gate

1. Preserve every original input, prompt, manifest, native result and raw reply.
   Use the existing receipt/auditor/parser/no-write route. Do not transform an
   answer, manufacture historical A5 artifacts or call A5.prepare for reuse.
2. Give the separate evaluation packet one identity owner. Bind the original
   run/actual prompt/model/settings, new independent key, reviewed code and
   complete two-arm schedule; reject changed or missing bindings. A7's current
   prepared-run owner is the relevant entry, not a parallel semantic grader.
3. Keep the original prompt era explicit. The existing PR.current_era gate
   assumes a newly prepared current-era producer; any amended reuse route
   must require the independently pinned evaluation identity. Never relax
   historical/current-run isolation globally or credit the three later rules.
4. Derive the full denominator from the original schedule, not returned
   answers. The current G1 denominator test already proves36/191/382 and
   exact key fact counts; a real evaluation plan still has to supply those
   fields honestly. L1/L2 to P1/P2 already has one owner in A5.arm_of_lane.
5. Derive original vs new spend without counting the382 original replies
   twice: the new source-only key lock already includes those prior calls.
   A6.ledger(run_dir) currently assumes supplied producer calls happened
   AFTER the lock; a reuse evaluation must state and prove the actual order.
6. Test the complete unchanged-raw -> parser -> no-write route -> grader packet
   and its identity/missing/invalid/duplicate cases before real grader calls.
   Reuse existing grader/proof/accounting owners; no new semantic matching,
   fixtures pretending to be native evidence, production redesign or Qwen.

These are direct consequences of the owner-approved reuse amendment. They
are not a request to rebuild the grader, re-run382 answers, or audit later steps.
The original scored-run path must remain unchanged and its applicable
regressions must pass. Do not treat these read-only notes as implementation
proof or a finished A5/A6 step.

## Direct consumer trace — before selecting the implementation

- PR.load/current currently owns the required A5 manifest and A6 pre-launch
  identity. G.run_of refreshes that identity on cold use; on warm use it checks
  PR.current_era plus the private exact whole-run digest. Preserve both checks.
- G.effective_slots already selects the original scheduled raw paths and
  invalid-only child correctly via RT.a1_plan_for_run/ordinals/finalizations.
  Reuse this code, not a second saved-answer reader or a copied response tree.
- G.materialize uses the unchanged a1_reader, full trace and A5.arm_for_call.
  Its denominator asks for plan.arms, absent from original A3 metadata. Its
  meta.events currently uses len(base_key), while the approved required count
  uses the full plan. The confirmed TEST key has33 item-bearing sources and
  the original plan36 sources; this specific count distinction must be tested
  through actual materialize after the entry is connected. Do not assume the
  previous denominator-only test proved full materialization.
- G23.load_verified_inputs pins the producer input manifest through the
  historically named a5_manifest_sha256 field. It must read the ORIGINAL source
  manifest hash for reuse; do not label an A3 source manifest as a new A5 run.
- A6._locked_rows already gives the one signed-key baseline; A6.ledger adds
  supplied producer calls as post-lock spend. The source-key initial package
  binds the same original launch_kfields_drafts.manifest.json and records382
  before its own calls. Any reuse accounting must verify that order through
  those existing bindings, not blindly subtract382 or suppress ledger rows.
- G1/G23 grader prompts, parsers, matchers, score formulas and production
  route do not need redesign for this metadata change. G.LANE is its own
  unchanged Sonnet binding; source-key role binding must never alter that role.

Preferred boundary to evaluate: extend the existing run/evaluation identity
and freeze owners for an explicitly pinned saved-answer evaluation, retaining
the original run path and original era. Avoid broad monkeypatch scopes or
fake A5 artifacts. No final implementation choice is asserted by these notes;
test the real entry and complete consumers before approving one.
