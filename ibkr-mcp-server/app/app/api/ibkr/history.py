"""Current price and historical OHLCV bar endpoints."""

import datetime as dt

from fastapi import HTTPException, Query

from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models.history import HistoricalBar, PriceSnapshot
from app.services.history import FREQ_TO_BAR_SIZE

# Module-level singletons for Query params that use non-str types (avoids B008).
_FROM_DATE = Query(description="Start date inclusive (YYYY-MM-DD)")
_TO_DATE = Query(
  default=None,
  description="End date inclusive (YYYY-MM-DD). Defaults to today.",
)


@ibkr_router.get("/price", operation_id="get_price", response_model=PriceSnapshot)
async def get_price(
  symbol: str = Query(description="Ticker symbol (e.g. SPX, VIX, AAPL)"),
  sec_type: str = Query(
    default="IND",
    description="Security type: IND, STK, ETF, FUT, CASH",
  ),
  exchange: str = Query(
    default="CBOE",
    description="Primary exchange (CBOE, NASDAQ, NYSE, …)",
  ),
  currency: str = Query(default="USD", description="Currency"),
) -> PriceSnapshot:
  """Get the latest price snapshot for any IB-supported contract.

  For indices (sec_type=IND) last contains the current index level and close
  contains the previous session close. bid/ask are null for pure indices.

  Args:
    symbol: Ticker symbol (e.g. "SPX", "VIX", "AAPL").
    sec_type: Security type (IND, STK, ETF, FUT, CASH).
    exchange: Primary exchange.
    currency: Currency code.

  Returns:
    PriceSnapshot with last, bid, ask, close, and UTC timestamp.

  Example:
    GET /ibkr/price?symbol=SPX&sec_type=IND&exchange=CBOE

  """
  try:
    logger.debug("Fetching current price: symbol={} exchange={}", symbol, exchange)
    return await ib_interface.get_current_price(symbol, sec_type, exchange, currency)
  except Exception as e:
    logger.error("Error fetching price for {}: {!s}", symbol, e)
    raise HTTPException(status_code=502, detail=f"IB Gateway error: {e}") from e


@ibkr_router.get(
  "/historical",
  operation_id="get_historical_bars",
  response_model=list[HistoricalBar],
)
async def get_historical_bars(
  symbol: str = Query(description="Ticker symbol (e.g. SPX, VIX, AAPL)"),
  sec_type: str = Query(
    default="IND",
    description="Security type: IND, STK, ETF, FUT, CASH",
  ),
  exchange: str = Query(
    default="CBOE",
    description="Primary exchange (CBOE, NASDAQ, NYSE, …)",
  ),
  freq: str = Query(
    default="1d",
    description=f"Bar frequency. One of: {', '.join(sorted(FREQ_TO_BAR_SIZE))}",
  ),
  from_date: dt.date = _FROM_DATE,
  to_date: dt.date | None = _TO_DATE,
  use_rth: bool = Query(default=True, description="Regular trading hours only"),
  currency: str = Query(default="USD", description="Currency"),
) -> list[HistoricalBar]:
  """Fetch OHLCV bars for any IB-supported contract over a date range.

  IB imposes per-bar-size limits on how much history can be fetched in one
  request. For intraday frequencies the maximum span is typically 30-60 days;
  for daily bars up to several years.

  Args:
    symbol: Ticker symbol.
    sec_type: Security type.
    exchange: Primary exchange.
    freq: Bar frequency (1min, 5min, 15min, 30min, 1h, 4h, 1d, 1w, 1M).
    from_date: Start date (inclusive).
    to_date: End date (inclusive). Defaults to today.
    use_rth: If True, only include regular-hours bars.
    currency: Currency code.

  Returns:
    List of OHLCV bars ordered oldest-first.

  Example:
    GET /ibkr/historical?symbol=SPX&sec_type=IND&exchange=CBOE&freq=1d
    &from_date=2024-01-01

  """
  resolved_to = to_date if to_date is not None else dt.datetime.now(dt.UTC).date()
  try:
    logger.debug(
      "Fetching historical: symbol={} exchange={} freq={} {}-{}",
      symbol,
      exchange,
      freq,
      from_date,
      resolved_to,
    )
    return await ib_interface.get_historical_bars(
      symbol,
      sec_type,
      exchange,
      freq,
      from_date,
      resolved_to,
      use_rth,
      currency,
    )
  except ValueError as e:
    raise HTTPException(status_code=422, detail=str(e)) from e
  except Exception as e:
    logger.error("Error fetching historical for {}: {!s}", symbol, e)
    raise HTTPException(status_code=502, detail=f"IB Gateway error: {e}") from e
