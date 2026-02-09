# Agent Teams Orchestration Plan

## Date: 2026-02-05

---

# Part 1: Quick Reference

## 1.1 What Agent Teams Are

Agent Teams is an **experimental** feature that coordinates multiple independent Claude Code sessions working together. One session acts as the team lead, spawning teammates that communicate via peer-to-peer messaging and coordinate via a shared task list.

**Enable**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json env block or shell environment.

**Storage**: `~/.claude/teams/{team-name}/config.json` (team config), `~/.claude/tasks/{team-name}/` (shared tasks).

## 1.2 Architecture

```
Team Lead (main Claude Code session)
    │
    ├── Teammate A (independent Claude Code instance)
    │       ├── Own context window
    │       ├── Loads CLAUDE.md, MCP, skills independently
    │       ├── Can message Lead, B, C directly
    │       └── Claims tasks from shared task list
    │
    ├── Teammate B (independent Claude Code instance)
    │       └── Same capabilities as A
    │
    └── Teammate C (independent Claude Code instance)
            └── Same capabilities as C

Shared: Task list, Mailbox (message routing), Filesystem
NOT shared: Conversation history, context window contents
```

## 1.3 Teams vs Sub-Agents vs Skills (Side-by-Side)

| Aspect | Sub-Agents (Task tool) | Skills (context: fork) | Agent Teams |
|--------|----------------------|----------------------|-------------|
| **Context** | Own window, results return to caller | Own window, results return to caller | Own window, **fully independent** |
| **Communication** | Report back to parent ONLY | Return value to parent ONLY | **Peer-to-peer messaging** |
| **Coordination** | Parent manages all work | Parent manages all work | **Shared task list + self-coordination** |
| **Nesting** | Cannot spawn sub-agents | Cannot use Task tool | **Cannot spawn nested teams** |
| **Parallelism** | YES (multiple Task calls in one message) | NO (sequential only) | YES (teammates work concurrently) |
| **Display** | Invisible to user | Invisible to user | **In-process or split-pane** (tmux/iTerm2) |
| **Token cost** | Medium (summarized back) | Medium (summarized back) | **~7x higher** (each = full session) |
| **MCP access** | Inherits, but background mode loses tools | Pre-load via allowed-tools | Each loads independently |
| **Lifecycle** | Spawned → completes → returns | Invoked → completes → returns | Spawned → runs independently → shutdown request |
| **User interaction** | None (automated) | None (automated) | **Direct messaging** (Shift+Up/Down or split pane) |
| **Tested in Infrastructure.md** | Extensively (Part 10) | Extensively (Parts 3, 9) | **Extensively (this doc, 31 capabilities)** |

## 1.4 Key Components

| Component | Purpose | How It Works |
|-----------|---------|--------------|
| **Team Lead** | Creates team, spawns teammates, coordinates, synthesizes | Main Claude Code session; cannot be transferred |
| **Teammates** | Independent workers, each with own context | Separate Claude Code instances; load CLAUDE.md, MCP, skills |
| **Shared Task List** | Coordinate work across team | Same `~/.claude/tasks/{team-name}/` system from Part 10 of Infrastructure.md |
| **Mailbox** | Peer-to-peer messaging | Automatic delivery, no polling needed |
| **Delegate Mode** | Restrict lead to coordination only | Press Shift+Tab; prevents lead from implementing |
| **Plan Approval** | Gate teammate implementation | Teammate plans in read-only, lead approves/rejects |

## 1.5 Environment Variables

| Variable | Purpose | Set By |
|----------|---------|--------|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Enable teams (set to `1`) | User (settings.json or shell) |
| `CLAUDE_CODE_TEAM_NAME` | Name of the team this teammate belongs to | Auto-set by Claude Code on teammates |
| `CLAUDE_CODE_PLAN_MODE_REQUIRED` | Teammate requires plan approval | Auto-set when lead requests plan approval |
| `CLAUDE_CODE_TASK_LIST_ID` | Share task list across sessions | User (settings.json or shell) |
| `CLAUDE_CODE_ENABLE_TASKS` | Enable task tools | User (settings.json or shell) |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Disable background functionality | User |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Override subagent model | User |

## 1.6 Display Modes

| Mode | How | Requirements |
|------|-----|--------------|
| `in-process` | Teammates run inside main terminal; Shift+Up/Down to navigate | Any terminal |
| `tmux` | Each teammate gets own pane | tmux installed |
| `auto` (default) | Split panes if in tmux/iTerm2, else in-process | Auto-detected |

Configure: `"teammateMode": "in-process"` in settings.json, or `--teammate-mode in-process` CLI flag.

## 1.7 Permissions

- Teammates inherit lead's permission settings at spawn
- If lead uses `--dangerously-skip-permissions`, all teammates do too
- Can change individual teammate modes AFTER spawning
- Cannot set per-teammate modes AT spawn time
- `delegate` permission mode: coordination-only tools (new, teams-specific)

---

# Part 2: Team Lifecycle

## 2.1 Creating a Team

Two paths:
1. **User requests**: "Create an agent team with 3 teammates to..."
2. **Claude proposes**: Claude suggests a team, user confirms

Claude won't create a team without user approval.

## 2.2 Spawning Teammates

- Natural language: "Create a team with 4 teammates..."
- Model selection: "Use Sonnet for each teammate"
- Plan approval: "Require plan approval before they make changes"
- Each teammate loads: CLAUDE.md, MCP servers, skills, spawn prompt (NOT lead's conversation history)

## 2.3 Communication

| Method | Target | Use Case |
|--------|--------|----------|
| `message` | One specific teammate | Direct instructions, follow-up questions |
| `broadcast` | All teammates | Team-wide updates (use sparingly — costs scale) |
| Automatic idle notification | Lead | When teammate finishes and stops |
| Shared task list | All agents | Task status, claiming, dependency tracking |

## 2.4 Task Claiming

- Lead creates tasks and assigns, OR teammates self-claim
- File locking prevents race conditions on concurrent claims
- Three states: pending, in_progress, completed
- Dependencies: blocked tasks can't be claimed until dependencies resolve

## 2.5 Teammate Shutdown

- Lead sends shutdown request: "Ask the researcher teammate to shut down"
- Teammate can approve (exits gracefully) or reject with explanation
- Shutdown can be slow (waits for current turn to complete)

## 2.6 Team Cleanup

- Lead runs cleanup: "Clean up the team"
- Checks for active teammates — fails if any still running
- Removes shared team resources
- **WARNING**: Only lead should run cleanup (teammates may leave resources inconsistent)

## 2.7 Orphan Handling

If tmux session persists after team ends:
```bash
tmux ls
tmux kill-session -t <session-name>
```

---

# Part 3: Known Limitations (from docs)

| Limitation | Detail | Workaround |
|------------|--------|------------|
| No session resumption with in-process teammates | `/resume` and `/rewind` don't restore teammates | Lead spawns new teammates after resume |
| Task status can lag | Teammates forget to mark tasks complete | Check manually, nudge teammate |
| Shutdown can be slow | Waits for current request/tool call | Be patient or force-kill |
| One team per session-hierarchy | Can't manage multiple teams. Constraint binds entire session (primary + all subagents). | Clean up before starting new team. Two separate `claude -p` processes for parallel teams. **Confirmed RT-12.** |
| No nested teams | Teammates cannot spawn their own teams | Use sub-agents within teammates instead |
| Lead must be primary agent | Subagents can TeamCreate but lack Task tool to spawn teammates. Only the primary can run a full team lifecycle. | Always create teams from the primary session. **Confirmed RT-12 Test D.** |
| Lead is fixed | Can't promote teammate or transfer leadership | Design lead role carefully upfront |
| Permissions set at spawn | All teammates inherit lead's mode | Change individually after spawning |
| Split panes require tmux/iTerm2 | Not supported in VS Code terminal, Windows Terminal, Ghostty | Use in-process mode |

---

# Part 4: Unknowns To Test

## 4.1 Teams + Sub-Agents Combination

**Question**: Can a teammate use the Task tool to spawn sub-agents?

**Why it matters**: If teammates CAN spawn sub-agents, we get two levels of parallelism:
```
Lead → spawns Teammates (parallel, independent)
  └── Teammate → spawns Sub-agents (parallel, within teammate's session)
```

This would be huge for the earnings architecture — a teammate could be the orchestrator that spawns parallel news-driver sub-agents.

**What to test**:
- [x] Can teammate call Task tool? **NO — Task tool entirely absent from teammate toolset**
- [x] Can teammate spawn foreground sub-agents? **NO — impossible without Task tool**
- [x] Can teammate spawn background sub-agents? **NO — impossible without Task tool**
- [ ] ~~Do sub-agents spawned by teammate have full tool access?~~ N/A
- [ ] ~~Can sub-agents see the team's shared task list?~~ N/A

**Status**: TESTED — Sub-agents from teammates NOT possible. Workaround: Skills with `context: fork`

---

## 4.2 Teams + Shared Task List (`CLAUDE_CODE_TASK_LIST_ID`)

**Question**: Does our existing `CLAUDE_CODE_TASK_LIST_ID=eventmarketdb-tasks` work with teams, or do teams use their own task list?

**Why it matters**: If teams use their own list, we need to understand how it interacts with our existing task persistence setup.

**What to test**:
- [x] Does `CLAUDE_CODE_TASK_LIST_ID` propagate to teammates? **YES — teammates use same list as lead**
- [x] Do teammates see tasks created by the lead? **YES — cross-visibility confirmed**
- [x] Do teammates see tasks created by other teammates? **YES — shared task IDs**
- [x] Can teammates use TaskCreate/TaskList/TaskGet/TaskUpdate? **YES — all four work**
- [x] Does the team task list persist across sessions? **Config persists on disk, but teammates cannot be resumed (per docs)**
- [x] What happens if `CLAUDE_CODE_TASK_LIST_ID` is set AND a team is created — conflict? **NO CONFLICT — team gets own internal dir, work tasks go to configured list**
- [x] Do task dependencies (addBlockedBy) work between teammates? **YES — blocked task unblocks when blocker completes**

**Status**: FULLY TESTED

---

## 4.3 Teams + MCP Tools

**Question**: Do teammates get MCP access (Neo4j, Perplexity, AlphaVantage)?

**Why it matters**: If teammates can't access MCP, they can't query Neo4j or search Perplexity, making them useless for earnings analysis.

**What to test**:
- [x] Do teammates load MCP servers from `.mcp.json`? **YES — all three providers visible as deferred**
- [x] Can teammates use `mcp__neo4j-cypher__read_neo4j_cypher` directly? **YES — queried AAPL successfully**
- [x] Does ToolSearch/MCPSearch work for teammates? **YES — loaded both neo4j and perplexity**
- [x] Can teammates use `mcp__perplexity__perplexity_search`? **YES — perplexity_ask worked with citations**
- [x] Do MCP tools work if pre-loaded via skill `allowed-tools`? **NO — MCP remains deferred, ToolSearch always required**

**Status**: FULLY TESTED — MCP access works via ToolSearch; pre-load does NOT work

---

## 4.4 Teams + Skills (context: fork)

**Question**: Can teammates invoke forked skills?

**Why it matters**: Our entire earnings architecture uses skills with `context: fork` for context isolation. If teammates can invoke these skills, teams become a natural orchestration layer.

**What to test**:
- [x] Can a teammate invoke a forked skill? **YES — test-re-arguments and test-re-model-field both worked**
- [x] Can a teammate invoke a complex forked skill chain? **YES — test-re-workflow (parent→child→parent continues) fully worked**
- [x] Does the skill's `context: fork` create a sub-agent within the teammate? **YES — skills ran in forked mode**
- [x] Do skills with `allowed-tools` for MCP pre-loading work in teammates? **NO — MCP stays deferred**
- [ ] Can a teammate invoke multiple skills sequentially?

**Status**: MOSTLY TESTED — Single and multi-layer skill chains work. MCP pre-load does not.

---

## 4.5 Teams + OpenAI/Gemini (`./agent`)

**Question**: Can teammates use the `./agent` script to call OpenAI/Gemini providers?

**Why it matters**: Our architecture supports provider swappability via `./agent`. If teammates can call Bash, they can call `./agent`.

**What to test**:
- [x] Can teammate run `./agent -p "test" --provider openai`? **YES — returned correct answer ("Tokyo")**
- [ ] Can teammate run `./agent -p "test" --provider gemini`?
- [x] Does Bash tool work for teammates? (prerequisite) **YES**
- [x] Does cross-provider peer messaging work? **YES — bidirectional, multi-round**
- [x] Does cross-provider shared task list work? **YES — both claimed/completed tasks**
- [x] Is there a native `provider` param on Task tool? **NO — only `model: sonnet|opus|haiku`**

**Status**: TESTED — OpenAI works via proxy pattern (see RT-10). Gemini untested but expected to work identically.

---

## 4.6 Delegate Mode Behavior

**Question**: What exactly happens when delegate mode is active? Which tools does the lead retain?

**What to test**:
- [ ] Which tools are available in delegate mode?
- [ ] Can lead still use TaskCreate/TaskList?
- [ ] Can lead read files? (Read tool)
- [ ] Can lead use Bash?
- [ ] Can lead invoke skills?
- [ ] Does delegate mode prevent lead from editing files?

**Status**: UNTESTED

---

## 4.7 Plan Approval Workflow

**Question**: How does plan approval work in practice? Can we automate approval criteria?

**What to test**:
- [x] Does "Require plan approval" actually gate implementation? **YES — mode: "plan" is enforced (soft), teammate enters plan mode**
- [ ] Can we set approval criteria in the prompt?
- [x] How does the lead communicate approval/rejection? **SendMessage type: plan_approval_response with approve: true/false**
- [ ] Can the user override the lead's approval decision?
- [ ] What happens if lead approves but teammate's plan is wrong?

**Status**: PARTIALLY TESTED — Core workflow works (plan → ExitPlanMode → lead approve/reject → continue)

---

## 4.8 Team + Earnings Architecture Integration

**Question**: Can we replace or augment our current orchestrator pattern with Agent Teams?

**Current architecture** (from Infrastructure.md Part 2):
```
Layer 0: Main Conversation
    └── Layer 1: /earnings-orchestrator (context: fork)
            ├── Layer 2: /earnings-prediction (context: fork)
            │       └── Layer 2.5: /filtered-data (context: fork)
            └── Layer 2: /earnings-attribution (context: fork)
```

**Potential team architecture**:
```
Team Lead (orchestrator role)
    ├── Teammate: Prediction
    │       ├── Invokes /filtered-data skill
    │       └── Queries Neo4j via MCP
    ├── Teammate: Attribution
    │       ├── Queries Neo4j directly
    │       └── Searches Perplexity
    └── Teammate: Judge (waits for both, synthesizes)
            └── Reads files written by Prediction and Attribution
```

**Key advantages if this works**:
- True parallelism (Prediction and Attribution run simultaneously)
- Peer messaging (Attribution can ask Prediction clarifying questions)
- Shared task list coordination (no file-based polling)
- Each teammate has full context window (no compaction pressure)

**Key risks**:
- 7x token cost
- Teammates can't inherit conversation history (need detailed spawn prompts)
- No nested teams (can't have sub-teams)
- Experimental feature — may have undiscovered bugs

**What to test**:
- [ ] Can Prediction teammate invoke /filtered-data skill?
- [ ] Can Attribution teammate query Neo4j via MCP?
- [ ] Can Judge teammate read files written by other teammates?
- [ ] Does messaging work for coordinating handoff?
- [ ] Is the token cost acceptable for our use case?

**Status**: UNTESTED

---

## 4.9 New Subagent Features (Not Teams — But New Since Infrastructure.md)

These were discovered while researching Agent Teams docs. They are new subagent/skill features that need testing independently of teams.

### 4.9.1 Persistent Memory for Subagents

**Feature**: `memory` field in subagent frontmatter — `user`, `project`, or `local` scope.

**What it does**: Gives subagent a persistent directory to write notes across conversations. Documentation claims auto-loaded `MEMORY.md` (first 200 lines) in system prompt — **but auto-preload does NOT work as of v2.1.34**.

**Storage locations**:
| Scope | Location | Tested |
|-------|----------|--------|
| `user` | `~/.claude/agent-memory/<agent-name>/` | Not tested |
| `project` | `.claude/agent-memory/<agent-name>/` | ✅ Tested |
| `local` | `.claude/agent-memory-local/<agent-name>/` | ✅ Tested |

**Test results (v2.1.34, 2026-02-06)**:
- [x] Does `memory: project` create the directory? **YES** — dir created at `.claude/agent-memory/<name>/`
- [x] Does `memory: local` create the directory? **YES** — dir created at `.claude/agent-memory-local/<name>/`
- [x] Can subagent write/read from memory directory? **YES** — Write + Read both work
- [x] Does memory persist across sessions? **YES** — files survive restarts
- [x] Does MEMORY.md auto-load on next invocation? **NO — CONFIRMED NOT WORKING**

**Definitive auto-preload test** (4 separate tests):
1. `test-memory-local` agent wrote `MEMORY_LOCAL_TEST=mango_2026_local` to MEMORY.md → restarted → re-ran same agent → agent reports NO memory content in system prompt
2. `test-re-memory-agent` agent wrote `MEMORY_TEST_VALUE=banana_2026` to MEMORY.md → restarted → re-ran same agent → agent reports NO memory content in system prompt
3. Both agents explicitly searched entire system prompt for the memory strings → zero matches
4. Both `local` and `project` scopes behave identically: storage works, recall doesn't

**Status**: ⚠️ **STORAGE ONLY** — Dir + files persist; auto-preload into system prompt does NOT work.

**Workaround**: Agent manually `Read`s its memory dir at startup. This actually gives more control (per-company files, selective loading, no 200-line limit):
```yaml
# Agent frontmatter:
memory: local
```
```
# Agent prompt instructions:
At startup, check .claude/agent-memory-local/<agent-name>/ for relevant files.
Read them for prior context. When done, write updated findings back.
```

---

### 4.9.2 Skills Preloading in Subagents

**Feature**: `skills` field in subagent frontmatter — preload skill content at startup.

```yaml
# .claude/agents/api-developer.md
---
name: api-developer
skills:
  - api-conventions
  - error-handling-patterns
---
```

**Key distinction**: Full skill content is INJECTED at startup (not on-demand). Subagents don't inherit skills from parent — must list explicitly.

**What to test**:
- [ ] Does `skills: [neo4j-schema]` preload the schema skill?
- [ ] Does preloaded skill content appear in subagent's context?
- [ ] Can subagent use preloaded skill knowledge without invoking it?
- [ ] What's the context cost of preloading vs on-demand?

**Status**: UNTESTED

---

### 4.9.3 `disallowedTools` Enforcement (Retest)

**Infrastructure.md finding** (Jan 2026): `disallowedTools` was NOT ENFORCED for skills.

**Current docs**: `disallowedTools` is listed as a working field for subagents: "Tools to deny, removed from inherited or specified list."

**What to test**:
- [ ] Does `disallowedTools: [Write, Edit]` prevent subagent from writing?
- [ ] Does `disallowedTools: [Bash]` prevent subagent from running commands?
- [ ] Is enforcement different for subagents vs skills?

**Status**: NEEDS RETEST — may have been fixed since Jan 2026

---

### 4.9.4 SubagentStart / SubagentStop Hook Events

**Feature**: New hook events in settings.json (not skill frontmatter) that fire when subagents start/stop.

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/setup-db.sh" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/cleanup.sh" }
        ]
      }
    ]
  }
}
```

**What to test**:
- [x] Does SubagentStart fire when a custom subagent starts? **YES** (tested in Infrastructure.md)
- [ ] Does the matcher filter by agent name correctly?
- [x] Does SubagentStop fire when subagent completes? **YES** (tested in Infrastructure.md)
- [ ] Can we use these to set up/tear down resources per agent?

**Status**: TESTED (basic lifecycle — see Infrastructure.md retest 2026-02-05)

### 4.9.5 TaskCompleted Hook Event (v2.1.33 — NEW)

**Feature**: New `TaskCompleted` hook event fires when any task status transitions to `completed`.

**Test results (v2.1.34, 2026-02-06)**:
- [x] Does TaskCompleted fire when a task is marked completed? **YES**
- [x] What data does the hook receive? **JSON via STDIN**

**Hook STDIN schema** (actual from test):
```json
{
  "session_id": "95629380-...",
  "transcript_path": "/home/faisal/.claude/projects/.../95629380-....jsonl",
  "cwd": "/home/faisal/EventMarketDB",
  "hook_event_name": "TaskCompleted",
  "task_id": "3051",
  "task_subject": "DUMMY_TASK_FOR_HOOK_TEST",
  "task_description": "This task exists solely to test the TaskCompleted hook."
}
```

**Environment variables propagated**: `CLAUDE_CODE_ENABLE_TASKS`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CODE_TASK_LIST_ID`, `CLAUDE_PROJECT_DIR`, `CLAUDE_CODE_ENTRYPOINT`

**Configuration**:
```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/on-task-complete.sh" }
        ]
      }
    ]
  }
}
```

**Status**: ✅ **WORKS** — fires reliably, rich JSON payload

### 4.9.6 TeammateIdle Hook Event (v2.1.33 — NEW)

**Feature**: New `TeammateIdle` hook event fires when a teammate's turn ends and it goes idle.

**Test results (v2.1.34, 2026-02-06)**:
- [x] Does TeammateIdle fire when a teammate goes idle? **YES**
- [x] What data does the hook receive? **JSON via STDIN**

**Hook STDIN schema** (actual from test):
```json
{
  "session_id": "95629380-...",
  "transcript_path": "/home/faisal/.claude/projects/.../95629380-....jsonl",
  "cwd": "/home/faisal/EventMarketDB",
  "permission_mode": "default",
  "hook_event_name": "TeammateIdle",
  "teammate_name": "idle-worker",
  "team_name": "test-hooks-2133"
}
```

**Environment variables propagated**: Same as TaskCompleted

**Configuration**:
```json
{
  "hooks": {
    "TeammateIdle": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/on-teammate-idle.sh" }
        ]
      }
    ]
  }
}
```

**Use cases**:
- Auto-assign next task when teammate goes idle
- Log teammate activity for cost tracking
- Trigger external notification (Slack, webhook)

**Status**: ✅ **WORKS** — fires reliably, includes teammate_name and team_name

### 4.9.7 Agent `Task(AgentType)` Restriction (v2.1.33 — NEW)

**Feature**: In agent frontmatter `tools:` field, use `Task(AgentType)` to restrict which sub-agent types can be spawned.

**Test results (v2.1.34, 2026-02-06)**:
- [x] Does `Task(Explore)` in tools allow spawning Explore agents? **YES**
- [x] Does `Task(Bash)` in tools allow spawning Bash agents? **YES**
- [x] Are unlisted types blocked? **YES** — `Task(general-purpose)` and `Task(Plan)` both blocked
- [x] Is enforcement strict? **YES** — agent type restriction is a hard block, not soft

**Agent frontmatter syntax**:
```yaml
---
name: my-restricted-agent
tools:
  - Read
  - Write
  - Grep
  - Glob
  - Task(Explore)
  - Task(Bash)
---
```

Only `Explore` and `Bash` sub-agents can be spawned. All other `subagent_type` values are blocked.

**Key insight**: This is a **hard enforcement** (unlike delegate mode which is soft). The tool call fails with an error when an unlisted agent type is requested.

**Use cases**:
- Restrict data-gathering agents to only spawn read-only sub-agents (Explore)
- Prevent agents from spawning general-purpose sub-agents that could do anything
- Create sandboxed agent hierarchies

**Status**: ✅ **ENFORCED** — strict whitelist, unlisted types blocked

---

### 4.9.5 New Skill Features

| Feature | What It Does | Test? |
|---------|-------------|-------|
| `disable-model-invocation: true` | Hide skill from Claude's auto-invocation | TEST |
| `user-invocable: false` | Hide from `/` menu, only Claude can invoke | TEST |
| `$ARGUMENTS[N]` / `$N` | Positional argument access | TEST |
| `${CLAUDE_SESSION_ID}` | Session ID substitution in skill content | TEST |
| `!`command`` | Shell command preprocessing before skill loads | TEST |
| `@path` imports | File imports in CLAUDE.md and skills | TEST |
| Auto-compaction for subagents | 95% threshold, configurable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | TEST |

**Status**: ALL UNTESTED

---

# Part 5: Test Plan (Ordered by Priority)

## Phase 1: Enable & Basic Team Operations

| # | Test | Description | Expected Outcome |
|---|------|-------------|-----------------|
| 1 | Enable teams | Add `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to settings.json | Feature available |
| 2 | Create basic team | "Create a team with 2 teammates" | Team created, teammates spawned |
| 3 | Teammate messaging | Lead sends message to teammate | Message received and processed |
| 4 | Teammate task claiming | Create tasks, teammates self-claim | Tasks distributed correctly |
| 5 | Teammate shutdown | "Ask teammate A to shut down" | Graceful shutdown |
| 6 | Team cleanup | "Clean up the team" | Resources removed |

## Phase 2: Teams + Existing Infrastructure

| # | Test | Description | Expected Outcome |
|---|------|-------------|-----------------|
| 7 | Teams + Task List | Test with `CLAUDE_CODE_TASK_LIST_ID` set | Shared or separate? |
| 8 | Teams + MCP | Teammate queries Neo4j | MCP tools accessible |
| 9 | Teams + Skills | Teammate invokes forked skill | Skill executes correctly |
| 10 | Teams + Sub-agents | Teammate spawns Task sub-agent | Sub-agent runs with tools |
| 11 | Teams + Bash/agent | Teammate runs `./agent --provider openai` | External provider works |

## Phase 3: Advanced Team Patterns

| # | Test | Description | Expected Outcome |
|---|------|-------------|-----------------|
| 12 | Delegate mode | Enable delegate mode, verify restrictions | Lead can only coordinate |
| 13 | Plan approval | Require plan approval for teammate | Plan → approve → implement |
| 14 | Multi-teammate coordination | 3+ teammates share findings via messages | Information flows correctly |
| 15 | Teammate + skill chain | Teammate runs multi-layer skill chain | Full chain executes |

## Phase 4: Earnings Architecture with Teams

| # | Test | Description | Expected Outcome |
|---|------|-------------|-----------------|
| 16 | Prediction teammate | Teammate runs earnings-prediction | Prediction file written |
| 17 | Attribution teammate | Teammate runs earnings-attribution | Attribution file written |
| 18 | Team orchestration | Lead coordinates prediction + attribution | Both run in parallel |
| 19 | Judge synthesis | Third teammate synthesizes results | Combined report |

## Phase 5: New Subagent/Skill Features (Independent of Teams)

| # | Test | Description | Expected Outcome |
|---|------|-------------|-----------------|
| 20 | Persistent memory | Subagent with `memory: project` | ⚠️ Storage only — no auto-preload (tested v2.1.34) |
| 21 | Skills preloading | Subagent with `skills: [neo4j-schema]` | Content injected |
| 22 | disallowedTools retest | Subagent with `disallowedTools: [Write]` | ✅ Enforced on agents (tested Feb 2026) |
| 23 | SubagentStart/Stop hooks | Hook fires on subagent lifecycle | ✅ Works (tested Feb 2026) |
| 28 | TaskCompleted hook | Hook fires on task completion | ✅ Works (tested v2.1.34) |
| 29 | TeammateIdle hook | Hook fires when teammate goes idle | ✅ Works (tested v2.1.34) |
| 30 | Agent Task(AgentType) restrict | tools: [Task(Explore)] blocks others | ✅ Hard enforcement (tested v2.1.34) |
| 24 | disable-model-invocation | Skill hidden from Claude | Only manual invocation works |
| 25 | Dynamic context injection | `!`command`` in skill | Command output injected |
| 26 | Positional arguments | `$ARGUMENTS[0]`, `$0` | Correct substitution |
| 27 | Session ID substitution | `${CLAUDE_SESSION_ID}` in skill | ID injected |

---

# Part 6: Configuration Reference

## 6.1 Settings to Enable Teams

Add to `.claude/settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_ENABLE_TASKS": "true",
    "CLAUDE_CODE_TASK_LIST_ID": "eventmarketdb-tasks"
  },
  "teammateMode": "in-process"
}
```

## 6.2 Team Config File Format

Teams are stored at `~/.claude/teams/{team-name}/config.json`:
```json
{
  "members": [
    {
      "name": "prediction-agent",
      "agentId": "abc123",
      "agentType": "teammate"
    },
    {
      "name": "attribution-agent",
      "agentId": "def456",
      "agentType": "teammate"
    }
  ]
}
```

Teammates can read this file to discover other team members.

## 6.3 Task List Integration

Teams use the same task list system from Infrastructure.md Part 10:
- Tasks stored at `~/.claude/tasks/{team-name}/`
- Same TaskCreate/TaskList/TaskGet/TaskUpdate tools
- File locking for concurrent claim prevention
- Dependencies with addBlockedBy/addBlocks

## 6.4 Communication Protocol

| Action | How | Cost |
|--------|-----|------|
| Message one teammate | `message` | Low (one context) |
| Broadcast to all | `broadcast` | High (N contexts, scales with team size) |
| Idle notification | Automatic | Free (system event) |
| Task status | Shared task list | Free (file-based) |

---

# Part 7: Design Patterns for Earnings

## 7.1 Pattern A: Teams as Top-Level Orchestrator

```
User → "Analyze AAPL earnings for Q1 2024"
    │
    └── Team Lead (orchestrator)
            │
            ├── Teammate: Prediction
            │   - Spawn prompt includes all PIT data instructions
            │   - Invokes /filtered-data, /neo4j-report skills
            │   - Writes prediction to predictions.csv
            │   - Messages Lead when done
            │
            ├── Teammate: Attribution
            │   - Spawn prompt includes post-hoc data instructions
            │   - Queries Neo4j for news, transcripts
            │   - Writes attribution to Companies/{ticker}/
            │   - Messages Lead when done
            │
            └── Lead synthesizes:
                - Reads prediction file
                - Reads attribution file
                - Compares prediction vs actual
                - Writes final report
```

**Pros**: True parallelism, each teammate has full context window, can communicate.
**Cons**: 7x token cost, detailed spawn prompts needed, experimental.

## 7.2 Pattern B: Teams + Sub-Agents Hybrid

```
User → "Analyze AAPL earnings for Q1 2024"
    │
    └── Team Lead (orchestrator)
            │
            ├── Teammate: Data Gatherer
            │   - Spawns sub-agents for parallel Neo4j queries
            │   - Task: neo4j-report for 8-K data
            │   - Task: neo4j-news for news
            │   - Task: neo4j-transcript for earnings calls
            │   - Writes consolidated data files
            │   - Messages Lead when done
            │
            ├── Teammate: Prediction Analyst
            │   - Waits for Data Gatherer (task dependency)
            │   - Reads PIT-filtered data files
            │   - Thinks deeply about prediction
            │   - Writes prediction
            │
            └── Teammate: Attribution Analyst
                - Waits for Data Gatherer (task dependency)
                - Reads all data files (including post-hoc)
                - Analyzes why stock moved
                - Writes attribution
```

**Pros**: Sub-agents handle I/O-heavy queries, teammates handle analysis, maximum parallelism.
**Cons**: Most complex, requires teams + sub-agents both working, highest token cost.

**STATUS: RULED OUT** — Task tool is NOT available to teammates. Cannot spawn sub-agents from within a teammate. Workaround: use Skills with `context: fork` instead (tested: works).

## 7.3 Pattern C: Lightweight Teams (Research Only)

```
User → "Research what drove AAPL stock after Q1 2024 earnings"
    │
    └── Team Lead
            │
            ├── Teammate: Neo4j Researcher
            │   - Queries 8-K, news, transcripts from Neo4j
            │   - Writes findings to file
            │
            ├── Teammate: Web Researcher
            │   - Searches Perplexity for analyst commentary
            │   - Writes findings to file
            │
            └── Teammate: Devil's Advocate
                - Reads both researchers' files
                - Challenges their conclusions
                - Identifies gaps
                - Reports back to Lead
```

**Pros**: Clean separation of concerns, devil's advocate improves quality.
**Cons**: Still 4x token cost vs single agent.

---

# Part 8: Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Experimental feature instability | High | Test thoroughly before production use |
| 7x token cost | Medium | Use Sonnet for teammates, keep teams small |
| No session resumption for teammates | Medium | Design for single-session completion |
| Task status lag | Low | Add mandatory task update instructions |
| MCP tools might not load for teammates | High | Test in Phase 2, have fallback to sub-agents |
| Skills might not work in teammates | High | Test in Phase 2, have fallback to direct instructions |
| Teammates can't spawn sub-agents | High | Test in Phase 2, determines hybrid pattern viability |
| Lead shuts down before work done | Medium | Use delegate mode, explicit "wait for all" instruction |

---

# Part 9: Test Results Log (Tested 2026-02-05)

## 9.1 Phase 1: Basic Team Operations

### Test 1: Enable & Create Team

| Test | Result | Evidence |
|------|--------|----------|
| Enable via settings.json env | **PASS** | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — tools appeared in same session |
| `Teammate(spawnTeam)` | **PASS** | Created `~/.claude/teams/test-basic/config.json` |
| Team task dir auto-created | **YES** | `~/.claude/tasks/test-basic/` created with `.lock` file |

**Config file format** (actual from test):
```json
{
  "name": "test-basic",
  "description": "Basic Agent Teams capability testing",
  "createdAt": 1770326607098,
  "leadAgentId": "team-lead@test-basic",
  "leadSessionId": "cb1f7e40-eaf8-4a6b-8353-472fd91838e7",
  "members": [
    {
      "agentId": "team-lead@test-basic",
      "name": "team-lead",
      "agentType": "team-lead",
      "model": "claude-opus-4-6",
      "joinedAt": 1770326607098,
      "tmuxPaneId": "",
      "cwd": "/home/faisal/EventMarketDB",
      "subscriptions": []
    }
  ]
}
```

**Key details**:
- Agent ID format: `{name}@{team-name}`
- Lead auto-registered as first member
- `tmuxPaneId: ""` in in-process mode
- `cwd` inherited from lead's working directory

### Test 2: Spawn Teammate

| Test | Result | Evidence |
|------|--------|----------|
| `Task(team_name, name, subagent_type)` | **PASS** | Teammate registered in config.json |
| Teammate model inheritance | **INHERITED** | Got `claude-opus-4-6` from lead |
| Spawn prompt stored in config | **YES** | Full prompt visible in `config.json` |
| Teammate runs async (not blocking) | **YES** | Returns immediately, teammate messages when done |
| `backendType` | `in-process` | Running in same terminal |
| Auto-task for teammate | **YES** | `test-basic/1.json` created with `_internal: true`, subject = teammate name |

**Teammate config entry** (actual):
```json
{
  "agentId": "worker-1@test-basic",
  "name": "worker-1",
  "agentType": "general-purpose",
  "model": "claude-opus-4-6",
  "prompt": "(full spawn prompt stored here)",
  "color": "blue",
  "planModeRequired": false,
  "joinedAt": 1770326644494,
  "tmuxPaneId": "in-process",
  "cwd": "/home/faisal/EventMarketDB",
  "subscriptions": [],
  "backendType": "in-process"
}
```

### Test 3: Teammate Tool Inventory

Full tool list reported by teammate (worker-1, general-purpose):

| Tool | Available? | Notes |
|------|-----------|-------|
| Bash | **YES** | Shell access |
| Read | **YES** | File reading |
| Write | **YES** | File writing |
| Edit | **YES** | File editing |
| Glob | **YES** | File pattern matching |
| Grep | **YES** | Content search |
| NotebookEdit | **YES** | Jupyter access |
| WebFetch | **YES** | Web content |
| WebSearch | **YES** | Web search |
| Skill | **YES** | Can invoke skills |
| TaskCreate | **YES** | Create tasks |
| TaskList | **YES** | List tasks |
| TaskGet | **YES** | Get task details |
| TaskUpdate | **YES** | Update tasks |
| Teammate | **YES** | Team operations (can teammate spawn more teammates?) |
| SendMessage | **YES** | Peer messaging |
| ToolSearch | **YES** | Load deferred MCP tools |
| **Task** | **NO — ABSENT** | Cannot spawn sub-agents. Tool entirely missing. |

**MCP tools** (deferred, loadable via ToolSearch):
- `mcp__neo4j-cypher__*` (get_neo4j_schema, read_neo4j_cypher, write_neo4j_cypher)
- `mcp__perplexity__*` (perplexity_ask, perplexity_research, perplexity_reason, perplexity_search)
- `mcp__alphavantage__*` (TOOL_LIST, TOOL_GET, TOOL_CALL)

### Test 4: Task List Cross-Visibility

| Test | Result | Evidence |
|------|--------|----------|
| Team creates own task dir | **YES** | `~/.claude/tasks/test-basic/` with internal task |
| Lead tasks go to `CLAUDE_CODE_TASK_LIST_ID` | **YES** | Tasks land in `earnings-orchestrator/`, NOT `test-basic/` |
| Teammate tasks go to same list as lead | **YES** | Teammate's TaskCreate put #3030 in `earnings-orchestrator/` |
| Teammate sees lead-created tasks | **YES** | Teammate saw #3031 (LEAD-SIDE-TASK) created by lead |
| Lead sees teammate-created tasks | **YES** | Lead saw #3030 (LEAD-CREATED-TASK) created by teammate |
| High-water mark shared | **YES** | Task IDs continue from same sequence (3030, 3031) |
| Team internal task in team dir | **YES** | `test-basic/1.json` — `_internal: true`, tracks teammate itself |

**Architecture**:
```
~/.claude/tasks/
├── test-basic/              ← TEAM internal task list
│   └── 1.json               ← Auto-created: tracks teammate as work item
│                               subject: "worker-1", _internal: true
│
└── earnings-orchestrator/   ← SHARED task list (from CLAUDE_CODE_TASK_LIST_ID)
    ├── 3030.json            ← Created by TEAMMATE
    └── 3031.json            ← Created by LEAD
    Both visible to both lead and teammate
```

**Key insight**: `CLAUDE_CODE_TASK_LIST_ID` wins for task routing. The team task dir is for internal tracking only. Lead and teammates share the configured task list.

### Test 5: Messaging

| Test | Result | Evidence |
|------|--------|----------|
| Lead → Teammate (SendMessage) | **PASS** | Message delivered, teammate acted on it |
| Teammate → Lead (SendMessage) | **PASS** | Teammate sent summary back to lead |
| Idle notification | **AUTO** | System sends `idle_notification` when teammate's turn ends |
| Shutdown request | **PASS** | Lead sends request, teammate approves, system sends `teammate_terminated` |
| Message after idle | **SOMETIMES** | First retry went idle without acting; second retry worked |

**Message delivery sequence** (observed):
```
1. Lead sends SendMessage → "Message sent to worker-1's inbox"
2. Teammate processes message, does work
3. Teammate sends SendMessage back to lead → appears as teammate-message
4. System sends idle_notification automatically
5. Lead sends shutdown_request → teammate approves
6. System sends teammate_terminated
7. System sends shutdown_approved
```

### Test 6: Permission Inheritance

| Test | Result | Evidence |
|------|--------|----------|
| `mode: "bypassPermissions"` on Task spawn | **IGNORED** | Teammate still prompted for Write permissions |
| Docs confirmation | **CONFIRMED** | "you can't set per-teammate modes at spawn time" |
| Teammate inherits lead's mode | **YES** | Lead in `default` mode → teammates in `default` mode |
| To bypass all permissions | **REQUIRES** | Lead must start with `--dangerously-skip-permissions` |

## 9.2 Phase 2: Teams + Existing Infrastructure

### Test 7: Teams + MCP Tools

| Test | Result | Evidence File |
|------|--------|---------------|
| ToolSearch for neo4j from teammate | **PASS** | `team-test-mcp.txt` |
| Neo4j query execution | **PASS** | Returned `{"c.name": "APPLE INC", "c.ticker": "AAPL"}` |
| ToolSearch for perplexity from teammate | **PASS** | `team-test-mcp.txt` |
| Perplexity query execution | **PASS** | Returned "Apple Inc.'s ticker symbol is AAPL" with citations |

**Conclusion**: Teammates have FULL MCP access via ToolSearch. All three providers (neo4j, perplexity, alphavantage) visible as deferred tools.

### Test 8: Teams + Skills

| Test | Result | Evidence File |
|------|--------|---------------|
| Skill tool available to teammate | **YES** | `team-test-skill.txt` |
| `test-re-arguments` with args | **PASS** | $ARGUMENTS substitution worked, ran in forked mode |
| `test-re-model-field` (model: haiku) | **PASS** | Ran as Haiku 4.5, confirming model: field enforcement in skills invoked by teammates |

**Conclusion**: Teammates CAN invoke Skills. Skills run in forked mode. $ARGUMENTS substitution works. Model field honored.

### Test 9: Teams + Sub-Agents (Task Tool)

| Test | Result | Evidence File |
|------|--------|---------------|
| Task tool available to teammate | **NO — ABSENT** | `team-test-subagent.txt` |
| Can teammate spawn sub-agents | **NO** | Tool entirely missing from teammate's tool list |
| Error type | **NOT BLOCKED — MISSING** | Not a permission error; the tool simply doesn't exist |

**Conclusion**: Teammates CANNOT spawn sub-agents. The Task tool is not provided to teammates. This rules out Pattern B (Teams + Sub-Agents Hybrid) from Part 7.

**Workaround**: Teammates CAN invoke Skills with `context: fork`, which creates a forked sub-agent internally. This is the path for teammates to delegate work.

## 9.3 Phase 3: Peer-to-Peer Messaging & Advanced

### Test 10: Peer-to-Peer Messaging

| Test | Result | Evidence File |
|------|--------|---------------|
| peer-a → peer-b send | **SUCCESS** | `team-test-peer-a.txt` |
| peer-b → peer-a send | **SUCCESS** | `team-test-peer-b.txt` |
| peer-b received peer-a's message | **YES** | `received_from_peer_a: HELLO FROM PEER-A` |
| peer-a received peer-b's message | **YES** | `received_from_peer_b: HELLO FROM PEER-B` (updated after delay) |
| Routing without config entry | **WORKS** | peer-a sent to peer-b before peer-b appeared in config.json |

**Key insight**: SendMessage routes by teammate name, NOT by config.json entries. The mailbox system handles routing independently of the config file. Teammates can message each other even if they haven't discovered each other via config.

**Timing note**: Messages between peers may arrive after a teammate's current turn ends. The teammate processes the message on its next wake-up. Both peers eventually received each other's messages after going idle and being woken by the incoming message.

### Test 11: Teammate Model Override

| Test | Result | Evidence File |
|------|--------|---------------|
| `model: "haiku"` on Task spawn | **STORED in config** | config.json shows `"model": "haiku"` |
| Actual model used | **Opus 4.6** | `team-test-model.txt`: `model_actual: claude-opus-4-6` |

**Conclusion**: The `model` parameter on Task tool is STORED in the team config but **NOT HONORED** at runtime. Teammate ran as Opus 4.6 (inherited from lead) despite config showing `"model": "haiku"`. This matches the permission behavior — teammates inherit everything from the lead.

### Test 12: Team Cleanup

| Test | Result | Evidence |
|------|--------|----------|
| `Teammate(cleanup)` | **PASS** | Returns success message |
| Team config dir removed | **YES** | `~/.claude/teams/test-basic/` deleted |
| Team task dir removed | **YES** | `~/.claude/tasks/test-basic/` deleted |
| Shared task list affected | **NO** | `~/.claude/tasks/earnings-orchestrator/` untouched |

**Key insight**: Cleanup removes ONLY the team-specific directories. The shared task list (`CLAUDE_CODE_TASK_LIST_ID`) is NOT affected.

### Test 13: Permission Propagation Fix

To avoid teammates prompting for every Write/Edit, add permission allow rules to settings.json:
```json
{
  "permissions": {
    "allow": [
      "Write", "Edit", "Skill", "Bash", "Read", "Glob", "Grep",
      "WebFetch", "WebSearch", "Task",
      "mcp__neo4j-cypher", "mcp__perplexity", "mcp__alphavantage"
    ]
  }
}
```
Teammates inherit these allow rules from the lead. This eliminates permission prompts without needing `--dangerously-skip-permissions`.

## 9.4 Phase 4: Broadcast, Nested Spawning, Idle Wakeup

### Test 14: Broadcast Messaging

| Test | Result | Evidence File |
|------|--------|---------------|
| `SendMessage(type: broadcast)` | **PASS** | Reported "broadcast to 3 teammate(s)" |
| listener-a received broadcast | **YES** | `team-test-broadcast-a.txt` |
| listener-b received broadcast | **YES** | `team-test-broadcast-b.txt` |
| spawner received broadcast | **YES** | `team-test-nested.txt` (appended broadcast receipt) |
| Broadcast wakes idle teammates | **YES** | Both listeners were idle, woke up on broadcast |

**Timing observation**: Teammates went idle saying "waiting for broadcast" (initial prompt had no immediate work). Broadcast was sent 3s later. Both woke up and processed it. Broadcast-to-idle-wake delivery is reliable.

### Test 15: Nested Team/Teammate Spawning

| Test | Result | Evidence File |
|------|--------|---------------|
| Teammate has `Teammate` tool | **YES** | Listed in tools |
| `Teammate(spawnTeam)` from teammate | **BLOCKED** | Error: "Already leading team 'test-round3'. A leader can only manage one team at a time." |
| Task tool (sub-agent spawn) from teammate | **ABSENT** | Tool not in teammate's toolset |

**Key insight**: Teammates have the `Teammate` tool but CANNOT use `spawnTeam` because they're already associated with a team. The error says "Already leading team" — the system treats the teammate as if it's a leader of the current team, which blocks creating a new one.

**No nesting possible**: Teammates cannot create nested teams AND cannot spawn sub-agents. The only delegation path is Skills with `context: fork`.

### Test 16: Idle → Wake Reliability (Broadcast)

| Test | Result | Notes |
|------|--------|-------|
| Broadcast wakes idle teammates | **RELIABLE** | All 3 teammates woke up and processed |
| Direct message wakes idle teammate | **SOMETIMES** | Earlier test: first retry after idle failed, second worked |

**Hypothesis**: Broadcast delivery may be more reliable than direct message for waking idle teammates. Or the earlier failure was a one-time race condition. Needs more testing.

## 9.5 Evidence Files

| File | Test | Location |
|------|------|----------|
| `team-test-basic.txt` | Tool inventory | `earnings-analysis/test-outputs/` |
| `team-test-tasklist.txt` | Task list visibility | `earnings-analysis/test-outputs/` |
| `team-test-crossvis.txt` | Cross-visibility | `earnings-analysis/test-outputs/` |
| `team-test-mcp.txt` | MCP access | `earnings-analysis/test-outputs/` |
| `team-test-skill.txt` | Skill invocation | `earnings-analysis/test-outputs/` |
| `team-test-subagent.txt` | Sub-agent spawn attempt | `earnings-analysis/test-outputs/` |
| `team-test-peer-a.txt` | Peer A messaging | `earnings-analysis/test-outputs/` |
| `team-test-peer-b.txt` | Peer B messaging | `earnings-analysis/test-outputs/` |
| `team-test-model.txt` | Model override | `earnings-analysis/test-outputs/` |
| `team-test-broadcast-a.txt` | Broadcast listener A | `earnings-analysis/test-outputs/` |
| `team-test-broadcast-b.txt` | Broadcast listener B | `earnings-analysis/test-outputs/` |
| `team-test-nested.txt` | Nested spawn + broadcast | `earnings-analysis/test-outputs/` |
| `team-test-rt2-combined.txt` | RT-2: Plan approval workflow | `earnings-analysis/test-outputs/` |
| `team-test-rt9-combined.txt` | RT-3/RT-9: Task deps + team launch | `earnings-analysis/test-outputs/` |
| `team-test-rt4-skill-chain.txt` | RT-4: Skill chain from teammate | `earnings-analysis/test-outputs/` |
| `team-test-rt5-combined.txt` | RT-5: File conflict (3 writers) | `earnings-analysis/test-outputs/` |
| `team-test-rt5-shared.txt` | RT-5: Shared file (last writer wins) | `earnings-analysis/test-outputs/` |
| `team-test-rt5-writer[1-3].txt` | RT-5: Individual writer reports | `earnings-analysis/test-outputs/` |
| `team-test-rt7-hooks.txt` | RT-7: Hook enforcement | `earnings-analysis/test-outputs/` |
| `team-test-rt8-mcp-preload.txt` | RT-8: MCP pre-load test | `earnings-analysis/test-outputs/` |
| `team-test-skill-launch.txt` | RT-9: Skill-driven team launch | `earnings-analysis/test-outputs/` |
| `team-test-skill-launch-a.txt` | RT-9: Worker-a output | `earnings-analysis/test-outputs/` |
| `team-test-skill-launch-b.txt` | RT-9: Worker-b output | `earnings-analysis/test-outputs/` |
| `test-teams-rt9-a.txt` | RT-9 round 1: Worker-a output | `earnings-analysis/test-outputs/` |
| `team-test-rt9-b.txt` | RT-9 round 1: Worker-b output | `earnings-analysis/test-outputs/` |
| `test_mixed_claude_worker.txt` | RT-10: Claude worker in mixed-provider team | `earnings-analysis/test-outputs/` |
| `test_mixed_openai_worker.txt` | RT-10: OpenAI proxy worker in mixed-provider team | `earnings-analysis/test-outputs/` |
| `test_memory_local.txt` | v2.1.34: memory: local test | `earnings-analysis/test-outputs/` |
| `test_memory_local_verify.txt` | v2.1.34: memory: local cross-agent verify | `earnings-analysis/test-outputs/` |
| `test_memory_local_rerun.txt` | v2.1.34: memory: local preload retest | `earnings-analysis/test-outputs/` |
| `test_memory_project_definitive.txt` | v2.1.34: memory: project definitive preload test | `earnings-analysis/test-outputs/` |
| `test_agent_type_restrict.txt` | v2.1.34: agent Task(AgentType) restriction | `earnings-analysis/test-outputs/` |
| `test_hook_task_completed.log` | v2.1.34: TaskCompleted hook raw log | `earnings-analysis/test-outputs/` |
| `test_hook_teammate_idle.log` | v2.1.34: TeammateIdle hook raw log | `earnings-analysis/test-outputs/` |
| `test_hook_teammate_idle_worker.txt` | v2.1.34: TeammateIdle worker proof-of-life | `earnings-analysis/test-outputs/` |
| `test_cross_dep_openai.txt` | RT-10b: OpenAI data via cross-provider dep | `earnings-analysis/test-outputs/` |
| `test_cross_dep_claude.txt` | RT-10b: Claude analysis of OpenAI data | `earnings-analysis/test-outputs/` |
| `test-parallel-teams.txt` | RT-12: Parallel TeamCreate from primary agent | `earnings-analysis/test-outputs/` |
| `test-parallel-teams-subagent.txt` | RT-12: Parallel TeamCreate from subagent | `earnings-analysis/test-outputs/` |
| `test-parallel-teams-split.txt` | RT-12: Split leadership (primary + subagent) | `earnings-analysis/test-outputs/` |
| `test-parallel-teams-dual-sub.txt` | RT-12: Dual subagents parallel team creation | `earnings-analysis/test-outputs/` |
| `test-subagent-team-leader.txt` | RT-12: Subagent full team lifecycle test | `earnings-analysis/test-outputs/` |

## 9.6 Master Capability Matrix (All Tests)

| # | Capability | Works? | Notes |
|---|------------|--------|-------|
| 1 | Create team (`Teammate spawnTeam`) | **YES** | Creates config + task dir |
| 2 | Spawn teammate (`Task` with `team_name`) | **YES** | Async, non-blocking, registered in config |
| 3 | Teammate tool access (Read/Write/Edit/Bash/etc) | **YES** | Full toolset except Task tool |
| 4 | Teammate Task tool (spawn sub-agents) | **NO** | Tool entirely absent |
| 5 | Teammate Skill tool | **YES** | Can invoke forked skills, model: field honored |
| 6 | Teammate MCP (Neo4j) | **YES** | Via ToolSearch → query |
| 7 | Teammate MCP (Perplexity) | **YES** | Via ToolSearch → ask |
| 8 | Teammate MCP (AlphaVantage) | **DEFERRED** | Visible, not yet tested |
| 9 | Lead → teammate messaging | **YES** | SendMessage type: message |
| 10 | Teammate → lead messaging | **YES** | SendMessage type: message |
| 11 | Peer-to-peer messaging | **YES** | Bidirectional, routes by name not config |
| 12 | Broadcast messaging | **YES** | Reaches all teammates, wakes idle ones |
| 13 | Shared task list (cross-visibility) | **YES** | Both use `CLAUDE_CODE_TASK_LIST_ID` |
| 14 | Task dependencies (`addBlockedBy`) | **YES** | Blocks correctly, unblocks when blocker completes |
| 15 | Teammate model override | **NO** | Config stores it, runtime ignores it |
| 16 | Teammate permission mode override (`bypassPermissions`) | **NO** | `mode` param ignored, inherits lead |
| 17 | Permission allow rules propagation | **YES** | Settings.json allow rules inherited |
| 18 | Team cleanup | **YES** | Removes team + task dirs, leaves shared list |
| 19 | Teammate shutdown (graceful) | **YES** | Request → approve → terminated |
| 20 | Internal team task tracking | **YES** | `_internal: true` task auto-created per teammate |
| 21 | Nested team from teammate | **NO** | "Already leading team" error |
| 22 | Sub-agent from teammate | **NO** | Task tool absent |
| 23 | Delegate mode (Shift+Tab) | **YES (soft)** | Cycles normal→plan→delegate. Soft-enforced — tools still execute. |
| 24 | Plan approval workflow (`mode: "plan"`) | **YES** | First mode param that works! Soft-enforced (Write doesn't hard-fail) |
| 25 | Skills with `context: fork` from teammate | **YES** | Skills run in forked mode within teammate |
| 26 | Multi-layer skill chain from teammate | **YES** | Parent → child → parent continues. Return values propagate. |
| 27 | File conflict (multiple writers) | **LAST-WRITE-WINS** | No worktrees. Write overwrites silently. Edit has stale-file detection. |
| 28 | Hooks fire for teammates | **YES** | PreToolUse/PostToolUse from settings.json fire and can block |
| 29 | Skill-driven team launch | **YES** | Skill can create team, tasks, spawn teammates. Needs session restart for cache. |
| 30 | MCP pre-load via skill allowed-tools | **NO** | MCP always deferred, ToolSearch always required |
| 31 | Session persistence / resume | **PARTIAL** | Config+tasks persist, teammates die. Orphans need manual cleanup. |
| 32 | Delegate mode task list routing | **CHANGED** | Routes to team internal dir, not CLAUDE_CODE_TASK_LIST_ID |
| 33 | Orphaned team handling | **MANUAL** | Cleanup only removes active team. `rm -rf` needed for orphans. |
| 34 | TaskCompleted hook (v2.1.33) | **YES** | Fires on task completion; JSON has task_id, subject, description |
| 35 | TeammateIdle hook (v2.1.33) | **YES** | Fires when teammate goes idle; JSON has teammate_name, team_name |
| 36 | Agent `Task(AgentType)` restriction (v2.1.33) | **YES (HARD)** | `tools: [Task(Explore)]` blocks unlisted sub-agent types. Hard enforcement. |
| 37 | `memory: local` scope (v2.1.33) | **STORAGE ONLY** | Dir + files persist; auto-preload NOT working (v2.1.34) |
| 38 | `memory: project` scope | **STORAGE ONLY** | Dir + files persist; auto-preload NOT working (v2.1.34) |
| 39 | Mixed-provider team (native) | **NO** | Task tool has no `provider` param; only `model: sonnet\|opus\|haiku` |
| 40 | Mixed-provider team (proxy via `./agent`) | **YES** | Claude teammate delegates to `./agent --provider openai`; full comms work |
| 41 | Cross-provider peer messaging | **YES** | Claude-worker ↔ OpenAI-worker bidirectional messaging confirmed |
| 42 | Cross-provider shared task list | **YES** | Both providers claimed/completed tasks on shared list |
| 43 | Cross-provider task dependencies | **YES** | OpenAI completes → unblocks Claude. Full addBlockedBy chain works. |
| 44 | OpenAI-as-brain (relay pattern) | **YES** | Claude as thin executor, OpenAI drives decisions via ./agent |
| 45 | Parallel team creation (primary x2) | **NO** | "A leader can only manage one team at a time." Hard-enforced. |
| 46 | Parallel team creation (primary + subagent) | **NO** | Subagent inherits parent's team leadership context. |
| 47 | Parallel team creation (dual subagents) | **NO** | First subagent's team binds entire session hierarchy. |
| 48 | Subagent TeamCreate access | **YES** | general-purpose subagents have TeamCreate and it works (1 team max). |
| 49 | Session-wide team leadership constraint | **CONFIRMED** | One team per session-hierarchy. All agents in session share slot. |
| 50 | Subagent full team lifecycle | **NO** | Can create team + tasks, but Task tool absent → can't spawn teammates. |

---

# Part 10: Open Questions (Updated with Answers)

### Answered

1. **Task list overlap**: Team creates its OWN task dir for internal tracking (`_internal: true`), but lead AND teammates both use `CLAUDE_CODE_TASK_LIST_ID` for actual work tasks. **ANSWERED: Both exist, `CLAUDE_CODE_TASK_LIST_ID` wins for routing.**
4. **Teammate model selection**: `model` param stored in config but **IGNORED at runtime**. Teammates always inherit lead's model. **ANSWERED: Inherits from lead.**
5. **Teammate skill inheritance**: Teammates CAN invoke skills from `.claude/skills/`. Both `test-re-arguments` and `test-re-model-field` worked. **ANSWERED: YES.**
8. **Teammate CLAUDE.md**: Skills loaded and worked correctly, confirming project context is active.
11. **Peer-to-peer messaging**: Fully bidirectional. Works even before target appears in config.json. **ANSWERED: YES.**
12. **Teammate → spawnTeam**: BLOCKED. Error: "Already leading team". Cannot create nested teams. **ANSWERED: NO.**
13. **Broadcast delivery**: YES — reaches all teammates reliably, wakes idle ones. **ANSWERED: YES.**

### Answered (Post-Compaction)

7. **Teammate hooks**: YES — PreToolUse/PostToolUse from settings.json fire for teammates. Tested with gx validation hook: invalid write BLOCKED. **ANSWERED: YES.**
16. **Multiple teammates same file**: Last-write-wins for Write tool (silent overwrite). Edit tool has stale-file detection (fails if file changed since last read). No worktrees, no automatic merge. **ANSWERED: Last-write-wins, use separate files.**
3. **Team config persistence**: Config + tasks persist on disk across sessions. Teammates (in-process) die with session and cannot be restored. Orphaned configs need manual `rm -rf`. **ANSWERED: Config YES, teammates NO.**
17. **Plan approval (mode: "plan")**: WORKS — first mode param that's actually enforced on teammates. Full workflow: plan → ExitPlanMode → lead review → approve/reject. Write is soft-enforced. **ANSWERED: YES.**
18. **Task dependencies**: addBlockedBy WORKS between teammates. Blocked task becomes available when blocker completes. **ANSWERED: YES.**
19. **Skill chains from teammate**: Multi-layer skill chains (parent → child → parent continues) work perfectly from teammates. Return values propagate. **ANSWERED: YES.**
20. **MCP pre-load in teammate skills**: Does NOT work. MCP tools remain deferred, ToolSearch always required. **ANSWERED: NO.**
21. **Skill-driven team launch**: Skills CAN create teams, tasks with dependencies, and spawn teammates. Requires `disable-model-invocation: false` and session restart for new skills. **ANSWERED: YES.**

### Answered (v2.1.33/34, 2026-02-06)

22. **Agent memory auto-preload**: Does MEMORY.md auto-load into agent system prompt? **NO — storage only.** Files persist on disk but are NOT injected into system prompt. Tested both `local` and `project` scopes across 2 restarts. **ANSWERED: Storage works, preload doesn't.**
23. **TaskCompleted hook**: Does it fire? **YES** — rich JSON with task_id, subject, description. **ANSWERED: WORKS.**
24. **TeammateIdle hook**: Does it fire? **YES** — rich JSON with teammate_name, team_name. **ANSWERED: WORKS.**
25. **Agent type restriction via tools**: Does `Task(AgentType)` in frontmatter restrict sub-agent spawning? **YES — hard enforcement.** Unlisted types blocked. **ANSWERED: ENFORCED.**
28. **Mixed-provider teams (native)**: Can Task tool spawn OpenAI/Gemini teammates? **NO** — no `provider` parameter exists. Only `model: sonnet|opus|haiku`. **ANSWERED: NOT POSSIBLE natively.**
29. **Mixed-provider teams (proxy)**: Can a Claude teammate proxy to OpenAI via `./agent`? **YES** — full bidirectional messaging, shared task list, task claiming all work. **ANSWERED: WORKS via proxy pattern.**
30. **Cross-provider peer messaging**: Does Claude ↔ OpenAI-proxy peer messaging work? **YES** — multiple messages exchanged in both directions. **ANSWERED: WORKS.**

### Answered (v2.1.37, 2026-02-08) — Parallel Teams & Subagent Leadership

31. **Parallel team creation (same agent)**: Can one agent call TeamCreate twice? **NO — hard-enforced.** Error: "A leader can only manage one team at a time." **ANSWERED: BLOCKED.**
32. **Subagent TeamCreate access**: Can subagents create teams? **YES** — TeamCreate works from subagents. **ANSWERED: YES (one team max).**
33. **Parallel teams via split leadership (primary + subagent)**: Primary creates Team A, subagent creates Team B? **NO** — subagent inherits parent's team context, gets blocked. **ANSWERED: BLOCKED.**
34. **Parallel teams via dual subagents (primary creates none)**: Two subagents each create a team? **NO** — first subagent's team binds entire session hierarchy, second blocked. **ANSWERED: BLOCKED.**
35. **Session-wide team constraint**: Is the one-team limit per-agent or per-session? **Per-session-hierarchy.** All agents in a session (primary + all subagents) share one team leadership slot. **ANSWERED: PER-SESSION.**
36. **Subagent as full team leader**: Can a subagent create a team AND spawn teammates? **NO** — TeamCreate works, TaskCreate works, but Task tool (needed to spawn teammates) is absent from subagents. Admin functions work, lifecycle doesn't. **ANSWERED: PARTIAL (admin only).**
37. **Any way to run two teams in parallel**: Tested 4 approaches (primary x2, primary+subagent, subagent x2, dual subagents). All blocked. **Only workaround**: two separate `claude -p` OS processes. **ANSWERED: NOT POSSIBLE within one session.**

### Still Open

2. **Team + SDK**: Can teams be created via the Agent SDK, or only interactively?
6. **Max teammates**: Is there a limit on the number of teammates?
9. **Cost tracking**: Does `/cost` in the lead show aggregate team cost?
10. **Teammate context window**: Do teammates get the same context window size as the lead?
14. **Team task dir purpose**: The `_internal: true` task — used for anything beyond tracking?
15. **Idle reliability**: Direct message to idle teammate sometimes lost — race condition?
26. **Memory auto-preload**: Will this be fixed in a future version? Feature exists in docs but doesn't work.
27. **`memory: user` scope**: Untested — does it write to `~/.claude/agent-memory/<name>/`?

---

# Part 11: Extended Tests (9 items — tested post-compaction)

ALL 9 TESTS COMPLETED.

### RT-1: Delegate Mode — TESTED ✅ WORKS (SOFT-ENFORCED)
**What**: Press Shift+Tab to enter delegate mode. Lead restricted to coordination-only tools.
**Test**: User pressed Shift+Tab. Mode cycled: normal → plan mode → delegate mode. System message listed allowed tools (TeammateTool, TaskCreate/Get/Update/List, SendMessage) and blocked tools (Bash, Read, Write, Edit, etc.). Tested: SendMessage WORKED, TaskCreate WORKED (#3036), Write SUCCEEDED despite "blocked", Read SUCCEEDED despite "blocked".
**Result**: Delegate mode IS ACTIVATED by Shift+Tab but enforcement is SOFT — the system tells the agent it cannot use certain tools, but they still execute. Same soft-enforcement pattern as plan mode. Task list routing changes to team's internal dir (not CLAUDE_CODE_TASK_LIST_ID).
**Output**: `earnings-analysis/test-outputs/team-test-rt1-rt6-combined.txt`

### RT-2: Plan Approval Workflow — TESTED ✅ WORKS (mode: "plan" IS ENFORCED)
**What**: Spawn teammate with plan approval required. Teammate plans, lead approves/rejects.
**Test**: Spawned planner with `mode: "plan"`. Planner entered plan mode, wrote plan file, called ExitPlanMode. Lead received `plan_approval_request` with full plan content. Lead approved via `plan_approval_response`. Planner exited plan mode.
**Result**: `mode: "plan"` IS ENFORCED — the FIRST mode param that actually works on teammates (bypassPermissions was ignored). Write tool is "soft-enforced" (doesn't hard-fail, but system flags restriction). Full approval workflow: plan → ExitPlanMode → lead reviews → approve/reject → teammate continues.
**Output**: `earnings-analysis/test-outputs/team-test-rt2-combined.txt`

### RT-3: Task Dependencies Between Teammates — TESTED ✅ WORKS
**What**: Create tasks with `addBlockedBy` — teammate B waits for teammate A to finish.
**Test**: Created task #3032 (TASK-A) and #3033 (TASK-B blocked by A). worker-a completed A, worker-b saw blocked status, then saw it unblock after A completed.
**Result**: Dependencies WORK. `addBlockedBy` correctly blocks tasks. When blocker completes, dependent task becomes available. worker-b confirmed: `task_was_blocked: YES`, `task_now_unblocked: YES`, `blocker_status: completed`.
**Output**: `earnings-analysis/test-outputs/team-test-rt9-combined.txt`

### RT-4: Complex Skill Chain from Teammate — TESTED ✅ FULL CHAIN WORKS
**What**: Teammate invokes a multi-layer skill chain (parent skill calls child skill, parent continues after child returns).
**Test**: Spawned skill-runner teammate, invoked `/test-re-workflow`. Full 4-step chain executed: Step1 (parent writes) → Child invoked & executed → Step3 (parent continues with child return value "CHILD_DONE") → Step4 (workflow complete).
**Result**: Multi-layer skill chains work perfectly from teammates. Parent continues after child returns. Return values propagate correctly. This confirms teammates CAN run our full earnings architecture via skills.
**Output**: `earnings-analysis/test-outputs/team-test-rt4-skill-chain.txt`

### RT-5: Multiple Teammates Editing Same File — TESTED ✅ LAST-WRITE-WINS
**What**: Three teammates write to the same file simultaneously.
**Test**: Spawned 3 writers to same file. Writer-1 wrote first, writer-2 overwrote, writer-3 overwrote again.
**Result**: NO worktrees used — all teammates share same filesystem. Write tool = last-write-wins (silent overwrite). Edit tool has stale-file detection (fails if file changed since last read, forcing re-read). No automatic merge exists. writer-3 confirmed hitting stale-file error, had to re-read before successful write.
**Implication**: Teammates must write to SEPARATE files, then lead merges. Never have multiple teammates Edit the same file.
**Output**: `earnings-analysis/test-outputs/team-test-rt5-combined.txt`

### RT-6: Session Persistence / Resume — TESTED ✅ CONFIG PERSISTS, TEAMMATES DON'T
**What**: Can a team survive across sessions? Does `/resume` work?
**Test**: Left team `test-teams-rt1-rt6` alive (no cleanup), restarted session. Checked what survived.
**Result**:
- Config file (`~/.claude/teams/{name}/config.json`): **PERSISTS** — full config with members, prompts, timestamps
- Task dir (`~/.claude/tasks/{name}/`): **PERSISTS** — tasks and lock file intact
- Inboxes dir: **PERSISTS** — with undelivered messages
- Teammates (in-process): **DEAD** — killed with session, cannot be restored
- Message to dead teammate: Accepted by inbox but never processed
- New team creation with orphan present: **WORKS** — no conflict
- Orphan cleanup: **MANUAL ONLY** — `Teammate(cleanup)` only removes active team, orphans need `rm -rf`
**Implication**: Teams are single-session. Orphaned configs accumulate and must be cleaned up manually.
**Output**: `earnings-analysis/test-outputs/team-test-rt1-rt6-combined.txt`

### RT-7: Teammate Hooks — TESTED ✅ HOOKS FIRE FOR TEAMMATES
**What**: Do global hooks from settings.json (PreToolUse, PostToolUse) fire for teammate sessions?
**Test**: Spawned hook-tester teammate. Normal write succeeded. Invalid gx write (wrong field count) was BLOCKED by PreToolUse hook (validate_gx_output.sh). Hook log confirmed: `BLOCK invalid field count` with teammate's write path and content.
**Result**: All hooks from settings.json fire for teammates. Quality gates (PreToolUse, PostToolUse) apply automatically. No extra configuration needed.
**Output**: `earnings-analysis/test-outputs/team-test-rt7-hooks.txt`, `logs/gx-output-guard.log`

### RT-9: Skill That Creates a Team (One-Button Team Setup) — TESTED ✅ FULLY WORKS
**What**: Write a skill (no `context: fork`) that when invoked, creates a team and spawns teammates automatically.
**Test round 1**: Created `/test-teams-launch` skill. Skill cache didn't refresh mid-session. Executed steps manually — full lifecycle worked.
**Test round 2**: After session restart, invoked `/test-teams-launch` via Skill tool. Skill loaded from cache. Full execution: team created → 2 tasks with dependency → 2 teammates spawned → worker-a completed TASK-A → worker-b detected unblock, completed TASK-B → shutdown → cleanup. ALL PASS.
**Result**: One-button team launch via skill WORKS. Key requirements: `disable-model-invocation: false` in frontmatter, session restart needed after creating new skills.
**Skill location**: `.claude/skills/test-teams-launch/SKILL.md`
**Output**: `earnings-analysis/test-outputs/team-test-skill-launch.txt`

### RT-8: MCP Pre-load via Skill allowed-tools in Teammate — TESTED ❌ DOES NOT WORK
**What**: If a teammate invokes a skill with `allowed-tools: mcp__neo4j-cypher__read_neo4j_cypher`, does the MCP tool pre-load without needing ToolSearch?
**Test**: Spawned mcp-tester teammate, invoked `/test-re-mcp-preload` (has `allowed-tools: mcp__neo4j-cypher__read_neo4j_cypher`, `context: fork`). Skill ran, but MCP tool remained deferred. ToolSearch still required.
**Result**: MCP pre-load via `allowed-tools` does NOT work — not in teammates, not in regular skills, not anywhere. MCP tools always require ToolSearch. Consistent with Infrastructure.md findings.
**Output**: `earnings-analysis/test-outputs/team-test-rt8-mcp-preload.txt`

### RT-10: Mixed Claude/OpenAI Provider Team — TESTED ✅ WORKS (PROXY PATTERN)

**What**: Can one teammate use OpenAI while another uses Claude? Does cross-provider communication work?

**Test A — Native attempt**: The Task tool only accepts `model: sonnet|opus|haiku`. There is no `provider` parameter. All teammates are Claude Code sessions natively. **RESULT: NOT POSSIBLE.**

**Test B — Proxy pattern**: Spawn two teammates on the same team:
- `claude-worker`: Normal Claude teammate (general-purpose)
- `openai-worker`: Claude teammate that delegates all knowledge questions to `./agent --provider openai` via Bash

**Exact reproduction steps**:

```
Step 1: Create team
  TeamCreate(team_name="test-mixed-provider")

Step 2: Create shared tasks
  TaskCreate(subject="MIXED-PROVIDER-TASK-A: Claude worker task")
  TaskCreate(subject="MIXED-PROVIDER-TASK-B: OpenAI worker task")

Step 3: Spawn claude-worker
  Task(
    subagent_type="general-purpose",
    team_name="test-mixed-provider",
    name="claude-worker",
    prompt="Claim task A. Write CLAUDE_RESULT to file. Send peer message to openai-worker."
  )

Step 4: Spawn openai-worker
  Task(
    subagent_type="general-purpose",
    team_name="test-mixed-provider",
    name="openai-worker",
    prompt="Claim task B. Call ./agent -p 'question' --provider openai via Bash.
            Write OPENAI_RESULT to file. Send peer message to claude-worker."
  )

Step 5: Wait for both to complete, verify cross-provider messaging
```

**Communication matrix tested**:

| From | To | Method | Result |
|------|----|--------|--------|
| Lead (Claude) → claude-worker | Task spawn + prompt | **WORKS** |
| Lead (Claude) → openai-worker | Task spawn + prompt | **WORKS** |
| claude-worker → openai-worker | SendMessage (peer) | **WORKS** — message delivered, openai-worker acted on it |
| openai-worker → claude-worker | SendMessage (peer) | **WORKS** — message delivered, claude-worker acted on it |
| openai-worker → OpenAI API | `./agent --provider openai` via Bash | **WORKS** — returned "Tokyo" |
| claude-worker → Lead | Task completion | **WORKS** — task #3052 completed |
| openai-worker → Lead | Task completion | **WORKS** — task #3053 completed |

**Actual message flow observed** (multi-round peer exchange):
```
1. claude-worker writes file, sends to openai-worker: "What is the capital of Germany?"
2. openai-worker calls ./agent --provider openai, gets answer, writes file
3. openai-worker sends to claude-worker: "What is the capital of Italy? (from OpenAI proxy)"
4. claude-worker receives openai-worker's message, replies: "Rome"
5. openai-worker calls ./agent --provider openai for Germany answer, sends: "Berlin (from OpenAI)"
6. claude-worker receives second message from openai-worker
7. Both write final summaries with CROSS_PROVIDER_COMMS: WORKS
```

**Claude worker final output** (`test_mixed_claude_worker.txt`):
```
CLAUDE_RESULT=The capital of France is Paris
PEER_MESSAGE_FROM_OPENAI_1: What is the capital of Italy? This answer came from OpenAI proxy.
PEER_MESSAGE_FROM_OPENAI_2: The capital of Germany is Berlin. (Answer from OpenAI proxy)
--- FINAL SUMMARY ---
YOUR_PROVIDER: Claude
TASK_COMPLETED: YES
PEER_MESSAGE_SENT: YES
PEER_MESSAGE_RECEIVED: YES - Received 2 messages from openai-worker
CROSS_PROVIDER_COMMS: WORKS
```

**OpenAI worker final output** (`test_mixed_openai_worker.txt`):
```
OPENAI_RESULT=Tokyo
PEER_MESSAGE_RECEIVED_FROM_CLAUDE_WORKER: "What is the capital of Germany?"
PEER_REPLY_SENT: "The capital of Germany is Berlin. (Answer from OpenAI proxy)"
PEER_REPLY_RECEIVED_FROM_CLAUDE_WORKER: "The capital of Italy is Rome."
--- FINAL SUMMARY ---
YOUR_PROVIDER: OpenAI (via proxy)
OPENAI_CALL: SUCCESS
TASK_COMPLETED: YES
PEER_MESSAGE_SENT: YES
PEER_MESSAGE_RECEIVED: YES
CROSS_PROVIDER_COMMS: WORKS
```

**Result**: Cross-provider team communication **FULLY WORKS** via proxy pattern. The team infrastructure (messaging, task list, shutdown) is provider-agnostic — it only cares about the Claude Code session layer. What happens inside the session (calling OpenAI via `./agent`) is transparent to the team.

**Key insight**: The proxy pattern works because:
1. **Team infrastructure is transport-layer** — mailbox routing, task lists, shutdown are all Claude Code plumbing that doesn't care what LLM the teammate uses internally
2. **`./agent --provider openai`** runs as a Bash subprocess, returns text, teammate relays it via SendMessage
3. **No special configuration needed** — just instruct the teammate's spawn prompt to use `./agent` for answers

**Limitations of proxy pattern**:
- OpenAI teammate is still a Claude Code session (Claude handles the plumbing)
- Extra latency: Claude receives message → calls `./agent` → OpenAI responds → Claude relays
- Extra tokens: Claude processes the message AND OpenAI processes the question
- No streaming: `./agent` returns complete text, not streamed

**Output files**:
- `earnings-analysis/test-outputs/test_mixed_claude_worker.txt`
- `earnings-analysis/test-outputs/test_mixed_openai_worker.txt`

**Test artifacts created**:
- No new agents/skills — used built-in `general-purpose` agent type
- Team `test-mixed-provider` (created and cleaned up during test)
- Tasks #3052 and #3053 (completed and cleaned up)

### RT-10b: Cross-Provider Task Dependencies + OpenAI-as-Brain Pattern — TESTED ✅ WORKS

**What**: Test two additional capabilities:
1. Task dependency chain across providers (OpenAI completes → unblocks Claude)
2. "OpenAI-as-brain" pattern where Claude is a thin relay/executor

**Setup**:
- Team: `test-mixed-advanced`
- Task #3054: OpenAI gathers data (no blockers)
- Task #3055: Claude analyzes data (blocked by #3054)
- `openai-brain` teammate: Claude session that routes ALL thinking to `./agent --provider openai` (spawn attempted with `model: haiku`)
- `claude-analyst` teammate: Normal Claude that polls for task unblock

**Cross-provider task dependency results**:

| Step | What happened | Result |
|------|--------------|--------|
| 1 | openai-brain called `./agent --provider openai` | ✅ Got "NYSE, NASDAQ, TSE" |
| 2 | openai-brain wrote data to `test_cross_dep_openai.txt` | ✅ File created |
| 3 | openai-brain marked task #3054 completed | ✅ Status → completed |
| 4 | Task #3055 automatically unblocked | ✅ blockedBy cleared |
| 5 | claude-analyst detected unblock, claimed #3055 | ✅ Polled and saw unblock |
| 6 | claude-analyst read OpenAI's file | ✅ Got the exchange data |
| 7 | claude-analyst wrote combined analysis | ✅ `test_cross_dep_claude.txt` |
| 8 | claude-analyst received message from openai-brain | ✅ Logged in output file |
| 9 | Both tasks completed | ✅ Full dependency chain resolved |

**OpenAI-as-brain pattern results**:

The Claude relay pattern worked — openai-brain made 2+ OpenAI calls via `./agent` and used their responses to drive file writes, task updates, and peer messaging. Claude's role was purely mechanical (execute tool calls that OpenAI's answers dictated).

**Claude analyst output** (`test_cross_dep_claude.txt`):
```
SOURCE: OpenAI worker (test_cross_dep_openai.txt)
=== ORIGINAL DATA FROM OPENAI ===
1. New York Stock Exchange (NYSE) - New York City, United States
2. NASDAQ - New York City, United States
3. Tokyo Stock Exchange (TSE) - Tokyo, Japan
=== CLAUDE ANALYSIS ===
1. NYSE: The world's largest stock exchange by market capitalization...
2. NASDAQ: The first electronic stock exchange...
3. TSE: The largest exchange in Asia...
CROSS_PROVIDER_DEPENDENCY: WORKS
=== MESSAGES FROM OPENAI-BRAIN ===
[openai-brain]: "Thanks for confirming. Glad the cross-provider dependency flow worked end to end."
```

**model: haiku on teammate**: Config stored `"model": "haiku"` for openai-brain. Runtime behavior still likely Opus (inherited from lead), consistent with RT-11 Test 11 finding. Since this teammate is a thin relay anyway, the model matters less — OpenAI does the thinking.

**The "OpenAI can't think natively" workaround**:

The key insight: Claude Code is **transport + tools**, not the intelligence. With the relay pattern:
```
Message arrives → Claude (cheap, just a relay) → ./agent --provider openai →
OpenAI thinks → returns answer → Claude executes tool calls → next step
```

To minimize Claude's cost as relay:
1. Use `model: haiku` on spawn (stored in config, may be honored in future versions)
2. Keep spawn prompt purely mechanical: "call ./agent, write file, send message"
3. OpenAI does ALL reasoning, Claude just executes the plan

**What remains impossible** (even with workaround):
- OpenAI cannot directly call SendMessage, TaskUpdate, or any Claude Code tool
- Every tool call requires a Claude round-trip (Claude reads OpenAI's output → calls tool)
- If OpenAI needs multi-step tool use (read file → think → write file), each step needs a Claude relay hop

**Output files**:
- `earnings-analysis/test-outputs/test_cross_dep_openai.txt` — OpenAI's data gathering
- `earnings-analysis/test-outputs/test_cross_dep_claude.txt` — Claude's analysis of OpenAI's data

### RT-11: v2.1.33/34 Feature Tests — Consolidated Results

**Tests run (2026-02-06, v2.1.34)**:

| Test | Agent/Artifact | Result | Output File |
|------|---------------|--------|-------------|
| Memory: local (write) | `.claude/agents/test_memory_local.md` | ✅ Dir + file created | `test_memory_local.txt` |
| Memory: local (verify cross-agent) | `.claude/agents/test_memory_local_verify.md` | ✅ Scoped correctly | `test_memory_local_verify.txt` |
| Memory: local (preload on rerun) | Same agent re-invoked | ❌ No preload | `test_memory_local_rerun.txt` |
| Memory: project (preload) | `.claude/agents/test-re-memory-agent` | ❌ No preload | `test_memory_project_definitive.txt` |
| TaskCompleted hook | `test_task_completed.sh` in settings.json | ✅ Fires with JSON | `test_hook_task_completed.log` |
| TeammateIdle hook | `test_teammate_idle.sh` in settings.json | ✅ Fires with JSON | `test_hook_teammate_idle.log` |
| Agent type restriction | `.claude/agents/test_agent_type_restrict.md` | ✅ Hard enforcement | `test_agent_type_restrict.txt` |
| Mixed-provider team | Team `test-mixed-provider` | ✅ Proxy pattern works | `test_mixed_claude_worker.txt`, `test_mixed_openai_worker.txt` |

### RT-12: Parallel Team Creation (Two Teams Simultaneously) — TESTED ❌ NOT POSSIBLE

**What**: Can a single agent call `TeamCreate` twice in the same message to run two independent teams in parallel?

**Test A — Primary agent (skill, no fork)**:
- Skill: `.claude/skills/test-parallel-teams.md` (no `context: fork`)
- Method: `claude -p` invokes skill → primary session calls TeamCreate x2 in one message
- TeamCreate #1 (`test-pteam-alpha`): **SUCCESS** — team created, config.json + task dir on disk
- TeamCreate #2 (`test-pteam-beta`): **FAILED** — `Already leading team "test-pteam-alpha". A leader can only manage one team at a time. Use TeamDelete to end the current team before creating a new one.`
- Disk: alpha dir existed (verified), beta dir never created
- **Note**: Team dirs auto-cleaned on session exit (team lead exit triggers cleanup)

**Test B — Subagent (general-purpose via Task tool)**:
- Skill: `.claude/skills/test-parallel-teams-subagent.md` (spawns general-purpose subagent)
- Method: `claude -p` invokes skill → primary spawns subagent → subagent calls TeamCreate x2
- TeamCreate #1 (`test-pteam-sub-alpha`): **SUCCESS** — team created
- TeamCreate #2 (`test-pteam-sub-beta`): **FAILED** — same error: `Already leading team "test-pteam-sub-alpha". A leader can only manage one team at a time.`
- Disk: alpha dir survived on disk (session killed before cleanup), beta never created
- **Bonus finding**: Subagents CAN create teams via TeamCreate (not just the primary session)

**Error message** (exact, both tests):
```
Already leading team "{first-team-name}". A leader can only manage one team at a time.
Use TeamDelete to end the current team before creating a new one.
```

**Conclusion**: **One team per agent, hard-enforced.** The constraint is per-agent-session, not per-tool-call. Once TeamCreate succeeds, the agent is bound as leader of that team. A second TeamCreate is blocked until TeamDelete releases leadership. This applies to both primary agents and subagents.

**Test C — Dual subagents, primary creates NO team**:
- Skill: `.claude/skills/test-parallel-teams-dual-sub.md`
- Method: Primary spawns TWO general-purpose subagents in parallel. Neither the primary nor the subagents share a team initially. Each subagent calls TeamCreate independently.
- Subagent A (`test-pteam-dual-a`): **SUCCESS** — team created
- Subagent B (`test-pteam-dual-b`): **FAILED** — `Already leading team "test-pteam-dual-a". A leader can only manage one team at a time.`
- **Critical insight**: Even though the primary never called TeamCreate, subagent A's TeamCreate made the entire session hierarchy a leader. Subagent B, sharing the same session, was blocked.

**Definitive conclusion**: **No way to run two teams in parallel within a single Claude Code session**, regardless of approach:

| Approach | Primary creates team? | Who creates 2nd? | Result |
|----------|----------------------|-------------------|--------|
| Primary x2 parallel | Yes (1st) | Primary (2nd) | BLOCKED |
| Primary + subagent | Yes | Subagent | BLOCKED (inherits parent team) |
| Subagent alone x2 | No | Subagent A then B | BLOCKED (A's team binds session) |
| Dual subagents parallel | No | Two subagents | BLOCKED (one wins, other inherits) |

The constraint is **per-session-hierarchy**, not per-agent. All agents within a session (primary + all subagents) share ONE team leadership slot.

**Only workaround**: Two completely separate `claude -p` processes (separate OS processes, separate sessions). They share the filesystem but nothing else.

**Output files**:
- `earnings-analysis/test-outputs/test-parallel-teams.txt` — primary x2 results
- `earnings-analysis/test-outputs/test-parallel-teams-subagent.txt` — single subagent x2 results
- `earnings-analysis/test-outputs/test-parallel-teams-split.txt` — primary + subagent split results
- `earnings-analysis/test-outputs/test-parallel-teams-dual-sub.txt` — dual subagent results

**Test D — Subagent as full team leader (create + spawn teammates)**:
- Skill: `.claude/skills/test-subagent-team-leader.md`
- Method: Primary spawns ONE general-purpose subagent. Subagent creates a team, creates a task, then tries to spawn a teammate on the team.
- TeamCreate: **SUCCESS** — subagent became `team-lead@test-sub-led-team`
- TaskCreate: **SUCCESS** — task #3057 created on shared list
- Spawn teammate (Task tool): **FAILED — Task tool not available to subagents**
- **Conclusion**: A subagent can create teams and tasks (admin functions), but **cannot spawn teammates** because the Task tool is absent from subagents. Only the primary agent has the Task tool. Therefore a subagent cannot run a full team lifecycle.

| Capability | Subagent can do it? |
|-----------|-------------------|
| TeamCreate | YES |
| TaskCreate/List/Get/Update | YES |
| TeamDelete | YES |
| SendMessage | YES |
| Spawn teammates (Task tool) | **NO — tool absent** |

**Test skills created**:
- `.claude/skills/test-parallel-teams.md` — primary agent test
- `.claude/skills/test-parallel-teams-subagent.md` — subagent test
- `.claude/skills/test-parallel-teams-split.md` — split leadership test
- `.claude/skills/test-parallel-teams-dual-sub.md` — dual subagent test
- `.claude/skills/test-subagent-team-leader.md` — subagent full lifecycle test

**All test artifact naming convention**: Files start with `test_` prefix to distinguish from production artifacts.

**Test agents created** (`.claude/agents/`):
- `test_memory_local.md` — memory: local scope test
- `test_memory_local_verify.md` — memory: local cross-agent verification
- `test_agent_type_restrict.md` — Task(AgentType) restriction in tools frontmatter

**Test hooks created** (`.claude/hooks/`):
- `test_task_completed.sh` — logs TaskCompleted event to file
- `test_teammate_idle.sh` — logs TeammateIdle event to file

**Hook configuration added** (`.claude/settings.json`):
```json
{
  "hooks": {
    "TaskCompleted": [
      { "hooks": [{ "type": "command", "command": ".../test_task_completed.sh" }] }
    ],
    "TeammateIdle": [
      { "hooks": [{ "type": "command", "command": ".../test_teammate_idle.sh" }] }
    ]
  }
}
```

---

# Part 12: Plain English — What Teams Actually Change

## 12.1 The Problem We Had Before Teams

Our earnings system needs to do 3 things:
1. **Predict** which way a stock will move after an earnings release (using ONLY data available before the release)
2. **Attribute** why the stock actually moved (using all data, including after the release)
3. **Orchestrate** — run both, keep their data separate, then compare results

The old way (Infrastructure.md) used **skills with `context: fork`**. Think of it like this:

```
You (main conversation)
  └── You say "/earnings-orchestrator AAPL"
        └── A new Claude is born (the orchestrator)
              It runs /earnings-prediction → another new Claude is born
              That finishes, writes a file, dies
              Then it runs /earnings-attribution → another new Claude is born
              That finishes, writes a file, dies
              Orchestrator reads both files, compares, done
```

**The key problems with the old way:**
- **Sequential, not parallel**: Prediction runs, FINISHES, then attribution runs. Can't run both at the same time. Skills always execute one after another.
- **One-way communication**: A child skill can only write files and return text to its parent. It can't ask a question mid-way. It can't talk to its siblings.
- **No sub-agents inside skills**: The Task tool (which spawns parallel workers) is blocked inside forked skills. This was the biggest frustration.
- **No coordination**: If prediction needs data that attribution already fetched, too bad — they can't share in real-time.

## 12.2 What Teams Give You

Teams are fundamentally different. Instead of a parent spawning children that run and die, you get **multiple independent Claude sessions running at the same time**, all able to talk to each other.

```
You (team lead)
  ├── Teammate: Predictor (alive, running, can message anyone)
  ├── Teammate: Attributor (alive, running, can message anyone)
  └── Teammate: Judge (alive, waiting for both, then synthesizes)
```

**What's different:**
- **Truly parallel**: Predictor and Attributor run AT THE SAME TIME
- **Can talk to each other**: Predictor can message Attributor and vice versa
- **Can talk to you**: Each teammate messages the lead when done
- **Shared task list**: Everyone sees the same to-do list with dependencies
- **Each has full tools**: Read, Write, Edit, Bash, MCP (Neo4j, Perplexity), Skills — everything except spawning sub-agents

## 12.3 What Teams DON'T Give You (Limitations)

- **No sub-agents from teammates**: A teammate can't use the Task tool to spawn workers. But it CAN invoke skills (which create their own mini-forks internally).
- **No nested teams**: You can't have a team inside a team.
- **No parallel teams**: One team per session-hierarchy. The primary agent + all its subagents share a single team leadership slot. Tested 4 approaches (primary x2, primary+subagent, subagent x2, dual subagents) — all blocked. Only workaround: separate OS processes. *(Confirmed RT-12, 2026-02-08)*
- **Lead must be primary agent**: Subagents can call TeamCreate (team is created on disk) but lack the Task tool to spawn teammates. A team without teammates is useless. Only the primary session can run a full team lifecycle. *(Confirmed RT-12 Test D, 2026-02-08)*
- **No worktrees**: Everyone writes to the same filesystem. If two teammates write the same file, last one wins. Solution: each writes to their own file.
- **7x token cost**: Each teammate is a full Claude session. 3 teammates = 4 sessions (including you) = ~4x the cost.
- **Single session only**: If you restart, teammates die. Config stays on disk but teammates must be re-spawned.
- **Model override doesn't work**: You can't make one teammate use Haiku and another use Opus. They all inherit your model.
- **Soft enforcement only**: Delegate mode and plan mode tell the agent what it shouldn't do, but don't actually hard-block the tools.

## 12.4 Old Way vs New Way — Side by Side

### Scenario: Analyze AAPL's Q3 2024 Earnings

**OLD WAY (Skills Only — what Infrastructure.md describes):**
```
Step 1: You type /earnings-orchestrator AAPL Q3-2024
Step 2: Orchestrator skill runs (forked, isolated context)
Step 3: Orchestrator calls /earnings-prediction (forked)
          → Prediction queries Neo4j for PIT data
          → Prediction writes prediction to file
          → Prediction finishes and DIES
Step 4: Orchestrator calls /earnings-attribution (forked)
          → Attribution queries Neo4j for all data
          → Attribution searches Perplexity for news
          → Attribution writes analysis to file
          → Attribution finishes and DIES
Step 5: Orchestrator reads both files, compares, writes report
Step 6: Orchestrator finishes and DIES
Step 7: You see the final report

Total: ~15-20 minutes (sequential)
Cost: ~3 sessions worth of tokens
Parallelism: NONE (each step waits for the previous)
Communication: NONE between prediction and attribution
```

**NEW WAY (Teams):**
```
Step 1: You type /test-teams-launch AAPL Q3-2024 (or create team manually)
Step 2: Team created, two teammates spawned in parallel
Step 3: SIMULTANEOUSLY:
          - Predictor queries Neo4j, writes prediction
          - Attributor queries Neo4j + Perplexity, writes analysis
          Both run at the same time!
Step 4: Each messages you (the lead) when done
Step 5: You read both files, compare, write report
Step 6: Shut down teammates, clean up

Total: ~8-10 minutes (parallel)
Cost: ~3 sessions worth of tokens (same — but faster)
Parallelism: YES (prediction + attribution run simultaneously)
Communication: YES (can ask each other questions mid-way)
```

**Time saved**: Roughly cut in half because the two analysis steps overlap.

### Scenario: Deep Research with Multiple Sources

**OLD WAY**: You'd run one query at a time, or use the Task tool from main conversation to spawn parallel sub-agents (which works but each sub-agent can't see what the others found).

**NEW WAY**: Spawn 3 teammates:
- Neo4j Researcher: queries the database
- Web Researcher: searches Perplexity
- Devil's Advocate: reads both, challenges conclusions

They share files AND can message each other. The Devil's Advocate can say "Your Neo4j data is missing Q2 — go check" and the Neo4j Researcher acts on it.

## 12.5 When to Use Which

| Situation | Use This | Why |
|-----------|----------|-----|
| Simple single query | **Direct (no skill, no team)** | Overhead not worth it |
| Multi-step but sequential | **Skills (fork)** | Cheaper, context isolation is automatic |
| Need context isolation (PIT data) | **Skills (fork)** | Skills give you automatic context walls |
| Two+ independent analyses | **Teams** | True parallelism saves time |
| Need real-time coordination | **Teams** | Teammates can message each other |
| Tight budget | **Skills (fork)** | Teams cost more (each teammate = full session) |
| One-button automation | **Skill that creates a Team** | Best of both: `/launch-team AAPL` triggers everything |

## 12.6 The Recommended Architecture Going Forward

```
You type: /earnings-team AAPL Q3-2024
  │
  │  (This skill creates a team and spawns teammates)
  │
  ├── Teammate: Predictor
  │     Invokes /earnings-prediction skill (which internally forks)
  │     Skill queries Neo4j via MCP, applies PIT filter
  │     Writes prediction file
  │     Messages lead: "Prediction done"
  │
  ├── Teammate: Attributor
  │     Invokes /earnings-attribution skill (which internally forks)
  │     Skill queries Neo4j + Perplexity
  │     Writes attribution file
  │     Messages lead: "Attribution done"
  │
  └── You (lead):
        Wait for both messages
        Read prediction file + attribution file
        Compare prediction vs actual
        Write final report
        Shut down teammates, clean up
```

**This combines the best of both:**
- Teams for parallelism and communication
- Skills inside teammates for context isolation (PIT data stays clean)
- Hooks fire for all teammates (quality gates apply everywhere)
- One-button launch via a skill

## 12.7 What Hooks/Quality Gates Still Apply

Everything from Infrastructure.md Part 6 still works with teams:
- **PreToolUse hooks**: Fire for ALL teammates (tested — gx validation blocked bad output)
- **PostToolUse hooks**: Fire for ALL teammates
- **Skills inside teammates**: Can have their own hooks too
- **The block/retry pattern**: If a hook blocks a teammate's write, the teammate auto-corrects

You don't need to change any of your existing hooks. They just work.

---

# Part 13: Diagrams

## Diagram 1: What a Team Looks Like

```
┌─────────────────────────────────────────────────────────┐
│                      YOUR SESSION                        │
│                     (Team Lead)                          │
│                                                          │
│  Tools: Everything                                       │
│  Role:  Create team, assign tasks, read results          │
│                                                          │
│         ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│         │Teammate A│  │Teammate B│  │Teammate C│       │
│         │          │  │          │  │          │       │
│         │ Its own  │  │ Its own  │  │ Its own  │       │
│         │ Claude   │  │ Claude   │  │ Claude   │       │
│         │ session  │  │ session  │  │ session  │       │
│         └──────────┘  └──────────┘  └──────────┘       │
│              │              │              │              │
│              └──────────────┼──────────────┘              │
│                             │                             │
│                    ┌────────┴────────┐                    │
│                    │  Shared Stuff:  │                    │
│                    │  • Task list    │                    │
│                    │  • Filesystem   │                    │
│                    │  • Mailbox      │                    │
│                    └─────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## Diagram 2: What Each Teammate CAN and CAN'T Do

```
  ┌─────────────── TEAMMATE ───────────────┐
  │                                         │
  │  ✅ CAN DO:                             │
  │  ├── Read / Write / Edit files          │
  │  ├── Run Bash commands                  │
  │  ├── Search web (WebSearch, WebFetch)   │
  │  ├── Query Neo4j (via ToolSearch)       │
  │  ├── Query Perplexity (via ToolSearch)  │
  │  ├── Invoke Skills (/earnings-pred)     │
  │  │     └── Skills can chain (A→B→A)    │
  │  ├── Create/Read/Update tasks           │
  │  ├── Message lead or other teammates    │
  │  └── Be quality-gated by hooks          │
  │                                         │
  │  ❌ CAN'T DO:                           │
  │  ├── Spawn sub-agents (no Task tool)    │
  │  ├── Create nested teams                │
  │  ├── Run parallel teams (1 per session) │
  │  ├── Override its own model             │
  │  ├── Survive a session restart          │
  │  └── Use a different model than lead    │
  │                                         │
  └─────────────────────────────────────────┘
```

## Diagram 3: Who Can Talk to Who

```
                    ┌──────────┐
                    │   YOU    │
                    │ (Lead)   │
                    └────┬─────┘
                 ─────── │ ────────
               │         │         │
          ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐
          │  A     │ │   B    │ │   C    │
          └───┬────┘ └───┬────┘ └───┬────┘
              │          │          │
              └──────────┼──────────┘
              Everyone can message everyone

  ✅ Lead → Teammate        (direct message)
  ✅ Teammate → Lead        (direct message)
  ✅ Teammate → Teammate    (peer-to-peer)
  ✅ Lead → ALL teammates   (broadcast)
  ✅ Idle teammates wake up on message
```

## Diagram 4: OLD Way — Skills Chain (Sequential)

```
  TIME ──────────────────────────────────────────────►

  ┌──────────────────────────────────────────────────┐
  │ Orchestrator                                      │
  │                                                    │
  │  Step 1         Step 2            Step 3           │
  │  ┌─────────┐   ┌──────────────┐   ┌───────────┐  │
  │  │Predict  │   │ Attribution  │   │ Compare   │  │
  │  │         │   │              │   │ & Report  │  │
  │  │ query   │   │ query Neo4j  │   │           │  │
  │  │ Neo4j   │   │ query Perp.  │   │ read both │  │
  │  │ write   │   │ write file   │   │ files     │  │
  │  │ file    │   │              │   │           │  │
  │  └─────────┘   └──────────────┘   └───────────┘  │
  │  ◄── 7 min ──► ◄──── 8 min ────► ◄── 3 min ──►  │
  │                                                    │
  │  Total: ~18 minutes                                │
  └──────────────────────────────────────────────────┘

  Problems:
  • Prediction must FINISH before Attribution starts
  • They can't talk to each other
  • If Attribution needs something Prediction found — too late
```

## Diagram 5: NEW Way — Teams (Parallel)

```
  TIME ──────────────────────────────────────────────►

  ┌──────────────────────────────────────────────────┐
  │ You (Lead)                                        │
  │                                                    │
  │  Step 1                     Step 2                 │
  │  ┌─────────────────────┐   ┌───────────┐          │
  │  │ Predictor teammate  │   │ Compare   │          │
  │  │ query Neo4j         │   │ & Report  │          │
  │  │ write prediction    │   │           │          │
  │  │ ✉ "done"           │   │ read both │          │
  │  ├─────────────────────┤   │ files     │          │
  │  │ Attributor teammate │   │           │          │
  │  │ query Neo4j         │   │           │          │
  │  │ search Perplexity   │   │           │          │
  │  │ write attribution   │   │           │          │
  │  │ ✉ "done"           │   │           │          │
  │  └─────────────────────┘   └───────────┘          │
  │  ◄────── 8 min ──────►    ◄── 3 min ──►          │
  │                                                    │
  │  Total: ~11 minutes (saved ~7 min)                 │
  └──────────────────────────────────────────────────┘

  Benefits:
  • Both run AT THE SAME TIME
  • Can message each other if needed
  • Lead gets notified when each finishes
```

## Diagram 6: Teams + Skills Combined (Recommended)

```
  ┌───────────────────────────────────────────────────────┐
  │                                                        │
  │  You type: /earnings-team AAPL                         │
  │                                                        │
  │  ┌──────────────────────────────────────────────────┐  │
  │  │ Skill creates team + spawns 2 teammates          │  │
  │  └──────────────────────┬───────────────────────────┘  │
  │                         │                               │
  │         ┌───────────────┼───────────────┐               │
  │         ▼                               ▼               │
  │  ┌─────────────────┐           ┌─────────────────┐     │
  │  │ PREDICTOR        │           │ ATTRIBUTOR       │     │
  │  │ (teammate)       │           │ (teammate)       │     │
  │  │                  │           │                  │     │
  │  │  Invokes skill:  │           │  Invokes skill:  │     │
  │  │  /earnings-pred  │           │  /earnings-attr  │     │
  │  │       │          │           │       │          │     │
  │  │       ▼          │           │       ▼          │     │
  │  │  ┌──────────┐   │           │  ┌──────────┐   │     │
  │  │  │ Forked   │   │           │  │ Forked   │   │     │
  │  │  │ skill    │   │           │  │ skill    │   │     │
  │  │  │          │   │           │  │          │   │     │
  │  │  │ Context  │   │           │  │ Context  │   │     │
  │  │  │ isolated │   │           │  │ isolated │   │     │
  │  │  │ PIT-safe │   │           │  │ Full data│   │     │
  │  │  └──────────┘   │           │  └──────────┘   │     │
  │  │                  │           │                  │     │
  │  │  Writes file     │           │  Writes file     │     │
  │  │  ✉ "done"       │           │  ✉ "done"       │     │
  │  └─────────────────┘           └─────────────────┘     │
  │         │                               │               │
  │         └───────────────┬───────────────┘               │
  │                         ▼                               │
  │  ┌──────────────────────────────────────────────────┐  │
  │  │ YOU (lead): read both files, compare, report     │  │
  │  └──────────────────────────────────────────────────┘  │
  │                                                        │
  │  WHY THIS IS THE BEST OF BOTH WORLDS:                  │
  │  • Teams → parallelism (both run at same time)         │
  │  • Skills → context isolation (PIT data stays clean)   │
  │  • Hooks → quality gates (fire for ALL teammates)      │
  │  • One command → entire analysis                       │
  │                                                        │
  └───────────────────────────────────────────────────────┘
```

## Diagram 7: Shared Task List with Dependencies

```
  ┌─────────────────────────────────────────────┐
  │             SHARED TASK LIST                  │
  │                                               │
  │  #1 ┌──────────────────┐                     │
  │     │ Fetch 8-K data    │  ← no blocker      │
  │     │ owner: worker-a   │     can start now   │
  │     │ status: ✅ done   │                     │
  │     └────────┬─────────┘                     │
  │              │ unblocks                        │
  │              ▼                                 │
  │  #2 ┌──────────────────┐                     │
  │     │ Run prediction    │  ← was blocked      │
  │     │ owner: worker-a   │     now free         │
  │     │ status: ✅ done   │                     │
  │     └────────┬─────────┘                     │
  │              │ unblocks                        │
  │              ▼                                 │
  │  #3 ┌──────────────────┐                     │
  │     │ Compare & judge   │  ← was blocked      │
  │     │ owner: (lead)     │     now free         │
  │     │ status: ⏳ next   │                     │
  │     └──────────────────┘                     │
  │                                               │
  │  Everyone sees this list.                     │
  │  Tasks unblock automatically when             │
  │  their blockers complete.                     │
  └─────────────────────────────────────────────┘
```

## Diagram 8: What We Tested (Coverage Map)

```
  ┌─────────────────────────────────────────────────────┐
  │               TESTED CAPABILITIES                    │
  │                                                      │
  │  BASICS                          ADVANCED            │
  │  ✅ Create team                  ✅ Task deps        │
  │  ✅ Spawn teammates              ✅ Plan approval    │
  │  ✅ Shutdown teammates           ✅ Delegate mode    │
  │  ✅ Cleanup team                 ✅ Multi-layer      │
  │  ✅ Task create/list/update         skill chains     │
  │                                  ✅ Hooks fire for   │
  │  COMMUNICATION                      teammates        │
  │  ✅ Lead → teammate              ✅ One-button       │
  │  ✅ Teammate → lead                 team launch      │
  │  ✅ Peer ↔ Peer                     via skill        │
  │  ✅ Broadcast to all                                 │
  │  ✅ Wake idle teammates          LIMITATIONS         │
  │                                  ❌ No sub-agents    │
  │  INTEGRATIONS                    ❌ No nested teams  │
  │  ✅ Neo4j MCP works              ❌ No model override│
  │  ✅ Perplexity MCP works         ❌ No MCP pre-load  │
  │  ✅ Skills work                  ❌ No worktrees     │
  │  ✅ Skill chains work            ❌ Session = death  │
  │  ✅ Shared filesystem            ❌ Soft enforcement  │
  │  ✅ Permission inheritance          only             │
  │                                                      │
  │  FILE HANDLING                                       │
  │  ⚠️  Last-write-wins (no merge)                     │
  │  ✅ Edit tool detects stale files                    │
  │  📝 Rule: each teammate writes its OWN file          │
  │                                                      │
  │  51 capabilities tested, all documented              │
  │                                                      │
  │  v2.1.33/34 ADDITIONS (2026-02-06)                  │
  │  ✅ TaskCompleted hook event                         │
  │  ✅ TeammateIdle hook event                          │
  │  ✅ Agent Task(AgentType) restriction (HARD)         │
  │  ⚠️  memory: local/project (storage only, no preload)│
  │                                                      │
  │  MIXED-PROVIDER TEAM (2026-02-06)                   │
  │  ❌ Native provider param (doesn't exist)            │
  │  ✅ Proxy via ./agent --provider openai              │
  │  ✅ Cross-provider peer messaging                    │
  │  ✅ Cross-provider shared task list                  │
  │                                                      │
  │  PARALLEL TEAMS & SUBAGENT LEADERSHIP (2026-02-08)  │
  │  ❌ Two teams from one session (hard-enforced)       │
  │  ❌ Split leadership: primary + subagent (inherits)  │
  │  ❌ Dual subagents each create team (1st binds all)  │
  │  ❌ Subagent full lifecycle (no Task tool = no spawn)│
  │  ✅ Subagent can create 1 team (admin only)          │
  │  ✅ Subagent TaskCreate/List/Update works             │
  │  📝 Only primary agent can lead a functional team    │
  │  📝 Parallel teams need separate OS processes        │
  └─────────────────────────────────────────────────────┘
```

## Diagram 9: Decision Flowchart — Which Approach to Use

```
  START: What do you need to do?
    │
    ├── Simple query or one-step task?
    │     └── Just do it directly. No skill, no team.
    │
    ├── Multi-step but ONE thing at a time?
    │     └── Use a SKILL (context: fork)
    │         Cheaper. Context isolation built in.
    │
    ├── Need to keep prediction data separate from attribution?
    │     └── Use SKILLS inside teammates
    │         Team = parallelism
    │         Skill = context isolation
    │
    ├── Two+ independent analyses at the same time?
    │     └── Use a TEAM
    │         Each teammate does one analysis
    │         Lead combines results
    │
    ├── Need real-time back-and-forth between agents?
    │     └── Use a TEAM
    │         Only teams can message each other
    │
    └── Want one-button automation?
          └── Write a SKILL that creates a TEAM
              /earnings-team AAPL → does everything
```
