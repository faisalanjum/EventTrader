# Transcript Extraction Profile

Per-source extraction rules for earnings call transcripts. Loaded by the guidance extraction agent when `SOURCE_TYPE = transcript`.

## Data Structure

Transcripts arrive via query 3B, with optional fallback via 3C:

| Component | Node Label | Relationship | Content Format |
|-----------|-----------|--------------|----------------|
| **Prepared Remarks** | PreparedRemark | `Transcript-[:HAS_PREPARED_REMARKS]->` | JSON text with speaker statements and position markers in brackets |
| **Q&A Exchanges** | QAExchange | `Transcript-[:HAS_QA_EXCHANGE]->` | Array of objects with `questioner`, `responders`, `exchanges` |
| **Q&A Section** (fallback) | QuestionAnswer | `Transcript-[:HAS_QA_SECTION]->` | JSON string content (parse to dialogue array) with optional `speaker_roles` JSON string map. Used by ~40 transcripts that lack QAExchange nodes. |

### Transcript Metadata (from Transcript node)

| Field | Type | Example |
|-------|------|---------|
| `t.id` | String | `AAPL_2025-01-30T17.00.00-05.00` |
| `t.conference_datetime` | String (ISO) | `2025-01-30T17:00:00-05:00` |
| `t.fiscal_quarter` | String | `Q1` |
| `t.fiscal_year` | String | `2025` |
| `t.company_name` | String | `Apple Inc` |

### QAExchange Fields

| Field | Type | Description |
|-------|------|-------------|
| `qa.sequence` | String | Order in Q&A session. Use `toInteger()` for sorting. |
| `qa.questioner` | String | Analyst name |
| `qa.questioner_title` | String | Analyst title/firm |
| `qa.responders` | String | Management responder name(s) |
| `qa.responder_title` | String | Management responder title(s) |
| `qa.exchanges` | String | Full Q&A dialogue text |
| `qa.embedding` | float[] | Vector embedding (for semantic search) |

---

## Scan Scope

Process ALL content from the transcript. Do not skip any section. Transcripts are the richest guidance source.

### Speaker Hierarchy (Guidance Priority)

| Priority | Speaker | What to Look For |
|----------|---------|-----------------|
| 1 (Highest) | **CFO** (prepared remarks) | FORMAL GUIDANCE — revenue/margin/EPS guidance with specific numbers, ranges, or YoY comparisons. This is where official guidance statements live. |
| 2 | **CFO** (Q&A responses) | Clarifications, additional detail, segment-level breakdowns, GAAP vs non-GAAP distinctions, "comfortable with consensus" signals |
| 3 | **CEO** (prepared remarks) | Strategic outlook, market positioning, product momentum, qualitative direction |
| 4 | **CEO** (Q&A responses) | Strategic context, long-range targets, acquisition/product guidance |
| 5 | **Other executives** (Q&A) | Segment-specific guidance (e.g., VP of Cloud, Head of Devices) |
| Skip | **Operator** | Procedural remarks only (introductions, instructions). No guidance content. |

---

## Prepared Remarks Processing

### Structure

Prepared remarks arrive as a single `content` string containing a JSON array of speaker statements. Each statement includes position markers in brackets.

### Extraction Steps

1. **Identify speakers** — parse speaker names and roles from the text
2. **Locate CFO section** — this is the primary guidance source
3. **Scan CEO section** — strategic outlook and qualitative guidance
4. **Skip operator remarks** — procedural only
5. **Extract all forward-looking statements** with specific numbers, ranges, or growth descriptors

### What to Extract from Prepared Remarks

| Signal | Example | Extract? |
|--------|---------|----------|
| Explicit range | "We expect Q2 revenue of $94-98 billion" | Yes: `derivation=calculated`, low/high from source |
| Point guidance | "We expect gross margin of approximately 47%" | Yes: `derivation=point`, low=mid=high |
| YoY comparison | "We expect services to grow double digits" | Yes: `derivation=implied`, qualitative="double digits" |
| Qualitative direction | "We see continued strength in iPhone" | No: lacks quantitative anchor |
| Prior period results | "Q1 revenue was $124 billion" | No: past period, not forward guidance |
| Safe harbor boilerplate | "These statements involve risks..." | No: but keep any concrete guidance adjacent to it |

### Quote Prefix

All guidance extracted from prepared remarks MUST use quote prefix: `[PR]`

Example: `[PR] We expect second quarter revenue to be between $94 billion and $98 billion`

---

## Q&A Processing

### Structure

Q&A exchanges arrive as an array of objects, each containing:
- `questioner` / `questioner_title` — analyst asking
- `responders` / `responder_title` — management answering
- `exchanges` — full text of the Q&A dialogue

### Why Q&A Matters

Q&A is often MORE valuable for guidance than prepared remarks because:
1. Analysts probe for specifics not in prepared remarks
2. Management reveals segment-level detail under questioning
3. Geographic/product breakdowns emerge
4. GAAP vs non-GAAP clarifications are made
5. "Comfortable with consensus" signals (implied guidance)
6. Conditional guidance appears ("if X, then we'd expect Y")
7. Sensitivity bounds are revealed ("plus or minus 100 bps")

### Extraction Steps

1. **Process every exchange** — do not skip any Q&A
2. **Focus on management responses** — analyst questions provide context, but guidance comes from management answers
3. **Look for CFO responses** — these carry highest guidance authority in Q&A
4. **Capture analyst name** — use in `section` field for citation (e.g., `Q&A #3 (analyst name)`)

### What to Extract from Q&A

| Signal | Example | Extract? |
|--------|---------|----------|
| Specific numbers in response | "For the June quarter, we're looking at OpEx of $14.5-14.7 billion" | Yes |
| Consensus comfort | "We're comfortable with where the Street is" | Yes: `derivation=implied`, note in qualitative field |
| Segment detail | "Services growth will be in the mid-to-high teens" | Yes: segment="Services", qualitative |
| Conditional guidance | "Assuming no FX headwinds, we'd see 2% higher growth" | Yes: note condition in `conditions` field |
| Clarification of PR guidance | "To be more specific, that's on a non-GAAP basis" | Yes: updates basis for the PR guidance item |
| Analyst estimate repetition | "Your consensus shows $3.50" | No: analyst estimate, not company guidance |
| Generic positive sentiment | "We feel good about the business" | No: no quantitative anchor |

### Quote Prefix

All guidance extracted from Q&A MUST use quote prefix: `[Q&A]`

Example: `[Q&A] We are targeting services growth in the mid-to-high teens year over year`

### Section Field Format

For Q&A guidance, the `section` field should identify where in the Q&A:
- `Q&A #1` (by sequence number)
- `Q&A (Shannon Cross)` (by analyst name, when available)
- `Q&A #3 (Ben Reitzes)` (both, preferred)

---

## Duplicate Resolution

When the same metric appears in BOTH prepared remarks and Q&A:

1. **If Q&A is more specific** → use Q&A version as the primary extraction
   - Example: PR says "mid-40s gross margin" → Q&A says "46% to 47% gross margin"
   - Extract the Q&A version (46-47%) with `[Q&A]` prefix

2. **If PR is more specific** → use PR version
   - Rare, but possible when analyst question gets a vague response

3. **If both are equally specific but values differ** → extract BOTH
   - This represents a potential revision within the same call
   - The later statement (typically Q&A) takes precedence for "latest" determination

4. **Never skip a metric** — if it appears in Q&A with new detail not in PR, extract it even if PR also covered it

---

## Empty Content Handling

| Scenario | Action |
|----------|--------|
| `prepared_remarks` is null AND `qa_exchanges` is empty | Try Q&A Section fallback (3C) before returning empty |
| `prepared_remarks` is null, `qa_exchanges` has content | Process Q&A only — valid extraction |
| `prepared_remarks` has content, `qa_exchanges` is empty | Try Q&A Section fallback (3C); if also empty, process PR only |
| Both have content | Process both — standard case |

### Fallback: Q&A Section (Query 3C)

~40 transcripts use `HAS_QA_SECTION → QuestionAnswer` instead of `HAS_QA_EXCHANGE → QAExchange`. When query 3B returns empty `qa_exchanges`, try 3C:

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_QA_SECTION]->(qa:QuestionAnswer)
RETURN qa.id, qa.content, qa.speaker_roles
```

**Content format differs from QAExchange**:
- `content`: JSON **string** (not a native list) containing an array of speaker-labeled dialogue lines. Must be JSON-parsed.
- `speaker_roles`: JSON **string** containing an object mapping speaker names to roles (OPERATOR, EXECUTIVE, ANALYST). Must be JSON-parsed. **Can be NULL** (~7 of 41 nodes) — handle gracefully.
- Use `speaker_roles` to identify management responses (EXECUTIVE) vs analyst questions (ANALYST)
- No `questioner`/`responders` fields — derive from the `speaker_roles` map
- For the `section` field, use `Q&A (derived)` since sequence numbers are not available

### Fallback: Full Transcript Text (Query 3D)

If both 3B and 3C return empty content, attempt fallback query 3D:
```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
RETURN ft.content
```
**Note**: Only 28 FullTranscriptText nodes exist. This fallback rarely applies.

---

## Period Identification

Transcripts cover multiple periods. Each guidance statement references a target period.

### Common Patterns

| Transcript Statement | period_type | fiscal_year | fiscal_quarter |
|---------------------|-------------|-------------|----------------|
| "For the December quarter" | quarter | Derive from FYE | Derive from FYE |
| "For the full fiscal year" | annual | From t.fiscal_year | `.` |
| "For the March quarter" | quarter | Derive from FYE | Derive from FYE |
| "For the second half" | half | From t.fiscal_year | `.` |
| "By fiscal 2027" | long-range | 2027 | `.` |
| "Over the next several years" | long-range | Best-effort | `.` |

### Calendar → Fiscal Mapping

When source uses calendar quarter names ("December quarter"), use FYE to determine fiscal quarter. Do NOT guess — use `fiscal_resolve.py` with the company's FYE month.

| FYE Month | Company Example | Q1 Months | Q2 Months | Q3 Months | Q4 Months |
|-----------|-----------------|-----------|-----------|-----------|-----------|
| 9 (Sep) | Apple | Oct-Dec | Jan-Mar | Apr-Jun | Jul-Sep |
| 12 (Dec) | Most companies | Jan-Mar | Apr-Jun | Jul-Sep | Oct-Dec |
| 6 (Jun) | Microsoft | Jul-Sep | Oct-Dec | Jan-Mar | Apr-Jun |
| 3 (Mar) | Oracle (old) | Apr-Jun | Jul-Sep | Oct-Dec | Jan-Mar |

**Rule**: Q1 starts in FYE month + 1. When source says "Q1" or "Q2" explicitly, use as-is.

---

## Basis, Segment, Quality Filters

See SKILL.md [§6 Basis Rules](../SKILL.md#6-basis-rules), [§7 Segment Rules](../SKILL.md#7-segment-rules), [§13 Quality Filters](../SKILL.md#13-quality-filters).

### Transcript-Specific Trap: Implicit Basis Switches

CFO may switch between GAAP and non-GAAP within the same paragraph without re-stating the basis. Each metric gets its own basis determination from its own quote span:
```
"On a GAAP basis, we expect EPS of $3.20. And revenue should be about $95 billion."
```
Here: EPS = `gaap`, Revenue = `unknown` (no explicit qualifier for revenue).

### Transcript-Specific: given_date

Always `t.conference_datetime`. This is the point-in-time stamp for when the guidance became public via earnings call.

### Transcript-Specific: source_key

Always `"full"` for transcripts.

---
*Version 1.3 | 2026-02-21 | Fixed QuestionAnswer types: content/speaker_roles are JSON strings (not lists), speaker_roles nullable. v1.2: Added HAS_QA_SECTION fallback (3C). v1.1: Deduplicated → SKILL.md refs.*
