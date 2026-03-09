# Guidance x Transcript — Primary Pass

Rules for extracting guidance from transcript prepared remarks. Loaded at slot 4 by the primary agent.

## Scan Scope — Transcript

Process all prepared remarks content from the transcript. Do not skip any speaker section.
When falling back to Q&A data (prepared remarks empty/truncated),
apply your quality filters from the pass brief. Use quote prefix `[Q&A]` for any items
extracted from Q&A fallback data. The enrichment agent handles specialized Q&A extraction.

## Content Fetch — Always Use Bash for 3B

Transcript content (query 3B) typically exceeds 50KB and triggers SDK output persistence.
Always fetch via Bash instead of MCP to avoid parse failures:

```bash
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh $TICKER --transcript $TRANSCRIPT_ID
```

Result written to `/tmp/transcript_content_{TRANSCRIPT_ID}.json`. Read this file instead of parsing MCP output.

## Speaker Hierarchy (Guidance Priority)

| Priority | Speaker | What to Look For |
|----------|---------|-----------------|
| 1 (Highest) | **CFO** (prepared remarks) | FORMAL GUIDANCE — revenue/margin/EPS guidance with specific numbers, ranges, or YoY comparisons. This is where official guidance statements live. |
| 2 | **CFO** (Q&A responses) | Clarifications, additional detail, segment-level breakdowns, GAAP vs non-GAAP distinctions, "comfortable with consensus" signals |
| 3 | **CEO** (prepared remarks) | Strategic outlook, market positioning, product momentum, qualitative direction |
| 4 | **CEO** (Q&A responses) | Strategic context, long-range targets, acquisition/product guidance |
| 5 | **Other executives** (Q&A) | Segment-specific guidance (e.g., VP of Cloud, Head of Devices) |
| Skip | **Operator** | Procedural remarks only (introductions, instructions). No guidance content. |

↳ Priority sets precedence for conflicts, not scope. Extract guidance from all speakers.

## Extraction Steps — Prepared Remarks

1. **Identify speakers** — parse speaker names and roles from the text
2. **Locate CFO section** — this is the primary guidance source
3. **Scan CEO section** — strategic outlook and qualitative guidance
4. **Skip operator remarks** — procedural only
5. **Extract all forward-looking statements** with specific numbers, ranges, or growth descriptors

## What to Extract from Prepared Remarks

| Signal | Example | Extract? |
|--------|---------|----------|
| Explicit range | "We expect Q2 revenue of $94-98 billion" | Yes: `derivation=explicit`, low/high from source |
| Point guidance | "We expect gross margin of approximately 47%" | Yes: `derivation=point`, low=mid=high |
| YoY comparison | "We expect services to grow double digits" | Yes: `derivation=implied`, qualitative="double digits" |
| Dividend guidance | "quarterly dividend of $X.XX per share" | Yes: `derivation=point`. Do NOT extract buyback authorizations or investment programs (separate type). |
| Qualitative direction | "We see continued strength in iPhone" | No: lacks quantitative anchor |
| Prior period results | "Q1 revenue was $124 billion" | No: past period, not forward guidance |
| Safe harbor boilerplate | "These statements involve risks..." | No: but keep any concrete guidance adjacent to it |

## Basis Context Trap

Executives can switch between GAAP and non-GAAP within the same paragraph without restating the basis for every metric. Determine basis per quoted metric span, not per paragraph. If a qualifier does not clearly attach to a specific metric, leave `basis_norm = "unknown"` for that metric.

## Quote Prefix — Prepared Remarks

All guidance extracted from prepared remarks MUST use quote prefix: `[PR]`

Example: `[PR] We expect second quarter revenue to be between $94 billion and $98 billion`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"transcript"` |
| `source_key` | `"full"` |
| `given_date` | `t.conference_datetime` |
| `source_refs` | PreparedRemark ID: `{SOURCE_ID}_pr`. For Q&A fallback items: QAExchange IDs `{SOURCE_ID}_qa__{sequence}`. For 3C fallback (QuestionAnswer nodes): use `qa.id` directly — no sequence available. |
| `section` | Speaker's section label (e.g., `"CFO Prepared Remarks"`, `"CEO Prepared Remarks"`) |
