# Alpha Vantage PIT Safety Analysis

**Date**: 2026-01-14
**API Calls Used**: 0 (analysis based on documentation only)
**Free Tier Limit**: 10 calls/day

---

## Executive Summary

**80+ Alpha Vantage tools available. Most are UNSAFE for PIT prediction.**

Current `earnings-prediction` workflow does NOT use Alpha Vantage - it uses:
- Neo4j for historical data (already PIT-filtered)
- `perplexity-search` for consensus estimates (article dates filterable)

**Recommendation**: Do NOT add Alpha Vantage to filtered-data. Current coverage is sufficient.

---

## Complete Tool Classification

### CATEGORY 1: DEFINITELY UNSAFE (Reveal Returns)

These tools return price/market data that would reveal what we're predicting:

| Tool | Why Unsafe |
|------|------------|
| TIME_SERIES_INTRADAY | Stock prices after PIT = return data |
| TIME_SERIES_DAILY | Stock prices after PIT = return data |
| TIME_SERIES_DAILY_ADJUSTED | Stock prices after PIT = return data |
| TIME_SERIES_WEEKLY | Stock prices = return data |
| TIME_SERIES_WEEKLY_ADJUSTED | Stock prices = return data |
| TIME_SERIES_MONTHLY | Stock prices = return data |
| TIME_SERIES_MONTHLY_ADJUSTED | Stock prices = return data |
| GLOBAL_QUOTE | Current price = reveals outcome |
| REALTIME_BULK_QUOTES | Current prices = reveals outcome |
| TOP_GAINERS_LOSERS | Current market movers = reveals outcome |
| REALTIME_OPTIONS | Current options derived from prices |
| HISTORICAL_OPTIONS | Could contain post-PIT data |
| NEWS_SENTIMENT | Contains post-PIT news articles |
| ANALYTICS_FIXED_WINDOW | Analytics on price data |
| ANALYTICS_SLIDING_WINDOW | Analytics on price data |

**All Technical Indicators** (30+ tools) - Derived from price data:
- SMA, EMA, WMA, DEMA, TEMA, TRIMA, KAMA, MAMA, T3
- MACD, MACDEXT
- STOCH, STOCHF, RSI, STOCHRSI
- WILLR, ADX, ADXR, APO, PPO, MOM, BOP, CCI, CMO, ROC, ROCR
- AROON, AROONOSC, MFI, TRIX, ULTOSC, DX
- MINUS_DI, PLUS_DI, MINUS_DM, PLUS_DM
- BBANDS, MIDPOINT, MIDPRICE, SAR, VWAP
- TRANGE, ATR, NATR, AD, ADOSC, OBV
- HT_TRENDLINE, HT_SINE, HT_TRENDMODE, HT_DCPERIOD, HT_DCPHASE, HT_PHASOR

**Forex/Crypto** (8 tools) - Price data for other assets:
- CURRENCY_EXCHANGE_RATE
- FX_INTRADAY, FX_DAILY, FX_WEEKLY, FX_MONTHLY
- CRYPTO_INTRADAY
- DIGITAL_CURRENCY_DAILY, DIGITAL_CURRENCY_WEEKLY, DIGITAL_CURRENCY_MONTHLY

**Count: ~55 tools UNSAFE**

---

### CATEGORY 2: SPECIAL CASE - EARNINGS_ESTIMATES

| Tool | Real-Time Prediction | Backtesting |
|------|---------------------|-------------|
| EARNINGS_ESTIMATES | ✅ SAFE | ❌ UNSAFE |

**Why the difference**:
- Returns CURRENT consensus, not historical point-in-time
- For real-time: current consensus = pre-release consensus = SAFE
- For backtest: current consensus ≠ consensus at filing time = UNSAFE

**Fields returned**:
```
eps_estimate_average/high/low
revenue_estimate_average/high/low
eps_estimate_analyst_count
Revision trends: _7_days_ago, _30_days_ago, _60_days_ago, _90_days_ago
horizon: "next fiscal quarter", "next fiscal year", "historical fiscal quarter"
```

**Critical insight**: Revision trends are relative to TODAY, not the PIT date.

---

### CATEGORY 3: POTENTIALLY SAFE (With Date Filtering)

These have date fields that could be used for PIT filtering:

| Tool | PIT Field | Can Filter | Notes |
|------|-----------|------------|-------|
| EARNINGS | `reportedDate` | ✅ Yes | Has historical surprise data |
| DIVIDENDS | `ex_dividend_date` | ✅ Yes | Corporate action dates |
| SPLITS | `effective_date` | ✅ Yes | Split dates |
| INCOME_STATEMENT | `fiscalDateEnding` | ⚠️ Partial | Period coverage, not filing date |
| BALANCE_SHEET | `fiscalDateEnding` | ⚠️ Partial | Period coverage, not filing date |
| CASH_FLOW | `fiscalDateEnding` | ⚠️ Partial | Period coverage, not filing date |
| INSIDER_TRANSACTIONS | `transaction_date` | ✅ Yes | Has dates |
| EARNINGS_CALL_TRANSCRIPT | Quarter-based | ⚠️ Partial | Need to map quarter to date |

**Important**: `fiscalDateEnding` is the PERIOD the report covers, not when it was FILED/AVAILABLE.
- Example: Q3 2024 (period ending Sep 30) might be filed in November
- This is same issue as Neo4j `periodOfReport` - use with caution

---

### CATEGORY 4: SAFE (Static/Schedule Info)

These don't reveal returns and are generally safe:

| Tool | Notes |
|------|-------|
| EARNINGS_CALENDAR | Future earnings dates (schedule) |
| IPO_CALENDAR | Upcoming IPOs (schedule) |
| COMPANY_OVERVIEW | Static company profile |
| ETF_PROFILE | Static ETF info |
| LISTING_STATUS | Active/delisted list |
| SYMBOL_SEARCH | Ticker lookup |
| MARKET_STATUS | Market open/close status |

**Count: 7 tools SAFE**

---

### CATEGORY 5: ECONOMIC INDICATORS (Low Risk)

These don't reveal individual stock returns but have own release schedules:

| Tool | Notes |
|------|-------|
| REAL_GDP | Quarterly, scheduled release |
| REAL_GDP_PER_CAPITA | Quarterly |
| TREASURY_YIELD | Daily yields (not stock returns) |
| FEDERAL_FUNDS_RATE | Scheduled FOMC releases |
| CPI | Monthly, scheduled release |
| INFLATION | Annual |
| RETAIL_SALES | Monthly |
| DURABLES | Monthly |
| UNEMPLOYMENT | Monthly |
| NONFARM_PAYROLL | Monthly |

**Count: 10 tools LOW RISK**

---

### CATEGORY 6: COMMODITIES (Medium Risk)

Price data for commodities, not stocks directly:

| Tool | Notes |
|------|-------|
| WTI, BRENT | Oil prices |
| NATURAL_GAS | Gas prices |
| COPPER, ALUMINUM | Metal prices |
| WHEAT, CORN, COTTON, SUGAR, COFFEE | Agricultural |
| ALL_COMMODITIES | Commodity index |

Don't reveal stock returns directly, but could be used to infer sector movements.

**Count: 11 tools MEDIUM RISK**

---

## Current earnings-prediction Data Sources

| Need | Source | Status |
|------|--------|--------|
| Filing content | neo4j-report | ✅ Covered |
| Historical financials | neo4j-xbrl | ✅ Covered |
| Prior transcripts | neo4j-transcript | ✅ Covered |
| Pre-filing news | neo4j-news | ✅ Covered |
| Corporate actions | neo4j-entity | ✅ Covered |
| Consensus estimates | perplexity-search | ✅ Covered |

**All data needs are met WITHOUT Alpha Vantage.**

---

## Why perplexity-search is Better for Consensus

| Aspect | perplexity-search | EARNINGS_ESTIMATES |
|--------|------------------|-------------------|
| Point-in-time | ✅ Article dates filterable | ❌ Current consensus only |
| Backtesting | ✅ Can find pre-filing articles | ❌ Uses today's estimates |
| Format | ✅ Structured `Date:` lines | ⚠️ Unknown JSON format |
| PIT validation | ✅ Already implemented | ❌ Would need new validator |

---

## Recommendations

### Option A: Do Not Add Alpha Vantage (RECOMMENDED)

**Rationale**:
1. Current coverage via Neo4j + perplexity-search is complete
2. EARNINGS_ESTIMATES is unsafe for backtesting
3. Most tools (55+) are completely unsafe
4. Saves API calls (10/day limit)
5. No new validator needed

**Action**: No changes to filtered-data.

### Option B: Add Minimal Safe Subset

If Alpha Vantage is needed later, add ONLY:

```yaml
skills: alphavantage-safe
# Contains: EARNINGS_CALENDAR, COMPANY_OVERVIEW, SYMBOL_SEARCH
```

**Exclude**:
- All price/time series tools
- Technical indicators
- EARNINGS_ESTIMATES (current consensus)
- NEWS_SENTIMENT

### Option C: Add with Custom Validator

If historical surprise data (EARNINGS) is needed:
1. Create `validate_alphavantage.sh`
2. Check `reportedDate` against PIT
3. Add EARNINGS only to filtered-data

**Not recommended** due to complexity vs benefit.

---

## If We Test (Use Sparingly!)

Should we decide to test, prioritize these 3 calls:

1. **EARNINGS_CALENDAR** (SAFE) - Verify CSV format
2. **EARNINGS** (POTENTIALLY SAFE) - Check reportedDate format
3. **EARNINGS_ESTIMATES** - Understand structure for documentation

This would use 3 of 10 daily calls.

---

## Summary Table

| Category | Count | PIT Status | In filtered-data? |
|----------|-------|------------|-------------------|
| Price/Return Data | ~55 | ❌ UNSAFE | No |
| EARNINGS_ESTIMATES | 1 | ⚠️ Real-time only | No |
| Date-filterable | ~8 | ⚠️ Needs validator | No |
| Safe/Static | 7 | ✅ SAFE | Optional |
| Economic | 10 | ⚠️ Low risk | No |
| Commodities | 11 | ⚠️ Medium risk | No |

---

*Version 1.0 | 2026-01-14 | Analysis without API calls*
