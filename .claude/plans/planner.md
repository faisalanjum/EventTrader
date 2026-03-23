# Planner Module Plan

**Created**: 2026-02-08  
**Status**: Planning Scaffold  
**Parent Plan**: `earnings-orchestrator.md` (source of truth)

---

## Collaboration Protocol (LOCKED)

`CLAUDE INSTRUCTION`: Do not delete this section, the bot-to-bot notes, or any `CHATGPT`-prefixed block unless the user explicitly asks.

`CHATGPT NOTE`: This section consolidates the former "Active Collaboration Context", "CHATGPT - Collaboration Guard", "Shared Project Requirements", and "Session Start Rules" sections. All rules are preserved; none were deleted.

### Parallel Editing

1. Two bots may edit this plan in parallel: **ChatGPT** and **Claude**.
2. Re-read full doc before every response/edit. Before each reply, re-check parent-plan consistency and update the module doc directly.
3. Work on only this module per session — do not modify other module plans or the master plan.

### Source of Truth & Conflict Resolution

4. `earnings-orchestrator.md` is the parent source of truth. Read it first at session start. If this file conflicts with the master plan, the master plan wins.
5. Then read this file's Primary Context Pack in full (Infrastructure.md, DataSubAgents.md, etc.).
6. Do not redesign architecture; resolve only open questions in this module plan.

### Decision Process

7. All decisions are provisional until the user explicitly confirms they are final. Lock a decision only after explicit user confirmation that they have made up their mind.
8. One focused decision/question at a time; reprioritize after every user answer.
9. For each major design choice, compare alternatives and record tradeoffs (alternatives, choice, reason).
10. Keep open questions in the register (§8) until explicitly resolved. Record unresolved items in the open-question table; when resolved, update the relevant main section(s) and mark the corresponding open question as resolved.
11. Reason independently before locking any decision; challenge assumptions; do not auto-accept proposals.

### Bot-to-Bot Notes

12. Bot-to-bot notes are append-only; mark handled, do not delete history.
13. Append to bot-to-bot notes at session start and when resolving questions.

Bot-to-bot notes (append-only; mark handled, do not delete history):
- [2026-02-08] [Claude] Initial scaffold created. I7 resolved: agent catalog locked in master plan §2b. P0, P1, P5 marked resolved.
- [2026-03-22] [Claude] P2, P3, P4 resolved. §11 added: 12 detailed implementation steps covering skill frontmatter, 8-K content assembly (warmup_cache.py), planner lessons placeholder, guidance history (new function needed), inter-quarter context, agent catalog static embed, fetch_plan.json placeholder, orchestrator validation, context pollution management, expanded rules, canonical IDs + anchor flags, and testing plan.
- [2026-03-23] [Claude] §11 Step 5 updated with verified Neo4j data type findings. Added "Neo4j Data Type Reference" section with exact field types, row counts, and parsing helpers (`_parse_json_field`, `_fmt_vol`, `_fmt_txn`). Key findings: channels/authors/items/exhibits are JSON strings requiring `json.loads()`; volume is fractional 3.10% of the time (mostly 2026+ Polygon artifact); transactions is always integer-valued. Test case counts corrected from live CRM run (74 news, 4 filings, 1 dividend). Added CLI parsing code, test cases 8-9 (JSON parsing + volume formatting). Implementation order expanded to 11 steps with full self-contained instructions for zero-context implementor.

---

## Design Constraints (LOCKED)

1. Priority order is fixed: reliability first, full required data coverage second, speed third, then maximum accuracy via comprehensive/exhaustive research within runtime limits.
2. No over-engineering: add complexity only when it has clear reliability or quality value.
3. Must remain SDK-triggerable and non-interactive. Keep SDK compatibility and non-interactive execution constraints from `Infrastructure.md`.
4. Map each requirement to a tested primitive/pattern before accepting a design.
5. Validate choices against `Infrastructure.md`, `AgentTeams.md`, and `DataSubAgents.md` primitives.

---

## 0) Purpose

Define the Planner module contract and implementation decisions so a zero-context bot can implement it without ambiguity.

Planner role: read 8-K plus prior learning context, output one `fetch_plan.json` for orchestrator execution.

---

## 0.1) I7 Status: RESOLVED

**I7 (Planner agent catalog) is locked in `earnings-orchestrator.md §2b`.**

14 available agents across 5 domains (Neo4j 6, Alpha Vantage 1, Yahoo 1, Benzinga API 1, Perplexity 5) + planned families (`WEB_SEARCH`, `SEC_API_FREE_TEXT_SEARCH`, `PRESENTATIONS`; IDs provisional and may expand). Any `fetch.agent` value not in the catalog is a validation error. Tier guidance for priority patterns included.

**Key dependency**: The planner consumes the catalog from `earnings-orchestrator.md`; it does not build or maintain agents. Available agents are implemented under `DataSubAgents.md`. Planned agents remain invalid `fetch.agent` values until they are built and moved into the available table.

Planner should only reference agents in the "available" table. Planned agents are not valid `fetch.agent` values until they are built and moved to "available."

---

## 1) Primary Context Pack (LOCKED)

Every bot implementing Planner must read these first:

1. `earnings-orchestrator.md` (primary source of truth).
2. `Infrastructure.md` (execution constraints and SDK behavior).
3. `AgentTeams.md` (alternative primitives; use only when justified).
4. `DataSubAgents.md` (data access layer assumptions).
5. `guidanceInventory.md` (guidance extraction schema — defines the Guidance/GuidanceUpdate nodes that `build_guidance_history()` reads from).
6. This file (`planner.md`).
7. Existing skills:
   - `.claude/skills/earnings-orchestrator/SKILL.md`
   - `.claude/skills/earnings-planner/` (currently empty; target location)

---

## 2) SDK and Automation Contract (LOCKED)

1. Planner must be non-interactive (no user prompts, no manual approval logic).
2. Planner must produce machine-parseable JSON only.
3. Missing required inputs must fail fast with explicit error.
4. Keep compatibility with SDK-triggered orchestration defined in `earnings-orchestrator.md`.

---

## 3) Scope and Non-Goals

### In Scope

1. Planner input assembly contract.
2. Planner output contract (`fetch_plan.v1`).
3. Single-turn behavior and validation boundaries.

### Out of Scope

1. Executing data fetches (orchestrator owns execution).
2. Predictor scoring logic.
3. Attribution/Learner logic.

---

## 4) Module Interface Contract (Current Master Snapshot)

### Caller -> Callee

- Caller: Orchestrator Step 3b.
- Callee: Planner.

### Required Input (from orchestrator)

1. `ticker`
2. `quarter`
3. `filed_8k`
4. `8k_packet.json` — canonical 8-K content packet assembled by `build_8k_packet()`. See §11 Step 2.
5. `planner_lessons_history` — chronological per-quarter array from prior attribution feedback. See §11 Step 3.
6. `guidance_history.json` — structured guidance trajectory from Neo4j, assembled by `build_guidance_history()`. See §11 Step 4.
7. Agent catalog (static embed in prompt — 14 valid `fetch[].agent` values with tier guidance). See §11 Step 6 and `earnings-orchestrator.md §2b`.

### Required Output (to orchestrator)

- `fetch_plan.json` using `fetch_plan.v1` contract from master plan:
  - `schema_version`, `ticker`, `quarter`, `filed_8k`
  - `questions[]` entries with `id`, `question`, `why`, `output_key`, `fetch`
  - `fetch` as tiered array-of-arrays:
    - within tier: parallel
    - across tiers: sequential fallback

### Hard Constraints

1. Planner is single-turn.
2. Planner does not fetch data itself.
3. PIT handling remains orchestrator concern, not planner concern.

---

## 5) Design Rules

1. Planner relevance principle: each fetch request should map to 8-K claim, core dimension, or U1 lesson.
2. Keep schema deterministic and simple for parsing.
3. Prefer over-fetch to under-fetch when uncertain (orchestrator parallelizes).
4. Avoid free-form prose outputs.

---

## 6) Validation and Failure Policy

### Block

1. Invalid JSON output.
2. Missing required top-level schema fields.

### Warn

1. Missing common families (e.g., no consensus/prior-financial coverage) if allowed by context.

### Rule

Validation lives in orchestrator pipeline; planner output must be machine-checkable.

---

## 7) Implementation Phases

### Phase 0: Contract Lock

1. Confirm implementation mapping to locked orchestrator contracts (I2 + I7).
2. Keep planner local assumptions aligned with parent-plan revisions.

### Phase 1: Skill Build

1. Create `.claude/skills/earnings-planner/SKILL.md`.
2. Implement single-turn JSON output behavior.

### Phase 2: Validation

1. Add parser/validator checks in orchestrator.
2. Test 3-5 representative earnings quarters.

---

## 8) Open Questions Register

| ID | Question | Priority | Status |
|---|---|---|---|
| P0 | I7 Planner agent catalog: exact allowed `fetch.agent` values + purpose + invalid-name behavior | P0 | **Resolved** — 14 agents locked in `earnings-orchestrator.md §2b`. Invalid name = validation error (block). |
| P1 | Exact planner input payload schema from orchestrator? | P0 | **Resolved** — locked by I2 in `earnings-orchestrator.md §2a`. |
| P2 | Agent catalog delivery: static list in prompt or external file? | P1 | **Resolved** — static embed in planner SKILL.md prompt. 14 agents with one-line descriptions + tier guidance. Changes rarely; no external file needed. See §11 Step 6. |
| P3 | Canonical question IDs vs free-form IDs? | P1 | **Resolved** — 9 canonical IDs for standard families + custom IDs allowed (`snake_case`, no ticker/quarter). 4 anchor-flag-linked output_keys MUST use canonical names. See §11 Step 11. |
| P4 | 8-K truncation/sectioning rules for large filings? | P1 | **Resolved** — no truncation (1M context window). Use `build_8k_packet()` which assembles sections + EX-99.x + EX-10.x previews + filing text fallback via direct Bolt. Orchestrator caches once in quarter directory, planner + predictor share. See §11 Step 2. |
| P5 | Sanity check policy: warn-only or block in edge cases? | P1 | **Resolved** — master plan R5: log warning, not block. Planner may have valid reasons to omit common data types; U1 self-corrects. |

---

## 9) Done Criteria

Planner module plan is done when:

1. P0 questions are resolved.
2. Input and output contracts are unambiguous and testable.
3. Planner skill frontmatter + behavior requirements are locked.
4. Orchestrator integration is deterministic and parse-safe.

---

## 10) References

1. `earnings-orchestrator.md`
2. `Infrastructure.md`
3. `AgentTeams.md`
4. `DataSubAgents.md`
5. `guidanceInventory.md`
6. `.claude/skills/earnings-orchestrator/SKILL.md`

---

## 11) Implementation Steps (Detailed)

Expands §7 phases into actionable steps. Each step includes decisions, open items, and references to `earnings-orchestrator.md` where applicable.

---

### Step 1: Create Skill Frontmatter

**Target**: `.claude/skills/earnings-planner/SKILL.md`

```yaml
---
name: earnings-planner
description: Single-turn fetch plan generator for earnings prediction pipeline
model: opus
effort: high
context: fork
user-invocable: false
permissionMode: dontAsk
allowed-tools:
  - Read
  - Write
---
```

**Decisions**:
- `effort: high` — enables extended thinking for reasoning about which data to fetch. Confirmed working for skills (v2.1.80, Infrastructure.md).
- `model: opus` — enforced in skills (v2.1.74+, Infrastructure.md). Planner needs strong reasoning for 8-K analysis.
- `allowed-tools: [Read, Write]` — NOT enforced for skills (Infrastructure.md), but documents intent. Planner only needs Read (8-K content file) and Write (fetch_plan.json). No Task, Skill, MCP, Bash, Grep, Glob.
- `user-invocable: false` — called by orchestrator only, not directly by user.
- `permissionMode: dontAsk` — SDK automation, no interactive prompts.

**Resolved**: `EnterPlanMode`/`ExitPlanMode` are NOT needed. The planner is single-turn: read inputs → write one JSON file. Plan mode is for multi-step interactive work. Even if available in forked skills (Infrastructure.md v2.1.76 says ABSENT), it would add no value to a single-turn JSON generator.

**Ref**: `earnings-orchestrator.md §2b` (planner behavior), `Infrastructure.md` (frontmatter fields).

---

### Step 2: 8-K Content Assembly — `build_8k_packet()` (LOCKED)

**What**: The orchestrator assembles a canonical `8k_packet.json` for the target quarter BEFORE calling the planner. Both planner and predictor read from the same packet file. One fetch, one packet, two views.

#### Architecture

```
_fetch_8k_core(manager, accession)         ← private helper (4J + 4K), shared
    │                                         returns (sections, exhibits_99)
    │
    ├── run_8k(accession)                  ← GUIDANCE EXTRACTION (unchanged)
    │   calls _fetch_8k_core()
    │   writes /tmp/8k_content_{ACC}.json
    │
    └── build_8k_packet(accession, ticker, out_path)  ← EARNINGS ORCHESTRATION
        1. 4G-enriched: inventory + all Report metadata (one query)
        2. _fetch_8k_core() for sections + EX-99.x
        3. Non-99 exhibits via inventory diff → preview (2500 chars) + full_size
        4. Filing text fallback if sections + all exhibits empty
        5. Assemble 8k_packet.v1
        6. Atomic write (temp file + rename) to out_path
```

**Key design rules**:
- `run_8k()` stays untouched externally. No guidance extraction regression risk.
- `_fetch_8k_core()` is a private helper inside `warmup_cache.py`. Both `run_8k()` and `build_8k_packet()` call it. No logic duplication, no drift.
- `build_8k_packet()` is orchestrator-owned. Changing it does NOT affect guidance extraction.
- **Normalize at assembly time**: Parse `r.items` into a clean array (not raw string). Strip nulls from `section_names` / `exhibit_numbers` in `content_inventory`. The packet must be clean and deterministic — no nulls in arrays, no unparsed JSON strings.

#### Schema: `8k_packet.v1`

```json
{
  "schema_version": "8k_packet.v1",
  "ticker": "CRM",
  "accession_8k": "0001628280-25-025432",
  "filed_8k": "2025-05-28T16:05:00Z",
  "form_type": "8-K",
  "items": ["Item 2.02", "Item 9.01"],
  "period_of_report": "2025-03-31",
  "market_session": "post_market",  // use real enum from r.market_session (verify actual stored values before implementation)
  "is_amendment": false,
  "cik": "0001108524",

  "content_inventory": {
    "section_names": ["Item 2.02", "Item 9.01"],
    "exhibit_numbers": ["EX-99.1"],
    "has_filing_text": true
  },

  "sections": [
    {"section_name": "Item 2.02", "content": "...full text..."},
    {"section_name": "Item 9.01", "content": "...full text..."}
  ],

  "exhibits_99": [
    {"exhibit_number": "EX-99.1", "content": "...full text..."}
  ],

  "exhibits_other": [
    {
      "exhibit_number": "EX-10.1",
      "content_preview": "...first 2500 chars...",
      "full_size": 185000
    }
  ],

  "filing_text": null,

  "assembled_at": "2026-03-22T14:00:00Z"
}
```

#### Field reference

| Field | Source | Purpose |
|---|---|---|
| `schema_version` | hardcoded `"8k_packet.v1"` | Versioning for future schema changes |
| `ticker` | parameter | Company identification |
| `accession_8k` | parameter | Filing identification — aligned with orchestrator/event.json vocabulary |
| `filed_8k` | 4G: `r.created` | Filing acceptance datetime — aligned with orchestrator vocabulary (not "created") |
| `form_type` | 4G: `r.formType` | Validation — should always be "8-K" for earnings |
| `items` | 4G: `r.items` | Which items the filing covers (parsed normalized array) |
| `period_of_report` | 4G: `r.periodOfReport` | Fiscal period this earnings covers |
| `market_session` | 4G: `r.market_session` | Pre/post/in-market timing — context for prediction |
| `is_amendment` | 4G: `r.isAmendment` | Edge case flag (8-K/A vs 8-K) |
| `cik` | 4G: `r.cik` | SEC company identifier for cross-reference |
| `content_inventory` | 4G: collected | What EXISTS vs what was FETCHED — debugging and audit |
| `sections` | 4J via `_fetch_8k_core()` | Full section text — primary filing content. `section_name` is the raw Neo4j value (source truth). If human-friendly labels are needed, map separately in the view renderer — do not overload this field. |
| `exhibits_99` | 4K via `_fetch_8k_core()` | Full EX-99.x text — press releases, presentations, supplemental data |
| `exhibits_other` | inventory diff → 4K-other-preview | Preview (first 2500 chars) + `full_size` for any non-EX-99 exhibit. Future-proof: auto-detects any new exhibit type via inventory diff, not hardcoded families. Bounded: preview prevents 200KB contract bloat. |
| `filing_text` | 4F | Fallback ONLY — null unless sections + all exhibits are empty. Last resort (~1.6% of earnings 8-Ks). |
| `assembled_at` | runtime | Audit timestamp |

#### Non-EX-99 exhibit policy (LOCKED)

- **EX-99.x**: full text (always — press releases, presentations, core content)
- **All other exhibits**: preview (first 2500 chars) + `full_size` integer
- Detection: `exhibits_other = inventory.exhibit_numbers - fetched_ex99_numbers` (inventory diff, not hardcoded families)
- If EX-21 (subsidiary list), EX-23 (auditor consent), or any future exhibit type is added to the graph, the assembler picks it up automatically

#### Content-bearing relationships covered by the packet

The assembler covers ALL content-bearing paths from the Report node:

| # | Relationship | Covered by | In packet as |
|---|---|---|---|
| 1 | `HAS_SECTION → ExtractedSectionContent` | Query 4J via `_fetch_8k_core()` | `sections[]` |
| 2 | `HAS_EXHIBIT → ExhibitContent` (EX-99.x) | Query 4K via `_fetch_8k_core()` | `exhibits_99[]` |
| 3 | `HAS_EXHIBIT → ExhibitContent` (non-EX-99) | Query 4K-other-preview via inventory diff | `exhibits_other[]` (preview) |
| 4 | `HAS_FILING_TEXT → FilingTextContent` | Query 4F (fallback only) | `filing_text` |
| 5 | `r.extracted_sections` (inline property) | **Redundant** — same content as HAS_SECTION nodes. Skipped. |
| 6 | `r.exhibit_contents` (inline property) | **Redundant** — same content as HAS_EXHIBIT nodes. Skipped. |
| 7 | Report node metadata | Query 4G-enriched | Top-level fields (`items`, `period_of_report`, etc.) |

**Not in the packet** (graph context links, not filing content):

| # | Relationship | Why excluded |
|---|---|---|
| 7 | `PRIMARY_FILER` return properties (`daily_stock`, `hourly_stock`, etc.) | **FORBIDDEN** — prediction outcomes, not inputs |
| 8 | `INFLUENCES → MarketIndex/Sector/Industry` | Graph context — orchestrator has this from Company node |
| 9 | `IN_CATEGORY → AdminReport` | Administrative metadata, zero signal |
| 10 | `REFERENCED_IN → Company` | 0 hits for earnings 8-Ks |
| 11 | `GuidanceUpdate -[:FROM_SOURCE]→ Report` (inbound) | Covered separately by Step 4 (guidance history) |
| 12 | `r.description` | Useless metadata ("Form 8-K - Current report - Item 2.02") |

#### Queries to add to `warmup_cache.py`

**Existing (unchanged)**:
- `QUERY_4J` (line 246) — all sections
- `QUERY_4K` (line 252) — EX-99.x exhibits

**New constants**:
```python
# 4G-enriched — inventory + all Report metadata in one query
# Joins PRIMARY_FILER to validate accession belongs to the expected ticker
QUERY_4G_META = """
MATCH (r:Report {accessionNo: $accession})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
RETURN r.created AS filed_8k,
       r.formType AS form_type,
       r.items AS items,
       r.periodOfReport AS period_of_report,
       r.market_session AS market_session,
       r.isAmendment AS is_amendment,
       r.cik AS cik,
       collect(DISTINCT e.exhibit_number) AS exhibit_numbers,
       collect(DISTINCT s.section_name) AS section_names,
       count(DISTINCT ft) > 0 AS has_filing_text
"""

# Non-99 exhibits — preview (first 2500 chars) + full_size
QUERY_4K_OTHER_PREVIEW = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE NOT e.exhibit_number STARTS WITH 'EX-99'
RETURN e.exhibit_number AS exhibit_number,
       left(e.content, 2500) AS content_preview,
       size(e.content) AS full_size
ORDER BY e.exhibit_number
"""

# 4F — Filing text fallback
QUERY_4F = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.content AS content
"""
```

#### Ownership comments (required in `warmup_cache.py`)

```python
# ─────────────────────────────────────────────────────────────────────
# SHARED OWNERSHIP WARNING
#
# _fetch_8k_core()     — private helper, shared by BOTH pipelines below
# run_8k()             — used by GUIDANCE EXTRACTION (extraction_worker.py)
# build_8k_packet()    — used by EARNINGS ORCHESTRATION (earnings-orchestrator)
#
# Changing _fetch_8k_core() affects BOTH pipelines.
# Changing run_8k() affects guidance extraction ONLY.
# Changing build_8k_packet() affects earnings orchestration ONLY.
# ─────────────────────────────────────────────────────────────────────
```

#### Storage path (LOCKED)

```
earnings-analysis/Companies/{TICKER}/events/{quarter}/8k_packet.json
```

- Orchestrator passes explicit `out_path` to `build_8k_packet()`.
- `/tmp/earnings_8k_packet_{ACC}.json` is the default for manual/debug invocation only.
- `run_8k()` keeps its existing `/tmp/8k_content_{ACC}.json` path for guidance extraction — completely separate.
- **Live-mode staging**: If `quarter_label` is not yet resolved at packet-build time (e.g., live mode before fiscal math completes), write to the accession-keyed default path first, then move to the quarter directory once quarter identity is resolved. The orchestrator typically resolves quarter_label before needing the packet, but this staging path is cheap insurance against ordering edge cases.

#### CLI interface

```bash
# Guidance extraction (unchanged):
bash warmup_cache.sh $TICKER --8k $ACCESSION

# Earnings orchestration (new):
bash warmup_cache.sh $TICKER --8k-packet $ACCESSION [--out-path /path/to/8k_packet.json]
```

#### Planner view vs Predictor view

One canonical packet, two read patterns — not separate fetches, not separate files.

- **Planner view**: Reads `sections` + `exhibits_99` + `items` + `period_of_report`. Skips `exhibits_other` and `filing_text` (planner decides what data to fetch, doesn't need contract previews or raw fallback text).
- **Predictor view**: Reads everything in the packet. `exhibits_other` previews can reveal M&A, restructuring, leadership changes relevant to prediction. `filing_text` fallback gives the predictor something when nothing else exists.

Views are implemented as rendering logic in the orchestrator (when building the planner prompt vs the predictor bundle), not as separate files.

#### Implementation order

1. Add `_fetch_8k_core(manager, accession)` private helper — extracts the 4J+4K logic from `run_8k()`
2. Refactor `run_8k()` to call `_fetch_8k_core()` — output unchanged, regression test confirms
3. Add new query constants (`QUERY_4G_META`, `QUERY_4K_OTHER_PREVIEW`, `QUERY_4F`)
4. Add `build_8k_packet(accession, ticker, out_path=None)` function
5. Add `--8k-packet` CLI flag to `warmup_cache.py` main()
6. Add ownership comments
7. Run test cases

#### Test cases (6 required)

| # | Case | What to verify |
|---|---|---|
| 1 | Normal 2.02 + EX-99.1 | Sections + EX-99.1 populated, `exhibits_other` empty, `filing_text` null |
| 2 | 2.02 + EX-99.1 + EX-99.2 | Both exhibits in `exhibits_99`, multi-exhibit handling correct |
| 3 | Section-only 8-K (no exhibits) | `exhibits_99` empty, sections populated, `filing_text` null |
| 4 | Empty sections + exhibits | `filing_text` populated (fallback activated), sections/exhibits empty |
| 5 | 8-K with EX-10.x | `exhibits_other` has preview (2500 chars) + `full_size`, `exhibits_99` has press release |
| 6 | `run_8k()` regression | After `_fetch_8k_core()` refactor, `run_8k()` output is byte-identical to before |

**Ref**: `earnings-orchestrator.md §2a` (8k_content field), `report-queries/SKILL.md` (queries 4F/4G/4J/4K/4L), `warmup_cache.py` (lines 246-282), `extract/types/guidance/assets/8k-primary.md` (guidance extraction content fetch strategy).

---

### Step 3: Planner Lessons (U1 Feedback) — LOCKED

**What**: Prior quarters' `planner_lessons` from attribution feedback, assembled by the orchestrator and passed to the planner as structured chronological history.

**Status**: Placeholder input until the learner (§B2 in master plan) is built. The planner skill and orchestrator assembly logic should be implemented now with the locked shape below. First quarter for any ticker receives `[]`.

#### Data shape (LOCKED)

```json
"planner_lessons_history": [
  {
    "quarter": "Q1_FY2024",
    "planner_lessons": [
      "Fetch transcript Q&A via neo4j-transcript, not just news headlines — the key bearish signal on margin pressure came from analyst questioning, not the press release"
    ]
  },
  {
    "quarter": "Q2_FY2024",
    "planner_lessons": [
      "Add peer earnings for top sector peers (XOM, CVX) via neo4j-entity — sector headwind was the primary Q1 driver but was completely absent from the bundle",
      "Include inter-quarter analyst upgrades/downgrades via yahoo-earnings — 15 PT cuts over 2 months signaled sustained bearish pressure that news titles alone didn't capture"
    ]
  },
  {
    "quarter": "Q3_FY2024",
    "planner_lessons": [
      "Fetch XBRL operating margins for prior 4 quarters via neo4j-xbrl — margin trend reversal was the real story, not headline EPS beat"
    ]
  }
]
```

**Why this shape**:
- Better than a flat list: preserves chronology and quarter context so the planner can see patterns evolve (e.g., same lesson repeating = high importance).
- Smaller than full `u1_feedback`: planner only gets what it actually needs (`planner_lessons`), not `predictor_lessons`, `what_failed`, `why`, etc.
- Future-safe: if the learner refines lessons over time, the planner can see repetition/change across quarters.
- First quarter: trivially `[]`.
- **Why strings, not structured objects**: The producer (learner) and consumer (planner) are both LLMs. Natural language is their native format. A structured object like `{condition, fetch_target, source_hint, why}` is just a decomposed sentence — the planner LLM extracts these components from a well-written sentence just as easily, with zero schema overhead.

#### Assembly rules (orchestrator responsibility)

1. Orchestrator reads all prior `attribution/result.json` files for this ticker, in chronological order (oldest → newest).
2. Skip quarters where `attribution/result.json` does not exist (no attribution yet — common during first historical bootstrap).
3. For each existing attribution file, extract `quarter_label` + `feedback.planner_lessons`.
4. Skip entries where `planner_lessons` is empty (`[]`) — no value in passing empty arrays per quarter.
5. Preserve chronological order of remaining entries (oldest → newest). Do NOT flatten or dedupe across quarters — repeated lessons across quarters signal importance.
6. Pass the assembled array to the planner as `planner_lessons_history`.

#### Lesson authoring contract (LOCKED — enforced in learner)

Each `planner_lesson` string must be a **specific, actionable, sentence-form instruction**. Fragment-style lessons ("include peer earnings", "check transcripts") are NOT acceptable — they lose the context that makes the lesson useful.

**Required sentence template**: `[Action] [target data] via [source agent(s)] — [specific gap or failure that caused this lesson]`

| Part | What it tells the planner | Required? |
|---|---|---|
| Action | What to add, change, expand, or stop doing | Yes |
| Target data | The specific data dimension or question | Yes |
| Source agent(s) | Which agent(s) should be used | Yes |
| Gap/failure reason | Why this was needed — what was missed and what it caused | Yes |

**Examples of acceptable lessons**:
- "Fetch transcript Q&A via neo4j-transcript, not just news headlines — the key bearish signal on margin pressure came from analyst questioning, not the press release"
- "Add peer earnings for top sector peers (XOM, CVX) via neo4j-entity — sector headwind was the primary driver but was completely absent from the bundle"
- "Expand news search window to ±5 days via neo4j-news — pre-filing analyst downgrade 4 days before the 8-K was the strongest leading indicator but fell outside the default window"
- "Do not use perplexity-research for sector context on niche-industry tickers — returned generic macro commentary with no peer-specific signal, wasted a Tier 2 call"

**Examples of UNACCEPTABLE lessons** (too lossy, no actionable detail):
- "include sector peer earnings" — which peers? via which agent? why was it needed?
- "check transcript Q&A" — for what? what was the failure that triggered this?
- "add analyst data" — too vague to act on

**Enforcement (to be implemented in learner)**: The learner's SubagentStop hook (learner.md §12, Layer 4) must validate that each `planner_lessons` string meets minimum quality: non-empty, minimum 50 characters, and contains source/agent reference. The learner's prompt (Layer 1) must include the sentence template. Short fragments must be blocked before the learner can complete. **This enforcement does not exist yet** — it must be built when implementing the learner agent (§B2 in master plan).

**Cross-reference**: This authoring contract must be added to `learner.md` as a hard output requirement for the `feedback.planner_lessons` field when the learner is implemented. The planner consumes what the learner produces — quality must be enforced at the source.

#### Planner prompt behavior

- **Empty `[]`**: First quarter or no attribution yet. Planner reasons from 8-K + guidance + agent catalog alone. This is the normal cold-start case — no special handling needed.
- **Populated array**: Planner uses lessons as soft priors for fetch priority decisions. Each lesson contains the action, target, source, and reason — the planner maps these directly to fetch plan questions and agent assignments. Repeated lessons across multiple quarters carry more weight.
- **Guardrail**: Lessons are advisory, not commands. Current-quarter 8-K evidence overrides any past lesson. If the 8-K shows no sector relevance, the planner can skip peer earnings even if U1 suggested it.

#### Caps

Per `earnings-orchestrator.md §2d`: `planner_lessons` is capped at 3 items per quarter. With ~10 quarters of history, maximum payload is ~30 sentence-form strings — trivial context even with richer per-lesson content.

**Ref**: `earnings-orchestrator.md §2b` (self-learning input), `§2d` (U1 loop, feedback block — `planner_lessons` max 3 items per quarter), `learner.md §4` (learner output contract — must mirror the authoring contract above).

---

### Step 4: Guidance History — `build_guidance_history()` (LOCKED)

**What**: Queries all GuidanceUpdate nodes for a ticker from Neo4j, groups into metric series, collapses same-day same-value cross-source duplicates into single events with merged provenance, writes a canonical JSON file, and renders text for the planner/predictor prompt.

**Status**: New function needed. No rendering function exists in the codebase today. The guidance extraction pipeline writes to Neo4j (5,227 GuidanceUpdate + 328 Guidance + 187 GuidancePeriod nodes) via `guidance_writer.py`, but nothing reads it back as structured history.

#### Architecture

```
build_guidance_history(ticker, pit=None, out_path=None)
  │
  ├─ 1. Query all GuidanceUpdates for ticker (+ optional PIT filter)
  │     + Guidance label/id + GuidancePeriod + optional Concept/Member
  │
  ├─ 2. Resolve unit groups (absorb "unknown" canonical_unit)
  │
  ├─ 3. Group into series by 6-dimension key
  │
  ├─ 4. Within each series, collapse same-day same-value cross-source events
  │     → one row per guidance event, sources merged
  │
  ├─ 5. Sort: series by metric name, updates by given_date
  │
  ├─ 6. Write canonical JSON (guidance_history.v1)
  │
  └─ 7. Atomic write (temp + rename) to out_path
```

#### Graph Schema Reference

```
GuidanceUpdate (5,227) — the star center, one per data point
  ──UPDATES──────────→ Guidance (328 — metric label catalog)
  ──HAS_PERIOD────────→ GuidancePeriod (187 — calendar date range)
  ──FOR_COMPANY───────→ Company
  ──FROM_SOURCE───────→ Transcript (53.2%) or Report (46.8%)
  ──MAPS_TO_CONCEPT──→ Concept (51.3% — XBRL concept match)
  ──MAPS_TO_MEMBER───→ Member (3.6% — XBRL segment match)
```

All relationships have zero properties. Guidance and GuidancePeriod are lightweight lookup targets.

#### Queries

Two variants — Python selects based on `pit` parameter:

```python
QUERY_GUIDANCE_HISTORY = """
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(concept:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(member:Member)
RETURN g.label AS metric, g.id AS metric_id,
       gu.basis_norm, gu.segment, gu.segment_slug,
       gu.period_scope, gu.canonical_unit, gu.time_type,
       gu.fiscal_year, gu.fiscal_quarter,
       gu.given_date, gu.low, gu.mid, gu.high,
       gu.source_type, gu.derivation,
       gu.qualitative, gu.conditions,
       gu.evhash16,
       gp.start_date AS period_start, gp.end_date AS period_end,
       concept.qname AS xbrl_qname,
       collect(DISTINCT member.qname) AS member_qnames
ORDER BY g.label, gu.basis_norm, gu.segment_slug, gu.period_scope,
         gu.canonical_unit, gu.time_type, gu.given_date
"""

QUERY_GUIDANCE_HISTORY_PIT = """
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE datetime(gu.given_date) <= datetime($pit)
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(concept:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(member:Member)
RETURN g.label AS metric, g.id AS metric_id,
       gu.basis_norm, gu.segment, gu.segment_slug,
       gu.period_scope, gu.canonical_unit, gu.time_type,
       gu.fiscal_year, gu.fiscal_quarter,
       gu.given_date, gu.low, gu.mid, gu.high,
       gu.source_type, gu.derivation,
       gu.qualitative, gu.conditions,
       gu.evhash16,
       gp.start_date AS period_start, gp.end_date AS period_end,
       concept.qname AS xbrl_qname,
       collect(DISTINCT member.qname) AS member_qnames
ORDER BY g.label, gu.basis_norm, gu.segment_slug, gu.period_scope,
         gu.canonical_unit, gu.time_type, gu.given_date
"""
```

Python selection:
```python
query = QUERY_GUIDANCE_HISTORY_PIT if pit else QUERY_GUIDANCE_HISTORY
params = {'ticker': ticker, 'pit': pit} if pit else {'ticker': ticker}
```

#### Step 2: Resolve Unit Groups

Before grouping, absorb `unknown` canonical_unit into the real unit when unambiguous. Verified against live graph: **185 out of 1,000 groups (18.5%) have mixed canonical_units** — this step is NOT optional.

```python
def resolve_unit_groups(rows):
    """For each base series (5D key without unit), if exactly one non-unknown
    canonical_unit exists, remap all 'unknown' entries to that unit.
    Prevents false series splits from extraction quality gaps."""

    base_units = {}  # (metric_id, basis, seg_slug, scope, tt) → set of non-unknown units
    for r in rows:
        base = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                r['period_scope'], r['time_type'])
        if r['canonical_unit'] != 'unknown':
            base_units.setdefault(base, set()).add(r['canonical_unit'])

    for r in rows:
        if r['canonical_unit'] == 'unknown':
            base = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                    r['period_scope'], r['time_type'])
            real_units = base_units.get(base, set())
            if len(real_units) == 1:
                r['resolved_unit'] = next(iter(real_units))
            else:
                r['resolved_unit'] = 'unknown'
        else:
            r['resolved_unit'] = r['canonical_unit']

    return rows
```

Three cases:
- ONE real unit + unknowns → unknowns become that unit (e.g., EPS: `usd` + `unknown` → all `usd`)
- MULTIPLE real units + unknowns → unknowns stay `unknown` (legitimate ambiguity)
- ALL unknown → stays `unknown`

#### Step 3: Grouping Key (6 dimensions, verified)

```
Internal key: (metric_id, basis_norm, segment_slug, period_scope, resolved_unit, time_type)
Display:      (metric,    basis_norm, segment,      period_scope, resolved_unit, time_type)
```

- `metric_id` (`g.id`, e.g., `"guidance:capex"`) for internal grouping — stable canonical identifier. `metric` (`g.label`) is display-only.
- `segment_slug` for internal grouping (prevents casing variants: "High-End Consumer" vs "High-end Consumer")
- `resolved_unit` for grouping (absorbs unknowns)
- At the series level in JSON, store `raw_unit_variants` (array of all distinct `canonical_unit` values in the series, e.g., `["usd", "unknown"]`) plus `resolved_unit` (the resolved display unit). This makes the absorption auditable — a single `canonical_unit` at series level would be misleading when unknowns were absorbed.

**Display segment selection rule (deterministic)**: When `segment_slug` groups rows with different raw `segment` strings (casing variants), pick the **most frequent non-null `segment` label** in the series. Tie-break: lexicographically first. This ensures identical output on every run.

**Verified against live graph**: 6-dimension key correctly separates all tested cases:
- Annual vs quarterly EPS → separate series ✅
- GAAP vs non-GAAP EPS → separate series ✅
- Total vs Dollar Tree segment → separate series ✅
- Percent vs basis_points (same metric) → separate series ✅
- Duration vs instant (Diluted Share Count) → separate series ✅

#### Step 4: Collapse Same-Day Cross-Source Duplicates

Within each series, collapse entries that represent the **same guidance event from different sources** into one row with merged provenance.

**Date contract**: JSON stores BOTH full timestamp and calendar day per update:
- `given_date_ts`: full ISO8601 timestamp from Neo4j (e.g., `"2023-03-15T16:05:00Z"`) — provenance precision preserved
- `given_day`: calendar date string (e.g., `"2023-03-15"`) — used for collapse logic and rendered text display

Collapse uses `given_day`. Rendered text shows `given_day`. Full `given_date_ts` is JSON-only audit data.

**Collapse key for numeric guidance**: `(series_key, fiscal_year, fiscal_quarter, given_day, low, mid, high)`

- `given_day` = `given_date_ts` truncated to **calendar date** (not exact timestamp — 8k at 16:00 and transcript at 20:30 on the same day are the same event. Verified: exact-timestamp matches across sources are near-zero; calendar-day matches are common.)
- Numeric payload (`low`, `mid`, `high`) must match exactly

**Collapse key for qualitative-only entries** (low/mid/high all null): `(series_key, fiscal_year, fiscal_quarter, given_day, normalized_qualitative)`

- `normalized_qualitative` = normalize the qualitative string for collapse comparison:
  1. `(qualitative or "").lower().strip()` — case + whitespace
  2. Replace hyphens with spaces (`"low-single-digits"` → `"low single digits"`)
  3. Strip trailing `s` on the last word (`"low single digits"` → `"low single digit"`) — handles plural variants
  4. Collapse multiple spaces to single space
  This handles verified real-world variants: "low single-digit" vs "low-single-digits", "flat to 3%" vs "Flat to 3%", while preserving genuinely distinct same-day statements (e.g., "inventory expected to grow" vs "inventory expected to decline"). Handles null qualitative gracefully (treated as empty string → collapses with other nulls).

**What gets merged**:
- `sources`: collect all `source_type` values, **sorted by fixed priority order**: `8k` > `transcript` > `10q` > `10k` > `news`. Always deterministic.
- `conditions`: keep richest (longest non-null)
- `qualitative`: keep richest (longest non-null)
- `derivation`: keep from primary source (same priority: `8k` > `transcript` > `10q` > `10k` > `news`)
- `xbrl_qname`: keep first non-null
- `member_qnames`: union all, **sorted alphabetically** for deterministic output
- `evhash16`: keep first (for audit)
- `given_date_ts`: keep earliest (first source's timestamp)

**What does NOT collapse**:
- Different fiscal years or quarters → separate events
- Different numeric values on same day → separate events (genuinely different guidance)
- Same values on different calendar days → separate events ("maintained" is real timeline data)

**Example — FIVE CapEx (before → after collapse)**:

Before (raw from Neo4j):
```
FY2024: $325M (2023-03-15, 8k, point)
FY2024: $325M (2023-03-15, transcript, point)
FY2024: $325M (2023-03-16, 10k, point)         ← different day, NOT collapsed
FY2024: $335M (2023-06-01, 8k, point)
FY2024: $335M (2023-06-01, transcript, point)
FY2024: $335M (2023-06-02, 10q, point)         ← different day, NOT collapsed
```

After collapse:
```
FY2024: $325M (2023-03-15, sources: [8k, transcript], point)
FY2024: $325M (2023-03-16, sources: [10k], point)
FY2024: $335M (2023-06-01, sources: [8k, transcript], point)
FY2024: $335M (2023-06-02, sources: [10q], point)
```

Typical reduction: FIVE 468 → ~250-300 events. No information lost — every distinct value on every distinct day is preserved.

**Note on ±1 day tolerance**: The 10-K/10-Q filed the day after the 8-K/transcript is NOT collapsed with them (different calendar day). This is the safest rule. If this feels noisy, a ±1 day tolerance can be added later — but exact calendar day is correct for now.

#### Real Enum Values (verified against live graph, 2026-03-22)

| Field | Stored values |
|---|---|
| `basis_norm` | `constant_currency`, `gaap`, `non_gaap`, `unknown` |
| `period_scope` | `annual`, `half`, `long_range`, `long_term`, `medium_term`, `monthly`, `quarter`, `short_term`, `undefined` |
| `time_type` | `duration`, `instant` |
| `canonical_unit` | `basis_points`, `count`, `m_usd`, `percent`, `percent_points`, `percent_yoy`, `unknown`, `usd`, `x` |

| `derivation` | `explicit`, `implied`, `point`, `floor`, `ceiling`, `calculated`, `comparative` (verify full list during implementation — run `collect(DISTINCT gu.derivation)`) |

Use these exact values in code — do not assume or invent enum values. Run verification queries during implementation to confirm the full set has not expanded.

#### JSON Schema: `guidance_history.v1`

```json
{
  "schema_version": "guidance_history.v1",
  "ticker": "FIVE",
  "pit": "2024-08-28T20:30:00Z",
  "series": [
    {
      "metric": "CapEx",
      "metric_id": "guidance:capex",
      "basis_norm": "unknown",
      "segment": "Total",
      "segment_slug": "total",
      "period_scope": "annual",
      "raw_unit_variants": ["m_usd"],
      "resolved_unit": "m_usd",
      "time_type": "duration",
      "updates": [
        {
          "fiscal_year": 2024,
          "fiscal_quarter": null,
          "given_date_ts": "2023-03-15T16:05:00Z",
          "given_day": "2023-03-15",
          "low": 325.0,
          "mid": 325.0,
          "high": 325.0,
          "sources": ["8k", "transcript"],
          "derivation": "point",
          "qualitative": null,
          "conditions": null,
          "evhash16": "abc123...",
          "period_start": "2024-02-01",
          "period_end": "2025-01-31",
          "xbrl_qname": "us-gaap:CapitalExpenditures",
          "member_qnames": []
        },
        {
          "fiscal_year": 2024,
          "fiscal_quarter": null,
          "given_date_ts": "2023-06-01T16:10:00Z",
          "given_day": "2023-06-01",
          "low": 335.0,
          "mid": 335.0,
          "high": 335.0,
          "sources": ["8k", "transcript"],
          "derivation": "point",
          "qualitative": null,
          "conditions": "reflecting store opening cadence adjustments",
          "evhash16": "def456...",
          "period_start": "2024-02-01",
          "period_end": "2025-01-31",
          "xbrl_qname": "us-gaap:CapitalExpenditures",
          "member_qnames": []
        }
      ]
    },
    {
      "metric": "Comparable Sales Growth",
      "metric_id": "guidance:comparable_sales_growth",
      "basis_norm": "unknown",
      "segment": "Total",
      "segment_slug": "total",
      "period_scope": "annual",
      "raw_unit_variants": ["percent"],
      "resolved_unit": "percent",
      "time_type": "duration",
      "updates": [
        {
          "fiscal_year": 2024,
          "fiscal_quarter": null,
          "given_date_ts": "2023-03-15T16:05:00Z",
          "given_day": "2023-03-15",
          "low": 1.0,
          "mid": 2.5,
          "high": 4.0,
          "sources": ["8k", "transcript"],
          "derivation": "explicit",
          "qualitative": null,
          "conditions": null,
          "evhash16": "...",
          "period_start": "...",
          "period_end": "...",
          "xbrl_qname": null,
          "member_qnames": []
        }
      ]
    }
  ],
  "summary": {
    "total_series": 85,
    "total_updates_raw": 468,
    "total_updates_collapsed": 280,
    "earliest_date": "2023-01-09",
    "latest_date": "2024-08-28"
  },
  "assembled_at": "2026-03-22T14:00:00Z"
}
```

#### Rendered Text (Planner View)

**Series header format**: `{metric} ({period_scope}, {resolved_unit}, {basis_norm} basis, {segment}, {time_type})`

**Simplification rules** (for clean headers in the common case):
- Omit `basis_norm` when `"unknown"` (most common)
- Omit `segment` when `"Total"` (most common)
- Omit `time_type` when `"duration"` (most common)

**Deterministic ordering rules** (critical for reproducible output):
- **Series ordering**: Within the same metric family (same `metric_id`), render `"Total"` segment FIRST, then segment breakdowns sorted alphabetically by `segment_slug`. Across metric families, sort alphabetically by `metric` (display label).
- **Sources list**: Always sorted by fixed priority: `8k`, `transcript`, `10q`, `10k`, `news`. Never random order.
- **member_qnames**: Sorted alphabetically for deterministic JSON output.
- **Updates within a series**: Sorted by `given_day` ascending (chronological). Tie-break: `fiscal_year` ascending, then `fiscal_quarter` ascending.

**Update line format**: `{period}: {value} ({given_day}, sources: {merged_sources}, {derivation}[, conditions if present])`

**Example render (FIVE, cutoff 2024-08-28)**:

```
=== GUIDANCE HISTORY: FIVE (85 series, 280 events, cutoff 2024-08-28) ===

CapEx (annual, m_usd):
  FY2024: $325M (2023-03-15, sources: 8k+transcript, point)
  FY2024: $335M (2023-06-01, sources: 8k+transcript, point)
  FY2024: $335M (2023-08-30, sources: 8k+transcript, point)
  FY2024: $335M (2023-11-29, sources: 8k+transcript, point)
  FY2025: $365M (2024-03-20, sources: 8k+transcript, point)
  FY2025: $345-$355M (2024-06-05, sources: 8k+transcript, explicit)
  FY2025: $335-$345M (2024-08-28, sources: 8k+transcript, explicit)

Comparable Sales Growth (annual, percent):
  FY2024: 1.0-4.0% (2023-03-15, sources: 8k+transcript, explicit)
  FY2024: 1.0-3.0% (2023-06-01, sources: 8k+transcript, explicit)
  FY2024: ~2.5% (2023-11-29, sources: transcript, point)
  FY2025: 0.0-3.0% (2024-03-20, sources: 8k+transcript, explicit)
  FY2025: -5.0 to -3.0% (2024-06-05, sources: 8k+transcript, explicit)
  FY2025: -5.5 to -4.0% (2024-08-28, sources: 8k, explicit)

EPS (annual, usd, non_gaap basis):
  FY2024: $5.16-$5.40 (2023-03-15, sources: 8k+transcript, explicit)
  FY2025: $4.35-$4.70 (2024-03-20, sources: 8k+transcript, explicit)
  FY2025: $3.20-$3.52 (2024-06-05, sources: 8k+transcript, explicit)
  FY2025: $3.15-$3.42 (2024-08-28, sources: 8k, explicit)

Gross Margin (quarter, basis_points):
  FY2025-Q2: -40 to -20 bps (2024-06-05, sources: 8k+transcript, explicit)
  FY2025-Q3: +20 to +60 bps (2024-08-28, sources: transcript, explicit)

Operating Margin (annual, percent, non_gaap basis):
  FY2025: 11.5-12.0% (2024-03-20, sources: 8k+transcript, explicit)
  FY2025: 8.5-9.0% (2024-06-05, sources: 8k+transcript, explicit)
  FY2025: 8.0-8.5% (2024-08-28, sources: 8k, explicit)

CapEx (annual, percent):
  FY2025: consistent with or slightly less than FY2024 as % of sales (2023-03-15, sources: transcript, comparative)
```

**Segmented retailer example (DLTR)** — segments appear as separate series:

```
=== GUIDANCE HISTORY: DLTR (90 series, 200 events, cutoff 2025-11-20) ===

Net Sales (annual, m_usd):
  FY2025: $30.6-$30.9B (2024-08-28, sources: 8k, explicit)

Net Sales (annual, percent, Family Dollar segment):
  FY2025: -5 to -3% (2024-08-28, sources: 8k, explicit)

Comp Store Sales (annual, Dollar Tree segment):
  FY2025: low single-digits (2024-08-28, sources: 8k+transcript, explicit)

Comp Store Sales (annual, Family Dollar segment):
  FY2025: -2 to 0% (2024-08-28, sources: 8k, explicit)
```

#### Properties: Included vs Excluded

**Included in both JSON and rendered text**:

| Property | JSON field | Text field | Role |
|---|---|---|---|
| `g.label` | `series.metric` | Header | Metric name |
| `gu.basis_norm` | `series.basis_norm` | Header (omit if "unknown") | GAAP/non-GAAP/constant_currency |
| `gu.segment` | `series.segment` | Header (omit if "Total") | Display segment name |
| `gu.period_scope` | `series.period_scope` | Header | annual/quarter/half/etc. |
| `resolved_unit` | `series.resolved_unit` | Header | Unknown-absorbed unit |
| `gu.time_type` | `series.time_type` | Header (omit if "duration") | duration/instant |
| `gu.fiscal_year` | `update.fiscal_year` | Period label | Target period |
| `gu.fiscal_quarter` | `update.fiscal_quarter` | Period label (when quarterly) | Target quarter |
| `gu.given_date` | `update.given_day` (calendar day) | Date | When guidance was stated (day precision for display) |
| `gu.low/mid/high` | `update.low/mid/high` | Value | The numbers |
| merged `sources` | `update.sources` | Source list | Collapsed provenance, sorted by fixed priority: 8k > transcript > 10q > 10k > news |
| `gu.derivation` | `update.derivation` | Tag | explicit/implied/point/floor/ceiling/calculated/comparative (verify full list during implementation) |
| `gu.qualitative` | `update.qualitative` | Value (when no numbers) | Non-numeric guidance |
| `gu.conditions` | `update.conditions` | Appended (truncated 100ch) | Context/drivers |

**Included in JSON only** (for predictor/learner, not in rendered text):

| Property | JSON field | Role |
|---|---|---|
| `g.id` | `series.metric_id` | Internal metric ID |
| `gu.segment_slug` | `series.segment_slug` | Internal grouping key |
| `gu.canonical_unit` (per-row) | `series.raw_unit_variants` (array) | All distinct raw canonical_unit values in the series (e.g., `["usd", "unknown"]`). Makes unit absorption auditable. |
| `gu.given_date` (full timestamp) | `update.given_date_ts` | Full ISO8601 timestamp — provenance precision preserved. Collapse and display use `given_day`. |
| `gu.evhash16` | `update.evhash16` | Audit/dedup hash |
| `gp.start_date/end_date` | `update.period_start/period_end` | Calendar period validation |
| `concept.qname` | `update.xbrl_qname` | XBRL concept for automated matching |
| `member.qname` | `update.member_qnames` | XBRL segment for automated matching |

**Excluded entirely**:

| Property | Why |
|---|---|
| `g.aliases` | Extraction-time metric matching, not consumer input |
| `gu.quote` | Too verbose (full paragraphs) — raw text is in 8k_packet or transcripts |
| `gu.section` | Extraction detail ("Q&A #3 (Michael Lasser)") |
| `gu.source_key`, `gu.source_refs` | Extraction internals |
| `gu.created` | When extraction ran, not when guidance was stated |
| `gu.label_slug` | Internal slug (metric_id serves this purpose) |
| `gu.basis_raw` | Only 3.8% coverage, extraction artifact |
| `gu.unit_raw` | Extraction artifact |

#### Storage Path

```
earnings-analysis/Companies/{TICKER}/events/{quarter}/guidance_history.json
```

- PIT filter makes it quarter-specific (different quarters see different history)
- Orchestrator passes explicit `out_path` to `build_guidance_history()`
- Default `/tmp/earnings_guidance_{TICKER}.json` for manual/debug invocation only

#### Empty Handling

Zero GuidanceUpdate nodes for ticker:
- JSON: `{"schema_version": "guidance_history.v1", "ticker": "...", "pit": null, "series": [], "summary": {"total_series": 0, "total_updates_raw": 0, "total_updates_collapsed": 0, "earliest_date": null, "latest_date": null}, "assembled_at": "..."}`
- Text: `=== GUIDANCE HISTORY: {TICKER} ===\n(no guidance data available)`
- Orchestrator sets `anchor_flags.has_prior_guidance = false`

#### Ownership Comment

```python
# ─────────────────────────────────────────────────────────────────────
# build_guidance_history() — EARNINGS ORCHESTRATION only
# Reads Guidance/GuidanceUpdate/GuidancePeriod nodes written by
# guidance extraction (guidance_writer.py). Read-only — never writes
# to Neo4j. Changes here do NOT affect guidance extraction.
# ─────────────────────────────────────────────────────────────────────
```

#### CLI Interface

```bash
# Guidance history for earnings orchestration (new):
bash warmup_cache.sh $TICKER --guidance-history [--pit ISO8601] [--out-path /path/to/guidance_history.json]
```

#### Tests (9 cases)

| # | Case | What to verify |
|---|---|---|
| 1 | FIVE (468 raw entries) | Series grouping correct, collapse reduces count (~280), trajectory readable |
| 2 | DLTR (351 entries, segmented) | Dollar Tree / Family Dollar / Total appear as separate series. Total rendered BEFORE segment breakdowns within each metric family. |
| 3 | Unit resolution | `unknown` absorbed into `usd` when only one real unit in base series. `raw_unit_variants` shows `["usd", "unknown"]`. |
| 4 | Mixed real units | `percent` + `basis_points` stay as separate series (not collapsed into each other) |
| 5 | `time_type: instant` | Diluted Share Count instant vs duration are separate series |
| 6 | PIT filter | Same ticker, two PIT dates → later PIT has more entries |
| 7 | Empty ticker | Returns empty JSON structure + text "(no guidance data available)" |
| 8 | Qualitative-only same-day edge case | Two genuinely distinct qualitative statements on the same day for the same series (e.g., different inventory direction) are NOT collapsed. Trivial casing variants ("flat to 3%" vs "Flat to 3%") ARE collapsed. |
| 9 | Segment display canonicalization | Casing variants (e.g., "High-End Consumer" vs "High-end Consumer") group under same `segment_slug`, display segment is deterministic (most frequent label, tie-break lexicographic). |

#### Implementation Order

1. Add query constants (`QUERY_GUIDANCE_HISTORY`, `QUERY_GUIDANCE_HISTORY_PIT`) to `warmup_cache.py`
2. Add `resolve_unit_groups()` helper function (absorb unknown units)
3. Add grouping logic using 6-dimension key with `metric_id` internally
4. Add display segment selection (most frequent label, tie-break lexicographic)
5. Add collapse logic: numeric = same series + fiscal period + given_day + low/mid/high. Qualitative = same + normalized qualitative. Merge sources sorted by priority.
6. Add `build_guidance_history(ticker, pit=None, out_path=None)` function with atomic write
7. Add `--guidance-history` CLI flag to `warmup_cache.py` main()
8. Add ownership comment
9. Run 9 test cases (verify all derivation enum values exist: `collect(DISTINCT gu.derivation)` before hardcoding)

#### Function Location

`warmup_cache.py` — same file as `_fetch_8k_core()`, `run_8k()`, and `build_8k_packet()`. Same Bolt connection via `get_manager()`.

**Ref**: `earnings-orchestrator.md §2a` (guidance_history field, I5 resolution), `guidance-queries.md` (queries 7A-7F, 8B), `guidance_writer.py` (write schema — shows all fields available), `guidance_ids.py` (ID computation, evhash16 formula).

---

### Step 5: Inter-Quarter Context — `build_inter_quarter_context()` (LOCKED)

**Full implementation spec**: [`plannerStep5.md`](plannerStep5.md) — self-contained, supersedes this section where they conflict.

**What**: A unified chronological timeline of EVERYTHING that happened between the previous earnings and the context cutoff — daily prices, news, filings, dividends, splits — assembled as a planner input so it can generate targeted fetch plan questions based on what actually occurred.

**Design decision**: Instead of 3 separate categories (inter_quarter_8k, significant_moves, inter_quarter_news), we build ONE unified timeline. The planner sees the complete picture and generates targeted questions like "Investigate the gap day on Jan 27" or "Fetch full details on the CFO change 8-K" instead of blind generic questions.

**Dual-mode cutoff**: The function is mode-unaware. The orchestrator passes `context_cutoff_ts`:
- **Live**: `decision_cutoff_ts` (include everything available before prediction starts)
- **Historical**: release-session floor (exclude the entire current earnings release cluster, stay PIT-clean)

**Return-window validation (PIT safety)**: Even with the correct event-inclusion cutoff, a previous-day post_market news item's daily/session return windows can extend past the cutoff into the earnings reaction. The builder nulls any return horizon whose `end_ts > context_cutoff_ts`. This prevents 939 return value leaks across pre_market and in_market 8-K cases. See `plannerStep5.md` for exact implementation.

See `plannerStep5.md` "Context Cutoff" section for the exact floor rules.

#### Architecture

```
build_inter_quarter_context(ticker, prev_8k_ts, context_cutoff_ts, out_path=None)
  │
  ├─ 1. Query all trading days: Date-[HAS_PRICE]->Company + SPY + Sector
  │
  ├─ 2. Query all news: News-[INFLUENCES]->Company in date range
  │
  ├─ 3. Query all filings: Report-[PRIMARY_FILER]->Company in date range (all types)
  │     + PRIMARY_FILER return properties (hourly/session/daily stock + sector + industry + macro)
  │
  ├─ 4. Query dividends: Company-[DECLARED_DIVIDEND]->Dividend in date range
  │
  ├─ 5. Merge all by date → chronological timeline
  │
  ├─ 6. Annotate: *** for |adj_return| ≥ 2%, GAP for significant move with no headlines
  │
  ├─ 7. Write JSON (inter_quarter_context.v1) + rendered text
  │
  └─ 8. Atomic write (temp + rename) to out_path
```

#### ⚠️ STALE — The sections below (Date Range, Graph Traversals, Neo4j Data Type Reference, Rendered Text, Queries, Tests, Implementation Order) are from the original Step 5 draft. They use outdated window semantics (`current_8k_date` instead of `context_cutoff_ts`), old counts (74 news / 4 filings), and lack return-window validation. **Use [`plannerStep5.md`](plannerStep5.md) as the sole implementation reference.** The sections below are retained only as historical context.

#### Date Range and PIT

- **Window**: `prev_8k_date` (exclusive) → `current_8k_date` (exclusive)
- **Naturally PIT-safe**: all events in this window predate the current 8-K filing
- Orchestrator gets both dates from `event.json` (prior quarter's `filed_8k` and current quarter's `filed_8k`)

#### Graph Traversals (verified against live Neo4j, 2026-03-22)

**Layer 1: Daily prices** (every trading day in window)
```
Date-[HAS_PRICE]->Company {ticker}     : open, high, low, close, daily_return, volume, vwap, transactions, timestamp
Date-[HAS_PRICE]->MarketIndex {SPY}    : daily_return, close
Company-[:BELONGS_TO]->Industry-[:BELONGS_TO]->Sector
Date-[HAS_PRICE]->Sector               : daily_return (7,544 relationships, good coverage)
Date-[HAS_PRICE]->Industry             : daily_return (35,541 relationships, but some industries have gaps)
```

Note: Industry HAS_PRICE may return null for some industries (e.g., SoftwareApplication). Sector is the reliable comparison. Include industry when available, omit gracefully when null.

**Layer 2: News events** (matched to dates)
```
News-[:INFLUENCES]->Company {ticker}
Properties: created (datetime), title, channels, market_session, authors, url, id
```
**CAUTION**: `channels` and `authors` are stored as **JSON strings** in Neo4j (e.g., `'["News", "Management"]'`), NOT native lists. Must `json.loads()` before use. See "Neo4j Data Type Reference" below.

**Layer 3: Filing events** (all types — 8-K, 10-Q, 10-K)
```
Report-[PRIMARY_FILER]->Company {ticker}
Report properties: created, formType, items, market_session, accessionNo, exhibits, periodOfReport
PRIMARY_FILER return properties:
  hourly_stock, session_stock, daily_stock      (stock reaction to this specific filing)
  hourly_sector, session_sector, daily_sector   (sector context)
  hourly_industry, session_industry, daily_industry
  hourly_macro, session_macro, daily_macro      (broad market context)
```

These PRIMARY_FILER returns are specific to EACH filing — they measure the market reaction to THAT filing event, not just the day. Critical for the planner: "this 8-K caused a -4.92% daily reaction."

**CAUTION**: `items` and `exhibits` are stored as **JSON strings** in Neo4j. `items` is a JSON array string (e.g., `'["Item 2.02: ...", "Item 9.01: ..."]'`); 8,011 Report nodes have `items IS NULL` (10-Q/10-K). `exhibits` is a JSON object string (e.g., `'{"EX-99.1": "https://..."}'`); use `sorted(json.loads(exhibits).keys())` for exhibit_keys. Must `json.loads()` before use. See "Neo4j Data Type Reference" below.

**Layer 4: Dividend events**
```
Company-[:DECLARED_DIVIDEND]->Dividend
Properties: declaration_date, ex_dividend_date, cash_amount, currency, frequency, dividend_type, pay_date, record_date
```

**Layer 5: Split events** (if any exist for this ticker)
```
Company-[*SPLIT*]->Split (relationship name varies — check during implementation)
```

#### Neo4j Data Type Reference (verified 2026-03-23)

Field storage types that require parsing at read time. All counts verified against live production Neo4j.

**JSON String Fields** — stored as raw JSON strings in Neo4j, require `json.loads()`:

| Field | Node.property | Storage type | Example raw value | Parsed result | Verification |
|---|---|---|---|---|---|
| `channels` | `News.channels` | JSON array string | `'["News", "Management"]'` | `["News", "Management"]` | 343,825 News nodes. ALL are JSON_ARRAY strings. 0 NULLs. |
| `authors` | `News.authors` | JSON array string | `'["Benzinga Newsdesk"]'` | `["Benzinga Newsdesk"]` | Same storage type as channels. |
| `items` | `Report.items` | JSON array string | `'["Item 2.02: ...", "Item 9.01: ..."]'` | `["Item 2.02: ...", "Item 9.01: ..."]` | 25,936 JSON_ARRAY strings. 8,011 NULLs (10-Q/10-K filings lack items). |
| `exhibits` | `Report.exhibits` | JSON object string | `'{"EX-99.1": "https://..."}'` | `{"EX-99.1": "https://..."}` | 33,947 JSON_OBJECT strings. 0 NULLs. Keys are exhibit numbers (EX-10.1, EX-99.1, etc.), values are EDGAR URLs. |

**Parse helper** (add to `warmup_cache.py` — use for ALL four JSON string fields above):

```python
def _parse_json_field(raw, fallback=None):
    """Parse a JSON string field from Neo4j. Returns parsed value or fallback.

    Neo4j stores channels, authors, items, exhibits as raw JSON strings.
    This helper handles None, already-parsed values, and parse errors.
    """
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict)):
        return raw  # already parsed (defensive)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback
```

Usage in event assembly:
```python
# News events
channels = _parse_json_field(n['channels'], [])           # → list of strings
authors = _parse_json_field(n['authors'], [])             # → list of strings

# Filing events
items = _parse_json_field(r['items'], [])                 # → list of strings
exhibits = _parse_json_field(r['exhibits'], {})           # → dict
exhibit_keys = sorted(exhibits.keys()) if isinstance(exhibits, dict) else []
```

**Numeric Fields** — Neo4j Bolt driver returns ALL numbers as Python `float`, even integer-valued ones:

| Field | Has fractional values? | JSON output rule | Rendered text rule | Verification |
|---|---|---|---|---|
| `hp.volume` | **YES** — 16,763 / 540,015 rows (3.10%) are fractional. Mostly 2026+ data (Polygon API artifact: 3,815 in 2026-02, 11,419 in 2026-03). CRM has 20 fractional rows (all 2026-02-23+). CRM Dec 2024–Feb 2025 window: 0 fractional. | Keep raw float | `int(v)` when `v == int(v)`, else `f'{v:,.2f}'` | Exact counts verified 2026-03-23 |
| `hp.transactions` | **NO** — 0 / 540,015 fractional rows. Always integer-valued float (e.g., `173551.0`). | Keep raw float | Always safe to `int(v)` | Exact count verified 2026-03-23 |
| `hp.open/high/low/close/vwap` | Yes — inherently decimal (prices) | Keep raw float | Keep decimal as-is | N/A |
| `hp.daily_return`, `spy/sector/industry.daily_return` | Yes — inherently decimal (percentages) | Keep raw float | `f'{v:+.2f}%'` | N/A |
| All `pf.*` return properties | Yes — inherently decimal (percentages) | Keep raw float | `f'{v}%'` (keep precision from graph) | N/A |

**Volume/transactions formatting helper** (for rendered text only):

```python
def _fmt_vol(v):
    """Format volume for rendered text. Int when whole, 2-decimal otherwise."""
    if v is None:
        return '?'
    if v == int(v):
        return f'{int(v):,}'
    return f'{v:,.2f}'

def _fmt_txn(v):
    """Format transactions for rendered text. Always int (verified: 0 fractional rows)."""
    if v is None:
        return '?'
    return f'{int(v):,}'
```

**Date/datetime fields** — all stored as strings in Neo4j:

| Field | Format | Example |
|---|---|---|
| `Date.date` | ISO date string | `'2025-02-05'` |
| `News.created` | ISO datetime with TZ | `'2025-02-05T17:09:48-05:00'` |
| `Report.created` | ISO datetime with TZ | `'2025-02-05T17:05:54-04:00'` |
| `Dividend.declaration_date` | ISO date string | `'2024-12-05'` |
| `Dividend.ex_dividend_date` | ISO date string | `'2024-12-18'` |

String comparison `>` / `<` works correctly for ISO format. To extract calendar day from a datetime: `str(value)[:10]`.

#### Rendered Text Format (LOCKED)

**Every trading day gets a day header.** Events are indented below their date with exact datetime and market_session.

```
=== INTER-QUARTER TIMELINE: CRM (2024-12-03 → 2025-02-26) ===
Industry: SoftwareApplication | Sector: Technology
55 trading days | 74 news | 4 filings | 1 dividends
7 significant move days | 3 gap days

═══════════════════════════════════════════════════════════════════════
2025-02-05 | CRM +1.10% (adj: +0.69%)
  open=345.72  high=348.04  low=338.87  close=347.93
  vol=4,521,009  vwap=344.95  txns=91,660
  SPY +0.41% | Technology +1.39%
═══════════════════════════════════════════════════════════════════════

  17:05 post_market | [8-K] Item 5.02: Departure of Directors; Appointment of Officers
    accession: 0001193125-25-020881 | period: 2025-02-05
    exhibits: EX-10.1
    returns → hourly: -0.15%  session: -2.18%  daily: -4.92%
    sector  → hourly: +0.21%  session: +0.31%  daily: +0.27%
    industry→ hourly: +0.04%  session: +0.02%  daily: +0.18%
    macro   → hourly: -0.04%  session: +0.17%  daily: +0.32%

  17:09 post_market | 📰 Salesforce Says Robin Washington Will Become President
                         And Chief Operating And Financial Officer [Management]

═══════════════════════════════════════════════════════════════════════
2025-02-06 | CRM -4.92% (adj: -5.27%)  ***
  open=337.48  high=337.48  low=329.10  close=330.81
  vol=13,240,635  vwap=332.66  txns=214,731
  SPY +0.35% | Technology +0.27%
═══════════════════════════════════════════════════════════════════════

  07:32 pre_market | 📰 Needham Reiterates Buy, Maintains $400 PT [Analyst Ratings, Price Target]
  09:00 pre_market | 📰 Where Salesforce Stands With Analysts [Analyst Ratings]
  10:00 in_market  | 📰 Salesforce Unusual Options Activity [Options]

═══════════════════════════════════════════════════════════════════════
2025-01-27 | CRM +3.96% (adj: +5.37%)  ***  GAP
  open=332.00  high=353.00  low=330.00  close=347.00
  vol=15,661,109  vwap=...  txns=...
  SPY -1.41% | Technology -4.9%
═══════════════════════════════════════════════════════════════════════

  (no events — gap day: significant move with zero headlines or filings)
```

**Null handling**:
- **JSON**: Include ALL fields in every event, use `null` when unavailable. Consistent schema — consumers never need to handle missing keys.
- **Render**: Omit null/empty lines. Don't render "industry→ hourly: null". Only show fields with actual values. If industry_return is null for a day, skip that column.

**Non-trading days**: Weekends and holidays have no HAS_PRICE data but may still have events (8-K filings, news published on weekends). Include these days in the timeline with `price: null` and only the events listed below. Render as:
```
2025-01-20 | (non-trading day — MLK Day)
  09:15 pre_market | 📰 Salesforce Announces Partnership With... [News]
```

**Format rules**:
- Every trading day gets a day header with full HAS_PRICE data + SPY + Sector
- `***` marker on days where |adj_return| ≥ 2% (draws planner attention to significant moves)
- `GAP` marker on *** days with zero news headlines and zero filings (hidden information flow)
- Events indented below their date, chronologically by timestamp
- Filing events include PRIMARY_FILER return properties (hourly/session/daily × stock/sector/industry/macro)
- Filing events list exhibit keys (EX-10.1, EX-99.1, etc.) — planner can decide whether to fetch full content
- News events: time, market_session, title, channels
- Dividend events: declaration_date, ex_dividend_date, cash_amount, type

#### Day Header Fields

| Field | Source | Purpose |
|---|---|---|
| `date` | Date node | Calendar date |
| `daily_return` | `hp.daily_return` | Stock daily return |
| `adj_return` | `daily_return - spy_return` | Market-adjusted (CRM-specific vs broad market) |
| `open, high, low, close` | `hp.*` | Price context (intraday range, gap up/down from prior close) |
| `volume` | `hp.volume` | Activity level (high volume = conviction) |
| `vwap` | `hp.vwap` | Volume-weighted average price |
| `transactions` | `hp.transactions` | Trade count |
| `spy_return` | SPY `HAS_PRICE` | Broad market context |
| `sector_return` | Sector `HAS_PRICE` | Sector context (move with or against sector?) |
| `industry_return` | Industry `HAS_PRICE` | Industry context (null for some industries — omit if unavailable) |

#### Event Fields

**Report events** (all types — 8-K, 10-Q, 10-K):

| Field | Source | In render | In JSON | Purpose |
|---|---|---|---|---|
| `created` (datetime) | `r.created` | ✅ | ✅ | Exact filing time |
| `market_session` | `r.market_session` | ✅ | ✅ | pre_market, in_market, post_market |
| `form_type` | `r.formType` | ✅ | ✅ | 8-K, 10-Q, 10-K, 8-K/A, etc. |
| `items` | `r.items` | ✅ | ✅ | Which items (e.g., "Item 5.02: Departure of Directors") |
| `accession` | `r.accessionNo` | ✅ | ✅ | Filing identifier (planner can request full content via neo4j-report) |
| `period_of_report` | `r.periodOfReport` | ✅ | ✅ | Fiscal period this filing covers (e.g., "2025-01-31" for Q4) |
| `is_amendment` | `r.isAmendment` | ✅ (flag if true) | ✅ | 8-K/A vs 8-K — amendments are different events |
| `exhibit_keys` | `r.exhibits` (inline keys) | ✅ | ✅ | Exhibit numbers (EX-10.1, EX-99.1) — not full content, just what exists |
| `hourly_stock` | `pf.hourly_stock` | ✅ | ✅ | Stock reaction in first hour after filing |
| `session_stock` | `pf.session_stock` | ✅ | ✅ | Stock reaction over the session |
| `daily_stock` | `pf.daily_stock` | ✅ | ✅ | Stock reaction over the full day |
| `hourly/session/daily_sector` | `pf.*_sector` | ✅ | ✅ | Sector comparison for same time windows |
| `hourly/session/daily_industry` | `pf.*_industry` | ✅ | ✅ | Industry comparison |
| `hourly/session/daily_macro` | `pf.*_macro` | ✅ | ✅ | Broad market (SPY) comparison |
| `id` | `r.id` | — | ✅ | Internal ID (same as accession in practice, preserved for completeness) |
| `filing_links` | `r.primaryDocumentUrl`, `r.linkToTxt`, `r.linkToHtml`, `r.linkToFilingDetails` | — | ✅ | Audit/debug — direct EDGAR links |
| `section_names` | via OPTIONAL MATCH `r-[:HAS_SECTION]->s` | — | ✅ | Content inventory: which sections exist (for 10-Q/10-K, shows Item 7, Item 8, etc.) |
| `has_filing_text` | via OPTIONAL MATCH `r-[:HAS_FILING_TEXT]->ft` | — | ✅ | Boolean: does raw filing text fallback exist? |
| `xbrl_status` | `r.xbrl_status` | — | ✅ | XBRL availability: "COMPLETED", "SKIPPED", etc. |
| `financial_statement_count` | via OPTIONAL MATCH `r-[:HAS_FINANCIAL_STATEMENT]->fs` | — | ✅ | Count of structured financial statement nodes (relevant for 10-Q/10-K) |

**News events**:

| Field | Source | In render | In JSON | Purpose |
|---|---|---|---|---|
| `created` (datetime) | `n.created` | ✅ | ✅ | Exact publish time |
| `market_session` | `n.market_session` | ✅ | ✅ | pre_market, in_market, post_market |
| `title` | `n.title` | ✅ | ✅ | Headline text |
| `channels` | `n.channels` | ✅ | ✅ | Category tags (Analyst Ratings, M&A, Guidance, etc.) |
| `id` | `n.id` | — | ✅ | Benzinga ID (bzNews_*) — for follow-up full article fetch |
| `url` | `n.url` | — | ✅ | Article URL — audit/debug |
| `authors` | `n.authors` | — | ✅ | Author attribution (note: field is `authors`, not `author`) |

**Dividend events**:

| Field | Source | Purpose |
|---|---|---|
| `declaration_date` | `div.declaration_date` | When declared |
| `ex_dividend_date` | `div.ex_dividend_date` | Ex-date (price adjustment) |
| `cash_amount` | `div.cash_amount` | Amount per share |
| `frequency` | `div.frequency` | Quarterly, Annual, etc. |
| `dividend_type` | `div.dividend_type` | Regular, Special, etc. |

#### JSON Schema: `inter_quarter_context.v1`

```json
{
  "schema_version": "inter_quarter_context.v1",
  "ticker": "CRM",
  "window_start": "2024-12-03",
  "window_end": "2025-02-26",
  "industry": "SoftwareApplication",
  "sector": "Technology",
  "days": [
    {
      "date": "2025-02-05",
      "price": {
        "open": 345.72, "high": 348.04, "low": 338.87, "close": 347.93,
        "daily_return": 1.10, "volume": 4521009, "vwap": 344.95, "transactions": 91660,
        "timestamp": "2025-02-05 16:00:00-0500"
      },
      "spy_return": 0.41,
      "sector_return": 1.39,
      "industry_return": null,
      "adj_return": 0.69,
      "is_significant": false,
      "is_gap_day": false,
      "events": [
        {
          "type": "filing",
          "created": "2025-02-05T17:05:59-05:00",
          "market_session": "post_market",
          "form_type": "8-K",
          "items": ["Item 5.02: Departure of Directors; Appointment of Officers"],
          "accession": "0001193125-25-020881",
          "period_of_report": "2025-02-05",
          "is_amendment": false,
          "exhibit_keys": ["EX-10.1"],
          "returns": {
            "hourly_stock": -0.15, "session_stock": -2.18, "daily_stock": -4.92,
            "hourly_sector": 0.21, "session_sector": 0.31, "daily_sector": 0.27,
            "hourly_industry": 0.04, "session_industry": 0.02, "daily_industry": 0.18,
            "hourly_macro": -0.04, "session_macro": 0.17, "daily_macro": 0.32
          },
          "id": "0001193125-25-020881",
          "filing_links": {
            "primary_doc_url": "https://www.sec.gov/Archives/edgar/data/1108524/...",
            "link_to_txt": "https://www.sec.gov/Archives/edgar/data/1108524/...",
            "link_to_html": "https://www.sec.gov/Archives/edgar/data/1108524/...",
            "link_to_filing_details": "https://www.sec.gov/Archives/edgar/data/1108524/..."
          },
          "section_names": ["Item 5.02"],
          "has_filing_text": true,
          "xbrl_status": "SKIPPED",
          "financial_statement_count": 0
        },
        {
          "type": "news",
          "created": "2025-02-05T17:09:48-05:00",
          "market_session": "post_market",
          "title": "Salesforce Says Robin Washington Will Become President And COO/CFO",
          "channels": ["News", "Management"],
          "id": "bzNews_43514109",
          "url": "https://www.benzinga.com/news/25/02/43514109/...",
          "authors": ["Benzinga Newsdesk"]
        }
      ]
    },
    {
      "date": "2025-02-06",
      "price": {
        "open": 337.48, "high": 337.48, "low": 329.10, "close": 330.81,
        "daily_return": -4.92, "volume": 13240635, "vwap": 332.66, "transactions": 214731,
        "timestamp": "2025-02-06 16:00:00-0500"
      },
      "spy_return": 0.35,
      "sector_return": 0.27,
      "industry_return": null,
      "adj_return": -5.27,
      "is_significant": true,
      "is_gap_day": false,
      "events": [
        {
          "type": "news",
          "created": "2025-02-06T07:32:16-05:00",
          "market_session": "pre_market",
          "title": "Needham Reiterates Buy on Salesforce, Maintains $400 Price Target",
          "channels": ["News", "Price Target", "Reiteration", "Analyst Ratings"]
        }
      ]
    },
    {
      "date": "2025-01-27",
      "price": {"open": 332, "close": 347, "daily_return": 3.96, "...": "..."},
      "spy_return": -1.41,
      "sector_return": -4.9,
      "adj_return": 5.37,
      "is_significant": true,
      "is_gap_day": true,
      "events": []
    }
  ],
  "summary": {
    "total_trading_days": 55,
    "significant_move_days": 7,
    "gap_days": 3,
    "total_news": 74,
    "total_filings": 4,
    "total_dividends": 1,
    "price_change_pct": -10.2,
    "spy_change_pct": 1.3
  },
  "assembled_at": "2026-03-22T16:00:00Z"
}
```

#### Queries

```python
# 1. All trading days with stock + SPY + sector returns
QUERY_INTER_QUARTER_PRICES = """
MATCH (d:Date)-[hp:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date > $start AND d.date < $end
OPTIONAL MATCH (d)-[spy:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)-[:BELONGS_TO]->(sec:Sector)
OPTIONAL MATCH (d)-[sec_hp:HAS_PRICE]->(sec)
OPTIONAL MATCH (d)-[ind_hp:HAS_PRICE]->(ind)
RETURN d.date AS date,
       hp.open AS open, hp.high AS high, hp.low AS low, hp.close AS close,
       hp.daily_return AS daily_return, hp.volume AS volume,
       hp.vwap AS vwap, hp.transactions AS transactions, hp.timestamp AS timestamp,
       spy.daily_return AS spy_return,
       sec_hp.daily_return AS sector_return, sec.name AS sector_name,
       ind_hp.daily_return AS industry_return, ind.name AS industry_name
ORDER BY d.date
"""

# 2. All news in date range (with id/url/authors for JSON-only fields)
QUERY_INTER_QUARTER_NEWS = """
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE toString(n.created) > $start AND toString(n.created) < $end
RETURN n.created AS created, n.title AS title, n.channels AS channels,
       n.market_session AS market_session,
       n.id AS news_id, n.url AS url, n.authors AS authors
ORDER BY n.created
"""

# 3. All filings with PRIMARY_FILER return properties + content inventory
QUERY_INTER_QUARTER_FILINGS = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE toString(r.created) > $start AND toString(r.created) < $end
OPTIONAL MATCH (r)-[:HAS_SECTION]->(sec:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
RETURN r.created AS created, r.formType AS form_type, r.items AS items,
       r.accessionNo AS accession, r.id AS report_id,
       r.market_session AS market_session,
       r.exhibits AS exhibits, r.periodOfReport AS period_of_report,
       r.isAmendment AS is_amendment, r.xbrl_status AS xbrl_status,
       r.primaryDocumentUrl AS primary_doc_url, r.linkToTxt AS link_to_txt,
       r.linkToHtml AS link_to_html, r.linkToFilingDetails AS link_to_filing_details,
       collect(DISTINCT sec.section_name) AS section_names,
       count(DISTINCT ft) > 0 AS has_filing_text,
       count(DISTINCT fs) AS financial_statement_count,
       pf.hourly_stock AS hourly_stock, pf.session_stock AS session_stock,
       pf.daily_stock AS daily_stock,
       pf.hourly_sector AS hourly_sector, pf.session_sector AS session_sector,
       pf.daily_sector AS daily_sector,
       pf.hourly_industry AS hourly_industry, pf.session_industry AS session_industry,
       pf.daily_industry AS daily_industry,
       pf.hourly_macro AS hourly_macro, pf.session_macro AS session_macro,
       pf.daily_macro AS daily_macro
ORDER BY r.created
"""

# 4. Dividends in date range
QUERY_INTER_QUARTER_DIVIDENDS = """
MATCH (c:Company {ticker: $ticker})-[:DECLARED_DIVIDEND]->(div:Dividend)
WHERE div.declaration_date >= $start AND div.declaration_date < $end
RETURN div.declaration_date AS declaration_date, div.ex_dividend_date AS ex_date,
       div.cash_amount AS cash_amount, div.currency AS currency,
       div.frequency AS frequency, div.dividend_type AS dividend_type,
       div.pay_date AS pay_date, div.record_date AS record_date
ORDER BY div.declaration_date
"""
```

Note: `Date.date` is stored as STRING in Neo4j (verified 2026-03-23, sample: `'2025-02-05'`). String comparison `>` / `<` works correctly for ISO date format. The price query uses `d.date > $start AND d.date < $end` (both exclusive). The news and filings queries use `toString(n.created)` / `toString(r.created)` for the same comparison — these are ISO datetime strings with timezone (e.g., `'2025-02-05T17:09:48-05:00'`) and string comparison works correctly because the format is lexicographically orderable.

#### Storage Path

```
earnings-analysis/Companies/{TICKER}/events/{quarter}/inter_quarter_context.json
```

Same pattern as 8k_packet and guidance_history. Quarter directory, explicit `out_path`, `/tmp/` default for debug.

#### Empty Handling

If no trading days exist in the window (unlikely but defensive):
- JSON: `{"schema_version": "inter_quarter_context.v1", "ticker": "...", "days": [], "summary": {"total_trading_days": 0, ...}, "assembled_at": "..."}`
- Text: `=== INTER-QUARTER TIMELINE: {TICKER} ===\n(no data available for window)`

#### Ownership Comment

```python
# ─────────────────────────────────────────────────────────────────────
# build_inter_quarter_context() — EARNINGS ORCHESTRATION only
# Reads Date/HAS_PRICE, News/INFLUENCES, Report/PRIMARY_FILER,
# Dividend nodes. Read-only — never writes to Neo4j.
# ─────────────────────────────────────────────────────────────────────
```

#### CLI Interface

```bash
# Add to warmup_cache.py module docstring:
#   warmup_cache.py TICKER --inter-quarter --prev-8k ISO8601 --current-8k ISO8601 [--out-path PATH]

# Add to warmup_cache.sh usage comment:
#   Bash("bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh TICKER --inter-quarter --prev-8k ISO8601 --current-8k ISO8601 [--out-path PATH]")

# Example:
bash warmup_cache.sh CRM --inter-quarter --prev-8k 2024-12-03T16:03:38-05:00 --current-8k 2025-02-26T16:03:55-05:00
bash warmup_cache.sh CRM --inter-quarter --prev-8k 2024-12-03T16:03:38-05:00 --current-8k 2025-02-26T16:03:55-05:00 --out-path earnings-analysis/Companies/CRM/events/Q4_FY2025/inter_quarter_context.json

# Default output (no --out-path):
#   /tmp/earnings_inter_quarter_{TICKER}.json
```

**CLI parsing in `main()`** — add BEFORE the `--guidance-history` branch (so `--inter-quarter` is checked first):

```python
if '--inter-quarter' in sys.argv:
    prev_8k = None
    if '--prev-8k' in sys.argv:
        idx = sys.argv.index('--prev-8k')
        if idx + 1 >= len(sys.argv):
            print("Error: --prev-8k requires ISO8601 argument", file=sys.stderr)
            sys.exit(1)
        prev_8k = sys.argv[idx + 1]
    else:
        print("Error: --inter-quarter requires --prev-8k", file=sys.stderr)
        sys.exit(1)
    current_8k = None
    if '--current-8k' in sys.argv:
        idx = sys.argv.index('--current-8k')
        if idx + 1 >= len(sys.argv):
            print("Error: --current-8k requires ISO8601 argument", file=sys.stderr)
            sys.exit(1)
        current_8k = sys.argv[idx + 1]
    else:
        print("Error: --inter-quarter requires --current-8k", file=sys.stderr)
        sys.exit(1)
    out_path = None
    if '--out-path' in sys.argv:
        op_idx = sys.argv.index('--out-path')
        if op_idx + 1 >= len(sys.argv):
            print("Error: --out-path requires PATH argument", file=sys.stderr)
            sys.exit(1)
        out_path = sys.argv[op_idx + 1]
    build_inter_quarter_context(ticker, prev_8k, current_8k, out_path)
```

#### Tests (9 cases)

All test case counts verified against live Neo4j on 2026-03-23.

| # | Case | What to verify |
|---|---|---|
| 1 | CRM Dec 2024 → Feb 2025 | Full timeline with 55 trading days, **74** news, **4** filings, **1** dividend. 7 significant move days, 3 gap days. |
| 2 | Day with filing + news + significant move | Feb 5-6 2025: 8-K Item 5.02 with PRIMARY_FILER returns (hourly=-0.15%, session=-2.18%, daily=-4.92%), news below, *** on Feb 6 (-5.27% adj) |
| 3 | Gap day | Jan 27 2025: +5.37% adj, zero headlines, zero filings → GAP marker |
| 4 | Filing PRIMARY_FILER returns | All 12 return fields present (hourly/session/daily × stock/sector/industry/macro). Sector context shows CRM-specific vs broad market. |
| 5 | Sector/Industry returns | Sector (Technology) returns present on all trading days. Industry (SoftwareApplication) returns may be null — render omits null gracefully (no "industry→ hourly: None" lines). |
| 6 | Dividend in window | CRM Dec 5 2024: $0.40 Regular Quarterly dividend declared, ex-date 2024-12-18. Event appears under the Dec 5 trading day. |
| 7 | Empty window | Non-existent ticker or date range with no data → empty JSON + text `(no data available for window)` |
| 8 | JSON string field parsing | `channels` renders as `[News, Management]` not `[, ", N, e, w, s, ...]`. `items` renders as parsed list. `exhibits` keys extracted correctly. `authors` in JSON output is a list not raw string. Verify with any CRM news/filing event. |
| 9 | Volume formatting | For the CRM Dec 2024–Feb 2025 window: all volumes should render as integers (0 fractional in this window). For 2026+ data: fractional volumes render with 2 decimals (e.g., `15,498,141.34`). `transactions` always renders as integer. |

#### Implementation Order

1. Add `_parse_json_field(raw, fallback=None)` helper function (see "Neo4j Data Type Reference" above for exact code)
2. Add `_fmt_vol(v)` and `_fmt_txn(v)` helper functions (see "Neo4j Data Type Reference" above for exact code)
3. Add 4 query constants to `warmup_cache.py` (`QUERY_INTER_QUARTER_PRICES`, `QUERY_INTER_QUARTER_NEWS`, `QUERY_INTER_QUARTER_FILINGS`, `QUERY_INTER_QUARTER_DIVIDENDS`)
4. Add `build_inter_quarter_context(ticker, prev_8k_date, current_8k_date, out_path=None)` function:
   a. Extract calendar-day start/end from datetime params: `start = str(prev_8k_date)[:10]`, `end = str(current_8k_date)[:10]`
   b. Run 4 queries with `{'ticker': ticker, 'start': start, 'end': end}`
   c. Build day_map from prices (keyed by `d.date` string); compute `adj_return = daily_return - spy_return`
   d. Parse and merge news events into day_map — use `_parse_json_field()` for `channels` and `authors`; extract calendar day from `str(created)[:10]`; create non-trading-day entries for news on weekends/holidays
   e. Parse and merge filing events into day_map — use `_parse_json_field()` for `items` and `exhibits`; extract `exhibit_keys = sorted(parsed_exhibits.keys())`
   f. Merge dividend events into day_map by `declaration_date`
   g. Sort all days chronologically; annotate `is_significant` (`|adj_return| >= 2.0`) and `is_gap_day` (significant + zero events)
   h. Sort events within each day by `created` timestamp
5. Add `render_inter_quarter_text(packet)` function:
   - Day headers: use `_fmt_vol()` for volume, `_fmt_txn()` for transactions
   - News channels: render parsed list as `[Ch1, Ch2]` (already a Python list after `_parse_json_field()`)
   - Filing items: render parsed list joined by `; `
   - Omit null industry/sector lines in render (JSON keeps them as `null`)
6. Add `--inter-quarter` CLI flag with `--prev-8k` and `--current-8k` parameters to `main()`
7. Add ownership comment (see exact text in "Ownership Comment" section above)
8. Atomic write (temp file + `os.replace()`) — same pattern as `build_8k_packet()` and `build_guidance_history()`
9. Update shell wrapper `warmup_cache.sh` usage comment to include `--inter-quarter`
10. Update `warmup_cache.py` module docstring to include `--inter-quarter` usage example
11. Run 9 test cases

#### Function Location

`warmup_cache.py` — same file as `build_8k_packet()` and `build_guidance_history()`. Same Bolt connection via `get_manager()`.

**Ref**: `predictor.md §4b` (inputs 3-5), `earnings-orchestrator.md §2a` (fetched_data schema), `entity-queries/SKILL.md` (HAS_PRICE patterns), `news-queries/SKILL.md` (INFLUENCES patterns), `report-queries/SKILL.md` (PRIMARY_FILER patterns).

---

### Step 6: Agent Catalog (Static Embed)

**What**: The 14 valid `fetch[].agent` values, embedded directly in the planner prompt.

**Format**: One-line description per agent with domain and tier guidance:

```
=== AVAILABLE DATA AGENTS ===
Tier 0 (primary — fast, structured, reliable):
  neo4j-report:          SEC filings (8-K, 10-K, 10-Q text, exhibits, sections)
  neo4j-transcript:      Earnings call transcripts (prepared remarks, Q&A)
  neo4j-xbrl:            Structured financials (EPS, revenue, margins from XBRL)
  neo4j-entity:          Company metadata, price series, dividends, splits
  neo4j-news:            News articles (fulltext search over ingested corpus)
  neo4j-vector-search:   Semantic similarity search (News + QAExchange)
  alphavantage-earnings:  Consensus EPS/revenue estimates, actuals, surprise

Tier 1 (fallback — broader coverage, slower):
  yahoo-earnings:         Earnings history + analyst upgrades/downgrades
  bz-news-api:            Benzinga headlines with channels/tags (on-demand API)
  perplexity-search:      Web search (URLs + snippets)
  perplexity-ask:         Quick factual Q&A with citations
  perplexity-sec:         SEC EDGAR filing search

Tier 2 (expensive — use as LAST-RESORT fallback only):
  perplexity-research:    Deep multi-source synthesis (slow, 30s+)
  perplexity-reason:      Multi-step reasoning with chain-of-thought

RULES:
- Never place perplexity-research or perplexity-reason in Tier 0.
- Any agent name not in this list is INVALID and will be rejected.
- Planned agents (web-search, sec-fulltext, presentations) are NOT yet available.
```

**Delivery**: Static embed in planner SKILL.md prompt. 14 agents, changes rarely. No external file needed.

**Note on cost control**: Tier guidance is soft — planner decides — but the `fetch` tiered array-of-arrays structurally enforces sequential fallback. If perplexity-research is in Tier 2, it literally only runs when Tier 0 and Tier 1 both returned nothing.

**Ref**: `earnings-orchestrator.md §2b` (full agent catalog with PIT status), `DataSubAgents.md` (implementation details).

---

### Step 7: fetch_plan.json Output Schema

**Status**: Placeholder. Schema is locked in `earnings-orchestrator.md §2b`. Requires deep walkthrough of every field before implementation.

**Schema reference** (`fetch_plan.v1`):
```json
{
  "schema_version": "fetch_plan.v1",
  "ticker": "...",
  "quarter": "...",
  "filed_8k": "...",
  "questions": [
    {
      "id": "guidance_delta",
      "question": "...",
      "why": "...",
      "output_key": "guidance_context",
      "fetch": [
        [{"agent": "neo4j-report", "query": "..."}, {"agent": "neo4j-transcript", "query": "..."}],
        [{"agent": "perplexity-search", "query": "..."}]
      ]
    }
  ]
}
```

**Key points to flesh out later**:
- Every field's exact semantics and validation rules
- How `output_key` maps to `fetched_data{}` keys and `anchor_flags`
- How the `query` string is constructed (natural language prompt for the agent)
- Examples for all 4 fetch patterns (single, parallel, fallback, parallel+fallback)

**Ref**: `earnings-orchestrator.md §2b` (full contract with examples and 4 fetch patterns).

---

### Step 8: Orchestrator Validation (Post-Planner)

**What**: After the planner returns, the orchestrator validates `fetch_plan.json` before executing it.

**Validation checks** (from `earnings-orchestrator.md §2b`):
1. Valid JSON? → **Block** if not
2. Required top-level fields present (`schema_version`, `ticker`, `quarter`, `filed_8k`, `questions`)? → **Block** if missing
3. Every `fetch[].agent` value in the 14-agent catalog? → **Block** if invalid name
4. Each question has required fields (`id`, `question`, `why`, `output_key`, `fetch`)? → **Block** if missing
5. **Sanity check** (R5): At least one question targeting consensus data AND one targeting prior financials? → **Warn** (log, not block). Planner may have valid reasons to omit; U1 self-corrects.

**Where validation lives**: Inline Python in the orchestrator. Not a hook (planner is a Skill fork, returns output to orchestrator context — no file write to hook on until orchestrator persists it).

**Ref**: `earnings-orchestrator.md §2b` (execution semantics point 4, sanity check point 5).

---

### Step 9: Context Pollution Management

**What**: When the orchestrator executes the fetch plan via Task fan-out, agent results return to the orchestrator's context. For historical mode (10+ quarters), this can grow large.

**Current design**: Agent results come back in-context. Orchestrator merges them into `context_bundle.json`, writes to disk, renders to text for predictor.

**Question**: Can agents write results directly to files instead of returning in-context?

**Analysis**:
- Task-spawned agents CAN use `Write` tool to write files
- Orchestrator could pass a file path in the agent prompt: `"Write results to events/{quarter}/fetch/{output_key}.json"`
- Orchestrator then reads only the file paths, not the full content
- This keeps orchestrator context clean across many quarters

**Feasibility**: Yes, this works today. Each data subagent already has `Write` or `Bash` in its tools. The orchestrator prompt just needs to instruct: "Write result to {path}" and then read the file.

**Trade-off**:
| Approach | Pros | Cons |
|---|---|---|
| In-context (current design) | Simpler orchestrator logic, no file coordination | Context grows with each quarter's agent results |
| Write-to-file | Clean orchestrator context, scales to many quarters | Agent must write correct path, orchestrator must verify file exists, slightly more complex |

**Resolved**: Use in-context returns (simpler orchestrator logic). The 1M context window gives significant headroom. If context pressure becomes a problem in historical mode (10+ quarters), switch to write-to-file — the architecture supports both without redesign.

**Ref**: `earnings-orchestrator.md §2a` (context bundle assembly), `Infrastructure.md` (Task tool behavior).

---

### Step 10: Rules and Constraints (Expanded)

**Core rules** (from §5 Design Rules):
1. Planner relevance principle: each fetch should map to 8-K claim, core dimension, or U1 lesson.
2. Keep schema deterministic and simple for parsing.
3. Prefer over-fetch to under-fetch (orchestrator parallelizes).
4. Avoid free-form prose outputs.

**Additional rules for implementation**:
5. Never place `perplexity-research` or `perplexity-reason` in Tier 0. Reserve for Tier 2 fallback only.
6. Always include at least one question for consensus (`consensus_vs_actual`) and one for prior financials (`prior_financials`). Omitting these triggers orchestrator sanity-check warning.
7. If 8-K mentions a specific operating metric (e.g., adjusted EBITDA, free cash flow), consider including a question targeting that metric. **Note**: XBRL data (`neo4j-xbrl`) may not be updated on time for the current quarter's filing — prior-quarter XBRL is reliable, current-quarter may lag. Use XBRL for historical baselines, not current-quarter actuals.
8. U1 `planner_lessons` are strong soft priors — if a lesson says "add peer data," the planner should include it unless current-quarter 8-K evidence clearly makes it irrelevant. Lessons carry weight because they come from actual attribution analysis, but current-quarter evidence still wins (consistent with Step 3 guardrail).
9. Do NOT fetch return labels (`daily_stock`, `hourly_stock`) — these are prediction outcomes, not inputs.
10. Do NOT worry about PIT — orchestrator appends `--pit` to agent prompts in historical mode. Planner is PIT-unaware.
11. Custom question IDs are allowed (stable `snake_case`, no ticker/quarter encoding). Use canonical IDs for the 4 anchor-flag-linked questions (`consensus_vs_actual`, `prior_financials`, `prior_transcript_context`, and `guidance_delta`/`guidance_context` output_key). Custom IDs for everything else.

**Ref**: `earnings-orchestrator.md §2b` (noise policy, canonical IDs, tier guidance), `predictor.md §4b` (XBRL timing note).

---

### Step 11: Canonical Question IDs and Anchor Flags

**7 canonical IDs** (from `earnings-orchestrator.md §2b`; reduced from 9 after unifying the 3 inter-quarter fields into one):

| ID | output_key | Drives anchor_flag? | Typical Tier 0 agents |
|---|---|---|---|
| `guidance_delta` | `guidance_context` | (via `guidance_history`) | neo4j-report, neo4j-transcript |
| `consensus_vs_actual` | `consensus_context` | `has_consensus` | alphavantage-earnings |
| `prior_financials` | `prior_financials` | `has_prior_financials` | neo4j-xbrl |
| `prior_transcript_context` | `prior_transcript_context` | `has_transcript_context` | neo4j-transcript |
| `peer_earnings` | `peer_earnings` | — | neo4j-entity |
| `sector_context` | `sector_context` | — | perplexity-search/ask |
| `inter_quarter_context` | `inter_quarter_context` | — | (pre-assembled by Step 5 `build_inter_quarter_context()` — unified timeline replaces the old separate `inter_quarter_8k`, `significant_moves`, `inter_quarter_news`) |

**Not limited to 9**: Custom IDs allowed for non-standard data needs. Must be `snake_case`, must not encode ticker/quarter. Examples: `acquisition_context`, `regulatory_risk`, `management_change`.

**Critical**: 3 anchor flags are driven by planner output_keys (`consensus_context` → `has_consensus`, `prior_financials` → `has_prior_financials`, `prior_transcript_context` → `has_transcript_context`). These output_keys MUST use their canonical names — if the planner invents a different key for consensus data, the anchor flag won't trigger. The 4th anchor flag (`has_prior_guidance`) is driven by the `guidance_history` bundle field from Step 4 (assembled by the orchestrator, not a planner output_key).

**Ref**: `earnings-orchestrator.md §2a` (anchor_flags definition), `§2b` (canonical IDs table), `§2c` (missing-data policy).

---

### Step 12: Testing Plan

**Phase 1: Smoke test** (single quarter, interactive)
1. Pick a well-known ticker with rich data (e.g., CRM Q1 FY2025)
2. Manually assemble planner inputs (8k_packet.json via `build_8k_packet()`, guidance_history.json via `build_guidance_history()`, empty `planner_lessons_history: []`, agent catalog in prompt)
3. Invoke planner skill interactively
4. Verify: valid JSON, all required fields, agent names in catalog, reasonable question set

**Phase 2: Historical validation** (3-5 quarters)
1. Run planner on 3-5 quarters for 1-2 tickers
2. Compare fetch plans: are questions relevant to each 8-K? Do they cover core dimensions?
3. Check: does the planner use canonical IDs for standard questions?
4. Check: are tier assignments reasonable (neo4j Tier 0, perplexity Tier 1-2)?

**Phase 3: Orchestrator integration** (requires orchestrator rewrite)
1. Orchestrator calls planner → validates fetch_plan → executes → assembles bundle
2. End-to-end test: does the predictor receive a well-formed context bundle?

**Ref**: `earnings-orchestrator.md §7` (Phase B1: Planner + Predictor), `§8` (module readiness snapshot).
