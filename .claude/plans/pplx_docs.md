# Perplexity Docs + PIT Integration Notes

Updated: 2026-02-16
Purpose: Ground Perplexity implementation in official docs, then map it to our DataSubAgents PIT/Open architecture with minimal, centralized code.

---

## 0) Scope and sources

This note is based on:
- Official docs (requested):
  - https://docs.perplexity.ai/docs/getting-started/overview
  - https://docs.perplexity.ai/docs/getting-started/quickstart
  - https://docs.perplexity.ai/docs/cookbook
  - https://docs.perplexity.ai/api-reference/responses-post
  - https://docs.perplexity.ai/docs/search/quickstart
  - https://docs.perplexity.ai/docs/agent-api/quickstart
- Additional official references used for parameter precision:
  - https://docs.perplexity.ai/api-reference/search-post
  - https://docs.perplexity.ai/docs/search/filters
  - https://docs.perplexity.ai/guides/chat-completions-guide
  - https://docs.perplexity.ai/docs/openai-compatibility
  - https://docs.perplexity.ai/docs/getting-started/integrations/mcp-server
- Local implementation and plans:
  - `.claude/plans/DataSubAgents.md`
  - `.claude/plans/earnings-orchestrator.md`
  - `.claude/agents/perplexity-*.md`
  - `.claude/skills/perplexity-*/SKILL.md`
  - `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py`
  - `utils/perplexity_search.py`

---

## 1) Simple answers to your 5 decisions

1. "Can we reuse what we built for internal Neo4j agents?"
- Yes for the shared control plane (`pit-envelope`, `evidence-standards`, `pit_gate.py`, thin agent style).
- No for the runtime path. Neo4j uses MCP Cypher reads directly; Perplexity should use the external wrapper path (`Bash -> pit_fetch.py`) so PIT is explicit and deterministic.

2. "Keep one runtime entrypoint"
- Agree. Keep only one external runtime entrypoint: `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py`.

3. "Rework skills into PIT/Open command patterns + gaps policy"
- Agree. That matches DataSubAgents architecture and keeps agents thin.

4. "Do all Perplexity MCP (search/ask/reason/research) first?"
- Agree. Best batch order because 3 of them can share one chat handler with only model differences.

5. "Add to PIT_DONE only after tests and gate checks"
- Agree. Add each agent to `PIT_DONE` only when that agent passes its source tests and gate-integrated checks.

---

## 2) What Perplexity officially provides (verified)

### 2.1 API families
From Overview/Quickstart docs:
- Search API (`/search`) for ranked search results.
- Sonar API (`/chat/completions`) for grounded answer generation.
- Agent API (`/responses`) for tool-using agent workflows.

### 2.2 Search API (`POST /search`)
Key points from API reference + search quickstart/filters:
- Required: `query`.
- Common options: `max_results` (1-20), `search_domain_filter`, `search_recency_filter`, `country`, `locale`, `search_mode` (`web`, `academic`, `sec`).
- Date filters: `search_after_date_filter`, `search_before_date_filter`.
- Search filters doc specifies date format as `MM/DD/YYYY`.
- Returns structured results with metadata fields including URL/title/snippet/date.

### 2.3 Sonar (`POST /chat/completions`)
From Chat Completions guide + OpenAI compatibility:
- Supports `model` + `messages` and web grounding parameters.
- Supports search controls such as domain and recency filters.
- Supports date filters (`search_after_date_filter`, `search_before_date_filter`) and `search_mode` (including `sec`) in Sonar workflows.
- Used for ask/reason/research-style outputs.

### 2.4 Responses API (`POST /responses`)
From responses reference + agent quickstart:
- Supports `input`, `model`, `tools`, `tool_choice`, `temperature`, `stream`, token controls.
- Supports structured output controls (`response_format`) including schema-style output.
- Agent quickstart shows web-search/reasoning tool patterns.

### 2.5 MCP server integration
From MCP integration docs:
- Perplexity MCP exposes tools such as `perplexity_search`, `perplexity_ask`, `perplexity_reason`, `perplexity_research`.
- This is convenient for direct use, but our PIT architecture still requires deterministic PIT propagation and normalized envelopes.

---

## 3) Current repo state (as-is)

### 3.1 Agents and skills
Current `perplexity-*` agents are still old style:
- `perplexity-search`, `perplexity-ask`, `perplexity-reason`, `perplexity-research` use direct MCP tools and do not yet load `pit-envelope`.
- `perplexity-sec` uses Bash + `utils/perplexity_search.py`, but is not yet standardized to PIT wrapper contract.

### 3.2 Wrapper status
- `pit_fetch.py` currently supports only `bz-news-api` source.
- No Perplexity source handlers yet.

### 3.3 Plan alignment
Per `DataSubAgents.md` and `earnings-orchestrator.md`:
- Perplexity external agents are explicitly "Needs rework" / Phase 4 pending.
- External PIT pattern is already decided: wrapper + envelope + gate.

---

## 4) PIT/Open requirements applied to Perplexity

### 4.1 PIT mode (strict)
- Output must be JSON envelope only: `{ "data": [...], "gaps": [...] }`.
- Every `data[]` item must include:
  - `available_at` (ISO8601 datetime with timezone)
  - `available_at_source` (canonical source tag)
- Unverifiable items must not leak into `data[]`; they must become gaps.

### 4.2 Open mode
- No PIT cutoff enforcement.
- Same envelope shape still required for consistency.

### 4.3 Why wrapper path for Perplexity
- We need explicit PIT propagation in the tool call input that hook can see.
- We need one deterministic place to normalize provider outputs into envelope format.
- This is exactly the external adapter pattern already documented in DataSubAgents.

---

## 5) Centralized DRY architecture for Perplexity (recommended)

Use one shared runtime entrypoint (`pit_fetch.py`) with two Perplexity handlers for the 4 MCP-style agents:

1. `--source perplexity-search`
- For `perplexity-search` agent.
- Calls Perplexity Search API.
- Normalizes each result into a PIT/Open envelope item.

2. `--source perplexity-chat`
- For `perplexity-ask`, `perplexity-reason`, `perplexity-research`.
- Same handler; choose behavior via `--model` (`sonar-pro`, `sonar-reasoning-pro`, `sonar-deep-research`).
- Produces normalized envelope with provider-backed evidence fields and availability mapping policy.

Optional later:
3. `--source perplexity-sec`
- Keep separate because SEC mode has special locator behavior in current plan.

Shared helper functions (single implementation reused by all Perplexity handlers):
- PIT ISO8601 -> Perplexity date-filter format conversion (`MM/DD/YYYY`).
- Provider date -> `available_at` normalization policy.
- Uniform envelope builder.
- Uniform drop->gap accounting.

Result: write core logic once; all Perplexity agents reuse it.

---

## 6) Thin agent pattern (same as bz-news-api external archetype)

For each Perplexity external agent:
- `tools: [Bash]`
- `skills: [<domain-skill>, pit-envelope, evidence-standards]`
- PostToolUse hook on Bash -> `python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py`
- Body stays thin:
  - PIT mode command pattern
  - Open mode command pattern
  - gaps policy

This keeps behavior standardized and avoids duplicated contract text.

---

## 7) Perplexity-first implementation sequence (search/ask/reason/research)

Step 1. Add Perplexity handlers to `pit_fetch.py`
- Implement `perplexity-search` and `perplexity-chat` only.
- Keep SEC behavior out of this first batch unless explicitly included.

Step 2. Add focused tests in `test_pit_fetch.py`
- Perplexity-search: PIT-clean, PIT-gap, open.
- Perplexity-chat: PIT-clean, PIT-gap, open.
- Include malformed/undated item cases to verify drop->gap behavior.

Step 3. Rewrite 4 agents
- `perplexity-search`, `perplexity-ask`, `perplexity-reason`, `perplexity-research` to Bash-wrapper archetype.

Step 4. Rewrite 4 skills
- Each skill becomes command patterns + arguments + gaps policy (PIT/Open).

Step 5. Gate + lint rollout
- Run gate tests and source tests.
- Add each agent to `PIT_DONE` only after it passes.

---

## 8) Decisions to lock before coding

1. Date-only provider metadata mapping policy
- Need one explicit policy for converting provider date-only values to ISO8601 `available_at`.
- Must be consistent across all Perplexity handlers.

2. `perplexity-sec` scope for this batch
- Either defer to a dedicated follow-up pass (cleanest), or include now as locator-only.

3. Output granularity for chat-style agents
- Define whether wrapper emits only normalized source items, or source items plus a synthesized "answer" item.
- Keep one policy across ask/reason/research.

---

## 9) Recommended execution choice right now

Given current status and your priority:
- Start with Perplexity batch exactly in this order:
  1. `perplexity-search` handler and agent
  2. shared `perplexity-chat` handler
  3. `perplexity-ask`
  4. `perplexity-reason`
  5. `perplexity-research`
- Defer `perplexity-sec` to next pass unless you want SEC included in the same sprint.

This gives fastest throughput with the least code duplication and cleanest PIT/Open standardization.

---

## 10) Source links (for quick reuse)

- Overview: https://docs.perplexity.ai/docs/getting-started/overview
- Quickstart: https://docs.perplexity.ai/docs/getting-started/quickstart
- Cookbook: https://docs.perplexity.ai/docs/cookbook
- Search quickstart: https://docs.perplexity.ai/docs/search/quickstart
- Search filters: https://docs.perplexity.ai/docs/search/filters
- Search API reference: https://docs.perplexity.ai/api-reference/search-post
- Responses API reference: https://docs.perplexity.ai/api-reference/responses-post
- Agent API quickstart: https://docs.perplexity.ai/docs/agent-api/quickstart
- OpenAI compatibility: https://docs.perplexity.ai/docs/openai-compatibility
- Chat Completions guide: https://docs.perplexity.ai/guides/chat-completions-guide
- MCP server docs: https://docs.perplexity.ai/docs/getting-started/integrations/mcp-server

