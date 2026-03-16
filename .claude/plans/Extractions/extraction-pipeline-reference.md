# Extraction Pipeline v3.5 — Architecture, Design & Roadmap

> Single reference for architecture, design reasoning, validated results, and open work.
> Replaces 14 prior plan files. Source of truth: implementation code.
> Consolidation date: 2026-03-09.

**Live type**: `guidance`. **Assets**: `transcript`, `8k`, `10q`, `10k`, `news`.
Treat this file as the authoritative reference for this folder.

---

## Source Of Truth

Use code first:

- Runtime: `scripts/trigger-extract.py`, `scripts/extraction_worker.py`, `k8s/processing/extraction-worker.yaml`
- Orchestrator: `.claude/skills/extract/SKILL.md`
- Generic agents: `.claude/agents/extraction-primary-agent.md`, `.claude/agents/extraction-enrichment-agent.md`
- Active prompt stack: `.claude/skills/extract/assets/*`, `.claude/skills/extract/types/guidance/*`, `.claude/skills/extract/queries-common.md`, `.claude/skills/extract/evidence-standards.md`
- Deterministic validation/write path: `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py`, `guidance_write_cli.py`, `guidance_writer.py`, `guidance_write.sh`, `concept_resolver.py`
- Warmup helpers: `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py`, `warmup_cache.sh`
- Global hooks/guardrails: `.claude/settings.json`

Legacy guidance files still exist elsewhere in the repo, but they are not the source of truth for the current generic extraction pipeline.

---

## 1. Guiding Principles (Invariants)

Non-negotiable for any future work on this pipeline. A bot rebuilding or extending this system MUST follow all of these.

1. **NO CONTAGION** — Each extraction type lives entirely in `types/{TYPE}/` + intersection files. Asset profiles, pass briefs, common queries contain zero type-specific content. Prevents bias when a new type reuses the same asset.
2. **CONTENT RELOCATION, NEVER DELETION** — Removing content from a shared file? It MUST be relocated to the scoped file the same agent already loads. Never just delete.
3. **FILESYSTEM IS THE REGISTRY FOR TYPES AND PASSES** — Path convention (`types/{TYPE}/core-contract.md`, `types/{TYPE}/assets/{ASSET}-{pass}.md`) drives type discovery and enrichment gating. Assets still require runtime registration in `ASSET_QUERIES` and `ASSET_LABELS`.
4. **GENERIC RUNTIME** — Worker, trigger, orchestrator, and agent shells are type-agnostic. Adding a new extraction type requires zero runtime code changes, but it still requires type-owned prompt files and type-owned writer scripts.
5. **DETERMINISTIC IDS** — No UUIDs, no sequences. All writes use MERGE on computed IDs (e.g., `gu:{source_id}:{label_slug}:{period_u_id}:{basis_norm}:{segment_slug}`). Idempotent by construction.
6. **SCRIPTS FOR DETERMINISM** — All ID computation, unit canonicalization, period routing, and graph writes go through deterministic Python scripts, typically invoked via Bash wrappers. Agents never compute IDs or canonicalize values manually.
7. **AGENT ISOLATION** — Each agent sees ONLY its own pass-relevant content via the 8-slot protocol. No cross-agent state sharing except through the graph.
8. **EVIDENCE-FIRST** — No evidence = no item. No guesses. Quotes required for every extracted item.
9. **RECALL OVER PRECISION** — When in doubt, extract. False positives are cheaper than missed guidance. 6 quality filters applied post-extraction: forward-looking, specificity required, no fabricated numbers, quote max 500 chars, 100% recall priority, factors are conditions not items.
10. **3-AXIS DECOMPOSITION** — TYPE x ASSET x PASS. TYPE = what to extract, ASSET = where to look, PASS = extraction phase. Each axis independently extensible. PASS is subordinate to TYPE (each type defines its own passes).
11. **BOUNDARY RULES** — Asset files describe HOW to read data, not WHAT to extract. Pass briefs describe the generic workflow, not asset-specific rules. Intersection files bridge both — asset-specific rules FOR a specific type.
12. **SUPER MINIMALISM** — No premature abstractions. Per-type scripts until >50% overlap proves shared abstraction. Optional intersection files. Single queue.
13. **ONE JOB = ONE {TYPE, ASSET, SOURCE_ID}** — Atomic processing unit. No multi-source batching.

---

## 2. Architecture

### 2.1. Data Flow

```
trigger-extract.py → Redis LPUSH (extract:pipeline) → KEDA auto-scale (1→7 pods)
  → extraction_worker.py (async BRPOP listener)
    → Claude Agent SDK (bypassPermissions, MAX_TURNS=80, $5 budget)
      → /extract skill (SKILL.md orchestrator)
        ├─→ extraction-primary-agent  (8 files loaded → primary-pass.md workflow)
        └─→ extraction-enrichment-agent (conditional → enrichment-pass.md workflow)
      → Neo4j writes (via guidance_write.sh, deterministic MERGE)
      → Status property set on source node ({type}_status = completed|failed)
```

**Design**: Generic runtime (never changes) + specialized prompt packets (per-type instructions).

**Dynamic type discovery**: Both worker and trigger scan `types/*/` for directories containing the 3 required files (`core-contract.md`, `primary-pass.md`, `{type}-queries.md`). No hardcoded type list.

### 2.2. 8-Slot Agent Load Order

Both agent shells load exactly 8 instruction files before execution:

| Slot | File | Scope | Purpose |
|------|------|-------|---------|
| 1 | `types/{TYPE}/core-contract.md` | Type | Full schema: fields, enums, ID rules, quality filters, error taxonomy |
| 2 | `types/{TYPE}/primary-pass.md` or `enrichment-pass.md` | Type+Pass | Working brief — follow start to finish |
| 3 | `assets/{ASSET}.md` | Asset | Data structure: node labels, properties, content layers, fetch order |
| 4 | `types/{TYPE}/assets/{ASSET}-{pass}.md` | Type+Asset+Pass | Intersection rules (**optional** — skip if absent) |
| 5 | `queries-common.md` | Global | Shared Cypher: context (1A–1D), warmup caches (2A–2B), inventory (8A), fulltext (9A–9F) |
| 6 | `assets/{ASSET}-queries.md` | Asset | Asset-specific content fetch queries |
| 7 | `types/{TYPE}/{TYPE}-queries.md` | Type | Type-specific lookup queries |
| 8 | `evidence-standards.md` | Global | 4 universal anti-hallucination guardrails |

**Slot 4 is the key innovation**: it bridges type-specific extraction rules with asset-specific data structure without contaminating either. Missing slot 4 files are silently skipped.

### 2.3. Enrichment Gate

Orchestrator runs enrichment ONLY IF both files exist on disk:
1. `types/{TYPE}/enrichment-pass.md`
2. `types/{TYPE}/assets/{ASSET}-enrichment.md`

Currently only `guidance` × `transcript` has enrichment (Q&A secondary content). All other asset types are single-pass. Enrichment verdicts: **ENRICHES** {item} | **NEW ITEM** | **NO GUIDANCE**.

### 2.4. Result Protocol

- Agents write JSON to `/tmp/extract_pass_{TYPE}_{pass}_{SOURCE_ID}.json`
- Worker reads back and parses result file
- File-based transfer avoids SDK output parsing issues with large payloads

### 2.5. Status & Retry

- Worker sets `{type}_status` property on source node (`in_progress` → `completed`|`failed`)
- Each type has independent status — multiple types can process the same source independently
- Dead-letter queue: `extract:pipeline:dead` after 3 retries
- Trigger skips completed sources (overridable with `--force`)

### 2.6. K8s Deployment

- **Pod**: `extraction-worker` in `processing` namespace on `minisforum` node
- **Scaling**: KEDA ScaledObject — min 1, max 7 pods, 300s cooldown, Redis list trigger
- **Termination**: 300s grace period (in-flight extraction completes)
- **Auth**: 1-year refresh token via `setup-token`, auto-rotates

### 2.7. Model Configuration

**Current production model: Sonnet 4.6** (validated 2026-03-15)

Model is configured per type×asset via `config.yaml` with 3 independently controllable roles:

| Role | What it controls | How it's set |
|------|-----------------|--------------|
| `orchestrator` | `/extract` skill session (SKILL.md) | `ClaudeAgentOptions(model=)` from config |
| `primary` | extraction-primary-agent | Agent tool `model=` param (overrides frontmatter) |
| `enrichment` | extraction-enrichment-agent | Agent tool `model=` param (overrides frontmatter) |

**Config file**: `types/{TYPE}/config.yaml` — one per extraction type, auto-loaded by worker.

```yaml
# types/guidance/config.yaml
orchestrator: sonnet        # default for all assets
primary: sonnet
enrichment: sonnet

assets:                     # per-asset overrides (inherit from defaults)
  news:
    orchestrator: haiku
    primary: haiku
  # transcript inherits defaults (sonnet/sonnet/sonnet)
```

**Resolution order**: asset override > type default > hardcoded fallback (`sonnet`).

**How it works**:
1. Worker reads `types/{TYPE}/config.yaml` via `load_type_config()`
2. `resolve_models(config, asset)` merges defaults with asset overrides
3. Orchestrator model → `ClaudeAgentOptions(model=)`
4. Agent models → passed as `PRIMARY_MODEL=` / `ENRICHMENT_MODEL=` in prompt args
5. SKILL.md passes `model={PRIMARY_MODEL}` to Agent tool, overriding agent frontmatter

**Verified 2026-03-15**: Same pod processed guidance/news (haiku) and guidance/transcript (sonnet) simultaneously. Worker log confirmed: `Model config for guidance/news: orchestrator=haiku primary=haiku enrichment=sonnet` and `Model config for guidance/transcript: orchestrator=sonnet primary=sonnet enrichment=sonnet`. All 36 news SDK messages showed `model=claude-haiku-4-5-20251001`, all transcript messages showed `model=claude-sonnet-4-6`.

**Agent frontmatter** (`model: sonnet` in both agent `.md` files) serves as the **fallback default** — it applies when `PRIMARY_MODEL`/`ENRICHMENT_MODEL` are not passed (e.g., manual `/extract` invocation without the worker).

**Parallel execution:** Redis queue + KEDA naturally supports different types/assets running in parallel on different pods. Each worker independently loads its type's config. No coordination needed.

**Empirical model comparison (ADI transcript, 2026-03-14/15):**

| Model | Items | XBRL Links | Members | Period Accuracy | basis_norm | Speed |
|-------|-------|-----------|---------|-----------------|------------|-------|
| Haiku 4.5 | 8 | 38% | 0% | Correct | Mixed | ~2 min |
| **Sonnet 4.6** | **16** | **88%** | **38%** | **Correct** | **Best** | ~5 min |
| Opus 4.6 | 14 (full pipeline retest) | 63% | 31% | **Wrong** (+1 month) | Often "unknown" | ~8 min |

Opus period bug is reproducible (confirmed in 2 independent runs). Root cause: incorrect fiscal year-end math for non-standard FYE companies (ADI FYE=Oct 31).

Full comparisons: `.claude/plans/Extractions/guidanceModelComp.md`, `adi_opus_vs_sonnet_comparison.md`, `adi_sonnet_backup.json`

### 2.8. Active Runtime Guardrails

These live outside the extraction prompt stack and apply globally. Do not reimplement inside contracts.

- Extraction agents expose Neo4j **read** access only — `write_neo4j_cypher` is not in their tool lists
- `PreToolUse` on `Write` runs output validators (`.claude/settings.json`)
- `PreToolUse` on `Edit|Write` blocks env-file edits (`.claude/settings.json`)
- `PreToolUse` on Neo4j write MCP calls runs delete guard (`.claude/settings.json`)
- `PostToolUse` on `Write` runs cleanup (`.claude/settings.json`)

### 2.8. Already Implemented (Do Not Reopen)

- 10-K is a first-class asset with its own `10k.md` and `10k-queries.md`
- The old `SOURCE_TYPE` pipeline parameter was removed; graph `source_type` still exists and is derived from `{ASSET}`
- All 5 asset profiles were decontaminated
- Guidance-specific asset rules live in guidance intersection files
- Dynamic type discovery is live in both trigger and worker
- Enrichment gating is file-existence based
- Warmup helpers exist for concept/member caches and transcript query `3B`
- Guidance writer/id tests passed locally on 2026-03-09 (`181 passed`)
- Per-type×asset model configuration via `config.yaml` (2026-03-15) — 3 independent roles (orchestrator/primary/enrichment) configurable per asset. Verified: guidance/news→haiku and guidance/transcript→sonnet ran on same pod with correct model routing. See Section 2.7.

---

## 3. File Inventory

All skill/query paths relative to `.claude/skills/extract/`.

```
.claude/agents/
  extraction-primary-agent.md      (66 lines)    Generic primary agent shell
  extraction-enrichment-agent.md   (69 lines)    Generic enrichment agent shell

.claude/skills/extract/
  SKILL.md                         (53 lines)    Orchestrator: primary → conditional enrichment → report (parses PRIMARY_MODEL/ENRICHMENT_MODEL)
  evidence-standards.md            (12 lines)    4 universal guardrails
  queries-common.md               (323 lines)    Shared queries: context (1A–1D), caches (2A–2B), inventory (8A), fulltext (9A–9F)

  assets/                                        Asset profiles (data structure) + asset queries
    transcript.md / transcript-queries.md         (138 / 104 lines)  3A–3G queries
    8k.md / 8k-queries.md                         (152 / 114 lines)  4A–4I queries
    10q.md / 10q-queries.md                       (162 / 142 lines)  5A–5I queries
    10k.md / 10k-queries.md                       (162 / 142 lines)  5A–5I queries
    news.md / news-queries.md                     (122 / 103 lines)  6A–6E queries

  types/guidance/                                 Guidance extraction type
    config.yaml                    (17 lines)     Per-asset model config: orchestrator/primary/enrichment per asset
    core-contract.md               (707 lines)    Schema, fields, ID formula, XBRL/member matching, write path
    primary-pass.md                (229 lines)    FETCH → EXTRACT → VALIDATE → WRITE workflow
    enrichment-pass.md             (173 lines)    Existing items → secondary content → enrich → write
    guidance-queries.md            (132 lines)    7A–7F, 8B: existing tags, readback, baseline, counts

    assets/                                       Intersection files (TYPE × ASSET extraction rules)
      transcript-primary.md        (74 lines)     Speaker hierarchy, basis context trap, [PR] prefix
      transcript-enrichment.md     (94 lines)     Q&A scanning, consensus comfort, [Q&A] prefix
      8k-primary.md               (106 lines)     Exhibit-first routing, table scanning, [8-K] prefix
      10q-primary.md               (78 lines)     MD&A primary, forward-looking strictness, [10-Q] prefix
      10k-primary.md               (78 lines)     Same as 10-Q + multi-year targets, [10-K] prefix
      news-primary.md              (79 lines)     Attribution rule, prior period values, [News] prefix
```

### Deterministic Scripts (`.claude/skills/earnings-orchestrator/scripts/`)

| Script | Purpose |
|--------|---------|
| `guidance_ids.py` | ID generation, unit canonicalization, evidence hashing, period routing |
| `guidance_writer.py` | MERGE patterns, param assembly, Neo4j writes (atomic per item) |
| `guidance_write_cli.py` | CLI entry point: reads JSON, computes IDs, calls writer. Modes: `--dry-run` / `--write` |
| `guidance_write.sh` | Shell wrapper (venv activation + Neo4j connection env vars) |
| `concept_resolver.py` | Deterministic XBRL concept resolution (49-entry reviewed registry) + concept family mapping (19-entry canonical anchor table). Runs in `guidance_write_cli.py` before writer. |
| `warmup_cache.py/.sh` | Pre-compute concept cache (2A), member cache (2B), transcript content (3B) to `/tmp/` — bypasses MCP truncation |
| `fiscal_math.py` | Calendar-to-fiscal date math (FYE variants) |
| `fiscal_resolve.py` | Period resolution from XBRL periods |

### Runtime Infrastructure (`scripts/`)

| Script | Purpose |
|--------|---------|
| `extraction_worker.py` (~520 lines) | K8s worker: Redis BRPOP → load config.yaml → resolve models → Agent SDK → status tracking |
| `trigger-extract.py` (280 lines) | Query Neo4j for unprocessed → LPUSH. Flags: `--all`, `--type`, `--asset`, `--list`, `--force`, `--retry-failed`, `--source-id` |

### K8s Manifest

| File | Purpose |
|------|---------|
| `k8s/processing/extraction-worker.yaml` (148 lines) | Deployment + KEDA ScaledObject (min 1, max 7) |

**Total**: 23 skill files (~3,400 lines instructions) + 7 deterministic scripts + 2 runtime scripts + 1 K8s manifest.

---

## 4. Design Decisions

| # | Decision | Reasoning |
|---|----------|-----------|
| D1 | 2 generic agent shells, not N per type/asset | Agents are shells that load content via path convention. Per-type agents cause proliferation. |
| D2 | Intersection files at slot 4 | Decouple type-specific extraction rules from asset data structure. Eliminates contagion. |
| D3 | 3 axes (TYPE × ASSET × PASS) | 2 insufficient (proven by exhaustive analysis). 4 unnecessary. PASS subordinate to TYPE. |
| D4 | File-existence gate for enrichment | Simpler than metadata. Adding enrichment = add a file. Removing = delete it. |
| D5 | Python scripts for deterministic ops, usually wrapped by Bash | Agents are nondeterministic. IDs, units, periods, and writes must be deterministic. Scripts are tested (181 tests passing). |
| D6 | File-based result protocol (/tmp JSON) | SDK output parsing unreliable for large results. File transfer is robust. |
| D7 | Dynamic type discovery (disk scan) | Worker/trigger scan `types/` directory. No config to update when adding types. |
| D8 | Single Redis queue for all types | All types share `extract:pipeline`. Worker routes by payload `type` field. No queue proliferation. |
| D9 | Per-type status on source nodes | `{type}_status` property. Multiple types can process the same source independently. |
| D10 | Calendar-based periods | `gp_2025-04-01_2025-06-30`, not fiscal keys. Company-agnostic — same calendar window shares same node. 4 sentinels: `short_term`, `medium_term`, `long_term`, `undefined`. |
| D11 | Corporate announcements EXCLUDED | Buybacks, investment programs, facility plans are not guidance. Dividend guidance IS extractable. |
| D12 | Pass briefs intentionally redundant with core-contract | Redundancy IS the quality mechanism. Agents see critical rules twice from different angles. |
| D13 | Quote prefixes per source type | `[PR]`, `[Q&A]`, `[8-K]`, `[10-Q]`, `[10-K]`, `[News]` enable provenance tracking. |
| D14 | Hyphen-free asset names | Collision with `-{pass}` delimiter in `{ASSET}-primary.md`. Use underscores. |
| D15 | Evidence hash (evhash16) | SHA-256 first 16 chars of evidence content. Cross-source change detection without affecting ID. |
| D16 | Frozen originals archived | Old pipeline in `.claude/archive/`. Retirement quality-gated, not time-gated. |
| D17 | KEDA min=1, max=7, cooldown 300s | min=1 prevents killing pods mid-extraction. max=7 safe for parallel tickers. |
| D18 | FG agents, not BG | BG custom agents collapse to 1 tool (Bash only) — agents need 7 tools including MCP. Sequential primary→enrichment dependency means no parallelism benefit. KEDA handles cross-job parallelism at pod level. |

---

## 5. Validated Results (Golden Steps)

### 5.1. AAPL First Production Run

- 5 transcripts (2023-02 through 2024-02), 46 GuidanceUpdate nodes written
- All graph links correct (Guidance, GuidancePeriod, Company, Concept, Member)
- KEDA parallel scaling (1→4 pods) verified
- First confirmation that the full pipeline works end-to-end

### 5.2. CRM E2E Validation (2026-03-09)

All 5 asset types validated in a single company run:

| Asset | Source | Items | Key Metrics |
|-------|--------|-------|-------------|
| Transcript | `CRM_2026-02-25T17.00` | 5 (3P+2E) | FY27 Rev $46.2B, FY30 Rev $63B, FCF, Gross Margin |
| 8-K (earnings) | `0001108524-25-000027` | 20 | Revenue, EPS (GAAP+non-GAAP), OpMargin, cRPO, FCF, OCF, Tax Rate |
| 8-K (non-earnings) | `0001108524-25-000040` | 0 | Correct NO_GUIDANCE (board appointment) |
| 10-Q | `0001108524-25-000030` | 1 | Restructuring Costs $160-190M |
| 10-K | `0001108524-25-000006` | 1 | Restructuring Cash Payments $300-325M |
| News (guidance) | `bzNews_49196246` | 1 | FY2026 GAAP EPS $7.22-$7.24 |
| News (analyst) | `bzNews_50977877` | 0 | Correct NO_GUIDANCE (analyst rating) |

**28 GuidanceUpdate nodes. Manual verification: 100% value accuracy. Enrichment correctly only ran for transcript.**

### What Made It Work

- **8-slot loading** gave agents exactly the right context with zero pollution between types/assets
- **Deterministic IDs** made writes idempotent — re-running the same source safely overwrites
- **Two-pass architecture**: primary (prepared remarks) → enrichment (Q&A) captured all guidance with correct derivation types
- **`warmup_cache.sh`** bypassed MCP query transcription errors and improved large-query fidelity for 2A/2B/3B, though large `/tmp` reads still remain an open issue
- **Calendar-based periods** shared correctly across companies (no fiscal-year confusion)
- **Per-segment guidance** (e.g., iPhone/iPad/Mac/Services/Total revenue) handled via `segment_slug` in ID — no false duplicates
- **Quality filters** caught edge cases: `derivation=floor` for "at least" language, null values for qualitative, correct NO_GUIDANCE for non-guidance sources

### Not Bugs (Confirmed Working-As-Designed)

- **Revenue "duplicates"** — 5 GUs for same period = correct per-segment guidance. ID includes member suffix so records are distinct.
- **Null `metric_value`** — Expected for qualitative guidance. Null is correct when no number is given.

### Regression Bar

Future changes must preserve:

- Same `GuidanceUpdate` IDs for unchanged logic
- Same key field values for validated items
- Same no-guidance behavior on non-guidance sources
- Same idempotent rerun behavior
- Same deterministic write path

---

## 6. Recipes

### 6.1. Adding a New Extraction Type

Example: `analyst_estimates`. Runtime auto-discovers types via `discover_allowed_types()`.

**Step 1 — Create type directory** (auto-discovered, zero runtime changes):
```
.claude/skills/extract/types/analyst_estimates/
├── core-contract.md                     # Schema: graph nodes, fields, ID formula, validation
├── primary-pass.md                      # Working brief: FETCH → EXTRACT → VALIDATE → WRITE
├── analyst_estimates-queries.md         # Type-specific Cypher queries
├── enrichment-pass.md                   # Optional: only if multi-section extraction needed
└── assets/
    ├── transcript-primary.md            # Intersection: what to extract from transcripts
    ├── 8k-primary.md                    # Intersection: what to extract from 8-Ks
    └── news-primary.md                  # etc.
```

**Step 2 — Create writer scripts** (mirror `guidance_ids.py` / `guidance_writer.py` pattern):
```
.claude/skills/earnings-orchestrator/scripts/
├── analyst_estimates_ids.py
├── analyst_estimates_writer.py
├── analyst_estimates_write_cli.py
└── analyst_estimates_write.sh
```

**Step 3 — Validate**:
```bash
python3 scripts/trigger-extract.py --type analyst_estimates --mode dry_run --source-id {ID} {TICKER}
```

**Zero changes required** to: worker, trigger, orchestrator, agents, SKILL.md, evidence-standards, asset files, or asset queries. Status tracked via `analyst_estimates_status` property on source nodes.

### 6.2. Adding a New Data Asset

Example: `proxy` (DEF 14A proxy statements).

**Step 1 — Create 2 asset files** at `.claude/skills/extract/assets/`:
```
proxy.md              # Data structure: Neo4j label, content layers, fetch order
proxy-queries.md      # Asset-specific Cypher queries
```

**Step 2 — Register in runtime** (code change required in 2 files):
```python
# trigger-extract.py — add to ASSET_QUERIES:
"proxy": ("Report", "r", "r.formType='DEF 14A'", ("PRIMARY_FILER", "out"))

# extraction_worker.py — add to ASSET_LABELS:
"proxy": ("Report", "r")
```

**Step 3 — Create intersection files** for each type that uses this asset:
```
.claude/skills/extract/types/guidance/assets/proxy-primary.md
```

**Step 4 — Naming**: Asset names must NOT contain hyphens (collision with `-{pass}` delimiter). Use underscores.

**Step 5 — Follow the Decontamination Standard** (3 requirements for new asset files):
- **R1**: Any new extraction type must work without adding new queries (asset queries are generic)
- **R2**: Zero type-specific vocabulary in asset profile or asset queries
- **R3**: Current extraction types still work after changes (no regression)

### 6.3. Verification Gates (required for every new TYPE × ASSET combination)

- **Gate 1 (prompt-stream diff)**: What agents see must be equivalent before and after changes. No content loss.
- **Gate 2 (dry-run regression)**: Output quality must match or exceed baseline. Test with both "rich content" and "no content" sources.

### 6.4. What to Preserve When Extending

- Keep pass briefs redundant with core-contract (redundancy = quality)
- Keep per-type scripts until >50% overlap proves shared abstraction
- Keep enrichment conditional on file existence, not hardcoded
- Keep atomic commits (single commit, single `git revert` rollback)
- Gate 1 + Gate 2 for every new TYPE × ASSET combination
- Test with both "rich guidance" and "no guidance" sources to verify precision AND recall

---

## 7. Open Items

### 7.1. Runtime Issues

| # | Issue | Severity | Root Cause & Fix Path |
|---|-------|----------|----------------------|
| E4c | 10-K MD&A content truncation | Low | `<persisted-output>` ~50KB threshold. CRM 10-K MD&A is 52.2KB. Agent works around with Bash. Fix: extend `warmup_cache.py` with `--10k-content ACCESSION`. |
| E4d | Member cache Read truncation | Medium | CRM 143 members = 52.6KB. `warmup_cache.sh` writes correctly, agent's `Read` hits threshold on both passes. Fix: instruct Bash-based reading or split into per-axis files. |
| E4e | Transcript JSON Read truncation | Medium | CRM transcript 76.7KB. Same root cause. Agent recovers with Bash+Python chunking (3-4 extra turns, ~$0.50–$1.00 wasted). Fix: have warmup split into chunks. |
| E5 | MCP-vs-Python Neo4j divergence (re-verify) | **High if real** | Older validation notes reported MCP `neo4j-cypher` seeing different data than Python `get_manager()`, but this document was updated from repo audit rather than live infra checks. Re-verify before coding against it. |
| E8 | Inconsistent period codes across sources | Low | Same disclosure: `gp_UNDEF` (10-Q) vs `gp_ST` (10-K) for "future cash payments". Fix: standardize "future, no end date" → one canonical code in pass briefs. |
| E9 | ~~Inconsistent concept linking~~ | ~~Low~~ | **RESOLVED** — `concept_resolver.py` with 49-entry CONCEPT_CANDIDATES registry + concept family mapping. Deterministic, fail-closed. See S23. |
| E10 | Inconsistent entity naming across sources | Low | Same disclosure → different labels (e.g., `restructuring_costs` vs `restructuring_cash_payments`). Fix: label normalization table or post-processing dedup. |

**E4 shared root cause**: the `~50KB` `<persisted-output>` threshold applies to MCP output, `Read`, and large shell output. `warmup_cache.sh` helps by moving 2A/2B/3B results into `/tmp`, but large subsequent reads of those files can still hit the same ceiling.

### 7.2. Quick Wins (1-line changes each)

| # | Change | Where | Benefit |
|---|--------|-------|---------|
| S14 | `includeGitInstructions: false` | `settings.json` or env var `CLAUDE_CODE_INCLUDE_GIT_INSTRUCTIONS=false` | ~500 tokens/turn saved |
| S19 | `argument-hint: "TICKER ASSET SOURCE_ID TYPE= MODE="` | `/extract` SKILL.md | Autocomplete help |
| S20 | `disable-model-invocation: true` | `/extract` SKILL.md | ~100 tokens saved |
| S22 | `disallowedTools: [mcp__neo4j-cypher__write_neo4j_cypher]` | Both agent shells | Defense-in-depth |

### 7.3. Enhancements

| # | Item | Reasoning |
|---|------|-----------|
| S12 | `${CLAUDE_SKILL_DIR}` for portable paths | v2.1.69+. Only helps SKILL.md; agents still need project-relative. |
| S13 | `agent_type` in hooks for per-agent validation | v2.1.69+. `jq` check per hook script to differentiate primary vs enrichment. |
| S15 | Per-company agent memory | Two-tier: shared MEMORY.md + per-company `{TICKER}.md`. `memory: project` scope. Agents accumulate company-specific patterns. |
| ~~S16~~ | ~~`model:` field for cost optimization~~ | **DONE** — `config.yaml` per type with per-asset overrides. 3 independent roles (orchestrator/primary/enrichment). Worker reads config, passes `PRIMARY_MODEL`/`ENRICHMENT_MODEL` to SKILL.md, which passes `model=` to Agent tool. Opus comparison completed: Sonnet wins (period bug, XBRL regression). See Section 2.7. |
| S17 | `PostToolUseFailure` hook | Structured error logging without transcript parsing. |
| S18 | `skills:` field for evidence-standards | Auto-load. Saves 1 Read call per invocation. |
| S21 | Stop hook as quality gate | Validate result JSON before returning to worker. Saves full retry cost. Complex. |
| ~~S23~~ | ~~Inline deterministic concept resolver~~ | **DONE** — `concept_resolver.py` implemented: 49-entry CONCEPT_CANDIDATES registry (xbrl_qname resolution) + 19-entry CONCEPT_FAMILY table (concept_family_qname). Concept repair runs before inheritance; concept_family_qname assigned after inheritance, before writer. 19 tests pass. |

### 7.4. Pending Confirmations

| # | Item | Action |
|---|------|--------|
| S2 | Budget/cost per extraction | Measure actual Claude API spend for AAPL vs CRM runs. Needed for scaling estimates. |
| S3 | `earnings_trigger.py` retirement | Verify legacy trigger is fully dormant (uses different queue `earnings:trigger`). If dormant, archive. |

### 7.5. Deferred Items

| # | Item | Trigger |
|---|------|---------|
| S1 | GuidancePeriod: share across types? | Phase 4 — when second type needs period nodes |
| S4 | `core-contract.md` too long (707 lines) | Post-retirement — consider schema/rules split |
| S6 | Rename `{type}-inventory` convention | Post-retirement (cosmetic) |
| S8 | Shared `write_cli.py` abstraction | Phase 4+ — only if >50% code shared with type #2 |

### 7.6. Design Proposals (Not Yet Implemented)

**Principle-based extraction rules**: Replace enumerated positive/negative example tables across 8 intersection files with 8 abstract principles in `core-contract.md`. Reduces ~140 lines. Principles: Forward-looking, From management, Quantitative anchor, Guidance not actions, Verbatim evidence, No fabrication, Factors are conditions, Recall over precision. Risk: 6 regression scenarios at boundary cases. Speaker hierarchy + Prior Period Values tables KEPT (asset/type-specific edge cases). Full plan in git history.

### 7.7. Post-Extraction Batch Fix: XBRL Concept Linking (Priority 1 — after historical extraction completes)

**Problem:** Some companies use XBRL concept variants not in the `CONCEPT_CANDIDATES` alias table. The resolver only matches EXACT local names from the company's concept cache. If the company uses a variant not listed, the link fails.

**Validated examples (2026-03-15, KSS + DELL empirical testing):**
- KSS Dividend Per Share: uses `CommonStockDividendsPerShareCashPaid` (not `Declared`) — **fixed** by adding second candidate
- KSS CapEx: uses `PaymentsToAcquireProductiveAssets` (not `PropertyPlantAndEquipment`) — **fixed** by adding third candidate
- Both fixes verified: DELL resolves to candidate #1, KSS resolves to new candidates. Zero regression.

**Why after, not now:** All extraction data (values, quotes, periods, source links) is correct. Only the XBRL concept link property (`xbrl_qname`) may be missing or non-standard. More companies processed = more variants surface = easier batch fix. Once fixed, all future live extractions immediately benefit (the resolver runs at write time).

**Two classes of gaps to find:**

| Gap Class | What | How to find | Example |
|---|---|---|---|
| **Direct miss** | Label IS in alias table, no candidate matched, `xbrl_qname=NULL` | Query 1 | KSS "Dividend Per Share" before fix |
| **Survivor** | Label IS in alias table, resolver returned None, but agent's cache-valid qname was preserved (line 293-296). Graph has a valid link, but the alias table is incomplete. | Query 2 | Agent finds `PaymentsToAcquireProductiveAssets`, resolver doesn't know it, agent value kept |

**Step-by-step fix (single session):**

**Step 1: Find direct misses (null xbrl_qname)**
```cypher
-- Query 1: Items where concept link is missing
MATCH (gu:GuidanceUpdate)
WHERE gu.xbrl_qname IS NULL
RETURN gu.label, count(*) AS unlinked
ORDER BY unlinked DESC
```
For each high-count label: check if `slug(label)` IS in `CONCEPT_CANDIDATES`. If yes → variant is missing. If no → unreviewed label (add to alias table or confirm it's correctly null).

**Step 2: Find survivors (non-standard links the agent found)**
```cypher
-- Query 2: All (label, qname) pairs across all companies
MATCH (gu:GuidanceUpdate)
WHERE gu.xbrl_qname IS NOT NULL
RETURN gu.label, gu.xbrl_qname, count(*) AS cnt
ORDER BY gu.label, cnt DESC
```
Cross-reference against `CONCEPT_CANDIDATES`. If CapEx maps to 3 different qnames across companies but only 2 are in the alias table → add the third. The graph data is already correct (agent found the right concept); this just makes the resolver complete.

**Step 3: Discover missing variants**

For each unresolved label from Step 1:
```bash
# Regenerate concept cache for an affected company
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh $TICKER

# Search cache for the missing variant
python3 -c "
import json
with open('/tmp/concept_cache_$TICKER.json') as f:
    data = json.load(f)
for r in data:
    if 'KEYWORD' in r.get('label', '') or 'KEYWORD' in r.get('qname', ''):
        print(r)
"
```

**Step 4: Add variants to alias table**

Append to `CONCEPT_CANDIDATES` tuple in `concept_resolver.py`. Curated candidates tried first, new variant tried last. Same pattern as the KSS fixes.

**Step 5: Backfill historical nodes**

Option A — Re-run extraction with `--force` on affected companies (idempotent, re-resolves concepts).

Option B — Direct Cypher update for known fixes:
```cypher
// Example: backfill CapEx with PaymentsToAcquireProductiveAssets for companies that have it
MATCH (gu:GuidanceUpdate)
WHERE gu.xbrl_qname IS NULL AND gu.label =~ '(?i)capex|capital expenditures?|capital spending'
MATCH (gu)-[:FOR_COMPANY]->(c:Company)
// Check if company has the variant in their XBRL
MATCH (c)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x)-[:USES_CONCEPT]->(con:Concept)
WHERE con.qname = 'us-gaap:PaymentsToAcquireProductiveAssets'
SET gu.xbrl_qname = 'us-gaap:PaymentsToAcquireProductiveAssets'
RETURN gu.id, c.ticker
```

**Step 6: Link Concept edges for backfilled items**
```cypher
MATCH (gu:GuidanceUpdate)
WHERE gu.xbrl_qname IS NOT NULL
AND NOT (gu)-[:MAPS_TO_CONCEPT]->(:Concept)
MATCH (con:Concept {qname: gu.xbrl_qname})
MERGE (gu)-[:MAPS_TO_CONCEPT]->(con)
RETURN count(*) AS edges_created
```

**Rationale for no runtime audit/capture system:** All evidence needed for this fix is permanent — GuidanceUpdate nodes persist in Neo4j with label/xbrl_qname properties, concept caches are regeneratable from XBRL data, alias table is in git. Survivor cases are discoverable via Query 2 (qname diversity analysis). No ephemeral data is lost between extraction and fix. Evaluated 3 alternative approaches (shared-prefix auto-discovery, full forensic audit, non-heuristic miss logger) — all add runtime complexity for evidence that's already derivable from persistent data.

### 7.8. Future Work

| Item | Blocked On | Notes |
|------|------------|-------|
| Phase 4: first non-guidance type | Type selection | 5-6 files (auto-discovered). Zero infrastructure changes. |
| Generic type for learner | `learner.md` design | Learner edits 1 pass file. Auto-ingest + ad-hoc triggers. |
| Event Trader → earnings:trigger | Phase 2 design | Listener ready; producer not wired. |
| Old pipeline retirement | Quality-gated | `kubectl delete` old claude-code-worker. |
| Quota guard | Design needed | Beyond MAX_BUDGET ($5) and MAX_TURNS (80). |
| Obsidian integration | Design needed | Persist extraction JSON payloads per-company (currently ephemeral /tmp). |
| ~~Sonnet vs Opus comparison~~ | ~~`model:` field (S16)~~ | **DONE** — 3-model comparison (Haiku/Sonnet/Opus) on PG/DECK/NSC + full-pipeline Opus retest on ADI. Sonnet wins. See `guidanceModelComp.md`, `adi_opus_vs_sonnet_comparison.md`. |
| Multi-source trigger design | Generic type | Unify auto-ingestion, manual, learner, scheduled, event-driven triggers. |

---

## 8. Design Notes

Preserved from architecture proofs — useful context for future decisions:

1. **PASS is subordinate to TYPE** — each type defines its own pass set. Model is 2 independent axes (TYPE × ASSET) + TYPE-defined phases.
2. **Intersection files are optional** — not every TYPE × ASSET × PASS combo needs one. Missing files caught by dry-run regression, not loading mechanism.
3. **Cross-type data sharing intentionally absent** — handled at orchestrator level, not instruction files. Prevents pollution by design.
4. **File proliferation is linear** — N types × M assets × P passes. 3 types × 5 assets ≈ 25 intersection files max.
5. **>2 content sections** — if a future asset has 3+ content sections, extend enrichment or add tertiary pass. Current model assumes at most 2 sections.
6. **Canonical units** — `usd`, `m_usd`, `percent`, `percent_yoy`, `percent_points`, `basis_points`, `x`, `count`, `unknown`. Per-share labels (EPS/DPS) use `usd`, not `m_usd`. Canonicalized by `guidance_ids.py`.
7. **Graph architecture decisions** — No Context nodes (direct FOR_COMPANY edge), no Unit nodes (canonical_unit is property), calendar-based GuidancePeriod (company-agnostic, shared), single atomic MERGE query per item, no NEXT/PREVIOUS edges.
8. **Derivation taxonomy** — explicit, calculated, point, implied, floor, ceiling, comparative. Each has specific extraction rules in core-contract.md.
9. **Idempotency** — Deterministic slot-based IDs + MERGE = safe re-extraction. Evidence hash (`evhash16`) detects content changes independently of ID.
10. **Implementation deviations** — Frozen originals archived to `.claude/archive/` (not kept in-place). Evidence-standards is a 12-line local copy (not the 46-line original). Neither impacts functionality.

### Subtle Current Truths That Old Plans Often Got Wrong

- Adding a new **type** does NOT require a whitelist edit — type discovery is dynamic from disk.
- Adding a new **asset** still DOES require code edits in 2 Python files (`ASSET_QUERIES` + `ASSET_LABELS`).
- The shared queue is intentional. Isolation comes from the prompt stack and job granularity, not per-type queues.
- `evidence-standards` is loaded from `.claude/skills/extract/evidence-standards.md`, not from the separate old skill at `.claude/skills/evidence-standards/SKILL.md`.
- Global hooks are configured in `.claude/settings.json`; they are not encoded in the extraction agents' frontmatter.
- `source_type` still exists on graph records, but the pipeline now derives it from `{ASSET}`; the old `SOURCE_TYPE` argument is gone.

### Practical Guidance For Future Bots

- If a markdown plan conflicts with code, trust the code.
- If you need to move rules, move them downward: generic -> type -> type+asset intersection, never the reverse.
- Do not assume a new asset is docs-only; asset onboarding still touches Python.
- Do not assume a new type is runtime-only; the type contract is prompt-first and script-backed.
- Do not introduce direct Neo4j writes from agents.
- Do not reintroduce shared prompt contamination just to save files.
- When large payloads are involved, solve fidelity first and elegance second.

---

## 9. Key Commits (Milestone Reference)

| Commit | What |
|--------|------|
| `8a87a0f` | Transcript pollution fix — intersection file pattern established |
| `d3af160` | 10-K split + SOURCE_TYPE removal (15 files: 2 creates + 13 edits) |
| `84fc97f` | Total contagion fix (categories A/B/C/E) — all generic files cleaned |
| `42ebdf6` | News decontamination + dynamic type discovery in control plane |
| `6c626d6` | 10-Q/10-K decontamination + warmup_cache.py (E1/E4a/E4b fixes) |
| `4f5d7c3` | 8-K/Transcript decontamination — all 5 asset profiles clean |
| `349bd86` | Concept labels in 2A cache + CRM E2E validation (28 items, all 5 assets) |
