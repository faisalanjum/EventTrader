# Extraction Instruction Stack

Repo-grounded visual map of what the current generic extraction pipeline loads, in what order, for the concrete path:

```text
TYPE=guidance
ASSET=transcript
```

This shows what the two generic skeleton agents actually see, not just the intended architecture.

---

## 1. Big Picture

```text
Worker SDK
  |
  | query("/extract AAPL transcript {SOURCE_ID} TYPE=guidance MODE=write RESULT_PATH=...")
  v
/extract orchestrator skill (runs in main SDK session, NOT forked)
  |
  | Step 1: reads transcript.md → checks sections field
  | Step 2: spawns primary agent via Agent tool
  |
  +--> extraction-primary-agent (subagent)
  |      |
  |      +--> 7 Read tool calls in fixed order
  |
  | Step 3: reads primary result file
  | Step 4: enrichment gate — BOTH must be true:
  |   (a) asset has >1 section (transcript: prepared_remarks, qa → YES)
  |   (b) enrichment-pass.md file exists for this type (guidance → YES)
  |
  +--> extraction-enrichment-agent (subagent)
         |
         +--> 7 Read tool calls in fixed order
```

---

## 2. Naming Convention For Blocks

```text
A*  = ambient / runtime layers (hidden, not repo files)
O*  = orchestrator-visible blocks (main SDK session)
P*  = primary-agent-visible blocks
E*  = enrichment-agent-visible blocks
```

Kinds:

```text
[RUNTIME]   hidden system prompt or SDK configuration
[PROMPT]    runtime prompt text / invocation args
[SHELL]     generic skeleton agent definition file
[BRIEF]     pass-specific working brief
[REF]       shared contract / asset / queries
[GUARD]     evidence / anti-hallucination rules
```

Message types (how each block enters the LLM context):

```text
[SYSTEM]       injected into system prompt — always visible to the LLM
[USER]         first user message — visible from turn 1
[TOOL_RESULT]  returned from Read tool calls — visible after the agent's first action
```

---

## 3. End-to-End Order

```text
──── AMBIENT (not repo files, not user-controllable) ────
A0  Claude Code runtime system prompt                    [SYSTEM]
A1  .claude/settings.json: permissions, hooks, env vars  [RUNTIME config, not text]

──── ORCHESTRATOR (main SDK session) ────
O0  Worker runtime prompt: /extract ...                  [USER]
O1  /extract SKILL.md body (instructions)                [loaded as skill content]
O2  transcript.md asset metadata read                    [TOOL_RESULT]
O3  spawn primary shell agent via Agent tool

──── PRIMARY AGENT (subagent, own session) ────
P1  extraction-primary-agent.md body                     [SYSTEM]   ← agent definition
P0  primary spawn args                                   [USER]     ← from Agent tool call
P2  core-contract.md                                     [TOOL_RESULT]  ← Read call #1
P3  primary-pass.md                                      [TOOL_RESULT]  ← Read call #2
P4  transcript.md                                        [TOOL_RESULT]  ← Read call #3
P5  queries-common.md                                    [TOOL_RESULT]  ← Read call #4
P6  transcript-queries.md                                [TOOL_RESULT]  ← Read call #5
P7  guidance-queries.md                                  [TOOL_RESULT]  ← Read call #6
P8  evidence-standards.md                                [TOOL_RESULT]  ← Read call #7

──── ORCHESTRATOR (resumes after primary completes) ────
O4  orchestrator reads primary result file
O5  enrichment gate: sections > 1 AND enrichment-pass.md exists → PASS
O6  spawn enrichment shell agent via Agent tool

──── ENRICHMENT AGENT (subagent, own session) ────
E1  extraction-enrichment-agent.md body                  [SYSTEM]   ← agent definition
E0  enrichment spawn args                                [USER]     ← from Agent tool call
E2  core-contract.md                                     [TOOL_RESULT]  ← Read call #1
E3  enrichment-pass.md                                   [TOOL_RESULT]  ← Read call #2
E4  transcript.md                                        [TOOL_RESULT]  ← Read call #3
E5  queries-common.md                                    [TOOL_RESULT]  ← Read call #4
E6  transcript-queries.md                                [TOOL_RESULT]  ← Read call #5
E7  guidance-queries.md                                  [TOOL_RESULT]  ← Read call #6
E8  evidence-standards.md                                [TOOL_RESULT]  ← Read call #7

──── ORCHESTRATOR (resumes after enrichment completes) ────
O7  orchestrator reads enrichment result file
O8  orchestrator combines final result → writes RESULT_PATH
```

Note: P1 appears before P0 because the agent definition is loaded as system instructions BEFORE the spawn args arrive as the first user message. Same for E1/E0.

---

## 4. Orchestrator View

### O0 `[PROMPT]` Worker runtime prompt

Path:
`scripts/extraction_worker.py` line 228

Built as:

```text
/extract {ticker} {asset} {source_id} TYPE={type_name} MODE={mode} RESULT_PATH={result_path}
```

Concrete example:

```text
/extract AAPL transcript AAPL_2025-01-30T17.00 TYPE=guidance MODE=write RESULT_PATH=/tmp/extract_result_guidance_AAPL_2025-01-30T17.00_a3f8b2c1.json
```

SDK options that shape the session:

```text
setting_sources = ["project"]       → loads .claude/settings.json, .claude/skills/*, .claude/agents/*
permission_mode = "bypassPermissions"
max_turns       = 80
max_budget_usd  = 5.0
mcp_servers     = { "neo4j-cypher": http://... }   ← only Neo4j, no perplexity/alphavantage
```

### O1 `[SHELL]` Extract orchestrator skill

Path:
`.claude/skills/extract/SKILL.md` (55 lines)

Not forked — runs in the main SDK session. The LLM follows this skill's body as its instructions.

Role:
- parse args
- inspect asset metadata (Step 1)
- spawn primary agent (Step 2)
- read primary result file
- check enrichment gate — both conditions (Step 3)
- spawn enrichment agent if gate passes
- combine outputs → write RESULT_PATH (Step 4)

### O2 `[REF]` Asset metadata probe

Path:
`.claude/skills/extract/assets/transcript.md`

The orchestrator reads this file in Step 1 to extract the `sections:` field.

Critical metadata:

```text
sections: prepared_remarks, qa
```

This feeds into the enrichment gate (O5). More than one section means secondary content exists.

### O5 Enrichment gate (two conditions)

Both must be true for enrichment to run:

```text
1. Asset sections > 1     → transcript has "prepared_remarks, qa" → YES
2. enrichment-pass.md     → .claude/skills/extract/types/guidance/enrichment-pass.md exists → YES
```

For the concrete path (guidance x transcript), both conditions pass. An asset with `sections: full` (e.g., news) would fail condition 1. A type without an enrichment pass file would fail condition 2.

### Orchestrator-visible stack

```text
A0  Claude Code runtime system prompt
  + O0  runtime /extract prompt
  + O1  .claude/skills/extract/SKILL.md body
  + O2  transcript.md metadata read
  + O4  primary result file read
  + O5  enrichment gate evaluation
  + O7  enrichment result file read
  + O8  combined result write
```

---

## 5. Primary Skeleton Agent View

### Primary visual stack

```text
             Message Type     Block
             ────────────     ─────
[SYSTEM]     agent def body → P1  extraction-primary-agent.md
[USER]       spawn args     → P0  "AAPL transcript ... TYPE=guidance MODE=write"
[TOOL_RESULT] Read call #1  → P2  core-contract.md
[TOOL_RESULT] Read call #2  → P3  primary-pass.md
[TOOL_RESULT] Read call #3  → P4  transcript.md
[TOOL_RESULT] Read call #4  → P5  queries-common.md
[TOOL_RESULT] Read call #5  → P6  transcript-queries.md
[TOOL_RESULT] Read call #6  → P7  guidance-queries.md
[TOOL_RESULT] Read call #7  → P8  evidence-standards.md
```

### P0 `[PROMPT]` Primary spawn args

Source: Agent tool call in /extract SKILL.md Step 2:

```text
Agent(subagent_type=extraction-primary-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

Concrete value:

```text
AAPL transcript AAPL_2025-01-30T17.00 TYPE=guidance MODE=write
```

Note: RESULT_PATH is NOT passed to agents. Agents write pass-specific result files to fixed paths. Only the orchestrator writes to RESULT_PATH.

### P1 `[SHELL]` Generic primary shell

Path:
`.claude/agents/extraction-primary-agent.md` (65 lines total)

This file has two parts:

```text
Lines 1-14:   YAML frontmatter (parsed by Claude Code runtime, NOT visible to the LLM)
Lines 15-65:  Markdown body (injected as SYSTEM instructions, visible to the LLM)
```

**Frontmatter** (14 lines — configures the agent, LLM never sees this text):

```yaml
name: extraction-primary-agent
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
  - Write
  - Read
model: opus
permissionMode: dontAsk
```

**Body** (51 lines — the LLM sees this as its system instructions):
- "Extraction — Primary Pass Agent"
- "ALWAYS use ultrathink"
- 3 GUARDRAILS: no direct Neo4j writes, use deterministic scripts, follow primary-pass.md
- Input parsing: `$ARGUMENTS` → TICKER, ASSET, SOURCE_ID, TYPE, MODE
- Step 0: READ 7 FILES (the instruction that drives the 7 Read calls below)
- Execution summary: FETCH → EXTRACT → VALIDATE → WRITE
- Result file contract: `/tmp/extract_pass_{TYPE}_primary_{SOURCE_ID}.json`

### P2 `[REF]` Shared type contract

Path:
`.claude/skills/extract/types/guidance/core-contract.md` (736 lines)

This is the largest single loaded block. It defines:
- graph schema (Guidance, GuidanceUpdate nodes)
- 20 extraction fields
- deterministic ID computation
- normalization rules (unit, basis, segment)
- quality filters
- write path (writer script + JSON envelope)
- error taxonomy (SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_GUIDANCE, etc.)

Role: reference document. The pass brief (P3) says "follow me start to finish, consult core-contract for schema details."

### P3 `[BRIEF]` Primary working brief

Path:
`.claude/skills/extract/types/guidance/primary-pass.md` (241 lines)

This is the active execution brief for the primary run:
- fetch context (company, FYE, inventory)
- fetch source content (prepared remarks only for transcripts)
- extract forward-looking guidance items from primary section
- validate via deterministic scripts
- write batch payload via type-specific writer script

This file drives the agent's behavior. core-contract.md (P2) is the reference; this is the playbook.

### P4 `[REF]` Transcript asset profile

Path:
`.claude/skills/extract/assets/transcript.md` (245 lines)

It supplies:
- transcript data structure (PreparedRemark, QAExchange, QuestionAnswer nodes)
- transcript metadata fields (id, conference_datetime, fiscal_quarter, fiscal_year)
- scan scope rules
- speaker hierarchy with extraction priority
- prepared remarks processing steps
- Q&A processing steps
- empty-content fallback chain (3B → 3C → 3D)
- period identification and calendar → fiscal mapping
- basis/segment quality filter notes

Important current reality: this file contains 31 guidance-specific references (e.g., "Guidance Priority", "derivation=explicit", "forward-looking statements"). The asset profile is supposed to be asset-specific (how to read transcripts) but currently blends in guidance extraction rules. This means a future non-guidance type would inherit guidance bias from this shared asset layer. Acceptable now (only one type exists) but needs refactoring when type #2 is added.

### P5 `[REF]` Shared query file

Path:
`.claude/skills/extract/queries-common.md` (319 lines)

It supplies:
- company context lookup (1A/1B)
- FYE lookup
- concept cache (2A/2B)
- member cache
- inventory queries
- fulltext recall helpers

Shared across all types and all assets.

### P6 `[REF]` Transcript queries

Path:
`.claude/skills/extract/assets/transcript-queries.md` (104 lines)

It supplies:
- structured transcript fetch (3B — prepared remarks + Q&A exchanges)
- Q&A Section fallback (3C — for ~40 legacy transcripts)
- full transcript text fallback (3D — for ~28 transcripts with FullTranscriptText)
- Q&A-only re-scan query

### P7 `[REF]` Guidance queries

Path:
`.claude/skills/extract/types/guidance/guidance-queries.md` (129 lines)

It supplies:
- existing guidance item tags (for dedup/readback)
- source-level readback (what was already extracted from this source)
- completeness baseline (for enrichment comparison)
- guidance keyword hints

### P8 `[GUARD]` Evidence rules

Path:
`.claude/skills/extract/evidence-standards.md` (12 lines)

Note: this file has YAML skill frontmatter (lines 1-5: name, description, user-invocable). When loaded via Read tool, the agent sees all 12 lines including the frontmatter as plain text. The frontmatter is only parsed by the runtime when invoked as a skill — here it's Read as a reference file, so the YAML is harmless text.

It supplies 4 rules:
- no evidence = no item
- keep items with unclear fields, use unknown/null instead of guessing
- keep quotes exact; scripts own normalization and IDs
- no guesses

### Primary-visible combined stack

```text
PRIMARY agent sees, in message order:

  [SYSTEM]       P1  generic primary shell body            51 lines
  [USER]         P0  spawn args                            1 line
  [TOOL_RESULT]  P2  core-contract.md                      736 lines
  [TOOL_RESULT]  P3  primary-pass.md                       241 lines
  [TOOL_RESULT]  P4  transcript.md                         245 lines
  [TOOL_RESULT]  P5  queries-common.md                     319 lines
  [TOOL_RESULT]  P6  transcript-queries.md                 104 lines
  [TOOL_RESULT]  P7  guidance-queries.md                   129 lines
  [TOOL_RESULT]  P8  evidence-standards.md                 12 lines
                                                        ──────────
                     Total LLM-visible repo text         1,838 lines
```

After loading all 7 files, the agent proceeds to execute the pipeline from P3 (primary-pass.md).

---

## 6. Enrichment Skeleton Agent View

### Enrichment visual stack

```text
             Message Type     Block
             ────────────     ─────
[SYSTEM]     agent def body → E1  extraction-enrichment-agent.md
[USER]       spawn args     → E0  "AAPL transcript ... TYPE=guidance MODE=write"
[TOOL_RESULT] Read call #1  → E2  core-contract.md
[TOOL_RESULT] Read call #2  → E3  enrichment-pass.md
[TOOL_RESULT] Read call #3  → E4  transcript.md
[TOOL_RESULT] Read call #4  → E5  queries-common.md
[TOOL_RESULT] Read call #5  → E6  transcript-queries.md
[TOOL_RESULT] Read call #6  → E7  guidance-queries.md
[TOOL_RESULT] Read call #7  → E8  evidence-standards.md
```

### E0 `[PROMPT]` Enrichment spawn args

Source: Agent tool call in /extract SKILL.md Step 3:

```text
Agent(subagent_type=extraction-enrichment-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

Concrete value:

```text
AAPL transcript AAPL_2025-01-30T17.00 TYPE=guidance MODE=write
```

Identical format to P0. Neither agent receives RESULT_PATH.

### E1 `[SHELL]` Generic enrichment shell

Path:
`.claude/agents/extraction-enrichment-agent.md` (68 lines total)

```text
Lines 1-14:   YAML frontmatter (parsed by runtime, NOT visible to LLM)
Lines 15-68:  Markdown body (injected as SYSTEM instructions, visible to LLM)
```

**Frontmatter** (14 lines — identical tool list to primary):

```yaml
name: extraction-enrichment-agent
tools:                                        # same 7 tools as primary
  - mcp__neo4j-cypher__read_neo4j_cypher
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
  - Write
  - Read
model: opus
permissionMode: dontAsk
```

**Body** (54 lines — 3 lines more than primary):
- "Extraction — Enrichment Pass Agent"
- "ALWAYS use ultrathink"
- 4 GUARDRAILS (primary has 3 — extra: "ONLY write changed or new items")
- Same input parsing
- Step 0: READ 7 FILES (enrichment-pass.md instead of primary-pass.md)
- Execution: FETCH → LOAD secondary → EXTRACT with verdicting → COMPLETENESS CHECK → VALIDATE → WRITE
- Result file: `/tmp/extract_pass_{TYPE}_enrichment_{SOURCE_ID}.json`

### E3 `[BRIEF]` Enrichment working brief

Path:
`.claude/skills/extract/types/guidance/enrichment-pass.md` (175 lines)

This is the active execution brief for the enrichment run:
- read back primary-pass items from Neo4j
- load Q&A / secondary content
- verdict each exchange as ENRICHES / NEW ITEM / NO GUIDANCE
- run completeness check against prior baseline
- write only changed/new items via writer script

### Shared blocks

These are the same files as the primary shell also sees:

```text
E2 = same as P2  core-contract.md           736 lines
E4 = same as P4  transcript.md              245 lines
E5 = same as P5  queries-common.md          319 lines
E6 = same as P6  transcript-queries.md      104 lines
E7 = same as P7  guidance-queries.md        129 lines
E8 = same as P8  evidence-standards.md       12 lines
```

### Enrichment-visible combined stack

```text
ENRICHMENT agent sees, in message order:

  [SYSTEM]       E1  generic enrichment shell body         54 lines
  [USER]         E0  spawn args                            1 line
  [TOOL_RESULT]  E2  core-contract.md                      736 lines
  [TOOL_RESULT]  E3  enrichment-pass.md                    175 lines
  [TOOL_RESULT]  E4  transcript.md                         245 lines
  [TOOL_RESULT]  E5  queries-common.md                     319 lines
  [TOOL_RESULT]  E6  transcript-queries.md                 104 lines
  [TOOL_RESULT]  E7  guidance-queries.md                   129 lines
  [TOOL_RESULT]  E8  evidence-standards.md                 12 lines
                                                        ──────────
                     Total LLM-visible repo text         1,775 lines
```

After loading all 7 files, the agent proceeds to execute the pipeline from E3 (enrichment-pass.md).

---

## 7. Primary vs Enrichment: Exact Difference

```text
Same (6 blocks, byte-identical):
  core-contract.md              736 lines
  transcript.md                 245 lines
  queries-common.md             319 lines
  transcript-queries.md         104 lines
  guidance-queries.md           129 lines
  evidence-standards.md          12 lines
                              ──────────
  Shared total               1,545 lines

Different (2 blocks):
  extraction-primary-agent.md body     51 lines    vs  extraction-enrichment-agent.md body   54 lines
  primary-pass.md                     241 lines    vs  enrichment-pass.md                   175 lines
```

Practical meaning:

```text
Primary shell:
  "Extract from the primary section" (prepared remarks for transcripts)
  3 guardrails

Enrichment shell:
  "Read back primary items, analyze Q&A, enrich / add only deltas"
  4 guardrails (extra: only write changed or new items)
```

---

## 8. Line Counts: What Each Agent Actually Sees

### Full file sizes vs LLM-visible text

The agent shell files have YAML frontmatter (14 lines each) that is parsed by the Claude Code runtime for configuration (tools, model, permissionMode). The LLM never sees frontmatter as text — only the body after the closing `---` becomes system instructions.

The 7 Read files are loaded via the Read tool. The LLM sees their entire content including any YAML-looking text (e.g., evidence-standards.md has skill frontmatter, but it's read as plain text, not parsed).

### Primary agent

```text
Block                        Total file    LLM-visible    Message type
─────                        ──────────    ───────────    ────────────
P1  Shell body                   65            51         [SYSTEM]  (14 lines frontmatter parsed, not shown)
P2  Core contract               736           736         [TOOL_RESULT]
P3  Primary pass                241           241         [TOOL_RESULT]
P4  Transcript profile          245           245         [TOOL_RESULT]
P5  Common queries              319           319         [TOOL_RESULT]
P6  Transcript queries          104           104         [TOOL_RESULT]
P7  Guidance queries            129           129         [TOOL_RESULT]
P8  Evidence standards           12            12         [TOOL_RESULT]
                             ──────        ──────
                              1,851         1,837         + spawn args + runtime system prompt
```

### Enrichment agent

```text
Block                        Total file    LLM-visible    Message type
─────                        ──────────    ───────────    ────────────
E1  Shell body                   68            54         [SYSTEM]  (14 lines frontmatter parsed, not shown)
E2  Core contract               736           736         [TOOL_RESULT]
E3  Enrichment pass             175           175         [TOOL_RESULT]
E4  Transcript profile          245           245         [TOOL_RESULT]
E5  Common queries              319           319         [TOOL_RESULT]
E6  Transcript queries          104           104         [TOOL_RESULT]
E7  Guidance queries            129           129         [TOOL_RESULT]
E8  Evidence standards           12            12         [TOOL_RESULT]
                             ──────        ──────
                              1,788         1,774         + spawn args + runtime system prompt
```

### Dominance

```text
Core contract alone is 42% of visible text (736 / 1,774).
The shell agents are small (51/54 lines = 3% of total).
Shared reference files dominate what the agents actually see.
```

---

## 9. Proven Boundaries

### Included in this map

- worker-built runtime prompt (exact format, SDK options)
- `/extract` skill body and orchestrator logic
- both shell agent files (frontmatter vs body distinction)
- exact 7-file read order per agent shell Step 0
- current transcript/guidance file resolution
- enrichment gate conditions (both)

### Not expanded here

- hidden Claude Code runtime system prompt (tool instructions, general coding guidelines, git instructions — ~2000+ tokens, not user-controllable)
- hidden SDK/framework prompt text
- startup metadata for unrelated skills (descriptions of 60+ skills loaded for recognition in the orchestrator session)

### Proven absent in current repo state

```text
CLAUDE.md                            → no project-level CLAUDE.md exists
memory: field on agents              → neither agent has memory: in frontmatter
skills: field on agents              → neither agent has skills: auto-load
includeGitInstructions: false        → neither agent has this (git instructions still included)
SubagentStart hook                   → no hook injecting extra context into these agents
disallowedTools on agents            → neither agent explicitly blocks any tools
```

### Active but non-textual: hooks

Current `.claude/settings.json` hooks that fire for these agents:

```text
PreToolUse "Write"                         → validate_gx_output.sh
                                           → validate_judge_output.sh
PreToolUse "Edit|Write"                    → block_env_edits.sh
PreToolUse "mcp__neo4j-cypher__write..."   → guard_neo4j_delete.sh
PostToolUse "Write"                        → cleanup_after_ok.sh
```

Hooks do NOT inject text into the agents' prompts. They are behavioral modifiers: they fire when the agent uses a matching tool, can validate the tool input/output, and can block the call with an error message that forces the agent to retry. The agents experience hook blocks as tool-call failures with a reason string.

### Orchestrator session vs agent sessions

```text
Orchestrator (main SDK session):
  - HAS auto-memory loaded (~/.claude/projects/.../memory/MEMORY.md)
  - HAS all 60+ skill descriptions loaded for recognition
  - HAS all project settings/hooks active
  - Only neo4j-cypher MCP server configured (worker SDK option)

Agent subagents:
  - NO auto-memory (would need memory: field in frontmatter)
  - NO skill descriptions (Skill tool not in their tools list)
  - DO inherit project hooks from settings.json (see above)
  - DO have neo4j-cypher MCP available (from their tools list)
```

---

## 10. Source Trace

Main files used to build and verify this map:

```text
scripts/extraction_worker.py                                    ← prompt format, SDK options
.claude/skills/extract/SKILL.md                                 ← orchestrator logic
.claude/agents/extraction-primary-agent.md                      ← primary shell (frontmatter + body)
.claude/agents/extraction-enrichment-agent.md                   ← enrichment shell (frontmatter + body)
.claude/skills/extract/types/guidance/core-contract.md          ← type contract (736 lines)
.claude/skills/extract/types/guidance/primary-pass.md           ← primary working brief
.claude/skills/extract/types/guidance/enrichment-pass.md        ← enrichment working brief
.claude/skills/extract/assets/transcript.md                     ← asset profile
.claude/skills/extract/queries-common.md                        ← shared queries
.claude/skills/extract/assets/transcript-queries.md             ← asset-specific queries
.claude/skills/extract/types/guidance/guidance-queries.md       ← type-specific queries
.claude/skills/extract/evidence-standards.md                    ← evidence guardrails
.claude/settings.json                                           ← hooks, permissions, env vars
```

---

## 11. Final Answer In One Screen

```text
What the PRIMARY skeleton agent sees (1,837 lines of repo text):

  [SYSTEM]       generic primary shell body            51 lines
  [USER]         spawn args                            ~1 line
  [TOOL_RESULT]  guidance core contract                736 lines
  [TOOL_RESULT]  guidance primary pass (★ working brief)  241 lines
  [TOOL_RESULT]  transcript asset profile              245 lines
  [TOOL_RESULT]  common query pack                     319 lines
  [TOOL_RESULT]  transcript query pack                 104 lines
  [TOOL_RESULT]  guidance query pack                   129 lines
  [TOOL_RESULT]  evidence guardrails                   12 lines


What the ENRICHMENT skeleton agent sees (1,774 lines of repo text):

  [SYSTEM]       generic enrichment shell body         54 lines
  [USER]         spawn args                            ~1 line
  [TOOL_RESULT]  guidance core contract                736 lines
  [TOOL_RESULT]  guidance enrichment pass (★ working brief)  175 lines
  [TOOL_RESULT]  transcript asset profile              245 lines
  [TOOL_RESULT]  common query pack                     319 lines
  [TOOL_RESULT]  transcript query pack                 104 lines
  [TOOL_RESULT]  guidance query pack                   129 lines
  [TOOL_RESULT]  evidence guardrails                   12 lines


Only 2 blocks differ: shell body (51 vs 54 lines) and pass brief (241 vs 175 lines).
The other 6 blocks (1,545 lines) are byte-identical.
```

---
---

# PART B: After Transcript Guidance Pollution Fix

Plan: `.claude/plans/extraction-pipeline/transcript-guidancePollutionFix.md`

The pollution fix moves 77 lines of guidance-specific extraction rules OUT of `transcript.md` (generic asset profile) and INTO the two pass files where they belong. No new files. No agent infrastructure changes. Same 7-file read order.

---

## 12. What Changes (4 files touched, 5 unchanged)

### Files that CHANGE

```text
File                         Before    After    Delta    What happens
────                         ──────    ─────    ─────    ────────────
transcript.md                  245      168      −77     Guidance rules removed, 4 minor text rewrites
primary-pass.md                241      279      +38     PR extraction rules moved in (from transcript.md)
enrichment-pass.md             175      229      +54     Q&A extraction rules moved in (from transcript.md)
transcript-queries.md          104      104        0     1 line rewrite (stale ref fix), same length
```

### Files that DO NOT change

```text
extraction-primary-agent.md       65 (51 body)    UNCHANGED — same shell, same frontmatter
extraction-enrichment-agent.md    68 (54 body)    UNCHANGED — same shell, same frontmatter
core-contract.md                 736              UNCHANGED
queries-common.md                319              UNCHANGED
guidance-queries.md              129              UNCHANGED
evidence-standards.md             12              UNCHANGED
```

---

## 13. Content Flow: What Moves Where

```text
┌─────────────────────────────────────────────────────────────────────┐
│  transcript.md (BEFORE: 245 lines, MIXED generic + guidance)       │
│                                                                     │
│  STAYS (168 lines — pure generic):                                 │
│    Lines 1-42    Data structure, metadata, fields                  │
│    Lines 63-67   PR data format (how content string arrives)       │
│    Lines 97-104  Q&A data format (array structure, field names)    │
│    Lines 150-245 Duplicate resolution, fallbacks, period mapping,  │
│                  calendar→fiscal, basis traps, given_date,         │
│                  source_key                                        │
│                                                                     │
│  REMOVED (77 lines — guidance-specific):                           │
│    ┌─────────────────────────────────────────────────────────┐     │
│    │ Lines 44-59:  Scan scope + Speaker hierarchy (15 lines) │     │
│    │               ──→ BOTH pass files (intentional dup)     │     │
│    ├─────────────────────────────────────────────────────────┤     │
│    │ Lines 69-93:  PR extraction steps + signal table +      │     │
│    │               [PR] quote prefix (25 lines)              │     │
│    │               ──→ primary-pass.md ONLY                  │     │
│    ├─────────────────────────────────────────────────────────┤     │
│    │ Lines 106-148: Why Q&A Matters + Q&A extraction steps + │     │
│    │               signal table + [Q&A] quote prefix +       │     │
│    │               section field format (43 lines)           │     │
│    │               ──→ enrichment-pass.md ONLY               │     │
│    └─────────────────────────────────────────────────────────┘     │
│                                                                     │
│  4 REWRITES (generic wording):                                     │
│    Line 3:   "extraction rules" → "profile"                       │
│    Line 196: "guidance statement" → "extracted item"               │
│    Line 226: "See core-contract.md S6/S7/S13" →                   │
│              "See your type's core-contract for..."                │
│    Line 238: "guidance became public" → "content became public"    │
└─────────────────────────────────────────────────────────────────────┘

                    │                              │
         ┌──────────┘                              └──────────┐
         ▼                                                     ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│  primary-pass.md                │   │  enrichment-pass.md             │
│  BEFORE: 241 lines              │   │  BEFORE: 175 lines              │
│  AFTER:  279 lines (+38)        │   │  AFTER:  229 lines (+54)        │
│                                 │   │                                 │
│  INSERT after line 94           │   │  INSERT after line 57           │
│  (after Quality Filters,       │   │  (after verdict taxonomy,       │
│   before Numeric Value Rules)   │   │   before COMPLETENESS CHECK)    │
│                                 │   │                                 │
│  NEW SECTION:                   │   │  NEW SECTION:                   │
│  "Per-Asset: Transcript         │   │  "Per-Asset: Transcript         │
│   Extraction Rules"             │   │   Extraction Rules"             │
│                                 │   │                                 │
│  Contains:                      │   │  Contains:                      │
│  + Scan scope (REWRITTEN        │   │  + Scan scope (REWRITTEN        │
│    for PR: "Process all         │   │    for Q&A: "Process all        │
│    prepared remarks content")   │   │    Q&A content")                │
│  + Speaker hierarchy table      │   │  + Speaker hierarchy table      │
│    (all 6 rows + footer)        │   │    (all 6 rows + footer)        │
│  + PR extraction steps 1-5     │   │  + Why Q&A Matters (7 reasons)  │
│  + "What to Extract from PR"   │   │  + Q&A extraction steps 1-4    │
│    signal table (7 rows)        │   │  + "What to Extract from Q&A"  │
│  + [PR] quote prefix rule       │   │    signal table (8 rows)        │
│                                 │   │  + [Q&A] quote prefix rule      │
│                                 │   │  + Section field format          │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

### 15 lines intentionally duplicated in BOTH pass files

```text
Scan scope heading + rewritten scope text       3 lines  (different wording per pass)
Speaker Hierarchy table + header + footer       12 lines (verbatim identical)
                                              ────────
                                               15 lines in each pass file
```

Both agents need the speaker hierarchy for their respective sections (primary uses CFO/CEO PR rows, enrichment uses CFO/CEO/Other Q&A rows). Keeping the full table in both prevents either agent from losing priority context.

---

## 14. Before vs After: Primary Agent Side-by-Side

```text
BEFORE (1,837 LLM-visible lines)               AFTER (1,798 LLM-visible lines)
════════════════════════════════                ════════════════════════════════

[SYSTEM] P1 primary shell body   51            [SYSTEM] P1 primary shell body   51
                                                         (UNCHANGED)

[USER]   P0 spawn args           ~1            [USER]   P0 spawn args           ~1
                                                         (UNCHANGED)

[TOOL_RESULT] P2 core-contract  736            [TOOL_RESULT] P2 core-contract  736
                                                         (UNCHANGED)

[TOOL_RESULT] P3 primary-pass   241            [TOOL_RESULT] P3 primary-pass   279  ← +38 lines
              │                                              │
              │ (extraction rules                            │ SAME extraction rules
              │  for all assets)                             │ for all assets
              │                                              │
              │                                              ├─ NEW: "Per-Asset: Transcript
              │                                              │   Extraction Rules"
              │                                              │   + Scan scope (PR-specific)
              │                                              │   + Speaker hierarchy table
              │                                              │   + PR extraction steps 1-5
              │                                              │   + "What to Extract" table
              │                                              │   + [PR] quote prefix
              │                                              │
              └─ Numeric Value Rules...                      └─ Numeric Value Rules...

[TOOL_RESULT] P4 transcript.md  245            [TOOL_RESULT] P4 transcript.md  168  ← −77 lines
              │                                              │
              ├─ Data structure (1-42)                       ├─ Data structure (1-42)
              ├─ Scan scope + speaker hier (44-59) ◄─GONE   │   (UNCHANGED)
              ├─ PR data format (63-67)                      ├─ PR data format (63-67)
              ├─ PR extraction rules (69-93) ◄──────GONE     │   (UNCHANGED)
              ├─ Q&A data format (97-104)                    ├─ Q&A data format (97-104)
              ├─ Q&A extraction rules (106-148) ◄───GONE     │   (UNCHANGED)
              ├─ Duplicate resolution (150-156)              ├─ Duplicate resolution
              ├─ Empty content handling (157-191)            ├─ Empty content handling
              ├─ Period identification (192-221)             ├─ Period identification
              └─ Basis/given_date/source_key (222-245)       └─ Basis/given_date/source_key
                                                              + 4 minor text rewrites

[TOOL_RESULT] P5 queries-common 319            [TOOL_RESULT] P5 queries-common 319
                                                         (UNCHANGED)

[TOOL_RESULT] P6 transcript-q   104            [TOOL_RESULT] P6 transcript-q   104
                                                         (1 line rewrite, same length)

[TOOL_RESULT] P7 guidance-q     129            [TOOL_RESULT] P7 guidance-q     129
                                                         (UNCHANGED)

[TOOL_RESULT] P8 evidence-std    12            [TOOL_RESULT] P8 evidence-std    12
                                                         (UNCHANGED)
                               ─────                                           ─────
                               1,837                                           1,798
                                                                         (−39 lines net)
```

### What the primary agent GAINS

```text
Nothing new — all 38 lines already existed in transcript.md (slot 3).
They now appear in primary-pass.md (slot 2), ~670 lines earlier in context.
Same content, different position.
```

### What the primary agent LOSES

```text
43 lines of Q&A extraction rules (lines 106-148 from transcript.md):
  - "Why Q&A Matters" rationale
  - Q&A extraction steps
  - "What to Extract from Q&A" signal table
  - [Q&A] quote prefix rule
  - Section field format

These were ALWAYS IGNORED — primary-pass.md line 37 says:
"Extract from Prepared Remarks only. Full Q&A analysis is handled by the enrichment pass."
Removing irrelevant Q&A noise is a net positive for context clarity.
```

---

## 15. Before vs After: Enrichment Agent Side-by-Side

```text
BEFORE (1,774 LLM-visible lines)               AFTER (1,751 LLM-visible lines)
════════════════════════════════                ════════════════════════════════

[SYSTEM] E1 enrichment shell     54            [SYSTEM] E1 enrichment shell     54
                                                         (UNCHANGED)

[USER]   E0 spawn args           ~1            [USER]   E0 spawn args           ~1
                                                         (UNCHANGED)

[TOOL_RESULT] E2 core-contract  736            [TOOL_RESULT] E2 core-contract  736
                                                         (UNCHANGED)

[TOOL_RESULT] E3 enrichment-p   175            [TOOL_RESULT] E3 enrichment-p   229  ← +54 lines
              │                                              │
              │ Verdict taxonomy                             │ Verdict taxonomy
              │ (ENRICHES/NEW/NO_GUIDANCE)                   │ (ENRICHES/NEW/NO_GUIDANCE)
              │                                              │
              │                                              ├─ NEW: "Per-Asset: Transcript
              │                                              │   Extraction Rules"
              │                                              │   + Scan scope (Q&A-specific)
              │                                              │   + Speaker hierarchy table
              │                                              │   + Why Q&A Matters (7 reasons)
              │                                              │   + Q&A extraction steps 1-4
              │                                              │   + "What to Extract" table
              │                                              │   + [Q&A] quote prefix
              │                                              │   + Section field format
              │                                              │
              └─ COMPLETENESS CHECK...                       └─ COMPLETENESS CHECK...

[TOOL_RESULT] E4 transcript.md  245            [TOOL_RESULT] E4 transcript.md  168  ← −77 lines
              │                                              │
              ├─ Data structure (1-42)                       ├─ Data structure (1-42)
              ├─ Scan scope + speaker hier (44-59) ◄─GONE   │   (UNCHANGED)
              ├─ PR data format (63-67)                      ├─ PR data format (63-67)
              ├─ PR extraction rules (69-93) ◄──────GONE     │   (UNCHANGED)
              ├─ Q&A data format (97-104)                    ├─ Q&A data format (97-104)
              ├─ Q&A extraction rules (106-148) ◄───GONE     │   (UNCHANGED)
              ├─ Duplicate resolution (150-156)              ├─ Duplicate resolution
              ├─ Empty content handling (157-191)            ├─ Empty content handling
              ├─ Period identification (192-221)             ├─ Period identification
              └─ Basis/given_date/source_key (222-245)       └─ Basis/given_date/source_key
                                                              + 4 minor text rewrites

[TOOL_RESULT] E5-E8 (same as before)           [TOOL_RESULT] E5-E8 (same as before)
  queries-common     319                         queries-common     319
  transcript-q       104                         transcript-q       104
  guidance-q         129                         guidance-q         129
  evidence-std        12                         evidence-std        12
                   ─────                                           ─────
                   1,774                                           1,751
                                                             (−23 lines net)
```

### What the enrichment agent GAINS

```text
Nothing new — all 54 lines already existed in transcript.md (slot 3).
They now appear in enrichment-pass.md (slot 2), ~670 lines earlier in context.
Same content, different position.
```

### What the enrichment agent LOSES

```text
25 lines of PR extraction rules (lines 69-93 from transcript.md):
  - PR extraction steps 1-5
  - "What to Extract from Prepared Remarks" signal table
  - [PR] quote prefix rule

These were irrelevant — the enrichment agent processes Q&A, not PR.
It has its own [PR]...[Q&A] format rules in enrichment-pass.md lines 122-123.
```

---

## 16. Summary: Before vs After in One Screen

```text
PRIMARY AGENT — BEFORE (1,837 lines)         PRIMARY AGENT — AFTER (1,798 lines)
────────────────────────────────────         ───────────────────────────────────

  [SYS]  shell body                 51         [SYS]  shell body                51
  [USER] spawn args                 ~1         [USER] spawn args                ~1
  [TR]   core-contract             736         [TR]   core-contract            736
  [TR]   primary-pass              241         [TR]   primary-pass         ▲   279  (+38: PR rules from transcript.md)
  [TR]   transcript.md             245         [TR]   transcript.md        ▼   168  (−77: all guidance rules removed)
  [TR]   queries-common            319         [TR]   queries-common           319
  [TR]   transcript-queries        104         [TR]   transcript-queries        104
  [TR]   guidance-queries          129         [TR]   guidance-queries          129
  [TR]   evidence-standards         12         [TR]   evidence-standards         12
                                 ─────                                        ─────
                                 1,837                                        1,798  (−39 net)


ENRICHMENT AGENT — BEFORE (1,774 lines)      ENRICHMENT AGENT — AFTER (1,751 lines)
────────────────────────────────────────      ────────────────────────────────────────

  [SYS]  shell body                 54         [SYS]  shell body                54
  [USER] spawn args                 ~1         [USER] spawn args                ~1
  [TR]   core-contract             736         [TR]   core-contract            736
  [TR]   enrichment-pass           175         [TR]   enrichment-pass      ▲   229  (+54: Q&A rules from transcript.md)
  [TR]   transcript.md             245         [TR]   transcript.md        ▼   168  (−77: all guidance rules removed)
  [TR]   queries-common            319         [TR]   queries-common           319
  [TR]   transcript-queries        104         [TR]   transcript-queries        104
  [TR]   guidance-queries          129         [TR]   guidance-queries          129
  [TR]   evidence-standards         12         [TR]   evidence-standards         12
                                 ─────                                        ─────
                                 1,774                                        1,751  (−23 net)


WHAT CHANGED:
  ▲ Pass files GREW — absorbed guidance rules from transcript.md
  ▼ transcript.md SHRANK — became pure generic asset profile
  All other files: UNCHANGED

WHAT EACH AGENT LOST (intentional context reduction):
  Primary:    −43 lines of Q&A rules it never used (its brief says "PR only")
  Enrichment: −25 lines of PR rules it never used (its scope is Q&A)

WHAT EACH AGENT GAINED:
  Nothing new. Same content, earlier position (slot 2 instead of slot 3).

INFRASTRUCTURE UNCHANGED:
  Agent shells:       same files, same frontmatter, same body
  Read order:         same 7 files, same sequence
  Orchestrator:       same /extract SKILL.md
  Worker:             same extraction_worker.py
  Hooks:              same settings.json
```

---

## 17. Documented Deviations from Exact Equivalence

Two known deviations, both assessed as low-risk:

```text
1. LOAD ORDER SHIFT
   Content that was at slot 3 (transcript.md, position ~1000 in full context)
   now appears at slot 2 (pass file, position ~330).
   ~670 lines earlier in the context window.
   Impact: Low — agent reads all 7 files before starting execution.

2. CONTEXT REDUCTION
   Each agent loses the OTHER pass's extraction rules:
     Primary loses 43 lines of Q&A rules  → was always ignored (brief says "PR only")
     Enrichment loses 25 lines of PR rules → was always irrelevant (scope is Q&A)
   Impact: Low — both agents have explicit scope directives.

3. 15 LINES INTENTIONALLY DUPLICATED
   Scan scope (3 lines, different wording) + speaker hierarchy (12 lines, verbatim)
   appear in BOTH pass files.
   Reason: Both agents need speaker priority for their respective sections.
```

### Edge case: Primary Q&A fallback

primary-pass.md line 37 allows using Q&A as a fallback if PR is truncated/empty. After the fix, the primary agent would apply its own PR extraction rules to Q&A content without seeing the Q&A-specific signal table. Q&A data FORMAT info (field names, structure) stays in transcript.md. Risk: low — the fallback uses Q&A as a substitute data source, not a Q&A-specific analysis pass. If regression detected, add the Q&A signal table to primary-pass.md too.

---

## 18. Verification: Hard Gates

**Gate 1 — Prompt-stream diff**: Concatenate all 7 files each agent reads, before and after. Diff must show ONLY:

```text
7 planned text changes:
  1. transcript.md line 3:   "extraction rules" → "profile"
  2. transcript.md line 196: "guidance statement" → "extracted item"
  3. transcript.md line 226: "See core-contract.md S6/S7/S13" → "See your type's core-contract..."
  4. transcript.md line 238: "guidance became public" → "content became public"
  5. transcript-queries.md line 48: stale PROFILE_TRANSCRIPT.md ref → "transcript.md"
  6. primary-pass.md: new scan scope "Process all prepared remarks content..."
  7. enrichment-pass.md: new scan scope "Process all Q&A content..."

Plus: position shifts (content at different file offsets) and context reduction (removed blocks).
Any OTHER diff = accidental change → investigate before proceeding.
```

**Gate 2 — Dry-run regression**: Run extraction on known transcripts before AND after, compare full JSON output (item count, labels, quotes, sections, period fields, guidance_ids).
