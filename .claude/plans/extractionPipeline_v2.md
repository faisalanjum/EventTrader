# Extraction Pipeline — Implementation Plan

**Status: APPROVED v3.5** — Final end-state architecture. Generic runtime + specialized prompt packets. Ready for implementation.

**Baseline lock**: The current `/guidance-transcript` pipeline stays FROZEN and untouched. We build ALONGSIDE the old. Originals are never moved, renamed, or edited. Retirement is quality-gated, not time-gated.

### Guiding Principles

1. **Super minimalism** — zero over-engineering, simplest thing that works
2. **100% output reliability** — guidance-transcript quality is the gold standard, never degrade it
3. **Plug-and-play** — trivially easy to add/remove any extraction type for any data asset
4. **Always actionable** — every section points toward clear implementation; zero paralysis by analysis
5. **Generic runtime, specialized prompt packets** — infrastructure (trigger, worker, queue, orchestrator, two agent shells) is generic and reusable. Prompt content (pass-specific brief files) is specialized and preserves production-tuned extraction rules near-verbatim from the current agents. Each agent loads only its own pass file — primary never sees enrichment instructions, enrichment never sees primary instructions. Pass files are self-contained working briefs, intentionally redundant with core-contract sections. The redundancy IS the quality mechanism.

**Version**: 3.5 | 2026-03-06
**Goal**: Generalize the guidance extraction pipeline into a reusable framework for ANY extraction type across ALL data assets.
**Prior versions**: v1.5 in `extractionPipeline.md` (SUPERSEDED). v2.0-v3.0 superseded by this file.

---

## S0: Current State

### How It Works Today

```
User or SDK:
  /guidance-transcript AAPL transcript AAPL_2025-01-30T17.00 MODE=write

Skill: .claude/skills/guidance-transcript/SKILL.md  (14 lines)
  Spawns 2 agents sequentially:

  Agent 1: Task(guidance-extract)     -> PR extraction
  Agent 2: Task(guidance-qa-enrich)   -> Q&A enrichment

Each agent auto-loads 3 instruction files:
  1. guidance-inventory/SKILL.md       (733 lines -- the type contract)
  2. guidance-inventory/QUERIES.md     (755 lines -- 42 Cypher queries)
  3. PROFILE_TRANSCRIPT.md             (242 lines -- asset reading rules)

Then executes:  FETCH -> EXTRACT -> VALIDATE -> WRITE
```

### The 4 Stages

```
+-------------+   +-------------+   +---------------+   +-------------+
| FETCH       |-->| EXTRACT     |-->| VALIDATE      |-->| WRITE       |
| Neo4j reads |   | LLM reads   |   | Python scripts|   | Python      |
| via queries |   | text, finds  |   | compute IDs,  |   | scripts     |
|             |   | items        |   | validate      |   | MERGE to    |
|             |   |              |   |               |   | Neo4j       |
+------+------+   +------+------+   +-------+-------+   +------+------+
       |                 |                  |                    |
  queries-common   core-contract +     guidance_ids        guidance_writer
  + asset queries  pass file +         .py                 .py
                   asset profile
```

### K8s Trigger Path (current)

```
trigger-guidance.py -> Redis "earnings:trigger" -> earnings_worker.py
  |-- Query: Transcript.guidance_status IS NULL
  |-- Group by ticker
  |-- BRPOP -> Claude SDK: /guidance-transcript
  \-- Mark completed/failed on Transcript node
```

### Current File Inventory

| Layer | File | Lines | Role |
|-------|------|-------|------|
| **Skill** | `guidance-transcript/SKILL.md` | 14 | Orchestrator |
| **Agent 1** | `agents/guidance-extract.md` | 285 | PR extraction |
| **Agent 2** | `agents/guidance-qa-enrich.md` | 182 | Q&A enrichment |
| **Contract** | `guidance-inventory/SKILL.md` | 733 | Schema, fields, validation, quality |
| **Queries** | `guidance-inventory/QUERIES.md` | 755 | 42 Cypher queries |
| **Profile** | `guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | 242 | Transcript rules |
| **Profile** | `guidance-inventory/reference/PROFILE_8K.md` | 194 | 8-K rules |
| **Profile** | `guidance-inventory/reference/PROFILE_NEWS.md` | 223 | News rules |
| **Profile** | `guidance-inventory/reference/PROFILE_10Q.md` | 237 | 10-Q/10-K rules |
| **Script** | `earnings-orchestrator/scripts/guidance_ids.py` | ~600 | IDs, units, periods |
| **Script** | `earnings-orchestrator/scripts/guidance_writer.py` | ~400 | Cypher MERGE |
| **Script** | `earnings-orchestrator/scripts/guidance_write_cli.py` | ~200 | CLI glue |
| **Script** | `earnings-orchestrator/scripts/guidance_write.sh` | 22 | Venv + env |
| **Trigger** | `scripts/trigger-guidance.py` | 189 | Neo4j -> Redis |
| **Worker** | `scripts/earnings_worker.py` | 368 | Redis -> Claude SDK |

---

## S1: The Two-Axis Model

Every extraction job is defined by two axes:

```
JOB = TYPE x ASSET x SOURCE

TYPE  = what to extract        (guidance, analyst, risk...)
ASSET = where to extract from  (transcript, 8-K, 10-Q, news)
SOURCE = specific document     (AAPL_2025-01-30T17.00)
```

```
               JOB GRID

                      ASSET
               transcript   8k   10q   news
TYPE
guidance         [*]        [ ]  [ ]   [ ]       [*] = today (production)
analyst          [ ]        [ ]  [ ]   [ ]       [ ] = future slot
announcement     [ ]        [ ]  [ ]   [ ]
```

### What Varies by Each Axis

```
                    FETCH       EXTRACT      VALIDATE     WRITE
                    -----       -------      --------     -----
Varies by TYPE?      no         YES          YES          YES
Varies by ASSET?    YES         partly        no           no
```

- **FETCH is an ASSET concern** -- different queries per source type
- **VALIDATE and WRITE are pure TYPE concerns** -- scripts don't care where data came from
- **EXTRACT straddles both** -- LLM needs type rules AND asset reading rules

### The Universal Noun: ExtractionJob

Every component in the system revolves around one object:

```
ExtractionJob = {
  type,       // "guidance"
  asset,      // "transcript"
  source_id,  // "AAPL_2025-01-30T17.00"
  ticker,     // "AAPL"
  mode        // "write"
}
```

One job = one type + one asset + one source. Always.

Trigger creates it. Worker dispatches it. Orchestrator executes it. Agent processes it.

---

## S2: Architecture

### Two Focused Generic Agents

The current system has per-type agents (`guidance-extract.md`, `guidance-qa-enrich.md`). The new system has TWO focused generic agent shells — one for primary extraction, one for enrichment — each loading only its own pass-specific prompt packet. Neither agent ever sees the other pass's instructions.

```
CURRENT: Each type gets its own agent files
=======
  guidance-extract.md      (285 lines, TYPE-SPECIFIC)
  guidance-qa-enrich.md    (182 lines, TYPE-SPECIFIC)
  (future: analyst-extract.md, analyst-qa-enrich.md...)

NEW: Two generic agents + split type contract
===
  extraction-primary-agent.md     (~50 lines, GENERIC)
  extraction-enrichment-agent.md  (~50 lines, GENERIC)
  + types/guidance/
      core-contract.md              (shared schema/rules, ~733 lines)
      primary-pass.md               (primary prompt packet, ~180 lines)
      enrichment-pass.md            (enrichment prompt packet, ~110 lines)
```

### Why This Works -- The Agent Dissection

Line-by-line analysis of `guidance-extract.md` (285 lines) proves the agent is mostly redundant with SKILL.md:

```
guidance-extract.md (285 lines)
|
|-- 48 lines [GENERIC]    -- pipeline structure (same for any type)
|     Frontmatter, input format, context loading, error handling
|
|-- 98 lines [REDUNDANT]  -- ALREADY in SKILL.md (LLM reads it twice)
|     S4 metric decomp, S6 basis, S7 segment, S8 unit, S9 period,
|     S11 xbrl, S13 quality, S16 modes, S17 errors, S13 rules
|
|-- 79 lines [UNIQUE]     -- NOT in SKILL.md
|     Bash templates (build_period_id, build_ids)    = 32 lines
|     JSON payload full example                       = 30 lines
|     Output format + "no TSV" rule                   = 12 lines
|     "PR only for primary pass"                      =  3 lines
|     guidance_write.sh exact commands                 =  5 lines
|
|-- 14 lines [ASSET]      -- source routing (also in SKILL.md S12)
|
\-- 46 lines [FORMATTING] -- blank lines, headers
```

**The 79 UNIQUE lines ALL move to `primary-pass.md`.** Zero information lost.

Same analysis for `guidance-qa-enrich.md` (182 lines):

```
guidance-qa-enrich.md (182 lines)
|
|-- 38 lines [GENERIC]    -- pipeline structure
|-- 42 lines [REDUNDANT]  -- already in SKILL.md
|-- 68 lines [UNIQUE]     -- enrichment verdicts, log format,
|                            completeness check, quote format
\-- 34 lines [FORMATTING]
```

**The 68 UNIQUE lines move to `enrichment-pass.md`.**

### Why Two Agents, Not One with PASS=

Earlier versions of this plan used a single agent with `PASS=primary|enrichment` loading one monolithic contract containing both pass briefs. That was cleaner engineering but worse for extraction quality:

- **Primary agent saw enrichment instructions** — ~110 lines of irrelevant S20 content in context
- **Enrichment agent saw primary instructions** — ~180 lines of irrelevant S19 content in context
- **Cross-contamination diluted attention** — the LLM had to ignore pass-irrelevant content

Two focused agents eliminate this entirely:
- Primary agent loads `core-contract.md` + `primary-pass.md` — never sees enrichment logic
- Enrichment agent loads `core-contract.md` + `enrichment-pass.md` — never sees primary logic
- Each agent's context is 100% relevant to its task — matching the current system's signal density

The cost is minimal: two ~50-line agent shells (~80% identical) instead of one ~60-line agent. Both are generic — they work for any type via file path convention.

### Total Context Comparison

```
CURRENT (primary)                    NEW (primary agent)
=================                    ==================
guidance-extract.md    285 lines     extraction-primary-agent.md  ~50 lines
guidance-inventory/                  extraction/types/guidance/
  SKILL.md             733 lines       core-contract.md          ~733 lines
guidance-inventory/                    primary-pass.md            ~180 lines
  QUERIES.md           755 lines     extraction/
                                       queries-common.md         ~414 lines
PROFILE_TRANSCRIPT.md  242 lines       transcript-queries        ~101 lines
                                     extraction/assets/
                                       transcript.md              242 lines
------------------------------------  ----------------------------------
TOTAL:                2,015 lines    TOTAL:                    ~1,720 lines
REDUNDANT:              206 lines    REDUNDANT:                     0 lines
(accidental)                         (+ 3 guardrails in agent
                                      + ~180 lines in primary-pass.md
                                        — intentional, near-verbatim
                                        from current agent)
IRRELEVANT:               0 lines    IRRELEVANT:                    0 lines
(enrichment never loaded)            (enrichment never loaded)

Post-parity addition:  evidence-standards  46 lines  -> ~1,766 lines total
```

```
CURRENT (enrichment)                 NEW (enrichment agent)
=================                    ==================
guidance-qa-enrich.md  182 lines     extraction-enrichment-agent.md  ~50 lines
guidance-inventory/                  extraction/types/guidance/
  SKILL.md             733 lines       core-contract.md              ~733 lines
guidance-inventory/                    enrichment-pass.md             ~110 lines
  QUERIES.md           755 lines     extraction/
                                       queries-common.md             ~414 lines
PROFILE_TRANSCRIPT.md  242 lines       transcript-queries            ~101 lines
                                     extraction/assets/
                                       transcript.md                  242 lines
------------------------------------  ----------------------------------
TOTAL:                1,912 lines    TOTAL:                        ~1,650 lines
IRRELEVANT:               0 lines    IRRELEVANT:                        0 lines
(primary never loaded)               (primary never loaded)
```

### The Full Architecture

```
+=============================================================+
|                    GENERIC (never changes)                     |
|                                                               |
|  trigger-extract.py -> Redis -> extraction_worker.py          |
|                                    |                          |
|                          /extract (ONE orchestrator)          |
|                                    |                          |
|         extraction-primary-agent.md    (primary pass)         |
|         extraction-enrichment-agent.md (enrichment pass)      |
|                         |              |                      |
+=========================|==============|======================+
                          |              |
            +-------------+---------+   +---------+
            v                       v             v
+=======================+   +=======================+   +====================+
|  TYPE FOLDER           |   |  PASS-SPECIFIC BRIEFS  |   |  ASSET DIRECTORY    |
|  (shared schema)       |   |  (prompt packets)      |   |  (one per WHERE)    |
|                        |   |                        |   |                     |
|  types/guidance/       |   |  types/guidance/       |   |  assets/            |
|    core-contract.md    |   |    primary-pass.md     |   |    transcript.md    |
|                        |   |    enrichment-pass.md  |   |    transcript-      |
|  Scripts (referenced   |   |                        |   |      queries.md     |
|  by pass files, live   |   |  Near-verbatim from    |   |                     |
|  in earnings-orch/     |   |  current production    |   |  "How to read +     |
|  scripts/):            |   |  agents                |   |   fetch this kind   |
|    guidance_ids.py     |   |                        |   |   of document"      |
|    guidance_writer.py  |   |                        |   |                     |
+=======================+   +=======================+   +====================+
```

### ONE Orchestrator

```
/extract {TICKER} {ASSET} {SOURCE_ID} TYPE={type} MODE={mode} RESULT_PATH={path}

  Read assets/{ASSET}.md -> check if it has secondary sections

  1. Spawn Task(extraction-primary-agent):
     "{TICKER} {ASSET} {SOURCE_ID} TYPE={type} MODE={mode}"

  2. Check enrichment: Glob for extraction/types/{type}/enrichment-pass.md
     If file exists AND asset has secondary sections:
       Spawn Task(extraction-enrichment-agent):
       "{TICKER} {ASSET} {SOURCE_ID} TYPE={type} MODE={mode}"

  3. Clean up pass result files (/tmp/extract_pass_* for this job)
  4. Write combined result file to RESULT_PATH (passed by worker, UUID-suffixed)
     (deterministic via Write tool -- not LLM text generation)
     Result MUST contain: type, source_id, status
```

### How the Two Agents Work

```
extraction-primary-agent.md receives:
  {TICKER} {ASSET} {SOURCE_ID} TYPE={type} MODE={mode}

  STEP 0: Load instructions
    Read extraction/types/{type}/core-contract.md       <- shared schema, IDs, rules
    Read extraction/types/{type}/primary-pass.md         <- primary prompt packet
    Read extraction/assets/{asset}.md                    <- how to read source
    Read extraction/queries-common.md                    <- shared queries
    Read extraction/assets/{asset}-queries.md             <- asset-specific queries
    Read .claude/skills/evidence-standards/SKILL.md       <- [POST-PARITY]

  "primary-pass.md is your complete working brief. Follow it start to finish.
   core-contract.md is reference for schema details."

  STEP 1: FETCH -- queries 1A, 1B, 2A, 2B, 7A + asset-specific queries
  STEP 2: EXTRACT -- LLM reads text, applies rules from primary-pass.md
  STEP 3: VALIDATE -- call scripts from contract (types/{type}/*.py)
  STEP 4: WRITE -- call write script from contract

  Write result: /tmp/extract_pass_{TYPE}_primary_{SOURCE_ID}.json
```

```
extraction-enrichment-agent.md receives:
  {TICKER} {ASSET} {SOURCE_ID} TYPE={type} MODE={mode}

  STEP 0: Load instructions
    Read extraction/types/{type}/core-contract.md       <- shared schema, IDs, rules
    Read extraction/types/{type}/enrichment-pass.md      <- enrichment prompt packet
    Read extraction/assets/{asset}.md                    <- how to read source
    Read extraction/queries-common.md                    <- shared queries
    Read extraction/assets/{asset}-queries.md             <- asset-specific queries
    Read .claude/skills/evidence-standards/SKILL.md       <- [POST-PARITY]

  "enrichment-pass.md is your complete working brief. Follow it start to finish.
   core-contract.md is reference for schema details."

  STEP 1: FETCH context + existing items (7E) + secondary content
  STEP 2: EXTRACT with verdicting (ENRICHES/NEW/NO_GUIDANCE)
  STEP 3: VALIDATE + completeness check (7F)
  STEP 4: WRITE -- only changed/new items

  Write result: /tmp/extract_pass_{TYPE}_enrichment_{SOURCE_ID}.json
```

### How Two-Pass Works: Type x Asset Intersection

Two-pass is determined by the COMBINATION of asset (has secondary sections) and type (defines enrichment behavior). Neither alone is sufficient.

```
Decision tree:

  Does asset have secondary sections?
    NO  -> 1 pass (primary only)
    YES -> Does types/{type}/enrichment-pass.md exist?
             NO  -> 1 pass (type doesn't use enrichment for this asset)
             YES -> 2 passes (primary + enrichment)
```

The asset declares WHAT sections exist (markdown metadata, not YAML frontmatter):

```markdown
## Asset Metadata
- sections: prepared_remarks, qa
- label: Transcript
- neo4j_label: Transcript
```

```
transcript.md:  sections: prepared_remarks, qa     -> has secondary
8k.md:          sections: full                      -> no secondary
news.md:        sections: full                      -> no secondary
10q.md:         sections: full                      -> no secondary
```

The type contract declares HOW to use those sections:
```
types/guidance/
  primary-pass.md:     "Extract from prepared_remarks only"
  enrichment-pass.md:  readback, verdicting, completeness check
                       (triggered when asset has secondary sections)
```

A future type might NOT have `enrichment-pass.md`. In that case, even for transcripts, only one pass runs. No CapabilitySpec needed -- the orchestrator checks two things: asset sections and `enrichment-pass.md` file existence.

---

## S3: Design Decisions

**D1: Contract-driven** -- Each type is defined by a contract file + scripts. Working code IS the contract.

**D2: Two focused generic agents** -- Two agent shells (`extraction-primary-agent.md`, `extraction-enrichment-agent.md`), each ~50 lines, each loading only its own pass-specific prompt packet. Primary never sees enrichment instructions; enrichment never sees primary instructions. Zero cross-contamination. Both are generic — they work for any type via file path convention. Adding a type = adding a folder, NOT adding agents.

**D3: One orchestrator** -- `/extract` handles all types and assets. The agent routes to the correct asset profile via file path convention (`assets/{asset}.md`), not if/else.

**D4: Two-pass is type x asset** -- The asset declares its sections. The type contract declares enrichment behavior. The orchestrator checks BOTH before spawning an enrichment pass.

**D5: File path convention replaces routing code** -- `types/{type}/core-contract.md`, `types/{type}/primary-pass.md`, and `assets/{asset}.md` are loaded by name from the prompt. No registry, no YAML, no if/else. The filesystem IS the registry.

**D6: Per-type status properties** -- `guidance_status`, `analyst_status` on source nodes. Trigger constructs `f"{type}_status"` dynamically. Neo4j is schema-free.

**D7: Single queue `extract:pipeline`** -- One Redis queue for all jobs. Payload carries `asset` and `type` (singular). BRPOP is atomic — multiple workers can safely consume from the same queue without popping the same item. The real concurrency risk is duplicate queue entries (trigger run twice, retry re-queues overlapping with new entries). Mitigation: writes are idempotent via MERGE (safe by design). For stricter duplicate-job tolerance, add Redis `SET NX` locking on `extract:lock:{source_id}` with TTL.

**D8: One job = one type** -- Each queue message is exactly one type + one asset + one source. No multi-type batching. Retries, status, and observability are trivially simple.

**D9: Generic runtime, specialized prompt packets** -- Infrastructure (trigger, worker, queue, orchestrator, agent shells) is generic. Prompt content (pass-specific briefs) is specialized — near-verbatim from the current production agents, loaded in isolation so each pass sees only its own instructions.
  **(a) Guardrails** — Three safety-critical rules echoed in both agent shells AND core-contract.
  **(b) `primary-pass.md` (~180 lines)** — near-verbatim from `guidance-extract.md`: extraction rules, bash templates, JSON example, output format. Loaded ONLY by the primary agent.
  **(c) `enrichment-pass.md` (~110 lines)** — near-verbatim from `guidance-qa-enrich.md`: verdict taxonomy, completeness check, quote format. Loaded ONLY by the enrichment agent.
  Pass briefs ARE redundant with core-contract sections. The redundancy preserves the production-tuned prompt-engineering knowledge that drives extraction quality. Thin summaries or cross-references ("see S4") lose signal density.

**D10: Separate labels per type** -- Guidance (tag) + GuidanceUpdate (data-point) + GuidancePeriod (supporting). Future types follow same pattern with their own labels.

**D11: Per-type scripts** -- `ids.py`, `writer.py`, `write_cli.py` are type-owned. No premature abstraction into shared write_cli.py. Revisit when type #2 reveals the actual shared pattern.

**D12: Asset-owned queries** -- `queries-common.md` holds shared queries (context, caches, existing items, fulltext, keywords). Each asset owns its fetch queries in `assets/{asset}-queries.md`. Agent loads common + asset-specific. Reduces irrelevant context (~309 lines) per invocation. "Add an asset" = one directory, no shared file edits.

**D13: File-based result protocol** -- Worker generates a unique `RESULT_PATH` per job (UUID-suffixed, e.g., `/tmp/extract_result_{TYPE}_{SOURCE_ID}_{UUID}.json`) and passes it in the prompt. Orchestrator writes the combined result to that path. Result file MUST contain `type`, `source_id`, `status`. Missing or malformed file = mark as failed. This eliminates stale-file bugs on retry and collision on duplicate queue entries. Follows the existing `/tmp/gu_` payload pattern with deterministic Write tool (not LLM text generation).

**D14: Type whitelist** -- Worker validates `type` from queue payload against a known set before constructing Cypher queries. Defense-in-depth against injection via CLI arguments.

---

## S4: File Layout

```
.claude/skills/extraction/                    <- NEW directory
|
|-- SKILL.md                                  <- Generic orchestrator (~25 lines)
|                                               /extract {TICKER} {ASSET} {SOURCE_ID}
|                                               TYPE={type} MODE={mode}
|
|-- queries-common.md                         <- Shared queries: S1 context, S2 caches,
|                                               S7 existing items, S8 inventory,
|                                               S9 fulltext, S10 keywords (~414 lines)
|
|-- types/
|   \-- guidance/
|       |-- core-contract.md                  <- guidance-inventory/SKILL.md (733 lines)
|       |                                       Schema, fields, IDs, XBRL, validation,
|       |                                       write path, error taxonomy
|       |
|       |-- primary-pass.md                   <- Primary prompt packet (~180 lines)
|       |                                       Near-verbatim from guidance-extract.md:
|       |                                       extraction rules + bash templates +
|       |                                       JSON example + output format
|       |
|       \-- enrichment-pass.md                <- Enrichment prompt packet (~110 lines)
|                                               Near-verbatim from guidance-qa-enrich.md:
|                                               verdicts + completeness + quote format
|
\-- assets/
    |-- transcript.md                         <- Profile (data structure, scan scope, sections)
    |-- transcript-queries.md                 <- S3 fetch queries (3A-3G, ~101 lines)
    |-- 8k.md                                 <- Profile
    |-- 8k-queries.md                         <- S4 fetch queries (4A-4G, ~91 lines)
    |-- news.md                               <- Profile
    |-- news-queries.md                       <- S6 fetch queries (6A-6E, ~61 lines)
    |-- 10q.md                                <- Profile
    \-- 10q-queries.md                        <- S5 fetch queries (5A-5E, ~56 lines)

.claude/agents/
|-- extraction-primary-agent.md               <- Generic primary agent (~50 lines)
\-- extraction-enrichment-agent.md            <- Generic enrichment agent (~50 lines)

scripts/
|-- trigger-extract.py                        <- NEW (based on trigger-guidance.py)
\-- extraction_worker.py                      <- NEW (based on earnings_worker.py)
```

### Original Files -- ALL UNTOUCHED

| File | Status |
|------|--------|
| `.claude/skills/guidance-transcript/SKILL.md` | FROZEN |
| `.claude/agents/guidance-extract.md` | FROZEN |
| `.claude/agents/guidance-qa-enrich.md` | FROZEN |
| `.claude/skills/guidance-inventory/SKILL.md` | FROZEN |
| `.claude/skills/guidance-inventory/QUERIES.md` | FROZEN |
| `.claude/skills/guidance-inventory/reference/PROFILE_*.md` | FROZEN |
| All scripts (`guidance_ids.py`, etc.) | FROZEN (shared by both old + new) |
| `scripts/trigger-guidance.py` | FROZEN |
| `scripts/earnings_worker.py` | FROZEN |

### What the Type Files Contain

**`types/guidance/core-contract.md`** (~733 lines) = current SKILL.md:

```
core-contract.md
|
|-- S1-S14: IDENTICAL to current SKILL.md S1-S14
|           (schema, fields, IDs, normalization, derivation,
|            basis, segment, unit, period, XBRL, source, quality)
|
|-- S15: Write Path (pipeline, modes, error taxonomy)
|-- S16: Execution Modes
|-- S17: Error Taxonomy
\-- S18: Reference Files
```

This is the shared reference material. Both agents load it. It defines WHAT guidance is, HOW IDs are computed, and WHERE to write results. It does NOT contain pass-specific instructions.

**`types/guidance/primary-pass.md`** (~180 lines) = production-tuned primary prompt packet:

```
primary-pass.md — near-verbatim from guidance-extract.md
|
|-- Pipeline steps (fetch, extract, validate, write)
|-- Extraction rules (adapted from agent's 98 curated lines):
|     - Metric decomposition (base label + segment split)
|     - Basis rules (explicit-only qualifier, else "unknown")
|     - Segment rules (default "Total", set only for business dimensions)
|     - Quality / acceptance filters (what to extract vs skip)
|     - Numeric value rules (copy exactly as printed)
|     - LLM period extraction fields table
|     - Quote / citation requirements (max 500 chars, no citation = no node)
|     - No fabricated numbers (qualitative = implied/comparative derivation)
|-- Practical how-to (from agent's 79 unique lines):
|     - Bash templates: build_guidance_period_id, build_guidance_ids
|     - JSON payload full example with all fields
|     - guidance_write.sh exact invocation commands
|     - Output format spec + "no TSV" rule
|-- Scope: "Extract from primary section only"
\-- MUST invoke deterministic validation via scripts
```

**`types/guidance/enrichment-pass.md`** (~110 lines) = production-tuned enrichment prompt packet:

```
enrichment-pass.md — near-verbatim from guidance-qa-enrich.md
|
|-- Step 1: Load existing items (7E readback)
|-- Step 2: Load secondary content (asset-specific query)
|-- Step 3: Verdict taxonomy (ENRICHES / NEW / NO_GUIDANCE)
|-- Step 4: Q&A Analysis Log format (MANDATORY, with topic summary)
|-- Step 5: Completeness check vs 7F baseline
|-- Step 6: Quote enrichment format [PR]...[Q&A]
|-- Rule: "Only write changed/new items"
|-- Extraction rules (from agent's 42 curated lines):
|     - Quality / acceptance filters
|     - No fabricated numbers
|     - Quote max 500 chars, no citation = no node
|     - Metric decomposition for new Q&A-only items
|-- Practical how-to:
|     - JSON payload assembly for enriched + new items
|     - guidance_write.sh invocation
|     - Output format spec
\-- MUST invoke deterministic validation via scripts
```

**Why separate pass files, not one monolithic contract**: The current agents were iterated to production quality through real extraction runs. That iteration baked in implicit prompt-engineering knowledge — which rules to emphasize, what order to present them, what examples to include. Each pass file preserves this knowledge near-verbatim and is loaded ONLY by its corresponding agent. The primary agent never sees enrichment logic; the enrichment agent never sees primary-only logic. Zero cross-contamination. Generic runtime for maintainability; specialized prompt packets for extraction quality.

**Rules for pass files**: They ARE redundant with core-contract sections (S4/S6/S7/S13) — intentionally. They should read like standalone agent instructions, not like references to earlier sections. Must NOT cross-reference "see S4" — inline the rules. The production-tuned wording from the current agents should be preserved, not summarized.

**Implementation rule**: During implementation, `primary-pass.md` should be built by literally copying `guidance-extract.md`'s content and editing for structure, not by rewriting from scratch. Same for `enrichment-pass.md` from `guidance-qa-enrich.md`. Copy first, restructure minimally.

**Attention weight trade-off**: The generic shell + pass brief design is close to the current system but not identical — the extraction rules move from the agent prompt (high attention weight) to a Read-loaded file (slightly lower attention weight). For extraction quality, the v1.5 approach of copying agents directly is marginally safer. The pass-brief design accepts this small trade-off in exchange for generic extensibility. Mitigate by keeping pass files as close to the original agent content as possible — copy, don't rewrite.

Core contracts should only be as long as needed. The guidance core is ~733 lines because guidance extraction is genuinely complex. A simpler type might have a 200-line core. Pass files vary by complexity — guidance primary is ~180 lines; a simple type's primary might be 60 lines.

### What the Generic Agents Contain

Both agent shells are ~50 lines, ~80% identical. The only difference is which pass file they load.

```
extraction-primary-agent.md (~50 lines)
|
|-- Frontmatter (tools, model, permissionMode)
|
|-- GUARDRAILS (echoed from contract for emphasis):
|     "NEVER write Cypher directly"
|     "MUST invoke deterministic validation via scripts"
|
|-- Auto-Load (5 files for parity, 6 for end-state):
|     1. Read extraction/types/{TYPE}/core-contract.md
|     2. Read extraction/types/{TYPE}/primary-pass.md
|     3. Read extraction/assets/{ASSET}.md
|     4. Read extraction/queries-common.md
|     5. Read extraction/assets/{ASSET}-queries.md
|     6. Read .claude/skills/evidence-standards/SKILL.md  [POST-PARITY]
|
|-- Input: {TICKER} {ASSET} {SOURCE_ID} TYPE={type} MODE={mode}
|
|-- "primary-pass.md is your complete working brief.
|    core-contract.md is reference. Follow primary-pass.md start to finish."
|
|-- Result: Write /tmp/extract_pass_{TYPE}_primary_{SOURCE_ID}.json
\-- Error handling: reference core-contract S17
```

```
extraction-enrichment-agent.md (~50 lines)
|
|-- Frontmatter (tools, model, permissionMode)
|
|-- GUARDRAILS (echoed from contract for emphasis):
|     "NEVER write Cypher directly"
|     "MUST invoke deterministic validation via scripts"
|     "ONLY write changed/new items"
|
|-- Auto-Load (5 files for parity, 6 for end-state):
|     1. Read extraction/types/{TYPE}/core-contract.md
|     2. Read extraction/types/{TYPE}/enrichment-pass.md
|     3. Read extraction/assets/{ASSET}.md
|     4. Read extraction/queries-common.md
|     5. Read extraction/assets/{ASSET}-queries.md
|     6. Read .claude/skills/evidence-standards/SKILL.md  [POST-PARITY]
|
|-- Input: {TICKER} {ASSET} {SOURCE_ID} TYPE={type} MODE={mode}
|
|-- "enrichment-pass.md is your complete working brief.
|    core-contract.md is reference. Follow enrichment-pass.md start to finish."
|
|-- Result: Write /tmp/extract_pass_{TYPE}_enrichment_{SOURCE_ID}.json
\-- Error handling: reference core-contract S17
```

### Query Split

Current `QUERIES.md` (755 lines, 42 queries) splits cleanly along existing section boundaries:

```
queries-common.md (~414 lines):
  S1  Context Resolution (1A-1D)        56 lines   <- shared
  S2  Warmup Caches (2A-2B)             89 lines   <- shared
  S7  Existing Guidance Lookup (7A-7F)  92 lines   <- shared
  S8  Data Inventory (8A-8B)            40 lines   <- shared
  S9  Fulltext / Keyword Recall (9A-9F) 76 lines   <- shared
  S10 Guidance Extraction Keywords      61 lines   <- shared

transcript-queries.md (~101 lines):
  S3  Source Content: Transcript (3A-3G)           <- asset-specific

8k-queries.md (~91 lines):
  S4  Source Content: 8-K / Exhibits (4A-4G)       <- asset-specific

10q-queries.md (~56 lines):
  S5  Source Content: 10-Q / 10-K (5A-5E)          <- asset-specific

news-queries.md (~61 lines):
  S6  Source Content: News (6A-6E)                  <- asset-specific
```

### Scripts -- Shared, Not Copied

All extraction scripts stay in `.claude/skills/earnings-orchestrator/scripts/`. The type contract references them by path. Future types add their scripts to the same directory (`analyst_ids.py`, `analyst_writer.py`, `analyst_write_cli.py`). Accept the historical `earnings-orchestrator/` naming -- renaming would break every path reference in every contract for zero functional benefit. Use symlinks only if the name becomes genuinely confusing.

---

## S5: How to Add Things

### Add a New Type ("analyst")

```
CREATE:
  extraction/types/analyst/
    core-contract.md                       <- schema, fields, IDs, validation
    primary-pass.md                        <- primary extraction prompt packet
    enrichment-pass.md                     <- enrichment prompt packet (or omit if N/A)
  earnings-orchestrator/scripts/
    analyst_ids.py                         <- deterministic ID computation
    analyst_writer.py                      <- Neo4j MERGE patterns
    analyst_write_cli.py                   <- CLI glue

EDIT:
  trigger-extract.py                      <- add "analyst" to ALLOWED_TYPES
  extraction_worker.py                    <- add "analyst" to ALLOWED_TYPES

AGENTS: reused (both generic agents load types/{type}/ by name)
ORCHESTRATOR: reused (/extract handles all types via TYPE= param)
TRIGGER: reused (trigger-extract.py --type analyst)
WORKER: reused (extraction_worker.py reads type from payload)

TOTAL: 5-6 files created + 1 line added to 2 files. Everything else is reused.
```

### Add a New Asset ("press-release")

```
CREATE:
  extraction/assets/press-release.md             <- profile (data structure, scan scope, sections)
  extraction/assets/press-release-queries.md     <- fetch queries

EDIT:
  trigger-extract.py                             <- add entry to ASSET_QUERIES dict

AGENTS: reused (both read assets/{asset}.md + {asset}-queries.md by name)
ORCHESTRATOR: reused (/extract AAPL press-release ...)
TRIGGER: reused (--asset press-release)
WORKER: reused

TOTAL: 2 files created + 1 line added to trigger. Everything else is reused.
```

### Contract Checklist for New Types

Every new type MUST define in its type folder:

**A. Graph Schema** -- complete node/relationship map:

| Component | Guidance Reference | New Type Fills In |
|-----------|-------------------|-------------------|
| Tag node (one per metric) | `Guidance` (id, label, aliases) | `{Type}Topic` |
| Data-point node (one per extraction) | `GuidanceUpdate` (20+ fields) | `{Type}Item` |
| Supporting nodes | `GuidancePeriod` (optional) | As needed |
| Relationships | UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD, MAPS_TO_CONCEPT, MAPS_TO_MEMBER | Required: UPDATES, FROM_SOURCE, FOR_COMPANY. Optional: rest. |

**B. Extraction Contract:**

| Component | Must Define |
|-----------|-------------|
| ID slot formula | `{prefix}:{source}:{label}:{period}:{basis}:{segment}` |
| Extraction fields | Every field the LLM must extract |
| Quality filters | What to accept/reject |
| Validation rules | Unit canonicalization, period resolution, etc. |
| Error taxonomy | Standard error codes |
| Execution modes | dry_run / shadow / write |
| Script invocations | Exact Bash one-liners for calling scripts |
| JSON payload format | Full example with all fields |
| Output format | Structured summary template |
| `primary-pass.md` | Self-contained prompt packet: pipeline steps + extraction rules + bash templates + JSON example + output format. Must NOT cross-reference "see S4" — inline the rules. |
| `enrichment-pass.md` | Self-contained prompt packet: verdict taxonomy, log format, completeness check + extraction rules + output format. Omit file entirely if type doesn't use enrichment. |

Core contracts should only be as long as needed. A simple type might have a 200-line core and 60-line pass files. Pass files should read like standalone agent instructions, not like references to the core contract.

---

## S6: K8s Infrastructure

### Single Queue, One Job Per Type

**Trigger** (`trigger-extract.py`, new file based on `trigger-guidance.py`):

```
trigger-extract.py
  --type guidance|analyst|all
  --asset transcript|8k|10q|news|all
  --ticker AAPL [or --all]
  --mode write

  -> Queries Neo4j: WHERE t.{type}_status IS NULL
  -> Groups by ticker
  -> LPUSH one message per (type, asset, source_id) to Redis "extract:pipeline"
```

**Asset-specific trigger queries** -- the trigger is a Python script, not an LLM. It cannot read markdown asset profiles. Per-asset MATCH patterns live in a dict:

```python
ASSET_QUERIES = {
    "transcript": ("Transcript", "t"),
    "8k": ("Report", "r", "r.formType = '8-K'"),
    "10q": ("Report", "r", "r.formType IN ['10-Q', '10-K']"),
    "news": ("News", "n"),
}
```

This is the one piece of asset-specific knowledge that lives in Python code, not markdown. Adding an asset = adding one line to this dict.

**Payload** (one type + one source per message, always):

```json
{
  "asset": "transcript",
  "ticker": "AAPL",
  "source_id": "AAPL_2025-01-30T17.00",
  "type": "guidance",
  "mode": "write"
}
```

**Worker** (`extraction_worker.py`, new file based on `earnings_worker.py`):

```
1. BRPOP from "extract:pipeline"
2. Parse payload — extract asset, ticker, source_id, type, mode
3. Validate type against ALLOWED_TYPES whitelist
4. mark_status(type, source_id, "in_progress")
   -> SET t.{type}_status = 'in_progress'
5. Generate RESULT_PATH = /tmp/extract_result_{type}_{source_id}_{uuid}.json
6. Claude SDK: query("/extract {ticker} {asset} {source_id}
   TYPE={type} MODE={mode} RESULT_PATH={result_path}")
7. Read RESULT_PATH — validate type, source_id, status fields
8. If result file valid and status=completed:
     mark_status(type, source_id, "completed")
   Else (missing, malformed, or status!=completed):
     mark_status(type, source_id, "failed")
     SET t.{type}_error = error message
9. Clean up RESULT_PATH
10. On failure: retry up to 3x, then dead-letter
```

Worker inherits structured logging, usage/cost tracking, and duration metrics from `earnings_worker.py` patterns.

### Result Protocol (file-based, unique per job)

Results flow through deterministic files, not LLM text parsing. Worker generates a unique `RESULT_PATH` per job invocation to prevent stale-file and collision bugs:

```
Worker:
  Generates RESULT_PATH = /tmp/extract_result_{TYPE}_{SOURCE_ID}_{UUID}.json
  Passes RESULT_PATH in prompt to /extract skill

Agent (each pass):
  Writes /tmp/extract_pass_{TYPE}_{PASS}_{SOURCE_ID}.json via Write tool
  {"status": "completed", "items_extracted": 12, "items_written": 12, "errors": 0}

Orchestrator:
  Reads pass result files
  Writes combined result to RESULT_PATH (from prompt) via Write tool
  Deletes pass result files after combining (cleanup ownership: each layer
    cleans up what the layer below produced)
  Required fields: {"type": "guidance", "source_id": "...", "status": "completed",
                     "primary_items": 12, "enriched_items": 3, "new_qa_items": 1}

Worker:
  Reads RESULT_PATH (it generated the path, knows exactly where to look)
  Missing file = mark as failed
  Malformed file (missing type/source_id/status) = mark as failed
  Cleans up result file after reading
```

This follows the existing pattern: the agent already writes `/tmp/gu_{TICKER}_{SOURCE_ID}.json` as its extraction payload. Result files use the same deterministic Write tool approach. No regex parsing of LLM output. UUID suffix ensures retries and duplicate queue entries never collide.

### Status Tracking

```python
# Type whitelist (defense-in-depth):
ALLOWED_TYPES = {"guidance", "analyst", "announcement"}
assert type in ALLOWED_TYPES, f"Unknown type: {type}"

# Trigger query (generic via string interpolation):
# Node label comes from ASSET_QUERIES dict (Transcript, Report, News)
status_prop = f"{type}_status"
label, alias = ASSET_QUERIES[asset][:2]
query = f"MATCH ({alias}:{label}) WHERE {alias}.{status_prop} IS NULL ..."

# Worker set (generic — label resolved from payload's asset field):
query = f"MATCH ({alias}:{label} {{id: $sid}}) SET {alias}.{status_prop} = $status"

# On failure, also set error property:
query = f"MATCH ({alias}:{label} {{id: $sid}}) SET {alias}.{status_prop} = 'failed', {alias}.{type}_error = $error"
```

No ExtractionStatus nodes. No new labels. No new relationships. Adding a type adds one property per source node. Neo4j is schema-free.

### Dead-Letter Queue

```python
DEAD_LETTER_QUEUE = f"{QUEUE_NAME}:dead"  # = "extract:pipeline:dead"
```

After MAX_RETRIES (3) failures, worker LPUSHes to dead-letter queue with enriched payload:

```json
{
  "asset": "transcript",
  "ticker": "AAPL",
  "source_id": "AAPL_2025-01-30T17.00",
  "type": "guidance",
  "mode": "write",
  "_retry": 4,
  "_error": "No result file after SDK completion",
  "_failed_at": "2026-03-06T14:30:00Z"
}
```

Also sets `{type}_status = 'failed'` and `{type}_error` on the source node. Gives both queue-level and graph-level failure visibility.

### Concurrency

BRPOP is atomic — multiple workers can safely consume from the same queue (each message goes to exactly one consumer). The real concurrency risk is **duplicate queue entries**: trigger run twice, or retry re-queues overlapping with new trigger runs, causing two workers to process the same source_id simultaneously. Mitigations:

1. **Writes are idempotent by design** — MERGE-based writes produce the same result regardless of execution count
2. **Status properties are eventually consistent** — both workers set `{type}_status = 'completed'`, safe to overwrite
3. **For stricter dedup (optional)** — add Redis `SET NX` locking on `extract:lock:{source_id}` with TTL before processing; skip if lock already held

### K8s Files

| New File | Based On | Change |
|----------|----------|--------|
| `scripts/extraction_worker.py` | `earnings_worker.py` | Generic payload, single type, file-based result, type whitelist, DLQ, error property |
| `scripts/trigger-extract.py` | `trigger-guidance.py` | `--type`/`--asset` flags, ASSET_QUERIES dict, generic query, new queue |
| `k8s/processing/extraction-worker.yaml` | `claude-code-worker.yaml` | KEDA for `extract:pipeline` |

Original K8s files stay frozen until retirement.

---

## S7: Quality & Validation

### Golden Checks

Any reorganization MUST produce identical output:

1. **Same GuidanceUpdate IDs** -- deterministic slot-based IDs match exactly
2. **Same key field values** -- low/mid/high, basis, period, derivation, unit, segment, quote
3. **Same relationship edge counts** -- FROM_SOURCE, FOR_COMPANY, HAS_PERIOD per source
4. **Idempotent rerun** -- same transcript twice = zero new nodes
5. **Same error taxonomy** -- SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_GUIDANCE unchanged

### Validation Method

Run both pipelines on the same 5+ transcripts in `dry_run` mode. Both write to `/tmp/gu_{TICKER}_{SOURCE_ID}.json`. Run old, rename output, run new, `diff` the two files.

---

## S8: Implementation Phases

### Phase 1: Build New Infrastructure

Create the extraction framework alongside the existing pipeline. Nothing existing is moved.

| Step | Action | Validation |
|------|--------|------------|
| 1.1 | Create `extraction/assets/` directory. Copy + rename PROFILE files -> `assets/{asset}.md`. Add `## Asset Metadata` section with `sections:` to each. | New copies exist with metadata, originals untouched |
| 1.2 | Split `guidance-inventory/QUERIES.md` into `queries-common.md` + per-asset query files (`transcript-queries.md`, `8k-queries.md`, `10q-queries.md`, `news-queries.md`). Cut along existing section boundaries. | Combined content byte-identical to original. No query lost. |
| 1.3 | Create `types/guidance/core-contract.md` from SKILL.md (733 lines). Create `types/guidance/primary-pass.md` (~180 lines, near-verbatim from `guidance-extract.md`: extraction rules + bash templates + JSON example + output format). Create `types/guidance/enrichment-pass.md` (~110 lines, near-verbatim from `guidance-qa-enrich.md`: verdicts + completeness + quote format). | Core has all SKILL.md content. Pass files preserve production-tuned agent content. |
| 1.4 | Create two generic agents: `extraction-primary-agent.md` and `extraction-enrichment-agent.md` (~50 lines each), guardrail echoes, auto-load 5 files each (core-contract, pass brief, asset, common queries, asset queries). evidence-standards (6th file) omitted for parity — added post-parity in Phase 3. | Each agent loads only its own pass file. Primary never sees enrichment. |
| 1.5 | Create `/extract` orchestrator: one skill, receives `TYPE` + `ASSET` in prompt, checks asset sections + `enrichment-pass.md` existence for two-pass, spawns appropriate agent, writes result file | Spawns same pipeline as `/guidance-transcript` |
| 1.6 | **Baseline validation**: Run `/extract AAPL transcript AAPL_2025-01-30T17.00 TYPE=guidance MODE=dry_run` on 5+ transcripts, diff against `/guidance-transcript` | Golden checks pass (S7) |

**Implementation note**: Two focused agents IS the target architecture. If step 1.6 reveals parity issues, debug the pass files — the production-tuned content should match the current agents near-verbatim.

### Phase 2: Generalize Trigger + Worker

| Step | Action | Validation |
|------|--------|------------|
| 2.1 | Create `trigger-extract.py` (based on `trigger-guidance.py`) with `--type`/`--asset` flags, ASSET_QUERIES dict, dynamic status property | `--type guidance --asset transcript` produces correct payloads |
| 2.2 | Create `extraction_worker.py` (based on `earnings_worker.py`) with file-based result reading, type whitelist, DLQ spec, `{type}_error` property | Reads payload, invokes `/extract`, reads result file, marks correct status |
| 2.3 | New queue `extract:pipeline` (old `earnings:trigger` stays) | KEDA config |
| 2.4 | **Canary validation**: `/extract AAPL transcript {known_source_id} TYPE=guidance MODE=dry_run` -> expect result file with `"status": "completed"` and non-zero items | Canary green |
| 2.5 | **End-to-end K8s validation** | trigger -> queue -> worker -> `/extract` -> result file -> Neo4j |

### Phase 3: Expand to Other Assets (guidance only) + Post-Parity Additions

| Step | Action | Validation |
|------|--------|------------|
| 3.0 | **Post-parity**: Add evidence-standards as 6th auto-load in both agent shells. This changes prompt context and is NOT parity-neutral — added only after Phase 1-2 golden checks pass. | Both agents load 6 files. Output may differ slightly (stricter anti-hallucination). |
| 3.1 | Add `--asset 8k` entry to ASSET_QUERIES dict | Trigger finds unprocessed 8-Ks |
| 3.2 | Run `/extract AAPL 8k {accession} TYPE=guidance MODE=dry_run` on 3+ 8-Ks | Golden checks pass |
| 3.3 | Repeat for `--asset 10q` (10-Q + 10-K) | |
| 3.4 | Repeat for `--asset news` | |
| 3.5 | **Cross-asset validation** | All assets produce valid output |

### Phase 4: First Non-Guidance Type (future)

| Step | Action | Validation |
|------|--------|------------|
| 4.1 | Choose type (analyst? announcement?) | |
| 4.2 | Create `types/{type}/core-contract.md` + `primary-pass.md` + optional `enrichment-pass.md` + scripts (5-6 files) | |
| 4.3 | Add type to ALLOWED_TYPES in trigger + worker | |
| 4.4 | Run `/extract AAPL transcript {sid} TYPE={type} MODE=dry_run` | |
| 4.5 | Evaluate whether `write_cli.py` pattern should be abstracted | Only if >50% shared code between types |
| 4.6 | Proves the framework works for multiple types | |

### Retirement (quality-gated, no timeline)

Gates:
1. New infrastructure running in parallel for significant period
2. Golden checks pass consistently
3. User has reviewed output quality and explicitly approved
4. No regressions in any edge case

When approved: new files replace frozen counterparts. K8s: `trigger-extract.py` replaces `trigger-guidance.py`, `extraction_worker.py` replaces `earnings_worker.py`, `extract:pipeline` replaces `earnings:trigger`.

Post-retirement: accept the historical `earnings-orchestrator/` directory naming. Renaming would break every path reference in every contract for zero functional benefit. Use symlinks only if the name becomes genuinely confusing.

---

## S9: Data Assets -- Status

| Asset | Status | Profile | Queries | Gap |
|-------|--------|---------|---------|-----|
| **Transcript** | Production | transcript.md | transcript-queries.md (S3) | Build `/extract` alongside -> golden checks |
| **8-K** | Agent-ready | 8k.md | 8k-queries.md (S4) | Phase 3: extend trigger, validate |
| **10-Q/10-K** | Agent-ready | 10q.md | 10q-queries.md (S5) | Phase 3: extend trigger, validate |
| **News** | Agent-ready | news.md | news-queries.md (S6) | Phase 3: extend trigger, validate |

---

## S10: Design Rationale

Decisions evaluated against the actual codebase with line-by-line reasoning.

| # | Decision | Reasoning |
|---|----------|-----------|
| 1 | Two-pass = type x asset | `guidance-qa-enrich.md` does readback (7E), verdicting (ENRICHES/NEW), completeness check (7F) -- all type-specific. A future analyst type would have different enrichment logic. Asset declares sections; type contract declares what to do with them. |
| 2 | One job = one type | Multi-type jobs make retries ambiguous, status tracking complex, result parsing harder. Queue cost is negligible (Redis LPUSH is free; Claude SDK invocation cost is the same either way). |
| 3 | Two focused agents (not one with PASS=) | Primary agent loads only `primary-pass.md`; enrichment loads only `enrichment-pass.md`. Zero cross-contamination — each agent's context is 100% relevant to its task. Matches the current system's signal density. Two ~50-line generic shells (~80% identical) is trivial maintenance cost for meaningful extraction quality benefit. |
| 4 | Asset-owned queries | Clean separation of concerns. Agent loads only relevant queries (~100 lines) instead of all 42 queries (~755 lines). "Add an asset" = one directory, no shared file edits. Split follows existing section boundaries -- trivial cut. |
| 5 | Reject ExtractionStatus nodes | `{type}_status` is already generic via `f"{type}_status"` string interpolation. ExtractionStatus adds a label + relationship + query complexity for zero benefit with <5 types. |
| 6 | Per-type scripts, not shared write_cli | ~70% of `guidance_write_cli.py` is guidance-specific (concept inheritance, member matching, guidance_ids imports). Revisit when type #2 reveals actual shared pattern. |
| 7 | File-based result protocol | Write tool is deterministic; LLM text output is fragile (markdown wrapping, commentary, truncation). Worker generates unique RESULT_PATH per job (UUID-suffixed) to prevent stale-file/collision bugs on retry or duplicate queue entries. Result file must contain type, source_id, status. Missing/malformed = failed. |
| 8 | Generic runtime + specialized prompt packets | Infrastructure is generic (two agent shells, one orchestrator). Pass files are specialized prompt packets — near-verbatim from current production agents, loaded in isolation. Preserves the prompt-engineering knowledge iterated through real extraction runs. Thin summaries ("see S4") lose signal density and cost recall/precision. The redundancy with core-contract IS the quality mechanism. |
| 9 | Type whitelist | Defense-in-depth. `f"SET t.{type}_status"` is injection-shaped. Whitelist validates type before Cypher construction. 2 lines. |
| 10 | evidence-standards as cross-type auto-load (post-parity) | 46-line anti-hallucination file applies to ALL extraction, not type-specific. Added as 5th auto-load AFTER parity golden checks pass (Phase 3.0), since any prompt context change is not parity-neutral. |

---

## S11: Open Questions

Items below are NOT blockers to Phase 1-2 implementation. OPEN/DEFERRED/PENDING items are tracked for future phases.

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 1 | GuidancePeriod: share with other types? | DEFERRED | Calendar-based `gp_` is general. Rename when needed. |
| 2 | Budget/cost optimization | OPEN | |
| 3 | `earnings_trigger.py` status | PENDING | Shares old queue. Confirm dormant before retirement. |
| 4 | `guidance-inventory/SKILL.md` too long (733 lines) | DEFERRED | Split S9-S11 into separate reference file post-retirement. |
| 5 | `evidence-standards` loading | RESOLVED | 6th auto-load file in generic agent (cross-type). Added post-parity only. |
| 6 | Rename `{type}-inventory` convention | POST-RETIREMENT | Accept historical naming per retirement section. |
| 7 | Asset `sections` declaration format | RESOLVED | Markdown `## Asset Metadata` section with `- sections: prepared_remarks, qa`. No YAML frontmatter. |
| 8 | Shared write_cli.py abstraction | Phase 4+ | Evaluate when type #2 reveals actual shared pattern. Only if >50% code is shared. |

---

## S12: Why This Is Better

| Dimension | Current system | v3.5 (this plan) |
|-----------|----------------|-------------------|
| Orchestrator skills | 1 (per asset) | **1** (generic, all assets) |
| Agent files | 2 per type (type-specific) | **2 total** (generic shells) |
| Type contract | 1 monolithic (SKILL.md) | **3 files** (core + primary-pass + enrichment-pass) |
| Query organization | 1 monolithic file | **common + per-asset** |
| Jobs per queue message | 1 type implicit | **1 type explicit** |
| Result protocol | LLM text parsing | **Deterministic file (UUID-suffixed)** |
| Two-pass logic | Hardcoded in orchestrator | **Type x asset** |
| Add a type | Create 2 agents + contract | **5-6 files + 1 line x2** (agents reused) |
| Add an asset | Edit orchestrator + agent | **2 files + 1 line** |
| Cross-contamination | None (separate agents) | **None** (separate pass files) |
| Redundant content | 206 lines (accidental) | **~180 lines** (intentional, in pass files + 3 guardrails) |
| Irrelevant context loaded | ~309 lines other-asset queries | **0** |
| Failure visibility | status property only | **status + error property + DLQ** |

---

*v3.5 | 2026-03-06 | Structural change: split from one PASS= agent + monolithic contract into two focused generic agent shells + split type contract (core-contract.md + primary-pass.md + enrichment-pass.md). Each agent loads only its own pass file — primary never sees enrichment instructions, enrichment never sees primary instructions. Zero cross-contamination matches current system's signal density. Pass files remain near-verbatim from current production agents. Architecture is now: generic runtime (trigger, worker, queue, orchestrator, two agent shells) + specialized prompt packets (pass files loaded in isolation) + type-owned scripts + asset-owned queries. Prior: v3.4 (thick S19/S20 in monolithic contract). v3.3 (S19/S20 checklists). v3.2 (unique RESULT_PATH, concurrency, post-parity). v3.1 (operational). v3.0 (core architecture).*
