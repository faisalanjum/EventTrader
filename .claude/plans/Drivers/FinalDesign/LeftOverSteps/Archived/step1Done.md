# Step 1 — Freeze the exact EXP-5 migration scope

## Goal

Produce one complete, reproducible inventory of the EXP-5 exam kit before any
kit behavior changes. This step answers three questions:

1. Which exact files and generated artifacts can affect K-fields or EXP-5?
2. Which current V1 assumptions must change for staged V2?
3. Which exact rows belong to Steps 2, 3, and 4?

This is a read-only audit of code, source data, and external systems. The only
permitted repository output is the smallest inventory receipt needed for the
next session, plus its pointer and hash in the existing
`.claude/plans/Drivers/experiments/WORKORDER_STATUS.md` board. Do not edit
production code, contracts, fixtures, prompts, launchers, scorers, or tests in
this step.

## Place in the approved sequence

The committed Core V2 dry-run bridge is the prerequisite. This four-step job
then regenerates and freezes the EXP-5 kit while V1 remains live. Paid K-fields
drafting, EXP-5, EXP-6, the remaining catalog/identity experiments, the real
reader/kernel, the V1-to-V2 switch, and graph writes all come later.

## Roles

- Core is the only repository implementer.
- Codex reviews the complete bounded result, not every intermediate thought.
- The owner alone approves paid calls, commit/push, activation, or Neo4j writes.

No chat message is authority. A fresh session starts from the live files and
the latest reviewed receipt named on `WORKORDER_STATUS.md`.

## Authority and topic ownership

Read these before acting:

1. Repository `AGENTS.md` and the non-authoritative
   `.claude/plans/Drivers/WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md`
   checklist.
2. `.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md` for meaning and
   ownership.
3. `.claude/plans/Drivers/FinalDesign/ChannelContractV2.md` for the staged V2
   public boundary.
4. Current committed Core V2 code for the executable schema and dry-run route.
5. `.claude/plans/Drivers/FinalDesign/FableExperimentPlan.md` for what EXP-5
   must prove.
6. `.claude/plans/Drivers/FinalDesign/FableExperimentWorkOrder.md` for how it
   must be prepared and scored.
7. `.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md`,
   `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md`, and
   `.claude/plans/Drivers/experiments/WORKORDER_STATUS.md` for procedure,
   current order, and current pins.

This is not one global "newest file wins" ladder. Each owner governs only its
topic: Final Design governs meaning, the V2 contract governs the public
boundary, Core code governs its executable schema and mechanics, the Plan
governs experiment questions and bars, and the WorkOrder governs approved run
mechanics. Code cannot silently amend an experiment rule, and a work order
cannot silently amend production meaning. A conflict inside or across those
topics stops the step for one exact decision.

`.claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md` is the live V1
internal packet. It is a protected parity baseline, not a V2 schema source.
Archived plans, old packages, history, scratch files, tests, and comments are
leads only. Tests prove behavior; they do not create a rule.

If two live owners genuinely conflict and current supersession history does not
resolve them, stop with one exact decision card. Do not guess.

## 1. Freeze the starting identity

Record, from raw commands:

- full HEAD, branch, index tree, origin/main identity already available locally,
  staged paths, unstaged paths, untracked paths, and ignored in-scope paths;
- runtime and dependency versions used by the existing harness;
- hashes of every authority listed above;
- the `XBRL/**` tree identity as a protected, read-only baseline;
- the current pin line at the top of `WORKORDER_STATUS.md`;
- the Core V2 bridge commit `0edb1be860524556134ecdedab248279590b23b9`
  and proof that it is an ancestor of the candidate.

Do not require HEAD itself to equal that bridge commit: these work orders or
separately reviewed documentation may have landed afterward. Instead, account
for every later commit and every local difference.

Any pre-existing status-document change must be either separately reviewed and
committed, or assigned its own inventory row. It must never ride into the kit
because it happened to be present.

Do not fetch, reset, clean, stage, or alter the worktree.

## 2. Derive the reachable file denominator

Start from real execution entry points, then follow imports, file reads,
generated-file dependencies, manifest references, and test collectors. Do not
start from filenames containing `exp5` and call that complete.

Seeds to verify, not a hand-written denominator, include:

- the item-contract builder and generated contract;
- K-fields protocol, drafting wrapper, checker, 36 draft inputs, and their hash
  manifest;
- launch-manifest builder, launcher template, and generated launcher;
- raw-response capture and parsing path;
- EXP-5 scorer, grader queue, and every reachable helper;
- the existing Core V2 schema, locator, matcher, validation, fusion, accounting,
  planning, and audit owners reached by the scorer;
- all pin, manifest, status, guard, mutation, and focused test owners that can
  accept or reject the kit.
- the existing affected-test derivation and exact Driver release command that
  Step 4 must later run; if no single command currently owns that gate, record
  the smallest exact command set rather than inventing a wrapper.

The discovery method must be reproducible. Record each root, every traversal
edge, exclusions, and stable totals. Generated outputs must point back to their
builder and authoritative inputs.

## 3. Freeze the behavior denominator

A behavior row is any condition that can change:

- the model-facing prompt or answer shape;
- evidence location or exact-number transport;
- whether an answer is accepted, refused, parked, skipped, matched, or graded;
- a score, denominator, pass result, launch plan, model setting, or budget;
- a file fingerprint or permission to execute.

For each row record:

| ID | behavior or artifact | real caller | authority | one code owner | current evidence | action | later step | completion proof |
|---|---|---|---|---|---|---|---|---|

Allowed actions are:

- `KEEP` — required and already correct;
- `CHANGE` — required but stale or wrong;
- `DELETE` — reachable duplication or retired behavior;
- `PROTECT` — authoritative/frozen input that must remain byte-identical;
- `OUTSIDE` — proved unreachable from this job;
- `DECISION` — unresolved conflict between current owners.

Every retained file must prevent a named real failure. If an existing owner can
do the job, a new builder, wrapper, checker, matcher, validator, or manifest
owner is forbidden.

## 4. Account for stale V1 behavior

Search the derived closure, not the whole repository, for all V1 assumptions.
The following are known leads, not the complete scanner vocabulary:

- PreparedFactV1 or the old model-owned field count;
- `lane` where V2 uses `fact_type`;
- flat numeric values or retired raw-unit, unit-kind, money-mode, or
  `sequential_evidence` fields;
- global quote occurrence instead of `part_ref` plus per-part
  `occurrence_in_part`;
- missing fact-level `per_x`;
- text evidence that may fall outside the quote;
- model-authored XBRL fields;
- copied field lists, copied validators, old fingerprints, or an exam-only
  FACT-16 engine;
- retired per-X exceptions or acronym guesses.

Classify every raw match as active behavior, generated output, test/invalid
fixture, historical text, dead code, or outside the closure. A match is not a
defect until its real caller and current authority prove it is one. Nothing may
disappear unexplained.

Also derive the semantic-pattern inventory from actual imports. Mechanical
format checks may be lawful; any regex, keyword list, fuzzy match, or exception
that decides source meaning is forbidden.

## 5. Confirm the current V2 comparison surface

Derive it mechanically from the committed owners; do not copy it into a new
owner. The current expected shape is:

- top-level `source_id`, `facts`, and `abstentions`;
- each fact carries the five fact-level keys owned by `PreparedFactV2`;
- `item` carries the current 32 model-owned fields;
- every populated numeric slot carries `value`, `scale_multiplier`, and
  `unit_scale_evidence`;
- source/code-owned XBRL fields are absent from text-reader answers;
- text scale evidence is quote-local;
- locators are per source part.

The counts above come from current official owners. If live derivation produces
anything different, mark a conflict and stop; do not update the plan by memory.

## 6. Verify the complete finite input population

Account programmatically for all 36 approved event inputs and the separately
disabled OD-11 contingency. For each event record its source ID, repository-
relative path, byte hash, internal ID, ordered text parts, and supplied
point-in-time metadata.

Prove zero missing, extra, duplicate, or changed primary events. Do not fetch a
replacement filing or activate the contingency. The contingency remains only
the one WorkOrder-authorized replacement and can fire later only under its
stated gold-drafting condition.

## 7. Produce the one handoff receipt

Reuse an existing manifest/pin owner if it can carry the inventory honestly.
If none can, add one compact machine-readable inventory file; do not build a new
receipt framework. Record its repository-relative path and SHA-256 in the
current section of `WORKORDER_STATUS.md`.

The receipt must contain:

- exact starting identity and authority hashes;
- the complete file and behavior rows;
- stable totals by action and later step;
- the 36-event census;
- every unresolved conflict;
- exact discovery and verification commands;
- before/after Git status proving that only the receipt and status pointer were
  written;
- confirmation of zero AI calls, filing fetches, Neo4j writes, activation, or
  switch.

Codex independently repeats the closure and count checks, then returns
`VERIFIED` or one bounded `CHANGES_REQUIRED` packet tied to the receipt hash.

## Step 1 is complete only when

- The prerequisite bridge and every authority are pinned exactly.
- Every reachable file, generated artifact, rule, test, and input is accounted
  for once.
- Every active stale V1 behavior has a row.
- Every row has one owner, one action, one later step, and a measurable finish
  condition.
- Unknowns and owner decisions are zero, or the step stops without beginning
  implementation.
- Steps 2 and 3 have fixed, non-overlapping row sets; Step 4 owns only final
  proof and publication.
- The receipt is verified and discoverable from `WORKORDER_STATUS.md` without
  any chat context.
- No production behavior, source data, contract, model call, or database state
  changed.
