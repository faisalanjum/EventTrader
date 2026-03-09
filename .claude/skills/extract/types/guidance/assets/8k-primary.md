# Guidance × 8-K — Primary Pass

Rules for extracting guidance from 8-K earnings filings. Loaded at slot 4 by the primary agent.

## Routing — 8-K Content Fetch

Use the content fetch order in the asset profile (8k.md):
1. Query 4G (inventory) → 4C (exhibit EX-99.1)
2. Fallbacks: 4E (section text), 4F (filing text)

Apply empty-content rules from the asset profile.

## Guidance-Specific 8-K Content Strategy

Use these item-level tendencies when deciding which layer to read first:

```text
EXHIBIT-FIRST (check EX-99.x / EX-10.x first):
  Item 2.02 (94% in exhibit), Item 7.01 (85%)

CHECK BOTH (data may be in either):
  Item 1.01 (51% in EX-10.x), Item 8.01 (64% exhibit), Item 5.02 (57% exhibit)

SECTION-FIRST (data usually in section itself):
  Item 5.07 (>99% section), Item 2.06 (98% section)
```

## Scan Scope

### Exhibit (EX-99.1 Press Release)

Press releases have a consistent structure. Scan in this order:

| Section | What to Look For | Priority |
|---------|-----------------|----------|
| **Outlook / Guidance** | Explicit forward-looking section, usually near bottom | Highest |
| **Tables** | Revenue/EPS/margin projections, often GAAP vs non-GAAP side by side | High |
| **Footnotes** | GAAP/non-GAAP reconciliation, basis clarification | Medium |
| **Opening paragraphs** | Summary with key numbers (may mix actuals and forward-looking statements) | Medium |
| **Safe harbor** | Skip boilerplate, but keep adjacent concrete forward-looking content | Filter |

### Section Text (Item 2.02 / 7.01)

Usually shorter than exhibits. Often duplicates exhibit content in condensed form. May contain additional context not in the exhibit.

### Pre-Announcements (Item 7.01 / 8.01)

Mid-quarter forward-looking updates — often market-moving. These filings may:
- Raise/lower existing outlook
- Provide preliminary results
- Announce special items affecting outlook

Query 4B finds these. Same extraction rules apply but be especially attentive to revision language.

## Table Columns

When a table shows both GAAP and non-GAAP guidance columns, extract both if both are company-issued guidance. Do not prefer one column over the other.

## What to Extract from 8-K

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

## Do NOT Extract

1. **Pure actuals** — past period results with no forward component
2. **Pure safe-harbor boilerplate** — but keep concrete guidance adjacent to disclaimers (safe-harbor proximity rule)
3. **Analyst consensus references** — "versus analyst expectations of $X" is not company guidance
4. **Historical comparisons without forward projection** — "compared to $90B last year" is context, not guidance (unless paired with a forward statement)

## Safe Harbor Proximity

Filter pure disclaimer blocks, but do not drop adjacent lines if they carry concrete guidance numbers or target periods.

## Quote Prefix

All guidance extracted from 8-K exhibits/sections MUST use quote prefix: `[8-K]`

Example: `[8-K] We expect second quarter revenue to be between $94 billion and $98 billion`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"8k"` |
| `source_key` | `"EX-99.1"`, `"EX-99.2"`, `"Item 2.02"`, `"Item 7.01"`, `"Item 8.01"` (whichever contained the guidance) |
| `given_date` | `r.created` (the filing date) |
| `source_refs` | Exhibit or item IDs if available. Empty array `[]` when no sub-source granularity applies. |
| `section` | Same as `source_key` — the exhibit/item identifier (e.g., `"EX-99.1"`, `"Item 2.02"`) |

## Dedup Rule

When the same guidance metric appears in BOTH exhibit and section text:
1. **Exhibit is primary** — use the exhibit version (more detailed, includes tables)
2. **Section may add context** — annotate in `conditions` field
3. **Never double-count** — deterministic IDs prevent duplicates; verify `source_key` differs
