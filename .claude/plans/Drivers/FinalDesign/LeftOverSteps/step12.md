# Step 12 — Complete Cutover and Separately Gated Expansion

## Goal

Finish the live-system cutover without mixing three different risks:

```text
12A  move consumers and retire old Guidance safely
  ↓
12B  record no later channel in the first release; preserve the future gate
  ↓
12C  build native tagged-filing fact creation last
```

Each part has its own candidate, proof, approval, commits, and activation. A pass
in one part never authorizes another.

## Required starting state

Do not begin Step 12 until:

* Steps 0–11 are complete, committed, pushed, and independently
  verified;
* the initial approved Fiscal rollout has stable write, read, lifecycle,
  recovery, and point-in-time evidence;
* V2 is the only reachable contract and V1 is absent;
* all graph constraints, sentinels, operations, alerts, and stop controls needed
  by the live scope are green;
* the current graph, code, configuration, catalog, model pins, channel scope,
  consumer population, and test inventory are freshly frozen;
* no failed gate or owner decision affects the part being started.

Complete 12A before 12B, and 12B before 12C. The owner ruled on 2026-08-14 that
the first-release 12B set is empty. Record that decision and proceed without
inventing a channel merely to fill the step. Preserve the complete 12B
procedure below for a separately authorized future release.

Under the standing no-write ruling in `Steps.md`, agents may prepare, build,
test, simulate, review, and prove every part of this step without another owner
question. Stop before executing any live writer drain, consumer cutover,
deployment, schedule, real graph mutation, or deletion; each uses its stated
fresh approval gate.

## Authority

Apply these owners in order:

1. `FINAL_DESIGN.md` for graph meaning, evidence, identity, continuity, reads,
   facts, XBRL enrichment, and point-in-time behavior;
2. the live V2 `ChannelContract.md` and `15_CandidateFactPacket.md` for every
   enabled channel boundary and internal fact;
3. `BUILD_AND_OPERATIONS.md` §6 for old-Guidance retirement, §7 for operations,
   and §8.2 for the complete ratified native-XBRL mechanics and gates;
4. the exact signed outputs of Steps 1–11;
5. current production code, callers, tests, configuration, and fresh read-only
   graph evidence at each frozen candidate.

`STATUS_AND_HISTORY.md` reports status only. Untracked channel proposals,
diagnostic model work, archived designs, comments, old receipts, and this work
order do not create product law.

## Rules shared by all three parts

* Freeze one finite denominator before each part. No open-ended “find more”
  sweep may enter the active part.
* Reuse the live V2 reader, admission system, validators, writer, reads,
  operations ledger, recovery, and model-role owners. Add no channel-specific
  copy.
* Build no semantic regex, word list, threshold, mapping, exception, or company
  branch. Fixed behavior must come from a live rule, official standard, or an
  explicitly frozen owner decision.
* Preserve lawful history and inputs. Uncertain identity, source, period, unit,
  slice, concept, or comparison fails closed with measured recall loss.
* Target complete recall wherever deleting an unnecessary restriction, reusing
  an existing owner, or making a smaller general correction recovers it without
  reducing precision. Accept only measured residual loss; never add
  special-case logic or extra machinery merely to chase recall.
* Every behavior change is TDD-first through its real boundary, with a nearby
  lawful control and the smallest owner-level change.
* Derive complete affected populations from live code and read-only real data.
  Cover 100% of new or changed behavior branches and exception outcomes, plus
  adversarial, permutation, and required mutation behavior. Use existing proof
  owners; add no coverage framework solely to produce a percentage.
* Sonnet 5 high-effort calls bounded by this step need no separate owner or
  spending approval. Neo4j mutation, separately metered services, activation,
  and deletion retain the authority assigned to that action. Completed-step
  commits and normal pushes follow the standing ruling in `Steps.md`.
* Keep unrelated dirty-tree files, old source data, credentials, caches, and
  external systems untouched.

# Step 12A — Move Consumers and Retire Old Guidance

## Purpose

Move every current user to the proven Driver read layer, preserve a complete
restorable copy of the old Guidance system, then remove only the explicitly
approved old graph and code surfaces. Old Guidance is evidence only; it is never
converted into a Driver fact.

## Strict scope

12A includes only:

* every reachable old Guidance writer, reader, packet, prompt, worker, command,
  source link, graph object, constraint, index, and consumer;
* the prediction, learner, scanner, and any other live consumer discovered by
  the inventory;
* exact raw, current, historical, reconciled, point-in-time, and empty-history
  behavior each consumer actually needs;
* freezing and draining old writers;
* a complete hash-bound, restorable archive;
* one consumer-at-a-time cutover to the existing Driver read owner;
* exact owner-approved old graph deletion;
* removal of old seams only after zero reachability and graph deletion proof.

It excludes replay, translation, relabeling, dual writes, dual labels,
`legacy_name_map`, `regenerated_from`, a packet bridge, historical Driver
creation, a new read layer, or a convenience compatibility wrapper.

## Gate 12A.0 — Freeze the complete old-system denominator

Derive from live code, configuration, process definitions, graph metadata, and
read-only queries:

* every old writer and all routes that can invoke it;
* every old reader and consumer, including dynamic imports, shell commands,
  jobs, worker sidecars, prompts, extraction profiles, and configuration;
* every `Guidance`, `GuidanceUpdate`, and `GuidancePeriod` node;
* every property and every `UPDATES`, `FOR_COMPANY`, `FROM_SOURCE`,
  `HAS_PERIOD`, `MAPS_TO_CONCEPT`, and `MAPS_TO_MEMBER` edge;
* every old constraint and index;
* shared periods, sources, concepts, members, or helpers that must survive;
* every test, fixture, export, rollback, and empty-history branch;
* every consumer's required history horizon and point-in-time cutoff.

Record exact queries, raw results, database identity, timestamp, commit/tree,
configuration, process state, and status counts. Historical census values are
leads only.

Nothing may be classified by filename alone. Each row must be old-only,
shared-and-retained, consumer-to-move, graph target, evidence-only, or outside
scope.

## Gate 12A.1 — Freeze the cutover and history-gap decision

For every consumer, record:

* the exact old entry point and new Driver-read entry point;
* required view and fields;
* exact time semantics and strict historical cutoff;
* behavior with no Driver history;
* whether existing Driver history is sufficient at cutover;
* the test and rollback condition.

If a consumer cannot operate safely with the available Driver history, stop and
present one owner decision: accept the measured temporary gap or wait for fresh
Driver history. Never backfill the gap from old Guidance.

Freeze the exact writer-drain time, consumer order, rollback point, archive
location, deletion target, and approvals before action.

## Gate 12A.2 — Freeze and drain old writers

Follow the retirement order in `BUILD_AND_OPERATIONS.md` §6:

1. stop every old Guidance writer at the approved boundary;
2. let in-flight old writes finish or fail visibly;
3. prove all old queues and workers are drained;
4. record final cursors, counts, process state, graph identity, and cutoff time;
5. prevent any new old write without changing Driver operation;
6. prove a restart cannot silently re-enable the old writer.

Do not delete code or graph data yet.

## Gate 12A.3 — Export and verify a restorable archive

Export and hash:

* every old node, label, property, relationship, constraint, and index;
* every source and period reference needed to reconstruct the old subgraph;
* old code, prompts, extraction profiles, packets, manifests, locators,
  commands, configuration, and process definitions;
* exact counts, query text, database identity, timestamps, commit/tree, schema,
  and export tool identity.

Require source and export counts to agree for every node and relationship class.
Build the restore instructions and prove them against an isolated database with
explicit approval. The restored graph must match the archive counts, values,
relationships, constraints, and indexes exactly.

The archive is evidence and rollback material only. Production never reads it
as Driver input.

## Gate 12A.4 — Move consumers one at a time

For each consumer:

1. write a failing test through its real old call path;
2. add a lawful empty-history control and strict point-in-time cases;
3. switch only that caller to the existing Driver read owner;
4. prove raw/reconciled mode, series identity, source ordering, corrections,
   continuity, withdrawal, and effective guidance state only where that
   consumer uses them;
5. compare lawful overlapping old/new evidence as QA without making old output
   the truth;
6. prove realized returns or future facts cannot leak into historical reads;
7. run its focused and affected regression suites;
8. publish the reviewed caller change before moving to the next consumer.

Do not add a compatibility layer. If a consumer needs a genuinely missing read
behavior, return it to the one Step 8 read owner.

## Gate 12A.5 — Prove zero old reachability

After all consumers move, derive and execute a complete reachability scan for:

* old graph labels and relationship names;
* `build_guidance_history` and `guidance_history.v1`;
* old extraction profiles, packet schemas, prompts, commands, scripts, workers,
  jobs, environment flags, imports, and dynamic invocation strings;
* old readers, writers, concept resolvers, source locators, and sidecars;
* tests that still preserve a live old path rather than archive proof.

Reachable shared pure helpers may move under their surviving owner. Do not copy
them. Every old-only path must be disabled, deleted, or explicitly retained as
offline archive tooling with no production caller.

## Gate 12A.6 — Obtain exact deletion approval

Immediately before deletion, present:

* fresh graph identity and counts;
* verified archive identities and restore result;
* drained-writer proof;
* zero-consumer and zero-old-path proof;
* exact nodes, relationships, constraints, and indexes to delete;
* exact shared objects that must survive;
* rollback instructions and stop conditions.

Only the owner may approve this destructive graph action. Code, commit, switch,
or earlier rollout approval does not authorize it.

## Gate 12A.7 — Delete only the approved old graph

Within the exact approved scope:

1. delete `GuidanceUpdate` nodes;
2. delete `Guidance` nodes;
3. delete only orphan `GuidancePeriod` nodes that have no `DriverPeriod` label
   and no incoming `DriverUpdate` relationship;
4. delete only approved old Guidance constraints and indexes;
5. never relabel a `GuidancePeriod` as `DriverPeriod`;
6. never delete shared sources, companies, concepts, members, periods, or
   Driver objects;
7. stop on any target-count or relationship-count mismatch.

After commit, rerun the census and prove the expected old population is absent,
all protected populations are unchanged, Driver operation remains green, and
the archive still restores in isolation.

## Gate 12A.8 — Remove unreachable old code seams

Only after graph deletion succeeds:

* delete the old writer, command, shell wrapper, extraction profiles, worker
  sidecars, old-only concept resolver, and old-only read paths shown unreachable
  by Gate 12A.5;
* retain archive readers only when required to verify or restore the archive;
* remove tests that preserve deleted production behavior while keeping archive
  integrity and no-replay tests;
* run the reachability inventory again and require zero live old path.

Commit consumer moves, graph-retirement evidence, and old-code deletion
separately. Never sweep unrelated deletions into these commits.

## 12A completion condition

12A is complete only when:

* every consumer uses the Driver read owner and passes point-in-time and
  empty-history tests;
* the owner accepted any measured temporary history gap;
* all old writers are frozen and drained;
* the old graph and code are completely hash-bound and restorably archived;
* the owner approved the exact deletion immediately before it ran;
* only the allowed old nodes, eligible orphan periods, constraints, and indexes
  were deleted;
* every shared and Driver object is unchanged except for separately approved
  live Driver operation;
* no old reader, writer, packet, worker, profile, prompt, or production seam is
  reachable;
* no old fact was replayed, converted, relabeled, or used to mint a Driver;
* all focused, full, mutation, read, graph-integrity, archive, and recovery
  proofs pass on the exact published candidate.

# Step 12B — Certify Only Owner-Admitted Later Channels

## Purpose

Add later sources without giving any channel its own meaning, identity,
validation, or write logic. This is a repeatable gate over a finite owner-chosen
release set, not an open-ended promise to build every possible channel.

## First-release disposition

The owner-frozen first-release set is empty. For this release, Gate 12B.0
records that fact and 12B closes with no channel code, model call, source
retrieval, activation, or write. Every remaining 12B section is retained
unchanged as the authoritative work-order reference for a future owner-admitted
channel; it is not executed during the first release.

## Gate 12B.0 — Freeze the release channel set

The owner names the exact channels included in this release. Record each
channel's source types, source systems, company-binding rule, source ID
namespace, event-time owner, expected volume, required model use, budget, and
consumer need.

Every admitted model-using channel uses Sonnet 5 at high effort. Its calls need
no separate owner approval when bounded by that channel's frozen gate; an
unplanned or over-ceiling call is forbidden.

For the first release, record the already-ruled empty set and close 12B without
code. Unnamed future channels become numbered follow-up work and do not block
Step 13.

Before a channel begins, resolve only decisions it actually triggers, including:

* its Driver Genesis charter questions;
* expanded 8-K content taxonomy, if it needs more than the two closed earnings
  routes;
* non-USD support, if its population contains non-USD facts;
* the explicitly preserved future third-party company_confirmed=false class,
  if it proposes such facts; the first release keeps this class unreachable;
* any new source identity namespace with its independently proved injective
  mapping.

The smaller safe choice is to keep an unneeded class disabled.

## One channel's permitted implementation

A channel implements only:

```text
SELECT an eligible source event
→ FETCH exact source bytes and stable parts
→ SUBMIT one lawful V2 raw event
→ consume Core's final receipt
```

It may own source schedules, source retrieval, exact source-part construction,
source completeness, its cursor, and its receipt consumption. It may not own or
copy:

* Driver naming, meaning, reuse, creation, or links;
* fact types, units, scale, periods, slices, values, comparisons, or IDs;
* the shared reader, validators, fusion, writer, read layer, or recovery;
* a direct call to either internal trust door;
* a graph write or an outcome translation.

## Per-channel gate

For each admitted channel, in serial order:

1. freeze the complete eligible real-source population and exclusions;
2. freeze the exact public-time, company, source-ID, selection, completeness,
   and cursor rules from authoritative source data;
3. inventory every source boundary, parser, fetcher, cache, fallback, model
   call, event builder, caller, outcome, and failure branch;
4. write public-boundary tests before behavior changes;
5. implement only missing SELECT/FETCH/SUBMIT and receipt-consumption behavior;
6. prove exact bytes, part identities, quotes, occurrences, ordering, source
   time, company binding, late arrivals, duplicates, corrections, and incomplete
   search behavior;
7. independently certify source location and copying on frozen unseen cases;
8. enable only source groups with zero observed wrong accepts, reporting every
   miss, abstention, error, and confidence bound;
9. run real events through the shared V2 path in no-write mode;
10. run focused, full, branch, mutation, isolation, replay, and real-source
    tests on the exact candidate;
11. run shadow with exact accounting and graph unchanged;
12. obtain separate owner approval before that channel's first bounded write;
13. verify every planned and actual graph change, receipt, cursor, retry, and
    recovery result;
14. publish that channel separately before starting another.

Never use an opened development set as unseen certification. Sonnet 5 passing
another channel or task does not qualify it here without this channel's
required measured evidence.

Untracked `NewsChannel.md`, Qwen diagnostics, proposals, and old channel plans
remain leads until a live owner explicitly adopts them.

## 12B completion condition

For the first release, 12B is complete when the empty release-set record is
hash-bound and every later channel remains disabled. For any future non-empty
release, 12B is complete when every channel in its frozen release set:

* implements only SELECT, FETCH, SUBMIT, and receipt consumption;
* has a complete unseen source/evidence proof with zero observed wrong accepts;
* uses the shared V2 reader, admission system, validator, writer, reads,
  operations, and recovery with no copied rule;
* has complete late/duplicate/cursor/retry/outcome accounting;
* passed no-write, shadow, and any separately approved bounded-write gate;
* has exact reviewed local, remote, evidence, configuration, and graph
  identities;
* leaves every unapproved source group and later channel disabled.

# Step 12C — Build and Gate Native XBRL Materialization Last

## Purpose

Create exact numeric metric facts directly from machine-readable 10-K/10-Q
tags, but only for a company and Driver whose concept relationship was already
admitted and remains active.

Text remains the only route that can create Drivers, guidance, surprise,
action/event, causal, qualitative, or narrative facts. Machine tags never
decide meaning or Driver identity.

## Required starting state

In addition to 12A and 12B:

* EXP-6 passed its text-versus-XBRL convergence gate;
* the text-fact concept linker, full-universe proof, point-in-time menu,
  calculation-hierarchy veto, and monitoring are complete;
* active/revoked concept-resolution and recovery owners exist;
* the full slice table and HARD-EXCLUDE/PROVISIONAL owner review are frozen;
* the real writer, read layer, operations, alerts, rollback, and recovery have
  stable live evidence;
* every dormant P1–P17/P19 rule and ten associated amendment is inventoried
  from `BUILD_AND_OPERATIONS.md` §8.2;
* the native-XBRL feature and all dormant storage/read behavior remain off.

## Strict scope

The materializer may process only:

* `10-K`, `10-Q`, `10-K/A`, and `10-Q/A` reports with completed parsed XBRL;
* an in-filing fact belonging to the report's registrant;
* numeric, non-nil facts for an already-admitted active
  `(company, Driver) → concept` resolution;
* USD, shares, and USD-per-share units under the exact ratified mapping;
* representable complete dimensions and exact periods;
* source-stated signed values at canonical scale.

It must skip and count all unlinked, non-GAAP, unsupported-unit,
wrong-registrant, contextless, nil, qualitative, causal, guidance, surprise,
action, narrative, TextBlock-only, or unrepresentable-slice material.

No Q4 derivation, percent rewrite, inferred value, auto-surprise, name creation,
Driver creation, fuzzy concept mapping, source-text replacement, or catalog
bulk-sync is permitted.

## Required P1–P17/P19 pin checklist

Do not reinterpret these pins. Derive their exact tests and implementation from
`BUILD_AND_OPERATIONS.md` §8.2 and close each row visibly:

* **P1:** activate the native origin, exact machine-tag quote, `reported` state,
  exact window, member/slice, and full-validator behavior together. In normal
  order a matching text twin is skipped whole; the native fact never gains
  prose, and an ordinary text fact never gains native-origin fields. The
  existing text-fact concept enrichment remains separate and unchanged.
* **P2:** store no rank field; only the exact same-event/same-series read tie
  prefers native XBRL.
* **P3:** native `measurement` is empty. Apply the native-only declared family
  fold `{empty, gaap, reported, as_reported}` plus only the linked concept's
  own Basic or Diluted token in both the write-side twin test and read bucket.
  Basic and Diluted never fold together; stored identities never change.
* **P4:** implement the exact report/fact/unit/dimension/period/value/collision
  recipe in Gate 12C.1, including no Q4 derivation or auto-surprise.
* **P5:** materialize before text; suppress only a true compatible twin under
  the text fact's own stated precision; otherwise preserve text or use the
  exact state-based conflict path and writer backstop.
* **P6:** native facts and resolutions never supply evidence for ESTABLISHED
  eligibility; the retired `BROAD` shorthand creates no replacement state.
* **P7:** store the exact native attach mode, resolution identity, and source
  fact identity as provenance.
* **P8:** use one reified active/revoked concept-resolution lifecycle. Revocation
  and restoration each require the ratified two blind Sonnet 5 high-effort
  reviews and a
  RecoveryEvent; reads exclude revoked cohorts, and revocation or a recorded-edge
  quarantine re-enqueues the bounded parks and source events it affected. A
  newly XBRL-backed continuation endpoint must reuse Step 4's existing
  false-continuity tripwire; do not add another rename or recovery rule.
* **P9:** require Sonnet 5 high-effort final concept verification, the
  qualifier veto, XC-16,
  and the full-universe proof before materialization.
* **P10:** allow native concept fields and `reported` state only for the native
  origin through the one lane validator.
* **P11:** make every text-to-native upgrade reversible through one immutable
  UpgradeEvent and the existing repair/recovery lane.
* **P12:** a newly active resolution enqueues all eligible filings, including
  the current one; text never waits for that work.
* **P13:** at text-write time, log the same-event, same-head, value-compatible
  pair when exactly one of period or slice differs. A measurement difference is
  excluded. Never snap, park, or re-key either fact from the tripwire alone.
* **P14:** use the shared exact-date period-scope classifier, actual company
  calendar ends, null fiscal fields when unknown, and no sentinels.
* **P15:** derive effective state for native `reported` facts at read time from
  the governed date arithmetic; never write it back.
* **P16:** source evidence may create a fact; menus may only narrow. No hint may
  supply a value or scale.
* **P17:** prompt narrowing is a cost experiment only. Code-side eligibility
  and suppression remain the guarantee.
* **P19:** every hard pre-gate, fresh census, X-XL0–X-XL4 result, and
  industry-by-industry rollout rule remains binding.

The ten dormant contract, validator, storage, read, provenance, conflict,
recovery, and period amendments identified by §8.2 must activate in the same
reviewed feature batch. There is no P18.

## Gate 12C.0 — Freeze the complete rule and population denominator

Mechanically map every recipe branch, P1–P17/P19 pin, dormant contract/storage
amendment, report/fact/source category, unit, dimension state, period state,
dedupe state, conflict state, concept-resolution state, text-twin state,
recovery state, read behavior, operation, failure, and test to one owner.

Run a fresh read-only graph census covering:

* reports by exact form, registrant, parsing state, and `periodOfReport` state;
* numeric/nil facts, contexts, entity links, concepts, units, decimals, scales,
  dimensions, members, typed dimensions, and duplicate/conflict cohorts;
* active/revoked concept resolutions and eligible admitted Drivers;
* source and graph shapes used by the real writer;
* text/XBRL twin, non-twin, no-context, multi-registrant, amended-filing,
  52/53-week, null-period, precision-duplicate, and unsupported-unit cohorts.

Record query text, parameters, raw output, database identity, timestamp, code
candidate, population counts, and every exclusion. Historical EXP-1 data is
evidence, not a current census.

## Gate 12C.1 — Write tests for the ratified recipe before code

Tests must cover every branch of the following exact pipeline:

1. load active full-record concept resolutions; exclude latent bases;
2. select facts through the report registrant's context and require numeric
   non-nil state; process a multi-registrant filing as separate registrant runs;
3. apply the exact three-unit mapping—USD to money on the Driver's canonical
   scale, shares to count, and USD-per-share to per-share level—and count every
   unsupported unit;
4. remove identical raw duplicates;
5. within one scope, keep the highest precision only when values agree within
   declared decimals; otherwise park the whole scope as
   `xbrl_internal_conflict` until that report's parsed facts change;
6. preserve every axis; map governed slice axes, use the existing unknown-axis
   sentinel, and skip the whole fact on a non-slice axis or hard-excluded
   member;
7. resolve the period from its own context through the shared period owner;
8. build the normal DriverUpdate identity from source, Driver, and fact scope;
9. classify a fact as primary exactly when its period end equals
   `periodOfReport`; otherwise write only a new scope or changed value, skip an
   identical retag, and when `periodOfReport` is null use the report's maximum
   duration-period end or skip the report if none exists;
10. write only a metric point level through the existing writer: point shape,
    exact signed canonical value, `reported` state, native origin, exact
    machine-tag quote, public filing time, form-derived source type, concept,
    member, period, and provenance; forbid change, comparison, free-value text,
    conditions, and company confirmation;
11. materialize before text. Suppress only a same-event, same-head, same-period,
    same-slice, family-fold-compatible twin whose value agrees within the text
    fact's own stated precision; log the deferred fact and any crossed
    same-meaning links. Preserve text otherwise, and use the exact state-based
    conflict and writer-backstop paths;
12. preserve text extraction when a filing has no eligible XBRL fact;
13. emit the one-component period-or-slice twin-suspect tripwire without
    changing either fact;
14. keep active/revoked concept resolution, re-verification, cohort exclusion,
    re-extraction, upgrade, reversal, and RecoveryEvent behavior reversible and
    auditable;
15. apply native-XBRL read preference only within the exact same event and
    series after enablement.

Use the live owners for IDs, periods, units, slices, concept resolutions,
collision, validation, writer, recovery, and reads. The materializer only
selects eligible structured facts and submits the governed plans.

## Gate 12C.2 — Implement the smallest dormant path

Add one production materializer entry point behind one default-off feature
gate. It must call existing owners and expose complete per-report accounting:

```text
eligible reports
= processed + skipped-report + failed-report

eligible source facts
= written + merged + skipped + parked + rejected + explicit error
```

Every exclusion and conflict carries its existing machine-readable reason.
Free text is never parsed to determine an outcome. A report failure cannot
partially write its eligible facts.

Activate the dormant field, validator, read, conflict, provenance, and recovery
amendments only in the same reviewed feature batch. No native-XBRL object may
reach ordinary behavior while one required amendment remains inactive.

## Gate 12C.3 — Pass every hard pre-gate

Before any live enablement, require:

* XC-16 calculation-hierarchy veto;
* full-universe concept-link proof;
* strict point-in-time company-menu proof;
* the required falsifier dry-run over a materialized sample, scoped to
  non-native facts exactly as the ratified P4 rule requires;
* fresh graph census and source-shape proof;
* complete slice-table materialization and HARD-EXCLUDE/PROVISIONAL owner vet;
* every validator mutation caught;
* every detector catching its seeded corruption class;
* isolated write, rollback, recovery, revocation, reversal, and re-extraction
  tests;
* no change to text-only coverage when the native path is off.

## Gate 12C.4 — Run the P19 proof plan

Pre-register all samples, truth, metrics, bars, identities, and stop rules, then
run:

### X-XL0 — Determinism

Compare every produced fact with its surviving source fact for value, scale,
unit, period, member-to-slice mapping, concept, and entity. Require 100%.

Include a multi-registrant filing, null-`periodOfReport` report, precision
duplicate, amended filing, and 52/53-week filer.

### X-XL1 — True-twin identity

For frozen text/XBRL true twins, classify every divergence and require at least
99% DriverUpdate ID equality. Include 52/53-week filers. Do not count non-twins
as misses.

### X-XL2 — Suppression and tripwire

Compare suppression on versus off over the pre-registered filing sample.
Require zero suppressed non-twins, account for every duplicate and conflict,
measure the twin-suspect rate, and pre-register its rollout bar from this run.

### X-XL3 — Recall

Against an independent hash-locked key, require native-XBRL plus unsuppressed
text coverage to meet or exceed text-only coverage and lose zero market-moving
facts.

### X-XL4 — Cost

Report tokens, model calls, processing cost, and backfill cost for hybrid versus
text-only operation. This is informational and cannot override a safety bar.
Every required review call uses Sonnet 5 at high effort under the master
pre-authorization.

Any confirmed wrong fact, wrong suppression, unresolved true-twin divergence,
coverage loss, or incomplete denominator blocks rollout.

## Gate 12C.5 — Roll out one industry, then expand separately

After all hard pre-gates and X-XL0–3 pass:

1. obtain explicit owner approval for one named industry and exact candidate;
2. recheck graph, code, resolution, source, and feature identities;
3. enable the native path for only that industry;
4. reconcile every report, source fact, plan, write, skip, park, conflict,
   suppression, tripwire, read result, alert, and recovery action;
5. prove every X-XL0–3 bar still holds on live output;
6. stop and disable on the first confirmed wrong fact or suppression;
7. expand industry by industry only after separate evidence and approval.

The feature remains dormant for every unapproved industry.

## 12C completion condition

12C is complete only when:

* every P1–P17/P19 rule and dormant amendment is implemented once at its live
  owner or explicitly proved already satisfied;
* the materializer creates only exact numeric metric facts for active admitted
  company/Driver concept resolutions;
* text remains the sole creator of Drivers and non-metric/narrative facts;
* every report and source fact has one accounted outcome;
* all unsupported, ambiguous, conflicting, contextless, or unrepresentable
  cases fail closed with measured recall;
* every hard pre-gate passes;
* X-XL0 is 100%, X-XL1 is at least 99% on true twins, X-XL2 suppresses zero
  non-twins, and X-XL3 loses zero market-moving facts or coverage;
* rollback, revocation, reversal, re-extraction, and recovery are proven;
* each enabled industry has separate approval and continuing gate evidence;
* no unapproved industry, source class, unit, fact type, or dormant feature is
  active;
* focused, full, isolated, branch, mutation, real-data, graph-integrity, and
  exact-identity proofs pass.

## Step 12 publication and completion

Keep 12A consumer moves, writer drain/archive, graph deletion, and code removal
separate. Keep every 12B channel separate. Keep 12C implementation, proof, and
each rollout promotion separate. Test and review the exact staged tree before
each approved commit and verify local, origin, remote, configuration, and graph
identities afterward.

Step 12 is complete only when 12A and 12C are complete and every channel in the
owner-frozen 12B release set is complete. Unnamed future channels remain outside
the release and do not make this step unbounded.

The next step is Step 13: one final whole-system reconciliation. Step 13 may
record and close evidence; it must not hide a new behavior fix inside the final
gate.
