# KSS CapEx & Dividend Concept Linking Audit

## Executive Summary

KSS's CapEx and Dividend Per Share concepts were **NOT linked in the extraction pipeline** due to a restrictive mapping configuration that doesn't account for XBRL concept variation across companies.

## Findings

### Query 1: Recent KSS Filings
**Result:** ✓ Present (5 recent 10-K/10-Q filings dating back to 2024-06-06)

### Query 2: Does KSS have `PaymentsToAcquirePropertyPlantAndEquipment`?
**Result:** ✗ **ZERO facts found**

KSS does NOT file this concept. The warmup cache query (line 40 of `warmup_cache.py`) filters for consolidated facts only:
```cypher
(ctx.member_u_ids IS NULL OR ctx.member_u_ids = [])
```

### Query 3: Does KSS have `CommonStockDividendsPerShareDeclared`?
**Result:** ✗ **ZERO facts found**

However, KSS **DOES file** `CommonStockDividendsPerShareCashPaid` with **280 consolidated facts** — this is the actual per-share dividend data KSS reports, but the mapping is hardcoded to look for `CommonStockDividendsPerShareDeclared`.

### Query 4: What CapEx-related concepts does KSS actually file?

**KSS files: `PaymentsToAcquireProductiveAssets` (200 consolidated facts)**

This is a valid XBRL CapEx concept, but the resolution algorithm doesn't match it because it requires the exact include_pattern `PaymentsToAcquirePropertyPlantAndEquipment`.

**Cross-company context:**
- `PaymentsToAcquirePropertyPlantAndEquipment`: 1,156 filings (most common)
- `PaymentsToAcquireProductiveAssets`: 291 filings (used by ~25% of companies)
- Many other specialized CapEx variants exist for industry-specific cases

## Root Cause Analysis

The mapping system (in `/home/faisal/EventMarketDB/.claude/plans/done_fixes/xbrl-concept-linking.md`, line 423) uses:

```python
'capex':         ('PaymentsToAcquirePropertyPlantAndEquipment', ''),
'dividends_per_share': ('CommonStockDividendsPerShareDeclared', ''),
```

These are **hardcoded exact include patterns**. The resolution algorithm (line 439-448) requires:
1. The include_pattern string MUST appear in the concept's qname
2. No exclude_pattern can appear in the concept's qname
3. Highest usage wins (in case of ties)

**The problem:** Not all companies use the "standard" XBRL concepts.

## Impact

- **KSS guidance items tagged with `capex`**: Will resolve to `null` (no matching concept found in warmup cache)
- **KSS guidance items tagged with `dividends_per_share`**: Will resolve to `null` (no matching concept found in warmup cache)
- **Neo4j linking**: No MAPS_TO_CONCEPT edges created for these two guidance types for KSS
- **Data loss**: CapEx and Dividend guidance from KSS 10-Ks and transcripts cannot be linked to XBRL facts

## Solution Options

### Option 1: Expand include patterns to handle variants (RECOMMENDED)
Update the mapping rules to accept alternative concepts:

```python
'capex': ('PaymentsToAcquirePropertyPlantAndEquipment|PaymentsToAcquireProductiveAssets', ''),
'dividends_per_share': ('CommonStockDividendsPerShare', ''),  # matches both Declared and CashPaid
```

The regex pattern matching (using `=~` in Neo4j) already supports `|` for alternatives.

### Option 2: Audit all companies for concept variations
Run warmup_cache.py for all tickers in the database and identify:
- Which companies use which CapEx concepts
- Which companies use which Dividend concepts
- Build a comprehensive mapping of concept aliases

### Option 3: Hybrid approach
Keep the hardcoded "preferred" concepts but add a fallback:
- Primary: Try to match preferred concept (current behavior)
- Secondary: If primary fails, match any concept containing "Productive" or relevant keywords
- Tag the match with lower confidence

## Files Involved

- Mapping definition: `/home/faisal/EventMarketDB/.claude/plans/done_fixes/xbrl-concept-linking.md` (line 410-432)
- Warmup cache script: `/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/warmup_cache.py`
- Query 2A (concept cache): lines 29-44 of warmup_cache.py
- Guidance write logic: (references guidance_write_cli.py, not examined in this audit)

## Test Results Summary

**Query Data Collected:**
1. KSS has 5 recent 10-K/10-Q filings ✓
2. KSS has 0 `PaymentsToAcquirePropertyPlantAndEquipment` facts ✗
3. KSS has 0 `CommonStockDividendsPerShareDeclared` facts ✗
4. KSS has 200 `PaymentsToAcquireProductiveAssets` facts (alternative CapEx)
5. KSS has 280 `CommonStockDividendsPerShareCashPaid` facts (alternative dividend metric)
