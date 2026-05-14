"""Pydantic models for ticker data."""

from pydantic import BaseModel, Field


class GreeksData(BaseModel):
  """Model for options greeks data."""

  delta: float | None = Field(None, description="Delta value")
  gamma: float | None = Field(None, description="Gamma value")
  vega: float | None = Field(None, description="Vega value")
  theta: float | None = Field(None, description="Theta value")
  impliedVol: float | None = Field(None, description="Implied volatility")


class TickerData(BaseModel):
  """Model for ticker data."""

  contractId: int = Field(..., description="Contract ID")
  symbol: str = Field(..., description="Symbol")
  secType: str = Field(..., description="Security type")
  last: float | None = Field(None, description="Last price")
  bid: float | None = Field(None, description="Bid price")
  ask: float | None = Field(None, description="Ask price")
  greeks: GreeksData | None = Field(None, description="Greeks data for options")
  marketDataType: int | None = Field(
    None,
    description=(
      "IB market-data classification for this ticker: 1=Live, 2=Frozen, "
      "3=Delayed, 4=Delayed-Frozen. None if not reported. Mirrors the "
      "PriceSnapshot.market_data_type contract from Phase 1 so callers "
      "can tell live OPRA greeks (1) from delayed-frozen + model greeks (2/4)."
    ),
  )
