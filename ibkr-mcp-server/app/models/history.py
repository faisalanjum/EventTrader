"""Pydantic models for current price and historical bar data."""

from pydantic import BaseModel, Field


class PriceSnapshot(BaseModel):
  """Current price snapshot for a contract."""

  symbol: str = Field(..., description="Contract local symbol")
  sec_type: str = Field(..., description="Security type (IND, STK, ETF, FUT, CASH)")
  last: float | None = Field(None, description="Last trade price / index level")
  bid: float | None = Field(None, description="Bid price (null for indices)")
  ask: float | None = Field(None, description="Ask price (null for indices)")
  close: float | None = Field(None, description="Previous session close")
  timestamp: str = Field(..., description="Snapshot time (UTC ISO-8601)")
  is_realtime: bool = Field(
    ...,
    description=(
      "True iff IB served this in live market-data mode (type 1) with an active "
      "subscription. False for: indices without CBOE sub, paper account without "
      "live entitlement, delayed/frozen feed, historical-bar fallback. Bots: trust "
      "last/bid/ask as the current market only when is_realtime=True."
    ),
  )
  market_data_type: int = Field(
    ...,
    description=(
      "IB's market-data-type classification: 1=Live (real-time), 2=Frozen (last "
      "RTH close), 3=Delayed (15-min lagged), 4=Delayed-Frozen. Use for "
      "fine-grained data-quality decisions."
    ),
  )


class HistoricalBar(BaseModel):
  """Single OHLCV bar from a historical data request."""

  timestamp: str = Field(
    ...,
    description="Bar open time (ISO-8601; local exchange TZ for intraday bars)",
  )
  open: float = Field(..., description="Open price")
  high: float = Field(..., description="High price")
  low: float = Field(..., description="Low price")
  close: float = Field(..., description="Close price")
  volume: int | None = Field(
    None,
    description="Volume (null for indices and instruments that report no volume)",
  )
