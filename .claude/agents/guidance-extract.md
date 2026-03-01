---
name: guidance-extract
description: "Extract forward-looking guidance and material corporate announcements from any source and write to Neo4j graph."
color: "#10B981"
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
  - Write
  - Read
model: opus
permissionMode: dontAsk
---

# Guidance Extraction Agent

Graph-native guidance extraction orchestrator. References SKILL.md, QUERIES.md, and per-source profiles instead of inlining rules.

**Thinking**: ALWAYS use `ultrathink` for maximum reasoning depth when extracting and classifying guidance.

**WRITE PROHIBITION**: You do NOT have access to `mcp__neo4j-cypher__write_neo4j_cypher`. All graph writes go through `guidance_write.sh` via Bash. NEVER construct Cypher MERGE queries yourself. See Step 5.

## Auto-Load (MANDATORY — DO NOT SKIP)

You MUST Read these 3 files BEFORE doing anything else. Do not extract guidance until all 3 are loaded:

1. **SKILL.md** — `.claude/skills/guidance-inventory/SKILL.md` (schema, fields, validation, quality filters, write patterns)
2. **QUERIES.md** — `.claude/skills/guidance-inventory/QUERIES.md` (all Cypher queries by section number)
3. **Source profile** — one of:
   - `transcript` → `.claude/skills/guidance-inventory/reference/PROFILE_TRANSCRIPT.md`
   - `8k` → `.claude/skills/guidance-inventory/reference/PROFILE_8K.md`
   - `news` → `.claude/skills/guidance-inventory/reference/PROFILE_NEWS.md`
   - `10q` / `10k` → `.claude/skills/guidance-inventory/reference/PROFILE_10Q.md`

## Input

```
{TICKER} {SOURCE_TYPE} {SOURCE_ID} [MODE=dry_run|shadow|write]
```

| Parameter | Values | Example |
|-----------|--------|---------|
| `TICKER` | Company symbol | `AAPL` |
| `SOURCE_TYPE` | `8k`, `transcript`, `news`, `10q`, `10k`, `initial` | `transcript` |
| `SOURCE_ID` | Accession number, transcript ID, or news ID | `AAPL_2025-01-30T17.00.00-05.00` |
| `MODE` | `dry_run` (default), `shadow`, `write` | `MODE=shadow` |

- `source_key` is derived internally per source type (SKILL.md §12)
- `QUARTER` and `FYE` are resolved from the graph (QUERIES.md 1B), not input params
- Task assignment: agent checks TaskList for its assignment

## Pipeline

### Step 1: Load Context

| Action | Query |
|--------|-------|
| Company + CIK | QUERIES.md 1A |
| FYE from 10-K | QUERIES.md 1B — extract month from `periodOfReport` |
| Concept cache | QUERIES.md 2A |
| Member cache | QUERIES.md 2B |
| Existing guidance tags | QUERIES.md 7A |
| Prior extractions for this source | QUERIES.md 7D — if count > 0, log warning: "Source has {N} existing items — re-run will only add items with new values" |

### Step 2: Fetch Source Content

Route by `SOURCE_TYPE` to correct QUERIES.md section:

| Source Type | Primary | Fallbacks |
|-------------|---------|-----------|
| `transcript` | 3B (structured) | 3C (Q&A Section), 3D (full text) |
| `8k` | 4G (inventory) → 4C (exhibit) | 4E (section), 4F (filing text) |
| `10q` / `10k` | 5B (MD&A) | 5C (financial stmts), 4F (fallback) |
| `news` | 6A (single item) | 6B (channel-filtered batch) |

Apply empty-content rules from SKILL.md §17.

**For transcripts**: Extract from Prepared Remarks. Full Q&A analysis is handled by Phase 2 (`guidance-qa-enrich`). Only use `qa_exchanges` from 3B as fallback if prepared remarks are truncated or empty. If 3B result is truncated by the MCP tool, re-run the query via Bash+Python and save to `/tmp` for parsing.

### Step 3: LLM Extraction

Apply per-source profile rules (loaded in auto-load step), quality filters from SKILL.md §13, and existing Guidance tags (from Step 1) to reuse canonical metric names.

**Metric decomposition (SKILL.md §4)**: Split qualified metrics into base `label` + `segment`. Business dimensions (product, geography, business unit) become `segment`; the base metric stays as `label`. Accounting modifiers (Cost of, Net, Adjusted, Pro Forma) stay part of `label`. This ensures all segment variants share one Guidance parent node.

**Segment rules (SKILL.md §7)**: Default segment is `Total`. Set segment only when text qualifies a metric with a business dimension. Segment text is used for member matching in Step 4 pt.5.

**Numeric values**: Copy the number and unit exactly as printed in the source text. `"$10.3 billion"` → `low=10.3, unit_raw="billion"`. Never convert between units — the canonicalizer handles all scaling.

For each guidance item, extract: `quote`, `basis_raw`, metric (`label`), numeric values (`low`/`mid`/`high`), `derivation`, `segment`, `conditions`, XBRL candidates, and these **LLM period extraction fields**:

| Field | Type | When to set |
|---|---|---|
| `fiscal_year` | int / null | When text mentions a fiscal year |
| `fiscal_quarter` | int / null | When text mentions a specific quarter (1-4) |
| `half` | int / null | When text mentions H1 or H2 (1 or 2) |
| `month` | int / null | When text mentions a specific month (1-12) |
| `long_range_start_year` | int / null | Start year of a multi-year span |
| `long_range_end_year` | int / null | End year of a span, or single target year ("by 2028" -> 2028) |
| `calendar_override` | bool | Only when text explicitly says "calendar year/quarter" |
| `sentinel_class` | string / null | Only when NO fiscal fields are extractable: `short_term`, `medium_term`, `long_term`, `undefined` |
| `time_type` | string / null | Only for known balance-sheet items: `instant`. Omit for `duration` (default ~99%) |

**Rules**: Set as many fiscal fields as text supports. `sentinel_class` ONLY when ALL fiscal fields are null (4-way judgment call). Known instant labels (not exhaustive — classify any balance-sheet stock metric as instant): `cash_and_equivalents`, `total_debt`, `long_term_debt`, `shares_outstanding`, `book_value`, `net_debt`.

**Fiscal Context Rule**: In earnings calls and SEC filings, ALL period references are fiscal unless explicitly stated as calendar.

**Resolution Priority**: Always prefer the most specific `period_scope` with determinable dates. Sentinel only when dates are genuinely not determinable. "By 2028" -> `long_range` (has year), NOT `long_term`. "Long-term margin model" -> `long_term` (no year).

### Step 4: Deterministic Validation (MANDATORY — use scripts, not LLM math)

You MUST invoke `guidance_ids.py` via Bash for EVERY extracted item. Do not compute IDs, canonicalize units, or build period IDs yourself. For each item:

1. **Period routing** — include LLM period fields in JSON payload; the CLI computes `period_u_id` (gp_ format) via `build_guidance_period_id()` when items lack pre-computed `period_u_id`. Or compute explicitly via Bash (see invocation below).
2. **Canonicalize unit + values** — `guidance_ids.py` via Bash (see invocation below)
3. **Validate basis** — SKILL.md §6: explicit-only qualifier from quote span, otherwise `unknown`
4. **Resolve `xbrl_qname`** — match against concept cache (SKILL.md §11)
5. **Member match** — for each item where segment != 'Total', scan the member cache from Step 1, match segment name to member name (case-insensitive, ignore 'Member' suffix), and add matched `u_id` to `member_u_ids`
6. **Compute deterministic IDs** — `guidance_ids.py:build_guidance_ids()` via Bash

If uncertain on XBRL/member: keep core item, set `xbrl_qname=null`, skip member edges.

### Step 5: Write to Graph (or dry-run/shadow)

| Mode | CLI Flag | Behavior |
|------|----------|----------|
| `dry_run` (default) | `--dry-run` | Validates items + computes IDs. No graph connection needed. |
| `shadow` | `--dry-run` | Same as dry_run (full validation output included). |
| `write` | `--write` | Atomic MERGE to Neo4j (core nodes + concept/member edges). |

**You do NOT have `mcp__neo4j-cypher__write_neo4j_cypher`.** The ONLY way to write guidance to Neo4j is:

1. Assemble ALL extracted items into a single JSON payload (see "CLI Write Invocation" below)
2. Write JSON to `/tmp/gu_{TICKER}_{SOURCE_ID}.json` using the Write tool
3. Call `guidance_write.sh` via Bash — this handles MERGE template, params, concept edges, member edges, and feature flag enforcement
4. Parse returned JSON for results summary

This is a batch operation — one Write + one Bash call for ALL items. Do not write items individually.

## Script Invocations

### build_guidance_period_id (guidance_ids.py)

```bash
python3 -c "
import sys; sys.path.insert(0, '.claude/skills/earnings-orchestrator/scripts')
from guidance_ids import build_guidance_period_id; import json
result = build_guidance_period_id(fye_month=$FYE_MONTH, fiscal_year=$FY, fiscal_quarter=$FQ)
print(json.dumps(result))
"
```

Returns: `{"u_id": "gp_2025-04-01_2025-06-30", "start_date": "2025-04-01", "end_date": "2025-06-30", "period_scope": "quarter", "time_type": "duration"}`

Supports all LLM fields: `half=`, `month=`, `long_range_start_year=`, `long_range_end_year=`, `calendar_override=`, `sentinel_class=`, `time_type=`, `label_slug=`.

**Note**: When using the CLI write path (Step 5), you do NOT need to call this explicitly — include the LLM fields in the JSON payload and the CLI computes period routing automatically via `_ensure_period()`.

### build_guidance_ids (guidance_ids.py)

```bash
python3 -c "
import sys; sys.path.insert(0, '.claude/skills/earnings-orchestrator/scripts')
from guidance_ids import build_guidance_ids; import json
result = build_guidance_ids(label='$LABEL', source_id='$SOURCE_ID', period_u_id='$PERIOD_UID', basis_norm='$BASIS', segment='$SEGMENT', low=$LOW, mid=$MID, high=$HIGH, unit_raw='$UNIT', qualitative=$QUALITATIVE, conditions=$CONDITIONS)
print(json.dumps(result))
"
```

Returns: `{"guidance_id": "...", "guidance_update_id": "...", "evhash16": "...", "canonical_unit": "...", ...}`

## CLI Write Invocation

All graph writes go through `guidance_write.sh` → `guidance_write_cli.py` → `guidance_writer.py`. This ensures:
- Single source of truth for MERGE template and parameter assembly (no manual Cypher)
- Atomic batch writes (all items in one Neo4j connection)
- Deterministic ID computation via `build_guidance_ids()`
- Concept (`MAPS_TO_CONCEPT`) and member (`MAPS_TO_MEMBER`) edge linking handled automatically

### JSON Payload Format

Write this to `/tmp/gu_{TICKER}_{SOURCE_ID}.json`:

```json
{
    "source_id": "AAPL_2023-11-03T17.00.00-04.00",
    "source_type": "transcript",
    "ticker": "AAPL",
    "fye_month": 9,
    "items": [
        {
            "label": "Revenue",
            "given_date": "2023-11-02",
            "fiscal_year": 2024,
            "fiscal_quarter": 1,
            "basis_norm": "unknown",
            "segment": "Total",
            "low": 89.0, "mid": null, "high": 93.0,
            "unit_raw": "billion",
            "qualitative": "similar to last year",
            "conditions": null,
            "quote": "We expect revenue...",
            "section": "CFO Prepared Remarks",
            "source_key": "full",
            "derivation": "explicit",
            "basis_raw": null,
            "aliases": [],
            "xbrl_qname": "us-gaap:Revenues",
            "member_u_ids": [],
            "source_refs": []
        }
    ]
}
```

Items do NOT need pre-computed IDs or `period_u_id` — the CLI calls `build_guidance_period_id()` and `build_guidance_ids()` internally. Include `fye_month` at top level when items use LLM period fields instead of pre-computed `period_u_id`.

**`source_refs`**: Array of sub-source node IDs that produced the item. For transcripts, use PreparedRemark ID (`{SOURCE_ID}_pr`) or QAExchange IDs (`{SOURCE_ID}_qa__{sequence}`). For 8-K reports, use exhibit/item IDs if available. Empty array `[]` when no sub-source granularity applies. This enables downstream queries to trace exactly which sub-component of a source yielded the guidance.

**LLM period fields** (optional per item — only needed when `period_u_id` is not pre-computed): `fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_start_year`, `long_range_end_year`, `calendar_override`, `sentinel_class`, `time_type`.

### Invocation

```bash
# Dry-run (validates + computes IDs, no DB connection)
bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_AAPL_source.json --dry-run

# Actual write (MERGE to Neo4j) — env var enables writes without touching config files
ENABLE_GUIDANCE_WRITES=true bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_AAPL_source.json --write
```

### CLI Output (JSON to stdout)

```json
{
    "mode": "dry_run",
    "total": 3,
    "valid": 3,
    "id_errors": [],
    "results": [
        {"id": "gu:...", "dry_run": true, "guidance_id": "guidance:revenue", ...}
    ]
}
```

In `write` mode, each result includes `was_created` (true = new node, false = MERGE update) and edge linking results.

## Output

NEVER output pipe-delimited TSV lines. Return ONLY this structured summary:

```
Items extracted: {count}
Items written (was_created=true): {count}
Items updated (was_created=false): {count}
ID errors: {count} [{details}]
Errors: {count} [{details}]
```

In `dry_run`/`shadow` mode, include per-item IDs and canonical values from CLI output.

If team task assigned, update via TaskUpdate with extraction summary.

## Error Handling

Reference SKILL.md §17 error taxonomy:

| Error | Action |
|-------|--------|
| `SOURCE_NOT_FOUND` / `EMPTY_CONTENT` | Log and return early |
| `NO_GUIDANCE` | Acceptable — return empty extraction |
| `VALIDATION_FAILED` | Skip item, continue with remaining |
| `WRITE_FAILED` | Log error, do not retry |

## Rules

- **100% recall priority** — when in doubt, extract it; false positives > missed guidance
- **Corporate announcements are extractable** — management decisions that allocate specific capital or change shareholder returns (buyback authorizations, dividend declarations, investment announcements) should be extracted even though they announce actions rather than forecast metrics
- **No fabricated numbers** — qualitative guidance uses `implied`/`comparative` derivation
- **News: company guidance only** — ignore analyst estimates ("Est $X", "consensus $Y")
- **No citation = no node** — every GuidanceUpdate MUST have `quote`, `FROM_SOURCE`, `given_date`
- **Quote max 500 chars** — truncate at sentence boundary with "..."
