# Extraction Pipeline — Implementation Plan

**Status: APPROVED** — Implement phases in order. Each phase has a validation gate; do not start the next phase until the current gate passes.

**Baseline lock**: The current `/guidance-transcript` pipeline produces near-optimal output. The entire existing pipeline — orchestrator skill, agents, reference files, scripts — stays FROZEN and untouched throughout all phases. We build the new infrastructure ALONGSIDE the old by duplicating files (with new names fitting the extraction framework). The originals are never moved, renamed, or edited. Retirement only happens much later, after thorough parallel-run verification proves the new infrastructure matches or exceeds the original output quality.

### Guiding Principles

1. **Super minimalism** — zero over-engineering, simplest thing that works
2. **100% output reliability** — guidance-transcript quality is the gold standard, never degrade it
3. **Plug-and-play** — trivially easy to add/remove any extraction type for any data asset
4. **Always actionable** — every section points toward clear implementation; zero paralysis by analysis

**Version**: 1.4 | 2026-03-04
**Goal**: Generalize the guidance extraction pipeline into a reusable framework for ANY extraction type across ALL data assets.
**Archive**: Full deliberation history in `extractionPipeline-v04-archive.md`

---

## §0: Current State

### How It Works Today

```
User or SDK:
  /guidance-transcript AAPL transcript AAPL_2025-01-30T17.00 MODE=write

Skill: .claude/skills/guidance-transcript/SKILL.md
  (14 lines — thin orchestrator, spawns 2 agents sequentially)

  ┌─────────────────────────────────────────────────────────────┐
  │ Agent 1: Task(guidance-extract)                              │
  │   AAPL transcript AAPL_2025-01-30T17.00 MODE=write         │
  │                                                             │
  │   Auto-loads (3 files, MANDATORY):                          │
  │     1. SKILL.md (733 lines — schema, fields, validation)    │
  │     2. QUERIES.md (755 lines — 42 Cypher queries)           │
  │     3. PROFILE_TRANSCRIPT.md (242 lines — transcript rules) │
  │                                                             │
  │   Pipeline:                                                 │
  │     Step 1: Load Context                                    │
  │       ├── 1A: Company + CIK                                 │
  │       ├── 1B: FYE from 10-K                                 │
  │       ├── 2A: Concept usage cache                           │
  │       ├── 2B: Member profile cache                          │
  │       ├── 7A: Existing guidance tags                        │
  │       └── 7D: Prior extractions for this source             │
  │     Step 2: Fetch Source Content                             │
  │       ├── 3B: Structured transcript (PR + Q&A)              │
  │       ├── 3C: Q&A Section fallback (~40 transcripts)        │
  │       └── 3D: Full text fallback (~28 transcripts)          │
  │     Step 3: LLM Extraction (PR only)                        │
  │       ├── Route to PROFILE_TRANSCRIPT rules                 │
  │       ├── Extract: quote, period, basis, metric, values...  │
  │       └── Quality filters from SKILL.md §13                 │
  │     Step 4: Deterministic Validation (via Bash scripts)     │
  │       ├── guidance_ids.py: period routing, unit canon, IDs  │
  │       ├── Basis validation (explicit-only rule)             │
  │       ├── xbrl_qname resolution from concept cache          │
  │       └── Member matching from member cache                 │
  │     Step 5: Write (via Bash → guidance_write.sh)            │
  │       ├── Write JSON to /tmp/gu_{TICKER}_{SOURCE_ID}.json   │
  │       ├── guidance_write.sh → guidance_write_cli.py         │
  │       │   → guidance_writer.py                              │
  │       └── MERGE to Neo4j (or dry-run)                       │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ Agent 2: Task(guidance-qa-enrich)                            │
  │   AAPL transcript AAPL_2025-01-30T17.00 MODE=write         │
  │                                                             │
  │   Auto-loads: same 3 files                                  │
  │                                                             │
  │   Pipeline:                                                 │
  │     Step 1: Load Context (same as Phase 1)                  │
  │     Step 2: Load Existing Items                             │
  │       ├── 7E: Full readback of Phase 1 items                │
  │       └── 7F: Prior-transcript baseline (completeness)      │
  │     Step 3: Load Q&A Content                                │
  │       ├── 3F: Q&A exchanges only                            │
  │       └── 3C: QuestionAnswer fallback                       │
  │     Step 4: Q&A Enrichment                                  │
  │       ├── Per-exchange verdict: ENRICHES / NEW / NO_GUIDANCE│
  │       ├── Q&A Analysis Log (mandatory)                      │
  │       └── Completeness check vs 7F baseline                 │
  │     Step 5: Assemble (changed/new items only)               │
  │     Step 6: Validate + Write (same script path)             │
  └─────────────────────────────────────────────────────────────┘
```

### K8s Trigger Path

```
trigger-guidance.py
  ├── Queries Neo4j: Transcript.guidance_status IS NULL
  ├── Groups by ticker (1 queue item per company)
  └── LPUSH to Redis "earnings:trigger"

earnings_worker.py (K8s pod, KEDA 0→7)
  ├── BRPOP from "earnings:trigger"
  ├── Parses payload: {ticker, source_ids[], mode}
  ├── For each source_id (sequential within company):
  │     ├── mark_status(in_progress)
  │     ├── Claude SDK: query("/guidance-transcript {ticker} transcript {sid} MODE={mode}")
  │     └── mark_status(completed|failed)
  ├── On shutdown: re-queues remaining
  └── On failure: retry up to 3x, then dead-letter queue
```

### File Inventory

| Layer | File | Lines | Role |
|-------|------|-------|------|
| **Skill (orchestrator)** | `.claude/skills/guidance-transcript/SKILL.md` | 14 | Thin orchestrator — spawns 2 agents |
| **Agent (Phase 1)** | `.claude/agents/guidance-extract.md` | 285 | PR extraction agent |
| **Agent (Phase 2)** | `.claude/agents/guidance-qa-enrich.md` | 182 | Q&A enrichment agent |
| **Reference (schema)** | `.claude/skills/guidance-inventory/SKILL.md` | 733 | Schema, fields, validation, quality filters |
| **Reference (queries)** | `.claude/skills/guidance-inventory/QUERIES.md` | 755 | 42 Cypher queries |
| **Profile (transcript)** | `.claude/skills/guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | 242 | Transcript-specific extraction rules |
| **Profile (8-K)** | `.claude/skills/guidance-inventory/reference/PROFILE_8K.md` | 194 | 8-K-specific extraction rules |
| **Profile (news)** | `.claude/skills/guidance-inventory/reference/PROFILE_NEWS.md` | 223 | News-specific extraction rules |
| **Profile (10-Q/10-K)** | `.claude/skills/guidance-inventory/reference/PROFILE_10Q.md` | 237 | 10-Q/10-K-specific extraction rules |
| **Script (IDs)** | `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py` | ~600 | Deterministic IDs, unit canon, period routing |
| **Script (writer)** | `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py` | ~400 | Cypher MERGE patterns |
| **Script (CLI)** | `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py` | ~200 | CLI entry: JSON → IDs → write |
| **Script (shell)** | `.claude/skills/earnings-orchestrator/scripts/guidance_write.sh` | 22 | Venv + Neo4j env setup |
| **Trigger** | `scripts/trigger-guidance.py` | 189 | Neo4j query → Redis LPUSH |
| **Worker** | `scripts/earnings_worker.py` | 368 | Redis BRPOP → Claude SDK |
| **Canary** | `scripts/canary_sdk.py` | 235 | K8s deployment validation |
| **Separate pipeline** | `scripts/earnings_trigger.py` | 139 | Invokes `/earnings-orchestrator` (prediction + attribution). NOT part of extraction framework. **Status unclear** — shares `earnings:trigger` queue name; likely dormant. Confirm before queue rename (§6 Q5). |
| **Reference (quality)** | `.claude/skills/evidence-standards/SKILL.md` | 47 | Anti-hallucination rules. NOT loaded by current agents — added to new agents in Phase 2.1. |
| **Spec (historical)** | `.claude/plans/guidanceInventory.md` | 1231 | Architecture spec. Partially stale — working code is source of truth. Archive as historical reference. |

---

## §1: Architecture

### The 3-Manual System

An agent is a robot worker. You hand it 3 instruction manuals:

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    EXTRACTION AGENT                         │
  │                                                             │
  │  Reads 3 manuals, then does its job:                        │
  │                                                             │
  │  Manual 1: WHAT to extract ──► guidance-inventory/SKILL.md  │
  │            (fields, schema,    (one per job type)            │
  │             validation)                                     │
  │                                                             │
  │  Manual 2: HOW to fetch    ──► guidance-inventory/QUERIES.md │
  │            data from Neo4j     (SHARED, one source of truth)│
  │                                                             │
  │  Manual 3: HOW to read     ──► extraction/assets/           │
  │            THIS source         transcript.md                │
  │            (scan scope,        (one per data asset)         │
  │             fallbacks)                                      │
  │                                                             │
  │  Then calls scripts:       ──► earnings-orchestrator/       │
  │  guidance_ids.py → writer      scripts/                     │
  │  (one set per job type)        (shared directory)           │
  └─────────────────────────────────────────────────────────────┘
```

- **Manual 1** = type contract. Different for each extraction type. Guidance has `low/mid/high`, analyst comments would have completely different fields.
- **Manual 2** = source fetch queries. SHARED — stays in `guidance-inventory/QUERIES.md`, all agents (old and new) read from the same file. Zero drift risk.
- **Manual 3** = asset profile. Different per data source — transcripts have PR + Q&A sections, 8-Ks have exhibits.

Everything in this plan generalizes these three layers so they work for ANY extraction type across ANY data asset.

### The DRY Principle — What Lives Where

```
                         SHARED BY EVERYONE
                    (touch once, all benefit)
          ┌──────────────────────────────────────────┐
          │                                          │
          │  guidance-inventory/QUERIES.md            │
          │  (755 lines, 42 Cypher queries)          │
          │                                          │
          │  earnings-orchestrator/scripts/           │
          │  (fiscal_math.py, pit_fetch.py,          │
          │   guidance_write.sh, shared utils)        │
          │                                          │
          └──────────────────────────────────────────┘
                    │                       │
        ┌───────────┘                       └──────────┐
        ▼                                              ▼
   PER JOB TYPE                                  PER DATA ASSET
   (one set per WHAT)                            (one file per WHERE)
┌────────────────────────┐              ┌────────────────────────────┐
│                        │              │                            │
│  guidance-inventory/   │              │  extraction/assets/        │
│    SKILL.md (contract) │              │    transcript.md           │
│                        │              │    8k.md                   │
│  scripts/              │              │    10q.md                  │
│    guidance_ids.py     │              │    news.md                 │
│    guidance_writer.py  │              │                            │
│    guidance_write_cli  │              │  Each file has:            │
│                        │              │    ## Asset Structure      │
│  ┌──────────────────┐  │              │      (shared by all types) │
│  │ Future:          │  │              │    ## Extraction Rules:    │
│  │ analyst-inventory │  │              │      Guidance             │
│  │   SKILL.md       │  │              │      (type-specific hints) │
│  │ analyst_ids.py   │  │              │    ## Extraction Rules:    │
│  │ analyst_writer   │  │              │      Analyst  [future]    │
│  └──────────────────┘  │              │                            │
└────────────────────────┘              └────────────────────────────┘
        │                                          │
        └──────────────┐    ┌──────────────────────┘
                       ▼    ▼
              THE INTERSECTION
         (section inside asset file)

  "## Extraction Rules: Guidance" inside transcript.md
  = guidance-specific hints for reading transcripts

  Adding a new type = append a section to each asset file
  Adding a new asset = create one new asset file
```

**Three DRY rules:**
1. **Two axes, nothing else** — job type (WHAT) × data asset (WHERE). Every file belongs to: shared, per-type, or per-asset.
2. **Intersection = section, not file** — type-specific hints for an asset are a `## Extraction Rules: {type}` section inside the asset file. No file explosion.
3. **Share code, share queries, copy asset profiles** — scripts + type contract + QUERIES.md → shared (import chains / single source of truth, bug fix = one place). Asset profiles → copied to clean new location (standalone markdown, will evolve independently with per-type sections).

**Proof — adding a type or asset is trivial:**

```
ADD A NEW JOB TYPE (e.g., "analyst"):
─────────────────────────────────────
  Create:  analyst-inventory/SKILL.md                  ← new Manual 1
  Create:  scripts/analyst_ids.py                      ← new ID logic
  Create:  scripts/analyst_writer.py                   ← new writer
  Create:  agents/extraction-analyst.md                ← new agent
  Append:  "## Extraction Rules: Analyst"              ← to each asset file
           in extraction/assets/
  Wire:    Task(extraction-analyst) in orchestrators

  Everything else (QUERIES.md, asset files, K8s) = REUSED


ADD A NEW DATA ASSET (e.g., "press-release"):
─────────────────────────────────────────────
  Create:  extraction/assets/press-release.md          ← new Manual 3
  Append:  queries to guidance-inventory/QUERIES.md    ← source fetch queries
  Create:  skills/extract-press-release/SKILL.md       ← new orchestrator
  Wire:    trigger-extract.py --asset press-release

  Everything else (contracts, agents, scripts, K8s) = REUSED
```

### Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │           EXTRACTION FRAMEWORK                │
                    │                                              │
                    │  Orchestrator Skills (thin, per-asset):      │
                    │    /extract-transcript                        │
                    │    /extract-8k                                │
                    │    /extract-news                              │
                    │    /extract-10q  (covers both 10-Q and 10-K)   │
                    │                                              │
                    │  Each spawns N per-type agents:               │
                    │    /extract-transcript                        │
                    │      ├── Task(extraction-guidance)            │
                    │      ├── Task(extraction-guidance-qa) [opt-in]│
                    │      ├── Task(extraction-analyst)   [future]  │
                    │      └── Task(extraction-announce)  [future]  │
                    │                                              │
                    │    /extract-8k                                │
                    │      ├── Task(extraction-guidance)            │
                    │      └── Task(extraction-analyst)   [future]  │
                    └────────────┬─────────────────────────────────┘
                                 │ each agent auto-loads
                    ┌────────────▼─────────────────────────────────┐
                    │           REFERENCE LAYER                     │
                    │                                              │
                    │  Shared across ALL extraction types:          │
                    │    guidance-inventory/QUERIES.md (source fetch)│
                    │    extraction/assets/transcript.md            │
                    │    extraction/assets/8k.md                    │
                    │    extraction/assets/news.md                  │
                    │    extraction/assets/10q.md                   │
                    │                                              │
                    │  Per extraction-type (one contract per type): │
                    │    guidance-inventory/SKILL.md (schema)       │
                    │    analyst-inventory/SKILL.md (future)        │
                    └────────────┬─────────────────────────────────┘
                                 │ calls
                    ┌────────────▼─────────────────────────────────┐
                    │       DETERMINISTIC SCRIPTS                   │
                    │                                              │
                    │  Per extraction-type:                         │
                    │    guidance_ids.py (IDs, units, periods)      │
                    │    guidance_writer.py (MERGE patterns)        │
                    │    analyst_ids.py (future)                    │
                    │                                              │
                    │  Shared (reused from existing pipeline):       │
                    │    guidance_write.sh (venv + env setup)        │
                    └──────────────────────────────────────────────┘
```

### Design Decisions

**D1: Contract-driven framework** — Each extraction type is defined by a "contract" — a set of files that fully specify what to extract and how to validate it. The contract for guidance is: `guidance-inventory/SKILL.md` (schema + rules), `guidance_ids.py` (ID computation), `guidance_writer.py` (Neo4j write patterns). Adding a new type = creating a new contract. The working code IS the contract — no separate spec to keep in sync.

**D2: Asset profiles are single-file-per-asset with sections** — Each asset file (e.g., `transcript.md`) stays as ONE file with clearly marked sections:
- `## Asset Structure` — how to read the data asset (scan scope, speakers, fallback queries, empty handling). Shared by ALL extraction types.
- `## Extraction Rules: Guidance` — type-specific rules (derivation hints, quote conventions). Only read by guidance agents.
- `## Extraction Rules: Analyst` — future. Appended when needed.

All knowledge about one asset stays co-located. Adding a type = appending a section, not creating a new file. Current profiles are ~80% asset-generic + ~20% guidance-specific. Location: `.claude/skills/extraction/assets/` (COPIED from `guidance-inventory/reference/` — originals stay untouched).

**D3: Per-type agents + per-asset orchestrators** — One orchestrator per data asset (`/extract-transcript`, `/extract-8k`, etc.), each spawns focused agents per extraction type (`extraction-guidance`, future `extraction-analyst`). Each agent loads ~1,730 lines of type-specific instructions — combining types in one LLM pass would dilute attention and risk cross-contamination. Orchestrators are per-asset because they need to know the data asset (how to fetch content, which asset profile); types just determine which agents to spawn.

**D4: Two-phase enrichment is transcript-only and opt-in** — The PR → Q&A two-phase pattern only applies to transcripts (where the Q&A section can reveal new guidance items). Other assets (8-K, 10-Q, news) are single-pass. Each contract declares whether it needs enrichment. Currently only guidance + transcript uses it.

**D5: news-driver pipeline is 100% separate** — The `/news-driver` attribution/analysis workflow is a different architecture entirely. Not part of this extraction framework.

**D6: Per-type status properties, NOT JSON maps** — Simple properties on source nodes: `guidance_status`, `analyst_status`, etc. Not a JSON map — JSON sub-fields can't be indexed in Neo4j, would require APOC dependency, and existing `guidance_status` code works unchanged. Neo4j is schema-free; adding `analyst_status` is trivial, no migration needed.

**D7: GuidancePeriod rename — DEFERRED** — Calendar-based `gp_` format is inherently general. Will decide whether to rename to `CalendarPeriod` when first non-guidance type needs period tracking.

**D8: FOR_COMPANY edge — KEEP** — `(GuidanceUpdate)-[:FOR_COMPANY]->(Company)` stays. O(1) lookup, index-backed, simpler than multi-hop via `FROM_SOURCE`. All future extraction types follow the same pattern.

**D9: Separate labels (tag + data-point + optional supporting nodes)** — Each extraction type gets its own label set: `Guidance` (tag) + `GuidanceUpdate` (data-point) + `GuidancePeriod` (supporting) for the current type. Future types follow the same pattern: e.g., `AnalystTopic` + `AnalystComment` (no supporting node needed). Supporting nodes are optional — only created when the type needs them (guidance needs calendar periods, analyst comments probably don't). Different types have different properties (guidance needs `low/mid/high`, risk factors don't), and each type has its own writer — separate labels are natural. The full node/relationship graph is defined in the type's SKILL.md (see contract checklist §A).

**D10: Single queue `extract:pipeline`** — One Redis queue for all extraction jobs. Payload carries `asset` and `types`. One KEDA config, one dead-letter queue. Can split per-asset later if needed.

**D11: TYPES is mandatory** — If the orchestrator receives a prompt without `TYPES`, it MUST fail with an explicit error. No "default to all" guessing. The worker always passes TYPES from the payload. The trigger always includes TYPES in the payload. Explicit > implicit.

**D12: Error isolation — per-type independence** — When an orchestrator spawns multiple agents (e.g., guidance + analyst), each writes independently. If guidance succeeds but analyst fails, guidance results persist.

**How it works**: The orchestrator emits a structured summary line in its final output:
```
EXTRACTION_RESULTS: guidance=completed, analyst=failed
```

The worker parses this and marks `{type}_status` per-type:
- `SET t.guidance_status = 'completed'`
- `SET t.analyst_status = 'failed'`

If the orchestrator crashes entirely (no result at all), the worker marks ALL types as `failed`. Re-run only failed types via `trigger-extract.py --retry-failed`.

This keeps all status marking centralized in the worker (one mechanism, one Neo4j connection). The orchestrator just reports outcomes.

### How Types Get Routed

The trigger decides which types to run. The orchestrator just executes what it's told.

```
Trigger: --type guidance --asset transcript
  → queries WHERE t.guidance_status IS NULL
  → payload: {asset: "transcript", ticker, source_ids, types: ["guidance"], mode}

Worker: reads payload, invokes /extract-transcript AAPL ... TYPES=guidance MODE=write

Orchestrator (/extract-transcript): reads TYPES from prompt
  → if "guidance" in TYPES: spawn Task(extraction-guidance), then Task(extraction-guidance-qa)
  → if "analyst" in TYPES: spawn Task(extraction-analyst)  [future]

Agent (safety guard): checks {type}_status on source node before doing work
  → if already "completed": exit immediately (defense-in-depth, idempotent)
```

For historical backfill: `trigger-extract.py --type all --asset transcript` → includes all registered types.

### Asset Profile Dynamic Loading (Already Solved)

The current `guidance-extract.md` agent (duplicated as `extraction-guidance.md` in Phase 1) routes to the correct asset profile via a hardcoded `SOURCE_TYPE` if/else block in the agent's instructions. The agent receives `SOURCE_TYPE` in its prompt, reads the matching profile from `extraction/assets/`. QUERIES.md stays shared at `guidance-inventory/QUERIES.md` — both old and new agents read from the same file. When adding a new asset, create the asset file AND add a routing case to the agent's if/else block.

### What Varies by Extraction Type

| Component | Guidance | Future: Analyst Comments | Future: Risk Factors |
|-----------|----------|-------------------------|---------------------|
| **Node labels** | Guidance (tag) + GuidanceUpdate (data-point) | TBD (tag + data-point) | TBD |
| **Supporting nodes** | GuidancePeriod (calendar periods + ST/MT/LT buckets) | Likely none | Likely none |
| **Relationships** | UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD, MAPS_TO_CONCEPT, MAPS_TO_MEMBER | UPDATES, FROM_SOURCE, FOR_COMPANY (subset) | TBD |
| **Extraction fields** | 20 fields (low/mid/high, basis, derivation...) | Different field set | Different field set |
| **Quality filters** | Forward-looking, no fabrication, quote max 500 | Different filters | Different filters |
| **ID structure** | `gu:{source}:{label}:{period}:{basis}:{segment}` | Different slot components | Different slot components |
| **XBRL matching** | MAPS_TO_CONCEPT + MAPS_TO_MEMBER (pre-existing nodes) | Probably not applicable | Not applicable |
| **Period resolution** | GuidancePeriod (calendar-based) | May not need periods | Not period-based |

### What Varies by Data Asset

| Component | Transcript | 8-K | 10-Q/10-K | News |
|-----------|-----------|-----|-----------|------|
| **Source fetch queries** | 3B/3C/3D | 4C/4E/4F/4G | 5B/5C | 6A/6B |
| **Scan scope** | PR + Q&A (all speakers) | EX-99.* → sections → filing text | MD&A primary, bounded fallback | Title + body (channel-filtered) |
| **given_date** | conference_datetime | r.created | r.created | n.created |
| **source_key** | "full" | "EX-99.1", "Item 2.02" | "MD&A" | "title" |
| **Empty rules** | Both PR + Q&A empty | Strip == "" | MD&A strip == "" | Both title + body empty |
| **Two-phase?** | Yes (PR → Q&A) | No | No | No |

### Script Organization

All extraction scripts live in `.claude/skills/earnings-orchestrator/scripts/`. This directory contains both type-specific scripts (prefixed by type: `guidance_ids.py`, `guidance_writer.py`) and shared utilities (`fiscal_math.py`, `pit_fetch.py`, etc.). Future extraction types add their scripts to the same directory following the same naming convention (`analyst_ids.py`, `analyst_writer.py`). Directory rename from `earnings-orchestrator` to something more general is a post-retirement task.

### What's Shared Across All Types

1. **Context loading**: Company+CIK (1A), FYE (1B) — always needed, all assets
2. **Source fetch queries**: `guidance-inventory/QUERIES.md` — organized by asset type (3x/4x/5x/6x prefixes), shared by all agents
3. **Write path**: JSON → `guidance_write.sh` → `guidance_write_cli.py` → `guidance_writer.py` → Neo4j MERGE
4. **Execution modes**: dry_run / shadow / write
5. **Error taxonomy**: SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_GUIDANCE, etc.

### How to Add a New Extraction Type

1. Create `.claude/skills/{type}-inventory/SKILL.md` — define the full graph schema (nodes, relationships, supporting nodes per contract checklist §A below), extraction fields, ID formula, quality filters, validation rules (use `guidance-inventory/SKILL.md` as template)
2. Create `.claude/skills/earnings-orchestrator/scripts/{type}_ids.py` — deterministic ID computation (like `guidance_ids.py`)
3. Create `.claude/skills/earnings-orchestrator/scripts/{type}_writer.py` — Cypher MERGE patterns for the labels + relationships defined in step 1 (FROM_SOURCE, FOR_COMPANY, HAS_PERIOD as applicable; like `guidance_writer.py`)
4. Create agent: `.claude/agents/extraction-{type}.md` — references SKILL.md + `guidance-inventory/QUERIES.md` + `extraction/assets/*.md`
5. Append `## Extraction Rules: {type}` section to each applicable asset file in `extraction/assets/`
6. Add `Task(extraction-{type})` spawn to each per-asset orchestrator that applies
7. Add `{type}_status` property to trigger script's query + worker's `mark_status()`

Steps 1-3 are the substantive work. Steps 4-7 are boilerplate that follows the pattern.

**What goes where** — the 3 files and what each one specifies:

```
ADDING A NEW EXTRACTION TYPE: What goes where
══════════════════════════════════════════════

FILE 1: {type}-inventory/SKILL.md  (THE SPEC — define everything here first)
─────────────────────────────────────────────────────────────────────────────
  § Graph Schema
    ├── Tag node label + properties        (e.g., Guidance: id, label, aliases)
    ├── Data-point node label + properties  (e.g., GuidanceUpdate: 20+ fields)
    ├── Supporting node label + properties  (e.g., GuidancePeriod: id, u_id)  [if needed]
    └── All relationships                   (UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD, ...)

  § ID Formula
    └── Slot structure                      (e.g., gu:{source}:{label}:{period}:{basis}:{segment})

  § Extraction Fields
    └── Every field the LLM must extract    (low, mid, high, basis, unit, quote, ...)

  § Quality Filters
    └── What to accept/reject               (forward-looking only, quote max 500, ...)

  § Validation Rules
    └── Deterministic checks                (unit canon, period resolution, basis rules)

  § Error Taxonomy
    └── Standard error codes                (SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_{TYPE})

  § Execution Modes
    └── dry_run / shadow / write


FILE 2: {type}_ids.py  (IMPLEMENTS: IDs + validation from SKILL.md spec)
────────────────────────────────────────────────────────────────────────
  Reads SKILL.md §ID Formula, §Validation Rules
    ├── Deterministic ID computation         (slot assembly, dedup key)
    ├── Unit canonicalization                (raw unit → canonical)
    ├── Period resolution                    (date math → supporting node ID)  [if needed]
    └── Field validation                     (basis rules, required fields)


FILE 3: {type}_writer.py  (IMPLEMENTS: graph creation from SKILL.md spec)
─────────────────────────────────────────────────────────────────────────
  Reads SKILL.md §Graph Schema
    ├── MERGE tag node                       (e.g., Guidance)
    ├── MERGE data-point node                (e.g., GuidanceUpdate, all 20+ properties)
    ├── MERGE supporting node                (e.g., GuidancePeriod)  [if needed]
    ├── MERGE relationships:
    │     ├── UPDATES         (data-point → tag)
    │     ├── FROM_SOURCE     (data-point → source document)
    │     ├── FOR_COMPANY     (data-point → Company)
    │     ├── HAS_PERIOD      (data-point → supporting node)  [if needed]
    │     └── type-specific   (e.g., MAPS_TO_CONCEPT, MAPS_TO_MEMBER)
    └── Mode handling                        (dry_run → JSON only, write → Neo4j)


FLOW:  SKILL.md defines it  →  _ids.py validates it  →  _writer.py writes it to Neo4j
```

**Contract checklist** — every new type MUST define all of the following in its SKILL.md (use `guidance-inventory/SKILL.md` as template):

**A. Graph schema** — define the complete node/relationship map upfront. This is the blueprint that `{type}_ids.py` and `{type}_writer.py` implement.

Guidance reference (the pattern every new type follows):

```
                        Guidance (tag node)
                           ▲
                           │ UPDATES
                           │
Company ◄──FOR_COMPANY── GuidanceUpdate ──FROM_SOURCE──► Transcript/Report/News
                              │       │
                              │       ├── MAPS_TO_CONCEPT ──► Concept  (pre-existing)
                              │       └── MAPS_TO_MEMBER  ──► Member   (pre-existing)
                              │
                              └── HAS_PERIOD ──► GuidancePeriod (supporting node)
```

| Node | Type | Created by | Key properties |
|------|------|-----------|----------------|
| `Guidance` | Tag (one per metric label, e.g., "Revenue") | writer.py | id, label, aliases |
| `GuidanceUpdate` | Data-point (one per extraction) | writer.py | id, label, basis_norm, derivation, canonical_unit, segment, quote, source_type, source_key, xbrl_qname, period_scope, time_type, ... (20+ fields) |
| `GuidancePeriod` | Supporting (calendar periods + buckets) | writer.py | id (`gp_2024-01-01_2024-03-31` or `gp_ST/MT/LT`), u_id |

| Relationship | From → To | Required? | Notes |
|-------------|-----------|-----------|-------|
| `UPDATES` | GuidanceUpdate → Guidance | **YES — all types** | Links data-point to its tag |
| `FROM_SOURCE` | GuidanceUpdate → Transcript/Report/News | **YES — all types** | Links to source document |
| `FOR_COMPANY` | GuidanceUpdate → Company | **YES — all types** (D8) | O(1) company lookup |
| `HAS_PERIOD` | GuidanceUpdate → GuidancePeriod | Type-specific | Calendar period or ST/MT/LT bucket |
| `MAPS_TO_CONCEPT` | GuidanceUpdate → Concept | Type-specific | XBRL concept (pre-existing node) |
| `MAPS_TO_MEMBER` | GuidanceUpdate → Member | Type-specific | XBRL member (pre-existing node) |

**New type example** — an "analyst" type would fill the same tables:

| Node | Type | Key properties |
|------|------|----------------|
| `AnalystTopic` | Tag | id, label |
| `AnalystComment` | Data-point | id, label, sentiment, quote, analyst_firm, source_type, ... |
| *(none)* | Supporting | Not needed — no period tracking |

| Relationship | From → To | Notes |
|-------------|-----------|-------|
| `UPDATES` | AnalystComment → AnalystTopic | Required |
| `FROM_SOURCE` | AnalystComment → Transcript/Report/News | Required |
| `FOR_COMPANY` | AnalystComment → Company | Required |

The SKILL.md defines these tables, `analyst_writer.py` implements the MERGE patterns.

**B. Extraction contract** — everything else the SKILL.md must specify:

| Component | Guidance example | Where it lives |
|-----------|-----------------|----------------|
| **ID slot formula** | `gu:{source}:{label}:{period}:{basis}:{segment}` | SKILL.md (ID section) + `{type}_ids.py` |
| **Extraction fields** | 20 fields: low, mid, high, basis, derivation_type, unit, segment, quote, ... | SKILL.md (schema section) |
| **Quality filters** | Forward-looking only, no fabrication, quote max 500 chars | SKILL.md (quality section) |
| **Validation rules** | Unit canonicalization, period resolution, basis explicit-only | SKILL.md + `{type}_ids.py` |
| **Error taxonomy** | SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_GUIDANCE | SKILL.md (error section) |
| **Execution modes** | dry_run / shadow / write | SKILL.md (inherited pattern) |

### How to Add a New Data Asset

1. Add queries to `guidance-inventory/QUERIES.md` (or create `extraction/queries_{asset}.md` if >1000 lines)
2. Create `extraction/assets/{asset}.md` — data structure, scan scope, empty handling
3. Add `SOURCE_TYPE` routing case to extraction agent files (hardcoded if/else block that selects the asset profile)
4. Extend trigger to query for unprocessed items of the new asset type

---

## §2: Data Assets — Current Status

| Asset | Status | Profile | Gap |
|-------|--------|---------|-----|
| **Transcript** | Production (K8s worker) | transcript.md | Build `/extract-transcript` alongside → golden checks → parallel run → retire only after extensive verification |
| **8-K** | Agent-ready (profile routing works) | 8k.md | `/extract-8k` orchestrator, trigger extension (`formType='8-K'`), `guidance_status` on Report nodes |
| **10-Q/10-K** | Agent-ready | 10q.md | `/extract-10q` orchestrator (handles both 10-Q and 10-K), trigger extension |
| **News** | Agent-ready | news.md | `/extract-news` orchestrator, trigger extension. Channel pre-filter is guidance-specific |
| **Other (DEF 14A, S-1)** | Not started | — | Add asset file when needed |

---

## §3: K8s Infrastructure

Currently hardcoded to transcripts + guidance only (see §0 K8s Trigger Path for full detail).

### New Design: Single Queue, Payload-Driven

**Trigger** (`trigger-extract.py`, new file based on `trigger-guidance.py`):
```
trigger-extract.py
  --type guidance|analyst|all
  --asset transcript|8k|10q|news|all    (10q covers both 10-Q and 10-K filings)
  --ticker AAPL [or --all]
  --mode write

  → Queries Neo4j: WHERE t.{type}_status IS NULL (for specific type)
    or WHERE t.guidance_status IS NULL OR t.analyst_status IS NULL (for --type all)
  → Groups by ticker
  → Pushes to Redis queue: "extract:pipeline"
```

**Queue**: `extract:pipeline` (single queue). One KEDA config. One dead-letter queue.

**Payload**:
```json
{
  "asset": "transcript",
  "ticker": "AAPL",
  "source_ids": ["AAPL_2025-01-30T17.00"],
  "types": ["guidance"],
  "mode": "write"
}
```

**Worker** (`extraction_worker.py`, new file based on `earnings_worker.py`):
```
1. BRPOP from "extract:pipeline"
2. Parse payload → compute skill: /extract-{asset}
3. For each source_id:
   a. mark_status(in_progress) for each type in types
   b. Claude SDK: query("/extract-{asset} {ticker} {source_id} TYPES={types} MODE={mode}")
   c. Parse EXTRACTION_RESULTS from orchestrator output (see D12)
   d. mark_status(completed|failed) PER TYPE based on parsed results
   e. Fallback: if no result / crash → mark ALL types as failed
4. On shutdown: re-queue remaining
5. On failure: retry up to 3x, then dead-letter
```

### K8s Files — New vs Original

| New File | Based On | Change |
|----------|----------|--------|
| `scripts/extraction_worker.py` | `scripts/earnings_worker.py` | Generalize payload parsing, skill routing, per-type status tracking |
| `scripts/trigger-extract.py` | `scripts/trigger-guidance.py` | Add `--type`/`--asset` flags, generalize Neo4j query, new queue name |
| `k8s/processing/extraction-worker.yaml` | `claude-code-worker.yaml` | New KEDA config for `extract:pipeline` queue |
| `scripts/canary_sdk.py` | (update in place) | Validate generalized worker (new skill name, new payload format) |

**Original files stay frozen**: `earnings_worker.py`, `trigger-guidance.py`, `claude-code-worker.yaml` all remain operational on the `earnings:trigger` queue until retirement is explicitly approved.

**Open**: `earnings_trigger.py` status unclear — shares `earnings:trigger` queue. Confirm what else uses it before any retirement (§6 Q5).

---

## §4: Quality & Best Practices

### What Works Well (keep as-is)

1. **Two-phase transcript extraction** (PR → Q&A) — handles "Q&A reveals new items" cleanly. MERGE idempotency means Phase 2 safely overwrites Phase 1.
2. **Thin orchestrator skill** — 14 lines. Spawns agents, reports results. No logic duplication.
3. **Deterministic validation via scripts** — no LLM math. IDs, units, periods computed by Python with 169 tests.
4. **Per-source profiles** — adding a new source type = add one asset file.
5. **Write path isolation** — agents can't write to Neo4j directly. All writes go through `guidance_write.sh` → `guidance_writer.py`.
6. **K8s worker** — battle-tested. Graceful shutdown, re-queue, retry, dead-letter.
7. **Slot-based dedup** — deterministic IDs prevent duplicates across reruns. Latest write wins.

### Best Practices Issues (Phase 2 + post-retirement)

1. **SKILL.md too long** — `guidance-inventory/SKILL.md` is 733 lines (reference says <500). Split §9-§11 (Period Resolution, Company+Period, XBRL Matching) into a separate reference file.
2. **`guidance-inventory/SKILL.md` has irrelevant frontmatter** — it's a reference doc auto-loaded by agents, not user-invocable. Add `user-invocable: false`, remove `allowed-tools`/`permissionMode`.
3. **`guidanceInventory.md` is partially stale** — archive as historical reference. Working code is source of truth per D1.
4. **`evidence-standards` not loaded by extraction agents** — the 47-line anti-hallucination rules should be added to new agents' auto-load in Phase 2. Currently NOT loaded by guidance-extract or guidance-qa-enrich.

### Golden Checks (validation criteria)

Any reorganization MUST produce identical output. "Identical" means ALL of the following pass:

1. **Same GuidanceUpdate IDs** — deterministic slot-based IDs must match exactly
2. **Same key field values** — low/mid/high, basis, period, derivation_type, unit, segment, quote
3. **Same relationship edge counts** — FROM_SOURCE, FOR_COMPANY, HAS_PERIOD edges per source
4. **Idempotent rerun** — run the same transcript twice, zero new nodes created (MERGE idempotency)
5. **Same error taxonomy** — SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_GUIDANCE outcomes unchanged

### Quality Observations

Phase 1.4 validates the new infrastructure by running both `/guidance-transcript` (old) and `/extract-transcript` (new) on the same 5+ transcripts and diffing their output against the golden checks above. No separate baseline run needed — the old pipeline is frozen and always produces the same output.

---

## §5: Implementation Phases

Each phase has a validation gate. No phase starts until the previous gate passes.

### Phase 1: Build New Infrastructure (old pipeline stays frozen)

Create the new extraction framework alongside the existing pipeline. **Nothing existing is moved, renamed, or edited.** All new files are duplicates with new names fitting the extraction framework. The original `/guidance-transcript` pipeline continues working exactly as-is throughout.

**What changes — current vs new:**

```
CURRENT                                    NEW
═══════                                    ═══
                    ORCHESTRATORS
.claude/skills/                          .claude/skills/
  guidance-transcript/SKILL.md  ──COPY──►  extract-transcript/SKILL.md
  (14 lines, frozen)                       (clone; Phase 3 adds TYPES)

                      AGENTS
.claude/agents/                          .claude/agents/
  guidance-extract.md  ─────COPY────────►  extraction-guidance.md
  (frozen)                                 (new reference paths)
  guidance-qa-enrich.md ────COPY────────►  extraction-guidance-qa.md
  (frozen)                                 (new reference paths)

              QUERIES — SHARED (no copy)
.claude/skills/
  guidance-inventory/
    QUERIES.md  ◄────── both old + new agents read this (755 lines)

                 ASSET PROFILES — COPIED + RENAMED
  guidance-inventory/reference/            extraction/assets/
    PROFILE_TRANSCRIPT.md  ───COPY──────►    transcript.md
    PROFILE_8K.md  ─────────COPY──────►    8k.md
    PROFILE_NEWS.md  ───────COPY──────►    news.md
    PROFILE_10Q.md  ────────COPY──────►    10q.md

              TYPE CONTRACT — SHARED (no copy)
  guidance-inventory/
    SKILL.md  ◄────── both old + new agents read this (733 lines)

                SCRIPTS — SHARED (no copy)
  earnings-orchestrator/scripts/
    guidance_ids.py  ◄──── both old + new agents call this
    guidance_writer.py ◄── both old + new agents call this
    guidance_write_cli.py, guidance_write.sh
    fiscal_math.py, pit_fetch.py, etc.
```

**New files created:**

| New File | Copied From | Notes |
|----------|-------------|-------|
| `.claude/skills/extraction/assets/transcript.md` | `guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | Renamed copy |
| `.claude/skills/extraction/assets/8k.md` | `guidance-inventory/reference/PROFILE_8K.md` | Renamed copy |
| `.claude/skills/extraction/assets/news.md` | `guidance-inventory/reference/PROFILE_NEWS.md` | Renamed copy |
| `.claude/skills/extraction/assets/10q.md` | `guidance-inventory/reference/PROFILE_10Q.md` | Renamed copy |
| `.claude/skills/extract-transcript/SKILL.md` | `guidance-transcript/SKILL.md` | New orchestrator skill. Phase 1: exact clone — does NOT parse TYPES, unconditionally spawns guidance + guidance-qa agents, identical to `/guidance-transcript`. Phase 3 adds TYPES parsing per D11. |
| `.claude/agents/extraction-guidance.md` | `guidance-extract.md` | New agent — references `guidance-inventory/QUERIES.md` (shared) + `extraction/assets/` (new) + same `guidance-inventory/SKILL.md` and scripts |
| `.claude/agents/extraction-guidance-qa.md` | `guidance-qa-enrich.md` | New agent — same reference path changes |

**Original files — UNTOUCHED:**

| File | Status |
|------|--------|
| `.claude/skills/guidance-transcript/SKILL.md` | FROZEN — stays working as-is |
| `.claude/agents/guidance-extract.md` | FROZEN |
| `.claude/agents/guidance-qa-enrich.md` | FROZEN |
| `.claude/skills/guidance-inventory/reference/PROFILE_*.md` | FROZEN |
| `.claude/skills/guidance-inventory/SKILL.md` | FROZEN — shared by both old and new agents |
| `.claude/skills/guidance-inventory/QUERIES.md` | SHARED — both old and new agents read this |
| All scripts (`guidance_ids.py`, `guidance_writer.py`, etc.) | FROZEN — shared by both old and new agents |

| Step | Action | Validation |
|------|--------|------------|
| 1.1 | Create `extraction/assets/` directory. Copy + rename PROFILE files → `extraction/assets/{asset}.md` | New copies exist, originals untouched |
| 1.2 | Create new agents (`extraction-guidance.md`, `extraction-guidance-qa.md`) pointing to `extraction/assets/` (new) + `guidance-inventory/QUERIES.md` (shared) + same `guidance-inventory/SKILL.md` and scripts | Dry-run on 1 transcript, compare output |
| 1.3 | Create `/extract-transcript` orchestrator skill that spawns new agents | Spawns same pipeline as `/guidance-transcript` |
| 1.4 | **Baseline validation**: Run `/extract-transcript` on 5+ transcripts, diff output against `/guidance-transcript` | Golden checks pass (§4): same IDs, same fields, same edges, idempotent |
| 1.5 | **Canary validation**: Run `canary_sdk.py` with new skill name | Canary green |

**Retirement is NOT part of Phase 1.** The original pipeline stays frozen indefinitely. Retirement is a separate decision made only after extensive parallel running proves the new infrastructure matches or exceeds the original.

### Phase 2: Best Practices Cleanup (new files only — frozen files untouched)

| Step | Action | Validation |
|------|--------|------------|
| 2.1 | Add `evidence-standards` to NEW agents' auto-load (`extraction-guidance.md`, `extraction-guidance-qa.md`) | 47 lines, no behavior change |
| 2.2 | Archive `guidanceInventory.md` as historical reference (per D1: working code is source of truth) | |

**Deferred to post-retirement** (these edit frozen files):
- Split SKILL.md §9-§11 into reference file (get under 500 lines) — edits `guidance-inventory/SKILL.md` which is frozen
- Add `user-invocable: false` to `guidance-inventory/SKILL.md` frontmatter — edits a frozen file

### Phase 3: Generalize Trigger + Worker

| Step | Action | Validation |
|------|--------|------------|
| 3.1 | Update `/extract-transcript` to parse TYPES from prompt and spawn only listed types. Fail if TYPES missing (D11). | `/extract-transcript AAPL ... TYPES=guidance` spawns only guidance agents |
| 3.2 | Create `trigger-extract.py` (new file, based on `trigger-guidance.py`) | `--type guidance --asset transcript` produces correct payloads |
| 3.3 | Create `extraction_worker.py` (new file, based on `earnings_worker.py`) | Reads new payload format, invokes `/extract-transcript` |
| 3.4 | New queue `extract:pipeline` (old `earnings:trigger` stays until retirement) | KEDA config for new queue |
| 3.5 | Update `canary_sdk.py` for new skill/payload | |
| 3.6 | **End-to-end K8s validation**: trigger → queue → worker → `/extract-transcript` → Neo4j | Golden checks pass (§4) |
| 3.7 | Confirm `earnings_trigger.py` status (shares old queue — does anything else use it?) | |

**Original scripts stay frozen**: `trigger-guidance.py`, `earnings_worker.py`, and the `earnings:trigger` queue remain operational. The new scripts run on the new `extract:pipeline` queue in parallel.

### Phase 4: Expand to Other Data Assets (guidance extraction)

| Step | Action | Validation |
|------|--------|------------|
| 4.1 | Create `/extract-8k` orchestrator | Spawns `extraction-guidance` with SOURCE_TYPE=8k |
| 4.2 | Add `guidance_status` property to Report nodes | Trigger can find unprocessed 8-Ks |
| 4.3 | Extend `trigger-extract.py`: `--asset 8k` | Query Reports with formType='8-K' |
| 4.4 | Repeat for 10-Q/10-K (same `/extract-10q` orchestrator), News | |

### Phase 5: First Non-Guidance Extraction Type (future)

| Step | Action | Validation |
|------|--------|------------|
| 5.1 | Choose extraction type (analyst? announcement?) | |
| 5.2 | Design contract: fields, quality filters, ID formula | |
| 5.3 | Execute "How to Add a New Extraction Type" checklist (§1), steps 1-7 | All steps pass |
| 5.4 | Define contract template for future types | |

### Retirement of Original Pipeline (no timeline — quality-gated)

Retirement happens only when ALL gates pass:
1. New infrastructure running in parallel for a significant period
2. Golden checks pass consistently across all tested transcripts
3. User has thoroughly reviewed output quality and explicitly approved
4. No regressions in any edge case

When approved: new Phase 1 files replace their frozen counterparts (see Phase 1 comparison diagram for full old→new mapping). K8s replacements: `trigger-extract.py` replaces `trigger-guidance.py`, `extraction_worker.py` replaces `earnings_worker.py`, `extract:pipeline` queue replaces `earnings:trigger`.

**Not retired** (shared, used by both old and new): `guidance-inventory/SKILL.md`, `guidance-inventory/QUERIES.md`, all scripts in `earnings-orchestrator/scripts/`. Post-retirement cleanup: rename `earnings-orchestrator/` directory, rename `guidance-inventory/` to something extraction-generic, delete frozen originals (`guidance-inventory/reference/PROFILE_*.md`).

---

## §6: Open Questions

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 1 | GuidancePeriod: share with other types? | DEFERRED | Calendar-based `gp_` format is general. Decide rename to `CalendarPeriod` when first non-guidance type needs periods. |
| 2 | Specific output quality issues with guidance-transcript | PENDING | User will specify. Baseline from pipeline runs + Neo4j audit. |
| 3 | Extraction types beyond guidance | PENDING | Focus on infra first. Guidance is gold standard. New types added when ready. |
| 4 | Budget/cost optimization for K8s runs | OPEN | |
| 5 | `earnings_trigger.py` status | PENDING | Shares `earnings:trigger` queue. Confirm dormant before Phase 3 queue rename. |

---

*v1.3 | 2026-03-04 | Replaced Core Insight + Key Separation with 3-manual and DRY diagrams. Asset profiles renamed: `PROFILE_TRANSCRIPT.md` → `transcript.md` in `extraction/assets/`. Added current-vs-new infrastructure comparison to Phase 1. Updated all paths throughout. evidence-standards correctly noted as not currently loaded.*
*v1.3.1 | 2026-03-04 | QUERIES.md reverted to SHARED (stays in `guidance-inventory/QUERIES.md`; old + new agents both read it). Zero drift, truly DRY. Post-retirement: rename `guidance-inventory/` to extraction-generic name.*
*v1.3.2 | 2026-03-04 | Implementation-proof pass: (1) Banner → status field, (2) §0 Phase→Agent naming to avoid §5 collision, (3) evidence-standards added to File Inventory, (4) Phase 1 clone explicitly does NOT parse TYPES, (5) 10q covers both 10-Q/10-K — removed 10k as separate asset, (6) SOURCE_TYPE routing is hardcoded, not auto-detect.*
*v1.4 | 2026-03-04 | Added full graph schema to contract checklist: nodes (tag + data-point + supporting), all 6 relationships with guidance reference, node property summaries. D9 updated to cover supporting nodes. "What Varies" table expanded with supporting nodes and relationships rows. New type implementors now define their complete graph shape upfront in SKILL.md before writing any code.*
