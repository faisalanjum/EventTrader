# Primary Pass Working Brief — Guidance Extraction

This is your complete working brief. Follow it start to finish. core-contract.md is reference for schema details.

## Scope

Extract from primary section only (prepared remarks for transcripts, full content for other assets).

---

## Pipeline Steps

### STEP 1: FETCH — Load Context

| Action | Query |
|--------|-------|
| Company + CIK | QUERIES.md 1A |
| FYE from 10-K | QUERIES.md 1B — extract month from `periodOfReport` |
| Concept cache | QUERIES.md 2A |
| Member cache | QUERIES.md 2B |
| Existing guidance tags | QUERIES.md 7A |
| Prior extractions for this source | QUERIES.md 7D — if count > 0, log warning: "Source has {N} existing items — re-run will only add items with new values" |

### STEP 2: FETCH SOURCE — Route by Asset Type

Route by `SOURCE_TYPE` to correct query section (asset-queries):

| Source Type | Primary | Fallbacks |
|-------------|---------|-----------|
| `transcript` | 3B (structured) | 3C (Q&A Section), 3D (full text) |
| `8k` | 4G (inventory) → 4C (exhibit) | 4E (section), 4F (filing text) |
| `10q` / `10k` | 5B (MD&A) | 5C (financial stmts), 4F (fallback) |
| `news` | 6A (single item) | 6B (channel-filtered batch) |

Apply empty-content rules (core-contract.md S17).

**For transcripts**: Extract from Prepared Remarks only. Full Q&A analysis is handled by the enrichment pass. Only use `qa_exchanges` from 3B as fallback if prepared remarks are truncated or empty. If 3B result is truncated by the MCP tool, re-run the query via Bash+Python and save to `/tmp` for parsing.

### STEP 3: EXTRACT — LLM Extraction

Apply per-source profile rules, quality filters, and existing Guidance tags (from Step 1) to reuse canonical metric names.

See Extraction Rules below.

### STEP 4: VALIDATE — Deterministic Validation (MANDATORY — use scripts, not LLM math)

You MUST invoke `guidance_ids.py` via Bash for EVERY extracted item. Do not compute IDs, canonicalize units, or build period IDs yourself. For each item:

1. **Period routing** — include LLM period fields in JSON payload; the CLI computes `period_u_id` (gp_ format) via `build_guidance_period_id()`. Or compute explicitly via Bash (see Bash Templates below).
2. **Canonicalize unit + values** — `guidance_ids.py` via Bash
3. **Validate basis** — explicit-only qualifier from quote span, otherwise `unknown`
4. **Resolve `xbrl_qname`** — match against concept cache (core-contract.md S11)
5. **Member match** — for each item where segment != 'Total', scan the member cache from Step 1, match segment name to member name (case-insensitive, ignore 'Member' suffix), and add matched `u_id` to `member_u_ids`
6. **Compute deterministic IDs** — `guidance_ids.py:build_guidance_ids()` via Bash

If uncertain on XBRL/member: keep core item, set `xbrl_qname=null`, skip member edges.

### STEP 5: WRITE — Batch Write via guidance_write.sh

1. Assemble ALL extracted items into a single JSON payload (see JSON Payload Format below)
2. Write JSON to `/tmp/gu_{TICKER}_{SOURCE_ID}.json`
3. Call `guidance_write.sh` via Bash
4. Parse returned JSON for results summary

This is a batch operation — one Write + one Bash call for ALL items. Do not write items individually.

---

## Extraction Rules

### Metric Decomposition

Split qualified metrics into base `label` + `segment`. Business dimensions (product, geography, business unit) become `segment`; the base metric stays as `label`. Accounting modifiers (Cost of, Net, Adjusted, Pro Forma) stay part of `label`.

**Simple test**: Could you have this metric for iPhone AND for Total? If yes, the prefix is a segment — decompose. If the prefix changes the financial definition, keep it whole.

### Basis Rules

`basis_norm` is assigned ONLY when the basis qualifier is explicit in the same sentence/span as the guidance value. Otherwise default to `unknown`.

### Segment Rules

Default segment is `Total`. Set segment only when text qualifies a metric with a business dimension.

### Quality / Acceptance Filters

- **Forward-looking only** — target period must be after source date. Past-period results are actuals, not guidance.
- **Specificity required** — qualitative guidance needs a quantitative anchor: "low single digits", "double-digit", "mid-teens". Skip vague terms ("significant", "strong") without magnitude.
- **No fabricated numbers** — if guidance is qualitative, use `derivation=implied`/`comparative`. Never invent numeric values.
- **Quote max 500 chars** — truncate at sentence boundary with "..." if needed. No citation = no node.
- **100% recall priority** — when in doubt, extract it. False positives > missed guidance.
- **Corporate announcements ARE extractable** — management decisions that allocate specific capital or change shareholder returns (buyback authorizations, dividend declarations, investment announcements) should be extracted.
- **News: company guidance only** — ignore analyst estimates ("Est $X", "consensus $Y"). Extract only company-issued guidance.
- **Factors are conditions, not items** — if a forward-looking statement quantifies a factor affecting another guided metric (e.g., FX headwind, week count), capture it in that metric's `conditions` field — not as a standalone item.

### Numeric Value Rules

Copy the number and unit exactly as printed in the source text. `"$10.3 billion"` → `low=10.3, unit_raw="billion"`. Never convert between units — the canonicalizer handles all scaling.

### LLM Period Extraction Fields

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

### Fiscal Context Rule

In earnings calls and SEC filings, ALL period references are fiscal unless explicitly stated as calendar. "Second half" = fiscal H2. Only use calendar interpretation when text explicitly says "calendar year/quarter" — set `calendar_override: true`.

### Resolution Priority

Always prefer the most specific `period_scope` with determinable dates. Sentinel only when dates are genuinely not determinable. "By 2028" -> `long_range` (has year), NOT `long_term`. "Long-term margin model" -> `long_term` (no year).

### Quote / Citation Requirements

- Max 500 chars, truncate at sentence boundary with "..."
- No citation = no node — every GuidanceUpdate MUST have `quote`, `FROM_SOURCE`, `given_date`

---

## Bash Templates

### build_guidance_period_id

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

### build_guidance_ids

```bash
python3 -c "
import sys; sys.path.insert(0, '.claude/skills/earnings-orchestrator/scripts')
from guidance_ids import build_guidance_ids; import json
result = build_guidance_ids(label='$LABEL', source_id='$SOURCE_ID', period_u_id='$PERIOD_UID', basis_norm='$BASIS', segment='$SEGMENT', low=$LOW, mid=$MID, high=$HIGH, unit_raw='$UNIT', qualitative=$QUALITATIVE, conditions=$CONDITIONS)
print(json.dumps(result))
"
```

Returns: `{"guidance_id": "...", "guidance_update_id": "...", "evhash16": "...", "canonical_unit": "...", ...}`

---

## JSON Payload Format

Write to `/tmp/gu_{TICKER}_{SOURCE_ID}.json`:

```json
{
    "source_id": "AAPL_2023-11-03T17.00",
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

**`source_type`**: Use `{SOURCE_TYPE}` from your input arguments (not `{ASSET}`). These differ for 10-K filings routed through the `10q` asset pipeline.

Items do NOT need pre-computed IDs or `period_u_id` — the CLI calls `build_guidance_period_id()` and `build_guidance_ids()` internally. Include `fye_month` at top level when items use LLM period fields instead of pre-computed `period_u_id`.

**`source_refs`**: Array of sub-source node IDs that produced the item. For transcripts, use PreparedRemark ID (`{SOURCE_ID}_pr`) or QAExchange IDs (`{SOURCE_ID}_qa__{sequence}`). For 8-K reports, use exhibit/item IDs if available. Empty array `[]` when no sub-source granularity applies.

**LLM period fields** (optional per item — only needed when `period_u_id` is not pre-computed): `fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_start_year`, `long_range_end_year`, `calendar_override`, `sentinel_class`, `time_type`.

---

## CLI Invocation

```bash
# Dry-run (validates + computes IDs, no DB connection)
bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_{TICKER}_{SOURCE_ID}.json --dry-run

# Actual write (MERGE to Neo4j) — env var enables writes without touching config files
ENABLE_GUIDANCE_WRITES=true bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_{TICKER}_{SOURCE_ID}.json --write
```

---

## Output Format

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

---

## Result File

Write `/tmp/extract_pass_{TYPE}_primary_{SOURCE_ID}.json` with status, counts.
