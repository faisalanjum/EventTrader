# Plan: Rewrite `guidance-extract.md` Agent

## Context

The guidance extraction system has completed Phase 2: SKILL.md v2.2, QUERIES.md v2.6, 4 source profiles, and 3 utility scripts (125 tests) are all done. The agent file (`guidance-extract.md`) is the only remaining item — it's still the old TSV-output, pre-graph version (365 lines). It needs to become a thin graph-native orchestrator that references the completed reference files instead of duplicating their content.

## File to Modify

`.claude/agents/guidance-extract.md` — full rewrite (not incremental edit)

## What Gets Deleted (and Why)

Every line below is either duplicated in a reference file or dead (superseded by graph-native output):

| Lines | Content | Reason |
|-------|---------|--------|
| 36-46 | FYE usage table | Duplicated in SKILL.md §9, PROFILE_TRANSCRIPT |
| 52-123 | All Cypher queries (7 source-type queries) | All in QUERIES.md §3-§6 |
| 146-198 | Source-specific extraction hints | All in PROFILE_*.md files |
| 202-226 | Extract fields table (18 fields) | SKILL.md §2 (19 fields now) |
| 229-236 | Derivation rules | SKILL.md §5 (7 values now, not 4) |
| 240-252 | Segment rules | SKILL.md §7 |
| 255-270 | Metric normalization (8 metrics) | SKILL.md §4 (12 metrics now) |
| 274-283 | Qualitative guidance rules | SKILL.md §5 |
| 286-296 | Section values | Profiles cover per-source |
| 297-316 | Step 3: TaskUpdate + TSV file write | Dead (§15J) |
| 318-343 | Step 4: TSV output format | Dead (§15J) |
| 357-365 | Quality filters | SKILL.md §13 |

Total: ~250 of 365 lines deleted.

## What Gets Added (Section by Section)

### 1. Frontmatter

Add 2 missing tools, keep existing ones:
```yaml
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher   # Source fetch + warmup caches
  - mcp__neo4j-cypher__write_neo4j_cypher  # Graph writes (MERGE pattern)
  - Bash                                    # Python utilities (guidance_ids.py, fiscal_resolve.py)
  - TaskList                                # Team workflow context
  - TaskGet
  - TaskUpdate
  - Write                                   # Dry-run output logs
  - Read                                    # Auto-load reference files
```

### 2. Auto-Load Block (NEW — replaces all inlined content)

Before doing anything, agent must Read:
1. `SKILL.md` — schema, fields, validation, quality filters, write patterns
2. `QUERIES.md` — all Cypher queries by section number
3. The appropriate `PROFILE_*.md` for the source type being processed

This is the mechanism that eliminates duplication. The agent loads ~1400 lines of reference content at runtime instead of inlining ~250 lines of stale copies.

### 3. Input Format (REWRITE)

Old: `TICKER REPORT_ID SOURCE_TYPE SOURCE_KEY QUARTER FYE=M TASK_ID=N`
New: `{TICKER} {SOURCE_TYPE} {SOURCE_ID} [MODE=dry_run|shadow|write]`

Changes:
- Source types change from content-level (`exhibit`, `section`, `filing_text`) to filing-level (`8k`, `transcript`, `news`, `10q`, `10k`, `initial`)
- `SOURCE_KEY` removed from input — derived internally per source type (SKILL.md §12)
- `QUARTER` and `FYE` removed — derived from graph (QUERIES.md 1B) instead of manual params
- `TASK_ID` removed from input — agent checks TaskList for its assignment
- `MODE` added — controls dry_run/shadow/write behavior (SKILL.md §16)

### 4. Pipeline (REWRITE — 5 steps replacing old 4 steps)

**Step 1: Load Context**
- Company + CIK → QUERIES.md 1A
- FYE from 10-K → QUERIES.md 1B (extract month from `periodOfReport`)
- Pre-fetch Periods → QUERIES.md 1C
- Warmup caches → QUERIES.md 2A (concept), 2B (member)
- Existing guidance tags → QUERIES.md 7A

**Step 2: Fetch Source Content**
- Route by `SOURCE_TYPE` to correct QUERIES.md section:
  - `transcript` → 3B (structured), 3C fallback, 3D fallback
  - `8k` → 4G (inventory), 4C (exhibit), 4E (section), 4F (filing text fallback)
  - `10q`/`10k` → 5B (MD&A), 5C (financial stmts), 4F (fallback)
  - `news` → 6A (single item) or 6B (channel-filtered batch)
- Apply empty-content rules from SKILL.md §17

**Step 3: LLM Extraction**
- This IS the agent doing its job — no external tool call
- Apply per-source profile rules (loaded in auto-load step)
- Apply quality filters from SKILL.md §13
- For each guidance item, extract: quote, period intent, basis, metric, values, derivation, segment, conditions, XBRL candidates

**Step 4: Deterministic Validation**
- For each extracted item:
  - Resolve fiscal period → `fiscal_resolve.py` via Bash
  - Canonicalize unit + values → `guidance_ids.py` via Bash
  - Validate basis rule (SKILL.md §6): explicit-only or default `unknown`
  - Resolve `xbrl_qname` from concept cache (SKILL.md §11)
  - Apply member confidence gate (SKILL.md §7)
  - Compute deterministic IDs → `guidance_ids.py:build_guidance_ids()` via Bash
- If uncertain: keep core item, set `xbrl_qname=null`, skip member edges

**Step 5: Write to Graph (or dry-run/shadow)**
- `dry_run` (default): Log extracted items, skip writes
- `shadow`: Same + log exact MERGE Cypher with parameters
- `write`: Execute MERGE Cypher via `mcp__neo4j-cypher__write_neo4j_cypher`
- MERGE pattern follows `guidance_writer.py:_build_core_query()` — the agent constructs the same atomic Cypher (source by label, company by ticker, ON CREATE SET for GuidanceUpdate, member edges via UNWIND)

### 5. Script Invocation Patterns (NEW)

**fiscal_resolve.py** — CLI with stdin:
```bash
echo '$PERIODS_JSON' | python3 .claude/skills/earnings-orchestrator/scripts/fiscal_resolve.py $TICKER $FY $FQ $FYE_MONTH
```
Returns: `{"start_date": "...", "end_date": "...", "period_u_id": "duration_...", "source": "lookup|fallback"}`

**guidance_ids.py** — Python one-liner via Bash:
```bash
python3 -c "
import sys; sys.path.insert(0, '.claude/skills/earnings-orchestrator/scripts')
from guidance_ids import build_guidance_ids; import json
result = build_guidance_ids(label='$LABEL', source_id='$SOURCE_ID', period_u_id='$PERIOD_UID', basis_norm='$BASIS', segment='$SEGMENT', low=$LOW, high=$HIGH, unit_raw='$UNIT')
print(json.dumps(result))
"
```
Returns: `{"guidance_id": "...", "guidance_update_id": "...", "evhash16": "...", "canonical_unit": "...", ...}`

### 6. Write Cypher Template (NEW)

The agent needs the atomic MERGE Cypher for MCP write. This follows `guidance_writer.py:_build_core_query()` exactly. Include a concise template showing:
- MATCH source by label + MATCH company by ticker
- MERGE Guidance, Period, Context, Unit, GuidanceUpdate
- ON CREATE SET for GuidanceUpdate (idempotent)
- MERGE all 5 relationships
- Separate UNWIND query for member edges

This is NOT duplication — it's the MCP-adapted execution path. `guidance_writer.py` wraps the same Cypher for Python callers.

### 7. Output Format (REPLACE TSV)

Return a structured summary:
- Items extracted: count
- Items written (or would-write in dry-run): count
- Items skipped (MERGE no-op): count
- Errors: count + details
- Per-item detail if shadow mode (Cypher + params)

### 8. Error Handling (SIMPLIFY)

Reference SKILL.md §17 error taxonomy. Agent just needs rules:
- `SOURCE_NOT_FOUND` / `EMPTY_CONTENT`: log and return early
- `NO_GUIDANCE`: acceptable, return empty extraction
- `VALIDATION_FAILED`: skip item, continue with remaining
- `WRITE_FAILED`: log, do not retry

## Estimated Size

~120-150 lines. Breakdown:
- Frontmatter: ~12 lines
- Auto-load + description: ~15 lines
- Input format: ~15 lines
- Pipeline steps (5 steps, references only): ~40 lines
- Script invocations: ~20 lines
- Write Cypher template: ~25 lines
- Output + error handling: ~15 lines

## Key References (Do Not Modify)

| File | Path | Role |
|------|------|------|
| SKILL.md | `.claude/skills/guidance-inventory/SKILL.md` | Schema, fields, validation, quality filters |
| QUERIES.md | `.claude/skills/guidance-inventory/QUERIES.md` | All Cypher queries (~42) |
| PROFILE_TRANSCRIPT | `.claude/skills/guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | Transcript extraction rules |
| PROFILE_8K | `.claude/skills/guidance-inventory/reference/PROFILE_8K.md` | 8-K extraction rules |
| PROFILE_NEWS | `.claude/skills/guidance-inventory/reference/PROFILE_NEWS.md` | News extraction rules |
| PROFILE_10Q | `.claude/skills/guidance-inventory/reference/PROFILE_10Q.md` | 10-Q/10-K extraction rules |
| guidance_ids.py | `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py` | ID normalization, unit canonicalization |
| fiscal_resolve.py | `.claude/skills/earnings-orchestrator/scripts/fiscal_resolve.py` | Fiscal-to-calendar CLI wrapper |
| guidance_writer.py | `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py` | Write Cypher reference (Python path) |

## Verification

1. **No duplication check**: Grep for content that should only exist in reference files:
   - No Cypher queries (all in QUERIES.md)
   - No field table (in SKILL.md §2)
   - No derivation rules (in SKILL.md §5)
   - No metric normalization table (in SKILL.md §4)
   - No segment rules (in SKILL.md §7)
   - No unit alias table (in SKILL.md §8 / guidance_ids.py)
   - No FYE mapping table (in SKILL.md §9 / profiles)

2. **Reference integrity**: Every QUERIES.md section number and SKILL.md section number referenced in the agent must exist in those files.

3. **Tool coverage**: Verify frontmatter tools match what the pipeline steps actually use:
   - Step 1: `mcp read` + `Read`
   - Step 2: `mcp read`
   - Step 3: (agent LLM, no tool)
   - Step 4: `Bash` (scripts)
   - Step 5: `mcp write` or `Write` (dry-run log)
   - Team workflow: `TaskList` / `TaskGet` / `TaskUpdate`

4. **Existing tests still pass**: `python3 -m pytest .claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py test_fiscal_resolve.py test_guidance_writer.py` — all 125 tests (no script changes made).
