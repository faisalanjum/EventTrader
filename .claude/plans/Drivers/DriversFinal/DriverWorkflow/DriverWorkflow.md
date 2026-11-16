# Driver Workflow

> ⚠️ Living checklist: tick [x] when done · owner approves every other edit · fewest words.

**Goal:** turn unstructured text into Neo4j nodes/edges, stage by stage, until we trade company signals automatically. [Driver rules](../DRIVER_RULES_Categorized.md) apply. Updated 16 Nov 2026.

## Stages

- [ ] 1. **Drivers:** turn every source (SEC filings, transcripts, news, FiscalAI KPIs,  outside research) into Drivers and DriverUpdates.
- [ ] 2. **Explanations:** a workflow links each price move to the Driver updates behind it ([EXPLAINED_BY](../EXPLAINED_BY.md)).
- [ ] 3. **Context graph:** use the nodes, links and reasoning traces to know everything important about a company, with minimal noise.

## Company workflow

Build a company's context → keep it updated → trigger trade signals.

1. **Company context:** read the company's history; save its facts as Drivers and DriverUpdates, covering all 4 rulebook fact types (`metric`, `guidance`, `surprise`, `action_event`).
   - [ ] Organize `DRIVER_RULES_Categorized.md`.
   - [ ] Run the [Decider](DeciderExtraction.md) on every source type.
   - [ ] Do 1 company, then 2, then 10, logging each run, until first-context creation is automatic.
   - [ ] Check the finished context with [Perplexity Finance](https://www.perplexity.ai/hub/solutions/finance) for anything missing (catalysts, earnings analysis; data: Benzinga, EDGAR, Fiscal.ai, FMP, MT Newswires, Quartr …). Notes: [perplexity.md](../perplexity.md).
   - [ ] Pick the plan: which plans include this data isn't published, so test 1 month of individual Pro ($20) on one company; Enterprise Pro ($40) only for no-training protection.
2. **Update + trigger** (proposed: the [Decider](DeciderExtraction.md)): does a new report, news story or call update an existing Driver? If yes, send it through fact creation. Is the change worth evaluating as a trade?
3. **Quarterly review:** at each quarterly report, look deeper for new Drivers, missing updates and changes; feed them into the same history.

All three would use one shared creator (below).

## Base + copies → [details](BaseAndCopies.md)

Several readers share one document: Claude loads it once, and copies reuse it. Tested: ~97% of input reused from cache · every reader must see the whole document (partial views broke cell references) · more readers = faster, not more complete · "success" can hide a safety stop, so check coverage · automatic scores overstated accuracy, so grade against an independent answer key.

## Shared creator → [details](SharedCreator.md)

Idea, not vetted: one shared creator, a single interface every caller uses to turn a document into checked Driver updates, so creation rules never split into versions.
