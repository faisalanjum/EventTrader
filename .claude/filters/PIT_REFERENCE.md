# Point-in-Time (PIT) Filter Reference

## Core Principle

**"Publicly Available"** is the universal cutoff for ALL sources.

A data point passes PIT validation if and only if it was **publicly available** at or before the PIT timestamp. This is NOT when we ingested it into our database.

---

## When to Use PIT Filter

| Skill | Uses PIT | Reason |
|-------|----------|--------|
| **earnings-prediction** | YES | Predicting BEFORE market reacts; cannot see returns or post-filing data |
| **earnings-attribution** | NO | Analyzing AFTER the fact to understand WHY stock moved; needs all data |

### Prediction (PIT Required)
```
Goal: Predict stock direction BEFORE seeing the reaction
Forbidden: Return data, post-filing news, analyst reactions
Required: Route ALL queries through filtered-data agent with [PIT: datetime]
```

### Attribution (No PIT)
```
Goal: Explain WHY stock moved AFTER seeing the reaction
Allowed: Return data, all news, all transcripts, full context
Direct: Call neo4j-* agents directly without filter
```

---

## Timestamp Formats by Source

| Source | Field | Format | Example |
|--------|-------|--------|---------|
| **Report** | `created` | datetime + timezone | `2023-01-04T13:48:33-05:00` |
| **News** | `created` | datetime + timezone | `2023-01-05T14:31:29-05:00` |
| **Transcript** | `created`, `conference_datetime` | datetime + timezone | `2023-01-05T08:30:00-05:00` |
| **Dividend** | `declaration_date` | date-only | `2025-04-30` |
| **Split** | `execution_date` | date-only | `2024-12-13` |
| **Date** | `date` | date-only | `2023-01-01` |
| **Perplexity** | `Date:` line | date-only | `2025-07-31` |

### Implications

1. **Datetime sources** (Report, News, Transcript): PIT filtering is precise to the second
2. **Date-only sources** (Dividend, Split, Date, Perplexity): PIT comparison uses start of day (00:00:00)
   - PIT `2025-07-31T16:30:00` vs date `2025-07-31` → date interpreted as `2025-07-31T00:00:00` → PASSES
   - This is correct: a dividend declared on date X is available from start of that day

---

## What `created` Means (Verified Against Source APIs)

### SEC Reports (sec-api.io)
```python
# ReportProcessor.py line 671:
'created': content.get('filedAt')
```
- **Source API**: sec-api.io Query API
- **API Field**: `filedAt` - "The `Accepted` attribute of a filing in ISO 8601 format, shows the date and time the filing was accepted by the EDGAR system"
- **Format**: `2019-12-06T14:41:26-05:00` (Eastern Time)
- **Meaning**: When SEC EDGAR accepted and publicly posted the filing

### News (docs.benzinga.com)
```python
# bz_news_schemas.py:
created=self.created  # REST API
created=content.created_at  # WebSocket
```
- **Source API**: Benzinga Newsfeed API v2
- **API Field**: `created` - "When the article was first published/created"
- **Format**: RFC 2822 (e.g., "Wed, 19 Nov 2025 00:49:52 -0400")
- **Meaning**: Article publication timestamp

### Transcripts (earningscall.biz)
```cypher
-- Query confirmed: created = conference_datetime for ALL transcripts
```
- **Source API**: earningscall.biz API
- **API Field**: `conference_date` - "The date and time when the earnings call/conference occurred"
- **Format**: ISO 8601 datetime (e.g., `2023-01-05T08:30:00-05:00`)
- **Meaning**: When the earnings call happened (same as `conference_datetime`)

### XBRL (Linked to Reports)
- XBRL nodes are linked to Reports via `(Report)-[:HAS_XBRL]->(XBRLNode)`
- Use Report's `created` for PIT (the SEC filing acceptance time)
- **NOT** `periodOfReport` (that's fiscal period coverage, not availability)

---

## Fields NOT for PIT (Period Coverage)

These fields indicate WHAT PERIOD a report covers, not WHEN it became available:

| Field | What It Is | Why Not PIT |
|-------|------------|-------------|
| `periodOfReport` | Fiscal period end (e.g., Q3 2024) | Q3 report might be filed in Nov |
| `start_date` | XBRL period start | Coverage period, not filing time |
| `end_date` | XBRL period end | Coverage period, not filing time |
| `fiscal_quarter`, `fiscal_year` | Reporting period | Period, not availability |

---

## Forbidden Patterns (Return Data)

These fields are PROHIBITED in prediction mode because they reveal what we're trying to predict:

```json
[
  "daily_stock", "hourly_stock", "session_stock",
  "daily_return", "daily_macro", "daily_industry", "daily_sector",
  "hourly_macro", "hourly_industry", "hourly_sector"
]
```

---

## PIT Comparison Logic

```bash
# In validate_neo4j.sh:
PIT_EPOCH=$(date -d "$PIT" +%s)
DATE_EPOCH=$(date -d "$DATE" +%s)

if [ "$DATE_EPOCH" -gt "$PIT_EPOCH" ]; then
    echo "CONTAMINATED:PIT_VIOLATION:$DATE"
fi
```

### Date-Only PIT Behavior

If PIT is date-only (e.g., `2025-07-31`):
- Interpreted as `2025-07-31T00:00:00` local time
- Any data from that day (with time > 00:00) would be REJECTED
- This is strict but correct for true point-in-time semantics

### Recommendation

Always use full datetime PIT when possible:
```
[PIT: 2025-07-31T16:30:25-04:00]  # Good - precise
[PIT: 2025-07-31]                  # Strict - rejects all of that day
```

---

## Validator Files

| File | Purpose |
|------|---------|
| `validate.sh` | Dispatcher - routes to source-specific validators |
| `validate_neo4j.sh` | JSON validation with jq, forbidden patterns + PIT dates |
| `validate_perplexity.sh` | Text validation, `Date:` line extraction for PIT |
| `rules.json` | Configuration: forbidden patterns, date fields, enable/disable |

---

## Testing

```bash
# Test forbidden pattern detection
echo '[{"daily_stock": 5.2}]' | ./validate_neo4j.sh
# Output: CONTAMINATED:daily_stock

# Test PIT compliance
echo '[{"created": "2025-08-01T10:00:00-04:00"}]' | ./validate_neo4j.sh --pit "2025-07-31T16:00:00-04:00"
# Output: CONTAMINATED:PIT_VIOLATION:2025-08-01T10:00:00-04:00

# Test clean data
echo '[{"title": "Earnings Beat", "created": "2025-07-30T10:00:00-04:00"}]' | ./validate_neo4j.sh --pit "2025-07-31T16:00:00-04:00"
# Output: CLEAN
```

---

## Disabling Validation

For debugging or attribution mode:
```json
// rules.json
{ "enabled": false }
```

The filter agent becomes a pure passthrough.

---

*Version 1.0 | 2026-01-14 | Comprehensive PIT reference*
