---
description: "Orchestrate two-phase guidance extraction from earnings call transcripts: PR extraction then Q&A enrichment."
---

Parse `$ARGUMENTS` as: `{TICKER} transcript {SOURCE_ID} [MODE=dry_run|shadow|write]`

Spawn two agents sequentially via Task tool:

1. `Task(guidance-extract)`: `{TICKER} transcript {SOURCE_ID} MODE={MODE}`
   — Wait for completion before proceeding.
2. `Task(guidance-qa-enrich)`: `{TICKER} transcript {SOURCE_ID} MODE={MODE}`

Report combined results from both invocations.
