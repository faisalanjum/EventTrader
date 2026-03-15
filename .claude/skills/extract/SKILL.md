---
description: "Generic extraction orchestrator. Runs any extraction type against any data asset. Spawns primary + optional enrichment agents."
disable-model-invocation: true
argument-hint: "TICKER ASSET SOURCE_ID TYPE= MODE= PRIMARY_MODEL= ENRICHMENT_MODEL="
---

ALWAYS use `ultrathink` for maximum reasoning depth.

Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} [PRIMARY_MODEL={PM}] [ENRICHMENT_MODEL={EM}] [RESULT_PATH={PATH}]`

Defaults: `MODE=dry_run`

## Step 1: Run primary pass

Spawn via Agent tool (wait for completion). If `PRIMARY_MODEL` was provided, pass it as the `model` parameter:

```
Agent(subagent_type=extraction-primary-agent, model={PRIMARY_MODEL}): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

If `PRIMARY_MODEL` was NOT provided, omit the `model` parameter (agent frontmatter default applies):

```
Agent(subagent_type=extraction-primary-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

Read the result file: `/tmp/extract_pass_{TYPE}_primary_{SOURCE_ID}.json`

If primary pass failed, skip enrichment. Report the failure.

## Step 2: Check and run enrichment pass (conditional)

Run enrichment ONLY IF both conditions are true:
1. File exists: `.claude/skills/extract/types/{TYPE}/enrichment-pass.md`
2. File exists: `.claude/skills/extract/types/{TYPE}/assets/{ASSET}-enrichment.md`

If both true, spawn via Agent tool (wait for completion). If `ENRICHMENT_MODEL` was provided, pass it as the `model` parameter:

```
Agent(subagent_type=extraction-enrichment-agent, model={ENRICHMENT_MODEL}): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

If `ENRICHMENT_MODEL` was NOT provided, omit the `model` parameter (agent frontmatter default applies):

```
Agent(subagent_type=extraction-enrichment-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

Read the result file: `/tmp/extract_pass_{TYPE}_enrichment_{SOURCE_ID}.json`

## Step 3: Report results

Combine primary + enrichment results.

If `RESULT_PATH` was provided (worker invocation):
- Write combined result to `RESULT_PATH` via Write tool:
  ```json
  {"type": "{TYPE}", "source_id": "{SOURCE_ID}", "status": "completed", "primary_items": N, "enriched_items": N, "new_secondary_items": N}
  ```

If `RESULT_PATH` was NOT provided (manual invocation):
- Report results as text in the conversation

Clean up pass result files: delete `/tmp/extract_pass_{TYPE}_*_{SOURCE_ID}.json`
