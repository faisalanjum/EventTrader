# Step 10 — Freeze and Build the Minimal Running Layer

## Goal

Build the smallest reliable way to run the finished Driver pipeline repeatedly
without losing, duplicating, hiding, or silently retrying source events.

```text
approved external schedule
→ certified channel selects one source event
→ exact event bytes become durable
→ the existing V2 Core route runs once
→ the existing Core audit records the exact input, plan, and outcomes
→ the channel consumes the receipt
→ the lifecycle record and cursor advance safely
```

This step builds and proves operation with graph writes off. It does not turn on
a production schedule, make an unplanned or over-ceiling model call, create graph data,
move consumers, retire old Guidance, or activate any later feature.

## Required starting state

Do not implement Step 10 until:

* Steps 0–8 are complete, committed, pushed, and independently verified;
* Step 9A is complete for every Fiscal source group that this runner will use;
* Step 9B remains visible if it still waits for the first approved real Driver
  records; Step 9B is not a prerequisite for this no-write build;
* V2 is the sole live public and internal contract;
* the real shared reader, admission system, validator, fusion owner, writer
  planner, read layer, and Fiscal V2 command exist;
* the catalog has a validated frozen artifact and a proved incremental-refresh
  entry point;
* every production model role needed by the enabled scope has a signed exact
  model-and-setting choice;
* Core still refuses graph writes on the V2 route;
* the exact starting commit, tree, environment, dependencies, and active
  configuration are frozen in a clean isolated worktree;
* no earlier failed gate or required owner decision remains open.

The design-only inventory and decision packet may begin after Step 6. Code must
wait for the interfaces above to be final. Return a missing prerequisite to its
owning step; do not rebuild it here.

## Authority

Read and apply authority in this order:

1. `FINAL_DESIGN.md` for source time, safety, identity, admission, recovery,
   lazy Driver creation, reads, and feature-off rules;
2. the live V2 `ChannelContract.md` for channel selection, submission,
   completeness, cursor, receipt, reopening, and retry behavior;
3. the live V2 `15_CandidateFactPacket.md` for internal handoffs;
4. `BUILD_AND_OPERATIONS.md` §§3, 7, 8.1, 10, and 11 for the two earnings-8-K
   routes, running-layer requirements, approved kernel operations, hazards, and
   writer transaction/audit contract;
5. the exact signed model, catalog, Fiscal-certification, and read-layer
   contracts produced by Steps 1–9;
6. current production code and tests at the frozen Step 10 candidate.

`STATUS_AND_HISTORY.md` reports state; it does not define behavior.
`.claude/plans/Drivers/WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md` is a continuity checklist only.
`Steps.md`, this file, old Guidance operations, experiments, receipts, commits,
comments, scratch files, and archived plans are leads until reconciled to the
live authorities and exact candidate.

Step 10 closes the design gap in `BUILD_AND_OPERATIONS.md` §7. Approved Step 10
rules must be folded into that section or another explicitly designated live
owner. This work order must not become a second production authority.

## Scope

Step 10 includes only:

* the exact enabled source schedules and source selectors;
* one durable event, attempt, receipt, and cursor lifecycle;
* live and historical selection through the same channel and Core path;
* exact retry, reopening, park-drain, and stop rules derived from their owners;
* exact production model references, budget checks, billing guards, and
  canary behavior;
* minimal health output, alert delivery, and stop conditions;
* crash detection, restart, idempotent resubmission, reconciliation, and
  operational rollback with writes off;
* invocation of the existing incremental-catalog owner under its frozen rules;
* lazy born-complete Driver planning through the existing admission and writer
  path, still without execution;
* the operational handoff needed for the later consumer cutover and lawful
  empty-history behavior;
* focused, regression, branch, mutation, real-read-only-data, crash, identity,
  and no-write proof on one exact candidate.

Step 10 excludes:

* a second reader, admission system, validator, fusion engine, writer, source
  locator, catalog finalizer, read layer, or retry reason owner;
* a new Driver meaning rule, source matcher, semantic regular expression,
  vocabulary, threshold, exception, or company-specific branch;
* a service bus, distributed queue, task framework, workflow engine, cache,
  dashboard, object mapper, migration framework, or multi-host writer;
* a resident daemon when a bounded command invoked by an approved existing
  scheduler is sufficient;
* News or another channel that has not completed its own contract and
  certification;
* the optional OD-5 change scanner unless a real named consumer first proves it
  needs that output;
* catalog bulk-sync, factless Driver nodes, graph constraints, period sentinels,
  graph writes, shadow activation, or a write pilot;
* enabling CLAIM, native-XBRL materialization, or any deferred kernel feature;
* moving consumers, retiring or deleting old Guidance, running Track C, or
  executing the later production cutover;
* an unplanned or over-ceiling model call; source retrieval outside the master
  public-source ruling; deployment or activation without the approval required
  for that action; or a commit/push that violates the completed-step ruling;
* unrelated cleanup, dependency upgrades, test relocation, or file moves.

## Non-negotiable rules

* Start with deletion and reuse. Add code only for a reproduced running-layer
  failure that no current owner can prevent.
* Use one bounded single-host runner. Keep the existing single-writer lock and
  multi-host prohibition.
* One rule has one owner. The runner schedules and records; it never interprets
  facts, chooses Driver identity, resolves units or periods, validates facts,
  fuses facts, or plans writes.
* Use one physical Driver operations ledger. Channel-owned source discovery,
  pre-submission outcomes, completeness, cursor, and delivery records may
  occupy owned sections of that ledger; they must not become parallel files
  with competing truth.
* Keep the existing Core write-ahead audit as the sole exact Core input, plan,
  and item-outcome record. The operations ledger stores its identity and full
  fingerprint, not a copied rule engine or rewritten result.
* Keep kernel parks, deferred pairs, and recovery records in their existing
  semantic owners. The runner consumes their typed triggers; it never parses
  prose or reclassifies them.
* Keep catalog source and decision history in the catalog owner. The runner may
  invoke and record a refresh; it may not reimplement a fold or finalizer.
* Add no behavior-changing fixed string, list, number, range, threshold,
  pattern, regular expression, exception, status, or vocabulary unless an
  official standard or frozen owner contract supplies it, or code mechanically
  derives it from one.
* Meaning remains model-owned. Code may order, fingerprint, persist, compare
  exact values, enforce transitions, count, and stop; it may not infer meaning
  from labels, words, names, magnitudes, or patterns.
* Preserve every lawful event, late arrival, duplicate arrival, amended source,
  split fact, fused fact, skip reopening, and state-clearing retry.
* Uncertain source completeness, ownership, transition, retry eligibility,
  model identity, configuration, or audit state fails closed and stays visible.
* A cursor is an optimization, never proof that all sources were seen. A
  durable source-ID inventory or an authoritative monotonic source feed must
  catch late and backdated arrivals without an arbitrary look-back window.
* Whole-event retry means the complete event crosses the public path again.
  Never replay only a parked fact or surprise without its siblings.
* A later source is always a new event and may create its own fact. It may
  trigger reconsideration of an older whole event only through an exact
  owner-proved relationship or state change; the older event still uses only
  its own source evidence.
* Never retry inside the Core transaction or hide a second attempt inside one
  run. An authorized retry is a new durable whole-event attempt after the prior
  attempt is fully accounted or reconciled.
* Only an owner-registered structural reason may trigger automatic work. Never
  parse error text.
* The same event and exact payload must converge. A changed payload for the
  same source is a visible revision, not a silent overwrite or duplicate.
* Use full standard fingerprints for persisted identity checks. Never use a
  truncated digest as the sole durable key.
* Graph writes remain impossible. The runner exposes no write option in this
  step, and an environment variable cannot bypass that boundary.
* Runtime must not depend on a human. Owner approvals freeze configuration and
  activation; ordinary event handling must then be deterministic and bounded.
* TDD is required for every behavior change: reproduce through the real outer
  command, preserve a nearby lawful control, make the smallest owner-level fix,
  then run focused and affected regressions.
* Require 100% branch coverage for new running-layer code and every changed
  connection branch. If a defensive branch is genuinely unreachable, explain
  it and prove its guard by mutation or an equivalent test. A green line count
  cannot replace public-path, crash, real-population, and reconciliation proof.
* Accepted operational facts require exact accounting. Every selected event,
  attempt, item outcome, retry, reopening, delivery, cursor move, and exclusion
  must be counted; no category may disappear into logs.
* Step 10 may not change a fact, identity, or acceptance verdict. Frozen replay
  must preserve the earlier zero-observed-wrong-accept result and measured
  recall exactly; any movement returns to the owning step.

## Responsibility boundary

| Responsibility | Single owner |
|---|---|
| Choose eligible source events and prove source completeness | Certified channel selector |
| Apply the two earnings-8-K routes | Existing PER-21 owners only |
| Package one exact V2 source event | Channel V2 builder |
| Define cursor value, source completeness, and channel-only no-submission transition | Certified channel |
| Interpret source meaning | Shared reader |
| Reuse, create, park, and recover Driver identity | Admission kernel |
| Validate, combine, identify, plan, and audit facts | Existing Core owners and `run_event` |
| Plan or execute graph mutation | Existing writer; execution remains off here |
| Persist event/attempt/cursor/delivery lifecycle | One Driver operations ledger |
| Apply final Core-result cursor rules and invoke whole-event retry | One Core Driver runner |
| Fold and publish an incremental catalog | Existing catalog workflow/finalizer |
| Return historical/current views | Existing Step 8 read layer |
| Invoke the bounded command on a schedule | Approved existing host scheduler |
| Freeze operational choices and authorize separately metered spend and activation | Owner |
| Verify and publish a fully completed step | Codex review plus the standing owner ruling in `Steps.md` |

The physical operations ledger may hold records written on behalf of both the
runner and a channel, but ownership remains explicit per record type. Sharing a
store is not permission for the runner to decide channel completeness or Core
outcomes. The channel supplies the cursor value, completeness result, and any
channel-only outcome. For submitted events, the Core runner applies the frozen
cursor/retry rule from Core's structural receipt. The ledger makes either
owner's authorized transition durable; it decides neither.

## Verified starting leads — recheck at Gate 10.0

At the authoring snapshot:

* `driver/core/driver_write_cli.py` owns one never-overwritten write-ahead
  audit per Core run and the one local writer lock;
* a leftover Core audit in `prepared` state requires reconciliation and is not
  automatically safe;
* the V2 route is dry-run-only and refuses `enable_writes=True`;
* `driver/core/driver_neo4j_adapter.py` exposes only the current bounded Core
  command and read-only preflight; no Driver scheduler exists;
* Fiscal has source, skip, park, and packet files, but no durable cross-run
  Driver lifecycle or production cursor owner;
* `scripts/earnings/run_ledger.py` belongs to old Guidance, prediction, and
  learning operations. Its lock-and-fsync technique is a lead, but its
  business fields, random run identity, last-row-wins semantics, silent
  malformed-line skipping, and lack of atomic event/cursor handling do not
  satisfy this step unchanged;
* no production code other than the bounded Core command calls `run_event`;
* no Driver retry service, schedule, central ledger, catalog-refresh scheduler,
  or crash-resume owner exists.

These are leads, not frozen facts for the future candidate. Re-measure every
one after Steps 7–9A finish.

## Smallest permitted architecture

Freeze this shape before code:

```text
existing scheduler
       |
       v
one bounded Driver command ---- one process lock
       |
       +---- certified channel selector/builder
       |
       +---- one local transactional lifecycle ledger
       |
       +---- existing reader + kernel + Core run_event
       |                       |
       |                       `---- existing Core audit
       |
       +---- existing catalog refresh command
       |
       `---- one structured health/stop report
```

The default minimum is one standard-library SQLite file on approved persistent
single-host storage, with direct SQL and no object mapper or migration
framework. It is justified only because event persistence and cursor movement
must be atomic, duplicate claims must be rejected structurally, and restart
must recover after a process dies between those actions.

Gate 10.0 must still try to disprove that need. If a current live Driver owner
already passes every required atomicity, uniqueness, corruption, and restart
test, reuse it and delete the proposed store. Do not reuse the old earnings
ledger merely because it also writes lines.

Use one production module under `driver/` first. Split it only when the frozen
denominator proves two independently owned responsibilities cannot remain
clear in one module. Source selectors stay under their channel, Core behavior
stays under `driver/core/`, and catalog behavior stays in its current owner.

Do not build a plug-in registry for future channels. Connect only channels that
are certified at this candidate. A second real channel may justify extracting
a shared adapter interface later.

## Runbook decisions that must be frozen before code

Resolve the following as one owner-reviewed packet. Derive an answer from live
authority or measured operating evidence where possible. Ask the owner only
for the remaining real choices.

### 1. Enabled work

For each enabled job, freeze:

* owning channel or subsystem;
* exact production entry point;
* eligible source types and certified groups;
* exact selector and completeness owner;
* live, historical, or both;
* schedule trigger and cadence;
* schedule time zone, daylight-saving behavior, missed-invocation behavior, and
  overlap handling;
* ordering and partition key;
* maximum bounded work per invocation, if required;
* required model roles and cost class;
* success receipt and stop signal;
* activation state, initially off.

The initial channel scope is Fiscal only, limited to groups that passed Step 9A.
Do not add News or another channel as a placeholder.

Also enumerate the already-required non-channel jobs and keep their existing
owners:

* the kernel's create-triggered and nightly-backstop link sweep;
* its deferred-pair and retry-park drains;
* its falsifier, exact-attach audit, calibration, recovery, and fresh-key
  checks;
* Step 8 generic verdict-doorway and read maintenance, if an admitted channel
  uses them;
* incremental catalog refresh;
* lifecycle reconciliation and health reporting.

In Step 10 these run only against saved, fake, or read-only state. A job whose
owner or prerequisites are not final remains disabled. CLAIM and every recovery
mutation remain off.

### 2. Durable identities and revisions

Freeze these meanings without inventing a string grammar:

* one discovered source event is identified by the channel owner plus its
  canonical public `source_id`, even when fetching the complete event later
  fails;
* one submitted revision is that source event plus the full fingerprint of the
  exact ordered V2 event bytes;
* those bytes come from the one live public-input serializer and are exactly
  what Core audits; mapping-key presentation cannot create a false revision,
  while list order and raw-item position remain significant;
* identical resubmission returns or redelivers the existing final receipt;
* a changed ordered payload for the same source creates a visible revision;
* a late item, repaired corpus, or certified locator upgrade never overwrites
  the prior revision;
* an amended filing with its own source identity is a new event;
* two distinct sources with identical content remain distinct;
* raw item position remains the public item reference; content is never used to
  join items;
* each execution attempt has its own durable identity and references exactly
  one channel selection unit and, when submitted to Core, exactly one event
  revision;
* attempt identity never depends only on wall-clock time;
* every attempt pins the exact code tree, configuration, model manifest,
  catalog snapshot, input fingerprint, Core audit identity, and final receipt
  fingerprint.

### 3. Minimal ledger records

The one physical ledger needs only four logical record families:

1. channel selection units, source discoveries, pre-submission outcomes, and
   complete source-event revisions with their exact immutable input artifact;
2. execution attempts and append-only lifecycle transitions;
3. source-selector cursors and the event revision or authorized no-submission
   result that justified each move;
4. receipt delivery acknowledgements written by the owning channel.

The exact Core item rows remain in the Core audit. The ledger references the
final audit by path or artifact identity plus a full fingerprint and records
only the outcome counts required for health reconciliation. It never rewrites
the five public decisions or their codes.

The frozen schema must prove:

* exact allowed fields, types, null rules, and schema version;
* structural uniqueness for event revision, attempt, transition, cursor move,
  audit reference, and receipt acknowledgement;
* explicit allowed transitions; an unknown or impossible transition fails;
* append-only attempt history; no failed run is erased by a later success;
* timestamps are UTC observations, never identity or source-time authority;
* source public time and selection order remain separate from processing time;
* no credential, prompt secret, database password, or unredacted environment is
  stored;
* exact storage root, filesystem/lock assumptions, access permissions, capacity
  alarm, backup, retention, and restore procedure;
* no ledger or artifact is pruned, compacted, or rotated under an unfrozen
  size, age, or convenience rule;
* untrusted source identity is validated by its existing owner and is never
  cleaned into a new identity or used directly as an artifact path; immutable
  artifact names are content-addressed by their full fingerprint;
* all data values use bound database parameters; untrusted input never becomes
  SQL structure;
* an authorized fetch failure may leave a durable discovery without an event
  revision, but never a cursor move;
* a channel-owned lawful no-submission result may justify a cursor move only
  when its exact outcome and completeness evidence are durable and the frozen
  reason matrix authorizes that transition;
* an immutable event or no-submission artifact is fingerprinted before its
  cursor may move; a model response is fingerprinted before its attempt may
  complete;
* corruption, missing artifacts, moved fingerprints, unsupported schema, and
  storage exhaustion stop the run loudly.

### 4. Cursor and selection law

For each enabled selector, freeze:

* the complete eligible source population;
* its stable source identity;
* its source public timestamp;
* deterministic order by company, source public time, then a source-owned
  stable tie-breaker;
* any authoritative monotonic ingestion cursor supplied by the source;
* the complete reconciliation method that catches late or backdated arrivals;
* the exact point at which the selection cursor moves;
* how malformed, missing, ambiguous, or deleted sources are recorded;
* how a changed source revision is detected without guessing from text.

Required safety order:

```text
enumerate and durably record the source discovery
→ channel fetches and accounts for the selection unit
→ either persist one complete event through the one public-input serializer
  or persist one owner-authorized no-submission outcome with its completeness proof
→ atomically register that durable result and its allowed cursor move
→ make a complete event revision eligible to run, or retain the no-submission outcome
```

A fetch failure remains on the discovery and follows only its authorized retry
rule. A crash before atomic result registration may fetch the source again;
uniqueness must converge it. A cursor move may never exist without the exact
durable event revision or owner-authorized no-submission result that justified
it.

If the source supplies no trustworthy monotonic ingestion cursor, use a
complete source-ID census and set difference. Do not invent a fixed look-back
window. At larger scale, optimization may be added only after it proves that
the complete reconciliation path still catches every late source.

Within one invocation, process a company's events chronologically. A newly
discovered older event runs as historical work at its own source time; it is
never dropped because a newer cursor was already seen.

Start with serial event execution under the one process lock. Add bounded
parallel preparation only if measured capacity proves serial work inadequate
and a new test proves per-company order, budget, receipt, and audit identity
remain exact. The existing writer stays globally serialized.

Measure the complete enabled population's processing time against each frozen
schedule before activation. If serial work cannot keep up, report the measured
gap and approve the smallest bounded concurrency change; do not pre-build a
worker pool.

### 5. Live and historical work

Use one event builder, one reader, one kernel, and one Core route. The mode may
change selection and source-time visibility only.

* Historical work uses the requested cutoff and may see only evidence public by
  that cutoff.
* Live work uses the current source graph while keeping source public time as
  the fact date.
* Writes and menus use information visible at or before the event public time;
  history reads remain strictly before the requested read cutoff.
* Live and historical selection may overlap; the event-revision identity makes
  the overlap converge.
* Backfill never sees realized returns, later catalog evidence, future links,
  later source text, or a current menu unavailable at the event time.
* Historical earnings 8-K selection calls the structured periodic-accession
  matcher. Live pre-periodic selection calls the approved quarter-identity
  owner. No third matcher, date guess, fiscal-label guess, or copied condition
  is allowed.
* Backfill priority and maximum work per invocation must be frozen from real
  capacity evidence. Until then, backfill stays disabled rather than starving
  live work.

### 6. Retry, reopening, and drain matrix

Build one mechanically derived table from all reachable structural outcomes.
For every reason, record:

* owning module and exported code or exception type;
* event-level or item-level scope;
* automatic retry, state-triggered reopening, terminal, or loud stop;
* exact trigger that permits another attempt;
* whether source bytes must change;
* whether the saved reader response may be reused or the full reader must run;
* delay, attempt cap, age alarm, and drain limit, if applicable;
* expected receipt after retry;
* positive control that must not retry.

Binding minimum:

* only `SourceUnavailable` carrying `SOURCE_UNAVAILABLE` has general automatic
  retry authority under the live channel contract;
* a new source is processed as a new event and never reopens an old skip by
  itself; an old source reopens only when its own corpus state changes or a
  certified locator upgrade can re-read that same source;
* incomplete source search remains parked until the channel's completeness
  owner reports the missing source state has changed;
* kernel retry parks drain only on the exact arrival or state-clear trigger
  registered by the kernel;
* kernel terminal classes remain counted and do not enter a retry queue;
* vague meaning, rejected identity, elapsed time, or a guessed future filing is
  terminal unless an existing owner exports a different exact trigger;
* `xbrl_internal_conflict` reopens only when that report's parsed structured
  facts change; an amendment is a new report;
* an execution failure, writer-busy result, unknown code, programming error,
  missing audit, or leftover `prepared` audit never enters a blind retry loop;
* unexpected errors propagate, halt the affected bounded run, and alert;
* every retry submits the whole event, preserves the prior attempt, and is
  idempotent at Core;
* no retry may borrow a quote, value, unit, period, or meaning from a later
  source;
* no free-text detail is parsed to choose a transition.

Do not hand-copy the matrix into multiple modules. If an owning component does
not expose its retry class structurally, add the smallest exported registry to
that owner and derive the runner table from it. A reason with no authority is a
stop, not an assumed retry.

Any delay, cap, or rate is an operational fixed value. Derive it from an
official provider rule or measured capacity and freeze it in the one approved
runtime configuration. Do not hide a default in code. No retry is infinite.

### 7. Model, budget, billing, and canary law

Freeze one production model manifest that references, without copying:

* each semantic role;
* exact provider, Sonnet 5 runtime identifier, high effort, token limit,
  response schema, and
  prompt-owner fingerprint;
* `fallback: none` under the first-release ruling;
* request transport and billing class;
* per-call and per-run budget ceilings;
* reservation, actual-use, and remaining-budget accounting;
* canary request, expected structural result, and stop behavior;
* model or prompt change procedure.

The runner must:

* refuse a missing, moved, or unqualified Sonnet 5 pin;
* refuse every fallback, cascade, vote, or provider substitution;
* reserve budget before a call and record actual use afterward;
* stop before, not after, an unauthorized or over-budget call;
* record exact request and raw response identities through the existing model
  audit owner;
* persist and replay the complete response bytes, including
  `continuity_hints`; retries may neither rebuild nor duplicate a relationship
  plan;
* keep canary data out of live Driver admission;
* treat a canary failure, invalid response, credential failure, or model drift
  as a stop;
* never use model confidence to bypass deterministic gates;
* never expose realized returns to a fact, identity, or verdict producer.

Reuse the Step 3 and Step 4 model transports and audit owners. Do not build a
second client or prompt loader in the runner. Prove the operations machinery
with saved responses. A real canary or other call already bounded by the
frozen runbook uses Sonnet 5 at high effort and needs no separate owner
approval; an unplanned or over-ceiling call is forbidden.

If the exact qualified Sonnet 5 high-effort configuration is unavailable,
changed, or fails its canary, stop that role. Do not call another model
automatically. Step 14 remains dormant under the current ruling.

### 8. Health, alerts, and stop conditions

Build one structured health report from the ledger and owner registries. It
must show, at minimum:

* eligible, selected, running, completed, waiting, stopped, and undelivered
  event-revision counts;
* item outcome counts by the five public decisions and structural code;
* source-completeness gaps and late arrivals;
* oldest authorized retry and park-drain age;
* attempts by reason and repeated failures;
* cursor positions and any event/cursor mismatch;
* missing, leftover, moved, or corrupt Core audits and response artifacts;
* exact active code, contract, catalog, model, prompt, and configuration pins;
* budget reserved, used, remaining, and refused;
* catalog-refresh state and last validated artifact;
* every active feature-off flag, including writes and CLAIM;
* the kernel owner's exact link-sweep, deferred-pair, attach-audit, falsifier,
  calibration, recovery, and fresh-key health measures, including fan-in,
  duplicate half-life, refusal rate, and park-drain age where their owners
  expose them;
* graph-write count observed by the no-write proof.

Freeze one existing alert delivery path and prove delivery. A nonzero command
exit plus a durable structured report is the minimum local signal; if the
approved scheduler cannot deliver it to an operator, deployment is blocked.
Do not build a dashboard or general monitoring platform.

Every threshold must come from a live contract, provider standard, measured
capacity, or explicit owner decision. Until a threshold is frozen, report the
raw measure and stop the affected automatic action.

### 9. Crash recovery and rollback

Freeze the exact recovery action for every durable boundary:

1. after source discovery but before or during the channel fetch;
2. after immutable event bytes are stored but before atomic
   event-and-cursor registration;
3. during that transaction and after it commits but before attempt claim;
4. after attempt claim and exact input/configuration pinning but before Core
   starts;
5. after the Core audit reaches `prepared` but before or during the reader;
6. after a raw model response is durable but before Core consumes it;
7. after the final plan is durable but before the Core audit becomes final;
8. after the final Core audit and result but before the operations-ledger
   transition;
9. after that transition but before channel receipt acknowledgement;
10. after acknowledgement but before the bounded process exits;
11. during catalog refresh before and after atomic state publication;
12. during a ledger or artifact write, including storage exhaustion.

On startup, acquire the one process lock and reconcile every nonterminal
attempt before selecting new work. Because only one host and one runner are
allowed, a prior runner session left active after restart is interrupted; no
time-based lease guess is required.

Reconciliation rules:

* a discovery without a complete event or owner-authorized no-submission result
  follows only its authorized fetch retry; it cannot advance a cursor or reach
  Core;
* no registered event revision means the complete channel fetch may occur
  again; an unreferenced fingerprinted payload is reported and retained until
  the frozen artifact reconciliation rule resolves it;
* a cursor move always points to an existing durable event revision or
  owner-authorized no-submission result;
* a complete final Core audit with matching fingerprints may supply the missed
  ledger transition or channel redelivery;
* a missing, corrupt, moved, contradictory, or `prepared` Core audit stops for
  exact reconciliation;
* with writes off, a proved interrupted attempt may be resubmitted as a new
  attempt while preserving the old audit and transition history;
* after writes are ever enabled in Step 11, a `prepared` audit must be compared
  read-only with the graph before any retry; Step 10 does not implement or
  exercise that mutation path;
* rollback stops future invocations, preserves ledger, audits, cursors, and
  source artifacts, restores the previously reviewed code and configuration,
  re-runs compatibility and integrity checks, then resumes from the durable
  ledger;
* rollback never deletes, rekeys, rewrites, or hides history.

### 10. Incremental catalog refresh

The runner may invoke only the Step 7 catalog owner's published refresh entry
point. The runbook must preserve:

* base plus delta folding;
* old-to-old decisions frozen at every level;
* the catalog source-ID ledger;
* the catalog owner's exact skip/reopen and park/terminal rules;
* inherited locked ruleset fingerprint;
* approved industry fold list;
* Transcript identity immutability before the first refresh;
* prior Driver types frozen during finalization;
* all already admitted live Drivers and earlier catalog decisions protected
  from batch overwrite;
* latent bases excluded from fold inputs;
* atomic publication of `_state.json` only after validation;
* finalizer-fingerprint mismatch as a loud owner signal, never automatic type
  invalidation;
* continued use of the prior validated catalog after any failed refresh;
* no graph bulk-sync; Drivers remain lazily born-complete with their first
  admitted fact.

The runner records the exact input sources, base artifact, delta, ruleset,
finalizer, validation result, output, and state-file fingerprints. It neither
opens catalog decisions nor copies finalizer logic.

### 11. Consumer cutover and empty history

Step 10 prepares but does not perform the later consumer move. Freeze the
operational handoff:

* the Step 8 read layer is the only Driver read owner;
* zero Driver records returns the already-proved lawful empty result, not an
  old-Guidance fallback or crash;
* a consumer never reads a partly published catalog, incomplete run, or
  unresolved receipt;
* consumer cutover waits for Step 11's approved graph pilot and Step 12A;
* stopping the Driver runner does not reactivate old writers automatically;
* old Guidance remains separate and unchanged until its own retirement gate;
* the cutover and rollback inventories are derived from real callers at their
  execution candidate.

## Fixed gate sequence

Only one gate may be active. A failed gate stays active until fixed or formally
blocked. Later work cannot make an earlier red gate green by assertion.

### Gate 10.0 — Freeze candidate and denominator

**Scope:** current authorities, production code, callers, scheduled jobs,
configuration, storage, tests, and all external effects reachable from the
future running entry point.

**Denominator:** programmatically enumerate:

* every production entry point and real caller;
* every channel selector, source type, source query, completeness branch, and
  source outcome;
* every Core public decision, structural code, exception class, and run state;
* every kernel retryable park, terminal outcome, deferred pair, and recovery
  trigger;
* every lifecycle transition and crash boundary;
* every cursor partition and source-order key;
* every model role, prompt owner, budget, and network call, plus the required
  refusal of every model fallback path;
* every file, ledger, audit, cache, source, graph read, possible graph write,
  and deployment artifact;
* every existing test and proof owner relevant to those paths.

Account for every match as in scope, owned dependency, proof-only, dead,
unrelated, or later work. Nothing disappears unexplained.

**Evidence:** exact commit and tree; staged/worktree/untracked state; path/blob
manifest; call graph; raw scanner output and classifications; dependency and
environment pins; read-only source and graph censuses; current test collection;
proof that no existing Driver running owner already satisfies the need.

**Complete when:** the denominator is stable, every reachable behavior has one
owner, the exact enabled Step 10 scope is known, and no unknown candidate byte
or unclassified side effect remains.

### Gate 10.1 — Freeze the minimal runbook

**Scope:** the eleven decision sections above and no implementation.

**Denominator:** every enabled job, event identity, revision rule, ledger field,
transition, cursor rule, retry/reopen reason, schedule value, model role,
budget, canary, alert, stop, recovery action, catalog-refresh action, and later
consumer handoff.

**Evidence:** authority citation or measured basis for each choice; rejected
larger alternatives; one explicit owner packet for only the choices that cannot
be derived.

**Complete when:** `BUILD_AND_OPERATIONS.md` §7 or its named live owner is no
longer design-incomplete for the enabled initial scope; every fixed value is
authorized; unsupported jobs remain off; and the owner approves the exact
runbook and configuration surface.

No production code begins before this gate closes.

### Gate 10.2 — Build the lifecycle ledger TDD-first

**Scope:** one local transactional ledger, one process lock, immutable payload
artifact, schema/integrity command, and tests. No channel, model, Core, catalog,
or graph action.

**Denominator:** every frozen record field, uniqueness rule, transition,
corruption case, storage failure, and startup-reconciliation state.

**Evidence:** failing public-ledger tests first; lawful controls; direct schema
inspection; branch coverage; mutation or equivalent proof for uniqueness,
transition, fingerprint, atomicity, and corruption guards.

**Complete when:** exact event bytes or an authorized no-submission result are
durable before one transaction registers that result and any allowed cursor
move together; duplicate claims converge; illegal transitions fail; complete
history survives restart; corruption and missing artifacts stop; and no second
ledger truth exists.

### Gate 10.3 — Connect certified selection, cursors, and backfill

**Scope:** certified Fiscal selection only, using the exact channel owners and
the one ledger. No reader, model, Core route, or graph write.

**Denominator:** every enabled Fiscal source group; every eligible live source
in the frozen read-only census; every historical boundary; every late,
duplicate, amended, malformed, missing, ambiguous, and changed-source branch;
both PER-21 routes.

**Evidence:** RED-first outer-command tests; complete real read-only source-ID
census; deterministic-order proof; cursor/event reconciliation; PIT attacks;
lawful controls; mutation proof that deleting the durable-before-cursor rule or
late-arrival reconciliation is detected.

**Complete when:** every eligible source is selected once per exact revision,
late events cannot be lost, identical submissions converge, changed revisions
stay visible, historical selection cannot see future evidence, and no third
8-K matcher exists.

### Gate 10.4 — Connect the existing V2 route and receipt delivery

**Scope:** invoke the real channel builder, shared reader, kernel, and Core
route from the bounded runner; persist references to their existing evidence;
deliver the exact final receipt to the channel. Writes remain off.

**Denominator:** every selected real saved event; every raw item; all five
public decisions; lawful split and fusion shapes; reader abstention; channel
rejection; source and identity parks; Core failure; channel-delivery failure;
duplicate delivery.

**Evidence:** saved exact reader responses and frozen real events; one-to-one
event/input/audit/receipt/channel-ledger reconciliation; public-path tests;
positive controls; full Core audit fingerprints; graph read-only transaction
and count comparison.

**Complete when:** every event revision has one reconstructable attempt, every
submitted raw item has all and only its lawful rows, redelivery is idempotent,
no rule is copied into the runner, and the graph is unchanged.

### Gate 10.5 — Implement retries, reopenings, and drains

**Scope:** dispatch only the frozen structural matrix. No new reason or meaning
decision.

**Denominator:** every reachable reason in the Gate 10.0 inventory, including
all positive retry/reopen triggers and one near-miss control for each.

**Evidence:** TDD through the bounded command; simulated outages and state
changes; whole-event proof; duplicate/loss accounting; age/drain metrics;
mutation proof that an unauthorized reason, prose parser, missing cap, or
item-only retry is caught.

**Complete when:** every reason has exactly one action; only authorized work
re-enters; terminal cases stay terminal; unknowns stop; whole-event retry
cannot duplicate or lose a fact; and no loop is unbounded.

### Gate 10.6 — Add model, budget, canary, health, and alert guards

**Scope:** invoke existing model guards and emit one operational report/alert.
Do not add a model client, prompt, semantic check, or dashboard.

**Denominator:** every production model role; zero allowed fallbacks; all budget states;
canary pass/fail; invalid response; credential failure; pin drift; every health
field, alert, and stop condition in the frozen runbook.

**Evidence:** saved-response transport tests; fake budget and credential
boundaries; alert-delivery proof; configuration fingerprint tests; mutations of
model ID, prompt hash, cost, fallback, and stop branches. Any real call must be
inside the frozen runbook ceiling and have a raw receipt; it needs no separate
owner approval.

**Complete when:** no call can occur under unknown identity, budget, billing,
or configuration; every stop is durable and visible; and health totals
reconcile exactly with ledger, channel, kernel, catalog, and Core owners.

### Gate 10.7 — Connect incremental catalog refresh

**Scope:** schedule and record the existing refresh owner. Do not change catalog
meaning or sync catalog nodes to the graph.

**Denominator:** every base, delta, source ID, old-to-old decision, fold level,
industry, prior type, latent, finalizer result, validation sidecar, output, and
state publication.

**Evidence:** RED-first invocation tests; current real catalog artifacts; two
identical rebuilds; planted old-decision drift; changed Transcript identity;
finalizer-fingerprint mismatch; crash before and after state publication;
failed-refresh preservation of the prior valid artifact.

**Complete when:** a valid delta publishes atomically and deterministically;
old decisions and prior types remain fixed; every invalid or interrupted run
leaves the prior catalog active; and no graph node is created.

### Gate 10.8 — Prove crash recovery, rollback, and empty-history handoff

**Scope:** all frozen crash points, startup reconciliation, code/config
rollback, and the later consumer handoff contract. No live consumer move.

**Denominator:** every nonterminal ledger state, every audit state, every
cursor/receipt ordering edge, every catalog publication edge, the empty Driver
graph, and one lawful nonempty synthetic/read-only control.

**Evidence:** process-kill or equivalent fault injection at every listed
boundary; restart from the same durable store; artifact corruption; disk-full
and permission failures; old-binary/new-schema refusal; read-layer empty
history tests; rollback rehearsal to the exact prior candidate.

**Complete when:** no crash loses or duplicates an event; every uncertain audit
stops for reconciliation; rollback preserves all evidence and resumes safely;
and consumers can lawfully observe empty Driver history without old-Guidance
fallback.

### Gate 10.9 — Final exact-candidate proof

**Scope:** the full disabled running candidate on frozen real saved Fiscal
events and a fresh read-only source/graph census.

**Denominator:** every Gate 10.0 row, enabled job, event revision, raw item,
attempt, outcome, retry, exclusion, cursor move, receipt, artifact, test
identity, changed branch, mutation, and file in the candidate.

**Evidence:** isolated clean worktree; exact dependency/configuration/model and
catalog pins; complete manifest; focused and full regressions; branch and
mutation results; crash matrix; two deterministic replays; graph transaction
and count comparison; credential scan; staged-tree identity.

**Complete when:** all in-scope rows are closed; every finite population count
reconciles; every changed branch is proved; every required mutation is caught;
all regressions pass; the graph, old Guidance, source data, live cursors, and
external caches are unchanged; schedules remain disabled; and no model call,
graph write, activation, or unapproved external action occurred.

## Required test matrix

Derive exact tests from Gate 10.0. At minimum prove:

### Event identity and accounting

* identical event and bytes submitted once and many times;
* same source with a changed ordered payload;
* same content under two source IDs;
* two identical raw items at different positions;
* one raw item splitting into several facts;
* several raw items fusing into one fact;
* mixed accepted and non-accepted rows from one raw item;
* zero-fact terminal outcome;
* every raw item, Core row, audit, and channel acknowledgement reconciled;
* full fingerprints catch one changed byte.

### Source order and completeness

* two events at the same public time;
* a late event older than the cursor;
* an amended filing;
* a deleted or unavailable source after selection;
* missing or malformed source time;
* duplicate source discovery by two invocations;
* complete-corpus skip and incomplete-corpus park;
* every owner-registered skip-reopening trigger and a near-miss;
* a later source processed separately from an older event;
* historical cutoff immediately before, at, and after source public time;
* live/backfill overlap;
* both PER-21 routes and refusal of a third-route substitute.

### Retry and stop behavior

* `SOURCE_UNAVAILABLE` retries the whole event;
* every kernel retry park drains only on its exact trigger;
* every terminal class remains terminal;
* vague and age-only waits never enter a retry queue;
* a triggered older whole event uses only its original source evidence;
* an unknown code or exception stops;
* writer busy and execution failure do not retry blindly;
* a `prepared` audit stops for reconciliation;
* retry cap, age alarm, and drain limit at both sides of their frozen boundary;
* retry preserves earlier attempts and cannot overwrite a receipt;
* a state change during retry cannot mix two configurations or catalog
  snapshots in one attempt.

### Concurrency, storage, and crashes

* a second runner cannot acquire the process lock;
* a second claim for one event revision is structurally refused;
* process death at every frozen boundary;
* clock moves backward without identity collision;
* partial, corrupt, missing, or fingerprint-moved artifact;
* ledger schema mismatch and integrity failure;
* disk full, read-only path, permission loss, and failed atomic replace;
* backup and restore of ledger plus referenced immutable artifacts;
* hostile but contract-lawful source identities cannot escape the artifact
  root or collide;
* restart repeats safe work and never skips uncertain work;
* rollback to the prior code/configuration reads the durable ledger or refuses
  incompatibility loudly.

### Models, budgets, and alerts

* exact model/prompt/config pins pass;
* each changed pin fails;
* missing credential fails before request;
* budget below, at, and above its frozen limit;
* reservation released or charged exactly once after each outcome;
* every attempted fallback, cascade, vote, or provider substitution fails;
* canary pass, malformed response, semantic stop signal, timeout, and drift;
* alert delivery succeeds; delivery failure remains a stop with a durable local
  report;
* secrets and raw environment values never appear in artifacts.

### Catalog and reads

* valid base-plus-delta refresh;
* old-to-old decision preservation at every fold level;
* prior type preservation;
* latent exclusion;
* changed Transcript identity;
* finalizer-fingerprint mismatch;
* crash on each side of `_state.json` publication;
* failed refresh leaves the prior catalog active;
* no catalog graph sync;
* empty Driver history and a lawful nonempty control through the Step 8 reader.

### No-write boundary

* runner has no write argument;
* write environment variable cannot bypass V2 refusal;
* every fake/test store records zero mutation calls;
* a fresh read-only graph transaction and object/relationship counts match
  before and after the full run;
* no constraint, sentinel, Driver, DriverUpdate, DriverPeriod, link, recovery
  state, old Guidance object, cursor, cache, or source record changes.

Every negative test needs a lawful positive control. Expected results come from
an independent authority, source census, or calculation, never from the code
under test.

## Implementation order

After Gate 10.1 approval:

1. add the outer failing lifecycle and crash tests;
2. build the smallest ledger and process lock;
3. connect certified source selection and cursor persistence;
4. connect the exact V2 event and Core receipt without models or writes, using
   saved evidence;
5. connect the structural retry/reopen matrix;
6. connect existing model/budget/canary guards and the one health/alert output;
7. connect the existing catalog refresh command;
8. run crash, rollback, empty-history, real-read-only-data, and full no-write
   proof;
9. freeze evidence, update status, and review the exact staged tree.

At each item:

* reproduce the failure first;
* prove the nearest lawful control;
* change the owning function or boundary only;
* delete any replaced duplicate;
* run focused and affected tests;
* prove the test catches the exact change;
* reconcile the denominator before moving on.

## Evidence package

Freeze one manifest containing:

* starting and final commit/tree identities;
* exact authority, contract, code, configuration, dependency, model, prompt,
  catalog, and source fingerprints;
* complete changed-path and blob list;
* frozen denominator and row dispositions;
* source census and selection/reconciliation totals;
* event/revision/attempt/cursor/receipt/outcome totals;
* retry/reopen/terminal/stop matrix and exercised counts;
* crash-point and rollback results;
* budget/canary/alert results;
* catalog refresh and old-decision preservation results;
* focused, full, branch, mutation, and test-identity results;
* before/after read-only graph transaction identity and counts;
* exact proof that no schedule, model call, graph write, or activation occurred;
* every remaining disabled or later item.

Raw source or model material stays in its approved durable evidence store.
Commit it only when repository policy and the owner permit it; otherwise commit
the fingerprinted manifest. Never commit credentials.

## Reviewed commit sequence

Do not mix the design freeze, storage, behavior, or evidence. Proposed commits:

1. approved running-layer law and machine-readable configuration contract;
2. lifecycle ledger, process lock, and crash tests;
3. Fiscal selection, cursor, bounded runner, and receipt-delivery integration;
4. structural retry, reopening, drain, budget, canary, health, and alert guards;
5. incremental catalog-refresh orchestration;
6. final no-write proof, status, and evidence manifest.

Omit an empty commit. Split a commit further when its rows have independent
owners. Before each commit:

* freeze the exact staged path and blob list;
* prove every staged path belongs only to closed rows;
* inspect the staged diff and test the staged tree;
* confirm no unrelated overlap, credential, generated secret, source drift,
  graph change, live cursor move, or enabled schedule;
* obtain Codex `VERIFIED` on the exact staged identity;
* verify local commit, tree, remote branch, and remote tree identities.

No unfinished rule, paid-run artifact, live configuration, graph setup, or
later Step 11 work goes to main. Never force-push or rewrite history here.

## Stop conditions

Stop if:

* any required Step 0–9A prerequisite is incomplete;
* the candidate, authority, contract, source population, model, prompt,
  configuration, catalog, or environment identity is unknown;
* the runbook still has an unresolved choice that changes behavior;
* a fixed value lacks official, measured, or owner-frozen authority;
* an enabled selector cannot prove complete late-arrival reconciliation;
* an event, item, attempt, outcome, cursor move, receipt, retry, reopening,
  exclusion, or artifact is unaccounted;
* implementation needs a semantic pattern, word list, fuzzy rule, magnitude
  rule, date guess, company exception, or copied matcher;
* an owner registry must be copied because it is not mechanically consumable;
* a generic retry would exceed the exact live contract;
* a retry, drain, schedule, budget, or backfill is unbounded;
* an audit is missing, corrupt, contradictory, fingerprint-moved, or left
  `prepared`;
* two runners, hosts, writers, or ledger truths can be active;
* persistent storage lacks the required atomicity, durability, capacity, or
  lock behavior;
* a model call is unplanned or over its frozen ceiling, source retrieval falls
  outside the master public-source ruling, deployment lacks exact approval, a
  commit/push violates the completed-step ruling, or any model fallback is
  attempted;
* a graph write, constraint, sentinel, live cursor movement, schedule
  activation, CLAIM activation, catalog bulk-sync, or old-Guidance change is
  attempted;
* a lawful late, duplicate, revised, split, fused, skipped, or parked case is
  lost;
* a wrong operational acceptance, wrong retry, future-information leak, or
  silent failure is observed;
* any required test, branch, mutation, real-data control, or graph identity
  proof is missing;
* unrelated files move during review.

## Completion condition

Step 10 is complete only when:

* the enabled initial running layer is design-complete in its live authority;
* the implementation contains only the bounded single-host runner, one
  lifecycle ledger, required guards, and connections to existing owners;
* every eligible enabled source event has one durable path from selection to
  exact channel acknowledgement;
* identical submissions converge and changed revisions remain separate;
* late and backdated sources cannot be hidden by a cursor;
* every raw item and public outcome reconciles to the exact Core audit;
* only authorized reasons retry or reopen, every retry is whole-event and
  bounded, and no retry can lose or duplicate work;
* later sources remain separate events and no old event borrows their evidence;
* frozen fact and identity replays preserve zero observed wrong accepts and the
  earlier measured recall exactly;
* every failure is durable, visible, attributable, and recoverable;
* crash and restart at every durability boundary preserve exact accounting;
* model identity, budget, billing, canary, health, and alert guards fail closed;
* no automatic model fallback or substitution is reachable;
* incremental refresh preserves all old decisions and atomically retains the
  last valid catalog on failure;
* lazy born-complete creation is proved as a plan only; no catalog bulk-sync
  exists;
* empty Driver history is lawful and later consumer cutover remains inactive;
* focused and full regressions, 100% new/changed branch coverage, required
  mutations, crash, rollback, real-read-only-data, identity, and staged-tree
  gates pass;
* graph state, old Guidance, source records, live cursors, caches, and external
  systems are unchanged;
* schedules, graph writes, CLAIM, native XBRL, consumers, and old-Guidance
  retirement remain off;
* exact reviewed local and remote identities match after separately approved
  commits and pushes.

The next step is Step 11: a fresh read-only graph census, isolated graph setup
proof, and full shadow operation before any separately approved graph mutation.
Step 9B runs read-only after Step 11 creates the first bounded real Fiscal
records and before any broader Fiscal harvest.
