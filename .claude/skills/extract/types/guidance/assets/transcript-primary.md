# Guidance x Transcript — Primary Pass

Rules for extracting guidance from transcript prepared remarks. Loaded at slot 4 by the primary agent.

## Scan Scope — Transcript

Process all prepared remarks content from the transcript. Do not skip any speaker section.
Transcripts are the richest source for extraction.

When falling back to Q&A data (prepared remarks empty/truncated per primary-pass.md),
apply your quality filters from the pass brief. Use quote prefix `[Q&A]` for any items
extracted from Q&A fallback data. The enrichment agent handles specialized Q&A extraction.

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
| Corporate announcement | "Share repurchase authorization of $XX billion", "quarterly dividend of $X.XX per share" | Yes: `derivation=explicit`, material capital announcement |
| Qualitative direction | "We see continued strength in iPhone" | No: lacks quantitative anchor |
| Prior period results | "Q1 revenue was $124 billion" | No: past period, not forward guidance |
| Safe harbor boilerplate | "These statements involve risks..." | No: but keep any concrete guidance adjacent to it |

## Quote Prefix — Prepared Remarks

All guidance extracted from prepared remarks MUST use quote prefix: `[PR]`

Example: `[PR] We expect second quarter revenue to be between $94 billion and $98 billion`
