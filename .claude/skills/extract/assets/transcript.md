# Transcript Extraction Profile

Per-source profile for earnings call transcripts. Loaded by the extraction agent when `ASSET = transcript`.

## Asset Metadata
- sections: prepared_remarks, qa
- label: Transcript
- neo4j_label: Transcript

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
| `t.id` | String | `AAPL_2025-01-30T17.00` |
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

## Prepared Remarks Processing

### Structure

Prepared remarks arrive as a single `content` string containing a JSON array of speaker statements. Each statement includes position markers in brackets.

---

## Q&A Processing

### Structure

Q&A exchanges arrive as an array of objects, each containing:
- `questioner` / `questioner_title` — analyst asking
- `responders` / `responder_title` — management answering
- `exchanges` — full text of the Q&A dialogue

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

Transcript statements can refer to different target periods.

### Common Patterns

| Transcript Statement | Likely interpretation |
|---------------------|-----------------------|
| "For the December quarter" | Quarterly target period; derive fiscal quarter from FYE |
| "For the full fiscal year" | Annual target period in the transcript fiscal year |
| "For the March quarter" | Quarterly target period; derive fiscal quarter from FYE |
| "For the second half" | Half-year target period in the transcript fiscal year |
| "By fiscal 2027" | Long-range target year 2027 |
| "Over the next several years" | Multi-year target period |

### Calendar → Fiscal Mapping

When source uses calendar quarter names ("December quarter"), use FYE to determine fiscal quarter. Do NOT guess — use the FYE month (from QUERIES.md 1B) with the calendar-to-fiscal mapping table below.

| FYE Month | Company Example | Q1 Months | Q2 Months | Q3 Months | Q4 Months |
|-----------|-----------------|-----------|-----------|-----------|-----------|
| 9 (Sep) | Apple | Oct-Dec | Jan-Mar | Apr-Jun | Jul-Sep |
| 12 (Dec) | Most companies | Jan-Mar | Apr-Jun | Jul-Sep | Oct-Dec |
| 6 (Jun) | Microsoft | Jul-Sep | Oct-Dec | Jan-Mar | Apr-Jun |
| 3 (Mar) | Oracle (old) | Apr-Jun | Jul-Sep | Oct-Dec | Jan-Mar |

**Rule**: Q1 starts in FYE month + 1. When source says "Q1" or "Q2" explicitly, use as-is.

## Source Identity

### given_date

Always `t.conference_datetime`. This is the point-in-time stamp for when the content became public via earnings call.

### source_key

Always `"full"` for transcripts.

---
*Version 1.4 | 2026-03-09 | Decontaminated generic transcript asset profile. Removed two-pass write semantics and guidance-specific basis rules from the asset file. Neutralized period table headers and moved source identity to its own section. v1.3: Fixed QuestionAnswer types: content/speaker_roles are JSON strings (not lists), speaker_roles nullable. v1.2: Added HAS_QA_SECTION fallback (3C). v1.1: Deduplicated → SKILL.md refs.*
