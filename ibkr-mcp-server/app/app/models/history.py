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
