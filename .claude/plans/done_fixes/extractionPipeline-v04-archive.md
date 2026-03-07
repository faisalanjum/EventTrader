# Extraction Pipeline — Generalization Spec

**DO NOT IMPLEMENT ANYTHING until this plan is 100% complete, validated end-to-end, and explicitly approved. Planning only — no code, no file changes, no "quick fixes" until every section is locked.**

**The whole point of this restructuring is: build a machine where plugging in a new extraction job is trivially easy, the output is bulletproof, and there's zero unnecessary complexity. Guidance-transcript is the proof that the pattern works — we're just making the pattern reusable. Every decision below optimizes for: simplest possible design, never degrade output quality, always be one step closer to implementation.**


**Baseline lock**: The current `/guidance-transcript` pipeline produces near-optimal extraction output. Any reorganization MUST preserve the exact behavior of every underlying component (agents, reference files, scripts, write path). Refactor the scaffolding, never the extraction logic — if a piece moves to a new location, its content stays identical until explicitly revised in a later phase.

### Initial Prompt (verbatim)

> Here is my next task but I am still debating how to accomplish it without breaking anything at all so for now nothing is set in stone. Now most important thing is before we forget anything we can either create a section inside /home/faisal/EventMarketDB/.claude/plans/guidanceInventory.md at the end or even create a new .md inside plan folder. But first help me brainstorm the scafolding of what I am trying to achive and then continiously write to either one of above (whatever we deciede is best). So first step is for me to throughly and deeply understand each line mentioned starting from /guidance-transcript skill including anything underslying it touches such as sub agents, skills, reference files etc - everything. The aim of this is atleast 3 fold. 1. I want it to be a perfect set of skills and sub agents and absolutely following the best practices - with some inspiration from here /home/faisal/EventMarketDB/docs/claude/skills-reference.md  2. I want to understand how can I best generalize this exact structure so same infrastructure can be easily and 100% efficiently be applied to all other data assets in my database such as News, Transcripts, Reports - (seperately for 10-k, 10q, 8k + A BLANKET GROUP FOR ALL OTHER TYPES OF REPORRS) - note a lot of already is in place but looking for super optimization. also I am almost close to super happy with results i AM already getting from /guidance-transcript but still require a few more tweaks which I will explain later (such as maybe removing the company link from guidandceUpdates since its already linked to each data asset which in turn links to the company so its redundant but needs to be thought through about pros and cons. 3. And this is the most important - I want to generlize this entire pipeline in such a way that if tomorow Instead of extracting guidance from each of these data assets, I am looking to extract say any one of these say management announcelemt (already do this for transcripts) and or say analyzt previews and reviews (this may be specific to news) and or any such criteria rather than just guidance, I should be able to do it in super structured and super easy way since pipeline is already set and we could just change the extraction rule sin one file - and ofcourse it may differ per each data asset type. 4. Other few things to keep in mind is it will all be triggered via the │ K8s Worker  │ earnings_worker.py + trigger-guidance.py (which for the most part is already in place but need to be thought through how it will work for different data assets plus different periods reports etc. In the end I need all of the above details to be fleshed out in a perfect way which make sense to me and is in line with super best practices and most importantly this pipeline is created in such a way that adding new sources and or new extraction rules (guidance versus analysis concerns etc is super easy). Building on that I may also need to think about how in neo4j we represent guidanceUpdates & guidance nodes versus say AnalystComents and so on. For now what I am looking for a way to help me structure this endeavour in most strategic manner so I can accomplish this as efficiently, 100% accurately and as easily and quickly as possible. so your task is to organize thsi endeveour which makes it tracktable as well as understandable. finally, as I mentioned the guidance-transcript skill is very close to my ideal ouput atleast in terms of the ouput it generates. Now do you have any questions which may not be clear from the above?

### Guiding Principles

1. **Super minimalism** — zero over-engineering, simplest thing that works
2. **100% output reliability** — guidance-transcript quality is the gold standard, never degrade it
3. **Plug-and-play** — trivially easy to add/remove any extraction type for any data asset
4. **Always actionable** — every planning step inches toward clear implementation; zero paralysis by analysis

**Version**: 0.4 | 2026-03-04
**Status**: Design phase — core architecture locked, details in progress
**Parent**: `guidanceInventory.md` (guidance-specific spec)
**Goal**: Generalize the guidance extraction pipeline into a reusable framework for ANY extraction type across ALL data assets.

---

## Table of Contents

0. [Current State: Complete Call Chain](#0-current-state-complete-call-chain)
1. [Best Practices Audit](#1-best-practices-audit)
2. [What Works / What Needs Tweaks](#2-what-works--what-needs-tweaks)
3. [Generalization Design](#3-generalization-design)
4. [Per-Data-Asset Application](#4-per-data-asset-application)
5. [Neo4j Schema Design](#5-neo4j-schema-design)
6. [K8s Worker Generalization](#6-k8s-worker-generalization)
7. [Open Questions](#7-open-questions)
8. [Design Decisions Log](#8-design-decisions-log)
9. [Implementation Phases](#9-implementation-phases)

---

## 0. Current State: Complete Call Chain

### Entry Point: `/guidance-transcript`

```
User or SDK:
  /guidance-transcript AAPL transcript AAPL_2025-01-30T17.00 MODE=write

Skill: .claude/skills/guidance-transcript/SKILL.md
  (14 lines — thin orchestrator, spawns 2 agents sequentially)

  ┌─────────────────────────────────────────────────────────────┐
  │ Phase 1: Task(guidance-extract)                             │
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
  │ Phase 2: Task(guidance-qa-enrich)                           │
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

### Complete File Inventory

| Layer | File | Lines | Role |
|-------|------|-------|------|
| **Skill (orchestrator)** | `.claude/skills/guidance-transcript/SKILL.md` | 14 | Thin orchestrator — spawns 2 agents |
| **Agent (Phase 1)** | `.claude/agents/guidance-extract.md` | 285 | PR extraction agent |
| **Agent (Phase 2)** | `.claude/agents/guidance-qa-enrich.md` | 182 | Q&A enrichment agent |
| **Reference (schema)** | `.claude/skills/guidance-inventory/SKILL.md` | 733 | Schema, fields, validation, quality filters |
| **Reference (queries)** | `.claude/skills/guidance-inventory/QUERIES.md` | 755 | 42 Cypher queries |
| **Profile (transcript)** | `guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | 242 | Transcript-specific extraction rules |
| **Profile (8-K)** | `guidance-inventory/reference/PROFILE_8K.md` | 194 | 8-K-specific extraction rules |
| **Profile (news)** | `guidance-inventory/reference/PROFILE_NEWS.md` | 223 | News-specific extraction rules |
| **Profile (10-Q/10-K)** | `guidance-inventory/reference/PROFILE_10Q.md` | 237 | 10-Q/10-K-specific extraction rules |
| **Script (IDs)** | `earnings-orchestrator/scripts/guidance_ids.py` | ~600 | Deterministic IDs, unit canon, period routing |
| **Script (writer)** | `earnings-orchestrator/scripts/guidance_writer.py` | ~400 | Cypher MERGE patterns |
| **Script (CLI)** | `earnings-orchestrator/scripts/guidance_write_cli.py` | ~200 | CLI entry: JSON → IDs → write |
| **Script (shell)** | `earnings-orchestrator/scripts/guidance_write.sh` | 22 | Venv + Neo4j env setup |
| **Trigger** | `scripts/trigger-guidance.py` | 189 | Neo4j query → Redis LPUSH |
| **Worker** | `scripts/earnings_worker.py` | 368 | Redis BRPOP → Claude SDK |
| **NOT loaded** | `.claude/skills/evidence-standards/SKILL.md` | 47 | Anti-hallucination rules (used by data sub-agents, NOT by guidance agents) |
| **Canary** | `scripts/canary_sdk.py` | 235 | K8s deployment validation — tests SDK import, MCP connectivity, skill invocation, dry-run |
| **Separate pipeline** | `scripts/earnings_trigger.py` | 139 | Invokes `/earnings-orchestrator` (prediction + attribution). NOT part of extraction framework. **Status unclear** — shares `earnings:trigger` queue name with `earnings_worker.py`; likely dormant since worker took over that queue. Confirm before queue rename. |
| **Spec (architecture)** | `.claude/plans/guidanceInventory.md` | 1231 | Architecture spec (this plan's parent) |

### Data Flow Diagram

```
                  ┌──────────────┐
                  │ Neo4j Graph  │
                  └──────┬───────┘
                         │ read (MCP)
                         ▼
┌──────────┐    ┌──────────────────┐    ┌───────────────┐
│ guidance │    │  guidance-extract │    │ guidance_ids.py│
│-transcript├──►│  (LLM agent)     ├───►│ (deterministic │
│ (skill)  │    │                  │    │  validation)   │
└──────────┘    └────────┬─────────┘    └───────┬───────┘
      │                  │                      │
      │         ┌────────▼─────────┐    ┌───────▼───────┐
      │         │guidance-qa-enrich│    │guidance_writer │
      │         │  (LLM agent)     ├───►│  (Cypher MERGE)│
      │         └──────────────────┘    └───────┬───────┘
      │                                         │ write
      │                                         ▼
      │                                 ┌──────────────┐
      │                                 │ Neo4j Graph  │
      └─────────────────────────────────┤              │
        (reads via MCP, writes via      │ Guidance     │
         Bash → guidance_writer.py)     │ GuidanceUpdate│
                                        │ GuidancePeriod│
                                        └──────────────┘
```

---

## 1. Best Practices Audit

Comparing current guidance pipeline against `docs/claude/skills-reference.md` checklist.

### Passing

| Rule | Status | Notes |
|------|--------|-------|
| SKILL.md name is lowercase with hyphens | PASS | `guidance-transcript`, `guidance-inventory` |
| Description includes WHAT + WHEN | PASS | Both skills have clear descriptions |
| Progressive disclosure (multi-file) | PASS | SKILL.md → QUERIES.md → PROFILE_*.md |
| References one level deep | PASS | SKILL.md → reference/PROFILE_*.md (no chains) |
| Scripts EXECUTED not READ | PASS | guidance_ids.py, guidance_writer.py run via Bash |
| Deterministic validation via scripts | PASS | All IDs, units, periods computed by Python |
| Feedback loops | PASS | Dry-run → shadow → write progression |
| Low freedom for fragile ops | PASS | Write path is exact scripts, not LLM-generated Cypher |

### Issues Found

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 1 | **SKILL.md > 500 lines** | MEDIUM | `guidance-inventory/SKILL.md` is 733 lines. Reference says < 500. Should extract more to reference files. |
| 2 | **QUERIES.md > 500 lines** | LOW | 755 lines, but this is a reference file, not SKILL.md itself. TOC is present. Acceptable. |
| 3 | **evidence-standards not loaded** | LOW | `guidanceInventory.md` §13 says "Load during extraction" but neither agent's `skills:` or auto-load includes it. Rules ARE duplicated inline in agents (§13 quality filters). Gap is cosmetic — same intent covered. |
| 4 | **No `allowed-tools` on skill** | INFO | `guidance-transcript/SKILL.md` has no `allowed-tools` frontmatter. It's an orchestrator that only spawns Task agents, so tool restriction doesn't apply. |
| 5 | **Model field uses string "opus"** | INFO | Both agents use `model: opus`. Works but `model: claude-opus-4-6` is more explicit per reference. |
| 6 | **`guidance-inventory` SKILL.md has `allowed-tools` + `permissionMode`** | MEDIUM | This is a reference doc auto-loaded by agents, not user-invocable. It has tool/permission config that's irrelevant (agents override with their own frontmatter). Should have `user-invocable: false`. |
| 7 | **Spec-vs-implementation divergence** | LOW | `guidanceInventory.md` (spec) describes `guidance_period_` fiscal-keyed Period namespace, but actual SKILL.md and writer use `gp_` calendar-based GuidancePeriod. Spec is stale on this point (v3.1 of SKILL.md supersedes). |

### Recommendations

1. **Split SKILL.md §9-§11** (Period Resolution, Company+Period, XBRL Matching) into a reference file — these are the most complex sections and are only needed at validation time, not during initial extraction.
2. **Add `user-invocable: false`** to `guidance-inventory/SKILL.md` frontmatter. Remove `allowed-tools`/`permissionMode` (agents set their own).
3. **Archive `guidanceInventory.md`** as historical reference. Working code (SKILL.md, agents, scripts) is source of truth per D1. Don't spend effort reconciling 1,231 lines of partially stale spec.
4. **evidence-standards**: Either formally add to agents' auto-load, or document the intentional gap (inline quality filters serve the same purpose). Prefer adding it — it's 47 lines and prevents drift.

---

## 2. What Works / What Needs Tweaks

### What Works Well (keep as-is)

1. **Two-phase transcript extraction** (PR → Q&A) — elegant. Handles the "Q&A reveals new items" problem cleanly. MERGE+SET idempotency means Phase 2 safely overwrites Phase 1 items.
2. **Thin orchestrator skill** — 14 lines. Spawns agents, reports results. No logic duplication.
3. **Deterministic validation via scripts** — no LLM math. IDs, units, periods all computed by Python with 169 tests.
4. **Per-source profiles** — clean separation. Adding a new source type = add one PROFILE_*.md file.
5. **Write path isolation** — agents can't write to Neo4j directly. All writes go through `guidance_write.sh` → `guidance_writer.py`. Defense in depth.
6. **K8s worker** — battle-tested. Graceful shutdown, re-queue, retry, dead-letter. Status tracking on Transcript nodes.
7. **Slot-based dedup** — deterministic IDs prevent duplicates across reruns. Latest write wins.

### Known Tweaks Needed (user mentioned)

1. **FOR_COMPANY edge** — DECIDED: KEEP. Direct O(1) lookup worth the minor redundancy. See §5.
2. **Other extraction types** — pipeline is guidance-specific. Need to identify what's reusable vs type-specific.
3. **Trigger generalization** — `trigger-guidance.py` only handles Transcripts. Needs to route to different data assets and extraction types.

### Quality Observations from Real Runs — PRE-PHASE-1 GATE

**Must be populated before Phase 1 starts.** Run current `/guidance-transcript` on a reference set of 5+ transcripts, record golden check values (below), and note any user-specified quality tweaks. This is the baseline that Phase 1.4 diffs against. Cannot be filled during planning — requires actual pipeline execution.

### Golden Checks (Phase 1.4 validation criteria)

Any reorganization MUST produce identical output. "Identical" means ALL of the following pass:

1. **Same GuidanceUpdate IDs** — deterministic slot-based IDs must match exactly
2. **Same key field values** — low/mid/high, basis, period, derivation_type, unit, segment, quote
3. **Same relationship edge counts** — FROM_SOURCE, FOR_COMPANY, HAS_PERIOD edges per source
4. **Idempotent rerun** — run the same transcript twice, zero new nodes created (MERGE idempotency)
5. **Same error taxonomy** — SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_GUIDANCE outcomes unchanged

These criteria are the yardstick for Phase 1.4 and Phase 3.5 validation gates.

---

## 3. Generalization Design

### The Core Insight

The guidance pipeline is really a **structured extraction pipeline** with these layers:

```
Layer 1: ORCHESTRATOR (thin skill)
  What to extract (extraction type) + What to extract FROM (data asset)
  → spawns agent(s)

Layer 2: EXTRACTION AGENT (LLM + rules)
  Reads source content → applies extraction rules → produces structured items
  - Reads: source content queries (QUERIES.md)
  - Applies: extraction-type rules (SKILL.md) + source-type rules (PROFILE_*.md)
  - Produces: JSON items with typed fields

Layer 3: VALIDATION + WRITE (deterministic scripts)
  Validates items → computes IDs → writes to Neo4j
  - IDs: deterministic, slot-based
  - Write: MERGE + SET (idempotent)
```

### What Varies by Extraction Type

| Component | Guidance | Future: Analyst Comments | Future: Risk Factors |
|-----------|----------|-------------------------|---------------------|
| **Node labels** | Guidance, GuidanceUpdate | TBD | TBD |
| **Extraction fields** | 20 fields (low/mid/high, basis, derivation...) | Different field set | Different field set |
| **Quality filters** | Forward-looking, no fabrication, quote max 500 | Different filters | Different filters |
| **ID structure** | `gu:{source}:{label}:{period}:{basis}:{segment}` | Different slot components | Different slot components |
| **XBRL matching** | Concept + Member caches | Probably not applicable | Not applicable |
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

### What's Shared (Extraction-Type-Agnostic)

1. **Orchestrator pattern**: Thin skill → spawn agent(s) via Task tool
2. **Agent structure**: Auto-load 3 files → Load context → Fetch content → LLM extract → Validate → Write
3. **Context loading**: Company+CIK (1A), FYE (1B) — always needed
4. **Source fetch queries**: QUERIES.md — already organized by asset type
5. **Write path**: JSON → shell wrapper → CLI → writer → Neo4j MERGE
6. **K8s trigger + worker**: Redis queue → SDK invocation → status tracking
7. **Execution modes**: dry_run / shadow / write
8. **Error taxonomy**: SOURCE_NOT_FOUND, EMPTY_CONTENT, NO_GUIDANCE, etc.

### Proposed Architecture

**Key principle**: Orchestrators are **per-asset** (one per data source type). Each orchestrator spawns **per-type agents** (one focused agent per extraction type). This preserves quality by keeping each agent focused on a single extraction contract, while sharing all infrastructure.

```
                    ┌──────────────────────────────────────────────┐
                    │           EXTRACTION FRAMEWORK                │
                    │                                              │
                    │  Orchestrator Skills (thin, per-asset):      │
                    │    /extract-transcript                        │
                    │    /extract-8k                                │
                    │    /extract-news                              │
                    │    /extract-10q                               │
                    │                                              │
                    │  Each spawns N per-type agents:               │
                    │    /extract-transcript                        │
                    │      ├── Task(guidance-extract)               │
                    │      ├── Task(guidance-qa-enrich)  [opt-in]   │
                    │      ├── Task(analyst-extract)     [future]   │
                    │      └── Task(announcement-extract) [future]  │
                    │                                              │
                    │    /extract-8k                                │
                    │      ├── Task(guidance-extract)               │
                    │      └── Task(analyst-extract)     [future]   │
                    └────────────┬─────────────────────────────────┘
                                 │ each agent auto-loads
                    ┌────────────▼─────────────────────────────────┐
                    │           REFERENCE LAYER                     │
                    │                                              │
                    │  Shared across ALL extraction types:          │
                    │    QUERIES.md (source fetch)                  │
                    │    evidence-standards (anti-hallucination)    │
                    │    PROFILE_TRANSCRIPT.md (per data-asset)    │
                    │    PROFILE_8K.md                              │
                    │    PROFILE_NEWS.md                            │
                    │    PROFILE_10Q.md                             │
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
                    │  Shared:                                      │
                    │    extraction_write.sh (venv + env setup)     │
                    └──────────────────────────────────────────────┘
```

**Why per-type agents, not single-pass multi-type?** The current guidance agent loads ~1,730 lines of instructions and achieves near-optimal output because it is 100% focused on one job. Loading multiple extraction contracts into a single LLM pass dilutes attention, risks cross-contamination between extraction rules, and directly violates the baseline lock. Per-type agents share all infrastructure (queries, profiles, write path) but each reads only ONE contract. Single-pass may be explored as a future optimization after quality parity is proven via A/B comparison.

### Orchestrator ↔ Agent Routing

The orchestrator receives a `TYPES` list from the worker payload (e.g., `TYPES=guidance` or `TYPES=guidance,analyst`). It only spawns agents for the specified types.

```
Trigger: --type guidance --asset transcript
  → queries WHERE t.guidance_status IS NULL
  → payload: {asset: "transcript", ticker, source_ids, types: ["guidance"], mode}

Worker: reads payload, invokes /extract-transcript AAPL ... TYPES=guidance MODE=write

Orchestrator (/extract-transcript): reads TYPES from prompt
  → if "guidance" in TYPES: spawn Task(guidance-extract), then Task(guidance-qa-enrich)
  → if "analyst" in TYPES: spawn Task(analyst-extract)  [future]

Agent (safety guard): checks {type}_status on source node before doing work
  → if already "completed": exit immediately (defense-in-depth, idempotent)
```

**TYPES required**: If TYPES is missing from the prompt, the orchestrator MUST fail with an explicit error. No default-to-all guessing. The worker always passes TYPES from the payload (mandatory field).

For historical backfill: `trigger-extract.py --type all --asset transcript` → `types: ["guidance", "analyst"]`.

### Error Isolation / Partial Success

When an orchestrator spawns multiple per-type agents, some may succeed and others fail. Each type's results are independent — guidance writes persist regardless of analyst failure.

**Mechanism**: The orchestrator emits a structured summary line in its final output:
```
EXTRACTION_RESULTS: guidance=completed, analyst=failed
```

The worker parses this and marks `{type}_status` per-type independently:
- `SET t.guidance_status = 'completed'`
- `SET t.analyst_status = 'failed'`

**Fallback**: If the orchestrator crashes entirely (no result), the worker marks ALL types in the payload as `failed`. The trigger's `--retry-failed` flag re-runs only the failed types.

This keeps all status marking centralized in the worker (one mechanism, one Neo4j connection). The orchestrator just reports outcomes.

### PROFILE Dynamic Loading (Already Solved)

The `guidance-extract.md` agent already routes to the correct PROFILE by `SOURCE_TYPE` parameter (lines 31-35 of agent file). The agent receives SOURCE_TYPE in its prompt, reads the matching PROFILE from a known directory. When profiles move to the shared location, we update 4 paths in the agent file. No new mechanism needed.

### Key Design Principle: Profile Files Are Asset-Specific, NOT Type-Specific

Currently PROFILE_TRANSCRIPT.md is inside `guidance-inventory/reference/`. But transcript scan scope (speakers, PR vs Q&A, fallback queries) is the SAME regardless of whether you're extracting guidance, analyst comments, or risk factors from that transcript.

**Decision**: Move PROFILE_*.md files to `.claude/skills/extraction-profiles/reference/`. Each profile describes HOW to read the asset, not WHAT to extract. The extraction-type SKILL.md describes WHAT to extract.

**Current state**: The profiles are 80% asset-generic + 20% guidance-specific (e.g., "What to Extract" tables that mention guidance derivation types).

**Implementation approach**: Keep each PROFILE as a **single file** with clearly marked sections rather than splitting into separate files. This avoids doubling the file count (4→8) and keeps all knowledge about one asset co-located:
- `## Asset Structure` — data structure, scan scope, speaker hierarchy, content fetch order, fallback queries, empty content handling, period identification patterns *(shared across all extraction types)*
- `## Extraction Rules: Guidance` — "What to Extract" tables, derivation hints, quote prefix conventions *(guidance-specific)*
- `## Extraction Rules: Analyst` — *(future, appended when needed)*

Each extraction agent loads the full PROFILE but its contract tells it which `Extraction Rules` section is relevant. Adding a new extraction type = append a new section to the existing PROFILE files.

### How Adding a New Extraction Type Would Work

1. Create `{type}-inventory/SKILL.md` — schema, fields, validation rules (like `guidance-inventory/SKILL.md`)
2. Create `{type}_ids.py` — deterministic ID computation (like `guidance_ids.py`)
3. Create `{type}_writer.py` — Cypher MERGE patterns (like `guidance_writer.py`)
4. Create agent: `.claude/agents/{type}-extract.md` — references SKILL.md + QUERIES.md + PROFILE_*.md
5. Append `## Extraction Rules: {type}` section to each applicable PROFILE_*.md file
6. Add `Task({type}-extract)` spawn to each per-asset orchestrator that applies
7. Add `{type}_status` property to trigger script's query + worker's `mark_status()`

Steps 1-3 are the substantive work. Steps 4-7 are boilerplate that follows the pattern.

### How Adding a New Data Asset Would Work

1. Add queries to QUERIES.md (or create a separate QUERIES_{asset}.md)
2. Create PROFILE_{asset}.md — data structure, scan scope, empty handling
3. Existing extraction agents auto-detect via `SOURCE_TYPE` routing
4. Extend trigger to query for unprocessed items of the new asset type

---

## 4. Per-Data-Asset Application

### Transcripts — Current State (Near-Ideal)

- **Current orchestrator**: `/guidance-transcript` (14 lines) — will be replaced by `/extract-transcript`
- **Agents**: `guidance-extract` + `guidance-qa-enrich`
- **Status**: Production-ready, triggered via K8s worker
- **Remaining tweaks**: User will specify later
- **Generalization notes**: Two-phase pattern (PR → Q&A enrichment) is transcript-specific. Other assets don't need it.
- **Migration**: Build `/extract-transcript` → validate identical output → retire `/guidance-transcript`

### 8-K — Current State

- **No dedicated orchestrator** — currently invoked via `guidance-extract` agent directly
- **No K8s trigger** — `trigger-guidance.py` only queries Transcripts
- **Agent coverage**: `guidance-extract` already handles 8-K via PROFILE_8K.md routing
- **What needs work**:
  - Per-asset orchestrator: `/extract-8k`
  - Trigger extension: query Reports with formType='8-K' + `guidance_status`
  - Status tracking: add `guidance_status` property to Report nodes

### 10-Q / 10-K — Current State

- **Same as 8-K** — no dedicated orchestrator or trigger
- **Agent coverage**: `guidance-extract` handles via PROFILE_10Q.md
- **What needs work**: Same as 8-K (per-asset orchestrator: `/extract-10q`)

### News — Current State

- **Same as 8-K** — no dedicated orchestrator or trigger
- **Agent coverage**: `guidance-extract` handles via PROFILE_NEWS.md
- **Special**: Channel pre-filter (Benzinga channels) before LLM processing
- **What needs work**: Same as 8-K (per-asset orchestrator: `/extract-news`), plus channel filter is guidance-specific and would differ for other extraction types

### Report Blanket Group (Other Filing Types)

- **Not yet in pipeline** — DEF 14A (proxy), S-1, 8-K non-earnings items, etc.
- **Low priority** — these rarely contain structured guidance
- **Design**: Same PROFILE pattern. Add PROFILE_OTHER.md when needed.

---

## 5. Neo4j Schema Design

### FOR_COMPANY Edge — DECIDED: KEEP

**Decision**: Keep `(GuidanceUpdate)-[:FOR_COMPANY]->(Company)`. All future extraction types follow the same pattern.

**Why**: Direct O(1) company lookup, simpler Cypher (no multi-hop through heterogeneous source nodes), index-backed. The minor redundancy (company derivable via FROM_SOURCE path) and extra MERGE per write are trivial costs. See D5 for full pros/cons analysis.

### Node Type Design: Separate vs Generic

This remains an open question (user said "not sure yet"). Here's the analysis:

#### Option A: Separate Node Types (Recommended)

```
(:Guidance {id, label, aliases})            — metric tag
(:GuidanceUpdate {id, 20 fields...})        — per-mention data point
(:AnalystEstimate {id, different fields})   — future
(:RiskFactor {id, different fields})        — future
```

**Pros**: Type-safe properties. Clear schema. Type-specific indexes. No "null column" bloat.
**Cons**: More node types to manage. Each needs its own writer.

#### Option B: Generic Extraction Node

```
(:Extraction {id, type: "guidance"|"analyst"|"risk", shared fields...})
(:ExtractionUpdate {id, type: "guidance"|"analyst"|"risk", union of all fields...})
```

**Pros**: One writer, one schema, one set of queries.
**Cons**: Property bloat (guidance needs `low/mid/high`, risk factors don't). Queries need `WHERE type = ...` everywhere. Loses schema clarity.

#### Option C: Hybrid (Label + Base Properties)

```
(:GuidanceUpdate:ExtractionUpdate {id, shared fields + type-specific fields})
(:AnalystEstimate:ExtractionUpdate {id, shared fields + type-specific fields})
```

Neo4j multi-label. Shared `ExtractionUpdate` label enables cross-type queries. Type-specific label enables type-specific indexes and queries.

**Pros**: Best of both worlds. `MATCH (eu:ExtractionUpdate)-[:FOR_COMPANY]->(c)` for cross-type. `MATCH (gu:GuidanceUpdate)` for type-specific.
**Cons**: Multi-label can be confusing. Need to be careful with constraints.

#### Decision: DEFERRED

Will decide after identifying concrete extraction types from the data asset deep dive. The pipeline design works regardless of which option is chosen — the writer is extraction-type-specific anyway.

---

## 6. K8s Worker Generalization

### Current State

```
trigger-guidance.py → Redis "earnings:trigger" → earnings_worker.py
  → Claude SDK: /guidance-transcript {ticker} transcript {sid} MODE={mode}
```

Hardcoded to: Transcripts only, guidance only, single queue.

### Decided Design: Single Queue, Payload-Driven

```
trigger-extract.py (replaces trigger-guidance.py)
  --type guidance|analyst|all
  --asset transcript|8k|10q|10k|news|all
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

**Worker** (`extraction_worker.py`, replaces `earnings_worker.py`):
```
1. BRPOP from "extract:pipeline"
2. Parse payload → compute skill: /extract-{asset}
3. For each source_id:
   a. mark_status(in_progress) for each type in types
   b. Claude SDK: query("/extract-{asset} {ticker} {source_id} TYPES={types} MODE={mode}")
   c. Parse EXTRACTION_RESULTS from orchestrator output (see §3 Error Isolation)
   d. mark_status(completed|failed) PER TYPE based on parsed results
   e. Fallback: if no result / crash → mark ALL types as failed
4. On shutdown: re-queue remaining
5. On failure: retry up to 3x, then dead-letter
```

**Status tracking** (per D6): Per-type simple properties on source nodes (`guidance_status`, `analyst_status`, etc.). Native Neo4j indexes, zero APOC dependency.

### Trigger → Worker → Orchestrator Flow

| Current | Generalized |
|---------|-------------|
| `find_unprocessed()` queries Transcripts only | Query ANY source node type by `{type}_status` |
| Groups by ticker | Same — ticker batching is universal |
| Redis queue `earnings:trigger` | Single queue `extract:pipeline` |
| Payload: `{ticker, source_ids, mode}` | `{asset, ticker, source_ids, types, mode}` |
| Invokes `/guidance-transcript` | Invokes `/extract-{asset}` (from payload) |
| `mark_status()` sets `guidance_status` | Sets `{type}_status` for each type in payload |

### K8s Files That Need Changes

| File | Change |
|------|--------|
| `scripts/earnings_worker.py` → `scripts/extraction_worker.py` | Generalize payload parsing, skill routing, status tracking |
| `scripts/trigger-guidance.py` → `scripts/trigger-extract.py` | Add `--type`/`--asset` flags, generalize Neo4j query, new queue name |
| `k8s/processing/claude-code-worker.yaml` | Update queue name in KEDA trigger, update script path |
| `scripts/canary_sdk.py` | Update to validate generalized worker (new skill name, new payload format) |
| `earnings_trigger.py` | **Status unclear** — shares old queue name; confirm dormant before queue rename |

---

## 7. Open Questions

### Decided

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 1 | Profile files: shared or per-type? | **DECIDED: SHARED** | Single file per asset with marked sections. See D2. |
| 2 | Per-asset orchestrators or per-type? | **DECIDED: PER-ASSET** | Orchestrators per-asset, agents per-type. See D3. |
| 3 | Single-pass or per-type agents? | **DECIDED: PER-TYPE** | Quality > cost. Baseline lock. See D3. |
| 4 | Two-phase (PR → Q&A): transcript-only? | **DECIDED: YES** | Other assets single-pass. Enrichment opt-in. See D4. |
| 5 | Keep FOR_COMPANY edge? | **DECIDED: YES** | See §5. |
| 6 | XBRL matching: guidance-only? | **DECIDED: YES** | XBRL = financial metrics, not analyst sentiment or risk factors |
| 7 | Status tracking: per-type properties or JSON? | **DECIDED: PER-TYPE PROPERTIES** | Native indexing, zero APOC. See D6. |
| 8 | QUERIES.md: one file or split? | **DECIDED: ONE** | 755 lines with TOC works. Revisit if >1000. |
| 9 | Trigger: one script or per-type? | **DECIDED: ONE** | `trigger-extract.py --type --asset`. See §6. |
| 10 | Worker: one or per-type? | **DECIDED: ONE** | Single queue, payload-driven. See §6. |
| 11 | Queue: multi or single? | **DECIDED: SINGLE** | `extract:pipeline`. See §6. |
| 12 | evidence-standards: add to agents? | **DECIDED: YES** | 47 lines, prevents drift. |
| 13 | PROFILE dynamic loading mechanism? | **DECIDED: ALREADY WORKS** | Agent reads correct PROFILE by SOURCE_TYPE. See §3. |
| 14a | Error isolation between extraction types? | **DECIDED: PER-TYPE ISOLATION** | Each agent writes independently. Orchestrator reports per-type results. Worker marks per-type status. See §3. |
| 14b | TYPES omitted from prompt? | **DECIDED: FAIL** | Orchestrator errors if TYPES missing. No default-to-all. Worker always passes TYPES. |

### Open

| # | Question | Status | Notes |
|---|----------|--------|-------|
| 15 | Separate vs generic node types | DEFERRED → **DECIDED: SEPARATE (Option A)** | Each type gets its own label pair following the tag+data-point pattern (e.g., `Guidance`+`GuidanceUpdate`, future `AnalystTopic`+`AnalystComment`). Writers are per-type so this is non-blocking. |
| 16 | GuidancePeriod: share with other types? | DEFERRED | See D7. Decide with first non-guidance type. |
| 17 | Specific output quality issues with guidance-transcript | PENDING | User will specify. Baseline established from pipeline code + Neo4j data review. |
| 18 | Extraction types beyond guidance | PENDING | Focus on infra first. Guidance is gold standard. New types added when ready. |
| 19 | Budget/cost optimization for K8s runs | OPEN | |
| 20 | `earnings_trigger.py` status | PENDING | Shares `earnings:trigger` queue. Confirm dormant before queue rename. |

---

## 8. Design Decisions Log

Quick-reference index. Full rationale in the referenced sections.

| ID | Decision | Details |
|----|----------|---------|
| D1 | **Contract-driven framework** — each extraction type defined by a contract (fields, quality filters, ID formula, writer config). Source of truth = working code, not stale spec. | §3 |
| D2 | **PROFILE: single file per asset** with marked sections (`## Asset Structure` shared, `## Extraction Rules: {type}` per-type). Move to `.claude/skills/extraction-profiles/reference/`. | §3 |
| D3 | **Per-type agents, per-asset orchestrators.** NOT single-pass. Each agent loads ONE contract, stays 100% focused. Baseline lock preserved. | §3 |
| D4 | **Enrichment is opt-in**, not standard phase. Each contract declares if it needs enrichment and for which assets. Currently only guidance+transcript uses it. | §3 |
| D5 | **news-driver pipeline: 100% separate.** Attribution/analysis workflow, not extraction. Different architecture entirely. | — |
| D6 | **Per-type status properties** (`guidance_status`, `analyst_status`). NOT JSON map. Native indexing, zero APOC, existing code unchanged. | §6 |
| D7 | **GuidancePeriod: DEFERRED.** Calendar-based `gp_` format is inherently general. Decide rename to `CalendarPeriod` when first non-guidance type needs periods. | §7 Q16 |
| D8 | **File inventory corrections** — `canary_sdk.py` (deployment validation), `earnings_trigger.py` (separate pipeline, status unclear). Both added to §0. | §0 |

### FOR_COMPANY Edge — Full Analysis (§5 reference, preserved for context)

**Current**: `(GuidanceUpdate)-[:FOR_COMPANY]->(Company)`

| Pros | Cons |
|------|------|
| O(1) company lookup, index-backed | Redundant (derivable from source) |
| Simpler Cypher — no multi-hop traversal | Extra MERGE per write (trivial) |
| Cross-source queries without knowing source types | Consistency risk if source changes company (theoretical) |
| Schema clarity — explicit relationship | |

**Decision**: KEEP. All future extraction types follow the same pattern.

### D6: Status Tracking — Full Analysis (preserved for reference)

| Concern | Per-type properties (DECIDED) | JSON map (rejected) |
|---------|-------------------------------|---------------------|
| **Indexing** | Native Neo4j index | Cannot index sub-fields |
| **Query** | `WHERE t.guidance_status IS NULL` | `apoc.convert.fromJsonMap(...)` |
| **Dependencies** | Zero — native Cypher | Requires APOC |
| **Update** | `SET t.analyst_status = 'completed'` | Read → parse → modify → serialize → write |
| **Existing code** | Works unchanged | Requires rewrite |

Neo4j is schema-free — adding a property is trivial. No migration needed for existing `guidance_status`.

---

## 9. Implementation Phases

Each phase has a validation gate. No phase starts until the previous gate passes.

### Phase 1: Infrastructure Migration (zero behavior change)

Move files and create the per-asset orchestrator. Guidance output MUST be identical before and after.

**Files in scope:**

| File | Change |
|------|--------|
| `guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | Move → `extraction-profiles/reference/` |
| `guidance-inventory/reference/PROFILE_8K.md` | Move → `extraction-profiles/reference/` |
| `guidance-inventory/reference/PROFILE_NEWS.md` | Move → `extraction-profiles/reference/` |
| `guidance-inventory/reference/PROFILE_10Q.md` | Move → `extraction-profiles/reference/` |
| `.claude/agents/guidance-extract.md` | Update 4 PROFILE paths |
| `.claude/skills/extract-transcript/SKILL.md` | **New** — clones `guidance-transcript/SKILL.md` |
| `.claude/skills/guidance-transcript/SKILL.md` | Retired after validation |

| Step | Action | Validation |
|------|--------|------------|
| 1.1 | Move PROFILE_*.md → `.claude/skills/extraction-profiles/reference/` | Agent can still read profiles by SOURCE_TYPE |
| 1.2 | Update paths in `guidance-extract.md` (4 lines) | Dry-run on 1 transcript, compare output |
| 1.3 | Create `/extract-transcript` orchestrator skill (clone of `/guidance-transcript` — no TYPES support yet, that's Phase 3) | Spawns same agents as `/guidance-transcript` |
| 1.4 | **Baseline validation**: Run `/extract-transcript` on 5+ transcripts, diff output against `/guidance-transcript` | Golden checks pass (§2): same IDs, same fields, same edges, idempotent |
| 1.5 | **Canary validation**: Run `canary_sdk.py` with new skill name | Canary green |
| 1.6 | Retire `/guidance-transcript` | Only after 1.4 + 1.5 pass |

### Phase 2: Best Practices Cleanup

| Step | Action | Validation |
|------|--------|------------|
| 2.1 | Split SKILL.md §9-§11 into reference file (get under 500 lines) | Agent still loads all needed content |
| 2.2 | Add `evidence-standards` to agent auto-load | 47 lines, no behavior change |
| 2.3 | Add `user-invocable: false` to `guidance-inventory/SKILL.md` | |
| 2.4 | Archive `guidanceInventory.md` as historical reference (per D1: working code is source of truth) | |

### Phase 3: Generalize Trigger + Worker

| Step | Action | Validation |
|------|--------|------------|
| 3.1 | Create `trigger-extract.py` (from `trigger-guidance.py`) | `--type guidance --asset transcript` produces identical queue payloads |
| 3.2 | Create `extraction_worker.py` (from `earnings_worker.py`) | Reads new payload format, invokes `/extract-transcript` |
| 3.3 | Rename queue: `earnings:trigger` → `extract:pipeline` | Update KEDA config |
| 3.4 | Update `canary_sdk.py` for new skill/payload | |
| 3.5 | **End-to-end K8s validation**: trigger → queue → worker → `/extract-transcript` → Neo4j | Identical to current pipeline |
| 3.6 | Confirm `earnings_trigger.py` status before final queue rename | |

### Phase 4: Expand to Other Data Assets (guidance extraction)

| Step | Action | Validation |
|------|--------|------------|
| 4.1 | Create `/extract-8k` orchestrator | Spawns `guidance-extract` with SOURCE_TYPE=8k |
| 4.2 | Add `guidance_status` property to Report nodes | Trigger can find unprocessed 8-Ks |
| 4.3 | Extend `trigger-extract.py`: `--asset 8k` | Query Reports with formType='8-K' |
| 4.4 | Repeat for 10-Q, News | |

### Phase 5: First Non-Guidance Extraction Type (future)

| Step | Action | Validation |
|------|--------|------------|
| 5.1 | Choose extraction type (analyst? announcement?) | |
| 5.2 | Design contract: fields, quality filters, ID formula | |
| 5.3 | Decide node type (§5 — currently deferred) | |
| 5.4 | Create `{type}_ids.py`, `{type}_writer.py`, `{type}-extract.md` | |
| 5.5 | Append `## Extraction Rules: {type}` to PROFILE files | |
| 5.6 | Add `Task({type}-extract)` to per-asset orchestrators | |
| 5.7 | Add `{type}_status` to trigger query | |
| 5.8 | Define contract template for future types | |

### Quality Baseline (§2)

Before Phase 1 starts, establish the baseline by running current `/guidance-transcript` on a reference set and recording golden check values (§2). Phase 1.4 diffs new output against this baseline.

---

*v0.4 | 2026-03-04 | Cross-bot review: fixed FOR_PERIOD→HAS_PERIOD (verified against guidance_writer.py:182), fixed D5 ID collision, fixed stale FOR_COMPANY ref in §2, changed guidanceInventory.md from "reconcile" to "archive" (per D1), added Phase 1 TYPES sequencing note, Quality Observations now explicit pre-Phase-1 gate. Q15 DECIDED: separate label pairs.*
