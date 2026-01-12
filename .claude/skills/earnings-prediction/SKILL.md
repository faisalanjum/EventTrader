---
name: earnings-prediction
description: Predicts stock direction/magnitude at T=0 (report release). Uses PIT data only. Run before earnings-attribution.
allowed-tools: Read, Write, Grep, Glob, Bash, TodoWrite, Task, mcp__perplexity__search, mcp__perplexity__reason
model: claude-opus-4-5
---

# Earnings Prediction

**Goal**: Predict stock direction and magnitude at report release (T=0) using only point-in-time data.

**Thinking**: ALWAYS use `ultrathink` for maximum reasoning depth.

---

## Resources

- **Output format**: [output_template.md](../earnings-shared/output_template.md)
- **Evidence audit**: [evidence_audit.md](../earnings-shared/evidence_audit.md)
- **Known data gaps**: [data_gaps.md](../earnings-shared/data_gaps.md)

---

## Output Locations

- **Report**: `earnings-analysis/Companies/{TICKER}/{accession}.md`
- **Predictions CSV**: `earnings-analysis/predictions.csv`

---

## PIT Data Rules

**CRITICAL**: All queries must use point-in-time filtering.

- Include PIT filter in all subagent prompts: `"PIT date: {filing_datetime}"`
- NO access to returns data (daily_stock, hourly_stock, etc.)
- NO access to post-filing news or transcripts
- Query only data that existed BEFORE the report was filed

---

## Workflow

(To be filled in later)

---

## Predictions CSV Format

```csv
accession,ticker,filed_date,predicted_direction,predicted_magnitude,confidence,rationale_summary
```

---

*Version 1.0 | 2026-01-12 | Initial skeleton*
