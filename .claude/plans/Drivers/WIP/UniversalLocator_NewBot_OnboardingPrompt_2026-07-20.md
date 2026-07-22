> ⛔ **SUPERSEDED-FOR-EXECUTION (2026-07-21):** The locked `UniversalLocator_Design_2026-07-18.md` is the BASE contract; `UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md` is the SOLE current execution amendment/work order (Phase 0-7; Batch B/C/D FROZEN). Reading order: locked Design v5.5 base (unchanged rules) -> FinalPlan (changes + current steps) -> Review Record (history). This file is history/evidence only — follow no execution instruction in it.

# New Bot Full Driver/Core/Fiscal Onboarding Prompt

You are taking over the Driver project in `/home/faisal/EventMarketDB`.

Your first job is **not to code**. Your first job is to recover and independently verify the
complete project state so no decision, reason, file, test, or ownership boundary is lost.
Do not claim that you understand the project until you have completed every gate below.

## 1. Current owner instruction

Focus only on the Fiscal Universal Locator work for now. Core is paused.

Until the owner explicitly changes this instruction:

- do not edit Core files;
- do not ask Core to commit;
- do not run the paid R8 reader test;
- do not push;
- do not write to Neo4j;
- do not mix a Core review and a Fiscal review into one task;
- do not edit Fiscal code before completing the read-only onboarding and current corrective
  audit.

At the time this prompt was written:

```text
origin/main = 80bae52  (WP1 closed and pushed)
local HEAD  = 47b2ecf  (WP2 corrective, not independently accepted)
main is 12 commits ahead of origin/main
```

This state may have changed. Verify it from Git before relying on it.

## 2. Project goals

Keep these goals visible throughout the review:

1. Aim for 100% **measured** precision and 100% **measured** recall where the available
   evidence permits both.
2. Deterministic precision is the hard release priority. Never keep a questionable link just
   to make recall look larger.
3. Recover as much safe deterministic recall as possible before spending reader/LLM tokens.
4. Every abstention must remain visible for the later reader lane. Never silently lose work.
5. Normal operation must be automatic. No human decision is allowed in the normal item flow.
   Human approval is only for owner gates such as a certified-baseline loss, a law/design
   change, prompt/token spending, push, production activation, or a Neo4j write.
6. Use the smallest solution that completely handles the real requirement. No speculative
   framework, fuzzy matcher, abbreviation list, copied resolver, new registry, or machinery
   for hypothetical cases.
7. For behavior changes: reproduce RED first, make the smallest fix, then run focused and
   regression tests.
8. A green count alone is not proof. Read the production code and reproduce the exact case.
9. A graph-dependent claim requires an independent read-only Neo4j query. A synthetic test
   may supplement that query, but cannot replace it.
10. Explain findings to the owner in short, plain language.

Measured zero errors is a release gate, not a mathematical promise that no future input can
ever fail. Report denominators and remaining uncertainty honestly.

## 3. Authority and ownership

Use the newest owner instruction and live repository evidence. For project content, classify
each file before trusting it.

### Core owns

- the live law in `.claude/plans/Drivers/FinalDesign/`;
- `driver/core/`;
- the shared decomposer;
- final Driver identity;
- final fact period and units;
- kernel admission/reuse/create/park decisions;
- validation, storage, runtime, and the only eventual Neo4j write path;
- PER-21 and the paid R8 law certification.

Fiscal must not edit Core law or implement Core identity/storage responsibilities.

### Fiscal owns

- Universal Locator design, plans, and append-only review record;
- source recipes and Fiscal adapters;
- WP2 neutral locator and one-source routes;
- WP3 dry-run source loop for 10-Q/K, amendments, complete 8-K accessions, and Transcripts;
- WP4 reader request/result, prompt, certification, and token report;
- read-only graph work for these packages.

### Neutral code

`driver/relocation/` is channel-neutral. Fiscal is currently implementing it, but it must
import no Fiscal/channel code. Fiscal adapters may call the neutral locator; the neutral
locator may not call Fiscal adapters.

### Owner-only gates

Only the owner may approve:

- a locked law/design change;
- a certified baseline loss;
- paid reader/LLM tokens;
- commit/push when explicitly owner-gated;
- production activation;
- any Neo4j write.

## 4. Phase zero: freeze and inspect

Before reading conclusions or changing files:

1. Read `/home/faisal/EventMarketDB/AGENTS.md` completely.
2. Run and record:

```bash
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate origin/main..HEAD
```

3. Record every modified, deleted, and untracked path relevant to Driver work.
4. Treat all unrelated dirty files as another owner's work.
5. Never reset, restore, delete, stage, commit, or push another owner's changes.
6. Use exact path-scoped diffs and exact path staging if edits are later approved.

During onboarding/audit, do not stash, checkout/switch, rebase, amend, clean, reset, restore,
change branches, alter the index, or run a broad formatter. Do not use destructive Git
commands.

The following were protected untracked work at the snapshot and must not be overwritten,
staged, or removed:

```text
.claude/plans/Drivers/WIP/UniversalLocator_NewBot_OnboardingPrompt_2026-07-20.md
.claude/plans/Drivers/WIP/UniversalLocator_Codex_ReviewHandoff_2026-07-20.md
.claude/plans/Drivers/WIP/UniversalLocator_WP1_Plan_2026-07-18.md
driver/relocation/test_neutral_boundary.py
```

Recompute their status live; protection follows ownership, not merely untracked status.

## 5. Read every handoff and working authority

Read primary authorities before the non-authoritative handoff, in this order:

1. `AGENTS.md`
2. live Git state and current relevant diffs from Phase zero
3. `.claude/plans/Drivers/WIP/UniversalLocator_Design_2026-07-18.md`
4. `.claude/plans/Drivers/WIP/UniversalLocator_WP1_Plan_2026-07-18.md`
5. `.claude/plans/Drivers/WIP/UniversalLocator_WP2_Plan_2026-07-19.md`
6. `.claude/plans/Drivers/WIP/UniversalLocator_ReviewRecord_2026-07-18.md`
7. complete the full FinalDesign, Core-code, and Fiscal-code reads in Phases 6-8 below
8. `.claude/plans/Drivers/WIP/UniversalLocator_Codex_ReviewHandoff_2026-07-20.md`

Then inventory every other file directly under `.claude/plans/Drivers/WIP/`. Read each one
whose subject touches Driver identity, graph schema, Core/Fiscal boundaries, source
relocation, reader certification, or incremental refresh. Classify each as current,
supporting, historical, superseded, or unrelated. Do not silently skip a file because its
name looks old.

The Codex handoff is non-authoritative. If it conflicts with current law, locked Fiscal
design, the approved WP2 plan, the append-only review record, committed code/tests, or fresh
evidence, report the conflict and follow the actual authority.

Use the handoff last as a claims/checklist audit against what you independently learned, not
as the source from which you derive conclusions.

## 6. Read all of `FinalDesign`, without exception

Recursively inventory and read **every file** under:

```text
.claude/plans/Drivers/FinalDesign/
```

At the time this prompt was written there were 62 files: 9 at the top level and 53 in the
archive. Do not trust that count; compute the live count yourself.

The top-level files observed were:

```text
15_CandidateFactPacket.md
BUILD_AND_OPERATIONS.md
ChannelContract.md
FINAL_DESIGN.md
FableExperimentPlan.md
FableExperimentWorkOrder.md
NewsChannel.md
ReasoningTraceQuestions.md
STATUS_AND_HISTORY.md
```

`NewsChannel.md` and `ReasoningTraceQuestions.md` were untracked work from other sessions at
the snapshot. Read and classify them, but do not edit, stage, or treat them as locked law
without evidence.

Read all archive files too, including the manifest, consolidation record, supersession files,
decision audit, old component designs, and every reader-test record. The archive is evidence
and history, not current authority. Your job is to understand:

- what each old rule meant;
- why it was accepted, reversed, or superseded;
- where the surviving rule now lives;
- whether any current file accidentally contradicts the history or current law.

Build a complete FinalDesign coverage table with one row per file found, including every
archive file:

```text
path | SHA-256 | line count | live/working/archive | owner | purpose |
authority level | key rules/decisions | superseded by | conflicts/gaps
```

Do not say "all FinalDesign files read" unless the table has one row for every recursive path
and the row count equals the recursive file count.

## 7. Understand every Core-authored code and test file

Use Git, not memory, to create the exact inventory:

```bash
git ls-files driver/core
git ls-files .claude/plans/Drivers/workflows
git ls-files .claude/plans/Drivers/test_driver_design_coverage.py
git ls-files .claude/plans/Drivers/DriverDesign.html
git log --reverse --name-status -- \
  driver/core \
  .claude/plans/Drivers/workflows \
  .claude/plans/Drivers/test_driver_design_coverage.py \
  .claude/plans/Drivers/DriverDesign.html
```

At the snapshot there were 27 tracked files under `driver/core/` and 37 tracked workflow,
workflow-test, coverage, and study-page files. Recompute the live numbers.

For completeness, union the tracked inventory with relevant modified/untracked filesystem
paths from `git status --porcelain=v1 --untracked-files=all` and a direct filesystem listing.
Create one sorted Core required-path manifest and one sorted Core read-ledger. Their set
difference must be empty before you claim complete Core coverage.

Also search Git history for Core-authored Driver code/tests outside those roots. Read the
external law/substrate and production helpers that Core actually imports:

```text
driver/README.md
.claude/plans/Drivers/HierarchicalCatalogPlan.md
.claude/plans/Drivers/Consolidation/GuidancePeriod.md
.claude/plans/Drivers/Consolidation/UnitExtraction.md
.claude/plans/Drivers/Consolidation/XBRL_SliceAxis_Catalog.md
.claude/skills/earnings-orchestrator/scripts/fiscal_math.py
.claude/skills/earnings-orchestrator/scripts/guidance_ids.py
```

Verify the helper paths from the current `sys.path`/self-location code; do not assume the
paths above are still the runtime paths.

Read every human-authored tracked source and test file returned by those commands. Follow
internal imports and callers until you can explain the full path:

```text
source/channel packet
  -> decomposer/prepared fact
  -> identity, slice, period and unit resolution
  -> validation
  -> admission/reuse/create/park
  -> writer/Neo4j adapter
```

For each Core file, record:

```text
path | commit provenance | purpose | public entry points | callers | callees |
inputs | outputs | reads/writes | governing law | tests | current status/gaps
```

Do not infer that code is production-ready merely because it exists. Distinguish:

- certified behavior;
- experimental workflow code;
- read-only adapter behavior;
- opt-in write probes;
- future work named in law but not implemented.

Reconcile code with the live FinalDesign law line by line where they overlap.

## 8. Understand every Fiscal and neutral locator code/test file

Derive the touched inventory from Git:

```bash
git log --reverse --name-status ba0c629..HEAD -- \
  driver/relocation \
  scripts/driver_seed \
  scripts/earnings \
  .claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py \
  data/driver_catalog_seed/wp1_evidence
```

Union this history-derived list with relevant modified/untracked filesystem paths from Git
status and a direct filesystem listing. Create one sorted Fiscal/neutral required-path
manifest and one sorted read-ledger. Their set difference must be empty before you claim
complete Fiscal coverage. Classify but do not overwrite unrelated untracked Fiscal-area
files.

Read every human-authored source/test file changed in that history. At the snapshot the
relevant set included:

```text
.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py
data/driver_catalog_seed/wp1_evidence/aci_queries.py
data/driver_catalog_seed/wp1_evidence/census_dimension_addresses.py
driver/relocation/exact_numbers.py
driver/relocation/locator.py
driver/relocation/test_anchor_schema_probe.py
driver/relocation/test_exact_numbers.py
driver/relocation/test_match_facts.py
scripts/driver_seed/build_packets.py
scripts/driver_seed/country_names.py
scripts/driver_seed/link_lib.py
scripts/driver_seed/locate.py
scripts/driver_seed/relocate_probe/STATE.md
scripts/driver_seed/relocate_probe/test_xbrl_gate.py
scripts/driver_seed/relocate_probe/xbrl_gate_expected.json
scripts/driver_seed/relocate_probe/xbrl_lane.py
scripts/driver_seed/run_code_tier.py
scripts/driver_seed/test_build_packets.py
scripts/driver_seed/test_exactness.py
scripts/driver_seed/test_locate.py
scripts/driver_seed/test_run_code_tier.py
scripts/driver_seed/test_wp1_verify.py
scripts/driver_seed/wp1_verify.py
scripts/earnings/test_get_quarterly_filings.py
```

Also read these required authorities even if the current diff did not touch them:

```text
scripts/earnings/quarter_identity.py
driver/relocation/test_neutral_boundary.py
```

The second file was an intentional untracked RED boundary test at the snapshot. Verify its
current state before interpreting it.

Read the committed evidence outputs and fixtures that the tests or manifests use. Do not
read thousands of unrelated generated outputs, caches, `__pycache__`, compiled files,
third-party data, or raw datasets merely to inflate coverage. Read a generated artifact when
it is part of a proof, fixture, hash manifest, or production input.

Follow every internal import and production caller used by the files above. Read those
dependencies too, even if Git says another commit originally created them.

Read the relevant commits and diffs in order, not only the final files. For each behavioral
change, connect the RED reproduction, smallest fix, evidence, regression gate, later
correction, and current surviving rule. A commit message or review-record claim is a lead to
verify, not proof.

For each Fiscal/neutral file, record:

```text
path | commit provenance | WP1/WP2/WP3/WP4 role | entry points | callers | callees |
inputs | outputs | graph/network/file side effects | governing design rule |
tests/fixtures | certified baseline | known gaps
```

Trace and explain these paths from actual code:

```text
WP1:
committed worklist -> run_code_tier -> locate_by_value -> source-proven record/residual/abstain

WP2 fingerprint:
stored Driver/fact -> rebuild_anchor -> locate_by_fingerprint ->
xbrl_lane adapter -> driver/relocation neutral matcher

Source routing:
historical 8-K -> get_quarterly_filings matcher + quarter_identity AUTO_OK trust only
live 8-K       -> quarter_identity only
```

Confirm from code that a failed historical match parks and never falls through to the live
resolver.

Confirm that `get_earnings_with_10q()` is only a display formatter and is not a third source
matcher.

## 9. Build a decision-and-reason ledger

Do not memorize rules without their reasons. Create a ledger with:

```text
decision | owner/date/source | reason/evidence | implementation | tests |
current/superseded | reopen condition
```

At minimum, recover and explain:

1. Why historical and live 8-K routing use different authorities.
2. Why `get_quarterly_filings.py` and `quarter_identity.py` are the only two authorities.
3. Why fiscal labels, projected dates, and a third matcher are forbidden.
4. Why a failed historical pairing parks instead of trying the live resolver.
5. Why the locator anchor is period-free.
6. Why prior XBRL pairs are never placed in the anchor or reused, even as hints; every target
   source proves complete pairs anew. Only source wording and the sole active
   ConceptResolution's prior stored concept identifier may guide retrieval.
7. Why concept identity is the exact identifier as stored: full qname when present, otherwise
   bare local name, never promoted.
8. Why complete `(axis, member)` pairs, exact period/time shape, and exact raw unit identity
   are all required.
9. Why different surviving identities abstain and alphabetical tie-breaking is forbidden.
10. Why quote/value proof must come from the same source occurrence.
11. Why a text-only 8-K carries no fake empty XBRL dimension address.
12. Why 8-K and Transcript evidence can gain XBRL identity only through safe chaining to the
    paired 10-Q/K.
13. Why precision holes abstain to the reader instead of being guessed.
14. Why country/acronym handling is closed and evidence-based, not a fuzzy vocabulary system.
15. Why financial/non-financial Driver classification is not stored yet and must be revisited
    before the first production Driver only if a real consumer and testable definition exist.
16. Why Core alone owns final period, units, Driver identity, storage, and graph writes.
17. Why normal execution has no human in the loop but owner release gates still exist.
18. Why full regeneration is not run after every small edit.

The list above is a minimum for the Fiscal/Core boundary, not complete Core decision
coverage. For Core, ledger every `Q1-Q5` and `R6-R13` ruling, all 43 supersession rows, and
every `FINAL`, `BUILD-PENDING`, `CONDITIONAL`, `OPEN`, `DORMANT`, and `OFF` item. Recompute
the counts from the live files. Do not let the current coverage test's narrower pattern turn
missing decisions into a false complete report.

If two sources disagree, do not choose silently. Name the conflict, identify the authority,
and show why one statement is stale or superseded.

## 10. Build the test and evidence map

For every important behavior, identify:

```text
law/claim | focused test | integration/live test | fixture/evidence | baseline | failure action
```

Verify that tests are actually collected. A test inside a `__main__` block is not a pytest
test unless a collected wrapper runs it.

Check test counts before and after any future test-file edit. Prior rounds accidentally
deleted tests while still reporting a smaller green battery.

Do not rerun an expensive regeneration during onboarding. First understand:

- the focused matcher/dispatch tests;
- the durable 150-case XBRL gate;
- the full Fiscal battery command;
- the 28 certified floors;
- the WP1 clean-worktree byte proof;
- the Core coverage/sync tests;
- the Core unit and live read-only tests;
- the R8 reader-test procedure and its owner-approved token cost.

For graph evidence, keep all queries read-only. Neo4j writes require explicit owner approval.

## 11. Current state you must verify, not assume

### Fiscal

- WP1 is closed and pushed at `80bae52`.
- WP2 Step 1, anchor rebuilding, is closed.
- WP2 Step 2 is in progress.
- `47b2ecf` is the current corrective commit at this snapshot, but is not independently
  accepted.
- The first active task is a findings-first audit of `814a15a..47b2ecf`.
- Do not build routes, move quote helpers, regenerate, or push during that audit.

Known audit focus:

1. Exact raw unit identity must outrank the broad money/non-money guess.
2. Reproduce the opaque `Unit12` case. An exact target-local ID must not be vetoed because
   its spelling lacks `usd`.
3. Verify the real PSEG/EOG case-sensitive compound-unit collision with a durable read-only
   query and focused test.
4. Prove every one of the prior 130 correct rows survived by stable
   `(pair_key, target.fact_id)`, not only by aggregate counts.
5. Verify each pinned target's exact Fact, accession, one nonblank raw unit ID, exactly one
   Unit edge, and matching semantic unit/divide data.
6. Verify pair forwarding, neither/both address rejection, malformed/repeated pair handling,
   malformed period handling, and exact abstention reasons.
7. Round-trip a valid fingerprint request through `json.dumps`/`json.loads`. Complete pair
   arrays must still validate and canonicalize internally; reject malformed content, not
   JSON's normal list representation.
8. Confirm the 19 `concept_missing` plus 1 `no_source_xbrl` split.
9. Confirm no test deletion, stale statement, route work, quote move, regeneration, Core edit,
   graph write, or push entered the corrective.

One suspicious production ordering was already observed in
`driver/relocation/locator.py`: the money/non-money heuristic appears to run before the exact
`unit_ref` equality check. Reproduce the behavior directly; do not accept or reject it from
this prompt alone.

If the corrective is accepted, the remaining planned flow is:

```text
quote-proof helper move, if still required
  -> R1/R2 neutral routes
  -> real-call boundary test green
  -> one final WP1 byte comparison if the final diff reaches WP1
  -> real 10-Q/K positive, real text-only 8-K positive, honest negative
  -> R1 all-period/dedupe/ambiguity/same-source-evidence gate
  -> R2 source-stamped-hint/no-prior-value-reuse gate
  -> transcript-shaped neutral fixture, without fetching or tokens
  -> census-only B2B/SaaS and EMEA/NAA acronym report, no list or matcher code
  -> WP2 gate
  -> WP3 source loop, including Transcript integration
  -> WP4 reader and token certification
```

The R1 all-period pin must cover quarter, YTD, FY, instant, and comparative facts; deduplicate
identical results; abstain on genuine ambiguity; and emit the quote/raw label from the same
current source. R2 hints must be stamped with the current `source_id`; a mismatch is rejected,
and no prior factual value is ever reused.

WP2 may use a transcript-shaped neutral payload fixture, but real Transcript-node fetching
and integration belongs to WP3. WP3 must also measure safe indirect XBRL chaining for
text-only 8-K and Transcript evidence through the paired 10-Q/K; it must not assume every
such source needs reader tokens.

### Core

Core is paused by owner instruction. Do not change it during the Fiscal audit.

The current dirty Core law work is not commit-ready merely because its tests are green. The
handoff records known gaps that must be rechecked later:

- the coverage test pattern is limited to `Q[1-5]|R[6-8]`, so it is blind to R9-R13;
- the study page does not properly cover R9-R13;
- the study-page footer says 71 rule IDs / 42 reversals / 8 rulings, while the live expected
  counts are 72 rule IDs / 43 supersession rows / 13 rulings;
- STATUS/BUILD say Track A 265+1, while the fresh suite is 266+1;
- the "R8 has not run" wording must become snapshot-stable;
- the PER-21 sync test is too weak;
- the paid R8 questions must explicitly test historical routing, live routing, failure
  parking/no fallback, and separation of source routing from fact-period resolution.

The seven tracked dirty Core paths at the snapshot are:

```text
.claude/plans/Drivers/DriverDesign.html
.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md
.claude/plans/Drivers/FinalDesign/ChannelContract.md
.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md
.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md
.claude/plans/Drivers/test_driver_design_coverage.py
.claude/plans/Drivers/workflows/tests/test_rulebook_sync.py
```

The untracked `FinalDesign/NewsChannel.md` and `FinalDesign/ReasoningTraceQuestions.md` are
other-session work. Never stage them with Core. Because the 12 unfinished Fiscal commits are
already below any future Core commit on local `main`, any push would publish those Fiscal
commits too. Use surgical path staging later and never push without the owner's word.

Fresh Core evidence at the snapshot was:

```text
coverage + sync: 15 passed
Track A workflows: 266 passed, 1 skipped
driver/core: 392 unit passed + 10 live read-only passed + 1 opt-in write probe skipped
```

This green state does not erase the coverage defects above.

Core's PER-21 law work and paid R8 are a later owner-gated task. R8 is estimated at
250k-400k reader tokens; the comparable prior run used 236,676. Do not spend those tokens
without the owner's explicit approval.

When the owner resumes Core, the required R8 sequence is:

1. Fix the coverage, study-page, count, status, and PER-21 test gaps.
2. Choose the future unique append-only R8 record name and make pre-R8 status text
   record-driven before freezing the tested snapshot.
3. Pin these seven files:
   `FINAL_DESIGN.md`, `ChannelContract.md`, `BUILD_AND_OPERATIONS.md`,
   `STATUS_AND_HISTORY.md`, `15_CandidateFactPacket.md`, `FableExperimentPlan.md`, and
   `FableExperimentWorkOrder.md`.
4. Commit the final law and guards.
5. Obtain owner approval for the 250k-400k reader-token spend.
6. Run from a clean detached worktree at the final certification SHA.
7. Record all seven hashes before and after; run the exact battery with checked exit status.
8. Use the first answer from one fresh blank-context reader and require 10/10, including
   historical routing, live routing, PARK/no live fallback, and source-routing versus
   fact-period separation.
9. Add the unique append-only R8 record in a later commit; change none of the seven certified
   files.
10. Push only on the owner's explicit word.

The old ten reader questions do not explicitly certify PER-21 and cannot be reused unchanged.

No production Driver graph is active. The CLI remains dry-run, `ENABLE_DRIVER_WRITES` is off,
adapter writes must raise, and the opt-in numeric write probe must not run without explicit
owner approval.

PER-21 cleanup/R8 is technically independent of finishing WP2/WP3; the owner paused it now
only to keep attention on Fiscal. Broad Core S4 implementation does wait for stable real
Fiscal WP3 packets. Core eventually owns the shared decomposer, kernel, final
identity/period/unit decision, writer, and production activation.

## 12. Required onboarding report

Before any code or document edit, return one report with these sections:

1. **Git state**
   - exact HEAD, origin/main, ahead/behind count, relevant local commits, and dirty paths;
   - separate Driver/Core/Fiscal changes from unrelated work.

2. **Handoff coverage**
   - every required handoff/plan/review file read;
   - SHA-256 and line count for each;
   - current authority versus historical/supporting status.

3. **FinalDesign coverage**
   - recursive live file count;
   - one row for every file;
   - current law versus archive/history;
   - contradictions, stale text, and missing coverage.

4. **Core code coverage**
   - every required Core/workflow/test file;
   - call graph, responsibilities, side effects, tests, and unfinished pieces.

5. **Fiscal code coverage**
   - every required Fiscal/neutral source, test, fixture, and proof artifact;
   - WP and route ownership;
   - call graph, side effects, tests, baselines, and known gaps.

6. **Decision ledger**
   - the important decision;
   - why it was made;
   - where it lives;
   - how it is tested;
   - whether it is current or superseded.

7. **Responsibility map**
   - Core;
   - Fiscal;
   - neutral code;
   - owner-only gates.

8. **Current work status**
   - what is complete;
   - what is in progress;
   - what is paused;
   - the exact next task and why.

9. **Current Fiscal corrective findings**
   - findings first, ordered by severity, with file/line references;
   - independent reproductions and read-only graph evidence;
   - remaining test or evidence gaps;
   - no fixes unless the owner separately asks.

10. **Completeness statement**
    - state the exact number of required files inventoried and read in each group;
    - show that `required inventory - read ledger` and `read ledger - required inventory` are
      both empty for FinalDesign, Core, and Fiscal/neutral groups;
    - list any unread file and why;
    - do not say "complete understanding" if even one required file remains unread.

Keep the owner-facing summary short and plain first. Put the detailed coverage tables after
the short verdict.

## 13. Hard stop rules

Stop and report instead of acting if:

- a required file cannot be read;
- a live authority conflicts with another live authority;
- a claimed graph fact cannot be reproduced read-only;
- any of the 130 certified correct cases is lost;
- a certified floor would drop;
- a change would alter locked behavior beyond a reproduced defect;
- a task crosses from Fiscal into Core responsibility;
- a prompt/token spend, push, production activation, or Neo4j write is needed;
- another session's dirty work makes the intended change unsafe.

Do not solve a scope conflict by adding a new layer. Ask one specific owner question and
recommend the smallest safe choice.

## 14. Completeness discipline

You may use subagents to inventory independent file groups, but the lead bot must:

- inspect their evidence;
- personally read all critical authority and production-path files;
- reconcile their inventories;
- verify hashes and counts;
- remain responsible for the final conclusions.

If the reading does not fit in one context window:

- work in batches;
- maintain an explicit path checklist;
- do not restart from memory after compaction;
- resume from the last verified path;
- never turn partial coverage into a claim of completeness.

Your onboarding is done only when the coverage report proves that every required file was
read and understood and the current Fiscal corrective has an independent findings-first
verdict.
