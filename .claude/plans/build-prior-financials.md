# build_prior_financials() — Implementation Plan

**Created**: 2026-03-28
**Status**: FINAL — pending ChatGPT validation
**Builder #**: 9 of 9 in prediction-system-v2.md

---

## 0) Purpose

Provide the predictor with 4-8 prior quarters of exact-as-filed financial metrics (revenue, margins, EPS, cash flow) so it can assess YoY/QoQ trends against the current 8-K earnings release.

**Not in scope**: current quarter financials (already in `8k_packet`), forward estimates (in `build_consensus`), guidance trajectory (in `build_guidance_history`).

---

## 1) Source Hierarchy

| Priority | Source | Stored in | Coverage | PIT-safe? |
|---|---|---|---|---|
| **Primary** | XBRL Fact graph (our pipeline) | `Fact → Concept → Context → Period` nodes | 760/772 companies (98.4%) | Yes — `Report.created` timestamp |
| **Fallback 1** | FinancialStatementContent (sec-api) | `fs.value` JSON blob per statement type | Patches ~112 XBRL gaps | Yes — `fs.filed_at` is always identical to `r.created` (verified: 0 mismatches across 30K+ records, both set from `report_data['created']` in `report.py:897`). Therefore `r.created <= as_of_ts` is sufficient for PIT — no separate `fs.filed_at` filter needed. |
| **Fallback 2 (OPT-IN)** | Yahoo Finance `quarterly_income_stmt` | External API (yfinance) | All companies | No filing dates — cross-ref needed |

**Rule**: Never mix sources within the same filing. Always emit `source: "xbrl"` or `source: "fsc"` or `source: "yahoo"` per quarter row.

**Yahoo is OPT-IN only** (`--allow-yahoo` flag). Default production path: XBRL → FSC → gap. Rationale: Yahoo is vendor-normalized data, not exact-as-filed. A predictor seeing explicit gaps is more honest than silently degraded data. The `source: "yahoo"` tag mitigates this, but for "perfect predictor context" the default should be SEC-only.

---

## 2) Metric Registry — Fixed Set

Fixed set of 19 XBRL concepts + 7 computed ratios for every company. Nulls where a company doesn't report that line item. All concepts use standard `us-gaap:` namespace — validated across all 772 companies with COMPLETED XBRL.

### Income Statement (`StatementsOfIncome`) — duration periods

| Output field | XBRL concept qnames (try in order) | Companies | % |
|---|---|---|---|
| `revenue` | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `RevenueFromContractWithCustomerIncludingAssessedTax`, `RevenuesNetOfInterestExpense`, `OperatingLeaseLeaseIncome`, `RegulatedOperatingRevenue` | 765 | 99.1% |
| `cost_of_revenue` | `CostOfGoodsAndServicesSold`, `CostOfRevenue` | 533 | 69.0% |
| `gross_profit` | `GrossProfit` | 376 | 48.7% |
| `sga` | `SellingGeneralAndAdministrativeExpense`, `SellingAndMarketingExpense` | 564 | 73.1% |
| `rd_expense` | `ResearchAndDevelopmentExpense` | 311 | 40.3% |
| `depreciation_amortization` | `DepreciationAndAmortization`, `DepreciationDepletionAndAmortization` | 601 | 77.8% |
| `interest_expense` | `InterestExpense`, `InterestExpenseNonoperating`, `InterestExpenseDebt` | 519 | 67.2% |
| `income_tax` | `IncomeTaxExpenseBenefit` | 746 | 96.6% |
| `operating_income` | `OperatingIncomeLoss` | 663 | 85.9% |
| `net_income` | `NetIncomeLoss`, `ProfitLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic` | 772 | 100% |
| `eps_diluted` | `EarningsPerShareDiluted` | 746 | 96.6% |
| `diluted_shares` | `WeightedAverageNumberOfDilutedSharesOutstanding` | 751 | 97.3% |

All concept qnames above are prefixed `us-gaap:` (omitted for readability).

### Balance Sheet (`BalanceSheets`) — instant periods

| Output field | XBRL concept qnames (try in order) | Companies | % |
|---|---|---|---|
| `total_assets` | `Assets` | 772 | 100% |
| `cash_and_equivalents` | `CashAndCashEquivalentsAtCarryingValue`, `CashCashEquivalentsAndShortTermInvestments` | 706 | 91.5% |
| `long_term_debt` | `LongTermDebt`, `LongTermDebtNoncurrent`, `LongTermDebtAndCapitalLeaseObligations` | 560 | 72.5% |
| `stockholders_equity` | `StockholdersEquity` | 727 | 94.2% |

### Cash Flow Statement (`StatementsOfCashFlows`) — duration periods (YTD in Q2/Q3)

| Output field | XBRL concept qnames | Companies | % |
|---|---|---|---|
| `operating_cash_flow` | `NetCashProvidedByUsedInOperatingActivities` | 760 | 98.4% |
| `capex` | `PaymentsToAcquirePropertyPlantAndEquipment` | 587 | 76.0% |
| `buybacks` | `PaymentsForRepurchaseOfCommonStock` | 506 | 65.5% |
| `dividends_per_share` | `CommonStockDividendsPerShareDeclared` | 314 | 40.7% |

### Computed (not from XBRL — derived in Python)

| Output field | Formula | Condition |
|---|---|---|
| `free_cash_flow` | `operating_cash_flow - capex` | Both non-null |
| `gross_margin_pct` | `gross_profit / revenue * 100` | Both non-null, revenue != 0 |
| `operating_margin_pct` | `operating_income / revenue * 100` | Both non-null, revenue != 0 |
| `net_margin_pct` | `net_income / revenue * 100` | Both non-null, revenue != 0 |
| `rd_pct_revenue` | `rd_expense / revenue * 100` | Both non-null, revenue != 0 |
| `effective_tax_rate` | `income_tax / (net_income + income_tax) * 100` | Both non-null, denominator != 0 |
| `debt_to_equity` | `long_term_debt / stockholders_equity` | Both non-null, equity != 0 |

### Coverage tiers

| Tier | Metrics | Coverage | Description |
|---|---|---|---|
| Universal (>95%) | revenue, net_income, eps_diluted, diluted_shares, income_tax, total_assets, ocf | 95-100% | Every company has these |
| High (70-95%) | operating_income, sga, dep_amort, cost_of_revenue, stockholders_equity, cash, capex, long_term_debt | 69-94% | Most companies except sector-specific gaps |
| Sector-specific (<70%) | gross_profit, rd_expense, interest_expense, buybacks, dividends_per_share | 40-67% | Depends on industry — null where inapplicable |

---

## 3) Filing Selection Algorithm

### Step 1: Identify the target quarters

Given `period_of_report` (the current 8-K's fiscal period end) and `N = 8` (history depth):

```
For each of the 8 prior quarters before period_of_report:
  - Use Report.periodOfReport to identify 10-Q/10-K filings for this ticker
  - Group by periodOfReport (each period = one quarter)
  - Include both original (10-Q, 10-K) AND amendments (10-Q/A, 10-K/A)
```

### Step 2: PIT filter

- **Historical** (`as_of_ts` provided): `WHERE datetime(r.created) <= datetime($as_of_ts)`
- **Live** (`as_of_ts` is None): No cutoff filter — use ALL available filings. This is intentional: live mode benefits from the latest amendments and newly processed filings. Quarter labels are assigned correctly via `period_to_fiscal()` regardless of when the builder runs.

This naturally:
- Historical: excludes amendments not yet filed at PIT time, excludes filings that didn't exist at PIT time
- Live: uses everything available, including recent amendments — correct by design since all prior quarters' filings predate the current 8-K
- The Redis SEC quarter cache is **NOT used in PIT mode** (it collapses to latest, leaking future amendments). Live mode MAY use it for FYE month resolution only.

### Step 3: Amendment overlay — per-metric, newest-first

**Critical finding from ChatGPT's audit**: Amendments are PARTIAL corrections. 83/96 10-K/A had only ~2.9% of the original's facts. 13/23 10-Q/A had ~6.8%.

**Rule**: For each period, collect all filings (original + amendments) that passed the PIT filter. For each metric in the registry, walk filings newest-to-oldest. Use the first filing that actually contains that specific Fact.

```python
# Pseudocode for per-metric amendment overlay
for period in target_quarters:
    filings = get_filings_for_period(ticker, period, as_of_ts)  # newest first
    for metric in METRIC_REGISTRY:
        for filing in filings:  # newest first
            value = extract_fact(filing, metric.concept_qnames)
            if value is not None:
                row[metric.output_field] = value
                break  # found it, stop walking
        else:
            row[metric.output_field] = None  # no filing had this metric
```

### Step 4: XBRL status check per filing

Before attempting Fact extraction from a filing:

```
if report.xbrl_status == 'COMPLETED':
    → Try XBRL Fact path
    → If Fact count == 0 (2 known anomalies): skip to Fallback 1
elif report has FinancialStatementContent:
    → Fallback 1: parse fs.value JSON
else:
    → Fallback 2 (only if --allow-yahoo): Yahoo. Otherwise → gap.
```

**Denylist** (2 known zero-fact anomalies, from ChatGPT's audit):
- `0000885725-24-000073` (filed 2024-11-01)
- `0001616707-24-000054` (filed 2024-11-01)

---

## 4) XBRL Fact Extraction (Primary Path)

### The Cypher query

Single query to extract all metrics for all prior quarters at once:

```cypher
// Step 1: Find the 8 most recent distinct periods, then get ALL filings for those periods
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.xbrl_status = 'COMPLETED'
  AND r.periodOfReport < $current_period
  AND ($as_of IS NULL OR datetime(r.created) <= datetime($as_of))
WITH DISTINCT r.periodOfReport AS period ORDER BY period DESC LIMIT 8
WITH collect(period) AS target_periods
// Step 2: Get ALL filings for those target periods (includes amendments)
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.xbrl_status = 'COMPLETED'
  AND r.periodOfReport IN target_periods
  AND ($as_of IS NULL OR datetime(r.created) <= datetime($as_of))
// Step 3: Extract facts
MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:HAS_PERIOD]->(p:Period)
WHERE con.qname IN $concept_list
  // $concept_list = all 19 metrics from registry, fully qualified:
  // Income: us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax, us-gaap:Revenues,
  //   us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax,
  //   us-gaap:RevenuesNetOfInterestExpense, us-gaap:OperatingLeaseLeaseIncome,
  //   us-gaap:RegulatedOperatingRevenue, us-gaap:CostOfGoodsAndServicesSold,
  //   us-gaap:CostOfRevenue, us-gaap:GrossProfit,
  //   us-gaap:SellingGeneralAndAdministrativeExpense, us-gaap:SellingAndMarketingExpense,
  //   us-gaap:ResearchAndDevelopmentExpense, us-gaap:DepreciationAndAmortization,
  //   us-gaap:DepreciationDepletionAndAmortization, us-gaap:InterestExpense,
  //   us-gaap:InterestExpenseNonoperating, us-gaap:InterestExpenseDebt,
  //   us-gaap:IncomeTaxExpenseBenefit, us-gaap:OperatingIncomeLoss,
  //   us-gaap:NetIncomeLoss, us-gaap:ProfitLoss,
  //   us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic,
  //   us-gaap:EarningsPerShareDiluted, us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding
  // Balance Sheet: us-gaap:Assets, us-gaap:CashAndCashEquivalentsAtCarryingValue,
  //   us-gaap:CashCashEquivalentsAndShortTermInvestments, us-gaap:LongTermDebt,
  //   us-gaap:LongTermDebtNoncurrent, us-gaap:LongTermDebtAndCapitalLeaseObligations,
  //   us-gaap:StockholdersEquity
  // Cash Flow: us-gaap:NetCashProvidedByUsedInOperatingActivities,
  //   us-gaap:PaymentsToAcquirePropertyPlantAndEquipment,
  //   us-gaap:PaymentsForRepurchaseOfCommonStock, us-gaap:CommonStockDividendsPerShareDeclared
  AND NOT exists { (f)-[:FACT_MEMBER]->(:Member) }
  AND p.start_date IS NOT NULL
  // DO NOT filter by period duration or end_date here.
  // Return ALL periods (quarterly, YTD, annual, instant) — Python classifies and selects.
  // Reason: Q4 derivation needs annual + 9M YTD, cash flow needs H1/9M YTD,
  // balance sheet needs instant periods (end_date = 'null').
RETURN r.periodOfReport AS period,
       r.formType AS form,
       r.accessionNo AS accession,
       toString(r.created) AS filed,
       con.qname AS concept,
       f.value AS value,
       f.decimals AS decimals,
       f.context_id AS context_id,
       f.unit_ref AS unit_ref,
       p.start_date AS period_start,
       p.end_date AS period_end
ORDER BY r.periodOfReport DESC, r.created DESC, con.qname
```

**Parameters**:
- `$ticker`: company ticker
- `$current_period`: the 8-K's periodOfReport (exclude current quarter)
- `$as_of`: PIT timestamp (null for live mode)
- `$concept_list`: all ~33 us-gaap concept qnames from the metric registry (19 metrics × multiple variants)

### Consolidated filter

`NOT exists { (f)-[:FACT_MEMBER]->(:Member) }` = consolidated total (no segment dimension).

Verified working across all company types: tech (CRM), retail (WMT, COST), pharma (PFE), insurance (UNH), banks (BK via `Revenues`), PE/finance (BX, KKR), industrial (GE), consumer (NKE), chips (NVDA).

**Exception**: 24 companies where the JSON showed "segments only" for revenue — but the Fact path with the Member-exclusion filter correctly finds the consolidated total. This was a JSON-parsing artifact, not a real issue.

### Balance sheet vs income/cash flow period handling

Balance sheet items (`Assets`, `CashAndCashEquivalentsAtCarryingValue`, `LongTermDebt`, `StockholdersEquity`) use **instant** periods (a single date, not a range). The XBRL Period node has `start_date` set to the instant date and `end_date = 'null'` or same as start.

For balance sheet facts, the filter is different:
- Duration filter (`months >= 2 AND months <= 4`) does NOT apply
- Instead, match the instant date to the Report's `periodOfReport`
- Balance sheet values are point-in-time — no Q4 derivation needed (the 10-K instant value IS the Q4 balance sheet)

The Cypher query should handle both:
```
// Duration items (income + cash flow): quarterly period filter
WHERE (p.end_date <> 'null' AND duration... months >= 2 AND months <= 4)
// OR instant items (balance sheet): match to report period
   OR (p.end_date = 'null' AND p.start_date = r.periodOfReport)
```

### Period classification (in Python, NOT in Cypher)

The Cypher query returns ALL periods. Python classifies each fact using the period dates:

```python
from datetime import date

def classify_period(period_start, period_end):
    """Classify XBRL period for selection logic.

    period_end = 'null' or None → instant (balance sheet)
    Otherwise compute duration in days → classify by month-equivalent range.
    """
    if period_end is None or period_end == 'null':
        return 'instant'  # Balance sheet item

    days = (date.fromisoformat(period_end) - date.fromisoformat(period_start)).days
    if days == 0:
        return 'instant'  # Same-day instant (some filings use end_date == start_date)
    if 60 <= days <= 120:       # ~2-4 months (handles 52-week = 91 days)
        return 'quarterly'
    elif 150 <= days <= 210:    # ~5-7 months (H1 YTD)
        return 'semi_annual'
    elif 240 <= days <= 310:    # ~8-10 months (9M YTD)
        return 'nine_month'
    elif 340 <= days <= 400:    # ~11-13 months (annual, handles 52-week = 364 days)
        return 'annual'
    return 'other'
```

**Why days instead of Neo4j months**: Neo4j `duration.between().months` returns 2 for 91-day periods (52-week calendars). Day-based classification is more precise and doesn't need Neo4j computation. 60-120 day range safely covers both standard quarters (90-92 days) and 52-week quarters (84-98 days).

**52-week calendar nuance**: Neo4j `duration.between(date(...), date(...)).months` returns 2 for periods like 2025-05-04 → 2025-08-03 (91 days). Our filter `months >= 2 AND months <= 4` already handles this. Verified with FIVE (52-week, FYE January).

### Quarterly value selection — per metric (CRITICAL: current vs comparative)

**Problem**: A single 10-Q contains MULTIPLE quarterly facts for the same concept — the current quarter AND prior-year same quarter (and sometimes adjacent quarters). All pass the `months >= 2 AND months <= 4` AND `no Member` filters. Verified empirically:

- CRM 10-Q (period 2025-04-30): Revenue has 2025-02-01→2025-05-01 ($9.8B) AND 2024-02-01→2024-05-01 ($9.1B)
- BK 10-Q (period 2025-06-30): NetIncome has THREE quarterly facts (current Q2, prior Q1, prior-year Q2)

**Rule (LOCKED)**: For each filing and concept, select the fact whose `period_end` is within 7 days of the Report's `periodOfReport`. This is the CURRENT period fact. Prior-year comparatives have period_end ~365 days earlier and are excluded.

```python
# Target-period selector — prevents picking prior-year comparative
def is_target_period(fact_period_end, report_period_of_report):
    """Accept fact if period_end is within 7 days of report's periodOfReport."""
    from datetime import date
    target = date.fromisoformat(report_period_of_report)
    actual = date.fromisoformat(fact_period_end)
    return abs((actual - target).days) <= 7
```

The 7-day window handles 52-week calendars where period_end may differ from periodOfReport by 1-3 days.

**After target-period selection**: If multiple facts still match (rare — dedupe residue), apply the canonical triple dedupe from §11.

### Period selection flow (per metric, per quarter)

```
For income statement metrics:
  1. Find 'quarterly' facts matching target period (within 7 days) → use directly
  2. If none (Q4 from annual-only 10-K) → Q4 derivation (§5)

For cash flow metrics:
  1. Find 'quarterly' facts matching target period → use directly (works for Q1)
  2. If only YTD available (Q2/Q3 10-Qs):
     Q2 = semi_annual - Q1_quarterly
     Q3 = nine_month - semi_annual
  3. Q4 = annual - nine_month (from 10-K + Q3 10-Q)

For balance sheet metrics:
  1. Find 'instant' facts where period_start matches report's periodOfReport → use directly
  2. No derivation needed — instant values are point-in-time snapshots

For EPS / diluted_shares:
  1. Find 'quarterly' facts matching target period → use directly
  2. Q4: ONLY if direct quarterly fact available. NEVER derive by subtraction (see §5 hard-lock)
```

### Read-time dedupe

ChatGPT found 133 reports with duplicate facts (5,605 extra rows). Dedupe by `(concept qname, context_id, unit_ref)`:

```python
def dedupe_facts(facts):
    """Dedupe by (qname, context_id, unit_ref). Highest decimals wins."""
    seen = {}
    for f in facts:
        key = (f['concept'], f['context_id'], f['unit_ref'])
        if key not in seen:
            seen[key] = f
        else:
            # Tie-break: higher decimals = more precise
            existing_dec = int(seen[key].get('decimals') or '-99')
            new_dec = int(f.get('decimals') or '-99')
            if new_dec > existing_dec:
                seen[key] = f
    return list(seen.values())
```

---

## 5) Q4 Derivation (when 10-K has only annual periods)

Only 46 of 722 10-Ks (6.4%) include direct Q4 quarterly periods. The rest need derivation.

### Extraction order (priority)

```
For Q4 of a fiscal year:

1. DIRECT: Check 10-K (and 10-K/A) for a quarterly period (2-4 months)
   ending on/near the FY end date.
   → If found: use it. Done. (Works for 6.4% of companies)

2. FY MINUS 9M YTD: Get the annual value from 10-K + the 9-month YTD
   value from Q3 10-Q.
   → Q4 = annual_value - nine_month_ytd
   → Only 1 subtraction. Preferred over option 3.
   → Q3 10-Q always includes 9M YTD for income statement items.

3. FY MINUS Q1+Q2+Q3: Get the annual value from 10-K + individual
   quarterly values from Q1, Q2, Q3 10-Qs.
   → Q4 = annual_value - q1_value - q2_value - q3_value
   → 3 subtractions. More rounding error. Last resort.
   → Required when Q3 10-Q 9M YTD is missing for a specific metric.
```

### Where to get the 9M YTD

From the Q3 10-Q's XBRL Facts: filter for `semi_annual` or `nine_month` period type (8-10 months) with the same concept. These are YTD values that 10-Qs are required to include.

### Q4 derivation limitations

- **EPS is NOT additive** (diluted shares differ each quarter). HARD-LOCKED RULES:
  1. If direct Q4 EPS exists (3-month period in 10-K matching FY end): use it
  2. If Q4 net_income is derived AND Q4 diluted_shares is available as a direct quarterly fact: `Q4 EPS = Q4 net_income / Q4 diluted_shares`
  3. **Otherwise: Q4 `eps_diluted` = null.** NEVER use annual EPS. NEVER use annual diluted shares. NEVER compute Q4 EPS from `annual_EPS - (Q1+Q2+Q3 EPS)`. These are all mathematically wrong because EPS uses weighted average shares which differ each quarter.
  4. Same rule for `diluted_shares` itself: if not directly available for Q4 as a quarterly fact → null. Do not use annual weighted average.
- **Cash flow statements**: YTD periods exist in Q2/Q3 10-Qs. Q4 OCF = FY OCF - 9M OCF. Cash flow items ARE additive across quarters (unlike EPS).
- **Balance sheet items**: Point-in-time (instant periods), not duration. No derivation needed — Q4 balance sheet = the 10-K instant value.

---

## 6) FinancialStatementContent Fallback (Fallback 1)

Used when a filing has `xbrl_status != 'COMPLETED'` OR is in the zero-fact denylist, BUT has `FinancialStatementContent` nodes.

### Source

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
WHERE fs.statement_type IN ['StatementsOfIncome', 'StatementsOfCashFlows', 'BalanceSheets']
RETURN fs.statement_type, fs.value
```

**Balance sheet handling in FSC**: Balance sheet items use `"period": {"instant": "2025-04-30"}` (not startDate/endDate). Match `instant` to the Report's `periodOfReport`. No duration filtering needed — instant values are point-in-time.

### Parsing

`fs.value` is a JSON string. Parse with `json.loads()`. Structure:

```json
{
  "RevenueFromContractWithCustomerExcludingAssessedTax": [
    {
      "decimals": "-6",
      "unitRef": "usd",
      "period": {"startDate": "2025-02-01", "endDate": "2025-05-01"},
      "value": "9829000000"
    },
    {
      "decimals": "-6",
      "unitRef": "usd",
      "period": {"startDate": "2025-02-01", "endDate": "2025-05-01"},
      "segment": {"explicitMember": {"dimension": "...", "$t": "..."}},
      "value": "9297000000"
    }
  ]
}
```

**Same concept names as XBRL Fact nodes** but **unqualified** — FSC keys omit the `us-gaap:` prefix (e.g., `RevenueFromContractWithCustomerExcludingAssessedTax` not `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`). When matching metric registry concepts against FSC keys, strip the `us-gaap:` prefix:
```python
fsc_key = concept_qname.split(':')[1] if ':' in concept_qname else concept_qname
```

**Consolidated filter**: `"segment" not in entry` (entries without a `segment` key are consolidated totals).

**FSC instant period mapping**: Balance sheet entries have `{"period": {"instant": "2025-04-30"}}` instead of `startDate/endDate`. Map to classify_period inputs: `period_start = instant_date, period_end = None`. This triggers the `instant` classification.

**Period handling — MUST be selection-equivalent to XBRL path**:
- Parse `period.startDate`/`period.endDate` (or `period.instant` for balance sheet)
- Apply the same `classify_period()` function (day-based, handles instants)
- Apply the same **7-day target-period selector**: accept fact only if `period_end` is within 7 days of `Report.periodOfReport`. This prevents picking prior-year comparatives.
- Retain ALL period types (quarterly + YTD + annual + instant) — needed for:
  - Cash flow Q2/Q3 derivation (H1 YTD, 9M YTD)
  - Q4 derivation (annual + 9M YTD)
  - Balance sheet (instant)
- Apply the same per-metric selection flow from §4 (quarterly first, derivation fallback)

### Known limitations

- 831 of 7,624 filings are partial (missing some statement types)
- 417 filings missing StatementsOfIncome
- No built-in dedupe semantics (apply same dedupe logic as Fact path)
- Third-party derivative data (sec-api parsed it)

---

## 7) Yahoo Finance Fallback (Fallback 2)

Used when a company has no COMPLETED XBRL AND no FinancialStatementContent for a period. Primarily covers companies not yet ingested in Neo4j (~30% during backfill).

### Source

```python
import yfinance as yf
t = yf.Ticker(ticker)
inc = t.quarterly_income_stmt      # 5-6 quarters
cf = t.quarterly_cashflow          # 5-6 quarters
```

### Field mapping

```python
YAHOO_FIELD_MAP = {
    'revenue': 'Total Revenue',
    'cost_of_revenue': 'Cost Of Revenue',
    'gross_profit': 'Gross Profit',
    'sga': 'Selling General And Administration',
    'rd_expense': 'Research And Development',
    'operating_income': 'Operating Income',
    'net_income': 'Net Income',
    'eps_diluted': 'Diluted EPS',
    'diluted_shares': 'Diluted Average Shares',
    'operating_cash_flow': 'Operating Cash Flow',  # from cashflow statement
    'capex': 'Capital Expenditure',                  # from cashflow statement
}
```

### PIT safety

Yahoo has no filing dates. For PIT mode, use `_get_fye_month()` + `fiscal_math.period_to_fiscal()` to identify fiscal quarters, then cross-reference with known 10-Q/10-K filing dates from Neo4j (if available) to approximate PIT filtering. If no filing date available, apply conservative date-only exclusion: exclude any quarter whose fiscal end date is within 45 days of `as_of_ts` (10-Q filing lag).

### Source tag

All Yahoo rows get `source: "yahoo"`. The predictor knows this is normalized data, not exact as-filed.

---

## 8) Fiscal Calendar — How Quarters Map

### FYE month resolution (reuse from build_consensus)

```
Tier 1: Redis — fiscal_year_end:{TICKER} (already has day<=5 adjustment)
Tier 2: SEC EDGAR API refresh → Redis (via sec_quarter_cache_loader)
Tier 3: Yahoo Finance t.info['lastFiscalYearEnd'] with day<=5 adjustment
```

Same function: `_get_fye_month(ticker, gaps)` from `build_consensus.py:262`.

### 52/53-week calendar handling

Companies like FIVE, AAPL, NKE, COST have fiscal quarters ending on dates like Aug 2, May 3, Nov 2 (not month-end). The XBRL Period nodes have the EXACT dates. We don't need fiscal math to find period dates — XBRL gives us the actual dates.

Fiscal math (`period_to_fiscal()`) is used ONLY to:
1. **Label** periods with fiscal quarter/year (e.g., "Q2 FY2026")
2. **Identify** which Report covers which fiscal quarter when grouping
3. **Derive Q4** date boundaries (Q3 end + 1 day → FY end)

The `day <= 5` adjustment in `period_to_fiscal()` handles 52-week calendars:
- FIVE period ending 2025-08-03 → adjusted to July → Q2 (correct)
- AAPL period ending 2025-06-29 → stays June → Q3 (correct)

**Validated at 99.1%** (544/549 filings across 73 companies). Known mismatches: ACI (extreme 52-week shift), ESTC (SEC metadata error).

### How XBRL periods relate to fiscal quarters

**10-Q** includes (for each income statement concept):
- Current quarter (3-month period) — **this is what we want**
- Prior year same quarter (3-month period) — useful for YoY comparison
- YTD cumulative (6-month for Q2, 9-month for Q3) — needed for Q4 derivation
- Prior year YTD — useful for context

**10-K** includes:
- Annual period (11-13 months) — **primary**
- Individual quarterly periods (2-4 months) — **only 6.4% of companies**
- Prior year comparisons

### Which quarter does a Report cover?

**Preferred (99.97% coverage)**: Read `dei:DocumentFiscalPeriodFocus` and `dei:DocumentFiscalYearFocus` from the filing's own XBRL Fact nodes. These are the SEC's authoritative fiscal labels.

```cypher
// Add to the main XBRL query — fetch fiscal metadata alongside financial facts
OPTIONAL MATCH (r)-[:HAS_XBRL]->(x)<-[:REPORTS]-(fp_fact:Fact)-[:HAS_CONCEPT]->(fp_con:Concept {qname: 'dei:DocumentFiscalPeriodFocus'})
OPTIONAL MATCH (r)-[:HAS_XBRL]->(x)<-[:REPORTS]-(fy_fact:Fact)-[:HAS_CONCEPT]->(fy_con:Concept {qname: 'dei:DocumentFiscalYearFocus'})
// Returns fp_fact.value = "Q1"/"Q2"/"Q3"/"FY", fy_fact.value = "2026"
```

**Fallback (2 reports missing)**: `period_to_fiscal(periodOfReport, fye_month, formType)` — 99.1% accurate, handles 52-week calendars.

**Label format**: `"{fp}_FY{fy}"` → e.g., `"Q1_FY2026"`, `"Q4_FY2025"`
- When `fp = "FY"`, label as `"Q4_FY{fy}"` (10-K is always Q4)

---

## 9) Output Schema — `prior_financials.v1`

```json
{
  "schema_version": "prior_financials.v1",
  "ticker": "FIVE",
  "period_of_report": "2025-11-01",
  "as_of_ts": "2025-12-05T16:00:09-05:00",
  "source_mode": "historical",
  "quarters": [
    {
      "period": "2025-08-02",
      "fiscal_label": "Q2_FY2026",
      "primary_form": "10-Q",
      "primary_accession": "...",
      "primary_filed": "2025-08-28T15:37:34-04:00",
      "primary_source": "xbrl",
      "_provenance": {
        "revenue": {"accession": "...", "form": "10-Q", "source": "xbrl"},
        "rd_expense": {"accession": "...", "form": "10-Q", "source": "xbrl"}
      },
      "revenue": 1026847000,
      "cost_of_revenue": 684478000,
      "gross_profit": 342369000,
      "gross_margin_pct": 33.3,
      "sga": 242314000,
      "rd_expense": null,
      "depreciation_amortization": null,
      "interest_expense": null,
      "income_tax": 9603000,
      "operating_income": 52365000,
      "operating_margin_pct": 5.1,
      "net_income": 42762000,
      "net_margin_pct": 4.2,
      "eps_diluted": 0.77,
      "diluted_shares": 55389479,
      "effective_tax_rate": 18.3,
      "total_assets": 4850000000,
      "cash_and_equivalents": 320000000,
      "long_term_debt": 750000000,
      "stockholders_equity": 2100000000,
      "debt_to_equity": 0.36,
      "operating_cash_flow": null,
      "capex": null,
      "free_cash_flow": null,
      "buybacks": null,
      "dividends_per_share": null,
      "rd_pct_revenue": null,
      "derived_metrics": []
    },
    {
      "period": "2025-02-01",
      "fiscal_label": "Q4_FY2025",
      "primary_form": "10-K",
      "primary_accession": "...",
      "primary_filed": "2025-03-20T16:02:06-04:00",
      "primary_source": "xbrl",
      "derived_metrics": [
        {"metric": "revenue", "method": "fy_minus_9m_ytd", "inputs": [
          {"accession": "10K-acc", "form": "10-K", "source": "xbrl", "role": "annual"},
          {"accession": "Q3-acc", "form": "10-Q", "source": "xbrl", "role": "9m_ytd"}
        ]},
        {"metric": "operating_income", "method": "fy_minus_9m_ytd", "inputs": ["...same..."]},
        {"metric": "operating_cash_flow", "method": "fy_minus_9m_ytd", "inputs": ["...same..."]}
      ],
      "revenue": 1390885000,
      "operating_income": 246764000,
      "..."
    }
  ],
  "summary": {
    "quarter_count": 8,
    "primary_source_breakdown": {"xbrl": 7, "fsc": 1, "yahoo": 0},
    "derived_metric_count": 6,
    "metrics_coverage": {
      "revenue": 8, "net_income": 8, "eps_diluted": 8, "operating_income": 8,
      "total_assets": 8, "income_tax": 8, "operating_cash_flow": 4,
      "gross_profit": 6, "sga": 8, "cost_of_revenue": 8,
      "depreciation_amortization": 6, "interest_expense": 4,
      "cash_and_equivalents": 8, "long_term_debt": 8, "stockholders_equity": 8,
      "capex": 4, "buybacks": 4, "dividends_per_share": 0, "rd_expense": 0
    }
  },
  "gaps": [
    {"type": "missing_metric", "period": "2025-02-01", "metric": "operating_cash_flow",
     "reason": "10-K cash flow is annual only, Q4 derivation requires Q3 9M YTD which is unavailable for this metric"}
  ],
  "segment_inventory": {
    "source_quarter": "2025-08-02",
    "revenue": {"concept": "us-gaap:RevenueFromContractWithCustomer...", "axes": {"srt:ProductOrServiceAxis": {"kind": "product_service", "members": ["..."]}, "srt:StatementGeographicalAxis": {"kind": "geography", "members": ["..."]}}},
    "operating_income": {"concept": "us-gaap:OperatingIncomeLoss", "axes": {}}
  },
  "assembled_at": "2026-03-28T14:00:00-04:00"
}
```

### Field semantics

- `period`: the fiscal period end date (from `Report.periodOfReport`)
- `fiscal_label`: human-readable label. Preferred source: `dei:DocumentFiscalPeriodFocus` + `dei:DocumentFiscalYearFocus` from XBRL (99.97% coverage). Fallback: `period_to_fiscal()` computation (99.1%).
- `primary_form`: the main filing type for this quarter (10-Q, 10-K, 10-Q/A, 10-K/A)
- `primary_accession`: the main filing's accession number
- `primary_filed`: exact filing timestamp (from `Report.created`)
- `_provenance`: per-metric dict mapping output field → source info. Three shapes:
  - **Simple** (single filing): `{"revenue": {"accession": "...", "form": "10-Q"}}` — when amendment overlay caused different metrics to come from different filings
  - **Derived** (Q4 from multiple filings): `{"revenue": {"derived": true, "method": "fy_minus_9m_ytd", "inputs": [{"accession": "10K-acc", "form": "10-K", "source": "xbrl", "role": "annual"}, {"accession": "Q3-acc", "form": "10-Q", "source": "xbrl", "role": "9m_ytd"}]}}`
  - **Omitted** (empty {} or absent): when all metrics come from the same filing and none are derived
- `primary_source`: the dominant data source for this quarter (`xbrl`, `fsc`, `yahoo`). In rare cases where per-metric amendment overlay mixes sources, individual `_provenance` entries carry their own `source` field.
- `_provenance` population rule: After extracting all metrics for a quarter, check if all metrics came from the same filing (same accession). If yes → `_provenance` is empty `{}` (omit). If any metric came from a different filing (amendment overlay) OR any metric was derived → populate `_provenance` for ALL metrics in that row. This makes it unambiguous: empty = all same source, populated = something non-trivial happened.
- `derived_metrics`: array of derivation records. Empty `[]` when all metrics are direct. Each entry:
  - `metric`: which output field was derived (e.g., `"revenue"`, `"operating_cash_flow"`)
  - `method`: `"fy_minus_9m_ytd"`, `"fy_minus_q1q2q3"`, `"h1_ytd_minus_q1"` (cash flow Q2), `"9m_ytd_minus_h1"` (cash flow Q3)
  - `inputs`: array of `{accession, form, source, role}` for each filing used. `source` is `"xbrl"` or `"fsc"` per input — enables full reconstruction even when derivation mixes sources.
  - Covers ALL derivation types: Q4 from 10-K, cash flow Q2/Q3 from YTD subtraction. Not just Q4.
- All financial values: raw numbers (no formatting). Null if not available.
- All percentages: pre-computed, rounded to 1 decimal.

### Row ordering

Newest quarter first (descending by period). Same as `build_consensus()`.

### Row count

Target 8 quarters. If fewer available (new company, incomplete backfill), return what exists. Minimum 1 (the most recent prior quarter).

---

## 10) Implementation Details

### File location

`scripts/earnings/build_prior_financials.py` — same directory as `build_consensus.py`, `peer_earnings_snapshot.py`, `macro_snapshot.py`.

### Function signature

```python
def build_prior_financials(ticker: str, quarter_info: dict,
                           as_of_ts: str | None = None,
                           out_path: str | None = None) -> dict:
    """
    Args:
        ticker: company ticker
        quarter_info: dict with 'period_of_report', 'filed_8k', 'market_session', 'quarter_label'
        as_of_ts: ISO8601 timestamp for PIT (None = live mode)
        out_path: output file path (None = /tmp/prior_financials_{TICKER}.json)

    Returns:
        prior_financials.v1 dict
    """
```

### Dependencies

- `neograph.Neo4jConnection.get_manager()` — for XBRL Fact queries
- `fiscal_math.period_to_fiscal()`, `fiscal_math._compute_fiscal_dates()` — for quarter labeling
- `_get_fye_month()` — reuse from build_consensus (or extract to shared module)
- `yfinance` — for Yahoo fallback (only when `--allow-yahoo`)
- `redis` — for FYE month cache (Tier 1)
- Standard library: `json`, `os`, `sys`, `datetime`, `tempfile`

### CLI interface

```bash
# Live mode (auto-derives period_of_report from most recent 8-K Item 2.02):
python3 scripts/earnings/build_prior_financials.py FIVE

# Historical PIT:
python3 scripts/earnings/build_prior_financials.py FIVE --pit 2025-12-05T16:00:09-05:00

# With explicit output path:
python3 scripts/earnings/build_prior_financials.py FIVE --pit 2025-12-05T16:00:09-05:00 --out-path /tmp/test.json

# With explicit period of report:
python3 scripts/earnings/build_prior_financials.py FIVE --period-of-report 2025-11-02

# With Yahoo fallback enabled:
python3 scripts/earnings/build_prior_financials.py FIVE --allow-yahoo
```

**CLI `period_of_report` auto-resolution** (when `--period-of-report` not provided):
```python
# Query Neo4j for the most recent 8-K with Item 2.02 for this ticker
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '8-K' AND r.items CONTAINS 'Item 2.02'
RETURN r.periodOfReport ORDER BY r.created DESC LIMIT 1
```
If no 8-K exists, exit with error: `"No 8-K Item 2.02 found for {ticker}"`

**`--allow-yahoo`**: Boolean flag (no value). When present, Yahoo Finance is used as Fallback 2 after XBRL and FSC. When absent (default), missing data emits gaps instead.

### Atomic write

Same pattern as all other builders: write to temp file, `os.replace()` to final path.

### Error handling

- No XBRL and no FSC → return empty quarters array + gap note (Yahoo only if `--allow-yahoo`)
- Partial data (some metrics missing) → null fields + metrics_coverage in summary
- Q4 derivation fails (missing 9M YTD) → null for that metric + gap note with reason
- Neo4j connection failure → gap (NOT silent Yahoo fallback). Yahoo only with explicit `--allow-yahoo`
- When `--allow-yahoo` enabled and Yahoo also fails → return what we have from XBRL/FSC

**Gap entry shapes**:
```python
# Missing metric for a specific period
{"type": "missing_metric", "period": "2025-02-01", "metric": "operating_cash_flow",
 "reason": "10-K cash flow is annual only, Q4 derivation requires Q3 9M YTD which is unavailable"}

# No data at all for a period
{"type": "missing_period", "period": "2024-04-30",
 "reason": "No COMPLETED XBRL or FSC for this period"}

# Connection failure
{"type": "connection_failure", "source": "neo4j",
 "reason": "Neo4j connection failed: [error message]"}

# Zero-fact anomaly
{"type": "zero_facts", "accession": "0000885725-24-000073",
 "reason": "COMPLETED report has 0 usable facts (known anomaly)"}
```

---

## 11) Dedupe Guard

From ChatGPT's audit: 133 reports have duplicate facts (5,605 extra rows total, max 143 per report).

### Dedupe key

`(concept qname, context_id, unit_ref)` — the canonical triple.

### Tie-break

1. Highest `decimals` value (more precise)
2. If still tied: more significant digits in `value` string
3. If still tied: first encountered (deterministic from query ORDER BY)

### Zero-fact guard

After dedupe, if a COMPLETED report has 0 usable facts → skip it, add to gaps, try next filing for that period.

Hardcoded denylist for 2 known anomalies:
```python
ZERO_FACT_DENYLIST = {
    '0000885725-24-000073',
    '0001616707-24-000054',
}
```

---

## 12) Amendment Rules

### Amendment identification

- `formType` ends with `/A`: `10-Q/A`, `10-K/A`
- Same `periodOfReport` as the original filing
- Has its own `Report.created` timestamp (always after original)

### Amendment overlay — per-metric

Amendments are PARTIAL corrections. 83/96 10-K/A had only ~2.9% of original facts.

**DO NOT replace entire original with amendment.**

**DO**: For each metric and period, walk filings newest-created-first. Use the first filing that contains that specific concept's Fact.

```python
# For a given periodOfReport, filings sorted by created DESC:
# [10-Q/A (2024-11-15), 10-Q (2024-08-28)]
#
# For revenue: 10-Q/A has it → use 10-Q/A value
# For R&D: 10-Q/A doesn't have it → fall through to 10-Q → use 10-Q value
# For gross_profit: neither has it → null
```

### PIT interaction

Amendments are only visible if `datetime(amendment.created) <= datetime($as_of_ts)`. A 10-Q/A filed on Nov 15 is invisible to a PIT of Oct 1 — the original 10-Q value is used.

---

## 13) Cash Flow — YTD Nuance

Cash flow statements in 10-Qs report YTD figures, not quarterly:
- Q1 10-Q: 3-month cash flow (= Q1)
- Q2 10-Q: 6-month YTD cash flow (= H1, not Q2 alone)
- Q3 10-Q: 9-month YTD cash flow

To get quarterly cash flow:
- Q1: direct (= YTD)
- Q2: H1 YTD - Q1
- Q3: 9M YTD - H1 YTD
- Q4: FY - 9M YTD

This applies to `operating_cash_flow` and `capex`. The builder must detect YTD periods and derive quarterly values by subtraction when needed.

**Where YTD values come from**: The SAME filing that reports for that quarter. A Q2 10-Q contains both the Q2 target-period facts AND the H1 YTD facts — they're in the same query results, from the same `periodOfReport`. No separate filing lookup needed. The builder groups all facts by `(periodOfReport, concept)`, classifies each by period type, and picks quarterly if available or derives from YTD if not.

**Income statement** does NOT have this problem — 10-Qs include direct quarterly periods for income items.

---

## 14) Testing Plan

### Unit tests (synthetic data)

1. Normal 10-Q extraction — 3 months, consolidated, all metrics
2. 52-week calendar — period shows 2 months in Neo4j (FIVE, AAPL)
3. Amendment overlay — 10-Q/A has corrected revenue, original has R&D
4. Q4 derivation — FY minus 9M YTD path
5. Q4 derivation — FY minus Q1+Q2+Q3 fallback
6. PIT filter — excludes future amendment
7. Zero-fact report — skipped, falls to FSC fallback
8. Yahoo fallback — company with no XBRL
9. Empty result — no data at all

### Integration tests (live Neo4j)

10. CRM — tech, standard month-end FYE (January)
11. FIVE — retail, 52-week calendar (January FYE, periods ending on non-month-end dates)
12. AAPL — tech, 52-week calendar (September FYE)
13. WMT — retail, 52-week calendar (January FYE), `Revenues` concept (not `RevenueFromContract...`)
14. CVS — healthcare, was "segments only" in JSON but works via Fact path
15. BX — PE/finance, limited metrics (no OpIncome, no GrossProfit)
16. NVDA — chips, very high margins, `Revenues` concept
17. AAP — has both 10-K and 10-K/A for same period (amendment test)
18. Historical PIT — CRM at 2 different PIT dates, verify different rows visible
19. Cross-validate XBRL vs Yahoo for same quarter (revenue should match within 1%)

### Coverage test

20. Run on all 772 companies with COMPLETED XBRL — verify revenue extracted for ≥98%

---

## 15) What This Builder Does NOT Do

- Does NOT provide current quarter financials (that's `8k_packet`)
- Does NOT provide consensus estimates (that's `build_consensus`)
- Does NOT provide guidance trajectory (that's `build_guidance_history`)
- Does NOT provide segment breakdowns (that's `neo4j-xbrl` agent via fetch plan)
- Does NOT provide non-GAAP metrics (those are in the 8-K press release text)
- Does NOT try to match 8-K line items to XBRL concepts (fixed registry, nulls where missing)
- Does NOT use the Redis SEC quarter cache in PIT mode (PIT-unsafe)

---

## 16) Segment Inventory (metadata only, no values)

The builder includes a lightweight **segment inventory** for the most recent quarter. This is NOT segment values — just a list of what segment members exist for key concepts. Enables the planner to pass exact member qnames to the neo4j-xbrl agent without a discovery step.

### Which concepts get segment inventory

| Concept | Companies with segments | Avg members | Include? |
|---|---|---|---|
| Revenue | ~650 | 9 | **YES** — #1 segment dimension in 8-Ks |
| OperatingIncomeLoss | 266 | 4.2 | **YES** — segment profitability |
| Assets | 264 | 4.9 | **NO** — mostly structural, not actionable |
| Others (COGS, SGA, R&D, OCF) | <278 | <4 | **NO** — rarely segmented in 8-Ks |

### How it's built

The segment inventory is extracted from the **most recent prior quarter's filing** (the same filing already identified by the builder's main selection logic).

**Step 1 — Get member qnames + labels** (from the XBRL Fact graph, always available for COMPLETED reports):
```cypher
// Run for revenue AND operating income concepts.
// revenue_concept_found = whichever concept qname was successfully used to extract
// consolidated revenue for this quarter (from the metric registry priority chain).
// The builder already knows this from the main extraction loop.
MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:FACT_MEMBER]->(m:Member)
WHERE con.qname IN [revenue_concept_found, 'us-gaap:OperatingIncomeLoss']
RETURN DISTINCT con.qname AS concept, m.qname AS member_qname, m.label AS member_label
```

**Step 2 — Get axis grouping** (three-tier fallback):
1. **Primary: FSC JSON** — parse `segment.explicitMember.dimension` field from `FinancialStatementContent.value`. Gives exact axis per member (e.g., `srt:ProductOrServiceAxis` for `crm:SalesCloudMember`).
2. **Fallback: Static standard member map** — for known `us-gaap:`/`srt:` members, the axis is deterministic:
   ```python
   STANDARD_MEMBER_AXIS = {
       'srt:AmericasMember': 'srt:StatementGeographicalAxis',
       'srt:EuropeMember': 'srt:StatementGeographicalAxis',
       'us-gaap:ProductMember': 'srt:ProductOrServiceAxis',
       'us-gaap:ServiceMember': 'srt:ProductOrServiceAxis',
       'us-gaap:OperatingSegmentsMember': 'srt:ConsolidationItemsAxis',
       # ... ~13 standard members with known axes
   }
   ```
3. **Default: `unknown` axis** — for custom members not in FSC and not in the standard map. Grouped under `"unknown_axis"` with `kind: "business"`. Planner still gets the qname + label for matching.

This ensures operating_income inventory works even without FSC parsing (Step 1 gives members, Step 2 fallback classifies them).

### Standard axis classification

```python
AXIS_KIND = {
    'srt:ProductOrServiceAxis': 'product_service',
    'srt:StatementGeographicalAxis': 'geography',
    'us-gaap:StatementBusinessSegmentsAxis': 'business_segment',
    'srt:ConsolidationItemsAxis': 'structural',
    'us-gaap:ContractWithCustomerSalesChannelAxis': 'channel',
}
```

### Output shape (axis-grouped, not flat)

```json
"segment_inventory": {
  "source_quarter": "2025-04-30",
  "revenue": {
    "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "axes": {
      "srt:ProductOrServiceAxis": {
        "kind": "product_service",
        "members": [
          {"qname": "crm:SalesCloudMember", "label": "Sales Cloud"},
          {"qname": "crm:ServiceCloudMember", "label": "Service Cloud"},
          {"qname": "crm:SalesforcePlatformandOtherMember", "label": "Salesforce Platform and Other"},
          {"qname": "crm:MarketingandCommerceCloudMember", "label": "Marketing and Commerce Cloud"},
          {"qname": "crm:IntegrationAndAnalyticsMember", "label": "Integration and Analytics"},
          {"qname": "crm:SubscriptionandSupportMember", "label": "Subscription and Support"},
          {"qname": "crm:ProfessionalServicesandOtherMember", "label": "Professional Services and Other"}
        ]
      },
      "srt:StatementGeographicalAxis": {
        "kind": "geography",
        "members": [
          {"qname": "srt:AmericasMember", "label": "Americas"},
          {"qname": "srt:EuropeMember", "label": "Europe"},
          {"qname": "srt:AsiaPacificMember", "label": "Asia Pacific"}
        ]
      }
    }
  },
  "operating_income": {
    "concept": "us-gaap:OperatingIncomeLoss",
    "axes": {}
  }
}
```

**Key design rules**:
- **Axis-grouped, not flat** — planner knows "Sales Cloud" is a product, "Americas" is a geography. No ambiguity.
- **Labels included** — planner matches 8-K text ("Sales Cloud grew 7%") against label ("Sales Cloud"), not qname.
- **Structural members flagged** — `OperatingSegmentsMember`, `IntersegmentEliminationMember`, `CorporateNonSegmentMember` get `kind: "structural"` so planner doesn't confuse them with business segments.
- **Only from most recent quarter** — segment structure rarely changes quarter-to-quarter.
- **Empty axes = no segments** — honest absence.
- **Null segment_inventory** if company has no segment data at all.

### How the planner uses this

The planner reads the 8-K: "Sales Cloud revenue grew 7% YoY." It scans `segment_inventory.revenue.axes["srt:ProductOrServiceAxis"].members` and finds `{"qname": "crm:SalesCloudMember", "label": "Sales Cloud"}`. It generates:

```json
{
  "id": "cloud_segment_trend",
  "question": "CRM Sales Cloud vs Service Cloud revenue trend",
  "fetch": [[{
    "agent": "neo4j-xbrl",
    "query": "Get CRM revenue for members crm:SalesCloudMember and crm:ServiceCloudMember for last 4 quarters using concept us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
  }]]
}
```

The agent receives exact concept + member qnames → uses the `segment_values_by_member` template from xbrl-queries skill → 5 seconds, no discovery.

---

## 17) Open Items — None

All design decisions are locked (including fixes from ChatGPT validation round):
- Source hierarchy: XBRL → FSC → gap (Yahoo opt-in only) ✓
- Metric registry: 19 metrics (33 concept qnames including variants) + 7 computed ratios ✓
- Amendment handling: per-metric newest-first ✓
- Q4 derivation: direct → FY-9M → FY-sum ✓
- Period filter: 2-4 months = quarterly ✓
- Consolidated filter: no FACT_MEMBER ✓
- Dedupe: canonical triple + decimals tie-break ✓
- PIT: Report.created filter ✓
- Cash flow: YTD derivation for Q2/Q3/Q4 ✓
- Fiscal math: reuse period_to_fiscal() for labeling only ✓
- Target-period selector: period_end within 7d of periodOfReport (prevents prior-year comparative selection) ✓
- Per-metric provenance: `_provenance` dict when amendment overlay splits sources ✓
- Yahoo: opt-in only (`--allow-yahoo`), default is XBRL/FSC → gap ✓
- FSC fallback: includes BalanceSheets + instant period handling ✓
- Q4 derived provenance: `inputs` array with every filing used ✓
- Quarter labels: prefer dei:DocumentFiscalPeriodFocus (99.97%), fallback period_to_fiscal() ✓
- Live mode: no cutoff, all filings available, correct quarter labels ✓
- Q4 EPS: hard-locked null when direct quarterly ingredients unavailable ✓
- Same-day instants: `days == 0` classified as instant ✓
- FSC selection-equivalent: 7-day target-period + all period types + same per-metric flow ✓
- derived_metrics: covers Q4, cash flow Q2/Q3, any derivation type ✓
- primary_source + per-metric source in _provenance: handles mixed-source quarters ✓
- Distinct-period query: no hard LIMIT, logically airtight period selection ✓
- segment_inventory: 3-tier axis resolution (FSC → standard map → unknown) ✓
- segment_inventory in top-level schema ✓
