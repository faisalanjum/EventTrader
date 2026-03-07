# Earnings Architecture Plan

## Date: 2026-01-22 (Reorganized)

---

# Part 1: Quick Reference

## 1.1 Quick Summary for Next Bot

**What this is**: Multi-layer earnings analysis system using forked skills for context isolation.

**Key findings from testing (2026-01-16, retested 2026-02-05, hooks tested 2026-02-08, retested 2026-02-18 v2.1.45, retested 2026-03-06 v2.1.70):**

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
| `model:` field in skill/agent | ✅ **NOW ENFORCED** (Feb 2026) | `model: haiku` actually runs Haiku; per-layer cost control works. **CAVEAT**: Agents without explicit `tools:` field inherit ALL MCP schemas including Perplexity v0.14.0's `anyOf` → API 400. FIX: add `tools:` field to agent frontmatter. See anyOf root cause section. |
| `allowed-tools` for restriction (skills) | ❌ NOT ENFORCED | Skills use prompt injection, not tool filtering |
| `allowed-tools` for MCP pre-load | ✅ **WORKS** | List MCP tools to pre-load them |
| `disallowedTools` (skills) | ❌ NOT ENFORCED | Cannot block tools in skills |
| `disallowedTools` (agents) | ✅ **NOW ENFORCED** (Feb 2026) | Tools completely removed from agent's tool set |
| `tools` allowlist (agents) | ✅ **NOW ENFORCED** (Feb 2026) | Agent only sees tools in its allowlist |
| `agent:` field in skills | ✅ **NOW WORKS** (Feb 2026) | Grants agent's MCP tools without ToolSearch |
| `memory:` field (agents) | ✅ **NOW WORKING** (v2.1.52, was broken v2.1.34→v2.1.50) | All 3 scopes confirmed: `project`, `user`, `local`. System injects `# Persistent Agent Memory` section + MEMORY.md first 200 lines into system prompt. Dir auto-created. Task tool spawn works IF agent has explicit `tools:` field (excludes bad Perplexity MCP schema). See Part 10.13b. |
| `skills:` field (agents) | ✅ **WORKS** (Feb 2026) | Auto-loads skills into agent context (args not passed through) |
| Agent-scoped hooks | ✅ **WORKS** (Feb 2026) | PreToolUse, PostToolUse, PostToolUseFailure, Stop in agent frontmatter; **only when spawned as subagent via Task tool** (NOT via `--agent` flag) |
| SubagentStart hook | ✅ **WORKS** (Feb 2026) | Fires when subagent spawns; additionalContext injection **confirmed working** for custom agents (context added to agent window, NOT logged in transcript) |
| SubagentStop hook | ✅ **WORKS** (Feb 2026) | Fires when subagent completes; **blocking confirmed** (decision:block prevents stop, stop_hook_active=true on 2nd fire allows) |
| **PostToolUseFailure hook** | ✅ **WORKS** (v2.1.37) | Fires when tool call fails; JSON has tool_name, tool_input, error, is_interrupt, tool_use_id |
| **type: "prompt" hooks** | ⚠️ **REGRESSION** (v2.1.45) | Was WORKING in v2.1.37, **NO LONGER ENFORCED** in v2.1.45. Both safe and blocked commands execute without interception. Hook is simply not evaluated. |
| **type: "agent" hooks** | ❌ **NOT ENFORCED** (v2.1.37→v2.1.45) | Still not enforced. Hook configured in agent frontmatter did not block in either version. |
| **--agent flag + hooks** | ❌ **NOT WORKING** (v2.1.37) | Agent frontmatter hooks ONLY activate via Task tool subagent spawn; `--agent` flag starts main session without hooks |
| Task→Skill nesting | ✅ **WORKS** (Feb 2026) | Sub-agents can invoke skills; combine parallel Task + Skill chains |
| MCP in fork | ✅ WORKS | Either use allowed-tools OR ToolSearch |
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
| Task→Task nesting | ❌ **STILL BLOCKED** (v2.1.47→v2.1.52) | Sub-agents do NOT get the Task spawner tool. FG gets **40 tools** (7 base + 33 deferred, incl. TaskCreate but NOT Task); BG gets **12 tools** (or fewer with `tools:` whitelist). Neither gets Task spawner. Listing `Task` in `tools:` frontmatter has no effect — runtime strips it. Use Skill chains for depth. |
| MCP wildcards pre-load | ❌ NO | Only grants permission, still need ToolSearch |
| Error propagation | ⚠️ TEXT ONLY | No exceptions, must parse response |
| **Task deletion unblocks dependents** | ✅ WORKS | `status: "deleted"` removes task, unblocks dependents |
| **Task completion unblocks dependents** | ✅ WORKS | `status: "completed"` keeps task, unblocks dependents |
| **Cross-agent task manipulation** | ✅ WORKS | Any agent can update/delete any task by ID |
| **Upfront task creation pattern** | ✅ WORKS | Create all tasks upfront, skip via completed/deleted |
| **Parallel foreground Task spawn** | ✅ PARALLEL | 194ms spread, full tool access (See Part 10.14) |
| **Background agents: Write/MCP/Skill** | ✅ **WORKS** (Feb 2026, re-confirmed v2.1.52) | **12 direct tools** (was 11). +EnterWorktree. **Task/Team/SendMessage tools STILL REMOVED in v2.1.52** — not just blocked, completely absent from tool manifest (base AND deferred). Skill workaround also fails (forked skill inherits BG tool restriction). `tools` frontmatter whitelist cannot expand base set. Parallel write independence confirmed. 8 concurrent agents stable. |
| **Task `run_in_background` default** | ⚠️ MAY AUTO-ENABLE | Claude may choose background mode; explicitly set `run_in_background: false` if you need task tools |
| **`background: true` frontmatter** | ✅ **NEW** (v2.1.49) | Declarative background scheduling. Auto-sets `run_in_background` on Task — even foreground Task spawns run in BG mode. Via `--agent` flag: full 27-tool set (no restriction). **3-tier hierarchy confirmed**: `--agent`=27, FG Task=21, BG Task=12 tools. `tools:` field = INTERSECTION with bg-allowed set (restricts but cannot expand). **Confirmed v2.1.52**: TaskCreate/List/Get/Update stripped regardless of `tools:` field. |
| **`isolation: worktree` frontmatter** | ✅ **NEW** (v2.1.50) | Agent runs in temporary git worktree. Auto-cleanup if no changes. WorktreeCreate/WorktreeRemove hooks available. |
| **Memory auto-preload** | ✅ **NOW WORKING** (v2.1.52, was broken v2.1.34→v2.1.50) | All 3 scopes (project, user, local) confirmed via `--agent` flag AND Task tool spawn. System injects `# Persistent Agent Memory` header + directory path + guidelines + `## MEMORY.md` (first 200 lines). User scope adds "keep learnings general" hint. Task tool spawn requires explicit `tools:` field (to exclude bad Perplexity MCP schemas). |
| **Agent discovery (Task tool)** | ⚠️ **SESSION-START SNAPSHOT** | Task tool's `subagent_type` list is frozen at session start. Agents created mid-session or between continuations are NOT discoverable. Must start brand-new `claude` session. |
| Skill-specific hooks | ✅ WORKS (v2.1.0+) | Define in SKILL.md frontmatter; 3 events only |
| **TaskCompleted hook** | ✅ **WORKS** (v2.1.33) | Fires on task completion; JSON has `task_id`, `task_subject`, `task_description` |
| **TeammateIdle hook** | ✅ **WORKS** (v2.1.33) | Fires when teammate goes idle; JSON has `teammate_name`, `team_name`, `permission_mode` |
| **Agent `Task(AgentType)` restriction** | ✅ **ENFORCED** (v2.1.33) | `tools: [Task(Explore), Task(Bash)]` blocks all other sub-agent types |
| **`memory: local` scope** | ✅ **NOW WORKING** (v2.1.52) | Dir + files persist + auto-preload confirmed. Was broken v2.1.34→v2.1.50. |
| **Task completion crash** | ✅ **FIXED** (v2.1.45) | Task tool no longer crashes with ReferenceError on completion; TaskCompleted hook fires correctly |
| **Skills context leak after compaction** | ✅ **FIXED** (v2.1.45) | Skills invoked by subagents no longer bleed into main session after compaction |
| **Sandbox: .claude/skills write block** | ✅ **HARDENED** (v2.1.38) | Sandbox mode blocks writes to .claude/skills (prevents persistent prompt injection via ToxicSkills-style attacks) |
| **Heredoc delimiter security** | ✅ **HARDENED** (v2.1.38) | Fixed parser mismatch that allowed command smuggling past permission system |
| **Nested session guard** | ✅ **NEW** (v2.1.41, relaxed v2.1.47) | `claude` CLI blocks interactive launch inside another session; non-interactive subcommands (`doctor`, `plugin validate`) now allowed (#25803) |
| **Plugins system** | ✅ **NEW** (v2.1.45) | Full plugin system: marketplaces, /plugin install, enabledPlugins, extraKnownMarketplaces, strictKnownMarketplaces |
| **SDK rename** | ⚠️ **BREAKING** | claude-code-sdk → claude-agent-sdk (Python v0.1.37, TypeScript v0.2.45); ClaudeCodeOptions → ClaudeAgentOptions |
| **SDKRateLimitInfo/Event** | ✅ **NEW** (v2.1.45) | Rate limit status tracking: utilization, reset times, overage info (TypeScript SDK v0.2.45) |
| **Bash env-var wrapper permission matching** | ✅ **FIXED** (v2.1.38) | `FOO=bar command` patterns now correctly matched by permission system |
| **Fatal errors swallowed** | ✅ **FIXED** (v2.1.39) | Fatal errors now displayed instead of silently swallowed; important for debugging agent failures |
| **Process hanging after session close** | ✅ **FIXED** (v2.1.39) | Sessions no longer hang after close; relevant for SDK/agent cleanup |
| **MCP image content streaming crash** | ✅ **FIXED** (v2.1.41) | MCP tools returning image content no longer crash during streaming |
| **Hook blocking stderr visibility** | ✅ **FIXED** (v2.1.41) | Hook exit-code-2 blocking errors now show stderr to the user (was hidden) |
| **Subagent elapsed time accuracy** | ✅ **FIXED** (v2.1.41) | Permission wait time no longer counted in subagent elapsed time display |
| **Stale permission rules on settings change** | ✅ **FIXED** (v2.1.41) | Permission rules now cleared and reloaded when settings.json changes on disk |
| **Non-agent .md warnings in .claude/agents/** | ✅ **FIXED** (v2.1.43) | Spurious warnings for non-agent markdown files (e.g. README.md) in agents dir suppressed |
| **Prompt cache hit improvement** | ✅ **IMPROVED** (v2.1.42) | Date moved out of system prompt → better prompt cache hit rates → lower cost |
| **Large shell output memory usage** | ✅ **FIXED** (v2.1.45) | RSS no longer grows unboundedly with shell command output size; matters for long-running agents |
| **`last_assistant_message` in Stop/SubagentStop** | ✅ **NEW** (v2.1.47) | New field in Stop and SubagentStop hook inputs; provides final assistant response text without parsing transcripts |
| **Parallel file write/edit independence** | ✅ **FIXED** (v2.1.47) | One failing file write/edit no longer aborts all sibling parallel operations; each completes independently |
| **Concurrent agent 400 errors** | ✅ **FIXED** (v2.1.47) | "thinking blocks cannot be modified" API 400 errors in sessions with concurrent agents fixed (interleaved streaming content blocks) |
| **Background agent results** | ✅ **FIXED** (v2.1.47) | Background agents now return final answer instead of raw transcript data (#26012) |
| **Bash permission classifier hallucination** | ✅ **HARDENED** (v2.1.47) | Classifier now validates match descriptions against actual rules; prevents hallucinated descriptions from granting permissions |
| **Agent `model:` field for team teammates** | ✅ **FIXED** (v2.1.47) | Custom model field in .claude/agents/*.md was ignored when spawning teammates; now respected (#26064) |
| **Nested session guard** | ✅ **RELAXED** (v2.1.47) | Non-interactive subcommands (`claude doctor`, `claude plugin validate`) now work inside sessions (#25803) |
| **Agent session memory (3 fixes)** | ✅ **FIXED** (v2.1.47) | Stream buffers released after use, task message history trimmed after completion, O(n²) progress update accumulation eliminated |
| **Plan mode through compaction** | ✅ **FIXED** (v2.1.47) | Plan mode no longer lost after context compaction (#26061) |
| **Backslash-newline bash continuation** | ✅ **FIXED** (v2.1.47) | `\`-continuation lines no longer produce spurious empty arguments |
| **Git worktree agent/skill discovery** | ✅ **FIXED** (v2.1.47) | .claude/agents/ and .claude/skills/ from main repo now discovered in worktrees (#25816) |
| **`claude remote-control`** | ✅ **NEW** (v2.1.51) | Bridges local CLI to claude.ai/code web UI. Gated by GrowthBook `tengu_ccr_bridge` flag; works on Max subscription. **Headless server tested**: `env -u CLAUDECODE claude remote-control` connects cleanly (bypasses nested guard). Skills/MCP/files all accessible from browser. **Interactive only** — no programmatic API, cannot trigger skills without human typing. One session at a time. Good for debugging/exploring headless servers, NOT for production automation (SDK is strictly better for that). |
| **BashTool login shell skip** | ✅ **AUTOMATIC** (v2.1.51) | BashTool no longer uses `-l` (login shell) flag. `shopt login_shell`=off, `CLAUDE_BASH_NO_LOGIN` UNSET (skip is implicit). ~4x faster shell startup (0.001s vs 0.004s). No configuration needed. |
| **ConfigChange hook event** | ✅ **NEW** (v2.1.49) | 13th hook event type. Fires when settings files change. Sources: `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills`. Can block changes via `{"decision": "block"}` (except policy_settings). Chicken-and-egg: first edit that ADDS the hook itself does NOT trigger it. |
| **Dynamic `CLAUDE_CODE_TASK_LIST_ID` mid-session** | ✅ **WORKS** (v2.1.52) | Changing env vars in `settings.json` mid-session takes effect IMMEDIATELY. Task tools use the new list directory without restart. Extends v2.1.41's "stale permission rules" fix. See Part 10.12. |
| **`${CLAUDE_SKILL_DIR}` variable** | ✅ **NEW** (v2.1.69) | Skills can reference their own directory in SKILL.md content. Resolves to absolute path (e.g., `/path/.claude/skills/my-skill`). Use for relative file refs within skill dirs. |
| **`InstructionsLoaded` hook event** | ✅ **NEW** (v2.1.69) | 14th hook event type. Fires when CLAUDE.md or `.claude/rules/*.md` loaded. JSON includes `file_path`, `memory_type` ("Project"), `load_reason` ("session_start"). Does NOT fire if no CLAUDE.md/rules exist. |
| **`agent_id`/`agent_type` in hook events** | ✅ **NEW** (v2.1.69) | All hook events now include `agent_id` (subagents only) and `agent_type` (subagents + `--agent`). Main session hooks show neither field. |
| **HTTP hooks** | ✅ **NEW** (v2.1.63) | New hook `type: "http"` — POSTs JSON to a URL and receives JSON response. Alternative to `type: "command"` shell scripts. |
| **Opus 4.6 medium effort default** | ⚠️ **CHANGED** (v2.1.68) | Opus 4.6 defaults to medium effort for Max/Team. Use "ultrathink" keyword in prompt for high effort. `alwaysThinkingEnabled: true` may override. |
| **"ultrathink" keyword** | ✅ **RE-INTRODUCED** (v2.1.68) | Say "ultrathink" in prompt to enable high effort for next turn. |
| **Opus 4/4.1 removed** | ⚠️ **BREAKING** (v2.1.68) | Removed from first-party API. Users auto-migrated to Opus 4.6. |
| **Sonnet 4.5 → 4.6 migration** | ⚠️ **CHANGED** (v2.1.70) | Pro/Max/Team Premium auto-migrated from Sonnet 4.5 to 4.6. |
| **TaskCreate without `activeForm`** | ✅ **WORKS** (v2.1.69 SDK) | `activeForm` field no longer required. Spinner falls back to task subject. |
| **Skill colon descriptions** | ✅ **FIXED** (v2.1.69) | Skill descriptions with colons (e.g., "Triggers include: X, Y") now parse correctly. |
| **Skills without `description:` field** | ✅ **FIXED** (v2.1.69) | Skills without description now appear in available skills list. Content used as fallback. |
| **`includeGitInstructions` setting** | ✅ **NEW** (v2.1.69) | Set to false (or `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS` env var) to remove commit/PR workflow instructions from system prompt. Saves tokens for automation agents. |
| **TeammateIdle/TaskCompleted stop** | ✅ **ENHANCED** (v2.1.69) | Hooks now support `{"continue": false, "stopReason": "..."}` to stop the teammate, matching Stop hook behavior. |
| **WorktreeCreate/WorktreeRemove hooks** | ✅ **FIXED** (v2.1.69) | Plugin hooks were silently ignored; now fire correctly. |
| **Nested skill from gitignored dirs** | ✅ **FIXED** (v2.1.69) | Security fix: skill discovery no longer loads from gitignored directories (e.g., `node_modules`). |
| **AskUserQuestion in skill allowed-tools** | ✅ **FIXED** (v2.1.69) | Was silently auto-allowed with empty answers; now properly prompts. |
| **Hooks settings.json live-reload** | ❌ **NOT LIVE-RELOADED** (v2.1.70) | Hooks added to settings.json mid-session do NOT take effect. Env vars DO live-reload, hooks do NOT. Must start new session. |
| **FG tool presentation change** | ⚠️ **CHANGED** (v2.1.70) | FG agents now show 1 direct tool (ToolSearch) + 30 deferred. Was "7 base + 33 deferred". Same functional tool set; all require ToolSearch except ToolSearch itself. |
| **Agent discovery session snapshot** | ❌ **STILL SNAPSHOT** (v2.1.70) | Agents created mid-session still NOT discoverable by Task tool. No change. |

---

### Retest Summary (2026-03-06, v2.1.70) — v2.1.53-v2.1.70 (18 versions)

**11 capabilities tested:**

| Feature | Status | Change from v2.1.52 |
|---------|--------|---------------------|
| `${CLAUDE_SKILL_DIR}` variable (v2.1.69) | ✅ **WORKS** | **NEW** — resolves to skill directory absolute path |
| Skill colon descriptions (v2.1.69) | ✅ **FIXED** | Was broken (YAML parse error), now loads correctly |
| Skills without `description:` (v2.1.69) | ✅ **FIXED** | Was invisible in skill list, now loads with content as fallback |
| FG tool inventory (general-purpose) | 31 tools (1+30) | Was 40 (7+33). Presentation changed, not function |
| BG tool inventory (general-purpose) | 22 tools (1+21) | Was 12 base. MCP now listed as deferred. Same built-in set |
| BG TaskCreate/List/Get/Update | ❌ Still blocked | **No change** from v2.1.52 |
| `agent_id`/`agent_type` in hooks | ✅ **WORKS** | **NEW** — confirmed in SubagentStart JSON |
| `InstructionsLoaded` hook event | ✅ **WORKS** | **NEW** — 14th hook type. JSON: file_path, memory_type, load_reason |
| TaskCreate without activeForm | ✅ **WORKS** | **NEW** — SDK simplification, spinner uses subject |
| Agent discovery mid-session | ❌ Still snapshot | **No change** — must start new session |
| Hooks live-reload from settings.json | ❌ **NOT live-reloaded** | **NEW finding** — env vars reload, hooks do NOT |

**11 changelog-only items documented (not tested):**

| Feature | Version | Details |
|---------|---------|---------|
| Auto-memory proactive saves | v2.1.59 | Claude saves useful context to auto-memory. `/memory` management |
| HTTP hooks | v2.1.63 | `type: "http"` POSTs JSON to URL. Alternative to shell commands |
| Worktree shared configs | v2.1.63 | Project configs & auto memory shared across git worktrees |
| `ENABLE_CLAUDEAI_MCP_SERVERS=false` | v2.1.63 | Opt out of claude.ai MCP servers |
| Opus 4.6 medium effort default | v2.1.68 | Max/Team default. "ultrathink" for high effort |
| Opus 4/4.1 removed | v2.1.68 | Auto-migrated to Opus 4.6. Breaking for pinned models |
| `includeGitInstructions` setting | v2.1.69 | Remove commit/PR instructions from system prompt |
| TeammateIdle/TaskCompleted stop | v2.1.69 | `{"continue": false}` stops teammate |
| WorktreeCreate/WorktreeRemove fixed | v2.1.69 | Plugin hooks were silently ignored |
| Sonnet 4.5 → 4.6 migration | v2.1.70 | Auto-migration for Pro/Max/Team Premium |
| ToolSearch empty response fix | v2.1.70 | Server-rendered schemas no longer confuse model |

**FG vs BG tool comparison (v2.1.70):**

| Category | FG (foreground) | BG (background) |
|----------|-----------------|-----------------|
| Direct tools | ToolSearch (1) | ToolSearch (1) |
| Built-in deferred | 20 | 11 |
| MCP deferred | 10 | 10 |
| **Total** | **31** | **22** |
| TaskCreate/List/Get/Update | ✅ Yes | ❌ No |
| TeamCreate/TeamDelete | ✅ Yes | ❌ No |
| SendMessage | ✅ Yes | ❌ No |
| ListMcpResourcesTool | ✅ Yes | ❌ No |

**InstructionsLoaded hook JSON schema:**
```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "/home/faisal/EventMarketDB",
  "hook_event_name": "InstructionsLoaded",
  "file_path": "/home/faisal/EventMarketDB/CLAUDE.md",
  "memory_type": "Project",
  "load_reason": "session_start"
}
```

**SubagentStart hook JSON (v2.1.70 — with new fields):**
```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "/home/faisal/EventMarketDB",
  "agent_id": "a387f1b9adaa2b65c",
  "agent_type": "general-purpose",
  "hook_event_name": "SubagentStart"
}
```

**Test artifacts:**

| File | What It Tests |
|------|--------------|
| `.claude/skills/test-v170-skill-dir/SKILL.md` | ${CLAUDE_SKILL_DIR} substitution |
| `.claude/skills/test-v170-colon-desc/SKILL.md` | Colon in description |
| `.claude/skills/test-v170-no-desc/SKILL.md` | No description field |
| `.claude/agents/test-v170-tool-inventory.md` | Tool inventory agent |
| `.claude/agents/test-v170-hook-agent.md` | Hook fields test agent |
| `.claude/hooks/test-v170-hook-fields.sh` | Hook JSON capture script |
| `earnings-analysis/test-outputs/test-v170-*.txt` | All test output files |
| `earnings-analysis/test-outputs/test-v170-consolidated-results.txt` | Consolidated results |

**Updated hook coverage (v2.1.70):**

| Hook Event | Tested? | Status |
|------------|---------|--------|
| PreToolUse | ✅ | Works (command type). **prompt type REGRESSED v2.1.45**. agent type still not enforced. |
| PostToolUse | ✅ | Works (command type) |
| PostToolUseFailure | ✅ | Works (command type in agent FM) |
| Stop/SubagentStop | ✅ | Works (blocking + stop_hook_active) |
| SubagentStart | ✅ | Works (fires + additionalContext + **agent_id/agent_type NEW**) |
| TaskCompleted | ✅ | Works. **NEW**: `{"continue": false}` stops teammate (v2.1.69) |
| TeammateIdle | ✅ | Works. **NEW**: `{"continue": false}` stops teammate (v2.1.69) |
| ConfigChange | ✅ | Works (v2.1.49) |
| **InstructionsLoaded** | ✅ **NEW** | Works. Fires on CLAUDE.md/.claude/rules/ load. JSON: file_path, memory_type, load_reason |
| SessionStart | ❌ | Untested |
| SessionEnd | ❌ | Untested |
| UserPromptSubmit | ❌ | Untested |
| PermissionRequest | ❌ | Untested |
| Notification | ❌ | Untested |
| PreCompact | ❌ | Untested |
| WorktreeCreate | ✅ | **FIXED** (v2.1.69) — plugin hooks were silently ignored |
| WorktreeRemove | ✅ | **FIXED** (v2.1.69) — plugin hooks were silently ignored |

**Total hook events: 17** (was 13 in v2.1.49). Added: InstructionsLoaded (v2.1.69), WorktreeCreate (v2.1.50), WorktreeRemove (v2.1.50), PreCompact (from docs). Note: ConfigChange was already the 13th.

---

### Retest Summary (2026-02-18, v2.1.45) — Comprehensive Update

**Versions tested**: v2.1.38 through v2.1.45 (8 versions since last checkpoint)

**11 capabilities retested/researched:**

| Feature | v2.1.37 Status | v2.1.45 Status | Change |
|---------|---------------|---------------|--------|
| Task completion | Untested | ✅ Works, no crash | **Fixed** (was ReferenceError) |
| `memory: local` auto-preload | ⚠️ Storage only | ⚠️ Storage only | **No change** — still broken |
| `memory: project` auto-preload | ⚠️ Storage only | ⚠️ Storage only | **No change** — still broken |
| `type: "agent"` hooks (agent FM) | ❌ Not Enforced | ❌ Not Enforced | **No change** |
| `type: "prompt"` hooks (agent FM) | ✅ Works | ❌ **NOT ENFORCED** | **⚠️ REGRESSION** |
| PostToolUseFailure hook | ✅ Works | ✅ Works | Stable (10 fields in JSON) |
| SubagentStart injection | ✅ Works | ✅ Works | Stable |
| SubagentStop blocking | ✅ Works | ✅ Works | Stable (2-phase block/allow) |
| Task(AgentType) restriction | ✅ Enforced | ✅ Enforced | Stable (hard enforcement) |
| TaskCompleted hook | ✅ Works | ✅ Works | Stable |
| Nested session guard | N/A | ✅ NEW | Blocks `claude` CLI inside Claude Code sessions |

**5 new capabilities documented:**

| Feature | Status | Details |
|---------|--------|---------|
| **Plugins system** (v2.1.45) | ✅ Full system | Marketplaces, /plugin install, enabledPlugins, extraKnownMarketplaces, strictKnownMarketplaces. Plugins bundle commands, agents, skills, hooks, MCP servers. Official marketplace: anthropics/claude-plugins-official. **Note**: extraKnownMarketplaces only processes during interactive trust dialogs, NOT in -p mode/CI. |
| **SDK rename** | ⚠️ Breaking | claude-code-sdk → claude-agent-sdk. Python v0.1.37 (latest), TypeScript v0.2.45 (latest). ClaudeCodeOptions → ClaudeAgentOptions. SDK no longer loads Claude Code system prompt by default. |
| **SDKRateLimitInfo/Event** (v2.1.45) | ✅ New types | Rate limit status: utilization, reset times, overage info. TypeScript SDK v0.2.45. Field definitions not yet in public docs. |
| **SDK task_started message** (v0.2.45) | ✅ New | System message emitted when subagent tasks are registered. Session.stream() fixed for background subagents. |
| **Python SDK ThinkingConfig** (v0.1.36) | ✅ New | ThinkingConfigAdaptive/Enabled/Disabled types. `effort` field: low/medium/high/max. `thinking` overrides deprecated `max_thinking_tokens`. |

**11 operational/infrastructure fixes documented (v2.1.38–v2.1.45):**

| Fix | Version | Impact |
|-----|---------|--------|
| Bash env-var wrapper permission matching | v2.1.38 | `FOO=bar cmd` now correctly matched by permission system |
| Fatal errors swallowed | v2.1.39 | Errors now displayed; critical for debugging agent failures |
| Process hanging after session close | v2.1.39 | Clean session teardown; relevant for SDK/agent cleanup |
| MCP image content streaming crash | v2.1.41 | MCP tools returning images no longer crash mid-stream |
| Hook blocking stderr visibility | v2.1.41 | Hook exit-code-2 blocks now show stderr (was hidden) |
| Subagent elapsed time accuracy | v2.1.41 | Permission wait time excluded from subagent timing |
| Stale permission rules on settings change | v2.1.41 | Rules reloaded when settings.json changes on disk |
| Non-agent .md warnings in .claude/agents/ | v2.1.43 | Spurious warnings for README.md etc. suppressed |
| Prompt cache hit improvement | v2.1.42 | Date moved out of system prompt → better cache hits → lower cost |
| Large shell output memory usage | v2.1.45 | RSS no longer grows unboundedly with output size |
| ENAMETOOLONG for deep paths | v2.1.44 | Deeply-nested directory paths no longer cause errors |

**2 security fixes documented:**

| Fix | Version | Details |
|-----|---------|---------|
| Sandbox .claude/skills write block | v2.1.38 | Prevents persistent prompt injection via ToxicSkills-style supply chain attacks. OS-level enforcement (bubblewrap/seatbelt). |
| Heredoc delimiter parsing | v2.1.38 | Fixed parser mismatch allowing command smuggling past permission system. Related to CVE-2025-66032. |

**1 regression identified:**

| Regression | Details |
|-----------|---------|
| **type: "prompt" hooks in agent frontmatter** | Was WORKING in v2.1.37 (correctly blocked commands matching BLOCK_ME). In v2.1.45, hook is simply not evaluated — both safe and blocked commands execute without interception. SubagentStart injection still works, confirming hooks fire but prompt-type PreToolUse evaluation is broken. |

---

### Retest Summary (2026-02-24, v2.1.52) — v2.1.49-v2.1.52 Changelog Features

**4 capabilities tested:**

| Feature | Status | Impact |
|---------|--------|--------|
| `claude remote-control` (v2.1.51) | ✅ Works (Max subscription) | Bridges local CLI to claude.ai/code web UI. NOT for automation — interactive web bridge. Gated by GrowthBook `tengu_ccr_bridge` flag. |
| BashTool login shell skip (v2.1.51) | ✅ Confirmed (automatic) | `shopt login_shell`=off, no env var needed. ~4x faster startup (0.001s vs 0.004s). Matters for agents running 100+ Bash calls. |
| ConfigChange hook event (v2.1.49) | ✅ Works | 13th hook event type. Fires on settings file changes. 5 source types. Blocking supported. Chicken-and-egg: first edit adding the hook doesn't trigger itself. |
| Dynamic `CLAUDE_CODE_TASK_LIST_ID` mid-session | ✅ **WORKS** | **BIG FINDING**: Changing env block in settings.json mid-session takes effect IMMEDIATELY. Task tools use new list directory. No restart needed. |

**Dynamic CLAUDE_CODE_TASK_LIST_ID test sequence:**
1. Baseline: TaskCreate #36 → `~/.claude/tasks/earnings-orchestrator/`
2. Changed settings.json: `earnings-orchestrator` → `test-dynamic-change`
3. TaskList: EMPTY (switched to new list!)
4. TaskCreate #1 → `~/.claude/tasks/test-dynamic-change/`
5. Restored settings.json → `earnings-orchestrator` (tasks visible again)

**Implication for Part 10.12**: The "settings.json Always Wins" limitation is STILL TRUE for env vars vs settings.json precedence. But settings.json ITSELF can be changed dynamically mid-session, and the change takes effect immediately. This means:
- Can switch task lists per-ticker without spawning subprocesses
- A ConfigChange hook could auto-route tasks based on context
- The v2.1.41 "stale permission rules on settings change" fix extends to env vars

**ConfigChange hook schema (from test):**
```json
{
  "session_id": "f6d5a190-...",
  "transcript_path": "/home/faisal/.claude/projects/.../f6d5a190-....jsonl",
  "cwd": "/home/faisal/EventMarketDB",
  "hook_event_name": "ConfigChange",
  "source": "project_settings",
  "file_path": "/home/faisal/EventMarketDB/.claude/settings.json"
}
```

**ConfigChange source types:** `user_settings` (global), `project_settings` (.claude/settings.json), `local_settings` (.claude/settings.local.json), `policy_settings` (managed), `skills` (.claude/skills/).

**Headless remote-control test (2026-02-24):**
- `env -u CLAUDECODE claude remote-control` connects cleanly (bypasses nested session guard)
- Bridge URL generated, process stays alive, JSON-RPC architecture confirmed
- Skills, MCP, files all accessible from browser — but interactive only, no programmatic API
- NOT a replacement for SDK automation. Good for manual debugging/exploration on headless servers.

**Dynamic task list WITHOUT SDK or human (key insight):**
The mid-session settings.json change can be done by ANY agent/skill (all tiers have Write/Edit). This means an orchestrator can programmatically switch task lists per-ticker:
1. Agent edits settings.json → `CLAUDE_CODE_TASK_LIST_ID: "earnings-AAPL"`
2. Agent runs TaskCreate → tasks land in AAPL list
3. Agent edits settings.json → `CLAUDE_CODE_TASK_LIST_ID: "earnings-MSFT"`
4. Agent runs TaskCreate → tasks land in MSFT list
5. No SDK, no subprocess, no human, no restart. One session.

The SDK env var approach is still better for PARALLEL multi-ticker processing (separate processes). The settings.json approach is sequential but simpler and works from any context.

**Test artifacts:**
| File | What It Tests |
|------|--------------|
| `.claude/hooks/test_config_change.sh` | ConfigChange audit logger |
| `.claude/hooks/test_config_change_block.sh` | ConfigChange blocking variant |
| `.claude/hooks/test_remote_control.sh` | Remote-control test script |
| `.claude/agents/test-bash-login-shell.md` | Bash login shell diagnostic agent |
| `.claude/agents/test-config-change-hook.md` | ConfigChange hook test agent |
| `.claude/agents/test-config-change-dynamic.md` | Dynamic task list ID test agent |
| `earnings-analysis/test-outputs/test-v2152-changelog-results.txt` | Consolidated results (all 4 tests) |
| `earnings-analysis/test-outputs/test-remote-control.txt` | Remote-control raw output |
| `earnings-analysis/test-outputs/test-bash-login-shell.txt` | Bash login shell raw output |
| `earnings-analysis/test-outputs/test-config-change-hook.log` | ConfigChange hook fire log (4 events) |
| `earnings-analysis/test-outputs/test-remote-control-headless.txt` | Headless remote-control test (bridge, skills, architecture) |
| `earnings-analysis/test-outputs/test-fg-tool-inventory-v252.txt` | FG agent full tool inventory (40 tools, task tools work) |
| `earnings-analysis/test-outputs/test-bg-base-tools-v252.txt` | BG agent base tool inventory (task tools absent) |
| `earnings-analysis/test-outputs/test-bg-skill-workaround-v252.txt` | BG→Skill→Task workaround test (FAILS) |
| `earnings-analysis/test-outputs/test-bg-task-tools-v252-consolidated.txt` | Consolidated BG task tools verdict (all tests) |
| `/tmp/mem-detail-project.txt` | Memory preload proof: project scope (full system prompt quotes) |
| `/tmp/mem-detail-user.txt` | Memory preload proof: user scope (full system prompt quotes) |
| `/tmp/mem-detail-local.txt` | Memory preload proof: local scope (full system prompt quotes) |

**Memory auto-preload: NOW WORKING (v2.1.52) — was broken v2.1.34→v2.1.50**

Tested all 3 scopes via `--agent` flag with unique canary values planted in each MEMORY.md:

| Scope | Directory | Canary | In System Prompt? | Instructions Injected? |
|-------|-----------|--------|-------------------|----------------------|
| `project` | `.claude/agent-memory/{agent-name}/` | `STARFRUIT_PROJECT_252` | ✅ YES | ✅ Full "Persistent Agent Memory" block |
| `user` | `~/.claude/agent-memory/{agent-name}/` | `DRAGONFRUIT_USER_252` | ✅ YES | ✅ Full block + "user-scope: keep learnings general" |
| `local` | `.claude/agent-memory-local/{agent-name}/` | `JACKFRUIT_LOCAL_252` | ✅ YES | ✅ Full block |

What the system injects into the agent's system prompt:
1. `# Persistent Agent Memory` section header
2. Directory path: `You have a persistent Persistent Agent Memory directory at {path}. Its contents persist across conversations.`
3. Guidelines: how to save, what not to save, searching instructions
4. `## MEMORY.md` — first 200 lines of the file, auto-preloaded
5. User scope adds: "Since this memory is user-scope, keep learnings general since they apply across all projects"

**Scope differences:**

| Scope | Storage Location | Shared Across | Best For |
|-------|-----------------|---------------|----------|
| `project` | `.claude/agent-memory/{name}/` (in repo) | Same project, all users | Project-specific patterns, conventions, file locations |
| `user` | `~/.claude/agent-memory/{name}/` (home dir) | All projects for this user | Cross-project learnings, user preferences |
| `local` | `.claude/agent-memory-local/{name}/` (in repo) | Same project, same machine only | Machine-specific config, local env details. Typically gitignored. |

**Test via Task tool**: ✅ **CONFIRMED WORKING** (v2.1.52, 2026-02-24). Requires explicit `tools:` field in agent frontmatter to exclude Perplexity MCP v0.14.0 bad schemas. Both FG and BG spawns confirmed. See "Task Tool Spawn" section below.

**Why this was broken before**: From v2.1.34 through v2.1.50, the `memory:` field created directories and persisted files, but the system did NOT inject MEMORY.md content or instructions into the system prompt. The agent had to manually `Read` its MEMORY.md at startup. Now the system does this automatically.

---

### Retest Summary (2026-02-08, v2.1.37) — Hooks Deep Dive

**5 new capabilities tested:**

| Feature | Status | Details |
|---------|--------|---------|
| `PostToolUseFailure` hook event | ✅ Works | In agent frontmatter. Fires when Bash fails (exit code 1). STDIN JSON: `hook_event_name`, `tool_name`, `tool_input`, `tool_use_id`, `error`, `is_interrupt`. Error includes full stderr. |
| `type: "prompt"` hook handler | ✅ Works | LLM (Haiku default) evaluates hook input. Uses `$ARGUMENTS` for JSON injection. Returns `{"ok": true/false, "reason": "..."}`. Selectively blocks commands based on content analysis. Error: `"PreToolUse:Bash hook error: Prompt hook condition was not met: [reason]"` |
| `type: "agent"` hook handler | ❌ Not Enforced | Hook configured in agent frontmatter did not block. Both safe and blocked commands executed normally. May only work in settings.json or not yet implemented for subagent context. |
| SubagentStart `additionalContext` | ✅ Works | Hook returns `{"hookSpecificOutput":{"hookEventName":"SubagentStart","additionalContext":"..."}}`. Context reaches custom agents (confirmed: agent reported seeing string that only existed in hook script). Injected context does NOT appear in transcript `.jsonl` files. |
| SubagentStop blocking | ✅ Works | Stop hook in agent frontmatter auto-converts to SubagentStop. `stop_hook_active=false` on first fire → block with reason. `stop_hook_active=true` on second fire → allow. Agent follows hook instructions between fires. |

**2 important negative findings:**

| Finding | Details |
|---------|---------|
| `--agent` flag does NOT activate hooks | Agent frontmatter hooks ONLY work when spawned as subagent via Task tool. Running `claude --agent <name>` starts a main session without hook activation. Control test: `test-re-agent-hooks` (previously confirmed working via Task) showed "hook not enforced" via `--agent`. |
| `type: "agent"` hooks not enforced in FM | Unlike `type: "prompt"` (which works), `type: "agent"` hooks in agent frontmatter had no effect. The agent-type hook may require spawning a sub-subagent which isn't available in subagent context. |

**Hook test JSON schemas (from output):**

```json
// PostToolUseFailure — STDIN to hook script
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "/home/faisal/EventMarketDB",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PostToolUseFailure",
  "tool_name": "Bash",
  "tool_input": {"command": "cat /tmp/nonexistent", "description": "..."},
  "tool_use_id": "toolu_01B7...",
  "error": "Exit code 1\ncat: ...: No such file or directory",
  "is_interrupt": false
}

// SubagentStart — STDIN to hook script
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "/home/faisal/EventMarketDB",
  "hook_event_name": "SubagentStart",
  "agent_id": "a35e35a",
  "agent_type": "test-hook-post-failure"
}
```

**Complete hook coverage (v2.1.37, updated v2.1.45):**

| Hook Event | Tested? | Status |
|------------|---------|--------|
| PreToolUse | ⚠️ | Works (command type). **prompt type REGRESSED in v2.1.45** (was working v2.1.37). agent type still not enforced. |
| PostToolUse | ✅ | Works (command type) |
| PostToolUseFailure | ✅ NEW | Works (command type in agent FM) |
| Stop/SubagentStop | ✅ | Works (blocking + stop_hook_active) |
| SubagentStart | ✅ | Works (fires + additionalContext injection) |
| TaskCompleted | ✅ | Works (v2.1.33) |
| TeammateIdle | ✅ | Works (v2.1.33) |
| SessionStart | ❌ | Untested (session-level) |
| SessionEnd | ❌ | Untested (session-level) |
| UserPromptSubmit | ❌ | Untested (user-level) |
| PermissionRequest | ❌ | Untested (needs unpermitted tool) |
| Notification | ❌ | Untested (hard to trigger) |
| PreCompact | ❌ | Untested (needs context fill) |

---

### Retest Summary (2026-02-06, v2.1.33) — What Changed

**4 new features tested:**

| Feature | Status | Details |
|---------|--------|---------|
| `TaskCompleted` hook event | ✅ Works | Add to settings.json `hooks.TaskCompleted`; fires when any task status → `completed`. STDIN JSON includes: `hook_event_name`, `task_id`, `task_subject`, `task_description`, `session_id`, `transcript_path`, `cwd`. Env vars propagated: `CLAUDE_CODE_ENABLE_TASKS`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CODE_TASK_LIST_ID`, `CLAUDE_PROJECT_DIR` |
| `TeammateIdle` hook event | ✅ Works | Add to settings.json `hooks.TeammateIdle`; fires when a teammate's turn ends. STDIN JSON includes: `hook_event_name`, `teammate_name`, `team_name`, `permission_mode`, `session_id`, `transcript_path`, `cwd`. Same env vars as TaskCompleted |
| Agent `Task(AgentType)` in tools | ✅ Enforced | In agent frontmatter: `tools: [Read, Write, Task(Explore), Task(Bash)]`. Only listed agent types can be spawned. `Task(general-purpose)` and `Task(Plan)` correctly blocked when not in list |
| `memory: local` scope | ⚠️ **STORAGE ONLY** | Dir + files persist at `.claude/agent-memory-local/<name>/`. Auto-preload of MEMORY.md into system prompt **confirmed NOT working** as of v2.1.34. Tested: (1) `local` and `project` scopes, (2) across 2 session restarts, (3) same agent re-invoked after writing memory, (4) agent explicitly searched entire system prompt for memory strings — zero matches. Both scopes behave identically: storage works, recall doesn't. Agents must manually `Read` their memory dir at startup. |

**Hook JSON schemas (from test output):**

```json
// TaskCompleted — STDIN to hook script
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "/home/faisal/EventMarketDB",
  "hook_event_name": "TaskCompleted",
  "task_id": "3051",
  "task_subject": "DUMMY_TASK_FOR_HOOK_TEST",
  "task_description": "This task exists solely to test the TaskCompleted hook."
}

// TeammateIdle — STDIN to hook script
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "/home/faisal/EventMarketDB",
  "permission_mode": "default",
  "hook_event_name": "TeammateIdle",
  "teammate_name": "idle-worker",
  "team_name": "test-hooks-2133"
}
```

**Memory: practical workaround for per-entity memory (e.g., per-company):**

Since auto-preload doesn't work, use manual file-based memory:
```yaml
# In agent frontmatter:
memory: local
```
```
# In agent prompt instructions:
At startup, check .claude/agent-memory-local/<agent-name>/ for a file named {TICKER}.md.
If it exists, Read it for prior context. When done, Write updated findings back to that file.
```
This gives per-company persistent memory with no size limit.

---

### Retest Summary (2026-02-05) — What Changed

**6 things that NOW WORK (were broken in Jan 2026):**

| Feature | Was | Now | Why it matters |
|---------|-----|-----|----------------|
| `model:` field | ❌ Ignored | ✅ Enforced | Use `model: haiku` for cheap L3 queries, `model: opus` for complex reasoning |
| `agent:` field in skills | ❌ Ignored | ✅ Works | Write `agent: neo4j-news` → get MCP tools without ToolSearch |
| `disallowedTools` on agents | ❌ Not enforced | ✅ Enforced | Block dangerous tools (Write, Bash) on read-only agents |
| `tools` allowlist on agents | ❌ Not enforced | ✅ Enforced | Give agent only Read+Grep = safe read-only worker |
| Task→Skill nesting | ❌ Untested | ✅ Works | Main→Task (parallel)→Skill (fork)→Skill (fork) chains |
| Agent-scoped hooks | ❌ Untested | ✅ Work | PreToolUse can block tools; Stop fires on completion |
| Background: Write/MCP/Skill | ❌ Broken (Bash only) | ✅ Fixed | 13 tools now available; only TaskCreate/List/Get/Update still blocked |

**4 brand-new features (didn't exist in Jan 2026):**

| Feature | What it does | How to use |
|---------|-------------|------------|
| `memory: project\|local\|user` | Agent has persistent memory dir on disk | Add to agent frontmatter; file persists but **no auto-preload** into prompt (must manually Read) |
| `skills:` field | Auto-load skills into agent context | `skills: [neo4j-report, neo4j-news]` in agent frontmatter |
| SubagentStart hook | Fires when sub-agent spawns | Add to settings.json; can inject context via `additionalContext` |
| SubagentStop hook | Fires when sub-agent completes | Add to settings.json; receives transcript path |
| TaskCompleted hook (v2.1.33) | Fires when task status → completed | Add to settings.json `hooks.TaskCompleted`; receives task_id, subject, description |
| TeammateIdle hook (v2.1.33) | Fires when teammate turn ends | Add to settings.json `hooks.TeammateIdle`; receives teammate_name, team_name |
| `Task(AgentType)` restriction (v2.1.33) | Restrict sub-agent spawning | `tools: [Task(Explore), Task(Bash)]` in agent frontmatter; unlisted types blocked |

**The big insight — AGENTS vs SKILLS:**

Tool restrictions (`disallowedTools`, `tools`) only work on **agents** (`.claude/agents/`), NOT on **skills** (`.claude/skills/`). Skills use prompt injection — there's no tool-call interceptor. Agents use actual tool filtering — blocked tools are removed from the tool set entirely.

| Feature | On Skills | On Agents |
|---------|-----------|-----------|
| `disallowedTools` | ❌ Not enforced | ✅ Enforced |
| `tools` allowlist | ❌ Not enforced | ✅ Enforced |
| `model:` field | ✅ Enforced | ✅ Enforced |
| `agent:` field | ✅ Works | N/A |
| `memory:` field | N/A | ⚠️ Storage only (dir persists, **no auto-preload** as of v2.1.34) |
| `skills:` field | N/A | ✅ Works |

**Nesting — what can call what:**

| From → To | Works? | Note |
|-----------|--------|------|
| Skill → Skill | ✅ Yes | Up to 3+ layers tested |
| Skill → Task | ❌ No | Task tool not provided in forks |
| Task → Task | ❌ No | Task tool not provided to sub-agents |
| Agent → Task (restricted) | ✅ Yes | `tools: [Task(Explore)]` limits which agent types can be spawned (v2.1.33) |
| Task → Skill | ✅ Yes | **New!** Sub-agents can invoke skills |
| Main → Skill | ✅ Yes | Standard fork |
| Main → Task | ✅ Yes | Standard sub-agent, parallel OK |

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

**UPDATE (2026-02-05)**: The `model:` field in skill frontmatter **NOW WORKS**. `model: haiku` correctly runs as Haiku 4.5 (claude-haiku-4-5-20251001) instead of inheriting the parent's Opus. This enables per-layer cost control directly in skill definitions.

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

### NEW (v2.1.52): Mid-Session Dynamic Change via settings.json

**Tested 2026-02-24**: You CAN change `CLAUDE_CODE_TASK_LIST_ID` in settings.json DURING a live session and Task tools immediately use the new value. No restart needed.

```
Session running with CLAUDE_CODE_TASK_LIST_ID=earnings-orchestrator
  → Edit settings.json: change to test-dynamic-change
  → TaskList: EMPTY (switched to new directory!)
  → TaskCreate: #1 lands in ~/.claude/tasks/test-dynamic-change/
  → Edit settings.json: change back to earnings-orchestrator
  → TaskList: original tasks visible again
```

This means the "settings.json Always Wins" rule is still true (settings.json > env var), but settings.json itself is live-reloaded. Combined with the ConfigChange hook (v2.1.49), you could:
1. Have an orchestrator edit settings.json to switch task lists per-ticker
2. Use a ConfigChange hook to audit/validate the change
3. All within the same session, no subprocess spawning needed

**Agent/skill can do this programmatically (confirmed 2026-02-24):**
The original dynamic test was performed by the agent (this Claude session) using the Edit tool to modify settings.json — NOT a human. Every tool tier has Write/Edit access:

| Who edits settings.json? | Has Write/Edit? | Can switch task lists? |
|--------------------------|----------------|----------------------|
| Main session (27 tools) | ✅ | ✅ Tested and confirmed |
| FG sub-agent (21 tools) | ✅ | ✅ Yes (has Edit/Write) |
| BG sub-agent (12 tools) | ✅ | ✅ Yes (has Edit/Write) |
| Skill (forked, 14 tools) | ✅ | ✅ Yes (has Edit/Write) |

**Practical pattern — orchestrator switches task lists automatically:**
```
Orchestrator skill starts:
  1. Edit settings.json → CLAUDE_CODE_TASK_LIST_ID = "earnings-AAPL"
     (ConfigChange hook fires → audit log)
  2. TaskCreate "BZ research AAPL", TaskCreate "Judge AAPL"
     → tasks land in ~/.claude/tasks/earnings-AAPL/
  3. Run AAPL analysis...
  4. Edit settings.json → CLAUDE_CODE_TASK_LIST_ID = "earnings-MSFT"
     (ConfigChange hook fires → audit log)
  5. TaskCreate "BZ research MSFT", TaskCreate "Judge MSFT"
     → tasks land in ~/.claude/tasks/earnings-MSFT/
  6. No SDK needed. No subprocess. No restart.
```

**Evidence**: `earnings-analysis/test-outputs/test-v2152-changelog-results.txt` (Test 4)

**Four approaches for per-ticker task lists (updated 2026-02-24):**

| Approach | Requires | Parallel? | Human needed? | Best for |
|----------|----------|-----------|---------------|----------|
| SDK env var per invocation | SDK + Python/TS code | ✅ Yes | No | Production batch processing |
| Agent edits settings.json mid-session | Edit tool (any tier) | ❌ Sequential | **No** | Automated orchestrator within one session |
| Human edits settings.json interactively | Interactive `claude` | ❌ Sequential | Yes | Manual one-off analysis |
| Remote-control + settings.json edit | Max subscription + browser | ❌ Sequential | Yes (browser) | Headless server debugging |

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

## 10.13 Background vs Foreground Agent Spawning (Tested 2026-01-29, Retested 2026-02-05, Retested 2026-02-19 v2.1.47)

### Background Agents — Mostly Fixed!

In Jan 2026, `run_in_background: true` gave agents only Bash. Most of those bugs are now fixed.

**Retest results (2026-02-19, v2.1.47) — 8 parallel background agents tested:**

| Capability | Jan 2026 | Feb 2026 | v2.1.47 | Status |
|------------|----------|----------|---------|--------|
| Bash | ✅ Works | ✅ Works | ✅ Works | Stable |
| Write/Edit files | ❌ Blocked | ✅ Works | ✅ Works | Stable |
| MCP tools (via ToolSearch) | ❌ Blocked | ✅ Works | ✅ Works | Stable |
| Skill tool | ❌ Untested | ✅ Works | ✅ Works | Stable |
| ToolSearch | ❌ Untested | ✅ Works | ✅ Works | Stable |
| Glob/Grep/Read | ✅ Works | ✅ Works | ✅ Works | Stable |
| WebFetch/WebSearch | ❌ Untested | ✅ Works | ✅ Works | Stable |
| NotebookEdit | ❌ Untested | ❌ Untested | ✅ **Works** | Confirmed |
| TaskCreate/List/Get/Update | ❌ Blocked | ❌ Blocked | ❌ **Still NOT in tool set** | Unchanged |
| Parallel file write independence | N/A | N/A | ✅ **Confirmed** | **NEW** (v2.1.47) |
| Concurrent 8-agent spawn (no 400s) | N/A | N/A | ✅ **No errors** | **FIXED** (v2.1.47) |
| Results quality (final answer) | N/A | N/A | ✅ **Clean answers** | **FIXED** (v2.1.47) |
| Task completion crash | N/A | N/A | ✅ **No crash** | **FIXED** (v2.1.45) |

**11 tools available** in background mode: Bash, Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, WebSearch, Skill, ToolSearch.

**NOT available in background**: TaskCreate, TaskList, TaskGet, TaskUpdate, TaskOutput, TaskStop, SendMessage, TeamCreate, EnterPlanMode, AskUserQuestion.

**What's still missing**: All orchestration tools (Task*, Team*, SendMessage) and interactive tools (EnterPlanMode, AskUserQuestion).

**GitHub bugs status**:
- [#13254](https://github.com/anthropics/claude-code/issues/13254) - Background MCP tools — **FIXED** (Feb 2026)
- [#13890](https://github.com/anthropics/claude-code/issues/13890) - Background write/MCP — **FIXED** (Feb 2026)
- [#14521](https://github.com/anthropics/claude-code/issues/14521) - Background write files — **FIXED** (Feb 2026)

### When to Use Background vs Foreground

| Use Case | Mode | Why |
|----------|------|-----|
| Agent needs Write, MCP, Skill, Bash | ✅ Background OK | These all work now |
| Agent needs TaskCreate/Update | ❌ Use foreground | Task tools still blocked in background |
| Orchestrator needs to do other work while agents run | ✅ Background | Non-blocking |
| Orchestrator just waits for results | Either works | Foreground blocks but agents still run in parallel |

### Foreground Parallel Spawns (still the safest option)

**Key insight**: Multiple Task calls in the SAME message run in PARALLEL even without `run_in_background`. This gives you parallel execution AND full tool access.

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

**Trade-off:**
- Foreground: full tools (including TaskCreate), but orchestrator blocks
- Background: most tools (no TaskCreate), but orchestrator keeps working

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
| **Background: Write files** | CLI main | ✅ **Works (Feb 2026, re-confirmed v2.1.47)** |
| **Background: MCP tools** | CLI main | ✅ **Works (Feb 2026, re-confirmed v2.1.47)** |
| **Background: Skill tool** | CLI main | ✅ **Works (Feb 2026, re-confirmed v2.1.47)** |
| **Background: WebFetch/WebSearch** | CLI main | ✅ **Works (confirmed v2.1.47)** |
| **Background: NotebookEdit** | CLI main | ✅ **Works (confirmed v2.1.47)** |
| **Background: Parallel write independence** | CLI main | ✅ **Works (NEW v2.1.47)** — sibling failure doesn't abort others |
| **Background: 8 concurrent agents** | CLI main | ✅ **No 400 errors (FIXED v2.1.47)** |
| **Background: TaskCreate** | CLI main | ❌ **Still NOT in tool set (v2.1.47)** |

### Implementation for earnings-orchestrator

```markdown
## Recommended Pattern (Foreground — if agents need TaskUpdate)

1. Create all tasks first:
   - TaskCreate subject="BZ-Q1 AAPL 2024-01-02", description="pending"
   - TaskCreate subject="BZ-Q1 AAPL 2024-01-03", description="pending"

2. Spawn all agents in ONE message (NO run_in_background):
   - Task subagent_type="news-driver-bz" prompt="... TASK_ID=1 ..."
   - Task subagent_type="news-driver-bz" prompt="... TASK_ID=2 ..."
   (Both run in parallel, both have task tools)

3. Agents update their tasks:
   - Each agent calls TaskUpdate with results

4. Orchestrator continues after all agents complete
```

```markdown
## Background Pattern (OK if agents DON'T need TaskUpdate)

Spawn with run_in_background: true
- Agent can: Write files, call MCP, use Skills, run Bash
- Agent cannot: TaskCreate/List/Get/Update
- Orchestrator: keeps working, checks results later via TaskOutput
```

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

## 10.13b Background & Memory Retest (2026-02-21, v2.1.50)

### What's New Since v2.1.47

| Feature | Version | Source |
|---------|---------|--------|
| `background: true` in agent frontmatter | v2.1.49 | Declarative background scheduling |
| `isolation: worktree` in agent frontmatter | v2.1.50 | Git worktree isolation per agent |
| `WorktreeCreate`/`WorktreeRemove` hooks | v2.1.50 | Lifecycle hooks for worktree agents |
| `last_assistant_message` in Stop/SubagentStop | v2.1.47 | Final answer without transcript parsing |
| Ctrl+F kills background agents (not ESC) | v2.1.47 | Background agents survive ESC |
| Memory leak fixes (3 separate fixes) | v2.1.50 | Task state, output, teammate GC |

### Background Agent Tool Inventory (v2.1.50 — Tested 2026-02-21)

**Background via `run_in_background: true` on Task tool (general-purpose agent):**

| Tool | Available? | Change vs v2.1.47 |
|------|-----------|-------------------|
| Bash | ✅ YES | Stable |
| Glob | ✅ YES | Stable |
| Grep | ✅ YES | Stable |
| Read | ✅ YES | Stable |
| Edit | ✅ YES | Stable |
| Write | ✅ YES | Stable |
| NotebookEdit | ✅ YES | Stable |
| WebFetch | ✅ YES | Stable |
| WebSearch | ✅ YES | Stable |
| Skill | ✅ YES | Stable |
| ToolSearch | ✅ YES | Stable |
| **EnterWorktree** | ✅ **YES** | **NEW** |
| TaskCreate | ❌ NO | Unchanged |
| TaskList | ❌ NO | Unchanged |
| TaskGet | ❌ NO | Unchanged |
| TaskUpdate | ❌ NO | Unchanged |
| Task | ❌ NO | Unchanged |
| TaskOutput | ❌ NO | Unchanged |
| TaskStop | ❌ NO | Unchanged |
| SendMessage | ❌ NO | Unchanged |
| TeamCreate | ❌ NO | Unchanged |
| AskUserQuestion | ❌ NO | Unchanged |
| EnterPlanMode | ❌ NO | Unchanged |

**Total: 12 tools** (was 11 in v2.1.47). **+1: EnterWorktree.**

**Cross-model verification (Opus 4.6 retest, 2026-02-21):**

| Model | BG Tool Count | TaskCreate | Result |
|-------|--------------|------------|--------|
| Haiku | API 400 (schema) | API 400 | `anyOf` schema unsupported |
| Sonnet | **12** | BLOCKED | `test-bg-general-tools-v250.txt` |
| **Opus 4.6** | **12** | **BLOCKED** | `test-bg-opus-tools-v250.txt` |

**Confirmed model-independent**: The 12-tool restriction is enforced at Claude Code runtime level, not by the model. All three models see identical tool sets. SubagentStart hook `additionalContext` injection confirmed working on all models (INJECTED_MAGIC_STRING_7842 visible).

**Foreground via Task tool (general-purpose agent) — for comparison:**

**21 direct tools** (was 20 in v2.1.47). **+2: TeamDelete, EnterWorktree.**

Full list: Bash, Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, WebSearch, Skill, ToolSearch, TaskCreate, TaskList, TaskGet, TaskUpdate, TeamCreate, **TeamDelete**, SendMessage, **EnterWorktree**, ListMcpResourcesTool, ReadMcpResourceTool.

Still NOT available in foreground: Task, TaskOutput, TaskStop, AskUserQuestion, EnterPlanMode.

### `background: true` Frontmatter Field (v2.1.49)

**What it is**: A boolean in agent `.md` frontmatter that makes the agent ALWAYS run in background mode when spawned via Task tool.

```yaml
---
name: my-agent
background: true
model: sonnet
---
```

**Test results (via `--agent` flag, 2026-02-21):**

| Test | Result | Evidence |
|------|--------|----------|
| Agent runs successfully with bg:true | ✅ WORKS | `test-bg-frontmatter-v250.txt` |
| Tool set via `--agent` | **27 tools (FULL)** | `test-bg-fm-vs-runtime.txt` |
| Task tools work via `--agent` | ✅ ALL WORK | `test-bg-fm-tasktools.txt` |
| AskUserQuestion via `--agent` | ✅ YES | In tool set |
| MCP via ToolSearch | ✅ WORKS | v2.1.47 confirmed, stable |

**CRITICAL DISTINCTION: `--agent` vs Task tool spawning**

| Spawn Method | bg:true Effect | Tool Set |
|-------------|---------------|----------|
| `claude --agent my-agent` | **No effect** — agent IS the main session | **27 tools (FULL)** |
| Task tool (foreground) | bg:true **FORCES BG mode** — agent runs as BG regardless | **5 tools** (with `tools:` whitelist) or **12 tools** (without) |
| Task tool (background) | bg:true + run_in_background = same result | **5 tools** (with `tools:` whitelist) or **12 tools** (without) |

**Why the difference**: `--agent` runs the agent as the primary Claude Code session, which always has full tool access. `background: true` only affects scheduling when spawned via Task tool — it tells the system to auto-enable `run_in_background: true`.

**Does `tools` frontmatter override bg tool restriction? — DEFINITIVELY NO (tested 2026-02-24)**

The agent `test-bg-fm-tasktools` has both `background: true` and `tools: [TaskCreate, TaskList, TaskGet, TaskUpdate, Bash, Read, Write, Glob, Grep]`:
- Via `--agent`: ✅ All task tools work (but this is main session, so bg:true irrelevant)
- Via Task tool (BG spawn): ❌ **Only 5 tools delivered** — Bash, Read, Write, Glob, Grep. All 4 Task tools stripped.
- Via Task tool (FG spawn): ❌ **Only 5 tools delivered** — same result. `background: true` in frontmatter forces BG mode even without `run_in_background`.

**Tool Set Algebra (CONFIRMED)**:
```
Requested via tools: field = {TaskCreate, TaskList, TaskGet, TaskUpdate, Bash, Read, Write, Glob, Grep}
Allowed for BG agents  = {Bash, Read, Write, Glob, Grep, Edit, ToolSearch, ...12 tools}
Actual delivered        = Requested ∩ BG-Allowed = {Bash, Read, Write, Glob, Grep}
```

The `tools:` whitelist CAN restrict (Edit was bg-allowed but not requested → not delivered), but CANNOT expand beyond what the bg runtime permits. Task tools are unconditionally stripped regardless of frontmatter.

Evidence: `test-bg-tasktools-background-v252.txt`, `test-bg-tasktools-foreground-v252.txt`

### `background: true` Gotcha (CONFIRMED)

**`run_in_background` MAY AUTO-ENABLE**: Infrastructure.md line 68 warns Claude may auto-enable background mode. This is now even more relevant because:
1. `background: true` in frontmatter FORCES background mode
2. The Task tool ALSO has `run_in_background` parameter
3. If you need TaskCreate/Update, you MUST: (a) NOT use `background: true` in frontmatter, AND (b) explicitly set `run_in_background: false` on the Task call

### Memory Auto-preload Status (v2.1.50 — Definitive Retest)

**5 independent tests, 3 scopes, including same-agent re-invocation:**

| Test | Scope | Invocation | Auto-preload? | Evidence |
|------|-------|-----------|---------------|----------|
| test-memory-autopreload | project | 1st (write canary) | N/A | `test-memory-autopreload.txt` |
| test-memory-autopreload-verify | project | 2nd agent (diff name) | ❌ NO | `test-memory-v250-verify.txt` |
| test-mem-same-agent-verify | project | 1st → 2nd (SAME agent) | ❌ **NO** | `test-mem-same-agent-verify.txt` |
| test-memory-local-v250 | local | 1st | ❌ NO instructions | `test-memory-v250-local.txt` |
| test-memory-user-scope | user | 1st | ❌ NO instructions | `test-memory-v250-user.txt` |
| test-memory-verify-general | N/A | general-purpose agent | ❌ NO | `test-memory-verify-general-v250.txt` |

**Cross-model verification (Opus 4.6 retest, 2026-02-21):**

| Test | Model | Auto-preload? | Evidence |
|------|-------|--------------|----------|
| Prior canary check | Opus 4.6 | ❌ NO | `test-bg-opus-memory-v250.txt` |
| Memory instructions in prompt | Opus 4.6 | ❌ NO | No agent-memory content injected |
| Storage (write/read) | Opus 4.6 | ✅ WORKS | `dragonfruit_opus_2026` written and read back |
| SubagentStart hook injection | Opus 4.6 | ✅ WORKS | INJECTED_MAGIC_STRING_7842 confirmed |

**Key Opus insight**: SubagentStart hook `additionalContext` injection WORKS, proving the injection infrastructure is functional. It's specifically the `memory:` auto-preload mechanism that was broken, not the system prompt injection pipeline.

**~~Definitive finding~~: OVERRIDDEN — Memory auto-preload NOW WORKS in v2.1.52** (was broken v2.1.34→v2.1.50).

### Memory Auto-Preload: Complete Reference (v2.1.52, tested 2026-02-24)

**Status**: ✅ **FULLY WORKING** via `--agent` flag. All 3 scopes confirmed. Write-back persistence confirmed.

#### What the system injects into the agent's system prompt

When an agent has `memory: <scope>` in frontmatter, the system adds:

1. **`# Persistent Agent Memory`** section header
2. **Directory path**: `You have a persistent Persistent Agent Memory directory at {path}. Its contents persist across conversations.`
3. **Guidelines** (verbatim from official docs):
   - `MEMORY.md is always loaded into your system prompt — lines after 200 will be truncated, so keep it concise`
   - `Create separate topic files (e.g., debugging.md, patterns.md) for detailed notes and link to them from MEMORY.md`
   - `Update or remove memories that turn out to be wrong or outdated`
   - `Organize memory semantically by topic, not chronologically`
   - `Use the Write and Edit tools to update your memory files`
4. **What to save**: Stable patterns, key architectural decisions, user preferences, recurring solutions
5. **What NOT to save**: Session-specific context, incomplete info, CLAUDE.md duplicates, speculative conclusions
6. **Explicit user requests**: Save when user asks to remember, remove when asked to forget
7. **Scope-specific hint** (user scope only): `Since this memory is user-scope, keep learnings general since they apply across all projects`
8. **Scope-specific hint** (project scope): `Since this memory is project-scope and shared with your team via version control, tailor your memories to this project`
9. **Searching instructions**: Grep patterns for the memory directory
10. **`## MEMORY.md`** — first 200 lines of the file, auto-preloaded into prompt

#### Scope reference

| Scope | Frontmatter | Directory | Shared With | Git? | Best For |
|-------|------------|-----------|-------------|------|----------|
| `project` | `memory: project` | `.claude/agent-memory/{agent-name}/` | Team (via VCS) | ✅ Commit | Project patterns, architecture, conventions |
| `user` | `memory: user` | `~/.claude/agent-memory/{agent-name}/` | Just you (all projects) | ❌ Home dir | Cross-project learnings, personal preferences |
| `local` | `memory: local` | `.claude/agent-memory-local/{agent-name}/` | Just you (this machine) | ❌ Gitignore | Machine-specific config, local env details |

#### Test evidence (v2.1.52)

| Test | Scope | Canary | Visible in Prompt? | Evidence |
|------|-------|--------|-------------------|----------|
| Canary preload | project | `STARFRUIT_PROJECT_252` | ✅ YES | `/tmp/mem-detail-project.txt` |
| Canary preload | user | `DRAGONFRUIT_USER_252` | ✅ YES | `/tmp/mem-detail-user.txt` |
| Canary preload | local | `JACKFRUIT_LOCAL_252` | ✅ YES | `/tmp/mem-detail-local.txt` |
| Write-back | project | `banana_writeback_252` | ✅ YES (next invocation) | `test-memory-guidelines-v252.txt` |
| Guidelines injected | project | N/A | ✅ Full block with What to save/NOT save | `test-memory-guidelines-v252.txt` |
| 200-line truncation | project | `SENTINEL_LINE_200` visible, `TRUNCATED_LINE_201` invisible | ✅ Exact 200-line cutoff + warning | `test-memory-truncation-v252.txt` |
| Topic files | project | `mango_topic_252` | NOT auto-preloaded, but readable via Read tool | `test-memory-topicfiles-v252.txt` |
| BG + memory | project | `banana_bg_v250` | ✅ Memory in prompt (via `--agent`) | `test-bg-memory-combo-v252.txt` |
| Proactive save | project | N/A | ✅ Agent saved selectively per guidelines | `test-memory-proactive-save-v252.txt` |

#### How the agent updates memory

The agent does NOT auto-update memory silently. It updates memory when:
1. **It encounters something worth remembering** (guided by "What to save" rules)
2. **The user explicitly asks** ("remember that we use pnpm")
3. **You include instructions in the agent's prompt** (e.g., "Update your memory as you discover patterns")

The system provides the Write/Edit tools and the guidelines, but the agent decides WHEN to write. You can customize this by adding instructions in the agent's markdown body:
```markdown
Update your agent memory as you discover codepaths, patterns, library
locations, and key architectural decisions. This builds up institutional
knowledge across conversations.
```

#### What changed vs v2.1.50

| Aspect | v2.1.50 (BROKEN) | v2.1.52 (FIXED) |
|--------|------------------|-----------------|
| Directory creation | ✅ Works | ✅ Works |
| File persistence | ✅ Works | ✅ Works |
| MEMORY.md in system prompt | ❌ NOT injected | ✅ Auto-preloaded (first 200 lines) |
| Memory instructions injected | ❌ NOT injected | ✅ Full "Persistent Agent Memory" block |
| Memory directory path shown | ❌ NOT shown | ✅ Shown with Grep patterns |
| What to save / NOT save | ❌ NOT present | ✅ Full guidelines |
| Scope-specific hints | ❌ NOT present | ✅ User/project scope hints |
| Write-back persistence | ✅ Works (manual) | ✅ Works (auto-guided) |
| Manual Read workaround needed | YES | NO — automatic |

#### Additional Tests (v2.1.52, tested 2026-02-24)

| Test | Result | Evidence |
|------|--------|----------|
| **200-line truncation** | ✅ CONFIRMED | Lines 1-200 visible, 201+ invisible. Warning appended: `"MEMORY.md is 208 lines (limit: 200). Only the first 200 lines were loaded."` Boundary is **inclusive** (line 200 IS loaded). | `test-memory-truncation-v252.txt` |
| **Topic files** | ✅ WORKS (not auto-preloaded) | Only MEMORY.md auto-preloaded. Topic files (e.g., `topics.md`) must be manually discovered via Glob and read via Read tool. This is BY DESIGN — MEMORY.md is the concise index, topic files hold details. | `test-memory-topicfiles-v252.txt` |
| **BG + memory combo** | ✅ WORKS (via `--agent` and Task tool) | `background: true` + `memory: project` coexist. Memory IS in prompt. Task tool spawn also confirmed working with `tools:` field fix. | `test-bg-memory-combo-v252.txt`, `test-bg-memory-task-spawn-v252.txt` |
| **Proactive memory save** | ✅ AGENT SAVES SELECTIVELY | Agent filtered 3 facts: saved only pipeline schedule (non-obvious), skipped Neo4j/Python (already evident from codebase). Followed guidelines correctly. | `test-memory-proactive-save-v252.txt` |
| **Write target contamination** | ⚠️ RISK | Agent with `memory: project` (own dir at `.claude/agent-memory/`) also has access to project auto-memory (`~/.claude/projects/.../memory/MEMORY.md`). When asked to "save," it wrote to project auto-memory instead of its own agent memory. **Mitigation**: Explicit prompt instructions to specify which memory file. |

#### Task Tool Spawn: CONFIRMED WORKING (fresh session 2026-02-24)

| Test | Agent | Spawn | Memory? | Result | Evidence |
|------|-------|-------|---------|--------|----------|
| FG + memory | `test-memory-autopreload` | Task tool (foreground) | ✅ Both canaries visible | ✅ PASS | `test-memory-task-spawn-v252.txt` |
| BG + memory | `test-bg-memory-combo` | Task tool (background) | ✅ Canary visible | ✅ PASS | `test-bg-memory-task-spawn-v252.txt` |
| FG no memory | `guidance-extract` | Task tool (foreground) | N/A (no memory field) | ✅ PASS | `test-guidance-extract-spawn.txt` |

**Prerequisite**: Agent must have explicit `tools:` field in frontmatter. Without it, Perplexity MCP v0.14.0 schemas (which use `anyOf` at top level) get included in the API request and cause HTTP 400. All our data sub-agents already have `tools:` fields. Any new agent with `memory:` must also include `tools:`.

**All memory tests now complete. No remaining untested items.**

### Background + MCP Access (v2.1.47 → v2.1.50)

| Capability | Status | Evidence |
|-----------|--------|----------|
| ToolSearch in bg agent | ✅ WORKS | `test-bg-mcp-v247.txt` |
| Neo4j MCP call in bg agent | ✅ WORKS | `RETURN 1 AS test` returned `[{"test": 1}]` |
| Perplexity in bg agent | ✅ WORKS | v2.1.47 confirmed |
| MCP tools deferred (loadable) | ✅ 19 deferred tools visible | All MCP servers accessible |

**MCP access in background agents is STABLE from v2.1.47 to v2.1.50.**

**⚠️ DOCS CONTRADICTION**: Official docs at code.claude.com state *"MCP tools are not available in background subagents"*. Our tests prove otherwise — ToolSearch discovers MCP tools and they execute successfully (neo4j, perplexity). Re-confirmed in v2.1.50 with 8 concurrent bg agents. May be stale doc or refer to *direct* MCP (without ToolSearch). Via ToolSearch: **MCP WORKS in background**.

### ⚠️ `anyOf` Schema API 400 Bug — ROOT CAUSE FOUND (2026-02-24)

**Bug**: Custom agents spawned via Task tool crash with `tools.N.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level`.

**Root cause**: **Perplexity MCP v0.14.0** (and possibly AlphaVantage HTTP MCP) expose tool schemas with `anyOf` at the top level. The Anthropic Messages API rejects these. When Claude Code builds the tool array for subagents, it includes ALL registered MCP tool schemas — even if the agent doesn't use them.

**Why main thread works but subagents fail**: Main thread uses ToolSearch with deferred loading — bad schemas are never sent upfront. Subagent spawn assembles the full tool array including bad MCP schemas → API 400.

**The FIX**: Add explicit `tools:` field to agent frontmatter that excludes bad MCP tools.

| Test | `tools:` field | Perplexity MCP included? | Result |
|------|---------------|-------------------------|--------|
| `guidance-extract` (has `tools:` with only neo4j + built-in) | ✅ YES | ❌ Excluded | ✅ **SPAWNS OK** |
| `test-memory-autopreload` (no `tools:` field) | ❌ NO | ✅ Included (inherited) | ❌ API 400 |
| `test-memory-autopreload` (`tools:` added mid-session) | ⚠️ Added but cached | ✅ Session snapshot uses old version | ❌ API 400 |

**Key insight**: Session-start snapshot captures agent frontmatter at startup. Mid-session edits to agent files are NOT picked up by Task tool. Must start fresh session after adding `tools:`.

**Permanent fix checklist**:
1. Add `tools:` field to ALL custom agents — list only the tools they need (no Perplexity/AlphaVantage MCP)
2. Start a fresh session so Task tool snapshot picks up the new `tools:` fields
3. Alternatively: downgrade Perplexity MCP to v0.2.2 (pre-anyOf schema) or disable it

**GitHub issues**: #4886, #5973, #10606, #3940, #4753, #4295, #13898 — 15+ issues filed, never fully fixed in subagent spawn path.

**Cross-model verification (2026-02-21):**

| Model | BG + ToolSearch MCP expansion | Tool uses before crash | Error |
|-------|------------------------------|----------------------|-------|
| Haiku | ❌ API 400 | 0 | `tools.14.custom.input_schema: ...` |
| Sonnet | ❌ API 400 | 3 | `tools.15.custom.input_schema: ...` |
| Opus 4.6 | ❌ API 400 | 2 | `tools.15.custom.input_schema: ...` |

**Foreground agents are unaffected** — their tool serialization path handles these schemas correctly.

**Workarounds**:
1. Use **foreground mode** for agents that need MCP tools (multiple Task calls in one message still run in parallel)
2. Pre-load MCP tools via `allowed-tools` in agent frontmatter (avoids ToolSearch expansion)
3. Use Skill tool to invoke a skill that has MCP in its `allowed-tools` (delegation pattern)

**Note**: Agents that DON'T call ToolSearch work fine in background — the 12 built-in tools have no schema issues. The bug only triggers when ToolSearch expands the tool set mid-session.

### Round 2 Confirmation (2026-02-21, 8 parallel bg agents, v2.1.50)

| Test | Mode | Finding | Evidence |
|------|------|---------|----------|
| Tool inventory | BG (Task) | 10+ tools confirmed. TaskCreate/TaskList/AskUser BLOCKED. | `test-bg-v250-tools.txt` |
| MCP access | BG (Task) | ToolSearch→neo4j→`[{"test":1}]` ✅ | `test-bg-v250-tools.txt` |
| Skill invocation | BG (Task) | test-re-arguments invoked in forked mode ✅ | `test-bg-v250-skill.txt` |
| Memory (project) | BG (Task) | Canary file exists, NOT in system prompt. Still broken. | `test-memory-v250-verify.txt` |
| Memory (local) | BG (Task) | Dir exists, R/W works. Old canary persists. No preload. | `test-memory-v250-local.txt` |
| Memory (user) | BG (Task) | Dir created, R/W works. No preload. | `test-memory-v250-user.txt` |
| bg:true CLI | --agent | BLOCKED: nested session guard | `test-bg-v250-frontmatter-meta.txt` |

**New findings**:
- Skill `test-re-model-field` API 400 in bg: `"input_schema does not support oneOf/allOf/anyOf"` — schema issue, not bg restriction.
- **Haiku silent failure**: `model: haiku` in agent frontmatter + `--agent` flag → exit 0 but **empty output** (no stdout, no stderr, no files written). Sonnet override works. Haiku may be too small to follow complex agent instructions reliably via `--agent`.
- **`background: true` + `memory: project` combo**: Both fields coexist. Memory dir created, R/W works. No memory instructions in prompt. Agent reported `BG_MEMORY_COMBO=WORKS`.

### Test Files Created (2026-02-21)

| File | What It Tests |
|------|--------------|
| `.claude/agents/test-bg-fm-tasktools.md` | bg:true + tools whitelist for TaskCreate |
| `.claude/agents/test-bg-fm-vs-runtime.md` | bg:true tool inventory comparison |
| `.claude/agents/test-mem-same-agent-verify.md` | Memory auto-preload same agent |
| `test-outputs/test-bg-general-tools-v250.txt` | BG agent (Task tool) tool inventory |
| `test-outputs/test-fg-general-tools-v250.txt` | FG agent (Task tool) tool inventory |
| `test-outputs/test-bg-frontmatter-v250.txt` | bg:true basic functionality |
| `test-outputs/test-bg-fm-vs-runtime.txt` | bg:true (--agent) full tool set |
| `test-outputs/test-bg-fm-tasktools.txt` | bg:true + TaskCreate via --agent |
| `test-outputs/test-mem-same-agent-verify.txt` | Same-agent memory re-invocation |
| `test-outputs/test-memory-v250-verify.txt` | Cross-agent memory check |
| `test-outputs/test-memory-v250-local.txt` | Local scope retest |
| `test-outputs/test-memory-v250-user.txt` | User scope retest |
| `test-outputs/test-memory-verify-general-v250.txt` | General agent memory check |
| `test-outputs/test-bg-v250-tools.txt` | **Round 2**: BG tool inventory (8 parallel agents) |
| `test-outputs/test-bg-v250-skill.txt` | **Round 2**: BG skill invocation |
| `test-outputs/test-bg-v250-frontmatter-meta.txt` | **Round 2**: bg:true via CLI (nested guard blocked) |
| `test-outputs/test-bg-v250-memory-combo.txt` | **Round 2**: bg+memory combo via CLI |
| `test-outputs/test-bg-opus-tools-v250.txt` | **Opus retest**: BG tool inventory (12 tools confirmed) |
| `test-outputs/test-bg-opus-mcp-v250.txt` | **Opus retest**: BG MCP access (API 400 — anyOf schema bug) |
| `test-outputs/test-bg-opus-memory-v250.txt` | **Opus retest**: Memory auto-preload (STILL BROKEN) |

### Key Decisions (Updated)

| Decision | Before (v2.1.47) | After (v2.1.50) | Impact |
|----------|------------------|------------------|--------|
| BG agent tools | 11 tools | **12 tools (+EnterWorktree)** | Minor improvement |
| FG agent tools | 20 tools | **40 tools** (7 base + 33 deferred incl. TaskCreate, MCP) | Major — FG agents have full deferred tools |
| `--agent` tools | N/A | **27 tools (FULL SET)** | bg:true has no effect via CLI |
| BG agent TaskCreate | ❌ BLOCKED | ❌ **STILL BLOCKED v2.1.52** (all models, all spawn methods, Skill workaround also fails) | No change — use foreground pattern |
| `tools` field vs bg restriction | Unknown | **CONFIRMED: Cannot expand bg base set** (Actual = Requested ∩ BG-Allowed) | Don't rely on `tools` to grant TaskCreate in bg mode |
| Memory auto-preload | ❌ BROKEN | ✅ **NOW WORKING** (v2.1.52, all 3 scopes, Task tool + `--agent`) | **MAJOR FIX** — works via Task tool with `tools:` field |
| BG + MCP (ToolSearch) | ✅ Works (v2.1.47) | ⚠️ **Perplexity MCP v0.14.0 schema** causes API 400 | FIX: Add `tools:` field excluding bad MCP. Or downgrade Perplexity to v0.2.2 |
| `background: true` frontmatter | N/A | ✅ **NEW** — scheduling directive only | Auto-sets run_in_background; no independent tool restriction |
| `isolation: worktree` frontmatter | N/A | ✅ **NEW** — git isolation | Use for parallel file-modifying agents |
| Agent discovery | N/A | **Session-start snapshot** (persists through continuations) | Must start brand-new session to discover new agents |

### Fresh-Session Retest Results (2026-02-21, Opus 4.6)

Custom agents created in the previous session (`test-bg-fm-tasktools`, `test-bg-fm-vs-runtime`, `test-mem-same-agent-verify`) were **still NOT available** as Task tool `subagent_type` values in the continued session. This confirms: the Task tool agent list is a **session-start snapshot** that persists through conversation continuations — it is NOT re-scanned on continuation.

**Workaround used**: `unset CLAUDECODE && claude -p --agent <name>` via Bash for frontmatter-specific tests; `general-purpose` subagent via Task tool for Task-tool-specific tests.

#### 3-Tier Tool Hierarchy (CONFIRMED, Opus 4.6)

| Spawn Method | Total Tools | Task Tools | Team Tools | Interactive | Nesting |
|-------------|------------|-----------|-----------|------------|---------|
| `claude --agent` (CLI) | **27** | ✅ All 4 | ✅ All 3 | ✅ All 3 | ✅ Task/TaskOutput/TaskStop |
| Task tool (foreground) | **40** (7 base + 33 deferred) | ✅ All 4 (deferred) | ✅ All 3 (deferred) | ❌ None | ❌ No Task spawner |
| Task tool (background) | **12** (base only, no deferred) | ❌ None | ❌ None | ❌ None | ❌ None |

Evidence files:
- `--agent`: `test-bg-fm-vs-runtime-opus.txt` (27 tools)
- FG Task: `test-fg-task-tool-memory-opus.txt` (21 tools)
- BG Task: `test-bg-task-tool-memory-opus.txt` (12 tools)

**Key insight**: `background: true` in agent frontmatter does NOT restrict tools when run via `--agent` (agent IS the main session). Tool restrictions are applied by the **Task tool runtime** based on `run_in_background`, not by the frontmatter field.

#### Q1: Does `tools` frontmatter override bg tool restriction?

**DEFINITIVELY NO.** (Confirmed via Task tool, 2026-02-24)

| Spawn | Agent | tools: field | Delivered | TaskCreate? |
|-------|-------|-------------|-----------|-------------|
| `--agent` | `test-bg-fm-tasktools` | 9 tools (incl. Task*) | 27 (full) | ✅ Works |
| Task (FG, no bg:true) | `general-purpose` | N/A | 40 (7 base + 33 deferred) | ✅ Works |
| Task (FG, bg:true agent) | `test-bg-fm-tasktools` | 9 tools (incl. Task*) | **5** | ❌ Stripped |
| Task (BG, bg:true agent) | `test-bg-fm-tasktools` | 9 tools (incl. Task*) | **5** | ❌ Stripped |

**Tool Set Algebra**: `Actual = Requested ∩ BG-Allowed`. The `tools:` field can RESTRICT (Edit was bg-allowed but not requested → not delivered) but CANNOT EXPAND beyond what the bg runtime permits. Task tools are unconditionally stripped.

**Key finding**: `background: true` in frontmatter FORCES bg mode even when Task tool spawns in foreground. Both FG and BG spawns of the same agent got identical 5-tool sets.

Evidence: `test-bg-tasktools-background-v252.txt`, `test-bg-tasktools-foreground-v252.txt`, `test-fg-tool-inventory-v252.txt`

#### Q2: Does bg:true frontmatter differ from run_in_background on Task?

**YES — fundamentally different mechanisms:**

| Aspect | `background: true` (frontmatter) | `run_in_background: true` (Task param) |
|--------|----------------------------------|---------------------------------------|
| When applied | At agent definition time | At spawn time |
| Effect via `--agent` | **None** — full 27 tools | N/A (not a Task tool parameter) |
| Effect via Task tool | Auto-sets `run_in_background` | Directly controls bg mode |
| Tool restriction | **None by itself** — only via Task runtime | **Yes** — 12 tools |
| Can override? | N/A | No (enforced at runtime) |

**Conclusion**: `background: true` is a **scheduling directive** that tells the Task tool to auto-enable `run_in_background`. It does NOT independently restrict tools. The tool restriction comes from the Task tool's runtime bg mode, not the frontmatter field.

#### Q3: Memory auto-preload via Task tool?

**❌ BROKEN** — identical to `--agent` results.

| Spawn Method | Model | Memory in Context | File on Disk | Evidence |
|-------------|-------|------------------|-------------|----------|
| Task tool (foreground) | Opus | ❌ NO | ✅ Exists | `test-fg-task-tool-memory-opus.txt` |
| Task tool (background) | Opus | ❌ NO | ✅ Exists | `test-bg-task-tool-memory-opus.txt` |
| `--agent` (same agent) | Opus | ❌ NO | ✅ Exists | `test-mem-same-agent-verify-opus.txt` |

**Definitive**: Memory auto-preload is broken across ALL spawn methods, ALL models, ALL scopes. The spawn mechanism (Task tool vs `--agent`) makes no difference.

#### Agent Discovery: Session-Start Snapshot (CONFIRMED)

Custom agents created during a conversation are NOT available as Task tool `subagent_type` values, even in a continuation session. The agent type list is:
- Scanned at original session start
- Preserved through conversation continuations
- NOT refreshed when `.claude/agents/` directory changes

**Implication**: To spawn custom agents via Task tool, you must start a **brand new** `claude` session (not a continuation).

#### Updated Test Files

| File | What It Tests |
|------|--------------|
| `test-outputs/test-bg-fm-tasktools-opus.txt` | **Fresh**: bg:true + tools whitelist (Opus, --agent) |
| `test-outputs/test-bg-fm-vs-runtime-opus.txt` | **Fresh**: bg:true 27-tool inventory (Opus, --agent) |
| `test-outputs/test-mem-same-agent-verify-opus.txt` | **Fresh**: Same-agent memory re-invocation (Opus, --agent) |
| `test-outputs/test-fg-task-tool-memory-opus.txt` | **Fresh**: FG Task agent memory+tools (Opus, Task tool) |
| `test-outputs/test-bg-task-tool-memory-opus.txt` | **Fresh**: BG Task agent memory+tools (Opus, Task tool) |

### Remaining Unknowns

| Question | Status |
|----------|--------|
| Does `tools` frontmatter override bg tool restriction via Task tool? | ❌ **CONFIRMED NO** (2026-02-24). Actual = Requested ∩ BG-Allowed. Evidence: `test-bg-tasktools-{background,foreground}-v252.txt` |
| Does bg:true + isolation:worktree combo work via Task? | **Untested** — needs brand-new session for agent discovery. |

---

*Updated: 2026-02-24 | v2.1.52 definitive tests | 3-tier hierarchy corrected (27/40/12) — FG has 33 deferred tools incl. TaskCreate | tools field = INTERSECTION (confirmed, not just inferred) | bg:true forces BG mode even in FG spawn | Memory auto-preload FIXED + Task tool spawn confirmed | anyOf root cause = Perplexity MCP v0.14.0 bad schemas, FIX = add tools: field | Task→Task nesting still blocked v2.1.52*

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
