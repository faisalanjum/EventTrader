# Step 13 — Reconcile and Close the Driver Program

## Goal

Prove one exact final system, with no hidden path, missing item, unresolved
in-scope decision, unexplained graph change, or stale authority claim.

Step 13 adds no product behavior. A real defect returns to its owning earlier
step, is fixed there by TDD, and then the complete final gate restarts on a new
candidate.

Step 13 closes the system on its qualified Sonnet 5 high-effort configuration. Optional
Step 14 is not a prerequisite and cannot delay or weaken this closure.

## Required starting state

Do not begin final closure until:

* Steps 0–12 are complete, committed, pushed, and independently verified;
* 12A old-Guidance retirement and 12C native-XBRL work are complete;
* the owner-frozen first-release 12B set is recorded as empty and every later
  channel remains disabled;
* every enabled channel, consumer, reader, identity path, writer, read view,
  operation, recovery path, and rollout has stable live evidence;
* every model call used Sonnet 5 at high effort within its frozen ceiling;
  graph mutations, deletions, and activations used their required approvals;
  commits and normal pushes satisfied the standing completed-step ruling;
* the exact release scope and explicitly excluded later work are frozen;
* no unresolved owner decision changes an enabled behavior.

## Authority

Apply these owners in order:

1. `FINAL_DESIGN.md` for product meaning and safety law;
2. the live `ChannelContract.md` and `15_CandidateFactPacket.md` for public and
   internal runtime contracts;
3. `BUILD_AND_OPERATIONS.md` for construction, operation, activation,
   retirement, and proof requirements;
4. `FableExperimentPlan.md`, `FableExperimentWorkOrder.md`, and their signed
   artifacts for the completed experiment program until it is archived;
5. `STATUS_AND_HISTORY.md` for status after every claim is independently
   verified;
6. live code, configuration, tests, manifests, receipts, and fresh read-only
   database output for the exact candidate.

This file, `Steps.md`, handovers, comments, commits, old receipts, archived
designs, and scratch files are leads only.

## Strict scope

Step 13 includes only:

* freezing the exact release candidate and finite closure denominator;
* reconciling all enabled production paths and all explicitly deferred paths;
* full code, contract, configuration, artifact, test, data, graph, operation,
  and side-effect proof;
* honest measured quality and residual-risk reporting;
* updating the one status owner and archiving the completed experiment plan
  only after its live responsibilities have migrated;
* exact reviewed publication and final owner acceptance.

It excludes:

* a new feature, channel, model role, rule, threshold, exception, refactor,
  framework, dependency upgrade, test move, cleanup sweep, or optimization;
* fixing a defect inside the closure packet;
* reopening signed work without current evidence of an enabled-path effect;
* treating an optional or future proposal as a release blocker;
* hiding an in-scope defect as follow-up work merely to finish;
* a graph mutation, deletion, activation, commit, or push without exact
  approval;
* unrelated credential or Git-history work.

## Non-negotiable rules

* The denominator comes from live code, configuration, data, and authorities,
  never memory or a hand-written sample list.
* Every row has exactly one status: proved complete, explicitly excluded from
  this release, or blocked on a named owner decision. Closure requires zero
  blocked in-scope row.
* Every behavior has one production owner. No proof-only copy may remain
  reachable.
* Every enabled fixed value, vocabulary, pattern, model, threshold, or
  exception must trace to an official standard, live owner contract, or frozen
  measured owner decision.
* Zero observed wrong accepted facts and identities is mandatory. Recall,
  parks, skips, refusals, invalid responses, and confidence bounds remain
  visible.
* A recall bar is a minimum gate, never the target. Closure requires proof that
  no deletion, existing-owner reuse, or smaller general correction can recover
  each residual miss without reducing precision. Never add special-case logic
  or extra machinery merely to chase recall.
* A green count is not proof by itself. Read the exact path and run its real
  scenario with lawful controls.
* Any candidate change invalidates affected hashes and proof. Rebuild only the
  affected evidence, then rerun the whole final gate.

## Gate 13.0 — Freeze the exact release candidate

Record and verify:

* branch, commit, tree, index tree, staged paths, worktree status, and remote
  identity;
* dependency and runtime versions;
* active contracts and their hashes;
* model IDs, effort/settings, prompts, budgets, and feature flags;
* catalog, answer keys, experiment outputs, channel certificates, operations
  runbook, and proof manifests;
* enabled channels, source groups, industries, consumers, read modes, write
  scopes, schedules, and native-XBRL cohorts;
* database identity, schema, sentinels, graph counts, and current operational
  state;
* the finite excluded-later-work list.

Use an isolated clean worktree for code proof. Preserve unrelated local changes.
No release artifact may move after this freeze.

## Gate 13.1 — Build the complete closure denominator

Derive and account for every:

* public channel entry point and enabled source selector;
* fetch, source-part, source-time, company-binding, completeness, cursor, and
  late-arrival branch;
* reader request, response, abstention, parse, and evidence branch;
* text/model and verified-XBRL trust-door branch;
* admission, reuse, creation, skip, park, link, continuation, detector,
  quarantine, and recovery branch;
* period, unit, value, slice, concept, identity, fusion, collision, validation,
  planning, transaction, and audit branch;
* public item outcome and channel acknowledgement;
* raw, current, historical, reconciled, point-in-time, guidance-movement,
  withdrawal, verdict, and consumer-read branch;
* schedule, selection, attempt, retry, reopening, drain, budget, canary, alert,
  crash, rollback, cursor, and catalog-refresh branch;
* enabled native-XBRL report, fact, conflict, suppression, recovery, and rollout
  branch;
* graph label, relationship, property, constraint, index, sentinel, write, and
  delete category;
* model call, external fetch, cache, durable artifact, configuration, secret,
  and side effect;
* test identity, mutation, real-data query, receipt, manifest, and owner
  decision;
* dormant, conditional, rejected, retired, and owner-excluded feature.

The inventory must reconcile programmatically to live entry points, changed
files, contract surfaces, configuration flags, and graph categories. Nothing
may disappear because it is parked, invalid, dead, deferred, or inconvenient.

## Gate 13.2 — Prove ownership, minimality, and reachability

For every enabled behavior row:

1. cite its live authority and one production owner;
2. state the real failure it prevents;
3. prove every real caller reaches that owner;
4. prove no second implementation, wrapper, prompt, schema, registry, reason
   vocabulary, validator, writer, read rule, or source matcher is reachable;
5. prove every behavior-changing constant or pattern is authorized or
   mechanically derived;
6. prove uncertainty fails closed without deleting lawful cases;
7. delete dead duplicate code only through its owning earlier step if closure
   discovers it.

Specifically require:

* V2 is the only public/internal route and no V1 code or pin is reachable;
* production imports no experiment harness or archived rule source;
* every channel owns only source transport and receipt consumption;
* the one shared reader and one admission system serve every enabled channel;
* the two trust doors remain distinct and share one deterministic tail;
* only Core writes Driver graph data;
* the offline catalog is not bulk-materialized into empty graph nodes;
* old Guidance has no live reader, writer, packet, worker, graph object, or
  production seam;
* optional and dormant features remain unreachable unless their exact gate and
  approval are recorded.

## Gate 13.3 — Reconcile contracts, code, and artifacts

Mechanically compare all enumerable contract surfaces with their live code
owners. Verify:

* public event, source-part, item, fact, outcome, reason, and lifecycle shapes;
* internal fact fields and every per-lane requirement/forbidden field;
* reader and identity envelopes, including continuity suggestions and accepted
  continuation-link or claim shapes;
* model roles and exact settings;
* catalog and family schemas;
* IDs, periods, units, slices, concept resolutions, and graph write shapes;
* read modes and series keys;
* operations ledger states and transitions;
* all manifest, prompt, key, result, catalog, source, and receipt hashes;
* every active document statement about live versus dormant behavior.

Require zero stale V1 field, retired hint, old Guidance instruction, dead path,
missing pin, duplicate authority, or unaccounted artifact.

## Gate 13.4 — Run the complete exact-candidate proof

Run, in the frozen order:

1. static contract, import, reachability, secret, and prohibited-pattern checks;
2. focused tests for every enabled component;
3. all affected regressions;
4. the full test suite with every expected identity accounted;
5. isolated no-credential and clean-environment gates;
6. 100% coverage of all new or changed behavior branches and exception outcomes;
7. every required mutation and deliberate-fault check;
8. deterministic replay and permutation tests;
9. crash, restart, lock, idempotency, rollback, recovery, and alert tests;
10. channel unseen-source and exact-copy proofs;
11. experiment, catalog, identity, concept, read, consumer, and native-XBRL
    release gates;
12. real read-only source and graph-population checks;
13. one fully accounted end-to-end live canary within the already approved
    release scope;
14. post-canary graph, receipt, cursor, read, alert, and recovery checks.

No test may be silently deselected, renamed away, skipped, or re-pinned. Explain
every lawful skip and prove it is not part of the enabled release.

## Gate 13.5 — Prove graph and history integrity

Take fresh read-only before/after evidence for:

* constraints, indexes, and four period sentinels;
* Driver, DriverUpdate, DriverPeriod, concept-resolution, continuation,
  recovery, verdict, source, company, concept, member, and relationship counts;
* identity uniqueness, period write-once behavior, exact relationship
  cardinality, and orphan populations;
* old Guidance absence and protected shared-object survival;
* native-XBRL versus text origin, suppression, conflict, tripwire, revocation,
  and recovery cohorts;
* point-in-time reads around source times, amendments, renames, and strict
  cutoffs;
* no unexplained node, edge, property, constraint, index, or deletion.

Compare the live graph with the exact approved plans and operations receipts.
Any unexplained difference is a failed release gate.

## Gate 13.6 — Prove operational recovery

Using the live-approved scope and safe fault controls, demonstrate:

* source outage and recovery;
* model outage, invalid reply, budget stop, and canary stop;
* whole-event retry only for authorized reasons;
* skip reopening only on its contract-owned triggers;
* park draining through the full owning path;
* process crash at each durability boundary;
* stale `prepared` audit reconciliation;
* catalog-refresh failure retaining the last valid catalog;
* writer lock and duplicate delivery convergence;
* graph transaction rollback and recovery events;
* alert delivery and operator-visible stop state;
* safe restart without event loss, duplicate fact, cursor leap, or hidden
  failure.

Do not introduce a failure framework solely for this gate. Use existing fault
injection, test doubles, and bounded operational controls unless they cannot
prove a named branch.

## Gate 13.7 — Report quality honestly

For each enabled channel, source group, fact lane, identity arm, concept-link
group, industry, and native-XBRL cohort, report:

* total eligible population and sampled population;
* accepted, written, merged, parked, skipped, rejected, invalid, failed, and
  excluded counts;
* confirmed wrong accepts and wrong identities;
* recall, precision, abstention, false-refusal, duplicate, and recovery rates;
* confidence bounds and sampling limits;
* model calls, invalid responses, retries, tokens, and cost;
* every residual semantic-only risk.

The release requires zero observed confirmed-wrong accepted fact or identity.
It does not claim mathematical perfection over all unseen language. Any recall
loss remains measured and explained only after the simple general recovery
options above are exhausted.

## Gate 13.8 — Resolve the final scope ledger

Every closure row must end as:

* `CLOSED` — exact proof on the frozen candidate; or
* `EXCLUDED-LATER` — outside the owner-frozen release, unreachable, and assigned
  a separate follow-up identity.

No `OPEN`, `UNKNOWN`, `PARTIAL`, `BLOCKED`, or unratified in-scope behavior may
remain.

Conditional items that never triggered stay absent. Unnamed future channels,
the optional OD-5 scanner, untriggered model/cache optimizations, and other
owner-excluded features do not become closure work.

## Gate 13.9 — Update and archive documents

After the code, graph, and proof candidate is final:

1. update `STATUS_AND_HISTORY.md` with exact commits, trees, contracts, model
   pins, test results, graph identities, enabled scope, quality measures, and
   honest residual risk;
2. remove stale “staged,” “pending,” “not live,” and old count claims only where
   current evidence proves the new state;
3. preserve design history without turning status prose into new law;
4. archive the experiment Plan/WorkOrder only after every live key, model pin,
   prompt owner, gate, and status duty has migrated to its permanent owner;
5. verify every active link and file reference;
6. run the mandatory blank-context document review: a new agent must recover
   the active system, enabled scope, safety gates, and next operational action
   without an archived or scratch file.

Documentation changes are separately reviewed and committed. They cannot hide
a code, contract, configuration, or graph change.

## Gate 13.10 — Publish and obtain final acceptance

For every final commit:

* stage only closed rows;
* record exact path and blob lists plus staged tree;
* inspect and test the staged tree;
* exclude secrets, local configuration, generated credentials, unrelated
  files, and unreviewed artifacts;
* obtain Codex `VERIFIED` on the exact staged identity;
* push normally without rewriting history;
* verify local HEAD/tree, origin, remote commit/tree, deployed configuration,
  and live graph identities.

Present one final closure packet with the complete denominator, proof results,
quality measures, graph state, enabled scope, excluded later work, recovery
status, and exact identities. The owner gives the final closure decision.

## Stop conditions

Stop and return the defect to its owner if:

* the release candidate or any authority/artifact identity moves;
* a live entry point, branch, side effect, graph category, test, or decision is
  absent from the denominator;
* a rule has no authority or more than one production owner;
* a V1, old Guidance, harness, bypass, direct channel write, or dormant path is
  reachable;
* a fixed semantic value or pattern lacks authority;
* an enabled behavior lacks a real-path test, lawful control, required mutation,
  or real-data proof;
* a test identity disappears, a relevant skip is unexplained, or a mutation
  survives;
* a wrong accepted fact, wrong identity, future leak, missing outcome,
  unbounded retry, silent failure, or unexplained graph change appears;
* a rollback, recovery, alert, cursor, archive, or restore path fails;
* an in-scope owner decision remains unresolved;
* documentation overstates precision, recall, completion, or live state;
* a destructive action or activation lacks exact approval, or a commit/push
  violates the completed-step ruling;
* unrelated files or external state move.

## Completion condition

The Driver program is complete only when:

* every enabled source uses the one V2 event path, shared reader, shared
  admission system, deterministic owners, writer, reads, operations, and
  recovery;
* every enabled consumer uses Driver reads;
* old Guidance is drained, restorable, retired, and unreachable;
* every owner-admitted later channel and every enabled native-XBRL cohort passed
  its own proof and activation gate;
* every input, item, decision, fact, graph change, receipt, cursor, retry,
  recovery, and exclusion is accounted;
* every in-scope closure row is `CLOSED` and all later work is explicitly
  unreachable and separately identified;
* zero observed confirmed-wrong accepted fact or identity remains, with recall
  and uncertainty reported honestly;
* focused, full, isolated, branch, mutation, real-data, graph-integrity,
  operations, recovery, and staged-tree gates all pass on one exact candidate;
* local, remote, deployed, configuration, contract, artifact, and graph
  identities agree;
* the live documents accurately describe the final system;
* the owner explicitly accepts final closure.

After closure, the owner may stop with the Sonnet 5 high-effort system permanently or
start Step 14. A failed or skipped Step 14 candidate does not reopen Step 13;
the Sonnet 5 high-effort configuration remains the accepted system.

The temporary #827 stop hook and any credential rotation or Git-history work
remain separate non-Driver housekeeping. They must not be smuggled into this
release or allowed to invalidate its proof-bound history.
