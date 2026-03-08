# 10-K Asset Split + SOURCE_TYPE Parameter Removal

## Context

The extraction pipeline uses a single `asset=10q` bucket for both 10-Q and 10-K filings. A `canonical_source_type()` function in `trigger-extract.py` remaps 10-K filings to `source_type="10k"` — the only special case in the pipeline. A separate `SOURCE_TYPE` parameter is threaded through SKILL.md → agent shells → pass files to carry this remapped value.

This plan eliminates the special case by making `10k` a first-class asset. After the split, ASSET and source_type are always identical, making the SOURCE_TYPE pipeline parameter dead code. We remove it in the same commit.

**Why single commit**: Zero production data exists (pipeline deployed 2 days ago, worker at 0 replicas, zero 10-K extractions). No backward compatibility concern. No historical backfill needed.

**Key design decisions**:
- Keep section numbers 5A-5H in both query files (no "5K*" renaming — files are namespaced by filename, agent loads only one)
- `source_type` as a **graph property** on GuidanceUpdate nodes stays — it just gets its value from `{ASSET}` directly
- `guidance_writer.py` already has `'10k': 'Report'` in SOURCE_LABEL_MAP — no change needed

---

## Files: 2 creates + 11 edits = 13 total (+ query 5F/5G/5H fix bundled in FILEs 1-4, 7)

| # | File | Action |
|---|------|--------|
| 1 | `.claude/skills/extract/assets/10k.md` | CREATE |
| 2 | `.claude/skills/extract/assets/10k-queries.md` | CREATE |
| 3 | `.claude/skills/extract/assets/10q.md` | EDIT — narrow to 10-Q only |
| 4 | `.claude/skills/extract/assets/10q-queries.md` | EDIT — narrow to 10-Q only |
| 5 | `scripts/trigger-extract.py` | EDIT — split entry, delete function, simplify payload |
| 6 | `scripts/extraction_worker.py` | EDIT — add whitelist entry, remove source_type plumbing |
| 7 | `.claude/skills/extract/types/guidance/primary-pass.md` | EDIT — split routing row, SOURCE_TYPE→ASSET |
| 8 | `.claude/skills/extract/types/guidance/core-contract.md` | EDIT — split routing, add 10k to enum/refs |
| 9 | `.claude/skills/extract/SKILL.md` | EDIT — remove SOURCE_TYPE parameter |
| 10 | `.claude/agents/extraction-primary-agent.md` | EDIT — remove SOURCE_TYPE from parse |
| 11 | `.claude/agents/extraction-enrichment-agent.md` | EDIT — remove SOURCE_TYPE from parse |
| 12 | `.claude/skills/extract/types/guidance/enrichment-pass.md` | EDIT — {SOURCE_TYPE}→{ASSET} |
| 13 | `.claude/skills/extract/queries-common.md` | EDIT — split stale 10-Q/10-K reference |

### Files NOT touched (verified correct as-is)

| File | Why |
|------|-----|
| `guidance_writer.py` | SOURCE_LABEL_MAP already has `'10k': 'Report'` (lines 42-48) |
| `guidance_write_cli.py` | Reads `source_type` from JSON payload — agents will write `{ASSET}` which resolves correctly |
| `guidance-queries.md` | 7E/7F use `gu.source_type` graph property — values unchanged, parameterized by `$source_type` |
| `evidence-standards.md` | No source_type references |
| Intersection files (`transcript-primary.md`, `transcript-enrichment.md`) | No source_type references |

---

## FILE 1: CREATE `assets/10k.md`

Copy `10q.md` and apply these changes:

| Line(s) | Current (10q.md) | New (10k.md) |
|---------|-------------------|--------------|
| 1 | `# 10-Q / 10-K Extraction Profile` | `# 10-K Extraction Profile` |
| 3 | `Per-source extraction rules for 10-Q and 10-K periodic filings. Loaded by the extraction agent when \`ASSET = 10q\`.` | `Per-source profile for 10-K annual filings. Loaded by the extraction agent when \`ASSET = 10k\`.` |
| 7 | `label: 10-Q/10-K` | `label: 10-K` |
| 12 | `10-Q/10-K content comes from multiple layers.` | `10-K content comes from multiple layers.` |
| 12 | `Use the content inventory query (4G) first` | `Use the content inventory query (5F) first` |
| 18+ | (after Filing Text row in Data Structure table) | ADD row: `\| **Exhibits** \| ExhibitContent \| \`Report-[:HAS_EXHIBIT]->\` \| Rare fallback — some 10-K filings have press releases attached \|` |
| 27 | `\`10-Q\` or \`10-K\`` | `\`10-K\`` |
| 48-56 | Both 10-Q (~99%) and 10-K (~98%) coverage sections | Keep ONLY 10-K section. Retitle to `### MD&A Coverage: ~98%` |
| 54 | `The same primary scan path (query 5B) works for both 10-Q and 10-K.` | `The primary scan path (query 5B) works reliably.` |
| 56 | `10-K MD&A uses a different \`section_name\` variant` | `10-K MD&A uses a curly apostrophe (U+2019) \`section_name\` variant` |
| 59 | `Check for exhibits (some 10-K filings have press releases attached)` | `Check for exhibits with query 5H (some 10-K filings have press releases attached)` |
| 61 | `use filing text (query 4F) with keyword-window scanning` | `use filing text (query 5G) with keyword-window scanning` |
| 64-73 | Both MD&A variant rows | Keep ONLY curly apostrophe row (10-K) |
| 66 | `Two naming variants exist for the same section. Query 5B checks both:` | `One naming variant applies to 10-K (curly apostrophe U+2019). Query 5B handles it:` |
| 80-81 | `Run query 4G to see what content types exist` | `Run query 5F to see what content types exist` |
| 85 | `primary scan scope for 10-Q/10-K` | `primary scan scope for 10-K` |
| 97 | `Query 4F. Only if MD&A returned zero guidance` | `Query 5G. Only if MD&A returned zero guidance` |
| 107 | `Zero guidance from a 10-Q/10-K` | `Zero guidance from a 10-K` |
| 152 | `Common Patterns in 10-Q/10-K` | `Common Patterns in 10-K` |
| 169 | `"MD&A" for 10-Q/10-K extractions` | `"MD&A" for 10-K extractions` |
| 171 | (after filing_text source_key sentence) | APPEND: `If from exhibit fallback (query 5H), use the exhibit number (e.g., \`"EX-99.1"\`) as source_key.` |
| 179 | `10-Q/10-K Trap` | `10-K Trap` |
| 183 | `10-Q/10-K Quality Addition` | `10-K Quality Addition` |
| 191 | `10-Q/10-K filings arrive 25-45 days after the earnings event.` | `10-K filings arrive 45-60 days after the fiscal year end.` |
| 195 | `the 10-Q/10-K may contain updated or more precise values` | `the 10-K may contain updated or more precise values` |
| 205 | `MD&A section missing (especially 10-K)` | `MD&A section missing` |
| 207 | `EMPTY_CONTENT\|10q\|MD&A' or 'EMPTY_CONTENT\|10k\|MD&A'` | `EMPTY_CONTENT\|10k\|MD&A` |
| 230-241 | Entire "10-K vs 10-Q Differences" section (12 lines) | DELETE |
| 242 | Version note referencing 10-K and 10-Q fixes | Update to 10-K-only version note |

---

## FILE 2: CREATE `assets/10k-queries.md`

Copy `10q-queries.md` and apply these changes. **Keep section numbers 5A-5E** (no renaming):

| Line(s) | Current (10q-queries.md) | New (10k-queries.md) |
|---------|--------------------------|----------------------|
| 1 | `# 10-Q / 10-K Queries (S5)` | `# 10-K Queries (S5)` |
| 3 | `Source content queries for 10-Q and 10-K filings.` | `Source content queries for 10-K annual filings.` |
| 7 | `## 5. Source Content: 10-Q / 10-K` | `## 5. Source Content: 10-K` |
| 9 | `### 5A. 10-Q/10-K Filing List` | `### 5A. 10-K Filing List` |
| 13 | `r.formType IN ['10-K', '10-Q']` | `r.formType = '10-K'` |
| 20 | `Primary for 10-Q/10-K` | `Primary for 10-K` |
| 22 | `10-Q/10-K guidance extraction` | `10-K guidance extraction` |
| 30 | `**Note**: Two naming variants exist. Check both.` | `**Note**: 10-K uses the curly apostrophe variant (U+2019).` |

Queries 5B-5E are byte-identical (they filter by `accessionNo`, not `formType`).

### Addition: Append queries 5F, 5G, 5H (fixes pre-existing cross-reference bugs)

The 10q.md/10k.md asset profiles reference queries 4F (filing text), 4G (content inventory), and "check for exhibits" (4C), but those only exist in `8k-queries.md`. The agent never loads `8k-queries.md` when `ASSET=10q` or `ASSET=10k`. Add self-contained copies as 5F/5G/5H to both query files.

Append after query 5E in `10k-queries.md`:

```markdown

### 5F. Content Inventory for Report

Quickly check what content types exist before fetching.

\`\`\`cypher
MATCH (r:Report {accessionNo: $accession})
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
RETURN r.accessionNo, r.formType, r.created,
       collect(DISTINCT e.exhibit_number) AS exhibits,
       collect(DISTINCT s.section_name) AS sections,
       collect(DISTINCT fs.statement_type) AS financial_stmts,
       count(DISTINCT ft) AS filing_text_count
\`\`\`

### 5G. Filing Text Content (Fallback)

Fallback when MD&A and financial statement parsing both fail. Average 690KB — large.

\`\`\`cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.content AS content, r.created AS filing_date
\`\`\`

### 5H. Exhibit Content (Fallback)

Fetch exhibit content by number. Use when 5F inventory shows exhibits exist and MD&A is missing. Some 10-K filings have press releases (EX-99.1) attached.

\`\`\`cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = $source_key
RETURN e.content AS content, r.created AS filing_date
\`\`\`
```

---

## FILE 3: EDIT `assets/10q.md`

Narrow to 10-Q only:

| Line(s) | Current | New |
|---------|---------|-----|
| 1 | `# 10-Q / 10-K Extraction Profile` | `# 10-Q Extraction Profile` |
| 3 | `Per-source extraction rules for 10-Q and 10-K periodic filings. Loaded by the extraction agent when \`ASSET = 10q\`.` | `Per-source profile for 10-Q quarterly filings. Loaded by the extraction agent when \`ASSET = 10q\`.` |
| 7 | `label: 10-Q/10-K` | `label: 10-Q` |
| 12 | `10-Q/10-K content comes from multiple layers.` | `10-Q content comes from multiple layers.` |
| 12 | `Use the content inventory query (4G) first` | `Use the content inventory query (5F) first` |
| 18+ | (after Filing Text row in Data Structure table) | ADD row: `\| **Exhibits** \| ExhibitContent \| \`Report-[:HAS_EXHIBIT]->\` \| Rare fallback — some filings have press releases attached \|` |
| 27 | `\`10-Q\` or \`10-K\`` | `\`10-Q\`` |
| 48-56 | Both coverage sections | Keep ONLY 10-Q section. Retitle to `### MD&A Coverage: ~99%` |
| 52-56 | 10-K coverage paragraph | DELETE |
| 58 | `**Fallback for rare missing MD&A** (~2% of 10-K):` | `**Fallback for rare missing MD&A** (~1% of 10-Q):` |
| 59 | `Check for exhibits (some 10-K filings have press releases attached)` | `Check for exhibits with query 5H (some filings have press releases attached)` |
| 61 | `use filing text (query 4F) with keyword-window scanning` | `use filing text (query 5G) with keyword-window scanning` |
| 62 | `Zero guidance from a 10-K is an acceptable result` | `Zero guidance from a 10-Q is an acceptable result` |
| 64-73 | Both MD&A variant rows | Keep ONLY no-apostrophe row (10-Q) |
| 66 | `Two naming variants exist for the same section. Query 5B checks both:` | `One naming variant applies to 10-Q (no apostrophe). Query 5B handles it:` |
| 80-81 | `Run query 4G to see what content types exist` | `Run query 5F to see what content types exist` |
| 85 | `primary scan scope for 10-Q/10-K` | `primary scan scope for 10-Q` |
| 97 | `Query 4F. Only if MD&A returned zero guidance` | `Query 5G. Only if MD&A returned zero guidance` |
| 107 | `Zero guidance from a 10-Q/10-K` | `Zero guidance from a 10-Q` |
| 152 | `Common Patterns in 10-Q/10-K` | `Common Patterns in 10-Q` |
| 169 | `"MD&A" for 10-Q/10-K extractions` | `"MD&A" for 10-Q extractions` |
| 171 | (after filing_text source_key sentence) | APPEND: `If from exhibit fallback (query 5H), use the exhibit number (e.g., \`"EX-99.1"\`) as source_key.` |
| 179 | `10-Q/10-K Trap` | `10-Q Trap` |
| 183 | `10-Q/10-K Quality Addition` | `10-Q Quality Addition` |
| 191 | `10-Q/10-K filings arrive 25-45 days after the earnings event.` | `10-Q filings arrive 25-40 days after the quarter end.` |
| 195 | `the 10-Q/10-K may contain updated or more precise values` | `the 10-Q may contain updated or more precise values` |
| 205 | `MD&A section missing (especially 10-K)` | `MD&A section missing` |
| 207 | both EMPTY_CONTENT variants | `EMPTY_CONTENT\|10q\|MD&A` only |
| 230-241 | Entire "10-K vs 10-Q Differences" section (12 lines) | DELETE |
| 242 | Version note referencing 10-K and 10-Q fixes | Update to 10-Q-only version note |

---

## FILE 4: EDIT `assets/10q-queries.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 1 | `# 10-Q / 10-K Queries (S5)` | `# 10-Q Queries (S5)` |
| 3 | `Source content queries for 10-Q and 10-K filings.` | `Source content queries for 10-Q quarterly filings.` |
| 7 | `## 5. Source Content: 10-Q / 10-K` | `## 5. Source Content: 10-Q` |
| 9 | `### 5A. 10-Q/10-K Filing List` | `### 5A. 10-Q Filing List` |
| 13 | `r.formType IN ['10-K', '10-Q']` | `r.formType = '10-Q'` |
| 20 | `Primary for 10-Q/10-K` | `Primary for 10-Q` |
| 22 | `10-Q/10-K guidance extraction` | `10-Q guidance extraction` |
| 30 | `**Note**: Two naming variants exist. Check both.` | `**Note**: 10-Q uses the no-apostrophe variant.` |

### Addition: Append queries 5F, 5G, 5H (same as FILE 2)

Append after query 5E in `10q-queries.md` — identical content to the 5F/5G/5H added to `10k-queries.md` in FILE 2. Both files get the same three queries.

---

## FILE 5: EDIT `scripts/trigger-extract.py`

### Change 1: Split ASSET_QUERIES entry (line 50)

```python
# BEFORE
"10q":        ("Report",     "r",   "r.formType IN ['10-Q', '10-K']",         ("PRIMARY_FILER", "out")),

# AFTER
"10q":        ("Report",     "r",   "r.formType = '10-Q'",                    ("PRIMARY_FILER", "out")),
"10k":        ("Report",     "r",   "r.formType = '10-K'",                    ("PRIMARY_FILER", "out")),
```

### Change 2: DELETE `canonical_source_type()` (lines 78-88)

Delete the entire function (lines 78-88, including trailing blank line).

### Change 3: Simplify `push_to_queue()` — remove source_type from payload (lines 164-172)

```python
# BEFORE (lines 162-172)
    for item in items:
        ticker = item["symbol"] or item["id"].split("_")[0]
        source_type = canonical_source_type(asset, item.get("form_type"))
        payload = json.dumps({
            "asset": asset,
            "source_type": source_type,
            "ticker": ticker,
            "source_id": item["id"],
            "type": extraction_type,
            "mode": mode,
        })

# AFTER
    for item in items:
        ticker = item["symbol"] or item["id"].split("_")[0]
        payload = json.dumps({
            "asset": asset,
            "ticker": ticker,
            "source_id": item["id"],
            "type": extraction_type,
            "mode": mode,
        })
```

### Change 4: Apply formType filter to `--source-id` lookup (lines 98-104)

The `--source-id` single-source path queries by `MATCH ({alias}:{label} {id: $sid})` without applying `extra_where`. After the split, `--source-id <10Q_ACCESSION> --asset 10k` would find the 10-Q Report node (no formType check), queue it as `asset=10k`, and the run would proceed with the wrong pipeline. This is a real misrouting bug introduced by the split.

```python
# BEFORE (lines 100-104)
        query = (
            f"MATCH ({alias}:{label} {{id: $sid}}) {join_clause} "
            f"RETURN {alias}.id AS id, {ticker_expr} AS symbol, "
            f"       {alias}.{status_prop} AS status, {alias}.formType AS form_type"
        )

# AFTER
        extra_filter = f"WHERE {extra_where}" if extra_where else ""
        query = (
            f"MATCH ({alias}:{label} {{id: $sid}}) {join_clause} {extra_filter} "
            f"RETURN {alias}.id AS id, {ticker_expr} AS symbol, "
            f"       {alias}.{status_prop} AS status, {alias}.formType AS form_type"
        )
```

Zero rows returned → existing "not found" handler at line 106 catches it naturally.

### Change 5 (OPTIONAL): Remove `form_type` from queries (lines 103, 118, 150)

`form_type` was only consumed by `canonical_source_type()`. After deleting that function, `form_type` becomes unused data carried harmlessly through the dict. **Skip this change for minimalism** — the extra column in query results is harmless and avoiding it means not touching query string formatting (trailing commas).

If cleaning up later:
- Line 103: remove `, {alias}.formType AS form_type` (and trailing comma handling)
- Line 118: remove `"form_type": row.get("form_type")` from dict
- Line 150: remove entire `f"{alias}.formType AS form_type "` line (fix trailing comma on line 149)

---

## FILE 6: EDIT `scripts/extraction_worker.py`

### Change 1: Add 10k to ASSET_LABELS (after line 86)

```python
# BEFORE (lines 83-88)
ASSET_LABELS = {
    "transcript": ("Transcript", "t"),
    "8k":         ("Report", "r"),
    "10q":        ("Report", "r"),
    "news":       ("News", "n"),
}

# AFTER
ASSET_LABELS = {
    "transcript": ("Transcript", "t"),
    "8k":         ("Report", "r"),
    "10q":        ("Report", "r"),
    "10k":        ("Report", "r"),
    "news":       ("News", "n"),
}
```

### Change 2: Update docstring — remove source_type from example payload + add 10k to assets (lines 10-21)

```python
# BEFORE (lines 10-21)
Payload format (JSON) — one message = one job:
  {
      "asset": "transcript",
      "source_type": "transcript",
      "ticker": "AAPL",
      "source_id": "AAPL_2025-01-30T17.00",
      "type": "guidance",
      "mode": "write"
  }

Supported types: guidance, analyst, announcement
Supported assets: transcript, 8k, 10q, news

# AFTER
Payload format (JSON) — one message = one job:
  {
      "asset": "transcript",
      "ticker": "AAPL",
      "source_id": "AAPL_2025-01-30T17.00",
      "type": "guidance",
      "mode": "write"
  }

Supported types: guidance, analyst, announcement
Supported assets: transcript, 8k, 10q, 10k, news
```

### Change 3: Remove `source_type` from `process_one()` signature (lines 208-216)

```python
# BEFORE
async def process_one(
    ticker: str,
    asset: str,
    source_type: str,
    source_id: str,
    type_name: str,
    mode: str,
    mgr,
) -> bool:

# AFTER
async def process_one(
    ticker: str,
    asset: str,
    source_id: str,
    type_name: str,
    mode: str,
    mgr,
) -> bool:
```

### Change 4: Remove SOURCE_TYPE from prompt string (line 230)

```python
# BEFORE
prompt = f"/extract {ticker} {asset} {source_id} TYPE={type_name} MODE={mode} SOURCE_TYPE={source_type} RESULT_PATH={result_path}"

# AFTER
prompt = f"/extract {ticker} {asset} {source_id} TYPE={type_name} MODE={mode} RESULT_PATH={result_path}"
```

### Change 5: Remove source_type from payload parsing and process_one call (lines 419, 424)

```python
# BEFORE (lines 417-424)
            ticker = payload["ticker"]
            asset = payload["asset"]
            source_type = payload.get("source_type", asset)
            source_id = payload["source_id"]
            type_name = payload["type"]
            mode = payload.get("mode", DEFAULT_MODE)

            success = await process_one(ticker, asset, source_type, source_id, type_name, mode, mgr)

# AFTER
            ticker = payload["ticker"]
            asset = payload["asset"]
            source_id = payload["source_id"]
            type_name = payload["type"]
            mode = payload.get("mode", DEFAULT_MODE)

            success = await process_one(ticker, asset, source_id, type_name, mode, mgr)
```

---

## FILE 7: EDIT `types/guidance/primary-pass.md`

### Change 1: Routing header (line 26)

```
# BEFORE
Route by `SOURCE_TYPE` to correct query section (asset-queries):

# AFTER
Route by `ASSET` to correct query section (asset-queries):
```

### Change 2: Rename column header + split routing table row + fix query references (lines 28, 32)

```
# BEFORE (line 28)
| Source Type | Primary | Fallbacks |

# AFTER
| Asset | Primary | Fallbacks |
```

```
# BEFORE (line 32)
| `10q` / `10k` | 5B (MD&A) | 5C (financial stmts), 4F (fallback) |

# AFTER
| `10q` | 5F (inventory) → 5B (MD&A) | 5C (financial stmts), 5H (exhibits), 5G (filing text) |
| `10k` | 5F (inventory) → 5B (MD&A) | 5C (financial stmts), 5H (exhibits), 5G (filing text) |
```

Note: Now matches the 8k row pattern (inventory-first). 4F→5G, 4G→5F, exhibit fallback→5H. All defined in 10q/10k-queries.md (FILEs 2, 4).

### Change 3: Rewrite source_type instruction (line 201)

```
# BEFORE
**`source_type`**: Use `{SOURCE_TYPE}` from your input arguments (not `{ASSET}`). These differ for 10-K filings routed through the `10q` asset pipeline.

# AFTER
**`source_type`**: Use `{ASSET}` — this is the source type identity written to the graph.
```

---

## FILE 8: EDIT `types/guidance/core-contract.md`

### Change 1: Split routing table (line 524)

```
# BEFORE
| `10q`, `10k` | [10q.md](../../assets/10q.md) |

# AFTER
| `10q` | [10q.md](../../assets/10q.md) |
| `10k` | [10k.md](../../assets/10k.md) |
```

### Change 2: Add 10k to ASSET enum (line 651)

```
# BEFORE
| `ASSET` | Enum | `transcript`, `8k`, `news`, `10q` |

# AFTER
| `ASSET` | Enum | `transcript`, `8k`, `news`, `10q`, `10k` |
```

### Change 3: Split empty content row (line 699)

```
# BEFORE
| `10q`/`10k` | MD&A section `strip() == ""` |

# AFTER
| `10q` | MD&A section `strip() == ""` |
| `10k` | MD&A section `strip() == ""` |
```

### Change 4: Add 10k to reference files table (after lines 719, 723)

```
# ADD after line 719:
| [10k-queries.md](../../assets/10k-queries.md) | 10-K fetch queries |

# ADD after line 723:
| [10k.md](../../assets/10k.md) | 10-K asset profile |
```

### Change 5: Update existing 10q references to be 10-Q-only (lines 719, 723)

```
# BEFORE
| [10q-queries.md](../../assets/10q-queries.md) | 10-Q/10-K fetch queries |
| [10q.md](../../assets/10q.md) | 10-Q/10-K asset profile |

# AFTER
| [10q-queries.md](../../assets/10q-queries.md) | 10-Q fetch queries |
| [10q.md](../../assets/10q.md) | 10-Q asset profile |
```

### Change 6: Routing instruction + table header (lines 517, 519)

```
# BEFORE (line 517)
Extraction MUST route by `source_type` before LLM processing. Each type has different scan scope and noise profiles. Per-source profiles in `reference/`:

# AFTER (swap `source_type` → asset type, rest of line unchanged)
Extraction MUST route by asset type before LLM processing. Each type has different scan scope and noise profiles. Per-source profiles in `reference/`:
```

```
# BEFORE (line 519)
| Source Type | Asset Profile |

# AFTER
| Asset | Asset Profile |
```

Note: L528 `source_type` column header in Source Type Mapping table stays — it documents the GuidanceUpdate.source_type **graph field**, not the pipeline parameter.

---

## FILE 9: EDIT `SKILL.md`

### Change 1: Remove SOURCE_TYPE from parse line (line 5)

```
# BEFORE
Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} [SOURCE_TYPE={SOURCE_TYPE}] [RESULT_PATH={PATH}]`

# AFTER
Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} [RESULT_PATH={PATH}]`
```

### Change 2: Remove SOURCE_TYPE default (line 7)

```
# BEFORE
Defaults: `MODE=dry_run`, `SOURCE_TYPE={ASSET}`

# AFTER
Defaults: `MODE=dry_run`
```

### Change 3: Remove SOURCE_TYPE from primary agent spawn (line 14)

```
# BEFORE
Agent(subagent_type=extraction-primary-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} SOURCE_TYPE={SOURCE_TYPE}

# AFTER
Agent(subagent_type=extraction-primary-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

### Change 4: Remove SOURCE_TYPE from enrichment agent spawn (line 30)

```
# BEFORE
Agent(subagent_type=extraction-enrichment-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} SOURCE_TYPE={SOURCE_TYPE}

# AFTER
Agent(subagent_type=extraction-enrichment-agent): {TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}
```

---

## FILE 10: EDIT `extraction-primary-agent.md`

### Change 1: Remove SOURCE_TYPE from parse line (line 29)

```
# BEFORE
Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} SOURCE_TYPE={SOURCE_TYPE}`

# AFTER
Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}`
```

---

## FILE 11: EDIT `extraction-enrichment-agent.md`

### Change 1: Remove SOURCE_TYPE from parse line (line 30)

```
# BEFORE
Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE} SOURCE_TYPE={SOURCE_TYPE}`

# AFTER
Parse `$ARGUMENTS` as: `{TICKER} {ASSET} {SOURCE_ID} TYPE={TYPE} MODE={MODE}`
```

---

## FILE 12: EDIT `types/guidance/enrichment-pass.md`

### Change 1: 7F instruction (line 35)

```
# BEFORE
**Prior-source baseline (query 7F)**: Load all labels previously extracted from this company's sources of this asset type, with frequency and last-seen date. Pass `$source_type = {SOURCE_TYPE}` (the SOURCE_TYPE argument from your input). Used in the completeness check (Step 5).

# AFTER
**Prior-source baseline (query 7F)**: Load all labels previously extracted from this company's sources of this asset type, with frequency and last-seen date. Pass `$source_type = {ASSET}`. Used in the completeness check (Step 5).
```

### Change 2: JSON payload source_type (line 85)

```
# BEFORE
    "source_type": "{SOURCE_TYPE}",

# AFTER
    "source_type": "{ASSET}",
```

---

## FILE 13: EDIT `queries-common.md`

### Change 1: Split stale 10-Q/10-K reference in execution order (line 307)

```
# BEFORE
   - 5A with null dates (All 10-Q/10-K filings) → for each: 5B (MD&A)

# AFTER
   - 5A with null dates (All 10-Q filings) → for each: 5B (MD&A)
   - 5A with null dates (All 10-K filings) → for each: 5B (MD&A)
```

Post-split, each asset has its own 5A with a narrowed formType filter. A single 5A call no longer returns both form types.

---

## Verification Checklist

### Pipeline Parameter Removal
- [ ] `grep -ri "SOURCE_TYPE" .claude/skills/extract/ .claude/agents/extraction-*` returns ZERO matches
- [ ] `grep "SOURCE_TYPE" scripts/extraction_worker.py scripts/trigger-extract.py` returns ZERO matches
- [ ] `grep "canonical_source_type" scripts/trigger-extract.py` returns ZERO matches
- [ ] `extraction_worker.py` docstring example payload has no `"source_type"` key
- [ ] `extraction_worker.py` docstring says "Supported assets: transcript, 8k, 10q, 10k, news"
- [ ] `core-contract.md` L517 says "route by asset type" not "route by `source_type`"

### Asset Split Correctness
- [ ] `10q-queries.md` 5A: `r.formType = '10-Q'` (not IN clause)
- [ ] `10k-queries.md` 5A: `r.formType = '10-K'` (not IN clause)
- [ ] `10q.md`: zero "10-K" references (except maybe MD&A section name variant context)
- [ ] `10k.md`: zero "10-Q" references
- [ ] Both query files use same section numbers (5A, 5B, 5C, 5D, 5E, 5F, 5G, 5H)
- [ ] `trigger-extract.py` ASSET_QUERIES has both `"10q"` and `"10k"` entries
- [ ] `extraction_worker.py` ASSET_LABELS has both `"10q"` and `"10k"` entries

### 5F/5G/5H Query Fix (4F/4G/4C cross-reference bug)
- [ ] `10q-queries.md` has queries 5F (content inventory), 5G (filing text fallback), 5H (exhibit content)
- [ ] `10k-queries.md` has queries 5F (content inventory), 5G (filing text fallback), 5H (exhibit content)
- [ ] `grep "4F\|4G" .claude/skills/extract/assets/10q.md .claude/skills/extract/assets/10k.md` returns ZERO matches
- [ ] `grep "4F\|4G" .claude/skills/extract/types/guidance/primary-pass.md` returns ZERO matches for 10q/10k rows (4F→5G, 4G only in 8k row)
- [ ] 5F Cypher matches 4G from `8k-queries.md` (same OPTIONAL MATCH pattern)
- [ ] 5G Cypher matches 4F from `8k-queries.md` (same HAS_FILING_TEXT pattern)
- [ ] 5H Cypher matches 4C from `8k-queries.md` (same HAS_EXHIBIT pattern)

### Graph Field Preserved
- [ ] `source_type` field still in core-contract.md schema (line 127) — UNCHANGED
- [ ] Query 7E still returns `gu.source_type` — UNCHANGED
- [ ] Query 7F still filters by `gu.source_type = $source_type` — UNCHANGED
- [ ] Primary-pass.md line 201 tells agent to set `source_type = {ASSET}` in JSON
- [ ] Enrichment-pass.md line 85 sets `"source_type": "{ASSET}"` in JSON
- [ ] `guidance_writer.py` SOURCE_LABEL_MAP has `'10k': 'Report'` — UNCHANGED (already exists)

### Historical Data — Pre-Split 10-K Guidance Check

Before committing, verify no historical 10-K guidance was written with wrong source_type:

```cypher
// Run via Neo4j bolt (port 30687) or MCP
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(r:Report)
WHERE r.formType = '10-K' AND gu.source_type = '10q'
RETURN count(gu) AS mismatched_rows
```

**Expected: 0 rows** (pipeline deployed 2 days ago, worker at 0 replicas, zero production extractions).

If non-zero, run this backfill BEFORE the code changes:
```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(r:Report)
WHERE r.formType = '10-K' AND gu.source_type = '10q'
SET gu.source_type = '10k'
RETURN count(gu) AS fixed_rows
```

### End-to-End Dry Run

```bash
# Test 10-Q extraction
python3 scripts/trigger-extract.py --source-id <10Q_ACCESSION> --asset 10q --type guidance --mode dry_run

# Test 10-K extraction
python3 scripts/trigger-extract.py --source-id <10K_ACCESSION> --asset 10k --type guidance --mode dry_run

# Negative test: mismatched asset/formType must be rejected
# This MUST print "Report not found" and return 0 items (not queue the wrong asset)
python3 scripts/trigger-extract.py --source-id <10Q_ACCESSION> --asset 10k --type guidance --mode dry_run
python3 scripts/trigger-extract.py --source-id <10K_ACCESSION> --asset 10q --type guidance --mode dry_run

# Verify payloads in queue (inspect without consuming)
redis-cli -p 31379 LRANGE extract:pipeline 0 -1
```

---

## 4F/4G/4C → 5F/5G/5H Query Fix

The `10q.md` and `10k.md` asset profiles reference queries 4F (filing text), 4G (content inventory), and "check for exhibits" (4C), but those only exist in `8k-queries.md`. The agent never loads that file when `ASSET=10q` or `ASSET=10k` — so the agent has no definitions for these queries. Fixed in this plan by:

1. Adding self-contained 5F (content inventory), 5G (filing text), and 5H (exhibit content) queries to both `10q-queries.md` and `10k-queries.md` (FILEs 2, 4)
2. Updating all 4G→5F, 4F→5G references and adding 5H exhibit references in `10q.md` and `10k.md` (FILEs 1, 3)
3. Updating the `primary-pass.md` routing table to include 5F inventory step, 5H exhibits, and 5G filing text (FILE 7)

---

## Rollback

```bash
git revert <commit>   # one command undoes all 13 files
```

---

## Commit Message

```
Split 10q into separate 10q/10k assets, remove SOURCE_TYPE parameter, fix 4F/4G/4C query gap
```
