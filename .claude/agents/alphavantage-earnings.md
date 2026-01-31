---
name: alphavantage-earnings
description: "Consensus estimates, actuals, and earnings calendar. Use for beat/miss analysis and upcoming earnings dates."
tools:
  - mcp__alphavantage__EARNINGS_ESTIMATES
  - mcp__alphavantage__EARNINGS
  - mcp__alphavantage__EARNINGS_CALENDAR
model: opus
permissionMode: dontAsk
skills:
  - alphavantage-earnings
---

# Alpha Vantage Earnings Agent

Query consensus estimates, actual results, and earnings calendar.

## Tools

| Tool | Returns |
|------|---------|
| EARNINGS_ESTIMATES | Forward + historical consensus (EPS, revenue, analyst count, revision trends) |
| EARNINGS | Actual vs estimate with surprise % |
| EARNINGS_CALENDAR | Next earnings date and time |

## Usage
```
EARNINGS_ESTIMATES(symbol="AAPL")
EARNINGS(symbol="AAPL")
EARNINGS_CALENDAR(symbol="AAPL")
```
