---
description: "Generic extraction orchestrator. Runs any extraction type against any data asset. Spawns primary + optional enrichment agents."
---

Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} [RESULT_PATH={PATH}]`

Defaults: `MODE=dry_run`

## Step 1: Check asset for secondary sections

Read `.claude/skills/extract/assets/{ASSET}.md` and find `## Asset Metadata` section. Check the `sections:` field.

- If sections contains more than one entry (e.g., `prepared_remarks, qa`) → asset has secondary sections
- If sections is just `full` → asset has no secondary sections

## Step 2: Run primary pass

Spawn via Agent tool (wait for completion):

```
Agent(subagent_type=extraction-primary-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

Read the result file: `/tmp/extract_pass_{TYPE}_primary_{SOURCE_ID}.json`

If primary pass failed, skip enrichment. Report the failure.

## Step 3: Check and run enrichment pass (conditional)

Run enrichment ONLY IF both conditions are true:
1. Asset has secondary sections (from Step 1)
2. File exists: `.claude/skills/extract/types/{TYPE}/enrichment-pass.md`

If both true, spawn via Agent tool (wait for completion):

```
Agent(subagent_type=extraction-enrichment-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

Read the result file: `/tmp/extract_pass_{TYPE}_enrichment_{SOURCE_ID}.json`

## Step 4: Report results

Combine primary + enrichment results.

If `RESULT_PATH` was provided (worker invocation):
- Write combined result to `RESULT_PATH` via Write tool:
  ```json
  {"type": "{TYPE}", "source_id": "{SOURCE_ID}", "status": "completed", "primary_items": N, "enriched_items": N, "new_qa_items": N}
  ```

If `RESULT_PATH` was NOT provided (manual invocation):
- Report results as text in the conversation

Clean up pass result files: delete `/tmp/extract_pass_{TYPE}_*_{SOURCE_ID}.json`
