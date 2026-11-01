# ReasoningTraceQuestions.md — the 10 questions the reasoning-trace graph must answer

> **Scope / status:** This is a NEW, standalone artifact for the **reasoning-traces layer**
> (storing *why* the predictor/learner decided, linked to Drivers + existing nodes). It is **NOT**
> part of the locked four-file Driver rulebook (`FINAL_DESIGN.md` / `BUILD_AND_OPERATIONS.md` /
> `STATUS_AND_HISTORY.md` / `ChannelContract.md`) and does not modify the frozen seven-file set.
> Additive only. Full study + the empirical library evaluation live in
> `.claude/plans/ReasoningTraces.md`. Created 2026-07-18.

## Why this file exists (the method)

Neo4j's own guidance for building a context graph: **don't design the schema in the abstract —
first write down the questions the graph must answer** (10–20, ideally with answers you already
know, so you can test it). The schema is then "whatever makes these answerable." (Going Meta S3E9
Jesús: *"the model is driven by a collection of questions"*; Deep-Dive 2026-07-17 Jean-Marc:
*"set 10–20 questions… it's a lot easier to iterate."*)

These are **our** questions — chosen by ONE test: *does answering this change a future call?* The
north star is **improve prediction accuracy** (and let agents learn what to adopt vs reject), NOT
audit for its own sake. Each also silently tests whether the proposed trace schema is complete.

> **v2 (2026-07-18) — refined by the north star.** Dropped two pure-audit questions ("why did we
> call X" = the substrate every question reads, not a question; "does reading Q&A help" = process
> trivia). Added three trading-critical ones that target what actually blows up an earnings system:
> **calibration** (over/under-confidence), the **beat-and-drop pattern** (good news → stock falls,
> which is exactly the AVGO case), and **right-for-the-right-reason** (skill vs luck).

## The proposed schema these questions must satisfy

```
NEW nodes:  ReasoningTrace · ReasoningStep · ToolCall · Tool · TraceOutcome
NEW edges:  HAS_STEP · USES_TOOL · INSTANCE_OF · TOUCHED · FOR_EVENT · ABOUT · OUTCOME
key props:  ReasoningTrace.kind ("prediction" | "learner")  ·  ReasoningTrace.pit_cutoff
```
Traces hang off existing nodes (`Company`, `Report`, `Fact`, `QAExchange`, `GuidanceUpdate`,
`News`, and — when the catalog gives a canonical name — `Driver` / `DriverUpdate`).

## The 10 questions

**Do we trust our own calls?**
1. **Calibration** — when we say 70% confidence, are we right ~70% of the time? *(hit-rate by
   confidence bucket)*
2. **Right for the right reason** — on our WINS, did the stated `falsifier` behave, or did we get
   lucky? *(skill vs luck)*

**Where do we systematically fail?**
3. **Beat-and-drop / miss-and-rally** — when the stock moved OPPOSITE the earnings surprise, what
   did those setups share? *(the AVGO case — the highest-value learnable pattern)*
4. **Recurring misread** — across all misses, which driver / setup / company do we repeatedly get
   wrong?

**Which signals to trust?**
5. **Driver trust** — per driver, when we key off it: hit-rate and mean error. Trust or distrust?
6. **Lesson value (adopt / reject)** — which past lessons, when applied, improved the call — and
   which misled us?

**What can't we see?**
7. **Fundamental blind spots** — which drivers the learner says moved the stock did the predictor
   never look at?
8. **Non-fundamental blind spots** — how often was the real cause positioning / flow / macro (a
   cause with no driver node)?

**Reuse & integrity**
9. **Case retrieval (the router)** — given today's setup, the most similar past reasonings and how
   they turned out.
10. **PIT safety** — would every input to this call have been visible before the event?

## What each question maps to (the schema test)

| Q | Answered by | Ready? |
|---|---|---|
| 1 Calibration | `Trace.confidence` + `TraceOutcome.direction_correct` (EV1 already computes Brier §18) | ✅ data exists |
| 2 Right-for-reason | `result.falsifier` + learner §15 falsifier-check + `OUTCOME` | ✅ data exists (underused) |
| 3 Beat-and-drop | surprise sign vs `actual_return` sign + shared `TOUCHED` context | 🟡 finds cases; shared setup includes non-fundamental (see Q8) |
| 4 Recurring misread | `OUTCOME.direction_correct=false` grouped by `driver_id` / company / setup | ✅ needs driver bridge |
| 5 Driver trust | `Step -TOUCHED-> Driver` + `OUTCOME`, group by driver | ✅ needs driver bridge |
| 6 Lesson value | predictor applied lesson (cite) → `OUTCOME` delta | 🟡 needs lesson→outcome link (§6 prior-reports is the surface; §12 dropped the lesson lifecycle) |
| 7 Fundamental blind spots | learner-Driver **minus** predictor-Driver on `FOR_EVENT` | ✅ needs driver bridge + `kind` |
| 8 Non-fundamental blind spots | learner cause with **no** Driver node | ❌ **no node for non-fundamental causes** (Hole 2) |
| 9 Case retrieval | vector over `ReasoningStep.embedding` + `OUTCOME`, PIT-filtered | 🟡 embedder open; feeding predictor contradicts §6 |
| 10 PIT safety | `WHERE trace.pit_cutoff < $as_of AND trace.kind` | ✅ well-designed |

## Readiness (current design)

- **Today, without the driver bridge:** ~4.5 / 10. The high-value driver questions (4, 5, 7) are
  blocked because `key_drivers.driver` is free text (§7) with no link to the catalog.
- **After the driver bridge** (predictor emits a canonical `driver_id`): ~8 / 10 — Q4/5/7 flip to
  answerable in one move.
- **The last ~1.5 points are two DECISIONS, not builds:**
  - **Q8** → non-fundamental causes (positioning, run-up, flow, macro) have no node, so aggregates
    silently under-count them and over-report "fundamentals drive stocks." Your own AVGO primary
    driver WAS positioning. Either accept-and-label the blind spot, or add a small controlled set
    of non-fundamental cause tags.
  - **Q9** → retrieval must be **PIT-safe** (`pit_cutoff` in Cypher, never a prompt), the embedder
    is an open cost/quality call (small local models proven weak on financial paraphrase —
    `ReasoningTraces.md` §0.5), and feeding similarity INTO the predictor contradicts §6's
    deterministic selection (fine for human analysis; a decision for the prediction loop).

## How to validate (free, when built)

We already have known answers (AVGO backfill, the 3 learner results, EV1 scores). Build the trace
graph, ask these 10, check the answers match. That's the validation set at zero cost — exactly the
"set questions you already know the answers to" step from the talk.

## Blocker (unchanged)

`Step -TOUCHED-> (:Driver)` — questions 3/4/5/9 — cannot be written until the Driver catalog gives
the predictor a **canonical driver name** to link to (`PredictorLearner/Final.md` §7 currently:
"Drivers are short causal phrases; no controlled vocabulary"). Company/Report/QAExchange links
(questions 1/2/6/10) work today. Build those first; the Driver edges slot in when the catalog lands.
</content>
