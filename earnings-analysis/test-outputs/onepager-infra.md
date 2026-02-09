## Data Layer & Platform Constraints

### Data Agents

**11 existing agents** (Neo4j + Perplexity + Alpha Vantage) all require PIT rework: each must return a standard JSON envelope with per-item `available_at` (ISO8601 datetime + timezone) and `available_at_source` provenance tag. **3 planned agents** to build: `web-search`, `sec-fulltext`, and `presentations` (earningscall.biz slide decks).

### PIT Enforcement

A single deterministic gate (`pit_gate.py`, stdlib-only Python) validates publication dates -- never content dates. It is **fail-closed**: missing or post-PIT `available_at` triggers block + retry (max 2), then clean gap. The gate runs as a `type: command` PostToolUse hook with per-agent specific matchers (no `matcher: "*"`).

Three PIT lanes feed the same gate:
1. **Internal structured (Neo4j)** -- `available_at` derived from known schema fields (`n.created`, `r.created`, `t.conference_datetime`); optional WHERE pre-filter for efficiency.
2. **External structured-by-provider** -- provider emits per-item dates; agent maps to `available_at`; gate validates.
3. **External messy (LLM normalizer)** -- raw output normalized into the JSON envelope via a transform-only pass; unverifiable items dropped as gaps.

### Platform Constraints (Shape the Entire Design)

| Constraint | Impact |
|---|---|
| **Task tool BLOCKED in forked skills** | All parallel data fetch must happen at orchestrator level via Task fan-out |
| **Task->Task nesting BLOCKED** | Flat fan-out only; sub-agents cannot spawn their own sub-agents |
| **Skills are SEQUENTIAL** | No parallel Skill calls; use Task for parallelism |
| **`disallowedTools` NOT enforced on skills** | Cannot rely on frontmatter restrictions; must use structural enforcement (hooks, wrappers) |
| **SubagentStop hooks CAN block** | Useful for output validation gates before results return to caller |
| **Agent hooks require Task spawn** | `--agent` flag does NOT activate frontmatter hooks; must spawn via Task tool |

### SDK Requirements

Automation runs require: `permission_mode="bypassPermissions"`, `tools={'type':'preset','preset':'claude_code'}`, and `CLAUDE_CODE_ENABLE_TASKS=1`. All workflows must be fully non-interactive -- `AskUserQuestion` is blocked in forked contexts. Optional: `CLAUDE_CODE_TASK_LIST_ID` for cross-session task persistence.
