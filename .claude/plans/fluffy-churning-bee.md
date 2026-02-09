# Data Sub-Agent PIT Envelope: neo4j-news Reference Implementation

**Parent**: `.claude/plans/DataSubAgents.md` (Phase 2)
**Prereq**: `.claude/hooks/pit_gate.py` (Phase 0, DONE)
**Status**: Plan v2.0

## Context

Data agents currently return ad-hoc text/JSON. The earnings orchestrator needs a **standard JSON envelope** from every data agent, validated by `pit_gate.py`, to enforce PIT safety deterministically. This plan builds the shared infrastructure (DRY across all 3 PIT lanes and all 11+ agents) and reworks `neo4j-news` as the reference implementation.

## 3-Lane Analysis

All 3 lanes converge on the **same envelope** and the **same gate**. No lane-specific infrastructure needed.

| Lane | Examples | What Produces `available_at` | Shared Infra |
|------|----------|------------------------------|-------------|
| 1 — Internal (Neo4j) | news, report, transcript, xbrl, entity | Cypher alias (`n.created AS available_at`) | pit-envelope skill + pit_gate.py |
| 2 — External structured | alphavantage, time series | Wrapper maps provider field | pit-envelope skill + pit_gate.py |
| 3 — External unstructured | perplexity | LLM normalizer extracts | pit-envelope skill + pit_gate.py |

**Verdict**: One shared skill + one gate = unified. Lane differences are agent-specific (field mappings, query patterns) and belong in each agent's files. No lane-specific shared code.

---

## Step 1: Update `pit_gate.py` — MCP Format + params.pit Extraction

**File**: `.claude/hooks/pit_gate.py`

### 1a. Add `params.pit` extraction (CRITICAL)

**Why**: The Neo4j MCP tool `read_neo4j_cypher` accepts `query: str` + `params: Optional[dict]` (confirmed from `/home/faisal/neo4j-mcp-server/.../server.py:115-118`). When the agent passes PIT as a Cypher parameter, it lands in `tool_input.params.pit`, but `extract_pit` currently only checks `tool_input.parameters.pit` and `tool_input.pit` — it misses `params.pit`.

**Change** to `extract_pit` (line 110-126): Add `tool_input.params.pit` check. New priority order:
1. `tool_input.parameters.pit` (generic nested — keep for non-Neo4j tools)
2. `tool_input.params.pit` (Neo4j MCP Cypher parameter dict)
3. `tool_input.pit` (flat fallback)
4. Bash `--pit` flag

### 1b. Handle MCP response format

**Why**: MCP `read_neo4j_cypher` returns `[TextContent(type="text", text=json_str)]`. The `_read` function (server.py:62-66) returns `json.dumps([r.data() for r in records])` — always a JSON array of record dicts. When Cypher returns `RETURN items AS data, [] AS gaps`, the MCP response text is `[{"data":[...],"gaps":[]}]` — a 1-element array wrapping the envelope.

**Change** to `extract_payload` (line 129-139):
1. If `tool_response` is a list and `tool_response[0]` has key `text` → extract `tool_response[0]["text"]` as payload string
2. If `tool_response` is a dict and has `result` key → extract `tool_response["result"][0]["text"]`
3. Fall through to existing behavior for other formats

**Change** to `main()` — after JSON parsing (line 280-288):
If parsed payload is a list with exactly 1 element that is a dict with `data` key → unwrap to that dict. This handles the Cypher single-record wrapping.

### 1c. New test cases

Add to `.claude/hooks/test_pit_gate.py`:
- T33: `params.pit` extraction → PIT detected correctly
- T34: MCP `[{"type":"text","text":"[{\"data\":[...]}]"}]` wrapping → allow
- T35: MCP wrapping with violation → block
- T36: Single-record array unwrap `[{"data":[...],"gaps":[]}]` → allow
- T37: Multi-record array (ambiguous) → block with `PIT_MISSING_ENVELOPE`

**Verification**: `python3 .claude/hooks/test_pit_gate.py` — all 37 tests must pass.

---

## Step 2: Create Shared Skill `pit-envelope`

**File**: `.claude/skills/pit-envelope/SKILL.md` (NEW, ~90 lines, `user-invocable: false`)

**Why**: Every data agent (all 3 lanes, all 11+ agents) must know the same envelope contract. Auto-loaded via `skills:` frontmatter — same proven pattern as `evidence-standards` and `skill-update`. Claude Code docs confirm `.claude/skills/` is the recommended location for reusable instruction packs preloaded into subagents. (Note: DataSubAgents.md §5 line 460 was overly narrow on this point; update that doc to align with platform behavior.)

**Contents**:

### 2a. Envelope Schema
```json
{
  "data": [
    {
      "available_at": "<ISO8601 datetime+tz>",
      "available_at_source": "<canonical source tag>",
      "...domain-specific fields..."
    }
  ],
  "gaps": [
    {"type": "no_data|pit_excluded|unverifiable", "reason": "...", "query": "..."}
  ]
}
```

### 2b. `available_at_source` Canonical Values
`neo4j_created`, `edgar_accepted`, `time_series_timestamp`, `provider_metadata`

### 2c. Field Mapping Table

| Agent | Source Field | Maps to `available_at` | `available_at_source` | Notes |
|-------|-------------|------------------------|----------------------|-------|
| neo4j-news | `n.created` | direct | `neo4j_created` | Full datetime+tz |
| neo4j-report | `r.created` | direct | `edgar_accepted` | Full datetime+tz |
| neo4j-transcript | `t.conference_datetime` | direct | `neo4j_created` | Full datetime+tz |
| neo4j-xbrl | parent Report `r.created` | join | `edgar_accepted` | Requires MATCH to parent Report |
| neo4j-entity (price) | `d.date` | **date-only: gap in PIT mode** | — | See §2i |
| neo4j-entity (div) | `div.declaration_date` | **date-only: gap in PIT mode** | — | See §2i |
| neo4j-entity (split) | `s.execution_date` | **date-only: gap in PIT mode** | — | See §2i |
| alphavantage EARNINGS | `reportedDate` | **date-only: verify or gap** | `provider_metadata` | See §2i |
| alphavantage (series) | per-datapoint timestamp | direct | `time_series_timestamp` | Full datetime |

### 2d. Forbidden Keys (NEVER include in PIT mode output)
`daily_stock`, `hourly_stock`, `session_stock`, `daily_return`, `daily_macro`, `daily_industry`, `daily_sector`, `hourly_macro`, `hourly_industry`, `hourly_sector`

**Where these live by relationship type**:
- `INFLUENCES` (News/Transcript → Company): `daily_stock`, `hourly_stock`, `session_stock`, `daily_macro`, `daily_industry`, `daily_sector`, `hourly_macro`, `hourly_industry`, `hourly_sector`
- `PRIMARY_FILER` (Report → Company): same return fields
- `HAS_PRICE` (Date → Company): `daily_return`

### 2e. PIT Propagation Rule
"When PIT is active, pass the PIT timestamp as a Cypher parameter named `pit` in the `params` dict. Example: `params: {ticker: 'NOG', pit: '2024-02-15T16:00:00-05:00'}`. The PostToolUse hook reads `tool_input.params.pit` for validation."

### 2f. Neo4j Envelope Query Pattern
```cypher
-- Template: wrap results into envelope via collect()
MATCH (...)
WHERE ... AND <source_field> <= $pit
WITH ... ORDER BY ...
WITH collect({
  available_at: <source_field>,
  available_at_source: '<tag>',
  ...domain fields (NO forbidden keys)...
}) AS items
RETURN items AS data, [] AS gaps
```

### 2g. Retry Rules
- On `PIT_VIOLATION_GT_CUTOFF`: tighten WHERE clause
- On `PIT_FORBIDDEN_FIELD`: remove offending RETURN columns
- On `PIT_MISSING_AVAILABLE_AT`: alias the correct source field
- Max 2 retries. If still blocked → return `{"data":[],"gaps":[{"type":"pit_excluded","reason":"..."}]}`

### 2h. Fail-Closed Rule
"If you cannot produce a reliable `available_at` for an item in PIT mode, drop it from `data[]` and record it in `gaps[]`. Never return 'maybe-clean' data."

### 2i. Date-Only Sources (neo4j-entity, some Alpha Vantage)
Date-only fields (e.g., `d.date`, `declaration_date`) cannot produce a full ISO8601 datetime+tz. Per DataSubAgents.md §4.3: "Date-only is not PIT-compliant by itself." These must be handled per-agent when their rework occurs. Options:
- Derive datetime from known market close time (e.g., 4PM ET for US equities)
- Use as locator only and gap if PIT-critical
- Document chosen approach per agent

---

## Step 3: Update `neo4j-news` Agent

**File**: `.claude/agents/neo4j-news.md`

### 3a. Frontmatter Changes

Add agent-level hooks for PIT gate AND write-block (per DataSubAgents.md §4.5 line 455):

```yaml
---
name: neo4j-news
description: "Query news articles from Neo4j with fulltext and vector search. Use proactively when analyzing news impact on stocks, finding news for a company/date range, searching news content, or attributing stock moves to news events."
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
model: opus
permissionMode: dontAsk
skills:
  - neo4j-schema
  - neo4j-news
  - evidence-standards
  - skill-update
hooks:
  PreToolUse:
    - matcher: "mcp__neo4j-cypher__write_neo4j_cypher"
      hooks:
        - type: command
          command: "echo '{\"decision\":\"block\",\"reason\":\"Neo4j writes forbidden\"}'"
  PostToolUse:
    - matcher: "mcp__neo4j-cypher__read_neo4j_cypher"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
---
```

Agent-level hooks are proven in production (3 agents: news-driver-bz, news-driver-web, news-driver-ppx). Preferred over project-level hooks per DataSubAgents §4.4.

### 3b. Frontmatter: Add `pit-envelope` to skills list

```yaml
skills:
  - neo4j-schema
  - neo4j-news
  - pit-envelope          # NEW — auto-loaded envelope contract
  - evidence-standards
  - skill-update
```

### 3c. Workflow Rewrite

Replace current workflow (lines 17-26):

```markdown
## Workflow
1. Parse request: ticker, date range, search type, PIT datetime (if provided)
2. Select query pattern from neo4j-news skill:
   - PIT mode: use PIT-safe envelope query (§PIT-Safe Envelope Queries in neo4j-news skill)
   - Open mode: use standard query, still return JSON envelope
4. Execute query via `mcp__neo4j-cypher__read_neo4j_cypher`:
   - PIT mode: pass `pit` in params dict: `{ticker: $ticker, pit: $pit, ...}`
   - Open mode: normal params (no `pit`)
5. If PIT mode and hook blocks: adjust query per pit-envelope retry rules (max 2 retries)
6. Return JSON-only envelope in ALL modes:
   - PIT mode: envelope validated by hook
   - Open mode: same envelope format, no PIT validation

## PIT Response Contract
Always return valid JSON envelope:
{
  "data": [...items with available_at + available_at_source...],
  "gaps": [...any missing data explanations...]
}
```

### 3d. Notes Update

Replace current Notes section:
```markdown
## Notes
- Relationship: `(n:News)-[:INFLUENCES]->(c:Company)` — returns live on INFLUENCES edges
- PIT mode: NEVER include INFLUENCES relationship properties (daily_stock, daily_macro, etc.) — forbidden
- PIT field mapping: `n.created` → `available_at`, source = `neo4j_created`
- Open mode: INFLUENCES properties allowed for impact analysis
- Filter NaN: `AND r.daily_stock IS NOT NULL AND NOT isNaN(r.daily_stock)` (open mode only)
- News.channels is JSON string: use `CONTAINS`
```

---

## Step 4: Add PIT Query Patterns to neo4j-news Skill

**File**: `.claude/skills/neo4j-news/SKILL.md`

Add a new section `## PIT-Safe Envelope Queries` after existing queries (which remain for open mode reference). All PIT queries use `<= $pit` (per DataSubAgents.md line 287: `available_at <= PIT`).

### 4a. Core PIT Query — News in Date Range

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $pit
WITH n ORDER BY n.created DESC
WITH collect({
  available_at: n.created,
  available_at_source: 'neo4j_created',
  id: n.id,
  title: n.title,
  teaser: n.teaser,
  channels: n.channels,
  created: n.created
}) AS items
RETURN items AS data, [] AS gaps
```

Key differences from open-mode version:
- `<= $pit` (PIT upper bound, boundary-inclusive per contract)
- `[:INFLUENCES]` with NO alias (no relationship properties needed)
- `collect({...})` wraps into `data[]` with `available_at` + `available_at_source`
- NO `daily_stock`, `daily_macro`, etc. in output (forbidden)

### 4b. PIT Query — News by Channel

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $pit
  AND n.channels CONTAINS $channel
WITH n ORDER BY n.created DESC
WITH collect({
  available_at: n.created,
  available_at_source: 'neo4j_created',
  id: n.id,
  title: n.title,
  channels: n.channels,
  created: n.created
}) AS items
RETURN items AS data, [] AS gaps
```

### 4c. PIT Query — Fulltext Search

```cypher
CALL db.index.fulltext.queryNodes('news_ft', $query)
YIELD node, score
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE node.created <= $pit
WITH node, score ORDER BY score DESC LIMIT 20
WITH collect({
  available_at: node.created,
  available_at_source: 'neo4j_created',
  id: node.id,
  title: node.title,
  teaser: node.teaser,
  created: node.created,
  ft_score: score
}) AS items
RETURN items AS data, [] AS gaps
```

### 4d. PIT Query — Semantic Vector Search

```cypher
CALL db.index.vector.queryNodes('news_vector_index', $k, $embedding)
YIELD node, score
MATCH (node)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE node.created <= $pit
WITH node, score ORDER BY score DESC
WITH collect({
  available_at: node.created,
  available_at_source: 'neo4j_created',
  id: node.id,
  title: node.title,
  teaser: node.teaser,
  created: node.created,
  vector_score: score
}) AS items
RETURN items AS data, [] AS gaps
```

### 4e. PIT Query — Latest News

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created <= $pit
WITH n ORDER BY n.created DESC LIMIT 10
WITH collect({
  available_at: n.created,
  available_at_source: 'neo4j_created',
  id: n.id,
  title: n.title,
  teaser: n.teaser,
  channels: n.channels,
  created: n.created
}) AS items
RETURN items AS data, [] AS gaps
```

### 4f. Section Notes

```markdown
### PIT-Safe Query Rules
- Use `n.created <= $pit` (boundary-inclusive; items at PIT are valid)
- NEVER include INFLUENCES relationship properties (daily_stock, daily_macro, etc.)
- Always include `available_at: n.created` and `available_at_source: 'neo4j_created'`
- Use `collect({...})` to produce `data[]` array
- Always `RETURN items AS data, [] AS gaps`
- Pass `pit` in the `params` dict alongside other Cypher parameters
- If query returns 0 results, the envelope `{"data":[],"gaps":[]}` passes the gate
```

---

## Step 5: Integration Verification

### 5a. Prerequisite: pit_gate.py Unit Tests

```bash
cd /home/faisal/EventMarketDB && python3 .claude/hooks/test_pit_gate.py
```
All 37 tests must pass (32 existing + 5 new).

### 5b. Live PIT-Clean Test

Spawn `neo4j-news` agent via Task with prompt:
"Find news for NOG before PIT 2025-01-01T00:00:00-05:00"

Verify:
1. MCP tool call includes `pit` in `params` dict in `tool_input`
2. Cypher results contain `data[]` with `available_at` and `available_at_source`
3. Hook allows clean data
4. No forbidden keys in response
5. Agent returns valid JSON envelope

### 5c. Live PIT-Gap Test

Spawn `neo4j-news` with PIT before all news for an obscure ticker. Verify:
1. Cypher returns empty `data[]`
2. Hook allows (empty is clean gap)
3. Agent returns `{"data":[],"gaps":[...]}`

### 5d. Open Mode Backward Compatibility

Spawn `neo4j-news` WITHOUT `--pit`. Verify:
1. Hook is a no-op (no `pit` in tool_input → allow)
2. Agent returns JSON envelope (same format as PIT mode, without PIT validation)
3. No breakage for live/attribution use cases

---

## Extension Pattern (How Next Agents Reuse This)

For each subsequent Neo4j agent (report, transcript, xbrl, entity):

1. **Add hooks to frontmatter**: Same PreToolUse write-block + PostToolUse PIT gate
2. **Add workflow**: "Use pit-envelope skill" + same PIT/open mode branching
3. **Add PIT query patterns**: Same `collect({available_at: <FIELD>, ...})` template, change:
   - Field name (`r.created`, `t.conference_datetime`, etc.)
   - Source tag (`edgar_accepted`, `neo4j_created`, etc.)
   - Forbidden key exclusions (varies by relationship type)
4. **Test**: Same 3 live tests (PIT-clean, PIT-gap, open mode)

For Lane 2 (alphavantage): Same pit-envelope skill, Bash wrapper + `--pit` flag.
For Lane 3 (perplexity): Same pit-envelope skill + normalizer step. Phase 4 scope.

---

## GPT Findings Verdict

| # | Finding | Verdict | Action |
|---|---------|---------|--------|
| 1 | pit-envelope should be cookbook, not skill | **REFUTED** | `.claude/skills/pit-envelope/SKILL.md` — same pattern as `evidence-standards`. Claude Code docs confirm skills for shared instruction packs. DataSubAgents.md §5 was overly narrow. |
| 2 | `params.pit` not in extract_pit | **ACCEPTED (CRITICAL)** | Add `tool_input.params.pit` to extraction |
| 3 | MCP response format unhandled | **ACCEPTED** | Step 1b: extract_payload update |
| 4 | Open mode should also return JSON | **ACCEPTED** | Both modes return envelope JSON |
| 5 | Write-block hook missing | **ACCEPTED** | PreToolUse hook added in Step 3a |
| 6 | `< $pit` should be `<= $pit` | **ACCEPTED** | Changed to `<= $pit` throughout |
| 7 | Hook path should use $CLAUDE_PROJECT_DIR | **ACCEPTED** | Fixed in Step 3a |
| 8 | "8 agents" overstated | **ACCEPTED** | Corrected: 3 production agents |
| 9 | Synthetic timestamps for date-only | **ACCEPTED** | Flagged in §2i; gap in PIT mode, resolve per-agent |
| 10 | Query location vs cookbook migration | **REFUTED** | Skills are appropriate for shared reference docs per Claude Code docs. Query patterns stay in skill (proven auto-loading). |

---

## Files Modified

| File | Action | Lines Changed |
|------|--------|--------------|
| `.claude/hooks/pit_gate.py` | EDIT | ~25 lines (extract_pit + extract_payload + unwrap) |
| `.claude/hooks/test_pit_gate.py` | EDIT | ~50 lines (5 new test cases) |
| `.claude/skills/pit-envelope/SKILL.md` | CREATE | ~90 lines |
| `.claude/agents/neo4j-news.md` | EDIT | ~35 lines (frontmatter + workflow + notes) |
| `.claude/skills/neo4j-news/SKILL.md` | EDIT | ~80 lines (PIT query section + vector search) |

## What This Does NOT Do

- Does NOT modify `.claude/settings.json` (hooks are agent-level)
- Does NOT touch other agents (one at a time per user request)
- Does NOT build `scripts/pit_fetch.py` (Lane 2, separate deliverable)
- Does NOT add LLM normalizer (Lane 3, Phase 4)
- Does NOT fabricate datetimes for date-only fields (gap instead, per DataSubAgents §4.3)

## DataSubAgents.md Correction (Minor)

DataSubAgents.md §5 line 460 states: "The `.claude/skills/` folder is reserved for actual invocable Skills." Per Claude Code docs (Feb 2026), `.claude/skills/` is the recommended location for reusable instruction packs preloaded into subagents, regardless of invocability. Existing pattern: `evidence-standards` and `skill-update` already use `user-invocable: false` and are loaded by all Neo4j agents. Update §5 to align with actual platform behavior.
