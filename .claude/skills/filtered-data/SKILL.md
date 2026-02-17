---
name: filtered-data
description: "DEPRECATED — use data sub-agents with --pit directly. See DataSubAgents.md."
allowed-tools: Skill, Bash, Read
skills: neo4j-report, neo4j-xbrl, neo4j-news, neo4j-entity, neo4j-transcript, perplexity-search
context: fork
model: sonnet
user-invocable: false
---

> **DEPRECATED (2026-02-17)** — Superseded by DataSubAgents architecture (`--pit` + `pit_gate.py` hooks).
> Use data sub-agents directly with `--pit <ISO8601>`. This skill is retained for reference only.

# FILTER PROTOCOL (LEGACY)

Arguments: $ARGUMENTS

## Step 1: PARSE
Extract: AGENT (after --agent), QUERY (after --query), PIT (from [PIT: datetime] if present)

## Step 2: FETCH DATA
Call Skill tool: skill=AGENT, args=QUERY
Store the COMPLETE response for validation.

## Step 3: VALIDATE (MANDATORY)
**YOU MUST EXECUTE THIS BASH COMMAND. DO NOT SKIP OR SIMULATE.**

First, output "[VALIDATING]" on its own line.

Then create a temp file with the COMPLETE response and validate it:
```bash
cat > /tmp/validate_input.txt << 'DATAEOF'
<paste the COMPLETE response from Step 2 here - every line, unmodified>
DATAEOF

cat /tmp/validate_input.txt | /home/faisal/EventMarketDB/.claude/filters/validate.sh --source "AGENT_NAME" --pit "PIT_TIMESTAMP"
```

**Example for perplexity-search:**
```bash
cat > /tmp/validate_input.txt << 'DATAEOF'
[
  {"title": "Article 1", "url": "...", "snippet": "...", "date": "2023-02-20"},
  {"title": "Article 2", "url": "...", "snippet": "...", "date": "2023-02-21"}
]
DATAEOF

cat /tmp/validate_input.txt | /home/faisal/EventMarketDB/.claude/filters/validate.sh --source "perplexity-search" --pit "2023-02-22T16:52:26-05:00"
```

The script outputs:
- "CLEAN" = data passes all checks
- "CONTAMINATED:PIT_VIOLATION:YYYY-MM-DD" = date after PIT found (exit code 1)
- "CONTAMINATED:FORBIDDEN_PATTERN:name" = forbidden field found (exit code 1)

**CRITICAL**: Show the exact output from the validation command. Do not paraphrase.

## Step 4: RETURN
Check what the validation bash command output:

**If the output was exactly "CLEAN":**
- Output "[VALIDATED:CLEAN]" on its own line
- Return the complete data response from Step 2

**If the output started with "CONTAMINATED:":**
- Output "[VALIDATED:CONTAMINATED]" on its own line
- Extract the violation type (e.g., "PIT_VIOLATION" or "FORBIDDEN_PATTERN")
- DO NOT return ANY data from the response
- Return error: "Data validation failed: [violation_type] violated PIT constraint"
- NEVER include specific dates, values, field contents, or article titles from contaminated data

**Example of correct contamination handling:**
```
Validation output: CONTAMINATED:PIT_VIOLATION:2025-06-04

Your response:
[VALIDATED:CONTAMINATED]
Data validation failed: PIT_VIOLATION violated PIT constraint
```

**REDACTION RULE**: When contamination detected, report ONLY the violation type. NEVER mention specific dates, values, article titles, URLs, or any content from the contaminated data.

**Execute steps 1-4 in order. Show [VALIDATING] and [VALIDATED:*] markers.**
