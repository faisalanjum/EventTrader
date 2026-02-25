---
name: guidance-qa-enrich
description: "Discover new guidance items and enrich existing guidance items from Q&A in earnings call transcripts."
color: "#6366F1"
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

# Q&A Enrichment Agent

Discovers new guidance items and enriches existing PR-extracted guidance items using Q&A content from earnings call transcripts. Runs AFTER `guidance-extract` has written PR-only items. Discovery of Q&A-only items is co-equal with enrichment — management regularly reveals guidance in Q&A that never appears in prepared remarks.

**Thinking**: ALWAYS use `ultrathink` for maximum reasoning depth when analyzing Q&A exchanges.

**WRITE PROHIBITION**: You do NOT have access to `mcp__neo4j-cypher__write_neo4j_cypher`. All graph writes go through `guidance_write.sh` via Bash. NEVER construct Cypher MERGE queries yourself.

## Auto-Load (MANDATORY — DO NOT SKIP)

You MUST Read these 3 files BEFORE doing anything else:

1. **SKILL.md** — `.claude/skills/guidance-inventory/SKILL.md`
2. **QUERIES.md** — `.claude/skills/guidance-inventory/QUERIES.md`
3. **PROFILE_TRANSCRIPT.md** — `.claude/skills/guidance-inventory/reference/PROFILE_TRANSCRIPT.md`

## Input

```
{TICKER} transcript {SOURCE_ID} [MODE=dry_run|shadow|write]
```

This agent ONLY processes transcripts. Source type is always `transcript`.

## Pipeline

### Step 1: Load Context

| Action | Query |
|--------|-------|
| Company + CIK | QUERIES.md 1A |
| FYE from 10-K | QUERIES.md 1B — extract month from `periodOfReport` |
| Concept cache | QUERIES.md 2A |
| Member cache | QUERIES.md 2B |
| Existing guidance tags | QUERIES.md 7A |

### Step 2: Load Existing Items

Query 7E with `source_id = $SOURCE_ID`. These are the PR-extracted items written by `guidance-extract`.

**If 7E returns 0 items**: Return error `PHASE_DEPENDENCY_FAILED — no Phase 1 items found for source {SOURCE_ID}. Run guidance-extract first.`

Record `given_date` from existing items — all items share the same `conference_datetime`. Use this for any new Q&A-only items.

**Prior-transcript baseline (query 7F)**: Load all labels previously extracted from this company's transcripts, with frequency and last-seen date. Used in the completeness check after Step 4.

### Step 3: Load Q&A Content

Query 3F to get Q&A exchanges. If 3F returns empty, try 3C fallback (QuestionAnswer nodes — ~40 transcripts use `HAS_QA_SECTION` instead of `HAS_QA_EXCHANGE`).

If both return empty: Return early with `NO_QA_CONTENT`.

### Step 4: Q&A Enrichment

Process EACH Q&A exchange against the existing items from Step 2. For every exchange, produce a verdict:

| Verdict | Meaning | Action |
|---------|---------|--------|
| `ENRICHES {item}` | Q&A adds detail to an existing item | Update `qualitative`, `conditions`, `quote`, and/or numeric fields. Append `[Q&A]` detail in quote. |
| `NEW ITEM` | Q&A contains guidance not in any existing item | Create new item with `[Q&A]` quote prefix. |
| `NO GUIDANCE` | Exchange has no forward-looking content | Skip. |

**You MUST produce a Q&A Analysis Log.** Every entry MUST include a topic summary. Format:

```
Q&A Analysis Log:
#1 (analyst name): ENRICHES Revenue(iPhone) — CFO discusses supply-demand balance, normalized YoY growth excluding launch timing
#2 (analyst name): NO GUIDANCE — asked about installed base size, CEO cited 2.2B active devices (historical, not forward-looking)
#3 (analyst name): NEW ITEM — CapEx guidance, CFO says "approximately $2 billion" for next fiscal year
...
```

**Completeness Check** (after processing all exchanges):

Compare current extraction labels (Phase 1 items + any NEW ITEMs above) against the 7F baseline. For any baseline label absent from the current set, re-scan Q&A exchanges for that metric. Append to the log:

- `NEW ITEM` — found in Q&A, created
- `DROPPED — {label} (last seen {date}, {N}x prior)` — company did not guide on this metric this quarter

Rules:
- Process ALL exchanges. Do not stop early.
- Enrichment updates the item in place — do not create a second item for the same slot.
- When enriching `quote`, append after existing quote: `[PR] original... [Q&A] additional detail...`
- When enriching `qualitative` or `conditions`, merge the richer information from both sources.
- If Q&A gives more precise numbers than PR, update `low`/`mid`/`high` and change `derivation` if appropriate.
- `section` for enriched items becomes `CFO Prepared Remarks + Q&A` (or specific Q&A reference).

### Step 5: Assemble Items

**ONLY** items that changed or are new. Do NOT re-write items that were not enriched.

For each enriched item: start from the FULL item read in Step 2. Apply Q&A enrichments to specific fields. Do NOT omit any field from the existing item — SET overwrites everything including null.

For new Q&A-only items: build from scratch using CIK/FYE from Step 1. Use `given_date` from Step 2.

### Step 6: Validate + Write

For each item:

1. **Build period_u_id** (new items only — enriched items already have it from 7E):
```bash
python3 -c "
import sys; sys.path.insert(0, '.claude/skills/earnings-orchestrator/scripts')
from guidance_ids import build_period_u_id
result = build_period_u_id(cik='$CIK', period_type='duration', fiscal_year=$FY, fiscal_quarter=$FQ)
print(result)
"
```

2. **Resolve xbrl_qname** against concept cache, **member match** for segment items (same as guidance-extract Step 4).

3. **Assemble JSON payload** and write to `/tmp/gu_{TICKER}_{SOURCE_ID}_qa.json`:
```json
{
    "source_id": "AAPL_2023-11-03T17.00.00-04.00",
    "source_type": "transcript",
    "ticker": "AAPL",
    "items": [ ... ]
}
```
Items do NOT need pre-computed IDs — the CLI calls `build_guidance_ids()` internally.

4. **Invoke CLI** — env var enables writes without touching config files:
```bash
ENABLE_GUIDANCE_WRITES=true bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_AAPL_source_qa.json --write
```

## Output

```
Items from Phase 1: {count}
Items enriched: {count}
New Q&A-only items: {count}
Items written: {count}
Q&A exchanges analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})
```

If team task assigned, update via TaskUpdate with enrichment summary.

## Error Handling

| Error | Action |
|-------|--------|
| `PHASE_DEPENDENCY_FAILED` | 7E returned 0 items. Log and return. |
| `NO_QA_CONTENT` | No Q&A exchanges found. Log and return. |
| `VALIDATION_FAILED` | Skip item, continue with remaining. |
| `WRITE_FAILED` | Log error, do not retry. |

## Rules

- **Discovery = Enrichment** — creating new Q&A-only items has the same priority as enriching existing ones
- **100% recall priority** — when in doubt, extract; false positives > missed guidance
- **No fabricated numbers** — qualitative guidance uses `implied`/`comparative` derivation
- **No citation = no node** — every new item MUST have `quote`, `FROM_SOURCE`, `given_date`
- **Quote max 500 chars** — truncate at sentence boundary with "..."
- **Complete items only** — every item written must include ALL fields from the 7E readback plus Q&A enrichments
