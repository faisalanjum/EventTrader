"""Historical OHLCV bars and current price snapshot operations."""

import datetime as dt
import math
import time

from ib_async.objects import BarData

from .client import IBClient
from app.core.setup_logging import logger
from app.models.history import HistoricalBar, PriceSnapshot


# Maps user-facing frequency strings to IB bar size settings.
FREQ_TO_BAR_SIZE: dict[str, str] = {
  "1min": "1 min",
  "5min": "5 mins",
  "15min": "15 mins",
  "30min": "30 mins",
  "1h": "1 hour",
  "4h": "4 hours",
  "1d": "1 day",
  "1w": "1 week",
  "1M": "1 month",
}

# IB whatToShow value per security type.
_WHAT_TO_SHOW: dict[str, str] = {
  "IND": "TRADES",
  "STK": "TRADES",
  "ETF": "TRADES",
  "FUT": "TRADES",
  "CASH": "MIDPOINT",
  "OPT": "TRADES",
}


def _to_float(v: float) -> float | None:
  """Return v as float, or None if it is NaN (IB sentinel for missing data)."""
  return None if math.isnan(v) else v


def _bar_date(bar: BarData) -> dt.date:
  """Extract date from a BarData, handling daily (date) and intraday (datetime) bars."""
  d = bar.date
  return d.date() if isinstance(d, dt.datetime) else d  # type: ignore[return-value]


def _bar_to_model(bar: BarData) -> HistoricalBar:
  """Convert an ib_async BarData to a HistoricalBar model."""
  vol = int(bar.volume) if bar.volume > 0 else None
  return HistoricalBar(
    timestamp=bar.date.isoformat(),
    open=bar.open,
    high=bar.high,
    low=bar.low,
    close=bar.close,
    volume=vol,
  )


class HistoryClient(IBClient):
  """Current price snapshots and historical OHLCV bar retrieval."""

  async def get_current_price(
    self,
    symbol: str,
    sec_type: str,
    exchange: str,
    currency: str = "USD",
  ) -> PriceSnapshot:
    """Fetch the latest price snapshot for a contract.

    Args:
      symbol: Ticker symbol (e.g. "SPX", "VIX", "AAPL").
      sec_type: Security type (IND, STK, ETF, FUT, CASH).
      exchange: Primary exchange (CBOE, NASDAQ, NYSE, …).
      currency: Currency code (default USD).

    Returns:
      PriceSnapshot with last, bid, ask, close, and UTC timestamp.

    """
    await self._connect()

    t0 = time.monotonic()
    contract = await self._qualify_contract(symbol, sec_type, exchange, currency)
    logger.debug("qualify_contract took {:.2f}s", time.monotonic() - t0)

    t0 = time.monotonic()
    if self._is_market_open():
      # Live path: reqTickersAsync returns real-time last/bid/ask.
      self.ib.reqMarketDataType(1)
      [ticker] = await self.ib.reqTickersAsync(contract)
      logger.debug("reqTickersAsync (live) took {:.2f}s", time.monotonic() - t0)
      return PriceSnapshot(
        symbol=contract.localSymbol or symbol,
        sec_type=sec_type,
        last=_to_float(ticker.last),
        bid=_to_float(ticker.bid),
        ask=_to_float(ticker.ask),
        close=_to_float(ticker.close),
        timestamp=dt.datetime.now(dt.UTC).isoformat(),
      )
    # Closed path: reqTickersAsync for indices waits ~11s for bid/ask that never
    # arrive. Use the last daily bar instead — IB returns it immediately.
    what_to_show = _WHAT_TO_SHOW.get(sec_type.upper(), "TRADES")
    bars = await self.ib.reqHistoricalDataAsync(
      contract,
      endDateTime="",
      durationStr="1 D",
      barSizeSetting="1 day",
      whatToShow=what_to_show,
      useRTH=True,
      formatDate=1,
      keepUpToDate=False,
    )
    logger.debug("reqHistoricalDataAsync (closed) took {:.2f}s", time.monotonic() - t0)
    if not bars:
      msg = f"No historical data returned for {symbol}/{exchange}"
      raise RuntimeError(msg)
    close = _to_float(bars[-1].close)
    return PriceSnapshot(
      symbol=contract.localSymbol or symbol,
      sec_type=sec_type,
      last=close,
      bid=None,
      ask=None,
      close=close,
      timestamp=dt.datetime.now(dt.UTC).isoformat(),
    )

  async def get_historical_bars(
    self,
    symbol: str,
    sec_type: str,
    exchange: str,
    freq: str,
    from_date: dt.date,
    to_date: dt.date,
    use_rth: bool = True,
    currency: str = "USD",
  ) -> list[HistoricalBar]:
    """Fetch OHLCV bars for a contract over a date range.

    Args:
      symbol: Ticker symbol (e.g. "SPX", "VIX", "AAPL").
      sec_type: Security type (IND, STK, ETF, FUT, CASH).
      exchange: Primary exchange.
      freq: Bar frequency — one of: 1min, 5min, 15min, 30min, 1h, 4h, 1d, 1w, 1M.
      from_date: First bar date (inclusive).
      to_date: Last bar date (inclusive).
      use_rth: Include regular trading hours only (default True).
      currency: Currency code (default USD).

    Returns:
      List of HistoricalBar ordered oldest-first.

    Raises:
      ValueError: If freq is unrecognised or from_date is after to_date.

    """
    bar_size = FREQ_TO_BAR_SIZE.get(freq)
    if bar_size is None:
      msg = f"Unsupported frequency '{freq}'. Valid values: {sorted(FREQ_TO_BAR_SIZE)}"
      raise ValueError(msg)

    if from_date > to_date:
      raise ValueError("from_date must not be after to_date")

    what_to_show = _WHAT_TO_SHOW.get(sec_type.upper(), "TRADES")

    # IB end datetime: end-of-day on to_date so all bars on that date are included.
    end_dt = dt.datetime.combine(to_date, dt.time(23, 59, 59))

    # Duration string covering from_date → to_date (inclusive).
    # IB accepts up to 365 D; for longer spans switch to full years.
    days = (to_date - from_date).days + 1
    duration = f"{math.ceil(days / 365)} Y" if days > 365 else f"{days} D"

    await self._connect()

    t0 = time.monotonic()
    contract = await self._qualify_contract(symbol, sec_type, exchange, currency)
    logger.debug("qualify_contract took {:.2f}s", time.monotonic() - t0)

    bars = await self.ib.reqHistoricalDataAsync(
      contract,
      endDateTime=end_dt,
      durationStr=duration,
      barSizeSetting=bar_size,
      whatToShow=what_to_show,
      useRTH=use_rth,
      formatDate=1,
      keepUpToDate=False,
    )

    logger.debug(
      "reqHistoricalData took {:.2f}s — received {} raw bars for {}/{} freq={} {}-{}",
      time.monotonic() - t0,
      len(bars),
      symbol,
      exchange,
      freq,
      from_date,
      to_date,
    )
    # IB's duration window is calendar days and may reach before from_date.
    # Post-filter to enforce the requested boundary.
    return [_bar_to_model(b) for b in bars if _bar_date(b) >= from_date]
