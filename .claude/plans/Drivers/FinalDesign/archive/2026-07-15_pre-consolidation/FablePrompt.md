# Fable Driver Catalog Design Challenge

## 1. Fable Focus

Your budget is constrained. Use Opus/Sonnet when spawning sub-agents unless the quality of Fable is truly needed.

The current baseline is `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableAdmissionKernelDesign.md` v3.4 plus the live FinalDesign topic docs and ledgers.

The purpose of this session is not to rubber-stamp v3.4, and not to restart from scratch. The purpose is to stress-test v3.4, find any fatal gaps, stale text, hidden failure modes, or needless complexity, and propose the smallest better design only if one exists.

Fable must think with full attention about how to create Drivers inside a living Driver/DriverUpdate system, where the catalog can be created in batch and also extended later on demand without damaging identity.

Nothing in this prompt is itself a new locked design.

Existing locked rules and owner-approved decisions in the FinalDesign docs must be preserved unless Fable explicitly identifies a contradiction, a hidden failure mode, or a better minimal rule for the owner to consider.

The open design challenge is the next iteration of the admission process: how to confirm, harden, simplify, or minimally revise the no-human Driver reuse/create/rewrite/skip/park path without damaging Driver identity.

## 2. Context Loading Instructions

Before solving, read:

1. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableAdmissionKernelDesign.md`
2. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableContextPack.md`
3. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/WorkflowContextPack.md`
4. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/66_IssuesToBeHandled.md`

Treat `FableAdmissionKernelDesign.md` v3.4 as the current kernel baseline.

Treat `FableContextPack.md` as the navigation and status map, not as authority.

Treat `WorkflowContextPack.md` as the map of old workflow code: useful for implementation and experiments, but stale wherever it conflicts with FinalDesign rules.

Use it to decide which source docs to open next.

On conflict, topic docs plus `90_OpenItems.md` and `95_Supersession.md` win over context packs. v3.4 wins for the current kernel synthesis unless it conflicts with those binding docs.

Pay special attention to already-decided or partially-decided admission rules:

- `12 §10.6` missing-Driver handling,
- `10 PIPE-13` G2 admission,
- `10 PIPE-22` propose-first,
- OD-1 terminal suffix admission,
- OD-2 bare-name fact_type proof,
- OD-3 name-vs-slice local role rule,
- OD-7 live-created Driver fact_type/family stamping recommendation,
- OD-15 concurrent live Driver creation / near-synonym over-split handling,
- `95 #26-#30` and `90 §E` status cleanups,
- `95 #39` / `10 PIPE-11 D4` scoped automatic quarantine.
- 2026-07-08 model default: Haiku or another cheap/lower-intelligence model for blind leaf Driver proposals; Sonnet 5 as the default strong-judge candidate for judgments, Refute, LINK/SAME_AS, BASE_METRIC/fact_type confirmations, quarantine, and similar identity-changing checks; higher models only if experiments prove they are needed.
- 2026-07-08 chunking idea: test paragraph-at-a-time source chunks versus huge wall-of-text chunks for blind leaf producers, but adopt only if automatic chunking preserves context and does not reduce recall/precision.

## 3. Scope

There are two parts to the full system:

1. Process of creating Driver Catalog and DriverUpdate facts.
2. Later consumers of those facts, such as predictor and learner.

This session focuses on the creation layer, especially Driver creation.

Do not spend meaningful effort designing predictor or learner loops, except where the Driver/DriverUpdate design must support them later.

The narrower focus is:

- designing the Driver creation process,
- preserving all rules and constraints,
- making the process autonomous,
- making it safe for both batch catalog creation and future on-demand Driver creation.

## 4. North Star

Imagine the system is fully built with Driver Catalog and DriverUpdate.

The design should be able to autonomously generate useful market signals with no human in the loop and with recall and precision as close to 100% as possible.

The system should avoid any review dependency. Humans should not be needed to approve, fix, or manually inspect normal Driver creation or DriverUpdate creation.

The Driver and DriverUpdate graph should become powerful even before prediction and learner loops are added.

It should become useful because it is:

- well designed,
- well connected,
- fully automated,
- actionable,
- useful for automatic trading.

The graph should become intelligent through its structure:

- Drivers,
- DriverUpdates,
- sources,
- companies,
- events,
- periods,
- concepts,
- members,
- verdicts,
- time.

These should connect in the right way so the system becomes more useful as new assets arrive.

## 5. Aim And Core Rules Reference

### The Aim

Create a market memory that maps messy event text into stable causes, so the system can learn what truly moves stocks.

We are building a reusable memory of market causes.

Without the Driver Catalog, every earnings call, filing, or news item is just fresh text.

The system would see "same-store sales," "comps," "restaurant sales," and "Taco Bell SSS" as scattered phrases.

The catalog turns them into one clean cause, so every future fact can line up.

```text
raw event text
    -> reusable cause name
    -> event fact
    -> stock-move verdict
    -> history
    -> learning / trading signal
```

The primary reasons:

- Create one stable identity per cause.
  So `same_store_sales` means the same reusable idea across events and companies.

- Turn messy text into clean histories.
  We need time series of causes, not isolated documents.

- Separate cause from occurrence.
  `revenue_guidance` is the cause class. "Company raised FY25 revenue guidance today" is one fact.

- Connect causes to stock reactions.
  The real prize is not "what happened." It is "what moved the stock, how often, and in what direction?"

- Learn across companies and time.
  If the same Driver appears at many companies, the system can learn patterns: which causes matter, when, for whom.

- Make future prediction possible.
  A predictor cannot learn from random wording. It needs stable cause names and clean fact histories.

- Make the graph tradeable even before ML.
  You can query: "Which causes changed today that historically moved stocks long or short?"

- Protect the system from permanent meaning damage.
  The catalog is the identity spine. If two different causes get merged, every later fact and lesson is polluted.

- Build a self-improving market memory.
  Every new source should either reuse an existing Driver or carefully create a new one, making the system stronger over time.

So the Driver Catalog is not mainly a list of names.

It is the cause identity layer for the whole trading system.

Without it, there is no clean history, no reliable learning, and no trustworthy prediction.

### Driver Catalog Creation Rules

#### Core Rules

- A Driver is a reusable cause, not one event.
- The catalog creates Driver classes only, never DriverUpdate facts.
- If unsure whether two names mean the same thing, keep them separate.
- Over-merge is the worst failure; over-split can be fixed later.
- Every Driver must be backed by source evidence.
- Do not invent broad names. Broadness must come from repeated reuse.
- A new Driver is allowed only if it is reusable, source-grounded, and clear.

#### Name Format

- Use lowercase snake case: `same_store_sales`.
- Use letters, digits, and underscores only.
- Start with a letter.
- No double underscores.
- No trailing underscore.
- Keep names short and noun-like.
- Use familiar finance terms when they exist: `gross_margin`, `free_cash_flow`.
- Keep standard phrases intact.

#### What Goes In The Name

- The reusable cause.
- External causes or actors when they are the thing driving the company.
- Unclear-role objects, when unsure if they are internal slice or external cause.
- Per-X denominators: `price_per_barrel`, `revenue_per_store`.
- Benchmark identity when it changes meaning.
- Terminal family suffixes only: `_guidance`, `_surprise`.

#### What Does Not Go In The Name

- Company name.
- Ticker.
- Date.
- Period.
- Number.
- Unit.
- Direction: up, down, rising, falling.
- State: raised, lowered, beat, missed.
- Size: big, small, major, minor.
- Source type: 8-K, transcript, news.
- Own segment, product, geography, customer, channel, or owned entity.
- Measurement/version words: adjusted, diluted, constant-currency, GAAP, non-GAAP.
- XBRL prefixes or accounting tag noise.
- Sentiment words like good, bad, strong, weak.

#### Name Vs Slice

- Own measured company part goes to slice, not name.
- Example: `same_store_sales` + `slice=segment:taco_bell`.
- Not: `taco_bell_same_store_sales`.
- External object stays in the name.
- Example: Qualcomm hurt by iPhone demand -> `iphone_demand`.
- If role is unclear, keep it in the name to avoid unsafe merging.

#### Measurement Rule

- `adjusted_eps` is wrong.
- Correct: `eps` with `measurement=adjusted`.
- `diluted_eps` is wrong.
- Correct: `eps` with `measurement=diluted`.

#### Family Rules

- `metric`, `guidance`, `surprise`, and `action_event` are separate Driver types.
- Do not merge `revenue`, `revenue_guidance`, and `revenue_surprise`.
- Every `_guidance` Driver must link to exactly one base metric with `BASE_METRIC`.
- Every `_surprise` Driver must link to exactly one base metric with `BASE_METRIC`.
- `action_event` Drivers do not need a base metric.
- Suffix must be terminal: `revenue_guidance`, not `guidance_revenue`.

#### SAME_AS Rules

- Use `SAME_AS` only for true synonyms.
- Do not use `SAME_AS` to link metric to guidance or surprise.
- Do not delete either name just because they are linked.
- Missing a link is fixable; wrong merging is dangerous.

#### Catalog Content Rules

- Driver can store: name, fact_type, evidence, `SAME_AS`, `BASE_METRIC`.
- Driver must not store: value, unit, period, slice, state, verdict, company-specific XBRL concept.
- XBRL links belong later on facts, not in the catalog.
- No event-specific data belongs in the catalog.

#### Build Rules

- Names are born from source text, not from a fixed word list.
- The AI can propose names.
- Code and validators enforce structure.
- Final catalog must stamp exactly one fact_type per Driver.
- Final catalog must validate family links before use.
- Rule changes must be general principles, not one-off sector examples.

## 6. Deepest Worry

The deepest Driver Catalog worry is that weak LLMs, used over time, will quietly break the catalog as a complete, source-backed, one-name-one-meaning map of market-moving causes.

Failure modes include:

- missing real reusable causes,
- merging different causes into one Driver,
- splitting one cause into near-duplicates,
- coining vague or inconsistent names,
- stamping the wrong type/family.

The dangerous case is that the catalog still looks neat and valid while it no longer reliably means:

```text
one Driver = one stable cause
```

## 7. Non-Negotiable Requirements

- Driver and DriverUpdate should be continuously and autonomously updated.
- There should be absolutely no human in the loop and no normal need for review.
- The system should handle parked and fail-closed facts automatically and efficiently.
- Parked or failed cases should be minimized as much as possible, ideally near none.
- The design should be as minimal as possible while preserving reliability.
- Do not add complex machinery unless it clearly improves recall, precision, cost, speed, or reliability.
- The design should fit naturally and instinctively with the entire process.

## 8. Expected Output

Fable's output must not be a vague architecture.

It should:

- compare design choices,
- reject weaker options,
- recommend the simplest design that satisfies the requirements,
- explain what should be built,
- explain what should not be built,
- define what must be tested,
- define the model strategy,
- define the experiment plan,
- identify unresolved risks or decisions,
- produce an implementation-ready design structure.

Optimize for:

- autonomy,
- recall,
- precision,
- Driver identity safety,
- minimalism,
- cost,
- speed,
- reliability.

## 9. Primary Fable Task: Unknowns-First Design Of The Driver Identity Admission Kernel

Section 9's required output is the concrete deliverable.

Section 8 describes the quality bar the deliverable must satisfy.

Your single highest-impact task is to audit and, only if necessary, revise the v3.4 Driver Identity Admission Kernel.

Do not discard v3.4. Treat it as the baseline to attack from first principles. If it survives, say so and recommend only the smallest cleanup, experiment, or implementation next step. If it does not survive, explain the exact failure and produce the minimal v3.5 delta.

This is the one core process that decides, for every source-backed candidate market cause, whether the system should:

1. reuse an existing Driver,
2. admit a new Driver,
3. rewrite the proposed Driver name and re-check it,
4. skip because no reusable cause exists,
5. or park/fail closed because the system cannot decide safely.

This kernel must work for both batch Driver Catalog creation and live/on-demand Driver creation during DriverUpdate extraction.

There must not be separate batch and live identity logic.

Before proposing any change, do a blind-spot pass.

Classify the unknowns:

- Known knowns: what the current rules already lock.
- Known unknowns: what the docs admit is unresolved.
- Unknown knowns: assumptions the owner may have but has not written clearly.
- Unknown unknowns: failure modes or missing design questions the current docs may not even notice.

Your job is not just to follow the current plan.

Your job is to discover where the plan could still silently fail.

The central danger to solve:

Weak LLMs, over time, may quietly break `one Driver = one stable cause` by missing real reusable causes, merging different causes, splitting one cause into duplicates, coining vague names, or stamping the wrong type/family, while the catalog still looks clean.

Confirm or revise the simplest production-safe admission kernel that prevents this.

The design must define:

- what evidence is required before a candidate Driver can be considered,
- what the producer proposes before seeing reuse candidates,
- exactly what reuse view the producer sees after proposing,
- how company, industry, sector, global, semantic, `SAME_AS`, `BASE_METRIC`, slice, and XBRL context are shown,
- what must never be shown,
- when to reuse,
- when to create,
- when to keep separate,
- when to rewrite,
- when to skip,
- when to park or fail closed,
- how `fact_type` is stamped,
- how guidance/surprise `BASE_METRIC` links are created,
- how `SAME_AS` is allowed without destroying identity,
- how validators enforce all structure rules,
- what model strength is needed at each decision point,
- what can be deterministic code,
- what must be LLM judgment,
- what tests prove the kernel protects `one Driver = one stable cause`.

Hard constraints:

- No human review in normal operation.
- Over-merge is worse than over-split.
- Missing a link is safer than a wrong link.
- Driver names must remain source-backed.
- Broad names must emerge from reuse, never be invented.
- Batch and live creation must share the same identity logic.
- Parked/fail-closed cases should be minimized, but never hidden.
- Minimal machinery only: add complexity only if it improves recall, precision, cost, speed, or reliability.

Required output:

1. Blind-spot pass: the most important unknowns and hidden risks remaining in v3.4.
2. Kernel verdict: keep v3.4 as-is, revise it minimally, or reject a part of it with a stronger replacement.
3. Recommended kernel design or delta: the exact decision flow from candidate cause to final outcome, clearly marking what is unchanged from v3.4 and what changed.
4. Reuse-display policy: confirm v3.4 or give the exact minimal correction.
5. Admission policy: precise rules for reuse/create/rewrite/skip/park.
6. Family policy: `fact_type`, `SAME_AS`, `BASE_METRIC`, and terminal suffix handling.
7. Validator policy: deterministic checks and fail-closed gates.
8. Model policy: cheapest safe model strategy for each step, starting from the 2026-07-08 owner default above, with Fable only where quality truly matters.
9. Evaluation plan: tests and adversarial cases proving near-100% recall/precision, tied explicitly to `10 PIPE-37` and OD-6's quality budget.
10. Rejected alternatives: weaker designs and why they fail.
11. Final minimal spec: implementation-ready, with no vague architecture.

If file write access is available and a design change is needed, update `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableAdmissionKernelDesign.md` in place. Do not create a new side document or changelog unless explicitly asked.

Do not spend the main effort on predictor, learner, report scope, full backfill strategy, or generic model benchmarking unless it directly changes the admission kernel.

Optimize for the north star: a no-human, continuously growing Driver/DriverUpdate graph where every new source either safely reuses an existing cause or safely creates a new one, making the market memory more useful over time without corrupting Driver identity.
