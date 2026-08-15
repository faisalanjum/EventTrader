# Step 3 — Rebuild the disabled launcher and real scoring path

## Goal

Connect the verified Step 2 prompt/envelope to the existing launch, raw-reply,
matching, Core dry-run, grading, and scoring owners. Prove the complete path
with fake replies only.

This is one coherent integration unit because the launch record must bind the
same prompt, response bytes, checker, matcher, Core route, and scorer. It makes
no AI call, creates no gold, runs no experiment, changes no production reader,
and writes nothing to Neo4j.

## Fresh-session start

Before acting, read repository `AGENTS.md` and these exact live files:

- `.claude/plans/Drivers/WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md`;
- `.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md`;
- `.claude/plans/Drivers/FinalDesign/ChannelContractV2.md`;
- `.claude/plans/Drivers/FinalDesign/FableExperimentPlan.md`;
- `.claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md`;
- `.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md`;
- `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md`;
- `.claude/plans/Drivers/experiments/WORKORDER_STATUS.md`.

Treat `.claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md` only as a
protected V1 baseline. Then read the exact VERIFIED Step 1 and Step 2 identities
recorded in
`.claude/plans/Drivers/experiments/WORKORDER_STATUS.md`. Recompute all hashes
before editing. Confirm:

- the Core V2 bridge commit remains in the candidate ancestry;
- Step 2 outputs are unchanged;
- the 36-event input manifest is exact;
- V1 remains live and writes remain disabled;
- Step 1 assigns every opened path to Step 3.

Use the topic ownership fixed in Step 1: Final Design owns meaning, the V2
contract owns the public boundary, Core owns executable structure/mechanics,
the Plan owns bars, and the WorkOrder owns run mechanics. No one source may
silently rewrite another topic.

If the current Core replay seam cannot carry the WorkOrder's whole-event answer
without loss, stop with the exact mismatch. Do not invent a second production
route or silently weaken the experiment.

## Fixed scope

Open only the Step 3 rows for:

- prompt assembly at launch time;
- K-fields and EXP-5 disabled launch plans;
- raw reply capture and exact parsing;
- replay of recorded answers through the committed Core V2 dry-run;
- the existing Core fact matcher and EXP-5 scorer;
- grader queue/ingestion, manifests, pins, and focused tests.

Do not modify Core or Fiscal production behavior unless Step 1 identified a
real prerequisite defect and the owner separately moved it into scope. The
normal result of this step is harness-only work reusing committed Core. Do not
edit the authority files, protected V1 files, or `XBRL/**`.

## 1. Reproduce failures first

Write focused red tests for every Step 3 row before correcting it. Derive them
from the receipt, including any active case where:

- a worker reads repository files instead of receiving one prompt;
- prompt/event/model/input drift is not detected;
- raw bytes or decimal precision are lost;
- a wrong-event, missing, extra, duplicate, or overwritten response is accepted;
- old V1 scoring or the duplicate `fact16_checks` engine is reached;
- a scorer reimplements Core validation or matching;
- a fact is double-credited or an unmatched row disappears;
- a missing/invalid grader ruling becomes a pass;
- a union hides an unsafe run.

Every negative has a lawful control. Preserve the red results in the existing
evidence mechanism.

## 2. Assemble one complete prompt

Use the one Step 2 builder. The trusted launcher supplies one preassembled
prompt; a model worker receives no repository path and performs no file access.

Order:

1. the WorkOrder-authorized short role;
2. the shared current rules and exact answer envelope;
3. the untrusted-evidence boundary;
4. the complete event view, last.

The view contains only the fields authorized by the current WorkOrder:
`source_id`, ordered `text_parts`, `ticker`, `fye_month`, `event_date`, and the
point-in-time slice menu. It contains no gold, current-filing XBRL values,
realized returns, future evidence, secrets, or absolute paths.

For a given event and role, prompt bytes are identical across model arms. Model
selection is call metadata, not evidence text. Only the approved gold-drafter
versus reader role preamble may differ.

## 3. Prove the finite event population

Check all 36 primary events, not a sample:

- unique source ID and matching internal ID;
- repository-relative input path and exact byte hash;
- complete ordered source parts and stable part references;
- lawful point-in-time menu and no prohibited leakage.

Keep the OD-11 ULTA-to-LUV replacement disabled. It may be proposed only after
later drafting finds fewer than the official number of sequential-basis facts,
and then requires a new versioned record and review. Add no general substitution
engine.

## 4. Build two separate disabled launch plans

### K-fields drafting plan

Prepare exactly the WorkOrder-owned plan: Sonnet and Opus each receive all 36
events at `effort=high`, blind to one another — 72 planned calls.
Haiku never drafts gold. Fable later adjudicates every unioned candidate and
signs the key; the union itself is never gold. No producer under test can
define its own key.

### EXP-5 reader plan

Prepare exactly the WorkOrder-owned arms: P1 `sonnet_run1`, P2 `sonnet_run2`,
P3 `haiku_run1`, and P4 `haiku_run2` over all 36 events, plus P5 `opus_ref`
over the deterministically selected 12-event sample — 156 planned producer
calls. Same-tier unions only. The former local-Qwen P6 remains withdrawn. The
conditional cheap fallback is disabled unless its official trigger later
fires and Fable/owner separately approves it.

The manifest records 156 producer calls exactly. Later grading volume depends
on the unmatched facts actually produced, so preparation records the
WorkOrder-owned grading formula and hard cap—not a made-up exact count.

These are separate approvals and separate manifests. Neither may launch the
other.

At preparation time, pin the official model roles and resolution rule. Exact
runtime model IDs are resolved and written only immediately before a future
approved run, as the WorkOrder requires. Never freeze an alias as though it
were the final ID.

## 5. Bind the existing manifest and budget owners

Extend/rebuild the existing launch-manifest machinery; do not create a second
fingerprint system. Each disabled plan must bind:

- Plan, WorkOrder, staged V2 contract, and Core foundation identities;
- Step 2 builder/instruction/checker identities;
- every event input and assembled prompt hash;
- launcher template/generated launcher, reply transport, matcher, scorer, and
  relevant test identities;
- model roles, effort, exact active/disabled arms, planned calls, and official
  caps;
- output paths, no-overwrite rule, and `made_calls = 0`.

Use repository-relative paths, raw file bytes, deterministic ordering, and
atomic writes. Exclude credentials, machine paths, volatile values from
reproducible build inputs, and self-referential hashes.

The future K-fields lock does not exist yet. The EXP-5 runner must refuse to
start until its real reviewed hash is supplied; never use a final-looking
placeholder.

## 6. Preserve raw replies before interpretation

The future execution path must, in order:

1. receive raw model text;
2. save the exact bytes and hash before parsing;
3. preserve every paid response even if another response is malformed;
4. refuse overwrite, duplicate, extra, missing, and wrong-event responses;
5. parse once with exact decimal handling and duplicate-key rejection;
6. run the Step 2 checker;
7. bind the checked response to its event, role, run, and manifest.

If a future reply is invalid, the runner may retry exactly once with the same
prompt, as the WorkOrder requires. Preserve both raw replies. A second invalid
reply enters the invalid bucket; it is never coerced or retried again.

Use fake replies in this step. Test malformed JSON, duplicate keys, NaN/
infinity, exponent and high-precision values, very large/small values, a
pre-parsed object, wrong source ID, interrupted batches, and overwrite attempts.

## 7. Replay recorded answers through the real Core route

The experiment reader produces a whole-event answer, while the committed V2
bridge exposes a recorded-reader seam per submitted raw item. Use the smallest
lossless callback inside the existing scorer/test path to replay each produced
fact or abstention through that seam. Do not add a module or wrapper unless the
verified Step 1 closure proves the existing scorer cannot own this callback.

The replay projection is mechanical and test-only:

- make exactly one synthetic text raw item for each emitted fact and each
  abstention, preserving its list kind and original zero-based list position;
- order facts in emitted order, then abstentions in emitted order, and retain
  the exact `(kind, original_index) -> synthetic_index` map;
- copy that record's exact quote into both `quote` and
  `raw_label_or_claim`—never derive a label, value, or meaning;
- keep every item in one event so normal same-event fusion still runs;
- preload the callback with the one already-captured whole-event response and,
  in the same deterministic item order, return only the corresponding fact or
  abstention; never call the model again;
- retain duplicate locators as separate positions, and let Core/accounting and
  the scorer report them rather than collapsing them in the adapter;
- represent a lawful empty whole-event answer as zero synthetic items and
  measure it honestly; do not fabricate an abstention.

If that exact projection cannot pass the current public shape and quote checks
without adding information absent from the response, stop with the mismatching
field. Do not weaken Core, use gold, or build a second route.

Required properties:

- the emitted whole-event set and original indexes are preserved;
- each replayed raw item comes only from that produced answer, never gold;
- the temporary source/company/typed-Driver context is built after the model
  reply from produced `(driver_name, fact_type)` pairs, as the WorkOrder says;
- conflicting emitted types fail closed;
- Core performs its real conversion, fusion, validation, raw-item accounting,
  planning, outcome codes, and durable dry-run audit;
- writes are disabled and an exception remains a loud failed run, not a made-up
  outcome.

Reuse `driver_write_cli.run_event` as it exists at the pinned commit. Do not
copy its rules into the scorer or change production merely to make the harness
convenient.

## 8. Reuse the existing fact matcher

Use `driver/core/fact_match.py` for the adopted matching law. Delete the old
scorer matcher once no caller needs it; do not create another.

The existing owner already guarantees:

- duplicate gold groups are inconclusive before linking;
- produced duplicates collapse for credit but remain a pass-blocking emit-once
  violation;
- automatic matching needs an exact complete V2 record and exact locator,
  unique both ways;
- each fact receives at most one link;
- every unmatched fact reaches later grading in stable order.

Meaning-based matches are decided later only by the qualified grader. No quote
overlap, value equality, fuzzy match, regex, or first-match shortcut may create
a link.

## 9. Preserve honest abstention and grading accounting

- A gold-linked abstention uses an exact locator, counts as a recall miss, and
  enters the would-park numerator and denominator exactly as the WorkOrder
  states.
- A diagnostic abstention outside gold is reported but changes no denominator.
- A produced duplicate earns no extra recall and blocks a silent pass.
- Every unmatched produced and gold fact enters the grader queue.
- Missing, duplicate, malformed, or disagreeing required grader rulings make
  the result incomplete.
- Grading uses only the EXP-0-qualified tier and the WorkOrder's independence,
  batching, retry, and blindness rules.

This step tests grader ingestion with fake verdicts; it makes no grader call.

The WorkOrder's would-park formula is kept exactly:

```text
parked emitted facts + gold-linked abstentions
------------------------------------------------
deduplicated emitted facts + gold-linked abstentions
```

## 10. Implement only the owned measurements

The scorer reports exactly:

- recall per run and same-tier two-run union;
- the WorkOrder's `wrong_lane` metric, interpreted under V2 as wrong
  `fact_type` or the named missing/wrong surprise cases;
- value/shape and `driver_state` accuracy;
- would-park rate;
- confirmed-wrong accepted facts;
- presence disagreement and named error attribution as diagnostics;
- invalid-response rate and rule-of-three bounds required by the WorkOrder.

Use the official denominators. `du_worthy:false` rows never enter recall.
Expected arithmetic in tests must be independently calculated, not produced by
the scorer itself.

Value/shape accuracy remains the WorkOrder's pooled `code_ok/code_all` metric.
Do not replace it with a per-field minimum or silently broaden it to every
field; per-field results outside the locked group are diagnostics.

The pass decision remains exactly the Plan/WorkOrder decision:

- single-run recall at least 95%, or same-tier union recall at least 98%;
- zero wrong fact types/cases counted by `wrong_lane`;
- value/shape accuracy at least 98%;
- `driver_state` accuracy at least 95%;
- would-park at most 10%;
- zero confirmed-wrong accepted facts;
- invalid-response rate at most 2%, per the WorkOrder's reliability gate.
- no emit-once duplicate violation or unresolved duplicate-gold group.

No diagnostic becomes a new pass bar. A union cannot rescue an unsafe arm. A
real omission in the hidden key makes the result inconclusive and requires a
new versioned key; scores are never edited to pass.

## 11. Prove the integrated path with fake data

Derive tests from every changed branch and failure outcome. Cover at least:

- missing/extra/duplicate/reordered events and changed input bytes;
- prompt ordering, event-last boundary, file-access and leakage attacks;
- model-role/effort/arm/cap drift;
- raw-reply loss, precision loss, wrong-event and overwrite attacks;
- lawful and malformed V2 answers, numberless facts, abstentions, and zero-fact
  events;
- Core accepted/refused/parked/skipped/planned outcomes and raw-item accounting;
- duplicate-gold, duplicate-produced, ambiguous, unmatched, and input-order
  matching cases;
- missing/invalid grader decisions;
- each score boundary immediately below, at, and above its official threshold;
- safe same-tier union, refused cross-tier union, and unsafe-run non-rescue.

Use current coverage/mutation/fake-launch machinery. Every changed branch must
have a lawful control. Add no new testing framework unless existing tools
cannot prove a required behavior.

## 12. Rebuild and hand off

Build both disabled plans twice from the same inputs in separate temporary
locations. Require identical filenames, prompt bytes, ordering, manifests,
call counts, and hashes. Mutate one representative member of each protected
class—source, prompt, model setting, contract, scorer, and writes-disabled
flag—and prove the existing gate detects it.

Run the focused Step 2/3 tests, existing EXP-5 harness guards, no-semantic-
pattern gate, manifest/pin checks, and the import-derived affected Core V2
tests. The one final wider regression belongs to Step 4.

Record exact candidate paths/hashes, commands, test identities/counts/skips,
planned calls, zero made calls, and zero writes on `WORKORDER_STATUS.md`. Do not
commit or push the incomplete kit. Codex reviews the exact complete Step 3
candidate once.

## Step 3 is complete only when

- Every Step 3 row is closed and no other row changed.
- One shared prompt builder and envelope serve both future paid jobs.
- Both launch plans are exact, separate, deterministic, and disabled.
- All 36 events and the disabled contingency are accounted for.
- Raw reply bytes survive before parsing and every response is reconciled.
- The smallest replay adapter reaches the real committed Core dry-run with no
  copied production rules and no gold-derived context.
- The existing Core fact matcher is the only automatic matching owner.
- Every fact, abstention, duplicate, unmatched row, outcome, grader ruling, and
  denominator is accounted for.
- Official bars and model-resolution rules are unchanged.
- Every changed branch has a test and lawful control; focused tests are green.
- Two integrated builds are byte-identical.
- No AI call, fetch, graph write, activation, commit, push, reader/kernel build,
  or V1-to-V2 switch occurred.
- The exact Step 4 candidate is recoverable from `WORKORDER_STATUS.md` without
  chat context and Codex has VERIFIED it.
