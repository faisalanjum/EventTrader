# DataSubAgents Architecture Plan (PIT-Safe)

**Created**: 2026-02-05  
**Status**: Draft (reviewed + iterated)

## Goal

Build a catalog of **data subagents** (Task-parallel) that lets any primary agent fetch:
- **Internal data**: Neo4j (reports, news, transcripts, XBRL, entities)
- **External data**: Perplexity + future APIs (SEC full-text search, slide decks, etc.)

With a single, minimal PIT switch (`--pit`) and **automatic recovery** (retry) when contamination is detected.

---

## Terminology (keep this consistent)

- **Data subagent**: `.claude/agents/*.md` agent spawned via Task for parallel fetch (e.g., `.claude/agents/neo4j-news.md`).
- **Cookbook**: reference file with query patterns/examples/edge cases, loaded deterministically via `Read`.
- **Skill (shared reference)**: `.claude/skills/<name>/SKILL.md` — reusable instruction packs auto-loaded into subagents via `skills:` frontmatter. May be user-invocable or non-invocable (`user-invocable: false`). Examples: `news-queries` (query patterns), `pit-envelope` (envelope contract), `evidence-standards` (citation rules).
- **PIT mode**: enforce “publicly available ≤ PIT timestamp” (see `.claude/filters/PIT_REFERENCE.md`).
- **PIT gate**: deterministic allow/block checker (`pit_gate.py`) used from hooks when `--pit` is present.

---

# 1) Requirements (prioritized)

## P0 (must-have)

1. **PIT on-demand**: same data interface works with or without PIT (minimal args).
2. **Non-strict PIT**: contamination is *not* a hard stop; it triggers **retry + query adjustment**, while still never leaking contaminated content.
3. **Fail-closed on leakage**: if PIT is enabled, either return **validated clean** output or return an error/empty result—never “maybe-clean”.
4. **Determinism via hooks**: prefer hooks for validation / gating; avoid “trust me” prompt-only rules.
5. **Citations everywhere**:
   - Neo4j: cite node type + identifier + availability date.
   - External: cite URL + publication date (or best available proxy).
6. **Minimalism**: smallest set of scripts/docs that still guarantees P0.

## P1 (should-have)

7. **Parallel by default where possible** (Task fan-out); accept sequential only when the platform forces it.
8. **Single response contract**: machine-checkable output shape (JSON-first).
9. **Resume/refine**: follow-up queries should reuse prior context (`resume: agent_id`, paging, narrowed windows).
10. **Extensible catalog**: adding a new source should be a repeatable pattern (agent + cookbook + validator config).

## P2 (good-to-have)

11. **Standardized docs per source**: known gaps, schema notes, examples.
12. **Thinking capture**: best-effort audit trail across layers.
13. **Optional external LLM augmentation** (need-to-use basis only).

---

# 2) Platform constraints (from `.claude/plans/Infrastructure.md`)

- Task fan-out is **parallel** from main conversation; Skill-to-Skill chains are **sequential**.
- Task spawning is **blocked in forked skill contexts** → design parallel fetch at top level.
- `allowed-tools` / `disallowedTools` are **not enforcement** → PIT correctness cannot rely on frontmatter alone.

---

# 3) References (tested + inspiration)

## Tested patterns (keep behavior, not necessarily the exact code)

- **Parallel fetch (Task fan-out)**: `.claude/plans/Infrastructure.md` (parallel Task from main conversation; blocked in forks).
- **Iterative refinement (`resume: agent_id`)**: `.claude/skills/earnings-attribution/SKILL.md` (subagent resume protocol).
- **Hook-based gating style**: `.claude/hooks/validate_pit_hook.sh` (example of “allow” vs “block” decision output).

## Existing artifacts (inspiration only; do not depend on them for correctness)

- PIT semantics: `.claude/filters/PIT_REFERENCE.md`
- Citation + domain boundaries: `.claude/skills/evidence-standards/SKILL.md` (canonical location; no cookbook migration needed)
- Legacy prediction-safe proxy: `.claude/skills/filtered-data/SKILL.md` → routes to another data skill, runs `.claude/filters/validate.sh`, returns only `CLEAN`.
- Existing validators (candidate to replace): `.claude/filters/validate.sh`, `.claude/filters/validate_neo4j.sh`, `.claude/filters/validate_perplexity.sh`
- Existing hook examples (candidate to replace): `.claude/hooks/validate_pit_hook.sh`

## Minimalism guardrails

- **One** response contract (JSON-first).
- **One** PIT gate (`pit_gate.py`) + retry loop (fail-closed when PIT is enabled).
- Add new docs/scripts only if they directly enforce P0 requirements.

---

# 4) Architecture (minimal + reliable)

## 4.1 Trust boundary rule

**Neo4j WHERE-clause filtering is an optimization, not the trust boundary.**
The trust boundary is the **PIT gate** when PIT is enabled:
- Subagents return structured JSON with explicit publication/availability fields.
- Hooks run `pit_gate.py` to allow/block deterministically.

Implementation note (keep it minimal): the first `pit_gate.py` can reuse existing validators (`.claude/filters/validate*.sh`) internally, but the *public contract* is “PIT gate decides allow/block”.

This protects against "forgot to add WHERE" or "returned the wrong field" mistakes.

## 4.2 PIT validation semantics (critical distinction)

**PIT validates PUBLICATION DATE, not content dates.**

The question PIT answers: "Was this information publicly available at the PIT timestamp?"

| Correct | Incorrect |
|---------|-----------|
| Check when the article/filing was **published** | Check dates **mentioned** in the content |
| `article.created <= PIT` | `any_date_in_text <= PIT` |

**Example**: An article published 2024-02-15 discussing "management raised 2030 guidance to $5B" is **not contaminated** if PIT is 2024-02-16. The 2030 date is content, not publication metadata.

**Key fields per source** (see `.claude/filters/PIT_REFERENCE.md`):
- Neo4j News: `n.created` (publication timestamp)
- Neo4j Report: `r.created` (SEC filing acceptance datetime)
- Neo4j Transcript: `t.conference_datetime` (call date)
- External (Perplexity): requires normalization of publication date into `published_at/published_date`

## 4.3 External dates: what we validate vs what we ignore

For external sources, the output may contain many dates:
- **Publication/availability metadata** (what we must validate for PIT)
- **Dates mentioned in content** (can include future years; these are NOT PIT contamination)

**Rule**: `pit_gate` validates only the **publication/availability timestamp field(s)** in the returned JSON, never arbitrary dates inside `snippet/body/text`.

That means external data agents must output a normalized publication field, e.g.:
- `published_at` (ISO8601 datetime when available)
- or `published_date` (YYYY-MM-DD when time is unavailable)

If an external item has **no reliable publication metadata**, it must be dropped in PIT mode (fail-closed) or returned as a gap.

### External PIT compliance: 3 supported lanes (plug-and-play)

We support **three** external PIT patterns. All three feed the **same** deterministic gate.

Canonical gating field (recommended for all lanes):
- Each `data[]` item should include `available_at` (ISO8601) as the **single canonical timestamp** the gate validates.
- Source-specific fields (`created`, `published_at`, `published_date`, `reportedDate`, time-series timestamps, …) should be mapped/derived into `available_at`.

**Lane 1 — Internal structured (Neo4j)**
- Availability timestamp comes from a known schema field (`n.created`, `r.created`, `t.conference_datetime`, …).
- Optional pre-filter in query (WHERE) for efficiency.
- `pit_gate.py` validates deterministically.

**Lane 2 — External structured-by-provider (schema enforced)**
- Use when the provider/tool can reliably emit a structured per-item date field.
- Examples:
  - A provider that already returns structured search results with a per-result `date`.
  - A direct API where we can request structured output (e.g., `response_format` / JSON schema).
- Data agent maps provider metadata → `published_at/published_date` and returns the JSON envelope.
- `pit_gate.py` validates deterministically.

**Lane 3 — External unstructured/messy (LLM normalizer + deterministic gate)**
- Use when the provider output is free text / mixed dates / inconsistent schemas.
- Add a **Normalizer step** whose *only job* is to transform raw output → the standard JSON envelope:
  - Extract candidate items/values.
  - Attach `available_at` per item from provider-backed metadata (not content dates).
  - Drop anything unverifiable (or return it as a gap).
- Then run `pit_gate.py`:
  - If any item is unverifiable or post-PIT → block + retry (non-strict PIT).
  - Final fallback is a **clean gap**: explicit “unverifiable as-of PIT”.

Important: “two sources agree” can increase confidence, but it is **not** a substitute for `published_at/published_date` metadata. PIT compliance is still decided by the gate.

### Perplexity notes (provider-specific)

Perplexity’s API supports **Structured Outputs** via `response_format: { type: "json_schema", ... }`, which can enforce a schema that includes `published_at/published_date` so the gate stays deterministic.

References:
- Structured Outputs: `https://docs.perplexity.ai/docs/grounded-llm/output-control/structured-outputs`
- Perplexity SEC guide (search_mode="sec"): `https://docs.perplexity.ai/guides/sec-guide`
- Perplexity MCP server: `https://docs.perplexity.ai/docs/getting-started/integrations/mcp-server`
- Perplexity Search API (`POST /search`): `https://docs.perplexity.ai/api-reference/search-post`

Operational notes (from Perplexity docs; treat as constraints):
- Links inside JSON may be unreliable; prefer using the API-provided `citations` / search result objects where possible.
- Reasoning models may prepend `<think>...</think>` before the JSON; downstream parsing must handle this if used.

Repository reality check (current state):
- `utils/perplexity_search.py` calls `https://api.perplexity.ai/chat/completions` with optional `search_mode="sec"` and returns **plain text** + a “Sources:” URL list.
- It does **not** currently pass `response_format` or emit per-item `published_at/published_date`.
- Our Perplexity “SEC” capability in this repo is **not MCP-based**; it is `search_mode="sec"` in `utils/perplexity_search.py`.

Treatment in this architecture:
- **PIT mode**: Perplexity responses are only admissible as *data* if they emit structured per-item `published_at/published_date`. Otherwise, drop those items and retry (or use Neo4j/sec-api).
- **Open mode**: Perplexity can return summaries, but keep the same JSON envelope (summary as a field) and include citations for auditability.
- **SEC-specific (`perplexity-sec`)**: our current implementation is a Perplexity API wrapper (`search_mode="sec"`) that returns narrative text + EDGAR URLs. Until it emits per-filing acceptance time (`published_at` = EDGAR accepted datetime), treat it as a **locator only**:
   - Use it to discover likely filings/URLs/accession numbers.
   - Then fetch the filing from **Neo4j (`neo4j-report`) or sec-api** to obtain the authoritative `created/filedAt` timestamp and content for PIT-safe use.

Concise conclusion (Perplexity interfaces):
- **MCP (`mcp__perplexity__*`)**: assume tool schemas are fixed; do **not** depend on being able to pass `response_format` unless we fork the MCP server.
- **Direct API (`utils/perplexity_search.py`)**: we control payloads, so we *can* add `response_format` (optional), but still fail-closed if publication metadata isn’t provider-backed.
- **Search API (`POST /search`)**: already returns structured results with a per-result `date` field → best default for PIT-safe external web results.

### External sources in general (not Perplexity-specific)

Not every external API supports structured outputs. Our rule stays the same:
- The **data agent** must normalize each item into JSON and include `published_at/published_date` from provider metadata.
- If the provider doesn’t supply publication metadata, PIT mode must fail-closed (drop + gap) and retry with a different source.

Special case: APIs that are structured by design (e.g., SEC search APIs, slide deck APIs) must still supply a reliable availability timestamp; if they only return a PDF without metadata, treat as “not PIT-safe” until a timestamp source is defined.

## 4.4 Hook type decision (PIT enforcement)

Use `type: command` + a single **Python** gate script for *all* sources.

| Use | Hook Type | Why |
|-----|-----------|-----|
| PIT allow/block | `type: command` | Deterministic, minimal, timezone-correct, no LLM “judgment” |
| Optional retry hints | `type: command` | Gate can output a precise reason to guide the agent’s retry |

**Hook scope preference (for clarity, not required):**
- First try **agent-level hooks** for data subagents (if supported by your Claude Code version/runtime).
- If agent-level hooks are not supported/reliable, use **project-level hooks** in `.claude/settings.json` (this is known to work broadly and is the minimal single control plane).

**Matcher rule (avoid accidental blocking):**
- Do **not** match all tools (e.g., `matcher: "*"`) for PIT gating. In PIT mode, the gate expects a data envelope; matching non-data tools (Write/Edit/general Bash) would incorrectly block unrelated operations.
- Prefer **specific matchers** that target only data retrieval tools used by that data subagent (Neo4j read, Perplexity tools, provider adapters).
- If a data agent must use `Bash` for a PIT-aware wrapper, it should treat `Bash` as *data retrieval only* (no miscellaneous commands) so `matcher: "Bash"` remains safe in that agent.

**Why not agent-based hooks for PIT enforcement?**
- PIT is a **correctness boundary** (P0). LLM-based gating can be nondeterministic and may mis-identify which date is “publication”.
- The hook’s job is “allow/block + reason”, not “interpret the world”.
- If we need LLM reasoning, it should happen in the **data agent** that produces the structured JSON, not in the gatekeeper.

**Command hook implementation**: `pit_gate.py` (stdlib-only) reads hook JSON input, extracts:
- PIT timestamp (must be present in tool input; see PIT propagation rule below)
- source name (neo4j-news / perplexity-search / etc.)
- publication fields from the tool response JSON (`created`, `conference_datetime`, `published_at`, `published_date`, etc.)

Then it returns either “allow” or “block with reason” (so the agent retries).

**PIT propagation rule (required for correctness)**:
- If the subagent was invoked with `--pit ...`, it must propagate that PIT timestamp into **every** downstream tool call so the PostToolUse hook can read it.
- Use explicit PIT parameters in tool input (for example: `tool_input.parameters.pit`). Do not rely on free-text PIT prefixes.

**Write-safety rule (required for correctness):**
- Neo4j writes must be impossible even if the model tries: block `mcp__neo4j-cypher__write_neo4j_cypher` via hook (do not rely on `disallowedTools`).

## 4.5 Implementation specs (hook I/O, matchers, wrapper)

These specs turn the architecture into concrete, implementable contracts.

### Hook I/O contract

Based on tested repo patterns (`.claude/hooks/validate_pit_hook.sh`, `.claude/hooks/block_bash_guard.sh`):

**Input (stdin JSON):**
```json
{
  "tool_name": "mcp__neo4j-cypher__read_neo4j_cypher",
  "tool_input": { "parameters": { "pit": "2024-02-15T16:00:00-05:00" }, "query": "MATCH ..." },
  "tool_response": { "stdout": "..." }
}
```
- `tool_input`: object with tool parameters (`.command` for Bash, `.query` for MCP, etc.)
- `tool_response`: object or string; for Bash, use `.stdout`

**Output (stdout):**
- Allow: `{}`
- Block: `{"decision":"block","reason":"PIT violation: 2024-02-20 > 2024-02-15"}`

**Exit code:** Always `0` (blocking is via stdout JSON, not exit code)

### `pit_gate.py` behavioral spec (deterministic)

**PIT detection (tool input):**
- PIT is **ON** only when a PIT timestamp is present in the tool input.
- Prefer an explicit field (when available): `tool_input.parameters.pit`
- If PIT is absent → allow (`{}`) (open mode).

**Tool output reading:**
- Bash: `tool_response.stdout`
- MCP tools: `tool_response` may be a string or object; handle both.

**Validation (PIT mode, fail-closed):**
- Parse tool output as JSON.
- Expect the **standard JSON envelope** with `data[]`.
- For each item in `data[]`:
  - `available_at` must exist and be full ISO8601 datetime with timezone (date-only is PIT non-compliant).
  - `available_at_source` must exist and be one of:
    - `neo4j_created`
    - `edgar_accepted`
    - `time_series_timestamp`
    - `provider_metadata`
  - `available_at <= PIT`
- If any item is missing/violating → block with a precise reason (so the agent can retry).

**Output (stdout):**
- Allow: `{}`
- Block: `{"decision":"block","reason":"..."}`
- Exit code: always `0`

### Tool matchers (per-agent, specific)

Each data subagent matches only its retrieval tools:

| Agent | Matcher |
|-------|---------|
| neo4j-news | `mcp__neo4j-cypher__read_neo4j_cypher` |
| neo4j-report | `mcp__neo4j-cypher__read_neo4j_cypher` |
| neo4j-transcript | `mcp__neo4j-cypher__read_neo4j_cypher` |
| neo4j-xbrl | `mcp__neo4j-cypher__read_neo4j_cypher` |
| neo4j-entity | `mcp__neo4j-cypher__read_neo4j_cypher` |
| neo4j-vector-search | `mcp__neo4j-cypher__read_neo4j_cypher` |
| perplexity-search | `mcp__perplexity__perplexity_search` |
| perplexity-ask | `mcp__perplexity__perplexity_ask` |
| perplexity-research | `mcp__perplexity__perplexity_research` |
| perplexity-reason | `mcp__perplexity__perplexity_reason` |
| bz-news-api | `Bash` (dedicated agent, Bash = `pit_fetch.py` wrapper only) |
| external-adapter | `Bash` (dedicated agent, Bash = wrapper only) |

**Write-block matcher** (all agents): `mcp__neo4j-cypher__write_neo4j_cypher` via PreToolUse

### Wrapper script location + interface

**Location:** `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py`

**Interface:**
```bash
python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source <source> --pit <ISO8601> [source-specific args...]
```

**Examples:**
```bash
python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source alphavantage --pit 2024-02-15T16:00:00-05:00 EARNINGS symbol=AAPL
python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source yahoo --pit 2024-02-15T16:00:00-05:00 consensus symbol=AAPL
python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source bz-news-api --pit 2024-02-15T16:00:00-05:00 --themes macro --limit 50
```

**Output:** Standard JSON envelope (§4.7) with `available_at` per item

**Wrapper hard contract (required for reliability):**
- STDOUT must be **JSON only** (no prose).
- Every `data[]` item must include:
  - `available_at` (full ISO8601 datetime with timezone)
  - `available_at_source` (one of the canonical values above)
  - source evidence fields required by that provider path
- In PIT mode:
  - If an item cannot produce a provider-backed `available_at`, it must be dropped from `data[]` and recorded in `gaps[]`.
  - If an item is post-PIT, it must be dropped+gap (wrappers do not return post-PIT items).

**Adding new source:** Add handler function in `pit_fetch.py`, define timestamp field mapping, done.

### `available_at` field mapping (canonical)

| Source | Provider field | Maps to `available_at` | Notes |
|--------|---------------|------------------------|-------|
| Neo4j News | `created` | ✅ | Publication timestamp |
| Neo4j Report | `created` | ✅ | SEC filing acceptance datetime |
| Neo4j Transcript | `conference_datetime` | ✅ | Call date |
| Neo4j XBRL | parent Report's `created` | ✅ | Inherit from filing |
| Neo4j Entity (prices/dividends/splits) | `Date.market_close_current_day` (normalized) | ✅ | Temporal: derive `available_at` from Date node's market close (handles DST + early closes). Company metadata: open mode pass-through (no temporal provenance). 65 dividend gaps (44 orphan + 21 holiday NULL close = 1.48% of 4,405). |
| Perplexity Search API (`POST /search`) | `date` | ⚠️ | Date-only is not PIT-compliant by itself; must resolve provider-backed publish datetime or gap |
| Perplexity MCP search (`mcp__perplexity__perplexity_search`) | ❌ none reliable | ⚠️ | Treat as Lane 3: normalize from citations/URLs, else gap |
| Perplexity Ask/Research/Reason | normalized or gap | ⚠️ | Lane 3: must extract from citations |
| Alpha Vantage TIME_SERIES_* | per-datapoint timestamp | ✅ | Filter to `<= PIT`; keep only timestamps with full datetime semantics |
| Alpha Vantage EARNINGS | `reportedDate` | ⚠️ | Often date-only; PIT mode requires a verifiable datetime path or gap |
| Alpha Vantage EARNINGS_ESTIMATES | ❌ not provable | ⚠️ | Historical PIT consensus not guaranteed; use only when PIT ≈ now, else gap |
| Benzinga News API | `created` | ✅ | Use `provider_metadata`; drop items with unparseable/missing timestamp |
| Yahoo | provider-specific | ⚠️ | Use Lane 3: URL/citation -> WebFetch timestamp extraction; if unverifiable datetime, gap |

### Hook YAML examples

**PostToolUse gating (data retrieval):**
```yaml
hooks:
  PostToolUse:
    - matcher: "mcp__neo4j-cypher__read_neo4j_cypher"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
```

**PreToolUse write-block (stop before executing):**
```yaml
hooks:
  PreToolUse:
    - matcher: "mcp__neo4j-cypher__write_neo4j_cypher"
      hooks:
        - type: command
          command: "echo '{\"decision\":\"block\",\"reason\":\"Neo4j writes forbidden\"}'"
```

### Bash gating note

If an agent uses `matcher: "Bash"` for PIT gating:
- That agent must use Bash **only** for wrapper calls (no mkdir, ls, echo, etc.)
- Otherwise harmless commands get blocked (their output isn't a data envelope)

**Recommended:** Create dedicated adapter agents per provider where Bash = wrapper only.

**Belt-and-suspenders:** `pit_gate.py` can check `tool_input.command`; if not a wrapper invocation, immediately return `{}` (allow).

---

## 4.6 Standard invocation contract

All data subagents must accept:
- `--pit <ISO8601>` (optional; enables PIT mode)

If `--pit` is absent, the call is **open** (no PIT gating). No separate `--mode` flag.

## 4.7 Standard response contract (JSON-first)

All data subagents return **JSON only** (no prose). The envelope has exactly two top-level keys:

```json
{
  "data": [
    {
      "available_at": "2024-11-07T13:01:00-05:00",
      "available_at_source": "neo4j_created",
      "id": "bzNews_12345",
      "title": "...",
      "...domain-specific fields..."
    }
  ],
  "gaps": [
    {"type": "no_data", "reason": "No news found for ticker before PIT", "query": "..."}
  ]
}
```

**`data[]` item requirements** (validated by `pit_gate.py`):
- `available_at`: full ISO8601 datetime with timezone. Required per item in PIT mode.
- `available_at_source`: one of `neo4j_created`, `edgar_accepted`, `time_series_timestamp`, `provider_metadata`. Required per item in PIT mode.
- `available_at <= PIT` must hold. Violation → block.
- Domain-specific fields vary by agent (see each agent's query skill).

**`gaps[]`**: always present (use `[]` if no gaps). Each gap object has `type` (`no_data`, `pit_excluded`, `unverifiable`), `reason`, and optionally `query`.

**Open mode**: same envelope format. `available_at` fields are optional (pit_gate.py is a no-op when no PIT in tool input).

## 4.8 Retry (non-strict PIT)

When PIT is enabled and contamination is detected:
1. **Do not return contaminated payload**.
2. Adjust query (narrow window / add explicit "before PIT" clause / reduce sources).
3. Retry up to `.claude/filters/rules.json:max_retries` (currently 2).
4. If still contaminated, return a **clean empty** response with explicit `gaps` explaining why (preferred) or an error.

Lane 3 retry rule (external messy sources):
1. Normalize with LLM (transform-only) into the standard envelope.
2. If publish datetime is missing/unverifiable/non-compliant, retry with narrower query/alternate source.
3. Max retries: 2.
4. If still non-compliant, return clean gap.

---

# 5) Catalog model: agents + shared references (recommended)

We do **not** require “a Skill per subagent”.

## Design rule (minimal + reliable)

- **Subagent prompt** (`.claude/agents/*`) contains only irreducible invariants:
  - JSON-only response contract + required fields
  - PIT gate usage (`pit_gate.py`) + fail-closed behavior
  - Domain boundaries + citation requirements
- **Shared query patterns/examples/edge cases** can live in either:
  - `.claude/skills/<domain>/SKILL.md` (auto-loaded via agent frontmatter `skills:`)
  - `.claude/cookbooks/data/<domain>.md` (loaded deterministically via `Read`)
- Per domain, keep one canonical source of truth to avoid duplicated, drifting instructions.

## Data subagent checklist (use for every new `.claude/agents/*` data agent)

Each data subagent must:
- Accept `--pit <ISO8601>` (optional; PIT mode on/off).
- In PIT mode, propagate PIT into **every** downstream retrieval tool input (so hooks can read it).
- Return **JSON only** in the standard envelope, with `available_at` per `data[]` item.
- Use per-agent **specific matchers** for gating (do not use `matcher: "*"`) and include a PreToolUse write-block for Neo4j write.
- Fail-closed: if it cannot produce a reliable `available_at` for an item in PIT mode, it must drop+gap (never "maybe-clean").

## `evidence-standards` skill — UPDATED 2026-02-11

Rewritten to v2: 4 universal rules (source-only, exact values, traceability, derived values) + domain boundary with date-anchor exception. Removed stale content (prose format, PIT markers, rigid domain table). Now loaded by all 13 data sub-agents (Neo4j 7 + Benzinga 1 + Perplexity 5 + Alpha Vantage 1). Canonical location: `.claude/skills/evidence-standards/SKILL.md`.

## Where reference files live

- Skill-based shared references: `.claude/skills/<domain>/SKILL.md`
- Cookbook-style references: `.claude/cookbooks/data/<domain>.md`
- Standards: `.claude/cookbooks/standards/<name>.md`

Migration note: no forced migration is required. Existing shared references under `.claude/skills/` can remain canonical; if moved to cookbooks, migrate per-domain and keep only one canonical copy.

## Parallelism note

Task fan-out parallelism is unaffected by whether the agent reads reference files or has skills listed; parallelism is driven by Task spawning at the top level.

## External data adapters (Alpha Vantage, etc.)

Some external MCP tools do not accept a `pit` parameter, which makes deterministic PIT gating difficult because hooks need PIT present in the tool input.

Minimal, 100% reliable pattern for PIT-critical external data:
- Use a **local wrapper script** (Python) that accepts `--pit`, calls the provider API/MCP, and returns **already-sanitized JSON** (truncated to `<= PIT`, forbidden fields removed).
- Invoke that wrapper via Bash with an explicit `--pit` so hooks can deterministically gate it.
- Use the same wrapper interface for any future external sources (standardization).

Alpha Vantage specifics:
- We **do not** solve PIT by “just blocking Alpha Vantage” in PIT mode. We solve it by **wrapping + sanitizing** so the model never sees post-PIT data.
- For price/series tools (TIME_SERIES_*): wrapper filters datapoints to `timestamp <= PIT`.
- For consensus/earnings tools:
  - If used for earnings-event PIT (PIT at/after filing time), `EARNINGS` can provide historical estimates at earnings time; wrapper must remove any forbidden return/price data.
  - If used for earlier-than-event PIT backtests, beware “as-of” ambiguity; wrapper must fail-closed if the provider cannot guarantee as-of-PIT values.

Lane 3 timestamp extraction policy (decided):
- Allowed tools for extracting provider-backed publish datetimes from citations/URLs:
  - `WebFetch` for deterministic page metadata extraction
  - Optional low-cost LLM pass (Haiku) for extraction/parsing assistance only
- Gate remains authoritative: if datetime is not verifiable after extraction, drop+gap.

---

# 6) Implementation plan (step-by-step)

## Phase 0 — Build order (do this in order)

1. ~~Create `.claude/hooks/pit_gate.py` (the only PIT gate).~~ **DONE** — 37/37 tests pass. Handles `params.pit`, MCP response format, single-record array unwrap.
2. Create `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py` (the only external wrapper entrypoint). **PARTIAL** — exists with `bz-news-api` source (386 lines). Needs `alphavantage` source handler.
3. ~~Update `.claude/agents/neo4j-news.md` end-to-end (reference implementation).~~ **DONE** — see Phase 2.
4. ~~Create an external adapter data agent (Bash = wrapper only) and gate it.~~ **DONE** — `bz-news-api` agent with PIT gate.
5. ~~Run the minimal tests below before expanding coverage.~~ **DONE** — Neo4j allow test passed. Perplexity + Alpha Vantage tests pending (Phase 4).

## Phase 1 — Common scaffolding (**DONE**)

1. ~~**Define the JSON contract**~~ — `pit-envelope` skill (`.claude/skills/pit-envelope/SKILL.md`): envelope schema, field mappings, forbidden keys, retry rules.
2. ~~**Build one PIT gate**~~ — `.claude/hooks/pit_gate.py` (stdlib-only Python, 37/37 tests in `test_pit_gate.py`).
3. ~~**Wire PIT gate via hooks**~~ — agent-level PostToolUse hooks (proven in 3 agents: neo4j-news, neo4j-vector-search, bz-news-api).

## Minimal tests (must pass before adding more sources)

1. ~~**Neo4j allow**: run `neo4j-news` with `--pit` and confirm gate allows clean data.~~ **PASSED** — 3 live tests (PIT-clean, PIT-gap, open mode).
2. **Perplexity MCP**: in PIT mode, MCP search/ask/reason/research must normalize to items with reliable `available_at` or return a clean gap (no unverifiable items). **PENDING** (Phase 4).
3. **Alpha Vantage wrapper**: run `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source alphavantage --pit ... TIME_SERIES_* ...` and confirm only datapoints `<= PIT` are returned. **PENDING** (Phase 4).

## SDK run checklist (top-level orchestrator)

Assumption: the orchestrator runs as the **primary/top-level session** (not a forked skill), both in Claude Code and via the Claude Agent SDK.

- **Parallelism**: use Task fan-out from the top level to spawn data subagents in parallel (Task tool is blocked only in forked skill contexts).
- **PIT toggle (SDK + CLI)**:
  - **Open mode (no PIT)**: omit `--pit` entirely → hooks/gate treat the run as open and do not block on PIT.
  - **PIT mode**: pass `--pit <ISO8601>` → PIT must be propagated into downstream retrieval tool inputs so hooks can validate.
- **Automation** (SDK): set `permission_mode="bypassPermissions"` to avoid interactive permission prompts.
- **Task tools** (SDK): use `tools={'type':'preset','preset':'claude_code'}` and enable tasks via `CLAUDE_CODE_ENABLE_TASKS=1`.
- **Optional persistence**: set `CLAUDE_CODE_TASK_LIST_ID` to a stable value for cross-session resumability (note: `.claude/settings.json` can override env vars).
- **Background spawn caution**: avoid `run_in_background: true` unless needed; it can change which task tools are available to spawned agents.

## Phase 2 — Build the first reference data subagent (**DONE**)

**neo4j-news** is the reference implementation. Completed deliverables:

- `.claude/agents/neo4j-news.md` — agent with hooks (PreToolUse write-block + PostToolUse pit_gate), skills (`neo4j-schema`, `news-queries`, `pit-envelope`, `evidence-standards`), workflow (PIT/open mode branching), PIT response contract
- `.claude/skills/news-queries/SKILL.md` — 487 lines, 40 code blocks. Reorganized into 8 sections: Core Access (6), Return & Impact (9), INFLUENCES Targets (4), Cross-Domain (2), Analytical Examples (15), PIT-Safe Envelope (4). Vector search removed (separate agent). Notes trimmed to News-unique items (neo4j-schema duplication removed).
- `.claude/skills/pit-envelope/SKILL.md` — shared envelope contract (all agents)
- `.claude/hooks/pit_gate.py` — PIT gate (37/37 tests)
- Live integration tests: PIT-clean (12 items), PIT-gap (empty data), open mode (5 items with returns) — all **PASSED**

**Reference pattern for remaining agents**:
1. Add hooks to agent frontmatter (copy from neo4j-news — identical PreToolUse + PostToolUse)
2. Add `pit-envelope` to skills list
3. Add PIT query section to query skill (same `collect({available_at, ...})` template)
4. Reorganize query skill if needed (core/analytical/PIT sections)
5. Run 3 live tests (PIT-clean, PIT-gap, open mode)

## Phase 3 — Extend Neo4j coverage

Upgrade remaining domains using the same contract + hook:
- ~~`.claude/agents/neo4j-report.md`~~ **DONE** — hooks wired, `pit-envelope` skill added, PIT-safe envelope queries in report-queries skill (5 queries), `r.created` → `available_at` (`edgar_accepted`)
- ~~`.claude/agents/neo4j-transcript.md`~~ **DONE** — hooks wired, `pit-envelope` skill added, PIT-safe envelope queries in transcript-queries skill (4 queries), `t.conference_datetime` → `available_at` (`neo4j_created`)
- ~~`.claude/agents/neo4j-xbrl.md`~~ **DONE** — hooks wired, `pit-envelope` skill added, PIT-safe envelope queries in xbrl-queries skill (3 queries), parent Report `r.created` → `available_at` (`edgar_accepted`)
- ~~`.claude/agents/neo4j-entity.md`~~ **DONE** — hooks wired, `pit-envelope` skill added, PIT-safe envelope queries in entity-queries skill (5 queries). Hybrid approach: temporal data (prices/dividends/splits) uses `Date.market_close_current_day` normalized to ISO8601 → `available_at` (`time_series_timestamp`); company metadata uses open mode pass-through (no `pit` in params). Coverage: prices 100%, splits 100%, dividends 98.52% (65 gaps: 44 orphan + 21 NULL close on holidays, of 4,405 total)
- ~~`.claude/agents/neo4j-vector-search.md`~~ **DONE** — semantic search across News + QAExchange; model: sonnet; Bash for embedding generation via `.claude/skills/earnings-orchestrator/scripts/generate_embedding.py`; hooks wired; queries inline (no separate skill)

## Phase 4 — External sources (same pattern)

Add/upgrade:
- `.claude/agents/perplexity-search.md` (PIT via `pit_gate.py`, retry)
- SEC full-text search adapter scaffold (HTTP wrapper first; MCP optional later)
- Slide deck API adapter (earningscall.biz)

### SEC full-text adapter scaffold (placeholder, implementation-ready structure)

Target path pattern:
- Wrapper handler in `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py` under `--source sec_full_text`
- Optional dedicated agent: `.claude/agents/sec-fulltext-adapter.md` (Bash = wrapper only)

Contract alignment (same as all external sources):
- Input: `python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source sec_full_text --pit <ISO8601> ...`
- Output: standard JSON envelope with `data[]`, `gaps[]`, `available_at`, `available_at_source`
- Gate: `pit_gate.py` PostToolUse validation + retry (max 2) + clean gap fallback

TODO (leave as placeholders until API wiring step):
- [TODO] Finalize exact SEC full-text endpoint + auth method
- [TODO] Finalize request parameters accepted by `--source sec_full_text`
- [TODO] Finalize `available_at` mapping field (must be provider-backed publish/accepted datetime)
- [TODO] Add deterministic test case: one PIT-pass and one PIT-fail/gap case

---

# 7) Decisions (explicitly tracked)

1. **Prediction vs attribution policy (decided)**:
   - **Prediction**: PIT-enabled and filtered (use `--pit` everywhere; only PIT-validated items may pass; gaps are allowed when unverifiable).
   - **Attribution**: open mode (no PIT gating; everything allowed).
   - Implementation note: `filtered-data` remains available as a legacy/transitional pattern during migration, but the **primary path** is `--pit` directly through data subagents + hooks (this plan).
2. **External LLM normalizer usage (decided via allowlist)**:
   - Purpose: Lane 3 only — normalize messy external outputs into the standard JSON envelope with per-item `available_at`, then let `pit_gate.py` decide allow/block.
   - **Allowed** (PIT mode only): Perplexity MCP tools (`mcp__perplexity__perplexity_search`, `mcp__perplexity__perplexity_ask`, `mcp__perplexity__perplexity_research`, `mcp__perplexity__perplexity_reason`) and Yahoo adapter outputs when they lack provider-backed per-item timestamps.
   - **Not allowed by default**: any new/unknown external source. Add it explicitly to this allowlist before using the normalizer (keeps behavior deterministic and audit-friendly).
   - PIT enforcement remains deterministic: the normalizer is a transformer; `pit_gate.py` is the gatekeeper (no agent-based hook gating).
3. **`available_at_source` provenance tagging (decided)**:
   - Required in PIT mode for every `data[]` item.
   - Allowed values: `neo4j_created`, `edgar_accepted`, `time_series_timestamp`, `provider_metadata`.
   - `pit_gate.py` fails-closed when missing/invalid.
4. **`neo4j-entity` PIT policy (resolved 2026-02-15)**:
   - **Temporal data** (prices, dividends, splits): derive `available_at` from `Date.market_close_current_day` — real datetime+tz field that handles DST (`-0400`/`-0500`) and early closes (`13:00:00`). Normalize to strict ISO8601 via Cypher string ops (space→T, insert colon in offset).
   - **Company metadata** (ticker, name, sector, industry, mkt_cap): no temporal provenance exists on Company node. Use open mode pass-through (omit `pit` from query params → gate allows as open mode). Current-snapshot, not PIT-verified.
   - **Gap cases**: 44 orphan dividends (no Date link) + 21 holiday declarations (NULL `market_close_current_day`) = 65 gaps (1.48% of 4,405 dividends). Splits: 0 gaps.
   - `available_at_source`: `time_series_timestamp` for all temporal entity data.

---

# 8) Decided (previously open)

1. **Hook format** (decided in §4.4):
   - All sources: `type: command` + `pit_gate.py` (Python, stdlib-only) for deterministic allow/block based on structured publication fields.

*Plan Version 2.5 | 2026-02-15 | Phase 0-2 DONE. Phase 3: 5/5 DONE (all Neo4j agents PIT-complete). Agent count: 13 (Neo4j 6 + AV 1 + BZ 1 + Perplexity 5). PIT-complete: 7/13 (neo4j-news, neo4j-vector-search, bz-news-api, neo4j-report, neo4j-transcript, neo4j-xbrl, neo4j-entity).*

---

# 9) Cross-Doc Discrepancy Check (Implementation Note)

Before closing any implementation pass for this plan, run a final consistency check against `.claude/plans/earnings-orchestrator.md` for these known discrepancy classes:

1. ~~Data-layer lifecycle status (`Draft` vs `done/assumed complete`).~~ **RESOLVED 2026-02-09**: earnings-orchestrator.md updated to "IN PROGRESS, out of scope for this doc" with Phase status.
2. ~~Agent catalog alignment.~~ **RESOLVED 2026-02-09**: Both docs aligned at 13 agents (Neo4j 6, AV 1, BZ 1, Perplexity 5). `neo4j-vector-search` added to both. earnings-orchestrator.md agent table now shows PIT status per agent.
3. `perplexity-sec` behavior (locator-only vs direct data source). **OPEN** — resolve when Phase 4 begins.
4. PIT propagation contract (`--pit` in subagent prompt vs explicit downstream tool parameter, e.g., `tool_input.params.pit` / `tool_input.parameters.pit`). **OPEN** — validated for Neo4j Lane 1; needs validation for Lane 2/3.
5. Response-shape integration (DataSubAgents JSON envelope `data[]/gaps[]` + `available_at` vs orchestrator merged text bundle fields). **OPEN** — envelope proven in production; orchestrator text rendering not yet built.
6. Legacy `filtered-data` policy wording (deprecated vs transitional availability). **OPEN** — both docs say deprecated.
7. ~~`neo4j-entity` PIT timestamp policy for date-only fields.~~ **RESOLVED 2026-02-15**: Use `Date.market_close_current_day` (real datetime+tz) for temporal data, open mode pass-through for company metadata. See §7 Decision #4.

Decision rule for implementers:
- `.claude/plans/earnings-orchestrator.md` is the final word for orchestrator integration behavior and consumer-facing contracts.
- If any discrepancy is still ambiguous or conflicts with implementation reality, stop and ask the user before proceeding.

---

# 10) Agent Body Standardization & Data Agent Linter

Added 2026-02-15 after audit of 3 DONE agents revealed duplicated content and 6 real bug classes.

## 10.1 Keep architecture as-is

- No new shared runtime file.
- Centralized layer remains: `pit-envelope` + `evidence-standards` + `pit_gate.py`.

## 10.2 Remove duplication from DONE agents

- In the 3 DONE agents (`neo4j-news`, `neo4j-vector-search`, `bz-news-api`), remove embedded PIT Response Contract example blocks.
- Replace each with one line: "See pit-envelope skill for envelope contract, field mappings, and forbidden keys."
- Keep agent workflows per-agent (do not template workflow logic).

## 10.3 Build remaining 10 agents as thin agents

- Only: frontmatter + domain-specific workflow + domain notes.
- Do not duplicate common contract/rules text already in shared skills.
- Target: ~15-20 lines of domain-specific body content.

## 10.4 Update plan docs for human builders

- Copy-paste frontmatter templates are documented below (not in §6 Phase 2, which is marked DONE).
- §6 Phase 2 "Reference pattern for remaining agents" remains unchanged (it describes the 5-step process; these templates supplement it with exact YAML).
- Keep runtime behavior unchanged.

### Frontmatter template (Neo4j Lane 1 agents)

```yaml
---
name: neo4j-<domain>
description: "..."
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
model: opus
permissionMode: dontAsk
skills:
  - neo4j-schema
  - <domain>-queries
  - pit-envelope
  - evidence-standards
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

### Frontmatter template (External Bash-wrapper agents)

```yaml
---
name: <source>-api
description: "..."
tools:
  - Bash
model: opus
permissionMode: dontAsk
skills:
  - <source>-queries
  - pit-envelope
  - evidence-standards
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
---
```

## 10.5 Add a lint-only guard (no generator, no autofix)

- New file: `.claude/skills/earnings-orchestrator/scripts/lint_data_agents.py`.
- Scope: only the 13 data agents (`.claude/agents/neo4j-*.md`, `bz-news-api.md`, `perplexity-*.md`, `alphavantage-*.md`) and their `skills:` entries.
- Deterministic, stdlib-only, no network.
- ~100 lines.

## 10.6 Linter rules (final)

| Rule | Severity | What it checks |
|------|----------|---------------|
| R1 | ERROR | Each data agent must include `evidence-standards` in `skills:` |
| R2 | ERROR | No wildcard PIT hook matchers (no `"*"` / catch-all in hooks) |
| R3 | ERROR | PIT-DONE agents must be fully compliant (see per-agent breakdown below) |
| R5 | ERROR | File paths referenced in data agent and their associated skill body content must resolve to existing files |
| R6 | ERROR | Hook commands must include `$CLAUDE_PROJECT_DIR` only when command references project paths (`.claude/` or `scripts/`). Do not apply to pure `echo` hooks |
| R7 | ERROR | Deprecated skills blocklist for data agents = `filtered-data` only. Do not block or warn on `skill-update` |

### R3 per-agent breakdown (PIT-DONE list)

- **neo4j-news**: `pit-envelope` in skills, Neo4j write-block PreToolUse, `pit_gate.py` PostToolUse on `mcp__neo4j-cypher__read_neo4j_cypher` matcher.
- **neo4j-vector-search**: same as neo4j-news.
- **bz-news-api**: `pit-envelope` in skills, `pit_gate.py` PostToolUse on `Bash` matcher.
- **neo4j-report**: same as neo4j-news. PIT field: `r.created` → `available_at` (source: `edgar_accepted`).
- **neo4j-transcript**: same as neo4j-news. PIT field: `t.conference_datetime` → `available_at` (source: `neo4j_created`).
- **neo4j-xbrl**: same as neo4j-news. PIT field: parent Report `r.created` → `available_at` (source: `edgar_accepted`).
- **neo4j-entity**: same as neo4j-news. PIT field: `Date.market_close_current_day` → `available_at` (source: `time_series_timestamp`). Metadata queries use open mode pass-through.

## 10.7 What is explicitly dropped

- No "planned agents warnings" rule (R4 dropped — 10 permanent warnings = noise).
- No `--strict-planned` mode.
- No blocklist entry for `skill-update` (not deprecated, just unused).

## 10.8 Operational behavior

- **PIT-DONE list** is maintained in linter config. As each agent migrates, add it to PIT-DONE list so it gets strict R3 validation immediately.
- **Output format**:
  - `ERROR [RULE] path: message`
  - `WARN  [RULE] path: message` (only if truly actionable/non-permanent)
  - Summary: `PASS`/`FAIL`, counts, checked agents.
- **Exit codes**: `0` pass, `1` fail.

## 10.9 Expected end state

- Thin agent bodies (~15-20 lines domain-specific).
- Single source of truth for common behavior in existing shared layer (`pit-envelope`, `evidence-standards`, `pit_gate.py`).
- Automatic regression protection against real, historical failure modes.
