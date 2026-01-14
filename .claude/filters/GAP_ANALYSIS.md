# PIT Validation Gap Analysis

**Date**: 2026-01-14
**Purpose**: Comprehensive audit of all sources available to earnings-prediction via filtered-data

---

## Executive Summary

**CRITICAL GAP FOUND**: 4 of 5 Perplexity tools CANNOT be reliably PIT-filtered because they return prose text without structured date fields.

---

## Source-by-Source Analysis

### Neo4j Sources (ALL PASS)

| Source | PIT Field | Format | Validator Status | Tested |
|--------|-----------|--------|------------------|--------|
| **neo4j-report** | `created` | datetime | ✅ WORKING | Yes |
| **neo4j-xbrl** | via Report's `created` | datetime | ✅ WORKING | Yes |
| **neo4j-news** | `created` | datetime | ✅ WORKING | Yes |
| **neo4j-entity** | `declaration_date`, `execution_date`, `date` | date-only | ✅ WORKING | Yes |
| **neo4j-transcript** | `conference_datetime` | datetime | ✅ WORKING | Yes |

**All Neo4j sources return JSON with extractable date fields. Validator correctly detects PIT violations.**

### Perplexity Sources (CRITICAL GAPS)

| Source | Output Format | Has Structured Dates | Validator Status | Risk |
|--------|--------------|---------------------|------------------|------|
| **perplexity-search** | Structured results with `Date:` lines | ✅ YES | ✅ CAN VALIDATE | Low |
| **perplexity-ask** | Prose text | ❌ NO | ⚠️ CANNOT VALIDATE | **HIGH** |
| **perplexity-reason** | Prose text | ❌ NO | ⚠️ CANNOT VALIDATE | **HIGH** |
| **perplexity-research** | Long prose report | ❌ NO | ⚠️ CANNOT VALIDATE | **HIGH** |
| **perplexity-sec** | Bash output | ❓ VARIES | ⚠️ UNRELIABLE | Medium |

---

## Perplexity Output Format Evidence

### perplexity-search (SAFE)
Returns structured results with extractable dates:
```
Title: Apple Q3 2024 Earnings Preview
URL: https://example.com/...
Date: 2024-07-30
Snippet: ...
```
**Validator can extract `Date:` line and compare to PIT.**

### perplexity-ask (UNSAFE)
Returns prose without structured dates:
```
Apple reported strong Q3 2024 earnings on August 1, 2024, with EPS of $1.40...
```
**No extractable date field. Validator sees "CLEAN" but response may contain future data.**

### perplexity-reason (UNSAFE)
Returns prose reasoning:
```
The search results provided contain Apple's Q3 2024 earnings data... Apple reported
record revenue of $85.8 billion, up 5% year-over-year, and EPS of $1.40...

Citations:
[1] https://www.mexem.com/blog/apple-inc-analysis-q3-2024-earnings-report
...
```
**Dates embedded in prose. Cannot reliably extract for PIT validation.**

### perplexity-research (UNSAFE)
Returns long research report:
```
# Apple Q3 FY2024 Consensus Earnings Per Share Estimates

Apple Inc. faced significant market scrutiny as investors and analysts prepared
for the company's fiscal third quarter 2024 earnings release...
```
**Multi-page prose with dates throughout text. No structured date field.**

---

## Risk Assessment

### What Can Go Wrong

**Scenario**: earnings-prediction asks perplexity-ask for consensus estimates before a filing.

**Problem**: Perplexity may return articles PUBLISHED AFTER the filing that mention the consensus retroactively. Example:
- PIT: 2024-08-01T09:00:00
- Query: "What were analyst expectations for AAPL Q3 2024 EPS?"
- Response: Article from 2024-08-02 saying "Before the results, analysts expected $1.35 EPS. Apple beat with $1.40."

**Result**: The response mentions the actual result ($1.40), contaminating the prediction.

**Why validator misses it**: No `Date:` field in prose output; validator returns "CLEAN".

---

## earnings-attribution Analysis

### Is It Truly Unrestricted?

**YES** - Confirmed via SKILL.md analysis:

1. **allowed-tools**: `Read, Write, Grep, Glob, Bash, TodoWrite, Task, mcp__perplexity__*`
   - Note: Does NOT list `Skill` - meaning it calls neo4j-* via Task tool, NOT filtered-data

2. **Data access pattern**:
   ```
   earnings-attribution
        │
        │ Task tool with subagent_type=neo4j-*
        ▼
   neo4j-* agents DIRECTLY (no filter)
   ```

3. **PIT is optional**: Line 68 says "PIT filtering (prediction mode)" - only when reusing attribution logic for prediction context

4. **Return data access**: Attribution NEEDS return data to explain stock movements - this is its core purpose

**Conclusion**: earnings-attribution correctly bypasses the filter and can access all data including return fields.

---

## Recommendations

### Option A: Restrict Perplexity Tools (RECOMMENDED)

Modify `/home/faisal/EventMarketDB/.claude/skills/filtered-data/SKILL.md` to only allow `perplexity-search`:

```yaml
skills: neo4j-report, neo4j-xbrl, neo4j-news, neo4j-entity, neo4j-transcript, perplexity-search
```

**Remove**: `perplexity-ask, perplexity-reason, perplexity-research, perplexity-sec`

**Rationale**: Only perplexity-search returns structured dates that can be validated.

### Option B: Add Prose Date Extraction (COMPLEX)

Enhance validator to:
1. Parse prose for date patterns (regex: `\d{4}-\d{2}-\d{2}`, `Month DD, YYYY`, etc.)
2. Extract ALL dates from text
3. Validate each against PIT

**Problems**:
- High false positive rate (historical dates in text)
- Complex regex patterns
- Unreliable extraction

**Not recommended** due to complexity and unreliability.

### Option C: Warn in Confidence (PRAGMATIC)

Keep all Perplexity tools but:
1. Document which tools are PIT-unsafe in earnings-prediction skill
2. Instruct agent to note when using unsafe tools in confidence assessment
3. Accept some risk of contamination

**Currently implemented** (see earnings-prediction SKILL.md line ~45):
> **Note**: Perplexity may return post-hoc articles mentioning stock movement. If detected, note in confidence assessment.

---

## Test Results Summary

### Forbidden Pattern Detection
```bash
echo '[{"daily_stock": 5.2}]' | ./validate_neo4j.sh
# Output: CONTAMINATED:daily_stock  ✅ WORKING
```

### PIT Violation Detection
```bash
echo '[{"created": "2025-08-01T10:00:00-04:00"}]' | ./validate_neo4j.sh --pit "2025-07-31T16:00:00-04:00"
# Output: CONTAMINATED:PIT_VIOLATION:2025-08-01T10:00:00-04:00  ✅ WORKING
```

### Clean Data Pass
```bash
echo '[{"title": "Earnings Beat", "created": "2025-07-30T10:00:00-04:00"}]' | ./validate_neo4j.sh --pit "2025-07-31T16:00:00-04:00"
# Output: CLEAN  ✅ WORKING
```

---

## Files Verified

| File | Status | Notes |
|------|--------|-------|
| rules.json | ✅ Complete | All forbidden patterns, all date fields documented |
| validate_neo4j.sh | ✅ Working | Detects forbidden patterns + PIT violations |
| validate_perplexity.sh | ⚠️ Limited | Only works with perplexity-search output format |
| validate.sh | ✅ Working | Routes to correct validator |
| PIT_REFERENCE.md | ✅ Complete | Full documentation with API verification |
| filtered-data/SKILL.md | ⚠️ Too permissive | Allows unsafe Perplexity tools |
| earnings-prediction/SKILL.md | ✅ Correct | Routes all queries through filtered-data |
| earnings-attribution/SKILL.md | ✅ Correct | Unrestricted access as intended |

---

## Decision: Option A Implemented

**Date**: 2026-01-14

**Changes Made**:
1. `filtered-data/SKILL.md` line 5: Removed `perplexity-ask, perplexity-reason, perplexity-research, perplexity-sec`
2. `earnings-prediction/SKILL.md` line 60: Updated diagram to show `perplexity-search` only
3. `earnings-prediction/SKILL.md` line 166: Updated version to 1.7

**Result**: 100% PIT validation guarantee for all sources available through filtered-data agent.

**Allowed Sources** (all PIT-validatable):
- neo4j-report
- neo4j-xbrl
- neo4j-news
- neo4j-entity
- neo4j-transcript
- perplexity-search

**Blocked Sources** (no structured dates):
- ~~perplexity-ask~~
- ~~perplexity-reason~~
- ~~perplexity-research~~
- ~~perplexity-sec~~

---

*Version 1.1 | 2026-01-14 | Option A implemented*
