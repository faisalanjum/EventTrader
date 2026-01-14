# Earnings Attribution Skill - Changelog

This file documents all changes to the earnings-attribution skill, including the reasoning behind each decision.

---

## Version 4.2 (2026-01-04) - Methodology Rigor

### Summary
Added strict numeric evidence rules, codified surprise calculation formulas, conflict resolution guidelines, and data quality guardrails based on analysis of external recommendations.

### Changes Made

1. **Strict Numeric Evidence Rules**
   - Numbers used in surprise calculations now REQUIRE exact value + source
   - Format: `{metric}: ${exact_value} (Source: {source_name}, {date})`
   - Qualitative observations can still use paraphrasing
   - Prevents calculation errors from polluting driver understanding

2. **Codified Surprise Calculation Formulas**
   - EPS Surprise % = ((Actual - Consensus) / |Consensus|) × 100
   - Revenue Surprise % = ((Actual - Consensus) / |Consensus|) × 100
   - Guidance: Compare midpoint of range to consensus
   - All percentages to 2 decimal places
   - Ensures consistency across all analyses

3. **Conflict Resolution Guidelines**
   - Source reliability hierarchy (8-K > Transcript > News)
   - Driver priority guidance (forward-looking usually > backward-looking)
   - Rule: Note conflicts explicitly rather than silently choosing

4. **Data Quality Guardrails**
   - News anomaly filter (existing)
   - Missing returns handling
   - Duplicate news detection
   - Stale consensus warning

### Reasoning
- Strict numbers prevent calculation drift that would corrupt driver understanding
- Consistent formulas enable meaningful comparison across events
- Conflict resolution prevents inconsistent attribution
- Guardrails prevent bad data from skewing analysis

### Files Changed
- `SKILL.md` - Added 4 new sections (239 → 352 lines, still under 500 limit)
- `CHANGELOG.md` - Added v4.2 entry

---

## Version 4.1 (2026-01-04) - Size Optimization

### Summary
Trimmed SKILL.md from 571 lines to 239 lines per best practices (<500 line limit).

### Changes Made

1. **Created output_template.md**
   - Moved full report template to reference file
   - Moved company learnings template
   - SKILL.md now references this file

2. **Trimmed verbose content**
   - Removed detailed Cypher queries (already in neo4j_schema.md)
   - Condensed explanations (Claude is smart)
   - Removed duplicate Data Sources Reference section

3. **Applied Progressive Disclosure**
   - SKILL.md now contains high-level guidance
   - Details are in reference files (loaded on-demand)
   - Follows "context window is a public good" principle

### Files Changed
- `SKILL.md` - Trimmed from 571 to 239 lines
- `output_template.md` - New file (report + learnings templates)
- `CHANGELOG.md` - Added v4.1 entry

### Best Practices Applied (from skills-reference.md)
- SKILL.md under 500 lines (now 239)
- Progressive disclosure architecture
- Reference files one level deep
- Concise, assume Claude is smart

---

## Version 4.0 (2026-01-04) - Complete Rewrite

### Summary
Complete rewrite based on line-by-line review with user. Shifted from pattern-matching to surprise-based fundamental analysis.

### Strategic Decisions Made

#### 1. Removed Pre-Defined Patterns
- **Before**: Patterns like "Beat-and-Raise", "Beat-and-Lower" with prescribed reactions
- **After**: No patterns; agent derives conclusions from fundamental data
- **Reasoning**:
  - Patterns can bias the agent to "look for" them instead of discovering what actually matters
  - Different companies have different sensitivities
  - New driver types can emerge that patterns don't capture
  - Goal is 100% accuracy, not pattern matching

#### 2. Added Surprise-Based Analysis
- **Change**: Stock moves are now explained as "actual vs expected" surprises
- **Reasoning**:
  - Stock prices move on SURPRISES, not absolute results
  - A "good" result can cause a drop if expectations were higher
  - This is how professional traders think about earnings
  - Essential for real-time prediction accuracy

#### 3. Added Data Inventory Step (Step 1)
- **Change**: Before any analysis, agent maps what data exists
- **Reasoning**:
  - Agent should never claim to have checked data that doesn't exist
  - Prevents fabrication by knowing upfront what's available
  - Enables honest "insufficient data" declarations

#### 4. Expanded Data Sources
- **Before**: Only News + Transcript
- **After**: News, Transcript, XBRL history, Dividends, Splits, sector/industry context
- **Reasoning**:
  - Comprehensiveness is critical for 100% accuracy
  - Dividend cuts can explain stock drops
  - Historical XBRL provides trend context
  - Sector/industry returns distinguish stock-specific vs sector-wide moves

#### 5. Always Query Perplexity for Consensus
- **Before**: Perplexity was "fallback only"
- **After**: Always query Perplexity for consensus estimates
- **Reasoning**:
  - Consensus estimates are critical for surprise calculation
  - Neo4j News doesn't reliably contain consensus figures
  - Better to always have the expectation baseline

#### 6. Ranked Confidence Instead of Percentages
- **Before**: Primary (60%), Secondary (30%), Tertiary (10%)
- **After**: Primary Driver + Contributing Factors (no percentages)
- **Reasoning**:
  - Percentages create false precision
  - How do you really know it's 60% vs 55%?
  - Ranked confidence is more honest about uncertainty

#### 7. Added Self-Audit Step
- **Change**: Agent validates all claims have sources before completing
- **Reasoning**:
  - Ensures reliability without external verification
  - Every claim must be traceable
  - Prevents hallucination by design

#### 8. Added Confidence Assessment Section
- **Change**: Required section in output with reasoning
- **Reasoning**:
  - Agent must honestly assess its own certainty
  - Explains why confidence is High/Medium/Insufficient
  - Critical for downstream decision-making

#### 9. Removed Cypher Queries from Report
- **Before**: All queries documented in report output
- **After**: Queries kept in logs only, not in report
- **Reasoning**:
  - Self-audit step makes verification redundant
  - Cleaner reports
  - Queries still available in logs for debugging

#### 10. Company-Specific Learning
- **Change**: Store learnings in `earnings-analysis/Companies/{TICKER}/learnings.md`
- **Reasoning**:
  - Each company has different driver sensitivities
  - Historical analysis builds company-specific knowledge
  - Foundation for real-time prediction accuracy

#### 11. Added mcp__perplexity__perplexity_research Tool
- **Change**: Added to allowed-tools
- **Reasoning**:
  - For complex cases where search/reason fail
  - For major moves (>10% adjusted)
  - For conflicting sources

#### 12. Query Principles Instead of Templates
- **Before**: Rigid query templates
- **After**: Query principles + examples
- **Reasoning**:
  - Templates constrain agent thinking
  - Principles teach WHY queries work
  - Enables better dynamic query crafting

#### 13. Created data_gaps.md
- **Change**: Moved known data gaps to separate file
- **Reasoning**:
  - Keeps SKILL.md focused on process
  - Gaps can be updated independently
  - Easier to maintain

### Files Changed
- `SKILL.md` - Complete rewrite (v3.1 → v4.0)
- `data_gaps.md` - New file
- `CHANGELOG.md` - New file (this file)

---

## Version 3.1 (2026-01-03)

### Changes
- Added Beat-and-Lower variants (Revenue/EPS)
- Added Known Data Gaps section

---

## Version 3.0 (Initial Documented Version)

### Features
- Pattern-based analysis (Beat-and-Raise, Beat-and-Lower, etc.)
- 8-step workflow
- News + Transcript as primary sources
- Perplexity as fallback
- Weighted attribution percentages

---

## How to Update This Changelog

When making changes to SKILL.md:

1. Increment version number in SKILL.md footer
2. Add new section at top of this file with:
   - Version and date
   - Summary of changes
   - Reasoning for each significant decision
   - Files changed

3. Keep reasoning detailed - future Claude instances need to understand WHY decisions were made

---

*Format: Version X.Y (YYYY-MM-DD) - Short Description*
