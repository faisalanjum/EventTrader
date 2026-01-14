# Known Data Gaps

This file tracks known data gaps encountered during earnings attribution analysis. Use this to:
1. Set appropriate expectations when querying
2. Know when to use alternative sources (News, Perplexity)
3. Prioritize data ingestion improvements

---

## Missing Exhibit Content (EX-99.1)

Some 8-K filings have EX-99.1 press releases referenced in Item 9.01 but the actual exhibit content is not extracted into `ExhibitContent` nodes.

| Accession | Ticker | Date | Notes |
|-----------|--------|------|-------|
| 0001514416-24-000020 | BAND | 2024-02-28 | Item 9.01 references EX-99.1 but 0 exhibits in database |

**Workaround**: Use News headlines (often quote exact EPS/Revenue vs estimates) or Perplexity for actual figures.

---

## Missing Transcripts

Earnings call transcripts that should exist but are not in the database.

| Ticker | Period | Expected Date | Filing Reference | Notes |
|--------|--------|---------------|------------------|-------|
| BAND | Q4 FY2023 | ~2024-02-28 | 0001514416-24-000020 | 8-K filed but no transcript; prior transcripts (Q2, Q3 2023) exist |

**Workaround**: Use prior quarter transcripts for management tone/themes, News for key quotes.

---

## News Data Quality Issues

### ~0.9% of News->Company relationships have `daily_industry` but no `daily_stock`
**Filter**: Always use `WHERE r.daily_stock IS NOT NULL` when querying News.

---

## Filing Metadata Gaps

### Fiscal Period Not Populated
Some 8-K filings have null `fiscalPeriod` and `fiscalYearEnd` fields despite being earnings releases.

| Accession | Ticker | Issue |
|-----------|--------|-------|
| 0001514416-24-000020 | BAND | fiscalPeriod=null, fiscalYearEnd=null |

**Workaround**: Infer fiscal period from filing date and company's fiscal calendar.

---

*Last updated: 2026-01-13*
