# Multi-Entity Filing Bug: Orphaned 10-K/10-Q/8-K Reports

**Discovered**: 2026-03-29
**Severity**: HIGH — ~27 companies had 10-K/10-Q/8-K reports with no PRIMARY_FILER
**Status**: ✅ FULLY FIXED (code + Cypher for both 10-K/10-Q and 8-K)

### Current Status (updated 2026-04-01)
- ✅ **Part 1 deployed**: CIK normalization in `sec_schemas.py` + source ticker preserved (`ticker=self.ticker`).
- ✅ **Part 2 deployed**: Unified entity fallback in `ReportProcessor.py` — 10-K/10-Q (sole match) + 8-K (sole match, index > 0, source_ticker agreement).
- ✅ **Part 3 deployed**: Conditional CIK update on ON MATCH in `report.py`.
- ✅ **Part 4 applied**: Cypher patch — 257 10-K/10-Q orphans repaired (PRIMARY_FILER created, return properties preserved).
- ✅ **Part 5 applied**: XBRL status reset — 257 10-K/10-Q reports set to NULL (eligible for queueing). All 257 now XBRL COMPLETED.
- ✅ **Part 6 applied**: 8-K Cypher patch — 569 8-K orphans repaired (PRIMARY_FILER created, return properties preserved, xbrl_status=SKIPPED).
- ✅ **XBRL complete**: 257 10-K/10-Q all processed. 569 8-K correctly SKIPPED (no XBRL for 8-K).

### How to verify fully done
```cypher
-- Check zero multi-entity orphans remain:
MATCH (r:Report)
WHERE r.formType IN ['10-K','10-K/A','10-Q','10-Q/A']
  AND NOT (r)-[:PRIMARY_FILER]->(:Company)
  AND (r.cik IS NULL OR r.cik = '')
RETURN count(r) AS remaining_orphans
-- Expected: 0

-- Check XBRL processing completed for repaired reports:
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN ['AAL','AEE','CEG','CNK','CTVA','D','DOW','DTE','DUK','ED','EIX','ETR','FE','HTZ','HUN','OGE','PEG','PNW','PPL','SBGI','SPG','SRE','URI','WMB','XRX']
  AND r.formType IN ['10-K','10-K/A','10-Q','10-Q/A']
RETURN r.xbrl_status AS status, count(r) AS cnt
-- Expected: mostly COMPLETED or QUEUED, zero REFERENCE_ONLY
```
**Authoritative fix**: Section 12 (all earlier fix sections are superseded)

---

## 1. Executive Summary

As of Apr 1, 2026 (post-backfill snapshot), there are **257 orphaned 10-K/10-Q reports** in Neo4j with no `PRIMARY_FILER` relationship to a `Company`. All 257 have exactly 1 `REFERENCED_IN` edge to the correct company, `xbrl_status = 'REFERENCE_ONLY'`, `cik: null`, and `is_xml: true`.

> **Note on earlier counts**: The original analysis (Mar 29, during active backfill) reported 254 total orphans: 251 main-bug + 3 single-entity outliers. The 3 outliers were transient (partial writes during backfill). The current stable count is **257**, all confirmed as the main combined-filer bug. Counts shifted as the backfill progressed — earlier per-ticker breakdowns are directionally correct but not exact.

These totals shifted during the backfill. The original Mar 29 snapshot showed 254 (251 main-bug + 3 transient outliers). The post-backfill Apr 1 snapshot shows **257**, all confirmed as the same main bug pattern:

- `cik: null`
- `xbrl_status: REFERENCE_ONLY`
- multi-entity combined filings
- the expected universe company CIK is present in `entities`, but **not at `entities[0]`**
- all 257 have exactly 1 `REFERENCED_IN` edge to the correct company
- the 3 earlier single-entity outliers (CMC, PHM, EPC) were transient partial-write artifacts during backfill and have since resolved

---

## 2. Validated Graph State (Apr 1, 2026 — post-backfill snapshot)

### Orphaned report counts
- **257 total** orphaned 10-K/10-Q reports with no PRIMARY_FILER

### XBRL / CIK state (all 257)
- `cik: null`
- `xbrl_status = REFERENCE_ONLY`
- `is_xml: true`

### Entity / relationship shape (all 257)
- Multi-entity combined filings
- Exactly 1 `REFERENCED_IN` edge to the correct company (which should become `PRIMARY_FILER`)
- Exactly 1 parsed symbol mapping to a `Company`
- `REFERENCED_IN` edges carry return properties (daily_stock, session_stock, etc.)
- `Report.symbols` is stored as a **JSON string** such as `["AAL"]`

### Enrichment state
- All 257 have `HAS_SECTION` nodes
- 0 have `HAS_XBRL` (blocked by REFERENCE_ONLY status)

---

## 3. Affected Tickers

### Full-scope bug tickers (zero linked 10-K/10-Q, 23 tickers)
| Ticker | Company | Orphaned 10-K | Orphaned 10-Q | Total |
|--------|---------|---------------|---------------|-------|
| AAL | American Airlines Group Inc | 4 | 9 | 13 |
| AEE | Ameren Corp | 3 | 7 | 10 |
| CEG | Constellation Energy Corp | 3 | 7 | 10 |
| CNK | Cinemark Holdings Inc | 3 | 8 | 11 |
| CTVA | Corteva Inc | 3 | 8 | 11 |
| D | Dominion Energy Inc | 3 | 8 | 11 |
| DOW | Dow Inc | 3 | 9 | 12 |
| DTE | DTE Energy Co | 2 | 6 | 8 |
| DUK | Duke Energy Corp | 2 | 7 | 9 |
| ED | Consolidated Edison Inc | 3 | 8 | 11 |
| EIX | Edison International | 3 | 9 | 12 |
| ETR | Entergy Corp | 3 | 8 | 11 |
| HTZ | Hertz Global Holdings Inc | 3 | 8 | 11 |
| HUN | Huntsman Corp | 3 | 7 | 10 |
| OGE | OGE Energy Corp | 3 | 8 | 11 |
| PEG | Public Service Enterprise Group Inc | 3 | 8 | 11 |
| PNW | Pinnacle West Capital Corp | 3 | 8 | 11 |
| PPL | PPL Corp | 3 | 8 | 11 |
| SBGI | Sinclair Inc | 2 | 7 | 9 |
| SPG | Simon Property Group Inc | 3 | 7 | 10 |
| SRE | Sempra | 3 | 7 | 10 |
| URI | United Rentals Inc | 3 | 9 | 12 |
| XRX | Xerox Holdings Corp | 3 | 8 | 11 |

### Partial-scope confirmed main-bug tickers (2 tickers)
| Ticker | Orphaned 10-K | Orphaned 10-Q | Total |
|--------|---------------|---------------|-------|
| FE | 0 | 2 | 2 |
| WMB | 1 | 2 | 3 |

### Single-entity outlier tickers (RESOLVED — were transient during backfill)
> CMC, EPC, PHM appeared as outliers in the Mar 29 snapshot but resolved when the backfill progressed. Not part of the main bug.

### Non-bug zero-filing ticker
- **ZI (ZoomInfo)**: zero linked reports because the company left the public filing universe after the Thoma Bravo acquisition. Not a bug.

**Post-backfill stable count**: 25 confirmed main-bug tickers (23 full-scope + 2 partial-scope FE, WMB), 257 total orphaned reports.

---

## 4. Confirmed Main Root Cause (257 Reports)

> Note: Original analysis used 251 (Mar 29 snapshot during active backfill). Stable post-backfill count is 257. The root cause chain below applies to all 257.

### Step 1: Historical fetch path is ticker-scoped
Historical REST ingestion queries SEC-API using `ticker:<symbol>`:

```python
search_query = (
    f'ticker:{ticker} AND '
    f'formType:"{form_type}" AND '
    f'filedAt:[{date_from} TO {date_to}]'
)
```

For sampled affected combined filings (`AAL`, `OGE`, `SPG`), the SEC-API response returned:

- top-level `ticker` = universe symbol
- top-level `cik` = universe / holding-company CIK
- `entities[0].cik` = operating subsidiary / LP CIK
- a later entity CIK = the actual tracked company

### Step 2: `sec_schemas.py` overwrites the correct filing-level CIK
`secReports/sec_schemas.py` currently does this:

```python
if self.entities and self.entities[0].cik:
    self.cik = str(self.entities[0].cik).zfill(10)
```

For combined filings, this replaces the correct ticker-scoped filing CIK with the first entity CIK, which is often the subsidiary.

**Confirmed examples from live sampled SEC-API responses**
- `AAL`: top-level `cik = 6201`, `entities[0].cik = 4515`
- `OGE`: top-level `cik = 1021635`, `entities[0].cik = 74145`
- `SPG`: top-level `cik = 1063761`, `entities[0].cik = 1022344`

### Step 3: `ReportProcessor` nulls the mismatched CIK but preserves the symbol
`redisDB/ReportProcessor.py` maps the filing CIK to the stock universe. If that primary CIK does not map to an allowed symbol, it sets:

```python
standardized['ticker'] = standardized['cik'] = None
```

It then separately adds valid symbols from the `entities` array.

That produces the exact broken shape seen in Neo4j for the main cluster:

- `symbols = ["AAL"]`
- `cik = null`

### Step 4: `report.py` creates `REFERENCED_IN` instead of `PRIMARY_FILER`
`neograph/mixins/report.py` currently does:

```python
report_cik = report_props.get("cik")

for param in company_params:
    if report_cik and param['cik'] == report_cik:
        primary_filer_params.append(param)
    else:
        referenced_in_params.append(param)
```

When `report_cik` is `null`, nothing can match, so the only company becomes `REFERENCED_IN` instead of `PRIMARY_FILER`.

This exactly matches the live graph state for all 257 orphaned reports:

- no `PRIMARY_FILER`
- one `REFERENCED_IN`
- correct symbol present
- correct company CIK present later in `entities`

### Step 5: `REFERENCE_ONLY` is set during XBRL reconciliation, not initial insert
The original draft was slightly loose here.

Initial report insertion only calls XBRL queueing when `report_props.get('cik')` is truthy. Null-CIK reports are **not** initially queued for XBRL at insert time.

Later, `neograph/mixins/xbrl.py` reconciliation scans reports whose XBRL status is `NULL` / `QUEUED` / `PROCESSING` / `PENDING`, calls `_enqueue_xbrl(...)`, and `_enqueue_xbrl` marks missing-CIK reports as:

```python
REFERENCE_ONLY
```

That is the actual path that explains why all 257 orphaned reports end up as `REFERENCE_ONLY`.

---

## 5. Single-Entity Outliers (RESOLVED)

The Mar 29 snapshot showed 3 single-entity outliers (CMC, PHM, EPC) that were not explained by the main multi-entity bug. These were **transient partial-write artifacts during active backfill** and have since resolved. The stable post-backfill count is 257, all matching the main bug pattern.

---

## 6. Historical Context: Original Draft Corrections

> The following corrections were noted during the Mar 29-31 analysis when counts were shifting during active backfill. The stable post-backfill state is now **257 reports, all same bug pattern**. These corrections are retained for audit trail only.

- Original draft said "252 orphans" — actual count shifted from 254 (Mar 29) to 257 (Apr 1 stable)
- Original draft included ZI as bug-affected — ZI is a delisted ticker, not a bug
- Original draft said single-entity outliers (CMC, PHM, EPC) were a separate bug — they were transient backfill artifacts, now resolved
- Original draft said "all future multi-entity filings will be correctly linked" — too strong without Part 2 (stream mode fix), now addressed in Section 12
- Counts were point-in-time during active backfill — all references now use the stable Apr 1 count of 257

---

## 7-8. SUPERSEDED — See Section 12 for the finalized 5-part fix

> **Sections 7 and 8 from the original analysis have been superseded** by the production-safe 5-part fix in Section 12. The earlier versions had three issues identified during deep review:
> 1. The Cypher patch deleted REFERENCED_IN without copying edge properties (loses return metrics)
> 2. The sole-entity promotion in report.py was unscoped (regression risk for 13D/425/SC TO-I filings)
> 3. The parser fix was the weaker `if not self.cik` version instead of digit-validated `_normalize_cik`
>
> **Section 12 is the authoritative fix plan.** All code changes, Cypher patches, and execution order are defined there.

---

## 9. Verification Queries

### Verify no bug-affected orphaned 10-K/10-Q remain

```cypher
MATCH (r:Report)
WHERE r.formType IN ['10-K','10-K/A','10-Q','10-Q/A']
  AND NOT (r)-[:PRIMARY_FILER]->(:Company)
RETURN count(r) AS remaining_orphans
```

Expected after Fix A:

- `remaining_orphans = 0`

### Verify the current orphan-bearing tickers now have linked 10-K / 10-Q coverage

```cypher
MATCH (c:Company)
WHERE c.ticker IN [
  'AAL','AEE','CEG','CNK','CTVA','D','DOW','DTE','DUK','ED','EIX','ETR',
  'HTZ','HUN','OGE','PEG','PNW','PPL','SBGI','SPG','SRE','URI','XRX',
  'CMC','EPC','FE','PHM','WMB'
]
OPTIONAL MATCH (c)<-[:PRIMARY_FILER]-(r:Report)
WHERE r.formType IN ['10-K','10-K/A','10-Q','10-Q/A']
RETURN c.ticker AS ticker,
       sum(CASE WHEN r.formType IN ['10-K','10-K/A'] THEN 1 ELSE 0 END) AS linked_10k,
       sum(CASE WHEN r.formType IN ['10-Q','10-Q/A'] THEN 1 ELSE 0 END) AS linked_10q
ORDER BY ticker
```

### Verify no same-company `REFERENCED_IN` remains where `PRIMARY_FILER` now exists

```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
MATCH (r)-[:REFERENCED_IN]->(c)
WHERE r.formType IN ['10-K','10-K/A','10-Q','10-Q/A']
RETURN count(r) AS same_company_dual_links
```

Expected after revised Fix A:

- `same_company_dual_links = 0`

---

## 10. Final Conclusion

**257 orphaned 10-K/10-Q reports** are caused by the multi-entity first-entity-CIK overwrite bug at `sec_schemas.py:233`. All 257 have the same pattern: `cik: null`, `xbrl_status: REFERENCE_ONLY`, exactly 1 REFERENCED_IN edge with return properties.

The finalized 5-part fix (Section 12) addresses all aspects: parser normalization, processor fallback for stream mode, writer CIK backfill, property-preserving graph repair, and XBRL requeue. Earlier fix versions in this document are superseded — Section 12 is authoritative.

---

## 11. SEC-API Documentation Analysis (2026-04-01)

### What the docs say about `entities[0]`

From `https://sec-api.io/docs/stream-api`:
> "entities (array) - A list of all entities referred to in the filing. **The first item in the array always represents the filing issuer.**"

For multi-entity filings:
> "multiple filing objects are created, each with a unique ID, but all with the same accessionNo"

### What actually happens (confirmed from live SEC-API responses)

For combined filings like AAL, OGE, SPG:
- Top-level `cik` = parent/holding company CIK (matches our ticker search) ← **CORRECT**
- `entities[0].cik` = operating subsidiary CIK ← **WRONG for our purposes**
- A later entity in the array = the actual tracked company

The docs say `entities[0]` is "the filing issuer," but for combined filings returned via ticker search, entities[0] is often the subsidiary co-registrant, NOT the parent company we searched for.

**Confirmed examples from live SEC-API responses:**
- `AAL`: top-level `cik = 6201` (American Airlines Group), `entities[0].cik = 4515` (American Airlines Inc — subsidiary)
- `OGE`: top-level `cik = 1021635` (OGE Energy Corp), `entities[0].cik = 74145` (Oklahoma Gas & Electric — subsidiary)
- `SPG`: top-level `cik = 1063761` (Simon Property Group), `entities[0].cik = 1022344` (Simon Property LP — subsidiary)

### Why the original code followed the docs but was still wrong

The code at `sec_schemas.py:233` was written to follow the documentation: use `entities[0].cik` as the primary filer. This is technically correct per the docs. But the docs don't account for combined filings where `entities[0]` is the subsidiary, not the parent company matching our ticker search. The top-level `cik` field IS the correct parent CIK for ticker-scoped searches.

### Impact on dedup

For multi-entity filings, sec-api.io creates separate filing objects sharing the same `accessionNo`. Our accessionNo-based dedup (both old PROCESSED_QUEUE and new `reports:confirmed_in_neo4j` SET) means only the first filing object processed determines the CIK. For historical ticker search, Part 1 fix ensures the correct CIK. For live stream mode, the order is non-deterministic — Part 2 (sole-entity fallback) addresses this.

---

## 12. Finalized 5-Part Fix (ChatGPT-refined + regression-tested)

### Part 1: CIK normalization in `sec_schemas.py:231-235` — PREVENTS FUTURE ORPHANS

```python
# BEFORE (broken — overwrites parent CIK with subsidiary):
if self.entities and self.entities[0].cik:
    self.cik = str(self.entities[0].cik).zfill(10)

# AFTER (robust — prefers top-level CIK, digit-validated, with fallback):
def _normalize_cik(value: object) -> str:
    """Extract only digits from CIK, pad to 10. Returns '' if no digits."""
    s = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
    return s.zfill(10) if s else ""

primary_cik = _normalize_cik(self.cik)
entity0_cik = (
    _normalize_cik(self.entities[0].cik)
    if self.entities and self.entities[0].cik else ""
)
self.cik = primary_cik or entity0_cik
```

**Regression analysis:**
- Normal single-entity filing: `cik="28917"` → `"0000028917"` ✅ (same as before)
- Combined filing (AAL): `cik="6201"` → `"0000006201"` ✅ (parent CIK kept, not overwritten)
- Empty CIK: `cik=""` → falls back to entities[0] ✅
- Malformed CIK: `cik="nan"` → no digits → falls back to entities[0] ✅
- `cik=None`: → no digits → falls back to entities[0] ✅
- Already padded: `cik="0000028917"` → `"0000028917"` ✅

### Part 2: Sole-entity fallback in `ReportProcessor.py:649-650` — FIXES STREAM MODE

**MUST be scoped to 10-K/10-Q form types only.** For other form types (Schedule 13D, 425, SC TO-I), a non-tracked filer that REFERENCES one tracked company should remain REFERENCED_IN, not be promoted to PRIMARY_FILER.

```python
# BEFORE (line 649-650):
else:
    standardized['ticker'] = standardized['cik'] = None

# AFTER:
else:
    promoted = False
    # For 10-K/10-Q combined filings only: if exactly one entity matches
    # our universe, promote it as primary (handles stream mode ordering)
    if content.get('formType') in ['10-K', '10-Q', '10-K/A', '10-Q/A']:
        entity_match = None
        for entity in content.get('entities', []):
            try:
                ecik = int(entity.get('cik'))
                matches = self.stock_universe[self.stock_universe.cik == ecik]
                if not matches.empty:
                    t = matches.iloc[0]['symbol'].strip().upper()
                    if t in self.allowed_symbols:
                        if entity_match is not None:
                            entity_match = None  # multiple matches — can't determine
                            break
                        entity_match = (ecik, t)
            except (ValueError, TypeError):
                continue
        if entity_match:
            standardized['cik'] = str(entity_match[0]).zfill(10)
            standardized['ticker'] = entity_match[1]
            symbols.add(entity_match[1])
            promoted = True
    if not promoted:
        standardized['ticker'] = standardized['cik'] = None
```

**Why scoping to 10-K/10-Q is critical:**
- 10-K/10-Q combined filings: the tracked company IS the parent/co-registrant → promotion is correct
- Schedule 13D (activist filing): filed BY activist, ABOUT tracked company → promotion would be WRONG
- 425 (merger notice): filed BY acquirer, ABOUT target → promotion would be WRONG
- Without scoping: ~1,500 non-10K/10Q filings would get false PRIMARY_FILER relationships

**Regression analysis:**
- Historical mode with Part 1 fix: primary CIK matches → this code path NOT reached ✅
- Stream mode combined filing: subsidiary object processed first → primary CIK doesn't match → sole entity match → promoted ✅
- Stream mode non-combined filing: primary CIK doesn't match → single entity (the filer) → doesn't match universe → no promotion → CIK nulled ✅
- Schedule 13D referencing tracked company: form type not in list → skipped → CIK nulled → REFERENCED_IN ✅

### Part 3: Conditional CIK update on ON MATCH in `report.py:361`

Add to the `on_match_parts` list:

```python
"r.cik = CASE WHEN (r.cik IS NULL OR r.cik = '') AND $cik IS NOT NULL AND $cik <> '' THEN $cik ELSE r.cik END",
```

**Why conservative (null-guard only):**
- Only fills null/empty CIK, never overwrites existing valid CIK
- Guards against null/empty incoming $cik
- Allows Part 4 Cypher patch to fix existing orphans via re-ingestion (if CIK is null, new value fills in)

**Why NOT "always overwrite":**
- If a re-ingestion from stream mode has the wrong CIK (subsidiary), it would overwrite a correct existing CIK
- The null-guard is safer: if the CIK is already set correctly, leave it alone

### Part 4: One-time Cypher graph repair — FIXES 257 EXISTING ORPHANS

```cypher
-- Repair orphaned reports: create PRIMARY_FILER, copy return properties, set CIK, delete stale REFERENCED_IN
MATCH (r:Report)-[ref:REFERENCED_IN]->(c:Company)
WHERE r.formType IN ['10-K','10-K/A','10-Q','10-Q/A']
  AND r.xbrl_status = 'REFERENCE_ONLY'
  AND NOT (r)-[:PRIMARY_FILER]->(:Company)
MERGE (r)-[pf:PRIMARY_FILER]->(c)
SET pf += properties(ref),
    r.cik = c.cik
DELETE ref
RETURN count(r) AS fixed
```

**Verified safe because:**
- All 257 orphans have exactly 1 REFERENCED_IN edge (confirmed via Neo4j query)
- `SET pf += properties(ref)` copies ALL return properties (daily_stock, session_stock, etc.) before deleting the old edge
- `r.cik = c.cik` fills the null CIK from the company's CIK
- `NOT (r)-[:PRIMARY_FILER]->(:Company)` ensures we only touch reports without existing PRIMARY_FILER

### Part 5: XBRL status reset — MAKES REPAIRED REPORTS ELIGIBLE FOR XBRL

```cypher
-- Reset REFERENCE_ONLY status so repaired reports can be XBRL-queued
MATCH (r:Report)-[:PRIMARY_FILER]->(:Company)
WHERE r.formType IN ['10-K','10-K/A','10-Q','10-Q/A']
  AND r.xbrl_status = 'REFERENCE_ONLY'
  AND NOT (r)-[:HAS_XBRL]->()
SET r.xbrl_status = NULL,
    r.xbrl_error = NULL
RETURN count(r) AS reset_for_xbrl
```

**Why this is needed:**
- `report.py:485`: `excluded_statuses = ['COMPLETED', 'PROCESSING', 'SKIPPED', 'REFERENCE_ONLY']` — REFERENCE_ONLY blocks XBRL queueing
- After Part 4 fixes CIK and creates PRIMARY_FILER, REFERENCE_ONLY status persists → must reset to NULL
- NULL is not in excluded_statuses → report becomes eligible for XBRL queueing
- All 257 have `is_xml: true` (verified) → they WILL pass the is_xml check at `report.py:491`
- `NOT (r)-[:HAS_XBRL]->()` prevents resetting reports that already have XBRL data

---

## 13. Execution Order

1. **Deploy Part 1** (code: `sec_schemas.py`) — prevents future orphans from parser level
2. **Deploy Part 2** (code: `ReportProcessor.py`) — prevents future orphans from stream mode
3. **Deploy Part 3** (code: `report.py`) — enables CIK backfill on re-ingestion
4. **Run Part 4** (Cypher) — fixes 257 existing orphans, preserves return properties
5. **Run Part 5** (Cypher) — resets XBRL status for repaired reports
6. **Verify** — run verification queries from Section 9

**When to execute:** After the current Aug 2025 → Mar 2026 backfill completes. Not urgent — the 257 orphans have existed since 2023 and are stable.

---

## 14. Known Limitations

- **Live-stream key collision**: `redisClasses.py:239` uses `accessionNo + filedAt` as the raw key. If sec-api.io sends multiple filing objects with the same accessionNo AND timestamp, they collapse onto the same key. The last one processed wins. This is pre-existing and NOT caused by this fix.
- **Part 2 scope**: The sole-entity fallback only applies to 10-K/10-Q. Other form types with combined filers (if any exist) would still get REFERENCED_IN.
- **Part 3 conservative**: The null-guard CIK update doesn't fix reports with WRONG non-null CIKs (if any exist). These would need a targeted Cypher patch.
- the original permanent fix was not robust enough to call “100% correct”
