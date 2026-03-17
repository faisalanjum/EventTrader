"""Yahoo Finance MCP Server — provides financial data tools via yfinance."""

import json
import os

import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("yahoo-finance")


def _df_to_json(df):
    """Convert DataFrame with DatetimeIndex to JSON-serializable records."""
    return json.loads(df.reset_index().to_json(orient="records", date_format="iso"))


@mcp.tool()
def get_earnings_dates(ticker: str, limit: int = 12) -> str:
    """Get upcoming and past earnings dates with EPS estimates and actuals.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        limit: Number of earnings dates to return (default 12)
    """
    try:
        t = yf.Ticker(ticker)
        df = t.get_earnings_dates(limit=limit)
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "earnings_dates": []})
        return json.dumps({"ticker": ticker, "earnings_dates": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_quote(ticker: str) -> str:
    """Get current quote: price, volume, market cap, 52-week range, moving averages.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info.toJSON()
        return json.dumps({"ticker": ticker, "quote": json.loads(info)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_price_history(ticker: str, period: str = "1mo", interval: str = "1d") -> str:
    """Get OHLCV price history for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        period: Time period — 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        interval: Bar interval — 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "history": []})
        return json.dumps({"ticker": ticker, "period": period, "interval": interval, "history": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_calendar(ticker: str) -> str:
    """Get next earnings date, ex-dividend date, and analyst estimates.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        cal = t.get_calendar()
        if cal is None:
            return json.dumps({"ticker": ticker, "calendar": {}})
        return json.dumps({"ticker": ticker, "calendar": cal}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_news(ticker: str) -> str:
    """Get recent news articles for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        news = t.news
        if not news:
            return json.dumps({"ticker": ticker, "news": []})
        return json.dumps({"ticker": ticker, "news": news}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_stock_info(ticker: str) -> str:
    """Get comprehensive stock data: company info, sector, industry, financials summary, description.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            return json.dumps({"ticker": ticker, "info": {}})
        return json.dumps({"ticker": ticker, "info": info}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_stock_actions(ticker: str) -> str:
    """Get dividend and stock split history.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        actions = t.actions
        if actions is None or actions.empty:
            return json.dumps({"ticker": ticker, "actions": []})
        return json.dumps({"ticker": ticker, "actions": _df_to_json(actions)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_financial_statement(ticker: str, statement: str = "income", quarterly: bool = False) -> str:
    """Get financial statements: income statement, balance sheet, or cash flow.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        statement: One of 'income', 'balance', 'cashflow'
        quarterly: If true, return quarterly data instead of annual
    """
    try:
        t = yf.Ticker(ticker)
        stmt_map = {
            "income": (t.quarterly_income_stmt if quarterly else t.income_stmt),
            "balance": (t.quarterly_balance_sheet if quarterly else t.balance_sheet),
            "cashflow": (t.quarterly_cash_flow if quarterly else t.cash_flow),
        }
        df = stmt_map.get(statement)
        if df is None:
            return json.dumps({"error": f"Unknown statement type: {statement}. Use 'income', 'balance', or 'cashflow'."})
        if df.empty:
            return json.dumps({"ticker": ticker, "statement": statement, "data": []})
        # Financial statements have dates as columns and line items as rows — transpose for readability
        result = json.loads(df.T.reset_index().to_json(orient="records", date_format="iso"))
        return json.dumps({"ticker": ticker, "statement": statement, "quarterly": quarterly, "data": result}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_holder_info(ticker: str, holder_type: str = "institutional") -> str:
    """Get shareholder information: institutional, insider, or mutual fund holders.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        holder_type: One of 'institutional', 'insider', 'mutualfund', 'major'
    """
    try:
        t = yf.Ticker(ticker)
        holder_map = {
            "institutional": t.institutional_holders,
            "insider": t.insider_transactions,
            "mutualfund": t.mutualfund_holders,
            "major": t.major_holders,
        }
        df = holder_map.get(holder_type)
        if df is None:
            return json.dumps({"error": f"Unknown holder_type: {holder_type}. Use 'institutional', 'insider', 'mutualfund', or 'major'."})
        if df.empty:
            return json.dumps({"ticker": ticker, "holder_type": holder_type, "holders": []})
        return json.dumps({"ticker": ticker, "holder_type": holder_type, "holders": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_option_expiration_dates(ticker: str) -> str:
    """Get available option expiration dates for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        dates = t.options
        return json.dumps({"ticker": ticker, "expiration_dates": list(dates)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_option_chain(ticker: str, expiration: str) -> str:
    """Get option chain (calls and puts) for a specific expiration date.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        expiration: Expiration date string from get_option_expiration_dates (e.g. '2026-03-18')
    """
    try:
        t = yf.Ticker(ticker)
        chain = t.option_chain(expiration)
        result = {
            "ticker": ticker,
            "expiration": expiration,
            "calls": _df_to_json(chain.calls),
            "puts": _df_to_json(chain.puts),
        }
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_recommendations(ticker: str, include_upgrades: bool = False) -> str:
    """Get analyst recommendations summary and optionally detailed upgrades/downgrades history.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        include_upgrades: If true, also include detailed upgrades/downgrades history
    """
    try:
        t = yf.Ticker(ticker)
        rec = t.recommendations
        result = {"ticker": ticker}
        if rec is not None and not rec.empty:
            result["recommendations"] = _df_to_json(rec)
        else:
            result["recommendations"] = []
        if include_upgrades:
            ud = t.upgrades_downgrades
            if ud is not None and not ud.empty:
                # Limit to last 50 to avoid huge responses
                result["upgrades_downgrades"] = _df_to_json(ud.head(50))
            else:
                result["upgrades_downgrades"] = []
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_analyst_price_targets(ticker: str) -> str:
    """Get analyst price targets: current, low, high, mean, and median.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        targets = t.analyst_price_targets
        if not targets:
            return json.dumps({"ticker": ticker, "price_targets": {}})
        return json.dumps({"ticker": ticker, "price_targets": targets}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_earnings_estimate(ticker: str) -> str:
    """Get consensus earnings estimates: current quarter, next quarter, current year, next year.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        df = t.earnings_estimate
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "earnings_estimate": []})
        return json.dumps({"ticker": ticker, "earnings_estimate": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_earnings_history(ticker: str) -> str:
    """Get earnings beat/miss history: EPS estimate vs actual and surprise percentage.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        df = t.earnings_history
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "earnings_history": []})
        return json.dumps({"ticker": ticker, "earnings_history": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_revenue_estimate(ticker: str) -> str:
    """Get consensus revenue estimates: current quarter, next quarter, current year, next year.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        df = t.revenue_estimate
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "revenue_estimate": []})
        return json.dumps({"ticker": ticker, "revenue_estimate": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_eps_trend(ticker: str) -> str:
    """Get EPS trend data: current estimate, 7/30/90 day revisions for upcoming quarters/years.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        df = t.eps_trend
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "eps_trend": []})
        return json.dumps({"ticker": ticker, "eps_trend": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_growth_estimates(ticker: str) -> str:
    """Get growth estimates: stock vs industry vs sector vs S&P 500.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        df = t.growth_estimates
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "growth_estimates": []})
        return json.dumps({"ticker": ticker, "growth_estimates": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_sec_filings(ticker: str) -> str:
    """Get recent SEC filings with links, types, dates, and descriptions.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        filings = t.sec_filings
        if not filings:
            return json.dumps({"ticker": ticker, "sec_filings": []})
        return json.dumps({"ticker": ticker, "sec_filings": filings}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_insider_roster(ticker: str) -> str:
    """Get insider roster: names, positions, most recent transaction dates and holdings.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
    """
    try:
        t = yf.Ticker(ticker)
        df = t.insider_roster_holders
        if df is None or df.empty:
            return json.dumps({"ticker": ticker, "insider_roster": []})
        return json.dumps({"ticker": ticker, "insider_roster": _df_to_json(df)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        import uvicorn
        app = mcp.streamable_http_app()
        print("Starting Yahoo Finance MCP server (HTTP) on port 8000...", flush=True)
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        mcp.run(transport="stdio")
