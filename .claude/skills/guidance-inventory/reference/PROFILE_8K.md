# 8-K Extraction Profile

Per-source extraction rules for 8-K earnings filings. Loaded by the guidance extraction agent when `SOURCE_TYPE = 8k`.

## Data Structure

8-K earnings content comes from multiple layers. Use the content inventory query (4G) first to determine what exists.

| Layer | Node Label | Relationship | Priority |
|-------|-----------|--------------|----------|
| **Exhibit** | ExhibitContent | `Report-[:HAS_EXHIBIT]->` | Primary — 93% of Item 2.02 filings have EX-99.1 |
| **Section** | ExtractedSectionContent | `Report-[:HAS_SECTION]->` | Secondary — Item 2.02/7.01 text |
| **Filing Text** | FilingTextContent | `Report-[:HAS_FILING_TEXT]->` | Fallback — full filing, avg 690KB |

### Report Metadata (from Report node)

| Field | Type | Example |
|-------|------|---------|
| `r.accessionNo` | String | `0000320193-25-000008` |
| `r.id` | String | Same as accessionNo |
| `r.created` | String (ISO) | `2025-01-30T16:30:00Z` |
| `r.formType` | String | `8-K` |
| `r.items` | String (JSON) | `Item 2.02, Item 9.01` |
| `r.market_session` | String | `after_hours`, `pre_market`, `regular` |
| `r.periodOfReport` | String | `2025-01-25` |

### ExhibitContent Fields

| Field | Type | Description |
|-------|------|-------------|
| `e.exhibit_number` | String | `EX-99.1`, `EX-99.2`. Note: dirty variants exist (`EX-99.01`, `EX-99.-1`) |
| `e.content` | String | Full exhibit text. Press releases avg 10-50KB. |

### ExtractedSectionContent Fields

| Field | Type | Description |
|-------|------|-------------|
| `s.section_name` | String | Canonical section key (see table below) |
| `s.content` | String | Section text content |

---

## Content Fetch Order

Fetch content in this priority order. Primary layer (EX-99.1) takes precedence; check secondary layers for additional metrics not covered by the primary.

### Step 1: Check Content Inventory

Run query 4G to see what exists:
```
exhibits, sections, financial_stmts, filing_text_count
```

### Step 2: Fetch EX-99.1 (Primary)

Query 4C with `source_key = 'EX-99.1'`. This is the press release — the richest source for 8-K guidance.

If EX-99.1 is missing, check EX-99.2 (presentation). Discovery query 4D lists all exhibits.

**Dirty exhibit numbers**: Some filings use non-standard exhibit numbering (`EX-99.01`, `EX-99.-1`). If exact match on `EX-99.1` fails, use query 4D to discover actual exhibit numbers and match the closest.

### Step 3: Fetch Section Text (Secondary)

Query 4E for the relevant section. Key `section_name` values for 8-K:

| section_name | 8-K Item | Content |
|-------------|----------|---------|
| `ResultsofOperationsandFinancialCondition` | Item 2.02 | Earnings announcement text |
| `RegulationFDDisclosure` | Item 7.01 | Mid-quarter updates, pre-announcements |
| `OtherEvents` | Item 8.01 | Material events, strategic updates |
| `FinancialStatementsandExhibits` | Item 9.01 | Exhibit index (rarely useful for guidance) |

### Step 4: Filing Text (Fallback)

Query 4F. Only if exhibit and section both failed or yielded zero guidance. This is the full filing text (~690KB avg) — scan with keyword windows, not full LLM processing.

---

## Scan Scope

### Exhibit (EX-99.1 Press Release)

Press releases have a consistent structure. Scan in this order:

| Section | What to Look For | Priority |
|---------|-----------------|----------|
| **Outlook / Guidance** | Explicit forward-looking section, usually near bottom | Highest |
| **Tables** | Revenue/EPS/margin projections, often GAAP vs non-GAAP side by side | High |
| **Footnotes** | GAAP/non-GAAP reconciliation, basis clarification | Medium |
| **Opening paragraphs** | Summary with key numbers (may mix actuals and guidance) | Medium |
| **Safe harbor** | Skip boilerplate, but keep adjacent concrete guidance | Filter |

### Section Text (Item 2.02 / 7.01)

Usually shorter than exhibits. Often duplicates exhibit content in condensed form. May contain additional context not in the exhibit.

### Pre-Announcements (Item 7.01 / 8.01)

Mid-quarter guidance updates — often market-moving. These filings may:
- Raise/lower existing guidance
- Provide preliminary results
- Announce special items affecting outlook

Query 4B finds these. Same extraction rules apply but be especially attentive to revision language.

---

## What to Extract

| Signal | Example | Extract? |
|--------|---------|----------|
| Explicit range | "We expect Q2 revenue of $94-98 billion" | Yes: `derivation=explicit`, low=94000, high=98000 |
| Point guidance | "CapEx of approximately $2 billion" | Yes: `derivation=point`, mid=2000 |
| Table projections | Revenue guidance row: `$94B - $98B` | Yes: extract from table context |
| GAAP vs non-GAAP pair | "GAAP EPS $3.20; non-GAAP EPS $3.50" | Yes: extract BOTH with appropriate `basis_norm` |
| Growth rate guidance | "Revenue growth of 5-7% year-over-year" | Yes: `unit=percent_yoy`, low=5, high=7 |
| Margin guidance | "Gross margin between 46.5% and 47.5%" | Yes: `unit=percent`, low=46.5, high=47.5 |
| Floor/ceiling | "At least $150M in free cash flow" | Yes: `derivation=floor`, low=150 |
| Qualitative direction | "We see continued momentum" | No: lacks quantitative anchor |
| Prior quarter results | "Q1 revenue was $124 billion" | No: past period, not forward guidance |
| Safe harbor only | "Forward-looking statements involve risks..." | No: boilerplate disclaimer |

---

## Do NOT Extract

1. **Pure actuals** — past period results with no forward component
2. **Pure safe-harbor boilerplate** — but keep concrete guidance adjacent to disclaimers (§3 safe-harbor proximity rule)
3. **Analyst consensus references** — "versus analyst expectations of $X" is not company guidance
4. **Historical comparisons without forward projection** — "compared to $90B last year" is context, not guidance (unless paired with a forward statement)

---

## Period Identification

### Common Patterns in 8-K Press Releases

| Source Text | period_type | Derivation |
|-------------|-------------|------------|
| "For the quarter ending March 2025" | quarter | Use filing date + FYE to determine fiscal quarter |
| "For fiscal year 2025" | annual | fiscal_year from source |
| "For the second half of fiscal 2025" | half | fiscal_year from source |
| "For the next twelve months" | annual | From filing date |
| Table header: "Q2 FY2025 Guidance" | quarter | Direct from table |

### given_date

Always `r.created` (the filing date). This is the point-in-time stamp for when the guidance became public.

### source_key

The exhibit or item key that contained the guidance:
- `"EX-99.1"` — most common (press release)
- `"EX-99.2"` — presentation/supplemental
- `"Item 2.02"` — section text
- `"Item 7.01"` — Reg FD section text

---

## Basis, Segment, Quality Filters

See SKILL.md [§6 Basis Rules](../SKILL.md#6-basis-rules), [§7 Segment Rules](../SKILL.md#7-segment-rules), [§13 Quality Filters](../SKILL.md#13-quality-filters).

### 8-K Trap: Table Columns

Tables often have GAAP and non-GAAP columns. Extract BOTH — each gets its own GuidanceUpdate node with the appropriate `basis_norm`. Do not skip the GAAP column because the non-GAAP is "more useful."

### 8-K Quality Addition: Safe-Harbor Proximity

Filter disclaimer-only blocks, but do not blindly drop adjacent lines if they contain concrete guidance numbers/periods.

---

## Duplicate Resolution

When the same guidance metric appears in BOTH exhibit and section text:

1. **Exhibit is primary** — use the exhibit version (more detailed, includes tables)
2. **Section may add context** — if section text provides additional detail (e.g., conditions) not in exhibit, annotate in `conditions` field
3. **Never double-count** — deterministic IDs (§2A) prevent duplicates if same values, but verify `source_key` differs

---

## Empty Content Handling

| Scenario | Action |
|----------|--------|
| EX-99.1 missing, section content exists | Process section content — valid extraction |
| EX-99.1 exists but is empty (`strip()==""`) | Return `EMPTY_CONTENT\|8k\|EX-99.1`, try section |
| No exhibit AND no section content | Try filing text (fallback) |
| Filing text also empty | Return `EMPTY_CONTENT\|8k\|full` |

---
*Version 1.1 | 2026-02-21 | Deduplicated basis/segment/quality sections → SKILL.md references. Kept 8-K-specific traps.*
