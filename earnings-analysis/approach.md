# Prediction System: New Approach

> **Goal**: Maximum prediction accuracy in real-time — when a new 8-K drops, predict the stock's 24-hour move (direction and magnitude) BEFORE seeing the actual returns.
>
> **Decision**: Strategy 2 (Prediction-First), simplified.

---

## Strategy 1: Current Approach (Significant Movers Only)

**Report Selection:**
- Only reports with absolute adjusted returns >3-4%
- Rationale: These are the "significant" events; non-movers may not be relevant

**Process:**
1. Select a report that caused a big move
2. Query all available data (Neo4j, Perplexity)
3. Perform attribution analysis (explain WHY it moved)
4. Store learnings in `learnings.md`
5. Repeat for other significant movers

**Data Constraint:**
- None explicitly — you're using post-hoc data (you already know the move)

**Output:**
- Attribution reports explaining significant moves
- Company-specific learnings about what drives big moves

---

## Strategy 2: Proposed Approach (Sequential, Prediction-First)

**Report Selection:**
- ALL reports for a company, processed sequentially (report 1, then 2, then 3...)
- Not filtered by outcome magnitude

**Process:**
1. Take the first report for a company
2. Query ONLY point-in-time data (data available BEFORE the earnings release)
3. Have a validation script that enforces no future data leakage
4. Ask Claude to make a PREDICTION (direction, magnitude, confidence)
5. Wait 24 hours (simulated for historical; real for live)
6. Reveal the actual returns
7. Ask Claude to REASSESS: What did it get right? What did it miss? Why?
8. Store learnings from the reassessment
9. Track prediction accuracy — does Claude improve as it processes more reports?
10. Move to the next report (report 2), now with learnings from report 1
11. Repeat, building cumulative knowledge

**Data Constraint:**
- Strict point-in-time — validation script ensures no data beyond the filing date
- This mimics real-time deployment exactly

**Output:**
- Predictions (before outcome)
- Reassessments (after outcome)
- Accuracy metrics over time (does Claude improve?)
- Company-specific learnings that evolve with each report

---

## Key Differences

| Dimension | Strategy 1 (Current) | Strategy 2 (Proposed) |
|-----------|---------------------|----------------------|
| Report Selection | Only significant movers (>3-4%) | All reports |
| Sequence | Any order | Chronological per company |
| Data Timing | Post-hoc (knows the outcome) | Point-in-time (no future data) |
| Task | Attribution (explain move) | Prediction (forecast move) |
| Feedback Loop | Implicit (learnings from analysis) | Explicit (predict → outcome → reassess) |
| Accuracy Tracking | None | Yes (tracked over time) |
| Learning Accumulation | Per-event | Cumulative across events |

---

## Recommendation: Strategy 2, Simplified

### Why Strategy 2

| Reason | Impact |
|--------|--------|
| You can't get good at prediction by practicing explanation | Strategy 1 trains the wrong task |
| Hindsight bias is eliminated | Prediction before outcome = honest learning |
| Calibration on full distribution | Learn when stocks WON'T move (critical for real-time) |
| Explicit feedback loop | Predict → Compare → Learn is how improvement happens |

### Simplify It

Skip the separate pre-assessment report. Instead:

1. **Log prediction** in a simple CSV (direction, magnitude, confidence, rationale)
2. **Reveal outcome**
3. **Write one final report** (like current) with added "Prediction vs Reality" section
4. **Update learnings** based on what was right/wrong
5. **Track accuracy** over time

This captures 90% of Strategy 2's benefit with 50% of the complexity.

### Bootstrap Suggestion

Start with significant movers first (5-10 per company), then expand to all reports. This builds initial learnings faster before processing lower-signal reports.

---

## Report Format Clarification

The final report (after reassessment) looks almost identical to current reports. The difference is the **process**, not the output format.

**Single final report** — same as current format, plus a "Prediction vs Reality" section:

```markdown
## Prediction vs Reality

| Metric | Predicted | Actual |
|--------|-----------|--------|
| Direction | DOWN | DOWN |
| Magnitude | 10%+ | -10.27% |
| Confidence | Medium-High | — |

**Direction**: CORRECT
**Magnitude**: CORRECT

### What I Got Right
- [explanation]

### What I Missed
- [explanation]

### Learning
- [generalized insight for future]
```

---

## Accuracy Tracking

**CSV Log**: `earnings-analysis/Companies/{TICKER}/accuracy.csv`

```csv
accession,filing_date,predicted_dir,predicted_mag,confidence,actual_dir,actual_return,dir_correct,mag_correct,sequence
0001193125-23-002899,2023-01-06,DOWN,10%+,HIGH,DOWN,-20.08%,TRUE,TRUE,1
```

**Track**: Does accuracy improve as more reports are processed per company?

---

## What Needs to Change

| Component | Change |
|-----------|--------|
| **SKILL.md** | Add prediction phase before attribution; add point-in-time constraint |
| **Validation script** | NEW: Enforce no data after filing date (Neo4j timestamps, Perplexity queries) |
| **output_template.md** | Add "Prediction vs Reality" section |
| **Accuracy logging** | NEW: CSV per company + summary |
| **Report selection** | All reports chronologically (not just significant movers) |
| **learnings.md** | Load BEFORE prediction; update with prediction accuracy |

---

## Implementation Order

1. Build point-in-time validation script
2. Modify SKILL.md workflow
3. Add prediction logging (CSV)
4. Add "Prediction vs Reality" section to output_template.md
5. Test on one company (GBX) end-to-end
6. Roll out to others

---

**Bottom line**: The goal is prediction accuracy. You must practice prediction to get good at it. Strategy 2 is the right approach — just keep the implementation lean.

---

*Decision made: 2026-01-10*
