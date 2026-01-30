# Earnings Architecture Plan

## Date: 2026-01-22 (Reorganized)

---

# Part 1: Quick Reference

## 1.1 Quick Summary for Next Bot

**What this is**: Multi-layer earnings analysis system using forked skills for context isolation.

**Key findings from testing (2026-01-16):**

| What | Status | Workaround |
|------|--------|------------|
| Skill tool in fork | ✅ WORKS | Use for all layer chaining |
| Task tool in fork | ❌ BLOCKED | Use Skill tool instead |
| AskUserQuestion in fork | ❌ BLOCKED | Non-interactive; use file-based communication |
| Thinking capture | ✅ PRIMARY + SUBAGENTS | In both primary transcript AND agent files (if Opus used) |
| Agent file agentIds | ⚠️ MISMATCH | Transcript IDs ≠ file IDs; match by sessionId |
| K8s/SDK execution | ✅ WORKS | Opus works; thinking captured from all layers |
| CLI v2.1.1 agent files | ⚠️ ROOT LEVEL | Older versions write to root, not session/subagents/ |
| K8s Opus thinking | ✅ 171 blocks | 159KB thinking (was 6.7KB with Sonnet) |
| Sub-agent model inheritance | ❌ NOT ENFORCED | `model:` in frontmatter ignored; inherits parent's model |
| `allowed-tools` for restriction | ❌ NOT ENFORCED | Other tools still accessible |
| `allowed-tools` for MCP pre-load | ✅ **WORKS** | List MCP tools to pre-load them |
| `disallowedTools` | ❌ NOT ENFORCED | Cannot block tools |
| `agent:` field | ❌ NOT WORKING | Doesn't inherit agent's tools |
| MCP in fork | ✅ WORKS | Either use allowed-tools OR MCPSearch |
| Tool inheritance parent→child | ❌ NO | Each skill has independent access |
| 3+ layer chains | ✅ WORKS | L1→L2→L3 all executed correctly |
| Sibling isolation | ✅ WORKS | Context isolated, filesystem shared |
| Return values | ✅ WORKS | Parent sees child's full output |
| **Workflow continuation (GH #17351)** | ✅ WORKS (v2.1.17) | Parent continues after child returns; tested single & multi-child |
| `$ARGUMENTS` substitution | ✅ WORKS | Pass args to skills dynamically |
| **TaskCreate/List/Get/Update in Interactive CLI** | ✅ WORKS | No extra config needed |
| **TaskCreate/List/Get/Update via SDK 0.1.23+** | ✅ **WORKS** | Requires `tools` preset + env var (See Part 10) |
| **SDK `claude_code` tools preset** | ✅ **INCLUDES TASK TOOLS** | SDK 0.1.23+ fixed the bug |
| **Task cross-visibility** | ✅ SHARED | All contexts see same task list |
| **Task dependencies** | ✅ WORKS | Chain, multiple blockers, wave patterns |
| **CLAUDE_CODE_TASK_LIST_ID** | ✅ **WORKS** | Enables cross-session persistence (See Part 10.3) |
| **Cross-session task persistence** | ✅ **WORKS** | Via settings.json or env var (See Part 10.3) |
| Parallel execution (Task tool) | ✅ PARALLEL | From main conversation only |
| Parallel execution (Skill tool) | ❌ SEQUENTIAL | Always sequential |
| Task tool in forked context | ❌ BLOCKED | Cannot use for parallelism |
| MCP wildcards pre-load | ❌ NO | Only grants permission, still need MCPSearch |
| Error propagation | ⚠️ TEXT ONLY | No exceptions, must parse response |
| **Task deletion unblocks dependents** | ✅ WORKS | `status: "deleted"` removes task, unblocks dependents |
| **Task completion unblocks dependents** | ✅ WORKS | `status: "completed"` keeps task, unblocks dependents |
| **Cross-agent task manipulation** | ✅ WORKS | Any agent can update/delete any task by ID |
| **Upfront task creation pattern** | ✅ WORKS | Create all tasks upfront, skip via completed/deleted |
| **Parallel foreground Task spawn** | ✅ PARALLEL | 194ms spread, full tool access (See Part 10.14) |
| Skill-specific hooks | ✅ WORKS (v2.1.0+) | Define in SKILL.md frontmatter; 3 events only |
| `color:` for sub-agents | ✅ UI only | Offered in `/agents` wizard; not documented as frontmatter field |
| `color:` for skills | ❓ UNTESTED | Not documented; test if `context: fork` skills can use it |

**Color Support (Researched 2026-01-22):**
- **Sub-agents**: Color offered in `/agents` interactive UI for visual identification, but NOT documented as a frontmatter field
- **Skills**: No color support documented
- **TODO**: Test if adding `color:` to a skill with `context: fork` works (since forked skills spawn sub-agents internally)

**WHY these limitations exist (Verified 2026-01-16):**

| Limitation | Verified Reason |
|------------|-----------------|
| **Task tool blocked in forks** | Tool simply not provided to forked skill contexts. 14 tools available, Task excluded. Prevents recursive subagent spawning and resource exhaustion. |
| **allowed-tools NOT enforced** | Skills use **prompt injection**, not execution isolation. Skill content is appended to conversation context. No tool-call interceptor checks allowed-tools before execution. (Tested: Write/Bash/Grep all worked despite `allowed-tools: [Read]`) |
| **Skill tool SEQUENTIAL** | Claude processes tool calls one at a time: execute → receive result → process → next tool. Task tool differs because it spawns independent subprocesses. (Tested: 92.68 second gap between parallel skill calls) |
| **Claude CLI can't spawn OpenAI/Gemini** | Task tool has NO `provider` parameter. Only accepts 17 predefined Claude-based `subagent_type` values. `model` parameter only accepts sonnet/opus/haiku. |
| **SDK needs `permission_mode: "bypassPermissions"`** | Same as CLI `--dangerously-skip-permissions`. In automated mode, no user to approve prompts → Claude refuses → operation fails. (Tested: Without bypass, Claude says "I need permission" and file NOT created) |
| **MAX_THINKING_TOKENS = 31999** | Claude's default max output is 32000 tokens. Thinking budget must be < max_tokens. 31999 leaves room for at least 1 output token. |

## 1.2 Quick Code Examples

**How to use MCP tools in forked skills (BEST METHOD):**
```yaml
# In SKILL.md frontmatter, list MCP tools in allowed-tools:
---
name: my-skill
allowed-tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
  - Write
context: fork
---
# MCP tool is now pre-loaded and directly available!
```
Alternative: Use MCPSearch in instructions (works but less elegant).

**Skill-specific hooks (v2.1.0+):**
```yaml
---
name: my-skill
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/lint.sh"
  Stop:
    - hooks:
      - type: command
        command: "./scripts/final-check.sh"
---
```
Only 3 hook events in skills (vs 12+ global). Known bug: #17688 - skill hooks don't trigger in plugins.

## 1.3 File Locations

| What | Location |
|------|----------|
| Test skills | `.claude/skills/test-*/SKILL.md` |
| Test outputs | `earnings-analysis/test-outputs/` |
| Transcripts | `~/.claude/projects/-home-faisal-EventMarketDB/{sessionId}/subagents/` |

**What's left to implement**: See "Next Steps" in Part 7.

---

# Part 2: Architecture Overview

## 2.1 Final Architecture

```
Layer 0: Main Conversation
      │
      └─→ Layer 1: /earnings-orchestrator (context: fork)
              │   agent: earnings-automation
              │   model: opus
              │   allowed-tools: Skill, Read, Write, Bash, TodoWrite
              │   Thinking: ✅ agent-{orch}.jsonl
              │
              ├─→ Layer 2: /earnings-prediction (context: fork)
              │       │   agent: earnings-automation
              │       │   model: opus
              │       │   allowed-tools: Skill, Read, Write
              │       │   Thinking: ✅ agent-{pred}.jsonl
              │       │   Uses: filtered-data (ENABLED)
              │       │
              │       └─→ Layer 2.5: /filtered-data (context: fork)
              │               │   agent: filtered-automation
              │               │   model: opus (upgraded from sonnet)
              │               │   allowed-tools: Skill, Bash, Read
              │               │   Thinking: ✅ agent-{filter}.jsonl
              │               │
              │               └─→ Layer 3: /neo4j-report (NO fork)
              │                       Runs inside filtered's context
              │                       allowed-tools: mcp__neo4j-cypher__read_neo4j_cypher
              │                       Prediction context stays clean ✅
              │
              └─→ Layer 2: /earnings-attribution (context: fork)
                      │   agent: earnings-automation
                      │   model: opus
                      │   allowed-tools: Skill, Read, Write
                      │   Thinking: ✅ agent-{attr}.jsonl
                      │   Uses: filtered-data (DISABLED) - calls neo4j directly
                      │
                      └─→ Layer 3: /neo4j-news (context: fork) ← FORKED!
                              agent: neo4j-reader
                              model: sonnet (cost savings)
                              allowed-tools: mcp__neo4j-cypher__read_neo4j_cypher
                              Thinking: ✅ agent-{neo4j}.jsonl
                              Attribution context stays clean ✅
```

## 2.2 Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Skill tool vs Task tool | **Skill tool** | Task tool blocked in forked contexts |
| Layer 3 fork (via filtered) | **No fork** | filtered-data already isolates |
| Layer 3 fork (direct call) | **Fork** | Prevent context pollution |
| Permission handling | **Agent with permissionMode** | Different MCP access per layer |
| Model for Layers 1-2.5 | **Opus** | Maximum thinking |
| Model for Layer 3 | **Sonnet** | Cost savings for query execution |

## 2.3 Why Context Separation Matters

### The Core Problem
We're building an earnings prediction system that must make predictions BEFORE seeing actual results, then attribute WHY stocks moved AFTER seeing results. If prediction and attribution share context, the prediction could be "contaminated" by future knowledge.

### Context Isolation Requirements

| Layer | Must NOT See | Why |
|-------|--------------|-----|
| Prediction | Actual returns, post-earnings news | Would invalidate the prediction (future leakage) |
| Attribution | Prediction's reasoning | Should analyze independently, then compare |
| Orchestrator | Children's intermediate thinking | Only needs final outputs to coordinate |

### Why Forked Skills?

1. **Thinking Capture**: Each forked skill gets its own transcript with thinking blocks. We need this for audit trail and analysis improvement.

2. **Context Purity**: Forked skills start fresh - they don't inherit parent's conversation history or file reads. Prediction won't accidentally see attribution's data.

3. **File-Based Communication**: Parent only sees child's return value. Detailed results are written to files, which parent reads explicitly. This is intentional - forces clear data boundaries.

4. **Sibling Isolation**: Prediction and Attribution run in separate forks. They cannot see each other's context. But they CAN see each other's files (for orchestrator to coordinate).

### The PIT (Point-In-Time) Principle

**Prediction** operates at T=0 (moment of earnings release):
- Can see: 8-K filing, historical financials, past news
- Cannot see: Stock return after filing, analyst reactions, next-day news

**Attribution** operates at T+1 (after market reaction):
- Can see: Everything prediction saw PLUS actual return, post-earnings news, analyst commentary
- Uses this to explain WHY the stock moved

## 2.4 File-Based Communication & Data Flow

Since parent only sees child's return value:

| File | Written By | Read By |
|------|------------|---------|
| `predictions.csv` | earnings-prediction | earnings-orchestrator |
| `Companies/{TICKER}/{accession}.md` | earnings-attribution | earnings-orchestrator |
| `orchestrator-runs/{run-id}.md` | earnings-orchestrator | Main conversation |

**Data Flow Diagram:**
```
Orchestrator
    │
    ├── calls Prediction (fork)
    │       └── writes to: predictions.csv, Companies/{ticker}/{accession}.md
    │
    └── calls Attribution (fork)
            └── writes to: Companies/{ticker}/{accession}.md (appends attribution)

Orchestrator reads files after each child completes.
```

---

# Part 3: Skill System Deep Dive

## 3.1 Why Skill Tool (Not Task Tool)

| Aspect | Task Tool | Skill Tool |
|--------|-----------|------------|
| Creates subagent | ✅ Yes | Only if `context: fork` |
| Works in forked context | ❌ **No** | ✅ **Yes** |
| Uses `.claude/agents/` | ✅ Yes | ❌ No (uses skills) |
| Uses `.claude/skills/` | ❌ No | ✅ Yes |

**Rule**: Subagents can't spawn subagents. Since our skills have `context: fork` (making them subagents), they can't use Task tool. They must use Skill tool.

**Verified (2026-01-16)**: Forked skills have exactly 14 tools available: Bash, Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, TodoWrite, WebSearch, Skill, MCPSearch, ListMcpResourcesTool, ReadMcpResourceTool. Task tool is NOT in this list.

## 3.2 Context Sharing

### What's Inherited

| Context Item | Inherited? | Notes |
|--------------|------------|-------|
| Conversation history | ❌ No | Each fork starts fresh |
| CLAUDE.md | ⚠️ Partial | Embed needed instructions in SKILL.md |
| Parent's SKILL.md | ❌ No | Child only sees its own |
| Sibling's context | ❌ No | Full isolation |
| Settings (MAX_THINKING_TOKENS) | ✅ Yes | Propagates to all layers |
| MCP servers | ✅ Yes | But restricted by allowed-tools |
| Filesystem | ✅ Yes | Shared for file-based communication |

### Parent-Child Visibility

| Direction | What's Visible |
|-----------|----------------|
| Parent → Child | Only the prompt/request sent |
| Child → Parent | Only the final return value |
| File-based | Children write files, parent reads them |

### Context Sharing Details (TESTED 2026-01-16)

**Child receives from parent:**
- [x] Arguments passed via Skill tool — Yes, visible as "$ARGUMENTS" in skill
- [x] CLAUDE.md content — Yes, injected via system-reminder
- [x] Working directory — Yes, /home/faisal/EventMarketDB
- [x] Git status snapshot — Yes, branch and recent commits
- [x] Parent's conversation history — **NO, isolated**
- [x] Files parent read — **NO, isolated**

**Parent receives from child:**
- [x] Child's full return value — Yes, all text child outputs is returned
- [x] Child's tool calls/intermediate steps — **NO, only final output**

**Sibling isolation:**
- [x] Sibling skills don't share context — test-sibling-a/b: Context isolated (no shared memory)
- [x] Siblings CAN see each other's files — Filesystem is shared, sibling B saw sibling A's file

**Environment propagation:**
- [x] MAX_THINKING_TOKENS propagates — Thinking works at all layers (Claude-specific, 31999 tokens)
- Note: OpenAI uses `reasoning.effort`, Gemini uses prompt-based. Each provider has own control.

## 3.3 Tool Inheritance (Parent ↔ Child)

**Key Finding: Each skill's tool access is INDEPENDENT. No inheritance.**

| Scenario | Result | Evidence |
|----------|--------|----------|
| Parent has MCP, child doesn't | Child must use MCPSearch | test-inherit-parent2 → test-inherit-child2 |
| Parent doesn't have MCP, child has it | Child can use directly | test-inherit-parent → test-inherit-child |
| MCP pre-loaded from parent? | **NO** | Child cannot directly call parent's MCP |

**Inheritance Model Summary:**
```
Parent (allowed-tools: [MCP_A])
    │
    └── Child (allowed-tools: [MCP_B])
            │
            ├── MCP_A: NOT pre-loaded (must use MCPSearch)
            └── MCP_B: Pre-loaded (directly available)
```

**Practical Implication:**
- List MCP tools in EACH skill's `allowed-tools:` that needs them
- Don't rely on parent's tools being available to children
- MCPSearch always available as fallback (but adds extra step)

## 3.4 `allowed-tools` Behavior

**Important**: `allowed-tools` has two different behaviors:

| Purpose | Works? | How |
|---------|--------|-----|
| **Restrict tools** | ❌ NOT ENFORCED | Other tools still accessible (tested: Write/Bash/Grep worked despite `allowed-tools: [Read]`) |
| **Pre-load MCP tools** | ✅ WORKS | List MCP tools to make them directly available without MCPSearch |

**Why restriction doesn't work**: Skills use prompt injection, not execution isolation. Skill content is appended to conversation context with no tool-call interceptor.

**Practical implication**: Use `allowed-tools` to pre-load MCP tools. For tool restriction, rely on skill instructions to guide behavior (not enforceable).

**Pattern from agentic-finance-review**: They use `allowed-tools` as documentation/convention even though enforcement relies on prompt guidance:
```yaml
# csv-edit-agent - most restricted (by convention)
allowed-tools: [Glob, Grep, Read, Edit, Write]

# graph-agent - most permissive
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Skill]
```

**SOLUTION for MCP in forked skills**: List MCP tools in `allowed-tools:` frontmatter. They'll be pre-loaded and directly available without MCPSearch.

**Note on tool restrictions**: Cannot restrict tools in forked skills. All tools remain accessible regardless of allowed-tools/disallowedTools. This is a limitation - rely on skill instructions to guide behavior, not tool restrictions.

## 3.5 MCP Tool Access Per Layer

| Layer | MCP Tools Available |
|-------|---------------------|
| 1 (Orchestrator) | None directly (delegates to children) |
| 2 (Prediction) | Via filtered-data or direct Skill calls |
| 2 (Attribution) | Direct: neo4j-cypher, perplexity |
| 2.5 (Filtered) | Via neo4j skills |
| 3 (Neo4j) | `mcp__neo4j-cypher__read_neo4j_cypher` only |

**Key**: Each layer gets ONLY its own `allowed-tools` list (no inheritance from parent).

### MCP Access Validation
- [x] MCP tools accessible via MCPSearch in fork — test-mcp-in-fork: MCPSearch worked, loaded neo4j-cypher
- [x] MCP tools work after MCPSearch loads them — Query executed, returned APPLE INC

### MCP Wildcards
- [x] `mcp__neo4j-cypher__*` pre-loads all matching tools? — **NO**
- Wildcards grant PERMISSION but do NOT pre-load
- Must use exact tool name (e.g., `mcp__neo4j-cypher__read_neo4j_cypher`) to pre-load
- MCPSearch still required as fallback

## 3.6 Skill-Specific Hooks (v2.1.0+)

Hooks can now be defined in SKILL.md frontmatter, scoped only to that skill's execution.

### Skill vs Global Hooks

| Feature | Global Hooks | Skill-Specific Hooks |
|---------|--------------|----------------------|
| **Definition** | `.claude/settings.json` | SKILL.md frontmatter |
| **Scope** | Entire session | Only during skill execution |
| **Events** | 12+ available | **3 only**: PreToolUse, PostToolUse, Stop |
| **Lifecycle** | Persistent | Auto-cleanup when skill ends |
| **Unique** | SessionStart, Setup, UserPromptSubmit | `once: true` option |

### Skill Hook Syntax

```yaml
---
name: validated-operations
description: Operations with validation hooks
context: fork
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/validate-output.sh"
  Stop:
    - hooks:
      - type: command
        command: "./scripts/final-validation.sh"
---
```

### Matcher Syntax
- `Bash` - Exact match
- `Write|Edit` - Multiple tools (OR)
- `.*Task.*` - Regex patterns
- `*` - Match all tools

### Hook Input/Output Protocol

**Hook receives (via stdin):**
```json
{
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": {"file_path": "/path/to/file.csv"}
}
```

**Hook returns (via stdout):**
```json
{}                                           // Allow - continue execution
{"decision": "block", "reason": "error msg"} // Block - agent retries with error context
```

### Known Limitation
**GitHub #17688**: Skill-scoped hooks don't trigger within plugins. Workaround: Use global hooks or call scripts directly from skill instructions.

---

# Part 4: Multi-Provider Support (OpenAI/Gemini)

## 4.1 Agent CLI (`./agent`)

The `./agent` script supports swapping providers at any layer:

```bash
./agent -p "prompt" --provider {claude|openai|gemini} [--model MODEL] [--skills SKILL] [--reasoning {low|medium|high|x-high}]
```

### Using with Skills

```bash
# Run earnings-attribution with Gemini
./agent -p "Analyze AAPL earnings" --provider gemini --skills earnings-attribution --reasoning high

# Run with OpenAI
./agent -p "Analyze AAPL earnings" --provider openai --model gpt-5.2 --skills earnings-attribution --reasoning medium
```

## 4.2 Reasoning/Thinking Support by Provider

| Provider | Thinking Method | Budget Control | Tested |
|----------|----------------|----------------|--------|
| Claude | Native SDK (`thinking.budget_tokens`) | low/medium/high/x-high | ✅ Works |
| OpenAI GPT-5.x | Native Responses API (`reasoning.effort`) | low/medium/high | ✅ Works (see note below) |
| Gemini | Structured prompt (`<reasoning>` tags) | Prompt-based | ✅ Works |

**OpenAI Reasoning Note (2026-01-16)**:
- Reasoning **works** regardless of org verification (model thinks internally)
- Warning `Org not verified for reasoning summaries` is **informational only**
- To export reasoning summaries: verify org at https://platform.openai.com/settings/organization/general
- Code handles gracefully: retries without summary if org not verified

## 4.3 Sub-Agent Spawning

| Primary | Can Spawn | Notes |
|---------|-----------|-------|
| OpenAI | Claude, OpenAI, Gemini | ✅ All work |
| Gemini | Claude, OpenAI, Gemini | ✅ All work |
| Claude (CLI) | Claude only | ❌ Cannot spawn OpenAI/Gemini (CLI has own Task tool) |

**Workaround for Claude as primary**: Use Anthropic SDK directly instead of Claude Code CLI.

**Claude Subagent Fix (2026-01-16)**: Added `--dangerously-skip-permissions` flag to Claude CLI calls in `./agent`.

**Why it's needed**: When Claude CLI runs as a subprocess (non-interactive), it cannot prompt the user for permission. Without the flag, Claude politely refuses: `"I need permission to write to X. Please grant write access."` — the file is NOT created and the operation fails silently. With the flag, Claude executes immediately.

**Verified behavior**:
```bash
# Without flag - refuses, file not created
echo "Write TEST to /tmp/test.txt" | claude -p --print
# Output: "I need permission to write..."

# With flag - executes, file created
echo "Write TEST to /tmp/test.txt" | claude -p --print --dangerously-skip-permissions
# Output: "Done. Written TEST to /tmp/test.txt"
```

**When used**: Only in `./agent` lines 303, 328 — when spawning Claude as subprocess from OpenAI/Gemini parent.

**Security note**: Per Claude CLI docs, "Recommended only for sandboxes with no internet access." Our use case is controlled (local multi-provider orchestration).

## 4.4 Tool Availability by Provider

| Tool | Claude (CLI) | Claude (SDK) | OpenAI | Gemini |
|------|-------------|--------------|--------|--------|
| Bash | ✅ | ❌ | ❌ | ❌ |
| Read/Write files | ✅ | ✅ | ✅ | ✅ |
| Glob/search_files | ✅ | ✅ | ✅ | ✅ |
| list_directory | ✅ | ✅ | ✅ | ✅ |
| Skill tool | ✅ | ❌ | ❌ | ❌ |
| MCP tools (via HTTP) | ✅ | ✅ | ✅ | ✅ |
| subagent tool | ❌ | ✅ | ✅ | ✅ |
| Thinking/Reasoning | ✅ | ✅ | ✅ | ✅ (prompt-based) |

**File tools added to `./agent`** (2026-01-16):
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Write content to file
- `list_directory(path)` - List directory contents
- `search_files(pattern, path)` - Glob search for files

### Where Each Provider Can Be Used

| Layer | Claude CLI | Claude SDK | OpenAI | Gemini | Notes |
|-------|-----------|------------|--------|--------|-------|
| Layer 1 (Orchestrator) | ✅ | ✅ | ✅ | ✅ | All have file ops now |
| Layer 2 (Prediction) | ✅ | ✅ | ✅ | ✅ | All have write_file |
| Layer 2 (Attribution) | ✅ | ✅ | ✅ | ✅ | All have write_file |
| Layer 3 (Neo4j queries) | ✅ | ✅ | ✅ | ✅ | All have MCP tools |

**All providers now fully supported for all layers via `./agent`.**

Only limitation: Claude CLI has Bash, others don't. But Bash not needed for earnings analysis.

## 4.5 100% Swappability Status

| Capability | Claude CLI | OpenAI | Gemini | Notes |
|------------|-----------|--------|--------|-------|
| File read/write | ✅ | ✅ | ✅ | via read_file, write_file |
| File search | ✅ | ✅ | ✅ | via search_files |
| MCP tools | ✅ | ✅ | ✅ | via HTTP endpoint |
| Subagent spawning | ✅ | ✅ | ✅ | via subagent tool |
| Skills | ✅ | ✅ | ✅ | via --skills flag |
| Reasoning capture | ✅ | ✅ | ✅ | via --reasoning-file |
| Bash | ✅ | ❌ | ❌ | Not needed for earnings |

**Conclusion: Any layer can use any provider (Claude/OpenAI/Gemini) via `./agent`.**

Transcripts saved to: `earnings-analysis/transcripts/subagent-{id}.txt`

## 4.6 MCP Bash/Shell Servers

If bash execution needed for OpenAI/Gemini, these MCP servers available:

| Server | GitHub | Features |
|--------|--------|----------|
| mcp-bash | [patrickomatik/mcp-bash](https://github.com/patrickomatik/mcp-bash) | Simple, direct bash execution |
| mcp-shell | [sonirico/mcp-shell](https://github.com/sonirico/mcp-shell) | Secure with allowlist/blocklist, audit trails |
| mcp-shell-server | [tumf/mcp-shell-server](https://github.com/tumf/mcp-shell-server) | Whitelisted commands, stdin support |
| mcp-shell-server | [mako10k/mcp-shell-server](https://github.com/mako10k/mcp-shell-server) | Sandbox, path control, multi-shell |

**Recommendation**: For earnings analysis, bash not needed. File tools cover all requirements.
If bash needed later, `sonirico/mcp-shell` is most secure (allowlist/blocklist + audit).

## 4.7 Thorough Testing (2026-01-16)

| Tool | OpenAI | Gemini | Evidence |
|------|--------|--------|----------|
| read_file | ✅ PASS | ✅ PASS | Read ./agent first 200 chars |
| write_file | ✅ PASS | ✅ PASS | *-filetools-test.txt, *-reasoning-test.txt |
| list_directory | ✅ PASS | ✅ PASS | Listed 32 files in test-outputs |
| search_files | ✅ PASS | ✅ PASS | Found 10+ .txt matches |
| subagent (same provider) | ✅ PASS | ✅ PASS | openai-subagent-test.txt, gemini-subagent-test.txt |
| subagent (cross-provider) | ✅ PASS | ✅ PASS | Gemini→OpenAI cascade worked |
| reasoning capture | ✅ PASS | ✅ PASS | Thinking blocks captured |

**Test Files Created:**
- `earnings-analysis/test-outputs/openai-reasoning-test.txt`
- `earnings-analysis/test-outputs/gemini-reasoning-test.txt`
- `earnings-analysis/test-outputs/openai-subagent-test.txt` (wrote "OPENAI-SUBAGENT-TEST")
- `earnings-analysis/test-outputs/gemini-subagent-test.txt` (wrote "GEMINI-SUBAGENT-TEST")
- `earnings-analysis/test-outputs/layer2-test.txt` (multi-layer cascade)

---

# Part 5: Thinking & Transcripts

## 5.1 Thinking Token Capture by Layer

| Layer | Transcript Location | Thinking Captured? |
|-------|--------------------|--------------------|
| 0 (Main) | `{sessionId}.jsonl` | ✅ Yes |
| 1 (Orchestrator) | `subagents/agent-{orch}.jsonl` | ✅ Yes |
| 2 (Prediction) | `subagents/agent-{pred}.jsonl` | ✅ Yes |
| 2 (Attribution) | `subagents/agent-{attr}.jsonl` | ✅ Yes |
| 2.5 (Filtered) | `subagents/agent-{filter}.jsonl` | ✅ Yes |
| 3 (Neo4j via filtered) | In filtered's transcript | ✅ Yes |
| 3 (Neo4j direct) | `subagents/agent-{neo4j}.jsonl` | ✅ Yes |

### Where Thinking is Stored (VALIDATED 2026-01-16)

| File Type | Contains Thinking? | Purpose |
|-----------|-------------------|---------|
| Primary transcript (`{sessionId}.jsonl`) | ✅ YES | Main conversation + primary thinking |
| Agent files (`agent-*.jsonl`) | ✅ YES (if Opus) | Sub-agent thinking (model dependent) |

### Model Inheritance for Sub-Agents (VERIFIED 2026-01-16)

| Skill | Model Setting | Actual Model | Thinking? |
|-------|--------------|--------------|-----------|
| All skills | Any `model:` value | **Inherits from parent** | Depends on parent model |

**Note**: The `model:` field in skill frontmatter does NOT work. All forked skills inherit the parent's model. This was empirically tested with `test-model-field` skill (model: haiku ran as Opus).

**Workaround to control model per layer**:
- Use `./agent --model sonnet` for cost savings at specific layers
- Or use Claude Agent SDK with explicit model parameter

## 5.2 Settings Configured

| Setting | Location | Value | Why |
|---------|----------|-------|-----|
| `ENABLE_TOOL_SEARCH` | `~/.claude/settings.json` | `"true"` | Enables MCPSearch tool for discovering MCP tools |
| `MAX_THINKING_TOKENS` | `~/.claude/settings.json` | `"31999"` | Max is 32000; thinking budget must be < max_tokens, so 31999 leaves room for output |
| `alwaysThinkingEnabled` | `~/.claude/settings.json` | `true` | Always use extended thinking for better reasoning |
| `plansDirectory` | `.claude/settings.json` | `".claude/plans"` | Store plan files in project directory |

## 5.3 Transcript Locations

- Session: `~/.claude/projects/-home-faisal-EventMarketDB/a9555be6-cc6c-4050-9c44-f1c6ca43ada2/`
- Subagents: `subagents/agent-{id}.jsonl`
- Layer 1 transcript: `agent-ade676b.jsonl` (orchestrator)
- Layer 2 transcript: `agent-a86e06a.jsonl` (child)

---

# Part 6: Architecture Patterns Worth Adopting

Based on research from [agentic-finance-review](https://github.com/disler/agentic-finance-review).

## 6.1 PostToolUse Validators (Immediate Feedback)

Run validation immediately after tool execution. If invalid, hook returns block → agent auto-corrects → retries.

```yaml
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/csv-validator.py"
```

**Use for**: Data format validation, schema checks, immediate error detection.

## 6.2 Stop Hooks (Final Quality Gate)

Run before skill/agent completes. Ensures output quality before returning to parent.

```yaml
hooks:
  Stop:
    - hooks:
      - type: command
        command: "./scripts/validate-prediction-output.sh"
```

**Use for**: Final validation, balance checks, required fields verification.

## 6.3 Validator Logging Pattern

**Critical for debugging hook failures.** All validators should log to co-located files.

```python
#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import json
import sys

LOG_FILE = Path(__file__).parent / "validator-name.log"

def log(message: str):
    """Append timestamped message to log file."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def main():
    # Read hook input
    stdin_data = sys.stdin.read()
    hook_input = json.loads(stdin_data) if stdin_data else {}

    log("=" * 50)
    log(f"VALIDATOR TRIGGERED")
    log(f"Hook input keys: {list(hook_input.keys())}")

    errors = []

    # Perform validation...
    if some_check_failed:
        log(f"✗ Check failed: {reason}")
        errors.append(reason)
    else:
        log(f"✓ Check passed")

    # Return decision
    if errors:
        log(f"RESULT: BLOCK ({len(errors)} errors)")
        print(json.dumps({"decision": "block", "reason": "\n".join(errors)}))
    else:
        log(f"RESULT: PASS")
        print(json.dumps({}))

if __name__ == "__main__":
    main()
```

**Log file location**: `.claude/hooks/validators/{validator-name}.log`

**What to log**:
- Trigger markers with separators (`"=" * 50`)
- Hook input keys and context
- Per-check results with visual markers (`✓`/`✗`)
- Final decision (PASS/BLOCK with error count)

## 6.4 Block/Retry Pattern

When hook returns `{"decision": "block", "reason": "..."}`:
1. Claude receives the error message
2. Claude auto-corrects based on the reason
3. Claude retries the operation
4. Hook validates again
5. Cycle repeats until validation passes

**This enables autonomous error correction without human intervention.**

## 6.5 Separation of Concerns

| Output | Destination | Purpose |
|--------|-------------|---------|
| Logs | `*.log` files | Human-readable audit trail |
| Decision | stdout (JSON) | Claude Code hook system |
| Errors | stderr + exit 2 | Blocking errors for retry |

---

# Part 7: Implementation Plan

## 7.1 Agent Definitions to Create

### 1. earnings-automation
```yaml
# .claude/agents/earnings-automation.md
---
name: earnings-automation
description: "Automation agent for earnings analysis tasks. No permission prompts."
permissionMode: dontAsk
tools:
  - Skill
  - Read
  - Write
  - Bash
  - TodoWrite
  - WebFetch
  - WebSearch
---
Automation agent for earnings orchestration, prediction, and attribution tasks.
Handles multi-step analysis without user prompts.
```

### 2. filtered-automation
```yaml
# .claude/agents/filtered-automation.md
---
name: filtered-automation
description: "Automation agent for filtered-data skill. Validates and passes through data."
permissionMode: dontAsk
tools:
  - Skill
  - Bash
  - Read
---
Passthrough filter agent that calls data sub-agents, validates responses, and returns clean data.
```

### 3. neo4j-reader
```yaml
# .claude/agents/neo4j-reader.md
---
name: neo4j-reader
description: "Read-only Neo4j query agent. Only has Cypher read access."
permissionMode: dontAsk
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
---
Neo4j read-only agent for executing Cypher queries.
No write access to database.
```

### 4. perplexity-reader
```yaml
# .claude/agents/perplexity-reader.md
---
name: perplexity-reader
description: "Perplexity search agent for web research."
permissionMode: dontAsk
tools:
  - mcp__perplexity__perplexity_ask
  - mcp__perplexity__perplexity_search
  - mcp__perplexity__perplexity_reason
  - mcp__perplexity__perplexity_research
---
Perplexity agent for web search and research tasks.
```

## 7.2 Skill Updates Required

### Layer 1: earnings-orchestrator
```yaml
---
name: earnings-orchestrator
description: Master orchestrator for batch earnings analysis
context: fork
agent: earnings-automation
model: opus
allowed-tools: Skill, Read, Write, Bash, TodoWrite
skills: earnings-prediction, earnings-attribution
---
```

### Layer 2: earnings-prediction
```yaml
---
name: earnings-prediction
description: Predict stock direction at T=0 using PIT-filtered data
context: fork
agent: earnings-automation
model: opus
allowed-tools: Skill, Read, Write
skills: filtered-data, neo4j-report, neo4j-entity, neo4j-xbrl
---
```

### Layer 2: earnings-attribution
```yaml
---
name: earnings-attribution
description: Analyze why stocks moved after earnings using post-hoc data
context: fork
agent: earnings-automation
model: opus
allowed-tools: Skill, Read, Write
skills: neo4j-report, neo4j-news, neo4j-transcript, perplexity-search
---
```

### Layer 2.5: filtered-data (UPDATE)
```yaml
---
name: filtered-data
description: Passthrough filter agent. Calls data sub-agents, validates responses.
context: fork
agent: filtered-automation
model: opus  # Upgraded from sonnet
allowed-tools: Skill, Bash, Read
skills: neo4j-report, neo4j-xbrl, neo4j-news, neo4j-entity, neo4j-transcript
---
```

### Layer 3: neo4j-report (UPDATE for direct calls)
```yaml
---
name: neo4j-report
description: Query SEC filings from Neo4j
context: fork  # Fork when called directly (not via filtered)
agent: neo4j-reader
model: sonnet
allowed-tools: mcp__neo4j-cypher__read_neo4j_cypher
---
```

### Layer 3: neo4j-news (UPDATE)
```yaml
---
name: neo4j-news
description: Query news articles from Neo4j
context: fork
agent: neo4j-reader
model: sonnet
allowed-tools: mcp__neo4j-cypher__read_neo4j_cypher
---
```

(Similar updates for neo4j-entity, neo4j-xbrl, neo4j-transcript)

## 7.3 Build Path

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1: Claude Code CLI** | 4-5 days | Build and validate architecture |
| **Phase 2: Port to SDK** | 1-2 days | Convert to production code |
| **Total** | 6-7 days | |

### Phase 1 Tasks
1. Create agent definitions (earnings-automation, neo4j-reader, etc.)
2. Update skill frontmatter (add context: fork, agent:, allowed-tools)
3. Test orchestrator → prediction → filtered → neo4j flow
4. Test orchestrator → attribution → neo4j direct flow
5. Validate thinking capture at all layers
6. Test with GBX earnings data

### Phase 2 Tasks
1. Copy SKILL.md files (100% portable)
2. Create AgentDefinition objects
3. Wire up subagents via Task tool
4. Test and deploy

## 7.4 Test Data

- **GBX**: 13 earnings 8-Ks (2023-01 to 2025-07)
- **AAPL**: 11 earnings 8-Ks (2023-02 to 2025-07)

Query:
```cypher
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE c.ticker = $ticker
  AND r.formType = '8-K'
  AND any(item IN r.items WHERE item CONTAINS 'Item 2.02')
  AND pf.daily_stock IS NOT NULL
RETURN r.accessionNo, c.ticker, r.created, pf.daily_stock
ORDER BY r.created ASC
```

## 7.5 Next Steps

1. [ ] Create agent definitions in `.claude/agents/`
2. [ ] Update earnings-orchestrator SKILL.md
3. [ ] Update earnings-prediction SKILL.md
4. [ ] Update earnings-attribution SKILL.md
5. [ ] Update filtered-data SKILL.md (model: opus)
6. [ ] Update neo4j-* skills (add context: fork, agent: neo4j-reader)
7. [ ] Test full flow with GBX
8. [ ] Validate thinking capture at all layers
9. [x] Update build-thinking-index.py to extract from subagent transcripts — Done 2026-01-16

---

# Part 8: Claude Agent SDK

## 8.1 Overview

**Purpose**: Trigger your Claude Code skills automatically from Python (event-driven automation).

**Key insight**: `setting_sources=["project"]` loads your entire `.claude/` directory unchanged.

### Files

| File | Purpose |
|------|---------|
| `scripts/test_sdk_compatibility.py` | Verify SDK works with your .claude/ directory |
| `scripts/earnings_trigger.py` | Production event listener (Redis → earnings flow) |

### Key SDK Options

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `setting_sources` | `["project"]` | Load `.claude/skills/`, `.claude/agents/`, `CLAUDE.md`, `.mcp.json` |
| `permission_mode` | `"bypassPermissions"` | No prompts (automation) |
| `model` | `"claude-opus-4-5-20250514"` | Model override (optional) |
| `max_turns` | `int` | Limit API calls (optional) |

### Development vs Production

| Phase | Tool | Why |
|-------|------|-----|
| Development | Claude Code CLI | Interactive, see output live |
| Production | Agent SDK (`scripts/earnings_trigger.py`) | Event-driven, automated |

Both use **the same `.claude/` directory**. No code changes needed.

## 8.2 Installation & Test

```bash
pip install claude-agent-sdk  # v0.1.19 tested

# Verify everything works
source venv/bin/activate
python scripts/test_sdk_compatibility.py
```

Expected output:
```
✅ Skills loaded: 61
✅ MCP servers: ['alphavantage', 'neo4j-cypher', 'perplexity']
✅ Skill invocation: PASS
✅ File writing: PASS
✅ ALL TESTS PASSED
```

### Run Event Listener

```bash
# Start the listener
source venv/bin/activate
python scripts/earnings_trigger.py

# In another terminal, trigger analysis
redis-cli -h 192.168.40.72 -p 31379 LPUSH earnings:trigger "0000320193-23-000005"
```

## 8.3 How It Works

```
Your App                          Claude Agent SDK
────────                          ────────────────
New 8-K hits Neo4j
       │
       ▼
Push to Redis ──────────────────► scripts/earnings_trigger.py
"earnings:trigger"                       │
                                         ▼
                              query("/earnings-orchestrator {accession}")
                                         │
                                         ▼
                              ┌──────────────────────────────────┐
                              │  YOUR .claude/ DIRECTORY RUNS    │
                              │                                  │
                              │  /earnings-orchestrator          │
                              │    ├── /earnings-prediction      │
                              │    │     └── /filtered-data      │
                              │    │          └── /neo4j-report  │
                              │    └── /earnings-attribution     │
                              │          └── /neo4j-news, etc.   │
                              │                                  │
                              │  Output: predictions.csv,        │
                              │          Companies/{ticker}/*.md │
                              └──────────────────────────────────┘
                                         │
                                         ▼
                              Files written ◄──────────────────── Your app reads
```

## 8.4 Authentication (No API Key Required)

**Verified 2026-01-16**: Claude Max subscription works via OAuth, no Anthropic API account needed.

**Proof from `~/.claude/.credentials.json`:**
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",
    "subscriptionType": "max",
    "rateLimitTier": "default_claude_max_20x",
    "scopes": ["user:inference", "user:profile", "user:sessions:claude_code"]
  }
}
```

**Key evidence:**
- `claudeAiOauth` - OAuth authentication, NOT API key
- `subscriptionType: "max"` - Uses Max subscription
- `refreshToken` - Self-renewing (long-lived)

**Setup for headless Linux / containers:**

```bash
# Step 1: Run once on server (gives URL to open in browser)
claude setup-token

# Step 2: Authenticate in browser on another machine

# Step 3: Token saved to ~/.claude/.credentials.json
```

**Summary:**

| Environment | Auth Method | API Key? |
|-------------|-------------|----------|
| Mac (local) | Subscription (logged in) | No |
| Headless Linux | `claude setup-token` → browser | No |
| Docker/K8s | Mount `.credentials.json` | No |

**100% confirmed: OAuth browser flow works for all environments using Max subscription.**

## 8.5 Kubernetes Deployment

### Pod Configuration (what worked)
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: earnings-prediction-final
  namespace: claude-test
spec:
  restartPolicy: Never
  nodeSelector:
    kubernetes.io/hostname: minisforum  # Where project files exist
  hostNetwork: true  # Access NodePort 30687 for Neo4j
  securityContext:
    runAsUser: 1000   # CRITICAL: Must be non-root (faisal user)
    runAsGroup: 1000
  containers:
  - name: test
    image: python:3.11-slim
    env:
    - name: HOME
      value: /home/faisal  # Use mounted credentials
    command:
    - /bin/bash
    - -c
    - |
      source /home/faisal/EventMarketDB/venv/bin/activate
      cd /home/faisal/EventMarketDB
      python3 -c "
      import asyncio
      from claude_agent_sdk import query, ClaudeAgentOptions

      async def run():
          async for msg in query(
              prompt='Run /earnings-prediction for ALKS 0000950170-25-099382...',
              options=ClaudeAgentOptions(
                  model='claude-sonnet-4-20250514',
                  setting_sources=['project'],
                  max_turns=50,
                  permission_mode='bypassPermissions',
              )
          ):
              pass
      asyncio.run(run())
      "
    volumeMounts:
    - name: home-faisal
      mountPath: /home/faisal  # Mount entire home (credentials + project)
  volumes:
  - name: home-faisal
    hostPath:
      path: /home/faisal
      type: Directory
```

### K8s Credentials Setup
```bash
# Create secret from credentials
kubectl create secret generic claude-credentials \
  --from-file=credentials.json=/home/faisal/.claude/.credentials.json \
  -n processing

# Pod spec - mount the secret
volumeMounts:
  - name: claude-creds
    mountPath: /root/.claude/.credentials.json
    subPath: credentials.json
    readOnly: true
volumes:
  - name: claude-creds
    secret:
      secretName: claude-credentials
```

### Key Requirements
1. **Must run as non-root** (runAsUser: 1000) - Claude CLI blocks `--dangerously-skip-permissions` as root
2. **Use SDK, not CLI directly** - SDK handles permission_mode properly for non-interactive use
3. **Mount entire /home/faisal** - Provides credentials, project, venv, mcp-servers all in one
4. **hostNetwork: true** - Required for localhost:30687 (Neo4j NodePort)
5. **nodeSelector: minisforum** - Where project files exist (hostPath mount)
6. **Use existing venv** - Avoids pip install issues in container
7. **max_turns: 50** - earnings-prediction skill chain needs more turns than default

### K8s Architecture: hostPath Mount (Not True Containerization)

**Key insight**: K8s pods use hostPath to access the host machine. This is NOT true containerization.

```
┌─────────────────────────────────────────────────────────────────┐
│                        minisforum (Host)                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  K8s Pod (earnings-prediction)                          │   │
│  │  - python:3.11-slim container                           │   │
│  │  - runAsUser: 1000 (faisal)                            │   │
│  │  - HOME=/home/faisal                                    │   │
│  │                                                         │   │
│  │  ┌─ hostPath Mount ─────────────────────────────────┐  │   │
│  │  │  /home/faisal ←→ /home/faisal                    │  │   │
│  │  │    ├── .claude/.credentials.json (Max OAuth)     │  │   │
│  │  │    ├── EventMarketDB/.claude/ (skills, settings) │  │   │
│  │  │    ├── EventMarketDB/venv/ (Python deps)         │  │   │
│  │  │    └── EventMarketDB/mcp_servers/ (MCP)          │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│         hostNetwork: true → localhost:30687 (Neo4j)            │
└─────────────────────────────────────────────────────────────────┘
```

**What the container accesses from host:**
| Resource | Host Path | Purpose |
|----------|-----------|---------|
| OAuth creds | `~/.claude/.credentials.json` | Max subscription auth (no API key) |
| Skills | `EventMarketDB/.claude/skills/` | Skill definitions |
| Settings | `EventMarketDB/.claude/settings.json` | MAX_THINKING_TOKENS, etc. |
| Python venv | `EventMarketDB/venv/` | Pre-installed dependencies |
| MCP servers | `EventMarketDB/mcp_servers/` | Neo4j, Perplexity, AlphaVantage |
| Output files | `EventMarketDB/earnings-analysis/` | Prediction/attribution reports |

**Why this approach:**
| Approach | Cost | Portability | Setup |
|----------|------|-------------|-------|
| **hostPath (current)** | Free (Max subscription) | Node-locked | Minimal |
| API key container | $$$ (API costs) | Portable | Need API account |
| Copy creds to image | Free but risky | Semi-portable | Security risk |

### Troubleshooting Journey (7 attempts)

| Attempt | Approach | Error | Solution |
|---------|----------|-------|----------|
| 1 | CLI as root with `--dangerously-skip-permissions` | "cannot be used with root/sudo privileges for security reasons" | Must run as non-root user |
| 2 | CLI as non-root (user 1000), install via pip --user | pip install failed - no writable home | Mount /home/faisal as HOME |
| 3 | CLI as non-root, npm global install | "claude: command not found" | PATH doesn't include npm global bin |
| 4 | CLI with fixed PATH (`/home/faisal/.npm-global/bin`) | "Reached max turns (30)" | Skills running but too complex for 30 turns |
| 5 | CLI basic test (no skills) | "I need permission to write to that file" | CLI needs interactive permission, can't use non-interactively |
| 6 | **SDK** with existing venv, user 1000 | **SUCCESS** - wrote `K8S_SDK_SUCCESS` | SDK handles `permission_mode: bypassPermissions` correctly |
| 7 | **SDK** full earnings-prediction | **SUCCESS** - 3897 byte prediction file | Use SDK, not CLI, for non-interactive K8s |

**Detailed failure analysis:**

**Attempt 1 - Root user blocked**:
```
--dangerously-skip-permissions cannot be used with root/sudo privileges for security reasons
```
Claude CLI has a security check that prevents bypassing permissions when running as root.

**Attempt 3 - PATH issue**:
```bash
npm install -g @anthropic-ai/claude-code  # Installs but not in PATH
claude --version  # "command not found"
```
Fix: Set `NPM_CONFIG_PREFIX=/home/faisal/.npm-global` and add to PATH.

**Attempt 5 - Interactive permission needed**:
```
I need permission to write to that file. Please grant write access when prompted...
```
CLI without `--dangerously-skip-permissions` asks for interactive permission.

**Why SDK works but CLI doesn't**:
- CLI requires interactive permission prompts OR `--dangerously-skip-permissions`
- `--dangerously-skip-permissions` is blocked when running as root (security)
- SDK's `permission_mode: bypassPermissions` works correctly as non-root

### Thinking Tokens Issue (discovered 2026-01-16)

The K8s test captured only 6,734 chars of thinking (vs 30,000+ expected). Two causes:

| Issue | K8s Test | Fix |
|-------|----------|-----|
| Model | `claude-sonnet-4-20250514` | Use `claude-opus-4-5-20251101` |
| Settings | `setting_sources=["project"]` | Add `"user"` to load `MAX_THINKING_TOKENS` |

**User settings** (`~/.claude/settings.json`) have the thinking config:
```json
{
  "env": {"MAX_THINKING_TOKENS": "31999"},
  "alwaysThinkingEnabled": true
}
```

**Project settings** (`.claude/settings.json`) do NOT have it.

**Fixed SDK call for full thinking**:
```python
options=ClaudeAgentOptions(
    model="claude-opus-4-5-20251101",      # Opus has more thinking
    setting_sources=["user", "project"],    # Load user settings for MAX_THINKING_TOKENS
    max_turns=50,
    permission_mode="bypassPermissions",
)
```

**Alternative**: Add to `.claude/settings.json`:
```json
{
  "plansDirectory": ".claude/plans",
  "env": {"MAX_THINKING_TOKENS": "31999"},
  "alwaysThinkingEnabled": true
}
```

### Subagent Transcripts Issue (VALIDATED 2026-01-16)

K8s session `1a2fb5f8` investigation revealed **agent files DO exist**, but with **different agentIds** than in the main transcript:

| Main Transcript (Skill Results) | Agent Files (Actual Executions) | Match? |
|---------------------------------|--------------------------------|--------|
| 23:57:19 - `a7736ec` | 23:56:45 - `af9f2b3` (filtered-data) | ❌ |
| 23:58:11 - `a07fb77` | 23:57:25 - `a129d63` (filtered-data) | ❌ |
| 00:00:34 - `acf12a7` | 23:58:21 - `aed23d6` (filtered-data) | ❌ |
| 00:01:02 - `a37aba3` | 00:00:35 - `ad0e360` (filtered-data) | ❌ |
| 00:02:05 - `a62c461` | 00:01:02 - `a376aa9` (filtered-data) | ❌ |
| 00:02:19 - `a5ff98e` | 00:02:05 - `a75aab6` (filtered-data) | ❌ |
| 00:03:34 - `a6dcebc` | 00:02:27 - `ae449c5` (filtered-data) | ❌ |
| **00:03:54 - `a030c25`** | **00:03:49 - `a030c25`** (alphavantage) | **✅** |

**K8s session agent file inventory**:
```
Total: 11 agent files for session 1a2fb5f8
- 3 Warmup files (SDK initialization)
- 8 Skill execution files (actual forked skills with thinking)
Location: ROOT level (not session/subagents/)
Reason: CLI version 2.1.1 writes to root; versions 2.1.3+ write to session/subagents/
```

**Root Cause (VALIDATED)**:

1. **Transcripts ARE being created** - All 8 skill executions have agent files
2. **AgentIds DON'T match** - Transcript reports one ID, file has different ID
3. **CLI version determines location**:
   - v2.0.76, v2.1.1: Write to ROOT level (`agent-{id}.jsonl`)
   - v2.1.3+: Write to `{sessionId}/subagents/agent-{id}.jsonl`
4. **NOT K8s-specific** - This is standard CLI/SDK behavior

**Why `build-thinking-index.py` can't find thinking**:
- Script searches for transcript agentIds (a7736ec, etc.)
- Actual files have different agentIds (af9f2b3, etc.)
- **FIX NEEDED**: Script should correlate by timestamp or sessionId, not agentId

**Comparison - CLI Versions**:
| Aspect | v2.1.1 (K8s test) | v2.1.3+ (Local) |
|--------|-------------------|-----------------|
| Main transcript | ✅ `{sessionId}.jsonl` | ✅ `{sessionId}.jsonl` |
| Session directory | ❌ Not created | ✅ `{sessionId}/` |
| Subagents folder | ❌ Not created | ✅ `{sessionId}/subagents/` |
| Agent files | ✅ ROOT level | ✅ In `subagents/` |
| Thinking captured | ✅ Yes | ✅ Yes |

**`build-thinking-index.py` bug fixes (2026-01-16)**:
1. ✅ Added ROOT-level agent file search for CLI v2.1.1
2. ✅ Added `SKILL_PATTERNS` dictionary for robust skill detection
3. ✅ Match by sessionId instead of agentId
4. ✅ Fixed bug: line 289 was resetting subagents list (discarded ROOT-level finds)
5. ✅ Added SDK/natural language prompt detection (not just slash commands)

**To add K8s sessions to history** (for thinking index):
Add entry to `/home/faisal/EventMarketDB/.claude/shared/earnings/subagent-history.csv`
or update earnings-prediction skill to write there when running from K8s.

### K8s Test Results

**Kubernetes Test (2026-01-16):**
```
=== Checking credentials mounted ===
-rw-r--r-- 1 root root  433 Jan 16 23:25 .credentials.json

=== Testing Claude auth ===
2.1.9 (Claude Code)

=== Quick inference test ===
AUTH_TEST_SUCCESS
```
**PROVEN**: OAuth credentials work in K8s pods. No API key needed.

**K8s Opus Test Results (session 7841be55)**:
- Primary thinking: 21 blocks
- Sub-agent thinking: 150+ blocks
- **Total**: 171 blocks, ~159KB
- Model: `claude-opus-4-5-20251101`
- CLI: v2.1.1 (agent files at ROOT level)

**Previous K8s Sonnet Test**: 15 blocks, 6,734 chars (no sub-agent thinking)

**Full Earnings Prediction Test:**
```
=== SUCCESS ===
File: earnings-analysis/Companies/ALKS/0000950170-25-099382.md
Size: 3897 bytes

# K8S_EARNINGS_PREDICTION_TEST
## Filing Information
- **Ticker**: ALKS (Alkermes plc)
- **Accession**: 0000950170-25-099382
...
## Prediction
| Field | Value |
|-------|-------|
| **Direction** | UP |
| **Magnitude** | MEDIUM (2-5%) |
| **Confidence** | HIGH |
```

**What this proves**:
1. ✅ OAuth Max subscription works in K8s containers
2. ✅ Claude Agent SDK invokes Claude Code correctly
3. ✅ Skills loaded from .claude/ directory
4. ✅ MCP tools connect to Neo4j via NodePort
5. ✅ Full earnings-prediction skill chain executes
6. ✅ Output files written to project directory
7. ✅ No API key required - uses subscription OAuth

**Cleanup command**:
```bash
kubectl delete namespace claude-test
```

**CLI version note**: v2.1.1 (K8s test) writes agent files to ROOT level; v2.1.3+ writes to `session/subagents/`.

## 8.6 OpenAI/Gemini Compatibility with SDK

**Question**: Can OpenAI/Gemini be used with Claude Agent SDK?

**Answer**: **100% COMPATIBLE** - They're subprocess-invoked, not SDK-loaded.

**Architecture:**
```
Claude Agent SDK
       │
       ▼
Claude Code (with your .claude/ directory)
       │
       ├─→ Skill → Bash → ./agent --provider openai → OpenAI API
       │                  ./agent --provider gemini → Gemini API
       │
       └─→ Skill → parallel_subagents → ThreadPoolExecutor → Multiple providers
```

**Why this works:**
1. SDK runs Claude Code, which loads `.claude/` directory
2. Skills can invoke `./agent` via Bash tool
3. `./agent` is a Python subprocess with its own API calls
4. Each subprocess has independent API credentials
5. No SDK involvement in OpenAI/Gemini calls

**What this means:**
| Provider | SDK-Direct? | Via ./agent? | Via parallel_subagents? |
|----------|-------------|--------------|------------------------|
| Claude | ✅ Yes | ✅ Yes | ✅ Yes |
| OpenAI | ❌ No | ✅ Yes | ✅ Yes |
| Gemini | ❌ No | ✅ Yes | ✅ Yes |

**Verified tests:**
- OpenAI via ./agent: `openai-subagent-test.txt` ✅
- Gemini via ./agent: `gemini-subagent-test.txt` ✅
- Cross-provider cascade: `layer2-test.txt` (Gemini→OpenAI) ✅
- Parallel providers: `parallel-agent-*.txt` (all 3 completed ~12s) ✅

**No architectural incompatibilities.** OpenAI/Gemini work as external subprocesses.

---

# Part 9: Test Evidence & Validation

## 9.1 Test Log

Tests are run by creating skills in `.claude/skills/test-*/SKILL.md` and invoking via `/skill-name`.
Results written to `earnings-analysis/test-outputs/`.

| Date | Test Skill | What Was Tested | Result | Output File |
|------|------------|-----------------|--------|-------------|
| 2026-01-16 | test-task-in-fork | Task tool availability in fork | BLOCKED as expected | task-in-fork-result.txt |
| 2026-01-16 | test-orchestrator-thinking | Skill tool chaining (L1→L2) | WORKS | orchestrator-*.txt, child-result.txt |
| 2026-01-16 | test-mcp-in-fork | MCP tool access via MCPSearch | WORKS | mcp-in-fork-result.txt |
| 2026-01-16 | test-restricted-tools | allowed-tools enforcement | **NOT ENFORCED** | restricted-tools-result.txt |
| 2026-01-16 | test-context-parent/child | Context sharing parent↔child | See findings below | context-*-report.txt |
| 2026-01-16 | test-agent-field | agent: field in skill frontmatter | **NOT WORKING** as expected | agent-field-result.txt |
| 2026-01-16 | test-3layer-top/mid/bottom | 3-layer nested skill chain | WORKS, thinking at all layers | 3layer-*.txt |
| 2026-01-16 | test-sibling-a/b | Sibling context isolation | Context isolated, filesystem shared | sibling-*-result.txt |
| 2026-01-16 | test-allowed-mcp | allowed-tools pre-loads MCP | **WORKS!** MCP directly available | allowed-mcp-result.txt |
| 2026-01-16 | test-disallowed-mcp | disallowedTools blocks MCP | **NOT ENFORCED** | disallowed-mcp-result.txt |
| 2026-01-16 | test-inherit-parent/child | Child has MCP, parent doesn't | Child CAN use directly | inherit-*-result.txt |
| 2026-01-16 | test-inherit-parent2/child2 | Parent has MCP, child doesn't | Child must use MCPSearch | inherit-*2-result.txt |
| 2026-01-16 | test-arguments | $ARGUMENTS substitution | **WORKS!** Args passed correctly | arguments-result.txt |
| 2026-01-16 | test-parallel-parent | Parallel skill execution | **SEQUENTIAL** not parallel | parallel-parent-result.txt |
| 2026-01-16 | test-mcp-wildcard | MCP wildcards in allowed-tools | **NO PRE-LOAD** only permission | mcp-wildcard-result.txt |
| 2026-01-16 | test-error-parent | Error propagation from child | **IN TEXT ONLY** no exceptions | error-parent-result.txt |
| 2026-01-23 | test-workflow-parent | **GH #17351**: Parent continues after child? | ✅ **WORKS** (v2.1.17) | workflow-step1/3/5.txt |
| 2026-01-23 | test-workflow-multi | Multi-child sequential workflow | ✅ **WORKS** - 2 children, 7 steps | workflow-multi-*.txt |
| 2026-01-23 | test-nested-grandparent | **GH #17351**: 3-layer nested return path | ✅ **WORKS** - L3→L2→L1 correct | nested-*.txt (6 files) |

### File Tool Tests (./agent - 2026-01-16)

| Date | Provider | Tool | Result | Evidence |
|------|----------|------|--------|----------|
| 2026-01-16 | OpenAI | read_file | ✅ PASS | Read ./agent header |
| 2026-01-16 | OpenAI | write_file | ✅ PASS | openai-reasoning-test.txt |
| 2026-01-16 | OpenAI | list_directory | ✅ PASS | Listed test-outputs/ |
| 2026-01-16 | OpenAI | search_files | ✅ PASS | Found 10+ .txt files |
| 2026-01-16 | OpenAI | subagent→OpenAI | ✅ PASS | openai-subagent-test.txt |
| 2026-01-16 | OpenAI | reasoning capture | ✅ PASS | Org warning but worked |
| 2026-01-16 | Gemini | read_file | ✅ PASS | Read agent file |
| 2026-01-16 | Gemini | write_file | ✅ PASS | gemini-reasoning-test.txt |
| 2026-01-16 | Gemini | list_directory | ✅ PASS | Listed 32 files |
| 2026-01-16 | Gemini | search_files | ✅ PASS | Found .txt files |
| 2026-01-16 | Gemini | subagent→Gemini | ✅ PASS | gemini-subagent-test.txt |
| 2026-01-16 | Gemini | subagent→OpenAI | ✅ PASS | layer2-test.txt (L2-COMPLETE) |
| 2026-01-16 | Gemini | reasoning capture | ✅ PASS | Reasoning blocks captured |

### MCP Bash Server Research (2026-01-16)

| Server | Status | Notes |
|--------|--------|-------|
| patrickomatik/mcp-bash | ✅ Found | Simple bash execution |
| sonirico/mcp-shell | ✅ Found | Secure with allowlist/blocklist |
| tumf/mcp-shell-server | ✅ Found | Whitelisted commands |
| mako10k/mcp-shell-server | ✅ Found | Sandbox, multi-shell |

**Conclusion**: MCP bash servers exist but not needed for earnings analysis.

## 9.2 Test Skills Inventory (28 skills)

Located in `.claude/skills/test-*/SKILL.md`:

**Core Mechanics:**
- test-task-in-fork — Task tool availability (BLOCKED)
- test-orchestrator-thinking — Layer 1 of 2-layer thinking test
- test-child-thinking — Layer 2 of 2-layer thinking test
- test-mcp-in-fork — MCP access via MCPSearch (WORKS)
- test-restricted-tools — allowed-tools enforcement (NOT ENFORCED)
- test-model-field — model: field in frontmatter (NOT ENFORCED)

**Context Sharing:**
- test-context-parent — Parent for context sharing test
- test-context-child — Child for context sharing test
- test-sibling-a/b — Sibling isolation test (ISOLATED)

**MCP Tools:**
- test-allowed-mcp — allowed-tools pre-loads MCP (**WORKS!**)
- test-disallowed-mcp — disallowedTools blocks MCP (NOT ENFORCED)
- test-mcp-wildcard — MCP wildcards (NO PRE-LOAD)

**Tool Inheritance:**
- test-inherit-parent/child — Child has MCP, parent doesn't (Child CAN use)
- test-inherit-parent2/child2 — Parent has MCP, child doesn't (No inheritance)
- test-agent-field — agent: field in frontmatter (NOT WORKING)

**Multi-Layer:**
- test-3layer-top/mid/bottom — 3-layer chain test (WORKS)

**Parallel Execution:**
- test-parallel-parent — Parallel skill execution (SEQUENTIAL)
- test-parallel-child-a/b — Children for parallel test

**Arguments & Errors:**
- test-arguments — $ARGUMENTS substitution (WORKS)
- test-error-parent/child — Error propagation (TEXT ONLY)

**Workflow Continuation (GH #17351):**
- test-workflow-parent — Single child, 5-step workflow (WORKS v2.1.17)
- test-workflow-child — Simple child for workflow tests
- test-workflow-multi — Multi-child sequential workflow (WORKS)
- test-nested-grandparent — Layer 1: 3-layer return path test (WORKS)
- test-nested-parent — Layer 2: middle layer with unique secret
- test-nested-child — Layer 3: innermost with unique secret

**Other:**
- test-resume — Subagent resumption

## 9.3 Test Output Files (53 files)

Located in `earnings-analysis/test-outputs/`:

**Re-verification command:**
```bash
ls -la earnings-analysis/test-outputs/*.txt
```

**Core tests:**
- task-in-fork-result.txt — Task tool blocked ✅
- orchestrator-reasoning.txt, orchestrator-summary.txt, child-result.txt — Skill chaining ✅
- mcp-in-fork-result.txt — MCP via MCPSearch ✅
- restricted-tools-result.txt — allowed-tools not enforced ✅
- allowed-mcp-result.txt — allowed-tools pre-loads MCP ✅
- disallowed-mcp-result.txt — disallowedTools not enforced ✅

**Context tests:**
- context-parent-report.txt, context-child-report.txt — Context isolation ✅
- sibling-a-result.txt, sibling-b-result.txt — Sibling isolation ✅
- sibling-a-secret.txt, sibling-b-secret.txt — Filesystem shared ✅

**Inheritance tests:**
- inherit-child-result.txt, inherit-parent-result.txt — Child has MCP, parent doesn't ✅
- inherit-child2-result.txt, inherit-parent2-result.txt — No pre-inheritance from parent ✅

**Multi-layer tests:**
- 3layer-top.txt, 3layer-mid.txt, 3layer-bottom.txt, 3layer-summary.txt — 3-layer chain ✅
- agent-field-result.txt — agent: field doesn't inherit tools ✅

**Mock tests (from earlier sessions):**
- mock-orchestrator-*.txt, mock-prediction-*.txt, mock-attribution-*.txt

## 9.4 Validation Checklist

### Core Mechanics
- [x] Skill tool works in forked context — test-orchestrator-thinking → test-child-thinking chain executed
- [x] Task tool blocked in forked context — test-task-in-fork: "Task Tool NOT Available"
- [x] Thinking captured at Layer 1 — agent-ade676b.jsonl has thinking blocks
- [x] Thinking captured at Layer 2 — agent-a86e06a.jsonl has thinking blocks
- [x] File-based communication works — All test output files created
- [x] 14 tools available in fork — Bash, Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, TodoWrite, WebSearch, Skill, MCPSearch, ListMcpResourcesTool, ReadMcpResourcesTool

### Skill Frontmatter Fields
- [x] `allowed-tools` restricts tools — **NOT ENFORCED!** All tools accessible despite restriction
- [x] `allowed-tools` pre-loads MCP tools — **WORKS!** List MCP tools to make them directly available
- [x] `disallowedTools` blocks tools — **NOT ENFORCED!** Tools still accessible (test-disallowed-mcp)
- [x] `agent:` field inherits agent's tools — **NOT WORKING!** Must list tools explicitly
- [x] `model:` field works in skill frontmatter — **NOT ENFORCED!** Skill runs with parent's model (tested 2026-01-16)
  - Workaround: Use `./agent --model sonnet` for cost savings at specific layers
  - Skill-based approach always inherits parent model

### Multi-Layer Behavior
- [x] Nested skill chains work (3+ layers) — test-3layer: L1→L2→L3 all executed, data flowed correctly
- [x] Thinking captured at Layer 3 — agent-a26d87c.jsonl, agent-a4f5a9f.jsonl have thinking blocks
- [x] Return value from child reaches parent — Yes, parent sees full text output from child

### Additional Architecture Tests (2026-01-16)

*Note: Multi-Provider Tests and MCP Bash Research results are in Part 4 and Test Log above.*

**$ARGUMENTS Substitution:**
- [x] `$ARGUMENTS` in skill content gets replaced — **WORKS!** Pass args via Skill tool
- Usage: `/test-arguments hello-world` → skill sees "hello-world" where $ARGUMENTS appears

**Parallel Execution (THOROUGHLY TESTED 2026-01-16):**

| Tool | Context | Execution | Evidence |
|------|---------|-----------|----------|
| **Task tool** | Main conversation | **PARALLEL** ✅ | 3 agents started within 0.5s, each slept 5s, total ~6s |
| **Skill tool** | Main conversation | **SEQUENTIAL** ❌ | Child A at 17:57:36, Child B at 17:58:23 (47s gap) |
| **Skill tool** | Forked context | **SEQUENTIAL** ❌ | Child A at 17:50:01, Child B at 17:50:16 (14s gap) |
| **Task tool** | Forked context | **BLOCKED** ❌ | Cannot use Task in forked skills |

**Key insight**: Task tool IS parallel, but it's blocked in forked skills!

**Implications for architecture:**
- Layer 0 (main conversation) CAN spawn parallel agents using Task tool
- Layer 1+ (forked skills) CANNOT spawn parallel children

**Workarounds for parallel execution:**
1. Design orchestrator at Layer 0 (not forked) to use Task tool for parallel spawning
2. Use `./agent parallel_subagents` tool for parallel subprocess spawning (**TESTED, WORKS!**)
3. Use Claude Agent SDK with `asyncio.gather()` for parallel queries
4. Have forked skills return quickly, let orchestrator parallelize at top level

**parallel_subagents Tool (Added 2026-01-16):**
```python
# In ./agent - spawns multiple subagents using ThreadPoolExecutor
parallel_subagents('[
    {"provider": "openai", "prompt": "Query 1"},
    {"provider": "openai", "prompt": "Query 2"},
    {"provider": "gemini", "prompt": "Query 3"}
]')
```
**Test results**: 3 agents completed in ~12 seconds (A & B wrote within 48ms of each other!)
**Evidence**: `earnings-analysis/test-outputs/parallel-agent-*.txt`

**Error Propagation:**
- [x] Parent receives exception when child fails? — **NO**
- Errors embedded in text response, not thrown as exceptions
- Skill tool returns "completed" even if child had errors
- **Detection strategy**: Parse response text for "Error", "Failed", or check expected outputs

### Existing Agents
- [x] Can skill `agent:` field reference existing agents? — **NO**, agent: field doesn't grant agent's tools/permissions to skill. Use MCPSearch workaround instead.

**Available agents** (can be used with Task tool, NOT with Skill tool):
- neo4j-report, neo4j-transcript, neo4j-xbrl, neo4j-entity, neo4j-news
- perplexity-ask, perplexity-search, perplexity-reason, perplexity-research, perplexity-sec
- alphavantage-earnings

## 9.5 SDK Verified Capabilities (2026-01-16)

| Test | Result | Evidence |
|------|--------|----------|
| Skills loaded | ✅ 61 skills | Init message `slash_commands` |
| MCP servers | ✅ 3 connected | neo4j-cypher, perplexity, alphavantage |
| Skill invocation | ✅ PASS | `/neo4j-report` returned AAPL 8-K |
| Skill chaining | ✅ PASS | `/neo4j-report` → `/neo4j-entity` in sequence |
| MCP Neo4j query | ✅ PASS | Returned accession `0000320193-25-000071`, company `APPLE INC` |
| File writing | ✅ PASS | Created `skill-chain-proof.txt` with query results |

### Test Scripts

| Script | Purpose | Run Time |
|--------|---------|----------|
| `scripts/test_sdk_compatibility.py` | Quick SDK verify | ~30s |
| `scripts/test_skill_chain_quick.py` | Sequential skill calls (SDK → A, SDK → B) | ~60s |
| `scripts/test_nested_skill_chain.py` | **Nested chaining (SDK → A → B → C)** | ~90s |
| `scripts/test_earnings_attribution.py` | Full attribution test | 5-10min |
| `scripts/earnings_trigger.py` | Production listener | Continuous |

### Test Evidence

```
earnings-analysis/test-outputs/sdk-compatibility-test.txt:
SDK_TEST_PASSED
Timestamp: 2026-01-16T18:00:07.142794
Skill: neo4j-report invoked successfully

earnings-analysis/test-outputs/skill-chain-proof.txt:
SKILL_CHAIN_TEST
Report: 0000320193-25-000071
Company: APPLE INC
```

### Why earnings-attribution Will Work

| Mechanism | Used By earnings-attribution | Tested |
|-----------|------------------------------|--------|
| Skill invocation | `/neo4j-report`, `/neo4j-news`, `/perplexity-search` | ✅ |
| Skill chaining | Multiple skills in sequence | ✅ |
| MCP Neo4j | 8-K data, news, transcripts | ✅ |
| File writing | `Companies/{ticker}/{accession}.md` | ✅ |

## 9.6 3-Layer Skill Chain via SDK (Final Proof - 2026-01-16)

The ultimate test: SDK → skill → skill → skill → MCP → Neo4j

**Command:**
```bash
source venv/bin/activate
python scripts/test_skill_chain_quick.py
```

**What it tested:**
```
SDK query("/test-3layer-top")
    │
    └─→ L1: test-3layer-top (forked skill)
            │
            └─→ L2: test-3layer-mid (forked skill)
                    │
                    └─→ L3: test-3layer-bottom (forked skill)
                            │
                            └─→ MCP: neo4j-cypher__read_neo4j_cypher
                                    │
                                    └─→ Neo4j: MATCH (c:Company) RETURN c.ticker LIMIT 3
```

**Output files created:**
| File | Content | Evidence |
|------|---------|----------|
| `3layer-bottom.txt` | `LAYER3_RESULT: [FMC, SMG, FLS]` | MCP query executed ✅ |
| `3layer-mid.txt` | L2 received L3 result + added LAYER2_SECRET | Data bubbled up ✅ |
| `3layer-top.txt` | L1 received aggregated data from L2 | Full chain complete ✅ |
| `3layer-summary.txt` | Comprehensive test summary | All layers passed ✅ |

**Proof points:**
1. ✅ SDK invoked L1 skill
2. ✅ L1 invoked L2 using Skill tool
3. ✅ L2 invoked L3 using Skill tool
4. ✅ L3 used MCP tool (pre-loaded via allowed-tools)
5. ✅ Data flowed back: L3 → L2 → L1
6. ✅ Context isolation: Each layer had unique secret
7. ✅ All layers used forked execution mode

**100% CONFIRMED: SDK works with full multi-layer skill architecture.**

## 9.7 Re-Verification Commands

```bash
# Check all test outputs exist
ls -la earnings-analysis/test-outputs/*.txt | wc -l  # Should be 53+

# Re-run 3-layer test
source venv/bin/activate && python scripts/test_skill_chain_quick.py

# Test SDK compatibility
python scripts/test_sdk_compatibility.py
```

---

# Part 10: Task Management System

*Last Updated: 2026-01-27*

## 10.1 Overview

Claude Code has **7 task-related tools** in two categories:

### Task Management Tools (Tracking Work)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| **TaskCreate** | Create a new task | `subject`, `description`, `activeForm` |
| **TaskList** | View all tasks and status | (none) |
| **TaskGet** | Get full task details by ID | `taskId` |
| **TaskUpdate** | Update status, dependencies, or delete | `taskId`, `status`, `addBlockedBy`, `description` |

### Sub-Agent Spawning Tools (Parallel Execution)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| **Task** | Spawn a sub-agent to handle work | `subagent_type`, `prompt`, `description`, `run_in_background` |
| **TaskOutput** | Retrieve results from background task | `task_id`, `block`, `timeout` |
| **TaskStop** | Cancel/stop a running background task | `task_id` |

### Key Distinction

- **Task Management** (TaskCreate/List/Get/Update): Track work items, manage dependencies, share state across agents
- **Sub-Agent Spawning** (Task/TaskOutput/TaskStop): Execute parallel work via independent agents

### Validated (2026-01-27)

| Tool | Tested | Result |
|------|--------|--------|
| TaskCreate | ✅ | Creates task, returns ID |
| TaskList | ✅ | Shows all tasks with status |
| TaskGet | ✅ | Returns full task details |
| TaskUpdate | ✅ | Updates status, description; `status: deleted` removes file |
| Task | ✅ | Spawns sub-agents, supports background mode |
| TaskOutput | ✅ | Retrieves background task results |
| TaskStop | ✅ | Terminates running task (SIGKILL, exit 137) |

### Task Fields

```json
{
  "id": "1",
  "subject": "Implement feature X",
  "description": "Detailed description of work",
  "activeForm": "Implementing feature X",  // Shown in spinner
  "status": "pending",                      // pending | in_progress | completed
  "blocks": ["2", "3"],                     // Tasks waiting on this one
  "blockedBy": ["0"]                        // Tasks this one waits for
}
```

---

## 10.2 Storage & Persistence

### Storage Location

Tasks are stored at: `~/.claude/tasks/{TASK_LIST_ID}/`

```
~/.claude/tasks/
├── random-uuid-session-1/     ← Default (random per session)
│   ├── 1.json
│   └── 2.json
├── random-uuid-session-2/
│   └── 1.json
└── my-project-tasks/          ← Custom named (persists across sessions!)
    ├── 1.json
    ├── 2.json
    └── 3.json
```

**Note**: The base path (`~/.claude/tasks/`) is NOT configurable. Only the subdirectory name can be customized via `CLAUDE_CODE_TASK_LIST_ID`.

### Task Status Behavior

| Status | File Behavior |
|--------|---------------|
| `pending` | File exists |
| `in_progress` | File exists, status field updated |
| `completed` | File exists, status field updated |
| `deleted` | **File removed from disk** |

---

## 10.3 Cross-Session Persistence

By default, each session gets a random UUID directory and tasks don't persist across sessions.

**To enable persistence**, set `CLAUDE_CODE_TASK_LIST_ID` to a fixed name:

### Method 1: Environment Variables

```bash
export CLAUDE_CODE_ENABLE_TASKS=true
export CLAUDE_CODE_TASK_LIST_ID=my-project-tasks
claude   # or run SDK script
```

### Method 2: settings.json (Recommended)

Add to your project's `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_TASK_LIST_ID": "eventmarketdb-tasks",
    "CLAUDE_CODE_ENABLE_TASKS": "true"
  }
}
```

### Settings Scope Hierarchy

| Scope | Location | Shared via Git? |
|-------|----------|-----------------|
| Project | `.claude/settings.json` | Yes |
| Local | `.claude/settings.local.json` | No (gitignored) |
| User | `~/.claude/settings.json` | No |

**Precedence**: Local > Project > User

### Verified Test Results (2026-01-27)

| Test | Result |
|------|--------|
| Session 1: Create task #1 | ✅ Stored in custom directory |
| Session 2: TaskList | ✅ Saw task #1 from previous session |
| Session 3: Update task #1 → completed | ✅ File updated, not deleted |
| Session 4: Update task #1 → deleted | ✅ File removed from disk |
| settings.json config (no manual export) | ✅ Works with `setting_sources=['project']` |

---

## 10.4 SDK Usage

### Requirements (3 Things Needed)

```python
# 1. Environment variable (or settings.json)
export CLAUDE_CODE_ENABLE_TASKS=true

# 2. SDK version 0.1.23+ (CRITICAL - older versions have a bug!)
pip install --upgrade claude-agent-sdk  # Must be >= 0.1.23

# 3. Use tools preset in your code
from claude_agent_sdk import query, ClaudeAgentOptions

async for msg in query(
    prompt='Use TaskCreate to create a task...',
    options=ClaudeAgentOptions(
        permission_mode='bypassPermissions',
        tools={'type': 'preset', 'preset': 'claude_code'},  # THIS IS KEY!
        setting_sources=['project'],  # Loads .claude/settings.json
    )
):
    ...
```

### SDK Version History

| SDK Version | Task Tools Work? | Notes |
|-------------|------------------|-------|
| 0.1.19 | ❌ NO | Bug - didn't pass task tools to subprocess |
| 0.1.23+ | ✅ YES | Fixed with `tools` preset + env var |

### Complete SDK Example

```python
#!/usr/bin/env python3
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    # With settings.json configured, no manual export needed
    async for msg in query(
        prompt='Create a task "Test Task" and then list all tasks',
        options=ClaudeAgentOptions(
            permission_mode='bypassPermissions',
            tools={'type': 'preset', 'preset': 'claude_code'},
            setting_sources=['project'],
            max_turns=5,
        )
    ):
        if hasattr(msg, 'content'):
            for block in msg.content:
                if hasattr(block, 'name'):
                    print(f'Tool: {block.name}')
        if hasattr(msg, 'result'):
            print(msg.result)

asyncio.run(main())
```

---

## 10.5 Tool Availability Matrix

| Context | TaskCreate/List/Get/Update | Task Tool (Subagents) | Requirements |
|---------|---------------------------|----------------------|--------------|
| Interactive CLI | ✅ YES | ✅ YES | None |
| SDK 0.1.23+ | ✅ YES | ✅ YES | `tools` preset + env var |
| SDK 0.1.19 (old) | ❌ NO | ✅ YES | BUG - upgrade SDK |
| Forked Skill (CLI) | ✅ YES | ❌ NO | - |
| Forked Skill (SDK 0.1.23+) | ✅ YES | ❌ NO | - |

**Key Distinction**:
- **Task tool** = Spawns sub-agents (parallel execution)
- **TaskCreate/List/Get/Update** = Task management (tracking work)

These are different tools. Forked skills can track tasks but cannot spawn sub-agents.

---

## 10.6 Parallel Execution

### Rules (Empirically Proven)

| Method | Execution | Evidence |
|--------|-----------|----------|
| Task tool → Sub-agents | ✅ **PARALLEL** | 0.24s gap between launches |
| Skill tool → Skills | ❌ **SEQUENTIAL** | 14+ second gaps |
| Sub-agent → Sub-agent | ❌ **IMPOSSIBLE** | Task tool unavailable in sub-agents |

### Architecture Implication

```
SDK query() → Main conversation (HAS Task tool + TaskCreate/TaskList)
    │
    ├─► Task: news_impact ──┐
    │                       ├──► Both run PARALLEL
    └─► Task: guidance ─────┘
                │
                └─► After both complete → sequential work
```

**Parallelism is ONE level deep only** - orchestrator can spawn parallel sub-agents, but sub-agents cannot spawn more sub-agents.

---

## 10.7 Dependencies

Tasks support dependency management:

```python
# Create tasks with dependencies
TaskCreate("Task A", "First task")           # id: 1
TaskCreate("Task B", "Depends on A")         # id: 2
TaskUpdate(taskId="2", addBlockedBy=["1"])   # B blocked by A

# When A completes, B becomes unblocked
TaskUpdate(taskId="1", status="completed")
```

### Verified Patterns

| Pattern | Works? |
|---------|--------|
| Chain (A→B→C) | ✅ Completing A unblocks B |
| Multiple blockers (D,E→G) | ✅ AND logic - both must complete |
| Wave parallelism | ✅ Unblocked tasks can run parallel |

---

## 10.8 Multi-Agent Coordination Patterns (Verified 2026-01-27)

Orchestrators can use the shared task list to coordinate multiple sub-agents.

### Pattern 1: Sub-Agents See Shared Task List

Sub-agents spawned via Task tool can see and update the same task list as the parent.

```
Orchestrator creates Task #1 → Sub-agent sees Task #1 via TaskList
                             → Sub-agent marks Task #1 completed
                             → Orchestrator sees the update
```

**Verified**: ✅ Changes by sub-agent immediately visible to parent.

### Pattern 2: Sub-Agents Pass Info to Next Agent

A sub-agent can add notes to another task's description for the next agent to read.

```python
# Agent-A completes task #1, adds info for Agent-B working on task #2
TaskUpdate(taskId="2", description="Original desc\n\nNOTE-FROM-AGENT-A: Data format is JSON")

# Agent-B reads task #2 and sees the note
TaskGet(taskId="2")  # Returns description with Agent-A's note
```

**Verified**: ✅ Agent-A added note, Agent-B found it.

### Pattern 3: Different Agent Types for Different Tasks

Use specialized sub-agent types for different task types.

**⚠️ Important**: Task tools depend on agent's `tools:` list!

| Agent Type | Has TaskList/Update? | Why |
|------------|---------------------|-----|
| **general-purpose** | ✅ YES | Has all tools by default |
| **Explore** | ✅ YES | Broad toolset |
| **Plan** | ✅ YES | Broad toolset |
| **Bash** | ❌ NO | Only has Bash in tools list |
| **Custom agents** | ⚠️ DEPENDS | Only if task tools in `tools:` list |

### How to Give Custom Agents Task Tools

Add task tools to the agent's `tools:` list in `.claude/agents/`:

```yaml
# .claude/agents/my-custom-agent.md
---
name: my-custom-agent
description: "Custom agent with task coordination"
tools:
  - Bash
  - TaskList      # ← Add these to enable task coordination
  - TaskCreate
  - TaskUpdate
  - TaskGet
permissionMode: dontAsk
---
```

**Verified (2026-01-28)**:
- `test-task-agent` (Bash + TaskList/Create/Update/Get) → ✅ TaskList works, TaskUpdate works
- `bz-news-driver` (Bash + TaskList/Get/Update) → ✅ TaskUpdate works — stored result in task description
- `external-news-driver` (tools + TaskList/Get/Update) → ✅ TaskUpdate works in full orchestrator flow
- `bz-news-driver` (only Bash in tools, old) → ❌ No TaskList access

**Key findings**:
1. Custom agents MUST have task tools explicitly listed AND clear mandatory instructions ("MANDATORY" / "NOT optional" language)
2. **Shared task list requires `CLAUDE_CODE_TASK_LIST_ID` in settings.json** — without it, orchestrator and sub-agents use different random task list IDs and can't see each other's tasks
3. Setting takes effect on session restart (not mid-session)

**Required settings.json for shared task list**:
```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TASKS": "true",
    "CLAUDE_CODE_TASK_LIST_ID": "earnings-orchestrator"
  }
}
```

All sessions/sub-agents then share `~/.claude/tasks/earnings-orchestrator/`. Use quarter+ticker prefix in task subjects for filtering:
- `BZ-Q4_FY2022 NOG 2023-01-03` (Benzinga analysis)
- `EXT-Q1_FY2023 NOG 2023-03-15` (External research)

**Resume logic**: Filter TaskList where subject starts with `BZ-Q4_FY2022 NOG` to find all Q4 work for that ticker.

### Alternative: Per-Ticker Isolation via Subprocess

For true filesystem isolation per ticker, spawn a subprocess with dynamic task list ID:

```bash
CLAUDE_CODE_TASK_LIST_ID=AAPL claude -p "Create task, spawn bz-news-driver..." --allowedTools "TaskCreate,TaskList,TaskGet,TaskUpdate,Task,Bash"
```

This subprocess:
1. Gets its own task list (`~/.claude/tasks/AAPL/`)
2. Can create tasks, spawn sub-agents, update tasks
3. Completely isolated per ticker

**Important**: Only works when settings.json does NOT have a static `CLAUDE_CODE_TASK_LIST_ID` — env var is overridden by settings.json.

**Trade-offs**:
| Approach | Pros | Cons |
|----------|------|------|
| **Shared list + prefix** | Simpler, no subprocess overhead | All tickers in one list |
| **Subprocess per ticker** | True isolation, parallel-safe | More complex, subprocess management |

**Recommendation**: Use shared list with ticker prefix for sequential processing. Use subprocess pattern only if running multiple tickers in parallel from different terminals.

**Working agent definition** (`.claude/agents/test-task-agent.md`):
```yaml
tools:
  - Bash
  - TaskList
  - TaskCreate
  - TaskUpdate
  - TaskGet
```

**Working bz-news-driver pattern** (`.claude/agents/bz-news-driver.md`):
```yaml
tools:
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
```
With mandatory Step 3 instruction:
```markdown
### Step 3: Update Task (MANDATORY)
**You MUST do this before returning.** Extract the task ID number N from `TASK_ID=N` in your prompt.
1. Call `TaskUpdate` with `taskId: "N"`, `status: "completed"`, and `description` set to your result line
2. This is NOT optional — the orchestrator reads your result from the task
```

### Orchestrator Instructions Template

Add these instructions to your orchestrator skill:

```markdown
## Task Coordination Rules

1. **Create tasks first**: Use TaskCreate to create all tasks with dependencies before spawning sub-agents.

2. **Tell sub-agents to update**: In each sub-agent prompt, include:
   "When you complete your work, use TaskUpdate to mark task #X as completed."

3. **Pass info forward**: Tell sub-agents:
   "If you discover something the next task needs to know, use TaskUpdate on that task to add a note to its description."

4. **Use appropriate agent types**:
   - Use `general-purpose` for tasks that need to update the task list
   - Use specialized agents (Bash, Explore) only for tasks that don't need task coordination

5. **Check task status**: After spawning sub-agents, use TaskList to verify tasks were completed.
```

### Example: Orchestrator Prompt

```
You are an orchestrator. Follow these steps:

1. Create tasks:
   - Task 1: "Fetch earnings data"
   - Task 2: "Analyze data" (blocked by Task 1)
   - Task 3: "Generate report" (blocked by Task 2)

2. Spawn sub-agent (general-purpose) for Task 1:
   "Find FETCH-EARNINGS task via TaskList. Mark it in_progress.
    Fetch the data. When done, mark it completed.
    If you find anything Task 2 should know, update Task 2's description with that info."

3. Spawn sub-agent (general-purpose) for Task 2:
   "Find ANALYZE-DATA task via TaskList. Read its description for any notes from previous agents.
    Do the analysis. Mark completed when done.
    Add any findings to Task 3's description for the report generator."

4. Spawn sub-agent (general-purpose) for Task 3:
   "Read Task 3 description for context from previous agents.
    Generate the report. Mark completed."

5. Use TaskList to verify all tasks completed.
```

---

## 10.9 Current Project Configuration

**File**: `/home/faisal/EventMarketDB/.claude/settings.json`

```json
{
  "plansDirectory": ".claude/plans",
  "env": {
    "CLAUDE_CODE_TASK_LIST_ID": "eventmarketdb-tasks",
    "CLAUDE_CODE_ENABLE_TASKS": "true"
  }
}
```

**Task storage**: `~/.claude/tasks/eventmarketdb-tasks/`

---

## 10.10 Limitations & Workarounds

### Cannot Customize Base Path

Tasks always go to `~/.claude/tasks/`. Cannot store in project directory.

**Workaround**: Use symlink
```bash
mkdir -p /path/to/project/.claude/tasks/my-tasks
ln -s /path/to/project/.claude/tasks/my-tasks ~/.claude/tasks/my-tasks
```

### Task Tools in Forked Skills

Forked skills CAN use TaskCreate/List/Get/Update but CANNOT use Task tool (sub-agent spawner).

**Workaround**: Keep orchestrator in main conversation for parallel execution.

---

## 10.11 Quick Reference

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `CLAUDE_CODE_ENABLE_TASKS` | Enable task tools | Yes (for SDK) |
| `CLAUDE_CODE_TASK_LIST_ID` | Custom task directory name | No (enables persistence) |

### SDK Options

```python
ClaudeAgentOptions(
    tools={'type': 'preset', 'preset': 'claude_code'},  # Required for task tools
    setting_sources=['project'],  # Load .claude/settings.json
    permission_mode='bypassPermissions',  # For automation
)
```

### Common Commands

```bash
# Upgrade SDK
pip install --upgrade claude-agent-sdk

# Check SDK version
pip show claude-agent-sdk | grep Version

# View task files
ls -la ~/.claude/tasks/eventmarketdb-tasks/

# Clean up old task directories
rm -rf ~/.claude/tasks/random-uuid-*
```

---

## 10.12 Dynamic Per-Ticker Task Lists (Tested 2026-01-28)

### The Problem

You want each ticker (AAPL, MSFT, etc.) to get its own task folder so tasks don't mix:
```
~/.claude/tasks/earnings-AAPL/   ← AAPL tasks only
~/.claude/tasks/earnings-MSFT/   ← MSFT tasks only
```

To do this you'd set `CLAUDE_CODE_TASK_LIST_ID=earnings-AAPL` before launching Claude.

### The Catch: settings.json Always Wins

If `.claude/settings.json` has `CLAUDE_CODE_TASK_LIST_ID` set, it **overwrites** any env var you pass from the terminal or SDK. The env var you set is ignored.

```
Terminal: CLAUDE_CODE_TASK_LIST_ID=earnings-AAPL
                     ↓
settings.json also sets: CLAUDE_CODE_TASK_LIST_ID=eventmarketdb-tasks
                     ↓
Result: tasks go to eventmarketdb-tasks/  ← your env var was ignored
```

### Test Evidence (2026-01-28)

| Test | settings.json has ID? | Env var set? | Task landed in | Result |
|------|----------------------|-------------|---------------|--------|
| CLI | YES (`eventmarketdb-tasks`) | YES (`earnings-AAPL-test`) | `eventmarketdb-tasks/` | **env var ignored** |
| CLI | NO (removed) | YES (`earnings-AAPL-test`) | `earnings-AAPL-test/` | **works** |
| SDK | NO (removed) | YES (`earnings-MSFT-test`) | `earnings-MSFT-test/` | **works** |

### How to Enable Dynamic Per-Ticker Lists

**Step 1**: Remove `CLAUDE_CODE_TASK_LIST_ID` from `.claude/settings.json`:
```json
{
  "plansDirectory": ".claude/plans",
  "env": {
    "CLAUDE_CODE_ENABLE_TASKS": "true"
  }
}
```

**Step 2 (CLI)**: Set the variable before each session:
```bash
CLAUDE_CODE_TASK_LIST_ID=earnings-AAPL claude -p "/earnings-orchestrator AAPL"
```

**Step 2 (SDK)**: Set it in Python before calling `query()`:
```python
ticker = sys.argv[1]
os.environ["CLAUDE_CODE_TASK_LIST_ID"] = f"earnings-{ticker}"

async for msg in query(
    prompt=f"/earnings-orchestrator {ticker}",
    options=ClaudeAgentOptions(
        setting_sources=["project"],
        permission_mode="bypassPermissions",
    )
):
    ...
```

### Tradeoff

| Scenario | With static ID in settings.json | Without (dynamic) |
|----------|--------------------------------|--------------------|
| Interactive `claude` (no env var) | Tasks persist in `eventmarketdb-tasks/` | Random UUID folder, tasks lost between sessions |
| Scripted/SDK per-ticker | **Cannot override** — all tickers share one folder | Each ticker gets its own folder |

### Precedence Rule

```
settings.json env block  >  process environment variable  >  random UUID default
```

There is no way to set a "default" in settings.json and override it per-session. It's one or the other.

### Cross-Session Resume (Tested 2026-01-28)

The same folder name = the same tasks. You can resume across any number of sessions, from both CLI and SDK.

**Tested 3-session scenario with `earnings-GOOG-resume`:**

| Session | Method | Action | Result |
|---------|--------|--------|--------|
| 1 | CLI | Created 3 tasks, completed #1, started #2 | Folder created with 3 JSON files |
| 2 | CLI (new session) | TaskList → saw all 3, completed #2, started #3 | Picked up exactly where Session 1 left off |
| 3 | SDK (Python) | TaskList → saw all 3, completed #3, deleted #1 | File `1.json` removed from disk, #2 and #3 remain |

**Key facts:**
- **Reuse**: Same `CLAUDE_CODE_TASK_LIST_ID` value → same folder → same tasks. Works indefinitely.
- **Partial cleanup**: Delete some tasks (file removed from disk), keep others. Next session sees only what remains.
- **Full cleanup**: Delete all tasks. Folder still exists (with `.lock`/`.highwatermark`). Next session starts fresh with new task IDs.
- **Both CLI and SDK**: Both read/write the same folder. You can create tasks from CLI, update them from SDK, or vice versa.

---

## 10.13 Background vs Foreground Agent Spawning (Tested 2026-01-29)

### The Problem

When using `run_in_background: true` with the Task tool, spawned agents lose access to task management tools (TaskCreate, TaskList, TaskGet, TaskUpdate) even when explicitly listed in the agent's `tools:` field.

### Test Evidence

| Mode | TaskList | TaskCreate | TaskUpdate | Write Files |
|------|----------|------------|------------|-------------|
| **Foreground** (default) | ✅ YES | ✅ YES | ✅ YES | ✅ YES |
| **Background** (`run_in_background: true`) | ❌ NO | ❌ NO | ❌ NO | ❌ NO |

**Background agent thinking (from test):**
> "Looking at my function definitions, I only have access to the **Bash** tool. I don't have TaskList, TaskCreate, TaskUpdate, or any other task management tools available."

### Root Cause

This is a **known bug** affecting multiple tool types:
- [#13254](https://github.com/anthropics/claude-code/issues/13254) - Background subagents cannot access MCP tools (REOPENED)
- [#13890](https://github.com/anthropics/claude-code/issues/13890) - Subagents unable to write files and call MCP tools (OPEN)
- [#14521](https://github.com/anthropics/claude-code/issues/14521) - Background agents cannot write files (Duplicate)

`run_in_background: true` spawns agents with a **reduced tool set** - only basic tools like Bash are available.

### The Solution: Foreground Parallel Spawns

**Key insight**: Multiple Task calls in the SAME message run in PARALLEL even without `run_in_background`.

```
Orchestrator sends ONE message with multiple Task tool calls:
├── Task: news-driver-bz for date 1  ──┐
├── Task: news-driver-bz for date 2  ──┼──► All run in PARALLEL
├── Task: news-driver-bz for date 3  ──┤
└── Task: news-driver-bz for date 4  ──┘
                                        │
                                        ▼
                        Orchestrator BLOCKS until all complete
                        (but agents execute concurrently)
```

**Benefits:**
- Agents have full tool access (TaskCreate, TaskUpdate, MCP, Write, etc.)
- Agents run in parallel (0.24s gap between launches)
- Orchestrator waits for all to complete, then continues

**Trade-off:**
- Orchestrator cannot do other work while waiting (blocking)
- For our use case (batch processing), this is acceptable

### Verified Patterns (All ✅)

| Pattern | Context | Result |
|---------|---------|--------|
| TaskCreate/List/Get/Update | CLI main | ✅ Works |
| TaskCreate/List/Get/Update | CLI skill | ✅ Works |
| TaskCreate/List/Get/Update | SDK skill | ✅ Works |
| Parallel foreground Task spawn | CLI main | ✅ Agents run parallel, have task tools |
| Parallel foreground Task spawn | CLI skill | ✅ Works |
| Single foreground Task spawn | SDK skill | ✅ Agent updated task successfully |
| Agent uses TaskUpdate to store result | All contexts | ✅ Works |

### Implementation for earnings-orchestrator

```markdown
## Correct Pattern (Foreground)

1. Create all tasks first:
   - TaskCreate subject="BZ-Q1 AAPL 2024-01-02", description="pending"
   - TaskCreate subject="BZ-Q1 AAPL 2024-01-03", description="pending"

2. Spawn all agents in ONE message (NO run_in_background):
   - Task subagent_type="news-driver-bz" prompt="... TASK_ID=1 ..."
   - Task subagent_type="news-driver-bz" prompt="... TASK_ID=2 ..."
   (Both run in parallel, both have task tools)

3. Agents update their tasks:
   - Each agent calls TaskUpdate with results

4. Orchestrator continues after all agents complete:
   - Read results via TaskGet
   - Create WEB tasks for escalation
   - Repeat pattern for WEB agents
```

### What NOT to Do

```markdown
## Wrong Pattern (Background - agents lose tools)

Task subagent_type="news-driver-bz"
     prompt="..."
     run_in_background: true   ← DON'T DO THIS
```

Agents spawned with `run_in_background: true` cannot:
- Use TaskCreate/TaskList/TaskGet/TaskUpdate
- Write files
- Call MCP tools

### Test Skills Created

| Skill | Purpose | Location |
|-------|---------|----------|
| test-sdk-task-simple | Verify task tools work via SDK | `.claude/skills/test-sdk-task-simple/` |
| test-sdk-spawn-single | Verify Task spawn works via SDK | `.claude/skills/test-sdk-spawn-single/` |
| test-parallel-fg-task | Verify parallel FG spawns in skill | `.claude/skills/test-parallel-fg-task/` |

### Test Output Files

| File | Evidence |
|------|----------|
| `sdk-task-simple-test.txt` | TaskCreate/List/Update/Get all work via SDK |
| `sdk-spawn-single-test.txt` | Spawned agent updated task via SDK |
| `parallel-fg-task-test.txt` | Parallel FG spawns work in skill context |

---

*Updated: 2026-01-29 | Background vs foreground tool availability tested | Foreground parallel pattern verified | SDK compatibility confirmed*

---

## 10.14 Upfront Task Creation & Dependency Patterns (Tested 2026-01-29)

### Overview

This section documents validated patterns for creating all tasks upfront with dependencies, allowing sub-agents to skip tiers by marking tasks as completed/deleted.

### Task Unblocking Mechanisms

**Two ways to unblock a dependent task:**

| Method | Command | Effect on Blocker | Effect on Dependent | Audit Trail |
|--------|---------|-------------------|---------------------|-------------|
| **Complete** | `TaskUpdate taskId=X status="completed"` | Task stays in list (status: completed) | Unblocked ✅ | Full - can see completed tasks |
| **Delete** | `TaskUpdate taskId=X status="deleted"` | Task removed from list | Unblocked ✅ | Minimal - task disappears |

**Both methods work identically for unblocking** - the dependent task becomes ready as soon as its blocker is either completed or deleted.

### Validated Test Results

| Test | Scenario | Result | Evidence File |
|------|----------|--------|---------------|
| **test-parallel-task-spawn** | 3 agents spawned in parallel | ✅ 194ms spread | `parallel-task-spawn.txt` |
| **test-upfront-tasks** | 8 tasks, BZ deletes WEB/PPX | ✅ All patterns work | `upfront-tasks.txt` |
| **test-cross-agent-delete** | BZ deletes tasks meant for WEB/PPX agents | ✅ Cross-agent works | `cross-agent-delete.txt` |
| **Completion unblocks** | Complete blocker → dependent ready | ✅ Works | Inline test |
| **Deletion unblocks** | Delete blocker → dependent ready | ✅ Works | Inline test |

### Cross-Agent Task Manipulation

**Key finding**: Tasks have NO ownership. Any agent with TaskUpdate can modify ANY task by ID.

```
Orchestrator creates:
  #1: BZ-Q1 AAPL 2024-01-02  (for news-driver-bz)
  #2: WEB-Q1 AAPL 2024-01-02 (for news-driver-web) [blocked by #1]
  #3: PPX-Q1 AAPL 2024-01-02 (for news-driver-ppx) [blocked by #2]
  #4: JUDGE-Q1 AAPL 2024-01-02 (for news-driver-judge) [blocked by #3]

BZ agent finds answer early:
  → TaskUpdate taskId="2" status="completed" description="SKIPPED: BZ found answer"
  → TaskUpdate taskId="3" status="completed" description="SKIPPED: BZ found answer"
  → TaskUpdate taskId="4" description="READY: {10-field result line}"
  → TaskUpdate taskId="1" status="completed"

Result: JUDGE (#4) is now unblocked and ready to run!
```

**Why this works**: The task system is shared global state. Task IDs are the only identifiers - there's no concept of which agent "owns" a task.

### The Upfront Task Creation Pattern

**Traditional Pattern (Reactive)**:
```
Orchestrator creates BZ tasks
  → BZ agents create WEB tasks (if needed)
    → WEB agents create PPX tasks (if needed)
      → PPX agents create JUDGE tasks
```
Problems: Polling latency, no cross-tier parallelism, complex sub-agents

**Upfront Pattern (Event-Driven)**:
```
Orchestrator creates ALL tasks upfront:
  BZ-1 → WEB-1 → PPX-1 → JUDGE-1  (dependencies set)
  BZ-2 → WEB-2 → PPX-2 → JUDGE-2  (dependencies set)

BZ agents run in parallel:
  BZ-1 finds answer → marks WEB-1/PPX-1 as "SKIPPED" → JUDGE-1 unblocks
  BZ-2 needs escalation → completes → WEB-2 unblocks

Orchestrator polls for ready tasks:
  → Finds JUDGE-1 and WEB-2 ready → spawns both in parallel!
```

Benefits: Cross-tier parallelism, simpler sub-agents (no TaskCreate needed), full visibility

### Implementation: Skip Pattern with COMPLETED Status

**Recommended**: Use `status="completed"` with SKIPPED marker instead of delete for audit trail.

```markdown
# BZ Agent Instructions (when external_research=false)

If you find the answer (no external research needed):
1. Mark WEB task as skipped:
   TaskUpdate taskId="{WEB_TASK_ID}" status="completed" description="SKIPPED: BZ found answer"
2. Mark PPX task as skipped:
   TaskUpdate taskId="{PPX_TASK_ID}" status="completed" description="SKIPPED: BZ found answer"
3. Update JUDGE task with your result:
   TaskUpdate taskId="{JUDGE_TASK_ID}" description="READY: {10-field result line}"
4. Mark your own task as completed:
   TaskUpdate taskId="{TASK_ID}" status="completed" description="{10-field result line}"

If you need external research:
1. Just mark your own task as completed:
   TaskUpdate taskId="{TASK_ID}" status="completed" description="{10-field result line}"
   (WEB task will auto-unblock because its blocker is complete)
```

### Dependency Parameters

| Parameter | Direction | Example | Meaning |
|-----------|-----------|---------|---------|
| `addBlockedBy` | This task waits for others | `TaskUpdate id=3 addBlockedBy=["1","2"]` | Task #3 waits for #1 AND #2 |
| `addBlocks` | This task blocks others | `TaskUpdate id=1 addBlocks=["3","4"]` | Task #1 blocks #3 and #4 |

**Note**: No `removeBlockedBy` parameter exists. To unblock a task, you must complete or delete its blockers.

### Comparison of Approaches

| Aspect | Reactive (current) | Upfront (new) |
|--------|-------------------|---------------|
| Task creation | Dynamic by sub-agents | All upfront by orchestrator |
| Sub-agent complexity | Must have TaskCreate | Only needs TaskUpdate |
| Cross-tier parallelism | ❌ No (JUDGE-1 waits for all WEB) | ✅ Yes (JUDGE-1 runs while WEB-2 runs) |
| Audit trail | Tasks appear as created | Full tree visible from start |
| Skipped tiers | Never created | Marked as SKIPPED (completed) |
| Polling loop | Tier-specific (check WEB, then PPX, then JUDGE) | Unified (check any unblocked) |

### Unified Polling Loop (New Pattern)

```python
# Instead of checking each tier separately:
WHILE any tasks pending:
    ready_tasks = [t for t in TaskList()
                   if t.status == "pending"
                   and all(blocker.status in ["completed", "deleted"]
                           for blocker in t.blockedBy)]

    for task in ready_tasks:
        if task.subject.startswith("WEB-"):
            spawn news-driver-web with PPX_ID, JUDGE_ID
        elif task.subject.startswith("PPX-"):
            spawn news-driver-ppx with JUDGE_ID
        elif task.subject.startswith("JUDGE-"):
            spawn news-driver-judge

    wait for spawned agents
    brief pause, repeat
```

### Test Skills Created

| Skill | Purpose | Location |
|-------|---------|----------|
| test-parallel-task-spawn | Verify parallel Task spawning | `.claude/skills/test-parallel-task-spawn/` |
| test-upfront-tasks | Full upfront pattern with deletion | `.claude/skills/test-upfront-tasks/` |
| test-task-dependency-flow | Event-driven task flow | `.claude/skills/test-task-dependency-flow/` |
| test-incremental-spawn | Incremental spawning pattern | `.claude/skills/test-incremental-spawn/` |

### Test Output Files

| File | Evidence |
|------|----------|
| `parallel-task-spawn.txt` | 194ms spread proves parallel execution |
| `upfront-tasks.txt` | Task deletion works, mixed-tier spawning works |
| `cross-agent-delete.txt` | BZ deleted WEB/PPX tasks, JUDGE unblocked |

---

*Updated: 2026-01-29 | Upfront task creation pattern validated | Cross-agent task manipulation confirmed | Completion vs deletion for unblocking tested*
