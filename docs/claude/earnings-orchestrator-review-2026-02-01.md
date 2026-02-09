# Earnings Orchestrator Review (2026-02-01)

This note captures the in-depth review of the earnings orchestrator, Claude Code alignment, and the observed failure modes from the 2026-02-01 AAPL run.

## Doc Alignment

- Claude Code skills live in .claude/skills/<skill>/SKILL.md and use YAML frontmatter (name, description, allowed-tools, context, agent). The earnings-orchestrator skill matches this layout.
  - Source: Claude Code docs (turn2view0)
- Subagents are defined in .claude/agents/*.md with frontmatter like name, description, tools, and model. The guidance-extract and news-driver-* agents match this structure.
  - Source: Claude Code docs (turn4view1)
- The Task tool is a built-in Claude Code tool for running subagents. The orchestrator's TaskCreate/List/Get/Update usage aligns with the documented tool.
  - Source: Claude Code docs (turn5view0)
- Hooks are configured in settings and can also be attached to skills/agents. Supported events include PreToolUse, PostToolUse, and Stop, aligning with the PostToolUse hook in the orchestrator.
  - Source: Claude Code docs (turn6view3)

## Current Orchestrator Structure (Local)

- Orchestrator skill: .claude/skills/earnings-orchestrator/SKILL.md
  - Top-level (no fork), so Task tool is available.
  - Gets E1/E2 via scripts/earnings/get_earnings.py and uses caches in earnings-analysis/news_processed.csv and earnings-analysis/guidance_processed.csv.
- Discovery:
  - News: scripts/earnings/get_significant_moves.py (significant moves only).
  - Guidance: get_8k/10k/10q/transcript/guidance_news_range.py -> unified list of content sources.
- Extraction:
  - Guidance: Task subagents with guidance-extract reading Neo4j via MCP, returning 18-field pipe lines.
  - News attribution: news-driver-* agents if there are significant moves.
- Thinking hooks:
  - .claude/hooks/build-thinking-on-complete.sh expects ORCHESTRATOR_COMPLETE <TICKER> to build thinking files.

## Why The 2026-02-01 Run Produced No news.csv And Less Guidance

- No news.csv: Q1/Q2 both returned OK|NO_MOVES from get_significant_moves.py (thresholds are 4% stock / 3% adj / 2x vol). Per the skill, that skips news attribution entirely, so earnings-analysis/Companies/AAPL/news.csv stays empty for those quarters.
- Q1 guidance was found but not persisted: Subagent logs contain valid guidance lines (e.g., bzNews_29585294, bzNews_29585292), but the orchestrator did not collect them.
  - Evidence:
    - /home/faisal/.claude/projects/-home-faisal-EventMarketDB/01ea6143-ee1c-490d-b558-edd10d4fe078/subagents/agent-ad3a153.jsonl
    - /home/faisal/.claude/projects/-home-faisal-EventMarketDB/01ea6143-ee1c-490d-b558-edd10d4fe078/subagents/agent-a29dfe9.jsonl (prepends extra text before the pipe line, likely breaking parsing)
- Many Q2 subagents were launched without a Task ID: Several subagent logs explicitly say "No task ID was provided," so their results were never persisted via TaskUpdate and were lost after compaction.
- Compaction loss: The primary run (/home/faisal/.claude/projects/-home-faisal-EventMarketDB/01ea6143-ee1c-490d-b558-edd10d4fe078.jsonl) shows Q1 guidance existed early, then the orchestrator later concluded "all NO_GUIDANCE," consistent with uncollected task results.
- Cache corruption: earnings-analysis/guidance_processed.csv was updated for Q1/Q2 even though Q1 guidance did not land, so re-runs now skip Q1 by default.
- Hook did not fire: The run echoed ORCHESTRATOR_COMPLETE without ticker, but the hook script expects ORCHESTRATOR_COMPLETE <TICKER>, so thinking files were not rebuilt.
- Policy change vs earlier run: guidance-extract explicitly excludes analyst estimates and requires company guidance in news; that likely excludes items like the MR headset forecasts in the earlier output (analyst/rumor rather than official guidance).

## Concrete Issues (Root Causes)

- Missing Task IDs on subagent prompts -> no TaskUpdate -> results lost.
- Output format violations (extra text in TaskUpdate) -> parser drop.
- No TaskList/TaskGet aggregation pass after batches -> reliance on memory; compaction wipes results.
- Hook expectation mismatch (ORCHESTRATOR_COMPLETE missing ticker).
- Strict "company guidance only" filter vs earlier permissive behavior.

## Proposed Fixes (High-Impact)

1. Always TaskCreate each guidance source and pass TASK_ID=N; never spawn subagents directly.
2. Add a final collection step: TaskList -> TaskGet for all guidance tasks; aggregate from task descriptions only.
3. Enforce strict TaskUpdate formatting (pipe lines only). If needed, add a hook to reject/strip extra text.
4. Fix the completion marker to include ticker (ORCHESTRATOR_COMPLETE AAPL) so the thinking hook triggers.
5. Decide guidance policy: company-only vs include analyst/rumor/supply-chain; update guidance-extract rules accordingly.
6. If you want news.csv even on NO_MOVES, update the orchestrator to write a "no moves" record and still mark news_processed.csv.

## Plan Additions (Why + How, For Next Agents)

### Goal

Maximize throughput while preserving correctness: spawn as early as possible, respect task blocking, and never rely on memory for aggregation.

### Rationale (Why This Order)

- Task tool provides true parallelism in the main context, so we should fan out immediately after discovery.
- Dependencies (BZ -> WEB -> PPX -> JUDGE) require blockedBy wiring before any agent runs; otherwise tasks can start in the wrong tier.
- Guidance tasks are independent and should run immediately to reduce total wall time.
- Compaction and stdout loss make TaskGet the only reliable output source; therefore aggregation must wait for task completion.

### Execution Plan (How To Run Fast Without Background Mode)

1. Create all tasks first.
   - For each significant date, TaskCreate BZ/WEB/PPX/JUDGE with blockedBy set.
   - For each guidance source, TaskCreate GX (no dependencies).
   - Why: ensures dependency graph is correct before any agent runs.

2. Spawn immediately in parallel (foreground).
   - Spawn all BZ tasks + all GX tasks right away.
   - Why: best fan-out; no need to wait for other tiers yet.

3. Cross-tier polling loop (fast path).
   - Every short interval (1-3s), TaskList for pending + unblocked tasks.
   - Spawn WEB/PPX/JUDGE as soon as they become unblocked.
   - Track spawned IDs to avoid duplicates.
   - Why: enables cross-tier parallelism (e.g., JUDGE for date A while WEB for date B).

4. Collect only after completion.
   - When all relevant tasks are completed, TaskGet JUDGE + GX results.
   - Never use memory or stdout for aggregation.
   - Why: avoids compaction loss and missing outputs.

### Invariants (Must Always Hold)

- Every guidance source must have a TASK_ID created before spawning guidance-extract.
- No Task tool call uses run_in_background.
- Caches update only after confirmed CSV writes based on TaskGet results.
- If any GX task has missing/invalid pipe output, stop and do not mark processed.

### Success Criteria

- No missing guidance rows when subagents report valid TaskUpdate.
- No "No task ID provided" in subagent logs.
- Q1/Q2 caches only update after rows written.
- Parallelism achieved without background mode (measured by overlapping task start times).

## Design Options: Task Creation + Compaction Risk

### A) Upfront Tasks (Primary Creates Full Graph)

**What:** Primary agent creates ALL tasks for the quarter (BZ/WEB/PPX/JUDGE + GX) before spawning any agents.

**Pros (Determinism):**
- Primary has a complete task inventory; can verify expected vs completed counts.
- Dependency wiring is correct before any agent runs.
- Easier to resume/retry because all task IDs are known.

**Cons:**
- Larger task list to scan; TaskList can be heavier for big quarters.
- Requires strict subject prefixing to filter only this ticker/quarter.

**Compaction Impact:** Low if aggregation uses TaskGet only and state is externalized (task list + files). Primary does not need memory of intermediate outputs.

### B) BZ-First Chain (BZ Creates WEB/PPX/JUDGE)

**What:** Primary spawns only BZ agents; BZ creates downstream tasks if needed.

**Pros (Speed/Load):**
- Fewer tasks created when BZ is confident (downstream not needed).
- Task list stays smaller.

**Cons (Determinism):**
- Success depends on subagent reliability to create tasks.
- Harder to enforce consistent dependency wiring.
- If BZ skips TaskCreate due to prompt miss or compaction, chain breaks silently.

**Compaction Impact:** Medium. Primary still must reconcile missing tasks and outputs without full inventory.

### C) On-Demand by Primary (Incremental Task Creation)

**What:** Primary creates tasks tier-by-tier as it discovers need.

**Pros:**
- Central control (no subagent TaskCreate).
- Smaller task list initially.

**Cons:**
- Harder to maximize parallelism; cross-tier overlap is weaker.
- More orchestration logic in primary, increasing compaction risk.

**Compaction Impact:** Medium-High. Primary must remember what was created and what remains.

### Recommendation (Given Priorities: Determinism > No Compaction > Speed > Production-Grade)

**Use Option A (Upfront Tasks) + Cross-Tier Polling.**

Reasoning:
- Determinism: full task inventory + explicit completion checks.
- Compaction safety: TaskGet is authoritative; minimal memory needed.
- Speed: cross-tier polling still enables parallelism across dates and tiers.

### Compaction Mitigations (All Options)

- Externalize state: write a task manifest file per run (ticker, quarter, task IDs, counts).
- Keep primary outputs concise: counts only, no long lists in chat.
- Fail fast if any GX task lacks valid pipe output (don’t update caches).
- Run per-quarter sessions if needed (separate runs for 10–15 quarters).

### Production-Grade Checklist

- Deterministic outputs: same inputs -> same rows written (no missing tasks).
- Strict cache update gating (only after confirmed CSV rows).
- Robust task filtering by prefix and quarter.
- Auditable run artifacts: manifest + logs + outputs.

## Reliability Plan (Fail-Closed, Not Silent)

### Reality Check

- 100% reliability is **not achievable** with LLM extraction + external tools.
- The goal is **100% deterministic pipeline behavior** and **no silent loss**.
- If something fails, the run must fail closed and be visible.

### Reliability Targets

1. **No silent drops**: every task must produce an output or the run fails.
2. **Deterministic aggregation**: only TaskGet results are used.
3. **Cache safety**: caches update only after verified outputs are written.
4. **Compaction safety**: state externalized to tasks + manifest.

### Required Changes (Plan, Not Yet Implemented)

1. **Task Manifest**
   - Write a per-quarter manifest file (ticker, quarter, task IDs, expected counts).
   - Source of truth for aggregation and validation.

2. **Validation Gate**
   - After polling completes, TaskGet every expected task.
   - Validate format (18 fields for guidance, 12 for judge).
   - If any missing/invalid -> STOP and do not update caches.

3. **Retry Loop**
   - For any failed tasks, respawn that agent (limited retries).
   - If still failing -> hard stop, no cache update.

4. **Best-effort mode (optional, deterministic)**
   - Write valid rows even if some tasks fail.
   - Record failed task IDs in a retry file.
   - Do NOT update processed caches unless retry list is empty.

4. **Mandatory Task IDs**
   - Never spawn without TASK_ID (guidance + news tiers).
   - Missing TASK_ID = immediate failure.

5. **Session Strategy (Compaction Mitigation)**
   - Run **one quarter per session** when processing 10–15 quarters.
   - Ensures context does not degrade long runs.

### Reliability Guarantees We Can Actually Claim

- **Pipeline correctness**: no missing tasks or partial outputs are marked complete.
- **Auditability**: every output ties back to a task and manifest entry.
- **Recoverability**: rerun is possible from manifest without redoing discovery.

## Intermediary Skill Idea (Can It Work?)

### Proposal

Insert a forked skill between the primary orchestrator and the news/guidance agents to reduce compaction.

### Constraints (Observed + Documented)

- Subagents cannot spawn subagents (Task tool cannot be used inside subagents). citeturn0search0
- Forked skills in this project do not have Task tool access (per Infrastructure.md testing).

### Conclusion

**A forked intermediary skill cannot manage news/guidance agent spawning** because:
- It cannot call Task tool in a forked context.
- Subagents cannot spawn other subagents.

### What Can Work Instead

1. **Keep Task orchestration at top-level** (no fork), but:
   - Externalize state (manifest + TaskGet).
   - Run per-quarter sessions to avoid compaction.

2. **Use forked skills only for short, isolated steps** (e.g., discovery parsing), then return results to the primary for Task spawning.

3. **External orchestration** (script or separate sessions):
   - Run each quarter in its own CLI session.
   - Primary orchestrator remains thin; no large context accumulation.

### Net Takeaway

Intermediary forked skills do **not** solve compaction if they need Task tool. The reliable path is to keep Task orchestration at the top level and minimize context through externalized state + per-quarter runs.

## Next Steps Plan (Foundations First, Tests Before Changes)

### Guiding Principles (Non-Negotiable)

1. **Fail-closed**: no cache updates unless outputs are verified.
2. **Externalized state**: task IDs + expected counts are written to disk (manifest).
3. **TaskGet is authoritative**: never rely on memory or stdout for aggregation.
4. **Parallelism without background mode**: Task tool foreground only.
5. **Test before change**: every design change must be validated by a test.

### Architecture Decision (Baseline)

- **Single top-level orchestrator** remains the control plane (Task tool required).
- **Per-quarter sessions** when running 10–15 quarters (compaction mitigation).
- **News + Guidance run in parallel**, then Prediction, then Attribution.

### Implementation Priorities (Order Matters)

1. **Task Manifest + Validation Gate**
   - Add manifest write/read.
   - Add validation gate before writing CSVs or updating caches.
   - Introduce retry loop for failed tasks (limited retries).

2. **Deterministic Aggregation**
   - Ensure aggregation uses TaskGet only.
   - Enforce TASK_ID requirement everywhere.

3. **Session Strategy**
   - Build a simple runner that executes one quarter per session.
   - Store outputs per quarter; aggregate at the end if needed.

4. **Policy Lock**
   - Decide guidance policy (company-only vs broader).
   - Lock rules to reduce variance in counts across runs.

### Test Plan (Must Pass Before Rollout)

**A. Task Infrastructure Tests**
- TaskCreate → TaskUpdate → TaskGet roundtrip.
- blockedBy unblocks in correct order (BZ → WEB → PPX → JUDGE).
- SKIPPED tasks unblock downstream correctly.

**B. Manifest + Validation Tests**
- Manifest lists all task IDs and expected counts.
- Validation fails if any task missing or invalid format.
- Caches NOT updated on validation failure.
 - Test skill: `test-manifest-gate` (writes manifest + validates TaskGet outputs).

**C. Context Isolation Tests (Run 2026-02-01)**
- Parent/child isolation confirmed (child cannot see parent history or reads).
- Sibling isolation confirmed (no shared context; filesystem only).
- Reports: `earnings-analysis/test-outputs/context-parent-report.txt`, `earnings-analysis/test-outputs/context-child-report.txt`, `earnings-analysis/test-outputs/sibling-a-result.txt`, `earnings-analysis/test-outputs/sibling-b-result.txt`.

**Implication:** Any “middle skill” must not rely on shared context. Only explicit arguments + filesystem persist across contexts.

**C. Aggregation Tests**
- JUDGE results collected only via TaskGet.
- GX results collected only via TaskGet.
- No output written if any GX task missing.

**D. Compaction Safety Tests**
- Simulate compaction by clearing context (new session) and re-run aggregation from manifest.
- Ensure outputs match the original TaskGet data.

**E. Performance Tests**
- Parallel spawn timing: verify near-simultaneous starts.
- End-to-end time for a small quarter (baseline).

### Acceptance Criteria (Go/No-Go)

- 0 missing rows when tasks report valid results.
- No cache entries without corresponding CSV rows.
- Repeat run yields identical outputs (deterministic).
- Each failure is visible and blocks cache updates.

## Run Notes / Observations (Track Issues + Fixes)

### 2026-02-01 AAPL Q1 test (current run)

**Observed issue:** Guidance source count mismatch  
- Log shows "Guidance news: 198", but `wc -l` returned **207**.  
- The full listing command **timed out**, which risks partial task creation.

**Root cause (likely):**
- Timeouts or partial output when listing guidance sources, causing inconsistent counts.

**Impact:**
- Manifest/task list could be incomplete → missing guidance tasks → validation failure or silent gaps.

**Fix (next iteration):**
- Run `get_guidance_news_range.py` once, **save output to a file**, then:
  - Use that file for task creation **and** manifest building.
  - Use the file to compute counts (single source of truth).
- Add guard: if `count != lines_in_file`, STOP.
- Add guard: if listing command times out, STOP and re-run listing.

---

### Prior run issue (2026-02-01 earlier)

**Observed issue:** Processed caches updated without CSV outputs  
- `news_processed.csv` / `guidance_processed.csv` updated despite missing `news.csv` / `guidance.csv`.

**Root cause:**  
- Orchestrator skipped validation + save steps, then edited caches directly.

**Fix implemented:**
- Skill-level PreToolUse guard + validation marker requirement.
- Processed CSVs cannot update unless marker exists and output CSV exists.

---

## Disler Patterns Reference (Research: 2026-02-04)

Research from GitHub user **disler** (IndyDevDan) across 14+ repositories with 5,000+ combined stars. Profile: "Betting the next 10 years of my career on AGENTIC software."

### Key Repositories Analyzed

| Repository | Stars | Focus |
|------------|-------|-------|
| claude-code-hooks-mastery | 2,279 | 13 lifecycle hooks, UV scripts |
| claude-code-hooks-multi-agent-observability | 950 | Real-time monitoring |
| always-on-ai-assistant | 972 | Persistent agent lifecycle |
| multi-agent-postgres-data-analytics | 869 | Conversation flows, orchestration |
| just-prompt | 705 | Multi-provider unified interface |
| infinite-agentic-loop | 507 | Wave-based parallel agents |
| single-file-agents | 423 | Self-contained Python agents |
| claude-code-damage-control | 353 | Defense-in-depth hooks |
| claude-code-is-programmable | 288 | Programmable tool patterns |
| beyond-mcp | 128 | Progressive disclosure skills |

### Directory Structure Pattern (claude-code-hooks-mastery)

```
.claude/
├── hooks/              # Python execution scripts (UV single-file)
│   ├── validators/     # Ruff linting, type checking
│   └── utils/          # TTS, LLM integrations
├── commands/           # Custom slash commands (/prime, /plan_w_team)
├── agents/             # Sub-agent configs (builder, validator, meta-agent)
├── output-styles/      # Response formatting templates
├── status_lines/       # Terminal status displays (9 versions)
└── settings.json       # Permissions, allowed tools
```

### Skill Structure Pattern (beyond-mcp)

```
.claude/skills/{skill-name}/
├── SKILL.md            # Description + triggers (YAML frontmatter)
└── scripts/            # Standalone Python scripts (progressive disclosure)
    ├── status.py
    ├── markets.py
    ├── orderbook.py
    ├── trades.py
    ├── search.py
    ├── events.py
    ├── event.py
    ├── series_list.py
    └── series.py
```

**Key Insight**: Agents load only needed scripts on-demand, reducing token consumption vs loading all tool definitions upfront.

### 13 Lifecycle Hooks (claude-code-hooks-mastery)

| Hook | Type | Purpose | Exit Codes |
|------|------|---------|------------|
| UserPromptSubmit | Control | Intercept/validate prompts before processing | 0=allow, 2=block |
| PreToolUse | Control | Block dangerous commands (rm -rf, .env access) | stderr → Claude |
| PostToolUse | Observational | Validate/transform output, Ruff linting | feedback only |
| Stop | Control | Force continuation, prevent completion | risky for loops |
| SessionStart | Observational | Initialize session, inject context | feedback only |
| SessionEnd | Observational | Cleanup, persist state | feedback only |
| Notification | Observational | Alert on events | feedback only |
| PreCompact | Maintenance | Before context compaction | feedback only |
| Setup | Maintenance | Environment initialization | feedback only |
| PermissionRequest | Control | Audit tool access requests | auto-allow read-only |
| SubagentStop | Observational | Subagent completion | feedback only |
| Error | Observational | Error handling | feedback only |
| PreTaskUpdate | Control | Validate task updates | 0=allow, 2=block |

**Exit Code Protocol:**
- `0` = Success / Allow
- `2` = Block (stderr sent back to Claude automatically)
- Other = Warning shown to user, command proceeds

### Hook Implementation Pattern (UV Single-File Scripts)

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "rich"]
# ///

import sys
import json

def main():
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Validation logic
    if "rm -rf" in tool_input.get("command", ""):
        print("BLOCKED: Destructive command not allowed", file=sys.stderr)
        sys.exit(2)

    # Allow
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Damage Control Pattern (patterns.yaml)

```yaml
# .claude/filters/patterns.yaml
bashToolPatterns:
  - pattern: "rm -rf"
    action: block
    ask: false  # hard block, no confirmation

  - pattern: "DELETE.*WHERE"
    action: ask
    ask: true   # confirmation dialog

zeroAccessPaths:
  - ~/.ssh/
  - ~/.aws/credentials
  - .env

readOnlyPaths:
  - /etc/*
  - ~/.bashrc

noDeletePaths:
  - node_modules/
  - .git/
```

### Three Execution Modes (install-and-maintain)

| Mode | Use Case | Characteristics |
|------|----------|-----------------|
| **Deterministic** | CI/CD pipelines | Fast, predictable, identical every time |
| **Agentic** | Failed setups | Agent analyzes logs, reports status |
| **Interactive** | New engineers | Asks clarifying questions mid-workflow |

**Core Principle**: "The script is the source of truth." Both hooks and prompts execute identical underlying scripts.

### Agent Configuration Pattern (nano-agent)

**Nested Two-Layer Architecture:**
```
Outer Agent (MCP client)
    │
    │ MCP Protocol
    ▼
Inner Agent (spawned per request)
    │
    │ 20 turns max
    ▼
File Tools (read, write, edit, list, get_info)
```

**Agent configs in `.claude/agents/`:**
- 3 OpenAI tiers: nano, mini, standard
- 4 Claude variants: Opus 4.1, Sonnet, Haiku
- 2 Ollama models: 20B, 120B

### Single-File Agent Pattern (single-file-agents)

**Structure:**
1. API client initialization
2. System prompt definition
3. Tool/function schema definitions
4. Main agent loop with message history
5. Result formatting and output

**CLI Arguments Standard:**
- `-d` database paths
- `-p` prompts/queries
- `-c` compute loop iterations (prevents infinite loops)
- `-i` input files
- `-o` output destinations

**Environment Variables:**
```bash
GEMINI_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
FIRECRAWL_API_KEY=...
```

### Multi-Agent Coordination (multi-agent-postgres-data-analytics)

**Conversation Flows**: Dictate which agent speaks, order, targets, and content.

**Orchestrator Pattern**: Manages single agent team, conversations, and outputs.

**Instruments**: Reusable tools with state + functions. Agents consume/manipulate state.

**Decision Agents**: Produce concrete decisions for agentic control flow.

### Observability Pattern (claude-code-hooks-multi-agent-observability)

**Event Flow:**
```
Claude Agents → Hook Scripts → HTTP POST → Bun Server → SQLite → WebSocket → Vue Client
```

**Event Types Captured:**
- PreToolUse/PostToolUse (tool execution)
- UserPromptSubmit (input logging)
- SessionStart/SessionEnd (lifecycle)
- Stop/SubagentStop (completion)
- PreCompact (context management)

**Each Event Includes:**
- Timestamps
- Session IDs
- Source application name
- Structured payloads

### Wave-Based Parallelism (infinite-agentic-loop)

**Four Execution Patterns:**
| Pattern | Agents | Use Case |
|---------|--------|----------|
| Single iteration | 1 | One variant generation |
| Small batch | 5 | Simultaneous work |
| Large batch | 20 | 5-agent waves for resource management |
| Infinite mode | ∞ | Continuous until context limits |

### Complete Allowed Tools Reference

**Core Tools (from claude-code-is-programmable):**
| Tool | Purpose |
|------|---------|
| Task | Launch sub-agents |
| Bash | Shell commands |
| Batch | Parallel tool execution |
| Read | Read files |
| Write | Create/overwrite files |
| Edit | Modify files |
| Glob | Pattern matching |
| Grep | Content search |
| LS | Directory listing |
| NotebookRead | Read Jupyter notebooks |
| NotebookEdit | Edit Jupyter notebooks |
| WebFetch | URL content retrieval |
| AskUserQuestion | Interactive clarification |
| TodoWrite | Todo tracking |
| EnterPlanMode | Plan mode |
| ExitPlanMode | Exit plan mode |
| TaskCreate | Create tasks |
| TaskList | List tasks |
| TaskGet | Get task details |
| TaskUpdate | Update task status |
| Skill | Invoke skills |

**MCP Tool Pattern:**
```
mcp__{server}__{tool}
```
Example: `mcp__neo4j-cypher__read_neo4j_cypher`

### Skill YAML Frontmatter Options

```yaml
---
name: skill-name                    # Required: skill identifier
description: "Trigger description"  # Required: auto-discovery trigger
context: fork                       # Optional: isolate from parent context
model: claude-opus-4-5              # Optional: opus/sonnet/haiku
permissionMode: dontAsk             # Optional: skip permission prompts
allowed-tools:                      # Optional: whitelist (exclusive)
  - Tool1
  - Tool2
  - mcp__server__tool
disallowedTools:                    # Optional: blacklist
  - DangerousTool
skills:                             # Optional: nested skill access
  - other-skill-1
  - other-skill-2
---
```

### Disler Skill Template (Recommended)

```yaml
---
name: {skill-name}
description: {1-2 sentence trigger description for auto-discovery}
context: fork
model: claude-opus-4-5
permissionMode: dontAsk
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskGet
  - TaskUpdate
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Skill
  - AskUserQuestion
disallowedTools:
  - {dangerous-tool}
skills:
  - {dependency-skill}
---

# {Skill Name}

**Goal**: {Single sentence objective}

**Thinking**: ALWAYS use `ultrathink` for {use case}.

---

## Triggers

Invoke when user asks about:
- {trigger phrase 1}
- {trigger phrase 2}

---

## Workflow ({N} Steps)

### Step 1: {Name}
{Description}

### Step 2: {Name}
{Description}

---

## Scripts

Available in `./scripts/`:
- `{script1}.py` - {purpose}
- `{script2}.py` - {purpose}

---

## Output

**File**: `{output_path}`
**Format**: {format description}

---

*Version {X.Y} | {Date} | {Change description}*
```

### Agent Definition Template (.claude/agents/*.md)

```yaml
---
name: {agent-name}
description: "{Trigger description for Task tool discovery}"
tools:
  - mcp__{server}__{tool}
disallowedTools:
  - mcp__{server}__{dangerous_tool}
model: opus                         # opus/sonnet/haiku
permissionMode: dontAsk
skills:
  - {skill-1}
  - {skill-2}
---

# {Agent Name}

{Brief description of what this agent does.}

## Workflow
1. {Step 1}
2. {Step 2}
3. {Step 3}

## Notes
- {Important constraint or behavior}
- {Data format expectation}
```

### Key Disler Principles

1. **"Script is the source of truth"**
   - Both hooks and prompts execute the same underlying scripts
   - Deterministic behavior in CI, agentic supervision for failures

2. **Progressive Disclosure**
   - Load only needed scripts/tools to save tokens
   - Skills expose scripts on-demand, not all at once

3. **Layered Defense**
   - PreToolUse hooks validate before execution
   - Exit code 2 blocks with stderr feedback to Claude
   - Multiple validation layers (prompt → tool → permission)

4. **Observability Built-In**
   - JSON logging for all events
   - Session-based tracking with color coding
   - WebSocket real-time monitoring option

5. **Exit Code Protocol**
   - 0 = allow
   - 2 = block (stderr → Claude)
   - other = warning, proceed

6. **Multi-Mode Support**
   - Deterministic for CI/CD
   - Agentic for complex failures
   - Interactive for humans needing guidance

7. **Agent Specialization**
   - Different model configs for different task types
   - Builder vs Validator pattern (implementation vs review)
   - Meta-agents that create other agents dynamically

8. **State Externalization**
   - Scratchpad files for persistent memory
   - Manifest files for task inventory
   - Never rely on context for aggregation

### Applicable Improvements for earnings-orchestrator

| Current State | Disler Pattern | Recommendation |
|---------------|----------------|----------------|
| Inline queries in SKILL.md | `scripts/` directory | Extract to standalone Python scripts |
| Basic hooks | 13 lifecycle hooks | Add PreToolUse validators for PIT |
| Manual task tracking | Manifest files | Write task manifest per run |
| Context-based aggregation | TaskGet only | Never use memory for aggregation |
| Single permission mode | patterns.yaml | Add blocklist for dangerous queries |
| No observability | JSON event logging | Add PostToolUse logging hook |
| One model config | Model variants | Consider haiku for fast tasks |

### Proposed Scripts Directory for earnings-orchestrator

```
.claude/skills/earnings-orchestrator/
├── SKILL.md
├── QUERIES.md
└── scripts/
    ├── validate_pit.py       # PIT date validation
    ├── calculate_surprise.py # Surprise calculation formulas
    ├── format_output.py      # Standardized output formatting
    ├── fetch_consensus.py    # Consensus estimate fetching
    ├── write_manifest.py     # Task manifest management
    ├── validate_manifest.py  # Manifest validation gate
    └── aggregate_results.py  # TaskGet-based aggregation
```

### Proposed Hooks for earnings-orchestrator

```
.claude/hooks/earnings/
├── pre_tool_use_pit.py       # Block future-dated queries in prediction
├── pre_tool_use_cache.py     # Block cache updates without marker
├── post_tool_use_log.py      # JSON logging for all tool calls
└── stop_validation.py        # Prevent completion without validation
```

### Example: pre_tool_use_pit.py

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import sys
import json
import os

def main():
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only check in prediction context
    context = os.environ.get("EARNINGS_CONTEXT", "")
    if context != "prediction":
        sys.exit(0)

    # Block return data queries in prediction mode
    query = tool_input.get("query", "") or tool_input.get("command", "")
    forbidden = ["daily_stock", "hourly_stock", "daily_return", "hourly_return"]

    for pattern in forbidden:
        if pattern.lower() in query.lower():
            print(f"BLOCKED: Cannot query {pattern} in prediction mode (future leakage)", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Example: patterns.yaml for earnings

```yaml
# .claude/filters/earnings_patterns.yaml

# Queries that leak future information in prediction mode
prediction_blocked:
  - pattern: "daily_stock"
    context: prediction
    action: block
    reason: "Return data is what we're predicting"

  - pattern: "hourly_stock"
    context: prediction
    action: block
    reason: "Return data is what we're predicting"

  - pattern: "WHERE.*created.*>.*filing_datetime"
    context: prediction
    action: block
    reason: "Post-filing data not allowed"

# Cache protection
cache_protected:
  - path: "earnings-analysis/*_processed.csv"
    requires_marker: true
    marker_file: ".validation_complete"

# Always blocked
always_blocked:
  - pattern: "DROP|TRUNCATE|DELETE"
    action: block
    reason: "Destructive database operations"
```

### Multi-Provider Pattern (just-prompt)

For potential future use with multi-model comparison:

**Provider Prefixes:**
- `o` or `openai` → OpenAI models
- `a` or `anthropic` → Anthropic Claude
- `g` or `gemini` → Google Gemini
- `q` or `groq` → Groq
- `d` or `deepseek` → DeepSeek
- `l` or `ollama` → Ollama

**CEO and Board Pattern:**
Send prompt to multiple "board member" models, have "CEO" model make decision based on responses. Useful for consensus or comparative analysis.

---

## Summary: What To Borrow from Disler

1. **Immediate**: Add `scripts/` directory to skills for progressive disclosure
2. **Immediate**: Expand allowed-tools list with Glob, Grep, AskUserQuestion
3. **Short-term**: Add PreToolUse hooks for PIT validation and cache protection
4. **Short-term**: Implement patterns.yaml for blocklist management
5. **Medium-term**: Add JSON event logging for observability
6. **Medium-term**: Create task manifest system for deterministic aggregation
7. **Long-term**: Consider multi-model comparison for consensus validation
