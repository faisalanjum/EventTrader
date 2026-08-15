# Step 5 — Prove the Complete V2 Route Without Database Writes

## Goal

Prove that every component built in Steps 3 and 4 works together correctly on real Fiscal events.

Fiscal source event
→ one shared meaning reader
→ one identity decision system
→ period, unit, slice, and value preparation
→ duplicate combination
→ one shared validator
→ write plan
→ complete result receipt

The current V1 route remains active. Database writes remain impossible. This step proves V2 readiness; it does not activate V2.

## Required starting state

Do not begin until:

* Step 3’s shared reader is frozen, committed, and independently verified.

* Step 4’s identity decision system is frozen, committed, and independently verified.

* The current Core and Fiscal commits, trees, dependency versions, contract hashes, model settings, and test identities are recorded.

* The exact eligible Fiscal event population is derived from the live tree.

* The working tree is separated from unrelated user changes.

* No unresolved Step 3 or Step 4 defect affects this route.

* Any required saved model answers are present and hash-verified.

* The live database baseline is measured through read-only queries.

If any condition is missing, stop. Do not replace a missing production component with a test shortcut.

## Authority

Apply `FINAL_DESIGN.md` §§1–9 for product behavior, the frozen staged
`ChannelContractV2.md` for the candidate public route, the active
`ChannelContract.md` and `15_CandidateFactPacket.md` only to preserve V1 until
Step 6, and `BUILD_AND_OPERATIONS.md` §§5 and 11 for ordering, outcomes,
validation, planning, audit, and no-write behavior. The signed Step 2 memo and
reviewed Step 3/4 outputs own their measured choices and exact interfaces.
Current code, tests, and fresh read-only data prove implementation claims.
Status, this work order, comments, receipts, and history are leads only.

## Scope

This step includes only:

* connecting the real shared reader;

* connecting the real identity decision system;

* using the existing value, unit, period, slice, evidence, identity, duplicate-combination, validation, audit, and write-planning owners;

* completing the public result receipt and its lifecycle;

* resolving the validation-door wording or implementation mismatch;

* proving both text and machine-tagged filing facts through the same public V2 route;

* proving every reachable result, failure, split, and combination path;

* proving database writes remain impossible.

This step excludes:

* activating V2;

* deleting V1;

* changing Fiscal’s live command to V2;

* unplanned or over-ceiling model calls, or any model other than Sonnet 5 at
  high effort;

* writing to the database;

* creating database rules or special period records;

* building the catalog, historical reader, concept linker, verdict writer, schedules, retries, monitoring, or other channels;

* upgrading dependencies without a reproduced requirement;

* broad cleanup or file movement;

* importing production behavior from experiment code.

## Frozen design rules

* There is one public event entry point.

* There is one shared meaning reader.

* There is one identity decision system.

* There is one owner each for conversion, duplicate combination, validation, audit, and write planning.

* Text and machine-tagged facts have different evidence-verification doors but join the same later route.

* The channel supplies source material; Core owns final validation, identity, outcomes, and write planning.

* Meaning decisions come from the approved reader or identity system, never from new code patterns.

* No semantic word list, regular expression, threshold, exception, or example-specific branch may be added unless derived from an official standard or frozen contract.

* Uncertain facts are skipped or parked. They are never guessed into acceptance.

* Every accepted fact must be fully supported.

* Every submitted item must be accounted for.

* V2 must reject every request to write during this step.

## The two evidence doors

### Text evidence

The shared reader proposes the meaning and fact fields.

Core must then prove:

* the named source part exists;
* the exact quote occurs inside that part;
* the stated occurrence number selects the intended repeated quote;
* text scale evidence appears inside that quote;
* the reader did not supply fields owned only by Core;
* the fact passes the common preparation and validation route.

Reuse the existing quote-occurrence function. Do not create another locator.

### Machine-tagged filing evidence

The same reader supplies the business meaning. Core supplies and verifies the structured filing evidence.

Core must prove:

* the concept, reporting context, unit, scale, period, dimensions, and source pieces agree;
* the channel did not invent the internal slice representation;
* Core derives that representation through its existing owner;
* unit_scale_evidence is null because the structured filing fields provide that proof;
* model-supplied source-owned filing fields are refused;
* the fact then enters the same preparation, identity, combination, validation, and planning route as a text fact.

Neither door may bypass the shared validator.

## Required processing order

The proven order must be:

1. Check the event envelope.
2. Establish the ordered input-item denominator.
3. Locate and verify the source.
4. Run the shared reader and preserve `continuity_hints` separately from facts.
5. Verify each fact and rename suggestion through the existing evidence owner.
6. Run the identity and continuity decision systems.
7. Prepare exact value, unit, period, slice, evidence, and identifiers.
8. Combine compatible duplicate fragments.
9. Validate each completed combined fact exactly once.
10. Produce the write plan without executing it.
11. Produce one complete receipt.
12. Finalize one immutable audit record.

Do not validate incomplete fragments before combination. Do not convert the combined fact back through a constructor intended for a single reader proposal.

## Resolve the validation-door mismatch

The staged V2 contract names validate_via_production, while the current route converts facts, combines them, and then calls the underlying shared validator.

Before changing code:

1. Derive every live caller of validate_via_production.
2. Establish whether any required production consumer needs the combined conversion-and-validation function.
3. Reproduce the mismatch through the public V2 route.
4. Add a lawful control showing that complementary fragments must combine before validation.

Then apply the smallest valid result:

* If the combined helper has no required production consumer, delete it and update the staged contract to name the existing conversion owner and shared validator accurately.

* If a required consumer exists, adjust the single existing owner so it can validate the completed combined value without repeating conversion.

Forbidden solutions:

* another validator;
* a wrapper used only to satisfy the contract’s wording;
* type-based bypasses;
* duplicated checks;
* validating fragments early;
* changing the contract merely to excuse incorrect behavior.

If the staged contract changes, record the new hash. In Step 6, verify whether the frozen experiment kit remains valid; regenerate it only if the changed contract affects its behavior or bytes.

## Result receipt

Reuse the event source identifier and the input item’s zero-based position. Do not invent public receipt identifiers, branch identifiers, queues, or a second receipt store.

A completed result contains only:

* overall status;
* optional overall reason code;
* ordered item-result rows.

Each item-result row contains only the frozen fields:

* input position;
* final fact identifier when one exists;
* one of the five public decisions;
* governed reason codes;
* human-readable detail that production code never parses.

The five public decisions remain exactly:

* written
* merged
* parked
* skipped
* rejected

Dry-run status is not a sixth decision.

A rename suggestion creates no new public decision. Its judgment and
relationship plan stay in the existing write plan and audit; fact accounting
remains unchanged.

## Complete input accounting

Every submitted item must have one receipt group.

* No produced fact: exactly one terminal row.

* One produced fact: exactly one fact row.

* One input split into several distinct facts: one row for each distinct fact, all carrying the same input position.

* Several branches of one input combine into one fact: one row.

* Several different input items combine into one fact: one row for each original input position, sharing the final fact identifier and result.

* A split with accepted and parked branches: retain both results.

* Repeated processing of the same branch must not create duplicate rows.

* No branch may receive contradictory final decisions.

* Do not collapse several results into a fabricated “worst” result.

An item-level failure must not erase successful sibling items. An event-level failure before a trustworthy item denominator exists must fail loudly rather than inventing partial results.

## Result meaning and lifecycle

* written: the dry-run plan predicts creation of a new fact.
* merged: the dry-run plan predicts safe reuse, filling, updating, or deduplication.
* parked: the item is preserved for later review because evidence is insufficient.
* skipped: the reader intentionally produced no fact.
* rejected: the item or its evidence violated a frozen rule.

Only the existing “source unavailable” reason promises automatic retry. Do not create retry behavior here.

Dry-run receipts:

* prove what would happen;
* do not claim anything was stored;
* do not advance a live Fiscal cursor;
* do not mark an event permanently completed.

A loud failure or unfinished run must also leave the live cursor unchanged.

## Test-first execution order

### 1. Freeze the candidate

Record:

* Core and Fiscal commits and tree hashes;
* staged and unstaged state;
* dependency and model versions;
* contract hashes;
* source-event and saved-answer hashes;
* test identities;
* read-only database baseline.

### 2. Derive the complete denominator

From live code, derive:

* the public entry point;
* every reachable production function;
* every reader result;
* every identity decision;
* every evidence-door branch;
* every preparation failure;
* every combination result;
* every validation failure;
* every planner result;
* every public decision;
* every exception;
* every eligible real Fiscal event and item.

Classify every row as exercised, unreachable with proof, or an explicit blocker. Nothing may silently disappear.

### 3. Prove the production components are real

Write failing public-path tests showing that:

* prepared semantic facts cannot be injected as a replacement for the real reader;
* identity decisions cannot be injected as a replacement for the real identity system;
* experiment modules cannot become production dependencies.

Tests may supply frozen raw model response bytes at the transport boundary. They may not supply already-decided facts.

### 4. Freeze receipt behavior

Write failing tests for every accounting and lifecycle rule before changing receipt code or contract text.

### 5. Resolve validation ordering

Write the failing duplicate-fragment case and lawful control. Then make the smallest owner-level correction.

### 6. Connect the shared reader

Call the one Step 3 production reader. Do not copy its prompt, parser, schema, or source checks.

### 7. Connect the identity system

Call the one Step 4 production decision system. Do not copy its candidate search, judge rules, or decision table.

### 8. Prove both evidence doors

Exercise text and machine-tagged evidence through their existing owners and prove they join the same later route.

### 9. Prove the shared tail

For every fact, prove the order:

prepare → combine → validate once → plan only

### 10. Run real-data replay

Replay every eligible real item and account for every excluded item with a measured reason.

### 11. Run the complete proof set

Run focused, affected, full, isolated, input-order, repeat-run, and mutation checks on the exact candidate.

### 12. Freeze the reviewed result

Recompute all identities and verify the exact staged tree independently.

## Required behavior coverage

### Fact kinds

Prove all four:

* measured value;
* company guidance;
* result versus a comparison;
* action or event.

Include:

* numeric and numberless guidance;
* lawful guidance using an earlier unit;
* every approved comparison basis;
* missing or conflicting comparison basis;
* impossible time wording;
* lawful periodless action or event;
* actions or events with real periods.

### Identity decisions

Prove every enabled Step 4 decision:

* attach to an existing cause;
* adopt a confirmed candidate;
* create a new cause;
* skip;
* park.

Also prove:

* different wording does not force a merge;
* insufficient evidence does not create;
* ambiguous candidates park;
* rename or continuity declarations are used only when proven;
* every suggestion is source-bound, judged, and either planned or refused;
* disabled decisions remain unreachable.

### Evidence cases

Prove:

* unique quote;
* repeated quote with the correct occurrence;
* identical quote in different source parts;
* wrong source part;
* missing quote;
* wrong occurrence;
* changed reader quote;
* lawful text scale proof;
* missing text scale proof;
* lawful structured scale proof;
* model attempt to provide structured filing proof;
* channel attempt to provide Core’s internal slice representation.

### Period, unit, value, and slice cases

Cover every reachable branch, including:

* instant and duration periods;
* lawful lane-specific missing period;
* frozen special periods where allowed;
* exact decimal values;
* signed, zero, large, and scaled values;
* lawful units and unit mismatch;
* empty, single, and multiple slices;
* provisional and excluded slice behavior;
* stable identifiers under harmless input ordering changes.

Use a small branch-covering matrix. Do not create every possible combination when component tests already prove independent internal rules.

### Split and combination cases

Prove:

* one input to one fact;
* one input to several facts;
* several inputs to one fact;
* several branches of one input combining;
* accepted and parked branches from one input;
* complementary fragments combining safely;
* conflicting fragments refusing combination;
* repeated identical input;
* input-order changes;
* retry of the same event.

### Failure boundaries

Prove:

* malformed event envelope;
* malformed item;
* source missing;
* source ambiguous;
* reader abstention;
* malformed reader response;
* text evidence failure;
* structured evidence failure;
* identity system park or failure;
* preparation failure;
* combination conflict;
* validation refusal;
* planning failure;
* audit failure;
* unexpected programming error.

Do not convert a programming fault into a normal channel rejection.

### Public decisions

Exercise all five public decisions through the real public route. If a decision is unreachable while writes are disabled, prove its dry-run planning equivalent without bypassing production code.

## Real-data proof

Derive the current Fiscal population programmatically. Historical totals are leads, not the denominator.

For every discovered event and item, classify it as:

* eligible and replayed;
* source unavailable;
* quote mismatch;
* missing frozen reader answer;
* outside the approved Fiscal scope;
* another named, evidenced exclusion.

Use:

* every currently eligible Fiscal V2 item;
* real text evidence;
* real machine-tagged filing evidence;
* real examples of every enabled fact kind;
* signed independent expected answers from the frozen Step 1 key, source evidence, or an official standard.

Never derive expected answers from the code being tested.

If a required real case lacks a frozen raw reader answer, freeze the smallest
exact Sonnet 5 high-effort call packet and run it under the master
pre-authorization. Do not substitute a prepared fact or exceed the packet's
call ceiling.

Report:

* total events and items;
* accepted, parked, skipped, and rejected counts;
* wrong accepted facts;
* missed lawful facts;
* precision;
* measured recall;
* every unexplained difference.

Completion requires zero observed wrong accepted facts. Before accepting recall
loss, prove no deletion, existing-owner reuse, or smaller general correction
recovers it without reducing precision; then measure and explain the residual.

## Database safety proof

Before and after the run:

* query the live database read-only;
* record relevant node, relationship, and rule counts;
* confirm the production write adapter never opens a write transaction;
* confirm every enable_writes=True attempt is refused;
* confirm no cursor or production completion record moves.

Use controlled in-memory or temporary test state for existing-fact merge cases when the live Driver graph is empty. Do not seed the live graph.

If unrelated live database activity changes the measured state during the proof, mark the run inconclusive and repeat it against a stable read-only snapshot.

## Audit proof

One run produces one immutable audit record containing:

* exact input;
* source identities;
* reader identity and raw response hash;
* identity-system identity and decision evidence;
* continuity judgments and relationship plans;
* prepared facts;
* evidence-door results;
* combination decisions;
* validation results;
* write plan;
* complete public receipt;
* failure state when applicable.

Prove:

* audit identifiers are unique;
* earlier audits cannot be changed;
* source-gate failures are audited;
* failed runs do not claim final success;
* no second audit or receipt engine was added.

## Test requirements

Run on the exact candidate:

* focused Step 5 tests;
* Step 3 reader tests;
* Step 4 identity tests;
* V2 route and raw-accounting tests;
* text and structured-evidence tests;
* combination, validation, outcome, audit, and planning tests;
* affected Fiscal and source-location tests;
* full Core and Fiscal regressions;
* isolated zero-credential tests;
* input-order and repeat-run tests;
* coverage for every new or changed behavior branch.

Mutation or equivalent checks must prove tests catch removal or bypass of:

* reader schema checks;
* source binding;
* quote occurrence;
* structured evidence verification;
* internal slice derivation;
* identity decision;
* continuity-hint source binding, judgment, and plan preservation;
* conversion-before-combination;
* combination-before-validation;
* shared validation;
* input accounting;
* write refusal;
* audit finalization.

Do not create a new proof framework unless the existing test owners cannot express a required case.

## Minimality review

Before completion review, prove production contains:

* one public run_event;
* one shared reader;
* one identity decision system;
* one conversion owner;
* one duplicate-combination owner;
* one validator;
* one planner;
* one audit owner;
* zero production imports from experiment code;
* zero duplicate prompts or schemas;
* zero new semantic regular expressions, vocabularies, thresholds, or example exceptions;
* zero unused wrappers, compatibility layers, or future-only hooks.

Delete temporary injection seams that are no longer needed. Preserve only seams required for raw transport testing.

## Protected behavior

The following must remain unchanged:

* V1 behavior and output;
* active V1 contract;
* active internal V1 packet;
* protected Fiscal artifacts;
* old Guidance data;
* unrelated repository files;
* graph contents.

The staged V2 contract may change only to close a proven Step 5 mismatch.

## Stop conditions

Stop and request a ruling if:

* Step 3 or Step 4 is not actually complete;
* a required rule has no frozen owner;
* real reader answers are missing and the required Sonnet 5 calls cannot be
  bounded inside this step;
* a proposed fix introduces a second owner;
* validation cannot occur after combination without changing frozen behavior;
* the public result contract is ambiguous;
* a lawful case must be rejected to make tests green;
* an accepted result lacks independent evidence;
* live database state changes unexpectedly;
* V1 behavior moves;
* unrelated files overlap the candidate.

## Completion condition

Step 5 is complete only when:

* real text and machine-tagged Fiscal events traverse the same public V2 route;
* the real shared reader and real identity system are used;
* both evidence doors are proven;
* every submitted item and fact branch is accounted for;
* all enabled fact kinds and identity decisions are exercised;
* all five public decisions are produced truthfully;
* conversion, combination, validation, and planning occur in the approved order;
* the staged validation-door mismatch is closed without duplicate logic;
* quote occurrence is re-proven through its existing owner;
* every rename suggestion is verified, judged, planned or refused, and audited;
* every accepted fact has exact source, value, unit, period, slice, identity, and evidence;
* zero observed wrong facts are accepted;
* recall loss is measured;
* all required tests and mutations pass;
* V1 remains byte-identical;
* the live database and cursors remain unchanged;
* V2 still refuses writes;
* the exact reviewed tree is frozen and independently verified;
* no unresolved in-scope row remains.

## Commit boundary

After review, propose the smallest atomic commits supported by the actual diff:

1. Receipt/lifecycle and validation-door correction, only if code or contract changes are required.
2. Complete no-write route integration and its focused proof.
3. Status update after the exact candidate passes.

Do not create empty or artificial commit divisions. After the full step passes,
commit and normally push only the exact Codex-verified staged tree under the
standing ruling in `Steps.md`.

## What follows

After Step 5 passes, Step 6 performs the pre-authorized atomic V1-to-V2 switch
under the exact conditions in Steps.md. Database writes remain disabled.
