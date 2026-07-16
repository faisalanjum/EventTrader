# FinalDesign Consolidation Audit and Plan

## 0. Task restatement and short answer

Read every plan file, identify the latest effective rule without changing its meaning, retain only what a new bot needs, and propose a small one-copy final document set plus a lossless archive plan. Change nothing except this audit file.

This audit covers all **33 source files other than this audit** in the folder: 11,320 lines and 1,362,208 bytes at the Phase-1 freeze, including the HTML file and the three untracked source files. *(Status sentence updated round 11: the original "all 33 hashes still match / nothing changed" claim described the pre-ruling state. Since then, by owner decision: TWO sources carry owner amendments — `ChannelContract.md` and `15_CandidateFactPacket.md`, Q4 + Q1-ext, post-amendment hashes in the §16 freeze; the pre-amendment baselines stay pinned in the Phase-1 manifest. Everything else remains byte-identical to the baseline. The four target files now EXIST and passed the §14.1-14.3 checks through round 10 — the front door for the design is now `FINAL_DESIGN.md`; this audit remains the migration map and decision record.)*

The folder contains one coherent design, but it is spread across final rules, build manuals, later owner amendments, stale summaries, experiment instructions, proposals, and retired history. The clean end state should be **four live files**, with one rule written in one place and all current source files preserved byte-for-byte in a dated archive. The frozen packet remains a temporary fifth file until its byte-identical relocation is explicitly approved and proved.

```text
FINAL_DESIGN.md               what the system means and must do
        |
        +-- ChannelContract.md       what every source channel may submit
        +-- BUILD_AND_OPERATIONS.md  how to build, test, run, and retire it
        +-- STATUS_AND_HISTORY.md    what is open, conditional, replaced, or archived
```

This file is an audit and migration plan only. It does **not** carry new Driver design authority.

**Role, stated exactly (updated round 13):** this file is the MAP, the PLAN, and the DECISION TRAIL. *(The original sentence "until the four target files exist, the 33 source files remain the rule authority" is OBSOLETE: the four target files exist and passed the §14.1-14.3 checks — the rule authority is now `FINAL_DESIGN.md` (front door) with `ChannelContract.md`/`BUILD_AND_OPERATIONS.md`/`STATUS_AND_HISTORY.md`; the 33 sources are the byte EVIDENCE baseline until Phase 5 archives them, plus the four live pending-decision files.)* A new bot today starts at `FINAL_DESIGN.md`, not here.

> **Fast path for a new bot:** read section 3 for authority, sections 4-5 for the design and contracts, section 6 for build rules, sections 7/9/10 for current status and blockers, and sections 12-15 for consolidation. Sections 8 and 11 are proof maps needed mainly during migration.

## 1. Requirements I followed

1. Read every file in `.claude/plans/Drivers/FinalDesign/` and record every rule, design choice, status, dependency, and replacement.
2. Treat a newer date as evidence of recency, not authority. A newer file wins only when it contains an explicit owner approval, active-contract statement, or replacement instruction.
3. Keep final rules separate from build status, open choices, candidate designs, evidence, and retired history.
4. Do not resolve unclear points by inventing a decision. Raise them for the owner.
5. Propose the smallest clear document set that keeps one copy of each live rule.
6. Archive old material only after a rule-by-rule and hash-by-hash proof that nothing was lost.
7. Change only `CONSOLIDATION.md` in this pass.

## 2. Status words for the consolidated files

These labels describe existing plan status; they do not add policy.

| Label | Plain meaning |
|---|---|
| **FINAL** | Explicitly locked, agreed, owner-approved, or frozen and not later replaced. |
| **FINAL / BUILD-PENDING** | The rule is final, but its code, wiring, full run, or proof is not complete. |
| **CONDITIONAL** | Approved only after a named gate passes, or approved in principle with operating details still gated. |
| **OPEN** | The plan deliberately leaves a choice unresolved. |
| **CANDIDATE** | A detailed proposal or lock candidate that still needs owner approval. |
| **EVIDENCE** | Test results, counts, rejected alternatives, or rationale; useful but not a rule. |
| **HISTORY** | A record of an old decision; never current authority. |
| **RETIRED** | Explicitly replaced and forbidden as a production path. |

Every rule in the final files should carry one of these labels. Phrases such as “ready,” “complete,” and “final” must always say whether they mean **design**, **code**, **test**, or **production run**.

### 2.1 Small glossary for overloaded terms

- **Catalog G1/G2:** G1 is the live reuse display; G2 is the final catalog admission gate. These are not the XBRL concept linker's G0/G1/G2 exclusion guards. Always qualify the name.
- **Menu:** a context-specific candidate list, such as a slice menu, concept menu, or live reuse view. It is not the whole catalog.
- **Slice:** the reporting company's own measured business population inside fact scope. It is not a Track A batch or fold partition.
- **Seed:** an evidence-backed catalog candidate artifact. It is not yet a graph Driver.
- **Fold:** combine child catalogs under the same reconcile law used elsewhere.
- **Head:** the current canonical representative in a reversible `SAME_AS` set.
- **Created:** the DriverUpdate write time. Public time and `event_time` mean the source release time.
- **Parked:** a retryable item that core cannot safely write yet.
- **Fail closed:** do not create, attach, merge, or write when required proof is missing.
- **Source:** the graph Event, Report, Transcript, or News node that owns the quote.
- **Archive:** a byte-preserved, non-authoritative historical snapshot.

## 3. Authority and time map

### 3.1 How authority is decided

Use this order when two statements differ:

1. The latest explicit owner approval, explicit reversal, signed execution decision for its governed slot, frozen contract, or active contract wins for its exact subject.
2. `95_Supersession.md` proves its “was” side is dead. Its “now” side applies even where an older topic file was not updated, unless a later item in step 1 supersedes it; any condition or gate stated in the row remains binding.
3. The current part of `66_IssuesToBeHandled.md` supplies owner-approved OD overlays and missing back-port details. Its older tail does not.
4. The topic file owns naming, scope, units, periods, families, fact fields, concept links, build, or retirement only after the overlays in steps 1-3 are applied.
5. Build manuals own build steps, but “build-ready” never means “implemented” or “run.”
6. `90_OpenItems.md` is the thin status list, subject to newer frozen contracts and signed experiment results.
7. Candidate designs, experiment plans, and work orders do not amend production rules unless an owner decision says they do.
8. Context packs, prompts, the HTML deck, and `99_Codex_Decision_Audit.md` are navigation, instructions, study aids, or history. They never beat a topic rule.
9. A timestamp alone never settles a conflict.

### 3.2 Important dates

| Date | What changed | Authority effect |
|---|---|---|
| 2026-07-02 | Original numbered design and audit set | Baseline only; many later amendments apply. |
| 2026-07-03 | Field contract, concept linking, Track B decisions | Current where not later amended. |
| 2026-07-04 | Track C v2.0 | Explicitly retires the old Guidance replay design. |
| 2026-07-05 to 2026-07-06 | OD-1/2/3/4/6/8/9-15 and reversals | These owner-approved OD rules override stale wording. OD-5, the broader OD-7 live-admission design, and OD-16 are tracked work/recommendations, not final owner rules; OD-2's narrower first-fact pin remains approved. |
| 2026-07-07 | Admission kernel v3.4 | Detailed lock candidate; only named owner-approved parts are final. |
| 2026-07-08 to 2026-07-09 | XBRL candidate, experiment plan/work order, Bayes proposal | Candidate, execution, or proposal material; not automatic production law. |
| 2026-07-09 | Signed EXP-1 result | XBRL experiment passed; it does not itself ratify the whole XBRL design. |
| 2026-07-10 | Signed EXP-0 result | Grader pair passed and was ratified. |
| 2026-07-11 | OD-17 through OD-20; signed EXP-2 | Portion, recovery, token-subset, and continuity rules added; reader choice passed. |
| 2026-07-13 | Driver Genesis discussion | Rationale only; no owner lock. |
| 2026-07-14 | OD-21 and Candidate Fact Packet v1.0 | Owner-approved surprise extension and frozen core packet. |
| 2026-07-15 | OD-21 correction and active Channel Contract | Latest tracked correction plus newest active input boundary. |

The latest tracked commit touching this folder is `36e0610` on 2026-07-15: the OD-21 correction. `15_CandidateFactPacket.md`, `ChannelContract.md`, and `DriverGenesisRestructure.md` are untracked additions. Authority comes from their declarations, not their modification times: the first is owner-frozen, the second is active/owner-directed, and Driver Genesis is earlier unapproved deliberation.

### 3.3 Effective source map

| Subject | Current owner | Important overlay |
|---|---|---|
| Mission and safety law | `01_Overview.md` | Later files repeat but do not replace it. |
| Driver names | `02_DriverCatalog.md` | OD-12 and OD-17; reversals 38 and 40. |
| Fact identity, slices, measurement, continuity | `03_Slices_FactScope.md` | OD-8 overrides FS-03; reversal 27 removes alias wording; OD-21 adds surprise. |
| Units | `04_Units.md` | Reversal 26 replaces UNIT-04 with per-slot hints. |
| Periods | `05_Periods.md` | OD-21 changes guidance-vs-consensus period meaning. |
| Fact families | `06_MetricFamily.md` | OD-1 and OD-2 strengthen final admission. |
| Fact lanes, states, verdict | `07_DriverUpdate.md` | `09` replaces DU-13 through DU-18; frozen packet/channel replace old creator wording. |
| Concept linking | `08_XBRL_ConceptLinking.md` | XBRL-native materializer remains a separate candidate. |
| Stored fields and read rules | `09_DriverUpdate_Fields.md` | OD-9 through OD-14 and OD-21 are effective. |
| Catalog build | `10_BuildPipeline.md` | OD-1, OD-2, and OD-6 are not fully back-ported. Signed EXP-2 changes the reader status. OD-8 belongs to DriverUpdate collision handling, not this Track A back-port list. |
| Track B rule census | `11_TrackB_DriverUpdate_Census.md` | OD-8 collision text and public producer boundary need correction. |
| Track B build | `12_TrackB_FactPipeline.md` | Channel contract replaces its public FACT-17b boundary; internal contract survives. |
| Old Guidance retirement | active `13_TrackC_GuidanceIntegration.md` | Entire retired `13_Track_RetiredDesign.md` is history only. |
| Shared candidate packet | `15_CandidateFactPacket.md` | Frozen v1.0, owner-approved; OD-21 applied. |
| Public source-channel input | `ChannelContract.md` | Active, owner-directed; newest boundary. |
| Open/status/history | `90`, `95`, current `66` | Stale rows must be corrected from topic files and signed artifacts. |

### 3.4 External boundaries and known stale sources

FinalDesign is the rule layer over existing code and external implementation material named by the build manuals. HCP means `.claude/plans/Drivers/HierarchicalCatalogPlan.md`, which supplies catalog-engine mechanics not replaced by Track A. The Consolidation substrate is `.claude/plans/Drivers/Consolidation/`, especially `.claude/plans/Drivers/Consolidation/GuidancePeriod.md` for the 21 period tests, `.claude/plans/Drivers/Consolidation/UnitExtraction.md` for the shared unit resolver, and `.claude/plans/Drivers/Consolidation/XBRL_SliceAxis_Catalog.md` for the frozen axis table. Track B also points to existing code by exact path/line. The four final files should retain those precise reuse pointers without copying the external documents or turning them into extra Driver-rule authorities. One load-bearing trap rides with the `UnitExtraction.md` pointer: its embedded NAMING block still shows `taco_bell_same_store_sales` (Rule 0) and `adjusted_eps` (Example 7) — both REVERSED rules (`95` #1/#2). Copy only its per-X Rules 2-6/8 into any prompt; never its naming examples.

Never recover a current Driver rule from these older outside sources: `.claude/plans/Drivers/Drivers.md`, `.claude/plans/Drivers/DriverOntology.md`, `.claude/plans/Drivers/INDEX.md` section 3b, `.claude/plans/Drivers/WIP/unit_probe/RESULTS.md`, `.claude/plans/Drivers/WIP/DriverGraphSchema.md` lines 331/333, or the older `.claude/plans/Drivers/archive/` tree. They may explain history only. The explicit FinalDesign authority order above wins.

## 4. The final design, in one coherent order

This section maps the accepted rules. It is not a rewrite of their meaning.

### 4.1 Goal and safety law

- A **Driver** is one reusable, atomic cause or standing thing that can matter to a company or market.
- A **DriverUpdate** is one real, source-backed occurrence of that Driver in one event.
- A source quote is required for every fact. A mention without a fact is dropped.
- The catalog must reuse the same name for the same cause across companies and time.
- True duplicates stay recoverable through reversible `SAME_AS`; nodes and facts are not deleted or re-keyed to make history look cleaner.
- The intended loop is: extract facts, attribute price moves, learn which Drivers matter, predict, and trade.
- The safety law is asymmetric: **merging different meanings causes permanent damage; keeping the same meaning separate is repairable. When unsure, keep separate.**
- Meaning judgments belong to a capable model. Structure, normalization, identity, validation, and hard safety checks belong to code.
- Work is point-in-time: a historical run may see only information public before its cutoff.
- Runtime should not depend on a human. One-time owner approval and one-time frozen list review are design/bootstrap steps, not runtime review queues.
- Use the smallest machinery that meets these rules. Missing links are safer than wrong links.

### 4.2 Graph and flow

```text
source channel
   -> raw event packet
   -> shared decomposer
   -> admission/reuse decision
   -> Driver class + first admitted DriverUpdate, or attach/park/skip/reject
   -> deterministic writer and enrichment
   -> point-in-time raw/reconciled readers

Event/Report/Transcript/News -> DriverUpdate -> Driver
                                |             |-- SAME_AS -> Driver
                                |             `-- BASE_METRIC -> Driver
                                |-- DriverPeriod
                                |-- XBRL Concept / Member
                                `-- optional EXPLAINED_BY verdict from Event or DCM
```

The source channel never creates graph identity. The shared core does. This replaces older “producer creates the fact” wording without changing storage law.

### 4.3 Driver naming: NAME-01 through NAME-19

1. **NAME-01:** The name contains the cause only. Event state, direction, size, time, company, unit, and quote live elsewhere.
2. **NAME-02:** One stored name has one meaning. Spelling, order, acronym, and plural variants reuse the canonical name. Do not store an alias list. True later duplicates may receive reversible `SAME_AS`.
3. **NAME-03:** Vocabulary is open and source-born. A closed vocabulary was tested and rejected.
4. **NAME-04:** Use all specificity supported by evidence. Do not invent a broader class to force reuse.
5. **NAME-05:** Format is lowercase ASCII letters, digits, and underscores; start with a letter; at least two characters; no trailing or doubled underscore.
6. **NAME-06:** Order is thing or actor, then detail, then metric. Use singular count nouns by default. Keep standard plural financial terms and any plural whose meaning differs. Do not alter a locked phrase.
7. **NAME-07:** Use the familiar form only when the source does not state a meaningful sibling or benchmark. A stated specific instrument wins over the familiar broad name.
8. **NAME-08:** Keep standard financial phrases whole. Loss, deficit, and negative margin are negative regions of signed `net_income`, `operating_margin`, `eps`, and similar Drivers; do not create duplicate loss Drivers.
9. **NAME-09:** One name carries one cause. Split independent causes. Keep the result short and noun-like.
10. **NAME-10:** A reporting company's own measured segment, product, geography, customer group, sales channel, or owned entity goes to the slice, not the Driver name.
11. **NAME-11:** Apply the local role test. Strip generic direction/effect words. An own measured part becomes a slice. An external actor, object, platform, policy, event, or product causing the outcome stays in the name. If the role is unclear, or stripping leaves a vague fragment, keep it in the name. A customer is a slice only when it is the reporting company's own customer population. There is no vendor slice kind.
12. **OD-17 portion rule:** `current`, `funded`, `fee_earning`, and similar population qualifiers stay in the Driver name and differ from the bare Driver. Omit the slice only for the true consolidated reporting population. Network, systemwide, GMV, or curated subsets remain qualified Drivers. Source-stated residuals may be company-specific slice values. Eliminations and consolidation artifacts are neither Driver names nor slices; drop and log the artifact while keeping the affected metric fact.
13. **NAME-12:** Only the cause, a stated per-X denominator, a benchmark, and a terminal family suffix may appear in a name.
14. **NAME-13:** A stated business or physical per-X denominator stays in the name. Do not invent one. Different denominators are different Drivers and never `SAME_AS`. Store the base unit; `eps` remains the familiar exception.
15. **NAME-14:** A measurement version such as adjusted, diluted, or constant currency belongs in `fact_scope.measurement`, not the name. An absent measurement never means GAAP.
16. **NAME-15/16:** Exclude state, direction, motion, reporting company, incidental entities, date/period, size/unit, source/vendor metadata, XBRL prefix, generic sentiment/effect, bare category, vague filler, and grammar glue. Carve-outs: the entity ban does not apply to an external actor whose action is the cause; stable nouns and metric phrases ending -ing/-ed (`pricing`, `bookings`, `operating_margin`) are legal names; a sentiment/effect word is legal only inside a specific reusable market force (`glp1_pressure` — generic "pressure" stays banned).
17. **NAME-17:** Terminal `_guidance` and `_surprise` stay in the name and also keep permanent `fact_type`. One surprise Driver holds all three surprise types. Link guidance/surprise to the base metric with `BASE_METRIC`, never `SAME_AS`.
18. **NAME-18:** Admit a new Driver only when no existing Driver has the same meaning, all name rules pass, nouns are source/catalog grounded, at least one causal evidence atom exists, the result is reusable, and its meaning is unambiguous. Vague evidence is skipped.
19. **NAME-19:** Change naming rules only through a general principle, never by adding a sector example as policy.

### 4.4 Driver types and families: MF-01 through MF-12, DU-05 through DU-07

- There are exactly four permanent `fact_type` values:
  - `metric`: a standing variable or condition, numeric or qualitative, which can be read again.
  - `guidance`: the company's own forward outlook.
  - `surprise`: a delivered actual or promised guide compared with a cross-party expectation.
  - `action_event`: a discrete happening.
- Use the persistence test for metric versus action: if a standing level or condition can be read again later, it is a metric; otherwise it is an action. `_guidance` and `_surprise` framing overrides. Outlook verbs route to guidance.
- The permanent type is set once during final admission/finalization. A Driver without a type cannot accept a fact. Later catalog work cannot retype a fact-bearing Driver.
- Bare-root defaults remain: litigation, convertible notes, dividend policy, and restructuring costs are metric; corporate restructuring and asset impairment are action.
- Different flavors of one topic are separate Drivers linked as a family. Every guidance or surprise Driver has exactly one `BASE_METRIC`; action Drivers have none.
- The base Driver must exist. It may begin as a latent, empty, non-tradeable base anchor. Exact later evidence graduates it automatically.
- Only a terminal suffix counts. Strip it once.
- A synonym relation uses `SAME_AS`; a family relation uses `BASE_METRIC`. Do not substitute one for the other.
- Only the base metric receives direct XBRL concept enrichment. Guidance and surprise inherit through the family when allowed.
- `company_confirmed` is a guidance-fact boolean, never a Driver-family or identity field.
- **OD-1 overlay:** terminal guidance/surprise admission needs two independent source-grounded yes checks and an admission memo. Invalid names are re-coined specifically or parked. Only a valid clean latent base may be created.
- **OD-2 overlay:** deterministic type rules run first. In a batch with the full evidence set, an action judgment stamps `action_event`; a proposed metric needs a second quote-backed “metric proves itself” check, and failure becomes `action_event` with `metric_proof_defaulted=true` and a counted warning. In live thin or unclear evidence, park and retry before any default. Bare guidance/surprise is a naming defect. A family base must be a deterministic, OD-2-proven, or OD-1-latent-proven metric.

### 4.5 Real-fact gate, birth, and ownership

- One real fact in one event is sufficient. Recurrence and “more than two events” are not gates.
- Boilerplate, bare mentions, and non-facts are dropped before storage.
- Any authorized evidence-bearing channel may submit raw source evidence. The shared core alone decomposes, reuses or creates the Driver, builds identity, validates, and writes.
- A newly admitted Driver is **born complete with its first fact**. General name-only catalog seeding is rejected because it lacks birth evidence. Exact latent base anchors are the only exception; dry-run proposed names may exist outside the graph.
- **OD-2 first-fact pin, homed in the still-broader OD-7 work:** a zero-fact Driver's first fact must have `driver_state != unknown`; otherwise park until a readable-state fact arrives. This owner-approved OD-2 supporting pin does not ratify OD-7's whole live-admission recommendation. It applies only at first birth; OD-14 still allows `unknown` on later or already-grounded facts where its lane rule requires it.
- Category labels describe the birth situation, not a second permanent Driver type.
- Cross-channel submissions for the same source event converge through the same code-built identity. Exact or compatible reruns fill safely; conflicts stay visible and separate. Near-synonym races are accepted over-splits and may later receive `SAME_AS`.
- A channel or weak model never final-confirms identity, family, link, fact placement, eligibility, or quarantine. A strong model is required where semantic confirmation is final.

### 4.6 Exact state vocabularies: DU-08 through DU-12

- `driver_state` lives on the DriverUpdate, not the Driver name. The quote remains the precise truth.
- Metric: `increased`, `decreased`, `unchanged`, `mixed`, `reported`, `persists`, `unknown`.
  - First match wins: stated direction; same Driver differs across parts; explicit flat; ongoing without direction; bare value; otherwise unknown. A bare value is `reported`; when a prior value is stated alongside it **in the source**, the fact routes to `increased` or `decreased` instead. Metric/surprise/action states are read from the source text alone — no graph-history read; only the guidance lane consumes a code-served prior view.
  - Good or bad never decides this state.
- Guidance: `introduced`, `raised`, `lowered`, `reaffirmed`, `withdrawn`, `unknown`.
  - Store movement only when the source states it. A bare guide stores `unknown`; readers may derive `effective_driver_state` from the prior collapsed value. Do not write the derived state back.
  - For a source-stated movement with two closed shapes, midpoint up means raised, midpoint down means lowered, and equal means reaffirmed. The validator skips this check for stored `unknown`.
- Surprise: `beat`, `in_line`, `missed`, `unknown`.
  - Code computes only position: above, inside, below, at floor, or at ceiling.
  - Code may set `in_line` for a wordless actual inside or on a closed expectation range, and for a wordless guide range that contains the consensus point.
  - `beat` and `missed` are meaning judgments from full context. Never assume higher is better. Wordless outside-range cases need a safe polarity proof or remain unknown.
- Action: `at_risk`, `announced`, `occurred`, `continued`, `resolved`, `canceled`, `suspended`, `rumored`, `failed`, `unknown`.
  - Classify the latest stage of one action.
  - Terminal: `failed` is involuntary failure; `canceled` is the company's voluntary withdrawal; `resolved` is a settled two-sided dispute; `occurred` is completion.
  - Non-terminal: `rumored` is unconfirmed third-party reporting; `at_risk` is a specific current adverse threat that is not the company's own plan; `suspended` is paused but resumable; `announced` is the company's stated action before completion; `continued` is still ongoing.
  - A denial remains rumored. Declining an offer never committed to is failed. Shelve/postpone maps to suspended; scrap/abandon/withdraw maps to canceled; a threat remains at risk until it happens, then maps to failed under the existing ladder.
  - Generic risk boilerplate is dropped.
- Code hard-fails a state outside its Driver's lane.

### 4.7 DriverUpdate identity and fact scope: FS-01 through FS-04, FS-27, OD-8

- Base identity is `event + driver + fact_scope`. Producer/model identity is never part of the fact key.
- Code builds the ID. IDs and stored scope tokens are immutable.
- Canonical scope slot order is:

```text
period=<period_u_id>
|slice=<sorted kind:value parts>
|measurement=<sorted tokens>
|surprise=<type>             # surprise lane only
|quote_hash=<full sha256>    # rare collision member only
```

- Omit absent slots. Do not store `slice=total`. Formatting normalization is allowed; semantic aliasing is not.
- `surprise=` is required only on surprise facts and forbidden elsewhere. Its values are `actual_vs_consensus`, `actual_vs_guidance`, and `guidance_vs_consensus`.
- Code composes the surprise slot before fusion from transient `surprise_basis_hint` (`actual` or `guidance`; required on every surprise item and forbidden on the other lanes) and required `comparison_baseline` (`consensus` or `previous_guidance`). Do not infer basis from whether a period ended.
- Every grounded surprise needs a matching home fact in the same event: actual surprise -> metric; guidance-vs-consensus -> guidance. Match family, period, period scope, slice, measurement, and normalized value/unit when value-bearing. A numberless surprise still needs a numberless home fact. An ungrounded “results beat” is parked. An actual surprise before its period ends is rejected.
- Add a future scope slot only when it is identity-bearing for its lane, cannot be derived from existing slots, and is never compared across lanes.
- Fuse same-event, same-driver, same-scope pieces before collision handling.
- **Effective collision rule, replacing stale FS-03/T3.4/FACT-12 text:** hash the fixed ten-slot value signature only: `level_low`, `level_high`, `level_unit`, `change_value`, `change_unit`, `comparison_low`, `comparison_high`, `comparison_baseline`, `value_text`, `conditions`. The field is intentionally still named `quote_hash` for compatibility even though quote text is excluded. Also exclude state, confirmation, producer, source type, date, and XBRL enrichment.
- The exact preimage is a fixed-order compact JSON **array**, ASCII-escaped with compact separators; JSON null stays distinct from empty string. Text uses the one shared normalizer. Numbers use the one writer decimal canonicalizer: no exponent, no trailing zeros, and `-0` becomes `0`. Units and values are canonical before the full untruncated SHA-256 is computed.
- Probe siblings only with `id = bare_id OR id STARTS WITH bare_id + "|quote_hash="`; a raw bare prefix is unsafe because scope slots are optional. `exact` means all ten slots, including nulls, match; `compatible` means no shared non-null slot disagrees; `conflict` means at least one shared non-null slot disagrees.
- All collision decisions use the **pre-batch graph state**, so input order cannot decide identity. With no sibling, one post-fusion fact stays bare; multiple initially pairwise-conflicting facts are all hashed. With one sibling, compatible fills without null-clobber and conflict creates a flagged hashed member. With multiple siblings, exact merges, conflict-with-all creates a hashed member, and compatible-but-not-exact parks as ambiguous.
- If two items in one batch compete to fill the same partial sibling, park the competitors; a richer rerun resolves them.
- A true signature correction requires the repair lane. Non-signature fields keep the approved last-write-wins-with-log correction behavior. At most one bare member may exist and members must pairwise conflict on at least one shared non-null slot. Late bare-plus-hashed history is legal and is not re-keyed. Equal-signature race duplicates read as one until repaired.
- A model may propose or approve `SAME_AS` and D5 fusions; code alone applies a reversible link from an approved trace. A model never directly deletes, re-keys, or moves facts, and never bypasses approval.

### 4.8 Slices: FS-05 through FS-24

- A stored slice token is `KIND:VALUE`. Values are normalized free text.
- Kinds are `segment`, `product`, `geography`, `customer`, `channel`, `entity_ownership`, plus safe fallback `unknown`.
- Tests: operates as -> segment; sells -> product; operates in -> geography; sells to -> customer; how it sells/runs -> channel; stake it owns -> entity ownership.
- `entity_ownership` is the least-clean kind. Joint-venture and equity-method cases are strongest; other entity rows are handled conservatively and are often provisional.
- A real slice is a business population for which “revenue/earnings from ___” makes sense. Accounting labels are not slices.
- Source-stated residuals such as Other or Corporate Unallocated are legal company-specific slices but should be marked non-continuous in reads. Eliminations, fair-value levels, and consolidation artifacts are dropped and logged as slice artifacts.
- Brand is not a kind. Its axis or prose role decides the kind.
- Multiple parts are code-sorted and joined with semicolons; do not drop one.
- Slices apply to all four fact types. Period is never a slice. Omitted slice means consolidated whole-company for metric/guidance/surprise and no applicable or narrower part for action.
- The axis-to-kind table is frozen in code and refreshed only through an offline governed update; that offline classification judges an axis by its MEMBERS, never its name — names lie, with roughly 20% error.
- Axis outcomes: known slice axis -> mapped kind; known non-slice axis -> exclude/skip its member role; unknown axis -> provisional, never silently dropped.
- The company menu is the union of members from all prior public 10-Q/10-K filings plus values already used for that company. Write menus are cut at event/source public time. Naming has no such menu; repair may see full history.
- For each part, choose one: menu reuse — the producer judges same meaning, and code validates that the pick is exactly a menu value, never near-snapping; source-grounded off-menu coin; `unknown:` when kind is unclear; omit for true whole-company/no part.
- If a normalized label exists under multiple menu kinds without selecting context, use `unknown:`. Clear prose may coin a kind. Ambiguous prose must not guess.
- An unknown XBRL axis/member uses the code-only sentinel `unknown:xbrlaxis_<lowercase UTF-8 hex of exact axis qname>__<normalized_member_value>`. Unknown values enter the company menu for later reuse.
- Code validates format and exact normalized equality only. It never near-snaps.
- Stored slice values are first-write immutable.
- There is no human alias layer and no “confident alias” merge. The only accepted label-drift grouping is read-time, company-scoped, and member-anchored: all linked facts for both labels must agree on the same exact axis/member pair. Prose-only drift stays split.
- The elimination guard uses three exact frozen buckets: hard exclude, provisional, and keep. Never replace it with a regex.
- `MAPS_TO_MEMBER` is fact-level enrichment, needs both axis and member, may be absent, and carries the slice part it supports.
- FS-22 recurrence across companies is retired. FS-23 cross-company slice-value comparison remains open and must exclude residuals.
- Raw reads group by the full series key, not slice alone. Provisional slices stay out of cross-company analysis until promoted.

### 4.9 Measurement: FS-25 and OD-9

- Measurement is an open, source-grounded, code-sorted set in `fact_scope`, not a closed enum and not a Driver-name field.
- The producer/core semantic step copies exact transient `measurement_raw_spans`; code alone normalizes lowercase, converts each non-alphanumeric run to `_`, trims, collapses repeats, sorts, and joins.
- A maximal contiguous qualifier span becomes one token: `adjusted, diluted` -> `adjusted_diluted`. Split only where non-qualifier prose separates spans.
- Any number modifier not captured losslessly by name, period, unit, slice, or sequential-basis logic stays in measurement. When unsure, keep it. This is the never-drop safety sink.
- Empty measurement is legal and never implies GAAP.
- Do not synonym-merge measurement tokens at write time. Equivalent-label views may exist at read time without changing identity.

### 4.10 Units and signed values: UNIT-01 through UNIT-14, OD-10 through OD-13

- The exact unit enum is: `usd`, `m_usd`, `percent`, `percent_yoy`, `percent_sequential`, `percent_points`, `basis_points`, `count`, `x`, `unknown`.
- Use the proven pure V2 resolver. The semantic extractor copies signed unscaled source numbers and verbatim raw units; code decides the canonical unit and scale.
- **Effective UNIT-04:** each numeric level or change slot carries its own required raw unit plus a unit-kind hint in `money`, `ratio`, `count`, `multiplier`, or `unknown`. Money mode is required for kind `money` and is `aggregate`, `price_like`, or `unknown`; it is null for other kinds. A legacy single hint pair may apply to level only. Resolve level and change separately.
- Validate both the final enum and scaled value. Glued billions convert to `m_usd` by 1,000; cents-on-aggregate and pre-scaled mistakes hard-fail. Non-USD gaps may remain `unknown` and are monitored.
- Units live on facts, not Drivers. A stated per-X denominator lives in the name while the value uses the base unit. There is no `comparison_unit`; comparisons share `level_unit`. `level_unit` is required when any level or comparison number is non-null. `change_unit` is required when `change_value` is non-null. `unknown` is legal for either required unit when the source does not safely resolve further. No number means no unit resolution.
- Escalate the per-X name/unit lint to a hard failure for a money level with a stated denominator but no `_per_` name.
- `percent_sequential` is a separate series. Apply the static-percentage gate first: bare “up/down X%” on a static percentage-level metric is `unknown` unless the source says points/bps or “of/to X%.” Percentage points or basis points beat growth wording; growth is never plain `percent`. Annual, YoY/comparable, and bare-dated growth use `percent_yoy`; immediately prior comparable periods use `percent_sequential`; a sentinel basis is `unknown`. Two stated bases split into two facts. A numberless **growth** fact may take its unit from source framing. Measurement is independent.
- Values use the signed Driver axis. A net loss is negative, not a positive loss magnitude. A charge/provision amount is positive; a benefit, credit, release, or reversal is negative. Bounds follow algebra: “loss up to 2B” is a floor at -2B; zero-crossing ranges are legal. A numberless loss has no numeric bounds. Conditional downside remains narrative. Co-stated one-sided bounds fuse under the normal within-event rule.
- Code never assigns beat/miss from sign. Meaning decides favorability.
- Code writes `series_unit` once as a grouping tag. Level-bearing facts use the level's canonical axis. Delta-only facts fold to the Driver's dimension only when their own evidence makes it unique; otherwise use exact change unit or unknown. Numberless facts use `series_unit=null`, except that a withdrawal or reaffirmation copies exactly one clear prior `series_unit` and otherwise fails closed. Reads group by equality only; no unit-family map and no unknown absorption.
- UNIT-13 evidence is strong, but UNIT-14 remains build-pending: wire the resolver, validators, parity/replay checks, and shared home.

### 4.11 Periods: PER-01 through PER-20

- `DriverPeriod` is the actual calendar window the fact is about, not event date, raw “Q1,” forecast marker, or a replacement for fact type.
- One generic node serves all four lanes. Keep label `DriverPeriod` and `gp_` IDs.
- Use one `HAS_PERIOD` edge. Its meaning comes from the fact lane.
- Guidance requires its target period. Metric and surprise use a stated, clearly implied, or safely derived real period. Action has a period only when a real action window is stated. Never force one.
- Actual surprise uses the reported period. Guidance-vs-consensus uses the guidance target period, even if that period has ended.
- Event metadata may supply an implied reported period only when exact and never for guidance-vs-consensus.
- Exact YTD, TTM, cumulative, and stated date ranges beat fiscal shorthand. Keep their real dates; do not collapse them to a quarter.
- Periodless action has no edge. Do not use `gp_UNDEF` as a quiet fallback.
- Four sentinels represent real dateless horizons only, with a two-way stored invariant: `short_term` <-> `gp_ST`, `medium_term` <-> `gp_MT`, `long_term` <-> `gp_LT`, and `undefined` <-> `gp_UNDEF`. Stored `long_range` is retired; a stated date range stores `exact_range`. Driver items with unresolved fields and no explicit sentinel hard-fail; action sentinels hard-fail.
- Reuse one shared fiscal resolver. Resolution order is exact dates, explicit sentinel, long range, month, half, quarter, year, then pure-builder undefined only for old parity. Missing fiscal year end fails closed. Market-wide facts use calendar mode.
- Code builds the ID. The same resolved period ID appears in `fact_scope` and `HAS_PERIOD`, checked both ways.
- The resolved period ID and dates are authoritative after write; raw fiscal year/quarter must never regroup facts later. Period nodes store only `id`, `u_id`, `start_date`, and `end_date`. Fiscal framing remains on the fact. Never group by period alone.
- Instant is the legal one-day form. A duration with `start_date == end_date` is invalid input. Dates and constraints are write-once.
- Old `GuidancePeriod` is retired with old Guidance. There is no dual-label transition or production replay.
- PER-20 remains build-pending: shared resolver, 21 required tests, Dec/non-Dec YTD and TTM proof, hardening, and XBRL-race eligibility.

### 4.12 Stored DriverUpdate contract: 24 counted fields

The count is exact: six code-written fields plus eighteen semantic/enrichment fields. Recovery metadata is outside the count.

| Owner | Fields |
|---|---|
| Code, 6 | `id`, `fact_scope`, `series_unit`, `created`, `date`, `source_type` |
| Semantic/enrichment, 18 | `driver_state`, `quote`, `level_low`, `level_high`, `level_unit`, `change_value`, `change_unit`, `comparison_low`, `comparison_high`, `comparison_baseline`, `value_text`, `conditions`, `company_confirmed`, `xbrl_qname`, `fiscal_year`, `fiscal_quarter`, `period_scope`, `time_type` |

- `created` is set only on create. `date` is the full source timestamp. The stored source enum currently lists `8k`, `transcript`, `10q`, `10k`, `news`.
- Recovery-only `disputed` is a boolean controlled solely by the recovery system. It is not producer-written and not one of the 24 fields.
- Number shapes are self-describing:
  - point: both low and high equal;
  - closed range: both present and low < high;
  - floor: low only;
  - ceiling: high only;
  - numberless: all number slots null.
- Transient shape hints are required when numbers exist, checked, and discarded.
- Change and comparison numbers are source-stated only. Use at most one primary baseline. A baseline may be present while comparison numbers are null. Do not compute and store a duplicate delta or expectation; specifically, leave `change_value=null` when it could merely be derived from a closed level/comparison shape.
- A change-flavored unit goes in `change_value` when the Driver's own level is absolute, but in the level slots when the Driver itself is the rate/growth metric. Percent-only guidance stores its growth basis in `level_unit`; only the guide's own revision size belongs in `change_value`.
- If `change_value` is present, `increased`/`raised` requires a positive value and `decreased`/`lowered` requires a negative value. `beat` and `missed` are excluded because favorability is semantic.
- `comparison_baseline` is one of `consensus`, `prior_year`, `sequential_period`, `previous_guidance`, or null.
- `value_text` is guidance-only, numberless-only, normalized, at most 200 characters, and rejects stored numeric values while allowing date/period anchors.
- `conditions` is guidance-only and its clause must remain in the quote.
- `company_confirmed` is guidance-only boolean. Current direct company output is true; third-party relays may be false.
- `xbrl_qname` is metric-only enrichment and is dual-stored with the concept edge.
- `period_scope` enum is `quarter`, `annual`, `half`, `monthly`, `ytd`, `ttm`, `exact_range`, `short_term`, `medium_term`, `long_term`, `undefined`. Do not store `long_range`.
- All stored level/change/comparison numbers are source-stated; deterministic scaling may canonicalize them. Classification, period, collision, and withdrawal may derive only their approved non-numeric state, IDs, or facts and never license an invented stored number.

### 4.13 Per-lane field rules

| Field | metric | guidance | surprise | action_event |
|---|---|---|---|---|
| Core identity, state, quote, source, Driver edge | required | required | required | required |
| Period | when real | required | when real; guidance-vs-consensus required | rare, when real |
| Level/change | only when stated | only when stated | only when stated | only when stated |
| Comparison values | when stated | prior band when stated | expectation when stated | when stated |
| Comparison baseline | only prior year/sequential; expectation baselines forbidden | consensus forbidden | required consensus/previous guidance | when stated |
| `surprise=` | forbidden | forbidden | required | forbidden |
| `value_text`, `conditions`, `company_confirmed` | forbidden | allowed under exact rules | forbidden | forbidden |
| Direct XBRL concept | allowed by enrichment | forbidden; inherit | forbidden; inherit | forbidden |

- A reported actual versus consensus or prior guidance writes a surprise plus its metric home fact.
- A forward guide versus consensus writes a surprise plus its guidance home fact.
- A guide versus the company's prior guide is guidance movement, not `guidance_vs_consensus` surprise.
- A temporal comparison with prior year or sequential period is a metric change, not a surprise.
- Revisit triggers for metric `value_text` and action `conditions` are not decisions. They activate only after the named real-data census conditions and a fresh owner change.

### 4.14 Edges, verdict, and DailyCompanyMoveEvent

- Each DriverUpdate has exactly one `OF_DRIVER` edge to a typed Driver.
- Every DriverUpdate identity is source-event-based and has `FROM_SOURCE` to that Event. News is the source Event on the macro/news path. A `DailyCompanyMoveEvent` is only an optional verdict target, never the fact's substitute source; a pure macro case with no source remains parked. Company is reached through the Event; DriverUpdate has no `FOR_COMPANY` edge.
- `HAS_PERIOD` follows the lane rules above.
- `MAPS_TO_CONCEPT` is metric-only, zero or one, best-effort, and paired with `xbrl_qname`.
- `MAPS_TO_MEMBER` is zero or more on any lane and carries `slice_part`.
- `EXPLAINED_BY` is an optional edge from an Event or `DailyCompanyMoveEvent` to the DriverUpdate it attributes. Provenance and attribution are never collapsed into one edge.
- The verdict is an edge, not a node. Its key is explained target + Driver + fact scope + producer, so two producers may disagree.
- The edge points to the DriverUpdate the producer judged. If the same verdict key would point to different same-day source facts, a uniqueness check prevents two rival endpoints; live-over-backfill precedence or same-mode failure applies.
- Verdict axes are independent:
  - `stock_impact`: `long` or `short`, the Driver's push and not necessarily the net move;
  - `weightage`: 0.1 through 1.0 deciles or null, an independent force, never a share and never summed to 100%; null means direction is known but size is not;
  - `confidence`: 0 through 100 in tens, certainty that the attribution is true.
- Other verdict fields are producer, mode (`live` or `backfill`), id, created, and its retained judgment hash. The hash is the first 16 hex characters of SHA-256 over `stock_impact|weightage|confidence`; mode is excluded and producer is in the key. Live wins over backfill.
- Reads may derive `share_i = weightage_i / sum(weightage)` within one event and producer, and signed force from weightage and impact. These are never stored as true causal shares; stored edges are not normalized to sum.
- Never show realized return to the verdict producer.
- `DailyCompanyMoveEvent` has its own label, `id=dcm:<cik>:<trade_date>`, `FOR_COMPANY`, and `ON_DATE`; realized return stays in the price graph. Its trade date comes from the returns/trading-day layer, not fact-date bucketing. News remains the source event when present. On a same-day filing/DCM overlap, the filing wins at read and the DCM is ignored, not deleted.
- DCM significance threshold, pure-macro source handling, and two-independent-catalyst handling remain open.

### 4.15 XBRL member and concept enrichment: XC-01 through XC-18

- Goal: attach the exact company-reported concept or attach nothing. A wrong concept is much worse than an absent concept.
- Rejected methods remain rejected: live value match, token match, static dictionary, and simple multi-method agreement.
- Current text-created fact linker order is: deterministic guard -> point-in-time company concept menu -> the locked cheap model (**Haiku**, XC-04) picks one or null -> exact in-menu check -> adversarial verify with default refute -> deterministic veto/backstop -> write or abstain. The exact guard order (G2 -> G0 -> G1), the exact GAAP-compatible measurement set, the two-equal-candidates -> higher-usage rule, and the four exact deny pairs live verbatim in `08` XC-04/05/06/07 and must transfer whole at migration.
- Guards reject non-GAAP/measurement-specific facts, unsuitable event/macro facts, and derived ratio/growth facts, with the stated tax-rate exception. The measurement set is the primary non-GAAP guard; name regex is legacy fallback only.
- Prompts stay loose enough to preserve recall. Deterministic code supplies the safety veto.
- Backstops cover instant/duration, basic/diluted, per-share versus cash total, and four explicit component/aggregate deny pairs. They veto only; they do not invent a link.
- The menu contains the company's consolidated numeric concepts and metadata, cut at the fact's public time for history; live may use the latest. Pass the whole menu and check the returned qname exactly.
- Store both `xbrl_qname` and `MAPS_TO_CONCEPT` on the metric fact. Match qname across taxonomy years with a bounded match. Missing graph concept does not block the fact and can self-heal later.
- Guidance/surprise inherit through `BASE_METRIC`; action abstains. Non-GAAP measurement blocks inheritance.
- Invocation uses in-session subscription agents. SDK/API-key use is not approved without separate owner approval.
- Evidence supports high precision, not universal zero error. Keep the caveats and sampling monitors.
- XC-16, the calculation-hierarchy veto, is recommended before full rollout and remains build/open timing work. Monitor period/balance signatures, abstentions, and optional run disagreement. Resolve once per company/base metric; add cache only if needed.

### 4.16 Read, collapse, and point-in-time rules

- The full series key is company, Driver, fact type, slice, resolved period, period scope, measurement, `series_unit`, `time_type`, and surprise subtype when applicable. Family is added only for cross-flavor views.
- `series_unit` groups by equality. No unknown absorption or runtime family map.
- Within one event, fuse before collision. Slices beat a vague `mixed` record when clean parts are stated. A consolidated fact exists only when itself stated.
- Render in this order: level shape; signed change; comparison; guidance `value_text`; truncated verbatim quote. Quote is the last display fallback, not the collapse comparator — the comparator is the numeric `level_*` signature, or normalized `value_text` for qualitative facts.
- Citation id uses Driver name plus fact-scope suffix when needed.
- Standing per-X policy level is a metric; a discrete decision to initiate, change, or suspend the policy is an action.
- A direction plus bps/percentage-points without “to X” is a change, not a level.
- `narrowed` is read-derived from consecutive closed widths and never stored.
- Within the same company/series/day, source rank is 8-K, transcript, 10-Q, 10-K, news; ties use later timestamp, then source id. Across days use the latest while retaining history. Amendments are new facts.
- “Day” follows Eastern Time. Backtest cutoff is strict `date < as_of`; live sees current graph. Never expose realized returns.
- Member-anchored grouping is deterministic, per company and per slice part, requires one exact shared axis/member pair, and changes display grouping only.
- Every read result is labeled `raw` or `reconciled`. Reconciled views can be disabled and use only deterministic point-in-time edges.
- Guidance movement is derived from the prior collapsed same-series guide only when the source did not state movement and the fact is not a correction. The result is `effective_driver_state`, never a stored rewrite.
- Withdrawal fan-out is the one bounded derived write: only clear exact-scope withdrawal, only open guides, resolved-period containment, add-only, no replacement/reaffirmation ambiguity. Late matching guides receive the missing withdrawn fact. Amendments remain new events.

### 4.17 Continuity and recovery: FS-26, kernel recovery D4 / `95` #39, OD-18 through OD-20

- A transient `continuity_hint` may propose `CONTINUES_AS`. Recast/recompose wording is a lexical pre-refusal. A dedicated blind strong continuity judge, not the sameness judge, must confirm an explicit old-to-new declaration, unchanged composition/methodology, and both exact endpoints; otherwise refuse.
- It is company-scoped, directional, dated, reversible, read-only, and point-in-time. It does not change stored IDs or facts and does not propagate across flavor/family links.
- Driver endpoints use an edge; slice/measurement string endpoints use a reified claim. At most one active outgoing continuation per old endpoint — fan-out is refused. Fan-in quarantines both; cycles are refused.
- Reads follow only declarations public before `as_of` — the cutoff is checked **per hop** along a chain — stop at the terminal label, and make no model calls. Exactly one reconciled-view instance exists (`CONTINUES_AS` chains); the once-proposed unknown-axis qname-grouping view was explicitly reviewed and DEFERRED (it fails point-in-time without dated table snapshots) — do not rebuild it without a fresh owner decision. Exact edge/record fields, indexes, and the recovery lane live in `03` FS-26.
- Confirmed-wrong `SAME_AS` and `CONTINUES_AS` links use their approved reversible quarantine paths. A confirmed mis-attached fact is marked `disputed`; disputed facts leave cross-company/history-weighted features until cleared. BASE_METRIC/family propagation remains candidate. Do not delete, re-key, or move history.
- Recovery uses auditable `RecoveryEvent` records. The separate candidate recovery machinery must not be presented as final merely because these approved paths exist.
- **OD-18 ATTACH rule:** run the deterministic risk prefilter synchronously. A flagged ATTACH receives a blind strong three-check (same cause + same causal scope + same mechanism, against the head's frozen anchor) before write. `REFUSE` can never be overturned toward a write; `UNSURE` gets one blind escalation and only `CONFIRM` writes. Any other result causes a specific re-coin or a counted terminal skip; judge timeout parks for retry. A QUARANTINED head blocks exact-ATTACH entirely: incoming facts PARK-RETRY (the safe under-attribution direction). On ESTABLISHED heads only qualifier heterogeneity flags; on non-ESTABLISHED heads the at-least-eight-company condition also flags. Keep `flag_rate`, `refuse_rate`, `escalation_disagreement_rate`, and `recoin_failure_rate`, plus the post-write sample audit. Accepted residual until OD-19's gate passes: a wrongly refused token-subset re-coin is not judge-recoverable — counted, visible under-attribution by design. The exact prefilter triggers live in kernel §9.2.
- CLAIM is separate from OD-18. The locked role-tier rule requires strong-judge confirmation if CLAIM is ever enabled; CLAIM currently ships off.
- OD-19 makes generic token-subset matching judge territory only after the K-pairs.v2 portion-family gate records zero wrong-same. Until then it remains inert. Cross-flavor, terminal-suffix, per-X, and OD-17 portion differences remain permanent refusals.

## 5. Input contracts

### 5.1 Raw adapter submission (active Channel Contract)

This is the newest active public boundary. It supersedes the channel-facing meaning of “producer packet” in Track B. It does not replace the internal decomposer-to-writer contract.

- Every source channel has only three jobs: select source events, fetch raw evidence, and submit one packet per event.
- The channel never names a Driver, selects an existing Driver, builds an ID/scope, resolves a fiscal period, creates measurement tokens, canonicalizes units, computes values, or writes the graph.
- Required event envelope: source id, allowed source type, ticker, fiscal-year-end data, and event time. The source id must already identify a graph Event/Report or the packet parks and retries. One invocation handles one source event.
- Each raw candidate carries the verbatim quote, untouched label/claim, signed unscaled stated values, raw units, and raw period/cadence/adjacent wording. When XBRL is present, concept qname, axis, and member are all required together with the exact start/end context and instant/duration type; optional fragments are not a valid XBRL block.
- Guidance candidates may also carry verbatim value text, conditions, and company-confirmation evidence.
- If an adapter happens to receive final names, IDs, periods, measurement tokens, canonical units, or derived values, the core ignores and recomputes them.
- Submit in public-time order per company. Channels do not coordinate with one another. Late and duplicate delivery is legal and must be idempotent.
- Core outcomes are machine-readable: written, merged, parked, skipped, or rejected. Conflicting evidence remains visible rather than overwriting identity.
- Each channel keeps a cursor and event ledger with a completeness/extraction stamp. It may mark a source absence only after a clean complete search. Reopen on a new source, repaired corpus, or certified locator improvement.
- A channel must never fabricate, round, paraphrase, group identity, or write graph data.
- A new channel is complete only after its select/fetch/submit adapter passes certification against the shared contract.

### 5.2 Internal core packet (frozen Candidate Fact Packet v1.0)

This is the internal shared object after raw evidence enters the core. The file calls it “three blocks” but numbers Block 0 through Block 3; the intended meaning is three required blocks plus an optional verdict block.

The source file is owner-frozen, but it does not embed a source hash. This audit recorded its PRE-AMENDMENT baseline SHA-256 as `86b2fc179c12c6e6179d819f18058bb57d2af72f908705e0e97e719383ceb3ab` (the Phase-1 manifest value); after the two 2026-07-15 owner amendments (Q4, Q1-ext) the CURRENT sha is `aa7239ed…` — the round-9 freeze in §16 is authoritative for current hashes. Its wording nits belong in status/history unless the owner explicitly authorizes an amendment. Consolidation may place this contract inside `BUILD_AND_OPERATIONS.md` only after that exact version is pinned, then copied byte-identically with the frozen banner and hash check preserved; until relocation is approved and proved, keep the source as a temporary fifth live file.

| Block | Purpose | Contents |
|---|---|---|
| 0 | Event envelope | source id/type, ticker, fiscal-year-end, optional calendar override, event time |
| 1 | Transient identity signals | proposed name, slices, measurement spans, per-X, quote, event time |
| 2 | Proven fact | admitted Driver/state/quote, all source values/text/conditions/confirmation, raw units/hints, shape hints, period inputs, slices; code builds identity fields |
| 3 | Optional verdict | target, long/short direction, force, confidence, live/backfill mode, producer |

- The admission evidence atom and writer item are the same fact. Creating a Driver admits it with this first fact.
- The packet has three consumers: admission kernel, deterministic fact writer, and optional verdict writer.
- Shared decomposition order is fixed:
  1. strip generic direction/effect words;
  2. peel exact measurement spans;
  3. keep a stated per-X denominator in the name;
  4. keep portion qualifiers in the name;
  5. apply the local own-part slice versus external/unclear name test;
  6. assemble the canonical name;
  7. stamp the permanent fact type with the suffix/persistence/metric-proof rules;
  8. resolve units and write `series_unit`.
- Code owns format normalization, axis tables, unit/period/ID construction, and validators. The semantic model proposes meaning. The strong admission layer makes final reuse/create/reject/type/family decisions.
- One shared decomposer serves all channels. Adapters stay thin. A label-only proposal may be cached only with per-quote confirmation; quote-dependent measurement, time, state, and markers are never cached.
- Fiscal.ai input is re-sorted from KPI-major to source-event-major, chronological per company. Channel grouping is provenance only. Separate source events remain separate facts and collapse later in reads.
- Cross-channel same-event behavior follows OD-8: exact match, compatible fill, conflict sibling and flag, no normal overwrite, at most one bare member, and read repair for concurrency duplicates.

### 5.3 Fiscal.ai adapter details

- Map a real accession to the canonical Report/Event. `canonicalize_source_id` maps `:` to `_`. If the graph event is not present, park until it is. Fiscal.ai facts store the true document source type as `8k`, `10q`, or `10k`; the older offline `fiscal.ai-kpi` evidence atom is not a DriverUpdate channel source type.
- Use the Report public timestamp for point-in-time order and company fiscal-year-end data for fiscal math.
- Period evidence tiers are: exact XBRL context first; then cadence plus adjacent wording; then governed fiscal math. `time_type` is a required semantic output and is never defaulted. A same-ticker/KPI T1 sibling period type is only a hint and any conflict parks; `KNOWN_INSTANT_LABELS` is also hint-only. Unclear cases park and may drain after a later T1 sibling or concept/context evidence.
- Park on a T1 context-versus-form mismatch or on a T2/T3 explicit window marker that contradicts the stamped window. A duration with equal start/end is invalid; an instant remains the legal one-day form.
- Preserve signed unscaled source value and `fmt`; code scales without changing sign. Enforce boundary and sign guards.
- Measurement comes from the quote first or a verified label path; otherwise park.
- A tagged member uses the frozen axis-kind/menu/unknown-sentinel logic. Untagged prose uses the same local kind ladder.
- A bare table value is `reported`; if the quote states a comparison, the decomposer judges it through DU-09. Quote remains required.
- Vendor-computed changes/common-size facts are skipped; source-stated growth is allowed. The observed vendor-computed share was about 45,000 rows or 62%, but that is evidence, not a permanent threshold.
- A missing value may be skipped only after a complete clean source search and must reopen when the source or locator improves.
- Component-level accuracy is not end-to-end accuracy. The seed-to-kernel-to-writer pilot remains required.
- Old Guidance rows are never converted. Guidance is extracted fresh from source documents.

## 6. Build and operating map

### 6.1 Track A: catalog build, PIPE-01 through PIPE-37

**Purpose and boundary**

- Build one shared evidence-backed Driver class catalog: name, permanent fact type, `SAME_AS`/`BASE_METRIC` links, and evidence.
- Company, value, time, slice, measurement, unit, state, verdict, concept/member, and write-time menu data belong to facts.
- Track A does not write DriverUpdates. The old “KPI evidence makes a name only” clause is superseded by governed born-complete admission for live/channel evidence. Offline catalog mechanics are not otherwise canceled.
- OD-16 recommends a Track-B-owned graph-sync tool and its protected-input guard: if adopted, it must never rename, delete, retype, re-key, or orphan a fact-bearing Driver and may only add reversible links. This is tracked build wiring, not an owner-approved final rule; its proposed factless catalog materialization conflicts with the newer frozen born-complete contract and needs owner reconciliation.

**Pipeline**

```text
billing guard -> resolve scope -> fetch source text -> conservative chunks
-> blind leaf reader -> exact seed convergence -> reconcile -> G2/Refute
-> deterministic assembly -> validate -> bottom-up folds -> repair
-> class finalization -> final validation -> fitness gate
```

- Names are born at company/leaf level except a governed same-name split.
- Current census shape is 11 sectors, 115 industries, and 796 companies, including 17 single-ticker industries; 796 versus older 786 remains open.
- Fetch all supported non-news company sources. Use byte-conserving 40,000-character chunks. The special 99.1 earnings 8-K path is chunked; its KPI evidence rides the first chunk.
- Surface zero-yield events in the manifest; do not silently call them clean.
- Batch limits remain 400 seed records and 300,000 compact-JSON characters.
- Apply the same reconcile logic at every level. Assemble deterministically, validate every level, and repair before finalization.

**D1 through D8 and stage-zero guards**

- D1: keep a complete approval trace.
- D2: keep the tree bounded and deterministic.
- D3: reuse the same reconcile law at every fold.
- D4: `SAME_AS` links are additive and reversible; a confirmed-wrong `SAME_AS` edge may use its approved quarantine path.
- D5: same-name collision requires explicit split/rewrite/park handling.
- D6: dedup uses the strong Refute checks, not lexical equality.
- D7: preserve byte completeness from source to evidence.
- D8: account exactly for every fold input/output/park.
- Every consumer verifies the validation sidecar, hashes, expected counts, fold flag, and unchanged bytes. Menus must match the chunk manifest. Every seed needs a gate result or review entry. Review/decision relays are count- and hash-bound. Repair may judge only code-suggested pairs. Scope/tickers are pinned code-to-code.

**Evidence and artifacts**

- The offline Track A evidence atom is company, source type, source id, date, and quote. Its special `fiscal.ai-kpi` empty-date catalog evidence is separate from the live DriverUpdate channel contract; it is not a live source type and needs only a clear boundary/back-port note.
- Keep one run directory per scope with source/chunk/menu/seed/decision/approved/catalog/validation/manifest files. Folds add fold manifests and sidecars; repair adds candidate/plan/batch/review artifacts; finalization adds type decisions, family data, and disagreements.
- Record exact model IDs by role in `manifest.models`. Do not trust moving aliases.

**Naming/finalization overrides**

- All prompts use NAME-01 through NAME-19, the slice law, and MF-02. Do not read naming rules from old ontology files.
- Apply local role, measurement-out, per-X-in, family-suffix, external-actor, singular/plural, and metric-proof rules exactly as mapped above.
- Delete class-level XBRL guesses and unused `optional_links`. Concept links are company/time-specific fact enrichment.
- Live reuse is propose-first, followed by a bounded point-in-time related view and strong admission. The old catalog-first tool stays unwired.
- Finalization stamps permanent fact types and builds family records. A suffix base resolves to an existing record, a matching variant's representative, or a latent name in `families.json`; a latent is not a catalog record or retrieval candidate.
- Final checks cover type completeness, family target/type, suffix coherence, latent sanity, and cross-flavor disagreement. No hand edits.
- OD-1, OD-2, and OD-6 are effective overlays even though `10` does not fully contain them. OD-8 is a Track B collision rule and is not part of this Track A back-port set.

**Models and measured changes**

- Models are configuration slots chosen by experiment. Any optimization that changes the model or visible context needs a measured A/B gate with no new wrong merges and under-merge within the stated noise rule.
- The folder's old leading default is stale for the reader. Signed EXP-2 adopted `claude-sonnet-5`, high effort, 40k chunks, one run. Strong final identity/refute roles remain governed separately and may not be weakened by this result.
- Singular/plural pairs are wording variants only when meaning is the same.
- Pin exact model IDs and use judged precision/recall on an adjudicated key, never quote or name overlap as the score.
- K2 keeps fold repair per pair. Batched repair remains allowed for leaves under its existing gates; batched fold repair is a deferred optimization that needs its own experiment.

**PIT, acceptance, and order**

- Offline name creation may use full history because the name contains no company fact value. Any name shown to a historical producer and every fact-time menu must be cut to public time.
- Consumers use only final validated catalog records. Parks, side lists, and latent anchors are never tradeable or reuse candidates.
- Mechanical acceptance requires complete type/family checks, byte conservation, full repair, green sidecars, and pinned reproducibility.
- The real fitness gate has not run. Freeze a catalog, use fresh covered-industry events, lock the answer key before calls, run at least two independent producers, keep grader distinct from producer, and score name plus direction and inter-producer agreement.
- The gate must meet the existing name-plus-direction floor of 0.634 and inter-producer agreement floor of 72%; the older 0.535 blind score is a comparison baseline, not the final pass floor.
- The original `PIPE-37` 0.1% wording is superseded by OD-6: at least 3,000 fixed pre-registered slots, zero two-grader-confirmed wrong merges, zero unresolved flags after one blind regrade round, existing baselines, and a fresh key after failure. Red or inconclusive burns the key and turns its cases into regression fixtures.
- WP-FC-EDITS landed in commit `5db902f` on 2026-07-10: NAME-01 through NAME-19 were inlined, dead leaf-path XBRL/optional-link code was removed, MF-02 and model slots/provenance were added, and `min_score=0.60` was set at all four sites. Its suite passed 260 tests with one skip. This does not complete the fold/tree truth-up, all prompt-mirror checks, finalizer, real folds, WP-FC-RUN, or the fitness gate.
- Build order now resumes from the proved edit batch: verify any remaining rule mirrors and fold/tree paths; build the finalizer; harden/recall floor; rebuild fixtures; use the signed reader result; recreate the calibration leaf; run the first real two-industry fold; finalize; then run the fitness gate.
- Carry constants rather than re-derive them: 40,000 chunk characters; seed limits 400 records/300,000 compact-JSON characters; 20 evidence items per side, drawing the smallest side first, round-robin by least-represented company, one per source type first, with the next disjoint 20 for view 2 and no padding; high blast is 8 companies or a global fold with at least two children.
- Repair constants are Python `limit=2000`, JavaScript per-pair `200`, batched `0` meaning all (`600` is a page only), `PIECE_ROWS=100`, batch `k=10`, hard record-disjoint deterministic h32 shuffle, and canary rate `0.02` with minimum `5`.
- Retrieval constants are `text-embedding-3-large`, `top_k=5`, `min_score=0.60`, and embeddings on by default but suggestion-only. `norm()` is strip plus lowercase; h32 is the non-cryptographic 31-polynomial UTF-16 rolling hash.

**Track A still unproved**

- The 261-test baseline and structural checks do not prove catalog quality.
- No production graph catalog and no successful fitness gate are established by this folder.
- G1 display, target universe, lifecycle/IPO handling, the graph-sync boundary/tool, remaining fold/tree prompt mirrors, finalization, real folds, and incremental refresh remain work. The `min_score=0.60` code edit is already done.

### 6.2 Track B: fact build, T1.1 through T12.9 and FACT-01 through FACT-36

**Scope**

- Track B defines a producer-agnostic writer, deterministic validators, period/unit/slice/concept/verdict/read modules, and a parked-fact ledger.
- Implementation may begin in unaffected modules, but the packet lifecycle, source-ID/schema gaps, and owner boundary questions mean the affected Track B contracts are not implementation-ready. Nothing in this folder proves the system is running.
- The generic raw channel contract now exists; individual adapters, orchestration, retries, run ledger, and full production proof do not.

**FACT-01 through FACT-10 orientation**

- FACT-01: build one four-lane writer/enrichment/verdict/read stack for all supported event types.
- FACT-02: apply the separation-first law; exact code identity and fail-closed validators only, with no fuzzy snap/default.
- FACT-03: stay source-channel/model agnostic by building against one internal item contract. Public packet, prompt, model, and cadence belong to the channel/running layer.
- FACT-04: Track B does not own channel prompts, G1 display, Track A, Track C retirement, live/backfill orchestration, incremental refresh, the scanner implementation, or the dormant XBRL rider.
- FACT-05: deliver IDs, writer/CLI/shell, period resolver, unit resolver, slice menu, concept linker, verdict/DCM writer, reads, park ledger, validators, and tests.
- FACT-06: topic rules and the census own meaning; this file owns fact-side build; old substrate supplies proven mechanics; `99` is a historical cross-check.
- FACT-07: mark every reused behavior as reuse, override, add, drop, or running-layer work.
- FACT-08: preserve the audited substrate floor of 468 tests plus seven guards while adding failing-then-green tests for every override.
- FACT-09: the target flow is internal item -> normalize/resolve/fuse/validate -> write/enrich/verdict/read; the active contract now owns public channel input.
- FACT-10: preserve the verified code-root census and its near-identical path warning, but re-audit paths before implementation because the map is dated.

**Writer and identity**

- ID shape is `du:{safe_source_id}:{driver_name}:{fact_scope}` with the effective OD-8 collision overlay. The known fiscal adapter mapping changes `:` to `_`; the final internal contract still needs the complete escaping/delimiter recipe and fixed test vectors rather than leaving them implicit.
- One atomic write merges the node, sets `created` only on create, writes legal non-null fields, never erases a richer stored value on a sparse rerun, and logs changes/no-ops.
- A conflicting signature slot creates a sibling; only explicit repair may overwrite/correct it. Non-signature conflicts keep the approved last-write-wins-with-log behavior; sparse reruns still never null-clobber a richer value.
- Required edges, periods, concept/member writes, and constraints are part of the atomic path.
- Dry-run is default. Writes require the explicit environment gate. Sidecars are source-event namespaced.
- One source event is the fusion/collision locality. Missing surprise home siblings require re-extracting the whole event, not replaying only the orphan.

**Validator groups**

- Validate ID/scope construction; existing typed Driver; lane matrix; state lane; shape hints/grammar; signed value rules; stated-only fields; baseline enum; units/scaling/per-X; period-edge/scope symmetry; ISO date; quote; value-text lint; instant/duration; stated guidance movement midpoint; period-scope/sentinel pairing; and surprise composition/home/tense.
- All failures are deterministic and machine-readable. Semantic proposal does not bypass code.

**Modules**

- Period: carve the shared resolver, add strict Driver wrapper, exact-date and YTD/TTM handling, 21 tests, parity test, and write-once mismatch guard.
- Units: relocate the proven resolver, preserve its parity test, resolve each slot, add sequential unit and per-X hard failure.
- Slices: materialize the fresh frozen tables, point-in-time union menu, exact/provisional/elimination outcomes, kind ladder, member edge part, and no alias layer.
- Concepts: measurement guard, point-in-time company menu, pick/verify/veto, family inheritance, monitoring, subscription invocation, and XC-16 before scale.
- Verdict: build edge writer and DCM validation after open DCM details are decided.
- Reads: full key, family inheritance, source rank/ties/ET, rendering, strict PIT, member grouping, and raw/reconciled continuity views.

**Build order**

1. IDs, scope serialization, and unknown-axis round trip.
2. Period resolver and proofs.
3. Unit relocation, per-slot hints, and lint.
4. Writer, constraints, field validators, and lane fixtures.
5. CLI order: hints -> compose/validate surprise -> fuse -> period/slice/measurement -> units/canonical values -> collision -> ID -> validate -> write; add prior view, sidecar, park ledger, shell seam.
6. Optional old-Guidance dry-run QA fixture, never production replay.
7. Slice/menu tables from a fresh graph census.
8. Verdict writer and DCM.
9. Concept linker and rollout gates.
10. Read layer and golden tests.
11. Dual-producer probe when real channel/core producers exist.

**Acceptance**

- Resolver and parity gates.
- Synthetic fixtures for every lane and shape, including all OD-21 failure and positive cases.
- Concept backstop and point-in-time menu proof.
- At least two independent fact producers over a locked sample; measure field, state, and fact-presence disagreement. Threshold remains owner-set after calibration.
- Collapse/day-boundary/member grouping/raw-reconciled/backtest-live read tests.

### 6.3 Track C: old Guidance retirement, GI-01 through GI-04 and active v2.0

- Archive and retire the old Guidance graph, code, writers, readers, prompts, and source-status seams. Preserve its evidence.
- Do not mint production Drivers or DriverUpdates from old Guidance rows.
- Do not create a replay, `legacy_name_map`, mini-run, packet bridge, compatibility layer, dual labels, `regenerated_from`, or hidden old source.
- New names come through Track A/admission. New facts use Track B. Fresh guidance comes from source documents through the new channel/core process.
- Old rows may be QA evidence for recall, qname/member answers, regression, and resolver/read parity. Source plus current rules always wins.
- Current census evidence is 8,432 updates, 894 sources (532 Reports and 362 Transcripts), 548 anchors, and 237 periods — plus the archive-baseline evidence the export must also capture: 4,148 fact-level qnames and 460 member links (answer-key evidence only), and the warning that legacy `guidance_status` exists on only 24 of the 894 sources, so it is never a reliable run ledger. Re-census at retirement because these are 2026-07-03 counts.
- Preserve a restorable archive: every property/edge/anchor/period, code/prompts, source manifest/locators, hashes/counts, timestamp, git identity, and database identity.
- Retirement order: freeze/drain old writers; export and verify; scan all consumers; cut prediction/learner readers over or make them tolerate empty history; prove no old packet/read path remains; obtain approval for deletion; delete old nodes/edges and only orphan old periods; remove schema/code seams.
- Green gates require exact export counts and evidence, drained writers, no remaining consumers, no replay marker, acceptable empty-history behavior or explicit wait, owner acceptance of the temporary historical gap, and no production residue.
- Shared pure helpers may move under Track B ownership. Old Guidance remains an oracle or archive only.

### 6.4 Running layer still needed

The design currently has strong storage and partial adapter contracts, but not a complete operating system. The final runbook must still define and prove:

- source schedules and per-channel selection rules;
- all channel adapters and certifications, not only fiscal.ai;
- one central event/run ledger and returned channel outcomes;
- core ownership of parked facts, whole-event retries, and cursor updates;
- live and historical backfill orchestration;
- verdict production and DCM open decisions;
- full QA gates, alerting, budgets, and exact model policy;
- catalog-to-graph materialization and protected imports;
- prediction/learner/scanner cutover and empty-history behavior;
- incremental refresh, source-id immutability, atomic publish, and rule/finalizer hashes;
- Track C archive/retirement execution;
- production write approval and rollback/recovery checks.

The already-recorded refresh rules must also survive: fold base plus delta; freeze old-to-old decisions at every level; keep a source-id ledger; reopen SKIP while PARK stays terminal as specified; publish `_state.json` atomically; inherit the locked ruleset hash; use the industry-level fold allow-list; verify Transcript-ID immutability before the first run; re-run finalization with prior types frozen; keep latent bases out of fold inputs; and treat a separate finalizer-hash mismatch as a loud owner signal rather than automatic type invalidation.

### 6.5 Load-bearing implementation warnings to preserve

These belong once in `BUILD_AND_OPERATIONS.md`. They are verified hazards, not optional background.

**Track A / catalog build**

- Never consume a catalog without a green `validation_exit.json`, matching catalog/approved hashes, correct fold flag, and final/family checks where applicable.
- Old `.claude/plans/Drivers/runs/` catalogs and seeds carry old naming rules. They are calibration evidence only. Frozen raw chunks may be reused only as declared evaluation fixtures.
- The current reconcile command may not throw on a failed validation; the next sidecar check is load-bearing until hardening changes it.
- The old two-argument validator path can skip approval/variant checks with only a warning. Always pass the approved file; harden this path.
- Resume/repair “plan” functions can unlink stale files. Treat them as mutating operations.
- Menu jobs finish out of order. Resume by exact filenames, never by a presumed contiguous prefix.
- Long JSON lines may be truncated by a file-reading tool, and large agent writes may truncate. Use piece writes, counts, and h32 assertions exactly as specified.
- Workflow arguments may arrive as JSON strings. Keep the parse shim in every workflow.
- Fold parks are not visible in the short validator summary and do not automatically roll up. Inspect fold sidecars.
- `SAME_AS` precedence may intentionally resolve a direction conflict without a diff alarm. Do not “fix” that without a rule change.
- Standalone repair can downgrade a fold sidecar; only the governed tree flow restores and revalidates it.
- Old CAKE catalogs and hand-stamped synthetic sidecars are not trusted final artifacts. Re-cut fixtures under current rules.
- Source-manifest source counts count events, not KPI pseudo-sources. Old backfilled sidecar timestamps are weak provenance.
- Use environment-first graph configuration. A hard-coded Neo4j fallback exists in old fetch/resolve code and must not drive writes.
- Seven of 47 CAKE events produced zero evidence, including substantive 8-Ks. Keep the recall-floor counter and investigate zero-yield events.
- Return schemas must handle real nulls consistently; a string-only schema can reject valid model output.
- Subscription billing guards are required. Do not use metered SDK/CLI paths without approval. Start large fan-outs in a fresh five-hour window, resume per chunk, and use exact-call cache behavior where valid.

**Track B / fact build**

- In Neo4j, `SET x = null` removes a property. Validate before any SET and never let a sparse rerun erase a richer fact.
- DriverPeriod dates are on-create/write-once. A wrong first date does not self-correct; mismatch must hard-fail.
- The inherited period cascade may fail open on infrastructure errors. Log the degradation. The Driver wrapper still hard-fails an unresolved item.
- `calendar_override` is read too late in the old substrate; route market/calendar facts before fiscal cache branches.
- The pure old period builder can create a year-2000 month when fiscal year is missing. The Driver wrapper forbids this.
- The unit resolver calls private old Guidance helpers. Keep its parity test in permanent CI.
- A raw `$/barrel` can resolve dangerously without hints. The per-X name/unit hard failure is load-bearing.
- Concept vetoes C and D and the historical PIT menu query were spec-only when audited; they must be built before rollout.
- Old paths disagree on `<` versus `<=` and date-only cutoffs. DriverUpdate backtest/history reads use strict `< as_of`; write/menu visibility uses `<= event public time`.
- The concept in-menu check is exact string equality. Menu and model output must use the same qname prefix form.
- Existing graph quirks include `is_numeric` stored as string `'1'` and consolidated membership represented by null or empty arrays. Preserve both checks.
- Do not use bare Python `assert` for production validation because optimization can remove it.
- Both current `gp_` and deprecated period-id namespaces may exist. The new resolver emits only `gp_`.
- Old `/tmp` sidecars, member maps, and caches are ephemeral and may collide. Namespace Driver artifacts.
- Old concept experiment outputs point to a dead scratch directory. Revalidation must re-pull source data.
- The extraction worker snapshots allowed types at import; adding `driver` needs a restart. It also has guidance-specific summary/sidecar assumptions and a run-ledger whitelist that must gain Driver support.
- The worker's metered SDK entry is not an approved live Driver path. Use the active subscription contract unless separately approved.
- The historical Track B floor was 468 tests plus seven guards. Treat that as provenance, not proof that the unbuilt current stack already passes.

### 6.6 Evidence and counts worth keeping once

- The fixed-vocabulary Driver v1 rejected about 82% of otherwise useful names. The eager-reuse v2 merged distinct demand stories. These failures justify open vocabulary and erring toward separation.
- Unit evidence includes 117/117 main cases, 29/29 plus seven guards in the resolver proof, and three 33/33 naming/unit runs. This proves components, not production wiring.
- Current concept-link evidence includes a 31-company proof with zero wrong links among 249 accepted and zero wrong abstention labels among 1,178 checked, plus about 99.4% tail recall. A later 274-company validation reported 100% sampled precision, about 70% recall, and 98% three-run identity, with an incomplete hand list and a known “one wrong” tuning caveat. Keep the caveat beside the numbers.
- Signed experiment evidence currently establishes EXP-1, EXP-0, and EXP-2 results listed below. Do not infer EXP-3 through EXP-6 from the dated work order.

## 7. Detailed material that is not fully final

### 7.1 Admission Kernel v3.4: lock candidate with accepted parts

The full file is **not** one accepted production rule. Preserve this split:

**Accepted or separately owner-approved**

- Governed born-complete admission and first fact.
- Cheap roles never final-confirm identity, family, link, fact placement, eligibility, or quarantine.
- OD-18 synchronous risk-prefiltered ATTACH confirmation before write, with the exact refuse/escalate/re-coin/skip/park behavior in section 4.17.
- Confirmed-wrong `SAME_AS` and `CONTINUES_AS` quarantine paths, plus fact-level `disputed` recovery for a confirmed mis-attachment.
- OD-19 conditional token-subset gate and permanent refusal classes.
- OD-20 continuity.
- Role tiers are locked; exact model membership remains experiment-driven.

**Candidate architecture, still needing the named owner bundle/tests** *[UPDATE 2026-07-15: the bundle WAS ratified (owner, §16) — this list is preserved as the audit-time record; every gate/experiment named in it remains binding]*

- Anchor-first live kernel plus a seed/deep-clean tree.
- Blind candidate, code normalization/lint/suffix/collision/PIT top-K, then arms: ATTACH, ADOPT, CLAIM/LINK, CREATE, SKIP, and one UNSURE rejudge.
- Limited G1 view: exact plus bounded related candidates and safe badges/evidence; never full catalog, values, XBRL, latent names, future data, or hidden scores.
- Exact attach, reorder-only adopt, at-most-one claim, named retry/terminal park classes, one shared type/family resolver, and protected live nodes.
- LINK pair assembly, permanent code refusals, strong default-refuse five-check judge, high-blast second skeptic, reversible SAME_AS memo/head/cache, and CLAIM kept off until the named zero-wrong stage. CLAIM's strong-tier requirement is separate from OD-18.
- Frozen raw birth quotes and refuted negatives; no default evidence distillation; controlled refreeze only.
- Broad/established eligibility, live transaction freeze, mature full-evidence split review, validators V1-V14, rollout gauntlet, smoke-alarm immune system, falsifier/attach audits, and unapproved BASE_METRIC/family recovery propagation.
- Cross-company use only after broad/clean status. Exact launch thresholds and §15 owner bundle remain pending.

Do not call this whole architecture “ratified” merely because the title says v3.4 or a few later OD rules were inserted.

Two kernel sections must transfer whole at migration rather than be re-derived: §15.0's exact MVP split (day-1 core versus deferred-inert list, including the coverage rule that no-XBRL admission stays fenced until falsifier (v) ships) and §16's honest residuals — above all that **qualitative homonyms have no model-independent tripwire**, the design's own stated deepest worry.

### 7.2 XBRL Integration Design: final proposal, not final rule

The title says “FINAL DESIGN,” but the status says lock candidate pending owner ratification. The existing text-to-fact concept linker in section 4.15 remains current. The proposed XBRL-native materializer is dormant until approved.

Candidate bundle:

- Text remains the only path that creates Drivers and narrative facts.
- Deterministic code may materialize entity-scoped numeric metric facts only for an already admitted active company/Driver concept resolution.
- Covered facts require in-filing entity match, approved measurement fold, representable axes, allowed unit, exact period, and source-stated value. Non-GAAP, unlinked, qualitative, causal, guidance, and action material stays text-side. Units are a v1 whitelist — USD, shares, and USD-per-share — so eligible EPS/per-share facts ARE materialized, the per-X living in the name per NAME-13; every other unit (pure, other currencies, custom/divide units) skips and is counted.
- Materialize before text; text twins dedupe only on same event/head/period/slice/fold/value. Mismatch splits or parks.
- Filter company entity, numeric/non-nil facts, allowed USD/shares/USD-per-share units, precision conflicts, and full axis preservation. Count every skip.
- Prefer period-of-report facts; comparatives are backfill/restatement. Use shared exact period/slice/writer rules and immutable provenance.
- Resolve quarter/YTD/half/annual/TTM/monthly/exact range from actual dates, including 52/53-week behavior.
- Same-series exact XBRL wins the tie; same-day 8-K remains. Compatible upgrades use a repair lane and auditable UpgradeEvent. Fold-equivalent facts may remain separate but read together.
- Active/revoked ConceptResolution lifecycle, cohort exclusion, recovery/re-extraction, menu-evidence invariant, isolated kernel falsifier, and duplicate/miss ledger.
- Honest non-repair lanes for divergent periods/slices remain. P1-P17/P19 and ten document amendments require owner approval after EXP-1/EXP-6 evidence.

The dormant rider in `09` must stay dormant. Do not add `origin`, `xbrl_link`, empty-equals-GAAP folding, or XBRL producer rules before ratification.

### 7.3 Experiment program

- `FableExperimentPlan.md` defines **what** to test and does not change design.
- `FableExperimentWorkOrder.md` defines **how** to run it and supersedes the Plan only for execution details. It explicitly does not amend production law.
- EXP-0 qualifies graders.
- EXP-1 tests deterministic XBRL reality.
- EXP-2 tests reader model, chunk size, run count, and rule context.
- EXP-3 tests G1/router behavior.
- EXP-4 tests identity linking, type stamping, and families.
- EXP-5 tests the 24-field fact packet.
- EXP-6 tests text/XBRL convergence.
- Pre-register and hash-lock keys, grade once, keep point-in-time inputs, use subscription execution and exact model IDs, show ambiguity exhibits, record denominators, and do not retest a rejected mechanism without a named fix.
- The work order's exact 36-event/12-company corpus, key schemas, quotas, runners, prompts, scores, schedule, and accepted O1-O9/O16 choices are experiment execution details, not production decisions.
- The work order changes several Plan mechanics: synthetic/out-of-corpus cases, 8,000-character arm instead of paragraph arm, company split when time split is empty, and `du_worthy` rather than market significance. Preserve those as execution changes.
- Kernel owner rules supersede cheap-final-confirm and shared-miss-discount interpretations in old experiment text. Shared miss is measured/reported, not automatically discounted.
- The Plan's approximately 4,000 total / 1,500 strong figures are rough caps. WorkOrder section D4 records the later arithmetic refinement: about 3,600-4,300 calls before conditionals/F-C readers, about 1,900-2,100 strong calls, and a 6,000 global abort derived from the Plan's own 1.5x convention. Preserve both estimates and D4's explanation as execution history; this is not an unresolved owner design choice.

**Current signed repository evidence, which is newer than the stale folder headers:**

| Item | Current proved status |
|---|---|
| WP-0 bootstrap | DONE, 2026-07-09. Its live count replaces the WorkOrder's earlier estimate for run planning only. |
| EXP-1 | PASS and signed, 2026-07-09, including the owner-ratified O13 dimension-binding rule (explicit-dims positional pairing; typed dims dropped fail-closed, skip+count). This proves the experiment result, not the whole XBRL candidate. |
| EXP-0 | PASS and signed, 2026-07-10. The qualified grader is two independent `claude-sonnet-5` calls at `effort=high`; qualification binds the model-and-effort pair. `claude-opus-4-8` at high effort is the backup/escalation reference. |
| WP-FC-EDITS | DONE in commit `5db902f`, 2026-07-10; 260 tests passed and one skipped. Fold/tree truth-up and the full run remain. |
| WP-FA and O2 | Corpus complete and O2 signed, 2026-07-10. |
| K-reader v3 | LOCKED: 1,175 records, 2026-07-10. |
| EXP-2 | PASS and signed, 2026-07-11; adopted `claude-sonnet-5` at high effort, 40,000-character chunks, one run. |
| EXP-3 through EXP-6, remaining keys, WP-FC-RUN, F-C freeze | PENDING; no signed completion established. |

Provenance guard: `FableExperimentPlan.md` still matches its pinned SHA-256 `51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472`; do not add a status banner to that hash-pinned file. The current WorkOrder hash is `4911a22f187cff1ca30a4c5bd9e4ddf452de4d178379b4b441b9d69416ef33b3`, while `.claude/plans/Drivers/experiments/WORKORDER_STATUS.md` still labels `1586761a475683f40100e8740cfbe43773a94009a08c316198151a3e790b0501` as current v1.8. Record the actual run-time WorkOrder hash/version before any remaining run. Two recorded status-board gates also bind the remaining program: the ra_0007 carry-forward (kernel §6.1 judge-contract semantics review) is due **before K-pairs.v2 is drafted/adjudicated**, and the qualified grader identity is the (model, effort) pair for every downstream graded call. `.claude/plans/Drivers/experiments/HANDOVER_2026-07-12.md` is a dated operations snapshot, not the design front door; it predates OD-21 and the two packet contracts.

### 7.4 Bayes proposal

- This is explicitly unvetted and is not a Driver creation or storage instruction.
- Its central proposal is one company-event-return-window training row containing all Drivers, never one full return assigned to each Driver separately.
- It is post-outcome only and requires strict outcome-blind train/live parity.
- Derived learner outputs are versioned and must never mutate Driver, DriverUpdate, or verdict data.
- The Bayesian learner must beat simple and joint baselines and pass its five proof gates before promotion.
- Keep it in a proposal archive with a pointer from status. Do not import its structural or model choices into the final Driver plan without owner approval.

### 7.5 Driver Genesis discussion

- The discussion agrees on controlled evidence-bearing channels, one shared admission kernel, open vocabulary, source-backed first facts, and demand-driven creation.
- It does not agree on three triggers versus five doors, whether analyst/news is a channel or support source, how material actions enter, or the precise creation/update boundary.
- It has no owner lock and does not replace Track A, the frozen packet, or the active channel contract.
- Preserve it as rationale until final channel charters settle those differences; then archive it.

### 7.6 OD-5 change scanner recommendation

OD-5 is a tracked downstream recommendation, not an owner-approved Driver/DriverUpdate rule. Its proposed contract is a read-time, code-only consumer of collapsed series and point-in-time history. Proposed triggers are named state transitions, closed-shape numeric deltas over configurable per-unit-family thresholds, derived `narrowed`, and exact inequality of normalized extractive `value_text`. The proposed output is a notification/flag event, never a DriverUpdate or stored fact field; it uses no model and never reads realized returns. Preserve this recommendation for the later scanner design, but do not present it as final or built.

## 8. Complete replacement ledger

These are the 42 stable `95_Supersession.md` history rows. The dead rule is retained once for audit safety; current wording lives only at the final anchor. Do not renumber these rows.

| # | Subject | Dead rule | Current rule anchor |
|---:|---|---|---|
| 1 | Own company parts | Put brand/segment in Driver name | NAME-10/11, section 4.3 |
| 2 | Measurement | Put adjusted/diluted in name | NAME-14, FS-25, and OD-9, sections 4.3/4.9 |
| 3 | Per-X | Omit denominator or treat it as unit | NAME-13 and UNIT-08, sections 4.3/4.10 |
| 4 | What makes an update | Only a change qualifies | DU-01/03, sections 4.1/4.5 |
| 5 | Evidence count | Require more than two events | DU-01, sections 4.1/4.5 |
| 6 | Verdict size | `magnitude` | DU-22, section 4.14 |
| 7 | Verdict allocation | Force shares must total 100% | DU-22/23, section 4.14 |
| 8 | Verdict storage | Verdict node/property | DU-20/21, section 4.14 |
| 9 | Related flavors | No family link or merge as synonyms | MF-01..12, section 4.4 |
| 10 | Period model | Guidance-only period | PER-01..20, section 4.11 |
| 11 | Slice kinds | Four kinds plus `store_type` | FS-05..12, section 4.8 |
| 12 | Slice identity | XBRL member ID | FS-02/08 and XC-13..18, sections 4.7/4.8/4.15 |
| 13 | Concept linking | Curated dictionary | XC-01..18, section 4.15 |
| 14 | RavenPack | Driver vocabulary | DU-11, section 4.6 |
| 15 | Model default | Fable two-pass reader | Signed EXP-2, sections 6.1/7.3 |
| 16 | Number shapes | Stored `level_bound`; low-only point | DU field contract, section 4.12 |
| 17 | Qualitative value | No qualitative field | `value_text`, section 4.12 |
| 18 | Fact hash | DriverUpdate `evhash16` | DU identity/verdict rules, sections 4.7/4.14 |
| 19 | Confirmation | Confirmation enum | `company_confirmed`, section 4.12 |
| 20 | Non-GAAP guard | Name regex | XC guards, section 4.15 |
| 21 | Live reuse | Show catalog first | PIPE live reuse, section 6.1 |
| 22 | Concept invocation | SDK/OAuth | XC operating rule, sections 4.15/6.5 |
| 23 | Missing period | Quiet `gp_UNDEF` fallback | PER sentinels/fail-closed rule, section 4.11 |
| 24 | Metric expectation | Allow previous guidance baseline | Lane matrix, sections 4.12/4.13 |
| 25 | Whole-company slice | Store `slice=total` | FS-10/15, section 4.8 |
| 26 | Unit hints | One hint pair per item | Effective UNIT-04, section 4.10 |
| 27 | Slice label drift | Human alias files/confident alias | FS-19/read rule, sections 4.8/4.16 |
| 28 | Slice menu | Latest prior filing only | FS-14..18, section 4.8 |
| 29 | Bare fact type | Trust one classifier | DU-07/OD-2, sections 4.4/6.1 |
| 30 | Collision hash | Quote/value truncated equality hash | FS-03/OD-8, section 4.7 |
| 31 | Surprise arithmetic | Above=beat, below=miss, sign hard-fail | OD-13 and DU-10/16.2, sections 4.6/4.12 |
| 32 | Loss values | Positive loss magnitude/loss Drivers | OD-12, section 4.10 |
| 33 | Sequential percent | Treat all percent growth as YoY | OD-11, section 4.10 |
| 34 | Guidance history | Store derived movement; unclear amendment/DCM | OD-14 read rules, section 4.16 |
| 35 | Measurement tokens | Producer final tokens; qualifiers may drop | OD-9, section 4.9 |
| 36 | Unit grouping | Read-time family map/unknown absorption | OD-10, sections 4.10/4.16 |
| 37 | Slice recurrence | Use cross-company recurrence for identity | FS-22 retired, section 4.8 |
| 38 | Brand/slice test | External-brand heuristic/default slice | NAME-11, section 4.3 |
| 39 | Wrong `SAME_AS` | Never reopen automatically | Kernel recovery D4 / `95` #39 confirmed-wrong-edge quarantine, section 4.17 |
| 40 | Entity names | Ban every ticker/legal/person token | NAME-11 and NAME-16 #4, sections 4.3/6.1 |
| 41 | Token subset | Permanent automatic refusal | OD-19 conditional rule, section 4.17 |
| 42 | Surprise scope | Actual-only; no subtype slot | OD-21/FS-27, sections 4.7/4.11/4.12 |

### 8.1 Other additions and tracked items that are not reversals

These must also appear once in the final history/status file:

- Born-complete governed Driver creation with the first fact; latent base is the exact exception.
- OD-1 terminal suffix admission checks and memo.
- OD-2 metric-must-prove-itself finalization.
- OD-6 fixed 3,000-slot zero-wrong quality gate.
- The broader OD-7 live missing-Driver design remains a tracked recommendation; OD-2's narrower first-fact pin is already approved.
- OD-8 exact collision algorithm.
- OD-9 through OD-15 measurement, unit, sequential percent, signed values, polarity, chronology, and near-synonym race rules.
- OD-16 catalog-to-graph sync recommendation/open owner-tool work, including its unresolved conflict with frozen born-complete admission.
- OD-17 portion/population/residual/artifact rules.
- OD-18 strong flagged-ATTACH confirmation and disputed fact-placement recovery; CLAIM is separate and ships off.
- OD-19 conditional token-subset narrowing.
- OD-20 `CONTINUES_AS`.
- OD-21 three surprise types and scope slot.
- Frozen Candidate Fact Packet v1.0.
- Active raw Channel Contract and the split between channel input and internal core packet.
- Track C's full no-replay retirement reversal.

## 9. Current status map

### 9.1 Final rules that are not fully built or run

| Area | Remaining work |
|---|---|
| Track A | WP-FC-EDITS is proved in `5db902f`; preserve its result, apply the remaining OD-1/2/6 and fold/tree prompt mirrors, finish hardening/finalizer, resolve the born-complete/graph-sync boundary, run real folds/WP-FC-RUN, and pass the OD-6 fitness gate. |
| Units | UNIT-14 production wiring, validators, parity/replay checks. |
| Periods | PER-20 resolver build, 21 tests, Dec/non-Dec YTD/TTM proof, date and race guards. |
| Slices | Materialize/freeze fresh exact lists and point-in-time menu code. |
| Concept linker | Build missing vetoes/PIT query, decide XC-16 timing, run full universe safely. |
| Track B writer | Implement ID/writer/validator/CLI/park ledger and all OD-8/OD-21 behavior. |
| Live admission | Close the exact packet-lifecycle and atomic born-complete transaction recipes/tests. Separately ratify or narrow the candidate reuse/create routing and launch gates; preserve the broader kernel as candidate. |
| Experiment program | EXP-3 through EXP-6, remaining keys, WP-FC-RUN, and F-C freeze are pending evidence/build work; use signed artifacts for status. |
| Reads | Full-key, ET collapse, raw/reconciled, member grouping, continuity, PIT tests. |
| Verdict/DCM | Writer, producer, open DCM details, and read precedence tests. |
| Channels | Per-channel select/fetch adapters, certification, central outcomes/cursors/retries. |
| Production | Schedules, run ledger, backfill, QA, budgets, model policy, writes, recovery. |
| Track C | Re-census, archive, consumer cutover, delete approval, retirement gates. |
| Incremental refresh | Verify source-ID stability, implement frozen old-old behavior and atomic publish. |
| Scanner/learner/predictor | Define and execute downstream cutover and operating process. |

### 9.2 Truly open design or owner choices

Direct contract choices are listed once in section 10.2 rather than duplicated here.

- G1 live reuse display.
- Catalog target 796 versus older 786 and company lifecycle/dormancy/IPO absorption.
- Exact full model/cost policy outside the signed reader result.
- FS-23 cross-company slice-value comparison, excluding residuals.
- 8-K taxonomy. Amendment handling is already final under OD-14.
- DCM significance threshold, pure-macro source, and two-independent-catalyst case.
- XC-16 exact rollout timing and calculation-hierarchy implementation.
- Full XBRL-native materializer/report scope and its ten proposed amendments.
- Admission kernel candidate bundle/launch thresholds not separately ratified. *[RESOLVED 2026-07-15: bundle ratified by the owner (§16); launch thresholds remain experiment-gated as designed]*
- Track B dual-producer pass thresholds after first calibration.
- Non-USD unit expansion, if monitoring proves it is needed.
- Metric `value_text` and action `conditions` revisit triggers, only if their censuses fire.
- Final Driver Genesis channel charter questions.
- Guidance/archive history-gap acceptance at Track C execution.

### 9.3 Conditional items

- OD-19 token-subset judge path is inert until K-pairs.v2 portion-family wrong-same equals zero.
- OD-18's at-least-eight-company threshold, ESTABLISHED/non-ESTABLISHED scoping, outcomes, counters, and flagged-ATTACH path are fixed. The named `SAME_AS`/`CONTINUES_AS`/`disputed` recovery paths are accepted. D4 `SAME_AS` detector/prompt/retry/dashboard/schema details, broader kernel recovery including BASE_METRIC/family propagation, and broader rollout remain gated or candidate as labeled.
- Model roles are configuration; exact role membership changes require the stated experiment/owner gates.
- XBRL-native materialization and dormant field rider remain off until owner ratification. *[UPDATE 2026-07-15: ratification DONE (§16); both remain OFF until the P19 bars + hard pre-gates + EXP-6 — the gates did not move]*
- Optional multi-run concept stability and caching are add-only if monitoring justifies them.

### 9.4 Accepted safety tradeoffs and honest limits

- Over-splitting is expected and repairable; wrong merging is not accepted.
- Missing concept/member links are safe under-linking; wrong links are the cardinal failure.
- Prose-only slice-label drift may remain split.
- Latent base metrics may temporarily have no facts or concepts and are not visible/tradeable.
- Collision extraction noise may create a flagged sibling; ambiguous partial collision members may park.
- Concurrent exact names converge through `Driver.name` uniqueness and `MERGE`; only near-synonyms may over-split and later use the approved reversible link path.
- Fresh Guidance retirement can create a temporary production-history gap if the owner accepts it after archive/cutover proof.
- Measurement-label drift (“adjusted” versus “non-GAAP” restatements of one series) may split that series — a locked accepted loss, recoverable only as a read-time view; member-anchored grouping does not cover it.
- First-pass under-extraction is accepted at write time (no deterministic guard exists); it is measured at the dual-producer probe, and the no-null-clobber merge makes reruns fill rather than erase.
- A variant collapsed at a lower fold survives only as a name string, its evidence unioned into the representative — separable evidence is not recoverable for it, by design.
- Deeply collapsed non-suffixed cross-flavor fusions are a consciously accepted residual: each was judged with full evidence at link time, and only the suffixed half is deterministically catchable later.
- “Near 100%” and “100/100” are goals, not mathematical guarantees. Every claimed rate must name its sample and gate.
- Existing concept evidence is strong but does not prove universal zero error.

## 10. Problems that must be visible during consolidation

These are documentation problems or unresolved logic questions. This audit does not choose a new answer.

### 10.1 Direct stale-text problems

1. `00_Coverage.md` omits six later files, says 39 rather than 42 reversals, stops FS at 25, and predates the frozen packet/channel contract.
2. `01_Overview.md` still says its track map, authority map, and dashboard are unfinished.
3. `03` FS-03 still describes quote-plus-value/all-hashed collision behavior; OD-8 is current. FS-02/FS-19 retain alias wording; reversal 27 rejects it.
4. `04` UNIT-04 still says one hint pair; reversal 26 requires per-slot pairs.
5. `07` DU-02/DU-04 still says producers alone create and divide work; the channel/core split supersedes that wording. DU-13 through DU-18 are explicitly replaced by `09`.
6. `09` still mentions read-time alias files in legacy prose and calls a series-key family map adopted even though `series_unit` replaced it. Its dormant XBRL rider is correctly not active but easy to misread.
7. `10` PIPE-03 still permits KPI name-only evidence and lacks the born-complete/orphan/protected-sync wording. OD-1, OD-2, and OD-6 are not fully back-ported. OD-8 is not a Track A back-port. Old model defaults predate signed EXP-2, while the WP-FC-EDITS code batch has already landed.
8. `11` T3.4 and `12` FACT-12/17 still contain old collision rules. Their “producer” duties now mean internal core duties.
9. `12` FACT-17b is labeled public/producer-facing but now survives only as the internal decomposer-to-writer item. Its old prior-guide state language also predates read-derived movement.
10. `14_BuildReadiness.md` rows 1/2 are resolved by OD-8 and row 12 by OD-6; the file also says the whole packet/part 2 is unwritten after the frozen packet and raw channel contract. The running layer itself is still incomplete.
11. `15` says “three blocks” while numbering four, duplicates slice/measurement signals across Blocks 1/2, omits `source_type` from its local “six code fields” list because the envelope owns it, and retains a stale “needs owner confirm” heading after Part C was approved. Its Part C ④ “Robustness = already built” (the FACT-16/17 validator suite, park ledger, dry-run default) is a build-status overclaim: those are design-final, NOT built — the section 9.1 Track B writer row is the true status; read “built” as “fully specified.” Because the file is frozen, record these as status nits; do not silently edit it.
12. `66` has a current master/owner section followed by a stale older audit. Its newer section says Track C is written, while an older Group 3 paragraph still says it is unwritten; the older tail also calls the quality budget undefined. Some “OPEN-DOC” rows are now done, while OD-1/2/6 remain genuine Track A back-port debt.
13. `90` needs to say the generic channel contract exists while individual channels/runtime remain open; it also omits resolved OD-17 through OD-20 from its summary.
14. `95` is the 42-row explicit replacement ledger, not a list of every rejected idea. Its uniform “locked” presentation also overstates #15 model status, #39 operating detail, and #41 conditionality.
15. `99` is explicitly historical and internally contradicts itself on Guidance retirement. It repeats many dead rules and should not be mechanically copied.
16. `FableAdmissionKernelDesign.md` has stale version/date/footer metadata and mixes ratified inserts with pending §15 items.
17. `XBRLIntegrationDesign.md` says FINAL in the title while its status is pending owner ratification.
18. `FableExperimentPlan.md` says not run and the WorkOrder says assets are to be created, while signed repository artifacts show EXP-0/1/2 passed. Keep the Plan byte-identical because its pinned hash is still valid. The current WorkOrder hash is `4911a22f...`, but `.claude/plans/Drivers/experiments/WORKORDER_STATUS.md` still calls `1586761a...` current v1.8; record the actual version/hash before more runs.
19. `DriverPlan.html` is a non-authority study export with old file/reversal/field counts, old model wording, old open items, and a wholly unwritten “part 2” statement.
20. `FableContextPack.md` omits OD-17 through OD-21. `WorkflowContextPack.md` is a dated, non-authoritative code map and can archive only after its remaining fold/build-tree residue is preserved and its live kernel/WorkOrder citations are repaired. `.claude/plans/Drivers/experiments/HANDOVER_2026-07-12.md` is also stale and mislabels `FablePromptv2.md` as the current prompt.
21. The verified D-5 through D-13 back-port debt must remain explicit: XC-12 lacks the non-GAAP no-inheritance carve-out; FS-24 names a too-short read key; FS-03 blurs restatement write identity with read collapse; FS-04/PIPE-04 overstate “LLM never merges”; Track A omits the news-only-via-live-G2 consequence and protected import/orphan guard; overloaded terms still need a glossary; and the recorded D-13 pointer/count/naming nits remain unapplied.
22. The public adapter contract is readable but not yet a complete machine contract: the final build guide still needs exact field types/nullability, a versioned schema, complete outcome/reason codes, cursor/completeness record shapes, and certification fixtures.
23. The internal writer contract still needs a complete stored-field type/nullability table plus the full source-id escaping/delimiter recipe and fixed ID test vectors. Only the fiscal `:` to `_` mapping is currently explicit.
24. “Channel packet” and “Candidate Fact Packet” currently name different stages. The final files need stable names: raw adapter submission for the former and internal core packet for the latter.

### 10.2 Owner choices — ✅ ALL FIVE DECIDED BY OWNER 2026-07-15 (rulings recorded in place below; the question texts and verification notes are retained as the decision record)

1. **`company_confirmed` ownership:** the channel contract lists it among raw guidance content while Track B calls it producer/core-derived. Clarify whether the channel supplies evidence and core derives the boolean. Note for the ruling (fifth-round precision): `99` §3.18's Locked half covers the boolean's meaning and guidance-only scope. The skip wording (analyst/consensus/third-party/ambiguous) sits under its "Current Guidance extraction pipeline check" — LEGACY pipeline behavior, the reason legacy output maps to `company_confirmed=true`, not standing target law. `false` is the reserved positive meaning: a future explicitly-ALLOWED third-party/rumored guidance-like claim not confirmed by the company (`99` §3.18 reserved text · `09` §3 flag row · `11` T-census flag row); which claim classes are ever allowed, and the who-said-it derivation that would produce `false` rows, are explicitly part-2 / news-channel scope (`13`'s part-2 boundary → `12` §13 · `11` §15) — never a default for unclear evidence. Whatever side owns the boolean, unclear attribution must skip/park, not guess.
   **✅ OWNER-DECIDED 2026-07-15:** the CORE derives `company_confirmed` (matching `11`'s producer-derived who-said-it law); channels submit the quote plus who-said-it attribution EVIDENCE only. Unclear attribution is never stored as a guessed boolean — it is SKIPPED, and that disposition is this ruling's own content (2026-07-15), consistent with the legacy pipeline behavior recorded in `99` §3.18's pipeline check. PARK applies only under the general taxonomy when the blocker is clearable (an incomplete fetch), never as an alternative disposition for genuine ambiguity. Scope guard: this ruling does NOT extend to admitting clearly-attributed third-party guidance claims as `false`-flagged facts — `false` keeps its reserved explicitly-allowed-class meaning, and switching any such class on stays a part-2 / news-channel owner decision, not decided here. The one-word clarification ("company-confirmation evidence") is applied to the live `ChannelContract.md` at the Phase-3 contract review; pre-amendment bytes are preserved by the Phase-1 freeze manifest.
2. **Non-slice/elimination behavior:** the frozen fiscal adapter says park/log some NON_SLICE/elimination cases, while FS-12/OD-17 say exclude the artifact but keep the affected metric fact. Clarify whether only member enrichment parks or the whole fact parks. Precision for the ruling (verified): this is NOT a direct document conflict — FS-12/FS-20's skip/drop wording governs menus and axis classification; the frozen packet's PARK+log is the only text disposing an incoming FACT, and all three reviewers agree on the meaning half (never strip the tag and store the number as company-wide). The real choice is bookkeeping taxonomy: PARK (its rare-but-real drain = FS-20's auto-demotion of a wrongly-excluded member to provisional) versus terminal SKIP-with-reopen (cleaner ledgers; note NON_SLICE-axis cases have no runtime drain at all — only the offline re-vet, ISS-15). Either preserves meaning; changing the frozen packet's PARK wording requires an owner amendment.
   **✅ OWNER-DECIDED 2026-07-15: no change.** The frozen packet's PARK+log stands for a fact whose measured population IS an accounting construct — never strip the tag, never write it as company-wide; FS-20's auto-demotion remains the drain. A prose fact citing a construct as the mechanism writes on the affected real metric per OD-17(c). A later PARK→SKIP re-classification remains available as a non-identity bookkeeping change if parked-ledger clutter ever warrants it.
3. **Catalog graph sync boundary:** the frozen packet rejects general factless seeding, while OD-16 recommends materializing every finalized Track A record as a Driver before facts. The frozen rejection is general; latent base anchors are its only explicit exception. The owner must choose or narrow this boundary, and OD-16 remains a recommendation until then. The rejection's own rationale targets evidence-FREE cards, while gauntleted seed records carry birth quotes — so two coherent resolutions exist, both requiring the owner: (a) allow evidence-bearing gauntleted-catalog sync (narrows the frozen rejection to quote-less names; keeps OD-16 as specced); (b) keep the catalog OFFLINE as artifact + retrieval source — exactly how the experiment program already runs it, zero graph nodes — and create each graph Driver lazily, born-complete at its first fact (satisfies the frozen text literally; amends OD-16's materialize-all recommendation; requires the admission layer to create the node in the same write when an ATTACH targets a card with no node yet). Openness, characterized precisely (fifth-round correction): under the frozen letter — `15`'s UNIFICATION ("every new Driver arrives WITH its first proven DriverUpdate"; on CREATE the same packet's Block 2 becomes the first DriverUpdate), born-complete STANDS with latent bases the only empty-node exception, and Part C superseding the open list — resolution (b) was already the standing DEFAULT, and OD-16 (a recommendation pinned 2026-07-06, never owner-approved per `66` §0.R's closing) could not license pre-fact nodes against it: an evidence-bearing card is still factless until its Block-2 fact writes. What remained the owner's was the amend-or-ratify call — (a) stayed a coherent AMENDMENT request because the rejection's stated rationale attacks evidence-free/name-only cards. The 2026-07-15 ruling ratified the default and retired the contrary recommendation.
   **✅ OWNER-DECIDED 2026-07-15: resolution (b).** The finalized catalog remains an OFFLINE artifact and retrieval source (exactly how the experiment program already operates); graph Driver nodes are created lazily, **born-complete at their first fact**; latent base anchors remain the only empty-node exception. OD-16's sync recommendation is narrowed accordingly — no materialize-all pre-fact sync; its protected-input guard survives for whatever sync step ultimately exists. The lazy-create write mechanics (node created in the same write when an ATTACH targets a card with no node yet) are specified at the OD-7/live-admission pass.
4. **Non-dimensional XBRL packet shape:** the active Channel Contract requires concept qname, axis, and member together when XBRL is present, but consolidated XBRL facts can have concept/context without a dimensional axis/member. Clarify whether such facts may send concept plus context with null dimension fields, or whether omitting their concept enrichment is intentional. Do not silently relax the active contract. Amendment refinement all reviewers now endorse: concept qname + exact context always required; the channel asserts a VERIFIED-empty dimension list explicitly (`dimensions=[]`) so a missed extraction can never masquerade as consolidated; every supplied dimension carries BOTH axis and member; never fragments. The same clarification should ride into the frozen packet's XBRL row in the same owner-amendment batch.
   **✅ OWNER-DECIDED 2026-07-15: amendment APPROVED**, one batch covering the active `ChannelContract.md` §3 XBRL row and the frozen packet's XBRL rows, with this exact meaning: *"When XBRL-tagged: concept qname + the EXACT context (start/end dates, instant-vs-duration) — always. The channel asserts a VERIFIED-empty dimension list explicitly (`dimensions=[]`); a missed extraction must never masquerade as consolidated. Every supplied dimension carries BOTH axis and member. Never fragments."* Applied at the Phase-3 contract review; pre-amendment bytes preserved by the Phase-1 freeze manifest.
5. **First-fact guard versus bare guidance (latent until live admission wires):** the owner-approved OD-2 supporting pin parks a zero-fact Driver's first fact when its stored `driver_state` is `unknown`, while OD-14 stores every bare (movement-unstated) guide as `unknown`. Composed literally, a NEW guidance Driver born from a bare numeric guide always parks until a source-stated movement arrives — and a `guidance_vs_consensus` surprise then also parks with its missing home sibling. All fail-closed and self-consistent, but potentially heavy parking on new guidance families. One observation for the owner's live-admission (OD-7) pass, raised as a question only: a terminal-suffix guidance Driver's lane is already proven by OD-1's two independent checks rather than by its first fact, so the owner may wish to scope the first-fact guard accordingly — or accept the parking as designed. No rule is changed here. Two scoping notes for the ruling (verified): the same logic covers `_surprise` — also suffix-proven via OD-1, and a numberless grounded surprise stores `unknown` by locked rule, so a NEW surprise Driver's first fact can park identically; a guidance-only loosening leaves that rarer residual. And any "write the companion surprise in the same database transaction" wording is an implementation suggestion only — the locked requirement is same-EVENT/CLI-BATCH sibling validation (FACT-16 #18c), with idempotent re-runs as the crash-recovery posture, not multi-fact transactions.
   **✅ OWNER-DECIDED 2026-07-15: the OD-2 first-fact lane-exercise guard is SCOPED to bare (non-suffix-proven) names.** Terminal-suffix `_guidance` and `_surprise` Drivers — whose lane is already proven by OD-1's two independent admission checks — may be born with an `unknown`-state first fact; the read layer derives `introduced`/movement per OD-14. The guard stands unchanged for bare names. Companion-surprise validation stays same-event-batch per FACT-16 #18c; no same-transaction mandate. This is a scoped owner amendment to the OD-2 supporting pin, recorded here per the no-pre-archive-source-edits rule; it rides into the new files at migration.

### 10.3 Missing contract or build recipes

These gaps need exact wording and tests, but they do not authorize a new design choice during consolidation.

1. **Packet lifecycle:** Block 1 proposes a name/type signal before admission, while Block 2 describes an admitted Driver/final fact. State exactly when the strong admission decision stamps the permanent type and how the blocks hand off without treating a proposal as final.
2. **Born-complete transaction:** frozen law says a new Driver is created with its first fact, while the detailed atomic CREATE transaction lives inside a candidate kernel. State the atomic write and failure behavior without ratifying the rest of that kernel.
3. **Source identity namespaces:** only the fiscal `:` to `_` conversion is explicit. Define collision-safe cross-channel namespaces, the complete escaping/delimiter law, and fixed test vectors before the ID contract is implementation-ready.

### 10.4 Boundaries already resolved by later authority

- Core owns parked retry work. The channel owns its cursor/completeness record and the returned event outcome. A missing surprise sibling causes whole-event re-extraction, never orphan-only replay.
- Experiment budget arithmetic is a recorded WorkOrder D4 refinement under the Plan's 1.5x convention, not an owner design question; preserve both estimates and the run-time cap history.

- Fiscal.ai live facts map to an existing Report/Event and store the true `8k`, `10q`, or `10k` source type. Offline Track A `fiscal.ai-kpi` evidence is a separate catalog input, not a DriverUpdate channel type.
- Every DriverUpdate remains source-event-based and uses `FROM_SOURCE`; News is the macro/news source when present. A DCM is an optional verdict target only, and a pure-macro fact without a source stays parked.
- Amendments are new facts at their public time under OD-14. Only the optional 8-K routing taxonomy remains open.
- Exact concurrent Driver names converge through the unique `Driver.name` plus `MERGE`; only near-synonyms may remain over-split.
- Track A remains active because no newer file cancels it. The whole Admission Kernel and XBRL materializer bundles remain candidates unless separately ratified.

## 11. File-by-file disposition map

Every source file has a destination. “Archive” means only after the zero-loss checks in section 14.

| File | Present role/status | Canonical destination | Later disposition |
|---|---|---|---|
| `00_Coverage.md` | Stale coverage map | `STATUS_AND_HISTORY` source/archive manifest | Archive original |
| `01_Overview.md` | Final mission, unfinished navigation | `FINAL_DESIGN` opening | Archive original |
| `02_DriverCatalog.md` | Final naming authority | `FINAL_DESIGN` naming | Archive original |
| `03_Slices_FactScope.md` | Final identity/slice/measurement/continuity with stale clauses | `FINAL_DESIGN` scope, with explicit approved overlays | Archive original |
| `04_Units.md` | Final unit law with stale UNIT-04 | `FINAL_DESIGN` units | Archive original |
| `05_Periods.md` | Final period law, build pending | `FINAL_DESIGN`; build steps in `BUILD_AND_OPERATIONS` | Archive original |
| `06_MetricFamily.md` | Final family law | `FINAL_DESIGN` families | Archive original |
| `07_DriverUpdate.md` | Final lane/state/verdict parts plus replaced field section | `FINAL_DESIGN` current parts; history in status | Archive original |
| `08_XBRL_ConceptLinking.md` | Final text-fact concept linker | `FINAL_DESIGN`; rollout in build | Archive original |
| `09_DriverUpdate_Fields.md` | Final 24-field/matrix/read authority | `FINAL_DESIGN` fact contract | Archive original |
| `10_BuildPipeline.md` | Track A design/build manual, unproved | `BUILD_AND_OPERATIONS` Track A | Archive original |
| `11_TrackB_DriverUpdate_Census.md` | Normative census, duplicates 09/12 | Final rules to `FINAL_DESIGN`; gates to build | Archive original |
| `12_TrackB_FactPipeline.md` | Track B build manual, public boundary stale | `BUILD_AND_OPERATIONS` Track B/internal packet | Archive original |
| `13_TrackC_GuidanceIntegration.md` | Active no-replay retirement plan | `BUILD_AND_OPERATIONS` Track C | Archive original |
| `13_Track_RetiredDesign.md` | Explicitly retired replay plan | History/archive only; no live mechanics | Archive original intact, with one status pointer to its still-useful non-replay analysis for the later running layer: the live bundle-read inclusive-`<=` rationale at `pit=filed_8k` (GI-31), the 894-source reachability audit, and the four stated-mid outlier rows |
| `14_BuildReadiness.md` | Non-authority checklist, partly stale | Current gaps/gates to build/status | Archive original |
| `15_CandidateFactPacket.md` | Frozen owner-approved internal packet | Byte-identical, versioned, hash-checked block in `BUILD_AND_OPERATIONS` | Keep as a temporary fifth live file until the owner permits relocation and the frozen banner/hash are proved; then archive original unchanged |
| `66_IssuesToBeHandled.md` | Current owner blocks plus stale old tail | Final atoms to `FINAL_DESIGN`; status/history elsewhere | Archive original |
| `90_OpenItems.md` | Thin status dashboard, needs refresh | `STATUS_AND_HISTORY` | Archive original |
| `95_Supersession.md` | Exact 42-row history authority | `STATUS_AND_HISTORY` replacement ledger | Archive original |
| `99_Codex_Decision_Audit.md` | Historical loss-prevention audit | Only unique build facts to build/history | Archive original wholesale |
| `BayesProposal.md` | Explicitly unvetted learner proposal | One status pointer | Archive under proposals |
| `ChannelContract.md` | Active public raw boundary | Keep as one of four live files after issue review | Keep live; snapshot old bytes in archive |
| `DriverGenesisRestructure.md` | Unapproved deliberation/rationale | Open charter questions in status | Archive once every open question/rationale pointer is preserved; no settlement required |
| `DriverPlan.html` | Stale non-authority study deck | None; regenerate later only from live docs | Archive original |
| `FableAdmissionKernelDesign.md` | Candidate architecture plus accepted inserts | Accepted atoms to final/build; pending bundle in build/status | **DONE: RATIFIED 2026-07-15 → fully integrated (BUILD §8.1) → original archived byte-verified** |
| `FableContextPack.md` | Non-authority navigation, stale | No rule destination; source map to status | Archive original |
| `FableExperimentPlan.md` | Hash-pinned what-to-test plan; header status stale | `BUILD_AND_OPERATIONS` experiment section | Keep byte-identical until the program is migrated; archive after its exact rules/hash and signed status pointers are preserved |
| `FableExperimentWorkOrder.md` | Execution runbook with later mechanics and stale status | `BUILD_AND_OPERATIONS`; live status from signed artifacts | Preserve exact work packages, D4 budget refinement, and current hash; archive after migration, without editing the pinned Plan |
| `FablePrompt.md` | Executed kernel brief, no design authority | Provenance entry only | Archive original |
| `FablePromptv2.md` | Separate executed XBRL brief, not replacement prompt | Provenance entry only | Archive original |
| `WorkflowContextPack.md` | Dated non-authority code map | Re-audit live code; preserve only still-current fold/build-tree residue and repair inbound links | Archive original after those checks |
| `XBRLIntegrationDesign.md` | Pending XBRL-native candidate | Candidate section in build/status | **DONE: RATIFIED 2026-07-15 → fully integrated (BUILD §8.2) → original archived byte-verified** |

`CONSOLIDATION.md` itself should move into the same dated audit archive after the four live files pass review. It should not become a fifth source of rules.

## 12. Recommended four-file final set

This is the smallest complete target. It assumes the owner permits the frozen Candidate Fact Packet to move byte-identically into the build guide with its version, banner, and SHA-256 preserved. Until that approval and hash check, keep `15_CandidateFactPacket.md` unchanged as a temporary fifth live file; do not silently rewrite or absorb it.

### 12.1 `FINAL_DESIGN.md` — sole front door and rulebook

Exact contents:

1. Status/date/authority banner and reading order.
2. Plain glossary and graph/flow picture.
3. Mission, safety law, point-in-time law, and code/model boundary.
4. Driver naming NAME-01 through NAME-19.
5. Four types, state lanes, family links, and admission/birth law.
6. Fact identity/scope/collision, slices, measurement, continuity/recovery.
7. Units/signed values/series unit and periods.
8. Exact 24 fields, shapes, per-lane matrix, edges, verdict, and DCM.
9. Current text-fact XBRL concept/member enrichment.
10. Read/collapse/render/PIT/reconciled rules.
11. Generated, non-authoritative status tags for build-pending/conditional/open items, each linked to its owning status row.

It owns rule meaning. Other live files reference rule IDs and do not restate the rule in different words.

### 12.2 `ChannelContract.md` — one small public boundary

Keep one standalone contract because every adapter must read it and nothing else before submitting. It contains only:

1. channel duties and forbidden duties;
2. event envelope and raw candidate fields;
3. order/idempotency/outcomes;
4. cursor/completeness/reopen rules;
5. select/fetch/submit certification;
6. one pointer to the internal packet in the build file.

Resolve its confirmation, schema, and source-identity gaps before calling it implementation-ready. Cursor/outcome versus parked-work ownership is already settled in section 10.4. The Fiscal.ai document-source mapping is also settled. Do not copy the full Driver rulebook into it.

### 12.3 `BUILD_AND_OPERATIONS.md` — one implementation and run guide

Exact contents:

1. Generated, non-authoritative status banner: design, code, tests, and production run shown separately and linked to the owning dashboard.
2. Channel raw submission -> shared decomposer -> internal Candidate Fact Packet -> admission -> writer flow.
3. Exact frozen packet blocks and decomposition order, preserved byte-for-byte with version, frozen banner, and source hash.
4. Track A stages, artifacts, constants, guards, finalization, gates, and build order.
5. Track B modules, internal item contract, validators, build order, and acceptance.
6. Track C archive, cutover, retirement order, and green gates.
7. Runtime schedules, adapters, central ledger, retries, backfill, QA, model/cost policy, recovery, and downstream cutover.
8. Candidate Admission Kernel and XBRL materializer sections, each clearly marked accepted parts versus pending bundle.
9. Experiment plan/work order, signed current status, remaining gates, and evidence paths.
10. Incremental refresh and scanner work.

It owns procedures. It references FINAL rule IDs instead of re-explaining their meaning.

### 12.4 `STATUS_AND_HISTORY.md` — one mutable dashboard and trail

Exact contents:

1. One-page status dashboard by design/code/test/run.
2. Final/build-pending/conditional/open/candidate/retired lists.
3. All 42 stable supersession IDs as terse topic/status/final-anchor rows plus final additions; live rule wording stays in `FINAL_DESIGN.md` rather than being copied here.
4. Current signed experiment decisions and remaining gates.
5. Known documentation/logic questions.
6. Full source-to-new-anchor crosswalk.
7. Archive manifest: original path, status, bytes, lines, SHA-256, git commit/blob or untracked timestamp, replacement anchor.
8. Evidence/rejected-alternative pointers, including Bayes and prompts.

It owns status and history, not live rule prose.

### 12.5 One-copy rule

- Semantic Driver/DriverUpdate rule meaning exists only in `FINAL_DESIGN.md`.
- Public adapter duties and raw submission fields exist only in `ChannelContract.md`.
- Internal schemas, build steps, tests, and run procedures exist only in `BUILD_AND_OPERATIONS.md`.
- Status, terse replacement pointers, old rules, and evidence pointers exist only in `STATUS_AND_HISTORY.md`. Any status shown in another live file is a generated, read-only summary linked to this source.
- Cross-references use stable IDs/anchors, never pasted paragraphs.
- Until the frozen packet relocation is explicitly approved, its source file is a temporary exception to the four-file root and one-copy target — as are the two experiment files: the hash-pinned `FableExperimentPlan.md` + `FableExperimentWorkOrder.md` (live until the experiment program migrates). *(Round-15 note: the two former candidates were ratified 2026-07-15, fully integrated, and archived — no longer root exceptions.)*
- A status change edits the dashboard and, only if rule meaning changed through owner approval, the one owning rule section plus a new supersession entry.
- Generated study pages are outputs, never authority.

## 13. Safe consolidation and archive plan

No move or rewrite should happen until the user approves this plan.

### Phase 1: freeze and account

1. Freeze the current 33 source files and record SHA-256, byte count, line count, git blob/last commit, and untracked timestamp where needed.
2. Commit or otherwise preserve the three untracked source files before moving them, so their provenance is not lost.
3. Create an atom ledger with: stable rule ID, exact meaning, status, effective date, owner source, superseded source, final file/anchor, and evidence pointer.
4. Add every unnumbered contract clause and candidate item to the same ledger.
5. Use one editor and one reviewable migration commit per phase. Do not back-port or rewrite the old source set first; it is the unchanged evidence baseline.

### Phase 2: resolve only documentation blockers

6. Put the owner choices from section 10.2 and missing recipes from section 10.3 into the new status/build files. An unanswered item does not block byte-preserving archive when it is copied exactly as open, but the affected contract must not be called implementation-ready.
   Interim hazard, stated plainly: because sources are not edited before archive, the known stale prose (section 10.1, especially the OD-8 collision text in `03`/`11`/`12`, per-slot hints in `04`, and expectation-baseline wording in `09 §8`/`07 §D`) formally wins for anyone reading a single old file until `FINAL_DESIGN.md` exists. Any build or agent work started in that window must read `66 §0.2-B` and this section 10.1 first — the experiment program already encodes this discipline in its implementer protocol.
7. Leave every broader open/candidate item open if the owner does not decide it; consolidation does not require promotion or resolution.
8. Re-audit live code paths before preserving the remaining fold/build-tree residue from `WorkflowContextPack.md`.
9. Read signed experiment `decision.json` artifacts to generate run status. Keep the hash-pinned Plan unchanged, record the current WorkOrder hash, and never copy stale Plan/WorkOrder/Handover status as current.

### Phase 3: write the four live files

10. Build `FINAL_DESIGN.md` from the atom ledger, retaining stable rule IDs and exact enums/validators.
11. Review the small `ChannelContract.md`; call it implementation-ready only after its direct boundary/schema gaps are closed, otherwise keep those blockers explicit.
12. Build `BUILD_AND_OPERATIONS.md` with one internal packet contract and honest implementation status. Move the frozen packet only with explicit owner approval and a byte/hash proof; otherwise keep its source file live temporarily.
13. Build `STATUS_AND_HISTORY.md` last so every source row points to a real final anchor.
14. Add a front-door reading order and reciprocal links among the four target files.

### Phase 4: prove zero loss and no drift

15. Run every check in section 14.
16. Build a mapping for every old `(file, section/rule ID)` to its new anchor. Verified 2026-07-15 external-citation scans over `.claude`, by pattern: **12** files cite exact FinalDesign filenames (the verified inbound-citation set — experiments board/handover/exhibits/keys/harness plus, load-bearing, the freshly committed engine prompts `workflows/menu_build.js`, `reconcile.js`, and `gate.js`, whose inlined rulebooks cite `02_DriverCatalog.md` as verbatim provenance); filename-stem scans reach **21**, and adding the bare word “FinalDesign” reaches **22**, of which at least one is a name-collision false positive (`INDEX.md` matches only via `WIP/IncrementalRefresh_FinalDesign.md`). Treat 12 as the confirmed rewrite set and the wider scans as the safety sweep; re-run both at migration time and update or validate every hit before moving sources. The engine-prompt provenance citations must stay resolvable, or their prompt-mirror checks must be re-pointed in the same change.
17. Have a new bot, with no chat context, perform the blank-context exercises.
18. Have the owner review only changed wording, open conflict handling, and candidate status; do not ask them to re-read duplicated prose.
19. Freeze hashes of the four target files, any temporary frozen fifth file, and the completed crosswalk.

### Phase 5: archive atomically

> **⚡ PHASE-5 EXECUTION CARD (round 17 — compaction-proof; assumes ZERO chat context; supersedes nothing, it OPERATIONALIZES steps 20-25 below). Precondition: the owner's explicit "GO phase 5".**
>
> **A. The exact 27 movers (33 manifest files − 4 stayers − 2 already-archived):** `00_Coverage.md` · `01_Overview.md` · `02_DriverCatalog.md` · `03_Slices_FactScope.md` · `04_Units.md` · `05_Periods.md` · `06_MetricFamily.md` · `07_DriverUpdate.md` · `08_XBRL_ConceptLinking.md` · `09_DriverUpdate_Fields.md` · `10_BuildPipeline.md` · `11_TrackB_DriverUpdate_Census.md` · `12_TrackB_FactPipeline.md` · `13_TrackC_GuidanceIntegration.md` · `13_Track_RetiredDesign.md` · `14_BuildReadiness.md` · `66_IssuesToBeHandled.md` · `90_OpenItems.md` · `95_Supersession.md` · `99_Codex_Decision_Audit.md` · `BayesProposal.md` · `DriverGenesisRestructure.md` · `DriverPlan.html` · `FableContextPack.md` · `FablePrompt.md` · `FablePromptv2.md` · `WorkflowContextPack.md`. The 4 stayers: `ChannelContract.md`, `15_CandidateFactPacket.md`, `FableExperimentPlan.md`, `FableExperimentWorkOrder.md`.
> **B. Order of operations:** (1) snapshots FIRST: `git show 49f1cd8:.claude/plans/Drivers/FinalDesign/ChannelContract.md > archive/2026-07-15_pre-consolidation/ChannelContract.pre-amendment.md` and the same for `15_CandidateFactPacket.pre-amendment.md` — verify each sha equals its MANIFEST value; then `cp FableExperimentWorkOrder.md archive/2026-07-15_pre-consolidation/FableExperimentWorkOrder.md` (verified 2026-07-15: the live file is STILL at its frozen bytes, sha8 `4911a22f` — copy BEFORE any 21c edit). (2) the 21b WorkflowContextPack re-audit (criteria in C). (3) the 21c WorkOrder citation re-point + re-record its new sha on `experiments/WORKORDER_STATUS.md` and in §16 — **including its line-14 authority sentence: "(… — still candidates under test)" must become "(ratified working designs, owner 2026-07-15 — operative mechanics in BUILD §8.1/§8.2; gates unchanged)".** (4) `git mv` each of the 27 into the archive; sha-verify each move equals its manifest hash. (5) update the archive README per step 22's spec. (6) the step-23 link sweep over the 12 citers (list in D). (7) the step-24 root check: exactly `FINAL_DESIGN.md`, `ChannelContract.md`, `BUILD_AND_OPERATIONS.md`, `STATUS_AND_HISTORY.md`, `15_CandidateFactPacket.md`, `FableExperimentPlan.md`, `FableExperimentWorkOrder.md` + `archive/`. (8) the step-24b reader test — the UNMODIFIED official §14.3 ten; store the record DURABLY IN THE REPO (a `READER_TEST_RECORD_<date>.md` beside the manifest in the archive dir: agent id, the full prompt, the full answers with citations, and the full tested hashes — machine-local `~/.claude` paths are not portable evidence). (9) the step-25 verification commit + push. (10) LAST: `git mv CONSOLIDATION.md archive/2026-07-15_pre-consolidation/` (per §11 — after the live files passed review), final commit + push.
> **C. The 21b re-audit criteria (pass/fail, previously unwritten):** grep `WorkflowContextPack.md` for every code path/behavior claim it makes (`workflows/*.js`, `scripts/**`, run-layout paths); verdict each claim EXISTS-AND-TRUE / STALE; any still-current fold/build-tree residue that is LOAD-BEARING and not yet carried in BUILD §4 gets carried there (one owning place) before the file moves; its inbound/outbound links repaired or recorded as historical. PASS = every claim verdicted + zero un-carried load-bearing residue.
> **D. The 12 inbound citers (regenerated 2026-07-15, by path — re-run the scan at execution; all under `.claude/plans/Drivers/`):** `evolution.md` · `experiments/FABLE_INCORPORATION_PACKAGE_2026-07-11.md` · `experiments/FABLE_LOCK_BLIND_REVIEW_TRACKER_2026-07-10.md` · `experiments/FABLE_LOCK_BLIND_VERDICT_2026-07-10.md` · `experiments/HANDOVER_2026-07-12.md` · `experiments/keys/K-reader/protocol.md` · `experiments/WORKORDER_STATUS.md` · `experiments/WP_FC_EDITS_review_baseline_e9127c02.md` · `experiments/exp2_reader/runs/2026-07-11T19-40-47Z_exp2/local_artifacts/RULES_full.txt` (a frozen run artifact — annotate, never rewrite a run artifact; note beside it instead) · `workflows/gate.js` · `workflows/menu_build.js` · `workflows/reconcile.js` (the three engine prompts cite `02_DriverCatalog.md` as verbatim provenance — re-point to the archive path or FINAL_DESIGN §3, keeping their prompt-mirror checks resolvable). Scan command: `grep -rl -E "(02_DriverCatalog|03_Slices_FactScope|09_DriverUpdate_Fields|12_TrackB_FactPipeline|15_CandidateFactPacket|FableExperimentPlan|FableExperimentWorkOrder|FableAdmissionKernelDesign|XBRLIntegrationDesign|10_BuildPipeline|11_TrackB_DriverUpdate|66_IssuesToBeHandled|95_Supersession|99_Codex_Decision_Audit)\.md" .claude/plans/Drivers --exclude-dir=FinalDesign` (+ the stem/bare-word sweeps per STATUS §7).
> **E. Hash law (one rule):** archived snapshots + the 27 moves verify against the Phase-1 MANIFEST; the live amended files verify against the CURRENT §16 freeze (round-16 full-hash block above); any later archival of a live-continuing file uses a VERSIONED filename and verifies against the then-current freeze.

20. Create `.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/` with a README that says **non-authority historical snapshot**. Open/candidate decisions do not prevent this byte-preserving move once their exact status and pointers survive.
21. Move the exact original sources there without preliminary wording edits, preserving filenames and bytes — **the exact arithmetic (post-INT-5, round 14 — the two ratified designs have ALREADY moved): REMAINING = 27 MOVES + 3 SNAPSHOT COPIES + 1 DEFERRED (the Plan) + the live-edited WorkOrder. End state at the root: SEVEN files (the four live files + the frozen packet + the Plan + the WorkOrder) + `archive/`.** FOUR of the remaining sources stay at the root: `ChannelContract.md` (live 4th file) and `15_CandidateFactPacket.md` (temporary 5th) — each gets a PRE-AMENDMENT SNAPSHOT COPY into the archive, reconstructed from git commit `49f1cd8` and verified against the Phase-1 MANIFEST hashes — plus `FableExperimentWorkOrder.md`, which stays live BUT is EDITED by step 21c, so its FROZEN ORIGINAL is snapshot-archived FIRST (manifest-verified) before any rewrite — plus `FableExperimentPlan.md` (hash-pinned; live until EXP-3..6 and the remaining work packages migrate). *(The two ratified designs already archived 2026-07-15 after integration + the archive-gate test — no longer part of this step.)* **Versioned-path rule:** a LATER archival of any live-continuing file lands at a VERSIONED filename beside its earlier snapshot (e.g. `15_CandidateFactPacket.v1.1-post-amendments.md`) — an archived snapshot is never overwritten. **Hash rule, one consistent law:** archive snapshots verify against the MANIFEST (pre-amendment baselines); the LIVE amended files verify against the current §16 freeze; any LATER archival of a live-continuing file (e.g. the packet at its approved relocation) verifies against the then-current freeze, with the manifest baseline retained alongside.
21b. **Pre-step (from step 8, still unexecuted):** re-audit live code paths for `WorkflowContextPack.md`'s remaining fold/build-tree residue and repair its inbound links — that file archives ONLY after this check.
21c. The WorkOrder cites source filenames for verbatim rule text; at Phase 5 re-point those citations to the live files (or the archive paths, for provenance-only uses) and RE-RECORD the WorkOrder hash on the status board (its hash is recorded, not pinned; only the Plan is byte-pinned). **The byte-pinned Plan cannot be edited: its frozen authority ladder (its lines 4/257 — "topic docs + 95 win > 90/14 > lock candidates > context packs") is resolved EXTERNALLY by this note + the STATUS crosswalk: the "lock candidates" it names were RATIFIED 2026-07-15 — their operative mechanics = BUILD §8.1/§8.2, their originals = archive evidence; the topic docs it names resolve to `archive/2026-07-15_pre-consolidation/<same filename>` with their meaning carried by the four live files; the precedence ORDER itself is unchanged.**
21d. *(moved — see 24b; the reader test must run LAST, after every move, edit, and link rewrite.)*
22. Include the manifest and this audit. Do not delete Git history or collapse old files into lossy summaries. **Update the archive README at the move (round 13):** its Phase-1 freeze instructions become history; the updated README states what the archive is (evidence only), the live root set, `FINAL_DESIGN.md` as the front door, the versioned-snapshot convention, and points at the ARCHIVED CONSOLIDATION.md's new path (the old relative link breaks when it moves).
23. Rewrite and validate every inbound link against the crosswalk. Keep archived originals byte-for-byte; do not turn them into pointer stubs.
24. End state at the root (round-15 final; the two ratified designs are ALREADY archived): **SEVEN files** — the four target files + the frozen packet (until its relocation is separately approved and proved) + the two experiment files (until program migration) — plus `archive/`.
24b. LAST GATE (after every move, edit, snapshot, README update, and link rewrite): rerun the blank-context reader test against ALL retained root files (the SEVEN-file set: the four live files + the frozen packet + the two experiment files), recording agent id, prompt, answers, citations, and the exact FULL file hashes tested.
25. In the final migration commit, verify every archived hash equals its Phase-1 MANIFEST hash (the two owner-amended files' archive entries are their PRE-amendment snapshots — the live copies keep the amendments and verify against the §16 freeze) and every live/inbound link resolves.

## 14. Zero-loss acceptance checks

### 14.1 Mechanical counts

- Exactly 33 original source rows in the archive manifest.
- Every stable rule range appears exactly once in the crosswalk:
  - NAME-01..19;
  - FS-01..27, including FS-22 retired and FS-23 open;
  - UNIT-01..14;
  - PER-01..20;
  - MF-01..12;
  - DU-01..24, with DU-13..18 explicitly replaced by `09`;
  - XC-01..18;
  - PIPE-01..37, including PIPE-27a, PIPE-27c, PIPE-27d, and PIPE-31b;
  - every literal T-labeled rule in `11`, from T1.1 through T12.9;
  - every literal FACT label from FACT-01 through FACT-36, including FACT-14b, FACT-17b, FACT-18a, FACT-26b, FACT-26e, and FACT-26f;
  - GI-01..04 and every active Track C section;
  - Track A D1..D8; issue-ledger D-1..D-13; OD-1..OD-21; K2; and all 42 supersession rows;
  - every Channel Contract clause, Candidate Packet block, candidate bundle, and open item.
- Exact schema counts: 24 stored fields = 6 code + 18 semantic/enrichment; `disputed` outside count.
- Exact enum counts: 4 fact types; 7 slice kinds including unknown; 10 units; 11 period scopes; 4 period sentinels; 3 surprise subtypes; 10 collision-signature slots.
- Exact state lists: metric 7, guidance 6, surprise 4, action 10.
- Exact field invariants: any level/comparison number requires `level_unit`; `change_value` requires `change_unit`; `unknown` is legal; each of the four stored horizon scopes maps both ways to its one `gp_*` sentinel; stored `long_range` never appears.

### 14.2 Stale-rule scans

The live files should contain these phrases only in a clearly labeled history/problem section, never as current law:

```text
9-unit
slice=total
quote + value
normalized quote +
confident alias
alias files
one unit hint pair
metric previous_guidance allowed
above means beat
beat must be positive
adjusted,diluted
GuidanceUpdate replay
legacy_name_map
both labels
39 reversals
three-slot scope
catalog-first
name-only KPI seed
```

Also scan for a candidate word written as final: `origin=xbrl_link`, empty measurement equals GAAP, cheap final-confirm, automatic shared-miss discount, and unratified XBRL materialization.

### 14.3 Meaning and behavior tests

A blank-context reader must be able to:

1. explain Driver versus DriverUpdate and the over-merge safety law;
2. take one source quote through channel, decomposition, name/slice/measurement/unit/period, identity, validation, write, and read;
3. construct one metric, guidance, actual surprise, guidance-vs-consensus surprise, and action example without violating a lane;
4. derive the scope slot order and collision signature;
5. list all 24 fields and identify code versus semantic ownership;
6. explain why own parts are slices, external causes stay in names, and portions stay in names;
7. explain why concept/member links may be absent and why wrong links are worse;
8. distinguish raw channel submission from the internal Candidate Fact Packet;
9. identify what is final-but-unbuilt, conditional, candidate, open, retired, and historical;
10. find every original source and its replacement anchor without opening chat history.

### 14.4 Archive and link tests

- Recompute SHA-256 for every archived source and compare to the frozen manifest.
- Verify tracked originals preserve their git history and untracked originals preserve recorded bytes/timestamps.
- Verify every internal anchor and file link from all four target docs, plus the temporary frozen packet if it remains live.
- Use the old-to-new `(file, section/rule ID)` map to rewrite or validate every inbound repository citation; no old root filename may become a silent broken link.
- Verify no source rule is present in two normative homes.
- Verify no source row lacks a destination and no final anchor lacks a source.
- Verify the root contains exactly the sanctioned set (round-15 final): the four target files + the frozen packet (until its approved relocation) + the hash-pinned `FableExperimentPlan.md` + the (step-21c-edited, original-snapshot-archived) `FableExperimentWorkOrder.md` + `archive/` — SEVEN files. Nothing else (the two ratified designs archived 2026-07-15).

## 15. Completion condition

The documentation consolidation is complete only when:

- all four target files pass the count, stale-rule, behavior, hash, and link checks, and any temporary frozen fifth file still matches its source hash;
- the owner choices and missing recipes in sections 10.2-10.3 are either closed or visibly left open, and any affected contract is not called implementation-ready while its blocker remains;
- candidate designs remain candidates unless explicitly ratified;
- every old file is recoverable byte-for-byte from the dated archive — or, for the two experiment files (the pinned Plan; the WorkOrder whose frozen original snapshots at Phase 5), is still live at the root with its archival completing at program migration (round-16 wording; the two ratified designs are already archived);
- a new bot can build the right mental model from `FINAL_DESIGN.md` without reading the archive;
- no production plan, code, graph, or data behavior changed as a side effect of the documentation move.

Archive moves may begin once zero-loss preservation, the crosswalk, and visible status labels pass. Open or candidate decisions may remain open; only lost meaning, an unlabeled conflict, or an implementation-ready claim over a known blocker stops the move.

## 16. Re-verification record

This section records the 2026-07-15 re-check of the later Claude update. It is audit evidence, not design authority.

- All 33 source-file hashes still match the first audit baseline; only `CONSOLIDATION.md` was edited.
- Verified additions were merged above: exact unit and sentinel invariants, signed EXP-0/1/2 status, WP-FC-EDITS commit/test status, experiment hash drift, stale external-source warnings, frozen-packet handling, and repository-wide citation migration checks.
- The appended second audit was removed after those unique facts were integrated because it repeated the same rules and made the reading path longer.
- Its proposed “about 19” live files actually listed 23 files plus a new master, or 24. That alternative was not carried forward because it duplicated authority and did not meet the requested few-file, one-copy goal.
- Its proposal to update all old source files before archiving was not carried forward. The safer plan is to build the four target files from the checked atom ledger, prove the crosswalk and links, and archive the original sources unchanged.
- No claim of “fully implemented” or “production-ready” is made. Final design, code, tests, experiment results, and production runs remain separate statuses throughout this audit.

**Second re-verification (Claude, 2026-07-15, after the cleanup above):**

- Re-verified mechanically: all three quoted hashes are exact (`FableExperimentPlan.md` = `5196…7472` byte-identical; WorkOrder = `4911a22f…`; frozen packet = `86b2fc17…`); the WorkOrder-vs-status-board hash drift is real; the HANDOVER file does mislabel `FablePromptv2.md` as “the current” prompt (its line 145); O13 and the ra_0007 pre-K-pairs.v2 gate are recorded owner/Fable rulings on the status board and are now reflected in section 7.3.
- Sections 4-6 were re-read line-by-line against the primary sources after the compression: meaning-faithful throughout; one precision fix was applied (metric `reported`-vs-`increased` routing keys on a prior value stated **in the source**, never a graph read).
- Corrected in this pass: the external-citation scan count (12 -> 22, pattern-dependent, incl. the three engine prompts whose inlined rulebooks cite `02_DriverCatalog.md`; the third re-verification later fixed this line's terminology — 12 exact-filename, 21 stem-union, 22 bare-word incl. one name-collision false positive); added the `13_Track_RetiredDesign` still-useful-analysis pointer; added open question 10.2 #5 (OD-2 first-fact guard x OD-14 bare-guide parking, latent until live admission); added the interim stale-prose hazard note to Phase 2.
- Adjudication of the removed second audit: the removal is accepted — its unique verified facts are integrated above, its per-file working notes survive only in session history and are not needed for this plan, and its “about 19 live files” alternative in fact enumerated 24 files; the correction is conceded. The four-file target is now jointly endorsed **given** the added machinery this plan carries (atom ledger, inbound-citation crosswalk and rewrite, byte-pure archive, section 14 checks, blank-context reader test); without that machinery the merge would have been unsafe, which is why the alternative existed.
- Confidence statement, scoped precisely: every substantive CLAIM in this file has been verified by two independent readers against the 33 sources, the git record, and the signed experiment artifacts, and the known ISSUES and OPEN CHOICES are exactly the items listed in sections 9.2, 10.2, and 10.3. This does NOT mean the file contains every rule detail — by design it summarizes and points (section 0's role statement); exact recipes, constants, prompt blocks, and fixtures remain in the sources until the four target files carry them, and section 14's checks are what will prove that transfer lossless.

**Third re-verification (Claude, 2026-07-15, checking the final external review):**

- The reviewer's verdict is CORRECT and is now stated in section 0: this audit is a complete, accurate MAP and PLAN — it is not itself the standalone zero-loss replacement, and the old files must not be archived until sections 13-14 are executed and pass. That was always the plan's own sequencing; it is now explicit.
- All of the reviewer's mechanical checks reproduced exactly on re-verification: this file's hash before this edit round (`5353e08d…`), the 11,320-line / 1,362,208-byte source totals, 33 disposition rows, 42 replacement rows, and the citation-count breakdown (12 exact-filename citers — reproduced by independent scan — 21 by stem, 22 with the bare word, including the `INDEX.md` name-collision false positive). Section 13 step 16 now carries the precise numbers.
- Of the nine claimed material gaps, all nine were verified real as facts. Three were genuine defects and are now fixed in place: the missing `UnitExtraction.md` naming-trap warning (section 3.4), the four missing accepted-limit rows (section 9.4), and the missing Track C archive-baseline counts (section 6.3). Four were summary-scope by design but earned pointer-hardening, also applied: the locked Haiku pin + exact-set pointer (section 4.15), the OD-18 quarantined-head/park + three-check wording + OD-19 residual (section 4.17), the FS-26 per-hop cutoff + deferred unknown-axis view (section 4.17), and the kernel §15.0/§16 transfer-whole note (section 7.1). Two (Track A finalization detail, Track B fixtures/constants) remain deliberately in their sources — they are exactly the atom-ledger transfer content of section 13, and duplicating them here would recreate the two-copy problem this plan exists to end.
- No status claim, hash, or rule statement from the external review was found wrong; conversely the review confirms the five owner questions stand and no false FINAL-versus-CANDIDATE or PASS-versus-PENDING claim exists in this file.
- Recommendation-round addendum (same day): the external reviewer's five per-question recommendations were verified against sources; the useful refinements were folded into the section 10.2 question texts as labeled "notes for the ruling" (Q1 unclear-attribution disposition per `99` §3.18; Q2 park-versus-skip taxonomy with the FS-20 auto-demotion drain and no-real-document-conflict correction; Q3 the two coherent resolution options, still open — the reviewer's "effectively settled" was an overclaim; Q4 the `dimensions=[]` verified-empty refinement; Q5 the `_surprise`-lane twin scope and the same-batch-not-same-transaction correction). All five remained owner decisions at that point; nothing was decided in this file until the rulings below.

**Owner rulings + Phase 1 executed (2026-07-15, recorded by Claude):**

- The owner decided all five section-10.2 questions; the rulings are recorded in place there (Q1 core-derives · Q2 no change, PARK stands · Q3 resolution (b), offline catalog + lazy born-complete nodes · Q4 amendment approved with the `dimensions=[]` wording · Q5 first-fact guard scoped to bare names). Q4 and the Q1 clarification apply to the live contract files at the Phase-3 review; Q5 is a scoped owner amendment to the OD-2 supporting pin; Q3 narrows the OD-16 recommendation. Per the no-pre-archive-edits rule, no source file was touched — the rulings ride here and land in the four target files at migration.
- **Phase 1 executed:** the three untracked sources were committed unchanged (`49f1cd8`); the freeze manifest was written to `archive/2026-07-15_pre-consolidation/MANIFEST.json` with a README — all 33 sources sha-256-pinned with bytes, lines, and git provenance; totals re-verified at 11,320 lines / 1,362,208 bytes. **The 33 sources are now FROZEN** (no edits until Phase 5 archives them byte-for-byte against this manifest). Next: Phase 3 — write the four target files from the atom ledger, then the section-14 checks, then archive.

**Fourth external round (2026-07-15, post-Phase-1; adjudicated by Claude against the frozen sources and the session transcript, not from memory):**

- The reviewer submitted 12 line-level points against this file. Ten were verified real and fixed in place: menu reuse is producer-judged same-meaning (never string-exact selection); the continuity line now uses the source's own terms (one outgoing continuation allowed, fan-out refused); the XBRL candidate DOES materialize USD-per-share/EPS facts (v1 unit whitelist stated); a withdrawal OR reaffirmation copies the one clear prior `series_unit`; the collapse comparator is stated positively (numeric `level_*` signature, normalized `value_text` for qualitative); `surprise_basis_hint` is required on surprise items and forbidden on other lanes; the -ing/-ed and market-force naming carve-outs were restored to the ban-list summary; offline axis classification judges by MEMBERS, never names; `15`'s "already built" overclaim is now flagged in stale-item 11; and the second-re-verification citation-count line was reworded to match the verified 12/21/22 breakdown.
- An eleventh point was accepted as precision only (Q1): `99` §3.18 is a Locked owner-approved rule recorded in a historical decision record (not a second source of truth), and its exact disposition for ambiguous attribution is SKIP — park applies only to clearable blockers under the general taxonomy. The ruling's substance (core derives; never a guessed boolean) is unchanged.
- One point was REJECTED: the claim that §10.2 Q3 "was never genuinely open." The frozen packet rejects NAME-ONLY seeding and its rationale targets evidence-free cards; OD-16's materialize-all recommendation stayed live until the owner ruling narrowed it (a ruling that would have been a no-op if pre-settled); and the same reviewer's pre-ruling "effectively settled / 100%" claim was already refuted in-session. The decision-history record stands as written.
- No frozen source was touched; no rule or ruling substance changed. All edits are to this audit file only.

**Fifth external round (2026-07-15; the reviewer challenged the two round-four remainders with NEW citations — both re-verified in the frozen sources):**

- Point 4 (Q1) conceded in full: the skip-of-ambiguous/third-party wording sits under `99` §3.18's "Current Guidance extraction pipeline check" — legacy pipeline behavior outside the Locked block (which covers the boolean's meaning and guidance-only scope); a topic-file sweep found no standing attribution-skip rule. The Q1 note and ruling wording were corrected in place: SKIP-on-unclear is the 2026-07-15 ruling's own content, and the legacy skip-ALL-third-party list is not carried forward as target law.
- Point 5 (Q3) — the round-four rejection is WITHDRAWN in substance: `15`'s UNIFICATION ("every new Driver arrives WITH its first proven DriverUpdate"; Block 2 becomes the first DriverUpdate on CREATE) plus born-complete-STANDS made resolution (b) the standing default, and OD-16 was a never-owner-approved recommendation (`66` §0.R closing: "the rest recommendations pinned") that could not license pre-fact nodes — an evidence-bearing card is still factless until its Block-2 fact writes. The Q3 question text now states this precisely. What stands from round four: the rejection's-rationale sentence (it targets evidence-free/name-only cards) remains true and is why resolution (a) was a coherent amendment request, and the reviewer's original "100% / effectively settled" certainty framing was still an overclaim, which the reviewer conceded. The concession was driven by the new citations, verified line-by-line — not by repetition.
**Phase 3 begun (2026-07-15, owner GO "all approved"; commits pushed to origin from here on):**

- Step 11 contract review executed — the owner-amendment batch (Q4 + Q1, both rulings above) is applied to the two live-continuing files: `ChannelContract.md` §3 XBRL row + guidance row + banner note (post-amendment sha `4fdeb821…`), and the frozen packet's FETCH XBRL clause (`15_CandidateFactPacket.md`, post-amendment sha `038a0f89…`, amendment tagged in place). Pre-amendment baselines stay pinned in the Phase-1 manifest (`ChannelContract` old sha per manifest; packet old sha `86b2fc17…`). These are the ONLY sanctioned source-file changes before Phase 5; the contract is still NOT implementation-ready (schema/nullability, versioning, outcome codes, source-identity namespaces — section 10.2 #22 / 10.3 #3 remain open and explicit).
- Build order per section 13: `FINAL_DESIGN.md` (step 10) → `BUILD_AND_OPERATIONS.md` (step 12) → `STATUS_AND_HISTORY.md` last (step 13) → front-door/reciprocal links (step 14) → section-14 checks (Phase 4) → byte-pure archive (Phase 5). Until Phase 4 passes, the frozen sources remain the byte evidence baseline and every new file carries a provisional banner.
**Sixth external round (2026-07-15, post-Phase-3; every point verified against frozen sources before any change):**

- The reviewer audited the three new files for exact-loss. Verified REAL and fixed in `FINAL_DESIGN.md`: OD-18's exact prefilter triggers inlined from kernel §9 item 2 (cross-industry exact-name · industry-cluster ≥2 · scope-qualifier heterogeneity incl. same-industry); the OD-11 ANNUAL pin restored (`66` OD-11 #4: annual sequential==YoY → always `percent_yoy`; validator: `percent_sequential`+annual invalid) plus the in-document-only override and consumes-resolved-`period_scope` clauses; `in_line` restored to MANDATORY code behavior incl. the corrects-to-`in_line` catch and open-shape boundary cases (`07`:75, `66`:470/476 — the audit ledger's own "may" was the propagated error); the OD-14 read rules enriched to full fidelity (mechanical midpoint derive from the COLLAPSED prior in the exact canonical series key, correction facts FORCED to `unknown` via source/event metadata or explicit wording, the four-condition withdrawal fan-out with scope-unclear → no fan-out and no-op re-withdrawals ignored, and the RETRACTION rule: numberless fact only when driver/scope exact); FS-26's exact edge/record shapes + indexes inlined (no dependence on the archived `03` for storage shape); the §10 tag error fixed (running layer = DESIGN-INCOMPLETE, OD-5 scanner = recommendation — neither is FINAL/BUILD-PENDING).
- Fixed in `BUILD_AND_OPERATIONS.md`: Track A finalization detail restored (suffix-base resolution ladder + the five final checks + no-hand-edits); §11 now carries the explicit source-resident exact-block transfer list (kernel §15.0/§16 · `12` §12.3 fixtures) proved at Phase 4. Fixed in `STATUS_AND_HISTORY.md`: the Track B cell no longer says bare "build-ready" — decisions final, affected contracts NOT implementation-ready (BUILD §11).
- Owner-amendment extension (same Q1 ruling, tagged in place): the frozen packet's FETCH row still told channels to send `company_confirmed`, contradicting the amended contract that names the packet its source of truth — the row now reads "company-confirmation attribution EVIDENCE (the CORE derives the boolean)". Packet post-amendment sha `aa7239ed…` (supersedes `038a0f89…`; pre-amendment baseline unchanged in the Phase-1 manifest).
- REJECTED with evidence: the claim that Track C retirement steps were shortened too far — all eight ordered steps and all green gates are present verbatim-faithful in BUILD §6. The reviewer's crosswalk-incompleteness point is correct but is Phase-4 work by design (step 16), not a Phase-3 defect. Agreed with the reviewer: run the section-14 checks next; defer the paid fresh-bot test until they pass; no Phase 5 yet.
- Post-fix hashes: FINAL_DESIGN `bb2fe1ef…` · BUILD_AND_OPERATIONS `1a54dadf…` · STATUS_AND_HISTORY `f9a2d4b8…`.

**Seventh external round (2026-07-15; each point source-verified before change):**

- Accepted and fixed in `FINAL_DESIGN.md`: OD-1 carried in FULL executable form (`66`:211-219 — the one-suffix-strip rule with stacked/mid-name cases, THE verbatim semantic question, two-independent-YES, the rewrite/park failure path, the `terminal_admissions.json` memo schema with freeze/reuse semantics, the latent-base creation constraints and exact-`norm()` automatic graduation, the seven finalization hard-fails, the non-rules) plus OD-2's verbatim C2 challenge and the F2 family gate's three proof classes; the OD-14 guidance-series key corrected from the source block's stale "unit-FAMILY" to `series_unit` equality (reversal #36/OD-10 — the reviewer caught my round-6 verbatim copy propagating a dead term); exact `fact_scope` separators stated (slice `;`-join per FS-09, measurement comma-join per `03`:195); FS-18 exact-after-normalization member fold; FS-20's three bucket CONTENTS (~24 hard-exclude with log+auto-demotion · ~241 provisional · ~3,000 keep; exact lists = external catalog §4 data); baseline precision (no `internal_target`, own-target → `previous_guidance`, read-derived beat size formula).
- Accepted and fixed in `BUILD_AND_OPERATIONS.md`: Track A finalization now the executable PIPE-24/25 contract (end-of-build single pass, three artifacts, the deterministic three-step BASE_METRIC lookup order, latent semantics, variant inheritance); Track C now carries the exact consumer search list, the exact deletion target (orphan-`GuidancePeriod` conditions, constraint/index drops, the no-relabel prohibition), and the six edge-count gate names — partial CONCESSION on my round-6 rejection: the eight steps were indeed all present (that stands), but these exact sub-rules were not. Stale packet hash corrected to `aa7239ed…` here and in the STATUS banner (round-6 bookkeeping miss).
- Ownership clarity: STATUS §2 now declares itself the owning file with FINAL_DESIGN §10 as the generated mirror (the earlier sentence said both, self-contradictorily); the ChannelContract crosswalk row states the contract is the sole public authority and its "source of truth" banner line is provenance — an optional owner banner one-liner is noted for the next amendment batch, and the contract file itself was NOT touched.
- Round verdict: 6 of 7 points real (one a refinement of a previously-rejected claim, honestly conceded); the "unit family" catch was the reviewer correcting MY round-6 fix — the verify-both-directions protocol working as intended.

**Phase 4 mechanical pass (2026-07-15, owner GO; seeded with the reviewer's six known failures — all verified real and fixed):**

- Seeds fixed: the two remaining stale packet-hash references (STATUS crosswalk row + manifest bullet → `aa7239ed…`); STATUS §2's circular ownership resolved by INLINING the five master status lists there (FINAL_DESIGN §10 = the generated mirror); the ChannelContract banner's "source of truth" line replaced by the provenance one-liner (owner batch, tagged in the amendment note); Track A finalization operational guards transferred (verbatim-classifier-prompt pin, `self_canonical` tagging + `--expect`/h32 batching, the re-stamp hard-fail, atomic temp+rename writes with re-run crash recovery, the `--final` sidecar contract, the PIPE-35 consumption contract, K2); the DU-15 multiple-comparison selection rule transferred (`12`:126 — one primary baseline on the home fact, the expectation comparison rides the producer-detected surprise fact); supersession row 34 re-described to its true four-part subject.
- Sweep results: stale-phrase scan CLEAN (every §14.2 phrase appears only as negation or labeled history; the packet's `long_range_start/end_year` are frozen Block-2 INPUT field names, distinct from the retired stored scope value); every §14.1 enum/state/count check GREEN (10 units · 11 scopes · 7/6/4/10 states · 4 types · 7 kinds · 3 subtypes · 4 sentinels · 10 signature slots · 24=6+18 · field invariants); rule-ID accounting GREEN via the NEW rule-ID crosswalk (STATUS §7.1) — every §14.1 range named once with its live anchor and the named exceptions (FS-22/23, DU-13..18, PIPE/FACT sub-IDs, T-census retirement note, GI-05+ history-only, D-ledgers, OD per-ID anchors, K2, the 42 rows, contract/packet/bundle/open items); the missing OD-3/OD-4/OD-15/K2 ID labels were attached to their already-carried content.
- **Blank-context reader test (14.3): PASS, 10/10.** A fresh agent with zero project context, restricted to the five live files, answered all ten exercises correctly with per-file citations and zero "cannot answer" gaps — including the full end-to-end walk (correct decomposition order, `product:iphone` slice, glued-billions scaling, OD-11 basis, prior-year-routes-to-metric, born-complete create, OD-8 no-sibling bare fact), five legal lane examples (it independently applied OD-1 to refuse a stacked surprise name and code-set `in_line` for a guide range containing consensus), the exact ten-slot preimage, the 6/18 field split, and the row-25/crosswalk lookups. Transcript: agent a5359f1b06e5e0b9e, 2026-07-15.
- ~~Step-19 hash freeze (Phase-4 exit state)~~ **SUPERSEDED by the round-9 freeze** (rounds 8-9 changed three of the five files after this was recorded — the staleness was the reviewer's round-9 finding 2). **Twelfth external round (2026-07-15; the reviewer ENDORSED the keep-live candidate policy; its seven blockers verified — 6 REAL/1 as-designed — via one Neo4j ground-truth read + a 2-agent fan-out + inline checks):**

- **Finding 1 (real executable bug, graph-verified):** the live graph stores `formType` as `10-K/A`/`10-Q/A` (slash forms — 137 + 41 nodes counted 2026-07-15), while the candidate's prose says "10-K-A/10-Q-A"; a literal match would silently skip every amended filing. BUILD §8.2's recipe header now carries the graph-verified literals with the warning.
- Finding 2 (testing currency): a FOURTH blank-context ten-question run was executed against the round-11 content — **PASS 10/10** (incl. the per-guide withdrawal composition, the conditional basis, and the open-gap discipline). Honest note recorded: round-12 edits (this record, policy/status/crosswalk prose) postdate that run but touch nothing the ten exercises test; the DEFINITIVE final run is pinned to the Phase-5 gate (step 21d, against the actual post-archive root set). Banners now say round 12 and name the step-21d re-run explicitly.
- Finding 3 (authority wrapper): BUILD §8's policy note now states the three tiers verbatim — FINAL_DESIGN owns current law · the live candidate files own proposal-only mechanics (their internal "topic docs win" lines resolve against FINAL_DESIGN as the topic docs' successor, archived originals as evidence) · archived files are evidence only.
- Finding 4 (accepted-vs-pending blur): a reading rule added — where a name appears on both sides (born-complete, recovery, CLAIM-off), the accepted side is the PRINCIPLE (already law), the candidate side is this kernel's IMPLEMENTATION; ratifying the bundle never re-opens the principle.
- Finding 5 (WorkOrder preservation): step 21 arithmetic corrected to **27 moves + 3 snapshots + 3 unchanged deferred** — the WorkOrder's frozen original is snapshot-archived BEFORE the step-21c citation rewrite; plus the versioned-path rule (a later archival of a live-continuing file never overwrites its earlier snapshot).
- Finding 6 (crosswalk exactness): T11.2/T11.6/T11.11 now have individual destinations in the §7.2 T-table (verified verbatim from the census by a reader agent), and the contract-clauses/packet-blocks/candidates/open-items row was split into four precise rows.
- Finding 7 (old-policy stragglers): the §11 kernel/XBRL disposition rows, the §14.4 root-set check, the §15 completion condition, and the dashboard round count all updated to the rounds-11/12 policy.

**Round-11 hash freeze (superseded by round 12 below):** FINAL_DESIGN `f3e99ad1…` · BUILD_AND_OPERATIONS `806d896b…` · STATUS_AND_HISTORY `9462ab3b…`.

**Thirteenth external round (2026-07-15; all seven blockers verified — 6 REAL fixed, 1 already-correct-but-under-recorded; small stales fixed):**

- Fixed: BUILD's named-correction override rule (a graph-verified correction beats a retained candidate's text) · the "their pins forbid edits" line (only the Plan is pinned; the WorkOrder is edited+rehashed at 21c after its original is snapshot-archived) · T6 per-rule anchors (five rules, five destinations, verified from the census bullets) · T11.2/T11.6 gained their ChannelContract-side destinations (§1+§4 · §5) and T11.11 is explicitly writer-side-only by design · the Phase-5 reader test moved to step 24b — the LAST gate after every move/edit/rewrite, against ALL retained root files, with agent/prompt/answers/citations/hashes recorded · step 22 now updates the archive README at the move (its Phase-1 instructions become history; the CONSOLIDATION link re-points) · the XBRL↔kernel DEPENDENCY recorded (P6/P7/P8/P4j consume kernel machinery; if the kernel is rejected the XBRL bundle re-bases; decide the kernel first or both together) · stale texts: the §0 role statement no longer calls the 33 sources the rule authority (FINAL_DESIGN is the front door); FINAL_DESIGN §10 now points at STATUS §4 as the rulings record.
- **OWNER-PENDING, honestly recorded: the keep-live candidate policy (rounds 11-12) has been RECOMMENDED by both reviewers but the owner has NOT yet explicitly approved it** — requested in the round-13 report; until then it stands as the working default, reversible.
- Round-13 freeze of the TESTED file set: FINAL_DESIGN `a9b1168b…` · BUILD_AND_OPERATIONS `ad9e62e7…` · STATUS_AND_HISTORY `3c0f0317…` · ChannelContract `9e6ffcbb…` · frozen packet `aa7239ed…`. The fifth full ten-question reader run below executes against exactly these hashes.

**Round-13 reader test (the fifth full run): PASS, 10/10 against the round-13 freeze above** (agent in wf_a976be72-9aa, ~111k tokens; incl. the NEW authority-tiers question — three tiers + the XBRL-re-base-if-kernel-rejected dependency answered exactly — and the amended-filing `formType` slash literals).

**🏛️ OWNER RATIFICATION (2026-07-15) — the governing decision for both former candidates:**

> "I approve the Admission Kernel v3.4 and XBRL Integration designs as our current working designs. They are no longer pending candidates. Integrate their complete current mechanics, rules, tests, safety gates, failure handling, and required examples into the correct four live documents. Apply all later verified corrections, including the slash-form filing names. **This approval does not authorize implementation, activation, or production use.** Keep every existing experiment gate, dormant state, OFF switch, and unresolved item clearly marked. Historical discussion can remain in the archive. Fix the remaining Round 13 documentation issues, prove every transferred item has an exact destination, and rerun the complete reader test on the final files after all moves and link changes. Only then archive the original candidate files. Future design corrections must update the single owning live section and add a short history entry. No parallel live copies should remain."

- Effects: the round-11/12 keep-live question is MOOT (superseded by ratification); both files now integrate FULLY into the four live documents (tasks INT-2..INT-5), every gate/dormant/OFF state stays marked, the two originals archive only after the integration + the post-move full reader test; Phase-5 arithmetic becomes **29 moves + 3 snapshots + 1 deferred (the Plan) + the live-edited WorkOrder** — the two former candidates join the moves at integration completion. The owner's forward change-law is recorded in STATUS: one owning live section per correction + a short history entry; no parallel live copies.

**INTEGRATION EXECUTED + ORIGINALS ARCHIVED (2026-07-15, tasks INT-2..INT-5 complete):**

- INT-2: the kernel's complete mechanics transferred into BUILD §8.1.1-8.1.13 (strategy · the full Stage 0-3 decision flow + axiom-C guarantee · G1 cards + the verbatim producer instruction · the 8 park codes + governance · family policy · the LINK mechanism whole: pair assembly, the repairability-classified auto-refusals, the five checks verbatim, high-blast, apply/memo/head election, cache, both triggers, deferred-ledger hygiene, the frozen anchor + refuted negatives + enrichment-OFF + re-freeze, union-preview, BROAD/ESTABLISHED/CLAIM_FROZEN + in-tx eligibility, the split-reconciliation lane · V1-V14 with meanings · phases/seed/gauntlet S-A1..6 + P1..P9 + pass bar + signal eligibility + contingency ladder · the immune system: smoke-alarm doctrine, falsifier (i)-(vii), drift probe, dispersion re-cluster, risk-stratified audits + stratum honesty, the planted calibration stream, flow metrics, launch blockers · recovery items 1-8 with propagation rules · the §11.0 locked tier rule + owner defaults · kernel experiments S1-S4/X0-X9/X-G/X-IM/X-C · reject-conditions + the terse rejected-alternatives list). INT-3: the ten XBRL amendments gate-tagged at their owning sections (BUILD §5 validators ×4 · §8.1.7 V9 · §8.1.6 eligibility · §8.1.9 falsifier · FINAL_DESIGN §8 rider/XC-18 · §9 collapse rank), all marked DORMANT until the materializer enables. INT-4: the per-element destination proof = STATUS §7.1b.
- **The archive-gate reader test (the sixth full run): PASS, 10/10** (agent in wf_51969a57-6d7, ~127k tokens) — a zero-context reader FORBIDDEN from opening the two originals reconstructed, from the live files alone: the exact 8 park codes, the five LINK checks + high-blast, the CLAIM lifecycle (OFF → shadow → S3-earned ON → one-wrong-link OFF), BROAD/ESTABLISHED/CLAIM_FROZEN + the in-tx eligibility formula, the gauntlet codes + pass bar, the formType slash literals + the pure-unit fence + the kernel-rejection re-base answer, the ratified-not-activated status, and the §7.1b destination proof.
- **The two originals then moved into the archive** (git mv), each verified BYTE-IDENTICAL to its Phase-1 manifest hash first (kernel `a813b05a…` ✓, XBRL `0fb89a0c…` ✓). The root live set is now: the four live files + the frozen packet + the experiment Plan/WorkOrder + the remaining 27 pre-consolidation sources awaiting the owner-gated Phase 5.

**Fourteenth external round (2026-07-15; post-integration audit — all six findings verified REAL, one a genuine SOURCE ambiguity):**

- **The exact enablement proof plan transferred** (the reviewer was right that naming ≠ carrying): X-XL0 determinism 100% + its four required fixtures · X-XL1 twin fidelity ≥99% id-equality with mandatory 52/53-week filers · X-XL2 suppression/tripwire calibration with the zero-suppressed-non-twins HARD ZERO and the pre-registered rollout bar · X-XL3 recall with the sha-locked key and the zero-market-moving-fact-lost HARD ZERO · X-XL4 cost (informational, never gating) · the hard pre-gates (XC-16 + full-universe run, PIT menu proof, falsifier-(iii) dry-run, the fresh census incl. `FACT_MEMBER`/`FACT_DIMENSION` wiring and cohort sizes) · the flag-on industry-by-industry rollout gated on X-XL0-3 holding — all now verbatim-faithful in BUILD §8.2.
- Also transferred: P13's exact twin-warning trigger (text-write time; same event + head + value-compatible level + exactly ONE differing scope component, measurement excluded; no park/snap/id change) · the kernel's owner-ruling-3 storage rule (NO `head_id` denormalization initially; one-hop union reads; the three conditions if ever added) · the P1-P7 model principles line · the X-S1 reject-condition (no coverage knee → re-open D1 WITH THE OWNER).
- **`xbrl_internal_conflict` unified (a real ambiguity in the SOURCE — P4g said "skip + log" while amendment 9 registered it as a state-based park class):** the ONE interpretation, recorded as a named round-14 clarification per the change law — the conflicting scope is NOT materialized and is recorded under the STATE-BASED park class (fail-closed, never fuse; re-enqueues only if the filing's XBRL is re-parsed/amended).
- Status staleness fixed: "dormant until ratification" → "DORMANT until the P19 proof plan (X-XL0-3) + every hard pre-gate" in both STATUS §2 and FINAL_DESIGN §10 (ratification happened; the gates did not move). Phase-5 arithmetic restated post-move: REMAINING 27 + 3 + 1 + the live-edited WorkOrder; end state SEVEN root files.
**Fifteenth external round (2026-07-15; all six findings verified — 5 REAL fixed, 1 escalated to the owner):**

- Fixed: the three remaining seven-vs-nine Phase-5 contradictions (step 24, the §14.4 root check, the §12.5 exceptions — all now the SEVEN-file end state, the ratified designs archived) · BUILD's post-ratification activation sentence (approval done; activation still waits on the P19 X-XL0-3 bars + every hard pre-gate + EXP-6 evidence) · the lost ROUTER promotion bar restored (claim-precision/recall AND zero wrong-ATTACH on the cross-industry fixture family — verified at the archived kernel line 268) · the three stale integration-in-progress/files-remain-live spots (FINAL_DESIGN §10, the BUILD §8 banner, the STATUS dashboard) → integration COMPLETE + originals archived.
- **ESCALATED TO THE OWNER (finding 6, correctly caught — my round-14 wording was NEW, not source):** the `xbrl_internal_conflict` RETRY TRIGGER. The source registers the class as state-based but never names its clearing state. Proposed: re-enqueue only on re-parse/amendment of the filing's XBRL. Alternatives: also on manual repair-lane action, or leave unspecified until build. The text now says OWNER-PENDING; awaiting the ruling.
- Point 5 conceded: the seventh run predated the last STATUS line-fix and its Q9 omitted two buckets — the EIGHTH run below executes the standard set against the TRUE final hashes, with the full prompt + hashes recorded here and the answers preserved in the workflow transcript.
- **Round-15 exit freeze (the tested set):** FINAL_DESIGN `1aaaedfa…` · ChannelContract `9e6ffcbb…` · BUILD_AND_OPERATIONS `13452ee7…` · STATUS_AND_HISTORY `9eafa61e…` · frozen packet `aa7239ed…`. The eighth reader run executed against EXACTLY these five hashes; prompt = the standard §14.3 ten with Q9 asking ALL status buckets and Q7 additionally probing the enablement bars + the owner-pending retry trigger.
**Sixteenth external round (2026-07-15; five findings verified REAL + the owner's retry-trigger RULING landed):**

- **OWNER RULING (round 16): the `xbrl_internal_conflict` retry trigger = option 1 with the sharper precision** — retry ONLY when the affected report's parsed XBRL facts actually change; an amended filing is processed as a NEW report and never silently rewrites the old one. Recorded in the owning section (BUILD §8.2 recipe step 4) with a history note; consistent with OD-14 amendments-as-new-facts and P4b.
- Fixed: the four remaining Phase-5 stragglers (step 21's stayer enumeration, the 21c Plan-ladder note, step 24b's file set, the §15 completion carve-out — all now the SEVEN-file post-archive state) · the rider's "before ratification" → "before ENABLEMENT" (the last dangerous activation sentence) · the two "LIVE candidate" phrasings (the BUILD three-tiers note + the P-map intro) and the two STATUS rows (dashboard + the bundles crosswalk row) → ratified-and-archived wording · X-XL4 results REPORTED TO THE OWNER restored · "the falsifier and ALL pre-filters are CODE, no model" restored (§8.1.11).
- **Eighth-run regrade conceded: 9/10, not 10/10** — its Q9 rubric omitted DESIGN-INCOMPLETE (my prompt's fault), and its "FablePrompt/FablePromptv2 … archived" answer was WRONG (they are among the 27 still at root; the crosswalk row states their DESTINATION). The NINTH run below uses the complete bucket rubric (incl. DESIGN-INCOMPLETE and a current-location question) and is recorded with FULL 64-char hashes + the persisted prompt-script and transcript paths.
- **Round-16 exit freeze — the ninth run's tested set (FULL hashes):**
  - FINAL_DESIGN.md = `1aaaedfa891c8fb3f167c67bc687264c920b4b35e73b5b0baca7abf7be9aa1af`
  - ChannelContract.md = `9e6ffcbbcbc1a34e3792a1afa37469915ddfe02cbeac20c978cdd09b89292cea`
  - BUILD_AND_OPERATIONS.md = `8acd73fc378e93e2460bde7b351817e452544138111d5e875bcc2a4e76c07b1d`
  - STATUS_AND_HISTORY.md = `4c2442c9319871708130d538db826793ce7fdc7fb73cc5c54b2eb859452539a1`
  - 15_CandidateFactPacket.md = `aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c`
**Seventeenth external round (2026-07-15; all five findings verified REAL and fixed):**

- Fixed: the rider-unlock line now names ALL THREE activation conditions (P19 bars + hard pre-gates + **EXP-6** — the round-16 wording had dropped EXP-6) · the ratification-bundle header, the §11 kernel/XBRL disposition rows, and the three present-tense audit-body spots (§7.1 candidate header, §9.2 not-ratified item, §9.3 off-until-ratification item) all carry dated RATIFIED/DONE annotations · the STATUS §7 rows now say the originals are ARCHIVED-DONE · the execution card's 21c step now explicitly includes the WorkOrder's line-14 authority sentence ("still candidates under test" → ratified working designs) · the card's 24b step now REQUIRES durable in-repo test records (machine-local `~/.claude` paths are not portable evidence).
- The ninth run honestly re-scoped: custom rubric 10/10, but it had REPLACED the official Q7 — so the **TENTH run executed the STRICT official §14.3 ten, unmodified: PASS, 10/10**, and its complete record is now DURABLE IN THE REPO: `archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-15_official-run-10.md` (agent run `wf_2e462b6d-c84` · the full prompt · the full answers with citations · the full tested hashes: FINAL `1aaaedfa…` / contract `9e6ffcbb…` / BUILD `f5988ed0…` / STATUS `7110fa18…` / packet `aa7239ed…`). Q7 (the official absent-vs-wrong-links question) answered exactly; Q9 covered all eight buckets including design-incomplete and historical; Q10 named all four crosswalk maps.

- **NINTH reader run: PASS, 10/10 on the COMPLETE rubric against exactly the freeze above** (workflow wf_0eb9fa06-1dc; prompt persisted at `…/workflows/scripts/ninth-reader-run-wf_0eb9fa06-1dc.js`; full answers in the run's transcript directory `…/subagents/workflows/wf_0eb9fa06-1dc/`; ~127k tokens). Every bucket answered including **DESIGN-INCOMPLETE** (the running layer); the destination-vs-current-location trap answered correctly (*FablePrompt.md is RIGHT NOW an un-archived source at the root, sha-pinned in the manifest; its DESTINATION is the archive as an executed brief*); the owner's retry-trigger ruling quoted verbatim; the X-XL bars, ten-slot hash preimage, 24-field split, per-lane matrix, and all four crosswalk maps (§7 · §7.1 · §7.1b · §7.2) exact. The §14.3 check stands against the true final hashes with the run fully documented.

- **EIGHTH reader run: PASS, re-graded 9/10 (see round 16)** (workflow wf_70507318-cfc, ~127k tokens; full answers in its transcript directory). Every bucket answered correctly — final-but-unbuilt (the Track B stack) · conditional (OD-19's exact gate) · approved-working-design (the kernel, not-activated, gates in force) · CANDIDATE (Bayes, unvetted) · open (FS-23) · RETIRED (`slice=total` + examples) · HISTORICAL/evidence-only (the executed prompt briefs, archive = evidence never authority) — and Q7 correctly reported the X-XL bars AND the `xbrl_internal_conflict` retry trigger as OWNER-PENDING with the proposed reading. The §14.3 check now stands against the true final hashes with the run fully recorded.

- The reviewer's earlier point-5 concession stands: the sixth run tested custom integration questions, not the standard set — so the **SEVENTH reader run executed the COMPLETE standard §14.3 ten-question set against the then-current post-integration files: PASS, 10/10** (agent a346bc6f483d8da8d, ~147k tokens) — including the upgraded Q7 (the exact X-XL enablement bars: 100% determinism, ≥99% twin id-equality, both HARD ZEROS, the pre-registered rollout bar, the hard pre-gates) and Q9 (the materializer's exact status: ratified as working design, DORMANT until P19 + gates, EXP-1 signed, nothing activated). The run also caught the last staleness — STATUS §2's "integration in progress" — fixed to integration COMPLETE + originals archived. **Round-14 exit freeze:** see the final hash line in the migration commit; the live set = 4 files + packet + Plan + WorkOrder, 27 sources awaiting the owner-gated Phase 5.

**Round-12 hash freeze (superseded by round 13 above):** FINAL_DESIGN `d4841644…` · BUILD_AND_OPERATIONS `d917d553…` · STATUS_AND_HISTORY `61715ed5…` · ChannelContract `9e6ffcbb…` · frozen packet `aa7239ed…`. Owner wording review = the twelve external rounds recorded above.
- Remaining before/at Phase 5 (owner GO required; "do not archive yet" stands): the 14.4 archive tests execute AT the move (recompute every archived source hash vs the Phase-1 manifest · rewrite/validate every inbound citation incl. the 12 exact-filename citers and the three engine prompts · verify the root then contains only the intended live set) · CONSOLIDATION.md itself moves into the archive at the end.

**Eighth external round (2026-07-15) — Phase 4 REOPENED on the reviewer's block; all six findings source-verified REAL and fixed:**

- The premature "Phase 4 COMPLETE" claim is withdrawn: BUILD's own §11.5 transfer list still named source-resident exact blocks. Now CLOSED by transfer: kernel §15.0's MVP split (day-1 core, deferred-inert list, the no-XBRL coverage fence), §16's five honest residuals, and the six-item ratification bundle → BUILD §8.1; `12` §12's six mechanical acceptance gates including the full F1-F9 OD-21 failure traps + P1-P8 positive fixtures (with the P1/P2/P7 blocked-until-build note) → BUILD §5; the XBRL materializer's exact nine-step recipe with its P3/P4a-i/P5a/P8 pins → BUILD §8.2. The §11.5 list now records the transfers as closed; the hash-pinned experiment prompt packs stay live files by their pins.
- Rule completions in FINAL_DESIGN (each verified at source): OD-2's memo field schema (`66`:239 — the eight fact_type_decisions row extensions + live memo = node properties), honest residuals, and the owner's four worked examples · DU-15's exact selection (`07`:117 — headline primary, prior_year > sequential_period tiebreak, null for non-temporal anchors, fact-type-aware "exceeded expectations") · `company_confirmed` is REQUIRED core-derived on every guidance fact (`11`:118 — the matrix row was split; "allowed" had understated it) · FS-26 recovery completed (V14 extension to ContinuationClaim, the XBRL falsifier tripwire across declared boundaries, the no-XBRL false-continuity residual class) · OD-11's report-only basis-default monitor · OD-13's offline mixed-polarity monitor (suppressed on balanced drivers, deliberately not a hard-fail) · OD-14's series-lock on late fan-out writes + the DCM (company, trade-date) read-grouping.
- Crosswalk corrected and refined: per-sub-range anchors with a total-coverage law and exact per-ID exceptions (STATUS §7.1); the invented FACT-15b REMOVED (it exists only inside the retired OD-16 recommendation's proposal — not in `12`); the GI range corrected to GI-05..36 (GI-36 verified at `13_Track`:130). Status contradictions fixed: the dashboard consolidation row says Phase 4 in progress; the ChannelContract crosswalk row no longer carries the pre-amendment hash/description.
- On the reader test: the 10/10 stands FOR the ten §14.3 exercises (the reviewer verified the transcript), but the framing is corrected — it proves mental-model completeness, not implementation-readiness; four of the reviewer's five "unrecoverable" items are §10.3/BUILD §11 DOCUMENTED open recipes (absent from the frozen sources too — open by design, visibly labeled, per the §15 completion condition), and the fifth was the now-closed source-resident-block finding. Also conceded: the round-7 stale-phrase claim "every hit was history or negation" was not literally exhaustive — the §14.2 phrase "both labels" occurs coincidentally inside valid current law (FINAL_DESIGN §5.2's label-drift rule), a harmless collision now on record.
**Ninth external round (2026-07-15) — verified via a 9-agent parallel source-verification workflow (wf_19b3d1f6, ~497k tokens; every claim checked against verbatim source quotes; edits applied centrally after adjudication):**

- Verdicts: **8 REAL, 1 PARTIAL, 0 wrong.** The deepest catch of the session: FINAL_DESIGN's withdrawal fan-out wording had turned T11.7's PER-GUIDE exclusion ("a guide the same source replaces/reaffirms/keeps is NOT withdrawn") into a GLOBAL veto — under which "we withdraw all FY2026 guidance except EPS, which we reaffirm" would have produced ZERO withdrawn facts. Fixed to the per-guide law (my round-6 fix had copied `66` OD-14(d)'s ambiguous "ALL hold" grammar and dropped both per-guide signals; `11` T11.7 is the precise back-ported form). Consequently the second reader test is honestly re-scored **8/10**: its Q8 answer was file-induced (it read my wrong text correctly) and its Q6 percent_sequential answer assumed sub-annual instead of conditioning on the resolved period — the reviewer's "too generous" charge is CONCEDED.
- Also transferred/fixed on verified evidence: the VERBATIM DU-05/DU-06 classifier text inlined (a pointer to the archived `07` would have broken the no-archive goal); the full XBRL pin map P1a..P19 (no P18) added to BUILD §8.2; XC-17 monitoring + XC-18 production-scale rules added (FINAL §8 + the concept-link gate); OD-13's exact polarity-proof fields (`polarity` · `basis` · `evidence` · one sentence) + invalid-proof classes + the surprise `change_value` sign-unclear rule; OD-12's sign-signal/comparative traps + monitor character; DU-23's whole-verdict-SET grading sentence; the writer's direct-field no-op detection (DU-19/evhash16 retirement) in both FINAL §7.1 and BUILD §5; the TrackC crosswalk row widened to §§0-15 with the meta-section note (PARTIAL verdict — the row was not defective, belt-and-braces applied); all three banners, the dashboard cell, and the §14.4 root-check updated (round-9 carve-out: the hash-pinned experiment Plan/WorkOrder stay live at root until EXP-3..6 migrate — Phase 5's end state is the four live files + frozen packet + those two + the archive).
- Status/hash staleness (reviewer's finding 2) fixed: banners no longer say Phase 3; the superseded step-19 freeze below is replaced by the round-9 freeze at the end of this record.
**Tenth external round (2026-07-15; every claim source-verified before change — 7 REAL, 1 partly-real):**

- **XBRL pin map completed:** P16 was omitted entirely (verified at the candidate's §11: "menus narrow, evidence creates — five-point structural enforcement; no value/scale hints ever") and several pins were over-compressed — BUILD §8.2 now carries the FULL faithful pin map P1-P17+P19 (each pin's operative content, all sub-letters) PLUS the ten declared amendments (§12.3), and the "authoritative = archived file" wording is inverted (finding 2): THIS map is the operative candidate map; the archived file keeps full historical prose, non-authority — consistent with the archive README.
- **Missing final rules restored:** OD-13's position-words/loose-verbs rule ("above"/"ahead of"/"beat the budget" are never automatic favorability — polarity test) · PER-18's exact Cypher shape (MERGE-by-id + ON CREATE dates + unique constraint + pre-created sentinels) into FINAL §6.2 · PER-20's `HAS_XBRL` race guard as a producer ELIGIBILITY check (never inside the resolver) into the build order.
- **Kernel/Track B transfer exactness (finding 4, PARTIAL):** four real drops restored (recovery = raw evidence/no falsifier framing · audit bound = 100% first N/T then risk-stratified · the S3 test controls · the outage rule contents) and the fixture-shim mappings + the renamed-label/conflict-stays-split parenthetical added; the reviewer's fifth sub-claim (history-quality measure lost) was WRONG — §8.1 already carried the four-component dashboard measure verbatim.
- **Crosswalk GI correction (finding 5):** verified by enumeration — the retired file has its OWN GI-01..07 and GI-10..36 (separate numbering from the active file's GI-01..04; NO GI-08/GI-09 exist anywhere); the row now says exactly that.
- **Phase-5 self-contradiction resolved (finding 6):** step 21 now moves 31 of 33 (the two experiment files stay live until program migration, then archive with it); step 21c handles the WorkOrder's verbatim-text citations (re-point + re-record its hash — only the Plan is byte-pinned); step 24's end state = four live files + packet + the two experiment files + archive; §12.5's "sole exception" wording widened to match. The step-8 WorkflowContextPack live-code re-audit + link repair is now an explicit Phase-5 pre-step (21b) so it cannot be skipped (finding 7).
- **Smaller stales fixed:** §5.2 no longer calls the pre-amendment packet hash "current"; the front-door banner names BOTH packet amendments and the two experiment-file root exceptions.
**Eleventh external round (2026-07-15; verified via a second 5-agent fan-out, wf_40e8bbb0, ~398k tokens — verdicts 5 REAL + 1 PARTIAL across the reviewer's six findings, plus two inline-verified):**

- **Finding 1 resolved by POLICY, not transfer (the round's decisive adjudication, flagged for owner veto):** the kernel verifier enumerated ~68 kernel-only build-critical elements absent from BUILD §8.1 (the eight park codes, the five LINK-check meanings, all fourteen V1-V14 definitions, the falsifier definitions, gauntlet/phase mechanics…) — proof that a pre-ratification "exact map" is impossible short of duplicating the whole unratified candidate. Therefore the two candidate files (`FableAdmissionKernelDesign.md`, `XBRLIntegrationDesign.md`) now stay LIVE at the root until the owner ratifies or rejects each — like the experiment files; on acceptance the content transfers into law properly, on rejection it archives. BUILD §8's headers reframed accordingly (split + ratification bundle, not a full map); the crosswalk rows, §12.5 exceptions, §13 step 21 arithmetic (now 27 moves + 2 snapshots + 4 deferred; SIX of the 33 stay at root), step 24 end state, and the FINAL_DESIGN banner all updated to match. The XBRL sub-claims that were bounded WERE transferred (7 elements: filing-type set, the half-ULP value-compatibility definition, the exact ConceptResolution field schema, the graded-reversal mechanics, the TextBlock disposition, the step-9 date/created/source_type/edges stamps, the QUARANTINED-vs-CLAIM_FROZEN park rule).
- Finding 2 fixed: the census T-groups now have a per-group exact anchor table (STATUS §7.2, twelve rows with per-rule exceptions). Finding 3 fixed inline: Phase-5 arithmetic corrected to 27+2+4 with ONE consistent hash law (archive snapshots ↔ manifest; live amended files ↔ §16 freeze). Finding 4 fixed: the byte-pinned Plan's frozen authority ladder is resolved externally (step 21c note + STATUS row: its lock candidates stay live; its topic docs resolve to archive paths; precedence order unchanged); a new step 21d requires the reader test to be rerun against the ACTUAL post-archive root set before the migration commit. Finding 5 fixed inline: the §0 status sentence corrected (two owner-amended sources; the four files exist; front door = FINAL_DESIGN), all three banners now say round 11. Finding 6 fixed: T12.9's full grouping law (join-only-when-all-linked-facts-agree, conflict-log-as-alarm, linkless-follow-own-label, latest-label display, qname-string comparison), XC-18's ambiguous-intersections-only cache clause, and OD-12's five worked validator encodings.
- **Finding 8 executed — FULL ten-question fresh-reader test rerun against the round-10 hashes (FINAL `53ee2768…` · BUILD `6e0b784b…` · STATUS `826d1b65…` · contract `9e6ffcbb…` · packet `aa7239ed…`): PASS, 10/10** (agent aedf6c7d64c3d98ab, ~128k tokens). All ten exercises answered correctly with citations — including the previously-failed withdrawal composition (four facts: one source-stated `reaffirmed` + three code-generated numberless `withdrawn` with the per-guide exclusion, resolved-scope containment, and the OD-10 `series_unit` copy) and the conditional growth-basis question (sub-annual → `percent_sequential`; annual → `percent_yoy` with the validator pin), plus the correct documented-open-gap answer with citations on cross-channel ID escaping. This is the complete fresh-reader pass the reviewer required; the §14.3 check now stands against the CURRENT hashes.

- **Targeted re-probe after the fixes (fresh zero-context reader, the two failed questions only): BOTH PASS** (agent a5d4ae37e70c18423) — Q-withdrawal: fan-out NOT cancelled, one `reaffirmed` EPS fact + three code-generated numberless `withdrawn` facts with the OPEN/containment guards and the OD-10 `series_unit` copy cited; Q-basis: correctly CONDITIONAL on the resolved target period (sub-annual → `percent_sequential`; annual → `percent_yoy` via the annual pin), `cc` → the measurement slot. The fixed files teach the corrected law.

- **Second blank-context reader run (post-round-8 fixes): PASS — re-scored 8/10 in round 9 (see above)** (agent aeffc0d8d1720a4f9): the exact OD-1 memo schema + all seven hard-fails · the full OD-2 path on `buyback` with the eight decisions-row fields · the F/P fixture split incl. the three build-blocked positives · the kernel MVP day-1 list + no-XBRL coverage fence · the materializer's `pure`-unit fence + beyond-precision whole-scope skip · a cc-sequential guide (basis in `level_unit=percent_sequential`, measurement orthogonal, annual-pin aware) · the withdrawal-vs-same-source-reaffirmation composition (fan-out defeated by condition (d); series lock cited) · `company_confirmed` required/core-derived/skip-on-unclear · the dead-rule row-26 lookup, FS-20 contents home, and the six-item ratification bundle. Decisive: asked for the cross-channel ID-escaping recipe, it answered "DOCUMENTED OPEN GAP" with the exact BUILD §5/§11 + STATUS §6 citations rather than guessing — the labeled-open discipline held. Post-round-8 mechanical sweep: ALL GREEN (full §14.2 list; every hit a negation, a dead-rule column, a candidate-labeled section, or the recorded coincidence). The §14.3 and §14.1/14.2 checks are now CLOSED; only the §14.4 at-move tests + owner approval gate Phase 5.

- **Phase 3 files WRITTEN (2026-07-15, commits `4be553b` / `440fc58` / next):** `FINAL_DESIGN.md` (all 11 section-12.1 items; XC-04..07 exact content; five owner rulings folded into §3-§7), `BUILD_AND_OPERATIONS.md` (all 10 section-12.3 items incl. exact Track-A constants, kernel/XBRL candidate splits, signed experiment status, load-bearing hazards, section-10.3 gaps), `STATUS_AND_HISTORY.md` (dashboard · 42 terse supersession rows + additions · rulings record · signed experiments · crosswalk · manifest/evidence pointers). Reciprocal reading-order links ride in each banner (step 14); `ChannelContract.md`'s deep-law pointer re-points at Phase 4/5 with the rest of the inbound-citation crosswalk (its banner forbids non-owner edits). Process deviation, recorded honestly: section 13 step 5 prescribed ONE migration commit per phase; Phase 3 used one commit per discrete deliverable (amendment batch, three files) for reviewability — same no-interleaving intent, finer grain. NEXT = Phase 4: run every section-14 check, build the old→new anchor mapping, blank-context bot test, owner wording review, freeze target hashes.

- Scope-creep guard, recorded: the reviewer's proposed "final owner clarification" for Q1 was NOT installed as a new owner ruling — because none was needed. The owner separately confirmed the intended semantics in their own words (true = the company/management itself states it in its filings or transcripts; an analyst statement does not count unless the company later confirms it — the confirmation being a NEW `true` fact; `false` = stated by people outside management), and these match the existing law exactly. Its restating half is already law (core-derived who-said-it classification per `11`; `true`/`false` meanings per `99` §3.18's Locked and reserved text; company-confirms-later = a new `true` fact at its own public time, which follows from store-when-stated and OD-14 amendments-as-new-facts — history never rewritten). Its operative half — "a clearly identified outside-management claim may be stored as `company_confirmed=false`" — is NOT current law: it drops the reserved meaning's explicitly-ALLOWED-class gate, and who-said-it `false` derivation is explicitly part-2 / news-channel scope (`13`'s part-2 boundary). Admitting any third-party claim class is an owner decision to be taken there; nothing was enabled here.
