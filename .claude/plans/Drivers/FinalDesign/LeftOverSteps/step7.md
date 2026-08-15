# Step 7 — Finish and Qualify the Production Catalog

## Goal

Build and prove the final offline catalog of reusable causes under the live V2
rules.

```text
approved source evidence
→ evidence-backed candidate causes
→ company evidence and industry catalogs
→ sector and global reconciliation
→ permanent type and family decisions
→ safety and fitness gates
→ frozen offline catalog
```

The catalog is a retrieval aid. It does not create graph nodes or facts. A
Driver enters Neo4j only later, together with its first proven fact.

## Required starting state

Do not begin until:

* Steps 0–6 are complete, committed, pushed, and independently verified;
* V2 is the sole live public and internal contract;
* the signed Step 2 result memo confirms Sonnet 5 at high effort for every
  required role and fixes its exact runtime ID, transport, prompt contract,
  and triggered design decision needed here;
* the Step 3 shared reader and Step 4 admission system are complete;
* the complete V2 no-write route passed in Step 5;
* the V1-to-V2 switch passed in Step 6;
* every graph write remains disabled;
* no earlier experiment or rule ambiguity needed by this step remains open;
* work starts from the exact Step 6 commit in an isolated clean tree.

If a prerequisite is missing, return it to its owning step. Do not recreate it
inside the catalog builder.

## Authority

Read and apply authority in this order:

1. `FINAL_DESIGN.md` for meaning and safety;
2. the live `ChannelContract.md` and `15_CandidateFactPacket.md` for the active
   V2 boundary;
3. `BUILD_AND_OPERATIONS.md` §4 and §8.1 for the catalog procedure and release
   gates;
4. the signed Step 2 result memo for measured model choices and amendments;
5. `FableExperimentPlan.md` and `FableExperimentWorkOrder.md` for experiment
   discipline;
6. `.claude/plans/Drivers/HierarchicalCatalogPlan.md` only for mechanics
   expressly retained by `BUILD_AND_OPERATIONS.md`.

The old catalog plan contains retired record fields and old prompt law. Its
mechanics are useful only where the live build document adopts them. Historical
runs, receipts, comments, and commit messages are leads, never authority.

## Scope

This step includes only:

* the existing offline catalog tools in `.claude/plans/Drivers/workflows/`;
* the smallest current-law corrections to those tools;
* the missing catalog finalizer;
* the exact eligible universe, seed roster, held-out sets, and source snapshots;
* company, industry, sector, and global catalog construction;
* duplicate reconciliation and repair;
* permanent type and family finalization;
* the seed-size, eligibility, defense, gauntlet, detector, and final fitness
  gates assigned to this phase;
* one frozen, fully accounted offline catalog and its proof files.

This step excludes:

* every Neo4j write, catalog-node sync, constraint, or sentinel creation;
* live schedules, retries, cursors, alerts, or recovery services;
* live shadow traffic and the later synchronous-versus-asynchronous link test;
* the text-fact concept linker and native-XBRL materializer;
* the Driver read layer, verdict writer, and old-Guidance retirement;
* Fiscal source-location certification;
* news as catalog-build input;
* other channels;
* the deferred X-C alternate-chunking test unless the current chunk shape
  fails or a new production choice is required, and the batched fold-repair
  optimization;
* dependency upgrades without a reproduced need;
* folder moves or unrelated cleanup;
* any new design, threshold, vocabulary, or exception.

Fiscal certification and the design-only part of the operating runbook may run
in parallel. Anything needing real catalog candidates waits for this step.

## Non-negotiable rules

* A wrong merge is worse than a duplicate. Uncertainty keeps causes separate or
  parked.
* Models decide meaning. Code may split bytes, normalize format, count, sort,
  hash, verify, route, and apply already-approved decisions only.
* A string, list, number, threshold, pattern, or regular expression may change
  behavior only when copied from a live rule, frozen protocol, or official
  standard, or mechanically derived from one.
* Regular expressions and token overlap may check syntax or suggest review
  pairs. They may never decide that two causes mean the same thing.
* Embeddings may suggest or rank. They never merge, admit, type, or reject.
* One rule has one owner. Extend existing normalization, reconciliation,
  assembly, repair, finalization, validation, and manifest owners; add no second
  version.
* Reuse the existing test and proof owners. Add proof machinery only when no
  existing owner can prove a required completion condition.
* Preserve every lawful case. Missing proof fails closed and its recall cost is
  counted.
* The release claim is zero observed wrong accepted merges on the frozen tests,
  not a mathematical promise over all future language. Report the measured
  upper bound and every miss.
* Use test-first changes and cover every changed success, refusal, park, crash,
  and recovery branch.
* Build the smallest code that satisfies current evidence. Delete retired
  behavior before adding machinery.

The fixed values already authorized by `BUILD_AND_OPERATIONS.md`—including
chunk, batch, evidence-view, repair, retrieval, and fitness values—are legal.
They must have one code owner and must not be copied into a second rule source.

## Verified starting leads

Recheck these against the exact Step 6 tree before acting:

* `fold_catalogs.js` still points a meaning decision at the retired
  `DriverOntology.md` and carries literal Opus role choices that conflict with
  the Sonnet 5 ruling;
* `build_tree.js` and `ab_pair_judge.js` carry the same stale literal Opus
  choices;
* the read-only tree-list route lacks the same billing guard as other routes;
* `fold_catalogs.py`, `validate_catalog.py`, and fold fixtures still carry the
  retired `optional_links` shape;
* `validate_catalog.py` has stale record-shape text;
* `gate.js` has stale default-Restaurants description text;
* `fetch_company_sources.py` still describes a non-earnings 8-K item code as
  semantic Driver evidence although the item/content taxonomy is open and the
  item-code feature is deferred;
* `catalog_first.js` is the retired old reuse path and `rescue_review.py` is a
  one-off relic; prove zero production callers and delete rather than repair
  them;
* the required `finalize_catalog.py` does not exist;
* higher-level prompt-mirror tests are incomplete;
* every existing rule-bearing catalog under `runs/2026-06-*` is historical and
  cannot seed or baseline this build.

These are verified leads, not an automatic edit list. Reproduce each mismatch
on the Step 6 tree and close only the ones that still exist.

## 1. Freeze the exact work denominator

Before editing, record:

* Step 6 commit and tree hashes;
* index, worktree, staged, and untracked state;
* Python, Node, database-driver, parser, and model-runtime versions;
* every catalog entry point and reachable helper;
* every rule-bearing prompt, response schema, model slot, threshold, validator,
  finalizer input, output file, and consumer;
* every workflow test identity and current result;
* every current catalog or source artifact and its hash;
* fresh read-only counts for Driver, DriverUpdate, DriverPeriod, relevant links,
  and old Guidance objects.

Build one functionality table:

```text
behavior | real failure prevented | authority | single owner | callers |
tests | keep/simplify/delete | completion proof
```

Classify every rule-like code match as:

* required current behavior;
* mechanical implementation of current behavior;
* retired behavior to delete;
* test or evidence data;
* historical artifact;
* unrelated to Step 7;
* unresolved authority conflict.

Every reachable branch, model call, source category, output row, failure result,
and deferred item must enter the denominator. Nothing may disappear because a
manual search missed it.

## 2. Freeze the production population

Use fresh read-only data to derive the complete eligible Company → Industry →
Sector universe. Do not use a handwritten roster or confuse this universe with
the smaller seed roster selected by `S1`/`X-S1`.

The standing population ruling in Steps.md settles the old 796-versus-786
discrepancy: run the current official read-only query at one recorded cutoff
instant and accept its complete mechanically eligible result. Never choose,
trim, or pad the population to reach either historical number.

Apply the standing lifecycle ruling in Steps.md: new eligible companies use
live admission until the next separately reviewed catalog refresh; companies
no longer officially eligible add no new catalog source material, while all
existing history and evidence remain intact. Add no automatic deletion,
rewrite, company exception, or second lifecycle registry.

Then produce one hash-bound population manifest containing:

* every included and excluded company with its reason;
* exact industry and sector membership;
* every single-company industry;
* the source-time cutoff;
* the exact read-only query and raw output;
* counts that reconcile company → industry → sector → global with no orphan or
  multiple-parent row.

The pre-`S1` population manifest must keep three roles distinct:

* the complete eligible universe produced by the standing data-derived
  population ruling;
* the companies eligible for each seed-size arm;
* held-out companies and events used only for later gates.

Freeze the seed-selection rule before seeing gate results. A held-out company or
event must never enter the catalog it later tests. After `S1`/`X-S1` passes,
write a separate hash-bound seed-roster manifest mechanically from that frozen
rule; do not rewrite the population manifest.

The frozen manifest applies to this production build. Later eligible arrivals
use the live admission path until the next separately reviewed catalog refresh.

## 3. Freeze every missing runnable gate before calling a model

The live documents name several gates but do not fully define their runnable
protocols. Before any call for one of them, create one reviewed protocol
record for:

* `S1`/`X-S1`—one seed-size test, not two tests with different names;
* `S4`—the company-count and eligibility-floor test;
* `X0–X9`—the defense-ladder tests;
* `X-G`—the seed gauntlet;
* `X-IM`—the detector and validator-mutation proof;
* `OD-6`—the final fitness and honesty gate;
* `S2`—only as a conditional protocol if the final fitness gate is red.

Each protocol must freeze the applicable fields below and explain every `N/A`:

* exact purpose and owning rule;
* exact input population and held-out split;
* complete denominator;
* model-free, producer, judge, and grader arms;
* exact Sonnet 5 runtime ID, high effort, prompt bytes, and call count;
* independent answer-key owner;
* metrics and formulas;
* pass, fail, and inconclusive conditions;
* whether equality at each published floor passes—the live documents use both
  “floor” and “beat,” so this must be explicit before results exist;
* retry, blind-regrade, and fresh-key rules;
* stop and cost limits;
* exact raw and derived artifacts and their hashes.

Reuse the Step 2 Sonnet 5 roles. The call that produced an answer may not
author its hidden truth or grade that same answer; required review uses a
separate blind Sonnet 5 high-effort call. A protocol gap stops the affected
gate; it never becomes an implementer choice or code constant. A reviewed,
bounded package needs no separate owner or spending approval.

## 4. Freeze the source snapshots

Do not harvest the complete eligible universe. Source collection has exactly
two catalog stages:

1. after the `S1`/`X-S1` protocol is frozen, collect only the companies and
   sources that its pre-registered arms require;
2. after that gate selects a size, derive the seed roster from the frozen rule
   and collect only that roster's catalog sources.

For each selected company, inventory all supported non-news sources under the
live source rules. Preserve every byte of every source component that contract
selects; do not select only high-move or easy events or expand the supported
component set.

The exact public, free sources selected by either frozen stage are
pre-authorized under the master public-source ruling. Stop before any paid,
private, separately metered, wider, or open-ended collection. Prefer an
existing snapshot only when its source IDs, cutoff, bytes, and coverage exactly
match the relevant frozen roster.

Each source manifest must record:

* company, source kind, source ID, byte hash, and publication time—or the
  authorized explicit absence of a publication time;
* source query or cache origin;
* every source with empty or unusable content;
* every zero-yield source and company;
* every exclusion and its frozen rule;
* complete source counts before and after each processing stage.

Keep gate-only sources in separate held-out manifests; they never enter the
catalog they test. Under the first-release 8-K taxonomy ruling, an item code is
metadata or abstain-only evidence: it may not coin, merge, type, rank, or route
a cause or fact. The source description or document text remains usable only
under the ordinary evidence rules.

Chunk by the existing byte-preserving ladder. Prove:

* no source byte is clipped or normalized;
* ordered chunk bytes reconstruct the original exactly;
* every declared part exists once;
* every chunk is processed once or is visibly pending;
* resume reuses only hash-identical completed work;
* missing, altered, duplicate, or out-of-scope chunks stop the run.

## 5. Write the behavior tests first

Before every behavior change, add a failing test that reproduces the live
defect and a nearby lawful control.

At minimum, test first for:

* stale prompt law reaching a higher-level merge;
* a literal model choice bypassing the frozen role configuration;
* any route that can call a model without the billing guard;
* retired `optional_links` surviving assembly, fold, validation, or fixtures;
* a catalog reaching a consumer before finalization;
* a missing, duplicate, extra, malformed, stale, or tampered finalizer verdict;
* an unapproved merge or rewrite reaching the catalog;
* a dropped source, chunk, candidate, refusal, park, or zero-yield row;
* a failed validator whose output is nevertheless consumed;
* a changed child catalog whose old validation receipt is reused;
* an interrupted write leaving a publishable partial artifact.

Expected results must come from the live contract, independent adjudication, or
an independent calculation. Never generate the expected answer with the code
being tested.

Delete tests that preserve retired fields or old prompt law. Move any still-
required behavior to its current owner.

## 6. Make the smallest builder corrections

Change only defects reproduced in §5 of this work order.

Required correction classes are:

1. Make the leaf, gate, reconcile, fold, repair, and pair-review prompts mirror
   current naming, slice, type, and cross-flavor law. Extend the existing
   rulebook-sync test; do not build a runtime document loader or a second rule
   store.
2. Route every model call through the one Step 2 Sonnet 5 high-effort
   configuration. Require its exact runtime ID and transport in the run
   manifest. Remove stale literal role choices and do not add another model
   registry.
3. Put the existing billing guard before every call-capable route, including
   tree listing.
4. Delete class-level XBRL guesses, `optional_links`, their conflict machinery,
   and fixtures that preserve them. XBRL links belong to later fact-level
   enrichment.
5. Correct stale descriptions only where they can misdirect an operator or
   test.
6. Delete a proven zero-caller retired workflow; do not modernize or replace it.
7. Add only the prompt-mirror, current-law, and branch tests needed to prove
   these changes.

Preserve the existing byte chunker, one reconciliation law, deterministic
assembler, duplicate-repair owner, bounded batching, validators, resume logic,
and explicit-run-ID tree walker. Do not rewrite working machinery.

## 7. Build the one missing finalizer

Add the planned `workflows/finalize_catalog.py` and no surrounding framework.
Use the one `stamp_fact_type` and `resolve_base_metric` owners built by
`step4.md`; do not copy their semantic rules.

Separate decision preparation from deterministic application. Before invoking
  the finalizer's apply path, use the existing model runner and those
shared owners to produce the hash-bound admission and type decisions required
by the frozen catalog:

* run the frozen terminal-name question twice in independent Sonnet 5
  high-effort calls for every
  terminal guidance or surprise name and retain both evidence-backed answers;
* run the frozen bare-name type and metric-proof path with Sonnet 5 at high
  effort for every self-canonical
  record and final-level wording variant;
* send a failed terminal admission through its governed rewrite-or-park path;
  apply every bare-name outcome exactly as `step4.md` specifies, including its
  counted action default and warning;
* freeze complete `terminal_admissions.json` and `fact_type_decisions.json`
  files before the finalizer reads them.

Request manifests are derived once, deterministically, from the validated input
and the shared live prompt owner. The existing approved runner supplies the
saved responses. Do not add a model client, prompt copy, or second workflow
framework to the finalizer.

The finalizer accepts only an unchanged, fully validated catalog, the complete
frozen decision files, and their required admission evidence. It must fail
before reading catalog records if the validation receipt or any input hash does
not match. It makes no model or network call. It must:

1. reject any input record already carrying a permanent type;
2. enumerate every surviving catalog record exactly once;
3. verify one bound decision for every self-canonical record and wording
   variant, plus both required terminal answers where applicable;
4. stamp self-canonical records only; variants copy their canonical record’s
   type;
5. apply terminal `_guidance` and `_surprise` admission only from the complete
   frozen two-answer memo;
6. apply bare-name types only from the complete frozen type and metric-proof
   decisions;
7. build `BASE_METRIC` families by the exact normalized lookup order;
8. keep an absent real base as a latent entry in `families.json`, never as a
    catalog record or retrieval candidate;
9. give action/event records no base-metric link;
10. preserve reversible `SAME_AS` links and never replace them with family
    links;
11. preserve the approved `fact_type_decisions.json` bytes and write the final
    catalog, `families.json`, and `fact_type_disagreements.json` through
    temporary files and atomic renames;
12. run final validation and bind the final catalog, family file, approval file,
    and fold state by hash.

Hard-fail on:

* missing, duplicate, extra, unbound, or malformed decisions;
* a changed input or response after its expected-count/hash check;
* a variant receiving an independent permanent type;
* a terminal suffix with no valid admission memo;
* stacked suffixes or a suffix/base mismatch;
* a guidance or surprise record with zero or more than one base;
* an unproven non-latent base;
* a latent name colliding with a record, variant, skip, or park;
* a suffixed latent name;
* a family pointing at a non-metric base;
* a cross-flavor `SAME_AS` link;
* any consumer reading a non-final catalog.

Test every branch before the implementation. Deliberately mutate each final
check and prove the suite detects it.

## 8. Certify current law before a real run

On the exact candidate:

1. compare every rule-bearing prompt, schema, model role, threshold, and
   validator with the then-current live authority;
2. prove the rulebook mirrors are exact;
3. prove all model aliases resolve once to exact IDs and stay fixed for the
   whole run;
4. prove no retired field or prompt source remains reachable;
5. rebuild fixtures under current law;
6. replay frozen model answers through deterministic stages twice and require
   byte-identical outputs;
7. run one current-law calibration leaf;
8. run one real second industry;
9. run the first real two-industry fold through `build_tree.js`, never by hand;
10. require every validation, repair, fold, and finalization receipt to be green
    and hash-current.

The old Restaurant rule-bearing outputs are never baselines. A sanctioned raw
text copy may be reused only after its exact source and chunk hashes pass.

Do not claim that repeating a model call must return identical wording. The
reproducibility claim is narrower: frozen inputs, prompts, settings, raw
responses, deterministic transforms, and pass/fail accounting can be replayed
exactly.

## 9. Run the seed-size and eligibility gates

Run the single frozen `S1`/`X-S1` protocol before fixing the production
companies-per-industry depth.

* Use the pre-registered population and arms.
* Measure the coverage gain and cost at each frozen size.
* Select only the size rule named by the protocol.
* If no coverage knee exists, stop and return the seed strategy to the owner.
* Never choose a size after seeing which value makes later tests green.

Write the separate seed-roster manifest from that result, freeze its §4 source
snapshot, and only then build the full seed. Run the frozen `S4` protocol
on the resulting evidence distribution before assigning eligibility standing.

* Report company counts only as descriptive evidence.
* Let the approved judge decide evidence coherence.
* Do not turn popularity into meaning.
* Do not build a `BROAD` label or mint standing from company count.
* An unproved catalog card remains young, not silently established.

## 10. Build the complete production catalog

Use the frozen population, source snapshot, model roles, and current-law
builder.

For each selected seed company and every included industry:

1. read every approved source in source-time order;
2. split it without changing or dropping bytes;
3. give each chunk to the blind catalog reader with only the rules needed to
   coin evidence-backed causes;
4. record every raw response, invalid response, abstention, candidate, quote,
   and zero-yield result;
5. group exact normalized names mechanically;
6. run the same admission, duplicate, and refutation law used at every level;
7. assemble only approved results;
8. validate;
9. run duplicate repair;
10. validate the changed bytes again.

Then fold explicitly:

```text
company evidence → industry leaves
industry leaves → sector catalogs
sector catalogs → one global catalog
```

Use the three-level tree by default. Split an oversized review into deterministic
bounded batches and reconcile the results again. Never send an oversized full
seed to a model. A one-child level may pass through visibly; no level may be
silently skipped.

Every leaf, sector, and global output must carry its exact inputs, counts,
decisions, parks, repair results, model settings, hashes, and validator receipt.

## 11. Reconcile and repair without semantic code

At every level:

* within one leaf, exact normalized names use the existing mechanical grouping;
  a mixed-meaning flag sends only that group to the governed same-name review;
* across child catalogs, identical normalized names are review candidates, not
  automatic semantic merges;
* a different-name pair reaches review only through an approved suggestion
  channel;
* every proposed merge or wording rewrite passes the same object, scope, and
  mechanism test;
* high-impact merges receive the required independent second view and both
  decisions must pass;
* uncertainty parks or remains separate;
* approved synonym links remain reversible;
* the deterministic assembler, never a model, applies the decision;
* repair only adds approved links among surviving records;
* repair never touches skips or parks and never reopens an approved link;
* every repair result is reassembled and revalidated through the same owners.

Token overlap and embeddings may propose pairs. Neither may decide sameness.
Cross-batch missed synonyms are safe under-merges; the required repair pass
measures and reduces them without weakening the merge rule.

Account exactly for:

* child names entering a fold;
* names preserved;
* names linked as variants;
* same-name splits;
* skips;
* rewrite parks;
* same-name parks;
* repair candidates, accepts, refusals, and unclear results;
* evidence references before and after every union.

## 12. Finalize and freeze the catalog

Run the finalizer only after the global catalog and repair pass are green.

Require:

* every surviving record has exactly one permanent type;
* every variant inherits its canonical type;
* every guidance and surprise record has exactly one valid base family;
* every action/event record has no base family;
* every latent base is valid, hidden, and absent from the catalog records;
* every disagreement is recorded and resolved or blocks finalization;
* no skip, park, latent, or side-list row enters retrieval;
* the final validator records `final=true`, preserves the fold flag, and binds
  every required file hash;
* the existing retrieval owner consumes only that final, validated catalog.

Freeze the raw model responses before finalization. Replay the deterministic
assembly and finalization twice and require byte-identical final files.

## 13. Run the frozen defense ladder

Run `X0–X9` exactly as owner-frozen in §3 of this work order.

The input must include the named hard families: broader-versus-narrower causes,
different benchmarks, cause versus result, same words with different
transmission mechanisms, different ownership scopes, no-rival ambiguity, and
known calibration pairs.

Do not infer the missing meanings of `X1–X9` from their labels or old archived
documents. Their approved protocol is the only runnable authority.

Any batch-versus-live decision difference stops the build as an implementation
fork. Any wrong merge stops the affected arm. A failed key becomes regression
evidence; it is never edited to pass.

## 14. Run the seed gauntlet

Run `X-G` against the frozen catalog and the real decision system built by
`step4.md`, with writes disabled.

### Static checks

* Single-token names must receive the required mechanism review before standing.
* Bare category names forbidden by current naming law must fail.
* Company, ticker, measurement, period, direction, and other forbidden tokens
  must be detected from the frozen rules and mechanically derived population
  data, never a hand-maintained sector list.
* A record whose own evidence splits into several mechanisms must be reviewed.
* A record attracting unrelated causes must be reviewed as a possible gravity
  well.
* Type and base family must be re-derived from evidence without revealing the
  suffix; disagreement on a guidance or surprise record fails.

### Dynamic checks

Pass the existing nine families:

1. three different demand mechanisms remain three causes;
2. metric, guidance, and surprise route separately with correct family links;
3. an owned segment stays a slice while an external cause stays in the name;
4. measurement words go to measurement, not the name;
5. stated per-X forms follow the written-out denominator law;
6. company, brand, and geography slices do not pollute names;
7. identical words with different mechanisms never converge;
8. a narrower species does not merge into its broader genus;
9. named benchmarks remain distinct from each other and from a generic metric.

Pass only when:

* forbidden static hits are zero;
* every review flag is proved clean or quarantined from the seed;
* wrong convergence across all nine dynamic families is zero;
* every input and decision is accounted for.

A card earns established standing only through the approved evidence and
gauntlet path. An unprovable card remains young. No partial catalog is synced.

## 15. Prove the detector and validator system

Run `X-IM` using the `step4.md` implementation; do not create catalog-local
copies.

Plant and detect every detector class enabled by the `step4.md` minimum,
including:

* one supposed cause splitting across incompatible accounting concepts or
  dimensions within a company;
* contradictory same-company, same-period, same-scope behavior under one head;
* two differently named heads repeatedly mapping to the same company, period,
  and accounting concept;
* duplicate qualitative causes with matching company and event patterns, if
  qualitative causes are enabled;
* suffix-hidden type or family disagreement;
* a planted wrong attachment.

Periodicity, market-reaction, extended drift, and other deferred detectors stay
off unless their existing trigger was met and their protocol was frozen before
this run. Do not build a deferred detector merely to make `X-IM` larger.

For each detector:

* prove its planted corruption fires;
* prove a nearby lawful control stays clean;
* prove missing evidence cannot become a semantic verdict;
* prove the only automatic action is the frozen reversible safety action;
* prove the recovery graders receive raw evidence, not the detector’s claim.

Mutate every applicable `step4.md` validator and prove a test fails. The planted
wrong attachment must end disputed and excluded from cross-company features.
Zero silent detectors and zero surviving mutations are required.

## 16. Run the final fitness and honesty gate

Freeze the final catalog before selecting or calling any final-gate producer.

Use fresh, held-out events from industries covered by the catalog. The key and
all slots must be fixed and hashed before calls. No producer may see future
information, returns, hidden answers, or evidence public after its event.

Require:

* at least 3,000 fixed graded slots;
* at least two independent producers;
* two independent Step 2-qualified graders, each distinct from the producers
  under the frozen independence rule;
* name-plus-direction performance against the frozen 0.634 registry and 0.535
  blind baselines using the pre-registered comparison operators;
* producer agreement against the frozen 72% baseline using the pre-registered
  comparison operator;
* zero two-grader-confirmed wrong merges;
* zero unresolved flags after the single allowed blind regrade;
* every invalid response, miss, false refusal, park, skip, and unscorable slot
  counted;
* recall, missed reuse, and park rates reported even when precision passes;
* the rule-of-three upper bound reported with every zero-error result.

No safety bar may be relaxed to improve recall. Target complete recall wherever
deleting an unnecessary restriction, reusing an existing owner, or making a
smaller general correction recovers it without reducing precision. Report any
residual loss; never add special-case machinery.

A red or inconclusive result does not permit prompt tuning on the same key.
Name the cause, turn exposed cases into regressions, make only an authorized
general fix, and use a fresh frozen key for any new release attempt.

## 17. Run the conditional three-world test only if triggered

If and only if the final fitness protocol classifies the result as red and its
frozen trigger calls for `S2`:

1. stop the release;
2. verify the already-frozen exact three-world protocol and call ceiling;
3. run it once on its locked inputs;
4. record the result without silently changing the catalog strategy;
5. return any required design change to its single owner;
6. rebuild and re-run every invalidated downstream gate on fresh evidence.

Do not run `S2` after a green result. Do not use an inconclusive result as an
automatic trigger unless the frozen protocol explicitly says so.

## 18. Complete accounting and reproducibility

One final manifest must hash or reference the existing hash owner for:

* code commit and tree;
* dependency and runtime versions;
* population and taxonomy;
* sources and chunks;
* prompts, schemas, model IDs, effort, and raw responses;
* menus, seeds, decisions, approvals, parks, and skips;
* leaf, sector, global, repair, and validation artifacts;
* `terminal_admissions.json`, `fact_type_decisions.json`, `families.json`,
  `fact_type_disagreements.json`, and the final catalog;
* every gate protocol, answer key, score, exhibit, and result;
* test identities and raw test outputs;
* read-only database evidence.

Programmatically reconcile:

```text
sources
→ chunks
→ model responses
→ candidates or zero-yield results
→ approvals, refusals, skips, or parks
→ catalog records and variants
→ final types and families
→ gate slots and results
```

Every row must have one destination. No count may be inferred from a summary
that omits parks or invalid responses.

## 19. Required tests

Run on the exact candidate:

* focused tests for each changed owner;
* the complete catalog-workflow suite;
* current-law prompt and model-pin checks;
* finalizer unit, integration, crash, and mutation tests;
* source-byte and chunk conservation tests;
* leaf, fold, repair, final-validation, and consumer-guard tests;
* lawful controls beside every rejection or park;
* boundary, hostile, permutation, and reordered-input tests;
* interrupted-run and exact-resume tests;
* replay determinism with frozen responses;
* the real calibration leaf and two-industry fold;
* the complete production-population accounting check;
* every frozen experiment and release gate;
* full repository regression;
* isolated zero-credential tests;
* exact test-identity reconciliation;
* 100% coverage of every new or changed behavior branch and exception outcome.

Use the existing coverage owner. Do not add a coverage framework solely to
produce a percentage.

No normal test may fetch sources, call a model, or write to Neo4j. Pre-authorized
live runs are separate, hash-bound evidence packages.

## 20. Database and side-effect proof

Before and after the exact final candidate:

* rerun the same read-only graph census;
* prove the run executed zero graph writes;
* prove Driver, DriverUpdate, DriverPeriod, relationship, constraint, and
  sentinel state did not change because of Step 7;
* prove old Guidance data and links are unchanged;
* prove the catalog cannot call the production writer;
* prove write-enable flags still fail before mutation;
* prove no Fiscal cursor or operating ledger advanced;
* account for every pre-authorized source fetch and every planned Sonnet 5
  high-effort model call.

The final catalog stays on disk as a frozen retrieval artifact. Do not bulk-
create name-only graph nodes.

## 21. Minimality audit

The finished catalog path must have:

* one source-population owner;
* one byte-preserving chunker;
* one leaf naming prompt contract;
* one normalization owner;
* one reconciliation law at every level;
* one deterministic assembler;
* one duplicate-repair path;
* one finalizer;
* one final validator;
* one model-role configuration;
* one final manifest;
* no active retired field or prompt;
* no lexical or embedding merge decision;
* no copied semantic vocabulary;
* no second type, family, or identity engine;
* no graph-write path;
* no unrelated refactor.

For every added function, branch, file, field, test helper, and artifact, state
the required failure it prevents. Delete it if an existing owner already
prevents that failure.

## 22. Documentation and blank-context check

Update only the live status and operative mechanics that actually changed.
Keep `STATUS_AND_HISTORY.md` as the status owner and update the generated status
mirror in `FINAL_DESIGN.md` without creating another dashboard.

Because this step adds operative mechanics and gates and is a major release
handoff, apply the standing R8 reader-test rule:

1. prepare the exact seven live files named by R8;
2. commit the code, catalog evidence, and status update locally;
3. run the existing ten-question blank-context check on that committed freeze;
4. require 10/10, 7/7 unchanged file hashes, and checked command exits;
5. add the append-only result record afterward without changing the tested
   seven files.

This AI-dependent check uses one independent Sonnet 5 high-effort call under
the master pre-authorization.

## 23. Commit and push sequence

Use separate reviewed commits for:

1. the owner-frozen eligible universe, selection rules, and runnable gate
   protocols;
2. current-law builder corrections and their tests;
3. the finalizer and its tests;
4. the final catalog, gate evidence, and truthful status update;
5. the append-only blank-context result record.

For each commit:

* stage only its reviewed paths;
* record the exact staged tree and path manifest;
* run its focused checks before commit;
* independently verify the staged bytes;
* obtain Codex `VERIFIED` on the exact staged identity;
* push normally, never with force or history rewrite;
* verify local main, origin/main, and the remote hash agree.

Do not commit raw source bytes or generated material merely because they exist.
Commit only artifacts required by the repository’s existing evidence policy;
hash every retained external artifact in the final manifest.

## Stop conditions

Stop if:

* any required earlier step is incomplete;
* the exact candidate or population is not frozen;
* the data-derived population query, eligibility fields, cutoff, or company
  lifecycle ruling is unresolved when population freeze begins;
* a gate lacks a reviewed runnable protocol;
* model identity, effort, key ownership, metric, or pass rule is unclear;
* a model call is unplanned or over its frozen ceiling, a source retrieval
  falls outside the master public-source ruling, a graph write lacks approval,
  or a commit/push violates the completed-step ruling;
* old rule-bearing output is used as current input or baseline;
* source bytes, chunks, candidates, decisions, or final rows do not reconcile;
* a model is asked to perform mechanical work code already owns;
* code is asked to decide meaning from a word, pattern, score, or threshold;
* a merge, rewrite, type, or family lacks its required approval evidence;
* a validator or hash check is bypassed;
* a wrong merge occurs;
* a required mutation survives;
* a fitness flag remains unresolved;
* the final fitness gate is red or inconclusive;
* an unrelated file overlaps the candidate;
* Neo4j, old Guidance, or a cursor changes;
* the blank-context check is not 10/10 with unchanged hashes.

## Completion condition

Step 7 is complete only when:

* the exact eligible universe, selected seed roster, held-out sets, and source
  snapshots are owner-frozen;
* every required protocol is owner-frozen before use;
* all current-law builder gaps are closed with the smallest changes;
* the one finalizer exists and every consumer refuses unfinished catalogs;
* the full multi-industry tree was built from complete, accounted source text;
* every leaf, fold, repair, type, family, skip, park, refusal, and zero-yield row
  is accounted for;
* the final catalog and every required side file are hash-bound;
* `S1`/`X-S1`, `S4`, `X0–X9`, `X-G`, `X-IM`, and `OD-6` are green;
* any legitimately triggered `S2` result is resolved and all invalidated gates
  were rerun;
* observed wrong accepted merges are zero and measured recall loss is fully
  reported;
* all focused, regression, isolation, identity, branch, and mutation checks
  pass on the exact candidate;
* the blank-context check passes;
* no catalog node or fact was written to Neo4j;
* the exact reviewed commits and remote identities match;
* no in-scope issue remains open.

After this, Step 8 may use real catalog candidates for the remaining fact,
enrichment, read, and verdict layers. Fiscal certification and operating-runbook
design may already be proceeding in parallel. Live graph activation still waits
for Steps 8, 9A, and 10 plus the separate Step 11 approval; Step 9B runs after
Step 11's first bounded lawful records and before any wider Fiscal rollout.
