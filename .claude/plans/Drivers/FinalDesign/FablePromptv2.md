# Fable Prompt v2: XBRL-Native Driver / DriverUpdate Integration

## 1. Mission

Your task is to design the minimal way for existing Neo4j XBRL facts and LLM-extracted 10-K/10-Q text to become one natural Driver/DriverUpdate system.

The goal is not to create a separate XBRL system.

The goal is to decide how XBRL should fit inside the existing Driver and DriverUpdate framework so that:

- XBRL-covered facts are reused instead of re-extracted,
- non-XBRL market-moving facts are still captured,
- duplicate DriverUpdates are avoided,
- Driver identity is not damaged,
- the design stays minimal and natural.

## 2. Read Context First

Do not reason from memory.

First read:

1. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableAdmissionKernelDesign.md`
2. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/FableContextPack.md`
3. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/08_XBRL_ConceptLinking.md`
4. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/12_TrackB_FactPipeline.md`
5. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/10_BuildPipeline.md`
6. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/03_Slices_FactScope.md`
7. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/06_MetricFamily.md`
8. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/09_DriverUpdate_Fields.md`

Then, only if needed, inspect the existing Neo4j/XBRL/query context:

- `/home/faisal/EventMarketDB/.claude/skills/report-queries/SKILL.md`
- `/home/faisal/EventMarketDB/.claude/skills/extract/assets/10k-queries.md`
- `/home/faisal/EventMarketDB/.claude/skills/extract/assets/10q-queries.md`
- `/home/faisal/EventMarketDB/drivers/docs/NEO4J_SCHEMA_v3.md`
- `/home/faisal/EventMarketDB/drivers/docs/XBRL_PATTERNS.md`
- `/home/faisal/EventMarketDB/drivers/docs/NON_XBRL_PATTERNS.md`

Use these to understand the existing system. Do not treat helper/context files as authority.

Authority order:

1. FinalDesign topic docs.
2. `90_OpenItems.md` and `95_Supersession.md`.
3. `FableAdmissionKernelDesign.md` v3.4 as current kernel baseline.
4. Context packs and code maps as navigation only.

## 3. Scope

Focus only on 10-K and 10-Q filings.

Do not redesign predictor, learner, trading logic, or the whole Driver admission kernel unless XBRL integration exposes a direct contradiction.

This task includes both:

- Driver creation/reuse, including all four fact_types:
  - `metric`
  - `guidance`
  - `surprise`
  - `action_event`

- DriverUpdate creation, including:
  - value
  - unit
  - period
  - slice
  - measurement
  - source evidence
  - XBRL concept/member links where applicable

## 4. Core Question

For each market-relevant fact in a 10-K or 10-Q, what is the cleanest source of truth?

Possible answers may include:

- XBRL-derived
- text-derived
- hybrid XBRL + text
- skip as duplicate
- park/fail closed

Do not assume these categories are complete or correct. Analyze whether they are right, wrong, or missing a better option.

## 5. Important Tension

XBRL is structured and cheap, but it may not express full market meaning.

Text is rich, but expensive and easier for weak LLMs to duplicate or distort.

The design must find the natural boundary between them.

Do not think in section-level terms unless you prove section-level routing is valid.

A 10-K/10-Q section can contain both:

- XBRL-covered numeric facts,
- and untagged narrative facts that still matter to the market.

## 6. What Fable Must Produce

Produce a clear design answer, not a vague architecture.

Your output should include:

1. Context summary:
   What the existing Driver/DriverUpdate design already does.
   What the existing XBRL infrastructure already provides.

2. Problem statement:
   The exact integration problem in one paragraph.

3. Design options:
   Compare the strongest possible approaches.
   Do not assume the owner's wording is correct.

4. Recommendation:
   The cleanest minimal design.

5. Boundary policy:
   How the system decides whether a fact is XBRL-derived, text-derived, hybrid, skipped, or parked.

6. Driver/DriverUpdate integration:
   How XBRL concepts, members, periods, units, values, slices, and source evidence connect to Driver and DriverUpdate.

7. Duplicate and miss prevention:
   How the design prevents both:
   - writing the same fact twice,
   - missing non-XBRL market-moving facts.

8. Fit with v3.4:
   Whether the design changes the v3.4 admission kernel, extends it, or leaves it unchanged.

9. Minimal proof:
   The smallest experiments needed to prove recall, precision, and cost improvement.

## 7. Hard Constraints

- Do not create a parallel XBRL catalog.
- Do not create a parallel fact system.
- Driver and DriverUpdate remain the market-memory layer.
- XBRL must integrate naturally into that layer.
- No human review in normal operation.
- Code checks structure; LLMs judge meaning.
- Over-merge remains worse than over-split.
- Missing a market-moving fact is also unacceptable.
- Minimal machinery only.

## 8. Final Answer Shape

Start with:

1. One-sentence answer.
2. The key design choice.
3. The main risk.
4. The recommended next step.

Then give the full reasoning.

If the current design already handles this cleanly, say so.

If it does not, propose the smallest change.
