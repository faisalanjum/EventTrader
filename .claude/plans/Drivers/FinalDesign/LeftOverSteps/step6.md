# Step 6 — Perform the Atomic V1-to-V2 Switch

## Goal

Replace the old public and internal formats with the already-proven V2 formats in one reviewed change.

Before                                After
Old V1 route ─┐
├─ run_event            V2 only ── run_event
Staged V2 ────┘

Writes disabled                       Writes disabled

This step changes which contract and route are official. It must not change fact meaning, decisions, validation, or stored data.

## Required starting state

Do not begin until:

* Step 5 passed on one exact committed candidate.
* Real Fiscal text and machine-tagged filing events passed the complete V2 route.
* The real reader and identity system were used.
* Every input and produced fact was fully accounted for.
* The validation-door mismatch was resolved.
* All five public results were proven.
* V2 still refused every write attempt.
* The live database was unchanged.
* No Step 5 issue remains open.
* The standing switch ruling in Steps.md is in force, and Codex verifies that
  this exact candidate satisfies every condition in that ruling.
* The work starts in an isolated clean tree from the exact Step 5 commit.

If Step 6 reveals a required behavior change, stop and return it to Step 5. The switch itself must contain no new behavior.

## Authority

Apply `FINAL_DESIGN.md` for unchanged product law,
`ChannelContractV2.md` as the exact reviewed public V2 candidate,
`ChannelContract.md` as the V1 file it replaces, `15_CandidateFactPacket.md` as
the separate internal contract to refreeze, and `BUILD_AND_OPERATIONS.md` for
the atomic release order and proof. The exact Step 5 candidate, call graph,
tests, and hashes prove what moves. Status, this work order, comments, commits,
old receipts, and scratch files are leads only.

## Scope

This step includes only:

* making V2 the live public channel contract;
* separately freezing the V2 internal fact contract;
* moving every real caller to V2;
* removing the old V1 route and V1-only code;
* updating active hashes, manifests, tests, help text, and status references;
* proving the switch changed no V2 behavior;
* proving writes remain impossible.

This step excludes:

* database writes or setup;
* enabling schedules, cursors, retries, or automatic runs;
* running Fiscal certification;
* building the catalog, read layer, concept linker, verdict writer, or operating system;
* changing reader or identity behavior;
* changing any fact rule;
* running models except the pre-authorized Sonnet 5 high-effort documentation
  check;
* fetching filings;
* rewriting historical evidence;
* moving folders or performing unrelated cleanup;
* deleting the old Guidance system.

## The atomic rule

No committed or published state may contain only half the switch.

The same switch commit must contain:

* the live V2 public contract;
* the separately frozen V2 internal contract;
* every live caller using V2;
* the old public route removed;
* V1-only production code removed;
* active tests and hashes updated;
* status documents stating the new truth;
* write protection unchanged.

Preparation may happen in an isolated working tree, but no partial switch commit may be published.

## 1. Freeze the exact switch denominator

Before editing, derive a complete inventory from the exact Step 5 tree.

Inventory:

* every production entry point;
* every caller of the public event function;
* every command-line entry;
* every Fiscal builder and submission path;
* every import of V1 or V2 fact classes;
* every active test and proof tool;
* every active document and machine-readable contract block;
* every current contract or packet hash;
* every manifest that verifies a current file;
* every saved artifact used by an active test;
* every write-capable function reachable from the public route.

Classify every V1-looking match as:

* reachable V1 production behavior to remove;
* required behavior whose test must move to V2;
* obsolete V1-only test or helper to delete;
* active documentation or hash to update;
* immutable historical evidence to preserve;
* unrelated text, such as validator labels “V1–V14,” which must not change.

“Zero V1” means zero reachable old Driver contract behavior. It does not mean deleting historical records or unrelated version labels.

Nothing may disappear from the inventory without a classification and evidence.

## 2. Write the switch tests first

Before changing production code, add failing tests proving that:

* V1 is still reachable;
* Fiscal’s live builder still chooses V1;
* the command-line loader still expects V1;
* the old V1 classes still import;
* the temporary V2 contract still exists;
* the active public contract is still V1;
* the internal packet still carries V1 law;
* active hashes still point to the V1 packet or staged contract.

Keep lawful V2 controls beside these failures.

The tests must derive names, fields, and allowed values from their owners. Do not hand-copy another contract list merely to test its deletion.

## 3. Promote the public V2 contract

Replace the contents of ChannelContract.md with the proved V2 public contract.

The promoted document must:

* identify itself as the active V2 contract;
* remove all “staged,” “current versus future,” and “at the switch” wording;
* describe only the behavior proved in Step 5;
* retain the same raw event, evidence, trust-door, scale, result, ledger, and source-completeness rules;
* state the actual shared validation owner chosen in Step 5;
* state that quote, part, and occurrence checking is wired;
* publish the proved `continuity_hints` handoff from its one machine-readable schema;
* state the final receipt behavior rather than the earlier partial behavior;
* state that Fiscal is the first enabled caller, not the only channel governed;
* keep the five public result words unchanged;
* keep database writes disabled.

Update the machine-readable contract block so that:

* every enumerable field and value is mechanically compared with its live code owner;
* the Fiscal raw profile is no longer described as unbuilt or staged;
* every public field has one authority;
* no second schema list becomes an independent owner.

Delete ChannelContractV2.md in the same switch commit.

Do not copy the old V1 contract into an archive during this step. Git history already preserves it.

## 4. Separately freeze the internal V2 contract

Rewrite 15_CandidateFactPacket.md as the internal V2 contract. Do not copy the public contract into it.

The public contract answers:

> What may a channel submit and what result does it receive?

The internal contract answers:

> What objects move between Core’s reader, evidence doors, identity system, preparation, validation, and
> planner?

Derive every enumerable internal field from the live V2 code owners at the exact Step 5 candidate.

The internal contract must distinguish:

* the public raw event;
* the reader's fact or abstention;
* the reader's separate continuity suggestions;
* the fact-level lane, evidence locator, repeated-quote position, and per-share signal;
* the reader-owned item fields;
* Core-owned structured filing fields;
* the identity decision;
* the prepared stored fact;
* the input-to-fact-to-result accounting relation;
* the final public receipt.

Remove V1-only material, including:

* raw-unit guessing fields;
* unit-kind and money-mode hints;
* the old sequential inference field;
* the V1 prepared-fact shape;
* any claim that a channel assembles the internal packet;
* any old path that lets code infer semantic units or names.

Preserve:

* model ownership of meaning;
* code ownership of exact mechanics;
* separate text and structured-evidence trust doors;
* final units and number-scale evidence;
* born-complete creation;
* one identity decision owner;
* one validator;
* one outcome per distinct fact branch and complete accounting per submitted item.

If a final but still-unbuilt feature remains relevant, point to its existing owner and mark it unbuilt. Do not duplicate its rules inside the packet.

Calculate the new packet hash and treat it as the only active internal-packet pin.

## 5. Make V2 the sole public code route

Keep the existing public function name. Do not create a new wrapper.

The smallest valid result is:

* one run_event;
* one accepted public input shape: the V2 raw event;
* one reader;
* two evidence-verification doors;
* one identity system;
* one shared deterministic tail;
* one result receipt;
* no type-based V1/V2 dispatcher.

Remove:

* the V1 branch inside run_event;
* V1-only arguments and compatibility checks;
* the V1 input loader;
* PreparedFactV1;
* RunInputV1;
* V1-only preparation and admission rehearsal code once its required V2 coverage exists;
* dead helpers used only by the deleted route.

Do not rename retained V2 classes or constants merely because V2 is now live. Versioned names are harmless; cosmetic renaming adds risk.

If deleting a V1 module would remove a helper still required by V2:

1. identify the real rule owner;
2. move or reuse only that helper;
3. prove all callers;
4. delete the V1 module.

Do not keep an obsolete module as a compatibility shell.

## 6. Move every caller

Derive the final caller list from the candidate tree after Steps 3–5. Do not rely on today’s list.

At minimum, check:

* Core’s command-line entry;
* Fiscal’s real packet builder and submission command;
* the experiment scorer if it remains an active proof consumer;
* shell commands and workflow entry points;
* tests that call the public route;
* help text and examples that users may execute.

Each caller must:

* submit the V2 raw event;
* use the real shared reader;
* use the real identity system;
* receive the proved V2 receipt;
* keep writes disabled;
* avoid old prepared-fact injection.

A captured old V1 input must now fail at the public boundary before database access, reader use, or planning.

## 7. Finish the Fiscal switch

Fiscal must have one active builder after the switch.

Remove the old Fiscal behavior:

* V1 item construction;
* unit_hints;
* the V1 build path;
* the obsolete V1 public adapter;
* tests whose only purpose was to preserve those retired shapes.

Promote the proved V2 builder to the one active builder and update its real command.

Retain the existing dimension-conversion owner if V2 still needs it. Delete or rehome it only if caller evidence proves the containing V1 adapter is otherwise dead.

Fiscal must continue to:

* group one event at a time;
* preserve ordered source parts;
* copy exact quotes and raw values;
* supply raw structured dimensions only;
* keep its ledger;
* perform no identity, unit, period, slice, or writing decision.

This activates the V2 code boundary, not a schedule, paid reader run, cursor advancement, or database write.

## 8. Preserve every required test while deleting V1 tests

For each V1 test:

* if it proves behavior still required under V2, migrate the behavior to the nearest V2 owner test before deleting the V1 test;

* if it proves a retired V1 shape, delete it with the matching contract reason;

* if it is immutable historical evidence, preserve it outside the active test denominator;

* if its purpose is already proved by a stronger V2 test, delete the duplicate.

Do not retain V1 code merely to keep an old test green. Do not delete a V1 test until its still-lawful behavior is visibly covered elsewhere.

Recompute the complete test-identity inventory. Every removed identity must map to a migrated behavior, retired behavior, or historical artifact.

## 9. Update active documents and pins

Update only active truth:

* FINAL_DESIGN.md: active-contract and internal-packet references only; no meaning change.

* BUILD_AND_OPERATIONS.md: V2 flow, internal packet, public route, and switch completion.

* STATUS_AND_HISTORY.md: exact switch commit, contract and packet hashes, V1 removal, writes-off state, and the conditional documentation-check pointer.

* ChannelContract.md: active V2 public law.

* 15_CandidateFactPacket.md: active V2 internal law.

* active READMEs, command help, tests, and manifests.

* the experiment board or work order only where it remains an active consumer.

Do not modify:

* archived reader records;
* historical receipts;
* frozen old packet artifacts;
* the old packet hash where it is quoted as historical evidence;
* the byte-pinned experiment plan unless Step 2 produced the required explicit amendment;
* unrelated Driver plans.

Replace an old hash only where it claims to identify the current active object. Preserve historical hashes as history.

The existing NAME-13 per-share guard is already flipped to the current written-out naming rule. Verify it remains green; do not reopen or rewrite it.

## 10. Verify the frozen EXP-5 evidence

Do not regenerate the experiment kit merely because the contract file moved.

First prove:

* every frozen kit file still matches its recorded hash;
* its original staged-contract hash matches the historical contract blob it tested;
* the promoted contract preserves every reader-facing field and behavior used by the kit;
* the Step 5 route change did not alter any behavior measured by the completed experiment.

Use the recorded commit when verifying an artifact whose manifest names the deleted ChannelContractV2.md path.

If only status text or the file path changed, preserve the kit unchanged.

If any reader-facing field, rule, validation result, or scoring behavior
changed, stop. The old result no longer proves the new behavior; rebuilding or
rerunning requires a separately reviewed plan. Any bounded rerun uses Sonnet 5
at high effort under the master pre-authorization.

## 11. Exact before-and-after behavior proof

Using Step 5’s frozen real events, saved raw reader replies, identity decisions, source store, and fixed clock:

* run the pre-switch V2 route;

* run the post-switch sole route;

* require identical public receipts;

* require identical prepared facts;

* require identical identities, periods, units, slices, evidence, combination results, validation results, and write plans;

* require identical continuity judgments and relationship plans;

* require identical audit contents;

* allow only the explicitly expected contract-version or file-path metadata difference.

Do not compare against V1 output as the correctness authority. V2 correctness was established in Steps 1–5.

## 12. Required switch tests

### Contract and code identity

Prove:

* ChannelContract.md is active V2.
* ChannelContractV2.md is absent.
* the internal packet is frozen as V2.
* every active packet hash matches.
* every machine-readable contract surface matches its code owner.
* no active document claims V1 is live.
* no active manifest points to a missing current file.

### Reachability

Prove:

* the official entry points reach only V2;
* no production import reaches PreparedFactV1 or RunInputV1;
* the old prepared-fact module cannot be imported;
* Fiscal cannot select its V1 builder;
* captured V1 inputs are rejected before any side effect;
* historical V1 files are not runtime inputs.

Use an import and call-graph check from the real entry points. A text search alone is insufficient.

### Behavioral coverage

Re-run every Step 5 case, including:

* text and structured-evidence inputs;
* all enabled fact kinds;
* every enabled identity decision;
* all five public results;
* split and combined facts;
* repeated quotes;
* lawful and unlawful periods, units, values, slices, and evidence;
* every public failure boundary;
* repeated submissions and changed input order.

### Mutation checks

Prove tests fail if someone:

* restores the V1 dispatcher;
* restores Fiscal’s V1 builder;
* imports a V1 class;
* accepts a retired Fiscal field;
* changes a contract field without its code owner;
* leaves a stale active hash;
* bypasses quote occurrence;
* bypasses the shared validator;
* enables a write;
* silently drops an input/result relation.

### Regression and isolation

Run on the exact candidate:

* focused switch tests;
* complete V2 route tests;
* reader and identity-system tests;
* Fiscal tests;
* Core tests;
* source-location tests;
* experiment replay tests still active after Step 2;
* full repository regression;
* isolated zero-credential tests;
* full test-identity reconciliation;
* 100% coverage of every new or changed behavior branch and exception outcome.

Use the existing coverage owner. Do not add a coverage framework solely to
produce a percentage.

No test may fetch a filing, call a model, or write to the database.

## 13. Database and side-effect proof

Before and after the exact switch candidate:

* run fresh read-only database counts;
* verify relevant node, relationship, rule, and sentinel state;
* verify the database transaction state is unchanged;
* verify the old Guidance graph is unchanged;
* prove enable_writes=True fails before mutation;
* prove the environment write flag cannot bypass the V2 refusal;
* prove the production adapter still refuses write transactions;
* prove no Fiscal cursor advances;
* prove no model call or filing fetch occurred.

Preserve XBRL/** and all protected Fiscal artifacts byte-for-byte.

## 14. Minimality audit

The final production path must contain:

* one public event function;
* one active public contract;
* one internal packet contract;
* one Fiscal builder;
* one shared reader;
* two evidence trust doors;
* one identity system;
* one conversion owner;
* one duplicate-combination owner;
* one validator;
* one planner;
* one audit owner;
* no V1 compatibility layer;
* no experiment import in production;
* no duplicate schema;
* no new semantic string list, number, threshold, regular expression, or special case;
* no unrelated refactor.

Every changed line must be required by promotion, caller migration, deletion, pin movement, or proof.

## 15. Mandatory blank-context document check

This switch changes a live contract and is a major release handoff. The standing R8 rule therefore requires one fresh reader check.

This is the only AI-dependent action in Step 6. Use one independent Sonnet 5
high-effort reviewer that did not author the switch documents; no separate
owner approval is required. Pin its exact runtime identity; if it is unavailable or
changed, stop rather than substituting another model.

Procedure:

1. Prepare the exact seven live files:

   * FINAL_DESIGN.md
   * ChannelContract.md
   * BUILD_AND_OPERATIONS.md
   * STATUS_AND_HISTORY.md
   * 15_CandidateFactPacket.md
   * FableExperimentPlan.md
   * FableExperimentWorkOrder.md

2. Put the future unique result-record path into the tested documents where required.

3. Commit the switch locally but do not push it.

4. Create a detached clean worktree at that commit.

5. Hash all seven files before the reader starts.

6. Run the existing R7-amended ten-question blank-context test with its locked grading rule.

7. Require 10/10.

8. Recheck all seven hashes and require 7/7 unchanged.

9. Run every prescribed command with its actual exit status checked.

10. Add one append-only result record after the run without changing the tested seven files.

A failed, incomplete, overloaded, or hash-mismatched run does not pass.

## 16. Commit and push sequence

1. Build and test the complete switch in an isolated tree.
2. Stage only the reviewed switch paths.
3. Record the exact staged tree hash and file manifest.
4. Independently verify the staged tree.
5. Verify that the exact staged switch satisfies the standing owner ruling in
   Steps.md; do not ask again when it does.
6. Commit one local atomic switch commit.
7. Run the mandatory blank-context check against that commit.
8. Commit the append-only check record separately, touching none of the seven tested files.
9. Re-run the final deterministic, zero-write, and identity checks.
10. After the full step passes, normally push the exact Codex-verified commits
    under the standing ruling in `Steps.md`.
11. Push normally—no force and no history rewrite.
12. Verify local main, remote main, commit, and tree identities match.

## Stop conditions

Stop if:

* Step 5 is not fully closed;
* a switch edit changes behavior;
* an active caller cannot move in the same commit;
* a required V1 test has no V2 replacement;
* the internal V2 packet cannot be derived unambiguously;
* a live plan conflicts with the promoted contract;
* the frozen experiment evidence no longer proves the active behavior;
* any write becomes reachable;
* any unplanned or over-ceiling model call occurs, or a source fetch falls
  outside the master public-source ruling;
* the database changes;
* an unrelated file overlaps the candidate;
* the blank-context check is not 10/10;
* any active pin or test identity remains unexplained.

## Completion condition

Step 6 is complete only when:

* V2 is the sole active public contract;
* the internal packet is separately frozen as V2;
* every live caller uses V2;
* the old public route and V1-only production code are absent;
* Fiscal has one V2 builder;
* captured V1 input fails closed;
* all still-required V1 test behavior is covered under V2;
* every active hash and manifest matches;
* the frozen experiment evidence remains valid;
* pre-switch and post-switch V2 behavior is identical;
* all deterministic and mutation tests pass;
* the blank-context check passes 10/10 with unchanged file hashes;
* the database, old Guidance, protected artifacts, and cursors are unchanged;
* V2 still refuses writes;
* the exact commits and remote identities are verified;
* no in-scope issue remains.

After this, Step 7 builds and qualifies the production catalog. Database writes still remain off.
