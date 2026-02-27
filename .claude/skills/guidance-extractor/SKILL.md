---
description: "Orchestrate guidance extraction from any source. For transcripts, runs PR extraction then Q&A enrichment."
---

Parse `$ARGUMENTS` as: `{TICKER} {SOURCE_TYPE} {SOURCE_ID} [MODE=dry_run|shadow|write]`

**For transcript sources** — spawn two agents sequentially via Task tool:

1. `Task(guidance-extract)`: `{TICKER} transcript {SOURCE_ID} MODE={MODE}`
   — Wait for completion before proceeding.
2. `Task(guidance-qa-enrich)`: `{TICKER} transcript {SOURCE_ID} MODE={MODE}`

Report combined results from both invocations.

**For all other source types** — spawn one agent:

1. `Task(guidance-extract)`: `{TICKER} {SOURCE_TYPE} {SOURCE_ID} MODE={MODE}`
