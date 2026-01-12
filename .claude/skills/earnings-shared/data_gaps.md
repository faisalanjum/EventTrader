# Known Data Gaps

This file documents known gaps in the Neo4j database that may affect earnings attribution analysis.

---

## Transcript Gaps

| Date Range | Affected Companies | Impact | Mitigation |
|------------|-------------------|--------|------------|
| Feb-Mar 2023 | Large-cap retailers (LOW, HD, TGT) | Missing transcripts | News coverage typically sufficient; use Perplexity fallback if needed |
| 2024 | PLCE (The Children's Place) | Only Q4 FY2022 transcript available; no Q1-Q3 FY2024/2025 | News headlines provided sufficient consensus data for this analysis |

---

## News Coverage Gaps

| Issue | Affected | Impact | Mitigation |
|-------|----------|--------|------------|
| Small-cap companies | Market cap < $500M | May have sparse news coverage | Rely more heavily on SEC filings and Perplexity |
| Consensus estimates missing | Perplexity returns no pre-filing estimates | Cannot verify consensus independently | WebSearch "{ticker} Q{N} FY{year} EPS estimate consensus" |

---

## XBRL Data Gaps

| Issue | Affected | Impact | Mitigation |
|-------|----------|--------|------------|
| 8-K reports | All 8-K filings | No XBRL data (by design) | Use historical 10-K/10-Q XBRL for trend context |
| Processing delays | Recent filings | XBRL may show `xbrl_status: 'QUEUED'` | Check `xbrl_status = 'COMPLETED'` before querying |

---

## Corporate Actions Gaps

| Issue | Affected | Impact | Mitigation |
|-------|----------|--------|------------|
| Dividend timing | Some records | `declaration_date` may not align exactly with announcement | Check ±3 day window |

---

## How to Update This File

When you encounter a data gap during analysis:

1. Document the gap with:
   - Date range or specific dates affected
   - Companies or company types affected
   - What data is missing
   - What mitigation you used

2. Add to the appropriate section above

3. If it's a systematic issue, consider whether it should be addressed in data collection

---

*Last updated: 2026-01-11*
