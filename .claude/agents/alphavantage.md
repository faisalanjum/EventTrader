# Alpha Vantage MCP Agent

## Overview
Remote MCP server providing real-time and historical financial market data via Alpha Vantage API.

**MCP URL:** `https://mcp.alphavantage.co/mcp?apikey=OEBNGLV527FIER4J`
**Type:** HTTP (remote)
**Rate Limit (Free):** 25 requests/day
**Config:** `.mcp.json` → `alphavantage`

---

## Tool Categories

| Category | Tools | Use Case |
|----------|-------|----------|
| Stock Time Series | 9 | Price history, quotes |
| Fundamental Data | 10 | Financials, earnings, estimates |
| Calendars & Market | 5 | Upcoming events, market status |
| News & Sentiment | 2 | News with sentiment scores |
| Options | 2 | Options chains with Greeks |
| Forex | 5 | Currency exchange rates |
| Crypto | 5 | Digital currency prices |
| Commodities | 11 | Oil, metals, agriculture |
| Economic Indicators | 9 | GDP, CPI, employment |
| Technical Indicators | 50+ | Moving averages, momentum, etc. |
| Analytics | 2 | Advanced metrics |
| Utility | 4 | Search, health check |

---

## Stock Time Series

### TIME_SERIES_INTRADAY
Returns 20+ years of historical intraday OHLCV data.
- **Required:** `symbol`, `interval` (1min, 5min, 15min, 30min, 60min)
- **Optional:** `adjusted`, `extended_hours`, `month`, `outputsize`, `datatype`, `entitlement`

### TIME_SERIES_DAILY
Returns raw daily OHLCV covering 20+ years.
- **Required:** `symbol`
- **Optional:** `outputsize` (compact=100pts, full=20+yrs), `datatype`, `entitlement`

### TIME_SERIES_DAILY_ADJUSTED
Daily OHLCV with adjusted close, splits, and dividends.
- **Required:** `symbol`
- **Optional:** `outputsize`, `datatype`, `entitlement`

### TIME_SERIES_WEEKLY
Weekly OHLCV (last trading day of each week).
- **Required:** `symbol`
- **Optional:** `datatype`, `entitlement`

### TIME_SERIES_WEEKLY_ADJUSTED
Weekly with adjusted close, volume, dividend.
- **Required:** `symbol`
- **Optional:** `datatype`, `entitlement`

### TIME_SERIES_MONTHLY
Monthly OHLCV (last trading day of each month).
- **Required:** `symbol`
- **Optional:** `datatype`, `entitlement`

### TIME_SERIES_MONTHLY_ADJUSTED
Monthly with adjusted close, volume, dividend.
- **Required:** `symbol`
- **Optional:** `datatype`, `entitlement`

### GLOBAL_QUOTE
Latest price and volume for a ticker.
- **Required:** `symbol`
- **Optional:** `datatype`, `entitlement`

### REALTIME_BULK_QUOTES
Realtime quotes for up to 100 symbols.
- **Required:** `symbol` (comma-separated, e.g., "MSFT,AAPL,IBM")
- **Optional:** `datatype`, `entitlement`

---

## Fundamental Data

### COMPANY_OVERVIEW
Company info, financial ratios, and key metrics.
- **Required:** `symbol`
- **Returns:** Description, sector, industry, market cap, P/E, EPS, dividend yield, 52-week high/low, etc.

### INCOME_STATEMENT
Annual and quarterly income statements.
- **Required:** `symbol`
- **Returns:** Revenue, gross profit, operating income, net income, EPS, etc.

### BALANCE_SHEET
Annual and quarterly balance sheets.
- **Required:** `symbol`
- **Returns:** Total assets, liabilities, equity, cash, debt, etc.

### CASH_FLOW
Annual and quarterly cash flow statements.
- **Required:** `symbol`
- **Returns:** Operating, investing, financing cash flows, capex, dividends, etc.

### EARNINGS
Annual and quarterly EPS with historical estimates and surprises.
- **Required:** `symbol`
- **Returns:**
  - `reportedEPS` - Actual EPS
  - `estimatedEPS` - Consensus estimate (historical)
  - `surprise` - Beat/miss amount
  - `surprisePercentage` - Beat/miss %
  - `reportTime` - pre-market/post-market

### EARNINGS_ESTIMATES ⭐
**Forward-looking consensus estimates for EPS and revenue.**
- **Required:** `symbol`
- **Returns:**
  - `eps_estimate_average` / `high` / `low`
  - `revenue_estimate_average` / `high` / `low`
  - `eps_estimate_analyst_count`
  - Estimate revisions (7/30/60/90 days ago)
  - Revision counts (up/down trailing 7/30 days)
- **Horizons:** next quarter, current year, next year

### DIVIDENDS
Historical and declared future dividends.
- **Required:** `symbol`
- **Optional:** `datatype`

### SPLITS
Historical stock split events.
- **Required:** `symbol`
- **Optional:** `datatype`

### ETF_PROFILE
ETF metrics, holdings, allocation by asset/sector.
- **Required:** `symbol`

### INSIDER_TRANSACTIONS
Insider buying/selling by key stakeholders.
- **Required:** `symbol`

---

## Calendars & Market Info

### EARNINGS_CALENDAR
Upcoming earnings in next 3, 6, or 12 months.
- **Optional:** `symbol` (filter by ticker), `horizon` (3month, 6month, 12month)

### IPO_CALENDAR
Upcoming IPOs in next 3 months.
- **Required:** none

### LISTING_STATUS
Active or delisted US stocks and ETFs.
- **Optional:** `state` (active/delisted), `date`

### MARKET_STATUS
Current market status (open/closed) for global trading venues.
- **Optional:** `entitlement`

### TOP_GAINERS_LOSERS
Top 20 gainers, losers, and most active tickers.
- **Required:** none

---

## News & Sentiment

### NEWS_SENTIMENT
Market news with sentiment scores from premier outlets.
- **Optional:**
  - `tickers` - Filter by symbols (e.g., "IBM" or "COIN,CRYPTO:BTC")
  - `topics` - Filter by topic (technology, ipo, earnings, etc.)
  - `time_from` / `time_to` - Date range (YYYYMMDDTHHMM format)
  - `sort` - LATEST, EARLIEST, RELEVANCE
  - `limit` - Number of results (default 50, max 1000)

### EARNINGS_CALL_TRANSCRIPT
Full earnings call transcript for a specific quarter.
- **Required:** `symbol`, `quarter` (format: "2024Q1")
- **Note:** Supports quarters since 2010Q1

---

## Options

### REALTIME_OPTIONS
Realtime US options chain with full market coverage.
- **Required:** `symbol`
- **Optional:** `contract` (specific contract ID), `require_greeks` (include Greeks/IV), `datatype`, `entitlement`

### HISTORICAL_OPTIONS
Historical options chain for a specific date.
- **Required:** `symbol`
- **Optional:** `date` (YYYY-MM-DD), `datatype`, `entitlement`

---

## Forex

### CURRENCY_EXCHANGE_RATE
Realtime exchange rate for any currency pair.
- **Required:** `from_currency`, `to_currency`
- **Optional:** `datatype`
- **Example:** from_currency=EUR, to_currency=USD

### FX_INTRADAY
Intraday FX OHLC, updated realtime.
- **Required:** `from_symbol`, `to_symbol`, `interval` (1min, 5min, 15min, 30min, 60min)
- **Optional:** `outputsize`, `datatype`

### FX_DAILY
Daily FX OHLC.
- **Required:** `from_symbol`, `to_symbol`
- **Optional:** `outputsize`, `datatype`

### FX_WEEKLY
Weekly FX OHLC.
- **Required:** `from_symbol`, `to_symbol`
- **Optional:** `datatype`

### FX_MONTHLY
Monthly FX OHLC.
- **Required:** `from_symbol`, `to_symbol`
- **Optional:** `datatype`

---

## Cryptocurrency

### CRYPTO_INTRADAY
Intraday crypto OHLCV, updated realtime.
- **Required:** `symbol` (e.g., ETH), `market` (e.g., USD), `interval`
- **Optional:** `outputsize`, `datatype`

### DIGITAL_CURRENCY_DAILY
Daily crypto prices in market currency and USD.
- **Required:** `symbol` (e.g., BTC), `market` (e.g., EUR)
- **Optional:** `datatype`

### DIGITAL_CURRENCY_WEEKLY
Weekly crypto prices.
- **Required:** `symbol`, `market`
- **Optional:** `datatype`

### DIGITAL_CURRENCY_MONTHLY
Monthly crypto prices.
- **Required:** `symbol`, `market`
- **Optional:** `datatype`

---

## Commodities

| Tool | Description | Intervals |
|------|-------------|-----------|
| `WTI` | West Texas Intermediate crude oil | daily, weekly, monthly |
| `BRENT` | Brent (Europe) crude oil | daily, weekly, monthly |
| `NATURAL_GAS` | Henry Hub natural gas | daily, weekly, monthly |
| `COPPER` | Global copper price | monthly, quarterly, annual |
| `ALUMINUM` | Global aluminum price | monthly, quarterly, annual |
| `WHEAT` | Global wheat price | monthly, quarterly, annual |
| `CORN` | Global corn price | monthly, quarterly, annual |
| `COTTON` | Global cotton price | monthly, quarterly, annual |
| `SUGAR` | Global sugar price | monthly, quarterly, annual |
| `COFFEE` | Global coffee price | monthly, quarterly, annual |
| `ALL_COMMODITIES` | Global commodity index | monthly, quarterly, annual |

**All commodity tools:**
- **Optional:** `interval`, `datatype`

---

## Economic Indicators (US)

| Tool | Description | Intervals |
|------|-------------|-----------|
| `REAL_GDP` | US Real GDP | annual, quarterly |
| `REAL_GDP_PER_CAPITA` | US GDP per capita | quarterly |
| `TREASURY_YIELD` | US Treasury yields | daily, weekly, monthly |
| `FEDERAL_FUNDS_RATE` | Fed interest rate | daily, weekly, monthly |
| `CPI` | Consumer Price Index | monthly, semiannual |
| `INFLATION` | Annual inflation rates | annual |
| `RETAIL_SALES` | Monthly retail sales | monthly |
| `DURABLES` | Durable goods orders | monthly |
| `UNEMPLOYMENT` | Unemployment rate | monthly |
| `NONFARM_PAYROLL` | Total nonfarm payroll | monthly |

**TREASURY_YIELD maturities:** 3month, 2year, 5year, 7year, 10year, 30year

---

## Technical Indicators

### Moving Averages
| Tool | Description | Required |
|------|-------------|----------|
| `SMA` | Simple Moving Average | symbol, interval, time_period, series_type |
| `EMA` | Exponential Moving Average | symbol, interval, time_period, series_type |
| `WMA` | Weighted Moving Average | symbol, interval, time_period, series_type |
| `DEMA` | Double EMA | symbol, interval, time_period, series_type |
| `TEMA` | Triple EMA | symbol, interval, time_period, series_type |
| `TRIMA` | Triangular Moving Average | symbol, interval, time_period, series_type |
| `KAMA` | Kaufman Adaptive MA | symbol, interval, time_period, series_type |
| `MAMA` | MESA Adaptive MA | symbol, interval, series_type |
| `T3` | Triple EMA (T3) | symbol, interval, time_period, series_type |
| `VWAP` | Volume Weighted Avg Price | symbol, interval |

### Momentum Indicators
| Tool | Description | Required |
|------|-------------|----------|
| `MACD` | Moving Avg Convergence/Divergence | symbol, interval, series_type |
| `MACDEXT` | MACD with MA type control | symbol, interval, series_type |
| `RSI` | Relative Strength Index | symbol, interval, time_period, series_type |
| `STOCH` | Stochastic Oscillator | symbol, interval |
| `STOCHF` | Stochastic Fast | symbol, interval |
| `STOCHRSI` | Stochastic RSI | symbol, interval, time_period, series_type |
| `WILLR` | Williams %R | symbol, interval, time_period |
| `MOM` | Momentum | symbol, interval, time_period, series_type |
| `ROC` | Rate of Change | symbol, interval, time_period, series_type |
| `ROCR` | Rate of Change Ratio | symbol, interval, time_period, series_type |
| `CMO` | Chande Momentum Oscillator | symbol, interval, time_period, series_type |
| `MFI` | Money Flow Index | symbol, interval, time_period |
| `ULTOSC` | Ultimate Oscillator | symbol, interval |
| `BOP` | Balance of Power | symbol, interval |
| `CCI` | Commodity Channel Index | symbol, interval, time_period |
| `TRIX` | Triple Smooth EMA ROC | symbol, interval, time_period, series_type |

### Trend Indicators
| Tool | Description | Required |
|------|-------------|----------|
| `ADX` | Average Directional Index | symbol, interval, time_period |
| `ADXR` | ADX Rating | symbol, interval, time_period |
| `AROON` | Aroon Indicator | symbol, interval, time_period |
| `AROONOSC` | Aroon Oscillator | symbol, interval, time_period |
| `DX` | Directional Movement Index | symbol, interval, time_period |
| `PLUS_DI` | Plus Directional Indicator | symbol, interval, time_period |
| `MINUS_DI` | Minus Directional Indicator | symbol, interval, time_period |
| `PLUS_DM` | Plus Directional Movement | symbol, interval, time_period |
| `MINUS_DM` | Minus Directional Movement | symbol, interval, time_period |
| `SAR` | Parabolic SAR | symbol, interval |
| `APO` | Absolute Price Oscillator | symbol, interval, series_type |
| `PPO` | Percentage Price Oscillator | symbol, interval, series_type |

### Volatility Indicators
| Tool | Description | Required |
|------|-------------|----------|
| `BBANDS` | Bollinger Bands | symbol, interval, time_period, series_type |
| `ATR` | Average True Range | symbol, interval, time_period |
| `NATR` | Normalized ATR | symbol, interval, time_period |
| `TRANGE` | True Range | symbol, interval |
| `MIDPOINT` | Midpoint (high+low)/2 | symbol, interval, time_period, series_type |
| `MIDPRICE` | Midprice | symbol, interval, time_period |

### Volume Indicators
| Tool | Description | Required |
|------|-------------|----------|
| `AD` | Chaikin A/D Line | symbol, interval |
| `ADOSC` | Chaikin A/D Oscillator | symbol, interval |
| `OBV` | On Balance Volume | symbol, interval |

### Hilbert Transform (Cycle Analysis)
| Tool | Description | Required |
|------|-------------|----------|
| `HT_TRENDLINE` | Instantaneous Trendline | symbol, interval, series_type |
| `HT_SINE` | Sine Wave | symbol, interval, series_type |
| `HT_TRENDMODE` | Trend vs Cycle Mode | symbol, interval, series_type |
| `HT_DCPERIOD` | Dominant Cycle Period | symbol, interval, series_type |
| `HT_DCPHASE` | Dominant Cycle Phase | symbol, interval, series_type |
| `HT_PHASOR` | Phasor Components | symbol, interval, series_type |

**Common Parameters:**
- `interval`: 1min, 5min, 15min, 30min, 60min, daily, weekly, monthly
- `series_type`: close, open, high, low
- `time_period`: Number of data points for calculation
- `month`: YYYY-MM format (intraday only)

---

## Analytics

### ANALYTICS_FIXED_WINDOW
Advanced metrics over a fixed time window.
- **Required:** `symbols`, `range_param`, `interval`, `calculations`
- **Optional:** `ohlc` (close, open, high, low)

### ANALYTICS_SLIDING_WINDOW
Advanced metrics over sliding windows.
- **Required:** `symbols`, `range_param`, `interval`, `window_size`, `calculations`
- **Optional:** `ohlc`

**Calculations available:** MEAN, STDDEV, VARIANCE, CORRELATION, COVARIANCE, etc.

---

## Utility Tools

### SYMBOL_SEARCH
Find symbols by keyword.
- **Required:** `keywords`
- **Optional:** `datatype`, `entitlement`

### SEARCH
Natural language query for Alpha Vantage data.
- **Required:** `query`
- **Example:** "AAPL stock price daily", "Tesla earnings data"

### FETCH
Fetch data by Alpha Vantage function ID.
- **Required:** `id` (function name from search results)

### PING
Health check for the service.
- **Required:** none

---

## Example Usage

### Get Latest Quote
```
Tool: GLOBAL_QUOTE
Arguments: { "symbol": "AAPL" }
```

### Get Earnings with Estimates
```
Tool: EARNINGS
Arguments: { "symbol": "MSFT" }
```

### Get Forward Consensus Estimates
```
Tool: EARNINGS_ESTIMATES
Arguments: { "symbol": "NVDA" }
```

### Get Daily Price History
```
Tool: TIME_SERIES_DAILY
Arguments: { "symbol": "TSLA", "outputsize": "full" }
```

### Get RSI Indicator
```
Tool: RSI
Arguments: { "symbol": "SPY", "interval": "daily", "time_period": 14, "series_type": "close" }
```

### Get Market News
```
Tool: NEWS_SENTIMENT
Arguments: { "tickers": "AAPL,MSFT", "limit": 10 }
```

---

## Rate Limits

| Tier | Requests | Notes |
|------|----------|-------|
| **Free** | 25/day | Standard endpoints |
| **$49.99/mo** | 75/min | No daily limits |
| **$99.99/mo** | 150/min | No daily limits |
| **$149.99/mo** | 300/min | No daily limits |
| **$199.99/mo** | 600/min | No daily limits |
| **$249.99/mo** | 1200/min | No daily limits |

---

## Key Endpoints for Earnings Analysis

For your earnings attribution workflow, the most relevant tools are:

1. **EARNINGS** - Historical EPS with estimates and surprises
2. **EARNINGS_ESTIMATES** - Forward consensus (EPS + Revenue)
3. **EARNINGS_CALENDAR** - Upcoming earnings dates
4. **EARNINGS_CALL_TRANSCRIPT** - Full call transcripts
5. **NEWS_SENTIMENT** - News around earnings events
6. **COMPANY_OVERVIEW** - Company fundamentals context
